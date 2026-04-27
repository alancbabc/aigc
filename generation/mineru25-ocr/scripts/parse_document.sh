#!/bin/bash
# Gitee AI MinerU2.5 document/image OCR / parsing via cURL
# Usage: bash parse_document.sh -f document.pdf -o output.md

set -euo pipefail

API_BASE_URL="${AIGC_GITEE_BASE_URL:-https://ai.gitee.com/v1}"
TASK_BASE_URL="${AIGC_GITEE_TASK_BASE_URL:-https://ai.gitee.com/api/v1/task}"
API_KEY="${AIGC_GITEE_API_KEY:-}"
API_URL="${API_BASE_URL}/async/documents/parse"

MODEL="MinerU2.5"
IS_OCR="true"
INCLUDE_IMAGE_BASE64="true"
FORMULA_ENABLE="true"
TABLE_ENABLE="true"
LAYOUT_MODEL="doclayout_yolo"
OUTPUT_FORMAT="md"
POLL_INTERVAL=5
TIMEOUT=1800

usage() {
    echo "Usage: $0 -f <file> -o <output.md> [options]"
    echo ""
    echo "Required:"
    echo "  -f, --file                  Input file path (PDF or image)"
    echo "  -o, --output                Output markdown path"
    echo ""
    echo "Options:"
    echo "  -m, --model                 Model name (default: MinerU2.5)"
    echo "      --is-ocr                Enable OCR: true/false (default: true)"
    echo "      --include-image-base64  Include image base64: true/false (default: true)"
    echo "      --formula-enable        Enable formula parsing: true/false (default: true)"
    echo "      --table-enable          Enable table parsing: true/false (default: true)"
    echo "      --layout-model          Layout model (default: doclayout_yolo)"
    echo "      --output-format         Output format (default: md)"
    echo "      --interval              Poll interval in seconds (default: 5)"
    echo "      --timeout               Max wait time in seconds (default: 1800)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file) FILE_PATH="$2"; shift 2 ;;
        -o|--output) OUTPUT_PATH="$2"; shift 2 ;;
        -m|--model) MODEL="$2"; shift 2 ;;
        --is-ocr) IS_OCR="$2"; shift 2 ;;
        --include-image-base64) INCLUDE_IMAGE_BASE64="$2"; shift 2 ;;
        --formula-enable) FORMULA_ENABLE="$2"; shift 2 ;;
        --table-enable) TABLE_ENABLE="$2"; shift 2 ;;
        --layout-model) LAYOUT_MODEL="$2"; shift 2 ;;
        --output-format) OUTPUT_FORMAT="$2"; shift 2 ;;
        --interval) POLL_INTERVAL="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "${FILE_PATH:-}" || -z "${OUTPUT_PATH:-}" ]]; then
    echo "Error: --file and --output are required"
    usage
fi

if [[ -z "$API_KEY" ]]; then
    echo "Error: AIGC_GITEE_API_KEY environment variable not set"
    exit 1
fi

if [[ ! -f "$FILE_PATH" ]]; then
    echo "Error: File not found: $FILE_PATH"
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"
STATUS_JSON_PATH="${OUTPUT_PATH%.md}.status.json"

echo "Submitting MinerU2.5 OCR job..."
echo "  File: $FILE_PATH"
echo "  Model: $MODEL"
echo "  Output: $OUTPUT_PATH"

RESPONSE=$(curl -sS "$API_URL" \
    -X POST \
    -H "Authorization: Bearer $API_KEY" \
    -F "file=@$FILE_PATH" \
    -F "model=$MODEL" \
    -F "is_ocr=$IS_OCR" \
    -F "include_image_base64=$INCLUDE_IMAGE_BASE64" \
    -F "formula_enable=$FORMULA_ENABLE" \
    -F "table_enable=$TABLE_ENABLE" \
    -F "layout_model=$LAYOUT_MODEL" \
    -F "output_format=$OUTPUT_FORMAT")

echo "$RESPONSE" > "$STATUS_JSON_PATH"

