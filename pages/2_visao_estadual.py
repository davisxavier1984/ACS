import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from acs_analyzer import ACSAnalyzer

st.set_page_config(
    page_title="Visão Estadual Comparativa",
    page_icon="🏛️",
    layout="wide"
)

def color_negative_red_positive_green(val):
    """
    Colors negative values red, positive values green, and zero white.
    """
    if isinstance(val, (int, float)):
        if val < 0:
            return 'color: #D32F2F; font-weight: bold;'  # Vermelho mais escuro
        elif val > 0:
            return 'color: #388E3C; font-weight: bold;'  # Verde mais escuro
    return ''

@st.cache_data
def carregar_e_processar_dados():
    data_dir = Path("data")
    json_files = list(data_dir.glob("dados_*.json"))
    
    if not json_files:
        return None, {}, []

    df_completo = pd.DataFrame()
    metadados_gerais = {'ufs': set(), 'competencias': set()}

    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            dados_brutos = json.load(f)
        
        metadados_gerais['ufs'].add(dados_brutos['metadados']['uf'])
        for comp in dados_brutos['metadados']['competencias']:
            metadados_gerais['competencias'].add(comp)
        
        resultados = dados_brutos.get('resultados', [])
        if resultados:
            dados_processados = ACSAnalyzer.processar_dados_coletados(resultados)
            df_temp = pd.DataFrame(dados_processados)
            df_completo = pd.concat([df_completo, df_temp], ignore_index=True)
    
    # Adiciona colunas calculadas
    df_completo['qtTotalCredenciado'] = df_completo['qtAcsDiretoCredenciado'] + df_completo['qtAcsIndiretoCredenciado']
    df_completo['qtTotalPago'] = df_completo['qtAcsDiretoPgto'] + df_completo['qtAcsIndiretoPgto']
    df_completo['vlTotalAcs'] = df_completo['vlTotalAcsDireto'] + df_completo['vlTotalAcsIndireto']
    
    return df_completo, metadados_gerais, sorted(list(metadados_gerais['competencias']), reverse=True)

# --- Interface Principal ---
st.title("🏛️ Visão Estadual Comparativa")

df_principal, metadados, competencias_disponiveis = carregar_e_processar_dados()

if df_principal is None or df_principal.empty:
    st.error("❌ Não foi possível carregar os dados. Verifique se existe um arquivo JSON na pasta 'data/'.")
    st.info("💡 Execute primeiro o coletor de dados para gerar o arquivo necessário.")
else:
    st.sidebar.header("Filtros")
    
    # Seletor de UF
    ufs_disponiveis = ["Todos os Estados"] + sorted(list(metadados['ufs']))
    uf_selecionada = st.sidebar.selectbox("Estado (UF):", ufs_disponiveis)
    
    competencia_selecionada = st.sidebar.selectbox("Competência:", competencias_disponiveis)
    
    # Lógica de comparação
    idx_atual = competencias_disponiveis.index(competencia_selecionada)
    competencia_anterior = competencias_disponiveis[idx_atual + 1] if idx_atual + 1 < len(competencias_disponiveis) else None
    
    # Filtrar por competência
    df_atual = df_principal[df_principal['competencia'] == competencia_selecionada].copy()
    
    # Filtrar por UF se não for "Todos os Estados"
    if uf_selecionada != "Todos os Estados":
        df_atual = df_atual[df_atual['uf'] == uf_selecionada].copy()
    
    if competencia_anterior:
        df_anterior = df_principal[df_principal['competencia'] == competencia_anterior].copy()
        
        # Filtrar df_anterior pela mesma UF se não for "Todos os Estados"
        if uf_selecionada != "Todos os Estados":
            df_anterior = df_anterior[df_anterior['uf'] == uf_selecionada].copy()
        
        df_merged = df_atual.merge(df_anterior[['municipio', 'vlTotalAcs', 'qtTotalPago']], on='municipio', suffixes=('', '_ant'), how='left')
        df_merged['var_valor_recebido'] = (df_merged['vlTotalAcs'] - df_merged['vlTotalAcs_ant']).fillna(0)
        df_merged['var_acs_pagos'] = (df_merged['qtTotalPago'] - df_merged['qtTotalPago_ant']).fillna(0)
    else:
        df_merged = df_atual
        df_merged['var_valor_recebido'] = 0
        df_merged['var_acs_pagos'] = 0

    # === EXIBIÇÃO DOS RESULTADOS ===
    
    st.header(f"📊 KPIs Estaduais Agregados - {competencia_selecionada}")
    if competencia_anterior:
        st.info(f"📅 **Comparação:** {competencia_selecionada} vs {competencia_anterior}")
    else:
        st.warning("⚠️ Apenas uma competência disponível. Variações mostrarão 0.")
    
    # KPIs em 5 colunas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_municipios = len(df_merged)
        st.metric("Total de Municípios", total_municipios)
    
    with col2:
        total_valor = df_merged['vlTotalAcs'].sum()
        var_valor_total = df_merged['var_valor_recebido'].sum()
        st.metric(
            "Valor Total (R$)",
            value=f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta=f"{var_valor_total:+,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            help="Total de repasses federais recebidos para ACS no estado."
        )
    
    with col3:
        total_acs_pagos = df_merged['qtTotalPago'].sum()
        var_acs_total = df_merged['var_acs_pagos'].sum()
        st.metric(
            "ACS Pagos",
            value=int(total_acs_pagos),
            delta=int(var_acs_total),
            help="Total de Agentes Comunitários de Saúde que receberam pagamento."
        )
    
    with col4:
        total_credenciados = df_merged['qtTotalCredenciado'].sum()
        st.metric(
            "ACS Credenciados",
            value=int(total_credenciados),
            help="Total de Agentes Comunitários de Saúde credenciados no estado."
        )
    
    with col5:
        saldo_total = df_merged['var_valor_recebido'].sum()
        st.metric(
            "Saldo Total (R$)",
            value=f"R$ {saldo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    
    st.divider()
    
    # === TABELA COMPARATIVA DETALHADA ===
    
    st.header("📋 Dados Municipais Detalhados")
    
    # Crie a tabela final COM AS COLUNAS JÁ ARREDONDADAS E COM TIPOS CORRETOS
    tabela_final = pd.DataFrame({
        'Município': df_merged['municipio'],
        'Valor Recebido (R$)': df_merged['vlTotalAcs'].round(2),
        'Variação vs. Mês Ant. (R$)': df_merged['var_valor_recebido'].round(2),
        'ACS Pagos': df_merged['qtTotalPago'].astype(int),
        'Variação vs. Mês Ant. (Qtd.)': df_merged['var_acs_pagos'].astype(int),
        'Perda/Ganho (R$)': df_merged['var_valor_recebido'].round(2)
    })
    
    # Aplique a formatação e as cores usando o método .style do Pandas DataFrame
    styled_table = tabela_final.style.applymap(
        color_negative_red_positive_green,
        subset=[
            'Variação vs. Mês Ant. (R$)', 
            'Variação vs. Mês Ant. (Qtd.)', 
            'Perda/Ganho (R$)'
        ]
    ).format({
        'Valor Recebido (R$)': 'R$ {:,.2f}',
        'Variação vs. Mês Ant. (R$)': 'R$ {:+,.2f}',
        'ACS Pagos': '{:,d}',
        'Variação vs. Mês Ant. (Qtd.)': '{:+,d}',
        'Perda/Ganho (R$)': 'R$ {:+,.2f}'
    })
    
    # Exibir tabela estilizada
    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Município": st.column_config.LinkColumn(
                "Município",
                help="Clique para ver a análise detalhada deste município."
            )
        }
    )