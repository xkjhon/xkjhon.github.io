# =============================================================
# eCobOne — updater.py (Módulo Principal de Atualização)
# =============================================================

import os
import sys
import time
import glob
import shutil
import base64
import hashlib
import getpass
import logging
from datetime import datetime, timedelta

# Define caminhos do projeto
BASE         = os.path.dirname(os.path.abspath(__file__))
FILES_DIR    = os.path.join(BASE, "Files")
CACHE_DIR    = os.path.join(FILES_DIR, "Cache")
TOTAL_DIR    = os.path.join(CACHE_DIR, "Total")
DOWNLOAD_TEMP = os.path.join(CACHE_DIR, "_download_temp")
LOGIN_FILE   = os.path.join(BASE, "login.dat")

# URLs do portal SIGS
LOGIN_URL     = "http://sigsreliga.equatorialenergia.com.br:3030/Meireles/Login/Index?ReturnUrl=%2fMeireles%2fAcompanhamento%2fTodosServicos"
RELATORIO_URL = "http://sigsreliga.equatorialenergia.com.br:3030/Meireles/Relatorio/ExportacaoSS"

# Lista de serviços para o Selenium baixar
SERVICOS = [
    {
        "nome": "Religações",
        "xpath": '//*[@id="ctl00_ConteudoPaginas_ASPxComboBox4_DDD_L_LBI0T0"]',
        "arquivo_destino": "arq_1.csv",
    },
    {
        "nome": "Suspensões",
        "xpath": '//*[@id="ctl00_ConteudoPaginas_ASPxComboBox4_DDD_L_LBI1T0"]',
        "arquivo_destino": "arq_2.csv",
    },
    {
        "nome": "Vistorias",
        "xpath": '//*[@id="ctl00_ConteudoPaginas_ASPxComboBox4_DDD_L_LBI2T0"]',
        "arquivo_destino": "arq_3.csv",
    },
    {
        "nome": "Visitas",
        "xpath": '//*[@id="ctl00_ConteudoPaginas_ASPxComboBox4_DDD_L_LBI4T0"]',
        "arquivo_destino": "arq_4.csv",
    },
]


class CredencialInvalidaError(Exception):
    pass


# -------------------------------------------------------------
# Criptografia e Gerenciamento de Credenciais
# -------------------------------------------------------------
def _gerar_chave_secreta():
    """Gera uma chave única derivada do usuário do SO para criptografia local."""
    usuario_so = os.environ.get("USERNAME", "ecob_user")
    raw_key = f"eCobOne_Secured_Key_{usuario_so}".encode("utf-8")
    return hashlib.sha256(raw_key).digest()


def criptografar_dados(texto: str) -> str:
    """Criptografa uma string usando XOR + Base64."""
    key = _gerar_chave_secreta()
    data = texto.encode("utf-8")
    encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    return "ENC:" + base64.b64encode(encrypted).decode("utf-8")


def descriptografar_dados(texto_enc: str) -> str:
    """Descriptografa uma string salva no login.dat."""
    texto_enc = texto_enc.strip()
    if not texto_enc.startswith("ENC:"):
        # Suporta leitura se estivesse em texto puro anteriormente
        return texto_enc
    raw_b64 = texto_enc[4:]
    encrypted_bytes = base64.b64decode(raw_b64)
    key = _gerar_chave_secreta()
    decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted_bytes)])
    return decrypted.decode("utf-8", errors="ignore")


