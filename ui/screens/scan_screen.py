"""
scan_screen.py - Tela de digitalização com navegação por etapas (PySide6).
"""

import io
import threading
import fitz # PyMuPDF
from PIL import Image

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QScrollArea, QProgressBar,
    QDialog, QMessageBox, QFileDialog,
)

from core import scanner as scan_module
from core import vision_processor
from core import ai_extractor
from core.transaction import Transaction, criar_etapa_responsavel_legal
from core.cpf_manager import find_all_documents_by_cpf, save_cpf_documents, validate_cpf
from ui.qt_styles import COLORS
from ui.components.page_thumbnail import PageThumbnail, pil_to_qpixmap


class ScanScreen(QWidget):
    def __init__(self, app, transaction: Transaction, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.transaction = transaction
        self._thumb_widgets: list[PageThumbnail] = []
        self._last_cpf_check = ""
        self._build()
        self._refresh()
        # Pré-preenche CPF se já definido
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf and etapa.cpf:
            self.entry_cpf.blockSignals(True)
            self.entry_cpf.setText(etapa.cpf)
            self.entry_cpf.blockSignals(False)
            self._last_cpf_check = etapa.cpf

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 16)
        layout.setSpacing(0)

        # ── Cabeçalho ─────────────────────────────────────────────────────
        self.lbl_tipo = QLabel("")
        self.lbl_tipo.setFont(QFont("Segoe UI", 12))
        self.lbl_tipo.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(self.lbl_tipo)

        self.lbl_titulo = QLabel("")
        self.lbl_titulo.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.lbl_titulo.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(self.lbl_titulo)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setFont(QFont("Segoe UI", 13))
        self.lbl_desc.setStyleSheet(f"color: {COLORS['text_label']};")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # ── Campo CPF ─────────────────────────────────────────────────────
        self.cpf_frame = QWidget()
        cpf_row = QHBoxLayout(self.cpf_frame)
        cpf_row.setContentsMargins(0, 12, 0, 0)

        lbl_cpf = QLabel("Digite o CPF para continuar:")
        lbl_cpf.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_cpf.setStyleSheet(f"color: {COLORS['success']};")
        cpf_row.addWidget(lbl_cpf)

        self.entry_cpf = QLineEdit()
        self.entry_cpf.setPlaceholderText("000.000.000-00")
        self.entry_cpf.setFont(QFont("Segoe UI", 14))
        self.entry_cpf.setFixedSize(180, 32)
        self.entry_cpf.setMaxLength(14)
        self.entry_cpf.textChanged.connect(self._on_cpf_changed)
        cpf_row.addWidget(self.entry_cpf)

        self.lbl_cpf_error = QLabel("⚠️ CPF Inválido")
        self.lbl_cpf_error.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_cpf_error.setStyleSheet(f"color: {COLORS['error']};")
        self.lbl_cpf_error.hide()
        cpf_row.addWidget(self.lbl_cpf_error)

        cpf_row.addStretch(1)
        self.cpf_frame.hide()
        layout.addWidget(self.cpf_frame)

        # ── Barra de progresso ────────────────────────────────────────────
        prog_frame = QWidget()
        prog_layout = QVBoxLayout(prog_frame)
        prog_layout.setContentsMargins(0, 12, 0, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        prog_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setFont(QFont("Segoe UI", 11))
        self.lbl_progress.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignRight)
        prog_layout.addWidget(self.lbl_progress)

        layout.addWidget(prog_frame)

        # ── Área de thumbs ────────────────────────────────────────────────
        thumb_container = QFrame()
        thumb_container.setObjectName("card")
        thumb_inner = QVBoxLayout(thumb_container)
        thumb_inner.setContentsMargins(8, 12, 8, 12)

        lbl_pages = QLabel("Páginas digitalizadas:")
        lbl_pages.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_pages.setStyleSheet(f"color: {COLORS['text_secondary']};")
        thumb_inner.addWidget(lbl_pages)

        # Scroll horizontal
        self.thumb_scroll = QScrollArea()
        self.thumb_scroll.setWidgetResizable(True)
        self.thumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.thumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thumb_scroll.setStyleSheet("background: transparent; border: none;")
        self.thumb_scroll.setMinimumHeight(700)

        self.thumb_content = QWidget()
        self.thumb_layout = QHBoxLayout(self.thumb_content)
        self.thumb_layout.setContentsMargins(8, 8, 8, 8)
        self.thumb_layout.setSpacing(20)
        self.thumb_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.thumb_scroll.setWidget(self.thumb_content)

        thumb_inner.addWidget(self.thumb_scroll, stretch=1)
        layout.addWidget(thumb_container, stretch=1)

        # Empty label
        self.lbl_empty = QLabel("Nenhuma página digitalizada ainda.")
        self.lbl_empty.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_empty.setStyleSheet(f"color: #37474F;")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_layout.addWidget(self.lbl_empty)

        # ── Controles ─────────────────────────────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.btn_prev = QPushButton("◀   Etapa Anterior")
        self.btn_prev.setObjectName("btn_secondary")
        self.btn_prev.setFont(QFont("Segoe UI", 13))
        self.btn_prev.setFixedHeight(44)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self._voltar_etapa)
        controls.addWidget(self.btn_prev, stretch=1)

        self.btn_scan = QPushButton("📷   Escanear Página")
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

        self.btn_next = QPushButton("Próxima Etapa  ▶")
        self.btn_next.setObjectName("btn_green")
        self.btn_next.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_next.setFixedHeight(44)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._pergunta_mais_paginas)
        controls.addWidget(self.btn_next, stretch=1)

        layout.addLayout(controls)

    # ── Atualização do estado visual ──────────────────────────────────────

    def _refresh(self):
        t = self.transaction
        etapa = t.etapa_atual

        self.lbl_tipo.setText(f"🏥  {t.nome_tipo}  •  Etapa {t.etapa_atual_index + 1} de {t.total_etapas}")
        self.lbl_titulo.setText(f"{etapa.icone}  {etapa.titulo}")
        self.lbl_desc.setText(etapa.descricao)

        progresso = int((t.etapa_atual_index / t.total_etapas) * 100)
        self.progress_bar.setValue(progresso)
        self.lbl_progress.setText(f"Etapa {t.etapa_atual_index + 1} / {t.total_etapas}")

        # CPF sync
        cpf_no_campo = self.entry_cpf.text()
        if etapa.require_cpf and cpf_no_campo and len(cpf_no_campo) == 14 and validate_cpf(cpf_no_campo):
            etapa.cpf = cpf_no_campo

        if etapa.require_cpf:
            self.cpf_frame.show()
            if etapa.cpf and not self.entry_cpf.text():
                self.entry_cpf.blockSignals(True)
                self.entry_cpf.setText(etapa.cpf)
                self.entry_cpf.blockSignals(False)
        else:
            self.cpf_frame.hide()

        self._render_thumbs(etapa.imagens)
        self._valida_estado_botoes()

    def _valida_estado_botoes(self):
        etapa = self.transaction.etapa_atual
        cpf_valido = True

        if etapa.require_cpf:
            cpf_texto = self.entry_cpf.text()
            is_completo = len(cpf_texto) == 14
            is_algoritmo_ok = validate_cpf(cpf_texto)
            cpf_valido = is_completo and is_algoritmo_ok
            self.lbl_cpf_error.setVisible(is_completo and not is_algoritmo_ok)

        self.btn_prev.setEnabled(self.transaction.etapa_atual_index > 0)

        if cpf_valido:
            self.btn_scan.setEnabled(True)
            self.btn_import.setEnabled(True)
            self.btn_next.setEnabled(etapa.tem_imagens)
        else:
            self.btn_scan.setEnabled(False)
            self.btn_import.setEnabled(False)
            self.btn_next.setEnabled(False)

    def _render_thumbs(self, imagens):
        # Limpa
        for w in self._thumb_widgets:
            self.thumb_layout.removeWidget(w)
            w.deleteLater()
        self._thumb_widgets.clear()

        if self.lbl_empty:
            self.lbl_empty.setVisible(not imagens)

        if not imagens:
            return

        for i, img in enumerate(imagens):
            card = PageThumbnail(i, img)
            card.delete_requested.connect(self._remover_imagem)
            card.rotate_left_requested.connect(lambda idx: self._girar_imagem(idx, 90))
            card.rotate_right_requested.connect(lambda idx: self._girar_imagem(idx, -90))
            self.thumb_layout.addWidget(card)
            self._thumb_widgets.append(card)

    # ── CPF ────────────────────────────────────────────────────────────────

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

        self._valida_estado_botoes()

        if len(masked) < 14:
            self._last_cpf_check = ""

        if len(masked) == 14 and validate_cpf(masked) and self._last_cpf_check != masked:
            self._last_cpf_check = masked
            self._verificar_documento_existente(masked)

    def _verificar_documento_existente(self, cpf: str):
        paths_existentes = find_all_documents_by_cpf(cpf, self.app.settings)
        if paths_existentes:
            dialog = FoundDocumentDialog(self, cpf, str(paths_existentes[0]))
            dialog.exec()
            if dialog.dialog_result == "use":
                try:
                    rotation = dialog.rotation_angle
                    for p in paths_existentes:
                        img = Image.open(p)
                        if rotation:
                            img = img.rotate(-rotation, expand=True)
                        self.transaction.etapa_atual.adicionar_imagem(img.copy())
                    self._valida_estado_botoes()
                    self._refresh()
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Não foi possível carregar o arquivo:\n{e}")

    # ── Rotação e Exclusão ────────────────────────────────────────────────

    def _girar_imagem(self, index: int, angulo: int):
        try:
            imagens = self.transaction.etapa_atual.imagens
            if 0 <= index < len(imagens):
                rotated = imagens[index].rotate(angulo, expand=True)
                imagens[index] = rotated
                self._refresh()
        except Exception as e:
            print(f"[ScanScreen] Erro ao girar: {e}")

    def _remover_imagem(self, index: int):
        self.transaction.etapa_atual.remover_imagem(index)
        self._last_cpf_check = ""
        self._valida_estado_botoes()
        self._refresh()

    # ── Ações de Scan ─────────────────────────────────────────────────────

    def _do_scan(self):
        settings = self.app.settings
        scanner_name = settings.get("scanner_name", "")
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("⌛  Escaneando...")

        def run():
            img, err = None, None
            try:
                if scanner_name:
                    img, err = scan_module.scan_page(scanner_name)
                
                if img is None and not err:
                    # Tenta com diálogo se não houver scanner fixo ou o fixo falhou sem erro explícito
                    img, err = scan_module.scan_with_dialog()
            except Exception as e:
                err = f"Erro na thread de scan: {e}"

            # Garante que o handler seja executado na thread principal
            QTimer.singleShot(0, lambda: self._on_scan_finished(img, err))

        threading.Thread(target=run, daemon=True).start()

    def _on_scan_finished(self, img, err):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("📷   Escanear Página")
        
        if err:
            QMessageBox.critical(self, "Erro no Scanner", f"Falha ao digitalizar:\n{err}")
            return
            
        if img:
            self._on_image_captured(img)

    def _do_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Arquivo",
            "", "Todos os Suportados (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.pdf);;Imagens (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;PDF (*.pdf);;Todos (*.*)"
        )
        if file_path:
            try:
                if file_path.lower().endswith(".pdf"):
                    # Abre o PDF e converte cada página para imagem
                    doc = fitz.open(file_path)
                    for page in doc:
                        pix = page.get_pixmap(dpi=200)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        self._on_image_captured(img)
                    doc.close()
                else:
                    img = Image.open(file_path)
                    self._on_image_captured(img)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível abrir o arquivo:\n{e}")

    def _on_image_captured(self, img):
        """
        Chamado quando uma imagem é capturada do scanner ou importada.
        Mostra a imagem na tela imediatamente e envia para a IA em background.
        """
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("📷   Escanear Página")

        if not img:
            return

        # 1. Processamento Inteligente (Vision) recortar documento do fundo
        p_img, _ = vision_processor.process_smart_capture(img)

        # Otimização e Rotação
        p_img = scan_module.optimize_image(p_img)
        p_img = vision_processor.auto_rotate_document(p_img)

        # 2. Adiciona imagem na tela IMEDIATAMENTE (antes da IA)
        self.transaction.etapa_atual.adicionar_imagem(p_img)
        self._refresh()

        # 3. Mostra overlay de "IA Analisando..." no thumbnail recém-adicionado
        img_index = len(self.transaction.etapa_atual.imagens) - 1
        if img_index < len(self._thumb_widgets):
            self._thumb_widgets[img_index].show_ai_overlay()

        # 4. IA analisa o documento em background
        self.lbl_progress.setText("🤖 Analisando documento com IA...")
        self.btn_scan.setEnabled(False)
        self.btn_import.setEnabled(False)

        def run_ai():
            try:
                data = ai_extractor.extract_document_data(p_img)
            except Exception as e:
                data = {"error": f"Crash na thread de IA: {e}"}
            
            # Garante que o handler seja executado na thread principal para mexer na UI
            QTimer.singleShot(0, lambda: self._handle_ai_result(p_img, data, img_index))

        threading.Thread(target=run_ai, daemon=True).start()

    def _handle_ai_result(self, p_img, data, img_index):
        try:
            self.btn_scan.setEnabled(True)
            self.btn_scan.setText("📷   Escanear Página")
            self.btn_import.setEnabled(True)

            # Remove overlay de IA do thumbnail (independente de sucesso ou erro)
            if img_index < len(self._thumb_widgets):
                self._thumb_widgets[img_index].hide_ai_overlay()

            if "error" in data:
                QMessageBox.warning(self, "IA", f"Erro na análise: {data['error']}")
                tipo_face = "COMPLETO"
            else:
                tipo_face = data.get("tipo_face", "COMPLETO").upper()

            if tipo_face in ["FRENTE", "VERSO"]:
                if not getattr(self, "_pending_half", None):
                    # Primeira metade: imagem já está na tela, guarda referência
                    self._pending_half = p_img
                    self._pending_half_index = img_index
                    msg = "Frente (Foto)" if tipo_face == "FRENTE" else "Verso (CPF)"
                    esperado = "Verso" if tipo_face == "FRENTE" else "Frente"
                    self.lbl_progress.setText(f"📸 {msg} detectado. Escaneie o {esperado} do documento.")
                    QMessageBox.information(self, "Aviso", f"Parece que você informou apenas o {msg}.\nPara unificar o documento, importe ou escaneie o lado restante ({esperado}).")
                    self._valida_estado_botoes()
                    return
                else:
                    # Segunda metade: combina as duas
                    p1 = self._pending_half
                    p2 = p_img

                    w = max(p1.width, p2.width)
                    h = p1.height + p2.height
                    combined = Image.new("RGB", (w, h), color=(255, 255, 255))
                    combined.paste(p1, (0, 0))
                    combined.paste(p2, (0, p1.height))

                    # Substitui a primeira metade pela imagem combinada
                    imagens = self.transaction.etapa_atual.imagens
                    half_idx = self._pending_half_index
                    if half_idx < len(imagens):
                        imagens[half_idx] = combined

                    # Remove a segunda metade (a que acabou de ser adicionada)
                    if img_index < len(imagens) and img_index != half_idx:
                        self.transaction.etapa_atual.remover_imagem(img_index)

                    self._pending_half = None
                    self._pending_half_index = None
                    self.lbl_progress.setText("✅ Faces unificadas com sucesso!")
            else:
                # Completo (ou desconhecido/erro)
                self._pending_half = None
                self._pending_half_index = None
                if "cpf" in data and data["cpf"]:
                    self.lbl_progress.setText("✅ Documento completo analisado.")
                else:
                    self.lbl_progress.setText("")

            # Atualiza o CPF se a IA tiver encontrado (não sobrescreve se já tiver)
            current_cpf = self.entry_cpf.text().strip().replace(".", "").replace("-", "")
            extracted_cpf = data.get("cpf")

            if not current_cpf and extracted_cpf:
                raw_cpf = str(extracted_cpf).replace(".", "").replace("-", "").replace("/", "")
                if raw_cpf.isdigit() and len(raw_cpf) >= 11:
                    self._update_cpf_from_ai(raw_cpf[:11])

            self._valida_estado_botoes()
            self._refresh()
        except Exception as e:
            print(f"[ScanScreen] Erro ao tratar resultado da IA: {e}")
            self._refresh()
        finally:
            # Garante remoção de overlays órfãos em todas as miniaturas após a IA terminar
            for w in self._thumb_widgets:
                w.hide_ai_overlay()

    def _update_cpf_from_ai(self, cpf_str):
        self.entry_cpf.setText(cpf_str)
        self.lbl_progress.setText("✅ CPF Extraído via IA")
        # Força a atualização da máscara e validação
        self._on_cpf_changed(cpf_str)

    # ── Navegação de Etapas ───────────────────────────────────────────────

    def _pergunta_mais_paginas(self):
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf:
            cpf_salvo = self.entry_cpf.text()
            etapa.cpf = cpf_salvo
            try:
                if etapa.tem_imagens:
                    save_cpf_documents(cpf_salvo, etapa.imagens, self.app.settings)
            except Exception as e:
                print(f"[ScanScreen] Falha ao salvar doc: {e}")

        dialog = MorePagesDialog(self, etapa.titulo)
        dialog.exec()
        if dialog.dialog_result == "next":
            if etapa.require_cpf:
                self._abrir_wizard_validacao()
            else:
                self._avancar_etapa()

    def _abrir_wizard_validacao(self):
        from ui.screens.doc_validation_wizard import DocValidationWizard

        etapa = self.transaction.etapa_atual
        wizard = DocValidationWizard(self, etapa.cpf)
        wizard.exec()

        if wizard.resultado == "aprovado":
            etapa.validacao_doc = wizard.dados_validacao
            if etapa.id == "id_paciente" and wizard.dados_validacao.get("is_menor", False):
                self.transaction.is_menor_idade = True
                self.transaction.idade_paciente = wizard.dados_validacao.get("idade", 0)
                if not self.transaction.ja_tem_etapa("id_responsavel"):
                    self.transaction.inserir_etapa_apos_atual(criar_etapa_responsavel_legal())
            if wizard.dados_validacao.get("is_idoso", False):
                self.transaction.is_idoso = True
                self.transaction.idade_paciente = wizard.dados_validacao.get("idade", 0)
            self._avancar_etapa()
        elif wizard.resultado == "refazer":
            etapa.imagens.clear()
            etapa.validacao_doc = {}
            self._refresh()
            QMessageBox.information(self, "Refazer Digitalização", "As imagens foram removidas. Digitalize novamente.")
        elif wizard.resultado == "cancelar":
            resp = QMessageBox.question(self, "Cancelar Transação",
                "Tem certeza que deseja cancelar toda a transação?\nTodas as imagens serão perdidas.")
            if resp == QMessageBox.StandardButton.Yes:
                self.app.show_home()

    def _avancar_etapa(self):
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf:
            etapa.cpf = self.entry_cpf.text()
        self._last_cpf_check = ""
        self.entry_cpf.blockSignals(True)
        self.entry_cpf.setText("")
        self.entry_cpf.blockSignals(False)

        tem_proxima = self.transaction.avancar_etapa()
        if tem_proxima:
            self._refresh()
        else:
            self.app.show_result(self.transaction)

    def _voltar_etapa(self):
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf:
            cpf_atual = self.entry_cpf.text()
            if cpf_atual and validate_cpf(cpf_atual):
                etapa.cpf = cpf_atual

        self.entry_cpf.blockSignals(True)
        self.entry_cpf.setText("")
        self.entry_cpf.blockSignals(False)

        if self.transaction.voltar_etapa():
            etapa_destino = self.transaction.etapa_atual
            self._last_cpf_check = etapa_destino.cpf or ""
            self._refresh()


