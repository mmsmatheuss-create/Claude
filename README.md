# Trocas e Avarias — modelo analítico (SAP ZMMR270)

Transforma o export bruto do relatório **ZMMR270** (depósito 0002 — Trocas/Avarias) em um
modelo analítico navegável: quantidade e valor por **loja**, período, categoria, fornecedor e produto.

O resultado é um painel HTML único, sem dependências externas (`dist/painel-trocas-avarias.html`),
que abre em qualquer navegador — os dados vão embutidos no próprio arquivo.

## Como regerar

```bash
python3 scripts/build_model.py <export-ZMMR270.txt> data/model.json
python3 scripts/build_dashboard.py data/model.json dashboard/template.html dist/painel-trocas-avarias.html
```

Requisitos: Python 3 com `pandas`.

## O modelo

O export tem 27 colunas no cabeçalho e 26 nas linhas — a coluna `MBLNR` (nº do documento de
material) não vem preenchida. As demais colunas seguem a ordem do cabeçalho.

`build_model.py` monta um esquema estrela compacto:

| Tabela | Grão | Origem |
|---|---|---|
| `lojas` | 124 | `WERKS`, `WERKS_TEXT`, `REGIO` |
| `cats` | 28 categorias em 7 setores | `HIERNODE4` dentro de `HIERNODE3` |
| `forn` | 104 | `LIFNR`, `LIFNR_TEXT` |
| `prod` | 799 | `MATNR`, `MATNR_TEXT`, `MEINS`, categoria |
| `fato` | loja × mês × produto × fornecedor | 106.018 linhas agregadas em 28.249 registros |

Cada registro do fato guarda entradas e saídas separadas (`qi`/`qo` em quantidade,
`li`/`lo` em custo líquido, `ci`/`co` em custo CSGM), o que permite calcular no cliente
resultado (entradas − saídas), movimentação (entradas + saídas) ou cada lado isolado,
sem voltar à base.

## Tratamentos aplicados

- **Sinal SAP invertido**: `132.60-` vira `-132.60`.
- **Período** vem de `CPUDT_MKPF` (data de lançamento). `MJAHR` pode divergir e não é usado.
- **`VERPR_BRUTO_TOTAL` é idêntico a `VERPR_LIQUIDO_TOTAL`** em 100% das linhas, então só o
  líquido e o CSGM entram como medidas.
- **Nada é deduplicado**: sem `MBLNR` não há como separar linhas idênticas de documentos
  diferentes, e 5.923 linhas repetidas são mantidas (somam nos totais, como no relatório).
- **Quantidade mistura UN e KG** (96.221 e 9.797 linhas); o painel tem filtro de unidade
  para totais homogêneos.
- Códigos de material e fornecedor perdem os zeros à esquerda; textos perdem caracteres de
  controle do export.

## Conferência

Os totais do painel batem com a base bruta: quantidade líquida 46.072,2 · custo líquido
R$ 334.642,32 · custo CSGM R$ 361.897,63 · 106.018 lançamentos.
