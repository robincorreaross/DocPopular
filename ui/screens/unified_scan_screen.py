"""
unified_scan_screen.py - Tela unificada de digitalização com Cards Inteligentes.
O operador digitaliza/importa todos os documentos em uma única tela.
A IA classifica e valida cada documento automaticamente via checklist.
"""

from __future__ import annotations

import io
import datetime
import threading
from typing import List, Tuple, Optional
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QMessageBox, QFileDialog, QDialog,
    QSizePolicy, QApplication
)

from core import logger
from core import scanner as scan_module
from core import vision_processor
from core import ai_extractor
from core.doc_validator import (
    validate_document, DocumentData,
    get_doc_type_label, get_display_label, is_document_valid,
    update_checklist_item, DOC_TIPO_IDENTIFICACAO
)
from core.transaction import Transaction
from ui.qt_styles import COLORS
from ui.components.doc_card import DocCard


class UnifiedScanScreen(QWidget):
    # Signals para comunicação thread-safe → UI
    _ai_result_signal = Signal(int, object)
    _scan_result_signal = Signal(object)

    def __init__(self, app, transaction: Transaction, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.transaction = transaction
        self._doc_cards: List[DocCard] = [] 
        self._ai_result_signal.connect(self._handle_ai_result)
        self._scan_result_signal.connect(self._handle_scan_result)
        self.engine = scan_module.ScannerEngine()
        self._build()
        self._refresh_cards()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(0)

        # ── Cabeçalho ─────────────────────────────────────────
        header_row = QHBoxLayout()

        lbl_title = QLabel("📋  Digitalização de Documentos")
        lbl_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_row.addWidget(lbl_title)

        header_row.addStretch(1)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setFont(QFont("Segoe UI", 12))
        self.lbl_progress.setStyleSheet(f"color: {COLORS['text_muted']};")
        header_row.addWidget(self.lbl_progress)

        layout.addLayout(header_row)

        # ── Subtítulo ─────────────────────────────────────────
        self.lbl_desc = QLabel(
            "Digitalize ou importe todos os documentos necessários para a transação.\n"
            "A IA identificará automaticamente o tipo e validará cada documento."
        )
        self.lbl_desc.setFont(QFont("Segoe UI", 12))
        self.lbl_desc.setStyleSheet(f"color: {COLORS['text_label']};")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)
        layout.addSpacing(12)

        # ── Status bar ────────────────────────────────────────
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 11))
        self.lbl_status.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(self.lbl_status)
        layout.addSpacing(8)

        # ── Área de cards ─────────────────────────────────────
        cards_container = QFrame()
        cards_container.setObjectName("card")
        cards_inner = QVBoxLayout(cards_container)
        cards_inner.setContentsMargins(8, 12, 8, 12)

        lbl_docs = QLabel("Documentos digitalizados:")
        lbl_docs.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_docs.setStyleSheet(f"color: {COLORS['text_secondary']};")
        cards_inner.addWidget(lbl_docs)

        # Scroll horizontal
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_scroll.setStyleSheet("background: transparent; border: none;")
        self.cards_scroll.setMinimumHeight(460)

        self.cards_content = QWidget()
        self.cards_content.setObjectName("cards_content")
        self.cards_content.setStyleSheet("background: transparent;")
        self.cards_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.cards_layout = QHBoxLayout(self.cards_content)
        self.cards_layout.setContentsMargins(16, 16, 16, 16)
        self.cards_layout.setSpacing(24)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.cards_scroll.setWidget(self.cards_content)

        cards_inner.addWidget(self.cards_scroll, stretch=1)
        layout.addWidget(cards_container, stretch=1)

        # ── Empty label ──────────────────────────────────────
        self.lbl_empty = QLabel("Nenhum documento digitalizado ainda.\nClique em Escanear ou Importar para começar.")
        self.lbl_empty.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_empty.setStyleSheet(f"color: #37474F;")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cards_layout.addWidget(self.lbl_empty)

        layout.addSpacing(8)

        # ── Controles ─────────────────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.btn_scan = QPushButton("📷   Escanear")
        self.btn_scan.setObjectName("btn_primary")
        self.btn_scan.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_scan.setFixedHeight(44)
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan.clicked.connect(self._do_scan)
        controls.addWidget(self.btn_scan, stretch=1)

        self.btn_import = QPushButton("📁   Importar Arquivo")
        self.btn_import.setObjectName("btn_secondary")
        self.btn_import.setFont(QFont("Segoe UI", 13))
        self.btn_import.setFixedHeight(44)
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.clicked.connect(self._do_import)
        controls.addWidget(self.btn_import, stretch=1)

        self.btn_finish = QPushButton("🏁   Finalizar Transação")
        self.btn_finish.setObjectName("btn_green")
        self.btn_finish.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_finish.setFixedHeight(44)
        self.btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finish.setEnabled(False)
        self.btn_finish.clicked.connect(self._finalizar)
        controls.addWidget(self.btn_finish, stretch=1)

        layout.addLayout(controls)

    @property
    def _documents(self) -> list:
        return self.transaction.etapa_atual.documents

    def _refresh_cards(self):
        """Reconstrói todos os cards baseado nos documents da transação."""
        try:
            # Proteção contra chamadas em widgets destruídos
            if not hasattr(self, "cards_layout") or self.cards_layout is None:
                return

            # Limpa APENAS os cards de documentos e stretches
            # O lbl_empty não deve ser deletado, apenas ocultado/exibido
            while self.cards_layout.count():
                item = self.cards_layout.takeAt(0)
                if item:
                    w = item.widget()
                    if w:
                        # Se for o label de "vazio", apenas removemos do layout sem deletar
                        if w == self.lbl_empty:
                            self.cards_layout.removeWidget(w)
                            w.setParent(None) # Mantém vivo no Python mas fora do layout
                        else:
                            w.deleteLater()
            
            self._doc_cards.clear()
            docs = self._documents
            
            # Gerencia o label de "vazio"
            if not docs:
                self.cards_layout.addWidget(self.lbl_empty)
                self.lbl_empty.show()
            else:
                self.lbl_empty.hide()

            for i, doc_data in enumerate(docs):
                card = DocCard(
                    doc_index=i,
                    pil_image=doc_data.image,
                    doc_type=get_display_label(doc_data),
                    status=doc_data.overall_status,
                )
                card.delete_requested.connect(self._delete_doc)
                card.rotate_left_requested.connect(lambda idx: self._rotate_doc(idx, 90))
                card.rotate_right_requested.connect(lambda idx: self._rotate_doc(idx, -90))
                card.inspect_requested.connect(self._inspect_doc)
                self.cards_layout.addWidget(card)
                self._doc_cards.append(card)

            # Adiciona UM ÚNICO stretch no fim para manter os cards à esquerda
            self.cards_layout.addStretch(1)
            
            # Força recalculação de layout
            self.cards_content.adjustSize()
            if self._doc_cards:
                QTimer.singleShot(100, lambda: self.cards_scroll.ensureWidgetVisible(self._doc_cards[-1]))

            self._update_progress()
            self._update_finish_button()
        except Exception as e:
            logger.error("UI", f"Erro ao atualizar cards: {e}")

    def _update_progress(self):
        docs = self._documents
        total = len(docs)
        valid = sum(1 for d in docs if d.overall_status == "valid")
        if total == 0:
            self.lbl_progress.setText("")
        else:
            self.lbl_progress.setText(f"✅ {valid} / {total} documentos válidos")

    def _update_finish_button(self):
        docs = self._documents
        all_valid = len(docs) > 0 and all(d.overall_status == "valid" for d in docs)
        self.btn_finish.setEnabled(all_valid)

    def _do_scan(self):
        # Feedback visual instantâneo (PI-01)
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("⌛  Iniciando...")
        QApplication.processEvents() # Força o Qt a redesenhar o botão imediatamente

        try:
            settings = self.app.settings
            scanner_name = settings.get("scanner_name", "")
            
            msg_log = f"=== BOTÃO SCAN CLICADO === (Scanner: {scanner_name or 'Padrão/Simulador'})"
            logger.scanner(msg_log)

            self._scan_timeout = QTimer(self)
            self._scan_timeout.setSingleShot(True)
            self._scan_timeout.timeout.connect(self._on_scan_timeout)
            self._scan_timeout.start(45000) # 45s para scanners lentos

            def on_done(img, err):
                self._scan_result_signal.emit((img, err))

            def on_status(msg):
                QTimer.singleShot(0, lambda: self.btn_scan.setText(f"⌛  {msg}"))

            self.engine.scan(scanner_name, on_done, on_status)
        except Exception as e:
            logger.error("UI", f"Erro ao disparar scan: {e}")
            self.btn_scan.setEnabled(True)
            self.btn_scan.setText("📷   Escanear")

    def _handle_scan_result(self, result):
        if not self.isVisible() or not hasattr(self, "btn_scan"):
            return 
            
        if hasattr(self, "_scan_timeout") and self._scan_timeout:
            self._scan_timeout.stop()
            
        img, err = result
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("📷   Escanear")
        
        if err:
            logger.error("Scanner", f"Erro no UnifiedScanScreen: {err}")
            QMessageBox.critical(self, "Erro no Scanner", f"Falha ao digitalizar:\n{err}")
            return
            
        if img:
            logger.info("Scanner", "Imagem recebida com sucesso. Iniciando captura...")
            self._on_image_captured(img)
        else:
            logger.warning("Scanner", "Scan finalizado sem imagem.")

    def _on_scan_timeout(self):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("📷   Escanear")
        logger.warning("Scanner", "Timeout de 45s atingido na UI.")
        QMessageBox.warning(self, "Scanner Lento", "O scanner não respondeu no tempo esperado.\nVerifique se ele está ligado ou se há papel preso.")

    def _do_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Arquivo", "", "Suportados (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.pdf)"
        )
        if file_path:
            logger.scanner(f"Importando: {file_path}")
            try:
                if file_path.lower().endswith(".pdf"):
                    doc = fitz.open(file_path)
                    for page in doc:
                        pix = page.get_pixmap(dpi=200)
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        self._on_image_captured(img)
                    doc.close()
                else:
                    img = Image.open(file_path)
                    self._on_image_captured(img)
            except Exception as e:
                logger.error("Import", f"Falha ao importar: {e}")
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir o arquivo:\n{e}")

    def _on_image_captured(self, img):
        if not img: return
        try:
            logger.info("Vision", "Processando e otimizando imagem...")
            # Limpeza e correção básica
            p_img, _ = vision_processor.process_smart_capture(img)
            p_img = scan_module.optimize_image(p_img)
            p_img = vision_processor.auto_rotate_document(p_img)

            # Cria dado do documento e adiciona à transação
            doc_data = DocumentData(image=p_img)
            self._documents.append(doc_data)
            logger.info("Transaction", f"Documento adicionado à transação. Total: {len(self._documents)}")
            
            # Atualiza interface
            self._refresh_cards()

            doc_index = len(self._documents) - 1
            if doc_index < len(self._doc_cards):
                self._doc_cards[doc_index].show_ai_overlay()

            self.lbl_status.setText("🤖 Analisando documento com IA...")
            self.btn_scan.setEnabled(False)
            self.btn_import.setEnabled(False)

            def run_ai():
                try:
                    logger.info("AI", f"Solicitando análise para o documento #{doc_index}...")
                    data = ai_extractor.extract_and_classify(p_img)
                    self._ai_result_signal.emit(doc_index, data)
                except Exception as ex:
                    logger.error("AI", f"Erro na análise de IA: {ex}")
                    self._ai_result_signal.emit(doc_index, {"error": str(ex)})

            threading.Thread(target=run_ai, daemon=True).start()
            
        except Exception as e:
            logger.error("UI", f"Erro fatal ao processar captura: {e}")
            self.btn_scan.setEnabled(True)
            self.btn_import.setEnabled(True)
            QMessageBox.critical(self, "Erro Interno", f"Falha ao processar imagem:\n{e}")

    def _handle_ai_result(self, doc_index: int, ai_data: dict):
        if not self.isVisible() or not hasattr(self, "btn_scan"):
            return
            
        self.btn_scan.setEnabled(True)
        self.btn_import.setEnabled(True)
        self.lbl_status.setText("✅ Análise finalizada.")
        
        if doc_index < len(self._doc_cards):
            self._doc_cards[doc_index].hide_ai_overlay()

        if doc_index < len(self._documents):
            try:
                doc_data = self._documents[doc_index]
                # Valida extração e checklist
                updated_doc = validate_document(ai_data, doc_data.image)
                self._documents[doc_index] = updated_doc
                
                logger.success("AI", f"Fim da análise Doc #{doc_index}: {updated_doc.doc_type}")
                self.lbl_status.setText(f"✅ Identificado: {get_doc_type_label(updated_doc.doc_type)}")
                self._refresh_cards()
            except Exception as e:
                logger.error("Validator", f"Erro no pós-processamento da IA: {e}")
                self._refresh_cards()

    def _rotate_doc(self, index: int, angle: int):
        if 0 <= index < len(self._documents):
            doc = self._documents[index]
            if doc.image:
                doc.image = doc.image.rotate(angle, expand=True)
                self._refresh_cards()

    def _delete_doc(self, index: int):
        if 0 <= index < len(self._documents):
            self._documents.pop(index)
            self._refresh_cards()

    def _inspect_doc(self, index: int):
        if index >= len(self._documents): return
        try:
            from ui.screens.doc_inspector import DocInspector
            inspector = DocInspector(self, self._documents[index])
            inspector.exec()
            self._refresh_cards()
        except Exception as e:
            logger.error("UI", f"Erro ao abrir inspetor: {e}")

    def _finalizar(self):
        if not self._documents: return
        self.transaction.etapa_atual_index = self.transaction.total_etapas
        self.app.show_result(self.transaction)
