"""Jetson I2S microphone capture for the one-word KWS check."""

import array
import math
import subprocess
import sys
import wave
from pathlib import Path


def configure_capture_route():
    """Route I2S2 input to the first ALSA capture stream (ADMAIF1)."""
    subprocess.run(
        ["amixer", "-c", "APE", "cset", "name=ADMAIF1 Mux", "I2S2"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def record_stereo(path: Path, device: str, seconds: int):
    """Record both I2S slots and display ALSA's live stereo VU meter."""
    print(f"开始录音 {seconds} 秒。请说‘拍照’，观察左/右声道音量条是否随声音变化。", flush=True)
    subprocess.run(
        [
            "arecord", "-D", device, "-f", "S16_LE", "-r", "48000",
            "-c", "2", "-V", "stereo", "-d", str(seconds), str(path),
        ],
        check=True,
    )


def split_channels(source: Path):
    """Save both I2S slots; the louder slot can be invalid digital noise."""
    with wave.open(str(source), "rb") as wav:
        if wav.getnchannels() != 2 or wav.getsampwidth() != 2:
            raise ValueError("录音必须是 16-bit 双声道 PCM WAV")
        rate = wav.getframerate()
        samples = array.array("h", wav.readframes(wav.getnframes()))

    if sys.byteorder != "little":
        samples.byteswap()
    left, right = samples[0::2], samples[1::2]
    if not left:
        raise ValueError("录音文件没有音频数据")

    def rms(channel):
        return math.sqrt(sum(value * value for value in channel) / len(channel))

    outputs = []
    for name, samples in (("左", left), ("右", right)):
        destination = source.with_name(source.stem.removesuffix("-raw") + ("-left.wav" if name == "左" else "-right.wav"))
        level = rms(samples)
        clipped = sum(abs(value) >= 32000 for value in samples) / len(samples)
        print(f"{name}声道 RMS={level:.1f}，削波比例={clipped:.1%}；文件: {destination}")
        with wave.open(str(destination), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(samples.tobytes())
        outputs.append((name, destination))
    return outputs


def capture_for_kws(destination: Path, device: str, seconds: int):
    """Record raw audio and return both mono candidates for recognition."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = destination.with_name(destination.stem + "-raw.wav")
    configure_capture_route()
    record_stereo(raw, device, seconds)
    channels = split_channels(raw)
    print(f"原始双声道录音: {raw}")
    return channels
