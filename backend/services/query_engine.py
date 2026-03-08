import logging
from datetime import datetime, timedelta
from typing import List, Dict
from openai import AsyncOpenAI
import json
import re
from zoneinfo import ZoneInfo

from config.settings import settings
from models.database import EventModel

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

class QueryEngine:
    """Natural language query engine using OpenAI"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.cam_tz = ZoneInfo(getattr(settings, 'CAMERA_TIMEZONE', 'UTC'))
        self.utc_tz = ZoneInfo('UTC')
    
    async def process_query(self, query: str, date: datetime = None) -> Dict:
        """
        Process natural language query about CCTV footage
        
        Examples:
        - "Show me when someone entered at 3 PM"
        - "Were there any people detected between 2-4 PM?"
        - "What happened around 5:30 PM?"
        """
        
        if date is None:
            date = datetime.now(self.cam_tz)
        
        logger.info(f"Processing query: {query}")
        
        try:
            # Parse query to extract intent and parameters
            query_params = await self._parse_query(query, date)
            
            # Fetch relevant events for the parsed time window
            events = await self._fetch_events(query_params)
            
            # Enforce the time window again at application level to avoid drift
            events = self._filter_events_by_time_window(events, query_params)
            
            # Generate response and apply stricter filtering for returned clips
            response = await self._generate_response(query, events, query_params)
            
            return {
                "query": query,
                "response": response["text"],
                "events": response["events"],
                "event_count": response.get("event_count", len(events))
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            return {
                "query": query,
                "response": "I encountered an error processing your query. Please try rephrasing.",
                "events": [],
                "event_count": 0
            }
    
    async def _parse_query(self, query: str, date: datetime) -> Dict:
        """Parse natural language query to extract parameters"""
        
        try:
            prompt = f"""Parse this CCTV query into structured parameters.

Query: "{query}"
Date: {date.date()}

Extract:
1. detection_type: Canonical object/person type string (one of: "person", "male", "female", "kid", "vehicle", "car", "truck", "motorcycle", "bus", or "any" if nothing specific).
2. time_start: Start time (24-hour HH:MM format like "09:30" or null)
3. time_end: End time (24-hour HH:MM format like "21:45" or null)
4. specific_time: Specific time mentioned (24-hour HH:MM or null)
5. intent: What does user want? (show_events, count, describe, check_presence)

Mapping rules for detection_type:
- If the user mentions "man", "men", "male", "boy", map to "male".
- If the user mentions "woman", "women", "lady", "girl", "female", map to "female".
- If the user mentions "kid", "child", "children", "baby", map to "kid".
- If the user only says generic words like "person", "people", map to "person".
- If the user mentions "vehicle" or "vehicles" (generic), map to "vehicle".
- If the user only talks about vehicles (car, bus, truck, motorcycle), map to that vehicle type.
- Only use "any" when the query truly does not specify any type.

Time rules:
- If the user says "today", use the Date above.
- If the user uses AM/PM (like "9:30am"), convert to 24-hour HH:MM.
- If the user gives a range ("between 9:30am and 9:50am"), set time_start and time_end.