TASK_ID=$(python - "$STATUS_JSON_PATH" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

task_id = data.get('task_id', '')
if not task_id:
    url = ((data.get('urls') or {}).get('get') or '').rstrip('/')
    if url:
        task_id = url.split('/')[-1]

print(task_id)
PY
)

if [[ -z "$TASK_ID" ]]; then
    echo "Error: Failed to extract task_id from response"
    cat "$STATUS_JSON_PATH"
    exit 1
fi

echo "Task submitted: $TASK_ID"
echo "Polling: ${TASK_BASE_URL}/${TASK_ID}"

extract_field() {
    local json_file="$1"
    local path_expr="$2"
    python - "$json_file" "$path_expr" <<'PY'
import json
import sys

json_file = sys.argv[1]
path = sys.argv[2].split('.')

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

value = data
for part in path:
    if isinstance(value, dict) and part in value:
        value = value[part]
    else:
        print("")
        raise SystemExit(0)

if isinstance(value, str):
    print(value)
else:
    print("")
PY
}

extract_segments_markdown() {
    local json_file="$1"
    python - "$json_file" <<'PY'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)

segments = ((data.get('output') or {}).get('segments') or [])
parts = []
for segment in segments:
    content = segment.get('content')
    if isinstance(content, str) and content:
        parts.append(content)

print("\n\n".join(parts))
PY
}

MAX_ATTEMPTS=$((TIMEOUT / POLL_INTERVAL))
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    ATTEMPT=$((ATTEMPT + 1))
    STATUS_RESPONSE=$(curl -sS "${TASK_BASE_URL}/${TASK_ID}" -H "Authorization: Bearer $API_KEY")
    echo "$STATUS_RESPONSE" > "$STATUS_JSON_PATH"

    STATUS=$(python - "$STATUS_JSON_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)

print(data.get('status', ''))
PY
)
    echo "  Status [$ATTEMPT]: ${STATUS:-unknown}"

    case "$STATUS" in
        success|succeeded|done)
            break
            ;;
        failed|error|cancelled)
            echo "Error: OCR task failed"
            cat "$STATUS_JSON_PATH"
            exit 1
            ;;
    esac

    sleep "$POLL_INTERVAL"
done

if [[ $ATTEMPT -ge $MAX_ATTEMPTS ]]; then
    echo "Error: Timeout waiting for OCR task completion"
    exit 1
fi

DOWNLOAD_URL=""
for field in output.markdown_url output.file_url markdown_url file_url output.url url; do
    DOWNLOAD_URL=$(extract_field "$STATUS_JSON_PATH" "$field")
    if [[ -n "$DOWNLOAD_URL" ]]; then
        break
    fi
done

if [[ -n "$DOWNLOAD_URL" ]]; then
    echo "Downloading markdown result..."
    curl -sS -L "$DOWNLOAD_URL" -o "$OUTPUT_PATH"
else
    MARKDOWN_TEXT=""
    for field in output.markdown markdown output.content content; do
        MARKDOWN_TEXT=$(extract_field "$STATUS_JSON_PATH" "$field")
        if [[ -n "$MARKDOWN_TEXT" ]]; then
            break
        fi
    done

    if [[ -z "$MARKDOWN_TEXT" ]]; then
        MARKDOWN_TEXT=$(extract_segments_markdown "$STATUS_JSON_PATH")
    fi

    if [[ -n "$MARKDOWN_TEXT" ]]; then
        printf '%s\n' "$MARKDOWN_TEXT" > "$OUTPUT_PATH"
    else
        echo "Error: Task succeeded but no markdown result field was found"
        cat "$STATUS_JSON_PATH"
        exit 1
    fi
fi

if [[ -f "$OUTPUT_PATH" ]]; then
    SIZE=$(wc -c < "$OUTPUT_PATH")
    echo "Markdown saved: $OUTPUT_PATH ($SIZE bytes)"
    echo "Status JSON saved: $STATUS_JSON_PATH"
else
    echo "Error: Output file was not created"
    exit 1
fi
