import feedparser
import re
import html
import random
from datetime import datetime
from collections import Counter
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------- CONFIG PRO ----------

UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
MAX_NOTICIAS_FEED = 8
MAX_FEED_INTERNACIONAL = 6   # ⭐ optimización rendimiento

modelo = SentenceTransformer("all-MiniLM-L6-v2")


# ---------- REFERENCIAS SESGO IA ----------

referencias_politicas = {
    "progresista": modelo.encode([
        "derechos sociales igualdad feminismo políticas públicas diversidad justicia social bienestar",
        "progresismo cambio climático políticas sociales regulación inclusión servicios públicos"
    ]),
    "conservador": modelo.encode([
        "seguridad fronteras defensa tradición economía mercado estabilidad control migratorio",
        "valores tradicionales seguridad nacional impuestos bajos orden liberalismo económico"
    ])
}


# ---------- FEEDS PORTADA ----------

feeds_es = {
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
    "Jacobin": "https://jacobin.com/feed"
}


# ---------- FEEDS INTERNACIONALES SOLO ESPAÑA ----------

feeds_internacionales = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=world",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Guardian": "https://www.theguardian.com/world/rss",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "Financial Times": "https://www.ft.com/world?format=rss",
    "Le Monde": "https://www.lemonde.fr/rss/une.xml",
    "France24 FR": "https://www.france24.com/fr/rss",
    "Le Figaro": "https://www.lefigaro.fr/rss/figaro_actualites.xml",
    "Der Spiegel": "https://www.spiegel.de/international/index.rss",
    "Die Welt": "https://www.welt.de/feeds/latest.rss",
    "Corriere": "https://xml2.corriereobjects.it/rss/homepage.xml",
    "La Repubblica": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
    "Publico PT": "https://www.publico.pt/rss",
    "Folha Brasil": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
    "Politico EU": "https://www.politico.eu/feed/",
    "Euronews": "https://www.euronews.com/rss?level=theme&name=news",
    "OpenDemocracy": "https://www.opendemocracy.net/en/rss.xml",
    "SCMP Hong Kong": "https://www.scmp.com/rss/91/feed",
    "Japan Times": "https://www.japantimes.co.jp/feed/",
    "China Daily": "http://www.chinadaily.com.cn/rss/world_rss.xml",
    "Clarin": "https://www.clarin.com/rss/lo-ultimo/",
    "El Tiempo CO": "https://www.eltiempo.com/rss/colombia.xml",
    "Granma": "http://www.granma.cu/feed",
    "Cubadebate": "http://www.cubadebate.cu/feed/",
    "Prensa Latina": "https://www.prensa-latina.cu/feed/"
}


# ---------- KEYWORDS MEJORADAS ESPAÑA ----------

KEYWORDS_ESPANA = [
    "españa","espana","spain","espagne","spanien","spagna",
    "spanish","español","spania","espanha",
    "iberia","iberian",
    "madrid","barcelona","catalonia",
    "andalusia","valencia","canary",
    "spaniard","spaniards"
]


# ---------- LIMPIEZA ----------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos","tras"
}

def limpiar_html(texto):
    texto = html.unescape(texto)
    texto = re.sub(r'<.*?>', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return [p for p in palabras if p not in stopwords and len(p) > 3]


# ---------- RECOGER PORTADA ----------

noticias = []

for medio, url in feeds_es.items():
    feed = feedparser.parse(url)

    # ⭐ evita feeds rotos o vacíos
    if feed.bozo or not feed.entries:
        continue

    for entry in feed.entries[:MAX_NOTICIAS_FEED]:
        if "title" in entry and "link" in entry:
            noticias.append({
                "medio": medio,
                "titulo": limpiar_html(entry.title),
                "link": entry.link.strip()
            })

# quitar duplicados URL
noticias = list({n["link"]: n for n in noticias}.values())


# ---------- INTERNACIONAL SOLO ESPAÑA ----------

noticias_espana = []

for medio, url in feeds_internacionales.items():
    feed = feedparser.parse(url)

    if feed.bozo or not feed.entries:
        continue

    for entry in feed.entries[:MAX_FEED_INTERNACIONAL]:
        titulo = limpiar_html(entry.title)

        if any(k in titulo.lower() for k in KEYWORDS_ESPANA):
            noticias_espana.append({
                "medio": medio,
                "titulo": titulo,
                "link": entry.link
            })

# quitar duplicados internacionales
noticias_espana = list({n["link"]: n for n in noticias_espana}.values())


print("Noticias portada:", len(noticias))
print("Noticias España internacional:", len(noticias_espana))
