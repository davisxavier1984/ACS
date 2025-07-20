"""
Módulo para gerenciar competências e fazer loop de consultas
"""
import requests
import streamlit as st
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CompetenciaData:
    """Dados de uma competência específica"""
    competencia: str
    parcela: str
    status: str
    dados: Optional[Dict] = None
    erro: Optional[str] = None

class CompetenciasManager:
    """Gerenciador de competências para consultas em lote"""
    
    def __init__(self, base_url: str = "https://relatorioaps-prd.saude.gov.br"):
        self.base_url = base_url
        self.headers = self._get_headers()
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers necessários para as requisições"""
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
    
    def get_competencias_disponiveis(self, ano: int = 2025) -> List[str]:
        """Retorna lista de competências disponíveis para um ano"""
        competencias = []
        for mes in range(1, 13):  # Janeiro a Dezembro
            competencia = f"{ano}{mes:02d}"
            competencias.append(competencia)
        
        # Para 2025, limita até julho (conforme dados conhecidos)
        if ano == 2025:
            competencias = competencias[:7]  # Jan-Jul
        
        return competencias
    
    def consultar_competencia(self, codigo_uf: str, codigo_municipio: str, 
                            competencia: str, tipo_relatorio: str = "COMPLETO") -> CompetenciaData:
        """Consulta uma competência específica"""
        
        params = {
            "unidadeGeografica": "MUNICIPIO",
            "coUf": codigo_uf,
            "coMunicipio": codigo_municipio,
            "nuParcelaInicio": competencia,
            "nuParcelaFim": competencia,
            "tipoRelatorio": tipo_relatorio
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/financiamento/pagamento",
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                dados = response.json()
                if dados and 'pagamentos' in dados and dados['pagamentos']:
                    return CompetenciaData(
                        competencia=competencia,
                        parcela=competencia,
                        status="sucesso",
                        dados=dados
                    )
                else:
                    return CompetenciaData(
                        competencia=competencia,
                        parcela=competencia,
                        status="sem_dados",
                        erro="Sem dados de pagamento para esta competência"
                    )
            else:
                return CompetenciaData(
                    competencia=competencia,
                    parcela=competencia,
                    status="erro_http",
                    erro=f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            return CompetenciaData(
                competencia=competencia,
                parcela=competencia,
                status="erro_requisicao",
                erro=str(e)
            )
    
    def consultar_multiplas_competencias(self, codigo_uf: str, codigo_municipio: str, 
                                       competencias: List[str], 
                                       progress_callback=None) -> List[CompetenciaData]:
        """Consulta múltiplas competências com progress bar"""
        
        resultados = []
        total = len(competencias)
        
        for i, competencia in enumerate(competencias):
            # Atualiza progress bar se fornecido
            if progress_callback:
                progress_callback(i / total, f"Consultando {competencia}...")
            
            resultado = self.consultar_competencia(codigo_uf, codigo_municipio, competencia)
            resultados.append(resultado)
            
            # Pequena pausa para não sobrecarregar a API
            import time
            time.sleep(0.5)
        
        if progress_callback:
            progress_callback(1.0, "Consultas concluídas!")
        
        return resultados
    
    def consolidar_dados_acs(self, resultados: List[CompetenciaData]) -> Dict:
        """Consolida dados de ACS de múltiplas competências"""
        
        dados_consolidados = {
            'competencias': [],
            'dados_por_competencia': {},
            'resumo_geral': {
                'total_competencias': 0,
                'competencias_com_dados': 0,
                'competencias_com_acs': 0
            }
        }
        
        for resultado in resultados:
            dados_consolidados['competencias'].append(resultado.competencia)
            dados_consolidados['resumo_geral']['total_competencias'] += 1
            
            if resultado.status == "sucesso" and resultado.dados:
                dados_consolidados['resumo_geral']['competencias_com_dados'] += 1
                
                # Verifica se tem dados de ACS
                pagamentos = resultado.dados.get('pagamentos', [])
                acs_records = [r for r in pagamentos if 'qtTetoAcs' in r]
                
                if acs_records:
                    dados_consolidados['resumo_geral']['competencias_com_acs'] += 1
                    dados_consolidados['dados_por_competencia'][resultado.competencia] = {
                        'dados': resultado.dados,
                        'registros_acs': len(acs_records),
                        'primeiro_registro': acs_records[0] if acs_records else None
                    }
        
        return dados_consolidados
    
    def extrair_metricas_por_competencia(self, dados_consolidados: Dict) -> List[Dict]:
        """Extrai as 6 métricas específicas por competência"""
        
        metricas_temporais = []
        
        for competencia, info in dados_consolidados['dados_por_competencia'].items():
            primeiro_registro = info.get('primeiro_registro')
            
            if primeiro_registro:
                # Extrai as 6 métricas específicas
                teto = primeiro_registro.get('qtTetoAcs', 0)
                credenciado_direto = primeiro_registro.get('qtAcsDiretoCredenciado', 0)
                credenciado_indireto = primeiro_registro.get('qtAcsIndiretoCredenciado', 0)
                pago_direto = primeiro_registro.get('qtAcsDiretoPgto', 0)
                pago_indireto = primeiro_registro.get('qtAcsIndiretoPgto', 0)
                valor_direto = primeiro_registro.get('vlTotalAcsDireto', 0)
                valor_indireto = primeiro_registro.get('vlTotalAcsIndireto', 0)
                
                credenciados = credenciado_direto + credenciado_indireto
                pagos = pago_direto + pago_indireto
                total_recebido = valor_direto + valor_indireto
                
                # Calcula valor que deveria receber (estimativa baseada no valor unitário)
                if pagos > 0 and total_recebido > 0:
                    valor_unitario = total_recebido / pagos
                    deveria_receber = teto * valor_unitario
                else:
                    deveria_receber = total_recebido
                
                # Perda de repasse federal (sempre positiva)
                perda = max(0, deveria_receber - total_recebido)
                
                metricas = {
                    'competencia': competencia,
                    'competencia_formatada': f"{competencia[:4]}/{competencia[4:]}",
                    'quantidade_teto': teto,
                    'quantidade_credenciado': credenciados,
                    'quantidade_pago': pagos,
                    'repasse_esperado': deveria_receber,
                    'repasse_recebido': total_recebido,
                    'perda_repasse': perda,
                    # Métricas auxiliares para análise
                    'taxa_ocupacao': (credenciados / teto * 100) if teto > 0 else 0,
                    'taxa_pagamento': (pagos / credenciados * 100) if credenciados > 0 else 0,
                    'eficiencia': (pagos / teto * 100) if teto > 0 else 0,
                    'percentual_perda_repasse': (perda / deveria_receber * 100) if deveria_receber > 0 else 0
                }
                
                metricas_temporais.append(metricas)
        
        return metricas_temporais