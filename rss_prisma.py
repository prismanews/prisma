#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador del sitio Prisma News con IA, clustering y análisis de sesgo.
Versión mejorada con todas las funcionalidades.
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
import pickle
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import jinja2

# Intento de importar spaCy para NER (fallback a keywords si no)
try:
    import spacy
    nlp_es = spacy.load("es_core_news_md")
    USE_SPACY = True
except:
    USE_SPACY = False
    logging.warning("spaCy no disponible, se usará detección por palabras clave")

# ---------- CONFIGURACIÓN ----------
UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
UMBRAL_AGRUPACION_MIN = 0.5
MAX_NOTICIAS_FEED = 8
MAX_NOTICIAS_TOTAL = 250
MAX_NOTICIAS_INTERNACIONAL = 40
CACHE_EMBEDDINGS = True
CACHE_FILE = "embeddings_cache.pkl"
LOG_FILE = "prisma.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

modelo = SentenceTransformer("all-MiniLM-L6-v2")

# Frases de referencia para sesgo (ampliadas)
referencias_politicas = {
    "progresista": modelo.encode([
        # español
        "derechos sociales igualdad feminismo justicia social diversidad políticas públicas bienestar",
        "progresismo cambio climático políticas sociales regulación inclusión servicios públicos",
        "derechos humanos libertad expresión manifestación protesta social sindicatos",
        "sanidad pública educación universal pensiones justas derechos laborales",
        "acogida refugiados inmigración regularización derechos LGTBI",
        "vivienda pública alquiler asequible okupación ley vivienda",
        "memoria histórica exhumación Franco víctimas guerra civil",

        # inglés
        "social justice equality progressive politics climate action diversity welfare public services",
        "left wing policies regulation social rights inclusion government intervention",
        "human rights free speech protests unions workers rights minimum wage",
        "refugee welcome immigration reform lgbtq rights gender equality",

        # internacional neutro
        "environmental protection social equality human rights public healthcare welfare state",
        "climate change sustainability renewable energy green transition"
    ]),

    "conservador": modelo.encode([
        # español
        "seguridad fronteras defensa tradición economía mercado estabilidad control migratorio",
        "valores tradicionales seguridad nacional impuestos bajos orden liberalismo económico",
        "familia libertad individual propiedad privada mérito esfuerzo autoridad",
        "unidad de españa constitución monarquía fuerzas armadas ley orden",
        "inmigración ilegal devoluciones control fronteras acuerdo con mafias",
        "reforma laboral despido libre bajada impuestos empresas emprendedores",
        "tauromaquia caza tradiciones culturales patrimonio",

        # inglés
        "border security national defense free market traditional values low taxes immigration control",
        "conservative policies economic freedom national identity law and order",
        "family values individual liberty private property merit authority",
        "illegal immigration deportation border wall crime rates",

        # internacional neutro
        "fiscal responsibility strong military traditional culture business friendly policies",
        "economic growth tax cuts deregulation free trade"
    ])
}

# Feeds españoles
feeds_espanoles = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "El Español": "https://www.elespanol.com/rss/",
    "RTVE": "https://www.rtve.es/rss/",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "HuffPost": "https://www.huffingtonpost.es/feeds/index.xml",
    "La Voz de Galicia": "https://www.lavozdegalicia.es/rss/portada.xml",
    "El Correo": "https://www.elcorreo.com/rss/portada.xml",
    "Diario Sur": "https://www.diariosur.es/rss/portada.xml",
    "Levante": "https://www.levante-emv.com/rss/portada.xml",
    "Heraldo": "https://www.heraldo.es/rss/portada/",
    "Diario Vasco": "https://www.diariovasco.com/rss/portada.xml",
    "Información Alicante": "https://www.informacion.es/rss/portada.xml",
    "Expansión": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "Cinco Días": "https://cincodias.elpais.com/seccion/rss/portada/",
    "Infolibre": "https://www.infolibre.es/rss",
    "El Salto": "https://www.elsaltodiario.com/rss",
    "CTXT": "https://ctxt.es/es/feed/",
    "Jacobin ES": "https://jacobin.com/feed",
}

