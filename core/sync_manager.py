"""
sync_manager.py - Gerenciador de Sincronização em Background (SQLite <-> Supabase)
"""

import threading
import time
import psycopg2
from typing import List, Dict, Any, Optional
from core.database import get_connection
from core.config import load_settings

# String de conexão do Supabase (postgres)
SUPABASE_CONN = "postgresql://postgres:95SYtXkAOfFEHgug@db.qyacinkmkvbbvrxvkfhv.supabase.co:5432/postgres"

class SyncManager:
    def __init__(self, interval_sec: int = 15):
        self.interval = interval_sec
        self._stop_event = threading.Event()
        self._thread = None
        self._remote_conn = None

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            print("[SyncManager] Iniciado.")

    def stop(self):
        print("[SyncManager] Parando...")
        self._stop_event.set()
        if self._thread:
            # Não esperamos join se estivermos fechando a GUI para evitar travar a main thread
            # mas o event garante que o loop interno pare.
            self._thread.join(timeout=1.0)
        
        if self._remote_conn:
            try: self._remote_conn.close()
            except: pass
            self._remote_conn = None

    def _get_remote_conn(self):
        """Mantém uma conexão persistente ou reconecta se necessário."""
        if self._remote_conn:
            try:
                # Teste rápido de conexão
                with self._remote_conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self._remote_conn
            except:
                self._remote_conn = None
        
        try:
            self._remote_conn = psycopg2.connect(SUPABASE_CONN)
            self._remote_conn.autocommit = True
            return self._remote_conn
        except Exception as e:
            print(f"[SyncManager] Falha ao conectar no Supabase: {e}")
            return None

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._sync_all()
            except Exception as e:
                print(f"[SyncManager] Erro durante sincronização: {e}")
            
            # Espera pelo intervalo OU pelo sinal de parada
            if self._stop_event.wait(self.interval):
                break

    def _sync_all(self):
        """Sincroniza todas as tabelas pendentes em uma única rodada."""
        conn = self._get_remote_conn()
        if not conn:
            return

        # Sincroniza tabelas na ordem de dependência
        self._sync_table(conn, "pacientes", ["cpf", "company_id", "nome_completo", "endereco_rua", "endereco_num", "data_nascimento", "data_emissao_doc"])
        self._sync_table(conn, "responsaveis", ["cpf_responsavel", "cpf_paciente", "company_id", "nome", "data_emissao_doc", "tem_procuracao"])
        self._sync_table(conn, "receitas", ["id", "cpf_paciente", "company_id", "data_receita", "crm_medico", "nome_medico", "is_anticoncepcional"])
        self._sync_table(conn, "autorizacoes", ["id", "cpf_paciente", "company_id", "numero_autorizacao", "data_venda", "numero_cupom_fiscal"])
        self._sync_table(conn, "arquivos_midia", ["id", "company_id", "entidade_tipo", "entidade_id", "path_local"])

    def _format_date(self, val: Any) -> Any:
        """Converte DD/MM/YYYY para YYYY-MM-DD para o Postgres."""
        if not val or not isinstance(val, str):
            return val
        
        # Se parece data brasileira DD/MM/YYYY
        if len(val) == 10 and val[2] == "/" and val[5] == "/":
            parts = val.split("/")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return val

    def _sync_table(self, remote_conn, table_name: str, columns: List[str]):
        """Sincroniza uma tabela genérica usando UPSERT (ON CONFLICT)."""
        with get_connection() as local_conn:
            cursor = local_conn.cursor()
            cursor.execute(f"SELECT {', '.join(columns)} FROM {table_name} WHERE sync_status = 'PENDING'")
            rows = cursor.fetchall()
            
            if not rows:
                return

            print(f"[SyncManager] Sincronizando {len(rows)} registros em {table_name}...")
            
            # Montar query de Upsert (Postgres)
            pk_cols = ["id"]
            if table_name == "pacientes": pk_cols = ["cpf", "company_id"]
            if table_name == "responsaveis": pk_cols = ["cpf_responsavel", "cpf_paciente", "company_id"]
            
            col_list = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))
            update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col not in pk_cols])
            conflict_target = ", ".join(pk_cols)

            upsert_query = f"""
                INSERT INTO {table_name} ({col_list})
                VALUES ({placeholders})
                ON CONFLICT ({conflict_target}) DO UPDATE SET {update_clause};
            """

            with remote_conn.cursor() as remote_cur:
                for row in rows:
                    try:
                        sanitized_values = []
                        for col_idx, val in enumerate(row):
                            # Decode bytes
                            if isinstance(val, bytes):
                                val = val.decode("utf-8", errors="replace")
                            
                            # Formata datas (nascimento e emissao costumam estar nos indices 5, 6 ou 4, 3)
                            # Para ser seguro, tentamos formatar qualquer string que pareça data brasileira
                            val = self._format_date(val)
                            
                            sanitized_values.append(val)

                        remote_cur.execute(upsert_query, tuple(sanitized_values))
                        self._mark_local_synced(table_name, pk_cols, row)
                    except Exception as e:
                        print(f"  - Erro no registro {row[0]}: {e}")

    def _mark_local_synced(self, table_name: str, pk_cols: List[str], row: Any):
        where_clause = " AND ".join([f"{col} = ?" for col in pk_cols])
        pk_values = tuple(row[col] for col in pk_cols)
        
        with get_connection() as conn:
            conn.execute(f"UPDATE {table_name} SET sync_status = 'SYNCED' WHERE {where_clause}", pk_values)
            conn.commit()

# Instância global
sync_manager = SyncManager(interval_sec=15)
