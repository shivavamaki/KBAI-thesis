from medicheck.evaluation import _parse_labels

def test_parse_labels_empty():
    assert _parse_labels("[]") == []

def test_parse_labels_list_string():
    assert _parse_labels('["wrong dose"]') == ["wrong dose"]
