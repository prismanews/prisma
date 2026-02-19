#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRISMA - Generador completo (VERSIÓN CORREGIDA CON MÁS INTERNACIONALES)
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

# ========== CONFIGURACIÓN ==========
UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
UMBRAL_AGRUPACION_MIN = 0.5
MAX_NOTICIAS_FEED = 8
MAX_NOTICIAS_TOTAL = 250
MAX_NOTICIAS_INTERNACIONAL = 80  # ✅ CAMBIADO DE 40 A 80
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

# ========== REFERENCIAS DE SESGO ==========
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
        # internacional
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
        # internacional
        "fiscal responsibility strong military traditional culture business friendly policies",
        "economic growth tax cuts deregulation free trade"
    ])
}

# ========== FEEDS ESPAÑOLES ==========
feeds_espanoles = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/feed/",
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
    "Infobae España": "https://www.infobae.com/espana/arc/outboundfeeds/rss/",
    "OK Diario": "https://okdiario.com/feed/",
    "El Plural": "https://www.elplural.com/feed",
    "Vozpópuli": "https://www.vozpopuli.com/feed.xml",
    "Moncloa.com": "https://www.moncloa.com/feed",
    "El Independiente": "https://www.elindependiente.com/feed",
    "The Objective": "https://theobjective.com/feed",
    "Crónica Global": "https://cronicaglobal.elespanol.com/feed",
    "El Debate": "https://www.eldebate.com/feed",
    "Libertad Digital": "https://www.libertaddigital.com/feed",
    "El Periódico de España": "https://www.epe.es/es/rss/portada.xml",
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
    "RT News": "https://www.rt.com/rss/news/",
    "RT en Español": "https://actualidad.rt.com/feeds/noticias.rss",
    "TASS": "http://tass.com/rss/v2.xml",
    "Yonhap News": "https://en.yna.co.kr/feed/",
    "Korea Times": "https://www.koreatimes.co.kr/www/rss/news.xml",
    "Korea Herald": "http://www.koreaherald.com/rss_xml.php",
    "Arirang News": "https://www.arirang.com/news/rss.xml",
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
    "Al Arabiya English": "https://english.alarabiya.net/alarabiya-rss",
    "Middle East Eye": "https://www.middleeasteye.net/rss",
    "The National": "https://www.thenationalnews.com/arc/outboundfeeds/rss/",
    "Arab News": "https://www.arabnews.com/rss",
    
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
    "Prensa Latina": "https://www.prensa-latina.cu/feed/",
    "Infobae América": "https://www.infobae.com/america/arc/outboundfeeds/rss/",
    "El Universal MX": "https://www.eluniversal.com.mx/rss",
    "La Nación AR": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/",
    "El Comercio PE": "https://elcomercio.pe/arc/outboundfeeds/rss/",
}

