from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStatusBar,
)
from PyQt6.QtCore import QTimer

from core.ble_worker import BleWorker
from core.device import Device, DeviceState
from core.scene_manager import SceneManager, Scene
from ui.device_panel import DevicePanel
from ui.control_panel import ControlPanel
from ui.scene_panel import ScenePanel

_LIVE_PUSH_DEBOUNCE_MS = 100


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Light Controller")
        self.setMinimumSize(1000, 600)

        self._scene_manager = SceneManager()
        self._worker = BleWorker()
        self._devices: dict[str, Device] = {}  # address -> Device

        # Debounce timer for live colour/brightness pushes
        self._live_push_timer = QTimer(self)
        self._live_push_timer.setSingleShot(True)
        self._live_push_timer.timeout.connect(self._push_live_state)

        self._build_ui()
        self._connect_signals()
        self._worker.start()

    # ── Build UI ──────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._device_panel  = DevicePanel()
        self._control_panel = ControlPanel()
        self._scene_panel   = ScenePanel(self._scene_manager)

        root.addWidget(self._device_panel,  stretch=1)
        root.addWidget(self._control_panel, stretch=2)
        root.addWidget(self._scene_panel,   stretch=1)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready.")

    # ── Wire signals ──────────────────────────────────────────────────
    def _connect_signals(self):
        w  = self._worker
        dp = self._device_panel
        cp = self._control_panel
        sp = self._scene_panel

        # Worker → MainWindow / UI
        w.scan_finished.connect(self._on_scan_finished)
        w.device_connected.connect(self._on_device_connected)
        w.device_failed.connect(self._on_device_failed)
        w.device_disconnected.connect(self._on_device_disconnected)
        w.status_message.connect(self._status_bar.showMessage)
        w.command_error.connect(
            lambda addr, msg: self._status_bar.showMessage(f"[{addr[-5:]}] Error: {msg}")
        )

        # DevicePanel → Worker / MainWindow
        dp.scan_requested.connect(w.request_scan)
        dp.connect_requested.connect(self._on_connect_requested)
        dp.disconnect_requested.connect(self._on_disconnect_requested)

        # ControlPanel → MainWindow / Worker
        cp.power_on_all_requested.connect(self._on_power_on_all)
        cp.power_off_all_requested.connect(self._on_power_off_all)
        cp.probe_requested.connect(self._on_probe)
        cp.color_changed.connect(self._on_color_or_brightness_changed)
        cp.brightness_changed.connect(self._on_color_or_brightness_changed)

        # ScenePanel → MainWindow
        sp.scene_apply_requested.connect(self._on_scene_apply)
        sp.scene_save_requested.connect(self._on_scene_save)

    # ── Helpers ───────────────────────────────────────────────────────
    def _get_control_state(self) -> tuple[int, int, int, int]:
        r, g, b = self._control_panel.get_color()
        return r, g, b, self._control_panel.get_brightness()

    def _update_device_state(self, address: str, state: DeviceState):
        if address in self._devices:
            self._devices[address].state = state
        self._device_panel.set_device_state(address, state)

    # ── Slots ─────────────────────────────────────────────────────────
    def _on_scan_finished(self, devices: list):
        self._devices = {d.address: d for d in devices}
        self._device_panel.populate_devices(devices)

    def _on_connect_requested(self, address: str):
        device = self._devices.get(address)
        if not device:
            return
        self._update_device_state(address, DeviceState.CONNECTING)
        self._worker.request_connect(device)

    def _on_disconnect_requested(self, address: str):
        self._worker.request_disconnect(address)

    def _on_device_connected(self, address: str):
        self._update_device_state(address, DeviceState.CONNECTED)

    def _on_device_failed(self, address: str, error: str):
        self._update_device_state(address, DeviceState.ERROR)

    def _on_device_disconnected(self, address: str):
        if address in self._devices:
            self._devices[address].is_on = False
        self._update_device_state(address, DeviceState.DISCONNECTED)
        self._status_bar.showMessage(f"Device {address[-5:]} disconnected.")

    def _on_power_on_all(self):
        r, g, b, brightness = self._get_control_state()
        for device in self._devices.values():
            if device.state == DeviceState.CONNECTED:
                device.is_on = True
        self._worker.request_send_command_all(r, g, b, brightness)

    def _on_power_off_all(self):
        for device in self._devices.values():
            if device.state == DeviceState.CONNECTED:
                device.is_on = False
        self._worker.request_power_off_all()

    def _on_color_or_brightness_changed(self):
        # Debounce rapid slider movement to avoid flooding BLE with writes
        self._live_push_timer.start(_LIVE_PUSH_DEBOUNCE_MS)

    def _push_live_state(self):
        r, g, b, brightness = self._get_control_state()
        for address, device in self._devices.items():
            if device.state == DeviceState.CONNECTED and device.is_on:
                self._worker.request_send_command(address, r, g, b, brightness)

    def _on_scene_apply(self, scene: Scene):
        self._control_panel.set_color(scene.red, scene.green, scene.blue)
        self._control_panel.set_brightness(scene.brightness)
        self._on_power_on_all()

    def _on_probe(self):
        for address, device in self._devices.items():
            if device.state == DeviceState.CONNECTED:
                self._worker.request_probe(address)
                return

    def _on_scene_save(self, name: str):
        r, g, b, brightness = self._get_control_state()
        self._scene_manager.upsert(Scene(name, r, g, b, brightness))
        self._scene_panel.refresh()
        self._status_bar.showMessage(f"Scene '{name}' saved.")

    # ── Window lifecycle ──────────────────────────────────────────────
    def closeEvent(self, event):
        self._worker.stop()
        event.accept()
