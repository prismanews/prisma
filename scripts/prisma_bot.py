
import feedparser
from datetime import datetime

# RSS medios españoles iniciales
feeds = [
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "https://www.abc.es/rss/feeds/abcPortada.xml"
]

noticias = []

for feed in feeds:
    f = feedparser.parse(feed)
    for entry in f.entries[:3]:
        noticias.append(entry.title)

html = f"""
<html>
<head>
<meta charset="UTF-8">
<title>Prisma Hoy</title>
</head>
<body>
<h1>Prisma Hoy</h1>
<p>Actualizado: {datetime.now()}</p>
<ul>
{''.join(f'<li>{n}</li>' for n in noticias)}
</ul>
</body>
</html>
"""

with open("hoy/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Página actualizada")
