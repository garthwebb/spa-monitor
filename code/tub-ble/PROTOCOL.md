# ACC SmarTouch BWF-200 Bluetooth protocol

Decoded on 2026-10-16 from iPhone PacketLogger captures of the SmarTouch iOS app
(`tools/pklg_decode.py`), then confirmed by driving the tub from a Mac with `tub.py`.

## Hardware

- ACC (Applied Computer Controls) SmarTouch Digital pack with the BWF-200 Wi-Fi/Bluetooth module.
- The module is an ESP32. Wi-Fi MAC `10:97:bd:36:93:c8` (192.168.3.108), Bluetooth MAC is Wi-Fi MAC + 2
  (`10:97:bd:36:93:ca`). It advertises as **`CedarTub`**.
- Wi-Fi only talks TLS to ACC's cloud; no local TCP/UDP control ports are open.
- Bluetooth accepts **one connection at a time**. While the phone app is connected over Bluetooth the
  module stops advertising. After a disconnect it takes 10-40 s to advertise again, and a connection
  takes 14-30 s to establish from macOS.

## GATT

Service `c5a092a5-2202-4ac6-8734-2e8ff796094d`. Handles are from the captures and may differ; use UUIDs.

| Handle | UUID | Props | Use |
|---|---|---|---|
| 0x2a | `12ead13c-4d06-48b7-a3f9-cdf725acdd87` | write | Light: ASCII `l0` **toggles** the light |
| 0x2c | `0daecf8f-2352-4ae8-bdb8-4ae862f041e3` | write | Setpoint: ASCII e.g. `102F` |
| 0x2e | `8cea517c-2d76-4190-ae05-2e222a3caacb` | write | Unknown (not used by light/temp) |
| 0x30 | `c67c0b5f-0f50-44fc-a0f9-449ff1f476f1` | write | Unknown |
| 0x32 | `30105eb3-19dc-4621-a227-a917b43162a6` | read, notify | Status / panel display mirror (below) |
| 0x35 | `5eb76cac-ada4-43c2-9ed0-b80547542e9f` | write | Unknown |
| 0x37 | `207da212-c2fd-43b5-9664-ac15166364d2` | read | Firmware: `{"v":"0.1.5","ptype":1}` |
| 0x39 | `aefc6b90-26f1-4842-b720-3d47f4a087cf` | read | Wi-Fi MAC as ASCII hex |
| 0x3b | `984cdbfb-446b-43b2-a879-c857a9a0f638` | read, write, notify | Auth state; notifies `M` after unlock |
| 0x3e | `6436e996-e573-4ff7-83fd-d0ea0bd09458` | write | Unlock string (30 ASCII chars, sent as 20 + 10 bytes) |
| 0x40 | `f8733ee9-6e45-485a-a8a1-9e4e8bdb0536` | write | Unknown |
| 0x42 | `71d67ace-65d6-4d28-b08f-f54735e7d50c` | read, notify | Unknown; the app subscribes but nothing arrived |

The unknown write characteristics are likely jets/pumps/blower; a capture of those buttons would identify them.

## Session

The app does, in order:

1. Enable notifications on 0x3b, 0x32 and 0x42.
2. Read 0x39 (MAC) and 0x37 (version).
3. Write the unlock string to 0x3e; 0x3b notifies `M`.
4. Read 0x32 for the current status.

**Without step 3, reads work but writes are silently ignored** (the write succeeds at the GATT level and
nothing changes). The unlock string is stored in `tub_config.json`, which is gitignored. It is unknown whether
it is fixed per module, derived from the MAC, or issued/rotated by ACC's cloud; if commands stop working,
take a fresh capture and compare.

## Status (0x32), 6 bytes

```
f1 4f 3f 06 08 10
│  └──┬───┘  │  └─ byte 5: 0x10 = light on
│     │      └──── byte 4: 0x20 = setpoint edit mode; 0x01 seen in one capture (heater?); 0x08 always set so far
│     └─────────── bytes 1-3: 7-segment digits, right to left ("103" here); 00 00 00 = blank
└───────────────── byte 0: always f1
```

Segment codes are the standard gfedcba encoding: `3f`=0 `06`=1 `5b`=2 `4f`=3 `66`=4 `6d`=5 `7d`=6 `07`=7 `7f`=8 `6f`=9.

Outside edit mode the display shows the water temperature.

## Setting the temperature

Writing `102F` makes the module emulate panel button presses: the display enters edit mode (byte 4 bit
0x20) and blinks (alternating blank frames) while stepping from the old setpoint to the new one, then
returns to the water temperature after a few seconds. The last digits shown in edit mode are the new
setpoint. Example from going 103F to 102F:

```
f1 00 00 00 08 00   blank
f1 4f 3f 06 28 00   "103" editing
f1 00 00 00 08 00   blank
f1 5b 3f 06 28 00   "102" editing
f1 4f 3f 06 08 00   "103" water temp, edit mode over
```
