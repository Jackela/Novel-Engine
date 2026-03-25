"""Character Application Service

Application service for character management operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from src.contexts.character.domain.aggregates.character import Character
from src.shared.application.result import Failure, Result, Success


class CharacterRepository(Protocol):
    """Protocol for character repository.

    Defines the contract for character persistence operations.
    Implementations handle the actual storage mechanism.
    """

    async def get_by_id(self, character_id: UUID) -> Optional[Character]:
        """Get a character by ID."""
        ...

    async def get_by_story(
        self,
        story_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Character]:
        """Get all characters in a story."""
        ...

    async def save(self, character: Character) -> None:
        """Save a character (create or update)."""
        ...

    async def delete(self, character_id: UUID) -> bool:
        """Delete a character. Returns True if deleted."""
        ...

    async def exists(self, character_id: UUID) -> bool:
        """Check if a character exists."""
        ...


class CharacterMemoryPort(Protocol):
    """Protocol for character memory operations.

    Defines the contract for storing and retrieving character memories.
    """

    async def store(
        self,
        character_id: UUID,
        content: str,
        story_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a memory for a character."""
        ...

    async def get_memories(
        self,
        character_id: UUID,
        story_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get memories for a character."""
        ...

    async def search_memories(
        self,
        character_id: UUID,
        query: str,
        story_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search memories for a character."""
        ...


class CharacterApplicationService:
    """Application service for character management.

    Handles character CRUD operations, attribute management,
    skills, inventory, relationships, and memory operations.

    AI注意:
    - Coordinates between domain aggregates and infrastructure
    - Returns Result[T, E] for error handling
    - All operations are async
    - Supports both character management and memory operations
    """

    def __init__(
        self,
        character_repo: Optional[CharacterRepository] = None,
        memory_port: Optional[CharacterMemoryPort] = None,
    ):
        """Initialize the service.

        Args:
            character_repo: Repository for character persistence
            memory_port: Optional port for memory operations
        """
        self.character_repo = character_repo
        self.memory_port = memory_port

    # Character CRUD Operations

    async def create_character(
        self,
        name: str,
        description: Optional[str] = None,
        attributes: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Character]:
        """Create a new character.

        Args:
            name: Character name
            description: Optional character description
            attributes: Optional attribute overrides
            metadata: Optional metadata

        Returns:
            Result containing the created character
        """
        try:
            character = Character(
                name=name,
                description=description,
                metadata=metadata or {},
            )

            if attributes:
                for attr_name, value in attributes.items():
                    character.set_attribute(attr_name, value)

            if self.character_repo:
                await self.character_repo.save(character)

            return Success(character)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def get_character(self, character_id: str) -> Result[Character]:
        """Get a character by ID.

        Args:
            character_id: The character UUID as string

        Returns:
            Result containing the character or error
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            return Success(character)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def update_character(
        self,
        character_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Result[Character]:
        """Update a character's basic information.

        Args:
            character_id: The character UUID as string
            name: Optional new name
            description: Optional new description
            status: Optional new status

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            # Note: Character is immutable for core fields in this domain model
            # We would need to implement update methods on the aggregate
            if description is not None:
                character.update_description(description)

            if status is not None:
                character.update_status(status)

            await self.character_repo.save(character)

            return Success(character)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def delete_character(self, character_id: str) -> Result[bool]:
        """Delete a character.

        Args:
            character_id: The character UUID as string

        Returns:
            Result containing success status
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            deleted = await self.character_repo.delete(UUID(character_id))

            if not deleted:
                return Failure("Character not found", "NOT_FOUND")

            return Success(True)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    # Attribute Operations

    async def update_attribute(
        self,
        character_id: str,
        attribute_name: str,
        value: int,
    ) -> Result[Character]:
        """Update a character attribute.

        Args:
            character_id: The character UUID as string
            attribute_name: Name of the attribute
            value: New value (1-100)

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            character.set_attribute(attribute_name, value)
            await self.character_repo.save(character)

            return Success(character)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def get_attributes(self, character_id: str) -> Result[Dict[str, int]]:
        """Get all attributes for a character.

        Args:
            character_id: The character UUID as string

        Returns:
            Result containing the attributes dictionary
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            return Success(character.attributes)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    # Skill Operations

    async def add_skill(
        self,
        character_id: str,
        name: str,
        category: str,
        level: int = 1,
        description: Optional[str] = None,
    ) -> Result[Character]:
        """Add a skill to a character.

        Args:
            character_id: The character UUID as string
            name: Skill name
            category: Skill category
            level: Skill level (1-100)
            description: Optional skill description

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            from src.contexts.character.domain.aggregates.character import Skill

            skill = Skill(
                name=name,
                category=category,
                level=level,
                description=description,
            )

            character.add_skill(skill)
            await self.character_repo.save(character)

            return Success(character)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def remove_skill(
        self,
        character_id: str,
        skill_name: str,
    ) -> Result[Character]:
        """Remove a skill from a character.

        Args:
            character_id: The character UUID as string
            skill_name: Name of the skill to remove

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            character.remove_skill(skill_name)
            await self.character_repo.save(character)

            return Success(character)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    # Inventory Operations

    async def add_item(
        self,
        character_id: str,
        name: str,
        item_type: str,
        quantity: int = 1,
        description: Optional[str] = None,
    ) -> Result[Character]:
        """Add an item to a character's inventory.

        Args:
            character_id: The character UUID as string
            name: Item name
            item_type: Type of item
            quantity: Quantity (default 1)
            description: Optional item description

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            from src.contexts.character.domain.aggregates.character import Item

            item = Item(
                name=name,
                item_type=item_type,
                quantity=quantity,
                description=description,
            )

            character.add_item(item)
            await self.character_repo.save(character)

            return Success(character)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def remove_item(
        self,
        character_id: str,
        item_id: str,
    ) -> Result[Character]:
        """Remove an item from a character's inventory.

        Args:
            character_id: The character UUID as string
            item_id: The item UUID as string

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            character.remove_item(UUID(item_id))
            await self.character_repo.save(character)

            return Success(character)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    # Relationship Operations

    async def add_relationship(
        self,
        character_id: str,
        target_character_id: str,
        relationship_type: str,
        strength: int = 50,
        description: Optional[str] = None,
    ) -> Result[Character]:
        """Add a relationship between characters.

        Args:
            character_id: The character UUID as string
            target_character_id: The target character UUID as string
            relationship_type: Type of relationship
            strength: Relationship strength (0-100)
            description: Optional description

        Returns:
            Result containing the updated character
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            character.add_relationship(
                target_character_id=UUID(target_character_id),
                relationship_type=relationship_type,
                strength=strength,
                description=description,
            )
            await self.character_repo.save(character)

            return Success(character)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    # Memory Operations

    async def store_memory(
        self,
        character_id: str,
        content: str,
        story_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[str]:
        """Store a memory for a character.

        Args:
            character_id: The character UUID as string
            content: Memory content
            story_id: Optional story context
            metadata: Optional metadata

        Returns:
            Result containing the memory ID
        """
        try:
            if not self.memory_port:
                return Failure("Memory port not configured", "CONFIG_ERROR")

            memory_id = await self.memory_port.store(
                character_id=UUID(character_id),
                content=content,
                story_id=story_id,
                metadata=metadata,
            )

            return Success(memory_id)

        except Exception as e:
            return Failure(str(e), "MEMORY_ERROR")

    async def get_memories(
        self,
        character_id: str,
        story_id: Optional[str] = None,
        limit: int = 100,
    ) -> Result[List[Dict[str, Any]]]:
        """Get memories for a character.

        Args:
            character_id: The character UUID as string
            story_id: Optional story context filter
            limit: Maximum number of memories

        Returns:
            Result containing list of memories
        """
        try:
            if not self.memory_port:
                return Failure("Memory port not configured", "CONFIG_ERROR")

            memories = await self.memory_port.get_memories(
                character_id=UUID(character_id),
                story_id=story_id,
                limit=limit,
            )

            return Success(memories)

        except Exception as e:
            return Failure(str(e), "MEMORY_ERROR")

    async def search_memories(
        self,
        character_id: str,
        query: str,
        story_id: Optional[str] = None,
        top_k: int = 5,
    ) -> Result[List[Dict[str, Any]]]:
        """Search memories for a character.

        Args:
            character_id: The character UUID as string
            query: Search query
            story_id: Optional story context
            top_k: Number of results

        Returns:
            Result containing list of matching memories
        """
        try:
            if not self.memory_port:
                return Failure("Memory port not configured", "CONFIG_ERROR")

            memories = await self.memory_port.search_memories(
                character_id=UUID(character_id),
                query=query,
                story_id=story_id,
                top_k=top_k,
            )

            return Success(memories)

        except Exception as e:
            return Failure(str(e), "MEMORY_ERROR")

    # Experience and Leveling

    async def add_experience(
        self,
        character_id: str,
        amount: int,
    ) -> Result[Dict[str, Any]]:
        """Add experience points to a character.

        Args:
            character_id: The character UUID as string
            amount: Experience amount to add

        Returns:
            Result containing experience update info
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            old_level = character.level
            leveled_up = character.gain_experience(amount)

            await self.character_repo.save(character)

            result = {
                "character_id": character_id,
                "experience_gained": amount,
                "total_experience": character.experience,
                "current_level": character.level,
                "leveled_up": leveled_up,
                "levels_gained": character.level - old_level if leveled_up else 0,
            }

            return Success(result)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    # Query Operations

    async def list_characters(
        self,
        story_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Result[List[Character]]:
        """List characters.

        Args:
            story_id: Optional story context filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Result containing list of characters
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            if story_id:
                characters = await self.character_repo.get_by_story(
                    story_id=story_id,
                    limit=limit,
                    offset=offset,
                )
            else:
                # TODO: Implement list_all in repository
                characters = []

            return Success(characters)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def get_character_stats(self, character_id: str) -> Result[Dict[str, Any]]:
        """Get statistics for a character.

        Args:
            character_id: The character UUID as string

        Returns:
            Result containing character statistics
        """
        try:
            if not self.character_repo:
                return Failure("Character repository not configured", "CONFIG_ERROR")

            character = await self.character_repo.get_by_id(UUID(character_id))

            if not character:
                return Failure("Character not found", "NOT_FOUND")

            stats = {
                "character_id": str(character.id),
                "name": character.name,
                "level": character.level,
                "experience": character.experience,
                "status": character.status,
                "attribute_points": character.total_attribute_points,
                "average_attribute": character.average_attribute,
                "skill_count": len(character.skills),
                "inventory_count": character.inventory_weight,
                "relationship_count": len(character.relationships),
            }

            return Success(stats)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")
