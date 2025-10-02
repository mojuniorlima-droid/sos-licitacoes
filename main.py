# main.py — start seguro (fallback nos alertas + lazy import das páginas)
from __future__ import annotations
import flet as ft
from pathlib import Path
import importlib

# ==== ALERTAS com fallback (não derruba o app se faltarem os componentes) ====
try:
    from components.alerts_modal import AlertsModal
    from components.alerts_bell import build_alerts_bell
    _ALERTS_OK = True
except Exception:
    _ALERTS_OK = False
    class AlertsModal:
        def __init__(self, page: ft.Page): self.page = page
        def open(self, *a, **k): pass
        def close(self, *a, **k): pass
        def refresh(self): pass
    def build_alerts_bell(page: ft.Page, alerts_modal: AlertsModal):
        # sino neutro, só para não quebrar o topo
        return ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE, tooltip="Alertas (indisponível)")

# ==== palette (não mexe no seu layout; apenas definimos cores de base) ====
LIGHT_BG, LIGHT_SURFACE, LIGHT_TEXT, LIGHT_TEXT_DIM = "#FFFFFF", "#FFFFFF", "#222222", "#666666"
LIGHT_ACCENT, LIGHT_DIVIDER, LIGHT_OVERLAY = "#0D47A1", "#E0E0E0", "#E0E0E0"
DARK_BG, DARK_SURFACE, DARK_TEXT, DARK_TEXT_DIM = "#0B1220", "#101826", "#EAF2FF", "#B7C1D6"
DARK_ACCENT, DARK_DIVIDER, DARK_OVERLAY = "#4EA1FF", "#2A3A50", "#1E2A3B"

# ==== NAV (mantenha como já usa) ====
NAV = [
    ("dashboard",        "Dashboard",        ft.Icons.INSIGHTS),
    ("empresas",         "Empresas",         ft.Icons.BUSINESS),
    ("licitacoes",       "Licitações",       ft.Icons.DESCRIPTION),
    ("certidoes",        "Certidões",        ft.Icons.VERIFIED),
    ("banco_precos",     "Banco de Preços",  ft.Icons.TABLE_CHART),
    ("edital_chat",      "Chat Edital",      ft.Icons.CHAT),
    ("oportunidades",    "Oportunidades",    ft.Icons.WORK_HISTORY),
]

# ==== fábrica de páginas (procura build/view/page/app no módulo) ====
def _page_factory(module_name: str):
    mod = importlib.import_module(module_name)
    base = module_name.split(".")[-1]
    for fname in ("build", "view", "page", "app", f"page_{base}", f"{base}_page"):
        if hasattr(mod, fname):
            return getattr(mod, fname)
    raise AttributeError(f"Módulo {module_name} não possui função fábrica compatível.")

# ==== LAZY IMPORT: não carrega as páginas no start ====
PAGES = {k: f"pages.{k}" for (k, _label, _icon) in NAV}
_PAGE_BUILDERS_CACHE: dict[str, callable] = {}

def _get_page_builder(key: str):
    if key in _PAGE_BUILDERS_CACHE:
        return _PAGE_BUILDERS_CACHE[key]
    try:
        factory = _page_factory(PAGES[key])
        _PAGE_BUILDERS_CACHE[key] = factory
        return factory
    except Exception as ex:
        # devolve uma “página” de erro amigável em vez de derrubar o app
        def _err(_page: ft.Page):
            return ft.Container(
                padding=20,
                content=ft.Column(spacing=8, controls=[
                    ft.Text(f"Falha ao carregar a página '{key}'.", weight=ft.FontWeight.W_700, color="#B00020"),
                    ft.Text(str(ex), size=12),
                ])
            )
        _PAGE_BUILDERS_CACHE[key] = _err
        return _err

def _view_of(key: str, page: ft.Page) -> ft.Control:
    builder = _get_page_builder(key)
    try:
        v = builder(page)
    except Exception as ex:
        v = ft.Container(padding=20, bgcolor= "#00000000",
                         content=ft.Text(f"Erro ao montar página '{key}': {ex}", color="#B00020"))
    return v if isinstance(v, ft.Control) else ft.Column(controls=[v], expand=True)

