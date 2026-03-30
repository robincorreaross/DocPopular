"""
doc_validator.py - Motor de validação por tipo de documento.
Utiliza 7 categorias de negócio em vez de tipos técnicos de documento.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from PIL import Image
from core import logger


# ── Modelos ──────────────────────────────────────────────────────────────────

@dataclass
class ChecklistItem:
    """Representa um item individual do checklist de validação."""
    id: str
    label: str
    value: Optional[str] = None
    status: str = "pending"  # "valid", "pending", "invalid"
    editable: bool = True
    required: bool = True
    field_type: str = "text"  # "text", "date", "select", "readonly", "bool"
    options: List[str] = field(default_factory=list)  # para field_type="select"


@dataclass
class DocumentData:
    """Representa um documento com seus dados de validação."""
    doc_type: str = "DESCONHECIDO"   # Categoria de negócio
    doc_role: str = ""               # "paciente", "responsavel_legal" (só para IDENTIFICACAO)
    checklist: List[ChecklistItem] = field(default_factory=list)
    overall_status: str = "pending"  # "valid", "pending", "invalid"
    is_audited: bool = False         # Auditoria humana obrigatória
    image: Optional[Image.Image] = None
    ai_raw: dict = field(default_factory=dict)


# ── Categorias de Negócio (os 7 tipos que o usuário definiu) ─────────────────

# Tipos técnicos da IA que mapeiam para "Identificação"
AI_TIPOS_IDENTIDADE = {"RG", "CIN", "CNH", "CERTIDAO_NASCIMENTO"}

# Os 7 tipos de negócio
DOC_TIPO_IDENTIFICACAO = "IDENTIFICACAO"
DOC_TIPO_RECEITA       = "RECEITA"
DOC_TIPO_LAUDO         = "LAUDO"
DOC_TIPO_TERMO         = "TERMO_DIGNIDADE"
DOC_TIPO_PROCURACAO    = "PROCURACAO"
DOC_TIPO_INTERDICAO    = "INTERDICAO"
DOC_TIPO_CUPOM         = "CUPOM"
DOC_TIPO_DESCONHECIDO  = "DESCONHECIDO"

# Labels amigáveis para os 7 tipos de negócio
DOC_TYPE_LABELS = {
    DOC_TIPO_IDENTIFICACAO: "🪪 Documento de Identificação",
    DOC_TIPO_RECEITA:       "📋 Receita Médica",
    DOC_TIPO_LAUDO:         "📋 Laudo Médico",
    DOC_TIPO_TERMO:         "📄 Termo Dignidade Menstrual",
    DOC_TIPO_PROCURACAO:    "📜 Procuração Simples",
    DOC_TIPO_INTERDICAO:    "⚖️ Interdição Judicial",
    DOC_TIPO_CUPOM:         "🧾 Cupom Fiscal / Cupom Vinculado",
    DOC_TIPO_DESCONHECIDO:  "❓ Desconhecido",
}

# Opções de seleção de tipo visíveis ao operador
DOC_TYPE_SELECT_OPTIONS = [
    "Documento de Identificação",
    "Receita Médica",
    "Laudo Médico",
    "Termo Dignidade Menstrual",
    "Procuração Simples",
    "Interdição Judicial",
    "Cupom Fiscal / Cupom Vinculado",
]

# Mapeamento de label → key interna
DOC_LABEL_TO_KEY = {v.split(" ", 1)[1]: k for k, v in DOC_TYPE_LABELS.items()}
DOC_LABEL_TO_KEY["Documento de Identificação"] = DOC_TIPO_IDENTIFICACAO
DOC_LABEL_TO_KEY["Receita Médica"]             = DOC_TIPO_RECEITA
DOC_LABEL_TO_KEY["Laudo Médico"]               = DOC_TIPO_LAUDO
DOC_LABEL_TO_KEY["Termo Dignidade Menstrual"]  = DOC_TIPO_TERMO
DOC_LABEL_TO_KEY["Procuração Simples"]         = DOC_TIPO_PROCURACAO
DOC_LABEL_TO_KEY["Interdição Judicial"]        = DOC_TIPO_INTERDICAO
DOC_LABEL_TO_KEY["Cupom Fiscal / Cupom Vinculado"] = DOC_TIPO_CUPOM

ROLES_IDENTIDADE = ["Paciente", "Responsável Legal"]

STATUS_LABELS = {
    "valid":   "✅ Válido",
    "pending": "⏳ Pendente",
    "invalid": "❌ Inválido",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ai_tipo_para_negocio(ai_tipo: str) -> str:
    """Converte tipo técnico da IA para categoria de negócio."""
    if ai_tipo in AI_TIPOS_IDENTIDADE:
        return DOC_TIPO_IDENTIFICACAO
    mapa = {
        "RECEITA": DOC_TIPO_RECEITA,
        "LAUDO":   DOC_TIPO_LAUDO,
        "TERMO_DIGNIDADE": DOC_TIPO_TERMO,
        "PROCURACAO": DOC_TIPO_PROCURACAO,
        "INTERDICAO": DOC_TIPO_INTERDICAO,
        "CUPOM": DOC_TIPO_CUPOM,
    }
    return mapa.get(ai_tipo, DOC_TIPO_DESCONHECIDO)


def _calcular_idade(data_nasc: date) -> int:
    hoje = date.today()
    idade = hoje.year - data_nasc.year
    if (hoje.month, hoje.day) < (data_nasc.month, data_nasc.day):
        idade -= 1
    return idade


def _verificar_validade_documento(data_emissao: date, max_anos: int = 10) -> bool:
    hoje = date.today()
    anos_passados = hoje.year - data_emissao.year
    if (hoje.month, hoje.day) < (data_emissao.month, data_emissao.day):
        anos_passados -= 1
    return anos_passados <= max_anos


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Tenta parsear uma data nos formatos DD/MM/AAAA ou AAAA-MM-DD."""
    if not date_str:
        return None
    try:
        if "/" in date_str:
            parts = date_str.split("/")
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        elif "-" in date_str:
            parts = date_str.split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        pass
    return None


