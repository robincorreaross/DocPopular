---
name: supabase-keep-alive
description: Automatiza a configuração de um sistema de "keep-alive" no Supabase para evitar suspensão por inatividade no plano gratuito.
---

# Skill: Supabase Keep-alive

Esta skill configura um agendamento (cron job) no banco de dados Supabase que realiza uma operação de escrita diária, garantindo que o projeto permaneça ativo mesmo sem acessos externos.

## Pré-requisitos
Para aplicar esta skill, o agente precisa de:
- `SUPABASE_PROJECT_ID` (também conhecido como "Ref")
- `DATABASE_PASSWORD` (Senha definida na criação do projeto)
- `SERVICE_ROLE_KEY` (Opcional, mas útil para verificação via API)

## Como Usar

### 1. Preparar o SQL
O script SQL abaixo deve ser executado no projeto alvo. Ele:
- Ativa a extensão `pg_cron`.
- Cria uma tabela técnica para o ping.
- Define a função de atualização.
- Agenda o cron job para as 00:00 UTC todos os dias.

```sql
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
SELECT 1, current_setting('request.jwt.primary_owner', true)
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
SELECT cron.unschedule('antigravity-keep-alive') FROM cron.job WHERE jobname = 'antigravity-keep-alive';
SELECT cron.schedule('antigravity-keep-alive', '0 0 * * *', 'SELECT _antigravity.execute_keep_alive_ping()');
```

### 2. Automação via Script
Se o agente tiver acesso ao Node.js e puder instalar o pacote `pg`, utilize o script em `scripts/apply_keep_alive.js`:

```bash
node .agents/skills/supabase-keep-alive/scripts/apply_keep_alive.js --project <ID> --password <PASSWORD>
```

## Verificação
Após a aplicação, execute:
```sql
SELECT * FROM cron.job WHERE jobname = 'antigravity-keep-alive';
```
Se retornar uma linha, o sistema está configurado.
