---
name: gd-town-daily
description: Use when producing "广东小镇" daily episodes — one Guangdong town per day, Cantonese narration with date/lunar/weekday opening, block/wrapped or vertical subtitles. Trigger words: 广东小镇, 小镇系列, 穷举所有镇, canto-culture-01, 日更, daily_plan.json, build_daily.py, make_overlays.py, compose.py, MiniMax TTS, 粤语配音.
---

# 广东小镇日更工厂 (gd-town-daily)

每日一集介绍广东省的一个镇。穷举全部镇，无优先级顺序；重大节日不做特辑。所有产出走本工作流的既有管道。

## 项目位置

```
C:\Users\ASUS\Desktop\project\AIGC\OpenMontage\projects\canto-culture-01\
├── daily_plan.json          # 全部排期（key = "MMDD-town-<拼音>"）
├── build_daily.py           # TTS: MiniMax → daily/<key>/assets/audio/line_N.mp3
├── make_overlays.py         # 字幕动画 → daily/<key>/assets/overlays/anim_N/
├── compose.py               # 渲染 → daily/<key>/renders/canto-town-<YYYY-MM-DD>.mp4
├── lib_lunar.py             # 农历+星期（date_card 生成首镜 date 卡）
├── assets/video/            # 素材库（复用或按需新增）
└── daily/<key>/             # 每集产物
```

## 每集生产流程（顺序执行）

1. **选镇**：按穷举顺序选下一个镇（从广州市/佛山市/东莞市/中山市等开始，逐县逐镇推进）。
2. **资料调研**：websearch「<镇名> 闻名 特色 文化 饮食 景点 经济」等，提取该镇 **最突出的 1-3 个方面**（不要求文化/饮食/景点/经济全覆盖——只讲突出的）。
3. **写文案**（见下）。
4. **写排期**：往 `daily_plan.json` 追加 key `MMDD-town-<拼音>`（date = 当天，slug = `canto-town`）。
5. **素材**：Pexels 搜关键词 → 下载候选封面 → Qwen-VL 审核（构图专业/光线/主体匹配）→ 下载选中片段（命名 `tn_<主题>_<id>.mp4` 或 `hm_` 等前缀）→ 合并进 `artifacts/video_candidates*.json` 与 `assets/video/`。优先复用素材库。
6. **TTS**：`python -X utf8 build_daily.py <key>`（逐集跑，集间 Start-Sleep 8s 防 MiniMax RPM 限流；遇到 1002 rate limit 等 60s 重试）。
7. **字幕**：`python -X utf8 make_overlays.py <key>`
8. **渲染**：`python -X utf8 compose.py <key>`（若音频/字幕有变更，先删 `daily/<key>/tmp/seg*.mp4` 清缓存再渲染！）
9. **验证**：ffmpeg 抽帧（时间点避开场景边界 ±0.3s）→ Qwen-VL 检查字幕在画面内/不遮主体/日期卡农历行/块状或竖排正确。
10. **交付**：复制成片到 `C:\Users\ASUS\Desktop\project\AIGC\canto-town-<YYYY-MM-DD>.mp4`，并播放给用户。

## 文案规范（粤语，9-10 镜）

- **s1 日期卡**：不写死，由 `lib_lunar.date_card` 自动生成：大字 `M/D` + 小字 `農曆X月X日・週X`；TTS 口播 `早晨各位，今日係八月二號，農曆六月二十，星期日`。
- **s2 开场**：`今日帶你認識一個鎮：嚟自<市>嘅<鎮>鎮`（东莞等直筒市写"嚟自東莞市嘅虎門鎮"）。
- **s3-s7 内容**：只讲突出的方面，每镜一句，数据尽量具体（"全國八成嘅年桔都出自呢度"、"六百幾座騎樓"、"鎖具佔全國兩成幾"）。
- **立意句**：倒数第二镜，一句话点题（例：「一個鎮，有歷史、有煙火、有未來」），TTS 加 `(breath)` 前缀，字幕开 **vertical**。
- **尾镜**：`聽日見啦`。
- 情绪：开场 calm、内容 happy、立意 calm、收尾 happy；庄重题材（历史/纪念）整体 calm。
- 每镜 `anchor` 手动分配位置避开素材主体（长句可放 (0.42,0.8)/(0.66,0.78) 两侧，立意竖排放 (0.18,0.5) 或 (0.82,0.5)）。

## 字幕规范（make_overlays.py 已实现）

- **块状换行**：按逗号/顿号语义断句成 2-3 块（`split_blocks`），超宽再按字拆行；3 行以上自动缩字号（52→42）。
- **竖排**：scene 加 `"vertical": true` → 右起竖排、多块并排成方形；适配缩小。
- **日期卡**：`make_date_card(text, sub)` 大字日期 + 小字农历星期行。
- 字体：默陌手写体（回退方正舒体/华文楷体），日期用微软雅黑粗体；白色 + 黑色高斯模糊双层阴影。

## TTS 规范（MiniMax）

- VOICE_ID=`Cantonese_GentleLady`，MODEL=`speech-2.8-hd`，SPEED=0.95，`language_boost="Chinese,Yue"`，emotion 按镜设置，`text_normalization=True`。
- API 返回 hex 字符串，必须 `bytes.fromhex` 解码为 mp3。
- key 在 `OpenMontage\.env`（`MINIMAX_API_KEY`）。
- 日期口播不要阿拉伯数字（"8月2號" 会被读出停顿），用汉字 `八月二號`。

## 素材库（assets/video/ 可复用，前缀表）

- pv_/ch_/cf_/ct_/wk_：通用城市/生活/美食/老街素材
- hm_：虎门（海面/大桥/海鲜/缝纫厂）
- ay_：军事（阅兵/军人/消防）
- tn_：三镇（花卉/年桔/兰花/河粉/古塔/煲仔饭/菊花/五金锁）

## 验证命令速查

- 抽帧：`<ffmpeg> -ss <t> -i <mp4> -frames:v 1 -q:v 2 <out.jpg>`（ffmpeg 在 `OpenMontage\projects\why-sky-blue\node_modules\@ffmpeg-installer\win32-x64\ffmpeg.exe`）
- VL 审核/验证：调 DashScope `qwen-vl-max`（key 在 .env `DASHSCOPE_API_KEY`），提示词要求输出：主体/光线/字幕转写(粤语繁体)/是否遮挡/横排竖排/是否出界。

## 清理约定

- 主题变更时，旧的 daily 目录 + daily_plan.json 对应 key 一并删除。
- 素材库跨主题保留（可复用），不随主题清理。
