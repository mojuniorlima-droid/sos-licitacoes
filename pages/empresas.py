# pages/empresas.py
from __future__ import annotations

import flet as ft

# --- Imports tolerantes ---
try:
    import services.db as db
except Exception:
    class _DBStub: ...
    db = _DBStub()

try:
    from components.tableview import SimpleTable
except Exception:
    class SimpleTable(ft.UserControl):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self._rows = []
            self._height = kwargs.get("height", 400)
            self._cols = args[0] if args else []
            self._include_master = kwargs.get("include_master", True)

        def set_rows(self, rows):
            self._rows = rows
            if hasattr(self, "update"): self.update()

        def set_height(self, h: int):
            self._height = h
            if hasattr(self, "update"): self.update()

        def selected_ids(self) -> list:
            # implementação mínima para compat local
            return [r.get("id") for r in self._rows[:1] if r.get("id") is not None]

        def select_all(self):
            pass

        def clear_selection(self):
            pass

        def build(self):
            return ft.Container(
                height=self._height,
                border=ft.border.all(1, ft.colors.with_opacity(0.12, ft.colors.BLACK)),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[ft.Text("Tabela indisponível (stub) – verifique components/tableview.py)")]
                        ),
                        ft.ListView(
                            expand=True,
                            controls=[ft.Text(str(r)) for r in self._rows]
                        ),
                    ],
                    expand=True,
                ),
            )

try:
    from components.forms import (
        FieldRow, snack_ok, snack_err, text_input, email_input, phone_input, cep_input, uf_input
    )
except Exception:
    class FieldRow(ft.Row):
        def __init__(self, label: str, control: ft.Control, width: int | None = None):
            super().__init__(spacing=6)
            self.controls = [ft.Text(label, width=160, weight=ft.FontWeight.BOLD), control]
            if width:
                control.width = width

    def snack_ok(page, msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg)); page.snack_bar.open = True; page.update()

    def snack_err(page, msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg)); page.snack_bar.open = True; page.update()

    def text_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)

    def email_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)

    def phone_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)

    def cep_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)

    def uf_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)

try:
    from components.inputs import cnpj_input, cpf_input
except Exception:
    def cnpj_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)
    def cpf_input(value="", label="", width=None, **k): 
        return ft.TextField(value=value, label=label, width=width)

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
        "nome", "razao", "razao_social", "empresa_nome", "company_name", "razaoNome", "razao_social_nome",
        default="(sem nome)"
    )

def _telefone_from(r):
    return _val(r, "telefone", "phone", "tel", default="")

def _cidade_from(r):
    return _val(r, "cidade", "city", "municipio", default="")

def _uf_from(r):
    return _val(r, "uf", "estado", "state", default="")

