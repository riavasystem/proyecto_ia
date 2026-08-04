from app.api.v1.routes._crud import build_crud_router
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyRead, PolicyUpdate

router = build_crud_router(
    model=Policy,
    create_schema=PolicyCreate,
    update_schema=PolicyUpdate,
    read_schema=PolicyRead,
    prefix="/policies",
    tags=["policies"],
)
