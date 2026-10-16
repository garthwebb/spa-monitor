#!/usr/bin/env python3
"""Dump GATT traffic from an Apple PacketLogger (.pklg) capture.

    python tools/pklg_decode.py "Tub BLE Log 2.pklg"

Prints connections, discovered characteristics (value handle -> UUID) and every
ATT write, read response and notification, with ASCII shown where printable.
"""

import datetime
import struct
import sys
import uuid

ATT_CID = 0x0004
OPS = {0x0B: "READ", 0x12: "WRITE", 0x52: "WRITE-NR", 0x1B: "NOTIFY", 0x1D: "INDICATE"}
PROPS = {0x02: "read", 0x04: "write-nr", 0x08: "write", 0x10: "notify", 0x20: "indicate"}


def records(path):
    data = open(path, "rb").read()
    i = 0
    while i + 13 <= len(data):
        length, = struct.unpack_from("<I", data, i)
        sec, usec = struct.unpack_from("<II", data, i + 4)
        yield sec + usec / 1e6, data[i + 12], data[i + 13:i + 4 + length]
        i += 4 + length


def att_packets(path):
    """Yield (timestamp, direction, conn_handle, peer_address, att_pdu); direction is '>' sent, '<' received."""
    peers, partial = {}, {}
    for ts, kind, d in records(path):
        if kind == 1 and len(d) > 13 and d[0] == 0x3E and d[2] in (0x01, 0x0A) and d[3] == 0:
            handle, = struct.unpack_from("<H", d, 4)
            peers[handle] = ":".join(f"{b:02x}" for b in reversed(d[8:14]))
            yield ts, "CONNECT", handle, peers[handle], b""
        elif kind in (2, 3) and len(d) >= 4:
            flags, length = struct.unpack_from("<HH", d, 0)
            handle, boundary, payload = flags & 0xFFF, (flags >> 12) & 3, d[4:4 + length]
            key = (handle, kind)
            if boundary in (0, 2) and len(payload) >= 4:
                l2cap_len, cid = struct.unpack_from("<HH", payload, 0)
                partial[key] = [l2cap_len, cid, bytearray(payload[4:])]
            elif boundary == 1 and key in partial:
                partial[key][2] += payload
            else:
                continue
            l2cap_len, cid, buf = partial[key]
            if len(buf) >= l2cap_len:
                del partial[key]
                if cid == ATT_CID:
                    yield ts, ">" if kind == 2 else "<", handle, peers.get(handle, "?"), bytes(buf[:l2cap_len])


def main(path):
    for ts, direction, handle, peer, pdu in att_packets(path):
        when = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]
        if direction == "CONNECT":
            print(f"{when} connect {peer} (handle 0x{handle:03x})")
            continue
        op = pdu[0]
        if op == 0x09 and len(pdu) > 1 and pdu[1] == 21:  # characteristic discovery, 128-bit UUIDs
            for i in range(2, len(pdu), 21):
                entry = pdu[i:i + 21]
                value_handle = int.from_bytes(entry[3:5], "little")
                props = "+".join(name for bit, name in PROPS.items() if entry[2] & bit)
                print(f"{when}   char 0x{value_handle:02x} {uuid.UUID(bytes=bytes(entry[5:21][::-1]))} {props}")
        elif op in OPS:
            att_handle = "" if op == 0x0B else f"0x{int.from_bytes(pdu[1:3], 'little'):02x}"
            body = pdu[1:] if op == 0x0B else pdu[3:]
            text = body.decode() if body and all(32 <= c < 127 for c in body) else ""
            print(f"{when} {direction} {OPS[op]:8} {att_handle:5} {body.hex():40} {text}")


if __name__ == "__main__":
    main(sys.argv[1])
