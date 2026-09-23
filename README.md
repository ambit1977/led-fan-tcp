# fanctl-python

macOS-native, dependency-free TCP client for the 42 cm 3D Circle LED fan.

While connected to the fan's Wi-Fi access point, query the SD-card index:

```sh
python3 fanctl.py list
python3 fanctl.py power
python3 fanctl.py upload /path/to/video.BIN
```

The verified controller endpoint is `192.168.4.1:20320`; override it with
`--host` and `--port` if needed. The verified frame is:

```text
C0EEB7C9BAA3 + payload + C0EEBDF9E5B7
```

`list` sends the empty vendor discovery frame and is read-only. It returns the
controller's `i` SD-card index. `power` first performs that mandatory
per-connection discovery handshake, then sends the vendor application's
power-toggle command. `raw <hex-payload>` remains deliberately low-level
protocol-research support; file upload is exposed through the safer `upload`
command below, while delete and format commands remain unavailable.

`upload` implements the observed V13 BIN streaming sequence and validates the
existing `.BIN` trailer. Video-to-BIN LED rasterization is model-specific and
is kept separate until its format is fully decoded. Existing remote names are
rejected by default; use `--replace` only when replacement is intentional.
The transport has been verified against a 42ue sample: `01KADO.BIN`
(12,386,356 bytes) appeared as `01KADO` in the controller's SD-card index.

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
