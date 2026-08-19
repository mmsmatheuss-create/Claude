#!/usr/bin/env python3
"""
Constroi o modelo analitico (star schema compacto) a partir do export SAP ZMMR270.

Entrada : arquivo .txt do ZMMR270 (delimitado por ';', UTF-8, CRLF, numeros SAP
          com sinal negativo a direita: "132.60-").
Saida   : JSON com dimensoes + tabela fato agregada no grao
          [loja x mes x produto x fornecedor], usado pelo dashboard HTML.

Uso: python3 scripts/build_model.py <arquivo.txt> <saida.json>
"""
import sys, json, unicodedata
import pandas as pd
import numpy as np

# O cabecalho do export tem 27 colunas mas as linhas de dados trazem 26:
# a coluna MBLNR (numero do documento de material) vem vazia/suprimida.
COLS = ["HLIFNR","HLIFNR_TEXT","LIFNR","LIFNR_TEXT","WERKS","WERKS_TEXT","LGORT","LGORT_TEXT",
        "HIERNODE3","HIERNODE3_TEXT","HIERNODE4","HIERNODE4_TEXT","REGIO","MATNR","MATNR_TEXT",
        "MEINS","MENGE","VERPR_BRUTO","VERPR_LIQUIDO","VERPR_CSGM","VERPR_BRUTO_TOTAL",
        "VERPR_LIQUIDO_TOTAL","VERPR_CSGM_TOTAL","MJAHR","ZEILE","CPUDT_MKPF"]

MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]


def sap_num(s: pd.Series) -> np.ndarray:
    """Converte numero SAP em float. Sinal negativo vem no final: '132.60-'."""
    s = s.str.strip()
    neg = s.str.endswith("-")
    v = pd.to_numeric(s.str.rstrip("-").replace("", "0"), errors="coerce").fillna(0.0)
    return np.where(neg, -v, v)


def clean(s: pd.Series) -> pd.Series:
    """Normaliza texto: remove caracteres de controle e espacos duplicados."""
    return (s.str.replace(r"[\x00-\x1f\x7f-\x9f]", "", regex=True)
             .str.replace(r"\s+", " ", regex=True).str.strip())


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", skiprows=1, names=COLS, dtype=str,
                     keep_default_na=False, encoding="utf-8")
    for c in COLS:
        df[c] = clean(df[c])
    for c in ["MENGE", "VERPR_LIQUIDO_TOTAL", "VERPR_CSGM_TOTAL"]:
        df[c] = sap_num(df[c])

    df["YM"] = df.CPUDT_MKPF.str[:6]
    df.loc[~df.YM.str.fullmatch(r"\d{6}"), "YM"] = ""
    df = df[df.YM != ""].copy()

    df["MATNR"] = df.MATNR.str.lstrip("0")
    df["LIFNR"] = df.LIFNR.str.lstrip("0").replace("", "—")
    df.loc[df.LIFNR_TEXT == "", "LIFNR_TEXT"] = "(sem fornecedor)"
    return df


def build(df: pd.DataFrame) -> dict:
    # ---------- dimensoes ----------
    lojas = (df.groupby("WERKS").agg(nome=("WERKS_TEXT", "first"), uf=("REGIO", "first"))
               .reset_index().sort_values("nome"))
    lojas_ix = {k: i for i, k in enumerate(lojas.WERKS)}

    cats = (df.groupby("HIERNODE4").agg(nome=("HIERNODE4_TEXT", "first"),
                                        g=("HIERNODE3", "first"), gnome=("HIERNODE3_TEXT", "first"))
              .reset_index().sort_values("nome"))
    cats_ix = {k: i for i, k in enumerate(cats.HIERNODE4)}

    forn = (df.groupby("LIFNR").agg(nome=("LIFNR_TEXT", "first"))
              .reset_index().sort_values("nome"))
    forn_ix = {k: i for i, k in enumerate(forn.LIFNR)}

    prod = (df.groupby("MATNR").agg(nome=("MATNR_TEXT", "first"), un=("MEINS", "first"),
                                    cat=("HIERNODE4", "first"))
              .reset_index().sort_values("nome"))
    prod_ix = {k: i for i, k in enumerate(prod.MATNR)}

    meses = sorted(df.YM.unique())
    mes_ix = {k: i for i, k in enumerate(meses)}

    # ---------- fato agregado ----------
    # Entradas (movimento positivo) e saidas (negativo) sao somadas em separado
    # para permitir ver liquido, entradas, saidas ou movimentacao total.
    d = df.assign(
        pos=df.MENGE > 0,
        qi=np.where(df.MENGE > 0, df.MENGE, 0.0),
        qo=np.where(df.MENGE < 0, -df.MENGE, 0.0),
        li=np.where(df.MENGE > 0, df.VERPR_LIQUIDO_TOTAL, 0.0),
        lo=np.where(df.MENGE < 0, -df.VERPR_LIQUIDO_TOTAL, 0.0),
        ci=np.where(df.MENGE > 0, df.VERPR_CSGM_TOTAL, 0.0),
        co=np.where(df.MENGE < 0, -df.VERPR_CSGM_TOTAL, 0.0),
    )
    fato = (d.groupby(["WERKS", "YM", "MATNR", "LIFNR"], sort=False)
             .agg(n=("qi", "size"), qi=("qi", "sum"), qo=("qo", "sum"),
                  li=("li", "sum"), lo=("lo", "sum"), ci=("ci", "sum"), co=("co", "sum"))
             .reset_index())

    rows = [[int(lojas_ix[r.WERKS]), int(mes_ix[r.YM]), int(prod_ix[r.MATNR]),
             int(forn_ix[r.LIFNR]), int(r.n),
             round(r.qi, 3), round(r.qo, 3),
             round(r.li, 2), round(r.lo, 2), round(r.ci, 2), round(r.co, 2)]
            for r in fato.itertuples()]

    return {
        "meta": {
            "fonte": "SAP ZMMR270 — Trocas e Avarias",
            "linhas_origem": int(len(df)),
            "linhas_fato": len(rows),
            "periodo": [meses[0], meses[-1]],
            "deposito": sorted(df.LGORT_TEXT.unique().tolist()),
        },
        "meses": meses,
        "lojas": [[w, n, u] for w, n, u in zip(lojas.WERKS, lojas.nome, lojas.uf)],
        "cats": [[c, n, g, gn] for c, n, g, gn in zip(cats.HIERNODE4, cats.nome, cats.g, cats.gnome)],
        "forn": [[c, n] for c, n in zip(forn.LIFNR, forn.nome)],
        "prod": [[c, n, u, int(cats_ix[k])] for c, n, u, k in
                 zip(prod.MATNR, prod.nome, prod.un, prod.cat)],
        "fato": rows,
    }


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    model = build(load(src))
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, separators=(",", ":"))
    m = model["meta"]
    print(f"origem={m['linhas_origem']} fato={m['linhas_fato']} "
          f"lojas={len(model['lojas'])} produtos={len(model['prod'])} "
          f"fornecedores={len(model['forn'])} meses={len(model['meses'])} "
          f"periodo={m['periodo']}")
