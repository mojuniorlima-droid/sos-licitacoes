# === services/storage.py ===
import os

# Diretório base do projeto (onde fica o main.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Caminhos dos arquivos de logo
LOGO_PNG = os.path.join(BASE_DIR, "logo.png")
LOGO_ICO = os.path.join(BASE_DIR, "logo.ico")

# Banco de dados SQLite
DB_PATH = os.path.join(BASE_DIR, "data.db")

# Pasta de exportações (CSV, Excel, etc.)
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)
