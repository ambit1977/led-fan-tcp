# fanctl-python

macOS-native, dependency-free TCP client for the 42 cm 3D Circle LED fan.

While connected to the fan's Wi-Fi access point, query the SD-card index:

```sh
python3 fanctl.py list
python3 fanctl.py power
python3 fanctl.py upload /path/to/already-converted.BIN
python3 fanctl.py convert /path/to/movie.mp4 --output /path/to/MOVIE.BIN
python3 fanctl.py convert-upload /path/to/movie.mp4 --output /path/to/MOVIE.BIN
python3 fanctl.py preview /path/to/MOVIE.BIN --output /path/to/MOVIE-preview.mp4
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
existing `.BIN` trailer. `convert` uses the locally installed `ffmpeg` to
scale from the short side and centre-crop a 256px square, maps it to the observed 224x128 polar
raster, and writes RGB as three one-bit device frames. `convert-upload` does
the same then uploads the generated BIN. Existing remote names are rejected by
default; use `--replace` only when replacement is intentional.

The encoder is based on the vendor's 224-angle, 128-radius frame structure and
has offline packing tests. Orientation is installation-specific: use
`--clockwise` and `--angle-offset` after a short physical test clip, rather
than uploading a long unverified video. The vendor manual limits a video to 15
minutes; the converter enforces that limit.

`preview` reverses those 42ue RGB bit planes into a normal 256px H.264 MP4 for
macOS playback. It is a decoding preview, not a measurement of the physical
fan's persistence-of-vision output.
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
