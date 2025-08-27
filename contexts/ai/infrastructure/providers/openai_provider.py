#!/usr/bin/env python3
"""
OpenAI Provider Implementation

Concrete implementation of ILLMProvider for OpenAI's GPT models.
Handles authentication, API communication, and response mapping
for OpenAI's REST API.
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


class OpenAIProvider(ILLMProvider):
    """
    OpenAI provider implementation with GPT model support.
    
    Provides integration with OpenAI's API for text generation,
    chat completions, and other AI operations using GPT models.
    """
    
    def __init__(
        self,
        api_key: str,
        organization_id: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key for authentication
            organization_id: Optional organization ID
            base_url: Base URL for OpenAI API
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
        """
        self._api_key = api_key
        self._organization_id = organization_id
        self._base_url = base_url.rstrip('/')
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        
        # Initialize provider identity
        self._provider_id = ProviderId(
            provider_name="OpenAI",
            provider_type=ProviderType.OPENAI,
            api_version="1.0.0",
            metadata={
                "base_url": self._base_url,
                "organization_id": self._organization_id
            }
        )
        
        # Define supported models with capabilities and pricing
        self._supported_models = self._initialize_supported_models()
        
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
        # Simple availability check - could be enhanced with health checks
        return bool(self._api_key)
    
    async def generate_async(
        self,
        request: LLMRequest,
        budget: Optional[TokenBudget] = None
    ) -> LLMResponse:
        """
        Generate response using OpenAI API.
        
        Args:
            request: LLM request to process
            budget: Optional token budget for enforcement
            
        Returns:
            LLM response with generated content
        """
        # Validate request
        if not self.validate_request(request):
            return LLMResponse.create_error(
                request_id=request.request_id,
                status=LLMResponseStatus.INVALID_REQUEST,
                error_details="Invalid request parameters for OpenAI provider"
            )
        
        # Check budget if provided
        if budget:
            estimated_tokens = self.estimate_tokens(request.prompt)
            estimated_cost = request.model_id.estimate_cost(estimated_tokens, request.max_tokens or 100)
            
            if budget.cost_limit and estimated_cost > (budget.cost_limit - budget.accumulated_cost):
                return LLMResponse.create_error(
                    request_id=request.request_id,
                    status=LLMResponseStatus.QUOTA_EXCEEDED,
                    error_details="Estimated cost exceeds budget limit"
                )
        
        try:
            # Get HTTP session
            session = await self._get_session()
            
            # Prepare API request
            api_request = self._prepare_api_request(request)
            
            # Make API call
            async with session.post(
                f"{self._base_url}/chat/completions",
                json=api_request,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self._timeout_seconds)
            ) as response:
                
                response_data = await response.json()
                
                if response.status == 200:
                    return self._parse_success_response(request, response_data)
                else:
                    return self._parse_error_response(request, response.status, response_data)
                    
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
        Generate streaming response using OpenAI API.
        
        Args:
            request: LLM request to process
            budget: Optional token budget for enforcement
            
        Yields:
            Streaming response chunks
        """
        if not self.validate_request(request):
            yield "Error: Invalid request parameters"
            return
        
        try:
            session = await self._get_session()
            api_request = self._prepare_api_request(request, stream=True)
            
            async with session.post(
                f"{self._base_url}/chat/completions",
                json=api_request,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self._timeout_seconds)
            ) as response:
                
                if response.status != 200:
                    yield f"Error: HTTP {response.status}"
                    return
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and data['choices']:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text using GPT tokenization rules.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Rough approximation: 1 token ≈ 4 characters for English text
        # This is a simplified estimation - real implementations would use tiktoken
        char_count = len(text)
        
        # Adjust for different content types
        if re.search(r'[^\x00-\x7F]', text):  # Non-ASCII characters
            token_ratio = 0.6  # Non-English text typically has fewer tokens per character
        else:
            token_ratio = 0.25  # English text: ~4 chars per token
        
        estimated_tokens = max(1, int(char_count * token_ratio))
        
        # Add some buffer for system messages and formatting
        return int(estimated_tokens * 1.1)
    
    def validate_request(self, request: LLMRequest) -> bool:
        """
        Validate request compatibility with OpenAI provider.
        
        Args:
            request: Request to validate
            
        Returns:
            True if request is valid for OpenAI
        """
        # Check if model is supported
        if request.model_id.model_name not in self._supported_models:
            return False
        
        # Check request type compatibility
        compatible_types = {
            LLMRequestType.CHAT,
            LLMRequestType.COMPLETION,
            LLMRequestType.CONVERSATION
        }
        
        if request.request_type not in compatible_types:
            return False
        
        # Check parameter ranges
        if not 0.0 <= request.temperature <= 2.0:
            return False
        
        if request.top_p and not 0.0 <= request.top_p <= 1.0:
            return False
        
        # Check max tokens
        max_model_tokens = self._supported_models[request.model_id.model_name].max_output_tokens
        if request.max_tokens and request.max_tokens > max_model_tokens:
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
            
            # Test API connectivity with minimal request
            async with session.get(
                f"{self._base_url}/models",
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                is_healthy = response.status == 200
                
                return {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'response_time_ms': 0,  # Would measure actual response time
                    'api_status': response.status,
                    'provider': 'OpenAI',
                    'timestamp': asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'provider': 'OpenAI',
                'timestamp': asyncio.get_event_loop().time()
            }
    
    async def close_async(self) -> None:
        """Clean up provider resources."""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
    
    def _initialize_supported_models(self) -> Dict[str, ModelId]:
        """Initialize supported models with capabilities and pricing."""
        models = {}
        
        # GPT-4 models
        models["gpt-4"] = ModelId(
            model_name="gpt-4",
            provider_id=self._provider_id,
            capabilities={
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CONVERSATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.ANALYSIS,
                ModelCapability.FUNCTION_CALLING
            },
            max_context_tokens=8192,
            max_output_tokens=4096,
            cost_per_input_token=Decimal('0.00003'),  # $0.03 per 1K tokens
            cost_per_output_token=Decimal('0.00006')  # $0.06 per 1K tokens
        )
        
        models["gpt-4-turbo-preview"] = ModelId(
            model_name="gpt-4-turbo-preview",
            provider_id=self._provider_id,
            capabilities={
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CONVERSATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.ANALYSIS,
                ModelCapability.FUNCTION_CALLING
            },
            max_context_tokens=128000,
            max_output_tokens=4096,
            cost_per_input_token=Decimal('0.00001'),  # $0.01 per 1K tokens
            cost_per_output_token=Decimal('0.00003')  # $0.03 per 1K tokens
        )
        
        # GPT-3.5 models
        models["gpt-3.5-turbo"] = ModelId(
            model_name="gpt-3.5-turbo",
            provider_id=self._provider_id,
            capabilities={
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CONVERSATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.FUNCTION_CALLING
            },
            max_context_tokens=4096,
            max_output_tokens=4096,
            cost_per_input_token=Decimal('0.0000015'),  # $0.0015 per 1K tokens
            cost_per_output_token=Decimal('0.000002')  # $0.002 per 1K tokens
        )
        
        return models
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            return self._session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Novel-Engine-AI-Gateway/1.0'
        }
        
        if self._organization_id:
            headers['OpenAI-Organization'] = self._organization_id
        
        return headers
    
    def _prepare_api_request(self, request: LLMRequest, stream: bool = False) -> Dict[str, Any]:
        """
        Prepare OpenAI API request from LLM request.
        
        Args:
            request: LLM request to convert
            stream: Whether to enable streaming
            
        Returns:
            Dictionary for OpenAI API request
        """
        # Convert prompt to messages format for chat completions
        messages = []
        
        if request.system_prompt:
            messages.append({
                'role': 'system',
                'content': request.system_prompt
            })
        
        # Extract messages from metadata if available (from chat requests)
        if request.metadata and 'messages' in request.metadata:
            messages.extend(request.metadata['messages'])
        else:
            # Convert simple prompt to user message
            messages.append({
                'role': 'user',
                'content': request.prompt
            })
        
        api_request = {
            'model': request.model_id.model_name,
            'messages': messages,
            'temperature': request.temperature,
            'stream': stream
        }
        
        # Optional parameters
        if request.max_tokens:
            api_request['max_tokens'] = request.max_tokens
        
        if request.top_p is not None:
            api_request['top_p'] = request.top_p
        
        if request.presence_penalty is not None:
            api_request['presence_penalty'] = request.presence_penalty
        
        if request.frequency_penalty is not None:
            api_request['frequency_penalty'] = request.frequency_penalty
        
        if request.stop_sequences:
            api_request['stop'] = request.stop_sequences
        
        return api_request
    
    def _parse_success_response(self, request: LLMRequest, response_data: Dict[str, Any]) -> LLMResponse:
        """
        Parse successful OpenAI API response.
        
        Args:
            request: Original request
            response_data: API response data
            
        Returns:
            LLM response object
        """
        # Extract content from response
        choices = response_data.get('choices', [])
        content = ""
        
        if choices:
            message = choices[0].get('message', {})
            content = message.get('content', '')
        
        # Extract usage statistics
        usage = response_data.get('usage', {})
        usage_stats = {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }
        
        # Calculate cost
        model_id = request.model_id
        input_cost = Decimal('0')
        output_cost = Decimal('0')
        
        if model_id.cost_per_input_token:
            input_cost = Decimal(str(usage_stats['input_tokens'])) * model_id.cost_per_input_token
        
        if model_id.cost_per_output_token:
            output_cost = Decimal(str(usage_stats['output_tokens'])) * model_id.cost_per_output_token
        
        return LLMResponse.create_success(
            request_id=request.request_id,
            content=content,
            model_id=model_id,
            input_tokens=usage_stats['input_tokens'],
            output_tokens=usage_stats['output_tokens'],
            cost_estimate=input_cost + output_cost,
            provider_response=response_data
        )
    
    def _parse_error_response(
        self, 
        request: LLMRequest, 
        status_code: int, 
        response_data: Dict[str, Any]
    ) -> LLMResponse:
        """
        Parse error response from OpenAI API.
        
        Args:
            request: Original request
            status_code: HTTP status code
            response_data: API response data
            
        Returns:
            LLM error response
        """
        # Map HTTP status codes to LLM response statuses
        status_mapping = {
            400: LLMResponseStatus.INVALID_REQUEST,
            401: LLMResponseStatus.FAILED,
            429: LLMResponseStatus.RATE_LIMITED,
            500: LLMResponseStatus.FAILED,
            502: LLMResponseStatus.FAILED,
            503: LLMResponseStatus.MODEL_UNAVAILABLE,
            504: LLMResponseStatus.TIMEOUT
        }
        
        llm_status = status_mapping.get(status_code, LLMResponseStatus.FAILED)
        
        # Extract error details
        error_info = response_data.get('error', {})
        error_message = error_info.get('message', f'HTTP {status_code} error')
        
        return LLMResponse.create_error(
            request_id=request.request_id,
            status=llm_status,
            error_details=error_message,
            provider_response=response_data
        )