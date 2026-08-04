from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.db.session import get_db
from app.plugins_runtime.manager import manager
from app.schemas.plugin import PluginExecuteRequest, PluginExecuteResponse

router = APIRouter(prefix="/plugins", tags=["plugins"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/{name}/execute",
    response_model=PluginExecuteResponse,
    dependencies=[Depends(require_scope("plugins:execute")), Depends(enforce_rate_limit)],
)
async def execute_plugin(
    name: str, payload: PluginExecuteRequest, company_id: CurrentCompanyId, db: DbSession
) -> PluginExecuteResponse:
    result = await manager.execute(db, company_id, name, payload.action, payload.payload)
    return PluginExecuteResponse(success=result.success, message=result.message, data=result.data)