# ── Validação para Documentos de Identificação ───────────────────────────────

def validate_identity_document(ai_data: dict, image: Optional[Image.Image] = None) -> DocumentData:
    """
    Cria um DocumentData para documentos de identificação.
    Categoria de negócio: IDENTIFICACAO (RG, CIN, CNH, Certidão).
    """
    has_ai = "error" not in ai_data and bool(ai_data)

    raw_tipo = ai_data.get("tipo_documento") if has_ai else None
    ai_tipo = raw_tipo.upper() if isinstance(raw_tipo, str) else "DESCONHECIDO"

    logger.info("Validator", f"validate_identity_document: has_ai={has_ai}, ai_tipo={ai_tipo}")

    # Extrair dados da IA
    nome           = ai_data.get("nome") if has_ai else None
    cpf            = ai_data.get("cpf") if has_ai else None
    data_nasc_str  = ai_data.get("data_nascimento") if has_ai else None
    data_emis_str  = ai_data.get("data_emissao") if has_ai else None
    legivel        = ai_data.get("legivel", None) if has_ai else None
    tem_foto       = ai_data.get("tem_foto", None) if has_ai else None

    # Calcular idade
    data_nasc = _parse_date(data_nasc_str)
    idade = _calcular_idade(data_nasc) if data_nasc else None

    # Validar data de emissão
    data_emissao = _parse_date(data_emis_str)
    emissao_valida = _verificar_validade_documento(data_emissao) if data_emissao else None

    is_certidao = ai_tipo == "CERTIDAO_NASCIMENTO"

    def _st(value):   return "valid" if value else "pending"
    def _sb(value):
        if value is None: return "pending"
        return "valid" if value else "invalid"
    def _se():
        if emissao_valida is None: return "pending"
        return "valid" if emissao_valida else "invalid"

    # O tipo no checklist é a *categoria de negócio*, não o tipo técnico da IA.
    # O operador escolherá entre os 7 tipos definidos.
    checklist = [
        ChecklistItem(
            id="tipo_negocio",
            label="Categoria do Documento",
            value="Documento de Identificação",  # pré-selecionado pela IA
            status="valid",
            editable=True,
            required=True,
            field_type="select",
            options=DOC_TYPE_SELECT_OPTIONS,
        ),
        ChecklistItem(
            id="doc_role",
            label="Titular (Paciente ou Responsável)",
            value=None,
            status="pending",
            editable=True,
            required=True,
            field_type="select",
            options=ROLES_IDENTIDADE,
        ),
        ChecklistItem(
            id="nome_completo",
            label="Nome Completo",
            value=nome,
            status=_st(nome),
            editable=True,
            required=True,
        ),
        ChecklistItem(
            id="cpf",
            label="CPF",
            value=cpf,
            status=_st(cpf),
            editable=True,
            required=True,
        ),
        ChecklistItem(
            id="data_nascimento",
            label="Data de Nascimento",
            value=data_nasc_str,
            status=_st(data_nasc_str),
            editable=True,
            required=True,
            field_type="date",
        ),
        ChecklistItem(
            id="idade",
            label="Idade (calculada)",
            value=f"{idade} anos" if idade is not None else None,
            status=_st(idade is not None),
            editable=False,
            required=False,
            field_type="readonly",
        ),
        ChecklistItem(
            id="data_emissao",
            label="Data de Emissão (≤10 anos)",
            value=data_emis_str,
            status=_se(),
            editable=True,
            required=True,
            field_type="date",
        ),
        ChecklistItem(
            id="legivel",
            label="Documento Legível",
            value="Sim" if legivel else "Não",
            status="valid" if legivel else "invalid", # Não inicia mais pendente para bools, vai direto pro estado do checkbox
            editable=True,
            required=True,
            field_type="bool",
        ),
    ]

    overall = _compute_overall_status_internal(checklist, False)
    return DocumentData(
        doc_type=DOC_TIPO_IDENTIFICACAO,
        doc_role="",
        checklist=checklist,
        overall_status=overall,
        is_audited=False,
        image=image,
        ai_raw=ai_data,
    )


