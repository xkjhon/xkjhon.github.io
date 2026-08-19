# =============================================================
# RELABOT v1.0 — step1.py (Step 1: Download dos arquivos CSV via Selenium)
# =============================================================

import os
import time
import shutil
from datetime import datetime, timedelta

# Define os caminhos das pastas base, da pasta Base (destino final) e temporária de download
BASE         = os.path.dirname(os.path.abspath(__file__))
BASE_DIR     = os.path.join(BASE, "Base")
DOWNLOAD_TEMP = os.path.join(BASE, "_download_temp")

# URLs de acesso ao sistema SIGS
LOGIN_URL     = "http://sigsreliga.equatorialenergia.com.br:3030/Meireles/Login/Index?ReturnUrl=%2fMeireles%2fAcompanhamento%2fTodosServicos"
RELATORIO_URL = "http://sigsreliga.equatorialenergia.com.br:3030/Meireles/Relatorio/ExportacaoSS"

# Lista de serviços que serão baixados sequencialmente no portal e salvos na pasta Base/
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


# Exceção personalizada para tratamento de login/senha incorretos
class CredencialInvalidaError(Exception):
    pass


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
    """
    Aguarda o download do arquivo CSV ser concluído na pasta temporária.
    Garante que não existem mais arquivos com extensão .crdownload (download em andamento).
    """
    os.makedirs(d, exist_ok=True)
    for _ in range(timeout):
        time.sleep(1)
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        arqs = os.listdir(d)
        # Verifica se o Chrome ainda está baixando o arquivo
        if not any(f.endswith(".crdownload") for f in arqs):
            csvs = [f for f in arqs if f.endswith(".csv")]
            if csvs:
                return csvs[0]
    raise Exception("Timeout aguardando download do arquivo.")


def calcular_intervalo_datas():
    """
    Calcula as datas inicial e final dinamicamente:
    - Data Final: Sempre a data de hoje.
    - Data Inicial:
        - Se hoje for Segunda-feira (weekday = 0): Data Inicial = Sexta-feira passada (-3 dias).
        - Qualquer outro dia da semana: Data Inicial = Ontem (-1 dia).
    Retorna strings formatadas no padrão DD/MM/YYYY.
    """
    hoje = datetime.now()
    
    # 0 indica Segunda-feira no Python datetime
    if hoje.weekday() == 0:
        data_inicial = hoje - timedelta(days=3)  # Última Sexta-feira
    else:
        data_inicial = hoje - timedelta(days=1)  # Ontem
        
    data_final = hoje  # Hoje

    return data_inicial.strftime("%d/%m/%Y"), data_final.strftime("%d/%m/%Y")


