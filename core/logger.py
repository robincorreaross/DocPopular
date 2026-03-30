"""
logger.py - Sistema de logs coloridos para o terminal do DocPopular.
Facilita o rastreamento de processos de IA, Visão Computacional e Scanner.
"""

import sys
import time
from datetime import datetime
import os

# Cores ANSI
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Caminho para o arquivo de log (Baseado no executável do app)
try:
    if getattr(sys, 'frozen', False):
        # Se for um executável (PyInstaller)
        base_dir = os.path.dirname(sys.executable)
    else:
        # Se for rodando via script
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    LOG_FILE = os.path.join(base_dir, "app.log")
    
    # Testa se consegue abrir para escrita
    with open(LOG_FILE, "a") as f:
        pass
except Exception:
    import tempfile
    LOG_FILE = os.path.join(tempfile.gettempdir(), "DocPopular_app.log")

def _log(prefix, message, color=Colors.ENDC, bold=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    bold_code = Colors.BOLD if bold else ""
    log_line = f"[{timestamp}] {prefix} {message}"
    
    # Print no console (com cores), apenas se o console existir
    if sys.stdout is not None:
        try:
            sys.stdout.write(f"[{timestamp}] {color}{bold_code}{prefix}{Colors.ENDC} {message}\n")
            sys.stdout.flush()
        except:
            pass
    
    # Salva no arquivo (sem cores) com flush forçado
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
            f.flush()
            os.fsync(f.fileno()) # Garante gravação física no disco
    except Exception:
        pass

def debug(tag, message):
    _log(f"DEBUG:{tag}", message, Colors.OKBLUE)

def info(tag, message):
    _log(f"INFO:{tag}", message, Colors.OKCYAN, bold=True)

def success(tag, message):
    _log(f"SUCCESS:{tag}", message, Colors.OKGREEN, bold=True)

def warning(tag, message):
    _log(f"WARNING:{tag}", message, Colors.WARNING, bold=True)

def error(tag, message):
    _log(f"ERROR:{tag}", message, Colors.FAIL, bold=True)

def ai(message):
    _log("🤖 IA", message, Colors.HEADER, bold=True)

def vision(message):
    _log("👁️ VISION", message, Colors.OKCYAN)

def scanner(message):
    _log("📷 SCAN", message, Colors.OKBLUE)

def system(message):
    _log("⚙️ SYSTEM", message, Colors.BOLD)

class Timer:
    """Helper para medir tempo de execução."""
    def __init__(self, tag, message_prefix="concluído em"):
        self.tag = tag
        self.message_prefix = message_prefix
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        success(self.tag, f"{self.message_prefix} {elapsed:.2f}s")
