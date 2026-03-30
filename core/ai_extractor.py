"""
ai_extractor.py - Extração e classificação de documentos usando OpenAI GPT-4o-mini.
"""

import base64
import io
import json
from openai import OpenAI
from core import logger

def encode_image(pil_img):
    """Converte imagem PIL para base64 com alta qualidade para OCR."""
    buffered = io.BytesIO()
    pil_img.save(buffered, format="JPEG", quality=95)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

import os
from dotenv import load_dotenv

# Carrega ambiente local, se existir
load_dotenv()

def get_openai_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.error("AI", "A chave OPENAI_API_KEY não foi encontrada nas variáveis de ambiente.")
        # Em ambiente de produção, não vamos crashar aqui para evitar RuntimeErrors,
        # daremos o erro genérico na chamada.
    return key


def _call_openai(pil_img, prompt, max_tokens=500):
    """Chamada genérica para a API OpenAI com imagem."""
    logger.ai(f"Chamando GPT-4o-mini (max_tokens={max_tokens})...")
    client = OpenAI(api_key=get_openai_api_key())
    base64_image = encode_image(pil_img)

    with logger.Timer("AI", "Requisição OpenAI finalizada em"):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Você é uma API que SEMPRE responde com um JSON válido e nunca inclui texto Markdown."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.0
            )

            content = response.choices[0].message.content
            if not content:
                return {"error": "Resposta da IA veio vazia."}

            content = content.strip()
            if content.startswith("```"):
                parts = content.split("```")
                if len(parts) > 1:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:].strip()

            try:
                parsed_data = json.loads(content)
                logger.info("AI", f"JSON recebido com sucesso: {list(parsed_data.keys())}")
                
                # Exibe a transcrição bruta no terminal para debug (conforme solicitado pelo usuário)
                if "transcricao_bruta" in parsed_data:
                    raw_text = parsed_data["transcricao_bruta"]
                    logger.debug("OCR", "--- INÍCIO DA TRANSCRIÇÃO BRUTA IA ---")
                    print(f"\033[36m{raw_text}\033[0m") # Ciano para OCR
                    logger.debug("OCR", "--- FIM DA TRANSCRIÇÃO BRUTA IA ---")
                
                # Log dos campos extraídos para debug
                logger.info("AI", f"  tipo_documento: {parsed_data.get('tipo_documento')}")
                logger.info("AI", f"  nome: {parsed_data.get('nome')}")
                logger.info("AI", f"  cpf: {parsed_data.get('cpf')}")
                logger.info("AI", f"  data_nascimento: {parsed_data.get('data_nascimento')}")
                logger.info("AI", f"  data_emissao: {parsed_data.get('data_emissao')}")

                return parsed_data
            except json.JSONDecodeError:
                logger.error("AI", f"Falha ao decodificar JSON. Retorno original: {content[:100]}...")
                return {"error": "Falha ao decodificar JSON da IA"}

        except Exception as e:
            logger.error("AI", f"Erro na requisição OpenAI: {str(e)}")
            return {"error": str(e)}


