from nexora.network import detect_system, get_status


def test_detect_system():
    system = detect_system()
    assert system in {"Windows", "Linux", "Darwin", "Unknown"}


def test_get_status_shape():
    status = get_status()
    assert isinstance(status.online, bool)
    assert isinstance(status.adapters, list)
    assert status.system == detect_system()
    assert status.method
    assert status.detail