# ==== app ====
def main(page: ft.Page):
    here = Path(__file__).resolve().parent
    page.assets_dir = str(here)
    page.title = "Programa de Licitação"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    def BG():       return LIGHT_BG      if page.theme_mode == ft.ThemeMode.LIGHT else DARK_BG
    def SURFACE():  return LIGHT_SURFACE if page.theme_mode == ft.ThemeMode.LIGHT else DARK_SURFACE
    def TXT():      return LIGHT_TEXT    if page.theme_mode == ft.ThemeMode.LIGHT else DARK_TEXT
    def TXT_DIM():  return LIGHT_TEXT_DIM if page.theme_mode == ft.ThemeMode.LIGHT else DARK_TEXT_DIM
    def ACCENT():   return LIGHT_ACCENT  if page.theme_mode == ft.ThemeMode.LIGHT else DARK_ACCENT
    def DIV():      return LIGHT_DIVIDER if page.theme_mode == ft.ThemeMode.LIGHT else DARK_DIVIDER
    def OVERLAY():  return LIGHT_OVERLAY if page.theme_mode == ft.ThemeMode.LIGHT else DARK_OVERLAY

    page.bgcolor = BG()
    try: page.window_bgcolor = BG()
    except Exception: pass

    # Logo (usa o que você já tiver no repo)
    if (here / "assets/icons/sos_licitacoes_256.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_256.png", 150
    elif (here / "assets/icons/sos_licitacoes_128.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_128.png", 84
    elif (here / "assets/icons/sos_licitacoes_64.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_64.png", 64
    elif (here / "assets/icons/sos_licitacoes_48.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_48.png", 48
    else:
        logo_src, logo_h = "logo.png", 64

    # Sobre
    def open_about(e=None):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sobre o Programa", weight=ft.FontWeight.W_700, size=18, text_align=ft.TextAlign.CENTER),
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Image(src=logo_src, height=128, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Programa de Licitação — S.O.S Tech", size=16, weight=ft.FontWeight.W_600),
                        ft.Text("Versão: 1.0.0", size=14),
                        ft.Text("Desenvolvido por: Fabio Júnior", size=14),
                    ],
                ),
            ),
            actions=[ft.TextButton("Fechar")],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg.actions[0].on_click = lambda ev: setattr(dlg, "open", False) or page.update()
        page.dialog = dlg; dlg.open = True; page.update()

    theme_btn = ft.IconButton(icon=ft.Icons.WB_SUNNY, tooltip="Alternar tema")
    def _refresh_theme_button():
        theme_btn.icon = ft.Icons.WB_SUNNY if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.DARK_MODE
    def toggle_theme(e=None):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        _apply_theme_colors(); render(current_key)

    about_btn = ft.IconButton(icon=ft.Icons.INFO, tooltip="Sobre", on_click=open_about)

    # Alertas (com fallback acima)
    alerts_modal = AlertsModal(page)
    alerts_bell  = build_alerts_bell(page, alerts_modal)

    # Header
    header = ft.Container(
        bgcolor= SURFACE(),
        padding=ft.padding.only(left=10, right=10, top=-35, bottom=-4),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Image(src=logo_src, height=logo_h, fit=ft.ImageFit.CONTAIN, filter_quality=ft.FilterQuality.HIGH),
                        ft.Text("PROGRAMA DE LICITAÇÃO", weight=ft.FontWeight.W_700, size=15),
                    ],
                ),
                ft.Row(controls=[theme_btn, about_btn, alerts_bell]),
            ],
        ),
    )
    title = header.content.controls[0].controls[1]

    # NAV (mesma ideia visual; só refiz em Row)
    def _make_btn(key: str, label: str, icon):
        return ft.TextButton(
            data=key,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(6, 10),
                overlay_color=OVERLAY(),
            ),
            on_click=lambda e: render(key),
            content=ft.Row(
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(icon, size=22), ft.Text(label, size=14)],
            ),
        )
    nav_buttons = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                         controls=[_make_btn(k, lbl, ic) for (k, lbl, ic) in NAV])

    nav_bar = ft.Container(bgcolor= SURFACE(),
                           padding=ft.padding.only(left=10, right=10, top=45, bottom=4),
                           margin=ft.margin.only(top=-50),
                           content=nav_buttons)

    divider = ft.Container(height=1, bgcolor= LIGHT_DIVIDER)

    # Área de conteúdo
    host = ft.Container(expand=True)
    content = ft.Container(expand=True, bgcolor= SURFACE(), padding=10, content=host)

    # Renderização
    current_key = NAV[0][0]  # página inicial segue a primeira do NAV
    def render(key: str):
        nonlocal current_key
        current_key = key
        # destaca botão atual
        for btn in nav_buttons.controls:
            sel = (btn.data == current_key)
            lbl = btn.content.controls[1]; icn = btn.content.controls[0]
            lbl.weight = ft.FontWeight.W_700 if sel else ft.FontWeight.W_400
            lbl.color  = ACCENT() if sel else TXT()
            icn.color  = ACCENT() if sel else TXT()
        # carrega a view da página (lazy)
        host.content = _view_of(key, page)
        try: alerts_bell.refresh_badge()
        except Exception: pass
        page.update()

    # Árvore raiz (mantendo estilo)
    root = ft.Container(
        expand=True,
        bgcolor= BG(),
        content=ft.Column(
            expand=True, spacing=0,
            controls=[header, nav_bar, divider, content],
        ),
    )

    def _apply_theme_colors():
        page.bgcolor = BG()
        try: page.window_bgcolor = BG()
        except Exception: pass
        header.bgcolor = SURFACE()
        nav_bar.bgcolor = SURFACE()
        divider.bgcolor = DIV()
        content.bgcolor = SURFACE()
        title.color = TXT()
        for btn in nav_buttons.controls:
            sel = (btn.data == current_key)
            lbl = btn.content.controls[1]; icn = btn.content.controls[0]
            lbl.color  = ACCENT() if sel else TXT()
            icn.color  = ACCENT() if sel else TXT()
            try: btn.style.overlay_color = OVERLAY()
            except Exception: pass
        _refresh_theme_button()

    page.add(root)
    _apply_theme_colors()
    theme_btn.on_click = toggle_theme
    render(current_key)  # mostra a primeira página

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, assets_dir=str(ROOT), web_renderer="html")
