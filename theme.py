# === theme.py — Flet 0.28.x (tema claro/escuro com persistência) ===
import flet as ft

_STORAGE_KEY = "theme_mode"  # "light" | "dark"

def _current_pref(page: ft.Page) -> str:
    try:
        v = page.client_storage.get(_STORAGE_KEY)
        if v in ("light", "dark"):
            return v
    except Exception:
        pass
    return "dark"  # padrão do app

def _apply_palette(page: ft.Page, mode: str):
    # Material 3 + paleta coerente pros dois modos
    page.theme = ft.Theme(use_material3=True)
    page.theme_mode = ft.ThemeMode.DARK if mode == "dark" else ft.ThemeMode.LIGHT

def apply_theme(page: ft.Page) -> None:
    mode = _current_pref(page)
    _apply_palette(page, mode)
    page.update()

def build_theme_toggle(page: ft.Page) -> ft.IconButton:
    # estado inicial pelo storage
    mode = _current_pref(page)

    def _toggle(_):
        new_mode = "light" if page.theme_mode == ft.ThemeMode.DARK else "dark"
        _apply_palette(page, new_mode)
        try:
            page.client_storage.set(_STORAGE_KEY, new_mode)
        except Exception:
            pass
        page.update()

    # ícone condizente com o modo atual
    icon = ft.Icons.DARK_MODE if mode == "dark" else ft.Icons.LIGHT_MODE
    btn = ft.IconButton(icon=icon, tooltip="Alternar tema", on_click=_toggle)
    # muda o ícone sempre que a página atualizar de modo
    def _sync_icon():
        btn.icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.LIGHT_MODE
    page.on_view_pop = lambda e: None  # só pra manter referência
    # fazemos um pequeno hook visual quando o botão é clicado
    def _on_click(e):
        _toggle(e)
        _sync_icon()
    btn.on_click = _on_click

    # garantir ícone correto no primeiro paint
    _apply_palette(page, mode)
    _sync_icon()
    return btn
