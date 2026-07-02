import pytest
import platform
from viperos.adapters import get_active_adapter, LinuxAdapter

def test_get_active_adapter_chooses_linux_for_raspberry_pi(monkeypatch):
    """
    Test that VIPEROSCore treats Raspberry Pi as Linux for adapter selection.
    On Raspberry Pi OS, platform.system() returns 'Linux'.
    """
    # Simulate Raspberry Pi environment by mocking platform.system
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    
    adapter = get_active_adapter()
    
    # Assertions to ensure LinuxAdapter is selected
    assert isinstance(adapter, LinuxAdapter), (
        f"Expected LinuxAdapter for Raspberry Pi (Linux), but got {type(adapter).__name__}. "
        "Requirement: Raspberry Pi must be treated as Linux."
    )
    assert adapter.get_name() == "Linux", (
        f"Expected adapter name 'Linux', but got '{adapter.get_name()}'"
    )

def test_linux_adapter_functionality_check():
    """
    Verify that the LinuxAdapter returned for Raspberry Pi has the expected defensive interface.
    """
    adapter = LinuxAdapter()
    
    # Verify name
    assert adapter.get_name() == "Linux"
    
    # Verify defensive defaults for unimplemented Raspberry Pi/Linux actions
    # These should return False or specific error strings rather than raising NotImplementedError
    assert adapter.launch_app("any_app") is False
    assert adapter.set_volume(75) is False
    assert "Error" not in adapter.execute_shell("echo 'ViperOS'")