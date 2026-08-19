# =============================================================
# RELABOT v1.0 — step2.py (Step 2: Juntar CSVs e gerenciar retenção)
# =============================================================

import os
import glob
import logging
from datetime import datetime, timedelta

BASE      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR  = os.path.join(BASE, "Base")
TOTAL_DIR = os.path.join(BASE_DIR, "Total")

ARQ_1 = os.path.join(BASE_DIR, "arq_1.csv")   # Religações
ARQ_2 = os.path.join(BASE_DIR, "arq_2.csv")   # Suspensões
ARQ_3 = os.path.join(BASE_DIR, "arq_3.csv")   # Vistorias
ARQ_4 = os.path.join(BASE_DIR, "arq_4.csv")   # Visitas


def limpar_arquivos_antigos(log=None, dias_retencao=7):
    """
    Remove arquivos arq_total_*.csv na pasta Base/Total que tenham mais de 7 dias de criação.
    Exemplo: se um arquivo foi gerado no dia 1, no dia 8 (após 7 dias) ele é apagado.
    """
    if not os.path.exists(TOTAL_DIR):
        return

    hoje = datetime.now().date()
    padrao = os.path.join(TOTAL_DIR, "arq_total_*.csv")
    arquivos = glob.glob(padrao)

    removidos = 0
    for arq in arquivos:
        try:
            # Obtém a data de modificação/criação do arquivo
            mtime = os.path.getmtime(arq)
            data_arq = datetime.fromtimestamp(mtime).date()
            
            dias_idade = (hoje - data_arq).days

            # Se a idade for maior ou igual a 7 dias, apaga o arquivo
            if dias_idade >= dias_retencao:
                os.remove(arq)
                removidos += 1
                msg = f"  [Retenção] Arquivo antigo removido ({dias_idade} dias atrás): {os.path.basename(arq)}"
                if log:
                    log.info(msg)
                else:
                    print(msg)
        except Exception as e:
            msg = f"  Erro ao verificar/remover arquivo {os.path.basename(arq)}: {e}"
            if log:
                log.warning(msg)
            else:
                print(msg)

    if removidos > 0 and log:
        log.info(f"  [Retenção] Total de {removidos} arquivo(s) antigo(s) limpado(s).")


def juntar_csvs(log=None):
    """
    Une arq_1.csv a arq_4.csv da pasta Base/: usa o cabeçalho de arq_1
    e concatena os dados de todos os arquivos.
    Salva como arq_total_[data-hora].csv na pasta Base/Total/.
    Executa a limpeza de retenção para manter no máximo 7 dias de histórico.
    """
    # 1. Garante que a pasta Base/Total exista
    os.makedirs(TOTAL_DIR, exist_ok=True)
    if log:
        log.info("[PROGRESS: 65] Iniciando consolidação e junção dos CSVs...")

    # 2. Executa a limpeza preventiva de arquivos com 7 dias ou mais
    limpar_arquivos_antigos(log=log, dias_retencao=7)

    # 3. Processa a junção dos CSVs
    arqs = [ARQ_1, ARQ_2, ARQ_3, ARQ_4]
    linhas_saida = []
    header_salvo = False

    for arq in arqs:
        if not os.path.exists(arq):
            msg = f"  Arquivo não encontrado: {os.path.basename(arq)}"
            if log:
                log.warning(msg)
            else:
                print(msg)
            continue

        linhas = []
        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try:
                with open(arq, "r", encoding=enc, errors="replace") as f:
                    linhas = f.readlines()
                break
            except Exception:
                linhas = []

        if not linhas:
            msg = f"  {os.path.basename(arq)} está vazio."
            if log:
                log.warning(msg)
            else:
                print(msg)
            continue

        if not header_salvo:
            linhas_saida.append(linhas[0])
            header_salvo = True
            dados = linhas[1:]
        else:
            dados = linhas[1:]

        linhas_saida.extend(dados)
        msg = f"  {os.path.basename(arq)}: {len(dados)} linhas adicionadas."
        if log:
            log.info(msg)
        else:
            print(msg)

    if not linhas_saida:
        msg = "  Nenhum dado encontrado para unir em arq_total."
        if log:
            log.error(msg)
        else:
            print(msg)
        return False

    # 4. Formata o nome do arquivo final com data e hora atual
    agora_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nome_arquivo_total = f"arq_total_{agora_str}.csv"
    caminho_total = os.path.join(TOTAL_DIR, nome_arquivo_total)

    # 5. Salva o CSV unificado em Base/Total/
    with open(caminho_total, "w", encoding="utf-8-sig") as f:
        f.writelines(linhas_saida)

    total_registros = len(linhas_saida) - 1
    msg_sucesso = f"[PROGRESS: 70] {nome_arquivo_total} gerado com sucesso em Base/Total/ — {total_registros} linhas de dados."
    if log:
        log.info(msg_sucesso)
    else:
        print(msg_sucesso)

    return True


# Alias para manter compatibilidade com padronização de s2.py
_juntar_csvs = juntar_csvs


if __name__ == "__main__":
    import sys
    # Teste rápido via terminal
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    logger = logging.getLogger("Step2Test")
    print("Iniciando Step 2...")
    juntar_csvs(logger)
