"""
Teste para gerar PDF no formato Dashboard ACS com dados de ANADIA.
"""

import pandas as pd
import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pdf_generator import gerar_pdf_municipal

def create_test_data():
    """Criar dados de teste baseados nos dados reais de ANADIA."""
    
    # Dados simulados baseados na estrutura encontrada
    df_3_meses = pd.DataFrame([
        {
            'competencia': '2025/05',
            'vlTotalAcs': 133584.0,
            'vlEsperado': 133584.0,
            'qtTotalCredenciado': 50,
            'qtTotalPago': 44
        },
        {
            'competencia': '2025/06',
            'vlTotalAcs': 133584.0,
            'vlEsperado': 133584.0,
            'qtTotalCredenciado': 44,
            'qtTotalPago': 44
        },
        {
            'competencia': '2025/07',
            'vlTotalAcs': 126026.0,
            'vlEsperado': 133584.0,
            'qtTotalCredenciado': 42,
            'qtTotalPago': 42
        }
    ])
    
    # Dados atuais (último período)
    dados_atual = df_3_meses.iloc[-1]
    
    competencias = ['2025/05', '2025/06', '2025/07']
    
    return df_3_meses, dados_atual, competencias

def test_dashboard_pdf():
    """Testar geração do PDF no formato Dashboard ACS."""
    
    print("Gerando dados de teste para ANADIA...")
    df_3_meses, dados_atual, competencias = create_test_data()
    
    print("Gerando PDF Dashboard ACS...")
    try:
        pdf_buffer = gerar_pdf_municipal(
            municipio="ANADIA",
            uf="AL",
            df_3_meses=df_3_meses,
            dados_atual=dados_atual,
            competencias=competencias
        )
        
        # Salvar o PDF
        with open("test_dashboard_anadia.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        
        print("PDF gerado com sucesso: test_dashboard_anadia.pdf")
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard_pdf()