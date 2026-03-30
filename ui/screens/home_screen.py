"""
home_screen.py - Tela inicial (PySide6).
Fluxo único inteligente: CPF + botão de iniciar.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QPushButton, QMessageBox,
)

from core.cpf_manager import validate_cpf
from core.transaction import criar_transacao_unica
from ui.qt_styles import COLORS

if TYPE_CHECKING:
    from ui.app import App


class HomeScreen(QWidget):
    def __init__(self, app: "App", **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(0)

        # ── Cabeçalho ─────────────────────────────────────────────────────
        lbl_title = QLabel("Nova Transação")
        lbl_title.setFont(QFont("Segoe UI", 30, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Inicie digitando o CPF do paciente. O sistema guiará você pelo processo de digitalização.")
        lbl_sub.setFont(QFont("Segoe UI", 14))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_label']};")
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)

        # Separador
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['separator']};")
        layout.addWidget(sep)
        layout.addSpacing(40)

        # ── Card Central ──────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(16)

        # Ícone + Título do Card
        lbl_card_icon = QLabel("🏥")
        lbl_card_icon.setFont(QFont("Segoe UI Emoji", 36))
        lbl_card_icon.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_card_icon)

        lbl_card_title = QLabel("Identificação do Paciente")
        lbl_card_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        lbl_card_title.setStyleSheet(f"color: {COLORS['accent']};")
        lbl_card_title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_card_title)

        lbl_card_sub = QLabel("Para iniciar, digite o CPF do Paciente")
        lbl_card_sub.setFont(QFont("Segoe UI", 13))
        lbl_card_sub.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl_card_sub.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_card_sub)

        card_layout.addSpacing(8)

        # Campo CPF
        cpf_container = QVBoxLayout()
        cpf_row = QHBoxLayout()

        lbl_cpf = QLabel("CPF:")
        lbl_cpf.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_cpf.setStyleSheet(f"color: {COLORS['text_primary']};")
        cpf_row.addWidget(lbl_cpf)

        self.entry_cpf = QLineEdit()
        self.entry_cpf.setPlaceholderText("000.000.000-00")
        self.entry_cpf.setFont(QFont("Segoe UI", 16))
        self.entry_cpf.setFixedHeight(44)
        self.entry_cpf.setMaxLength(14)
        self.entry_cpf.textChanged.connect(self._on_cpf_changed)
        cpf_row.addWidget(self.entry_cpf)

        cpf_container.addLayout(cpf_row)

        self.lbl_cpf_msg = QLabel("")
        self.lbl_cpf_msg.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_cpf_msg.setAlignment(Qt.AlignCenter)
        self.lbl_cpf_msg.hide()
        cpf_container.addWidget(self.lbl_cpf_msg)

        card_layout.addLayout(cpf_container)

        # Botões de Ação
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_start = QPushButton("🚀 Iniciar Digitalização")
        self.btn_start.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_start.setFixedSize(260, 46)  # Largura travada para evitar que o botão fique gigante
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._iniciar)
        self._set_button_enabled(self.btn_start, False)
        
        btn_row.addWidget(self.btn_start)
        btn_row.addStretch(1)
        card_layout.addLayout(btn_row)

        # Centraliza o card
        h_center = QHBoxLayout()
        h_center.addStretch(1)
        h_center.addWidget(card)
        h_center.addStretch(1)
        layout.addLayout(h_center)
        layout.addStretch(1)

    def _set_button_enabled(self, btn: QPushButton, enabled: bool):
        btn.setEnabled(enabled)
        if enabled:
            btn.setStyleSheet(f"background-color: {COLORS['btn_primary']}; color: white; border-radius: 10px; padding: 10px; border: 1px solid transparent;")
        else:
            btn.setStyleSheet(f"background-color: {COLORS['btn_secondary']}; color: {COLORS['text_muted']}; border-radius: 10px; padding: 10px; border: 1px solid transparent;")

    def _on_cpf_changed(self, text: str):
        """Aplica máscara de CPF e valida."""
        digits = "".join(c for c in text if c.isdigit())[:11]
        masked = ""
        for i, d in enumerate(digits):
            if i in [3, 6]:
                masked += "."
            elif i == 9:
                masked += "-"
            masked += d

        if text != masked:
            self.entry_cpf.blockSignals(True)
            self.entry_cpf.setText(masked)
            self.entry_cpf.setCursorPosition(len(masked))
            self.entry_cpf.blockSignals(False)

        # Validação
        if len(masked) == 14:
            if validate_cpf(masked):
                self.lbl_cpf_msg.setText("✅ CPF Válido")
                self.lbl_cpf_msg.setStyleSheet(f"color: {COLORS['success']};")
                self.lbl_cpf_msg.show()
                self._set_button_enabled(self.btn_start, True)
            else:
                self.lbl_cpf_msg.setText("⚠️ CPF Inválido")
                self.lbl_cpf_msg.setStyleSheet(f"color: {COLORS['error']};")
                self.lbl_cpf_msg.show()
                self._set_button_enabled(self.btn_start, False)
        else:
            self.lbl_cpf_msg.hide()
            self._set_button_enabled(self.btn_start, False)

    def _iniciar(self):
        cpf = self.entry_cpf.text()
        if not validate_cpf(cpf):
            return
        
        from core.transaction import criar_transacao_unificada
        transaction = criar_transacao_unificada(cpf_paciente=cpf)
        self.entry_cpf.clear()
        self.app.show_unified_scan(transaction)
