"""TCP framing for the 42 cm 3D Circle controller.

Evidence for this implementation comes from the bundled Windows controller,
the Mac-compatible iPhone application, and a successful exchange with the
connected controller. Only the empty discovery request and its `hfi` reply
are assigned a semantic meaning here.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass


FRAME_START = b"C0EEB7C9BAA3"
FRAME_END = b"C0EEBDF9E5B7"
DEFAULT_HOST = "192.168.4.1"
DEFAULT_PORT = 20320


@dataclass(frozen=True)
class Frame:
    """One protocol frame, without interpreting its payload."""

    payload: bytes

    def encode(self) -> bytes:
        return FRAME_START + self.payload + FRAME_END


def decode_frame(data: bytes) -> Frame:
    if not data.startswith(FRAME_START):
        raise ValueError("response is missing the C0EEB7C9BAA3 frame start")
    if not data.endswith(FRAME_END):
        raise ValueError("response is missing the C0EEBDF9E5B7 frame end")
    return Frame(data[len(FRAME_START) : -len(FRAME_END)])


def exchange(
    frame: Frame,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    receive_window: float = 5.0,
) -> bytes:
    """Send exactly one frame and gather reply data during `receive_window`."""
    with socket.create_connection((host, port), timeout=3) as connection:
        connection.settimeout(0.5)
        connection.sendall(frame.encode())
        received: list[bytes] = []
        deadline = time.monotonic() + receive_window
        while time.monotonic() < deadline:
            try:
                block = connection.recv(65_535)
            except socket.timeout:
                continue
            if not block:
                break
            received.append(block)
    return b"".join(received)


def request_file_index(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> list[str]:
    """Read the SD-card index with the vendor client's empty discovery frame."""
    response = exchange(Frame(b""), host, port)
    return parse_file_index(decode_frame(response))


def parse_file_index(frame: Frame) -> list[str]:
    """Parse the verified `\\0hfi` file-index reply without assuming its tail."""
    body = frame.payload
    if not body.startswith(b"\x00hfi"):
        raise ValueError(f"expected hfi index reply, got {body[:16].hex()}")

    cursor = 4
    names: list[str] = []
    while cursor < len(body):
        length = body[cursor]
        cursor += 1
        if length == 0 or cursor + length > len(body):
            break
        value = body[cursor : cursor + length]
        if any(byte < 0x20 or byte > 0x7E for byte in value):
            break
        names.append(value.decode("ascii"))
        cursor += length
    return names
