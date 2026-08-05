from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.db.session import get_db
from app.plugins_runtime.manager import manager
from app.schemas.plugin import PluginExecuteRequest, PluginExecuteResponse
from app.services.webhooks import emit_event

router = APIRouter(prefix="/plugins", tags=["plugins"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/{name}/execute",
    response_model=PluginExecuteResponse,
    dependencies=[Depends(require_scope("plugins:execute")), Depends(enforce_rate_limit)],
)
async def execute_plugin(
    name: str,
    payload: PluginExecuteRequest,
    company_id: CurrentCompanyId,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> PluginExecuteResponse:
    result = await manager.execute(db, company_id, name, payload.action, payload.payload)
    await emit_event(
        db,
        background_tasks,
        company_id,
        "plugin.executed",
        {
            "plugin": name,
            "action": payload.action,
            "success": result.success,
            "message": result.message,
        },
    )
    return PluginExecuteResponse(success=result.success, message=result.message, data=result.data)
