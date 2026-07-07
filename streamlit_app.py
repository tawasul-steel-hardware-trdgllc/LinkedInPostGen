"""Streamlit interface for the LinkedIn Post Generator AI Agent."""

import re
import os
import streamlit as st
from agent import LinkedInPostAgent, TranscriptError, PostGenerationError

# Page configuration
st.set_page_config(
    page_title="LinkedIn Post Generator",
    page_icon="🎥",
    layout="centered",
)

# Custom CSS (matching your Gradio styling)
st.markdown("""
<style>
    .main > div {max-width: 860px;}
    .stButton>button {
        background: linear-gradient(135deg, #0a66c2, #004182);
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 12px 28px;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
    }
    .loading-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align: center; padding: 40px 24px 28px; background: linear-gradient(135deg, #0a66c2 0%, #004182 100%); border-radius: 16px; margin-bottom: 28px; color: white;">
    <h1 style="margin: 0;">🎥 LinkedIn Post Generator</h1>
    <p style="margin: 10px 0 0; opacity: 0.9;">Paste a YouTube video URL or ID and let the AI agent craft a polished, ready-to-publish LinkedIn post in seconds.</p>
</div>
""", unsafe_allow_html=True)

# Helper function
def extract_video_id(raw: str) -> str:
    """Extract YouTube video ID from URL or return plain ID."""
    raw = raw.strip()
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", raw)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw
    return raw

# Sidebar - API Key Configuration
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key input (for development/testing)
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Enter your OpenAI API key. For production, use Streamlit Secrets.",
        value=os.getenv("OPENAI_API_KEY", "")
    )
    
    st.markdown("---")
    st.markdown("**How to use:**")
    st.markdown("""
    1. Paste a YouTube video URL or ID
    2. (Optional) Add custom instructions
    3. Click "Generate LinkedIn Post"
    """)

# Main content
st.markdown("### 📥 Video Input")

col1, col2 = st.columns([3, 1])
with col1:
    video_input = st.text_input(
        "YouTube Video URL or ID",
        placeholder="e.g. https://www.youtube.com/watch?v=Tia4am0tykE",
        label_visibility="collapsed"
    )
with col2:
    st.markdown("<div style='padding-top: 10px; font-size: 12px; color: #666;'>Must have captions enabled</div>", unsafe_allow_html=True)

# Custom instructions
custom_instructions = st.text_area(
    "Custom Instructions (optional)",
    placeholder="e.g. Focus on leadership lessons. Use a motivational tone. Keep it under 800 characters.",
    height=100
)

# Generate button
if st.button("✨ Generate LinkedIn Post", type="primary", use_container_width=True):
    if not video_input:
        st.error("Please enter a YouTube video URL or ID.")
        st.stop()
    
    # Get API key - prioritize Streamlit Secrets, then sidebar input, then env var
    api_key = None
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        api_key = api_key_input if api_key_input else os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        st.error("""
        🔑 **API Key Missing**
        
        Please add your OpenAI API key in one of these ways:
        1. **Streamlit Secrets** (recommended for deployment) - Add in Streamlit Cloud dashboard
        2. **Sidebar** - Enter in the settings panel on the left
        3. **.env file** (for local development only)
        """)
        st.stop()
    
    # Set environment variable for the agent
    os.environ["OPENAI_API_KEY"] = api_key
    
    video_id = extract_video_id(video_input)
    
    # Status container
    status_container = st.empty()
    output_container = st.empty()
    copy_container = st.empty()
    
    with st.spinner("⏳ Fetching transcript and generating your LinkedIn post..."):
        try:
            agent = LinkedInPostAgent()
            result = agent.run(video_id)
            post = result["post"]
            
            # Success message
            status_container.markdown(f"""
            <div class="success-box">
                ✅ Post generated — {result['word_count']} words · {result['char_count']} characters
            </div>
            """, unsafe_allow_html=True)
            
            # Display the post
            output_container.text_area(
                "Generated LinkedIn Post",
                value=post,
                height=400,
                key="post_output"
            )
            
            # Copy button
            copy_container.download_button(
                label="📋 Copy to Clipboard",
                data=post,
                file_name="linkedin_post.txt",
                mime="text/plain"
            )
            
        except TranscriptError as e:
            status_container.markdown(f"""
            <div class="error-box">
                ❌ Could not fetch transcript: {e}
            </div>
            """, unsafe_allow_html=True)
        except PostGenerationError as e:
            status_container.markdown(f"""
            <div class="error-box">
                ❌ Post generation failed: {e}
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            status_container.markdown(f"""
            <div class="error-box">
                ❌ Unexpected error: {e}
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 12px; color: #999; padding: 16px 0 8px;'>"
    "Built with Streamlit · Powered by OpenAI gpt-4o-mini · Transcripts via youtube-transcript-api"
    "</div>",
    unsafe_allow_html=True
)