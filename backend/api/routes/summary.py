from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from models.database import SummaryModel
from services.summarizer import SummarizerService
from config.settings import settings

router = APIRouter()
summarizer = SummarizerService()


@router.get("/today")
async def get_today_summary():
    try:
        summary = await SummaryModel.get_today()
        if not summary:
            return {"message": "No summary available for today yet", "summary": None}
        return _format_summary(summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date/{date}")
async def get_summary_by_date(date: str):
    """Get summary for specific date (YYYY-MM-DD)"""
    try:
        date_obj = datetime.fromisoformat(date)
        summary = await SummaryModel.get_by_date(date_obj)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for {date}"
            )
        
        return _format_summary(summary)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_summaries(limit: int = 7):
    """Get recent daily summaries"""
    try:
        summaries = await SummaryModel.get_recent(limit)
        
        return {
            "summaries": [_format_summary(s) for s in summaries],
            "count": len(summaries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_summary(
    background_tasks: BackgroundTasks,
    date: Optional[str] = None
):
    """Generate daily summary (async background task)"""
    try:
        date_obj = datetime.fromisoformat(date) if date else datetime.utcnow()
        
        # Run generation in background
        background_tasks.add_task(summarizer.generate_daily_summary, date_obj)
        
        return {
            "message": "Summary generation started",
            "date": date_obj.date().isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/sync")
async def generate_summary_sync(date: Optional[str] = None):
    """Generate daily summary (synchronous - wait for completion)"""
    try:
        date_obj = datetime.fromisoformat(date) if date else datetime.utcnow()
        
        result = await summarizer.generate_daily_summary(date_obj)
        
        return {
            "message": "Summary generated successfully",
            "date": date_obj.date().isoformat(),
            "summary": result
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_summary(summary: dict) -> dict:
    tz = ZoneInfo(getattr(settings, "CAMERA_TIMEZONE", "UTC"))
    utc = ZoneInfo("UTC")
    gen = summary.get('generated_at')
    if gen and gen.tzinfo is None:
        gen = gen.replace(tzinfo=utc)
    gen_local = gen.astimezone(tz) if gen else None
    return {
        "id": str(summary['_id']),
        "date": summary['date'].date().isoformat(),
        "summary": summary['summary'],
        "events_count": summary['events_count'],
        "key_events": summary['key_events'],
        "statistics": summary['statistics'],
        "generated_at": gen_local.isoformat() if gen_local else None
    }
