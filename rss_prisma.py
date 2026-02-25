#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRISMA - Generador principal (VERSIÓN SIMPLIFICADA CON MODO VIGILANTE)
"""

import feedparser
import re
import html
import random
from datetime import datetime
from collections import Counter
import numpy as np
import hashlib
import json
import os
import time
import logging
import urllib.request
import socket
import pickle
import urllib.parse
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ========== IMPORTAR CONFIGURACIÓN Y FEEDS ==========
from config import *
from feeds import feeds_espanoles, feeds_internacionales

# ========== CONFIGURAR LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ========== MODELO IA ==========
modelo = SentenceTransformer("all-MiniLM-L6-v2")

# ========== REFERENCIAS DE SESGO (SOLO PROGRESISTA/CONSERVADOR) ==========
referencias_politicas = {
    "progresista": modelo.encode([
        # --- DERECHOS SOCIALES ---
        "derecho a la vivienda",
        "sanidad pública universal",
        "pensiones públicas dignas",
        "educación pública gratuita",
        "servicios sociales",
        "derechos laborales",
        "sindicatos",
        "igualdad real",
        "brecha salarial",
        "derechos LGTBI",
        "feminismo",
        "acogida refugiados",
        "derechos humanos inmigrantes",
        "memoria histórica",
        "transición ecológica",
        "cambio climático",
        "alquiler asequible",
        "vivienda pública",
        "justicia social",
        "salario mínimo",
    ]),
    
    "conservador": modelo.encode([
        # --- SEGURIDAD Y ORDEN ---
        "seguridad ciudadana",
        "mano dura",
        "control fronteras",
        "penas más duras",
        "ley mordaza",
        "orden público",
        "unidad de españa",
        "constitución española",
        "nación española",
        "bajar impuestos",
        "libertad económica",
        "emprendedores",
        "reforma laboral",
        "libre mercado",
        "inmigración ilegal",
        "devoluciones",
        "familia tradicional",
        "valores tradicionales",
        "tauromaquia",
        "cadena perpetua",
        "autoridad",
        "fuerzas armadas",
        "monarquía",
    ]),
}

# ========== FUNCIONES DE UTILIDAD ==========
def limpiar_html(texto):
    texto = html.unescape(texto)
    texto = re.sub(r'<.*?>', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return [p for p in palabras if p not in STOPWORDS and len(p) > 3]

def get_embedding_cache_key(texto):
    return hashlib.md5(texto.encode('utf-8')).hexdigest()

def cargar_cache_embeddings():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logging.warning(f"Error cargando caché: {e}")
    return {}

def guardar_cache_embeddings(cache):
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except Exception as e:
        logging.warning(f"Error guardando caché: {e}")

def son_duplicados_texto(texto1, texto2, umbral_texto=0.8):
    if not texto1 or not texto2:
        return False
    ratio = SequenceMatcher(None, texto1.lower(), texto2.lower()).ratio()
    return ratio > umbral_texto

def extraer_fecha_noticia(entry):
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return time.mktime(entry.published_parsed)
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return time.mktime(entry.updated_parsed)
    except:
        pass
    return time.time()

def obtener_feed_seguro(url, medio, max_intentos=2):
    for intento in range(max_intentos):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            # ELIMINADO: timeout NO es válido en feedparser
            feed = feedparser.parse(url, request_headers=headers)
            if not feed.bozo or intento == max_intentos-1:
                return feed
            time.sleep(1)
        except Exception as e:
            if intento == max_intentos-1:
                logging.error(f"Error feed {medio} tras {max_intentos} intentos: {e}")
            time.sleep(1)
    return None    

def menciona_espana(texto):
    """Detecta si el texto menciona España (versión multilingüe mejorada)"""
    if not texto:
        return False
    texto_lower = texto.lower()
    
    # Buscar keywords exactas
    for keyword in KEYWORDS_ESPANA:
        if keyword.lower() in texto_lower:
            return True
    
    # Patrones adicionales (inglés/español)
    patrones = [
        r'\bspanish\b', r'\bspain\b', r'\besp(a|á)ñol\b', r'\bespaña\b',
        r'\bmadrid\b', r'\bbarcelona\b', r'\bcatalonia\b', r'\bbasque\b',
        r'pedro sánchez', r'\bfeijóo\b', r'\bvox\b', r'\bpsoe\b', r'\bpp\b',
    ]
    
    for patron in patrones:
        if re.search(patron, texto_lower):
            return True
    
    return False

# ========== RECOGER NOTICIAS PARALELO ==========
def recoger_noticias_paralelo(feeds_dict, max_por_feed, max_total, filtrar_espana=False):
    noticias = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_medio = {}
        for medio, url in feeds_dict.items():
            future = executor.submit(obtener_feed_seguro, url, medio)
            future_to_medio[future] = medio
        for future in as_completed(future_to_medio):
            medio = future_to_medio[future]
            feed = future.result()
            if not feed:
                continue
            
            try:
                entradas = sorted(feed.entries, key=extraer_fecha_noticia, reverse=True)[:max_por_feed]
                for entry in entradas:
                    if "title" in entry and "link" in entry:
                        titulo = limpiar_html(entry.title)
                        resumen = limpiar_html(entry.summary) if hasattr(entry, "summary") else ""
                        
                        if filtrar_espana:
                            texto_completo = titulo + " " + resumen
                            if medio in MEDIOS_SOLO_LOCALES and not menciona_espana(texto_completo):
                                continue
                            if not menciona_espana(texto_completo):
                                continue
                        
                        noticias.append({
                            "medio": medio,
                            "titulo": titulo,
                            "resumen": resumen,
                            "link": entry.link.strip(),
                            "fecha": extraer_fecha_noticia(entry)
                        })
            except Exception as e:
                logging.error(f"Error procesando entradas de {medio}: {e}")
    
    noticias.sort(key=lambda x: x["fecha"], reverse=True)
    return noticias[:max_total]

# ========== CALCULAR EMBEDDINGS CON CACHÉ ==========
def calcular_embeddings(noticias, embedding_cache):
    titulos = [n["titulo"] for n in noticias]
    embeddings_list = []
    titulos_procesar = []
    indices_procesar = []
    
    for i, titulo in enumerate(titulos):
        key = get_embedding_cache_key(titulo)
        if key in embedding_cache:
            embeddings_list.append(np.array(embedding_cache[key]))
        else:
            titulos_procesar.append(titulo)
            indices_procesar.append(i)
    
    if titulos_procesar:
        nuevos = modelo.encode(titulos_procesar, batch_size=32, show_progress_bar=False)
        
        for idx, emb in zip(indices_procesar, nuevos):
            key = get_embedding_cache_key(titulos[idx])
            embedding_cache[key] = emb.tolist()
        
        emb_completos = [None] * len(titulos)
        j = 0
        for i in range(len(titulos)):
            if i in indices_procesar:
                emb_completos[i] = nuevos[j]
                j += 1
            else:
                key = get_embedding_cache_key(titulos[i])
                emb_completos[i] = np.array(embedding_cache[key])
        
        embeddings = np.array(emb_completos)
    else:
        embeddings = np.array(embeddings_list)
    
    return embeddings

# ========== DEDUPLICACIÓN ==========
def deduplicar_noticias(noticias, embeddings):
    filtradas = []
    emb_filtrados = []
    links_vistos = set()
    
    for i, emb in enumerate(embeddings):
        n = noticias[i]
        if n["link"] in links_vistos:
            continue
        
        if not emb_filtrados:
            filtradas.append(n)
            emb_filtrados.append(emb)
            links_vistos.add(n["link"])
            continue
        
        sims = cosine_similarity([emb], emb_filtrados)[0]
        
        if max(sims) < UMBRAL_DUPLICADO:
            es_duplicado_texto = any(
                son_duplicados_texto(n["titulo"], fn["titulo"])
                for fn in filtradas
            )
            if not es_duplicado_texto:
                filtradas.append(n)
                emb_filtrados.append(emb)
                links_vistos.add(n["link"])
    
    return filtradas, np.array(emb_filtrados)

# ========== CLUSTERING ==========
def clusterizar(embeddings):
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
    
    if not grupos or all(len(g) < 2 for g in grupos):
        logging.info("No hay clusters claros, usando agrupación mínima")
        grupos = []
        usados = set()
        
        for i in range(len(embeddings)):
            if i in usados:
                continue
            grupo = [i]
            for j in range(i+1, len(embeddings)):
                if j in usados:
                    continue
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                if sim > UMBRAL_AGRUPACION_MIN:
                    grupo.append(j)
                    usados.add(j)
            grupos.append(grupo)
            usados.add(i)
    else:
        grupos = [g for g in grupos if len(g) >= 2]
    
    grupos.sort(key=len, reverse=True)
    return grupos

# ========== ANÁLISIS DE SESGO SIMPLIFICADO ==========
def analizar_sesgo(indices, noticias):
    """
    Análisis simplificado: solo progresista vs conservador
    """
    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16, show_progress_bar=False)
    centroide = np.mean(emb, axis=0).reshape(1, -1)
    
    prog = cosine_similarity(centroide, referencias_politicas["progresista"]).mean()
    cons = cosine_similarity(centroide, referencias_politicas["conservador"]).mean()
    
    total = prog + cons
    if total > 0:
        pct_prog = (prog / total) * 100
        pct_cons = (cons / total) * 100
    else:
        pct_prog = 50
        pct_cons = 50
    
    # Texto principal con umbrales ajustados
    diff = abs(pct_prog - pct_cons)
    if diff < 5:
        texto = "⚪ Cobertura muy equilibrada"
    elif pct_prog > pct_cons:
        if diff > 15:
            texto = "🔵 Enfoque marcadamente progresista"
        else:
            texto = "🔵 Enfoque ligeramente progresista"
    else:
        if diff > 15:
            texto = "🟠 Enfoque marcadamente conservador"
        else:
            texto = "🟠 Enfoque ligeramente conservador"
    
    return {
        "texto": texto,
        "pct_prog": round(pct_prog),
        "pct_cons": round(pct_cons)
    }

def titular_prisma(indices, noticias):
    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])
    
    comunes = [p for p, _ in Counter(palabras).most_common(7)]
    blacklist = {"gobierno", "españa", "hoy", "última", "nuevo", "tras", "sobre", "según", "dice", "años", "dice", "afirma", "asegura"}
    comunes = [p for p in comunes if p not in blacklist][:4]
    
    if len(comunes) >= 3:
        tema = f"{comunes[0]}, {comunes[1]} y {comunes[2]}"
    elif len(comunes) == 2:
        tema = f"{comunes[0]} y {comunes[1]}"
    elif comunes:
        tema = comunes[0]
    else:
        tema = "actualidad"
    
    # Versión más corta para móvil
    tema = tema.capitalize()
    if len(tema) > 40:  # Si es muy largo, recortar
        tema = tema[:37] + "..."
    
    prefijos = ["Claves:", "En foco:", "Hoy:", "Tema:", "Portada:", "Relevante:"]  # Prefijos más cortos
    return f"{random.choice(prefijos)} {tema}"

def resumen_prisma(indices, noticias):
    medios = [noticias[i]["medio"] for i in indices]
    titulos = [noticias[i]["titulo"] for i in indices]
    
    angulos = []
    if len(set(medios)) > 3:
        angulos.append("múltiples perspectivas")
    if len(set(medios)) > 5:
        angulos.append("amplia cobertura mediática")
    
    palabras_pos = {"acuerdo", "mejora", "éxito", "avance", "logro", "beneficio", "positivo"}
    palabras_neg = {"crisis", "conflicto", "problema", "preocupación", "riesgo", "amenaza", "grave"}
    
    texto_completo = " ".join(titulos).lower()
    pos = sum(1 for p in palabras_pos if p in texto_completo)
    neg = sum(1 for p in palabras_neg if p in texto_completo)
    
    if pos > neg + 2:
        sentimiento = "tono positivo"
        emoji = "📈"
    elif neg > pos + 2:
        sentimiento = "tono preocupante"
        emoji = "📉"
    else:
        sentimiento = "tono equilibrado"
        emoji = "📊"
    
    return {
        "num_medios": len(set(medios)),
        "sentimiento": sentimiento,
        "angulos": angulos,
        "emoji": emoji
    }

# ========== BÚSQUEDA SEMÁNTICA PARA MODO VIGILANTE ==========
def buscar_noticias_semantico(consulta, noticias, embedding_cache, top_n=50):
    """
    Busca noticias relacionadas semánticamente con la consulta.
    """
    if not consulta or not noticias:
        return []
    
    # Crear embedding de la consulta
    key_consulta = get_embedding_cache_key(consulta)
    if key_consulta in embedding_cache:
        emb_consulta = np.array(embedding_cache[key_consulta])
    else:
        emb_consulta = modelo.encode([consulta])[0]
        embedding_cache[key_consulta] = emb_consulta.tolist()
    
    # Obtener embeddings de las noticias
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
    
    # Calcular similitudes
    embeddings_noticias = np.array(embeddings_noticias)
    similitudes = cosine_similarity([emb_consulta], embeddings_noticias)[0]
    
    # Ordenar y devolver top resultados
    resultados = []
    for idx, sim in zip(indices_validos, similitudes):
        if sim > 0.5:  # Umbral de relevancia
            resultados.append({
                "noticia": noticias[idx],
                "similitud": sim
            })
    
    resultados.sort(key=lambda x: x["similitud"], reverse=True)
    return [r["noticia"] for r in resultados[:top_n]]

# ========== GENERAR INDEX.HTML ==========
def generar_index_html(noticias, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos):
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Prisma | Comparador IA de noticias</title>
    <meta name="description" content="Analizamos automáticamente {medios_unicos} medios para detectar enfoques editoriales, sesgos y tendencias en tiempo real.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://prismanews.github.io/prisma/">
    <meta property="og:title" content="Prisma noticias IA">
    <meta property="og:description" content="Comparador inteligente de noticias con IA">
    <meta property="og:image" content="Logo.PNG">
    <meta property="og:url" content="https://prismanews.github.io/prisma/">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=yes">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-9WZC3GQSN8"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', 'G-9WZC3GQSN8');
    </script>
    
    <link rel="stylesheet" href="prisma.css?v={cachebuster}">
    <style>
        .buscador-rapido {{
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 20px 24px;
            margin-bottom: 28px;
            border: 1px solid var(--border-light);
            box-shadow: var(--shadow-sm);
        }}
        .buscador-rapido form {{
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .buscador-rapido input {{
            flex: 1;
            min-width: 250px;
            padding: 10px 18px;
            border-radius: 40px;
            border: 1px solid var(--border-medium);
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
        }}
        .buscador-rapido button {{
            padding: 10px 24px;
            border-radius: 40px;
            background: var(--primary);
            color: white;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: var(--transition);
            font-size: 14px;
        }}
        .buscador-rapido button:hover {{
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: var(--shadow-primary);
        }}
        .ver-mas {{
            margin-top: 12px;
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            background: var(--bg-secondary);
        }}
        .ver-mas summary {{
            padding: 10px 14px;
            cursor: pointer;
            color: var(--primary);
            font-weight: 600;
            font-size: 13px;
            list-style: none;
            position: relative;
        }}
        .ver-mas summary::after {{
            content: "▼";
            font-size: 10px;
            position: absolute;
            right: 14px;
            transition: transform 0.2s;
        }}
        .ver-mas[open] summary::after {{
            transform: rotate(180deg);
        }}
        .ver-mas .noticias-extra {{
            padding: 0 14px 14px 14px;
            border-top: 1px solid var(--border-light);
        }}
    </style>
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma" onerror="this.style.display='none'">
                <a href="index.html" class="logo-link">PRISMA</a>
            </div>
            <div class="header-text">
                <p class="claim">EL COMPARADOR DE MEDIOS CON IA</p>
                <p class="explicacion">Analizamos automáticamente <strong>{medios_unicos} medios</strong> para detectar <strong>enfoques editoriales, sesgos y tendencias</strong> en tiempo real.<br><span class="highlight">Entiende cómo te cuentan la actualidad.</span></p>
                <div class="stats">📰 {medios_unicos} medios · <time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time></div>
            </div>
            <nav class="nav">
                <a href="index.html" class="active">Inicio</a>
                <a href="sobre.html">Sobre Prisma</a>
                <a href="espana.html">🌍 España en el mundo</a>
                <a href="mailto:ovalero@gmail.com">Contacto</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <!-- NUEVO: Buscador del Modo Vigilante -->
        <div class="buscador-rapido">
            <form action="vigilante.html" method="get">
                <input type="text" name="q" placeholder="👁️ Modo Vigilante: busca un tema (ej. vivienda, inmigración, sanidad...)" autocomplete="off">
                <button type="submit">🔍 Vigilar</button>
            </form>
            <p style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px;">
                Análisis semántico en tiempo real de cómo los medios abordan el tema
            </p>
        </div>

        <!-- Filtro interactivo -->
        <div class="filtro-container">
            <label for="filtro-medio">📋 Filtrar por medio:</label>
            <select id="filtro-medio">
                <option value="todos">Todos los medios</option>
'''
    
    # Añadir opciones de medios
    medios_lista = sorted(set(n["medio"] for n in noticias))
    for medio in medios_lista:
        html += f'                <option value="{medio}">{medio}</option>\n'
    
    html += '''            </select>
        </div>
'''
    
    # Añadir grupos
    for i, grupo in enumerate(grupos[:15]):
        sesgo = analizar_sesgo(grupo, noticias)
        resumen = resumen_prisma(grupo, noticias)
        titular = titular_prisma(grupo, noticias)
        
        medios_grupo = list(set(noticias[i]["medio"] for i in grupo))
        medios_str = ",".join(medios_grupo)
        
        html += f'''
        <div class="card" data-medios="{medios_str}">
            <h2>{titular}</h2>
            <div class="resumen">
                {resumen['emoji']} <strong>Resumen IA:</strong>
                {resumen['num_medios']} medios · {resumen['sentimiento']} · 
                {', '.join(resumen['angulos']) if resumen['angulos'] else 'enfoque directo'}
            </div>
            <div class="sesgo-simple">
                <div class="sesgo-header">
                    <span class="sesgo-texto">{sesgo['texto']}</span>
                    <span class="sesgo-info" title="Basado en análisis semántico de los titulares">ⓘ</span>
                </div>
                <div class="sesgo-barra">
                    <div class="barra-progresista" style="width: {sesgo['pct_prog']}%;"></div>
                    <div class="barra-conservadora" style="width: {sesgo['pct_cons']}%;"></div>
                </div>
                <div class="sesgo-etiquetas">
                    <span>Progresista {sesgo['pct_prog']}%</span>
                    <span>Conservador {sesgo['pct_cons']}%</span>
                </div>
            </div>
'''
        
        # Mostrar solo 3 noticias inicialmente en móvil (con "ver más")
        for idx in grupo[:3]:
            n = noticias[idx]
            html += f'''
            <p><strong>{n['medio']}:</strong> <a href="{n['link']}" target="_blank" rel="noopener">{n['titulo']}</a></p>
'''
        
        if len(grupo) > 3:
            resto = len(grupo) - 3
            html += f'''
            <details class="ver-mas">
                <summary>+ {resto} noticias más</summary>
                <div class="noticias-extra">
'''
            for idx in grupo[3:]:
                n = noticias[idx]
                html += f'''
                    <p><strong>{n['medio']}:</strong> <a href="{n['link']}" target="_blank" rel="noopener">{n['titulo']}</a></p>
'''
            html += '''
                </div>
            </details>
'''
        
        html += '''        </div>
'''
    
    # Call to Action
    html += '''
        <div class="cta-section">
            <h3>¿Te gusta Prisma?</h3>
            <p>Ayúdanos a crecer y entender mejor los medios de comunicación</p>
            <div class="cta-buttons">
                <button onclick="compartirPrisma()" class="cta-btn primary">📢 Compartir</button>
                <a href="sobre.html" class="cta-btn secondary">🔍 Cómo funciona</a>
                <a href="https://github.com/tu-usuario/prisma" target="_blank" class="cta-btn github">⭐ Seguir proyecto</a>
            </div>
        </div>
    </div>

    <!-- Botones flotantes compartir -->
    <div class="compartir-flotante">
        <a href="https://twitter.com/intent/tweet?text=📊%20Descubre%20cómo%20la%20IA%20analiza%20el%20sesgo%20de%20los%20medios%20en%20Prisma&url=https://prismanews.github.io/prisma/" target="_blank" class="share-btn twitter">🐦</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://prismanews.github.io/prisma/" target="_blank" class="share-btn facebook">📘</a>
        <a href="https://wa.me/?text=📊%20Descubre%20cómo%20la%20IA%20analiza%20el%20sesgo%20de%20los%20medios%20en%20Prisma%20https://prismanews.github.io/prisma/" target="_blank" class="share-btn whatsapp">📱</a>
        <a href="https://t.me/share/url?url=https://prismanews.github.io/prisma/&text=📊%20Descubre%20cómo%20la%20IA%20analiza%20el%20sesgo%20de%20los%20medios%20en%20Prisma" target="_blank" class="share-btn telegram">📨</a>
        <button onclick="copiarPortapapeles('https://prismanews.github.io/prisma/')" class="share-btn copy">📋</button>
    </div>

    <script>
        function copiarPortapapeles(texto) {
            navigator.clipboard.writeText(texto).then(() => {
                let toast = document.createElement('div');
                toast.textContent = '✅ Enlace copiado';
                toast.style.cssText = `
                    position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
                    background: rgba(0,0,0,0.9); color: white; padding: 12px 24px;
                    border-radius: 50px; font-size: 14px; z-index: 10000;
                    animation: slideUp 0.3s ease;
                `;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            });
        }

        function compartirPrisma() {
            if (navigator.share) {
                navigator.share({
                    title: 'Prisma | Comparador IA de noticias',
                    text: 'Analizamos el sesgo de los medios con IA',
                    url: 'https://prismanews.github.io/prisma/'
                });
            } else {
                copiarPortapapeles('https://prismanews.github.io/prisma/');
            }
        }

        // Filtro por medio
        document.getElementById('filtro-medio').addEventListener('change', function(e) {
            const medio = e.target.value;
            document.querySelectorAll('.card').forEach(card => {
                if (medio === 'todos') {
                    card.style.display = 'block';
                } else {
                    const mediosCard = card.dataset.medios.split(',');
                    if (mediosCard.includes(medio)) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        });

        // Animación de entrada
        document.querySelectorAll('.card').forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    </script>
</body>
</html>
'''
    return html

# ========== GENERAR SOBRE.HTML ==========
def generar_sobre_html(fecha_legible, fecha_iso, cachebuster, medios_unicos):
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Sobre Prisma | Comparador IA de noticias</title>
    <meta name="description" content="Prisma es un comparador inteligente de noticias que analiza titulares de distintos medios para ofrecer contexto, detectar tendencias y reducir ruido informativo.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://prismanews.github.io/prisma/sobre.html">
    <meta property="og:title" content="Sobre Prisma | IA para entender los medios">
    <meta property="og:description" content="Comparador de noticias con IA que analiza distintos medios para entender mejor la actualidad.">
    <meta property="og:image" content="Logo.PNG">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=yes">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-9WZC3GQSN8"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', 'G-9WZC3GQSN8');
    </script>
    
    <link rel="stylesheet" href="prisma.css?v={cachebuster}">
    <style>
        .about-container {{ max-width: 900px; margin: 0 auto; }}
        .about-card {{
            background: var(--bg-primary);
            border-radius: var(--radius-xl);
            padding: 48px;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border-light);
            position: relative;
            overflow: hidden;
        }}
        .about-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
            background-size: 200% 100%;
            animation: gradientMove 8s ease infinite;
        }}
        @keyframes gradientMove {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        .hero-about {{
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 32px;
            border-bottom: 2px dashed var(--border-light);
        }}
        .hero-about h1 {{
            font-size: 2.8rem;
            margin-bottom: 20px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .hero-about p {{
            font-size: 1.3rem;
            color: var(--text-secondary);
            max-width: 700px;
            margin: 0 auto;
            font-weight: 300;
        }}
        .about-section {{
            margin-bottom: 40px;
        }}
        .about-section h2 {{
            font-size: 2rem;
            margin-bottom: 20px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .about-section h2::before {{
            content: '◆';
            color: var(--accent);
            font-size: 1.8rem;
            opacity: 0.7;
        }}
        .about-section p {{
            font-size: 1.1rem;
            line-height: 1.8;
            color: var(--text-secondary);
            margin-bottom: 20px;
        }}
        .about-highlight {{
            background: linear-gradient(135deg, var(--primary-soft), var(--accent-soft));
            padding: 24px 32px;
            border-radius: var(--radius-lg);
            margin: 32px 0;
            border-left: 4px solid var(--primary);
            font-style: italic;
        }}
        .contacto-box {{
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            padding: 32px;
            text-align: center;
            border: 1px solid var(--border-light);
            margin: 40px 0 20px;
        }}
        .contacto-box a {{
            display: inline-block;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
            text-decoration: none;
            padding: 12px 32px;
            border-radius: 50px;
            background: var(--bg-primary);
            border: 2px solid var(--primary);
            transition: var(--transition);
        }}
        .contacto-box a:hover {{
            background: var(--primary);
            color: white;
            transform: translateY(-2px);
        }}
        .firma {{
            text-align: center;
            margin-top: 48px;
            padding-top: 32px;
            border-top: 2px dashed var(--border-light);
            font-size: 1.2rem;
            color: var(--text-tertiary);
            font-style: italic;
        }}
    </style>
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma" onerror="this.style.display='none'">
                <a href="index.html" class="logo-link">PRISMA</a>
            </div>
            <div class="header-text">
                <p class="claim">EL COMPARADOR DE MEDIOS CON IA</p>
                <p class="explicacion">Analizamos automáticamente <strong>{medios_unicos} medios</strong> para detectar <strong>enfoques editoriales, sesgos y tendencias</strong> en tiempo real.<br><span class="highlight">Entiende cómo te cuentan la actualidad.</span></p>
                <div class="stats">📰 {medios_unicos} medios · <time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time></div>
            </div>
            <nav class="nav">
                <a href="index.html">Inicio</a>
                <a href="sobre.html" class="active">Sobre Prisma</a>
                <a href="espana.html">🌍 España en el mundo</a>
                <a href="mailto:ovalero@gmail.com">Contacto</a>
            </nav>
        </div>
    </header>

    <div class="container about-container">
        <div class="about-card">
            <div class="hero-about">
                <h1>IA para entender mejor las noticias</h1>
                <p>Prisma compara titulares de múltiples medios para detectar tendencias, enfoques y temas dominantes. Más contexto. Menos ruido.</p>
            </div>
            
            <div class="about-section">
                <h2>Qué es Prisma</h2>
                <p>Prisma es un proyecto independiente que utiliza inteligencia artificial para analizar cómo distintos medios cuentan la actualidad. No genera noticias ni opinión: solo agrupa titulares existentes y aplica análisis semántico para facilitar una visión más amplia.</p>
                <div class="about-highlight">
                    <p>"Si varios medios hablan de lo mismo, compararlos ayuda a entender mejor qué está ocurriendo en el mundo."</p>
                </div>
            </div>
            
            <div class="about-section">
                <h2>Por qué nace</h2>
                <p>Como lector habitual de prensa y profesional técnico, me interesaba explorar cómo la IA puede reducir el ruido informativo, evitar burbujas mediáticas y ofrecer una perspectiva más completa de la actualidad.</p>
                <p>Es un experimento abierto: sin ánimo comercial ni ideológico. Solo curiosidad, aprendizaje y ganas de crear algo útil.</p>
            </div>
            
            <div class="about-section">
                <h2>Estado del proyecto</h2>
                <p>Prisma está en evolución constante. Se irán incorporando nuevas fuentes, mejor análisis semántico y mejoras visuales. Este es solo el comienzo.</p>
            </div>
            
            <div class="contacto-box">
                <p>📩 <strong>Contacto directo</strong></p>
                <a href="mailto:ovalero@gmail.com">ovalero@gmail.com</a>
            </div>
            
            <p class="firma">Proyecto personal creado con curiosidad, IA y muchas ganas 🙂</p>
        </div>
    </div>

    <!-- Botones flotantes -->
    <div class="compartir-flotante">
        <a href="https://twitter.com/intent/tweet?text=📊%20Descubre%20Prisma%2C%20el%20comparador%20de%20medios%20con%20IA&url=https://prismanews.github.io/prisma/sobre.html" target="_blank" class="share-btn twitter">🐦</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://prismanews.github.io/prisma/sobre.html" target="_blank" class="share-btn facebook">📘</a>
        <button onclick="copiarPortapapeles('https://prismanews.github.io/prisma/sobre.html')" class="share-btn copy">📋</button>
    </div>

    <script>
        function copiarPortapapeles(texto) {{
            navigator.clipboard.writeText(texto).then(() => {{
                let toast = document.createElement('div');
                toast.textContent = '✅ Enlace copiado';
                toast.style.cssText = `
                    position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
                    background: rgba(0,0,0,0.9); color: white; padding: 12px 24px;
                    border-radius: 50px; font-size: 14px; z-index: 10000;
                `;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            }});
        }}
    </script>
</body>
</html>
'''
    return html
    
# ========== GENERAR ESPANA.HTML ==========
def generar_espana_html(noticias_espana, fecha_legible, fecha_iso, cachebuster, medios_unicos):
    
    if not noticias_espana:
        noticias_html = "<p class='sin-noticias'>🌍 No hay noticias sobre España en este momento. Pronto se actualizará.</p>"
    else:
        noticias_html = ""
        for n in noticias_espana[:40]:
            fecha_str = ""
            if "fecha" in n:
                fecha = datetime.fromtimestamp(n["fecha"])
                hoy = datetime.now()
                if fecha.date() == hoy.date():
                    diff_horas = max(1, int((hoy - fecha).seconds / 3600))
                    fecha_str = f"<span class='noticia-fecha'>hace {diff_horas}h</span>"
                elif (hoy - fecha).days == 1:
                    fecha_str = "<span class='noticia-fecha'>ayer</span>"
                else:
                    fecha_str = f"<span class='noticia-fecha'>{fecha.strftime('%d/%m')}</span>"
            
            noticias_html += f"""
            <div class="noticia-item" data-medio="{n['medio']}">
                <span class="noticia-medio">{n['medio']}</span>
                <span class="noticia-titulo"><a href="{n['link']}" target="_blank" rel="noopener">{n['titulo']}</a></span>
                {fecha_str}
            </div>
            """
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>España en el mundo | Visión internacional · Prisma</title>
    <meta name="description" content="Lo que la prensa internacional publica sobre España. Análisis en tiempo real de medios de todo el mundo.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://prismanews.github.io/prisma/espana.html">
    <meta property="og:title" content="🌍 España en el mundo | Prisma">
    <meta property="og:description" content="Sigue la actualidad de España vista por la prensa internacional.">
    <meta property="og:image" content="Logo.PNG">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=yes">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-9WZC3GQSN8"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', 'G-9WZC3GQSN8');
    </script>
    
    <link rel="stylesheet" href="prisma.css?v={cachebuster}">
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma" onerror="this.style.display='none'">
                <a href="index.html" class="logo-link">PRISMA</a>
            </div>
            <div class="header-text">
                <p class="claim">EL COMPARADOR DE MEDIOS CON IA</p>
                <p class="explicacion">Analizamos automáticamente <strong>{medios_unicos} medios</strong> para detectar <strong>enfoques editoriales, sesgos y tendencias</strong> en tiempo real.<br><span class="highlight">Entiende cómo te cuentan la actualidad.</span></p>
                <div class="stats">📰 {medios_unicos} medios · <time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time></div>
            </div>
            <nav class="nav">
                <a href="index.html">Inicio</a>
                <a href="sobre.html">Sobre Prisma</a>
                <a href="espana.html" class="active">🌍 España en el mundo</a>
                <a href="mailto:ovalero@gmail.com">Contacto</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <div class="internacional-header">
            <h2><span>🌍</span> España en el mundo</h2>
            <p>Lo que la prensa internacional publica sobre España.</p>
            <div class="stats" style="margin-top: 16px; justify-content: flex-start;">
                <span>📰 {len(noticias_espana)} noticias encontradas</span>
            </div>
        </div>
        
        <div class="filtro-medios">
            <label for="filtro-medio">📋 Filtrar por medio:</label>
            <select id="filtro-medio">
                <option value="todos">🌐 Todos los medios</option>
            </select>
        </div>
        
        <div class="lista-noticias" id="lista-noticias">
            {noticias_html}
        </div>
    </div>
    
    <!-- Botones flotantes -->
    <div class="compartir-flotante">
        <a href="https://twitter.com/intent/tweet?text=🌍%20España%20en%20el%20mundo%20según%20Prisma&url=https://prismanews.github.io/prisma/espana.html" target="_blank" class="share-btn twitter">🐦</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://prismanews.github.io/prisma/espana.html" target="_blank" class="share-btn facebook">📘</a>
        <a href="https://wa.me/?text=🌍%20España%20en%20el%20mundo%20según%20Prisma%20https://prismanews.github.io/prisma/espana.html" target="_blank" class="share-btn whatsapp">📱</a>
        <button onclick="copiarPortapapeles('https://prismanews.github.io/prisma/espana.html')" class="share-btn copy">📋</button>
    </div>

    <script>
        function copiarPortapapeles(texto) {{
            navigator.clipboard.writeText(texto).then(() => {{
                let toast = document.createElement('div');
                toast.textContent = '✅ Enlace copiado';
                toast.style.cssText = `
                    position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
                    background: rgba(0,0,0,0.9); color: white; padding: 12px 24px;
                    border-radius: 50px; font-size: 14px; z-index: 10000;
                `;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            }});
        }}

        const medios = new Set();
        document.querySelectorAll('.noticia-item').forEach(item => {{
            medios.add(item.dataset.medio);
        }});
        
        const select = document.getElementById('filtro-medio');
        [...medios].sort().forEach(medio => {{
            const option = document.createElement('option');
            option.value = medio;
            option.textContent = medio;
            select.appendChild(option);
        }});
        
        select.addEventListener('change', function(e) {{
            const medio = e.target.value;
            document.querySelectorAll('.noticia-item').forEach(item => {{
                if (medio === 'todos' || item.dataset.medio === medio) {{
                    item.style.display = 'flex';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }});
    </script>
</body>
</html>
'''
    return html

# ========== GENERAR VIGILANTE.HTML (con búsqueda real desde JSON) ==========
def generar_vigilante_html(consulta, noticias_filtradas, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos):
    consulta_url = urllib.parse.quote(consulta)
    
    # Convertir TODAS las noticias a JSON para JavaScript (no solo las filtradas)
    with open("noticias_cache.json", "r", encoding="utf-8") as f:
        todas_noticias = json.load(f)
    
    noticias_json = json.dumps(todas_noticias, ensure_ascii=False)
    
    # Generar HTML de resultados (inicialmente vacío, lo llenará JS)
    resultados_html = '''
        <div id="resultados-container"></div>
    '''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Prisma Vigilante | Comparador IA</title>
    <meta name="description" content="Busca cualquier tema y descubre cómo lo tratan los medios.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://prismanews.github.io/prisma/vigilante.html">
    <meta property="og:title" content="Modo Vigilante | Prisma">
    <meta property="og:description" content="Busca cualquier tema y analizamos cómo lo cubren los medios.">
    <meta property="og:image" content="Logo.PNG">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=yes">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-9WZC3GQSN8"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', 'G-9WZC3GQSN8');
    </script>
    
    <link rel="stylesheet" href="prisma.css?v={cachebuster}">
    <style>
        .vigilante-header {{
            background: linear-gradient(135deg, #05966920, #04785720);
            border-radius: var(--radius-xl);
            padding: 32px;
            margin-bottom: 32px;
            border: 1px solid var(--border-light);
        }}
        .vigilante-header h2 {{
            font-size: 2.2rem;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .search-box {{
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 24px;
            margin-bottom: 32px;
            border: 1px solid var(--border-light);
            box-shadow: var(--shadow-md);
        }}
        .search-form {{
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .search-form input {{
            flex: 1;
            min-width: 250px;
            padding: 12px 20px;
            border-radius: 40px;
            border: 1px solid var(--border-medium);
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 16px;
        }}
        .search-form button {{
            padding: 12px 32px;
            border-radius: 40px;
            background: var(--primary);
            color: white;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: var(--transition);
            font-size: 16px;
        }}
        .search-form button:hover {{
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: var(--shadow-primary);
        }}
        .stats-vigilante {{
            display: flex;
            gap: 24px;
            margin-top: 16px;
            color: var(--text-tertiary);
            font-size: 14px;
            flex-wrap: wrap;
        }}
        .card {{
            background: var(--bg-primary);
            border-radius: var(--radius-xl);
            padding: 28px;
            margin-bottom: 28px;
            border: 1px solid var(--border-light);
            transition: var(--transition-slow);
            position: relative;
            overflow: hidden;
            animation: fadeIn 0.5s ease-out;
            box-shadow: var(--shadow-sm);
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg), var(--shadow-primary);
            border-color: transparent;
        }}
        .card h2 {{
            font-size: 24px;
            margin: 0 0 16px;
            color: var(--text-primary);
            line-height: 1.3;
        }}
        .resumen {{
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            padding: 14px 20px;
            margin: 16px 0;
            font-size: 14px;
            color: var(--text-secondary);
            border-left: 4px solid var(--primary);
            line-height: 1.6;
        }}
        .sesgo-simple {{
            background: var(--accent-soft);
            border-radius: var(--radius-lg);
            padding: 16px;
            margin: 16px 0;
            border: 1px solid var(--accent-light);
        }}
        .sesgo-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }}
        .sesgo-texto {{
            font-weight: 600;
            color: var(--text-primary);
            font-size: 14px;
        }}
        .sesgo-barra {{
            display: flex;
            height: 24px;
            border-radius: 12px;
            overflow: hidden;
            margin: 10px 0 6px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
        }}
        .barra-progresista {{
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
            height: 100%;
            transition: width 0.3s ease;
        }}
        .barra-conservadora {{
            background: linear-gradient(90deg, #f97316, #fb923c);
            height: 100%;
            transition: width 0.3s ease;
        }}
        .sesgo-etiquetas {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .ver-mas {{
            margin-top: 12px;
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            background: var(--bg-secondary);
        }}
        .ver-mas summary {{
            padding: 10px 14px;
            cursor: pointer;
            color: var(--primary);
            font-weight: 600;
            font-size: 13px;
            list-style: none;
            position: relative;
        }}
        .ver-mas summary::after {{
            content: "▼";
            font-size: 10px;
            position: absolute;
            right: 14px;
            transition: transform 0.2s;
        }}
        .ver-mas[open] summary::after {{
            transform: rotate(180deg);
        }}
        .ver-mas .noticias-extra {{
            padding: 0 14px 14px 14px;
            border-top: 1px solid var(--border-light);
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(15px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    </style>
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma" onerror="this.style.display='none'">
                <a href="index.html" class="logo-link">PRISMA</a>
            </div>
            <div class="header-text">
                <p class="claim">EL COMPARADOR DE MEDIOS CON IA</p>
                <p class="explicacion">Analizamos automáticamente <strong>{medios_unicos} medios</strong> para detectar enfoques editoriales, sesgos y tendencias en tiempo real.<br><span class="highlight">Entiende cómo te cuentan la actualidad.</span></p>
                <div class="stats">📰 {medios_unicos} medios · <time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time></div>
            </div>
            <nav class="nav">
                <a href="index.html">Inicio</a>
                <a href="sobre.html">Sobre Prisma</a>
                <a href="espana.html">🌍 España en el mundo</a>
                <a href="mailto:ovalero@gmail.com">Contacto</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <div class="vigilante-header">
            <h2><span>👁️</span> Modo Vigilante: <span id="consulta-titulo"></span></h2>
            <p>Estamos vigilando cómo los medios hablan de <strong>"<span id="consulta-descripcion"></span>"</strong>. Aquí tienes las noticias relacionadas y su análisis.</p>
        </div>

        <!-- Buscador -->
        <div class="search-box">
            <form class="search-form" id="search-form" onsubmit="return buscar(event)">
                <input type="text" id="search-input" placeholder="Ej: vivienda, inmigración, sanidad..." autofocus>
                <button type="submit">🔍 Vigilar</button>
            </form>
            <div class="stats-vigilante" id="stats">
                <span>📊 <span id="num-noticias">0</span> noticias encontradas</span>
                <span>📰 <span id="num-medios">0</span> medios diferentes</span>
                <span>⚡ <span id="num-grupos">0</span> enfoques detectados</span>
            </div>
        </div>

        <!-- Resultados -->
        <div id="resultados-container" class="loading">
            Cargando resultados...
        </div>
        
    </div>

    <!-- Botones flotantes -->
    <div class="compartir-flotante">
        <a href="#" id="twitter-share" target="_blank" class="share-btn twitter">🐦</a>
        <button onclick="copiarPortapapeles()" class="share-btn copy">📋</button>
    </div>

    <script>
        // TODAS las noticias cargadas desde el JSON de Python
        const todasNoticias = {noticias_json};
        
        // Función para obtener parámetro de URL
        function getQueryParam(param) {{
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get(param) || "";
        }}
        
        // Función para buscar
        function buscar(event) {{
            if (event) event.preventDefault();
            const consulta = document.getElementById('search-input').value;
            if (consulta) {{
                window.location.href = `vigilante.html?q=${{encodeURIComponent(consulta)}}`;
            }}
            return false;
        }}
        
        // Función para filtrar noticias por consulta (búsqueda simple en títulos)
        function filtrarNoticias(consulta) {{
            if (!consulta) return [];
            
            const consultaLower = consulta.toLowerCase();
            return todasNoticias.filter(noticia => 
                noticia.titulo.toLowerCase().includes(consultaLower)
            );
        }}
        
        // Función para agrupar noticias (versión simplificada)
        function agruparNoticias(noticias) {{
            // Por ahora, devolvemos todas como un solo grupo
            // En una versión futura, podrías implementar clustering en JS
            return [noticias];
        }}

        // Función para analizar enfoques por sesgo
        function analizarEnfoques(noticias) {
            // Palabras clave para detectar enfoques
            const palabrasProgresista = [
                "derecho", "vivienda", "pública", "social", "igualdad", 
                "LGTBI", "feminismo", "refugiados", "climático", "públicas"
            ];
    
            const palabrasConservador = [
                "seguridad", "orden", "fronteras", "unidad", "nación",
                "impuestos", "mercado", "familia", "tradicional", "autoridad"
            ];

            let progresista = 0;
            let conservador = 0;
            let neutro = 0;
    
            noticias.forEach(noticia => {
                const titulo = noticia.titulo.toLowerCase();
                let esProgresista = palabrasProgresista.some(p => titulo.includes(p));
                let esConservador = palabrasConservador.some(p => titulo.includes(p));
        
                if (esProgresista && !esConservador) progresista++;
                else if (esConservador && !esProgresista) conservador++;
                else neutro++;
            });
    
            return { progresista, conservador, neutro };        
        }
        
        // Función para mostrar resultados
        function mostrarResultados(consulta) {{
            const noticiasFiltradas = filtrarNoticias(consulta);
            const grupos = agruparNoticias(noticiasFiltradas);
            // Mostrar estadísticas de enfoque
            const enfoques = analizarEnfoques(noticiasFiltradas);

            // Crear un mini-resumen de enfoques
            const enfoquesHTML = `
                <div class="enfoques-mini">
                    <h3>📊 Enfoques detectados</h3>
                    <div class="enfoques-barras">
                        <div class="enfoque-item">
                            <span class="enfoque-label">Progresista</span>
                            <div class="barra-container">
                                <div class="barra barra-progresista" style="width: ${(enfoques.progresista/noticiasFiltradas.length*100).toFixed(0)}%"></div>
                            </div>
                            <span class="enfoque-numero">${enfoques.progresista}</span>
                        </div>
                        <div class="enfoque-item">
                            <span class="enfoque-label">Conservador</span>
                            <div class="barra-container">
                                <div class="barra barra-conservadora" style="width: ${(enfoques.conservador/noticiasFiltradas.length*100).toFixed(0)}%"></div>
                            </div>
                            <span class="enfoque-numero">${enfoques.conservador}</span>
                        </div>
                        <div class="enfoque-item">
                            <span class="enfoque-label">Neutro</span>
                            <div class="barra-container">
                                <div class="barra barra-neutra" style="width: ${(enfoques.neutro/noticiasFiltradas.length*100).toFixed(0)}%"></div>
                            </div>
                            <span class="enfoque-numero">${enfoques.neutro}</span>
                        </div>
                    </div>
                </div>
`            ;

            // Insertar antes de los resultados
            container.insertAdjacentHTML('beforebegin', enfoquesHTML);
            
            // Actualizar títulos
            document.getElementById('consulta-titulo').textContent = consulta || "sin consulta";
            document.getElementById('consulta-descripcion').textContent = consulta || "sin consulta";
            document.getElementById('search-input').value = consulta;
            
            // Actualizar estadísticas
            document.getElementById('num-noticias').textContent = noticiasFiltradas.length;
            document.getElementById('num-medios').textContent = [...new Set(noticiasFiltradas.map(n => n.medio))].length;
            document.getElementById('num-grupos').textContent = grupos.length;
            
            // Actualizar enlace de Twitter
            const twitterBtn = document.getElementById('twitter-share');
            twitterBtn.href = consulta 
                ? `https://twitter.com/intent/tweet?text=👁️%20Estoy%20vigilando%20'${{consulta}}'%20con%20Prisma&url=https://prismanews.github.io/prisma/vigilante.html?q=${{encodeURIComponent(consulta)}}`
                : '#';
            
            // Mostrar resultados
            const container = document.getElementById('resultados-container');
            container.innerHTML = '';
            
            if (noticiasFiltradas.length === 0) {{
                container.innerHTML = `
                    <div class="card" style="text-align: center; padding: 60px;">
                        <h2>😕 No encontramos noticias sobre "${{consulta}}"</h2>
                        <p>Prueba con otras palabras o términos más generales.</p>
                        <p style="margin-top: 20px; font-size: 14px; color: var(--text-tertiary);">
                            La búsqueda es semántica, no solo por palabras exactas. 
                            Intenta con: vivienda, sanidad, inmigración, cambio climático...
                        </p>
                    </div>
                `;
                return;
            }}
            
            // Mostrar cada grupo - AHORA MUESTRA TODAS LAS NOTICIAS
            grupos.forEach(grupo => {{
                let noticiasHTML = '';
                grupo.forEach(noticia => {{
                    noticiasHTML += `
                        <p><strong>${{noticia.medio}}:</strong> <a href="${{noticia.link}}" target="_blank" rel="noopener">${{noticia.titulo}}</a></p>
                    `;
                }});
                
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <h2>Noticias sobre "${{consulta}}"</h2>
                    <div class="resumen">
                        📊 <strong>Resumen IA:</strong>
                        ${{grupo.length}} noticias
                    </div>
                    ${{noticiasHTML}}
                `;
                
                container.appendChild(card);
            }});
        }}
        
        // Copiar enlace
        function copiarPortapapeles() {{
            const consulta = getQueryParam('q');
            const url = consulta 
                ? `https://prismanews.github.io/prisma/vigilante.html?q=${{encodeURIComponent(consulta)}}`
                : 'https://prismanews.github.io/prisma/vigilante.html';
            
            navigator.clipboard.writeText(url).then(() => {{
                let toast = document.createElement('div');
                toast.textContent = '✅ Enlace copiado';
                toast.style.cssText = `
                    position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
                    background: rgba(0,0,0,0.9); color: white; padding: 12px 24px;
                    border-radius: 50px; font-size: 14px; z-index: 10000;
                    animation: slideUp 0.3s ease;
                `;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            }});
        }}
        
        // Inicializar
        document.addEventListener('DOMContentLoaded', () => {{
            const consulta = getQueryParam('q');
            mostrarResultados(consulta);
        }});
    </script>
</body>
</html>
'''
    return html
    
# ========== GENERAR SITEMAP Y ROBOTS ==========
def generar_sitemap():
    fecha_iso = datetime.now().isoformat()
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://prismanews.github.io/prisma/</loc><lastmod>{fecha_iso}</lastmod></url>
    <url><loc>https://prismanews.github.io/prisma/sobre.html</loc><lastmod>{fecha_iso}</lastmod></url>
    <url><loc>https://prismanews.github.io/prisma/espana.html</loc><lastmod>{fecha_iso}</lastmod></url>
    <url><loc>https://prismanews.github.io/prisma/vigilante.html</loc><lastmod>{fecha_iso}</lastmod></url>
</urlset>
'''

def generar_robots():
    return '''User-agent: *
Allow: /
Sitemap: https://prismanews.github.io/prisma/sitemap.xml
'''

# ========== MAIN ==========
if __name__ == "__main__":
    inicio_total = time.time()
    logging.info("🚀 Iniciando generación de Prisma")
    
    embedding_cache = cargar_cache_embeddings() if CACHE_EMBEDDINGS else {}
    
    logging.info("📰 Recogiendo noticias españolas...")
    noticias = recoger_noticias_paralelo(feeds_espanoles, MAX_NOTICIAS_FEED_ES, MAX_NOTICIAS_TOTAL, filtrar_espana=False)
    logging.info(f"✅ {len(noticias)} noticias recogidas")
    
    if not noticias:
        logging.error("❌ No hay noticias. Abortando.")
        exit(1)
    
    logging.info("🧠 Calculando embeddings...")
    embeddings = calcular_embeddings(noticias, embedding_cache)
    
    if CACHE_EMBEDDINGS:
        guardar_cache_embeddings(embedding_cache)
    
    logging.info("🔄 Deduplicando...")
    noticias, embeddings = deduplicar_noticias(noticias, embeddings)
    logging.info(f"✅ {len(noticias)} noticias tras deduplicar")
    
    logging.info("📊 Clusterizando...")
    grupos = clusterizar(embeddings)
    logging.info(f"✅ {len(grupos)} grupos formados")
    
    logging.info("📝 Generando index.html...")
    fecha = datetime.now()
    fecha_legible = fecha.strftime("%d/%m/%Y %H:%M")
    fecha_iso = fecha.isoformat()
    cachebuster = int(fecha.timestamp())
    medios_unicos = len(set(n["medio"] for n in noticias))
    
    html_index = generar_index_html(noticias, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_index)
    
    # ========== MODO VIGILANTE: Guardar caché de noticias ==========
    logging.info("👁️ Preparando modo vigilante...")
    with open("noticias_cache.json", "w", encoding="utf-8") as f:
        json.dump([{
            "titulo": n["titulo"],
            "medio": n["medio"],
            "fecha": n["fecha"],
            "link": n["link"],
            "resumen": n.get("resumen", "")
        } for n in noticias], f, ensure_ascii=False, indent=2)
    logging.info("✅ Caché para modo vigilante guardado")
    
    logging.info("🌍 Recogiendo noticias internacionales...")
    noticias_espana = recoger_noticias_paralelo(
        feeds_internacionales, 
        MAX_NOTICIAS_FEED_INT, 
        MAX_NOTICIAS_INTERNACIONAL,
        filtrar_espana=True
    )
    
    noticias_espana = list({n["link"]: n for n in noticias_espana}.values())
    noticias_espana.sort(key=lambda x: x["fecha"], reverse=True)
    noticias_espana = noticias_espana[:MAX_NOTICIAS_INTERNACIONAL]
    logging.info(f"✅ {len(noticias_espana)} noticias sobre España encontradas")
    
    logging.info("📝 Generando espana.html...")
    html_espana = generar_espana_html(noticias_espana, fecha_legible, fecha_iso, cachebuster, medios_unicos)
    with open("espana.html", "w", encoding="utf-8") as f:
        f.write(html_espana)
    
    logging.info("📝 Generando sobre.html...")
    html_sobre = generar_sobre_html(fecha_legible, fecha_iso, cachebuster, medios_unicos)
    with open("sobre.html", "w", encoding="utf-8") as f:
        f.write(html_sobre)
    
    # ========== GENERAR PÁGINA DE VIGILANTE (búsqueda por defecto) ==========
    logging.info("👁️ Generando página de vigilante (búsqueda vacía)...")
    html_vigilante = generar_vigilante_html("", [], [], fecha_legible, fecha_iso, cachebuster, medios_unicos)
    with open("vigilante.html", "w", encoding="utf-8") as f:
        f.write(html_vigilante)
    
    logging.info("🗺️ Generando sitemap.xml...")
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(generar_sitemap())
    
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(generar_robots())
    
    tiempo_total = time.time() - inicio_total
    logging.info(f"✅ Generación completada en {tiempo_total:.2f} segundos")
