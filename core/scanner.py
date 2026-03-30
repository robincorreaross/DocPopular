"""
scanner.py - Motor de digitalização resiliente (Sincronizado com RossPDFEditor).
Suporta WIA (Windows Image Acquisition) e Modo Simulado para testes locais.
"""

from __future__ import annotations

import io
import os
import datetime
import threading
from pathlib import Path
from typing import List, Optional, Callable, Tuple
from PIL import Image

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

from core import logger

# GUID do formato PNG para o WIA
WIA_FORMAT_PNG = "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}"

def get_debug_log_path() -> Path:
    import sys
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = Path(base_dir) / "scanner_debug.log"
        # Garante que o arquivo existe
        if not p.exists():
            with open(p, "w", encoding="utf-8") as f: f.write("--- LOG INICIADO ---\n")
        return p
    except Exception:
        import tempfile
        return Path(tempfile.gettempdir()) / "DocPopular_scanner_debug.log"

def log_scanner_step(msg: str):
    """Grava log físico e imprime no console para debug imediato."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{now}] {msg}"
    # print(f"📷 SCAN {msg}") # Desativado em produção
    try:
        path = get_debug_log_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        pass

class ScannerEngine:
    """Motor de digitalização baseado em classe para isolamento de thread (padrão RossPDFEditor)."""
    
    def __init__(self):
        self._lock = threading.Lock()

    def list_scanners(self) -> List[str]:
        """Lista scanners WIA disponíveis. Retorna simulador se as bibliotecas falharem."""
        scanners = ["Simulador DocPopular"]
        
        if not pythoncom or not win32com:
            return scanners
            
        try:
            pythoncom.CoInitialize()
            try:
                manager = win32com.client.Dispatch("WIA.DeviceManager")
                for device in manager.DeviceInfos:
                    if device.Type == 1:  # 1 = Scanner
                        name = device.Properties("Name").Value
                        scanners.append(name)
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            log_scanner_step(f"Erro ao listar scanners WIA: {e}")
            
        return list(dict.fromkeys(scanners)) # Remove duplicatas mantendo ordem

    def scan(self, 
             device_name: str, 
             callback: Callable[[Optional[Image.Image], Optional[str]], None],
             status_callback: Callable[[str], None],
             dpi: int = 200):
        """Executa o scan em uma thread separada, reportando progresso."""
        
        def run_scan():
            log_scanner_step(f"=== INICIANDO PROCESSO DE SCAN: {device_name or 'Simulador DocPopular'} ===")
            status_callback("Iniciando...")
            
            # --- MODO SIMULADOR ---
            if device_name == "Simulador DocPopular" or not device_name:
                status_callback("Simulando aquisição...")
                import time
                time.sleep(1.0)
                # Gera uma imagem sólida cinza claro (estilo papel digitalizado)
                img = Image.new('RGB', (1654, 2339), color=(248, 248, 248))
                log_scanner_step("Simulador: Imagem gerada com sucesso.")
                status_callback("Scan simulado concluído.")
                callback(img, None)
                return

            if not pythoncom or not win32com:
                err = "Drivers WIA/COM não instalados no sistema."
                log_scanner_step(f"ERROR: {err}")
                callback(None, err)
                return

            img = None
            error_msg = None
            
            try:
                log_scanner_step("1. Inicializando COM...")
                pythoncom.CoInitialize()
                
                log_scanner_step(f"2. Conectando ao dispositivo: {device_name}")
                status_callback("Conectando...")
                manager = win32com.client.Dispatch("WIA.DeviceManager")
                
                target_device = None
                scanners_found = []
                for info in manager.DeviceInfos:
                    try:
                        name = info.Properties("Name").Value
                        scanners_found.append(name)
                        # Busca flexível: ignore case e substring
                        if device_name.lower() in name.lower() or name.lower() in device_name.lower():
                            target_device = info.Connect()
                            log_scanner_step(f"   MATCH ENCONTRADO: '{name}' corresponde a '{device_name}'")
                            break
                    except:
                        continue
                
                if not target_device:
                    msg = f"Scanner '{device_name}' não encontrado.\nScanners detectados: {', '.join(scanners_found) if scanners_found else 'Nenhum'}"
                    raise Exception(msg)
                
                log_scanner_step("3. Configurando parâmetros (DPI, Color)...")
                item = target_device.Items(1)
                
                # Configura DPI (Horizontal e Vertical)
                for prop_id in [6147, 6148]:
                    try: item.Properties(prop_id).Value = dpi
                    except: pass
                
                # Configura modo colorido (1 = Color, 2 = Gray, 4 = B&W)
                try: item.Properties(6146).Value = 1
                except: pass

                log_scanner_step("4. Solicitando transferência de imagem...")
                status_callback("Digitalizando...")
                
                image_wia = item.Transfer(WIA_FORMAT_PNG)
                
                log_scanner_step("5. Convertendo dados WIA para PIL...")
                status_callback("Processando...")
                image_bytes = bytes(image_wia.FileData.BinaryData)
                img = Image.open(io.BytesIO(image_bytes))
                img.load() # Garante que os dados foram lidos
                
                log_scanner_step("6. Finalizado com sucesso.")
                status_callback("Concluído!")
                
            except Exception as e:
                error_msg = str(e)
                log_scanner_step(f"FALHA CRÍTICA NO SCAN: {error_msg}")
            finally:
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass
                
            callback(img, error_msg)

        # Inicia a thread
        threading.Thread(target=run_scan, daemon=True).start()

def optimize_image(img: Image.Image) -> Image.Image:
    """Otimiza a imagem para economia de espaço mantendo legibilidade."""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Redimensiona se for maior que o necessário para IA (máximo 2000px na largura)
    if img.width > 2000:
        ratio = 2000 / img.width
        new_size = (2000, int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    return img
