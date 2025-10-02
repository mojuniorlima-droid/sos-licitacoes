# pages/banco_precos.py — Banco de Preços (scroll H/V, máscara Preço, Calculadora de Margens em lote + exports via FilePicker)
from __future__ import annotations

import flet as ft

# --- Imports tolerantes para web ---
try:
    from services.exports import export_csv, export_xlsx
except Exception:
    def export_csv(*a, **k): return False
    def export_xlsx(*a, **k): return False

try:
    from services import db
except Exception:
    class _DBStub: ...
    db = _DBStub()

try:
    from components.tableview import SimpleTable
except Exception:
    class SimpleTable(ft.UserControl):
        def build(self): return ft.Container(ft.Text("Tabela indisponível"))

try:
    from components.forms import FieldRow, snack_ok, snack_err, text_input, date_input, money_input
except Exception:
    class FieldRow(ft.Row): ...
    def snack_ok(page, msg): page.snack_bar = ft.SnackBar(ft.Text(msg)); page.snack_bar.open = True; page.update()
    def snack_err(page, msg): page.snack_bar = ft.SnackBar(ft.Text(msg)); page.snack_bar.open = True; page.update()
    def text_input(value="", label="", width=None, **k): return ft.TextField(value=value, label=label, width=width)
    def date_input(label="", value="", **k): return ft.TextField(value=value, label=label)
    def money_input(value="", label="", width=None, **k): return ft.TextField(value=str(value), label=label, width=width)

try:
    from components.margem_calc import open_margem_calc_dialog
except Exception:
    def open_margem_calc_dialog(page, *a, **k):
        snack_err(page, "Calculadora indisponível no ambiente web.")

BASE_DESCONTO = 240

CATEGORIES = [
    "Gêneros alimentícios (geral)",
    "Gêneros alimentícios (hortifrutigranjeiros)",
    "Expediente",
    "Permanente",
    "Informática",
    "Enxoval",
    "Higiene e limpeza",
    "Copa e cozinha",
    "Outros",
]
TIPOS_ORIGEM = ["Mercado", "Fornecedor", "Mercado Online"]

COLUMNS = [
    "ID", "Produto", "Categoria", "Tipo", "Origem", "Marca",
    "Unidade", "Embalagem", "Preço", "Data", "Link", "Observações"
]

# ---------- diálogos (padrão) ----------
def _install_page_open_patch(page: ft.Page):
    if getattr(page, "_novo5_dialog_patch", False):
        return
    page._novo5_dialog_patch = True
    _orig_open = page.open
    def _open_patched(dlg: ft.Control):
        try:
            if isinstance(dlg, ft.AlertDialog):
                vw = int(getattr(page, "window_width", None) or getattr(page, "width", 1200) or 1200)
                vh = int(getattr(page, "window_height", None) or getattr(page, "height", 800) or 800)
                w = int(min(980, max(720, vw * 0.90)))
                h = int(min(700, max(520, vh * 0.90)))
                dlg.content = ft.Container(
                    width=w, height=h, padding=12,
                    content=ft.Column(expand=True, spacing=12, controls=[dlg.content, ft.Container(expand=True)])
                )
        except Exception:
            pass
        return _orig_open(dlg)
    page.open = _open_patched  # type: ignore

def _dialog(page: ft.Page, title: str, content: ft.Control, on_save):
    _install_page_open_patch(page)
    btn_cancel = ft.TextButton("Cancelar")
    btn_save   = ft.FilledButton("Salvar")
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=content,
        actions=[btn_cancel, btn_save],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    def close_dlg(_=None):
        try: page.close(d)
        except Exception: pass
    btn_cancel.on_click = close_dlg
    def _on_save(_):
        try:
            btn_save.disabled = True; btn_save.text = "Salvando…"; page.update()
        except Exception:
            pass
        try:
            on_save(close_dlg)
        finally:
            try:
                btn_save.disabled = False; btn_save.text = "Salvar"; page.update()
            except Exception:
                pass
    btn_save.on_click = _on_save
    page.open(d)

