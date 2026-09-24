# ============================================================
# DogKong v2.3 — Criptomoeda com dificuldade dinâmica estilo Bitcoin
# PoW: CPU+RAM 64MB / P2P: 18555 / Dificuldade: bits/target + LWMA
# Anti-travamento: decaimento temporal em tempo real
# Genesis: minerado automaticamente na primeira execução
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

APP = "DogKong v2"
VERSION = "2.3"
P2P_PORT = 18555
CHAIN_ID = "DOGK-V2-MAINNET"

if getattr(sys, 'frozen', False):
    DATA = os.path.join(os.path.dirname(sys.executable), "dogk_data_v2")
else:
    DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dogk_data_v2")
WALLET_FILE = os.path.join(DATA, "wallet.json")
CHAIN_FILE = os.path.join(DATA, "blockchain.json")
MEMPOOL_FILE = os.path.join(DATA, "mempool.json")
PEERS_FILE = os.path.join(DATA, "peers.json")
SEEDS_FILE = os.path.join(DATA, "seeds.json")
LANG_FILE = os.path.join(DATA, "lang.txt")
os.makedirs(DATA, exist_ok=True)

INITIAL_SUPPLY_REF = 10_000_000_000
YEARLY_EMISSION = 5_256_000_000
BLOCK_TIME = 60
BLOCKS_YEAR = 262_800
REWARD_PER_BLOCK = 10_000.0

# ============================================================
# DIFICULDADE PADRÃO BITCOIN (BITS / TARGET) COM LWMA
# ============================================================
TARGET_MAX_BTC = 0x000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
INITIAL_DIFFICULTY = 0x207fffff   # MUITO fácil — genesis sai em <1s

DIFFICULTY_WINDOW = 17            # janela LWMA
MAX_TIME_DELTA = BLOCK_TIME * 4   # clamp de timestamp

# Anti-travamento em tempo real
STALL_TIME_MULT = 5               # ativa após 5 × BLOCK_TIME = 300s sem bloco

FAST_TIME = BLOCK_TIME // 2
SLOW_TIME = BLOCK_TIME * 2

MAX_BLOCK_TX = 3000
MAX_PEERS = 100

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

DEFAULT_SEEDS = ["seeddogkong.duckdns.org"]
    


# ============================================================
# 5 IDIOMAS
# ============================================================
LANGUAGES = {
    "pt": "🇧🇷 Português",
    "en": "🇺🇸 English",
    "es": "🇪🇸 Español",
    "zh": "🇨🇳 中文",
    "ru": "🇷🇺 Русский",
}

