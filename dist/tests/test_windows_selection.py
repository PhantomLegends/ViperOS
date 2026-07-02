import pytest
import platform
from viperos.adapters import get_active_adapter, WindowsAdapter

def test_get_active_adapter_chooses_windows_on_windows(monkeypatch):
    """
    Test that VIPEROSCore chooses the Windows adapter on Windows.
    Evaluates: :codeplain::AdditionalFunctionality:
    """
    # Mock platform.system to return 'Windows'
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    
    adapter = get_active_adapter()
    
    # Assertions
    assert isinstance(adapter, WindowsAdapter), f"Expected WindowsAdapter but got {type(adapter)}"
    assert adapter.get_name() == "Windows", f"Expected name 'Windows' but got {adapter.get_name()}"

def test_windows_adapter_identifies_correctly():
    """
    Verify the WindowsAdapter class itself reports the correct identity.
    """
    adapter = WindowsAdapter()
    assert adapter.get_name() == "Windows"