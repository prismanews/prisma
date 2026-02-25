# ========== CONFIGURACIÓN PRISMA ==========
UMBRAL_CLUSTER = 0.63
UMBRAL_DUPLICADO = 0.87
UMBRAL_AGRUPACION_MIN = 0.5
MAX_NOTICIAS_FEED_ES = 8
MAX_NOTICIAS_FEED_INT = 30
MAX_NOTICIAS_TOTAL = 300
MAX_NOTICIAS_INTERNACIONAL = 40  # ✅ REDUCIDO DE 150 A 30
CACHE_EMBEDDINGS = True
CACHE_FILE = "embeddings_cache.pkl"
LOG_FILE = "prisma.log"

# ✅ NUEVO: Lista negra de medios que rara vez hablan de España
MEDIOS_SOLO_LOCALES = ["La Nación AR", "Folha Brasil", "Clarin", "El Tiempo CO", "Infobae América"]

# ========== KEYWORDS MULTILINGÜES MEJORADAS ==========
KEYWORDS_ESPANA = [
    # Castellano / Español
    "españa", "espana", "español", "española", "españoles",
    "madrid", "barcelona", "valencia", "sevilla", "bilbao",
    "cataluña", "catalunya", "país vasco", "euskadi", "andalucía",
    "galicia", "canarias", "balears", "ibiza", "mallorca",
    "pedro sanchez", "feijoo", "abascal", "yolanda díaz",
    "gobierno español", "moncloa", "congreso", "senado",
    "la liga", "real madrid", "fc barcelona", "atlético",
    
    # English
    "spain", "spanish", "spaniard", "spain's", "spanish prime minister", "pedro sanchez",
    "catalonia", "basque country", "andalusia", "catalan", "basque", "andalusian",
    "spanish government", "prime minister spain", "valencia", "seville",
    "barcelona", "madrid", "real madrid", "fc barcelona",
    
    # Français
    "espagne", "espagnol", "espagnole", "espagnols",
    "catalogne", "pays basque", "andalousie",
    "gouvernement espagnol", "pedro sanchez", "premier ministre espagnol",
    
    # Deutsch
    "spanien", "spanisch", "spanier", "spanische", "spanischer",
    "katalonien", "baskenland", "andalusien",
    "spanische regierung", "ministerpräsident", "madrid", "barcelona",
    
    # Italiano
    "spagna", "spagnolo", "spagnola", "spagnoli",
    "catalogna", "paesi baschi", "andalusia",
    "governo spagnolo", "primo ministro spagnolo",
    
    # Português
    "espanha", "espanhol", "espanhola", "espanhóis",
    "catalunha", "país basco", "andalucia",
    "governo espanhol", "primeiro-ministro espanhol",
    
    # Русский
    "испания", "испанский", "испанская", "испанские",
    "мадрид", "барселона", "каталония",
    "премьер-министр испании", "правительство испании",
    
    # 中文
    "西班牙", "西班牙的", "西班牙人", "西班牙首相", "西班牙政府",
    "马德里", "巴塞罗那", "加泰罗尼亚",
    
    # 日本語
    "スペイン", "スペインの", "スペイン人",
    "マドリード", "バルセロナ", "カタルーニャ",
    "スペイン首相", "スペイン政府",
    
    # 한국어
    "스페인", "스페인의", "스페인 사람",
    "마드리드", "바르셀로나", "카탈루냐",
    "스페인 총리", "스페인 정부",
    
    # العربية
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
