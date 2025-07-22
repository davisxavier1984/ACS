"""
Configuração Específica para Relatórios PDF de ANADIA/AL

Este módulo contém configurações personalizadas para gerar relatórios PDF 
no formato específico do município de ANADIA - Alagoas, baseado no arquivo
de referência Relatorio_ACS_ANADIA_20250721_165816.pdf
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color
from pdf_config import PDFConfig, ChartConfig


@dataclass
class AndiaPDFConfig(PDFConfig):
    """Configuração específica para relatórios de ANADIA."""
    
    # Informações específicas do município
    municipio_nome: str = "ANADIA"
    municipio_codigo_ibge: str = "270020"
    uf: str = "AL"
    uf_nome: str = "ALAGOAS"
    
    # Cores institucionais customizadas
    primary_color: str = '#2E7D32'  # Verde escuro para ACS
    secondary_color: str = '#4CAF50'  # Verde médio
    accent_color: str = '#81C784'   # Verde claro
    header_bg_color: tuple = (0.18, 0.49, 0.20)  # Verde escuro RGB
    
    # Layout personalizado
    title_font_size: int = 18
    header_font_size: int = 16
    municipality_font_size: int = 14
    
    # Margens ajustadas para o formato ANADIA
    margin: float = 45
    header_height: float = 120  # Espaço maior para informações municipais
    footer_height: float = 60
    
    # Configurações de texto específicas
    report_title: str = "RELATÓRIO MUNICIPAL ACS"
    system_name: str = "Sistema de Acompanhamento de Agentes Comunitários de Saúde"
    
    # Valor de repasse padrão ACS (conforme especificado no sistema)
    valor_repasse_acs: float = 3036.00
    
    # Configurações de formatação monetária brasileira
    currency_symbol: str = "R$"
    thousand_separator: str = "."
    decimal_separator: str = ","
    
    @property
    def header_title_complete(self) -> str:
        """Título completo do cabeçalho."""
        return f"{self.report_title} - {self.municipio_nome} - {self.uf}"
    
    @property
    def municipality_info(self) -> Dict[str, str]:
        """Informações detalhadas do município."""
        return {
            "nome": self.municipio_nome,
            "codigo_ibge": self.municipio_codigo_ibge,
            "uf": self.uf,
            "uf_nome": self.uf_nome,
            "regiao": "NORDESTE"
        }


@dataclass 
class AnadiaChartConfig(ChartConfig):
    """Configuração específica para gráficos de ANADIA."""
    
    # Cores padronizadas para gráficos
    financial_colors: Dict[str, str] = field(default_factory=lambda: {
        'esperado': '#2E7D32',      # Verde escuro
        'recebido': '#4CAF50',      # Verde médio
        'diferenca': '#FF5722'      # Vermelho para perdas
    })
    
    personnel_colors: Dict[str, str] = field(default_factory=lambda: {
        'credenciados': '#81C784',  # Verde claro
        'pagos': '#388E3C',         # Verde intenso
        'pendentes': '#FFC107'      # Amarelo para pendências
    })
    
    # Configurações específicas para ANADIA
    background_color: str = 'white'
    grid_color: str = '#E0E0E0'
    text_color: str = '#2E2E2E'
    
    # Dimensões otimizadas para o formato ANADIA
    width: int = 750
    height: int = 400
    dpi: int = 150
    
    @classmethod
    def for_financial_analysis(cls) -> 'AnadiaChartConfig':
        """Configuração para gráficos de análise financeira."""
        return cls(
            width=750,
            height=350,
            title_font_size=16,
            font_size=12
        )
    
    @classmethod
    def for_personnel_analysis(cls) -> 'AnadiaChartConfig':
        """Configuração para gráficos de análise de pessoal."""
        return cls(
            width=750,
            height=320,
            title_font_size=16,
            font_size=12
        )


class AnadiaDataValidator:
    """Validador específico para dados de ANADIA."""
    
    def __init__(self, config: AndiaPDFConfig):
        self.config = config
    
    def validate_municipality_data(self, municipio: str, uf: str, 
                                 codigo_municipio: str = None) -> bool:
        """
        Valida se os dados pertencem a ANADIA/AL.
        
        Args:
            municipio: Nome do município
            uf: Sigla do estado
            codigo_municipio: Código IBGE do município
            
        Returns:
            True se os dados são válidos para ANADIA
        """
        # Verificar município
        municipio_normalizado = municipio.upper().strip()
        if municipio_normalizado not in ["ANADIA", "ANADIA/AL"]:
            return False
        
        # Verificar UF
        if uf.upper().strip() != "AL":
            return False
        
        # Verificar código IBGE se fornecido
        if codigo_municipio and codigo_municipio != self.config.municipio_codigo_ibge:
            return False
        
        return True
    
    def validate_competencia_format(self, competencia: str) -> bool:
        """
        Valida formato da competência (AAAA/MM).
        
        Args:
            competencia: String da competência
            
        Returns:
            True se formato é válido
        """
        try:
            if len(competencia) != 7 or competencia[4] != '/':
                return False
            
            ano = int(competencia[:4])
            mes = int(competencia[5:7])
            
            return 2020 <= ano <= 2030 and 1 <= mes <= 12
        except (ValueError, IndexError):
            return False
    
    def validate_financial_data(self, dados: Dict[str, Any]) -> List[str]:
        """
        Valida dados financeiros para ANADIA.
        
        Args:
            dados: Dicionário com dados financeiros
            
        Returns:
            Lista de erros encontrados (vazia se válido)
        """
        erros = []
        
        # Campos obrigatórios
        campos_obrigatorios = [
            'vlEsperado', 'vlTotalAcs', 'qtTotalCredenciado', 
            'qtTotalPago', 'competencia'
        ]
        
        for campo in campos_obrigatorios:
            if campo not in dados or dados[campo] is None:
                erros.append(f"Campo obrigatório ausente: {campo}")
        
        # Validar valores numéricos
        if 'vlEsperado' in dados and dados['vlEsperado'] < 0:
            erros.append("Valor esperado não pode ser negativo")
        
        if 'vlTotalAcs' in dados and dados['vlTotalAcs'] < 0:
            erros.append("Valor total ACS não pode ser negativo")
        
        if 'qtTotalCredenciado' in dados and dados['qtTotalCredenciado'] < 0:
            erros.append("Quantidade de ACS credenciados não pode ser negativa")
        
        if 'qtTotalPago' in dados and dados['qtTotalPago'] < 0:
            erros.append("Quantidade de ACS pagos não pode ser negativa")
        
        # Validar coerência dos dados
        if ('qtTotalCredenciado' in dados and 'qtTotalPago' in dados and
            dados['qtTotalPago'] > dados['qtTotalCredenciado']):
            erros.append("ACS pagos não pode ser maior que ACS credenciados")
        
        return erros


def format_currency_brazilian(valor: float, config: AndiaPDFConfig = None) -> str:
    """
    Formata valor monetário no padrão brasileiro específico para ANADIA.
    
    Args:
        valor: Valor a ser formatado
        config: Configuração específica (opcional)
        
    Returns:
        String formatada no padrão brasileiro
    """
    if config is None:
        config = AndiaPDFConfig()
    
    if valor is None:
        return f"{config.currency_symbol} 0{config.decimal_separator}00"
    
    # Formatação baseada no tamanho do valor
    if valor >= 1_000_000:
        # Milhões
        valor_mi = valor / 1_000_000
        return f"{config.currency_symbol} {valor_mi:.1f}Mi".replace('.', config.decimal_separator)
    elif valor >= 1_000:
        # Milhares
        valor_mil = valor / 1_000
        if valor_mil >= 100:
            return f"{config.currency_symbol} {valor_mil:.0f}Mil"
        else:
            return f"{config.currency_symbol} {valor_mil:.1f}Mil".replace('.', config.decimal_separator)
    else:
        # Valores menores que 1000
        valor_formatado = f"{valor:,.2f}"
        partes = valor_formatado.split('.')
        parte_inteira = partes[0].replace(',', config.thousand_separator)
        parte_decimal = partes[1] if len(partes) > 1 else "00"
        return f"{config.currency_symbol} {parte_inteira}{config.decimal_separator}{parte_decimal}"


def calculate_acs_expected_value(quantidade_acs: int, config: AndiaPDFConfig = None) -> float:
    """
    Calcula valor esperado baseado na quantidade de ACS e valor de repasse.
    
    Args:
        quantidade_acs: Número de ACS
        config: Configuração específica (opcional)
        
    Returns:
        Valor esperado calculado
    """
    if config is None:
        config = AndiaPDFConfig()
    
    return quantidade_acs * config.valor_repasse_acs


def get_anadia_default_config() -> AndiaPDFConfig:
    """
    Retorna configuração padrão para ANADIA.
    
    Returns:
        Instância configurada para ANADIA
    """
    return AndiaPDFConfig()


def get_anadia_chart_config() -> AnadiaChartConfig:
    """
    Retorna configuração de gráficos padrão para ANADIA.
    
    Returns:
        Instância de configuração de gráficos para ANADIA
    """
    return AnadiaChartConfig()