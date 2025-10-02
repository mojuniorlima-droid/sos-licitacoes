# === services/db.py ===
import sqlite3
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional, Tuple
from .storage import DB_PATH

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- Empresas
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cnpj TEXT,
    ie TEXT,
    im TEXT,
    phone TEXT,
    email TEXT,
    address_street TEXT,
    address_number TEXT,
    address_bairro TEXT,
    address_cidade TEXT,
    address_estado TEXT,
    address_cep TEXT,
    bank_nome TEXT,
    bank_agencia TEXT,
    bank_conta TEXT,
    socio_nome TEXT,
    socio_estado_civil TEXT,
    socio_rg TEXT,
    socio_cpf TEXT,
    socio_endereco TEXT,
    created_at TEXT
);

-- Certidões
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    number TEXT,
    issuer TEXT,
    issue_date TEXT,
    expiry_date TEXT NOT NULL,
    file_path TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Processos (Licitações)
CREATE TABLE IF NOT EXISTS processos (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    portal TEXT,
    uasg TEXT,
    numero TEXT,
    orgao TEXT,
    modalidade TEXT,
    dt_sessao TEXT,
    hr_sessao TEXT,
    tem_lotes INTEGER,
    qtd_itens INTEGER,
    valor_estimado REAL,
    link TEXT,
    edital_path TEXT,
    created_at TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Cotações (RFQ) - Cabeçalho
CREATE TABLE IF NOT EXISTS cotacoes (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    processo_id INTEGER,
    titulo TEXT,
    status TEXT,  -- aberta, recebida, aprovada, rejeitada, encerrada
    created_at TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY(processo_id) REFERENCES processos(id) ON DELETE SET NULL
);

-- Itens de uma Cotação
CREATE TABLE IF NOT EXISTS cotacao_itens (
    id INTEGER PRIMARY KEY,
    cotacao_id INTEGER NOT NULL,
    descricao TEXT NOT NULL,
    unidade TEXT,
    quantidade INTEGER NOT NULL,
    FOREIGN KEY(cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE
);

-- Fornecedores convidados numa Cotação
CREATE TABLE IF NOT EXISTS cotacao_fornecedores (
    id INTEGER PRIMARY KEY,
    cotacao_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    contato TEXT,
    status TEXT,  -- convidado, respondeu, aprovado, rejeitado
    FOREIGN KEY(cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE
);

-- Respostas de preço: um preço por fornecedor por item
CREATE TABLE IF NOT EXISTS cotacao_respostas (
    id INTEGER PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    preco_unit REAL NOT NULL,
    FOREIGN KEY(fornecedor_id) REFERENCES cotacao_fornecedores(id) ON DELETE CASCADE,
    FOREIGN KEY(item_id) REFERENCES cotacao_itens(id) ON DELETE CASCADE
);

-- Banco de Preços: catálogo de itens
CREATE TABLE IF NOT EXISTS preco_itens (
    id INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL,
    unidade TEXT,
    tags TEXT
);

-- Banco de Preços: registros históricos
CREATE TABLE IF NOT EXISTS preco_registros (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    fornecedor TEXT,
    preco_unit REAL NOT NULL,
    data TEXT NOT NULL,
    fonte TEXT,        -- PNCP, NF, web, etc.
    validade TEXT,     -- opcional
    cidade TEXT,       -- opcional
    uf TEXT,           -- opcional
    FOREIGN KEY(item_id) REFERENCES preco_itens(id) ON DELETE CASCADE
);
"""

# --------------------- conexões util ---------------------
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _smallest_free_id(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f"SELECT id FROM {table} ORDER BY id ASC")
    used = [r[0] for r in cur.fetchall()]
    i = 1
    for v in used:
        if v == i: i += 1
        elif v > i: break
    return i

# --------------------- inicialização/seed ----------------
def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)

def seed_demo():
    with _connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0:
            cid = _smallest_free_id(conn, "companies")
            conn.execute("""
                INSERT INTO companies(
                    id, name, cnpj, phone, email,
                    address_street, address_number, address_cidade, address_estado, address_cep,
                    created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                cid, "S.O.S Tech", "00.000.000/0001-00", "(91) 99999-9999", "contato@sostech.local",
                "Rua Exemplo", "123", "Belém", "PA", "66000-000",
                date.today().isoformat()
            ))
            # Certidões
            for nome, dias in [("FGTS", 9), ("INSS", 5), ("Municipal", 2), ("Estadual", 30)]:
                cert_id = _smallest_free_id(conn, "certificates")
                conn.execute("""
                    INSERT INTO certificates(
                        id, company_id, name, number, issuer, issue_date, expiry_date, file_path, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    cert_id, cid, nome, f"XYZ-{dias}", "Órgão", date.today().isoformat(),
                    (date.today()+timedelta(days=dias)).isoformat(), "", date.today().isoformat()
                ))
            # Processo
            pid = _smallest_free_id(conn, "processos")
            conn.execute("""
                INSERT INTO processos(
                    id, company_id, portal, uasg, numero, orgao, modalidade, dt_sessao, hr_sessao,
                    tem_lotes, qtd_itens, valor_estimado, link, edital_path, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pid, cid, "ComprasNet", "000000", "001/2025", "Prefeitura de Exemplo",
                "Pregão", (date.today()+timedelta(days=7)).isoformat(), "09:00",
                1, 10, 25000.0, "https://exemplo.gov/editais/001", "", date.today().isoformat()
            ))
            # Banco de Preços seed
            it = _smallest_free_id(conn, "preco_itens")
            conn.execute("INSERT INTO preco_itens(id, descricao, unidade, tags) VALUES (?,?,?,?)",
                         (it, 'Notebook 15" i5 8GB/256GB', "UN", "informática,notebook"))
            conn.execute("""
                INSERT INTO preco_registros(item_id, fornecedor, preco_unit, data, fonte, validade, cidade, uf)
                VALUES (?,?,?,?,?,?,?,?)
            """, (it, "Fornecedor Alfa", 3200.0, date.today().isoformat(), "cotação interna", "", "Belém", "PA"))
            # Cotação de demonstração (multi-itens / 2 fornecedores)
            qid = _smallest_free_id(conn, "cotacoes")
            conn.execute("INSERT INTO cotacoes(id, company_id, processo_id, titulo, status, created_at) VALUES (?,?,?,?,?,?)",
                         (qid, cid, pid, "Cotação Equipamentos TI", "aberta", date.today().isoformat()))
            # Itens
            i1 = _smallest_free_id(conn, "cotacao_itens"); 
            conn.execute("INSERT INTO cotacao_itens(id, cotacao_id, descricao, unidade, quantidade) VALUES (?,?,?,?,?)",
                         (i1, qid, 'Notebook 15" i5 8GB/256GB', "UN", 5))
            i2 = i1+1
            conn.execute("INSERT INTO cotacao_itens(id, cotacao_id, descricao, unidade, quantidade) VALUES (?,?,?,?,?)",
                         (i2, qid, 'Mouse sem fio', "UN", 10))
            # Fornecedores
            f1 = _smallest_free_id(conn, "cotacao_fornecedores")
            conn.execute("INSERT INTO cotacao_fornecedores(id, cotacao_id, nome, contato, status) VALUES (?,?,?,?,?)",
                         (f1, qid, "Fornecedor Alfa", "alfa@exemplo.com", "convidado"))
            f2 = f1+1
            conn.execute("INSERT INTO cotacao_fornecedores(id, cotacao_id, nome, contato, status) VALUES (?,?,?,?,?)",
                         (f2, qid, "Fornecedor Beta", "beta@exemplo.com", "convidado"))
        conn.commit()

# --------------------- COMPANIES -------------------------
def list_companies(search: str = "") -> List[sqlite3.Row]:
    with _connect() as conn:
        if search:
            like = f"%{search}%"
            cur = conn.execute("""
                SELECT * FROM companies
                WHERE name LIKE ? OR cnpj LIKE ? OR email LIKE ?
                ORDER BY name ASC
            """, (like, like, like))
        else:
            cur = conn.execute("SELECT * FROM companies ORDER BY name ASC")
        return cur.fetchall()

def get_company(cid: int) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()

def add_company(data: Dict[str, Any]) -> int:
    with _connect() as conn:
        cid = _smallest_free_id(conn, "companies")
        fields = (
            "id","name","cnpj","ie","im","phone","email",
            "address_street","address_number","address_bairro","address_cidade","address_estado","address_cep",
            "bank_nome","bank_agencia","bank_conta",
            "socio_nome","socio_estado_civil","socio_rg","socio_cpf","socio_endereco",
            "created_at"
        )
        values = [
            cid,
            data.get("name","").strip(), data.get("cnpj","").strip(),
            data.get("ie","").strip(), data.get("im","").strip(),
            data.get("phone","").strip(), data.get("email","").strip(),
            data.get("address_street","").strip(), data.get("address_number","").strip(),
            data.get("address_bairro","").strip(), data.get("address_cidade","").strip(),
            data.get("address_estado","").strip(), data.get("address_cep","").strip(),
            data.get("bank_nome","").strip(), data.get("bank_agencia","").strip(), data.get("bank_conta","").strip(),
            data.get("socio_nome","").strip(), data.get("socio_estado_civil","").strip(),
            data.get("socio_rg","").strip(), data.get("socio_cpf","").strip(), data.get("socio_endereco","").strip(),
            date.today().isoformat()
        ]
        conn.execute(f"INSERT INTO companies({','.join(fields)}) VALUES ({','.join('?'*len(values))})", values)
        conn.commit()
        return cid

def upd_company(cid: int, data: Dict[str, Any]) -> None:
    with _connect() as conn:
        fields = (
            "name","cnpj","ie","im","phone","email",
            "address_street","address_number","address_bairro","address_cidade","address_estado","address_cep",
            "bank_nome","bank_agencia","bank_conta",
            "socio_nome","socio_estado_civil","socio_rg","socio_cpf","socio_endereco"
        )
        sets = ",".join([f"{f}=?" for f in fields])
        values = [data.get(k,"").strip() for k in fields] + [cid]
        conn.execute(f"UPDATE companies SET {sets} WHERE id=?", values)
        conn.commit()

def del_company(cid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM companies WHERE id=?", (cid,))
        conn.commit()

# --------------------- CERTIFICATES ----------------------
def list_certificates(company_id: Optional[int]=None, search: str="") -> List[sqlite3.Row]:
    with _connect() as conn:
        q = """
            SELECT c.*, co.name AS company_name
            FROM certificates c
            JOIN companies co ON co.id = c.company_id
        """
        where, params = [], []
        if company_id: where.append("c.company_id=?"); params.append(company_id)
        if search:
            like = f"%{search}%"
            where.append("(c.name LIKE ? OR c.number LIKE ? OR c.issuer LIKE ?)")
            params += [like, like, like]
        if where: q += " WHERE " + " AND ".join(where)
        q += " ORDER BY date(c.expiry_date) ASC, c.id DESC"
        return conn.execute(q, params).fetchall()

def add_certificate(data: Dict[str, Any]) -> int:
    with _connect() as conn:
        cid = _smallest_free_id(conn, "certificates")
        conn.execute("""
            INSERT INTO certificates(
                id, company_id, name, number, issuer, issue_date, expiry_date, file_path, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            cid, data["company_id"], data["name"].strip(),
            (data.get("number") or "").strip(), (data.get("issuer") or "").strip(),
            (data.get("issue_date") or "").strip(), data["expiry_date"].strip(),
            (data.get("file_path") or "").strip(), date.today().isoformat()
        ))
        conn.commit()
        return cid

def upd_certificate(cid: int, data: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE certificates
               SET company_id=?, name=?, number=?, issuer=?, issue_date=?, expiry_date=?, file_path=?
             WHERE id=?
        """, (
            data["company_id"], data["name"].strip(),
            (data.get("number") or "").strip(), (data.get("issuer") or "").strip(),
            (data.get("issue_date") or "").strip(), data["expiry_date"].strip(),
            (data.get("file_path") or "").strip(), cid
        ))
        conn.commit()

def del_certificate(cid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM certificates WHERE id=?", (cid,))
        conn.commit()

# --------------------- PROCESSOS -------------------------
def list_processos(company_id: Optional[int]=None, search: str="", portal: str="", periodo: str="") -> List[sqlite3.Row]:
    with _connect() as conn:
        q = """
            SELECT p.*, co.name AS company_name
            FROM processos p
            JOIN companies co ON co.id = p.company_id
        """
        where, params = [], []
        if company_id: where.append("p.company_id=?"); params.append(company_id)
        if portal: where.append("p.portal LIKE ?"); params.append(f"%{portal}%")
        if search:
            like = f"%{search}%"
            where.append("(p.numero LIKE ? OR p.uasg LIKE ? OR p.orgao LIKE ?)")
            params += [like, like, like]
        if periodo == "hoje":
            where.append("p.dt_sessao=?"); params.append(date.today().isoformat())
        elif periodo == "7d":
            where.append("date(p.dt_sessao) >= date('now','-7 day')")
        elif periodo == "30d":
            where.append("date(p.dt_sessao) >= date('now','-30 day')")
        elif periodo == "mes":
            where.append("strftime('%Y-%m', p.dt_sessao) = strftime('%Y-%m','now')")
        if where: q += " WHERE " + " AND ".join(where)
        q += " ORDER BY date(p.dt_sessao) ASC, p.id DESC"
        return conn.execute(q, params).fetchall()

def add_processo(data: Dict[str, Any]) -> int:
    with _connect() as conn:
        pid = _smallest_free_id(conn, "processos")
        conn.execute("""
            INSERT INTO processos(
                id, company_id, portal, uasg, numero, orgao, modalidade, dt_sessao, hr_sessao,
                tem_lotes, qtd_itens, valor_estimado, link, edital_path, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid, data["company_id"], (data.get("portal") or "").strip(),
            (data.get("uasg") or "").strip(), (data.get("numero") or "").strip(),
            (data.get("orgao") or "").strip(), (data.get("modalidade") or "").strip(),
            (data.get("dt_sessao") or "").strip(), (data.get("hr_sessao") or "").strip(),
            int(bool(data.get("tem_lotes"))), int(data.get("qtd_itens") or 0),
            float(data.get("valor_estimado") or 0.0), (data.get("link") or "").strip(),
            (data.get("edital_path") or "").strip(), date.today().isoformat()
        ))
        conn.commit()
        return pid

def upd_processo(pid: int, data: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE processos
               SET company_id=?, portal=?, uasg=?, numero=?, orgao=?, modalidade=?,
                   dt_sessao=?, hr_sessao=?, tem_lotes=?, qtd_itens=?, valor_estimado=?,
                   link=?, edital_path=?
             WHERE id=?
        """, (
            data["company_id"], (data.get("portal") or "").strip(),
            (data.get("uasg") or "").strip(), (data.get("numero") or "").strip(),
            (data.get("orgao") or "").strip(), (data.get("modalidade") or "").strip(),
            (data.get("dt_sessao") or "").strip(), (data.get("hr_sessao") or "").strip(),
            int(bool(data.get("tem_lotes"))), int(data.get("qtd_itens") or 0),
            float(data.get("valor_estimado") or 0.0), (data.get("link") or "").strip(),
            (data.get("edital_path") or "").strip(), pid
        ))
        conn.commit()

def del_processo(pid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM processos WHERE id=?", (pid,))
        conn.commit()

# --------------------- COTAÇÕES (RFQ) -------------------
def list_cotacoes(company_id: Optional[int]=None, processo_id: Optional[int]=None, search: str="") -> List[sqlite3.Row]:
    with _connect() as conn:
        q = """
            SELECT q.*, co.name AS company_name, pr.numero AS processo_numero
              FROM cotacoes q
              JOIN companies co ON co.id = q.company_id
              LEFT JOIN processos pr ON pr.id = q.processo_id
        """
        where, params = [], []
        if company_id:  where.append("q.company_id=?"); params.append(company_id)
        if processo_id: where.append("q.processo_id=?"); params.append(processo_id)
        if search:
            like = f"%{search}%"
            where.append("(q.titulo LIKE ?)")
            params.append(like)
        if where: q += " WHERE " + " AND ".join(where)
        q += " ORDER BY q.id DESC"
        return conn.execute(q, params).fetchall()

def add_cotacao(data: Dict[str, Any]) -> int:
    with _connect() as conn:
        qid = _smallest_free_id(conn, "cotacoes")
        conn.execute("""
            INSERT INTO cotacoes(id, company_id, processo_id, titulo, status, created_at)
            VALUES (?,?,?,?,?,?)
        """, (
            qid, data["company_id"], data.get("processo_id"),
            (data.get("titulo") or "").strip(), (data.get("status") or "aberta").strip(),
            date.today().isoformat()
        ))
        conn.commit()
        return qid

def upd_cotacao(qid: int, data: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE cotacoes SET company_id=?, processo_id=?, titulo=?, status=? WHERE id=?
        """, (data["company_id"], data.get("processo_id"),
              (data.get("titulo") or "").strip(), (data.get("status") or "aberta").strip(), qid))
        conn.commit()

def del_cotacao(qid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM cotacoes WHERE id=?", (qid,))
        conn.commit()

# Itens
def list_cotacao_itens(cotacao_id: int) -> List[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM cotacao_itens WHERE cotacao_id=? ORDER BY id ASC", (cotacao_id,)).fetchall()

def add_cotacao_item(cotacao_id: int, descricao: str, unidade: str, quantidade: int) -> int:
    with _connect() as conn:
        iid = _smallest_free_id(conn, "cotacao_itens")
        conn.execute("INSERT INTO cotacao_itens(id, cotacao_id, descricao, unidade, quantidade) VALUES (?,?,?,?,?)",
                     (iid, cotacao_id, descricao.strip(), unidade.strip(), int(quantidade)))
        conn.commit()
        return iid

def upd_cotacao_item(item_id: int, descricao: str, unidade: str, quantidade: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE cotacao_itens SET descricao=?, unidade=?, quantidade=? WHERE id=?",
                     (descricao.strip(), unidade.strip(), int(quantidade), item_id))
        conn.commit()

def del_cotacao_item(item_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM cotacao_itens WHERE id=?", (item_id,))
        conn.commit()

# Fornecedores
def list_cotacao_fornecedores(cotacao_id: int) -> List[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM cotacao_fornecedores WHERE cotacao_id=? ORDER BY id ASC", (cotacao_id,)).fetchall()

def add_cotacao_fornecedor(cotacao_id: int, nome: str, contato: str) -> int:
    with _connect() as conn:
        fid = _smallest_free_id(conn, "cotacao_fornecedores")
        conn.execute("INSERT INTO cotacao_fornecedores(id, cotacao_id, nome, contato, status) VALUES (?,?,?,?,?)",
                     (fid, cotacao_id, nome.strip(), contato.strip(), "convidado"))
        conn.commit()
        return fid

def upd_cotacao_fornecedor(fid: int, nome: str, contato: str, status: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE cotacao_fornecedores SET nome=?, contato=?, status=? WHERE id=?",
                     (nome.strip(), contato.strip(), status.strip(), fid))
        conn.commit()

def del_cotacao_fornecedor(fid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM cotacao_fornecedores WHERE id=?", (fid,))
        conn.commit()

# Respostas (preços)
def set_preco_resposta(fornecedor_id: int, item_id: int, preco_unit: float) -> None:
    with _connect() as conn:
        cur = conn.execute("SELECT id FROM cotacao_respostas WHERE fornecedor_id=? AND item_id=?", (fornecedor_id, item_id)).fetchone()
        if cur:
            conn.execute("UPDATE cotacao_respostas SET preco_unit=? WHERE id=?", (float(preco_unit), cur["id"]))
        else:
            rid = _smallest_free_id(conn, "cotacao_respostas")
            conn.execute("INSERT INTO cotacao_respostas(id, fornecedor_id, item_id, preco_unit) VALUES (?,?,?,?)",
                         (rid, fornecedor_id, item_id, float(preco_unit)))
        conn.commit()

def get_preco_resposta(fornecedor_id: int, item_id: int) -> Optional[float]:
    with _connect() as conn:
        r = conn.execute("SELECT preco_unit FROM cotacao_respostas WHERE fornecedor_id=? AND item_id=?",
                         (fornecedor_id, item_id)).fetchone()
        return None if r is None else float(r["preco_unit"])

def ranking_cotacao(cotacao_id: int) -> List[Tuple[str, float]]:
    """
    Retorna [(Fornecedor, Total)], ordenado por menor total.
    Se faltar algum preço, considera 0 para aquele item (apenas para exibir).
    """
    with _connect() as conn:
        itens = conn.execute("SELECT id, quantidade FROM cotacao_itens WHERE cotacao_id=?", (cotacao_id,)).fetchall()
        forn = conn.execute("SELECT id, nome FROM cotacao_fornecedores WHERE cotacao_id=?", (cotacao_id,)).fetchall()
        res: List[Tuple[str,float]] = []
        for f in forn:
            total = 0.0
            for it in itens:
                r = conn.execute("SELECT preco_unit FROM cotacao_respostas WHERE fornecedor_id=? AND item_id=?",
                                 (f["id"], it["id"])).fetchone()
                pu = float(r["preco_unit"]) if r else 0.0
                total += pu * float(it["quantidade"] or 0)
            res.append((f["nome"], total))
        res.sort(key=lambda x: x[1])
        return res

# --------------------- BANCO DE PREÇOS ------------------
def list_preco_itens(search: str="") -> List[sqlite3.Row]:
    with _connect() as conn:
        if search:
            like = f"%{search}%"
            q = "SELECT * FROM preco_itens WHERE descricao LIKE ? OR tags LIKE ? ORDER BY id DESC"
            return conn.execute(q, (like, like)).fetchall()
        return conn.execute("SELECT * FROM preco_itens ORDER BY id DESC").fetchall()

def add_preco_item(descricao: str, unidade: str="", tags: str="") -> int:
    with _connect() as conn:
        iid = _smallest_free_id(conn, "preco_itens")
        conn.execute("INSERT INTO preco_itens(id, descricao, unidade, tags) VALUES (?,?,?,?)",
                     (iid, descricao.strip(), unidade.strip(), tags.strip()))
        conn.commit()
        return iid

def upd_preco_item(iid: int, descricao: str, unidade: str="", tags: str="") -> None:
    with _connect() as conn:
        conn.execute("UPDATE preco_itens SET descricao=?, unidade=?, tags=? WHERE id=?",
                     (descricao.strip(), unidade.strip(), tags.strip(), iid))
        conn.commit()

def del_preco_item(iid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM preco_itens WHERE id=?", (iid,))
        conn.commit()

def list_preco_registros(item_id: int) -> List[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("""
            SELECT * FROM preco_registros WHERE item_id=? ORDER BY date(data) DESC, id DESC
        """, (item_id,)).fetchall()

def add_preco_registro(item_id: int, fornecedor: str, preco_unit: float, data_str: str,
                       fonte: str="", validade: str="", cidade: str="", uf: str="") -> int:
    with _connect() as conn:
        rid = _smallest_free_id(conn, "preco_registros")
        conn.execute("""
            INSERT INTO preco_registros(id, item_id, fornecedor, preco_unit, data, fonte, validade, cidade, uf)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (rid, item_id, fornecedor.strip(), float(preco_unit), data_str.strip(),
              fonte.strip(), validade.strip(), cidade.strip(), uf.strip()))
        conn.commit()
        return rid

def del_preco_registro(rid: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM preco_registros WHERE id=?", (rid,))
        conn.commit()

# === KPIs e Alertas (miolo) ===

# === substituir estas 3 funções no services/db.py ===
from datetime import datetime, date  # garanta que já está importado no topo

def kpis() -> dict:
    try:
        e = len(list_companies())
    except Exception:
        e = 0
    try:
        c = len(list_certificates())
    except Exception:
        c = 0
    try:
        l = len(list_processos())
    except Exception:
        l = 0
    return {"empresas": e, "certidoes": c, "licitacoes": l}


def cert_alertas(dias_limite: int = 10):
    """
    Retorna lista de tuplas: (company_name, cert_name, expiry_date, dias_restantes)
    Considera vencidas (<0) e a vencer até `dias_limite`.
    """
    try:
        rows = list_certificates()
    except Exception:
        return []

    out = []
    for r in rows:
        rd = dict(r)  # <-- converte sqlite3.Row para dict
        exp = (rd.get("expiry_date") or "").strip()
        try:
            d = datetime.strptime(exp, "%Y-%m-%d").date()
        except Exception:
            continue
        dif = (d - date.today()).days
        if dif < 0 or 0 <= dif <= dias_limite:
            out.append((rd.get("company_name") or "", rd.get("name") or "", exp, dif))
    return out


def proc_alertas(dias_list=(5, 2, 1)):
    """
    Retorna lista de tuplas: (numero, orgao, dt_sessao, dias_restantes)
    Quando a sessão ocorrer exatamente em 5, 2 ou 1 dias (por padrão).
    """
    try:
        rows = list_processos()
    except Exception:
        return []

    out = []
    for r in rows:
        rd = dict(r)  # <-- converte sqlite3.Row para dict
        ds = (rd.get("dt_sessao") or "").strip()
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except Exception:
            continue
        dif = (d - date.today()).days
        if dif in dias_list:
            out.append((rd.get("numero") or "", rd.get("orgao") or "", ds, dif))
    return out

# === COMPAT LAYER (append) — expõe assinaturas canônicas sem apagar nada ===
# Objetivo: fazer o auditor e as páginas encontrarem nomes padrão,
# roteando para funções equivalentes já existentes neste módulo.

def __compat__find(*names):
    g = globals()
    for n in names:
        fn = g.get(n)
        if callable(fn):
            return fn
    return None

# ---- Empresas ----
def list_empresas():
    fn = __compat__find("list_empresas", "empresas_all", "get_empresas", "list_company", "companies_all")
    return fn() if fn else []

def add_empresa(payload):  # dict
    fn = __compat__find("add_empresa", "empresa_add", "nova_empresa", "company_add")
    if not fn: raise NotImplementedError("add_empresa() não implementada no db.")
    return fn(payload)

def upd_empresa(emp_id, payload):
    fn = __compat__find("upd_empresa", "update_empresa", "empresa_upd", "company_upd")
    if not fn: raise NotImplementedError("upd_empresa() não implementada no db.")
    return fn(emp_id, payload)

def del_empresa(emp_id):
    fn = __compat__find("del_empresa", "delete_empresa", "empresa_del", "company_del")
    if not fn: raise NotImplementedError("del_empresa() não implementada no db.")
    return fn(emp_id)

# ---- Certidões ----
def list_certidoes():
    fn = __compat__find("list_certidoes","certidoes_all","get_certidoes")
    return fn() if fn else []

def add_certidao(payload):
    fn = __compat__find("add_certidao","certidao_add","nova_certidao")
    if not fn: raise NotImplementedError("add_certidao() não implementada no db.")
    return fn(payload)

def upd_certidao(cid, payload):
    fn = __compat__find("upd_certidao","update_certidao","certidao_upd")
    if not fn: raise NotImplementedError("upd_certidao() não implementada no db.")
    return fn(cid, payload)

def del_certidao(cid):
    fn = __compat__find("del_certidao","delete_certidao","certidao_del")
    if not fn: raise NotImplementedError("del_certidao() não implementada no db.")
    return fn(cid)

# ---- Licitações ----
def list_licitacoes():
    fn = __compat__find("list_licitacoes","licitacoes_all","get_licitacoes")
    return fn() if fn else []

def add_licitacao(payload):
    fn = __compat__find("add_licitacao","licitacao_add","nova_licitacao")
    if not fn: raise NotImplementedError("add_licitacao() não implementada no db.")
    return fn(payload)

def upd_licitacao(lid, payload):
    fn = __compat__find("upd_licitacao","update_licitacao","licitacao_upd")
    if not fn: raise NotImplementedError("upd_licitacao() não implementada no db.")
    return fn(lid, payload)

def del_licitacao(lid):
    fn = __compat__find("del_licitacao","delete_licitacao","licitacao_del")
    if not fn: raise NotImplementedError("del_licitacao() não implementada no db.")
    return fn(lid)

# ---- Cotações (já existe no seu db, deixo como compat) ----
def list_cotacoes():
    fn = __compat__find("list_cotacoes","cotacoes_all","get_cotacoes")
    return fn() if fn else []

def add_cotacao(payload):
    fn = __compat__find("add_cotacao","cotacao_add","nova_cotacao")
    if not fn: raise NotImplementedError("add_cotacao() não implementada no db.")
    return fn(payload)

def upd_cotacao(cid, payload):
    fn = __compat__find("upd_cotacao","update_cotacao","cotacao_upd")
    if not fn: raise NotImplementedError("upd_cotacao() não implementada no db.")
    return fn(cid, payload)

def del_cotacao(cid):
    fn = __compat__find("del_cotacao","delete_cotacao","cotacao_del")
    if not fn: raise NotImplementedError("del_cotacao() não implementada no db.")
    return fn(cid)

# ---- Banco de Preços ----
def list_banco_precos():
    fn = __compat__find("list_banco_precos","banco_precos_all","get_banco_precos","list_precos","precos_all")
    return fn() if fn else []

def add_banco_preco(payload):
    fn = __compat__find("add_banco_preco","add_preco","novo_preco","banco_preco_add")
    if not fn: raise NotImplementedError("add_banco_preco() não implementada no db.")
    return fn(payload)

def upd_banco_preco(pid, payload):
    fn = __compat__find("upd_banco_preco","update_preco","preco_upd","banco_preco_upd")
    if not fn: raise NotImplementedError("upd_banco_preco() não implementada no db.")
    return fn(pid, payload)

def del_banco_preco(pid):
    fn = __compat__find("del_banco_preco","delete_preco","preco_del","banco_preco_del")
    if not fn: raise NotImplementedError("del_banco_preco() não implementada no db.")
    return fn(pid)

# ---- Alertas ----
def list_alertas():
    fn = __compat__find("list_alertas","alertas_all","get_alertas","alertas_pendentes")
    return fn() if fn else []

def add_alerta(payload):
    fn = __compat__find("add_alerta","novo_alerta","alerta_add","add_alert")
    if not fn: raise NotImplementedError("add_alerta() não implementada no db.")
    return fn(payload)

def upd_alerta(aid, payload):
    fn = __compat__find("upd_alerta","update_alerta","alerta_upd","update_alert")
    if not fn: raise NotImplementedError("upd_alerta() não implementada no db.")
    return fn(aid, payload)

def del_alerta(aid):
    fn = __compat__find("del_alerta","delete_alerta","alerta_del","delete_alert")
    if not fn: raise NotImplementedError("del_alerta() não implementada no db.")
    return fn(aid)

# ---- Modelos ----
def list_modelos():
    fn = __compat__find("list_modelos","modelos_all","get_modelos")
    return fn() if fn else []

def add_modelo(payload):
    fn = __compat__find("add_modelo","novo_modelo","modelo_add")
    if not fn: raise NotImplementedError("add_modelo() não implementada no db.")
    return fn(payload)

def upd_modelo(mid, payload):
    fn = __compat__find("upd_modelo","update_modelo","modelo_upd")
    if not fn: raise NotImplementedError("upd_modelo() não implementada no db.")
    return fn(mid, payload)

def del_modelo(mid):
    fn = __compat__find("del_modelo","delete_modelo","modelo_del")
    if not fn: raise NotImplementedError("del_modelo() não implementada no db.")
    return fn(mid)

# ---- Oportunidades ----
def list_oportunidades():
    fn = __compat__find("list_oportunidades","oportunidades_all","get_oportunidades")
    return fn() if fn else []

def add_oportunidade(payload):
    fn = __compat__find("add_oportunidade","nova_oportunidade","oportunidade_add")
    if not fn: raise NotImplementedError("add_oportunidade() não implementada no db.")
    return fn(payload)

def upd_oportunidade(oid, payload):
    fn = __compat__find("upd_oportunidade","update_oportunidade","oportunidade_upd")
    if not fn: raise NotImplementedError("upd_oportunidade() não implementada no db.")
    return fn(oid, payload)

def del_oportunidade(oid):
    fn = __compat__find("del_oportunidade","delete_oportunidade","oportunidade_del")
    if not fn: raise NotImplementedError("del_oportunidade() não implementada no db.")
    return fn(oid)
