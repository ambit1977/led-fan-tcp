# fanctl-python

macOS-native, dependency-free TCP client for the 42 cm 3D Circle LED fan.

While connected to the fan's Wi-Fi access point, query the SD-card index:

```sh
python3 fanctl.py list
```

The verified controller endpoint is `192.168.4.1:20320`; override it with
`--host` and `--port` if needed. The verified frame is:

```text
C0EEB7C9BAA3 + payload + C0EEBDF9E5B7
```

`list` sends the empty vendor discovery frame and is read-only. It returns the
controller's `\0hfi` SD-card index. `raw <hex-payload>` is deliberately
low-level protocol-research support: upload, delete, and play commands are not
exposed until their packet formats are confirmed.

## Multiple clients

Two simultaneous TCP discovery requests from the same host both returned valid
`hfi` replies from the controller. Read-only index requests can therefore
coexist. The vendor applications also contain an `otherdevicesending` error,
which indicates that file transfer is single-writer. Treat playback and setting
changes as shared device state: the protocol has no observed client ownership
or authentication, so do not issue competing control commands from multiple
clients.

Run the offline parser tests with:

```sh
python3 -m unittest discover -s tests -v
```
