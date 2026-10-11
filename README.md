# AIGC Agent

指令驱动的 AI 视频生产系统，基于 [OpenMontage](https://github.com/calesthio/OpenMontage) 构建。通过 AI Agent（OpenCode / Claude / Cursor 等）直接驱动视频创作：从剧本、分镜、素材生成到最终合成，全流程可自动化。

## 架构

```
AIGC/
├── OpenMontage/                  # 核心引擎（工具层 + 流水线 + 技能）
│   ├── tools/                    # Python 工具层（视频/音频/图像/TTS/合成）
│   ├── pipeline_defs/            # 流水线定义（YAML 状态机）
│   ├── skills/                   # 创意技能 + 流水线导演技能
│   ├── .agents/skills/           # 技术供应商技能包（Seedance/可灵/即梦等）
│   ├── lib/                      # 检查点、配置、素材库等基础设施
│   ├── schemas/                  # JSON Schema 校验
│   └── backlot/                  # 实时看板（FastAPI + SSE）
├── .opencode/
│   └── skills/gd-town-daily/     # 广东小镇日更工厂（自定义 OpenCode 技能）
├── short-drama-code-neko1/       # 短剧项目独立工作区
└── *.mp4                         # 交付成片
```

### 三层架构

| 层 | 位置 | 职责 |
|---|---|---|
| **指令层** | `skills/` + `.opencode/skills/` | Agent 如何使用系统：流程、导演技能、创意规范 |
| **工具层** | `tools/` + `lib/` | Python 可执行能力：视频生成、TTS、合成、剪辑 |
| **知识层** | `.agents/skills/` | 供应商技术细节：API 调用方式、模型参数、最佳实践 |

### 流水线状态机

```
research → proposal → script → scene_plan → assets → edit → compose → publish
```

每个阶段由 YAML 定义（`pipeline_defs/*.yaml`），指定可用工具、审核要点、成功标准和人工审批门槛。

## 已实现的项目

### 1. 广东小镇日更系列

穷举广东全部镇，每集一个镇，粤语旁白 + Pexels 实拍素材 + 动态字幕。

- **技能**: `.opencode/skills/gd-town-daily/SKILL.md`
- **项目**: `OpenMontage/projects/canto-culture-01/`
- **已产出**: 虎门、陈村、赤坎、小榄（4集）
- **工具链**: MiniMax TTS（粤语音色）→ Pexels 素材检索 → Qwen-VL 画面审核 → FFmpeg 合成

### 2. 短剧《代码封神的我，居然开始穿女装了》

16:9 横屏都市短剧先导片，自定义流水线 `169_cinematic_drama`。

- **流水线**: `pipeline_defs/169_cinematic_drama.yaml`
- **导演技能**: `skills/pipelines/cinematic-169/`（制片/编剧/分镜/素材/剪辑/合成 6 个导演角色）
- **已产出**: 30秒 i2v 先导片（DashScope 万相 wanx2.1-i2v-turbo，18镜视频 + 2镜文字卡）
- **特点**: 三幕式剧本 → 20镜分镜表 → 逐镜图生视频 → 剪辑合成

### 3. 其他

- **why-sky-blue**: 动画解释视频（天空为什么是蓝色）
- **kimi-k3-promo**: Kimi K3 推广片
- **morning-greeting**: 抖音粤语早安问候

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- FFmpeg

### 安装

```bash
git clone https://github.com/chasel12/aigc_agent.git
cd aigc_agent/OpenMontage
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 填入你的 API keys（至少需要 DASHSCOPE_API_KEY）
```

### 运行

```bash
# 查看可用流水线
python -m tools.tool_registry --summary

# 运行测试
make test
```

## 关键 API 依赖

| 服务 | 用途 | 环境变量 |
|---|---|---|
| DashScope（百炼） | 万相视频生成、Qwen 图像/TTS/ASR | `DASHSCOPE_API_KEY` |
| MiniMax | TTS 语音合成 | `MINIMAX_API_KEY` |
| Pexels | 免费实拍素材 | `PEXELS_API_KEY` |
| FFmpeg | 视频合成/剪辑 | 本地安装 |

## 自定义流水线

在 `pipeline_defs/` 中添加 YAML 定义新流水线，在 `skills/pipelines/<name>/` 中创建对应的导演技能。参考 `169_cinematic_drama.yaml` 和 `skills/pipelines/cinematic-169/`。

## License

基于 [OpenMontage](https://github.com/calesthio/OpenMontage)（AGPL-3.0），本地自定义部分遵循相同协议。
