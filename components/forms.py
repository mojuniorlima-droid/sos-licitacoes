# components/forms.py  (padrão "Novo 5 atual")
from __future__ import annotations
import re
import flet as ft

# ----------------- util -----------------
def digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def _safe_update(ctrl: ft.Control) -> None:
    try:
        ctrl.update()
    except AssertionError:
        pass
    except Exception:
        pass

# ----------------- componentes visuais -----------------
def FieldRow(label: str, control: ft.Control, width: int | None = None) -> ft.Container:
    return ft.Container(
        width=width,
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                control,
            ],
        ),
    )

def snack_ok(page: ft.Page, msg: str) -> None:
    page.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=ft.Colors.GREEN_600)
    page.snack_bar.open = True
    page.update()

def snack_err(page: ft.Page, msg: str) -> None:
    page.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=ft.Colors.ERROR)
    page.snack_bar.open = True
    page.update()

# ----------------- inputs genéricos -----------------
def text_input(value: str = "", label: str = "", width: int | None = None, **kw) -> ft.TextField:
    return ft.TextField(label=label, value=value or "", width=width, dense=True, **kw)

def email_input(label: str = "E-mail", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(label=label, value=value or "", width=width, keyboard_type=ft.KeyboardType.EMAIL, dense=True)
    def _on_blur(e=None):
        v = (tf.value or "").strip()
        tf.error_text = None if (not v or "@" in v) else "E-mail inválido"
        _safe_update(tf)
    tf.on_blur = _on_blur
    return tf

def phone_input(label: str = "Telefone", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(label=label, value=value or "", width=width, keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    def _mask(e=None):
        d = digits_only(tf.value)[:11]
        out = d
        if len(d) >= 1:
            out = f"({d[:2]}"
            if len(d) >= 3:
                if len(d) >= 11:
                    out += f") {d[2:7]}"
                    if len(d) >= 8:
                        out += f"-{d[7:11]}"
                else:
                    out += f") {d[2:6]}"
                    if len(d) >= 7:
                        out += f"-{d[6:10]}"
        tf.value = out
        _safe_update(tf)
    tf.on_change = _mask
    _mask(None)
    return tf

def cep_input(label: str = "CEP", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(label=label, value=value or "", width=width, keyboard_type=ft.KeyboardType.NUMBER, max_length=9, dense=True)
    def _mask(e=None):
        d = digits_only(tf.value)[:8]
        tf.value = f"{d[:5]}-{d[5:]}" if len(d) > 5 else d
        _safe_update(tf)
    tf.on_change = _mask
    _mask(None)
    return tf

def uf_input(label: str = "UF", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(
        label=label, value=(value or "").upper(), width=width, max_length=2,
        capitalization=ft.TextCapitalization.CHARACTERS, dense=True
    )
    def _mask(e=None):
        tf.value = (tf.value or "").upper()[:2]
        _safe_update(tf)
    tf.on_change = _mask
    _mask(None)
    return tf

def date_input(label: str = "Data (dd/mm/aaaa)", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(label=label, value=value or "", width=width, keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    def _mask(e=None):
        d = digits_only(tf.value)[:8]
        if len(d) >= 5:
            tf.value = f"{d[:2]}/{d[2:4]}/{d[4:]}"
        elif len(d) >= 3:
            tf.value = f"{d[:2]}/{d[2:]}"
        else:
            tf.value = d
        _safe_update(tf)
    tf.on_change = _mask
    _mask(None)
    return tf

def money_input(label: str, value: str = "", width: int = 200) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        width=width,
        prefix_text="R$ ",
        keyboard_type=ft.KeyboardType.NUMBER,
        dense=True,
    )
