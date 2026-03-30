"""
doc_validation_wizard.py - Wizard de validação do documento de identidade (PySide6).
Guia o operador por 5 passos de verificação via checklist manual.
"""

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QLineEdit, QPushButton, QProgressBar, QWidget,
)

from ui.qt_styles import COLORS


def _verificar_validade_documento(data_emissao: date, max_anos: int = 10) -> bool:
    hoje = date.today()
    anos_passados = hoje.year - data_emissao.year
    if (hoje.month, hoje.day) < (data_emissao.month, data_emissao.day):
        anos_passados -= 1
    return anos_passados <= max_anos


def _calcular_idade(data_nasc: date) -> int:
    hoje = date.today()
    idade = hoje.year - data_nasc.year
    if (hoje.month, hoje.day) < (data_nasc.month, data_nasc.day):
        idade -= 1
    return idade


def _apply_date_mask_qt(line_edit: QLineEdit, text: str):
    """Aplica máscara DD/MM/AAAA num QLineEdit."""
    digits = "".join(c for c in text if c.isdigit())[:8]
    masked = ""
    for i, d in enumerate(digits):
        if i in [2, 4]:
            masked += "/"
        masked += d

    if text != masked:
        line_edit.blockSignals(True)
        line_edit.setText(masked)
        line_edit.setCursorPosition(len(masked))
        line_edit.blockSignals(False)


