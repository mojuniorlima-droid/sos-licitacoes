# === components/pickers.py ===
import flet as ft

def DateField(value: str = "", placeholder: str = "AAAA-MM-DD", label: str | None = None, width: int = 200) -> ft.TextField:
    """
    Campo de data simplificado no formato AAAA-MM-DD.
    - Aceita só números e hífen
    - Se digitar 8 dígitos (AAAAMMDD), auto-formata
    """
    def _only_ymd(s: str) -> str:
        return "".join(ch for ch in (s or "") if ch.isdigit() or ch == "-")

    def _auto_format_ymd(s: str) -> str:
        s = "".join(ch for ch in (s or "") if ch.isdigit())
        if len(s) == 8:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
        return s

    tf = ft.TextField(
        value=value or "",
        hint_text=placeholder,
        label=label,
        width=width,
        input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9\-]*", replacement_string=""),
    )

    def _on_change(e: ft.ControlEvent):
        v = _only_ymd(tf.value)
        if len(v) == 8 and "-" not in v:
            tf.value = _auto_format_ymd(v)
        else:
            tf.value = v[:10]
        tf.update()

    tf.on_change = _on_change
    return tf
