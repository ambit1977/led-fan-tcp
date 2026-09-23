"""Render observed 42ue BIN frames to an ordinary MP4 preview on macOS."""

from __future__ import annotations

import functools
import math
import shutil
import subprocess
from pathlib import Path

from bin_format import BIN_TRAILER, FRAME_UNIT, inspect_bin
from convert import ANGLES, FPS, PLANES, RADIUS, SOURCE_SIZE


@functools.lru_cache(maxsize=None)
def _inverse_coordinates(*, clockwise: bool, angle_offset: int) -> list[int | None]:
    """Map every Cartesian preview pixel to its packed polar bit position."""
    center = (SOURCE_SIZE - 1) / 2
    coordinates: list[int | None] = []
    for y in range(SOURCE_SIZE):
        for x in range(SOURCE_SIZE):
            dx, dy = x - center, center - y
            radius = round(math.hypot(dx, dy))
            if radius >= RADIUS:
                coordinates.append(None)
                continue
            phase = math.atan2(dy, dx)
            if clockwise:
                phase = -phase
            angle = round(phase * ANGLES / (2 * math.pi) - angle_offset) % ANGLES
            coordinates.append(angle * RADIUS + radius)
    return coordinates


def render_rgb_frame(
    encoded: bytes,
    *,
    clockwise: bool = False,
    angle_offset: int = 0,
) -> bytes:
    """Render three packed device planes to a 256x256 RGB preview image."""
    if len(encoded) != FRAME_UNIT * len(PLANES):
        raise ValueError(f"expected {FRAME_UNIT * len(PLANES)} encoded bytes, got {len(encoded)}")
    result = bytearray(SOURCE_SIZE * SOURCE_SIZE * 3)
    coordinates = _inverse_coordinates(clockwise=clockwise, angle_offset=angle_offset)
    for pixel, source_bit in enumerate(coordinates):
        if source_bit is None:
            continue
        byte, bit = divmod(source_bit, 8)
        mask = 0x80 >> bit
        for channel in range(3):
            if encoded[channel * FRAME_UNIT + byte] & mask:
                result[pixel * 3 + channel] = 255
    return bytes(result)


def render_bin(
    source: Path,
    destination: Path,
    *,
    fps: int = FPS,
    clockwise: bool = False,
    angle_offset: int = 0,
) -> int:
    """Write a playable H.264 MP4 preview and return its RGB-frame count."""
    if fps <= 0:
        raise ValueError("fps must be positive")
    info = inspect_bin(source)
    if info.trailing_bytes or info.frame_units % len(PLANES):
        raise ValueError("BIN does not contain complete 42ue RGB frame triplets")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found; install FFmpeg and retry")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{SOURCE_SIZE}x{SOURCE_SIZE}", "-framerate", str(fps), "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destination),
    ]
    frames = info.frame_units // len(PLANES)
    with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        assert process.stdin is not None
        with source.open("rb") as contents:
            for _ in range(frames):
                encoded = contents.read(FRAME_UNIT * len(PLANES))
                process.stdin.write(render_rgb_frame(encoded, clockwise=clockwise, angle_offset=angle_offset))
        process.stdin.close()
        stderr = process.stderr.read().decode(errors="replace") if process.stderr else ""
        if process.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.strip()}")
    return frames
