import feedparser
from datetime import datetime
from difflib import SequenceMatcher

# ----------------------------
# RSS PERIÓDICOS
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
    "Europa Press": "https://www.europapress.es/rss/rss.aspx"
}

# ----------------------------
# SIMILITUD TITULARES
# ----------------------------

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ----------------------------
# LEER RSS
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
    except:
        pass


# ----------------------------
# AGRUPAR NOTICIAS
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

grupos.sort(key=len, reverse=True)


# ----------------------------
# GENERAR HTML PORTADA
# ----------------------------

fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Prisma</title>
<link rel="stylesheet" href="prisma.css">
<style>
body{{font-family:system-ui;max-width:900px;margin:auto;padding:40px}}
.card{{background:#f7f7f7;padding:20px;border-radius:12px;margin:20px 0}}
h1{{text-align:center}}
</style>
</head>
<body>

<h1>PRISMA</h1>
<p style="text-align:center">
La misma noticia observada desde distintos ángulos<br>
Actualizado: {fecha}
</p>
"""

for grupo in grupos[:5]:  # Top 5 noticias principales
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

html += "</body></html>"


# ----------------------------
# GUARDAR PORTADA
# ----------------------------

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Portada Prisma actualizada")
