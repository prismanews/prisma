#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRISMA - Generador principal (VERSIÓN SIMPLIFICADA)
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
    blacklist = {"gobierno", "españa", "hoy", "última", "nuevo", "tras", "sobre", "según", "dice", "años"}
    comunes = [p for p in comunes if p not in blacklist][:4]
    
    if len(comunes) >= 3:
        tema = f"{comunes[0]}, {comunes[1]} y {comunes[2]}"
    elif len(comunes) == 2:
        tema = f"{comunes[0]} y {comunes[1]}"
    elif comunes:
        tema = comunes[0]
    else:
        tema = "actualidad"
    
    prefijos = ["Claves informativas:", "En el foco:", "Lo que domina hoy:", "Tema principal:", "En portada:", "Lo más relevante:"]
    return f"{random.choice(prefijos)} {tema.capitalize()}"

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

# ========== GENERAR SOBRE.HTML (CON CABECERA COMPLETA) - VERSIÓN CORREGIDA ==========
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
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
        <a href="https://wa.me/?text=📊%20Descubre%20Prisma%2C%20el%20comparador%20de%20medios%20con%20IA%20https://prismanews.github.io/prisma/sobre.html" target="_blank" class="share-btn whatsapp">📱</a>
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
                    animation: slideUp 0.3s ease;
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
    
# ========== GENERAR ESPANA.HTML (SIN FECHA DUPLICADA) - VERSIÓN CORREGIDA ==========
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
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
