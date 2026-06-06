"""
QuantumDownloader — Next-Gen Download Manager UI
Ultra-polished, cross-platform, production-grade PyQt6 application.

Aesthetic: Deep-space luxury dark theme with crystalline accents,
           fluid micro-animations, and a precision-engineered layout.

Requires: PyQt6
Install:  pip install PyQt6
Run:      python quantum_downloader.py
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QProgressBar,
    QListWidget, QListWidgetItem, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QSizePolicy, QScrollArea,
    QLineEdit, QSpacerItem, QGridLayout
)
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty,
    QStandardPaths, QTimer, QRect, QPoint, QRectF, pyqtSignal,
    QParallelAnimationGroup, QSequentialAnimationGroup, QPointF
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QLinearGradient,
    QRadialGradient, QFont, QFontMetrics, QPainterPath, QConicalGradient,
    QPalette
)

# ─────────────────────────────────────────────────────────────────────────────
# PURE QPAINTER ICONS  — zero SVG/base64, no file I/O, no warnings
# ─────────────────────────────────────────────────────────────────────────────

_C_ACCENT = "#7DE8FF"
_C_DARK   = "#0A0E1A"
_C_GREY   = "#8A8FA8"
_C_RED    = "#FF6B6B"

def _base_px(size: int):
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return px, p

def _pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen

def _icon_download(size: int, color: str = _C_ACCENT) -> QIcon:
    px, p = _base_px(size)
    s = size; m = s * 0.15; cx = s / 2.0
    p.setPen(_pen(color, s * 0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(m, s*0.78), QPointF(s-m, s*0.78))
    p.drawLine(QPointF(cx, m*0.8), QPointF(cx, s*0.60))
    path = QPainterPath()
    path.moveTo(cx - s*0.22, s*0.40)
    path.lineTo(cx,          s*0.63)
    path.lineTo(cx + s*0.22, s*0.40)
    p.drawPath(path)
    p.end(); return QIcon(px)

def _icon_check(size: int, color: str = _C_ACCENT) -> QIcon:
    px, p = _base_px(size)
    s = size
    p.setPen(_pen(color, s * 0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(s*0.14, s*0.50)
    path.lineTo(s*0.42, s*0.76)
    path.lineTo(s*0.86, s*0.24)
    p.drawPath(path)
    p.end(); return QIcon(px)

def _icon_settings(size: int, color: str = _C_ACCENT) -> QIcon:
    px, p = _base_px(size)
    s = size; pen = _pen(color, s * 0.08); dot_r = s * 0.09
    p.setPen(pen)
    for y_frac, x_frac in [(0.28, 0.35), (0.50, 0.63), (0.72, 0.40)]:
        y = s * y_frac; xd = s * x_frac
        p.drawLine(QPointF(s*0.12, y), QPointF(s*0.88, y))
        p.setBrush(QBrush(QColor(color))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(xd-dot_r, y-dot_r, dot_r*2, dot_r*2))
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(pen)
    p.end(); return QIcon(px)

def _icon_plus(size: int, color: str = _C_DARK) -> QIcon:
    px, p = _base_px(size)
    s = size; m = s*0.22; cx = s/2.0; cy = s/2.0
    p.setPen(_pen(color, s * 0.10)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(cx, m),  QPointF(cx, s-m))
    p.drawLine(QPointF(m, cy), QPointF(s-m, cy))
    p.end(); return QIcon(px)

def _icon_pause(size: int, color: str = _C_GREY) -> QIcon:
    px, p = _base_px(size)
    s = size; bw = s*0.22; gap = s*0.14; top = s*0.22; h = s*0.56
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(color)))
    p.drawRoundedRect(QRectF(s/2-gap/2-bw, top, bw, h), 2, 2)
    p.drawRoundedRect(QRectF(s/2+gap/2,    top, bw, h), 2, 2)
    p.end(); return QIcon(px)

def _icon_play(size: int, color: str = _C_GREY) -> QIcon:
    px, p = _base_px(size)
    s = size
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(color)))
    tri = QPainterPath()
    tri.moveTo(s*0.28, s*0.20); tri.lineTo(s*0.80, s*0.50)
    tri.lineTo(s*0.28, s*0.80); tri.closeSubpath()
    p.drawPath(tri)
    p.end(); return QIcon(px)

def _icon_trash(size: int, color: str = _C_RED) -> QIcon:
    px, p = _base_px(size)
    s = size; pen = _pen(color, s*0.08)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(s*0.15, s*0.30), QPointF(s*0.85, s*0.30))
    p.drawLine(QPointF(s*0.38, s*0.30), QPointF(s*0.38, s*0.20))
    p.drawLine(QPointF(s*0.62, s*0.30), QPointF(s*0.62, s*0.20))
    p.drawLine(QPointF(s*0.38, s*0.20), QPointF(s*0.62, s*0.20))
    body = QPainterPath()
    body.moveTo(s*0.25, s*0.32); body.lineTo(s*0.30, s*0.82)
    body.lineTo(s*0.70, s*0.82); body.lineTo(s*0.75, s*0.32)
    p.drawPath(body)
    p.drawLine(QPointF(s*0.44, s*0.42), QPointF(s*0.44, s*0.72))
    p.drawLine(QPointF(s*0.56, s*0.42), QPointF(s*0.56, s*0.72))
    p.end(); return QIcon(px)

def _icon_link(size: int, color: str = _C_DARK) -> QIcon:
    px, p = _base_px(size)
    s = size; r = s*0.18
    p.setPen(_pen(color, s*0.09)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(s*0.08, s*0.35, s*0.40, s*0.30), r, r)
    p.drawRoundedRect(QRectF(s*0.52, s*0.35, s*0.40, s*0.30), r, r)
    p.drawLine(QPointF(s*0.42, s*0.50), QPointF(s*0.58, s*0.50))
    p.end(); return QIcon(px)

def _icon_activity(size: int, color: str = _C_ACCENT) -> QIcon:
    px, p = _base_px(size)
    s = size
    p.setPen(_pen(color, s*0.08))
    pts = [QPointF(s*0.05,s*0.50), QPointF(s*0.25,s*0.50),
           QPointF(s*0.38,s*0.20), QPointF(s*0.52,s*0.80),
           QPointF(s*0.65,s*0.50), QPointF(s*0.95,s*0.50)]
    for i in range(len(pts)-1):
        p.drawLine(pts[i], pts[i+1])
    p.end(); return QIcon(px)

_ICON_MAP = {
    "download": _icon_download,
    "check":    _icon_check,
    "settings": _icon_settings,
    "plus":     lambda s: _icon_plus(s, _C_DARK),
    "pause":    _icon_pause,
    "play":     _icon_play,
    "trash":    _icon_trash,
    "link":     lambda s: _icon_link(s, _C_DARK),
    "folder":   _icon_activity,
    "activity": _icon_activity,
}

def get_icon(name: str, size: int = 24) -> QIcon:
    fn = _ICON_MAP.get(name)
    if fn:
        return fn(size)
    px = QPixmap(size, size); px.fill(Qt.GlobalColor.transparent)
    return QIcon(px)

def make_shadow(blur: int = 24, color: str = "#00C8FF", alpha: int = 80,
                offset_y: int = 4) -> QGraphicsDropShadowEffect:
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    c = QColor(color)
    c.setAlpha(alpha)
    s.setColor(c)
    s.setOffset(0, offset_y)
    return s

# ─────────────────────────────────────────────────────────────────────────────
# THEME  (single source of truth)
# ─────────────────────────────────────────────────────────────────────────────
T = {
    "bg_deep":      "#07090F",
    "bg_base":      "#0A0E1A",
    "bg_panel":     "#0D1120",
    "bg_card":      "#111827",
    "bg_card2":     "#151D2E",
    "border":       "#1E2D45",
    "border_glow":  "#7DE8FF",
    "accent":       "#7DE8FF",
    "accent2":      "#5B6EFF",
    "accent3":      "#A259FF",
    "success":      "#3DFFA0",
    "warning":      "#FFB547",
    "danger":       "#FF6B6B",
    "text_primary": "#EDF2FF",
    "text_sec":     "#8A8FA8",
    "text_dim":     "#3D4460",
    "white":        "#FFFFFF",
}

QSS = f"""
/* ── Reset ── */
* {{
    border: none;
    outline: none;
    font-family: 'Segoe UI Variable', 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 10pt;
    color: {T['text_primary']};
}}