# --------- DB picks (apoio a aliases herdados) ---------
def _pick_db():
    """
    Seleciona funções do DB com tolerância a aliases (herdados do ZIP).
    Ex.: list_company, empresas_list, list_empresas, etc.
    """
    def pick(*names):
        for n in names:
            if hasattr(db, n):
                fn = getattr(db, n)
                if callable(fn):
                    return fn
        return None

    return {
        "list": pick("list_company", "empresas_list", "list_empresas", "companies", "list_companies"),
        "add":  pick("add_company", "empresa_add", "insert_empresa", "create_empresa"),
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
    tf = ft.TextField(value=value, password=True, can_reveal_password=True, read_only=True, width=280)
    return ft.Row(controls=[ft.Text(label, width=160, weight=ft.FontWeight.BOLD), tf], spacing=8)

# ---------------- formulário ----------------
def _form(r: dict | None = None) -> ft.Column:
    r = r or {}

    nome = text_input(_val(r, "nome", "razao", "razao_social", "empresa_nome"), "Nome da empresa*", width=420)
    cnpj = cnpj_input(value=_val(r, "cnpj"), label="CNPJ", width=220)
    ie   = text_input(_val(r, "ie", "inscricao_estadual"), "IE", width=200)
    im   = text_input(_val(r, "im", "inscricao_municipal"), "IM", width=220)

    tel  = phone_input(_val(r, "telefone", "phone", "tel"), "Telefone", width=220)
    mail = email_input(_val(r, "email"), "E-mail", width=300)
    mail_login = email_input(_val(r, "email_principal_login", "email_login"), "E-mail (login)", width=260)
    mail_senha = text_input(_val(r, "email_principal_senha", "email_senha"), "Senha do e-mail", width=200, password=True, can_reveal_password=True)

    log = text_input(_val(r, "logradouro", "address_logradouro"), "Logradouro", width=340)
    num = text_input(_val(r, "numero", "address_numero"), "Número/Compl.", width=150)
    bai = text_input(_val(r, "bairro", "address_bairro"), "Bairro", width=220)
    cid = text_input(_val(r, "cidade", "city", "municipio"), "Cidade", width=260)
    uf_ = uf_input(_val(r, "uf", "estado", "state"), "UF", width=80)
    cep = cep_input(_val(r, "cep", "address_cep"), "CEP", width=140)

    banco   = text_input(_val(r, "banco", "bank_nome"), "Banco", width=220)
    agencia = text_input(_val(r, "agencia", "bank_agencia"), "Agência", width=180)
    conta   = text_input(_val(r, "conta", "bank_conta"), "Conta", width=200)

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

    # Tabs de portais (web-safe)
    portais_tabs = ft.Tabs(
        tabs=[
            ft.Tab(
                text="ComprasNet",
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[comp_login, comp_senha]),
                    comp_obs
                ]),
            ),
            ft.Tab(
                text="Portal Compras Públicas",
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[pub_login, pub_senha]),
                    pub_obs
                ]),
            ),
            ft.Tab(
                text="BNC",
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[bnc_login, bnc_senha]),
                    bnc_obs
                ]),
            ),
            ft.Tab(
                text="Licitanet",
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[lct_login, lct_senha]),
                    lct_obs
                ]),
            ),
            ft.Tab(
                text="Compras Pará",
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[cpa_login, cpa_senha]),
                    cpa_obs
                ]),
            ),
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
            ft.Row(spacing=10, controls=[FieldRow("Logradouro", log, 340), FieldRow("Número/Compl.", num, 150), FieldRow("Bairro", bai, 220)]),
            ft.Row(spacing=10, controls=[FieldRow("Cidade", cid, 260), FieldRow("UF", uf_, 80), FieldRow("CEP", cep, 140)]),
            ft.Divider(),
            ft.Row(spacing=10, controls=[FieldRow("Banco", banco, 220), FieldRow("Agência", agencia, 180), FieldRow("Conta", conta, 200)]),
            ft.Divider(),
            ft.Row(spacing=10, controls=[FieldRow("Sócio – Nome", socio_nome, 320), FieldRow("Estado civil", socio_ec, 180), FieldRow("RG", socio_rg, 200)]),
            ft.Row(spacing=10, controls=[FieldRow("Sócio – CPF", socio_cpf, 220), FieldRow("Data de nascimento", socio_nasc, 260)]),
            ft.Row(spacing=10, controls=[FieldRow("Sócio – Endereço", socio_end, 540)]),
            ft.Row(spacing=10, controls=[FieldRow("Sócio – Nome do pai", socio_pai, 300), FieldRow("Sócio – Nome da mãe", socio_mae, 300)]),
            ft.Divider(),
            ft.Text("Portais de compras", weight=ft.FontWeight.BOLD),
            portais_tabs,
        ],
    )

    def _collect():
        return {
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
            "pcp_login": pub_login.value, "pcp_senha": pub_senha.value, "pcp_obs": pub_obs.value,
            "bnc_login": bnc_login.value, "bnc_senha": bnc_senha.value, "bnc_obs": bnc_obs.value,
            "licitanet_login": lct_login.value, "licitanet_senha": lct_senha.value, "licitanet_obs": lct_obs.value,
            "compraspara_login": cpa_login.value, "compraspara_senha": cpa_senha.value, "compraspara_obs": cpa_obs.value,
        }

    frm._collect_payload = _collect  # type: ignore[attr-defined]
    return frm