# ── Validação genérica (fallback para outros tipos) ──────────────────────────

def validate_generic_document(ai_data: dict, image: Optional[Image.Image] = None, doc_type: str = DOC_TIPO_DESCONHECIDO) -> DocumentData:
    """Cria um DocumentData básico para documentos não-identificação."""
    checklist = [
        ChecklistItem(
            id="tipo_negocio",
            label="Categoria do Documento",
            value=None,
            status="pending",
            editable=True,
            required=True,
            field_type="select",
            options=DOC_TYPE_SELECT_OPTIONS,
        ),
    ]
    
    # Adicionar 'legivel' apenas se já houver uma categoria de negócio selecionada 
    # (Para não poluir a tela inicial de documentos desconhecidos)
    if doc_type != DOC_TIPO_DESCONHECIDO:
        checklist.append(
            ChecklistItem(
                id="legivel",
                label="Documento Legível",
                value="Não",  # Inicia falso (Não) para obrigar o clique (Checked)
                status="invalid", # Impede submissão antes de interagir
                editable=True,
                required=True,
                field_type="bool",
            )
        )

    overall = _compute_overall_status_internal(checklist, False)
    return DocumentData(
        doc_type=doc_type,
        doc_role="",
        checklist=checklist,
        overall_status=overall,
        is_audited=False,
        image=image,
        ai_raw=ai_data,
    )


# ── Ponto de entrada unificado ────────────────────────────────────────────────

def validate_document(ai_data: dict, image: Optional[Image.Image] = None) -> DocumentData:
    """
    Ponto de entrada único: escolhe o validador correto baseado no tipo da IA.
    Retorna sempre um DocumentData com checklist preenchido.
    """
    has_ai = "error" not in ai_data and bool(ai_data)
    raw_tipo = ai_data.get("tipo_documento") if has_ai else None
    ai_tipo = raw_tipo.upper() if isinstance(raw_tipo, str) else "DESCONHECIDO"

    if ai_tipo in AI_TIPOS_IDENTIDADE:
        return validate_identity_document(ai_data, image)
    else:
        negocio = _ai_tipo_para_negocio(ai_tipo)
        return validate_generic_document(ai_data, image, negocio)


# ── Atualização de item do checklist ────────────────────────────────────────

def update_checklist_item(doc: DocumentData, item_id: str, new_value: str) -> None:
    """
    Atualiza o valor de um item do checklist e recalcula status.
    Ao alterar a categoria (tipo_negocio), recria dinamicamente a estrutura de campos.
    """
    # 1. Se mudar a categoria, precisamos recriar a estrutura do checklist (Injeção Dinâmica)
    if item_id == "tipo_negocio":
        key = DOC_LABEL_TO_KEY.get(new_value, DOC_TIPO_DESCONHECIDO)
        if key != doc.doc_type:
            logger.info("Validator", f"Categoria alterada de '{doc.doc_type}' para '{key}'. Recriando checklist.")
            old_values = {i.id: i.value for i in doc.checklist}
            old_values["tipo_negocio"] = new_value
            
            if key == DOC_TIPO_IDENTIFICACAO:
                new_doc = validate_identity_document(doc.ai_raw, doc.image)
            else:
                new_doc = validate_generic_document(doc.ai_raw, doc.image, key)
                
            doc.checklist = new_doc.checklist
            doc.doc_type = new_doc.doc_type
            doc.doc_role = new_doc.doc_role
            
            # Re-aplicar valores para manter status correto
            for i in doc.checklist:
                if i.id in old_values:
                    val = old_values[i.id]
                    if val is not None:
                        _apply_field_update(doc, i.id, val)
                    
            doc.overall_status = _compute_overall_status_internal(doc.checklist, doc.is_audited)
            return

    # 2. Atualização padrão
    _apply_field_update(doc, item_id, new_value)
    doc.overall_status = _compute_overall_status_internal(doc.checklist, doc.is_audited)


