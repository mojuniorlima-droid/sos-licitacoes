import flet as ft

# -----------------------------
# THEME: tenta importar; se não houver, usa fallback embutido (sem ft.colors)
# -----------------------------
try:
    from theme import apply_modern_theme as _apply_modern_theme_external  # type: ignore
except Exception:
    _apply_modern_theme_external = None

def apply_modern_theme(page: ft.Page):
    """
    Fallback de tema caso theme.apply_modern_theme não exista.
    Não usa ft.colors/ft.Colors para evitar incompatibilidades.
    """
    if _apply_modern_theme_external:
        try:
            return _apply_modern_theme_external(page)  # usa o do projeto, se existir
        except Exception:
            pass

    # Fallback simples: só define Theme Material 3 e brilho.
    if page.theme_mode == ft.ThemeMode.DARK:
        page.theme = ft.Theme(use_material3=True, brightness=ft.Brightness.DARK)
    else:
        page.theme = ft.Theme(use_material3=True, brightness=ft.Brightness.LIGHT)

    # Em desktop, window_bgcolor pode existir; em web, ignore.
    try:
        page.window_bgcolor = None
    except Exception:
        pass


# -----------------------------
# Fallbacks para componentes opcionais (não quebrar se faltar arquivo)
# -----------------------------
try:
    from components.alerts_bell import AlertsBell  # type: ignore
except Exception:
    def AlertsBell(page: ft.Page, alerts_modal=None) -> ft.Control:
        return ft.IconButton(icon=ft.icons.NOTIFICATIONS, tooltip="Alertas")

try:
    from components.alerts_modal import build_alerts_modal  # type: ignore
except Exception:
    def build_alerts_modal(page: ft.Page):
        def open_modal(_=None):
            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Alertas"),
                content=ft.Text("Sem alertas no momento."),
                actions=[ft.TextButton("Fechar", on_click=lambda e: close_modal(dlg))],
                actions_alignment="end",
            )
            page.dialog = dlg
            dlg.open = True
            page.update()
        def close_modal(dlg):
            dlg.open = False
            page.update()
        return type("AlertsModalStub", (), {"open": open_modal})()


# -----------------------------
# APP
# -----------------------------
def main(page: ft.Page):
    # Web-friendly
    page.scroll = "none"  # string em 0.28.3
    page.theme_mode = ft.ThemeMode.LIGHT
    apply_modern_theme(page)

    # Estado simples
    sidebar_expanded = True
    alerts_modal = build_alerts_modal(page)

    # Ícone de tema (troca ao alternar)
    theme_icon = ft.IconButton(
        icon=ft.icons.DARK_MODE,
        tooltip="Alternar tema",
        on_click=lambda e: toggle_theme(),
    )

    # -------- Modais padrão (Sobre)
    def show_about(e):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sobre o Programa de Licitação", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Text(
                "Sistema de apoio e gestão de processos licitatórios.\n"
                "Python + Flet 0.28.3 — compatível com Web e Desktop."
            ),
            actions=[ft.TextButton("Fechar", on_click=lambda _: close_dialog(dlg))],
            actions_alignment="end",
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def close_dialog(dlg):
        dlg.open = False
        page.update()

    # -------- Navegação (lazy import das páginas)
    content_area = ft.Container(expand=True)

    def navigate(route: str):
        try:
            module = __import__(f"pages.{route}", fromlist=["view"])
            content_area.content = module.view(page)  # padrão: def view(page) -> Control
        except Exception as ex:
            content_area.content = ft.Text(f"Erro ao abrir {route}: {ex}")
        page.update()

    # -------- Header (sem paddings negativos, web-safe)
    def build_header():
        left = ft.Row(
            [
                ft.Image(src="assets/icons/sos_licitacoes.png", width=32, height=32),
                ft.Text("S.O.S Licitações", size=20, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=10,
        )
        right = ft.Row(
            [
                theme_icon,
                ft.IconButton(icon=ft.icons.INFO_OUTLINED, tooltip="Sobre", on_click=show_about),
                AlertsBell(page, alerts_modal),
            ],
            alignment=ft.MainAxisAlignment.END,
            spacing=5,
        )
        return ft.Container(
            content=ft.Row(
                [left, right],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            height=60,
        )

    # -------- Sidebar colapsável (mesma essência; textos somem no colapso)
    def build_sidebar():
        nonlocal sidebar_expanded

        def toggle_sidebar(e):
            nonlocal sidebar_expanded
            sidebar_expanded = not sidebar_expanded
            rebuild()

        menu_items = [
            ("dashboard", ft.icons.DASHBOARD, "Dashboard"),
            ("empresas", ft.icons.BUSINESS, "Empresas"),
            ("licitacoes", ft.icons.LIST_ALT, "Licitações"),
            ("certidoes", ft.icons.DESCRIPTION, "Certidões"),
            ("banco_precos", ft.icons.ATTACH_MONEY, "Banco de Preços"),
            ("edital_chat", ft.icons.CHAT, "Chat Edital"),
            ("oportunidades", ft.icons.STAR, "Oportunidades"),
        ]

        items: list[ft.Control] = [
            ft.IconButton(icon=ft.icons.MENU, on_click=toggle_sidebar, tooltip="Menu"),
            ft.Divider(),
        ]
        for route, icon, label in menu_items:
            if sidebar_expanded:
                items.append(
                    ft.ListTile(
                        leading=ft.Icon(icon),
                        title=ft.Text(label),
                        on_click=lambda e, r=route: navigate(r),
                    )
                )
            else:
                items.append(
                    ft.IconButton(icon=icon, tooltip=label, on_click=lambda e, r=route: navigate(r))
                )

        return ft.Container(
            content=ft.Column(items, expand=True, spacing=2),
            width=200 if sidebar_expanded else 68,
            padding=10,
        )

    # -------- Tema
    def toggle_theme():
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            theme_icon.icon = ft.icons.LIGHT_MODE
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_icon.icon = ft.icons.DARK_MODE
        apply_modern_theme(page)
        page.update()

    # -------- Rebuild layout
    def rebuild():
        page.controls.clear()
        page.add(
            ft.Row(
                [
                    build_sidebar(),
                    ft.Column([build_header(), content_area], expand=True),
                ],
                expand=True,
            )
        )
        page.update()

    # Inicializa na Dashboard
    navigate("dashboard")
    rebuild()


if __name__ == "__main__":
    ft.app(target=main)
