#!/usr/bin/env python3
"""Injeta o modelo analitico (JSON) no template do painel e grava o HTML final.

Uso: python3 scripts/build_dashboard.py <modelo.json> <template.html> <saida.html>
"""
import sys, pathlib

modelo, template, saida = sys.argv[1], sys.argv[2], sys.argv[3]
dados = pathlib.Path(modelo).read_text(encoding="utf-8")
# "</" vira "<\/" para que a string nunca feche o <script> que a hospeda ("\/" e JSON valido).
dados = dados.replace("</", "<\\/")
html = pathlib.Path(template).read_text(encoding="utf-8").replace("__MODEL_JSON__", dados)
pathlib.Path(saida).write_text(html, encoding="utf-8")
print(f"{saida}: {len(html)/1048576:.2f} MB")
