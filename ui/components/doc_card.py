"""
doc_card.py - Card compacto que representa um documento digitalizado na tela unificada.
Mostra thumbnail (240x320), tipo do documento e status de validação.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QImage, QPainter, QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PIL import Image
import io

from ui.qt_styles import COLORS
from core.doc_validator import get_doc_type_label, get_status_label


class HoverButton(QPushButton):
    """Botão hover circular flutuante."""
    def __init__(self, text, text_color, font_size, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self._text = text
        self._text_color = QColor(text_color)
        self._font_size = font_size
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        bg_alpha = 216 if self._hovered else 165
        painter.setBrush(QColor(0, 0, 0, bg_alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        r = self.rect()
        painter.drawEllipse(r)
        painter.setPen(self._text_color)
        font = painter.font()
        font.setPixelSize(self._font_size)
        font.setBold(True)
        painter.setFont(font)
        if self._text in ("↺", "↻"):
            r.translate(0, -2)
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, self._text)


def _pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Converte PIL.Image para QPixmap."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)


# ── Status colors ────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "valid": "#66BB6A",
    "pending": "#FFB74D",
    "invalid": "#EF5350",
}

STATUS_BG_COLORS = {
    "valid": "#0A2210",
    "pending": "#2A1F0D",
    "invalid": "#2A0D0D",
}


class DocCard(QFrame):
    """Card visual compacto que representa um documento digitalizado."""

    THUMB_WIDTH = 240
    THUMB_HEIGHT = 320

    delete_requested = Signal(int)
    rotate_left_requested = Signal(int)
    rotate_right_requested = Signal(int)
    inspect_requested = Signal(int)

    def __init__(self, doc_index: int, pil_image: Image.Image,
                 doc_type: str = "DESCONHECIDO", status: str = "pending", parent=None):
        super().__init__(parent)
        self.doc_index = doc_index

        self.setObjectName("doc_card")
        self.setFixedSize(self.THUMB_WIDTH + 24, self.THUMB_HEIGHT + 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#doc_card {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # ── Thumbnail ────────────────────────────────────────
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedSize(self.THUMB_WIDTH, self.THUMB_HEIGHT)
        self.thumb_label.setStyleSheet("background-color: #ffffff; border-radius: 6px;")
        layout.addWidget(self.thumb_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Tipo do documento ────────────────────────────────
        self.type_label = QLabel(doc_type)
        self.type_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.type_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_label.setWordWrap(True)
        layout.addWidget(self.type_label)

        # ── Status badge ─────────────────────────────────────
        self.status_btn = QPushButton(status) # Placeholder se get_status_label falhar
        try:
            self.status_btn.setText(get_status_label(status))
        except: pass
        
        self.status_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_btn.setFixedHeight(26)
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_btn.clicked.connect(lambda: self.inspect_requested.emit(self.doc_index))
        self._apply_status_style(status)
        layout.addWidget(self.status_btn)

        # ── Botões hover ─────────────────────────────────────
        self.btn_delete = HoverButton("✕", "#ff1744", 16, self)
        self.btn_delete.setToolTip("Excluir Documento")
        self.btn_delete.hide()
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.doc_index))

        self.btn_rotate_left = HoverButton("↺", "#40c4ff", 20, self)
        self.btn_rotate_left.setToolTip("Girar Esquerda")
        self.btn_rotate_left.hide()
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_left_requested.emit(self.doc_index))

        self.btn_rotate_right = HoverButton("↻", "#40c4ff", 20, self)
        self.btn_rotate_right.setToolTip("Girar Direita")
        self.btn_rotate_right.hide()
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_right_requested.emit(self.doc_index))

        # Posicionamento dos botões flutuantes
        self.btn_delete.move(self.width() - 36, 4)
        self.btn_rotate_left.move(8, self.THUMB_HEIGHT - 24)
        self.btn_rotate_right.move(self.THUMB_WIDTH - 8, self.THUMB_HEIGHT - 24)

        # Carregar imagem
        self._set_thumbnail(pil_image)

    def _set_thumbnail(self, pil_img: Image.Image):
        if pil_img is None:
            return
        try:
            pixmap = _pil_to_qpixmap(pil_img)
            if pixmap.isNull():
                return
            scaled = pixmap.scaled(
                self.THUMB_WIDTH - 8, self.THUMB_HEIGHT - 8,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.thumb_label.setPixmap(scaled)
        except Exception as e:
            print(f"Erro ao gerar thumbnail no DocCard: {e}")

    def update_thumbnail(self, pil_img: Image.Image):
        self._set_thumbnail(pil_img)

    def update_type(self, doc_type: str):
        self.type_label.setText(get_doc_type_label(doc_type))

    def update_status(self, status: str):
        self.status_btn.setText(get_status_label(status))
        self._apply_status_style(status)

    def _apply_status_style(self, status: str):
        color = STATUS_COLORS.get(status, STATUS_COLORS["pending"])
        bg = STATUS_BG_COLORS.get(status, STATUS_BG_COLORS["pending"])
        self.status_btn.setStyleSheet(
            f"background-color: {bg}; color: {color}; border: 1px solid {color}; "
            f"border-radius: 6px; padding: 2px 8px;"
        )

    # ── Overlay IA ────────────────────────────────────────────
    def show_ai_overlay(self):
        self.ai_overlay = QFrame(self.thumb_label)
        self.ai_overlay.setGeometry(self.thumb_label.rect())
        self.ai_overlay.setStyleSheet(
            "background-color: rgba(10, 22, 40, 190); border-radius: 6px;"
        )
        
        overlay_layout = QVBoxLayout(self.ai_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.ai_text = QLabel("🤖 IA Analisando...")
        self.ai_text.setStyleSheet("color: #4FC3F7; font-size: 14px; font-weight: bold; background: transparent;")
        overlay_layout.addWidget(self.ai_text, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Animação Neon
        from PySide6.QtCore import QPropertyAnimation, QRect, QEasingCurve
        self.scan_line = QFrame(self.ai_overlay)
        sw = self.thumb_label.width()
        sh = self.thumb_label.height()
        self.scan_line.setFixedSize(sw, 4)
        self.scan_line.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 rgba(79, 195, 247, 0), stop:0.5 rgba(79, 195, 247, 255), stop:1 rgba(79, 195, 247, 0));"
        )
        
        self.anim = QPropertyAnimation(self.scan_line, b"geometry")
        self.anim.setDuration(1600)
        self.anim.setStartValue(QRect(0, 0, sw, 4))
        self.anim.setEndValue(QRect(0, sh - 4, sw, 4))
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.start()
        
        self.ai_overlay.show()
        self.ai_overlay.raise_()

    def hide_ai_overlay(self):
        if hasattr(self, 'anim') and self.anim:
            self.anim.stop()
            self.anim = None
            
        if hasattr(self, 'ai_overlay') and self.ai_overlay:
            self.ai_overlay.deleteLater()
            self.ai_overlay = None

    def update_index(self, new_index: int):
        self.doc_index = new_index

    # ── Hover ─────────────────────────────────────────────────
    def enterEvent(self, event):
        self.btn_delete.show()
        self.btn_rotate_left.show()
        self.btn_rotate_right.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_delete.hide()
        self.btn_rotate_left.hide()
        self.btn_rotate_right.hide()
        super().leaveEvent(event)
