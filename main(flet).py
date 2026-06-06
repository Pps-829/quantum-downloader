"""
QuantumDownloader — Flet Edition
==================================
Cross-platform download manager with a rich dark-theme UI.

Features:
  • Real downloads via urllib (threaded, non-blocking)
  • Pause / Resume / Cancel per download
  • Per-download speed limiting
  • Concurrency queue (max N simultaneous)
  • Desktop notifications via SnackBar
  • Persistent settings (JSON)
  • Completed downloads history
  • Clipboard auto-detection of URLs
  • Open file / folder when done
  • Minimise-to-tray (platform tray via OS)

Run:    python main_flet.py
"""

import flet as ft
import threading
import urllib.request
import urllib.error
import os
import json
import time
import re
import platform
import subprocess
from pathlib import Path
from collections import deque

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS  (persisted to app config dir)
# ─────────────────────────────────────────────────────────────────────────────
_IS_ANDROID = "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ
if _IS_ANDROID:
    _CFG_DIR  = Path(__file__).parent / ".config" / "QuantumDownloader"
    _DL_DIR   = str(Path.home() / "Download")
else:
    _CFG_DIR  = Path.home() / ".config" / "QuantumDownloader"
    _DL_DIR   = str(Path.home() / "Downloads")
_CFG_FILE = _CFG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "download_dir":     _DL_DIR,
    "max_speed_kb":     0,
    "max_concurrent":   3,
    "minimize_to_tray": True,
    "notify_on_done":   True,
    "open_on_done":     False,
    "clipboard_watch":  True,
}

def load_settings() -> dict:
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    if _CFG_FILE.exists():
        try:
            s = DEFAULT_SETTINGS.copy()
            s.update(json.loads(_CFG_FILE.read_text()))
            return s
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(s: dict):
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    _CFG_FILE.write_text(json.dumps(s, indent=2))

SETTINGS = load_settings()

# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────
T = {
    "bg_deep":      "#07090F",
    "bg_base":      "#0A0E1A",
    "bg_panel":     "#0D1120",
    "bg_card":      "#111827",
    "bg_card2":     "#151D2E",
    "border":       "#1E2D45",
    "accent":       "#7DE8FF",
    "accent2":      "#5B6EFF",
    "accent3":      "#A259FF",
    "success":      "#3DFFA0",
    "warning":      "#FFB547",
    "danger":       "#FF6B6B",
    "text_primary": "#EDF2FF",
    "text_sec":     "#8A8FA8",
    "text_dim":     "#3D4460",
}

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD TASK  (runs in a background thread)
# ─────────────────────────────────────────────────────────────────────────────
class DownloadTask:
    """Manages a single file download in a thread."""

    CHUNK = 65536  # 64 KB

    def __init__(self, url: str, dest: str, max_speed_kb: int = 0):
        self.url          = url
        self.dest         = dest
        self.max_speed_kb = max_speed_kb
        self._pause       = threading.Event()
        self._pause.set()
        self._stop        = threading.Event()
        self._thread: threading.Thread | None = None
        self._samples: deque = deque(maxlen=8)
        # Public state accessible from UI thread
        self.progress_pct  = 0.0
        self.speed_bps     = 0.0
        self.size_str      = "—  /  —"
        self.speed_str     = "—"
        self.eta_str       = "ETA —:—"
        self.status        = "Queued"
        self.error_msg     = ""
        self._done_bytes   = 0
        self._total_bytes  = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.status = "Downloading"

    def pause(self):
        self._pause.clear()
        self.status = "Paused"

    def resume(self):
        self._pause.set()
        self.status = "Downloading"

    def cancel(self):
        self._stop.set()
        self._pause.set()
        self.status = "Cancelled"

    def _run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "QuantumDownloader/3.1 (Flet)"},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                total = int(r.headers.get("Content-Length", 0))
                self._total_bytes = total
                done = 0
                t0   = time.monotonic()
                tl   = t0
                bl   = 0
                os.makedirs(os.path.dirname(self.dest) or ".", exist_ok=True)
                with open(self.dest, "wb") as f:
                    while True:
                        if self._stop.is_set():
                            self._cleanup_partial()
                            self.status = "Cancelled"
                            return
                        self._pause.wait()
                        chunk = r.read(self.CHUNK)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        self._done_bytes = done

                        # Throttle
                        if self.max_speed_kb > 0:
                            elapsed  = time.monotonic() - t0
                            expected = done / (self.max_speed_kb * 1024)
                            if expected > elapsed:
                                time.sleep(expected - elapsed)

                        # Update stats every ~0.5 s
                        now = time.monotonic()
                        if now - tl >= 0.5:
                            bps = (done - bl) / (now - tl)
                            self._samples.append(bps)
                            avg = sum(self._samples) / len(self._samples)
                            self.speed_bps = avg
                            tl, bl = now, done
                            pct = (done / total * 100) if total else 0
                            self.progress_pct = pct
                            self.size_str  = self._fmt_size(done, total)
                            self.speed_str = self._fmt_speed(avg)
                            self.eta_str   = self._fmt_eta(total - done, avg)

                self.status = "Completed"
        except urllib.error.URLError as e:
            self.status = "Error"
            self.error_msg = f"Network error: {e.reason}"
            self._cleanup_partial()
        except Exception as e:
            self.status = "Error"
            self.error_msg = str(e) or "Unknown error"
            self._cleanup_partial()

    def _cleanup_partial(self):
        if os.path.exists(self.dest):
            try:
                os.remove(self.dest)
            except OSError:
                pass

    @staticmethod
    def _fmt_size(done, total):
        def h(b):
            for u in ["B", "KB", "MB", "GB"]:
                if b < 1024:
                    return f"{b:.1f} {u}"
                b /= 1024
            return f"{b:.2f} TB"
        return f"{h(done)} / {h(total)}" if total else h(done)

    @staticmethod
    def _fmt_speed(bps):
        if bps < 1024:
            return f"{bps:.0f} B/s"
        if bps < 1 << 20:
            return f"{bps / 1024:.1f} KB/s"
        return f"{bps / (1 << 20):.2f} MB/s"

    @staticmethod
    def _fmt_eta(rem, bps):
        if bps <= 0 or rem <= 0:
            return "--:--"
        s = int(rem / bps)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

