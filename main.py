from __future__ import annotations
import os
import importlib
import traceback
from dataclasses import dataclass
from pathlib import Path
import flet as ft


# ======================== TEMA ========================
LIGHT = dict(
    BG="#FFFFFF", SURFACE="#FFFFFF", TEXT="#222222", TEXT_DIM="#666666",
    ACCENT="#0D47A1", DIV="#E0E0E0", OVER="#F1F3F5",
)
DARK = dict(
    BG="#0B1220", SURFACE="#101826", TEXT="#EAF2FF", TEXT_DIM="#B7C1D6",
    ACCENT="#4EA1FF", DIV="#2A3A50", OVER="#1E2A3B",
)

NAV = [
    ("dashboard",        "Dashboard",        ft.Icons.INSIGHTS),
    ("empresas",         "Empresas",         ft.Icons.BUSINESS),
    ("licitacoes",       "Licitações",       ft.Icons.DESCRIPTION),
    ("certidoes",        "Certidões",        ft.Icons.VERIFIED),
    ("banco_precos",     "Banco de Preços",  ft.Icons.TABLE_CHART),
    ("edital_chat",      "Chat Edital",      ft.Icons.CHAT),
    ("oportunidades",    "Oportunidades",    ft.Icons.WORK_HISTORY),
]

# Alertas (se faltar componente, usa fallback inofensivo)
try:
    from components.alerts_modal import AlertsModal
    from components.alerts_bell import build_alerts_bell
except Exception:  # fallback seguro
    class AlertsModal:
        def __init__(self, page: ft.Page): self.page = page
        def open(self, *a, **k): pass
        def close(self, *a, **k): pass
        def refresh(self): pass
    def build_alerts_bell(page: ft.Page, alerts_modal: "AlertsModal"):
        return ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE, tooltip="Alertas")

@dataclass
class UIState:
    collapsed: bool = False
    current_key: str = NAV[0][0]


# ======================== HELPERS ========================
def get_theme(page: ft.Page):
    return LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else DARK

def page_factory(module_name: str):
    mod = importlib.import_module(module_name)
    for fn in ("build", "view", "page", "app"):
        if hasattr(mod, fn):
            return getattr(mod, fn)
    # nomes alternativos
    base = module_name.split(".")[-1]
    for fn in (f"page_{base}", f"{base}_page"):
        if hasattr(mod, fn):
            return getattr(mod, fn)
    raise AttributeError(f"{module_name} não possui função de fábrica compatível.")


