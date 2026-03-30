"""Label & Train panel — active-learning annotation and training UI.

Provides an interactive canvas for correcting YOLO predictions on
base screenshots, saving YOLO-format labels, and launching training.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QSpinBox, QCheckBox, QFormLayout,
    QDialogButtonBox, QProgressBar, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QRectF

from gui.widgets.annotation_canvas import AnnotationCanvas, BBoxItem, Mode
from gui.widgets.class_selector import ClassSelector
from training.generate.class_registry import ALL_CLASSES, CLASS_INDEX
from training.dataset_manager import DatasetManager

logger = logging.getLogger("coc.labeling")


class LabelingPanel(QWidget):
    """Main labeling and training panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_paths: list[Path] = []
        self._current_idx = -1
        self._unsaved = False
        self._dataset_mgr = DatasetManager()
        self._train_worker = None

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self._btn_load = QPushButton("Load Images")
        self._btn_load.setProperty("class", "accent")
        self._btn_load.clicked.connect(self._load_images)
        toolbar.addWidget(self._btn_load)

        self._btn_prev = QPushButton("<")
        self._btn_prev.setFixedWidth(32)
        self._btn_prev.clicked.connect(self._prev_image)
        toolbar.addWidget(self._btn_prev)

        self._btn_next = QPushButton(">")
        self._btn_next.setFixedWidth(32)
        self._btn_next.clicked.connect(self._next_image)
        toolbar.addWidget(self._btn_next)

        self._lbl_counter = QLabel("0 / 0")
        self._lbl_counter.setStyleSheet("color: rgba(255,255,255,0.6); padding: 0 8px;")
        toolbar.addWidget(self._lbl_counter)

        toolbar.addStretch()

        self._btn_detect = QPushButton("Auto-Detect")
        self._btn_detect.setProperty("class", "accent")
        self._btn_detect.clicked.connect(self._auto_detect)
        toolbar.addWidget(self._btn_detect)

        self._btn_draw = QPushButton("Draw Mode")
        self._btn_draw.setCheckable(True)
        self._btn_draw.toggled.connect(self._toggle_draw_mode)
        toolbar.addWidget(self._btn_draw)

        self._btn_save = QPushButton("Save")
        self._btn_save.setProperty("class", "success")
        self._btn_save.clicked.connect(self._save_current)
        toolbar.addWidget(self._btn_save)

        self._btn_collect = QPushButton("Collect Bases")
        self._btn_collect.clicked.connect(self._show_collect_dialog)
        toolbar.addWidget(self._btn_collect)

        self._btn_train = QPushButton("Train")
        self._btn_train.setProperty("class", "warning")
        self._btn_train.clicked.connect(self._show_train_dialog)
        toolbar.addWidget(self._btn_train)

        layout.addLayout(toolbar)

        # Main area: canvas + sidebar
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Canvas
        self._canvas = AnnotationCanvas()
        self._canvas.box_selected.connect(self._on_box_selected)
        self._canvas.box_created.connect(self._on_box_created)
        self._canvas.boxes_changed.connect(self._on_boxes_changed)
        splitter.addWidget(self._canvas)

        # Sidebar
        sidebar = QWidget()
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(4)

        self._class_selector = ClassSelector()
        self._class_selector.class_changed.connect(self._on_class_changed)
        side_layout.addWidget(self._class_selector, stretch=2)

        # Box list table
        side_layout.addWidget(QLabel("Boxes:"))
        self._box_table = QTableWidget(0, 3)
        self._box_table.setHorizontalHeaderLabels(["Class", "Conf", "Del"])
        self._box_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._box_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self._box_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self._box_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._box_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._box_table.cellClicked.connect(self._on_table_click)
        side_layout.addWidget(self._box_table, stretch=1)

        # Training progress (hidden by default)
        self._progress_widget = QWidget()
        prog_layout = QVBoxLayout(self._progress_widget)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        self._lbl_train_status = QLabel("Training...")
        self._lbl_train_status.setStyleSheet("color: rgba(255,255,255,0.8);")
        prog_layout.addWidget(self._lbl_train_status)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        prog_layout.addWidget(self._progress_bar)
        self._btn_stop_train = QPushButton("Stop Training")
        self._btn_stop_train.setProperty("class", "danger")
        self._btn_stop_train.clicked.connect(self._stop_training)
        prog_layout.addWidget(self._btn_stop_train)
        self._progress_widget.setVisible(False)
        side_layout.addWidget(self._progress_widget)

        splitter.addWidget(sidebar)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, stretch=1)

        # Status bar
        self._lbl_status = QLabel("Load images to begin labeling")
        self._lbl_status.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 11px; padding: 2px;")
        layout.addWidget(self._lbl_status)

    # ── Image loading ────────────────────────────────────────────

    def _load_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.jpg *.jpeg *.png);;All Files (*)")
        if not paths:
            return
        self._image_paths = [Path(p) for p in sorted(paths)]
        self._current_idx = 0
        self._show_current_image()

    def _prev_image(self):
        if self._current_idx > 0:
            self._maybe_save_prompt()
            self._current_idx -= 1
            self._show_current_image()

    def _next_image(self):
        if self._current_idx < len(self._image_paths) - 1:
            self._maybe_save_prompt()
            self._current_idx += 1
            self._show_current_image()

    def _show_current_image(self):
        if not self._image_paths or self._current_idx < 0:
            return
        path = self._image_paths[self._current_idx]
        bgr = cv2.imread(str(path))
        if bgr is None:
            self._lbl_status.setText(f"Failed to load: {path.name}")
            return

        self._canvas.load_image(bgr)
        self._lbl_counter.setText(
            f"{self._current_idx + 1} / {len(self._image_paths)}")
        self._lbl_status.setText(f"{path.name}  |  {bgr.shape[1]}x{bgr.shape[0]}")
        self._unsaved = False

        # Load existing labels if any
        existing = self._dataset_mgr.load_annotation(path.name)
        if existing:
            h, w = bgr.shape[:2]
            for box in existing:
                cx, cy, nw, nh = box["cx"], box["cy"], box["nw"], box["nh"]
                x1 = int((cx - nw / 2) * w)
                y1 = int((cy - nh / 2) * h)
                x2 = int((cx + nw / 2) * w)
                y2 = int((cy + nh / 2) * h)
                self._canvas.add_box(x1, y1, x2, y2, box["class_name"],
                                     is_prediction=False)
        self._refresh_table()

    # ── Auto-detect ──────────────────────────────────────────────

    def _auto_detect(self):
        bgr = self._canvas.image_bgr
        if bgr is None:
            self._lbl_status.setText("No image loaded")
            return

        try:
            from bot.detector import Detector
            model_path = "data/models/coc.pt"
            if not Path(model_path).exists():
                self._lbl_status.setText("No model found at data/models/coc.pt")
                return
            det = Detector(model_path, confidence=0.3)
            detections = det.predict(bgr)

            self._canvas.clear_boxes()
            for d in detections:
                self._canvas.add_box(d.x1, d.y1, d.x2, d.y2,
                                     d.cls, d.conf, is_prediction=True)
            self._lbl_status.setText(f"Detected {len(detections)} objects")
            self._refresh_table()
            self._unsaved = True
        except Exception as e:
            self._lbl_status.setText(f"Detection error: {e}")
            logger.exception("Auto-detect failed")

    # ── Draw mode ────────────────────────────────────────────────

    def _toggle_draw_mode(self, checked: bool):
        self._canvas.mode = Mode.DRAW if checked else Mode.SELECT

    # ── Box events ───────────────────────────────────────────────

    def _on_box_selected(self, box: BBoxItem | None):
        if box:
            self._class_selector.set_class(box.class_name)
            # Highlight table row
            boxes = self._canvas.get_boxes()
            # Reverse to match table order (added order)
            for i, b in enumerate(reversed(boxes)):
                if b is box:
                    self._box_table.selectRow(i)
                    break

    def _on_box_created(self, box: BBoxItem):
        """New box drawn — set its class to the last used one."""
        last = self._class_selector.last_class
        box.set_class(last)
        self._canvas._last_class = last
        self._refresh_table()
        self._unsaved = True

    def _on_class_changed(self, class_name: str):
        box = self._canvas.selected_box()
        if box:
            box.set_class(class_name)
            self._canvas._last_class = class_name
            self._refresh_table()
            self._unsaved = True

    def _on_boxes_changed(self):
        self._refresh_table()
        self._unsaved = True

    # ── Box table ────────────────────────────────────────────────

    def _refresh_table(self):
        boxes = list(reversed(self._canvas.get_boxes()))
        self._box_table.setRowCount(len(boxes))
        for i, box in enumerate(boxes):
            self._box_table.setItem(i, 0, QTableWidgetItem(box.class_name))
            conf_str = f"{box.confidence:.0%}" if box.confidence > 0 else "manual"
            self._box_table.setItem(i, 1, QTableWidgetItem(conf_str))
            del_btn = QPushButton("X")
            del_btn.setFixedSize(24, 24)
            del_btn.setStyleSheet(
                "color: #ef4444; background: transparent; border: none; font-weight: bold;")
            del_btn.clicked.connect(lambda checked, b=box: self._delete_box(b))
            self._box_table.setCellWidget(i, 2, del_btn)

    def _on_table_click(self, row: int, col: int):
        boxes = list(reversed(self._canvas.get_boxes()))
        if 0 <= row < len(boxes):
            self._canvas._scene.clearSelection()
            boxes[row].setSelected(True)

    def _delete_box(self, box: BBoxItem):
        self._canvas._scene.removeItem(box)
        self._canvas.boxes_changed.emit()

    # ── Save ─────────────────────────────────────────────────────

    def _save_current(self):
        bgr = self._canvas.image_bgr
        if bgr is None:
            return

        h, w = bgr.shape[:2]
        boxes = self._canvas.get_boxes()
        box_dicts = []
        for box in boxes:
            rect = box.rect()
            # Account for item position offset
            pos = box.pos()
            x1 = rect.x() + pos.x()
            y1 = rect.y() + pos.y()
            bw = rect.width()
            bh = rect.height()
            box_dicts.append({
                "class_name": box.class_name,
                "cx": (x1 + bw / 2) / w,
                "cy": (y1 + bh / 2) / h,
                "nw": bw / w,
                "nh": bh / h,
            })

        path = self._image_paths[self._current_idx]
        self._dataset_mgr.save_annotation(path.name, bgr, box_dicts)
        self._unsaved = False

        stats = self._dataset_mgr.get_stats()
        total_imgs = stats["train"]["images"] + stats["val"]["images"]
        total_boxes = stats["train"]["boxes"] + stats["val"]["boxes"]
        self._lbl_status.setText(
            f"Saved {len(box_dicts)} boxes  |  "
            f"Dataset: {total_imgs} images, {total_boxes} boxes total")

    def _maybe_save_prompt(self):
        if self._unsaved:
            self._save_current()

    # ── Training ─────────────────────────────────────────────────

    def _show_train_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Training Parameters")
        dialog.setMinimumWidth(300)

        form = QFormLayout(dialog)

        epochs_spin = QSpinBox()
        epochs_spin.setRange(10, 500)
        epochs_spin.setValue(50)
        form.addRow("Epochs:", epochs_spin)

        batch_spin = QSpinBox()
        batch_spin.setRange(1, 64)
        batch_spin.setValue(16)
        form.addRow("Batch Size:", batch_spin)

        resume_check = QCheckBox("Resume from last checkpoint")
        form.addRow(resume_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Prepare dataset
        self._dataset_mgr.split_val(ratio=0.15)
        yaml_path = self._dataset_mgr.generate_yaml()

        self._start_training(
            str(yaml_path),
            epochs_spin.value(),
            batch_spin.value(),
            resume_check.isChecked(),
        )

    def _start_training(self, data_yaml: str, epochs: int, batch: int,
                        resume: bool):
        from gui.workers.train_worker import TrainWorker

        self._train_worker = TrainWorker(data_yaml, epochs, batch, resume)
        self._train_worker.progress_updated.connect(self._on_train_progress)
        self._train_worker.training_finished.connect(self._on_train_finished)
        self._train_worker.error_occurred.connect(self._on_train_error)
        self._train_worker.start()

        self._progress_widget.setVisible(True)
        self._btn_train.setEnabled(False)
        self._lbl_train_status.setText("Training starting...")
        self._progress_bar.setValue(0)

    def _stop_training(self):
        if self._train_worker:
            self._train_worker.stop()
            self._lbl_train_status.setText("Stopping...")

    def _on_train_progress(self, epoch: int, total: int, loss: float, mAP: float):
        pct = int(epoch / total * 100) if total > 0 else 0
        self._progress_bar.setValue(pct)
        self._lbl_train_status.setText(
            f"Epoch {epoch}/{total}  |  loss={loss:.3f}  |  mAP50={mAP:.3f}")

    def _on_train_finished(self, model_path: str):
        self._progress_widget.setVisible(False)
        self._btn_train.setEnabled(True)
        self._train_worker = None

        if model_path:
            # Reload detector so next Auto-Detect uses the new model
            try:
                from bot.vision import reload_detector
                reload_detector()
            except Exception:
                pass
            self._lbl_status.setText(f"Training complete! Model saved to {model_path}")
        else:
            self._lbl_status.setText("Training stopped by user")

    def _on_train_error(self, msg: str):
        self._progress_widget.setVisible(False)
        self._btn_train.setEnabled(True)
        self._train_worker = None
        self._lbl_status.setText(f"Training error: {msg}")
        logger.error("Training failed: %s", msg)

    # ── Base Collection ──────────────────────────────────────────

    def _show_collect_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Collect Base Screenshots")
        dialog.setMinimumWidth(300)

        form = QFormLayout(dialog)

        count_spin = QSpinBox()
        count_spin.setRange(10, 5000)
        count_spin.setValue(500)
        form.addRow("Number of bases:", count_spin)

        auto_label_check = QCheckBox("Auto-label with synthetic model")
        auto_label_check.setChecked(True)
        form.addRow(auto_label_check)

        info = QLabel("Make sure:\n- Emulator is running with CoC open\n"
                       "- ADB is connected\n- Game is on village screen")
        info.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        form.addRow(info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._start_collection(count_spin.value(), auto_label_check.isChecked())

    def _start_collection(self, count: int, auto_label: bool):
        from PySide6.QtCore import QThread, Signal
        import threading

        class CollectWorker(QThread):
            progress = Signal(int, int)   # collected, total
            finished = Signal(str)
            error = Signal(str)

            def __init__(self, count, auto_label):
                super().__init__()
                self._count = count
                self._auto_label = auto_label
                self._stop = threading.Event()

            def stop(self):
                self._stop.set()

            def run(self):
                try:
                    from training.collect.collect_bases import (
                        _screencap, _tap, _find_template, _detect_state,
                        _tap_button, _wait_for_state,
                    )
                    from pathlib import Path
                    import cv2

                    out = Path("datasets/bases")
                    (out / "images").mkdir(parents=True, exist_ok=True)
                    if self._auto_label:
                        (out / "labels").mkdir(parents=True, exist_ok=True)

                    # Check state
                    img = _screencap()
                    if img is None:
                        self.error.emit("ADB screencap failed")
                        return
                    state = _detect_state(img)
                    if state != "village":
                        self.error.emit(f"Not on village screen (state={state})")
                        return

                    # Enter search
                    _tap_button("attack_button", delay=2)
                    _tap_button("find_match", delay=2)
                    _tap_button("start_battle", delay=3)

                    if not _wait_for_state("scouting", timeout=30):
                        self.error.emit("Timed out waiting for first base")
                        return

                    # Auto-label detector
                    detector = None
                    if self._auto_label:
                        try:
                            from bot.detector import Detector
                            label_model = Path("data/models/coc_synthetic.pt")
                            if not label_model.exists():
                                label_model = Path("data/models/coc.pt")
                            detector = Detector(str(label_model), confidence=0.15)
                        except Exception:
                            pass

                    collected = 0
                    while collected < self._count and not self._stop.is_set():
                        img = _screencap()
                        if img is None:
                            import time; time.sleep(1)
                            continue
                        if _detect_state(img) != "scouting":
                            import time; time.sleep(1)
                            continue

                        timestamp = int(time.time() * 1000)
                        cv2.imwrite(
                            str(out / "images" / f"base_{timestamp}.jpg"),
                            img, [cv2.IMWRITE_JPEG_QUALITY, 95])

                        if detector:
                            dets = detector.predict(img)
                            h, w = img.shape[:2]
                            lines = []
                            for d in dets:
                                cx = (d.x1 + d.x2) / 2 / w
                                cy = (d.y1 + d.y2) / 2 / h
                                nw = (d.x2 - d.x1) / w
                                nh = (d.y2 - d.y1) / h
                                cls_id = list(detector._model.names.keys())[
                                    list(detector._model.names.values()).index(d.cls)
                                ] if d.cls in detector._model.names.values() else 0
                                lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                            (out / "labels" / f"base_{timestamp}.txt").write_text("\n".join(lines))

                        collected += 1
                        self.progress.emit(collected, self._count)

                        pos = _find_template(img, "next_base")
                        if pos:
                            _tap(*pos, delay=0.5)
                        import time; time.sleep(3)

                    # Go home
                    _tap_button("end_battle", delay=3)
                    import time; time.sleep(3)
                    _tap_button("return_home", delay=3)

                    self.finished.emit(f"Collected {collected} bases")
                except Exception as e:
                    self.error.emit(str(e))

        self._collect_worker = CollectWorker(count, auto_label)
        self._collect_worker.progress.connect(
            lambda c, t: self._lbl_status.setText(f"Collecting bases: {c}/{t}"))
        self._collect_worker.finished.connect(self._on_collect_done)
        self._collect_worker.error.connect(
            lambda msg: self._lbl_status.setText(f"Collection error: {msg}"))
        self._collect_worker.start()

        self._btn_collect.setEnabled(False)
        self._lbl_status.setText("Starting base collection...")

    def _on_collect_done(self, msg: str):
        self._btn_collect.setEnabled(True)
        self._collect_worker = None
        self._lbl_status.setText(msg)
        # Load collected images for review
        from pathlib import Path
        bases_dir = Path("datasets/bases/images")
        if bases_dir.exists():
            self._image_paths = sorted(bases_dir.glob("*.jpg"))
            if self._image_paths:
                self._current_idx = 0
                self._show_current_image()
                self._lbl_status.setText(
                    f"{msg} — loaded {len(self._image_paths)} images for review")