class DocValidationWizard(QDialog):
    TOTAL_PASSOS = 5

    def __init__(self, parent, cpf_digitado: str):
        super().__init__(parent)
        self.cpf_digitado = cpf_digitado
        self.resultado: Optional[str] = None
        self.motivos_reprovacao: list = []
        self.dados_validacao: dict = {}
        self._passo_atual = 0

        self.setWindowTitle("Validação do Documento")
        self.setFixedSize(560, 500)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {COLORS['bg_main']};")

        self._build()
        self._mostrar_passo(0)

    def _build(self):
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(24, 20, 24, 20)
        self._root_layout.setSpacing(8)

        # Cabeçalho
        self.lbl_titulo = QLabel("")
        self.lbl_titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.lbl_titulo.setStyleSheet(f"color: {COLORS['text_primary']};")
        self._root_layout.addWidget(self.lbl_titulo)

        self.lbl_passo = QLabel("")
        self.lbl_passo.setFont(QFont("Segoe UI", 11))
        self.lbl_passo.setStyleSheet(f"color: {COLORS['text_muted']};")
        self._root_layout.addWidget(self.lbl_passo)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setMaximum(100)
        self.progress.setTextVisible(False)
        self._root_layout.addWidget(self.progress)

        # Conteúdo (dinâmico)
        self.content_frame = QWidget()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self.content_frame, stretch=1)

        # Rodapé
        self.footer = QWidget()
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self.footer)

    def _mostrar_passo(self, passo: int):
        self._passo_atual = passo
        self._limpar_conteudo()
        self._limpar_footer()
        self.progress.setValue(int((passo + 1) / self.TOTAL_PASSOS * 100))
        self.progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: #1E88E5; border-radius: 3px; }}")
        self.lbl_passo.setText(f"Passo {passo + 1} de {self.TOTAL_PASSOS}")

        [
            self._passo_legibilidade,
            self._passo_data_emissao,
            self._passo_cpf,
            self._passo_idade,
            self._passo_assinatura,
        ][passo]()

    # ── Passo 1: Legibilidade ─────────────────────────────────────────────

    def _passo_legibilidade(self):
        self.lbl_titulo.setText("📋  Legibilidade e Foto")

        lbl = QLabel("Verifique o documento digitalizado:")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.content_layout.addWidget(lbl)

        checklist = QFrame()
        checklist.setObjectName("card")
        cl_layout = QVBoxLayout(checklist)
        cl_layout.setContentsMargins(16, 12, 16, 12)
        for item in [
            "✔  O documento está legível (texto e dados visíveis)",
            "✔  O documento possui foto do paciente",
            "✔  A imagem não está cortada ou desfocada",
        ]:
            lbl_item = QLabel(item)
            lbl_item.setFont(QFont("Segoe UI", 13))
            lbl_item.setStyleSheet(f"color: {COLORS['success']};")
            cl_layout.addWidget(lbl_item)
        self.content_layout.addWidget(checklist)

        lbl_q = QLabel("O documento atende a todos os critérios acima?")
        lbl_q.setFont(QFont("Segoe UI", 13))
        lbl_q.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.content_layout.addWidget(lbl_q)
        self.content_layout.addStretch(1)

        self._botoes_sim_nao(
            on_sim=lambda: self._mostrar_passo(1),
            on_nao=lambda: self._reprovar("Documento ilegível ou sem foto"),
        )

    # ── Passo 2: Data de Emissão ──────────────────────────────────────────

    def _passo_data_emissao(self):
        self.lbl_titulo.setText("📅  Data de Emissão")

        lbl = QLabel("O documento deve ter no máximo 10 anos desde a emissão.")
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)

        lbl2 = QLabel("Digite a data de emissão (DD/MM/AAAA):")
        lbl2.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl2.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.content_layout.addWidget(lbl2)

        entry_row = QHBoxLayout()
        self._entry_emissao = QLineEdit()
        self._entry_emissao.setPlaceholderText("DD/MM/AAAA")
        self._entry_emissao.setFont(QFont("Segoe UI", 14))
        self._entry_emissao.setFixedSize(160, 36)
        self._entry_emissao.setMaxLength(10)
        self._entry_emissao.textChanged.connect(lambda t: _apply_date_mask_qt(self._entry_emissao, t))
        entry_row.addWidget(self._entry_emissao)

        self._lbl_emissao_erro = QLabel("")
        self._lbl_emissao_erro.setFont(QFont("Segoe UI", 12))
        self._lbl_emissao_erro.setStyleSheet(f"color: {COLORS['error']};")
        entry_row.addWidget(self._lbl_emissao_erro)
        entry_row.addStretch(1)
        self.content_layout.addLayout(entry_row)
        self.content_layout.addStretch(1)

        self._entry_emissao.setFocus()
        self._botao_confirmar(on_click=self._validar_data_emissao)

    def _validar_data_emissao(self):
        texto = self._entry_emissao.text().strip()
        try:
            parts = texto.replace("-", "/").replace(".", "/").split("/")
            dia, mes, ano = int(parts[0]), int(parts[1]), int(parts[2])
            data = date(ano, mes, dia)
        except (ValueError, IndexError):
            self._lbl_emissao_erro.setText("❌ Data inválida. Use DD/MM/AAAA")
            return

        if data > date.today():
            self._lbl_emissao_erro.setText("❌ Data no futuro")
            return

        valido = _verificar_validade_documento(data)
        self.dados_validacao["data_emissao"] = data.isoformat()
        self.dados_validacao["doc_valido"] = valido

        if valido:
            self._mostrar_passo(2)
        else:
            anos = date.today().year - data.year
            self._reprovar(f"Documento vencido — emitido há {anos} anos (limite: 10 anos)")

    # ── Passo 3: CPF ──────────────────────────────────────────────────────

    def _passo_cpf(self):
        self.lbl_titulo.setText("🔢  Conferência do CPF")

        lbl = QLabel("O CPF no documento deve conferir com o CPF digitado.")
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.content_layout.addWidget(lbl)

        info = QFrame()
        info.setObjectName("card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 12, 16, 12)

        lbl_cpf_title = QLabel("CPF digitado pelo operador:")
        lbl_cpf_title.setFont(QFont("Segoe UI", 12))
        lbl_cpf_title.setStyleSheet(f"color: {COLORS['text_label']};")
        info_layout.addWidget(lbl_cpf_title)

        lbl_cpf_val = QLabel(self.cpf_digitado)
        lbl_cpf_val.setFont(QFont("Segoe UI", 22, QFont.Bold))
        lbl_cpf_val.setStyleSheet(f"color: {COLORS['accent']};")
        info_layout.addWidget(lbl_cpf_val)

        self.content_layout.addWidget(info)

        lbl_q = QLabel("O CPF no documento confere com o CPF acima?")
        lbl_q.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_q.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.content_layout.addWidget(lbl_q)
        self.content_layout.addStretch(1)

        self._botoes_sim_nao(
            on_sim=lambda: (
                self.dados_validacao.update({"cpf_confere": True}),
                self._mostrar_passo(3),
            ),
            on_nao=lambda: self._reprovar("CPF no documento não confere com o CPF digitado"),
        )

    # ── Passo 4: Idade ────────────────────────────────────────────────────

    def _passo_idade(self):
        self.lbl_titulo.setText("🎂  Idade do Paciente")

        lbl = QLabel("Verificação da idade a partir da data de nascimento.")
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)

        lbl2 = QLabel("Digite a data de nascimento (DD/MM/AAAA):")
        lbl2.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl2.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.content_layout.addWidget(lbl2)

        entry_row = QHBoxLayout()
        self._entry_nasc = QLineEdit()
        self._entry_nasc.setPlaceholderText("DD/MM/AAAA")
        self._entry_nasc.setFont(QFont("Segoe UI", 14))
        self._entry_nasc.setFixedSize(160, 36)
        self._entry_nasc.setMaxLength(10)
        self._entry_nasc.textChanged.connect(lambda t: _apply_date_mask_qt(self._entry_nasc, t))
        entry_row.addWidget(self._entry_nasc)

        self._lbl_nasc_erro = QLabel("")
        self._lbl_nasc_erro.setFont(QFont("Segoe UI", 12))
        self._lbl_nasc_erro.setStyleSheet(f"color: {COLORS['error']};")
        entry_row.addWidget(self._lbl_nasc_erro)
        entry_row.addStretch(1)
        self.content_layout.addLayout(entry_row)
        self.content_layout.addStretch(1)

        self._entry_nasc.setFocus()
        self._botao_confirmar(on_click=self._validar_idade)

    def _validar_idade(self):
        texto = self._entry_nasc.text().strip()
        try:
            parts = texto.replace("-", "/").replace(".", "/").split("/")
            dia, mes, ano = int(parts[0]), int(parts[1]), int(parts[2])
            data_nasc = date(ano, mes, dia)
        except (ValueError, IndexError):
            self._lbl_nasc_erro.setText("❌ Data inválida. Use DD/MM/AAAA")
            return

        if data_nasc > date.today():
            self._lbl_nasc_erro.setText("❌ Data no futuro")
            return

        idade = _calcular_idade(data_nasc)
        self.dados_validacao["data_nascimento"] = data_nasc.isoformat()
        self.dados_validacao["idade"] = idade
        self.dados_validacao["is_menor"] = idade < 18
        self.dados_validacao["is_idoso"] = idade >= 60

        # Resultado
        self._limpar_conteudo()
        self.lbl_titulo.setText("🎂  Resultado — Idade")

        info = QFrame()
        info.setObjectName("card")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 16, 16, 16)

        lbl_age = QLabel(f"Idade calculada: {idade} anos")
        lbl_age.setFont(QFont("Segoe UI", 20, QFont.Bold))
        lbl_age.setStyleSheet(f"color: {COLORS['text_primary']};")
        info_layout.addWidget(lbl_age)

        lbl_dob = QLabel(f"Data de Nascimento: {data_nasc.strftime('%d/%m/%Y')}")
        lbl_dob.setFont(QFont("Segoe UI", 13))
        lbl_dob.setStyleSheet(f"color: {COLORS['text_label']};")
        info_layout.addWidget(lbl_dob)

        if idade < 18:
            cat, cor = "👶  MENOR DE IDADE", "#FFB74D"
            desc = "A etapa de assinatura será pulada.\nUma etapa adicional será necessária para o responsável legal."
            on_next = self._aprovar
        elif idade >= 60:
            cat, cor = "👴  IDOSO (≥ 60 anos)", COLORS['accent']
            desc = "Paciente classificado como idoso."
            on_next = lambda: self._mostrar_passo(4)
        else:
            cat, cor = "👤  ADULTO (18-59 anos)", COLORS['success']
            desc = "Faixa etária padrão."
            on_next = lambda: self._mostrar_passo(4)

        lbl_cat = QLabel(cat)
        lbl_cat.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_cat.setStyleSheet(f"color: {cor};")
        info_layout.addWidget(lbl_cat)

        lbl_desc = QLabel(desc)
        lbl_desc.setFont(QFont("Segoe UI", 12))
        lbl_desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl_desc.setWordWrap(True)
        info_layout.addWidget(lbl_desc)

        self.content_layout.addWidget(info)
        self.content_layout.addStretch(1)

        self._limpar_footer()
        self._botao_confirmar(on_click=on_next, texto="Prosseguir  ▶")

    # ── Passo 5: Assinatura ───────────────────────────────────────────────

    def _passo_assinatura(self):
        self.lbl_titulo.setText("✍️  Assinatura do Documento")

        lbl = QLabel("Verifique se o documento possui assinatura do titular.")
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)

        lbl2 = QLabel("Caso não possua assinatura, pode indicar\nalguma incapacidade. Verificaremos a impressão do polegar.")
        lbl2.setFont(QFont("Segoe UI", 12))
        lbl2.setStyleSheet(f"color: {COLORS['text_label']};")
        lbl2.setWordWrap(True)
        self.content_layout.addWidget(lbl2)

        lbl_q = QLabel("O documento possui assinatura?")
        lbl_q.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_q.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.content_layout.addWidget(lbl_q)
        self.content_layout.addStretch(1)

        self._botoes_sim_nao(
            on_sim=lambda: self._finalizar_assinatura(True, False),
            on_nao=self._perguntar_polegar,
        )

    def _perguntar_polegar(self):
        self._limpar_conteudo()
        self._limpar_footer()
        self.lbl_titulo.setText("👆  Impressão do Polegar")

        lbl = QLabel("O documento não possui assinatura.")
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet("color: #FFB74D;")
        self.content_layout.addWidget(lbl)

        lbl2 = QLabel("É necessário verificar se existe impressão do polegar como alternativa.")
        lbl2.setFont(QFont("Segoe UI", 13))
        lbl2.setStyleSheet(f"color: {COLORS['text_secondary']};")
        lbl2.setWordWrap(True)
        self.content_layout.addWidget(lbl2)

        lbl_q = QLabel("O documento possui impressão do dedo polegar?")
        lbl_q.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_q.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.content_layout.addWidget(lbl_q)
        self.content_layout.addStretch(1)

        self._botoes_sim_nao(
            on_sim=lambda: self._finalizar_assinatura(False, True),
            on_nao=lambda: self._reprovar("Documento sem assinatura e sem impressão do polegar"),
        )

    def _finalizar_assinatura(self, tem_assinatura: bool, tem_polegar: bool):
        self.dados_validacao["tem_assinatura"] = tem_assinatura
        self.dados_validacao["tem_polegar"] = tem_polegar
        self._aprovar()

    # ── Resultados ────────────────────────────────────────────────────────

    def _aprovar(self):
        self.resultado = "aprovado"
        self.accept()

    def _reprovar(self, motivo: str):
        self.motivos_reprovacao.append(motivo)
        self._limpar_conteudo()
        self._limpar_footer()

        self.lbl_titulo.setText("❌  Documento Reprovado")
        self.lbl_passo.setText("Validação não aprovada")
        self.progress.setValue(100)
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #C62828; border-radius: 3px; }")

        motivo_frame = QFrame()
        motivo_frame.setStyleSheet(f"background-color: #2A0D0D; border-radius: 10px;")
        m_layout = QVBoxLayout(motivo_frame)
        m_layout.setContentsMargins(16, 12, 16, 12)

        lbl_m = QLabel("Motivo da reprovação:")
        lbl_m.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_m.setStyleSheet("color: #FF8A80;")
        m_layout.addWidget(lbl_m)

        for m in self.motivos_reprovacao:
            lbl = QLabel(f"  ⛔  {m}")
            lbl.setFont(QFont("Segoe UI", 13))
            lbl.setStyleSheet("color: #FFCDD2;")
            lbl.setWordWrap(True)
            m_layout.addWidget(lbl)

        self.content_layout.addWidget(motivo_frame)

        lbl_q = QLabel("O que deseja fazer?")
        lbl_q.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_q.setStyleSheet(f"color: {COLORS['text_primary']};")
        lbl_q.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(lbl_q)
        self.content_layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_refazer = QPushButton("🔄  Refazer Digitalização")
        btn_refazer.setObjectName("btn_primary")
        btn_refazer.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_refazer.setFixedSize(220, 44)
        btn_refazer.setCursor(Qt.PointingHandCursor)
        btn_refazer.clicked.connect(self._refazer)
        btn_row.addWidget(btn_refazer)

        btn_cancel = QPushButton("🚫  Cancelar Transação")
        btn_cancel.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_cancel.setFixedSize(220, 44)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"background-color: {COLORS['delete_bg']}; color: white; border: none; border-radius: 10px;")
        btn_cancel.clicked.connect(self._cancelar)
        btn_row.addWidget(btn_cancel)

        self.footer_layout.addLayout(btn_row)

    def _refazer(self):
        self.resultado = "refazer"
        self.accept()

    def _cancelar(self):
        self.resultado = "cancelar"
        self.accept()

    def closeEvent(self, event):
        self.resultado = "cancelar"
        super().closeEvent(event)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _limpar_conteudo(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _limpar_footer(self):
        while self.footer_layout.count():
            item = self.footer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _botoes_sim_nao(self, on_sim, on_nao):
        self._limpar_footer()
        btn_sim = QPushButton("✅   Sim")
        btn_sim.setObjectName("btn_green")
        btn_sim.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_sim.setFixedSize(200, 42)
        btn_sim.setCursor(Qt.PointingHandCursor)
        btn_sim.clicked.connect(on_sim)
        self.footer_layout.addWidget(btn_sim)

        btn_nao = QPushButton("❌   Não")
        btn_nao.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_nao.setFixedSize(200, 42)
        btn_nao.setCursor(Qt.PointingHandCursor)
        btn_nao.setStyleSheet(f"background-color: {COLORS['delete_bg']}; color: white; border: none; border-radius: 10px;")
        btn_nao.clicked.connect(on_nao)
        self.footer_layout.addWidget(btn_nao)

    def _botao_confirmar(self, on_click, texto: str = "Confirmar  ✔"):
        self._limpar_footer()
        btn = QPushButton(texto)
        btn.setObjectName("btn_green")
        btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn.setFixedSize(240, 42)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click)
        self.footer_layout.addWidget(btn, alignment=Qt.AlignCenter)