feeds_internacionales = {
    # 🇬🇧 Inglés
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=world",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Guardian": "https://www.theguardian.com/world/rss",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "Financial Times": "https://www.ft.com/world?format=rss",
    # 🇫🇷 Francés
    "Le Monde": "https://www.lemonde.fr/rss/une.xml",
    "France24 FR": "https://www.france24.com/fr/rss",
    "Le Figaro": "https://www.lefigaro.fr/rss/figaro_actualites.xml",
    # 🇩🇪 Alemán
    "Der Spiegel": "https://www.spiegel.de/international/index.rss",
    "Die Welt": "https://www.welt.de/feeds/latest.rss",
    # 🇮🇹 Italiano
    "Corriere": "https://xml2.corriereobjects.it/rss/homepage.xml",
    "La Repubblica": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
    # 🇵🇹 Portugués
    "Publico PT": "https://www.publico.pt/rss",
    "Folha Brasil": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
    # 🇪🇺 Europa general
    "Politico EU": "https://www.politico.eu/feed/",
    "Euronews": "https://www.euronews.com/rss?level=theme&name=news",
    # 🌏 Asia
    "SCMP Hong Kong": "https://www.scmp.com/rss/91/feed",
    "Japan Times": "https://www.japantimes.co.jp/feed/",
    "China Daily": "http://www.chinadaily.com.cn/rss/world_rss.xml",
    # 🌎 América Latina
    "Clarin": "https://www.clarin.com/rss/lo-ultimo/",
    "El Tiempo CO": "https://www.eltiempo.com/rss/colombia.xml",
    "Granma": "http://www.granma.cu/feed",
    "Cubadebate": "http://www.cubadebate.cu/feed/",
    "Prensa Latina": "https://www.prensa-latina.cu/feed/"
}

# Palabras clave para detectar España (usadas si no hay NER)
KEYWORDS_ESPANA = [
    "españa","espana","spain","espagne","spanien","spagna","espanya",
    "spanish","español","spaniard","madrid","barcelona","valencia",
    "catalonia","cataluña","basque","andalucia","galicia",
    "pedro sanchez","feijoo","vox","psoe","pp",
]

# Stopwords mejoradas
STOPWORDS = set([
    "el","la","los","las","un","una","unos","unas",
    "de","del","al","a","en","por","para","con","sin",
    "sobre","entre","hasta","desde","y","o","e","ni","que",
    "como","pero","aunque","porque","ya","también","solo",
    "su","sus","se","lo","le","les","esto","esta",
    "hoy","ayer","mañana","tras","antes","después",
    "dice","según","afirma","asegura","explica",
    "the","a","an","of","to","in","on","for","with",
    "and","or","but","from","by","about","as",
])

