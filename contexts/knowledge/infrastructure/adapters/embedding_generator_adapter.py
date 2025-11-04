"""
Embedding Generation Adapter

Generates vector embeddings for knowledge entry content using LLM or embedding model.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter for external embedding service
- Article V (SOLID): SRP - embedding generation only
"""

from typing import List
import hashlib
import json


class EmbeddingGeneratorAdapter:
    """
    Adapter for generating vector embeddings from text content.
    
    Uses OpenAI embeddings API (or compatible service) to generate
    1536-dimensional vectors for semantic search.
    
    Constitution Compliance:
        - Article II (Hexagonal): External service adapter
        - Article V (SOLID): Single responsibility - embedding generation
    """
    
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-ada-002"):
        """
        Initialize embedding generator with API configuration.
        
        Args:
            api_key: Optional API key for embedding service
                    If None, will attempt to use environment variable OPENAI_API_KEY
            model: Embedding model to use (default: text-embedding-ada-002)
        
        Models:
            - text-embedding-ada-002: 1536 dimensions (OpenAI standard)
            - text-embedding-3-small: 1536 dimensions (OpenAI newer, cheaper)
            - text-embedding-3-large: 3072 dimensions (OpenAI higher quality)
        """
        self._api_key = api_key
        self._model = model
        self._embedding_cache = {}  # Simple in-memory cache
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text content.
        
        Args:
            text: Text content to embed (knowledge entry content)
        
        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        
        Example:
            >>> generator = EmbeddingGeneratorAdapter()
            >>> embedding = await generator.generate_embedding("The spacecraft has quantum drive")
            >>> len(embedding)
            1536
            >>> all(isinstance(x, float) for x in embedding)
            True
        
        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding service fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        # Generate embedding
        try:
            embedding = await self._call_embedding_service(text)
            
            # Cache result
            self._embedding_cache[cache_key] = embedding
            
            return embedding
        
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        More efficient than calling generate_embedding() repeatedly.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process per API call (default: 100)
        
        Returns:
            List of embedding vectors, same order as input texts
        
        Example:
            >>> generator = EmbeddingGeneratorAdapter()
            >>> texts = ["text 1", "text 2", "text 3"]
            >>> embeddings = await generator.generate_embeddings_batch(texts)
            >>> len(embeddings) == len(texts)
            True
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self._call_embedding_service_batch(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text content."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    async def _call_embedding_service(self, text: str) -> List[float]:
        """
        Call external embedding service API.
        
        This is a placeholder implementation for MVP.
        In production, this would call OpenAI API or similar service.
        
        For now, we'll return a mock embedding for testing purposes.
        """
        # TODO: Implement actual OpenAI API call
        # Example:
        # import openai
        # response = await openai.Embedding.acreate(
        #     model=self._model,
        #     input=text,
        # )
        # return response['data'][0]['embedding']
        
        # Mock implementation for MVP
        return self._generate_mock_embedding(text)
    
    async def _call_embedding_service_batch(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Call external embedding service API for batch of texts.
        
        Placeholder implementation for MVP.
        """
        # TODO: Implement actual batch API call
        # In production, would batch multiple texts in single API call
        
        # Mock implementation
        return [self._generate_mock_embedding(text) for text in texts]
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic mock embedding for testing.
        
        Uses text hash to create consistent embeddings.
        Real implementation would call external API.
        """
        # Create deterministic seed from text
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        
        # Generate 1536-dimensional vector
        # Use simple hash-based approach for consistency
        import random
        random.seed(seed)
        
        # Generate normalized vector
        embedding = [random.gauss(0, 1) for _ in range(1536)]
        
        # Normalize to unit length (standard for embeddings)
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def clear_cache(self) -> None:
        """
        Clear embedding cache.
        
        Useful for testing or when memory is constrained.
        """
        self._embedding_cache.clear()
    
    def get_embedding_dimension(self) -> int:
        """
        Get dimensionality of embeddings produced by this generator.
        
        Returns:
            1536 for text-embedding-ada-002 (default)
            3072 for text-embedding-3-large
        """
        if self._model == "text-embedding-3-large":
            return 3072
        return 1536
