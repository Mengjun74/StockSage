from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.pipelines.evaluation import EvaluationPipeline
from app.schemas.evaluation import PerformanceReport


router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("", response_model=PerformanceReport)
async def get_performance(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PerformanceReport:
    """How past calls actually turned out.

    Reads scored outcomes only; scoring itself runs as a job, so asking this question
    never changes the answer.
    """
    return await EvaluationPipeline().report(session)
