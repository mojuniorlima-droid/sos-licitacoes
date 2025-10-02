# services/credentials.py — CRUD de credenciais por portal
from __future__ import annotations
import sqlite3
from typing import Optional, List
from .storage import DB_PATH

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def list_company_credentials(company_id: int) -> List[sqlite3.Row]:
    with _connect() as conn:
        cur = conn.execute("""
            SELECT * FROM company_credentials
            WHERE company_id=?
            ORDER BY LOWER(portal) ASC, id ASC
        """, (company_id,))
        return cur.fetchall()

def upsert_company_credential(company_id: int, portal: str, payload: dict) -> int:
    login = (payload.get("login") or "").strip()
    senha = (payload.get("senha") or "").strip()
    url   = (payload.get("url")   or "").strip()
    obs   = (payload.get("obs")   or "").strip()
    with _connect() as conn:
        row = conn.execute("""
            SELECT id FROM company_credentials WHERE company_id=? AND portal=?
        """, (company_id, portal)).fetchone()
        if row:
            conn.execute("""
                UPDATE company_credentials
                SET login=?, senha=?, url=?, obs=?
                WHERE id=?
            """, (login, senha, url, obs, row["id"]))
            conn.commit()
            return row["id"]
        cur = conn.execute("""
            INSERT INTO company_credentials(company_id, portal, login, senha, url, obs)
            VALUES (?,?,?,?,?,?)
        """, (company_id, portal, login, senha, url, obs))
        conn.commit()
        return cur.lastrowid

def delete_company_credential(cred_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM company_credentials WHERE id=?", (cred_id,))
        conn.commit()
