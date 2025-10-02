# pages/dashboard.py
from __future__ import annotations
import flet as ft
from datetime import date, datetime
import services.db as db

# ========= Config / Helpers =========
_CER_THRESH = {"leve": 15, "moderado": 7, "pesado": 1}
_LIC_THRESH = {"leve": 7,  "moderado": 3, "pesado": 1}
_CARD_MIN_H = 160  # altura mínima por caixa

def _pdate(s: str):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def _today() -> date:
    return date.today()

def _nivel_por_dias(dias: int, mapa: dict) -> str | None:
    if dias <= mapa["pesado"]:
        return "pesado"
    if dias <= mapa["moderado"]:
        return "moderado"
    if dias <= mapa["leve"]:
        return "leve"
    return None

def _safe_call(name: str, default):
    fn = getattr(db, name, None)
    if not callable(fn):
        return default
    try:
        return fn()
    except Exception:
        return default

def _count_try(list_names: list[str], count_names: list[str]) -> int:
    for nm in count_names:
        v = _safe_call(nm, None)
        if v is not None:
            try:
                return int(v)
            except Exception:
                pass
    for nm in list_names:
        items = _safe_call(nm, None)
        if items is not None:
            try:
                return len(items or [])
            except Exception:
                pass
    return 0

def _join_text(*parts: str) -> str:
    parts = [p for p in parts if p and str(p).strip()]
    return " — ".join(parts) if parts else ""

def _badge(nivel: str) -> ft.Control:
    # leve=azul, moderado=amarelo, urgente=vermelho, vencida=rosa
    map_bg = {"pesado":"#FFCDD2","moderado":"#FFE0B2","leve":"#BBDEFB","vencida":"#F8BBD0"}
    map_fg = {"pesado":"#B71C1C","moderado":"#E65100","leve":"#0D47A1","vencida":"#880E4F"}
    label_map = {"pesado":"urgente","moderado":"moderado","leve":"leve","vencida":"vencida"}
    txt = label_map.get(nivel, nivel or "")
    return ft.Container(
        bgcolor=map_bg.get(nivel, "#ECEFF1"),
        padding=ft.padding.only(8,2,8,2),
        border_radius=9999,
        content=ft.Text(txt, size=10, weight=ft.FontWeight.BOLD, color=map_fg.get(nivel, "#37474F")),
    )

# ========= Blocos visuais =========
def _recent_box(title, rows, icon, surface, border, text_dim, min_h=_CARD_MIN_H):
    items = []
    for r in rows or []:
        try:
            nome = (r.get("nome") if hasattr(r, "get") else (r["nome"] if isinstance(r, dict) else str(r)))
        except Exception:
            nome = str(r)
        items.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=16, color="#546E7A"),
                    ft.Container(
                        expand=True,
                        content=ft.Text(nome, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ),
                ],
            )
        )
    if not items:
        items = [ft.Text("— nenhum registro —", italic=True, size=12, color=text_dim)]
    header = ft.Text(title, weight=ft.FontWeight.BOLD, size=13)
    controls_list = [header] + items
    return ft.Container(
        bgcolor=surface,
        border_radius=12,
        border=ft.border.all(1, border),
        padding=12,
        height=min_h,
        content=ft.Column(
            spacing=8,
            controls=controls_list,
        ),
    )

def _info_box(title: str, message: str, surface, border, text_dim, min_h=_CARD_MIN_H):
    header = ft.Text(title, weight=ft.FontWeight.BOLD, size=13)
    body = ft.Text(message, size=12, color=text_dim)
    return ft.Container(
        bgcolor=surface,
        border_radius=12,
        border=ft.border.all(1, border),
        padding=12,
        height=min_h,
        content=ft.Column(
            spacing=8,
            controls=[header, body],
        ),
    )

def _kpis_row(n_emp, n_cer, n_lic):
    def _card_kpi(title, value, icon, bg, note: str | None = None):
        return ft.Container(
            expand=True, bgcolor=bg, border_radius=16, padding=16,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[ft.Text(title, color="#FFFFFF", size=12, weight=ft.FontWeight.BOLD),
                                  ft.Icon(icon, color="#FFFFFF", size=20)],
                    ),
                    ft.Text(str(value), color="#FFFFFF", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(note or "", color="#FFFFFF", size=10),
                ],
            ),
        )
    return ft.Row(
        spacing=12,
        controls=[
            _card_kpi("Empresas",      n_emp, ft.Icons.BUSINESS,     "#1565C0"),
            _card_kpi("Certidões",     n_cer, ft.Icons.VERIFIED,     "#2E7D32"),
            _card_kpi("Licitações",    n_lic, ft.Icons.DESCRIPTION,  "#4527A0"),
            _card_kpi("Oportunidades", "—",   ft.Icons.WORK_HISTORY, "#EF6C00", note="Disp. na 1.0.1"),
        ],
    )

