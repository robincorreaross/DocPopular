"""
settings_screen.py - Tela de configurações (PySide6): Scanner e Armazenamento.
"""

from __future__ import annotations

import copy
import threading
from typing import TYPE_CHECKING, List, Optional, Tuple
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QPushButton, QComboBox,
    QScrollArea, QFileDialog, QMessageBox, QLayout
)

from core import scanner as scan_module
from ui.qt_styles import COLORS

if TYPE_CHECKING:
    from ui.app import App


class SettingsScreen(QWidget):
    # Sinal para receber o resultado do scanner de forma thread-safe
    _scan_result_signal = Signal(object)

    def __init__(self, app: "App", **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.settings = copy.deepcopy(app.settings)
        self.engine = scan_module.ScannerEngine()
        
        # Conexão do sinal
        self._scan_result_signal.connect(self._handle_test_result)
        
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 16)
        layout.setSpacing(0)

        # Cabeçalho
        lbl_title = QLabel("Configurações")
        lbl_title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Gerencie as configurações de scanner e armazenamento.")
        lbl_sub.setFont(QFont("Segoe UI", 13))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_label']};")
        layout.addWidget(lbl_sub)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['separator']};")
        layout.addWidget(sep)
        layout.addSpacing(16)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, stretch=1)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 10, 0) # Espaço para scrollbar
        scroll_layout.setSpacing(24)
        scroll.setWidget(scroll_content)

        # ── Seção Armazenamento ───────────────────────────────────────────
        storage_card, s_layout = self._make_section("📂  Armazenamento")

        lbl_path = QLabel("Pasta de saída dos PDFs:")
        lbl_path.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_path.setStyleSheet(f"color: {COLORS['text_secondary']};")
        s_layout.addWidget(lbl_path)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        self.folder_entry = QLineEdit(self.settings.get("output_folder", ""))
        self.folder_entry.setReadOnly(True)
        self.folder_entry.setFont(QFont("Segoe UI", 12))
        self.folder_entry.setFixedHeight(40)
        path_row.addWidget(self.folder_entry, stretch=1)

        btn_folder = QPushButton("📂  Alterar")
        btn_folder.setObjectName("btn_secondary")
        btn_folder.setFixedSize(120, 40)
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self._escolher_pasta)
        path_row.addWidget(btn_folder)
        s_layout.addLayout(path_row)

        self.lbl_count = QLabel("")
        self.lbl_count.setFont(QFont("Segoe UI", 11))
        self.lbl_count.setStyleSheet(f"color: {COLORS['text_muted']};")
        s_layout.addWidget(self.lbl_count)
        self._update_pdf_count()

        scroll_layout.addWidget(storage_card)

        # ── Seção Scanner ─────────────────────────────────────────────────
        scanner_card, sc_layout = self._make_section("🖨️  Scanner")

        lbl_scanner = QLabel("Scanner selecionado:")
        lbl_scanner.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_scanner.setStyleSheet(f"color: {COLORS['text_secondary']};")
        sc_layout.addWidget(lbl_scanner)

        scanner_row = QHBoxLayout()
        scanner_row.setSpacing(10)
        self.scanner_list = self.engine.list_scanners()
        
        current_scanner = self.settings.get("scanner_name", "")
        combo_val = current_scanner if current_scanner in self.scanner_list else self.scanner_list[0]

        self.scanner_combo = QComboBox()
        self.scanner_combo.addItems(self.scanner_list)
        self.scanner_combo.setCurrentText(combo_val)
        self.scanner_combo.setFont(QFont("Segoe UI", 12))
        self.scanner_combo.setFixedHeight(40)
        self.scanner_combo.setMinimumWidth(250) # Restrição para evitar sobreposição
        scanner_row.addWidget(self.scanner_combo, stretch=1)

        btn_refresh = QPushButton("🔄  Atualizar")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.setFixedSize(120, 40)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self._atualizar_scanners)
        scanner_row.addWidget(btn_refresh)

        btn_test = QPushButton("🧪  Testar")
        btn_test.setObjectName("btn_secondary")
        btn_test.setFixedSize(100, 40)
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.clicked.connect(self._testar_scanner)
        scanner_row.addWidget(btn_test)

        sc_layout.addLayout(scanner_row)

        self.lbl_scanner_status = QLabel("ℹ️ Selecione seu scanner. Use 'Simulador DocPopular' se estiver testando localmente.")
        self.lbl_scanner_status.setFont(QFont("Segoe UI", 11))
        self.lbl_scanner_status.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.lbl_scanner_status.setWordWrap(True)
        self.lbl_scanner_status.setMinimumHeight(40)
        sc_layout.addWidget(self.lbl_scanner_status)

        scroll_layout.addWidget(scanner_card)
        scroll_layout.addStretch(1)

        # Botão salvar
        layout.addSpacing(16)
        btn_save = QPushButton("💾   Salvar Configurações")
        btn_save.setObjectName("btn_primary")
        btn_save.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn_save.setFixedHeight(50)
        btn_save.setMinimumWidth(300)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._salvar)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)

    def _make_section(self, title: str) -> Tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {COLORS['accent']};")
        card_layout.addWidget(lbl)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        sep.setMinimumHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['separator']};")
        card_layout.addWidget(sep)

        return card, card_layout

    def _update_pdf_count(self):
        folder = self.settings.get("output_folder", "")
        if folder and Path(folder).exists():
            count = len(list(Path(folder).glob("*.pdf")))
            self.lbl_count.setText(f"📄  {count} arquivo(s) PDF encontrados.")
        else:
            self.lbl_count.setText("⚠️  Pasta de saída inválida ou não configurada.")

    def _escolher_pasta(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta de saída")
        if path:
            self.folder_entry.setText(path)
            self.settings["output_folder"] = path
            self._update_pdf_count()

    def _atualizar_scanners(self):
        self.scanner_list = self.engine.list_scanners()
        self.scanner_combo.clear()
        self.scanner_combo.addItems(self.scanner_list)
        self.lbl_scanner_status.setText(f"✅ Lista atualizada: {len(self.scanner_list)-1} scanner(s) encontrados.")

    def _testar_scanner(self):
        scanner_name = self.scanner_combo.currentText()
        self.lbl_scanner_status.setText("⌛  Iniciando teste de hardware...")
        
        self._test_timeout = QTimer(self)
        self._test_timeout.setSingleShot(True)
        self._test_timeout.timeout.connect(self._on_test_timeout)
        self._test_timeout.start(30000)

        def on_done(img, err):
            self._scan_result_signal.emit((img, err))

        def on_status(msg):
            QTimer.singleShot(0, lambda: self.lbl_scanner_status.setText(f"⌛  {msg}"))

        self.engine.scan(scanner_name, on_done, on_status)

    def _handle_test_result(self, result):
        img, err = result
        if hasattr(self, "_test_timeout"):
            self._test_timeout.stop()
            
        if img:
            self.lbl_scanner_status.setText(f"✅ Teste concluído com sucesso! ({img.width}x{img.height})")
            QMessageBox.information(self, "Scanner", "Hardware respondendo perfeitamente.")
        else:
            err_final = err or "Erro desconhecido"
            self.lbl_scanner_status.setText(f"❌ Falha no teste: {err_final}")
            QMessageBox.critical(self, "Scanner", f"O scanner reportou um erro:\n{err_final}")

    def _on_test_timeout(self):
        self.lbl_scanner_status.setText("❌ Timeout: O hardware não respondeu.")
        QMessageBox.warning(self, "Scanner", "Limite de 30 segundos atingido.")

    def _salvar(self):
        self.settings["output_folder"] = self.folder_entry.text()
        self.settings["scanner_name"] = self.scanner_combo.currentText()
        self.app.update_settings(self.settings)
        QMessageBox.information(self, "Sucesso", "Configurações aplicadas com sucesso!")