# ======================== APP ========================
def main(page: ft.Page):
    # “modo mínimo” de diagnóstico, se necessário
    if os.environ.get("APP_MINIMAL") == "1":
        page.add(ft.Container(padding=20, content=ft.Text("Minimal OK", size=20, weight=ft.FontWeight.W_700)))
        return

    here = Path(__file__).resolve().parent
    page.assets_dir = str(here)
    page.title = "Programa de Licitação"
    page.padding = 0
    page.spacing = 0
    page.scroll = ft.ScrollMode.NEVER  # evita scroll duplo em web
    page.theme_mode = ft.ThemeMode.LIGHT

    state = UIState()
    PAGES = {k: f"pages.{k}" for (k, *_ ) in NAV}
    PAGE_CACHE: dict[str, callable] = {}

    # ---------- carregar logo web-friendly ----------
    def pick_logo() -> tuple[str, int]:
        for fn, h in [
            ("assets/icons/sos_licitacoes_256.png", 40),
            ("assets/icons/sos_licitacoes_128.png", 40),
            ("assets/icons/sos_licitacoes_64.png", 36),
            ("assets/icons/sos_licitacoes_48.png", 32),
            ("logo.png", 32),
        ]:
            if (here / fn).exists(): return fn, h
        return "logo.png", 32
    logo_src, logo_h = pick_logo()

    # ---------- ações do topo ----------
    alerts_modal = AlertsModal(page)
    alerts_bell  = build_alerts_bell(page, alerts_modal)

    def open_about(e=None):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sobre o Programa", weight=ft.FontWeight.W_700, size=18, text_align=ft.TextAlign.CENTER),
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Image(src=logo_src, height=96, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Programa de Licitação — S.O.S Tech", size=15, weight=ft.FontWeight.W_600),
                        ft.Text("Versão: 1.0.0", size=13),
                        ft.Text("Desenvolvido por: Fabio Júnior", size=13),
                    ],
                ),
            ),
            actions=[ft.TextButton("Fechar")],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg.actions[0].on_click = lambda ev: (setattr(dlg, "open", False), page.update())
        page.dialog = dlg
        dlg.open = True
        page.update()

    def toggle_theme(e=None):
        page.theme_mode = (
            ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        )
        apply_theme()
        # re-render para recalcular cores ativas no menu
        render(state.current_key)

    theme_btn = ft.IconButton(icon=ft.Icons.DARK_MODE, tooltip="Alternar tema")
    about_btn = ft.IconButton(icon=ft.Icons.INFO, tooltip="Sobre")
    theme_btn.on_click = toggle_theme
    about_btn.on_click = open_about

    # ---------- header (web safe) ----------
    title_text = ft.Text("PROGRAMA DE LICITAÇÃO", weight=ft.FontWeight.W_700, size=15)
    header = ft.Container(
        height=64,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[ft.Image(src=logo_src, height=logo_h, fit=ft.ImageFit.CONTAIN),
                              title_text],
                ),
                ft.Row(spacing=6, controls=[theme_btn, about_btn, alerts_bell]),
            ],
        ),
    )

    # ---------- content hosts ----------
    host = ft.Container(expand=True)
    content = ft.Container(expand=True, padding=10, content=host)
    divider = ft.Container(height=1)

    # ---------- sidebar ----------
    collapse_btn = ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Recolher/Expandir menu")
    sidebar_header = ft.Row(controls=[collapse_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def nav_button(key: str, label: str, icon):
        # texto fica invisível quando colapsado (mas ocupa zero)
        text = ft.Text(label, size=14, visible=not state.collapsed, no_wrap=True)
        row = ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                     controls=[ft.Icon(icon, size=22), text])
        btn = ft.TextButton(
            data=key,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8),
                                 padding=ft.padding.symmetric(6, 10)),
            content=row,
            on_click=lambda e: render(key),
        )
        return btn

    nav_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
    def rebuild_nav():
        nav_list.controls = [nav_button(k, lbl, ic) for (k, lbl, ic) in NAV]

    footer_title = ft.Text("Bem-vindo ao Programa de Licitação", size=13, weight=ft.FontWeight.W_600)
    footer_sub   = ft.Text("Escolha uma seção no menu", size=12)
    sidebar_footer = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[ft.Column(spacing=2, controls=[footer_title, footer_sub]), ft.Container(width=1)],
        visible=True,
    )

    def apply_sidebar():
        sidebar.width = 72 if state.collapsed else 240
        collapse_btn.icon = ft.Icons.CHEVRON_RIGHT if state.collapsed else ft.Icons.CHEVRON_LEFT
        sidebar_header.alignment = ft.MainAxisAlignment.CENTER if state.collapsed else ft.MainAxisAlignment.SPACE_BETWEEN
        sidebar_footer.visible = not state.collapsed

    def toggle_sidebar(e=None):
        state.collapsed = not state.collapsed
        rebuild_nav()
        apply_theme()
        apply_sidebar()
        page.update()

    collapse_btn.on_click = toggle_sidebar
    rebuild_nav()

    sidebar = ft.Container(
        padding=ft.padding.all(10),
        width=240,
        content=ft.Column(expand=True, spacing=10,
                          controls=[sidebar_header, nav_list, sidebar_footer]),
    )

    # ---------- root layout ----------
    app_root = ft.Container(
        expand=True,
        content=ft.Column(
            spacing=0,
            controls=[
                header,
                divider,
                ft.Row(spacing=0, controls=[
                    sidebar,
                    ft.VerticalDivider(width=1),
                    ft.Container(expand=True, content=content),
                ]),
            ],
        ),
    )
    page.add(app_root)

    # ---------- tema & cores ----------
    def apply_theme():
        T = get_theme(page)
        page.bgcolor = T["BG"]
        header.bgcolor = T["SURFACE"]
        content.bgcolor = T["SURFACE"]
        sidebar.bgcolor = T["SURFACE"]
        divider.bgcolor = T["DIV"]
        title_text.color = T["TEXT"]
        footer_title.color = T["TEXT"]
        footer_sub.color = T["TEXT_DIM"]
        # ícones topo
        for b in (collapse_btn, theme_btn, about_btn):
            try: b.icon_color = T["TEXT"]
            except Exception: pass
        # destacar item atual
        for btn in nav_list.controls:
            if not isinstance(btn, ft.TextButton): continue
            sel = (btn.data == state.current_key)
            icon = btn.content.controls[0]
            text = btn.content.controls[1]
            color = (T["ACCENT"] if sel else T["TEXT"])
            icon.color = color
            text.color = color
            text.visible = not state.collapsed
        # tema do botão ‘tema’
        theme_btn.icon = ft.Icons.LIGHT_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE

    # ---------- render de página ----------
    def get_builder(key: str):
        if key not in PAGE_CACHE:
            try:
                PAGE_CACHE[key] = page_factory(PAGES[key])
            except Exception as ex:
                def _err(_page: ft.Page):
                    return ft.Container(
                        padding=20,
                        content=ft.Column(spacing=8, controls=[
                            ft.Text(f"Falha ao carregar '{key}'", color="#B00020", weight=ft.FontWeight.W_700),
                            ft.Text(str(ex), size=12),
                        ]),
                    )
                PAGE_CACHE[key] = _err
        return PAGE_CACHE[key]

    def view_of(key: str):
        builder = get_builder(key)
        try:
            v = builder(page)
        except Exception as ex:
            v = ft.Container(padding=20, content=ft.Text(f"Erro ao montar '{key}': {ex}", color="#B00020"))
        return v if isinstance(v, ft.Control) else ft.Column(controls=[v], expand=True)

    def render(key: str):
        state.current_key = key
        host.content = view_of(key)
        apply_theme()
        page.update()

    # ---------- primeira pintura ----------
    apply_theme()
    apply_sidebar()
    try:
        render(state.current_key)
    except Exception:
        err = traceback.format_exc()
        host.content = ft.Container(padding=20, content=ft.Text(err, color="#B00020", selectable=True))
        page.update()


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    ft.app(target=main, view=ft.AppView.FLET_APP, assets_dir=str(ROOT))
