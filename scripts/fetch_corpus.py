"""Rebuild a PDF corpus from an official-source manifest."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/138.0 Safari/537.36 FinDocIQ/0.1"
)
READ_SIZE = 1024 * 1024
MAX_ATTEMPTS = 4


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    id: str
    kind: str
    source: str
    url: str

    @classmethod
    def from_mapping(cls, value: Any) -> CorpusEntry:
        if not isinstance(value, dict):
            raise ValueError("each corpus document must be a mapping")
        expected = {"id", "kind", "source", "url"}
        if set(value) != expected:
            raise ValueError(
                f"invalid keys for corpus document; expected={sorted(expected)}, "
                f"actual={sorted(value)}"
            )
        entry = cls(**value)
        if not entry.id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in entry.id
        ):
            raise ValueError(f"invalid corpus id: {entry.id!r}")
        if entry.kind not in {"annual_report", "rating_rationale"}:
            raise ValueError(f"invalid corpus kind for {entry.id}: {entry.kind}")
        if not entry.url.startswith("https://"):
            raise ValueError(f"corpus URL must use HTTPS: {entry.url}")
        return entry


@dataclass(frozen=True, slots=True)
class LockedEntry:
    id: str
    kind: str
    source: str
    url: str
    filename: str
    sha256: str
    bytes: int


def load_manifest(path: Path) -> tuple[str, tuple[CorpusEntry, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"name", "documents"}:
        raise ValueError("manifest must contain exactly 'name' and 'documents'")
    entries = tuple(CorpusEntry.from_mapping(value) for value in payload["documents"])
    identifiers = [entry.id for entry in entries]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("corpus document IDs must be unique")
    return str(payload["name"]), entries


def download(entry: CorpusEntry, output_dir: Path) -> LockedEntry:
    destination = output_dir / f"{entry.id}.pdf"
    if destination.is_file():
        return lock_existing(entry, destination)

    last_error: BaseException | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return download_once(entry, output_dir, destination)
        except urllib.error.HTTPError as error:
            if error.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(
                    f"source returned HTTP {error.code} for {entry.id}"
                ) from error
            last_error = error
        except (
            http.client.RemoteDisconnected,
            TimeoutError,
            urllib.error.URLError,
        ) as error:
            last_error = error
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(attempt)
    raise RuntimeError(
        f"failed to download {entry.id} after {MAX_ATTEMPTS} attempts"
    ) from last_error


def download_once(entry: CorpusEntry, output_dir: Path, destination: Path) -> LockedEntry:
    request = urllib.request.Request(
        entry.url,
        headers={
            "Accept": "application/pdf,*/*;q=0.8",
            "Connection": "close",
            "User-Agent": USER_AGENT,
        },
    )
    with (
        urllib.request.urlopen(request, timeout=90) as response,  # noqa: S310
        tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as temporary,
    ):
        temporary_path = Path(temporary.name)
        digest = hashlib.sha256()
        prefix = b""
        size = 0
        while block := response.read(READ_SIZE):
            if not prefix:
                prefix = block[:5]
            temporary.write(block)
            digest.update(block)
            size += len(block)
    try:
        if prefix != b"%PDF-":
            raise ValueError(f"source did not return a PDF for {entry.id}")
        shutil.move(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return LockedEntry(
        **asdict(entry),
        filename=destination.name,
        sha256=digest.hexdigest(),
        bytes=size,
    )


def lock_existing(entry: CorpusEntry, path: Path) -> LockedEntry:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        prefix = handle.read(5)
        if prefix != b"%PDF-":
            raise ValueError(f"cached source is not a PDF for {entry.id}")
        digest.update(prefix)
        for block in iter(lambda: handle.read(READ_SIZE), b""):
            digest.update(block)
    return LockedEntry(
        **asdict(entry),
        filename=path.name,
        sha256=digest.hexdigest(),
        bytes=path.stat().st_size,
    )


def build_lock(name: str, entries: list[LockedEntry], lock_path: Path) -> None:
    payload = {
        "name": name,
        "documents": [asdict(entry) for entry in entries],
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("configs/corpus/phase1.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("corpus/phase1"))
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path("configs/corpus/phase1.lock.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    name, entries = load_manifest(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    locked: list[LockedEntry] = []
    for index, entry in enumerate(entries, start=1):
        print(f"[{index}/{len(entries)}] {entry.id}", flush=True)
        locked.append(download(entry, args.output_dir))
    build_lock(name, locked, args.lock)
    total_bytes = sum(item.bytes for item in locked)
    print(f"locked {len(locked)} PDFs ({total_bytes / 1024 / 1024:.1f} MiB) at {args.lock}")


if __name__ == "__main__":
    main()
