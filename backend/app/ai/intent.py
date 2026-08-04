import unicodedata
from enum import StrEnum

# Palabras clave por intención. El orden de INTENT_KEYWORDS define la prioridad
# cuando un mensaje matchea más de una categoría.


class Intent(StrEnum):
    GREETING = "greeting"
    SCHEDULE = "schedule"
    SERVICES = "services"
    PRODUCTS = "products"
    PROMOTIONS = "promotions"
    POLICIES = "policies"
    FAQ = "faq"
    UNKNOWN = "unknown"


INTENT_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.SCHEDULE: ("horario", "hora", "abren", "cierran", "atienden", "atencion", "abierto"),
    Intent.SERVICES: ("servicio", "precio", "costo", "cuesta", "valor", "cotizar", "cotizacion"),
    Intent.PRODUCTS: ("producto", "stock", "disponible", "comprar", "codigo"),
    Intent.PROMOTIONS: ("promocion", "descuento", "oferta", "rebaja"),
    Intent.POLICIES: (
        "politica",
        "garantia",
        "devolucion",
        "reembolso",
        "pago",
        "reserva",
        "cancelacion",
        "privacidad",
    ),
    Intent.GREETING: ("hola", "buenas", "buen dia", "buenos dias", "que tal", "hey"),
}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in normalized if not unicodedata.combining(c))


def detect_intent(message: str) -> Intent:
    folded = _fold(message)
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in folded for keyword in keywords):
            return intent
    return Intent.UNKNOWN
