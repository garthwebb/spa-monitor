#!/usr/bin/env python3
"""Local Bluetooth LE client for the ACC SmarTouch BWF-200 spa module.

See PROTOCOL.md for how the module's GATT interface was decoded.

    python tub.py status
    python tub.py light on|off|toggle
    python tub.py temp 102
    python tub.py watch
"""

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

CONFIG_PATH = Path(__file__).with_name("tub_config.json")

SERVICE = "c5a092a5-2202-4ac6-8734-2e8ff796094d"
CHAR_LIGHT = "12ead13c-4d06-48b7-a3f9-cdf725acdd87"
CHAR_SETPOINT = "0daecf8f-2352-4ae8-bdb8-4ae862f041e3"
CHAR_STATUS = "30105eb3-19dc-4621-a227-a917b43162a6"
CHAR_VERSION = "207da212-c2fd-43b5-9664-ac15166364d2"
CHAR_WIFI_MAC = "aefc6b90-26f1-4842-b720-3d47f4a087cf"
CHAR_AUTH_STATE = "984cdbfb-446b-43b2-a879-c857a9a0f638"
CHAR_UNLOCK = "6436e996-e573-4ff7-83fd-d0ea0bd09458"

# Standard 7-segment encoding (bit 0 = segment a ... bit 6 = segment g)
SEGMENTS = {
    0x3F: "0", 0x06: "1", 0x5B: "2", 0x4F: "3", 0x66: "4",
    0x6D: "5", 0x7D: "6", 0x07: "7", 0x7F: "8", 0x6F: "9",
    0x00: " ", 0x40: "-", 0x71: "F", 0x39: "C",
}

FLAG_EDITING = 0x20  # status byte 4: setpoint edit mode
FLAG_LIGHT = 0x10    # status byte 5: light on

MIN_SETPOINT_F = 80
MAX_SETPOINT_F = 104
MAX_WRITE = 20  # ATT payload limit at the default MTU of 23


@dataclass
class Status:
    raw: bytes

    @property
    def display(self) -> str:
        # The three digits arrive right-to-left
        return "".join(SEGMENTS.get(b, "?") for b in reversed(self.raw[1:4]))

    @property
    def number(self) -> Optional[int]:
        text = self.display.strip()
        return int(text) if text.isdigit() else None

    @property
    def light(self) -> bool:
        return bool(self.raw[5] & FLAG_LIGHT)

    @property
    def editing(self) -> bool:
        return bool(self.raw[4] & FLAG_EDITING)

    @property
    def blank(self) -> bool:
        return self.raw[1:4] == b"\x00\x00\x00"

    @property
    def water_temp(self) -> Optional[int]:
        # Outside edit mode the panel shows the water temperature
        return None if self.editing or self.blank else self.number

    def __str__(self) -> str:
        return (f"display={self.display!r} water={self.water_temp} light={'on' if self.light else 'off'} "
                f"editing={self.editing} flags=0x{self.raw[4]:02x}/0x{self.raw[5]:02x} raw={self.raw.hex()}")


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        raise SystemExit(f"Missing {path.name}; copy tub_config.example.json and fill in unlock_token")
    return json.loads(path.read_text())


