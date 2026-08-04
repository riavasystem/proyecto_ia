from fastapi import APIRouter

from app.api.v1.routes import (
    api_keys,
    auth,
    branches,
    company,
    conversations_admin,
    faqs,
    plugins_admin,
    policies,
    products,
    promotions,
    schedule,
    services,
)

router = APIRouter(prefix="/admin")
router.include_router(auth.router)
router.include_router(company.router)
router.include_router(api_keys.router)
router.include_router(services.router)
router.include_router(products.router)
router.include_router(branches.router)
router.include_router(schedule.router)
router.include_router(promotions.router)
router.include_router(policies.router)
router.include_router(faqs.router)
router.include_router(conversations_admin.router)
router.include_router(plugins_admin.router)
