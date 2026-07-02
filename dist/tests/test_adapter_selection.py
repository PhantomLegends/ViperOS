import pytest
import platform
from viperos.adapters import (
    get_active_adapter, 
    WindowsAdapter, 
    LinuxAdapter, 
    MacOSAdapter, 
    UnknownAdapter
)

def test_get_active_adapter_windows(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    adapter = get_active_adapter()
    assert isinstance(adapter, WindowsAdapter)
    assert adapter.get_name() == "Windows"

def test_get_active_adapter_linux(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    adapter = get_active_adapter()
    assert isinstance(adapter, LinuxAdapter)
    assert adapter.get_name() == "Linux"

def test_get_active_adapter_macos(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    adapter = get_active_adapter()
    assert isinstance(adapter, MacOSAdapter)
    assert adapter.get_name() == "macOS"

def test_get_active_adapter_unknown(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "FreeBSD")
    adapter = get_active_adapter()
    assert isinstance(adapter, UnknownAdapter)
    assert adapter.get_name() == "Unknown"
    # Ensure defensive methods don't crash
    assert adapter.launch_app("test") is False
    assert "Error" in adapter.execute_shell("ls")