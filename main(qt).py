"""
QuantumDownloader — Production-grade Download Manager
======================================================
Features:
  • Real downloads via urllib (threaded, non-blocking)
  • Clipboard auto-detection of URLs
  • Pause / Resume (via threading Event)
  • Per-download speed limiting (KB/s)
  • Open file / folder when done
  • System tray with minimize-to-tray
  • Desktop notifications on completion
  • Persistent settings (JSON)
  • Completed downloads history
  • Concurrency queue (max N simultaneous)

Requires:  pip install PyQt6
Run:       python quantum_downloader.py
"""

import sys
import os
import json
import time
import threading
import urllib.request
import urllib.error
import subprocess
import platform
from pathlib import Path
from collections import deque

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QSizePolicy, QScrollArea, QLineEdit,
    QSystemTrayIcon, QMenu, QFileDialog, QSpinBox, QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, QStandardPaths,
    QTimer, QPointF, QRectF, pyqtSignal, QThread, QObject,
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QLinearGradient,
    QRadialGradient, QPainterPath, QPalette,
)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS  (persisted to app config dir)
# ─────────────────────────────────────────────────────────────────────────────
_CFG_DIR  = Path(QStandardPaths.writableLocation(
    QStandardPaths.StandardLocation.AppConfigLocation)) / "QuantumDownloader"
_CFG_FILE = _CFG_DIR / "settings.json"
_DL_DIR   = Path(QStandardPaths.writableLocation(
    QStandardPaths.StandardLocation.DownloadLocation))