def obter_credenciais(interactive: bool = True, log: logging.Logger = None):
    """
    Obtém as credenciais do login.dat.
    Se o arquivo estiver vazio ou não existir:
      - Solicita usuário e senha interativamente.
      - Pergunta se deseja salvar criptografado no login.dat.
    """
    usuario = ""
    senha = ""

    if os.path.exists(LOGIN_FILE):
        try:
            with open(LOGIN_FILE, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if conteudo:
                    conteudo_descripto = descriptografar_dados(conteudo)
                    if ";" in conteudo_descripto:
                        usuario, senha = conteudo_descripto.split(";", 1)
                    elif "\n" in conteudo_descripto:
                        partes = conteudo_descripto.splitlines()
                        usuario = partes[0].strip()
                        senha = partes[1].strip() if len(partes) > 1 else ""
        except Exception as e:
            if log:
                log.warning(f"Erro ao ler login.dat: {e}")

    # Se já temos usuário e senha válidos no arquivo
    if usuario and senha:
        if log:
            log.info("Credenciais carregadas com sucesso do login.dat (criptografado).")
        return usuario, senha

    # Se não há credenciais e o modo for interativo
    if interactive:
        print("\n==================================================")
        print(" [eCobOne] Configuração Inicial de Credenciais")
        print("==================================================")
        usuario = input("Digite seu usuário do SIGS: ").strip()
        senha = getpass.getpass("Digite sua senha do SIGS: ").strip()

        if not usuario or not senha:
            if log:
                log.error("Usuário ou senha não podem ser vazios.")
            return None, None

        resposta = input("\nDeseja salvar seu login e senha criptografados no login.dat? (s/n): ").strip().lower()
        if resposta in ("s", "sim", "y", "yes"):
            try:
                dado_para_salvar = f"{usuario};{senha}"
                dado_criptografado = criptografar_dados(dado_para_salvar)
                with open(LOGIN_FILE, "w", encoding="utf-8") as f:
                    f.write(dado_criptografado + "\n")
                print("✓ Credenciais salvas com sucesso no login.dat (criptografado).\n")
                if log:
                    log.info("Credenciais salvas e criptografadas no login.dat.")
            except Exception as e:
                print(f"❌ Erro ao salvar credenciais: {e}")
                if log:
                    log.error(f"Erro ao salvar login.dat: {e}")

        return usuario, senha

    return None, None


# -------------------------------------------------------------
# Utilitários de Arquivo e Datas
# -------------------------------------------------------------
def _limpar_dir(d):
    """Limpa todos os arquivos de uma pasta temporária."""
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        p = os.path.join(d, f)
        if os.path.isfile(p):
            try:
                os.unlink(p)
            except Exception:
                pass


def _aguardar_download(d, timeout=60):
    """Aguarda o download do CSV ser concluído na pasta temporária."""
    os.makedirs(d, exist_ok=True)
    for _ in range(timeout):
        time.sleep(1)
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        arqs = os.listdir(d)
        if not any(f.endswith(".crdownload") for f in arqs):
            csvs = [f for f in arqs if f.endswith(".csv")]
            if csvs:
                return csvs[0]
    raise Exception("Timeout aguardando download do arquivo.")


def calcular_intervalo_datas():
    """
    Data Final: Hoje
    Data Inicial: Segunda-feira -> Sexta passada (-3 dias), outros dias -> Ontem (-1 dia).
    """
    hoje = datetime.now()
    if hoje.weekday() == 0:
        data_inicial = hoje - timedelta(days=3)
    else:
        data_inicial = hoje - timedelta(days=1)
    data_final = hoje
    return data_inicial.strftime("%d/%m/%Y"), data_final.strftime("%d/%m/%Y")


# -------------------------------------------------------------
# Etapa 1: Download Selenium (Salva em Files/Cache)
# -------------------------------------------------------------
def baixar_relatorios(usuario=None, senha=None, interactive=True, log=None):
    """
    Baixa os 4 relatórios via Selenium e salva na pasta Files/Cache/.
    """
    if not log:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
        log = logging.getLogger("UpdaterDownload")

    if not usuario or not senha:
        usuario, senha = obter_credenciais(interactive=interactive, log=log)

    if not usuario or not senha:
        log.error("Impossível prosseguir sem usuário e senha.")
        return False

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        log.error("Selenium não instalado. Execute: pip install selenium")
        return False

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_TEMP, exist_ok=True)

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_experimental_option(
        "prefs",
        {
            "download.default_directory": DOWNLOAD_TEMP,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    driver = None
    try:
        log.info("[1/2] Inicializando navegador Chrome (Headless)...")
        driver = webdriver.Chrome(options=opts)
        wait = WebDriverWait(driver, 30)

        log.info("Acessando portal SIGS para login...")
        driver.get(LOGIN_URL)

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="ctl00_ConteudoLogin_ControlLogin_UserName"]')
            )
        ).send_keys(usuario)

        driver.find_element(
            By.XPATH, '//*[@id="ctl00_ConteudoLogin_ControlLogin_Password"]'
        ).send_keys(senha)

        driver.find_element(
            By.XPATH, '//*[@id="ctl00_ConteudoLogin_ControlLogin_LoginButton"]'
        ).click()
        time.sleep(3)

        if "login" in driver.current_url.lower():
            driver.quit()
            raise CredencialInvalidaError("Usuário ou senha incorretos no portal SIGS.")

        log.info("Login autenticado com sucesso.")

        driver.get(RELATORIO_URL)
        time.sleep(5)

        # Seleciona filtro 'Data de importação'
        try:
            log.info("Selecionando filtro 'Data de importação'...")
            select_periodo = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_cmbPeriodo"]')
                )
            )
            select_periodo.click()
            time.sleep(1)

            opt_importacao = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_cmbPeriodo"]/option[contains(translate(text(), "IMPORTAÇÃO", "importação"), "importa")]')
                )
            )
            opt_importacao.click()
            time.sleep(1)
        except Exception as e_filtro:
            log.warning(f"Aviso ao selecionar 'Data de importação': {e_filtro}")

        dt_ini, dt_fim = calcular_intervalo_datas()
        log.info(f"Intervalo de datas definido: {dt_ini} até {dt_fim}")

        try:
            elem_ini = driver.find_element(By.XPATH, '//*[@id="ctl00_ConteudoPaginas_dtInicial_I"]')
            elem_ini.clear()
            elem_ini.send_keys(dt_ini)
            elem_ini.send_keys(Keys.TAB)
            time.sleep(1)
        except Exception as e_dt_ini:
            log.warning(f"Erro ao preencher Data Inicial: {e_dt_ini}")

        try:
            elem_fim = driver.find_element(By.XPATH, '//*[@id="ctl00_ConteudoPaginas_dtFinal_I"]')
            elem_fim.clear()
            elem_fim.send_keys(dt_fim)
            elem_fim.send_keys(Keys.TAB)
            time.sleep(1)
        except Exception as e_dt_fim:
            log.warning(f"Erro ao preencher Data Final: {e_dt_fim}")

        # Baixa os 4 arquivos para Files/Cache/
        for idx, srv in enumerate(SERVICOS, start=1):
            log.info(f"Baixando ({idx}/4): {srv['nome']}...")
            _limpar_dir(DOWNLOAD_TEMP)

            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_ASPxComboBox4_B-1"]')
                )
            ).click()
            time.sleep(1)

            wait.until(EC.element_to_be_clickable((By.XPATH, srv["xpath"]))).click()
            time.sleep(1)

            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_btgGerar_CD"]/span')
                )
            ).click()

            arq_tmp = _aguardar_download(DOWNLOAD_TEMP)
            origem = os.path.join(DOWNLOAD_TEMP, arq_tmp)
            destino = os.path.join(CACHE_DIR, srv["arquivo_destino"])

            if os.path.exists(destino):
                os.remove(destino)
            shutil.move(origem, destino)
            log.info(f"✓ {srv['arquivo_destino']} salvo com sucesso em Files/Cache/")
            time.sleep(2)

        driver.quit()
        try:
            shutil.rmtree(DOWNLOAD_TEMP)
        except Exception:
            pass

        log.info("✓ Todos os 4 arquivos baixados para Files/Cache/ com sucesso.")
        return True

    except Exception as e:
        log.error(f"Erro durante o download Selenium: {e}")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return False


