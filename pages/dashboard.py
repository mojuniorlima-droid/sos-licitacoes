# pages/dashboard.py (hotfix start seguro no Render)
from __future__ import annotations
import flet as ft
from datetime import date, datetime

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

# === acesso ao DB com import lazy e tolerante ===
def _db():
    try:
        import services.db as db
        return db
    except Exception:
        return None

def _safe_call(fn_name: str, default):
    mod = _db()
    if not mod:
        return default
    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        return default
    try:
        return fn()
    except Exception:
        return default

def _count_try(list_names: list[str], count_names: list[str]) -> int:
    # tenta primeiro funções de contagem, depois lista e len()
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

def _nivel_por_dias(dias: int, mapa: dict) -> str | None:
    if dias <= mapa["pesado"]:
        return "pesado"
    if dias <= mapa["moderado"]:
        return "moderado"
    if dias <= mapa["leve"]:
        return "leve"
    return None

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
                controls=[ft.Icon(icon, size=16, color="#546E7A"),
                          ft.Text(nome, size=12, color=text_dim, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)],
            )
        )
    if not items:
        items = [ft.Text("— nenhum registro —", italic=True, size=12, color=text_dim)]
    return ft.Container(
        bgcolor=surface, border_radius=12, border=ft.border.all(1, border), padding=12, height=min_h,
        content=ft.Column(spacing=8, controls=[ft.Text(title, weight=ft.FontWeight.BOLD, size=13)] + items),
    )

def _info_box(title: str, message: str, surface, border, text_dim, min_h=_CARD_MIN_H):
    header = ft.Text(title, weight=ft.FontWeight.BOLD, size=13)
    body = ft.Text(message, size=12, color=text_dim)
    return ft.Container(
        bgcolor=surface, border_radius=12, border=ft.border.all(1, border), padding=12, height=min_h,
        content=ft.Column(spacing=8, controls=[header, body]),
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
                    ft.Text(str(value), color="#FFFFFF", size=24, weight=ft.FontWeight.W_800),
                    ft.Text(note or "", color="#E3F2FD", size=11),
                ],
            ),
        )
    return ft.Row(spacing=10, controls=[
        _card_kpi("Empresas", n_emp, ft.Icons.BUSINESS, "#0D47A1"),
        _card_kpi("Certidões", n_cer, ft.Icons.VERIFIED, "#1565C0", "vencendo/hoje"),
        _card_kpi("Licitações", n_lic, ft.Icons.DESCRIPTION, "#1976D2", "próximas"),
    ])

# ========= Coleta dos dados =========
def _recentes_empresas():
    return (_safe_call("empresas_recent", None) or
            _safe_call("empresas_list", None)   or
            _safe_call("get_empresas", None)    or
            [])[:5]

def _recentes_licitacoes():
    return (_safe_call("licitacoes_recent", None) or
            _safe_call("list_licitacoes", None)   or
            _safe_call("get_licitacoes", None)    or
            [])[:8]

def _alertas_certidoes():
    rows = (_safe_call("certidoes_list_alertas", None) or
            _safe_call("list_certidoes", None)         or
            _safe_call("get_certidoes", None)          or
            [])
    hoje = _today()
    out = []
    for r in rows:
        validade = r.get("validade") or r.get("data_validade") or r.get("vencimento")
        empresa = r.get("empresa_nome") or r.get("empresa") or "Empresa"
        tipo    = r.get("tipo") or r.get("certidao") or "Certidão"
        d = _pdate(validade or "")
        if not d:
            continue
        dias = (d - hoje).days
        if dias >= 0:
            nivel = _nivel_por_dias(dias, _CER_THRESH)
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
            _safe_call("licitacoes_all", [])   or
            _safe_call("get_licitacoes", [])   or
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
        emp = r.get("empresa_nome") or r.get("empresa") or ""
        obj = r.get("objeto") or r.get("titulo") or ""
        out.append({
            "descricao": _join_text(obj, f"em {dias}d"),
            "nivel": nivel,
            "dias": dias,
            "empresa": emp,
        })
    out.sort(key=lambda x: (x.get("dias", 999), x.get("descricao","")))
    return out[:6]

