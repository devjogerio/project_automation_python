from src.gui.state import ApplicationState


def test_state_transitions() -> None:
    s = ApplicationState()
    assert s.current_tab == "Chat"
    s.switch_tab("🎛️ Controles")
    assert s.current_tab == "🎛️ Controles"
    assert s.activity is False
    s.set_activity(True)
    s.add_notification(2)
    s.set_connected(True)
    assert s.activity is True
    assert s.notifications == 2
    assert s.connected is True

