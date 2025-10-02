# services/migrations.py — migrações seguras (SQLite)
from __future__ import annotations
import sqlite3
from .storage import DB_PATH

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _has_table(conn, name: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def _columns(conn, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in cur.fetchall()}

# --- Empresas: garantir colunas (mantido do seu base) ---
def ensure_companies_columns():
    with _connect() as conn:
        if not _has_table(conn, "companies"):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companies(
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    cnpj TEXT,
                    ie   TEXT,
                    im   TEXT,
                    phone TEXT,
                    email TEXT,
                    email_principal TEXT,
                    address TEXT,
                    city TEXT,
                    uf TEXT,
                    cep TEXT,
                    socio_nome TEXT,
                    socio_estado_civil TEXT,
                    socio_rg TEXT,
                    socio_cpf TEXT,
                    socio_endereco TEXT,
                    socio_data_nascimento TEXT,
                    socio_nome_pai TEXT,
                    socio_nome_mae TEXT,
                    comprasnet_login TEXT,
                    comprasnet_senha TEXT,
                    comprasnet_obs TEXT,
                    pcp_login TEXT,
                    pcp_senha TEXT,
                    pcp_obs TEXT,
                    bnc_login TEXT,
                    bnc_senha TEXT,
                    bnc_obs TEXT,
                    licitanet_login TEXT,
                    licitanet_senha TEXT,
                    licitanet_obs TEXT,
                    compraspara_login TEXT,
                    compraspara_senha TEXT,
                    compraspara_obs TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
        else:
            need_cols = {
                "email_principal","socio_nome","socio_estado_civil","socio_rg","socio_cpf",
                "socio_endereco","socio_data_nascimento","socio_nome_pai","socio_nome_mae",
                "comprasnet_login","comprasnet_senha","comprasnet_obs",
                "pcp_login","pcp_senha","pcp_obs",
                "bnc_login","bnc_senha","bnc_obs",
                "licitanet_login","licitanet_senha","licitanet_obs",
                "compraspara_login","compraspara_senha","compraspara_obs",
                "created_at"
            }
            cols = _columns(conn, "companies")
            for col in need_cols - cols:
                conn.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT")
            conn.commit()

def ensure_company_credentials():
    with _connect() as conn:
        if not _has_table(conn, "company_credentials"):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS company_credentials(
                    id INTEGER PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    portal TEXT NOT NULL,
                    login TEXT,
                    senha TEXT,
                    url TEXT,
                    obs TEXT,
                    UNIQUE(company_id, portal),
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

def ensure_licitacoes_table():
    """Cria a tabela `licitacoes` se não existir (idempotente)."""
    with _connect() as conn:
        if not _has_table(conn, "licitacoes"):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS licitacoes (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER,
                    orgao TEXT,
                    modalidade TEXT,
                    processo TEXT,
                    data_sessao TEXT,
                    hora TEXT,
                    qtd_itens TEXT,
                    valor_estimado TEXT,
                    link TEXT,
                    tem_lotes INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY(empresa_id) REFERENCES companies(id) ON DELETE SET NULL
                )
            """)
            conn.commit()
        else:
            cols = _columns(conn, "licitacoes")
            if "tem_lotes" not in cols:
                conn.execute("ALTER TABLE licitacoes ADD COLUMN tem_lotes INTEGER DEFAULT 0")
            if "created_at" not in cols:
                conn.execute("ALTER TABLE licitacoes ADD COLUMN created_at TEXT")
            conn.commit()

def run_all():
    ensure_companies_columns()
    ensure_company_credentials()
    ensure_licitacoes_table()
    ensure_cotacoes_table()
    ensure_banco_precos_table()
    ensure_certidoes_table()

def ensure_cotacoes_table():
    """Cria/ajusta a tabela `cotacoes` (empresa_id compatível com legado)."""
    with _connect() as conn:
        if not _has_table(conn, "cotacoes"):
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cotacoes (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER,
                    item TEXT NOT NULL,
                    preco REAL,
                    validade TEXT,
                    fonte TEXT,
                    observacoes TEXT,
                    created_at TEXT,
                    FOREIGN KEY(empresa_id) REFERENCES companies(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cot_empresa ON cotacoes(empresa_id);
            """)
            conn.commit()
        else:
            cols = _columns(conn, "cotacoes")
            if "empresa_id" not in cols:
                conn.execute("ALTER TABLE cotacoes ADD COLUMN empresa_id INTEGER")
            if "company_id" in cols:
                conn.execute("UPDATE cotacoes SET empresa_id=company_id WHERE empresa_id IS NULL")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cot_empresa ON cotacoes(empresa_id)")
            if "created_at" not in cols:
                conn.execute("ALTER TABLE cotacoes ADD COLUMN created_at TEXT")
            conn.commit()

# --- NOVO: Banco de Preços ---
def ensure_banco_precos_table():
    """
    Cria/ajusta a tabela `banco_precos` com índices.
    Campos: produto, categoria, tipo_origem, origem_nome, marca, unidade, embalagem,
            preco (REAL), data_coleta (dd/mm/aaaa), link, observacoes, created_at.
    """
    with _connect() as conn:
        # cria se não existir
        if not _has_table(conn, "banco_precos"):
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS banco_precos (
                    id INTEGER PRIMARY KEY,
                    produto TEXT NOT NULL,
                    categoria TEXT,
                    tipo_origem TEXT,        -- Mercado | Fornecedor
                    origem_nome TEXT,        -- nome do mercado/fornecedor
                    marca TEXT,
                    unidade TEXT,            -- ex.: kg, pacote, un, cx
                    embalagem TEXT,          -- ex.: 5kg, 500g, 12x500ml
                    preco REAL,
                    data_coleta TEXT,        -- dd/mm/aaaa
                    link TEXT,               -- quando online
                    observacoes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_preco_produto  ON banco_precos(produto);
                CREATE INDEX IF NOT EXISTS idx_preco_categoria ON banco_precos(categoria);
                CREATE INDEX IF NOT EXISTS idx_preco_tipo      ON banco_precos(tipo_origem);
                CREATE INDEX IF NOT EXISTS idx_preco_origem    ON banco_precos(origem_nome);
                CREATE INDEX IF NOT EXISTS idx_preco_data      ON banco_precos(data_coleta);
            """)
            conn.commit()
        else:
            # garantir colunas e índices em bases antigas
            cols = _columns(conn, "banco_precos")
            want = {
                "produto":"TEXT","categoria":"TEXT","tipo_origem":"TEXT","origem_nome":"TEXT",
                "marca":"TEXT","unidade":"TEXT","embalagem":"TEXT","preco":"REAL",
                "data_coleta":"TEXT","link":"TEXT","observacoes":"TEXT","created_at":"TEXT"
            }
            for c, typ in want.items():
                if c not in cols:
                    conn.execute(f"ALTER TABLE banco_precos ADD COLUMN {c} {typ}")
            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_preco_produto  ON banco_precos(produto);
                CREATE INDEX IF NOT EXISTS idx_preco_categoria ON banco_precos(categoria);
                CREATE INDEX IF NOT EXISTS idx_preco_tipo      ON banco_precos(tipo_origem);
                CREATE INDEX IF NOT EXISTS idx_preco_origem    ON banco_precos(origem_nome);
                CREATE INDEX IF NOT EXISTS idx_preco_data      ON banco_precos(data_coleta);
            """)
            conn.commit()

# --- NOVO: Certidões ---
def ensure_certidoes_table():
    """
    Tabela `certidoes` para controlar documentos por empresa.
    """
    with _connect() as conn:
        if not _has_table(conn, "certidoes"):
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS certidoes (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER,             -- FK para companies.id
                    tipo TEXT,                      -- ex: FGTS, INSS, Municipal, Estadual...
                    orgao_emissor TEXT,             -- quem emite
                    numero TEXT,                    -- identificador/código
                    situacao TEXT,                  -- Válida | Vencida | Pendente
                    dt_emissao TEXT,                -- dd/mm/aaaa
                    dt_validade TEXT,               -- dd/mm/aaaa
                    link_consulta TEXT,             -- URL de conferência
                    arquivo TEXT,                   -- caminho/identificador do arquivo (opcional)
                    observacoes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY(empresa_id) REFERENCES companies(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cert_empresa  ON certidoes(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_cert_tipo     ON certidoes(tipo);
                CREATE INDEX IF NOT EXISTS idx_cert_situacao ON certidoes(situacao);
                CREATE INDEX IF NOT EXISTS idx_cert_validade ON certidoes(dt_validade);
            """)
            conn.commit()
        else:
            cols = _columns(conn, "certidoes")
            need = {
                "empresa_id":"INTEGER","tipo":"TEXT","orgao_emissor":"TEXT","numero":"TEXT",
                "situacao":"TEXT","dt_emissao":"TEXT","dt_validade":"TEXT","link_consulta":"TEXT",
                "arquivo":"TEXT","observacoes":"TEXT","created_at":"TEXT"
            }
            for c, t in need.items():
                if c not in cols:
                    conn.execute(f"ALTER TABLE certidoes ADD COLUMN {c} {t}")
            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_cert_empresa  ON certidoes(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_cert_tipo     ON certidoes(tipo);
                CREATE INDEX IF NOT EXISTS idx_cert_situacao ON certidoes(situacao);
                CREATE INDEX IF NOT EXISTS idx_cert_validade ON certidoes(dt_validade);
            """)
            conn.commit()
