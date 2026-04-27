#!/bin/bash
# Qwen TTS local-service generation via bash + Node UTF-8 transport
# Usage: bash generate_qwen_tts_local.sh --text "你好" --output output.wav [options]

set -euo pipefail

BASE_URL="${QWEN_TTS_LOCAL_BASE_URL:-http://10.0.180.14:7786}"
LANGUAGE="auto"
SPEAKER=""
INSTRUCT=""
POLL_SECONDS=10

usage() {
    echo "Usage: $0 --text <text> --output <output> [options]"
    echo ""
    echo "Required:"
    echo "  --text            Text to synthesize"
    echo "  --output          Output audio path (.wav)"
    echo ""
    echo "Options:"
    echo "  --language        Language (default: auto)"
    echo "  --speaker         Preset speaker name"
    echo "  --instruct        Voice instruction / style hint"
    echo "  --base-url        Service base URL (default from QWEN_TTS_LOCAL_BASE_URL)"
    echo "  --poll-seconds    Poll interval in seconds (default: 10)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --text) TEXT="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        --language) LANGUAGE="$2"; shift 2 ;;
        --speaker) SPEAKER="$2"; shift 2 ;;
        --instruct) INSTRUCT="$2"; shift 2 ;;
        --base-url) BASE_URL="$2"; shift 2 ;;
        --poll-seconds) POLL_SECONDS="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "${TEXT:-}" || -z "${OUTPUT:-}" ]]; then
    echo "Error: --text and --output are required"
    usage
fi

mkdir -p "$(dirname "$OUTPUT")"

PIPELINE_NAME="qwen_tts_voicedesign"
if [[ -n "$SPEAKER" ]]; then
    PIPELINE_NAME="qwen_tts_customvoice"
fi

echo "Submitting Qwen TTS job to $BASE_URL..."
echo "  Pipeline: $PIPELINE_NAME"
echo "  Language: $LANGUAGE"
[[ -n "$SPEAKER" ]] && echo "  Speaker: $SPEAKER"
echo "  Output: $OUTPUT"

NODE_SCRIPT="$(dirname "$0")/submit_qwen_tts_local.mjs"
NODE_ARGS=(
    "$NODE_SCRIPT"
    --base-url "$BASE_URL"
    --text "$TEXT"
    --pipeline-name "$PIPELINE_NAME"
    --language "$LANGUAGE"
)

[[ -n "$INSTRUCT" ]] && NODE_ARGS+=(--instruct "$INSTRUCT")
[[ -n "$SPEAKER" ]] && NODE_ARGS+=(--speaker "$SPEAKER")

RESPONSE=$(node "${NODE_ARGS[@]}")
echo "Response: $RESPONSE"

TASK_ID=$(printf '%s' "$RESPONSE" | grep -o '"task_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d '"' -f4)
STATUS=$(printf '%s' "$RESPONSE" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d '"' -f4)

if [[ -z "$TASK_ID" || "$STATUS" != "submitted" ]]; then
    echo "Error: Failed to submit Qwen TTS job"
    exit 1
fi

echo "Task submitted: $TASK_ID"
echo "Waiting for task to complete..."

while true; do
    STATUS_JSON=$(curl -s "$BASE_URL/status/$TASK_ID")
    STATUS=$(printf '%s' "$STATUS_JSON" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d '"' -f4)

    echo "  Status: $STATUS"

    if [[ "$STATUS" == "done" ]]; then
        break
    elif [[ "$STATUS" == "error" ]]; then
        echo "Error: Task failed"
        echo "$STATUS_JSON"
        exit 1
    fi

    sleep "$POLL_SECONDS"
done

echo "Downloading audio to $OUTPUT..."

ATTEMPT=0
MAX_ATTEMPTS=3
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    ATTEMPT=$((ATTEMPT + 1))
    if curl -s -o "$OUTPUT" "$BASE_URL/download/$TASK_ID"; then
        if [[ -f "$OUTPUT" ]]; then
            SIZE=$(wc -c < "$OUTPUT")
            if [[ "$SIZE" -gt 0 ]]; then
                echo "Audio saved: $OUTPUT ($SIZE bytes)"
                exit 0
            fi
        fi
    fi

    if [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; then
        echo "Download retry [$ATTEMPT/$MAX_ATTEMPTS]..."
        sleep 2
    fi
done

echo "Error: Download failed for task $TASK_ID"
exit 1
