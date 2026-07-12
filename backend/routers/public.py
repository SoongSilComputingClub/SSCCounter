from fastapi import APIRouter

from services.stats_service import (
    get_current_status_from_db,
    get_today_stats_from_db,
    get_weekly_stats_from_db,
)

router = APIRouter(prefix="/api/v2", tags=["public"])


@router.get("/count/current")
async def get_current_count():
    """
    [프론트엔드용] 현재 동아리방 인원수를 반환합니다.
    """
    return get_current_status_from_db()


@router.get("/stats/today")
async def get_today_stats():
    """
    [프론트엔드용] 오늘 시간대별 인원 통계를 반환합니다.
    """
    return get_today_stats_from_db()


@router.get("/stats/weekly")
async def get_weekly_stats():
    """
    [프론트엔드용] 평일 시간대별 평균 통계를 반환합니다.
    """
    return get_weekly_stats_from_db()
