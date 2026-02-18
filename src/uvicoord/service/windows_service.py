"""Windows Service wrapper for Uvicoord."""

import os
import socket
import sys
from pathlib import Path

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


if PYWIN32_AVAILABLE:
    class UvicoordService(win32serviceutil.ServiceFramework):
        """Windows Service for Uvicoord Coordinator."""
        
        _svc_name_ = "Uvicoord"
        _svc_display_name_ = "Uvicoord Coordinator Service"
        _svc_description_ = "Port registry and coordinator for Python uvicorn applications"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.server = None
        
        def SvcStop(self):
            """Stop the service."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.server:
                self.server.should_exit = True
        
        def SvcDoRun(self):
            """Run the service."""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, "")
            )
            self.main()
        
        def main(self):
            """Main service logic."""
            import uvicorn
            from uvicoord.service.main import app
            from uvicoord.service.port_manager import PortManager
            
            # Load config to get port
            pm = PortManager()
            port = pm.config.coordinator_port
            
            # Configure uvicorn
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="info",
            )
            self.server = uvicorn.Server(config)
            
            # Run until stop event
            self.server.run()


def add_to_system_path(scripts_path: str) -> bool:
    """Add a path to the system PATH environment variable."""
    try:
        import winreg
        
        # Open the system environment variables key
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        
        # Get current PATH
        current_path, _ = winreg.QueryValueEx(key, "Path")
        
        # Check if already in PATH
        paths = current_path.split(";")
        if scripts_path.lower() not in [p.lower() for p in paths]:
            # Add to PATH
            new_path = f"{current_path};{scripts_path}"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"Added to system PATH: {scripts_path}")
            print("Note: Restart your terminal for PATH changes to take effect.")
        else:
            print(f"Already in system PATH: {scripts_path}")
        
        winreg.CloseKey(key)
        
        # Broadcast WM_SETTINGCHANGE to notify other processes
        try:
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0, 1000, None
            )
        except Exception:
            pass  # Non-critical
        
        return True
    except PermissionError:
        print("Error: Administrator privileges required to modify system PATH.")
        return False
    except Exception as e:
        print(f"Error adding to PATH: {e}")
        return False


def install_service():
    """Install the Windows service."""
    if not PYWIN32_AVAILABLE:
        print("Error: pywin32 is required for Windows service support.")
        print("Install it with: pip install pywin32")
        return False
    
    try:
        # Determine the Python executable path
        python_exe = sys.executable
        script_path = Path(__file__).resolve()
        
        # Install service
        win32serviceutil.InstallService(
            UvicoordService._svc_class_,
            UvicoordService._svc_name_,
            UvicoordService._svc_display_name_,
            startType=win32service.SERVICE_AUTO_START,
            description=UvicoordService._svc_description_,
        )
        print(f"Service '{UvicoordService._svc_name_}' installed successfully.")
        
        # Add Scripts folder to system PATH
        scripts_dir = Path(sys.executable).parent
        if scripts_dir.name == "Scripts" or (scripts_dir / "uvicoord.exe").exists():
            add_to_system_path(str(scripts_dir))
        else:
            # Might be in a venv
            venv_scripts = scripts_dir / "Scripts"
            if venv_scripts.exists():
                add_to_system_path(str(venv_scripts))
        
        print("Start it with: uvicoord service start")
        return True
    except Exception as e:
        print(f"Error installing service: {e}")
        return False


def uninstall_service():
    """Uninstall the Windows service."""
    if not PYWIN32_AVAILABLE:
        print("Error: pywin32 is required for Windows service support.")
        return False
    
    try:
        win32serviceutil.RemoveService(UvicoordService._svc_name_)
        print(f"Service '{UvicoordService._svc_name_}' uninstalled successfully.")
        return True
    except Exception as e:
        print(f"Error uninstalling service: {e}")
        return False


def start_service():
    """Start the Windows service."""
    if not PYWIN32_AVAILABLE:
        print("Error: pywin32 is required for Windows service support.")
        return False
    
    try:
        win32serviceutil.StartService(UvicoordService._svc_name_)
        print(f"Service '{UvicoordService._svc_name_}' started.")
        return True
    except Exception as e:
        print(f"Error starting service: {e}")
        return False


def stop_service():
    """Stop the Windows service."""
    if not PYWIN32_AVAILABLE:
        print("Error: pywin32 is required for Windows service support.")
        return False
    
    try:
        win32serviceutil.StopService(UvicoordService._svc_name_)
        print(f"Service '{UvicoordService._svc_name_}' stopped.")
        return True
    except Exception as e:
        print(f"Error stopping service: {e}")
        return False


if __name__ == "__main__":
    if PYWIN32_AVAILABLE:
        if len(sys.argv) == 1:
            # Started by Windows Service Control Manager
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(UvicoordService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            # Command line arguments
            win32serviceutil.HandleCommandLine(UvicoordService)
    else:
        print("Windows service support requires pywin32.")
        print("Install with: pip install pywin32")