# ---------- UTILIDADES ----------
def limpiar_html(texto):
    texto = html.unescape(texto)
    texto = re.sub(r'<.*?>', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return [p for p in palabras if p not in STOPWORDS and len(p) > 3]

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
    """Detecta si el texto menciona España usando NER o keywords"""
    if USE_SPACY:
        doc = nlp_es(texto[:1000])  # limitar longitud
        for ent in doc.ents:
            if ent.label_ == "LOC" and ent.text.lower() in ["españa", "spain", "madrid", "barcelona", "cataluña", "andalucía"]:
                return True
    # fallback a keywords
    texto_lower = texto.lower()
    return any(k.lower() in texto_lower for k in KEYWORDS_ESPANA)

# ---------- CACHÉ DE EMBEDDINGS ----------
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

# ---------- RECOGIDA DE NOTICIAS ----------
def recoger_noticias(feeds_dict, max_por_feed, max_total):
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
                        noticias.append({
                            "medio": medio,
                            "titulo": limpiar_html(entry.title),
                            "link": entry.link.strip(),
                            "fecha": extraer_fecha_noticia(entry)
                        })
            except Exception as e:
                logging.error(f"Error procesando entradas de {medio}: {e}")
    # Ordenar por fecha y limitar
    noticias.sort(key=lambda x: x["fecha"], reverse=True)
    return noticias[:max_total]

# ---------- DEDUPLICACIÓN ----------
def deduplicar_noticias(noticias, embeddings, umbral_duplicado):
    filtradas = []
    emb_filtrados = []
    links_vistos = set()
    for i, emb in enumerate(embeddings):
        n = noticias[i]
        if n["link"] in links_vistos:
            continue
        if not filtradas:
            filtradas.append(n)
            emb_filtrados.append(emb)
            links_vistos.add(n["link"])
            continue
        sims = cosine_similarity([emb], emb_filtrados)[0]
        if max(sims) < umbral_duplicado:
            es_duplicado_texto = any(
                son_duplicados_texto(n["titulo"], fn["titulo"])
                for fn in filtradas
            )
            if not es_duplicado_texto:
                filtradas.append(n)
                emb_filtrados.append(emb)
                links_vistos.add(n["link"])
    return filtradas, np.array(emb_filtrados)

# ---------- CLUSTERING ----------
def clusterizar(embeddings, umbral):
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
        if mejor_score > umbral:
            grupos[mejor_grupo].append(i)
        else:
            grupos.append([i])

    # Filtrar grupos con al menos 2 elementos
    grupos = [g for g in grupos if len(g) >= 2]
    # Si no hay grupos, crear grupos artificiales con similitud mínima
    if not grupos:
        logging.info("No hay clusters claros, agrupando por similitud mínima")
        usados = set()
        for i in range(len(noticias)):
            if i in usados:
                continue
            grupo = [i]
            for j in range(i+1, len(noticias)):
                if j in usados:
                    continue
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                if sim > UMBRAL_AGRUPACION_MIN:
                    grupo.append(j)
                    usados.add(j)
            grupos.append(grupo)
            usados.add(i)
    grupos.sort(key=len, reverse=True)
    return grupos

# ---------- ANÁLISIS DE SESGO ----------
def analizar_sesgo(indices, noticias):
    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16)
    centroide = np.mean(emb, axis=0).reshape(1, -1)

    prog = cosine_similarity(centroide, referencias_politicas["progresista"]).mean()
    cons = cosine_similarity(centroide, referencias_politicas["conservador"]).mean()

    total = prog + cons
    pct_prog = (prog / total) * 100 if total > 0 else 50
    pct_cons = (cons / total) * 100 if total > 0 else 50

    if abs(prog - cons) < 0.015:
        texto = "Cobertura muy equilibrada"
    elif prog > cons:
        texto = "Enfoque ligeramente progresista" if (prog-cons)*100 < 20 else "Enfoque marcadamente progresista"
    else:
        texto = "Enfoque ligeramente conservador" if (cons-prog)*100 < 20 else "Enfoque marcadamente conservador"

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
    blacklist = {"gobierno", "españa", "hoy", "última", "nuevo", "tras", "sobre"}
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

    palabras_pos = {"acuerdo", "mejora", "éxito", "avance", "logro", "beneficio"}
    palabras_neg = {"crisis", "conflicto", "problema", "preocupación", "riesgo", "amenaza"}
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

