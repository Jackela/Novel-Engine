## ADDED Requirements

### Requirement: Calendar tracks current in-world date

The WorldCalendar entity SHALL maintain the current in-world date consisting of:
- `year`: Positive integer representing the current year
- `month`: Integer from 1-12 representing the current month
- `day`: Integer from 1-30 representing the current day
- `era_name`: String label for the current era (e.g., "Third Age")

#### Scenario: Initial calendar state

- **WHEN** a new WorldCalendar is created with default values
- **THEN** the calendar SHALL have year=1, month=1, day=1, era_name="First Age"

#### Scenario: Custom initial calendar state

- **WHEN** a WorldCalendar is created with year=1042, month=5, day=14, era_name="Third Age"
- **THEN** the calendar SHALL reflect those exact values

---

### Requirement: Calendar validates date constraints

The WorldCalendar entity SHALL enforce the following constraints:
- Months SHALL be between 1 and 12 (inclusive)
- Days SHALL be between 1 and 30 (inclusive)
- Years SHALL be positive integers (>= 1)
- Era name SHALL be a non-empty string

#### Scenario: Invalid month rejected

- **WHEN** creating a WorldCalendar with month=13
- **THEN** the system SHALL raise a validation error

#### Scenario: Invalid day rejected

- **WHEN** creating a WorldCalendar with day=31
- **THEN** the system SHALL raise a validation error

#### Scenario: Invalid year rejected

- **WHEN** creating a WorldCalendar with year=0
- **THEN** the system SHALL raise a validation error

---

### Requirement: Time can be advanced by days

The WorldCalendar entity SHALL provide an `advance_days(n: int)` method that:
- Accepts a strictly positive integer (n >= 1)
- Increments the day by n
- Rolls over to next month when day exceeds 30
- Rolls over to next year when month exceeds 12
- Returns a new WorldCalendar instance (immutability)

#### Scenario: Advance days within same month

- **GIVEN** calendar at day=10, month=5, year=1042
- **WHEN** advance_days(5) is called
- **THEN** the result SHALL be day=15, month=5, year=1042

#### Scenario: Advance days crossing month boundary

- **GIVEN** calendar at day=28, month=5, year=1042
- **WHEN** advance_days(5) is called
- **THEN** the result SHALL be day=3, month=6, year=1042

#### Scenario: Advance days crossing year boundary

- **GIVEN** calendar at day=28, month=12, year=1042
- **WHEN** advance_days(5) is called
- **THEN** the result SHALL be day=3, month=1, year=1043

#### Scenario: Advance multiple months

- **GIVEN** calendar at day=15, month=3, year=1042
- **WHEN** advance_days(90) is called (3 months worth)
- **THEN** the result SHALL be day=15, month=6, year=1042

#### Scenario: Backward time travel prevented

- **WHEN** advance_days(0) or advance_days(-1) is called
- **THEN** the system SHALL raise a validation error

---

### Requirement: Calendar provides display formatting

The WorldCalendar entity SHALL provide a `display_string` property that returns a human-readable date format.

#### Scenario: Standard display format

- **GIVEN** calendar at year=1042, month=5, day=14, era_name="Third Age"
- **WHEN** display_string is accessed
- **THEN** the result SHALL be "Day 14, Month 5, Year 1042 (Third Age)"

---

### Requirement: Time advancement emits domain event

The WorldCalendar entity SHALL emit a `TimeAdvancedEvent` when time is advanced, containing:
- `previous_date`: The date before advancement
- `new_date`: The date after advancement
- `days_advanced`: The number of days advanced

#### Scenario: Event contains advancement details

- **GIVEN** calendar at day=10, month=5, year=1042
- **WHEN** advance_days(5) is called
- **THEN** a TimeAdvancedEvent SHALL be emitted with:
  - previous_date = {day=10, month=5, year=1042}
  - new_date = {day=15, month=5, year=1042}
  - days_advanced = 5