Respond ONLY with valid JSON:
{
  "detection_type": "...",
  "time_start": "HH:MM or null",
  "time_end": "HH:MM or null",
  "specific_time": "HH:MM or null",
  "intent": "..."
}"""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a query parser. Respond only with JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            content = response.choices[0].message.content or ""
            try:
                params = json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if not match:
                    raise
                params = json.loads(match.group(0))

            # Heuristic fallback for detection_type based on raw query text
            det = str(params.get('detection_type', 'any') or 'any').lower()
            qlow = query.lower()
            if det in ('vehicles', 'vehicle', 'automobile', 'automobiles', 'auto', 'autos'):
                det = 'vehicle'
            elif det in ('motorbike', 'motorbikes', 'bike', 'bikes', 'scooter', 'scooters'):
                det = 'motorcycle'
            if det == 'any':
                if any(w in qlow for w in ['vehicle', 'vehicles', 'automobile', 'automobiles', 'auto', 'autos']):
                    det = 'vehicle'
                elif any(w in qlow for w in ['car', 'cars']):
                    det = 'car'
                elif any(w in qlow for w in ['truck', 'trucks']):
                    det = 'truck'
                elif any(w in qlow for w in ['bus', 'buses']):
                    det = 'bus'
                elif any(w in qlow for w in ['motorcycle', 'motorcycles', 'motorbike', 'motorbikes', 'bike', 'bikes', 'scooter', 'scooters']):
                    det = 'motorcycle'
                elif any(w in qlow for w in ['female', 'woman', 'women', 'lady', 'girl', 'girls']):
                    det = 'female'
                elif any(w in qlow for w in ['male', 'man', 'men', 'boy', 'boys']):
                    det = 'male'
                elif any(w in qlow for w in ['kid', 'child', 'children', 'baby', 'toddler']):
                    det = 'kid'
            params['detection_type'] = det

            if not params.get('time_start') and not params.get('time_end') and not params.get('specific_time') and not params.get('datetime_start') and not params.get('datetime_end'):
                now_cam = date
                if now_cam.tzinfo is None:
                    now_cam = now_cam.replace(tzinfo=self.cam_tz)
                after_match = re.search(r"\bafter\s+([0-9:\samp\.]+)", qlow)
                before_match = re.search(r"\bbefore\s+([0-9:\samp\.]+)", qlow)
                if after_match:
                    t = after_match.group(1).strip()
                    try:
                        dt_start = self._parse_time_to_datetime(t, date)
                        dt_end = now_cam
                        if dt_end < dt_start:
                            dt_end = dt_start.replace(hour=23, minute=59, second=59, microsecond=0)
                            if dt_end.tzinfo is None:
                                dt_end = dt_end.replace(tzinfo=self.cam_tz)
                        params['datetime_start'] = dt_start
                        params['datetime_end'] = dt_end
                    except Exception:
                        pass
                elif before_match:
                    t = before_match.group(1).strip()
                    try:
                        dt_end = self._parse_time_to_datetime(t, date)
                        dt_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                        if dt_start.tzinfo is None:
                            dt_start = dt_start.replace(tzinfo=self.cam_tz)
                        params['datetime_start'] = dt_start
                        params['datetime_end'] = dt_end
                    except Exception:
                        pass
                if not params.get('datetime_start') and not params.get('datetime_end'):
                    rel_match = re.search(r'(last|past|previous)\s+(\d+)\s*(minute|minutes|hour|hours)', qlow)
                    if rel_match:
                        value = int(rel_match.group(2))
                        unit = rel_match.group(3)
                        if "hour" in unit:
                            delta = timedelta(hours=value)
                        else:
                            delta = timedelta(minutes=value)
                        params['datetime_start'] = now_cam - delta
                        params['datetime_end'] = now_cam
                    elif "last hour" in qlow or "past hour" in qlow:
                        params['datetime_start'] = now_cam - timedelta(hours=1)
                        params['datetime_end'] = now_cam
                    elif "last 24 hours" in qlow or "past 24 hours" in qlow:
                        params['datetime_start'] = now_cam - timedelta(hours=24)
                        params['datetime_end'] = now_cam
                    elif "yesterday" in qlow:
                        y = now_cam - timedelta(days=1)
                        params['datetime_start'] = y.replace(hour=0, minute=0, second=0, microsecond=0)
                        params['datetime_end'] = y.replace(hour=23, minute=59, second=59, microsecond=0)
            
            # Convert times to datetime
            if params.get('time_start'):
                params['datetime_start'] = self._parse_time_to_datetime(
                    params['time_start'], date
                )
            
            if params.get('time_end'):
                params['datetime_end'] = self._parse_time_to_datetime(
                    params['time_end'], date
                )
            
            if params.get('specific_time'):
                specific_dt = self._parse_time_to_datetime(params['specific_time'], date)
                # Create 30-minute window around specific time
                params['datetime_start'] = specific_dt - timedelta(minutes=15)
                params['datetime_end'] = specific_dt + timedelta(minutes=15)

            if not params.get('datetime_start') or not params.get('datetime_end'):
                dt_start, dt_end = self._extract_time_range_from_query(query, date)
                if dt_start and dt_end:
                    params['datetime_start'] = dt_start
                    params['datetime_end'] = dt_end
            
            logger.info(f"Parsed parameters: {params}")
            return params
            
        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            dt_start, dt_end = self._extract_time_range_from_query(query, date)
            if dt_start and dt_end:
                return {
                    "detection_type": "any",
                    "datetime_start": dt_start,
                    "datetime_end": dt_end,
                    "intent": "show_events"
                }
            # Fallback to full-day window if nothing else can be parsed
            return {
                "detection_type": "any",
                "datetime_start": date.replace(hour=0, minute=0, second=0),
                "datetime_end": date.replace(hour=23, minute=59, second=59),
                "intent": "show_events"
            }

    def _extract_time_range_from_query(self, query: str, date: datetime):
        q = query.lower()
        m = re.search(r"between\s+([0-9:\samp\.]+?)\s+(?:and|to|-)+\s+([0-9:\samp\.]+)", q)
        if not m:
            m = re.search(r"from\s+([0-9:\samp\.]+?)\s+(?:to|-)+\s+([0-9:\samp\.]+)", q)
        if m:
            t1 = m.group(1).strip()
            t2 = m.group(2).strip()
            try:
                dt1 = self._parse_time_to_datetime(t1, date)
                dt2 = self._parse_time_to_datetime(t2, date)
            except Exception:
                return None, None
            if dt2 < dt1:
                dt1, dt2 = dt2, dt1
            return dt1, dt2
        after_m = re.search(r"\bafter\s+([0-9:\samp\.]+)", q)
        if after_m:
            t = after_m.group(1).strip()
            try:
                start = self._parse_time_to_datetime(t, date)
            except Exception:
                pass
            else:
                end = date.replace(hour=23, minute=59, second=59, microsecond=0)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=self.cam_tz)
                return start, end
        before_m = re.search(r"\bbefore\s+([0-9:\samp\.]+)", q)
        if before_m:
            t = before_m.group(1).strip()
            try:
                end = self._parse_time_to_datetime(t, date)
            except Exception:
                pass
            else:
                start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=self.cam_tz)
                return start, end
        m_single = re.search(r"(?:around|about|at)\s+([0-9:\samp\.]+)", q)
        if not m_single:
            return None, None
        t = m_single.group(1).strip()
        try:
            center = self._parse_time_to_datetime(t, date)
        except Exception:
            return None, None
        start = center - timedelta(minutes=15)
        end = center + timedelta(minutes=15)
        return start, end
    
    def _parse_time_to_datetime(self, time_str: str, date: datetime) -> datetime:
        s = time_str.strip().lower()
        if s in {"", "null", "none"}:
            raise ValueError("empty time string")
        ampm = None
        if "am" in s or "pm" in s:
            if "am" in s:
                ampm = "am"
            if "pm" in s:
                ampm = "pm"
            s = s.replace("am", "").replace("pm", "").strip()
        parts = s.split(":")
        if not parts or not parts[0].isdigit():
            raise ValueError(f"Unrecognized time format: {time_str}")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if ampm:
            hour = hour % 12
            if ampm == "pm":
                hour += 12
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))
        dt = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.cam_tz)
        return dt
    
    async def _fetch_events(self, params: Dict) -> List[Dict]:
        """Fetch events based on parsed parameters"""
        
        start = params.get('datetime_start')
        end = params.get('datetime_end')
        
        if not start or not end:
            now_cam = datetime.now(self.cam_tz)
            start = now_cam.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now_cam
        
        start_utc = start.astimezone(self.utc_tz).replace(tzinfo=None)
        end_utc = end.astimezone(self.utc_tz).replace(tzinfo=None)
        
        events = await EventModel.get_by_date_range(start_utc, end_utc)
        
        # Filter by detection type if specified
        detection_type = params.get('detection_type', 'any')
        if detection_type != 'any':
            dt = str(detection_type).lower()
            vehicle_types = {"car", "truck", "motorcycle", "bus"}
            if dt in {"vehicle", "vehicles"}:
                events = [
                    e for e in events
                    if str(e.get('detection_type', '')).lower() in vehicle_types
                ]
            else:
                events = [
                    e for e in events
                    if str(e.get('detection_type', '')).lower() == dt
                ]
        
        return events

    def _filter_events_by_time_window(self, events: List[Dict], params: Dict) -> List[Dict]:
        """Strict time filter in camera timezone so clips & stats stay inside the window."""
        if not events:
            return events
        start = params.get('datetime_start')
        end = params.get('datetime_end')
        if not start or not end:
            return events
        if start.tzinfo is None:
            start = start.replace(tzinfo=self.cam_tz)
        else:
            start = start.astimezone(self.cam_tz)
        if end.tzinfo is None:
            end = end.replace(tzinfo=self.cam_tz)
        else:
            end = end.astimezone(self.cam_tz)
        filtered: List[Dict] = []
        for e in events:
            ts = e.get('timestamp')
            if not isinstance(ts, datetime):
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=self.utc_tz)
            else:
                ts = ts.astimezone(self.utc_tz)
            ts_cam = ts.astimezone(self.cam_tz)
            if start <= ts_cam <= end:
                filtered.append(e)
        return filtered or events
    
    def _filter_events_for_query(self, query: str, events: List[Dict], params: Dict) -> List[Dict]:
        """Apply type-specific filtering (female/male/kid/vehicle) based on parsed params and raw query text.
        This ensures the returned clips list matches what the user actually asked for.
        """
        if not events:
            return events
        q = query.lower()
        parsed_type = str(params.get("detection_type", "any") or "any").lower()
        vehicle_types = {"car", "truck", "motorcycle", "bus"}
        explicit_type = None
        explicit_group = None
        has_vehicle_word = any(w in q for w in ["vehicle", "vehicles", "automobile", "automobiles", "auto", "autos"])
        if any(w in q for w in ["female", "woman", "women", "lady", "girl", "girls"]):
            explicit_type = "female"
        elif any(w in q for w in ["male", "man", "men", "boy", "boys"]):
            explicit_type = "male"
        elif any(w in q for w in ["kid", "child", "children", "baby", "toddler"]):
            explicit_type = "kid"
        elif any(w in q for w in ["car", "cars"]):
            explicit_type = "car"
        elif any(w in q for w in ["truck", "trucks"]):
            explicit_type = "truck"
        elif any(w in q for w in ["bus", "buses"]):
            explicit_type = "bus"
        elif any(w in q for w in ["motorcycle", "motorcycles", "motorbike", "motorbikes", "bike", "bikes", "scooter", "scooters"]):
            explicit_type = "motorcycle"
        if has_vehicle_word and explicit_type in {None, "car", "truck", "bus", "motorcycle"}:
            explicit_group = "vehicle"
        final_group = explicit_group or ("vehicle" if parsed_type in {"vehicle", "vehicles"} else None)
        final_type = explicit_type or (parsed_type if parsed_type not in {"any", "vehicle", "vehicles"} else None)
        if final_group == "vehicle":
            filtered = [e for e in events if str(e.get("detection_type", "")).lower() in vehicle_types]
            return filtered or events
        if not final_type:
            return events
        ftype = final_type.lower()
        filtered = [e for e in events if str(e.get("detection_type", "")).lower() == ftype]
        return filtered or events

    def _infer_intent(self, query: str, params: Dict) -> str:
        q = query.lower()
        if "how many" in q or "count" in q or "number of" in q or "total" in q:
            return "count"
        if any(p in q for p in ["what happened", "describe", "summary"]):
            return "describe"
        if any(p in q for p in ["was there", "were there", "did you see", "is there", "are there", "anyone", "anything"]):
            return "check_presence"
        if any(p in q for p in ["show", "list", "give", "find", "clip", "clips", "footage"]):
            return "show_events"
        raw = str(params.get("intent", "") or "").lower().strip()
        if raw in {"show_events", "count", "describe", "check_presence"}:
            return raw
        return "show_events"

    def _select_events_for_clips(self, events: List[Dict], limit: int = 20) -> List[Dict]:
        if not events:
            return []
        with_clip = [e for e in events if e.get("clip_path")]
        without_clip = [e for e in events if not e.get("clip_path")]
        with_clip.sort(key=lambda e: e.get("timestamp"))
        without_clip.sort(key=lambda e: e.get("timestamp"))
        ordered = with_clip + without_clip
        n = len(ordered)
        if n <= limit:
            return ordered
        if limit == 1:
            return [ordered[n // 2]]
        step = (n - 1) / float(limit - 1)
        indices = [int(round(i * step)) for i in range(limit)]
        return [ordered[i] for i in indices]

    def _format_time_range(self, params: Dict) -> str:
        start = params.get("datetime_start")
        end = params.get("datetime_end")
        if not start or not end:
            return ""
        if start.tzinfo is None:
            start = start.replace(tzinfo=self.cam_tz)
        else:
            start = start.astimezone(self.cam_tz)
        if end.tzinfo is None:
            end = end.replace(tzinfo=self.cam_tz)
        else:
            end = end.astimezone(self.cam_tz)
        if start.date() == end.date():
            return f" between {start.strftime('%I:%M %p')} and {end.strftime('%I:%M %p')}"
        return f" between {start.strftime('%b %d %I:%M %p')} and {end.strftime('%b %d %I:%M %p')}"

    def _rule_based_response(self, query: str, filtered_events: List[Dict], params: Dict, intent: str) -> str:
        count = len(filtered_events)
        dtype = str(params.get("detection_type", "any") or "any").lower()
        time_range = self._format_time_range(params)
        vehicle_types = {"car", "truck", "motorcycle", "bus"}
        label = "events" if dtype == "any" else ("vehicles" if dtype in {"vehicle", "vehicles"} else dtype)
        if label not in {"events", "vehicles"} and count != 1:
            label = f"{label}s"
        if intent == "count":
            if count == 0:
                return f"I did not find any {label}{time_range}."
            breakdown = ""
            if dtype in {"vehicle", "vehicles"}:
                by_type: Dict[str, int] = {}
                for e in filtered_events:
                    t = str(e.get("detection_type", "")).lower()
                    if t in vehicle_types:
                        by_type[t] = by_type.get(t, 0) + 1
                if by_type:
                    parts = [f"{v} {k}" for k, v in by_type.items()]
                    breakdown = " (" + ", ".join(parts) + ")"
            return f"I found {count} {label}{time_range}.{breakdown}"
        if intent == "check_presence":
            if count == 0:
                return f"No {label} detected{time_range}."
            return f"Yes, I found {count} {label}{time_range}."
        if count == 0:
            return f"No {label} detected{time_range}."
        show_count = min(20, count)
        return f"Found {count} {label}{time_range}. Showing {show_count} matching clips."

    async def _generate_response(
        self, 
        query: str, 
        events: List[Dict],
        params: Dict
    ) -> Dict:
        """Generate natural language response"""
        
        try:
            filtered_events = self._filter_events_for_query(query, events, params)
            intent = self._infer_intent(query, params)
            events_for_clips = self._select_events_for_clips(filtered_events, limit=20)

            if intent in {"count", "check_presence", "show_events"}:
                text = self._rule_based_response(query, filtered_events, params, intent)
            else:
                stats_text = self._format_stats_for_gpt(filtered_events, params)
                events_data = self._format_events_for_gpt(events_for_clips)
                prompt = f"""You are an assistant summarising CCTV footage.

