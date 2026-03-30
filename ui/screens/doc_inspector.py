"""
doc_inspector.py - Modal de inspeção e validação de documento.
Split horizontal: viewer com zoom (esquerda) + checklist de validação (direita).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QPixmap, QImage, QPainter, QColor, QTransform
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QScrollArea, QWidget, QComboBox, QCheckBox
)
from PIL import Image
import io

from ui.qt_styles import COLORS
from core.doc_validator import (
    DocumentData, ChecklistItem, update_checklist_item,
    is_document_valid, is_checklist_valid, get_doc_type_label, 
    get_display_label, get_status_label,
    DOC_TIPO_IDENTIFICACAO,
)


def _pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)


class ZoomableImageLabel(QWidget):
    """Widget que suporta zoom com scroll, pan com drag, e rotação."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._rotation = 0  # graus
        self._pixmap_original: QPixmap | None = None
        self._pixmap_display: QPixmap | None = None
        self._pan_start = QPoint()
        self._pan_offset = QPoint(0, 0)
        self._dragging = False
        self.setStyleSheet("background-color: #0A0A1A; border-radius: 8px;")
        self.setMinimumSize(400, 500)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_image(self, pixmap: QPixmap):
        self._pixmap_original = pixmap
        self._zoom = 1.0
        self._rotation = 0
        self._pan_offset = QPoint(0, 0)
        self._update_display()

    def rotate_image(self, angle: int):
        """Rotaciona a imagem em ângulo (90, -90, 180)."""
        self._rotation = (self._rotation + angle) % 360
        self._update_display()

    def _update_display(self):
        if not self._pixmap_original:
            return
        # Aplicar rotação
        transform = QTransform()
        transform.rotate(self._rotation)
        rotated = self._pixmap_original.transformed(transform, Qt.TransformationMode.SmoothTransformation)

        w = int(rotated.width() * self._zoom)
        h = int(rotated.height() * self._zoom)
        max_w = self.width() - 16
        max_h = self.height() - 16
        self._pixmap_display = rotated.scaled(
            min(w, max_w * 2), min(h, max_h * 2),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.update()  # Dispara repaint

    def paintEvent(self, event):
        if not self._pixmap_display:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # Centralizar + offset de pan
        x = (self.width() - self._pixmap_display.width()) // 2 + self._pan_offset.x()
        y = (self.height() - self._pixmap_display.height()) // 2 + self._pan_offset.y()
        painter.drawPixmap(x, y, self._pixmap_display)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom = min(self._zoom * 1.15, 5.0)
        else:
            self._zoom = max(self._zoom / 1.15, 0.3)
        self._update_display()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.pos() - self._pan_start
            self._pan_offset += delta
            self._pan_start = event.pos()
            self.update()  # Repinta com novo offset

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()


class DocInspector(QDialog):
    """Modal de inspeção de documento com viewer + checklist."""

    def __init__(self, parent, doc_data: DocumentData):
        super().__init__(parent)
        self.doc_data = doc_data
        self.resultado = None  # "validated", "refazer", None

        self.setWindowTitle("Validação do Documento")
        self.setMinimumSize(1000, 650)
        self.resize(1100, 700)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {COLORS['bg_main']};")

        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # ── Header ───────────────────────────────────────────
        header = QHBoxLayout()
        lbl_title = QLabel(f"📋  Validação — {get_display_label(self.doc_data)}")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(lbl_title)
        header.addStretch(1)

        self.lbl_overall = QLabel(get_status_label(self.doc_data.overall_status))
        self.lbl_overall.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._style_overall_label()
        header.addWidget(self.lbl_overall)

        root.addLayout(header)

        # ── Body split ───────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(12)

        # Lado esquerdo: viewer + botões
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)

        self.viewer = ZoomableImageLabel()
        if self.doc_data.image:
            pixmap = _pil_to_qpixmap(self.doc_data.image)
            self.viewer.set_image(pixmap)
        left_panel.addWidget(self.viewer, stretch=1)

        # Botões de rotação do viewer
        viewer_controls = QHBoxLayout()
        viewer_controls.setSpacing(6)

        btn_rot_left = QPushButton("↺  Girar Esquerda")
        btn_rot_left.setFont(QFont("Segoe UI", 10))
        btn_rot_left.setFixedHeight(30)
        btn_rot_left.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rot_left.setStyleSheet(
            f"background-color: {COLORS['btn_secondary']}; color: white; "
            f"border: none; border-radius: 6px; padding: 0 12px;"
        )
        btn_rot_left.clicked.connect(lambda: self.viewer.rotate_image(-90))
        viewer_controls.addWidget(btn_rot_left)

        btn_rot_right = QPushButton("↻  Girar Direita")
        btn_rot_right.setFont(QFont("Segoe UI", 10))
        btn_rot_right.setFixedHeight(30)
        btn_rot_right.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rot_right.setStyleSheet(
            f"background-color: {COLORS['btn_secondary']}; color: white; "
            f"border: none; border-radius: 6px; padding: 0 12px;"
        )
        btn_rot_right.clicked.connect(lambda: self.viewer.rotate_image(90))
        viewer_controls.addWidget(btn_rot_right)

        viewer_controls.addStretch(1)
        left_panel.addLayout(viewer_controls)

        body.addLayout(left_panel, stretch=3)

        # Lado direito: checklist
        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_panel.setFixedWidth(360)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(4)

        lbl_checklist = QLabel("📋 Checklist de Validação")
        lbl_checklist.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_checklist.setStyleSheet(f"color: {COLORS['accent']};")
        right_layout.addWidget(lbl_checklist)

        # Scroll area para o checklist
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.checklist_layout = QVBoxLayout(scroll_content)
        self.checklist_layout.setContentsMargins(0, 4, 0, 4)
        self.checklist_layout.setSpacing(6)

        self._render_checklist()

        scroll.setWidget(scroll_content)
        right_layout.addWidget(scroll, stretch=1)

        # Dica
        lbl_hint = QLabel("🔍 Scroll = zoom | Pendentes em amarelo")
        lbl_hint.setFont(QFont("Segoe UI", 9))
        lbl_hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(lbl_hint)

        body.addWidget(right_panel)
        root.addLayout(body, stretch=1)

        # ── Footer buttons ───────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(8)

        btn_refazer = QPushButton("🔄  Refazer Digitalização")
        btn_refazer.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn_refazer.setFixedHeight(40)
        btn_refazer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refazer.setStyleSheet(
            f"background-color: {COLORS['delete_bg']}; color: white; "
            f"border: none; border-radius: 8px; padding: 0 20px;"
        )
        btn_refazer.clicked.connect(self._refazer)
        footer.addWidget(btn_refazer)

        footer.addStretch(1)

        self.btn_validate = QPushButton("✅  Validar Documento")
        self.btn_validate.setObjectName("btn_green")
        self.btn_validate.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_validate.setFixedHeight(40)
        self.btn_validate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate.clicked.connect(self._validate)
        self._update_validate_button()
        footer.addWidget(self.btn_validate)

        root.addLayout(footer)

    def _render_checklist(self):
        """Renderiza os itens do checklist."""
        # Limpa
        while self.checklist_layout.count():
            item = self.checklist_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.deleteLater()

        for ci in self.doc_data.checklist:
            row = self._create_checklist_row(ci)
            self.checklist_layout.addWidget(row)

        self.checklist_layout.addStretch(1)

    def _create_checklist_row(self, ci: ChecklistItem) -> QFrame:
        """Cria uma linha do checklist."""
        row = QFrame()
        row_style = self._row_bg_color(ci.status)
        row.setStyleSheet(f"background-color: {row_style}; border-radius: 6px; padding: 4px;")

        layout = QVBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # Label + status icon
        header_row = QHBoxLayout()

        status_icon = "✅" if ci.status == "valid" else ("⏳" if ci.status == "pending" else "❌")
        req_mark = " *" if ci.required else ""

        lbl = QLabel(f"{status_icon}  {ci.label}{req_mark}")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        header_row.addWidget(lbl)
        header_row.addStretch(1)

        layout.addLayout(header_row)

        # Valor / Input
        if ci.field_type == "readonly":
            if ci.value:
                lbl_val = QLabel(f"  → {ci.value}")
                lbl_val.setFont(QFont("Segoe UI", 10))
                lbl_val.setStyleSheet(f"color: {COLORS['accent']}; background: transparent;")
                layout.addWidget(lbl_val)

        elif ci.field_type == "select":
            combo = QComboBox()
            combo.addItem("— Selecione —")
            for opt in ci.options:
                combo.addItem(opt)
            if ci.value and ci.value in ci.options:
                combo.setCurrentText(ci.value)
            # FIX: garantir tamanho de fonte > 0 para evitar Warning do Qt
            font_combo = QFont("Segoe UI")
            font_combo.setPointSize(10)
            combo.setFont(font_combo)
            combo.setFixedHeight(32)
            combo.setStyleSheet(
                f"QComboBox {{ background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 8px; }}"
                f"QComboBox::drop-down {{ border: none; }}"
                f"QComboBox QAbstractItemView {{ background-color: {COLORS['bg_input']}; "
                f"color: {COLORS['text_primary']}; selection-background-color: {COLORS['accent']}; }}"
            )

            item_id = ci.id
            combo.currentTextChanged.connect(
                lambda text, iid=item_id: self._on_field_changed(iid, text if text != "— Selecione —" else "")
            )
            layout.addWidget(combo)

        elif ci.field_type == "bool":
            cb = QCheckBox("Sim")
            cb.setFont(QFont("Segoe UI", 10))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Ajuste do stylesheet para aumentar o tamanho da caixa
            cb.setStyleSheet(
                f"QCheckBox {{ color: {COLORS['text_primary']}; spacing: 8px; }}"
                "QCheckBox::indicator { width: 22px; height: 22px; }"
            )

            # Inicia bloqueado se for Não (falso)
            is_checked = (ci.value == "Sim")
            cb.setChecked(is_checked)

            item_id = ci.id
            def on_state_changed(state, iid=item_id):
                if state == Qt.CheckState.Checked.value:
                    self._on_field_changed(iid, "Sim")
                else:
                    self._on_field_changed(iid, "Não")

            cb.stateChanged.connect(on_state_changed)
            layout.addWidget(cb)


        elif ci.field_type == "date":
            entry = QLineEdit()
            entry.setPlaceholderText("DD/MM/AAAA")
            entry.setMaxLength(10)
            entry.setFont(QFont("Segoe UI", 10))
            entry.setFixedHeight(28)
            if ci.value:
                entry.setText(ci.value)

            item_id = ci.id

            def _on_date_text_changed(text, e=entry, iid=item_id):
                self._apply_date_mask(e, text)
                # Dispara validação automática quando a data estiver completa (10 chars)
                cleaned = e.text()
                if len(cleaned) == 10:
                    self._on_field_changed(iid, cleaned)

            entry.textChanged.connect(_on_date_text_changed)
            if not ci.editable:
                entry.setReadOnly(True)
            layout.addWidget(entry)

        else:  # text
            entry = QLineEdit()
            entry.setFont(QFont("Segoe UI", 10))
            entry.setFixedHeight(28)
            if ci.value:
                entry.setText(ci.value)
            if ci.id == "cpf":
                entry.setPlaceholderText("000.000.000-00")
                entry.setMaxLength(14)

            item_id = ci.id
            entry.editingFinished.connect(
                lambda iid=item_id, e=entry: self._on_field_changed(iid, e.text())
            )
            if not ci.editable:
                entry.setReadOnly(True)
            layout.addWidget(entry)

        return row

    def _row_bg_color(self, status: str) -> str:
        if status == "valid":
            return "rgba(46, 125, 50, 30)"
        elif status == "pending":
            return "rgba(255, 183, 77, 20)"
        elif status == "invalid":
            return "rgba(183, 28, 28, 30)"
        return "transparent"

    def _on_field_changed(self, item_id: str, value: str):
        """Chamado quando o operador edita um campo no checklist."""
        update_checklist_item(self.doc_data, item_id, value)
        self._render_checklist()
        self._update_overall()
        self._update_validate_button()

    def _update_overall(self):
        self.lbl_overall.setText(get_status_label(self.doc_data.overall_status))
        self._style_overall_label()

    def _style_overall_label(self):
        status = self.doc_data.overall_status
        colors = {"valid": COLORS['success'], "pending": "#FFB74D", "invalid": COLORS['error']}
        color = colors.get(status, "#FFB74D")
        self.lbl_overall.setStyleSheet(f"color: {color}; background: transparent;")

    def _update_validate_button(self):
        # O botão habilita quando o CHECKLIST está ok (independente se já foi auditado ou não)
        can_validate = is_checklist_valid(self.doc_data)
        self.btn_validate.setEnabled(can_validate)
        if can_validate:
            self.btn_validate.setStyleSheet(
                f"background-color: {COLORS['btn_green']}; color: white; "
                f"border: none; border-radius: 8px; padding: 0 20px;"
            )
        else:
            self.btn_validate.setStyleSheet(
                f"background-color: {COLORS['btn_secondary']}; color: {COLORS['text_muted']}; "
                f"border: none; border-radius: 8px; padding: 0 20px;"
            )

    def _apply_date_mask(self, entry: QLineEdit, text: str):
        digits = "".join(c for c in text if c.isdigit())[:8]
        masked = ""
        for i, d in enumerate(digits):
            if i in [2, 4]:
                masked += "/"
            masked += d
        if text != masked:
            entry.blockSignals(True)
            entry.setText(masked)
            entry.setCursorPosition(len(masked))
            entry.blockSignals(False)

    def _validate(self):
        # Define como auditado para que o status mude para 'valid'
        self.doc_data.is_audited = True
        # Força atualização do status geral no objeto
        update_checklist_item(self.doc_data, "", "") 
        
        self.resultado = "validated"
        self.accept()

    def _refazer(self):
        self.resultado = "refazer"
        self.accept()

    def closeEvent(self, event):
        if self.resultado is None:
            self.resultado = "closed"
        super().closeEvent(event)
