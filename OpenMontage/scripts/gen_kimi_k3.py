import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['PATH'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Scripts') + os.pathsep + os.environ.get('PATH', '')

from tools.graphics.dashscope_image import DashscopeImage
from tools.audio.dashscope_tts import DashscopeTTS
import json, subprocess
from pathlib import Path

BASE = Path('projects/kimi-k3-promo')
IMGDIR = BASE / 'assets' / 'images'
AUDDIR = BASE / 'assets' / 'audio'
RENDER = BASE / 'renders'
IMGDIR.mkdir(parents=True, exist_ok=True)
AUDDIR.mkdir(parents=True, exist_ok=True)
RENDER.mkdir(parents=True, exist_ok=True)

# Scene image prompts
scenes = [
    ('sc1', '深邃宇宙空间中，一道金色光芒划破黑暗，光芒中浮现立体K3标志，科技感蓝色调，电影级光影，极简构图，8K高清', 0, 5),
    ('sc2', '抽象神经网络在暗色背景中发光，蓝色数据流如星辰般交错流动，思维脉络可视化，赛博朋克风格，超现实', 5, 13),
    ('sc3', '多模态信息交汇中心，文字、代码、图像数据融合成光球，全息投影风格，深色背景，科技感未来主义', 13, 22),
    ('sc4', '黑暗中的无数光点汇聚成一轮明月，月光下浮现品牌标语，极简构图，深邃静谧，电影级光影', 22, 30),
]

# Step 1: Generate images
img = DashscopeImage()
print('=== Generating images with DashScope ===')
scene_images = []
for sid, prompt, start, end in scenes:
    outpath = str(IMGDIR / f'{sid}.png')
    print(f'  {sid}: generating...')
    result = img.execute({
        'prompt': prompt,
        'size': '1920*1080',
        'n': 1,
        'output_path': outpath,
    })
    if result.success:
        print(f'  {sid}: OK -> {result.data.get("output")}')
        scene_images.append((sid, result.data.get("output"), start, end))
    else:
        print(f'  {sid}: FAIL -> {result.error}')

# Step 2: Generate TTS narration (Mandarin)
tts = DashscopeTTS()
print('\n=== Generating TTS narration ===')
narration_segments = [
    ('s1', '这不是一次简单的升级。', 0, 5, 0),
    ('s2', 'Kimi K3，月之暗面最新力作。万亿参数级智能，在每一次对话中觉醒。', 5, 13, 5),
    ('s3', '超长上下文，深度推理，多模态理解。不是更快的回答，而是更深的思考。', 13, 22, 13),
    ('s4', 'Kimi K3。探索智能的边界，点亮未知的暗面。', 22, 30, 22),
]

tts_segments = []
for sid, text, start, end, offset in narration_segments:
    outpath = str(AUDDIR / f'{sid}.wav')
    print(f'  {sid}: synthesizing...')
    result = tts.execute({
        'text': text,
        'model': 'qwen3-tts-flash',
        'voice': 'Cherry',
        'output_path': outpath,
    })
    if result.success:
        print(f'  {sid}: OK -> {result.data.get("output")}')
        tts_segments.append((sid, str(result.data.get("output")), start, end, offset))
    else:
        print(f'  {sid}: FAIL -> {result.error}')

print('\n=== Generation complete ===')
print(f'Images: {len(scene_images)} generated')
print(f'TTS segments: {len(tts_segments)} generated')
