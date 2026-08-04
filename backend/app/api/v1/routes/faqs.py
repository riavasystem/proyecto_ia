from app.api.v1.routes._crud import build_crud_router
from app.models.faq import FAQ
from app.schemas.faq import FAQCreate, FAQRead, FAQUpdate

router = build_crud_router(
    model=FAQ,
    create_schema=FAQCreate,
    update_schema=FAQUpdate,
    read_schema=FAQRead,
    prefix="/faqs",
    tags=["faqs"],
)
