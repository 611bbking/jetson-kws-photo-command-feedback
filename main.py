"""One-word test: Jetson I2S microphone -> WAV -> KWS result for 拍照."""

import argparse
from pathlib import Path

from audio_capture import capture_for_kws, split_channels
from kws_engine import recognize_photo


def main():
    parser = argparse.ArgumentParser(description="在 Jetson 上测试关键词‘拍照’")
    parser.add_argument("--sherpa-dir", type=Path, default=Path("~/Documents/voice/sherpa-onnx").expanduser())
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--wav", type=Path, help="使用已有的单声道 WAV")
    source.add_argument("--raw-wav", type=Path, help="重新检查已有的双声道录音")
    parser.add_argument("--device", default="plughw:APE,0", help="ALSA 录音设备")
    parser.add_argument("--seconds", type=int, default=8, help="现场录音秒数")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds 必须大于 0")

    if args.wav or args.raw_wav:
        wav = (args.wav or args.raw_wav).expanduser().resolve()
        if not wav.is_file():
            parser.error(f"WAV 不存在: {wav}")
        channels = split_channels(wav) if args.raw_wav else [("指定文件", wav)]
    else:
        wav = Path(__file__).resolve().parent / "photo-test.wav"
        channels = capture_for_kws(wav, args.device, args.seconds)

    keywords = Path(__file__).resolve().parent / "photo_keywords.txt"
    for name, channel_wav in channels:
        print(f"正在检查{name}声道: {channel_wav}")
        output, found = recognize_photo(args.sherpa_dir.expanduser().resolve(), keywords, channel_wav)
        for line in output.splitlines():
            if '"keyword"' in line:
                print(line)
        if found:
            print(f"[识别] 拍照（{name}声道）")
            return 0
    print("[识别] 两个声道均未检测到‘拍照’")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
