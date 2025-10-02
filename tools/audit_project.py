# tools/audit_project.py
import os, re, importlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "dashboard": "pages/dashboard.py",
    "empresas": "pages/empresas.py",
    "certidoes": "pages/certidoes.py",
    "licitacoes": "pages/licitacoes.py",
    "cotacoes": "pages/cotacoes.py",
    "banco_precos": "pages/banco_precos.py",
    "alertas": "pages/alertas.py",
    "modelos": "pages/modelos.py",
    "oportunidades": "pages/oportunidades.py",
}
SERVICES = {
    "db": "services/db.py",
    "exports": "services/exports.py",
}
COMPONENTS = {
    "badges": "components/badges.py",
    "quick_filters": "components/quick_filters.py",
    "forms": "components/forms.py",
}

FEATURES = {
    "global": {
        "BASE_DESCONTO": re.compile(r"BASE_DESCONTO\s*=\s*-?1\d{2}"),
        "ProgressRing": re.compile(r"\bProgressRing\b"),
        "on_resize": re.compile(r"\.on_resize\s*="),
    },
    "certidoes": {
        "status_badges": re.compile(r"badge_(regular|vencendo|vencida)"),
        "filters": re.compile(r"quick_filter_bar"),
        "export": re.compile(r"export_(csv|xlsx)"),
    },
    "licitacoes": {
        "badges": re.compile(r"badge_"),
        "filters": re.compile(r"quick_filter_bar"),
        "export": re.compile(r"export_(csv|xlsx)"),
    },
    "cotacoes": {
        "total_calc": re.compile(r"_total_row"),
        "export": re.compile(r"export_(csv|xlsx)"),
    },
    "banco_precos": {
        "two_columns": re.compile(r"COL_LEFT|COL_RIGHT"),
        "filters": re.compile(r"quick_filter_bar"),
        "export": re.compile(r"export_left|export_right"),
    },
    "alertas": {
        "cards": re.compile(r"ListView\(.*controls=\[\]\)|Container\(.*cart"),
        "badges": re.compile(r"badge_"),
        "export": re.compile(r"export_(csv|xlsx)"),
    },
    "modelos": {
        "templates": re.compile(r"TEMPLATES\s*=\s*\{"),
        "export": re.compile(r"export_(csv|xlsx)"),
    },
    "oportunidades": {
        "pncp_btn": re.compile(r"PNCP"),
        "comprasnet_btn": re.compile(r"ComprasNet"),
        "export": re.compile(r"export_(csv|xlsx)"),
    }
}

DB_FUNCS_EXPECTED = {
    "empresas": ["list_empresas","add_empresa","upd_empresa","del_empresa"],
    "certidoes": ["list_certidoes","add_certidao","upd_certidao","del_certidao"],
    "licitacoes": ["list_licitacoes","add_licitacao","upd_licitacao","del_licitacao"],
    "cotacoes": ["list_cotacoes","add_cotacao","upd_cotacao","del_cotacao"],
    "banco_precos": ["list_banco_precos","add_banco_preco","upd_banco_preco","del_banco_preco"],
    "alertas": ["list_alertas","add_alerta","upd_alerta","del_alerta"],
    "modelos": ["list_modelos","add_modelo","upd_modelo","del_modelo"],
    "oportunidades": ["list_oportunidades","add_oportunidade","upd_oportunidade","del_oportunidade"],
}

def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def check_patterns(file_path, patterns):
    code = read(file_path)
    found = {}
    for key, rx in patterns.items():
        found[key] = bool(rx.search(code))
    return found

def import_services_db():
    sys.path.insert(0, str(ROOT))
    try:
        db = importlib.import_module("services.db")
        return db
    except Exception as ex:
        return None

def check_db_funcs(dbmod):
    present = {}
    for area, funcs in DB_FUNCS_EXPECTED.items():
        present[area] = {f: hasattr(dbmod, f) for f in funcs}
    return present

def main():
    report = []
    report.append(f"# Auditoria — {ROOT.name}\n")

    # Global
    main_py = ROOT / "main.py"
    report.append("## Global\n")
    g = check_patterns(main_py, FEATURES["global"]) if main_py.exists() else {}
    for k, v in g.items():
        report.append(f"- {k}: {'OK' if v else 'FALTA'}")

    # Components
    report.append("\n## Components\n")
    for name, rel in COMPONENTS.items():
        p = ROOT / rel
        report.append(f"- {rel}: {'OK' if p.exists() else 'FALTA'}")

    # Pages
    report.append("\n## Páginas\n")
    for page_name, rel in PAGES.items():
        p = ROOT / rel
        status = "OK" if p.exists() else "FALTA"
        report.append(f"### {page_name} — {rel} [{status}]")
        if p.exists() and page_name in FEATURES:
            feats = check_patterns(p, FEATURES[page_name])
            for k, v in feats.items():
                report.append(f"- {k}: {'OK' if v else 'FALTA'}")

    # DB
    report.append("\n## services.db\n")
    dbmod = import_services_db()
    if not dbmod:
        report.append("- Falha ao importar services.db (verifique sys.path e erros de sintaxe).")
    else:
        present = check_db_funcs(dbmod)
        for area, funcs in present.items():
            oks = sum(1 for _k, _v in funcs.items() if _v)
            total = len(funcs)
            report.append(f"### {area}: {oks}/{total} funções")
            for fname, ok in funcs.items():
                report.append(f"- {fname}: {'OK' if ok else 'FALTA'}")

    out = ROOT / "audit_report.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"Relatório gerado em: {out}")

if __name__ == "__main__":
    main()