# ========== KEYWORDS MULTILINGÜES MEJORADAS ==========
KEYWORDS_ESPANA = [
    # Castellano / Español (todo lo que ya tenías)
    "españa", "espana", "español", "española", "españoles",
    "madrid", "barcelona", "valencia", "sevilla", "bilbao",
    "cataluña", "catalunya", "país vasco", "euskadi", "andalucía",
    "galicia", "canarias", "balears", "ibiza", "mallorca",
    "pedro sanchez", "feijoo", "abascal", "yolanda díaz",
    "gobierno español", "moncloa", "congreso", "senado",
    "la liga", "real madrid", "fc barcelona", "atlético",
    
    # English (mejorado)
    "spain", "spanish", "spaniard", "spain's", "spanish prime minister", "pedro sanchez",
    "catalonia", "basque country", "andalusia", "catalan", "basque", "andalusian",
    "spanish government", "prime minister spain", "valencia", "seville",
    "barcelona", "madrid", "real madrid", "fc barcelona",
    
    # Français (mejorado)
    "espagne", "espagnol", "espagnole", "espagnole", "espagnols",
    "catalogne", "pays basque", "andalousie",
    "gouvernement espagnol", "pedro sanchez", "premier ministre espagnol",
    
    # Deutsch (mejorado)
    "spanien", "spanisch", "spanier", "spanische", "spanischer",
    "katalonien", "baskenland", "andalusien",
    "spanische regierung", "ministerpräsident", "madrid", "barcelona",
    
    # Italiano (mejorado)
    "spagna", "spagnolo", "spagnola", "spagnoli",
    "catalogna", "paesi baschi", "andalusia",
    "governo spagnolo", "primo ministro spagnolo",
    
    # Português (mejorado)
    "espanha", "espanhol", "espanhola", "espanhóis",
    "catalunha", "país basco", "andalucia",
    "governo espanhol", "primeiro-ministro espanhol",
    
    # Русский (Ruso) - MEJORADO
    "испания", "испанский", "испанская", "испанские",
    "мадрид", "барселона", "каталония",
    "премьер-министр испании", "правительство испании",
    
    # 中文 (Chino) - MEJORADO
    "西班牙", "西班牙的", "西班牙人", "西班牙首相", "西班牙政府",
    "马德里", "巴塞罗那", "加泰罗尼亚",
    
    # 日本語 (Japonés) - MEJORADO
    "スペイン", "スペインの", "スペイン人",
    "マドリード", "バルセロナ", "カタルーニャ",
    "スペイン首相", "スペイン政府",
    
    # 한국어 (Coreano) - MEJORADO
    "스페인", "스페인의", "스페인 사람",
    "마드리드", "바르셀로나", "카탈루냐",
    "스페인 총리", "스페인 정부",
    
    # العربية (Árabe) - MEJORADO
    "إسبانيا", "الإسبانية", "الإسبان",
    "مدريد", "برشلونة", "كاتالونيا",
    "رئيس الوزراء الإسباني", "الحكومة الإسبانية",
]

# Stopwords
STOPWORDS = set([
    "el","la","los","las","un","una","unos","unas","de","del","al","a","en","por","para","con","sin",
    "sobre","entre","hasta","desde","y","o","e","ni","que","como","pero","aunque","porque","ya","también","solo",
    "su","sus","se","lo","le","les","esto","esta","estos","estas","ese","esa","esos","esas",
    "hoy","ayer","mañana","tras","antes","después","dice","según","afirma","asegura","explica",
    "the","a","an","of","to","in","on","for","with","and","or","but","from","by","about","as","at",
    "le","la","les","du","des","sur","dans","avec","pour","par","est","sont","ont","été",
    "der","die","das","und","mit","von","für","auf","bei","nach","aus","durch","über","unter",
    "il","la","le","gli","i","del","della","dei","con","per","tra","fra","che","cui",
    "o","a","os","as","do","da","dos","das","para","com","sem","sob","entre","após",
])

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
        r'\bmadrid\b', r'\bbarcelona\b', r'\bcatalon ia\b', r'\bbasque\b',
        r'pedro sánchez', r'\bfeijóo\b', r'\bvox\b', r'\bpsoe\b', r'\bpp\b',
    ]
    
    for patron in patrones:
        if re.search(patron, texto_lower):
            return True
    
    return False

# ========== RECOGER NOTICIAS PARALELO ==========
def recoger_noticias_paralelo(feeds_dict, max_por_feed, max_total):
    noticias = []
    
    with ThreadPoolExecutor(max_workers=15) as executor:
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

# ========== ANÁLISIS DE SESGO ==========
def analizar_sesgo(indices, noticias):
    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16, show_progress_bar=False)
    centroide = np.mean(emb, axis=0).reshape(1, -1)
    
    prog = cosine_similarity(centroide, referencias_politicas["progresista"]).mean()
    cons = cosine_similarity(centroide, referencias_politicas["conservador"]).mean()
    
    total = prog + cons
    pct_prog = (prog / total) * 100 if total > 0 else 50
    pct_cons = (cons / total) * 100 if total > 0 else 50
    
    if abs(prog - cons) < 0.015:
        texto = "Cobertura muy equilibrada"
    elif prog > cons:
        diff = (prog - cons) * 100
        texto = "Enfoque marcadamente progresista" if diff > 20 else "Enfoque ligeramente progresista"
    else:
        diff = (cons - prog) * 100
        texto = "Enfoque marcadamente conservador" if diff > 20 else "Enfoque ligeramente conservador"
    
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

