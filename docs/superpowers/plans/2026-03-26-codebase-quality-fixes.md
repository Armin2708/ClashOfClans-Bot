# Codebase Quality Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 high-confidence bugs found in the code review: thread-safety issues, GUI blocking, double metric logging, and stale ADB path.

**Architecture:** Minimal, targeted fixes — no refactors. Each fix is isolated to one file. No new abstractions introduced.

**Tech Stack:** Python 3.13, PySide6, threading, urllib

---

## Already Fixed (context)
- **Stop bug** — `main_window.py` worker orphan on 5s timeout fixed; `bot_stopped` signal now cleans up worker
- **Update notification false positive** — `.spec` now bakes version into `bot/_version.py` at build time

---

## Files to Modify

| File | Issue |
|------|-------|
| `bot/settings.py:153` | `__new__` checks `_instance is None` without holding `_lock` — race condition |
| `bot/main.py:199,296` | `metrics.log_final()` called before `return` AND again in `finally` block |
| `bot/screen.py:10,18,35` | `ADB_PATH` bound at import time — stale if setting changed at runtime |
| `bot/vision.py:42,99,190` | `_TEMPLATES`/`_TEMPLATES_GRAY` mutated from worker + GUI threads without a lock |
| `bot/updater.py:88` | `QMessageBox(self._parent)` called after parent window may be destroyed |
| `gui/panels/settings_panel.py:241` | `urllib.request.urlopen(..., timeout=10)` blocks GUI thread up to 10s |

---

## Task 1: Thread-safe Settings singleton

**Files:**
- Modify: `bot/settings.py:153-157`

**Problem:** Two threads calling `Settings()` simultaneously can both pass `_instance is None` before either sets it, constructing two instances. `_lock` exists but is never acquired in `__new__`.

- [ ] **Step 1: Apply double-checked locking in `__new__`**

Replace `__new__` in `bot/settings.py`:

```python
def __new__(cls):
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
    return cls._instance
```

- [ ] **Step 2: Verify singleton is thread-safe**

```bash
cd /Users/arminrad/Desktop/ClashOfClans-Bot
python3 -c "
import threading
from bot.settings import Settings
instances = []
def get(): instances.append(id(Settings()))
threads = [threading.Thread(target=get) for _ in range(20)]
[t.start() for t in threads]
[t.join() for t in threads]
assert len(set(instances)) == 1, f'Got {len(set(instances))} instances!'
print('PASS: singleton is thread-safe')
"
```

Expected: `PASS: singleton is thread-safe`

- [ ] **Step 3: Commit**

```bash
git add bot/settings.py
git commit -m "fix: thread-safe Settings singleton using double-checked locking"
```

---

## Task 2: Fix double metrics.log_final() call

**Files:**
- Modify: `bot/main.py:199,296`

**Problem:** Circuit breaker early-return calls `metrics.log_final()` before `return`, then the `finally` block calls it again — two "Final Metrics" log lines and two Discord summary notifications sent per circuit breaker trip.

- [ ] **Step 1: Remove redundant call from `main()` circuit breaker**

In `bot/main.py` inside `main()`, find:
```python
            if circuit_breaker.is_tripped():
                logger.error("Circuit breaker tripped: %d restarts failed in %d seconds",
                             CIRCUIT_BREAKER_MAX_FAILURES, CIRCUIT_BREAKER_WINDOW)
                notify(f"Bot stopped: circuit breaker tripped ({CIRCUIT_BREAKER_MAX_FAILURES} "
                       f"failures in {CIRCUIT_BREAKER_WINDOW}s)")
                metrics.log_final()
                return
```

Remove the `metrics.log_final()` line. The `finally` block handles it.

- [ ] **Step 2: Remove redundant call from `farm_to_max()` circuit breaker**

