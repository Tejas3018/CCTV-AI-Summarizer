import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict
from openai import AsyncOpenAI
from zoneinfo import ZoneInfo

from config.settings import settings
from models.database import EventModel, SummaryModel

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

class SummarizerService:
    """Daily summary generation service using OpenAI"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.cam_tz = ZoneInfo(getattr(settings, 'CAMERA_TIMEZONE', 'UTC'))
        self.utc_tz = ZoneInfo('UTC')
    
    async def generate_daily_summary(self, date: datetime = None) -> Dict:
        """Generate summary for a specific date"""
        if date is None:
            date = datetime.now(self.cam_tz)
        
        logger.info(f"Generating summary for {date.date()}")
        
        try:
            # Get events for the day
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            start_utc = start_of_day.astimezone(self.utc_tz).replace(tzinfo=None)
            end_utc = end_of_day.astimezone(self.utc_tz).replace(tzinfo=None)
            
            events = await EventModel.get_by_date_range(start_utc, end_utc)
            
            if not events:
                logger.info("No events found for the day")
                return {
                    "summary": "No activity detected today.",
                    "events_count": 0,
                    "key_events": [],
                    "statistics": {}
                }
            
            # Prepare statistics
            stats = await self._calculate_statistics(events, start_utc, end_utc)
            
            # Get key events
            key_events = self._extract_key_events(events)
            
            # Generate AI summary
            summary_text = await self._generate_ai_summary(events, stats)
            
            # Save to database
            await SummaryModel.create(
                date=date,
                summary=summary_text,
                events_count=len(events),
                key_events=key_events,
                statistics=stats
            )
            
            logger.info(f"Summary generated successfully: {len(events)} events")
            
            return {
                "summary": summary_text,
                "events_count": len(events),
                "key_events": key_events,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}", exc_info=True)
            raise
    
    async def _calculate_statistics(
        self, 
        events: List[Dict], 
        start: datetime, 
        end: datetime
    ) -> Dict:
        """Calculate statistics from events"""
        
        # Count by type
        by_type = await EventModel.count_by_type(start, end)
        
        hourly_counts = {}
        people_breakdown = {"male": 0, "female": 0, "kid": 0, "person": 0, "total": 0}
        vehicles_total = 0
        time_of_day = {"night": 0, "morning": 0, "afternoon": 0, "evening": 0}
        for event in events:
            ts = event['timestamp']
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=self.utc_tz)
            local_ts = ts.astimezone(self.cam_tz)
            hour = local_ts.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            if 0 <= hour < 6:
                time_of_day["night"] += 1
            elif 6 <= hour < 12:
                time_of_day["morning"] += 1
            elif 12 <= hour < 18:
                time_of_day["afternoon"] += 1
            else:
                time_of_day["evening"] += 1
            det_type = str(event.get('detection_type', '')).lower()
            if det_type in people_breakdown:
                people_breakdown[det_type] += 1
            if det_type in ("car", "truck", "motorcycle", "bus"):
                vehicles_total += 1
        people_breakdown["total"] = sum(people_breakdown[k] for k in ("person", "male", "female", "kid"))
        
        peak_hours = sorted(
            hourly_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        sorted_events = sorted(events, key=lambda x: x['timestamp'])
        if sorted_events:
            ts_first = sorted_events[0]['timestamp']
            ts_last = sorted_events[-1]['timestamp']
            if ts_first.tzinfo is None:
                ts_first = ts_first.replace(tzinfo=self.utc_tz)
            if ts_last.tzinfo is None:
                ts_last = ts_last.replace(tzinfo=self.utc_tz)
            first_activity = ts_first.astimezone(self.cam_tz).strftime("%I:%M %p")
            last_activity = ts_last.astimezone(self.cam_tz).strftime("%I:%M %p")
        else:
            first_activity = None
            last_activity = None
        
        hourly_str = {str(h): c for h, c in hourly_counts.items()}
        return {
            "total_detections": len(events),
            "by_type": by_type,
            "hourly_distribution": hourly_str,
            "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
            "first_activity": first_activity,
            "last_activity": last_activity,
            "people_breakdown": people_breakdown,
            "vehicles_total": vehicles_total,
            "time_of_day": time_of_day,
        }
    
    def _extract_key_events(self, events: List[Dict], limit: int = 10) -> List[Dict]:
        """Extract key events (highest confidence, different types)"""
        
        # Group by type
        by_type = {}
        for event in events:
            det_type = event['detection_type']
            if det_type not in by_type:
                by_type[det_type] = []
            by_type[det_type].append(event)
        
        # Get top events from each type
        key_events = []
        for det_type, type_events in by_type.items():
            # Sort by confidence
            sorted_events = sorted(
                type_events,
                key=lambda x: x['confidence'],
                reverse=True
            )
            
            # Take top 2 from each type
            for event in sorted_events[:2]:
                ts = event['timestamp']
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=self.utc_tz)
                local_ts = ts.astimezone(self.cam_tz)
                key_events.append({
                    "timestamp": local_ts.strftime("%Y-%m-%d %I:%M:%S %p"),
                    "type": event['detection_type'],
                    "confidence": event['confidence'],
                    "event_id": str(event['_id'])
                })
        
        # Sort by timestamp and limit
        key_events.sort(key=lambda x: x['timestamp'])
        return key_events[:limit]
    
    async def _generate_ai_summary(self, events: List[Dict], stats: Dict) -> str:
        """Generate natural language summary using OpenAI"""
        
        try:
            # Prepare event data for GPT
            events_summary = self._prepare_events_for_gpt(events, stats)
            
            people = stats.get('people_breakdown', {})
            tod = stats.get('time_of_day', {})
            vehicles_total = stats.get('vehicles_total', 0)
            peak_hours_str = ', '.join([
                f"{h['hour']:02d}:00 ({h['count']} events)" for h in stats.get('peak_hours', [])
            ]) or 'none'

            # Create prompt
            prompt = f"""You are a home security AI assistant. Generate a clear, insightful daily summary of CCTV activity.

