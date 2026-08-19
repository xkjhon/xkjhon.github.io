# =============================================================
# eCobOne — betatester.py (Script de Teste Completo)
# =============================================================

import os
import sys
import time
import logging
from updater import (
    obter_credenciais,
    baixar_relatorios,
    consolidar_csvs,
    gerar_dados_txt,
    executar_atualizacao,
    CACHE_DIR,
    TOTAL_DIR,
    DADOS_TXT,
    LOGIN_FILE,
    SERVICOS
)


def configurar_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    return logging.getLogger("BetaTester")


def exibir_cabecalho():
    print("=" * 60)
    print("           eCobOne — SUÍTE DE TESTES (BETA TESTER)")
    print("=" * 60)
    print("Este script testa de forma isolada ou integrada as etapas de:")
    print("  1. Verificação / Cadastro de Credenciais (login.dat)")
    print("  2. Download dos 4 relatórios CSV via Selenium")
    print("  3. Consolidação e Retenção na pasta Files/Cache/Total/")
    print("  4. Geração do arquivo estruturado Files/dados.txt")
    print("=" * 60)


def testar_credenciais(logger):
    print("\n--- [TESTE 1] Verificação de Credenciais ---")
    if os.path.exists(LOGIN_FILE):
        tamanho = os.path.getsize(LOGIN_FILE)
        print(f"✓ Arquivo login.dat encontrado ({tamanho} bytes).")
    else:
        print("ℹ Arquivo login.dat não encontrado. O sistema irá solicitar usuário e senha.")

    user, pw = obter_credenciais(interactive=True, log=logger)
    if user and pw:
        senha_mascarada = pw[0] + "*" * (len(pw) - 2) + pw[-1] if len(pw) > 2 else "***"
        print(f"✓ Credenciais prontas para uso: Usuário = '{user}' | Senha = '{senha_mascarada}'")
        return user, pw
    else:
        print("❌ Não foi possível obter credenciais válidas.")
        return None, None


def testar_download(logger, user, pw):
    print("\n--- [TESTE 2] Execução do Download via Selenium ---")
    inicio = time.time()
    sucesso = baixar_relatorios(usuario=user, senha=pw, interactive=False, log=logger)
    tempo = time.time() - inicio

    if sucesso:
        print(f"\n✓ Download concluído em {tempo:.1f} segundos!")
        print("Relatórios baixados em Files/Cache/:")
        for srv in SERVICOS:
            caminho = os.path.join(CACHE_DIR, srv["arquivo_destino"])
            if os.path.exists(caminho):
                tam_kb = os.path.getsize(caminho) / 1024
                try:
                    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                        qtd_linhas = sum(1 for _ in f) - 1
                except Exception:
                    qtd_linhas = 0
                print(f"  • {srv['nome']} ({srv['arquivo_destino']}): {tam_kb:.1f} KB | {qtd_linhas} registros")
            else:
                print(f"  ❌ {srv['nome']} ({srv['arquivo_destino']}): NÃO ENCONTRADO")
        return True
    else:
        print(f"\n❌ Falha no teste de download após {tempo:.1f} segundos.")
        return False


def testar_consolidacao(logger):
    print("\n--- [TESTE 3] Consolidação de CSVs ---")
    inicio = time.time()
    caminho_total = consolidar_csvs(log=logger)
    tempo = time.time() - inicio

    if caminho_total and os.path.exists(caminho_total):
        tam_kb = os.path.getsize(caminho_total) / 1024
        try:
            with open(caminho_total, "r", encoding="utf-8", errors="ignore") as f:
                qtd_linhas = sum(1 for _ in f) - 1
        except Exception:
            qtd_linhas = 0

        print(f"\n✓ Consolidação concluída em {tempo:.1f} segundos!")
        print(f"Arquivo gerado: {os.path.basename(caminho_total)}")
        print(f"Caminho completo: {caminho_total}")
        print(f"Tamanho: {tam_kb:.1f} KB | Total de Registros: {qtd_linhas}")
        return caminho_total
    else:
        print(f"\n❌ Falha na consolidação de CSVs.")
        return None


def testar_geracao_dados(logger, caminho_csv=None):
    print("\n--- [TESTE 4] Geração de dados.txt ---")
    inicio = time.time()
    caminho_dados = gerar_dados_txt(caminho_csv=caminho_csv, log=logger)
    tempo = time.time() - inicio

    if caminho_dados and os.path.exists(caminho_dados):
        tam_kb = os.path.getsize(caminho_dados) / 1024
        try:
            with open(caminho_dados, "r", encoding="utf-8", errors="ignore") as f:
                linhas = f.readlines()
                qtd_linhas = len(linhas)
        except Exception:
            qtd_linhas = 0

        print(f"\n✓ Geração de dados.txt concluída em {tempo:.2f} segundos!")
        print(f"Caminho: {caminho_dados}")
        print(f"Tamanho: {tam_kb:.1f} KB | Total de Linhas: {qtd_linhas}")
        print("\n--- PRÉVIA DO CONTEÚDO DO DADOS.TXT (PRIMEIRAS 25 LINHAS) ---")
        for line in linhas[:25]:
            print(line.rstrip())
        print("------------------------------------------------------------")
        return True
    else:
        print(f"\n❌ Falha na geração do arquivo dados.txt.")
        return False


def menu_interativo():
    logger = configurar_logger()
    exibir_cabecalho()

    while True:
        print("\nESCOLHA UMA OPÇÃO DE TESTE:")
        print("  1 - Executar Ciclo Completo (Download + Consolidação + dados.txt)")
        print("  2 - Testar apenas Login / Credenciais")
        print("  3 - Testar apenas Download Selenium")
        print("  4 - Testar apenas Consolidação (Files/Cache/Total)")
        print("  5 - Testar apenas Geração de dados.txt (usando consolidado existente)")
        print("  0 - Sair")

        opcao = input("\nOpção desejada: ").strip()

        if opcao == "1":
            user, pw = testar_credenciais(logger)
            if user and pw:
                if testar_download(logger, user, pw):
                    cam_tot = testar_consolidacao(logger)
                    if cam_tot:
                        testar_geracao_dados(logger, caminho_csv=cam_tot)
        elif opcao == "2":
            testar_credenciais(logger)
        elif opcao == "3":
            user, pw = testar_credenciais(logger)
            if user and pw:
                testar_download(logger, user, pw)
        elif opcao == "4":
            testar_consolidacao(logger)
        elif opcao == "5":
            testar_geracao_dados(logger)
        elif opcao == "0":
            print("\nSaindo da suíte de testes. Até logo!")
            break
        else:
            print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    menu_interativo()
