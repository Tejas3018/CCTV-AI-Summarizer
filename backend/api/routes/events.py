from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
import os

from models.database import EventModel, Database
from config.settings import settings
from zoneinfo import ZoneInfo

router = APIRouter()


@router.get("/")
async def list_events(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """List recent events"""
    try:
        events = await EventModel.get_recent(limit + skip)
        events = events[skip:]
        
        return {
            "events": [_format_event(e) for e in events],
            "count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today")
async def get_today_events():
    """Get today's events"""
    try:
        events = await EventModel.get_today()
        
        return {
            "events": [_format_event(e) for e in events],
            "count": len(events),
            "date": datetime.utcnow().date().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/range")
async def get_events_by_range(
    start: str = Query(..., description="Start datetime (ISO format)"),
    end: str = Query(..., description="End datetime (ISO format)")
):
    """Get events in date range"""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        
        events = await EventModel.get_by_date_range(start_dt, end_dt)
        
        return {
            "events": [_format_event(e) for e in events],
            "count": len(events),
            "start": start,
            "end": end
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}")
async def get_event(event_id: str):
    """Get specific event by ID"""
    try:
        event = await EventModel.get_by_id(event_id)
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return _format_event(event)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clip/{event_id}")
async def get_event_clip(event_id: str):
    """Stream event video clip"""
    try:
        event = await EventModel.get_by_id(event_id)
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        clip_filename = event.get('clip_path')
        if not clip_filename:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        clip_path = os.path.join(settings.CLIPS_STORAGE_PATH, clip_filename)
        
        if not os.path.exists(clip_path):
            raise HTTPException(status_code=404, detail="Clip file not found")
        
        return FileResponse(
            clip_path,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename={clip_filename}"
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thumbnail/{event_id}")
async def get_event_thumbnail(event_id: str):
    """Get event thumbnail image"""
    try:
        event = await EventModel.get_by_id(event_id)
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        thumbnail_filename = event.get('thumbnail_path')
        if not thumbnail_filename:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        thumbnail_path = os.path.join(settings.THUMBNAILS_PATH, thumbnail_filename)
        
        if not os.path.exists(thumbnail_path):
            raise HTTPException(status_code=404, detail="Thumbnail file not found")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            thumbnail_path,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename={thumbnail_filename}"
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/day")
async def get_stats_by_day(
    date: str = Query(..., description="Date (YYYY-MM-DD)")
):
    try:
        tz_name = getattr(settings, "CAMERA_TIMEZONE", "UTC")
        cam_tz = ZoneInfo(tz_name)
        utc_tz = ZoneInfo("UTC")
        date_obj = datetime.fromisoformat(date)
        start_cam = datetime(
            year=date_obj.year,
            month=date_obj.month,
            day=date_obj.day,
            tzinfo=cam_tz,
        )
        end_cam = start_cam + timedelta(days=1)
        start = start_cam.astimezone(utc_tz).replace(tzinfo=None)
        end = end_cam.astimezone(utc_tz).replace(tzinfo=None)
        events = await EventModel.get_by_date_range(start, end)
        by_type: dict[str, int] = {}
        hourly: dict[int, int] = {}
        for event in events:
            t = event.get('detection_type', '').lower()
            if t:
                by_type[t] = by_type.get(t, 0) + 1
            hour = event['timestamp'].hour
            hourly[hour] = hourly.get(hour, 0) + 1
        people_breakdown = {
            "male": 0,
            "female": 0,
            "kid": 0,
            "person": 0,
            "total": 0,
        }
        for e in events:
            t = e.get('detection_type', '').lower()
            if t in people_breakdown:
                people_breakdown[t] += 1
        people_breakdown["total"] = sum(people_breakdown[k] for k in ("person", "male", "female", "kid"))
        return {
            "total": len(events),
            "by_type": by_type,
            "hourly_distribution": hourly,
            "people_breakdown": people_breakdown,
            "date": date_obj.date().isoformat(),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/today")
async def get_today_stats():
    try:
        events = await EventModel.get_today()
        by_type: dict[str, int] = {}
        hourly: dict[int, int] = {}
        for event in events:
            t = event.get('detection_type', '').lower()
            if t:
                by_type[t] = by_type.get(t, 0) + 1
            hour = event['timestamp'].hour
            hourly[hour] = hourly.get(hour, 0) + 1
        people_breakdown = {
            "male": 0,
            "female": 0,
            "kid": 0,
            "person": 0,
            "total": 0,
        }
        for e in events:
            t = e.get('detection_type', '').lower()
            if t in people_breakdown:
                people_breakdown[t] += 1
        people_breakdown["total"] = sum(people_breakdown[k] for k in ("person", "male", "female", "kid"))
        tz_name = getattr(settings, "CAMERA_TIMEZONE", "UTC")
        try:
            cam_tz = ZoneInfo(tz_name)
            date_val = datetime.now(cam_tz).date().isoformat()
        except Exception:
            date_val = datetime.utcnow().date().isoformat()
        return {
            "total": len(events),
            "by_type": by_type,
            "hourly_distribution": hourly,
            "people_breakdown": people_breakdown,
            "date": date_val,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_event(event: dict) -> dict:
    tz_name = getattr(settings, "CAMERA_TIMEZONE", "UTC")
    try:
        cam_tz = ZoneInfo(tz_name)
        utc_tz = ZoneInfo("UTC")
        ts = event['timestamp']
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=utc_tz)
        local_ts = ts.astimezone(cam_tz)
    except Exception:
        offset_min = getattr(settings, "CAMERA_TIME_OFFSET_MINUTES", 0)
        local_ts = event['timestamp'] + timedelta(minutes=offset_min)
    return {
        "id": str(event['_id']),
        "timestamp": local_ts.isoformat(),
        "camera_id": event['camera_id'],
        "detection_type": event['detection_type'],
        "confidence": event['confidence'],
        "bounding_box": event['bounding_box'],
        "clip_url": f"/api/events/clip/{event['_id']}" if event.get('clip_path') else None,
        "thumbnail_url": f"/api/events/thumbnail/{event['_id']}" if event.get('thumbnail_path') else None,
        "metadata": event.get('metadata', {})
    }
