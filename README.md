# Trocas e Avarias — modelo analítico (SAP ZMMR270)

Transforma o export bruto do relatório **ZMMR270** (depósito 0002 — Trocas/Avarias) em um
modelo analítico navegável: quantidade e valor por **loja**, período, categoria, fornecedor e produto.

O resultado é um painel HTML único, sem dependências externas. São duas saídas do mesmo template:

| Arquivo | Para quê |
|---|---|
| `dist/painel-trocas-avarias-offline.html` | documento HTML completo e **vazio** (83 KB): abre pedindo o export e monta o modelo no navegador |
| `dist/painel-trocas-avarias.html` | só o conteúdo da página, com a base embutida, para publicar como Artifact |

## Como regerar

```bash
python3 scripts/build_model.py <export-ZMMR270.txt> data/model.json
python3 scripts/build_dashboard.py data/model.json dashboard/template.html \
  dist/painel-trocas-avarias-offline.html --standalone --sem-base   # arquivo vazio
python3 scripts/build_dashboard.py data/model.json dashboard/template.html \
  dist/painel-trocas-avarias.html                          # para publicar como Artifact
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

Cada registro do fato guarda entradas e saídas separadas — `qi`/`qo` em quantidade e `li`/`lo`
em reais — o que permite calcular no cliente o resultado (entradas − saídas) ou cada lado isolado,
sem voltar à base. O valor em reais é sempre
`VERPR_LIQUIDO_TOTAL`; `VERPR_CSGM_TOTAL` não entra no modelo.

## Cálculos

`docs/calculos.html` documenta, campo a campo, a conta que produz cada número: o tratamento da linha
do relatório, os sete acumuladores do grão, o filtro, a combinação medida × visão e a fórmula de cada
indicador, barra, coluna de tabela e coluna exportada — com um exemplo conferido de ponta a ponta.
Se a conta mudar no código, esse documento muda junto.

## Tratamentos aplicados

- **Sinal SAP invertido**: `132.60-` vira `-132.60`.
- **Período** vem de `CPUDT_MKPF` (data de lançamento). `MJAHR` pode divergir e não é usado.
- **O valor em reais é só o custo líquido** (`VERPR_LIQUIDO_TOTAL`). `VERPR_BRUTO_TOTAL` é idêntico
  a ele em 100% das linhas e `VERPR_CSGM_TOTAL` ficou fora do modelo — nenhum cálculo usa CSGM.
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
python3 scripts/build_dashboard.py data/model.json dashboard/template.html \
  dist/painel-trocas-avarias-offline.html --standalone --sem-base   # arquivo vazio
python3 scripts/build_dashboard.py data/model.json dashboard/template.html \
  dist/painel-trocas-avarias.html                          # para publicar como Artifact
```

## Itens por loja

O cartão **Itens com trocas lançadas** tem o próprio seletor de loja e lista *todos* os itens com
lançamento nela — não um top N. Cada linha soma os lançamentos do item: última movimentação,
quantidade de entrada, saída e líquida, os mesmos três em R$, hierarquia e fornecedor. Ordena por
qualquer coluna, busca por descrição, código, categoria ou fornecedor, e fecha com o total, que bate
com a linha da loja na tabela acima. O seletor é o filtro global de loja: mudá-lo reescreve o painel
inteiro. Com uma única loja no recorte o ranking de lojas sai da tela — uma barra só não é gráfico.

## Exportar o recorte filtrado

Botão **Baixar base**: um clique, um arquivo — a base detalhada do recorte filtrado, uma linha por
registro do grão loja × mês × produto × fornecedor. Traz as sete medidas (lançamentos, quantidade e reais, cada um em entrada,
saída e resultado), independente da medida escolhida na tela.

- **.xlsx** — cabeçalho congelado, autofiltro e formato numérico. Gerado em JS (zip com deflate via
  `CompressionStream`), sem biblioteca externa.
- **.csv** — separador `;`, decimal com vírgula e BOM, abre direto no Excel em português. É o formato
  usado onde o `.xlsx` não é permitido.

O botão aparece quando salvar arquivo é possível: sempre no `dist/painel-trocas-avarias-offline.html` aberto
direto no navegador; na versão publicada como Artifact, só com a capacidade `downloads`, que exige o
artefato **não** estar compartilhado publicamente.

## Conferência

Os totais do painel batem com a base bruta: quantidade líquida 46.072,2 · R$ 334.642,32 ·
106.018 lançamentos.

O leitor em JS foi conferido contra o pipeline em Python: recarregando o mesmo export pelo botão
**Atualizar dados**, os seis indicadores e as dimensões ficam idênticos. Um recorte filtrado
(loja 1046, set/2024 a ago/2026) exportado pelo painel bate com o `pandas` em todas as colunas:
641 lançamentos, 2.809 / 1.633 / 1.176 de quantidade, R$ 83.655,02 / 54.199,03 / 29.455,99 e
306 linhas no grão detalhado.
