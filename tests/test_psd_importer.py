"""Tests for PSD importer naming convention parser and logic."""
from vtkspa.template.psd_importer import _parse_layer_name, _slugify


def test_parse_photo_default():
    result = _parse_layer_name("@photo")
    assert result["kind"] == "photo_slot"
    assert result["id"] == "photo"


def test_parse_photo_named():
    result = _parse_layer_name("@photo:headshot")
    assert result["kind"] == "photo_slot"
    assert result["id"] == "headshot"


def test_parse_text_field():
    result = _parse_layer_name("@text:name")
    assert result["kind"] == "text_slot"
    assert result["data_field"] == "name"
    assert result["id"] == "name"


def test_parse_text_team():
    result = _parse_layer_name("@text:team")
    assert result["kind"] == "text_slot"
    assert result["data_field"] == "team"


def test_parse_text_number():
    result = _parse_layer_name("@text:number")
    assert result["kind"] == "text_slot"
    assert result["data_field"] == "number"


def test_parse_static_layer():
    result = _parse_layer_name("Background")
    assert result["kind"] == "image"


def test_parse_static_layer_no_prefix():
    result = _parse_layer_name("Logo Overlay")
    assert result["kind"] == "image"


def test_slugify():
    assert _slugify("Hello World") == "hello_world"
    assert _slugify("Test 123!") == "test_123_"
