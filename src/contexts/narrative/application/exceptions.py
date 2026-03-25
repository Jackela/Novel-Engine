"""Narrative application layer exceptions."""


class NarrativeError(Exception):
    """Base exception for narrative context."""

    pass


class StoryNotFoundError(NarrativeError):
    """Story not found."""

    pass


class StoryAlreadyExistsError(NarrativeError):
    """Story already exists."""

    pass


class ChapterNotFoundError(NarrativeError):
    """Chapter not found."""

    pass


class SceneNotFoundError(NarrativeError):
    """Scene not found."""

    pass


class NarrativeValidationError(NarrativeError):
    """Validation error for narrative."""

    pass


class InvalidStoryStateError(NarrativeError):
    """Invalid story state."""

    pass


class SceneGenerationError(NarrativeError):
    """Error during scene generation."""

    pass
