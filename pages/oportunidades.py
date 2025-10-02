# === pages/oportunidades.py — PNCP integrado (multi-seleção simulada com Dropdown custom) ===
from __future__ import annotations
import flet as ft
from typing import List, Dict, Any

# 🔒 PNCP
try:
    import services.pncp as pncp
except Exception:
    class _PNCPStub:
        def buscar(self, *a, **k): return []
    pncp = _PNCPStub()

# 🔒 exports
try:
    from services.exports import export_csv, export_xlsx
except Exception:
    def export_csv(*a, **k): return False
    def export_xlsx(*a, **k): return False

# 🔒 SimpleTable
try:
    from components.tableview import SimpleTable
except Exception:
    class SimpleTable(ft.UserControl):
        def build(self): return ft.Container(ft.Text("Tabela indisponível"))


def build(page: ft.Page):
    return ft.Container(
        padding=20,
        content=ft.Text("Oportunidades — em construção", size=16, weight=ft.FontWeight.W_600),
    )


BASE_DESCONTO = -150

COLUMNS = [
    "ID","UF","Município","Órgão","Objeto","Sessão","Valor","Link","Edital",
]

UF_ITEMS = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
    "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
]
PRESETS_MUNICIPIOS = ["Belém","Castanhal","Marabá","Ananindeua","Parauapebas","Santarém"]
PRESETS_ORGAOS = ["Prefeitura Municipal","Governo do Estado","UFPA","IFPA"]


