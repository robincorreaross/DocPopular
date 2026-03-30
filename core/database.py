"""
database.py - Gerenciador do Banco de Dados SQLite Local com suporte Multi-Tenant.
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from core.config import APP_DATA_DIR

DB_PATH = APP_DATA_DIR / "docpopular.db"

def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão ativa com o banco SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Cria as tabelas do banco de dados na primeira execução."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # TABELA: pacientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                cpf TEXT,
                company_id TEXT,
                nome_completo TEXT NOT NULL,
                endereco_rua TEXT,
                endereco_num TEXT,
                data_nascimento DATE,
                data_emissao_doc DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'PENDING',
                PRIMARY KEY (cpf, company_id)
            )
        """)

        # TABELA: responsaveis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responsaveis (
                cpf_responsavel TEXT,
                cpf_paciente TEXT,
                company_id TEXT,
                nome TEXT NOT NULL,
                data_emissao_doc DATE,
                tem_procuracao INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'PENDING',
                PRIMARY KEY (cpf_responsavel, cpf_paciente, company_id),
                FOREIGN KEY(cpf_paciente, company_id) REFERENCES pacientes(cpf, company_id)
            )
        """)

        # TABELA: receitas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receitas (
                id TEXT PRIMARY KEY,
                cpf_paciente TEXT NOT NULL,
                company_id TEXT NOT NULL,
                data_receita DATE NOT NULL,
                crm_medico TEXT,
                nome_medico TEXT,
                is_anticoncepcional INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'PENDING',
                FOREIGN KEY(cpf_paciente, company_id) REFERENCES pacientes(cpf, company_id)
            )
        """)

        # TABELA: autorizacoes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autorizacoes (
                id TEXT PRIMARY KEY,
                cpf_paciente TEXT NOT NULL,
                company_id TEXT NOT NULL,
                numero_autorizacao TEXT NOT NULL,
                data_venda DATE NOT NULL,
                numero_cupom_fiscal TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'PENDING',
                FOREIGN KEY(cpf_paciente, company_id) REFERENCES pacientes(cpf, company_id)
            )
        """)

        # TABELA: arquivos_midia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_midia (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                entidade_tipo TEXT NOT NULL, 
                entidade_id TEXT NOT NULL, 
                path_local TEXT NOT NULL,
                path_nuvem TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'PENDING'
            )
        """)
        
        conn.commit()

# --- DAOs Genéricos e Helpers ---

def get_current_company_id(settings: dict) -> str:
    """Extrai ou computa o company_id a partir das configurações/licença"""
    # Temporário: Retorna o hash da license key, ou um fallback caso ainda não definida.
    from core.license import get_machine_id
    lic_key = settings.get("license_key", "")
    if lic_key:
        return lic_key.split("-")[0] if "-" in lic_key else lic_key[:8]
    return "default_company"

# ================= PACIENTES =================

def upsert_paciente(cpf: str, company_id: str, nome_completo: str, 
                    endereco_rua: str = "", endereco_num: str = "", 
                    data_nascimento: str | None = None, data_emissao_doc: str | None = None) -> bool:
    """Insere ou atualiza os dados de um paciente"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pacientes 
            (cpf, company_id, nome_completo, endereco_rua, endereco_num, data_nascimento, data_emissao_doc, updated_at, sync_status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'PENDING')
            ON CONFLICT(cpf, company_id) DO UPDATE SET 
                nome_completo=excluded.nome_completo,
                endereco_rua=excluded.endereco_rua,
                endereco_num=excluded.endereco_num,
                data_nascimento=excluded.data_nascimento,
                data_emissao_doc=excluded.data_emissao_doc,
                updated_at=CURRENT_TIMESTAMP,
                sync_status='PENDING';
        """, (cpf, company_id, nome_completo, endereco_rua, endereco_num, data_nascimento, data_emissao_doc))
        conn.commit()
    return True

