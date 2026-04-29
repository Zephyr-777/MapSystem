import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.models.geo_asset import GeoAsset

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None

logger = logging.getLogger(__name__)


DEFAULT_RESULT_LIMIT = 20
COMPLEX_QUERY_HINTS = ("最近", "显示", "查找", "查询", "包含", "附近", "并且", "同时", "筛选", "上传")
STOP_PHRASES = [
    "最近一天",
    "最近一周",
    "最近一月",
    "最近一个月",
    "最近1天",
    "最近7天",
    "最近30天",
    "查找",
    "查询",
    "显示",
    "搜索",
    "上传的",
    "数据",
    "地质",
    "描述",
    "包含",
    "有关",
    "相关",
    "资料",
    "文件",
    "信息",
]
TOKEN_NORMALIZATION = {
    "geotiff": "GeoTIFF",
    "tiff": "GeoTIFF",
    "tif": "GeoTIFF",
    "dem": "GeoTIFF",
    "netcdf": "NetCDF",
    "nc": "NetCDF",
    "shapefile": "Shapefile",
    "shp": "Shapefile",
    "vector": "矢量",
    "raster": "栅格",
    "excel": "表格",
    "xlsx": "表格",
    "xls": "表格",
    "csv": "表格",
}
DATE_RANGE_HINTS: list[tuple[int, tuple[str, ...]]] = [
    (1, ("最近一天", "最近1天", "近一天", "今日", "今天")),
    (7, ("最近一周", "最近7天", "近一周", "本周")),
    (30, ("最近一月", "最近一个月", "最近30天", "近一个月", "本月")),
]
FILE_TYPE_HINTS = {
    "矢量": ("矢量", "vector", "shp", "shape", "shape file"),
    "栅格": ("栅格", "影像", "遥感", "raster"),
    "文档": ("excel", "xlsx", "xls", "csv", "表格", "属性表", "附件", "文档"),
}
SUB_TYPE_HINTS = {
    "GeoTIFF": ("geotiff", "tif", "tiff", "dem", "高程", "地形"),
    "NetCDF": ("netcdf", ".nc", " nc ", "nc数据", "nc文件"),
    "Shapefile": ("shapefile", ".shp", "shp", "shape file"),
}
GEOLOGY_KEYWORDS = (
    "断层", "岩性", "矿产", "地层", "遥感", "高程", "地形", "栅格", "矢量",
    "钻孔", "剖面", "影像", "构造", "沉积", "玄武岩", "花岗岩", "砂岩", "石灰岩",
)


@dataclass
class RuntimeSearchConfig:
    enabled: bool = True
    provider: str = "zhipu"
    model: str = "glm-4.5-air"
    api_key: str = ""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"


@dataclass
class ParsedSearchIntent:
    keywords: list[str] = field(default_factory=list)
    file_type: Optional[str] = None
    sub_type: Optional[str] = None
    date_range_days: Optional[int] = None
    limit: int = DEFAULT_RESULT_LIMIT
    sort_by: str = "updated_at_desc"

    def normalized_keywords(self) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for keyword in self.keywords:
            cleaned = keyword.strip().strip("\"'").lower()
            if not cleaned:
                continue
            cleaned = TOKEN_NORMALIZATION.get(cleaned, cleaned)
            if cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized


@dataclass(frozen=True)
class CatalogSearchItem:
    id: int
    dataset_id: str
    name: str
    file_type: str
    sub_type: str
    description: str
    extent: list[float]
    center_x: float
    center_y: float
    srid: int = 4326
    source: str = "catalog"
    asset_family: str = "dataset"
    render_mode: str = "map-overlay"
    overlay_supported: bool = True
    index_point_enabled: bool = True
    downloadable: bool = True
    overlay_id: Optional[str] = None
    download_url: Optional[str] = None
    time_range: Optional[str] = None
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


