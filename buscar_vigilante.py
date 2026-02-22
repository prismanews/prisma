#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRISMA - Buscador del Modo Vigilante
Ejecutar: python buscar_vigilante.py "consulta"
"""

import sys
import json
import urllib.parse
from datetime import datetime
import numpy as np

from config import *
from rss_prisma import (
    modelo, cargar_cache_embeddings, get_embedding_cache_key,
    buscar_noticias_semantico, clusterizar,
    generar_vigilante_html
)

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python buscar_vigilante.py \"consulta\"")
        print("Ejemplo: python buscar_vigilante.py \"vivienda alquiler\"")
        sys.exit(1)
    
    consulta = sys.argv[1]
    consulta_url = urllib.parse.quote(consulta)
    
    print(f"👁️ Buscando: {consulta}")
    
    # Cargar caché
    embedding_cache = cargar_cache_embeddings() if CACHE_EMBEDDINGS else {}
    
    # Cargar noticias
    try:
        with open("noticias_cache.json", "r", encoding="utf-8") as f:
            noticias = json.load(f)
        print(f"📰 {len(noticias)} noticias en caché")
    except FileNotFoundError:
        print("❌ No hay noticias en caché. Ejecuta primero rss_prisma.py")
        sys.exit(1)
    
    # Buscar noticias relacionadas
    print("🔍 Buscando noticias semánticamente relacionadas...")
    noticias_filtradas = buscar_noticias_semantico(consulta, noticias, embedding_cache, top_n=100)
    print(f"✅ {len(noticias_filtradas)} noticias encontradas")
    
    if not noticias_filtradas:
        grupos = []
    else:
        # Calcular embeddings y clusterizar
        titulos = [n["titulo"] for n in noticias_filtradas]
        embeddings = modelo.encode(titulos, batch_size=32, show_progress_bar=False)
        grupos = clusterizar(embeddings)
        print(f"📊 {len(grupos)} enfoques detectados")
    
    # Generar HTML
    fecha = datetime.now()
    html = generar_vigilante_html(
        consulta,
        noticias_filtradas,
        grupos,
        fecha.strftime("%d/%m/%Y %H:%M"),
        fecha.isoformat(),
        int(fecha.timestamp()),
        len(noticias)
    )
    
    # Guardar archivo
    nombre_archivo = f"vigilante_{consulta_url}.html"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ Generado: {nombre_archivo}")
    print(f"🌐 Abre: https://prismanews.github.io/prisma/{nombre_archivo}")

if __name__ == "__main__":
    main()
