import os
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.geo_asset import GeoAsset
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class SemanticSearchEngine:
    def __init__(self, db: Session):
        self.db = db
        # Use DashScope API Key from Env or Default
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-80313781df2f4a30adbaf0224b696835")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # Model configuration
        self.model_name = "qwen3.5-flash"  # As requested by user
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        ) if self.api_key else None
        
        # System prompt for NL2SQL
        self.system_prompt = """
        You are a PostgreSQL + PostGIS expert. Convert natural language queries to SQL.
        
        Table Schema:
        geo_assets (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            file_type VARCHAR,
            description VARCHAR,
            created_at TIMESTAMP,
            extent GEOMETRY(Polygon, 4326), -- Spatial column
            extent_min_x FLOAT, extent_min_y FLOAT, extent_max_x FLOAT, extent_max_y FLOAT
        );
        
        Rules:
        1. Return ONLY the SQL query. No markdown, no explanation.
        2. Use ST_Intersects or ST_Contains for spatial queries if 'extent' is valid.
        3. If spatial query is complex or ambiguous, fallback to bounding box filter using extent_min_x/y etc.
        4. Always select * from geo_assets.
        5. Limit results to 20 if not specified.
        """

    async def search(self, query: str) -> List[GeoAsset]:
        """
        Execute semantic search: NL -> SQL -> Execution -> Rerank
        """
        # Check if client is initialized properly (requires API key)
        if not self.client or not self.api_key:
            print("API Key missing or client init failed. Returning simple name search.")
            return self._fallback_search(query)

        try:
            # 1. NL2SQL
            sql_query = self._generate_sql(query)
            print(f"Generated SQL: {sql_query}")
            
            # Basic sanitization
            cleaned_sql = sql_query.replace("```sql", "").replace("```", "").strip()
            
            # 2. Execute SQL
            # Safety check: ensure read-only (simple heuristic)
            if any(kw in cleaned_sql.lower() for kw in ["drop", "delete", "update", "insert", "alter", "truncate"]):
                 print(f"Unsafe SQL blocked: {cleaned_sql}")
                 return self._fallback_search(query)
                
            # Use execute with text()
            try:
                result_proxy = self.db.execute(text(cleaned_sql))
                # We expect columns, but let's just get IDs if possible or map results
                # The prompt asks to select *, but we only need IDs to fetch objects cleanly via ORM
                
                # Fetch as dicts to be safe
                results = result_proxy.mappings().all()
            except Exception as e:
                print(f"SQL Execution failed: {e}")
                return self._fallback_search(query)
            
            if not results:
                return []
                
            # Extract IDs. Assuming 'id' column exists and is returned.
            ids = [row['id'] for row in results if 'id' in row]
            
            if not ids:
                 # Maybe user selected something else?
                 return self._fallback_search(query)

            assets = self.db.query(GeoAsset).filter(GeoAsset.id.in_(ids)).all()
            
            # 3. Semantic Reranking (Optional - can be slow)
            # Only rerank if we have results and it's worth it
            # For now, let's skip reranking to ensure speed and stability, or make it robust
            # reranked_assets = await self._semantic_rerank(assets, query)
            # return reranked_assets
            
            return assets

        except Exception as e:
            print(f"Smart Search failed: {e}")
            return self._fallback_search(query)

    def _generate_sql(self, query: str) -> str:
        try:
            # Use configured model
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Query: {query}\nSQL:"}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM generation failed: {e}")
            raise e

    async def _semantic_rerank(self, assets: List[GeoAsset], query: str) -> List[GeoAsset]:
        if not assets:
            return []
            
        # Get query embedding
        query_emb = self._get_embedding(query)
        
        # Get doc embeddings (name + description)
        docs = [f"{a.name} {a.description or ''}" for a in assets]
        
        # Qwen embedding models usually accept batch, but let's loop if batch fails or is limited
        # text-embedding-v1 is a common DashScope embedding model
        # Or compatible openai endpoint might map to it
        doc_embs = [self._get_embedding(d) for d in docs] 
        
        # Compute cosine similarity
        similarities = cosine_similarity([query_emb], doc_embs)[0]
        
        # Sort assets by similarity
        # Pair asset with score
        scored_assets = list(zip(assets, similarities))
        scored_assets.sort(key=lambda x: x[1], reverse=True)
        
        return [a for a, s in scored_assets]

    def _get_embedding(self, text: str) -> List[float]:
        # Use DashScope compatible embedding model
        # 'text-embedding-v1' or 'text-embedding-v2' are common Qwen embeddings
        # Or standard openai model names if mapped
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-v2" 
        )
        return response.data[0].embedding

    def _fallback_search(self, query: str) -> List[GeoAsset]:
        # Simple SQL LIKE search
        return self.db.query(GeoAsset).filter(
            (GeoAsset.name.ilike(f"%{query}%")) | 
            (GeoAsset.description.ilike(f"%{query}%"))
        ).limit(20).all()
