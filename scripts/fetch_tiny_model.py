from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPOSITORY = "Systran/faster-whisper-tiny.en"
REQUIRED_FILES = ("config.json", "model.bin", "tokenizer.json")


def fetch(output: Path) -> Path:
    from huggingface_hub import snapshot_download

    output.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=REPOSITORY,
        local_dir=output,
    )
    shutil.rmtree(output / ".cache", ignore_errors=True)
    missing = [filename for filename in REQUIRED_FILES if not (output / filename).is_file()]
    if missing:
        raise RuntimeError(f"Downloaded tiny.en model is incomplete: {', '.join(missing)}")
    if (output / "model.bin").stat().st_size < 50_000_000:
        raise RuntimeError("Downloaded tiny.en model.bin is unexpectedly small")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the bundled prxmpt speech model")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    location = fetch(arguments.output.resolve())
    print(f"tiny.en ready: {location}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
