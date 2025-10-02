# pages/empresas.py
from __future__ import annotations

import flet as ft
import services.db as db
from components.tableview import SimpleTable
from components.forms import (
    FieldRow, snack_ok, snack_err, text_input, email_input, phone_input, cep_input, uf_input
)
from components.inputs import cnpj_input, cpf_input

BASE_DESCONTO = 240
COLUMNS = ["ID", "Nome", "CNPJ", "Telefone", "E-mail", "Cidade", "UF"]

# ---------------- util ----------------
def _get(row, key, default=None):
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        if hasattr(row, "keys"):
            return row[key] if key in row.keys() else default
    except Exception:
        pass
    return default

def _val(r: dict, *keys, default: str = "") -> str:
    """Retorna o primeiro valor não-vazio dentre várias chaves possíveis (compat com o ZIP / DB)."""
    for k in keys:
        v = _get(r, k)
        if v not in (None, "", []):
            return v
    return default

def _name_from(r):
    return _val(
        r,
        "nome", "name",
        "razao_social", "razao", "razaosocial",
        "fantasia", "nome_fantasia", "empresa",
        "company", "title",
        default=""
    )

def _telefone_from(r):
    return _val(r, "telefone", "phone", "celular", default="")

def _cidade_from(r):
    return _val(r, "cidade", "address_cidade", "municipio", default="")

def _uf_from(r):
    return _val(r, "uf", "address_estado", "estado", default="")

def _pick_db():
    """Mesma lógica do 'Novo 5 atual': escolhe funções reais e evita wrappers recursivos."""
    def pick(*names):
        for n in names:
            if hasattr(db, n):
                return getattr(db, n)
        return None
    return {
        "list": pick("list_companies", "companies_all", "list_company", "empresas_all", "get_empresas", "empresas_list"),
        "add":  pick("add_company", "empresa_add", "nova_empresa", "create_empresa"),
        "upd":  pick("upd_company", "empresa_upd", "update_empresa", "edit_empresa"),
        "del":  pick("del_company", "empresa_del", "delete_empresa", "remove_empresa"),
        "get":  pick("get_company", "company_get"),
    }

# -------- máscaras / helpers de UI --------
def _mask_date_value(v: str) -> str:
    """Formata dígitos como dd/mm/aaaa (máx 10 chars)."""
    digits = "".join(ch for ch in (v or "") if ch.isdigit())[:8]
    if not digits:
        return ""
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}/{digits[2:]}"
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"

def _attach_date_mask(tf: ft.TextField):
    def _on_change(e):
        new = _mask_date_value(tf.value or "")
        if (tf.value or "") != new:
            tf.value = new
            tf.update()
    tf.on_change = _on_change

def _masked(text: str) -> str:
    if not text:
        return "—"
    return "•" * max(4, len(text))

def _password_row(label: str, value: str) -> ft.Row:
    """Linha com texto e botão 'olhinho' para mostrar/ocultar senha."""
    txt = ft.Text(_masked(value), data="hidden")
    def toggle(e):
        if txt.data == "hidden":
            txt.value = value or "—"
            txt.data = "shown"
        else:
            txt.value = _masked(value)
            txt.data = "hidden"
        txt.update()
    eye = ft.IconButton(
        icon=ft.Icons.REMOVE_RED_EYE_OUTLINED,
        tooltip="Mostrar / ocultar",
        icon_size=18,
        on_click=toggle,
    )
    return ft.Row(spacing=6, controls=[ft.Text(label, italic=True), txt, eye])