TRANSLATIONS = {
    "pt": {
        "overview": "Visão Geral", "send": "Enviar", "receive": "Receber",
        "transactions": "Transações", "history": "Histórico", "refresh": "🔄 Atualizar",
        "network": "Rede",
        "start_mining": "▶ Minerar", "stop_mining": "■ Parar",
        "balance": "Saldo:", "block": "Bloco", "difficulty": "Dificuldade",
        "next_diff": "Próxima dif", "peers": "Peers", "mempool": "Mempool",
        "reward": "Recompensa", "public_ip": "IP público", "pow": "PoW",
        "hashrate_net": "Hashrate rede", "hashrate_local": "Hashrate local",
        "your_wallet": "Sua carteira", "address": "Endereço:", "copy": "Copiar",
        "wif_mnemonic": "WIF/Mnemônico", "copy_p2p": "Copiar P2P",
        "password_on": "🔒 Senha ativa", "send_btcx": "Enviar DOGK",
        "dest_addr": "Endereço destino:", "amount": "Quantidade:", "fee": "Taxa:",
        "send_btn": "Enviar", "my_transactions": "Minhas transações",
        "type": "Tipo", "value": "Valor", "conf": "Conf",
        "sent": "Enviado", "received": "Recebido", "block_num": "Bloco:",
        "show": "Mostrar", "last": "Último", "language": "Idioma",
        "copied": "Copiado!", "invalid_addr": "Endereço inválido.",
        "insufficient": "Saldo insuficiente.", "rejected": "Transação rejeitada.",
        "invalid_values": "Valores inválidos.", "added_mempool": "Transação adicionada ao mempool.",
        "tx_sent": "Transação enviada", "mining_started": "Mineração iniciada",
        "mining_stopped": "Mineração parada", "miner_on": "Minerador ligado",
        "miner_off": "Minerador desligado", "wallet_locked": "🔒 Carteira Bloqueada",
        "unlock_hint": "Digite a senha pra desbloquear:", "unlock_btn": "Desbloquear",
        "wrong_pass": "Senha incorreta.", "wait_sec": "Aguarde {s}s antes de tentar.",
        "never_share": "NUNCA compartilhe WIF ou palavras.",
        "copy_address": "📋 COPIAR ENDEREÇO", "copy_wif": "📋 COPIAR WIF",
        "copy_mnemonic": "📋 COPIAR 12 PALAVRAS", "chain_id": "Chain ID",
        "meta_block": "Meta de bloco", "year_emission": "Emissão anual",
        "reward_block": "Recompensa/bloco", "network_events": "Eventos da rede",
        "copy_addr_ok": "Endereço copiado!", "copy_wif_ok": "WIF copiado!",
        "copy_mn_ok": "12 palavras copiadas!",
        "new_wallet": "Nova Carteira", "import_wif": "Importar WIF",
        "restore_mnemonic": "Restaurar 12 palavras",
        "show_wallet": "Mostrar Carteira / WIF / Mnemônico",
        "backup": "Backup da Carteira",
        "set_password": "🔒 Definir Senha", "remove_password": "🔓 Remover Senha",
        "change_password": "🔑 Trocar Senha", "exit": "Sair",
        "file_menu": "Arquivo", "settings_menu": "Configurações",
        "help_menu": "Ajuda", "lang_menu": "🌐 Idioma",
        "connect_peer": "Conectar Peer", "sync_network": "Sincronizar Rede",
        "edit_seeds": "Editar Seeds", "about": "Sobre DogKong",
    },
    "en": {
        "overview": "Overview", "send": "Send", "receive": "Receive",
        "transactions": "Transactions", "history": "History", "refresh": "🔄 Refresh",
        "network": "Network",
        "start_mining": "▶ Mine", "stop_mining": "■ Stop",
        "balance": "Balance:", "block": "Block", "difficulty": "Difficulty",
        "next_diff": "Next diff", "peers": "Peers", "mempool": "Mempool",
        "reward": "Reward", "public_ip": "Public IP", "pow": "PoW",
        "hashrate_net": "Network hashrate", "hashrate_local": "Local hashrate",
        "your_wallet": "Your wallet", "address": "Address:", "copy": "Copy",
        "wif_mnemonic": "WIF/Mnemonic", "copy_p2p": "Copy P2P",
        "password_on": "🔒 Password on", "send_btcx": "Send DOGK",
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
        "miner_off": "Miner off", "wallet_locked": "🔒 Wallet Locked",
        "unlock_hint": "Enter password to unlock:", "unlock_btn": "Unlock",
        "wrong_pass": "Wrong password.", "wait_sec": "Wait {s}s before trying.",
        "never_share": "NEVER share WIF or words.",
        "copy_address": "📋 COPY ADDRESS", "copy_wif": "📋 COPY WIF",
        "copy_mnemonic": "📋 COPY 12 WORDS", "chain_id": "Chain ID",
        "meta_block": "Block time", "year_emission": "Yearly emission",
        "reward_block": "Reward/block", "network_events": "Network events",
        "copy_addr_ok": "Address copied!", "copy_wif_ok": "WIF copied!",
        "copy_mn_ok": "12 words copied!",
        "new_wallet": "New Wallet", "import_wif": "Import WIF",
        "restore_mnemonic": "Restore 12 words",
        "show_wallet": "Show Wallet / WIF / Mnemonic",
        "backup": "Backup Wallet",
        "set_password": "🔒 Set Password", "remove_password": "🔓 Remove Password",
        "change_password": "🔑 Change Password", "exit": "Exit",
        "file_menu": "File", "settings_menu": "Settings",
        "help_menu": "Help", "lang_menu": "🌐 Language",
        "connect_peer": "Connect Peer", "sync_network": "Sync Network",
        "edit_seeds": "Edit Seeds", "about": "About DogKong",
    },
    "es": {
        "overview": "Vista General", "send": "Enviar", "receive": "Recibir",
        "transactions": "Transacciones", "history": "Historial", "refresh": "🔄 Actualizar",
        "network": "Red",
        "start_mining": "▶ Minar", "stop_mining": "■ Parar",
        "balance": "Saldo:", "block": "Bloque", "difficulty": "Dificultad",
        "next_diff": "Próxima dif", "peers": "Pares", "mempool": "Mempool",
        "reward": "Recompensa", "public_ip": "IP público", "pow": "PoW",
        "hashrate_net": "Hashrate red", "hashrate_local": "Hashrate local",
        "your_wallet": "Tu cartera", "address": "Dirección:", "copy": "Copiar",
        "wif_mnemonic": "WIF/Mnemónico", "copy_p2p": "Copiar P2P",
        "password_on": "🔒 Contraseña activa", "send_btcx": "Enviar DOGK",
        "dest_addr": "Dirección destino:", "amount": "Cantidad:", "fee": "Comisión:",
        "send_btn": "Enviar", "my_transactions": "Mis transacciones",
        "type": "Tipo", "value": "Valor", "conf": "Conf",
        "sent": "Enviado", "received": "Recibido", "block_num": "Bloque:",
        "show": "Mostrar", "last": "Último", "language": "Idioma",
        "copied": "¡Copiado!", "invalid_addr": "Dirección inválida.",
        "insufficient": "Saldo insuficiente.", "rejected": "Rechazada.",
        "invalid_values": "Valores inválidos.", "added_mempool": "Añadido al mempool.",
        "tx_sent": "Enviado", "mining_started": "Minería iniciada",
        "mining_stopped": "Minería parada", "miner_on": "Minero encendido",
        "miner_off": "Minero apagado", "wallet_locked": "🔒 Cartera Bloqueada",
        "unlock_hint": "Contraseña:", "unlock_btn": "Desbloquear",
        "wrong_pass": "Contraseña incorrecta.", "wait_sec": "Espera {s}s.",
        "never_share": "NUNCA compartas WIF o palabras.",
        "copy_address": "📋 COPIAR DIRECCIÓN", "copy_wif": "📋 COPIAR WIF",
        "copy_mnemonic": "📋 COPIAR 12 PALABRAS", "chain_id": "Chain ID",
        "meta_block": "Tiempo de bloque", "year_emission": "Emisión anual",
        "reward_block": "Recompensa/bloque", "network_events": "Eventos de red",
        "copy_addr_ok": "¡Dirección copiada!", "copy_wif_ok": "¡WIF copiado!",
        "copy_mn_ok": "¡12 palabras copiadas!",
        "new_wallet": "Nueva Cartera", "import_wif": "Importar WIF",
        "restore_mnemonic": "Restaurar 12 palabras",
        "show_wallet": "Mostrar Cartera / WIF / Mnemónico",
        "backup": "Backup de Cartera",
        "set_password": "🔒 Definir Contraseña", "remove_password": "🔓 Quitar Contraseña",
        "change_password": "🔑 Cambiar Contraseña", "exit": "Salir",
        "file_menu": "Archivo", "settings_menu": "Configuración",
        "help_menu": "Ayuda", "lang_menu": "🌐 Idioma",
        "connect_peer": "Conectar Par", "sync_network": "Sincronizar Red",
        "edit_seeds": "Editar Seeds", "about": "Acerca de DogKong",
    },
    "zh": {
        "overview": "概览", "send": "发送", "receive": "接收", "transactions": "交易",
        "history": "历史", "refresh": "🔄 刷新", "network": "网络",
        "start_mining": "▶ 挖矿",
        "stop_mining": "■ 停止", "balance": "余额:", "block": "区块",
        "difficulty": "难度", "next_diff": "下一难度", "peers": "节点",
        "mempool": "内存池", "reward": "奖励", "public_ip": "公网 IP",
        "pow": "工作量证明", "hashrate_net": "网络算力", "hashrate_local": "本地算力",
        "your_wallet": "您的钱包", "address": "地址:",
        "copy": "复制", "wif_mnemonic": "WIF/助记词", "copy_p2p": "复制 P2P",
        "password_on": "🔒 密码已启用", "send_btcx": "发送 DOGK",
        "dest_addr": "目标地址:", "amount": "金额:", "fee": "手续费:",
        "send_btn": "发送", "my_transactions": "我的交易", "type": "类型",
        "value": "金额", "conf": "确认", "sent": "已发送", "received": "已接收",
        "block_num": "区块:", "show": "显示", "last": "最后", "language": "语言",
        "copied": "已复制!", "invalid_addr": "地址无效。", "insufficient": "余额不足。",
        "rejected": "被拒绝。", "invalid_values": "值无效。",
        "added_mempool": "已加入内存池。", "tx_sent": "已发送",
        "mining_started": "挖矿已开始", "mining_stopped": "挖矿已停止",
        "miner_on": "矿机开启", "miner_off": "矿机关闭",
        "wallet_locked": "🔒 钱包已锁定", "unlock_hint": "输入密码:",
        "unlock_btn": "解锁", "wrong_pass": "密码错误。",
        "wait_sec": "等待 {s} 秒。", "never_share": "切勿分享 WIF。",
        "copy_address": "📋 复制地址", "copy_wif": "📋 复制 WIF",
        "copy_mnemonic": "📋 复制 12 个单词", "chain_id": "链 ID",
        "meta_block": "区块时间", "year_emission": "年发行量",
        "reward_block": "每块奖励", "network_events": "网络事件",
        "copy_addr_ok": "地址已复制!", "copy_wif_ok": "WIF 已复制!",
        "copy_mn_ok": "12 个单词已复制!",
        "new_wallet": "新钱包", "import_wif": "导入 WIF",
        "restore_mnemonic": "恢复 12 个单词",
        "show_wallet": "显示钱包 / WIF / 助记词",
        "backup": "备份钱包",
        "set_password": "🔒 设置密码", "remove_password": "🔓 移除密码",
        "change_password": "🔑 更改密码", "exit": "退出",
        "file_menu": "文件", "settings_menu": "设置",
        "help_menu": "帮助", "lang_menu": "🌐 语言",
        "connect_peer": "连接节点", "sync_network": "同步网络",
        "edit_seeds": "编辑种子", "about": "关于 DogKong",
    },
    "ru": {
        "overview": "Обзор", "send": "Отправить", "receive": "Получить",
        "transactions": "Транзакции", "history": "История", "refresh": "🔄 Обновить",
        "network": "Сеть",
        "start_mining": "▶ Майнить", "stop_mining": "■ Стоп", "balance": "Баланс:",
        "block": "Блок", "difficulty": "Сложность", "next_diff": "След. сложность",
        "peers": "Пиры", "mempool": "Мемпул", "reward": "Награда",
        "public_ip": "Публичный IP", "pow": "PoW",
        "hashrate_net": "Хэшрейт сети", "hashrate_local": "Локальный хэшрейт",
        "your_wallet": "Кошелёк",
        "address": "Адрес:", "copy": "Копировать", "wif_mnemonic": "WIF/Мнемоника",
        "copy_p2p": "Копировать P2P", "password_on": "🔒 Пароль активен",
        "send_btcx": "Отправить DOGK", "dest_addr": "Адрес:",
        "amount": "Сумма:", "fee": "Комиссия:", "send_btn": "Отправить",
        "my_transactions": "Мои транзакции", "type": "Тип", "value": "Сумма",
        "conf": "Подтв", "sent": "Отправлено", "received": "Получено",
        "block_num": "Блок:", "show": "Показать", "last": "Последний",
        "language": "Язык", "copied": "Скопировано!", "invalid_addr": "Неверный адрес.",
        "insufficient": "Недостаточно средств.", "rejected": "Отклонена.",
        "invalid_values": "Неверные значения.", "added_mempool": "В мемпуле.",
        "tx_sent": "Отправлено", "mining_started": "Майнинг запущен",
        "mining_stopped": "Майнинг остановлен", "miner_on": "Майнер вкл",
        "miner_off": "Майнер выкл", "wallet_locked": "🔒 Заблокирован",
        "unlock_hint": "Пароль:", "unlock_btn": "Разблокировать",
        "wrong_pass": "Неверный пароль.", "wait_sec": "Подождите {s}с.",
        "never_share": "НИКОГДА не делитесь WIF.", "copy_address": "📋 КОПИРОВАТЬ АДРЕС",
        "copy_wif": "📋 КОПИРОВАТЬ WIF", "copy_mnemonic": "📋 КОПИРОВАТЬ 12 СЛОВ",
        "chain_id": "ID сети", "meta_block": "Время блока",
        "year_emission": "Годовая эмиссия", "reward_block": "Награда/блок",
        "network_events": "События сети", "copy_addr_ok": "Адрес скопирован!",
        "copy_wif_ok": "WIF скопирован!", "copy_mn_ok": "12 слов скопированы!",
        "new_wallet": "Новый кошелёк", "import_wif": "Импорт WIF",
        "restore_mnemonic": "Восстановить 12 слов",
        "show_wallet": "Показать кошелёк / WIF / Мнемонику",
        "backup": "Резервная копия",
        "set_password": "🔒 Задать пароль", "remove_password": "🔓 Убрать пароль",
        "change_password": "🔑 Сменить пароль", "exit": "Выход",
        "file_menu": "Файл", "settings_menu": "Настройки",
        "help_menu": "Помощь", "lang_menu": "🌐 Язык",
        "connect_peer": "Подключить пир", "sync_network": "Синхронизировать сеть",
        "edit_seeds": "Редактировать seeds", "about": "О DogKong",
    },
}

