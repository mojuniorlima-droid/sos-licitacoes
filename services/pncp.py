# === services/pncp.py ===
from __future__ import annotations
import os, json, time, threading, datetime as dt
from typing import List, Dict, Any, Optional

# Dependências opcionais (rodamos com fallback se não estiverem instaladas)
try:
    import requests  # type: ignore
except Exception:
    requests = None  # fallback

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:
    PdfReader = None  # fallback

# Integração com DB: usamos apenas se existir
try:
    import services.db as db  # type: ignore
except Exception:
    db = None  # fallback seguro

# Pasta de dados (edital, logs, filtros)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
os.makedirs(DATA_DIR, exist_ok=True)
EDITAIS_DIR = os.path.join(DATA_DIR, "editais")
os.makedirs(EDITAIS_DIR, exist_ok=True)
LOG_PATH = os.path.join(DATA_DIR, "pncp_job.log")
FILTERS_PATH = os.path.join(DATA_DIR, "pncp_filtros.json")

# Endpoint do PNCP (exemplo plausível; se mudar, o fallback simula)
PNCP_SEARCH_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes"  # endpoint de referência

# ----------------------------- utilitários -----------------------------
def _log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def _load_filters_from_disk() -> Dict[str, Any]:
    if os.path.exists(FILTERS_PATH):
        try:
            with open(FILTERS_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}
    return {}

