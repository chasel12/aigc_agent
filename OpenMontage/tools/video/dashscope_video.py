"""DashScope Wan video generation — text-to-video & image-to-video via Aliyun API."""
from __future__ import annotations

import os, time, json, base64, requests, subprocess
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile,
    RetryPolicy, ToolResult, ToolRuntime, ToolStability, ToolStatus, ToolTier,
)


class DashscopeVideo(BaseTool):
    name = "dashscope_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "dashscope"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set DASHSCOPE_API_KEY to your Alibaba Cloud DashScope API key.\n"
        "  Get one at https://dashscope.aliyun.com/"
    )
    fallback_tools = ["kling_video", "pexels_video", "pixabay_video"]

    capabilities = ["text_to_video", "image_to_video"]
    supports = {
        "reference_image": True,
        "aspect_ratio": True,
        "resolution": True,
        "duration": True,
        "prompt_extend": True,
    }
    best_for = [
        "cost-effective AI video generation via Alibaba Cloud",
        "Chinese-language prompt understanding",
        "image-to-video with existing generated images",
    ]
    not_good_for = ["offline generation", "long videos (>15s)"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video"],
                "default": "text_to_video",
            },
            "model": {
                "type": "string",
                "default": "wan2.6-t2v",
                "description": "Models: wan2.7-t2v-2026-06-12 (best multi-shot), wan2.6-t2v, wan2.6-i2v-flash, wan2.1-t2v-turbo",
            },
            "image_path": {
                "type": "string",
                "description": "Path to reference image (required for image_to_video)",
            },
            "size": {
                "type": "string",
                "default": "1280*720",
                "description": 'Size as "W*H". Used for t2v models.',
            },
            "resolution": {
                "type": "string",
                "enum": ["720P", "1080P"],
                "default": "720P",
            },
            "duration": {
                "type": "integer",
                "default": 5,
                "minimum": 2,
                "maximum": 15,
            },
            "prompt_extend": {"type": "boolean", "default": True},
            "shot_type": {
                "type": "string",
                "enum": ["multi"],
                "description": "Enable multi-shot narrative (wan2.6+). Set 'multi' to enable.",
            },
            "ratio": {
                "type": "string",
                "default": "16:9",
                "description": "Aspect ratio (wan2.7): 16:9, 1:1, 9:16, etc.",
            },
            "watermark": {"type": "boolean", "default": False},
            "seed": {"type": "integer"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=200, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "operation", "seed"]
    side_effects = [
        "writes video file to output_path",
        "calls DashScope video generation API (async, polls for result)",
    ]
    user_visible_verification = ["Watch generated clip for motion coherence"]

    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"

    def get_status(self) -> ToolStatus:
        if os.environ.get("DASHSCOPE_API_KEY"):
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.05  # ~$0.05 per 5s clip

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return ToolResult(success=False, error="DASHSCOPE_API_KEY not set")
        start = time.time()
        try:
            op = inputs.get("operation", "text_to_video")
            model = inputs.get("model", "wan2.6-i2v-flash" if op == "image_to_video" else "wan2.1-t2v-turbo")
            prompt = inputs["prompt"]
            duration = int(inputs.get("duration", 5))

            body: dict[str, Any] = {
                "model": model,
                "input": {"prompt": prompt},
                "parameters": {
                    "duration": duration,
                    "prompt_extend": inputs.get("prompt_extend", True),
                    "watermark": inputs.get("watermark", False),
                }
            }

            # shot_type (wan2.6+ multi-shot)
            st = inputs.get("shot_type")
            if st:
                body["parameters"]["shot_type"] = st

            if op == "image_to_video":
                img_path = inputs.get("image_path", "")
                if not img_path:
                    return ToolResult(success=False, error="image_path required for image_to_video")
                with open(str(img_path), "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                body["input"]["img_url"] = f"data:image/{Path(img_path).suffix[1:]};base64,{b64}"
                body["parameters"]["resolution"] = inputs.get("resolution", "720P")
            else:
                if model.startswith("wan2.7"):
                    body["parameters"]["resolution"] = inputs.get("resolution", "720P")
                    body["parameters"]["ratio"] = inputs.get("ratio", "16:9")
                else:
                    body["parameters"]["size"] = inputs.get("size", "1280*720")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            r = requests.post(self.API_URL, headers=headers, json=body, timeout=120)
            if r.status_code != 200:
                return ToolResult(success=False, error=f"API error {r.status_code}: {r.text[:300]}")
            data = r.json()
            task_id = data.get("output", {}).get("task_id", "")
            if not task_id:
                return ToolResult(success=False, error=f"No task_id: {json.dumps(data, ensure_ascii=False)[:500]}")

            poll_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
            for _ in range(120):
                time.sleep(10)
                pr = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
                pdata = pr.json()
                status = pdata.get("output", {}).get("task_status", "")
                if status == "SUCCEEDED":
                    output = pdata.get("output", {})
                    video_url = output.get("video_url", "") or output.get("result", {}).get("video_url", "")
                    if not video_url:
                        return ToolResult(success=False, error="No video_url in response")
                    vr = requests.get(video_url, timeout=180)
                    outpath = Path(inputs.get("output_path", f"dashscope_video_{int(time.time())}.mp4"))
                    outpath.parent.mkdir(parents=True, exist_ok=True)
                    outpath.write_bytes(vr.content)
                    return ToolResult(success=True, data={
                        "provider": "dashscope",
                        "model": model,
                        "task_id": task_id,
                        "output_path": str(outpath),
                        "file_size_bytes": len(vr.content),
                        "duration_seconds": duration,
                    })
                elif status in ("FAILED",):
                    err = pdata.get("output", {}).get("error", {}).get("message", str(pdata)[:300])
                    return ToolResult(success=False, error=f"Video gen failed: {err}")
            return ToolResult(success=False, error=f"Timeout polling task {task_id}")
        except Exception as e:
            return ToolResult(success=False, error=f"DashScope video error: {e}")
