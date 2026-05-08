#!/bin/bash
# Hermes YouTube Links Processor - Runs periodically to process queued YouTube links
# This bypasses the LLM orchestration layer and directly executes NotebookLM processing

# Note: NOT using 'set -e' because we want to continue on failures
trap 'echo "Script interrupted"' EXIT

WIKI_REPO="/home/zhouhuijuan1987/wiki/youtube-video-research-wiki"
YOUTUBE_LINKS_DIR="$WIKI_REPO/raw/youtube-links"
NOTEBOOKLM_PROCESSOR="/home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py"
ANALYSIS_DIR="$WIKI_REPO/raw/notebooklm-analysis"
MINDMAPS_DIR="$WIKI_REPO/raw/notebooklm-mindmaps"
LOG_DIR="$WIKI_REPO/logs"

# Create output directories
mkdir -p "$ANALYSIS_DIR" "$MINDMAPS_DIR" "$LOG_DIR"

# Extract all YouTube URLs from markdown files
extract_urls() {
    local file="$1"
    grep -o "https://[^[:space:]]*youtube\.[^[:space:]]*\|https://youtu\.be/[^[:space:]]*" "$file" 2>/dev/null || true
}

# Process a single YouTube link
process_youtube_link() {
    local url="$1"
    local log_file="$2"
    
    # Clean the URL - remove trailing whitespace and special chars
    url=$(echo "$url" | sed 's/[[:space:]]*$//' | sed 's/\\n$//' | tr -d '\r\n')
    
    # Validate URL format
    if [[ ! $url =~ https://youtu(\.be|be\.com) ]]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Skipping invalid URL: $url" >> "$log_file"
        return 0
    fi
    
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Processing: $url (Language: 中文/Chinese)" >> "$log_file"
    
    # Call Python processor with Chinese language setting
    if output=$(timeout 900 python3 "$NOTEBOOKLM_PROCESSOR" "$url" --language zh_Hans 2>&1); then
        status=$(echo "$output" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [ "$status" = "success" ]; then
            # Extract generated file paths
            report_path=$(echo "$output" | jq -r '.processed_urls[0].report_path // ""' 2>/dev/null || true)
            mindmap_path=$(echo "$output" | jq -r '.processed_urls[0].mindmap_path // ""' 2>/dev/null || true)
            
            # Move files to wiki directories
            if [ -n "$report_path" ] && [ -f "$report_path" ]; then
                filename=$(basename "$report_path")
                cp "$report_path" "$ANALYSIS_DIR/$filename"
                echo "  ✅ 报告: $filename (Chinese 中文)" >> "$log_file"
            fi
            
            if [ -n "$mindmap_path" ] && [ -f "$mindmap_path" ]; then
                filename=$(basename "$mindmap_path")
                cp "$mindmap_path" "$MINDMAPS_DIR/$filename"
                echo "  ✅ 脑图: $filename (中文)" >> "$log_file"
            fi
        else
            errors=$(echo "$output" | jq -r '.errors[]? // ""' 2>/dev/null | head -1 || true)
            echo "  ❌ 失败: $errors" >> "$log_file"
        fi
    else
        echo "  ❌ 处理器超时或错误" >> "$log_file"
    fi
    
    return 0
}

# Main logic
main() {
    cd "$WIKI_REPO"
    
    local run_id=$(date -u +%Y%m%dT%H%M%SZ)
    local log_file="$LOG_DIR/youtube-processor-${run_id}.log"
    
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] YouTube Links Processor started" > "$log_file"
    
    # Check for new/modified files in raw/youtube-links/
    if ! git diff --name-only HEAD > /tmp/changed_files.txt 2>/dev/null; then
        echo "  Note: git diff failed, checking file modification times" >> "$log_file"
    fi
    
    # Process each file in youtube-links directory
    local urls_processed=0
    local files_processed=0
    
    for file in "$YOUTUBE_LINKS_DIR"/*.md; do
        [ -f "$file" ] || continue
        
        filename=$(basename "$file")
        echo "  Processing file: $filename" >> "$log_file"
        
        # Extract URLs from file and process each one
        count=0
        extract_urls "$file" | while IFS= read -r url; do
            [ -z "$url" ] && continue
            process_youtube_link "$url" "$log_file"
            count=$((count + 1))
        done
        
        ((files_processed++))
    done
    
    # Commit generated files if any
    git add raw/notebooklm-*/ 2>/dev/null || true
    
    if ! git diff --cached --quiet 2>/dev/null; then
        if git commit -m "chore: add notebooklm analysis (auto-processor)" 2>&1 >> "$log_file"; then
            # Push to trigger next stage
            if git push origin main 2>&1 >> "$log_file"; then
                echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Successfully pushed video analyses" >> "$log_file"
            else
                echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Push failed" >> "$log_file"
            fi
        fi
    else
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] No new files generated" >> "$log_file"
    fi
    
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Completed" >> "$log_file"
}

main "$@"
