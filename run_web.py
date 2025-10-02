# run_web.py — Flet em modo servidor (FLET_APP), bind no PORT do Render
from __future__ import annotations
import os, sys, traceback
from pathlib import Path
import flet as ft

def main():
    root = Path(__file__).resolve().parent

    # Render injeta PORT; localmente você pode definir PORT, senão cai para 0 (porta livre)
    port = int(os.environ.get("PORT", "0"))

    # Logs sem buffer
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    # Deixe sem FLET_FORCE_WEB em produção
    os.environ.pop("FLET_FORCE_WEB", None)

    print(f"[BOOT] FLET_APP listening on 0.0.0.0:{port}", flush=True)
    try:
        import main as app_main
        print("[BOOT] Import main OK", flush=True)
    except Exception:
        print("[BOOT][FATAL] Failed to import main:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    try:
        ft.app(
            target=app_main.main,           # sua função main(page)
            view=ft.AppView.FLET_APP,       # <<< servidor Flet (modo web)
            assets_dir=str(root),
            host="0.0.0.0",                 # necessário no Render
            port=port,                      # Render dá o PORT
            web_renderer="html",            # pode trocar para "canvaskit" se quiser
        )
    except Exception:
        print("[BOOT][FATAL] ft.app crashed:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