def _confirm_dialog(page: ft.Page, title: str, message: str, on_confirm):
    _install_page_open_patch(page)
    vw = int(getattr(page, "window_width", None) or getattr(page, "width", 1200) or 1200)
    vh = int(getattr(page, "window_height", None) or getattr(page, "height", 800) or 800)
    w = int(min(520, max(380, vw * 0.50))); h = int(min(260, max(200, vh * 0.30)))
    btn_cancel = ft.TextButton("Cancelar"); btn_del = ft.FilledButton("Excluir", icon=ft.Icons.DELETE_OUTLINE)
    body = ft.Container(width=w, height=h, padding=12, content=ft.Column(expand=True, spacing=12, controls=[ft.Text(message), ft.Container(expand=True)]))
    d = ft.AlertDialog(modal=True, title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD), content=body, actions=[btn_cancel, btn_del], actions_alignment=ft.MainAxisAlignment.END)
    btn_cancel.on_click = lambda e: page.close(d)
    btn_del.on_click = lambda e: (on_confirm(), page.close(d))
    page.open(d)

# ---------- FilePicker p/ exports ----------
def _ensure_filepicker(page: ft.Page) -> ft.FilePicker:
    fp = next((x for x in page.overlay if isinstance(x, ft.FilePicker)), None)
    if not fp:
        fp = ft.FilePicker()
        page.overlay.append(fp)
        page.update()
    return fp

