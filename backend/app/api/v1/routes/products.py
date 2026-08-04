from app.api.v1.routes._crud import build_crud_router
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = build_crud_router(
    model=Product,
    create_schema=ProductCreate,
    update_schema=ProductUpdate,
    read_schema=ProductRead,
    prefix="/products",
    tags=["products"],
)