/* ── Root ── */
QMainWindow, QWidget#root {{
    background-color: {T['bg_base']};
}}

/* ── Sidebar ── */
QFrame#sidebar {{
    background-color: {T['bg_panel']};
    border-right: 1px solid {T['border']};
}}

QLabel#app_logo_text {{
    font-size: 15pt;
    font-weight: 800;
    letter-spacing: 1px;
    color: {T['accent']};
    padding: 0 4px;
}}

QLabel#app_logo_sub {{
    font-size: 7.5pt;
    color: {T['text_dim']};
    letter-spacing: 3px;
    padding: 0 5px;
}}

/* Nav buttons */
QPushButton.nav_btn {{
    background-color: transparent;
    text-align: left;
    padding: 11px 14px;
    border-radius: 10px;
    font-size: 10pt;
    font-weight: 600;
    color: {T['text_sec']};
    border-left: 3px solid transparent;
}}
QPushButton.nav_btn:hover {{
    background-color: rgba(125, 232, 255, 0.06);
    color: {T['text_primary']};
}}
QPushButton.nav_btn:checked {{
    background-color: rgba(125, 232, 255, 0.10);
    color: {T['accent']};
    border-left: 3px solid {T['accent']};
}}

/* Stat chips in sidebar */
QFrame#stat_chip {{
    background-color: {T['bg_card']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: 4px 8px;
}}
QLabel#stat_num {{
    font-size: 18pt;
    font-weight: 700;
    color: {T['accent']};
}}
QLabel#stat_lbl {{
    font-size: 8pt;
    color: {T['text_sec']};
    letter-spacing: 1px;
}}

