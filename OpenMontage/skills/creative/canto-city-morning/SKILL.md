# Canto City Morning — 粤语城市早安短视频 (Layer 2 Creative Skill)

> Frozen from `morning-greeting-01` v7, rendered 2026-07-31 (17.0s, 1280x720, ~11MB).
> This is the **only** skill for the 粤语城市早安/励志类 format. Keep it in sync with what the user approves.

## When to Use

Producing a 10-20s Cantonese morning-greeting / short motivational video for Douyin:
landscape 1280x720, standard Hong Kong Cantonese TTS, 4K city footage with
photography-grade composition, handwriting-style connected-script subtitles with
PPT scale fade animations. Trigger phrases: "粤语早安", "早晨问候视频", "励志文案".

## Format Spec (verified, do not change without user sign-off)

| Aspect | Value |
|---|---|
| Canvas / fps | 1280x720, 30fps, H.264 crf 20, ~17s |
| Duration budget | 6 scenes, narration + 0.3s gap each, min 1.8s; total 15-20s |
| TTS | edge-tts `zh-HK-HiuMaanNeural`, rate `+20%`, mp3 per line |
| Narration structure | hook (问候) → date (当日真实日期) → 2-3 emotional lines → closing uplift |
| Scene count | 6 |
| Footage | Pexels videos, ≥2560px wide, landscape, one camera per scene |
| Camera | gentle Ken Burns on 4K (zoom 1.0↔1.12 push/pull alternating + lateral drift) |
| Transitions | black-dip fade 0.22s per edge, fade in/out 0.3/0.5s |
| Subtitle animation | 0.15s delay → 0.45s scale 88%→100% ease-out smoothstep → hold → 0.45s fade-out |
| Subtitle style | **white text, NO stroke, NO background plate**; layered gaussian shadow (blur 16, alpha 235, dy 7) for legibility |
| Subtitle positions | varied anchors per scene, avoid subject (s1 center, s2 upper-center, s3 left-mid, s4 bottom-right, s5 bottom-left, s6 upper-center) |
| Scene 1 subtitle | date broadcast `7/31` — bold digits (msyhbd.ttc 148px), centered |
| BGM | lowpass=900, volume 0.32, fade in 1s / out 2.5s |

## Prerequisites

| Resource | Where |
|---|---|
| Core scripts | `scripts/build_tts.py`, `scripts/make_overlays.py`, `scripts/compose.py`, `scripts/find_footage.py` — copy into the project workspace root |
| Fonts | `assets/fonts/momo_raw.bin` (默陌专辑手写体, fontowns downf 1230298); system `C:/Windows/Fonts/FZSTK.TTF` (方正舒体, 行书), `STKAITI.TTF` (华文楷体), `msyhbd.ttc` (粗体数字) |
| Pexels key | `PEXELS_API_KEY` in `.env` (workspace root = OpenMontage root) |
| Qwen-VL | `DASHSCOPE_API_KEY` in `.env` — used for preview + final frame review |
| ffmpeg/ffprobe | `OpenMontage/projects/why-sky-blue/node_modules/@ffmpeg-installer/win32-x64/` |
| edge-tts | pip package, needs network to Microsoft |
| FontTools | `fontTools` pip package (coverage check) |

## Process

### Step 1 — 文案（script）

Write 6 scene lines in the same shape as `build_tts.py`'s `scenes` list:
`{clip, dur, text, narration}`. Rules:

- `text` = what appears on screen (multi-line via single space between phrases),
  `narration` = spoken Cantonese. They may differ slightly (e.g. narration adds 啦/。
  particles) but text must stay close to speech for standard reading.
- Real **today's date** in scene 2 (`今日係 {m}月{d}號 {星期X}`) and scene 3
  (`{m}月嘅最後一日` when it is the last day of the month — otherwise rephrase,
  e.g. `{m}月嘅最後幾日`).
- Traditional characters, Cantonese written conventions (嘅/係/嗰/唔/靚). Every
  line ≤ 12 characters; two short phrases per line reads best.
- Scene 1 text becomes the date broadcast `7/31` on screen (narration keeps the
  greeting). Auto-generated in `make_overlays.py` (i == 0 → `7/31`).

### Step 2 — TTS

`python build_tts.py <date>` — synthesizes `assets/audio/line_{1..6}.mp3` with
`zh-HK-HiuMaanNeural` +20% and writes `artifacts/greeting_script.json`.
Then `python make_overlays.py` probes real narration durations
(`max(1.8, dur + 0.3)`) and writes per-scene `dur` back into the script JSON.

**Verify:** line durations sum ≈ 15s. Total video ≈ 17s.

### Step 3 — Footage

```
python find_footage.py "guangzhou aerial city" "city skyline sunrise aerial" "city street people walking" "pearl river city night" "city night aerial timelapse" "hong kong street morning"
```

- Queries: `<city> aerial / skyline / street / river night` style combos.
  Target 6 distinct camera feelings: tower, bridge day, bridge night, night
  skyline, street walk, dusk skyline.
