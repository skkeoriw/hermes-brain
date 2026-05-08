#!/bin/bash
# Wrapper script for NotebookLM processing

set -e

YOUTUBE_LINKS_DIR="/home/zhouhuijuan1987/wiki/youtube-video-research-wiki/raw/youtube-links"
NOTEBOOKLM_PROCESSOR="/home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py"
OUTPUT_DIR="/tmp/notebooklm_output"

mkdir -p "$OUTPUT_DIR"

# Collect all YouTube URLs from changed files
URLS=()
for file in "$YOUTUBE_LINKS_DIR"/*.md; do
    if [ -f "$file" ]; then
        # Extract YouTube URLs (very basic regex)
        while IFS= read -r line; do
            if [[ $line =~ https://youtu(\.be|be\.com) ]]; then
                # Extract URL
                url=$(echo "$line" | grep -oE 'https://youtu[\.be]+\.com/watch\?v=[^[:space:]]+|https://youtu\.be/[^[:space:]]+' | head -1)
                if [ -n "$url" ]; then
                    URLS+=("$url")
                fi
            fi
        done < "$file"
    fi
done

# If no URLs found, exit with error
if [ ${#URLS[@]} -eq 0 ]; then
    echo '{"status": "error", "message": "No YouTube URLs found"}'
    exit 1
fi

# Call Python processor
python3 "$NOTEBOOKLM_PROCESSOR" "${URLS[@]}"
