import json
import subprocess
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent
FFMPEG = str(ROOT / "projects" / "why-sky-blue" / "node_modules" / "@ffmpeg-installer" / "win32-x64" / "ffmpeg.exe")
FFPROBE = str(ROOT / "projects" / "why-sky-blue" / "node_modules" / "@ffprobe-installer" / "win32-x64" / "ffprobe.exe")
TMP = WORK / "renders" / "tmp_v7"
TMP.mkdir(parents=True, exist_ok=True)
W, H = 1280, 720
FPS = 30
TEXT_DELAY = 0.15
XFADE = 0.22

# scene -> video asset + camera motion (zoom in/out + drift + focal point)
VIDEOS = [
    ("guangzhou_canton_tower", 1.0, 1.10, 0, 0.42),    # tower, gentle push-in, upper center
    ("v6_s2_bridge_37202553", 1.12, 1.02, -30, 0.5),   # bridge across river, pull-out, drift left
    ("v6_s3_bridge_night_36809520", 1.0, 1.08, 25, 0.5),  # night bridge, push-in, drift right
    ("v6_s4_night_skyline_32905188", 1.10, 1.0, 0, 0.5),  # night landmark, pull-out
    ("v6_s5_street_walk_19329334", 1.0, 1.12, -20, 0.48),  # pedestrian silhouettes, push-in
    ("v6_s6_dusk_skyline_2818567", 1.12, 1.03, 20, 0.5),   # dusk skyline, pull-out, drift right
]

date_label = sys.argv[1] if len(sys.argv) > 1 else "2026-07-31"


def run(args, label):
    print(f"  [{label}]")
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-1800:])
        sys.exit(f"FAILED: {label}")


def dur(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    sc = json.loads((WORK / "artifacts" / "greeting_script.json").read_text(encoding="utf-8"))
    scenes = sc["scenes"]
    durs = [s["dur"] for s in scenes]
    starts = []
    t = 0
    for d in durs:
        starts.append(t)
        t += d
    total = t
    print(f"  scenes: {durs}  total {total:.2f}s")

    # ---- 1. per scene: source video -> Ken Burns crop -> subtitle overlay ----
    segs = []
    for i, s in enumerate(scenes):
        vid, z0, z1, drift, cy = VIDEOS[i]
        src = WORK / "assets" / "video" / f"{vid}.mp4"
        anim = WORK / "assets" / "overlays" / f"anim_{i + 1}" / "f%04d.png"
        out = TMP / f"seg{i}.mp4"
        n_frames = int(round(durs[i] * FPS))
        zexpr = f"min({z1},{z0}+({z1}-{z0})*on/{n_frames})"
        vf = (
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop=1920:1080,fps={FPS},"
            f"zoompan=z='{zexpr}':"
            f"x='min(iw-iw/zoom,max(0,iw/2-(iw/zoom/2)+{drift}/zoom))':"
            f"y='min(ih-ih/zoom,max(0,ih*{cy}-(ih/zoom/2)))':"
            f"d=1:s={W}x{H}:fps={FPS},"
            f"fade=t=in:st=0:d={XFADE},"
            f"fade=t=out:st={durs[i] - XFADE:.2f}:d={XFADE}[base];"
            f"[1:v]format=rgba,setpts=PTS-STARTPTS[ov];"
            f"[base][ov]overlay=0:0,format=yuv420p"
        )
        if not out.exists():
            run([FFMPEG, "-y", "-i", str(src),
                 "-i", str(anim),
                 "-filter_complex", vf,
                 "-t", str(durs[i]),
                 "-r", str(FPS),
                 "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-an",
                 str(out)], f"scene {i + 1} ({vid})")
        segs.append(out)

    # ---- 2. concat ----
    lst = TMP / "concat.txt"
    lst.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in segs), encoding="utf-8")
    VIDEO = TMP / "video.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(VIDEO)],
        "concat scenes")

    # ---- 3. audio: narration at scene starts + BGM ----
    offsets = [s + TEXT_DELAY for s in starts]
    inputs = []
    fc = []
    for i, off in enumerate(offsets):
        ms = int(off * 1000)
        inputs += ["-i", str(WORK / "assets" / "audio" / f"line_{i + 1}.mp3")]
        fc.append(f"[{i}:a]aresample=44100,adelay={ms}|{ms}[n{i}]")

    bgm = WORK / "assets" / "music" / "bgm_test.mp3"
    if bgm.exists():
        inputs += ["-i", str(bgm)]
        n = len(scenes)
        fc.append(f"[{n}:a]atrim=0:{total},afade=t=in:st=0:d=1,afade=t=out:st={total - 2.5:.2f}:d=2.5,"
                  f"lowpass=f=900,volume=0.32[music]")
        mix_in = "".join(f"[n{i}]" for i in range(n)) + "[music]"
        nin = n + 1
    else:
        mix_in = "".join(f"[n{i}]" for i in range(n))
        nin = n

    fc.append(f"{mix_in}amix=inputs={nin}:duration=longest:dropout_transition=1,"
              f"volume={nin * 0.85},alimiter=limit=0.95[a]")

    MIXED = TMP / "mixed.wav"
    run([FFMPEG, "-y"] + inputs + ["-filter_complex", ";".join(fc),
                                   "-map", "[a]", "-acodec", "pcm_s16le", str(MIXED)], "mix audio")

    # ---- 4. final with fade in/out ----
    FINAL = WORK / "renders" / f"morning-greeting-v7-{date_label}.mp4"
    run([FFMPEG, "-y", "-i", str(VIDEO), "-i", str(MIXED),
         "-filter_complex", f"fade=t=in:st=0:d=0.3,fade=t=out:st={total - 0.5:.2f}:d=0.5",
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(FINAL)], "finalize")

    d = dur(FINAL)
    s = FINAL.stat().st_size
    print(f"\n{'=' * 60}")
    print(f"  FINAL: {FINAL}")
    print(f"  {d:.1f}s, {s / 1024 / 1024:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

