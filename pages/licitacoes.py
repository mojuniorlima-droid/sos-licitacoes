# pages/licitacoes.py
from __future__ import annotations
import flet as ft
import services.db as db
from components.tableview import SimpleTable
from components.forms import FieldRow, snack_ok, snack_err, text_input, date_input

BASE_DESCONTO = 240
COLUMNS = [
    "ID", "Empresa", "Órgão", "Modalidade", "Processo",
    "Data da sessão", "Hora", "Qtd Itens", "Valor estimado", "Tem lotes", "Link"
]

# -------- utils --------
def _get(row, key, dflt=None):
    if row is None:
        return dflt
    try:
        return row.get(key, dflt)
    except AttributeError:
        try:
            return row[key]
        except Exception:
            return dflt

def _val(row, *keys, default=""):
    for k in keys:
        v = _get(row, k, None)
        if isinstance(v, str):
            v = v.strip()
        if v not in (None, ""):
            return v
    return default

def _pick_db_licit():
    def pick(*names):
        for n in names:
            if hasattr(db, n):
                return getattr(db, n)
        return None
    return {
        "list": pick("list_licitacoes", "licitacoes_all", "get_licitacoes"),
        "add":  pick("add_licitacao", "licitacao_add", "nova_licitacao"),
        "upd":  pick("upd_licitacao", "update_licitacao", "licitacao_upd"),
        "del":  pick("del_licitacao", "delete_licitacao", "licitacao_del"),
    }

def _pick_db_empresas_list():
    for n in ["list_companies", "companies_all", "list_company", "empresas_all", "get_empresas", "empresas_list"]:
        if hasattr(db, n):
            return getattr(db, n)
    return None

def _empresa_items():
    items, lister = [], _pick_db_empresas_list()
    rows = []
    if lister:
        try:
            rows = lister() or []
        except Exception:
            rows = []
    for c in rows:
        cid = _get(c, "id", "")
        nm = (_get(c, "name") or _get(c, "nome") or "").strip()
        if cid and nm:
            items.append((str(cid), nm))
    return items

# -------- máscara BRL (para Valor estimado) --------
def _format_brl_from_digits(digits: str) -> str:
    if not digits:
        return ""
    n = int(digits)
    cents = f"{n:0>3}"
    reais, cent = cents[:-2], cents[-2:]
    parts = []
    while reais:
        parts.insert(0, reais[-3:])
        reais = reais[:-3]
    return f"R$ {'/'.join(parts).replace('/', '.')},{cent}".replace("R$ .", "R$ ")

def _attach_brl_mask(textfield: ft.TextField):
    def digits_only(s: str) -> str:
        return "".join(ch for ch in s if ch.isdigit())
    if textfield.value:
        d = digits_only(textfield.value)
        textfield.value = _format_brl_from_digits(d)
    def _on_change(e):
        d = digits_only(textfield.value or "")
        textfield.value = _format_brl_from_digits(d)
        textfield.update()
    textfield.on_change = _on_change

def _unmask_brl_to_number(s: str) -> str:
    if not s:
        return ""
    s = s.replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    return s

# -------- máscara de hora (HH:MM) --------
def _attach_time_mask(textfield: ft.TextField):
    def only_digits(s: str) -> str:
        return "".join(ch for ch in s if ch.isdigit())
    if textfield.value:
        d = only_digits(textfield.value)[:4]
        if len(d) >= 3:
            textfield.value = f"{d[:2]}:{d[2:]}"
    def _on_change(e):
        d = only_digits(textfield.value or "")[:4]
        if len(d) <= 2:
            textfield.value = d
        else:
            textfield.value = f"{d[:2]}:{d[2:]}"
        textfield.update()
    textfield.on_change = _on_change

# -------- diálogos (padrão Empresas) --------
def _install_page_open_patch(page: ft.Page):
    if getattr(page, "_novo5_dialog_patch", False):
        return
    page._novo5_dialog_patch = True
    _orig_open = page.open
    def _open_patched(dlg: ft.Control):
        try:
            if isinstance(dlg, ft.AlertDialog):
                body = dlg.content
                dlg.content = ft.Container(
                    content=ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, controls=[body] if body else []),
                    width=min(980, (page.window_width or page.width or 1200) - 80),
                    height=min(620, (page.window_height or page.height or 800) - 80),
                    padding=10,
                )
        except Exception:
            pass
        return _orig_open(dlg)
    page.open = _open_patched  # type: ignore

