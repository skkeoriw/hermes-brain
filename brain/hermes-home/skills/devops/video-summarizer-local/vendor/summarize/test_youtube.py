from youtube_transcript_api import YouTubeTranscriptApi
import re
import sys

url = "https://www.youtube.com/watch?v=S6XCelOhZ6w"
video_id = re.search(r'(?:watch\?v=|/videos/|embed/|youtu.be/|/v/)([-\w]{11})', url)

if video_id:
    video_id = video_id.group(1)
    print(f"Video ID: {video_id}")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(f"✓ 字幕已获取，共 {len(transcript)} 条")
        print("\n前100个字符:")
        print(" ".join([t['text'] for t in transcript[:10]]))
    except Exception as e:
        print(f"✗ 获取失败: {str(e)}")
        sys.exit(1)
