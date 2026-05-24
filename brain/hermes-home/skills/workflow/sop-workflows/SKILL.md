---
name: sop-workflows
description: A collection of standard operating procedures and workflows for various tasks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [sop, workflow, procedures, automation]
    category: workflow
---

# Standard Operating Procedures and Workflows

This skill serves as a central repository for various Standard Operating Procedures (SOPs) and automated workflows. Each section or linked reference details a specific process, guiding the agent through recurring tasks, common problem-solving approaches, or automated sequences.

## How to Use This Skill

-   **Browse Sections:** Navigate through the different sections below, each describing a distinct workflow.
-   **Refer to Linked Files:** For detailed scripts, templates, or extensive documentation, check the `references/`, `templates/`, and `scripts/` directories linked to this skill.
-   **Contribute:** When a complex task is completed or a robust solution is found, consider documenting it here as a new section or a linked file.

## Available Workflows

### NotebookLM Post-Processor

**Purpose**
This workflow processes the raw output from `notebooklm_processor.py` to extract clean JSON, and then uses `copy-and-rename-output.py` for further processing.

**Arguments**
- `processor_raw_output_file`: Absolute path to the raw output file from `notebooklm_processor.py` (e.g., `/tmp/processor_full_output.txt`).
- `wiki_local_path`: Absolute path to the local wiki repository.

**Steps**

1.  **Extract and clean JSON output**:
    -   Reads `processor_raw_output_file`.
    -   Uses `grep -oP '{.*}'` to extract all lines that look like JSON objects.
    -   Takes the `tail -1` to get the last complete JSON object.
    -   Saves this cleaned JSON to `/tmp/processor_clean_output.json`.

2.  **Execute `copy-and-rename-output.py`**:
    -   Runs `copy-and-rename-output.py` using `/tmp/processor_clean_output.json` as input and the `wiki_local_path`.
    -   Captures its stdout to `/tmp/copy_rename_output.json`.

3.  **Return Results**:
    -   Reads and returns the content of `/tmp/processor_clean_output.json` and `/tmp/copy_rename_output.json`.

**Script**
The core logic for this workflow is contained in a script. This script handles the extraction and execution steps.
