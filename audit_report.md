# Auditoria — novo 5

## Global

- BASE_DESCONTO: OK
- ProgressRing: OK
- on_resize: OK

## Components

- components/badges.py: OK
- components/quick_filters.py: OK
- components/forms.py: OK

## Páginas

### dashboard — pages/dashboard.py [OK]
### empresas — pages/empresas.py [OK]
### certidoes — pages/certidoes.py [OK]
- status_badges: OK
- filters: OK
- export: OK
### licitacoes — pages/licitacoes.py [OK]
- badges: OK
- filters: OK
- export: OK
### cotacoes — pages/cotacoes.py [OK]
- total_calc: FALTA
- export: OK
### banco_precos — pages/banco_precos.py [OK]
- two_columns: OK
- filters: OK
- export: OK
### alertas — pages/alertas.py [OK]
- cards: OK
- badges: OK
- export: OK
### modelos — pages/modelos.py [OK]
- templates: OK
- export: OK
### oportunidades — pages/oportunidades.py [OK]
- pncp_btn: OK
- comprasnet_btn: OK
- export: OK

## services.db

### empresas: 4/4 funções
- list_empresas: OK
- add_empresa: OK
- upd_empresa: OK
- del_empresa: OK
### certidoes: 4/4 funções
- list_certidoes: OK
- add_certidao: OK
- upd_certidao: OK
- del_certidao: OK
### licitacoes: 4/4 funções
- list_licitacoes: OK
- add_licitacao: OK
- upd_licitacao: OK
- del_licitacao: OK
### cotacoes: 4/4 funções
- list_cotacoes: OK
- add_cotacao: OK
- upd_cotacao: OK
- del_cotacao: OK
### banco_precos: 4/4 funções
- list_banco_precos: OK
- add_banco_preco: OK
- upd_banco_preco: OK
- del_banco_preco: OK
### alertas: 4/4 funções
- list_alertas: OK
- add_alerta: OK
- upd_alerta: OK
- del_alerta: OK
### modelos: 4/4 funções
- list_modelos: OK
- add_modelo: OK
- upd_modelo: OK
- del_modelo: OK
### oportunidades: 4/4 funções
- list_oportunidades: OK
- add_oportunidade: OK
- upd_oportunidade: OK
- del_oportunidade: OK