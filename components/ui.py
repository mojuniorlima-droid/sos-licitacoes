# === components/ui.py ===
import flet as ft
from services.storage import LOGO_PNG

def kpi_card(title: str, value: str, icon: str, color=ft.Colors.BLUE) -> ft.Container:
    return ft.Container(
        bgcolor=color,
        border_radius=16,
        padding=16,
        expand=True,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(title, size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE70),
                        ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                ),
                ft.Icon(icon, size=28, color=ft.Colors.WHITE),
            ],
        ),
    )

def section_card(title: str, child: ft.Control) -> ft.Container:
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        border_radius=16,
        padding=16,
        content=ft.Column(
            spacing=12,
            controls=[ft.Text(title, size=14, weight=ft.FontWeight.W_700), child],
        ),
    )

def app_header(page: ft.Page, title: str, on_refresh=None) -> ft.Row:
    theme_icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
    left = ft.Row(
        spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Image(src="logo.png" if LOGO_PNG else "", width=28, height=28),
            ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
        ],
    )
    right = ft.Row(
        spacing=8,
        controls=[
            ft.ElevatedButton("Atualizar", icon=ft.Icons.REFRESH, on_click=lambda e: on_refresh() if on_refresh else None),
            ft.IconButton(
                icon=theme_icon, tooltip="Alternar tema",
                on_click=lambda e: _toggle_theme(page),
            ),
        ],
    )
    return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[left, right])

def zebra_datatable(columns: list[str]) -> ft.DataTable:
    return ft.DataTable(
        columns=[ft.DataColumn(ft.Text(h)) for h in columns],
        rows=[],
        data_row_color=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
        divider_thickness=0,
        show_bottom_border=True,
        heading_row_color=ft.Colors.with_opacity(0.06, ft.Colors.PRIMARY),
        column_spacing=18,
    )

def _toggle_theme(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
    page.update()

def _chain_resize(page: ft.Page, fn):
    """Anexa um callback ao on_resize existente (sem sobrescrever o anterior)."""
    prev = getattr(page, "on_resize", None)
    def handler(e):
        if prev:
            try:
                prev(e)
            except TypeError:
                prev()
        fn(e)
    page.on_resize = handler

def data_area(page: ft.Page, child: ft.Control, minus: int = 220, min_height: int = 240) -> ft.Container:
    """
    Painel padrão para tabelas/listas (os "quadros").
    - minus: quanto descontar da altura da janela (header, filtros, etc.)
    - min_height: altura mínima do painel
    """
    box = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        border_radius=12,
        padding=12,
        content=child,
        height=max(min_height, page.window_height - minus),
    )

    def _resize(_):
        box.height = max(min_height, page.window_height - minus)
        box.update()

    _chain_resize(page, _resize)
    return box

# exporta símbolos para importadores (Pylance para de reclamar)
__all__ = ["data_area", "_chain_resize"]