In `bot/main.py` inside `farm_to_max()`, find:
```python
            if circuit_breaker.is_tripped():
                logger.error("Circuit breaker tripped")
                notify("Farm mode stopped: circuit breaker tripped")
                metrics.log_final()
                return
```

Remove the `metrics.log_final()` line.

- [ ] **Step 3: Verify exactly 2 calls remain (both in finally blocks)**

```bash
grep -n "metrics.log_final" bot/main.py
```

Expected — exactly two lines, both in `finally` blocks:
```
260:        metrics.log_final()
358:        metrics.log_final()
```
(line numbers may shift by 1 after edits — confirm both are inside `finally:`)

- [ ] **Step 4: Commit**

```bash
git add bot/main.py
git commit -m "fix: remove duplicate metrics.log_final() before circuit breaker return"
```

---

## Task 3: Fix stale ADB path in screen.py

**Files:**
- Modify: `bot/screen.py:10,18,35`

**Problem:** `ADB_PATH` is bound once at module import time. If the user changes `adb_path` in Settings after startup, the running bot uses the old value. `device_address` is read dynamically on every call — inconsistent.

- [ ] **Step 1: Remove `ADB_PATH` from the import**

In `bot/screen.py` line 10, change:
```python
from bot.config import ADB_PATH, GAME_PACKAGE, SCREEN_WIDTH, SCREEN_HEIGHT
```
to:
```python
from bot.config import GAME_PACKAGE, SCREEN_WIDTH, SCREEN_HEIGHT
```

- [ ] **Step 2: Read `adb_path` dynamically in `_adb_cmd`**

Replace `_adb_cmd`:
```python
def _adb_cmd(*args):
    """Build an ADB command list, inserting -s <device> when configured."""
    adb = Settings().get("adb_path", "adb")
    device = Settings().get("device_address", "")
    cmd = [adb]
    if device:
        cmd += ["-s", device]
    cmd += list(args)
    return cmd
```

- [ ] **Step 3: Fix direct `ADB_PATH` use in `check_adb_connection`**

In `check_adb_connection()`, find:
```python
            result = subprocess.run(
                [ADB_PATH, "connect", device],
                capture_output=True, text=True, timeout=10
            )
```
Change to:
```python
            result = subprocess.run(
                [Settings().get("adb_path", "adb"), "connect", device],
                capture_output=True, text=True, timeout=10
            )
```

- [ ] **Step 4: Confirm no remaining ADB_PATH references**

```bash
grep -n "ADB_PATH" bot/screen.py
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add bot/screen.py
git commit -m "fix: read adb_path dynamically from Settings instead of stale import"
```

---

## Task 4: Thread-safe template cache in vision.py

**Files:**
- Modify: `bot/vision.py`

**Problem:** `_TEMPLATES` and `_TEMPLATES_GRAY` are module-level globals. `_load_templates()` is called from the worker thread at startup; `auto_capture_template()` calls `_reload_template()` mid-battle. No lock protects these — a partial dict state can be observed by the other thread.

- [ ] **Step 1: Add `_templates_lock` after existing globals**

In `bot/vision.py`, after `import logging` add `import threading` (check first: `grep "^import threading" bot/vision.py`).

After the line `_auto_captured = set()` (~line 134), add:
```python
_templates_lock = threading.Lock()
```

- [ ] **Step 2: Make `_load_templates` lock-aware (must be called under lock)**

Add a docstring note to `_load_templates`:
```python
def _load_templates():
    """Load all button templates into module-level caches.
    Must be called with _templates_lock held by the caller."""
    global _TEMPLATES, _TEMPLATES_GRAY
    # ... rest of body unchanged ...
```

- [ ] **Step 3: Update `get_template` to acquire the lock**

Replace:
```python
def get_template(name):
    global _TEMPLATES
    if _TEMPLATES is None:
        _load_templates()
    return _TEMPLATES.get(name)
```
With:
```python
def get_template(name):
    with _templates_lock:
        if _TEMPLATES is None:
            _load_templates()
        return _TEMPLATES.get(name)
```

