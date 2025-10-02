from __future__ import annotations
import os
import flet as ft
from pathlib import Path
import main as app_main  # usa a função main(page) do seu main.py

def _run():
    ROOT = Path(__file__).resolve().parent
    port = int(os.environ.get("PORT", "8000"))
    ft.app(
        target=app_main.main,
        view=ft.AppView.FLET_APP,     # renderizador Flet web
        assets_dir=str(ROOT),         # garante assets na raiz do projeto
        port=port,
        web_renderer="html",
    )

if __name__ == "__main__":
    _run()
