#!/usr/bin/env python3
"""Debug script to test campaign log parsing"""

import tempfile

from chronicler_agent import ChroniclerAgent

# Test log content from the test
log_content = """
        Turn 1 - 2024-01-01 12:00:00
        [Agent Registration] pilot registered as Alex Chen - Galactic Defense Force
        [Turn Begin] Starting simulation in deep space research facility
        [Action] pilot: Navigating through asteroid field to reach station
        [Turn End] Turn 1 completed successfully

        Turn 2 - 2024-01-01 12:05:00
        [Agent Registration] scientist registered as Dr. Maya Patel - Research Institute
        [Action] scientist: Analyzing alien artifact discovered on asteroid
        [Action] pilot: Providing security for research operation
        [Turn End] Turn 2 completed with significant discoveries
        """

print("=== DEBUGGING CAMPAIGN LOG PARSING ===")
print("Original log content:")
print(repr(log_content))
print("\nLog content lines:")
for i, line in enumerate(log_content.split("\n")):
    print(f"{i:2d}: '{line.strip()}'")

print("\n=== Testing parsing ===")
chronicler = ChroniclerAgent()

# Parse content directly
events = chronicler._parse_campaign_log_content(log_content)
print(f"\nParsed {len(events)} events:")
for i, event in enumerate(events):
    print(
        f"  {i+1}. {event.event_type}: {event.description} (participants: {event.participants})"
    )

# Generate segments
segments = chronicler._generate_narrative_segments(events)
print(f"\nGenerated {len(segments)} narrative segments:")
for i, segment in enumerate(segments):
    print(f"  {i+1}. {segment.event_type}: {segment.narrative_text[:100]}...")

# Combine story
story = chronicler._combine_narrative_segments(segments)
print(f"\nFinal story length: {len(story)}")
print("Story content:")
print(story)

# Test file-based parsing
with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
    f.write(log_content)
    temp_path = f.name

try:
    story2 = chronicler.transcribe_log(temp_path)
    print(f"\nFile-based transcription length: {len(story2)}")
    print("File-based story:")
    print(story2)
finally:
    import os

    os.unlink(temp_path)
