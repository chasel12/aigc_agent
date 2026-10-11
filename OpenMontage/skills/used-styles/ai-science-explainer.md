名称: AI多镜头科普短片
英文: AI Multi-Shot Science Explainer
日期: 2026-07-30
项目: 天空为什么是蓝色的 (why-sky-blue)

### 视频参数
- 时长: 38s
- 分辨率: 1280x720 (720P)
- 帧率: 30fps
- 文件大小: ~10MB

### 制作流程
1. **文案脚本** → 6段中文解说词，每段对应一个科学知识点
2. **Wan2.6多镜头视频生成** → `shot_type: "multi"`，每段5s，1280x720
3. **ffmpeg concat拼接** → 6段视频合并为30s剧情片
4. **DashScope TTS配音** → Cherry女声(中文)，生成 narration_v5.wav
5. **SRT字幕** → 6段中文解说词生成字幕，用 drawtext 滤镜烧录
6. **背景音乐** → Pixabay "Technology" 曲目，低通800Hz+回音处理变氛围感
7. **音频混合** → 配音(vol=1.0) + BGM(vol=0.10)，amix duration=first
8. **数字人开场**:
   - DashScope qwen-image-2.0-pro 生成中国女性主持人正面照
   - DashScope qwen3-tts-flash 生成开场白 "大家好..."
   - Wan2.2-s2v 720P 将照片+音频合成说话视频
   - ffmpeg minterpolate 插帧到30fps + 缩放1280x720
9. **最终合成** → 数字人开场(8s) + 科普剧情(30s)，音频三轨混合

### 使用的工具
| 工具 | 用途 |
|------|------|
| DashScope Wan2.6-t2v | 多镜头视频生成 |
| DashScope qwen-image-2.0-pro | 主持人照片生成 |
| DashScope qwen3-tts-flash | 中文TTS配音(Cherry) |
| DashScope Wan2.2-s2v | 照片+音频→说话视频 |
| ffmpeg (N-92722 2018) | 拼接、字幕、音频混合、插帧、缩放 |

### 风格特征
- **视觉**: Wan2.6生成的写实画面，多镜头切换，蓝天/日落/棱镜等科学意象
- **色调**: 自然光色调，蓝天为主，暖色日落对比
- **节奏**: 中速，每段5s，适合科普解说
- **音频**: 中文女声清晰解说 + 低氛围BGM
- **字幕**: 微软雅黑26号字，底部居中，半透明黑底框
- **开场**: AI数字人主持人正面出镜介绍主题

### 适合场景
科普短视频、知识解说、教育类内容、中文短视频平台（抖音/B站/视频号）
