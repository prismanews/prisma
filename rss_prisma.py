import feedparser
import re
from datetime import datetime
from collections import Counter

# IA embeddings reales
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# modelo semántico (ligero y muy bueno)
modelo = SentenceTransformer('all-MiniLM-L6-v2')


# ---------------- FEEDS ----------------

feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "OK Diario": "https://okdiario.com/feed/",
    "Libertad Digital": "https://www.libertaddigital.com/rss/",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "La Sexta": "https://www.lasexta.com/rss.xml",
    "La Razón": "https://www.larazon.es/rss/",
    "El Español": "https://www.elespanol.com/rss/",
    "RTVE": "https://www.rtve.es/rss/",
    "Expansión": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "Cinco Días": "https://cincodias.elpais.com/seccion/rss/portada/",
    "El Periódico de España": "https://www.epe.es/rss/portada.xml",
    "Infolibre": "https://www.infolibre.es/rss/",
    "Vozpópuli": "https://www.vozpopuli.com/rss/",
    "El Independiente": "https://www.elindependiente.com/rss/",
    "El Debate": "https://www.eldebate.com/rss/",
    "Servimedia": "https://www.servimedia.es/rss",
    "The Objective": "https://theobjective.com/feed/",
    "Xataka": "https://www.xataka.com/feed.xml",
    "Hipertextual": "https://hipertextual.com/feed",
    "Genbeta": "https://www.genbeta.com/feed.xml",
    "El Androide Libre": "https://www.elespanol.com/elandroidelibre/rss/",
    "CTXT": "https://ctxt.es/rss.xml",
    "Nuevatribuna": "https://www.nuevatribuna.es/rss/",
    "BBC Mundo": "https://feeds.bbci.co.uk/mundo/rss.xml",
    "France24 Español": "https://www.france24.com/es/rss",
    "DW Español": "https://rss.dw.com/xml/rss-es-all",

    # Regional
    "La Voz de Galicia": "https://www.lavozdegalicia.es/rss/portada.xml",
    "El Periódico de Extremadura": "https://www.elperiodicoextremadura.com/rss/portada.xml",
    "La Nueva España": "https://www.lne.es/rss/portada.xml",
    "Heraldo de Aragón": "https://www.heraldo.es/rss/portada/",
    "El Periódico de Catalunya": "https://www.elperiodico.com/es/rss/rss_portada.xml",
    "Levante EMV": "https://www.levante-emv.com/rss/portada.xml",
    "Diario de Sevilla": "https://www.diariodesevilla.es/rss/",
    "Diario de Cádiz": "https://www.diariodecadiz.es/rss/",
    "El Periódico de Aragón": "https://www.elperiodicodearagon.com/rss/portada.xml",
    "El Correo": "https://www.elcorreo.com/rss/portada.xml",
    "Diario Vasco": "https://www.diariovasco.com/rss/portada.xml",
    "Sur": "https://www.diariosur.es/rss/portada.xml",
    "La Opinión de Málaga": "https://www.laopiniondemalaga.es/rss/portada.xml",

    # Deportes
    "AS": "https://as.com/rss/tags/ultimas_noticias.xml",
    "Marca": "https://e00-marca.uecdn.es/rss/portada.xml",
}


# ---------------- LIMPIAR TEXTO ----------------

stopwords = {
    "el","la","los","las","de","del","en","para","por","con",
    "sin","un","una","unos","unas","al","a","y","o","que",
    "se","su","sus","ante","como","más","menos"
}

def limpiar(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    palabras = texto.split()
    return [p for p in palabras if p not in stopwords and len(p) > 3]


# ---------------- IA SEMÁNTICA ----------------

def similares(t1, t2):
    emb = modelo.encode([t1, t2])
    score = cosine_similarity([emb[0]], [emb[1]])[0][0]
    return score > 0.55


# ---------------- TEMA DOMINANTE ----------------

def tema_dominante(grupo):
    palabras = []
    for n in grupo:
        palabras += limpiar(n["titulo"])

    comunes = Counter(palabras).most_common(2)
    return " / ".join(p for p, _ in comunes) if comunes else ""


def resumen_ia(grupo):
    palabras = []
    for n in grupo:
        palabras += limpiar(n["titulo"])

    comunes = Counter(palabras).most_common(3)
    if not comunes:
        return ""

    tema = ", ".join(p for p, _ in comunes)

    return f"""
    <div class="resumen">
    <strong>Lectura IA:</strong>
    La noticia gira en torno a <b>{tema}</b>.
    </div>
    """


# ---------------- RECOGER NOTICIAS ----------------

noticias = []

for medio, url in feeds.items():
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            noticias.append({
                "medio": medio,
                "titulo": feed.entries[0].title,
                "link": feed.entries[0].link
            })
    except:
        pass


# ---------------- CLUSTERING IA ----------------

grupos = []

for noticia in noticias:

    if not grupos:
        grupos.append([noticia])
        continue

    mejor_grupo = None
    mejor_score = 0

    for grupo in grupos:
        emb = modelo.encode([noticia["titulo"], grupo[0]["titulo"]])
        score = cosine_similarity([emb[0]], [emb[1]])[0][0]

        if score > mejor_score:
            mejor_score = score
            mejor_grupo = grupo

    if mejor_score > 0.55:
        mejor_grupo.append(noticia)
    else:
        grupos.append([noticia])


# ordenar impacto
grupos.sort(key=len, reverse=True)

max_medios = max(len(g) for g in grupos)
total_medios = sum(len(g) for g in grupos)


# ---------------- HTML ----------------

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma</title>
<link rel="stylesheet" href="prisma.css">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header class="cabecera">
<h1><img src="Logo.PNG" class="logo-inline"> PRISMA</h1>
<p>Más contexto menos ruido. La actualidad sin sesgos</p>
<p>Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
<div class="contador">📰 {total_medios} medios analizados hoy</div>
</header>

<div class="container">
"""


for i, grupo in enumerate(grupos, 1):

    tema = tema_dominante(grupo)

    html += "<div class='card'>"

    if len(grupo) > 1:
        html += f"<div class='ranking'>#{i} noticia del día</div>"

    if len(grupo) == max_medios and len(grupo) > 1:
        html += "<div class='trending'>🔥 Trending</div>"

    num = len(grupo)

    consenso = (
        "🟢 Consenso alto" if num >= 4 else
        "🟡 Cobertura variada" if num >= 2 else
        "🔴 Solo un medio"
    )

    html += f"<div class='consenso'>{consenso} — {num} medios</div>"
    html += f"<h2>{max(grupo, key=lambda n: len(n['titulo']))['titulo']}</h2>"
    html += f"<div class='tema'>🧭 Tema: {tema}</div>"

    if num > 1:
        html += resumen_ia(grupo)

    for n in grupo:
        html += f"""
        <p><strong class="medio">{n['medio']}:</strong>
        <a href="{n['link']}" target="_blank">{n['titulo']}</a></p>
        """

    html += "</div>"

html += "</div></body></html>"


with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("PRISMA generado con clustering IA semántico")