- Preview JPEGs land in `analysis/previews/`. Batch-review ALL of them with
  Qwen-VL: 主体 / 光线时间 / 构图(专业摄影感?) / 运动感 / 城市归属. Only pick
  "专业摄影感" clips; reject "普通随手拍".
- Mind the light arc across scenes: morning → day → dusk → night reads better
  than random cuts.
- Set `PICK` in `find_footage.py` (name → id) and re-run with `--pick` to
  download ≥2560px clips to `assets/video/v6_<name>_<id>.mp4`.
- Update `VIDEOS` in `scripts/compose.py`: (name, z0, z1, drift, focus_y).
  Alternate push-in / pull-out and drift direction every scene.

### Step 4 — Subtitles (make_overlays.py)

Font chain (fallback by glyph): **默陌专辑手写体 (momo_raw.bin)** →
**方正舒体 FZSTK.TTF** (行书, supplies 係號圓滿帶勝過猶) → **华文楷体 STKAITI.TTF**
(supplies 嘅). No font in the chain is a kaiti-regular look — momo is hard-pen
connected handwriting, FZSTK is semi-cursive; the chain only kicks in for the 9
traditional chars missing from momo. Verify with fontTools before rendering:

```python
from fontTools.ttLib import TTFont
need = "早晨呀今日係7月31號星期五嘅最後一日唔好逼自己事事圓滿你帶住瑕疵向前行早已勝過原地猶豫嘅人7/31"
cmaps = [TTFont(p).getBestCmap() for p in [momo, FZSTK, STKAITI]]
missing = [c for c in need if not any(ord(c) in cm for cm in cmaps)]
assert not missing, missing
```

- First scene: `7/31` in msyhbd.ttc 148px bold, centered — date-broadcast opener.
- **stroke_width = 0** everywhere. Legibility comes from the two-layer shadow.
- ANCHORS: one per scene, varied, clear of the subject.

### Step 5 — Compose

`python compose.py <date>` → per scene: 4K source → scale 1920x1080 →
zoompan (d=1, fps=30, clamped x/y drift, focus_y) → 1280x720 → black-dip
fade 0.22s → overlay anim frames → concat → mix narration (adelay to
scene_start + 0.15s, aresample 44100) + BGM (atrim, fades, lowpass 900,
volume 0.32) → amix dropout → final fade in/out → `renders/morning-greeting-v7-<date>.mp4`.

### Step 6 — Verify (mandatory, Qwen-VL)

Extract 6 frames at scene midpoints, ask Qwen-VL per frame:
主体场景 / 光线 / 字幕逐字转写 / 有无描边或深色背景板 / 构图是否专业.

**Pass criteria (all must hold):**
- Subtitle transcription is exactly correct, incl. 係號嘅圓滿帶勝過猶.
- No stroke, no background plate visible.
- Composition judged professional/photography-grade.
- 7/31 appears in scene 1.

Fail any → fix (usually: re-run make_overlays for layout, or swap footage) and
re-verify. Then play the render for the user.

## Common Pitfalls

- **Simplified fonts always miss 係號嘅圓滿帶勝過猶** (and 嘅 is GBK-only).
  Never silently render simplified forms — the chain above is mandatory.
- Qwen-VL misjudges font *style* (it called STSONG and even WenKai "黑体") — judge
  by transcription correctness, not by its style label.
- Qwen-VL misses text on dark frames sometimes — if a frame transcription is empty,
  re-extract a slightly different timestamp before concluding.
- Dark night footage + white text can look like a "black plate" to Qwen-VL —
  confirm with a second frame before "fixing" a non-bug.
- Pexels `pexels_video.py` tool only returns the first result — go through the
  raw API for candidate shortlists.
- zoompan drift x/y must be clamped (`min(iw-iw/zoom, max(0, ...))`) or frames
  skip on pull-outs.
- zoom beyond ~1.12 on 720p output looks mushy; keep push/pull within 1.0–1.12.
- edge-tts needs network; DashScope CosyVoice Cantonese voices were rejected by
  the user as non-standard — do not swap voice without asking.
- PowerShell: inline `python -c "..."` with quotes breaks — always write a
  temp `.py` file.
- The overlay anims are pre-rendered full-canvas RGBA PNG sequences — any font /
  layout change requires re-running `make_overlays.py` before compose.

## Self-Evaluation (1–5, pass ≥ 4)

| Criterion | 5 = good |
|---|---|
| Narration authentic HK Cantonese, timing tight | voice + rate + adelay all aligned, no clipping |
| Footage professional, light arc coherent | all scenes photography-grade, day→dusk→night arc |
| Subtitles correct incl. traditional chars | transcription verified char-exact |
| No stroke / plate, legible on bright bg | shadow layers carry legibility |
| Motion variety | push/pull/drift alternate, no two scenes identical |
| Run reproducible | scripts from skill copied, dates parameterized |