# ---------------- form ----------------
def _form(record=None) -> ft.Column:
    r = record or {}

    # Empresa
    nome = text_input(_val(r, "nome", "name"), "Nome da empresa*", width=420)
    cnpj = cnpj_input("CNPJ", value=_val(r, "cnpj"), width=220)
    ie   = text_input(_val(r, "ie", "inscricao_estadual"),  "Inscrição Estadual (00.000.000-0)", width=200)
    im   = text_input(_val(r, "im", "inscricao_municipal"), "Inscrição Municipal (000.000-0)",   width=220)
    tel  = phone_input(label="Telefone", value=_val(r, "telefone", "phone"), width=220)
    mail = email_input(label="E-mail",   value=_val(r, "email"), width=300)

    # E-mail principal (login/senha)
    mail_login = text_input(_val(r, "email_principal_login", "email_login", "mail_login"), "E-mail (login)", width=260)
    mail_senha = text_input(_val(r, "email_principal_senha", "email_senha", "mail_senha"), "Senha do e-mail", width=200, password=True, can_reveal_password=True)

    # Endereço
    log = text_input(_val(r, "logradouro", "address_street"), "Logradouro", width=360)
    num = text_input(_val(r, "numero", "address_number"), "Número/Compl.", width=150)
    bai = text_input(_val(r, "bairro", "address_bairro"), "Bairro", width=220)
    cid = text_input(_val(r, "cidade", "address_cidade"), "Cidade", width=220)
    uf_ = uf_input("UF", value=_val(r, "uf", "address_estado"), width=90)
    cep = cep_input(label="CEP", value=_val(r, "cep", "address_cep"), width=150)

    # Banco
    banco   = text_input(_val(r, "banco", "bank_nome"), "Banco", width=240)
    agencia = text_input(_val(r, "agencia", "bank_agencia"), "Agência (0000-0)", width=160)
    conta   = text_input(_val(r, "conta", "bank_conta"), "Conta (000000-0)", width=180)

    # Sócio
    socio_nome = text_input(_val(r, "socio_nome"), "Sócio – Nome", width=320)
    socio_ec   = text_input(_val(r, "socio_estado_civil"), "Sócio – Estado civil", width=180)
    socio_rg   = text_input(_val(r, "socio_rg"), "Sócio – RG (00.000.000-0)", width=200)
    socio_cpf  = cpf_input("Sócio – CPF", value=_val(r, "socio_cpf"), width=220)
    socio_end  = text_input(_val(r, "socio_endereco"), "Sócio – Endereço", width=540)
    socio_nasc = text_input(_val(r, "socio_nascimento", "socio_data_nascimento", "data_nascimento"), "Sócio – Data de nascimento (dd/mm/aaaa)", width=260)
    _attach_date_mask(socio_nasc)
    socio_pai  = text_input(_val(r, "socio_pai", "nome_pai", "pai"), "Sócio – Nome do pai", width=300)
    socio_mae  = text_input(_val(r, "socio_mae", "nome_mae", "mae"), "Sócio – Nome da mãe", width=300)

    # Portais (aceita variações ao exibir; no form mantemos chaves padrão)
    def pfx(prefix: str):
        login = text_input(_val(r, f"{prefix}_login"), "Login", width=220)
        senha = text_input(_val(r, f"{prefix}_senha"), "Senha", width=220, password=True, can_reveal_password=True)
        obs   = text_input(_val(r, f"{prefix}_obs"),   "Observações", width=360)
        return login, senha, obs

    comp_login, comp_senha, comp_obs = pfx("comprasnet")
    pub_login,  pub_senha,  pub_obs  = pfx("pcp")
    bnc_login,  bnc_senha,  bnc_obs  = pfx("bnc")
    lct_login,  lct_senha,  lct_obs  = pfx("licitanet")
    cpa_login,  cpa_senha,  cpa_obs  = pfx("compraspara")

    portais_tabs = ft.Tabs(
        tabs=[
            ft.Tab(text="ComprasNet", content=ft.Column(spacing=8, controls=[ft.Row(spacing=10, controls=[comp_login, comp_senha]), comp_obs])),
            ft.Tab(text="Portal Compras Públicas", content=ft.Column(spacing=8, controls=[ft.Row(spacing=10, controls=[pub_login, pub_senha]), pub_obs])),
            ft.Tab(text="BNC", content=ft.Column(spacing=8, controls=[ft.Row(spacing=10, controls=[bnc_login, bnc_senha]), bnc_obs])),
            ft.Tab(text="Licitanet", content=ft.Column(spacing=8, controls=[ft.Row(spacing=10, controls=[lct_login, lct_senha]), lct_obs])),
            ft.Tab(text="Compras Pará", content=ft.Column(spacing=8, controls=[ft.Row(spacing=10, controls=[cpa_login, cpa_senha]), cpa_obs])),
        ]
    )

    frm = ft.Column(
        spacing=8,
        controls=[
            ft.Row(spacing=10, controls=[FieldRow("Nome da empresa*", nome, 420)]),
            ft.Row(spacing=10, controls=[FieldRow("CNPJ", cnpj, 220), FieldRow("IE", ie, 200), FieldRow("IM", im, 220)]),
            ft.Row(spacing=10, controls=[FieldRow("Telefone", tel, 220), FieldRow("E-mail", mail, 300)]),
            ft.Row(spacing=10, controls=[FieldRow("E-mail (login)", mail_login, 260), FieldRow("Senha do e-mail", mail_senha, 200)]),
            ft.Divider(),
            ft.Row(spacing=10, controls=[FieldRow("Logradouro", log, 360), FieldRow("Número/Compl.", num, 150), FieldRow("Bairro", bai, 220)]),
            ft.Row(spacing=10, controls=[FieldRow("Cidade", cid, 220), FieldRow("UF", uf_, 90), FieldRow("CEP", cep, 150)]),
            ft.Divider(),
            ft.Row(spacing=10, controls=[FieldRow("Banco", banco, 240), FieldRow("Agência", agencia, 160), FieldRow("Conta", conta, 180)]),
            ft.Divider(),
            ft.Row(spacing=10, controls=[FieldRow("Nome", socio_nome, 320), FieldRow("Estado civil", socio_ec, 180), FieldRow("RG", socio_rg, 200), FieldRow("CPF", socio_cpf, 220)]),
            FieldRow("Endereço", socio_end, 540),
            ft.Row(spacing=10, controls=[FieldRow("Data de nascimento", socio_nasc, 260), FieldRow("Nome do pai", socio_pai, 300), FieldRow("Nome da mãe", socio_mae, 300)]),
            ft.Divider(),
            ft.Text("Portais (credenciais por empresa)", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(height=220, content=portais_tabs),
        ],
    )

    def _collect():
        if not (nome.value or "").strip():
            snack_err(frm.page, "Nome é obrigatório.")
            return None
        return {
            # empresa
            "nome": nome.value, "cnpj": cnpj.value, "ie": ie.value, "im": im.value,
            "telefone": tel.value, "email": mail.value,
            "email_principal_login": mail_login.value, "email_principal_senha": mail_senha.value,
            # endereço
            "logradouro": log.value, "numero": num.value, "bairro": bai.value,
            "cidade": cid.value, "uf": uf_.value, "cep": cep.value,
            # banco
            "banco": banco.value, "agencia": agencia.value, "conta": conta.value,
            # sócio
            "socio_nome": socio_nome.value, "socio_estado_civil": socio_ec.value,
            "socio_rg": socio_rg.value, "socio_cpf": socio_cpf.value, "socio_endereco": socio_end.value,
            "socio_nascimento": socio_nasc.value, "socio_pai": socio_pai.value, "socio_mae": socio_mae.value,
            # portais
            "comprasnet_login": comp_login.value, "comprasnet_senha": comp_senha.value, "comprasnet_obs": comp_obs.value,
            "pcp_login": pub_login.value,        "pcp_senha": pub_senha.value,         "pcp_obs": pub_obs.value,
            "bnc_login": bnc_login.value,        "bnc_senha": bnc_senha.value,         "bnc_obs": bnc_obs.value,
            "licitanet_login": lct_login.value,  "licitanet_senha": lct_senha.value,   "licitanet_obs": lct_obs.value,
            "compraspara_login": cpa_login.value,"compraspara_senha": cpa_senha.value, "compraspara_obs": cpa_obs.value,
        }

    frm._collect_payload = _collect  # type: ignore[attr-defined]
    return frm

# ---------------- diálogo (padrão do ZIP: AlertDialog + patch) ----------------
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
                    width=w,
                    height=h,
                    padding=12,
                    content=ft.Column([dlg.content], expand=True, scroll=ft.ScrollMode.ALWAYS),
                )
        except Exception:
            pass
        return _orig_open(dlg)
    page.open = _open_patched

