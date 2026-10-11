"""Generate AI video clips from Kimi K3 images via DashScope Wan2.6-i2v-flash."""
import sys, os, json, time, base64, subprocess, requests as req
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

ASSETS = Path('projects/kimi-k3-promo/assets')
IMGDIR = ASSETS / 'images'
VIDDIR = ASSETS / 'video'
VIDDIR.mkdir(parents=True, exist_ok=True)

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
    'X-DashScope-Async': 'enable',
}
API_URL = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis'

# Scene prompts for image-to-video
scenes = [
    ('sc1.png', '镜头缓缓拉近，机器人头部微微转动，眼睛发出柔和的蓝色脉冲光芒，背景粒子缓缓流动'),
    ('sc2.png', '画面中Kimi K3的界面元素柔和闪烁，数据流沿着线条流动，整体呈现高级科技感'),
    ('sc3.png', '深度推理的网络节点图像微微发光，线条流动传递信息，展现AI思考过程'),
    ('sc4.png', '代码在屏幕上逐行滚动浮现，光影在界面间缓慢移动，营造编程氛围'),
]

# Reduce image size with ffmpeg before sending
FFMPEG = str(Path('.venv/Scripts/ffmpeg.exe').resolve())
MAX_SIZE_KB = 500  # Keep images under 500KB

generated_videos = []

for i, (img_name, prompt) in enumerate(scenes):
    src = IMGDIR / img_name
    small_img = VIDDIR / f'sc{i+1}_small.jpg'
    
    # Compress image
    subprocess.run([
        FFMPEG, '-y', '-i', str(src),
        '-vf', 'scale=960:-1',
        '-q:v', '15',  # lower quality for small size
        str(small_img)
    ], check=True, capture_output=True)
    
    img_size = small_img.stat().st_size
    print(f'\n=== Scene {i+1}: {img_name} ({img_size//1024}KB) ===')
    
    with open(str(small_img), 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    img_data_url = f'data:image/jpeg;base64,{img_b64}'
    
    body = {
        'model': 'wan2.6-i2v-flash',
        'input': {
            'prompt': prompt,
            'img_url': img_data_url,
        },
        'parameters': {
            'resolution': '720P',
            'duration': 5,
            'prompt_extend': True,
            'watermark': False,
        }
    }
    
    try:
        r = req.post(API_URL, headers=headers, json=body, timeout=120)
        if r.status_code != 200:
            print(f'  API Error: {r.status_code} {r.text[:200]}')
            continue
        
        data = r.json()
        task_id = data.get('output', {}).get('task_id', '')
        if not task_id:
            print(f'  No task_id: {data}')
            continue
        
        print(f'  Task: {task_id}')
        
        # Poll for result
        poll_url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
        for poll_i in range(60):
            time.sleep(10)
            pr = req.get(poll_url, headers=headers, timeout=30)
            pdata = pr.json()
            status = pdata.get('output', {}).get('task_status', 'unknown')
            print(f'    [{poll_i*10}s] {status}')
            
            if status == 'SUCCEEDED':
                output = pdata.get('output', {})
                video_url = output.get('video_url', '') or output.get('result', {}).get('video_url', '')
                if video_url:
                    vr = req.get(video_url, timeout=120)
                    outpath = VIDDIR / f'ai_scene_{i+1}.mp4'
                    with open(str(outpath), 'wb') as f:
                        f.write(vr.content)
                    print(f'  Downloaded: {outpath.name} ({len(vr.content)//1024}KB)')
                    generated_videos.append(str(outpath))
                break
            elif status in ('FAILED',):
                print(f'  FAILED: {json.dumps(pdata,ensure_ascii=False)[:500]}')
                break
    except Exception as e:
        print(f'  ERROR: {e}')
        continue

print(f'\n=== Generated {len(generated_videos)}/{len(scenes)} videos ===')
for v in generated_videos:
    print(f'  {v}')
