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
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------- CONFIG PRO ----------

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prisma.log'),
        logging.StreamHandler()
    ]
)

UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
UMBRAL_AGRUPACION_MIN = 0.5
MAX_NOTICIAS_FEED = 8
MAX_NOTICIAS_TOTAL = 250
MAX_NOTICIAS_INTERNACIONAL = 40
CACHE_EMBEDDINGS = True
CACHE_FILE = "embeddings_cache.json"

modelo = SentenceTransformer("all-MiniLM-L6-v2")


# ---------- REFERENCIAS NLP SESGO (MEJORADAS PRO) ----------

referencias_politicas = {
    "progresista": modelo.encode([
        # español
        "derechos sociales igualdad feminismo justicia social diversidad políticas públicas bienestar",
        "progresismo cambio climático políticas sociales regulación inclusión servicios públicos",
        "derechos humanos libertad expresión manifestación protesta social sindicatos",
        "sanidad pública educación universal pensiones justas derechos laborales",

        # inglés
        "social justice equality progressive politics climate action diversity welfare public services",
        "left wing policies regulation social rights inclusion government intervention",
        "human rights free speech protests unions workers rights minimum wage",

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

        # inglés
        "border security national defense free market traditional values low taxes immigration control",
        "conservative policies economic freedom national identity law and order",
        "family values individual liberty private property merit authority",

        # internacional neutro
        "fiscal responsibility strong military traditional culture business friendly policies",
        "economic growth tax cuts deregulation free trade"
    ])
}

# ---------- FEEDS ----------
feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "El Español": "https://www.elespanol.com/rss/",
    "RTVE": "https://www.rtve.es/rss/",
    "BBC Mundo": "https://feeds.bbci.co.uk/mundo/rss.xml",
    "France24 Español": "https://www.france24.com/es/rss",
    "DW Español": "https://rss.dw.com/xml/rss-es-all",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "HuffPost": "https://www.huffingtonpost.es/feeds/index.xml",
    "CNN Español": "https://cnnespanol.cnn.com/feed/",
    "NYTimes World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "La Voz de Galicia": "https://www.lavozdegalicia.es/rss/portada.xml",
    "El Correo": "https://www.elcorreo.com/rss/portada.xml",
    "Diario Sur": "https://www.diariosur.es/rss/portada.xml",
    "Levante": "https://www.levante-emv.com/rss/portada.xml",
    "Heraldo": "https://www.heraldo.es/rss/portada/",
    "Xataka": "https://www.xataka.com/feedburner.xml",
    "Genbeta": "https://www.genbeta.com/feedburner.xml",
    "Trendencias": "https://www.trendencias.com/feedburner.xml",
    "Verne": "https://feeds.elpais.com/mrss-s/pages/ep/site/verne.elpais.com/portada",
    "Yorokobu": "https://www.yorokobu.es/feed/",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=general-news",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "El Periódico": "https://www.elperiodico.com/es/rss/rss_portada.xml",
    "Diario Vasco": "https://www.diariovasco.com/rss/portada.xml",
    "Información Alicante": "https://www.informacion.es/rss/portada.xml",
    "Hipertextual": "https://hipertextual.com/feed",
    "Microsiervos": "https://www.microsiervos.com/index.xml",
    "Applesfera": "https://www.applesfera.com/feedburner.xml",
    "Expansión": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "Cinco Días": "https://cincodias.elpais.com/seccion/rss/portada/",
    "Nature News": "https://www.nature.com/nature.rss",
    "Scientific American": "https://rss.sciam.com/ScientificAmerican-Global",
    "Infolibre": "https://www.infolibre.es/rss",
    "El Salto": "https://www.elsaltodiario.com/rss",
    "CTXT": "https://ctxt.es/es/feed/",
    "Jacobin": "https://jacobin.com/feed",
    "Politico EU": "https://www.politico.eu/feed/",
    "OpenDemocracy": "https://www.opendemocracy.net/en/rss.xml"
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

    # 🌎 América Latina internacional
    "Clarin": "https://www.clarin.com/rss/lo-ultimo/",
    "El Tiempo CO": "https://www.eltiempo.com/rss/colombia.xml",
    "Granma": "http://www.granma.cu/feed",
    "Cubadebate": "http://www.cubadebate.cu/feed/",
    "Prensa Latina": "https://www.prensa-latina.cu/feed/"
}

