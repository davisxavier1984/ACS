#!/usr/bin/env python3
"""
Coletor de Dados Estadual Multi-Competência para ACS
Coleta dados de ACS de todos os municípios de uma UF para múltiplas competências
"""

import argparse
import sys
import re
import logging
import json
import os
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from saude_api import SaudeApi


def validar_uf(uf: str) -> str:
    """Valida e normaliza código da UF"""
    ufs_validas = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    }
    
    uf_upper = uf.upper().strip()
    if uf_upper not in ufs_validas:
        raise argparse.ArgumentTypeError(
            f"UF '{uf}' inválida. Use: {', '.join(sorted(ufs_validas))}"
        )
    return uf_upper


def validar_competencias(competencias_str: str) -> List[str]:
    """Valida e normaliza lista de competências no formato AAAA/MM"""
    competencias = [comp.strip() for comp in competencias_str.split(',')]
    competencias_validas = []

    padrao_competencia = re.compile(r'^\d{4}/(0[1-9]|1[0-2])$')
    ano_atual = datetime.now().year

    for comp in competencias:
        if not padrao_competencia.match(comp):
            raise argparse.ArgumentTypeError(
                f"Competência '{comp}' inválida. Use formato AAAA/MM (ex: 2024/01)"
            )

        ano, mes = comp.split('/')
        ano_int = int(ano)
        if ano_int < 2020 or ano_int > ano_atual:
            raise argparse.ArgumentTypeError(
                f"Ano {ano_int} fora do intervalo válido (2020-{ano_atual})"
            )

        competencias_validas.append(comp)

    return competencias_validas


