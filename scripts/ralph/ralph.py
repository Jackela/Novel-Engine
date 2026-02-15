#!/usr/bin/env python3
"""
Ralph for Windows - Python version
Autonomous AI agent loop that works around Claude Code --print bugs on Windows.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PRD_FILE = SCRIPT_DIR / "prd.json"
PROGRESS_FILE = SCRIPT_DIR / "progress.txt"
CLAUDE_MD = SCRIPT_DIR / "CLAUDE.md"


def log(message: str) -> None:
    """Print log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def load_prd() -> dict:
    """Load the PRD JSON file."""
    with open(PRD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_prd(prd: dict) -> None:
    """Save the PRD JSON file."""
    with open(PRD_FILE, "w", encoding="utf-8") as f:
        json.dump(prd, f, indent=2, ensure_ascii=False)


def get_next_story(prd: dict) -> dict | None:
    """Get the highest priority story with passes: false."""
    stories = prd.get("userStories", [])
    # Filter stories that are not passed
    available = [s for s in stories if not s.get("passes", False)]
    if not available:
        return None
    # Sort by priority (lower number = higher priority)
    available.sort(key=lambda s: s.get("priority", 999))
    return available[0]


def run_claude_iteration() -> bool:
    """
    Run Claude Code with the CLAUDE.md prompt.

    Returns True if iteration completed, False if it hung/timed out.
    """
    log("Starting Claude Code iteration...")

    # Read CLAUDE.md content
    with open(CLAUDE_MD, "r", encoding="utf-8") as f:
        prompt_content = f.read()

    # On Windows, we use a different approach to avoid the --print hang bug
    # Instead of piping input, we write to a temp file and use --print with explicit exit

    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(prompt_content)
        tmp_path = tmp.name

    try:
        # Build the claude command
        # Note: Using --print with explicit timeout to avoid hanging
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--print",
            "--no-session-persistence",  # Don't save session
        ]

        # Run with the temp file as stdin
        with open(tmp_path, "r") as stdin_file:
            result = subprocess.run(
                cmd,
                stdin=stdin_file,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per iteration
            )

        output = result.stdout + result.stderr

        # Check for completion signal
        if "<promise>COMPLETE</promise>" in output:
            log("✅ All tasks completed!")
            return True

        # Check for successful completion
        if result.returncode == 0 or "feat:" in output:
            log("✅ Iteration completed successfully")
            return True

        log(f"⚠️  Claude exit code: {result.returncode}")
        return True  # Continue even if non-zero exit

    except subprocess.TimeoutExpired:
        log("⏱️  Claude timed out (this is a known Windows bug)")
        log("   The story may have been completed - checking PRD...")
        return True  # Assume completion and check PRD

    except Exception as e:
        log(f"❌ Error running Claude: {e}")
        return False

    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink()
        except:
            pass


def check_and_commit(prd: dict) -> None:
    """Check if there are changes to commit."""
    import subprocess

    # Run git status
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR.parent.parent,
    )

    if result.stdout.strip():
        log("📝 Changes detected - you may want to commit manually")
    else:
        log("✅ No changes to commit")


def main():
    """Main Ralph loop."""
    if len(sys.argv) > 1:
        try:
            max_iterations = int(sys.argv[1])
        except ValueError:
            max_iterations = 10
    else:
        max_iterations = 10

    log(f"🚀 Starting Ralph (Python version) - Max iterations: {max_iterations}")
    log(f"   PRD: {PRD_FILE}")
    log(f"   Branch: {Path('.git').exists() and 'git repo detected' or 'no git'}")

    for iteration in range(1, max_iterations + 1):
        log(f"\n{'='*60}")
        log(f"  Iteration {iteration}/{max_iterations}")
        log(f"{'='*60}")

        # Load PRD and check next story
        prd = load_prd()
        next_story = get_next_story(prd)

        if next_story is None:
            log("🎉 All stories passed! Ralph complete.")
            break

        log(f"📋 Next story: {next_story['id']} - {next_story['title']}")

        # Run Claude Code
        run_claude_iteration()

        # Reload PRD and check if story was completed
        prd_after = load_prd()
        story_after = next(
            (
                s
                for s in prd_after.get("userStories", [])
                if s["id"] == next_story["id"]
            ),
            None,
        )

        if story_after and story_after.get("passes", False):
            log(f"✅ {next_story['id']} marked as complete!")
        else:
            log(f"⚠️  {next_story['id']} still not passed - may need manual review")

        # Check for git changes
        check_and_commit(prd_after)

        log("⏳ Waiting 2 seconds before next iteration...")
        import time

        time.sleep(2)

    log("\n🏁 Ralph loop finished")


if __name__ == "__main__":
    main()