def _dialog(page: ft.Page, title: str, content: ft.Control, on_save_with_close):
    _install_page_open_patch(page)
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=content,
        actions_alignment=ft.MainAxisAlignment.END,
    )
    def close_dlg(_=None):
        d.open = False
        page.update()
    d.actions = [
        ft.TextButton("Cancelar", on_click=close_dlg),
        ft.ElevatedButton("Salvar", on_click=lambda e: on_save_with_close(close_dlg)),
    ]
    page.open(d)

def _confirm_dialog(page: ft.Page, title: str, message: str, on_confirm):
    _install_page_open_patch(page)
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(content=ft.Column(expand=True, spacing=12, controls=[ft.Text(message), ft.Container(expand=True)])),
        actions_alignment=ft.MainAxisAlignment.END,
    )
    def close_dlg(_=None):
        d.open = False
        page.update()
    d.actions = [
        ft.TextButton("Cancelar", on_click=close_dlg),
        ft.ElevatedButton("Excluir", on_click=lambda e: (on_confirm(), close_dlg())),
    ]
    page.open(d)

# -------- form --------
def _form(record=None) -> ft.Column:
    r = record or {}

    empresa_combo = ft.Dropdown(
        label="Empresa",
        hint_text="Selecione...",
        options=[ft.dropdown.Option(key=i, text=t) for i, t in _empresa_items()],
        width=380,
        value=None,
    )

    orgao_inp       = text_input(_val(r, "orgao"), "Órgão", width=320)
    modalidade_inp  = text_input(_val(r, "modalidade"), "Modalidade", width=220)
    processo_inp    = text_input(_val(r, "processo"), "Nº do processo", width=220)
    data_sessao_inp = date_input("Data da sessão (dd/mm/aaaa)", value=_val(r, "data_sessao", "data"), width=220)
    hora_inp        = text_input(_val(r, "hora"), "Hora (00:00)", width=160)
    _attach_time_mask(hora_inp)

    qtd_itens_inp   = text_input(str(_val(r, "qtd_itens") or ""), "Qtd Itens", width=160)
    valor_inp       = text_input(_val(r, "valor_estimado", "valor"), "Valor estimado (R$)", width=220)
    _attach_brl_mask(valor_inp)

    link_inp        = text_input(_val(r, "link", "url"), "Link/URL", width=380)
    tem_lotes_chk   = ft.Checkbox(label="Tem lotes?", value=bool(_get(r, "tem_lotes", 0)))

    rid_emp = _get(r, "empresa_id", None)
    if rid_emp:
        empresa_combo.value = str(rid_emp)
    else:
        nome_emp = _val(r, "empresa_nome", "empresa", default="")
        if nome_emp:
            for op in empresa_combo.options:
                if op.text == nome_emp:
                    empresa_combo.value = op.key
                    break

    form = ft.Column(
        spacing=10,
        controls=[
            ft.Row(spacing=10, controls=[FieldRow("Empresa", empresa_combo, 380), FieldRow("Órgão", orgao_inp, 320)]),
            ft.Row(spacing=10, controls=[FieldRow("Modalidade", modalidade_inp, 220), FieldRow("Nº do processo", processo_inp, 220)]),
            ft.Row(spacing=10, controls=[FieldRow("Data da sessão", data_sessao_inp, 220), FieldRow("Hora", hora_inp, 160)]),
            ft.Row(spacing=10, controls=[FieldRow("Qtd Itens", qtd_itens_inp, 160), FieldRow("Valor estimado (R$)", valor_inp, 220)]),
            ft.Row(spacing=10, controls=[FieldRow("Link/URL", link_inp, 380), tem_lotes_chk]),
        ],
    )

    def _collect_payload():
        return {
            "empresa_id": int(empresa_combo.value) if empresa_combo.value else None,
            "orgao": orgao_inp.value.strip(),
            "modalidade": modalidade_inp.value.strip(),
            "processo": processo_inp.value.strip(),
            "data_sessao": data_sessao_inp.value.strip(),
            "hora": hora_inp.value.strip(),
            "qtd_itens": qtd_itens_inp.value.strip(),
            "valor_estimado": _unmask_brl_to_number(valor_inp.value.strip()),
            "link": link_inp.value.strip(),
            "tem_lotes": tem_lotes_chk.value,
        }

    form._collect_payload = _collect_payload  # type: ignore
    return form