CATALOG_SEARCH_ITEMS: tuple[CatalogSearchItem, ...] = (
    CatalogSearchItem(
        id=-1001,
        dataset_id="himalaya-topography-2018",
        name="喜马拉雅山脉遥感影像",
        file_type="栅格",
        sub_type="GeoTIFF",
        description="喜马拉雅山区 1:25 万地形 GeoTIFF，达到指定缩放级别后作为地图影像图层叠加。",
        extent=[73.0, 25.0, 105.0, 40.5],
        center_x=89.0,
        center_y=32.75,
        source="local-overlay",
        asset_family="raster",
        overlay_id="himalaya-topography-2018",
        download_url="/api/geodata/local-raster-download/himalaya-topography-2018",
        time_range="2018",
        aliases=("喜马拉雅", "喜马拉雅山区", "himalaya", "地形影像", "1:25万"),
        tags=("GeoTIFF", "地形", "遥感", "本地 TIF", "可下载"),
    ),
    CatalogSearchItem(
        id=-1002,
        dataset_id="heihe-soil-respiration",
        name="黑河地区数据",
        file_type="文档",
        sub_type="HeiheSite",
        description="黑河下游 Li-8100 土壤呼吸观测数据，默认以站点聚合展示，放大后查看逐次观测点。",
        extent=[99.0, 39.0, 102.5, 42.5],
        center_x=100.75,
        center_y=40.75,
        download_url="/api/download/heihe",
        time_range="2014年7月-8月",
        aliases=("黑河", "黑河下游", "heihe", "土壤呼吸", "Li-8100", "观测点"),
        tags=("专题数据", "GeoJSON", "站点", "土壤呼吸", "可下载"),
    ),
    CatalogSearchItem(
        id=-1003,
        dataset_id="heihe-grassland-1988",
        name="黑河流域草场分布数据集",
        file_type="矢量",
        sub_type="Shapefile",
        description="黑河流域 1:100 万草场分布 Shapefile（1988），以面图层展示草场类型，并提供聚合索引点和原始数据整包下载。",
        extent=[96.0, 37.0, 104.5, 43.5],
        center_x=100.25,
        center_y=40.25,
        download_url="/api/download/heihe-grassland",
        time_range="1988",
        aliases=("黑河草场", "黑河流域", "heihe grassland", "草场分布"),
        tags=("Shapefile", "矢量", "草场", "1988", "可下载"),
    ),
    CatalogSearchItem(
        id=-1004,
        dataset_id="badaling-town-imagery",
        name="八达岭镇分级遥感影像",
        file_type="栅格",
        sub_type="GeoTIFF",
        description="八达岭镇双分幅 GeoTIFF 金字塔影像，地图会根据缩放级别自动切换 L11-L16 分辨率并叠加显示。",
        extent=[115.85, 40.2, 116.15, 40.5],
        center_x=116.0,
        center_y=40.35,
        download_url="/api/download/badaling-imagery",
        time_range="原始影像",
        aliases=("八达岭", "八达岭镇", "badaling", "影像金字塔", "分级影像"),
        tags=("GeoTIFF", "遥感", "L11-L16", "金字塔", "可下载"),
    ),
)


