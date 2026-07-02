import pytest
import platform
from viperos.adapters import get_active_adapter, UnknownAdapter

def test_get_active_adapter_with_custom_unknown_platform(monkeypatch):
    """
    Verifies that :VIPEROSCore: chooses the generic adapter (UnknownAdapter) 
    for platforms that are not Windows, Linux, or macOS.
    """
    # Mocking an arbitrary unknown platform name
    monkeypatch.setattr(platform, "system", lambda: "Solaris")
    
    adapter = get_active_adapter()
    
    assert isinstance(adapter, UnknownAdapter), "Should return UnknownAdapter for 'Solaris'"
    assert adapter.get_name() == "Unknown"

def test_unknown_adapter_defensive_behavior():
    """
    Ensures the generic adapter provides safe fallback returns and does not crash.
    """
    adapter = UnknownAdapter()
    
    # Generic adapter should return False for actions it cannot perform
    assert adapter.launch_app("AnyApp") is False
    assert adapter.set_volume(50) is False
    assert adapter.speak("Hello") is False
    
    # Shell execution on unknown platform should return an error message string
    result = adapter.execute_shell("ls")
    assert "Error" in result
    assert "Unsupported platform" in result

def test_get_active_adapter_empty_platform(monkeypatch):
    """
    Verifies fallback when platform.system() returns an empty string or None.
    """
    monkeypatch.setattr(platform, "system", lambda: "")
    adapter = get_active_adapter()
    assert isinstance(adapter, UnknownAdapter)