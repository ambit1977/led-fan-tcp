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
POWER_TOGGLE = b"a"



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


def encode_command_payload(payload: bytes) -> bytes:
    """Encode the vendor's three-byte payload-length header.

    The V13 Windows application encodes non-empty commands in mixed radix
    323 (= 19 * 17). For example, the one-byte power command `a` is sent as
    `00 63 63 61` after the frame start marker. Empty discovery is the sole
    known command without this header.
    """
    if not payload:
        return b""
    high, remainder = divmod(len(payload), 19 * 17)
    middle, low = divmod(remainder, 17)
    if high > 0xFF:
        raise ValueError("payload too large for the observed length header")
    return bytes((high, ord("c") + middle, ord("b") + low)) + payload


def decode_command_payload(frame: Frame) -> bytes:
    """Remove and validate the three-byte header of a non-empty response."""
    if len(frame.payload) < 3:
        raise ValueError("response is too short for a command payload header")
    high, middle, low = frame.payload[:3]
    if not (ord("c") <= middle < ord("c") + 19 and ord("b") <= low < ord("b") + 17):
        raise ValueError(f"invalid command payload header: {frame.payload[:3].hex()}")
    expected_length = high * (19 * 17) + (middle - ord("c")) * 17 + (low - ord("b"))
    payload = frame.payload[3:]
    if len(payload) != expected_length:
        raise ValueError(f"payload length mismatch: header={expected_length}, actual={len(payload)}")
    return payload


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
            # The controller can send unrelated index updates while its mobile
            # app holds another TCP session. A request has one C0 frame; stop
            # at its terminator instead of concatenating later broadcasts.
            if b"".join(received).endswith(FRAME_END):
                break
    return b"".join(received)


def exchange_command(
    payload: bytes,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    receive_window: float = 5.0,
) -> bytes:
    """Send a vendor command payload, including its required length header."""
    return exchange(Frame(encode_command_payload(payload)), host, port, receive_window=receive_window)


def request_file_index(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> list[str]:
    """Read the SD-card index with the vendor client's empty discovery frame."""
    response = exchange(Frame(b""), host, port)
    return parse_file_index(decode_command_payload(decode_frame(response)))


def toggle_power(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Toggle display/motor power after the mandatory index handshake.

    A newly opened connection accepts an empty discovery frame first.  Sending
    the otherwise-valid ``a`` command before that exchange makes this
    controller close the socket without applying the command.
    """
    with socket.create_connection((host, port), timeout=5.0) as connection:
        connection.settimeout(5.0)
        connection.sendall(Frame(b"").encode())
        index_reply = _receive_one_frame(connection)
        # Validate that this is the observed controller index reply before
        # issuing a state-changing command on the session.
        parse_file_index(decode_command_payload(decode_frame(index_reply)))
        connection.sendall(Frame(encode_command_payload(POWER_TOGGLE)).encode())
        _receive_one_frame(connection)


def _receive_one_frame(connection: socket.socket) -> bytes:
    """Read one complete C0-framed response from an already-open socket."""
    received: list[bytes] = []
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            break
        received.append(chunk)
        message = b"".join(received)
        if message.endswith(FRAME_END):
            return message
    raise ConnectionError("controller closed the connection before a complete frame")


def parse_file_index(body: bytes) -> list[str]:
    """Parse the verified `i` file-index reply without assuming its tail."""
    if not body.startswith(b"i"):
        raise ValueError(f"expected hfi index reply, got {body[:16].hex()}")

    cursor = 1
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
