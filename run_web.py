# run_web.py — boot com diagnóstico (modo FLET_APP)
from __future__ import annotations
import os, sys, traceback, threading, time
from pathlib import Path
import flet as ft

BOOT_MARKS = []

def log(msg: str):
    BOOT_MARKS.append(msg)
    print(f"[BOOT] {msg}", flush=True)

def _diagnose_target(app_main):
    def target(page: ft.Page):
        try:
            page.title = "Diagnóstico de Inicialização"
            page.scroll = ft.ScrollMode.AUTO
            status = ft.Text("Iniciando aplicação...", size=14, weight=ft.FontWeight.W_600)
            details = ft.Column(spacing=4)
            page.add(
                ft.Container(
                    padding=20,
                    content=ft.Column(spacing=10, controls=[
                        ft.Text("Diagnóstico de inicialização (provisório)", size=16, weight=ft.FontWeight.W_700),
                        status,
                        ft.Divider(),
                        ft.Text("Marcos de boot:", size=12),
                        details,
                        ft.Divider(),
                        ft.Text("Se esta tela não sumir em 2–3s, há travamento no boot do app.", size=11, color="#9E9E9E"),
                    ])
                )
            )
            page.update()

            def _feed_marks():
                last_len = 0
                while True:
                    time.sleep(0.3)
                    if len(BOOT_MARKS) != last_len:
                        details.controls = [ft.Text(m, size=12) for m in BOOT_MARKS]
                        last_len = len(BOOT_MARKS)
                        try: page.update()
                        except Exception: break

            threading.Thread(target=_feed_marks, daemon=True).start()

            log("Chamando main(page)...")
            app_main.main(page)
            log("main(page) retornou.")
        except Exception:
            err = traceback.format_exc()
            log("EXCEÇÃO no main(page)")
            details.controls.append(ft.Text(err, size=12, color="#B00020"))
            try: page.update()
            except Exception: pass
            raise
    return target

def _boot():
    # Porta 0 = o sistema escolhe uma porta livre (evita 10048)
    port = int(os.environ.get("PORT", "0"))
    root = Path(__file__).resolve().parent
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("FLET_LOG_LEVEL", "debug")

    log(f"Starting Flet app on port {port} | CWD={os.getcwd()} | assets={root}")

    try:
        import main as app_main
        log("Import main OK")
    except Exception:
        print("[BOOT][FATAL] Failed to import main:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    try:
        ft.app(
            target=_diagnose_target(app_main),
            view=ft.AppView.FLET_APP,     # <<< chave aqui
            assets_dir=str(root),
            port=port,                    # 0 escolhe livre localmente; no Render virá $PORT
            web_renderer="html",
        )
    except Exception:
        print("[BOOT][FATAL] ft.app crashed:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    _boot()
