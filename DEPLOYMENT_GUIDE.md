# Deployment Guide: GitHub & Streamlit Community Cloud

This guide walks you through uploading your LinkedIn Post Generator to GitHub and deploying it on Streamlit Community Cloud, while keeping your API keys secure.

---

## ⚠️ Important: Your Project Currently Uses Gradio

Your current project uses **Gradio** for the web interface. Streamlit Community Cloud requires a **Streamlit** app. You have two options:

### Option A: Convert to Streamlit (Recommended for Streamlit Deployment)
Create a Streamlit version of your app. The core logic in `agent.py` can be reused — only the UI layer needs to change.

### Option B: Use Alternative Hosting for Gradio
If you want to keep using Gradio, consider:
- **Hugging Face Spaces** (supports Gradio natively)
- **Gradio Cloud** (share.gradio.app)

---

## Part 1: Convert Your App to Streamlit

### Step 1.1: Create `streamlit_app.py`

Create a new file `streamlit_app.py` with the Streamlit interface. Here's a template based on your existing Gradio UI:

```python
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
```

### Step 1.2: Update `requirements.txt`

Make sure your `requirements.txt` includes Streamlit:

```txt
streamlit
openai
youtube-transcript-api
python-dotenv
requests
```

---

## Part 2: Prepare for GitHub Upload

### Step 2.1: Verify `.gitignore`

Your `.gitignore` already includes `.env` — this is crucial! It prevents your API keys from being uploaded to GitHub.

```gitignore
# Environment variables
.env
```

### Step 2.2: Keep `.env.example` (Already Exists)

The `.env.example` file is safe to upload because it only contains placeholder values, not real keys.

### Step 2.3: Files to Upload to GitHub

Your repository should include:
- `streamlit_app.py` (your new Streamlit app)
- `agent.py` (core logic - safe to share)
- `requirements.txt` (dependencies)
- `.env.example` (template)
- `.gitignore`
- `README.md`

**NEVER upload:**
- `.env` (contains real API keys)
- Any file with actual credentials

---

## Part 3: Upload to GitHub

### Step 3.1: Create a New Repository on GitHub

