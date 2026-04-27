#!/bin/bash
# LTX-2.3 Audio-to-Video generation via cURL
# Usage: bash generate_a2v.sh -a /path/to/audio.wav -p "prompt" -o output.mp4

set -euo pipefail

BASE_URL="${LTX23_BASE_URL:-http://10.0.180.14:80}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Defaults
HEIGHT=1024
WIDTH=1536
VIDEO_SECONDS=5
FRAME_RATE=24
NUM_INFERENCE_STEPS=30
A2V_AUDIO_START_TIME=0
A2V_AUDIO_INSERT_VIDEO_TIME=0
A2V_AUDIO_MAX_DURATION=""
SEED=""
NEGATIVE_PROMPT=""
IMAGES=""
IMAGE_IDXS=""
IMAGE_STRENGTHS=""

usage() {
    echo "Usage: $0 -a <audio> -p <prompt> -o <output> [options]"
    echo ""
    echo "Required:"
    echo "  -a, --audio       Audio file path (.wav or .mp3)"
    echo "  -p, --prompt      Video content description"
    echo "  -o, --output      Output video path (.mp4)"
    echo ""
    echo "Options:"
    echo "  -h, --height      Video height (default: 1024)"
    echo "  -w, --width       Video width (default: 1536)"
    echo "  -d, --duration    Video duration in seconds (default: 5)"
    echo "  -r, --frame-rate  Frame rate (default: 24)"
    echo "  -s, --steps       Inference steps (default: 30)"
    echo "      --seed        Random seed"
    echo "      --negative    Negative prompt"
    echo "      --images      Reference image paths (comma-separated)"
    echo "      --image-idxs  Image insertion positions (comma-separated)"
    echo "      --image-strengths Image strengths (comma-separated)"
    echo "      --audio-start Audio start time in seconds (default: 0)"
    echo "      --audio-max   Audio max duration in seconds"
    echo "      --insert-time Video insertion time in audio (default: 0)"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--audio) AUDIO="$2"; shift 2 ;;
        -p|--prompt) PROMPT="$2"; shift 2 ;;
        -o|--output) OUTPUT="$2"; shift 2 ;;
        -h|--height) HEIGHT="$2"; shift 2 ;;
        -w|--width) WIDTH="$2"; shift 2 ;;
        -d|--duration) VIDEO_SECONDS="$2"; shift 2 ;;
        -r|--frame-rate) FRAME_RATE="$2"; shift 2 ;;
        -s|--steps) NUM_INFERENCE_STEPS="$2"; shift 2 ;;
        --seed) SEED="$2"; shift 2 ;;
        --negative) NEGATIVE_PROMPT="$2"; shift 2 ;;
        --images) IMAGES="$2"; shift 2 ;;
        --image-idxs) IMAGE_IDXS="$2"; shift 2 ;;
        --image-strengths) IMAGE_STRENGTHS="$2"; shift 2 ;;
        --audio-start) A2V_AUDIO_START_TIME="$2"; shift 2 ;;
        --audio-max) A2V_AUDIO_MAX_DURATION="$2"; shift 2 ;;
        --insert-time) A2V_AUDIO_INSERT_VIDEO_TIME="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Validate required args
if [[ -z "${AUDIO:-}" || -z "${PROMPT:-}" || -z "${OUTPUT:-}" ]]; then
    echo "Error: --audio, --prompt, and --output are required"
    usage
fi

if [[ ! -f "$AUDIO" ]]; then
    echo "Error: Audio file not found: $AUDIO"
    exit 1
fi

# Calculate num_frames (8n + 1) without Python dependency
TOTAL_FRAMES=$(awk "BEGIN { printf \"%.0f\", ($VIDEO_SECONDS * $FRAME_RATE) }")
NUM_FRAMES=$(( ((TOTAL_FRAMES + 7) / 8) * 8 + 1 ))

# Detect audio type
if [[ "$AUDIO" == *.wav ]]; then
    AUDIO_TYPE="audio/wav"
elif [[ "$AUDIO" == *.mp3 ]]; then
    AUDIO_TYPE="audio/mpeg"
else
    echo "Error: Audio must be .wav or .mp3"
    exit 1
fi

echo "Submitting job to $BASE_URL..."
echo "  Prompt: ${PROMPT:0:50}..."
echo "  Audio: $AUDIO"
echo "  Frames: $NUM_FRAMES (${WIDTH}x${HEIGHT} @ ${FRAME_RATE}fps)"

# Validate images before submit
if [[ -n "$IMAGES" ]]; then
    IFS=',' read -ra IMG_ARRAY <<< "$IMAGES"
    for IMG in "${IMG_ARRAY[@]}"; do
        if [[ ! -f "$IMG" ]]; then
            echo "Error: Image file not found: $IMG"
            exit 1
        fi
    done
fi

# Submit via UTF-8 safe Node multipart transport
NODE_ARGS=(
    "$SCRIPT_DIR/submit_ltx_transport.mjs"
    --base-url "$BASE_URL"
    --prompt "$PROMPT"
    --height "$HEIGHT"
    --width "$WIDTH"
    --num-frames "$NUM_FRAMES"
    --frame-rate "$FRAME_RATE"
    --num-inference-steps "$NUM_INFERENCE_STEPS"
    --pipeline-name a2vid_two_stage
    --audio-path "$AUDIO"
    --audio-type "$AUDIO_TYPE"
    --audio-start "$A2V_AUDIO_START_TIME"
    --insert-time "$A2V_AUDIO_INSERT_VIDEO_TIME"
)

[[ -n "$SEED" ]] && NODE_ARGS+=(--seed "$SEED")
[[ -n "$NEGATIVE_PROMPT" ]] && NODE_ARGS+=(--negative "$NEGATIVE_PROMPT")
[[ -n "$A2V_AUDIO_MAX_DURATION" ]] && NODE_ARGS+=(--audio-max "$A2V_AUDIO_MAX_DURATION")
[[ -n "$IMAGES" ]] && NODE_ARGS+=(--images "$IMAGES")
[[ -n "$IMAGE_IDXS" ]] && NODE_ARGS+=(--image-idxs "$IMAGE_IDXS")
[[ -n "$IMAGE_STRENGTHS" ]] && NODE_ARGS+=(--image-strengths "$IMAGE_STRENGTHS")

RESPONSE=$(node "${NODE_ARGS[@]}")
echo "Response: $RESPONSE"

TASK_ID=$(printf '%s' "$RESPONSE" | grep -o '"task_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d '"' -f4)

if [[ -z "$TASK_ID" ]]; then
    echo "Error: Failed to extract task_id from response"
    exit 1
fi

echo "Task submitted: $TASK_ID"

# Poll for completion
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

# Download
echo "Downloading video to $OUTPUT..."
curl -s -o "$OUTPUT" "$BASE_URL/download/$TASK_ID"

if [[ -f "$OUTPUT" ]]; then
    SIZE=$(wc -c < "$OUTPUT")
    echo "Video saved: $OUTPUT ($SIZE bytes)"
else
    echo "Error: Download failed"
    exit 1
fi
