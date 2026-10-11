"""Final composition: 4 AI video clips + 5 TTS + BGM, proper freeze frame."""
import sys, os, subprocess, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path

BASE = Path('projects/kimi-k3-promo')
VID = BASE / 'assets' / 'video'
AUD = BASE / 'assets' / 'audio'
RENDER = BASE / 'renders'
INT = RENDER / 'intermediate'
INT.mkdir(parents=True, exist_ok=True)
FFMPEG = str(Path('.venv/Scripts/ffmpeg.exe').resolve())

w, h, fps = 1920, 1080, 30

def get_dur(path):
    r = subprocess.run([FFMPEG, '-i', str(path)], capture_output=True, text=True)
    for line in r.stderr.split('\n'):
        if 'Duration' in line:
            m = re.search(r'(\d+):(\d+):(\d+\.\d+)', line)
            if m: return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
    return 5.0

# Assets
ai_clips = [VID / f'ai_scene_{i+1}.mp4' for i in range(4)]
audio_files = [AUD / f's{i}.wav' for i in range(1, 6)]
total_audio = sum(get_dur(a) for a in audio_files)
total_video = sum(get_dur(c) for c in ai_clips)
print(f'Audio: {total_audio:.1f}s, AI clips: {total_video:.1f}s')

# Step 1: Scale each AI clip to 1920x1080 (same framerate) with fade
scaled = []
for i, clip in enumerate(ai_clips):
    out = RENDER / f'intermediate/ai_scale_{i}.mp4'
    d = get_dur(clip)
    fade_d = 0.4
    vf = (
        f'scale={w}:{h}:force_original_aspect_ratio=decrease,'
        f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,'
        f'fade=t=in:st=0:d={fade_d},'
        f'fade=t=out:st={d-fade_d}:d={fade_d}'
    )
    subprocess.run([FFMPEG, '-y', '-i', str(clip),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-vf', vf, '-r', '30', '-preset', 'fast', '-crf', '23', '-an',
        str(out)], check=True, capture_output=True)
    scaled.append(out)
    print(f'  Scale {i}: {d}s -> {w}x{h} @30fps')

# Step 2: Concat scaled clips
concat_list = RENDER / 'intermediate/concat_list.txt'
with open(str(concat_list), 'w') as f:
    for s in scaled:
        f.write(f"file '{s.resolve()}'\n")
video_12 = RENDER / 'intermediate/video_12.mp4'
subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_list), '-c', 'copy', str(video_12)], check=True, capture_output=True)

# Step 3: If audio longer, create loop of last frame
need = total_audio - total_video
if need > 0:
    # Extract last frame as png
    last_frame = RENDER / 'intermediate/last_frame.png'
    subprocess.run([FFMPEG, '-y', '-sseof', '-0.04', '-i', str(video_12), '-vframes', '1', '-update', '1', str(last_frame)], check=True, capture_output=True)
    # Loop it with fade in
    freeze = RENDER / 'intermediate/freeze.mp4'
    subprocess.run([FFMPEG, '-y', '-loop', '1', '-i', str(last_frame),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-vf', f'fade=t=in:st=0:d=0.5,setpts=PTS-STARTPTS',
        '-r', '30', '-preset', 'fast', '-crf', '23',
        '-t', str(need + 0.5),
        str(freeze)], check=True, capture_output=True)
    # Concat
    concat2 = RENDER / 'intermediate/concat_list2.txt'
    with open(str(concat2), 'w') as f:
        f.write(f"file '{video_12.resolve()}'\n")
        f.write(f"file '{freeze.resolve()}'\n")
    video_final_no_audio = RENDER / 'intermediate/video_final_no_audio.mp4'
    subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(concat2), '-c', 'copy', str(video_final_no_audio)], check=True, capture_output=True)
else:
    video_final_no_audio = video_12

video_dur = get_dur(video_final_no_audio)
print(f'Video duration: {video_dur:.1f}s (need {need:.1f}s extra)')

# Step 4: Merge audio segments
audio_list = RENDER / 'intermediate/audio_list.txt'
with open(str(audio_list), 'w') as f:
    for a in audio_files:
        f.write(f"file '{a.resolve()}'\n")
merged_audio = RENDER / 'intermediate/audio_merged.wav'
subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(audio_list), '-c', 'copy', str(merged_audio)], check=True, capture_output=True)

# Step 5: BGM
bgm = RENDER / 'intermediate/bgm.aac'
subprocess.run([FFMPEG, '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
    '-t', str(total_audio+1),
    '-af', 'aecho=0.8:0.9:1000:0.3,volume=0.10',
    '-c:a', 'aac', '-b:a', '128k', str(bgm)], check=True, capture_output=True)

# Step 6: Mix
mixed = RENDER / 'intermediate/audio_mixed.wav'
subprocess.run([FFMPEG, '-y', '-i', str(merged_audio), '-i', str(bgm),
    '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2',
    '-c:a', 'pcm_s16le', str(mixed)], check=True, capture_output=True)

# Step 7: Final compose
final = RENDER / 'kimi-k3-promo-ai.mp4'
subprocess.run([
    FFMPEG, '-y', '-i', str(video_final_no_audio), '-i', str(mixed),
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
    '-shortest', '-map', '0:v:0', '-map', '1:a:0', str(final)
], check=True, capture_output=True)

size = os.path.getsize(str(final))
print(f'\nDone! {final} ({size/1024/1024:.1f}MB)')
