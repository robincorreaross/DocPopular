"""
license_screen.py - Tela de ativação de licença standalone (PySide6).
Exibida ao iniciar o app quando não há licença válida.
"""

from __future__ import annotations

import webbrowser
import urllib.parse

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QMessageBox, QApplication,
)

from core.license import LicenseError, get_machine_id, validar_licenca
from ui.qt_styles import COLORS


class LicenseScreen(QMainWindow):
    def __init__(self, settings: dict, estado: str = "novo", msg_extra: str = ""):
        super().__init__()
        self.settings = settings
        self.estado = estado.lower()
        self.msg_extra = msg_extra
        self.machine_id = get_machine_id()

        self.setWindowTitle("DocPopular — Gerenciamento de Licença")
        self.setFixedSize(630, 580)
        self.setStyleSheet(f"background-color: {COLORS['bg_main']};")

        # Centraliza
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 630) // 2, (screen.height() - 580) // 2)

        self._build()

    def _build(self):
        config = {
            "novo": {
                "icon": "👋", "titulo": "Seja Bem-vindo!",
                "subtitulo": "Para começar a usar o DocPopular, você precisa de uma licença ativa.",
                "orientacao": "Fale com o administrador para escolher o plano ideal e liberar seu acesso.",
                "cor": COLORS['accent'],
                "zap_msg": f"Olá Robinson, acabei de instalar o DocPopular e gostaria de escolher um plano. Meu ID: {self.machine_id}"
            },
            "expirado": {
                "icon": "⚠️", "titulo": "Sua Licença Expirou",
                "subtitulo": "O prazo de validade do seu plano atual chegou ao fim.",
                "orientacao": "Entre em contato para renovar sua assinatura.",
                "cor": COLORS['error'],
                "zap_msg": f"Olá Robinson, minha licença do DocPopular expirou. Gostaria de renovar. Meu ID: {self.machine_id}"
            },
            "inativo": {
                "icon": "🚫", "titulo": "Licença Inativada",
                "subtitulo": "Seu acesso foi desativado temporariamente pelo administrador.",
                "orientacao": "Favor entrar em contato para verificar o status da sua conta.",
                "cor": "#FF9800",
                "zap_msg": f"Olá Robinson, meu acesso ao DocPopular aparece como Inativo. Pode verificar? Meu ID: {self.machine_id}"
            }
        }.get(self.estado, {
            "icon": "💊", "titulo": "DocPopular",
            "subtitulo": "Gerenciamento inteligente de licenças.",
            "orientacao": "Entre em contato para ativar sua licença.",
            "cor": COLORS['accent'],
            "zap_msg": f"Olá Robinson, preciso de ativação no DocPopular. Meu ID: {self.machine_id}"
        })

        self.zap_msg = config["zap_msg"]

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(8)

        # Ícone
        lbl_icon = QLabel(config["icon"])
        lbl_icon.setFont(QFont("Segoe UI Emoji", 40))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        # Título
        lbl_title = QLabel(config["titulo"])
        lbl_title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {config['cor']};")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # Subtítulo
        lbl_sub = QLabel(config["subtitulo"])
        lbl_sub.setFont(QFont("Segoe UI", 13))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)
        layout.addSpacing(10)

        # Card Machine ID
        mid_card = QFrame()
        mid_card.setObjectName("card")
        mid_layout = QVBoxLayout(mid_card)
        mid_layout.setContentsMargins(25, 15, 25, 15)

        lbl_mid_title = QLabel("🖥️  Seu Identificador (Machine ID)")
        lbl_mid_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_mid_title.setStyleSheet(f"color: #B0BEC5;")
        mid_layout.addWidget(lbl_mid_title)

        mid_inner = QFrame()
        mid_inner.setStyleSheet(f"background-color: {COLORS['bg_input']}; border-radius: 10px;")
        mid_row = QHBoxLayout(mid_inner)
        mid_row.setContentsMargins(15, 12, 10, 12)

        lbl_mid = QLabel(self.machine_id)
        lbl_mid.setFont(QFont("Courier New", 17, QFont.Weight.Bold))
        lbl_mid.setStyleSheet(f"color: {COLORS['text_primary']};")
        mid_row.addWidget(lbl_mid, stretch=1)

        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setObjectName("btn_primary")
        btn_copy.setMinimumSize(100, 36)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._copiar_mid)
        mid_row.addWidget(btn_copy)

        mid_layout.addWidget(mid_inner)

        lbl_orient = QLabel(config["orientacao"])
        lbl_orient.setFont(QFont("Segoe UI", 11))
        lbl_orient.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic;")
        lbl_orient.setWordWrap(True)
        mid_layout.addWidget(lbl_orient)

        layout.addWidget(mid_card)
        layout.addSpacing(10)

        # Botões
        btn_recheck = QPushButton("🔄  Já adquiri! Verificar Agora")
        btn_recheck.setObjectName("btn_primary")
        btn_recheck.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn_recheck.setFixedHeight(48)
        btn_recheck.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recheck.clicked.connect(self._recheck)
        layout.addWidget(btn_recheck)

        btn_zap = QPushButton("💬  Falar com Robinson (WhatsApp)")
        btn_zap.setObjectName("btn_green")
        btn_zap.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn_zap.setFixedHeight(48)
        btn_zap.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zap.clicked.connect(self._abrir_whatsapp)
        layout.addWidget(btn_zap)

        # Status
        self._status_label = QLabel(self.msg_extra if self.msg_extra else "Aguardando ativação...")
        self._status_label.setFont(QFont("Segoe UI", 11))
        self._status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)
        layout.addStretch(1)

    def _copiar_mid(self):
        QApplication.clipboard().setText(self.machine_id)
        self._status_label.setText("✅ ID copiado! Envie pelo WhatsApp.")
        self._status_label.setStyleSheet(f"color: {COLORS['success']};")

    def _recheck(self):
        self._status_label.setText("🔍 Verificando no servidor...")
        self._status_label.setStyleSheet(f"color: {COLORS['accent']};")
        QApplication.processEvents()
        try:
            info = validar_licenca("")
            if info.get("valido"):
                QMessageBox.information(self, "Sucesso", "✅ Acesso liberado! Bom trabalho.")
                self.close()
                from ui.app import App
                self._app = App()
                self._app.showMaximized()
            else:
                self._status_label.setText("❌ Ainda não consta como ativo na planilha.")
                self._status_label.setStyleSheet(f"color: {COLORS['error']};")
        except LicenseError as e:
            msg = str(e)
            if "novo" in msg:
                msg = "Aguardando liberação no sistema."
            self._status_label.setText(f"❌ {msg}")
            self._status_label.setStyleSheet(f"color: {COLORS['error']};")
        except Exception:
            self._status_label.setText("⚠️ Verifique sua internet.")
            self._status_label.setStyleSheet("color: #FFA726;")

    def _abrir_whatsapp(self):
        url = f"https://wa.me/5516991080895?text={urllib.parse.quote(self.zap_msg)}"
        webbrowser.open(url)


class LicenseExpiredScreen(LicenseScreen):
    def __init__(self, settings: dict, msg_extra: str = ""):
        super().__init__(settings, estado="expirado", msg_extra=msg_extra)
