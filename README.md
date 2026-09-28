# 🐕🦍 DogKong v2.5

Cryptocurrency with Bitcoin-style difficulty (bits/target + LWMA), CPU+RAM PoW.

## Download
https://github.com/marquesslim-hue/DOGKONG/releases/download/v2.5/DogKongV2.5.rar

Get the latest version: [Releases](https://github.com/marquesslim-hue/DOGKONG/releases)

## Official Links

| Service | URL |
|---|---|
| 💰 Web Wallet | https://dogkongwallet.duckdns.org/carteira |
| 🔍 Explorer | https://dogkong.duckdns.org/ |
| 🌱 Seed Node | `seeddogkong.duckdns.org:18555` |

## Specifications

| Spec | Value |
|---|---|
| Ticker | DOGK |
| Chain ID | DOGK-V2-MAINNET |
| Block time | 60 seconds |
| Block reward | 10,000 DOGK |
| PoW | CPU + RAM (64 MB, 128 iterations) |
| Difficulty | bits/target + LWMA (14-block window) |
| P2P port | 18555 |
| Mnemonic | BIP39 (12 words) |
| Derivation | BIP32 (m/44'/9999'/0'/0/0) |
| Encryption | Argon2id + AES-256-GCM |

## How to Use

1. Download `DOGKONG_2.rar` from Releases
2. Extract to a folder (e.g. `C:\DogKong\`)
3. Run `DogKong.exe`
4. File → New Wallet (save the 12 words!)
5. Click "Mine" and choose your H/s limit

⚠️ **NEVER share your private key, WIF, or 12 words.**

## Build from Source

```bash
pip install pyinstaller pycryptodome cryptography

python -m PyInstaller --onefile --windowed --name DogKong ^
  --hidden-import=Crypto ^
  --hidden-import=Crypto.Hash.RIPEMD160 ^
  --hidden-import=cryptography ^
  --collect-all Crypto ^
  dogk_core.py
