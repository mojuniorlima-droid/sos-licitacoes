# services/ingestors.py
"""
Motor de ingestão para Oportunidades:
- Estrutura pronta para sincronizar PNCP e ComprasNet automaticamente 1x/dia
- Botão "Sincronizar agora" chama sync_once()
- Pontos de integração: implemente fetch_from_pncp() / fetch_from_comprasnet()
"""
from __future__ import annotations
import threading
from datetime import datetime
import services.db as db

# ====== adaptadores de DB ======
def _db_funcs():
    f = {}
    for n in ["list_oportunidades", "oportunidades_all", "get_oportunidades", "oportunidades"]:
        if hasattr(db, n):
            f["list"] = getattr(db, n); break
    for n in ["add_oportunidade", "oportunidade_add", "novo_oportunidade", "add_oportunidade"]:
        if hasattr(db, n):
            f["add"] = getattr(db, n); break
    for n in ["upd_oportunidade", "update_oportunidade", "oportunidade_upd"]:
        if hasattr(db, n):
            f["upd"] = getattr(db, n); break
    return f

# ====== coletores (implemente de verdade aqui depois) ======
def fetch_from_pncp() -> list[dict]:
    """
    TODO: Implementar coleta real.
    Por enquanto, exemplo estático para validar o fluxo.
    """
    # Exemplo: retorne registros “normalizados”
    return [
        {
            "empresa": "—",
            "portal": "PNCP",
            "processo": "PNCP-0001/2025",
            "orgao": "Prefeitura ABC",
            "modalidade": "Pregão",
            "data": "30/09/2025",
            "hora": "10:00",
            "valor": "150000,00",
            "link": "https://pncp.gov.br/.../detalhe",
        }
    ]

def fetch_from_comprasnet() -> list[dict]:
    """
    TODO: Implementar coleta real.
    """
    return [
        {
            "empresa": "—",
            "portal": "ComprasNet",
            "processo": "90023/2025",
            "orgao": "IFXYZ",
            "modalidade": "Pregão",
            "data": "25/09/2025",
            "hora": "09:30",
            "valor": "95000,00",
            "link": "https://www.gov.br/compras/...",
        }
    ]

# ====== normalização/merge ======
def _merge(existing: list[dict], incoming: list[dict]) -> tuple[int, list[dict]]:
    """
    Junta incoming com existing:
    - Se processo+portal já existe, atualiza campos.
    - Se não existe, adiciona.
    Retorna (alterados/novos, lista_final).
    """
    by_key = {}
    for r in existing or []:
        key = f"{(r.get('portal') or '').strip()}|{(r.get('processo') or '').strip()}"
        by_key[key] = r

    changed = 0
    out = existing[:] if existing else []

    def _upd(dst, src):
        nonlocal changed
        fields = ["empresa","portal","processo","orgao","modalidade","data","hora","valor","link"]
        dirty=False
        for f in fields:
            sv = (src.get(f) or "").strip()
            dv = (dst.get(f) or "").strip()
            if sv and sv != dv:
                dst[f] = sv; dirty=True
        if dirty: changed += 1

    for s in incoming or []:
        key = f"{(s.get('portal') or '').strip()}|{(s.get('processo') or '').strip()}"
        if key in by_key:
            _upd(by_key[key], s)
        else:
            out.append(s); changed += 1
    return changed, out

# ====== fachada pública ======
class _OportunidadesIngestor:
    def __init__(self):
        self._lock = threading.Lock()
        self._timer = None

    def sync_once(self) -> int:
        """
        Busca de PNCP e ComprasNet, mescla e grava no DB.
        Retorna a quantidade de novos/atualizados.
        """
        funcs = _db_funcs()
        existing = funcs.get("list", lambda: [])()
        # coleta
        new_data = []
        new_data.extend(fetch_from_pncp())
        new_data.extend(fetch_from_comprasnet())
        # merge
        changed, merged = _merge(existing or [], new_data)
        # grava (simples: se tiver update no DB, use; senão, apaga e re-insere)
        if "upd" in funcs or "add" in funcs:
            # escreve cada registro (se existir id equivalente, usa upd; se não, add)
            # chave de equivalência: (portal, processo)
            # cria índice temporário:
            idx = {}
            for r in existing or []:
                k = f"{(r.get('portal') or '').strip()}|{(r.get('processo') or '').strip()}"
                idx[k] = r.get("id")

            for r in merged:
                k = f"{(r.get('portal') or '').strip()}|{(r.get('processo') or '').strip()}"
                rid = idx.get(k)
                if rid and "upd" in funcs:
                    try: funcs["upd"](rid, r)
                    except Exception: pass
                elif "add" in funcs:
                    try: funcs["add"](r)
                    except Exception: pass
        return changed

    def ensure_scheduler(self):
        """
        Agenda sincronização diária (a cada ~24h).
        Pode ser refinado para agendar em horário específico.
        """
        with self._lock:
            if self._timer is None:
                self._timer = threading.Timer(60 * 60 * 24, self._scheduled_run)
                self._timer.daemon = True
                self._timer.start()

    def _scheduled_run(self):
        try:
            self.sync_once()
        finally:
            # reagenda
            with self._lock:
                self._timer = None
            self.ensure_scheduler()

oportunidades_ingestor = _OportunidadesIngestor()