# ---------- GENERACIÓN HTML CON JINJA2 ----------
def renderizar_index(noticias, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos):
    template_str = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Prisma | Comparador IA de noticias</title>
    <meta name="description" content="Analizamos automáticamente {{ medios_unicos }} medios para detectar enfoques editoriales, sesgos y tendencias en tiempo real.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://prismanews.github.io/prisma/">
    <meta property="og:title" content="Prisma noticias IA">
    <meta property="og:description" content="Comparador inteligente de noticias con IA">
    <meta property="og:image" content="Logo.PNG">
    <meta property="og:url" content="https://prismanews.github.io/prisma/">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="theme-color" content="#2563eb">
    <meta http-equiv="Cache-Control" content="no-cache">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="prisma.css?v={{ cachebuster }}">
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma">
                <a href="index.html" class="logo-link">PRISMA</a>
            </div>
            <div class="header-text">
                <p class="claim">EL COMPARADOR DE MEDIOS CON IA</p>
                <p class="explicacion">Analizamos automáticamente <strong>{{ medios_unicos }} medios</strong> para detectar <strong>enfoques editoriales, sesgos y tendencias</strong> en tiempo real.<br><span class="highlight">Entiende cómo te cuentan la actualidad.</span></p>
                <div class="stats">📰 {{ medios_unicos }} medios · <time datetime="{{ fecha_iso }}">Actualizado: {{ fecha_legible }}</time></div>
            </div>
            <nav class="nav">
                <a href="index.html?v={{ cachebuster }}" class="active">Inicio</a>
                <a href="sobre.html">Sobre Prisma</a>
                <a href="espana.html?v={{ cachebuster }}">España en el mundo</a>
                <a href="mailto:ovalero@gmail.com">Contacto</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <!-- Filtro interactivo -->
        <div class="filtro-container">
            <label for="filtro-medio">Filtrar por medio:</label>
            <select id="filtro-medio">
                <option value="todos">Todos los medios</option>
                {% for medio in medios_lista %}
                <option value="{{ medio }}">{{ medio }}</option>
                {% endfor %}
            </select>
        </div>

        {% for grupo in grupos %}
        <div class="card {% if loop.first %}portada{% endif %}" data-medios="{{ grupo.medios|join(',') }}">
            <h2>{{ grupo.titular }}</h2>
            <div class="resumen">
                {{ grupo.resumen.emoji }} <strong>Resumen IA:</strong>
                {{ grupo.resumen.num_medios }} medios · {{ grupo.resumen.sentimiento }} · 
                {{ grupo.resumen.angulos|join(', ') if grupo.resumen.angulos else 'enfoque directo' }}
            </div>
            <div class="sesgo-card">
                <div class="sesgo-header">
                    <span class="sesgo-texto">{{ grupo.sesgo.texto }}</span>
                    <span class="sesgo-info" title="Basado en análisis semántico de los titulares">ⓘ</span>
                </div>
                <div class="sesgo-barra">
                    <div class="barra-progresista" style="width: {{ grupo.sesgo.pct_prog }}%;"></div>
                    <div class="barra-conservadora" style="width: {{ grupo.sesgo.pct_cons }}%;"></div>
                </div>
                <div class="sesgo-etiquetas">
                    <span>Progresista {{ grupo.sesgo.pct_prog }}%</span>
                    <span>Conservador {{ grupo.sesgo.pct_cons }}%</span>
                </div>
                <p class="sesgo-nota">Análisis automático basado en el lenguaje de los titulares</p>
            </div>
            {% for idx in grupo.indices[:6] %}
            <p><strong>{{ noticias[idx].medio }}:</strong> <a href="{{ noticias[idx].link }}" target="_blank" rel="noopener">{{ noticias[idx].titulo }}</a></p>
            {% endfor %}
        </div>
        {% endfor %}

        <!-- Call to Action -->
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
        <a href="https://twitter.com/intent/tweet?text=📊%20Descubre%20cómo%20la%20IA%20analiza%20el%20sesgo%20de%20los%20medios%20en%20Prisma&url=https://prismanews.github.io/prisma/" target="_blank" class="share-btn twitter" title="Compartir en X">🐦</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://prismanews.github.io/prisma/" target="_blank" class="share-btn facebook" title="Compartir en Facebook">📘</a>
        <a href="https://wa.me/?text=📊%20Descubre%20cómo%20la%20IA%20analiza%20el%20sesgo%20de%20los%20medios%20en%20Prisma%20https://prismanews.github.io/prisma/" target="_blank" class="share-btn whatsapp" title="Compartir en WhatsApp">📱</a>
        <a href="https://t.me/share/url?url=https://prismanews.github.io/prisma/&text=📊%20Descubre%20cómo%20la%20IA%20analiza%20el%20sesgo%20de%20los%20medios%20en%20Prisma" target="_blank" class="share-btn telegram" title="Compartir en Telegram">📨</a>
        <button onclick="copiarPortapapeles('https://prismanews.github.io/prisma/')" class="share-btn copy" title="Copiar enlace">📋</button>
    </div>

    <!-- Scripts -->
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

        // Exit intent mejorado (solo una vez, menos intrusivo)
        let exitShown = false;
        document.addEventListener('mouseleave', (e) => {
            if (e.clientY < 0 && !exitShown && window.innerWidth > 768) {
                exitShown = true;
                setTimeout(() => {
                    if (confirm('👋 ¿Te gusta Prisma? Compártelo con tus amigos')) {
                        compartirPrisma();
                    }
                }, 100);
            }
        });
    </script>