# ---------------- diálogo (padrão do ZIP: AlertDialog + patch) ----------------
def _install_page_open_patch(page: ft.Page):
    if getattr(page, "_novo5_dialog_patch", False):
        return
    page._novo5_dialog_patch = True
    _orig_open = page.open

    def _open_patched(dlg: ft.AlertDialog):
        # garante rolagem interna em conteúdo grande
        if isinstance(dlg.content, ft.Container) and isinstance(dlg.content.content, ft.Column):
            dlg.content.content.scroll = ft.ScrollMode.AUTO
        return _orig_open(dlg)

    page.open = _open_patched  # type: ignore[assignment]

def _dialog(page: ft.Page, title: str, body: ft.Control, on_save=None):
    _install_page_open_patch(page)
    vw = int(getattr(page, "width", 1200) or 1200)
    vh = int(getattr(page, "height", 800) or 800)
    w = int(min(980, max(680, vw * 0.80)))
    h = int(min(620, max(420, vh * 0.70)))

    btn_close = ft.TextButton("Fechar")
    btn_save  = ft.FilledButton("Salvar", icon=ft.icons.SAVE)

    body = ft.Container(
        width=w, height=h, padding=12,
        content=ft.Column(
            expand=True, spacing=12,
            controls=[body]
        )
    )
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=body,
        actions=[btn_close, btn_save] if on_save else [btn_close],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    def close_dlg(*_):
        try: page.close(d)
        except Exception: pass
    btn_close.on_click = close_dlg
    if on_save:
        btn_save.on_click = lambda e: on_save(close_dlg)
    page.open(d); page.update()

def _viewer_dialog(page: ft.Page, title: str, content: ft.Control):
    _install_page_open_patch(page)
    vw = int(getattr(page, "width", 1200) or 1200)
    vh = int(getattr(page, "height", 800) or 800)
    w = int(min(980, max(680, vw * 0.80)))
    h = int(min(620, max(420, vh * 0.70)))

    body = ft.Container(
        width=w, height=h, padding=12,
        content=ft.Column(expand=True, spacing=12, controls=[content], scroll=ft.ScrollMode.AUTO),
    )
    d = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
        content=body,
        actions=[ft.TextButton("Fechar", on_click=lambda e: page.close(d))],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(d); page.update()

def _confirm_dialog(page: ft.Page, title: str, message: str, on_confirm):
    """Diálogo compacto de confirmação com 'Excluir' e 'Cancelar'."""
    _install_page_open_patch(page)
    vw = int(getattr(page, "width", 1200) or 1200)
    vh = int(getattr(page, "height", 800) or 800)
    # tamanho menor e proporcional
    w = int(min(520, max(380, vw * 0.50)))
    h = int(min(260, max(200, vh * 0.30)))

    btn_cancel = ft.TextButton("Cancelar")
    btn_del    = ft.FilledButton("Excluir", icon=ft.icons.DELETE_OUTLINE)

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
    page.open(d); page.update()

