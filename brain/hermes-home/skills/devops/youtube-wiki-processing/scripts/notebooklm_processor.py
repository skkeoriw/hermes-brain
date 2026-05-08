#!/usr/bin/env python3
"""
NotebookLM Processor for YouTube URLs
Processes YouTube URLs via notebooklm-cli to generate reports and mindmaps.
"""

import json
import sys
import subprocess
import os
from pathlib import Path

def run_notebooklm_cmd(cmd_args):
    """Run a notebooklm command and return parsed JSON output."""
    result = subprocess.run(
        ['notebooklm'] + cmd_args,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error running notebooklm {' '.join(cmd_args)}: {result.stderr}", 
              file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON output: {result.stdout}", file=sys.stderr)
        return None

def process_youtube_url(url, notebook_id):
    """Process a single YouTube URL: add source, wait, generate report and mindmap."""
    print(f"Processing URL: {url}")
    
    # Add YouTube source
    add_result = run_notebooklm_cmd(['source', 'add', url, '--json'])
    if not add_result:
        return None
    source_id = add_result.get('source', {}).get('id')
    if not source_id:
        print(f"Failed to get source ID for {url}", file=sys.stderr)
        return None
    
    # Wait for source processing
    wait_result = subprocess.run(
        ['notebooklm', 'source', 'wait', source_id, '-n', notebook_id],
        capture_output=True,
        text=True
    )
    if wait_result.returncode != 0:
        print(f"Source wait failed for {url}: {wait_result.stderr}", file=sys.stderr)
        return None
    
    # Generate report
    report_result = run_notebooklm_cmd([
        'generate', 'report', 
        '--format', 'study-guide',
        '--notebook', notebook_id
    ])
    if not report_result:
        return None
    report_task_id = report_result.get('task_id')
    
    # Generate mindmap
    mindmap_result = run_notebooklm_cmd([
        'generate', 'mind-map',
        '--notebook', notebook_id
    ])
    if not mindmap_result:
        return None
    mindmap_task_id = mindmap_result.get('task_id')
    
    return {
        'source_id': source_id,
        'report_task_id': report_task_id,
        'mindmap_task_id': mindmap_task_id
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: notebooklm_processor.py <youtube_url> [youtube_url...]", file=sys.stderr)
        sys.exit(1)
    
    urls = sys.argv[1:]
    
    # Create notebook for this batch
    notebook_title = f"YouTube Analysis {len(urls)} videos"
    create_result = run_notebooklm_cmd(['create', notebook_title, '--json'])
    if not create_result:
        sys.exit(1)
    notebook_id = create_result.get('notebook', {}).get('id')
    if not notebook_id:
        print("Failed to create notebook", file=sys.stderr)
        sys.exit(1)
    
    print(f"Created notebook: {notebook_id}")
    
    results = []
    for url in urls:
        result = process_youtube_url(url, notebook_id)
        if result:
            results.append(result)
    
    # Wait for all generation tasks to complete (simplified - in reality would need proper waiting)
    # For this script, we assume the webhook will handle waiting via separate runs
    
    output = {
        'notebook_id': notebook_id,
        'url_count': len(urls),
        'processed_count': len(results),
        'results': results
    }
    
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()