#!/usr/bin/env python3
"""
Unit tests for World Time API Schemas

Test suite for WorldTimeResponse and AdvanceTimeRequest schemas
used by the world time router endpoints.
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


class TestWorldTimeResponse:
    """Test suite for WorldTimeResponse schema."""

    def test_world_time_response_creation_success(self):
        """Test successful WorldTimeResponse creation with all fields."""
        from src.api.schemas.world_schemas import WorldTimeResponse

        response = WorldTimeResponse(
            year=1247,
            month=6,
            day=15,
            era_name="Third Era",
            display_string="15th day of the 6th month, 1247 Third Era",
        )

        assert response.year == 1247
        assert response.month == 6
        assert response.day == 15
        assert response.era_name == "Third Era"
        assert response.display_string == "15th day of the 6th month, 1247 Third Era"

    def test_world_time_response_required_fields(self):
        """Test that all fields are required for WorldTimeResponse."""
        from src.api.schemas.world_schemas import WorldTimeResponse

        # Missing year
        with pytest.raises(ValidationError) as exc_info:
            WorldTimeResponse(
                month=6,
                day=15,
                era_name="Third Era",
                display_string="test",
            )
        assert "year" in str(exc_info.value)

        # Missing month
        with pytest.raises(ValidationError) as exc_info:
            WorldTimeResponse(
                year=1247,
                day=15,
                era_name="Third Era",
                display_string="test",
            )
        assert "month" in str(exc_info.value)

        # Missing day
        with pytest.raises(ValidationError) as exc_info:
            WorldTimeResponse(
                year=1247,
                month=6,
                era_name="Third Era",
                display_string="test",
            )
        assert "day" in str(exc_info.value)

        # Missing era_name
        with pytest.raises(ValidationError) as exc_info:
            WorldTimeResponse(
                year=1247,
                month=6,
                day=15,
                display_string="test",
            )
        assert "era_name" in str(exc_info.value)

        # Missing display_string
        with pytest.raises(ValidationError) as exc_info:
            WorldTimeResponse(
                year=1247,
                month=6,
                day=15,
                era_name="Third Era",
            )
        assert "display_string" in str(exc_info.value)

    def test_world_time_response_field_types(self):
        """Test that fields have correct types."""
        from src.api.schemas.world_schemas import WorldTimeResponse

        response = WorldTimeResponse(
            year=1247,
            month=6,
            day=15,
            era_name="Third Era",
            display_string="test",
        )

        assert isinstance(response.year, int)
        assert isinstance(response.month, int)
        assert isinstance(response.day, int)
        assert isinstance(response.era_name, str)
        assert isinstance(response.display_string, str)


class TestAdvanceTimeRequest:
    """Test suite for AdvanceTimeRequest schema."""

    def test_advance_time_request_default_value(self):
        """Test that AdvanceTimeRequest has default value of 1 day."""
        from src.api.schemas.world_schemas import AdvanceTimeRequest

        request = AdvanceTimeRequest()

        assert request.days == 1

    def test_advance_time_request_valid_range(self):
        """Test AdvanceTimeRequest with valid day values."""
        from src.api.schemas.world_schemas import AdvanceTimeRequest

        # Minimum value
        request_min = AdvanceTimeRequest(days=1)
        assert request_min.days == 1

        # Maximum value
        request_max = AdvanceTimeRequest(days=365)
        assert request_max.days == 365

        # Middle value
        request_mid = AdvanceTimeRequest(days=30)
        assert request_mid.days == 30

    def test_advance_time_request_validation_too_low(self):
        """Test that AdvanceTimeRequest rejects days < 1."""
        from src.api.schemas.world_schemas import AdvanceTimeRequest

        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest(days=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest(days=-1)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_advance_time_request_validation_too_high(self):
        """Test that AdvanceTimeRequest rejects days > 365."""
        from src.api.schemas.world_schemas import AdvanceTimeRequest

        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest(days=366)
        assert "less than or equal to 365" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest(days=1000)
        assert "less than or equal to 365" in str(exc_info.value)

    def test_advance_time_request_field_type(self):
        """Test that days field is an integer."""
        from src.api.schemas.world_schemas import AdvanceTimeRequest

        request = AdvanceTimeRequest(days=10)

        assert isinstance(request.days, int)
