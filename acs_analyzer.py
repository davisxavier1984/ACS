import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ACSMetrics:
    """Classe para armazenar as 6 métricas principais de ACS"""
    estado: str
    municipio: str
    codigo_uf: str
    codigo_municipio: str
    
    # AS 6 MÉTRICAS PRINCIPAIS SOLICITADAS
    quantidade_teto: int                    # qtTetoAcs
    quantidade_credenciado: int             # qtAcsDiretoCredenciado + qtAcsIndiretoCredenciado  
    quantidade_pago: int                    # qtAcsDiretoPgto + qtAcsIndiretoPgto
    total_deveria_receber: float           # Valor estimado baseado no teto
    total_recebido: float                  # vlTotalAcsDireto + vlTotalAcsIndireto
    total_perda: float                     # Diferença entre deveria receber e recebido
    
    # Métricas auxiliares para análise
    taxa_ocupacao: float                   # credenciados/teto * 100
    taxa_pagamento: float                  # pagos/credenciados * 100
    eficiencia: float                      # pagos/teto * 100
    percentual_perda: float                # perda/deveria_receber * 100
    
    # Detalhamento (mantido para compatibilidade)
    credenciados_direto: int = 0
    credenciados_indireto: int = 0
    pagos_direto: int = 0
    pagos_indireto: int = 0
    valor_recebido_direto: float = 0
    valor_recebido_indireto: float = 0
    
    # Período
    competencias: List[str] = None
    data_atualizacao: str = ""

@dataclass
class ACSDetalhePeriodo:
    """Detalhamento por período/competência"""
    competencia: str
    parcela: str
    teto: int
    credenciados_direto: int
    credenciados_indireto: int
    pagos_direto: int
    pagos_indireto: int
    valor_direto: float
    valor_indireto: float
    valor_total: float

