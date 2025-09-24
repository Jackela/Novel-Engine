#!/usr/bin/env python3
"""Debug script to replicate the exact test conditions"""

import os
import tempfile

from chronicler_agent import ChroniclerAgent

# Create the exact log content from the test
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

print("=== REPLICATING EXACT TEST CONDITIONS ===")

# Create the temp file exactly like the test does
with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
    f.write(log_content)
    temp_path = f.name

print(f"Created temp file: {temp_path}")

try:
    # Test with no parameters like the test does
    chronicler = ChroniclerAgent()
    story = chronicler.transcribe_log(temp_path)

    print(f"Story length: {len(story)}")
    print(f"Story content: {repr(story)}")

    if len(story) >= 200:
        print("✅ SUCCESS: Story length adequate")
    else:
        print("❌ FAILED: Story too short")

    # Check if this matches the error pattern
    if story == "No significant events to narrate.":
        print("⚠️  ERROR: Got fallback message - transcription failed")

        # Let's check if the file exists and has content
        print(f"File exists: {os.path.exists(temp_path)}")
        if os.path.exists(temp_path):
            with open(temp_path, "r") as f:
                file_content = f.read()
            print(f"File content length: {len(file_content)}")
            print(f"File content: {repr(file_content[:200])}")

            # Test the parsing directly on the file content
            try:
                events = chronicler._parse_campaign_log_content(file_content)
                print(f"Direct parsing found {len(events)} events")
            except Exception as e:
                print(f"Direct parsing failed: {e}")

except Exception as e:
    print(f"Exception occurred: {e}")
    import traceback

    traceback.print_exc()
finally:
    os.unlink(temp_path)
