# Jetson 离线“拍照”语音反馈

在 Jetson Orin Nano Super 上持续监听 I2S 麦克风。识别到“拍照”后，程序暂停收音，通过 I2S 扬声器播放预先生成的“拍照成功”语音，然后继续监听。识别与播放均在本机完成，运行时无需联网。

**当前只验证语音指令与反馈，不控制相机，也不会保存照片。**

## 已验证的硬件与软件

- Jetson 的 ALSA 声卡为 `APE`，录音和播放设备均使用设备 0；I2S 接口为 `I2S2`。
- `ADMAIF1 Mux = I2S2` 用于收音；`I2S2 Mux = ADMAIF1` 用于播放。
- 当前麦克风的有效语音位于双声道录音的左声道。`hw:APE,0` 单声道读取会报 `Input/output error`；16 kHz 双声道读取正常。
- `kws-left.asoundrc` 强制硬件按双声道采集，只把左声道提供给 sherpa-onnx 的实时 KWS 程序。
- `test_voice.py` 可用的播放参数是 48 kHz、16 位、双声道、`hw:APE,0`。`sounds/photo_success_48k_stereo.wav` 已按这些参数在板上播放，现场确认能听到声音。
- 真人“拍照”已被实时 KWS 识别；改用新语音文件后的完整“识别 → 播放 → 恢复监听”循环仍需现场复测。

这些配置针对当前板卡和接线。更换声卡、I2S 接口或麦克风时，需检查 `audio_capture.py`、`audio_feedback.py` 和 `kws-left.asoundrc` 中的设备与路由。

## 准备环境

推荐目录结构：

```text
~/Documents/voice/
├── photo_test/       # 本仓库
├── sherpa-onnx/      # 已编译的 sherpa-onnx 及模型
└── venv/             # 可选；这些 Python 脚本只用标准库
```

需要安装 ALSA 工具 `amixer`、`arecord`、`aplay`。`sherpa-onnx/build/bin/` 下需要已有 `sherpa-onnx-keyword-spotter-alsa` 和 `sherpa-onnx-keyword-spotter`，并将模型 `sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20` 放在 `sherpa-onnx/` 下。模型目录需要 `tokens.txt` 和 `encoder`、`decoder`、`joiner` 的 `epoch-13-avg-2-chunk-16-left-64.onnx` 文件。程序启动时会检查这些文件。

从 GitHub 克隆：

```bash
cd ~/Documents/voice
git clone https://github.com/611bbking/jetson-kws-photo-command-feedback.git photo_test
cd photo_test
```

如果使用现有的 `~/Documents/voice/venv/`，下面的命令可直接复制；否则把 Python 路径换成 `python3`。

## 运行

先验证一次识别与播放：

```bash
cd ~/Documents/voice/photo_test
~/Documents/voice/venv/bin/python live_photo.py --once
```

说“拍照”后，应看到 `识别到指令“拍照”`，并听到“拍照成功”。`--once` 播放一次后退出。通过后持续运行：

```bash
~/Documents/voice/venv/bin/python live_photo.py
```

按 `Ctrl+C` 停止。默认麦克风设备是 `kws_left`，播放设备是 `hw:APE,0`；可通过 `--mic-device`、`--speaker-device` 覆盖。若 sherpa-onnx 位于其他目录，传入 `--sherpa-dir /path/to/sherpa-onnx`。

## 单独检查收音与播放

当前板卡的原始双声道收音：

```bash
amixer -c APE cset name='ADMAIF1 Mux' I2S2
arecord -D hw:APE,0 -f S16_LE -r 16000 -c 2 -d 3 /tmp/photo-stereo.wav
```

检查左声道虚拟设备：

```bash
ALSA_CONFIG_PATH="$PWD/kws-left.asoundrc" arecord -D kws_left -f S16_LE -r 16000 -c 1 -d 3 /tmp/photo-left.wav
```

使用脚本录制双声道、分别保存左右声道并进行一次性 KWS 检查：

```bash
~/Documents/voice/venv/bin/python main.py
```

单独播放当前提示音：

```bash
amixer -c APE cset name='I2S2 Mux' ADMAIF1
aplay -D hw:APE,0 sounds/photo_success_48k_stereo.wav
```

如果 `aplay` 正常退出却听不到声音，先比较实际播放格式和已能发声的 `test_voice.py`。旧的 `sounds/photo_success.wav` 是 22.05 kHz 单声道，不能作为当前板卡的播放验收文件。

## 文件与工作流程

| 文件 | 作用 |
| --- | --- |
| `live_photo.py` | 启动监听，识别后停止 KWS 子进程，调用播放，再重新监听。 |
| `kws_engine.py` | 组合 sherpa-onnx 的模型、关键词与实时识别命令；也支持已有 WAV 的识别。 |
| `audio_capture.py` | 设置收音路由，提供一次性录音与左右声道检查。 |
| `kws-left.asoundrc` | 把 APE 的双声道硬件输入映射为左声道单声道。 |
| `audio_feedback.py` | 设置播放路由，调用 `aplay` 播放提示音。 |
| `photo_keywords.txt` | 当前模型的“拍照”关键词 token：`p āi zh ào @拍照`。 |
| `sounds/photo_success.wav` | 最初由本地中文系统语音预先生成的文件；具体语音引擎和声音未记录。 |
| `sounds/photo_success_48k_stereo.wav` | 当前实际播放的 48 kHz、16 位双声道语音文件。 |

“拍照成功”是在运行前生成的固定语音，Jetson 运行时不调用文字转语音服务。播放文件由原始语音转换得到：

```bash
ffmpeg -i sounds/photo_success.wav -ar 48000 -ac 2 -c:a pcm_s16le sounds/photo_success_48k_stereo.wav
```

模型、编译后的 sherpa-onnx 和 Python 虚拟环境不包含在本仓库中。硬件录音、播放与真人触发需要在 Jetson 上验收。
