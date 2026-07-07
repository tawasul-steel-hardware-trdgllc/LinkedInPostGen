"""Gradio web interface for the LinkedIn Post Generator AI Agent."""

import re
import os
import gradio as gr
from dotenv import load_dotenv
from agent import LinkedInPostAgent, TranscriptError, PostGenerationError

load_dotenv()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YT_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})"
)


def _extract_video_id(raw: str) -> str:
    """Return a bare 11-char video ID from a URL or a plain ID string."""
    raw = raw.strip()
    match = _YT_ID_RE.search(raw)
    if match:
        return match.group(1)
    # Assume the user pasted a plain ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw
    return raw  # let the agent surface a meaningful error


def _build_custom_prompt(base_prompt: str, custom: str) -> str | None:
    """Merge optional custom instructions into the system prompt."""
    custom = (custom or "").strip()
    if not custom:
        return None
    return f"{base_prompt}\n\nAdditional instructions from the user:\n{custom}"


# ---------------------------------------------------------------------------
# Core generation function wired to the UI
# ---------------------------------------------------------------------------

def generate_post(video_input: str, custom_instructions: str):
    """Generate a LinkedIn post and return (post_text, status_message).

    Yields intermediate status updates so the UI can show a live loading
    message while the agent is working.
    """
    video_input = (video_input or "").strip()
    if not video_input:
        yield (
            "",
            _status("error", "Please enter a YouTube video URL or ID before generating."),
            gr.update(visible=False),
        )
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        yield (
            "",
            _status(
                "error",
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.",
            ),
            gr.update(visible=False),
        )
        return

    video_id = _extract_video_id(video_input)

    # --- loading state ---
    yield (
        "",
        _status("loading", "Fetching transcript and generating your LinkedIn post — this may take a few seconds…"),
        gr.update(visible=False),
    )

    try:
        agent = LinkedInPostAgent()
        result = agent.run(video_id)
        post = result["post"]
        meta = (
            f"✅ Post generated — "
            f"{result['word_count']} words · "
            f"{result['char_count']} characters"
        )
        yield post, _status("success", meta), gr.update(visible=True)

    except TranscriptError as e:
        yield "", _status("error", f"Could not fetch transcript: {e}"), gr.update(visible=False)
    except PostGenerationError as e:
        yield "", _status("error", f"Post generation failed: {e}"), gr.update(visible=False)
    except Exception as e:
        yield "", _status("error", f"Unexpected error: {e}"), gr.update(visible=False)


def _status(kind: str, message: str) -> str:
    """Return an HTML status badge."""
    colours = {
        "loading": ("#e8f4fd", "#1a73e8", "#1a73e8"),
        "success": ("#e6f4ea", "#137333", "#137333"),
        "error":   ("#fce8e6", "#c5221f", "#c5221f"),
    }
    icons = {"loading": "⏳", "success": "✅", "error": "❌"}
    bg, border, text = colours.get(kind, colours["error"])
    icon = icons.get(kind, "")
    return (
        f'<div style="background:{bg};border-left:4px solid {border};'
        f'color:{text};padding:12px 16px;border-radius:6px;'
        f'font-size:14px;margin-top:8px;">'
        f"{icon} {message}</div>"
    )


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
/* ── Global ── */
.gradio-container {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}

/* ── Hero header ── */
#hero {
    text-align: center;
    padding: 40px 24px 28px;
    background: linear-gradient(135deg, #0a66c2 0%, #004182 100%);
    border-radius: 16px;
    margin-bottom: 28px;
    color: #fff;
}
#hero h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 10px;
    letter-spacing: -0.5px;
}
#hero p {
    font-size: 1rem;
    opacity: 0.88;
    margin: 0;
    line-height: 1.6;
}

/* ── Cards ── */
.card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
}

/* ── Labels ── */
.gr-form label, label.svelte-1b6s6s {
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #1a1a1a !important;
}

/* ── Generate button ── */
#generate-btn {
    background: linear-gradient(135deg, #0a66c2, #004182) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    padding: 12px 28px !important;
    cursor: pointer !important;
    transition: opacity .2s;
    width: 100%;
}
#generate-btn:hover { opacity: .88 !important; }

