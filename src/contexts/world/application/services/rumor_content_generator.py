"""Rumor content generation during propagation.

This module handles the generation of rumor content based on historical events
and applies variations as rumors spread through the world.
"""


from src.contexts.world.domain.entities.history_event import (
    EventType,
    HistoryEvent,
)


class RumorContentGenerator:
    """Generates rumor content from historical events.

        This class provides methods to generate engaging rumor text based on
    the type of historical event, with support for different event categories.
    """

    def generate_content(self, event: HistoryEvent) -> str:
        """Generate rumor content based on event type.

        Uses templates specific to each event type to create
        engaging rumor text.

        Args:
            event: HistoryEvent to generate content for

        Returns:
            Rumor content string
        """
        event_type = event.event_type
        event_name = event.name

        generators = {
            EventType.WAR: self._generate_war_content,
            EventType.BATTLE: self._generate_battle_content,
            EventType.TRADE: self._generate_trade_content,
            EventType.DEATH: self._generate_death_content,
            EventType.BIRTH: self._generate_birth_content,
            EventType.MARRIAGE: self._generate_marriage_content,
            EventType.ALLIANCE: self._generate_alliance_content,
            EventType.CORONATION: self._generate_coronation_content,
            EventType.DISASTER: self._generate_disaster_content,
            EventType.DISCOVERY: self._generate_discovery_content,
            EventType.REVOLUTION: self._generate_revolution_content,
            EventType.MIRACLE: self._generate_miracle_content,
            EventType.MAGICAL: self._generate_magical_content,
        }

        generator = generators.get(event_type, self._generate_default_content)
        return generator(event, event_name)

    def _generate_war_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for war events."""
        faction_names = self._format_faction_list(event)
        return f"Word spreads of conflict between {faction_names}. {event_name}..."

    def _generate_battle_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for battle events."""
        location = self._format_location_list(event)
        return f"Tales of a great battle at {location} circulate. {event_name}..."

    def _generate_trade_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for trade events."""
        return f"Merchants whisper about new trade routes. {event_name}..."

    def _generate_death_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for death events."""
        figures = (
            ", ".join(event.key_figures) if event.key_figures else "a notable figure"
        )
        return f"Rumors of {figures}'s passing circulate through the realm..."

    def _generate_birth_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for birth events."""
        figures = (
            ", ".join(event.key_figures) if event.key_figures else "a notable figure"
        )
        return f"News arrives of {figures}'s birth. A new chapter begins..."

    def _generate_marriage_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for marriage events."""
        figures = (
            " and ".join(event.key_figures)
            if len(event.key_figures) >= 2
            else "two noble houses"
        )
        return f"Word spreads of the union between {figures}..."

    def _generate_alliance_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for alliance events."""
        faction_names = self._format_faction_list(event)
        return f"Diplomats speak of a new alliance between {faction_names}..."

    def _generate_coronation_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for coronation events."""
        figures = event.key_figures[0] if event.key_figures else "a new ruler"
        return f"Proclamations announce the coronation of {figures}..."

    def _generate_disaster_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for disaster events."""
        location = self._format_location_list(event)
        return f"Terrifying news of disaster at {location} spreads. {event_name}..."

    def _generate_discovery_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for discovery events."""
        location = self._format_location_list(event)
        return f"Whispers of a discovery at {location} excite scholars. {event_name}..."

    def _generate_revolution_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for revolution events."""
        location = self._format_location_list(event)
        return f"Reports of uprising in {location} spread rapidly. {event_name}..."

    def _generate_miracle_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for miracle events."""
        location = self._format_location_list(event)
        return f"Tales of a miracle at {location} inspire the faithful. {event_name}..."

    def _generate_magical_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate content for magical events."""
        location = self._format_location_list(event)
        return (
            f"Strange tales of magical occurrence at {location} spread. {event_name}..."
        )

    def _generate_default_content(self, event: HistoryEvent, event_name: str) -> str:
        """Generate default content for unknown event types."""
        location = self._format_location_list(event)
        return f"Something happened at {location}. {event_name}..."

    def _format_faction_list(self, event: HistoryEvent) -> str:
        """Format faction IDs as a readable string.

        Args:
            event: HistoryEvent with faction_ids

        Returns:
            Formatted string of faction names (or count if unavailable)
        """
        if not event.faction_ids:
            return "unknown parties"

        if len(event.faction_ids) == 1:
            return "an unknown faction"

        if len(event.faction_ids) == 2:
            return "two great powers"

        return f"{len(event.faction_ids)} factions"

    def _format_location_list(self, event: HistoryEvent) -> str:
        """Format location IDs as a readable string.

        Args:
            event: HistoryEvent with location_ids

        Returns:
            Formatted string describing locations
        """
        locations = event.location_ids or event.affected_location_ids or []

        if not locations:
            return "an unknown location"

        if len(locations) == 1:
            return "a distant land"

        return "several locations"
