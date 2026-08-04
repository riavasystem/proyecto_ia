from app.api.v1.routes._crud import build_crud_router
from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchRead, BranchUpdate

router = build_crud_router(
    model=Branch,
    create_schema=BranchCreate,
    update_schema=BranchUpdate,
    read_schema=BranchRead,
    prefix="/branches",
    tags=["branches"],
)