def page_oportunidades(page: ft.Page) -> ft.Control:
    try:
        saved = pncp.load_saved_filters() or {}
    except Exception:
        saved = {}

    # ------------------- MULTI-SELEÇÃO COM POPUP -------------------
    cb_ufs = [ft.Checkbox(label=f"UF: {uf}", value=(uf in (saved.get("ufs") or []))) for uf in UF_ITEMS]
    cb_muns = [ft.Checkbox(label=f"Município: {m}", value=(m in (saved.get("municipios") or []))) for m in PRESETS_MUNICIPIOS]
    cb_orgs = [ft.Checkbox(label=f"Órgão: {o}", value=(o in (saved.get("orgaos") or []))) for o in PRESETS_ORGAOS]

    all_checkboxes = cb_ufs + cb_muns + cb_orgs

    dropdown_display = ft.TextField(
        label="Filtros (UFs, Municípios, Órgãos)",
        value="Nenhum selecionado",
        read_only=True,
        width=350,
        suffix_icon=ft.Icons.ARROW_DROP_DOWN,  # ✅ ajuste aqui
        on_click=lambda e: toggle_popup(True)
    )

    popup = ft.Container(
        bgcolor=ft.Colors.SURFACE,
        border_radius=6,
        padding=10,
        visible=False,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=all_checkboxes + [
                ft.ElevatedButton("OK", on_click=lambda e: toggle_popup(False))
            ],
        ),
        width=350,
        height=300
    )

    def toggle_popup(show: bool):
        popup.visible = show
        if not show:
            update_dropdown_text()
        page.update()

    def update_dropdown_text():
        selected = [c.label for c in all_checkboxes if c.value]
        if not selected:
            dropdown_display.value = "Nenhum selecionado"
        elif len(selected) <= 3:
            dropdown_display.value = ", ".join(selected)
        else:
            dropdown_display.value = f"{len(selected)} selecionados"
        page.update()

    # ------------------- CAMPOS EXTRAS -------------------
    objeto = ft.TextField(label="Objeto (palavras-chave)", width=380, value=saved.get("objeto",""))
    data_ini = ft.TextField(label="Data inicial (dd/mm/aaaa)", width=160, value=saved.get("data_ini",""))
    data_fim = ft.TextField(label="Data final (dd/mm/aaaa)", width=160, value=saved.get("data_fim",""))

    tbl = SimpleTable(
        COLUMNS, include_master=True, zebra=True,
        height=max(240, page.window_height - BASE_DESCONTO)
    )
    lbl_status = ft.Text("", size=12)

    # ------------------- HELPERS -------------------
    def _current_filters() -> Dict[str, Any]:
        sel_ufs, sel_muns, sel_orgs = [], [], []
        for c in cb_ufs:
            if c.value: sel_ufs.append(c.label.replace("UF: ",""))
        for c in cb_muns:
            if c.value: sel_muns.append(c.label.replace("Município: ",""))
        for c in cb_orgs:
            if c.value: sel_orgs.append(c.label.replace("Órgão: ",""))
        return {
            "ufs": sel_ufs,
            "municipios": sel_muns,
            "orgaos": sel_orgs,
            "objeto": objeto.value or "",
            "data_ini": data_ini.value or "",
            "data_fim": data_fim.value or "",
        }

    def _adapt_rows(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        adapted = []
        for r in (raw or []):
            adapted.append({
                "id": r.get("id"),
                "ID": r.get("id"),
                "UF": r.get("uf",""),
                "Município": r.get("municipio",""),
                "Órgão": r.get("orgao",""),
                "Objeto": r.get("objeto",""),
                "Sessão": r.get("data_sessao",""),
                "Valor": r.get("valor_estimado",""),
                "Link": r.get("link",""),
                "Edital": "⭳",
                "_edital_url": r.get("edital_url",""),
            })
        return adapted

    # ------------------- AÇÕES -------------------
    def ac_buscar(_=None):
        lbl_status.value = "Buscando no PNCP…"
        page.update()
        try:
            filters = _current_filters()
            rows = pncp.search_opportunities(filters)
            tbl.set_rows(_adapt_rows(rows))
            lbl_status.value = f"{len(rows)} oportunidade(s) encontradas."
            page.update()
        except Exception as ex:
            lbl_status.value = f"Erro na busca: {ex}"
            page.update()

    def ac_salvar_filtro(_=None):
        try:
            pncp.save_filters(_current_filters())
            lbl_status.value = "Filtro salvo."
            page.update()
        except Exception as ex:
            lbl_status.value = f"Erro ao salvar filtro: {ex}"
            page.update()

    def ac_agendar(_=None):
        try:
            pncp.start_daily_job(hour=3, minute=0)  # 03:00
            lbl_status.value = "Agendado diário às 03:00."
            page.update()
        except Exception as ex:
            lbl_status.value = f"Erro ao agendar: {ex}"
            page.update()

    def ac_parar(_=None):
        try:
            pncp.stop_daily_job()
            lbl_status.value = "Agendamento parado."
            page.update()
        except Exception as ex:
            lbl_status.value = f"Erro ao parar: {ex}"
            page.update()

    def ac_baixar_edital(_=None):
        sel = tbl.selected_ids()
        if not sel:
            lbl_status.value = "Selecione ao menos 1 oportunidade."
            page.update()
            return
        count_ok = 0
        count_fail = 0
        for rid in sel:
            row = next((r for r in tbl._rows_data if r.get("id") == rid), None)
            if not row:
                count_fail += 1
                continue
            url = row.get("_edital_url")
            try:
                path = pncp.download_edital(url, oportunidade_id=rid)
            except Exception:
                path = None
            if path:
                count_ok += 1
            else:
                count_fail += 1
        lbl_status.value = f"Editais: baixados {count_ok}; falhas {count_fail}."
        page.update()

    # ------------------- EXPORT -------------------
    fp = ft.FilePicker()
    if fp not in page.overlay:
        page.overlay.append(fp)

    def export(kind: str):
        head = COLUMNS
        data = [{h: r.get(h, "") for h in head} for r in tbl._rows_data]
        if kind == "csv":
            fp.on_result = lambda e: export_csv(head, data, e.path) if e.path else None
            fp.save_file(file_name="oportunidades.csv")
        else:
            fp.on_result = lambda e: export_xlsx(head, data, e.path) if e.path else None
            fp.save_file(file_name="oportunidades.xlsx")

    # ------------------- UI -------------------
    filtros = ft.Column(spacing=10, controls=[
        ft.Text("Filtros do PNCP", size=18, weight=ft.FontWeight.BOLD),
        ft.Stack([dropdown_display, popup]),
        ft.Row(spacing=10, controls=[objeto, data_ini, data_fim]),
        ft.Row(spacing=8, controls=[
            ft.FilledButton("🔍 Buscar no PNCP", on_click=ac_buscar),
            ft.OutlinedButton("💾 Salvar filtro", on_click=ac_salvar_filtro),
            ft.OutlinedButton("⏱️ Agendar diário (03:00)", on_click=ac_agendar),
            ft.OutlinedButton("⏹️ Parar agendamento", on_click=ac_parar),
            ft.OutlinedButton("⭳ Baixar edital (selecionados)", on_click=ac_baixar_edital),
            ft.OutlinedButton("⭳ CSV", on_click=lambda e: export("csv")),
            ft.OutlinedButton("⭳ Excel", on_click=lambda e: export("xlsx")),
        ])
    ])

    tbl_header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Oportunidades (PNCP)", size=16, weight=ft.FontWeight.BOLD),
            ft.Row(spacing=8, controls=[
                ft.OutlinedButton("Selecionar todos", on_click=lambda e: (tbl.select_all(), page.update())),
                ft.OutlinedButton("Desmarcar", on_click=lambda e: (tbl.clear_selection(), page.update())),
                ft.IconButton(ft.Icons.REFRESH, on_click=lambda e: ac_buscar()),
            ]),
        ]
    )

    quadro = ft.Column(spacing=8, controls=[tbl_header, tbl.control()])

    footer = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
        border_radius=10,
        padding=ft.Padding(10, 8, 10, 8),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[lbl_status, ft.Text("Dica: use as caixas para seleção em massa.", size=12)],
        ),
    )

    layout = ft.Column(
        spacing=8,
        controls=[filtros, ft.Divider(height=1, thickness=1, color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)), quadro, footer],
    )

    # resize mantém a tabela proporcional
    prev = page.on_resize
    def _on_resize(e):
        try:
            if prev: prev(e)
        except TypeError:
            if prev: prev()
        nh = max(240, page.window_height - BASE_DESCONTO - 60)
        tbl.set_height(nh)
        page.update()
    page.on_resize = _on_resize
    _on_resize(None)

    if saved:
        try:
            t = ft.Timer(interval=20, repeat=False, on_tick=lambda e: ac_buscar())
            if t not in page.overlay: page.overlay.append(t)
        except Exception:
            pass

    return layout
