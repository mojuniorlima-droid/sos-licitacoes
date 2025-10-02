# components/inputs.py
from __future__ import annotations
import re
import flet as ft

def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def cnpj_input(label: str = "CNPJ", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(label=label, value=value or "", width=width, keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    def _mask(e=None):
        d = _digits_only(tf.value)[:14]
        out = d
        if len(d) >= 3:
            out = f"{d[:2]}.{d[2:5]}"
            if len(d) >= 6:
                out = f"{out}.{d[5:8]}"
                if len(d) >= 9:
                    out = f"{out}/{d[8:12]}"
                    if len(d) >= 13:
                        out = f"{out}-{d[12:14]}"
        tf.value = out
        try: tf.update()
        except Exception: pass
    tf.on_change = _mask
    _mask(None)
    return tf

def cpf_input(label: str = "CPF", value: str = "", width: int | None = None) -> ft.TextField:
    tf = ft.TextField(label=label, value=value or "", width=width, keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    def _mask(e=None):
        d = _digits_only(tf.value)[:11]
        out = d
        if len(d) >= 4:
            out = f"{d[:3]}.{d[3:6]}"
            if len(d) >= 7:
                out = f"{out}.{d[6:9]}"
                if len(d) >= 10:
                    out = f"{out}-{d[9:11]}"
        tf.value = out
        try: tf.update()
        except Exception: pass
    tf.on_change = _mask
    _mask(None)
    return tf
