"""
app.py - Janela principal do DocPopular (PySide6) com navegação por sidebar.
"""

from __future__ import annotations

import os
import sys
import webbrowser
import urllib.parse
from typing import Any, List, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMessageBox,
    QProgressBar, QSizePolicy, QApplication,
)

from core.config import load_settings, save_settings
from version import APP_VERSION
from ui.qt_styles import COLORS
from core.sync_manager import sync_manager


def get_resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    return str(base_path / relative_path)


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DocPopular — Auditor de Documentos PFPB")
        self.setMinimumSize(1000, 650)
        self.resize(1150, 720)

        # Ícone
        icon_path = get_resource_path("assets/icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings = load_settings()
        self.current_transaction = None
        self._update_zip_url: str = ""
        self._license_cache: dict | None = None

        self._build_layout()
        self.show_home()

        # Verificações em background
        QTimer.singleShot(1000, self._iniciar_verificacao_update)
        QTimer.singleShot(1500, self._verificar_expiracao_proxima)
        
        # Inicia o Sincronizador com Supabase (intervalo de 30s)
        sync_manager.start()

    def update_settings(self, new_settings: dict) -> None:
        """Salva as novas configurações no arquivo e atualiza o estado em memória."""
        from core.config import save_settings
        self.settings = new_settings
        save_settings(self.settings)


    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Banner de Expiração ────────────────────────────────────────────
        self._expiration_banner = QFrame()
        self._expiration_banner.setStyleSheet(f"background-color: {COLORS['warning']};")
        self._expiration_banner.setFixedHeight(0)
        self._expiration_banner.hide()
        self._exp_banner_layout = QHBoxLayout(self._expiration_banner)
        self._exp_banner_layout.setContentsMargins(16, 0, 16, 0)
        root_layout.addWidget(self._expiration_banner)

        # ── Banner de Update ───────────────────────────────────────────────
        self._update_banner = QFrame()
        self._update_banner.setStyleSheet("background-color: #0D2B0D;")
        self._update_banner.setFixedHeight(42)
        self._update_banner.hide()
        self._update_banner_layout = QHBoxLayout(self._update_banner)
        self._update_banner_layout.setContentsMargins(16, 0, 16, 0)
        root_layout.addWidget(self._update_banner)

        # ── Body (Sidebar + Content) ──────────────────────────────────────
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root_layout.addLayout(body, stretch=1)

        # ── Sidebar ───────────────────────────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(260)  # Aumentado de 200 para 260 para evitar cortes
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo
        logo_frame = QWidget()
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.setContentsMargins(16, 24, 16, 8)

        lbl_icon = QLabel("🏥")
        lbl_icon.setFont(QFont("Segoe UI Emoji", 32))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(lbl_icon)

        lbl_name = QLabel("DocPopular")
        lbl_name.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_name.setStyleSheet(f"color: {COLORS['accent']};")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(lbl_name)

        lbl_sub = QLabel("Auditor PFPB")
        lbl_sub.setFont(QFont("Segoe UI", 11))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_label']};")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(lbl_sub)

        sidebar_layout.addWidget(logo_frame)

        # Separador
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['separator']};")
        sidebar_layout.addWidget(sep)

        # Botões da Sidebar
        self._sidebar_buttons: list[QPushButton] = []

        self.btn_home = self._make_sidebar_btn("  📋  Nova Transação", lambda: self._confirmar_navegacao(self.show_home))
        sidebar_layout.addWidget(self.btn_home)

        self.btn_search_doc = self._make_sidebar_btn("  🔍  Procurar Documento", lambda: self._confirmar_navegacao(self.show_search_doc))
        sidebar_layout.addWidget(self.btn_search_doc)

        self.btn_settings = self._make_sidebar_btn("  ⚙️  Configurações", lambda: self._confirmar_navegacao(self.show_settings))
        sidebar_layout.addWidget(self.btn_settings)

        self.btn_help = self._make_sidebar_btn("  ❓  Ajuda e Suporte", lambda: self._confirmar_navegacao(self.show_help))
        sidebar_layout.addWidget(self.btn_help)

        # Espaçador
        sidebar_layout.addStretch(1)

        # Versão
        lbl_version = QLabel(f"v{APP_VERSION}")
        lbl_version.setFont(QFont("Segoe UI", 10))
        lbl_version.setStyleSheet(f"color: #B0BEC5;")
        lbl_version.setContentsMargins(16, 0, 0, 12)
        sidebar_layout.addWidget(lbl_version)

        body.addWidget(self.sidebar)

        # ── Área de Conteúdo ──────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        body.addWidget(self.stack, stretch=1)

        self._current_screen = None

    def _make_sidebar_btn(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("sidebar_btn")
        btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(50)  # Aumentado de 38 para 50 para melhor ergonomia
        btn.clicked.connect(callback)
        self._sidebar_buttons.append(btn)
        return btn

    # ── Sistema de update ────────────────────────────────────────────────────

    def _verificar_expiracao_proxima(self) -> None:
        try:
            from core.license import validar_licenca, carregar_licenca
            key = carregar_licenca(self.settings)
            info = validar_licenca(key or "")
            self._license_cache = info
            dias = info.get("dias_restantes", 999)
            if 0 <= dias <= 3:
                self._mostrar_banner_expiracao(dias)
        except Exception:
            pass

    def _mostrar_banner_expiracao(self, dias: int) -> None:
        # Limpa layout de forma segura
        while self._exp_banner_layout.count():
            item = self._exp_banner_layout.takeAt(0)
            if item:
                w = item.widget()
                if w: w.deleteLater()

        self._expiration_banner.setFixedHeight(40)
        self._expiration_banner.show()

        msg = f"⚠️ Sua licença expira em {dias} dia(s)! Clique aqui para renovar agora." if dias > 0 else "⚠️ Sua licença expira HOJE! Renove agora para não parar."

        btn = QPushButton(msg)
        btn.setStyleSheet("background: transparent; color: white; font-weight: bold; font-size: 12px; border: none;")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._abrir_whatsapp_renovacao)
        self._exp_banner_layout.addWidget(btn)

    def _abrir_whatsapp_renovacao(self) -> None:
        from core.license import get_machine_id
        mid = get_machine_id()
        msg = f"Olá Robinson, minha licença do DocPopular está vencendo e gostaria de renovar. Meu ID: {mid}"
        url = f"https://wa.me/5516991080895?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def _iniciar_verificacao_update(self) -> None:
        try:
            from core.updater import verificar_atualizacao
            verificar_atualizacao(
                on_update_available=lambda v, c, m, z, sha="": QTimer.singleShot(
                    0, lambda: self._mostrar_banner_update(v, c, m, z, sha)
                )
            )
        except Exception:
            pass

    def _mostrar_banner_update(self, nova_versao: str, changelog: List[str], obrigatoria: bool, zip_url: str = "", expected_sha256: str = "") -> None:
        self._update_zip_url = zip_url
        self._expected_sha256 = expected_sha256

        while self._update_banner_layout.count():
            item = self._update_banner_layout.takeAt(0)
            if item:
                w = item.widget()
                if w: w.deleteLater()

        self._update_banner.show()

        emoji = "🚨" if obrigatoria else "🟢"
        tipo = "OBRIGATÓRIA" if obrigatoria else "disponível"
        texto = f"{emoji}  Atualização {tipo}: versão {nova_versao}   —   {changelog[0] if changelog else ''}"

        lbl = QLabel(texto)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {'#FFCDD2' if obrigatoria else '#A5D6A7'};")
        self._update_banner_layout.addWidget(lbl, stretch=1)

        if not obrigatoria:
            btn_close = QPushButton("✕")
            btn_close.setFixedSize(28, 28)
            btn_close.setStyleSheet("background: transparent; color: #78909C; border: none; font-size: 11px;")
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.clicked.connect(self._fechar_banner)
            self._update_banner_layout.addWidget(btn_close)

        btn_dl = QPushButton("⬇️  Baixar agora")
        btn_dl.setObjectName("btn_primary" if not obrigatoria else "btn_green")
        btn_dl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_dl.setFixedSize(140, 28)
        btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        color = "#2E7D32" if not obrigatoria else "#C62828"
        btn_dl.setStyleSheet(f"background-color: {color}; color: white; border: none; border-radius: 6px;")
        btn_dl.clicked.connect(self._abrir_download)
        self._update_banner_layout.addWidget(btn_dl)

    def _abrir_download(self) -> None:
        if self._update_zip_url:
            self._mostrar_progresso_download(self._update_zip_url, getattr(self, "_expected_sha256", ""))
        else:
            from core.updater import abrir_download
            abrir_download()

    def _mostrar_progresso_download(self, zip_url: str, expected_sha256: str = "") -> None:
        from core.updater import baixar_e_instalar
        from PySide6.QtWidgets import QDialog

        dialog = QDialog(self)
        dialog.setWindowTitle("Instalando Atualização")
        dialog.setFixedSize(480, 240)
        dialog.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        lbl_title = QLabel("⬇️  Baixando atualização...")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['accent']};")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        status_lbl = QLabel("Conectando...")
        status_lbl.setFont(QFont("Segoe UI", 12))
        status_lbl.setStyleSheet(f"color: {COLORS['text_label']};")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_lbl)

        prog_bar = QProgressBar()
        prog_bar.setFixedWidth(400)
        prog_bar.setValue(0)
        layout.addWidget(prog_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        pct_lbl = QLabel("0%")
        pct_lbl.setFont(QFont("Segoe UI", 11))
        pct_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pct_lbl)

        def on_progress(pct: int, msg: str) -> None:
            QTimer.singleShot(0, lambda: [
                prog_bar.setValue(pct),
                status_lbl.setText(msg),
                pct_lbl.setText(f"{pct}%"),
            ])

        def on_success() -> None:
            def _done():
                status_lbl.setText("✅ Instalação concluída! Reiniciando...")
                status_lbl.setStyleSheet(f"color: {COLORS['success']};")
                pct_lbl.setText("100%")
                QTimer.singleShot(2000, self.close)
            QTimer.singleShot(0, _done)

        def on_error(msg: str) -> None:
            def _show():
                status_lbl.setText(f"❌ Erro: {msg}")
                status_lbl.setStyleSheet(f"color: {COLORS['error']};")
                btn_manual = QPushButton("Baixar manualmente")
                btn_manual.setObjectName("btn_primary")
                btn_manual.clicked.connect(lambda: webbrowser.open(getattr(sys.modules.get('version', None), 'DOWNLOAD_URL', '')))
                layout.addWidget(btn_manual, alignment=Qt.AlignmentFlag.AlignCenter)
            QTimer.singleShot(0, _show)

        baixar_e_instalar(
            zip_url=zip_url,
            expected_sha256=getattr(self, "_expected_sha256", ""),
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
        )
        dialog.exec()

    def _fechar_banner(self) -> None:
        self._update_banner.hide()

    # ── Navegação ────────────────────────────────────────────────────────────────

    def _confirmar_navegacao(self, callback) -> None:
        if not self.current_transaction or self.current_transaction.concluida:
            callback()
            return

        res = QMessageBox.question(
            self, "Sair da Transação?",
            "Você tem uma transação em andamento. Deseja realmente descartá-la e voltar para o início?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            res2 = QMessageBox.question(
                self, "Atenção!",
                "Todo o trabalho realizado nesta digitalização será perdido.\n\nConfirma o cancelamento?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res2 == QMessageBox.StandardButton.Yes:
                self.current_transaction = None
                callback()

    def _set_active_btn(self, active_btn: QPushButton) -> None:
        for btn in self._sidebar_buttons:
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        active_btn.setProperty("active", True)
        active_btn.style().unpolish(active_btn)
        active_btn.style().polish(active_btn)

    def _show_screen(self, screen_class, **kwargs) -> None:
        if self._current_screen:
            self.stack.removeWidget(self._current_screen)
            self._current_screen.deleteLater()
        self._current_screen = screen_class(app=self, **kwargs)
        self.stack.addWidget(self._current_screen)
        self.stack.setCurrentWidget(self._current_screen)

    def show_home(self) -> None:
        from ui.screens.home_screen import HomeScreen
        self._set_active_btn(self.btn_home)
        self._show_screen(HomeScreen)

    def show_scan(self, transaction) -> None:
        from ui.screens.scan_screen import ScanScreen
        self.current_transaction = transaction
        self._show_screen(ScanScreen, transaction=transaction)

    def show_unified_scan(self, transaction) -> None:
        from ui.screens.unified_scan_screen import UnifiedScanScreen
        self.current_transaction = transaction
        self._show_screen(UnifiedScanScreen, transaction=transaction)

    def show_result(self, transaction) -> None:
        from ui.screens.result_screen import ResultScreen
        self._show_screen(ResultScreen, transaction=transaction)

    def show_settings(self) -> None:
        from ui.screens.settings_screen import SettingsScreen
        self._set_active_btn(self.btn_settings)
        self._show_screen(SettingsScreen)

    def show_search_doc(self) -> None:
        from ui.screens.search_document_screen import SearchDocumentScreen
        self._set_active_btn(self.btn_search_doc)
        self._show_screen(SearchDocumentScreen)

    def show_help(self) -> None:
        from ui.screens.help_screen import HelpScreen
        self._set_active_btn(self.btn_help)
        self._show_screen(HelpScreen)

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        self.settings = new_settings
        save_settings(new_settings)

    def closeEvent(self, event) -> None:
        """Encerra threads de background e confirma fechamento se houver transação ativa."""
        from ui.screens.scan_screen import ScanScreen
        from ui.screens.unified_scan_screen import UnifiedScanScreen
        is_scanning = isinstance(self._current_screen, (ScanScreen, UnifiedScanScreen))
        
        if is_scanning and self.current_transaction and not self.current_transaction.concluida:
            resp = QMessageBox.question(
                self, "Confirmar Cancelamento",
                "Você está no meio de uma digitalização.\n\nDeseja descartar as imagens atuais e fechar o aplicativo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        # Pergunta final de saída (opcional, mas bom para evitar fechamentos acidentais)
        # Se já confirmou o cancelamento acima ou se não estava escaneando, pergunta normal
        else:
            resp = QMessageBox.question(
                self, "Sair do DocPopular",
                "Deseja realmente fechar o aplicativo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        # Se chegou aqui, encerra tudo
        print("[App] Encerrando SyncManager...")
        sync_manager.stop()
        event.accept()