/* ── Content / Pages ── */
QFrame#content_bg {{
    background-color: {T['bg_base']};
}}

/* Page titles */
QLabel#page_title {{
    font-size: 20pt;
    font-weight: 800;
    color: {T['text_primary']};
    letter-spacing: -0.5px;
}}
QLabel#page_subtitle {{
    font-size: 9pt;
    color: {T['text_sec']};
    letter-spacing: 0.5px;
}}

/* Primary CTA */
QPushButton#btn_primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {T['accent']}, stop:1 {T['accent2']});
    color: {T['bg_deep']};
    font-weight: 700;
    font-size: 9.5pt;
    letter-spacing: 0.4px;
    padding: 9px 20px;
    border-radius: 10px;
}}
QPushButton#btn_primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #9AEFFF, stop:1 #7B8EFF);
}}
QPushButton#btn_primary:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5BC8E0, stop:1 #4050DD);
}}

/* URL input */
QLineEdit#url_input {{
    background-color: {T['bg_card']};
    border: 1.5px solid {T['border']};
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 10pt;
    color: {T['text_primary']};
    selection-background-color: {T['accent2']};
}}
QLineEdit#url_input:focus {{
    border: 1.5px solid {T['accent']};
    background-color: {T['bg_card2']};
}}
QLineEdit#url_input::placeholder {{
    color: {T['text_dim']};
}}

/* ── Download Cards ── */
QFrame#dl_card {{
    background-color: {T['bg_card']};
    border: 1px solid {T['border']};
    border-radius: 14px;
}}
QFrame#dl_card:hover {{
    border: 1px solid rgba(125,232,255,0.25);
    background-color: {T['bg_card2']};
}}

QLabel#dl_filename {{
    font-weight: 700;
    font-size: 10.5pt;
    color: {T['text_primary']};
}}
QLabel#dl_url {{
    font-size: 8.5pt;
    color: {T['text_dim']};
}}
QLabel.dl_info {{
    font-size: 8.5pt;
    color: {T['text_sec']};
}}
QLabel#dl_speed {{
    font-size: 9pt;
    font-weight: 600;
    color: {T['accent']};
}}
QLabel#dl_percent {{
    font-size: 13pt;
    font-weight: 800;
    color: {T['accent']};
}}

/* Progress bar */
QProgressBar#dl_progress {{
    background-color: rgba(255,255,255,0.04);
    border-radius: 5px;
    border: none;
    max-height: 6px;
    text-align: center;
}}
QProgressBar#dl_progress::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {T['accent']}, stop:1 {T['accent2']});
    border-radius: 5px;
}}

/* Action icon buttons */
QPushButton.icon_btn {{
    background-color: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 6px;
    border: 1px solid {T['border']};
}}
QPushButton.icon_btn:hover {{
    background-color: rgba(125,232,255,0.12);
    border: 1px solid {T['accent']};
}}

