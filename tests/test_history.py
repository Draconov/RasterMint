from rastermint.core.history import UndoHistory


def test_undo_redo_round_trip():
    history = UndoHistory(limit=10)
    state0 = {"value": 0}
    state1 = {"value": 1}
    history.record(state0, "Value")
    restored, action = history.undo(state1)
    assert restored == state0
    assert action == "Value"
    assert history.can_redo
    redone, action = history.redo(restored)
    assert redone == state1
    assert action == "Value"


def test_grouped_slider_gesture_is_one_undo_step():
    history = UndoHistory(limit=10)
    history.begin_group("Brightness")
    assert history.record({"value": 0}, "Brightness")
    assert not history.record({"value": 10}, "Brightness")
    assert not history.record({"value": 20}, "Brightness")
    history.end_group()

    restored, action = history.undo({"value": 30})
    assert restored == {"value": 0}
    assert action == "Brightness"
    assert not history.can_undo


def test_new_edit_clears_redo_stack():
    history = UndoHistory()
    history.record({"value": 0}, "First")
    restored, _ = history.undo({"value": 1})
    assert history.can_redo
    history.record(restored, "Second")
    assert not history.can_redo


def test_changing_limit_trims_oldest_history_entries():
    history = UndoHistory(limit=10)
    for value in range(6):
        history.record({"value": value}, f"Value {value}")

    history.set_limit(3)
    assert history.limit == 3

    current = {"value": 6}
    restored_values = []
    while history.can_undo:
        current, _ = history.undo(current)
        restored_values.append(current["value"])

    assert restored_values == [5, 4, 3]
