import flet as ft

# IMPORTA a função main da SUA aplicação, sem modificar nada
from main import main  # seu main.py precisa ter def main(page): ...

if __name__ == "__main__":
    # Usa renderer HTML (costuma evitar bug de clique no Web)
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, assets_dir=".", web_renderer="html")