LANG = "pt"


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
# NÚCLEO DE DIFICULDADE — BITS/TARGET ESTILO BITCOIN + LWMA
# ============================================================
def target_para_bits(target):
    """Converte target de 256 bits para o campo 'bits' de 4 bytes."""
    if target > TARGET_MAX_BTC:
        target = TARGET_MAX_BTC
    if target < 1:
        target = 1
    s = f"{target:x}"
    if len(s) % 2 != 0:
        s = "0" + s
    tamanho = len(s) // 2
    mantissa = s[:6]
    if int(mantissa, 16) > 0x7FFFFF:
        mantissa = "00" + mantissa[:4]
        tamanho += 1
    return (tamanho << 24) | int(mantissa, 16)


def bits_para_target(bits):
    """Converte bits de 4 bytes para target de 256 bits."""
    tamanho = bits >> 24
    mantissa = bits & 0xFFFFFF
    return mantissa * (256 ** (tamanho - 3))


def calcular_dificuldade_alvo(chain, window=DIFFICULTY_WINDOW,
                              block_time=BLOCK_TIME,
                              max_time_delta=MAX_TIME_DELTA,
                              initial_bits=INITIAL_DIFFICULTY):
    """Calcula BITS do próximo bloco via LWMA com amortecedor 0.5x-2.0x."""
    if len(chain) < 2:
        return initial_bits

    end = len(chain)
    start = max(1, end - window)
    janela = chain[start:end]

    if len(janela) < 2:
        return int(chain[-1].get("bits", initial_bits))

    soma_tempos = 0
    peso_total = 0

    for i in range(1, len(janela)):
        tempo_bloco = int(janela[i]["time"]) - int(janela[i - 1]["time"])
        if tempo_bloco <= 0:
            tempo_bloco = 1
        if tempo_bloco > max_time_delta:
            tempo_bloco = max_time_delta
        peso = i
        soma_tempos += tempo_bloco * peso
        peso_total += peso

    if peso_total <= 0:
        peso_total = 1

    tempo_medio_ponderado = soma_tempos / peso_total

    ultimo_bits = int(chain[-1].get("bits", initial_bits))
    ultimo_target = bits_para_target(ultimo_bits)

    proporcao = tempo_medio_ponderado / block_time
    proporcao = max(0.5, min(proporcao, 2.0))

    novo_target = int(ultimo_target * proporcao)
    if novo_target > TARGET_MAX_BTC:
        novo_target = TARGET_MAX_BTC
    elif novo_target < 1:
        novo_target = 1

    return target_para_bits(novo_target)