# ---------- página ----------
def page_banco_precos(page: ft.Page) -> ft.Control:
    BTN_COMPACT = ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=6))

    # filtros
    dd_categoria = ft.Dropdown(
        value="Todas", dense=True, width=260,
        options=[ft.dropdown.Option("Todas")] + [ft.dropdown.Option(c) for c in CATEGORIES]
    )
    dd_tipo = ft.Dropdown(
        value="Todos", dense=True, width=180,
        options=[ft.dropdown.Option("Todos")] + [ft.dropdown.Option(t) for t in TIPOS_ORIGEM]
    )
    txt_busca = ft.TextField(dense=True, width=260, hint_text="Buscar: produto/origem/marca")

    tbl = SimpleTable(
        COLUMNS, include_master=True, zebra=True,
        height=max(240, page.window_height - BASE_DESCONTO),
    )

    lbl_count = ft.Text("", size=12)

    def load():
        try:
            rows_src = db.list_banco_precos({
                "categoria": dd_categoria.value,
                "tipo_origem": dd_tipo.value,
                "q": txt_busca.value,
            }) or []
        except Exception:
            rows_src = []
        rows = []
        for r in rows_src:
            pr = r.get("preco")
            if isinstance(pr, (int, float)):
                pr_fmt = f"R$ {pr:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")
            elif pr:
                pr_fmt = str(pr)
            else:
                pr_fmt = ""
            rows.append({
                "id": r.get("id"),
                "ID": r.get("id"),
                "Produto": r.get("produto") or "",
                "Categoria": r.get("categoria") or "",
                "Tipo": r.get("tipo_origem") or "",
                "Origem": r.get("origem_nome") or "",
                "Marca": r.get("marca") or "",
                "Unidade": r.get("unidade") or "",
                "Embalagem": r.get("embalagem") or "",
                "Preço": pr_fmt,
                "Data": r.get("data_coleta") or "",
                "Link": r.get("link") or "",
                "Observações": r.get("observacoes") or "",
            })
        tbl.set_rows(rows)
        lbl_count.value = f"{len(rows)} registro(s)"
        page.update()

    # formulário (igual)
    def _form(rec: dict | None = None) -> ft.Control:
        produto   = text_input("", "", width=420); produto.hint_text = "Ex.: Arroz tipo 1"
        categoria = ft.Dropdown(dense=True, width=420, options=[ft.dropdown.Option(c) for c in CATEGORIES])
        tipo      = ft.Dropdown(dense=True, width=220, options=[ft.dropdown.Option(t) for t in TIPOS_ORIGEM])
        origem    = text_input("", "", width=420); origem.hint_text = "Nome do Mercado/Fornecedor"
        marca     = text_input("", "", width=200)
        unidade   = text_input("", "", width=160);   unidade.hint_text = "un / kg / cx / pct…"
        embalagem = text_input("", "", width=200);   embalagem.hint_text = "Ex.: 5kg / 12x500ml"
        preco     = money_input("Preço", value="", width=180)
        data      = date_input("Data da coleta (dd/mm/aaaa)", value="")
        link      = text_input("", "", width=420); link.hint_text = "URL (quando online)"
        obs       = text_input("", "", width=940, multiline=True)

        try:
            preco.input_filter = ft.InputFilter(allow=True, regex=r"[0-9,.\sR$]")
        except Exception:
            pass

        def _fmt_brl(txt: str) -> str:
            if not txt:
                return ""
            s = str(txt).strip().replace("R$", "").replace(" ", "")
            if "," in s and "." in s:
                s = s.replace(".", "")
            s = s.replace(",", ".")
            try:
                val = float(s)
            except Exception:
                return txt
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        preco.on_blur = lambda e: (setattr(preco, "value", _fmt_brl(preco.value)), page.update())
        preco.text_align = ft.TextAlign.RIGHT
        if not getattr(preco, "hint_text", None):
            preco.hint_text = "Ex.: 12,50"

        if rec:
            produto.value   = rec.get("Produto") or ""
            categoria.value = rec.get("Categoria") or None
            tipo.value      = rec.get("Tipo") or None
            origem.value    = rec.get("Origem") or ""
            marca.value     = rec.get("Marca") or ""
            unidade.value   = rec.get("Unidade") or ""
            embalagem.value = rec.get("Embalagem") or ""
            preco.value     = rec.get("Preço") or ""
            data.value      = rec.get("Data") or ""
            link.value      = rec.get("Link") or ""
            obs.value       = rec.get("Observações") or ""

        frm = ft.Column(spacing=8, controls=[
            ft.Row(spacing=10, controls=[ FieldRow("Produto*", produto, 420), FieldRow("Categoria", categoria, 420) ]),
            ft.Row(spacing=10, controls=[ FieldRow("Tipo de origem", tipo, 220), FieldRow("Origem (Mercado/Fornecedor)", origem, 420), FieldRow("Marca", marca, 200) ]),
            ft.Row(spacing=10, controls=[ FieldRow("Unidade", unidade, 160), FieldRow("Embalagem", embalagem, 200), FieldRow("Preço", preco, 180), FieldRow("Data", data, 220) ]),
            ft.Row(spacing=10, controls=[ FieldRow("Link (se online)", link, 420) ]),
            ft.Row(spacing=10, controls=[ FieldRow("Observações", obs, 940) ]),
        ])

        def _collect():
            return {
                "produto": (produto.value or "").strip(),
                "categoria": categoria.value,
                "tipo_origem": tipo.value,
                "origem_nome": (origem.value or "").strip(),
                "marca": (marca.value or "").strip(),
                "unidade": (unidade.value or "").strip(),
                "embalagem": (embalagem.value or "").strip(),
                "preco": (preco.value or "").strip(),
                "data_coleta": (data.value or "").strip(),
                "link": (link.value or "").strip(),
                "observacoes": (obs.value or "").strip(),
            }
        frm._collect_payload = _collect  # type: ignore[attr-defined]
        return frm

    # CRUD
    def new():
        frm = _form()
        def save(close):
            data = frm._collect_payload()  # type: ignore[attr-defined]
            if not data["produto"]:
                return snack_err(page, "Informe o produto.")
            try:
                db.add_banco_preco(data)
                close(); snack_ok(page, "Registro criado."); load()
            except Exception as ex:
                close(); snack_err(page, f"Erro ao salvar: {ex}")
        _dialog(page, "➕ Novo preço", frm, save)

    def edit():
        sel = tbl.selected_ids()
        if not sel:
            return snack_err(page, "Selecione uma linha.")
        rid = sel[0]
        rec = next((r for r in tbl._rows_data if r.get("id")==rid), None)
        if not rec:
            return snack_err(page, "Registro não encontrado.")
        frm = _form(rec)
        def save(close):
            data = frm._collect_payload()  # type: ignore[attr-defined]
            if not data["produto"]:
                return snack_err(page, "Informe o produto.")
            try:
                db.upd_banco_preco(rid, data)
                close(); snack_ok(page, "Registro atualizado."); load()
            except Exception as ex:
                close(); snack_err(page, f"Erro: {ex}")
        _dialog(page, "✏️ Editar preço", frm, save)

    def delete():
        ids = tbl.selected_ids()
        if not ids:
            return snack_err(page, "Selecione ao menos uma linha.")
        def do_confirm():
            ok, fail = 0, 0
            for _id in ids:
                try:
                    db.del_banco_preco(_id); ok += 1
                except Exception:
                    fail += 1
            snack_ok(page, f"Excluídos: {ok} • Falhas: {fail}"); load()
        _confirm_dialog(page, "Excluir preços", f"Confirmar exclusão de {len(ids)} registro(s)?", do_confirm)

    # ---------- Calculadora ----------
    def _apply_final_to_selection(valor_final: float):
        sel = tbl.selected_ids()
        if not sel:
            return snack_err(page, "Selecione uma linha para aplicar.")
        page.set_clipboard(f"R$ {valor_final:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        snack_ok(page, "Preço final copiado; cole no campo desejado (não salvo).")

    def _parse_brl(txt: str) -> float:
        if not txt:
            return 0.0
        t = str(txt).replace("R$","").replace(" ","")
        t = t.replace(".","").replace(",",".")
        try:
            return float(t)
        except Exception:
            return 0.0

    def open_calc(_=None):
        itens = []
        sel = tbl.selected_ids() or []
        if sel:
            for rid in sel:
                row = next((r for r in (tbl._rows_data or []) if str(r.get("id")) == str(rid)), None)
                if row:
                    itens.append({"id": row.get("ID"), "produto": row.get("Produto"), "preco": _parse_brl(row.get("Preço") or "")})
        preco_inicial = itens[0]["preco"] if len(itens) == 1 else 0.0
        open_margem_calc_dialog(page, preco_base_inicial=preco_inicial, itens_selecionados=itens,
                                frete_padrao=13.0, lucro_padrao=22.0, on_apply_final=_apply_final_to_selection)

    # ---------- Exports via FilePicker ----------
    fp = _ensure_filepicker(page)

    def _export_left_csv(_=None):
        headers = COLUMNS
        rows = [{h: r.get(h, "") for h in headers} for r in (tbl._rows_data or [])]
        def _save(e: ft.FilePickerResultEvent):
            if not e.path: return
            try:
                export_csv(headers, rows, e.path)
                snack_ok(page, "CSV exportado.")
            except TypeError:
                try:
                    export_csv(rows, e.path)  # fallback
                    snack_ok(page, "CSV exportado.")
                except Exception as ex2:
                    snack_err(page, f"Falha ao exportar: {ex2}")
            except Exception as ex:
                snack_err(page, f"Falha ao exportar: {ex}")
        fp.on_result = _save
        fp.save_file(file_name="banco_precos.csv")

    def _export_left_xlsx(_=None):
        headers = COLUMNS
        rows = [{h: r.get(h, "") for h in headers} for r in (tbl._rows_data or [])]
        def _save(e: ft.FilePickerResultEvent):
            if not e.path: return
            try:
                export_xlsx("Banco de Preços", headers, rows, e.path)
                snack_ok(page, "Excel exportado.")
            except TypeError:
                try:
                    export_xlsx(headers, rows, e.path)  # fallback
                    snack_ok(page, "Excel exportado.")
                except Exception as ex2:
                    snack_err(page, f"Falha ao exportar: {ex2}")
            except Exception as ex:
                snack_err(page, f"Falha ao exportar: {ex}")
        fp.on_result = _save
        fp.save_file(file_name="banco_precos.xlsx")

    # ====== TOPO COM DUAS LINHAS COMPACTAS ======
    # Linha 1: Filtros + Filtrar/Limpar (NÃO QUEBRA; scroll horizontal se precisar)
    filtros_row = ft.Row(
        spacing=8, wrap=False,  # <- evita quebra
        scroll=ft.ScrollMode.AUTO,  # permite rolar na horizontal se faltar espaço
        controls=[
            FieldRow("Categoria", dd_categoria, 260),
            FieldRow("Tipo", dd_tipo, 180),
            FieldRow("Buscar", txt_busca, 260),
            ft.OutlinedButton("Filtrar", on_click=lambda e: load(), style=BTN_COMPACT),
            ft.OutlinedButton(
                "Limpar",
                on_click=lambda e: (
                    setattr(dd_categoria, "value", "Todas"),
                    setattr(dd_tipo, "value", "Todos"),
                    setattr(txt_busca, "value", ""),
                    load()
                ),
                style=BTN_COMPACT
            ),
        ],
        expand=True,  # ocupa toda a largura disponível
    )

    # Linha 2: Botões de ação
    acoes_row = ft.Row(
        spacing=8, wrap=True, scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.FilledButton("➕ Novo", on_click=lambda e: new(), style=BTN_COMPACT),
            ft.OutlinedButton("✏️ Editar", on_click=lambda e: edit(), style=BTN_COMPACT),
            ft.OutlinedButton("🗑️ Excluir", on_click=lambda e: delete(), style=BTN_COMPACT),
            ft.OutlinedButton("Calculadora de Margens", on_click=open_calc, style=BTN_COMPACT),
            ft.OutlinedButton("Exportar CSV", on_click=_export_left_csv, style=BTN_COMPACT),
            ft.OutlinedButton("Exportar Excel", on_click=_export_left_xlsx, style=BTN_COMPACT),
        ],
    )

    header = ft.Column(
        spacing=6,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Text("Banco de Preços", size=18, weight=ft.FontWeight.BOLD)],
            ),
            filtros_row,
            acoes_row,
        ],
    )

    divider = ft.Divider(height=1, thickness=1, color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE))

    # QUADRO com rolagem HORIZONTAL + VERTICAL
    quadro = ft.Container(
        expand=True,
        content=ft.Row(
            scroll=ft.ScrollMode.AUTO,  # horizontal
            controls=[
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,  # vertical
                        controls=[tbl.control()],
                    ),
                ),
            ],
        ),
    )

    footer  = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
        border_radius=10, padding=ft.Padding(10, 8, 10, 8),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[ft.Text("", size=12), ft.Text("Clique na caixa para selecionar.", size=12)],
        ),
    )
    layout = ft.Column(expand=True, spacing=8, controls=[header, divider, quadro, footer])

    def set_count(txt: str):
        footer.content.controls[0] = ft.Text(txt, size=12)

    prev = page.on_resized
    def _on_resized(e=None):
        try:
            if prev: prev(e) if callable(prev) and e is not None else (prev() if callable(prev) else None)
        except Exception:
            pass
        vw = (page.window_width or page.width or 1200)
        # largura “elástica”; sem limite inferior muito alto para evitar wrap
        filtros_row.width = max(520, int(vw * 0.70))
        acoes_row.width   = max(420, int(vw * 0.60))
        nh = max(360, (page.window_height or page.height or 720) - BASE_DESCONTO)
        tbl.set_height(nh)
        page.update()
    page.on_resized = _on_resized
    _on_resized(None)

    def _load_and_count():
        load()
        set_count(f"{len(tbl._rows_data)} registro(s)")
        page.update()
    _load_and_count()
    return layout
