# Dashboard de Análise Financeira ACS - Documento de Requisitos do Produto (PRD)

**Versão:** 1.1
**Autor:** John (PM), Sarah (PO)

## 1. Metas e Contexto de Fundo

### Metas
- Desenvolver um dashboard de análise para identificar perdas e ganhos financeiros nos repasses federais para ACS.
- Fornecer duas visões: uma **Visão Municipal** detalhada e temporal (últimos 3 meses) e uma **Visão Estadual** comparativa (um único mês).
- Garantir uma interface simples, clara e otimizada para gestores não técnicos.
- Assegurar alta performance na Visão Estadual através de um sistema de pré-processamento e cache de dados.
- Habilitar um fallback para consulta de API ao vivo na Visão Municipal para dados não cacheados.

### Contexto de Fundo
A gestão dos repasses para ACS é complexa, e os municípios carecem de ferramentas para identificar perdas financeiras. Este projeto cria um sistema de dashboards de duas camadas para resolver este problema, com uma arquitetura que separa a coleta de dados (processo offline) da visualização (interface online), garantindo uma experiência de usuário rápida e resiliente.

### Log de Alterações
| Data | Versão | Descrição | Autor |
| :--- | :--- | :--- | :--- |
| 20/07/2025 | 1.0 | Rascunho inicial do PRD. | John (PM) |
| 20/07/2025 | 1.1 | PRD revisado e validado pela PO. | Sarah (PO) |

## 2. Requisitos

### Requisitos Funcionais (FR)
- **FR1:** Implementar a Visão Municipal.
- **FR2:** Implementar a Visão Estadual.
- **FR3:** Exibir KPIs Municipais com comparativo mensal.
- **FR4:** Exibir Gráficos Municipais de Análise Financeira e de Pessoal.
- **FR5:** Exibir KPIs Estaduais Agregados.
- **FR6:** Implementar Tabela Estadual Interativa (ordenável e com busca).
- **FR7:** Habilitar Navegação (Drill-Down) da Visão Estadual para a Municipal.
- **FR8:** Criar um Coletor de Dados Offline (`coletor_dados.py`) que gere um banco de dados local (SQLite).
- **FR9:** Implementar lógica de fallback na Visão Municipal para consultar a API ao vivo se os dados não estiverem no banco local.

### Requisitos Não Funcionais (NFR)
- **NFR1:** A Visão Estadual deve carregar dados exclusivamente do banco local.
- **NFR2:** A Visão Municipal deve priorizar o carregamento do banco local.
- **NFR3:** A interface do usuário deve ser minimalista e clara.
- **NFR4:** Tecnologia restrita a Streamlit, Plotly, e Pandas.
- **NFR5:** O cálculo da perda deve usar o valor de R$ 3.036,00/agente, mas ser facilmente atualizável no código.
- **NFR6:** A arquitetura de código deve ser modular.

## 3. Estratégia de Implantação
A implantação será via Streamlit Community Cloud, acionada por `git push` na branch principal. O `requirements.txt` garantirá a consistência do ambiente.

## 4. Épicos e Estórias de Usuário

### Épico 1: Plataforma de Coleta e Armazenamento de Dados de ACS
**Meta:** Construir a ferramenta para coletar, processar e armazenar localmente os dados de ACS para um estado inteiro, cobrindo múltiplas competências.

- **Estória 1.1: Desenvolvimento do Coletor de Dados Estadual Multi-Competência**
  - **Critérios de Aceitação:**
    1. O script `coletor_dados.py` aceita UF e lista de competências como argumentos.
    2. Itera por todos os municípios e competências, reutilizando a lógica de cálculo.
    3. Implementa política de retentativas (3x com pausa) e logging de erros.
    4. Salva os dados consolidados em um único arquivo de banco de dados: `data/dados_UF.sqlite`.
    5. Exibe progresso claro durante a execução.
    6. Cria a estrutura de diretórios inicial (`pages`, `data`).
    7. Cria o `requirements.txt`.
    8. A lógica de API (com headers e tratamento de erro) é centralizada no módulo `saude_api.py`.

