"""Upload an already converted BIN file using the observed V13 protocol."""

from __future__ import annotations

import socket
from pathlib import Path

from bin_format import inspect_bin, iter_chunks
from fan_protocol import DEFAULT_HOST, DEFAULT_PORT, FRAME_END, FRAME_START, _receive_one_frame, encode_command_payload

UPLOAD_SESSION_MARKER = b"B2DDDDEDC0EEBDF9E5B7"


def upload_bin(path: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *, remote_name: str | None = None, replace: bool = False) -> int:
    """Upload a BIN; replacement is explicit because the device has no trash."""
    path = path.resolve()
    info = inspect_bin(path)
    name = remote_name or path.name
    if not name.lower().endswith(".bin"):
        raise ValueError("remote_name must end with .BIN")
    if not name or any(char in name for char in "\\/:*?\"<>|\x00"):
        raise ValueError("remote_name contains an invalid filename character")
    if not replace:
        raise ValueError("upload requires explicit replace=True")
    with socket.create_connection((host, port), timeout=10) as connection:
        connection.settimeout(10)
        connection.sendall(UPLOAD_SESSION_MARKER)
        connection.sendall(FRAME_START + encode_command_payload(name.encode("ascii")) + FRAME_END)
        _receive_one_frame(connection)
        sent = 0
        for block in iter_chunks(path):
            connection.sendall(block)
            sent += len(block)
        connection.sendall(UPLOAD_SESSION_MARKER)
        connection.shutdown(socket.SHUT_WR)
    if sent != info.size:
        raise IOError(f"uploaded {sent} bytes, expected {info.size}")
    return sent
