import pytest
import platform
from viperos.adapters import get_active_adapter, LinuxAdapter

def test_get_active_adapter_chooses_linux_on_linux(monkeypatch):
    """
    Test that VIPEROSCore chooses the Linux adapter on Linux.
    Evaluates: :codeplain::AdditionalFunctionality:
    """
    # Mock platform.system to return 'Linux'
    # This covers standard Linux distributions and Raspberry Pi (treated as Linux)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    
    adapter = get_active_adapter()
    
    # Assertions
    assert isinstance(adapter, LinuxAdapter), f"Expected LinuxAdapter but got {type(adapter)}"
    assert adapter.get_name() == "Linux", f"Expected name 'Linux' but got {adapter.get_name()}"

def test_linux_adapter_identifies_correctly():
    """
    Verify the LinuxAdapter class itself reports the correct identity.
    """
    adapter = LinuxAdapter()
    assert adapter.get_name() == "Linux"

def test_linux_adapter_defensive_methods():
    """
    Ensure LinuxAdapter methods are present and return expected defensive defaults 
    where not yet fully implemented.
    """
    adapter = LinuxAdapter()
    # Test a method with some implementation
    assert "Error" not in adapter.execute_shell("echo 'test'")
    # Test unimplemented methods return False/defensive values
    assert adapter.launch_app("any_app") is False
    assert adapter.set_volume(50) is False