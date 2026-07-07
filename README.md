# CreatePosts — LinkedIn Post Generator AI Agent

An AI Agent that generates LinkedIn posts from YouTube videos using OpenAI, `youtube-transcript-api`, and a Gradio web interface.

## Project Structure

```
createpost/
├── main.py            # Entry point — launches the app
├── agent.py           # AI Agent logic (transcript fetch + post generation)
├── ui.py              # Gradio web interface
├── verify_setup.py    # Setup verification script
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
└── .gitignore
```

## Setup

**1. Clone the repository**
```bash
git clone https://gitlab.com/individual-group8085827/createposts.git
cd createposts
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

**5. Verify the setup**
```bash
python verify_setup.py
```

## Run the app

```bash
python main.py
```

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | Interact with OpenAI AI models |
| `youtube-transcript-api` | Fetch transcripts from YouTube videos |
| `gradio` | Build the web interface |
| `python-dotenv` | Load environment variables from `.env` |
| `requests` | HTTP utility |