# ── Diálogo "Mais páginas?" ───────────────────────────────────────────────

class MorePagesDialog(QDialog):
    def __init__(self, parent, etapa_titulo: str):
        super().__init__(parent)
        self.dialog_result = None
        self.setWindowTitle("")
        self.setFixedSize(420, 200)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {COLORS['bg_main']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        lbl_q = QLabel("Mais páginas?")
        lbl_q.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        lbl_q.setStyleSheet(f"color: {COLORS['text_primary']};")
        lbl_q.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_q)

        lbl_sub = QLabel(f"Existem mais páginas para «{etapa_titulo}»?")
        lbl_sub.setFont(QFont("Segoe UI", 12))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_label']};")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)
        layout.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_sim = QPushButton("✔   Sim, há mais páginas")
        btn_sim.setObjectName("btn_secondary")
        btn_sim.setFixedWidth(180)
        btn_sim.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sim.clicked.connect(self._sim)
        btn_row.addWidget(btn_sim)

        btn_nao = QPushButton("▶   Não, próxima etapa")
        btn_nao.setObjectName("btn_green")
        btn_nao.setFixedWidth(180)
        btn_nao.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nao.clicked.connect(self._nao)
        btn_row.addWidget(btn_nao)

        layout.addLayout(btn_row)

    def _sim(self):
        self.dialog_result = "more"
        self.accept()

    def _nao(self):
        self.dialog_result = "next"
        self.accept()


