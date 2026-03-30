"""
result_screen.py - Tela de auditoria humana e resultado (PySide6).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QPushButton, QMessageBox,
)

from core.pdf_generator import gerar_pdf
from core.transaction import Transaction
from ui.qt_styles import COLORS

if TYPE_CHECKING:
    from ui.app import App


def _apply_date_mask_qt(entry: QLineEdit, text: str):
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


def _apply_auth_mask_qt(entry: QLineEdit, text: str):
    digits = "".join(c for c in text if c.isdigit())[:15]
    blocks = [digits[i:i+3] for i in range(0, len(digits), 3)]
    masked = ".".join(blocks)
    if text != masked:
        entry.blockSignals(True)
        entry.setText(masked)
        entry.setCursorPosition(len(masked))
        entry.blockSignals(False)


class ResultScreen(QWidget):
    def __init__(self, app: "App", transaction: Transaction, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.transacao = transaction
        self._build()
        QTimer.singleShot(100, self._show_manual_input_form)

    def _build(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(40, 32, 40, 32)
        self._layout.setSpacing(0)

        lbl_title = QLabel("Auditoria Humana")
        lbl_title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {COLORS['text_primary']};")
        self._layout.addWidget(lbl_title)

        self._header_sub = QLabel("Realize a conferência manual dos documentos e insira os dados da transação.")
        self._header_sub.setFont(QFont("Segoe UI", 13))
        self._header_sub.setStyleSheet(f"color: {COLORS['text_label']};")
        self._layout.addWidget(self._header_sub)

        self.center = QFrame()
        self.center.setObjectName("card")
        self.center_layout = QVBoxLayout(self.center)
        self.center_layout.setContentsMargins(24, 24, 24, 24)
        self._layout.addWidget(self.center, stretch=1)

    def _clear_center(self):
        while self.center_layout.count():
            item = self.center_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_approved(self, autorizacao: str, data: str):
        self._header_sub.setText("Documentação salva com sucesso.")
        self._clear_center()
        self.center_layout.setAlignment(Qt.AlignCenter)

        lbl_icon = QLabel("✅")
        lbl_icon.setFont(QFont("Segoe UI Emoji", 64))
        lbl_icon.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(lbl_icon)

        lbl_ok = QLabel("Documentação Validada!")
        lbl_ok.setFont(QFont("Segoe UI", 22, QFont.Bold))
        lbl_ok.setStyleSheet(f"color: {COLORS['success']};")
        lbl_ok.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(lbl_ok)

        info = QFrame()
        info.setStyleSheet("background-color: #0A2210; border-radius: 10px;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(24, 12, 24, 12)

        lbl_auth = QLabel(f"🔖  Autorização: {autorizacao}")
        lbl_auth.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_auth.setStyleSheet(f"color: {COLORS['success']};")
        info_layout.addWidget(lbl_auth)

        lbl_date = QLabel(f"📅  Data: {data}")
        lbl_date.setFont(QFont("Segoe UI", 13))
        lbl_date.setStyleSheet(f"color: {COLORS['success']};")
        info_layout.addWidget(lbl_date)

        self.center_layout.addWidget(info)

        btn_new = QPushButton("Nova Transação")
        btn_new.setObjectName("btn_secondary")
        btn_new.setFont(QFont("Segoe UI", 15, QFont.Bold))
        btn_new.setFixedSize(240, 50)
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self.app.show_home)
        self.center_layout.addWidget(btn_new, alignment=Qt.AlignCenter)

    def _create_date_input(self, placeholder: str) -> QLineEdit:
        entry = QLineEdit()
        entry.setPlaceholderText(placeholder)
        entry.setFont(QFont("Segoe UI", 12))
        entry.setMaxLength(10)
        entry.textChanged.connect(lambda t: _apply_date_mask_qt(entry, t))
        return entry

    def _show_manual_input_form(self):
        self._header_sub.setText("Preencha os dados extraídos dos documentos para salvar no banco.")
        self._clear_center()
        
        # Cria um Scroll Area para caber tudo
        from PySide6.QtWidgets import QScrollArea, QGroupBox, QFormLayout, QGridLayout, QCheckBox
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        form_main_layout = QVBoxLayout(container)
        form_main_layout.setContentsMargins(10, 10, 20, 10)
        
        # --- GRUPO: Paciente ---
        gb_pac = QGroupBox("👤 Dados do Paciente")
        gb_pac.setFont(QFont("Segoe UI", 12, QFont.Bold))
        gb_pac.setStyleSheet(f"QGroupBox {{ color: {COLORS['accent']}; border: 1px solid #37474F; margin-top: 15px; padding-top: 15px; }} QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}")
        lo_pac = QFormLayout(gb_pac)
        
        self.entry_nome_pac = QLineEdit()
        self.entry_nome_pac.setFont(QFont("Segoe UI", 12))
        lo_pac.addRow("Nome Completo:", self.entry_nome_pac)
        
        self.entry_nasc = self._create_date_input("DD/MM/AAAA")
        self.entry_emissao_pac = self._create_date_input("DD/MM/AAAA")
        hb_datas_pac = QHBoxLayout()
        hb_datas_pac.addWidget(QLabel("Data Nascimento:"))
        hb_datas_pac.addWidget(self.entry_nasc)
        hb_datas_pac.addWidget(QLabel("  Data Emissão (Doc):"))
        hb_datas_pac.addWidget(self.entry_emissao_pac)
        lo_pac.addRow(hb_datas_pac)
        
        self.entry_rua = QLineEdit()
        self.entry_num = QLineEdit()
        hb_end = QHBoxLayout()
        hb_end.addWidget(self.entry_rua, stretch=3)
        hb_end.addWidget(QLabel("Nº:"))
        hb_end.addWidget(self.entry_num, stretch=1)
        lo_pac.addRow("Endereço (Rua):", hb_end)
        
        form_main_layout.addWidget(gb_pac)
        
        # --- GRUPO: Receita ---
        gb_rec = QGroupBox("📄 Receita Médica")
        gb_rec.setFont(QFont("Segoe UI", 12, QFont.Bold))
        gb_rec.setStyleSheet(f"QGroupBox {{ color: {COLORS['success']}; border: 1px solid #37474F; margin-top: 15px; padding-top: 15px; }} QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}")
        lo_rec = QFormLayout(gb_rec)
        
        self.entry_data_rec = self._create_date_input("DD/MM/AAAA")
        self.entry_crm = QLineEdit()
        self.entry_medico = QLineEdit()
        hb_rec1 = QHBoxLayout()
        hb_rec1.addWidget(QLabel("Data Receita:"))
        hb_rec1.addWidget(self.entry_data_rec)
        hb_rec1.addWidget(QLabel("  CRM:"))
        hb_rec1.addWidget(self.entry_crm)
        lo_rec.addRow(hb_rec1)
        
        self.chk_anticoncepcional = QCheckBox("É Anticoncepcional? (Validade 1 ano)")
        self.chk_anticoncepcional.setFont(QFont("Segoe UI", 11))
        lo_rec.addRow("Nome Médico:", self.entry_medico)
        lo_rec.addRow("", self.chk_anticoncepcional)
        
        form_main_layout.addWidget(gb_rec)
        
        # --- GRUPO: Responsável Legal ---
        gb_resp = QGroupBox("👨‍👩‍👧 Responsável Legal (Opcional)")
        gb_resp.setCheckable(True)
        gb_resp.setChecked(False)
        self.gb_resp = gb_resp
        gb_resp.setFont(QFont("Segoe UI", 12, QFont.Bold))
        gb_resp.setStyleSheet(f"QGroupBox {{ color: #FFB300; border: 1px solid #37474F; margin-top: 15px; padding-top: 15px; }} QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}")
        lo_resp = QFormLayout(gb_resp)
        
        self.entry_cpf_resp = QLineEdit()
        self.entry_nome_resp = QLineEdit()
        self.entry_emissao_resp = self._create_date_input("DD/MM/AAAA")
        self.chk_procuracao = QCheckBox("Possui Procuração?")
        
        hb_resp1 = QHBoxLayout()
        hb_resp1.addWidget(QLabel("CPF:"))
        hb_resp1.addWidget(self.entry_cpf_resp)
        hb_resp1.addWidget(QLabel("  Data Emissão:"))
        hb_resp1.addWidget(self.entry_emissao_resp)
        
        lo_resp.addRow(hb_resp1)
        lo_resp.addRow("Nome:", self.entry_nome_resp)
        lo_resp.addRow("", self.chk_procuracao)
        
        form_main_layout.addWidget(gb_resp)
        
        # --- GRUPO: Autorização PFPB ---
        gb_auth = QGroupBox("🔖 Autorização PFPB e Cupom")
        gb_auth.setFont(QFont("Segoe UI", 12, QFont.Bold))
        gb_auth.setStyleSheet(f"QGroupBox {{ color: {COLORS['btn_primary']}; border: 1px solid #37474F; margin-top: 15px; padding-top: 15px; }} QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}")
        lo_auth = QFormLayout(gb_auth)
        
        self.entry_auth = QLineEdit()
        self.entry_auth.setPlaceholderText("Ex: 111.222.333.444.555")
        self.entry_auth.setMaxLength(19)
        self.entry_auth.textChanged.connect(lambda t: _apply_auth_mask_qt(self.entry_auth, t))
        
        self.entry_data_venda = self._create_date_input("DD/MM/AAAA")
        self.entry_cupom = QLineEdit()
        
        lo_auth.addRow("Núm Autorização:", self.entry_auth)
        
        hb_auth1 = QHBoxLayout()
        hb_auth1.addWidget(QLabel("Data Venda:"))
        hb_auth1.addWidget(self.entry_data_venda)
        hb_auth1.addWidget(QLabel("  Cupom Fiscal:"))
        hb_auth1.addWidget(self.entry_cupom)
        lo_auth.addRow(hb_auth1)
        
        form_main_layout.addWidget(gb_auth)
        
        # Finaliza Scroll
        scroll.setWidget(container)
        self.center_layout.addWidget(scroll, stretch=1)
        
        # Botões de Ação Inferiores
        hb_btns = QHBoxLayout()
        
        btn_back = QPushButton("Voltar às Imagens")
        btn_back.setStyleSheet(f"background: transparent; color: {COLORS['text_label']}; border: 1px solid {COLORS['text_label']}; border-radius: 8px; font-weight: bold; padding: 10px;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(lambda: self.app.show_scan(self.transacao))
        hb_btns.addWidget(btn_back)
        
        btn_save = QPushButton("💾 Salvar no Banco e Concluir")
        btn_save.setObjectName("btn_green")
        btn_save.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_save.setFixedSize(280, 46)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #2E7D32; color: white; border: none; border-radius: 8px;")
        btn_save.clicked.connect(self._salvar_manual)
        hb_btns.addWidget(btn_save)
        
        self.center_layout.addLayout(hb_btns)

    def _salvar_manual(self):
        # 1. Obter CPF da transação
        cpf_paciente = self.transacao.etapas[0].cpf

        # 2. Dados Paciente
        nome_pac = self.entry_nome_pac.text().strip()
        rua_pac = self.entry_rua.text().strip()
        num_pac = self.entry_num.text().strip()
        nasc_pac = self.entry_nasc.text().strip()
        emiss_pac = self.entry_emissao_pac.text().strip()
        
        # 3. Dados Receita
        data_rec = self.entry_data_rec.text().strip()
        crm = self.entry_crm.text().strip()
        medico = self.entry_medico.text().strip()
        is_anti = 1 if self.chk_anticoncepcional.isChecked() else 0
        
        # 4. Dados Responsável (Opcional)
        usa_resp = self.gb_resp.isChecked()
        cpf_resp = self.entry_cpf_resp.text().strip()
        nome_resp = self.entry_nome_resp.text().strip()
        emiss_resp = self.entry_emissao_resp.text().strip()
        tem_proc = 1 if self.chk_procuracao.isChecked() else 0

        # 5. Dados Autorização
        auth = self.entry_auth.text().strip()
        data_venda = self.entry_data_venda.text().strip()
        cupom = self.entry_cupom.text().strip()

        # Validações Mínimas
        if not nome_pac or not data_rec or not auth or not data_venda:
            QMessageBox.warning(self, "Campos Obrigatórios", "Nome do Paciente, Data da Receita, Autorização e Data Venda são obrigatórios.")
            return

        if not re.match(r"^\d{3}\.\d{3}\.\d{3}\.\d{3}\.\d{3}$", auth):
            QMessageBox.critical(self, "Formato Inválido", "A Autorização deve ter 15 números (XXX.XXX.XXX.XXX.XXX).")
            return

        # Salvando no SQLite...
        try:
            from core.database import (
                get_current_company_id, upsert_paciente, upsert_responsavel, 
                insert_receita, insert_autorizacao, insert_arquivo_midia
            )
            
            company_id = get_current_company_id(self.app.settings)
            
            # Persiste Paciente
            upsert_paciente(cpf_paciente, company_id, nome_pac, rua_pac, num_pac, nasc_pac, emiss_pac)
            
            # Persiste Responsável (se marcado)
            if usa_resp and cpf_resp and nome_resp:
                upsert_responsavel(cpf_resp, cpf_paciente, company_id, nome_resp, emiss_resp, tem_proc)
                
            # Persiste Receita
            insert_receita(cpf_paciente, company_id, data_rec, crm, medico, is_anti)
            
            # Persiste Autorizacao
            auth_id = insert_autorizacao(cpf_paciente, company_id, auth, data_venda, cupom)

            # --- GERAÇÃO PDF ---
            out_folder = self.app.settings.get("output_folder", str(Path.home() / "Documents" / "DocPopular"))
            images = self.transacao.todas_imagens()
            
            # Mantemos 'gerar_pdf' gerando o PDF consolidado
            pdf_path = gerar_pdf(imagens=images, autorizacao=auth, data=data_venda, output_folder=out_folder)
            
            # Persiste Mídia Completa
            insert_arquivo_midia(company_id, "transacao_completa", auth_id, str(pdf_path))
            
            self.transacao.etapa_atual_index = self.transacao.total_etapas  # Conclui
            self._show_approved(auth, data_venda)
            
            try:
                if hasattr(os, 'startfile'):
                    os.startfile(pdf_path.parent)
            except Exception:
                pass
                
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível persistir no banco de dados ou gerar o PDF:\n{e}")