# -------------------------------------------------------------
# Etapa 2: Consolidação dos CSVs (Salva em Files/Cache/Total)
# -------------------------------------------------------------
def limpar_arquivos_antigos(log=None, horas_retencao=1):
    """Remove arquivos arq_total_*.csv com mais de N horas (padrão: 1h) na pasta Total."""
    if not os.path.exists(TOTAL_DIR):
        return

    agora = datetime.now()
    arquivos = glob.glob(os.path.join(TOTAL_DIR, "arq_total_*.csv"))

    removidos = 0
    for arq in arquivos:
        try:
            mtime = os.path.getmtime(arq)
            data_arq = datetime.fromtimestamp(mtime)
            horas_idade = (agora - data_arq).total_seconds() / 3600.0
            if horas_idade >= horas_retencao:
                os.remove(arq)
                removidos += 1
                msg = f"  [Retenção] Arquivo antigo removido ({horas_idade:.1f}h de idade): {os.path.basename(arq)}"
                if log:
                    log.info(msg)
                else:
                    print(msg)
        except Exception as e:
            if log:
                log.warning(f"Erro ao verificar retenção do arquivo {os.path.basename(arq)}: {e}")

    if removidos > 0 and log:
        log.info(f"[Retenção] {removidos} arquivo(s) antigo(s) (>1h) removido(s).")


