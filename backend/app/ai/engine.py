from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import responder
from app.ai.faq_matcher import find_best_faq_match
from app.ai.intent import Intent, detect_intent, fold
from app.models.company import Company
from app.models.faq import FAQ
from app.models.installed_plugin import InstalledPlugin
from app.models.policy import Policy
from app.models.product import Product
from app.models.promotion import Promotion
from app.models.schedule import BusinessHour
from app.models.service import Service
from app.plugins_runtime.manager import manager as plugin_manager
from app.plugins_runtime.registry import registry as plugin_registry


@dataclass
class AIReply:
    intent: Intent
    text: str


async def _try_plugins(db: AsyncSession, company_id: UUID, message: str) -> AIReply | None:
    """Sección 7 del CLAUDE.md: "determinar si debe ejecutarse un plugin".
    El Core no conoce la lógica de ningún plugin — solo compara el mensaje
    contra los chat_triggers que cada plugin declaró en su manifiesto, y si
    hay match delega la respuesta completa al plugin (acción "chat")."""
    installed = (
        (
            await db.execute(
                select(InstalledPlugin).where(
                    InstalledPlugin.company_id == company_id,
                    InstalledPlugin.is_enabled.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    if not installed:
        return None

    folded = fold(message)
    for installation in installed:
        plugin_manifest = plugin_registry.get_manifest(installation.plugin_name)
        if plugin_manifest is None:
            continue
        if not any(fold(trigger) in folded for trigger in plugin_manifest.chat_triggers):
            continue

        result = await plugin_manager.execute(
            db, company_id, installation.plugin_name, "chat", {"message": message}
        )
        if result.success and result.message:
            return AIReply(intent=Intent.PLUGIN, text=result.message)
    return None


async def process_message(db: AsyncSession, company_id: UUID, message: str) -> AIReply:
    """Intención → consultar información estructurada del tenant → determinar
    si debe ejecutarse un plugin → construir respuesta. Sin RAG, sin
    embeddings: todo sale de PostgreSQL filtrado por company_id, según la
    sección 1 del CLAUDE.md."""
    faqs = (await db.execute(select(FAQ).where(FAQ.company_id == company_id))).scalars().all()
    faq_match = find_best_faq_match(message, list(faqs))
    if faq_match is not None:
        return AIReply(intent=Intent.FAQ, text=responder.faq_reply(faq_match))

    plugin_reply = await _try_plugins(db, company_id, message)
    if plugin_reply is not None:
        return plugin_reply

    intent = detect_intent(message)

    if intent is Intent.GREETING:
        company = await db.get(Company, company_id)
        return AIReply(intent=intent, text=responder.greeting(company))

    if intent is Intent.SERVICES:
        services_result = await db.execute(
            select(Service).where(Service.company_id == company_id, Service.is_active.is_(True))
        )
        services = list(services_result.scalars().all())
        return AIReply(intent=intent, text=responder.services_reply(services))

    if intent is Intent.PRODUCTS:
        products_result = await db.execute(
            select(Product).where(Product.company_id == company_id, Product.is_active.is_(True))
        )
        products = list(products_result.scalars().all())
        return AIReply(intent=intent, text=responder.products_reply(products))

    if intent is Intent.SCHEDULE:
        hours_result = await db.execute(
            select(BusinessHour)
            .where(BusinessHour.company_id == company_id)
            .order_by(BusinessHour.day_of_week)
        )
        hours = list(hours_result.scalars().all())
        return AIReply(intent=intent, text=responder.schedule_reply(hours))

    if intent is Intent.PROMOTIONS:
        today = date.today()
        promotions_result = await db.execute(
            select(Promotion).where(
                Promotion.company_id == company_id,
                Promotion.is_active.is_(True),
                (Promotion.starts_on.is_(None)) | (Promotion.starts_on <= today),
                (Promotion.ends_on.is_(None)) | (Promotion.ends_on >= today),
            )
        )
        promotions = list(promotions_result.scalars().all())
        return AIReply(intent=intent, text=responder.promotions_reply(promotions))

    if intent is Intent.POLICIES:
        policies_result = await db.execute(select(Policy).where(Policy.company_id == company_id))
        policies = list(policies_result.scalars().all())
        return AIReply(intent=intent, text=responder.policies_reply(policies))

    return AIReply(intent=Intent.UNKNOWN, text=responder.unknown_reply())