def criar_parser() -> argparse.ArgumentParser:
    """Cria e configura o parser de argumentos de linha de comando"""
    parser = argparse.ArgumentParser(
        prog='coletor_dados.py',
        description='Coletor de Dados Estadual Multi-Competência para ACS',
        epilog="""
Exemplos de uso:
  python coletor_dados.py --uf PE --competencias "2024/01,2024/02,2024/03"
  python coletor_dados.py -u SP -c "2025/06"
  python coletor_dados.py --uf AC --competencias "2024/12,2025/01,2025/02"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--uf', '-u',
        type=validar_uf,
        required=True,
        help='Código da UF (ex: PE, SP, AC). Use --help para lista completa.'
    )
    
    parser.add_argument(
        '--competencias', '-c',
        type=validar_competencias,
        required=True,
        help='Lista de competências no formato "AAAA/MM" separadas por vírgula (ex: "2024/01,2024/02,2024/03")'
    )
    
    return parser


def criar_estrutura_diretorios():
    """Cria estrutura de diretórios necessária"""
    diretorios = ['data', 'logs']
    for diretorio in diretorios:
        if not os.path.exists(diretorio):
            os.makedirs(diretorio)
            print(f"📁 Diretório '{diretorio}' criado")


def processar_coleta_dados(uf: str, municipios: List[Dict], competencias: List[str]) -> List[Dict]:
    """
    Processa a coleta de dados para todos os municípios e competências
    
    Args:
        uf: Sigla da UF
        municipios: Lista de municípios da UF
        competencias: Lista de competências a processar
        
    Returns:
        Lista de resultados coletados
    """
    resultados = []
    total_municipios = len(municipios)
    total_combinacoes = total_municipios * len(competencias)
    
    print(f"\n🚀 Iniciando coleta de dados:")
    print(f"   📊 {total_municipios} municípios")
    print(f"   📅 {len(competencias)} competências")
    print(f"   🔢 {total_combinacoes} consultas totais")
    
    # Obter código da UF para as requisições
    codigo_uf = None
    for uf_info in SaudeApi.UFS_BRASIL:
        if uf_info['sigla'] == uf:
            codigo_uf = uf_info['codigo']
            break
    
    if not codigo_uf:
        logging.error(f"Código da UF {uf} não encontrado")
        return []
    
    contador_processados = 0
    sucessos = 0
    falhas = 0
    
    for i, municipio in enumerate(municipios, 1):
        codigo_municipio = municipio.get('codigo')
        nome_municipio = municipio.get('nome', 'N/A')
        
        print(f"\n🏙️  [{i:3d}/{total_municipios}] Processando: {nome_municipio}")
        
        for competencia in competencias:
            contador_processados += 1
            
            try:
                # Coletar dados de pagamento
                dados = SaudeApi.get_dados_pagamento(codigo_uf, codigo_municipio, competencia)
                
                if dados is not None:
                    # Dados coletados com sucesso
                    resultado = {
                        'uf': uf,
                        'codigo_uf': codigo_uf,
                        'municipio': nome_municipio,
                        'codigo_municipio': codigo_municipio,
                        'competencia': competencia,
                        'timestamp_coleta': datetime.now().isoformat(),
                        'status': 'sucesso',
                        'dados': dados
                    }
                    resultados.append(resultado)
                    sucessos += 1
                    print(f"      ✅ {competencia}: dados coletados")
                else:
                    # Sem dados ou erro
                    falhas += 1
                    print(f"      ❌ {competencia}: sem dados")
                    logging.warning(f"Sem dados para {nome_municipio} - {competencia}")
                    
            except Exception as e:
                falhas += 1
                print(f"      💥 {competencia}: erro - {e}")
                logging.error(f"Erro coletando dados para {nome_municipio} - {competencia}: {e}")
        
        # Feedback de progresso a cada 10 municípios
        if i % 10 == 0:
            print(f"\n📈 Progresso: {i}/{total_municipios} municípios processados")
            print(f"   ✅ Sucessos: {sucessos}")
            print(f"   ❌ Falhas: {falhas}")
            print(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+falhas)*100):.1f}%" if (sucessos+falhas) > 0 else "0%")
    
    print(f"\n🏁 Coleta finalizada:")
    print(f"   📊 {contador_processados} consultas realizadas")
    print(f"   ✅ {sucessos} sucessos")
    print(f"   ❌ {falhas} falhas")
    print(f"   📈 Taxa de sucesso: {(sucessos/(sucessos+falhas)*100):.1f}%" if (sucessos+falhas) > 0 else "0%")
    
    return resultados


def salvar_resultados(resultados: List[Dict], uf: str) -> str:
    """
    Salva os resultados em arquivo JSON
    
    Args:
        resultados: Lista de resultados coletados
        uf: Sigla da UF
        
    Returns:
        Caminho do arquivo salvo
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nome_arquivo = f"dados_{uf}_{timestamp}.json"
    caminho_arquivo = os.path.join("data", nome_arquivo)
    
    # Preparar dados para salvamento
    dados_arquivo = {
        'metadados': {
            'uf': uf,
            'timestamp_coleta': datetime.now().isoformat(),
            'total_resultados': len(resultados),
            'competencias': list(set([r['competencia'] for r in resultados])),
            'municipios': list(set([r['municipio'] for r in resultados]))
        },
        'resultados': resultados
    }
    
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_arquivo, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Dados salvos em: {caminho_arquivo}")
        return caminho_arquivo
        
    except Exception as e:
        logging.error(f"Erro ao salvar arquivo {caminho_arquivo}: {e}")
        print(f"❌ Erro ao salvar dados: {e}")
        return ""


def main():
    """Função principal do coletor de dados"""
    try:
        # Configurar logging básico
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        parser = criar_parser()
        args = parser.parse_args()
        
        print(f"🚀 Iniciando coleta de dados para UF: {args.uf}")
        print(f"📅 Competências: {', '.join(args.competencias)}")
        print(f"📊 Total de competências a processar: {len(args.competencias)}")
        
        # Buscar municípios da UF
        print(f"\n🔍 Buscando municípios da UF {args.uf}...")
        municipios = SaudeApi.get_municipios_por_uf_sigla(args.uf)
        
        if not municipios:
            print(f"❌ Nenhum município encontrado para a UF {args.uf}")
            return 1
        
        print(f"✅ Encontrados {len(municipios)} municípios para a UF {args.uf}")
        
        # Exibir alguns exemplos de municípios (primeiros 3)
        print(f"📋 Primeiros municípios: {', '.join([m.get('nome', 'N/A') for m in municipios[:3]])}...")
        
        # Criar estrutura de diretórios
        criar_estrutura_diretorios()
        
        # Processar coleta de dados
        resultados = processar_coleta_dados(args.uf, municipios, args.competencias)
        
        if not resultados:
            print("❌ Nenhum dado foi coletado")
            return 1
        
        # Salvar resultados
        arquivo_salvo = salvar_resultados(resultados, args.uf)
        
        if arquivo_salvo:
            print(f"\n🎉 Coleta concluída! Dados salvos em '{arquivo_salvo}'")
            return 0
        else:
            print("❌ Erro ao salvar dados")
            return 1
        
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logging.exception("Erro detalhado:")
        return 1


if __name__ == "__main__":
    sys.exit(main())