# ========== GENERAR INDEX.HTML (CON GOOGLE ANALYTICS) ==========
def generar_index_html(noticias, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos):
    html = f"""<!DOCTYPE html>
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
    <style>
        .filtro-container {{
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 16px 24px;
            margin-bottom: 32px;
            border: 1px solid var(--border-light);
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .filtro-container select {{
            padding: 8px 16px;
            border-radius: 40px;
            border: 1px solid var(--border-medium);
            background: var(--bg-primary);
            color: var(--text-primary);
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
        <!-- Filtro interactivo -->
        <div class="filtro-container">
            <label for="filtro-medio">📋 Filtrar por medio:</label>
            <select id="filtro-medio">
                <option value="todos">Todos los medios</option>
"""
    
    # Añadir opciones de medios
    medios_lista = sorted(set(n["medio"] for n in noticias))
    for medio in medios_lista:
        html += f'                <option value="{medio}">{medio}</option>\n'
    
    html += """            </select>
        </div>
"""
    
    # Añadir grupos
    for i, grupo in enumerate(grupos[:15]):
        sesgo = analizar_sesgo(grupo, noticias)
        resumen = resumen_prisma(grupo, noticias)
        titular = titular_prisma(grupo, noticias)
        
        medios_grupo = list(set(noticias[i]["medio"] for i in grupo))
        medios_str = ",".join(medios_grupo)
        
        html += f"""
        <div class="card" data-medios="{medios_str}">
            <h2>{titular}</h2>
            <div class="resumen">
                {resumen['emoji']} <strong>Resumen IA:</strong>
                {resumen['num_medios']} medios · {resumen['sentimiento']} · 
                {', '.join(resumen['angulos']) if resumen['angulos'] else 'enfoque directo'}
            </div>
            <div class="sesgo-card">
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
                <p class="sesgo-nota">Análisis automático basado en el lenguaje de los titulares</p>
            </div>
"""
        
        for idx in grupo[:6]:
            n = noticias[idx]
            html += f"""
            <p><strong>{n['medio']}:</strong> <a href="{n['link']}" target="_blank" rel="noopener">{n['titulo']}</a></p>
"""
        
        html += "        </div>\n"
    
    # Call to Action
    html += """
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
"""
    return html

# ========== GENERAR ESPANA.HTML (CON GOOGLE ANALYTICS) ==========
def generar_espana_html(noticias_espana, cachebuster):
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if not noticias_espana:
        noticias_html = "<p class='sin-noticias'>🌍 No hay noticias sobre España en este momento. Pronto se actualizará.</p>"
    else:
        noticias_html = ""
        for n in noticias_espana[:40]:
            # Formatear fecha
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
    
    html = f"""<!DOCTYPE html>
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
    <style>
        .internacional-header {{
            background: linear-gradient(135deg, #1e3a8a20, #0d948820);
            border-radius: var(--radius-xl);
            padding: 32px;
            margin-bottom: 32px;
            border: 1px solid var(--border-light);
        }}
        .internacional-header h2 {{
            font-size: 2.2rem;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .filtro-medios {{
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 20px 24px;
            margin-bottom: 32px;
            border: 1px solid var(--border-light);
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .filtro-medios select {{
            padding: 10px 20px;
            border-radius: 40px;
            border: 1px solid var(--border-medium);
            background: var(--bg-primary);
            color: var(--text-primary);
            min-width: 200px;
        }}
        .lista-noticias {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .noticia-item {{
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 20px 24px;
            border: 1px solid var(--border-light);
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .noticia-item:hover {{
            transform: translateX(4px);
            box-shadow: var(--shadow-md);
            border-color: var(--primary);
        }}
        .noticia-medio {{
            font-weight: 700;
            color: var(--accent);
            background: var(--accent-soft);
            padding: 4px 16px;
            border-radius: 40px;
            font-size: 0.85rem;
            white-space: nowrap;
            border: 1px solid var(--accent-light);
        }}
        .noticia-titulo {{
            flex: 1;
            color: var(--text-primary);
        }}
        .noticia-titulo a {{
            color: inherit;
            text-decoration: none;
        }}
        .noticia-titulo a:hover {{
            color: var(--primary);
            text-decoration: underline;
        }}
        .noticia-fecha {{
            color: var(--text-tertiary);
            font-size: 0.85rem;
            white-space: nowrap;
        }}
        .sin-noticias {{
            text-align: center;
            padding: 60px 20px;
            background: var(--bg-secondary);
            border-radius: var(--radius-xl);
            color: var(--text-tertiary);
        }}
        @media (max-width: 640px) {{
            .noticia-item {{
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }}
            .noticia-fecha {{
                align-self: flex-end;
            }}
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
            <p>Lo que la prensa internacional publica sobre España. Actualizado: {fecha_actual}</p>
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

        // Cargar medios en el filtro
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
        
        // Filtrar al cambiar
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
"""
    return html

