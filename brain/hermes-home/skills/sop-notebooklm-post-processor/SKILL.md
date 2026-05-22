---
name: sop-notebooklm-post-processor
description: "Extracts clean JSON output from notebooklm_processor.py raw output and executes copy-and-rename-output.py."
version: 1.0.0
---

## Purpose
This skill takes the raw output file from `notebooklm_processor.py`, extracts the clean JSON result, and then executes `copy-and-rename-output.py`.

## Arguments
- `processor_raw_output_file`: Absolute path to the raw output file from `notebooklm_processor.py` (e.g., `/tmp/processor_full_output.txt`).
- `wiki_local_path`: Absolute path to the local wiki repository.

## Steps

1.  **Extract and clean JSON output**:
    -   Read `processor_raw_output_file`.
    -   Use `grep -oP '{.*}'` to extract all lines that look like JSON objects.
    -   Take the `tail -1` to get the last complete JSON object (which should be the final result).
    -   Save this cleaned JSON to `/tmp/processor_clean_output.json`.

2.  **Execute `copy-and-rename-output.py`**:
    -   Run `copy-and-rename-output.py` using `/tmp/processor_clean_output.json` as input and the `wiki_local_path`.
    -   Capture its stdout to `/tmp/copy_rename_output.json`.

3.  **Return Results**:
    -   Read and return the content of `/tmp/processor_clean_output.json` and `/tmp/copy_rename_output.json`.

```bash
# Step 1: Extract and clean JSON output
CLEAN_JSON_FILE="/tmp/processor_clean_output.json"

# Ensure the raw output file exists and is not empty before processing
if [ ! -s "${processor_raw_output_file}" ]; then
  echo "ERROR: processor_raw_output_file '${processor_raw_output_file}' is empty or does not exist." >&2
  exit 1
fi

JSON_OUTPUT=$(grep -oP '{.*}' "${processor_raw_output_file}" | tail -1)
if [ -z "${JSON_OUTPUT}" ]; then
  echo "ERROR: No JSON output found in '${processor_raw_output_file}'." >&2
  # Dump raw content for debugging
  cat "${processor_raw_output_file}" >&2
  exit 1
fi
echo "${JSON_OUTPUT}" > "${CLEAN_JSON_FILE}"

# Step 2: Execute copy-and-rename-output.py
COPY_RENAME_OUTPUT_FILE="/tmp/copy_rename_output.json"
python3 "/home/zhouhuijuan1987/agent-brain-plugins/youtube-wiki/skills/sop-notebooklm-research/scripts/copy-and-rename-output.py" "${CLEAN_JSON_FILE}" "${wiki_local_path}" > "${COPY_RENAME_OUTPUT_FILE}" 2>&1
COPY_RENAME_EXIT_CODE=$?

# Step 3: Return Results (read files)
PROCESSOR_RESULT_JSON=$(cat "${CLEAN_JSON_FILE}")
COPY_RENAME_RESULT_JSON=$(cat "${COPY_RENAME_OUTPUT_FILE}")

echo "__PROCESSOR_RESULT_JSON_START__"
echo "${PROCESSOR_RESULT_JSON}"
echo "__PROCESSOR_RESULT_JSON_END__"

echo "__COPY_RENAME_RESULT_JSON_START__"
echo "${COPY_RENAME_RESULT_JSON}"
echo "__COPY_RENAME_RESULT_JSON_END__"

exit $COPY_RENAME_EXIT_CODE
