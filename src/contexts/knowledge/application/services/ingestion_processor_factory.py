"""
Ingestion Processor Factory

Factory that maps SourceType to appropriate IIngestionProcessor
with a GenericProcessor fallback for unknown types.

Constitution Compliance:
- Article II (Hexagonal): Application service for processor creation
- Article V (SOLID): SRP - factory only handles processor instantiation
"""

from __future__ import annotations

from typing import Dict

from ...application.ports.i_ingestion_processor import IIngestionProcessor
from ...domain.models.source_type import SourceType
from .ingestion_processors import (
    GenericProcessor,
    LoreProcessor,
    CharacterProcessor,
    SceneProcessor,
    PlotlineProcessor,
    ItemProcessor,
    LocationProcessor,
)


class IngestionProcessorFactory:
    """
    Factory for creating ingestion processors by source type.

    Maps SourceType enum values to their corresponding processor implementations,
    with GenericProcessor as fallback for any unknown types.

    Why factory pattern:
        - Centralizes processor selection logic
        - Makes adding new processors straightforward
        - Supports testing with mock processors
        - Allows easy fallback behavior

    Example:
        >>> factory = IngestionProcessorFactory()
        >>> processor = factory.get_processor(SourceType.CHARACTER)
        >>> assert isinstance(processor, CharacterProcessor)

    Example with custom processor:
        >>> factory = IngestionProcessorFactory()
        >>> factory.register_processor(SourceType.CUSTOM, CustomProcessor())
        >>> processor = factory.get_processor(SourceType.CUSTOM)
    """

    # Default processor mapping - class level for easy modification
    _DEFAULT_PROCESSORS: Dict[SourceType, type[IIngestionProcessor]] = {
        SourceType.LORE: LoreProcessor,
        SourceType.CHARACTER: CharacterProcessor,
        SourceType.SCENE: SceneProcessor,
        SourceType.PLOTLINE: PlotlineProcessor,
        SourceType.ITEM: ItemProcessor,
        SourceType.LOCATION: LocationProcessor,
    }

    def __init__(
        self,
        custom_processors: Dict[SourceType, IIngestionProcessor] | None = None,
        fallback_processor: IIngestionProcessor | None = None,
    ):
        """
        Initialize the processor factory.

        Args:
            custom_processors: Optional mapping of SourceType to processor instances
                to override defaults. Useful for testing or custom behavior.
            fallback_processor: Optional custom fallback processor for unknown types.
                Defaults to GenericProcessor if not provided.
        """
        self._processors: Dict[SourceType, IIngestionProcessor] = {}

        # Register default processors (instantiate lazily)
        self._processor_classes = self._DEFAULT_PROCESSORS.copy()

        # Register any custom processors (already instantiated)
        if custom_processors:
            for source_type, processor in custom_processors.items():
                self._processors[source_type] = processor

        # Set fallback
        self._fallback_processor = fallback_processor

    def get_processor(self, source_type: SourceType) -> IIngestionProcessor:
        """
        Get the processor for a given source type.

        Args:
            source_type: The SourceType to get a processor for

        Returns:
            IIngestionProcessor instance for the source type

        Example:
            >>> factory = IngestionProcessorFactory()
            >>> processor = factory.get_processor(SourceType.LORE)
            >>> strategy = processor.get_chunking_strategy()
        """
        # Check for cached instance
        if source_type in self._processors:
            return self._processors[source_type]

        # Check for processor class to instantiate
        if source_type in self._processor_classes:
            processor_class = self._processor_classes[source_type]
            instance = processor_class()
            self._processors[source_type] = instance
            return instance

        # Use fallback
        if self._fallback_processor:
            return self._fallback_processor

        # Default fallback to GenericProcessor
        if SourceType.LORE not in self._processors:
            self._processors[SourceType.LORE] = GenericProcessor()

        return self._processors[SourceType.LORE]

    def register_processor(
        self,
        source_type: SourceType,
        processor: IIngestionProcessor,
    ) -> None:
        """
        Register a custom processor for a source type.

        Args:
            source_type: The SourceType to register the processor for
            processor: The processor instance to use

        Why:
            Allows customization and testing without modifying defaults.

        Example:
            >>> factory = IngestionProcessorFactory()
            >>> mock_processor = Mock(spec=IIngestionProcessor)
            >>> factory.register_processor(SourceType.CHARACTER, mock_processor)
        """
        self._processors[source_type] = processor

    def register_processor_class(
        self,
        source_type: SourceType,
        processor_class: type[IIngestionProcessor],
    ) -> None:
        """
        Register a processor class for lazy instantiation.

        Args:
            source_type: The SourceType to register the processor class for
            processor_class: The processor class to instantiate when needed

        Why:
            Supports lazy instantiation for memory efficiency.
        """
        self._processor_classes[source_type] = processor_class
        # Remove any cached instance
        self._processors.pop(source_type, None)

    def has_processor(self, source_type: SourceType) -> bool:
        """
        Check if a processor is registered for a source type.

        Args:
            source_type: The SourceType to check

        Returns:
            True if a processor is registered, False otherwise

        Example:
            >>> factory = IngestionProcessorFactory()
            >>> factory.has_processor(SourceType.CHARACTER)
            True
            >>> factory.has_processor(SourceType.CUSTOM)  # Assuming CUSTOM doesn't exist
            False
        """
        return (
            source_type in self._processors
            or source_type in self._processor_classes
        )

    def set_fallback_processor(self, processor: IIngestionProcessor) -> None:
        """
        Set the fallback processor for unknown source types.

        Args:
            processor: The processor to use as fallback

        Why:
            Allows custom fallback behavior for new content types.
        """
        self._fallback_processor = processor

    @classmethod
    def get_default_factory(cls) -> IngestionProcessorFactory:
        """
        Get a factory instance with all default processors.

        Returns:
            IngestionProcessorFactory with default configuration

        Why:
            Convenience method for getting a standard factory.
        """
        return cls()

    def get_registered_types(self) -> list[SourceType]:
        """
        Get all source types with registered processors.

        Returns:
            List of SourceType values that have processors

        Why:
            Useful for debugging and introspection.
        """
        types = set(self._processors.keys()) | set(self._processor_classes.keys())
        return list(types)


__all__ = ["IngestionProcessorFactory"]
