# ============================================================
# DogKong v2.3  Criptomoeda com dificuldade dinmica estilo Bitcoin
# PoW: CPU+RAM 64MB / P2P: 18555 / Dificuldade: bits/target + LWMA
# Anti-travamento: decaimento temporal em tempo real
# Genesis: minerado automaticamente na primeira execuo
# ============================================================

import os
import sys
import json
import time
import math
import hmac
import socket
import shutil
import hashlib
import os, datetime

if getattr(sys, 'frozen', False):
    NOTIF_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "notificacoes.txt")
else:
    NOTIF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notificacoes.txt")

def add_notificacao(msg):
    if msg.startswith('BLOCO') or msg.startswith('Bloco'):
        return
    try:
        with open(NOTIF_FILE, "a", encoding="utf-8") as f:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
        try:
            flag = NOTIF_FILE + ".new"
            with open(flag, "w") as ff:
                ff.write("1")
        except:
            pass
    except Exception as e:
        print(f"[NOTIF] erro: {e}", flush=True)
import secrets
import struct
import urllib.request
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass


import ctypes
import sys
import os

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def liberar_firewall():
    if os.name != "nt":
        return
    try:
        os.system('netsh advfirewall firewall add rule name="DogKong P2P" dir=in action=allow protocol=TCP localport=18555 >nul 2>&1')
    except:
        pass

if os.name == "nt":
    if not is_admin():
        try:
            resultado = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            if resultado <= 32:
                print("[ERRO] Permissao de Administrador negada.")
                sys.exit(1)
            sys.exit(0)
        except Exception as e:
            print(f"[ERRO] Falha ao pedir permissao: {e}")
            sys.exit(1)
    else:
        liberar_firewall()

APP = "DogKong v2"
VERSION = "2.3"
P2P_PORT = 18555
CHAIN_ID = "DOGK-V2-MAINNET"

SEED_ONLY = os.environ.get("DOGK_SEED_ONLY") == "1"
HUB_MODE = os.environ.get("DOGK_HUB") == "1"
MAX_ACTIVE_CONNS = 50

FORCE_SEED_IP = os.environ.get("DOGK_SEED_IP", "").strip()
SEED_CONNS = int(os.environ.get("DOGK_SEED_CONNS", "2"))
TOR_ENABLED = os.environ.get("DOGK_TOR", "0") == "1"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE_DIR, "dogk_data_v2")
WALLET_FILE = os.path.join(DATA, "wallet.json")
CHAIN_FILE = os.path.join(DATA, "blockchain.json")
MEMPOOL_FILE = os.path.join(DATA, "mempool.json")
PEERS_FILE = os.path.join(DATA, "peers.json")
SEEDS_FILE = os.path.join(DATA, "seeds.json")
LANG_FILE = os.path.join(DATA, "lang.txt")
os.makedirs(DATA, exist_ok=True)

def _caminho_recurso(nome):
    """Procura o recurso. PRIORIDADE: pasta do .exe > cwd > _MEIPASS."""
    candidatos = []
    if getattr(sys, 'frozen', False):
        # PRIORIDADE 1: pasta do .exe (sys.argv[0])
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        candidatos.append(os.path.join(exe_dir, nome))
        # PRIORIDADE 2: pasta do sys.executable
        candidatos.append(os.path.join(os.path.dirname(sys.executable), nome))
        # PRIORIDADE 3: cwd
        candidatos.append(os.path.join(os.getcwd(), nome))
        # PRIORIDADE 4: _MEIPASS (temp do PyInstaller)
        if hasattr(sys, '_MEIPASS'):
            candidatos.append(os.path.join(sys._MEIPASS, nome))
    else:
        candidatos.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), nome))
        candidatos.append(os.path.join(os.getcwd(), nome))
    for caminho in candidatos:
        if os.path.exists(caminho):
            try:
                print(f"[_caminho_recurso] {nome} -> ENCONTRADO: {caminho}", flush=True)
            except: pass
            return caminho
    try:
        print(f"[_caminho_recurso] {nome} -> NAO ENCONTRADO. Candidatos: {candidatos}", flush=True)
    except: pass
    return candidatos[0] if candidatos else nome


# ============================================================
# DETECCAO AUTOMATICA DE PRINCIPAL (VPS / primeiro no)
# Regra:
#   1. Se existe principal.txt na pasta dogk_data_v2/  -> PRINCIPAL
#   2. Senao, se peers.json nao existe ou esta vazio    -> PRINCIPAL
#   3. Senao                                            -> PEER NORMAL
# ============================================================
PRINCIPAL_FILE = os.path.join(DATA, "principal.txt")
PEERS_FILE_TMP = os.path.join(DATA, "peers.json")

def _detectar_principal():
    # 1. Env var DOGK_PRINCIPAL=1 forca principal
    if os.environ.get("DOGK_PRINCIPAL", "0") == "1":
        try:
            with open(PRINCIPAL_FILE, "w", encoding="utf-8") as f:
                f.write("1")
        except Exception:
            pass
        return True
    # 2. Se principal.txt existe, e principal
    if os.path.exists(PRINCIPAL_FILE):
        return True
    return False

SOU_PRINCIPAL = False
PRINCIPAL_CONNS = int(os.environ.get("DOGK_PRINCIPAL_CONNS", "4"))

INITIAL_SUPPLY_REF = 10_000_000_000
YEARLY_EMISSION = 5_256_000_000
BLOCK_TIME = 60
BLOCKS_YEAR = 525_600
REWARD_PER_BLOCK = 10_000.0

# ============================================================
# DIFICULDADE PADRO BITCOIN (BITS / TARGET) COM LWMA
# ============================================================
TARGET_MAX_BTC = 0x000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
INITIAL_DIFFICULTY = 0x1e0fffff   # MUITO fcil  genesis sai em <1s

DIFFICULTY_WINDOW = 14            # janela LWMA
LWMA_START_HEIGHT = 11984        # LWMA real a partir deste bloco
MAX_TIME_DELTA = BLOCK_TIME * 4   # clamp de timestamp

# Anti-travamento em tempo real
STALL_TIME_MULT = 5               # ativa aps 5  BLOCK_TIME = 300s sem bloco

FAST_TIME = BLOCK_TIME // 2
SLOW_TIME = BLOCK_TIME * 2

MAX_BLOCK_TX = 3000
MAX_PEERS = 1000

# ============================================================
# HARDENING
# ============================================================
PROTOCOL_VERSION = 2
MIN_PROTOCOL_VERSION = 2
MAGIC = b"DOGK"
MAX_MEMPOOL_TX = 20000
MAX_MEMPOOL_BYTES = 20_000_000
MAX_FUTURE_TIME = 7200
CHECKPOINT_INTERVAL = 1000
CHECKPOINT_DEPTH = 100
PEER_BAN_TIME = 3600
MAX_PEERS_PER_IP = 10
MIN_OUTBOUND_PEERS = 4
HANDSHAKE_TIMEOUT = 10
MAX_PEER_MESSAGES_PER_MIN = 120

USE_ARGON2 = False
try:
    import argon2.low_level as _argon2
    USE_ARGON2 = True
except ImportError:
    pass

MEMORY_MB = 64
MEMORY_ITER = 128

MINER_CPU_PERCENT = 95
MINER_BATCH = 200

MIN_FEE = 0.0001
PBKDF2_ITER = 600_000
MAX_MSG_BYTES = 10_000_000
RATE_LIMIT_PER_SEC = 20

DEFAULT_SEEDS = [
    "dogkong-seed1.duckdns.org",
]
HARDCODED_IPS = []  # Sem IP fixo (P2P puro)
REMOTE_SEEDS_URL = ""
    


# ============================================================
# 5 IDIOMAS
# ============================================================
LANGUAGES = {
    "en": "English",
    "pt": "Portugues",
    "es": "Espanol",
    "zh": "Zhongwen",
    "ru": "Russkiy",

}

TRANSLATIONS = {
    "pt": {
        "overview": "Viso Geral", "send": "Enviar", "receive": "Receber",
        "transactions": "Transaes", "history": "Histrico", "refresh": " Atualizar",
        "network": "Rede",
        "start_mining": " Minerar", "stop_mining": " Parar",
        "balance": "Saldo:", "block": "Bloco", "difficulty": "Dificuldade",
        "next_diff": "Prxima dif", "peers": "Peers", "mempool": "Mempool",
        "reward": "Recompensa", "public_ip": "IP pblico", "pow": "PoW",
        "hashrate_net": "Hashrate rede", "hashrate_local": "Hashrate local",
        "your_wallet": "Sua carteira", "address": "Endereo:", "copy": "Copiar",
        "wif_mnemonic": "WIF/Mnemnico", "copy_p2p": "Copiar P2P",
        "password_on": " Senha ativa", "send_btcx": "Enviar DOGK",
        "dest_addr": "Endereo destino:", "amount": "Quantidade:", "fee": "Taxa:",
        "send_btn": "Enviar", "my_transactions": "Minhas transaes",
        "type": "Tipo", "value": "Valor", "conf": "Conf",
        "sent": "Enviado", "received": "Recebido", "block_num": "Bloco:",
        "show": "Mostrar", "last": "ltimo", "language": "Idioma",
        "copied": "Copiado!", "invalid_addr": "Endereo invlido.",
        "insufficient": "Saldo insuficiente.", "rejected": "Transao rejeitada.",
        "invalid_values": "Valores invlidos.", "added_mempool": "Transao adicionada ao mempool.",
        "tx_sent": "Transao enviada", "mining_started": "Minerao iniciada",
        "mining_stopped": "Minerao parada", "miner_on": "Minerador ligado",
        "miner_off": "Minerador desligado", "wallet_locked": " Carteira Bloqueada",
        "unlock_hint": "Digite a senha pra desbloquear:", "unlock_btn": "Desbloquear",
        "wrong_pass": "Senha incorreta.", "wait_sec": "Aguarde {s}s antes de tentar.",
        "never_share": "NUNCA compartilhe WIF ou palavras.",
        "copy_address": " COPIAR ENDEREO", "copy_wif": " COPIAR WIF",
        "copy_mnemonic": " COPIAR 12 PALAVRAS", "chain_id": "Chain ID",
        "meta_block": "Meta de bloco", "year_emission": "Emisso anual",
        "reward_block": "Recompensa/bloco", "network_events": "Eventos da rede",
        "copy_addr_ok": "Endereo copiado!", "copy_wif_ok": "WIF copiado!",
        "copy_mn_ok": "12 palavras copiadas!",
        "new_wallet": "Nova Carteira", "import_wif": "Importar WIF",
        "restore_mnemonic": "Restaurar 12 palavras",
        "show_wallet": "Mostrar Carteira / WIF / Mnemnico",
        "backup": "Backup da Carteira",
        "set_password": " Definir Senha", "remove_password": " Remover Senha",
        "change_password": " Trocar Senha", "exit": "Sair",
        "file_menu": "Arquivo", "settings_menu": "Configuraes",
        "help_menu": "Ajuda", "lang_menu": " Idioma",
        "connect_peer": "Conectar Peer", "sync_network": "Sincronizar Rede",
        "edit_seeds": "Editar Seeds", "about": "Sobre DogKong",
    },
    "en": {
        "overview": "Overview", "send": "Send", "receive": "Receive",
        "transactions": "Transactions", "history": "History", "refresh": " Refresh",
        "network": "Network",
        "start_mining": " Mine", "stop_mining": " Stop",
        "balance": "Balance:", "block": "Block", "difficulty": "Difficulty",
        "next_diff": "Next diff", "peers": "Peers", "mempool": "Mempool",
        "reward": "Reward", "public_ip": "Public IP", "pow": "PoW",
        "hashrate_net": "Network hashrate", "hashrate_local": "Local hashrate",
        "your_wallet": "Your wallet", "address": "Address:", "copy": "Copy",
        "wif_mnemonic": "WIF/Mnemonic", "copy_p2p": "Copy P2P",
        "password_on": " Password on", "send_btcx": "Send DOGK",
        "dest_addr": "Destination address:", "amount": "Amount:", "fee": "Fee:",
        "send_btn": "Send", "my_transactions": "My transactions",
        "type": "Type", "value": "Value", "conf": "Conf",
        "sent": "Sent", "received": "Received", "block_num": "Block:",
        "show": "Show", "last": "Last", "language": "Language",
        "copied": "Copied!", "invalid_addr": "Invalid address.",
        "insufficient": "Insufficient balance.", "rejected": "Transaction rejected.",
        "invalid_values": "Invalid values.", "added_mempool": "Transaction added to mempool.",
        "tx_sent": "Transaction sent", "mining_started": "Mining started",
        "mining_stopped": "Mining stopped", "miner_on": "Miner on",
        "miner_off": "Miner off", "wallet_locked": " Wallet Locked",
        "unlock_hint": "Enter password to unlock:", "unlock_btn": "Unlock",
        "wrong_pass": "Wrong password.", "wait_sec": "Wait {s}s before trying.",
        "never_share": "NEVER share WIF or words.",
        "copy_address": " COPY ADDRESS", "copy_wif": " COPY WIF",
        "copy_mnemonic": " COPY 12 WORDS", "chain_id": "Chain ID",
        "meta_block": "Block time", "year_emission": "Yearly emission",
        "reward_block": "Reward/block", "network_events": "Network events",
        "copy_addr_ok": "Address copied!", "copy_wif_ok": "WIF copied!",
        "copy_mn_ok": "12 words copied!",
        "new_wallet": "New Wallet", "import_wif": "Import WIF",
        "restore_mnemonic": "Restore 12 words",
        "show_wallet": "Show Wallet / WIF / Mnemonic",
        "backup": "Backup Wallet",
        "set_password": " Set Password", "remove_password": " Remove Password",
        "change_password": " Change Password", "exit": "Exit",
        "file_menu": "File", "settings_menu": "Settings",
        "help_menu": "Help", "lang_menu": " Language",
        "connect_peer": "Connect Peer", "sync_network": "Sync Network",
        "edit_seeds": "Edit Seeds", "about": "About DogKong",
    },
    "es": {
        "overview": "Vista General", "send": "Enviar", "receive": "Recibir",
        "transactions": "Transacciones", "history": "Historial", "refresh": " Actualizar",
        "network": "Red",
        "start_mining": " Minar", "stop_mining": " Parar",
        "balance": "Saldo:", "block": "Bloque", "difficulty": "Dificultad",
        "next_diff": "Prxima dif", "peers": "Pares", "mempool": "Mempool",
        "reward": "Recompensa", "public_ip": "IP pblico", "pow": "PoW",
        "hashrate_net": "Hashrate red", "hashrate_local": "Hashrate local",
        "your_wallet": "Tu cartera", "address": "Direccin:", "copy": "Copiar",
        "wif_mnemonic": "WIF/Mnemnico", "copy_p2p": "Copiar P2P",
        "password_on": " Contrasea activa", "send_btcx": "Enviar DOGK",
        "dest_addr": "Direccin destino:", "amount": "Cantidad:", "fee": "Comisin:",
        "send_btn": "Enviar", "my_transactions": "Mis transacciones",
        "type": "Tipo", "value": "Valor", "conf": "Conf",
        "sent": "Enviado", "received": "Recibido", "block_num": "Bloque:",
        "show": "Mostrar", "last": "ltimo", "language": "Idioma",
        "copied": "Copiado!", "invalid_addr": "Direccin invlida.",
        "insufficient": "Saldo insuficiente.", "rejected": "Rechazada.",
        "invalid_values": "Valores invlidos.", "added_mempool": "Aadido al mempool.",
        "tx_sent": "Enviado", "mining_started": "Minera iniciada",
        "mining_stopped": "Minera parada", "miner_on": "Minero encendido",
        "miner_off": "Minero apagado", "wallet_locked": " Cartera Bloqueada",
        "unlock_hint": "Contrasea:", "unlock_btn": "Desbloquear",
        "wrong_pass": "Contrasea incorrecta.", "wait_sec": "Espera {s}s.",
        "never_share": "NUNCA compartas WIF o palabras.",
        "copy_address": " COPIAR DIRECCIN", "copy_wif": " COPIAR WIF",
        "copy_mnemonic": " COPIAR 12 PALABRAS", "chain_id": "Chain ID",
        "meta_block": "Tiempo de bloque", "year_emission": "Emisin anual",
        "reward_block": "Recompensa/bloque", "network_events": "Eventos de red",
        "copy_addr_ok": "Direccin copiada!", "copy_wif_ok": "WIF copiado!",
        "copy_mn_ok": "12 palabras copiadas!",
        "new_wallet": "Nueva Cartera", "import_wif": "Importar WIF",
        "restore_mnemonic": "Restaurar 12 palabras",
        "show_wallet": "Mostrar Cartera / WIF / Mnemnico",
        "backup": "Backup de Cartera",
        "set_password": " Definir Contrasea", "remove_password": " Quitar Contrasea",
        "change_password": " Cambiar Contrasea", "exit": "Salir",
        "file_menu": "Archivo", "settings_menu": "Configuracin",
        "help_menu": "Ayuda", "lang_menu": " Idioma",
        "connect_peer": "Conectar Par", "sync_network": "Sincronizar Red",
        "edit_seeds": "Editar Seeds", "about": "Acerca de DogKong",
    },
    "zh": {
        "overview": "æ¦‚è§ˆ", "send": "å‘é€", "receive": "æŽ¥æ”¶",
        "transactions": "äº¤æ˜“åŽ†å²", "history": "åŒºå—åŽ†å²", "refresh": " åˆ·æ–°",
        "network": "ç½‘ç»œ",
        "start_mining": " å¼€å§‹æŒ–çŸ¿", "stop_mining": " åœæ­¢æŒ–çŸ¿",
        "balance": "ä½™é¢:", "block": "åŒºå—", "difficulty": "éš¾åº¦",
        "next_diff": "ä¸‹ä¸ªéš¾åº¦", "peers": "èŠ‚ç‚¹æ•°", "mempool": "äº¤æ˜“æ± ",
        "reward": "åŒºå—å¥–åŠ±", "public_ip": "å…¬ç½‘ IP", "pow": "å·¥ä½œé‡è¯æ˜Ž",
        "hashrate_net": "ç½‘ç»œç®—åŠ›", "hashrate_local": "æœ¬åœ°ç®—åŠ›",
        "your_wallet": "æ‚¨çš„é’±åŒ…", "address": "åœ°å€:",
        "copy": "å¤åˆ¶", "wif_mnemonic": "WIF/åŠ©è®°è¯", "copy_p2p": "å¤åˆ¶ P2P",
        "password_on": " å¯†ç å·²å¼€", "send_btcx": " å‘é€ DOGK",
        "dest_addr": "å‡ºåœ°å€:", "amount": "æ•°é‡:", "fee": "æ‰‹ç»­è´¹:",
        "send_btn": "å‘é€", "my_transactions": "æˆ‘çš„äº¤æ˜“",
        "type": "ç±»åž‹", "value": "ä»·å€¼", "conf": "ç¡®è®¤",
        "sent": "å·²å‘é€", "received": "å·²æŽ¥æ”¶", "block_num": "åŒºå—:",
        "show": "æ˜¾ç¤º", "last": "æœ€åŽ", "language": "è¯­è¨€",
        "copied": "å·²å¤åˆ¶!", "invalid_addr": "åœ°å€æ— æ•ˆ.",
        "insufficient": "ä½™é¢ä¸è¶³.", "rejected": "äº¤æ˜“è¢«æ‹’.",
        "invalid_values": "æ•°å€¼æ— æ•ˆ.", "added_mempool": "äº¤æ˜“å·²åŠ å…¥æ± .",
        "tx_sent": "äº¤æ˜“å·²å‘é€", "mining_started": "å¼€å§‹æŒ–çŸ¿",
        "mining_stopped": "æŒ–çŸ¿åœæ­¢", "miner_on": "æŒ–çŸ¿å¼€å¯",
        "miner_off": "æŒ–çŸ¿å…³é—­", "wallet_locked": " é’±åŒ…å·²é”",
        "unlock_hint": "è¾“å…¥å¯†ç è§£é”:", "unlock_btn": "è§£é”",
        "wrong_pass": "å¯†ç é”™è¯¯.", "wait_sec": "ç­‰ {s} ç§’åŽå†è¯•.",
        "never_share": "æ°¸è¿œä¸è¦åˆ†äº« WIF æˆ–å•è¯.",
        "copy_address": " å¤åˆ¶åœ°å€", "copy_wif": " å¤åˆ¶ WIF",
        "copy_mnemonic": " å¤åˆ¶ 12 ä¸ªå•è¯", "chain_id": "Chain ID",
        "meta_block": "åŒºå—æ—¶é—´", "year_emission": "å‘è¡Œé‡",
        "reward_block": "åŒºå—å¥–åŠ±", "network_events": "ç½‘ç»œäº‹ä»¶",
        "copy_addr_ok": "åœ°å€å·²å¤åˆ¶!", "copy_wif_ok": "WIF å·²å¤åˆ¶!",
        "copy_mn_ok": "12 ä¸ªå•è¯å·²å¤åˆ¶!",
        "new_wallet": "æ–°é’±åŒ…", "import_wif": "å¯¼å…¥ WIF",
        "restore_mnemonic": "æ¢å¤ 12 ä¸ªå•è¯",
        "show_wallet": "æ˜¾ç¤º é’±åŒ… / WIF / åŠ©è®°è¯",
        "backup": "å¤‡ä»½é’±åŒ…",
        "set_password": " è®¾ç½®å¯†ç ", "remove_password": " ç§»é™¤å¯†ç ",
        "change_password": " æ›´æ¢å¯†ç ", "exit": "é€€å‡º",
        "file_menu": "æ–‡ä»¶", "settings_menu": "è®¾ç½®",
        "help_menu": "å¸®åŠ©", "lang_menu": " è¯­è¨€",
        "connect_peer": "è¿žæŽ¥èŠ‚ç‚¹", "sync_network": "åŒæ­¥ç½‘ç»œ",
        "edit_seeds": "ç¼–è¾‘ç§å­", "about": "å…³äºŽ DogKong",
    },
    "ru": {
        "overview": "ÐžÐ±Ð·Ð¾Ñ€", "send": "ÐžÑ‚Ð¿Ñ€Ð°Ð²Ð¸Ñ‚ÑŒ", "receive": "ÐŸÐ¾Ð»ÑƒÑ‡Ð¸Ñ‚ÑŒ",
        "transactions": "Ð¢Ñ€Ð°Ð½Ð·Ð°ÐºÑ†Ð¸Ð¸", "history": "Ð˜ÑÑ‚Ð¾Ñ€Ð¸Ñ", "refresh": " ÐžÐ±Ð½Ð¾Ð²Ð¸Ñ‚ÑŒ",
        "network": "Ð¡ÐµÑ‚ÑŒ",
        "start_mining": " ÐœÐ°Ð¹Ð½Ð¸Ñ‚ÑŒ", "stop_mining": " Ð¡Ñ‚Ð¾Ð¿",
        "balance": "Ð‘Ð°Ð»Ð°Ð½Ñ:", "block": "Ð‘Ð»Ð¾Ðº", "difficulty": "Ð¡Ð»Ð¾Ð¶Ð½Ð¾ÑÑ‚ÑŒ",
        "next_diff": "Ð¡Ð»ÐµÐ´. ÑÐ»Ð¾Ð¶Ð½.", "peers": "ÐŸÐ¸Ñ€Ñ‹", "mempool": "ÐœÐµÐ¼Ð¿ÑƒÐ»",
        "reward": "ÐÐ°Ð³Ñ€Ð°Ð´Ð°", "public_ip": "ÐŸÑƒÐ±Ð»Ð¸Ñ‡Ð½Ñ‹Ð¹ IP", "pow": "PoW",
        "hashrate_net": "Ð¥ÑÑˆÑ€ÐµÐ¹Ñ‚ ÑÐµÑ‚Ð¸", "hashrate_local": "Ð¥ÑÑˆÑ€ÐµÐ¹Ñ‚ Ð½Ð¾Ð´Ð°",
        "your_wallet": "Ð’Ð°Ñˆ ÐºÐ¾ÑˆÐµÐ»ÐµÐº", "address": "ÐÐ´Ñ€ÐµÑ:",
        "copy": "ÐšÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ", "wif_mnemonic": "WIF/ÐœÐ½ÐµÐ¼Ð¾Ð½Ð¸ÐºÐ°", "copy_p2p": "ÐšÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ P2P",
        "password_on": " ÐŸÐ°Ñ€Ð¾Ð»ÑŒ Ð°ÐºÑ‚Ð¸Ð²ÐµÐ½", "send_btcx": " ÐžÑ‚Ð¿Ñ€Ð°Ð²Ð¸Ñ‚ÑŒ DOGK",
        "dest_addr": "ÐÐ´Ñ€ÐµÑ Ð½Ð°Ð·Ð½Ð°Ñ‡ÐµÐ½Ð¸Ñ:", "amount": "Ð¡ÑƒÐ¼Ð¼Ð°:", "fee": "ÐšÐ¾Ð¼Ð¸ÑÑÐ¸Ñ:",
        "send_btn": "ÐžÑ‚Ð¿Ñ€Ð°Ð²Ð¸Ñ‚ÑŒ", "my_transactions": "ÐœÐ¾Ð¸ Ñ‚Ñ€Ð°Ð½Ð·Ð°ÐºÑ†Ð¸Ð¸",
        "type": "Ð¢Ð¸Ð¿", "value": "Ð—Ð½Ð°Ñ‡ÐµÐ½Ð¸Ðµ", "conf": "ÐŸÐ¾Ð´Ñ‚Ð²ÐµÑ€Ð¶Ð´ÐµÐ½Ð¸Ðµ",
        "sent": "ÐžÑ‚Ð¿Ñ€Ð°Ð²Ð»ÐµÐ½Ð¾", "received": "ÐŸÐ¾Ð»ÑƒÑ‡ÐµÐ½Ð¾", "block_num": "Ð‘Ð»Ð¾Ðº:",
        "show": "ÐŸÐ¾ÐºÐ°Ð·Ð°Ñ‚ÑŒ", "last": "ÐŸÐ¾ÑÐ»ÐµÐ´Ð½Ð¸Ð¹", "language": "Ð¯Ð·Ñ‹Ðº",
        "copied": "Ð¡ÐºÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ð½Ð¾!", "invalid_addr": "ÐÐµÐ²ÐµÑ€Ð½Ñ‹Ð¹ Ð°Ð´Ñ€ÐµÑ.",
        "insufficient": "ÐÐµÐ´Ð¾ÑÑ‚Ð°Ñ‚Ð¾Ñ‡Ð½Ð¾ ÑÑ€ÐµÐ´ÑÑ‚Ð².", "rejected": "Ð¢Ñ€Ð°Ð½Ð·Ð°ÐºÑ†Ð¸Ñ Ð¾Ñ‚ÐºÐ»Ð¾Ð½ÐµÐ½Ð°.",
        "invalid_values": "ÐÐµÐ²ÐµÑ€Ð½Ñ‹Ðµ Ð·Ð½Ð°Ñ‡ÐµÐ½Ð¸Ñ.", "added_mempool": "Ð¢Ñ€Ð°Ð½Ð·Ð°ÐºÑ†Ð¸Ñ Ð´Ð¾Ð±Ð°Ð²Ð»ÐµÐ½Ð° Ð² Ð¼ÐµÐ¼Ð¿ÑƒÐ».",
        "tx_sent": "Ð¢Ñ€Ð°Ð½Ð·Ð°ÐºÑ†Ð¸Ñ Ð¾Ñ‚Ð¿Ñ€Ð°Ð²Ð»ÐµÐ½Ð°", "mining_started": "ÐœÐ°Ð¹Ð½Ð¸Ð½Ð³ Ð½Ð°Ñ‡Ð°Ñ‚",
        "mining_stopped": "ÐœÐ°Ð¹Ð½Ð¸Ð½Ð³ Ð¾ÑÑ‚Ð°Ð½Ð¾Ð²Ð»ÐµÐ½", "miner_on": "ÐœÐ°Ð¹Ð½ÐµÑ€ Ð²ÐºÐ»",
        "miner_off": "ÐœÐ°Ð¹Ð½ÐµÑ€ Ð²Ñ‹ÐºÐ»", "wallet_locked": " ÐšÐ¾ÑˆÐµÐ»ÐµÐº Ð·Ð°Ð±Ð»Ð¾ÐºÐ¸Ñ€Ð¾Ð²Ð°Ð½",
        "unlock_hint": "Ð’Ð²ÐµÐ´Ð¸Ñ‚Ðµ Ð¿Ð°Ñ€Ð¾Ð»ÑŒ:", "unlock_btn": "Ð Ð°Ð·Ð±Ð»Ð¾ÐºÐ¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ",
        "wrong_pass": "ÐÐµÐ²ÐµÑ€Ð½Ñ‹Ð¹ Ð¿Ð°Ñ€Ð¾Ð»ÑŒ.", "wait_sec": "ÐŸÐ¾Ð´Ð¾Ð¶Ð´Ð¸Ñ‚Ðµ {s} ÑÐµÐº.",
        "never_share": "ÐÐ¸ÐºÐ¾Ð³Ð´Ð° Ð½Ðµ Ð´ÐµÐ»Ð¸Ñ‚ÐµÑÑŒ WIF Ð¸Ð»Ð¸ ÑÐ»Ð¾Ð²Ð°Ð¼Ð¸.",
        "copy_address": " ÐšÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ Ð°Ð´Ñ€ÐµÑ", "copy_wif": " ÐšÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ WIF",
        "copy_mnemonic": " ÐšÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ 12 ÑÐ»Ð¾Ð²", "chain_id": "ID Ñ†ÐµÐ¿Ð¸",
        "meta_block": "Ð’Ñ€ÐµÐ¼Ñ Ð±Ð»Ð¾ÐºÐ°", "year_emission": "Ð“Ð¾Ð´Ð¾Ð²Ð°Ñ ÑÐ¼Ð¸ÑÑÐ¸Ñ",
        "reward_block": "ÐÐ°Ð³Ñ€Ð°Ð´Ð°/Ð±Ð»Ð¾Ðº", "network_events": "Ð¡Ð¾Ð±Ñ‹Ñ‚Ð¸Ñ ÑÐµÑ‚Ð¸",
        "copy_addr_ok": "ÐÐ´Ñ€ÐµÑ ÑÐºÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ð½!", "copy_wif_ok": "WIF ÑÐºÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ð½!",
        "copy_mn_ok": "12 ÑÐ»Ð¾Ð² ÑÐºÐ¾Ð¿Ð¸Ñ€Ð¾Ð²Ð°Ð½Ð¾!",
        "new_wallet": "ÐÐ¾Ð²Ñ‹Ð¹ ÐºÐ¾ÑˆÐµÐ»ÐµÐº", "import_wif": "Ð˜Ð¼Ð¿Ð¾Ñ€Ñ‚ WIF",
        "restore_mnemonic": "Ð’Ð¾ÑÑÑ‚Ð°Ð½Ð¾Ð²Ð¸Ñ‚ÑŒ 12 ÑÐ»Ð¾Ð²",
        "show_wallet": "ÐŸÐ¾ÐºÐ°Ð·Ð°Ñ‚ÑŒ ÐºÐ¾ÑˆÐµÐ»ÐµÐº / WIF / ÐœÐ½ÐµÐ¼Ð¾Ð½Ð¸ÐºÑƒ",
        "backup": "Ð‘ÑÐºÐ°Ð¿ ÐºÐ¾ÑˆÐµÐ»ÑŒÐºÐ°",
        "set_password": " Ð£ÑÑ‚Ð°Ð½Ð¾Ð²Ð¸Ñ‚ÑŒ Ð¿Ð°Ñ€Ð¾Ð»ÑŒ", "remove_password": " Ð£Ð´Ð°Ð»Ð¸Ñ‚ÑŒ Ð¿Ð°Ñ€Ð¾Ð»ÑŒ",
        "change_password": " Ð¡Ð¼ÐµÐ½Ð¸Ñ‚ÑŒ Ð¿Ð°Ñ€Ð¾Ð»ÑŒ", "exit": "Ð’Ñ‹Ñ…Ð¾Ð´",
        "file_menu": "Ð¤Ð°Ð¹Ð»", "settings_menu": "ÐÐ°ÑÑ‚Ñ€Ð¾Ð¹ÐºÐ¸",
        "help_menu": "ÐŸÐ¾Ð¼Ð¾Ñ‰ÑŒ", "lang_menu": " Ð¯Ð·Ñ‹Ðº",
        "connect_peer": "ÐŸÐ¾Ð´ÐºÐ»ÑŽÑ‡Ð¸Ñ‚ÑŒ Ð¿Ð¸Ñ€", "sync_network": "Ð¡Ð¸Ð½Ñ…Ñ€Ð¾Ð½Ð¸Ð·Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ ÑÐµÑ‚ÑŒ",
        "edit_seeds": "Ð ÐµÐ´Ð°ÐºÑ‚Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ ÑÐµÐ¼ÐµÐ½Ð°", "about": "Ðž DogKong",
    },
}

