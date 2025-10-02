# components/margem_calc.py
from __future__ import annotations
import flet as ft
from typing import List, Dict, Any, Callable, Optional
from components.forms import FieldRow, text_input, money_input, snack_ok, snack_err
from services.exports import export_xlsx  # helper do projeto p/ Excel

# ===================== Helpers BR =====================
def br_money_parse(s: str | None) -> float:
    if not s:
        return 0.0
    t = str(s).strip().replace("R$", "").replace(" ", "")
    t = t.replace(".", "")          # remove milhar
    t = t.replace(",", ".")         # vírgula -> ponto
    try:
        return float(t)
    except Exception:
        return 0.0

def br_money_format(v: float) -> str:
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def br_percent_format(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} %"

def _normalize_percent(s: str | None, default: float = 0.0) -> float:
    if s is None:
        return default
    t = str(s).replace("%", "").strip()
    if "," in t and "." in t:
        t = t.replace(".", "")      # BR: ponto milhar
        t = t.replace(",", ".")     # vírgula decimal
    elif "," in t:
        t = t.replace(",", ".")     # só vírgula -> decimal
    # senão: só ponto -> já decimal
    try:
        return float(t)
    except Exception:
        return default

# ===================== Cálculo =====================
def _calc_acumulado(base: float, frete: float, lucro: float, outros: float):
    a = base * (1 + frete/100.0)
    b = a    * (1 + lucro/100.0)
    c = b    * (1 + outros/100.0)
    return {"apos_frete": a, "apos_lucro": b, "apos_outros": c, "final": c,
            "margem_efetiva": (c/base - 1.0) * 100.0 if base > 0 else 0.0}

def _calc_soma_simples(base: float, frete: float, lucro: float, outros: float):
    total = frete + lucro + outros
    c = base * (1 + total/100.0)
    a = base * (1 + frete/100.0)
    b = base * (1 + (frete+lucro)/100.0)
    return {"apos_frete": a, "apos_lucro": b, "apos_outros": c, "final": c,
            "margem_efetiva": (c/base - 1.0) * 100.0 if base > 0 else 0.0}

# ===================== Patch diálogo com scroll =====================
def _install_dialog_patch(page: ft.Page):
    """Dialog rolável verticalmente (scroll AUTO)."""
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
                    content=ft.Column(
                        expand=True, spacing=12, scroll=ft.ScrollMode.AUTO,
                        controls=[dlg.content],
                    ),
                )
        except Exception:
            pass
        return _orig_open(dlg)
    page.open = _open_patched  # type: ignore

# --------------------- FilePicker helper ---------------------
def _ensure_filepicker(page: ft.Page) -> ft.FilePicker:
    fp = next((x for x in page.overlay if isinstance(x, ft.FilePicker)), None)
    if not fp:
        fp = ft.FilePicker()
        page.overlay.append(fp)
        page.update()
    return fp

