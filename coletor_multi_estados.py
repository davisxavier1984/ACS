#!/usr/bin/env python3
"""
Coletor de Dados Multi-Estados para ACS
Coleta dados de ACS de todos os municípios de múltiplas UFs para múltiplas competências
Suporta processamento sequencial e paralelo
"""

import argparse
import sys
import re
import logging
import json
import os
import time
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from saude_api import SaudeApi


# Lock global para operações thread-safe
progress_lock = Lock()
stats_lock = Lock()


class ColetorStats:
    """Classe para rastrear estatísticas de coleta"""
    def __init__(self):
        self.total_ufs = 0
        self.ufs_processadas = 0
        self.total_municipios = 0
        self.municipios_processados = 0
        self.total_consultas = 0
        self.sucessos = 0
        self.falhas = 0
        self.inicio = None
        self.stats_por_uf = {}
    
    def add_uf_stats(self, uf: str, municipios: int, competencias: int):
        """Adiciona estatísticas de uma UF"""
        with stats_lock:
            self.stats_por_uf[uf] = {
                'municipios': municipios,
                'competencias': competencias,
                'consultas_totais': municipios * competencias,
                'sucessos': 0,
                'falhas': 0,
                'processado': False
            }
    
    def update_uf_progress(self, uf: str, sucesso: bool):
        """Atualiza progresso de uma UF"""
        with stats_lock:
            if uf in self.stats_por_uf:
                if sucesso:
                    self.stats_por_uf[uf]['sucessos'] += 1
                    self.sucessos += 1
                else:
                    self.stats_por_uf[uf]['falhas'] += 1
                    self.falhas += 1
    
    def marcar_uf_concluida(self, uf: str):
        """Marca UF como concluída"""
        with stats_lock:
            if uf in self.stats_por_uf:
                self.stats_por_uf[uf]['processado'] = True
                self.ufs_processadas += 1
    
    def get_progress_summary(self) -> str:
        """Retorna resumo do progresso"""
        with stats_lock:
            if self.total_consultas == 0:
                return "Iniciando..."
            
            progress_pct = ((self.sucessos + self.falhas) / self.total_consultas) * 100
            tempo_decorrido = time.time() - self.inicio if self.inicio else 0
            
            summary = f"UFs: {self.ufs_processadas}/{self.total_ufs} | "
            summary += f"Consultas: {self.sucessos + self.falhas}/{self.total_consultas} ({progress_pct:.1f}%) | "
            summary += f"Sucessos: {self.sucessos} | Falhas: {self.falhas} | "
            summary += f"Tempo: {tempo_decorrido:.0f}s"
            
            return summary


def validar_ufs(ufs_str: str) -> List[str]:
    """Valida e normaliza lista de UFs ou processa 'ALL'"""
    ufs_validas = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    }
    
    if ufs_str.upper().strip() == 'ALL':
        return sorted(list(ufs_validas))
    
    ufs = [uf.strip().upper() for uf in ufs_str.split(',')]
    ufs_invalidas = [uf for uf in ufs if uf not in ufs_validas]
    
    if ufs_invalidas:
        raise argparse.ArgumentTypeError(
            f"UFs inválidas: {', '.join(ufs_invalidas)}. "
            f"Use: {', '.join(sorted(ufs_validas))} ou 'ALL'"
        )
    
    return sorted(list(set(ufs)))  # Remove duplicatas e ordena


def validar_competencias(competencias_str: str) -> List[str]:
    """Valida e normaliza lista de competências no formato AAAA/MM"""
    competencias = [comp.strip() for comp in competencias_str.split(',')]
    competencias_validas = []
    
    padrao_competencia = re.compile(r'^\d{4}/(0[1-9]|1[0-2])$')
    
    for comp in competencias:
        if not padrao_competencia.match(comp):
            raise argparse.ArgumentTypeError(
                f"Competência '{comp}' inválida. Use formato AAAA/MM (ex: 2024/01)"
            )
        
        ano, mes = comp.split('/')
        ano_int = int(ano)
        if ano_int < 2020 or ano_int > 2025:
            raise argparse.ArgumentTypeError(
                f"Ano {ano_int} fora do intervalo válido (2020-2025)"
            )
        
        competencias_validas.append(comp)
    
    return competencias_validas


