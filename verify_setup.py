"""Run this script to verify all required packages are installed correctly."""

import importlib
import sys

REQUIRED_PACKAGES = {
    "openai": "openai",
    "youtube_transcript_api": "youtube-transcript-api",
    "gradio": "gradio",
    "dotenv": "python-dotenv",
    "requests": "requests",
}


def verify():
    all_ok = True
    print(f"Python version: {sys.version}\n")
    print("Checking required packages...")
    print("-" * 40)

    for module, package in REQUIRED_PACKAGES.items():
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, "__version__", "unknown")
            print(f"  [OK] {package} (version: {version})")
        except ImportError:
            print(f"  [MISSING] {package} — run: pip install {package}")
            all_ok = False

    print("-" * 40)
    if all_ok:
        print("\nAll packages installed successfully. You're ready to build!")
    else:
        print("\nSome packages are missing. Install them with:")
        print("  pip install -r requirements.txt")


if __name__ == "__main__":
    verify()