/* ── Copy button ── */
#copy-btn {
    background: #f0f7ff !important;
    color: #0a66c2 !important;
    border: 1px solid #0a66c2 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
    cursor: pointer !important;
    transition: background .2s;
}
#copy-btn:hover { background: #dbeeff !important; }

/* ── Output text area ── */
#post-output textarea {
    font-size: 15px !important;
    line-height: 1.7 !important;
    color: #1a1a1a !important;
    border-radius: 8px !important;
    padding: 16px !important;
    background: #fafafa !important;
}

/* ── Hint text ── */
.hint {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}

/* ── Footer ── */
#footer {
    text-align: center;
    font-size: 12px;
    color: #999;
    padding: 16px 0 8px;
}
"""

# ---------------------------------------------------------------------------
# Copy-to-clipboard JS
# ---------------------------------------------------------------------------

COPY_JS = """
async () => {
    const ta = document.querySelector('#post-output textarea');
    if (!ta || !ta.value) return;
    try {
        await navigator.clipboard.writeText(ta.value);
        const btn = document.querySelector('#copy-btn');
        const orig = btn.textContent;
        btn.textContent = '✅ Copied!';
        setTimeout(() => { btn.textContent = orig; }, 2000);
    } catch(e) {
        console.error('Copy failed', e);
    }
}
"""


# ---------------------------------------------------------------------------
# Interface builder
# ---------------------------------------------------------------------------

def create_interface() -> gr.Blocks:
    """Create and return the Gradio Blocks interface."""

    with gr.Blocks(title="LinkedIn Post Generator") as demo:

        # ── Hero ──────────────────────────────────────────────────────────
        gr.HTML(
            '<div id="hero">'
            "<h1>🎥 LinkedIn Post Generator</h1>"
            "<p>Paste a YouTube video URL or ID and let the AI agent craft a"
            " polished, ready-to-publish LinkedIn post in seconds.</p>"
            "</div>"
        )

        # ── Input card ────────────────────────────────────────────────────
        with gr.Group(elem_classes="card"):
            gr.Markdown("### 📥 Video Input")

            video_input = gr.Textbox(
                label="YouTube Video URL or ID",
                placeholder="e.g. https://www.youtube.com/watch?v=Tia4am0tykE  or  Tia4am0tykE",
                lines=1,
                max_lines=1,
            )
            gr.HTML('<p class="hint">Paste the full YouTube URL or just the 11-character video ID. The video must have captions enabled.</p>')

            custom_instructions = gr.Textbox(
                label="Custom Instructions (optional)",
                placeholder="e.g. Focus on leadership lessons. Use a motivational tone. Keep it under 800 characters.",
                lines=3,
                max_lines=6,
            )
            gr.HTML('<p class="hint">Add any extra guidance for the AI — tone, focus area, length, audience, etc.</p>')

            generate_btn = gr.Button(
                "✨ Generate LinkedIn Post",
                elem_id="generate-btn",
                variant="primary",
            )

        # ── Status ────────────────────────────────────────────────────────
        status_html = gr.HTML(value="", visible=True)

        # ── Output card ───────────────────────────────────────────────────
        with gr.Group(elem_classes="card"):
            gr.Markdown("### 📝 Generated Post")

            post_output = gr.Textbox(
                label="",
                placeholder="Your LinkedIn post will appear here once generated…",
                lines=14,
                max_lines=30,
                interactive=True,
                elem_id="post-output",
            )

            copy_btn = gr.Button(
                "📋 Copy to Clipboard",
                elem_id="copy-btn",
                visible=False,
            )
            copy_btn.click(fn=None, js=COPY_JS)

        # ── Footer ────────────────────────────────────────────────────────
        gr.HTML(
            '<div id="footer">'
            "Built with Gradio · Powered by OpenAI gpt-4o-mini · "
            "Transcripts via youtube-transcript-api"
            "</div>"
        )

        # ── Wiring ────────────────────────────────────────────────────────
        generate_btn.click(
            fn=generate_post,
            inputs=[video_input, custom_instructions],
            outputs=[post_output, status_html, copy_btn],
        )

        # Allow pressing Enter in the video ID field to trigger generation
        video_input.submit(
            fn=generate_post,
            inputs=[video_input, custom_instructions],
            outputs=[post_output, status_html, copy_btn],
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = create_interface()
    app.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        show_error=True,
        css=CSS,
    )