KEYWORDS_ESPANA = [

    # ----- País básico (multilenguaje) -----
    "españa","espana","spain",
    "espagne","spanien","spagna","espanya",
    "西班牙","スペイン","스페인",
    # Árabe (transliterado)
    "isbania", "isbaniya", "اسبانیا",
    # Ruso (transliterado)
    "ispaniya", "ispanya", "испания",
    # Chino (pinyin)
    "xibanya", "xībānyá",
    # Japonés (romaji)
    "supein",
    # Coreano (romaji)
    "seupain",

    # gentilicios
    "spanish","español","spaniard","spaniards",
    "espagnol","espagnols",
    "spanisch",
    "spagnolo","spagnoli",
    "espanhol","espanhóis",

    # ----- Ciudades internacionales -----
    "madrid","barcelona","valencia","sevilla","seville",
    "bilbao","zaragoza","malaga","málaga",
    "granada","ibiza","mallorca","majorca",

    # ----- Regiones / territorios -----
    "catalonia","cataluña","catalunya",
    "basque country","pais vasco",
    "andalusia","andalucía",
    "galicia",
    "balearic islands","canary islands",
    "islas canarias",

    # ----- Política española internacional -----
    "spanish government","gobierno español",
    "gobierno de españa",
    "pedro sanchez","sánchez","feijoo",
    "vox spain","psoe","pp spain",

    # francés / alemán política frecuente
    "gouvernement espagnol",
    "regierung spanien",

    # italiano / portugués política
    "governo spagnolo",
    "governo espanhol",

    # ----- Economía / turismo -----
    "spanish economy","economía española",
    "economia spagnola","economia espanhola",
    "spanische wirtschaft",

    "tourism spain","turismo españa",
    "turismo spagna","turismo espanhol",

    "housing spain","crisis vivienda españa",

    # ----- Cultura / deporte -----
    "la liga",
    "real madrid","fc barcelona",
    "spanish football",
    "fútbol español",

    # ----- Geopolítica / ubicación -----
    "iberian peninsula","península ibérica",
    "iberia",
    "southern europe",
    "mediterranean spain",
    "spain eu","spanish presidency eu",
    "nato spain"
]

# ---------- STOPWORDS MEJORADAS ----------

stopwords = {
    # artículos / básicos español
    "el","la","los","las","un","una","unos","unas",
    "de","del","al","a","en","por","para","con","sin",
    "sobre","entre","hasta","desde",

    # conjunciones / conectores
    "y","o","e","ni","que","como","pero","aunque",
    "porque","ya","también","solo",

    # posesivos / pronombres
    "su","sus","se","lo","le","les","esto","esta",
    "estos","estas","ese","esa","esos","esas",

    # tiempo típico noticias
    "hoy","ayer","mañana","tras","antes","después",
    "última","últimas","último","últimos",

    # palabras periodísticas vacías
    "dice","según","afirma","asegura","explica",
    "parte","caso","forma","vez","años","días","meses",

    # inglés frecuente en feeds
    "the","a","an","of","to","in","on","for","with",
    "and","or","but","from","by","about","as",
    "after","before","over","under","during",

    # prensa internacional típica
    "says","said","report","reports","new","latest",
    "update","breaking","news","live","video","photos"
}

# ---------- FUNCIONES DE UTILIDAD ----------

