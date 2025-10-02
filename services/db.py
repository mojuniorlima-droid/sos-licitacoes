# services/db.py
from __future__ import annotations

"""
DB unificado do projeto "Novo 5 atual" — compatível com Flet 0.28.3.

- Importa TUDO do legado (services/db_legacy.py) para não quebrar outras páginas.
- Fornece CRUD de EMPRESAS (compat PT/EN + credenciais + campos extras do sócio
  + e-mail principal da empresa).
- Fornece CRUD de LICITAÇÕES com FK para companies e ON DELETE SET NULL.
- Migrações idempotentes (NÃO perdem dados).
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# 1) IMPORTA O DB LEGADO (mantém tudo que já existia nas outras páginas)
# -----------------------------------------------------------------------------
_legacy = None
try:
    from . import db_legacy as _legacy  # type: ignore
    for _name in dir(_legacy):
        if _name.startswith("_"):
            continue
        # Não sobrescreve nomes que definimos aqui
        if _name in globals():
            continue
        globals()[_name] = getattr(_legacy, _name)
except Exception:
    pass

# -----------------------------------------------------------------------------
# 2) CONEXÃO / CAMINHO DO DB
# -----------------------------------------------------------------------------
def _load_db_path() -> str:
    # 1) storage.DB_PATH
    try:
        from .storage import DB_PATH as _DB  # type: ignore
        if _DB and str(_DB).strip():
            return str(_DB).strip()
    except Exception:
        pass
    # 2) .env DB_PATH
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
        envp = os.getenv("DB_PATH")
        if envp and envp.strip():
            return envp.strip()
    except Exception:
        pass
    # 3) fallback: ../app.db
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.db"))

DB_PATH = _load_db_path()

def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = _dict_factory
        yield conn
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# 3) ESQUEMAS / MIGRAÇÕES
#    (empresas + licitações, idempotentes)
# -----------------------------------------------------------------------------
SCHEMA_SQL_EMPRESAS = """
CREATE TABLE IF NOT EXISTS companies (
    id                      INTEGER PRIMARY KEY,
    -- empresa
    name                    TEXT,
    cnpj                    TEXT,
    ie                      TEXT,
    im                      TEXT,
    phone                   TEXT,
    email                   TEXT,
    email_principal_login   TEXT,  -- login da caixa de e-mail principal
    email_principal_senha   TEXT,  -- senha da caixa de e-mail principal
    -- endereço
    address_street          TEXT,
    address_number          TEXT,
    address_bairro          TEXT,
    address_cidade          TEXT,
    address_estado          TEXT,
    address_cep             TEXT,
    -- banco
    bank_nome               TEXT,
    bank_agencia            TEXT,
    bank_conta              TEXT,
    -- sócio
    socio_nome              TEXT,
    socio_estado_civil      TEXT,
    socio_rg                TEXT,
    socio_cpf               TEXT,
    socio_endereco          TEXT,
    socio_nascimento        TEXT,  -- dd/mm/aaaa
    socio_pai               TEXT,
    socio_mae               TEXT,
    -- credenciais (portais)
    comprasnet_login        TEXT,
    comprasnet_senha        TEXT,
    comprasnet_obs          TEXT,
    pcp_login               TEXT,
    pcp_senha               TEXT,
    pcp_obs                 TEXT,
    bnc_login               TEXT,
    bnc_senha               TEXT,
    bnc_obs                 TEXT,
    licitanet_login         TEXT,
    licitanet_senha         TEXT,
    licitanet_obs           TEXT,
    compraspara_login       TEXT,
    compraspara_senha       TEXT,
    compraspara_obs         TEXT,
    created_at              TEXT
);
"""

SCHEMA_SQL_LICITACOES = """
CREATE TABLE IF NOT EXISTS licitacoes (
    id              INTEGER PRIMARY KEY,
    empresa_id      INTEGER,
    orgao           TEXT,
    modalidade      TEXT,
    processo        TEXT,
    data_sessao     TEXT,
    hora            TEXT,
    qtd_itens       TEXT,
    valor_estimado  TEXT,
    link            TEXT,
    tem_lotes       INTEGER DEFAULT 0,
    created_at      TEXT,
    FOREIGN KEY(empresa_id) REFERENCES companies(id) ON DELETE SET NULL
);
"""

def _ensure_company_columns(conn: sqlite3.Connection) -> None:
    """Garante todas as colunas usadas na página Empresas (idempotente)."""
    conn.executescript(SCHEMA_SQL_EMPRESAS)
    # Adiciona colunas que possam faltar em bases antigas
    info = conn.execute("PRAGMA table_info(companies)").fetchall()
    have = {r["name"] for r in info}
    need = [
        "email_principal_login","email_principal_senha",
        "address_street","address_number","address_bairro","address_cidade","address_estado","address_cep",
        "bank_nome","bank_agencia","bank_conta",
        "socio_nascimento","socio_pai","socio_mae",
        "comprasnet_login","comprasnet_senha","comprasnet_obs",
        "pcp_login","pcp_senha","pcp_obs",
        "bnc_login","bnc_senha","bnc_obs",
        "licitanet_login","licitanet_senha","licitanet_obs",
        "compraspara_login","compraspara_senha","compraspara_obs",
        "created_at",
    ]
    for c in need:
        if c not in have:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {c} TEXT")
    conn.commit()

def _ensure_licitacoes(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL_LICITACOES)
    conn.commit()

def init_db_empresas() -> None:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_company_columns(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_cnpj ON companies(cnpj)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)")
        conn.commit()

def init_db_licitacoes() -> None:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_licitacoes(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_licitacoes_empresa ON licitacoes(empresa_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_licitacoes_data ON licitacoes(data_sessao)")
        conn.commit()

# tenta inicializar, mas não falha o import
try:
    init_db_empresas()
    init_db_licitacoes()
except Exception:
    pass

# -----------------------------------------------------------------------------
# 4) HELPERS
# -----------------------------------------------------------------------------
def _smallest_free_id(conn: sqlite3.Connection, table: str) -> int:
    rows = conn.execute(f"SELECT id FROM {table} ORDER BY id ASC").fetchall()
    used = [r["id"] for r in rows if r.get("id") is not None]
    nxt = 1
    for v in used:
        if v == nxt:
            nxt += 1
        elif v > nxt:
            break
    return nxt

def _g(data: Dict[str, Any], *keys: str) -> str:
    """Primeiro valor não vazio (aceita aliases)."""
    for k in keys:
        v = data.get(k)
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
        if v not in ("", None, []):
            return str(v)
    return ""

def _bool01(v) -> int:
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return 1 if v != 0 else 0
    s = str(v or "").strip().lower()
    return 1 if s in ("1","true","t","yes","sim","y","on") else 0

# -----------------------------------------------------------------------------
# 5) CRUD EMPRESAS (compat com a página)
# -----------------------------------------------------------------------------
def add_company(data: Dict[str, Any]) -> int:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_company_columns(conn)

        cid = _smallest_free_id(conn, "companies")
        now = date.today().isoformat()

        cols = (
            "id","name","cnpj","ie","im","phone","email",
            "email_principal_login","email_principal_senha",
            "address_street","address_number","address_bairro","address_cidade","address_estado","address_cep",
            "bank_nome","bank_agencia","bank_conta",
            "socio_nome","socio_estado_civil","socio_rg","socio_cpf","socio_endereco",
            "socio_nascimento","socio_pai","socio_mae",
            "comprasnet_login","comprasnet_senha","comprasnet_obs",
            "pcp_login","pcp_senha","pcp_obs",
            "bnc_login","bnc_senha","bnc_obs",
            "licitanet_login","licitanet_senha","licitanet_obs",
            "compraspara_login","compraspara_senha","compraspara_obs",
            "created_at"
        )
        vals = [
            cid,
            _g(data,"name","nome"),
            _g(data,"cnpj"),
            _g(data,"ie","inscricao_estadual"),
            _g(data,"im","inscricao_municipal"),
            _g(data,"phone","telefone"),
            _g(data,"email"),
            _g(data,"email_principal_login","email_login","mail_login"),
            _g(data,"email_principal_senha","email_senha","mail_senha"),
            _g(data,"address_street","logradouro"),
            _g(data,"address_number","numero"),
            _g(data,"address_bairro","bairro"),
            _g(data,"address_cidade","cidade"),
            _g(data,"address_estado","uf"),
            _g(data,"address_cep","cep"),
            _g(data,"bank_nome","banco"),
            _g(data,"bank_agencia","agencia"),
            _g(data,"bank_conta","conta"),
            _g(data,"socio_nome"),
            _g(data,"socio_estado_civil"),
            _g(data,"socio_rg"),
            _g(data,"socio_cpf"),
            _g(data,"socio_endereco"),
            _g(data,"socio_nascimento","socio_data_nascimento","data_nascimento"),
            _g(data,"socio_pai","nome_pai","pai"),
            _g(data,"socio_mae","nome_mae","mae"),
            _g(data,"comprasnet_login","compras_gov_login","comprasgovbr_login","compras_gov_br_login"),
            _g(data,"comprasnet_senha","compras_gov_senha","comprasgovbr_senha","compras_gov_br_senha"),
            _g(data,"comprasnet_obs","compras_gov_obs","comprasgovbr_obs","compras_gov_br_obs"),
            _g(data,"pcp_login","portalcompras_login","portal_compras_publicas_login"),
            _g(data,"pcp_senha","portalcompras_senha","portal_compras_publicas_senha"),
            _g(data,"pcp_obs","portalcompras_obs","portal_compras_publicas_obs"),
            _g(data,"bnc_login","bionexo_login"),
            _g(data,"bnc_senha","bionexo_senha"),
            _g(data,"bnc_obs","bionexo_obs"),
            _g(data,"licitanet_login"),
            _g(data,"licitanet_senha"),
            _g(data,"licitanet_obs"),
            _g(data,"compraspara_login","compras_pa_login","compraspara_pa_login"),
            _g(data,"compraspara_senha","compras_pa_senha","compraspara_pa_senha"),
            _g(data,"compraspara_obs","compras_pa_obs","compraspara_pa_obs"),
            now
        ]

        qms = ",".join(["?"]*len(cols))
        conn.execute(f"INSERT INTO companies ({','.join(cols)}) VALUES ({qms})", vals)
        conn.commit()
        return cid

def upd_company(cid: int, data: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_company_columns(conn)

        sets = (
            "name","cnpj","ie","im","phone","email",
            "email_principal_login","email_principal_senha",
            "address_street","address_number","address_bairro","address_cidade","address_estado","address_cep",
            "bank_nome","bank_agencia","bank_conta",
            "socio_nome","socio_estado_civil","socio_rg","socio_cpf","socio_endereco",
            "socio_nascimento","socio_pai","socio_mae",
            "comprasnet_login","comprasnet_senha","comprasnet_obs",
            "pcp_login","pcp_senha","pcp_obs",
            "bnc_login","bnc_senha","bnc_obs",
            "licitanet_login","licitanet_senha","licitanet_obs",
            "compraspara_login","compraspara_senha","compraspara_obs"
        )
        vals = [
            _g(data,"name","nome"),
            _g(data,"cnpj"),
            _g(data,"ie","inscricao_estadual"),
            _g(data,"im","inscricao_municipal"),
            _g(data,"phone","telefone"),
            _g(data,"email"),
            _g(data,"email_principal_login","email_login","mail_login"),
            _g(data,"email_principal_senha","email_senha","mail_senha"),
            _g(data,"address_street","logradouro"),
            _g(data,"address_number","numero"),
            _g(data,"address_bairro","bairro"),
            _g(data,"address_cidade","cidade"),
            _g(data,"address_estado","uf"),
            _g(data,"address_cep","cep"),
            _g(data,"bank_nome","banco"),
            _g(data,"bank_agencia","agencia"),
            _g(data,"bank_conta","conta"),
            _g(data,"socio_nome"),
            _g(data,"socio_estado_civil"),
            _g(data,"socio_rg"),
            _g(data,"socio_cpf"),
            _g(data,"socio_endereco"),
            _g(data,"socio_nascimento","socio_data_nascimento","data_nascimento"),
            _g(data,"socio_pai","nome_pai","pai"),
            _g(data,"socio_mae","nome_mae","mae"),
            _g(data,"comprasnet_login","compras_gov_login","comprasgovbr_login","compras_gov_br_login"),
            _g(data,"comprasnet_senha","compras_gov_senha","comprasgovbr_senha","compras_gov_br_senha"),
            _g(data,"comprasnet_obs","compras_gov_obs","comprasgovbr_obs","compras_gov_br_obs"),
            _g(data,"pcp_login","portalcompras_login","portal_compras_publicas_login"),
            _g(data,"pcp_senha","portalcompras_senha","portal_compras_publicas_senha"),
            _g(data,"pcp_obs","portalcompras_obs","portal_compras_publicas_obs"),
            _g(data,"bnc_login","bionexo_login"),
            _g(data,"bnc_senha","bionexo_senha"),
            _g(data,"bnc_obs","bionexo_obs"),
            _g(data,"licitanet_login"),
            _g(data,"licitanet_senha"),
            _g(data,"licitanet_obs"),
            _g(data,"compraspara_login","compras_pa_login","compraspara_pa_login"),
            _g(data,"compraspara_senha","compras_pa_senha","compraspara_pa_senha"),
            _g(data,"compraspara_obs","compras_pa_obs","compraspara_pa_obs"),
        ]
        sql = "UPDATE companies SET " + ", ".join([f"{k}=?" for k in sets]) + " WHERE id=?"
        conn.execute(sql, vals + [int(cid)])
        conn.commit()

def del_company(cid: int) -> None:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        # Tenta deletar direto (ON DELETE SET NULL já deve resolver)
        try:
            conn.execute("DELETE FROM companies WHERE id=?", (int(cid),))
            conn.commit()
            return
        except sqlite3.IntegrityError:
            # Bases antigas sem SET NULL: zera empresa_id nas licitações e tenta de novo
            conn.execute("UPDATE licitacoes SET empresa_id=NULL WHERE empresa_id=?", (int(cid),))
            conn.execute("DELETE FROM companies WHERE id=?", (int(cid),))
            conn.commit()

def get_company(cid: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM companies WHERE id=?", (int(cid),)).fetchone()
        return row if row else None

def list_companies() -> List[Dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM companies ORDER BY id ASC")
        return cur.fetchall()

# ALIASES (compat)
def companies_all() -> List[Dict[str, Any]]: return list_companies()
def list_company() -> List[Dict[str, Any]]: return list_companies()
def empresas_all() -> List[Dict[str, Any]]: return list_companies()
def get_empresas() -> List[Dict[str, Any]]: return list_companies()
def empresas_list() -> List[Dict[str, Any]]: return list_companies()

def add_empresa(data: Dict[str, Any]) -> int: return add_company(data)
def nova_empresa(data: Dict[str, Any]) -> int: return add_company(data)
def empresa_add(data: Dict[str, Any]) -> int: return add_company(data)

def upd_empresa(cid: int, data: Dict[str, Any]) -> None: return upd_company(cid, data)
def update_empresa(cid: int, data: Dict[str, Any]) -> None: return upd_company(cid, data)
def edit_empresa(cid: int, data: Dict[str, Any]) -> None: return upd_company(cid, data)

def empresa_del(cid: int) -> None: return del_company(cid)
def delete_empresa(cid: int) -> None: return del_company(cid)
def remove_empresa(cid: int) -> None: return del_company(cid)

def company_get(cid: int) -> Optional[Dict[str, Any]]: return get_company(cid)

# -----------------------------------------------------------------------------
# 6) LICITAÇÕES — CRUD
# -----------------------------------------------------------------------------
def list_licitacoes() -> List[Dict[str, Any]]:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_licitacoes(conn)
        sql = """
        SELECT
            L.id,
            L.empresa_id,
            C.name AS empresa_nome,
            L.orgao,
            L.modalidade,
            L.processo,
            L.data_sessao,
            L.hora,
            L.qtd_itens,
            L.valor_estimado,
            L.link,
            L.tem_lotes,
            L.created_at
        FROM licitacoes L
        LEFT JOIN companies C ON C.id = L.empresa_id
        ORDER BY L.id ASC
        """
        return conn.execute(sql).fetchall() or []

def add_licitacao(data: Dict[str, Any]) -> int:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_licitacoes(conn)

        lid = _smallest_free_id(conn, "licitacoes")
        now = date.today().isoformat()
        fields = ("id","empresa_id","orgao","modalidade","processo",
                  "data_sessao","hora","qtd_itens","valor_estimado",
                  "link","tem_lotes","created_at")
        payload = (
            lid,
            int((data.get("empresa_id") or 0) or 0) or None,
            _g(data,"orgao"),
            _g(data,"modalidade"),
            _g(data,"processo"),
            _g(data,"data_sessao","data"),
            _g(data,"hora"),
            _g(data,"qtd_itens","itens"),
            _g(data,"valor_estimado","valor"),
            _g(data,"link","url"),
            _bool01(data.get("tem_lotes",0)),
            now
        )
        qmarks = ",".join(["?"]*len(fields))
        conn.execute(f"INSERT INTO licitacoes ({','.join(fields)}) VALUES ({qmarks})", payload)
        conn.commit()
        return lid

def upd_licitacao(lid: int, data: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _ensure_licitacoes(conn)
        sets = [
            ("empresa_id", int((data.get("empresa_id") or 0) or 0) or None),
            ("orgao", _g(data,"orgao")),
            ("modalidade", _g(data,"modalidade")),
            ("processo", _g(data,"processo")),
            ("data_sessao", _g(data,"data_sessao","data")),
            ("hora", _g(data,"hora")),
            ("qtd_itens", _g(data,"qtd_itens","itens")),
            ("valor_estimado", _g(data,"valor_estimado","valor")),
            ("link", _g(data,"link","url")),
            ("tem_lotes", _bool01(data.get("tem_lotes",0))),
        ]
        sql = "UPDATE licitacoes SET " + ", ".join([f"{k}=?" for k,_ in sets]) + " WHERE id=?"
        params = [v for _,v in sets] + [int(lid)]
        conn.execute(sql, params)
        conn.commit()

def del_licitacao(lid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM licitacoes WHERE id=?", (int(lid),))
        conn.commit()

# aliases compat
def licitacoes_all() -> List[Dict[str, Any]]: return list_licitacoes()
def get_licitacoes() -> List[Dict[str, Any]]: return list_licitacoes()
def licitacao_add(data: Dict[str, Any]) -> int: return add_licitacao(data)
def nova_licitacao(data: Dict[str, Any]) -> int: return add_licitacao(data)
def update_licitacao(lid: int, data: Dict[str, Any]) -> None: return upd_licitacao(lid, data)
def licitacao_upd(lid: int, data: Dict[str, Any]) -> None: return upd_licitacao(lid, data)
def delete_licitacao(lid: int) -> None: return del_licitacao(lid)
def licitacao_del(lid: int) -> None: return del_licitacao(lid)

# ============================
# Banco de Preços — CRUD nativo
# ============================
import sqlite3
from services.storage import DB_PATH  # já deve existir no arquivo; mantém por segurança

def _bp__table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None

def _bp__columns(conn, table: str) -> set[str]:
    try:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall() or []
        return { (r[1] if isinstance(r, tuple) else r["name"]) for r in info }
    except Exception:
        return set()

def _bp__ensure_banco_precos():
    """Defensivo: garante a existência/colunas/índices mesmo sem rodar migrations."""
    con = sqlite3.connect(DB_PATH)
    try:
        if not _bp__table_exists(con, "banco_precos"):
            con.executescript("""
                CREATE TABLE IF NOT EXISTS banco_precos (
                    id INTEGER PRIMARY KEY,
                    produto TEXT NOT NULL,
                    categoria TEXT,
                    tipo_origem TEXT,
                    origem_nome TEXT,
                    marca TEXT,
                    unidade TEXT,
                    embalagem TEXT,
                    preco REAL,
                    data_coleta TEXT,
                    link TEXT,
                    observacoes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_preco_produto  ON banco_precos(produto);
                CREATE INDEX IF NOT EXISTS idx_preco_categoria ON banco_precos(categoria);
                CREATE INDEX IF NOT EXISTS idx_preco_tipo      ON banco_precos(tipo_origem);
                CREATE INDEX IF NOT EXISTS idx_preco_origem    ON banco_precos(origem_nome);
                CREATE INDEX IF NOT EXISTS idx_preco_data      ON banco_precos(data_coleta);
            """); con.commit()
        else:
            cols = _bp__columns(con, "banco_precos")
            want = {
                "produto":"TEXT","categoria":"TEXT","tipo_origem":"TEXT","origem_nome":"TEXT",
                "marca":"TEXT","unidade":"TEXT","embalagem":"TEXT","preco":"REAL",
                "data_coleta":"TEXT","link":"TEXT","observacoes":"TEXT","created_at":"TEXT"
            }
            for c, typ in want.items():
                if c not in cols:
                    con.execute(f"ALTER TABLE banco_precos ADD COLUMN {c} {typ}")
            con.executescript("""
                CREATE INDEX IF NOT EXISTS idx_preco_produto  ON banco_precos(produto);
                CREATE INDEX IF NOT EXISTS idx_preco_categoria ON banco_precos(categoria);
                CREATE INDEX IF NOT EXISTS idx_preco_tipo      ON banco_precos(tipo_origem);
                CREATE INDEX IF NOT EXISTS idx_preco_origem    ON banco_precos(origem_nome);
                CREATE INDEX IF NOT EXISTS idx_preco_data      ON banco_precos(data_coleta);
            """); con.commit()
    finally:
        con.close()

def _bp__money_to_float(v):
    if v is None: return None
    if isinstance(v, (int,float)): return float(v)
    s = str(v).strip().replace("R$","").replace(" ","").replace(".","").replace(",",".")
    try: return float(s)
    except Exception: return None

# -------- LIST --------
def list_banco_precos(filtros: dict | None = None):
    """
    Lista registros do banco de preços.
    filtros opcionais:
      - categoria: str | "Todas"
      - tipo_origem: str | "Todos"
      - q: str (busca em produto/origem_nome/marca)
    """
    _bp__ensure_banco_precos()
    filtros = filtros or {}
    categoria = filtros.get("categoria")
    tipo      = filtros.get("tipo_origem")
    q         = filtros.get("q")

    where, args = [], []
    if categoria and categoria != "Todas":
        where.append("categoria = ?"); args.append(categoria)
    if tipo and tipo != "Todos":
        where.append("tipo_origem = ?"); args.append(tipo)
    if q:
        like = f"%{q.strip()}%"
        where.append("(produto LIKE ? OR origem_nome LIKE ? OR marca LIKE ?)")
        args.extend([like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    try:
        rows = con.execute(f"""
            SELECT id, produto, categoria, tipo_origem, origem_nome, marca,
                   unidade, embalagem, preco, data_coleta, link, observacoes
            FROM banco_precos
            {where_sql}
            ORDER BY id DESC
        """, args).fetchall() or []
        return [dict(r) for r in rows]
    finally:
        con.close()

# -------- ADD --------
def add_banco_preco(data: dict) -> int:
    """
    Insere um registro.
    Campos aceitos: produto (obrigatório), categoria, tipo_origem, origem_nome, marca,
                    unidade, embalagem, preco, data_coleta, link, observacoes
    """
    _bp__ensure_banco_precos()
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    try:
        cur.execute("""
            INSERT INTO banco_precos
                (produto, categoria, tipo_origem, origem_nome, marca,
                 unidade, embalagem, preco, data_coleta, link, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("produto"),
            data.get("categoria"),
            data.get("tipo_origem"),
            data.get("origem_nome"),
            data.get("marca"),
            data.get("unidade"),
            data.get("embalagem"),
            _bp__money_to_float(data.get("preco")),
            data.get("data_coleta"),
            data.get("link"),
            data.get("observacoes"),
        ))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

