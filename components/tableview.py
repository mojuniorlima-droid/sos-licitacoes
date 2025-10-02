from __future__ import annotations
import flet as ft

class SimpleTable:
    """
    Tabela simples e estável para Flet 0.28.3.
    - Sem ListView/expand que cubra o cabeçalho.
    - Altura controlada, borda sutil e LARGURA 100%.
    """
    def __init__(self, headers, include_master=True, zebra=True, height=400):
        self.headers = list(headers)
        self.include_master = include_master
        self.zebra = zebra
        self.height = height

        self._rows_data: list[dict] = []
        self._selected_ids: set = set()

        self._dt: ft.DataTable | None = None
        self._container: ft.Container | None = None
        self._master_cb: ft.Checkbox | None = ft.Checkbox(value=False) if include_master else None
        if self._master_cb:
            self._master_cb.on_change = self._on_master_toggle

    # -------- API pública --------
    def control(self) -> ft.Control:
        self._build()
        return self._container

    def set_rows(self, rows: list[dict]):
        self._rows_data = rows or []
        alive = {r.get("id") for r in self._rows_data if "id" in r}
        self._selected_ids = {rid for rid in self._selected_ids if rid in alive}
        self._refresh()

    def selected_ids(self) -> list:
        return list(self._selected_ids)

    def select_all(self):
        self._selected_ids = {r.get("id") for r in self._rows_data if r.get("id") is not None}
        self._refresh()

    def clear_selection(self):
        self._selected_ids.clear()
        self._refresh()

    def set_height(self, h: int):
        self.height = max(160, int(h))
        if self._container:
            self._container.height = self.height
            try: self._container.update()
            except Exception: pass

    # -------- construção interna --------
    def _build(self):
        cols = []
        if self.include_master and self._master_cb:
            cols.append(ft.DataColumn(ft.Row(controls=[self._master_cb])))
        for h in self.headers:
            cols.append(ft.DataColumn(ft.Text(h, weight=ft.FontWeight.BOLD)))

        self._dt = ft.DataTable(
            columns=cols,
            rows=[],
            heading_row_height=42,
            data_row_min_height=38,
            data_row_max_height=48,
            divider_thickness=0.6,
            show_checkbox_column=False,
        )

        # Importante: expand=True para preencher a LARGURA.
        self._container = ft.Container(
            expand=True,                 # <<<<<< ocupa 100% da largura do pai
            height=self.height,
            padding=8,
            bgcolor=ft.Colors.with_opacity(0.015, ft.Colors.ON_SURFACE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)),
            border_radius=10,
            content=self._dt,
        )
        self._refresh()

    def _refresh(self):
        if not self._dt:
            return
        rows = []
        alt = False
        for r in self._rows_data:
            rid = r.get("id")
            cb = ft.Checkbox(value=(rid in self._selected_ids))
            cb.on_change = self._mk_row_toggle(rid)

            cells = []
            if self.include_master:
                cells.append(ft.DataCell(cb))
            for h in self.headers:
                cells.append(ft.DataCell(ft.Text(str(r.get(h, "")))))

            color = ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE) if (self.zebra and alt) else None
            alt = not alt
            rows.append(ft.DataRow(cells=cells, color=color))

        self._dt.rows = rows
        try: self._dt.update()
        except Exception: pass
        self._update_master_cb()

    def _mk_row_toggle(self, rid):
        def _h(e):
            if rid is None:
                return
            if e.control.value:
                self._selected_ids.add(rid)
            else:
                self._selected_ids.discard(rid)
            self._update_master_cb()
        return _h

    def _on_master_toggle(self, e):
        if not self._rows_data:
            if self._master_cb:
                self._master_cb.value = False
                try: self._master_cb.update()
                except Exception: pass
            return
        if self._master_cb and self._master_cb.value:
            self.select_all()
        else:
            self.clear_selection()

    def _update_master_cb(self):
        if not (self.include_master and self._master_cb):
            return
        total = len([r for r in self._rows_data if r.get("id") is not None])
        sel = len(self._selected_ids)
        want = (sel > 0 and sel == total) if total else False
        if self._master_cb.value != want:
            self._master_cb.value = want
            try: self._master_cb.update()
            except Exception: pass
