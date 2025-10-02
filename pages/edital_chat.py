# pages/edital_chat.py
from __future__ import annotations
import os, threading, shutil, tempfile
import flet as ft

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

def page_edital_chat(page: ft.Page) -> ft.Control:
    sv = _svc_resolver()

    # -------- estado UI (iguais) --------
    docs_list = ft.ListView(spacing=6, expand=True)

    # resposta agora é 1 Markdown dentro do mesmo cartão (sem mudar layout)
    md_resp = ft.Markdown(
        "",
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        selectable=True,
    )

    # rodapé de fontes fixo no fim do cartão (colapsável por padrão)
    fontes_list = ft.ListView(spacing=4, expand=False, height=0, visible=False)
    fontes_header = ft.Row(
        controls=[
            ft.Text("Fontes", size=12, weight=ft.FontWeight.BOLD),
            ft.TextButton("Mostrar", on_click=lambda e: toggle_srcs(True)),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def toggle_srcs(show: bool):
        if show:
            fontes_list.visible = True
            fontes_list.height = 120
            # troca o botão para "Esconder"
            fontes_header.controls[1] = ft.TextButton("Esconder", on_click=lambda e: toggle_srcs(False))
        else:
            fontes_list.visible = False
            fontes_list.height = 0
            fontes_header.controls[1] = ft.TextButton("Mostrar", on_click=lambda e: toggle_srcs(True))
        fontes_header.update()
        fontes_list.update()

    spinner_overlay = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        visible=False,
        content=ft.ProgressRing(),
    )

    def set_loading(v: bool):
        spinner_overlay.visible = v
        btn_ask.disabled = v
        btn_index.disabled = v
        page.update()

    def _auto_hide(control: ft.Control, secs: float = 3.0):
        def _hide():
            try:
                if control in docs_list.controls:
                    docs_list.controls.remove(control)
                    page.update()
            except Exception:
                pass
        threading.Timer(secs, _hide).start()

    def render_docs():
        docs_list.controls.clear()
        try:
            items = sv["list"]() if sv["list"] else []
            for d in (items or []):
                name = d.get("name") if isinstance(d, dict) else str(d)
                info = ""
                if isinstance(d, dict) and d.get("chunks"):
                    info = f" · {d['chunks']} trecho(s)"
                docs_list.controls.append(
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.DESCRIPTION, size=16),
                            ft.Text(f"{name}{info}", size=12, no_wrap=True, expand=True),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    )
                )
        except Exception as ex:
            docs_list.controls.append(ft.Text(f"Falha ao listar: {ex}", color=ft.Colors.ERROR))
        page.update()

    # -------- seletor nativo + cópia p/ cache (OneDrive safe) --------
    def _pick_file_native() -> str | None:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception:
            return None
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title="Selecione um PDF",
                filetypes=[("PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
            )
            root.destroy()
            return path if path else None
        except Exception:
            return None

    def _cache_copy(src_path: str) -> str:
        base = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), "novo5", "edital_cache")
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            import tempfile as _tmp
            base = os.path.join(_tmp.gettempdir(), "novo5_edital_cache")
            os.makedirs(base, exist_ok=True)
        dst = os.path.join(base, os.path.basename(src_path))
        try:
            shutil.copy2(src_path, dst)
        except Exception:
            shutil.copy(src_path, dst)
        return dst

    def do_index():
        opening = ft.Container(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=6,
            padding=6,
            content=ft.Text("Abrindo seletor de arquivos…", size=12),
        )
        docs_list.controls.insert(0, opening)
        docs_list.update()

        path = _pick_file_native()
        if not path:
            opening.content = ft.Text("Seleção cancelada.", size=12)
            docs_list.update()
            _auto_hide(opening, 2.0)
            return

        name = os.path.basename(path)
        opening.content = ft.Row(
            spacing=8,
            controls=[ft.ProgressRing(width=16, height=16), ft.Text(f"Copiando para cache: {name}", size=12)],
        )
        docs_list.update()

        try:
            cached = _cache_copy(path)
        except Exception as ex:
            opening.bgcolor = ft.Colors.ERROR_CONTAINER
            opening.content = ft.Text(f"Erro ao copiar: {ex}", size=12, color=ft.Colors.ON_ERROR_CONTAINER)
            docs_list.update()
            _auto_hide(opening, 4.0)
            return

        opening.content = ft.Row(
            spacing=8,
            controls=[ft.ProgressRing(width=16, height=16), ft.Text(f"Indexando: {name}", size=12)],
        )
        docs_list.update()

        docs_list.controls.insert(
            1,
            ft.Row(
                controls=[ft.Icon(ft.Icons.DESCRIPTION, size=16),
                          ft.Text(name, size=12, no_wrap=True, expand=True)],
                alignment=ft.MainAxisAlignment.START,
            ),
        )
        docs_list.update()

        set_loading(True)

        def _worker():
            ok, ex = True, None
            try:
                if sv["index"]:
                    sv["index"](cached)
                else:
                    raise RuntimeError("Serviço de indexação indisponível.")
            except Exception as _ex:
                ok, ex = False, _ex

            if ok:
                opening.content = ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.PRIMARY),
                        ft.Text(f"Indexado com sucesso: {name}", size=12, color=ft.Colors.PRIMARY),
                    ],
                )
                docs_list.update()
                _auto_hide(opening)
                render_docs()
            else:
                opening.bgcolor = ft.Colors.ERROR_CONTAINER
                opening.content = ft.Text(f"Erro ao indexar: {ex}", size=12, color=ft.Colors.ON_ERROR_CONTAINER)
                docs_list.update()
                _auto_hide(opening, 5.0)

            set_loading(False)

        page.run_thread(_worker)

    def do_clear():
        set_loading(True)
        try:
            if sv["clear"]:
                sv["clear"]()
            render_docs()
            md_resp.value = ""
            fontes_list.controls.clear()
            toggle_srcs(False)
            page.update()
        except Exception as ex:
            md_resp.value = f"**Erro ao limpar índice:** {ex}"
            fontes_list.controls.clear()
            toggle_srcs(False)
            page.update()
        finally:
            set_loading(False)

    # -------- Perguntar (sem mudar teu fluxo) --------
    def ask(_=None):
        q = inp_question.value.strip()
        if not q:
            return

        # limpa área de resposta e fontes (mantendo o layout)
        md_resp.value = ""
        fontes_list.controls.clear()
        toggle_srcs(False)
        page.update()

        use_ai = sw_ai.value
        set_loading(True)

        def _worker():
            try:
                ans = sv["ask"](q, use_ai=use_ai) if sv["ask"] else {"markdown": "Serviço indisponível."}

                # pega markdown “bonito” da resposta
                md_text = ""
                if isinstance(ans, dict):
                    for k in ("markdown", "answer_md", "text", "content", "message", "answer"):
                        v = ans.get(k)
                        if isinstance(v, str) and v.strip():
                            md_text = v.strip()
                            break
                elif isinstance(ans, str):
                    md_text = ans

                if not md_text:
                    md_text = "_Sem conteúdo útil encontrado. Verifique se há documentos indexados._"

                md_resp.value = md_text

                # fontes presas no rodapé (colapsadas por padrão)
                srcs = []
                if isinstance(ans, dict):
                    srcs = ans.get("sources") or []
                if not srcs and sv["srcs"]:
                    try:
                        srcs = sv["srcs"]() or []
                    except Exception:
                        srcs = []

                fontes_list.controls.clear()
                for s in srcs[:30]:
                    fontes_list.controls.append(ft.Text(f"• {s}", size=12, selectable=True))

            except Exception as ex:
                md_resp.value = f"**Erro ao consultar:** {ex}"
                fontes_list.controls.clear()
                toggle_srcs(False)
            finally:
                page.update()
                set_loading(False)

        page.run_thread(_worker)

    # -------- UI (layout preservado) --------
    title = ft.Text("Chat do Edital", size=16, weight=ft.FontWeight.BOLD)

    inp_question = ft.TextField(
        hint_text="Me entregue informações pertinentes sobre esse processo",
        expand=True,
        on_submit=ask,
    )
    sw_ai = ft.Switch(label="Chat GPT-4.1", value=True)
    btn_index = ft.FilledButton("Indexar PDF", icon=ft.Icons.UPLOAD_FILE, on_click=lambda e: do_index())
    btn_clear = ft.OutlinedButton("Limpar índice", icon=ft.Icons.DELETE_SWEEP, on_click=lambda e: do_clear())
    btn_ask = ft.FilledButton("Perguntar", icon=ft.Icons.QUESTION_MARK, on_click=ask)

    header = ft.Row(
        controls=[inp_question, sw_ai, btn_index, btn_clear, btn_ask],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    left_panel = ft.Container(
        width=300,
        padding=10,
        content=ft.Column(
            expand=True,
            spacing=8,
            controls=[
                ft.Text("Documentos Indexados", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=10,
                    padding=8,
                    content=docs_list,
                    expand=True,
                ),
            ],
        ),
    )

    # cartão de resposta (sem mudar a estrutura)
    resp_card = ft.Container(
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=10,
        padding=12,
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=8,
            controls=[
                # área principal com scroll automático (o Markdown fica aqui)
                ft.Container(expand=True, content=ft.ListView(spacing=8, expand=True, controls=[md_resp])),
                ft.Divider(height=1),
                # rodapé com fontes (colado embaixo)
                ft.Column(spacing=6, controls=[fontes_header, fontes_list]),
            ],
        ),
    )

    right_panel = ft.Container(
        expand=True,
        padding=10,
        content=ft.Column(
            expand=True,
            spacing=8,
            controls=[
                ft.Text("Resposta", size=14, weight=ft.FontWeight.BOLD),
                ft.Stack(controls=[resp_card, spinner_overlay], expand=True),
            ],
        ),
    )

    body_row = ft.Row(
        expand=True,
        spacing=12,
        controls=[left_panel, right_panel],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    root = ft.Column(spacing=12, expand=True, controls=[title, header, body_row])

    render_docs()
    return root