User query:
{query}

Overall time window:{self._format_time_range(params) or " (not specified)"}

Overall statistics (for ALL matching events in this window):
{stats_text}

Sample events (up to 20, chronological):
{events_data}

Instructions:
- Base your answer ONLY on the events in this time window.
- Mention approximate counts and the types of things detected (people, males, females, kids, vehicles).
- Refer to specific example times where useful.
- Keep the answer under 120 words.
- If no events match, clearly say that nothing was detected in this time window."""

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful home security assistant. Provide clear, specific answers about CCTV footage using the supplied statistics and sample events. Do not invent events."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.6,
                    max_tokens=220
                )
                text = response.choices[0].message.content.strip()
            
            formatted_events = [
                {
                    "id": str(e['_id']),
                    "timestamp": (e['timestamp'].replace(tzinfo=self.utc_tz).astimezone(self.cam_tz)).isoformat(),
                    "type": e['detection_type'],
                    "confidence": e['confidence'],
                    "clip_path": e.get('clip_path', ''),
                    "thumbnail_path": e.get('thumbnail_path', '')
                }
                for e in events_for_clips
            ]
            
            return {
                "text": text,
                "events": formatted_events,
                "event_count": len(filtered_events),
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                "text": self._generate_fallback_response(events),
                "events": []
            }
    
    def _format_events_for_gpt(self, events: List[Dict]) -> str:
        """Format sample events for GPT consumption"""
        
        if not events:
            return "No sample events (but statistics above still reflect all matching events)."
        
        lines = []
        for event in events[:20]:
            ts = event['timestamp']
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=self.utc_tz)
            local_ts = ts.astimezone(self.cam_tz)
            time_str = local_ts.strftime("%I:%M:%S %p")
            lines.append(
                f"- {time_str}: {event['detection_type']} (confidence: {event['confidence']:.2f})"
            )
        
        if len(events) > 20:
            lines.append(f"... and {len(events) - 20} more events in this window")
        
        return "\n".join(lines)

    def _format_stats_for_gpt(self, events: List[Dict], params: Dict) -> str:
        if not events:
            return "No events matched this query in the selected time window."
        total = len(events)
        by_type: Dict[str, int] = {}
        people_breakdown = {"male": 0, "female": 0, "kid": 0}
        first_ts = None
        last_ts = None
        for e in events:
            t = str(e.get("detection_type", "")).lower()
            by_type[t] = by_type.get(t, 0) + 1
            if t in people_breakdown:
                people_breakdown[t] += 1
            ts = e.get("timestamp")
            if ts is not None:
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
        parts = [f"total events: {total}"]
        if by_type:
            type_str = ", ".join(f"{c} {k}" for k, c in sorted(by_type.items(), key=lambda x: x[0]))
            parts.append(f"by type: {type_str}")
        if any(people_breakdown.values()):
            pb = ", ".join(f"{v} {k}" for k, v in people_breakdown.items() if v)
            parts.append(f"people breakdown: {pb}")
        if first_ts and last_ts:
            if first_ts.tzinfo is None:
                first_ts = first_ts.replace(tzinfo=self.utc_tz)
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=self.utc_tz)
            first_local = first_ts.astimezone(self.cam_tz).strftime("%I:%M:%S %p")
            last_local = last_ts.astimezone(self.cam_tz).strftime("%I:%M:%S %p")
            parts.append(f"first event at {first_local}, last event at {last_local}")
        return "; ".join(parts)
    
    def _generate_fallback_response(self, events: List[Dict]) -> str:
        """Generate basic response without AI"""
        
        if not events:
            return "No events were detected for your query."
        
        count = len(events)
        types = {}
        for e in events:
            t = e['detection_type']
            types[t] = types.get(t, 0) + 1
        
        type_str = ", ".join([f"{c} {t}" for t, c in types.items()])
        
        return f"Found {count} events: {type_str}."


async def test_query():
    """Test query engine"""
    logger.info("=" * 60)
    logger.info("Query Engine Test")
    logger.info("=" * 60)
    
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not configured!")
        return
    
    engine = QueryEngine()
    
    # Test queries
    test_queries = [
        "Show me people detected after 5 PM",
        "Were there any cars in the afternoon?",
        "What happened around 3:30 PM?",
        "How many people were detected today?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        result = await engine.process_query(query)
        
        print(f"Response: {result['response']}")
        print(f"Events found: {result['event_count']}")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_query())