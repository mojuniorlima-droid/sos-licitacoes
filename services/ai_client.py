from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Tentamos usar a lib oficial da OpenAI, mas caímos fora com graça se não existir.
try:
    from openai import OpenAI  # openai>=1.0
except Exception:  # ImportError ou versões antigas
    OpenAI = None  # type: ignore


def _read_dotenv_key(name: str) -> Optional[str]:
    """
    Lê .env na raiz do projeto (opcional) e retorna a variável pedida.
    Formato suportado: NOME=valor (linhas com # são ignoradas)
    """
    root = Path(".").resolve()
    env_file = root / ".env"
    if not env_file.exists():
        return None
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _get_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY") or _read_dotenv_key("OPENAI_API_KEY")


def is_available() -> bool:
    """IA está disponível? (lib instalada + chave presente)"""
    return OpenAI is not None and _get_api_key() is not None


def summarize_edital(question: str, context_md: str) -> str:
    """
    Chama um modelo compacto para transformar EXTRATOS do edital
    em uma resposta objetiva e formatada em Markdown/PT-BR.
    Se a IA não estiver disponível, devolve string vazia.
    """
    if not is_available():
        return ""

    client = OpenAI(api_key=_get_api_key())

    system = (
        "Você é um analista de licitações no Brasil. Responda em português do Brasil, "
        "com objetividade máxima, tópicos claros, e SOMENTE com base nos EXTRATOS fornecidos. "
        "Se algo não aparecer nos trechos, diga 'não informado'. "
        "Formate a saída em Markdown, evitando parágrafos longos."
    )

    # Instruções de formatação para as perguntas mais comuns
    guidelines = (
        "Quando perguntarem sobre ABERTURA, responda com:\n"
        "- **Data:** dd/mm/aaaa\n- **Hora:** hh:mm\n- **Plataforma:** Nome (URL se houver)\n\n"
        "Quando perguntarem por DOCUMENTOS, agrupe como:\n"
        "### Habilitação jurídica\n- ...\n\n### Regularidade fiscal e trabalhista\n- ...\n\n"
        "### Qualificação técnica\n- ...\n\n### Qualificação econômico-financeira\n- ...\n\n"
        "### Declarações usuais\n- ...\n\n"
        "Quando pedirem RESUMO/INFORMAÇÕES PERTINENTES, traga seções sintéticas: "
        "**Objeto**, **Abertura**, **Documentos de habilitação (resumo)**, **Prazos/Condições**, "
        "**Valor estimado (se houver)**, **Contatos**.\n"
        "Nunca invente datas/horas/links."
    )

    user = (
        f"PERGUNTA:\n{question.strip()}\n\n"
        "EXTRATOS (use APENAS o que está abaixo):\n"
        f"{context_md.strip()}\n"
    )

    # Modelo econômico e bom para síntese com contexto
    model = "gpt-4o-mini"

    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=900,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": guidelines},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as ex:
        # Falha na IA -> devolvemos vazio para o chamador cair no modo local
        return ""
