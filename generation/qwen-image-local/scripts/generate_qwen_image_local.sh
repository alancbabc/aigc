#!/bin/bash
# Qwen Image Local generation via cURL
# Usage: bash generate_qwen_image_local.sh -p "prompt" -o output.png [options]

set -euo pipefail

BASE_URL="${QWEN_IMAGE_LOCAL_BASE_URL:-http://10.0.180.14:9000}"

# Defaults
HEIGHT=1328
WIDTH=1328
NUM_INFERENCE_STEPS=50
SEED=""
NEGATIVE_PROMPT=""
IMAGES=""

usage() {
    echo "Usage: $0 -p <prompt> -o <output> [options]"
    echo ""
    echo "Required:"
    echo "  -p, --prompt      Image prompt"
    echo "  -o, --output      Output image path (.png/.jpg)"
    echo ""
    echo "Options:"
    echo "  -h, --height      Image height (default: 1328)"
    echo "  -w, --width       Image width (default: 1328)"
    echo "  -s, --steps       Inference steps (default: 50)"
    echo "      --seed        Random seed"
    echo "      --negative    Negative prompt"
    echo "      --images      Reference image paths (comma-separated)"
    echo "      --base-url    Service base URL (default from QWEN_IMAGE_LOCAL_BASE_URL)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--prompt) PROMPT="$2"; shift 2 ;;
        -o|--output) OUTPUT="$2"; shift 2 ;;
        -h|--height) HEIGHT="$2"; shift 2 ;;
        -w|--width) WIDTH="$2"; shift 2 ;;
        -s|--steps) NUM_INFERENCE_STEPS="$2"; shift 2 ;;
        --seed) SEED="$2"; shift 2 ;;
        --negative) NEGATIVE_PROMPT="$2"; shift 2 ;;
        --images) IMAGES="$2"; shift 2 ;;
        --base-url) BASE_URL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "${PROMPT:-}" || -z "${OUTPUT:-}" ]]; then
    echo "Error: --prompt and --output are required"
    usage
fi

mkdir -p "$(dirname "$OUTPUT")"

PIPELINE_NAME="qwen_image"
if [[ -n "$IMAGES" ]]; then
    PIPELINE_NAME="qwen_image_edit"
fi

echo "Submitting job to $BASE_URL..."
echo "  Prompt: ${PROMPT:0:50}..."
echo "  Output: $OUTPUT"
echo "  Pipeline: $PIPELINE_NAME"
echo "  Size: ${WIDTH}x${HEIGHT}"

CURL_ARGS=(
    -s -X POST "$BASE_URL/submit"
    -F "prompt=$PROMPT"
    -F "height=$HEIGHT"
    -F "width=$WIDTH"
    -F "num_inference_steps=$NUM_INFERENCE_STEPS"
    -F "pipeline_name=$PIPELINE_NAME"
)

[[ -n "$SEED" ]] && CURL_ARGS+=(-F "seed=$SEED")
[[ -n "$NEGATIVE_PROMPT" ]] && CURL_ARGS+=(-F "negative_prompt=$NEGATIVE_PROMPT")

if [[ -n "$IMAGES" ]]; then
    IFS=',' read -ra IMG_ARRAY <<< "$IMAGES"
    for IMG in "${IMG_ARRAY[@]}"; do
        if [[ ! -f "$IMG" ]]; then
            echo "Error: Image file not found: $IMG"
            exit 1
        fi

        case "${IMG##*.}" in
            png|PNG) MIME="image/png" ;;
            jpg|JPG|jpeg|JPEG) MIME="image/jpeg" ;;
            *)
                echo "Error: Image must be .png, .jpg, or .jpeg"
                exit 1
                ;;
        esac

        CURL_ARGS+=(-F "images=@$IMG;type=$MIME")
    done
fi

RESPONSE=$(curl "${CURL_ARGS[@]}")
echo "Response: $RESPONSE"

TASK_ID=$(printf '%s' "$RESPONSE" | grep -o '"task_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d '"' -f4)

if [[ -z "$TASK_ID" ]]; then
    echo "Error: Failed to extract task_id from response"
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

    sleep 10
done

echo "Downloading image to $OUTPUT..."
curl -s -o "$OUTPUT" "$BASE_URL/download/$TASK_ID"

if [[ -f "$OUTPUT" ]]; then
    SIZE=$(wc -c < "$OUTPUT")
    echo "Image saved: $OUTPUT ($SIZE bytes)"
else
    echo "Error: Download failed"
    exit 1
fi
