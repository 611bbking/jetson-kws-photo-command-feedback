"""共享的词、路径和当前 Jetson 音频参数；模型参数由 kws_engine 管理。"""
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_SHERPA_DIR = Path("~/Documents/voice/sherpa-onnx").expanduser()
MIC_DEVICE = "kws_left"
SPEAKER_DEVICE = "hw:APE,0"
CAPTURE_DEVICE = "plughw:APE,0"
AUDIO_CARD = "APE"
I2S_INTERFACE = "I2S2"
DMA_INTERFACE = "ADMAIF1"
WAKE_KEYWORD = "楠机楠机"
SLEEP_KEYWORD = "再见楠机"
PLAYBACK_SETTLE_SECONDS = 0.5
COMMAND_SOUNDS = {
    "拍照": "takephoto.wav",
    "录像": "start_record.wav",
    "停止录像": "stop_record.wav",
    "冻结": "freeze.wav",
    "测量": "measure.wav",
    "归零": "reset.wav",
    SLEEP_KEYWORD: "goodbye.wav",
}