/* Status badge */
QLabel.badge_downloading {{
    background-color: rgba(125,232,255,0.12);
    color: {T['accent']};
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QLabel.badge_paused {{
    background-color: rgba(255,181,71,0.12);
    color: {T['warning']};
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 8pt;
    font-weight: 700;
}}
QLabel.badge_queued {{
    background-color: rgba(138,143,168,0.12);
    color: {T['text_sec']};
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 8pt;
    font-weight: 700;
}}
QLabel.badge_done {{
    background-color: rgba(61,255,160,0.12);
    color: {T['success']};
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 8pt;
    font-weight: 700;
}}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {T['border']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {T['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    border: none; background: transparent; height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {T['border']}; border-radius: 3px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {T['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── QListWidget base ── */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    background: transparent;
    padding: 0;
    border: none;
}}
QListWidget::item:selected {{
    background: transparent;
}}

/* ── Settings labels ── */
QLabel#settings_section {{
    font-size: 9pt;
    font-weight: 700;
    color: {T['text_dim']};
    letter-spacing: 1.5px;
}}
QLabel#settings_key {{
    font-size: 10pt;
    color: {T['text_primary']};
    font-weight: 600;
}}
QLabel#settings_val {{
    font-size: 9.5pt;
    color: {T['text_sec']};
}}
QFrame#settings_row {{
    background-color: {T['bg_card']};
    border: 1px solid {T['border']};
    border-radius: 10px;
}}

/* Divider */
QFrame#h_divider {{
    background-color: {T['border']};
    max-height: 1px;
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# ANIMATED STACKED WIDGET  (fixed signal leak + proper effect)
# ─────────────────────────────────────────────────────────────────────────────
class AnimatedStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._pending = None

    def slide_to(self, index: int):
        if index == self.currentIndex():
            return
        self._pending = index
        self._anim.stop()
        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        self._anim.setDuration(160)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._swap)
        self._anim.start()

    def _swap(self):
        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        if self._pending is not None:
            self.setCurrentIndex(self._pending)
            self._pending = None
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