class SemanticSearchEngine:
    def __init__(self, db: Session):
        self.db = db

    async def search(self, query: str, config: Optional[dict[str, Any]] = None) -> tuple[list[GeoAsset | CatalogSearchItem], str, Optional[str]]:
        normalized_query = (query or "").strip()
        if not normalized_query:
            return [], "fallback", "empty_query"

        runtime_config = self.resolve_runtime_config(config)
        rule_intent = self.parse_rule_based(normalized_query)
        fallback_reason: Optional[str] = None

        ai_intent: Optional[ParsedSearchIntent] = None
        if self.should_use_ai(normalized_query, rule_intent, runtime_config):
            ai_intent, fallback_reason = self.parse_with_model(normalized_query, runtime_config)

        merged_intent = self.merge_intents(rule_intent, ai_intent)
        assets = self.run_search(normalized_query, merged_intent)

        if ai_intent is not None:
            return assets, "ai", None

        return assets, "fallback", fallback_reason or self.default_fallback_reason(runtime_config)

    def resolve_runtime_config(self, config: Optional[dict[str, Any]]) -> RuntimeSearchConfig:
        config = config or {}
        enabled = bool(config.get("enabled", True))
        provider = str(config.get("provider") or settings.SMART_SEARCH_PROVIDER).strip().lower() or "zhipu"
        model = str(config.get("model") or settings.SMART_SEARCH_MODEL).strip() or "glm-4.5-air"
        api_key = str(config.get("api_key") or settings.SMART_SEARCH_API_KEY).strip()
        base_url = str(config.get("base_url") or settings.SMART_SEARCH_BASE_URL).strip() or "https://open.bigmodel.cn/api/paas/v4"
        base_url = base_url.rstrip("/")

        return RuntimeSearchConfig(
            enabled=enabled,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

    def parse_rule_based(self, query: str) -> ParsedSearchIntent:
        normalized = query.lower()
        intent = ParsedSearchIntent()

        for days, hints in DATE_RANGE_HINTS:
            if any(token in normalized for token in hints):
                intent.date_range_days = days
                break

        for file_type, hints in FILE_TYPE_HINTS.items():
            if any(token in normalized for token in hints):
                intent.file_type = file_type
                break

        for sub_type, hints in SUB_TYPE_HINTS.items():
            if any(token in normalized for token in hints):
                intent.sub_type = sub_type
                if sub_type in {"GeoTIFF", "NetCDF"}:
                    intent.file_type = intent.file_type or "栅格"
                elif sub_type == "Shapefile":
                    intent.file_type = intent.file_type or "矢量"
                break

        quoted_keywords = re.findall(r"[\"'“”‘’]([^\"'“”‘’]{1,40})[\"'“”‘’]", query)
        if quoted_keywords:
            intent.keywords.extend(quoted_keywords)

        limit_match = re.search(r"(?:前|返回|展示|显示|给我)\s*(\d{1,2})\s*(?:条|个|份)?", query)
        if limit_match:
            intent.limit = self.safe_limit(limit_match.group(1))

        if "按名称" in query:
            intent.sort_by = "name_asc"
        elif any(token in query for token in ("最新", "最近", "刚刚", "新上传")):
            intent.sort_by = "updated_at_desc"

        cleaned_query = query
        for phrase in STOP_PHRASES:
            cleaned_query = cleaned_query.replace(phrase, " ")

        for symbol in ("，", ",", "。", "；", ";", "、", "附近", "的", "并且", "同时", "以及", "和"):
            cleaned_query = cleaned_query.replace(symbol, " ")

        tokens = [token.strip() for token in re.split(r"\s+", cleaned_query) if token.strip()]
        for token in tokens:
            lowered = token.lower()
            if lowered in TOKEN_NORMALIZATION:
                continue
            if len(token) <= 1:
                continue
            intent.keywords.append(token)

        intent.keywords = intent.normalized_keywords()
        return intent

    def should_use_ai(self, query: str, intent: ParsedSearchIntent, config: RuntimeSearchConfig) -> bool:
        if not config.enabled or not config.api_key or not OpenAI:
            return False
        if config.provider != "zhipu":
            return False
        if len(query) < 6:
            return False
        has_complex_phrase = any(hint in query for hint in COMPLEX_QUERY_HINTS)
        has_multi_condition = sum(bool(value) for value in (intent.file_type, intent.sub_type, intent.date_range_days)) >= 2
        sparse_keywords = len(intent.keywords) <= 1
        has_geology_semantics = any(token in query for token in GEOLOGY_KEYWORDS)
        return has_complex_phrase or has_multi_condition or (sparse_keywords and has_geology_semantics)

    def parse_with_model(self, query: str, config: RuntimeSearchConfig) -> tuple[Optional[ParsedSearchIntent], Optional[str]]:
        try:
            client = OpenAI(
                api_key=config.api_key,
                base_url=f"{config.base_url}/",
                timeout=20.0,
                max_retries=1,
            )
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是地理数据搜索解析器。"
                            "请把用户自然语言查询解析成 JSON。"
                            "只输出 JSON，不要输出解释。"
                            '字段固定为: {"keywords": [], "file_type": null, "sub_type": null, '
                            '"date_range_days": null, "limit": 20, "sort_by": "updated_at_desc"}。'
                            "file_type 只能是 矢量 或 栅格 或 文档 或 null。"
                            "sub_type 只能是 GeoTIFF、NetCDF、Shapefile 或 null。"
                            "keywords 只保留真正检索词，不要包含‘查找’‘数据’这类功能词。"
                            "如果用户提到最近/最新，优先设置 date_range_days 或 sort_by。"
                            "limit 只能返回 1-50 的整数。"
                            "sort_by 只能是 updated_at_desc 或 name_asc。"
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.01,
                max_tokens=300,
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            content = self.extract_message_text(response.choices[0].message.content)
            parsed = self.parse_intent_payload(content)
            if parsed is None:
                return None, "ai_invalid_json"
            return parsed, None
        except Exception as exc:  # pragma: no cover - network/runtime path
            logger.warning("Smart search AI parsing failed: %s", exc)
            return None, "ai_unavailable"

    def parse_intent_payload(self, payload: str) -> Optional[ParsedSearchIntent]:
        cleaned = payload.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None
        if not {"keywords", "file_type", "sub_type", "date_range_days", "limit", "sort_by"} & set(data.keys()):
            return None

        keywords = self.normalize_keywords_payload(data.get("keywords"))

        intent = ParsedSearchIntent(
            keywords=keywords,
            file_type=data.get("file_type"),
            sub_type=data.get("sub_type"),
            date_range_days=data.get("date_range_days"),
            limit=self.safe_limit(data.get("limit")),
            sort_by=data.get("sort_by") or "updated_at_desc",
        )
        intent.keywords = intent.normalized_keywords()
        if intent.file_type not in {"矢量", "栅格", "文档", None}:
            intent.file_type = None
        if intent.sub_type not in {"GeoTIFF", "NetCDF", "Shapefile", None}:
            intent.sub_type = None
        if intent.date_range_days is not None:
            try:
                intent.date_range_days = max(1, min(int(intent.date_range_days), 365))
            except (TypeError, ValueError):
                intent.date_range_days = None
        if intent.sort_by not in {"updated_at_desc", "name_asc"}:
            intent.sort_by = "updated_at_desc"
        if not intent.keywords and intent.file_type is None and intent.sub_type is None and intent.date_range_days is None:
            return None
        return intent

    def extract_message_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(part for part in parts if part).strip()
        return str(content or "").strip()

    def normalize_keywords_payload(self, payload: Any) -> list[str]:
        if payload is None:
            return []
        if isinstance(payload, str):
            parts = re.split(r"[\s,，、;；/]+", payload)
            return [part for part in parts if part.strip()]
        if isinstance(payload, Iterable):
            return [str(item).strip() for item in payload if str(item).strip()]
        return [str(payload).strip()] if str(payload).strip() else []

    def merge_intents(self, base: ParsedSearchIntent, ai: Optional[ParsedSearchIntent]) -> ParsedSearchIntent:
        if ai is None:
            return base

        merged = ParsedSearchIntent(
            keywords=list(base.keywords),
            file_type=base.file_type or ai.file_type,
            sub_type=base.sub_type or ai.sub_type,
            date_range_days=base.date_range_days or ai.date_range_days,
            limit=base.limit if base.limit != DEFAULT_RESULT_LIMIT else ai.limit,
            sort_by=ai.sort_by or base.sort_by,
        )
        merged.keywords.extend(ai.keywords)
        merged.keywords = merged.normalized_keywords()
        return merged

    def run_search(self, original_query: str, intent: ParsedSearchIntent) -> list[GeoAsset | CatalogSearchItem]:
        query = self.base_query()
        query = self.apply_filters(query, intent)

        candidate_limit = max(intent.limit * 8, 80)
        assets = query.limit(candidate_limit).all()
        scored_assets: list[tuple[int, Any]] = [
            (self.score_asset(asset, original_query, intent), asset)
            for asset in assets
        ]
        scored_assets.extend(
            (self.score_catalog_item(item, original_query, intent), item)
            for item in CATALOG_SEARCH_ITEMS
        )
        scored_assets.sort(
            key=lambda item: (
                item[0],
                getattr(item[1], "updated_at", None) or datetime.now(),
            ),
            reverse=True,
        )

        deduped: list[GeoAsset | CatalogSearchItem] = []
        seen_ids: set[int] = set()
        for score, asset in scored_assets:
            if score <= 0:
                continue
            if asset.id in seen_ids:
                continue
            seen_ids.add(asset.id)
            deduped.append(asset)
            if len(deduped) >= intent.limit:
                break

        return deduped

    def score_catalog_item(self, item: CatalogSearchItem, original_query: str, intent: ParsedSearchIntent) -> int:
        if intent.file_type and item.file_type != intent.file_type:
            return 0
        if intent.sub_type and item.sub_type != intent.sub_type:
            return 0
        if intent.date_range_days:
            # Built-in catalog datasets are stable references, not uploaded records.
            # Keep "最近上传" searches focused on uploaded GeoAsset rows.
            return 0

        score = 0
        query_lower = original_query.lower().strip()
        searchable_parts = [
            item.name,
            item.dataset_id,
            item.file_type,
            item.sub_type,
            item.description,
            item.time_range or "",
            " ".join(item.aliases),
            " ".join(item.tags),
        ]
        searchable_text = " ".join(part for part in searchable_parts if part).lower()

        if query_lower and query_lower in item.name.lower():
            score += 120
        if query_lower and query_lower in searchable_text:
            score += 70

        matched_keywords = 0
        for keyword in intent.keywords or [query_lower]:
            keyword_lower = keyword.lower().strip()
            if not keyword_lower:
                continue
            if self.keyword_in_text(keyword_lower, item.name):
                score += 60
                matched_keywords += 1
            elif self.keyword_in_text(keyword_lower, searchable_text):
                score += 34
                matched_keywords += 1

        if intent.file_type:
            score += 20
        if intent.sub_type:
            score += 24

        keyword_count = len(intent.keywords)
        if keyword_count:
            if matched_keywords == keyword_count:
                score += 36
            else:
                score -= (keyword_count - matched_keywords) * 28

        return score

    def base_query(self) -> Query:
        return self.db.query(GeoAsset).filter(GeoAsset.is_sidecar == False)

    def apply_filters(self, query: Query, intent: ParsedSearchIntent) -> Query:
        if intent.file_type:
            query = query.filter(GeoAsset.file_type == intent.file_type)
        if intent.sub_type:
            query = query.filter(GeoAsset.sub_type == intent.sub_type)
        if intent.date_range_days:
            start_time = datetime.now() - timedelta(days=intent.date_range_days)
            query = query.filter(GeoAsset.updated_at >= start_time)

        if intent.keywords:
            keyword_filters = []
            for keyword in intent.keywords:
                like = f"%{keyword}%"
                keyword_filters.append(GeoAsset.name.ilike(like))
                keyword_filters.append(GeoAsset.description.ilike(like))
                keyword_filters.append(GeoAsset.file_path.ilike(like))
            query = query.filter(or_(*keyword_filters))

        if intent.sort_by == "updated_at_desc":
            query = query.order_by(GeoAsset.updated_at.desc())
        else:
            query = query.order_by(GeoAsset.name.asc())

        return query

    def score_asset(self, asset: GeoAsset, original_query: str, intent: ParsedSearchIntent) -> int:
        score = 0
        query_lower = original_query.lower()
        name = (asset.name or "").lower()
        description = (asset.description or "").lower()
        file_path = (getattr(asset, "file_path", "") or "").lower()
        file_type = (asset.file_type or "").lower()
        sub_type = (asset.sub_type or "").lower()
        searchable_text = " ".join(part for part in (name, description, file_path, file_type, sub_type) if part)

        if name == query_lower:
            score += 140
        elif query_lower in name:
            score += 90
        elif query_lower in description:
            score += 60

        matched_keywords = 0

        for keyword in intent.keywords or [query_lower]:
            keyword_lower = keyword.lower()
            matched_this_keyword = False
            if self.keyword_in_text(keyword_lower, name):
                score += 45
                matched_this_keyword = True
            if self.keyword_in_text(keyword_lower, description):
                score += 28
                matched_this_keyword = True
            if self.keyword_in_text(keyword_lower, file_path):
                score += 20
                matched_this_keyword = True
            if self.keyword_in_text(keyword_lower, file_type):
                score += 18
                matched_this_keyword = True
            if self.keyword_in_text(keyword_lower, sub_type):
                score += 24
                matched_this_keyword = True
            if matched_this_keyword:
                matched_keywords += 1

        if intent.file_type and asset.file_type == intent.file_type:
            score += 24
        if intent.sub_type and asset.sub_type == intent.sub_type:
            score += 30
        if intent.date_range_days and asset.updated_at:
            freshness_threshold = datetime.now() - timedelta(days=intent.date_range_days)
            if asset.updated_at >= freshness_threshold:
                score += 16
            else:
                score -= 10

        keyword_count = len(intent.keywords)
        if keyword_count:
            score += matched_keywords * 12
            if matched_keywords == keyword_count:
                score += 35
            elif keyword_count >= 2:
                score -= (keyword_count - matched_keywords) * 30
            if all(self.keyword_in_text(keyword.lower(), searchable_text) for keyword in intent.keywords):
                score += 20

        if intent.sort_by == "updated_at_desc" and asset.updated_at:
            age_days = max((datetime.now() - asset.updated_at).days, 0)
            score += max(10 - min(age_days, 10), 0)

        return score

    def keyword_in_text(self, keyword: str, text: str) -> bool:
        if not keyword or not text:
            return False

        keyword = keyword.lower().strip()
        text = text.lower()
        if re.fullmatch(r"[a-z0-9._-]+", keyword):
            return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None
        return keyword in text

    def default_fallback_reason(self, config: RuntimeSearchConfig) -> str:
        if not config.enabled:
            return "ai_disabled"
        if not config.api_key:
            return "missing_api_key"
        if config.provider != "zhipu":
            return "unsupported_provider"
        return "fallback_search"

    def safe_limit(self, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return DEFAULT_RESULT_LIMIT
        return max(1, min(parsed, 50))