### Épico 2: Dashboards de Análise Municipal e Estadual
**Meta:** Construir as interfaces de visualização que leem exclusivamente do banco de dados local criado no Épico 1, com fallback para API ao vivo.

- **Estória 2.1: Interface da Visão Municipal com Fallback para API ao Vivo**
  - **Critérios de Aceitação:**
    1. A página tem seletores de Estado, Município e Competência.
    2. O sistema primeiro tenta buscar os dados no banco de dados local.
    3. Se encontrados, carrega instantaneamente.
    4. Se não encontrados, exibe uma mensagem informativa e executa uma consulta de API ao vivo.
    5. KPIs e gráficos são exibidos corretamente, independentemente da fonte dos dados.

- **Estória 2.2: Interface da Visão Estadual**
  - **Critérios de Aceitação:**
    1. A página tem seletores de Estado e Competência, populados com base nos dados disponíveis no banco local.
    2. Carrega dados de todos os municípios instantaneamente do banco local.
    3. KPIs estaduais agregados são calculados e exibidos.
    4. A tabela comparativa (com variações vs. mês anterior) é exibida.
    5. A tabela é ordenável, com busca e com cores de destaque.

- **Estória 2.3: Implementação da Navegação Drill-Down**
  - **Critérios de Aceitação:**
    1. O nome do município na tabela estadual é um link.
    2. Clicar no link navega para a Visão Municipal.
    3. O estado e município corretos são carregados automaticamente na Visão Municipal.

## 5. Ordem de Implementação Sugerida
1. Estória 1.1 (Coletor de Dados)
2. Estória 2.2 (Visão Estadual)
3. Estória 2.1 (Visão Municipal)
4. Estória 2.3 (Drill-Down)
```---

**Fase 3: Início do Desenvolvimento com Agentes BMad**

Agora que o plano está no seu projeto, vamos começar o ciclo de desenvolvimento no Claude Code.

1.  **Ative o Agente Product Owner (PO):**
    *   Abra o chat do Claude no VS Code (`Ctrl+Shift+P` e procure por "Claude: New Chat").
    *   No chat, digite: `/po` e pressione Enter. O Claude agora está agindo como a Sarah, a PO.

2.  **Divida (Shard) o PRD:**
    *   Esta etapa não é estritamente necessária, pois nosso PRD já está bem organizado. Mas como prática, vamos pedir para a PO organizar as estórias.
    *   No mesmo chat, digite o prompt:
        `Por favor, revise o PRD em @docs/prd.md e crie arquivos de estória de usuário individuais para cada uma das 4 estórias na pasta 'docs/stories/'.`

3.  **Inicie um Novo Chat e Ative o Scrum Master (SM):**
    *   **CRÍTICO:** Sempre inicie um **novo chat** ao trocar de agente. Isso mantém o contexto limpo.
    *   Em um novo chat do Claude, digite: `/sm` e pressione Enter.

4.  **Peça a Primeira Tarefa ao SM:**
    *   O SM irá preparar a primeira estória para o desenvolvimento. Digite o prompt:
        `Com base nos arquivos em 'docs/stories/', qual é a primeira estória que devemos implementar? Por favor, prepare-a para o desenvolvimento.`

5.  **Inicie um Novo Chat e Ative o Desenvolvedor (Dev):**
    *   Em um **terceiro novo chat**, digite: `/dev` e pressione Enter.
    *   Agora, você está pronto para começar a codificar. Dê ao agente Dev a primeira estória que o SM preparou. Use o símbolo `@` para referenciar o arquivo da estória:
        `Vamos começar a implementação da estória @docs/stories/1.1-Coletor-de-Dados.md. Por favor, comece implementando o arquivo 'coletor_dados.py' seguindo os critérios de aceitação.`

A partir daqui, o agente Dev começará a escrever o código, criar arquivos e pedir suas confirmações. Você é o **"Vibe CEO"** — você revisa, aprova e guia a direção, enquanto o agente executa.

Siga estes passos e você terá o Coletor de Dados funcionando em breve. Depois, basta repetir o ciclo para as próximas estórias. Bom desenvolvimento