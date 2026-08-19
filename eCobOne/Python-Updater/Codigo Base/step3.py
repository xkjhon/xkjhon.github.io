# =============================================================
# RELABOT v1.0 — step3.py (Step 3: Contagem e Geração da Database)
# =============================================================

import os
import glob
import logging
from datetime import datetime, timedelta
import pandas as pd

BASE         = os.path.dirname(os.path.abspath(__file__))
BASE_DIR     = os.path.join(BASE, "Base")
TOTAL_DIR    = os.path.join(BASE_DIR, "Total")
DATABASE_DIR = os.path.join(BASE_DIR, "Database")

# Mapeamento de Agências para Regiões conforme Passo 1 do step-by-step.md
MAPA_AGENCIA_REGIAO = {
    "04.CSC ANÁPOLIS":     "ANAPOLIS",
    "05.CSC JARAGUÁ":      "ANAPOLIS",
    "06.CSC ÁGUAS LINDAS": "LUZIANIA",
    "07.CSC LUZIÂNIA":     "LUZIANIA",
    "08.CSC CAMPOS BELOS": "FORMOSA",
    "09.CSC FORMOSA":      "FORMOSA",
    "10.CSC PORANGATU":    "URUACU",
    "11.CSC URUAÇU":       "URUACU",
    "16.CSC QUIRINÓPOLIS": "RIO VERDE",
    "17.CSC RIO VERDE":    "RIO VERDE",
    "18.CSC  MORRINHOS":   "MORRINHOS",
    "18.CSC MORRINHOS":    "MORRINHOS",
    "19.CSC CATALÃO":      "MORRINHOS",
}


def _limpar_nome_colaborador(nome):
    """
    Remove prefixos como 'MEIRELES - MEIRELES - ' do nome do colaborador.
    Retorna a string em caixa alta e sem espaços extras.
    """
    if pd.isna(nome):
        return ""
    nome_str = str(nome).strip()
    if " - " in nome_str:
        nome_str = nome_str.rsplit("-", 1)[-1]
    return nome_str.strip().upper()


def _mapear_regiao(agencia):
    """Mapeia o nome da agência para a sua respectiva região."""
    if pd.isna(agencia):
        return "DESCONHECIDO"
    ag_str = str(agencia).strip()
    
    if ag_str in MAPA_AGENCIA_REGIAO:
        return MAPA_AGENCIA_REGIAO[ag_str]
    
    # Busca por correspondência parcial (insensível a maiúsculas/minúsculas)
    ag_upper = ag_str.upper()
    for chave, regiao in MAPA_AGENCIA_REGIAO.items():
        if chave.upper() in ag_upper:
            return regiao
            
    return "DESCONHECIDO"


def _normalizar_etapa(etapa):
    """
    Normaliza o nome da etapa para padronizar variações com/sem acento
    (ex: NAO EXECUTADO e NÃO EXECUTADO) garantindo a contagem correta em quant2.txt.
    """
    if pd.isna(etapa):
        return ""
    et_str = str(etapa).strip().upper()
    if "NAO EXECUTADO" in et_str or "NÃO EXECUTADO" in et_str:
        return "NÃO EXECUTADO"
    if "EM CAMPO" in et_str:
        return "EM CAMPO"
    if "EXECUTADO" in et_str:
        return "EXECUTADO"
    if "PENDENTE" in et_str:
        return "PENDENTE"
    return et_str


def encontrar_arquivo_total():
    """
    Encontra o arquivo CSV consolidado mais recente na pasta Base/Total/.
    Caso não exista, busca na pasta Base/.
    """
    if os.path.exists(TOTAL_DIR):
        padrao = os.path.join(TOTAL_DIR, "arq_total_*.csv")
        arquivos = glob.glob(padrao)
        if arquivos:
            # Ordena pelo horário de modificação (mais recente primeiro)
            arquivos.sort(key=os.path.getmtime, reverse=True)
            return arquivos[0]

    # Fallback: procura qualquer CSV unificado em Base/
    for arq in ["arq_total.csv", "arq_1.csv"]:
        caminho = os.path.join(BASE_DIR, arq)
        if os.path.exists(caminho):
            return caminho
            
    return None