LANG = "en"


def t(key):
    return TRANSLATIONS.get(LANG, TRANSLATIONS["pt"]).get(key, key)


def load_lang():
    global LANG
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as f:
            l = f.read().strip()
        if l in LANGUAGES:
            LANG = l
    except:
        pass


def save_lang():
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            f.write(LANG)
    except:
        pass


load_lang()


# ============================================================
# NCLEO DE DIFICULDADE  BITS/TARGET ESTILO BITCOIN + LWMA
# ============================================================
def target_para_bits(target):
    """Implementacao correta (Bitcoin Core)."""
    if target > TARGET_MAX_BTC:
        target = TARGET_MAX_BTC
    if target < 1:
        target = 1
    nbits = target.bit_length()
    if nbits <= 3:
        exp = 3
        mant = target << (8 * (3 - nbits))
    else:
        exp = (nbits + 7) // 8
        mant = target >> (8 * (exp - 3))
    if mant & 0x800000:
        mant >>= 8
        exp += 1
    return (exp << 24) | (mant & 0xFFFFFF)


def bits_para_target(bits):
    """Implementacao correta (Bitcoin Core)."""
    exp = bits >> 24
    mant = bits & 0xFFFFFF
    if exp <= 3:
        return mant >> (8 * (3 - exp))
    else:
        return mant << (8 * (exp - 3))


def _calcular_antigo(chain, candidate_time=None):
    """
    DogKong - dificuldade deterministica estilo Bitcoin

    REGRA NORMAL:
      - Retarget a cada 100 blocos (100, 200, 300...)
      - Janela de 101 blocos = 100 intervalos
      - Alvo: 60 segundos por bloco
      - Ajuste limitado a 4x (Bitcoin style)
      - Matematica 100% inteira (sem float)

    REGRA DE EMERGENCIA:
      - Se passar mais de 150 segundos sem bloco
      - Dificuldade cai 2x (nao 1000x)
      - Maximo 1 emergencia a cada 10 blocos
      - Nao usa relogio local - deterministico
    """

    altura = len(chain)

    if altura == 0:
        return INITIAL_DIFFICULTY

    ultimo = chain[-1]
    ultimo_bits = int(ultimo.get("bits", INITIAL_DIFFICULTY))
    ultimo_time = int(ultimo.get("time", 0))

    bits_minimos = target_para_bits(TARGET_MAX_BTC)

    # =========================================================
    # 1. RETARGET A CADA 100 BLOCOS
    # =========================================================

    if altura >= 101 and altura % 100 == 0:

        janela = chain[-101:]

        if len(janela) != 101:
            return ultimo_bits

        try:
            t_first = int(janela[0]["time"])
            t_last = int(janela[-1]["time"])
        except (KeyError, TypeError, ValueError):
            return ultimo_bits

        tempo_real = t_last - t_first
        tempo_esperado = 100 * BLOCK_TIME

        if tempo_real <= 0:
            return ultimo_bits

        target_atual = bits_para_target(ultimo_bits)
        if target_atual <= 0:
            return ultimo_bits

        novo_target = (target_atual * tempo_real) // tempo_esperado

        max_target = target_atual * 4
        min_target = target_atual // 4

        if novo_target > max_target:
            novo_target = max_target
        elif novo_target < min_target:
            novo_target = min_target

        if novo_target < 1:
            novo_target = 1
        if novo_target > TARGET_MAX_BTC:
            novo_target = TARGET_MAX_BTC

        try:
            novo_bits = target_para_bits(novo_target)
        except (TypeError, ValueError, OverflowError):
            return ultimo_bits

        if int(novo_bits) <= 0:
            return ultimo_bits

        return int(novo_bits)

    # =========================================================
    # 2. EMERGENCIA SUAVE (150s+ sem bloco)
    # =========================================================

    if candidate_time is not None:

        candidate_time = int(candidate_time)

        if candidate_time < ultimo_time:
            return ultimo_bits

        atraso = candidate_time - ultimo_time
        STALL_LIMIT = 150

        if atraso > STALL_LIMIT:

            # Anti-loop: verifica se ultimos 10 blocos tiveram emergencia
            ja_teve_emergencia_recente = False
            lookback = min(10, len(chain))
            for j in range(1, lookback + 1):
                b_check = chain[-j]
                bits_check = int(b_check.get("bits", INITIAL_DIFFICULTY))
                if bits_check != ultimo_bits:
                    target_check = bits_para_target(bits_check)
                    target_normal = bits_para_target(ultimo_bits)
                    if target_check > target_normal:
                        ja_teve_emergencia_recente = True
                        break

            if ja_teve_emergencia_recente:
                return ultimo_bits

            target_atual = bits_para_target(ultimo_bits)
            novo_target = target_atual * 2

            if novo_target < 1:
                novo_target = 1
            if novo_target > TARGET_MAX_BTC:
                novo_target = TARGET_MAX_BTC

            bits_emergencia = target_para_bits(novo_target)

            if bits_emergencia == bits_minimos:
                return bits_minimos

            return bits_emergencia

    # =========================================================
    # 3. ENTRE AJUSTES: MANTEM
    # =========================================================

    return ultimo_bits


# ============================================================
# LWMA REAL (Zawy's LWMA-3) - a partir do bloco LWMA_START_HEIGHT
# Ajusta a dificuldade A CADA BLOCO usando media ponderada.
# Aguenta de 2 a 100k mineradores sem mexer.
# ============================================================
LWMA_WINDOW = 60   # janela de 60 blocos

def calcular_dificuldade_alvo(chain, candidate_time=None):
    """
    Se chain < LWMA_START_HEIGHT -> usa calculo antigo (compativel)
    Senao -> LWMA real (ajuste por bloco)
    """
    altura = len(chain)
    if altura < LWMA_START_HEIGHT:
        return _calcular_antigo(chain, candidate_time)

    # LWMA real
    N = LWMA_WINDOW
    if len(chain) < N + 2:
        if len(chain) < 1:
            return INITIAL_DIFFICULTY
        return int(chain[-1].get("bits", INITIAL_DIFFICULTY))

    janela = chain[-(N + 1):]
    if len(janela) != N + 1:
        return int(chain[-1].get("bits", INITIAL_DIFFICULTY))

    ultimo_bits = int(janela[-1].get("bits", INITIAL_DIFFICULTY))
    target_atual = bits_para_target(ultimo_bits)
    if target_atual <= 0:
        return ultimo_bits

    soma_pesos = 0
    soma_deltas_ponderados = 0

    T = BLOCK_TIME
    T_MIN = 1
    T_MAX = T * 6

    for i in range(1, N + 1):
        try:
            t_prev = int(janela[i - 1]["time"])
            t_curr = int(janela[i]["time"])
        except (KeyError, TypeError, ValueError):
            return ultimo_bits

        delta = t_curr - t_prev
        if delta < T_MIN:
            delta = T_MIN
        elif delta > T_MAX:
            delta = T_MAX

        soma_pesos += i
        soma_deltas_ponderados += delta * i

    if soma_pesos == 0:
        return ultimo_bits

    media_ponderada = soma_deltas_ponderados // soma_pesos
    if media_ponderada <= 0:
        media_ponderada = 1

    # EMERGENCIA: se candidate_time passou 150s+ do ultimo bloco, cai 2x
    if candidate_time is not None:
        ultimo_time = int(janela[-1].get("time", 0))
        candidate_time = int(candidate_time)
        if candidate_time > ultimo_time:
            atraso = candidate_time - ultimo_time
            if atraso > 150:
                # Cai 2x
                novo_target = target_atual * 2
                if novo_target > TARGET_MAX_BTC:
                    novo_target = TARGET_MAX_BTC
                try:
                    novo_bits = target_para_bits(novo_target)
                    return int(novo_bits)
                except Exception:
                    return ultimo_bits

    novo_target = (target_atual * media_ponderada) // T

    max_target = target_atual * 2
    min_target = target_atual // 2

    if novo_target > max_target:
        novo_target = max_target
    elif novo_target < min_target:
        novo_target = min_target

    if novo_target < 1:
        novo_target = 1
    if novo_target > TARGET_MAX_BTC:
        novo_target = TARGET_MAX_BTC

    try:
        novo_bits = target_para_bits(novo_target)
    except (TypeError, ValueError, OverflowError):
        return ultimo_bits

    if int(novo_bits) <= 0:
        return ultimo_bits

    return int(novo_bits)


def estimar_hashrate_rede(chain, initial_bits=INITIAL_DIFFICULTY):
    """Estima hashrate (H/s) pela frmula do Bitcoin: 2^256 / target / BLOCK_TIME."""
    if len(chain) < 2:
        return 0.0
    ultimo_bits = int(chain[-1].get("bits", initial_bits))
    target = bits_para_target(ultimo_bits)
    if target <= 0:
        return 0.0
    hashes_estimados = (2 ** 256) / target
    return hashes_estimados / BLOCK_TIME


# ============================================================
# UTILITRIOS DE HASH
# ============================================================
def sha256(b): return hashlib.sha256(b).digest()
def sha256d(b): return sha256(sha256(b))
def h(b): return hashlib.sha256(b).hexdigest()
def now(): return int(time.time())