def protecao_anti_travamento_tempo_real(ultimo_bits, tempo_decorrido_sem_bloco,
                                        block_time=BLOCK_TIME):
    """
    Anti-travamento: se passar de STALL_TIME_MULT × BLOCK_TIME sem bloco,
    dobra o target (corta a dificuldade pela metade) a cada minuto extra.
    """
    limite_espera = block_time * STALL_TIME_MULT

    if tempo_decorrido_sem_bloco > limite_espera:
        target = bits_para_target(ultimo_bits)
        tempo_extra = tempo_decorrido_sem_bloco - limite_espera
        ciclos_atraso = int(tempo_extra / 60) + 1
        novo_target = target * (2 ** ciclos_atraso)
        if novo_target > TARGET_MAX_BTC:
            novo_target = TARGET_MAX_BTC
        return target_para_bits(novo_target)

    return ultimo_bits


def estimar_hashrate_rede(chain, initial_bits=INITIAL_DIFFICULTY):
    """Estima hashrate (H/s) pela fórmula do Bitcoin: 2^256 / target / BLOCK_TIME."""
    if len(chain) < 2:
        return 0.0
    ultimo_bits = int(chain[-1].get("bits", initial_bits))
    target = bits_para_target(ultimo_bits)
    if target <= 0:
        return 0.0
    hashes_estimados = (2 ** 256) / target
    return hashes_estimados / BLOCK_TIME


# ============================================================
# UTILITÁRIOS DE HASH
# ============================================================
def sha256(b): return hashlib.sha256(b).digest()
def sha256d(b): return sha256(sha256(b))
def h(b): return hashlib.sha256(b).hexdigest()
def now(): return int(time.time())


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
        raise ValueError("strength inválido")
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
            raise ValueError("Base58 inválido")
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
    from Crypto.Hash import RIPEMD160
    return RIPEMD160.new(data).digest()


def address_from_pub(pub):
    payload = b"\x1E" + ripemd160(sha256(pub))
    return b58e(payload + sha256d(payload)[:4])


def wif_from_priv(priv):
    raw = b"\x9E" + priv.to_bytes(32, "big") + b"\x01"
    return b58e(raw + sha256d(raw)[:4])


