"""
gerar_licenca.py - Ferramenta do desenvolvedor para gerar chaves de licença.
Execute via terminal:  python tools/gerar_licenca.py

NÃO distribua este arquivo para os clientes.
"""

from __future__ import annotations

import sys
import os

# Garante que o módulo core seja encontrado
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.license import gerar_licenca, get_machine_id

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║          DocPopular — Gerador de Licenças                ║
║                  USO EXCLUSIVO INTERNO                   ║
╚══════════════════════════════════════════════════════════╝
"""


def main() -> None:
    try:
        print(BANNER)

        print("Machine ID desta máquina (para testes):")
        print(f"  → {get_machine_id()}\n")

        print("─" * 58)
        print("Digite os dados da licença:\n")

        machine_id = input("  Machine ID do cliente (Código de 16-32 chars): ").strip()
        if not machine_id:
            print("\n❌  Erro: Machine ID não pode ser vazio.")
            input("\nPressione Enter para sair...")
            return

        # Valida o formato básico (Machine ID gerado pelo app tem 24-32 chars)
        parts = machine_id.replace("-", "")
        if len(parts) < 10:
            print("\n❌  Erro: Machine ID muito curto ou inválido.")
            input("\nPressione Enter para sair...")
            return

        meses_str = input("  Validade em meses [padrão: 1]: ").strip()
        meses = 1
        if meses_str:
            try:
                meses = int(meses_str)
                if meses < 1:
                    raise ValueError
            except ValueError:
                print("\n❌  Erro: Número de meses inválido.")
                input("\nPressione Enter para sair...")
                return

        print("\n⚙️  Gerando licença...")
        chave = gerar_licenca(machine_id, meses)

        print("\n" + "═" * 58)
        print("✅  CHAVE DE LICENÇA GERADA COM SUCESSO\n")
        print(f"  {chave}")
        print("═" * 58)

        from datetime import date, timedelta
        expiry = (date.today() + timedelta(days=30 * meses)).strftime("%d/%m/%Y")
        print(f"\n  Machine ID : {machine_id}")
        print(f"  Validade   : {meses} mês(es) — expira em {expiry}")
        print("\n  Envie a chave ao cliente para ativação.")

        # Tenta copiar para clipboard (opcional)
        try:
            import subprocess
            subprocess.run(
                ["clip"],
                input=chave.encode(),
                check=False,
                capture_output=True,
            )
            print("  📋 Chave copiada para a área de transferência!\n")
        except Exception:
            pass
        
        input("Pressione Enter para fechar...")

    except Exception as e:
        print(f"\n❌  OCORREU UM ERRO INESPERADO:\n{str(e)}")
        import traceback
        traceback.print_exc()
        input("\nPressione Enter para fechar...")


if __name__ == "__main__":
    main()
