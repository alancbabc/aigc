import argparse
import asyncio
import os
import time
from pathlib import Path
from typing import Iterable

import aiohttp
from PIL import Image


DEFAULT_BASE_URL = os.environ.get("QWEN_IMAGE_LOCAL_BASE_URL", "http://10.0.180.14:9000")


def parse_images(images_arg: str | None) -> list[str]:
    if not images_arg:
        return []
    return [item.strip() for item in images_arg.split(",") if item.strip()]


def ensure_parent_dir(file_path: str) -> None:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def validate_images(images: Iterable[str]) -> None:
    for image_path in images:
        suffix = Path(image_path).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(f"Unsupported image format: {image_path}")


def infer_size_from_first_image(images: list[str]) -> tuple[int, int]:
    with Image.open(images[0]) as image:
        return image.width, image.height


class QwenImageLocalClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def submit(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str | None = None,
        seed: int | None = None,
        height: int = 1328,
        width: int = 1328,
        num_inference_steps: int = 50,
        images: list[str] | None = None,
    ) -> str:
        pipeline_name = "qwen_image_edit" if images else "qwen_image"
        form = aiohttp.FormData()
        form.add_field("prompt", prompt)
        form.add_field("height", str(height))
        form.add_field("width", str(width))
        form.add_field("num_inference_steps", str(num_inference_steps))
        form.add_field("pipeline_name", pipeline_name)

        if negative_prompt:
            form.add_field("negative_prompt", negative_prompt)
        if seed is not None:
            form.add_field("seed", str(seed))

        opened_files = []
        try:
            if images:
                validate_images(images)
                for image_path in images:
                    opened = open(image_path, "rb")
                    opened_files.append(opened)
                    content_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
                    form.add_field(
                        "images",
                        opened,
                        filename=os.path.basename(image_path),
                        content_type=content_type,
                    )

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/submit", data=form) as response:
                    response.raise_for_status()
                    result = await response.json()
        finally:
            for opened in opened_files:
                opened.close()

        if result.get("status") != "submitted" or "task_id" not in result:
            raise RuntimeError(f"Submit failed: {result}")

        ensure_parent_dir(output_path)
        return result["task_id"]

    async def wait_until_done(self, task_id: str, poll_interval: int = 20) -> None:
        while True:
            await asyncio.sleep(poll_interval)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/status/{task_id}") as response:
                    response.raise_for_status()
                    result = await response.json()

            status = result.get("status")
            if status == "done":
                return
            if status in {"queued", "running", "submitted"}:
                continue
            raise RuntimeError(f"Task failed or disappeared: {result}")

    async def download(self, task_id: str, output_path: str, max_retries: int = 3) -> None:
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/download/{task_id}") as response:
                        response.raise_for_status()
                        with open(output_path, "wb") as output_file:
                            async for chunk in response.content.iter_chunked(1024 * 1024):
                                if chunk:
                                    output_file.write(chunk)
                return
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
        raise RuntimeError(f"Download failed for task {task_id}") from last_error

    async def run(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str | None = None,
        seed: int | None = None,
        height: int | None = None,
        width: int | None = None,
        num_inference_steps: int = 50,
        images: list[str] | None = None,
    ) -> None:
        normalized_images = images or []
        if normalized_images and (height is None or width is None):
            width, height = infer_size_from_first_image(normalized_images)

        resolved_width = width if width is not None else 1328
        resolved_height = height if height is not None else 1328

        task_id = await self.submit(
            prompt=prompt,
            output_path=output_path,
            negative_prompt=negative_prompt,
            seed=seed,
            height=resolved_height,
            width=resolved_width,
            num_inference_steps=num_inference_steps,
            images=normalized_images,
        )
        print(f"Job submitted: {task_id}")
        await self.wait_until_done(task_id)
        await self.download(task_id, output_path)
        print(f"Image saved to {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate images via local Qwen Image service")
    parser.add_argument("--prompt", required=True, help="Prompt text")
    parser.add_argument("--negative-prompt", default=None, help="Optional negative prompt")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    parser.add_argument("--width", type=int, default=None, help="Image width")
    parser.add_argument("--height", type=int, default=None, help="Image height")
    parser.add_argument("--steps", type=int, default=50, help="Inference steps")
    parser.add_argument("--images", default=None, help="Comma-separated reference image paths")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Service base URL")
    parser.add_argument("--output", default=None, help="Output image path")
    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    images = parse_images(args.images)

    timestamp = str(int(time.time()))
    output_path = args.output or f"outputs/qwen_image_{timestamp}.png"

    client = QwenImageLocalClient(base_url=args.base_url)
    await client.run(
        prompt=args.prompt,
        output_path=output_path,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        width=args.width,
        height=args.height,
        num_inference_steps=args.steps,
        images=images,
    )


if __name__ == "__main__":
    asyncio.run(main())
