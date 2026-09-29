"""Run the already-built sherpa-onnx KWS executable on one WAV file."""

import re
import subprocess
from pathlib import Path


MODEL_NAME = "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"
MODEL_PARTS = ("encoder", "decoder", "joiner")
MODEL_SUFFIX = "epoch-13-avg-2-chunk-16-left-64.onnx"


def model_files(sherpa_dir: Path, keywords: Path, binary_name="sherpa-onnx-keyword-spotter"):
    """Resolve and validate the files from this Jetson's existing build."""
    model = sherpa_dir / MODEL_NAME
    binary = sherpa_dir / "build/bin" / binary_name
    parts = {part: model / f"{part}-{MODEL_SUFFIX}" for part in MODEL_PARTS}
    tokens = model / "tokens.txt"
    required = [binary, tokens, keywords, *parts.values()]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("缺少文件:\n" + "\n".join(missing))

    # The checked-in keyword line is for this model's phone+ppinyin token set.
    available = {line.split()[0] for line in tokens.read_text(encoding="utf-8").splitlines() if line.strip()}
    if not {"p", "āi", "zh", "ào"}.issubset(available):
        raise ValueError("模型词表不包含‘拍照’所需 token，请重新生成关键词文件")
    return binary, parts, tokens


def recognize_photo(sherpa_dir: Path, keywords: Path, wav: Path):
    """Return the decoder output and whether it contains the requested word."""
    binary, parts, tokens = model_files(sherpa_dir, keywords)
    result = subprocess.run(
        [
            str(binary),
            *(f"--{part}={parts[part]}" for part in MODEL_PARTS),
            f"--tokens={tokens}",
            f"--keywords-file={keywords}",
            str(wav),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    output = result.stdout + result.stderr
    found = bool(re.search(r'"keyword"\s*:\s*"拍照"', output))
    return output, found


def realtime_command(sherpa_dir: Path, keywords: Path, device: str):
    """Build the existing ALSA streaming KWS command for this model."""
    binary, parts, tokens = model_files(
        sherpa_dir, keywords, binary_name="sherpa-onnx-keyword-spotter-alsa"
    )
    return [
        str(binary),
        *(f"--{part}={parts[part]}" for part in MODEL_PARTS),
        f"--tokens={tokens}",
        f"--keywords-file={keywords}",
        device,
    ]