def _dialog(page: ft.Page, title: str, content: ft.Control, on_save):
    """Dialogo padrão com Salvar/Cancelar (para Novo/Editar)."""
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
        try:
            page.close(d)
        except Exception:
            pass
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

# --------- diálogos somente visualização e confirmação (sem "Salvar") ----------
def _viewer_dialog(page: ft.Page, title: str, body: ft.Control):
    """Dialogo de visualização: apenas Fechar (sem Salvar/Cancelar)."""
    _install_page_open_patch(page)
    btn_close = ft.FilledButton("Fechar")
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=body,
        actions=[btn_close],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    btn_close.on_click = lambda e: page.close(d)
    page.open(d)

def _confirm_dialog(page: ft.Page, title: str, message: str, on_confirm):
    """Diálogo compacto de confirmação com 'Excluir' e 'Cancelar'."""
    _install_page_open_patch(page)
    vw = int(getattr(page, "window_width", None) or getattr(page, "width", 1200) or 1200)
    vh = int(getattr(page, "window_height", None) or getattr(page, "height", 800) or 800)
    # tamanho menor e proporcional
    w = int(min(520, max(380, vw * 0.50)))
    h = int(min(260, max(200, vh * 0.30)))

    btn_cancel = ft.TextButton("Cancelar")
    btn_del    = ft.FilledButton("Excluir", icon=ft.Icons.DELETE_OUTLINE)

    body = ft.Container(
        width=w, height=h, padding=12,
        content=ft.Column(
            expand=True, spacing=12,
            controls=[ft.Text(message), ft.Container(expand=True)]
        )
    )
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=body,
        actions=[btn_cancel, btn_del],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    def close():
        try: page.close(d)
        except Exception: pass
    btn_cancel.on_click = lambda e: close()
    btn_del.on_click    = lambda e: (on_confirm(), close())
    page.open(d)

