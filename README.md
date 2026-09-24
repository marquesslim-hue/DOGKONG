# 🐕 DOGKONG

wallet: https://dogkongwallet.duckdns.org/carteira

explore: https://dogkong.duckdns.org/


**DogKong v2** — Cryptocurrency with miner, wallet, and P2P network.

## 🚀 Download

👉 **[Download DogKong v2.0](https://github.com/marquesslim-hue/DOGKONG/releases/download/v2.0/dogkong_v2.zip)**

## ⚠️ IMPORTANT NOTICE (Windows)

Windows may show a security warning ("Windows protected your PC"). **It is NOT a virus** — it's because the `.exe` has no digital signature.

**To open it:**
1. Click **"More info"**
2. Click **"Run anyway"**
3. Done!

## 📦 How to use

1. Download `dogkong_v2.zip`
2. Extract to a folder
3. Run `DogKong.exe`
4. Click **"Minerar"** (Mine)
5. Done! You're mining DOGK

## 🎯 Features

- ⛏️ CPU + 64MB RAM miner
- 💼 Built-in wallet
- 🌐 P2P network (port 18555)
- 📦 Single executable (auto-creates data folder)

## 📊 Network info

| Item | Value |
|------|-------|
| **Total supply** | 10,000,000,000 DOGK |
| **Block reward** | 10,000 DOGK |
| **Block time** | 60 seconds |
| **Seed** | `seeddogkong.duckdns.org` |
| **P2P port** | 18555 |

## 💻 Build from source

```bash
pip install pycryptodome pyinstaller
pyinstaller --clean --onefile --windowed --name DogKong --hidden-import=Crypto --collect-all Crypto dogkong_v2.py
