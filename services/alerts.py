from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import re

# Janelas "alerta"
LIC_LEVE = 7
LIC_MOD  = 3
LIC_URG  = 1

CER_LEVE = 15
CER_MOD  = 7
CER_URG  = 1

# --------------------- Parsers ---------------------
def _to_date(v) -> Optional[date]:
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()

    s = str(v).strip()
    if not s:
        return None

    cand = [
        "%Y-%m-%d", "%Y/%m/%d",
        "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
    ]
    for fmt in cand:
        try:
            return datetime.strptime(s.replace("Z","").strip(), fmt).date()
        except Exception:
            pass

    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            return date(y, mo, d)
        except Exception:
            return None
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        d, mo, y = map(int, m.groups())
        try:
            return date(y, mo, d)
        except Exception:
            return None
    return None

def _dias_restantes(d: Optional[date]) -> Optional[int]:
    if not d:
        return None
    return (d - date.today()).days

def _pick(*names):
    import services.db as db  # type: ignore
    for n in names:
        if hasattr(db, n):
            return getattr(db, n)
    return None

def _as_dict(row: Any) -> Dict[str, Any]:
    try:
        if isinstance(row, dict):
            return row
        return {k: row[k] for k in row.keys()}
    except Exception:
        try:
            return dict(row)
        except Exception:
            return {}

def _is_inactive(it: Dict[str, Any]) -> bool:
    for key in ("status", "ativo", "situacao", "situação"):
        if key in it:
            v = str(it.get(key)).strip().lower()
            if v in {"inativo", "inativa", "cancelado", "cancelada", "desativado", "0", "false", "f", "nao", "não"}:
                return True
    return False

# --------------------- Coletas ---------------------
def _listar_licitacoes() -> List[Dict[str, Any]]:
    f = _pick("list_licitacoes", "licitacoes_all", "get_licitacoes", "listar_licitacoes", "lic_all")
    if f:
        try:
            return [_as_dict(x) for x in (f() or [])]
        except Exception:
            return []
    return []

def _listar_certidoes() -> List[Dict[str, Any]]:
    f = _pick(
        "list_certidoes", "certidoes_all", "get_certidoes", "listar_certidoes",
        "certidoes_para_alerta", "certidoes_vencimentos", "certidoes_list"
    )
    if f:
        try:
            return [_as_dict(x) for x in (f() or [])]
        except Exception:
            return []
    return []

# --------------------- Títulos melhores ---------------------
def _titulo_licitacao(it: Dict[str, Any]) -> str:
    numero = it.get("numero") or it.get("edital") or it.get("processo") or ""
    modalidade = it.get("modalidade") or it.get("tipo") or ""
    orgao = it.get("uasg") or it.get("orgao") or it.get("órgão") or ""
    objeto = it.get("objeto") or it.get("descricao") or it.get("descrição") or ""

    partes = []
    if numero:
        partes.append(f"Nº {numero}")
    if modalidade:
        partes.append(str(modalidade))
    if orgao:
        partes.append(str(orgao))

    cabeca = " — ".join([p for p in partes if p]) or "Licitação"
    if objeto:
        # reduz objeto para não estourar o layout
        txt = str(objeto).strip()
        if len(txt) > 120:
            txt = txt[:117] + "..."
        return f"{cabeca}: {txt}"
    return cabeca

# --------------------- Datas dos itens ---------------------
_CER_DATE_CANDIDATES = [
    "vencimento", "validade", "data_validade", "venc", "venc_em", "validade_em",
    "data_venc", "data_vencimento", "vencimento_em", "expira", "expira_em",
    "expires_at", "expiry", "expiry_date",
]
_LIC_DATE_CANDIDATES = [
    "data_sessao", "sessao", "data_abertura", "abertura", "data_entrega",
    "prazo", "limite", "limite_entrega",
]

def _extract_date_any(it: Dict[str, Any], explicit_candidates: List[str]) -> Optional[date]:
    for c in explicit_candidates:
        if c in it and it.get(c) not in (None, ""):
            d = _to_date(it.get(c))
            if d:
                return d
    for k in it.keys():
        kl = str(k).lower()
        if ("venc" in kl or "valid" in kl) and it.get(k) not in (None, ""):
            d = _to_date(it.get(k))
            if d:
                return d
    # prazo em dias + emissão (certidões)
    try:
        prazo = None
        for pk in ("prazo_dias", "validade_dias", "prazo"):
            if it.get(pk) not in (None, ""):
                prazo = int(str(it.get(pk)))
                break
        if prazo:
            for ek in ("emissao", "data_emissao", "emitido_em"):
                if it.get(ek) not in (None, ""):
                    em = _to_date(it.get(ek))
                    if em:
                        return em + timedelta(days=int(prazo))
    except Exception:
        pass
    return None

# --------------------- Classificação ---------------------
def list_alertas_licitacoes() -> Dict[str, list]:
    itens = _listar_licitacoes()
    out = {"leve": [], "moderado": [], "urgente": []}

    for it in itens:
        if _is_inactive(it):
            continue

        d = _extract_date_any(it, _LIC_DATE_CANDIDATES)
        dias = _dias_restantes(d)
        if dias is None:
            continue

        titulo = _titulo_licitacao(it)

        payload = {"titulo": titulo, "dias": dias}

        if dias <= LIC_URG:
            out["urgente"].append(payload)
        elif dias <= LIC_MOD:
            out["moderado"].append(payload)
        elif dias <= LIC_LEVE:
            out["leve"].append(payload)

    return out

def list_alertas_certidoes() -> Dict[str, list]:
    itens = _listar_certidoes()
    out = {"leve": [], "moderado": [], "urgente": []}

    for it in itens:
        if _is_inactive(it):
            continue

        d = _extract_date_any(it, _CER_DATE_CANDIDATES)
        dias = _dias_restantes(d)
        if dias is None:
            continue

        titulo = it.get("nome") or it.get("tipo") or it.get("descricao") or it.get("id") or "Certidão"
        payload = {"titulo": str(titulo), "dias": dias}

        if dias <= CER_URG:
            out["urgente"].append(payload)
        elif dias <= CER_MOD:
            out["moderado"].append(payload)
        elif dias <= CER_LEVE:
            out["leve"].append(payload)

    return out

def count_all() -> int:
    lic = list_alertas_licitacoes()
    cer = list_alertas_certidoes()
    return sum(len(v) for v in lic.values()) + sum(len(v) for v in cer.values())
