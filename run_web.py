import os
import flet as ft
from main import main

if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        assets_dir=".",  # garante que assets/ está acessível
    )
