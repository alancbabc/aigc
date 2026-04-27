#!/bin/bash
# LTX-2 High-Quality Image-to-Video via Gitee API
# Usage: bash generate_hq_gitee.sh -p "prompt" -i image.png -o output.mp4

set -euo pipefail

# Config
API_URL="https://ai.gitee.com/v1/async/videos/image-to-video"
STATUS_URL="https://ai.gitee.com/api/v1/task"
API_TOKEN="${GITEE_API_TOKEN:-}"

# Defaults
MODEL="LTX-2"
HEIGHT=640
WIDTH=512
NUM_FRAMES=63
FPS=24
NUM_INFERENCE_STEPS=8
GUIDANCE_SCALE=1
TIMEOUT=1800  # 30 minutes

usage() {
    echo "Usage: $0 -p <prompt> -i <image> -o <output> [options]"
    echo ""
    echo "Required:"
    echo "  -p, --prompt      Video content description"
    echo "  -i, --image       Reference image path"
    echo "  -o, --output      Output video path (.mp4)"
    echo ""
    echo "Options:"
    echo "  -h, --height      Video height (default: 683)"
    echo "  -w, --width       Video width (default: 512)"
    echo "  -n, --num-frames  Number of frames (default: 63)"
    echo "  -f, --fps         Frame rate (default: 24)"
    echo "  -s, --steps       Inference steps (default: 8)"
    echo "  -g, --guidance    Guidance scale (default: 1)"
    echo "      --token       Gitee API token (or set GITEE_API_TOKEN env)"
    echo "      --timeout     Max wait time in seconds (default: 1800)"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--prompt) PROMPT="$2"; shift 2 ;;
        -i|--image) IMAGE="$2"; shift 2 ;;
        -o|--output) OUTPUT="$2"; shift 2 ;;
        -h|--height) HEIGHT="$2"; shift 2 ;;
        -w|--width) WIDTH="$2"; shift 2 ;;
        -n|--num-frames) NUM_FRAMES="$2"; shift 2 ;;
        -f|--fps) FPS="$2"; shift 2 ;;
        -s|--steps) NUM_INFERENCE_STEPS="$2"; shift 2 ;;
        -g|--guidance) GUIDANCE_SCALE="$2"; shift 2 ;;
        --token) API_TOKEN="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Validate required args
if [[ -z "${PROMPT:-}" || -z "${IMAGE:-}" || -z "${OUTPUT:-}" ]]; then
    echo "Error: --prompt, --image, and --output are required"
    usage
fi

if [[ -z "$API_TOKEN" ]]; then
    echo "Error: Gitee API token required. Set GITEE_API_TOKEN env or use --token"
    exit 1
fi

if [[ ! -f "$IMAGE" ]]; then
    echo "Error: Image file not found: $IMAGE"
    exit 1
fi

# Detect image mime type
IMAGE_NAME=$(basename "$IMAGE")
case "${IMAGE##*.}" in
    png) MIME="image/png" ;;
    jpg|jpeg) MIME="image/jpeg" ;;
    webp) MIME="image/webp" ;;
    *) MIME="application/octet-stream" ;;
esac

echo "Submitting to Gitee API..."
echo "  Prompt: ${PROMPT:0:50}..."
echo "  Image: $IMAGE"
echo "  Output: ${WIDTH}x${HEIGHT} @ ${FPS}fps, ${NUM_FRAMES} frames"

# Submit task
RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Authorization: Bearer $API_TOKEN" \
    -F "prompt=$PROMPT" \
    -F "model=$MODEL" \
    -F "num_inference_steps=$NUM_INFERENCE_STEPS" \
    -F "num_frames=$NUM_FRAMES" \
    -F "fps=$FPS" \
    -F "guidance_scale=$GUIDANCE_SCALE" \
    -F "height=$HEIGHT" \
    -F "width=$WIDTH" \
    -F "image=@$IMAGE;type=$MIME")

echo "Response: $RESPONSE"

TASK_ID=$(echo "$RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || echo "")

if [[ -z "$TASK_ID" ]]; then
    echo "Error: Failed to extract task_id from response"
    exit 1
fi

echo "Task submitted: $TASK_ID"

# Poll for completion
echo "Waiting for task to complete..."
MAX_ATTEMPTS=$((TIMEOUT / 10))
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "  Checking status [$ATTEMPT]... "

    STATUS_JSON=$(curl -s "$STATUS_URL/$TASK_ID" -H "Authorization: Bearer $API_TOKEN")
    
    # Check for error
    ERROR=$(echo "$STATUS_JSON" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null || echo "")
    if [[ -n "$ERROR" ]]; then
        ERROR_MSG=$(echo "$STATUS_JSON" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','Unknown error'))" 2>/dev/null || echo "Unknown")
        echo "ERROR"
        echo "Error: $ERROR - $ERROR_MSG"
        exit 1
    fi

    STATUS=$(echo "$STATUS_JSON" | python -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    echo "$STATUS"

    if [[ "$STATUS" == "success" ]]; then
        FILE_URL=$(echo "$STATUS_JSON" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('output',{}).get('file_url',''))" 2>/dev/null || echo "")
        if [[ -n "$FILE_URL" ]]; then
            echo "Download URL: $FILE_URL"
            echo "Downloading to $OUTPUT..."
            curl -s -L -o "$OUTPUT" "$FILE_URL"
            
            if [[ -f "$OUTPUT" ]]; then
                SIZE=$(wc -c < "$OUTPUT")
                echo "Video saved: $OUTPUT ($SIZE bytes)"
            else
                echo "Error: Download failed"
                exit 1
            fi
        else
            echo "Error: No file_url in response"
            echo "$STATUS_JSON"
            exit 1
        fi
        exit 0
    elif [[ "$STATUS" == "failed" || "$STATUS" == "cancelled" ]]; then
        echo "Task $STATUS"
        exit 1
    fi

    sleep 10
done

echo "Timeout: Maximum wait time exceeded ($TIMEOUT seconds)"
exit 1
