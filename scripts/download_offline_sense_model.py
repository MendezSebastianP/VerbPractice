from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path


REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
BASE_URL = (
    "https://huggingface.co/intfloat/multilingual-e5-small/resolve/"
    f"{REVISION}"
)
FILES = {
    "tokenizer.json": "tokenizer.json",
    "onnx/model_qint8_avx512_vnni.onnx": "onnx/model_qint8_avx512_vnni.onnx",
}
SHA256 = {
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    "onnx/model_qint8_avx512_vnni.onnx": "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88",
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
        description="Download the pinned CPU-only multilingual sense model."
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(".local/models/multilingual-e5-small"),
    )
    args = parser.parse_args()
    download(args.destination.resolve())


if __name__ == "__main__":
    main()