# ===================== API principal =====================
def open_margem_calc_dialog(
    page: ft.Page,
    *,
    preco_base_inicial: float | None = None,
    itens_selecionados: Optional[List[Dict[str, Any]]] = None,
    frete_padrao: float = 13.0,
    lucro_padrao: float = 22.0,
    on_apply_final: Optional[Callable[[float], None]] = None,
):
    _install_dialog_patch(page)

    # Entradas
    preco_base = money_input("Preço base (R$)", value=br_money_format(preco_base_inicial or 0.0), width=220)
    frete      = text_input(value=f"{frete_padrao:.2f}", label="Frete (%)", width=120)
    lucro      = text_input(value=f"{lucro_padrao:.2f}", label="Lucro (%)", width=120)
    outros     = text_input(value="", label="Outros (%)", width=120)
    preco_base.on_blur = lambda e: (setattr(preco_base, "value", br_money_format(br_money_parse(preco_base.value))), page.update())

    modo = ft.Dropdown(
        label="Modo de cálculo",
        options=[ft.dropdown.Option("Acumulado"), ft.dropdown.Option("Soma simples")],
        value="Acumulado", width=180, dense=True
    )

    # Saídas (cabeçalho)
    out_ap_frete  = ft.Text("—", size=14)
    out_ap_lucro  = ft.Text("—", size=14)
    out_ap_outros = ft.Text("—", size=14)
    out_final     = ft.Text("—", size=16, weight=ft.FontWeight.BOLD)
    out_margem    = ft.Text("—", size=14)

    # Tabela em lote
    lote_columns = ["ID","Produto","Preço base","Após frete","Após lucro","Após outros","Preço final","Margem efetiva"]
    data_for_export: List[Dict[str, Any]] = []
    data_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(h)) for h in lote_columns],
        rows=[], data_row_max_height=42, heading_row_height=42, column_spacing=16,
    )

    def _calc_for_base(base: float):
        fr = _normalize_percent(frete.value, 0.0)
        lu = _normalize_percent(lucro.value, 0.0)
        ot = _normalize_percent(outros.value, 0.0)
        return _calc_soma_simples(base, fr, lu, ot) if modo.value == "Soma simples" else _calc_acumulado(base, fr, lu, ot)

    def _recalc_header():
        base = br_money_parse(preco_base.value)
        r = _calc_for_base(base)
        out_ap_frete.value  = br_money_format(r["apos_frete"])
        out_ap_lucro.value  = br_money_format(r["apos_lucro"])
        out_ap_outros.value = br_money_format(r["apos_outros"])
        out_final.value     = br_money_format(r["final"])
        out_margem.value    = br_percent_format(r["margem_efetiva"])

    def _recalc_lote():
        nonlocal data_for_export
        data_for_export = []
        selecionados = itens_selecionados or []
        rows = []
        for item in selecionados:
            pid   = item.get("id")
            nome  = item.get("produto") or item.get("Produto") or ""
            price = item.get("preco")
            if price is None:
                price = br_money_parse(item.get("Preço") or "")
            elif isinstance(price, str):
                price = br_money_parse(price)

            base = float(price or 0.0)
            r = _calc_for_base(base)
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(pid or ""))),
                ft.DataCell(ft.Text(str(nome))),
                ft.DataCell(ft.Text(br_money_format(base))),
                ft.DataCell(ft.Text(br_money_format(r["apos_frete"]))),
                ft.DataCell(ft.Text(br_money_format(r["apos_lucro"]))),
                ft.DataCell(ft.Text(br_money_format(r["apos_outros"]))),
                ft.DataCell(ft.Text(br_money_format(r["final"]))),
                ft.DataCell(ft.Text(br_percent_format(r["margem_efetiva"]))),
            ]))
            data_for_export.append({
                "ID": pid, "Produto": nome, "Preço base": base,
                "Após frete": r["apos_frete"], "Após lucro": r["apos_lucro"],
                "Após outros": r["apos_outros"], "Preço final": r["final"],
                "Margem efetiva (%)": r["margem_efetiva"],
            })
        data_table.rows = rows

    def _recalc_all(_=None):
        _recalc_header()
        _recalc_lote()
        page.update()

    for ctrl in (preco_base, frete, lucro, outros, modo):
        ctrl.on_change = _recalc_all
    _recalc_all()

    # Ações
    def _copy_final(_=None):
        if isinstance(out_final.value, str):
            page.set_clipboard(out_final.value)
            snack_ok(page, "Preço final copiado para a área de transferência.")

    def _apply_final(_=None):
        if not on_apply_final:
            return snack_err(page, "Nada para aplicar aqui (somente cálculo).")
        num = br_money_parse(out_final.value or "")
        try:
            on_apply_final(num); snack_ok(page, "Valor aplicado (sem salvar em banco).")
        except Exception as ex:
            snack_err(page, f"Falha ao aplicar: {ex}")

    def _export_excel(_=None):
        if not data_for_export:
            return snack_err(page, "Nenhum dado para exportar.")
        fp = _ensure_filepicker(page)
        def _do_save(e: ft.FilePickerResultEvent):
            if not e.path:  # usuário cancelou
                return
            try:
                # assinatura preferida: título, colunas, linhas(dict), caminho
                export_xlsx("Margens aplicadas", list(data_for_export[0].keys()), data_for_export, e.path)
                snack_ok(page, "Excel exportado.")
            except TypeError:
                try:
                    # fallback para assinaturas alternativas
                    export_xlsx(list(data_for_export[0].keys()), data_for_export, e.path)
                    snack_ok(page, "Excel exportado.")
                except Exception as ex2:
                    snack_err(page, f"Falha ao exportar: {ex2}")
            except Exception as ex:
                snack_err(page, f"Falha ao exportar: {ex}")
        fp.on_result = _do_save
        fp.save_file(file_name="margens_aplicadas.xlsx")

    # Layout
    header_controls = [
        FieldRow("Preço base (R$)", preco_base, 220),
        FieldRow("Frete (%)", frete, 120),
        FieldRow("Lucro (%)", lucro, 120),
        FieldRow("Outros (%)", outros, 120),
        FieldRow("Modo de cálculo", modo, 180),
    ]
    header_result = ft.Row(
        spacing=24,
        controls=[
            ft.Column([ft.Text("Após frete:"), out_ap_frete]),
            ft.Column([ft.Text("Após lucro:"), out_ap_lucro]),
            ft.Column([ft.Text("Após outros:"), out_ap_outros]),
            ft.Column([ft.Text("Preço final:"), out_final]),
            ft.Column([ft.Text("Margem efetiva total:"), out_margem]),
        ],
    )
    lote_block = None
    if itens_selecionados and len(itens_selecionados) > 0:
        lote_block = ft.Column(
            spacing=10,
            controls=[
                ft.Text(f"Itens selecionados ({len(itens_selecionados)})", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    height=360,
                    content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[data_table]),
                ),
                ft.Row(spacing=8, controls=[
                    ft.OutlinedButton("Exportar Excel (lote)", icon=ft.Icons.GRID_ON_ROUNDED, on_click=_export_excel),
                ]),
            ],
        )

    content = ft.Column(
        spacing=12,
        controls=[
            ft.Text("Calculadora de Margens", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Row(spacing=10, wrap=True, controls=header_controls),
            ft.Divider(),
            ft.Text("Resultados (preço base acima)", size=16, weight=ft.FontWeight.BOLD),
            header_result,
            ft.Container(padding=8),
            ft.Row(spacing=8, controls=[
                ft.OutlinedButton("Copiar preço final", icon=ft.Icons.CONTENT_COPY, on_click=_copy_final),
                ft.FilledTonalButton("Aplicar ao item selecionado", icon=ft.Icons.CHECK, on_click=_apply_final),
            ]),
            ft.Divider(),
        ] + ([lote_block] if lote_block else []),
    )

    dlg = ft.AlertDialog(
        modal=True, title=None,
        content=content,
        actions=[ft.TextButton("Fechar", on_click=lambda e: _close_dialog(page, dlg))],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(dlg)

def _close_dialog(page: ft.Page, dlg: ft.AlertDialog):
    dlg.open = False
    page.update()
