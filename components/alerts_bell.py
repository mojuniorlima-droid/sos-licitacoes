from __future__ import annotations
import flet as ft

def build_alerts_bell(page: ft.Page, modal) -> ft.Control:
    """
    Sininho com badge (bolinha). Compatível com Flet 0.28.x.
    O botão fica por cima no Stack para garantir o clique.
    Exponho bell.refresh_badge() para você chamar quando quiser.
    """
    # Badge (bolinha)
    badge_text = ft.Text("0", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    badge_box = ft.Container(
        content=badge_text,
        bgcolor=ft.Colors.RED,
        border_radius=999,
        padding=ft.padding.symmetric(horizontal=5, vertical=1),
        visible=False,  # some quando total == 0
    )

    def refresh_badge():
        total = 0
        try:
            from services.alerts import count_all  # type: ignore
            total = int(count_all() or 0)
        except Exception:
            total = 0
        badge_text.value = str(total if total <= 99 else "99+")
        badge_box.visible = total > 0
        try:
            page.update()
        except Exception:
            pass

    # Botão do sino (fica por cima no Stack)
    def on_click(e):
        modal.open()
        refresh_badge()

    bell_btn = ft.IconButton(
        icon=ft.Icons.NOTIFICATIONS_OUTLINED,
        tooltip="Alertas",
        on_click=on_click,
    )

    # Camada do badge no topo-direita
    badge_layer = ft.Container(
        width=40,
        height=40,
        alignment=ft.alignment.top_right,
        content=badge_box,
    )

    # Importante: o botão vem por último (renderiza por cima e recebe o clique)
    bell_stack = ft.Stack(
        controls=[badge_layer, bell_btn],
        width=40,
        height=40,
    )

    # Atualiza badge na criação
    refresh_badge()

    # Expor método para uso externo (ex.: ao trocar de página)
    setattr(bell_stack, "refresh_badge", refresh_badge)

    return bell_stack
