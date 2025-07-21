import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Sistema ACS - Agentes Comunitários de Saúde",
    page_icon="🏥",
    layout="wide"
)

# Logo e cabeçalho
col_logo, col_title = st.columns([1, 4])

with col_logo:
    st.image("logo.png", width=120)

with col_title:
    st.title("🏥 Sistema ACS - Agentes Comunitários de Saúde")
    st.markdown("**Sistema completo de análise de dados do Ministério da Saúde**")

st.markdown("---")

# Cards informativos sobre cada página
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🏘️ Visão Municipal
    **Análise detalhada por município**
    - Histórico de 3 meses
    - KPIs com variações
    - Gráficos comparativos
    - Dados financeiros e de pessoal
    
    👈 **Use a barra lateral** para navegar
    """)

with col2:
    st.markdown("""
    ### 🏛️ Visão Estadual
    **Comparação entre municípios**
    - Ranking estadual
    - Variações mensais
    - Drill-down para municípios
    - Dados agregados por UF
    
    👈 **Use a barra lateral** para navegar
    """)

with col3:
    st.markdown("""
    ### 📊 Análise Multi-Competência
    **Relatório temporal completo**
    - Múltiplas competências
    - Evolução temporal
    - Tendências e projeções
    - Análise de eficiência
    
    👈 **Use a barra lateral** para navegar
    """)

st.markdown("---")

# Recursos do sistema
st.header("📊 Recursos do Sistema")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    **Funcionalidades Principais:**
    - 🏘️ **Análise Municipal Detalhada**
    - 🏛️ **Comparação Estadual** 
    - 📈 **Evolução Temporal**
    - 💰 **Métricas Financeiras**
    - 📊 **Visualizações Interativas**
    - 📋 **Relatórios Exportáveis**
    """)

with col2:
    st.markdown("""
    **Características:**
    - ✅ **Dados Oficiais** do Ministério da Saúde
    - ✅ **Tempo Real** via API oficial
    - ✅ **Histórico Completo** desde 2020
    - ✅ **Interface Intuitiva** e responsiva
    - ✅ **Análises Detalhadas** por município
    - ✅ **Comparações** entre regiões
    """)

st.markdown("---")

# Informações sobre os dados
with st.expander("ℹ️ Sobre os Dados ACS"):
    st.markdown("""
    **📊 As 5 Métricas Principais de ACS:**
    1. **✅ ACS Credenciados** - Total de ACS habilitados (direto + indireto)
    2. **💰 ACS Pagos** - Total de ACS que receberam pagamento
    3. **🎯 Repasse Federal Esperado** - Valor estimado baseado nos credenciados
    4. **💵 Repasse Federal Recebido** - Valor efetivamente transferido
    5. **📉 Perda de Repasse Federal** - Diferença entre esperado e recebido
    
    **🗓️ Períodos Disponíveis:**
    - 2020 a 2025 (Jan-Jul para 2025)
    - Dados mensais por competência (AAAA/MM)
    
    **🏛️ Fonte dos Dados:**
    - API oficial do Ministério da Saúde
    - Base: https://relatorioaps-prd.saude.gov.br
    - Atualização: Dados oficiais em tempo real
    
    **📍 Exemplo para Teste:**
    - **Município**: Abaré/PE (Pernambuco)
    - **Competência**: 2025/06
    - Este município possui dados ACS disponíveis para exploração
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    💡 <strong>Dica:</strong> Use a barra lateral para navegar entre as análises<br>
    📊 <strong>Sistema:</strong> Análise completa de dados ACS do Ministério da Saúde
</div>
""", unsafe_allow_html=True)

# Copyright na barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.8em; margin-top: 2rem;'>"
    "© Mais Gestor (2025)<br>"
    "Todos os direitos reservados"
    "</div>", 
    unsafe_allow_html=True
)