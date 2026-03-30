"""
search_document_screen.py - Tela de pesquisa de documentos por CPF (PySide6).
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QPushButton, QScrollArea,
    QFileDialog, QMessageBox,
)
from PIL import Image

from core.cpf_manager import validate_cpf
from core.database import get_current_company_id, get_arquivos_by_entidade
from ui.qt_styles import COLORS
from ui.components.page_thumbnail import pil_to_qpixmap

if TYPE_CHECKING:
    from ui.app import App


class SearchDocumentScreen(QWidget):
    def __init__(self, app: "App", **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._found_paths: list[str] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(0)

        # Cabeçalho
        lbl_title = QLabel("🔍  Procurar Documento")
        lbl_title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Busque por documentos de identificação já digitalizados no sistema informando o CPF.")
        lbl_sub.setFont(QFont("Segoe UI", 14))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_label']};")
        layout.addWidget(lbl_sub)
        layout.addSpacing(8)

        # Barra de Busca
        search_card = QFrame()
        search_card.setObjectName("card")
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(24, 24, 24, 24)

        lbl_cpf = QLabel("CPF:")
        lbl_cpf.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_cpf.setStyleSheet(f"color: {COLORS['success']};")
        search_layout.addWidget(lbl_cpf)

        self.entry_cpf = QLineEdit()
        self.entry_cpf.setPlaceholderText("000.000.000-00")
        self.entry_cpf.setFont(QFont("Segoe UI", 16))
        self.entry_cpf.setFixedSize(220, 40)
        self.entry_cpf.setMaxLength(14)
        self.entry_cpf.textChanged.connect(self._on_cpf_changed)
        search_layout.addWidget(self.entry_cpf)

        self.lbl_cpf_error = QLabel("⚠️ CPF Inválido")
        self.lbl_cpf_error.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_cpf_error.setStyleSheet(f"color: {COLORS['error']};")
        self.lbl_cpf_error.hide()
        search_layout.addWidget(self.lbl_cpf_error)

        self.btn_search = QPushButton("Pesquisar")
        self.btn_search.setObjectName("btn_secondary")
        self.btn_search.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_search.setFixedHeight(40)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self._do_search)
        search_layout.addWidget(self.btn_search)

        search_layout.addStretch(1)
        layout.addWidget(search_card)
        layout.addSpacing(8)

        # Resultados
        self.result_frame = QFrame()
        self.result_frame.setObjectName("card")
        self.result_layout = QVBoxLayout(self.result_frame)
        self.result_layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self.result_frame, stretch=1)

        self._show_empty_state("Digite um CPF válido e clique em Pesquisar.")

    def _on_cpf_changed(self, text: str):
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

        if len(masked) == 14:
            self.lbl_cpf_error.setVisible(not validate_cpf(masked))
        else:
            self.lbl_cpf_error.hide()

    def _show_empty_state(self, message: str):
        self._found_paths = []
        self._clear_results()

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel("📁")
        lbl_icon.setFont(QFont("Segoe UI Emoji", 48))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(lbl_icon)

        lbl_msg = QLabel(message)
        lbl_msg.setFont(QFont("Segoe UI", 14))
        lbl_msg.setStyleSheet(f"color: {COLORS['text_muted']};")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(lbl_msg)

        self.result_layout.addWidget(container, stretch=1)

    def _clear_results(self):
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _do_search(self):
        cpf = self.entry_cpf.text()
        if len(cpf) != 14:
            self._show_empty_state("CPF incompleto. Formato: XXX.XXX.XXX-XX")
            return
        if not validate_cpf(cpf):
            self._show_empty_state("CPF numericamente inválido. Verifique os dígitos.")
            return

        company_id = get_current_company_id(self.app.settings)
        # Busca arquivos vinculados ao paciente (CPF)
        arquivos = get_arquivos_by_entidade(company_id, "paciente_doc", cpf)
        
        if arquivos:
            self._found_paths = [r["path_local"] for r in arquivos]
            self._show_result(cpf, self._found_paths)
        else:
            self._show_empty_state(f"Nenhum documento encontrado para o CPF {cpf}.")

    def _show_result(self, cpf: str, image_paths: List[str]):
        self._clear_results()

        # Top bar
        top_row = QHBoxLayout()
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)

        lbl_found = QLabel("✅ Documento Encontrado!")
        lbl_found.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_found.setStyleSheet(f"color: {COLORS['success']};")
        info_layout.addWidget(lbl_found)

        lbl_count = QLabel(f"Total: {len(image_paths)} página(s) para o CPF {cpf}")
        lbl_count.setFont(QFont("Segoe UI", 14))
        lbl_count.setStyleSheet(f"color: {COLORS['success']};")
        info_layout.addWidget(lbl_count)

        top_row.addWidget(info, stretch=1)

        btn_dl = QPushButton("📥  Baixar Documento")
        btn_dl.setObjectName("btn_green")
        btn_dl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        btn_dl.setFixedHeight(40)
        btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dl.clicked.connect(self._download_files)
        top_row.addWidget(btn_dl)

        self.result_layout.addLayout(top_row)

        # Scroll com imagens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_inner = QVBoxLayout(scroll_content)
        scroll_inner.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        scroll.setWidget(scroll_content)

        for i, path in enumerate(image_paths, 1):
            lbl_page = QLabel(f"Página {i}")
            lbl_page.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            lbl_page.setStyleSheet(f"color: {COLORS['text_label']};")
            lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_inner.addWidget(lbl_page)

            try:
                img = Image.open(path)
                pixmap = pil_to_qpixmap(img)
                target_w = 700
                scaled = pixmap.scaledToWidth(target_w, Qt.TransformationMode.SmoothTransformation)

                lbl_img = QLabel()
                lbl_img.setPixmap(scaled)
                lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scroll_inner.addWidget(lbl_img)
            except Exception as e:
                lbl_err = QLabel(f"Erro ao carregar página {i}: {e}")
                lbl_err.setStyleSheet(f"color: {COLORS['error']};")
                scroll_inner.addWidget(lbl_err)

        self.result_layout.addWidget(scroll, stretch=1)

    def _download_files(self):
        if not self._found_paths:
            return

        if len(self._found_paths) == 1:
            source = self._found_paths[0]
            dest, _ = QFileDialog.getSaveFileName(
                self, "Salvar Documento",
                os.path.basename(source),
                "Imagens JPEG (*.jpg)"
            )
            if dest:
                try:
                    shutil.copy2(source, dest)
                    QMessageBox.information(self, "Sucesso", "Documento salvo com sucesso!")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{e}")
        else:
            dest_dir = QFileDialog.getExistingDirectory(self, "Selecione a pasta para salvar")
            if dest_dir:
                try:
                    for p in self._found_paths:
                        shutil.copy2(p, os.path.join(dest_dir, os.path.basename(p)))
                    QMessageBox.information(self, "Sucesso", f"{len(self._found_paths)} páginas salvas em:\n{dest_dir}")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{e}")
