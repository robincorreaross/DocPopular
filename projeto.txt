Vamos criar uma aplicação desktop para windows que irá scanear documentos, receitas medicas, laudos etc, afim de guardar esses dados para futuras auditorias do programa farmacia popular do brasil. O aplicativo seguirá alguns lógicas dependendo do tipo de transação e após coletar todas as imagens irá salvar o arquivo em formato PDF seguindo uma norma:

AUTORIZAÇÃO 111.222.333.444.555 - DATA 01-01-2021.pdf

No cabeçalho de cada página do PDF deve conter essa descrição (AUTORIZAÇÃO 111.222.333.444.555 - DATA 01-01-2021)

Existirão três tipos de transações:

1 Próprio Paciente
2 Procurador
3 Menor de Idade

1 Próprio Paciente:
Solicitar a seguinte ordem de documentos:
a) Cupom Fiscal com o Cupom Vinculado
b) Receita Médica e/ou Laudo Médico
c) Documento de Identificação do paciente da receita
Em cada solicitação sempre perguntar se existe mais páginas, caso não haja, prosseguir para próximo passo.

2 Procurador:
Solicitar a seguinte ordem de documentos:
a) Cupom Fiscal com o Cupom Vinculado
b) Receita Médica e/ou Laudo Médico
c) Documento de Identificação do paciente da receita
d) Documento de Identificação do procurador do paciente
e) Procuração
Em cada solicitação sempre perguntar se existe mais páginas, caso não haja, prosseguir para próximo passo.

3 Menor de Idade:
a) Cupom Fiscal com o Cupom Vinculado
b) Receita Médica e/ou Laudo Médico
c) Documento de Identificação do paciente da receita ou Certidão de Nascimento
d) Documento de Identificação do responsável do paciente
Em cada solicitação sempre perguntar se existe mais páginas, caso não haja, prosseguir para próximo passo.

Após a digitalização de todos os documentos, o sistema usará IA para ler todos os documentos digitalizados e fará uma auditoria baseado no prompt específico que está no arquivo master_prompt.md

Se estiver tudo ok, a transação será salva num único arquivo PDF.
Caso a análise não aprova a transação, deve ser mostrada uma mensagem de alerta mostrando o(s) erro(s) pedindo para analisar o erro cancelando toda a digitalização.
