from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal

from core.device import Device, DeviceState

# Indicator dot colour per connection state
_STATE_COLOUR = {
    DeviceState.DISCONNECTED: "#888888",
    DeviceState.CONNECTING:   "#FFA500",
    DeviceState.CONNECTED:    "#00C800",
    DeviceState.ERROR:        "#FF4444",
}


class DeviceRow(QWidget):
    connect_clicked    = pyqtSignal(str)   # address
    disconnect_clicked = pyqtSignal(str)   # address

    def __init__(self, device: Device, parent=None):
        super().__init__(parent)
        self.address = device.address

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self._indicator = QLabel("●")
        self._indicator.setFixedWidth(18)

        self._name_label = QLabel(f"<b>{device.name}</b><br><small>{device.address}</small>")
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._connect_btn    = QPushButton("Connect")
        self._disconnect_btn = QPushButton("Disconnect")
        self._connect_btn.setFixedWidth(90)
        self._disconnect_btn.setFixedWidth(90)

        self._connect_btn.clicked.connect(lambda: self.connect_clicked.emit(self.address))
        self._disconnect_btn.clicked.connect(lambda: self.disconnect_clicked.emit(self.address))

        layout.addWidget(self._indicator)
        layout.addWidget(self._name_label)
        layout.addWidget(self._connect_btn)
        layout.addWidget(self._disconnect_btn)

        self.set_state(device.state)

    def set_state(self, state: DeviceState):
        colour = _STATE_COLOUR[state]
        self._indicator.setStyleSheet(f"color: {colour}; font-size: 20px;")
        connected   = state == DeviceState.CONNECTED
        connecting  = state == DeviceState.CONNECTING
        self._connect_btn.setEnabled(not connected and not connecting)
        self._disconnect_btn.setEnabled(connected)


class DevicePanel(QWidget):
    scan_requested       = pyqtSignal()
    connect_requested    = pyqtSignal(str)   # address
    disconnect_requested = pyqtSignal(str)   # address

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: dict[str, DeviceRow] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("<b>Devices</b>")
        layout.addWidget(title)

        self._scan_btn = QPushButton("Scan for Devices")
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self._scan_btn)

        # Scrollable device list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

    def _on_scan_clicked(self):
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning...")
        self.scan_requested.emit()

    def scan_finished(self):
        """Re-enables the scan button after a scan completes."""
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan for Devices")

    def populate_devices(self, devices: list):
        # Remove existing rows
        for row in self._rows.values():
            row.deleteLater()
        self._rows.clear()

        for device in devices:
            row = DeviceRow(device)
            row.connect_clicked.connect(self.connect_requested)
            row.disconnect_clicked.connect(self.disconnect_requested)
            # Insert before the trailing stretch
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)
            self._rows[device.address] = row

        self.scan_finished()

    def set_device_state(self, address: str, state: DeviceState):
        row = self._rows.get(address)
        if row:
            row.set_state(state)