DEFAULT_SETTINGS = {
    "download_dir":     str(_DL_DIR),
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

QSS = f"""
* {{
    border: none; outline: none;
    font-family: 'Segoe UI Variable','SF Pro Display','Segoe UI','Helvetica Neue',sans-serif;
    font-size: 10pt; color: {T['text_primary']};
}}
QMainWindow, QWidget#root {{ background-color: {T['bg_base']}; }}
QFrame#sidebar {{
    background-color: {T['bg_panel']};
    border-right: 1px solid {T['border']};
}}
QLabel#app_logo_text {{
    font-size: 15pt; font-weight: 800; letter-spacing: 1px;
    color: {T['accent']}; padding: 0 4px;
}}
QLabel#app_logo_sub {{
    font-size: 7.5pt; color: {T['text_dim']};
    letter-spacing: 3px; padding: 0 5px;
}}
QPushButton[class="nav_btn"] {{
    background-color: transparent; text-align: left;
    padding: 11px 14px; border-radius: 10px;
    font-size: 10pt; font-weight: 600; color: {T['text_sec']};
    border-left: 3px solid transparent;
}}
QPushButton[class="nav_btn"]:hover {{
    background-color: rgba(125,232,255,0.06); color: {T['text_primary']};
}}
QPushButton[class="nav_btn"]:checked {{
    background-color: rgba(125,232,255,0.10);
    color: {T['accent']}; border-left: 3px solid {T['accent']};
}}
QFrame#stat_chip {{
    background-color: {T['bg_card']}; border: 1px solid {T['border']};
    border-radius: 10px; padding: 4px 8px;
}}
QLabel#stat_num {{ font-size: 18pt; font-weight: 700; color: {T['accent']}; }}
QLabel#stat_lbl {{ font-size: 8pt; color: {T['text_sec']}; letter-spacing: 1px; }}
QLabel#page_title {{
    font-size: 20pt; font-weight: 800;
    color: {T['text_primary']}; letter-spacing: -0.5px;
}}
QLabel#page_subtitle {{ font-size: 9pt; color: {T['text_sec']}; letter-spacing: 0.5px; }}
QPushButton#btn_primary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {T['accent']}, stop:1 {T['accent2']});
    color: {T['bg_deep']}; font-weight: 700; font-size: 9.5pt;
    letter-spacing: 0.4px; padding: 9px 20px; border-radius: 10px;
}}
QPushButton#btn_primary:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #9AEFFF, stop:1 #7B8EFF);
}}
QPushButton#btn_secondary {{
    background-color: {T['bg_card2']}; border: 1px solid {T['border']};
    color: {T['text_primary']}; font-weight: 600; padding: 8px 16px;
    border-radius: 10px;
}}
QPushButton#btn_secondary:hover {{
    border: 1px solid {T['accent']}; color: {T['accent']};
}}
QLineEdit#url_input {{
    background-color: {T['bg_card']}; border: 1.5px solid {T['border']};
    border-radius: 10px; padding: 9px 14px; font-size: 10pt;
    color: {T['text_primary']};
}}
QLineEdit#url_input:focus {{
    border: 1.5px solid {T['accent']}; background-color: {T['bg_card2']};
}}
QFrame#dl_card {{
    background-color: {T['bg_card']}; border: 1px solid {T['border']};
    border-radius: 14px;
}}
QLabel#dl_filename {{ font-weight: 700; font-size: 10.5pt; color: {T['text_primary']}; }}
QLabel#dl_url      {{ font-size: 8.5pt; color: {T['text_dim']}; }}
QLabel#dl_speed    {{ font-size: 9pt; font-weight: 600; color: {T['accent']}; }}
QLabel#dl_percent  {{ font-size: 13pt; font-weight: 800; color: {T['accent']}; }}
QPushButton[class="icon_btn"] {{
    background-color: rgba(255,255,255,0.05); border-radius: 8px;
    padding: 6px; border: 1px solid {T['border']};
}}
QPushButton[class="icon_btn"]:hover {{
    background-color: rgba(125,232,255,0.12); border: 1px solid {T['accent']};
}}
QScrollBar:vertical {{
    border: none; background: transparent; width: 6px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {T['border']}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {T['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical,  QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    border: none; background: transparent; height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {T['border']}; border-radius: 3px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {T['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ background: transparent; padding: 0; border: none; }}
QListWidget::item:selected {{ background: transparent; }}
QFrame#h_divider {{ background-color: {T['border']}; max-height: 1px; }}
QLabel#settings_section {{
    font-size: 9pt; font-weight: 700; color: {T['text_dim']}; letter-spacing: 1.5px;
}}
QFrame#settings_row {{
    background-color: {T['bg_card']}; border: 1px solid {T['border']};
    border-radius: 10px;
}}
QLabel#settings_key {{ font-size: 10pt; color: {T['text_primary']}; font-weight: 600; }}
QLabel#settings_val {{ font-size: 9.5pt; color: {T['text_sec']}; }}
QSpinBox {{
    background-color: {T['bg_card2']}; border: 1px solid {T['border']};
    border-radius: 8px; padding: 4px 8px; color: {T['text_primary']}; font-size: 10pt;
}}
QSpinBox:focus {{ border: 1px solid {T['accent']}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {T['border']}; border-radius: 4px; width: 18px;
}}
QCheckBox {{ color: {T['text_primary']}; font-size: 10pt; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 1.5px solid {T['border']}; background: {T['bg_card2']};
}}
QCheckBox::indicator:checked {{
    background: {T['accent']}; border: 1.5px solid {T['accent']};
}}
QMessageBox {{ background-color: {T['bg_base']}; }}
QMenu {{
    background: {T['bg_card']}; color: {T['text_primary']};
    border: 1px solid {T['border']}; border-radius: 8px; padding: 4px;
}}
QMenu::item:selected {{ background: {T['accent2']}; border-radius: 4px; }}
"""

# ─────────────────────────────────────────────────────────────────────────────
# PURE QPAINTER ICONS
# ─────────────────────────────────────────────────────────────────────────────
_CA = "#7DE8FF"; _CD = "#0A0E1A"; _CG = "#8A8FA8"; _CR = "#FF6B6B"; _CS = "#3DFFA0"

def _px(size):
    px = QPixmap(size, size); px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return px, p

def _pen(color, w):
    pen = QPen(QColor(color)); pen.setWidthF(w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen

def _i_download(n, c=_CA):
    px,p=_px(n); s=n; cx=s/2.0; m=s*0.15
    p.setPen(_pen(c,s*0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(m,s*0.78),QPointF(s-m,s*0.78))
    p.drawLine(QPointF(cx,m*0.8),QPointF(cx,s*0.60))
    path=QPainterPath(); path.moveTo(cx-s*0.22,s*0.40); path.lineTo(cx,s*0.63); path.lineTo(cx+s*0.22,s*0.40)
    p.drawPath(path); p.end(); return QIcon(px)

def _i_check(n, c=_CA):
    px,p=_px(n); s=n
    p.setPen(_pen(c,s*0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    path=QPainterPath(); path.moveTo(s*0.14,s*0.50); path.lineTo(s*0.42,s*0.76); path.lineTo(s*0.86,s*0.24)
    p.drawPath(path); p.end(); return QIcon(px)

def _i_settings(n, c=_CA):
    px,p=_px(n); s=n; pen=_pen(c,s*0.08); dr=s*0.09; p.setPen(pen)
    for yf,xf in [(0.28,0.35),(0.50,0.63),(0.72,0.40)]:
        y=s*yf; xd=s*xf
        p.drawLine(QPointF(s*0.12,y),QPointF(s*0.88,y))
        p.setBrush(QBrush(QColor(c))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(xd-dr,y-dr,dr*2,dr*2))
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(pen)
    p.end(); return QIcon(px)

def _i_plus(n, c=_CD):
    px,p=_px(n); s=n; m=s*0.22; cx=s/2.0; cy=s/2.0
    p.setPen(_pen(c,s*0.10)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(cx,m),QPointF(cx,s-m)); p.drawLine(QPointF(m,cy),QPointF(s-m,cy))
    p.end(); return QIcon(px)

def _i_pause(n, c=_CG):
    px,p=_px(n); s=n; bw=s*0.22; gap=s*0.14; top=s*0.22; h=s*0.56
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(c)))
    p.drawRoundedRect(QRectF(s/2-gap/2-bw,top,bw,h),2,2)
    p.drawRoundedRect(QRectF(s/2+gap/2,top,bw,h),2,2)
    p.end(); return QIcon(px)

def _i_play(n, c=_CG):
    px,p=_px(n); s=n
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(c)))
    tri=QPainterPath(); tri.moveTo(s*0.28,s*0.20); tri.lineTo(s*0.80,s*0.50)
    tri.lineTo(s*0.28,s*0.80); tri.closeSubpath(); p.drawPath(tri)
    p.end(); return QIcon(px)

def _i_trash(n, c=_CR):
    px,p=_px(n); s=n; pen=_pen(c,s*0.08)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(s*0.15,s*0.30),QPointF(s*0.85,s*0.30))
    p.drawLine(QPointF(s*0.38,s*0.30),QPointF(s*0.38,s*0.20))
    p.drawLine(QPointF(s*0.62,s*0.30),QPointF(s*0.62,s*0.20))
    p.drawLine(QPointF(s*0.38,s*0.20),QPointF(s*0.62,s*0.20))
    body=QPainterPath(); body.moveTo(s*0.25,s*0.32); body.lineTo(s*0.30,s*0.82)
    body.lineTo(s*0.70,s*0.82); body.lineTo(s*0.75,s*0.32); p.drawPath(body)
    p.drawLine(QPointF(s*0.44,s*0.42),QPointF(s*0.44,s*0.72))
    p.drawLine(QPointF(s*0.56,s*0.42),QPointF(s*0.56,s*0.72))
    p.end(); return QIcon(px)

