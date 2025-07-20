import requests
import streamlit as st
from typing import List, Dict, Optional

class IBGEApi:
    BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
    
    @staticmethod
    @st.cache_data
    def get_estados() -> List[Dict]:
        """
        Obtém lista de todos os estados brasileiros da API do IBGE
        """
        try:
            response = requests.get(f"{IBGEApi.BASE_URL}/estados")
            response.raise_for_status()
            estados = response.json()
            
            # Ordena por nome
            estados = sorted(estados, key=lambda x: x['nome'])
            return estados
        except requests.RequestException as e:
            st.error(f"Erro ao carregar estados: {e}")
            return []
    
    @staticmethod
    @st.cache_data
    def get_municipios_por_estado(codigo_uf: str) -> List[Dict]:
        """
        Obtém lista de municípios por código da UF
        """
        try:
            response = requests.get(f"{IBGEApi.BASE_URL}/estados/{codigo_uf}/municipios")
            response.raise_for_status()
            municipios = response.json()
            
            # Ordena por nome
            municipios = sorted(municipios, key=lambda x: x['nome'])
            return municipios
        except requests.RequestException as e:
            st.error(f"Erro ao carregar municípios: {e}")
            return []
    
    @staticmethod
    def formatar_estado_para_dropdown(estado: Dict) -> str:
        """
        Formata estado para exibição no dropdown
        """
        return f"{estado['sigla']} - {estado['nome']}"
    
    @staticmethod
    def formatar_municipio_para_dropdown(municipio: Dict) -> str:
        """
        Formata município para exibição no dropdown
        """
        return municipio['nome']