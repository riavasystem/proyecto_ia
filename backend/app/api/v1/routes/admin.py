from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    branches,
    faqs,
    policies,
    products,
    promotions,
    schedule,
    services,
)

router = APIRouter(prefix="/admin")
router.include_router(auth.router)
router.include_router(services.router)
router.include_router(products.router)
router.include_router(branches.router)
router.include_router(schedule.router)
router.include_router(promotions.router)
router.include_router(policies.router)
router.include_router(faqs.router)
