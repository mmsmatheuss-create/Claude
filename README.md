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
| `cats` | 28 nós do 4º nível, dentro de 7 do 3º | `HIERNODE4`/`HIERNODE4_TEXT` dentro de `HIERNODE3`/`HIERNODE3_TEXT` |
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
- **Hierarquia de mercadoria** aparece pela denominação, não pelo código: `HIERNODE3_TEXT`
  é a *Denominação 3º Nó* (7 nós) e `HIERNODE4_TEXT` a *Denominação 4º Nó* (28 nós). O painel
  filtra e agrupa por qualquer um dos dois níveis.
- Códigos de material e fornecedor perdem os zeros à esquerda; textos perdem caracteres de
  controle do export.

## Atualizar a base

Dois caminhos, com o mesmo resultado:

**Pelo painel** — botão **Atualizar dados**: escolha (ou arraste) um novo export do ZMMR270 em `.txt`.
O painel lê e reagrega tudo no próprio navegador — o arquivo não sai da máquina — e guarda a base em
IndexedDB, então ela sobrevive ao recarregar. "Restaurar a base publicada" volta à base embutida.
O leitor em JS (`dashboard/template.html`, `lerZMMR270`) aceita o layout com ou sem `MBLNR`, em UTF-8 ou
ANSI, e localiza as colunas pelo cabeçalho.

**Pelos scripts** — regera o HTML publicado, com a base nova já embutida:

```bash
python3 scripts/build_model.py <novo-export.txt> data/model.json
python3 scripts/build_dashboard.py data/model.json dashboard/template.html dist/painel-trocas-avarias.html
```

## Exportar o recorte filtrado

Botão **Baixar planilha**. Sai exatamente o que está filtrado, em oito recortes: filtros e totais,
por loja, por mês, por 3º nó, por 4º nó, por fornecedor, por produto e a base detalhada no grão
loja × mês × produto × fornecedor. Toda tabela traz as dez medidas (lançamentos, quantidade e os dois
custos, cada um em entrada, saída e resultado), independente da medida escolhida na tela.

- **.xlsx** — pasta completa, uma aba por recorte, com cabeçalho congelado, autofiltro e formato
  numérico. Gerada em JS (zip com deflate via `CompressionStream`), sem biblioteca externa.
- **.csv** — um recorte por arquivo, separador `;`, decimal com vírgula e BOM, abre direto no Excel
  em português.

O botão aparece quando salvar arquivo é possível: sempre no `dist/painel-trocas-avarias.html` aberto
direto no navegador; na versão publicada como Artifact, só com a capacidade `downloads`, que exige o
artefato **não** estar compartilhado publicamente.

## Conferência

Os totais do painel batem com a base bruta: quantidade líquida 46.072,2 · custo líquido
R$ 334.642,32 · custo CSGM R$ 361.897,63 · 106.018 lançamentos.

O leitor em JS foi conferido contra o pipeline em Python: recarregando o mesmo export pelo botão
**Atualizar dados**, os seis indicadores e as dimensões ficam idênticos. Um recorte filtrado
(loja 1046, set/2024 a ago/2026) exportado pelo painel bate com o `pandas` em todas as colunas:
641 lançamentos, 2.809 / 1.633 / 1.176 de quantidade, R$ 83.655,02 / 54.199,03 / 29.455,99 de custo
líquido e 306 linhas no grão detalhado.
