# main.py — start robusto para web (Render) mantendo seu layout
from __future__ import annotations
import os
import traceback
from pathlib import Path
import importlib
import flet as ft

# ---------- TEMA E CORES ----------
LIGHT_BG, LIGHT_SURFACE, LIGHT_TEXT, LIGHT_TEXT_DIM = "#FFFFFF", "#FFFFFF", "#222222", "#666666"
LIGHT_ACCENT, LIGHT_DIVIDER, LIGHT_OVERLAY = "#0D47A1", "#E0E0E0", "#E0E0E0"
DARK_BG, DARK_SURFACE, DARK_TEXT, DARK_TEXT_DIM = "#0B1220", "#101826", "#EAF2FF", "#B7C1D6"
DARK_ACCENT, DARK_DIVIDER, DARK_OVERLAY = "#4EA1FF", "#2A3A50", "#1E2A3B"

# ---------- ALERTAS (fallback seguro) ----------
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

    def build_alerts_bell(page: ft.Page, alerts_modal: "AlertsModal"):
        return ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE, tooltip="Alertas (indisponível)")

# ---------- NAV ----------
NAV = [
    ("dashboard",        "Dashboard",        ft.Icons.INSIGHTS),
    ("empresas",         "Empresas",         ft.Icons.BUSINESS),
    ("licitacoes",       "Licitações",       ft.Icons.DESCRIPTION),
    ("certidoes",        "Certidões",        ft.Icons.VERIFIED),
    ("banco_precos",     "Banco de Preços",  ft.Icons.TABLE_CHART),
    ("edital_chat",      "Chat Edital",      ft.Icons.CHAT),
    ("oportunidades",    "Oportunidades",    ft.Icons.WORK_HISTORY),
]

# ---------- BRIDGE DE RESIZE (no-op seguro) ----------
def _install_resize_bridge(page: ft.Page) -> None:
    try:
        def _on_resized(e): pass
        page.on_resized = _on_resized
    except Exception:
        pass

# ---------- FÁBRICA DE PÁGINAS + LAZY CACHE ----------
def _page_factory(module_name: str):
    mod = importlib.import_module(module_name)
    base = module_name.split(".")[-1]
    for fname in ("build", "view", "page", "app", f"page_{base}", f"{base}_page"):
        if hasattr(mod, fname):
            return getattr(mod, fname)
    raise AttributeError(f"Módulo {module_name} não possui função fábrica compatível.")

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
        def _err(_page: ft.Page):
            return ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(f"Falha ao carregar a página '{key}'.", weight=ft.FontWeight.W_700, color="#B00020"),
                        ft.Text(str(ex), size=12),
                    ],
                ),
            )
        _PAGE_BUILDERS_CACHE[key] = _err
        return _err

def _view_of(key: str, page: ft.Page) -> ft.Control:
    builder = _get_page_builder(key)
    try:
        v = builder(page)
    except Exception as ex:
        v = ft.Container(
            padding=20,
            bgcolor="#00000000",
            content=ft.Text(f"Erro ao montar página '{key}': {ex}", color="#B00020"),
        )
    return v if isinstance(v, ft.Control) else ft.Column(controls=[v], expand=True)

