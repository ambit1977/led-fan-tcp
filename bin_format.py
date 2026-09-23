"""Observed V13-family BIN container checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FRAME_UNIT = 3584
UPLOAD_CHUNK = 0x3C000
BIN_TRAILER = b"B2DDDDEDC0EEBDF9E5B7"


@dataclass(frozen=True)
class BinInfo:
    path: Path
    size: int
    payload_size: int
    frame_units: int
    trailing_bytes: int


def inspect_bin(path: Path) -> BinInfo:
    size = path.stat().st_size
    with path.open("rb") as source:
        source.seek(max(0, size - len(BIN_TRAILER)))
        trailer = source.read(len(BIN_TRAILER))
    if trailer != BIN_TRAILER:
        raise ValueError(f"{path} does not end with the observed BIN trailer")
    payload_size = size - len(BIN_TRAILER)
    return BinInfo(path, size, payload_size, payload_size // FRAME_UNIT, payload_size % FRAME_UNIT)


def iter_chunks(path: Path, chunk_size: int = UPLOAD_CHUNK):
    with path.open("rb") as source:
        while block := source.read(chunk_size):
            yield block
