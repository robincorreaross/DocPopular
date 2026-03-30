"""
date_manager.py - Utilitários para formatação e máscara de datas.
Versão PySide6: funções de máscara agora são standalone (não dependem de CTk).
"""


def apply_date_mask_to_text(text: str) -> str:
    """
    Aplica a máscara DD/MM/AAAA a um texto bruto.
    Retorna o texto formatado. Pode ser usado com qualquer framework.
    """
    apenas_nums = "".join(filter(str.isdigit, text))[:8]
    novo = ""
    for i, d in enumerate(apenas_nums):
        if i in [2, 4]:
            novo += "/"
        novo += d
    return novo


def format_date_br_to_iso(date_str: str) -> str:
    """Converte DD/MM/AAAA para AAAA-MM-DD."""
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return ""

def format_iso_to_date_br(iso_str: str) -> str:
    """Converte AAAA-MM-DD para DD/MM/AAAA."""
    try:
        parts = iso_str.split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return ""
