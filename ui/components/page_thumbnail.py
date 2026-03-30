"""
page_thumbnail.py - Componente de Card de Página para o DocPopular (PySide6).
Extraído e adaptado do RossPDFEditor para trabalhar com PIL.Image.
"""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PIL import Image
import io


class HoverButton(QPushButton):
    """Botão customizado flutuante que desenha seu próprio fundo e ícone
    contornando bugs de renderização CSS com alpha em fontes unicode do Qt."""
    def __init__(self, text, text_color, font_size, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self._text = text
        self._text_color = QColor(text_color)
        self._font_size = font_size
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)

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
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Fundo circular, mais escuro no hover
        bg_alpha = 216 if self._hovered else 165
        painter.setBrush(QColor(0, 0, 0, bg_alpha))
        painter.setPen(Qt.NoPen)
        r = self.rect()
        painter.drawEllipse(r)

        # Texto (ícone) desenhado manualmente
        painter.setPen(self._text_color)
        font = painter.font()
        font.setPixelSize(self._font_size)
        font.setBold(True)
        painter.setFont(font)

        if self._text in ("↺", "↻"):
            r.translate(0, -2)

        painter.drawText(r, Qt.AlignCenter, self._text)


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Converte PIL.Image para QPixmap."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)


class PageThumbnail(QFrame):
    """Card visual que representa uma página digitalizada."""

    delete_requested = Signal(int)
    rotate_left_requested = Signal(int)
    rotate_right_requested = Signal(int)

    THUMB_WIDTH = 480
    THUMB_HEIGHT = 640

    def __init__(self, page_index: int, pil_image: Image.Image, parent=None):
        super().__init__(parent)
        self.page_index = page_index

        self.setObjectName("page_card")
        self.setFixedSize(self.THUMB_WIDTH + 40, self.THUMB_HEIGHT + 60)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#page_card {
                background-color: transparent;
                border-radius: 12px;
            }
        """)

        # ── Layout ───────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(4)

        # Miniatura
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(self.THUMB_WIDTH, self.THUMB_HEIGHT)
        self.thumb_label.setStyleSheet("background-color: #ffffff; border-radius: 6px;")
        layout.addWidget(self.thumb_label, alignment=Qt.AlignCenter)

        # Número da página
        self.page_label = QLabel(f"Página {page_index + 1}")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #90A4AE; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.page_label)

        # ── Botão Excluir (canto superior direito) ────────────
        self.btn_delete = HoverButton("✕", "#ff1744", 22, self)
        self.btn_delete.setToolTip("Excluir Página")
        self.btn_delete.hide()
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.page_index))

        # ── Botão Girar Esq (canto inferior esquerdo) ──────────
        self.btn_rotate_left = HoverButton("↺", "#40c4ff", 28, self)
        self.btn_rotate_left.setToolTip("Girar para Esquerda")
        self.btn_rotate_left.hide()
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_left_requested.emit(self.page_index))

        # ── Botão Girar Dir (canto inferior direito) ──────────
        self.btn_rotate_right = HoverButton("↻", "#40c4ff", 28, self)
        self.btn_rotate_right.setToolTip("Girar para Direita")
        self.btn_rotate_right.hide()
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_right_requested.emit(self.page_index))

        # Posicionamento
        self.btn_delete.move(self.width() - 48, 4)
        self.btn_rotate_left.move(12, self.THUMB_HEIGHT - 30)
        self.btn_rotate_right.move(self.THUMB_WIDTH - 4, self.THUMB_HEIGHT - 30)

        # Carregar imagem
        self._set_thumbnail(pil_image)

    def _set_thumbnail(self, pil_img: Image.Image):
        """Carrega um PIL.Image na label de miniatura."""
        if pil_img is None:
            return
        pixmap = pil_to_qpixmap(pil_img)
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.THUMB_WIDTH - 8, self.THUMB_HEIGHT - 8,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.thumb_label.setPixmap(scaled)

    def update_thumbnail(self, pil_img: Image.Image):
        """Atualiza a imagem da miniatura."""
        self._set_thumbnail(pil_img)

    # ── Overlay de IA ──────────────────────────────────────
    def show_ai_overlay(self):
        """Exibe overlay semi-transparente indicando que a IA está analisando."""
        self.ai_overlay = QLabel(self)
        self.ai_overlay.setFixedSize(self.THUMB_WIDTH, self.THUMB_HEIGHT)
        self.ai_overlay.move(self.thumb_label.pos())
        self.ai_overlay.setAlignment(Qt.AlignCenter)
        self.ai_overlay.setStyleSheet(
            "background-color: rgba(10, 22, 40, 180);"
            "border-radius: 6px;"
            "color: #4FC3F7;"
            "font-size: 18px;"
            "font-weight: bold;"
        )
        self.ai_overlay.setText("🤖  IA Analisando...")
        self.ai_overlay.show()
        self.ai_overlay.raise_()

    def hide_ai_overlay(self):
        """Remove o overlay de análise da IA."""
        # Limpa qualquer overlay órfão que pertença a este widget
        for child in self.findChildren(QLabel):
            if child.text() == "🤖  IA Analisando...":
                child.deleteLater()
        if hasattr(self, 'ai_overlay') and self.ai_overlay:
            try:
                self.ai_overlay.deleteLater()
            except: pass
            self.ai_overlay = None

    def update_index(self, new_index: int):
        self.page_index = new_index
        self.page_label.setText(f"Página {new_index + 1}")

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
