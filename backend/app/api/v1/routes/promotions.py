from app.api.v1.routes._crud import build_crud_router
from app.models.promotion import Promotion
from app.schemas.promotion import PromotionCreate, PromotionRead, PromotionUpdate

router = build_crud_router(
    model=Promotion,
    create_schema=PromotionCreate,
    update_schema=PromotionUpdate,
    read_schema=PromotionRead,
    prefix="/promotions",
    tags=["promotions"],
)
