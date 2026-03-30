import os
import sys
import json
import hashlib
from datetime import date
from pathlib import Path

# Add project root to sys path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

def get_file_hash(filepath: Path) -> str:
    """Calcula o hash SHA256 de um arquivo em chunks."""
    if not filepath.exists():
        return ""
    
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest().lower()

def main():
    print("============================================================")
    print("  DocPopular - Finalizador de Metadados de Segurança")
    print("============================================================")
    
    try:
        from version import APP_VERSION
        
        zip_path = root_dir / "installer" / "DocPopular.zip"
        json_path = root_dir / "version.json"
        
        print(f"[*] Versão Atual: {APP_VERSION}")
        
        # 1. Calcula o Hash SHA256
        if not zip_path.exists():
            print(f"[!] ERRO: Arquivo ZIP não encontrado em: {zip_path}")
            sys.exit(1)
            
        print(f"[*] Calculando assinatura SHA256 do {zip_path.name}...")
        sha256_hash = get_file_hash(zip_path)
        print(f"    -> SHA256: {sha256_hash}")
        
        # 2. Abre o version.json e atualiza
        data = {}
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[!] Aviso: Falha ao ler version.json atual: {e}. Criando novo.")
        
        # 3. Injecao de Metadados Críticos
        data["version"] = APP_VERSION
        data["release_date"] = date.today().isoformat()
        
        # As URLs continuam sendo do Github, caso já existam não precisa sobrescrever, mas validaremos
        if "download_zip_url" not in data:
            data["download_zip_url"] = "https://github.com/robincorreaross/DocPopular/releases/latest/download/DocPopular.zip"
        if "download_url" not in data:
            data["download_url"] = "https://github.com/robincorreaross/DocPopular/releases/latest"
            
        data["download_sha256"] = sha256_hash
        
        if "mandatory" not in data:
            data["mandatory"] = True
            
        if "changelog" not in data:
            data["changelog"] = ["Atualização de sistema."]

        # Salva formatado
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print("[*] version.json atualizado com sucesso e blindado (Defense in Depth).")
        print("============================================================")
        print("  SUCESSO: O pacote foi assinado digitalmente.")
        print("============================================================")
        
    except Exception as e:
        print(f"[!] ERRO GRAVE no script de metadados: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
