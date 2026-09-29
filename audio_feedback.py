"""Play a fixed spoken response through Jetson's I2S output."""

import subprocess
from pathlib import Path


def play_photo_success(sound: Path, device: str):
    if not sound.is_file():
        raise FileNotFoundError(f"提示音不存在: {sound}")

    # Playback uses the opposite AHUB route from microphone capture.
    subprocess.run(
        ["amixer", "-c", "APE", "cset", "name=I2S2 Mux", "ADMAIF1"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(["aplay", "-D", device, str(sound)], check=True)
