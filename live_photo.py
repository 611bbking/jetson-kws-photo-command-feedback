"""Listen continuously for 拍照, then speak 拍照成功 once per trigger."""

import argparse
import os
import re
import subprocess
import time
from pathlib import Path

from audio_capture import configure_capture_route
from audio_feedback import play_photo_success
from kws_engine import realtime_command


PHOTO_EVENT = re.compile(r'\{[^{}]*"keyword"\s*:\s*"拍照"[^{}]*\}')


def wait_for_photo(command, env=None):
    """Wait for one event from sherpa's ALSA listener and release the mic."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    recent = b""
    try:
        while True:
            chunk = os.read(process.stderr.fileno(), 4096)
            if not chunk:
                detail = recent.decode("utf-8", errors="replace")[-1200:]
                raise RuntimeError(f"实时 KWS 意外退出:\n{detail}")
            recent = (recent + chunk)[-16000:]
            if PHOTO_EVENT.search(recent.decode("utf-8", errors="ignore")):
                return
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stderr.close()


def main():
    parser = argparse.ArgumentParser(description="持续监听‘拍照’并播放语音提示")
    parser.add_argument("--sherpa-dir", type=Path, default=Path("~/Documents/voice/sherpa-onnx").expanduser())
    parser.add_argument("--mic-device", default="kws_left")
    parser.add_argument("--speaker-device", default="hw:APE,0")
    parser.add_argument("--once", action="store_true", help="识别并播放一次后退出，便于验收")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    sound = root / "sounds/photo_success_48k_stereo.wav"
    command = realtime_command(args.sherpa_dir.expanduser().resolve(), root / "photo_keywords.txt", args.mic_device)
    env = None
    if args.mic_device == "kws_left":
        env = {**os.environ, "ALSA_CONFIG_PATH": str(root / "kws-left.asoundrc")}
    if not sound.is_file():
        parser.error(f"提示音不存在: {sound}")

    print("持续监听中。请说‘拍照’；按 Ctrl+C 退出。", flush=True)
    try:
        while True:
            configure_capture_route()
            wait_for_photo(command, env)
            print("识别到指令“拍照”", flush=True)
            # The listener has released the mic before speaker playback.
            play_photo_success(sound, args.speaker_device)
            if args.once:
                break
            time.sleep(0.5)
            print("继续监听中……", flush=True)
    except KeyboardInterrupt:
        print("\n已停止监听")


if __name__ == "__main__":
    main()
