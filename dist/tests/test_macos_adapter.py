import pytest
import subprocess
from viperos.platform_adapters import MacOSAdapter

@pytest.fixture
def mac_adapter():
    return MacOSAdapter()

def test_macos_adapter_name(mac_adapter):
    assert mac_adapter.get_name() == "macOS"

def test_macos_launch_app(mac_adapter, monkeypatch):
    calls = []
    def mock_popen(cmd, **kwargs):
        calls.append(cmd)
        return None
    
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    
    assert mac_adapter.launch_app("Calculator") is True
    assert ["open", "-a", "Calculator"] in calls

def test_macos_open_url(mac_adapter, monkeypatch):
    calls = []
    def mock_popen(cmd, **kwargs):
        calls.append(cmd)
        return None
    
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    
    assert mac_adapter.open_url("https://apple.com") is True
    assert ["open", "https://apple.com"] in calls

def test_macos_set_volume(mac_adapter, monkeypatch):
    calls = []
    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    assert mac_adapter.set_volume(50) is True
    assert ["osascript", "-e", "set volume output volume 50"] in calls

def test_macos_mute_volume(mac_adapter, monkeypatch):
    calls = []
    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    assert mac_adapter.mute_volume() is True
    assert ["osascript", "-e", "set volume with output muted"] in calls

def test_macos_speak(mac_adapter, monkeypatch):
    calls = []
    def mock_popen(cmd, **kwargs):
        calls.append(cmd)
        return None
    
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    
    assert mac_adapter.speak("Hello World") is True
    assert ["say", "Hello World"] in calls

def test_macos_execute_shell_success(mac_adapter, monkeypatch):
    def mock_check_output(cmd, **kwargs):
        return "mac_output"
    
    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    assert mac_adapter.execute_shell("ls") == "mac_output"

def test_macos_execute_shell_failure(mac_adapter, monkeypatch):
    def mock_check_output(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, output="failed")
    
    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    result = mac_adapter.execute_shell("invalid")
    assert "Error executing macOS command" in result
    assert "failed" in result