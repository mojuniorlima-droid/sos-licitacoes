# run_web.py
from __future__ import annotations
import os, sys, traceback
from pathlib import Path
import flet as ft

def _boot():
    port = int(os.environ.get("PORT", "8000"))
    root = Path(__file__).resolve().parent
    os.environ.setdefault("PYTHONUNBUFFERED", "1")  # logs sem buffer

    print(f"[BOOT] Starting Flet app on port {port} | CWD={os.getcwd()}", flush=True)
    try:
        import main as app_main
    except Exception as ex:
        print("[BOOT][FATAL] Failed to import main:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    try:
        ft.app(
            target=app_main.main,            # usa sua função main(page)
            view=ft.AppView.WEB_BROWSER,     # forçar renderer web puro
            assets_dir=str(root),
            port=port,
            web_renderer="html",
        )
    except Exception as ex:
        print("[BOOT][FATAL] ft.app crashed:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    _boot()