def _i_link(n, c=_CD):
    px,p=_px(n); s=n; r=s*0.18
    p.setPen(_pen(c,s*0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(s*0.08,s*0.35,s*0.40,s*0.30),r,r)
    p.drawRoundedRect(QRectF(s*0.52,s*0.35,s*0.40,s*0.30),r,r)
    p.drawLine(QPointF(s*0.42,s*0.50),QPointF(s*0.58,s*0.50))
    p.end(); return QIcon(px)

def _i_activity(n, c=_CA):
    px,p=_px(n); s=n; p.setPen(_pen(c,s*0.08))
    pts=[QPointF(s*0.05,s*0.50),QPointF(s*0.25,s*0.50),QPointF(s*0.38,s*0.20),
         QPointF(s*0.52,s*0.80),QPointF(s*0.65,s*0.50),QPointF(s*0.95,s*0.50)]
    for i in range(len(pts)-1): p.drawLine(pts[i],pts[i+1])
    p.end(); return QIcon(px)

def _i_folder(n, c=_CA):
    px,p=_px(n); s=n; r=s*0.10
    p.setPen(_pen(c,s*0.08)); p.setBrush(Qt.BrushStyle.NoBrush)
    tab=QPainterPath(); tab.moveTo(s*0.10,s*0.42); tab.lineTo(s*0.10,s*0.35)
    tab.lineTo(s*0.38,s*0.35); tab.lineTo(s*0.46,s*0.42); p.drawPath(tab)
    p.drawRoundedRect(QRectF(s*0.10,s*0.42,s*0.80,s*0.42),r,r)
    p.end(); return QIcon(px)

def _i_open(n, c=_CA):
    px,p=_px(n); s=n
    p.setPen(_pen(c,s*0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(s*0.55,s*0.15),QPointF(s*0.85,s*0.15))
    p.drawLine(QPointF(s*0.85,s*0.15),QPointF(s*0.85,s*0.45))
    p.drawLine(QPointF(s*0.55,s*0.45),QPointF(s*0.85,s*0.15))
    p.drawRoundedRect(QRectF(s*0.10,s*0.35,s*0.55,s*0.50),s*0.08,s*0.08)
    p.end(); return QIcon(px)

def _i_tray(n, c=_CA):
    px,p=_px(n); s=n; cx=s/2.0
    p.setPen(Qt.PenStyle.NoPen)
    g=QRadialGradient(cx,cx,cx*0.8); g.setColorAt(0,QColor(c)); g.setColorAt(1,QColor(T['accent2']))
    p.setBrush(QBrush(g)); p.drawEllipse(QRectF(s*0.15,s*0.15,s*0.70,s*0.70))
    p.setPen(_pen(T['bg_deep'],s*0.10)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(cx,s*0.30),QPointF(cx,s*0.62))
    path=QPainterPath(); path.moveTo(cx-s*0.18,s*0.45); path.lineTo(cx,s*0.65); path.lineTo(cx+s*0.18,s*0.45)
    p.drawPath(path); p.end(); return QIcon(px)

_ICONS = {
    "download":_i_download, "check":_i_check, "settings":_i_settings,
    "plus":lambda n:_i_plus(n,_CD), "pause":_i_pause, "play":_i_play,
    "trash":_i_trash, "link":lambda n:_i_link(n,_CD),
    "activity":_i_activity, "folder":_i_folder, "open":_i_open, "tray":_i_tray,
}

def get_icon(name, size=24):
    fn = _ICONS.get(name)
    if fn: return fn(size)
    px=QPixmap(size,size); px.fill(Qt.GlobalColor.transparent); return QIcon(px)

def make_shadow(blur=24, color="#00C8FF", alpha=80, dy=4):
    s=QGraphicsDropShadowEffect(); s.setBlurRadius(blur)
    c=QColor(color); c.setAlpha(alpha); s.setColor(c); s.setOffset(0,dy); return s

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD WORKER  (runs inside a QThread)
# ─────────────────────────────────────────────────────────────────────────────
class DownloadWorker(QObject):
    progress   = pyqtSignal(float, str, str, str)  # pct, size_str, speed_str, eta_str
    status_msg = pyqtSignal(str)
    finished   = pyqtSignal(bool, str)             # success, filepath

    CHUNK = 65536  # 64 KB

    def __init__(self, url, dest, max_speed_kb=0):
        super().__init__()
        self.url          = url
        self.dest         = dest
        self.max_speed_kb = max_speed_kb
        self._pause       = threading.Event(); self._pause.set()
        self._stop        = threading.Event()
        self._samples: deque = deque(maxlen=8)

    def pause(self):  self._pause.clear()
    def resume(self): self._pause.set()
    def cancel(self): self._stop.set(); self._pause.set()

    def run(self):
        try:
            req = urllib.request.Request(self.url,
                headers={"User-Agent":"QuantumDownloader/3.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                total = int(r.headers.get("Content-Length", 0))
                done  = 0
                t0    = time.monotonic()
                tl    = t0; bl = 0
                os.makedirs(os.path.dirname(self.dest) or ".", exist_ok=True)
                with open(self.dest, "wb") as f:
                    while True:
                        if self._stop.is_set():
                            self.finished.emit(False, ""); return
                        self._pause.wait()
                        chunk = r.read(self.CHUNK)
                        if not chunk: break
                        f.write(chunk); done += len(chunk)

                        # throttle
                        if self.max_speed_kb > 0:
                            elapsed  = time.monotonic() - t0
                            expected = done / (self.max_speed_kb * 1024)
                            if expected > elapsed:
                                time.sleep(expected - elapsed)

                        # emit every ~0.5 s
                        now = time.monotonic()
                        if now - tl >= 0.5:
                            bps = (done - bl) / (now - tl)
                            self._samples.append(bps)
                            avg = sum(self._samples) / len(self._samples)
                            tl = now; bl = done
                            pct = done / total * 100 if total else 0
                            self.progress.emit(
                                pct,
                                self._fmt_size(done, total),
                                self._fmt_speed(avg),
                                self._fmt_eta(total - done, avg),
                            )
            self.status_msg.emit("Completed")
            self.finished.emit(True, self.dest)
        except urllib.error.URLError as e:
            err = f"Network error: {e.reason}"
            self.status_msg.emit("Error")
            self.finished.emit(False, err)
        except Exception as e:
            err = str(e) or "Unknown download error"
            self.status_msg.emit("Error")
            self.finished.emit(False, err)

    @staticmethod
    def _fmt_size(done, total):
        def h(b):
            for u in ["B","KB","MB","GB"]:
                if b < 1024: return f"{b:.1f} {u}"
                b /= 1024
            return f"{b:.2f} TB"
        return f"{h(done)} / {h(total)}" if total else h(done)

    @staticmethod
    def _fmt_speed(bps):
        if bps < 1024:    return f"{bps:.0f} B/s"
        if bps < 1<<20:   return f"{bps/1024:.1f} KB/s"
        return f"{bps/(1<<20):.2f} MB/s"

    @staticmethod
    def _fmt_eta(rem, bps):
        if bps <= 0 or rem <= 0: return "--:--"
        s = int(rem / bps); m,s = divmod(s,60); h,m = divmod(m,60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# ─────────────────────────────────────────────────────────────────────────────
# GLOW PROGRESS BAR
# ─────────────────────────────────────────────────────────────────────────────
class GlowBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self._v = 0
        self.setFixedHeight(6)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setValue(self, v): self._v = max(0,min(100,v)); self.update()
    def value(self): return self._v

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect(); h = r.height(); rad = h/2.0
        p.setBrush(QBrush(QColor(255,255,255,10))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(r), rad, rad)
        if self._v > 0:
            fw = max(int(r.width()*self._v/100), int(rad*2))
            fr = QRectF(r.x(), r.y(), fw, h)
            g = QLinearGradient(fr.left(),0,fr.right(),0)
            g.setColorAt(0,QColor(T['accent2'])); g.setColorAt(1,QColor(T['accent']))
            p.setBrush(QBrush(g)); p.drawRoundedRect(fr, rad, rad)
            gx=float(fr.right()-3); gy=float(r.center().y())
            rg=QRadialGradient(gx,gy,8.0)
            ts=QColor(T['accent']); tt=QColor(T['accent']); tt.setAlpha(0)
            rg.setColorAt(0,ts); rg.setColorAt(1,tt)
            p.setBrush(QBrush(rg)); p.drawEllipse(QRectF(gx-8,gy-8,16,16))
        p.end()

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD CARD
# ─────────────────────────────────────────────────────────────────────────────
class DownloadCard(QFrame):
    remove_requested = pyqtSignal(object)
    open_requested   = pyqtSignal(str)
    finished         = pyqtSignal(bool, str)

    def __init__(self, filename, url, dest):
        super().__init__()
        self.setObjectName("dl_card"); self.setContentsMargins(16,14,16,14)
        self.url = url; self.dest = dest
        self._status = "Queued"; self._paused = False
        self._worker: DownloadWorker | None = None
        self._thread: QThread | None = None
        self._speed_bps = 0.0
        self._error_msg = ""

        outer = QVBoxLayout(self); outer.setSpacing(10); outer.setContentsMargins(0,0,0,0)

        # Row 1
        r1 = QHBoxLayout(); r1.setSpacing(14)
        chip = QFrame(); chip.setFixedSize(42,42)
        chip.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {T['accent2']},stop:1 {T['accent3']});border-radius:10px;")
        ext = filename.rsplit(".",1)[-1].upper()[:4] if "." in filename else "FILE"
        el = QLabel(ext); el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setStyleSheet("font-size:7.5pt;font-weight:800;color:#FFF;background:transparent;")
        cl = QVBoxLayout(chip); cl.setContentsMargins(0,0,0,0); cl.addWidget(el)

        info = QVBoxLayout(); info.setSpacing(3)
        self.lbl_name = QLabel(filename); self.lbl_name.setObjectName("dl_filename")
        self.lbl_name.setWordWrap(True)
        self.lbl_url  = QLabel(url);      self.lbl_url.setObjectName("dl_url")
        self.lbl_url.setWordWrap(False)
        self.lbl_url.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.addWidget(self.lbl_name); info.addWidget(self.lbl_url)

        self.lbl_pct = QLabel("0%"); self.lbl_pct.setObjectName("dl_percent")
        self.lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        self.lbl_pct.setFixedWidth(54)
        r1.addWidget(chip); r1.addLayout(info,1); r1.addWidget(self.lbl_pct)

        # Progress bar
        self.bar = GlowBar()

        # Row 2
        r2 = QHBoxLayout(); r2.setSpacing(8)
        self.lbl_size  = QLabel("—  /  —")
        self.lbl_size.setStyleSheet(f"color:{T['text_sec']};font-size:8.5pt;")
        self.lbl_speed = QLabel("—"); self.lbl_speed.setObjectName("dl_speed")
        sep = QLabel("·"); sep.setStyleSheet(f"color:{T['text_dim']};")
        self.lbl_eta   = QLabel("ETA —")
        self.lbl_eta.setStyleSheet(f"color:{T['text_sec']};font-size:8.5pt;")
        r2.addWidget(self.lbl_size); r2.addWidget(sep)
        r2.addWidget(self.lbl_speed); r2.addWidget(sep)
        r2.addWidget(self.lbl_eta); r2.addStretch()

        self.badge = QLabel("QUEUED"); self._badge("Queued")

        self.btn_pause  = self._ibtn("pause",  "Pause / Resume")
        self.btn_open   = self._ibtn("open",   "Open file")
        self.btn_folder = self._ibtn("folder", "Show in folder")
        self.btn_cancel = self._ibtn("trash",  "Cancel & remove")
        self.btn_open.setVisible(False); self.btn_folder.setVisible(False)

        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_open.clicked.connect(lambda: self.open_requested.emit(self.dest))
        self.btn_folder.clicked.connect(self._reveal)
        self.btn_cancel.clicked.connect(self._cancel)

        r2.addWidget(self.badge)
        r2.addWidget(self.btn_pause); r2.addWidget(self.btn_open)
        r2.addWidget(self.btn_folder); r2.addWidget(self.btn_cancel)

        outer.addLayout(r1); outer.addWidget(self.bar); outer.addLayout(r2)

    def _ibtn(self, icon, tip):
        b = QPushButton(); b.setProperty("class","icon_btn")
        b.setIcon(get_icon(icon,16)); b.setIconSize(QSize(16,16))
        b.setFixedSize(32,32); b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tip); return b

    def _badge(self, status):
        styles = {
            "Downloading": f"background:rgba(125,232,255,0.12);color:{T['accent']};",
            "Paused":      f"background:rgba(255,181,71,0.12);color:{T['warning']};",
            "Queued":      f"background:rgba(138,143,168,0.10);color:{T['text_sec']};",
            "Completed":   f"background:rgba(61,255,160,0.12);color:{T['success']};",
            "Error":       f"background:rgba(255,107,107,0.12);color:{T['danger']};",
        }
        base = "border-radius:6px;padding:2px 10px;font-size:8pt;font-weight:700;letter-spacing:0.5px;"
        self.badge.setStyleSheet(styles.get(status, styles["Queued"]) + base)
        self.badge.setText(status.upper()); self._status = status

    @property
    def status(self): return self._status

    def start(self, max_speed_kb=0):
        if self._thread and self._thread.isRunning(): return
        self._worker = DownloadWorker(self.url, self.dest, max_speed_kb)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.status_msg.connect(self._badge)
        self._worker.finished.connect(self._on_worker_finished)
        self._thread.start()
        self._badge("Downloading")

    def _toggle_pause(self):
        if not self._worker: return
        self._paused = not self._paused
        if self._paused:
            self._worker.pause(); self._badge("Paused")
            self.btn_pause.setIcon(get_icon("play",16))
        else:
            self._worker.resume(); self._badge("Downloading")
            self.btn_pause.setIcon(get_icon("pause",16))

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
            self._worker = None
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        self.remove_requested.emit(self)

    def _on_progress(self, pct, size, speed, eta):
        self.bar.setValue(int(pct)); self.lbl_pct.setText(f"{int(pct)}%")
        self.lbl_size.setText(size); self.lbl_speed.setText(speed)
        self.lbl_eta.setText(f"ETA {eta}")
        # Parse and store raw speed for aggregate tracking
        try:
            val, unit = speed.split()
            val = float(val)
            if "MB" in unit: val *= 1024 * 1024
            elif "GB" in unit: val *= 1024 * 1024 * 1024
            elif "KB" in unit: val *= 1024
            self._speed_bps = val
        except Exception:
            self._speed_bps = 0.0

    def _on_worker_finished(self, ok, fp):
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        self._worker = None
        if ok:
            self.bar.setValue(100); self.lbl_pct.setText("100%")
            self.lbl_speed.setText("Done"); self.lbl_eta.setText("")
            self.btn_pause.setVisible(False)
            self.btn_open.setVisible(True); self.btn_folder.setVisible(True)
        else:
            self.btn_pause.setVisible(False)
            if fp:
                self._error_msg = fp
                self._badge("Error")
                self.setToolTip(fp)
        self.finished.emit(ok, fp)

    def _reveal(self):
        folder = os.path.dirname(self.dest)
        sys = platform.system()
        if sys == "Windows":
            subprocess.run(["explorer","/select,",self.dest], check=False)
        elif sys == "Darwin":
            subprocess.run(["open","-R",self.dest], check=False)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def enterEvent(self, e):
        self.setGraphicsEffect(make_shadow(32,T['accent'],40,6)); super().enterEvent(e)
    def leaveEvent(self, e):
        self.setGraphicsEffect(None); super().leaveEvent(e)

# ─────────────────────────────────────────────────────────────────────────────
# CARD LIST
# ─────────────────────────────────────────────────────────────────────────────
class EmptyState(QWidget):
    def __init__(self, msg):
        super().__init__()
        lay=QVBoxLayout(self); lay.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.setSpacing(10)
        ic=QLabel("↓"); ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet(f"font-size:40pt;color:{T['text_dim']};background:transparent;")
        lb=QLabel(msg); lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setStyleSheet(f"font-size:11pt;color:{T['text_dim']};background:transparent;")
        lay.addWidget(ic); lay.addWidget(lb)

class CardList(QScrollArea):
    count_changed = pyqtSignal()

    def __init__(self, empty_msg="Nothing here yet"):
        super().__init__()
        self.setWidgetResizable(True); self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cont = QWidget(); self._cont.setStyleSheet("background:transparent;")
        self._lay = QVBoxLayout(self._cont)
        self._lay.setContentsMargins(0,0,8,0); self._lay.setSpacing(10); self._lay.addStretch()
        self.setWidget(self._cont)
        self._cards: list[DownloadCard] = []
        self._empty = EmptyState(empty_msg)
        self._lay.insertWidget(0, self._empty)

    def add_card(self, card: DownloadCard):
        if card in self._cards: return
        self._cards.append(card)
        if self._empty.isVisible():
            self._lay.removeWidget(self._empty); self._empty.hide()
        self._lay.insertWidget(self._lay.count()-1, card)
        card.remove_requested.connect(self._remove)
        eff=QGraphicsOpacityEffect(card); card.setGraphicsEffect(eff)
        a=QPropertyAnimation(eff,b"opacity",card)
        a.setDuration(300); a.setStartValue(0.0); a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self.count_changed.emit()

    def _remove(self, card):
        if card not in self._cards: return
        self._cards.remove(card); self._lay.removeWidget(card); card.deleteLater()
        if not self._cards:
            self._lay.insertWidget(0,self._empty); self._empty.show()
        self.count_changed.emit()

    def take(self, card):
        """Detach without deleting — for moving to another list."""
        if card not in self._cards: return
        try: card.remove_requested.disconnect(self._remove)
        except RuntimeError: pass
        self._cards.remove(card); self._lay.removeWidget(card)
        card.setParent(None)
        if not self._cards:
            self._lay.insertWidget(0,self._empty); self._empty.show()
        self.count_changed.emit()

    def cards(self): return list(self._cards)

# ─────────────────────────────────────────────────────────────────────────────
# ANIMATED STACK
# ─────────────────────────────────────────────────────────────────────────────
class AnimatedStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._eff=QGraphicsOpacityEffect(self); self._eff.setOpacity(1.0)
        self.setGraphicsEffect(self._eff)
        self._anim=QPropertyAnimation(self._eff,b"opacity",self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic); self._p=None

    def slide_to(self, idx):
        if idx==self.currentIndex(): return
        self._p=idx; self._anim.stop()
        try: self._anim.finished.disconnect()
        except RuntimeError: pass
        self._anim.setDuration(160); self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0); self._anim.finished.connect(self._swap); self._anim.start()

    def _swap(self):
        try: self._anim.finished.disconnect()
        except RuntimeError: pass
        if self._p is not None: self.setCurrentIndex(self._p); self._p=None
        self._anim.setDuration(220); self._anim.setStartValue(0.0); self._anim.setEndValue(1.0)
        self._anim.start()

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS PAGE
# ─────────────────────────────────────────────────────────────────────────────
def _divider():
    d=QFrame(); d.setObjectName("h_divider"); d.setFixedHeight(1); return d

def _section(text):
    l=QLabel(text.upper()); l.setObjectName("settings_section"); return l

def _srow(*widgets):
    f=QFrame(); f.setObjectName("settings_row"); f.setContentsMargins(14,10,14,10)
    lay=QHBoxLayout(f); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
    for w in widgets: lay.addWidget(w)
    return f

class SettingsPage(QWidget):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        lay=QVBoxLayout(self); lay.setContentsMargins(28,26,28,20); lay.setSpacing(12)
        lay.addWidget(QLabel("Settings") if False else self._title())
        lay.addSpacing(4)

        # Download folder
        lay.addWidget(_section("Download Location"))
        lk=QLabel("Save to"); lk.setObjectName("settings_key")
        self.lbl_dir=QLabel(SETTINGS["download_dir"]); self.lbl_dir.setObjectName("settings_val")
        self.lbl_dir.setWordWrap(True)
        btn=QPushButton("Browse…"); btn.setObjectName("btn_secondary")
        btn.setFixedWidth(90); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._browse)
        lay.addWidget(_srow(*[lk, self.lbl_dir, btn]))

        # Speed + concurrency
        lay.addSpacing(4); lay.addWidget(_section("Speed & Concurrency"))

        lk2=QLabel("Speed limit  (0 = unlimited)"); lk2.setObjectName("settings_key")
        self.spin_spd=QSpinBox(); self.spin_spd.setRange(0,100_000)
        self.spin_spd.setValue(SETTINGS["max_speed_kb"]); self.spin_spd.setSuffix("  KB/s")
        self.spin_spd.setFixedWidth(150)
        lay.addWidget(_srow(lk2, self.spin_spd))

        lk3=QLabel("Max simultaneous downloads"); lk3.setObjectName("settings_key")
        self.spin_cc=QSpinBox(); self.spin_cc.setRange(1,10)
        self.spin_cc.setValue(SETTINGS["max_concurrent"]); self.spin_cc.setFixedWidth(60)
        lay.addWidget(_srow(lk3, self.spin_cc))

        # Checkboxes
        lay.addSpacing(4); lay.addWidget(_section("Behaviour"))
        for key, label in [
            ("minimize_to_tray", "Minimize to system tray when window is closed"),
            ("notify_on_done",   "Desktop notification when a download completes"),
            ("open_on_done",     "Automatically open file when download completes"),
            ("clipboard_watch",  "Watch clipboard and auto-fill detected URLs"),
        ]:
            cb=QCheckBox(label); cb.setChecked(SETTINGS[key])
            cb.stateChanged.connect(lambda v,k=key: self._toggle(k, bool(v)))
            lay.addWidget(cb)

        lay.addStretch()

        # Wire spinboxes
        self.spin_spd.valueChanged.connect(lambda v: self._set("max_speed_kb",v))
        self.spin_cc.valueChanged.connect(lambda v: self._set("max_concurrent",v))

    def _title(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(2)
        t=QLabel("Settings"); t.setObjectName("page_title")
        s=QLabel("Preferences are saved automatically"); s.setObjectName("page_subtitle")
        l.addWidget(t); l.addWidget(s); return w

    def _browse(self):
        d=QFileDialog.getExistingDirectory(self,"Choose download folder",SETTINGS["download_dir"])
        if d:
            SETTINGS["download_dir"]=d; self.lbl_dir.setText(d)
            save_settings(SETTINGS); self.changed.emit()

    def _toggle(self, key, val):
        SETTINGS[key]=val; save_settings(SETTINGS); self.changed.emit()

    def _set(self, key, val):
        SETTINGS[key]=val; save_settings(SETTINGS); self.changed.emit()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuantumDownloader")
        self.setMinimumSize(880,600); self.setGeometry(80,80,1100,740)
        self.setWindowIcon(get_icon("tray"))
        self._last_clip=""
        self._build_ui(); self._build_tray()
        # Timers
        self._clip_timer=QTimer(self); self._clip_timer.timeout.connect(self._check_clip)
        self._clip_timer.start(700)
        self._queue_timer=QTimer(self); self._queue_timer.timeout.connect(self._flush_queue)
        self._queue_timer.start(1500)
        self._speed_timer=QTimer(self); self._speed_timer.timeout.connect(self._update_speed)
        self._speed_timer.start(1000)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root=QWidget(self); root.setObjectName("root"); self.setCentralWidget(root)
        rl=QHBoxLayout(root); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)

        # Sidebar
        sb_frame=QFrame(); sb_frame.setObjectName("sidebar"); sb_frame.setFixedWidth(210)
        sb=QVBoxLayout(sb_frame); sb.setContentsMargins(12,20,12,20); sb.setSpacing(6)
        l1=QLabel("QUANTUM"); l1.setObjectName("app_logo_text")
        l2=QLabel("DOWNLOADER"); l2.setObjectName("app_logo_sub")
        sb.addWidget(l1); sb.addWidget(l2); sb.addSpacing(18)
        sb.addWidget(_divider()); sb.addSpacing(14)

        self.nav_active    = self._nav("activity","Active")
        self.nav_completed = self._nav("check","Completed")
        self.nav_settings  = self._nav("settings","Settings")
        self._navs=[self.nav_active, self.nav_completed, self.nav_settings]
        for btn in self._navs: btn.clicked.connect(self._on_nav); sb.addWidget(btn)
        self.nav_active.setChecked(True)

        sb.addSpacing(20); sb.addWidget(_divider()); sb.addSpacing(14)

        self.chip_a=_StatChip("0","ACTIVE")
        self.chip_c=_StatChip("0","COMPLETED")
        chips=QHBoxLayout(); chips.setSpacing(8)
        chips.addWidget(self.chip_a); chips.addWidget(self.chip_c)
        sb.addLayout(chips); sb.addSpacing(12)

        self.lbl_speed=QLabel("↓  0 KB/s")
        self.lbl_speed.setStyleSheet(
            f"font-size:9pt;font-weight:600;color:{T['accent']};"
            "padding:6px 10px;background:rgba(125,232,255,0.07);"
            "border-radius:8px;border:1px solid rgba(125,232,255,0.12);")
        sb.addWidget(self.lbl_speed); sb.addStretch()
        ver=QLabel("v3.1 — production")
        ver.setStyleSheet(f"font-size:7.5pt;color:{T['text_dim']};")
        sb.addWidget(ver)

        # Content
        content=QFrame(); content.setObjectName("content_bg")
        cl=QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)
        self.stack=AnimatedStack()
        cl.addWidget(self.stack)
        self._build_active_page()
        self._build_completed_page()
        sp=SettingsPage(); sp.changed.connect(lambda: None)  # settings live
        self.stack.addWidget(sp)

        rl.addWidget(sb_frame); rl.addWidget(content,1)

    def _nav(self, icon, label):
        btn=QPushButton(); btn.setProperty("class","nav_btn"); btn.setCheckable(True)
        btn.setIcon(get_icon(icon,18)); btn.setIconSize(QSize(18,18))
        btn.setText(f"  {label}"); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(44); return btn

    def _build_active_page(self):
        page=QWidget(); lay=QVBoxLayout(page)
        lay.setContentsMargins(28,26,28,20); lay.setSpacing(16)
        t=QLabel("Active Downloads"); t.setObjectName("page_title")
        s=QLabel("Real downloads · pause, resume, speed-limit, open when done")
        s.setObjectName("page_subtitle")
        lay.addWidget(t); lay.addWidget(s)

        # URL bar
        bar_frame=QFrame(); bar_frame.setObjectName("dl_card")
        bar_frame.setContentsMargins(14,10,14,10)
        bar_lay=QHBoxLayout(bar_frame); bar_lay.setSpacing(10)
        ic=QLabel(); ic.setPixmap(get_icon("link",18).pixmap(18,18))
        ic.setFixedSize(22,22); ic.setStyleSheet("background:transparent;")
        self.url_input=QLineEdit(); self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText(
            "Paste a URL here  ·  clipboard is watched automatically")
        self.url_input.returnPressed.connect(self._from_bar)
        self.btn_dl=QPushButton(get_icon("download",16),"  Download")
        self.btn_dl.setObjectName("btn_primary"); self.btn_dl.setIconSize(QSize(16,16))
        self.btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dl.setFixedHeight(38); self.btn_dl.clicked.connect(self._from_bar)
        bar_lay.addWidget(ic); bar_lay.addWidget(self.url_input,1); bar_lay.addWidget(self.btn_dl)
        lay.addWidget(bar_frame)

        self.active_list=CardList("Paste a URL above — clipboard is watched automatically")
        self.active_list.count_changed.connect(self._update_chips)
        lay.addWidget(self.active_list,1)
        self.stack.addWidget(page)

    def _build_completed_page(self):
        page=QWidget(); lay=QVBoxLayout(page)
        lay.setContentsMargins(28,26,28,20); lay.setSpacing(16)
        t=QLabel("Completed"); t.setObjectName("page_title")
        s=QLabel("Open or locate finished downloads"); s.setObjectName("page_subtitle")
        lay.addWidget(t); lay.addWidget(s)
        self.comp_list=CardList("No completed downloads yet")
        self.comp_list.count_changed.connect(self._update_chips)
        lay.addWidget(self.comp_list,1)
        self.stack.addWidget(page)

    # ── Tray ──────────────────────────────────────────────────────────────────
    def _build_tray(self):
        self._tray=None
        if not QSystemTrayIcon.isSystemTrayAvailable(): return
        self._tray=QSystemTrayIcon(get_icon("tray"),self)
        self._tray.setToolTip("QuantumDownloader")
        menu=QMenu()
        menu.addAction("Show", self._show_win)
        menu.addAction("Active", lambda: self._goto(0))
        menu.addSeparator()
        menu.addAction("Quit", QApplication.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(lambda r:
            (self._show_win() if self.isHidden() else self.hide())
            if r==QSystemTrayIcon.ActivationReason.Trigger else None)
        self._tray.show()

    def _show_win(self):
        self.show(); self.raise_(); self.activateWindow()

    def _goto(self, idx):
        self._show_win()
        for i,b in enumerate(self._navs): b.setChecked(i==idx)
        self.stack.slide_to(idx)

    def closeEvent(self, e):
        if SETTINGS.get("minimize_to_tray") and self._tray:
            e.ignore(); self.hide()
            self._tray.showMessage("QuantumDownloader",
                "Minimized to tray. Right-click the icon to quit.",
                QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            # Stop all active downloads before closing
            for c in list(self.active_list.cards()):
                if c.status in ("Downloading", "Paused"):
                    if c._worker:
                        c._worker.cancel()
                        c._worker = None
                    if c._thread:
                        c._thread.quit()
                        c._thread.wait(2000)
                        c._thread = None
            e.accept()

    # ── Download lifecycle ────────────────────────────────────────────────────
    def _from_bar(self):
        url=self.url_input.text().strip()
        if url: self._enqueue(url); self.url_input.clear()

    def _enqueue(self, url: str):
        if not url.startswith(("http://","https://","ftp://")):
            QMessageBox.warning(self,"Invalid URL",
                f"Not a recognisable HTTP/FTP URL:\n{url}"); return

        raw = url.split("?")[0].split("/")[-1]
        filename = raw if raw and "." in raw else f"download_{int(time.time())}"
        # Sanitize filename — remove path separators and illegal chars
        filename = "".join(c for c in filename if c.isprintable() and c not in '<>:"/\\|?*')
        filename = filename.strip(". ") or f"download_{int(time.time())}"

        dest = os.path.join(SETTINGS["download_dir"], filename)
        base,ext=os.path.splitext(dest); n=1
        while os.path.exists(dest): dest=f"{base} ({n}){ext}"; n+=1

        card=DownloadCard(filename, url, dest)
        card.open_requested.connect(lambda fp:
            QDesktopServices.openUrl(QUrl.fromLocalFile(fp)) if os.path.exists(fp) else None)
        card.finished.connect(lambda ok, fp, c=card: self._on_done(ok, fp, c))
        self.active_list.add_card(card)
        self._try_start(card)

    def _try_start(self, card: DownloadCard):
        running=sum(1 for c in self.active_list.cards() if c.status=="Downloading")
        if running < SETTINGS["max_concurrent"]:
            card.start(SETTINGS["max_speed_kb"])

    def _flush_queue(self):
        """Start Queued cards when slots free up."""
        running=sum(1 for c in self.active_list.cards() if c.status=="Downloading")
        slots=SETTINGS["max_concurrent"]-running
        for c in self.active_list.cards():
            if slots<=0: break
            if c.status=="Queued":
                c.start(SETTINGS["max_speed_kb"])
                slots-=1

    def _on_done(self, ok: bool, fp: str, card: DownloadCard):
        if not ok:
            card.setToolTip(fp or "Download failed")
            return
        # Notify
        if SETTINGS["notify_on_done"] and self._tray and ok:
            self._tray.showMessage("Download complete",
                card.lbl_name.text(), QSystemTrayIcon.MessageIcon.Information, 4000)
        # Open file
        if SETTINGS["open_on_done"] and fp and os.path.exists(fp):
            QDesktopServices.openUrl(QUrl.fromLocalFile(fp))
        # Move card to completed tab after a short pause
        QTimer.singleShot(1400, lambda: self._move_done(card))

    def _move_done(self, card: DownloadCard):
        if card not in self.active_list.cards(): return
        self.active_list.take(card)
        self.comp_list.add_card(card)
        self._update_chips()

    # ── Clipboard watcher ─────────────────────────────────────────────────────
    def _check_clip(self):
        if not SETTINGS.get("clipboard_watch"): return
        try:
            text=QApplication.clipboard().text().strip()
            if text==self._last_clip: return
            self._last_clip=text
            if (text.startswith(("http://","https://","ftp://"))
                    and "\n" not in text and len(text) < 2048
                    and not self.url_input.text()):
                self.url_input.setText(text)
        except Exception:
            pass

    # ── Nav ───────────────────────────────────────────────────────────────────
    def _on_nav(self):
        s=self.sender()
        for i,b in enumerate(self._navs):
            b.setChecked(b is s)
            if b is s: self.stack.slide_to(i)

    # ── Chips & speed label ───────────────────────────────────────────────────
    def _update_chips(self):
        self.chip_a.num.setText(str(len(self.active_list.cards())))
        self.chip_c.num.setText(str(len(self.comp_list.cards())))

    def _update_speed(self):
        total=0.0
        for c in self.active_list.cards():
            if c.status!="Downloading": continue
            total += c._speed_bps
        if total>=1024*1024*1024:
            self.lbl_speed.setText(f"↓  {total/1024/1024/1024:.2f} GB/s")
        elif total>=1024*1024:
            self.lbl_speed.setText(f"↓  {total/1024/1024:.1f} MB/s")
        elif total>=1024:
            self.lbl_speed.setText(f"↓  {total/1024:.0f} KB/s")
        elif total>0:
            self.lbl_speed.setText(f"↓  {total:.0f} B/s")
        else:
            self.lbl_speed.setText("↓  0 KB/s")

class _StatChip(QFrame):
    def __init__(self, n, lbl):
        super().__init__(); self.setObjectName("stat_chip")
        lay=QVBoxLayout(self); lay.setContentsMargins(12,10,12,10); lay.setSpacing(2)
        self.num=QLabel(n); self.num.setObjectName("stat_num")
        lb=QLabel(lbl); lb.setObjectName("stat_lbl")
        lay.addWidget(self.num); lay.addWidget(lb)

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app=QApplication(sys.argv)
    app.setApplicationName("QuantumDownloader")
    app.setStyleSheet(QSS)
    app.setQuitOnLastWindowClosed(False)   # stay alive in tray

    pal=QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(T['bg_base']))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(T['text_primary']))
    pal.setColor(QPalette.ColorRole.Base,            QColor(T['bg_card']))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(T['bg_panel']))
    pal.setColor(QPalette.ColorRole.Text,            QColor(T['text_primary']))
    pal.setColor(QPalette.ColorRole.Button,          QColor(T['bg_card']))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(T['text_primary']))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(T['accent']))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(T['bg_deep']))
    app.setPalette(pal)

    win=MainWindow()
    win.show()
    sys.exit(app.exec())