def processar_contagem(log=None, caminho_csv=None):
    """
    Executa o Step 3:
    1. Lê o arquivo consolidado de CSVs (arq_total).
    2. Identifica os colaboradores únicos, limpa o nome e detecta a Região.
    3. Gera /Base/Database/colab.txt: [ID],[NOME DO COLABORADOR],[REGIÃO]
    4. Aplica os filtros:
       - Remove o colaborador 'BERENICE RIBEIRO DE SOUZA'
       - Remove linhas com 'VISITA DE LEITURA' na coluna nomeServico
       - Remove linhas com 'DESALOCADO' e 'NÃO ALOCADO' na coluna Etapa
       - Elimina na Coluna Y (Data despacho) todas as linhas com a data de ontem, mantendo a data de hoje.
    5. Gera /Base/Database/quant1.txt (e quant.txt): [ID],[ETAPA],[SS]
    6. Gera /Base/Database/quant2.txt: [ID],[EM CAMPO],[EXECUTADO],[NÃO EXECUTADO],[PENDENTE]
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)

    # 1. Localiza o arquivo CSV de entrada
    if not caminho_csv:
        caminho_csv = encontrar_arquivo_total()

    if not caminho_csv or not os.path.exists(caminho_csv):
        msg = "  ❌ Nenhum arquivo consolidado (arq_total) encontrado para processamento no Step 3."
        if log:
            log.error(msg)
        else:
            print(msg)
        return False

    nome_arq_entrada = os.path.basename(caminho_csv)
    msg_inicio = f"[PROGRESS: 75] Lendo e processando dados do arquivo: {nome_arq_entrada}"
    if log:
        log.info(msg_inicio)
    else:
        print(msg_inicio)

    # 2. Carrega o CSV usando pandas
    df = None
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            df = pd.read_csv(caminho_csv, sep=";", encoding=enc, dtype=str, on_bad_lines="skip")
            break
        except Exception:
            try:
                df = pd.read_csv(caminho_csv, sep=",", encoding=enc, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                continue

    if df is None or df.empty:
        msg = f"  ❌ Falha ao carregar o arquivo CSV: {nome_arq_entrada}"
        if log:
            log.error(msg)
        else:
            print(msg)
        return False

    # Garante que os nomes das colunas não tenham espaços extras
    df.columns = df.columns.str.strip()

    # Valida presença das colunas essenciais
    colunas_obrigatorias = ["Equipe", "Agencia", "nomeServico", "Etapa", "SS"]
    faltantes = [c for c in colunas_obrigatorias if c not in df.columns]
    if faltantes:
        msg = f"  ❌ Colunas obrigatórias não encontradas no CSV: {', '.join(faltantes)}"
        if log:
            log.error(msg)
        else:
            print(msg)
        return False

    # Criar coluna limpa 'Nome_Limpo' e 'Etapa_Norm'
    df["Nome_Limpo"]  = df["Equipe"].apply(_limpar_nome_colaborador)
    df["Regiao"]      = df["Agencia"].apply(_mapear_regiao)
    df["Etapa_Norm"]  = df["Etapa"].apply(_normalizar_etapa)

    # Passo 2: Mapear colaboradores únicos e atribuir ID sequencial (1, 2, 3, ...)
    df_colabs = df[~df["Nome_Limpo"].str.contains("BERENICE RIBEIRO DE SOUZA", na=False)].copy()
    
    colabs_unicos = df_colabs["Nome_Limpo"].unique()
    colabs_unicos = [n for n in colabs_unicos if n]  # Remove vazios
    colabs_unicos.sort()

    mapa_colab_id = {}
    linhas_colab = []

    for idx, nome in enumerate(colabs_unicos, start=1):
        mapa_colab_id[nome] = idx
        # Identifica a região mais frequente deste colaborador
        sub_df = df_colabs[df_colabs["Nome_Limpo"] == nome]
        regiao = sub_df["Regiao"].mode()[0] if not sub_df["Regiao"].empty else "DESCONHECIDO"
        linhas_colab.append(f"{idx},{nome},{regiao}")

    # Salva /Base/Database/colab.txt
    caminho_colab = os.path.join(DATABASE_DIR, "colab.txt")
    with open(caminho_colab, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_colab) + ("\n" if linhas_colab else ""))

    msg_colab = f"  ✓ colab.txt gerado com {len(linhas_colab)} colaboradores cadastrados."
    if log:
        log.info(msg_colab)
    else:
        print(msg_colab)

    # Passo 3: Aplicar Filtros de Exclusão
    # - Excluir Berenice Ribeiro de Souza
    # - Excluir 'VISITA DE LEITURA' na coluna nomeServico
    # - Excluir 'DESALOCADO' e 'NÃO ALOCADO' / 'NAO ALOCADO' na coluna Etapa
    # - Eliminar linhas com a data de ontem na Coluna Y (Data despacho)
    cond_colab  = ~df["Nome_Limpo"].str.contains("BERENICE RIBEIRO DE SOUZA", na=False)
    cond_serv   = ~df["nomeServico"].astype(str).str.upper().str.contains("VISITA DE LEITURA", na=False)
    cond_etapa  = ~df["Etapa_Norm"].isin(["DESALOCADO", "NÃO ALOCADO", "NAO ALOCADO"])

    # Filtro da Coluna Y (Data despacho)
    hoje_dt = datetime.now()
    data_hoje_str = hoje_dt.strftime("%d/%m/%Y")
    
    col_despacho_nome = None
    for c in df.columns:
        if "despacho" in c.lower():
            col_despacho_nome = c
            break

    if col_despacho_nome:
        data_despacho_str = df[col_despacho_nome].astype(str).str.split(" ").str[0].str.strip()
        cond_y = data_despacho_str.str.startswith(data_hoje_str, na=False)
    else:
        cond_y = True

    df_filtrado = df[cond_colab & cond_serv & cond_etapa & cond_y].copy()

    # Associa o ID do colaborador
    df_filtrado["ID"] = df_filtrado["Nome_Limpo"].map(mapa_colab_id)
    df_filtrado = df_filtrado.dropna(subset=["ID"]).copy()
    df_filtrado["ID"] = df_filtrado["ID"].astype(int)

    # Preencher quant1.txt (e quant.txt) -> [ID],[ETAPA],[SS]
    linhas_quant1 = []
    for _, row in df_filtrado.iterrows():
        id_colab = row["ID"]
        etapa    = str(row["Etapa_Norm"]).strip()
        ss       = str(row["SS"]).strip()
        linhas_quant1.append(f"{id_colab},{etapa},{ss}")

    caminho_quant1 = os.path.join(DATABASE_DIR, "quant1.txt")
    caminho_quant  = os.path.join(DATABASE_DIR, "quant.txt")

    conteudo_quant1 = "\n".join(linhas_quant1) + ("\n" if linhas_quant1 else "")
    with open(caminho_quant1, "w", encoding="utf-8") as f:
        f.write(conteudo_quant1)
    with open(caminho_quant, "w", encoding="utf-8") as f:
        f.write(conteudo_quant1)

    msg_quant1 = f"  ✓ quant1.txt gerado com {len(linhas_quant1)} registros de serviços (filtrados para a data de hoje)."
    if log:
        log.info(msg_quant1)
    else:
        print(msg_quant1)

    # Preencher quant2.txt -> [ID],[EM CAMPO],[EXECUTADO],[NÃO EXECUTADO],[PENDENTE]
    # Coluna A: ID
    # Coluna B: EM CAMPO
    # Coluna C: EXECUTADO
    # Coluna D: NÃO EXECUTADO
    # Coluna E: PENDENTE
    etapas_alvo = ["EM CAMPO", "EXECUTADO", "NÃO EXECUTADO", "PENDENTE"]
    linhas_quant2 = []

    # Agrupa por ID e Etapa_Norm
    contagem_etapas = df_filtrado.groupby(["ID", "Etapa_Norm"]).size().unstack(fill_value=0)

    for idx in sorted(mapa_colab_id.values()):
        counts = []
        for et in etapas_alvo:
            if idx in contagem_etapas.index and et in contagem_etapas.columns:
                counts.append(str(contagem_etapas.loc[idx, et]))
            else:
                counts.append("0")
        
        str_counts = ",".join(counts)
        linhas_quant2.append(f"{idx},{str_counts}")

    caminho_quant2 = os.path.join(DATABASE_DIR, "quant2.txt")
    with open(caminho_quant2, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_quant2) + ("\n" if linhas_quant2 else ""))

    # Garante a existência do arquivo bc.txt para manter integridade da base
    caminho_bc = os.path.join(DATABASE_DIR, "bc.txt")
    if not os.path.exists(caminho_bc):
        open(caminho_bc, "w", encoding="utf-8").close()

    msg_quant2 = f"  ✓ quant2.txt gerado com contagens de etapas para {len(linhas_quant2)} colaboradores."
    if log:
        log.info(msg_quant2)
    else:
        print(msg_quant2)

    msg_sucesso = f"[PROGRESS: 85] Step 3 finalizado com SUCESSO! Banco de dados atualizado em: {DATABASE_DIR}"
    if log:
        log.info(msg_sucesso)
    else:
        print(msg_sucesso)

    return True


# Alias para padronização
_processar_contagem = processar_contagem


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    logger = logging.getLogger("Step3Test")
    print("Iniciando Step 3...")
    processar_contagem(logger)
