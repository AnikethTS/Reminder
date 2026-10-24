import json

import storage


def _use(tmp_path, monkeypatch):
    path = tmp_path / "reminders.json"
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DATA_FILE", path)
    return path


def test_round_trip(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    reminders = [{"id": "a", "title": "Call mom", "datetime": "2026-05-01T09:00:00"}]
    storage.save_reminders(reminders)
    assert storage.load_reminders() == reminders
    assert json.loads(path.read_text()) == reminders
    assert not (tmp_path / "reminders.json.tmp").exists()


def test_missing_file_is_an_empty_list(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    assert storage.load_reminders() == []


def test_corrupt_json_is_backed_up_and_not_wiped(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text("{not json")
    assert storage.load_reminders() == []
    assert path.read_text() == "{not json"
    assert (tmp_path / "reminders.json.bak").read_text() == "{not json"


def test_non_list_payload_is_backed_up(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text('{"id": "nope"}')
    assert storage.load_reminders() == []
    assert (tmp_path / "reminders.json.bak").read_text() == '{"id": "nope"}'


def test_non_dict_entries_are_dropped_and_rewritten(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text('[1, {"id": "a", "title": "Keep"}, "x"]')
    assert storage.load_reminders() == [{"id": "a", "title": "Keep"}]
    assert json.loads(path.read_text()) == [{"id": "a", "title": "Keep"}]
