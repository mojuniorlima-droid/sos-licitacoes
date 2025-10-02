# === components/badges.py ===
import flet as ft

def _chip(text: str, fg, bg) -> ft.Container:
    return ft.Container(
        bgcolor=bg,
        border_radius=20,
        padding=ft.Padding(10, 4, 10, 4),
        content=ft.Text(text, size=12, color=fg, weight=ft.FontWeight.BOLD),
    )

def badge_regular(text="Regular") -> ft.Container:
    return _chip(text, fg=ft.Colors.GREEN, bg=ft.Colors.with_opacity(0.12, ft.Colors.GREEN))

def badge_vencendo(text="Vencendo") -> ft.Container:
    return _chip(text, fg=ft.Colors.AMBER, bg=ft.Colors.with_opacity(0.12, ft.Colors.AMBER))

def badge_vencida(text="Vencida") -> ft.Container:
    return _chip(text, fg=ft.Colors.RED, bg=ft.Colors.with_opacity(0.12, ft.Colors.RED))

def badge_info(text: str) -> ft.Container:
    return _chip(text, fg=ft.Colors.BLUE, bg=ft.Colors.with_opacity(0.12, ft.Colors.BLUE))
