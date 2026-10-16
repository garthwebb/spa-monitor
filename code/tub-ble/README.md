# tub-ble

Local Bluetooth control of the ACC SmarTouch spa (BWF-200 module), no cloud. Protocol details in
[PROTOCOL.md](PROTOCOL.md).

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp tub_config.example.json tub_config.json   # then fill in unlock_token
```

`tub_config.json` is gitignored because it holds the unlock token. To recover the token from a
capture, run `tools/pklg_decode.py` on it and join the two writes to handle `0x3e`.

## Usage

```sh
.venv/bin/python tub.py status        # display, water temp, light
.venv/bin/python tub.py info          # firmware version, Wi-Fi MAC
.venv/bin/python tub.py light on      # on | off | toggle
.venv/bin/python tub.py temp 102      # setpoint in F (80-104)
.venv/bin/python tub.py watch         # stream status changes
```

From code:

```python
async with Tub.from_config() as tub:
    print(tub.status.water_temp)
    await tub.set_light(True)
    await tub.set_temperature(102)
```

## Notes

- The module allows one Bluetooth connection at a time. Close the SmarTouch app (or turn off the
  phone's Bluetooth) or the tub won't be found.
- Connecting is slow: 14-30 s to connect, and after a disconnect the module takes another 10-40 s
  to start advertising again (measured 2026-10-16). `connect()` retries for up to 2 minutes. For
  automations, prefer one long-lived connection (it also streams status changes) over a new
  connection per command.
- On macOS, run from Terminal.app. macOS kills Bluetooth use from processes whose parent app lacks a
  Bluetooth usage description (e.g. Claude Code), even if Bluetooth permission was granted.
- Bluetooth range is ~10 m, so a permanent setup needs a host near the tub (Raspberry Pi, or an
  ESP32 running the same sequence).
