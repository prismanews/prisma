#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRISMA - Buscador del Modo Vigilante
Uso: python buscar.py?q=vivienda
"""

import sys
import json
import urllib.parse
from datetime import datetime
import numpy as np

# Configuración básica
import feedparser
import re
import html
import random
from collections import Counter
import hashlib
import os
import time
import pickle
from difflib import SequenceMatcher
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Importar config
from config import *

# Cargar modelo
print("🔄 Cargando modelo IA...")
modelo = SentenceTransformer("all-MiniLM-L6-v2")

# Funciones necesarias (copia las que ya tienes en rss_prisma.py)
def get_embedding_cache_key(texto):
    return hashlib.md5(texto.encode('utf-8')).hexdigest()

def cargar_cache_embeddings():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def buscar_noticias_semantico(consulta, noticias, embedding_cache, top_n=50):
    if not consulta or not noticias:
        return []
    
    key_consulta = get_embedding_cache_key(consulta)
    if key_consulta in embedding_cache:
        emb_consulta = np.array(embedding_cache[key_consulta])
    else:
        emb_consulta = modelo.encode([consulta])[0]
        embedding_cache[key_consulta] = emb_consulta.tolist()
    
    titulos = [n["titulo"] for n in noticias]
    embeddings_noticias = []
    indices_validos = []
    
    for i, titulo in enumerate(titulos):
        key = get_embedding_cache_key(titulo)
        if key in embedding_cache:
            embeddings_noticias.append(np.array(embedding_cache[key]))
            indices_validos.append(i)
        else:
            emb = modelo.encode([titulo])[0]
            embedding_cache[key] = emb.tolist()
            embeddings_noticias.append(emb)
            indices_validos.append(i)
    
    if not embeddings_noticias:
        return []
    
    embeddings_noticias = np.array(embeddings_noticias)
    similitudes = cosine_similarity([emb_consulta], embeddings_noticias)[0]
    
    resultados = []
    for idx, sim in zip(indices_validos, similitudes):
        if sim > 0.5:
            resultados.append({
                "noticia": noticias[idx],
                "similitud": sim
            })
    
    resultados.sort(key=lambda x: x["similitud"], reverse=True)
    return [r["noticia"] for r in resultados[:top_n]]

def clusterizar(embeddings):
    from sklearn.metrics.pairwise import cosine_similarity
    grupos = []
    
    for i, emb in enumerate(embeddings):
        mejor_grupo = None
        mejor_score = 0
        
        for g_idx, grupo in enumerate(grupos):
            centroide = np.mean(embeddings[grupo], axis=0)
            score = cosine_similarity([emb], [centroide])[0][0]
            
            if score > mejor_score:
                mejor_score = score
                mejor_grupo = g_idx
        
        if mejor_score > UMBRAL_CLUSTER:
            grupos[mejor_grupo].append(i)
        else:
            grupos.append([i])
    
    return [g for g in grupos if len(g) >= 2]

def analizar_sesgo(indices, noticias):
    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16, show_progress_bar=False)
    centroide = np.mean(emb, axis=0).reshape(1, -1)
    
    # Simplificado - necesitas cargar referencias_politicas
    return {
        "texto": "Análisis de sesgo",
        "pct_prog": 50,
        "pct_cons": 50
    }

def generar_html_resultados(consulta, noticias_filtradas, grupos):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Vigilante: {consulta} | Prisma</title>
        <link rel="stylesheet" href="prisma.css">
        <meta http-equiv="refresh" content="0; URL=vigilante.html?q={urllib.parse.quote(consulta)}">
    </head>
    <body>
        <p>Redirigiendo a los resultados de "{consulta}"...</p>
    </body>
    </html>
    """
    return html

def main():
    # Obtener query string
    query_string = sys.argv[1] if len(sys.argv) > 1 else ""
    params = urllib.parse.parse_qs(query_string.lstrip('?'))
    consulta = params.get('q', [''])[0]
    
    if not consulta:
        print("Contenido-Type: text/html\n")
        print("<html><body><script>window.location='vigilante.html';</script></body></html>")
        return
    
    # Cargar caché y noticias
    embedding_cache = cargar_cache_embeddings()
    
    try:
        with open("noticias_cache.json", "r", encoding="utf-8") as f:
            noticias = json.load(f)
    except FileNotFoundError:
        print("Contenido-Type: text/html\n")
        print("<html><body><h3>Error: No hay noticias en caché</h3></body></html>")
        return
    
    # Buscar y procesar
    noticias_filtradas = buscar_noticias_semantico(consulta, noticias, embedding_cache, top_n=100)
    
    if noticias_filtradas:
        titulos = [n["titulo"] for n in noticias_filtradas]
        embeddings = modelo.encode(titulos, batch_size=32, show_progress_bar=False)
        grupos = clusterizar(embeddings)
    else:
        grupos = []
    
    # Guardar resultado como archivo HTML estático
    consulta_segura = consulta.lower().replace(" ", "_")
    nombre_archivo = f"buscar_{consulta_segura}.html"
    
    from rss_prisma import generar_vigilante_html
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
    
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Redirigir
    print(f"Contenido-Type: text/html\n")
    print(f"<html><body><script>window.location='{nombre_archivo}';</script></body></html>")

if __name__ == "__main__":
    main()