class Tub:
    def __init__(self, unlock_token: str, name: str = "CedarTub", address: Optional[str] = None):
        self.unlock_token = unlock_token.encode()
        self.name = name
        self.address = address
        self.client: Optional[BleakClient] = None
        self.status: Optional[Status] = None
        self._listeners: list[Callable[[Status], None]] = []
        self._changed = asyncio.Event()

    @classmethod
    def from_config(cls, path: Path = CONFIG_PATH) -> "Tub":
        cfg = load_config(path)
        return cls(cfg["unlock_token"], cfg.get("name", "CedarTub"), cfg.get("address"))

    async def __aenter__(self) -> "Tub":
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()

    async def connect(self, timeout: float = 120) -> None:
        # The module is slow to resume advertising after a disconnect, so keep retrying until the deadline
        deadline = time.monotonic() + timeout
        last_error: Exception = ConnectionError(f"{self.address or self.name} not found; is another phone connected to it?")
        while time.monotonic() < deadline:
            try:
                await self._connect_once(scan_timeout=min(15, max(1.0, deadline - time.monotonic())))
                return
            except (TimeoutError, asyncio.TimeoutError, BleakError, ConnectionError) as e:
                last_error = e
                await self.disconnect()
                await asyncio.sleep(3)
        raise last_error

    async def _connect_once(self, scan_timeout: float) -> None:
        if self.address:
            device = await BleakScanner.find_device_by_address(self.address, timeout=scan_timeout)
        else:
            device = await BleakScanner.find_device_by_name(self.name, timeout=scan_timeout)
        if device is None:
            raise ConnectionError(f"{self.address or self.name} not found; is another phone connected to it?")
        self.client = BleakClient(device, timeout=15)
        await self.client.connect()
        await self.client.start_notify(CHAR_STATUS, self._on_status)
        await self._unlock()
        self._set_status(bytes(await self.client.read_gatt_char(CHAR_STATUS)))

    async def disconnect(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def _unlock(self) -> None:
        # Without this the module accepts writes but ignores them
        for i in range(0, len(self.unlock_token), MAX_WRITE):
            await self.client.write_gatt_char(CHAR_UNLOCK, self.unlock_token[i:i + MAX_WRITE], response=True)
        await asyncio.sleep(0.5)

    def _on_status(self, _sender, data: bytearray) -> None:
        self._set_status(bytes(data))

    def _set_status(self, raw: bytes) -> None:
        self.status = Status(raw)
        self._changed.set()
        for listener in self._listeners:
            listener(self.status)

    def add_listener(self, fn: Callable[[Status], None]) -> None:
        self._listeners.append(fn)

    async def _wait_for(self, predicate: Callable[[Status], bool], timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while not predicate(self.status):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self._changed.clear()
            try:
                await asyncio.wait_for(self._changed.wait(), remaining)
            except asyncio.TimeoutError:
                return False
        return True

    async def info(self) -> dict:
        return {
            "version": json.loads(bytes(await self.client.read_gatt_char(CHAR_VERSION))),
            "wifi_mac": bytes(await self.client.read_gatt_char(CHAR_WIFI_MAC)).decode(),
            "auth_state": bytes(await self.client.read_gatt_char(CHAR_AUTH_STATE)).decode(),
        }

    async def toggle_light(self) -> bool:
        before = self.status.light
        await self.client.write_gatt_char(CHAR_LIGHT, b"l0", response=True)
        if not await self._wait_for(lambda s: s.light != before, timeout=5):
            raise TimeoutError("light did not change; unlock token may be wrong")
        return self.status.light

    async def set_light(self, on: bool) -> bool:
        # The module only offers a toggle
        if self.status.light != on:
            await self.toggle_light()
        return self.status.light

    async def set_temperature(self, fahrenheit: int, timeout: float = 30) -> int:
        """Set the setpoint and wait for the panel to leave edit mode. Returns the setpoint the panel showed."""
        if not MIN_SETPOINT_F <= fahrenheit <= MAX_SETPOINT_F:
            raise ValueError(f"setpoint must be {MIN_SETPOINT_F}-{MAX_SETPOINT_F}F")
        shown: list[int] = []

        def track(s: Status) -> None:
            if s.editing and s.number is not None:
                shown.append(s.number)

        self._listeners.append(track)
        try:
            await self.client.write_gatt_char(CHAR_SETPOINT, f"{fahrenheit}F".encode(), response=True)
            if not await self._wait_for(lambda s: s.editing or s.blank, timeout=5):
                raise TimeoutError("panel never entered edit mode")
            if not await self._wait_for(lambda s: not s.editing and not s.blank, timeout=timeout):
                raise TimeoutError("panel stayed in edit mode")
        finally:
            self._listeners.remove(track)
        if not shown:
            raise RuntimeError("panel never displayed a setpoint while editing; result unknown")
        if shown[-1] != fahrenheit:
            raise RuntimeError(f"panel showed setpoint {shown[-1]}F, expected {fahrenheit}F")
        return shown[-1]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("info")
    light = sub.add_parser("light")
    light.add_argument("state", choices=["on", "off", "toggle"])
    temp = sub.add_parser("temp")
    temp.add_argument("fahrenheit", type=int)
    watch = sub.add_parser("watch")
    watch.add_argument("--seconds", type=float, default=0, help="stop after N seconds (default: run forever)")
    args = parser.parse_args()

    async with Tub.from_config() as tub:
        if args.cmd == "status":
            print(tub.status)
        elif args.cmd == "info":
            print(json.dumps(await tub.info(), indent=2))
        elif args.cmd == "light":
            on = await (tub.toggle_light() if args.state == "toggle" else tub.set_light(args.state == "on"))
            print(f"light {'on' if on else 'off'}")
        elif args.cmd == "temp":
            print(f"setpoint {await tub.set_temperature(args.fahrenheit)}F; {tub.status}")
        elif args.cmd == "watch":
            print(tub.status)
            tub.add_listener(lambda s: print(time.strftime("%H:%M:%S"), s))
            await asyncio.sleep(args.seconds or float("inf"))


if __name__ == "__main__":
    asyncio.run(main())
