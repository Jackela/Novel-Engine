"""JSON parser for bulk event import.

This module provides JSON parsing functionality for importing historical events.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


@dataclass
class JSONParseResult:
    """Result of parsing a JSON file.

    Attributes:
        success: Whether parsing was successful
        events: List of parsed event dictionaries
        total_records: Total number of records processed
        errors: List of parsing errors
    """

    success: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)
    total_records: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)


class JSONEventParser:
    """Parser for JSON event import files.

    This parser handles JSON files containing historical event data,
    converting records to event dictionaries suitable for creating HistoryEvent objects.

    Expected JSON format:
        {
            "events": [
                {
                    "name": "Event Name",
                    "description": "Event description",
                    "event_type": "war",
                    ...
                }
            ]
        }

    Or a direct array:
        [
            {"name": "Event 1", ...},
            {"name": "Event 2", ...}
        ]
    """

    # Required fields for event creation
    REQUIRED_FIELDS = {
        "name",
        "description",
        "event_type",
        "significance",
        "outcome",
        "date_description",
    }

    # Optional fields with their default values
    OPTIONAL_FIELDS: dict[str, Any] = {
        "duration_description": None,
        "location_ids": [],
        "faction_ids": [],
        "key_figures": [],
        "causes": [],
        "consequences": [],
        "preceding_event_ids": [],
        "following_event_ids": [],
        "related_event_ids": [],
        "is_secret": False,
        "sources": [],
        "narrative_importance": 50,
        "impact_scope": None,
        "affected_faction_ids": [],
        "affected_location_ids": [],
    }

    # Valid enum values
    VALID_EVENT_TYPES = {
        "war",
        "battle",
        "treaty",
        "founding",
        "destruction",
        "discovery",
        "invention",
        "coronation",
        "death",
        "birth",
        "marriage",
        "revolution",
        "migration",
        "disaster",
        "miracle",
        "prophecy",
        "conquest",
        "liberation",
        "alliance",
        "betrayal",
        "religious",
        "cultural",
        "economic",
        "scientific",
        "magical",
        "political",
        "trade",
        "natural",
    }

    VALID_SIGNIFICANCE = {
        "trivial",
        "minor",
        "moderate",
        "major",
        "world_changing",
        "legendary",
    }
    VALID_OUTCOMES = {"positive", "negative", "neutral", "mixed", "unknown"}
    VALID_IMPACT_SCOPES = {"local", "regional", "global"}

    def __init__(self) -> None:
        """Initialize the JSON parser."""
        self.logger = logger.bind(parser="JSONEventParser")

    def parse(self, json_content: str) -> JSONParseResult:
        """Parse JSON content into event dictionaries.

        Args:
            json_content: Raw JSON content as string

        Returns:
            JSONParseResult containing parsed events and any errors
        """
        self.logger.info("json_parse_started", content_length=len(json_content))

        result = JSONParseResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            self.logger.error("json_decode_error", error=str(e))
            result.errors.append({"row": 0, "message": f"JSON decode error: {e}"})
            return result

        # Extract events array
        events_data: List[Dict[str, Any]] = []
        if isinstance(data, list):
            events_data = data
        elif isinstance(data, dict):
            if "events" in data:
                events_data = data.get("events", [])
                if not isinstance(events_data, list):
                    result.errors.append(
                        {"row": 0, "message": "'events' field must be an array"}
                    )
                    return result
            else:
                # Single event object
                events_data = [data]
        else:
            result.errors.append(
                {"row": 0, "message": "JSON must be an object or array"}
            )
            return result

        result.total_records = len(events_data)

        # Parse each event
        for idx, event_data in enumerate(events_data, start=1):
            if not isinstance(event_data, dict):
                result.errors.append(
                    {
                        "row": idx,
                        "message": f"Event must be an object, got {type(event_data).__name__}",
                    }
                )
                continue

            event, errors = self._parse_event(event_data, idx)
            if errors:
                result.errors.extend(errors)
            elif event:
                result.events.append(event)

        result.success = len(result.errors) == 0

        self.logger.info(
            "json_parse_completed",
            total_records=result.total_records,
            success_count=len(result.events),
            error_count=len(result.errors),
        )

        return result

    def _parse_event(
        self, data: Dict[str, Any], index: int
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse a single event from JSON data.

        Args:
            data: Event data dictionary
            index: Event index for error reporting

        Returns:
            Tuple of (event_dict or None, list of errors)
        """
        errors: list[Any] = []
        event: Dict[str, Any] = {}

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            value = data.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(
                    {
                        "row": index,
                        "field": field_name,
                        "message": f"Required field '{field_name}' is missing or empty",
                        "value": str(value) if value is not None else None,
                    }
                )
            else:
                event[field_name] = value.strip() if isinstance(value, str) else value

        if errors:
            return None, errors

        # Parse optional fields
        for opt_field, default_value in self.OPTIONAL_FIELDS.items():
            value = data.get(opt_field)

            if value is None:
                event[opt_field] = default_value
            elif opt_field == "is_secret":
                # Parse boolean
                if isinstance(value, bool):
                    event[opt_field] = value
                elif isinstance(value, str):
                    event[opt_field] = value.lower() in ("true", "1", "yes", "t")
                else:
                    event[opt_field] = bool(value)
            elif opt_field == "narrative_importance":
                # Parse integer
                try:
                    event[field] = int(value) if value is not None else default_value
                    if not 0 <= event[field] <= 100:
                        errors.append(
                            {
                                "row": index,
                                "field": field_name,
                                "message": "narrative_importance must be between 0 and 100",
                                "value": str(value),
                            }
                        )
                except (ValueError, TypeError):
                    errors.append(
                        {
                            "row": index,
                            "field": field_name,
                            "message": "Invalid integer value",
                            "value": str(value),
                        }
                    )
                    event[field] = default_value
            elif field in [
                "location_ids",
                "faction_ids",
                "key_figures",
                "causes",
                "consequences",
                "preceding_event_ids",
                "following_event_ids",
                "related_event_ids",
                "sources",
                "affected_faction_ids",
                "affected_location_ids",
            ]:
                # Parse list fields
                if isinstance(value, list):
                    event[field] = [str(v) for v in value if v is not None]
                elif isinstance(value, str):
                    # Support semicolon-separated string
                    event[field] = [v.strip() for v in value.split(";") if v.strip()]
                else:
                    event[field] = [str(value)] if value is not None else []
            else:
                event[field] = value

        # Validate enum values
        event_type = event.get("event_type", "").lower()
        if event_type not in self.VALID_EVENT_TYPES:
            errors.append(
                {
                    "row": index,
                    "field": "event_type",
                    "message": f"Invalid event_type: '{event_type}'",
                    "value": event_type,
                }
            )
        else:
            event["event_type"] = event_type

        significance = event.get("significance", "").lower()
        if significance not in self.VALID_SIGNIFICANCE:
            errors.append(
                {
                    "row": index,
                    "field": "significance",
                    "message": f"Invalid significance: '{significance}'",
                    "value": significance,
                }
            )
        else:
            event["significance"] = significance

        outcome = event.get("outcome", "").lower()
        if outcome not in self.VALID_OUTCOMES:
            errors.append(
                {
                    "row": index,
                    "field": "outcome",
                    "message": f"Invalid outcome: '{outcome}'",
                    "value": outcome,
                }
            )
        else:
            event["outcome"] = outcome

        # Validate impact_scope if present
        impact_scope = event.get("impact_scope")
        if impact_scope:
            impact_scope = impact_scope.lower()
            if impact_scope not in self.VALID_IMPACT_SCOPES:
                errors.append(
                    {
                        "row": index,
                        "field": "impact_scope",
                        "message": f"Invalid impact_scope: '{impact_scope}'",
                        "value": impact_scope,
                    }
                )
            else:
                event["impact_scope"] = impact_scope

        # Validate name and description
        name = event.get("name", "")
        if len(name) > 300:
            errors.append(
                {
                    "row": index,
                    "field": "name",
                    "message": f"Name exceeds 300 characters ({len(name)})",
                    "value": name[:50] + "...",
                }
            )

        description = event.get("description", "")
        if not description or len(description) < 1:
            errors.append(
                {
                    "row": index,
                    "field": "description",
                    "message": "Description cannot be empty",
                    "value": "",
                }
            )

        return event if not errors else None, errors

    def validate_events(
        self, events: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate a list of parsed events.

        Args:
            events: List of event dictionaries

        Returns:
            Tuple of (valid_events, errors)
        """
        valid_events: list[Any] = []
        errors: list[Any] = []
        for i, event in enumerate(events):
            event_errors = self._validate_event(event, i + 1)
            if event_errors:
                errors.extend(event_errors)
            else:
                valid_events.append(event)

        return valid_events, errors

    def _validate_event(
        self, event: Dict[str, Any], index: int
    ) -> List[Dict[str, Any]]:
        """Validate a single event.

        Args:
            event: Event dictionary
            index: Event index for error reporting

        Returns:
            List of validation errors
        """
        errors: list[Any] = []
        # Validate name length
        name = event.get("name", "")
        if len(name) > 300:
            errors.append(
                {
                    "row": index,
                    "field": "name",
                    "message": f"Name exceeds 300 characters ({len(name)})",
                    "value": name[:50] + "...",
                }
            )

        # Validate description
        description = event.get("description", "")
        if not description or len(description) < 1:
            errors.append(
                {
                    "row": index,
                    "field": "description",
                    "message": "Description cannot be empty",
                    "value": "",
                }
            )

        return errors
