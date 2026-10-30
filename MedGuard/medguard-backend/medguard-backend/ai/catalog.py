"""Versioned first-release medicine catalog and matching helpers."""

CATALOG_VERSION = "2026.1"
MEDICINE_CATALOG = [
    "Acemiz", "Allegra", "Alprax 0-25", "Amalong", "Atarax", "Becozinc", "Bifilac",
    "Canitiz", "Cetzine", "Ciplar 10", "Cofsils", "Cranmed", "Cyclopam", "D-Rise",
    "D-Well", "D3 More 2K", "Dolo-650", "Eldoper", "Emeset", "Etoshine 90",
    "Etoshine MR", "Folvite", "Gelusil", "Gestorab", "GlimiSave M 0-5", "Gluxit10",
    "M-Strong", "Meftal 250 DT", "Melecobalamine", "Menoease", "Metronidazole",
    "Montair", "Muvera", "Mysopas", "P-650", "Pacimol650", "Pan 20", "Pan-D",
    "Paracip-650", "Redotil", "Shelcal 500", "Sibelium 10mg", "Sompraz", "Strepsils",
    "Tayo60k", "Tendonease", "Udapa-Trio", "Unienzyme", "Velgut", "Vitamin E",
    "Vomikind", "Zincovit", "Zofer",
]

def normalize_name(value: str | None) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in (value or "")).split())

def catalog_label_in_text(text: str | None) -> str | None:
    normalized = normalize_name(text)
    for label in sorted(MEDICINE_CATALOG, key=len, reverse=True):
        if normalize_name(label) in normalized:
            return label
    return None