# ─────────────────────────────────────────────────────────────────────────────
# CRYSTAL PROGRESS BAR  (custom-painted glow variant)
# ─────────────────────────────────────────────────────────────────────────────
class GlowProgressBar(QWidget):
    """A progress bar that paints a gradient fill with a glow tip."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.setFixedHeight(6)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setValue(self, v: int):
        self._value = max(0, min(100, v))
        self.update()

    def value(self) -> int:
        return self._value

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        h = r.height()
        radius = h / 2

        # Track
        p.setBrush(QBrush(QColor(255, 255, 255, 10)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, radius, radius)

        if self._value > 0:
            fill_w = max(int(r.width() * self._value / 100), int(radius * 2))
            fill_r = QRect(r.x(), r.y(), fill_w, h)

            # Gradient fill
            grad = QLinearGradient(fill_r.left(), 0, fill_r.right(), 0)
            grad.setColorAt(0, QColor(T['accent2']))
            grad.setColorAt(1, QColor(T['accent']))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(fill_r, radius, radius)

            # Glow dot at tip — QRadialGradient requires QPointF (not QPoint)
            glow_x = float(fill_r.right() - 3)
            glow_y = float(r.center().y())
            rg = QRadialGradient(glow_x, glow_y, 8.0)
            tip_solid = QColor(T['accent'])
            tip_trans = QColor(T['accent'])
            tip_trans.setAlpha(0)
            rg.setColorAt(0.0, tip_solid)
            rg.setColorAt(1.0, tip_trans)
            p.setBrush(QBrush(rg))
            p.drawEllipse(QRectF(glow_x - 8, glow_y - 8, 16, 16))

        p.end()

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD CARD WIDGET
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_URLS = [
    "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso",
    "https://storage.googleapis.com/chrome-for-testing-public/stable/win64/chrome-win64.zip",
    "https://download.blender.org/release/Blender4.0/blender-4.0.2-windows-x64.msi",
    "https://github.com/microsoft/vscode/releases/download/1.85.0/VSCode-win32-x64-1.85.0.zip",
    "https://download.jetbrains.com/python/pycharm-professional-2023.3.2.exe",
]
_card_counter = [0]

class DownloadCard(QFrame):
    remove_requested = pyqtSignal(object)

    STATUS_STYLES = {
        "Downloading": "badge_downloading",
        "Paused":      "badge_paused",
        "Queued":      "badge_queued",
        "Completed":   "badge_done",
    }

    def __init__(self, filename: str, url: str = "", status: str = "Queued"):
        super().__init__()
        _card_counter[0] += 1
        self.setObjectName("dl_card")
        self.setContentsMargins(16, 14, 16, 14)
        self._status = status
        self._paused = False

        outer = QVBoxLayout(self)
        outer.setSpacing(10)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Row 1: icon column + main info + percent ──────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        # File-type colour chip
        chip = QFrame()
        chip.setFixedSize(42, 42)
        chip.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {T['accent2']},stop:1 {T['accent3']});"
            f"border-radius:10px;"
        )
        ext_lbl = QLabel(filename.rsplit(".", 1)[-1].upper()[:4] if "." in filename else "FILE")
        ext_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ext_lbl.setStyleSheet(
            "font-size:7.5pt; font-weight:800; color:#FFF; letter-spacing:0.5px;"
            "background:transparent;"
        )
        chip_layout = QVBoxLayout(chip)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.addWidget(ext_lbl)

        # Centre info
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        self.lbl_name = QLabel(filename)
        self.lbl_name.setObjectName("dl_filename")
        self.lbl_name.setWordWrap(True)

        self.lbl_url = QLabel(url if url else "—")
        self.lbl_url.setObjectName("dl_url")
        self.lbl_url.setWordWrap(False)
        self.lbl_url.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        info_col.addWidget(self.lbl_name)
        info_col.addWidget(self.lbl_url)

        # Percent label (right-aligned)
        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setObjectName("dl_percent")
        self.lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_pct.setFixedWidth(52)

        row1.addWidget(chip)
        row1.addLayout(info_col, 1)
        row1.addWidget(self.lbl_pct)

        # ── Progress bar ──────────────────────────────────────────────────────
        self.progress = GlowProgressBar()

        # ── Row 2: stats + status badge + actions ─────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.lbl_size = QLabel("—  /  —")
        self.lbl_size.setProperty("class", "dl_info")
        self.lbl_size.setStyleSheet(f"color:{T['text_sec']}; font-size:8.5pt;")

        self.lbl_speed = QLabel("—")
        self.lbl_speed.setObjectName("dl_speed")

        sep1 = QLabel("·")
        sep1.setStyleSheet(f"color:{T['text_dim']};")
        self.lbl_eta = QLabel("ETA —")
        self.lbl_eta.setStyleSheet(f"color:{T['text_sec']}; font-size:8.5pt;")

        row2.addWidget(self.lbl_size)
        row2.addWidget(sep1)
        row2.addWidget(self.lbl_speed)
        row2.addWidget(sep1)
        row2.addWidget(self.lbl_eta)
        row2.addStretch()

        # Status badge
        self.badge = QLabel(status.upper())
        self.badge.setProperty("class", self.STATUS_STYLES.get(status, "badge_queued"))
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_badge(status)

        # Action buttons
        self.btn_pause = QPushButton()
        self.btn_pause.setIcon(get_icon("pause", 16))
        self.btn_pause.setProperty("class", "icon_btn")
        self.btn_pause.setFixedSize(32, 32)
        self.btn_pause.setIconSize(QSize(16, 16))
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setToolTip("Pause / Resume")
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_cancel = QPushButton()
        self.btn_cancel.setIcon(get_icon("trash", 16))
        self.btn_cancel.setProperty("class", "icon_btn")
        self.btn_cancel.setFixedSize(32, 32)
        self.btn_cancel.setIconSize(QSize(16, 16))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setToolTip("Remove download")
        self.btn_cancel.clicked.connect(lambda: self.remove_requested.emit(self))

        row2.addWidget(self.badge)
        row2.addWidget(self.btn_pause)
        row2.addWidget(self.btn_cancel)

        outer.addLayout(row1)
        outer.addWidget(self.progress)
        outer.addLayout(row2)

    def _apply_badge(self, status: str):
        styles = {
            "Downloading": f"background:rgba(125,232,255,0.12);color:{T['accent']};",
            "Paused":      f"background:rgba(255,181,71,0.12);color:{T['warning']};",
            "Queued":      f"background:rgba(138,143,168,0.10);color:{T['text_sec']};",
            "Completed":   f"background:rgba(61,255,160,0.12);color:{T['success']};",
        }
        base = "border-radius:6px;padding:2px 10px;font-size:8pt;font-weight:700;letter-spacing:0.5px;"
        self.badge.setStyleSheet(styles.get(status, styles["Queued"]) + base)
        self.badge.setText(status.upper())

    def _toggle_pause(self):
        self._paused = not self._paused
        new_status = "Paused" if self._paused else "Downloading"
        self.set_status(new_status)
        self.btn_pause.setIcon(get_icon("play" if self._paused else "pause", 16))

    def set_status(self, status: str):
        self._status = status
        self._apply_badge(status)

    def update_progress(self, pct: float, size: str, speed: str, eta: str):
        self.progress.setValue(int(pct))
        self.lbl_pct.setText(f"{int(pct)}%")
        self.lbl_size.setText(size)
        self.lbl_speed.setText(speed)
        self.lbl_eta.setText(f"ETA {eta}")

    def enterEvent(self, event):
        shadow = make_shadow(32, T['accent'], 40, 6)
        self.setGraphicsEffect(shadow)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setGraphicsEffect(None)
        super().leaveEvent(event)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAV BUTTON
# ─────────────────────────────────────────────────────────────────────────────
class NavButton(QPushButton):
    def __init__(self, icon_name: str, label: str):
        super().__init__()
        self.setProperty("class", "nav_btn")
        self.setCheckable(True)
        self.setIcon(get_icon(icon_name, 18))
        self.setIconSize(QSize(18, 18))
        self.setText(f"  {label}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(44)

# ─────────────────────────────────────────────────────────────────────────────
# STAT CHIP  (sidebar KPI)
# ─────────────────────────────────────────────────────────────────────────────
class StatChip(QFrame):
    def __init__(self, number: str, label: str):
        super().__init__()
        self.setObjectName("stat_chip")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        n = QLabel(number)
        n.setObjectName("stat_num")
        l = QLabel(label)
        l.setObjectName("stat_lbl")

        layout.addWidget(n)
        layout.addWidget(l)

        self.num_label = n

# ─────────────────────────────────────────────────────────────────────────────
# ADD URL BAR  (top of active page)
# ─────────────────────────────────────────────────────────────────────────────
class AddUrlBar(QFrame):
    download_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("dl_card")
        self.setContentsMargins(14, 10, 14, 10)

        lay = QHBoxLayout(self)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("link", 18).pixmap(18, 18))
        icon_lbl.setFixedSize(22, 22)
        icon_lbl.setStyleSheet("background:transparent;")

        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText("Paste a download URL here…")
        self.url_input.returnPressed.connect(self._emit)

        self.btn = QPushButton(get_icon("download", 16), "  Download")
        self.btn.setObjectName("btn_primary")
        self.btn.setIconSize(QSize(16, 16))
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setFixedHeight(38)
        self.btn.clicked.connect(self._emit)

        lay.addWidget(icon_lbl)
        lay.addWidget(self.url_input, 1)
        lay.addWidget(self.btn)

    def _emit(self):
        url = self.url_input.text().strip()
        if url:
            self.download_requested.emit(url)
            self.url_input.clear()

# ─────────────────────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────────────────────
class EmptyState(QWidget):
    def __init__(self, message: str = "Nothing here yet"):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)

        icon_lbl = QLabel("↓")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size:40pt; color:{T['text_dim']}; background:transparent;"
        )
        msg_lbl = QLabel(message)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet(f"font-size:11pt; color:{T['text_dim']}; background:transparent;")

        lay.addWidget(icon_lbl)
        lay.addWidget(msg_lbl)

# ─────────────────────────────────────────────────────────────────────────────
# SCROLLABLE CARD LIST
# ─────────────────────────────────────────────────────────────────────────────
class CardList(QScrollArea):
    """A scroll area that holds DownloadCard widgets vertically."""
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setStyleSheet("background:transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 8, 0)
        self._layout.setSpacing(10)
        self._layout.addStretch()

        self.setWidget(self._container)
        self._cards: list[DownloadCard] = []

        self._empty = EmptyState("Paste a URL above to start downloading")
        self._layout.insertWidget(0, self._empty)

    def add_card(self, card: DownloadCard):
        if card not in self._cards:
            self._cards.append(card)
            # insert before the stretch
            idx = self._layout.count() - 1
            if self._empty.isVisible():
                self._layout.removeWidget(self._empty)
                self._empty.hide()
            self._layout.insertWidget(idx, card)
            card.remove_requested.connect(self._remove_card)

            # Slide-in animation
            eff = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", card)
            anim.setDuration(300)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _remove_card(self, card: DownloadCard):
        if card in self._cards:
            self._cards.remove(card)
            self._layout.removeWidget(card)
            card.deleteLater()
            if not self._cards:
                self._layout.insertWidget(0, self._empty)
                self._empty.show()

    def cards(self):
        return list(self._cards)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def make_divider():
    d = QFrame()
    d.setObjectName("h_divider")
    d.setFixedHeight(1)
    return d

def make_page_header(title: str, subtitle: str = "") -> QVBoxLayout:
    lay = QVBoxLayout()
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("page_title")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("page_subtitle")
        lay.addWidget(s)
    return lay

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS ROWS
# ─────────────────────────────────────────────────────────────────────────────
def settings_row(key: str, value: str) -> QFrame:
    f = QFrame()
    f.setObjectName("settings_row")
    f.setContentsMargins(16, 12, 16, 12)
    lay = QHBoxLayout(f)
    lay.setContentsMargins(0, 0, 0, 0)
    k = QLabel(key);   k.setObjectName("settings_key")
    v = QLabel(value); v.setObjectName("settings_val")
    v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    v.setWordWrap(True)
    lay.addWidget(k, 1)
    lay.addWidget(v, 2)
    return f

# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuantumDownloader")
        self.setMinimumSize(880, 600)
        self.setGeometry(80, 80, 1100, 740)
        self.setWindowIcon(get_icon("download"))

        # ── Root ──────────────────────────────────────────────────────────────
        root = QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 20, 12, 20)
        sb_lay.setSpacing(6)

        # Logo
        logo_text = QLabel("QUANTUM")
        logo_text.setObjectName("app_logo_text")
        logo_sub = QLabel("DOWNLOADER")
        logo_sub.setObjectName("app_logo_sub")
        sb_lay.addWidget(logo_text)
        sb_lay.addWidget(logo_sub)
        sb_lay.addSpacing(18)
        sb_lay.addWidget(make_divider())
        sb_lay.addSpacing(14)

        # Nav
        self.nav_active    = NavButton("activity", "Active")
        self.nav_completed = NavButton("check",    "Completed")
        self.nav_settings  = NavButton("settings", "Settings")
        self._nav_buttons  = [self.nav_active, self.nav_completed, self.nav_settings]

        for btn in self._nav_buttons:
            btn.clicked.connect(self._on_nav)
            sb_lay.addWidget(btn)
        self.nav_active.setChecked(True)

        sb_lay.addSpacing(20)
        sb_lay.addWidget(make_divider())
        sb_lay.addSpacing(14)

        # KPI chips
        self.chip_active    = StatChip("0", "ACTIVE")
        self.chip_completed = StatChip("0", "COMPLETED")
        chips_lay = QHBoxLayout()
        chips_lay.setSpacing(8)
        chips_lay.addWidget(self.chip_active)
        chips_lay.addWidget(self.chip_completed)
        sb_lay.addLayout(chips_lay)

        sb_lay.addSpacing(14)
        self.lbl_speed_total = QLabel("↓  0 KB/s")
        self.lbl_speed_total.setStyleSheet(
            f"font-size:9pt; font-weight:600; color:{T['accent']};"
            "padding:6px 10px; background:rgba(125,232,255,0.07);"
            "border-radius:8px; border:1px solid rgba(125,232,255,0.12);"
        )
        sb_lay.addWidget(self.lbl_speed_total)

        sb_lay.addStretch()

        ver = QLabel("v3.0.0 — next-gen")
        ver.setStyleSheet(f"font-size:7.5pt; color:{T['text_dim']};")
        sb_lay.addWidget(ver)

        # ── Content ───────────────────────────────────────────────────────────
        content_bg = QFrame()
        content_bg.setObjectName("content_bg")
        content_lay = QVBoxLayout(content_bg)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        self.stack = AnimatedStack()
        content_lay.addWidget(self.stack)

        self._build_active_page()
        self._build_completed_page()
        self._build_settings_page()

        root_lay.addWidget(sidebar)
        root_lay.addWidget(content_bg, 1)

        # ── Demo ticker ───────────────────────────────────────────────────────
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._demo_tick)
        self._timer.start(800)

        # Seed a few demo downloads
        self._seed_demo()

    # ── Page builders ─────────────────────────────────────────────────────────
    def _build_active_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 26, 28, 20)
        lay.setSpacing(16)

        hdr = make_page_header("Active Downloads", "Manage and monitor your queue")
        lay.addLayout(hdr)

        self.url_bar = AddUrlBar()
        self.url_bar.download_requested.connect(self._add_download_from_url)
        lay.addWidget(self.url_bar)

        self.active_list = CardList()
        lay.addWidget(self.active_list, 1)

        self.stack.addWidget(page)

    def _build_completed_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 26, 28, 20)
        lay.setSpacing(16)

        hdr = make_page_header("Completed", "Your finished downloads")
        lay.addLayout(hdr)

        self.completed_list = CardList()
        self.completed_list._empty = EmptyState("No completed downloads yet")
        lay.addWidget(self.completed_list, 1)

        self.stack.addWidget(page)

    def _build_settings_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 26, 28, 20)
        lay.setSpacing(20)

        hdr = make_page_header("Settings", "Application preferences")
        lay.addLayout(hdr)

        dl_path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation)
        ver_info = f"Python {sys.version.split()[0]}  ·  PyQt6"

        # General section
        sec_lbl = QLabel("GENERAL")
        sec_lbl.setObjectName("settings_section")
        lay.addWidget(sec_lbl)

        for k, v in [
            ("Default download folder",  dl_path),
            ("Max simultaneous downloads", "4"),
            ("Auto-start on launch",       "Enabled"),
            ("System tray integration",    "Enabled"),
        ]:
            lay.addWidget(settings_row(k, v))

        lay.addSpacing(6)
        sec_lbl2 = QLabel("ABOUT")
        sec_lbl2.setObjectName("settings_section")
        lay.addWidget(sec_lbl2)

        for k, v in [
            ("Version",    "3.0.0 — next-gen"),
            ("Runtime",    ver_info),
            ("Platform",   sys.platform.title()),
            ("Build date", "April 2026"),
        ]:
            lay.addWidget(settings_row(k, v))

        lay.addStretch()
        self.stack.addWidget(page)

    # ── Nav ───────────────────────────────────────────────────────────────────
    def _on_nav(self):
        sender = self.sender()
        for btn in self._nav_buttons:
            btn.setChecked(btn is sender)
        idx = self._nav_buttons.index(sender)
        self.stack.slide_to(idx)

    # ── Download management ───────────────────────────────────────────────────
    def _add_download_from_url(self, url: str):
        filename = url.split("/")[-1] or "download"
        card = DownloadCard(filename, url, "Queued")
        self.active_list.add_card(card)
        self._update_chips()

    def _add_dummy(self, filename: str, url: str, pct: float,
                   size: str, speed: str, eta: str, status: str = "Downloading"):
        card = DownloadCard(filename, url, status)
        card.update_progress(pct, size, speed, eta)
        self.active_list.add_card(card)
        self._update_chips()
        return card

    def _seed_demo(self):
        data = [
            ("ubuntu-22.04.3-desktop-amd64.iso",
             SAMPLE_URLS[0], 62, "3.86 GB / 4.7 GB", "12.4 MB/s", "01:08"),
            ("chrome-win64.zip",
             SAMPLE_URLS[1], 28, "28.6 MB / 102 MB", "3.2 MB/s", "00:23"),
            ("blender-4.0.2-windows-x64.msi",
             SAMPLE_URLS[2],  0, "—  /  —", "—", "—:—", "Queued"),
        ]
        for d in data:
            self._add_dummy(*d)

    def _update_chips(self):
        active = len(self.active_list.cards())
        completed = len(self.completed_list.cards())
        self.chip_active.num_label.setText(str(active))
        self.chip_completed.num_label.setText(str(completed))

    # ── Demo animation tick ───────────────────────────────────────────────────
    def _demo_tick(self):
        self._tick += 1
        total_speed = 0.0
        for card in self.active_list.cards():
            if card._paused or card._status != "Downloading":
                continue
            pct = card.progress.value()
            if pct < 100:
                inc = 0.4 + (hash(card.lbl_name.text()) % 10) * 0.08
                new_pct = min(pct + inc, 100)
                speed_mb = 2.0 + (hash(card.lbl_name.text()) % 20) * 0.5
                total_speed += speed_mb
                total_mb = 500 + (hash(card.lbl_name.text()) % 4000)
                done_mb = total_mb * new_pct / 100
                rem_mb = total_mb - done_mb
                eta_s = int(rem_mb / speed_mb) if speed_mb > 0 else 0
                eta_str = f"{eta_s//60:02d}:{eta_s%60:02d}"

                if done_mb < 1000:
                    size_str = f"{done_mb:.1f} MB / {total_mb:.0f} MB"
                else:
                    size_str = f"{done_mb/1024:.2f} GB / {total_mb/1024:.2f} GB"

                card.update_progress(new_pct, size_str, f"{speed_mb:.1f} MB/s", eta_str)
                if new_pct >= 100:
                    card.set_status("Completed")

        if total_speed >= 1024:
            self.lbl_speed_total.setText(f"↓  {total_speed/1024:.2f} GB/s")
        elif total_speed > 0:
            self.lbl_speed_total.setText(f"↓  {total_speed:.1f} MB/s")
        else:
            self.lbl_speed_total.setText("↓  0 KB/s")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)

    # Force the palette to dark so native widgets (scroll bars, etc.) match
    pal = QPalette()
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

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