</body>
</html>
"""
    # Preparar datos para la plantilla
    medios_lista = sorted(set(n["medio"] for n in noticias))
    grupos_data = []
    for g in grupos:
        medios_grupo = list(set(noticias[i]["medio"] for i in g))
        sesgo = analizar_sesgo(g, noticias)
        resumen = resumen_prisma(g, noticias)
        grupos_data.append({
            "indices": g,
            "titular": titular_prisma(g, noticias),
            "sesgo": sesgo,
            "resumen": resumen,
            "medios": medios_grupo
        })

    template = jinja2.Template(template_str)
    return template.render(
        noticias=noticias,
        grupos=grupos_data,
        fecha_legible=fecha_legible,
        fecha_iso=fecha_iso,
        cachebuster=cachebuster,
        medios_unicos=medios_unicos,
        medios_lista=medios_lista
    )

def renderizar_espana(noticias_espana, cachebuster):
    template_str = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>España en el mundo | Prisma</title>
    <meta name="description" content="Visión de la prensa internacional sobre España.">
    <link rel="stylesheet" href="prisma.css?v={{ cachebuster }}">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma">
                <a href="index.html" class="logo-link">PRISMA</a>
            </div>
            <nav class="nav">
                <a href="index.html">Inicio</a>
                <a href="sobre.html">Sobre Prisma</a>
                <a href="espana.html" class="active">España en el mundo</a>
                <a href="mailto:ovalero@gmail.com">Contacto</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <div class="card portada">
            <h2>🌍 España en el mundo</h2>
            <p>Visión de la prensa internacional sobre España.</p>
            <div class="filtro-container">
                <label for="filtro-medio-int">Filtrar por medio:</label>
                <select id="filtro-medio-int">
                    <option value="todos">Todos los medios</option>
                    {% for medio in medios_int %}
                    <option value="{{ medio }}">{{ medio }}</option>
                    {% endfor %}
                </select>
            </div>
        </div>

        <div id="noticias-int">
            {% for n in noticias_espana %}
            <p class="noticia-item" data-medio="{{ n.medio }}"><strong>{{ n.medio }}:</strong> <a href="{{ n.link }}" target="_blank" rel="noopener">{{ n.titulo }}</a></p>
            {% endfor %}
        </div>
    </div>

    <!-- Botones flotantes (igual que en index) -->
    <div class="compartir-flotante">
        <a href="https://twitter.com/intent/tweet?text=🌍%20España%20en%20el%20mundo%20según%20Prisma&url=https://prismanews.github.io/prisma/espana.html" target="_blank" class="share-btn twitter">🐦</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://prismanews.github.io/prisma/espana.html" target="_blank" class="share-btn facebook">📘</a>
        <a href="https://wa.me/?text=🌍%20España%20en%20el%20mundo%20según%20Prisma%20https://prismanews.github.io/prisma/espana.html" target="_blank" class="share-btn whatsapp">📱</a>
        <a href="https://t.me/share/url?url=https://prismanews.github.io/prisma/espana.html&text=🌍%20España%20en%20el%20mundo%20según%20Prisma" target="_blank" class="share-btn telegram">📨</a>
        <button onclick="copiarPortapapeles('https://prismanews.github.io/prisma/espana.html')" class="share-btn copy">📋</button>
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
                `;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            });
        }

        document.getElementById('filtro-medio-int').addEventListener('change', function(e) {
            const medio = e.target.value;
            document.querySelectorAll('.noticia-item').forEach(item => {
                if (medio === 'todos' || item.dataset.medio === medio) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    </script>
</body>
</html>
"""
    medios_int = sorted(set(n["medio"] for n in noticias_espana))
    template = jinja2.Template(template_str)
    return template.render(
        noticias_espana=noticias_espana,
        cachebuster=cachebuster,
        medios_int=medios_int
    )

