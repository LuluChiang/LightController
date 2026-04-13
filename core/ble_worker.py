import asyncio
import logging
import threading
import traceback
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    BleakScanner = None
    BleakClient = None

from core.device import Device, DeviceState
from core.ble_protocol import WRITE_UUID, NOTIFY_UUID, DEVICE_NAME_FILTER, build_command, build_off_command, CMD_ON

logging.basicConfig(
    filename="lightcontroller.log",
    filemode="a",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


class BleWorker(QThread):
    # Emitted after a scan completes
    scan_finished       = pyqtSignal(list)      # list[Device]
    # Emitted when a device connects or fails
    device_connected    = pyqtSignal(str)       # address
    device_failed       = pyqtSignal(str, str)  # address, error_message
    device_disconnected = pyqtSignal(str)       # address
    # Emitted when a GATT write fails
    command_error       = pyqtSignal(str, str)  # address, error_message
    # General status text for the status bar
    status_message      = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_ready = threading.Event()
        # address -> BleakClient; mutated only from the asyncio loop thread
        self._clients: dict[str, "BleakClient"] = {}

    # ------------------------------------------------------------------ #
    # QThread entry point
    # ------------------------------------------------------------------ #
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_forever()

    def stop(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()

    # ------------------------------------------------------------------ #
    # Public API — called from the Qt main thread
    # ------------------------------------------------------------------ #
    def request_scan(self):
        self._submit(self._scan())

    def request_connect(self, device: Device):
        self._submit(self._connect(device))

    def request_disconnect(self, address: str):
        self._submit(self._disconnect(address))

    def request_send_command(self, address: str, r: int, g: int, b: int, brightness: int):
        self._submit(self._send_command(address, r, g, b, brightness))

    def request_send_command_all(self, r: int, g: int, b: int, brightness: int):
        self._submit(self._send_command_all(r, g, b, brightness))

    def request_power_off(self, address: str):
        self._submit(self._power_off(address))

    def request_power_off_all(self):
        self._submit(self._power_off_all())

    def request_probe(self, address: str):
        self._submit(self._probe(address))

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _submit(self, coro):
        """Thread-safe submission of a coroutine to the worker loop."""
        self._loop_ready.wait()
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    # ------------------------------------------------------------------ #
    # Async implementations (run on the asyncio loop thread)
    # ------------------------------------------------------------------ #
    async def _scan(self):
        if BleakScanner is None:
            self.status_message.emit("Error: bleak library is not installed.")
            self.scan_finished.emit([])
            return

        self.status_message.emit("Scanning for BLE devices...")
        try:
            raw = await BleakScanner.discover(timeout=5.0)
            devices = [
                Device(name=d.name, address=d.address)
                for d in raw
                if d.name and DEVICE_NAME_FILTER in d.name
            ]
            log.info("Scan complete — found %d device(s): %s",
                     len(devices), [d.address for d in devices])
            self.scan_finished.emit(devices)
            self.status_message.emit(f"Scan complete — found {len(devices)} device(s).")
        except Exception:
            log.error("Scan failed:\n%s", traceback.format_exc())
            self.status_message.emit(f"Scan failed — see lightcontroller.log")
            self.scan_finished.emit([])

    async def _connect(self, device: Device):
        if BleakClient is None:
            self.device_failed.emit(device.address, "bleak not installed")
            return

        log.info("Connecting to %s (%s)...", device.name, device.address)
        self.status_message.emit(f"Connecting to {device.name}...")
        try:
            client = BleakClient(
                device.address,
                disconnected_callback=lambda c: self._on_disconnect(c.address),
            )
            await client.connect(timeout=10.0)
            self._clients[device.address] = client

            # Subscribe to notify characteristic and record any challenge bytes
            try:
                self._last_notify: dict[str, bytes] = getattr(self, "_last_notify", {})

                def _on_notify(sender, data):
                    log.debug("NOTIFY from %s: %s", device.address, data.hex())
                    self._last_notify[device.address] = data

                await client.start_notify(NOTIFY_UUID, _on_notify)
                log.info("Subscribed to notifications on %s", NOTIFY_UUID)
            except Exception:
                log.warning("Could not subscribe to notify: %s", traceback.format_exc().splitlines()[-1])

            # Read fff3 to discover device state / protocol hints
            try:
                val = await client.read_gatt_char(WRITE_UUID)
                log.info("READ fff3 on connect: %s", val.hex())
            except Exception:
                log.warning("READ fff3 failed: %s", traceback.format_exc().splitlines()[-1])

            log.info("Connected to %s. Full GATT profile:", device.name)
            for service in client.services:
                log.info("  SERVICE  %s  (%s)", service.uuid, service.description)
                for char in service.characteristics:
                    log.info("    CHAR   %s  props=%s  (%s)",
                             char.uuid, char.properties, char.description)
            self.device_connected.emit(device.address)
            self.status_message.emit(f"Connected to {device.name}.")
        except Exception:
            log.error("Connection to %s failed:\n%s", device.address, traceback.format_exc())
            self.device_failed.emit(device.address, traceback.format_exc().splitlines()[-1])
            self.status_message.emit(f"Connection to {device.name} failed — see lightcontroller.log")

    async def _disconnect(self, address: str):
        client = self._clients.get(address)
        if client and client.is_connected:
            await client.disconnect()
        # disconnected_callback will fire and emit device_disconnected

    async def _write(self, address: str, command: bytes):
        """Write a raw command to a connected device. Emits command_error on failure."""
        client = self._clients.get(address)
        if not client or not client.is_connected:
            log.warning("_write(%s): not connected", address)
            self.command_error.emit(address, "Not connected")
            return
        log.debug("_write(%s): sending %s", address, command.hex())
        try:
            await client.write_gatt_char(WRITE_UUID, command, response=True)
            log.debug("_write(%s): OK", address)
        except Exception:
            log.error("_write(%s) failed:\n%s", address, traceback.format_exc())
            self.command_error.emit(address, traceback.format_exc().splitlines()[-1])

    async def _send_command(self, address: str, r: int, g: int, b: int, brightness: int):
        log.debug("_send_command(%s): r=%d g=%d b=%d brightness=%d", address, r, g, b, brightness)
        await self._write(address, CMD_ON)
        await self._write(address, build_command(r, g, b, brightness))

    async def _send_command_all(self, r: int, g: int, b: int, brightness: int):
        await asyncio.gather(*[
            self._send_command(addr, r, g, b, brightness)
            for addr in list(self._clients.keys())
        ])

    async def _power_off(self, address: str):
        await self._write(address, build_off_command())

    async def _power_off_all(self):
        await asyncio.gather(*[
            self._power_off(addr)
            for addr in list(self._clients.keys())
        ])

    async def _probe(self, address: str):
        """
        Systematically try known ELK-BLEDDM command formats.
        Each candidate is sent with a 1.5s gap so the device has time to respond.
        Watch lightcontroller.log for NOTIFY responses after each attempt.
        """
        client = self._clients.get(address)
        if not client or not client.is_connected:
            log.warning("probe: not connected to %s", address)
            return

        # Read current fff3 state before probing
        device_id = None
        try:
            device_id = await client.read_gatt_char(WRITE_UUID)
            log.info("PROBE READ fff3: %s  (ascii: %s)",
                     device_id.hex(), device_id.rstrip(b'\x00').decode("ascii", errors="replace"))
        except Exception:
            log.warning("PROBE READ fff3 failed: %s", traceback.format_exc().splitlines()[-1])

        # Also try reading fff4
        try:
            val4 = await client.read_gatt_char(NOTIFY_UUID)
            log.info("PROBE READ fff4: %s", val4.hex())
        except Exception:
            log.warning("PROBE READ fff4 failed: %s", traceback.format_exc().splitlines()[-1])

        # Echo back the last notify bytes as a potential challenge response
        challenge = getattr(self, "_last_notify", {}).get(address)
        challenge_candidates = []
        if challenge:
            log.info("PROBE last notify was: %s — will try echoing it back", challenge.hex())
            challenge_candidates = [
                (f"echo challenge back: {challenge.hex()}", challenge),
                (f"challenge XOR 0xFF: {bytes(b ^ 0xFF for b in challenge).hex()}",
                 bytes(b ^ 0xFF for b in challenge)),
            ]

        # Each candidate is tried twice: once with response=True, once response=False
        # Try writing the device ID back as an auth handshake
        auth_candidates = []
        if device_id:
            auth_candidates = [
                ("write device-ID back as auth", device_id),
                ("write first 4 bytes of device-ID", device_id[:4]),
            ]

        raw_candidates = [
            ("CC 23 33 power-on",      bytes([0xCC, 0x23, 0x33])),
            ("7-byte white 0xAA",      bytes([0x56, 0xFF, 0xFF, 0xFF, 0x00, 0xF0, 0xAA])),
        ] + challenge_candidates + auth_candidates

        candidates = []
        for label, cmd in raw_candidates:
            candidates.append((f"[resp=T] {label}", cmd, True))
            candidates.append((f"[resp=F] {label}", cmd, False))

        log.info("=== PROTOCOL PROBE START on %s ===", address)
        self.status_message.emit("Protocol probe running — watch lightcontroller.log …")

        for label, cmd, resp in candidates:
            log.info("PROBE trying [%s]: %s", label, cmd.hex())
            try:
                await client.write_gatt_char(WRITE_UUID, cmd, response=resp)
                log.info("PROBE sent OK — waiting 1.5s for device response …")
            except Exception:
                log.error("PROBE send failed: %s", traceback.format_exc().splitlines()[-1])
            await asyncio.sleep(1.5)

        log.info("=== PROTOCOL PROBE END ===")
        self.status_message.emit("Probe done — check lightcontroller.log for NOTIFY responses.")

    def _on_disconnect(self, address: str):
        """
        Called by BleakClient's disconnected_callback.
        Runs on the asyncio loop thread — emitting a Qt signal here is safe
        because PyQt6 auto-queues cross-thread signal emissions.
        """
        self._clients.pop(address, None)
        self.device_disconnected.emit(address)