# -------- detalhes (mantido para futuro, mas não é usado sem o botão) --------
def _show_details(page: ft.Page, rec: dict):
    def row(lbl, val):
        return ft.Row(spacing=8, controls=[ft.Text(lbl, weight=ft.FontWeight.BOLD), ft.Text(val or "—")])
    valor_fmt = _val(rec, "valor_estimado", "valor")
    if valor_fmt:
        try:
            valor_fmt = _format_brl_from_digits("".join(ch for ch in str(valor_fmt) if ch.isdigit()))
        except Exception:
            pass
    content = ft.Column(
        spacing=6,
        controls=[
            row("Empresa:",  _val(rec, "empresa_nome", "empresa")),
            row("Órgão:",    _val(rec, "orgao")),
            row("Modalidade:", _val(rec, "modalidade")),
            row("Processo:", _val(rec, "processo")),
            row("Data da sessão:", _val(rec, "data_sessao", "data")),
            row("Hora:",     _val(rec, "hora")),
            row("Qtd Itens:", str(_val(rec, "qtd_itens") or "")),
            row("Valor estimado:", valor_fmt or _val(rec, "valor_estimado", "valor")),
            row("Tem lotes:", "Sim" if str(_get(rec, "tem_lotes", 0)).lower() in ("1", "true", "sim") else "Não"),
            row("Link/URL:", _val(rec, "link", "url")),
        ],
    )
    _install_page_open_patch(page)
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text("🔎 Detalhes da Licitação", size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(content=ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, controls=[content]), padding=6),
        actions=[ft.TextButton("Fechar", on_click=lambda e: (setattr(d, "open", False), page.update()))],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(d)

