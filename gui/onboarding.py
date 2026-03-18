"""First-launch onboarding — card carousel with slide animations."""

import subprocess
import re
import webbrowser

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import (
    Signal, Qt, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup,
)
from PySide6.QtGui import QFont

from bot.settings import Settings, BASE_WIDTH, BASE_HEIGHT


class _DotIndicator(QWidget):
    """Dot progress indicator for carousel steps."""

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self._count = count
        self._current = 0
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        self._dots = []
        for i in range(count):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            layout.addWidget(dot)
            self._dots.append(dot)
        self._update()

    def set_current(self, index):
        self._current = index
        self._update()

    def _update(self):
        for i, dot in enumerate(self._dots):
            if i == self._current:
                dot.setStyleSheet(
                    "background: #3b82f6; border-radius: 4px; border: none;"
                )
            else:
                dot.setStyleSheet(
                    "background: rgba(255,255,255,0.15); border-radius: 4px; border: none;"
                )


class _BaseCard(QWidget):
    """Base card for onboarding steps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QWidget { background: rgba(255,255,255,0.06); "
            "border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; }"
        )


class OnboardingWidget(QWidget):
    """Full-window onboarding carousel."""

    completed = Signal()

    BLUESTACKS_URL = "https://www.bluestacks.com/download"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()
        self._current = 0
        self._animating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card container (fixed size for animation)
        self._card_container = QWidget()
        self._card_container.setFixedSize(500, 420)
        self._card_container.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._card_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Create cards as children of card_container
        self._cards = [
            self._make_welcome_card(),
            self._make_bluestacks_card(),
            self._make_connect_card(),
            self._make_ready_card(),
        ]

        for card in self._cards:
            card.setParent(self._card_container)
            card.setGeometry(0, 0, 500, 420)
            card.hide()

        self._cards[0].show()

        # Dots
        self._dots = _DotIndicator(4)
        layout.addWidget(self._dots, alignment=Qt.AlignmentFlag.AlignCenter)

        # Navigation buttons
        nav = QHBoxLayout()
        self._back_btn = QPushButton("Back")
        self._back_btn.setFixedWidth(100)
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setVisible(False)

        self._next_btn = QPushButton("Get Started")
        self._next_btn.setProperty("class", "accent")
        self._next_btn.setFixedWidth(200)
        self._next_btn.setFixedHeight(40)
        self._next_btn.clicked.connect(self._go_next)

        nav.addWidget(self._back_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

    def _make_welcome_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\u2694\uFE0F")
        icon.setFont(QFont("", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        title = QLabel("Welcome to CoC Bot")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(
            "Automated farming for Clash of Clans.\n"
            "Let's get you set up in a few steps."
        )
        sub.setStyleSheet(
            "font-size: 14px; color: rgba(255,255,255,0.50); "
            "border: none; background: transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addStretch()

        return card

    def _make_bluestacks_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Install BlueStacks")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        body = QLabel(
            "CoC Bot works with BlueStacks emulator.\n"
            "Download and install it, then configure:\n\n"
            "1. Open BlueStacks Settings\n"
            "2. Go to Display tab\n"
            "3. Set resolution to 2560 x 1440\n"
            "4. Install Clash of Clans from Play Store"
        )
        body.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.55); line-height: 1.6; "
            "border: none; background: transparent;"
        )
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        dl_btn = QPushButton("Download BlueStacks")
        dl_btn.setProperty("class", "accent")
        dl_btn.setFixedHeight(36)
        dl_btn.clicked.connect(lambda: webbrowser.open(self.BLUESTACKS_URL))
        layout.addWidget(dl_btn)

        return card

    def _make_connect_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Connect to BlueStacks")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        body = QLabel(
            "Enter the ADB address for your BlueStacks instance.\n"
            "The default is usually localhost:5555."
        )
        body.setStyleSheet(
            "font-size: 13px; color: rgba(255,255,255,0.55); "
            "border: none; background: transparent;"
        )
        body.setWordWrap(True)
        layout.addWidget(body)

        self._addr_input = QLineEdit()
        self._addr_input.setPlaceholderText("localhost:5555")
        self._addr_input.setText("localhost:5555")
        layout.addWidget(self._addr_input)

        test_btn = QPushButton("Test Connection")
        test_btn.setProperty("class", "accent")
        test_btn.setFixedHeight(36)
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)

        self._connect_status = QLabel("")
        self._connect_status.setStyleSheet("border: none; background: transparent;")
        self._connect_status.setWordWrap(True)
        layout.addWidget(self._connect_status)

        layout.addStretch()
        return card

    def _make_ready_card(self):
        card = _BaseCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\u2705")
        icon.setFont(QFont("", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon)

        title = QLabel("You're All Set!")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: rgba(255,255,255,0.92); "
            "border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(
            "CoC Bot is ready to farm.\n"
            "Head to the Dashboard and hit Start!"
        )
        sub.setStyleSheet(
            "font-size: 14px; color: rgba(255,255,255,0.50); "
            "border: none; background: transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addStretch()

        return card

    def _test_connection(self):
        addr = self._addr_input.text().strip()
        adb = self._settings.get("adb_path", "adb")

        if not addr:
            self._connect_status.setText("Please enter an address.")
            self._connect_status.setStyleSheet(
                "color: #ef4444; font-weight: 500; border: none; background: transparent;"
            )
            return

        try:
            result = subprocess.run(
                [adb, "connect", addr],
                capture_output=True, text=True, timeout=10,
            )
            if "connected" not in result.stdout.lower():
                self._connect_status.setText(
                    "Could not connect. Make sure BlueStacks is running."
                )
                self._connect_status.setStyleSheet(
                    "color: #ef4444; font-weight: 500; border: none; background: transparent;"
                )
                return

            # Check resolution
            res = subprocess.run(
                [adb, "-s", addr, "shell", "wm", "size"],
                capture_output=True, text=True, timeout=10,
            )
            match = re.search(r"(\d+)x(\d+)", res.stdout)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                self._settings.set("device_address", addr)
                self._settings.set("screen_width", w)
                self._settings.set("screen_height", h)
                self._settings.save()

                if w == BASE_WIDTH and h == BASE_HEIGHT:
                    self._connect_status.setText(
                        f"Connected! Resolution: {w}x{h}"
                    )
                    self._connect_status.setStyleSheet(
                        "color: #22c55e; font-weight: 500; border: none; background: transparent;"
                    )
                    self._next_btn.setEnabled(True)
                else:
                    self._connect_status.setText(
                        f"Connected but resolution is {w}x{h}.\n"
                        f"Please set BlueStacks to {BASE_WIDTH}x{BASE_HEIGHT}."
                    )
                    self._connect_status.setStyleSheet(
                        "color: #eab308; font-weight: 500; border: none; background: transparent;"
                    )
                    self._next_btn.setEnabled(False)
            else:
                self._settings.set("device_address", addr)
                self._settings.save()
                self._connect_status.setText(
                    "Connected! (Could not verify resolution)"
                )
                self._connect_status.setStyleSheet(
                    "color: #eab308; font-weight: 500; border: none; background: transparent;"
                )

        except FileNotFoundError:
            self._connect_status.setText(f"ADB not found at '{adb}'")
            self._connect_status.setStyleSheet(
                "color: #ef4444; font-weight: 500; border: none; background: transparent;"
            )
        except subprocess.TimeoutExpired:
            self._connect_status.setText("Connection timed out.")
            self._connect_status.setStyleSheet(
                "color: #ef4444; font-weight: 500; border: none; background: transparent;"
            )

    def _go_next(self):
        if self._animating:
            return

        if self._current == 2:
            # On connect page, require successful connection
            status_text = self._connect_status.text()
            if not status_text.startswith("Connected!"):
                return

        if self._current >= 3:
            self.completed.emit()
            return

        self._animate_to(self._current + 1, direction=1)

    def _go_back(self):
        if self._animating or self._current <= 0:
            return
        self._animate_to(self._current - 1, direction=-1)

    def _animate_to(self, new_index, direction=1):
        self._animating = True
        w = self._card_container.width()

        old_card = self._cards[self._current]
        new_card = self._cards[new_index]

        # Position new card off-screen
        new_card.setGeometry(direction * w, 0, w, self._card_container.height())
        new_card.show()

        group = QParallelAnimationGroup(self)

        # Slide old card out
        anim_old = QPropertyAnimation(old_card, b"pos")
        anim_old.setDuration(300)
        anim_old.setStartValue(QPoint(0, 0))
        anim_old.setEndValue(QPoint(-direction * w, 0))
        anim_old.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_old)

        # Slide new card in
        anim_new = QPropertyAnimation(new_card, b"pos")
        anim_new.setDuration(300)
        anim_new.setStartValue(QPoint(direction * w, 0))
        anim_new.setEndValue(QPoint(0, 0))
        anim_new.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_new)

        def on_done():
            old_card.hide()
            self._current = new_index
            self._animating = False
            self._update_nav()

        group.finished.connect(on_done)
        group.start()

    def _update_nav(self):
        self._dots.set_current(self._current)
        self._back_btn.setVisible(self._current > 0)

        labels = ["Get Started", "I've Installed BlueStacks", "Continue", "Launch Bot"]
        self._next_btn.setText(labels[self._current])

        # Disable next on connect page until connection succeeds
        if self._current == 2:
            status_text = self._connect_status.text()
            self._next_btn.setEnabled(status_text.startswith("Connected!"))
        else:
            self._next_btn.setEnabled(True)
