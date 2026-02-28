"""
config.py - Gerenciamento de configurações persistentes do DocPopular
Salva/carrega configurações em settings.json.

Em produção (PyInstaller): settings e key ficam em AppData/Local/DocPopular/
Em desenvolvimento: ficam na raiz do projeto.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


def _get_app_data_dir() -> Path:
    """
    Retorna o diretório de dados da aplicação:
    - Produção (PyInstaller): %APPDATA%/DocPopular/
    - Dev: raiz do projeto
    """
    if getattr(sys, "frozen", False):
        # Executando como .exe gerado pelo PyInstaller
        app_data = Path.home() / "AppData" / "Local" / "DocPopular"
    else:
        # Modo desenvolvimento
        app_data = Path(__file__).parent.parent

    app_data.mkdir(parents=True, exist_ok=True)
    return app_data


def _get_master_prompt_path() -> Path:
    """
    Retorna o caminho do master_prompt.md.
    Em produção (PyInstaller --onedir): fica na pasta do exe.
    Em desenvolvimento: fica na raiz do projeto.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller extrai dados para sys._MEIPASS (onefile) ou pasta do exe (onedir)
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / "master_prompt.md"


# Diretórios e arquivos
APP_DATA_DIR = _get_app_data_dir()
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
KEY_FILE = APP_DATA_DIR / ".app_key"

AVAILABLE_MODELS = {}

# Configurações padrão
DEFAULT_SETTINGS: dict[str, Any] = {
    "output_folder": str(Path.home() / "Documents" / "DocPopular"),
    "scanner_name": "",
    "license_key": "",
}


def _get_or_create_key() -> bytes:
    """Obtém ou cria a chave de criptografia local."""
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key


def _encrypt(value: str) -> str:
    if not value:
        return ""
    f = Fernet(_get_or_create_key())
    return f.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    if not value:
        return ""
    try:
        f = Fernet(_get_or_create_key())
        return f.decrypt(value.encode()).decode()
    except Exception:
        return ""


def load_settings() -> dict[str, Any]:
    """Carrega as configurações do arquivo JSON."""
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    # Descriptografa as chaves de API
    for provider in data.get("api_keys", {}):
        data["api_keys"][provider] = _decrypt(data["api_keys"][provider])

    # Garante que campos novos existam
    for key, value in DEFAULT_SETTINGS.items():
        if key not in data:
            data[key] = value

    return data


def save_settings(settings: dict[str, Any]) -> None:
    """Salva as configurações no arquivo JSON (criptografando as chaves de API)."""
    data = settings.copy()
    data["api_keys"] = {}
    for provider, key in settings.get("api_keys", {}).items():
        data["api_keys"][provider] = _encrypt(key)

    # Garante que a pasta de saída existe
    output_folder = Path(settings.get("output_folder", str(DEFAULT_SETTINGS["output_folder"])))
    output_folder.mkdir(parents=True, exist_ok=True)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_master_prompt() -> str:
    """Removido em DocPopular."""
    return ""


def get_active_api_key(settings: dict[str, Any]) -> str:
    """Removido em DocPopular."""
    return ""
