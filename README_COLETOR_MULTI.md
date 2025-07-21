# 🚀 Coletor Multi-Estados ACS

Sistema de coleta de dados de múltiplos estados simultaneamente para análise de Agentes Comunitários de Saúde.

## 📋 Características

- ✅ **Multi-Estado**: Coleta dados de vários estados em uma operação
- ✅ **Modos de Processamento**: Sequencial (estável) ou Paralelo (rápido)
- ✅ **Progress Tracking**: Acompanhamento em tempo real
- ✅ **Arquivos Consolidados**: Saída única + arquivos individuais opcionais
- ✅ **Tratamento de Erros**: Resiliente a falhas individuais por estado
- ✅ **Compatibilidade**: 100% compatível com sistema de análise existente

## 🔧 Instalação

O coletor usa as mesmas dependências do projeto principal:

```bash
pip install streamlit requests pandas plotly
```

## 📖 Uso Básico

### Sintaxe Geral
```bash
python coletor_multi_estados.py --ufs "<LISTA_UFS>" --competencias "<LISTA_COMPETENCIAS>" [OPÇÕES]
```

### Exemplos Práticos

**1. Coletar dados de alguns estados específicos:**
```bash
python coletor_multi_estados.py --ufs "PE,SP,BA" --competencias "2025/06,2025/07"
```

**2. Coletar dados de todos os estados:**
```bash
python coletor_multi_estados.py --ufs "ALL" --competencias "2025/06"
```

**3. Processamento paralelo (mais rápido):**
```bash
python coletor_multi_estados.py --ufs "PE,SP,BA" --competencias "2025/06" --modo paralelo --max-workers 3
```

**4. Apenas arquivo consolidado (sem arquivos individuais):**
```bash
python coletor_multi_estados.py --ufs "AC,RR,AP" --competencias "2025/06" --output-consolidado
```

## 📊 Parâmetros

### Obrigatórios
- `--ufs` / `-u`: Lista de UFs separadas por vírgula ou "ALL"
- `--competencias` / `-c`: Lista de competências no formato "AAAA/MM"

### Opcionais
- `--modo` / `-m`: "sequencial" (padrão) ou "paralelo"
- `--max-workers` / `-w`: Número de workers paralelos (padrão: 3)
- `--output-consolidado` / `-o`: Gera apenas arquivo consolidado

## 📁 Estrutura de Saída

### Arquivo Consolidado
```
data/dados_multi_estados_YYYYMMDDHHMMSS.json
```

### Arquivos Individuais (compatibilidade)
```
data/dados_UF_YYYYMMDDHHMMSS.json
```

## 🎯 Estados Suportados

| Código | Estado | Código | Estado |
|--------|---------|--------|---------|
| AC | Acre | MT | Mato Grosso |
| AL | Alagoas | MS | Mato Grosso do Sul |
| AP | Amapá | MG | Minas Gerais |
| AM | Amazonas | PA | Pará |
| BA | Bahia | PB | Paraíba |
| CE | Ceará | PR | Paraná |
| DF | Distrito Federal | PE | Pernambuco |
| ES | Espírito Santo | PI | Piauí |
| GO | Goiás | RJ | Rio de Janeiro |
| MA | Maranhão | RN | Rio Grande do Norte |
| **ALL** | **Todos os Estados** | **--** | **--** |

## ⚡ Modos de Processamento

### Modo Sequencial (Padrão)
- **Vantagens**: Mais estável, menor carga na API
- **Desvantagens**: Mais lento
- **Recomendado**: Primeiro uso, muitos estados, ambientes com limitações

### Modo Paralelo
- **Vantagens**: Mais rápido, aproveita múltiplos cores
- **Desvantagens**: Maior carga na API, pode ser instável
- **Recomendado**: Poucos estados, ambiente estável, pressa

## 📈 Performance

### Tempos Estimados (modo sequencial)

| Estados | Competências | Tempo Estimado |
|---------|--------------|----------------|
| 3 pequenos (AC,RR,AP) | 1 competência | 2-5 min |
| 5 médios (PE,AL,SE,PB,RN) | 1 competência | 10-20 min |
| 3 grandes (SP,MG,BA) | 1 competência | 30-60 min |
| ALL (27 estados) | 1 competência | 2-4 horas |

**Modo paralelo:** ~50-70% mais rápido dependendo do hardware.

## 🛠️ Resolução de Problemas

### Estados com Muitos Municípios
Para estados grandes (SP, MG, BA), considere:
- Usar modo sequencial para maior estabilidade
- Reduzir número de competências por execução
- Executar em horários de menor carga da API

### Falhas de Conexão
- O sistema automaticamente tenta novamente (3 tentativas por município)
- Estados que falharam não impedem o processamento dos outros
- Logs detalhados em `logs/coletor_multi_estados.log`

### Memória Insuficiente
- Use `--output-consolidado` para economizar memória
- Processe menos estados por vez
- Considere incrementar a memória virtual

## 📋 Logs e Monitoramento

### Arquivo de Log
```
logs/coletor_multi_estados.log
```

### Informações Registradas
- Progresso por UF e município
- Erros e tentativas de retry
- Estatísticas de sucesso/falha
- Tempos de execução

## 🔄 Integração com Sistema Existente

### Compatibilidade Total
- Arquivos gerados são 100% compatíveis com sistema de análise
- Páginas Streamlit reconhecem automaticamente os novos dados
- Estrutura JSON idêntica ao coletor original

### Uso com Dashboards
1. Execute o coletor multi-estados
2. Os novos dados ficam disponíveis automaticamente
3. Use qualquer página de análise (Municipal, Estadual, Multi-Competência)

## 💡 Dicas de Uso

### Para Análise Nacional
```bash
# Coletar todos os estados para uma competência específica
python coletor_multi_estados.py --ufs "ALL" --competencias "2025/06"
```

### Para Análise Regional
```bash
# Nordeste
python coletor_multi_estados.py --ufs "MA,PI,CE,RN,PB,PE,AL,SE,BA" --competencias "2025/06"

# Sudeste
python coletor_multi_estados.py --ufs "MG,ES,RJ,SP" --competencias "2025/06"

# Sul
python coletor_multi_estados.py --ufs "PR,SC,RS" --competencias "2025/06"
```

### Para Testes
```bash
# Estados pequenos para teste rápido
python coletor_multi_estados.py --ufs "AC,RR,AP" --competencias "2025/06"
```

## 🚨 Limitações

- **API Rate Limiting**: Pausa automática entre requisições (0.5s)
- **Timeout**: 30s por requisição individual
- **Retry Policy**: 3 tentativas por município
- **Memória**: Proporcional ao número de municípios × competências

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs em `logs/coletor_multi_estados.log`
2. Teste com estados pequenos primeiro
3. Use modo sequencial se houver instabilidade
4. Consulte a documentação do projeto principal