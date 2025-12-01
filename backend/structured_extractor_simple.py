import os
from typing import List, Dict, Any
import json
import logging

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)

class StructuredExtractor:
    """Extract structured data from construction documents"""
    
    def __init__(self):
        self.client = None
        gemini_key = os.getenv("GEMINI_API_KEY", "AIzaSyDRHz6iNnjkBgHQN9putbHHPdb0H0kkuqI")
        
        if gemini_key and gemini_key.startswith("AIza") and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_key)
                self.client = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("Structured extractor initialized with Gemini")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.client = None
    
    def extract_structured_data(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect extraction type and extract structured data"""
        
        query_lower = query.lower()
        
        if "door" in query_lower and "schedule" in query_lower:
            return self.extract_door_schedule(context_chunks)
        elif "room" in query_lower:
            return self.extract_room_schedule(context_chunks)
        elif "equipment" in query_lower:
            return self.extract_equipment_list(context_chunks)
        else:
            return {
                "extraction_type": "unknown",
                "data": [],
                "message": "Could not determine extraction type. Try asking for a door schedule, room list, or equipment list."
            }
    
    def extract_door_schedule(self, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract door schedule from context"""
        
        if not self.client:
            return {
                "extraction_type": "door_schedule",
                "data": [],
                "error": "AI provider not configured",
                "sources": []
            }
        
        context = "\n\n".join([
            f"[{chunk['filename']}, Page {chunk['page_number']}]:\n{chunk['content']}"
            for chunk in context_chunks[:5]
        ])
        
        prompt = f"""You are a construction document analyzer. Extract ALL door schedule information from the provided text.

For each door mentioned, extract:
- mark: Door identifier (e.g., "D-101")
- location: Where the door is located (e.g., "Level 1 Corridor", "Main Entrance")
- width_mm: Door width in millimeters
- height_mm: Door height in millimeters
- fire_rating: Fire rating (e.g., "1 Hour", "90 min", "Non-rated")
- material: Door material (e.g., "Hollow Metal", "Wood", "Glass")

Return ONLY a valid JSON array. No markdown, no explanation, just the JSON array.

Text:
{context}

JSON array:"""

        try:
            response = self.client.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean up markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Try to parse JSON
            data = json.loads(result_text)
            
            # Ensure it's a list
            if not isinstance(data, list):
                data = [data] if isinstance(data, dict) else []
            
            return {
                "extraction_type": "door_schedule",
                "data": data,
                "sources": [{"filename": chunk["filename"], "page_number": chunk["page_number"]} 
                           for chunk in context_chunks[:3]],
                "total_items": len(data)
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {
                "extraction_type": "door_schedule",
                "data": [],
                "error": f"Failed to parse extraction results: {str(e)}",
                "sources": []
            }
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {
                "extraction_type": "door_schedule",
                "data": [],
                "error": str(e)
            }
    
    def extract_room_schedule(self, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract room information from context"""
        
        if not self.client:
            return {"extraction_type": "room_schedule", "data": [], "error": "AI provider not configured"}
        
        context = "\n\n".join([
            f"[{chunk['filename']}, Page {chunk['page_number']}]:\n{chunk['content']}"
            for chunk in context_chunks[:5]
        ])
        
        prompt = f"""Extract ALL room information from the text. For each room, extract:
- number: Room number
- name: Room name/description
- area_sqm: Area in square meters (if available)
- floor_finish: Flooring material
- wall_finish: Wall finish
- ceiling_finish: Ceiling material
- ceiling_height_mm: Ceiling height in mm

Return ONLY a valid JSON array:

Text:
{context}

JSON array:"""

        try:
            response = self.client.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(result_text)
            if not isinstance(data, list):
                data = [data] if isinstance(data, dict) else []
            
            return {
                "extraction_type": "room_schedule",
                "data": data,
                "sources": [{"filename": chunk["filename"], "page_number": chunk["page_number"]} 
                           for chunk in context_chunks[:3]],
                "total_items": len(data)
            }
        except Exception as e:
            return {"extraction_type": "room_schedule", "data": [], "error": str(e)}
    
    def extract_equipment_list(self, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract equipment list from context"""
        
        if not self.client:
            return {"extraction_type": "equipment_list", "data": [], "error": "AI provider not configured"}
        
        context = "\n\n".join([
            f"[{chunk['filename']}, Page {chunk['page_number']}]:\n{chunk['content']}"
            for chunk in context_chunks[:5]
        ])
        
        prompt = f"""Extract ALL equipment/MEP equipment from the text. For each item:
- tag: Equipment tag/identifier
- type: Equipment type (e.g., "HVAC Unit", "Electrical Panel")
- location: Where it's located
- capacity: Capacity or rating
- manufacturer: Manufacturer (if mentioned)

Return ONLY a valid JSON array:

Text:
{context}

JSON array:"""

        try:
            response = self.client.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(result_text)
            if not isinstance(data, list):
                data = [data] if isinstance(data, dict) else []
            
            return {
                "extraction_type": "equipment_list",
                "data": data,
                "sources": [{"filename": chunk["filename"], "page_number": chunk["page_number"]} 
                           for chunk in context_chunks[:3]],
                "total_items": len(data)
            }
        except Exception as e:
            return {"extraction_type": "equipment_list", "data": [], "error": str(e)}
