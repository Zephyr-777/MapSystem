from types import SimpleNamespace

from app.services.smart_search import CATALOG_SEARCH_ITEMS, ParsedSearchIntent, RuntimeSearchConfig, SemanticSearchEngine


def test_parse_rule_based_time_and_type():
    engine = SemanticSearchEngine(db=None)

    intent = engine.parse_rule_based("查找最近一周上传的矢量数据")

    assert intent.date_range_days == 7
    assert intent.file_type == "矢量"


def test_parse_rule_based_quoted_keyword():
    engine = SemanticSearchEngine(db=None)

    intent = engine.parse_rule_based("查询包含'断层'描述的数据")

    assert "断层" in intent.keywords


def test_parse_rule_based_extracts_sub_type_and_limit():
    engine = SemanticSearchEngine(db=None)

    intent = engine.parse_rule_based("显示最近一周前10条 GeoTIFF 断层数据")

    assert intent.date_range_days == 7
    assert intent.sub_type == "GeoTIFF"
    assert intent.file_type == "栅格"
    assert intent.limit == 10


def test_parse_intent_payload_filters_invalid_values():
    engine = SemanticSearchEngine(db=None)

    intent = engine.parse_intent_payload(
        '{"keywords":["DEM"],"file_type":"非法","sub_type":"GeoTIFF","date_range_days":"7","limit":200}'
    )

    assert intent is not None
    assert intent.file_type is None
    assert intent.sub_type == "GeoTIFF"
    assert intent.date_range_days == 7
    assert intent.limit == 50


def test_parse_intent_payload_normalizes_string_keywords_and_invalid_sort():
    engine = SemanticSearchEngine(db=None)

    intent = engine.parse_intent_payload(
        '{"keywords":"GeoTIFF 断层","file_type":"GeoTIFF","sub_type":"非法","date_range_days":7,"limit":5,"sort_by":"date_desc"}'
    )

    assert intent is not None
    assert intent.keywords == ["GeoTIFF", "断层"]
    assert intent.file_type is None
    assert intent.sub_type is None
    assert intent.sort_by == "updated_at_desc"


def test_should_use_ai_requires_key():
    engine = SemanticSearchEngine(db=None)
    intent = ParsedSearchIntent(keywords=["断层"])
    config = RuntimeSearchConfig(enabled=True, provider="zhipu", model="glm-4.5-air", api_key="", base_url="https://open.bigmodel.cn/api/paas/v4")

    assert engine.should_use_ai("查询包含断层描述的数据", intent, config) is False


def test_default_fallback_reason_for_unsupported_provider():
    engine = SemanticSearchEngine(db=None)
    config = RuntimeSearchConfig(enabled=True, provider="other", model="glm-4.5-air", api_key="x", base_url="https://open.bigmodel.cn/api/paas/v4")

    assert engine.default_fallback_reason(config) == "unsupported_provider"


def test_score_asset_prioritizes_name_and_sub_type():
    engine = SemanticSearchEngine(db=None)
    asset = SimpleNamespace(
        name="北京DEM地形图",
        description="包含高程栅格数据",
        file_type="栅格",
        sub_type="GeoTIFF",
        updated_at=None,
    )

    score = engine.score_asset(
        asset,
        "北京 DEM",
        ParsedSearchIntent(keywords=["北京", "dem"], file_type="栅格", sub_type="GeoTIFF"),
    )

    assert score >= 80


def test_score_asset_penalizes_missing_keywords():
    engine = SemanticSearchEngine(db=None)
    asset = SimpleNamespace(
        name="北京地质概览",
        description="包含基础说明",
        file_path="rasters/demo.tif",
        file_type="栅格",
        sub_type="GeoTIFF",
        updated_at=None,
    )

    loose_score = engine.score_asset(
        asset,
        "北京 DEM 断层",
        ParsedSearchIntent(keywords=["北京", "DEM", "断层"], file_type="栅格", sub_type="GeoTIFF"),
    )

    assert loose_score < 80


def test_catalog_search_finds_builtin_datasets():
    engine = SemanticSearchEngine(db=None)
    item = next(item for item in CATALOG_SEARCH_ITEMS if item.dataset_id == "himalaya-topography-2018")
    himalaya = engine.score_catalog_item(item, "喜马拉雅", ParsedSearchIntent(keywords=["喜马拉雅"]))

    assert himalaya > 0


def test_catalog_search_returns_heihe_and_badaling_without_geo_assets():
    class EmptyQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    class EmptyDb:
        def query(self, *_args, **_kwargs):
            return EmptyQuery()

    engine = SemanticSearchEngine(db=EmptyDb())

    heihe_results = engine.run_search("黑河", ParsedSearchIntent(keywords=["黑河"]))
    badaling_results = engine.run_search("八达岭", ParsedSearchIntent(keywords=["八达岭"]))

    assert {item.dataset_id for item in heihe_results} >= {"heihe-soil-respiration", "heihe-grassland-1988"}
    assert [item.dataset_id for item in badaling_results] == ["badaling-town-imagery"]