# ========== GENERAR SOBRE.HTML (CON GOOGLE ANALYTICS) ==========
def generar_sobre_html():
    html = """<!DOCTYPE html>
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
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-9WZC3GQSN8');
    </script>
    
    <link rel="stylesheet" href="prisma.css">
    <style>
        .about-container { max-width: 900px; margin: 0 auto; }
        .about-card {
            background: var(--bg-primary);
            border-radius: var(--radius-xl);
            padding: 48px;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border-light);
            position: relative;
            overflow: hidden;
        }
        .about-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
            background-size: 200% 100%;
            animation: gradientMove 8s ease infinite;
        }
        @keyframes gradientMove {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .hero-about {
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 32px;
            border-bottom: 2px dashed var(--border-light);
        }
        .hero-about h1 {
            font-size: 2.8rem;
            margin-bottom: 20px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-about p {
            font-size: 1.3rem;
            color: var(--text-secondary);
            max-width: 700px;
            margin: 0 auto;
            font-weight: 300;
        }
        .about-section {
            margin-bottom: 40px;
        }
        .about-section h2 {
            font-size: 2rem;
            margin-bottom: 20px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .about-section h2::before {
            content: '◆';
            color: var(--accent);
            font-size: 1.8rem;
            opacity: 0.7;
        }
        .about-section p {
            font-size: 1.1rem;
            line-height: 1.8;
            color: var(--text-secondary);
            margin-bottom: 20px;
        }
        .about-highlight {
            background: linear-gradient(135deg, var(--primary-soft), var(--accent-soft));
            padding: 24px 32px;
            border-radius: var(--radius-lg);
            margin: 32px 0;
            border-left: 4px solid var(--primary);
            font-style: italic;
        }
        .contacto-box {
            background: var(--bg-secondary);
            border-radius: var(--radius-lg);
            padding: 32px;
            text-align: center;
            border: 1px solid var(--border-light);
            margin: 40px 0 20px;
        }
        .contacto-box a {
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
        }
        .contacto-box a:hover {
            background: var(--primary);
            color: white;
            transform: translateY(-2px);
        }
        .firma {
            text-align: center;
            margin-top: 48px;
            padding-top: 32px;
            border-top: 2px dashed var(--border-light);
            font-size: 1.2rem;
            color: var(--text-tertiary);
            font-style: italic;
        }
        @media (max-width: 768px) {
            .about-card { padding: 32px 24px; }
            .hero-about h1 { font-size: 2.2rem; }
        }
    </style>
</head>
<body>
    <header class="header glass">
        <div class="header-content">
            <div class="logo">
                <img src="Logo.PNG" class="logo-img" alt="Prisma" onerror="this.style.display='none'">
                <a href="index.html" class="logo-link">PRISMA</a>
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
    </script>
</body>
</html>
"""
    return html