- [ ] **Step 4: Update `_get_template_gray` to acquire the lock**

Replace:
```python
def _get_template_gray(name):
    """Get a pre-converted grayscale template for fast matching."""
    global _TEMPLATES_GRAY
    if _TEMPLATES_GRAY is None:
        _load_templates()
    return _TEMPLATES_GRAY.get(name)
```
With:
```python
def _get_template_gray(name):
    """Get a pre-converted grayscale template for fast matching."""
    with _templates_lock:
        if _TEMPLATES_GRAY is None:
            _load_templates()
        return _TEMPLATES_GRAY.get(name)
```

- [ ] **Step 5: Update `_reload_template` to acquire the lock**

Replace the entire `_reload_template` function:
```python
def _reload_template(name):
    """Reload a single template from disk into the in-memory caches."""
    global _TEMPLATES, _TEMPLATES_GRAY
    paths = {
        "next_base": "templates/buttons/next_base.png",
    }
    path = paths.get(name)
    if not path:
        return

    from bot.settings import BASE_WIDTH, BASE_HEIGHT
    rx = SCREEN_WIDTH / BASE_WIDTH
    ry = SCREEN_HEIGHT / BASE_HEIGHT

    bgr = load_template(path)
    if bgr is not None and (rx != 1.0 or ry != 1.0):
        h, w = bgr.shape[:2]
        new_w, new_h = max(1, int(w * rx)), max(1, int(h * ry))
        bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    with _templates_lock:
        if _TEMPLATES is None:
            _load_templates()
        _TEMPLATES[name] = bgr
        _TEMPLATES_GRAY[name] = (
            cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr is not None else None
        )
```

- [ ] **Step 6: Verify import**

```bash
python3 -c "from bot.vision import get_template, validate_critical_templates; print('PASS: vision imports ok')"
```

Expected: `PASS: vision imports ok`

- [ ] **Step 7: Commit**

```bash
git add bot/vision.py
git commit -m "fix: protect template cache globals with threading.Lock"
```

---

## Task 5: Guard UpdateChecker against destroyed parent window

**Files:**
- Modify: `bot/updater.py:88-104`

**Problem:** If the window closes while the update HTTP request is in flight, `_on_result` fires after `QMainWindow` is destroyed. `QMessageBox(self._parent)` raises `RuntimeError: Internal C++ object already deleted`.

- [ ] **Step 1: Extract `_cleanup` helper**

Add after `_on_result`:
```python
def _cleanup(self):
    """Stop and release the background worker thread."""
    if self._worker:
        self._worker.quit()
        self._worker.wait()
        self._worker = None
```

- [ ] **Step 2: Add destruction guard and use `_cleanup` throughout `_on_result`**

Replace the entire `_on_result` method:
```python
def _on_result(self, data):
    if not data:
        return

    tag = data.get("tag_name", "")
    release_notes = data.get("body", "")
    html_url = data.get("html_url", "")

    if not tag:
        return

    remote_version = tag.lstrip("v")

    try:
        if Version(remote_version) <= Version(APP_VERSION):
            logger.debug("App is up to date (v%s)", APP_VERSION)
            self._cleanup()
            return
    except Exception:
        self._cleanup()
        return

    download_url = html_url
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".dmg"):
            download_url = asset["browser_download_url"]
            break

    logger.info("Update available: v%s -> v%s", APP_VERSION, remote_version)

    try:
        msg = QMessageBox(self._parent)
    except RuntimeError:
        logger.debug("Update check: parent window destroyed, skipping dialog")
        self._cleanup()
        return

    msg.setWindowTitle("Update Available")
    msg.setText(f"A new version is available: v{remote_version}")
    msg.setInformativeText(
        f"{release_notes}\n\n"
        f"You are running v{APP_VERSION}.\n"
        "Would you like to download the update?"
    )
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)

    if msg.exec() == QMessageBox.Yes:
        webbrowser.open(download_url)

    self._cleanup()
```