def consolidar_csvs(log=None):
    """
    Junta os arquivos arq_1.csv .. arq_4.csv localizados em Files/Cache/
    em um arquivo único arq_total_[timestamp].csv em Files/Cache/Total/.
    Mantec retenção de 1 hora.
    """
    if not log:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
        log = logging.getLogger("UpdaterConsolidate")

    log.info("[2/2] Iniciando consolidação dos arquivos CSV...")
    os.makedirs(TOTAL_DIR, exist_ok=True)
    limpar_arquivos_antigos(log=log, horas_retencao=1)

    arqs_entradas = [
        os.path.join(CACHE_DIR, srv["arquivo_destino"]) for srv in SERVICOS
    ]

    linhas_saida = []
    header_salvo = False

    for arq in arqs_entradas:
        if not os.path.exists(arq):
            log.warning(f"Arquivo não encontrado para consolidação: {os.path.basename(arq)}")
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
            log.warning(f"Arquivo {os.path.basename(arq)} está vazio.")
            continue

        if not header_salvo:
            linhas_saida.append(linhas[0])
            header_salvo = True
            dados = linhas[1:]
        else:
            dados = linhas[1:]

        linhas_saida.extend(dados)
        log.info(f"  + {os.path.basename(arq)}: {len(dados)} linhas adicionadas.")

    if not linhas_saida:
        log.error("Nenhum dado encontrado nos arquivos para consolidação.")
        return False

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nome_arquivo_total = f"arq_total_{timestamp}.csv"
    caminho_total = os.path.join(TOTAL_DIR, nome_arquivo_total)

    with open(caminho_total, "w", encoding="utf-8-sig") as f:
        f.writelines(linhas_saida)

    total_registros = len(linhas_saida) - 1
    log.info(f"✓ Arquivo consolidado gerado: {nome_arquivo_total} ({total_registros} registros).")
    return caminho_total


# -------------------------------------------------------------
# Etapa 3: Geração do Arquivo dados.txt
# -------------------------------------------------------------
DADOS_TXT = os.path.join(FILES_DIR, "dados.txt")

REGIOES_CONFIG = [
    ("ANAPOLIS", "ANA", ["04.CSC ANÁPOLIS", "05.CSC JARAGUÁ"]),
    ("LUZIANIA", "LUZ", ["06.CSC ÁGUAS LINDAS", "07.CSC LUZIÂNIA"]),
    ("FORMOSA", "FOR", ["08.CSC CAMPOS BELOS", "09.CSC FORMOSA"]),
    ("URUAÇU", "URU", ["10.CSC PORANGATU", "11.CSC URUAÇU"]),
    ("RIO VERDE", "RVR", ["16.CSC QUIRINÓPOLIS", "17.CSC RIO VERDE"]),
    ("MORRINHOS", "MNH", ["18.CSC MORRINHOS", "18.CSC  MORRINHOS", "19.CSC CATALÃO"]),
]


def _limpar_nome_colaborador(nome):
    import pandas as pd
    if pd.isna(nome):
        return ""
    nome_str = str(nome).strip()
    if " - " in nome_str:
        nome_str = nome_str.rsplit("-", 1)[-1]
    return nome_str.strip().upper()


def _normalizar_etapa(etapa):
    import pandas as pd
    if pd.isna(etapa):
        return ""
    e_str = str(etapa).strip().upper()
    if "NAO EXECUTADO" in e_str or "NÃO EXECUTADO" in e_str:
        return "NAO EXECUTADO"
    if "EM CAMPO" in e_str:
        return "EM CAMPO"
    if "EXECUTADO" in e_str:
        return "EXECUTADO"
    return e_str


def _converter_valor(val):
    import pandas as pd
    if pd.isna(val):
        return 0.0
    v_str = str(val).strip().replace(".", "").replace(",", ".")
    try:
        return float(v_str)
    except Exception:
        return 0.0


