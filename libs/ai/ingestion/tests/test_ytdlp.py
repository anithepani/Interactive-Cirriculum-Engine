from ice_ingestion._ytdlp import run_with_client_rotation


def test_rotation_uses_fresh_nested_options(monkeypatch):
    monkeypatch.setattr("ice_ingestion._ytdlp._CLIENTS", ["mweb", "tv"])
    monkeypatch.setattr("ice_ingestion._ytdlp._POT_BASE_URL", "http://provider:4416")
    seen = []

    def run(options):
        seen.append(options)
        if len(seen) == 1:
            raise RuntimeError("Sign in to confirm you're not a bot")
        return "ok"

    base = {"extractor_args": {"custom": ["unchanged=true"]}}
    assert run_with_client_rotation(run, base, operation="test") == "ok"
    assert base == {"extractor_args": {"custom": ["unchanged=true"]}}
    assert seen[0]["extractor_args"]["youtube"] == ["player_client=mweb"]
    assert seen[1]["extractor_args"]["youtube"] == ["player_client=tv"]