# ---------------- diálogos de detalhes/credenciais ----------------
def _show_details(page: ft.Page, rec: dict):
    # inclui IE/IM e cobre aliases do DB + novos dados do sócio
    grid: list[ft.Control] = [
        ft.Row(spacing=8, controls=[ft.Text("Nome:", weight=ft.FontWeight.BOLD), ft.Text(_name_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("CNPJ:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "cnpj") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("IE:",   weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "ie", "inscricao_estadual", "ie_numero") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("IM:",   weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "im", "inscricao_municipal", "im_numero") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Telefone:", weight=ft.FontWeight.BOLD), ft.Text(_telefone_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("E-mail:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "email") or "—")]),
        _password_row("Senha do e-mail:", _val(rec, "email_principal_senha", "email_senha", "mail_senha")),
        ft.Row(spacing=8, controls=[ft.Text("E-mail (login):", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "email_principal_login", "email_login", "mail_login") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Logradouro:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "logradouro", "address_street") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Número/Compl.:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "numero", "address_number") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Bairro:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "bairro", "address_bairro") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Cidade:", weight=ft.FontWeight.BOLD), ft.Text(_cidade_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("UF:", weight=ft.FontWeight.BOLD), ft.Text(_uf_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("CEP:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "cep", "address_cep") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Banco:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "banco", "bank_nome") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Agência:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "agencia", "bank_agencia") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Conta:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "conta", "bank_conta") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – Nome:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_nome") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – Estado civil:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_estado_civil") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – RG:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_rg") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – CPF:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_cpf") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – Endereço:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_endereco") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – Data de nascimento:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_nascimento", "socio_data_nascimento", "data_nascimento") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – Nome do pai:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_pai", "nome_pai", "pai") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Sócio – Nome da mãe:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "socio_mae", "nome_mae", "mae") or "—")]),
    ]
    _viewer_dialog(page, "🔎 Detalhes da empresa", ft.Column(spacing=6, controls=grid))

