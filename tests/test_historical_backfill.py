import pytest
import sys
from unittest.mock import patch
from scripts.historical_backfill import parse_mlb, process_nfl, handle_chunking, transition_state

def test_transition_state():
    assert transition_state("init", "start") == "running"
    assert transition_state("running", "pause") == "paused"
    assert transition_state("paused", "resume") == "running"
    assert transition_state("running", "finish") == "completed"
    assert transition_state("running", "error") == "failed"
    assert transition_state("failed", "retry") == "running"
    assert transition_state("paused", "abort") == "failed"
    # Invalid transition should return current state
    assert transition_state("completed", "start") == "completed"
    assert transition_state("init", "pause") == "init"

def test_handle_chunking():
    items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    chunks = handle_chunking(items, 3)
    assert chunks == [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]

    assert handle_chunking([], 5) == []
    assert handle_chunking([1, 2], 5) == [[1, 2]]

def test_parse_mlb():
    assert parse_mlb(None) == {}
    assert parse_mlb({}) == {}
    data = {"game_id": "123", "home": "NYY", "away": "BOS"}
    result = parse_mlb(data)
    assert result == {"parsed": True, "data": data}

def test_process_nfl():
    with patch('sys.exit') as mock_exit, patch('builtins.print') as mock_print:
        process_nfl({"some": "data"})
        mock_print.assert_called_once_with("NFL processing is currently a placeholder. Exiting.")
        mock_exit.assert_called_once_with(0)