# ========== GENERAR SITEMAP Y ROBOTS ==========
def generar_sitemap():
    fecha_iso = datetime.now().isoformat()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://prismanews.github.io/prisma/</loc><lastmod>{fecha_iso}</lastmod></url>
    <url><loc>https://prismanews.github.io/prisma/sobre.html</loc><lastmod>{fecha_iso}</lastmod></url>
    <url><loc>https://prismanews.github.io/prisma/espana.html</loc><lastmod>{fecha_iso}</lastmod></url>
</urlset>
"""

def generar_robots():
    return """User-agent: *
Allow: /
Sitemap: https://prismanews.github.io/prisma/sitemap.xml
"""

# ========== MAIN ==========
if __name__ == "__main__":
    inicio_total = time.time()
    logging.info("🚀 Iniciando generación de Prisma")
    
    # Cargar caché
    embedding_cache = cargar_cache_embeddings() if CACHE_EMBEDDINGS else {}
    
    # 1. Noticias españolas
    logging.info("📰 Recogiendo noticias españolas...")
    noticias = recoger_noticias_paralelo(feeds_espanoles, MAX_NOTICIAS_FEED, MAX_NOTICIAS_TOTAL)
    logging.info(f"✅ {len(noticias)} noticias recogidas")
    
    if not noticias:
        logging.error("❌ No hay noticias. Abortando.")
        exit(1)
    
    # Calcular embeddings
    logging.info("🧠 Calculando embeddings...")
    embeddings = calcular_embeddings(noticias, embedding_cache)
    
    # Guardar caché
    if CACHE_EMBEDDINGS:
        guardar_cache_embeddings(embedding_cache)
    
    # Deduplicar
    logging.info("🔄 Deduplicando...")
    noticias, embeddings = deduplicar_noticias(noticias, embeddings)
    logging.info(f"✅ {len(noticias)} noticias tras deduplicar")
    
    # Clusterizar
    logging.info("📊 Clusterizando...")
    grupos = clusterizar(embeddings)
    logging.info(f"✅ {len(grupos)} grupos formados")
    
    # Generar index.html
    logging.info("📝 Generando index.html...")
    fecha = datetime.now()
    fecha_legible = fecha.strftime("%d/%m/%Y %H:%M")
    fecha_iso = fecha.isoformat()
    cachebuster = int(fecha.timestamp())
    medios_unicos = len(set(n["medio"] for n in noticias))
    
    html_index = generar_index_html(noticias, grupos, fecha_legible, fecha_iso, cachebuster, medios_unicos)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_index)
    
    # 2. Noticias internacionales sobre España - ✅ AHORA CON LÍMITE CORREGIDO
    logging.info("🌍 Recogiendo noticias internacionales...")
    noticias_int = recoger_noticias_paralelo(feeds_internacionales, MAX_NOTICIAS_FEED, MAX_NOTICIAS_INTERNACIONAL)  # ✅ CAMBIADO
    
    # Filtrar las que mencionan España
    noticias_espana = []
    for n in noticias_int:
        texto = n["titulo"] + " "
        if "resumen" in n:
            texto += n["resumen"]
        if menciona_espana(texto):
            noticias_espana.append(n)
    
    # Eliminar duplicados
    noticias_espana = list({n["link"]: n for n in noticias_espana}.values())
    noticias_espana.sort(key=lambda x: x["fecha"], reverse=True)
    noticias_espana = noticias_espana[:MAX_NOTICIAS_INTERNACIONAL]
    logging.info(f"✅ {len(noticias_espana)} noticias sobre España encontradas")
    
    # Generar espana.html
    logging.info("📝 Generando espana.html...")
    html_espana = generar_espana_html(noticias_espana, cachebuster)
    with open("espana.html", "w", encoding="utf-8") as f:
        f.write(html_espana)
    
    # Generar sobre.html
    logging.info("📝 Generando sobre.html...")
    html_sobre = generar_sobre_html()
    with open("sobre.html", "w", encoding="utf-8") as f:
        f.write(html_sobre)
    
    # Generar sitemap y robots
    logging.info("🗺️ Generando sitemap.xml...")
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(generar_sitemap())
    
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(generar_robots())
    
    tiempo_total = time.time() - inicio_total
    logging.info(f"✅ Generación completada en {tiempo_total:.2f} segundos")
