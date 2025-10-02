# services/edital_ia.py
from __future__ import annotations

import os
import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# -------------------------
# .env robusto
# -------------------------
try:
    from dotenv import load_dotenv, find_dotenv
except Exception:
    def load_dotenv(*_, **__):  # fallback inofensivo
        return False
    def find_dotenv(*_, **__):
        return ""

_DOTENV = find_dotenv(usecwd=True)
if not _DOTENV:
    _DOTENV = str(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(_DOTENV, override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = (os.getenv("GPT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()

# -------------------------
# OpenAI (opcional)
# -------------------------
_client = None
_openai_ok = False
try:
    if OPENAI_API_KEY:
        from openai import OpenAI  # openai>=1.x
        _client = OpenAI(api_key=OPENAI_API_KEY)
        _openai_ok = True
except Exception:
    _client = None
    _openai_ok = False

# -------------------------
# Index - onde guardamos
# -------------------------
ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "data" / "edital_index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = INDEX_DIR / "index.json"

# Estrutura do index.json:
# {
#   "docs": [{"name": "arquivo.pdf", "pages": N}],
#   "chunks": [{"doc": 0, "page": 5, "text": "..."}, ...]
# }

# Cache em memória
_MEM = {"docs": [], "chunks": []}
_LAST_SOURCES: List[str] = []


# =============================================================================
# Utilidades de texto
# =============================================================================
_WS = re.compile(r"\s+")

def _norm_txt(s: str) -> str:
    return _WS.sub(" ", s or "").strip()

def _tokenize(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^\wáéíóúàâêôãõçü\-]+", " ", s, flags=re.UNICODE)
    toks = [t for t in s.split() if len(t) > 1]
    return toks

def _split_into_chunks(text: str, target_chars: int = 1400) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    cur = ""
    for p in paras:
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= target_chars:
            cur += "\n" + p
        else:
            chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


# =============================================================================
# Carregar / salvar índice
# =============================================================================
def _load_index() -> None:
    global _MEM
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            _MEM["docs"] = data.get("docs", [])
            _MEM["chunks"] = data.get("chunks", [])
        except Exception:
            _MEM["docs"] = []
            _MEM["chunks"] = []
    else:
        _MEM["docs"] = []
        _MEM["chunks"] = []

def _save_index() -> None:
    data = {"docs": _MEM["docs"], "chunks": _MEM["chunks"]}
    INDEX_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# =============================================================================
# Leitura de PDF
# =============================================================================
def _extract_pdf_texts(path: str) -> List[str]:
    path = str(path)
    pages: List[str] = []

    # pypdf
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(path)
        for i in range(len(reader.pages)):
            try:
                txt = reader.pages[i].extract_text() or ""
            except Exception:
                txt = ""
            pages.append(_norm_txt(txt))
        return pages
    except Exception:
        pass

    # PyPDF2
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(path)
        for i in range(len(reader.pages)):
            try:
                txt = reader.pages[i].extract_text() or ""
            except Exception:
                txt = ""
            pages.append(_norm_txt(txt))
        return pages
    except Exception as ex:
        raise RuntimeError(f"Falha ao ler PDF: {ex}")


# =============================================================================
# API pública: índice
# =============================================================================
def list_indexed_docs() -> List[Dict[str, Any]]:
    _load_index()
    out = []
    for i, d in enumerate(_MEM["docs"]):
        c = sum(1 for ch in _MEM["chunks"] if ch.get("doc") == i)
        out.append({"name": d.get("name", f"doc_{i}"), "chunks": c})
    return out

def clear_index() -> None:
    _MEM["docs"] = []
    _MEM["chunks"] = []
    _save_index()

def index_pdf(path: str) -> Dict[str, Any]:
    _load_index()
    if not path:
        raise ValueError("Caminho do PDF vazio.")
    name = os.path.basename(path)
    pages = _extract_pdf_texts(path)
    total_pages = len(pages)
    if total_pages == 0:
        raise RuntimeError("PDF sem páginas legíveis.")

    doc_id = len(_MEM["docs"])
    _MEM["docs"].append({"name": name, "pages": total_pages})

    added = 0
    for pg, txt in enumerate(pages, start=1):
        if not txt.strip():
            continue
        parts = _split_into_chunks(txt, target_chars=1400)
        for ptxt in parts:
            _MEM["chunks"].append({"doc": doc_id, "page": pg, "text": ptxt})
            added += 1

    _save_index()
    return {"name": name, "chunks": added, "pages": total_pages}


# =============================================================================
# Ranqueador simples (TF-IDF leve)
# =============================================================================
def _idf_map(chunks: List[Dict[str, Any]]) -> Dict[str, float]:
    df = {}
    for ch in chunks:
        seen = set(_tokenize(ch["text"]))
        for t in seen:
            df[t] = df.get(t, 0) + 1
    N = max(1, len(chunks))
    return {t: math.log((N + 1) / (dfi + 0.5)) + 1.0 for t, dfi in df.items()}

def _score(query: str, chunk_text: str, idf: Dict[str, float]) -> float:
    q = _tokenize(query)
    if not q:
        return 0.0
    terms = _tokenize(chunk_text)
    if not terms:
        return 0.0
    tf = {}
    for t in terms:
        tf[t] = tf.get(t, 0) + 1
    denom = len(terms)
    score = 0.0
    for t in set(q):
        if t in tf:
            score += (tf[t] / denom) * idf.get(t, 1.0)
    return score

def _search_chunks(question: str, k: int = 12) -> List[Dict[str, Any]]:
    _load_index()
    chunks = _MEM["chunks"]
    if not chunks:
        return []
    idf = _idf_map(chunks)
    scored = []
    for ch in chunks:
        s = _score(question, ch["text"], idf)
        if s > 0:
            scored.append((s, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ch for _, ch in scored[:k]]


# =============================================================================
# Pré-extração (heurísticas)
# =============================================================================
_DATE = re.compile(r"\b([0-3]?\d/[0-1]?\d/\d{4})\b")
_TIME = re.compile(r"\b([01]?\d|2[0-3])[:hH.]?([0-5]\d)\b")  # 14:00 | 14h00 | 14.00
_LINK = re.compile(r"https?://[^\s)]+", re.IGNORECASE)

_PLAT_KEYS = [
    "comprasnet", "compras gov", "bbmnet", "bnc", "banco do brasil",
    "portal de compras públicas", "pcp", "licitanet", "compras pará",
    "bionexo", "sei", "licitacoes-e", "gov.br"
]

_HAB_KEYS = ["habilita", "habilitac", "documentos", "regularidade", "qualificação", "certidão", "declaração"]

def _pre_extract(context: str) -> Dict[str, Any]:
    """
    Vasculha o contexto e tenta puxar:
    - data/hora de abertura
    - plataforma/local/link
    - validade de proposta
    - prazo de entrega/execução
    - lista de documentos de habilitação
    """
    lines = [ln.strip() for ln in context.splitlines() if ln.strip()]
    joined = " ".join(lines).lower()

    # Datas/horas
    dates = _DATE.findall(context)
    times = ["{}:{}".format(h, m) for h, m in _TIME.findall(context)]

    # Plataforma/local
    plat = None
    for kw in _PLAT_KEYS:
        if kw in joined:
            plat = kw
            break
    links = _LINK.findall(context)

    # Validade de proposta
    validade = None
    for m in re.finditer(r"validade[^.\n]{0,60}?(\d{2,3})\s*dias", joined):
        validade = f"{m.group(1)} dias"
    if not validade:
        for m in re.finditer(r"proposta[^.\n]{0,60}?(\d{2,3})\s*dias", joined):
            validade = f"{m.group(1)} dias"

    # Prazo de entrega/execução
    prazo = None
    for m in re.finditer(r"prazo[^.\n]{0,100}?(\d{1,3})\s*dias", joined):
        prazo = f"{m.group(1)} dias"
    if not prazo:
        for m in re.finditer(r"entrega[^.\n]{0,100}?(\d{1,3})\s*dias", joined):
            prazo = f"{m.group(1)} dias"

    # Documentos de habilitação (pega blocos onde essas palavras aparecem)
    hab_items: List[str] = []
    for i, ln in enumerate(lines):
        lnl = ln.lower()
        if any(k in lnl for k in _HAB_KEYS):
            # pega a linha e vizinhas com bullets/itens
            window = lines[max(0, i-3): i+8]
            for w in window:
                if re.search(r"(^[\-\•\–\·]\s)|(^\(?[a-z]\)|^\(?\d+\))", w.strip(), flags=re.IGNORECASE):
                    hab_items.append(_norm_txt(w))
                elif any(x in w.lower() for x in _HAB_KEYS):
                    hab_items.append(_norm_txt(w))

    # Limpa duplicatas e exageros
    seen = set()
    clean_hab = []
    for it in hab_items:
        if it not in seen and len(it) > 5:
            seen.add(it)
            clean_hab.append(it)

    return {
        "datas": list(dict.fromkeys(dates)),
        "horas": list(dict.fromkeys(times)),
        "plataforma": plat,
        "links": list(dict.fromkeys(links))[:3],
        "validade": validade,
        "prazo": prazo,
        "hab_docs": clean_hab[:20],
    }


# =============================================================================
# LLM (OpenAI) + formatação markdown
# =============================================================================
_SYSTEM = (
    "Você é um assistente especializado em analisar editais de licitação do Brasil. "
    "Responda APENAS com base no CONTEXTO fornecido."
)

_INSTRUCTIONS = (
    "Formate assim (markdown):\n"
    "## Resumo direto\n"
    "- resposta objetiva em 1–2 linhas\n\n"
    "## Detalhes\n"
    "- data e hora (se houver)\n"
    "- plataforma/local (link se disponível)\n"
    "- validade mínima da proposta (se houver)\n"
    "- prazo de entrega/execução (se houver)\n\n"
    "## Documentos de habilitação\n"
    "- lista sintética e organizada (jurídica, fiscal, técnica) – somente se constar\n\n"
    "## Observações\n"
    "- penalidades, impugnação, contato etc. – somente se constar"
)

def _format_context(chs: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    _load_index()
    out = []
    sources = []
    for ch in chs:
        doc_meta = _MEM["docs"][ch["doc"]] if 0 <= ch["doc"] < len(_MEM["docs"]) else {"name": f"doc_{ch['doc']}"}
        name = doc_meta.get("name", f"doc_{ch['doc']}")
        page = ch.get("page", "?")
        txt = _norm_txt(ch.get("text", ""))
        out.append(f"[{name} · pág. {page}] {txt}")
        sources.append(f"{name} · pág. {page}")
    ctx = "\n\n".join(out)
    return ctx, sources

def _llm_answer(question: str, context: str, extracted: Dict[str, Any], model: str) -> str:
    if not (_client and _openai_ok and OPENAI_API_KEY):
        raise RuntimeError("OPENAI indisponível.")

    extra_hints = []
    if extracted.get("datas"):
        extra_hints.append(f"Datas encontradas: {', '.join(extracted['datas'])}.")
    if extracted.get("horas"):
        extra_hints.append(f"Horários encontrados: {', '.join(extracted['horas'])}.")
    if extracted.get("plataforma"):
        extra_hints.append(f"Plataforma provável: {extracted['plataforma']}.")
    if extracted.get("links"):
        extra_hints.append(f"Links possíveis: {', '.join(extracted['links'])}.")
    if extracted.get("validade"):
        extra_hints.append(f"Validade de proposta vista: {extracted['validade']}.")
    if extracted.get("prazo"):
        extra_hints.append(f"Prazo de entrega/execução visto: {extracted['prazo']}.")
    if extracted.get("hab_docs"):
        extra_hints.append("Trechos de habilitação detectados (resuma e organize):\n- " + "\n- ".join(extracted["hab_docs"][:8]))

    user_msg = (
        f"{_INSTRUCTIONS}\n\n"
        f"PERGUNTA:\n{question}\n\n"
        f"PISTAS EXTRAÍDAS:\n" + ("\n".join(extra_hints) if extra_hints else "(nenhuma)") + "\n\n"
        f"CONTEXTO:\n{context}"
    )

    # 1) Responses API
    try:
        resp = _client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_output_tokens=900,
        )
        if hasattr(resp, "output_text"):
            return (resp.output_text or "").strip()
        try:
            return (resp.output[0].content[0].text or "").strip()
        except Exception:
            pass
    except Exception:
        pass

    # 2) Chat Completions
    cc = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )
    return (cc.choices[0].message.content or "").strip()


# =============================================================================
# Fallback local com markdown
# =============================================================================
def _local_answer_md(question: str, ctx: str, extracted: Dict[str, Any]) -> str:
    resumo = "- Não foi possível usar a IA agora; abaixo um resumo aproximado do que foi encontrado no edital."
    det = []
    if extracted.get("datas") or extracted.get("horas"):
        det.append(f"- **Data/Hora:** {' / '.join(extracted.get('datas', [])[:1])} {('às ' + extracted['horas'][0]) if extracted.get('horas') else ''}".strip())
    if extracted.get("plataforma"):
        p = extracted["plataforma"].title()
        det.append(f"- **Plataforma/Local:** {p}")
    if extracted.get("links"):
        det.append(f"- **Links:** {', '.join(extracted['links'])}")
    if extracted.get("validade"):
        det.append(f"- **Validade da proposta:** {extracted['validade']}")
    if extracted.get("prazo"):
        det.append(f"- **Prazo de entrega/execução:** {extracted['prazo']}")

    if not det:
        det = ["- (sem detalhes claros no contexto)"]

    hab = extracted.get("hab_docs") or []
    if hab:
        hab_md = "\n".join(f"- {h}" for h in hab[:12])
    else:
        hab_md = "- (itens não identificados com segurança no contexto)"

    return (
        "## Resumo direto\n"
        f"{resumo}\n\n"
        "## Detalhes\n"
        + "\n".join(det) + "\n\n"
        "## Documentos de habilitação\n"
        + hab_md + "\n"
    )


# =============================================================================
# API pública: perguntas
# =============================================================================
def qa(question: str, use_ai: bool = True) -> Dict[str, Any]:
    global _LAST_SOURCES
    try:
        q = (question or "").strip()
        if not q:
            return {"title": "Resposta", "answer": "Pergunta vazia.", "sources": [], "ok": False}

        chs = _search_chunks(q, k=12)
        ctx, sources = _format_context(chs)
        _LAST_SOURCES = sources[:]  # guarda p/ UI

        if not ctx:
            ans = (
                "Não encontrei trechos relevantes nos documentos indexados para responder.\n\n"
                "Sugestões de pergunta: **Data e hora de abertura?** • **Documentos de habilitação?** • "
                "**Validade mínima da proposta?** • **Prazo de entrega?**"
            )
            return {"title": "Resposta", "answer": ans, "sources": sources, "ok": False}

        extracted = _pre_extract(ctx)

        if use_ai and _openai_ok and OPENAI_API_KEY:
            try:
                text = _llm_answer(q, ctx, extracted, model=DEFAULT_MODEL)
                if not text.strip():
                    text = _local_answer_md(q, ctx, extracted)
                return {"title": "Resposta", "answer": text, "sources": sources, "ok": True}
            except Exception:
                text = _local_answer_md(q, ctx, extracted)
                msg = text + "\n\n> Observação: IA indisponível no momento; usei um resumo local."
                return {"title": "Resposta", "answer": msg, "sources": sources, "ok": False}

        # Sem IA
        text = _local_answer_md(q, ctx, extracted)
        return {"title": "Resposta", "answer": text, "sources": sources, "ok": True}

    except Exception as ex:
        return {
            "title": "Resposta",
            "answer": f"Não consegui responder agora. Detalhe técnico: {ex}",
            "sources": _LAST_SOURCES[:],
            "ok": False,
        }

# aliases esperados
def ask(question: str, use_ai: bool = True) -> Dict[str, Any]:
    return qa(question, use_ai=use_ai)

def query(question: str, use_ai: bool = True) -> Dict[str, Any]:
    return qa(question, use_ai=use_ai)

def last_sources() -> List[str]:
    return _LAST_SOURCES[:]

def diag() -> str:
    ok = bool(OPENAI_API_KEY)
    return f"IA {'ON' if ok else 'OFF'} · Modelo: {DEFAULT_MODEL} · Docs indexados: {len(_MEM.get('docs', []))} · .env: {(_DOTENV or '<nao encontrado>')}"
