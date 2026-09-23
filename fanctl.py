#!/usr/bin/env python3
"""Dependency-free CLI for the 3D Circle / 42 cm fan TCP service."""

from __future__ import annotations

import argparse
from pathlib import Path

from fan_protocol import DEFAULT_HOST, DEFAULT_PORT, exchange_command, request_file_index, toggle_power
from upload import upload_bin


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "power", "upload", "raw"))
    parser.add_argument("payload", nargs="?", help="hex payload for raw (without frame markers)")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--replace", action="store_true", help="allow replacing an existing remote BIN")
    args = parser.parse_args()

    if args.command == "list":
        names = request_file_index(args.host, args.port)
        print(f"controller={args.host}:{args.port}")
        print(f"entries={len(names)}")
        for number, name in enumerate(names, 1):
            print(f"{number:>2}: {name}")
        return

    if args.command == "power":
        toggle_power(args.host, args.port)
        print("power toggle sent (the controller does not acknowledge this command)")
        return

    if args.command == "upload":
        if not args.payload:
            parser.error("upload requires a local .BIN path")
        local_path = Path(args.payload)
        remote_name = local_path.name
        if not args.replace:
            existing = {name.casefold() for name in request_file_index(args.host, args.port)}
            if remote_name.casefold() in existing:
                parser.error(f"remote file already exists: {remote_name}; pass --replace explicitly")
        sent = upload_bin(local_path, args.host, args.port, replace=True)
        print(f"uploaded={sent} bytes")
        return

    if not args.payload:
        parser.error("raw requires a hexadecimal payload")
    try:
        payload = bytes.fromhex(args.payload)
    except ValueError as error:
        parser.error(f"invalid hexadecimal payload: {error}")
    print(exchange_command(payload, args.host, args.port).hex())


if __name__ == "__main__":
    main()