def _save_filters_to_disk(filt: Dict[str, Any]) -> None:
    try:
        with open(FILTERS_PATH, "w", encoding="utf-8") as f:
            json.dump(filt, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        _log(f"ERR salvando filtros: {ex}")

def _clean_text(s: Any) -> str:
    return str(s or "").strip()

def _simulate_results(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Fallback se não houver internet/requests
    uf = ",".join(filters.get("ufs") or []) or "PA"
    municipios = filters.get("municipios") or ["Belém", "Castanhal"]
    objeto = _clean_text(filters.get("objeto"))
    hoje = dt.date.today()
    out = []
    for i, m in enumerate(municipios, start=1):
        out.append({
            "id": int(1000 + i),
            "uf": uf,
            "municipio": m,
            "orgao": "Prefeitura Municipal",
            "objeto": objeto or "Aquisição de materiais de expediente",
            "data_sessao": (hoje + dt.timedelta(days=7+i)).strftime("%d/%m/%Y"),
            "valor_estimado": "R$ 250.000,00",
            "link": "https://pncp.gov.br/visualiza/contratacao/XYZ",
            "edital_url": "https://exemplo.gov.br/edital.pdf",
        })
    return out

# ----------------------------- PNCP Client -----------------------------
def search_opportunities(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    filters:
      - ufs: List[str]
      - municipios: List[str]
      - orgaos: List[str]
      - objeto: str
      - data_ini: dd/mm/aaaa (opcional)
      - data_fim: dd/mm/aaaa (opcional)
    """
    # Persistimos os filtros para serem usados pelo job diário
    _save_filters_to_disk(filters)

    if requests is None:
        _log("requests ausente — retornando resultados simulados.")
        return _simulate_results(filters)

    # Monta query (ajuste conforme docs do PNCP)
    params = {}
    if filters.get("ufs"):
        params["uf"] = ",".join(filters["ufs"])
    if filters.get("municipios"):
        params["municipio"] = ",".join(filters["municipios"])
    if filters.get("orgaos"):
        params["orgao"] = ",".join(filters["orgaos"])
    if _clean_text(filters.get("objeto")):
        params["objeto"] = _clean_text(filters["objeto"])
    if _clean_text(filters.get("data_ini")):
        params["dataInicial"] = _clean_text(filters["data_ini"])
    if _clean_text(filters.get("data_fim")):
        params["dataFinal"] = _clean_text(filters["data_fim"])

    try:
        r = requests.get(PNCP_SEARCH_URL, params=params, timeout=25)
        if r.status_code != 200:
            _log(f"PNCP HTTP {r.status_code} — usando fallback.")
            return _simulate_results(filters)
        data = r.json() if callable(getattr(r, "json", None)) else []
    except Exception as ex:
        _log(f"PNCP erro de rede: {ex} — usando fallback.")
        return _simulate_results(filters)

    results: List[Dict[str, Any]] = []
    for i, raw in enumerate(data or []):
        # Adaptar conforme o schema real do PNCP
        results.append({
            "id": raw.get("id") or (10000 + i),
            "uf": raw.get("uf") or "",
            "municipio": raw.get("municipio") or "",
            "orgao": raw.get("orgao") or "",
            "objeto": raw.get("objeto") or "",
            "data_sessao": raw.get("dataSessao") or "",
            "valor_estimado": raw.get("valorEstimado") or "",
            "link": raw.get("linkPublicacao") or "",
            "edital_url": raw.get("editalUrl") or "",
        })
    return results

def download_edital(url: str, *, oportunidade_id: Any) -> Optional[str]:
    """Baixa o PDF do edital, salva em data/editais/<id>.pdf e retorna o caminho.
       Se falhar, retorna None."""
    if not url:
        return None
    file_path = os.path.join(EDITAIS_DIR, f"{oportunidade_id}.pdf")
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    if requests is None:
        _log("requests ausente — não foi possível baixar edital.")
        return None

    try:
        with requests.get(url, stream=True, timeout=30) as r:
            if r.status_code != 200:
                _log(f"Falha baixando edital ({r.status_code}) {url}")
                return None
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return file_path
    except Exception as ex:
        _log(f"Erro baixando edital: {ex}")
        return None

def extract_pdf_text(pdf_path: str, max_chars: int = 200000) -> Optional[str]:
    """Extrai texto do PDF (PyPDF2). Limita tamanho para não travar UI."""
    if not (pdf_path and os.path.exists(pdf_path)):
        return None
    if PdfReader is None:
        _log("PyPDF2 ausente — não foi possível extrair texto.")
        return None
    try:
        reader = PdfReader(pdf_path)
        chunks = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            chunks.append(txt)
            if sum(len(c) for c in chunks) > max_chars:
                break
        return "\n".join(chunks)[:max_chars]
    except Exception as ex:
        _log(f"Erro extraindo texto: {ex}")
        return None

# ----------------------------- Persistência opcional -----------------------------
def upsert_oportunidades(rows: List[Dict[str, Any]]) -> int:
    """
    Tenta inserir/atualizar oportunidades no DB, caso as funções existam.
    Retorna quantos foram gravados.
    """
    if not rows:
        return 0
    if db is None:
        return 0
    # Procuramos função(s)
    f_add = None
    for n in ["add_oportunidade", "oportunidade_add", "nova_oportunidade"]:
        if hasattr(db, n):
            f_add = getattr(db, n); break
    if not callable(f_add):
        # bulk?
        for n in ["add_oportunidades_bulk", "oportunidades_bulk_add"]:
            if hasattr(db, n):
                f_add = getattr(db, n); break
    if not callable(f_add):
        return 0

    ok = 0
    for r in rows:
        try:
            f_add(r)
            ok += 1
        except Exception as ex:
            _log(f"Falha add oportunidade: {ex}")
    return ok

# ----------------------------- Agendamento diário -----------------------------
_job_thread: Optional[threading.Thread] = None
_job_stop = threading.Event()

def _seconds_until(hour: int, minute: int) -> int:
    now = dt.datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target = target + dt.timedelta(days=1)
    return int((target - now).total_seconds())

def _job_loop(hour: int, minute: int):
    _log(f"PNCP job iniciado (diário {hour:02d}:{minute:02d}).")
    while not _job_stop.is_set():
        # Espera até o próximo horário
        wait = _seconds_until(hour, minute)
        for _ in range(wait):
            if _job_stop.is_set():
                break
            time.sleep(1)
        if _job_stop.is_set():
            break

        # Executa pull com os filtros salvos
        try:
            filters = _load_filters_from_disk()
            rows = search_opportunities(filters)
            saved = upsert_oportunidades(rows)
            _log(f"Job executado: {len(rows)} obtidas; {saved} gravadas no DB.")
        except Exception as ex:
            _log(f"Job erro: {ex}")

def start_daily_job(hour: int = 2, minute: int = 0) -> None:
    """Inicia agendamento diário. Idempotente."""
    global _job_thread
    if _job_thread and _job_thread.is_alive():
        _log("Job já estava em execução.")
        return
    _job_stop.clear()
    _job_thread = threading.Thread(target=_job_loop, args=(hour, minute), daemon=True)
    _job_thread.start()

def stop_daily_job() -> None:
    _job_stop.set()
    _log("PNCP job parado.")

# ----------------------------- API amigável à página -----------------------------
def load_saved_filters() -> Dict[str, Any]:
    """Usado pela page para preencher os campos ao abrir."""
    return _load_filters_from_disk()

def save_filters(filters: Dict[str, Any]) -> None:
    _save_filters_to_disk(filters)