def _show_credentials(page: ft.Page, rec: dict):
    # cobre aliases e inclui e-mail principal com olhinho
    def trio(prefixes: tuple[str, ...]):
        lg = _val(rec, *(f"{p}_login" for p in prefixes))
        sh = _val(rec, *(f"{p}_senha" for p in prefixes))
        ob = _val(rec, *(f"{p}_obs"   for p in prefixes))
        return lg, sh, ob

    comprasnet_aliases  = ("comprasnet", "compras_gov", "comprasgovbr", "compras_gov_br")
    pcp_aliases         = ("pcp", "portalcompras", "portal_compras_publicas")
    bnc_aliases         = ("bnc", "bionexo")
    licitanet_aliases   = ("licitanet",)
    compraspara_aliases = ("compraspara", "compras_pa", "compraspara_pa")

    blocks = [
        ("E-MAIL PRINCIPAL",
         (_val(rec, "email_principal_login","email_login","mail_login"),
          _val(rec, "email_principal_senha","email_senha","mail_senha"), "")),
        ("COMPRAS.GOV.BR",  trio(comprasnet_aliases)),
        ("PORTAL COMPRAS PÚBLICAS", trio(pcp_aliases)),
        ("BIONEXO / BNC",   trio(bnc_aliases)),
        ("LICITANET",       trio(licitanet_aliases)),
        ("COMPRAS PARÁ",    trio(compraspara_aliases)),
    ]

    def bloco(label, vals):
        lg, sh, ob = vals
        rows: list[ft.Control] = [
            ft.Text(label, weight=ft.FontWeight.BOLD),
            ft.Row(spacing=6, controls=[ft.Text("Login:", italic=True), ft.Text(lg or "—")]),
            _password_row("Senha:", sh),
        ]
        if label != "E-MAIL PRINCIPAL":
            rows.append(ft.Row(spacing=6, controls=[ft.Text("Obs.:", italic=True), ft.Text(ob or "—")]))
        rows.append(ft.Divider())
        return ft.Column(spacing=4, controls=rows)

    body = ft.Column(spacing=8, controls=[bloco(lbl, vals) for lbl, vals in blocks])
    _viewer_dialog(page, "🔑 Credenciais", body)

