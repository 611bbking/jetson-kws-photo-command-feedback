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

    available = {line.split()[0] for line in tokens.read_text(encoding="utf-8").splitlines() if line.strip()}
    # @ 后是显示名称，不属于模型 token；注释行不参与词表检查。
    required_tokens = {
        token
        for line in keywords.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        for token in line.split("@", 1)[0].split()
    }
    missing_tokens = required_tokens - available
    if missing_tokens:
        raise ValueError(f"模型词表不包含关键词 token: {', '.join(sorted(missing_tokens))}")
    return binary, parts, tokens


def _keyword_command(sherpa_dir: Path, keywords: Path, binary_name: str) -> list[str]:
    """封装两种识别入口共有的模型参数；输入 WAV/设备由调用方追加。"""
    binary, parts, tokens = model_files(sherpa_dir, keywords, binary_name)
    return [
        str(binary),
        *(f"--{part}={parts[part]}" for part in MODEL_PARTS),
        f"--tokens={tokens}",
        f"--keywords-file={keywords}",
    ]


def recognize_photo(sherpa_dir: Path, keywords: Path, wav: Path):
    """Return the decoder output and whether it contains the requested word."""
    command = _keyword_command(sherpa_dir, keywords, "sherpa-onnx-keyword-spotter")
    result = subprocess.run(
        [*command, str(wav)],
        check=True,
        text=True,
        capture_output=True,
    )
    output = result.stdout + result.stderr
    found = bool(re.search(r'"keyword"\s*:\s*"拍照"', output))
    return output, found


def realtime_command(sherpa_dir: Path, keywords: Path, device: str):
    """Build the existing ALSA streaming KWS command for this model."""
    command = _keyword_command(sherpa_dir, keywords, "sherpa-onnx-keyword-spotter-alsa")
    return [*command, device]
