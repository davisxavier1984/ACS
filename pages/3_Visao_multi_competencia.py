import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
from datetime import datetime
from saude_api import SaudeApi
from acs_analyzer import ACSAnalyzer, ACSMetrics
from competencias_manager import CompetenciasManager

# Configuração da página
st.set_page_config(
    page_title="Análise Multi-Competência",
    page_icon="📊",
    layout="wide"
)

# CSS customizado para cards mais claros
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card.green {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
    }
    .metric-card.yellow {
        background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
    }
    .metric-card.red {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
    }
    .metric-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        opacity: 0.9;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .metric-subtitle {
        font-size: 0.9rem;
        opacity: 0.8;
    }
    .progress-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def create_metric_card(title: str, value: str, subtitle: str, color_class: str = ""):
    """Cria um card de métrica mais visual"""
    return f"""
    <div class="metric-card {color_class}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtitle">{subtitle}</div>
    </div>
    """

def format_currency(value: float) -> str:
    """Formata valor monetário com abreviações Mil e Mi"""
    if value >= 1_000_000:
        return f"R$ {value/1_000_000:.1f}Mi"
    elif value >= 1_000:
        return f"R$ {value/1_000:.0f}Mil"
    else:
        return f"R$ {value:,.0f}".replace(',', '.')

def format_number(value: int) -> str:
    """Formata número inteiro com abreviações Mil e Mi"""
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}Mi"
    elif value >= 1_000:
        return f"{value/1_000:.0f}Mil"
    else:
        return f"{value:,}".replace(',', '.')