# ========= Dados =========
def _recentes_empresas(limit=5):
    rows = (_safe_call("list_empresas", []) or
            _safe_call("empresas_all", []) or
            _safe_call("list_companies", []) or
            _safe_call("companies_all", []) or
            [])
    try:
        rows = sorted(rows, key=lambda r: ((r.get("created_at") or ""), (r.get("id") or 0)), reverse=True)
    except Exception:
        try:
            rows = sorted(rows, key=lambda r: (r.get("id") or 0), reverse=True)
        except Exception:
            pass
    return [{"id": r.get("id"), "nome": (r.get("name") or r.get("nome") or f"Empresa #{r.get('id')}")} for r in rows[:limit]]

def _recentes_licitacoes(limit=12):
    rows = _safe_call("list_licitacoes", []) or _safe_call("licitacoes_all", []) or []
    try:
        rows = sorted(rows, key=lambda r: ((r.get("created_at") or ""), (r.get("id") or 0)), reverse=True)
    except Exception:
        try:
            rows = sorted(rows, key=lambda r: (r.get("id") or 0), reverse=True)
        except Exception:
            pass
    out = []
    for r in rows[:limit]:
        titulo = _join_text(r.get("orgao",""), r.get("processo") or r.get("modalidade",""))
        out.append({"id": r.get("id"), "nome": (titulo or f"Licit. #{r.get('id')}")})
    return out

def _alertas_certidoes():
    prontos = _safe_call("certidoes_expirando", None)
    if isinstance(prontos, list) and prontos:
        return prontos
    certs = (_safe_call("list_certidoes", []) or
             _safe_call("certidoes_all", []) or
             _safe_call("get_certidoes", []) or
             [])
    hoje = _today()
    out = []
    for r in certs:
        validade = r.get("validade") or r.get("dt_validade") or r.get("vencimento") or ""
        dv = _pdate(validade)
        if not dv:
            continue
        dias = (dv - hoje).days
        nivel = _nivel_por_dias(dias, _CER_THRESH)
        if nivel is None and dias >= 0:
            continue
        empresa = r.get("empresa") or r.get("razao") or r.get("nome") or ""
        tipo = r.get("tipo") or r.get("certidao") or ""
        if dias >= 0:
            desc = f"{empresa} – {tipo} vence em {dias}d ({validade})"
            nivel_out = (nivel or "leve")
        else:
            desc = f"{empresa} – {tipo} VENCIDA ({validade})"
            nivel_out = "vencida"
        out.append({"descricao": desc, "dias": dias, "nivel": nivel_out})
    ord_key = {"pesado":0,"moderado":1,"leve":2,"vencida":3}
    out.sort(key=lambda x: (ord_key.get(x.get("nivel"), 9), x.get("dias", 999)))
    return out

def _alertas_licitacoes():
    prontos = _safe_call("licitacoes_proximas", None)
    if isinstance(prontos, list) and prontos:
        return prontos
    rows = (_safe_call("list_licitacoes", []) or
            _safe_call("licitacoes_all", []) or
            _safe_call("get_licitacoes", []) or
            [])
    hoje = _today()
    out = []
    for r in rows:
        ds_raw = r.get("data_sessao") or r.get("data") or r.get("sessao_data")
        ds = _pdate(ds_raw or "")
        if not ds:
            continue
        dias = (ds - hoje).days
        if dias < 0:
            continue
        nivel = _nivel_por_dias(dias, _LIC_THRESH)
        if nivel is None:
            continue
        orgao = r.get("orgao") or ""
        processo = r.get("processo") or ""
        hora = r.get("hora") or ""
        obj = (r.get("objeto") or "").strip()
        titulo = obj if obj else _join_text(orgao, processo)
        texto = f"{titulo} — sessão em {ds.strftime('%d/%m/%Y')} {hora} (em {dias}d)"
        out.append({"objeto": texto, "dias": dias, "nivel": nivel})
    out.sort(key=lambda x: ({"pesado":0,"moderado":1,"leve":2}.get(x.get("nivel"), 9), x.get("dias", 999)))
    return out

