#!/usr/bin/env python3
"""Injeta o modelo analitico (JSON) no template do painel e grava o HTML final.

Sem --standalone grava so o conteudo da pagina, do jeito que o publicador de
Artifact espera (ele mesmo envolve em <!doctype html><head>...</head><body>).
Com --standalone grava um documento HTML completo, para abrir direto do disco.
Com --sem-base grava o painel vazio: ele abre pedindo o export do ZMMR270 e
monta o modelo no navegador, sem nenhum dado dentro do arquivo.

Uso: python3 scripts/build_dashboard.py <modelo.json> <template.html> <saida.html>
                                        [--standalone] [--sem-base]
"""
import sys, pathlib

CABECALHO = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>*{margin:0}img,svg{display:block;max-width:100%}</style>
</head>
<body>
"""
RODAPE = "\n</body>\n</html>\n"

modelo, template, saida = sys.argv[1], sys.argv[2], sys.argv[3]
opcoes = sys.argv[4:]
completo = "--standalone" in opcoes
sem_base = "--sem-base" in opcoes

if sem_base:
    dados = "null"
else:
    dados = pathlib.Path(modelo).read_text(encoding="utf-8")
    # "</" vira "<\/" para que a string nunca feche o <script> que a hospeda ("\/" e JSON valido).
    dados = dados.replace("</", "<\\/")
html = pathlib.Path(template).read_text(encoding="utf-8").replace("__MODEL_JSON__", dados)
if completo:
    html = CABECALHO + html + RODAPE
pathlib.Path(saida).write_text(html, encoding="utf-8")
marcas = ", ".join(m for m, on in [("documento completo", completo), ("sem base", sem_base)] if on)
print(f"{saida}: {len(html)/1048576:.2f} MB{' (' + marcas + ')' if marcas else ''}")
