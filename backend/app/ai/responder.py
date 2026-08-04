from app.models.company import Company
from app.models.faq import FAQ
from app.models.product import Product
from app.models.promotion import Promotion
from app.models.schedule import BusinessHour
from app.models.service import Service

_DAY_NAMES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def greeting(company: Company | None) -> str:
    name = company.name if company else "la empresa"
    return f"¡Hola! Soy el asistente de {name}. ¿En qué te puedo ayudar?"


def services_reply(services: list[Service]) -> str:
    if not services:
        return "Por el momento no tenemos servicios cargados en el sistema."
    lines = [
        f"- {s.name}" + (f": ${s.price:,.0f}" if s.price is not None else "") for s in services
    ]
    return "Estos son nuestros servicios disponibles:\n" + "\n".join(lines)


def products_reply(products: list[Product]) -> str:
    if not products:
        return "Por el momento no tenemos productos cargados en el sistema."
    lines = [
        f"- {p.name}" + (f": ${p.price:,.0f}" if p.price is not None else "") for p in products
    ]
    return "Estos son nuestros productos disponibles:\n" + "\n".join(lines)


def schedule_reply(hours: list[BusinessHour]) -> str:
    if not hours:
        return "Todavía no tenemos un horario de atención cargado en el sistema."
    lines = [
        f"- {_DAY_NAMES[h.day_of_week]}: {h.opens_at:%H:%M} a {h.closes_at:%H:%M}" for h in hours
    ]
    return "Nuestro horario de atención es:\n" + "\n".join(lines)


def promotions_reply(promotions: list[Promotion]) -> str:
    if not promotions:
        return "Por el momento no tenemos promociones activas."
    lines = [f"- {p.name}" + (f": {p.description}" if p.description else "") for p in promotions]
    return "Estas son nuestras promociones vigentes:\n" + "\n".join(lines)


def policies_reply(policies: list) -> str:  # type: ignore[type-arg]
    if not policies:
        return "Todavía no tenemos políticas cargadas en el sistema."
    lines = [f"- {p.type}: {p.content}" for p in policies]
    return "Esta es nuestra información sobre políticas:\n" + "\n".join(lines)


def faq_reply(faq: FAQ) -> str:
    return faq.answer


def unknown_reply() -> str:
    return (
        "No estoy seguro de haber entendido tu mensaje. Puedo ayudarte con información sobre "
        "nuestros servicios, productos, horarios, promociones o políticas."
    )
