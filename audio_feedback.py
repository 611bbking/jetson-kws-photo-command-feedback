"""Play a fixed spoken response through Jetson's I2S output."""

import subprocess
from pathlib import Path

from app_config import AUDIO_CARD, DMA_INTERFACE, I2S_INTERFACE


def play_audio(sound: Path, device: str):
    if not sound.is_file():
        raise FileNotFoundError(f"提示音不存在: {sound}")

    # Playback uses the opposite AHUB route from microphone capture.
    subprocess.run(
        ["amixer", "-c", AUDIO_CARD, "cset", f"name={I2S_INTERFACE} Mux", DMA_INTERFACE],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["aplay", "-D", device, str(sound)], check=True)