def fechar_socket_seguro(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    try:
        sock.close()
    except Exception:
        pass


class PersistError(Exception):
    pass


def save_json(path, obj):
    tmp = path + ".tmp"
    bak = path + ".bak"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise PersistError("Falha ao gravar " + tmp + ": " + str(e))

    try:
        if os.path.exists(path):
            shutil.copy2(path, bak)
    except Exception:
        pass

    try:
        os.replace(tmp, path)
    except Exception as e:
        raise PersistError("Falha ao renomear " + tmp + " -> " + path + ": " + str(e))


def load_json(path, default=None, critical=False):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e1:
        bak = path + ".bak"
        if os.path.exists(bak):
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print("[DOGK] Aviso: " + path + " corrompido; recuperado do .bak")
                return data
            except Exception as e2:
                if critical:
                    raise PersistError(path + " corrompido e backup tambem falhou.")
                return default
        else:
            if critical:
                raise PersistError(path + " corrompido e sem backup .bak.")
            return default


def detect_public_ip():
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                ip = r.read().decode().strip()
                if ip and len(ip) <= 45:
                    return ip
        except Exception:
            continue
    return None


# ============================================================
# BIP39
# ============================================================
BIP39_WORDS = [
"abandon","ability","able","about","above","absent","absorb","abstract","absurd","abuse",
"access","accident","account","accuse","achieve","acid","acoustic","acquire","across","act",
"action","actor","actress","actual","adapt","add","addict","address","adjust","admit",
"adult","advance","advice","aerobic","affair","afford","afraid","again","age","agent",
"agree","ahead","aim","air","airport","aisle","alarm","album","alcohol","alert",
"alien","all","alley","allow","almost","alone","alpha","already","also","alter",
"always","amateur","amazing","among","amount","amused","analyst","anchor","ancient","anger",
"angle","angry","animal","ankle","announce","annual","another","answer","antenna","antique",
"anxiety","any","apart","apology","appear","apple","approve","april","arch","arctic",
"area","arena","argue","arm","armed","armor","army","around","arrange","arrest",
"arrive","arrow","art","artefact","artist","artwork","ask","aspect","assault","asset",
"assist","assume","asthma","athlete","atom","attack","attend","attitude","attract","auction",
"audit","august","aunt","author","auto","autumn","average","avocado","avoid","awake",
"aware","away","awesome","awful","awkward","axis","baby","bachelor","bacon","badge",
"bag","balance","balcony","ball","bamboo","banana","banner","bar","barely","bargain",
"barrel","base","basic","basket","battle","beach","bean","beauty","because","become",
"beef","before","begin","behave","behind","believe","below","belt","bench","benefit",
"best","betray","better","between","beyond","bicycle","bid","bike","bind","biology",
"bird","birth","bitter","black","blade","blame","blanket","blast","bleak","bless",
"blind","blood","blossom","blouse","blue","blur","blush","board","boat","body",
"boil","bomb","bone","bonus","book","boost","border","boring","borrow","boss",
"bottom","bounce","box","boy","bracket","brain","brand","brass","brave","bread",
"breeze","brick","bridge","brief","bright","bring","brisk","broccoli","broken","bronze",
"broom","brother","brown","brush","bubble","buddy","budget","buffalo","build","bulb",
"bulk","bullet","bundle","bunker","burden","burger","burst","bus","business","busy",
"butter","buyer","buzz","cabbage","cabin","cable","cactus","cage","cake","call",
"calm","camera","camp","can","canal","cancel","candy","cannon","canoe","canvas",
"canyon","capable","capital","captain","car","carbon","card","cargo","carpet","carry",
"cart","case","cash","casino","castle","casual","cat","catalog","catch","category",
"cattle","caught","cause","caution","cave","ceiling","celery","cement","census","century",
"cereal","certain","chair","chalk","champion","change","chaos","chapter","charge","chase",
"chat","cheap","check","cheese","chef","cherry","chest","chicken","chief","child",
"chimney","choice","choose","chronic","chuckle","chunk","churn","cigar","cinnamon","circle",
"citizen","city","civil","claim","clap","clarify","claw","clay","clean","clerk",
"clever","click","client","cliff","climb","clinic","clip","clock","clog","close",
"cloth","cloud","clown","club","clump","cluster","clutch","coach","coast","coconut",
"code","coffee","coil","coin","collect","color","column","combine","come","comfort",
"comic","common","company","concert","conduct","confirm","congress","connect","consider","control",
"convince","cook","cool","copper","copy","coral","core","corn","correct","cost",
"cotton","couch","country","couple","course","cousin","cover","coyote","crack","cradle",
"craft","cram","crane","crash","crater","crawl","crazy","cream","credit","creek",
"crew","cricket","crime","crisp","critic","crop","cross","crouch","crowd","crucial",
"cruel","cruise","crumble","crunch","crush","cry","crystal","cube","culture","cup",
"cupboard","curious","current","curtain","curve","cushion","custom","cute","cycle","dad",
"damage","damp","dance","danger","daring","dash","daughter","dawn","day","deal",
"debate","debris","decade","december","decide","decline","decorate","decrease","deer","defense",
"define","defy","degree","delay","deliver","demand","demise","denial","dentist","deny",
"depart","depend","deposit","depth","deputy","derive","describe","desert","design","desk",
"despair","destroy","detail","detect","develop","device","devote","diagram","dial","diamond",
"diary","dice","diesel","diet","differ","digital","dignity","dilemma","dinner","dinosaur",
"direct","dirt","disagree","discover","disease","dish","dismiss","disorder","display","distance",
"divert","divide","divorce","dizzy","doctor","document","dog","doll","dolphin","domain",
"donate","donkey","donor","door","dose","double","dove","draft","dragon","drama",
"drastic","draw","dream","dress","drift","drill","drink","drip","drive","drop",
"drum","dry","duck","dumb","dune","during","dust","dutch","duty","dwarf",
"dynamic","eager","eagle","early","earn","earth","easily","east","easy","echo",
"ecology","economy","edge","edit","educate","effort","egg","eight","either","elbow",
"elder","electric","elegant","element","elephant","elevator","elite","else","embark","embody",
"embrace","emerge","emotion","employ","empower","empty","enable","enact","end","endless",
"endorse","enemy","energy","enforce","engage","engine","enhance","enjoy","enlist","enough",
"enrich","enroll","ensure","enter","entire","entry","envelope","episode","equal","equip",
"era","erase","erode","erosion","error","erupt","escape","essay","essence","estate",
"eternal","ethics","evidence","evil","evoke","evolve","exact","example","excess","exchange",
"excite","exclude","excuse","execute","exercise","exhaust","exhibit","exile","exist","exit",
"exotic","expand","expect","expire","explain","expose","express","extend","extra","eye",
"eyebrow","fabric","face","faculty","fade","faint","faith","fall","false","fame",
"family","famous","fan","fancy","fantasy","farm","fashion","fat","fatal","father",
"fatigue","fault","favorite","feature","february","federal","fee","feed","feel","female",
"fence","festival","fetch","fever","few","fiber","fiction","field","figure","file",
"film","filter","final","find","fine","finger","finish","fire","firm","first",
"fiscal","fish","fit","fitness","fix","flag","flame","flash","flat","flavor",
"flee","flight","flip","float","flock","floor","flower","fluid","flush","fly",
"foam","focus","fog","foil","fold","follow","food","foot","force","forest",
"forget","fork","fortune","forum","forward","fossil","foster","found","fox","fragile",
"frame","frequent","fresh","friend","fringe","frog","front","frost","frown","frozen",
"fruit","fuel","fun","funny","furnace","fury","future","gadget","gain","galaxy",
"gallery","game","gap","garage","garbage","garden","garlic","garment","gas","gasp",
"gate","gather","gauge","gaze","general","genius","genre","gentle","genuine","gesture",
"ghost","giant","gift","giggle","ginger","giraffe","girl","give","glad","glance",
"glare","glass","glide","glimpse","globe","gloom","glory","glove","glow","glue",
"goat","goddess","gold","good","goose","gorilla","gospel","gossip","govern","gown",
"grab","grace","grain","grant","grape","grass","gravity","great","green","grid",
"grief","grit","grocery","group","grow","grunt","guard","guess","guide","guilt",
"guitar","gun","gym","habit","hair","half","hammer","hamster","hand","happy",
"harbor","hard","harsh","harvest","hat","have","hawk","hazard","head","health",
"heart","heavy","hedgehog","height","hello","helmet","help","hen","hero","hidden",
"high","hill","hint","hip","hire","history","hobby","hockey","hold","hole",
"holiday","hollow","home","honey","hood","hope","horn","horror","horse","hospital",
"host","hotel","hour","hover","hub","huge","human","humble","humor","hundred",
"hungry","hunt","hurdle","hurry","hurt","husband","hybrid","ice","icon","idea",
"identify","idle","ignore","ill","illegal","illness","image","imitate","immense","immune",
"impact","impose","improve","impulse","inch","include","income","increase","index","indicate",
"indoor","industry","infant","inflict","inform","inhale","inherit","initial","inject","injury",
"inmate","inner","innocent","input","inquiry","insane","insect","inside","inspire","install",
"intact","interest","into","invest","invite","involve","iron","island","isolate","issue",
"item","ivory","jacket","jaguar","jar","jazz","jealous","jeans","jelly","jewel",
"job","join","joke","journey","joy","judge","juice","jump","jungle","junior",
"junk","just","kangaroo","keen","keep","ketchup","key","kick","kid","kidney",
"kind","kingdom","kiss","kit","kitchen","kite","kitten","kiwi","knee","knife",
"knock","know","lab","label","labor","ladder","lady","lake","lamp","language",
"laptop","large","later","latin","laugh","laundry","lava","law","lawn","lawsuit",
"layer","lazy","leader","leaf","learn","leave","lecture","left","leg","legal",
"legend","leisure","lemon","lend","length","lens","leopard","lesson","letter","level",
"liar","liberty","library","license","life","lift","light","like","limb","limit",
"link","lion","liquid","list","little","live","lizard","load","loan","lobster",
"local","lock","logic","lonely","long","loop","lottery","loud","lounge","love",
"loyal","lucky","luggage","lumber","lunar","lunch","luxury","lyrics","machine","mad",
"magic","magnet","maid","mail","main","major","make","mammal","man","manage",
"mandate","mango","mansion","manual","maple","marble","march","margin","marine","market",
"marriage","mask","mass","master","match","material","math","matrix","matter","maximum",
"maze","meadow","mean","measure","meat","mechanic","medal","media","melody","melt",
"member","memory","mention","menu","mercy","merge","merit","merry","mesh","message",
"metal","method","middle","midnight","milk","million","mimic","mind","minimum","minor",
"minute","miracle","mirror","misery","miss","mistake","mix","mixed","mixture","mobile",
"model","modify","mom","moment","monitor","monkey","monster","month","moon","moral",
"more","morning","mosquito","mother","motion","motor","mountain","mouse","move","movie",
"much","muffin","mule","multiply","muscle","museum","mushroom","music","must","mutual",
"myself","mystery","myth","naive","name","napkin","narrow","nasty","nation","nature",
"near","neck","need","negative","neglect","neither","nephew","nerve","nest","net",
"network","neutral","never","news","next","nice","night","noble","noise","nominee",
"noodle","normal","north","nose","notable","note","nothing","notice","novel","now",
"nuclear","number","nurse","nut","oak","obey","object","oblige","obscure","observe",
"obtain","obvious","occur","ocean","october","odor","off","offer","office","often",
"oil","okay","old","olive","olympic","omit","once","one","onion","online",
"only","open","opera","opinion","oppose","option","orange","orbit","orchard","order",
"ordinary","organ","orient","original","orphan","ostrich","other","outdoor","outer","output",
"outside","oval","oven","over","own","owner","oxygen","oyster","ozone","pact",
"paddle","page","pair","palace","palm","panda","panel","panic","panther","paper",
"parade","parent","park","parrot","party","pass","patch","path","patient","patrol",
"pattern","pause","pave","payment","peace","peanut","pear","peasant","pelican","pen",
"penalty","pencil","people","pepper","perfect","permit","person","pet","phone","photo",
"phrase","physical","piano","picnic","picture","piece","pig","pigeon","pill","pilot",
"pink","pioneer","pipe","pistol","pitch","pizza","place","planet","plastic","plate",
"play","please","pledge","pluck","plug","plunge","poem","poet","point","polar",
"pole","police","pond","pony","pool","popular","portion","position","possible","post",
"potato","pottery","poverty","powder","power","practice","praise","predict","prefer","prepare",
"present","pretty","prevent","price","pride","primary","print","priority","prison","private",
"prize","problem","process","produce","profit","program","project","promote","proof","property",
"prosper","protect","proud","provide","public","pudding","pull","pulp","pulse","pumpkin",
"punch","pupil","puppy","purchase","purity","purpose","purse","push","put","puzzle",
"pyramid","quality","quantum","quarter","question","quick","quit","quiz","quote","rabbit",
"raccoon","race","rack","radar","radio","rail","rain","raise","rally","ramp",
"ranch","random","range","rapid","rare","rate","rather","raven","raw","razor",
"ready","real","reason","rebel","rebuild","recall","receive","recipe","record","recycle",
"reduce","reflect","reform","refuse","region","regret","regular","reject","relax","release",
"relief","rely","remain","remember","remind","remove","render","renew","rent","reopen",
"repair","repeat","replace","report","require","rescue","resemble","resist","resource","response",
"result","retire","retreat","return","reunion","reveal","review","reward","rhythm","rib",
"ribbon","rice","rich","ride","ridge","rifle","right","rigid","ring","riot",
"ripple","risk","ritual","rival","river","road","roast","robot","robust","rocket",
"romance","roof","rookie","room","rose","rotate","rough","round","route","royal",
"rubber","rude","rug","rule","run","runway","rural","sad","saddle","sadness",
"safe","sail","salad","salmon","salon","salt","salute","same","sample","sand",
"satisfy","satoshi","sauce","sausage","save","say","scale","scan","scare","scatter",
"scene","scheme","school","science","scissors","scorpion","scout","scrap","screen","script",
"scrub","sea","search","season","seat","second","secret","section","security","seed",
"seek","segment","select","sell","seminar","senior","sense","sentence","series","service",
"session","settle","setup","seven","shadow","shaft","shallow","share","shed","shell",
"sheriff","shield","shift","shine","ship","shiver","shock","shoe","shoot","shop",
"short","shoulder","shove","shrimp","shrug","shuffle","shy","sibling","sick","side",
"siege","sight","sign","silent","silk","silly","silver","similar","simple","since",
"sing","siren","sister","situate","six","size","skate","sketch","ski","skill",
"skin","skirt","skull","slab","slam","sleep","slender","slice","slide","slight",
"slim","slogan","slot","slow","slush","small","smart","smile","smoke","smooth",
"snack","snake","snap","sniff","snow","soap","soccer","social","sock","soda",
"soft","solar","soldier","solid","solution","solve","someone","song","soon","sorry",
"sort","soul","sound","soup","source","south","space","spare","spatial","spawn",
"speak","special","speed","spell","spend","sphere","spice","spider","spike","spin",
"spirit","split","spoil","sponsor","spoon","sport","spot","spray","spread","spring",
"spy","square","squeeze","squirrel","stable","stadium","staff","stage","stairs","stamp",
"stand","start","state","stay","steak","steel","stem","step","stereo","stick",
"still","sting","stock","stomach","stone","stool","story","stove","strategy","street",
"strike","strong","struggle","student","stuff","stumble","style","subject","submit","subway",
"success","such","sudden","suffer","sugar","suggest","suit","summer","sun","sunny",
"sunset","super","supply","supreme","sure","surface","surge","surprise","surround","survey",
"suspect","sustain","swallow","swamp","swap","swarm","swear","sweet","swift","swim",
"swing","switch","sword","symbol","symptom","syrup","system","table","tackle","tag",
"tail","talent","talk","tank","tape","target","task","taste","tattoo","taxi",
"teach","team","tell","ten","tenant","tennis","tent","term","test","text",
"thank","that","theme","then","theory","there","they","thing","this","thought",
"three","thrive","throw","thumb","thunder","ticket","tide","tiger","tilt","timber",
"time","tiny","tip","tired","tissue","title","toast","tobacco","today","toddler",
"toe","together","toilet","token","tomato","tomorrow","tone","tongue","tonight","tool",
"tooth","top","topic","topple","torch","tornado","tortoise","toss","total","tourist",
"toward","tower","town","toy","track","trade","traffic","tragic","train","transfer",
"trap","trash","travel","tray","treat","tree","trend","trial","tribe","trick",
"trigger","trim","trip","trophy","trouble","truck","true","truly","trumpet","trust",
"truth","try","tube","tuition","tumble","tuna","tunnel","turkey","turn","turtle",
"twelve","twenty","twice","twin","twist","two","type","typical","ugly","umbrella",
"unable","unaware","uncle","uncover","under","undo","unfair","unfold","unhappy","uniform",
"unique","unit","universe","unknown","unlock","until","unusual","unveil","update","upgrade",
"uphold","upon","upper","upset","urban","urge","usage","use","used","useful",
"useless","usual","utility","vacant","vacuum","vague","valid","valley","valve","van",
"vanish","vapor","various","vast","vault","vehicle","velvet","vendor","venture","venue",
"verb","verify","version","very","vessel","veteran","viable","vibrant","vicious","victory",
"video","view","village","vintage","violin","virtual","virus","visa","visit","visual",
"vital","vivid","vocal","voice","void","volcano","volume","vote","voyage","wage",
"wagon","wait","walk","wall","walnut","want","warfare","warm","warrior","wash",
"wasp","waste","water","wave","way","wealth","weapon","wear","weasel","weather",
"web","wedding","weekend","weird","welcome","west","wet","whale","what","wheat",
"wheel","when","where","whip","whisper","wide","width","wife","wild","will",
"win","window","wine","wing","wink","winner","winter","wire","wisdom","wise",
"wish","witness","wolf","woman","wonder","wood","wool","word","work","world",
"worry","worth","wrap","wreck","wrestle","wrist","write","wrong","yard","year",
"yellow","you","young","youth","zebra","zero","zone","zoo"
]

if len(BIP39_WORDS) < 2048:
    raise Exception(f"BIP39 tem {len(BIP39_WORDS)} palavras (precisa 2048)")
BIP39_WORDS = BIP39_WORDS[:2048]


def bip39_generate(strength_bits=128):
    if strength_bits not in (128, 160, 192, 224, 256):
        raise ValueError("strength invlido")
    entropy = secrets.token_bytes(strength_bits // 8)
    checksum_bits = strength_bits // 32
    checksum = hashlib.sha256(entropy).digest()
    bits = ""
    for byte in entropy:
        bits += format(byte, '08b')
    for byte in checksum:
        bits += format(byte, '08b')
    bits = bits[:strength_bits + checksum_bits]
    words = []
    for i in range(0, len(bits), 11):
        idx = int(bits[i:i + 11], 2)
        words.append(BIP39_WORDS[idx])
    return " ".join(words)


def bip39_to_seed(mnemonic, passphrase=""):
    mnemonic = mnemonic.strip().lower()
    salt = ("mnemonic" + passphrase).encode("utf-8")
    return hashlib.pbkdf2_hmac(
        "sha512", mnemonic.encode("utf-8"), salt, 2048, dklen=64
    )


def bip39_validate(mnemonic):
    words = mnemonic.strip().lower().split()
    if len(words) not in (12, 15, 18, 21, 24):
        return False
    indices = []
    for w in words:
        if w not in BIP39_WORDS:
            return False
        indices.append(BIP39_WORDS.index(w))
    bits = ""
    for idx in indices:
        bits += format(idx, '011b')
    total_bits = len(bits)
    checksum_bits = total_bits // 33
    entropy_bits = total_bits - checksum_bits
    entropy_str = bits[:entropy_bits]
    checksum_str = bits[entropy_bits:]
    entropy = bytearray()
    for i in range(0, len(entropy_str), 8):
        entropy.append(int(entropy_str[i:i + 8], 2))
    expected_hash = hashlib.sha256(bytes(entropy)).digest()
    expected_bits = ""
    for byte in expected_hash:
        expected_bits += format(byte, '08b')
    expected_bits = expected_bits[:checksum_bits]
    return checksum_str == expected_bits


def bip32_master_key(seed):
    result = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    return result[:32], result[32:]


def bip32_derive_child(key, chain_code, index, hardened=False):
    if hardened:
        data = b"\x00" + key + struct.pack(">I", index | 0x80000000)
    else:
        data = key + struct.pack(">I", index)
    I = hmac.new(chain_code, data, hashlib.sha512).digest()
    return I[:32], I[32:]


def bip32_derive_path(seed, path="m/44'/9999'/0'/0/0"):
    key, chain = bip32_master_key(seed)
    parts = path.split("/")[1:]
    for part in parts:
        hardened = part.endswith("'")
        if hardened:
            part = part[:-1]
        index = int(part)
        key, chain = bip32_derive_child(key, chain, index, hardened)
    return key


ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58e(data):
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = ALPH[r] + out
    pad = 0
    for x in data:
        if x == 0:
            pad += 1
        else:
            break
    return "1" * pad + (out or "1")


def b58d(s):
    n = 0
    for c in s:
        if c not in ALPH:
            raise ValueError("Base58 invlido")
        n = n * 58 + ALPH.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = 0
    for c in s:
        if c == "1":
            pad += 1
        else:
            break
    return b"\0" * pad + raw


P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
GY = 32670510020758816978083085130507043184471273380659243275938904335757337482424
G = (GX, GY)


def inv(a, n=P): return pow(a, -1, n)


def ec_add(a, b):
    if a is None: return b
    if b is None: return a
    x1, y1 = a
    x2, y2 = b
    if x1 == x2 and (y1 + y2) % P == 0: return None
    if a == b:
        if y1 == 0: return None
        m = ((3 * x1 * x1) * inv(2 * y1)) % P
    else:
        m = ((y2 - y1) * inv(x2 - x1)) % P
    x3 = (m * m - x1 - x2) % P
    y3 = (m * (x1 - x3) - y1) % P
    return x3, y3


def ec_mul(k, point=G):
    r = None
    a = point
    while k:
        if k & 1: r = ec_add(r, a)
        a = ec_add(a, a)
        k >>= 1
    return r


def pubkey(priv):
    x, y = ec_mul(priv)
    return bytes([2 + (y & 1)]) + x.to_bytes(32, "big")


def ripemd160(data):
    try:
        from Crypto.Hash import RIPEMD160
        return RIPEMD160.new(data).digest()
    except ImportError:
        h = hashlib.new("ripemd160")
        h.update(data)
        return h.digest()


def address_from_pub(pub):
    payload = b"\x1E" + ripemd160(sha256(pub))
    return b58e(payload + sha256d(payload)[:4])


def wif_from_priv(priv):
    raw = b"\x9E" + priv.to_bytes(32, "big") + b"\x01"
    return b58e(raw + sha256d(raw)[:4])


def priv_from_wif(wif):
    raw = b58d(wif)
    if len(raw) != 38: raise ValueError("WIF invlido")
    body = raw[:-4]
    checksum = raw[-4:]
    if sha256d(body)[:4] != checksum: raise ValueError("Checksum WIF invlido")
    if body[0] != 0x9E: raise ValueError("WIF no compatvel com DogKong")
    if body[-1] != 1: raise ValueError("WIF comprimido esperado")
    return int.from_bytes(body[1:33], "big")


def valid_address(addr):
    try:
        raw = b58d(addr)
        if len(raw) != 25: return False
        body = raw[:-4]
        check = raw[-4:]
        if body[0] != 0x1E: return False
        return sha256d(body)[:4] == check
    except:
        return False


# ============================================================
# ECDSA
# ============================================================
def deterministic_k(priv, msg):
    seed = priv.to_bytes(32, "big") + msg
    return (int.from_bytes(hashlib.sha256(seed).digest(), "big") % N) or 1


def sign(priv, text):
    z = int.from_bytes(hashlib.sha256(text.encode()).digest(), "big")
    while True:
        k = deterministic_k(priv, z.to_bytes(32, "big"))
        R = ec_mul(k)
        if R is None: continue
        r = R[0] % N
        if r == 0: continue
        s = (inv(k, N) * (z + r * priv) % N)
        if s == 0: continue
        if s > N // 2: s = N - s
        return f"{r:064x}{s:064x}"


def decompress_pub(pub):
    if not isinstance(pub, (bytes, bytearray)):
        raise ValueError("pubkey no  bytes")
    if len(pub) != 33:
        raise ValueError("pubkey precisa ter 33 bytes")
    prefix = pub[0]
    if prefix not in (0x02, 0x03):
        raise ValueError("prefixo de pubkey invlido")
    x = int.from_bytes(pub[1:], "big")
    if x <= 0 or x >= P:
        raise ValueError("x fora do range da curva")
    y2 = (pow(x, 3, P) + 7) % P
    y = pow(y2, (P + 1) // 4, P)
    if (y * y) % P != y2:
        raise ValueError("ponto no est na curva secp256k1")
    if (y & 1) != (prefix & 1):
        y = P - y
    return x, y


def verify(pub, text, signature):
    try:
        if not isinstance(pub, (bytes, bytearray)):
            return False
        if not isinstance(signature, str):
            return False
        if not isinstance(text, str):
            return False
        if len(signature) != 128:
            return False
        if len(pub) != 33:
            return False
        if pub[0] not in (0x02, 0x03):
            return False
        try:
            r = int(signature[:64], 16)
            s = int(signature[64:], 16)
        except ValueError:
            return False
        if not (1 <= r < N and 1 <= s < N):
            return False
        try:
            pub_point = decompress_pub(bytes(pub))
        except Exception:
            return False
        z = int.from_bytes(hashlib.sha256(text.encode()).digest(), "big")
        try:
            w = inv(s, N)
        except Exception:
            return False
        u1 = z * w % N
        u2 = r * w % N
        try:
            R = ec_add(ec_mul(u1), ec_mul(u2, pub_point))
        except Exception:
            return False
        if R is None:
            return False
        return R[0] % N == r
    except Exception:
        return False


# ============================================================
# CRIPTOGRAFIA DA CARTEIRA
# ============================================================
def _keystream(key, nonce, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.pbkdf2_hmac(
            "sha256", key, nonce + struct.pack(">I", counter), 1000, dklen=32
        )
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_wallet(data_json, password):
    plaintext = json.dumps(data_json, separators=(",", ":")).encode("utf-8")
    salt = secrets.token_bytes(32)
    nonce = secrets.token_bytes(12)

    if USE_ARGON2:
        key = _argon2.hash_secret_raw(
            secret=password.encode(),
            salt=salt,
            time_cost=3, memory_cost=65536, parallelism=4,
            hash_len=32, type=_argon2.Type.ID
        )
    else:
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000, dklen=32)

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        ct = AESGCM(key).encrypt(nonce, plaintext, b"DOGK-WALLET-v2")
        return {
            "version": 2, "encrypted": True,
            "kdf": "argon2id" if USE_ARGON2 else "pbkdf2-sha256-600k",
            "cipher": "aes-256-gcm",
            "salt": salt.hex(), "nonce": nonce.hex(),
            "ciphertext": ct.hex()
        }
    except ImportError:
        stream = _keystream(key, nonce[:16], len(plaintext))
        ct = bytes(a ^ b for a, b in zip(plaintext, stream))
        mac_key = hmac.new(key, b"MAC-v2", hashlib.sha256).digest()
        mac = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
        return {
            "version": 2, "encrypted": True,
            "kdf": "argon2id" if USE_ARGON2 else "pbkdf2-sha256-600k",
            "cipher": "xor-hmac-sha256",
            "salt": salt.hex(), "nonce": nonce.hex(),
            "ciphertext": ct.hex(), "mac": mac.hex()
        }


def decrypt_wallet(data, password):
    if not data.get("encrypted"):
        return data
    salt = bytes.fromhex(data["salt"])
    nonce = bytes.fromhex(data["nonce"])
    ct = bytes.fromhex(data["ciphertext"])

    if USE_ARGON2:
        key = _argon2.hash_secret_raw(
            secret=password.encode(), salt=salt,
            time_cost=3, memory_cost=65536, parallelism=4,
            hash_len=32, type=_argon2.Type.ID)
    else:
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000, dklen=32)

    cipher = data.get("cipher", "xor-hmac-sha256")
    if cipher == "aes-256-gcm":
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        try:
            pt = AESGCM(key).decrypt(nonce, ct, b"DOGK-WALLET-v2")
            return json.loads(pt.decode())
        except Exception:
            raise ValueError("Senha incorreta ou wallet corrompida")
    else:
        mac_stored = bytes.fromhex(data["mac"])
        mac_key = hmac.new(key, b"MAC-v2", hashlib.sha256).digest()
        mac_calc = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
        if not hmac.compare_digest(mac_calc, mac_stored):
            raise ValueError("Senha incorreta")
        stream = _keystream(key, nonce[:16], len(ct))
        pt = bytes(a ^ b for a, b in zip(ct, stream))
        return json.loads(pt.decode())


class PasswordGuard:
    def __init__(self):
        self.attempts = 0
        self.lock_until = 0

    def check(self):
        agora = time.time()
        if agora < self.lock_until:
            return False, int(self.lock_until - agora)
        return True, 0

    def register_failure(self):
        self.attempts += 1
        delays = [0, 2, 5, 30, 300, 3600]
        idx = min(self.attempts, len(delays) - 1)
        self.lock_until = time.time() + delays[idx]
        return delays[idx]

    def reset(self):
        self.attempts = 0
        self.lock_until = 0


PASSWORD_GUARD = PasswordGuard()


def bip39_to_private_key(mnemonic, passphrase=""):
    seed = bip39_to_seed(mnemonic, passphrase)
    key_bytes = bip32_derive_path(seed, "m/44'/9999'/0'/0/0")
    return int.from_bytes(key_bytes, "big") % N


class Wallet:
    def __init__(self):
        self.priv = None
        self.pub = None
        self.address = None
        self.wif = None
        self.mnemonic = None
        self.encrypted = False
        self.password = None
        self._encrypted_data = None
        self.load()

    def generate_mnemonic(self):
        self.mnemonic = bip39_generate(128)
        self.priv = bip39_to_private_key(self.mnemonic)
        self.pub = pubkey(self.priv)
        self.address = address_from_pub(self.pub)
        self.wif = wif_from_priv(self.priv)

    def generate(self, password=None):
        self.generate_mnemonic()
        self.password = password
        self.encrypted = bool(password)
        self.save()

    def load(self):
        if os.path.exists(WALLET_FILE):
            try:
                with open(WALLET_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                bak = WALLET_FILE + ".bak"
                if os.path.exists(bak):
                    try:
                        with open(bak, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        print("[DOGK] wallet.json corrompido; recuperado do .bak")
                    except Exception:
                        raise PersistError("wallet.json corrompido e backup falhou.")
                else:
                    raise PersistError("wallet.json corrompido e sem backup.")
        else:
            data = None

        if not data:
            self.generate_mnemonic()
            self.encrypted = False
            self.save()
            return
        if data.get("encrypted"):
            self.encrypted = True
            self._encrypted_data = data
            return
        self._load_plain(data)

    def _load_plain(self, data):
        try:
            if "mnemonic" in data:
                self.mnemonic = data["mnemonic"]
                self.priv = bip39_to_private_key(self.mnemonic)
            else:
                self.priv = int(data["private_key"], 16)
            self.pub = pubkey(self.priv)
            self.address = address_from_pub(self.pub)
            self.wif = wif_from_priv(self.priv)
            if "address" in data and data["address"] != self.address:
                raise ValueError("carteira inconsistente")
        except Exception as e:
            print(f"[DOGK] Erro ao carregar carteira: {e}")
            self.generate_mnemonic()
            self.encrypted = False
            self.save()

    def unlock(self, password):
        if not self._encrypted_data:
            return True
        try:
            data = decrypt_wallet(self._encrypted_data, password)
            self._load_plain(data)
            self.password = password
            self.encrypted = True
            self._encrypted_data = None
            return True
        except ValueError:
            return False

    def is_locked(self):
        return self.encrypted and self.priv is None

    def save(self):
        plain = {
            "private_key": f"{self.priv:064x}",
            "public_key": self.pub.hex(),
            "address": self.address,
            "wif": self.wif,
        }
        if self.mnemonic:
            plain["mnemonic"] = self.mnemonic
        if self.encrypted and self.password:
            data = encrypt_wallet(plain, self.password)
        else:
            data = plain
        save_json(WALLET_FILE, data)

    def set_password(self, password):
        self.password = password
        self.encrypted = True
        self.save()

    def remove_password(self):
        self.password = None
        self.encrypted = False
        self.save()

    def change_password(self, old_password, new_password):
        if self.encrypted and old_password != self.password:
            raise ValueError("Senha antiga incorreta")
        self.password = new_password
        self.encrypted = True
        self.save()

    def import_wif(self, wif):
        p = priv_from_wif(wif)
        self.priv = p
        self.pub = pubkey(p)
        self.address = address_from_pub(self.pub)
        self.wif = wif
        self.mnemonic = None
        self.save()

    def import_mnemonic(self, mnemonic, password=None):
        if not bip39_validate(mnemonic):
            raise ValueError("Mnemnico invlido")
        self.mnemonic = mnemonic.strip().lower()
        self.priv = bip39_to_private_key(self.mnemonic)
        self.pub = pubkey(self.priv)
        self.address = address_from_pub(self.pub)
        self.wif = wif_from_priv(self.priv)
        self.password = password
        self.encrypted = bool(password)
        self.save()


def block_reward(height):
    return REWARD_PER_BLOCK


def tx_message(tx):
    d = dict(tx)
    d.pop("signature", None)
    d.pop("id", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def make_tx(wallet, to_addr, amount, fee):
    tx = {
        "id": "",
        "chain": CHAIN_ID,
        "from": wallet.address,
        "to": to_addr,
        "amount": float(amount),
        "fee": float(fee),
        "pubkey": wallet.pub.hex(),
        "time": now(),
        "signature": ""
    }
    tx["id"] = h(tx_message(tx).encode())
    tx["signature"] = sign(wallet.priv, tx["id"])
    return tx


def block_header_bytes(block):
    """Header usa bits em vez de difficulty."""
    return (
        f"{block['height']}:"
        f"{block['time']}:"
        f"{block['prev']}:"
        f"{block['bits']}:"
        f"{block['nonce']}:"
        f"{block['miner']}"
    ).encode()


def compute_pow_hash(block):
    header = block_header_bytes(block)
    digest = hashlib.sha256(header).digest()
    table = MEMORY_TABLE
    size = MEMORY_SIZE
    sha256 = hashlib.sha256
    for _ in range(MEMORY_ITER):
        pos1 = int.from_bytes(digest[:4], "big") % (size - 64)
        pos2 = int.from_bytes(digest[4:8], "big") % (size - 64)
        chunk1 = table[pos1:pos1 + 32]
        chunk2 = table[pos2:pos2 + 32]
        digest = sha256(digest + chunk1 + chunk2).digest()
    return digest.hex()


def compute_block_hash(block):
    return hashlib.sha256(block_header_bytes(block)).hexdigest()


MEMORY_SIZE = MEMORY_MB * 1024 * 1024
MEMORY_TABLE_FILE = os.path.join(DATA, "memory_table.bin")


def _build_memory_table():
    """
    Carrega o memory_table.bin empacotado dentro do .exe (ou do lado do .py).
    NUNCA gera em runtime â€” instantÃ¢neo sempre.
    """
    if getattr(sys, 'frozen', False):
        # .exe: procura do lado do executavel PRIMEIRO
        lado_exe = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "memory_table.bin")
        if os.path.exists(lado_exe):
            caminho = lado_exe
        else:
            # Senao, dentro do _MEIPASS
            caminho = os.path.join(getattr(sys, "_MEIPASS", ""), "memory_table.bin")
    else:
        # Rodando como .py: pega do lado do arquivo
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_table.bin")

    if not os.path.exists(caminho):
        print(f"[DOGK v2] Gerando {caminho} ({MEMORY_MB}MB)...", flush=True)
        table = bytearray()
        bloco = b"DOGK-MEMORY-TABLE-v1"
        while len(table) < MEMORY_SIZE:
            bloco = hashlib.sha256(bloco).digest()
            table.extend(bloco)
        table = bytes(table[:MEMORY_SIZE])
        with open(caminho, "wb") as f:
            f.write(table)
        print(f"[DOGK v2] Arquivo gerado.", flush=True)

    with open(caminho, "rb") as f:
        dados = f.read()

    if len(dados) != MEMORY_SIZE:
        raise Exception(
            f"memory_table.bin tem {len(dados)} bytes, "
            f"esperado {MEMORY_SIZE} bytes ({MEMORY_MB} MB)"
        )

    print(f"[DOGK v2] Tabela RAM carregada do .exe ({len(dados)} bytes).", flush=True)
    return dados


print("[DOGK v2] Construindo tabela RAM de %d MB..." % MEMORY_MB)
MEMORY_TABLE = _build_memory_table()
print("[DOGK v2] Tabela RAM pronta.")


# ============================================================
# BENCHMARK
# ============================================================
def benchmark_hashrate(duracao=2.0):
    bloco_fake = {
        "height": 999999,
        "time": now(),
        "prev": "0" * 64,
        "bits": 0x207fffff,
        "nonce": 0,
        "miner": "BENCHMARK",
        "tx": [],
        "hash": ""
    }
    sha256 = hashlib.sha256
    table = MEMORY_TABLE
    size = MEMORY_SIZE
    hashes = 0
    inicio = time.time()
    nonce = 0
    while (time.time() - inicio) < duracao:
        bloco_fake["nonce"] = nonce
        header = block_header_bytes(bloco_fake)
        digest = sha256(header).digest()
        for _ in range(MEMORY_ITER):
            pos1 = int.from_bytes(digest[:4], "big") % (size - 64)
            pos2 = int.from_bytes(digest[4:8], "big") % (size - 64)
            chunk1 = table[pos1:pos1 + 32]
            chunk2 = table[pos2:pos2 + 32]
            digest = sha256(digest + chunk1 + chunk2).digest()
        hashes += 1
        nonce += 1
    decorrido = max(1e-6, time.time() - inicio)
    return hashes / decorrido


def median_time_past(chain, n=11):
    if len(chain) < 1:
        return 0
    times = []
    for b in chain[-n:]:
        try:
            times.append(int(b.get("time", 0)))
        except Exception:
            pass
    if not times:
        return 0
    times.sort()
    return times[len(times) // 2]


class BlockchainStub:
    def __init__(self):
        self.chain = [{"height": 0, "hash": "0"*64, "time": 0, "bits": INITIAL_DIFFICULTY, "prev": "0"*64, "nonce": 0, "miner": "SEED", "tx": [], "peers": []}]
        self.mempool = []
        self.lock = threading.RLock()
    def height(self): return 0
    def last_block(self): return self.chain[0]
    def difficulty(self): return INITIAL_DIFFICULTY
    def hashrate_rede(self): return 0.0
    def save(self): pass
    def target_difficulty(self, candidate_time=None): return INITIAL_DIFFICULTY
    def balance(self, address, min_conf=1): return 0.0
    def add_transaction(self, tx): return False
    def accept_chain(self, chain): return False
    def reorg_chain(self, chain): return False
    def valid_chain(self, chain): return False
    def tx_exists(self, txid): return False
    def create_coinbase(self, address, height): return None


class Blockchain:
    def __init__(self):
        self.lock = threading.RLock()
        chain_existe = os.path.exists(CHAIN_FILE)
        chain = None
        erro_principal = None

        if chain_existe:
            try:
                with open(CHAIN_FILE, "r", encoding="utf-8") as f:
                    chain = json.load(f)
            except Exception as e:
                erro_principal = e
                chain = None

        if chain is None and chain_existe:
            bak = CHAIN_FILE + ".bak"
            if os.path.exists(bak):
                try:
                    with open(bak, "r", encoding="utf-8") as f:
                        chain = json.load(f)
                    print("[DOGK v2] blockchain.json corrompido; carregado do .bak")
                except Exception:
                    chain = None

        if chain_existe and chain is None:
            raise PersistError("blockchain.json existe mas nao pode ser lido.")

        if not chain_existe:
            # NAO cria genesis. Espera sincronizar com a rede.
            # Chain vazia = aguardando bootstrap.
            self.chain = []
            self.mempool = []
            self._aguardando_sync = True
            print("[DOGK v2] Sem blockchain local. Aguardando sincronizacao com a rede...", flush=True)
            return
        self._aguardando_sync = False

        if not chain:
            raise PersistError("blockchain.json esta vazio.")

        # NAO valida a chain local (confia no que ta salvo)
        # A validacao so acontece quando recebe chain de outro peer
        self.chain = chain
        self.mempool = load_json(MEMPOOL_FILE, default=[])

    # --------------------------------------------------------
    # GENESIS (criado automaticamente na primeira execuo)
    # --------------------------------------------------------
    def criar_bloco_genesis(self):
        """
        Monta e minera o Bloco Gnese (altura 0).
        - hash_anterior = "0" * 64
        - bits = 0x1D00FFFF (super fcil)
        - tx = [] (sem coinbase no genesis, igual Bitcoin)
        - PoW CPU+RAM: hash <= target(bits)
        """
        bloco = {
            "height": 0,
            "time": now() - BLOCK_TIME,
            "prev": "0" * 64,
            "bits": INITIAL_DIFFICULTY,
            "nonce": 0,
            "miner": "DOGK-V2-GENESIS",
            "tx": [],
            "message": "DogKong v2 Genesis Block",
            "hash": ""
        }

        target = bits_para_target(INITIAL_DIFFICULTY)
        print(f"[DOGK v2] Genesis bits=0x{INITIAL_DIFFICULTY:08X} "
              f"target=0x{target:064X}")

        nonce = 0
        inicio = time.time()
        while True:
            bloco["nonce"] = nonce
            hh = compute_pow_hash(bloco)
            if int(hh, 16) <= target:
                bloco["hash"] = hh
                break
            nonce += 1
            if nonce % 5000 == 0:
                decorrido = time.time() - inicio
                print(f"[DOGK v2] Minerando genesis... nonce={nonce} "
                      f"({decorrido:.1f}s)")

        decorrido = time.time() - inicio
        print(f"[DOGK v2] Genesis minerado: nonce={nonce} "
              f"hash={bloco['hash'][:16]}... em {decorrido:.1f}s")
        return bloco

    # Alias pra manter compat
    def genesis(self):
        return self.criar_bloco_genesis()

    def save(self):
        with self.lock:
            save_json(CHAIN_FILE, self.chain)
            save_json(MEMPOOL_FILE, self.mempool)
            # .bak extra a cada save (save_json ja faz .bak automatico)

    def height(self):
        if not self.chain:
            return -1
        return len(self.chain) - 1

    def last_block(self):
        if not self.chain:
            return None
        return self.chain[-1]

    def difficulty(self):
        if not self.chain:
            return INITIAL_DIFFICULTY
        return int(self.chain[-1].get("bits", INITIAL_DIFFICULTY))

    def _check_timestamp(self, block):
        if int(block["time"]) > now() + MAX_FUTURE_TIME:
            return False
        return True

    def valid_pow(self, block):
        hh = compute_pow_hash(block)
        if hh != block.get("hash"):
            return False
        target = bits_para_target(int(block["bits"]))
        return int(hh, 16) <= target

    def chain_work(self, chain=None):
        if chain is None:
            chain = self.chain
        total = 0
        for b in chain:
            bits = int(b.get("bits", INITIAL_DIFFICULTY))
            target = bits_para_target(bits)
            if target > 0:
                total += (2 ** 256) // target
        return total

    def target_difficulty(self, chain=None, candidate_time=None):
        if chain is None:
            chain = self.chain
        if not chain:
            return INITIAL_DIFFICULTY
        return calcular_dificuldade_alvo(chain, candidate_time=candidate_time)

    def expected_difficulty_for_chain(self, chain, height, candidate_time=None):
        if height <= 1:
            return INITIAL_DIFFICULTY
        prev_chain = chain[:height]
        if len(prev_chain) < 2:
            return INITIAL_DIFFICULTY
        return calcular_dificuldade_alvo(prev_chain, candidate_time=candidate_time)

    def hashrate_rede(self, chain=None):
        if chain is None:
            chain = self.chain
        return estimar_hashrate_rede(chain)

    def _balance_cached(self, address, min_conf=1):
        """Calcula saldo uma vez e guarda em cache. Invalida quando chain muda."""
        cache_key = (address, min_conf)
        chain_len = len(self.chain)
        if not hasattr(self, "_bal_cache"):
            self._bal_cache = {}
        cached = self._bal_cache.get(cache_key)
        if cached is not None and cached[0] == chain_len:
            return cached[1]
        bal = 0.0
        n_blocks = chain_len
        for i, block in enumerate(self.chain):
            conf = n_blocks - i
            for tx in block.get("tx", []):
                sender = tx.get("from")
                receiver = tx.get("to")
                amount = float(tx.get("amount", 0))
                fee = float(tx.get("fee", 0))
                if sender == "COINBASE":
                    if receiver == address and conf >= min_conf:
                        bal += amount
                    continue
                if sender == address:
                    bal -= amount
                    bal -= fee
                if receiver == address and conf >= min_conf:
                    bal += amount
        if min_conf <= 0:
            for tx in self.mempool:
                if tx.get("from") == address:
                    bal -= float(tx.get("amount", 0))
                    bal -= float(tx.get("fee", 0))
        bal = max(0.0, bal)
        self._bal_cache[cache_key] = (chain_len, bal)
        return bal

    def balance(self, address, min_conf=1):
        return self._balance_cached(address, min_conf)

    def tx_exists(self, txid):
        for b in self.chain:
            for tx in b.get("tx", []):
                if tx.get("id") == txid:
                    return True
        return any(x.get("id") == txid for x in self.mempool)

    def validate_tx(self, tx, allow_coinbase=False):
        try:
            if not isinstance(tx, dict):
                return False
            if tx.get("from") == "COINBASE":
                return allow_coinbase
            if tx.get("chain") != CHAIN_ID:
                return False
            required = ["id", "from", "to", "amount", "fee", "pubkey", "signature"]
            if any(k not in tx for k in required):
                return False
            txid = tx.get("id")
            if not isinstance(txid, str) or len(txid) != 64:
                return False
            try:
                int(txid, 16)
            except ValueError:
                return False
            sender = tx.get("from")
            receiver = tx.get("to")
            if not isinstance(sender, str) or not isinstance(receiver, str):
                return False
            if len(sender) > 100 or len(receiver) > 100:
                return False
            if not valid_address(receiver):
                return False
            pubkey_hex = tx.get("pubkey")
            if not isinstance(pubkey_hex, str):
                return False
            if len(pubkey_hex) != 66:
                return False
            try:
                pub = bytes.fromhex(pubkey_hex)
            except ValueError:
                return False
            sig = tx.get("signature")
            if not isinstance(sig, str) or len(sig) != 128:
                return False
            try:
                int(sig, 16)
            except ValueError:
                return False
            try:
                amount = float(tx["amount"])
                fee = float(tx["fee"])
            except (ValueError, TypeError):
                return False
            if not (amount > 0 and amount < 1_000_000_000):
                return False
            if not (fee >= 0 and fee < 1_000_000):
                return False
            if fee < MIN_FEE:
                return False
            if address_from_pub(pub) != sender:
                return False
            if self.tx_exists(txid):
                return False
            if h(tx_message(tx).encode()) != txid:
                return False
            if not verify(pub, txid, sig):
                return False
            if self.balance(sender, min_conf=6) < amount + fee:
                return False
            return True
        except Exception:
            return False

    def _check_mempool_limits(self):
        total = sum(len(json.dumps(tx)) for tx in self.mempool)
        if total > MAX_MEMPOOL_BYTES:
            self.mempool.sort(key=lambda t: float(t.get("fee", 0)), reverse=True)
            while sum(len(json.dumps(tx)) for tx in self.mempool) > MAX_MEMPOOL_BYTES:
                self.mempool.pop()
        if len(self.mempool) > MAX_MEMPOOL_TX:
            self.mempool.sort(key=lambda t: float(t.get("fee", 0)), reverse=True)
            self.mempool = self.mempool[:MAX_MEMPOOL_TX]

    def _balance_after_mempool(self, address, min_conf=1):
        bal = 0.0
        n_blocks = len(self.chain)
        for i, block in enumerate(self.chain):
            conf = n_blocks - i
            for tx in block.get("tx", []):
                s = tx.get("from")
                r = tx.get("to")
                a = float(tx.get("amount", 0))
                f = float(tx.get("fee", 0))
                if s == "COINBASE":
                    if r == address and conf >= min_conf:
                        bal += a
                    continue
                if s == address:
                    bal -= (a + f)
                if r == address and conf >= min_conf:
                    bal += a
        if min_conf <= 0:
            for tx in self.mempool:
                if tx.get("from") == address:
                    bal -= float(tx.get("amount", 0))
                    bal -= float(tx.get("fee", 0))
        return bal

    def add_transaction(self, tx):
        with self.lock:
            if not self.validate_tx(tx):
                return False
            if any(x.get("id") == tx["id"] for x in self.mempool):
                return False
            saldo_disponivel = self._balance_after_mempool(tx["from"], min_conf=6)
            custo_total = float(tx["amount"]) + float(tx["fee"])
            if saldo_disponivel < custo_total:
                return False
            self.mempool.append(tx)
            self._check_mempool_limits()
            self.save()
            return True

    def create_coinbase(self, address, height, txs=None):
        reward = block_reward(height)
        taxas = 0.0
        if txs and height > 11964:
            for tx in txs:
                if tx.get("from") != "COINBASE":
                    taxas += float(tx.get("fee", 0))
        total = reward + taxas
        return {
            "id": h(f"COINBASE:{height}:{address}:{total}".encode()),
            "from": "COINBASE",
            "to": address,
            "amount": total,
            "fee": 0,
            "time": now()
        }

    def valid_chain(self, chain):
        try:
            if not chain:
                return False
            g = chain[0]
            # Bootstrap: chain vinda da rede pode comecar em altura > 0
            # (so valida se comecar do genesis real)
            if g.get("height") != 0:
                # Aceita como chain parcial (bootstrap)
                # Valida so os hashes internos e PoW
                for i in range(1, len(chain)):
                    b = chain[i]
                    if b.get("prev") != chain[i-1].get("hash"):
                        return False
                    if not self.valid_pow(b):
                        return False
                return True
            if g.get("prev") != "0" * 64:
                return False
            if g.get("prev") != "0" * 64:
                return False
            if int(g.get("bits", 0)) not in (INITIAL_DIFFICULTY, 0x207fffff):
                return False
            if not g.get("hash"):
                return False
            bits_gen = int(g.get("bits", INITIAL_DIFFICULTY))
            target_gen = bits_para_target(bits_gen)
            if int(g["hash"], 16) > target_gen:
                return False
            for i, b in enumerate(chain):
                # Pula validacao rigorosa dos primeiros 1000 blocos
                if False:  # BUGFIX
                    if int(b["height"]) != i:
                        return False
                    if i > 0 and b["prev"] != chain[i - 1]["hash"]:
                        return False
                    continue
                if i > 0 and i % CHECKPOINT_INTERVAL == 0:
                    if i < len(chain):
                        if chain[i]["hash"] != b["hash"]:
                            return False
                if i == 0:
                    continue
                if b["prev"] != chain[i - 1]["hash"]:
                    return False
                if not self.valid_pow(b):
                    return False
                if int(b["time"]) < int(chain[i - 1]["time"]):
                    return False
                # MTP NAO e validado no bootstrap
                pass

                if len(b.get("tx", [])) > MAX_BLOCK_TX:
                    return False
                # Bits NAO sao validados no bootstrap (confia na chain)
                # So valida se for chain recebida de peer (reorg_chain)
                pass
                txs = b.get("tx", [])
                if not txs:
                    return False
                coinbases = 0
                seen = set()
                for tx in txs:
                    txid = tx.get("id")
                    if not txid or txid in seen:
                        return False
                    seen.add(txid)
                    if tx.get("from") == "COINBASE":
                        coinbases += 1
                        if coinbases > 1:
                            return False
                        expected = block_reward(i)
                        if i > 11964:
                            taxas_bloco = 0.0
                            for tx2 in txs:
                                if tx2.get("from") != "COINBASE":
                                    taxas_bloco += float(tx2.get("fee", 0))
                            expected = block_reward(i) + taxas_bloco
                        if abs(float(tx.get("amount", -1)) - expected) > 1e-8:
                            return False
                        if not valid_address(tx.get("to", "")):
                            return False
                        continue
                    if tx.get("chain") != CHAIN_ID:
                        return False
                    if float(tx.get("fee", 0)) < MIN_FEE:
                        return False
                    pub = bytes.fromhex(tx["pubkey"])
                    if address_from_pub(pub) != tx["from"]:
                        return False
                    if h(tx_message(tx).encode()) != tx["id"]:
                        return False
                    if not verify(pub, tx["id"], tx["signature"]):
                        return False
                if coinbases != 1:
                    return False
                if i > 11964:
                    gastos_por_endereco = {}
                    for tx in txs:
                        if tx.get("from") == "COINBASE":
                            continue
                        sender = tx.get("from")
                        valor = float(tx.get("amount", 0)) + float(tx.get("fee", 0))
                        gastos_por_endereco[sender] = gastos_por_endereco.get(sender, 0.0) + valor
                    for endereco, total in gastos_por_endereco.items():
                        saldo_hist = 0.0
                        for j in range(i):
                            for tx2 in chain[j].get("tx", []):
                                s2 = tx2.get("from")
                                r2 = tx2.get("to")
                                a2 = float(tx2.get("amount", 0))
                                f2 = float(tx2.get("fee", 0))
                                if s2 == "COINBASE":
                                    if r2 == endereco:
                                        saldo_hist += a2
                                    continue
                                if s2 == endereco:
                                    saldo_hist -= (a2 + f2)
                                if r2 == endereco:
                                    saldo_hist += a2
                        if saldo_hist < total:
                            return False
            return True
        except Exception as e:
            import traceback
            print("[DOGK v2] valid_chain FALHOU:", e)
            traceback.print_exc()
            return False


    def reorg_chain(self, nova_chain):
        with self.lock:
            if len(nova_chain) <= len(self.chain):
                return False
            if self.chain_work(nova_chain) <= self.chain_work(self.chain):
                return False
            fork_point = 0
            for i in range(min(len(nova_chain), len(self.chain))):
                if nova_chain[i].get("hash") != self.chain[i].get("hash"):
                    fork_point = i
                    break
            else:
                fork_point = len(self.chain)
            for i in range(max(1, fork_point), len(nova_chain)):
                b = nova_chain[i]
                if not self.valid_pow(b):
                    return False
                if b.get("prev") != nova_chain[i-1].get("hash"):
                    return False
            self.chain = list(nova_chain)
            self.mempool = [tx for tx in self.mempool if not self.tx_exists(tx['id'])]
            self.save()
            return True

    def accept_chain(self, new_chain):
        with self.lock:
            # Bootstrap: chain local vazia -> aceita SEM validar (confia no seed)
            if not self.chain:
                if not new_chain:
                    return False
                # Valida SO o ultimo bloco (PoW)
                ultimo = new_chain[-1]
                if not self.valid_pow(ultimo):
                    print("[DOGK v2] accept_chain: PoW do ultimo bloco invalido", flush=True)
                    return False
                self.chain = list(new_chain)
                self._aguardando_sync = False
                self.save()
                print(f"[DOGK v2] Bootstrap: chain adotada da rede ({len(new_chain)} blocos)", flush=True)
                return True
            if len(new_chain) < len(self.chain):
                return False
            fork_point = 0
            for i in range(min(len(new_chain), len(self.chain))):
                if new_chain[i]["hash"] != self.chain[i]["hash"]:
                    fork_point = i
                    break
            else:
                fork_point = len(self.chain)
            if len(self.chain) - fork_point > CHECKPOINT_DEPTH:
                return False
            if self.chain_work(new_chain) <= self.chain_work(self.chain):
                return False
            if not True:  # DESABILITADO
                return False
            self.chain = new_chain
            self.mempool = [tx for tx in self.mempool if not self.tx_exists(tx["id"])]
            self._check_mempool_limits()
            self.save()
            return True



IRC_SERVER = "irc.libera.chat"
IRC_SERVERS = [
    ("irc.libera.chat", 6697),
    ("irc.oftc.net", 6697),
    ("irc.efnet.org", 6697),
    ("irc.rizon.net", 6697),
    ("irc.dal.net", 6697),
]
IRC_PORT = 6697
IRC_CHANNEL = "#dogkong"
IRC_NICK_PREFIX = "dogk_"
IRC_TIMEOUT = 10

def resolver_duckdns():
    """Resolve o DNS seed do DuckDNS."""
    import socket
    ips = set()
    for seed in DEFAULT_SEEDS:
        if "duckdns" not in seed:
            continue
        try:
            results = socket.getaddrinfo(seed, P2P_PORT, socket.AF_INET, socket.SOCK_STREAM)
            for res in results:
                ips.add(res[4][0])
            pass  # DUCKDNS logado depois; import sys; sys.stdout.flush()
        except Exception as e:
            pass  # DUCKDNS falha silenciosa
    return list(ips)

def postar_irc(meu_ip, meu_onion=None):
    """IRC DESABILITADO."""
    return


def resolver_irc(irc_servers=None):
    """IRC DESABILITADO - so usa seeds.json local."""
    print("[IRC] Desabilitado (usa so seeds.json)", flush=True)
    return []

def _resolver_irc_server(IRC_SERVER, IRC_PORT, ips):
    import socket, ssl, time, threading, secrets, re
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        s = socket.create_connection((IRC_SERVER, IRC_PORT), timeout=IRC_TIMEOUT)
        s = ctx.wrap_socket(s, server_hostname=IRC_SERVER)
        # Nick unico
        import secrets
        nick = IRC_NICK_PREFIX + secrets.token_hex(4)
        s.sendall(f"NICK {nick}\r\n".encode())
        s.sendall(f"USER {nick} 0 * :DogKong\r\n".encode())
        # Espera 2s e entra no canal
        time.sleep(2)
        s.sendall(f"JOIN {IRC_CHANNEL}\r\n".encode())
        # Le mensagens por 10s
        s.settimeout(10)
        inicio = time.time()
        buf = b""
        while time.time() - inicio < 10:
            try:
                data = s.recv(4096)
                if not data:
                    break
                buf += data
                for linha in buf.decode(errors="ignore").split("\r\n"):
                    # Procura IPs em mensagens
                    import re
                    # So captura IPs que vieram de mensagens DOGKPEER (nao lixo do canal)
                    for m in re.findall(r'DOGKPEER\s+([a-z2-7]{16,56}\.onion)', linha):
                        ips.add(m)
                    for m in re.findall(r'DOGKPEER\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):', linha):
                        ips.add(m)
            except socket.timeout:
                break
        s.sendall(f"QUIT :bye\r\n".encode())
        s.close()
        pass  # IRC logado depois; import sys; sys.stdout.flush()
    except Exception as e:
        pass  # IRC falha silenciosa
    return list(ips)



def resolver_remote_seeds():
    """Le o Gist remoto e retorna (irc_servers, dns_seeds + onion)."""
    import urllib.request, json
    irc = []
    dns = []
    try:
        with urllib.request.urlopen(REMOTE_SEEDS_URL, timeout=10) as r:
            data = json.loads(r.read())
        for s in data.get("irc", []):
            if ":" in s:
                host, port = s.split(":", 1)
                try:
                    port = int(port)
                except ValueError:
                    port = 6697
            else:
                host, port = s, 6697
            irc.append((host, port))
        dns = [s for s in data.get("dns", []) if isinstance(s, str)]
        onion = [s for s in data.get("onion", []) if isinstance(s, str)]
        dns = dns + onion
    except Exception as e:
        print(f"[GIST] Falha: {e}")
    return irc, dns


def resolver_dns_seeds(seeds=None):
    """
    Resolve dominios DNS para IPs (igual Bitcoin/Dogecoin).
    Retorna lista de IPs (sem porta).
    """
    if seeds is None:
        seeds = DEFAULT_SEEDS
    
    ips = set()
    for seed in seeds:
        # Se j  IP, adiciona direto
        if seed.count(".") == 3 and not any(c.isalpha() for c in seed):
            ips.add(seed)
            continue
        
        # Remove porta se tiver
        host = seed.split(":")[0]
        
        try:
            # Resolve DNS (IPv4)
            results = socket.getaddrinfo(host, P2P_PORT, socket.AF_INET, socket.SOCK_STREAM)
            for res in results:
                ip = res[4][0]
                ips.add(ip)
            print(f"[DNS] {host} -> {len(results)} IP(s)")
        except socket.gaierror as e:
            print(f"[DNS] Falha ao resolver {host}: {e}")
        except Exception as e:
            print(f"[DNS] Erro em {host}: {e}")
    
    return list(ips)


def tentar_upnp(porta=18555):
    """
    Tenta abrir a porta via UPnP (funciona em 80% dos roteadores domesticos).
    Pure Python - compativel com PyInstaller.
    """
    try:
        import upnpclient
    except ImportError:
        print("[UPnP] Biblioteca upnpclient nao instalada - pulando")
        return False
    
    try:
        # Descobre dispositivos UPnP na rede
        print("[UPnP] Procurando roteadores UPnP...")
        devices = upnpclient.discover(timeout=3)
        
        if not devices:
            print("[UPnP] Nenhum roteador UPnP encontrado")
            return False
        
        # Pra cada dispositivo, tenta achar o servico de WAN
        for device in devices:
            try:
                service = None
                for s in device.services:
                    if "WANIPConnection" in s.service_type or "WANPPPConnection" in s.service_type:
                        service = s
                        break
                
                if not service:
                    continue
                
                # Pega o IP local
                import socket
                s_temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s_temp.connect(("8.8.8.8", 80))
                ip_local = s_temp.getsockname()[0]
                s_temp.close()
                
                # Adiciona o mapeamento
                service.AddPortMapping(
                    NewRemoteHost="",
                    NewExternalPort=porta,
                    NewProtocol="TCP",
                    NewInternalPort=porta,
                    NewInternalClient=ip_local,
                    NewEnabled="1",
                    NewPortMappingDescription="DogKong P2P",
                    NewLeaseDuration="0"
                )
                
                print(f"[UPnP] Porta {porta} aberta automaticamente!")
                return True
                
            except Exception as e:
                print(f"[UPnP] Falha no dispositivo {device.friendly_name}: {e}")
                continue
        
        print("[UPnP] Nenhum roteador compativel encontrado")
        return False
        
    except Exception as e:
        print(f"[UPnP] Erro geral: {e}")
        return False


class Network:
    def __init__(self, core):
        self.core = core
        self.peers = {}
        self.lock = threading.Lock()
        self.running = True
        self.public_ip = None
        self.rate_limit = {}
        self.rate_lock = threading.Lock()
        self.server_sock = None
        self.banned = {}
        self.ban_lock = threading.Lock()
        self.peers_per_ip = {}
        self.peer_msgs = {}
        self.outbound_peers = set()
        self.onion_address = None
        self.principal_ips = set()
        # Conexoes persistentes
        self.active_connections = {}
        self.conn_lock = threading.Lock()
        self.send_queues = {}
        self.writer_threads = {}
        self.reader_threads = {}
        # Backoff de reconexao
        self.reconnect_backoff = {}
        # Deduplicacao
        self.seen_blocks = set()
        self.seen_txs = set()
        self.seen_lock = threading.Lock()
        # Seeds
        self.seeds = []
        self.irc_servers = []
        self.load_peers()
        self.load_seeds()
        def upnp_bg():
            try:
                tentar_upnp(P2P_PORT)
            except Exception:
                pass
        threading.Thread(target=upnp_bg, daemon=True).start()
        if TOR_ENABLED:
            threading.Thread(target=self._setup_tor, daemon=True).start()
        threading.Thread(target=self.server, daemon=True).start()
        threading.Thread(target=self.discovery_loop, daemon=True).start()
        threading.Thread(target=self.detect_ip_bg, daemon=True).start()
        threading.Thread(target=self.keepalive_loop, daemon=True).start()

    def _setup_tor(self):
        try:
            import stem
            from stem.control import Controller
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                response = controller.create_ephemeral_hidden_service({P2P_PORT: P2P_PORT}, await_publication=True)
                self.onion_address = response.service_id + ".onion"
                self.core.log(f"Tor: {self.onion_address}:{P2P_PORT}")
        except Exception as e:
            self.core.log(f"Tor: {e}")

    # ============================================================
    # CONEXAO PERSISTENTE
    # ============================================================
    def _conectar(self, host, timeout=10):
        with self.conn_lock:
            if host in self.active_connections:
                return self.active_connections[host]
        try:
            s = socket.create_connection((host, P2P_PORT), timeout=timeout)
            s.settimeout(None)
        except Exception as e:
            self.core.log(f"[P2P] CONNECT FALHOU {host}: {e}")
            return None
        if not self._do_handshake(s, host, outbound=True):
            try:
                s.close()
            except:
                pass
            return None
        with self.conn_lock:
            if host in self.active_connections:
                try:
                    s.close()
                except:
                    pass
                return self.active_connections[host]
            self.active_connections[host] = s
            self.send_queues[host] = []
        self.core.log(f"[P2P] PEER_ACTIVE {host} | Conexoes: {len(self.active_connections)}/{MAX_ACTIVE_CONNS}")
        self._iniciar_reader(host, s)
        self._iniciar_writer(host)
        return s

    def _iniciar_reader(self, host, s):
        if host in self.reader_threads:
            return
        def reader():
            try:
                while self.running:
                    if host not in self.active_connections:
                        break
                    msg = self._receber_msg(s, timeout=180)
                    if not msg:
                        break
                    self._processar_msg(host, msg)
            except Exception:
                pass
            finally:
                self._desconectar(host)
        t = threading.Thread(target=reader, daemon=True)
        self.reader_threads[host] = t
        t.start()

    def _iniciar_writer(self, host):
        if host in self.writer_threads:
            return
        def writer():
            while self.running:
                with self.conn_lock:
                    if host not in self.active_connections:
                        break
                    q = self.send_queues.get(host, [])
                    if not q:
                        item = None
                    else:
                        item = q.pop(0)
                if item is None:
                    time.sleep(0.05)
                    continue
                s = self.active_connections.get(host)
                if not s:
                    break
                try:
                    raw = json.dumps(item, separators=(",", ":")).encode()
                    tamanho = len(raw).to_bytes(4, "big")
                    s.sendall(tamanho + raw)
                except Exception as e:
                    self.core.log(f"[P2P] TX ERRO {host}: {e}")
                    self._desconectar(host)
                    break
        t = threading.Thread(target=writer, daemon=True)
        self.writer_threads[host] = t
        t.start()

    def _enfileirar(self, host, obj):
        with self.conn_lock:
            if host not in self.active_connections:
                return False
            self.send_queues.setdefault(host, []).append(obj)
            return True

    def _desconectar(self, host):
        with self.conn_lock:
            s = self.active_connections.pop(host, None)
            self.send_queues.pop(host, None)
            self.reader_threads.pop(host, None)
            self.writer_threads.pop(host, None)
        if s:
            try:
                s.close()
            except:
                pass
        self.core.log(f"[P2P] DISCONNECT {host} | Conexoes: {len(self.active_connections)}/{MAX_ACTIVE_CONNS}")

    # ============================================================
    # PROCESSAMENTO DE MENSAGENS
    # ============================================================
    def _processar_msg(self, host, msg):
        try:
            typ = msg.get("type")
            self.core.log(f"[P2P] RX {host} tipo={typ}")
            # Atualiza altura do peer se a mensagem trouxer
            with self.lock:
                if host in self.peers:
                    if "height" in msg:
                        self.peers[host]["last_height"] = int(msg.get("height", 0))
                    if "last_hash" in msg:
                        self.peers[host]["last_hash"] = msg.get("last_hash")
            # Atualiza altura do peer se a mensagem trouxer
            with self.lock:
                if host in self.peers:
                    if "height" in msg:
                        self.peers[host]["last_height"] = int(msg.get("height", 0))
                    if "last_hash" in msg:
                        self.peers[host]["last_hash"] = msg.get("last_hash")
            if typ == "ping":
                self._enfileirar(host, {"type": "pong"})
            elif typ == "pong":
                pass
            elif typ == "version":
                self._enfileirar(host, {
                    "type": "version", "proto": PROTOCOL_VERSION,
                    "min_proto": MIN_PROTOCOL_VERSION, "magic": MAGIC.hex(),
                    "nonce": secrets.token_hex(8), "height": self.core.bc.height(),
                    "last_hash": (self.core.bc.last_block() or {}).get("hash", "0" * 64),
                    "difficulty": self.core.bc.difficulty(),
                    "hashrate": self.core.bc.hashrate_rede(),
                    "user_agent": f"DogKong-v2/{VERSION}",
                    "is_hub": HUB_MODE, "is_seed": SEED_ONLY,
                    "is_principal": SOU_PRINCIPAL, "onion": self.onion_address
                })
            elif typ == "get_peers":
                with self.lock:
                    lst = [p for p in self.peers if p not in DEFAULT_SEEDS and p not in self.principal_ips and p != self.public_ip and p != host]
                    import random; random.shuffle(lst)
                    self._enfileirar(host, {"type": "peers", "peers": lst[:50]})
            elif typ == "peers":
                for p in msg.get("peers", [])[:MAX_PEERS]:
                    self.add_peer(p, outbound=True)
            elif typ == "get_chain":
                with self.core.bc.lock:
                    self._enfileirar(host, {"type": "chain", "chain": list(self.core.bc.chain)})
            elif typ == "chain":
                chain = msg.get("chain", [])
                if len(chain) > 100000:
                    self.ban_peer(host, 3600)
                else:
                    # Atualiza altura do peer com base na chain recebida
                    if chain:
                        altura_peer = int(chain[-1].get("height", 0))
                        with self.lock:
                            if host in self.peers:
                                self.peers[host]["last_height"] = altura_peer
                                self.core.log(f"[P2P] peer_height atualizado (chain): {host} = {altura_peer}")
                    if self.core.bc.accept_chain(chain):
                        self.core.log("Blockchain sincronizada")
                        self.core.schedule_refresh()
            elif typ == "get_headers":
                start = max(0, int(msg.get("start", 0)))
                headers = []
                with self.core.bc.lock:
                    for b in self.core.bc.chain[start:start + 2000]:
                        headers.append({"height": b["height"], "hash": b["hash"], "prev": b["prev"], "time": b["time"], "bits": b["bits"]})
                self._enfileirar(host, {"type": "headers", "headers": headers})
            elif typ == "get_blocks":
                start = max(0, int(msg.get("start", 0)))
                with self.core.bc.lock:
                    blocks = list(self.core.bc.chain[start:start + 500])
                self._enfileirar(host, {"type": "blocks", "blocks": blocks})
            elif typ == "get_mempool":
                with self.core.bc.lock:
                    self._enfileirar(host, {"type": "mempool", "tx": list(self.core.bc.mempool[:1000])})
            elif typ == "get_hashrate":
                self._enfileirar(host, {"type": "hashrate", "hashrate": self.core.bc.hashrate_rede(), "difficulty": self.core.bc.difficulty(), "next_difficulty": self.core.bc.target_difficulty()})
            elif typ == "tx":
                tx = msg.get("tx")
                if tx:
                    txid = tx.get("id")
                    with self.seen_lock:
                        if txid in self.seen_txs:
                            return
                        self.seen_txs.add(txid)
                    if self.core.bc.add_transaction(tx):
                        self.core.log(f"[P2P] TX {txid[:16]}... aceita")
                        self.broadcast({"type": "tx", "tx": tx}, exclude=host)
            elif typ == "block":
                blk = msg.get("block")
                if blk:
                    bh = blk.get("hash")
                    with self.seen_lock:
                        if bh in self.seen_blocks:
                            return
                        self.seen_blocks.add(bh)
                    # Atualiza altura do peer ANTES de processar
                    with self.lock:
                        if host in self.peers:
                            altura_bloco = int(blk.get("height", 0))
                            altura_atual = self.peers[host].get("last_height")
                            if altura_atual is None or altura_bloco > altura_atual:
                                self.peers[host]["last_height"] = altura_bloco
                                self.core.log(f"[P2P] peer_height atualizado: {host} = {altura_bloco}")
                    self.core.on_new_block(blk, host)
            elif typ == "addr":
                for p in msg.get("addrs", [])[:MAX_PEERS]:
                    self.add_peer(p, outbound=True)
            else:
                self._enfileirar(host, {"type": "ok"})
        except Exception as e:
            self.core.log(f"[P2P] ERRO processar {host}: {e}")

    # ============================================================
    # HANDSHAKE
    # ============================================================
    def _do_handshake(self, sock, host, outbound=False):
        try:
            my_nonce = secrets.token_bytes(8)
            hello = {
                "type": "version", "proto": PROTOCOL_VERSION,
                "min_proto": MIN_PROTOCOL_VERSION, "magic": MAGIC.hex(),
                "nonce": my_nonce.hex(), "height": self.core.bc.height(),
                "last_hash": (self.core.bc.last_block() or {}).get("hash", "0" * 64),
                "difficulty": self.core.bc.difficulty(),
                "hashrate": self.core.bc.hashrate_rede(),
                "peers": list(self.peers)[:MAX_PEERS],
                "user_agent": f"DogKong-v2/{VERSION}",
                "is_hub": HUB_MODE, "is_seed": SEED_ONLY,
                "is_principal": SOU_PRINCIPAL, "onion": self.onion_address,
            }
            raw = json.dumps(hello, separators=(",", ":")).encode()
            sock.sendall(len(raw).to_bytes(4, "big") + raw)
            reply = self._receber_msg(sock, timeout=HANDSHAKE_TIMEOUT)
            if not reply or reply.get("type") != "version":
                return None
            if reply.get("magic") != MAGIC.hex():
                self.ban_peer(host, 3600)
                return None
            if int(reply.get("proto", 0)) < MIN_PROTOCOL_VERSION:
                return None
            if reply.get("nonce") == my_nonce.hex():
                return None
            if reply.get("is_principal"):
                self.principal_ips.add(host)
            # Guarda altura do peer do handshake
            altura_peer = int(reply.get("height", 0))
            with self.lock:
                if host in self.peers:
                    self.peers[host]["last_height"] = altura_peer
                else:
                    self.peers[host] = {"last_seen": time.time(), "first_seen": time.time(), "failures": 0, "next_retry": 0, "last_height": altura_peer}
            self.core.log(f"[P2P] HANDSHAKE OK {host} | altura peer={altura_peer}")
            return reply
        except Exception as e:
            self.core.log(f"[P2P] HANDSHAKE ERRO {host}: {e}")
            return None

    def _enviar_msg(self, sock, obj):
        raw = json.dumps(obj, separators=(",", ":")).encode()
        sock.sendall(len(raw).to_bytes(4, "big") + raw)

    def _receber_msg(self, sock, timeout=None):
        if timeout:
            sock.settimeout(timeout)
        cab = b""
        while len(cab) < 4:
            p = sock.recv(4 - len(cab))
            if not p:
                return None
            cab += p
        tam = int.from_bytes(cab, "big")
        if tam <= 0 or tam > MAX_MSG_BYTES:
            return None
        dados = b""
        while len(dados) < tam:
            p = sock.recv(min(65536, tam - len(dados)))
            if not p:
                return None
            dados += p
        try:
            return json.loads(dados.decode("utf-8"))
        except:
            return None

    # ============================================================
    # SERVER (aceita conexoes de entrada)
    # ============================================================
    def server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", P2P_PORT))
            s.listen(MAX_PEERS)
        except Exception as e:
            self.core.log(f"[P2P] Porta {P2P_PORT} indisponivel: {e}")
            return
        self.server_sock = s
        self.core.log(f"[P2P] Escutando na porta {P2P_PORT}")
        while self.running:
            try:
                c, addr = s.accept()
                host = addr[0]
                if self._is_banned(host):
                    c.close()
                    continue
                if host in self.active_connections:
                    c.close()
                    continue
                if len(self.active_connections) >= MAX_ACTIVE_CONNS:
                    c.close()
                    continue
                threading.Thread(target=self._aceitar_conexao, args=(c, host), daemon=True).start()
            except Exception:
                if not self.running:
                    break
                time.sleep(0.5)

    def _aceitar_conexao(self, c, host):
        try:
            handshake = self._do_handshake(c, host, outbound=False)
            if not handshake:
                c.close()
                return
            # Guarda altura do peer
            altura_peer = int(handshake.get("height", 0))
            with self.lock:
                if host in self.peers:
                    self.peers[host]["last_height"] = altura_peer
                else:
                    self.peers[host] = {"last_seen": time.time(), "first_seen": time.time(), "failures": 0, "next_retry": 0, "last_height": altura_peer}
            with self.conn_lock:
                if host in self.active_connections:
                    c.close()
                    return
                self.active_connections[host] = c
                self.send_queues[host] = []
            self.core.log(f"[P2P] PEER_ACTIVE {host} | Conexoes: {len(self.active_connections)}/{MAX_ACTIVE_CONNS}")
            self._iniciar_reader(host, c)
            self._iniciar_writer(host)
        except Exception as e:
            self.core.log(f"[P2P] ERRO accept {host}: {e}")
            try:
                c.close()
            except:
                pass

    # ============================================================
    # PEERS
    # ============================================================
    def add_peer(self, host, outbound=False):
        if not isinstance(host, str) or not host:
            return
        if self.public_ip and host == self.public_ip:
            return
        if host in DEFAULT_SEEDS:
            return
        if ":" in host:
            host = host.split(":")[0]
        if self._is_banned(host):
            return
        if host in ("127.0.0.1", "localhost") and host not in self.seeds:
            return
        with self.lock:
            if host in self.peers:
                self.peers[host]["last_seen"] = time.time()
                self.peers[host]["failures"] = 0
                if outbound:
                    self.outbound_peers.add(host)
                return
            if len(self.peers) >= MAX_PEERS:
                return
            self.peers[host] = {"last_seen": time.time(), "first_seen": time.time(), "failures": 0, "next_retry": 0}
            self.peers_per_ip.setdefault(host, set()).add(host)
            if outbound:
                self.outbound_peers.add(host)
        self.save_peers()
        if outbound and host not in self.active_connections:
            threading.Thread(target=self._conectar, args=(host,), daemon=True).start()

    def load_peers(self):
        data = load_json(PEERS_FILE, [])
        agora = time.time()
        self.peers = {}
        if isinstance(data, list):
            for p in data:
                if isinstance(p, str) and p:
                    self.peers[p] = {"last_seen": agora, "first_seen": agora, "failures": 0}
        elif isinstance(data, dict):
            for ip, info in data.items():
                if isinstance(ip, str) and ip:
                    if isinstance(info, dict):
                        self.peers[ip] = {"last_seen": info.get("last_seen", agora), "first_seen": info.get("first_seen", agora), "failures": info.get("failures", 0)}
                    elif isinstance(info, (int, float)):
                        self.peers[ip] = {"last_seen": info, "first_seen": info, "failures": 0}

    def save_peers(self):
        try:
            agora = time.time()
            para_remover = []
            for ip, info in self.peers.items():
                last = info.get("last_seen", 0)
                fails = info.get("failures", 0)
                if (agora - last > 7 * 86400) or (fails >= 5):
                    para_remover.append(ip)
            for ip in para_remover:
                self.peers.pop(ip, None)
            if len(self.peers) > 1000:
                ordenados = sorted(self.peers.items(), key=lambda x: (x[1].get("failures", 0), -x[1].get("last_seen", 0)))
                self.peers = dict(ordenados[:1000])
            save_json(PEERS_FILE, self.peers)
        except:
            pass

    def load_seeds(self):
        seeds = load_json(SEEDS_FILE, None)
        if seeds is None:
            seeds = {"irc": [], "dns": []}
            try:
                save_json(SEEDS_FILE, seeds)
            except:
                pass
        if isinstance(seeds, dict):
            self.seeds = [s for s in seeds.get("dns", []) if isinstance(s, str)]
            self.irc_servers = []
        else:
            self.seeds = [s for s in seeds if isinstance(s, str)]
            self.irc_servers = list(IRC_SERVERS)
        for ip in HARDCODED_IPS:
            if ip not in self.seeds:
                self.seeds.append(ip)
        agora = time.time()
        for s in self.seeds:
            if s not in self.peers:
                self.peers[s] = {"last_seen": agora, "first_seen": agora, "failures": 0}
        def resolver_bg():
            try:
                ips_dns = resolver_dns_seeds(self.seeds)
                ips_duck = resolver_duckdns()
                ips = list(set(ips_dns + ips_duck))
                for ip in ips:
                    self.core.log(f"[P2P] SEED {ip}")
                    self.add_peer(ip, outbound=True)
            except Exception as e:
                self.core.log(f"[P2P] SEED falhou: {e}")
        threading.Thread(target=resolver_bg, daemon=True).start()
        self.save_peers()

    def sync_chain(self, host):
        try:
            s = self._conectar(host)
            if not s:
                return False
            # So pede chain se ja temos altura menor que o peer
            with self.lock:
                info = self.peers.get(host, {})
                altura_peer = info.get("last_height", 0)
            if altura_peer > 0 and altura_peer <= self.core.bc.height():
                return True
            self.core.log(f"[SYNC] Pedindo chain para {host} (local={self.core.bc.height()} peer={altura_peer})")
            self._enfileirar(host, {"type": "get_chain"})
            return True
        except Exception as e:
            self.core.log(f"[P2P] SYNC ERRO {host}: {e}")
            return False

    def sync_peer(self, host):
        if self._is_banned(host):
            return False
        self.add_peer(host, outbound=True)
        return self.sync_chain(host)

    def broadcast(self, msg, exclude=None):
        with self.conn_lock:
            hosts = list(self.active_connections.keys())
        enviados = 0
        for h in hosts:
            if h == exclude:
                continue
            if self._enfileirar(h, msg):
                enviados += 1
        if enviados > 0:
            self.core.log(f"[P2P] TX broadcast {msg.get('type')} -> {enviados} peers")

    def discovery_loop(self):
        time.sleep(5)
        while self.running:
            try:
                agora_loop = time.time()
                with self.conn_lock:
                    ativos = set(self.active_connections.keys())
                with self.lock:
                    candidatos = [p for p, info in self.peers.items()
                                  if info.get("failures", 0) < 5
                                  and info.get("next_retry", 0) <= agora_loop
                                  and p not in ativos
                                  and p != self.public_ip]
                import random
                random.shuffle(candidatos)
                for p in candidatos[:5]:
                    threading.Thread(target=self._conectar, args=(p,), daemon=True).start()
            except Exception as e:
                self.core.log(f"[P2P] DISCOVERY erro: {e}")
            time.sleep(10)


    def keepalive_loop(self):
        time.sleep(30)
        while self.running:
            try:
                with self.conn_lock:
                    hosts = list(self.active_connections.keys())
                for h in hosts:
                    self._enfileirar(h, {"type": "ping"})
            except:
                pass
            time.sleep(30)

    def detect_ip_bg(self):
        ip = detect_public_ip()
        if ip:
            self.public_ip = ip
            self.core.log(f"[P2P] IP publico: {ip}:{P2P_PORT}")

    def _is_banned(self, host):
        with self.ban_lock:
            until = self.banned.get(host, 0)
            if until > time.time():
                return True
            if until:
                self.banned.pop(host, None)
            return False

    def ban_peer(self, host, seconds=PEER_BAN_TIME):
        with self.ban_lock:
            self.banned[host] = time.time() + seconds
        self._desconectar(host)
        self.core.log(f"[P2P] BAN {host} ({seconds}s)")

    def shutdown(self):
        self.running = False
        with self.conn_lock:
            hosts = list(self.active_connections.keys())
        for h in hosts:
            self._desconectar(h)
        try:
            if self.server_sock:
                self.server_sock.close()
        except:
            pass


class MinerBridge:
    """Bridge que se comunica com o minerador C++ via socket local."""
    def __init__(self, core):
        self.core = core
        self.socket_server = None
        self.socket_client = None
        self.processo = None
        self.rodando = False
        self.minerando = False
        self.thread_aceitar = None
        self.thread_receber = None
        self.lock = threading.Lock()
        self.template_atual = None
        self.nonce_atual = 0

    def iniciar_minerador(self):
        """Executa dogkong_miner.exe e conecta via socket."""
        import subprocess
        caminho_miner = _caminho_recurso("dogkong_miner.exe")
        if not os.path.exists(caminho_miner):
            self.core.log("[MINER] dogkong_miner.exe nao encontrado")
            return False
        try:
            self.processo = subprocess.Popen(
                [caminho_miner],
                cwd=BASE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            self.core.log("[MINER] Minerador C++ iniciado")
            return True
        except Exception as e:
            self.core.log(f"[MINER] Erro ao iniciar: {e}")
            return False

    def iniciar_servidor(self):
        """Abre socket local na porta 18556."""
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_server.bind(("127.0.0.1", 18556))
        self.socket_server.listen(1)
        self.rodando = True
        self.core.log("[MINER] Aguardando minerador na porta 18556...")
        self.thread_aceitar = threading.Thread(target=self._aceitar, daemon=True)
        self.thread_aceitar.start()

    def _aceitar(self):
        """Aceita conexao do minerador."""
        try:
            self.socket_server.settimeout(30)
            self.socket_client, addr = self.socket_server.accept()
            self.core.log(f"[MINER] Minerador conectado: {addr}")
            self.socket_client.settimeout(None)
            self.thread_receber = threading.Thread(target=self._receber, daemon=True)
            self.thread_receber.start()
            # NAO manda template automatico. So minera quando clicar em "Minerar".
        except socket.timeout:
            self.core.log("[MINER] Timeout: minerador nao conectou")
        except Exception as e:
            self.core.log(f"[MINER] Erro no accept: {e}")

    def _receber(self):
        """Recebe nonce + hash do minerador."""
        buffer = b""
        while self.rodando:
            try:
                dados = self.socket_client.recv(65536)
                if not dados:
                    self.core.log("[MINER] Minerador desconectou")
                    break
                buffer += dados
                while b"\n" in buffer:
                    linha, buffer = buffer.split(b"\n", 1)
                    self._processar_resultado(linha.decode().strip())
            except Exception as e:
                self.core.log(f"[MINER] Erro no recv: {e}")
                break

    def _processar_resultado(self, linha):
        """Processa o nonce + hash recebido do minerador."""
        try:
            resultado = json.loads(linha)
            nonce = int(resultado.get("nonce", 0))
            hash_final = resultado.get("hash", "")
            self.core.log(f"[MINER] Bloco encontrado! nonce={nonce} hash={hash_final[:16]}...")
            self._validar_e_adicionar(nonce, hash_final)
        except Exception as e:
            self.core.log(f"[MINER] Erro ao processar: {e}")

    def _coletar_peers_para_bloco(self):
        # DESABILITADO: nunca salva peers nos blocos
        return []

    def _validar_e_adicionar(self, nonce, hash_final):
        """Valida o bloco e adiciona na blockchain."""
        with self.core.bc.lock:
            template = self.template_atual
            if not template:
                return
            height = template["height"]
            mempool_txs = list(self.core.bc.mempool[:MAX_BLOCK_TX - 1])
            coinbase = self.core.bc.create_coinbase(self.core.wallet.address, height, mempool_txs)
            block = {
                "height": height,
                "time": template["time"],
                "prev": template["prev"],
                "bits": template["bits"],
                "nonce": nonce,
                "miner": template["miner"],
                "tx": [coinbase] + mempool_txs,
                "hash": hash_final,
                "peers": [],
            }
            if self.core.bc.chain[-1]["hash"] != template["prev"]:
                self.core.log("[MINER] Chain mudou, abortando bloco")
                self.minerar()
                return
            if not self.core.bc.valid_pow(block):
                self.core.log("[MINER] PoW invalido, descartando")
                self.minerar()
                return
            self.core.bc.chain.append(block)
            used = {x.get("id") for x in block.get("tx", [])}
            self.core.bc.mempool = [x for x in self.core.bc.mempool if x.get("id") not in used]
            self.core.bc.save()
            self.core.log("*** BLOCO " + str(height) + " ***")
            self.core.log("Hash: " + hash_final)
            self.core.network.broadcast({"type": "block", "block": block})
            self.core.schedule_refresh()
            self.minerar()

    def minerar(self):
        """Manda template pro minerador."""
        with self.lock:
            if not self.socket_client:
                self.core.log("[MINER] Minerador nao conectado")
                return False
            # Monta template
            with self.core.bc.lock:
                height = self.core.bc.height() + 1
                previous = dict(self.core.bc.chain[-1])
            block_time = now()
            if block_time <= int(previous["time"]):
                block_time = int(previous["time"]) + 1
            with self.core.bc.lock:
                bits = self.core.bc.target_difficulty(candidate_time=block_time)
                mempool_txs = self.core.bc.mempool[:MAX_BLOCK_TX - 1]
                coinbase = self.core.bc.create_coinbase(self.core.wallet.address, height, mempool_txs)
                txs = [coinbase] + mempool_txs
            template = {
                "height": height,
                "time": block_time,
                "prev": previous["hash"],
                "bits": bits,
                "miner": self.core.wallet.address,
            }
            self.template_atual = template
            self.minerando = True
            try:
                raw = json.dumps(template, separators=(",", ":")).encode() + b"\n"
                self.socket_client.sendall(raw)
                self.core.log(f"[MINER] Template enviado: bloco #{height} | bits 0x{bits:08X}")
                return True
            except Exception as e:
                self.core.log(f"[MINER] Erro ao enviar template: {e}")
                return False

    def parar(self):
        """Manda STOP pro minerador."""
        with self.lock:
            self.minerando = False
            if self.socket_client:
                try:
                    self.socket_client.sendall(b"STOP\n")
                    self.core.log("[MINER] STOP enviado")
                except Exception:
                    pass

    @property
    def hashrate_pc(self):
        return 5600.0

    @property
    def hashrate_alvo(self):
        return 5600.0

    def hashrate_local(self):
        return 5600.0

    def is_running(self):
        return self.minerando

    def fechar(self):
        """Fecha tudo."""
        self.rodando = False
        self.minerando = False
        if self.socket_client:
            try:
                self.socket_client.sendall(b"EXIT\n")
            except Exception:
                pass
            try:
                self.socket_client.close()
            except Exception:
                pass
        if self.socket_server:
            try:
                self.socket_server.close()
            except Exception:
                pass
        if self.processo:
            try:
                self.processo.terminate()
                self.processo.wait(timeout=5)
            except Exception:
                try:
                    self.processo.kill()
                except Exception:
                    pass
        self.core.log("[MINER] Fechado")

class DogKongCore:
    def __init__(self):
        self.wallet = Wallet()
        # SEED_ONLY agora tem chain REAL (nao stub)
        self.bc = Blockchain()
        self.logs = []
        self._refresh_queued = False
        self.global_rate = {}
        self.global_rate_lock = threading.Lock()

        self.root = tk.Tk()
        self.root.title(f"{APP} {VERSION}")
        self.root.geometry("680x660")
        self.root.minsize(620, 600)
        self.root.configure(bg="#d4d0c8")

        self.style = ttk.Style()
        try:
            self.style.theme_use("classic")
        except:
            pass

        self.network = Network(self)
        if SOU_PRINCIPAL:
            self.miner = None
            self.log("[PRINCIPAL] Modo principal: minerador desativado, chain salva")
        else:
            self.miner = MinerBridge(self)
            self.miner.iniciar_servidor()
            self.miner.iniciar_minerador()

        # ===== WATCHER DE TX DA CARTEIRA WEB =====
        threading.Thread(target=self._tx_watcher, daemon=True).start()

        self.build_menu()
        self.build_toolbar()
        self.build_main()
        self.build_status()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.refresh()
        threading.Thread(target=self.initial_sync, daemon=True).start()

    def _tx_watcher(self):
        import time, json, os
        PENDING = os.path.join(DATA, "pending_tx_local.json")
        while True:
            try:
                if os.path.exists(PENDING):
                    with open(PENDING, "r", encoding="utf-8") as f:
                        txs = json.load(f)
                    if txs:
                        for tx in txs:
                            txid = tx.get("id")
                            if txid:
                                if self.bc.add_transaction(tx):
                                    self.log("TX injetada: " + txid[:16] + "...")
                                    try:
                                        self.network.broadcast({"type": "tx", "tx": tx})
                                    except:
                                        pass
                                else:
                                    self.log("TX rejeitada: " + txid[:16] + "...")
                        with open(PENDING, "w", encoding="utf-8") as f:
                            json.dump([], f)
            except Exception as e:
                self.log(f"TX watcher erro: {e}")
            time.sleep(3)

    def _global_rate_ok(self, ip):
        agora = time.time()
        with self.global_rate_lock:
            lst = self.global_rate.setdefault(ip, [])
            lst[:] = [t for t in lst if agora - t < 60]
            if len(lst) >= 300:
                return False
            lst.append(agora)
            return True

    def log(self, text):
        self.logs.append(time.strftime("%H:%M:%S") + "  " + text)
        self.logs = self.logs[-200:]
        try:
            self.root.after(0, self.update_log)
        except:
            pass

    def update_log(self):
        if not hasattr(self, "logbox"):
            return
        try:
            self.logbox.delete("1.0", tk.END)
            self.logbox.insert(tk.END, "\n".join(self.logs))
            self.logbox.see(tk.END)
        except:
            pass

    def on_close(self):
        try:
            self.miner.stop()
        except:
            pass
        try:
            self.network.shutdown()
        except:
            pass
        try:
            with self.bc.lock:
                save_json(CHAIN_FILE, self.bc.chain)
                save_json(MEMPOOL_FILE, self.bc.mempool)
        except:
            pass
        try:
            self.wallet.save()
        except:
            pass
        try:
            self.root.destroy()
        except:
            pass

    def initial_sync(self):
        self.log("Sincronizando...")
        with self.network.lock:
            peers = list(self.network.peers)
        if not peers:
            self.log("Nenhum peer. Modo standalone.")
            self.log(f"Bloco local: #{self.bc.height()}")
            return
        # Bootstrap: SO PRINCIPAL cria genesis. Peer espera baixar.
        if not self.bc.chain:
            if SOU_PRINCIPAL:
                self.log("[BOOTSTRAP] PRINCIPAL sem chain. Criando genesis local...")
                try:
                    genesis = self.bc.criar_bloco_genesis()
                    self.bc.chain = [genesis]
                    self.bc._aguardando_sync = False
                    self.bc.save()
                    self.log(f"[BOOTSTRAP] Genesis criado: #{genesis['height']}")
                except Exception as e:
                    self.log(f"[BOOTSTRAP] Erro: {e}")
                return
            else:
                self.log("[BOOTSTRAP] Peer sem chain. Baixando da rede...")
        # Principal: tenta TODOS os peers em paralelo pra achar chain maior
        if SOU_PRINCIPAL:
            self.log(f"[PRINCIPAL] Bootstrap: tentando {len(peers)} peer(s)")
            import concurrent.futures
            def _try(p):
                try:
                    return self.network.sync_peer(p)
                except Exception:
                    return False
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                list(ex.map(_try, peers))
        else:
            for p in peers:
                try:
                    self.network.sync_peer(p)
                except Exception:
                    pass
        self.log(f"Sincronizado. Bloco: #{self.bc.height()}")
        # NAO chama schedule_refresh (evita parar minerador)

    def on_new_block(self, block, from_host):
        bc = self.bc
        precisa_sync = False
        with bc.lock:
            height = int(block.get("height", -1))
            if height != bc.height() + 1:
                if height > bc.height() + 1:
                    precisa_sync = True
                else:
                    return
            else:
                if int(block.get("time", 0)) > now() + MAX_FUTURE_TIME:
                    self.network.ban_peer(from_host, 3600)
                    return
                if int(block.get("time", 0)) < int(bc.chain[-1].get("time", 0)):
                    return
                if int(block.get("time", 0)) > int(bc.chain[-1].get("time", 0)) + MAX_FUTURE_TIME:
                    return
                if block.get("prev") != bc.chain[-1]["hash"]:
                    return
                if not bc.valid_pow(block):
                    return
                bits_recebidos = int(block["bits"])
                bits_esperados = bc.target_difficulty(candidate_time=int(block["time"]))
                if bits_recebidos != bits_esperados:
                    self.log(
                        f"Bloco #{height} rejeitado: "
                        f"bits 0x{bits_recebidos:08X} != esperado 0x{bits_esperados:08X}"
                    )
                    return
                txs = block.get("tx", [])
                if not txs:
                    return
                coinbases = 0
                for tx in txs:
                    if tx.get("from") == "COINBASE":
                        coinbases += 1
                        if abs(float(tx.get("amount", -1)) - block_reward(height)) > 1e-8:
                            return
                        continue
                    try:
                        pub = bytes.fromhex(tx["pubkey"])
                    except Exception:
                        return
                    if address_from_pub(pub) != tx["from"]:
                        return
                    if h(tx_message(tx).encode()) != tx["id"]:
                        return
                    if not verify(pub, tx["id"], tx["signature"]):
                        return
                if coinbases != 1:
                    return
                bc.chain.append(block)
                used = {x.get("id") for x in txs}
                bc.mempool = [x for x in bc.mempool if x.get("id") not in used]
                bc.save()
                add_notificacao(f"Bloco #{height} recebido de {from_host}")
                self.log(
                    f"Bloco #{height} de {from_host} | bits 0x{block['bits']:08X} | "
                    f"hashrate rede ~{bc.hashrate_rede():.0f} H/s"
                )
                self.network.broadcast({"type": "block", "block": block}, exclude=from_host)
                self.schedule_refresh()
                return
        if precisa_sync:
            self.network.sync_chain(from_host)

    def build_menu(self):
        menu = tk.Menu(self.root, tearoff=0)

        filemenu = tk.Menu(menu, tearoff=0)
        filemenu.add_command(label=t("new_wallet"), command=self.new_wallet)
        filemenu.add_command(label=t("import_wif"), command=self.import_wif)
        filemenu.add_command(label=t("restore_mnemonic"), command=self.restore_mnemonic)
        filemenu.add_separator()
        filemenu.add_command(label=t("show_wallet"), command=self.show_keys)
        filemenu.add_command(label=t("backup"), command=self.backup)
        filemenu.add_separator()
        filemenu.add_command(label=t("set_password"), command=self.set_password)
        filemenu.add_command(label=t("remove_password"), command=self.remove_password)
        filemenu.add_command(label=t("change_password"), command=self.change_password)
        filemenu.add_separator()
        filemenu.add_command(label=t("exit"), command=self.on_close)
        menu.add_cascade(label=t("file_menu"), menu=filemenu)

        langmenu = tk.Menu(menu, tearoff=0)
        self.lang_var = tk.StringVar(value=LANG)
        for code, name in LANGUAGES.items():
            langmenu.add_radiobutton(
                label=name,
                variable=self.lang_var,
                value=code,
                command=lambda c=code: self.change_language(c)
            )
        menu.add_cascade(label=t("lang_menu"), menu=langmenu)

        settings = tk.Menu(menu, tearoff=0)
        settings.add_command(label=t("connect_peer"), command=self.connect_peer)
        settings.add_command(label=t("sync_network"), command=self.sync)
        settings.add_command(label=t("edit_seeds"), command=self.edit_seeds)
        settings.add_separator()
        settings.add_command(label="Redefinir limite de H/s", command=self.reset_hashrate)
        menu.add_cascade(label=t("settings_menu"), menu=settings)

        notifmenu = tk.Menu(menu, tearoff=0)
        notifmenu.add_command(label="Ver notificacoes", command=self.mostrar_notificacoes)
        notifmenu.add_command(label="Limpar notificacoes", command=self.limpar_notificacoes)
        self.notifmenu = notifmenu
        self.notif_index = menu.index(tk.END) + 1
        menu.add_cascade(label="Notificacao", menu=self.notifmenu)
        self._menu_ref = menu

        helpmenu = tk.Menu(menu, tearoff=0)
        helpmenu.add_command(label=t("about"), command=self.about)
        menu.add_cascade(label=t("help_menu"), menu=helpmenu)

        self.root.config(menu=menu)

    def change_language(self, code):
        global LANG
        LANG = code
        save_lang()
        for w in self.root.winfo_children():
            w.destroy()
        self.build_menu()
        self.build_toolbar()
        self.build_main()
        self.build_status()
        self.refresh()
        self.log(f"Idioma: {LANGUAGES[code]}")

    def build_toolbar(self):
        bar = tk.Frame(self.root, bg="#d4d0c8", relief=tk.RAISED, bd=2)
        bar.pack(fill=tk.X)

        buttons = [
            (t("overview"), self.overview),
            (t("send"), self.send_page),
            (t("receive"), self.receive_page),
            (t("transactions"), self.transactions),
            (t("history"), self.history_page),
            (t("network"), self.network_page),
        ]
        for text, cmd in buttons:
            tk.Button(
                bar, text=text, command=cmd,
                relief=tk.RAISED, width=9, font=("Arial", 8)
            ).pack(side=tk.LEFT, padx=1, pady=3)

        tk.Button(
            bar,
            text=t("refresh"),
            command=self.refresh_page,
            relief=tk.RAISED,
            width=11,
            font=("Arial", 9, "bold"),
            bg="#f39c12",
            fg="white",
            activebackground="#f1c40f"
        ).pack(side=tk.LEFT, padx=2, pady=3)

        self.btn_stop = tk.Button(
            bar,
            text=t("stop_mining"),
            command=self.stop_mining,
            width=10,
            relief=tk.RAISED,
            bg="#c0392b",
            fg="white",
            activebackground="#e74c3c",
            font=("Arial", 8)
        )
        self.btn_stop.pack(side=tk.RIGHT, padx=2)

        self.btn_start = tk.Button(
            bar,
            text=t("start_mining"),
            command=self.start_mining,
            width=12,
            relief=tk.RAISED,
            bg="#c0392b",
            fg="white",
            activebackground="#e74c3c",
            font=("Arial", 8)
        )
        self.btn_start.pack(side=tk.RIGHT, padx=2)

    def update_mining_buttons(self):
        if self.miner is None:
            try:
                self.btn_start.config(bg="#7f8c8d", activebackground="#7f8c8d", state="disabled")
                self.btn_stop.config(bg="#7f8c8d", activebackground="#7f8c8d", state="disabled")
            except Exception:
                pass
            return
        if self.miner.is_running():
            self.btn_start.config(bg="#27ae60", activebackground="#2ecc71")
            self.btn_stop.config(bg="#27ae60", activebackground="#2ecc71")
        else:
            self.btn_start.config(bg="#c0392b", activebackground="#e74c3c")
            self.btn_stop.config(bg="#c0392b", activebackground="#e74c3c")

    def refresh_page(self):
        self.log("Atualizando...")
        self.overview()
        self.refresh_once()

    def build_main(self):
        self.main = tk.Frame(self.root, bg="#ece9e2")
        self.main.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.title = tk.Label(
            self.main, text="DogKong v2",
            font=("Arial", 14, "bold"), bg="#ece9e2"
        )
        self.title.pack(anchor="w")

        self.build_log()

        self.content = tk.Frame(self.main, bg="#ece9e2")
        self.content.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.overview()

    def build_log(self):
        frame = tk.LabelFrame(self.main, text=t("network_events"), bg="#ece9e2")
        frame.pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=(4, 4))

        self.logbox = tk.Text(
            frame, height=6, bg="white",
            relief=tk.SUNKEN, bd=2, font=("Courier", 8)
        )
        self.logbox.pack(fill=tk.X, padx=4, pady=4)

    def build_status(self):
        self.status = tk.StringVar()
        tk.Label(
            self.root,
            textvariable=self.status,
            anchor="w",
            relief=tk.SUNKEN,
            bd=1,
            font=("Courier", 8)
        ).pack(fill=tk.X, side=tk.BOTTOM)

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def overview(self):
        self.clear()

        if self.wallet.is_locked():
            self.show_unlock_screen()
            return

        bal = self.bc.balance(self.wallet.address, min_conf=1)
        frame = tk.Frame(self.content, bg="#ece9e2")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=t("balance"), font=("Arial", 10), bg="#ece9e2").pack(anchor="w", pady=(2, 0))
        tk.Label(frame, text=f"{bal:.8f} DOGK", font=("Arial", 16, "bold"), bg="#ece9e2").pack(anchor="w")

        net = tk.LabelFrame(frame, text="Rede DogKong v2", bg="#ece9e2")
        net.pack(fill=tk.X, pady=4)

        with self.network.lock:
            peers = len(self.network.peers)

        hashrate_rede = self.bc.hashrate_rede()
        hashrate_local = self.miner.hashrate_local() if self.miner is not None else 0.0
        bits_atual = self.bc.difficulty()
        bits_prox = self.bc.target_difficulty()

        public_ip = self.network.public_ip or "(...)"
        rows = [
            (t("block"), f"#{self.bc.height()}"),
            (t("difficulty"), f"0x{bits_atual:08X}"),
            (t("next_diff"), f"0x{bits_prox:08X}"),
            (t("hashrate_net"), self._fmt_hashrate(hashrate_rede)),
            (t("hashrate_local"), self._fmt_hashrate(hashrate_local)),
            (t("peers"), str(peers)),
            (t("mempool"), str(len(self.bc.mempool))),
            (t("reward"), f"{REWARD_PER_BLOCK:.2f} DOGK"),
            (t("public_ip"), public_ip),
            (t("pow"), f"CPU+RAM ({MEMORY_MB}MB)"),
        ]
        for i, (k, v) in enumerate(rows):
            tk.Label(net, text=k + ":", bg="#ece9e2", font=("Arial", 8, "bold")).grid(
                row=i, column=0, sticky="w", padx=4, pady=1)
            ent = tk.Entry(net, width=50, font=("Courier", 8))
            ent.insert(0, str(v))
            ent.config(state="readonly")
            ent.grid(row=i, column=1, sticky="w", padx=4, pady=1)

        box = tk.LabelFrame(frame, text=t("your_wallet"), bg="#ece9e2")
        box.pack(fill=tk.X, pady=4)

        tk.Label(box, text=t("address"), bg="#ece9e2", font=("Arial", 8)).grid(
            row=0, column=0, sticky="w", padx=4, pady=2)
        e = tk.Entry(box, width=52, font=("Courier", 8))
        e.insert(0, self.wallet.address)
        e.config(state="readonly")
        e.grid(row=1, column=0, padx=4, pady=2)
        tk.Button(box, text=t("copy"), command=lambda: self.copy(self.wallet.address),
                  font=("Arial", 8)).grid(row=1, column=1, padx=2)

        btn_frame = tk.Frame(box, bg="#ece9e2")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=3, sticky="w")
        tk.Button(btn_frame, text=t("wif_mnemonic"), command=self.show_keys,
                  font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text=t("copy_p2p"), command=self.copy_p2p,
                  font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
        if self.wallet.encrypted:
            tk.Button(btn_frame, text=t("password_on"), fg="green",
                      font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=2)

        if bits_atual > bits_prox:
            aviso = f"Dificuldade subindo: 0x{bits_atual:08X} -> 0x{bits_prox:08X}"
        elif bits_atual < bits_prox:
            aviso = f"Dificuldade caindo: 0x{bits_atual:08X} -> 0x{bits_prox:08X}"
        else:
            aviso = f"Dificuldade estavel em 0x{bits_atual:08X} (meta: 1 bloco/{BLOCK_TIME}s)"
        tk.Label(frame, text=aviso, bg="#ece9e2", font=("Arial", 9, "bold"),
                 fg="#2c3e50").pack(anchor="w", pady=(6, 0))

    def _fmt_hashrate(self, h):
        if h <= 0:
            return "0 H/s"
        if h < 1_000:
            return f"{h:.1f} H/s"
        if h < 1_000_000:
            return f"{h/1_000:.1f} kH/s"
        if h < 1_000_000_000:
            return f"{h/1_000_000:.2f} MH/s"
        return f"{h/1_000_000_000:.2f} GH/s"

    def show_unlock_screen(self):
        frame = tk.Frame(self.content, bg="#ece9e2")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=t("wallet_locked"), font=("Arial", 14, "bold"),
                 bg="#ece9e2", fg="#c0392b").pack(pady=20)
        tk.Label(frame, text=t("unlock_hint"), bg="#ece9e2").pack()

        senha_entry = tk.Entry(frame, show="*", width=30)
        senha_entry.pack(pady=8)
        senha_entry.focus()

        def try_unlock():
            ok, restantes = PASSWORD_GUARD.check()
            if not ok:
                messagebox.showerror("DogKong v2", t("wait_sec").format(s=restantes))
                return
            senha = senha_entry.get()
            if not senha:
                return
            if self.wallet.unlock(senha):
                PASSWORD_GUARD.reset()
                self.log("Carteira desbloqueada")
                self.overview()
            else:
                delay = PASSWORD_GUARD.register_failure()
                senha_entry.delete(0, tk.END)
                msg = t("wrong_pass")
                if delay > 0:
                    msg += "\n" + t("wait_sec").format(s=delay)
                messagebox.showerror("DogKong v2", msg)

        senha_entry.bind("<Return>", lambda e: try_unlock())
        tk.Button(frame, text=t("unlock_btn"), command=try_unlock, width=20).pack(pady=8)
        tk.Label(frame, text="AVISO: " + t("never_share"), fg="red", bg="#ece9e2",
                 font=("Arial", 8)).pack(pady=10)

    def copy_p2p(self):
        ip = self.network.public_ip
        if not ip:
            messagebox.showwarning("DogKong v2", "IP ainda nao detectado.")
            return
        txt = f"{ip}:{P2P_PORT}"
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.root.update()
        messagebox.showinfo("DogKong v2", f"P2P copiado:\n{txt}")

    def receive_page(self):
        self.clear()
        tk.Label(self.content, text=t("receive") + " DOGK",
                 font=("Arial", 13, "bold"), bg="#ece9e2").pack(anchor="w", pady=6)

        e = tk.Entry(self.content, width=58, font=("Courier", 8))
        e.insert(0, self.wallet.address)
        e.config(state="readonly")
        e.pack(anchor="w", pady=4)

        tk.Button(self.content, text=t("copy_address"),
                  command=lambda: self.copy(self.wallet.address)).pack(anchor="w", pady=4)

    def send_page(self):
        self.clear()
        tk.Label(self.content, text=t("send_btcx"),
                 font=("Arial", 13, "bold"), bg="#ece9e2").pack(anchor="w", pady=6)

        form = tk.Frame(self.content, bg="#ece9e2")
        form.pack(anchor="w")

        tk.Label(form, text=t("dest_addr"), bg="#ece9e2",
                 font=("Arial", 9)).grid(row=0, column=0, sticky="w", pady=2)
        dest = tk.Entry(form, width=52, font=("Courier", 8))
        dest.grid(row=1, column=0, pady=2)

        tk.Label(form, text=t("amount"), bg="#ece9e2",
                 font=("Arial", 9)).grid(row=2, column=0, sticky="w", pady=2)
        amount = tk.Entry(form, width=20)
        amount.grid(row=3, column=0, sticky="w")

        tk.Label(form, text=t("fee") + f" (min {MIN_FEE})", bg="#ece9e2",
                 font=("Arial", 9)).grid(row=4, column=0, sticky="w", pady=2)
        fee = tk.Entry(form, width=20)
        fee.insert(0, str(MIN_FEE))
        fee.grid(row=5, column=0, sticky="w")

        def send():
            try:
                to = dest.get().strip()
                value = float(amount.get())
                f = float(fee.get())
                if not valid_address(to):
                    messagebox.showerror("DogKong v2", t("invalid_addr"))
                    return
                if value <= 0:
                    raise ValueError()
                if f < MIN_FEE:
                    messagebox.showerror("DogKong v2", f"Min {MIN_FEE}")
                    return
                if self.bc.balance(self.wallet.address, min_conf=6) < value + f:
                    messagebox.showerror("DogKong v2", t("insufficient"))
                    return
                tx = make_tx(self.wallet, to, value, f)
                if not self.bc.add_transaction(tx):
                    messagebox.showerror("DogKong v2", t("rejected"))
                    return
                self.network.broadcast({"type": "tx", "tx": tx})
                self.log(t("tx_sent"))
                add_notificacao(f"Enviou {value} DOGK para {to} | TXID: {tx['id']}")
                messagebox.showinfo("DogKong v2", t("added_mempool"))
                self.transactions()
            except:
                messagebox.showerror("DogKong v2", t("invalid_values"))

        tk.Button(form, text=t("send_btn"), command=send,
                  width=15).grid(row=6, column=0, pady=10, sticky="w")

    def transactions(self):
        self.clear()
        tk.Label(self.content, text=t("my_transactions"),
                 font=("Arial", 13, "bold"), bg="#ece9e2").pack(anchor="w", pady=6)

        tree = ttk.Treeview(self.content,
                            columns=("h", "tp", "a", "c"),
                            show="headings", height=10)
        for col, txt, w in [("h", t("block"), 60),
                            ("tp", t("type"), 80),
                            ("a", t("value"), 130),
                            ("c", t("conf"), 60)]:
            tree.heading(col, text=txt)
            tree.column(col, width=w)
        tree.pack(fill=tk.BOTH, expand=True)

        height = self.bc.height()
        for b in reversed(self.bc.chain):
            for tx in b.get("tx", []):
                if tx.get("from") == self.wallet.address or tx.get("to") == self.wallet.address:
                    if tx.get("from") == self.wallet.address:
                        typ = t("sent")
                        amt = -float(tx.get("amount", 0))
                    else:
                        typ = t("received")
                        amt = float(tx.get("amount", 0))
                    conf = height - b["height"] + 1
                    tree.insert("", tk.END,
                                values=(b["height"], typ, f"{amt:.4f}", conf))

    def history_page(self):
        self.clear()
        tk.Label(self.content, text=t("history"),
                 font=("Arial", 13, "bold"), bg="#ece9e2").pack(anchor="w", pady=6)

        top = tk.Frame(self.content, bg="#ece9e2")
        top.pack(fill=tk.X)
        tk.Label(top, text=t("block_num"), bg="#ece9e2",
                 font=("Arial", 9)).pack(side=tk.LEFT)
        idx = tk.Entry(top, width=8)
        idx.pack(side=tk.LEFT, padx=4)

        info = tk.Text(self.content, height=14, bg="white",
                       relief=tk.SUNKEN, bd=2, font=("Courier", 8))
        info.pack(fill=tk.BOTH, expand=True, pady=4)

        def show():
            info.delete("1.0", tk.END)
            try:
                n = int(idx.get())
                if n < 0 or n >= len(self.bc.chain):
                    info.insert(tk.END, "Bloco inexistente.\n")
                    return
                b = self.bc.chain[n]
                info.insert(tk.END, f"Bloco #{b['height']}\n")
                info.insert(tk.END, f"Horario: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(b['time'])))}\n")
                info.insert(tk.END, f"Hash: {b['hash']}\n")
                info.insert(tk.END, f"Anterior: {b['prev']}\n")
                info.insert(tk.END, f"Bits: 0x{b['bits']:08X}\n")
                info.insert(tk.END, f"Nonce: {b['nonce']}\n")
                info.insert(tk.END, f"Minerador: {b['miner']}\n")
                info.insert(tk.END, f"Transacoes: {len(b.get('tx', []))}\n")
                info.insert(tk.END, f"Recompensa: {block_reward(b['height']):.4f} DOGK\n")
                if "message" in b:
                    info.insert(tk.END, f"Mensagem: {b['message']}\n")
                info.insert(tk.END, "\n--- Transacoes ---\n")
                for tx in b.get("tx", []):
                    info.insert(tk.END, f"ID: {tx.get('id')}\n")
                    info.insert(tk.END, f"  De:  {tx.get('from')}\n")
                    info.insert(tk.END, f"  Para: {tx.get('to')}\n")
                    info.insert(tk.END, f"  Valor: {tx.get('amount')}\n")
                    info.insert(tk.END, f"  Taxa: {tx.get('fee')}\n\n")
            except:
                info.insert(tk.END, "Bloco invalido.\n")

        tk.Button(top, text=t("show"), command=show).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text=t("last"),
                  command=lambda: (idx.delete(0, tk.END),
                                   idx.insert(0, str(self.bc.height())),
                                   show())).pack(side=tk.LEFT, padx=2)

        if self.bc.height() >= 0:
            idx.insert(0, str(self.bc.height()))
            show()

    def network_page(self):
        self.clear()
        tk.Label(self.content, text="Rede DogKong v2",
                 font=("Arial", 13, "bold"), bg="#ece9e2").pack(anchor="w", pady=6)

        top = tk.Frame(self.content, bg="#ece9e2")
        top.pack(fill=tk.X, pady=2)

        hashrate_rede = self.bc.hashrate_rede()
        hashrate_local = self.miner.hashrate_local() if self.miner is not None else 0.0
        bits_atual = self.bc.difficulty()
        bits_prox = self.bc.target_difficulty()

        tempos = []
        janela = min(DIFFICULTY_WINDOW, len(self.bc.chain) - 1)
        if janela >= 2:
            recent = self.bc.chain[-janela:]
            for i in range(1, len(recent)):
                dt = int(recent[i]["time"]) - int(recent[i-1]["time"])
                if dt <= 0:
                    dt = 1
                if dt > MAX_TIME_DELTA:
                    dt = MAX_TIME_DELTA
                tempos.append(dt)
        tempo_medio = sum(tempos) / len(tempos) if tempos else 0.0

        info = tk.LabelFrame(top, text="Estatisticas", bg="#ece9e2")
        info.pack(fill=tk.X, pady=4)

        limite_txt = "(sem limite)"
        if self.miner is None:
            limite_txt = "(PRINCIPAL - nao minera)"
        elif self.miner.hashrate_alvo > 0:
            limite_txt = f"{self.miner.hashrate_alvo:.0f} H/s"
        elif self.miner.hashrate_pc > 0:
            limite_txt = f"{self.miner.hashrate_pc:.0f} H/s (100%)"

        rows = [
            ("Bloco atual",              f"#{self.bc.height()}"),
            ("Bits atual",               f"0x{bits_atual:08X}"),
            ("Bits proximo",             f"0x{bits_prox:08X}"),
            ("Hashrate da rede",         self._fmt_hashrate(hashrate_rede)),
            ("Hashrate local",           self._fmt_hashrate(hashrate_local)),
            ("Limite configurado",       limite_txt),
            ("Tempo medio/bloco",        f"{tempo_medio:.1f}s (meta {BLOCK_TIME}s)"),
            ("Meta",                     f"1 bloco a cada {BLOCK_TIME}s"),
            ("Janela LWMA",              f"{DIFFICULTY_WINDOW} blocos"),
            ("Anti-travamento",          f"apos {BLOCK_TIME * STALL_TIME_MULT}s"),
        ]
        for i, (k, v) in enumerate(rows):
            tk.Label(info, text=k + ":", bg="#ece9e2",
                     font=("Arial", 9, "bold")).grid(row=i, column=0, sticky="w", padx=4, pady=1)
            ent = tk.Entry(info, width=40, font=("Courier", 9))
            ent.insert(0, str(v))
            ent.config(state="readonly")
            ent.grid(row=i, column=1, sticky="w", padx=4, pady=1)

        hist = tk.LabelFrame(self.content, text="Bits dos ultimos blocos",
                             bg="#ece9e2")
        hist.pack(fill=tk.BOTH, expand=True, pady=4)

        tree = ttk.Treeview(hist,
                            columns=("h", "t", "b"),
                            show="headings", height=8)
        for col, txt, w in [("h", "Bloco", 70),
                            ("t", "Tempo desde anterior", 180),
                            ("b", "Bits", 160)]:
            tree.heading(col, text=txt)
            tree.column(col, width=w)
        tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        recent = self.bc.chain[-20:] if len(self.bc.chain) >= 20 else self.bc.chain
        prev_time = None
        for b in reversed(recent):
            t = int(b["time"])
            if prev_time is None:
                dt_str = "-"
            else:
                dt = prev_time - t
                dt_str = f"{dt}s"
            prev_time = t
            bits = int(b.get("bits", INITIAL_DIFFICULTY))
            tree.insert("", tk.END,
                        values=(b["height"], dt_str, f"0x{bits:08X}"))

        peers_box = tk.LabelFrame(self.content, text="Peers conectados", bg="#ece9e2")
        peers_box.pack(fill=tk.X, pady=4)
        with self.network.lock:
            peers = sorted(self.network.peers)
        if peers:
            txt = tk.Text(peers_box, height=4, bg="white",
                          relief=tk.SUNKEN, bd=2, font=("Courier", 8))
            txt.pack(fill=tk.X, padx=4, pady=4)
            txt.insert("1.0", "\n".join(peers))
            txt.config(state="disabled")
        else:
            tk.Label(peers_box, text="(nenhum peer conectado)",
                     bg="#ece9e2", font=("Arial", 9)).pack(anchor="w", padx=4, pady=4)

    def connect_peer(self):
        host = simpledialog.askstring("DogKong v2", "IP do peer (IP:porta):")
        if not host:
            return
        host = host.strip()
        self.network.add_peer(host)
        threading.Thread(target=self.network.sync_peer, args=(host,), daemon=True).start()
        self.log(f"Conectando ao peer {host}")

    def edit_seeds(self):
        win = tk.Toplevel(self.root)
        win.title("Seeds DogKong v2")
        win.geometry("500x340")
        win.transient(self.root)

        tk.Label(win, text="Um IP por linha:").pack(anchor="w", padx=10, pady=4)
        txt = tk.Text(win, height=12, width=58)
        txt.pack(padx=10, pady=4, fill=tk.BOTH, expand=True)
        txt.insert("1.0", "\n".join(self.network.seeds))

        def save_seeds():
            lines = [l.strip() for l in txt.get("1.0", tk.END).splitlines() if l.strip()]
            save_json(SEEDS_FILE, lines)
            self.network.seeds = lines
            for l in lines:
                self.network.add_peer(l)
            messagebox.showinfo("DogKong v2", "Seeds salvos.")
            win.destroy()

        tk.Button(win, text="Salvar", command=save_seeds).pack(pady=5)

    def reset_hashrate(self):
        self.miner.hashrate_pc = 0.0
        self.miner.hashrate_alvo = 0.0
        self.log("Limite de H/s resetado. Proximo Minerar vai perguntar de novo.")

    def sync(self):
        threading.Thread(target=self.sync_thread, daemon=True).start()

    def sync_thread(self):
        self.log("Sincronizando...")
        with self.network.lock:
            peers = list(self.network.peers)
        for p in peers:
            self.network.sync_peer(p)
        self.log(f"Sincronizado - bloco #{self.bc.height()}")
        self.schedule_refresh()

    def start_mining(self):
        if SOU_PRINCIPAL:
            messagebox.showinfo("DogKong v2", "Este no e PRINCIPAL. Nao minera, so salva blocos.")
            return
        if SEED_ONLY:
            messagebox.showinfo("DogKong v2", "Este no e seed only. Nao minera.")
            return
        if self.wallet.is_locked():
            messagebox.showerror("DogKong v2", "Desbloqueie a carteira primeiro.")
            return
        # SEGURANCA: nao minerar se chain ainda esta no genesis (evita fork)
        if self.bc.height() <= 0:
            messagebox.showerror("DogKong v2",
                "Nao sincronizou com a rede ainda (bloco #0).\n"
                "Aguarde a sincronizacao antes de minerar.\n"
                "Se demorar, verifique a conexao com os seeds.")
            return
        self.miner.minerar()
        self.log(t("miner_on"))
        self.update_mining_buttons()
        self.schedule_refresh()
    def stop_mining(self):
        if self.miner is not None:
            self.miner.parar()
        self.log(t("miner_off"))
        self.update_mining_buttons()
        self.schedule_refresh()

    def marcar_notif_nova(self):
        try:
            idx = self._menu_ref.index("Notificacao")
            self._menu_ref.entryconfig(idx, label="(!) Notificacao")
            print("[MENU] Notificacao marcada!", flush=True)
        except Exception as e:
            print(f"[MENU] ERRO: {e}", flush=True)

    def limpar_marca_notif(self):
        try:
            idx = self._menu_ref.index("(!) Notificacao")
            self._menu_ref.entryconfig(idx, label="Notificacao")
            print("[MENU] Notificacao limpa.", flush=True)
        except:
            pass

    def _abrir_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def mostrar_notificacoes(self):
        win = tk.Toplevel(self.root)
        win.title("Notificacoes")
        win.geometry("620x520")
        win.configure(bg="#ece9e2")
        tk.Label(win, text="Notificacoes", font=("Arial", 14, "bold"), bg="#ece9e2").pack(pady=10)
        canvas = tk.Canvas(win, bg="#ece9e2")
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg="#ece9e2")
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(6,0))
        scrollbar.pack(side="right", fill="y")
        import re as _re
        txt = None
        try:
            with open(NOTIF_FILE, "r", encoding="utf-8") as f:
                conteudo = f.read()
            if not conteudo.strip():
                conteudo = "(sem notificacoes)"
        except FileNotFoundError:
            conteudo = "(sem notificacoes)"
        if True:
            linhas = conteudo.splitlines()
            if not linhas:
                tk.Label(frame, text="(sem notificacoes)", bg="#ece9e2").pack(pady=20)
            else:
                for linha in reversed(linhas):
                    linha = linha.strip()
                    if not linha:
                        continue
                    bloco = tk.Frame(frame, bg="white", relief="groove", bd=1)
                    bloco.pack(fill="x", padx=6, pady=3)
                    tk.Label(bloco, text=linha, bg="white", anchor="w",
                             justify="left", wraplength=560,
                             font=("Courier", 8)).pack(anchor="w", padx=6, pady=4)
                    m = _re.search(r'TXID:\s*([0-9a-f]{64})', linha)
                    if m:
                        txid = m.group(1)
                        url = "https://dogkong.duckdns.org/search?q=" + txid
                        tk.Button(bloco, text="Abrir no Explorer",
                                  bg="#3498db", fg="white",
                                  font=("Arial", 8, "bold"),
                                  command=lambda u=url: self._abrir_url(u)
                                  ).pack(anchor="w", padx=6, pady=(0, 6))
        self.limpar_marca_notif()
        try:
            flag = NOTIF_FILE + ".new"
            if os.path.exists(flag):
                os.remove(flag)
        except:
            pass
        tk.Button(win, text="Fechar", command=win.destroy, bg="#d9534f", fg="white").pack(pady=10)

    def limpar_notificacoes(self):
        try:
            with open(NOTIF_FILE, "w", encoding="utf-8") as f:
                f.write("")
            messagebox.showinfo("Notificacoes", "Notificacoes limpas!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def about(self):
        messagebox.showinfo(
            "Sobre DogKong v2",
            "DogKong v2.3 - No Completo + Carteira + Minerador\n"
            "Dificuldade estilo Bitcoin (bits/target + LWMA)\n"
            "Anti-travamento temporal em tempo real\n\n"
            "Hardening: Argon2id/AES-GCM, PoW 64MB, anti-Sybil\n\n"
            f"P2P: {P2P_PORT}\n"
            f"Chain ID: {CHAIN_ID}\n"
            f"PoW: CPU + RAM ({MEMORY_MB}MB, {MEMORY_ITER} iter)\n"
            f"Protocolo P2P: v{PROTOCOL_VERSION}\n"
            "Carteira: BIP39 (12 palavras) + Senha\n"
            f"Taxa minima: {MIN_FEE}\n"
            f"Meta de bloco: {BLOCK_TIME}s\n"
            f"Bits inicial: 0x{INITIAL_DIFFICULTY:08X}\n"
            f"Janela LWMA: {DIFFICULTY_WINDOW} blocos\n"
            f"Anti-travamento: ativa apos {BLOCK_TIME * STALL_TIME_MULT}s\n"
            f"Emissao anual: {YEARLY_EMISSION:,} DOGK\n"
            f"Recompensa/bloco: {REWARD_PER_BLOCK:.4f} DOGK\n\n"
            "Idiomas: Portugues, English, Espanol, Zhongwen, Russkiy"
        )

    def set_password(self):
        if self.wallet.encrypted:
            messagebox.showinfo("DogKong v2", "Senha ja ativa.")
            return
        s1 = simpledialog.askstring("DogKong v2", "Nova senha:", show="*")
        if not s1:
            return
        s2 = simpledialog.askstring("DogKong v2", "Confirme:", show="*")
        if s1 != s2:
            messagebox.showerror("DogKong v2", "Senhas diferentes.")
            return
        if len(s1) < 8:
            messagebox.showerror("DogKong v2", "Minimo 8 caracteres.")
            return
        self.wallet.set_password(s1)
        messagebox.showinfo("DogKong v2", "Senha ativada! Guarde bem.")
        self.log("Senha ativada")
        self.overview()

    def remove_password(self):
        if not self.wallet.encrypted:
            messagebox.showinfo("DogKong v2", "Sem senha ativa.")
            return
        s = simpledialog.askstring("DogKong v2", "Senha atual:", show="*")
        if not s:
            return
        if s != self.wallet.password:
            messagebox.showerror("DogKong v2", "Senha incorreta.")
            return
        self.wallet.remove_password()
        messagebox.showinfo("DogKong v2", "Senha removida.")
        self.overview()

    def change_password(self):
        if not self.wallet.encrypted:
            messagebox.showinfo("DogKong v2", "Nenhuma senha ativa.")
            return
        old = simpledialog.askstring("DogKong v2", "Senha atual:", show="*")
        if not old:
            return
        if old != self.wallet.password:
            messagebox.showerror("DogKong v2", "Senha antiga incorreta.")
            return
        new = simpledialog.askstring("DogKong v2", "Nova senha:", show="*")
        if not new or len(new) < 8:
            messagebox.showerror("DogKong v2", "Senha muito curta.")
            return
        self.wallet.change_password(old, new)
        messagebox.showinfo("DogKong v2", "Senha alterada.")
        self.log("Senha alterada")

    def new_wallet(self):
        ok = messagebox.askyesno(
            "DogKong v2",
            "Criar nova carteira?\n\nVai gerar 12 palavras. Anote!"
        )
        if not ok:
            return
        s1 = simpledialog.askstring("DogKong v2", "Senha (vazio = sem senha):", show="*")
        if s1 and len(s1) < 8:
            messagebox.showerror("DogKong v2", "Senha muito curta.")
            return
        self.wallet.generate_mnemonic()
        if s1:
            self.wallet.password = s1
            self.wallet.encrypted = True
        else:
            self.wallet.encrypted = False
        self.wallet.save()

        win = tk.Toplevel(self.root)
        win.title("Anote as 12 palavras")
        win.geometry("560x420")
        win.transient(self.root)
        win.configure(bg="#ece9e2")

        tk.Label(win, text="ANOTE ESTAS 12 PALAVRAS",
                 font=("Arial", 12, "bold"), fg="red", bg="#ece9e2").pack(pady=6)
        tk.Label(win, text="Se perder, PERDE ACESSO pra sempre.",
                 fg="red", bg="#ece9e2").pack(pady=2)

        txt = tk.Text(win, height=5, width=54, font=("Courier", 11))
        txt.pack(pady=8, padx=10)
        txt.insert("1.0", self.wallet.mnemonic)
        txt.config(state="disabled")

        tk.Label(win, text="Endereco:\n" + self.wallet.address,
                 font=("Courier", 9), bg="#ece9e2").pack(pady=4)

        def copiar():
            self.root.clipboard_clear()
            self.root.clipboard_append(self.wallet.mnemonic)
            self.root.update()
            messagebox.showinfo("DogKong v2", t("copy_mn_ok"))

        tk.Button(win, text=t("copy_mnemonic"), command=copiar,
                  bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                  width=30, height=2).pack(pady=6)

        self.overview()

    def import_wif(self):
        wif = simpledialog.askstring("DogKong v2", "Cole o WIF:")
        if not wif:
            return
        try:
            self.wallet.import_wif(wif.strip())
            messagebox.showinfo("DogKong v2", "WIF importado.\n\n" + self.wallet.address)
            self.overview()
        except Exception as e:
            messagebox.showerror("DogKong v2", f"WIF invalido:\n{e}")

    def restore_mnemonic(self):
        mn = simpledialog.askstring(
            "DogKong v2",
            "Digite as 12 palavras separadas por espaco:"
        )
        if not mn:
            return
        try:
            if not bip39_validate(mn):
                messagebox.showerror("DogKong v2", "Mnemnico invalido.")
                return
            s1 = simpledialog.askstring(
                "DogKong v2",
                "Nova senha (vazio = sem senha):", show="*"
            )
            self.wallet.import_mnemonic(mn, s1 if s1 else None)
            messagebox.showinfo("DogKong v2", "Restaurada!\n\n" + self.wallet.address)
            self.overview()
        except Exception as e:
            messagebox.showerror("DogKong v2", f"Erro: {e}")

    def show_keys(self):
        win = tk.Toplevel(self.root)
        win.title("Carteira DogKong v2")
        win.geometry("680x540")
        win.transient(self.root)
        win.configure(bg="#ece9e2")

        def copiar(txt, msg_ok):
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.root.update()
            messagebox.showinfo("DogKong v2", msg_ok)

        tk.Label(win, text=t("address"), font=("Arial", 11, "bold"),
                 bg="#ece9e2").pack(anchor="w", padx=10, pady=(10, 2))
        a = tk.Entry(win, width=84, font=("Courier", 9))
        a.insert(0, self.wallet.address)
        a.config(state="readonly")
        a.pack(padx=10)
        tk.Button(
            win, text=t("copy_address"),
            command=lambda: copiar(self.wallet.address, t("copy_addr_ok")),
            width=32, height=2, bg="#3498db", fg="white",
            font=("Arial", 10, "bold")
        ).pack(pady=6)

        tk.Label(win, text="WIF", font=("Arial", 11, "bold"),
                 bg="#ece9e2").pack(anchor="w", padx=10, pady=(10, 2))
        w = tk.Entry(win, width=84, font=("Courier", 9))
        w.insert(0, self.wallet.wif or "(bloqueado)")
        w.config(state="readonly")
        w.pack(padx=10)
        tk.Button(
            win, text=t("copy_wif"),
            command=lambda: copiar(self.wallet.wif or "", t("copy_wif_ok")),
            width=32, height=2, bg="#e67e22", fg="white",
            font=("Arial", 10, "bold")
        ).pack(pady=6)

        if self.wallet.mnemonic:
            tk.Label(win, text="12 palavras", font=("Arial", 11, "bold"),
                     bg="#ece9e2").pack(anchor="w", padx=10, pady=(10, 2))
            m = tk.Text(win, height=3, width=84, font=("Courier", 9))
            m.pack(padx=10)
            m.insert("1.0", self.wallet.mnemonic)
            m.config(state="disabled")
            tk.Button(
                win, text=t("copy_mnemonic"),
                command=lambda: copiar(self.wallet.mnemonic, t("copy_mn_ok")),
                width=32, height=2, bg="#27ae60", fg="white",
                font=("Arial", 10, "bold")
            ).pack(pady=6)

        tk.Label(win, text="AVISO: " + t("never_share"),
                 fg="red", bg="#ece9e2",
                 font=("Arial", 9, "bold")).pack(pady=10)

    def backup(self):
        path = filedialog.asksaveasfilename(
            title="Backup DogKong v2",
            defaultextension=".json",
            filetypes=[("Carteira DogKong", "*.json")]
        )
        if not path:
            return
        try:
            with open(WALLET_FILE, "rb") as src:
                data = src.read()
            with open(path, "wb") as dst:
                dst.write(data)
            messagebox.showinfo("DogKong v2", "Backup OK.")
        except Exception as e:
            messagebox.showerror("DogKong v2", str(e))

    def copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("DogKong v2", t("copied"))

    def schedule_refresh(self):
        if self._refresh_queued:
            return
        self._refresh_queued = True
        try:
            self.root.after(0, self._do_queued_refresh)
        except:
            self._refresh_queued = False

    def _do_queued_refresh(self):
        self._refresh_queued = False
        self.refresh_once()

    def _check_notif_flag(self):
        flag = NOTIF_FILE + ".new"
        if os.path.exists(flag):
            os.remove(flag)
            print("[FLAG] Detectada! Marcando menu...", flush=True)
            self.marcar_notif_nova()
            print("[FLAG] Menu marcado.", flush=True)

    def refresh_once(self):
        try:
            hgt = self.bc.height()
            bits = self.bc.difficulty()
            # Cache: so recalcula a cada 10s
            agora = time.time()
            if not hasattr(self, "_cache_refresh"):
                self._cache_refresh = {}
            if agora - self._cache_refresh.get("ts", 0) > 10:
                self._cache_refresh["next_bits"] = self.bc.target_difficulty()
                self._cache_refresh["hashrate_rede"] = self.bc.hashrate_rede()
                self._cache_refresh["ts"] = agora
            next_bits = self._cache_refresh.get("next_bits", bits)
            hashrate_rede = self._cache_refresh.get("hashrate_rede", 0.0)
            with self.network.lock:
                peers = len(self.network.peers)
            if self.miner is not None and self.miner.is_running():
                rate = self.miner.hashrate_local()
                mining = f" | Local: {self._fmt_hashrate(rate)}"
            elif self.miner is None:
                mining = " | PRINCIPAL"
            else:
                mining = " | OFF"
            lock = "LOCK " if self.wallet.is_locked() else ""
            self.status.set(
                f"{lock}DOGK v2 | Peers: {peers} | #{hgt} | "
                f"Bits: 0x{bits:08X}->0x{next_bits:08X} | "
                f"Rede: {self._fmt_hashrate(hashrate_rede)}{mining}"
            )
            self._check_notif_flag()
            self.update_log()
        except:
            pass

    def refresh(self):
        self._check_notif_flag()
        self.refresh_once()
        self.root.after(2000, self.refresh)

    def run(self):
        self.log(f"{APP} v{VERSION}")
        self.log(f"Carteira: {self.wallet.address if self.wallet.address else '(bloqueada)'}")
        self.log(f"Blockchain: bloco #{self.bc.height()}")
        self.log(f"P2P: {P2P_PORT} | Chain: {CHAIN_ID}")
        self.log(f"PoW: CPU + RAM ({MEMORY_MB}MB, {MEMORY_ITER} iter)")
        self.log(f"Dificuldade Bitcoin-style: bits 0x{INITIAL_DIFFICULTY:08X} "
                 f"janela LWMA={DIFFICULTY_WINDOW}")
        self.log(f"Anti-travamento: ativa apos {BLOCK_TIME * STALL_TIME_MULT}s")
        self.log(f"Protocolo: v{PROTOCOL_VERSION} | Argon2: {USE_ARGON2}")
        self.log(f"Idioma: {LANGUAGES.get(LANG, LANG)}")
        self.log("Rede pronta")
        self.update_mining_buttons()
        self.root.mainloop()


# ============================================================
# INICIO
# ============================================================
if __name__ == "__main__":
    # ============================================================
    # MODO CLI (VPS / SEM TELA)
    # ============================================================
    if "--no-gui" in sys.argv or "--cli" in sys.argv:
        print("[DOGK v2] Iniciando em MODO CLI (sem interface grafica)...", flush=True)
        try:
            class DogKongHeadless:
                def __init__(self):
                    self.wallet = Wallet()
                    # SEED_ONLY agora tem chain REAL (nao stub)
                    self.bc = Blockchain()
                    self.miner = None
                    self.logs = []
                    self.global_rate = {}
                    self.global_rate_lock = threading.Lock()
                    self.network = Network(self)
                    threading.Thread(target=self._tx_watcher, daemon=True).start()
                    threading.Thread(target=self.initial_sync, daemon=True).start()
                    if SOU_PRINCIPAL:
                        self.log("[PRINCIPAL] Modo principal: nao minera, sincroniza e serve chain")
                    elif SEED_ONLY:
                        self.log("[SEED] Modo seed: nao minera, descobre peers e serve chain")
                    else:
                        self.log("[PEER] Modo peer: minerador C++ indisponivel em CLI")

                def log(self, text):
                    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)

                def schedule_refresh(self):
                    pass

                def _tx_watcher(self):
                    import time, json, os
                    PENDING = os.path.join(DATA, "pending_tx_local.json")
                    ja_injetadas = set()
                    while True:
                        try:
                            if os.path.exists(PENDING):
                                with open(PENDING, "r", encoding="utf-8") as f:
                                    txs = json.load(f)
                                if txs:
                                    for tx in txs:
                                        txid = tx.get("id")
                                        if txid and txid not in ja_injetadas:
                                            if self.bc.add_transaction(tx):
                                                self.log("TX web injetada: " + txid[:16])
                                                ja_injetadas.add(txid)
                                                try:
                                                    self.network.broadcast({"type": "tx", "tx": tx})
                                                except:
                                                    pass
                                    with open(PENDING, "w", encoding="utf-8") as f:
                                        json.dump([], f)
                        except Exception:
                            pass
                        time.sleep(5)

                def initial_sync(self):
                    self.log("Sincronizando...")
                    # FIX B: SO PRINCIPAL cria genesis. Peer espera baixar da rede.
                    if not self.bc.chain:
                        if SOU_PRINCIPAL:
                            self.log("[BOOTSTRAP] PRINCIPAL sem chain. Criando genesis local...")
                            try:
                                genesis = self.bc.criar_bloco_genesis()
                                self.bc.chain = [genesis]
                                self.bc._aguardando_sync = False
                                self.bc.save()
                                self.log(f"[BOOTSTRAP] Genesis criado: #{genesis['height']}")
                            except Exception as e:
                                self.log(f"[BOOTSTRAP] Erro: {e}")
                            return
                        else:
                            self.log("[BOOTSTRAP] Peer sem chain. Baixando da rede...")
                    with self.network.lock:
                        peers = list(self.network.peers)
                    if SOU_PRINCIPAL:
                        self.log(f"[PRINCIPAL] Bootstrap: tentando {len(peers)} peer(s)")
                        import concurrent.futures
                        def _try(p):
                            try:
                                return self.network.sync_peer(p)
                            except Exception:
                                return False
                        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                            list(ex.map(_try, peers))
                    else:
                        for p in peers:
                            try:
                                self.network.sync_peer(p)
                            except:
                                pass
                    self.log(f"Sincronizado. Bloco: #{self.bc.height()}")

                def on_new_block(self, block, from_host):
                    bc = self.bc
                    precisa_sync = False
                    with bc.lock:
                        height = int(block.get("height", -1))
                        if height != bc.height() + 1:
                            if height > bc.height() + 1:
                                precisa_sync = True
                            else:
                                return
                        else:
                            if int(block.get("time", 0)) > now() + MAX_FUTURE_TIME:
                                return
                            if block.get("prev") != bc.chain[-1]["hash"]:
                                return
                            if not bc.valid_pow(block):
                                return
                            bits_recebidos = int(block.get("bits", 0))
                            bits_esperados = bc.target_difficulty(candidate_time=int(block.get("time", 0)))
                            if bits_recebidos != bits_esperados:
                                return
                            bc.chain.append(block)
                            used = {x.get("id") for x in block.get("tx", [])}
                            bc.mempool = [x for x in bc.mempool if x.get("id") not in used]
                            bc.save()
                    if precisa_sync:
                        self.network.sync_chain(from_host)

                def run(self):
                    self.log("No ativo (CLI). Rodando...")
                    last_h = 0
                    while True:
                        time.sleep(10)
                        try:
                            h = self.bc.height()
                            if h != last_h:
                                with self.network.lock:
                                    peers = len(self.network.peers)
                                self.log(f"Bloco: #{h} | Peers: {peers} | Rede: {self.bc.hashrate_rede():.1f} H/s")
                                last_h = h
                        except:
                            pass

            globals()["DOGK_CORE_GLOBAL"] = DogKongHeadless()
            globals()["DOGK_CORE_GLOBAL"].run()
        except Exception as e:
            print(f"[ERRO CLI]: {e}", flush=True)
            traceback.print_exc()
    else:
        # ============================================================
        # MODO GUI (Windows / Desktop)
        # ============================================================
        try:
            import __main__
            globals()["DOGK_CORE_GLOBAL"] = DogKongCore()
            globals()["DOGK_CORE_GLOBAL"].run()
        except Exception as e:
            try:
                messagebox.showerror("DogKong v2 - Erro", str(e))
            except:
                print(e)
            traceback.print_exc()








