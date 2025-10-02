from __future__ import annotations
import flet as ft
from pathlib import Path
import importlib

# === IMPORTS DO ALERTAS (NOVOS) ===
from components.alerts_modal import AlertsModal
from components.alerts_bell import build_alerts_bell
# ==================================

# ---------------- SHIMS ----------------
if not hasattr(ft, "colors"):
    class _ColorsShim:
        def __getattr__(self, name): return "#000000"
        def __getitem__(self, key):   return "#000000"
    ft.colors = _ColorsShim()
if not hasattr(ft, "Colors"):
    ft.Colors = ft.colors

NAV = [
    ("dashboard",        "Dashboard",        ft.Icons.INSIGHTS),
    ("empresas",         "Empresas",         ft.Icons.BUSINESS),
    ("licitacoes",       "Licitações",       ft.Icons.DESCRIPTION),
    ("certidoes",        "Certidões",        ft.Icons.VERIFIED),
    ("banco_precos",     "Banco de Preços",  ft.Icons.TABLE_CHART),
    ("edital_chat",      "Chat Edital",      ft.Icons.CHAT),
    ("oportunidades",    "Oportunidades",    ft.Icons.WORK_HISTORY),
]

def _page_factory(module_name: str):
    mod = importlib.import_module(module_name)
    base = module_name.split(".")[-1]
    for fname in ("build", "view", "page", "app", f"page_{base}", f"{base}_page"):
        if hasattr(mod, fname):
            return getattr(mod, fname)
    raise AttributeError(f"Módulo {module_name} não possui função fábrica compatível.")

PAGES = {k: _page_factory(f"pages.{k}") for (k, _label, _icon) in NAV}

# --------- compat on_resize ----------
def _install_resize_bridge(page: ft.Page):
    if not hasattr(page, "on_resize"):
        page.on_resize = None
    def _sync_dims():
        try:
            page.window_height = getattr(page.window, "height", None) or getattr(page, "height", None)
            page.window_width  = getattr(page.window, "width",  None) or getattr(page, "width",  None)
        except Exception:
            pass
    prev = getattr(page, "on_resized", None)
    def _bridge(e=None):
        _sync_dims()
        cb = getattr(page, "on_resize", None)
        if callable(cb):
            try: cb(e)
            except Exception: pass
        if prev:
            try: prev()
            except TypeError:
                try: prev(e)
                except Exception: pass
    _sync_dims()
    page.on_resized = _bridge

# ---------- PALETA ----------
LIGHT_BG        = "#FFFFFF"
LIGHT_SURFACE   = "#FFFFFF"
LIGHT_TEXT      = "#222222"
LIGHT_TEXT_DIM  = "#666666"
LIGHT_ACCENT    = "#0D47A1"
LIGHT_DIVIDER   = "#E0E0E0"
LIGHT_OVERLAY   = "#E0E0E0"

DARK_BG         = "#0B1220"
DARK_SURFACE    = "#101826"
DARK_TEXT       = "#EAF2FF"
DARK_TEXT_DIM   = "#B7C1D6"
DARK_ACCENT     = "#4EA1FF"
DARK_DIVIDER    = "#2A3A50"
DARK_OVERLAY    = "#1E2A3B"