Date: {datetime.now(self.cam_tz).date()}
Total events: {stats['total_detections']}

People:
- Total: {people.get('total', 0)} (male: {people.get('male', 0)}, female: {people.get('female', 0)}, kids: {people.get('kid', 0)}, unlabeled: {people.get('person', 0)})

Vehicles:
- Total: {vehicles_total}

Time of day distribution:
- Night (00-06): {tod.get('night', 0)}
- Morning (06-12): {tod.get('morning', 0)}
- Afternoon (12-18): {tod.get('afternoon', 0)}
- Evening (18-24): {tod.get('evening', 0)}

Other statistics:
- First activity: {stats.get('first_activity', 'N/A')}
- Last activity: {stats.get('last_activity', 'N/A')}
- Peak hours: {peak_hours_str}

Activity breakdown by type:
{events_summary}

Write the summary in 3 short sections (separated by blank lines):
1) Overview: 2-3 sentences describing overall activity and whether today was quiet or busy.
2) People and vehicles: describe patterns using the numbers above (especially kids and unusual presence of people or cars).
3) Timing patterns & security insight: mention when activity was highest, any long quiet periods, and one practical security observation.

Be concise, avoid repeating the same numbers many times, and keep the whole response under 220 words."""

            # Call OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful home security assistant that provides clear, concise summaries of daily surveillance footage."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info("AI summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate AI summary: {e}")
            # Fallback to basic summary
            return self._generate_fallback_summary(stats)
    
    def _prepare_events_for_gpt(self, events: List[Dict], stats: Dict) -> str:
        """Prepare events data in readable format for GPT"""
        
        by_type = stats.get('by_type', {})
        
        lines = []
        for det_type, count in sorted(by_type.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"- {det_type.capitalize()}: {count} detections")
        
        # Add some temporal context
        hourly = stats.get('hourly_distribution', {})
        if hourly:
            busiest_hour = max(hourly.items(), key=lambda x: x[1])
            lines.append(f"\nBusiest hour overall: {int(busiest_hour[0]):02d}:00 with {busiest_hour[1]} events")
        
        return "\n".join(lines)
    
    def _generate_fallback_summary(self, stats: Dict) -> str:
        """Generate basic summary without AI"""
        
        total = stats['total_detections']
        by_type = stats.get('by_type', {})
        
        type_str = ", ".join([f"{count} {type}" for type, count in by_type.items()])
        
        return f"Today recorded {total} detection events: {type_str}. " \
               f"Activity started at {stats.get('first_activity', 'N/A')} " \
               f"and ended at {stats.get('last_activity', 'N/A')}."
    
    def schedule_daily_generation(self):
        """Schedule daily summary generation"""
        
        # Parse time
        hour, minute = map(int, settings.SUMMARY_GENERATION_TIME.split(':'))
        
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
            lambda: asyncio.run(self.generate_daily_summary())
        )
        
        logger.info(f"Scheduled daily summary at {settings.SUMMARY_GENERATION_TIME}")
    
    def run_scheduler(self):
        """Run the scheduler loop"""
        logger.info("Starting summary scheduler...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


async def main():
    """Test summary generation"""
    logger.info("=" * 60)
    logger.info("Daily Summary Generator")
    logger.info("=" * 60)
    
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not configured!")
        logger.error("Please set OPENAI_API_KEY in .env file")
        return
    
    summarizer = SummarizerService()
    
    # Generate summary for today
    result = await summarizer.generate_daily_summary()
    
    print("\n" + "=" * 60)
    print("DAILY SUMMARY")
    print("=" * 60)
    print(result['summary'])
    print("\n" + "=" * 60)
    print(f"Total Events: {result['events_count']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