class DownloadCard(ft.Container):
    """A single download card showing file info, progress, and actions."""

    def __init__(self, filename: str, url: str, dest: str, task: DownloadTask,
                 page: ft.Page, on_remove):
        self._filename = filename
        self._url      = url
        self._dest     = dest
        self._task     = task
        self._page     = page
        self._on_remove = on_remove

        # File-type colour chip
        ext = filename.rsplit(".", 1)[-1].upper()[:4] if "." in filename else "FILE"
        chip = ft.Container(
            width=42, height=42,
            border_radius=10,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[T["accent2"], T["accent3"]],
            ),
            content=ft.Text(ext, size=10, weight=ft.FontWeight.W_800,
                            color="white", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
        )

        # Filename and URL
        self._lbl_name = ft.Text(filename, size=13, weight=ft.FontWeight.W_700,
                                  color=T["text_primary"])
        self._lbl_url  = ft.Text(url, size=11, color=T["text_dim"],
                                  no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)

        # Percent label
        self._lbl_pct = ft.Text("0%", size=20, weight=ft.FontWeight.W_800,
                                 color=T["accent"], text_align=ft.TextAlign.RIGHT)

        # Info column
        info_col = ft.Column([self._lbl_name, self._lbl_url], spacing=2, expand=True)

        # Row 1: chip + info + percent
        row1 = ft.Row([chip, info_col, self._lbl_pct], spacing=14,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Progress bar
        self._bar = ft.ProgressBar(
            width=float("inf"), height=6,
            value=0,
            bar_thickness=6,
            color=T["accent"],
            bgcolor="#1A1F35",
            border_radius=ft.border_radius.all(3),
        )

        # Row 2: size, speed, eta, badge, buttons
        self._lbl_size  = ft.Text("—  /  —", size=11, color=T["text_sec"])
        self._lbl_speed = ft.Text("—", size=11, weight=ft.FontWeight.W_600,
                                   color=T["accent"])
        sep             = ft.Text("·", size=11, color=T["text_dim"])
        self._lbl_eta   = ft.Text("ETA —", size=11, color=T["text_sec"])

        self._badge = ft.Container(
            content=ft.Text("QUEUED", size=10, weight=ft.FontWeight.W_700,
                            color=T["text_sec"]),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor="rgba(138, 143, 168, 0.10)",
        )

        # Buttons
        self._btn_pause  = self._make_icon_button(ft.icons.PAUSE_CIRCLE_FILLED,
                                                    "Pause / Resume", self._toggle_pause)
        self._btn_open   = self._make_icon_button(ft.icons.OPEN_IN_NEW,
                                                    "Open file", self._open_file)
        self._btn_folder = self._make_icon_button(ft.icons.FOLDER_OPEN,
                                                    "Show in folder", self._reveal)
        self._btn_cancel = self._make_icon_button(ft.icons.DELETE_FOREVER,
                                                    "Cancel & remove", self._cancel)
        self._btn_open.visible   = False
        self._btn_folder.visible = False

        row2 = ft.Row([
            self._lbl_size, sep, self._lbl_speed, sep, self._lbl_eta,
            ft.Container(expand=True),
            self._badge,
            self._btn_pause, self._btn_open, self._btn_folder, self._btn_cancel,
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        super().__init__(
            content=ft.Column([row1, self._bar, row2], spacing=10),
            border=ft.border.all(1, T["border"]),
            border_radius=14,
            bgcolor=T["bg_card"],
            padding=16,
            animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        )

    def _make_icon_button(self, icon, tooltip, on_click):
        return ft.IconButton(
            icon=icon,
            icon_size=18,
            tooltip=tooltip,
            on_click=on_click,
            style=ft.ButtonStyle(
                color=T["text_sec"],
                bgcolor={"": "rgba(255,255,255,0.05)",
                         ft.MaterialState.HOVERED: "rgba(125,232,255,0.12)"},
                shape=ft.RoundedRectangleBorder(radius=8),
                side={"": ft.BorderSide(1, T["border"]),
                       ft.MaterialState.HOVERED: ft.BorderSide(1, T["accent"])},
            ),
        )

    def _toggle_pause(self, e):
        if self._task.status == "Downloading":
            self._task.pause()
            self._btn_pause.icon = ft.icons.PLAY_CIRCLE_FILLED
            self._apply_badge("Paused")
        elif self._task.status == "Paused":
            self._task.resume()
            self._btn_pause.icon = ft.icons.PAUSE_CIRCLE_FILLED
            self._apply_badge("Downloading")
        self.update()

    def _open_file(self, e):
        if os.path.exists(self._dest):
            _open_file_or_folder(self._dest)

    def _reveal(self, e):
        folder = os.path.dirname(self._dest)
        if os.path.isdir(folder):
            _open_file_or_folder(folder)

    def _cancel(self, e):
        self._task.cancel()
        self._on_remove(self)

    def refresh_from_task(self):
        """Update UI from the current task state."""
        t = self._task
        if t.status == "Downloading":
            pct = int(t.progress_pct)
            self._bar.value = pct / 100.0
            self._lbl_pct.value = f"{pct}%"
            self._lbl_size.value = t.size_str
            self._lbl_speed.value = t.speed_str
            self._lbl_eta.value = f"ETA {t.eta_str}"
            self._apply_badge("Downloading")
        elif t.status == "Paused":
            self._apply_badge("Paused")
        elif t.status == "Completed":
            self._bar.value = 1.0
            self._lbl_pct.value = "100%"
            self._lbl_speed.value = "Done"
            self._lbl_eta.value = ""
            self._btn_pause.visible = False
            self._btn_open.visible = True
            self._btn_folder.visible = True
            self._apply_badge("Completed")
        elif t.status == "Error":
            self._apply_badge("Error")
            self.tooltip = t.error_msg or "Download failed"
            self._btn_pause.visible = False
        elif t.status == "Cancelled":
            self._apply_badge("Cancelled")
            self._btn_pause.visible = False
        else:
            self._apply_badge(t.status)

    def _apply_badge(self, status):
        styles = {
            "Downloading": ("DOWNLOADING", T["accent"], "rgba(125,232,255,0.12)"),
            "Paused":      ("PAUSED",      T["warning"], "rgba(255,181,71,0.12)"),
            "Queued":      ("QUEUED",      T["text_sec"], "rgba(138,143,168,0.10)"),
            "Completed":   ("COMPLETED",   T["success"], "rgba(61,255,160,0.12)"),
            "Error":       ("ERROR",       T["danger"], "rgba(255,107,107,0.12)"),
            "Cancelled":   ("CANCELLED",   T["text_sec"], "rgba(138,143,168,0.10)"),
        }
        text, color, bg = styles.get(status, ("QUEUED", T["text_sec"], "rgba(138,143,168,0.10)"))
        self._badge.content = ft.Text(text, size=10, weight=ft.FontWeight.W_700, color=color)
        self._badge.bgcolor = bg
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _open_file_or_folder(path):
    sys_name = platform.system()
    if sys_name == "Windows":
        subprocess.run(["explorer", "/select,", path], check=False)
    elif sys_name == "Darwin":
        subprocess.run(["open", "-R", path], check=False)
    else:
        try:
            subprocess.run(["xdg-open", path], check=False)
        except Exception:
            pass


def sanitise_filename(name: str) -> str:
    name = "".join(c for c in name if c.isprintable() and c not in '<>:"/\\|?*')
    name = name.strip(". ")
    return name or f"download_{int(time.time())}"


# ─────────────────────────────────────────────────────────────────────────────
# PAGE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

class ActiveView(ft.Container):
    def __init__(self, page: ft.Page, app_ref):
        super().__init__(expand=True)
        self._page = page
        self._app  = app_ref
        self._cards: list[DownloadCard] = []

        # URL bar
        self._url_input = ft.TextField(
            hint_text="Paste a download URL here…",
            border_radius=10,
            filled=True,
            fill_color=T["bg_card"],
            border_color=T["border"],
            focused_border_color=T["accent"],
            text_style=ft.TextStyle(color=T["text_primary"], size=13),
            hint_style=ft.TextStyle(color=T["text_dim"]),
            expand=True,
            on_submit=self._from_bar,
            prefix_icon=ft.icons.LINK,
        )
        self._btn_dl = ft.FilledButton(
            "Download",
            icon=ft.icons.DOWNLOAD,
            on_click=self._from_bar,
            style=ft.ButtonStyle(
                color=T["bg_deep"],
                bgcolor={"": ft.LinearGradient(
                    begin=ft.alignment.center_left,
                    end=ft.alignment.center_right,
                    colors=[T["accent"], T["accent2"]],
                )},
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )
        url_bar = ft.Container(
            content=ft.Row([self._url_input, self._btn_dl], spacing=10),
            border=ft.border.all(1, T["border"]),
            border_radius=14,
            bgcolor=T["bg_card"],
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
        )

        # Card list (scrollable)
        self._card_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        self._empty_state = ft.Container(
            content=ft.Column([
                ft.Text("↓", size=48, color=T["text_dim"]),
                ft.Text("Paste a URL above to start downloading",
                        size=14, color=T["text_dim"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.center,
            expand=True,
        )

        # Stack: card list on top, empty state behind
        self._card_stack = ft.Stack(
            [self._empty_state, ft.Container(content=self._card_list, expand=True)],
            expand=True,
        )

        self.content = ft.Column([
            ft.Text("Active Downloads", size=26, weight=ft.FontWeight.W_800,
                    color=T["text_primary"]),
            ft.Text("Manage and monitor your queue", size=12, color=T["text_sec"]),
            ft.Container(height=8),
            url_bar,
            ft.Container(height=8),
            self._card_stack,
        ], spacing=4, expand=True)
        self.padding = 28

    def _from_bar(self, e):
        url = self._url_input.value.strip()
        if url:
            self._app.enqueue(url)
            self._url_input.value = ""
            self._url_input.update()

    def add_card(self, card: DownloadCard):
        self._cards.append(card)
        self._card_list.controls.append(card)
        self._update_empty_state()
        self._card_list.update()

    def remove_card(self, card: DownloadCard):
        if card in self._cards:
            self._cards.remove(card)
            self._card_list.controls.remove(card)
            self._update_empty_state()
            self._card_list.update()

    def take_card(self, card: DownloadCard):
        """Detach without deleting — for moving to completed."""
        if card in self._cards:
            self._cards.remove(card)
            self._card_list.controls.remove(card)
            self._update_empty_state()
        return card

    def _update_empty_state(self):
        show = len(self._cards) == 0
        self._empty_state.visible = show
        for c in self._card_list.controls:
            c.visible = not show

    def refresh_all(self):
        for card in self._cards:
            card.refresh_from_task()
        if self._cards:
            self._card_list.update()


class CompletedView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page
        self._cards: list[DownloadCard] = []

        self._card_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        self._empty_state = ft.Container(
            content=ft.Column([
                ft.Text("✓", size=48, color=T["text_dim"]),
                ft.Text("No completed downloads yet", size=14, color=T["text_dim"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            alignment=ft.alignment.center,
            expand=True,
        )

        self._stack = ft.Stack(
            [self._empty_state, ft.Container(content=self._card_list, expand=True)],
            expand=True,
        )

        self.content = ft.Column([
            ft.Text("Completed", size=26, weight=ft.FontWeight.W_800,
                    color=T["text_primary"]),
            ft.Text("Your finished downloads", size=12, color=T["text_sec"]),
            ft.Container(height=12),
            self._stack,
        ], spacing=4, expand=True)
        self.padding = 28

    def add_card(self, card: DownloadCard):
        self._cards.append(card)
        self._card_list.controls.append(card)
        self._update_empty_state()
        self._card_list.update()

    def _update_empty_state(self):
        show = len(self._cards) == 0
        self._empty_state.visible = show
        for c in self._card_list.controls:
            c.visible = not show


class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, on_change):
        super().__init__(expand=True)
        self._page     = page
        self._on_change = on_change

        # Download directory
        self._lbl_dir = ft.Text(SETTINGS["download_dir"], size=13,
                                 color=T["text_sec"], expand=True)

        def pick_dir(e):
            # Flet's file picker dialog
            def on_result(result: ft.FilePickerResultEvent):
                if result.path:
                    SETTINGS["download_dir"] = result.path
                    self._lbl_dir.value = result.path
                    self._lbl_dir.update()
                    save_settings(SETTINGS)
                    self._on_change()
            if not hasattr(self._page, "_dir_picker"):
                self._page._dir_picker = ft.FilePicker(on_result=on_result)
                self._page.overlay.append(self._page._dir_picker)
            self._page._dir_picker.get_directory_path()

        self._dir_picker_btn = ft.TextButton("Browse…", on_click=pick_dir,
                                              style=ft.ButtonStyle(
                                                  color=T["accent"],
                                                  shape=ft.RoundedRectangleBorder(radius=10),
                                                  side=ft.BorderSide(1, T["border"]),
                                              ))

        dir_row = ft.Row([
            ft.Text("Save to", size=13, weight=ft.FontWeight.W_600,
                    color=T["text_primary"]),
            self._lbl_dir,
            self._dir_picker_btn,
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Speed limit
        self._spd_field = ft.TextField(
            value=str(SETTINGS["max_speed_kb"]),
            label="Speed limit (0 = unlimited)",
            suffix_text="KB/s",
            width=180,
            border_radius=10,
            filled=True,
            fill_color=T["bg_card"],
            border_color=T["border"],
            focused_border_color=T["accent"],
            text_style=ft.TextStyle(color=T["text_primary"]),
            label_style=ft.TextStyle(color=T["text_sec"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._save_spd,
        )

        # Max concurrent
        self._cc_field = ft.TextField(
            value=str(SETTINGS["max_concurrent"]),
            label="Max simultaneous",
            suffix_text="downloads",
            width=200,
            border_radius=10,
            filled=True,
            fill_color=T["bg_card"],
            border_color=T["border"],
            focused_border_color=T["accent"],
            text_style=ft.TextStyle(color=T["text_primary"]),
            label_style=ft.TextStyle(color=T["text_sec"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._save_cc,
        )

        speed_cc_row = ft.Row([self._spd_field, self._cc_field], spacing=24)

        # Behaviour checkboxes
        self._cb_toggle    = ft.Checkbox(label="Minimise to system tray",
                                           value=SETTINGS["minimize_to_tray"],
                                           on_change=lambda e: self._toggle("minimize_to_tray", e))
        self._cb_notify    = ft.Checkbox(label="Notification when download completes",
                                           value=SETTINGS["notify_on_done"],
                                           on_change=lambda e: self._toggle("notify_on_done", e))
        self._cb_open      = ft.Checkbox(label="Automatically open file when done",
                                           value=SETTINGS["open_on_done"],
                                           on_change=lambda e: self._toggle("open_on_done", e))
        self._cb_clip      = ft.Checkbox(label="Watch clipboard for URLs",
                                           value=SETTINGS["clipboard_watch"],
                                           on_change=lambda e: self._toggle("clipboard_watch", e))

        # About
        ver_info = f"Python {platform.python_version()}  ·  Flet"

        def make_row(*controls):
            return ft.Container(
                content=ft.Row(controls, spacing=12,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                border=ft.border.all(1, T["border"]),
                border_radius=10,
                bgcolor=T["bg_card"],
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
            )

        def section(title):
            return ft.Text(title, size=11, weight=ft.FontWeight.W_700,
                           color=T["text_dim"], letter_spacing=1.5)

        self.content = ft.Column([
            ft.Text("Settings", size=26, weight=ft.FontWeight.W_800,
                    color=T["text_primary"]),
            ft.Text("Preferences are saved automatically", size=12,
                    color=T["text_sec"]),
            ft.Container(height=12),
            section("DOWNLOAD LOCATION"),
            make_row(dir_row),
            ft.Container(height=8),
            section("SPEED & CONCURRENCY"),
            make_row(speed_cc_row),
            ft.Container(height=8),
            section("BEHAVIOUR"),
            make_row(self._cb_toggle),
            make_row(self._cb_notify),
            make_row(self._cb_open),
            make_row(self._cb_clip),
            ft.Container(height=8),
            section("ABOUT"),
            make_row(
                ft.Text("Version", size=13, weight=ft.FontWeight.W_600,
                        color=T["text_primary"]),
                ft.Text("3.1 — Flet Edition", size=12, color=T["text_sec"],
                        expand=True, text_align=ft.TextAlign.RIGHT),
            ),
            make_row(
                ft.Text("Runtime", size=13, weight=ft.FontWeight.W_600,
                        color=T["text_primary"]),
                ft.Text(ver_info, size=12, color=T["text_sec"],
                        expand=True, text_align=ft.TextAlign.RIGHT),
            ),
            make_row(
                ft.Text("Platform", size=13, weight=ft.FontWeight.W_600,
                        color=T["text_primary"]),
                ft.Text(platform.system(), size=12, color=T["text_sec"],
                        expand=True, text_align=ft.TextAlign.RIGHT),
            ),
        ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
        self.padding = 28

    def _toggle(self, key, e):
        SETTINGS[key] = e.control.value
        save_settings(SETTINGS)
        self._on_change()

    def _save_spd(self, e):
        try:
            SETTINGS["max_speed_kb"] = int(self._spd_field.value)
            save_settings(SETTINGS)
            self._on_change()
        except ValueError:
            pass

    def _save_cc(self, e):
        try:
            SETTINGS["max_concurrent"] = max(1, min(10, int(self._cc_field.value)))
            save_settings(SETTINGS)
            self._on_change()
        except ValueError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class QuantumApp:
    def __init__(self, page: ft.Page):
        self._page = page
        self._active_tasks: list[DownloadTask] = []
        self._last_clip = ""

        # Configure page
        page.title = "QuantumDownloader"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = T["bg_base"]
        page.scroll = ft.ScrollMode.NO_SCROLL
        page.padding = 0
        page.update()

        # Views
        self._active_view    = ActiveView(page, self)
        self._completed_view = CompletedView(page)
        self._settings_view  = SettingsView(page, self._on_settings_change)

        # Stack all views
        self._view_stack = ft.Stack(
            [self._active_view, self._completed_view, self._settings_view],
            expand=True,
        )
        self._completed_view.visible = False
        self._settings_view.visible  = False

        # Sidebar
        self._nav_buttons: list[ft.Container] = []
        self._build_sidebar()

        # Main layout: sidebar + content
        main_row = ft.Row([
            self._sidebar_container,
            ft.Container(content=self._view_stack, expand=True, bgcolor=T["bg_base"]),
        ], spacing=0, expand=True)

        page.add(main_row)

        # Timers — use call_later for periodic tasks
        self._schedule_refresh()
        self._schedule_queue_flush()
        self._schedule_clipboard()

    # ── Sidebar ────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        logo = ft.Container(
            content=ft.Column([
                ft.Text("QUANTUM", size=20, weight=ft.FontWeight.W_800,
                        color=T["accent"], letter_spacing=1),
                ft.Text("DOWNLOADER", size=10, weight=ft.FontWeight.W_400,
                        color=T["text_dim"], letter_spacing=3),
            ], spacing=0),
            padding=ft.padding.only(left=6, top=20, bottom=8),
        )

        def make_nav(icon, label, idx):
            btn = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=20, color=T["text_sec"]),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_600,
                            color=T["text_sec"]),
                ], spacing=12),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=11),
                ink=True,
                on_click=lambda e, i=idx: self._switch_view(i),
            )
            return btn

        # KPI chips
        self._chip_active = ft.Container(
            content=ft.Column([
                ft.Text("0", size=24, weight=ft.FontWeight.W_700,
                        color=T["accent"]),
                ft.Text("ACTIVE", size=9, weight=ft.FontWeight.W_600,
                        color=T["text_sec"], letter_spacing=1),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            border=ft.border.all(1, T["border"]),
            border_radius=10,
            bgcolor=T["bg_card"],
            padding=12,
            expand=True,
        )
        self._chip_completed = ft.Container(
            content=ft.Column([
                ft.Text("0", size=24, weight=ft.FontWeight.W_700,
                        color=T["accent"]),
                ft.Text("COMPLETED", size=9, weight=ft.FontWeight.W_600,
                        color=T["text_sec"], letter_spacing=1),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            border=ft.border.all(1, T["border"]),
            border_radius=10,
            bgcolor=T["bg_card"],
            padding=12,
            expand=True,
        )

        chips = ft.Row([self._chip_active, self._chip_completed], spacing=8)

        # Total speed
        self._lbl_speed_total = ft.Container(
            content=ft.Text("↓  0 KB/s", size=11, weight=ft.FontWeight.W_600,
                            color=T["accent"]),
            border=ft.border.all(1, "rgba(125,232,255,0.12)"),
            border_radius=8,
            bgcolor="rgba(125,232,255,0.07)",
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        )

        version = ft.Text("v3.1 — Flet Edition", size=9, color=T["text_dim"])

        # Build nav buttons
        nav_items = [
            (ft.icons.INSIGHTS, "Active", 0),
            (ft.icons.CHECK_CIRCLE_OUTLINE, "Completed", 1),
            (ft.icons.SETTINGS_OUTLINED, "Settings", 2),
        ]
        for icon, label, idx in nav_items:
            btn = make_nav(icon, label, idx)
            self._nav_buttons.append(btn)
            if idx == 0:
                btn.bgcolor = "rgba(125,232,255,0.10)"
                btn.content.controls[0].color = T["accent"]
                btn.content.controls[1].color = T["accent"]

        self._sidebar_container = ft.Container(
            content=ft.Column([
                logo,
                ft.Divider(height=1, color=T["border"]),
                ft.Container(height=8),
                *self._nav_buttons,
                ft.Container(height=16),
                ft.Divider(height=1, color=T["border"]),
                ft.Container(height=8),
                chips,
                ft.Container(height=8),
                self._lbl_speed_total,
                ft.Container(expand=True),
                version,
            ], spacing=4),
            width=200,
            bgcolor=T["bg_panel"],
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.border.only(right=ft.BorderSide(1, T["border"])),
        )

    def _update_nav_style(self, active_idx: int):
        for i, btn in enumerate(self._nav_buttons):
            if i == active_idx:
                btn.bgcolor = "rgba(125,232,255,0.10)"
                btn.content.controls[0].color = T["accent"]  # icon
                btn.content.controls[1].color = T["accent"]  # text
            else:
                btn.bgcolor = None
                btn.content.controls[0].color = T["text_sec"]
                btn.content.controls[1].color = T["text_sec"]
            btn.update()

    def _switch_view(self, idx: int):
        self._update_nav_style(idx)
        self._active_view.visible    = (idx == 0)
        self._completed_view.visible = (idx == 1)
        self._settings_view.visible  = (idx == 2)
        self._view_stack.update()

    # ── Download lifecycle ────────────────────────────────────────────────

    def enqueue(self, url: str):
        if not url.startswith(("http://", "https://", "ftp://")):
            self._page.show_snack_bar(
                ft.SnackBar(ft.Text(f"Invalid URL: {url}"),
                            bgcolor=T["danger"])
            )
            return

        raw = url.split("?")[0].split("/")[-1]
        filename = raw if raw and "." in raw else f"download_{int(time.time())}"
        filename = sanitise_filename(filename)

        dest = os.path.join(SETTINGS["download_dir"], filename)
        base, ext = os.path.splitext(dest)
        n = 1
        while os.path.exists(dest):
            dest = f"{base} ({n}){ext}"
            n += 1

        task  = DownloadTask(url, dest, SETTINGS["max_speed_kb"])
        card  = DownloadCard(filename, url, dest, task,
                             self._page, self._remove_card_from_active)
        self._active_tasks.append(task)
        self._active_view.add_card(card)
        self._try_start(task)
        self._update_chips()

    def _remove_card_from_active(self, card: DownloadCard):
        if card._task in self._active_tasks:
            self._active_tasks.remove(card._task)
        self._active_view.remove_card(card)
        self._update_chips()

    def _try_start(self, task: DownloadTask):
        running = sum(1 for t in self._active_tasks
                      if t.status == "Downloading")
        if running < SETTINGS["max_concurrent"]:
            task.start()

    def _flush_queue(self):
        running = sum(1 for t in self._active_tasks
                      if t.status == "Downloading")
        slots = SETTINGS["max_concurrent"] - running
        for task in self._active_tasks:
            if slots <= 0:
                break
            if task.status == "Queued":
                task.start()
                slots -= 1

    def _on_task_done(self, task: DownloadTask):
        """Called when a download completes or fails."""
        if task.status != "Completed":
            return

        # Find matching card
        card = None
        for v in [self._active_view, self._completed_view]:
            for c in v._cards:
                if c._task is task:
                    card = c
                    break
            if card:
                break
        if not card:
            return

        # Notify
        if SETTINGS["notify_on_done"]:
            self._page.show_snack_bar(
                ft.SnackBar(
                    ft.Text(f"Download complete: {card._filename}"),
                    bgcolor=T["success"],
                    duration=4000,
                )
            )

        # Open file
        if SETTINGS["open_on_done"] and os.path.exists(task.dest):
            _open_file_or_folder(task.dest)

        # Move to completed after a short delay
        def _move():
            self._active_view.take_card(card)
            self._completed_view.add_card(card)
            self._update_chips()
        self._page.call_later(1.5, _move)

    # ── Timers ────────────────────────────────────────────────────────────

    def _schedule_refresh(self):
        self._refresh_all_ui()
        self._page.call_later(0.5, self._schedule_refresh)

    def _schedule_queue_flush(self):
        self._flush_queue()
        # Check for completed tasks
        for task in list(self._active_tasks):
            if task.status == "Completed":
                self._on_task_done(task)
        self._page.call_later(1.5, self._schedule_queue_flush)

    def _schedule_clipboard(self):
        self._check_clipboard()
        self._page.call_later(0.7, self._schedule_clipboard)

    def _refresh_all_ui(self):
        self._active_view.refresh_all()

        # Update total speed
        total = sum(t.speed_bps for t in self._active_tasks
                    if t.status == "Downloading")
        if total >= 1024 * 1024 * 1024:
            txt = f"↓  {total / 1024 / 1024 / 1024:.2f} GB/s"
        elif total >= 1024 * 1024:
            txt = f"↓  {total / 1024 / 1024:.1f} MB/s"
        elif total >= 1024:
            txt = f"↓  {total / 1024:.0f} KB/s"
        elif total > 0:
            txt = f"↓  {total:.0f} B/s"
        else:
            txt = "↓  0 KB/s"
        self._lbl_speed_total.content.value = txt
        self._lbl_speed_total.update()

    def _update_chips(self):
        active_cnt    = len(self._active_view._cards)
        completed_cnt = len(self._completed_view._cards)
        self._chip_active.content.controls[0].value  = str(active_cnt)
        self._chip_completed.content.controls[0].value = str(completed_cnt)
        self._chip_active.update()
        self._chip_completed.update()

    def _check_clipboard(self):
        if not SETTINGS.get("clipboard_watch"):
            return
        try:
            import pyperclip
            text = pyperclip.paste().strip()
            if text and text != self._last_clip:
                self._last_clip = text
                if (text.startswith(("http://", "https://", "ftp://"))
                        and "\n" not in text
                        and len(text) < 2048
                        and not self._active_view._url_input.value):
                    self._active_view._url_input.value = text
                    self._active_view._url_input.update()
        except ImportError:
            pass  # pyperclip not installed — skip clipboard watch

    def _on_settings_change(self):
        pass  # settings already saved


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main(page: ft.Page):
    app = QuantumApp(page)


def run():
    try:
        ft.app(target=main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