def create_main_metrics_cards(metrics: ACSMetrics):
    """Cria os 5 cards principais das métricas de ACS"""
    
    st.subheader("📊 As 5 Métricas Principais de ACS")
    
    # Primeira linha - ACS Credenciados e Pagos
    col1, col2 = st.columns(2)
    
    with col1:
        color = "green" if metrics.quantidade_credenciado > 0 else "red"
        card_html = create_metric_card(
            "✅ ACS Credenciados", 
            format_number(metrics.quantidade_credenciado),
            "Total de ACS habilitados (direto + indireto)",
            color
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    with col2:
        eficiencia = (metrics.quantidade_pago / metrics.quantidade_credenciado * 100) if metrics.quantidade_credenciado > 0 else 0
        color = "green" if eficiencia >= 95 else "yellow" if eficiencia >= 85 else "red"
        card_html = create_metric_card(
            "💰 ACS Pagos",
            format_number(metrics.quantidade_pago),
            f"{eficiencia:.1f}% dos credenciados receberam pagamento",
            color
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    # Segunda linha - Valores Financeiros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        color = "green" if metrics.total_deveria_receber > 0 else "red"
        card_html = create_metric_card(
            "🎯 Repasse Federal Esperado",
            format_currency(metrics.total_deveria_receber),
            "Valor estimado baseado nos ACS credenciados",
            color
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    with col2:
        # Verde se recebeu próximo ao esperado, vermelho se recebeu muito menos
        eficiencia_repasse = (metrics.total_recebido / metrics.total_deveria_receber * 100) if metrics.total_deveria_receber > 0 else 0
        color = "green" if eficiencia_repasse >= 95 else "yellow" if eficiencia_repasse >= 85 else "red"
        
        card_html = create_metric_card(
            "💵 Repasse Federal Recebido",
            format_currency(metrics.total_recebido),
            f"Efetividade: {eficiencia_repasse:.1f}% do esperado",
            color
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    with col3:
        # Para repasses federais, valores menores sempre são perdas para o município
        perda_absoluta = max(0, metrics.total_perda)  # Perda nunca é negativa
        perda_perc = abs(metrics.percentual_perda)
        
        # Cores baseadas no nível de perda (verde = pouca perda, vermelho = muita perda)
        color = "green" if perda_perc <= 5 else "yellow" if perda_perc <= 15 else "red"
        
        card_html = create_metric_card(
            "📉 Perda de Repasse Federal",
            format_currency(perda_absoluta),
            f"{perda_perc:.1f}% de perda dos recursos federais",
            color
        )
        st.markdown(card_html, unsafe_allow_html=True)

def create_summary_chart(metrics: ACSMetrics):
    """Gráfico de barras comparando ACS Credenciados vs Pagos"""
    
    # Calcular eficiência de pagamento
    eficiencia = (metrics.quantidade_pago / metrics.quantidade_credenciado * 100) if metrics.quantidade_credenciado > 0 else 0
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='ACS Credenciados',
        x=['ACS Credenciados'],
        y=[metrics.quantidade_credenciado],
        marker_color='#2E86AB',
        text=[format_number(metrics.quantidade_credenciado)],
        textposition='auto',
        width=0.6
    ))
    
    fig.add_trace(go.Bar(
        name='ACS Pagos',
        x=['ACS Pagos'],
        y=[metrics.quantidade_pago],
        marker_color='#4CAF50',
        text=[f"{format_number(metrics.quantidade_pago)}<br>({eficiencia:.1f}%)"],
        textposition='auto',
        width=0.6
    ))
    
    fig.update_layout(
        title="📊 ACS Credenciados vs Pagos",
        yaxis_title="Quantidade de ACS",
        xaxis_title="Categoria",
        height=400,
        showlegend=False,
        xaxis=dict(categoryorder='array', categoryarray=['ACS Credenciados', 'ACS Pagos'])
    )
    
    return fig

def create_financial_chart(metrics: ACSMetrics):
    """Gráfico de barras dos valores financeiros"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Valores'],
        y=[metrics.total_deveria_receber],
        name='Deveria Receber',
        marker_color='#4CAF50',
        text=[format_currency(metrics.total_deveria_receber)],
        textposition='auto',
        width=0.6
    ))
    
    fig.add_trace(go.Bar(
        x=['Valores'],
        y=[metrics.total_recebido],
        name='Total Recebido',
        marker_color='#2196F3',
        text=[format_currency(metrics.total_recebido)],
        textposition='auto',
        width=0.4
    ))
    
    # Sempre mostra a perda (diferença entre esperado e recebido)
    perda_absoluta = max(0, metrics.total_perda)
    if perda_absoluta > 0:
        fig.add_trace(go.Bar(
            x=['Valores'],
            y=[perda_absoluta],
            name='Perda de Repasse',
            marker_color='#F44336',
            text=[format_currency(perda_absoluta)],
            textposition='auto',
            width=0.2
        ))
    
    fig.update_layout(
        title="💰 Repasses Federais - Esperado vs Recebido",
        yaxis_title="Valor (R$)",
        barmode='overlay',
        height=400,
        showlegend=True
    )
    
    return fig

def consultar_multiplas_competencias(codigo_uf: str, codigo_municipio: str, ano: int = None):
    """Consulta múltiplas competências e retorna dados consolidados"""
    from datetime import datetime

    if ano is None:
        ano = datetime.now().year

    manager = CompetenciasManager()
    competencias = manager.get_competencias_disponiveis(ano)

    st.info(f"🔍 Consultando {len(competencias)} competências de {ano} para obter relatório completo...")
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(progress, message):
        progress_bar.progress(progress)
        status_text.text(message)
    
    # Consulta múltiplas competências
    resultados = manager.consultar_multiplas_competencias(
        codigo_uf, codigo_municipio, competencias, update_progress
    )
    
    # Consolida dados
    dados_consolidados = manager.consolidar_dados_acs(resultados)
    metricas_temporais = manager.extrair_metricas_por_competencia(dados_consolidados)
    
    # Remove progress bar
    progress_bar.empty()
    status_text.empty()
    
    return dados_consolidados, metricas_temporais, resultados

def create_temporal_chart(metricas_temporais: list):
    """Gráfico temporal das 5 métricas de ACS"""
    
    if not metricas_temporais:
        return None
    
    df = pd.DataFrame(metricas_temporais)
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('ACS Credenciados vs Pagos', 'Eficiência de Pagamento (%)', 'Valores Financeiros (R$)', 'Taxa de Perda (%)'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Gráfico 1: ACS Credenciados vs Pagos (sem teto)
    fig.add_trace(go.Scatter(x=df['competencia_formatada'], y=df['quantidade_credenciado'], 
                            name='Credenciados', line=dict(color='#2E86AB', width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['competencia_formatada'], y=df['quantidade_pago'], 
                            name='Pagos', line=dict(color='#4CAF50', width=3)), row=1, col=1)
    
    # Gráfico 2: Eficiência de Pagamento
    fig.add_trace(go.Scatter(x=df['competencia_formatada'], y=df['eficiencia'], 
                            name='Eficiência Pagamento', line=dict(color='#FF9800', width=3)), row=1, col=2)
    
    # Gráfico 3: Valores (repasses federais)
    repasse_esperado = df.get('repasse_esperado', df.get('total_deveria_receber', []))
    repasse_recebido = df.get('repasse_recebido', df.get('total_recebido', []))
    
    fig.add_trace(go.Scatter(x=df['competencia_formatada'], y=repasse_esperado, 
                            name='Repasse Esperado', line=dict(color='#2196F3', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['competencia_formatada'], y=repasse_recebido, 
                            name='Repasse Recebido', line=dict(color='#9C27B0', width=3)), row=2, col=1)
    
    # Gráfico 4: Perda de repasse
    perda_percentual = df.get('percentual_perda_repasse', df.get('percentual_perda', []))
    fig.add_trace(go.Scatter(x=df['competencia_formatada'], y=perda_percentual, 
                            name='% Perda Repasse', line=dict(color='#F44336', width=3)), row=2, col=2)
    
    fig.update_layout(height=800, title_text="📈 Evolução Temporal das 5 Métricas Principais de ACS")
    
    return fig

def main():
    # Logo e cabeçalho
    col_logo, col_title = st.columns([1, 4])

    with col_logo:
        st.image("logo.png", width=120)

    with col_title:
        st.title("📊 Análise Multi-Competência ACS")
        st.markdown("**Análise temporal completa dos Agentes Comunitários de Saúde**")
    
    st.markdown("---")
    
    # Interface de seleção
    st.subheader("🔍 Configuração da Consulta")
    
    # Carregamento das UFs
    ufs = SaudeApi.get_ufs()
    
    if not ufs:
        st.error("Não foi possível carregar a lista de UFs. Verifique sua conexão.")
        return
    
    # Seleção da UF e Ano
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        uf_options = ["Selecione um estado..."] + [SaudeApi.formatar_uf_para_dropdown(uf) for uf in ufs]
        uf_selecionada = st.selectbox("🗺️ Estado (UF)", uf_options)

    # Seleção do ano (dinâmico)
    anos_disponiveis = SaudeApi.get_anos_disponiveis()
    with col3:
        ano_selecionado = st.selectbox("📅 Ano", anos_disponiveis)
    
    municipio_selecionado = None
    codigo_uf = None
    codigo_municipio = None
    
    if uf_selecionada != "Selecione um estado...":
        # Encontra o código da UF selecionada
        codigo_uf = SaudeApi.extrair_codigo_uf(uf_selecionada, ufs)
        
        if codigo_uf:
            with col2:
                # Carregamento dos municípios
                municipios = SaudeApi.get_municipios_por_uf(codigo_uf)
                
                if municipios:
                    municipio_options = ["Selecione um município..."] + [SaudeApi.formatar_municipio_para_dropdown(municipio) for municipio in municipios]
                    municipio_selecionado = st.selectbox("🏘️ Município", municipio_options)
                    
                    if municipio_selecionado != "Selecione um município...":
                        codigo_municipio = SaudeApi.extrair_codigo_municipio(municipio_selecionado, municipios)
    
    # Botão de consulta
    if codigo_uf and codigo_municipio:
        st.success(f"✅ Configurado: {uf_selecionada} → {municipio_selecionado}")
        
        if st.button("🚀 Gerar Relatório Completo de ACS", type="primary", use_container_width=True):

            # Consulta múltiplas competências para o ano selecionado
            dados_consolidados, metricas_temporais, resultados = consultar_multiplas_competencias(codigo_uf, codigo_municipio, ano_selecionado)
            
            if metricas_temporais:
                st.markdown("---")
                
                # Usa a primeira métrica para o cabeçalho
                primeira_metrica = metricas_temporais[0]
                st.header(f"📊 {municipio_selecionado} - {uf_selecionada.split(' - ')[0]}")
                st.caption(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} | Ano: {ano_selecionado} | {len(metricas_temporais)} competências analisadas")
                
                # Cria métricas consolidadas (média/última competência)
                ultima_competencia = metricas_temporais[-1]
                metrics_consolidadas = ACSMetrics(
                    estado=uf_selecionada.split(' - ')[0],
                    municipio=municipio_selecionado,
                    codigo_uf=codigo_uf,
                    codigo_municipio=codigo_municipio,
                    quantidade_teto=ultima_competencia['quantidade_teto'],
                    quantidade_credenciado=ultima_competencia['quantidade_credenciado'],
                    quantidade_pago=ultima_competencia['quantidade_pago'],
                    total_deveria_receber=sum(m.get('repasse_esperado', m.get('total_deveria_receber', 0)) for m in metricas_temporais),
                    total_recebido=sum(m.get('repasse_recebido', m.get('total_recebido', 0)) for m in metricas_temporais),
                    total_perda=sum(m.get('perda_repasse', m.get('total_perda', 0)) for m in metricas_temporais),
                    taxa_ocupacao=ultima_competencia['taxa_ocupacao'],
                    taxa_pagamento=ultima_competencia['taxa_pagamento'],
                    eficiencia=ultima_competencia['eficiencia'],
                    percentual_perda=sum(m.get('perda_repasse', m.get('total_perda', 0)) for m in metricas_temporais) / sum(m.get('repasse_esperado', m.get('total_deveria_receber', 1)) for m in metricas_temporais) * 100 if sum(m.get('repasse_esperado', m.get('total_deveria_receber', 1)) for m in metricas_temporais) > 0 else 0
                )
                
                # Cards principais
                create_main_metrics_cards(metrics_consolidadas)
                
                st.markdown("---")
                
                # Gráficos resumo
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_summary = create_summary_chart(metrics_consolidadas)
                    st.plotly_chart(fig_summary, use_container_width=True)
                
                with col2:
                    fig_financial = create_financial_chart(metrics_consolidadas)
                    st.plotly_chart(fig_financial, use_container_width=True)
                
                # Gráfico temporal
                st.subheader("📈 Evolução Temporal das Métricas")
                fig_temporal = create_temporal_chart(metricas_temporais)
                if fig_temporal:
                    st.plotly_chart(fig_temporal, use_container_width=True)
                
                # Tabela detalhada
                st.subheader("📋 Detalhamento por Competência")
                df_detalhado = pd.DataFrame(metricas_temporais)
                
                # Colunas com compatibilidade para nomes antigos e novos (sem teto)
                colunas_display = ['competencia_formatada', 'quantidade_credenciado', 'quantidade_pago']
                
                # Adiciona colunas de repasse (novo) ou financeiras (antigo)
                if 'repasse_recebido' in df_detalhado.columns:
                    colunas_display.extend(['repasse_recebido', 'perda_repasse'])
                else:
                    colunas_display.extend(['total_recebido', 'total_perda'])
                
                colunas_display.append('eficiencia')
                
                df_display = df_detalhado[colunas_display].copy()
                df_display.columns = ['Competência', 'Credenciados', 'Pagos', 'Repasse Recebido (R$)', 'Perda Repasse (R$)', 'Eficiência (%)']
                
                # Formatação
                df_display['Repasse Recebido (R$)'] = df_display['Repasse Recebido (R$)'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                df_display['Perda Repasse (R$)'] = df_display['Perda Repasse (R$)'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                df_display['Eficiência (%)'] = df_display['Eficiência (%)'].apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(df_display, use_container_width=True)
                
                # Download dos dados
                st.subheader("⬇️ Exportar Relatório")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV do relatório
                    csv_string = df_detalhado.to_csv(index=False, encoding='utf-8-sig')
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename_csv = f"relatorio_acs_{municipio_selecionado.replace(' ', '_')}_{timestamp}.csv"
                    
                    st.download_button(
                        label="📊 Baixar Relatório CSV",
                        data=csv_string,
                        file_name=filename_csv,
                        mime="text/csv"
                    )
                
                with col2:
                    # JSON consolidado
                    dados_export = {
                        'municipio': municipio_selecionado,
                        'uf': uf_selecionada.split(' - ')[0],
                        'data_relatorio': datetime.now().isoformat(),
                        'metricas_por_competencia': metricas_temporais,
                        'resumo_consolidado': dados_consolidados['resumo_geral']
                    }
                    json_string = json.dumps(dados_export, indent=2, ensure_ascii=False)
                    filename_json = f"dados_acs_{municipio_selecionado.replace(' ', '_')}_{timestamp}.json"
                    
                    st.download_button(
                        label="📥 Baixar Dados JSON",
                        data=json_string,
                        file_name=filename_json,
                        mime="application/json"
                    )
                
            else:
                st.warning("⚠️ Nenhum dado de ACS encontrado para este município nas competências consultadas.")
                st.info("💡 **Dica**: Nem todos os municípios possuem dados de ACS disponíveis em todas as competências.")
    
    else:
        # Informações sobre o sistema
        st.markdown("---")
        st.info("👆 **Selecione um estado e município para gerar o relatório completo de ACS**")
        
        with st.expander("ℹ️ Sobre o Relatório Multi-Competência"):
            st.markdown("""
            Este relatório consulta **automaticamente todas as competências disponíveis** para o ano selecionado,
            fornecendo uma análise temporal completa dos Agentes Comunitários de Saúde.
            
            **📊 As 5 Métricas Principais:**
            1. **✅ ACS Credenciados** - Total de ACS habilitados (direto + indireto)
            2. **💰 ACS Pagos** - Total de ACS que receberam pagamento
            3. **🎯 Repasse Federal Esperado** - Valor estimado baseado nos credenciados
            4. **💵 Repasse Federal Recebido** - Valor efetivamente transferido
            5. **📉 Perda de Repasse Federal** - Diferença entre esperado e recebido
            
            **🔄 Funcionalidades:**
            - ✅ Consulta automática de múltiplas competências
            - ✅ Gráficos temporais de evolução
            - ✅ Cards visuais com status por cores
            - ✅ Tabela detalhada por período
            - ✅ Download de relatórios CSV e JSON
            - ✅ Análise de tendências e eficiência
            
            **⏱️ Tempo estimado:** 3-5 segundos por competência
            """)

# Copyright na barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.8em; margin-top: 2rem;'>"
    "© Mais Gestor (2025)<br>"
    "Todos os direitos reservados"
    "</div>", 
    unsafe_allow_html=True
)

if __name__ == "__main__":
    main()