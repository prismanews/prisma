#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRISMA - Buscador del Modo Vigilante (VERSIÓN MEJORADA)
Uso: python buscar.py "vivienda alquiler"
"""

import sys
import json
import urllib.parse
from datetime import datetime
import numpy as np
import os
import pickle
import hashlib
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Importar config
from config import *

# ========== CONFIGURACIÓN ==========
CACHE_BUSQUEDAS = "busquedas_cache.pkl"
UMBRAL_RELEVANCIA = 0.5  # Mínimo para considerar una noticia relevante
MAX_RESULTADOS = 100

# ========== CARGAR MODELO (UNA SOLA VEZ) ==========
print("🔄 Cargando modelo IA...")
modelo = SentenceTransformer("all-MiniLM-L6-v2")

# ========== FUNCIONES DE CACHÉ ==========
def get_cache_key(texto):
    return hashlib.md5(texto.encode('utf-8')).hexdigest()

def cargar_cache():
    if os.path.exists(CACHE_BUSQUEDAS):
        try:
            with open(CACHE_BUSQUEDAS, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def guardar_cache(cache):
    try:
        with open(CACHE_BUSQUEDAS, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass

# ========== BÚSQUEDA SEMÁNTICA MEJORADA ==========
def buscar_noticias_semantico(consulta, noticias, embedding_cache, top_n=50):
    """Busca noticias relacionadas semánticamente con la consulta"""
    if not consulta or not noticias:
        return []
    
    # Cache para la consulta
    key_consulta = get_cache_key(consulta)
    if key_consulta in embedding_cache:
        emb_consulta = np.array(embedding_cache[key_consulta])
    else:
        emb_consulta = modelo.encode([consulta])[0]
        embedding_cache[key_consulta] = emb_consulta.tolist()
    
    # Obtener embeddings de noticias
    titulos = [n["titulo"] for n in noticias]
    embeddings = []
    indices_validos = []
    
    for i, titulo in enumerate(titulos):
        key = get_cache_key(titulo)
        if key in embedding_cache:
            embeddings.append(np.array(embedding_cache[key]))
            indices_validos.append(i)
        else:
            emb = modelo.encode([titulo])[0]
            embedding_cache[key] = emb.tolist()
            embeddings.append(emb)
            indices_validos.append(i)
    
    if not embeddings:
        return []
    
    # Calcular similitudes
    embeddings = np.array(embeddings)
    similitudes = cosine_similarity([emb_consulta], embeddings)[0]
    
    # Filtrar y ordenar
    resultados = []
    for idx, sim in zip(indices_validos, similitudes):
        if sim > UMBRAL_RELEVANCIA:
            resultados.append({
                "noticia": noticias[idx],
                "similitud": round(sim, 3)
            })
    
    resultados.sort(key=lambda x: x["similitud"], reverse=True)
    return resultados[:top_n]

# ========== DESTACAR PALABRAS CLAVE ==========
def destacar_palabras(titulo, consulta):
    """Resalta las palabras de la consulta en el título"""
    palabras = consulta.lower().split()
    titulo_destacado = titulo
    
    for palabra in palabras:
        if len(palabra) > 3:
            # Resaltar con <mark> (amarillo)
            patron = re.compile(re.escape(palabra), re.IGNORECASE)
            titulo_destacado = patron.sub(f'<mark>{palabra}</mark>', titulo_destacado)
    
    return titulo_destacado

# ========== SUGERENCIAS DE BÚSQUEDA ==========
def sugerir_palabras(consulta, noticias):
    """Sugiere palabras relacionadas basadas en las noticias encontradas"""
    from collections import Counter
    
    palabras = consulta.lower().split()
    todas_palabras = []
    
    for n in noticias[:20]:  # Limitar a 20 noticias para velocidad
        titulo = n["titulo"].lower()
        for p in titulo.split():
            if len(p) > 4 and p not in palabras:
                todas_palabras.append(p)
    
    comunes = [p for p, _ in Counter(todas_palabras).most_common(5)]
    return comunes

# ========== GENERAR HTML DE RESULTADOS ==========
def generar_html_resultados(consulta, resultados, sugerencias):
    """Genera una página HTML con los resultados"""
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Prisma - Búsqueda: {consulta}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="prisma.css">
    <style>
        .resultado-item {{
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 16px 20px;
            margin-bottom: 12px;
            border: 1px solid var(--border-light);
            transition: var(--transition);
        }}
        .resultado-item:hover {{
            transform: translateX(4px);
            border-color: var(--primary);
            box-shadow: var(--shadow-md);
        }}
        .resultado-medio {{
            font-weight: 700;
            color: var(--accent);
            font-size: 13px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .resultado-titulo {{
            font-size: 16px;
            margin-bottom: 6px;
        }}
        .resultado-titulo a {{
            color: var(--text-primary);
            text-decoration: none;
        }}
        .resultado-titulo a:hover {{
            color: var(--primary);
            text-decoration: underline;
        }}
        .resultado-meta {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--text-tertiary);
        }}
        .resultado-similitud {{
            background: var(--primary-soft);
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
        }}
        mark {{
            background: #fef08a;
            padding: 0 2px;
            border-radius: 3px;
            color: var(--text-primary);
        }}
        .sugerencias {{
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            padding: 16px;
            margin: 20px 0;
            border: 1px solid var(--border-light);
        }}
        .sugerencias h3 {{
            font-size: 14px;
            margin-bottom: 10px;
            color: var(--text-secondary);
        }}
        .sugerencias-lista {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .sugerencia {{
            padding: 6px 14px;
            background: var(--bg-primary);
            border: 1px solid var(--border-medium);
            border-radius: 30px;
            font-size: 13px;
            color: var(--primary);
            text-decoration: none;
            transition: var(--transition);
        }}
        .sugerencia:hover {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }}
        .stats-busqueda {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 16px;
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div style="margin: 30px 0;">
            <a href="index.html" class="nav-link">← Volver a Inicio</a>
        </div>
        
        <h1>🔍 Resultados para "{consulta}"</h1>
        
        <div class="stats-busqueda">
            <span>📊 {len(resultados)} noticias encontradas</span>
            <span>📰 {len(set(r['medio'] for r in resultados))} medios diferentes</span>
        </div>
"""
    
    if sugerencias:
        html += f"""
        <div class="sugerencias">
            <h3>🔗 También podrías buscar:</h3>
            <div class="sugerencias-lista">
"""
        for sug in sugerencias:
            html += f'<a href="?q={sug}" class="sugerencia">{sug}</a>'
        html += """
            </div>
        </div>
"""
    
    if not resultados:
        html += f"""
        <div class="card" style="text-align: center; padding: 60px;">
            <h2>😕 No encontramos noticias sobre "{consulta}"</h2>
            <p>Prueba con otras palabras o términos más generales.</p>
        </div>
"""
    else:
        for r in resultados:
            titulo_destacado = destacar_palabras(r['titulo'], consulta)
            fecha = datetime.fromtimestamp(r['fecha']).strftime('%d/%m/%Y')
            html += f"""
        <div class="resultado-item">
            <div class="resultado-medio">{r['medio']}</div>
            <div class="resultado-titulo"><a href="{r['link']}" target="_blank">{titulo_destacado}</a></div>
            <div class="resultado-meta">
                <span>📅 {fecha}</span>
                <span class="resultado-similitud">Relevancia: {int(r.get('similitud', 0)*100)}%</span>
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    return html

# ========== MAIN ==========
def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python buscar.py \"consulta\"")
        print("Ejemplo: python buscar.py \"vivienda alquiler\"")
        sys.exit(1)
    
    consulta = sys.argv[1].strip()
    print(f"🔍 Buscando: {consulta}")
    
    # Cargar caché
    embedding_cache = cargar_cache()
    
    # Cargar noticias
    try:
        with open("noticias_cache.json", "r", encoding="utf-8") as f:
            noticias = json.load(f)
        print(f"📰 {len(noticias)} noticias en caché")
    except FileNotFoundError:
        print("❌ No hay noticias en caché. Ejecuta primero rss_prisma.py")
        sys.exit(1)
    
    # Buscar
    resultados = buscar_noticias_semantico(consulta, noticias, embedding_cache, top_n=MAX_RESULTADOS)
    print(f"✅ {len(resultados)} resultados encontrados")
    
    # Guardar caché actualizada
    guardar_cache(embedding_cache)
    
    # Generar sugerencias
    sugerencias = sugerir_palabras(consulta, [r['noticia'] for r in resultados]) if resultados else []
    
    # Generar HTML
    html = generar_html_resultados(
        consulta,
        [r['noticia'] for r in resultados],
        sugerencias
    )
    
    # Guardar archivo
    nombre_archivo = f"buscar_{consulta.lower().replace(' ', '_')}.html"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ Generado: {nombre_archivo}")
    print(f"🌐 Abre: https://prismanews.github.io/prisma/{nombre_archivo}")

if __name__ == "__main__":
    main()
