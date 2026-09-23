#!/usr/bin/env python3
"""Dependency-free CLI for the 3D Circle / 42 cm fan TCP service."""

from __future__ import annotations

import argparse

from fan_protocol import DEFAULT_HOST, DEFAULT_PORT, Frame, exchange, request_file_index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "raw"))
    parser.add_argument("payload", nargs="?", help="hex payload for raw (without frame markers)")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.command == "list":
        names = request_file_index(args.host, args.port)
        print(f"controller={args.host}:{args.port}")
        print(f"entries={len(names)}")
        for number, name in enumerate(names, 1):
            print(f"{number:>2}: {name}")
        return

    if not args.payload:
        parser.error("raw requires a hexadecimal payload")
    try:
        payload = bytes.fromhex(args.payload)
    except ValueError as error:
        parser.error(f"invalid hexadecimal payload: {error}")
    print(exchange(Frame(payload), args.host, args.port).hex())


if __name__ == "__main__":
    main()
