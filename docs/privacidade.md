# Política de Privacidade — PRÓLOGOS

Última atualização: 2026-01-25

Esta Política de Privacidade explica como o PRÓLOGOS (“Plataforma”) trata dados pessoais quando você utiliza nossos serviços. Ela deve ser lida em conjunto com os [Termos de Uso](./termos.md).

> **Aviso:** este documento é um modelo inicial. Dependendo do seu fluxo real (logs, autenticação, pagamentos, provedores etc.), pode ser necessário complementar e revisar juridicamente.

## 1. Papéis (LGPD)

Em regra:

- **Controlador**: PRÓLOGOS (responsável por decisões sobre o tratamento).
- **Operadores**: provedores e serviços utilizados para operar a Plataforma (ex.: infraestrutura, armazenamento, APIs de modelos), quando aplicável.

## 2. Quais dados podem ser tratados

Dependendo do uso, podemos tratar:

- **Dados fornecidos pelo usuário**: textos, informações de processos, metadados e arquivos enviados (ex.: PDFs).
- **Dados técnicos**: informações de dispositivo/navegador, logs de acesso, data/hora, identificadores e métricas de desempenho (na medida em que existirem no ambiente).
- **Dados de terceiros**: informações provenientes de bases públicas consultadas para fins de jurimetria (ex.: DataJud/CNJ), conforme disponibilidade e regras dessas bases.

## 3. Finalidades do tratamento

Podemos tratar dados para:

- disponibilizar funcionalidades (análises, dossiês, simulações e relatórios);
- melhorar a qualidade, segurança e estabilidade da Plataforma;
- prevenir fraude, abuso e uso indevido;
- cumprir obrigações legais e responder a solicitações de autoridades, quando necessário.

## 4. Bases legais (LGPD)

As bases legais podem variar conforme o caso, incluindo:

- **execução de contrato** e/ou procedimentos preliminares a pedido do titular;
- **legítimo interesse**, observados os limites e avaliações aplicáveis;
- **cumprimento de obrigação legal/regulatória**;
- **consentimento**, quando aplicável (por exemplo, para certas finalidades específicas).

## 5. Compartilhamento de dados

Podemos compartilhar dados:

- com provedores de infraestrutura/serviços necessários ao funcionamento da Plataforma;
- com serviços de processamento de linguagem/IA, quando acionados para gerar análises (por exemplo, provedores de LLM para “dossiê”/“parecer”, quando configurados);
- mediante ordem legal, obrigação regulatória ou para proteção de direitos.

Não vendemos dados pessoais.

### 5.1. Provedores de IA/LLM (ex.: Groq)

Quando você utiliza recursos que geram texto por IA (ex.: “dossiê” e/ou “parecer”), partes do conteúdo fornecido e/ou recuperado pela Plataforma (ex.: texto de petição, trechos de decisões, contexto informado) **podem ser enviados a um provedor externo** para processamento.

Recomendação: **evite incluir dados pessoais sensíveis desnecessários** nos documentos e textos enviados.

## 6. Transferências internacionais

Dependendo dos provedores utilizados, dados podem ser processados em outros países. Nesses casos, adotamos salvaguardas compatíveis com a legislação aplicável.

## 7. Retenção e descarte

Retemos dados pelo tempo necessário para:

- prestar o serviço;
- cumprir obrigações legais;
- resguardar direitos e prevenir abuso.

Quando possível, aplicamos descarte ou anonimização após o término da necessidade.

### 7.1. Retenção técnica (estado atual do projeto)

No estado atual:

- **Uploads (PDFs)**: são processados **em memória** para gerar análises; não há persistência intencional do arquivo no disco pelo backend (salvo comportamento do ambiente de deploy/infra).
- **Cache DataJud**: para reduzir carga e risco de bloqueio, pode existir um cache local em SQLite (`backend/datajud_cache.sqlite3`) com TTL configurável (padrão: 7 dias).
- **Jobs de clonagem**: o status/resultado de jobs pode ficar armazenado no Redis por um período configurável (TTL), para permitir consulta de progresso e reprocessamento controlado.
- **Logs**: podem conter metadados técnicos (ex.: tempos, rotas, códigos HTTP, requestId). Não devem incluir conteúdo integral de petições/decisões nem segredos.

## 8. Segurança da informação

Empregamos medidas razoáveis de segurança para proteger os dados contra acesso não autorizado, perda, alteração ou divulgação indevida. Nenhum sistema é 100% seguro; por isso, não podemos garantir segurança absoluta.

## 9. Direitos do titular

Você pode solicitar, nos termos da LGPD:

- confirmação e acesso;
- correção;
- anonimização, bloqueio ou eliminação (quando aplicável);
- portabilidade (quando aplicável);
- informação sobre compartilhamentos;
- revogação de consentimento (quando aplicável);
- oposição a tratamentos baseados em legítimo interesse, quando cabível.

## 10. Como entrar em contato

Para exercer direitos ou tirar dúvidas:

- Canal preferencial: [GitHub Issues](https://github.com/jrlampa/prologos/issues)

## 11. Alterações desta Política

Podemos atualizar esta Política periodicamente. A data de “Última atualização” indicará a versão vigente.