# ========= Página =========
def build(page: ft.Page) -> ft.Control:
    # Cores seguem seu padrão aprovado (LIGHT/DARK definidos no main)
    surface = "#FFFFFF" if page.theme_mode == ft.ThemeMode.LIGHT else "#101826"
    border  = "#E0E0E0" if page.theme_mode == ft.ThemeMode.LIGHT else "#2A3A50"
    text    = "#222222" if page.theme_mode == ft.ThemeMode.LIGHT else "#EAF2FF"
    text_dim= "#666666" if page.theme_mode == ft.ThemeMode.LIGHT else "#B7C1D6"

    # KPIs
    n_emp = _count_try(["empresas_list","get_empresas"], ["empresas_count"])
    n_cer = len([a for a in _alertas_certidoes() if a.get("nivel") in {"pesado","moderado","leve"}])
    n_lic = len(_alertas_licitacoes())

    kpis = _kpis_row(n_emp, n_cer, n_lic)

    # Coluna esquerda: empresas recentes + info oportunidades + certidões
    recentes_emp = _recentes_empresas()
    box_emp = _recent_box("Empresas recentes", recentes_emp, ft.Icons.BUSINESS, surface, border, text_dim)

    certs = _alertas_certidoes()
    if certs:
        cert_rows = []
        for c in certs[:6]:
            cert_rows.append(
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        _badge(c.get("nivel")),
                        ft.Text(c.get("descricao",""), size=12, color=text_dim, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                )
            )
        box_certs = ft.Container(
            bgcolor=surface, border_radius=12, border=ft.border.all(1, border), padding=12, height=_CARD_MIN_H,
            content=ft.Column(spacing=8, controls=[ft.Text("Certidões em alerta", weight=ft.FontWeight.BOLD, size=13)] + cert_rows),
        )
    else:
        box_certs = _info_box("Certidões em alerta", "Nenhuma certidão em alerta no momento.", surface, border, text_dim)

    box_oport = _info_box("Oportunidades da semana",
                          "Integração prevista na versão 1.0.1 — exibirá oportunidades filtradas e atualizadas.",
                          surface, border, text_dim)

    left_column = ft.Column(spacing=12, expand=True, controls=[box_emp, box_oport, box_certs])

    # Direita: alertas licitações + licitações recentes
    lic_alerts = _alertas_licitacoes()
    if lic_alerts:
        alert_rows = []
        for a in lic_alerts:
            alert_rows.append(
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        _badge(a.get("nivel")),
                        ft.Text(a.get("descricao",""), size=12, color=text_dim, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                )
            )
        right_alerts = ft.Container(
            bgcolor=surface, border_radius=12, border=ft.border.all(1, border), padding=12, height=_CARD_MIN_H,
            content=ft.Column(spacing=8, controls=[ft.Text("Alertas de licitações", weight=ft.FontWeight.BOLD, size=13)] + alert_rows),
        )
    else:
        right_alerts = _info_box("Alertas de licitações", "Nenhum alerta para os próximos dias.", surface, border, text_dim)

    recentes_lic = _recentes_licitacoes()
    lic_items = []
    for r in recentes_lic[:10]:
        titulo = r.get("objeto") or r.get("titulo") or r.get("processo") or "Licitação"
        lic_items.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(ft.Icons.DESCRIPTION, size=16, color="#546E7A"),
                          ft.Text(titulo, size=12, color=text_dim, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)],
            )
        )
    if not lic_items:
        lic_items = [ft.Text("— nenhum registro —", italic=True, size=12, color=text_dim)]
    lic_box = ft.Container(
        bgcolor=surface, border_radius=12, border=ft.border.all(1, border), padding=12, height=_CARD_MIN_H*2,
        content=ft.Column(spacing=8, controls=[ft.Text("Licitações recentes", weight=ft.FontWeight.BOLD, size=13)] + lic_items),
    )

    right_column = ft.Column(spacing=12, expand=True, controls=[right_alerts, lic_box])

    return ft.Container(
        expand=True,
        content=ft.Row(spacing=12, controls=[left_column, right_column]),
    )
