import psycopg2
import sys

# Configurações fornecidas pelo usuário
CONN_STRING = "postgresql://postgres:95SYtXkAOfFEHgug@db.qyacinkmkvbbvrxvkfhv.supabase.co:5432/postgres"

KEEP_ALIVE_SQL = """
-- 1. Garantir que a extensão pg_cron exista
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Criar esquema técnico se não existir
CREATE SCHEMA IF NOT EXISTS _antigravity;

-- 3. Criar tabela de controle de pulsação
CREATE TABLE IF NOT EXISTS _antigravity.keep_alive (
    id SERIAL PRIMARY KEY,
    last_ping TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    project_ref TEXT
);

-- 4. Inserir registro inicial
INSERT INTO _antigravity.keep_alive (id, project_ref) 
SELECT 1, 'qyacinkmkvbbvrxvkfhv'
WHERE NOT EXISTS (SELECT 1 FROM _antigravity.keep_alive WHERE id = 1);

-- 5. Criar função que realiza o ping
CREATE OR REPLACE FUNCTION _antigravity.execute_keep_alive_ping()
RETURNS void AS $$
BEGIN
    UPDATE _antigravity.keep_alive 
    SET last_ping = NOW()
    WHERE id = 1;
END;
$$ LANGUAGE plpgsql;

-- 6. Agendar o job (limpa o anterior se houver para evitar duplicados)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'antigravity-keep-alive') THEN
        PERFORM cron.unschedule('antigravity-keep-alive');
    END IF;
END $$;

SELECT cron.schedule('antigravity-keep-alive', '0 0 * * *', 'SELECT _antigravity.execute_keep_alive_ping()');
"""

SCHEMA_SQL = """
-- TABELAS DO DOCPOPULAR --

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
);

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
);

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
);

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
);

CREATE TABLE IF NOT EXISTS arquivos_midia (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    entidade_tipo TEXT NOT NULL, 
    entidade_id TEXT NOT NULL, 
    path_local TEXT NOT NULL,
    path_nuvem TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'PENDING'
);
"""

def apply():
    try:
        print(f"Conectando ao Supabase...")
        conn = psycopg2.connect(CONN_STRING)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Aplicando Keep-alive...")
        cur.execute(KEEP_ALIVE_SQL)
        
        print("Aplicando Schema do Projeto...")
        cur.execute(SCHEMA_SQL)
        
        print("✅ Configuração aplicada com sucesso!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao aplicar configuração: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply()
