import os
from pathlib import Path
from typing import Dict, List, Any
import json
import base64
from openai import OpenAI

class AIGeodataClassifier:
    def __init__(self):
        # Use DashScope API Key
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-80313781df2f4a30adbaf0224b696835")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        ) if self.api_key else None
        
        self.text_model = "qwen3.5-flash" # Updated per user request
        self.vision_model = "qwen-vl-max" # Keep vision model as is unless specified
    
    async def classify_upload(self, file_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        智能分类上传的地质数据，支持多模态（视觉+文本）
        """
        if not self.client:
            return self._mock_classification(file_path, metadata)

        try:
            # Check if file is an image (GeoTIFF/IMG/PNG/JPG) for visual analysis
            is_image = file_path.suffix.lower() in ['.tif', '.tiff', '.img', '.png', '.jpg', '.jpeg']
            
            messages = []
            
            if is_image:
                # Encode image to base64
                # Note: Qwen-VL might have size limits, usually need to resize or use URL.
                # For local file, base64 is standard for OpenAI compatible API.
                # But DashScope Qwen-VL often prefers OSS URL. 
                # Let's try standard base64 data URI first.
                base64_image = self._encode_image(file_path)
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._construct_prompt(file_path, metadata)},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
                model = self.vision_model
            else:
                # Text-only analysis for vector/tabular data
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
                print(f"Failed to parse JSON from AI response: {result_text}")
                return self._mock_classification(file_path, metadata)
            
            return {
                "predicted_type": result.get("predicted_type", "Unknown"),
                "confidence": result.get("confidence", 0.5),
                "suggested_tags": result.get("suggested_tags", []),
                "auto_description": result.get("auto_description", "")
            }
            
        except Exception as e:
            print(f"AI Classification failed: {e}")
            return self._mock_classification(file_path, metadata)

    def _encode_image(self, image_path: Path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

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