def executar_download(log, username, password):
    """
    Executa a automação Selenium:
    1. Abre o navegador Chrome em modo invisível (headless).
    2. Realiza o login no portal SIGS.
    3. Navega até a página de exportação de relatórios.
    4. Define o filtro como 'Data de importação'.
    5. Preenche Data Inicial (Ontem ou Sexta) e Data Final (Hoje).
    6. Baixa os 4 relatórios (Religações, Suspensões, Vistorias, Visitas).
    7. Salva os arquivos na pasta Base/ nomeando-os de arq_1.csv até arq_4.csv.
    """
    # ── PASSO 1: Importação dos módulos do Selenium
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

    # Garante que as pastas de destino Base/ e temporária existam
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_TEMP, exist_ok=True)

    # ── PASSO 2: Configuração das opções do Chrome (Modo Headless / Invisível)
    opts = Options()
    opts.add_argument("--headless")  # Executa o navegador sem abrir janela gráfica
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--log-level=3")  # Reduz logs no console
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    # Define a pasta temporária como local padrão de download no Chrome
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
        # ── PASSO 3: Inicialização do WebDriver do Chrome
        driver = webdriver.Chrome(options=opts)
        wait = WebDriverWait(driver, 30)

        # ── PASSO 4: Realização do Login no SIGS
        log.info("[PROGRESS: 5] Acessando página de login do RelaBot...")
        driver.get(LOGIN_URL)
        
        # Preenche Usuário
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="ctl00_ConteudoLogin_ControlLogin_UserName"]')
            )
        ).send_keys(username)
        
        # Preenche Senha
        driver.find_element(
            By.XPATH, '//*[@id="ctl00_ConteudoLogin_ControlLogin_Password"]'
        ).send_keys(password)
        
        # Clica em Entrar
        driver.find_element(
            By.XPATH, '//*[@id="ctl00_ConteudoLogin_ControlLogin_LoginButton"]'
        ).click()
        time.sleep(3)

        # Verifica se o login falhou
        if "login" in driver.current_url.lower():
            driver.quit()
            raise CredencialInvalidaError(
                "Usuário ou senha incorretos."
            )
        log.info("[PROGRESS: 10] Login realizado com sucesso.")

        # ── PASSO 5: Navegação e Configuração dos Filtros de Data
        driver.get(RELATORIO_URL)
        time.sleep(5)

        # 5.1: Seleciona o filtro 'Data de importação' no dropdown de tipo de período
        try:
            log.info("[PROGRESS: 15] Selecionando tipo de período: Data de importação...")
            select_periodo = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_cmbPeriodo"]')
                )
            )
            select_periodo.click()
            time.sleep(1)
            
            # Clica na opção contendo 'importa' (Data de importação)
            opt_importacao = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_cmbPeriodo"]/option[contains(translate(text(), "IMPORTAÇÃO", "importação"), "importa")]')
                )
            )
            opt_importacao.click()
            time.sleep(1)
        except Exception as e_filtro:
            log.warning(f"  Não foi possível selecionar 'Data de importação' via dropdown: {e_filtro}")

        # 5.2: Calcula o intervalo de datas (Ontem/Sexta até Hoje)
        str_dt_ini, str_dt_fim = calcular_intervalo_datas()
        log.info(f"[PROGRESS: 18] Definindo intervalo de datas: Data Inicial = {str_dt_ini} | Data Final = {str_dt_fim}")

        # 5.3: Preenche o campo Data Inicial
        try:
            elem_ini = driver.find_element(By.XPATH, '//*[@id="ctl00_ConteudoPaginas_dtInicial_I"]')
            elem_ini.clear()
            elem_ini.send_keys(str_dt_ini)
            elem_ini.send_keys(Keys.TAB)
            time.sleep(1)
        except Exception as e_dt_ini:
            log.warning(f"  Erro ao preencher Data Inicial: {e_dt_ini}")

        # 5.4: Preenche o campo Data Final
        try:
            elem_fim = driver.find_element(By.XPATH, '//*[@id="ctl00_ConteudoPaginas_dtFinal_I"]')
            elem_fim.clear()
            elem_fim.send_keys(str_dt_fim)
            elem_fim.send_keys(Keys.TAB)
            time.sleep(1)
        except Exception as e_dt_fim:
            log.warning(f"  Erro ao preencher Data Final: {e_dt_fim}")

        # ── PASSO 6: Loop de Download dos 4 Serviços para a pasta Base/
        for idx, srv in enumerate(SERVICOS):
            progress_pct = 20 + idx * 10
            log.info(f"[PROGRESS: {progress_pct}] Baixando: {srv['nome']}...")
            _limpar_dir(DOWNLOAD_TEMP)

            # Clica no dropdown de escolha de tipo de serviço
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_ASPxComboBox4_B-1"]')
                )
            ).click()
            time.sleep(1)

            # Clica no serviço desejado (Religações, Suspensões, Vistorias ou Visitas)
            wait.until(EC.element_to_be_clickable((By.XPATH, srv["xpath"]))).click()
            time.sleep(1)

            # Clica no botão "Gerar" para emitir e baixar o CSV
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ctl00_ConteudoPaginas_btgGerar_CD"]/span')
                )
            ).click()

            # Aguarda o término do download do CSV na pasta temporária
            arq_tmp = _aguardar_download(DOWNLOAD_TEMP)
            origem  = os.path.join(DOWNLOAD_TEMP, arq_tmp)
            destino = os.path.join(BASE_DIR, srv["arquivo_destino"])

            # Move e salva como arq_1.csv, arq_2.csv, arq_3.csv ou arq_4.csv dentro da pasta Base/
            if os.path.exists(destino):
                os.remove(destino)
            shutil.move(origem, destino)
            log.info(f"[PROGRESS: {progress_pct + 5}] {srv['arquivo_destino']} salvo com sucesso em Base/")
            time.sleep(2)

        # ── PASSO 7: Finalização e Limpeza
        driver.quit()
        try:
            shutil.rmtree(DOWNLOAD_TEMP)
        except Exception:
            pass

        log.info("[PROGRESS: 60] Todos os 4 arquivos baixados com sucesso para a pasta Base/.")
        return True

    except CredencialInvalidaError as e:
        log.error(str(e))
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return False

    except Exception as e:
        log.error(f"Erro no download no step1: {e}")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return False