# ---------------- visualização “ver mais” / credenciais ----------------
def _show_details(page: ft.Page, rec: dict | None):
    if not rec:
        return snack_err(page, "Registro não encontrado.")
    grid = [
        ft.Row(spacing=8, controls=[ft.Text("Nome:", weight=ft.FontWeight.BOLD), ft.Text(_name_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("CNPJ:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "cnpj") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Telefone:", weight=ft.FontWeight.BOLD), ft.Text(_telefone_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("E-mail:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "email") or "—")]),
        ft.Divider(),
        ft.Row(spacing=8, controls=[ft.Text("Logradouro:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "logradouro", "address_logradouro") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Número/Compl.:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "numero", "address_number") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Bairro:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "bairro", "address_bairro") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Cidade:", weight=ft.FontWeight.BOLD), ft.Text(_cidade_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("UF:", weight=ft.FontWeight.BOLD), ft.Text(_uf_from(rec) or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("CEP:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "cep", "address_cep") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Banco:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "banco", "bank_nome") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Agência:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "agencia", "bank_agencia") or "—")]),
        ft.Row(spacing=8, controls=[ft.Text("Conta:", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "conta", "bank_conta") or "—")]),
        ft.Divider(),
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
    compraspara_aliases = ("compraspara", "compras_pará", "compras_para")

    comp = trio(comprasnet_aliases)
    pcp  = trio(pcp_aliases)
    bnc  = trio(bnc_aliases)
    lct  = trio(licitanet_aliases)
    cpa  = trio(compraspara_aliases)

    rows = [
        ft.Row(spacing=8, controls=[ft.Text("E-mail (login):", weight=ft.FontWeight.BOLD), ft.Text(_val(rec, "email_principal_login", "email_login") or "—")]),
        _password_row("E-mail (senha):", _val(rec, "email_principal_senha", "email_senha") or ""),
        ft.Divider(),
        ft.Text("ComprasNet", weight=ft.FontWeight.BOLD),
        ft.Row(spacing=8, controls=[ft.Text("Login:", width=160, weight=ft.FontWeight.BOLD), ft.Text(comp[0] or "—")]),
        _password_row("Senha:", comp[1] or ""),
        ft.Text(f"Obs.: {comp[2] or '—'}"),
        ft.Divider(),
        ft.Text("Portal Compras Públicas", weight=ft.FontWeight.BOLD),
        ft.Row(spacing=8, controls=[ft.Text("Login:", width=160, weight=ft.FontWeight.BOLD), ft.Text(pcp[0] or "—")]),
        _password_row("Senha:", pcp[1] or ""),
        ft.Text(f"Obs.: {pcp[2] or '—'}"),
        ft.Divider(),
        ft.Text("BNC", weight=ft.FontWeight.BOLD),
        ft.Row(spacing=8, controls=[ft.Text("Login:", width=160, weight=ft.FontWeight.BOLD), ft.Text(bnc[0] or "—")]),
        _password_row("Senha:", bnc[1] or ""),
        ft.Text(f"Obs.: {bnc[2] or '—'}"),
        ft.Divider(),
        ft.Text("Licitanet", weight=ft.FontWeight.BOLD),
        ft.Row(spacing=8, controls=[ft.Text("Login:", width=160, weight=ft.FontWeight.BOLD), ft.Text(lct[0] or "—")]),
        _password_row("Senha:", lct[1] or ""),
        ft.Text(f"Obs.: {lct[2] or '—'}"),
        ft.Divider(),
        ft.Text("Compras Pará", weight=ft.FontWeight.BOLD),
        ft.Row(spacing=8, controls=[ft.Text("Login:", width=160, weight=ft.FontWeight.BOLD), ft.Text(cpa[0] or "—")]),
        _password_row("Senha:", cpa[1] or ""),
        ft.Text(f"Obs.: {cpa[2] or '—'}"),
    ]
    _viewer_dialog(page, "🔐 Credenciais de portais", ft.Column(spacing=6, controls=rows))

# ---------------- página ----------------
def page_empresas(page: ft.Page) -> ft.Control:
    funcs = _pick_db()

    # Tabela padrão (mantendo layout consolidado)
    h0 = (page.height or 720)
    tbl = SimpleTable(COLUMNS, include_master=True, zebra=True, height=max(360, h0 - BASE_DESCONTO))
    lbl_count = ft.Text("", size=12)

    rows_cache: list[dict] = []  # cache do último load

    # carregar
    def load():
        nonlocal rows_cache
        rows = []
        if funcs.get("list"):
            try:
                for r in funcs["list"]() or []:
                    try:
                        rows.append(dict(r) if hasattr(r, "keys") else (r if isinstance(r, dict) else {}))
                    except Exception:
                        pass
            except Exception:
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
                close(); snack_err(page, f"Erro: {ex}")
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
                        "🔐 Credenciais",
                        on_click=lambda e: (
                            _show_credentials(page, _find_rec_by_id(tbl.selected_ids()[0]))
                            if tbl.selected_ids() else snack_err(page, "Selecione uma linha.")
                        ),
                    ),
                    lbl_count,
                ],
            ),
        ],
    )

    layout = ft.Column(
        expand=True,
        controls=[
            header,
            ft.Container(height=6),
            tbl,
            ft.Container(
                padding=ft.padding.only(top=6),
                content=ft.Text("Clique na caixa para selecionar.", size=12, color=ft.colors.ON_SURFACE_VARIANT),
            ),
        ],
    )

    # altura responsiva da tabela
    def _on_resized(e):
        try:
            pass
        except Exception:
            pass
        nh = max(360, (page.height or 720) - BASE_DESCONTO)
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

# Compat: alguns roteadores chamam view(page)
def view(page: ft.Page) -> ft.Control:
    return page_empresas(page)
