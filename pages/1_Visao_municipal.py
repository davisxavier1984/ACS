import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import plotly.express as px
from acs_analyzer import ACSAnalyzer
from saude_api import SaudeApi
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.units import inch, cm
from PIL import Image as PILImage
import io
import base64

# Constante para cálculo de valores esperados
VALOR_REPASSE_POR_ACS = 3036.00

# Configuração da página
st.set_page_config(
    page_title="Dashboard ACS - Análise Municipal",
    page_icon="🏘️", 
    layout="wide"
)

def formatar_moeda_brasileira(valor: float) -> str:
    """
    Formata um valor numérico para o padrão de moeda brasileira com abreviações Mil e Mi
    """
    if valor is None:
        return "R$ 0,00"
    
    if valor >= 1_000_000:
        return f"R$ {valor/1_000_000:.1f}Mi"
    elif valor >= 1_000:
        return f"R$ {valor/1_000:.0f}Mil"
    else:
        # Para valores menores que 1000, manter formato original
        valor_formatado = f"{valor:,.2f}"
        partes = valor_formatado.split('.')
        parte_inteira = partes[0]
        parte_decimal = partes[1] if len(partes) > 1 else "00"
        parte_inteira = parte_inteira.replace(',', '.')
        return f"R$ {parte_inteira},{parte_decimal}"

def plotly_to_image(fig):
    """
    Converte um gráfico Plotly para PIL Image compatível com ReportLab
    """
    img_bytes = fig.to_image(format="png", width=800, height=400)
    return PILImage.open(io.BytesIO(img_bytes))

