import os
from pathlib import Path
from typing import Dict, Any
import json
import logging

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None

logger = logging.getLogger(__name__)

class AIGeodataClassifier:
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        ) if self.api_key and OpenAI else None
        
        self.text_model = "qwen3.5-flash"
    
    async def classify_upload(self, file_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        智能分类上传的地质数据，基于文本元数据分析
        """
        if not self.client:
            return self._mock_classification(file_path, metadata)

        try:
            # Text-only analysis for all file types
            messages = [
                {"role": "system", "content": "You are an expert geologist and data scientist. Analyze the file metadata and suggest classification, tags, and description."},
                {"role": "user", "content": self._construct_prompt(file_path, metadata)}
            ]
            model = self.text_model

            # Call LLM
            # Note: response_format={"type": "json_object"} might not be fully supported by all Qwen versions in compatible mode yet.
            # We will ask for JSON in prompt and parse it.
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False
            )
            
            result_text = response.choices[0].message.content
            # Cleanup json block
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
                
            try:
                result = json.loads(result_text)
            except:
                # Fallback if JSON parsing fails
                logger.warning("Failed to parse JSON from AI response: %s", result_text)
                return self._mock_classification(file_path, metadata)
            
            return {
                "predicted_type": result.get("predicted_type", "Unknown"),
                "confidence": result.get("confidence", 0.5),
                "suggested_tags": result.get("suggested_tags", []),
                "auto_description": result.get("auto_description", "")
            }
            
        except Exception as e:
            logger.warning("AI Classification failed: %s", e)
            return self._mock_classification(file_path, metadata)

    def _construct_prompt(self, file_path: Path, metadata: Dict) -> str:
        extension = file_path.suffix
        filename = file_path.name
        size = file_path.stat().st_size
        
        return f"""
        Analyze the following geological data file:
        Filename: {filename}
        Extension: {extension}
        Size: {size} bytes
        Metadata: {json.dumps(metadata)}
        
        Please provide a VALID JSON response with the following fields:
        - predicted_type: (e.g., GeoTIFF, Shapefile, CSV, NetCDF)
        - confidence: (float between 0 and 1)
        - suggested_tags: (list of strings, e.g., ["Elevation", "Terrain", "China"])
        - auto_description: (a short natural language description)
        
        Do not include any other text outside the JSON.
        """

    def _mock_classification(self, file_path: Path, metadata: Dict) -> Dict:
        # Fallback mock implementation
        ext = file_path.suffix.lower()
        if ext in ['.tif', '.tiff']:
            return {
                "predicted_type": "GeoTIFF",
                "confidence": 0.85,
                "suggested_tags": ["Raster", "Imagery", "Elevation"],
                "auto_description": f"Automated detection: Raster dataset ({file_path.name})"
            }
        elif ext in ['.shp', '.zip']:
            return {
                "predicted_type": "Shapefile",
                "confidence": 0.9,
                "suggested_tags": ["Vector", "GIS", "Spatial"],
                "auto_description": f"Automated detection: Vector dataset ({file_path.name})"
            }
        elif ext == '.nc':
            return {
                "predicted_type": "NetCDF",
                "confidence": 0.95,
                "suggested_tags": ["Multidimensional", "Climate", "Scientific"],
                "auto_description": f"Automated detection: NetCDF multidimensional data ({file_path.name})"
            }
        elif ext == '.csv':
            return {
                "predicted_type": "CSV",
                "confidence": 0.8,
                "suggested_tags": ["Tabular", "Point Data"],
                "auto_description": f"Automated detection: Tabular data ({file_path.name})"
            }
        else:
             return {
                "predicted_type": "Unknown",
                "confidence": 0.0,
                "suggested_tags": [],
                "auto_description": "Unknown file type"
            }