def _apply_field_update(doc: DocumentData, item_id: str, new_value: str) -> None:
    """Função interna para atualizar e calcular status de um campo individual."""
    for item in doc.checklist:
        if item.id == item_id:
            old_val = item.value
            item.value = new_value

            if item_id == "tipo_negocio":
                key = DOC_LABEL_TO_KEY.get(new_value, DOC_TIPO_DESCONHECIDO)
                doc.doc_type = key
                item.status = "valid" if key != DOC_TIPO_DESCONHECIDO else "pending"
                _update_role_requirement(doc)

            elif item_id == "doc_role":
                item.status = "valid" if new_value in ROLES_IDENTIDADE else "pending"
                doc.doc_role = (
                    new_value.lower()
                    .replace("á", "a").replace("é", "e")
                    .replace(" ", "_")
                ) if new_value else ""

            elif item_id == "data_nascimento":
                parsed = _parse_date(new_value)
                if parsed and parsed <= date.today():
                    item.status = "valid"
                    idade = _calcular_idade(parsed)
                    _set_item_value(doc, "idade", f"{idade} anos", "valid")
                    logger.debug("Validator", f"Idade recalculada: {idade} anos para nasc={new_value}")
                else:
                    item.status = "pending"
                    _set_item_value(doc, "idade", None, "pending")

            elif item_id == "data_emissao":
                parsed = _parse_date(new_value)
                if parsed:
                    item.status = "valid" if _verificar_validade_documento(parsed) else "invalid"
                else:
                    item.status = "pending"

            elif item_id in ("legivel", "tem_foto"):
                item.status = "valid" if new_value == "Sim" else "invalid"

            else:
                item.status = "valid" if new_value and new_value.strip() else "pending"

            logger.debug("Validator", f"Item '{item_id}' atualizado: '{old_val}' -> '{new_value}' (Status: {item.status})")
            break

    doc.overall_status = _compute_overall_status_internal(doc.checklist, doc.is_audited)


# ── Funções auxiliares públicas ───────────────────────────────────────────────

def is_document_valid(doc: DocumentData) -> bool:
    """Verifica se o documento foi auditado e se o checklist está ok."""
    return doc.overall_status == "valid"


def is_checklist_valid(doc: DocumentData) -> bool:
    """Verifica se todos os itens obrigatórios do checklist estão válidos (independente de auditoria)."""
    if not doc.checklist:
        return False
    for item in doc.checklist:
        if item.required and item.status != "valid":
            return False
    return True


def _compute_overall_status_internal(checklist: List[ChecklistItem], is_audited: bool) -> str:
    """Calcula o status geral baseado no checklist e na auditoria humana."""
    has_invalid = any(i.status == "invalid" and i.required for i in checklist)
    has_pending = any(i.status == "pending" and i.required for i in checklist)
    
    if has_invalid: return "invalid"
    if has_pending: return "pending"
    
    # Se tudo no checklist está OK, o status final depende da auditoria humana
    return "valid" if is_audited else "pending"


def _set_item_value(doc: DocumentData, item_id: str, value: Optional[str], status: str) -> None:
    for item in doc.checklist:
        if item.id == item_id:
            item.value = value
            item.status = status
            break


def _update_role_requirement(doc: DocumentData) -> None:
    """Exibe/oculta o campo de titularidade conforme o tipo de negócio."""
    is_id = doc.doc_type == DOC_TIPO_IDENTIFICACAO
    for item in doc.checklist:
        if item.id == "doc_role":
            item.required = is_id
            if not is_id:
                item.status = "valid"  # não obrigatório
            break


def get_doc_type_label(doc_type: str) -> str:
    return DOC_TYPE_LABELS.get(doc_type, DOC_TYPE_LABELS[DOC_TIPO_DESCONHECIDO])


def get_display_label(doc_data: DocumentData) -> str:
    """Label completo com titularidade para docs de identificação."""
    if doc_data.doc_type == DOC_TIPO_IDENTIFICACAO:
        role = doc_data.doc_role
        if role == "paciente":
            return "🪪 Identificação do Paciente"
        elif "responsavel" in role:
            return "🪪 Identificação do Responsável Legal"
        else:
            return "🪪 Documento de Identificação"
    return get_doc_type_label(doc_data.doc_type)


def get_status_label(status: str) -> str:
    return STATUS_LABELS.get(status, STATUS_LABELS["pending"])
