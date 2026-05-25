from gi.repository import GLib

from kazam.backend import portal


def test_generate_token_is_safe_identifier():
    tok = portal.generate_token()
    assert tok.startswith("kazam")
    assert tok.replace("kazam", "").replace("_", "").isalnum()


def test_generate_token_is_unique():
    assert portal.generate_token() != portal.generate_token()


def test_select_sources_monitor_embedded_cursor():
    opts = portal.select_sources_options(
        handle_token="kazam_h1",
        source_types=portal.SourceType.MONITOR,
        cursor_embedded=True,
        restore_token=None,
    )
    assert opts["types"] == GLib.Variant("u", portal.SourceType.MONITOR)
    assert opts["cursor_mode"] == GLib.Variant("u", portal.CursorMode.EMBEDDED)
    assert opts["persist_mode"] == GLib.Variant("u", portal.PersistMode.PERSISTENT)
    assert opts["handle_token"] == GLib.Variant("s", "kazam_h1")
    assert "restore_token" not in opts


def test_select_sources_window_hidden_cursor_with_restore():
    opts = portal.select_sources_options(
        handle_token="kazam_h2",
        source_types=portal.SourceType.MONITOR | portal.SourceType.WINDOW,
        cursor_embedded=False,
        restore_token="abc-123",
    )
    assert opts["types"] == GLib.Variant(
        "u", portal.SourceType.MONITOR | portal.SourceType.WINDOW
    )
    assert opts["cursor_mode"] == GLib.Variant("u", portal.CursorMode.HIDDEN)
    assert opts["restore_token"] == GLib.Variant("s", "abc-123")


def test_parse_start_response_extracts_streams_and_token():
    results = GLib.Variant(
        "a{sv}",
        {
            "restore_token": GLib.Variant("s", "tok-xyz"),
            "streams": GLib.Variant(
                "a(ua{sv})",
                [
                    (
                        42,
                        {
                            "size": GLib.Variant("(ii)", (1920, 1080)),
                            "position": GLib.Variant("(ii)", (0, 0)),
                            "source_type": GLib.Variant("u", portal.SourceType.MONITOR),
                        },
                    )
                ],
            ),
        },
    )
    streams, restore_token = portal.parse_start_response(results)
    assert restore_token == "tok-xyz"
    assert streams == [
        {
            "node_id": 42,
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "source_type": portal.SourceType.MONITOR,
        }
    ]


def test_parse_start_response_missing_optionals():
    results = GLib.Variant(
        "a{sv}",
        {
            "streams": GLib.Variant(
                "a(ua{sv})",
                [(7, {"size": GLib.Variant("(ii)", (800, 600))})],
            )
        },
    )
    streams, restore_token = portal.parse_start_response(results)
    assert restore_token is None
    assert streams[0]["node_id"] == 7
    assert streams[0]["width"] == 800
    assert streams[0]["x"] == 0  # position defaults to (0, 0)