# ── Diálogo "Documento Encontrado" ────────────────────────────────────────

class FoundDocumentDialog(QDialog):
    def __init__(self, parent, cpf: str, image_path: str):
        super().__init__(parent)
        self.dialog_result = "new"
        self.rotation_angle = 0
        self._zoom_factor = 1.0
        self._original_image = None

        self.setWindowTitle("Documento Encontrado")
        self.setFixedSize(700, 750)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {COLORS['bg_main']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Título
        lbl_title = QLabel("Documento Já Existe")
        lbl_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['accent']};")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(f"Foi encontrado um documento salvo para o CPF {cpf}.")
        lbl_sub.setFont(QFont("Segoe UI", 13))
        lbl_sub.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)

        # Preview
        preview_frame = QFrame()
        preview_frame.setObjectName("card")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: white; border-radius: 6px;")
        preview_layout.addWidget(self.preview_label, stretch=1)

        # Botões de rotação dentro do frame
        rot_row = QHBoxLayout()
        btn_rl = QPushButton("↺  Girar Esq")
        btn_rl.setObjectName("btn_secondary")
        btn_rl.setFixedHeight(36)
        btn_rl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rl.clicked.connect(self._rotate_left)
        rot_row.addWidget(btn_rl)
        rot_row.addStretch(1)
        btn_rr = QPushButton("↻  Girar Dir")
        btn_rr.setObjectName("btn_secondary")
        btn_rr.setFixedHeight(36)
        btn_rr.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rr.clicked.connect(self._rotate_right)
        rot_row.addWidget(btn_rr)
        preview_layout.addLayout(rot_row)

        layout.addWidget(preview_frame, stretch=1)

        # Dica
        lbl_hint = QLabel("🔍 Use a rodinha do mouse para zoom")
        lbl_hint.setFont(QFont("Segoe UI", 11))
        lbl_hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_hint)

        # Pergunta + Botões
        lbl_q = QLabel("O que deseja fazer?")
        lbl_q.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_q.setStyleSheet(f"color: {COLORS['text_primary']};")
        lbl_q.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_q)

        btn_row = QHBoxLayout()
        btn_use = QPushButton("📄  Usar Recente Salvo")
        btn_use.setObjectName("btn_secondary")
        btn_use.setFixedSize(220, 44)
        btn_use.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_use.clicked.connect(self._use)
        btn_row.addWidget(btn_use)

        btn_new = QPushButton("📸  Fazer Nova e Substituir")
        btn_new.setObjectName("btn_green")
        btn_new.setFixedSize(220, 44)
        btn_new.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self._new)
        btn_row.addWidget(btn_new)
        layout.addLayout(btn_row)

        # Load image
        try:
            self._original_image = Image.open(image_path)
            self._render_preview()
        except Exception:
            self.preview_label.setText("Não foi possível carregar a prévia.")

    def _render_preview(self):
        if self._original_image is None:
            return
        img = self._get_rotated()
        if img is None:
            return
            
        pixmap = pil_to_qpixmap(img)
        # Scala para caber no label
        label_size = self.preview_label.size()
        if label_size.width() < 50:
            max_w, max_h = 650, 500
        else:
            max_w, max_h = label_size.width() - 16, label_size.height() - 16
        
        scaled = pixmap.scaled(
            int(max_w * self._zoom_factor),
            int(max_h * self._zoom_factor),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)

    def _get_rotated(self):
        if self._original_image is None:
            return None
        if self.rotation_angle == 0:
            return self._original_image
        return self._original_image.rotate(-self.rotation_angle, expand=True)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_factor = min(self._zoom_factor * 1.15, 5.0)
        else:
            self._zoom_factor = max(self._zoom_factor / 1.15, 0.3)
        self._render_preview()

    def _rotate_left(self):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self._render_preview()

    def _rotate_right(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._render_preview()

    def _use(self):
        self.dialog_result = "use"
        self.accept()

    def _new(self):
        self.dialog_result = "new"
        self.accept()
