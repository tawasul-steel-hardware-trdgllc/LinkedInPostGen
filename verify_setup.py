"""Run this script to verify all required packages are installed correctly."""

import importlib
import sys
import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED_PACKAGES = {
    "openai": "openai",
    "youtube_transcript_api": "youtube-transcript-api",
    "gradio": "gradio",
    "dotenv": "python-dotenv",
    "requests": "requests",
}

ENV_VARS_TO_CHECK = [
    "OPENAI_API_KEY",
    "YOUTUBE_PROXY_HTTP",
    "YOUTUBE_PROXY_HTTPS",
    "YOUTUBE_VERIFY_SSL",
]


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

    print("\nChecking environment variables...")
    print("-" * 40)
    for var in ENV_VARS_TO_CHECK:
        value = os.getenv(var)
        if value:
            if var == "OPENAI_API_KEY":
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "[set]"
                print(f"  [OK] {var}={masked}")
            else:
                print(f"  [OK] {var}={value[:60]}")
        else:
            print(f"  [  ] {var} — not set (optional for proxy, required for API key)")
            if var == "OPENAI_API_KEY":
                all_ok = False

    print("-" * 40)

    # Test proxy-aware YouTubeTranscriptApi creation
    print("\nTesting proxy-aware YouTubeTranscriptApi creation...")
    from requests import Session
    from youtube_transcript_api import YouTubeTranscriptApi

    http_client = Session()
    http_proxy = os.getenv("YOUTUBE_PROXY_HTTP")
    https_proxy = os.getenv("YOUTUBE_PROXY_HTTPS")
    verify_ssl = os.getenv("YOUTUBE_VERIFY_SSL", "true").lower() != "false"
    http_client.verify = verify_ssl

    proxies = {}
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    if proxies:
        http_client.proxies.update(proxies)

    try:
        api = YouTubeTranscriptApi(http_client=http_client)
        print(f"  [OK] YouTubeTranscriptApi created with Session (verify_ssl={verify_ssl})")
        if proxies:
            print(f"  [OK] Proxies configured: {', '.join(proxies.keys())}")
        else:
            print("  [  ] No proxies configured — using direct connection")
    except Exception as e:
        print(f"  [WARN] YouTubeTranscriptApi creation triggered unexpected issue: {e}")

    print("-" * 40)
    if all_ok:
        print("\n✅ All packages installed and required env vars set. You're ready to build!")
    else:
        print("\n⚠️  Some checks failed. Review the messages above.")


if __name__ == "__main__":
    verify()