"""DashScope Wan2.2-s2v digital human — photo + audio → talking video."""
from __future__ import annotations

import os, time, json, base64, requests, hashlib
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile,
    RetryPolicy, ToolResult, ToolRuntime, ToolStability, ToolStatus, ToolTier,
)


class DashscopeDigitalHuman(BaseTool):
    name = "dashscope_digital_human"
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
    )

    capabilities = ["digital_human", "portrait_to_video", "audio_driven_avatar"]
    supports = {
        "reference_image": True,
        "audio_input": True,
        "style": True,
        "resolution": True,
    }
    best_for = [
        "talking-head video from photo + audio via Alibaba Cloud",
        "Chinese-language digital human",
        "cost-effective avatar generation",
    ]
    not_good_for = ["offline generation", "videos >20s per segment"]

    input_schema = {
        "type": "object",
        "required": ["image", "audio"],
        "properties": {
            "image": {
                "type": "string",
                "description": "Portrait image path (local) or HTTP URL",
            },
            "audio": {
                "type": "string",
                "description": "Audio file path (local) or HTTP URL",
            },
            "style": {
                "type": "string",
                "enum": ["speech", "sing", "perform"],
                "default": "speech",
            },
            "resolution": {
                "type": "string",
                "enum": ["480P", "720P"],
                "default": "480P",
            },
            "detect_only": {
                "type": "boolean",
                "default": False,
                "description": "If true, only run wan2.2-s2v-detect (image check)",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=200, network_required=True)
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    side_effects = [
        "writes video file to output_path",
        "uploads image/audio to DashScope temporary storage if local files provided",
        "calls DashScope s2v API (async, polls for result)",
    ]

    API_BASE = "https://dashscope.aliyuncs.com"
    S2V_URL = f"{API_BASE}/api/v1/services/aigc/image2video/video-synthesis/"
    DETECT_URL = f"{API_BASE}/api/v1/services/aigc/image2video/video-synthesis/"
    POLL_BASE = f"{API_BASE}/api/v1/tasks"

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if os.environ.get("DASHSCOPE_API_KEY") else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.5  # ~$0.5 per call (varies by duration)

    def _is_url(self, s: str) -> bool:
        return s.startswith("http://") or s.startswith("https://") or s.startswith("oss://")

    def _upload_to_dashscope(self, file_path: str, model: str = "wan2.2-s2v") -> str:
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        fp = Path(file_path)
        if not fp.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = fp.suffix.lower()
        allowed_image = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        allowed_audio = {".wav", ".mp3"}
        if ext not in allowed_image | allowed_audio:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {allowed_image | allowed_audio}")

        print(f"  [upload] Getting upload credentials for {fp.name}...")
        r = requests.get(
            f"{self.API_BASE}/api/v1/uploads",
            params={"action": "getPolicy", "model": model},
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Failed to get upload policy: {r.status_code} {r.text[:300]}")
        cred = r.json().get("data", {})

        upload_host = cred["upload_host"]
        upload_dir = cred["upload_dir"]
        policy = cred["policy"]
        signature = cred["signature"]
        oss_key = cred["oss_access_key_id"]
        acl = cred["x_oss_object_acl"]
        forbid_overwrite = cred["x_oss_forbid_overwrite"]

        object_key = f"{upload_dir}/{fp.name}"

        print(f"  [upload] Uploading to OSS...")
        with open(fp, "rb") as f:
            files = {
                "OSSAccessKeyId": (None, oss_key),
                "policy": (None, policy),
                "Signature": (None, signature),
                "key": (None, object_key),
                "x-oss-object-acl": (None, acl),
                "x-oss-forbid-overwrite": (None, forbid_overwrite),
                "success_action_status": (None, "200"),
                "file": (fp.name, f, "application/octet-stream"),
            }
            ur = requests.post(upload_host, files=files, timeout=120)
            if ur.status_code not in (200, 201, 204):
                raise RuntimeError(f"OSS upload failed: {ur.status_code} {ur.text[:300]}")

        oss_url = f"oss://{object_key}"
        print(f"  [upload] OK -> {oss_url}")
        return oss_url

    def _resolve_file(self, path_or_url: str, purpose: str) -> tuple[str, bool]:
        if self._is_url(path_or_url):
            return path_or_url, False
        oss_url = self._upload_to_dashscope(path_or_url)
        return oss_url, True

    def _detect_image(self, image_url: str, use_oss_header: bool) -> bool:
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        body = {
            "model": "wan2.2-s2v-detect",
            "input": {"image_url": image_url},
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if use_oss_header:
            headers["X-DashScope-OssResourceResolve"] = "enable"

        r = requests.post(self.DETECT_URL, headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            print(f"  [detect] WARNING: detection failed ({r.status_code}), proceeding anyway")
            return True
        data = r.json()
        status = data.get("output", {}).get("task_status", "")
        if status == "SUCCEEDED":
            print(f"  [detect] Image check passed")
            return True
        else:
            print(f"  [detect] WARNING: {data.get('output', {}).get('message', 'unknown issue')}, proceeding anyway")
            return True

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return ToolResult(success=False, error="DASHSCOPE_API_KEY not set")
        start = time.time()
        try:
            image_input = inputs["image"]
            audio_input = inputs["audio"]
            style = inputs.get("style", "speech")
            resolution = inputs.get("resolution", "480P")
            output_path = inputs.get("output_path", f"digital_human_{int(time.time())}.mp4")

            resolve_oss = False

            print(f"  [s2v] Resolving image...")
            if self._is_url(image_input):
                image_url = image_input
            else:
                image_url, _ = self._resolve_file(image_input, "image")
                resolve_oss = True

            print(f"  [s2v] Resolving audio...")
            if self._is_url(audio_input):
                audio_url = audio_input
            else:
                audio_url, oss_used = self._resolve_file(audio_input, "audio")
                resolve_oss = resolve_oss or oss_used

            if inputs.get("detect_only"):
                ok = self._detect_image(image_url, resolve_oss)
                return ToolResult(success=ok, data={"detect_passed": ok})

            print(f"  [s2v] Calling wan2.2-s2v ({style}, {resolution})...")
            body = {
                "model": "wan2.2-s2v",
                "input": {
                    "image_url": image_url,
                    "audio_url": audio_url,
                },
                "parameters": {
                    "style": style,
                    "resolution": resolution,
                },
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }
            if resolve_oss:
                headers["X-DashScope-OssResourceResolve"] = "enable"

            r = requests.post(self.S2V_URL, headers=headers, json=body, timeout=60)
            if r.status_code != 200:
                return ToolResult(success=False, error=f"s2v API error {r.status_code}: {r.text[:300]}")
            data = r.json()
            task_id = data.get("output", {}).get("task_id", "")
            if not task_id:
                return ToolResult(success=False, error=f"No task_id: {json.dumps(data, ensure_ascii=False)[:500]}")

            print(f"  [s2v] Task submitted: {task_id}")
            print(f"  [s2v] Polling (this takes ~5-10 min)...")

            poll_url = f"{self.POLL_BASE}/{task_id}"
            for attempt in range(120):
                time.sleep(15)
                pr = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
                pdata = pr.json()
                status = pdata.get("output", {}).get("task_status", "")
                if status == "SUCCEEDED":
                    output = pdata.get("output", {})
                    results = output.get("results", {})
                    video_url = ""
                    if isinstance(results, list) and results:
                        video_url = results[0].get("video_url", "")
                    elif isinstance(results, dict):
                        video_url = results.get("video_url", "")
                    if not video_url:
                        video_url = output.get("video_url", "")
                    if not video_url:
                        return ToolResult(success=False, error="No video_url in response")
                    usage = pdata.get("usage", {})
                    print(f"  [s2v] Generated! Downloading...")
                    vr = requests.get(video_url, timeout=300)
                    outpath = Path(output_path)
                    outpath.parent.mkdir(parents=True, exist_ok=True)
                    outpath.write_bytes(vr.content)
                    dur = usage.get("duration", 0)
                    return ToolResult(success=True, data={
                        "provider": "dashscope",
                        "model": "wan2.2-s2v",
                        "task_id": task_id,
                        "output_path": str(outpath),
                        "file_size_bytes": len(vr.content),
                        "duration_seconds": dur,
                        "resolution": resolution,
                        "style": style,
                    })
                elif status in ("FAILED",):
                    err = pdata.get("output", {}).get("error", {}).get("message", str(pdata)[:300])
                    return ToolResult(success=False, error=f"s2v failed: {err}")
                if attempt % 8 == 0:
                    print(f"  [s2v] ...still processing ({status})...")
            return ToolResult(success=False, error=f"Timeout polling task {task_id}")
        except Exception as e:
            return ToolResult(success=False, error=f"DashScope s2v error: {e}")
