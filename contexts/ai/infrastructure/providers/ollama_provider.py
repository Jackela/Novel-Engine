#!/usr/bin/env python3
"""
Ollama Provider Implementation

Concrete implementation of ILLMProvider for Ollama's local LLM models.
Handles local API communication and response mapping for Ollama's REST API.
"""

import asyncio
import json
import re
from decimal import Decimal
from typing import Dict, List, Optional, Any, AsyncIterator
from uuid import uuid4

import aiohttp

from ...domain.services.llm_provider import (
    ILLMProvider, LLMRequest, LLMResponse, LLMRequestType, LLMResponseStatus
)
from ...domain.value_objects.common import ProviderId, ModelId, TokenBudget, ModelCapability, ProviderType


class OllamaProvider(ILLMProvider):
    """
    Ollama provider implementation for local LLM models.
    
    Provides integration with Ollama's local API for running
    open-source models locally without external API dependencies.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 60,
        max_retries: int = 2
    ):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Base URL for Ollama API
            timeout_seconds: Request timeout (longer for local models)
            max_retries: Maximum retry attempts
        """
        self._base_url = base_url.rstrip('/')
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        
        # Initialize provider identity
        self._provider_id = ProviderId(
            provider_name="Ollama",
            provider_type=ProviderType.CUSTOM,
            api_version="1.0.0",
            metadata={
                "base_url": self._base_url,
                "local": True
            }
        )
        
        # Available models will be discovered at runtime
        self._supported_models: Dict[str, ModelId] = {}
        self._models_loaded = False
        
        # HTTP session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
    
    @property
    def provider_id(self) -> ProviderId:
        """Get the provider identifier."""
        return self._provider_id
    
    @property
    def supported_models(self) -> List[ModelId]:
        """Get list of models supported by this provider."""
        return list(self._supported_models.values())
    
    @property
    def is_available(self) -> bool:
        """Check if provider is currently available."""
        # This would be enhanced with actual connectivity check
        return True
    
    async def generate_async(
        self,
        request: LLMRequest,
        budget: Optional[TokenBudget] = None
    ) -> LLMResponse:
        """
        Generate response using Ollama API.
        
        Args:
            request: LLM request to process
            budget: Optional token budget for enforcement
            
        Returns:
            LLM response with generated content
        """
        # Ensure models are loaded
        await self._ensure_models_loaded()
        
        # Validate request
        if not self.validate_request(request):
            return LLMResponse.create_error(
                request_id=request.request_id,
                status=LLMResponseStatus.INVALID_REQUEST,
                error_details="Invalid request parameters for Ollama provider"
            )
        
        # Budget checking is simpler for local models (no API costs)
        if budget and budget.allocated_tokens > 0:
            estimated_tokens = self.estimate_tokens(request.prompt)
            if budget.consumed_tokens + estimated_tokens > budget.allocated_tokens:
                return LLMResponse.create_error(
                    request_id=request.request_id,
                    status=LLMResponseStatus.QUOTA_EXCEEDED,
                    error_details="Estimated tokens exceed budget allocation"
                )
        
        try:
            session = await self._get_session()
            api_request = self._prepare_api_request(request)
            
            async with session.post(
                f"{self._base_url}/api/generate",
                json=api_request,
                timeout=aiohttp.ClientTimeout(total=self._timeout_seconds)
            ) as response:
                
                if response.status == 200:
                    # Ollama streams by default, collect full response
                    full_response = await self._collect_full_response(response)
                    return self._parse_success_response(request, full_response)
                else:
                    response_text = await response.text()
                    return self._parse_error_response(request, response.status, response_text)
                    
        except asyncio.TimeoutError:
            return LLMResponse.create_error(
                request_id=request.request_id,
                status=LLMResponseStatus.TIMEOUT,
                error_details="Request timed out"
            )
        except aiohttp.ClientError as e:
            return LLMResponse.create_error(
                request_id=request.request_id,
                status=LLMResponseStatus.FAILED,
                error_details=f"HTTP client error: {str(e)}"
            )
        except Exception as e:
            return LLMResponse.create_error(
                request_id=request.request_id,
                status=LLMResponseStatus.FAILED,
                error_details=f"Unexpected error: {str(e)}"
            )
    
    async def generate_stream_async(
        self,
        request: LLMRequest,
        budget: Optional[TokenBudget] = None
    ) -> AsyncIterator[str]:
        """
        Generate streaming response using Ollama API.
        
        Args:
            request: LLM request to process
            budget: Optional token budget for enforcement
            
        Yields:
            Streaming response chunks
        """
        await self._ensure_models_loaded()
        
        if not self.validate_request(request):
            yield "Error: Invalid request parameters"
            return
        
        try:
            session = await self._get_session()
            api_request = self._prepare_api_request(request, stream=True)
            
            async with session.post(
                f"{self._base_url}/api/generate",
                json=api_request,
                timeout=aiohttp.ClientTimeout(total=self._timeout_seconds)
            ) as response:
                
                if response.status != 200:
                    yield f"Error: HTTP {response.status}"
                    return
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str:
                        try:
                            data = json.loads(line_str)
                            if 'response' in data:
                                yield data['response']
                            
                            # Check if done
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Simple estimation for local models
        # Different models may have different tokenizers
        char_count = len(text)
        
        # Conservative estimation: ~3 characters per token for most models
        estimated_tokens = max(1, int(char_count / 3))
        
        return estimated_tokens
    
    def validate_request(self, request: LLMRequest) -> bool:
        """
        Validate request compatibility with Ollama provider.
        
        Args:
            request: Request to validate
            
        Returns:
            True if request is valid for Ollama
        """
        # Check request type compatibility
        compatible_types = {
            LLMRequestType.COMPLETION,
            LLMRequestType.CHAT,
            LLMRequestType.CONVERSATION
        }
        
        if request.request_type not in compatible_types:
            return False
        
        # Check parameter ranges
        if not 0.0 <= request.temperature <= 2.0:
            return False
        
        if request.top_p and not 0.0 <= request.top_p <= 1.0:
            return False
        
        return True
    
    def get_model_info(self, model_name: str) -> Optional[ModelId]:
        """
        Get detailed information about specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information if supported, None otherwise
        """
        return self._supported_models.get(model_name)
    
    async def health_check_async(self) -> Dict[str, Any]:
        """
        Perform provider health check.
        
        Returns:
            Health status information
        """
        try:
            session = await self._get_session()
            
            # Test API connectivity
            async with session.get(
                f"{self._base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                is_healthy = response.status == 200
                
                if is_healthy:
                    # Also check if any models are available
                    response_data = await response.json()
                    models = response_data.get('models', [])
                    has_models = len(models) > 0
                    
                    return {
                        'status': 'healthy' if has_models else 'unhealthy',
                        'models_available': len(models),
                        'api_status': response.status,
                        'provider': 'Ollama',
                        'timestamp': asyncio.get_event_loop().time(),
                        'issues': [] if has_models else ['No models installed']
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'api_status': response.status,
                        'provider': 'Ollama',
                        'timestamp': asyncio.get_event_loop().time()
                    }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'provider': 'Ollama',
                'timestamp': asyncio.get_event_loop().time()
            }
    
    async def close_async(self) -> None:
        """Clean up provider resources."""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
    
    async def discover_models_async(self) -> List[str]:
        """
        Discover available models from Ollama.
        
        Returns:
            List of available model names
        """
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self._base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    return [model['name'] for model in models]
                else:
                    return []
                    
        except Exception:
            return []
    
    async def _ensure_models_loaded(self) -> None:
        """Ensure supported models list is loaded."""
        if not self._models_loaded:
            await self._load_supported_models()
            self._models_loaded = True
    
    async def _load_supported_models(self) -> None:
        """Load available models from Ollama API."""
        model_names = await self.discover_models_async()
        
        for model_name in model_names:
            # Create model info based on known model characteristics
            model_info = self._create_model_info(model_name)
            self._supported_models[model_name] = model_info
    
    def _create_model_info(self, model_name: str) -> ModelId:
        """
        Create ModelId for discovered model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelId with estimated capabilities
        """
        # Determine capabilities based on model name patterns
        capabilities = {ModelCapability.TEXT_GENERATION}
        
        # Common model patterns and their capabilities
        if any(pattern in model_name.lower() for pattern in ['chat', 'instruct', 'vicuna']):
            capabilities.add(ModelCapability.CONVERSATION)
        
        if any(pattern in model_name.lower() for pattern in ['code', 'deepseek', 'starcoder']):
            capabilities.add(ModelCapability.CODE_GENERATION)
        
        # Estimate context window based on model name
        context_tokens = 4096  # Default
        if 'llama2' in model_name.lower():
            context_tokens = 4096
        elif 'llama' in model_name.lower():
            context_tokens = 2048
        elif 'mistral' in model_name.lower():
            context_tokens = 8192
        elif 'deepseek' in model_name.lower():
            context_tokens = 16384
        
        return ModelId(
            model_name=model_name,
            provider_id=self._provider_id,
            capabilities=capabilities,
            max_context_tokens=context_tokens,
            max_output_tokens=min(context_tokens // 2, 4096),
            # Local models have no API cost
            cost_per_input_token=Decimal('0'),
            cost_per_output_token=Decimal('0')
        )
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            return self._session
    
    def _prepare_api_request(self, request: LLMRequest, stream: bool = False) -> Dict[str, Any]:
        """
        Prepare Ollama API request from LLM request.
        
        Args:
            request: LLM request to convert
            stream: Whether to enable streaming
            
        Returns:
            Dictionary for Ollama API request
        """
        # Combine system prompt and main prompt
        prompt = ""
        if request.system_prompt:
            prompt = f"System: {request.system_prompt}\n\nUser: {request.prompt}"
        else:
            prompt = request.prompt
        
        api_request = {
            'model': request.model_id.model_name,
            'prompt': prompt,
            'stream': stream,
            'options': {}
        }
        
        # Map parameters to Ollama options
        if request.temperature != 0.7:  # Only include if different from default
            api_request['options']['temperature'] = request.temperature
        
        if request.top_p is not None:
            api_request['options']['top_p'] = request.top_p
        
        if request.max_tokens:
            api_request['options']['num_predict'] = request.max_tokens
        
        if request.stop_sequences:
            api_request['options']['stop'] = request.stop_sequences
        
        return api_request
    
    async def _collect_full_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """
        Collect full response from Ollama streaming API.
        
        Args:
            response: HTTP response from Ollama
            
        Returns:
            Collected response data
        """
        content_parts = []
        final_data = {}
        
        async for line in response.content:
            line_str = line.decode('utf-8').strip()
            
            if line_str:
                try:
                    data = json.loads(line_str)
                    
                    # Collect response content
                    if 'response' in data:
                        content_parts.append(data['response'])
                    
                    # Keep track of final data for metadata
                    final_data = data
                    
                    # Check if done
                    if data.get('done', False):
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Combine collected content
        full_content = ''.join(content_parts)
        
        # Return combined response data
        return {
            'response': full_content,
            'done': True,
            'total_duration': final_data.get('total_duration', 0),
            'load_duration': final_data.get('load_duration', 0),
            'prompt_eval_count': final_data.get('prompt_eval_count', 0),
            'eval_count': final_data.get('eval_count', 0),
            'context': final_data.get('context', [])
        }
    
    def _parse_success_response(self, request: LLMRequest, response_data: Dict[str, Any]) -> LLMResponse:
        """
        Parse successful Ollama API response.
        
        Args:
            request: Original request
            response_data: API response data
            
        Returns:
            LLM response object
        """
        content = response_data.get('response', '')
        
        # Extract usage statistics from Ollama response
        prompt_tokens = response_data.get('prompt_eval_count', 0)
        completion_tokens = response_data.get('eval_count', 0)
        
        usage_stats = {
            'input_tokens': prompt_tokens,
            'output_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens
        }
        
        # Local models have no API cost
        return LLMResponse.create_success(
            request_id=request.request_id,
            content=content,
            model_id=request.model_id,
            input_tokens=usage_stats['input_tokens'],
            output_tokens=usage_stats['output_tokens'],
            cost_estimate=Decimal('0'),  # No cost for local models
            provider_response=response_data
        )
    
    def _parse_error_response(
        self, 
        request: LLMRequest, 
        status_code: int, 
        response_text: str
    ) -> LLMResponse:
        """
        Parse error response from Ollama API.
        
        Args:
            request: Original request
            status_code: HTTP status code
            response_text: Response text
            
        Returns:
            LLM error response
        """
        # Map HTTP status codes to LLM response statuses
        status_mapping = {
            400: LLMResponseStatus.INVALID_REQUEST,
            404: LLMResponseStatus.MODEL_UNAVAILABLE,
            500: LLMResponseStatus.FAILED,
            502: LLMResponseStatus.FAILED,
            503: LLMResponseStatus.MODEL_UNAVAILABLE,
            504: LLMResponseStatus.TIMEOUT
        }
        
        llm_status = status_mapping.get(status_code, LLMResponseStatus.FAILED)
        
        # Try to extract error details from response
        error_message = response_text or f'HTTP {status_code} error'
        
        try:
            # Ollama sometimes returns JSON error responses
            error_data = json.loads(response_text)
            if 'error' in error_data:
                error_message = error_data['error']
        except (json.JSONDecodeError, TypeError):
            pass
        
        return LLMResponse.create_error(
            request_id=request.request_id,
            status=llm_status,
            error_details=error_message
        )