def validar_modo(modo_str: str) -> str:
    """Valida modo de processamento"""
    modo = modo_str.lower().strip()
    if modo not in ['sequencial', 'paralelo']:
        raise argparse.ArgumentTypeError(
            f"Modo '{modo_str}' inválido. Use: 'sequencial' ou 'paralelo'"
        )
    return modo


def criar_parser() -> argparse.ArgumentParser:
    """Cria e configura o parser de argumentos de linha de comando"""
    parser = argparse.ArgumentParser(
        prog='coletor_multi_estados.py',
        description='Coletor de Dados Multi-Estados para ACS',
        epilog="""
Exemplos de uso:
  python coletor_multi_estados.py --ufs "PE,SP,BA" --competencias "2025/06,2025/07"
  python coletor_multi_estados.py --ufs "ALL" --competencias "2025/06" --modo paralelo
  python coletor_multi_estados.py --ufs "AC,RR,AP" --competencias "2024/12,2025/01" --max-workers 2
  python coletor_multi_estados.py --ufs "MG" --competencias "2025/06" --modo sequencial
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--ufs', '-u',
        type=validar_ufs,
        required=True,
        help='Lista de UFs separadas por vírgula (ex: "PE,SP,BA") ou "ALL" para todos os estados'
    )
    
    parser.add_argument(
        '--competencias', '-c',
        type=validar_competencias,
        required=True,
        help='Lista de competências no formato "AAAA/MM" separadas por vírgula (ex: "2024/01,2024/02")'
    )
    
    parser.add_argument(
        '--modo', '-m',
        type=validar_modo,
        default='sequencial',
        help='Modo de processamento: "sequencial" (padrão) ou "paralelo"'
    )
    
    parser.add_argument(
        '--max-workers', '-w',
        type=int,
        default=3,
        help='Número máximo de UFs processadas em paralelo (padrão: 3, apenas para modo paralelo)'
    )
    
    parser.add_argument(
        '--output-consolidado', '-o',
        action='store_true',
        help='Gera apenas arquivo consolidado (não salva arquivos individuais por UF)'
    )
    
    return parser


def criar_estrutura_diretorios():
    """Cria estrutura de diretórios necessária"""
    diretorios = ['data', 'logs']
    for diretorio in diretorios:
        if not os.path.exists(diretorio):
            os.makedirs(diretorio)
            print(f"📁 Diretório '{diretorio}' criado")


def processar_uf_individual(uf: str, competencias: List[str], stats: ColetorStats) -> Dict:
    """
    Processa uma UF individual (função para uso em thread)
    
    Args:
        uf: Sigla da UF
        competencias: Lista de competências
        stats: Objeto de estatísticas compartilhado
        
    Returns:
        Dicionário com resultados da UF
    """
    print(f"\n🌟 [{uf}] Iniciando processamento...")
    
    # Buscar municípios da UF
    municipios = SaudeApi.get_municipios_por_uf_sigla(uf)
    
    if not municipios:
        print(f"❌ [{uf}] Nenhum município encontrado")
        return {
            'uf': uf,
            'status': 'erro',
            'erro': 'Nenhum município encontrado',
            'resultados': []
        }
    
    # Adicionar estatísticas da UF
    stats.add_uf_stats(uf, len(municipios), len(competencias))
    
    print(f"✅ [{uf}] {len(municipios)} municípios encontrados")
    
    # Obter código da UF para as requisições
    codigo_uf = None
    for uf_info in SaudeApi.UFS_BRASIL:
        if uf_info['sigla'] == uf:
            codigo_uf = uf_info['codigo']
            break
    
    if not codigo_uf:
        return {
            'uf': uf,
            'status': 'erro',
            'erro': f'Código da UF {uf} não encontrado',
            'resultados': []
        }
    
    resultados = []
    
    for i, municipio in enumerate(municipios, 1):
        codigo_municipio = municipio.get('codigo')
        nome_municipio = municipio.get('nome', 'N/A')
        
        with progress_lock:
            print(f"🏙️  [{uf}] [{i:3d}/{len(municipios)}] {nome_municipio}")
        
        for competencia in competencias:
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
                    stats.update_uf_progress(uf, True)
                    
                    with progress_lock:
                        print(f"      ✅ {competencia}: dados coletados")
                else:
                    # Sem dados
                    stats.update_uf_progress(uf, False)
                    with progress_lock:
                        print(f"      ❌ {competencia}: sem dados")
                    
            except Exception as e:
                stats.update_uf_progress(uf, False)
                with progress_lock:
                    print(f"      💥 {competencia}: erro - {e}")
                logging.error(f"[{uf}] Erro coletando dados para {nome_municipio} - {competencia}: {e}")
        
        # Pausa entre municípios para evitar sobrecarga da API
        time.sleep(0.5)
    
    stats.marcar_uf_concluida(uf)
    print(f"🏁 [{uf}] Processamento concluído!")
    
    return {
        'uf': uf,
        'codigo_uf': codigo_uf,
        'status': 'sucesso',
        'total_municipios': len(municipios),
        'total_competencias': len(competencias),
        'total_resultados': len(resultados),
        'resultados': resultados
    }


def processar_modo_sequencial(ufs: List[str], competencias: List[str], stats: ColetorStats) -> Dict:
    """
    Processa UFs em modo sequencial
    """
    print(f"\n🔄 Modo Sequencial: processando {len(ufs)} UFs...")
    
    resultados_por_uf = {}
    
    for i, uf in enumerate(ufs, 1):
        print(f"\n📊 Progresso Geral: UF {i}/{len(ufs)} ({uf})")
        print(f"📈 {stats.get_progress_summary()}")
        
        resultado_uf = processar_uf_individual(uf, competencias, stats)
        resultados_por_uf[uf] = resultado_uf
        
        # Pausa entre UFs
        if i < len(ufs):
            time.sleep(2)
    
    return resultados_por_uf


def processar_modo_paralelo(ufs: List[str], competencias: List[str], stats: ColetorStats, max_workers: int) -> Dict:
    """
    Processa UFs em modo paralelo
    """
    print(f"\n⚡ Modo Paralelo: processando {len(ufs)} UFs com {max_workers} workers...")
    
    resultados_por_uf = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as UFs para processamento
        future_to_uf = {
            executor.submit(processar_uf_individual, uf, competencias, stats): uf 
            for uf in ufs
        }
        
        # Processar resultados conforme ficam prontos
        for future in as_completed(future_to_uf):
            uf = future_to_uf[future]
            try:
                resultado_uf = future.result()
                resultados_por_uf[uf] = resultado_uf
                
                print(f"\n📊 {stats.get_progress_summary()}")
                
            except Exception as e:
                print(f"❌ Erro ao processar UF {uf}: {e}")
                logging.error(f"Erro ao processar UF {uf}: {e}")
                resultados_por_uf[uf] = {
                    'uf': uf,
                    'status': 'erro',
                    'erro': str(e),
                    'resultados': []
                }
    
    return resultados_por_uf


def salvar_arquivo_consolidado(resultados_por_uf: Dict, ufs: List[str], competencias: List[str]) -> str:
    """
    Salva arquivo consolidado com dados de todas as UFs
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nome_arquivo = f"dados_multi_estados_{timestamp}.json"
    caminho_arquivo = os.path.join("data", nome_arquivo)
    
    # Consolidar todos os resultados
    todos_resultados = []
    stats_finais = {}
    
    for uf, dados_uf in resultados_por_uf.items():
        if dados_uf['status'] == 'sucesso':
            todos_resultados.extend(dados_uf['resultados'])
            stats_finais[uf] = {
                'total_municipios': dados_uf['total_municipios'],
                'total_competencias': dados_uf['total_competencias'],
                'total_resultados': dados_uf['total_resultados'],
                'status': 'sucesso'
            }
        else:
            stats_finais[uf] = {
                'status': 'erro',
                'erro': dados_uf.get('erro', 'Erro desconhecido')
            }
    
    # Preparar dados para salvamento
    dados_arquivo = {
        'metadados': {
            'ufs_processadas': ufs,
            'competencias': competencias,
            'timestamp_coleta': datetime.now().isoformat(),
            'total_resultados': len(todos_resultados),
            'total_ufs': len(ufs),
            'stats_por_uf': stats_finais,
            'resumo': {
                'ufs_com_sucesso': len([uf for uf, dados in stats_finais.items() if dados['status'] == 'sucesso']),
                'ufs_com_erro': len([uf for uf, dados in stats_finais.items() if dados['status'] == 'erro']),
                'total_municipios': sum([dados.get('total_municipios', 0) for dados in stats_finais.values()]),
                'total_consultas_realizadas': len(todos_resultados)
            }
        },
        'resultados': todos_resultados
    }
    
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_arquivo, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Arquivo consolidado salvo: {caminho_arquivo}")
        return caminho_arquivo
        
    except Exception as e:
        logging.error(f"Erro ao salvar arquivo consolidado {caminho_arquivo}: {e}")
        print(f"❌ Erro ao salvar arquivo consolidado: {e}")
        return ""


def salvar_arquivos_individuais(resultados_por_uf: Dict, competencias: List[str]) -> List[str]:
    """
    Salva arquivos individuais por UF (compatibilidade com sistema existente)
    """
    arquivos_salvos = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    for uf, dados_uf in resultados_por_uf.items():
        if dados_uf['status'] == 'sucesso' and dados_uf['resultados']:
            nome_arquivo = f"dados_{uf}_{timestamp}.json"
            caminho_arquivo = os.path.join("data", nome_arquivo)
            
            # Preparar dados no formato individual (compatível com coletor original)
            dados_arquivo = {
                'metadados': {
                    'uf': uf,
                    'timestamp_coleta': datetime.now().isoformat(),
                    'total_resultados': len(dados_uf['resultados']),
                    'competencias': competencias,
                    'municipios': list(set([r['municipio'] for r in dados_uf['resultados']]))
                },
                'resultados': dados_uf['resultados']
            }
            
            try:
                with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                    json.dump(dados_arquivo, f, ensure_ascii=False, indent=2)
                
                arquivos_salvos.append(caminho_arquivo)
                print(f"💾 [{uf}] Arquivo salvo: {nome_arquivo}")
                
            except Exception as e:
                logging.error(f"Erro ao salvar arquivo individual {caminho_arquivo}: {e}")
                print(f"❌ [{uf}] Erro ao salvar arquivo: {e}")
    
    return arquivos_salvos


def main():
    """Função principal do coletor multi-estados"""
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/coletor_multi_estados.log'),
                logging.StreamHandler()
            ]
        )
        
        parser = criar_parser()
        args = parser.parse_args()
        
        print(f"🚀 Coletor Multi-Estados ACS")
        print(f"📍 UFs: {', '.join(args.ufs)} ({len(args.ufs)} estados)")
        print(f"📅 Competências: {', '.join(args.competencias)} ({len(args.competencias)} períodos)")
        print(f"⚙️  Modo: {args.modo}")
        if args.modo == 'paralelo':
            print(f"👥 Workers: {args.max_workers}")
        print(f"📦 Output: {'Apenas consolidado' if args.output_consolidado else 'Consolidado + Individual'}")
        
        # Criar estrutura de diretórios
        criar_estrutura_diretorios()
        
        # Inicializar estatísticas
        stats = ColetorStats()
        stats.total_ufs = len(args.ufs)
        stats.total_consultas = 0  # Será calculado conforme cada UF é processada
        stats.inicio = time.time()
        
        # Processar conforme o modo selecionado
        if args.modo == 'sequencial':
            resultados_por_uf = processar_modo_sequencial(args.ufs, args.competencias, stats)
        else:
            resultados_por_uf = processar_modo_paralelo(args.ufs, args.competencias, stats, args.max_workers)
        
        # Salvar arquivo consolidado
        arquivo_consolidado = salvar_arquivo_consolidado(resultados_por_uf, args.ufs, args.competencias)
        
        # Salvar arquivos individuais (se solicitado)
        arquivos_individuais = []
        if not args.output_consolidado:
            arquivos_individuais = salvar_arquivos_individuais(resultados_por_uf, args.competencias)
        
        # Relatório final
        tempo_total = time.time() - stats.inicio
        print(f"\n🎉 Coleta Multi-Estados Concluída!")
        print(f"⏱️  Tempo total: {tempo_total:.0f}s")
        print(f"📊 {stats.get_progress_summary()}")
        
        if arquivo_consolidado:
            print(f"📦 Arquivo consolidado: {arquivo_consolidado}")
        
        if arquivos_individuais:
            print(f"📁 Arquivos individuais: {len(arquivos_individuais)} arquivos salvos")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logging.exception("Erro detalhado:")
        return 1


if __name__ == "__main__":
    sys.exit(main())