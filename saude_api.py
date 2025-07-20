import requests
import streamlit as st
from typing import List, Dict, Optional

class SaudeApi:
    BASE_URL = "https://relatorioaps-prd.saude.gov.br"
    
    # Lista oficial de UFs do Brasil com códigos IBGE
    UFS_BRASIL = [
        {"codigo": "11", "sigla": "RO", "nome": "Rondônia"},
        {"codigo": "12", "sigla": "AC", "nome": "Acre"},
        {"codigo": "13", "sigla": "AM", "nome": "Amazonas"},
        {"codigo": "14", "sigla": "RR", "nome": "Roraima"},
        {"codigo": "15", "sigla": "PA", "nome": "Pará"},
        {"codigo": "16", "sigla": "AP", "nome": "Amapá"},
        {"codigo": "17", "sigla": "TO", "nome": "Tocantins"},
        {"codigo": "21", "sigla": "MA", "nome": "Maranhão"},
        {"codigo": "22", "sigla": "PI", "nome": "Piauí"},
        {"codigo": "23", "sigla": "CE", "nome": "Ceará"},
        {"codigo": "24", "sigla": "RN", "nome": "Rio Grande do Norte"},
        {"codigo": "25", "sigla": "PB", "nome": "Paraíba"},
        {"codigo": "26", "sigla": "PE", "nome": "Pernambuco"},
        {"codigo": "27", "sigla": "AL", "nome": "Alagoas"},
        {"codigo": "28", "sigla": "SE", "nome": "Sergipe"},
        {"codigo": "29", "sigla": "BA", "nome": "Bahia"},
        {"codigo": "31", "sigla": "MG", "nome": "Minas Gerais"},
        {"codigo": "32", "sigla": "ES", "nome": "Espírito Santo"},
        {"codigo": "33", "sigla": "RJ", "nome": "Rio de Janeiro"},
        {"codigo": "35", "sigla": "SP", "nome": "São Paulo"},
        {"codigo": "41", "sigla": "PR", "nome": "Paraná"},
        {"codigo": "42", "sigla": "SC", "nome": "Santa Catarina"},
        {"codigo": "43", "sigla": "RS", "nome": "Rio Grande do Sul"},
        {"codigo": "50", "sigla": "MS", "nome": "Mato Grosso do Sul"},
        {"codigo": "51", "sigla": "MT", "nome": "Mato Grosso"},
        {"codigo": "52", "sigla": "GO", "nome": "Goiás"},
        {"codigo": "53", "sigla": "DF", "nome": "Distrito Federal"}
    ]
    
    @staticmethod
    def _get_headers():
        """
        Headers necessários para todas as requisições à API do Ministério da Saúde
        """
        return {
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
    
    @staticmethod
    def get_ufs() -> List[Dict]:
        """
        Obtém lista de UFs do Brasil (lista local - sempre disponível)
        """
        return SaudeApi.UFS_BRASIL.copy()
    
    @staticmethod
    @st.cache_data
    def get_municipios_por_uf(codigo_uf: str) -> List[Dict]:
        """
        Obtém lista de municípios por código da UF usando a API nativa do Ministério da Saúde
        """
        try:
            response = requests.get(
                f"{SaudeApi.BASE_URL}/ibge/municipios", 
                params={"coUf": codigo_uf},
                headers=SaudeApi._get_headers(), 
                timeout=30
            )
            response.raise_for_status()
            municipios = response.json()
            
            # Ordena por nome se tiver a estrutura esperada
            if municipios and isinstance(municipios, list) and len(municipios) > 0:
                if isinstance(municipios[0], dict) and 'nome' in municipios[0]:
                    municipios = sorted(municipios, key=lambda x: x.get('nome', ''))
            
            return municipios
        except requests.RequestException as e:
            st.error(f"Erro ao carregar municípios: {e}")
            return []
    
    @staticmethod
    def get_anos_disponiveis() -> List[int]:
        """
        Obtém lista de anos disponíveis (lista local - API /anos não existe)
        Baseado no orienta.txt - apenas /data/parcelas?ano=X existe
        """
        return [2025, 2024, 2023, 2022, 2021, 2020]
    
    @staticmethod
    @st.cache_data
    def get_parcelas_por_ano(ano: int) -> List[Dict]:
        """
        Obtém parcelas disponíveis para um ano específico
        """
        try:
            response = requests.get(
                f"{SaudeApi.BASE_URL}/data/parcelas", 
                params={"ano": ano},
                headers=SaudeApi._get_headers(), 
                timeout=30
            )
            response.raise_for_status()
            parcelas = response.json()
            
            return parcelas if isinstance(parcelas, list) else []
        except requests.RequestException as e:
            st.warning(f"Erro ao carregar parcelas para {ano}: {e}")
            return []
    
    @staticmethod
    @st.cache_data
    def get_parcelas_por_ano_mes(ano: int, mes: int) -> List[Dict]:
        """
        Obtém parcelas disponíveis para um ano e mês específicos
        """
        try:
            response = requests.get(
                f"{SaudeApi.BASE_URL}/data/parcelas", 
                params={"ano": ano, "mes": mes},
                headers=SaudeApi._get_headers(), 
                timeout=30
            )
            response.raise_for_status()
            parcelas = response.json()
            
            return parcelas if isinstance(parcelas, list) else []
        except requests.RequestException as e:
            st.warning(f"Erro ao carregar parcelas para {ano}/{mes:02d}: {e}")
            return []
    
    @staticmethod
    def formatar_uf_para_dropdown(uf: Dict) -> str:
        """
        Formata UF para exibição no dropdown
        """
        if isinstance(uf, dict):
            sigla = uf.get('sigla', uf.get('codigo', ''))
            nome = uf.get('nome', '')
            if sigla and nome:
                return f"{sigla} - {nome}"
            elif nome:
                return nome
            elif sigla:
                return sigla
        return str(uf)
    
    @staticmethod
    def formatar_municipio_para_dropdown(municipio: Dict) -> str:
        """
        Formata município para exibição no dropdown
        """
        if isinstance(municipio, dict):
            return municipio.get('nome', str(municipio))
        return str(municipio)
    
    @staticmethod
    def extrair_codigo_uf(uf_formatada: str, ufs: List[Dict]) -> Optional[str]:
        """
        Extrai código da UF a partir da string formatada
        """
        if " - " in uf_formatada:
            sigla = uf_formatada.split(" - ")[0]
            for uf in ufs:
                if uf.get('sigla') == sigla:
                    return uf.get('codigo')
        return None
    
    @staticmethod
    def extrair_codigo_municipio(municipio_nome: str, municipios: List[Dict]) -> Optional[str]:
        """
        Extrai código do município a partir do nome
        """
        for municipio in municipios:
            if municipio.get('nome') == municipio_nome:
                return str(municipio.get('codigo', municipio.get('id', municipio.get('codigoIBGE', ''))))
        return None