1. Go to [github.com](https://github.com) and sign in
2. Click the **+** button (top right) → **New repository**
3. Name your repository (e.g., `linkedin-post-generator`)
4. Choose **Public** or **Private** (Private is more secure)
5. **Do NOT** initialize with README, .gitignore, or license (you already have these)
6. Click **Create repository**

### Step 3.2: Upload Your Files

#### Option A: Using Git Command Line (Recommended)

```bash
# Navigate to your project folder
cd c:\Users\moiz1\createposts

# Initialize git (if not already done)
git init

# Add all files (gitignore will exclude .env)
git add .

# Commit
git commit -m "Initial commit: LinkedIn Post Generator with Streamlit"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/linkedin-post-generator.git

# Push to GitHub
git push -u origin main
```

#### Option B: Using GitHub Website

1. On your repository page, click **uploading an existing file**
2. Drag and drop these files:
   - `streamlit_app.py`
   - `agent.py`
   - `requirements.txt`
   - `.env.example`
   - `.gitignore`
   - `README.md`
3. Click **Commit changes**

### Step 3.3: Verify Upload

Visit your GitHub repository and confirm:
- ✅ All files are present
- ✅ `.env` file is NOT present (check `.gitignore` is working)
- ✅ `requirements.txt` includes `streamlit`

---

## Part 4: Deploy to Streamlit Community Cloud

### Step 4.1: Go to Streamlit Community Cloud

1. Open [share.streamlit.io](https://share.streamlit.io)
2. Click **Sign up** or **Sign in** with GitHub
3. Authorize Streamlit to access your GitHub account

### Step 4.2: Create New App

1. Click **New app** (or **Deploy** button)
2. Fill in the deployment form:

   | Field | Value |
   |-------|-------|
   | **Repository** | Select your repository (e.g., `linkedin-post-generator`) |
   | **Branch** | `main` (or `master`) |
   | **Main file path** | `streamlit_app.py` |

3. Click **Deploy!**

### Step 4.3: Wait for Deployment

Streamlit will:
1. Clone your repository
2. Install dependencies from `requirements.txt`
3. Run `streamlit run streamlit_app.py`

This takes 2-5 minutes. You'll see a progress log.

---

## Part 5: Configure API Keys with Streamlit Secrets

### Step 5.1: Access App Settings

1. After deployment, click your app name to open it
2. Click the **⋮** (three dots) menu in the top right
3. Select **Settings**

### Step 5.2: Add Secrets

1. Scroll to the **Secrets** section
2. Click **Add secret** (or edit existing secrets)
3. Paste this template:

```toml
# OpenAI API Key
OPENAI_API_KEY = "sk-proj-YOUR_ACTUAL_API_KEY_HERE"
```

4. **Replace** `sk-proj-YOUR_ACTUAL_API_KEY_HERE` with your real OpenAI API key
5. Click **Save**

### Step 5.3: How Secrets Work

In your `streamlit_app.py`, the code reads the secret like this:

```python
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    # Fallback to other methods
    pass
```

The API key is:
- ✅ Stored securely on Streamlit's servers
- ✅ Never exposed in your GitHub code
- ✅ Automatically available to your deployed app
- ✅ Not visible to app users

---

## Part 6: Test Your Deployed App

### Step 6.1: Open Your Public URL

Streamlit provides a public URL like:
```
https://yourusername-linkedin-post-generator-streamlit-app-abc123.streamlit.app
```

### Step 6.2: Test the App

1. Open the URL in a browser
2. Paste a YouTube video URL (e.g., `https://www.youtube.com/watch?v=Tia4am0tykE`)
3. (Optional) Add custom instructions
4. Click **Generate LinkedIn Post**
5. Verify:
   - ✅ App loads without errors
   - ✅ Transcript is fetched
   - ✅ Post is generated
   - ✅ No API keys are visible in the UI
   - ✅ Copy button works

### Step 6.3: Check Deployment Logs

If something fails:
1. Go to your Streamlit dashboard
2. Click on your app
3. Click **Logs** to see deployment output
4. Look for errors related to:
   - Missing packages
   - API key issues
   - Import errors

---

## Troubleshooting Common Issues

### Issue 1: `ModuleNotFoundError: No module named 'streamlit'`

**Cause:** `streamlit` missing from `requirements.txt`

**Fix:** Add `streamlit` to `requirements.txt` and push to GitHub:
```bash
echo "streamlit" >> requirements.txt
git add requirements.txt
git commit -m "Add streamlit to requirements"
git push
```

### Issue 2: `KeyError: 'OPENAI_API_KEY'`

**Cause:** API key not configured in Streamlit Secrets

**Fix:**
1. Go to Streamlit dashboard → Settings → Secrets
2. Add:
```toml
OPENAI_API_KEY = "your-real-api-key"
```
3. Save and restart the app

### Issue 3: App Deploys But Shows Blank Page

**Cause:** The main file path is incorrect or the app has a startup error

**Fix:**
1. Check the deployment logs in Streamlit dashboard
2. Verify your main file is named `streamlit_app.py`
3. Ensure there are no syntax errors in the file

### Issue 4: "This app is using a deprecated version" Warning

**Cause:** Using old Streamlit syntax

**Fix:** Update your code to use modern Streamlit patterns (the template above uses current syntax)

### Issue 5: API Calls Fail with Authentication Error

**Cause:** Invalid or expired API key

**Fix:**
1. Test your API key locally first
2. Ensure there are no extra spaces in the secret value
3. Regenerate your OpenAI API key if needed

---

## Security Best Practices

### ✅ DO:
- Use Streamlit Secrets for all API keys
- Keep `.env` in `.gitignore`
- Use a private GitHub repository if possible
- Regularly rotate your API keys
- Monitor your OpenAI usage dashboard

### ❌ DON'T:
- Hardcode API keys in Python files
- Commit `.env` files to GitHub
- Share your API keys in public repositories
- Use the same API key across multiple projects
- Store API keys in client-side code

---

## Alternative: Local Development with `.env`

For local testing (not deployed), you can still use the `.env` file:

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and add your real API key:
```
OPENAI_API_KEY=sk-proj-your-real-key-here
```

3. Run locally:
```bash
streamlit run streamlit_app.py
```

The app will automatically load the key from the `.env` file.

---

## Summary Checklist

Before deploying, ensure:

- [ ] Created `streamlit_app.py` with Streamlit interface
- [ ] Updated `requirements.txt` to include `streamlit`
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` exists (safe to share)
- [ ] Uploaded files to GitHub (NOT including `.env`)
- [ ] Created Streamlit Community Cloud account
- [ ] Deployed app pointing to `streamlit_app.py`
- [ ] Added `OPENAI_API_KEY` in Streamlit Secrets
- [ ] Tested the deployed app
- [ ] Verified no API keys are visible in the UI

---

## Additional Resources

- [Streamlit Community Cloud Documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/library/advanced-features/secrets-management)
- [OpenAI API Key Best Practices](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
- [GitHub Security: Protecting Your Repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure)

---

## Need Help?

If you encounter issues:

1. Check the Streamlit deployment logs
2. Review the troubleshooting section above
3. Test locally first with `streamlit run streamlit_app.py`
4. Ensure your OpenAI API key is valid and has credits

Good luck with your deployment! 🚀