def limpiar_html(texto):
    texto = html.unescape(texto)
    texto = re.sub(r'<.*?>', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return [p for p in palabras if p not in stopwords and len(p) > 3]


def get_embedding_cache_key(texto):
    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def cargar_cache_embeddings():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Error cargando caché: {e}")
    return {}


def guardar_cache_embeddings(cache):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
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


def obtener_feeds_seguro(url, medio, max_intentos=2):
    for intento in range(max_intentos):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            feed = feedparser.parse(url, request_headers=headers)
            if not feed.bozo or intento == max_intentos - 1:
                return feed
            time.sleep(1)
        except Exception as e:
            if intento == max_intentos - 1:
                logging.error(f"Error feed {medio} tras {max_intentos} intentos: {e}")
            time.sleep(1)
    return None

# ---------- RECOGER NOTICIAS ----------

start_time = time.time()
logging.info("Iniciando proceso de recogida de noticias")

embedding_cache = cargar_cache_embeddings() if CACHE_EMBEDDINGS else {}

noticias = []

for medio, url in feeds.items():
    feed = obtener_feeds_seguro(url, medio)
    if not feed:
        continue

    try:
        entradas = sorted(feed.entries, 
                         key=extraer_fecha_noticia, 
                         reverse=True)[:MAX_NOTICIAS_FEED]

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

print("Noticias recogidas:", len(noticias))

# ---------- INTERNACIONAL ESPAÑA ----------

noticias_espana = []
visto = set()

for medio, url in feeds_internacionales.items():
    feed = obtener_feeds_seguro(url, medio)
    if not feed or feed.bozo:
        continue

    try:
        for entry in feed.entries[:MAX_NOTICIAS_INTERNACIONAL]:
            if "title" not in entry or "link" not in entry:
                continue

            link = entry.link.strip()
            if link in visto:
                continue

            titulo = limpiar_html(entry.title)
            texto = titulo.lower()

            if "summary" in entry:
                texto += " " + limpiar_html(entry.summary).lower()
            if "description" in entry:
                texto += " " + limpiar_html(entry.description).lower()

            if any(k.lower() in texto for k in KEYWORDS_ESPANA):
                noticias_espana.append({
                    "medio": medio,
                    "titulo": titulo,
                    "link": link,
                    "fecha": extraer_fecha_noticia(entry)
                })
                visto.add(link)

    except Exception as e:
        logging.error(f"Error procesando feed internacional {medio}: {e}")

# quitar duplicados internacionales
noticias_espana = list({n["link"]: n for n in noticias_espana}.values())
noticias_espana.sort(key=lambda x: x.get("fecha", 0), reverse=True)
noticias_espana = noticias_espana[:MAX_NOTICIAS_INTERNACIONAL]

# ---------- LIMITAR NOTICIAS TOTALES ----------

if len(noticias) > MAX_NOTICIAS_TOTAL:
    logging.info(f"Limitando noticias de {len(noticias)} a {MAX_NOTICIAS_TOTAL}")
    noticias = noticias[:MAX_NOTICIAS_TOTAL]

# ---------- EMBEDDINGS CON CACHÉ ----------

titulos = [n["titulo"] for n in noticias]

if not titulos:
    print("⚠️ No hay titulares.")
    embeddings = np.array([])
else:
    embeddings_list = []
    titulos_procesar = []
    indices_procesar = []

    for i, titulo in enumerate(titulos):
        if CACHE_EMBEDDINGS:
            key = get_embedding_cache_key(titulo)
            if key in embedding_cache:
                embeddings_list.append(np.array(embedding_cache[key]))
            else:
                titulos_procesar.append(titulo)
                indices_procesar.append(i)
        else:
            titulos_procesar.append(titulo)
            indices_procesar.append(i)

    if titulos_procesar:
        nuevos_embeddings = modelo.encode(titulos_procesar, batch_size=32)
        
        if CACHE_EMBEDDINGS:
            for idx, emb in zip(indices_procesar, nuevos_embeddings):
                key = get_embedding_cache_key(titulos[idx])
                embedding_cache[key] = emb.tolist()
            
            guardar_cache_embeddings(embedding_cache)

        if CACHE_EMBEDDINGS:
            emb_completos = [None] * len(titulos)
            for i, emb in zip(indices_procesar, nuevos_embeddings):
                emb_completos[i] = emb
            
            for i in range(len(titulos)):
                if emb_completos[i] is None:
                    key = get_embedding_cache_key(titulos[i])
                    emb_completos[i] = np.array(embedding_cache[key])
            
            embeddings = np.array(emb_completos)
        else:
            embeddings = nuevos_embeddings
    else:
        embeddings = np.array(embeddings_list)

# ---------- DEDUPLICADO MEJORADO ----------

filtradas = []
emb_filtrados = []
links_vistos = set()

for i, emb in enumerate(embeddings):
    if noticias[i]["link"] in links_vistos:
        continue

    if not emb_filtrados:
        filtradas.append(noticias[i])
        emb_filtrados.append(emb)
        links_vistos.add(noticias[i]["link"])
        continue

    similitudes = cosine_similarity([emb], emb_filtrados)[0]

    if max(similitudes) < UMBRAL_DUPLICADO:
        es_duplicado_texto = any(
            son_duplicados_texto(noticias[i]["titulo"], n["titulo"])
            for n in filtradas
        )
        if not es_duplicado_texto:
            filtradas.append(noticias[i])
            emb_filtrados.append(emb)
            links_vistos.add(noticias[i]["link"])

noticias = filtradas
embeddings = np.array(emb_filtrados)

# ---------- CLUSTERING PRO (NO PÁGINA VACÍA) ----------

grupos = []

for i, emb in enumerate(embeddings):

    mejor_grupo = None
    mejor_score = 0

    for grupo in grupos:
        centroide = np.mean(embeddings[grupo], axis=0)
        score = cosine_similarity([emb], [centroide])[0][0]

        if score > mejor_score:
            mejor_score = score
            mejor_grupo = grupo

    if mejor_score > UMBRAL_CLUSTER:
        mejor_grupo.append(i)
    else:
        grupos.append([i])

# 👉 FIX PROFESIONAL:
# evita página vacía si no hay clusters claros
if not grupos or all(len(g) < 2 for g in grupos):
    logging.info("No hay clusters claros, agrupando por similitud mínima")
    grupos = []
    usados = set()
    
    for i in range(len(noticias)):
        if i in usados:
            continue
        grupo = [i]
        for j in range(i + 1, len(noticias)):
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


# ---------- SESGO NLP MEJORADO CON BARRA VISUAL ----------

def sesgo_politico(indices):
    textos = [noticias[i]["titulo"] for i in indices]
    emb = modelo.encode(textos, batch_size=16)

    centroide = np.mean(emb, axis=0).reshape(1, -1)

    prog = cosine_similarity(
        centroide,
        referencias_politicas["progresista"]
    ).mean()

    cons = cosine_similarity(
        centroide,
        referencias_politicas["conservador"]
    ).mean()

    # Calcular porcentajes para la barra
    total = prog + cons
    porcentaje_prog = (prog / total) * 100 if total > 0 else 50
    porcentaje_cons = (cons / total) * 100 if total > 0 else 50
    
    # Determinar texto y colores
    if abs(prog - cons) < 0.015:
        texto = "⚖️ Cobertura muy equilibrada"
        color_prog = "#94a3b8"
        color_cons = "#94a3b8"
    elif prog > cons:
        diferencia = (prog - cons) * 100
        if diferencia > 20:
            texto = f"⬅️️ Enfoque marcadamente progresista"
        else:
            texto = f"🌿 Enfoque ligeramente progresista"
    else:
        diferencia = (cons - prog) * 100
        if diferencia > 20:
            texto = f"➡️ Enfoque marcadamente conservador"
        else:
            texto = f"🏛️ Enfoque ligeramente conservador"

    return f"""
    <div class="sesgo-card">
        <div class="sesgo-header">
            <span class="sesgo-texto">{texto}</span>
            <span class="sesgo-info" title="Basado en análisis semántico de los titulares mediante IA">ⓘ</span>
        </div>
        <div class="sesgo-barra">
            <div class="barra-progresista" style="width: {porcentaje_prog:.0f}%;"></div>
            <div class="barra-conservadora" style="width: {porcentaje_cons:.0f}%;"></div>
        </div>
        <div class="sesgo-etiquetas">
            <span>🌿 Progresista {porcentaje_prog:.0f}%</span>
            <span>🏛️ Conservador {porcentaje_cons:.0f}%</span>
        </div>
        <p class="sesgo-nota">Análisis automático basado en el lenguaje de los titulares</p>
    </div>
    """

# ---------- TITULAR IA ----------

def titular_prisma(indices):
    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = [p for p, _ in Counter(palabras).most_common(7)]

    blacklist = {"gobierno", "españa", "hoy", "última", "últimas", "nuevo", "nueva", "tras", "sobre"}
    comunes = [p for p in comunes if p not in blacklist][:4]

    if len(comunes) >= 3:
        tema = f"{comunes[0]}, {comunes[1]} y {comunes[2]}"
    elif len(comunes) == 2:
        tema = f"{comunes[0]} y {comunes[1]}"
    elif comunes:
        tema = comunes[0]
    else:
        tema = "actualidad"

    prefijos = [
        "🧭 Claves informativas:",
        "📊 En el foco:",
        "📰 Lo que domina hoy:",
        "🔥 Tema principal:",
        "🎯 En portada:",
        "📌 Lo más relevante:"
    ]

    return f"{random.choice(prefijos)} {tema.capitalize()}"

def resumen_prisma(indices):
    titulos_cluster = [noticias[i]["titulo"] for i in indices]
    medios_cluster = [noticias[i]["medio"] for i in indices]

    angulos = []
    if len(set(medios_cluster)) > 3:
        angulos.append("múltiples perspectivas")
    if len(set(medios_cluster)) > 5:
        angulos.append("amplia cobertura mediática")

    palabras_positivas = {"acuerdo", "mejora", "éxito", "avance", "logro", "beneficio"}
    palabras_negativas = {"crisis", "conflicto", "problema", "preocupación", "riesgo", "amenaza"}

    texto_completo = " ".join(titulos_cluster).lower()

    positivas = sum(1 for p in palabras_positivas if p in texto_completo)
    negativas = sum(1 for p in palabras_negativas if p in texto_completo)

    if positivas > negativas + 2:
        sentimiento = "🌞 tono positivo"
        emoji = "📈"
    elif negativas > positivas + 2:
        sentimiento = "🌧️ tono preocupante"
        emoji = "📉"
    else:
        sentimiento = "⚖️ tono equilibrado"
        emoji = "📊"

    palabras = []
    for i in indices:
        palabras += limpiar(noticias[i]["titulo"])

    comunes = [p for p, _ in Counter(palabras).most_common(6)]
    blacklist = {"gobierno", "españa", "última", "hoy", "tras", "según", "dice", "años", "parte", "caso"}
    comunes = [p for p in comunes if p not in blacklist][:3]

    tema_principal = ", ".join(comunes) if comunes else "la actualidad"

    return f"""
<p class="resumen">
{emoji} <b>Resumen IA:</b>
{len(set(medios_cluster))} medios · {sentimiento} · 
{', '.join(angulos) if angulos else 'enfoque directo'}
<br>
<small>🎯 Tema central: {tema_principal}</small>
</p>
"""
    
fecha = datetime.now()
fecha_legible = fecha.strftime("%d/%m/%Y %H:%M")
fecha_iso = fecha.isoformat()
cachebuster = int(fecha.timestamp())
medios_unicos = len(set(n["medio"] for n in noticias))

# ---------- TU HTML ORIGINAL COMPLETAMENTE INTACTO ----------

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">

<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-9WZC3GQSN8"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-9WZC3GQSN8');
</script>

<title>Prisma | Comparador IA de noticias</title>

<meta name="description"
content="Comparador inteligente de noticias. Analiza múltiples medios para ofrecer contexto y reducir ruido informativo.">

<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="googlebot" content="index, follow">
<link rel="canonical" href="https://prismanews.github.io/prisma/">

<!-- Open Graph -->
<meta property="og:title" content="Prisma noticias IA">
<meta property="og:description" content="Comparador inteligente de noticias con IA">
<meta property="og:image" content="Logo.PNG">
<meta property="og:type" content="website">
<meta property="og:url" content="https://prismanews.github.io/prisma/">
<meta http-equiv="content-language" content="es">

<!-- SEO extra -->
<meta name="theme-color" content="#ffffff">
<meta name="author" content="Prisma News">

<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">

<link rel="stylesheet" href="prisma.css?v={cachebuster}">
<meta name="viewport" content="width=device-width, initial-scale=1">

</head>
<body>

<header class="header">
<div class="logo">
<img src="Logo.PNG" class="logo-img">
<a href="index.html" class="logo-link">PRISMA</a>
</div>

<!-- NUEVO: Claim y explicación mejorada -->
<p class="claim">EL COMPARADOR DE MEDIOS CON IA</p>

<p class="explicacion">
    Analizamos automáticamente <strong>{medios_unicos} medios</strong> para detectar 
    <strong>enfoques editoriales, sesgos y tendencias informativas</strong> en tiempo real.
    <br><span class="highlight">Entiende cómo te cuentan la actualidad.</span>
</p>

<div class="stats">
📰 {medios_unicos} medios analizados ·
<time datetime="{fecha_iso}">Actualizado: {fecha_legible}</time>
</div>

<nav class="nav">
<a href="index.html?v={cachebuster}">Inicio</a>
<a href="sobre.html">Sobre Prisma</a>
<a href="espana.html?v={cachebuster}">España en el mundo</a>
<a href="mailto:ovalero@gmail.com?subject=Contacto%20Prisma">Contacto</a>
</nav>
</header>

<div class="container">
"""
<div class="container">
"""

for i, grupo in enumerate(grupos, 1):

    clase = "card"
    if i == 1:
        clase = "card portada"
    html += f"""
<div class="{clase}">

<h2>{titular_prisma(grupo)}</h2>
{resumen_prisma(grupo)}
{sesgo_politico(grupo)} 
"""

    for idx in grupo[:6]:
        n = noticias[idx]
        html += f"""
<p>
<strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank" rel="noopener noreferrer">{n['titulo']}</a>
</p>
"""
  
    html += "</div>"


# 👉 Truco tráfico joven (SEO + UX)
html += """
<footer style="text-align:center;opacity:.7;margin:40px 0;font-size:.9em">
Comparador automático de noticias con IA · Actualización continua
</footer>
"""

html += "</div></body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)


# ---------- SITEMAP ----------

sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://prismanews.github.io/prisma/</loc></url>
<url><loc>https://prismanews.github.io/prisma/espana.html</loc></url>
</urlset>
"""

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap)

# ---------- HTML ESPAÑA EN EL MUNDO ----------

html_espana = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="robots" content="index, follow">
<meta name="googlebot" content="index, follow">
<title>España en el mundo | Prisma</title>
<link rel="stylesheet" href="prisma.css?v={cachebuster}">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header class="header">
<div class="logo">
<img src="Logo.PNG" class="logo-img">
<a href="index.html" class="logo-link">PRISMA</a>
</div>

<nav class="nav">
<a href="index.html">Inicio</a>
<a href="sobre.html">Sobre Prisma</a>
<a href="espana.html">España en el mundo</a>
<a href="mailto:ovalero@gmail.com?subject=Contacto%20Prisma">
Contacto
</a>
</nav>
</header>

<div class="container">
<div class="card portada">
<h2>🌍 España en el mundo</h2>
<p>Visión de la prensa internacional sobre España.</p>
"""

for n in noticias_espana[:40]:
    html_espana += f"""
<p>
<strong>{n['medio']}:</strong>
<a href="{n['link']}" target="_blank" rel="noopener noreferrer">
{n['titulo']}
</a>
</p>
"""

html_espana += "</div></div></body></html>"

with open("espana.html", "w", encoding="utf-8") as f:
    f.write(html_espana)

# ---------- ROBOTS ----------

robots = """User-agent: *
Allow: /

Sitemap: https://prismanews.github.io/prisma/sitemap.xml
"""

with open("robots.txt", "w", encoding="utf-8") as f:
    f.write(robots)

# ---------- EXTRAS PARA VIRALIDAD Y ENGANCHE JOVEN ----------

def generar_widgets_compartir():
    """Genera botones de compartir para redes sociales"""
    url_actual = "https://prismanews.github.io/prisma/"
    texto_compartir = "📊 Descubre cómo la IA analiza el sesgo de los medios en Prisma"
    
    return f"""
    <!-- Botones flotantes de compartir -->
    <div class="compartir-flotante">
        <a href="https://twitter.com/intent/tweet?text={texto_compartir}&url={url_actual}" target="_blank" class="share-btn twitter">🐦</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u={url_actual}" target="_blank" class="share-btn facebook">📘</a>
        <a href="https://wa.me/?text={texto_compartir}%20{url_actual}" target="_blank" class="share-btn whatsapp">📱</a>
        <a href="https://t.me/share/url?url={url_actual}&text={texto_compartir}" target="_blank" class="share-btn telegram">📨</a>
        <button onclick="copiarPortapapeles('{url_actual}')" class="share-btn copy">📋</button>
    </div>

    <style>
    .compartir-flotante {{
        position: fixed;
        bottom: 20px;
        right: 20px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        z-index: 9999;
    }}
    .share-btn {{
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: white;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        text-decoration: none;
        transition: all 0.3s;
        animation: aparecer 0.5s ease;
    }}
    .share-btn:hover {{
        transform: scale(1.15);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }}
    .twitter {{ background: #1DA1F2; color: white; }}
    .facebook {{ background: #4267B2; color: white; }}
    .whatsapp {{ background: #25D366; color: white; }}
    .telegram {{ background: #0088cc; color: white; }}
    .copy {{ background: #6c757d; color: white; }}
    @keyframes aparecer {{
        from {{ transform: scale(0); opacity: 0; }}
        to {{ transform: scale(1); opacity: 1; }}
    }}
    </style>
    """

def generar_scripts_virales():
    """Genera JavaScript para funcionalidades virales"""
    return """
    <script>
    function copiarPortapapeles(texto) {
        navigator.clipboard.writeText(texto).then(() => {
            let toast = document.createElement('div');
            toast.textContent = '✅ Enlace copiado';
            toast.style.cssText = `
                position: fixed;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.9);
                color: white;
                padding: 12px 24px;
                border-radius: 50px;
                font-size: 14px;
                z-index: 10000;
                animation: slideUp 0.3s ease;
            `;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2000);
        });
    }

    // Animación de entrada para las tarjetas
    document.querySelectorAll('.card').forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Exit intent (detecta cuando el usuario va a salir)
    let exitIntentShown = false;
    document.addEventListener('mouseleave', (e) => {
        if (e.clientY < 0 && !exitIntentShown) {
            exitIntentShown = true;
            let toast = document.createElement('div');
            toast.textContent = '🔥 ¡No te vayas! Comparte Prisma';
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: #ff4d4d;
                color: white;
                padding: 12px 24px;
                border-radius: 50px;
                font-size: 14px;
                z-index: 10000;
                animation: slideDown 0.3s ease;
            `;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }
    });
    </script>

    <style>
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(100px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    @keyframes slideDown {
        from { transform: translateX(-50%) translateY(-100px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    </style>
    """

# ---------- APLICAR LAS MEJORAS A LOS HTML ----------

# Añadir los elementos virales a index.html
html = html.replace('</body>', generar_widgets_compartir() + generar_scripts_virales() + '</body>')

# Añadir los elementos virales a espana.html
html_espana = html_espana.replace('</body>', generar_widgets_compartir() + generar_scripts_virales() + '</body>')

# Guardar los archivos actualizados
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

with open("espana.html", "w", encoding="utf-8") as f:
    f.write(html_espana)

print("✅ PRISMA VIRAL generado correctamente")
print("📱 Botones flotantes: Twitter, Facebook, WhatsApp, Telegram, Copiar")
print("✨ Animaciones y efectos visuales incluidos")
print("🔥 Exit intent activado")       
print("PRISMA NLP PRO generadom 🚀")
