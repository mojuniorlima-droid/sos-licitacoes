# run_web.py — Flet server (FLET_APP), com detecção de ambiente e logs claros
from __future__ import annotations
import os, sys, traceback
from pathlib import Path
import flet as ft

import os, flet as ft

def main(page: ft.Page):
    # ===== DIAGNÓSTICO MÍNIMO (temporário) =====
    if os.environ.get("APP_MINIMAL") == "1":
        print("[APP] main() entrou (modo mínimo)", flush=True)
        page.title = "SOS Licitações — Modo Mínimo"
        page.add(ft.Container(padding=20, content=ft.Text("Minimal OK", size=20, weight=ft.FontWeight.W_700)))
        page.update()
        return
    print("[APP] main() entrou (modo completo)", flush=True)
    # ===== FIM DO BLOCO DE DIAGNÓSTICO =====


def main():
    root = Path(__file__).resolve().parent

    # Detecta Render: em produção, Render injeta PORT e (geralmente) RENDER
    on_render = os.environ.get("RENDER", "").lower() in ("1", "true", "yes")

    # Porta:
    # - Produção (Render): usa $PORT obrigatoriamente
    # - Local: usa 8550 para você saber a URL (nada de 0)
    port = int(os.environ.get("PORT", "8550" if not on_render else "0"))

    # Logs sem buffer
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    # Força navegador SOMENTE local (no Render deixe sem)
    if not on_render:
        os.environ.setdefault("FLET_FORCE_WEB", "1")

    print(f"[BOOT] FLET_APP on 0.0.0.0:{port} | env.RENDER={on_render}", flush=True)
    try:
        import main as app_main
        print("[BOOT] Import main OK", flush=True)
    except Exception:
        print("[BOOT][FATAL] Failed to import main:", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    try:
        ft.app(
            target=app_main.main,        # sua função main(page)
            view=ft.AppView.FLET_APP,    # modo servidor (web)
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
