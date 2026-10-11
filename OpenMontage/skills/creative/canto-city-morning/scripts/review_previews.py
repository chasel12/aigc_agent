import base64
import json
import os
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(WORK.parent.parent))
from lib.env_loader import load_env
load_env()

import requests

API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
KEY = os.environ["DASHSCOPE_API_KEY"]
TOPN = 4


def describe(path: str) -> str:
    img = base64.b64encode(Path(path).read_bytes()).decode()
    payload = {
        "model": "qwen-vl-max",
        "input": {"messages": [{"role": "user", "content": [
            {"image": f"data:image/jpeg;base64,{img}"},
            {"text": ("视频封面帧。简短判断(中文，每项≤12字): 1主体 2光线时间 3构图(专业摄影感/普通随手拍/看不清) "
                      "4画面动感 5氛围(积极/松弛/压抑/市井/都市)。")}
        ]}]},
    }
    r = requests.post(API, headers={"Authorization": f"Bearer {KEY}",
                                    "Content-Type": "application/json"}, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["output"]["choices"][0]["message"]["content"][0]["text"]


def main():
    workdir = sys.argv[1] if len(sys.argv) > 1 else "."
    wd = Path(workdir).resolve()
    files = sorted((wd / "analysis" / "previews").glob("*.jpg"))
    by_query = {}
    for f in files:
        q = f.name.rsplit("_", 1)[0]
        by_query.setdefault(q, []).append(f)
    selected = [f for fs in by_query.values() for f in fs[:TOPN]]
    print(f"{len(files)} previews -> {len(selected)} to review")

    results = []
    for f in selected:
        try:
            txt = describe(str(f))
            results.append({"file": f.name, "vision": txt})
            print(f"=== {f.name}")
            print(txt)
        except Exception as e:
            results.append({"file": f.name, "error": str(e)})
            print(f"=== {f.name} ERROR {e}")

    (wd / "analysis" / "preview_vision.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("->", wd / "analysis" / "preview_vision.json")


if __name__ == "__main__":
    main()
