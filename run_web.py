# run_web.py — smoke test/override controlado por APP_HELLO
from __future__ import annotations
import os, sys, traceback
from pathlib import Path
import flet as ft

def hello_target(page: ft.Page):
    page.title = "Smoke Test"
    page.add(ft.Container(padding=20, content=ft.Text("HELLO FROM RENDER ✅", size=22, weight=ft.FontWeight.W_700)))
    page.update()

def main():
    root = Path(__file__).resolve().parent
    port = int(os.environ.get("PORT", "10000"))
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    use_hello = os.environ.get("APP_HELLO") == "1"  # <<< liga override
    print(f"[BOOT] FLET_APP on 0.0.0.0:{port} | APP_HELLO={use_hello}", flush=True)

    try:
        if use_hello:
            target = hello_target
            print("[BOOT] Using hello_target()", flush=True)
        else:
            import main as app_main
            print("[BOOT] Import main OK", flush=True)
            target = app_main.main
    except Exception:
        print("[BOOT][FATAL] Failed to import main:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    try:
        ft.app(
            target=target,
            view=ft.AppView.FLET_APP,   # servidor web do Flet
            assets_dir=str(root),
            host="0.0.0.0",
            port=port,
            web_renderer="html",
        )
    except Exception:
        print("[BOOT][FATAL] ft.app crashed:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
