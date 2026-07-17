"""Entry point and main workflow for the LinkedIn Post Generator AI Agent."""

import os
import sys
from dotenv import load_dotenv
from agent import LinkedInPostAgent, TranscriptError, PostGenerationError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# A publicly available YouTube video used for workflow testing.
# Replace with any valid video ID that has captions enabled.
TEST_VIDEO_ID = "xe4cTkq_il8"  # TED Talk: "The happy secret to better work"

SEPARATOR = "=" * 60
THIN_SEP   = "-" * 60


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def _step(number: int, message: str) -> None:
    print(f"\n[Step {number}] {message}")


def _ok(message: str) -> None:
    print(f"  ✔  {message}")


def _info(label: str, value: str) -> None:
    print(f"  {label:<18} {value}")


def _error(message: str) -> None:
    print(f"\n  ✘  ERROR: {message}", file=sys.stderr)


def _display_result(result: dict) -> None:
    """Pretty-print the structured result returned by the agent."""
    _header("GENERATED LINKEDIN POST")
    print()
    print(result["post"])
    print()
    print(THIN_SEP)
    _info("Video ID:",   result["video_id"])
    _info("Word count:", str(result["word_count"]))
    _info("Char count:", str(result["char_count"]))
    _info("Status:",     result["status"])
    print(THIN_SEP)


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

def _validate_env() -> None:
    """Ensure required environment variables are present before doing any work."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _error(
            "OPENAI_API_KEY is missing.\n"
            "  Copy .env.example to .env and add your key, then re-run."
        )
        sys.exit(1)
    _ok(f"OPENAI_API_KEY loaded ({len(api_key)} chars)")


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def run_workflow(video_id: str = TEST_VIDEO_ID) -> dict | None:
    """Execute the full LinkedIn post generation workflow.

    This is the standardized pipeline used by both the CLI entry point and
    the Gradio UI. It runs the following steps in order:

      1. Validate environment variables.
      2. Initialise the AI agent.
      3. Fetch the YouTube transcript.
      4. Run the agent to generate the LinkedIn post.
      5. Display and return the structured result.

    Args:
        video_id: YouTube video ID to process. Defaults to TEST_VIDEO_ID.

    Returns:
        The result dict from ``LinkedInPostAgent.run()`` on success, or
        ``None`` if the workflow failed.
    """
    _header("LinkedIn Post Generator — AI Agent Workflow")

    # Step 1 — environment
    _step(1, "Loading and validating environment variables...")
    _validate_env()

    # Step 2 — agent initialisation
    _step(2, "Initialising the AI agent...")
    try:
        agent = LinkedInPostAgent()
        _ok("Agent initialised (model: gpt-4o-mini, tools: generate_linkedin_post)")
    except EnvironmentError as e:
        _error(str(e))
        return None

    # Step 3 — transcript
    _step(3, f"Fetching YouTube transcript for video ID: '{video_id}'...")
    try:
        transcript = agent.fetch_transcript(video_id)
        preview = transcript[:120].replace("\n", " ")
        _ok(f"Transcript fetched ({len(transcript):,} characters)")
        print(f"  Preview: \"{preview}...\"")
    except TranscriptError as e:
        _error(str(e))
        return None

    # Step 4 — post generation
    _step(4, "Running the AI agent to generate the LinkedIn post...")
    print("  (This may take a few seconds while the model processes the transcript)")
    try:
        result = agent.run(video_id)
        _ok("Post generated successfully.")
    except (TranscriptError, PostGenerationError) as e:
        _error(str(e))
        return None
    except Exception as e:
        _error(f"Unexpected error: {e}")
        return None

    # Step 5 — display
    _step(5, "Displaying results...")
    _display_result(result)

    return result


def main():
    """CLI entry point — runs the workflow with the default test video."""
    result = run_workflow(TEST_VIDEO_ID)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()