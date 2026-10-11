import asyncio
import datetime
import json
import sys
from pathlib import Path

import edge_tts

WORK = Path(__file__).resolve().parent
VOICE = "zh-HK-HiuMaanNeural"  # 微软香港粤语女声，标准港粤
RATE = "+20%"


async def synthesize(text: str, out: Path):
    c = edge_tts.Communicate(text, voice=VOICE, rate=RATE)
    await c.save(str(out))


async def main():
    date_label = sys.argv[1] if len(sys.argv) > 1 else "2026-07-31"
    year, month, day = date_label.split("-")
    weekday = "星期" + "一二三四五六日"[
        datetime.date(int(year), int(month), int(day)).weekday()]

    # 6 scenes, each with: clip id, duration, screen text, narration
    # NOTE: scene 1 screen text = date broadcast (numeric, bold on screen);
    # make_overlays.py renders numeric text in msyhbd bold automatically.
    scenes = [
        {"clip": "guangzhou_canton_tower", "dur": 2.2,
         "text": "7/31", "narration": "早晨呀！"},
        {"clip": "guangzhou_temple", "dur": 2.2,
         "text": f"今日係 {int(month)}月{int(day)}號 {weekday}", "narration": f"今日係{int(month)}月{int(day)}號，{weekday}。"},
        {"clip": "guangzhou_pearl_river", "dur": 2.2,
         "text": f"{int(month)}月嘅最後一日", "narration": f"{int(month)}月嘅最後一日啦！"},
        {"clip": "guangzhou_city_street", "dur": 2.2,
         "text": "唔好逼自己 事事圓滿", "narration": "唔好逼自己，事事圓滿。"},
        {"clip": "guangzhou_river", "dur": 2.2,
         "text": "你帶住瑕疵 向前行", "narration": "帶住瑕疵向前行，好靚！"},
        {"clip": "guangzhou_night", "dur": 2.6,
         "text": "早已勝過 原地猶豫嘅人", "narration": "早已勝過原地猶豫嘅人！"},
    ]

    script = {"date": date_label, "weekday": weekday, "scenes": scenes}
    (WORK / "artifacts" / "greeting_script.json").write_text(
        json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    for i, sc in enumerate(scenes):
        out = WORK / "assets" / "audio" / f"line_{i + 1}.mp3"
        if not out.exists():
            try:
                await synthesize(sc["narration"], out)
                print(f"TTS OK line_{i + 1}: {sc['narration']}")
            except Exception as e:
                print(f"TTS FAIL line_{i + 1}: {e}")
                sys.exit(1)
        else:
            print(f"TTS cached line_{i + 1}")

    script["tts"] = {"engine": "edge-tts", "voice": VOICE, "rate": RATE}
    (WORK / "artifacts" / "greeting_script.json").write_text(
        json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    print("-> artifacts/greeting_script.json")


if __name__ == "__main__":
    asyncio.run(main())
