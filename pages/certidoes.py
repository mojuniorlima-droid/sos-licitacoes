from __future__ import annotations
import flet as ft
from pathlib import Path
import shutil
import urllib.parse
from datetime import datetime

from services import db
from components.tableview import SimpleTable
from components.forms import FieldRow, snack_ok, snack_err, text_input, date_input

# ----------------- Config -----------------
BASE_DESCONTO = 240
SITUACOES = ["Válida", "Vencida", "Pendente"]
PESSOAS = ["Pessoa Física", "Pessoa Jurídica"]
AUTO_DELETE_PDF_ON_RECORD_DELETE = True

# Faixas de alerta (Certidões): 15 / 7 / 1 (leve / moderado / urgente)
ALERTA_LEVE_DIAS = 15
ALERTA_MODERADO_DIAS = 7
ALERTA_URGENTE_DIAS = 1  # 1 dia = urgente

COLUMNS = [
    "ID","Empresa","Tipo","Órgão","Situação","Número","Emissão","Validade",
    "Verificação","PDF","Observações"
]

# ----------------- Helpers -----------------
def _list_empresas() -> list[tuple[int,str]]:
    out = []
    for name in ("list_empresas","empresas_all","get_empresas"):
        if hasattr(db, name):
            try:
                for r in getattr(db, name)() or []:
                    rid = r.get("id"); nm = r.get("name") or r.get("nome")
                    if rid: out.append((rid, nm or f"Empresa {rid}"))
                break
            except Exception:
                pass
    return sorted(out, key=lambda x: (x[1] or "").lower())

