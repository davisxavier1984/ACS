import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from saude_api import SaudeApi

# Configuração da página
st.set_page_config(
    page_title="Consulta API Ministério da Saúde",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Consulta de Financiamento APS - Ministério da Saúde")
st.markdown("Sistema para consulta de dados de financiamento da Atenção Primária à Saúde por município")

# URL da API do Ministério da Saúde
API_SAUDE_URL = "https://relatorioaps-prd.saude.gov.br/financiamento/pagamento"

def fazer_requisicao_saude(codigo_uf: str, codigo_municipio: str, parcela_inicio: str, parcela_fim: str, tipo_relatorio: str = "COMPLETO"):
    """
    Faz requisição para a API do Ministério da Saúde com headers corretos
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
        with st.spinner("Fazendo requisição..."):
            st.info(f"Consultando: UF={codigo_uf}, Município={codigo_municipio}, Período={parcela_inicio}-{parcela_fim}")
            response = requests.get(API_SAUDE_URL, params=params, headers=headers, timeout=30)
            
            # Debug da resposta
            st.write(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                if dados:
                    return dados
                else:
                    st.warning("API retornou dados vazios. Verifique se o município possui dados para o período selecionado.")
                    return None
            else:
                st.error(f"Erro HTTP {response.status_code}: {response.text}")
                return None
                
    except requests.RequestException as e:
        st.error(f"Erro na requisição: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Erro ao decodificar JSON: {e}")
        st.write("Resposta recebida:", response.text[:500] + "..." if len(response.text) > 500 else response.text)
        return None

def main():
    # Sidebar com configurações
    st.sidebar.header("⚙️ Configurações")
    
    # Carregamento das UFs
    ufs = SaudeApi.get_ufs()
    
    if not ufs:
        st.error("Não foi possível carregar a lista de UFs. Verifique sua conexão.")
        return
    
    # Seleção da UF
    uf_options = ["Selecione um estado..."] + [SaudeApi.formatar_uf_para_dropdown(uf) for uf in ufs]
    uf_selecionada = st.sidebar.selectbox("🗺️ Estado (UF)", uf_options)
    
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
                municipio_selecionado = st.sidebar.selectbox("🏘️ Município", municipio_options)
                
                if municipio_selecionado != "Selecione um município...":
                    codigo_municipio = SaudeApi.extrair_codigo_municipio(municipio_selecionado, municipios)
    
    # Configurações de período
    st.sidebar.subheader("📅 Período")
    
    # Carrega anos disponíveis
    anos_disponiveis = SaudeApi.get_anos_disponiveis()
    
    if anos_disponiveis:
        # Campos de período com anos válidos
        col1, col2 = st.sidebar.columns(2)
        with col1:
            ano_inicio = st.selectbox("Ano início", anos_disponiveis, index=0 if anos_disponiveis else 0)
            mes_inicio = st.number_input("Mês início", min_value=1, max_value=12, value=1)
        
        with col2:
            ano_fim = st.selectbox("Ano fim", anos_disponiveis, index=0 if anos_disponiveis else 0)
            mes_fim = st.number_input("Mês fim", min_value=1, max_value=12, value=12)
        
        # Mostra parcelas disponíveis se um ano estiver selecionado
        if ano_inicio:
            parcelas_inicio = SaudeApi.get_parcelas_por_ano(ano_inicio)
            if parcelas_inicio:
                st.sidebar.info(f"📊 {len(parcelas_inicio)} parcelas disponíveis em {ano_inicio}")
    else:
        # Fallback para campos manuais
        ano_atual = datetime.now().year
        col1, col2 = st.sidebar.columns(2)
        with col1:
            ano_inicio = st.number_input("Ano início", min_value=2020, max_value=ano_atual, value=ano_atual)
            mes_inicio = st.number_input("Mês início", min_value=1, max_value=12, value=1)
        
        with col2:
            ano_fim = st.number_input("Ano fim", min_value=2020, max_value=ano_atual, value=ano_atual)
            mes_fim = st.number_input("Mês fim", min_value=1, max_value=12, value=12)
    
    # Formatação das parcelas
    parcela_inicio = f"{ano_inicio}{mes_inicio:02d}"
    parcela_fim = f"{ano_fim}{mes_fim:02d}"
    
    # Tipo de relatório
    tipo_relatorio = st.sidebar.selectbox("📊 Tipo de Relatório", ["COMPLETO", "RESUMIDO"])
    
    # Área principal
    if codigo_uf and codigo_municipio:
        st.success(f"✅ Configurado: {uf_selecionada} → {municipio_selecionado}")
        
        # Informações da requisição
        with st.expander("ℹ️ Detalhes da Requisição"):
            st.write(f"**Estado:** {uf_selecionada} (Código: {codigo_uf})")
            st.write(f"**Município:** {municipio_selecionado} (Código: {codigo_municipio})")
            st.write(f"**Período:** {parcela_inicio} até {parcela_fim}")
            st.write(f"**Tipo:** {tipo_relatorio}")
        
        # Botão para fazer requisição
        if st.button("🚀 Consultar Dados", type="primary", use_container_width=True):
            dados = fazer_requisicao_saude(codigo_uf, codigo_municipio, parcela_inicio, parcela_fim, tipo_relatorio)
            
            if dados:
                st.success("✅ Dados obtidos com sucesso!")
                
                # Tabs para visualização
                tab1, tab2, tab3 = st.tabs(["📊 Dados", "🔍 JSON", "⬇️ Download"])
                
                with tab1:
                    st.subheader("Dados Retornados")
                    
                    # Se for uma lista, mostra como DataFrame
                    if isinstance(dados, list) and dados:
                        df = pd.DataFrame(dados)
                        st.dataframe(df, use_container_width=True)
                        st.info(f"Total de registros: {len(dados)}")
                    elif isinstance(dados, dict):
                        # Se for dict, tenta mostrar as chaves principais
                        for key, value in dados.items():
                            if isinstance(value, (list, dict)):
                                st.write(f"**{key}:** {type(value).__name__}")
                                if isinstance(value, list) and value:
                                    st.write(f"  - {len(value)} itens")
                            else:
                                st.write(f"**{key}:** {value}")
                    else:
                        st.write("Dados recebidos em formato não tabelar")
                
                with tab2:
                    st.subheader("JSON Completo")
                    st.json(dados)
                
                with tab3:
                    st.subheader("Download dos Dados")
                    
                    # Prepara o JSON para download
                    json_string = json.dumps(dados, indent=2, ensure_ascii=False)
                    
                    # Nome do arquivo
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    municipio_nome = municipio_selecionado.replace(' ', '_') if municipio_selecionado else 'municipio'
                    filename = f"dados_saude_{municipio_nome}_{timestamp}.json"
                    
                    st.download_button(
                        label="📥 Baixar JSON",
                        data=json_string,
                        file_name=filename,
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    st.info(f"Arquivo: {filename}")
                    st.info(f"Tamanho: {len(json_string):,} caracteres")
    
    else:
        st.info("👈 Selecione um estado e município na barra lateral para começar")
        
        # Informações sobre a aplicação
        with st.expander("ℹ️ Sobre esta aplicação"):
            st.markdown("""
            Esta aplicação permite consultar dados de financiamento da Atenção Primária à Saúde 
            através da API oficial do Ministério da Saúde.
            
            **Funcionalidades:**
            - 🗺️ Seleção de estados e municípios via APIs nativas do Ministério da Saúde
            - 📅 Configuração inteligente de período com anos disponíveis
            - 📊 Visualização dos dados em formato tabular
            - 🔍 Visualização do JSON completo
            - ⬇️ Download dos dados em formato JSON
            
            **APIs utilizadas:**
            - `/ufs` - Lista de unidades federativas
            - `/ibge/municipios` - Municípios por UF
            - `/data/parcelas` - Parcelas disponíveis por ano
            - `/financiamento/pagamento` - Dados de financiamento
            
            **Como usar:**
            1. Selecione o estado na barra lateral
            2. Escolha o município
            3. Configure o período desejado (apenas anos com dados)
            4. Clique em "Consultar Dados"
            5. Visualize e faça download dos resultados
            """)

if __name__ == "__main__":
    main()