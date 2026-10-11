import json
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent
FFPROBE = str(ROOT / "projects" / "why-sky-blue" / "node_modules" / "@ffprobe-installer" / "win32-x64" / "ffprobe.exe")
W, H = 1280, 720
FPS = 30

# 主字体：默陌专辑手写体（硬笔手写连笔）；回退1：方正舒体（行书连笔）；回退2：华文楷体（仅补嘅）
FONTS = [
    str(WORK / "assets" / "fonts" / "momo_raw.bin"),
    "C:/Windows/Fonts/FZSTK.TTF",
    "C:/Windows/Fonts/STKAITI.TTF",
]
# 7/31 日期播报：粗体数字
FONT_NUM = "C:/Windows/Fonts/msyhbd.ttc"

OUT = WORK / "assets" / "overlays"
TEXT_DELAY = 0.15
FADE_IN = 0.45
FADE_OUT = 0.45
HOLD_SCALE = 1.0
START_SCALE = 0.88
GAP = 0.3
MIN_DUR = 1.8

ANCHORS = [
    (0.50, 0.46),  # scene 1: 7/31 日期播报，居中
    (0.50, 0.28),  # scene 2: date badge center-upper
    (0.38, 0.52),  # scene 3: 7月嘅最後一日 left-mid
    (0.66, 0.78),  # scene 4: 唔好逼自己 bottom-right
    (0.42, 0.80),  # scene 5: 帶住瑕疵向前行 bottom-left
    (0.50, 0.34),  # scene 6: 早已勝過 center-upper
]

_font_cache = {}
_cmaps = None


def get_cmaps():
    global _cmaps
    if _cmaps is None:
        _cmaps = []
        for p in FONTS:
            f = TTFont(p, lazy=True)
            _cmaps.append(f.getBestCmap())
    return _cmaps


def load_font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def pick_font(ch, size):
    for cmap, path in zip(get_cmaps(), FONTS):
        if ord(ch) in cmap:
            return load_font(path, size)
    return load_font(FONTS[2], size)


def dur(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def ease(frac):
    return frac * frac * (3 - 2 * frac)


def render_text_block(text, size):
    lines = [ln for ln in text.split(" ") if ln]
    widths = []
    for ln in lines:
        w = 0.0
        for ch in ln:
            f = pick_font(ch, size)
            w += f.getlength(ch)
        widths.append(int(w))
    tw, th = int(max(widths)), len(lines) * int(size * 1.35)
    img = Image.new("RGBA", (tw + 24, th + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 12
    for ln, wdt in zip(lines, widths):
        x = (tw - wdt) / 2 + 12
        for ch in ln:
            f = pick_font(ch, size)
            d.text((x, y), ch, font=f, fill=(255, 255, 255, 255))
            x += f.getlength(ch)
        y += int(size * 1.35)
    return img


def add_shadow(text_img, blur=16, dy=7, alpha=235):
    pad = blur * 2 + 6
    canvas = Image.new("RGBA", (text_img.width + pad * 2, text_img.height + pad * 2 + dy),
                       (0, 0, 0, 0))
    alpha_mask = text_img.split()[3]
    sh = Image.new("RGBA", text_img.size, (0, 0, 0, 0))
    sh.putalpha(alpha_mask.point(lambda p: min(p, alpha)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh, (pad, pad + dy))
    canvas.alpha_composite(text_img, (pad, pad))
    return canvas


def make_base(text, big=False, numeric=False):
    if numeric:
        size = 148
        f = ImageFont.truetype(FONT_NUM, size)
        w = int(f.getlength(text))
        h = int(size * 1.25)
        img = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text(((w - f.getlength(text)) / 2 + 12, 12), text, font=f, fill=(255, 255, 255, 255))
        return add_shadow(img)
    size = 104 if big else (84 if len(text) <= 6 else 68)
    t = render_text_block(text, size)
    return add_shadow(t)


def is_numeric(text):
    return bool(text) and all(c in "0123456789/" for c in text)


def render_frames(base, dur, outdir, cx, cy):
    n = int(round(dur * FPS))
    outdir.mkdir(parents=True, exist_ok=True)
    bw, bh = base.size
    for f in range(n):
        t = f / FPS
        if t < TEXT_DELAY:
            k, a = START_SCALE, 0
        elif t < TEXT_DELAY + FADE_IN:
            p = ease((t - TEXT_DELAY) / FADE_IN)
            k = START_SCALE + (HOLD_SCALE - START_SCALE) * p
            a = p
        elif t > dur - FADE_OUT:
            p = ease((dur - t) / FADE_OUT)
            k = HOLD_SCALE
            a = p
        else:
            k, a = HOLD_SCALE, 1
        scaled = base.resize((int(bw * k), int(bh * k)), Image.LANCZOS)
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sx = int(cx - scaled.width / 2)
        sy = int(cy - scaled.height / 2)
        frame.paste(scaled, (sx, sy), scaled)
        if a < 1:
            alpha = frame.split()[3].point(lambda p: int(p * a))
            frame.putalpha(alpha)
        frame.save(outdir / f"f{f:04d}.png")


def main():
    sc = json.loads((WORK / "artifacts" / "greeting_script.json").read_text(encoding="utf-8"))
    narr = [dur(WORK / "assets" / "audio" / f"line_{i + 1}.mp3") for i in range(len(sc["scenes"]))]
    durs = [max(MIN_DUR, n + GAP) for n in narr]
    for s, d in zip(sc["scenes"], durs):
        s["dur"] = round(d, 2)
    (WORK / "artifacts" / "greeting_script.json").write_text(
        json.dumps(sc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"scene durs: {durs}  total {sum(durs):.2f}s")

    for i, s in enumerate(sc["scenes"]):
        cx, cy = int(ANCHORS[i][0] * W), int(ANCHORS[i][1] * H)
        if i == 0 and is_numeric(s["text"]):
            base = make_base(s["text"], numeric=True)
        else:
            base = make_base(s["text"], big=(i == 1))
        render_frames(base, s["dur"], OUT / f"anim_{i + 1}", cx, cy)
        print(f"anim_{i + 1}: {s['text']} at {(cx, cy)}")


if __name__ == "__main__":
    main()