# ---------- APP ----------
def main(page: ft.Page):
    here = Path(__file__).resolve().parent
    page.assets_dir = str(here)
    page.title = "Programa de Licitação"
    page.theme_mode = ft.ThemeMode.LIGHT

    page.padding = 0
    page.spacing = 0
    page.bgcolor = LIGHT_BG
    try: page.window_bgcolor = LIGHT_BG
    except Exception: pass

    # --- Fallback: cria logo.ico multi-tamanhos a partir de uma imagem existente, se possível ---
    def _ensure_multi_size_ico(root_dir: Path) -> None:
        try:
            from PIL import Image  # Pillow opcional
        except Exception:
            return
        try:
            ico_path = root_dir / "logo.ico"
            if ico_path.exists(): return
            candidates = [
                root_dir / "logo.png",
                root_dir / "assets" / "icons" / "sos_licitacoes_256.png",
                root_dir / "assets" / "icons" / "sos_licitacoes_128.png",
                root_dir / "assets" / "icons" / "sos_licitacoes_64.png",
                root_dir / "assets" / "icons" / "sos_licitacoes_48.png",
            ]
            base_img = next((p for p in candidates if p.exists()), None)
            if not base_img: return
            sizes = [(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(128,128),(256,256)]
            with Image.open(base_img) as im:
                im = im.convert("RGBA")
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

    # --------- LOGO DO TOPO (S.O.S Licitações) ---------
    logo_src, logo_h = None, 150
    if (here / "assets/icons/sos_licitacoes_256.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_256.png", 150
    elif (here / "assets/icons/sos_licitacoes_128.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_128.png", 84
    elif (here / "assets/icons/sos_licitacoes_64.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_64.png", 64
    elif (here / "assets/icons/sos_licitacoes_48.png").exists():
        logo_src, logo_h = "assets/icons/sos_licitacoes_48.png", 48
    else:
        logo_src, logo_h = "logo.png", 64  # fallback

    # ---------- helpers compat ----------
    def _open_dialog(dlg: ft.AlertDialog):
        try:
            page.open(dlg)
        except Exception:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def _close_dialog(dlg: ft.AlertDialog):
        try:
            page.close(dlg)
        except Exception:
            dlg.open = False
            page.update()

    # ---------- SOBRE ----------
    sos_tech_logo = "logo_sos_tech.png" if (here / "logo_sos_tech.png").exists() else logo_src
    def open_about(e=None):
        vw = int(getattr(page, "window_width", None) or getattr(page, "width", 1200) or 1200)
        dlg_w = max(360, min(520, int(vw * 0.55)))
        body = ft.Container(
            width=dlg_w,
            padding=ft.padding.all(20),
            content=ft.Column(
                spacing=12,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Image(src=sos_tech_logo, height=256, fit=ft.ImageFit.CONTAIN, filter_quality=ft.FilterQuality.HIGH),
                    ft.Text("Programa de Licitação — S.O.S Tech", size=16, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                    ft.Text("Versão: 1.0.0", size=14, text_align=ft.TextAlign.CENTER),
                    ft.Text("Desenvolvido por: Fabio Júnior", size=14, text_align=ft.TextAlign.CENTER),
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6, controls=[ft.Icon(ft.Icons.LINK, size=18, color=ft.colors.BLUE), ft.Text("Instagram: @s.o.s_teech", size=14)]),
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6, controls=[ft.Icon(ft.Icons.PHONE, size=18, color=ft.colors.GREEN), ft.Text("WhatsApp: (91) 93300-2999", size=14)]),
                ],
            ),
        )
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sobre o Programa", weight=ft.FontWeight.W_700, size=18, text_align=ft.TextAlign.CENTER),
            content=body,
            actions=[ft.TextButton("Fechar")],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg.actions[0].on_click = lambda ev: _close_dialog(dlg)
        _open_dialog(dlg)

    about_btn = ft.IconButton(icon=ft.Icons.INFO, tooltip="Sobre", on_click=open_about)

    # ---------- BOTÃO TEMA ----------
    theme_btn = ft.IconButton(icon=ft.Icons.WB_SUNNY, tooltip="Alternar tema")
    def _refresh_theme_button():
        theme_btn.icon = ft.Icons.WB_SUNNY if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.DARK_MODE

    # ---------- ALERTAS (instância do modal + sininho com badge) ----------
    alerts_modal = AlertsModal(page)
    alerts_bell  = build_alerts_bell(page, alerts_modal)

    # ---------- HEADER (mantém sininho) ----------
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
                        ft.Image(src=logo_src, height=logo_h, fit=ft.ImageFit.CONTAIN, filter_quality=ft.FilterQuality.HIGH, tooltip="S.O.S Licitações"),
                        ft.Text("PROGRAMA DE LICITAÇÃO", weight=ft.FontWeight.W_700, size=15),
                    ],
                ),
                # << mantém apenas o sininho aqui >>
                ft.Row(controls=[alerts_bell]),
            ],
        ),
    )
    title = header.content.controls[0].controls[1]

    # ---------- CONTEÚDO ----------
    host = ft.Container(expand=True)
    content = ft.Container(expand=True, bgcolor=SURFACE(), padding=10, content=host)

    def _view_of(key: str):
        try:
            v = PAGES[key](page)
        except Exception as ex:
            v = ft.Container(padding=20, bgcolor=SURFACE(), content=ft.Text(f"Erro ao montar página '{key}': {ex}", color="#B00020"))
        return v if isinstance(v, ft.Control) else ft.Column(controls=[v], expand=True)

    current_key = NAV[0][0]

    # ======== BARRA LATERAL (colapsável) ========
    nav_collapsed = {"value": False}  # estado mutável simples

    def _make_nav_button(key: str, label: str, icon):
        # Quando colapsada: mostra só o ícone com tooltip
        if nav_collapsed["value"]:
            return ft.IconButton(
                icon=icon,
                tooltip=label,
                icon_size=22,
                on_click=lambda e: render(key),
                style=ft.ButtonStyle(overlay_color=OVERLAY(), padding=ft.padding.symmetric(6, 6)),
                data=key,
            )
        else:
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

    nav_buttons = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
    def _rebuild_nav_buttons():
        nav_buttons.controls = [_make_nav_button(k, lbl, ic) for (k, lbl, ic) in NAV]

    # Toggle colapso
    def _toggle_sidebar(e=None):
        nav_collapsed["value"] = not nav_collapsed["value"]
        _rebuild_nav_buttons()
        _apply_theme_colors()  # re-colore ícones/labels
        _update_sidebar_width()
        page.update()

    collapse_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT, tooltip="Recolher/Expandir",
        on_click=_toggle_sidebar, style=ft.ButtonStyle(overlay_color=OVERLAY()),
    )

    # Rodapé da barra: Tema + Sobre
    sidebar_footer = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN if not nav_collapsed["value"] else ft.MainAxisAlignment.CENTER,
        controls=[theme_btn, about_btn],
    )

    # Container da barra lateral
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
                ft.Container(expand=True),  # empurra o footer para baixo
                sidebar_footer,
            ],
        ),
        bgcolor=SURFACE(),
        width=240,  # ajustado dinamicamente
    )

    # Área central: sidebar | divisor vertical | conteúdo
    v_divider = ft.Container(width=1, bgcolor=LIGHT_DIVIDER, height=1)  # altura é ajustada pelo layout

    body = ft.Row(expand=True, spacing=0, controls=[sidebar, v_divider, content])

    # ---------- render / tema ----------
    def _update_sidebar_width():
        sidebar.width = 68 if nav_collapsed["value"] else 240
        collapse_btn.icon = ft.Icons.CHEVRON_RIGHT if nav_collapsed["value"] else ft.Icons.CHEVRON_LEFT
        # alinhamento do footer
        sidebar_footer.alignment = ft.MainAxisAlignment.CENTER if nav_collapsed["value"] else ft.MainAxisAlignment.SPACE_BETWEEN

    def render(key: str):
        nonlocal current_key
        current_key = key
        host.content = _view_of(key)
        # Atualiza seleção visual
        for btn in nav_buttons.controls:
            sel = (btn.data == current_key)
            if isinstance(btn, ft.TextButton):
                lbl = btn.content.controls[1]
                icn = btn.content.controls[0]
                lbl.weight = ft.FontWeight.W_700 if sel else ft.FontWeight.W_400
                lbl.color  = ACCENT() if sel else TXT()
                icn.color  = ACCENT() if sel else TXT()
            else:
                # IconButton (colapsado): só cor
                btn.icon_color = ACCENT() if sel else TXT()
        try:
            alerts_bell.refresh_badge()
        except Exception:
            pass
        page.update()

    def _apply_theme_colors():
        page.bgcolor = BG()
        try: page.window_bgcolor = BG()
        except Exception: pass

        root.bgcolor = BG()
        header.bgcolor = SURFACE()
        title.color = TXT()

        # Sidebar + botões
        sidebar.bgcolor = SURFACE()
        for btn in nav_buttons.controls:
            if isinstance(btn, ft.TextButton):
                lbl = btn.content.controls[1]
                icn = btn.content.controls[0]
                lbl.color = TXT()
                icn.color = TXT()
            elif isinstance(btn, ft.IconButton):
                btn.icon_color = TXT()

        # Footer da barra
        for b in (theme_btn, about_btn, collapse_btn):
            try: b.style.overlay_color = OVERLAY()
            except Exception: pass

        # Divisor vertical
        v_divider.bgcolor = DIV()

        # Conteúdo
        content.bgcolor = SURFACE()

        _refresh_theme_button()

    def toggle_theme(e=None):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        _apply_theme_colors()
        render(current_key)

    _rebuild_nav_buttons()
    _update_sidebar_width()

    root = ft.Container(
        expand=True,
        bgcolor=BG(),
        content=ft.Column(expand=True, spacing=0, controls=[header, body]),
    )

    page.add(root)
    _apply_theme_colors()
    theme_btn.on_click = toggle_theme
    render(current_key)

from pathlib import Path

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        assets_dir=str(ROOT),
        web_renderer="html",
    )
