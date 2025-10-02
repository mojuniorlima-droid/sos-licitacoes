# === components/validators.py ===
import re

_email_rx = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_url_rx   = re.compile(r"^https?://", re.IGNORECASE)

def is_email(s: str) -> bool:
    return bool(_email_rx.match((s or "").strip()))

def is_url(s: str) -> bool:
    return bool(_url_rx.match((s or "").strip()))
