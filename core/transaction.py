"""
transaction.py - Define os 3 tipos de transação e suas etapas de digitalização.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from PIL import Image


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


# ─── Fábricas de Transação ────────────────────────────────────────────────────

def criar_transacao_proprio_paciente() -> Transaction:
    """Tipo 1: Próprio Paciente — 3 etapas."""
    return Transaction(
        tipo=1,
        nome_tipo="Próprio Paciente",
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


def criar_transacao_procurador() -> Transaction:
    """Tipo 2: Procurador — 5 etapas."""
    return Transaction(
        tipo=2,
        nome_tipo="Procurador",
        etapas=[
            ScanStep(
                id="id_paciente",
                titulo="Documento de Identificação do Paciente",
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