# ---------- MAIN ----------
if __name__ == "__main__":
    start = time.time()
    logging.info("Iniciando generación de Prisma")

    # Cargar caché de embeddings
    embedding_cache = cargar_cache_embeddings() if CACHE_EMBEDDINGS else {}

    # 1. Noticias españolas
    noticias = recoger_noticias(feeds_espanoles, MAX_NOTICIAS_FEED, MAX_NOTICIAS_TOTAL)
    logging.info(f"Noticias recogidas: {len(noticias)}")

    if not noticias:
        logging.error("No se obtuvieron noticias. Abortando.")
        exit(1)

    # Calcular embeddings con caché
    titulos = [n["titulo"] for n in noticias]
    embeddings_list = []
    for titulo in titulos:
        key = hashlib.md5(titulo.encode()).hexdigest()
        if key in embedding_cache:
            embeddings_list.append(np.array(embedding_cache[key]))
        else:
            emb = modelo.encode([titulo])[0]
            embedding_cache[key] = emb.tolist()
            embeddings_list.append(emb)
    embeddings = np.array(embeddings_list)

    if CACHE_EMBEDDINGS:
        guardar_cache_embeddings(embedding_cache)

    # Deduplicar
    noticias, embeddings = deduplicar_noticias(noticias, embeddings, UMBRAL_DUPLICADO)
    logging.info(f"Después de deduplicar: {len(noticias)}")

    # Clusterizar
    grupos = clusterizar(embeddings, UMBRAL_CLUSTER)
    logging.info(f"Grupos formados: {len(grupos)}")

    # Preparar datos para template
    fecha = datetime.now()
    fecha_legible = fecha.strftime("%d/%m/%Y %H:%M")
    fecha_iso = fecha.isoformat()
    cachebuster = int(fecha.timestamp())
    medios_unicos = len(set(n["medio"] for n in noticias))

    html_index = renderizar_index(noticias, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_index)

    # 2. Internacional España
    noticias_int = recoger_noticias(feeds_internacionales, MAX_NOTICIAS_INTERNACIONAL, MAX_NOTICIAS_INTERNACIONAL*2)
    # Filtrar las que mencionan España
    noticias_espana = []
    for n in noticias_int:
        texto = n["titulo"] + " " + (n.get("resumen") or "")
        if menciona_espana(texto):
            noticias_espana.append(n)
    noticias_espana = list({n["link"]: n for n in noticias_espana}.values())
    noticias_espana.sort(key=lambda x: x["fecha"], reverse=True)
    noticias_espana = noticias_espana[:MAX_NOTICIAS_INTERNACIONAL]
    logging.info(f"Noticias internacionales sobre España: {len(noticias_espana)}")

    html_espana = renderizar_espana(noticias_espana, cachebuster)
    with open("espana.html", "w", encoding="utf-8") as f:
        f.write(html_espana)

    # 3. Sitemap y robots
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://prismanews.github.io/prisma/</loc><lastmod>{fecha_iso}</lastmod></url>
<url><loc>https://prismanews.github.io/prisma/espana.html</loc><lastmod>{fecha_iso}</lastmod></url>
</urlset>"""
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)

    robots = """User-agent: *
Allow: /
Sitemap: https://prismanews.github.io/prisma/sitemap.xml
"""
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(robots)

    logging.info(f"Generación completada en {time.time()-start:.2f} segundos")