# ========= Página =========
def build(page: ft.Page) -> ft.Control:
    light = (page.theme_mode == ft.ThemeMode.LIGHT)
    surface = "#FFFFFF" if light else "#101826"
    border = "#E0E0E0" if light else "#1E2A3B"
    text_dim = "#616161" if light else "#90A4AE"

    n_emp = _count_try(
        ["list_empresas", "empresas_all", "list_companies", "companies_all", "get_empresas"],
        ["count_empresas", "empresas_count", "count_companies"]
    )
    n_cer = _count_try(
        ["list_certidoes", "certidoes_all", "get_certidoes"],
        ["count_certidoes", "certidoes_count"]
    )
    n_lic = _count_try(
        ["list_licitacoes", "licitacoes_all", "get_licitacoes"],
        ["count_licitacoes", "licitacoes_count"]
    )

    recentes_emp = _recentes_empresas()
    recentes_lic = _recentes_licitacoes(limit=12)

    # listas de alertas (texto não vaza)
    cert_list_controls = []
    for c in _alertas_certidoes() or []:
        cert_list_controls.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER, size=16, color="#FFB300"),
                    ft.Container(expand=True, content=ft.Text(c.get("descricao",""), size=12, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)),
                    _badge(c.get("nivel","")),
                ],
            )
        )
    if not cert_list_controls:
        cert_list_controls = [ft.Text("— nenhum alerta —", italic=True, color=text_dim)]

    lic_list_controls = []
    for l in _alertas_licitacoes() or []:
        lic_list_controls.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.EVENT, size=16, color="#64B5F6"),
                    ft.Container(expand=True, content=ft.Text(l.get("objeto",""), size=12, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)),
                    _badge(l.get("nivel","")),
                ],
            )
        )
    if not lic_list_controls:
        lic_list_controls = [ft.Text("— nenhum alerta —", italic=True, color=text_dim)]

    kpis = _kpis_row(n_emp, n_cer, n_lic)

    # ESQUERDA: Empresas (em cima) + Oportunidades da semana (embaixo)
    left_grid = ft.Column(
        spacing=12,
        controls=[
            _recent_box("Empresas recentes", recentes_emp, ft.Icons.BUSINESS, surface, border, text_dim),
            _info_box(
                "Oportunidades da semana",
                "Integração prevista na versão 1.0.1 — exibirá oportunidades filtradas e atualizadas.",
                surface, border, text_dim
            ),
        ],
    )

    # DIREITA: Licitações recentes ocupando duas caixas (altura dupla)
    lic_items = []
    for item in recentes_lic:
        lic_items.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.DESCRIPTION, size=16, color="#546E7A"),
                    ft.Container(expand=True, content=ft.Text(item["nome"], size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ],
            )
        )
    if not lic_items:
        lic_items = [ft.Text("— nenhum registro —", italic=True, size=12, color=text_dim)]
    lic_header = ft.Text("Licitações recentes", weight=ft.FontWeight.BOLD, size=13)
    lic_controls = [lic_header] + lic_items

    right_grid = ft.Container(
        expand=True,
        content=ft.Container(
            bgcolor=surface,
            border_radius=12,
            border=ft.border.all(1, border),
            padding=12,
            height=_CARD_MIN_H * 2 + 12,  # 2 caixas + espaçamento
            content=ft.Column(
                spacing=8,
                controls=lic_controls,
            ),
        ),
    )

    grid_row = ft.Row(
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Container(expand=True, content=left_grid),
            right_grid,
        ],
    )

    # Coluna principal + painel de alertas
    left_column = ft.Container(
        expand=True, bgcolor=surface,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Início", size=18, weight=ft.FontWeight.BOLD),
                kpis,
                grid_row,
            ],
        ),
    )

    right_alerts = ft.Container(
        width=360,
        bgcolor=surface,
        border_radius=12,
        border=ft.border.all(1, border),
        padding=12,
        content=ft.Column(spacing=12, controls=[
            ft.Text("Alertas", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Certidões (≤15d leve • ≤7d moderado • ≤1d urgente)", size=12, color=text_dim),
            ft.Column(spacing=8, controls=cert_list_controls),
            ft.Divider(),
            ft.Text("Licitações (≤7d leve • ≤3d moderado • ≤1d urgente)", size=12, color=text_dim),
            ft.Column(spacing=8, controls=lic_list_controls),
        ]),
    )

    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(expand=True, bgcolor=surface),
            ft.Container(
                expand=True, bgcolor=surface, padding=0,
                content=ft.Row(spacing=12, controls=[left_column, right_alerts]),
            ),
        ],
    )