def _formatar_moeda(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_dados_txt(caminho_csv=None, log=None):
    """
    Lê a base consolidada (arq_total_*.csv), aplica os filtros de negócio do dia de hoje,
    e gera o arquivo Python-Updater/Files/dados.txt.
    """
    if not log:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
        log = logging.getLogger("UpdaterDados")

    log.info("[3/3] Gerando dados em Files/dados.txt...")
    import pandas as pd

    os.makedirs(FILES_DIR, exist_ok=True)

    if not caminho_csv:
        arquivos = glob.glob(os.path.join(TOTAL_DIR, "arq_total_*.csv"))
        if arquivos:
            arquivos.sort(key=os.path.getmtime, reverse=True)
            caminho_csv = arquivos[0]

    if not caminho_csv or not os.path.exists(caminho_csv):
        log.error("Nenhum arquivo consolidado arq_total encontrado para gerar dados.txt.")
        return False

    df = None
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            df = pd.read_csv(caminho_csv, sep=";", encoding=enc, dtype=str, on_bad_lines="skip")
            break
        except Exception:
            continue

    if df is None or df.empty:
        log.error(f"Falha ao carregar CSV para gerar dados.txt: {caminho_csv}")
        return False

    df.columns = df.columns.str.strip()

    # Filtro de Data de despacho de hoje
    hoje_str = datetime.now().strftime("%d/%m/%Y")
    if "Data despacho" in df.columns:
        data_despacho_col = df["Data despacho"].fillna("").astype(str).str.split(" ").str[0].str.strip()
        df_hoje = df[data_despacho_col == hoje_str].copy()
    else:
        df_hoje = df.copy()

    if df_hoje.empty:
        log.warning(f"Nenhum registro encontrado para a data de hoje ({hoje_str}) na Data de despacho.")

    df_hoje["Nome_Limpo"] = df_hoje["Equipe"].apply(_limpar_nome_colaborador) if "Equipe" in df_hoje.columns else ""
    df_hoje["Etapa_Norm"] = df_hoje["Etapa"].apply(_normalizar_etapa) if "Etapa" in df_hoje.columns else ""
    df_hoje["Valor_Float"] = df_hoje["Valor Total Debito"].apply(_converter_valor) if "Valor Total Debito" in df_hoje.columns else 0.0

    def mapear_regiao(ag):
        if pd.isna(ag):
            return ("OUTROS", "OUT")
        ag_str = str(ag).strip().upper()
        for r_nome, r_cod, ags in REGIOES_CONFIG:
            for a in ags:
                if a.upper() in ag_str:
                    return (r_nome, r_cod)
        return ("OUTROS", "OUT")

    if "Agencia" in df_hoje.columns:
        res = df_hoje["Agencia"].apply(mapear_regiao)
        df_hoje["Regiao"] = [r[0] for r in res]
        df_hoje["Regiao_Cod"] = [r[1] for r in res]
    else:
        df_hoje["Regiao"] = "OUTROS"
        df_hoje["Regiao_Cod"] = "OUT"

    SERV_EXCLUIDOS = [
        "VISITA DE LEITURA",
        "VISITA COMERCIAL GR",
        "RESTABELECIMENTO FORNEC. AUTOMÁTICO",
        "RESTABELECIMENTO FORNEC. NORMAL",
        "RESTABELECIMENTO FORNEC. NORMAL - MUDANÇA TITUL."
    ]

    RLGA_INCLUIDOS = [
        "RESTABELECIMENTO FORNEC. AUTOMÁTICO",
        "RESTABELECIMENTO FORNEC. NORMAL",
        "RESTABELECIMENTO FORNEC. NORMAL - MUDANÇA TITUL."
    ]

    NEPG_EXCLUIDOS = [
        "VISITA DE LEITURA",
        "VISITA COMERCIAL GR"
    ]

    def calc_metricas_bloco(sub_df):
        nome_serv_u = sub_df["nomeServico"].fillna("").astype(str).str.strip().str.upper() if "nomeServico" in sub_df.columns else pd.Series(dtype=str)
        etapa_u = sub_df["Etapa_Norm"]
        msg_u = sub_df["Mensagem"].fillna("").astype(str).str.strip().str.upper() if "Mensagem" in sub_df.columns else pd.Series(dtype=str)

        cond_serv = (etapa_u == "EXECUTADO") & (~nome_serv_u.isin(SERV_EXCLUIDOS))
        serv_cnt = int(cond_serv.sum())

        cond_rlga = (etapa_u == "EXECUTADO") & (nome_serv_u.isin(RLGA_INCLUIDOS))
        rlga_cnt = int(cond_rlga.sum())

        cond_nepg = (etapa_u == "NAO EXECUTADO") & (~nome_serv_u.isin(NEPG_EXCLUIDOS)) & (msg_u.str.contains("NE/PAGO"))
        nepg_cnt = int(cond_nepg.sum())

        fanp_val = float(sub_df[cond_nepg]["Valor_Float"].sum()) if not sub_df[cond_nepg].empty else 0.0

        cond_campo = (etapa_u == "EM CAMPO")
        svcapc_cnt = int(cond_campo.sum())

        serv_colab = sub_df[cond_serv].groupby("Nome_Limpo").size().to_dict() if not sub_df[cond_serv].empty else {}
        rlga_colab = sub_df[cond_rlga].groupby("Nome_Limpo").size().to_dict() if not sub_df[cond_rlga].empty else {}

        todos_colabs = set(serv_colab.keys()).union(set(rlga_colab.keys()))
        ranking = []
        for colab in todos_colabs:
            if not colab or "BERENICE" in colab:
                continue
            s_c = serv_colab.get(colab, 0)
            r_c = rlga_colab.get(colab, 0)
            tot = s_c + r_c
            ranking.append((colab, s_c, r_c, tot))

        ranking.sort(key=lambda x: (x[3], x[1], x[2]), reverse=True)
        top10 = ranking[:10]

        ranking_piores = sorted(ranking, key=lambda x: (x[3], x[1], x[2]))
        bottom10 = ranking_piores[:10]

        return serv_cnt, rlga_cnt, nepg_cnt, fanp_val, svcapc_cnt, top10, bottom10

    # Detecção de Religas / Restabelecimentos "ALERTA"
    etapa_raw = df_hoje["Etapa"].fillna("").astype(str).str.strip().str.upper() if "Etapa" in df_hoje.columns else pd.Series(dtype=str)
    nome_serv_raw = df_hoje["nomeServico"].fillna("").astype(str).str.strip().str.upper() if "nomeServico" in df_hoje.columns else pd.Series(dtype=str)

    col_ss = None
    for c_ss in ["Numero SS", "Número SS", "SS", "Ordem de Serviço", "OS"]:
        if c_ss in df_hoje.columns:
            col_ss = c_ss
            break

    cond_alerta = (etapa_raw.str.contains("ALERTA")) & (
        nome_serv_raw.str.contains("RESTABELECIMENTO") | nome_serv_raw.str.contains("RELIGA")
    )
    df_alertas = df_hoje[cond_alerta].copy()

    def _calcular_vencimento(row):
        for col_dt in ["Data abertura original", "Data abertura"]:
            if col_dt in row and pd.notna(row[col_dt]) and str(row[col_dt]).strip():
                try:
                    dt_val = str(row[col_dt]).strip()
                    dt_obj = datetime.strptime(dt_val, "%d/%m/%Y %H:%M:%S")
                    dt_venc = dt_obj + timedelta(hours=24)
                    return dt_venc.strftime("%H:%M")
                except Exception:
                    pass
        return "18:00"

    lista_alertas_txt = []
    if not df_alertas.empty:
        for _, row in df_alertas.iterrows():
            ss_v = str(row[col_ss]).strip() if col_ss and col_ss in row and pd.notna(row[col_ss]) else "S/N"
            colab_v = str(row["Nome_Limpo"]).strip() if "Nome_Limpo" in row and pd.notna(row["Nome_Limpo"]) else "NÃO INFORMADO"
            serv_v = str(row["nomeServico"]).strip() if "nomeServico" in row and pd.notna(row["nomeServico"]) else "RESTABELECIMENTO"
            reg_v = str(row["Regiao_Cod"]).strip() if "Regiao_Cod" in row and pd.notna(row["Regiao_Cod"]) else "OUT"
            venc_v = _calcular_vencimento(row)
            lista_alertas_txt.append(f"{ss_v};{colab_v};{serv_v};{reg_v};{venc_v}")

    # Data/Hora de atualização da base baixada
    mtime_csv = os.path.getmtime(caminho_csv) if caminho_csv and os.path.exists(caminho_csv) else time.time()
    dt_base_str = datetime.fromtimestamp(mtime_csv).strftime("%d/%m/%Y %H:%M:%S")

    linhas_txt = []
    linhas_txt.append(f"Atualizacao: {dt_base_str}")
    linhas_txt.append("")

    # Bloco de Alertas
    linhas_txt.append("Alertas:")
    if lista_alertas_txt:
        linhas_txt.extend(lista_alertas_txt)
    else:
        linhas_txt.append("0")
    linhas_txt.append("")

    # Bloco Geral
    serv, rlga, nepg, fanp, svcapc, top10, bottom10 = calc_metricas_bloco(df_hoje)
    linhas_txt.append("Geral:")
    linhas_txt.append(f"Serviços: {serv}")
    linhas_txt.append(f"Religas: {rlga}")
    linhas_txt.append(f"NePago: {nepg}")
    linhas_txt.append(f"Faturamento: {_formatar_moeda(fanp)}")
    linhas_txt.append(f"EmCampo: {svcapc}")
    for idx, (colab, s_c, r_c, _) in enumerate(top10, start=1):
        linhas_txt.append(f"{idx};{colab};{s_c};{r_c}")
    linhas_txt.append("Piores:")
    for idx, (colab, s_c, r_c, _) in enumerate(bottom10, start=1):
        linhas_txt.append(f"{idx};{colab};{s_c};{r_c}")

    # Bloco por Região
    for reg_nome, reg_cod, _ in REGIOES_CONFIG:
        sub_reg = df_hoje[df_hoje["Regiao_Cod"] == reg_cod]
        serv_r, rlga_r, nepg_r, fanp_r, svcapc_r, top10_r, bottom10_r = calc_metricas_bloco(sub_reg)
        linhas_txt.append("")
        linhas_txt.append(f"Região: {reg_nome} ({reg_cod})")
        linhas_txt.append(f"Serviços: {serv_r}")
        linhas_txt.append(f"Religas: {rlga_r}")
        linhas_txt.append(f"NePago: {nepg_r}")
        linhas_txt.append(f"Faturamento: {_formatar_moeda(fanp_r)}")
        linhas_txt.append(f"EmCampo: {svcapc_r}")
        for idx, (colab, s_c, r_c, _) in enumerate(top10_r, start=1):
            linhas_txt.append(f"{idx};{colab};{s_c};{r_c}")
        linhas_txt.append("Piores:")
        for idx, (colab, s_c, r_c, _) in enumerate(bottom10_r, start=1):
            linhas_txt.append(f"{idx};{colab};{s_c};{r_c}")

    conteudo_final = "\n".join(linhas_txt) + "\n"
    with open(DADOS_TXT, "w", encoding="utf-8") as f:
        f.write(conteudo_final)

    try:
        root_dir = os.path.abspath(os.path.join(BASE, "..", ".."))
        target_files_dir = os.path.join(root_dir, "Python-Updater", "Files")
        os.makedirs(target_files_dir, exist_ok=True)
        shutil.copy2(DADOS_TXT, os.path.join(target_files_dir, "dados.txt"))
    except Exception as e_sync:
        if log:
            log.warning(f"Aviso ao sincronizar dados.txt: {e_sync}")

    if log:
        log.info(f"✓ dados.txt gerado com sucesso em Files/dados.txt! ({len(linhas_txt)} linhas)")
    return DADOS_TXT


# -------------------------------------------------------------
# Orquestrador Principal
# -------------------------------------------------------------
def executar_atualizacao(usuario=None, senha=None, interactive=True, log=None):
    """Executa o ciclo completo de Download + Consolidação + Geração de dados.txt."""
    if not log:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
        log = logging.getLogger("UpdaterMain")

    log.info("==================================================")
    log.info("   INICIANDO CICLO DE ATUALIZAÇÃO (eCobOne)")
    log.info("==================================================")

    ok_download = baixar_relatorios(usuario=usuario, senha=senha, interactive=interactive, log=log)
    if not ok_download:
        log.error("Falha no download dos arquivos. Atualização abortada.")
        return False

    caminho_total = consolidar_csvs(log=log)
    if not caminho_total:
        log.error("Falha na consolidação dos arquivos CSV.")
        return False

    caminho_dados = gerar_dados_txt(caminho_csv=caminho_total, log=log)
    if not caminho_dados:
        log.error("Falha na geração do arquivo dados.txt.")
        return False

    log.info("==================================================")
    log.info(f"✓ ATUALIZAÇÃO CONCLUÍDA! Arquivos: {caminho_total} | {caminho_dados}")
    log.info("==================================================")
    return True


if __name__ == "__main__":
    executar_atualizacao(interactive=True)

