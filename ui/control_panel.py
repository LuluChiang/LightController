from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QColorDialog, QFrame, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor


class ControlPanel(QWidget):
    power_on_all_requested  = pyqtSignal()
    power_off_all_requested = pyqtSignal()
    probe_requested         = pyqtSignal()
    # Consumers call get_color() / get_brightness() after these fire
    color_changed      = pyqtSignal()
    brightness_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(255, 255, 255)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)

        layout.addWidget(QLabel("<b>Controls</b>"))

        # ── Power buttons ─────────────────────────────────────────────
        power_row = QHBoxLayout()
        self._on_btn  = QPushButton("All On")
        self._off_btn = QPushButton("All Off")
        self._on_btn.setMinimumHeight(36)
        self._off_btn.setMinimumHeight(36)
        self._probe_btn = QPushButton("Probe Protocol")
        self._probe_btn.setMinimumHeight(36)
        self._on_btn.clicked.connect(self.power_on_all_requested)
        self._off_btn.clicked.connect(self.power_off_all_requested)
        self._probe_btn.clicked.connect(self.probe_requested)
        power_row.addWidget(self._on_btn)
        power_row.addWidget(self._off_btn)
        power_row.addWidget(self._probe_btn)
        layout.addLayout(power_row)

        # ── Colour picker ─────────────────────────────────────────────
        layout.addWidget(QLabel("Colour"))
        colour_row = QHBoxLayout()

        self._colour_swatch = QFrame()
        self._colour_swatch.setFixedSize(52, 52)
        self._colour_swatch.setFrameShape(QFrame.Shape.Box)

        self._pick_btn = QPushButton("Pick Colour…")
        self._pick_btn.setMinimumHeight(36)
        self._pick_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._pick_btn.clicked.connect(self._open_colour_picker)

        colour_row.addWidget(self._colour_swatch)
        colour_row.addWidget(self._pick_btn)
        layout.addLayout(colour_row)

        # ── Brightness slider ─────────────────────────────────────────
        layout.addWidget(QLabel("Brightness"))
        brightness_row = QHBoxLayout()

        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(0, 255)
        self._brightness_slider.setValue(255)

        self._brightness_label = QLabel("255")
        self._brightness_label.setFixedWidth(32)
        self._brightness_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._brightness_slider.valueChanged.connect(self._on_brightness_changed)

        brightness_row.addWidget(self._brightness_slider)
        brightness_row.addWidget(self._brightness_label)
        layout.addLayout(brightness_row)

        layout.addStretch()
        self._update_swatch()

    # ── Private helpers ───────────────────────────────────────────────
    def _open_colour_picker(self):
        colour = QColorDialog.getColor(self._color, self, "Pick Light Colour")
        if colour.isValid():
            self._color = colour
            self._update_swatch()
            self.color_changed.emit()

    def _update_swatch(self):
        self._colour_swatch.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid #666;"
        )

    def _on_brightness_changed(self, value: int):
        self._brightness_label.setText(str(value))
        self.brightness_changed.emit()

    # ── Public API ────────────────────────────────────────────────────
    def get_color(self) -> tuple[int, int, int]:
        return self._color.red(), self._color.green(), self._color.blue()

    def get_brightness(self) -> int:
        return self._brightness_slider.value()

    def set_color(self, r: int, g: int, b: int):
        self._color = QColor(r, g, b)
        self._update_swatch()

    def set_brightness(self, value: int):
        self._brightness_slider.setValue(value)