# ---------------- página ----------------
def page_empresas(page: ft.Page) -> ft.Control:
    funcs = _pick_db()

    # Tabela padrão (mantendo layout consolidado)
    h0 = (page.window_height or page.height or 720)
    tbl = SimpleTable(COLUMNS, include_master=True, zebra=True, height=max(360, h0 - BASE_DESCONTO))
    lbl_count = ft.Text("", size=12)

    rows_cache: list[dict] = []  # cache do último load

    # carregar
    def load():
        nonlocal rows_cache
        rows = []
        if funcs.get("list"):
            try:
                rows = funcs["list"]() or []
            except Exception as ex:
                snack_err(page, f"Erro ao listar: {ex}")
                rows = []
        rows_cache = rows[:]  # mantém bruto para ver mais / credenciais
        adapted = []
        for r in rows:
            adapted.append({
                "id": _get(r, "id"),
                "ID": _get(r, "id", ""),
                "Nome": _name_from(r),
                "CNPJ": _val(r, "cnpj"),
                "Telefone": _telefone_from(r),
                "E-mail": _val(r, "email"),
                "Cidade": _cidade_from(r),
                "UF": _uf_from(r),
            })
        tbl.set_rows(adapted)
        lbl_count.value = f"{len(adapted)} registro(s)."
        page.update()

    def _find_rec_by_id(rid):
        for r in rows_cache:
            if _get(r, "id") == rid:
                return r
        return None

    # ações
    def new():
        frm = _form()
        def save(close):
            payload = frm._collect_payload()  # type: ignore[attr-defined]
            if not payload:
                return
            if not funcs.get("add"):
                close(); return snack_err(page, "add_company() indisponível no DB.")
            try:
                funcs["add"](payload)
                close(); snack_ok(page, "Empresa criada."); load()
            except Exception as ex:
                close(); snack_err(page, f"Erro ao salvar: {ex}")
        _dialog(page, "➕ Nova empresa", frm, save)

    def edit():
        sel = tbl.selected_ids()
        if not sel:
            return snack_err(page, "Selecione uma linha.")
        rid = sel[0]
        rec = None
        if funcs.get("get"):
            try:
                rec = funcs["get"](rid)
            except Exception:
                rec = None
        if not rec and funcs.get("list"):
            try:
                for r in funcs["list"]() or []:
                    if _get(r, "id") == rid:
                        rec = dict(r) if hasattr(r, "keys") else (r if isinstance(r, dict) else {})
                        break
            except Exception:
                rec = None
        if not rec:
            return snack_err(page, "Registro não encontrado.")

        frm = _form(rec)
        def save(close):
            payload = frm._collect_payload()  # type: ignore[attr-defined]
            if not payload:
                return
            if not funcs.get("upd"):
                close(); return snack_err(page, "upd_company() indisponível no DB.")
            try:
                funcs["upd"](rid, payload)
                close(); snack_ok(page, "Empresa atualizada."); load()
            except Exception as ex:
                close(); snack_err(page, f"Erro: {ex}")
        _dialog(page, "✏️ Editar empresa", frm, save)

    def delete():
        sel = tbl.selected_ids()
        if not sel:
            return snack_err(page, "Selecione ao menos uma linha.")
        ids = sel[:]
        def do_confirm():
            if not funcs.get("del"):
                return snack_err(page, "del_company() indisponível no DB.")
            ok = 0; fail = 0
            for rid in ids:
                try:
                    funcs["del"](rid); ok += 1
                except Exception:
                    fail += 1
            snack_ok(page, f"Excluídos: {ok} • Falhas: {fail}"); load()
        _confirm_dialog(page, "Excluir empresas", f"Confirmar exclusão de {len(ids)} registro(s)?", do_confirm)

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Empresas", size=18, weight=ft.FontWeight.BOLD),
            ft.Row(
                spacing=8,
                controls=[
                    ft.FilledButton("➕ Nova", on_click=lambda e: new()),
                    ft.OutlinedButton("✏️ Editar", on_click=lambda e: edit()),
                    ft.OutlinedButton("🗑️ Excluir", on_click=lambda e: delete()),
                    ft.OutlinedButton("Atualizar", on_click=lambda e: load()),
                    ft.OutlinedButton("Selecionar todos", on_click=lambda e: (tbl.select_all(), page.update())),
                    ft.OutlinedButton("Desmarcar", on_click=lambda e: (tbl.clear_selection(), page.update())),
                    # visualização
                    ft.OutlinedButton(
                        "🔎 Ver mais",
                        on_click=lambda e: (
                            _show_details(page, _find_rec_by_id(tbl.selected_ids()[0]))
                            if tbl.selected_ids() else snack_err(page, "Selecione uma linha.")
                        ),
                    ),
                    ft.OutlinedButton(
                        "🔑 Credenciais",
                        on_click=lambda e: (
                            _show_credentials(page, _find_rec_by_id(tbl.selected_ids()[0]))
                            if tbl.selected_ids() else snack_err(page, "Selecione uma linha.")
                        ),
                    ),
                ],
            ),
        ],
    )
    divider = ft.Divider(height=1, thickness=1, color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE))

    quadro = ft.Row(expand=True, controls=[ft.Container(expand=True, content=tbl.control())])

    footer = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
        border_radius=10, padding=ft.Padding(10, 8, 10, 8),
        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[lbl_count, ft.Text("Clique na caixa para selecionar.", size=12)]),
    )

    layout = ft.Column(expand=True, spacing=8, controls=[header, divider, quadro, footer])

    # resize → ajusta altura da tabela (mantendo seu layout consolidado)
    prev = page.on_resized
    def _on_resized(e=None):
        try:
            if prev: prev(e) if callable(prev) and e is not None else (prev() if callable(prev) else None)
        except Exception:
            pass
        nh = max(360, (page.window_height or page.height or 720) - BASE_DESCONTO)
        tbl.set_height(nh); page.update()
    page.on_resized = _on_resized
    _on_resized(None)

    load()
    return ft.Container(
         expand=True,
         content=ft.Column(
             scroll=ft.ScrollMode.AUTO,
             controls=[layout],
             ),
    )