def gerar_pdf_municipal(municipio: str, uf: str, df_3_meses: pd.DataFrame, dados_atual: pd.Series, competencias: list) -> io.BytesIO:
    """
    Gera PDF PROFISSIONAL com o dashboard municipal completo
    Qualidade corporativa "Mais Gestor" com fidelidade visual total à interface web
    
    Args:
        municipio: Nome do município
        uf: Nome do estado
        df_3_meses: DataFrame com dados dos 3 meses
        dados_atual: Série com dados do mês atual
        competencias: Lista de competências analisadas
    
    Returns:
        BytesIO com o PDF gerado
    """
    buffer = io.BytesIO()
    width, height = A4
    margin = 20  # Margens profissionais
    
    # Criar canvas com controle total
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    
    # === SEÇÃO 1: HEADER CORPORATIVO COM LOGO ===
    header_height = 80
    y_header = height - margin - header_height
    
    # Logo Mais Gestor com fundo branco (lado esquerdo)
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            # Fundo branco atrás da logo
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.lightgrey)
            c.setLineWidth(1)
            c.roundRect(margin, y_header + 25, 85, 55, 5, fill=True, stroke=True)
            
            # Logo PNG com tamanho aumentado
            c.drawInlineImage(logo_path, margin + 2.5, y_header + 27.5, width=80, height=50, preserveAspectRatio=True)
    except:
        pass  # Se logo não existir, continua sem erro
    
    # Título corporativo (lado direito do logo)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor('#003366'))
    titulo = f"Dashboard ACS - {municipio.split('/')[0]}"
    c.drawString(margin + 100, y_header + 45, titulo)
    
    # Subtítulo elegante
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor('#666666'))
    subtitulo = f"{uf} • {competencias[-1]} a {competencias[0]} • {datetime.now().strftime('%d/%m/%Y')}"
    c.drawString(margin + 100, y_header + 25, subtitulo)
    
    # Linha separadora elegante
    c.setStrokeColor(colors.HexColor('#003366'))
    c.setLineWidth(2)
    c.line(margin, y_header, width - margin, y_header)
    
    # === SEÇÃO 2: CARDS KPI PROFISSIONAIS ===
    kpi_y = y_header - 120
    kpi_height = 80
    kpi_width = (width - 2*margin - 40) / 3  # 40pt para espaçamento
    
    # Dados para cálculo
    dados_anterior = df_3_meses.iloc[1] if len(df_3_meses) > 1 else None
    valor_recebido = dados_atual['vlTotalAcs']
    acs_pagos = dados_atual['qtTotalPago']
    valor_esperado = dados_atual['vlEsperado']
    
    # Calcular deltas
    delta_valor = valor_recebido - dados_anterior['vlTotalAcs'] if dados_anterior is not None else 0
    delta_acs = int(acs_pagos - dados_anterior['qtTotalPago']) if dados_anterior is not None else 0
    delta_esperado = valor_esperado - dados_anterior['vlEsperado'] if dados_anterior is not None else 0
    
    # Dados dos cards com cores dinâmicas
    cards_data = [
        {
            'titulo': 'Valor Recebido',
            'valor': formatar_moeda_brasileira(valor_recebido),
            'delta': delta_valor,
            'x_pos': margin,
            'cor_bg': colors.HexColor('#E8F5E8') if delta_valor >= 0 else colors.HexColor('#FFEBEE'),
            'cor_borda': colors.HexColor('#2ca02c') if delta_valor >= 0 else colors.HexColor('#D32F2F'),
            'cor_delta': colors.HexColor('#2ca02c') if delta_valor >= 0 else colors.HexColor('#D32F2F')
        },
        {
            'titulo': 'ACS Pagos',
            'valor': f"{int(acs_pagos)}",
            'delta': delta_acs,
            'x_pos': margin + kpi_width + 20,
            'cor_bg': colors.HexColor('#E3F2FD') if delta_acs >= 0 else colors.HexColor('#FFEBEE'),
            'cor_borda': colors.HexColor('#1976D2') if delta_acs >= 0 else colors.HexColor('#D32F2F'),
            'cor_delta': colors.HexColor('#1976D2') if delta_acs >= 0 else colors.HexColor('#D32F2F')
        },
        {
            'titulo': 'Valor Esperado',
            'valor': formatar_moeda_brasileira(valor_esperado),
            'delta': delta_esperado,
            'x_pos': margin + 2*kpi_width + 40,
            'cor_bg': colors.HexColor('#FFF3E0'),
            'cor_borda': colors.HexColor('#FF9800'),
            'cor_delta': colors.HexColor('#E65100')
        }
    ]
    
    # Desenhar cards KPI profissionais
    for card in cards_data:
        x_pos = card['x_pos']
        
        # Card com sombra (efeito offset)
        c.setFillColor(colors.HexColor('#DDDDDD'))
        c.roundRect(x_pos + 2, kpi_y - 2, kpi_width, kpi_height, 8, fill=True, stroke=False)  # Sombra
        
        # Card principal com fundo colorido
        c.setFillColor(card['cor_bg'])
        c.setStrokeColor(card['cor_borda'])
        c.setLineWidth(2)
        c.roundRect(x_pos, kpi_y, kpi_width, kpi_height, 8, fill=True, stroke=True)
        
        # Título do card
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor('#424242'))
        c.drawString(x_pos + 10, kpi_y + kpi_height - 20, card['titulo'])
        
        # Valor principal (grande e destacado)
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.HexColor('#212121'))
        c.drawString(x_pos + 10, kpi_y + kpi_height - 45, card['valor'])
        
        # Delta com seta
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(card['cor_delta'])
        delta_val = card['delta']
        
        if 'ACS' in card['titulo']:
            delta_str = f"+{int(delta_val)}" if delta_val >= 0 else str(int(delta_val))
            seta = "↗" if delta_val >= 0 else "↘"
        else:
            delta_str = f"+{abs(delta_val)/1000:.0f}K" if delta_val >= 0 else f"-{abs(delta_val)/1000:.0f}K"
            seta = "↗" if delta_val >= 0 else "↘"
        
        c.drawString(x_pos + 10, kpi_y + 12, f"{seta} {delta_str}")
    
    # === SEÇÃO 3: GRÁFICOS PROFISSIONAIS ===
    graph_y = kpi_y - 220
    graph_height_section = 200
    
    # Preparar dados dos gráficos
    meses = [comp.replace('/', '/') for comp in df_3_meses['competencia'].tolist()[::-1]]
    valores_esperados = df_3_meses['vlEsperado'].tolist()[::-1]
    valores_recebidos = df_3_meses['vlTotalAcs'].tolist()[::-1]
    acs_credenciados = df_3_meses['qtTotalCredenciado'].tolist()[::-1]
    acs_pagos_lista = df_3_meses['qtTotalPago'].tolist()[::-1]
    
    # Gráfico Financeiro
    fig_financeiro = go.Figure()
    fig_financeiro.add_trace(go.Bar(
        name='Valor Esperado',
        x=meses,
        y=valores_esperados,
        marker_color='#003366',
        text=[f'{v/1000:.0f}K' for v in valores_esperados],
        textposition='auto',
        textfont={'size': 10, 'color': 'white'}
    ))
    fig_financeiro.add_trace(go.Bar(
        name='Valor Recebido',
        x=meses,
        y=valores_recebidos,
        marker_color='#2ca02c',
        text=[f'{v/1000:.0f}K' for v in valores_recebidos],
        textposition='auto',
        textfont={'size': 10, 'color': 'white'}
    ))
    
    fig_financeiro.update_layout(
        title={'text': '💰 Análise Financeira', 'font': {'size': 14, 'color': '#003366'}, 'x': 0.5},
        xaxis={'tickfont': {'size': 10}},
        yaxis={'tickfont': {'size': 10}},
        barmode='group',
        height=graph_height_section,
        width=int((width - 2*margin - 15) / 2),
        showlegend=True,
        legend={'font': {'size': 10}, 'orientation': 'h', 'y': 1.15, 'x': 0.5, 'xanchor': 'center'},
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Gráfico de Pessoal
    fig_pessoal = go.Figure()
    fig_pessoal.add_trace(go.Bar(
        name='ACS Credenciados',
        x=meses,
        y=acs_credenciados,
        marker_color='#8c8c8c',
        text=acs_credenciados,
        textposition='auto',
        textfont={'size': 10, 'color': 'white'}
    ))
    fig_pessoal.add_trace(go.Bar(
        name='ACS Pagos',
        x=meses,
        y=acs_pagos_lista,
        marker_color='#ff7f0e',
        text=acs_pagos_lista,
        textposition='auto',
        textfont={'size': 10, 'color': 'white'}
    ))
    
    fig_pessoal.update_layout(
        title={'text': '👥 Análise de Pessoal', 'font': {'size': 14, 'color': '#003366'}, 'x': 0.5},
        xaxis={'tickfont': {'size': 10}},
        yaxis={'tickfont': {'size': 10}},
        barmode='group',
        height=graph_height_section,
        width=int((width - 2*margin - 15) / 2),
        showlegend=True,
        legend={'font': {'size': 10}, 'orientation': 'h', 'y': 1.15, 'x': 0.5, 'xanchor': 'center'},
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Adicionar gráficos ao PDF
    img_financeiro = plotly_to_image(fig_financeiro)
    img_pessoal = plotly_to_image(fig_pessoal)
    
    graph_width = (width - 2*margin - 15) / 2
    c.drawInlineImage(img_financeiro, margin, graph_y, width=graph_width, height=graph_height_section)
    c.drawInlineImage(img_pessoal, margin + graph_width + 15, graph_y, width=graph_width, height=graph_height_section)
    
    # === SEÇÃO 4: TABELA PROFISSIONAL ===
    table_y = graph_y - 160
    table_height_section = 120
    
    # Título da seção
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor('#003366'))
    c.drawString(margin, table_y + table_height_section - 15, "📊 Resumo Mensal Detalhado")
    
    # Configurar tabela
    row_height = 20
    col_widths = [80, 100, 90, 70, 70]
    headers = ['Competência', 'Valor Recebido', 'Variação', 'ACS Pagos', 'Var. ACS']
    
    # Calcular posição central da tabela
    table_width = sum(col_widths)
    table_x = (width - table_width) / 2  # Centralizar na página
    
    # Header da tabela (azul corporativo)
    header_y = table_y + table_height_section - 45
    c.setFillColor(colors.HexColor('#003366'))
    c.rect(table_x, header_y, table_width, row_height, fill=True, stroke=False)
    
    # Texto do header (branco)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.white)
    x_pos = table_x + 5
    for i, header in enumerate(headers):
        c.drawString(x_pos, header_y + 6, header)
        x_pos += col_widths[i]
    
    # Dados da tabela com zebra striping
    c.setFont("Helvetica", 9)
    for i, (idx, row) in enumerate(df_3_meses.iterrows()):
        y_row = header_y - (i + 1) * row_height
        
        # Zebra striping (linhas alternadas)
        if i % 2 == 1:
            c.setFillColor(colors.HexColor('#F5F5F5'))
            c.rect(table_x, y_row, table_width, row_height, fill=True, stroke=False)
        
        # Calcular variações
        mes_anterior = None
        idx_atual = df_3_meses.index.get_loc(idx)
        if idx_atual < len(df_3_meses) - 1:
            mes_anterior = df_3_meses.iloc[idx_atual + 1]
        
        var_valor = row['vlTotalAcs'] - mes_anterior['vlTotalAcs'] if mes_anterior is not None else 0
        var_acs = row['qtTotalPago'] - mes_anterior['qtTotalPago'] if mes_anterior is not None else 0
        
        # Dados da linha
        dados_linha = [
            row['competencia'],
            formatar_moeda_brasileira(row['vlTotalAcs']),
            formatar_moeda_brasileira(var_valor) if var_valor >= 0 else f"-{formatar_moeda_brasileira(abs(var_valor))}" if var_valor != 0 else "—",
            f"{int(row['qtTotalPago'])}",
            f"{int(var_acs):+d}" if var_acs != 0 else "—"
        ]
        
        # Desenhar dados com cores condicionais
        x_pos = table_x + 5
        for j, dado in enumerate(dados_linha):
            # Colorir variações condicionalmente
            if j == 2 and dado != "—":  # Variação valor
                if dado.startswith('+'):
                    c.setFillColor(colors.HexColor('#2E7D32'))  # Verde escuro
                else:
                    c.setFillColor(colors.HexColor('#C62828'))  # Vermelho escuro
            elif j == 4 and dado != "—":  # Variação ACS
                if dado.startswith('+'):
                    c.setFillColor(colors.HexColor('#2E7D32'))  # Verde escuro
                else:
                    c.setFillColor(colors.HexColor('#C62828'))  # Vermelho escuro
            else:
                c.setFillColor(colors.HexColor('#212121'))  # Preto
            
            c.drawString(x_pos, y_row + 6, dado)
            x_pos += col_widths[j]
    
    # === SEÇÃO 5: STATUS REGULAMENTAR ===
    status_y = table_y - 80
    variacao_mensal = calcular_variacao_mensal(dados_atual, df_3_meses)
    
    if variacao_mensal < 0:
        # Card de alerta vermelho expandido
        card_height = 85
        c.setFillColor(colors.HexColor('#FFEBEE'))
        c.setStrokeColor(colors.HexColor('#D32F2F'))
        c.setLineWidth(2)
        c.roundRect(margin, status_y, width - 2*margin, card_height, 5, fill=True, stroke=True)
        
        # Título do alerta
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor('#D32F2F'))
        c.drawString(margin + 10, status_y + card_height - 18, "🚨 ALERTA REGULAMENTAR")
        
        # Portaria
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor('#424242'))
        c.drawString(margin + 10, status_y + card_height - 35, "Portaria GM/MS Nº 6.907, de 29 de abril de 2025")
        
        # Motivo da suspensão (quebra após "produção")
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor('#424242'))
        c.drawString(margin + 10, status_y + card_height - 50, "Motivo: Observadas 6 (seis) competências consecutivas de ausência de envio de informação sobre a produção")
        c.drawString(margin + 10, status_y + card_height - 62, "ao SISAB - Suspensão do recurso ACS")
        
        # Perda financeira
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor('#D32F2F'))
        c.drawString(margin + 10, status_y + 10, f"PERDA APROXIMADA: {formatar_moeda_brasileira(abs(variacao_mensal))}/MÊS")
    else:
        # Card de conformidade verde
        c.setFillColor(colors.HexColor('#E8F5E8'))
        c.setStrokeColor(colors.HexColor('#2ca02c'))
        c.setLineWidth(2)
        c.roundRect(margin, status_y, width - 2*margin, 40, 5, fill=True, stroke=True)
        
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor('#2ca02c'))
        c.drawString(margin + 10, status_y + 20, "✅ Município em conformidade regulamentar")
    
    # === FOOTER CORPORATIVO ===
    footer_y = 40
    
    # Linha separadora
    c.setStrokeColor(colors.HexColor('#DDDDDD'))
    c.setLineWidth(1)
    c.line(margin, footer_y + 25, width - margin, footer_y + 25)
    
    # Texto do footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor('#666666'))
    c.drawString(margin, footer_y + 15, "© 2025 Mais Gestor - Sistema ACS | Relatório gerado automaticamente")
    c.drawString(margin, footer_y + 5, f"Fonte: Ministério da Saúde • Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    
    # Finalizar PDF
    c.save()
    buffer.seek(0)
    return buffer

# Ler parâmetros da URL para drill-down
query_params = st.query_params
uf_param = query_params.get("uf", None)
municipio_ibge_param = query_params.get("municipio_ibge", None)
competencia_param = query_params.get("competencia", None)

def carregar_dados_locais_municipio(codigo_municipio: str, competencias: list) -> dict:
    """
    Carrega dados locais para um município específico e competências específicas
    
    Args:
        codigo_municipio: Código IBGE do município
        competencias: Lista de competências no formato "AAAA/MM"
        
    Returns:
        Dict com dados encontrados por competência
    """
    dados_encontrados = {}
    data_dir = Path("data")
    json_files = list(data_dir.glob("dados_*.json"))
    
    for competencia in competencias:
        dados_encontrados[competencia] = None
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dados_brutos = json.load(f)
                
                # Verificar se esta competência está nos metadados
                metadados_competencias = dados_brutos.get('metadados', {}).get('competencias', [])
                if competencia not in metadados_competencias:
                    continue
                
                # Buscar o município nos resultados
                resultados = dados_brutos.get('resultados', [])
                for resultado in resultados:
                    if str(resultado.get('codigo_municipio', '')) == str(codigo_municipio):
                        # Verificar se tem dados para esta competência específica
                        dados_processados = ACSAnalyzer.processar_dados_coletados([resultado])
                        df_temp = pd.DataFrame(dados_processados)
                        
                        # Filtrar pela competência
                        df_competencia = df_temp[df_temp['competencia'] == competencia]
                        if not df_competencia.empty:
                            dados_encontrados[competencia] = df_competencia.iloc[0].to_dict()
                            break
                
                if dados_encontrados[competencia] is not None:
                    break
                    
            except Exception as e:
                st.warning(f"Erro ao ler arquivo {file_path}: {e}")
                continue
    
    return dados_encontrados

def buscar_dados_api(codigo_uf: str, codigo_municipio: str, competencia: str) -> dict:
    """
    Busca dados via API para uma competência específica e os formata
    para serem processados pelo ACSAnalyzer.processar_dados_coletados
    """
    dados_brutos_api = SaudeApi.get_dados_pagamento(codigo_uf, codigo_municipio, competencia)
    
    if dados_brutos_api is None:
        return None
    
    # Formatar para simular a saída de um único item do coletor
    # ACSAnalyzer.processar_dados_coletados espera uma lista de dicionários,
    # onde cada dicionário tem chaves como 'municipio', 'competencia', 'dados', 'status'
    
    municipio_nome = "Nome Desconhecido" # Será preenchido pelo ACSAnalyzer se disponível nos dados brutos
    if dados_brutos_api and 'pagamentos' in dados_brutos_api and dados_brutos_api['pagamentos']:
        # Tenta extrair o nome do município do primeiro registro de pagamento, se disponível
        first_payment_record = dados_brutos_api['pagamentos']
        if first_payment_record and 'noMunicipio' in first_payment_record:
            municipio_nome = first_payment_record['noMunicipio']


    # Retornar o dicionário no formato que o ACSAnalyzer.processar_dados_coletados espera
    # (um item da lista 'resultados' do JSON salvo)
    resultado_formatado = {
        'uf': SaudeApi.extrair_sigla_uf(codigo_uf), # Extrai sigla da UF
        'codigo_uf': codigo_uf,
        'municipio': municipio_nome,
        'codigo_municipio': codigo_municipio,
        'competencia': competencia, # Formato AAAA/MM
        'timestamp_coleta': datetime.now().isoformat(),
        'status': 'sucesso',
        'dados': dados_brutos_api # O JSON bruto completo da API vai para a chave 'dados'
    }
    
    # Agora, passe esta lista contendo UM item para ACSAnalyzer.processar_dados_coletados
    # A função processar_dados_coletados já espera uma LISTA
    dados_processados = ACSAnalyzer.processar_dados_coletados([resultado_formatado])

    if dados_processados:
        return dados_processados[0] # Retorna o primeiro item processado (que é o único)
    
    return None # Retorna None se não conseguir processar

def calcular_variacao_mensal(dados_atual, df_3_meses) -> float:
    """
    Calcula a variação mensal usando a mesma lógica da tabela.
    
    Args:
        dados_atual: Linha mais recente (dados do mês atual)
        df_3_meses: DataFrame completo com dados dos 3 meses
        
    Returns:
        float: Variação mensal (atual - anterior). Negativo = perda
    """
    if dados_atual is None or df_3_meses is None or len(df_3_meses) < 2:
        return 0
    
    # dados_atual é df_3_meses.iloc[0] (mais recente)
    # mes_anterior é df_3_meses.iloc[1] (segundo mais recente)
    valor_atual = dados_atual.get('vlTotalAcs', 0)
    mes_anterior = df_3_meses.iloc[1]
    valor_anterior = mes_anterior.get('vlTotalAcs', 0)
    
    # Variação mensal: atual - anterior (igual à tabela)
    variacao_mensal = valor_atual - valor_anterior
    return variacao_mensal

def detectar_condicoes_suspensao(dados_atual, df_3_meses) -> bool:
    """
    Detecta condições que indicam suspensão de recursos ACS.
    Critério: qualquer perda mensal (variação negativa).
    
    Args:
        dados_atual: Pandas Series com dados do município (linha mais recente)
        df_3_meses: DataFrame completo para calcular variação mensal
        
    Returns:
        bool: True se devemos mostrar o alerta de suspensão (sempre que há perda mensal)
    """
    # Verificar se dados_atual é None ou Series/DataFrame vazio
    if dados_atual is None:
        return False
    
    # Para pandas Series, verificar se está vazio
    if hasattr(dados_atual, 'empty') and dados_atual.empty:
        return False
    
    # Calcular variação mensal usando a mesma lógica da tabela
    variacao_mensal = calcular_variacao_mensal(dados_atual, df_3_meses)
    
    # Critério simples: mostrar sempre que há perda mensal (variação negativa)
    # Isso corresponde aos valores vermelhos na tabela
    return variacao_mensal < 0

def render_suspension_status_card(dados_atual, df_3_meses, municipio: str):
    """
    Renderiza o card de alerta regulamentar com informações da Portaria GM/MS 6.907.
    
    Args:
        dados_atual: Pandas Series com dados do município (linha mais recente)
        df_3_meses: DataFrame completo para calcular variação mensal
        municipio: Nome do município para exibição
    """
    # Calcular variação mensal usando a mesma lógica da tabela
    variacao_mensal = calcular_variacao_mensal(dados_atual, df_3_meses)
    
    # Usar o valor absoluto da variação (para mostrar a perda como valor positivo)
    valor_perda = abs(variacao_mensal)
    
    # Usar função existente para formatar moeda
    valor_formatado = formatar_moeda_brasileira(valor_perda)
    
    # Renderizar card de alerta usando st.error para destaque visual máximo
    st.error(f"""
🚨 **ALERTA REGULAMENTAR - {municipio}**

**Portaria GM/MS Nº 6.907, de 29 de abril de 2025**

**Motivo da Suspensão:** Observadas 6 (seis) competências consecutivas de ausência de envio de informação sobre a produção ao Sistema de Informação em Saúde para a Atenção Básica (SISAB).

Suspensão do recurso do ACS.

**PERDA APROXIMADAMENTE {valor_formatado}/MÊS**
    """)

def gerar_ultimas_competencias(competencia_referencia: str, qtd: int = 3) -> list:
    """
    Gera lista das últimas competências a partir de uma competência de referência
    
    Args:
        competencia_referencia: Competência no formato "AAAA/MM"
        qtd: Quantidade de competências a retornar
        
    Returns:
        Lista de competências em ordem decrescente
    """
    try:
        ano, mes = map(int, competencia_referencia.split('/'))
        data_ref = datetime(ano, mes, 1)
        
        competencias = []
        for i in range(qtd):
            data_comp = data_ref - relativedelta(months=i)
            comp_str = f"{data_comp.year}/{data_comp.month:02d}"
            competencias.append(comp_str)
        
        return competencias
    except Exception as e:
        st.error(f"Erro ao gerar competências: {e}")
        return []

# --- Interface Principal ---
# Logo e cabeçalho
col_logo, col_title = st.columns([1, 4])

with col_logo:
    st.image("logo.png", width=120)

with col_title:
    st.title("🏘️ Dashboard ACS - Análise Municipal")
    st.markdown("**Sistema de análise detalhada dos Agentes Comunitários de Saúde por município**")

# Informações sobre navegação entre páginas
with st.expander("📌 Sobre o Sistema ACS"):
    st.markdown("""
    **🏘️ Página Atual: Análise Municipal (Página Principal)**
    - Análise detalhada de um município específico nos últimos 3 meses
    - Dados históricos e comparativos
    - Visualizações financeiras e de pessoal
    
    **📑 Outras Análises Disponíveis:**
    - **Visão Estadual**: Comparação entre municípios de um estado
    - **Análise Multi-Competência**: Relatório temporal completo com múltiplas competências
    
    **💡 Dica**: Use a barra lateral para navegar entre as diferentes visões!
    """)

st.markdown("---")

# Seletores
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔍 Seleção de Localização")
    
    # Carregar UFs
    ufs = SaudeApi.get_ufs()
    ufs_formatadas = [SaudeApi.formatar_uf_para_dropdown(uf) for uf in ufs]
    
    # Encontrar o índice do UF que veio como parâmetro
    default_uf_index = 0
    if uf_param and uf_param in [uf['codigo'] for uf in ufs]:
        default_uf_index = [uf['codigo'] for uf in ufs].index(uf_param)
    
    uf_selecionada = st.selectbox("Estado (UF):", ufs_formatadas, index=default_uf_index)
    
    # Extrair código da UF selecionada
    codigo_uf = SaudeApi.extrair_codigo_uf(uf_selecionada, ufs)
    
    # Carregar municípios se UF foi selecionada
    municipios = []
    if codigo_uf:
        municipios = SaudeApi.get_municipios_por_uf(codigo_uf)
        municipios_formatados = [SaudeApi.formatar_municipio_para_dropdown(mun) for mun in municipios]
        
        # Encontrar o índice do município que veio como parâmetro
        default_municipio_index = 0
        if municipio_ibge_param and municipio_ibge_param in [mun['codigo'] for mun in municipios]:
            default_municipio_index = [mun['codigo'] for mun in municipios].index(municipio_ibge_param)
        
        municipio_selecionado = st.selectbox("Município:", municipios_formatados, index=default_municipio_index)
        codigo_municipio = SaudeApi.extrair_codigo_municipio(municipio_selecionado, municipios)
    else:
        st.warning("Selecione uma UF válida")
        codigo_municipio = None

with col2:
    st.subheader("📅 Período de Análise")
    
    # Competência de referência
    competencia_referencia = st.selectbox(
        "Competência de Referência:",
        ["2025/07", "2025/06", "2025/05", "2025/04", "2025/03", "2025/02", "2025/01",
         "2024/12", "2024/11", "2024/10", "2024/09", "2024/08", "2024/07"]
    )
    
    # Botão de análise
    analisar_manualmente = st.button("🔍 Analisar Município", type="primary", use_container_width=True)

# Processamento quando botão for clicado OU quando parâmetros da URL estiverem presentes
if ((uf_param and municipio_ibge_param) or analisar_manualmente) and codigo_uf and codigo_municipio and competencia_referencia:
    
    # Gerar competências dos últimos 3 meses
    competencias_desejadas = gerar_ultimas_competencias(competencia_referencia, 3)
    
    # Tentar carregar dados locais primeiro
    dados_locais = carregar_dados_locais_municipio(codigo_municipio, competencias_desejadas)
    
    # Buscar dados ausentes via API
    dados_finais = []
    
    for comp in competencias_desejadas:
        if dados_locais[comp] is not None:
            # Usar dados locais
            dados_finais.append(dados_locais[comp])
        else:
            # Buscar via API
            dados_api = buscar_dados_api(codigo_uf, codigo_municipio, comp)
            
            if dados_api is not None:
                dados_finais.append(dados_api)
    
    # Processar dados e criar dashboard
    if dados_finais:
        df_3_meses = pd.DataFrame(dados_finais)
        
        # Adicionar colunas calculadas se não existirem
        if 'qtTotalCredenciado' not in df_3_meses.columns:
            df_3_meses['qtTotalCredenciado'] = (
                df_3_meses.get('qtAcsDiretoCredenciado', 0) + 
                df_3_meses.get('qtAcsIndiretoCredenciado', 0)
            )
        
        if 'qtTotalPago' not in df_3_meses.columns:
            df_3_meses['qtTotalPago'] = (
                df_3_meses.get('qtAcsDiretoPgto', 0) + 
                df_3_meses.get('qtAcsIndiretoPgto', 0)
            )
        
        if 'vlTotalAcs' not in df_3_meses.columns:
            df_3_meses['vlTotalAcs'] = (
                df_3_meses.get('vlTotalAcsDireto', 0) + 
                df_3_meses.get('vlTotalAcsIndireto', 0)
            )
        
        # Adicionar coluna valor esperado (baseado em ACS credenciados diretos e valor oficial de repasse)
        df_3_meses['vlEsperado'] = df_3_meses.get('qtAcsDiretoCredenciado', 0) * VALOR_REPASSE_POR_ACS
        
        # Ordenar por competência (mais recente primeiro)
        df_3_meses = df_3_meses.sort_values('competencia', ascending=False)
        
        
        # === TÍTULO E CONTEXTO ===
        st.divider()
        st.title(f"🏘️ Dashboard Municipal - {municipio_selecionado}")
        st.info(f"📍 **Estado:** {uf_selecionada} | **Período:** {competencias_desejadas[-1]} a {competencias_desejadas[0]} | **Registros:** {len(df_3_meses)}")
        
        # === KPIs MUNICIPAIS COM DELTAS ===
        st.header("📊 Indicadores Principais")
        
        # Dados do mês mais recente e anterior para calcular deltas
        dados_atual = df_3_meses.iloc[0] if len(df_3_meses) > 0 else None
        dados_anterior = df_3_meses.iloc[1] if len(df_3_meses) > 1 else None
        
        if dados_atual is not None:
            col1, col2, col3 = st.columns(3)

            # --- KPI 1: Valor Recebido (R$) ---
            with col1:
                valor_recebido = dados_atual['vlTotalAcs']
                delta_valor = float(valor_recebido - dados_anterior['vlTotalAcs']) if dados_anterior is not None else 0
                st.metric(
                    "Valor Recebido (R$)",
                    value=formatar_moeda_brasileira(valor_recebido),
                    delta=delta_valor if dados_anterior is not None else None,
                    delta_color="normal" # Verde para positivo, vermelho para negativo
                )

            # --- KPI 2: ACS Pagos ---
            with col2:
                acs_pagos = dados_atual['qtTotalPago']
                delta_acs = int(acs_pagos - dados_anterior['qtTotalPago']) if dados_anterior is not None else 0
                st.metric(
                    "ACS Pagos",
                    value=f"{int(acs_pagos)}",
                    delta=delta_acs if dados_anterior is not None else None,
                    delta_color="normal" # Verde para positivo, vermelho para negativo
                )

            # --- KPI 3: Valor Esperado (R$) ---
            with col3:
                valor_esperado = dados_atual['vlEsperado'] # Agora vlEsperado está calculado corretamente
                delta_esperado = float(valor_esperado - dados_anterior['vlEsperado']) if dados_anterior is not None else 0
                st.metric(
                    "Valor Esperado (R$)",
                    value=formatar_moeda_brasileira(valor_esperado),
                    delta=delta_esperado if dados_anterior is not None else None,
                    delta_color="normal" # Verde para positivo, vermelho para negativo
                )

                
        
        # === GRÁFICOS COMPARATIVOS ===
        st.header("📈 Análise Comparativa")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Análise Financeira")
            
            # Preparar dados para o gráfico financeiro
            meses = [comp.replace('/', '/') for comp in df_3_meses['competencia'].tolist()[::-1]]  # Ordem cronológica
            valores_esperados = df_3_meses['vlEsperado'].tolist()[::-1]
            valores_recebidos = df_3_meses['vlTotalAcs'].tolist()[::-1]
            
            fig_financeiro = go.Figure()
            fig_financeiro.add_trace(go.Bar(
                name='Valor Esperado',
                x=meses,
                y=valores_esperados,
                marker_color='#003366',  # Azul Escuro
                text=[f'R$ {v:,.0f}' for v in valores_esperados],
                textposition='auto'
            ))
            fig_financeiro.add_trace(go.Bar(
                name='Valor Recebido',
                x=meses,
                y=valores_recebidos,
                marker_color='#2ca02c',  # Verde Vibrante
                text=[f'R$ {v:,.0f}' for v in valores_recebidos],
                textposition='auto'
            ))
            
            fig_financeiro.update_layout(
                title='Comparação: Esperado vs Recebido',
                xaxis_title='Competência',
                yaxis_title='Valor (R$)',
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig_financeiro, use_container_width=True)
        
        with col2:
            st.subheader("👥 Análise de Pessoal")
            
            # Preparar dados para o gráfico de pessoal
            acs_credenciados = df_3_meses['qtTotalCredenciado'].tolist()[::-1]
            acs_pagos_lista = df_3_meses['qtTotalPago'].tolist()[::-1]
            
            fig_pessoal = go.Figure()
            fig_pessoal.add_trace(go.Bar(
                name='ACS Credenciados',
                x=meses,
                y=acs_credenciados,
                marker_color='#8c8c8c',  # Cinza Médio
                text=acs_credenciados,
                textposition='auto'
            ))
            fig_pessoal.add_trace(go.Bar(
                name='ACS Pagos',
                x=meses,
                y=acs_pagos_lista,
                marker_color='#ff7f0e',  # Laranja Intenso
                text=acs_pagos_lista,
                textposition='auto'
            ))
            
            fig_pessoal.update_layout(
                title='Comparação: Credenciados vs Pagos',
                xaxis_title='Competência',
                yaxis_title='Quantidade de ACS',
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig_pessoal, use_container_width=True)
        
        # === TABELA DE RESUMO DETALHADA ===
        st.header("📋 Resumo Detalhado por Mês")
        
        # Criar DataFrame para tabela com variações calculadas
        tabela_resumo = []
        
        for i, row in df_3_meses.iterrows():
            # Encontrar dados do mês anterior para calcular variação
            mes_anterior = None
            idx_atual = df_3_meses.index.get_loc(i)
            if idx_atual < len(df_3_meses) - 1:
                mes_anterior = df_3_meses.iloc[idx_atual + 1]
            
            # Calcular variações
            var_valor = row['vlTotalAcs'] - mes_anterior['vlTotalAcs'] if mes_anterior is not None else 0
            var_acs = row['qtTotalPago'] - mes_anterior['qtTotalPago'] if mes_anterior is not None else 0
            perda_ganho = var_valor  # Simplificado - pode ser refinado
            
            tabela_resumo.append({
                'Mês/Ano': row['competencia'],
                'Valor Recebido (R$)': row['vlTotalAcs'],
                'Variação vs. Mês Ant. (R$)': var_valor,
                'ACS Pagos': int(row['qtTotalPago']),
                'Variação vs. Mês Ant. (Qtd.)': int(var_acs),
                'Perda/Ganho (R$)': perda_ganho
            })
        
        df_tabela = pd.DataFrame(tabela_resumo)
        
        # Função para colorir valores negativos e positivos
        def color_negative_red_positive_green(val):
            if isinstance(val, (int, float)):
                if val < 0:
                    return 'color: #D32F2F; font-weight: bold;'  # Vermelho
                elif val > 0:
                    return 'color: #388E3C; font-weight: bold;'  # Verde
            return ''
        
        # Aplicar formatação e cores
        styled_table = df_tabela.style.applymap(
            color_negative_red_positive_green,
            subset=['Variação vs. Mês Ant. (R$)', 'Variação vs. Mês Ant. (Qtd.)', 'Perda/Ganho (R$)']
        ).format({
            'Valor Recebido (R$)': 'R$ {:,.2f}',
            'Variação vs. Mês Ant. (R$)': 'R$ {:+,.2f}',
            'ACS Pagos': '{:,d}',
            'Variação vs. Mês Ant. (Qtd.)': '{:+,d}',
            'Perda/Ganho (R$)': 'R$ {:+,.2f}'
        })
        
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
        
        # === SEÇÃO REGULAMENTAR ===
        st.markdown("---")  # Separador visual
        st.subheader("⚖️ Status Regulamentar")
        
        # Verificar condições de suspensão baseado nos dados atuais
        if detectar_condicoes_suspensao(dados_atual, df_3_meses):
            render_suspension_status_card(dados_atual, df_3_meses, municipio_selecionado)
        else:
            st.success("✅ Município em conformidade com as normas regulamentares vigentes")
        
        # === BOTÃO PARA GERAR PDF ===
        st.markdown("---")
        st.subheader("📄 Exportar Relatório")
        
        col_pdf1, col_pdf2, col_pdf3 = st.columns([2, 1, 2])
        with col_pdf2:
            if st.button("📄 Gerar PDF", type="secondary", use_container_width=True):
                with st.spinner("Gerando PDF do relatório..."):
                    try:
                        # Gerar nome do arquivo
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        municipio_limpo = municipio_selecionado.split('/')[0].replace(' ', '_')
                        nome_arquivo = f"Relatorio_ACS_{municipio_limpo}_{timestamp}.pdf"
                        
                        # Gerar PDF
                        pdf_buffer = gerar_pdf_municipal(
                            municipio_selecionado, 
                            uf_selecionada, 
                            df_3_meses, 
                            dados_atual, 
                            competencias_desejadas
                        )
                        
                        # Botão de download
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=nome_arquivo,
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
                        
                        st.success("✅ PDF gerado com sucesso! Clique em 'Download PDF' para baixar.")
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar PDF: {str(e)}")
                        st.warning("Verifique se todas as dependências estão instaladas: `pip install reportlab kaleido Pillow`")
        
    else:
        st.error("❌ Nenhum dado foi encontrado para o município e período selecionados.")

elif analisar_manualmente:
    st.error("⚠️ Por favor, selecione UF, município e competência de referência antes de analisar.")

else:
    # Informações sobre o sistema quando nada foi selecionado
    st.markdown("---")
    st.info("👆 **Selecione um estado, município e período para começar a análise**")
    
    # Exemplo com dados de teste
    with st.expander("💡 Exemplo de Análise - Dados de Teste"):
        st.markdown("""
        **Município exemplo:** Abaré/PE (Pernambuco)
        - Este município possui dados ACS disponíveis para teste
        - Período recomendado: 2025/06 
        - Use este exemplo para explorar as funcionalidades do sistema
        
        **Funcionalidades da Análise Municipal:**
        - 📊 KPIs principais com variações mensais
        - 📈 Gráficos comparativos (financeiro e pessoal)
        - 📋 Tabela detalhada com histórico de 3 meses
        - 🔍 Busca automática em dados locais e API
        
        **Navegação:**
        - Use a barra lateral para acessar outras análises
        - **Visão Estadual**: Comparar municípios de um estado
        - **Multi-Competência**: Análise temporal completa
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