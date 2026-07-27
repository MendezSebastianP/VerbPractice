from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path


REVISION = "ca5daf3d11b6c4b3143b1f4602a2edfb64c3ad7e"
BASE_URL = (
    "https://huggingface.co/onnx-community/"
    "multilingual-MiniLMv2-L6-mnli-xnli-ONNX/resolve/"
    f"{REVISION}"
)
FILES = {
    "tokenizer.json": "tokenizer.json",
    "onnx/model_int8.onnx": "model_int8.onnx",
}
SHA256 = {
    "tokenizer.json": "d0091a328b3441d754e481db5a390d7f3b8dabc6016869fd13ba350d23ddc4cd",
    "onnx/model_int8.onnx": "55614f3c7da74184742eaa0006b978744437aa91de9ba4913db42f94d7844a8f",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(destination: Path) -> None:
    for remote_name, local_name in FILES.items():
        target = destination / local_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size > 1_000:
            if _sha256(target) == SHA256[remote_name]:
                print(f"Already present: {target}")
                continue
            raise RuntimeError(f"Checksum mismatch for existing file: {target}")
        url = f"{BASE_URL}/{remote_name}?download=true"
        temporary = target.with_suffix(f"{target.suffix}.part")
        print(f"Downloading {remote_name}...")
        try:
            with urllib.request.urlopen(url) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            actual = _sha256(temporary)
            if actual != SHA256[remote_name]:
                raise RuntimeError(
                    f"Checksum mismatch for {remote_name}: expected "
                    f"{SHA256[remote_name]}, got {actual}"
                )
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Saved {target}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the pinned quantized multilingual NLI model."
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(".local/models/multilingual-nli"),
    )
    args = parser.parse_args()
    download(args.destination.resolve())


if __name__ == "__main__":
    main()
