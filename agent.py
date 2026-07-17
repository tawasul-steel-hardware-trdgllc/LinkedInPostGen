"""AI Agent responsible for generating LinkedIn posts from YouTube transcripts."""

import os
import json

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError, AuthenticationError, RateLimitError
from requests import Session
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class TranscriptError(Exception):
    """Raised when a transcript cannot be fetched for any reason."""


class PostGenerationError(Exception):
    """Raised when LinkedIn post generation fails."""


# ---------------------------------------------------------------------------
# Tool definition exposed to the OpenAI agent
# ---------------------------------------------------------------------------

GENERATE_POST_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_linkedin_post",
        "description": (
            "Generate a professional LinkedIn post from a YouTube video transcript. "
            "The post includes a strong opening hook, 3-4 key insights, "
            "professional formatting, and relevant hashtags."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "The full transcript text of the YouTube video.",
                },
            },
            "required": ["transcript"],
        },
    },
}

# System prompt that shapes the post style
_SYSTEM_PROMPT = """\
You are an expert LinkedIn content creator. When given a video transcript, you produce
a single, ready-to-publish LinkedIn post that follows this exact structure:

1. HOOK (1-2 lines) — a bold, curiosity-driven opening that stops the scroll.
2. BLANK LINE
3. KEY INSIGHTS — exactly 3-4 bullet points (use the emoji ▶ as the bullet).
   Each insight is one concise sentence drawn directly from the transcript.
4. BLANK LINE
5. CLOSING LINE — one actionable takeaway or thought-provoking question.
6. BLANK LINE
7. HASHTAGS — 5-7 relevant hashtags on a single line.

Rules:
- Write in first-person, professional but conversational tone.
- No filler phrases like "In this video..." or "The speaker says...".
- Keep the total post under 1 300 characters (LinkedIn sweet spot).
- Output ONLY the post text — no explanations, no markdown code fences.
"""


# ---------------------------------------------------------------------------
# Helper: read config from Streamlit Secrets or environment variables
# ---------------------------------------------------------------------------

def _get_secret_or_env(key: str, default: str | None = None) -> str | None:
    """Get a config value from Streamlit Secrets first, then os.environ / .env.

    This allows the same code to work both on Streamlit Cloud (where secrets
    are set via the dashboard) and locally (where values come from the .env file).

    Handles TOML parsing: Streamlit Secrets uses TOML format where ``false``
    and ``true`` are parsed as Python booleans, so this function converts
    booleans back to their string representation.
    """
    try:
        import streamlit as st
        value = st.secrets.get(key)
        if value is None:
            value = os.getenv(key, default)
        elif isinstance(value, bool):
            value = "true" if value else "false"
        return value
    except Exception:
        return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Proxy-aware YouTubeTranscriptApi factory
# ---------------------------------------------------------------------------

def _create_youtube_transcript_api():
    """Create YouTubeTranscriptApi with optional ScraperAPI proxy settings.

    Reads the following environment variables (set them in .env or Streamlit Secrets):
      YOUTUBE_PROXY_HTTP    — http proxy URL (e.g.
                              http://scraperapi:KEY@proxy-server.scraperapi.com:8001)
      YOUTUBE_PROXY_HTTPS   — https proxy URL (same format)
      YOUTUBE_VERIFY_SSL    — set to "false" to disable SSL verification (default "true")
    """
    http_proxy = _get_secret_or_env("YOUTUBE_PROXY_HTTP")
    https_proxy = _get_secret_or_env("YOUTUBE_PROXY_HTTPS")
    verify_ssl = _get_secret_or_env("YOUTUBE_VERIFY_SSL", "true").lower() != "false"

    http_client = Session()

    # On Windows, Python often can't find the system's CA certificates.
    # Use certifi to provide a known-good CA bundle when verification is enabled.
    if verify_ssl:
        try:
            import certifi
            http_client.verify = certifi.where()
        except ImportError:
            pass  # fall back to default behaviour
    else:
        # Disable SSL verification (handles Windows cert store issues)
        http_client.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    proxies = {}
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy

    if proxies:
        http_client.proxies.update(proxies)

    return YouTubeTranscriptApi(http_client=http_client)


