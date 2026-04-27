#!/bin/bash
# FLUX Image Edit 批量生成脚本
# 用法: bash batch_gen.sh

API_KEY="${AIGC_GITEE_API_KEY}"
API_URL="${AIGC_GITEE_BASE_URL:-https://ai.gitee.com/v1}/images/edits"
OUTPUT_DIR="${OUTPUT_DIR:-./outputs/keyframes}"

if [ -z "$API_KEY" ]; then
  echo "AIGC_GITEE_API_KEY is required"
  exit 1
fi

mkdir -p "$OUTPUT_DIR/scene-01"

# 测试单张图生图
curl -s -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -F "prompt=A cute little girl walking on a street" \
  -F "image=@./inputs/character.png" \
  -F "task_types=id" \
  -F "task_types=style" \
  -F "model=FLUX.2-klein-9B" \
  -F "size=1024x576" \
  -F "num_inference_steps=4" \
  -F "guidance_scale=1" | python3 -c "
import json, sys, time, requests
data = json.load(sys.stdin)
if 'task_id' in data:
    print('Task ID:', data['task_id'])
    # 轮询结果
    for i in range(30):
        time.sleep(5)
        import os
        resp = requests.get(
            f'https://ai.gitee.com/api/v1/task/{data[\"task_id\"]}',
            headers={'Authorization': 'Bearer ' + os.environ.get('AIGC_GITEE_API_KEY', '')}
        )
        result = resp.json()
        print(f'Check {i+1}:', result.get('status'))
        if result.get('status') == 'success':
            # 下载图片
            output_url = result.get('output', {}).get('data', [{}])[0].get('url')
            if output_url:
                import urllib.request
                urllib.request.urlretrieve(output_url, './outputs/keyframes/scene-01/flux_test.png')
                print('Downloaded!')
            break
        elif result.get('status') == 'failed':
            print('Failed:', result)
            break
else:
    print(data)
"
