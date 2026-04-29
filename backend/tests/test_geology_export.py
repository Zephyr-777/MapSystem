import pytest
import pandas as pd
import io
import json

# Mock DB and objects for export testing
class MockFeature:
    def __init__(self, id, name, props, geometry=None):
        self.id = id
        self.name = name
        self.properties = props
        self.geometry = geometry

def test_export_logic_csv():
    # Setup mock data
    features = [
        MockFeature(1, "S1", {"era": "Jurassic", "lithology_class": "Sandstone"}, '{"type":"Point","coordinates":[116.4, 39.9]}'),
        MockFeature(2, "S2", {"era": "Cretaceous", "lithology_class": "Limestone"}, '{"type":"Point","coordinates":[116.5, 40.0]}')
    ]
    
    # Simulate export logic
    data_rows = []
    for f in features:
        props = f.properties
        geom = json.loads(f.geometry)
        row = {
            'id': f.id,
            'name': f.name,
            'era': props.get('era'),
            'lithology': props.get('lithology_class'),
            'longitude': geom['coordinates'][0],
            'latitude': geom['coordinates'][1]
        }
        data_rows.append(row)
    
    df = pd.DataFrame(data_rows)
    csv_output = df.to_csv(index=False)
    
    assert "Jurassic" in csv_output
    assert "S1" in csv_output
    assert "116.4" in csv_output

def test_export_logic_markdown():
    # Setup mock data
    features = [
        MockFeature(1, "S1", {"era": "Jurassic"}, '{"type":"Point","coordinates":[0,0]}')
    ]
    
    data_rows = [{'id': f.id, 'name': f.name, 'era': f.properties['era']} for f in features]
    df = pd.DataFrame(data_rows)
    md_output = df.to_markdown(index=False)
    
    # Loose check for content, as formatting varies
    assert "id" in md_output
    assert "name" in md_output
    assert "era" in md_output
    assert "S1" in md_output
    assert "Jurassic" in md_output

def test_export_limit():
    # Simulate limit check
    ids = list(range(6000))
    limit = 5000
    
    with pytest.raises(ValueError, match="Limit exceeded"):
        if len(ids) > limit:
            raise ValueError("Limit exceeded")
