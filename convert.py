"""Video-to-BIN encoder for the 42ue / 3D Circle 224-pixel fan.

The vendor V13 decoder stores each colour video frame as three consecutive
1-bit polar rasters.  A raster is 224 angular samples by 128 radial samples,
packed MSB-first (224 * 128 / 8 == 3,584 bytes).  This module produces that
container from FFmpeg-decoded RGB frames.  The resulting image orientation is
kept configurable because the physical installation direction is a device
setting rather than a property recorded in a BIN file.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from bin_format import BIN_TRAILER, FRAME_UNIT


ANGLES = 224
RADIUS = 128
SOURCE_SIZE = RADIUS * 2
FPS = 30
PLANES = "rgb"


def _sample_coordinates(*, clockwise: bool, angle_offset: int) -> list[tuple[int, int]]:
    """Return source coordinates in BIN byte order, angle-major then radial."""
    result: list[tuple[int, int]] = []
    center = (SOURCE_SIZE - 1) / 2
    for angle in range(ANGLES):
        phase = (angle + angle_offset) * 2 * math.pi / ANGLES
        if clockwise:
            phase = -phase
        cos_phase, sin_phase = math.cos(phase), math.sin(phase)
        for radius in range(RADIUS):
            x = round(center + radius * cos_phase)
            y = round(center - radius * sin_phase)
            result.append((max(0, min(SOURCE_SIZE - 1, x)), max(0, min(SOURCE_SIZE - 1, y))))
    return result


def pack_rgb_frame(
    rgb: bytes,
    *,
    threshold: int = 128,
    clockwise: bool = False,
    angle_offset: int = 0,
) -> bytes:
    """Encode one ``256x256 rgb24`` input image as three 3,584-byte planes."""
    expected = SOURCE_SIZE * SOURCE_SIZE * 3
    if len(rgb) != expected:
        raise ValueError(f"expected {expected} RGB bytes, got {len(rgb)}")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be in 0..255")

    coordinates = _sample_coordinates(clockwise=clockwise, angle_offset=angle_offset)
    encoded = bytearray()
    for channel in range(3):
        plane = bytearray(FRAME_UNIT)
        for destination, (x, y) in enumerate(coordinates):
            source = (y * SOURCE_SIZE + x) * 3 + channel
            if rgb[source] >= threshold:
                plane[destination // 8] |= 0x80 >> (destination % 8)
        encoded.extend(plane)
    return bytes(encoded)


def _ffmpeg_command(source: Path, *, fps: int) -> list[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found; install FFmpeg and retry")
    # Scale from the short side until the source covers the whole square, then
    # crop the excess equally from the long side. This keeps a centred subject
    # and avoids letterbox bands on the circular display.
    vf = (
        f"fps={fps},scale={SOURCE_SIZE}:{SOURCE_SIZE}:force_original_aspect_ratio=increase,"
        f"crop={SOURCE_SIZE}:{SOURCE_SIZE}:(iw-ow)/2:(ih-oh)/2"
    )
    return [ffmpeg, "-v", "error", "-i", str(source), "-an", "-vf", vf,
            "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]


def convert_video(
    source: Path,
    destination: Path,
    *,
    fps: int = FPS,
    threshold: int = 128,
    clockwise: bool = False,
    angle_offset: int = 0,
    max_seconds: float | None = None,
) -> int:
    """Convert an ordinary video/image supported by FFmpeg to a V13 BIN.

    Returns the number of source video frames written.  A conservative
    15-minute limit matches the vendor manual unless ``max_seconds`` supplies
    a shorter explicit test limit.
    """
    if not source.is_file():
        raise FileNotFoundError(source)
    if fps <= 0:
        raise ValueError("fps must be positive")
    frame_bytes = SOURCE_SIZE * SOURCE_SIZE * 3
    limit = int(fps * (900 if max_seconds is None else max_seconds))
    if limit <= 0:
        raise ValueError("max_seconds must allow at least one frame")

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = _ffmpeg_command(source, fps=fps)
    completed_frames = 0
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        assert process.stdout is not None
        with destination.open("wb") as output:
            while block := process.stdout.read(frame_bytes):
                if len(block) != frame_bytes:
                    process.kill()
                    raise RuntimeError("ffmpeg ended with a partial RGB frame")
                if completed_frames >= limit:
                    process.kill()
                    raise ValueError("video exceeds the 15-minute device limit")
                output.write(pack_rgb_frame(block, threshold=threshold, clockwise=clockwise, angle_offset=angle_offset))
                completed_frames += 1
            stderr = process.stderr.read().decode(errors="replace") if process.stderr else ""
            if process.wait() != 0:
                raise RuntimeError(f"ffmpeg failed: {stderr.strip()}")
            if completed_frames == 0:
                raise RuntimeError("ffmpeg produced no video frames")
            output.write(BIN_TRAILER)
    return completed_frames