def extract_and_classify(pil_img):
    """
    Classifica o tipo de documento, extrai dados e avalia qualidade em uma única chamada.
    Retorna dict com campos:
      - tipo_documento: RG, CIN, CNH, CERTIDAO_NASCIMENTO, RECEITA, LAUDO, CUPOM, PROCURACAO, DESCONHECIDO
      - tipo_face: COMPLETO, FRENTE, VERSO
      - nome, cpf, data_nascimento, data_emissao
      - legivel (bool)
      - transcricao_bruta
    """
    prompt = (
        "Você é um especialista em análise e classificação de documentos brasileiros. "
        "Analise a imagem e retorne um JSON com os seguintes campos obrigatórios:\n\n"

        "1. \"tipo_documento\": Classifique entre: "
        "\"RG\", \"CIN\", \"CNH\", \"CERTIDAO_NASCIMENTO\", \"RECEITA\", \"LAUDO\", "
        "\"CUPOM\", \"PROCURACAO\", \"TERMO_DIGNIDADE\", \"INTERDICAO\", \"DESCONHECIDO\".\n"
        "   - RG: Carteira de Identidade antiga com 'SECRETARIA DE SEGURANÇA PÚBLICA'.\n"
        "   - CIN: Carteira de Identidade Nacional (novo modelo, QR Code).\n"
        "   - CNH: Carteira Nacional de Habilitação.\n"
        "   - CERTIDAO_NASCIMENTO: Certidão de Nascimento.\n\n"

        "2. \"tipo_face\": \"COMPLETO\" se FOTO e CPF visíveis. "
        "\"FRENTE\" se só FOTO. \"VERSO\" se só dados/CPF.\n\n"

        "3. \"transcricao_bruta\": Transcrição COMPLETA de TODO o texto visível na imagem, "
        "incluindo nomes de campos, números, carimbos. Ser minucioso.\n\n"

        "4. \"nome\": Nome completo em MAIÚSCULAS. "
        "Leia do campo rotulado 'NOME'. null se não encontrado.\n\n"

        "5. \"cpf\": ATENÇÃO MÁXIMA NESTE CAMPO!\n"
        "   O CPF é um número de 11 dígitos que aparece ao lado do rótulo 'CPF' ou 'CPF/MF'.\n"
        "   Em RGs antigos, o CPF pode ter 3 formatos:\n"
        "     a) Com BARRA: '933131285/72' → retorne '93313128572'\n"
        "     b) Com PONTOS e TRAÇO: '933.131.285-72' → retorne '93313128572'\n"
        "     c) Só dígitos: '93313128572' → retorne '93313128572'\n"
        "   SEMPRE retorne APENAS os 11 dígitos numéricos.\n"
        "   CUIDADO: os seguintes números NÃO são CPF, IGNORE-OS:\n"
        "     - 'Registro Geral' ou 'RG' (número de identidade)\n"
        "     - 'T. Eleitor' (título de eleitor)\n"
        "     - 'CTPS' (carteira de trabalho)\n"
        "     - 'CNH' (habilitação)\n"
        "     - 'Série' ou 'SÉRIE'\n"
        "     - 'CNS' (cartão nacional de saúde)\n"
        "   Se o CPF estiver como '000.000.000-00' ou similar com todos zeros, retorne null.\n"
        "   null se não encontrado.\n\n"

        "6. \"data_nascimento\": Formato DD/MM/AAAA. ATENÇÃO REDOBRADA!\n"
        "   Leia do campo rotulado 'DATA NASCIMENTO', 'DATA DE NASCIMENTO' ou 'NASCIMENTO'.\n"
        "   No RG, esse campo fica na FRENTE (lado da foto), geralmente abaixo da FILIAÇÃO.\n"
        "   REGRAS DE OURO PARA DATAS:\n"
        "     - Verifique cada dígito DUAS VEZES (Double-Check).\n"
        "     - CUIDADO: Os meses '01' (janeiro) e '02' (fevereiro) são frequentemente confundidos. Olhe atentamente.\n"
        "     - Valide a data contra a sua 'transcricao_bruta' antes de finalizar.\n"
        "     - Se estiver em dúvida entre dois números, use o que faz mais sentido no contexto brasileiro.\n"
        "   Copie EXATAMENTE os números. null se não encontrado.\n\n"

        "7. \"data_emissao\": Formato DD/MM/AAAA.\n"
        "   Leia do campo 'DATA DE EXPEDIÇÃO' ou 'DATA DA EXPEDIÇÃO'.\n"
        "   No RG, esse campo fica no VERSO (lado oposto à foto).\n"
        "   Aplique a mesma REGRA DE OURO de conferência dupla.\n"
        "   Copie EXATAMENTE. null se não encontrado.\n\n"

        "8. \"legivel\": true se legível, false se ilegível.\n\n"

        "REGRAS CRÍTICAS:\n"
        "- LEIA EXATAMENTE OS CARACTERES DA IMAGEM. NÃO INVENTE DADOS.\n"
        "- Faça a transcrição bruta PRIMEIRO, sendo extremamente minucioso nos números das datas.\n"
        "- O documento pode estar ROTACIONADO ou ABERTO (frente+verso visíveis).\n"
        "- Para o CPF, se houver barra (ex: 933131285/72), ignore a barra e retorne os 11 dígitos.\n"
        "- Se uma informação não estiver legível, retorne null.\n"
    )

    return _call_openai(pil_img, prompt, max_tokens=800)


def extract_document_data(pil_img):
    """
    Função legada mantida para compatibilidade.
    Delega para extract_and_classify() que é mais completa.
    """
    return extract_and_classify(pil_img)