# -------- página --------
def page_licitacoes(page: ft.Page) -> ft.Control:
    funcs = _pick_db_licit()

    h0 = (page.window_height or page.height or 720)
    tbl = SimpleTable(COLUMNS, include_master=True, zebra=True, height=max(360, h0 - BASE_DESCONTO))
    lbl_count = ft.Text("", size=12)
    rows_cache: list[dict] = []

    # Igual à página EMPRESAS: lista de dicts + set_rows(adapted)
    def load():
        nonlocal rows_cache
        rows = []
        if funcs.get("list"):
            try:
                rows = funcs["list"]() or []
            except Exception as ex:
                snack_err(page, f"Erro ao listar: {ex}")
                rows = []
        rows_cache = rows[:]

        adapted = []
        for r in rows:
            rid = _get(r, "id")
            valor_fmt = _val(r, "valor_estimado", "valor")
            if valor_fmt:
                try:
                    valor_fmt = _format_brl_from_digits("".join(ch for ch in str(valor_fmt) if ch.isdigit()))
                except Exception:
                    pass
            adapted.append({
                "id": rid,
                "ID": rid,
                "Empresa": _val(r, "empresa_nome", "empresa"),
                "Órgão": _val(r, "orgao"),
                "Modalidade": _val(r, "modalidade"),
                "Processo": _val(r, "processo"),
                "Data da sessão": _val(r, "data_sessao", "data"),
                "Hora": _val(r, "hora"),
                "Qtd Itens": _val(r, "qtd_itens"),
                "Valor estimado": valor_fmt or _val(r, "valor_estimado", "valor"),
                "Tem lotes": "Sim" if str(_get(r, "tem_lotes", 0)).lower() in ("1", "true", "sim") else "Não",
                "Link": _val(r, "link", "url"),
            })

        tbl.set_rows(adapted)
        lbl_count.value = f"{len(adapted)} registro(s)."
        try:
            lbl_count.update()
            page.update()
        except Exception:
            pass

    # ações
    def new():
        frm = _form()
        def save(close):
            payload = frm._collect_payload()  # type: ignore
            if not funcs.get("add"):
                return snack_err(page, "add_licitacao() indisponível no DB.")
            try:
                funcs["add"](payload)
                snack_ok(page, "Licitação criada.")
                close()
                load()
            except Exception as ex:
                snack_err(page, f"Erro ao salvar: {ex}")
        _dialog(page, "➕ Nova licitação", frm, save)

    def edit():
        sel = tbl.selected_ids()
        if not sel:
            return snack_err(page, "Selecione uma linha.")
        rid = sel[0]
        rec = None
        if funcs.get("list"):
            try:
                for r in funcs["list"]() or []:
                    if str(_get(r, "id")) == str(rid):
                        rec = r
                        break
            except Exception:
                rec = None
        if not rec:
            return snack_err(page, "Não foi possível carregar o registro selecionado.")

        frm = _form(rec)
        def save(close):
            payload = frm._collect_payload()  # type: ignore
            if not funcs.get("upd"):
                return snack_err(page, "upd_licitacao() indisponível no DB.")
            try:
                funcs["upd"](rid, payload)
                snack_ok(page, "Licitação atualizada.")
                close()
                load()
            except Exception as ex:
                snack_err(page, f"Erro: {ex}")
        _dialog(page, "✏️ Editar licitação", frm, save)

    def delete():
        sel = tbl.selected_ids()
        if not sel:
            return snack_err(page, "Selecione ao menos uma linha.")
        ids = sel[:]
        def do_confirm():
            if not funcs.get("del"):
                return snack_err(page, "del_licitacao() indisponível no DB.")
            ok = fail = 0
            for rid in ids:
                try:
                    try:
                        funcs["del"](int(rid))
                    except Exception:
                        funcs["del"](rid)
                    ok += 1
                except Exception:
                    fail += 1
            snack_ok(page, f"Excluídos: {ok} • Falhas: {fail}")
            load()
        _confirm_dialog(page, "Excluir licitações", f"Confirmar exclusão de {len(ids)} registro(s)?", do_confirm)

    # Header/Toolbar (sem “Ver mais”)
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Licitações", size=18, weight=ft.FontWeight.BOLD),
            ft.Row(
                spacing=8,
                controls=[
                    ft.FilledButton("➕ Nova", on_click=lambda e: new()),
                    ft.OutlinedButton("✏️ Editar", on_click=lambda e: edit()),
                    ft.OutlinedButton("🗑️ Excluir", on_click=lambda e: delete()),
                    ft.VerticalDivider(),
                    ft.OutlinedButton("Selecionar tudo", on_click=lambda e: (tbl.select_all(), page.update())),
                    ft.OutlinedButton("Limpar seleção", on_click=lambda e: (tbl.clear_selection(), page.update())),
                ],
            ),
        ],
    )
    divider = ft.Divider(height=1, thickness=1)

    # === QUADRO COM ROLAGEM HORIZONTAL + VERTICAL ===
    # Para reduzir quebras de texto, usamos um container "largo" e rolagem horizontal.
    row_inner = ft.Row(controls=[tbl.control()])
    try:
        row_inner.scroll = ft.ScrollMode.AUTO  # horizontal
    except Exception:
        pass

    row_container = ft.Container(content=row_inner)  # largura ajustada no on_resized

    quadro = ft.Container(
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,  # vertical
            controls=[row_container],
        ),
    )

    footer = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
        border_radius=10,
        padding=ft.Padding(10, 8, 10, 8),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[lbl_count, ft.Text("Clique na caixa para selecionar.", size=12)],
        ),
    )

    layout = ft.Column(expand=True, spacing=8, controls=[header, divider, quadro, footer])

    # --- Resize: altura da tabela + largura mínima p/ evitar apertos ---
    prev = page.on_resized
    def _on_resized(e=None):
        try:
            if prev:
                prev(e) if callable(prev) and e is not None else (prev() if callable(prev) else None)
        except Exception:
            pass

        vw = (page.window_width or page.width or 1200)
        vh = (page.window_height or page.height or 720)

        # Altura da tabela mantendo padrão do projeto
        nh = max(360, int(vh - BASE_DESCONTO))
        try:
            tbl.set_height(nh)
        except Exception:
            pass

        # Largura "alargada" para reduzir quebras (com rolagem horizontal)
        try:
            row_container.width = max(int(vw * 1.35), 1280)
        except Exception:
            pass

        page.update()

    page.on_resized = _on_resized
    _on_resized(None)
    load()
    return layout