def page_certidoes(page: ft.Page) -> ft.Control:
    BTN_COMPACT = ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=6))

    # Raiz de assets + uploads/certidoes
    _default_root = Path(__file__).resolve().parent
    assets_root = Path(getattr(page, "assets_dir", str(_default_root)) or _default_root).resolve()
    uploads_dir = assets_root / "uploads" / "certidoes"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # --- Snacks com fallback ---
    def _notify_ok(msg: str):
        try:
            snack_ok(page, msg)
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text(msg))
            page.snack_bar.open = True
            page.update()

    def _notify_err(msg: str):
        try:
            snack_err(page, msg)
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=ft.colors.RED_400)
            page.snack_bar.open = True
            page.update()

    # --- Datas / formatos ---
    def _parse_br(d: str) -> datetime | None:
        try: return datetime.strptime(d.strip(), "%d/%m/%Y") if d else None
        except Exception: return None

    def _situation_badge(validade_br: str, situacao_base: str) -> str:
        """
        Retorna string da coluna Situação com classificação colorida por emoji:
        - 🔵 Leve (0 < dias <= 15 e > 7)
        - 🟡 Moderado (0 < dias <= 7 e > 1)
        - 🔴 Urgente (dias == 1)
        - Vencida (dias <= 0)  ← corrige o caso 'Válida (0d)'
        - Válida (dias > 15)   ← sem alerta
        """
        if (situacao_base or "").strip().lower() == "pendente":
            return "Pendente"

        dtv = _parse_br(validade_br)
        if not dtv:
            return "Indefinida"

        hoje = datetime.now().date()
        diff = (dtv.date() - hoje).days

        if diff <= 0:
            # já venceu ou vence hoje → contar como vencida; mostra 0d corretamente
            return f"Vencida (há {abs(diff)}d)"

        # Faixas de alerta
        if diff == ALERTA_URGENTE_DIAS:
            return f"🔴 Urgente ({diff}d)"
        if diff <= ALERTA_MODERADO_DIAS:
            return f"🟡 Moderado ({diff}d)"
        if diff <= ALERTA_LEVE_DIAS:
            return f"🔵 Leve ({diff}d)"

        return f"Válida ({diff}d)"

    # --- Normalização de caminho/URL (robusto para OneDrive) ---
    def _to_assets_rel(pdf: str) -> str:
        """
        Normaliza para algo utilizável:
        - http(s) -> mantém
        - OneDrive/absoluto -> tenta relativizar; senão, mapeia pelo nome para uploads/certidoes/
        - nome simples -> uploads/certidoes/<nome>.pdf (busca case-insensitive)
        - corrige .pd -> .pdf
        """
        if not pdf:
            return ""
        raw = (pdf or "").strip().strip('"').strip("'")

        if raw.lower().startswith(("http://", "https://")):
            return raw

        if raw.lower().endswith(".pd"):
            raw = raw + "f"

        if raw.startswith("/"):
            raw = raw[1:]

        if raw.lower().startswith("uploads/"):
            return raw.replace("\\", "/")

        p = Path(raw)

        # Caminho absoluto (inclui OneDrive)
        if p.is_absolute():
            if p.exists():
                try:
                    rel = p.resolve().relative_to(assets_root)
                    return str(rel).replace("\\", "/")
                except Exception:
                    pass
            name = p.name
            if not name.lower().endswith(".pdf"):
                name += ".pdf"
            cand = uploads_dir / name
            if cand.exists():
                return f"uploads/certidoes/{cand.name}"
            for f in uploads_dir.iterdir():
                if f.is_file() and f.suffix.lower() == ".pdf" and f.name.lower() == name.lower():
                    return f"uploads/certidoes/{f.name}"
            return str(p)

        # Só nome
        if ("/" not in raw) and ("\\" not in raw):
            name = raw if raw.lower().endswith(".pdf") else raw + ".pdf"
            cand = uploads_dir / name
            if cand.exists():
                return f"uploads/certidoes/{cand.name}"
            for f in uploads_dir.iterdir():
                if f.is_file() and f.suffix.lower()==".pdf" and f.name.lower()==name.lower():
                    return f"uploads/certidoes/{f.name}"
            return name

        return raw.replace("\\", "/")

    def _normalize_url(url: str) -> str:
        if not url: return ""
        url = url.strip()
        return url if url.startswith(("http://", "https://")) else "https://" + url

    def _file_to_uri(p: Path) -> str:
        return "file://" + urllib.parse.quote(str(p.resolve()).replace("\\", "/"))

    # ---------- Filtros ----------
    emp_opts = [ft.dropdown.Option("", "Todas as empresas")] + [
        ft.dropdown.Option(str(i), n) for i, n in _list_empresas()
    ]
    f_empresa  = ft.Dropdown(dense=True, width=260, options=emp_opts, value="")
    f_situacao = ft.Dropdown(dense=True, width=160,
                             options=[ft.dropdown.Option("Todas")] + [ft.dropdown.Option(s) for s in SITUACOES],
                             value="Todas")
    f_tipo     = ft.TextField(dense=True, width=200, hint_text="Tipo (ex.: FGTS, INSS)")
    f_busca    = ft.TextField(dense=True, width=240, hint_text="Buscar: nº/órgão/tipo")

    # ---------- Tabela ----------
    tbl = SimpleTable(COLUMNS, include_master=True, zebra=True,
                      height=max(240, page.window_height - BASE_DESCONTO))
    lbl_count = ft.Text("", size=12)
    row_extras: dict[int, dict] = {}

    def load():
        row_extras.clear()
        try:
            emp_id = int(f_empresa.value) if (f_empresa.value not in ("", None)) else None
        except Exception:
            emp_id = None

        rows_src = db.list_certidoes({
            "empresa_id": emp_id,
            "situacao": f_situacao.value,
            "tipo": (f_tipo.value or "").strip() or "Todos",
            "q": (f_busca.value or "").strip(),
        }) or []

        rows = []
        for r in rows_src:
            cid   = int(r.get("id"))
            link  = (r.get("link_consulta") or "").strip()
            arq   = (r.get("arquivo") or "").strip()
            pdf_norm = _to_assets_rel(arq)

            emissao   = r.get("dt_emissao") or ""
            validade  = r.get("dt_validade") or ""
            situ_base = r.get("situacao") or ""
            sit_col   = _situation_badge(validade, situ_base)

            row_extras[cid] = {"link": link, "pdf": pdf_norm, "validade": validade}
            rows.append({
                "id": cid,
                "ID": cid,
                "Empresa": r.get("empresa") or "",
                "Tipo": r.get("tipo") or "",
                "Órgão": r.get("orgao_emissor") or "",
                "Situação": sit_col,
                "Número": r.get("numero") or "",
                "Emissão": emissao,
                "Validade": validade,
                "Verificação": "🔗" if link else "",
                "PDF": "📄" if bool(pdf_norm) else "",
                "Observações": r.get("observacoes") or "",
            })

        tbl.set_rows(rows)
        lbl_count.value = f"{len(rows)} registro(s)"
        page.update()

    # ---------- FilePickers ----------
    file_picker = ft.FilePicker()    # anexar
    save_picker = ft.FilePicker()    # salvar/baixar
    # garantir ambos nos overlays
    try:
        page.overlay.extend([file_picker, save_picker])
    except Exception:
        page.overlay.append(file_picker)
        page.overlay.append(save_picker)

    # ---------- Form ----------
    def _form(rec: dict | None = None) -> ft.Control:
        empresas = _list_empresas()
        dd_emp = ft.Dropdown(dense=True, width=360, options=[ft.dropdown.Option(i, n) for i, n in empresas])
        pessoa = ft.Dropdown(dense=True, width=140, options=[ft.dropdown.Option(p) for p in PESSOAS], value=PESSOAS[1])

        tipo   = text_input("", "", width=180); tipo.hint_text = "Ex.: FGTS, INSS, Municipal..."
        orgao  = text_input("", "", width=200); orgao.hint_text = "Órgão emissor"
        numero = text_input("", "", width=180); numero.hint_text = "Número/ID"
        situ   = ft.Dropdown(dense=True, width=140, options=[ft.dropdown.Option(s) for s in SITUACOES])
        emissa = date_input("Emissão (dd/mm/aaaa)", value="", width=150)
        valid  = date_input("Validade (dd/mm/aaaa)", value="", width=150)
        link   = text_input("", "", width=420); link.hint_text = "URL de verificação / consulta"

        pdf_path_val = {"value": ""}  # 'uploads/certidoes/<nome>.pdf'
        lbl_pdf = ft.Text("", size=12, selectable=True, overflow=ft.TextOverflow.ELLIPSIS, width=420)

        def _pick_pdf(e=None):
            def on_result(res: ft.FilePickerResultEvent):
                if not res or not res.files:
                    return
                f = res.files[0]
                try:
                    if getattr(f, "path", None):
                        src = Path(f.path)
                        safe_name = src.name.replace(" ", "_")
                        dst = uploads_dir / safe_name
                        i = 1
                        while dst.exists():
                            stem = src.stem.replace(" ", "_")
                            dst = uploads_dir / f"{stem}_{i}{src.suffix}"
                            i += 1
                        shutil.copy2(src, dst)
                        pdf_path_val["value"] = f"uploads/certidoes/{dst.name}"
                        lbl_pdf.value = f"Anexado: {dst.name}"
                        page.update()
                    else:
                        pdf_path_val["value"] = f.name
                        lbl_pdf.value = f"Selecionado: {f.name}"
                        page.update()
                except Exception as ex:
                    _notify_err(f"Falha ao anexar: {ex}")

            file_picker.on_result = on_result
            file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["pdf"],
                file_type=ft.FilePickerFileType.CUSTOM
            )

        btn_pdf = ft.FilledButton("Anexar PDF", icon=ft.Icons.PICTURE_AS_PDF,
                                  on_click=_pick_pdf, style=BTN_COMPACT)
        obs    = text_input("", "", width=940, multiline=True)

        if rec:
            alvo = rec.get("Empresa") or ""
            for i, n in empresas:
                if n == alvo:
                    dd_emp.value = i
                    break
            tipo.value   = rec.get("Tipo") or ""
            orgao.value  = rec.get("Órgão") or ""
            numero.value = rec.get("Número") or ""
            situ.value   = (rec.get("Situação") or "").split(" ")[0] or None
            emissa.value = rec.get("Emissão") or ""
            valid.value  = rec.get("Validade") or ""
            try:
                rid = int(rec.get("ID"))
                link_raw = row_extras.get(rid, {}).get("link", "")
                pdf_raw  = row_extras.get(rid, {}).get("pdf", "")
            except Exception:
                link_raw, pdf_raw = "", ""
            link.value = link_raw
            if pdf_raw:
                lbl_pdf.value = f"Anexado: {Path(str(pdf_raw)).name}"
                pdf_path_val["value"] = str(pdf_raw)

        frm = ft.Column(spacing=8, controls=[
            ft.Row(spacing=10, controls=[
                FieldRow("Empresa", dd_emp, 360),
                FieldRow("Pessoa", pessoa, 140),
                FieldRow("Tipo", tipo, 180),
                FieldRow("Órgão emissor", orgao, 200),
            ]),
            ft.Row(spacing=10, controls=[
                FieldRow("Número", numero, 180),
                FieldRow("Situação", situ, 140),
                FieldRow("Emissão", emissa, 150),
                FieldRow("Validade", valid, 150),
            ]),
            ft.Row(spacing=10, controls=[
                FieldRow("Link de verificação", link, 420),
                FieldRow("Certidão (PDF)", ft.Row(spacing=8, controls=[btn_pdf, lbl_pdf]), 420),
            ]),
            ft.Row(spacing=10, controls=[ FieldRow("Observações", obs, 940) ]),
        ])

        def _collect():
            raw_pdf = _to_assets_rel(pdf_path_val["value"])
            obs_val = (obs.value or "").strip()
            tag = f"[{pessoa.value}]"
            if tag not in obs_val:
                obs_val = (f"{tag} " + obs_val).strip()
            return {
                "empresa_id": dd_emp.value if dd_emp.value not in ("", None) else None,
                "tipo": (tipo.value or "").strip(),
                "orgao_emissor": (orgao.value or "").strip(),
                "numero": (numero.value or "").strip(),
                "situacao": (situ.value or "").split(" ")[0],
                "dt_emissao": (emissa.value or "").strip(),
                "dt_validade": (valid.value or "").strip(),
                "link_consulta": (link.value or "").strip(),
                "arquivo": raw_pdf,
                "observacoes": obs_val,
            }
        frm._collect_payload = _collect  # type: ignore[attr-defined]
        return frm

    # ---------- Diálogos ----------
    def _install_page_open_patch():
        if getattr(page, "_dlg_patch_cert", False): return
        page._dlg_patch_cert = True
        _orig_open = page.open
        def _open_patched(dlg: ft.Control):
            try:
                if isinstance(dlg, ft.AlertDialog):
                    vw = int(getattr(page, "window_width", None) or getattr(page, "width", 1200) or 1200)
                    vh = int(getattr(page, "window_height", None) or getattr(page, "height", 800) or 800)
                    w = int(min(980, max(720, vw * 0.90)))
                    h = int(min(700, max(560, vh * 0.90)))
                    dlg.content = ft.Container(
                        width=w, height=h,
                        content=ft.Column(expand=True, spacing=12,
                                          controls=[dlg.content, ft.Container(expand=True)])
                    )
            except Exception:
                pass
            return _orig_open(dlg)
        page.open = _open_patched  # type: ignore

    def _dialog(title: str, content: ft.Control, on_save):
        _install_page_open_patch()
        btn_cancel = ft.TextButton("Cancelar", style=BTN_COMPACT)
        btn_save   = ft.FilledButton("Salvar", style=BTN_COMPACT)
        d = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
            content=content,
            actions=[btn_cancel, btn_save],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        btn_cancel.on_click = lambda e: page.close(d)
        def _on_save(e):
            try: btn_save.disabled = True; btn_save.text = "Salvando…"; page.update()
            except Exception: pass
            try: on_save(lambda: page.close(d))
            finally:
                try: btn_save.disabled = False; btn_save.text = "Salvar"; page.update()
                except Exception: pass
        btn_save.on_click = _on_save
        page.open(d)

    def _confirm(title: str, msg: str, on_ok):
        _install_page_open_patch()
        btn_cancel = ft.TextButton("Cancelar", style=BTN_COMPACT)
        btn_ok     = ft.FilledButton("Excluir", icon=ft.Icons.DELETE_OUTLINE, style=BTN_COMPACT)
        vw = int(getattr(page, "window_width", None) or getattr(page, "width", 1200) or 1200)
        w = int(min(520, max(380, vw * 0.50)))
        body = ft.Container(width=w, content=ft.Column(expand=True, spacing=12,
                            controls=[ft.Text(msg), ft.Container(expand=True)]))
        d = ft.AlertDialog(modal=True, title=ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                           content=body, actions=[btn_cancel, btn_ok],
                           actions_alignment=ft.MainAxisAlignment.END)
        btn_cancel.on_click = lambda e: page.close(d)
        btn_ok.on_click = lambda e: (on_ok(), page.close(d))
        page.open(d)

    # ---------- Exclusão de PDF físico opcional ----------
    def _delete_pdf_file(pdf_value: str) -> bool:
        try:
            if not pdf_value:
                return False
            raw = _to_assets_rel(pdf_value)
            if raw.lower().startswith(("http://", "https://")):
                return False
            rel = raw[1:] if raw.startswith("/") else raw
            target = (assets_root / rel).resolve()
            okroot = uploads_dir.resolve()
            if (okroot in target.parents) or (target.parent == okroot) or (target == okroot):
                if target.exists() and target.is_file():
                    target.unlink()
                    return True
            return False
        except Exception:
            return False

    # ---------- Ações ----------
    def new(e=None):
        frm = _form()
        def save(close):
            data = frm._collect_payload()  # type: ignore
            if not data["tipo"]:
                return _notify_err("Informe o tipo da certidão.")
            if data["link_consulta"]:
                data["link_consulta"] = _normalize_url(data["link_consulta"])
            try:
                db.add_certidao(data); close(); _notify_ok("Certidão criada."); load()
            except Exception as ex:
                close(); _notify_err(f"Erro ao salvar: {ex}")
        _dialog("➕ Nova certidão", frm, save)

    def edit(e=None):
        sel = tbl.selected_ids()
        if not sel: return _notify_err("Selecione uma linha.")
        rid = int(sel[0])
        rec = next((r for r in tbl._rows_data if r.get("id")==rid), None)
        if not rec: return _notify_err("Registro não encontrado.")
        frm = _form(rec)
        def save(close):
            data = frm._collect_payload()  # type: ignore
            if not data["tipo"]:
                return _notify_err("Informe o tipo da certidão.")
            if data["link_consulta"]:
                data["link_consulta"] = _normalize_url(data["link_consulta"])
            try:
                db.upd_certidao(rid, data); close(); _notify_ok("Certidão atualizada."); load()
            except Exception as ex:
                close(); _notify_err(f"Erro: {ex}")
        _dialog("✏️ Editar certidão", frm, save)

    def delete(e=None):
        ids = tbl.selected_ids()
        if not ids: return _notify_err("Selecione ao menos uma linha.")
        msg = f"Confirma excluir {len(ids)} registro(s)?"
        if AUTO_DELETE_PDF_ON_RECORD_DELETE:
            msg += " Os PDFs associados em uploads/certidoes/ também serão removidos do disco."
        def ok():
            okc, fail, pdfc = 0, 0, 0
            for rid in ids:
                try:
                    rid_int = int(rid)
                    raw = row_extras.get(rid_int, {}) or {}
                    pdf_value = (raw.get('pdf') or '').strip()
                    db.del_certidao(rid_int)
                    okc += 1
                    if AUTO_DELETE_PDF_ON_RECORD_DELETE and pdf_value:
                        if _delete_pdf_file(pdf_value):
                            pdfc += 1
                except Exception:
                    fail += 1
            _notify_ok(f"Excluídos: {okc} • PDFs removidos: {pdfc} • Falhas: {fail}")
            load()
        _confirm("Excluir certidões", msg, ok)

    # ---------- Resolver caminho local a partir do normalizado ----------
    def _resolve_local_pdf(norm: str) -> Path | None:
        if not norm:
            return None
        if norm.lower().startswith(("http://", "https://")):
            return None
        rel = norm[1:] if norm.startswith("/") else norm
        p = Path(rel)
        if not p.is_absolute():
            candidate = (assets_root / rel)
            if candidate.exists():
                return candidate
        p = Path(norm)
        if p.is_absolute() and p.exists():
            return p
        return None

    # ---------- Baixar PDF (substitui "Abrir PDF") ----------
    def download_pdf(e=None):
        try:
            sel = tbl.selected_ids()
            if not sel:
                return _notify_err("Selecione uma linha.")
            rid = int(sel[0])
            raw = row_extras.get(rid, {}) or {}
            pdf_field = (raw.get("pdf") or "").strip()
            if not pdf_field:
                return _notify_err("Registro sem PDF anexado.")

            norm = _to_assets_rel(pdf_field)

            # Se for URL pública → navegador (costuma baixar)
            if norm.lower().startswith(("http://", "https://")):
                _notify_ok("Abrindo no navegador para download…")
                return page.launch_url(norm)

            # Arquivo local
            local_path = _resolve_local_pdf(norm)
            if not local_path:
                return _notify_err("Não encontrei o arquivo local para baixar. Verifique se está em uploads/certidoes/.")

            suggested = local_path.name

            def on_save(res: ft.FilePickerResultEvent):
                try:
                    if not res or not getattr(res, "path", None):
                        return  # cancelado
                    destino = Path(res.path)
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_path, destino)
                    _notify_ok(f"PDF salvo em: {destino}")
                except Exception as ex:
                    _notify_err(f"Falha ao salvar: {ex}")

            save_picker.on_result = on_save
            save_picker.save_file(
                file_name=suggested,
                allowed_extensions=["pdf"],
                file_type=ft.FilePickerFileType.CUSTOM
            )
        except Exception as ex:
            return _notify_err(f"Falha ao preparar download: {ex}")

    def open_link(e=None):
        sel = tbl.selected_ids()
        if not sel: return _notify_err("Selecione uma linha.")
        rid = int(sel[0])
        raw = row_extras.get(rid, {}) or {}
        url = _normalize_url(raw.get("link") or "")
        if not url:
            return _notify_err("Registro sem link de verificação.")
        try:
            page.launch_url(url)
        except Exception as ex:
            _notify_err(f"Falha ao abrir link: {ex}")

    # ---------- Header / Divider / Quadro / Footer ----------
    # Linha 1: Filtros + Filtrar/Limpar
    filtros_row = ft.Row(
        spacing=8, wrap=True,
        controls=[
            FieldRow("Empresa", f_empresa, 260),
            FieldRow("Situação", f_situacao, 160),
            FieldRow("Tipo", f_tipo, 200),
            FieldRow("Buscar", f_busca, 240),
            ft.OutlinedButton("Filtrar", on_click=load, style=BTN_COMPACT),
            ft.OutlinedButton("Limpar", on_click=lambda e: (
                setattr(f_empresa,"value",""), setattr(f_situacao,"value","Todas"),
                setattr(f_tipo,"value",""), setattr(f_busca,"value",""), load()
            ), style=BTN_COMPACT),
        ],
    )

    # Linha 2: Botões de ação
    acoes_row = ft.Row(
        spacing=8, wrap=True,
        controls=[
            ft.FilledButton("➕ Nova", on_click=new, style=BTN_COMPACT),
            ft.OutlinedButton("✏️ Editar", on_click=edit, style=BTN_COMPACT),
            ft.OutlinedButton("🗑️ Excluir", on_click=delete, style=BTN_COMPACT),
            ft.OutlinedButton("Baixar PDF", on_click=download_pdf, style=BTN_COMPACT),
            ft.OutlinedButton("Abrir Link", on_click=open_link, style=BTN_COMPACT),
        ],
    )

    header = ft.Column(
        spacing=6,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Text("Certidões", size=18, weight=ft.FontWeight.BOLD)]
            ),
            filtros_row,
            acoes_row,
        ],
    )

    divider = ft.Divider(height=1, thickness=1, color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE))

    # ---- Área da Tabela (mantida como estava OK para você) ----
    row_inner = ft.Row(controls=[tbl.control()])
    try:
        row_inner.scroll = ft.ScrollMode.AUTO
    except Exception:
        pass
    row_container = ft.Container(content=row_inner)

    quadro = ft.ListView(
        expand=True,
        auto_scroll=False,
        controls=[row_container],
    )

    footer = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
        border_radius=10,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[lbl_count, ft.Text("Clique na caixa para selecionar.", size=12)],
        ),
    )
    layout = ft.Column(expand=True, spacing=8, controls=[header, divider, quadro, footer])

    # ---------- Resize ----------
    prev = page.on_resized
    def _on_resized(e=None):
        try:
            if prev: prev(e) if callable(prev) and e is not None else (prev() if callable(prev) else None)
        except Exception:
            pass
        vw = (getattr(page, "window_width", None) or getattr(page, "width", None) or 1200)
        vh = (getattr(page, "window_height", None) or getattr(page, "height", None) or 720)

        nh = max(360, int(vh - BASE_DESCONTO))
        tbl.set_height(nh)

        try:
            row_container.width = max(int(vw * 1.35), 1280)
        except Exception:
            pass

        page.update()
    page.on_resized = _on_resized
    _on_resized(None)

    load()
    return layout
