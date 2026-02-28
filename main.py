"""
main.py - Ponto de entrada do DocPopular.
Verifica licença antes de abrir a aplicação principal.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que o diretório raiz do projeto está no PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from core.config import load_settings, save_settings
from core.license import LicenseError, get_machine_id, validar_licenca, carregar_licenca


def _verificar_licenca(settings: dict) -> tuple[bool, str]:  # type: ignore[type-arg]
    """
    Retorna (valida, mensagem_erro).
    Tenta validar online primeiro (via ID da máquina), depois offline (via chave salva).
    """
    chave = carregar_licenca(settings)
    
    # validar_licenca agora é híbrida: tenta online(mid) e depois offline(key)
    try:
        # Passamos a chave salva (pode ser vazia para novos clientes online)
        res = validar_licenca(chave or "")
        return res.get("valido", False), ""
    except LicenseError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Erro inesperado na validação: {e}"


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    settings = load_settings()
    valida, msg_erro = _verificar_licenca(settings)

    if valida:
        # Licença OK → abre o app diretamente
        from ui.app import App
        app = App()
        app.mainloop()
    else:
        # Sem licença ou erro → abre tela de ativação dinâmica
        from ui.screens.license_screen import LicenseScreen

        def _abrir_app() -> None:
            from ui.app import App
            app = App()
            app.mainloop()

        # Determina o estado baseado na mensagem de erro
        estado = "padrao"
        if "novo" in msg_erro.lower():
            estado = "novo"
        elif "expirou" in msg_erro.lower():
            estado = "expirado"
        elif "inativa" in msg_erro.lower():
            estado = "inativo"

        screen = LicenseScreen(settings, _abrir_app, estado=estado, msg_extra=msg_erro if estado == "padrao" else "")
        screen.mainloop()


if __name__ == "__main__":
    main()