class ACSAnalyzer:
    """Analisador de dados de ACS"""
    
    @staticmethod
    def extract_acs_data(json_data: Dict) -> Optional[ACSMetrics]:
        """
        Extrai e calcula métricas de ACS do JSON da API
        """
        # Verifica se há dados na seção 'pagamentos' (onde estão os campos de ACS)
        if not json_data:
            return None
        
        # Prioriza dados da seção 'pagamentos' onde estão os campos qtTetoAcs
        pagamentos = json_data.get('pagamentos', [])
        resumos = json_data.get('resumosPlanosOrcamentarios', [])
        
        # Encontra registros com dados de ACS - Filtro Duplo
        acs_records = []
        acs_orcamentarios = []
        
        # Primeiro, procura na seção 'pagamentos' (dados detalhados com qtTetoAcs)
        for record in pagamentos:
            if 'qtTetoAcs' in record:
                acs_records.append(record)
        
        # Se não encontrou na seção pagamentos, procura na seção resumos (dados orçamentários)
        if not acs_records:
            for record in resumos:
                # Dados detalhados (com campos quantitativos) - pouco provável aqui
                if 'qtTetoAcs' in record:
                    acs_records.append(record)
                # Dados orçamentários (apenas valores financeiros)
                elif record.get('dsPlanoOrcamentario') == 'Agentes Comunitários de Saúde':
                    acs_orcamentarios.append(record)
        
        # Se não há dados detalhados, tenta usar dados orçamentários
        if not acs_records and not acs_orcamentarios:
            return None
        
        # Prioritiza dados detalhados, mas aceita orçamentários como fallback
        if acs_records:
            # Usa dados detalhados (com campos quantitativos)
            dados_principais = acs_records
            usar_dados_orcamentarios = False
        else:
            # Usa dados orçamentários (só valores financeiros)
            dados_principais = acs_orcamentarios
            usar_dados_orcamentarios = True
        
        # Pega informações básicas do primeiro registro
        first_record = dados_principais[0]
        estado = first_record.get('sgUf', '')
        municipio = first_record.get('noMunicipio', '')
        codigo_uf = first_record.get('coUfIbge', '')
        codigo_municipio = first_record.get('coMunicipioIbge', '')
        
        # Agrega dados por competência
        competencias_data = {}
        
        if usar_dados_orcamentarios:
            # Usa dados orçamentários (apenas valores financeiros)
            for record in dados_principais:
                comp = record.get('nuCompCnes', '')
                parcela = record.get('nuParcela', '')
                
                if comp not in competencias_data:
                    competencias_data[comp] = {
                        'competencia': comp,
                        'parcela': parcela,
                        'teto': 0,  # Não disponível nos dados orçamentários
                        'credenciados_direto': 0,  # Não disponível
                        'credenciados_indireto': 0,  # Não disponível
                        'pagos_direto': 0,  # Não disponível
                        'pagos_indireto': 0,  # Não disponível
                        'valor_direto': record.get('vlEfetivoRepasse', 0),  # Usa valor efetivo
                        'valor_indireto': 0
                    }
        else:
            # Usa dados detalhados (com campos quantitativos)
            for record in dados_principais:
                comp = record.get('nuCompCnes', '')
                parcela = record.get('nuParcela', '')
                
                if comp not in competencias_data:
                    competencias_data[comp] = {
                        'competencia': comp,
                        'parcela': parcela,
                        'teto': record.get('qtTetoAcs', 0),
                        'credenciados_direto': record.get('qtAcsDiretoCredenciado', 0),
                        'credenciados_indireto': record.get('qtAcsIndiretoCredenciado', 0),
                        'pagos_direto': record.get('qtAcsDiretoPgto', 0),
                        'pagos_indireto': record.get('qtAcsIndiretoPgto', 0),
                        'valor_direto': record.get('vlTotalAcsDireto', 0),
                        'valor_indireto': record.get('vlTotalAcsIndireto', 0)
                    }
        
        # Calcula totais e médias
        if not competencias_data:
            return None
        
        # Pega a competência mais recente para os dados principais
        ultima_comp = max(competencias_data.keys())
        dados_comp = competencias_data[ultima_comp]
        
        # Extrai as 6 métricas principais de forma clara
        quantidade_teto = dados_comp['teto']
        credenciados_direto = dados_comp['credenciados_direto']
        credenciados_indireto = dados_comp['credenciados_indireto']
        quantidade_credenciado = credenciados_direto + credenciados_indireto
        
        pagos_direto = dados_comp['pagos_direto']
        pagos_indireto = dados_comp['pagos_indireto']
        quantidade_pago = pagos_direto + pagos_indireto
        
        # Valores financeiros (soma de todas as competências)
        valor_recebido_direto = sum(comp['valor_direto'] for comp in competencias_data.values())
        valor_recebido_indireto = sum(comp['valor_indireto'] for comp in competencias_data.values())
        total_recebido = valor_recebido_direto + valor_recebido_indireto
        
        # Calcula quanto deveria receber baseado no teto
        if usar_dados_orcamentarios:
            # Para dados orçamentários, usa valor recebido como referência
            total_deveria_receber = total_recebido
        else:
            # Para dados detalhados, calcula valor previsto baseado no teto
            if quantidade_pago > 0 and total_recebido > 0:
                valor_unitario_medio = total_recebido / quantidade_pago
                total_deveria_receber = quantidade_teto * valor_unitario_medio
            else:
                total_deveria_receber = total_recebido
        
        # Calcula a perda total (sempre positiva - perda de repasse federal)
        total_perda = max(0, total_deveria_receber - total_recebido)
        
        # Calcula métricas auxiliares
        taxa_ocupacao = (quantidade_credenciado / quantidade_teto * 100) if quantidade_teto > 0 else 0
        taxa_pagamento = (quantidade_pago / quantidade_credenciado * 100) if quantidade_credenciado > 0 else 0
        eficiencia = (quantidade_pago / quantidade_teto * 100) if quantidade_teto > 0 else 0
        # Percentual de perda de repasse federal
        percentual_perda = (total_perda / total_deveria_receber * 100) if total_deveria_receber > 0 else 0
        
        return ACSMetrics(
            estado=estado,
            municipio=municipio,
            codigo_uf=codigo_uf,
            codigo_municipio=codigo_municipio,
            # AS 6 MÉTRICAS PRINCIPAIS
            quantidade_teto=quantidade_teto,
            quantidade_credenciado=quantidade_credenciado,
            quantidade_pago=quantidade_pago,
            total_deveria_receber=total_deveria_receber,
            total_recebido=total_recebido,
            total_perda=total_perda,
            # Métricas auxiliares
            taxa_ocupacao=taxa_ocupacao,
            taxa_pagamento=taxa_pagamento,
            eficiencia=eficiencia,
            percentual_perda=percentual_perda,
            # Detalhamento (para compatibilidade)
            credenciados_direto=credenciados_direto,
            credenciados_indireto=credenciados_indireto,
            pagos_direto=pagos_direto,
            pagos_indireto=pagos_indireto,
            valor_recebido_direto=valor_recebido_direto,
            valor_recebido_indireto=valor_recebido_indireto,
            # Período
            competencias=list(competencias_data.keys()),
            data_atualizacao=json_data.get('data', datetime.now().strftime('%d/%m/%Y'))
        )
    
    @staticmethod
    def extract_acs_timeline(json_data: Dict) -> List[ACSDetalhePeriodo]:
        """
        Extrai dados de ACS por período para análise temporal
        """
        if not json_data:
            return []
        
        # Prioriza dados da seção 'pagamentos' onde estão os campos qtTetoAcs
        pagamentos = json_data.get('pagamentos', [])
        resumos = json_data.get('resumosPlanosOrcamentarios', [])
        
        # Encontra registros com dados de ACS - primeiro em pagamentos
        acs_records = []
        for record in pagamentos:
            if 'qtTetoAcs' in record:
                acs_records.append(record)
        
        # Se não encontrou em pagamentos, procura em resumos
        if not acs_records:
            for record in resumos:
                if 'qtTetoAcs' in record:
                    acs_records.append(record)
        
        if not acs_records:
            return []
        
        # Organiza por competência
        timeline = []
        for record in acs_records:
            periodo = ACSDetalhePeriodo(
                competencia=record.get('nuCompCnes', ''),
                parcela=record.get('nuParcela', ''),
                teto=record.get('qtTetoAcs', 0),
                credenciados_direto=record.get('qtAcsDiretoCredenciado', 0),
                credenciados_indireto=record.get('qtAcsIndiretoCredenciado', 0),
                pagos_direto=record.get('qtAcsDiretoPgto', 0),
                pagos_indireto=record.get('qtAcsIndiretoPgto', 0),
                valor_direto=record.get('vlTotalAcsDireto', 0),
                valor_indireto=record.get('vlTotalAcsIndireto', 0),
                valor_total=record.get('vlTotalAcsDireto', 0) + record.get('vlTotalAcsIndireto', 0)
            )
            timeline.append(periodo)
        
        # Ordena por parcela
        timeline.sort(key=lambda x: x.parcela)
        
        return timeline
    
    @staticmethod
    def format_currency(value: float) -> str:
        """Formata valor monetário"""
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """Formata percentual"""
        return f"{value:.1f}%"
    
    @staticmethod
    def get_efficiency_status(efficiency: float) -> tuple:
        """Retorna status da eficiência (cor, ícone, descrição)"""
        if efficiency >= 90:
            return ("🟢", "success", "Excelente")
        elif efficiency >= 75:
            return ("🟡", "warning", "Boa")
        elif efficiency >= 60:
            return ("🟠", "warning", "Regular")
        else:
            return ("🔴", "error", "Crítica")