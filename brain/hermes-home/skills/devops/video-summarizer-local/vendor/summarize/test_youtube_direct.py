#!/usr/bin/env python3
"""Direct YouTube transcript test - bypasses audio processing"""

import os
import sys
import re
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from summarizer.transcription import extract_youtube_id, get_youtube_transcript
from summarizer.summarizer import Summarizer
from summarizer.config_file import ConfigFile

def test_youtube_summarize():
    """Test YouTube transcript and summarization with OpenRouter"""
    
    url = "https://www.youtube.com/watch?v=S6XCelOhZ6w"
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set in environment")
        return False
    
    print(f"🎬 Testing: {url}")
    print(f"🔑 Using API key: {api_key[:20]}...")
    
    try:
        # Step 1: Extract video ID
        print("\n[1] Extracting video ID...")
        video_id = extract_youtube_id(url)
        print(f"    ✓ Video ID: {video_id}")
        
        # Step 2: Get YouTube transcript
        print("\n[2] Fetching YouTube transcript...")
        transcript = get_youtube_transcript(video_id, verbose=True)
        print(f"    ✓ Transcript length: {len(transcript)} chars")
        print(f"    Preview: {transcript[:200]}...")
        
        # Step 3: Summarize
        print("\n[3] Summarizing with OpenRouter...")
        
        # Load config
        config = ConfigFile()
        
        # Create summarizer
        summarizer = Summarizer(
            provider="openrouter",
            api_key=api_key,
            prompt_type="Distill Wisdom"
        )
        
        summary = summarizer.summarize(transcript)
        print(f"    ✓ Summary generated!")
        print(f"\n{'='*60}")
        print(summary)
        print(f"{'='*60}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_youtube_summarize()
    sys.exit(0 if success else 1)
