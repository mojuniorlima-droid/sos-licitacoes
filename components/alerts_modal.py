from __future__ import annotations
import flet as ft

# Compat Flet 0.28.x — abrir/fechar via page.open()/page.close() com fallback

BADGE_RADIUS = 999

def _badge(text: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        bgcolor=color,
        border_radius=BADGE_RADIUS,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )

def _pill(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=12, weight=ft.FontWeight.W_500),
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
        border_radius=BADGE_RADIUS,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )

def _section_title(title: str, right_content: ft.Control | None = None) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Text(title, size=14, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            right_content or ft.Container(),
        ],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

def _hint(text: str) -> ft.Text:
    return ft.Text(text, size=12, color=ft.Colors.GREY, italic=True)

def _divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLACK))

class AlertsModal:
    """
    Modal de Alertas:
    - Licitações: leve ≤7d, moderado ≤3d, urgente ≤1d (inclui vencidos)
    - Certidões:  leve ≤15d, moderado ≤7d, urgente ≤1d (inclui vencidos)
    - Scroll único usando ListView (não acumula barras)
    """
    def __init__(self, page: ft.Page):
        self.page = page

        # Lista com rolagem única e altura fixa (evita barras duplicadas)
        self._list = ft.ListView(
            spacing=12,
            auto_scroll=False,
            height=440,         # ajuste se quiser mais/menos alto
            controls=[],
        )

        header = ft.Row(
            controls=[
                ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED),
                ft.Text("Alertas", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Recarregar",
                    on_click=self._on_refresh_click,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        footer = ft.Row(
            controls=[
                ft.Container(expand=True),
                ft.OutlinedButton("Fechar", on_click=self._on_close_click),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        body = ft.Container(
            content=ft.Column(
                controls=[header, _divider(), self._list, _divider(), footer],
                spacing=12,
            ),
            padding=ft.padding.all(16),
            width=680,
        )

        self.dialog = ft.AlertDialog(content=body, modal=True)

    # --------- handlers ----------
    def _on_refresh_click(self, e=None):
        self.load()

    def _on_close_click(self, e=None):
        self.close()

    # --------- API pública ----------
    def open(self):
        try:
            self.page.open(self.dialog)
        except Exception:
            try:
                self.page.dialog = self.dialog
                self.dialog.open = True
                self.page.update()
            except Exception:
                self.dialog.open = True
                self.page.update()
        self.load()

    def close(self):
        # tenta fechar do jeito "oficial"
        try:
            self.page.close(self.dialog)
        except Exception:
            pass
        # garante o fechamento mesmo em versões antigas
        try:
            self.dialog.open = False
            self.page.update()
        except Exception:
            pass

    def load(self):
        # zera a lista (um único scroll sempre)
        self._list.controls.clear()

        # Estruturas no padrão ("urgente")
        lic_counts = {"leve": 0, "moderado": 0, "urgente": 0}
        cer_counts = {"leve": 0, "moderado": 0, "urgente": 0}
        lic_items = {"leve": [], "moderado": [], "urgente": []}
        cer_items = {"leve": [], "moderado": [], "urgente": []}

        # Busca via services.alerts (preferencial)
        try:
            from services.alerts import list_alertas_licitacoes, list_alertas_certidoes  # type: ignore
            lic = list_alertas_licitacoes() or {}
            cer = list_alertas_certidoes() or {}

            # compat se vier "pesado"
            def _normalize(d: dict):
                if "pesado" in d and "urgente" not in d:
                    d["urgente"] = d.get("pesado") or []
                d.setdefault("leve", [])
                d.setdefault("moderado", [])
                d.setdefault("urgente", [])
                return d

            lic = _normalize(lic)
            cer = _normalize(cer)

            for k in ["urgente", "moderado", "leve"]:
                lic_items[k] = lic.get(k, []) or []
                cer_items[k] = cer.get(k, []) or []
                lic_counts[k] = len(lic_items[k])
                cer_counts[k] = len(cer_items[k])

        except Exception:
            # Fallback: services.db antigo (leve/moderado/pesado)
            try:
                import services.db as db  # type: ignore
                if hasattr(db, "list_alertas_licitacoes"):
                    lic_old = db.list_alertas_licitacoes() or {}
                    lic_items["leve"]     = lic_old.get("leve", []) or []
                    lic_items["moderado"] = lic_old.get("moderado", []) or []
                    lic_items["urgente"]  = lic_old.get("pesado", []) or []
                if hasattr(db, "list_alertas_certidoes"):
                    cer_old = db.list_alertas_certidoes() or {}
                    cer_items["leve"]     = cer_old.get("leve", []) or []
                    cer_items["moderado"] = cer_old.get("moderado", []) or []
                    cer_items["urgente"]  = cer_old.get("pesado", []) or []
                for k in ["urgente", "moderado", "leve"]:
                    lic_counts[k] = len(lic_items[k])
                    cer_counts[k] = len(cer_items[k])
            except Exception:
                pass

        # --- Montagem do conteúdo na ListView ---
        # Licitações
        lic_badges = ft.Row(
            controls=[
                _badge(f"Urgente (≤1d): {lic_counts['urgente']}", ft.Colors.RED),
                _badge(f"Moderado (≤3d): {lic_counts['moderado']}", ft.Colors.AMBER),
                _badge(f"Leve (≤7d): {lic_counts['leve']}", ft.Colors.BLUE),
            ],
            spacing=8,
            wrap=True,
        )
        self._list.controls += [
            _section_title("Licitações", lic_badges),
            _hint("Regras: urgente 1 dia (inclui vencidos) • moderado 3 dias • leve 7 dias"),
            self._make_list(lic_items, "Nenhuma licitação com prazo próximo."),
            _divider(),
        ]

        # Certidões
        cer_badges = ft.Row(
            controls=[
                _badge(f"Urgente (≤1d): {cer_counts['urgente']}", ft.Colors.RED),
                _badge(f"Moderado (≤7d): {cer_counts['moderado']}", ft.Colors.AMBER),
                _badge(f"Leve (≤15d): {cer_counts['leve']}", ft.Colors.BLUE),
            ],
            spacing=8,
            wrap=True,
        )
        self._list.controls += [
            _section_title("Certidões", cer_badges),
            _hint("Regras: urgente 1 dia (inclui vencidos) • moderado 7 dias • leve 15 dias"),
            self._make_list(cer_items, "Nenhuma certidão próxima do vencimento."),
        ]

        self.page.update()

    # --------- helpers de UI ----------
    def _make_list(self, items_by_level: dict[str, list], empty_text: str) -> ft.Container:
        rows: list[ft.Control] = []

        def section(level_name: str, color: str, items: list):
            rows.append(
                ft.Row(
                    controls=[
                        _pill(level_name.capitalize()),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, opacity=0.4),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
            if not items:
                rows.append(ft.Text("— sem itens —", size=12, color=ft.Colors.GREY))
                return
            for it in items:
                title = str(it.get("titulo") or it.get("descricao") or it.get("empresa_nome") or "Item")
                dias  = it.get("dias")
                right = ft.Row(
                    controls=[ft.Text(f"{dias} dia(s)", size=12, color=ft.Colors.GREY) if dias is not None else ft.Container()],
                    spacing=6,
                )
                rows.append(
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CIRCLE, size=6, color=color),
                            ft.Text(title, size=13),
                            ft.Container(expand=True),
                            right,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )

        # Ordem: urgente, moderado, leve
        section("urgente", ft.Colors.RED, items_by_level.get("urgente", []) or items_by_level.get("pesado", []))
        section("moderado", ft.Colors.AMBER, items_by_level.get("moderado", []))
        section("leve", ft.Colors.BLUE, items_by_level.get("leve", []))

        return ft.Container(content=ft.Column(rows, spacing=6, tight=True))
