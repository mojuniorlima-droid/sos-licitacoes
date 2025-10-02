# pages/edital_chat.py — mesmo layout/comportamento, agora com FilePicker no Web
from __future__ import annotations
import os, tempfile, shutil, threading
import flet as ft

# --------- serviço (tolerante) ---------
def _svc_resolver():
    try:
        from services import edital_ia as svc
    except Exception:
        class _SvcStub:
            def list_indexed_docs(self): return []
            def list_docs(self): return []
            def list(self): return []
            def index_pdf(self, *a, **k): return False
            def ingest_pdf(self, *a, **k): return False
            def clear_index(self): return False
            def clear(self): return False
            def ask(self, *a, **k): return "IA indisponível no ambiente web."
            def query(self, *a, **k): return "IA indisponível no ambiente web."
            def last_sources(self): return []
            def get_sources(self): return []
        svc = _SvcStub()
    def pick(*names):
        for n in names:
            if hasattr(svc, n):
                return getattr(svc, n)
        return None
    return {
        "list":  pick("list_indexed_docs", "list_docs", "list"),
        "index": pick("index_pdf", "ingest_pdf"),
        "clear": pick("clear_index", "clear"),
        "ask":   pick("ask", "query"),
        "srcs":  pick("last_sources", "get_sources"),
    }

# --------- util UI ---------
def _snack(page: ft.Page, msg: str, ok=True):
    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="#2E7D32" if ok else "#B00020")
    page.snack_bar.open = True
    page.update()

# --------- seleção de arquivo: web (FilePicker) + desktop (tkinter) ---------
def _pick_pdf_desktop() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        fn = filedialog.askopenfilename(
            title="Selecione um PDF",
            filetypes=[("PDF", "*.pdf")],
        )
        root.destroy()
        return fn or None
    except Exception:
        return None

def _mk_web_picker(page: ft.Page, on_selected):
    picker = ft.FilePicker(on_result=lambda e: on_selected(e.files[0].path) if e.files else None)
    page.overlay.append(picker)
    page.update()
    def open_dialog(_=None):
        picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"])
    return open_dialog

# --------- página ---------
def page(page: ft.Page) -> ft.Control:
    sv = _svc_resolver()

    # estado
    docs_list = ft.ListView(expand=True, spacing=6)
    resp_md = ft.Markdown("", extension_set=ft.MarkdownExtensionSet.GITHUB_WEB, selectable=True)
    fontes_list = ft.ListView(spacing=4, expand=False, height=0, visible=False)

    fontes_header = ft.Row(
        controls=[
            ft.Text("Fontes", size=12, weight=ft.FontWeight.BOLD),
            ft.TextButton("Mostrar", on_click=lambda e: toggle_srcs(True)),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def toggle_srcs(show: bool):
        fontes_list.visible = show
        fontes_list.height = 160 if show else 0
        fontes_header.controls[1].text = "Esconder" if show else "Mostrar"
        fontes_header.controls[1].on_click = (lambda e: toggle_srcs(False)) if show else (lambda e: toggle_srcs(True))
        page.update()

    # lista de documentos indexados
    def refresh_docs():
        docs_list.controls.clear()
        try:
            items = sv["list"]() or []
        except Exception as ex:
            items = []
            _snack(page, f"Falha ao listar documentos: {ex}", ok=False)
        for it in items:
            docs_list.controls.append(ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.PICTURE_AS_PDF, size=18),
                ft.Text(str(it))
            ]))
        page.update()

    # seleção de PDF
    selected_pdf_path: dict[str, str | None] = {"path": None}

    def _after_pick(path: str | None):
        selected_pdf_path["path"] = path
        lbl_pdf.value = os.path.basename(path) if path else "Nenhum arquivo selecionado"
        page.update()

    # detectar ambiente web vs desktop
    is_web = page.client_platform in ("web", "android", "ios") or page.web

    if is_web:
        open_picker = _mk_web_picker(page, on_selected=_after_pick)
    else:
        def open_picker(_=None):
            _after_pick(_pick_pdf_desktop())

    lbl_pdf = ft.Text("Nenhum arquivo selecionado", size=12)

    # indexação
    def do_index(e=None):
        if not selected_pdf_path["path"]:
            _snack(page, "Selecione um PDF primeiro.", ok=False)
            return
        path = selected_pdf_path["path"]
        _snack(page, "Indexando PDF…")
        def run():
            ok = False
            tmp = None
            try:
                # no web (sandbox) pode ser necessário copiar para /tmp
                if not os.access(path, os.R_OK):
                    fd, tmp = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
                    shutil.copy(path, tmp)
                    use = tmp
                else:
                    use = path
                ok = bool(sv["index"](use))
            except Exception as ex:
                _snack(page, f"Falha ao indexar: {ex}", ok=False)
            finally:
                if tmp and os.path.exists(tmp):
                    os.remove(tmp)
                if ok:
                    _snack(page, "PDF indexado com sucesso!")
                    refresh_docs()
        threading.Thread(target=run, daemon=True).start()

    # pergunta ao modelo
    inp = ft.TextField(label="Pergunte sobre o edital", multiline=True, min_lines=3)
    def do_ask(e=None):
        q = (inp.value or "").strip()
        if not q:
            _snack(page, "Digite uma pergunta.", ok=False); return
        resp_md.value = "⏳ consultando…"
        fontes_list.controls.clear(); toggle_srcs(False)
        page.update()
        def run():
            try:
                ans = sv["ask"](q) or "Sem resposta."
                resp_md.value = str(ans)
                # fontes (se houver)
                try:
                    srcs = sv["srcs"]() or []
                except Exception:
                    srcs = []
                fontes_list.controls = [ft.Text(f"- {s}") for s in srcs]
                toggle_srcs(bool(srcs))
            except Exception as ex:
                resp_md.value = f"**Erro:** {ex}"
            finally:
                page.update()
        threading.Thread(target=run, daemon=True).start()

    # layout (mantém sua estética)
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Chat sobre o Edital", size=16, weight=ft.FontWeight.BOLD),
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton("Selecionar PDF", icon=ft.Icons.UPLOAD_FILE, on_click=open_picker),
                lbl_pdf,
                ft.OutlinedButton("Indexar", icon=ft.Icons.TASK, on_click=do_index),
            ])
        ],
    )

    body = ft.Row(
        expand=True,
        spacing=10,
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Pergunta", size=13, weight=ft.FontWeight.W_600),
                    inp,
                    ft.Row(spacing=8, controls=[ft.FilledButton("Perguntar", icon=ft.Icons.SEND, on_click=do_ask)]),
                    ft.Divider(),
                    ft.Text("Resposta", size=13, weight=ft.FontWeight.W_600),
                    resp_md,
                    ft.Divider(),
                    fontes_header,
                    fontes_list,
                ])
            ),
            ft.Container(width=280, content=ft.Column(spacing=8, controls=[
                ft.Text("Documentos Indexados", size=13, weight=ft.FontWeight.W_600),
                ft.Container(height=380, content=docs_list),
                ft.FilledTonalButton("Atualizar lista", icon=ft.Icons.REFRESH, on_click=lambda e: refresh_docs()),
            ]))
        ]
    )

    root = ft.Column(expand=True, spacing=10, controls=[header, body])
    # popular lista ao abrir
    page.call_later(refresh_docs, 0.01)
    return root

# aliases aceitos pelo main.py
build = page
view = page
app = page
page_edital_chat = page
edital_chat_page = page
