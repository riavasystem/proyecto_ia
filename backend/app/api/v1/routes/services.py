from app.api.v1.routes._crud import build_crud_router
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate

router = build_crud_router(
    model=Service,
    create_schema=ServiceCreate,
    update_schema=ServiceUpdate,
    read_schema=ServiceRead,
    prefix="/services",
    tags=["services"],
)
