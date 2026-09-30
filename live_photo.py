"""Accept commands after waking, and sleep again on 再见楠机."""

import argparse
import os
import re
import subprocess
import time
from pathlib import Path

from app_config import (
    COMMAND_SOUNDS, DEFAULT_SHERPA_DIR, MIC_DEVICE, PLAYBACK_SETTLE_SECONDS,
    PROJECT_DIR, SLEEP_KEYWORD, SPEAKER_DEVICE, WAKE_KEYWORD,
)
from audio_capture import configure_capture_route
from audio_feedback import play_audio
from kws_engine import realtime_command


EVENT = re.compile(r'\{[^{}]*"keyword"\s*:\s*"([^"]+)"[^{}]*\}')



def wait_for_keyword(command: list[str], keywords, env=None) -> str:
    """Wait for one event from sherpa's ALSA listener and release the mic."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    # 保留原始字节，避免读取边界截断中文 UTF-8 或跨块的 JSON 事件。
    recent = b""
    volume_pending = b""
    show_volume = env is not None and "SHERPA_KWS_VOLUME" in env
    try:
        while True:
            chunk = os.read(process.stderr.fileno(), 4096)
            if not chunk:
                detail = recent.decode("utf-8", errors="replace")[-1200:]
                raise RuntimeError(f"实时 KWS 意外退出:\n{detail}")
            if show_volume:
                # 只转发完整的音量行；跨块的日志保留到下一次读取。
                volume_pending += chunk
                lines = volume_pending.split(b"\n")
                volume_pending = lines.pop()[-16000:]
                for line in lines:
                    if line.startswith(b"[volume]"):
                        print(line.decode("utf-8", errors="replace"), flush=True)
            recent = (recent + chunk)[-16000:]
            matches = [
                event.group(1)
                for event in EVENT.finditer(recent.decode("utf-8", errors="ignore"))
                if event.group(1) in keywords
            ]
            if matches:
                # 同批事件中优先完整长词，避免“停止录像”被“录像”抢先命中。
                return max(matches, key=len)
    finally:
        # 先回收监听进程、释放麦克风，再允许调用方播放提示音。
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stderr.close()


def main():
    parser = argparse.ArgumentParser(description="先用‘楠机楠机’唤醒，再识别指令并播放语音提示")
    parser.add_argument("--sherpa-dir", type=Path, default=DEFAULT_SHERPA_DIR)
    parser.add_argument("--mic-device", default=MIC_DEVICE)
    parser.add_argument("--speaker-device", default=SPEAKER_DEVICE)
    parser.add_argument("--once", action="store_true", help="识别并播放一次后退出，便于验收")
    parser.add_argument("--volume-meter", action="store_true", help="同时打印 KWS 输入音量，需先运行 build_volume_meter.py")
    args = parser.parse_args()

    root = PROJECT_DIR
    greeting = root / "sounds/nanji.wav"
    sounds = {keyword: root / "sounds" / filename for keyword, filename in COMMAND_SOUNDS.items()}
    sherpa_dir = args.sherpa_dir.expanduser().resolve()
    # 未启用音量时，继续调用原版可执行文件与原有参数。
    meter_options = {"volume_meter": True} if args.volume_meter else {}
    wake_command = realtime_command(sherpa_dir, root / "wake_keywords.txt", args.mic_device, **meter_options)
    action_command = realtime_command(sherpa_dir, root / "command_keywords.txt", args.mic_device, **meter_options)
    # 仅虚拟左声道设备加载项目 ALSA 配置；显式设备沿用系统配置。
    env = None
    if args.mic_device == MIC_DEVICE:
        env = {**os.environ, "ALSA_CONFIG_PATH": str(root / "kws-left.asoundrc")}
    if args.volume_meter:
        env = {**(env if env is not None else os.environ), "SHERPA_KWS_VOLUME": "1"}
    for sound in (greeting, *sounds.values()):
        if not sound.is_file():
            parser.error(f"提示音不存在: {sound}")

    try:
        while True:
            configure_capture_route()
            print("等待唤醒词‘楠机楠机’；按 Ctrl+C 退出。", flush=True)
            wait_for_keyword(wake_command, {WAKE_KEYWORD}, env)
            print("识别到唤醒词“楠机楠机”，播放问候语", flush=True)
            play_audio(greeting, args.speaker_device)
            print("问候语播放完成，请说指令", flush=True)
            # 内层循环维持唤醒状态；退出指令返回外层重新等待唤醒。
            while True:
                configure_capture_route()
                keyword = wait_for_keyword(action_command, COMMAND_SOUNDS, env)
                print(f"识别到指令“{keyword}”", flush=True)
                # The listener has released the mic before speaker playback.
                play_audio(sounds[keyword], args.speaker_device)
                print("拍照成功" if keyword == "拍照" else f"提示音播放完成：{keyword}", flush=True)
                if args.once:
                    return
                time.sleep(PLAYBACK_SETTLE_SECONDS)
                if keyword == SLEEP_KEYWORD:
                    print("已退出指令模式，重新等待唤醒", flush=True)
                    break
                print("继续监听指令……", flush=True)
    except KeyboardInterrupt:
        print("\n已停止监听")


if __name__ == "__main__":
    main()
