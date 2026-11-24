from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST_SHA256.txt"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    failures: list[str] = []
    checked = 0
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing: {relative}")
            continue
        actual = digest(path)
        checked += 1
        if actual != expected:
            failures.append(f"digest mismatch: {relative}")
    if failures:
        raise SystemExit("Release verification failed:\n" + "\n".join(failures))
    print(f"Verified {checked} files with no SHA-256 mismatch.")


if __name__ == "__main__":
    main()

