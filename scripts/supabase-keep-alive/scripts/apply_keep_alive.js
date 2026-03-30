const { Client } = require('pg');

const args = process.argv.slice(2);
const projectRef = args.find(a => a.startsWith('--project='))?.split('=')[1];
const password = args.find(a => a.startsWith('--password='))?.split('=')[1];

if (!projectRef || !password) {
    console.error('Uso: node apply_keep_alive.js --project=<REF> --password=<PASSWORD>');
    process.exit(1);
}

const connectionString = `postgresql://postgres:${password}@db.${projectRef}.supabase.co:5432/postgres`;

const sql = `
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
SELECT 1, '${projectRef}'
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

-- 6. Agendar o job
SELECT cron.unschedule('antigravity-keep-alive') FROM cron.job WHERE jobname = 'antigravity-keep-alive';
SELECT cron.schedule('antigravity-keep-alive', '0 0 * * *', 'SELECT _antigravity.execute_keep_alive_ping()');
`;

async function run() {
    const client = new Client({ connectionString });
    try {
        console.log(`Conectando ao projeto ${projectRef}...`);
        await client.connect();
        console.log('Aplicando configurações de keep-alive...');
        await client.query(sql);
        console.log('✅ Sucesso! O sistema de keep-alive foi configurado.');
    } catch (err) {
        console.error('❌ Erro ao aplicar keep-alive:', err.message);
    } finally {
        await client.end();
    }
}

run();
