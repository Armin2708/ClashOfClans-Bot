"""Resource threshold configuration panel."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QSpinBox,
)

from bot.settings import Settings


class ResourcePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Attack Thresholds
        attack_group = QGroupBox("Attack Thresholds")
        attack_form = QFormLayout()
        attack_form.addRow(
            "Min Loot to Attack:",
            self._create_spinbox("min_loot_to_attack", 0, 20_000_000, 100_000, 1_000_000),
        )
        attack_group.setLayout(attack_form)
        layout.addWidget(attack_group)

        # Storage Thresholds
        storage_group = QGroupBox("Storage Thresholds")
        storage_form = QFormLayout()
        storage_form.addRow(
            "Gold Storage Full:",
            self._create_spinbox("gold_storage_full", 0, 50_000_000, 1_000_000, 24_000_000),
        )
        storage_form.addRow(
            "Elixir Storage Full:",
            self._create_spinbox("elixir_storage_full", 0, 50_000_000, 1_000_000, 24_000_000),
        )
        storage_group.setLayout(storage_form)
        layout.addWidget(storage_group)

        # Farm Targets
        farm_group = QGroupBox("Farm Targets")
        farm_form = QFormLayout()
        farm_form.addRow(
            "Farm Target Gold:",
            self._create_spinbox("farm_target_gold", 0, 50_000_000, 1_000_000, 31_000_000),
        )
        farm_form.addRow(
            "Farm Target Elixir:",
            self._create_spinbox("farm_target_elixir", 0, 50_000_000, 1_000_000, 31_000_000),
        )
        farm_group.setLayout(farm_form)
        layout.addWidget(farm_group)

        # Wall Upgrades
        wall_group = QGroupBox("Wall Upgrades")
        wall_form = QFormLayout()
        wall_form.addRow(
            "Max Wall Upgrades per Round:",
            self._create_spinbox("max_wall_upgrades", 1, 10, 1, 3),
        )
        wall_group.setLayout(wall_form)
        layout.addWidget(wall_group)

        layout.addStretch()

    def _create_spinbox(self, key, min_val, max_val, step, default):
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(step)
        spinbox.setValue(self._settings.get(key, default))
        spinbox.valueChanged.connect(lambda v: self._save(key, v))
        return spinbox

    def _save(self, key, value):
        self._settings.set(key, value)
        self._settings.save()
