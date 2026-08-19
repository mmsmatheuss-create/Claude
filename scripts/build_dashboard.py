#!/usr/bin/env python3
"""Injeta o modelo analitico (JSON) no template do painel e grava o HTML final.

Sem --standalone grava so o conteudo da pagina, do jeito que o publicador de
Artifact espera (ele mesmo envolve em <!doctype html><head>...</head><body>).
Com --standalone grava um documento HTML completo, para abrir direto do disco.

Uso: python3 scripts/build_dashboard.py <modelo.json> <template.html> <saida.html> [--standalone]
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
completo = "--standalone" in sys.argv[4:]

dados = pathlib.Path(modelo).read_text(encoding="utf-8")
# "</" vira "<\/" para que a string nunca feche o <script> que a hospeda ("\/" e JSON valido).
dados = dados.replace("</", "<\\/")
html = pathlib.Path(template).read_text(encoding="utf-8").replace("__MODEL_JSON__", dados)
if completo:
    html = CABECALHO + html + RODAPE
pathlib.Path(saida).write_text(html, encoding="utf-8")
print(f"{saida}: {len(html)/1048576:.2f} MB{' (documento completo)' if completo else ''}")