def priv_from_wif(wif):
    raw = b58d(wif)
    if len(raw) != 38: raise ValueError("WIF inválido")
    body = raw[:-4]
    checksum = raw[-4:]
    if sha256d(body)[:4] != checksum: raise ValueError("Checksum WIF inválido")
    if body[0] != 0x9E: raise ValueError("WIF não compatível com DogKong")
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
        raise ValueError("pubkey não é bytes")
    if len(pub) != 33:
        raise ValueError("pubkey precisa ter 33 bytes")
    prefix = pub[0]
    if prefix not in (0x02, 0x03):
        raise ValueError("prefixo de pubkey inválido")
    x = int.from_bytes(pub[1:], "big")
    if x <= 0 or x >= P:
        raise ValueError("x fora do range da curva")
    y2 = (pow(x, 3, P) + 7) % P
    y = pow(y2, (P + 1) // 4, P)
    if (y * y) % P != y2:
        raise ValueError("ponto não está na curva secp256k1")
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
            raise ValueError("Mnemônico inválido")
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
    if os.path.exists(MEMORY_TABLE_FILE):
        try:
            with open(MEMORY_TABLE_FILE, "rb") as f:
                cached = f.read()
            if len(cached) == MEMORY_SIZE:
                return cached
        except Exception:
            pass
    table = bytearray()
    seed = b"DOGK-V2-MEMORY-TABLE-HARDENED"
    while len(table) < MEMORY_SIZE:
        seed = hashlib.sha256(seed).digest()
        table.extend(seed)
    result = bytes(table[:MEMORY_SIZE])
    try:
        with open(MEMORY_TABLE_FILE, "wb") as f:
            f.write(result)
    except Exception:
        pass
    return result


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
            self.chain = [self.criar_bloco_genesis()]
            self.mempool = []
            self.save()
            return

        if not chain:
            raise PersistError("blockchain.json esta vazio.")

        if not self.valid_chain(chain):
            raise PersistError("blockchain.json existe mas e INVALIDA.")

        self.chain = chain
        self.mempool = load_json(MEMPOOL_FILE, default=[])

    # --------------------------------------------------------
    # GENESIS (criado automaticamente na primeira execução)
    # --------------------------------------------------------
    def criar_bloco_genesis(self):
        """
        Monta e minera o Bloco Gênese (altura 0).
        - hash_anterior = "0" * 64
        - bits = 0x1D00FFFF (super fácil)
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

    def height(self):
        return len(self.chain) - 1

    def last_block(self):
        return self.chain[-1]

    def difficulty(self):
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

    def target_difficulty(self, chain=None):
        if chain is None:
            chain = self.chain
        return calcular_dificuldade_alvo(chain)

    def expected_difficulty_for_chain(self, chain, height):
        if height <= 1:
            return INITIAL_DIFFICULTY
        prev_chain = chain[:height]
        if len(prev_chain) < 2:
            return INITIAL_DIFFICULTY
        return calcular_dificuldade_alvo(prev_chain)

    def hashrate_rede(self, chain=None):
        if chain is None:
            chain = self.chain
        return estimar_hashrate_rede(chain)

    def balance(self, address):
        bal = 0.0
        for block in self.chain:
            for tx in block.get("tx", []):
                sender = tx.get("from")
                receiver = tx.get("to")
                amount = float(tx.get("amount", 0))
                fee = float(tx.get("fee", 0))
                if sender == "COINBASE":
                    if receiver == address:
                        bal += amount
                    continue
                if sender == address:
                    bal -= amount
                    bal -= fee
                if receiver == address:
                    bal += amount
        for tx in self.mempool:
            if tx.get("from") == address:
                bal -= float(tx.get("amount", 0))
                bal -= float(tx.get("fee", 0))
        return max(0.0, bal)

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
            if self.balance(sender) < amount + fee:
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

    def _balance_after_mempool(self, address):
        bal = 0.0
        for block in self.chain:
            for tx in block.get("tx", []):
                s = tx.get("from")
                r = tx.get("to")
                a = float(tx.get("amount", 0))
                f = float(tx.get("fee", 0))
                if s == "COINBASE":
                    if r == address:
                        bal += a
                    continue
                if s == address:
                    bal -= (a + f)
                if r == address:
                    bal += a
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
            saldo_disponivel = self._balance_after_mempool(tx["from"])
            custo_total = float(tx["amount"]) + float(tx["fee"])
            if saldo_disponivel < custo_total:
                return False
            self.mempool.append(tx)
            self._check_mempool_limits()
            self.save()
            return True

    def create_coinbase(self, address, height):
        reward = block_reward(height)
        return {
            "id": h(f"COINBASE:{height}:{address}:{reward}".encode()),
            "from": "COINBASE",
            "to": address,
            "amount": reward,
            "fee": 0,
            "time": now()
        }

    def valid_chain(self, chain):
        try:
            if not chain:
                return False
            g = chain[0]
            if g.get("height") != 0:
                return False
            if g.get("prev") != "0" * 64:
                return False
            if int(g.get("bits", 0)) != INITIAL_DIFFICULTY:
                return False
            if not g.get("hash"):
                return False
            target_gen = bits_para_target(INITIAL_DIFFICULTY)
            if int(g["hash"], 16) > target_gen:
                return False
            for i, b in enumerate(chain):
                # Pula validacao rigorosa dos primeiros 1000 blocos
                if i < 1361:
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
                if len(b.get("tx", [])) > MAX_BLOCK_TX:
                    return False
                # Aceita QUALQUER bits (anti-travamento e clamp)
                # A validação real de PoW já garante que o hash ≤ target
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
                        if abs(float(tx.get("amount", -1)) - block_reward(i)) > 1e-8:
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
            return True
        except Exception as e:
            import traceback
            print("[DOGK v2] valid_chain FALHOU:", e)
            traceback.print_exc()
            return False

    def accept_chain(self, new_chain):
        with self.lock:
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
            if not self.valid_chain(new_chain):
                return False
            self.chain = new_chain
            self.mempool = [tx for tx in self.mempool if not self.tx_exists(tx["id"])]
            self._check_mempool_limits()
            self.save()
            return True


def resolver_dns_seeds(seeds=None):
    """
    Resolve dominios DNS para IPs (igual Bitcoin/Dogecoin).
    Retorna lista de IPs (sem porta).
    """
    if seeds is None:
        seeds = DEFAULT_SEEDS
    
    ips = set()
    for seed in seeds:
        # Se já é IP, adiciona direto
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
        self.peers = set()
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
        self.load_peers()
        self.load_seeds()
        
        # Tenta abrir a porta via UPnP (em background, nao trava o boot)
        def upnp_bg():
            try:
                tentar_upnp(P2P_PORT)
            except Exception as e:
                print(f"[UPnP] Erro: {e}")
        
        threading.Thread(target=upnp_bg, daemon=True).start()
        
        threading.Thread(target=self.server, daemon=True).start()
        threading.Thread(target=self.discovery_loop, daemon=True).start()
        threading.Thread(target=self.detect_ip_bg, daemon=True).start()

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
        with self.lock:
            self.peers.discard(host)
        self.core.log(f"Peer banido: {host} ({seconds}s)")

    def _rate_ok(self, host):
        agora = time.time()
        with self.rate_lock:
            lst = self.rate_limit.setdefault(host, [])
            lst[:] = [t for t in lst if agora - t < 1.0]
            if len(lst) >= RATE_LIMIT_PER_SEC:
                return False
            lst.append(agora)
            return True

    def _msg_rate_ok(self, host):
        agora = time.time()
        with self.rate_lock:
            lst = self.peer_msgs.setdefault(host, [])
            lst[:] = [t for t in lst if agora - t < 60]
            if len(lst) >= MAX_PEER_MESSAGES_PER_MIN:
                return False
            lst.append(agora)
            return True

    def _can_accept_ip(self, host):
        with self.lock:
            s = self.peers_per_ip.setdefault(host, set())
            if len(s) >= MAX_PEERS_PER_IP and host not in s:
                return False
            return True

    def detect_ip_bg(self):
        ip = detect_public_ip()
        if ip:
            self.public_ip = ip
            self.core.log(f"Seu IP público: {ip}:{P2P_PORT}")

    def load_peers(self):
        arr = load_json(PEERS_FILE, [])
        for p in arr:
            if isinstance(p, str):
                self.peers.add(p)

    def save_peers(self):
        try:
            save_json(PEERS_FILE, list(self.peers))
        except:
            pass

    def load_seeds(self):
        # Carrega seeds do arquivo, se existir
        seeds = load_json(SEEDS_FILE, None)
        if seeds is None:
            seeds = list(DEFAULT_SEEDS)
            try:
                save_json(SEEDS_FILE, seeds)
            except:
                pass
        
        self.seeds = [s for s in seeds if isinstance(s, str)]
        
        # Adiciona os seeds brutos (pode ser IP ou dominio)
        for s in self.seeds:
            self.peers.add(s)
        
        # Resolve DNS seeds em background (nao trava o boot)
        def resolver_bg():
            try:
                ips = resolver_dns_seeds(self.seeds)
                for ip in ips:
                    self.add_peer(ip, outbound=True)
                if ips:
                    self.core.log(f"DNS Seeds resolvidos: {len(ips)} IPs")
            except Exception as e:
                self.core.log(f"DNS Seeds falharam: {e}")
        
        threading.Thread(target=resolver_bg, daemon=True).start()
        
        self.save_peers()

    def add_peer(self, host, outbound=False):
        if not isinstance(host, str) or not host:
            return
        if ":" in host:
            host = host.split(":")[0]
        if self._is_banned(host):
            return
        if host in ("127.0.0.1", "localhost") and host not in self.seeds:
            return
        if not self._can_accept_ip(host):
            return
        with self.lock:
            if len(self.peers) >= MAX_PEERS:
                return
            self.peers.add(host)
            self.peers_per_ip.setdefault(host, set()).add(host)
            if outbound:
                self.outbound_peers.add(host)
        self.save_peers()

    def server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", P2P_PORT))
            s.listen(MAX_PEERS)
        except Exception as e:
            self.core.log(f"P2P: porta {P2P_PORT} indisponível ({e})")
            return
        self.server_sock = s
        self.core.log(f"P2P ativo na porta {P2P_PORT}")

        self._active_conns = 0
        self._conns_lock = threading.Lock()
        MAX_ACTIVE_CONNS = 64

        while self.running:
            try:
                c, addr = s.accept()
                host = addr[0]
                if self._is_banned(host):
                    try:
                        c.close()
                    except:
                        pass
                    continue
                with self._conns_lock:
                    if self._active_conns >= MAX_ACTIVE_CONNS:
                        try:
                            c.close()
                        except:
                            pass
                        continue
                    self._active_conns += 1
                try:
                    c.settimeout(HANDSHAKE_TIMEOUT)
                except:
                    pass
                threading.Thread(target=self._handle_wrapped,
                                 args=(c, host), daemon=True).start()
            except:
                if not self.running:
                    break
                time.sleep(1)

    def _handle_wrapped(self, c, host):
        try:
            self.handle(c, host)
        except Exception:
            pass
        finally:
            try:
                c.close()
            except:
                pass
            with self._conns_lock:
                if self._active_conns > 0:
                    self._active_conns -= 1

    def _do_handshake(self, sock, host, outbound=False):
        try:
            my_nonce = secrets.token_bytes(8)
            hello = {
                "type": "version",
                "proto": PROTOCOL_VERSION,
                "min_proto": MIN_PROTOCOL_VERSION,
                "magic": MAGIC.hex(),
                "nonce": my_nonce.hex(),
                "height": self.core.bc.height(),
                "last_hash": self.core.bc.last_block()["hash"],
                "difficulty": self.core.bc.difficulty(),
                "hashrate": self.core.bc.hashrate_rede(),
                "peers": list(self.peers)[:MAX_PEERS],
                "user_agent": f"DogKong-v2/{VERSION}"
            }
            raw = json.dumps(hello, separators=(",", ":")).encode() + b"\n"
            sock.sendall(raw)
            sock.settimeout(HANDSHAKE_TIMEOUT)
            data = b""
            while len(data) < MAX_MSG_BYTES:
                p = sock.recv(65536)
                if not p:
                    break
                data += p
                if b"\n" in data:
                    break
            if not data:
                return None
            reply = json.loads(data.split(b"\n", 1)[0])
            if reply.get("type") != "version":
                return None
            if reply.get("magic") != MAGIC.hex():
                self.ban_peer(host, 3600)
                return None
            if int(reply.get("proto", 0)) < MIN_PROTOCOL_VERSION:
                return None
            if reply.get("nonce") == my_nonce.hex():
                return None
            return reply
        except Exception:
            return None

    def send(self, host, obj, timeout=5, handshake=True):
        try:
            raw = json.dumps(obj, separators=(",", ":")).encode() + b"\n"
            if len(raw) > MAX_MSG_BYTES:
                return None
            s = socket.create_connection((host, P2P_PORT), timeout=timeout)
            if handshake:
                if not self._do_handshake(s, host, outbound=True):
                    s.close()
                    return None
            s.sendall(raw)
            s.settimeout(timeout)
            data = b""
            while len(data) < MAX_MSG_BYTES:
                part = s.recv(65536)
                if not part:
                    break
                data += part
                if b"\n" in data:
                    break
            s.close()
            if data:
                return json.loads(data.split(b"\n", 1)[0])
        except Exception:
            pass
        return None

    def handle(self, c, host):
        try:
            if not self._rate_ok(host):
                return
            handshake = self._do_handshake(c, host, outbound=False)
            if not handshake:
                c.close()
                return
            self.add_peer(host)
            c.settimeout(20)
            data = b""
            while len(data) < MAX_MSG_BYTES:
                p = c.recv(65536)
                if not p:
                    break
                data += p
                if b"\n" in data:
                    break
            if not data:
                return
            msg = json.loads(data.split(b"\n", 1)[0])
            typ = msg.get("type")

            if not self._msg_rate_ok(host):
                c.close()
                return

            if typ == "version":
                reply = {"type": "ok", "proto": PROTOCOL_VERSION}
            elif typ == "get_peers":
                with self.lock:
                    reply = {"type": "peers", "peers": list(self.peers)[:MAX_PEERS]}
            elif typ == "get_chain":
                with self.core.bc.lock:
                    reply = {"type": "chain", "chain": list(self.core.bc.chain)}
            elif typ == "get_headers":
                start = max(0, int(msg.get("start", 0)))
                if start > self.core.bc.height() + 1:
                    reply = {"type": "error"}
                else:
                    headers = []
                    with self.core.bc.lock:
                        for b in self.core.bc.chain[start:start + 2000]:
                            headers.append({"height": b["height"], "hash": b["hash"],
                                            "prev": b["prev"], "time": b["time"],
                                            "bits": b["bits"]})
                    reply = {"type": "headers", "headers": headers}
            elif typ == "get_blocks":
                start = max(0, int(msg.get("start", 0)))
                if start > self.core.bc.height() + 1:
                    reply = {"type": "error"}
                else:
                    with self.core.bc.lock:
                        blocks = list(self.core.bc.chain[start:start + 500])
                    reply = {"type": "blocks", "blocks": blocks}
            elif typ == "get_mempool":
                with self.core.bc.lock:
                    reply = {"type": "mempool", "tx": list(self.core.bc.mempool[:1000])}
            elif typ == "get_hashrate":
                reply = {"type": "hashrate",
                         "hashrate": self.core.bc.hashrate_rede(),
                         "difficulty": self.core.bc.difficulty(),
                         "next_difficulty": self.core.bc.target_difficulty()}
            elif typ == "tx":
                tx = msg.get("tx")
                if tx and self.core.bc.add_transaction(tx):
                    self.broadcast({"type": "tx", "tx": tx}, exclude=host)
                reply = {"type": "ok"}
            elif typ == "block":
                blk = msg.get("block")
                if blk:
                    self.core.on_new_block(blk, host)
                reply = {"type": "ok"}
            elif typ == "chain":
                chain = msg.get("chain", [])
                if len(chain) > 100000:
                    self.ban_peer(host, 3600)
                    reply = {"type": "error"}
                elif self.core.bc.accept_chain(chain):
                    self.core.log("Blockchain sincronizada")
                    self.core.schedule_refresh()
                    reply = {"type": "ok", "height": self.core.bc.height()}
                else:
                    reply = {"type": "ok", "height": self.core.bc.height()}
            elif typ == "peers":
                for p in msg.get("peers", [])[:MAX_PEERS]:
                    self.add_peer(p)
                reply = {"type": "ok"}
            else:
                reply = {"type": "error"}

            c.sendall(json.dumps(reply, separators=(",", ":")).encode() + b"\n")
        except Exception:
            pass
        finally:
            try:
                c.close()
            except:
                pass

    def broadcast(self, msg, exclude=None):
        with self.lock:
            peers = list(self.peers)
        for p in peers:
            if p == exclude or self._is_banned(p):
                continue
            threading.Thread(target=self.send, args=(p, msg), daemon=True).start()

    def sync_peer(self, host):
        if self._is_banned(host):
            return False
        self.add_peer(host, outbound=True)
        headers = self.send(host, {"type": "get_headers", "start": 0})
        if headers and headers.get("type") == "headers":
            for hdr in headers.get("headers", []):
                try:
                    if int(hdr.get("time", 0)) > now() + MAX_FUTURE_TIME:
                        self.ban_peer(host, 3600)
                        return False
                except Exception:
                    self.ban_peer(host, 3600)
                    return False
        local_height = self.core.bc.height()
        while True:
            response = self.send(host, {"type": "get_blocks", "start": local_height})
            if not response or response.get("type") != "blocks":
                break
            blocks = response.get("blocks", [])
            if not blocks:
                break
            with self.core.bc.lock:
                base = list(self.core.bc.chain)
            if blocks[0].get("prev") == base[-1]["hash"]:
                candidate = base + blocks
                if self.core.bc.accept_chain(candidate):
                    local_height = self.core.bc.height()
                    self.core.log(f"Sincronizado com {host} até bloco #{local_height}")
                    self.core.schedule_refresh()
                else:
                    break
            else:
                resp = self.send(host, {"type": "get_chain"}, timeout=60)
                if resp and resp.get("type") == "chain":
                    if self.core.bc.accept_chain(resp.get("chain", [])):
                        self.core.log(f"Cadeia substituída por {host}")
                        self.core.schedule_refresh()
                break
            if len(blocks) < 500:
                break
        response = self.send(host, {"type": "get_mempool"})
        if response and response.get("type") == "mempool":
            for tx in response.get("tx", [])[:2000]:
                self.core.bc.add_transaction(tx)
        response = self.send(host, {"type": "get_peers"})
        if response and response.get("type") == "peers":
            for p in response.get("peers", [])[:MAX_PEERS]:
                if p != host:
                    self.add_peer(p, outbound=True)
        return True

    def discovery_loop(self):
        time.sleep(3)
        while self.running:
            with self.lock:
                peers = list(self.peers)
            if len(self.outbound_peers) < MIN_OUTBOUND_PEERS:
                for p in peers:
                    if not self.running:
                        break
                    self.sync_peer(p)
            else:
                for p in peers:
                    if not self.running:
                        break
                    self.sync_peer(p)
            time.sleep(45)

    def shutdown(self):
        self.running = False
        try:
            if self.server_sock:
                self.server_sock.close()
        except:
            pass


class Miner:
    def __init__(self, core):
        self.core = core
        self.running = False
        self.thread = None
        self.hashes = 0
        self.start_time = 0
        self.lock = threading.Lock()
        self.batch_size = MINER_BATCH
        self.hashrate_alvo = 0.0
        self.hashrate_pc = 0.0
        self.sleep_per_batch = 0.0
        self.last_hashrate = 0.0
        self.block_start_time = 0

    def start(self):
        with self.lock:
            if self.running:
                return
            self.running = True
            self.hashes = 0
            self.start_time = time.time()
            self.last_hashrate = 0.0
            self.thread = threading.Thread(target=self.mine, daemon=True)
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False

    def is_running(self):
        with self.lock:
            return self.running

    def hashrate_local(self):
        with self.lock:
            if not self.running or self.start_time <= 0:
                return 0.0
            elapsed = max(1e-6, time.time() - self.start_time)
            return self.hashes / elapsed

    def configurar_hashrate(self, hashrate_pc, hashrate_alvo):
        self.hashrate_pc = max(1.0, hashrate_pc)
        self.hashrate_alvo = max(1.0, min(hashrate_alvo, hashrate_pc))
        fracao = self.hashrate_alvo / self.hashrate_pc
        fracao = max(0.01, min(1.0, fracao))
        tempo_batch_cheio = self.batch_size / self.hashrate_pc
        if fracao >= 0.99:
            self.sleep_per_batch = 0.0
        else:
            self.sleep_per_batch = tempo_batch_cheio * (1.0 / fracao - 1.0)

    def mine(self):
        self.core.log(t("mining_started") + " (CPU + RAM)")
        if self.hashrate_alvo > 0:
            self.core.log(
                f"Limite: {self.hashrate_alvo:.0f} H/s "
                f"(PC faz ~{self.hashrate_pc:.0f} H/s)"
            )
        sha256 = hashlib.sha256
        table = MEMORY_TABLE
        size = MEMORY_SIZE

        while self.running:
            bc = self.core.bc
            with bc.lock:
                height = bc.height() + 1
                bits = bc.target_difficulty()
                coinbase = bc.create_coinbase(self.core.wallet.address, height)
                txs = [coinbase] + bc.mempool[:MAX_BLOCK_TX - 1]
                previous = dict(bc.chain[-1])

            block_time = now()
            if block_time <= int(previous["time"]):
                block_time = int(previous["time"]) + 1

            bloco_inicio = time.time()
            bits_efetivos = bits
            target = bits_para_target(bits_efetivos)

            self.core.log(f"Minerando bloco {height} | bits 0x{bits:08X}")

            nonce = 0
            found = False
            counter = 0
            batch = self.batch_size
            sleep_time = self.sleep_per_batch
            ultimo_check_stall = bloco_inicio

            while self.running:
                # Anti-travamento em tempo real
                agora = time.time()
                if (agora - ultimo_check_stall) >= 5:
                    ultimo_check_stall = agora
                    decorrido = agora - bloco_inicio
                    limite = BLOCK_TIME * STALL_TIME_MULT
                    if decorrido > limite:
                        bits_novos = protecao_anti_travamento_tempo_real(bits, decorrido)
                        if bits_novos != bits_efetivos:
                            bits_efetivos = bits_novos
                            target = bits_para_target(bits_efetivos)
                            self.core.log(
                                f"[ANTI-TRAVA] {int(decorrido)}s sem bloco — "
                                f"bits 0x{bits:08X}->0x{bits_efetivos:08X}"
                            )

                prefix = (
                    f"{height}:"
                    f"{block_time}:"
                    f"{previous['hash']}:"
                    f"{bits_efetivos}:"
                ).encode()
                suffix = f":{self.core.wallet.address}".encode()
                header = prefix + str(nonce).encode() + suffix
                digest = sha256(header).digest()
                for _ in range(MEMORY_ITER):
                    pos1 = int.from_bytes(digest[:4], "big") % (size - 64)
                    pos2 = int.from_bytes(digest[4:8], "big") % (size - 64)
                    chunk1 = table[pos1:pos1 + 32]
                    chunk2 = table[pos2:pos2 + 32]
                    digest = sha256(digest + chunk1 + chunk2).digest()
                hh = digest.hex()
                self.hashes += 1

                # Bitcoin: hash <= target
                if int(hh, 16) <= target:
                    block = {
                        "height": height,
                        "time": block_time,
                        "prev": previous["hash"],
                        "bits": bits_efetivos,
                        "nonce": nonce,
                        "miner": self.core.wallet.address,
                        "tx": txs,
                        "hash": hh
                    }
                    with bc.lock:
                        if bc.chain[-1]["hash"] != previous["hash"]:
                            break
                        if int(block["time"]) > now() + MAX_FUTURE_TIME:
                            break
                        if not bc.valid_pow(block):
                            break
                        bc.chain.append(block)
                        used = {x.get("id") for x in txs}
                        bc.mempool = [x for x in bc.mempool if x.get("id") not in used]
                        bc.save()
                    self.core.log(f"*** BLOCO {height} ***")
                    self.core.log(f"Hash: {hh}")
                    self.core.log(f"Bits: 0x{bits_efetivos:08X} | Hashrate rede: {bc.hashrate_rede():.1f} H/s")
                    self.core.network.broadcast({"type": "block", "block": block})
                    self.core.schedule_refresh()
                    found = True
                    break

                nonce += 1
                counter += 1
                if counter >= batch:
                    counter = 0
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    else:
                        time.sleep(0)

            if not found and not self.running:
                break
            time.sleep(0.01)

        self.core.log(t("mining_stopped"))


class DogKongCore:
    def __init__(self):
        self.wallet = Wallet()
        self.bc = Blockchain()
        self.miner = Miner(self)
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
                                    self.log("TX web injetada: " + txid[:16] + "...")
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
        for p in peers:
            self.network.sync_peer(p)
        self.log(f"Sincronizado. Bloco: #{self.bc.height()}")
        self.schedule_refresh()

    def on_new_block(self, block, from_host):
        bc = self.bc
        with bc.lock:
            height = int(block.get("height", -1))
            if height != bc.height() + 1:
                return
            if int(block.get("time", 0)) > now() + MAX_FUTURE_TIME:
                self.network.ban_peer(from_host, 3600)
                return
            if block.get("prev") != bc.chain[-1]["hash"]:
                return
            if not bc.valid_pow(block):
                return
            bits_recebidos = int(block["bits"])
            bits_esperados = bc.target_difficulty()
            if bits_recebidos > bits_esperados:
                pass
            else:
                if bits_recebidos != bits_esperados:
                    self.log(
                        f"Bloco #{height} rejeitado: bits 0x{bits_recebidos:08X} "
                        f"!= esperado 0x{bits_esperados:08X}"
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
        self.log(
            f"Bloco #{height} de {from_host} | bits 0x{block['bits']:08X} | "
            f"hashrate rede ~{bc.hashrate_rede():.0f} H/s"
        )
        self.network.broadcast({"type": "block", "block": block}, exclude=from_host)
        self.schedule_refresh()

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

        bal = self.bc.balance(self.wallet.address)
        frame = tk.Frame(self.content, bg="#ece9e2")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=t("balance"), font=("Arial", 10), bg="#ece9e2").pack(anchor="w", pady=(2, 0))
        tk.Label(frame, text=f"{bal:.8f} DOGK", font=("Arial", 16, "bold"), bg="#ece9e2").pack(anchor="w")

        net = tk.LabelFrame(frame, text="Rede DogKong v2", bg="#ece9e2")
        net.pack(fill=tk.X, pady=4)

        with self.network.lock:
            peers = len(self.network.peers)

        hashrate_rede = self.bc.hashrate_rede()
        hashrate_local = self.miner.hashrate_local()
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
                if self.bc.balance(self.wallet.address) < value + f:
                    messagebox.showerror("DogKong v2", t("insufficient"))
                    return
                tx = make_tx(self.wallet, to, value, f)
                if not self.bc.add_transaction(tx):
                    messagebox.showerror("DogKong v2", t("rejected"))
                    return
                self.network.broadcast({"type": "tx", "tx": tx})
                self.log(t("tx_sent"))
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
        hashrate_local = self.miner.hashrate_local()
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
        if self.miner.hashrate_alvo > 0:
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
        if self.wallet.is_locked():
            messagebox.showerror("DogKong v2", "Desbloqueie a carteira primeiro.")
            return
        if self.miner.is_running():
            return

        if self.miner.hashrate_pc <= 0:
            self.log("Medindo poder do seu PC (2 segundos)...")
            self.root.update_idletasks()
            hr_pc = benchmark_hashrate(duracao=2.0)
            if hr_pc < 1:
                hr_pc = 1.0
            self.log(f"PC faz ~{hr_pc:.0f} H/s")
            sugestao = int(hr_pc * 0.5)
            if sugestao < 1:
                sugestao = 1
            resposta = simpledialog.askinteger(
                "DogKong v2 — Limite de mineracao",
                f"Seu PC faz ~{hr_pc:.0f} H/s.\n\n"
                f"Quantos H/s voce quer usar?\n"
                f"(1 a {int(hr_pc)})\n\n"
                f"Sugestao: {sugestao} (metade — PC fica responsivo)",
                initialvalue=sugestao,
                minvalue=1,
                maxvalue=int(hr_pc)
            )
            if resposta is None:
                self.log("Mineracao cancelada.")
                return
            self.miner.configurar_hashrate(hr_pc, resposta)
            self.log(f"Limite aplicado: {resposta} H/s "
                     f"({100.0 * resposta / hr_pc:.0f}% do PC)")

        self.miner.start()
        self.log(t("miner_on"))
        self.update_mining_buttons()
        self.schedule_refresh()

    def stop_mining(self):
        self.miner.stop()
        self.log(t("miner_off"))
        self.update_mining_buttons()
        self.schedule_refresh()

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
                messagebox.showerror("DogKong v2", "Mnemônico invalido.")
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

    def refresh_once(self):
        try:
            hgt = self.bc.height()
            bits = self.bc.difficulty()
            next_bits = self.bc.target_difficulty()
            hashrate_rede = self.bc.hashrate_rede()
            with self.network.lock:
                peers = len(self.network.peers)
            if self.miner.is_running():
                rate = self.miner.hashrate_local()
                mining = f" | Local: {self._fmt_hashrate(rate)}"
            else:
                mining = " | OFF"
            lock = "LOCK " if self.wallet.is_locked() else ""
            self.status.set(
                f"{lock}DOGK v2 | Peers: {peers} | #{hgt} | "
                f"Bits: 0x{bits:08X}->0x{next_bits:08X} | "
                f"Rede: {self._fmt_hashrate(hashrate_rede)}{mining}"
            )
            self.update_log()
            self.update_mining_buttons()
        except:
            pass

    def refresh(self):
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
    try:
        DogKongCore().run()
    except Exception as e:
        try:
            messagebox.showerror("DogKong v2 - Erro", str(e))
        except:
            print(e)
        traceback.print_exc()