import feedparser
from datetime import datetime
from difflib import SequenceMatcher
import os

# ----------------------------
# FUENTES RSS (puedes ampliar)
# ----------------------------

feeds = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "ABC": "https://www.abc.es/rss/feeds/abcPortada.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20 Minutos": "https://www.20minutos.es/rss/",
    "eldiario.es": "https://www.eldiario.es/rss/",
    "RTVE": "https://www.rtve.es/rss/portada.xml",
    "El Confidencial": "https://www.elconfidencial.com/rss/",
    "Público": "https://www.publico.es/rss/",
    "La Razón": "https://www.larazon.es/rss/",
    "OK Diario": "https://okdiario.com/feed/",
    "Libertad Digital": "https://www.libertaddigital.com/rss/portada.xml",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx"
}

# ----------------------------
# SIMILITUD TITULARES
# ----------------------------

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ----------------------------
# CARGAR NOTICIAS RSS
# ----------------------------

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
    except Exception as e:
        print(f"Error en {medio}: {e}")


# ----------------------------
# AGRUPAR NOTICIAS SIMILARES
# ----------------------------

grupos = []

for noticia in noticias:
    añadido = False

    for grupo in grupos:
        if similar(noticia["titulo"], grupo[0]["titulo"]) > 0.55:
            grupo.append(noticia)
            añadido = True
            break

    if not añadido:
        grupos.append([noticia])


# Ordenar por relevancia (más medios = primero)
grupos.sort(key=len, reverse=True)


# ----------------------------
# GENERAR HTML
# ----------------------------

fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Hoy · Prisma</title>
<link rel="stylesheet" href="../prisma.css">
</head>
<body>

<header>
<h1>Hoy</h1>
<p>Comparativa automática · {fecha}</p>
<nav>
<a href="../">Inicio</a>
<a href="../archivo/">Archivo</a>
</nav>
</header>

<div class="container">
"""


for grupo in grupos:
    html += "<div class='card'>"

    html += "<h2>Comparativa de medios</h2>"

    for noticia in grupo:
        html += f"""
        <p>
        <strong>{noticia['medio']}:</strong>
        <a href="{noticia['link']}" target="_blank">
        {noticia['titulo']}
        </a>
        </p>
        """

    html += "</div>"


html += """
</div>
</body>
</html>
"""


# ----------------------------
# GUARDAR ARCHIVO
# ----------------------------

os.makedirs("hoy", exist_ok=True)

with open("hoy/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Página generada correctamente")
