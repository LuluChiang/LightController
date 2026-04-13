from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QLabel, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from core.scene_manager import SceneManager, Scene

_USER_ROLE = Qt.ItemDataRole.UserRole


class ScenePanel(QWidget):
    scene_apply_requested = pyqtSignal(object)  # Scene
    scene_save_requested  = pyqtSignal(str)      # scene name

    def __init__(self, scene_manager: SceneManager, parent=None):
        super().__init__(parent)
        self._manager = scene_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(QLabel("<b>Scenes</b>"))

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)

        # ── Save row ──────────────────────────────────────────────────
        save_row = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Scene name…")
        self._save_btn = QPushButton("Save")
        self._save_btn.setFixedWidth(60)
        self._save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self._name_input)
        save_row.addWidget(self._save_btn)
        layout.addLayout(save_row)

        # ── Apply / Delete row ────────────────────────────────────────
        action_row = QHBoxLayout()
        self._apply_btn  = QPushButton("Apply")
        self._delete_btn = QPushButton("Delete")
        self._apply_btn.clicked.connect(self._on_apply)
        self._delete_btn.clicked.connect(self._on_delete)
        action_row.addWidget(self._apply_btn)
        action_row.addWidget(self._delete_btn)
        layout.addLayout(action_row)

        self.refresh()

    # ── Helpers ───────────────────────────────────────────────────────
    def refresh(self):
        self._list.clear()
        for scene in self._manager.get_all():
            item = QListWidgetItem(scene.name)
            item.setData(_USER_ROLE, scene)
            self._list.addItem(item)

    def _selected_scene(self) -> Scene | None:
        item = self._list.currentItem()
        return item.data(_USER_ROLE) if item else None

    # ── Slots ─────────────────────────────────────────────────────────
    def _on_double_click(self, item: QListWidgetItem):
        scene = item.data(_USER_ROLE)
        if scene:
            self.scene_apply_requested.emit(scene)

    def _on_apply(self):
        scene = self._selected_scene()
        if scene:
            self.scene_apply_requested.emit(scene)

    def _on_save(self):
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Scene", "Please enter a scene name.")
            return
        self.scene_save_requested.emit(name)
        self._name_input.clear()

    def _on_delete(self):
        scene = self._selected_scene()
        if not scene:
            return
        reply = QMessageBox.question(
            self, "Delete Scene",
            f"Delete scene '{scene.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete(scene.name)
            self.refresh()
