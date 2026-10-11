"""Pexels footage pipeline for the Canto city-morning skill.

Usage (from a project workspace):
    python find_footage.py "guangzhou aerial city" "city skyline sunrise aerial" ...

Steps:
    1. search Pexels video API per query (landscape), record top 10 per query
    2. download preview JPEGs to analysis/previews/
    3. run Qwen-VL review (separate, see SKILL.md) to pick scene ids
    4. edit PICK below (name -> video id), re-run to download selected 4K clips
       to assets/video/<prefix>_<name>_<id>.mp4
"""
import json
import os
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent
for cand in [WORK.parent.parent.parent.parent, WORK.parent.parent, Path.cwd().parent]:
    if (cand / "lib" / "env_loader.py").exists():
        sys.path.insert(0, str(cand))
        break

from lib.env_loader import load_env
load_env()

import requests

KEY = os.environ["PEXELS_API_KEY"]
HEADERS = {"Authorization": KEY}
PREFIX = "v6"  # asset name prefix


def search(queries, out_json="artifacts/video_candidates.json"):
    out = {}
    for q in queries:
        r = requests.get("https://api.pexels.com/videos/search",
                         params={"query": q, "orientation": "landscape", "per_page": 10},
                         headers=HEADERS, timeout=30)
        r.raise_for_status()
        items = []
        for v in r.json().get("videos", []):
            files = sorted(v["video_files"], key=lambda f: f.get("width") or 0, reverse=True)
            best = files[0]
            pics = v.get("video_pictures") or []
            items.append({
                "id": v["id"], "w": best.get("width"), "h": best.get("height"),
                "dur": v.get("duration"), "url": best.get("link"),
                "preview": pics[0]["picture"] if pics else None,
            })
        out[q] = items
        print(f"{q}: {len(items)} candidates")
    Path(out_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def download_previews(cands, outdir="analysis/previews"):
    outdir = WORK / outdir
    outdir.mkdir(parents=True, exist_ok=True)
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}
    for q, items in cands.items():
        for it in items:
            p = outdir / f"{q.replace(' ', '_')}_{it['id']}.jpg"
            if p.exists():
                continue
            r = requests.get(it["preview"], headers=UA, timeout=30)
            if r.status_code == 200 and r.content[:3] == b"\xff\xd8\xff":
                p.write_bytes(r.content)
    print("previews in", outdir)


def download_picked(cands, pick, outdir="assets/video"):
    """pick: {name: video_id}. Only clips >= 2560px wide are saved."""
    outdir = WORK / outdir
    outdir.mkdir(parents=True, exist_ok=True)
    ids = {vid: name for name, vid in pick.items()}
    for items in cands.values():
        for it in items:
            if it["id"] in ids and it["w"] and it["w"] >= 2560:
                name = ids[it["id"]]
                dest = outdir / f"{PREFIX}_{name}_{it['id']}.mp4"
                if dest.exists() and dest.stat().st_size > 1000000:
                    print("exists", dest.name)
                    continue
                print("downloading", name, it["id"], it["w"], "x", it["h"])
                r = requests.get(it["url"], timeout=300)
                dest.write_bytes(r.content)
                print("  saved", dest.stat().st_size)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cands = search(sys.argv[1:])
    download_previews(cands)
    # After Qwen-VL review of analysis/previews/*, set PICK below and re-run:
    #   python find_footage.py --pick
    if sys.argv[1] == "--pick":
        PICK = {
            # "scene_name": 1234567,
        }
        download_picked(cands, PICK)
