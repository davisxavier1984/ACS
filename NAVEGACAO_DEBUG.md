# Documentação de Problemas de Navegação - ACS Dashboard

## Resumo do Problema e Resolução

### Data: 2025-07-20
### Contexto: Implementação de drill-down entre Visão Estadual e Visão Municipal

---

## Problema Identificado

### Situação Inicial
- **Arquivo de origem:** `pages/2_Visao_estadual.py`
- **Arquivo de destino:** `pages/1_Visao_municipal.py`
- **Funcionalidade:** Botão "Ver" na coluna Ação da tabela municipal
- **URL funcionando:** `/Visao_municipal?uf=...&municipio_ibge=...&competencia=...`

### Erro Cometido
Quando solicitado para atualizar links com primeira letra maiúscula, o desenvolvedor:

1. ✅ **Corretamente atualizou:** `/visao_municipal` → `/Visao_municipal`
2. ❌ **Incorretamente assumiu:** Que o "page not found" era devido ao case sensitivity
3. ❌ **Reverteu desnecessariamente:** `/Visao_municipal` → `/visao_municipal`

### Resultado do Erro
- Link "Ver" parou de funcionar (page not found)
- Navegação drill-down quebrada
- Usuário reportou que funcionava ANTES da alteração desnecessária

---

## Solução Aplicada

### Correção Final
```python
# Arquivo: pages/2_Visao_estadual.py, linha 160
# CORRETO (funcionando):
lambda row: f"/Visao_municipal?uf={row['codigo_uf']}&municipio_ibge={row['codigo_municipio']}&competencia={competencia_selecionada}",
```

### Estado Final dos Arquivos
- ✅ `pages/1_Visao_municipal.py` (maiúsculo)
- ✅ `pages/2_Visao_estadual.py` (maiúsculo)  
- ✅ URL de navegação: `/Visao_municipal` (maiúsculo)

---

## Lições Aprendidas

### ❌ Erros Cometidos
1. **Assumir sem testar:** Mudou URL funcionando baseado em suposição
2. **Ignorar feedback do usuário:** "Funcionava antes" deveria ter sido indicativo
3. **Sobre-engenharia:** Tentou "corrigir" algo que não estava quebrado

### ✅ Práticas Corretas
1. **Se algo funciona, não mude:** "If it ain't broke, don't fix it"
2. **Testar antes de implementar:** Sempre verificar se mudança é necessária
3. **Escutar o usuário:** Feedback sobre funcionalidade anterior é crucial
4. **Documentar problemas:** Para evitar repetição de erros

---

## Mapeamento de URLs do Streamlit

### Descobertas sobre URL Mapping
- **Arquivo:** `1_Visao_municipal.py`
- **URL gerada:** `/Visao_municipal` (preserva case do nome do arquivo)
- **Padrão:** Streamlit remove prefixo numérico, mantém case do identificador
- **Sensibilidade:** URLs são case-sensitive no Streamlit

### Regras Identificadas
1. `1_Visao_municipal.py` → `/Visao_municipal`
2. `2_Visao_estadual.py` → `/Visao_estadual`
3. Underscores são tratados como espaços na navegação sidebar
4. URLs preservam case exato do nome do arquivo

---

## Checklist para Futuras Mudanças de Navegação

### Antes de Alterar URLs
- [ ] Confirmar que URL atual NÃO está funcionando
- [ ] Testar em ambiente de desenvolvimento
- [ ] Verificar documentação oficial do Streamlit
- [ ] Fazer backup da versão funcionando

### Durante a Alteração
- [ ] Fazer apenas UMA mudança por vez
- [ ] Testar imediatamente após mudança
- [ ] Documentar o que foi alterado e por quê

### Após a Alteração
- [ ] Verificar que navegação funciona completamente
- [ ] Testar todos os cenários de drill-down
- [ ] Confirmar que parâmetros são passados corretamente
- [ ] Obter confirmação do usuário

---

## Código de Referência

### Estrutura da URL Drill-down
```python
# Template correto para drill-down
def gerar_url_municipal(codigo_uf, codigo_municipio, competencia):
    return f"/Visao_municipal?uf={codigo_uf}&municipio_ibge={codigo_municipio}&competencia={competencia}"

# Implementação na tabela
df_merged['municipio_url'] = df_merged.apply(
    lambda row: f"/Visao_municipal?uf={row['codigo_uf']}&municipio_ibge={row['codigo_municipio']}&competencia={competencia_selecionada}",
    axis=1
)
```

### Configuração da LinkColumn
```python
column_config={
    "Ação": st.column_config.LinkColumn(
        "Ação",
        help="Clique para ver a análise detalhada deste município",
        display_text="Ver"
    )
}
```

---

## Contato e Suporte

**Desenvolvedor:** James (Dev Agent)  
**Data da Documentação:** 2025-07-20  
**Última Atualização:** 2025-07-20  

---

*Esta documentação serve como referência para evitar problemas similares em futuras implementações de navegação no sistema ACS.*