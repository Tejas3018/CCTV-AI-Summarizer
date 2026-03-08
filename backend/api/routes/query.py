from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from services.query_engine import QueryEngine

router = APIRouter()
query_engine = QueryEngine()


class QueryRequest(BaseModel):
    query: str
    date: Optional[str] = None


@router.post("/")
async def process_query(request: QueryRequest):
    """
    Process natural language query
    
    Examples:
    - "Show me when someone entered at 3 PM"
    - "Were there any people detected between 2-4 PM?"
    - "What happened around 5:30 PM?"
    """
    try:
        # Parse date if provided
        date_obj = None
        if request.date:
            try:
                date_obj = datetime.fromisoformat(request.date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format")
        
        # Process query
        result = await query_engine.process_query(request.query, date_obj)
        
        return result
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_query_examples():
    """Get example queries"""
    return {
        "examples": [
            {
                "query": "Show me people detected after 5 PM",
                "description": "Find person detections in the evening"
            },
            {
                "query": "Were there any cars this morning?",
                "description": "Check for vehicle activity in morning"
            },
            {
                "query": "What happened around 3:30 PM?",
                "description": "Get events near specific time"
            },
            {
                "query": "How many people were detected today?",
                "description": "Count person detections for the day"
            },
            {
                "query": "Show me activity between 2 and 4 PM",
                "description": "Get all events in time range"
            },
            {
                "query": "Was anyone detected in the last hour?",
                "description": "Recent person detections"
            }
        ]
    }
