"""
transaction.py - Define os 3 tipos de transação e suas etapas de digitalização.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from core.doc_validator import DocumentData


@dataclass
class ScanStep:
    """Representa uma etapa de digitalização dentro de um fluxo de transação."""
    id: str
    titulo: str
    descricao: str
    icone: str = "📄"
    imagens: List[Image.Image] = field(default_factory=list)
    require_cpf: bool = False
    cpf: str = ""
    validacao_doc: dict = field(default_factory=dict)  # Resultados da validação OCR
    documents: list = field(default_factory=list)  # List[DocumentData] para o novo fluxo

    def adicionar_imagem(self, imagem: Image.Image) -> None:
        self.imagens.append(imagem)

    def remover_imagem(self, index: int) -> None:
        if 0 <= index < len(self.imagens):
            self.imagens.pop(index)

    @property
    def tem_imagens(self) -> bool:
        return len(self.imagens) > 0

    @property
    def total_imagens(self) -> int:
        return len(self.imagens)


@dataclass
class Transaction:
    """Representa uma transação completa com tipo e etapas."""
    tipo: int
    nome_tipo: str
    etapas: List[ScanStep]
    etapa_atual_index: int = 0
    is_menor_idade: bool = False
    is_idoso: bool = False
    idade_paciente: int = 0

    @property
    def etapa_atual(self) -> ScanStep:
        return self.etapas[self.etapa_atual_index]

    @property
    def total_etapas(self) -> int:
        return len(self.etapas)

    @property
    def progresso(self) -> float:
        return self.etapa_atual_index / self.total_etapas

    @property
    def concluida(self) -> bool:
        return self.etapa_atual_index >= self.total_etapas

    def avancar_etapa(self) -> bool:
        """Avança para a próxima etapa. Retorna False se já está na última."""
        if self.etapa_atual_index < self.total_etapas - 1:
            self.etapa_atual_index += 1
            return True
        self.etapa_atual_index = self.total_etapas  # marca como concluída
        return False

    def voltar_etapa(self) -> bool:
        """Volta para a etapa anterior. Retorna False se já está na primeira."""
        if self.etapa_atual_index > 0:
            # Se estava concluída (index == total_etapas), volta para a última
            if self.etapa_atual_index >= self.total_etapas:
                self.etapa_atual_index = self.total_etapas - 1
            else:
                self.etapa_atual_index -= 1
            return True
        return False

    def todas_imagens(self) -> List[Image.Image]:
        """Retorna todas as imagens de todas as etapas, em ordem."""
        todas: List[Image.Image] = []
        for etapa in self.etapas:
            todas.extend(etapa.imagens)
        return todas

    def resumo_etapas(self) -> List[dict]:  # type: ignore[type-arg]
        """Retorna um resumo de cada etapa com título e quantidade de imagens."""
        return [
            {
                "titulo": e.titulo,
                "imagens": e.total_imagens,
                "concluida": e.total_imagens > 0,
            }
            for e in self.etapas
        ]

    def inserir_etapa_apos_atual(self, etapa: ScanStep) -> None:
        """Insere uma nova etapa logo após a etapa atual."""
        self.etapas.insert(self.etapa_atual_index + 1, etapa)

    def ja_tem_etapa(self, etapa_id: str) -> bool:
        """Verifica se uma etapa com o ID dado já existe na transação."""
        return any(e.id == etapa_id for e in self.etapas)


# ─── Fábricas de Transação ────────────────────────────────────────────────────

def criar_transacao_proprio_paciente() -> Transaction:
    """Tipo 1: Próprio Paciente — 3 etapas."""
    return Transaction(
        tipo=1,
        nome_tipo="Próprio Paciente",
        etapas=[
            ScanStep(
                id="id_paciente",
                titulo="Identificação do Paciente",
                descricao=(
                    "Digitalize o documento de identificação com foto do paciente.\n"
                    "O documento deve conter o número do CPF."
                ),
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="receita",
                titulo="Receita Médica e/ou Laudo Médico",
                descricao=(
                    "Digitalize a Receita Médica e/ou o Laudo Médico.\n"
                    "Verifique se contém assinatura, carimbo e CRM do médico."
                ),
                icone="📋",
            ),
            ScanStep(
                id="cupom",
                titulo="Cupom Fiscal + Cupom Vinculado",
                descricao=(
                    "Digitalize o Cupom Fiscal e o Cupom Vinculado do programa.\n"
                    "O Cupom Vinculado deve conter o endereço do beneficiário e estar assinado."
                ),
                icone="🧾",
            ),
        ],
    )


def criar_transacao_procurador() -> Transaction:
    """Tipo 2: Procurador — 5 etapas."""
    return Transaction(
        tipo=2,
        nome_tipo="Procurador",
        etapas=[
            ScanStep(
                id="id_paciente",
                titulo="Identificação do Paciente",
                descricao=(
                    "Digitalize o documento de identificação com foto do paciente da receita.\n"
                    "O documento deve conter o número do CPF."
                ),
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="id_procurador",
                titulo="Documento de Identificação do Procurador",
                descricao=(
                    "Digitalize o documento de identificação com foto do procurador.\n"
                    "O documento deve conter o número do CPF."
                ),
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="procuracao",
                titulo="Procuração",
                descricao=(
                    "Digitalize o instrumento de procuração (público ou particular com "
                    "reconhecimento de firma).\n"
                    "Ou sentença judicial declaratória que comprove a representação legal."
                ),
                icone="📜",
            ),
            ScanStep(
                id="receita",
                titulo="Receita Médica e/ou Laudo Médico",
                descricao=(
                    "Digitalize a Receita Médica e/ou o Laudo Médico.\n"
                    "Verifique se contém assinatura, carimbo e CRM do médico."
                ),
                icone="📋",
            ),
            ScanStep(
                id="cupom",
                titulo="Cupom Fiscal + Cupom Vinculado",
                descricao=(
                    "Digitalize o Cupom Fiscal e o Cupom Vinculado do programa.\n"
                    "O Cupom Vinculado deve conter o endereço do beneficiário e estar assinado."
                ),
                icone="🧾",
            ),
        ],
    )


def criar_transacao_menor_de_idade() -> Transaction:
    """Tipo 3: Menor de Idade — 4 etapas."""
    return Transaction(
        tipo=3,
        nome_tipo="Menor de Idade",
        etapas=[
            ScanStep(
                id="id_paciente",
                titulo="Documento do Paciente ou Certidão de Nascimento",
                descricao="Digitalize o documento de identificação do menor (RG ou Certidão de Nascimento).",
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="id_responsavel",
                titulo="Documento de Identificação do Responsável",
                descricao=(
                    "Digitalize o documento de identificação with foto do responsável legal "
                    "(pai, mãe ou tutor).\nO documento deve conter o número do CPF."
                ),
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="receita",
                titulo="Receita Médica e/ou Laudo Médico",
                descricao=(
                    "Digitalize a Receita Médica e/ou o Laudo Médico.\n"
                    "Verifique se contém assinatura, carimbo e CRM do médico."
                ),
                icone="📋",
            ),
            ScanStep(
                id="cupom",
                titulo="Cupom Fiscal + Cupom Vinculado",
                descricao=(
                    "Digitalize o Cupom Fiscal e o Cupom Vinculado do programa.\n"
                    "O Cupom Vinculado deve conter o endereço do beneficiário e estar assinado."
                ),
                icone="🧾",
            ),
        ],
    )


FABRICAS_TRANSACAO = {
    1: criar_transacao_proprio_paciente,
    2: criar_transacao_procurador,
    3: criar_transacao_menor_de_idade,
}

TIPOS_TRANSACAO = {
    1: {
        "nome": "Próprio Paciente",
        "descricao": "O próprio paciente retira o medicamento.",
        "icone": "👤",
        "etapas": 3,
    },
    2: {
        "nome": "Procurador",
        "descricao": "Um procurador retira em nome do paciente.",
        "icone": "🤝",
        "etapas": 5,
    },
    3: {
        "nome": "Menor de Idade",
        "descricao": "Paciente menor de idade com responsável.",
        "icone": "👶",
        "etapas": 4,
    },
}


def criar_transacao(tipo: int) -> Transaction:
    """Cria uma nova transação do tipo especificado."""
    if tipo not in FABRICAS_TRANSACAO:
        raise ValueError(f"Tipo de transação inválido: {tipo}")
    return FABRICAS_TRANSACAO[tipo]()


# ─── Fluxo Único Inteligente (v2.0.0) ────────────────────────────────────────

def criar_transacao_unica() -> Transaction:
    """
    Cria uma transação com fluxo único inteligente.
    Começa apenas com o documento de identificação do paciente.
    As etapas seguintes são inseridas dinamicamente conforme a validação avança.
    """
    return Transaction(
        tipo=0,
        nome_tipo="Fluxo Único",
        etapas=[
            ScanStep(
                id="id_paciente",
                titulo="Documento de Identificação do Paciente",
                descricao=(
                    "Digitalize o documento de identificação com foto do paciente.\n"
                    "O documento deve conter o número do CPF."
                ),
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="receita",
                titulo="Receita Médica e/ou Laudo Médico",
                descricao=(
                    "Digitalize a Receita Médica e/ou o Laudo Médico.\n"
                    "Verifique se contém assinatura, carimbo e CRM do médico."
                ),
                icone="📋",
            ),
            ScanStep(
                id="cupom",
                titulo="Cupom Fiscal + Cupom Vinculado",
                descricao=(
                    "Digitalize o Cupom Fiscal e o Cupom Vinculado do programa.\n"
                    "O Cupom Vinculado deve conter o endereço do beneficiário e estar assinado."
                ),
                icone="🧾",
            ),
        ],
    )


# ─── Fluxo Unificado (v3.0.0) ────────────────────────────────────────────────

def criar_transacao_unificada(cpf_paciente: str = "") -> Transaction:
    """
    Cria uma transação com fluxo unificado — todos os documentos em uma única tela.
    O campo documents do ScanStep armazena os DocumentData de validação.
    """
    return Transaction(
        tipo=10,
        nome_tipo="Fluxo Unificado",
        etapas=[
            ScanStep(
                id="all_documents",
                titulo="Digitalização de Documentos",
                descricao=(
                    "Digitalize ou importe todos os documentos da transação.\n"
                    "A IA identificará o tipo e validará cada documento automaticamente."
                ),
                icone="📋",
                require_cpf=False,
                cpf=cpf_paciente,
            ),
        ],
    )


# ─── Etapas Dinâmicas ─────────────────────────────────────────────────────────

def criar_etapa_responsavel_legal() -> ScanStep:
    """Cria etapa para documento do responsável legal (menor de idade)."""
    return ScanStep(
        id="id_responsavel",
        titulo="Identificação do Responsável Legal",
        descricao=(
            "Paciente menor de 18 anos detectado.\n"
            "Digitalize o documento de identificação do responsável legal (pai, mãe ou tutor).\n"
            "O documento deve conter o número do CPF."
        ),
        icone="🪪",
        require_cpf=True,
    )