# -------- UPD --------
def upd_banco_preco(row_id: int, data: dict) -> None:
    """Atualiza um registro por ID."""
    _bp__ensure_banco_precos()
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("""
            UPDATE banco_precos
               SET produto=?, categoria=?, tipo_origem=?, origem_nome=?, marca=?,
                   unidade=?, embalagem=?, preco=?, data_coleta=?, link=?, observacoes=?
             WHERE id=?
        """, (
            data.get("produto"),
            data.get("categoria"),
            data.get("tipo_origem"),
            data.get("origem_nome"),
            data.get("marca"),
            data.get("unidade"),
            data.get("embalagem"),
            _bp__money_to_float(data.get("preco")),
            data.get("data_coleta"),
            data.get("link"),
            data.get("observacoes"),
            row_id
        ))
        con.commit()
    finally:
        con.close()

# -------- DEL --------
def del_banco_preco(row_id: int) -> None:
    """Exclui um registro por ID."""
    _bp__ensure_banco_precos()
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("DELETE FROM banco_precos WHERE id=?", (row_id,))
        con.commit()
    finally:
        con.close()

# ============================
# Certidões — CRUD nativo
# ============================
import sqlite3
from services.storage import DB_PATH

def _ct__table_exists(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

def _ct__columns(conn, table: str) -> set[str]:
    try:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall() or []
        return {(r[1] if isinstance(r, tuple) else r["name"]) for r in info}
    except Exception:
        return set()

def _ct__ensure():
    con = sqlite3.connect(DB_PATH)
    try:
        if not _ct__table_exists(con, "certidoes"):
            con.executescript("""
                CREATE TABLE IF NOT EXISTS certidoes (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER,
                    tipo TEXT,
                    orgao_emissor TEXT,
                    numero TEXT,
                    situacao TEXT,
                    dt_emissao TEXT,
                    dt_validade TEXT,
                    link_consulta TEXT,
                    arquivo TEXT,
                    observacoes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cert_empresa  ON certidoes(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_cert_tipo     ON certidoes(tipo);
                CREATE INDEX IF NOT EXISTS idx_cert_situacao ON certidoes(situacao);
                CREATE INDEX IF NOT EXISTS idx_cert_validade ON certidoes(dt_validade);
            """); con.commit()
        else:
            cols = _ct__columns(con, "certidoes")
            need = {
                "empresa_id":"INTEGER","tipo":"TEXT","orgao_emissor":"TEXT","numero":"TEXT",
                "situacao":"TEXT","dt_emissao":"TEXT","dt_validade":"TEXT","link_consulta":"TEXT",
                "arquivo":"TEXT","observacoes":"TEXT","created_at":"TEXT"
            }
            for c,t in need.items():
                if c not in cols:
                    con.execute(f"ALTER TABLE certidoes ADD COLUMN {c} {t}")
            con.commit()
    finally:
        con.close()

def list_certidoes(filtros: dict | None = None):
    """
    filtros: empresa_id, situacao (Válida|Vencida|Pendente ou 'Todas'),
             tipo (string ou 'Todos'), q (busca: número/órgão/tipo)
    """
    _ct__ensure()
    filtros = filtros or {}
    wh, args = [], []
    emp = filtros.get("empresa_id")
    sit = filtros.get("situacao")
    tipo = filtros.get("tipo")
    q   = filtros.get("q")
    if emp not in (None, "", 0):
        wh.append("c.empresa_id = ?"); args.append(emp)
    if sit and sit not in ("Todas", "Todos"):
        wh.append("c.situacao = ?"); args.append(sit)
    if tipo and tipo not in ("Todos", "Todas"):
        wh.append("c.tipo = ?"); args.append(tipo)
    if q:
        like = f"%{q.strip()}%"
        wh.append("(c.numero LIKE ? OR c.orgao_emissor LIKE ? OR c.tipo LIKE ?)")
        args.extend([like, like, like])
    where = ("WHERE " + " AND ".join(wh)) if wh else ""
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    try:
        rows = con.execute(f"""
            SELECT c.*, COALESCE(e.name,'') AS empresa
              FROM certidoes c
         LEFT JOIN companies e ON e.id = c.empresa_id
            {where}
          ORDER BY c.id DESC
        """, args).fetchall() or []
        return [dict(r) for r in rows]
    finally:
        con.close()

def add_certidao(data: dict) -> int:
    _ct__ensure()
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    try:
        cur.execute("""
            INSERT INTO certidoes
                (empresa_id, tipo, orgao_emissor, numero, situacao,
                 dt_emissao, dt_validade, link_consulta, arquivo, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("empresa_id"), data.get("tipo"), data.get("orgao_emissor"),
            data.get("numero"), data.get("situacao"), data.get("dt_emissao"),
            data.get("dt_validade"), data.get("link_consulta"),
            data.get("arquivo"), data.get("observacoes"),
        ))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def upd_certidao(row_id: int, data: dict) -> None:
    _ct__ensure()
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("""
            UPDATE certidoes
               SET empresa_id=?, tipo=?, orgao_emissor=?, numero=?, situacao=?,
                   dt_emissao=?, dt_validade=?, link_consulta=?, arquivo=?, observacoes=?
             WHERE id=?
        """, (
            data.get("empresa_id"), data.get("tipo"), data.get("orgao_emissor"),
            data.get("numero"), data.get("situacao"), data.get("dt_emissao"),
            data.get("dt_validade"), data.get("link_consulta"),
            data.get("arquivo"), data.get("observacoes"), row_id
        ))
        con.commit()
    finally:
        con.close()

def del_certidao(row_id: int) -> None:
    _ct__ensure()
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("DELETE FROM certidoes WHERE id=?", (row_id,))
        con.commit()
    finally:
        con.close()
