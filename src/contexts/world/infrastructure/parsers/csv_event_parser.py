"""CSV parser for bulk event import.

This module provides CSV parsing functionality for importing historical events.
"""

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


@dataclass
class CSVParseResult:
    """Result of parsing a CSV file.

    Attributes:
        success: Whether parsing was successful
        events: List of parsed event dictionaries
        total_rows: Total number of rows processed
        errors: List of parsing errors
    """

    success: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)
    total_rows: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)


class CSVEventParser:
    """Parser for CSV event import files.

    This parser handles CSV files containing historical event data,
    converting rows to event dictionaries suitable for creating HistoryEvent objects.

    Expected CSV format:
        name,description,event_type,significance,outcome,date_description,...

    List fields (location_ids, faction_ids, etc.) should be semicolon-separated.
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

    # Fields that contain lists (semicolon-separated)
    LIST_FIELDS = {
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
        """Initialize the CSV parser."""
        self.logger = logger.bind(parser="CSVEventParser")

    def parse(self, csv_content: str, skip_header: bool = True) -> CSVParseResult:
        """Parse CSV content into event dictionaries.

        Args:
            csv_content: Raw CSV content as string
            skip_header: Whether to skip the first row (header)

        Returns:
            CSVParseResult containing parsed events and any errors
        """
        self.logger.info("csv_parse_started", content_length=len(csv_content))

        result = CSVParseResult()
        rows = csv_content.strip().split("\n")

        if not rows:
            self.logger.warning("csv_empty_content")
            result.errors.append({"row": 0, "message": "Empty CSV content"})
            return result

        # Parse using CSV reader for proper quote handling
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            fieldnames = reader.fieldnames or []
        except csv.Error as e:
            self.logger.error("csv_parse_error", error=str(e))
            result.errors.append({"row": 0, "message": f"CSV parse error: {e}"})
            return result

        # Validate required fields exist
        missing_fields = self.REQUIRED_FIELDS - set(fieldnames)
        if missing_fields:
            self.logger.error(
                "csv_missing_required_fields", fields=list(missing_fields)
            )
            result.errors.append(
                {
                    "row": 0,
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                }
            )
            return result

        # Process each row
        for row_num, row in enumerate(reader, start=1):
            result.total_rows += 1
            event, errors = self._parse_row(row, row_num)

            if errors:
                result.errors.extend(errors)
            elif event:
                result.events.append(event)

        result.success = len(result.errors) == 0

        self.logger.info(
            "csv_parse_completed",
            total_rows=result.total_rows,
            success_count=len(result.events),
            error_count=len(result.errors),
        )

        return result

    def _parse_row(
        self, row: Dict[str, str], row_num: int
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse a single CSV row into an event dictionary.

        Args:
            row: CSV row as dictionary
            row_num: Row number for error reporting

        Returns:
            Tuple of (event_dict or None, list of errors)
        """
        errors: list[Any] = []
        event: Dict[str, Any] = {}

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            value = row.get(field_name, "").strip()
            if not value:
                errors.append(
                    {
                        "row": row_num,
                        "field": field_name,
                        "message": f"Required field '{field_name}' is empty",
                        "value": "",
                    }
                )
            else:
                event[field_name] = value

        if errors:
            return None, errors

        # Parse optional fields
        for opt_field, default_value in self.OPTIONAL_FIELDS.items():
            value = row.get(opt_field, "").strip()

            if not value:
                event[opt_field] = default_value
            elif opt_field in self.LIST_FIELDS:
                # Parse semicolon-separated list
                event[opt_field] = [v.strip() for v in value.split(";") if v.strip()]
            elif opt_field == "is_secret":
                # Parse boolean
                event[opt_field] = value.lower() in ("true", "1", "yes", "t")
            elif opt_field == "narrative_importance":
                # Parse integer
                try:
                    event[opt_field] = int(value)
                    if not 0 <= event[opt_field] <= 100:
                        errors.append(
                            {
                                "row": row_num,
                                "field": opt_field,
                                "message": "narrative_importance must be between 0 and 100",
                                "value": value,
                            }
                        )
                except ValueError:
                    errors.append(
                        {
                            "row": row_num,
                            "field": opt_field,
                            "message": "Invalid integer value",
                            "value": value,
                        }
                    )
                    event[opt_field] = default_value
            else:
                event[opt_field] = value

        # Validate enum values
        event_type = event.get("event_type", "").lower()
        if event_type not in self.VALID_EVENT_TYPES:
            errors.append(
                {
                    "row": row_num,
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
                    "row": row_num,
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
                    "row": row_num,
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
                        "row": row_num,
                        "field": "impact_scope",
                        "message": f"Invalid impact_scope: '{impact_scope}'",
                        "value": impact_scope,
                    }
                )
            else:
                event["impact_scope"] = impact_scope

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
        if len(description) < 1:
            errors.append(
                {
                    "row": index,
                    "field": "description",
                    "message": "Description cannot be empty",
                    "value": "",
                }
            )

        return errors
