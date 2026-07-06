from vtkspa.gui_helpers import format_psd_import_summary


def test_format_psd_import_summary_includes_counts_warnings_and_output():
    report = {
        "source": "/tmp/in.psd",
        "layers_imported": [{"id": "photo"}, {"id": "name"}],
        "layers_flattened": [{"count": 3}],
        "warnings": ["warn one", "warn two"],
    }

    lines = format_psd_import_summary(report, "/tmp/template")

    assert lines == [
        "✓ Imported PSD: /tmp/in.psd",
        "  Layers imported: 2",
        "  Static groups flattened: 1",
        "  ⚠ warn one",
        "  ⚠ warn two",
        "  Output: /tmp/template",
    ]


def test_format_psd_import_summary_handles_missing_lists():
    lines = format_psd_import_summary({"source": "a.psd"}, "/tmp/out")
    assert lines == [
        "✓ Imported PSD: a.psd",
        "  Layers imported: 0",
        "  Static groups flattened: 0",
        "  Output: /tmp/out",
    ]
