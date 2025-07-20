import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import json
from datetime import datetime
from saude_api import SaudeApi
from acs_analyzer import ACSAnalyzer, ACSMetrics, ACSDetalhePeriodo

# Configuração da página
st.set_page_config(
    page_title="Dashboard ACS - Agentes Comunitários de Saúde",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado para melhorar o visual
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
    }
    .success-card {
        border-left-color: #51cf66;
    }
    .warning-card {
        border-left-color: #ffd43b;
    }
    .error-card {
        border-left-color: #ff6b6b;
    }
    .big-font {
        font-size: 2rem;
        font-weight: bold;
    }
    .medium-font {
        font-size: 1.2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def fazer_requisicao_saude(codigo_uf: str, codigo_municipio: str, parcela_inicio: str, parcela_fim: str, tipo_relatorio: str = "COMPLETO"):
    """
    Faz requisição para a API do Ministério da Saúde com headers corretos (função original)
    """
    params = {
        "unidadeGeografica": "MUNICIPIO",
        "coUf": codigo_uf,
        "coMunicipio": codigo_municipio,
        "nuParcelaInicio": parcela_inicio,
        "nuParcelaFim": parcela_fim,
        "tipoRelatorio": tipo_relatorio
    }
    
    # Headers necessários baseados na requisição original
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'relatorioaps-prd.saude.gov.br',
        'Origin': 'https://relatorioaps.saude.gov.br',
        'Pragma': 'no-cache',
        'Referer': 'https://relatorioaps.saude.gov.br/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    
    try:
        with st.spinner("🔍 Consultando dados de ACS..."):
            st.info(f"Consultando: UF={codigo_uf}, Município={codigo_municipio}, Competência={parcela_inicio}")
            response = requests.get(
                "https://relatorioaps-prd.saude.gov.br/financiamento/pagamento", 
                params=params, 
                headers=headers, 
                timeout=30
            )
            
            # Debug da resposta
            st.write(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                if dados:
                    # Debug da estrutura dos dados
                    st.info("✅ JSON recebido com sucesso!")
                    
                    # Verifica seção resumosPlanosOrcamentarios
                    if 'resumosPlanosOrcamentarios' in dados:
                        resumos = dados['resumosPlanosOrcamentarios']
                        st.write(f"📊 Resumos orçamentários: {len(resumos)} registros")
                        
                        # Verifica se há dados de ACS em resumos
                        acs_records_resumos = [r for r in resumos if 'qtTetoAcs' in r]
                        if acs_records_resumos:
                            st.success(f"🎯 Encontrados {len(acs_records_resumos)} registros com dados de ACS em resumos!")
                        else:
                            st.warning("⚠️ Nenhum registro em resumos contém dados de ACS")
                    
                    # Verifica seção pagamentos (onde estão os dados de ACS)
                    if 'pagamentos' in dados:
                        pagamentos = dados['pagamentos']
                        st.write(f"💰 Pagamentos: {len(pagamentos)} registros")
                        
                        # Verifica se há dados de ACS em pagamentos
                        acs_records_pagamentos = [r for r in pagamentos if 'qtTetoAcs' in r]
                        if acs_records_pagamentos:
                            st.success(f"🎯 Encontrados {len(acs_records_pagamentos)} registros com dados de ACS em pagamentos!")
                            # Mostra exemplo dos campos encontrados
                            primeiro = acs_records_pagamentos[0]
                            st.write("📋 Campos de ACS encontrados:")
                            acs_fields = [k for k in primeiro.keys() if 'acs' in k.lower() or 'Acs' in k]
                            st.write(f"- {len(acs_fields)} campos: {', '.join(acs_fields[:10])}{'...' if len(acs_fields) > 10 else ''}")
                        else:
                            st.warning("⚠️ Nenhum registro em pagamentos contém dados de ACS")
                    else:
                        st.warning("⚠️ Seção 'pagamentos' não encontrada no JSON")
                    
                    return dados
                else:
                    st.warning("API retornou dados vazios. Verifique se o município possui dados para o período selecionado.")
                    return None
            else:
                st.error(f"Erro HTTP {response.status_code}: {response.text}")
                return None
                
    except requests.RequestException as e:
        st.error(f"❌ Erro na requisição: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Erro ao decodificar JSON: {e}")
        st.write("Resposta recebida:", response.text[:500] + "..." if len(response.text) > 500 else response.text)
        return None

def create_kpi_cards(metrics: ACSMetrics):
    """Cria cards com KPIs principais"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        eficiencia_icon, eficiencia_tipo, eficiencia_desc = ACSAnalyzer.get_efficiency_status(metrics.eficiencia)
        st.markdown(f"""
        <div class="metric-card {eficiencia_tipo}-card">
            <h4>{eficiencia_icon} Eficiência Geral</h4>
            <div class="big-font">{ACSAnalyzer.format_percentage(metrics.eficiencia)}</div>
            <div>{eficiencia_desc} - {metrics.pagos_total}/{metrics.teto_acs} ACS pagos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🎯 Taxa de Ocupação</h4>
            <div class="big-font">{ACSAnalyzer.format_percentage(metrics.taxa_ocupacao)}</div>
            <div>{metrics.credenciados_total}/{metrics.teto_acs} credenciados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h4>💰 Taxa de Pagamento</h4>
            <div class="big-font">{ACSAnalyzer.format_percentage(metrics.taxa_pagamento)}</div>
            <div>{metrics.pagos_total}/{metrics.credenciados_total} pagos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        cor_perda = "success" if metrics.perda_financeira <= 0 else ("warning" if metrics.perda_percentual < 10 else "error")
        st.markdown(f"""
        <div class="metric-card {cor_perda}-card">
            <h4>📉 Perda Financeira</h4>
            <div class="big-font">{ACSAnalyzer.format_currency(abs(metrics.perda_financeira))}</div>
            <div>{ACSAnalyzer.format_percentage(abs(metrics.perda_percentual))} do previsto</div>
        </div>
        """, unsafe_allow_html=True)

def create_summary_chart(metrics: ACSMetrics):
    """Cria gráfico de barras com resumo quantitativo"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Teto',
        x=['ACS'],
        y=[metrics.teto_acs],
        marker_color='lightblue',
        text=[metrics.teto_acs],
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        name='Credenciados',
        x=['ACS'],
        y=[metrics.credenciados_total],
        marker_color='orange',
        text=[metrics.credenciados_total],
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        name='Pagos',
        x=['ACS'],
        y=[metrics.pagos_total],
        marker_color='green',
        text=[metrics.pagos_total],
        textposition='auto'
    ))
    
    fig.update_layout(
        title="📊 Resumo Quantitativo - ACS",
        yaxis_title="Quantidade",
        barmode='group',
        height=400
    )
    
    return fig

def create_timeline_chart(timeline: list):
    """Cria gráfico temporal da evolução dos ACS"""
    
    if not timeline:
        return None
    
    df = pd.DataFrame([{
        'Parcela': t.parcela,
        'Teto': t.teto,
        'Credenciados': t.credenciados_direto + t.credenciados_indireto,
        'Pagos': t.pagos_direto + t.pagos_indireto,
        'Valor Total': t.valor_total
    } for t in timeline])
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Evolução Quantitativa', 'Evolução Financeira'),
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Gráfico quantitativo
    fig.add_trace(
        go.Scatter(x=df['Parcela'], y=df['Teto'], name='Teto', line=dict(color='lightblue', width=3)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Parcela'], y=df['Credenciados'], name='Credenciados', line=dict(color='orange', width=3)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['Parcela'], y=df['Pagos'], name='Pagos', line=dict(color='green', width=3)),
        row=1, col=1
    )
    
    # Gráfico financeiro
    fig.add_trace(
        go.Bar(x=df['Parcela'], y=df['Valor Total'], name='Valor Recebido', marker_color='darkgreen'),
        row=2, col=1
    )
    
    fig.update_layout(height=700, title_text="📈 Evolução Temporal dos ACS")
    fig.update_xaxes(title_text="Parcela", row=2, col=1)
    fig.update_yaxes(title_text="Quantidade", row=1, col=1)
    fig.update_yaxes(title_text="Valor (R$)", row=2, col=1)
    
    return fig

def create_distribution_chart(metrics: ACSMetrics):
    """Cria gráficos de distribuição direto/indireto"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico pizza - Credenciados
        fig_cred = px.pie(
            values=[metrics.credenciados_direto, metrics.credenciados_indireto],
            names=['Direto', 'Indireto'],
            title="📊 Distribuição de Credenciados",
            color_discrete_sequence=['#ff9999', '#66b3ff']
        )
        st.plotly_chart(fig_cred, use_container_width=True)
    
    with col2:
        # Gráfico pizza - Valores
        fig_val = px.pie(
            values=[metrics.valor_recebido_direto, metrics.valor_recebido_indireto],
            names=['Direto', 'Indireto'],
            title="💰 Distribuição de Valores",
            color_discrete_sequence=['#99ff99', '#ffcc99']
        )
        st.plotly_chart(fig_val, use_container_width=True)

def create_detailed_table(timeline: list):
    """Cria tabela detalhada por competência"""
    
    if not timeline:
        return None
    
    data = []
    for t in timeline:
        data.append({
            'Competência': t.competencia,
            'Parcela': t.parcela,
            'Teto': t.teto,
            'Cred. Direto': t.credenciados_direto,
            'Cred. Indireto': t.credenciados_indireto,
            'Total Cred.': t.credenciados_direto + t.credenciados_indireto,
            'Pagos Direto': t.pagos_direto,
            'Pagos Indireto': t.pagos_indireto,
            'Total Pagos': t.pagos_direto + t.pagos_indireto,
            'Valor Direto': ACSAnalyzer.format_currency(t.valor_direto),
            'Valor Indireto': ACSAnalyzer.format_currency(t.valor_indireto),
            'Valor Total': ACSAnalyzer.format_currency(t.valor_total)
        })
    
    df = pd.DataFrame(data)
    return df

def main():
    # Cabeçalho
    st.title("🏥 Dashboard ACS - Agentes Comunitários de Saúde")
    st.markdown("**Sistema de monitoramento e análise de ACS por município**")
    
    st.markdown("---")
    
    # Interface completa (igual ao app.py original)
    st.subheader("🔍 Configurações da Consulta")
    
    # Carregamento das UFs
    ufs = SaudeApi.get_ufs()
    
    if not ufs:
        st.error("Não foi possível carregar a lista de UFs. Verifique sua conexão.")
        return
    
    # Seleção da UF
    uf_options = ["Selecione um estado..."] + [SaudeApi.formatar_uf_para_dropdown(uf) for uf in ufs]
    uf_selecionada = st.selectbox("🗺️ Estado (UF)", uf_options)
    
    municipio_selecionado = None
    codigo_uf = None
    codigo_municipio = None
    
    if uf_selecionada != "Selecione um estado...":
        # Encontra o código da UF selecionada
        codigo_uf = SaudeApi.extrair_codigo_uf(uf_selecionada, ufs)
        
        if codigo_uf:
            # Carregamento dos municípios
            municipios = SaudeApi.get_municipios_por_uf(codigo_uf)
            
            if municipios:
                municipio_options = ["Selecione um município..."] + [SaudeApi.formatar_municipio_para_dropdown(municipio) for municipio in municipios]
                municipio_selecionado = st.selectbox("🏘️ Município", municipio_options)
                
                if municipio_selecionado != "Selecione um município...":
                    codigo_municipio = SaudeApi.extrair_codigo_municipio(municipio_selecionado, municipios)
    
    # Configurações de período
    st.subheader("📅 Período")
    
    # Carrega anos disponíveis
    anos_disponiveis = SaudeApi.get_anos_disponiveis()
    
    if anos_disponiveis:
        # Campos de período - single competência
        col1, col2 = st.columns(2)
        with col1:
            ano_consulta = st.selectbox("Ano da competência", anos_disponiveis, index=0 if anos_disponiveis else 0)
        
        with col2:
            mes_consulta = st.number_input("Mês da competência", min_value=1, max_value=12, value=6)
        
        # Mostra parcelas disponíveis se um ano estiver selecionado
        if ano_consulta:
            parcelas_competencia = SaudeApi.get_parcelas_por_ano(ano_consulta)
            if parcelas_competencia:
                st.info(f"📊 {len(parcelas_competencia)} parcelas disponíveis em {ano_consulta}")
    else:
        # Fallback para campos manuais
        ano_atual = datetime.now().year
        col1, col2 = st.columns(2)
        with col1:
            ano_consulta = st.number_input("Ano da competência", min_value=2020, max_value=ano_atual, value=ano_atual)
        
        with col2:
            mes_consulta = st.number_input("Mês da competência", min_value=1, max_value=12, value=6)
    
    # Formatação das parcelas - usando competência única como solicitado
    parcela_inicio = f"{ano_consulta}{mes_consulta:02d}"
    parcela_fim = parcela_inicio  # Mesma competência para início e fim
    
    # Tipo de relatório
    tipo_relatorio = st.selectbox("📊 Tipo de Relatório", ["COMPLETO", "RESUMIDO"])
    
    # Botão de consulta
    if codigo_uf and codigo_municipio:
        st.success(f"✅ Configurado: {uf_selecionada} → {municipio_selecionado}")
        
        # Informações da requisição
        with st.expander("ℹ️ Detalhes da Requisição"):
            st.write(f"**Estado:** {uf_selecionada} (Código: {codigo_uf})")
            st.write(f"**Município:** {municipio_selecionado} (Código: {codigo_municipio})")
            st.write(f"**Competência:** {parcela_inicio}")
            st.write(f"**Tipo:** {tipo_relatorio}")
        
        # Botão para fazer requisição
        if st.button("🚀 Consultar Dados de ACS", type="primary", use_container_width=True):
            dados = fazer_requisicao_saude(codigo_uf, codigo_municipio, parcela_inicio, parcela_fim, tipo_relatorio)
        
            if dados:
                # Analisa dados de ACS
                metrics = ACSAnalyzer.extract_acs_data(dados)
                timeline = ACSAnalyzer.extract_acs_timeline(dados)
                
                if metrics:
                    st.markdown("---")
                
                    # Cabeçalho do município
                    st.header(f"📊 {metrics.municipio} - {metrics.estado}")
                    st.caption(f"Última atualização: {metrics.data_atualizacao} | Competências: {len(metrics.competencias)}")
                    
                    # Inicializa variável para evitar erro
                    df_detalhado = None
                    
                    # KPIs principais
                    st.subheader("📈 Indicadores Principais")
                    create_kpi_cards(metrics)
                    
                    st.markdown("---")
                    
                    # Gráficos
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📊 Resumo Quantitativo")
                        fig_summary = create_summary_chart(metrics)
                        st.plotly_chart(fig_summary, use_container_width=True)
                    
                    with col2:
                        st.subheader("🔄 Distribuição Direto/Indireto")
                        create_distribution_chart(metrics)
                    
                    # Evolução temporal
                    if timeline and len(timeline) > 1:
                        st.subheader("📈 Evolução Temporal")
                        fig_timeline = create_timeline_chart(timeline)
                        if fig_timeline:
                            st.plotly_chart(fig_timeline, use_container_width=True)
                    
                    # Resumo financeiro
                    st.subheader("💰 Resumo Financeiro")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "💵 Valor Recebido Total",
                            ACSAnalyzer.format_currency(metrics.valor_recebido_total),
                            help="Total recebido em todas as competências"
                        )
                    
                    with col2:
                        st.metric(
                            "🎯 Valor Previsto Total",
                            ACSAnalyzer.format_currency(metrics.valor_previsto_total),
                            help="Valor que deveria ser recebido (estimativa)"
                        )
                    
                    with col3:
                        delta_color = "inverse" if metrics.perda_financeira > 0 else "normal"
                        st.metric(
                            "📉 Diferença",
                            ACSAnalyzer.format_currency(abs(metrics.perda_financeira)),
                            delta=f"{ACSAnalyzer.format_percentage(metrics.perda_percentual)} {'perda' if metrics.perda_financeira > 0 else 'economia'}",
                            delta_color=delta_color
                        )
                    
                    # Tabela detalhada
                    if timeline:
                        st.subheader("📋 Detalhamento por Competência")
                        df_detalhado = create_detailed_table(timeline)
                        if df_detalhado is not None:
                            st.dataframe(df_detalhado, use_container_width=True)
                    
                    # Download dos dados
                    st.subheader("⬇️ Exportar Dados")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # JSON dos dados brutos
                        json_string = json.dumps(dados, indent=2, ensure_ascii=False)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename_json = f"dados_acs_{municipio_selecionado.replace(' ', '_')}_{timestamp}.json"
                        
                        st.download_button(
                            label="📥 Baixar JSON Completo",
                            data=json_string,
                            file_name=filename_json,
                            mime="application/json"
                        )
                    
                    with col2:
                        # CSV da tabela detalhada
                        if df_detalhado is not None:
                            csv_string = df_detalhado.to_csv(index=False, encoding='utf-8-sig')
                            filename_csv = f"resumo_acs_{municipio_selecionado.replace(' ', '_')}_{timestamp}.csv"
                            
                            st.download_button(
                                label="📊 Baixar Resumo CSV",
                                data=csv_string,
                                file_name=filename_csv,
                                mime="text/csv"
                            )
                    
                else:
                    st.warning("⚠️ Nenhum dado de ACS encontrado para este município no período consultado.")
                    st.info("💡 **Dica**: Nem todos os municípios possuem dados de ACS disponíveis.")
            
            else:
                st.error("❌ Erro ao consultar dados. Verifique a conexão e tente novamente.")
    
    else:
        # Informações sobre o sistema
        st.markdown("---")
        st.info("👈 **Selecione um estado e município para consultar os dados de ACS**")
        
        # Botão de exemplo
        if st.button("📋 Usar Exemplo: Abaré/PE (com dados ACS)", type="secondary", use_container_width=True):
            st.info("📍 **Exemplo configurado**: PE - Pernambuco → Abaré")
            st.write("🔧 **Configuração manual necessária**:")
            st.write("1. Selecione **PE - Pernambuco** na lista de estados")
            st.write("2. Escolha **ABARÉ** na lista de municípios")
            st.write("3. Configure competência 2025/06")
            st.write("4. Clique **'Consultar Dados de ACS'**")
            st.success("✅ Este município **tem dados de ACS confirmados**!")
        
        with st.expander("ℹ️ Sobre o Dashboard ACS"):
            st.markdown("""
            Este dashboard permite consultar e analisar dados dos **Agentes Comunitários de Saúde (ACS)** 
            através da API oficial do Ministério da Saúde.
            
            **📊 Métricas Disponíveis:**
            - 🎯 **Quantidade teto**: Número máximo de ACS aprovado para o município
            - ✅ **ACS credenciados**: Quantidade de ACS habilitados (direto + indireto)
            - 💰 **ACS pagos**: Quantidade de ACS que receberam pagamento
            - 💵 **Valores financeiros**: Montantes transferidos e previstos
            - 📈 **Indicadores**: Taxa de ocupação, pagamento e eficiência
            
            **🔄 Tipos de ACS:**
            - **Direto**: ACS vinculado diretamente ao município
            - **Indireto**: ACS vinculado através de organizações parceiras
            
            **📅 Período de Consulta:**
            - Dados de Janeiro a Julho de 2025
            - Múltiplas competências para análise temporal
            
            **⚠️ Importante:**
            - Nem todos os municípios possuem dados de ACS
            - Use o exemplo **Abaré/PE** para testar (dados confirmados)
            
            **🚀 Como usar:**
            1. Selecione o estado (UF)
            2. Escolha o município  
            3. Configure o período
            4. Clique em "Consultar Dados de ACS"
            5. Analise os dados no dashboard
            6. Faça download dos relatórios se necessário
            """)

if __name__ == "__main__":
    main()