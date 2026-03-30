"""
main.py - Ponto de entrada do DocPopular (PySide6).
Verifica licença antes de abrir a aplicação principal.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Garante que o diretório raiz do projeto está no PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from core.config import load_settings
from core.license import LicenseError, get_machine_id, validar_licenca, carregar_licenca
from ui.qt_styles import GLOBAL_QSS


def get_resource_path(relative_path: str) -> str:
    """Retorna o caminho absoluto do recurso, compatível com PyInstaller."""
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return str(base_path / relative_path)


def _verificar_licenca(settings: dict) -> tuple[bool, str]:
    """
    Retorna (valida, mensagem_erro).
    Tenta validar online primeiro (via ID da máquina), depois offline (via chave salva).
    """
    chave = carregar_licenca(settings)
    try:
        res = validar_licenca(chave or "")
        return res.get("valido", False), ""
    except LicenseError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Erro inesperado na validação: {e}"


def main() -> None:
    # Habilita High DPI automaticamente
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("DocPopular")
    app.setOrganizationName("RossSistemas")
    app.setStyleSheet(GLOBAL_QSS)

    # Ícone
    icon_path = get_resource_path("assets/icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Registra AppUserModelID no Windows
    try:
        import ctypes
        myappid = 'RossSistemas.DocPopular.Auditor.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    settings = load_settings()
    valida, msg_erro = _verificar_licenca(settings)

    if valida:
        from ui.app import App
        window = App()
        window.showMaximized()
    else:
        from ui.screens.license_screen import LicenseScreen
        
        estado = "padrao"
        if "novo" in msg_erro.lower():
            estado = "novo"
        elif "expirou" in msg_erro.lower():
            estado = "expirado"
        elif "inativa" in msg_erro.lower():
            estado = "inativo"
        
        window = LicenseScreen(settings, estado=estado, msg_extra=msg_erro if estado == "padrao" else "")
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