# ---------- APP ----------
def main(page: ft.Page):
    # ===== DIAGNÓSTICO MÍNIMO (APP_MINIMAL=1) =====
    if os.environ.get("APP_MINIMAL") == "1":
        print("[APP] main() entrou (modo mínimo)", flush=True)
        page.title = "SOS Licitações — Modo Mínimo"
        page.add(ft.Container(padding=20, content=ft.Text("Minimal OK", size=20, weight=ft.FontWeight.W_700)))
        page.update()
        return
    print("[APP] main() entrou (modo completo)", flush=True)
    # ===== FIM DIAGNÓSTICO =====

    here = Path(__file__).resolve().parent
    page.assets_dir = str(here)
    page.title = "Programa de Licitação"
    page.theme_mode = ft.ThemeMode.LIGHT

    page.padding = 0
    page.spacing = 0
    page.bgcolor = LIGHT_BG
    try: page.window_bgcolor = LIGHT_BG
    except Exception: pass

    # (opcional) gerar logo.ico
    def _ensure_multi_size_ico(root_dir: Path) -> None:
        try:
            from PIL import Image
            ico_path = root_dir / "logo.ico"
            png_path = root_dir / "logo.png"
            if png_path.exists() and not ico_path.exists():
                sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
                with Image.open(png_path) as im:
                    im.save(ico_path, sizes=sizes)
        except Exception:
            pass

    _ensure_multi_size_ico(here)
    try: page.window.icon = str(here / "logo.ico")
    except Exception: pass

    _install_resize_bridge(page)

    def BG():       return LIGHT_BG      if page.theme_mode == ft.ThemeMode.LIGHT else DARK_BG
    def SURFACE():  return LIGHT_SURFACE if page.theme_mode == ft.ThemeMode.LIGHT else DARK_SURFACE
    def TXT():      return LIGHT_TEXT    if page.theme_mode == ft.ThemeMode.LIGHT else DARK_TEXT
    def TXT_DIM():  return LIGHT_TEXT_DIM if page.theme_mode == ft.ThemeMode.LIGHT else DARK_TEXT_DIM
    def ACCENT():   return LIGHT_ACCENT  if page.theme_mode == ft.ThemeMode.LIGHT else DARK_ACCENT
    def DIV():      return LIGHT_DIVIDER if page.theme_mode == ft.ThemeMode.LIGHT else DARK_DIVIDER
    def OVERLAY():  return LIGHT_OVERLAY if page.theme_mode == ft.ThemeMode.LIGHT else DARK_OVERLAY

    # Logo
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

    # Ações topo
    theme_btn = ft.IconButton(icon=ft.Icons.WB_SUNNY, tooltip="Alternar tema")
    about_btn = ft.IconButton(icon=ft.Icons.INFO, tooltip="Sobre")
    alerts_modal = AlertsModal(page)
    alerts_bell  = build_alerts_bell(page, alerts_modal)

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
        dlg.actions[0].on_click = lambda ev: setattr(dlg, "open", False) | page.update()
        page.dialog = dlg; dlg.open = True; page.update()

    def toggle_theme(e=None):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        _apply_theme_colors(); render(current_key)

    theme_btn.on_click = toggle_theme
    about_btn.on_click = open_about

    # Header
    header = ft.Container(
        bgcolor= LIGHT_SURFACE,
        padding=ft.padding.only(left=10, right=10, top=-35, bottom=-4),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Image(src=logo_src, height=logo_h, fit=ft.ImageFit.CONTAIN, filter_quality=ft.FilterQuality.HIGH, tooltip="S.O.S Licitações"),
                        ft.Text("PROGRAMA DE LICITAÇÃO", weight=ft.FontWeight.W_700, size=15),
                    ],
                ),
                ft.Row(controls=[theme_btn, about_btn, alerts_bell]),
            ],
        ),
    )
    title = header.content.controls[0].controls[1]

    # Conteúdo
    host = ft.Container(expand=True)
    content = ft.Container(expand=True, bgcolor= LIGHT_SURFACE, padding=10, content=host)
    divider = ft.Container(height=1, bgcolor= LIGHT_DIVIDER)

    # Sidebar
    nav_collapsed = {"value": False}
    collapse_btn = ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Recolher/Expandir menu")

    def _make_nav_button(key: str, label: str, icon):
        return ft.TextButton(
            data=key,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(6, 10),
            ),
            on_click=lambda e: render(key),
            content=ft.Row(
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(icon, size=22), ft.Text(label, size=14)],
            ),
        )

    nav_buttons = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
    def _rebuild_nav_buttons():
        nav_buttons.controls = [_make_nav_button(k, lbl, ic) for (k, lbl, ic) in NAV]

    def _toggle_sidebar(e=None):
        nav_collapsed["value"] = not nav_collapsed["value"]
        _rebuild_nav_buttons()
        _apply_theme_colors()
        _apply_sidebar()

    def _apply_sidebar():
        sidebar.width = 68 if nav_collapsed["value"] else 240
        collapse_btn.icon = ft.Icons.CHEVRON_RIGHT if nav_collapsed["value"] else ft.Icons.CHEVRON_LEFT
        sidebar_footer.alignment = ft.MainAxisAlignment.CENTER if nav_collapsed["value"] else ft.MainAxisAlignment.SPACE_BETWEEN

    collapse_btn.on_click = _toggle_sidebar
    _rebuild_nav_buttons()

    welcome = ft.Text("Bem-vindo ao Programa de Licitação", size=14, weight=ft.FontWeight.W_600)
    sub = ft.Text("Escolha uma seção no menu", size=12)

    sidebar_footer = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[ft.Column(spacing=2, controls=[welcome, sub]), ft.Container(width=1)],
    )

    sidebar = ft.Container(
        padding=ft.padding.all(10),
        content=ft.Column(
            expand=True,
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN if not nav_collapsed["value"] else ft.MainAxisAlignment.CENTER,
                    controls=[collapse_btn],
                ),
                nav_buttons,
                ft.Container(expand=True),
                sidebar_footer,
            ],
        ),
        bgcolor= LIGHT_SURFACE,
        width=240,
    )

    # Root
    current_key = NAV[0][0]

    def render(key: str):
        nonlocal current_key
        current_key = key
        host.content = _view_of(key, page)
        for btn in nav_buttons.controls:
            if not isinstance(btn, ft.TextButton):
                continue
            sel = (btn.data == current_key)
            lbl = btn.content.controls[1]
            icn = btn.content.controls[0]
            lbl.weight = ft.FontWeight.W_700 if sel else ft.FontWeight.W_400
            lbl.color  = (LIGHT_ACCENT if page.theme_mode == ft.ThemeMode.LIGHT else DARK_ACCENT) if sel else (
                LIGHT_TEXT if page.theme_mode == ft.ThemeMode.LIGHT else DARK_TEXT
            )
            icn.color = lbl.color
        try: alerts_bell.refresh_badge()
        except Exception: pass
        page.update()

    root = ft.Container(
        expand=True,
        bgcolor= LIGHT_BG,
        content=ft.Row(
            spacing=0,
            controls=[
                ft.Container(width=10),
                ft.Container(width=240, content=ft.Column(spacing=0, controls=[header, divider, sidebar])),
                ft.VerticalDivider(width=1, color= LIGHT_DIVIDER),
                ft.Container(expand=True, content=content),
            ],
        ),
    )

    def _apply_theme_colors():
        page.bgcolor = BG()
        try: page.window_bgcolor = BG()
        except Exception: pass
        header.bgcolor = SURFACE()
        sidebar.bgcolor = SURFACE()
        content.bgcolor = SURFACE()
        divider.bgcolor = DIV()
        title.color = TXT()
        welcome.color = TXT()
        sub.color = TXT_DIM()
        for btn in nav_buttons.controls:
            if isinstance(btn, ft.TextButton):
                sel = (btn.data == current_key)
                lbl = btn.content.controls[1]
                icn = btn.content.controls[0]
                lbl.color  = ACCENT() if sel else TXT()
                lbl.weight = ft.FontWeight.W_700 if sel else ft.FontWeight.W_400
                icn.color  = ACCENT() if sel else TXT()
        for b in (collapse_btn, about_btn, theme_btn, alerts_bell):
            try: b.icon_color = TXT()
            except Exception: pass
            try: b.style.overlay_color = OVERLAY()
            except Exception: pass

    page.add(root)
    _apply_theme_colors()
    _apply_sidebar()

    # ===== Render inicial adiado + captura de exceções =====
    def _safe_render_inicial():
        try:
            print("[APP] render inicial", flush=True)
            render(current_key)
            print("[APP] render OK", flush=True)
        except Exception:
            err = traceback.format_exc()
            print("[APP][EXC] durante render inicial:\n" + err, flush=True)
            host.content = ft.Container(padding=20, content=ft.Text(err, color="#B00020", selectable=True))
            page.update()

    # Compatível com Flet 0.28.3
    page.run_task(_safe_render_inicial)

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        assets_dir=str(ROOT),   # ok manter para seus assets
        # não force web_renderer aqui
    )