- [ ] **Step 3: Verify**

```bash
python3 -c "from bot.updater import UpdateChecker; print('PASS: updater imports ok')"
```

Expected: `PASS: updater imports ok`

- [ ] **Step 4: Commit**

```bash
git add bot/updater.py
git commit -m "fix: guard UpdateChecker against destroyed parent window on close"
```

---

## Task 6: Move Discord webhook test off the GUI thread

**Files:**
- Modify: `gui/panels/settings_panel.py`

**Problem:** `_on_test_webhook` calls `urllib.request.urlopen(..., timeout=10)` on the Qt main thread. If Discord is slow or rate-limiting, the entire application window freezes for up to 10 seconds.

- [ ] **Step 1: Add `QThread` and `Signal` to imports**

In `gui/panels/settings_panel.py`, change:
```python
from PySide6.QtCore import Qt
```
to:
```python
from PySide6.QtCore import Qt, QThread, Signal
```

- [ ] **Step 2: Add `_WebhookTestWorker` class before `SettingsPanel`**

Insert before `class SettingsPanel(QWidget):`:
```python
class _WebhookTestWorker(QThread):
    """Background thread for testing the Discord webhook — keeps GUI responsive."""
    result_ready = Signal(bool, str)  # (success, message)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            payload = json.dumps({"content": "CoC Bot: test message"}).encode()
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "COC-Bot/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    self.result_ready.emit(True, "Working!")
                else:
                    self.result_ready.emit(False, f"HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            self.result_ready.emit(False, f"HTTP {e.code}")
        except Exception as e:
            self.result_ready.emit(False, f"Error: {e}")
```

- [ ] **Step 3: Add `_webhook_worker` to `SettingsPanel.__init__`**

In `SettingsPanel.__init__`, after `self._settings = Settings()` add:
```python
self._webhook_worker = None
```

- [ ] **Step 4: Replace `_on_test_webhook` with async version and add result handler**

Replace the existing `_on_test_webhook` method:
```python
def _on_test_webhook(self):
    url = self._webhook_url.text().strip()
    if not url:
        self._discord_status.setText("No URL")
        self._discord_status.setStyleSheet("color: #ef4444; font-weight: 500;")
        return

    self._test_btn.setEnabled(False)
    self._discord_status.setText("Testing...")
    self._discord_status.setStyleSheet("color: rgba(255,255,255,0.5); font-weight: 500;")

    self._webhook_worker = _WebhookTestWorker(url, parent=self)
    self._webhook_worker.result_ready.connect(self._on_webhook_result)
    self._webhook_worker.start()

def _on_webhook_result(self, success, message):
    self._test_btn.setEnabled(True)
    color = "#22c55e" if success else "#ef4444"
    self._discord_status.setText(message)
    self._discord_status.setStyleSheet(f"color: {color}; font-weight: 500;")
    self._webhook_worker = None
```

- [ ] **Step 5: Verify**

```bash
python3 -c "from gui.panels.settings_panel import SettingsPanel; print('PASS: settings_panel imports ok')"
```

Expected: `PASS: settings_panel imports ok`

- [ ] **Step 6: Commit**

```bash
git add gui/panels/settings_panel.py
git commit -m "fix: run Discord webhook test in background thread, not GUI thread"
```

---

## Self-Review

**Spec coverage:** All 6 issues (confidence >= 82%) addressed, one task each.

**Skipped (verified false positives):**
- `ensure_on_village` implicit None — lines 140-143 always execute after the inner loop; no None return path
- Onboarding bypass — `_update_nav()` re-checks and re-disables Next when landing on card 2; bypass doesn't work as described

**Placeholder scan:** All steps contain concrete code. No TBDs.

**Type consistency:** No new types introduced. All method names match the existing codebase.
