# === components/masks.py ===
import re
from datetime import datetime

_re_digits = re.compile(r"\D+")

def only_digits(s: str) -> str:
    return _re_digits.sub("", s or "")

def mask_cnpj(s: str) -> str:
    d = only_digits(s)[:14]
    if len(d) <= 2:  return d
    if len(d) <= 5:  return f"{d[:2]}.{d[2:]}"
    if len(d) <= 8:  return f"{d[:2]}.{d[2:5]}.{d[5:]}"
    if len(d) <= 12: return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:]}"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"

def mask_cpf(s: str) -> str:
    d = only_digits(s)[:11]
    if len(d) <= 3:  return d
    if len(d) <= 6:  return f"{d[:3]}.{d[3:]}"
    if len(d) <= 9:  return f"{d[:3]}.{d[3:6]}.{d[6:]}"
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"

def mask_ie(s: str) -> str:
    d = only_digits(s)[:7]
    if len(d) <= 3: return d
    if len(d) <= 6: return f"{d[:3]}.{d[3:]}"
    return f"{d[:3]}.{d[3:6]}-{d[6]}"

def mask_im(s: str) -> str:
    d = only_digits(s)[:9]
    if len(d) <= 2: return d
    if len(d) <= 5: return f"{d[:2]}.{d[2:]}"
    if len(d) <= 8: return f"{d[:2]}.{d[2:5]}.{d[5:]}"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}-{d[8]}"

def mask_phone(s: str) -> str:
    d = only_digits(s)[:11]
    if len(d) <= 2:  return f"({d}"
    if len(d) <= 7:  return f"({d[:2]}) {d[2:]}"
    return f"({d[:2]}) {d[2:7]}-{d[7:11]}"

def mask_cep(s: str) -> str:
    d = only_digits(s)[:8]
    if len(d) <= 5: return d
    return f"{d[:5]}-{d[5:8]}"

def mask_agencia(s: str) -> str:
    d = only_digits(s)[:5]
    if len(d) <= 4: return d
    return f"{d[:4]}-{d[4]}"

def mask_conta(s: str) -> str:
    d = only_digits(s)[:7]
    if len(d) <= 6: return d
    return f"{d[:6]}-{d[6]}"

def mask_uf(s: str) -> str:
    s = (s or "").upper()[:2]
    return s

def mask_date(s: str) -> str:
    d = only_digits(s)[:8]
    if len(d) <= 2: return d
    if len(d) <= 4: return f"{d[:2]}/{d[2:]}"
    return f"{d[:2]}/{d[2:4]}/{d[4:8]}"

def mask_time(s: str) -> str:
    d = only_digits(s)[:4]
    if len(d) <= 2: return d
    return f"{d[:2]}:{d[2:4]}"

def parse_date(s: str):
    s = (s or "").strip()
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except Exception:
        return None

def parse_money(s: str) -> float:
    s = (s or "").strip()
    s = s.replace("R$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def fmt_money_brl(v: float) -> str:
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"
