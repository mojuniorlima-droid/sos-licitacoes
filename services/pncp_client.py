# services/pncp_client.py
# Cliente PNCP (consulta pública) – Python 3.11+ / sem dependências obrigatórias
from __future__ import annotations

import json
import time
import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    import urllib.request
    import urllib.parse
    _HAS_REQUESTS = False


class PNCPError(Exception):
    pass


def _iso_date(d: dt.date | dt.datetime | str | None) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, (dt.date, dt.datetime)):
        return d.strftime("%Y-%m-%d")
    s = str(d).strip()
    if not s:
        return None
    if "/" in s and len(s) >= 10:
        try:
            return dt.datetime.strptime(s[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            pass
    return s


class PNCPClient:
    """
    Cliente para API de consulta pública do PNCP.

    Base típica:
        https://pncp.gov.br/api/consulta/v1

    Endpoints variam por release:
      - /licitacoes
      - /compras
    O cliente tenta /licitacoes e cai para /compras se necessário.
    """

    def __init__(self, base_url: str = "https://pncp.gov.br/api/consulta/v1", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -------- HTTP --------
    def _get(self, path: str, params: Dict[str, Any]) -> Tuple[int, Dict[str, Any] | List[Any] | str]:
        url = f"{self.base_url}{path}"
        if _HAS_REQUESTS:
            try:
                r = requests.get(url, params=params, timeout=self.timeout)
                ct = r.headers.get("content-type", "")
                if "application/json" in (ct or "").lower():
                    return r.status_code, r.json()
                return r.status_code, r.text
            except Exception as ex:
                raise PNCPError(f"Falha HTTP (requests): {ex}") from ex
        else:
            try:
                qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
                with urllib.request.urlopen(f"{url}?{qs}", timeout=self.timeout) as resp:
                    raw = resp.read()
                    ctype = resp.headers.get("content-type", "")
                    if "application/json" in (ctype or "").lower():
                        return resp.status, json.loads(raw.decode("utf-8", errors="ignore"))
                    return resp.status, raw.decode("utf-8", errors="ignore")
            except Exception as ex:
                raise PNCPError(f"Falha HTTP (urllib): {ex}") from ex

    # -------- Consulta principal --------
    def fetch_licitacoes(
        self,
        termo: Optional[str] = None,           # objeto / palavra‑chave
        uf: Optional[str] = None,              # sigla UF
        municipio: Optional[str] = None,       # município comprador
        orgao_nome: Optional[str] = None,      # órgão comprador (texto livre)
        orgao_uasg: Optional[str] = None,      # UASG, se quiser
        modalidade: Optional[str] = None,      # Pregão, Concorrência, etc.
        data_ini: Optional[str | dt.date | dt.datetime] = None,  # publicação de
        data_fim: Optional[str | dt.date | dt.datetime] = None,  # publicação até
        pagina: int = 0,
        tamanho: int = 50,
        limite_paginas: int = 6,
        pausa_s: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """
        Retorna lista de licitações normalizada com filtros chave.
        """
        data_ini = _iso_date(data_ini)
        data_fim = _iso_date(data_fim)

        # Alguns backends aceitam chaves diferentes; mandamos opções redundantes.
        def _mount_params(p: int) -> Dict[str, Any]:
            params = {
                "page": p,
                "size": tamanho,
                "offset": p * tamanho,
                "limit": tamanho,

                # Texto/objeto
                "termo": termo,
                "palavraChave": termo,
                "objeto": termo,

                # UF / Município
                "uf": (uf or None),
                "siglaUf": (uf or None),
                "municipio": (municipio or None),
                "cidade": (municipio or None),

                # Órgão / UASG
                "uasg": orgao_uasg or None,
                "orgaoUasg": orgao_uasg or None,
                "orgao": orgao_nome or None,
                "orgaoNome": orgao_nome or None,
                "unidadeGestoraNome": orgao_nome or None,

                # Modalidade
                "modalidade": modalidade or None,
                "modalidadeLicitacao": modalidade or None,

                # Datas (publicação/abertura)
                "dataInicial": data_ini,
                "dataFinal": data_fim,
                "dataPublicacaoInicial": data_ini,
                "dataPublicacaoFinal": data_fim,
                "dataAberturaInicial": data_ini,
                "dataAberturaFinal": data_fim,

                "ordenarPor": "dataPublicacao",
                "direcao": "DESC",
            }
            return {k: v for k, v in params.items() if v is not None}

        candidates = ["/licitacoes", "/compras"]
        chosen: Optional[str] = None
        results: List[Dict[str, Any]] = []

        # primeiro disparo para descobrir endpoint
        for cand in candidates:
            status, body = self._get(cand, _mount_params(pagina))
            if status == 200:
                chosen = cand
                results.extend(self._adapt_list(body))
                break
        if not chosen:
            raise PNCPError("Nenhum endpoint público de consulta respondeu (tentativas: /licitacoes, /compras).")

        # paginação sequencial
        current = pagina + 1
        while current < pagina + limite_paginas:
            time.sleep(pausa_s)
            status, body = self._get(chosen, _mount_params(current))
            if status != 200:
                break
            page_items = self._adapt_list(body)
            if not page_items:
                break
            results.extend(page_items)
            if len(page_items) < tamanho:
                break
            current += 1

        return results

    # -------- Adaptador de resposta --------
    def _adapt_list(self, body: Dict[str, Any] | List[Any] | str) -> List[Dict[str, Any]]:
        if isinstance(body, str):
            return []
        if isinstance(body, dict):
            if "content" in body and isinstance(body["content"], list):
                data = body["content"]
            elif "items" in body and isinstance(body["items"], list):
                data = body["items"]
            elif "resultado" in body and isinstance(body["resultado"], list):
                data = body["resultado"]
            else:
                data = [body]
        else:
            data = body  # type: ignore

        rows: List[Dict[str, Any]] = []
        for r in data:
            numero = r.get("numero") or r.get("numeroProcesso") or r.get("processo") or ""
            modalidade = r.get("modalidade") or r.get("modalidadeLicitacao") or ""
            obj = r.get("objeto") or r.get("resumoObjeto") or r.get("descricao") or ""
            orgao = r.get("orgao") or r.get("orgaoNome") or r.get("unidadeGestora") or ""
            municipio = r.get("municipio") or r.get("cidade") or r.get("municipioNome") or ""
            uf = r.get("uf") or r.get("siglaUf") or ""
            uasg = r.get("uasg") or r.get("orgaoUasg") or r.get("unidadeGestoraCodigo") or ""
            data_pub = r.get("dataPublicacao") or r.get("dataPublicacaoPncp") or r.get("dataPublicacaoEdital") or ""
            data_sess = r.get("dataAbertura") or r.get("dataSessao") or r.get("dataInicioProposta") or ""
            hora_sess = r.get("horaAbertura") or r.get("horaSessao") or ""
            valor = r.get("valorEstimado") or r.get("valorTotalEstimado") or r.get("valor") or ""
            link = r.get("linkEdital") or r.get("urlEdital") or r.get("link") or r.get("url") or ""

            rows.append({
                "id_remoto": str(r.get("id") or r.get("idCompra") or r.get("identificador") or ""),
                "numero_processo": str(numero).strip(),
                "modalidade": str(modalidade).strip(),
                "objeto": str(obj).strip(),
                "orgao": str(orgao).strip(),
                "municipio": str(municipio).strip(),
                "uf": str(uf).strip(),
                "uasg": str(uasg).strip(),
                "data_publicacao": str(data_pub).strip(),
                "data_sessao": str(data_sess).strip(),
                "hora_sessao": str(hora_sess).strip(),
                "valor_estimado": valor,
                "link_edital": link,
                "raw": r,
            })
        return rows
