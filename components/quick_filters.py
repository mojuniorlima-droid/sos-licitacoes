# === components/quick_filters.py ===
import flet as ft

def quick_filter_bar(
    on_search=None,        # callback(str)
    on_filter1=None,       # callback(value)
    on_filter2=None,       # callback(value)
    hint="Buscar...",
    filter1_label=None, filter1_options: list[str] | None = None,
    filter2_label=None, filter2_options: list[str] | None = None,
) -> ft.Row:
    search = ft.TextField(
        hint_text=hint, width=280, dense=True, on_submit=lambda e: on_search and on_search(e.control.value)
    )
    def _fdd(label, opts, on_change):
        if not label or not opts:
            return None
        return ft.Dropdown(
            label=label, dense=True, options=[ft.dropdown.Option(x) for x in opts],
            on_change=lambda e: on_change and on_change(e.control.value), width=180
        )
    f1 = _fdd(filter1_label, filter1_options, on_filter1)
    f2 = _fdd(filter2_label, filter2_options, on_filter2)
    controls = [search]
    if f1: controls.append(f1)
    if f2: controls.append(f2)
    controls.append(ft.OutlinedButton("Limpar", icon=ft.Icons.CLEAR, on_click=lambda e: (
        setattr(search,"value",""), on_search and on_search("")
    )))
    return ft.Row(spacing=8, controls=controls)
