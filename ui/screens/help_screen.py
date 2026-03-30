"""
help_screen.py - Tela de Ajuda e Suporte (PySide6).
Exibe MachineID, validade da licença e contato do administrador.
"""

from __future__ import annotations

import webbrowser
import urllib.parse
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QScrollArea, QMessageBox, QApplication,
)

from core.license import get_machine_id, carregar_licenca, validar_licenca
from ui.qt_styles import COLORS

if TYPE_CHECKING:
    from ui.app import App


class HelpScreen(QWidget):
    def __init__(self, app: "App", **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.machine_id = get_machine_id()

        if self.app._license_cache:
            self.license_info = self.app._license_cache
        else:
            settings = self.app.settings
            key = carregar_licenca(settings)
            try:
                self.license_info = validar_licenca(key or "")
                self.app._license_cache = self.license_info
            except:
                self.license_info = None

        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        outer.addWidget(scroll)

        container = QWidget()
        container.setFixedWidth(700)
        scroll.setWidget(container)
        scroll.setAlignment(Qt.AlignHCenter)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Título
        lbl_title = QLabel("Central de Ajuda e Suporte")
        lbl_title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['accent']};")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        layout.addSpacing(16)

        # ── Card Licenciamento ────────────────────────────────────────────
        lic_card = QFrame()
        lic_card.setObjectName("card")
        lic_layout = QVBoxLayout(lic_card)
        lic_layout.setContentsMargins(25, 20, 25, 20)

        lbl_lic = QLabel("💳  Informações de Licenciamento")
        lbl_lic.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_lic.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lic_layout.addWidget(lbl_lic)
        lic_layout.addSpacing(8)

        # MachineID box
        mid_box = QFrame()
        mid_box.setStyleSheet(f"background-color: {COLORS['bg_input']}; border-radius: 10px;")
        mid_row = QHBoxLayout(mid_box)
        mid_row.setContentsMargins(15, 12, 15, 12)

        lbl_mid_title = QLabel("Machine ID:")
        lbl_mid_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_mid_title.setStyleSheet(f"color: {COLORS['text_muted']};")
        mid_row.addWidget(lbl_mid_title)

        lbl_mid_val = QLabel(self.machine_id)
        lbl_mid_val.setFont(QFont("Courier New", 15, QFont.Bold))
        lbl_mid_val.setStyleSheet(f"color: {COLORS['text_primary']};")
        mid_row.addWidget(lbl_mid_val, stretch=1)

        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setObjectName("btn_primary")
        btn_copy.setFixedSize(100, 32)
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.clicked.connect(self._copiar_mid)
        mid_row.addWidget(btn_copy)

        lic_layout.addWidget(mid_box)
        lic_layout.addSpacing(12)

        # Status
        status_row = QHBoxLayout()
        exp = "Desconhecida"
        plano = "N/A"
        if self.license_info:
            exp = self.license_info.get("expiry", "N/A")
            plano = str(self.license_info.get("plano", "N/A")).upper()

        lbl_exp = QLabel(f"📅  Vencimento: {exp}")
        lbl_exp.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_exp.setStyleSheet(f"color: {COLORS['success'] if self.license_info else COLORS['error']};")
        status_row.addWidget(lbl_exp)

        lbl_plano = QLabel(f"Plano: {plano}")
        lbl_plano.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_plano.setStyleSheet(f"color: {COLORS['accent']};")
        status_row.addWidget(lbl_plano, alignment=Qt.AlignRight)

        lic_layout.addLayout(status_row)
        layout.addWidget(lic_card)

        # ── Card Suporte ──────────────────────────────────────────────────
        sup_card = QFrame()
        sup_card.setObjectName("card")
        sup_layout = QVBoxLayout(sup_card)
        sup_layout.setContentsMargins(25, 20, 25, 25)

        lbl_sup = QLabel("🛠️  Suporte Técnico")
        lbl_sup.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_sup.setStyleSheet(f"color: {COLORS['text_secondary']};")
        sup_layout.addWidget(lbl_sup)

        lbl_sup_desc = QLabel("Precisa de renovação ou ajuda técnica? Chame nosso time pelo WhatsApp.")
        lbl_sup_desc.setFont(QFont("Segoe UI", 12))
        lbl_sup_desc.setStyleSheet(f"color: {COLORS['text_label']};")
        lbl_sup_desc.setWordWrap(True)
        sup_layout.addWidget(lbl_sup_desc)
        sup_layout.addSpacing(12)

        btn_zap = QPushButton("💬  Chamar Robinson no WhatsApp")
        btn_zap.setObjectName("btn_green")
        btn_zap.setFont(QFont("Segoe UI", 14, QFont.Bold))
        btn_zap.setFixedHeight(50)
        btn_zap.setCursor(Qt.PointingHandCursor)
        btn_zap.clicked.connect(self._abrir_whatsapp)
        sup_layout.addWidget(btn_zap)

        layout.addWidget(sup_card)
        layout.addStretch(1)

    def _copiar_mid(self):
        QApplication.clipboard().setText(self.machine_id)
        QMessageBox.information(self, "Copiado", "✅ Machine ID copiado! Pode enviar pelo WhatsApp.")

    def _abrir_whatsapp(self):
        msg = f"Olá Robinson, preciso de suporte no DocPopular (Machine ID: {self.machine_id})"
        url = f"https://wa.me/5516991080895?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)