class LinkedInPostAgent:
    """Agent that uses OpenAI to generate LinkedIn posts from YouTube video transcripts."""

    def __init__(self):
        """Initialize the agent, loading the OpenAI API key from the environment."""
        api_key = _get_secret_or_env("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )
        self.client = OpenAI(api_key=api_key)
        self.tools = [GENERATE_POST_TOOL]

    def fetch_transcript(self, video_id: str) -> str:
        """Fetch the full transcript for a YouTube video.

        Uses ScraperAPI proxy settings from environment variables if configured,
        so the app works reliably in regions where direct YouTube access is restricted.

        Args:
            video_id: The YouTube video ID (e.g. 'dQw4w9WgXcQ').

        Returns:
            The full transcript as a single string of text.

        Raises:
            TranscriptError: If the transcript is unavailable for any reason.
        """
        try:
            api = _create_youtube_transcript_api()
            transcript = api.fetch(video_id)
            return " ".join(entry.text for entry in transcript)

        except TranscriptsDisabled:
            raise TranscriptError(
                f"Transcripts are disabled for video '{video_id}'. "
                "The video owner has turned off captions."
            )
        except NoTranscriptFound:
            raise TranscriptError(
                f"No transcript found for video '{video_id}'. "
                "Try a different language or check if captions exist."
            )
        except VideoUnavailable:
            raise TranscriptError(
                f"Video '{video_id}' is unavailable. "
                "It may be private, deleted, or region-restricted."
            )
        except Exception as e:
            raise TranscriptError(
                f"An unexpected error occurred while fetching the transcript: {e}"
            ) from e

    def generate_post(self, transcript: str) -> str:
        """Generate a professional LinkedIn post from a video transcript.

        This method is registered as an OpenAI tool (see GENERATE_POST_TOOL) so
        the agent can invoke it autonomously during a tool-use loop.

        Args:
            transcript: The full transcript text of the YouTube video.

        Returns:
            A ready-to-publish LinkedIn post as a plain string.

        Raises:
            PostGenerationError: If the OpenAI call fails for any reason.
        """
        if not transcript or not transcript.strip():
            raise PostGenerationError("Transcript is empty — cannot generate a post.")

        # Truncate to ~12 000 chars to stay within model context limits
        truncated = transcript[:12_000]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Here is the video transcript. "
                            "Generate the LinkedIn post now:\n\n"
                            + truncated
                        ),
                    },
                ],
                temperature=0.7,
                max_tokens=1200,
            )
            post = response.choices[0].message.content
            if not post:
                raise PostGenerationError(
                    f"OpenAI returned an empty response. "
                    f"Finish reason: {response.choices[0].finish_reason}"
                )
            return post.strip()

        except AuthenticationError:
            raise PostGenerationError(
                "Invalid OpenAI API key. Check the OPENAI_API_KEY value in your .env file."
            )
        except RateLimitError:
            raise PostGenerationError(
                "OpenAI rate limit reached. Wait a moment and try again."
            )
        except OpenAIError as e:
            raise PostGenerationError(
                f"OpenAI API error while generating the post: {e}"
            ) from e
        except Exception as e:
            raise PostGenerationError(
                f"Unexpected error during post generation: {e}"
            ) from e

    def _handle_tool_call(self, tool_name: str, tool_args: dict) -> str:
        """Dispatch a tool call requested by the OpenAI agent.

        Args:
            tool_name: Name of the tool the model wants to invoke.
            tool_args:  Parsed JSON arguments for that tool.

        Returns:
            The tool result as a string to feed back to the model.
        """
        if tool_name == "generate_linkedin_post":
            return self.generate_post(tool_args["transcript"])
        raise PostGenerationError(f"Unknown tool requested by agent: '{tool_name}'")

    def run(self, video_id: str) -> dict:
        """Run the full agent pipeline for a given YouTube video ID.

        This method:
          1. Fetches the YouTube video transcript.
          2. Uses OpenAI to generate a LinkedIn post from the transcript.
          3. Returns the formatted result.

        Args:
            video_id: The YouTube video ID to process.

        Returns:
            A dict with the following keys:
              - ``post``        (str)  : The finished LinkedIn post.
              - ``video_id``    (str)  : The video ID that was processed.
              - ``word_count``  (int)  : Approximate word count of the post.
              - ``char_count``  (int)  : Character count of the post.
              - ``status``      (str)  : "success" or "error".
              - ``error``       (str | None): Error message when status is "error".

        Raises:
            TranscriptError: If the transcript cannot be fetched.
            PostGenerationError: If post generation fails.
        """
        # --- Step 1: fetch transcript ---
        transcript = self.fetch_transcript(video_id)
        
        # Validate transcript has enough content
        if not transcript or not transcript.strip():
            raise PostGenerationError(
                "Transcript fetched but is empty. The video may have no captions or the transcript could not be retrieved."
            )
        
        print(f"[INFO] Transcript fetched: {len(transcript)} characters, {len(transcript.split())} words")

        # --- Step 2: generate post directly ---
        # Use the generate_post method which handles the OpenAI call directly
        # This is more reliable than using a tool-use agent loop
        post = self.generate_post(transcript)
        
        return self._format_result(video_id, post)

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _format_result(video_id: str, post: str) -> dict:
        """Package the finished post into a clean, structured result dict."""
        return {
            "status": "success",
            "video_id": video_id,
            "post": post,
            "word_count": len(post.split()),
            "char_count": len(post),
            "error": None,
        }