def get_paciente(cpf: str, company_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pacientes WHERE cpf=? AND company_id=?", (cpf, company_id))
        row = cursor.fetchone()
        return dict(row) if row else None

# ================= RESPONSÁVEL =================
def upsert_responsavel(cpf_responsavel: str, cpf_paciente: str, company_id: str,
                       nome: str, data_emissao_doc: str | None = None, tem_procuracao: int = 0) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO responsaveis
            (cpf_responsavel, cpf_paciente, company_id, nome, data_emissao_doc, tem_procuracao, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ON CONFLICT(cpf_responsavel, cpf_paciente, company_id) DO UPDATE SET
                nome=excluded.nome,
                data_emissao_doc=excluded.data_emissao_doc,
                tem_procuracao=excluded.tem_procuracao,
                sync_status='PENDING';
        """, (cpf_responsavel, cpf_paciente, company_id, nome, data_emissao_doc, tem_procuracao))
        conn.commit()
    return True

# ================= RECEITAS =================
def insert_receita(cpf_paciente: str, company_id: str, data_receita: str,
                   crm_medico: str, nome_medico: str, is_anticoncepcional: int) -> str:
    rec_id = str(uuid.uuid4())
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO receitas
            (id, cpf_paciente, company_id, data_receita, crm_medico, nome_medico, is_anticoncepcional, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (rec_id, cpf_paciente, company_id, data_receita, crm_medico, nome_medico, is_anticoncepcional))
        conn.commit()
    return rec_id

# ================= AUTORIZACOES =================
def insert_autorizacao(cpf_paciente: str, company_id: str, numero_autorizacao: str,
                       data_venda: str, numero_cupom_fiscal: str) -> str:
    auth_id = str(uuid.uuid4())
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO autorizacoes
            (id, cpf_paciente, company_id, numero_autorizacao, data_venda, numero_cupom_fiscal, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        """, (auth_id, cpf_paciente, company_id, numero_autorizacao, data_venda, numero_cupom_fiscal))
        conn.commit()
    return auth_id

# ================= ARQUIVOS MÍDIA =================

def insert_arquivo_midia(company_id: str, entidade_tipo: str, entidade_id: str, path_local: str) -> str:
    """Registra o arquivo salvo no banco. Retorna o ID (UUID V4)."""
    midia_id = str(uuid.uuid4())
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO arquivos_midia (id, company_id, entidade_tipo, entidade_id, path_local, sync_status)
            VALUES (?, ?, ?, ?, ?, 'PENDING')
        """, (midia_id, company_id, entidade_tipo, entidade_id, path_local))
        conn.commit()
    return midia_id

def list_arquivos_midia_pendentes() -> List[Dict[str, Any]]:
    """Usado pelo SyncManager para achar quem precisa ser sincronizado."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM arquivos_midia WHERE sync_status = 'PENDING'")
        return [dict(row) for row in cursor.fetchall()]

def mark_arquivo_midia_synced(midia_id: str, path_nuvem: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE arquivos_midia 
            SET sync_status='SYNCED', path_nuvem=?
            WHERE id=?
        """, (path_nuvem, midia_id))
        conn.commit()

def get_arquivos_by_entidade(company_id: str, entidade_tipo: str, entidade_id: str) -> List[Dict[str, Any]]:
    """Busca arquivos vinculados a uma entidade (ex: paciente, receita)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM arquivos_midia 
            WHERE company_id=? AND entidade_tipo=? AND entidade_id=?
            ORDER BY created_at ASC
        """, (company_id, entidade_tipo, entidade_id))
        return [dict(row) for row in cursor.fetchall()]

def list_pacientes_by_nome_ou_cpf(company_id: str, query: str) -> List[Dict[str, Any]]:
    """Busca rápida de pacientes por parte do nome ou CPF."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM pacientes 
            WHERE company_id=? AND (cpf LIKE ? OR nome_completo LIKE ?)
            LIMIT 20
        """, (company_id, f"%{query}%", f"%{query}%"))
        return [dict(row) for row in cursor.fetchall()]

# Init imediato ao importar (criação rápida)
init_db()
