# run_native.py — launcher definitivo (carrega main.py por TABS)
from __future__ import annotations
import flet as ft

# IMPORTA o main correto (tabs) — NÃO o do teste de fumaça
from main import main as app_main

if __name__ == "__main__":
    # Observação:
    # - AppView.FLET_APP abre janela nativa (desktop)
    # - Se preferir abrir no navegador, troque por AppView.WEB_BROWSER
    ft.app(
        target=app_main,
        view=ft.AppView.FLET_APP,
        assets_dir=".",
        web_renderer="html",  # estável no desktop; troque p/ "canvaskit" se precisar
    )
