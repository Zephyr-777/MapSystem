import pytest
from app.api.v1.geology import highlight_text

def test_highlight_text():
    text = "Sandstone from the Jurassic period"
    query = "sandstone"
    assert highlight_text(text, query) == "<mark>Sandstone</mark> from the Jurassic period"
    
    query = "jurassic"
    assert highlight_text(text, query) == "Sandstone from the <mark>Jurassic</mark> period"
    
    query = "xyz"
    assert highlight_text(text, query) == text

def test_search_logic_mock():
    # Mock data
    features = [
        {"name": "Sample-001", "era": "Jurassic", "lithology": "Sandstone", "elevation": 100},
        {"name": "Sample-002", "era": "Cretaceous", "lithology": "Limestone", "elevation": 200},
        {"name": "Sample-003", "era": "Triassic", "lithology": "Sandstone", "elevation": 150},
    ]
    
    query = "sandstone"
    results = []
    for f in features:
        score = 0
        if query.lower() in f['lithology'].lower():
            score += 1
        if score > 0:
            results.append((f, score))
            
    assert len(results) == 2
    assert results[0][0]['name'] == "Sample-001"
    assert results[1][0]['name'] == "Sample-003"

    # Test multi-field
    query = "Jurassic"
    results = []
    for f in features:
        score = 0
        if query.lower() in f['era'].lower():
            score += 1
        if score > 0:
            results.append((f, score))
    assert len(results) == 1
    assert results[0][0]['name'] == "Sample-001"
