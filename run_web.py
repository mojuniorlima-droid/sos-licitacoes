# run_web.py — execução web pura (browser) com logs claros
from __future__ import annotations
import os, sys, traceback
from pathlib import Path
import flet as ft

def main():
    root = Path(__file__).resolve().parent
    port = int(os.environ.get("PORT", "8550"))  # 8550 local; Render injeta PORT
    os.environ.setdefault("FLET_FORCE_WEB", "1")     # força navegador
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("FLET_LOG_LEVEL", "debug")

    print(f"[BOOT] Web mode -> http://localhost:{port}", flush=True)
    try:
        import main as app_main
        print("[BOOT] Import main OK", flush=True)
    except Exception:
        print("[BOOT][FATAL] Failed to import main:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    try:
        ft.app(
            target=app_main.main,              # sua função main(page)
            view=ft.AppView.WEB_BROWSER,       # abre navegador
            assets_dir=str(root),
            port=port,
            host="0.0.0.0",                    # aceita conexões externas (Render)
            web_renderer="html",
        )
    except Exception:
        print("[BOOT][FATAL] ft.app crashed:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
