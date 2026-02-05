import feedparser
from datetime import datetime

feeds = {
    # Nacionales principales
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

    # Económicos
    "Expansión": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "El Economista": "https://www.eleconomista.es/rss/rss.html",
    "Cinco Días": "https://cincodias.elpais.com/seccion/rss/portada/",

    # Regionales importantes
    "La Voz de Galicia": "https://www.lavozdegalicia.es/rss/portada.xml",
    "Faro de Vigo": "https://www.farodevigo.es/rss/portada.xml",
    "El Correo": "https://www.elcorreo.com/rss/portada.xml",
    "Diario Vasco": "https://www.diariovasco.com/rss/portada.xml",
    "Heraldo": "https://www.heraldo.es/rss/portada/",
    "Levante": "https://www.levante-emv.com/rss/portada.xml",
    "La Nueva España": "https://www.lne.es/rss/portada.xml",
    "Diario de Sevilla": "https://www.diariodesevilla.es/rss/",
    "Ideal": "https://www.ideal.es/rss/portada.xml",
    "Sur": "https://www.diariosur.es/rss/portada.xml"
}

html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Hoy · Prisma</title>
<link rel="stylesheet" href="../prisma.css">
</head>
<body>
<header>
<h1>Hoy</h1>
<p>Comparativa automática · {}</p>
</header>
<nav>
<a href="../">Inicio</a>
<a href="../archivo/">Archivo</a>
</nav>
<div class="container">
""".format(datetime.now().strftime("%d/%m/%Y %H:%M"))

for medio, url in feeds.items():
    feed = feedparser.parse(url)
    if feed.entries:
        noticia = feed.entries[0]
        html += f"""
        <div class="card">
        <h2>{medio}</h2>
        <p>{noticia.title}</p>
        <a href="{noticia.link}" target="_blank">Leer noticia →</a>
        </div>
        """

html += "</div></body></html>"

with open("hoy/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Página generada")
