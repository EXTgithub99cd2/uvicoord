"""Windows platform implementation for Uvicoord."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


class WindowsPlatform:
    """Windows-specific service management using Task Scheduler."""
    
    TASK_NAME = "Uvicoord"
    
    def __init__(self):
        self.python_exe = sys.executable
        self.pythonw_exe = self.python_exe.replace("python.exe", "pythonw.exe")
    
    def is_task_installed(self) -> bool:
        """Check if the scheduled task is installed."""
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", self.TASK_NAME],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    
    def get_task_status(self) -> dict:
        """Get detailed task status."""
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", self.TASK_NAME, "/V", "/FO", "LIST"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"installed": False}
        
        status = {"installed": True}
        for line in result.stdout.split("\n"):
            if "Status:" in line:
                status["task_status"] = line.split(":")[-1].strip()
            elif "Last Result:" in line:
                status["last_result"] = line.split(":")[-1].strip()
            elif "Last Run Time:" in line:
                status["last_run"] = line.split(":", 1)[-1].strip()
        
        return status
    
    def install(self, elevate: bool = False, for_user: str = None) -> bool:
        """Install the Task Scheduler task."""
        target_user = for_user or os.environ.get("USERNAME", "")
        target_user_domain = os.environ.get("USERDOMAIN", "")
        
        # If elevate requested, restart as admin
        if elevate:
            current_user = os.environ.get("USERNAME", "")
            print(f"Requesting administrator privileges (for user: {current_user})...")
            subprocess.run([
                "powershell", "-Command",
                f"Start-Process powershell -Verb RunAs -ArgumentList '-NoExit -ExecutionPolicy Bypass -Command \"& ''{self.python_exe}'' -m uvicoord_windows.cli service install --for-user {current_user}; Write-Host; Read-Host ''Press Enter to close''\"'"
            ])
            return True
        
        # Use pythonw if available (no console window)
        exe_to_use = self.pythonw_exe if Path(self.pythonw_exe).exists() else self.python_exe
        
        # Full user identifier
        full_user = f"{target_user_domain}\\{target_user}" if target_user_domain and target_user else target_user
        
        # Create task XML
        task_xml = self._generate_task_xml(exe_to_use, full_user)
        
        # Write XML to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-16') as f:
            f.write(task_xml)
            xml_path = f.name
        
        try:
            result = subprocess.run(
                ["schtasks", "/Create", "/TN", self.TASK_NAME, "/XML", xml_path, "/F"],
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                if "access is denied" in result.stderr.lower():
                    print("Error: Administrator privileges required.")
                    print("\nOptions:")
                    print("  1. Run with --elevate flag: uvicoord service install --elevate")
                    print("  2. Run terminal as Administrator")
                    return False
                else:
                    print(f"Error installing service: {result.stderr}")
                    return False
            
            print("Uvicoord installed as startup task.")
            
            # Add to PATH
            self._add_to_path(for_user)
            
            print("\nStart the service now? Run: uvicoord service start")
            return True
            
        finally:
            Path(xml_path).unlink(missing_ok=True)
    
    def uninstall(self, elevate: bool = False) -> bool:
        """Remove the Task Scheduler task."""
        if elevate:
            print("Requesting administrator privileges...")
            subprocess.run([
                "powershell", "-Command",
                f"Start-Process powershell -Verb RunAs -ArgumentList '-NoExit -ExecutionPolicy Bypass -Command \"& ''{self.python_exe}'' -m uvicoord_windows.cli service uninstall; Write-Host; Read-Host ''Press Enter to close''\"'"
            ])
            return True
        
        # Stop if running
        subprocess.run(["schtasks", "/End", "/TN", self.TASK_NAME], capture_output=True)
        
        # Delete the task
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", self.TASK_NAME, "/F"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print("Uvicoord startup task removed.")
            return True
        elif "access is denied" in result.stderr.lower():
            print("Error: Administrator privileges required.")
            print("\nOptions:")
            print("  1. Run with --elevate flag: uvicoord service uninstall --elevate")
            print("  2. Run terminal as Administrator")
            return False
        else:
            print(f"Could not remove task (may not exist): {result.stderr}")
            return False
    
    def start(self) -> bool:
        """Start the service via Task Scheduler."""
        result = subprocess.run(
            ["schtasks", "/Run", "/TN", self.TASK_NAME],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Service started via Task Scheduler.")
            return True
        print(f"Failed to start: {result.stderr}")
        return False
    
    def stop(self) -> bool:
        """Stop the service via Task Scheduler."""
        result = subprocess.run(
            ["schtasks", "/End", "/TN", self.TASK_NAME],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Service stopped.")
            return True
        return False
    
    def _generate_task_xml(self, exe_path: str, user: str) -> str:
        """Generate Task Scheduler XML configuration."""
        working_dir = Path(exe_path).parent.parent
        
        return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Uvicorn Coordinator - Port registry for Python web applications</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{user}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions>
    <Exec>
      <Command>{exe_path}</Command>
      <Arguments>-m uvicoord.service.main</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
    
    def _add_to_path(self, for_user: str = None) -> None:
        """Add Scripts directory to user PATH."""
        import winreg
        
        scripts_dir = Path(sys.executable).parent
        current_user = os.environ.get("USERNAME", "")
        
        if for_user and for_user != current_user:
            # Adding to another user's PATH via registry (when elevated)
            try:
                sid_result = subprocess.run(
                    ["powershell", "-Command", 
                     f"(New-Object System.Security.Principal.NTAccount('{for_user}')).Translate([System.Security.Principal.SecurityIdentifier]).Value"],
                    capture_output=True,
                    text=True,
                )
                user_sid = sid_result.stdout.strip()
                
                if user_sid:
                    path_result = subprocess.run(
                        ["reg", "query", f"HKU\\{user_sid}\\Environment", "/v", "Path"],
                        capture_output=True,
                        text=True,
                    )
                    
                    current_path = ""
                    if path_result.returncode == 0:
                        for line in path_result.stdout.split('\n'):
                            if 'Path' in line and 'REG_' in line:
                                parts = line.split('REG_EXPAND_SZ')
                                if len(parts) > 1:
                                    current_path = parts[1].strip()
                                    break
                                parts = line.split('REG_SZ')
                                if len(parts) > 1:
                                    current_path = parts[1].strip()
                                    break
                    
                    if str(scripts_dir) not in current_path:
                        new_path = f"{current_path};{scripts_dir}" if current_path else str(scripts_dir)
                        set_result = subprocess.run(
                            ["reg", "add", f"HKU\\{user_sid}\\Environment", "/v", "Path", 
                             "/t", "REG_EXPAND_SZ", "/d", new_path, "/f"],
                            capture_output=True,
                            text=True,
                        )
                        if set_result.returncode == 0:
                            print(f"Added to {for_user}'s PATH: {scripts_dir}")
                            print("Restart your terminal for PATH changes to take effect.")
                        else:
                            print(f"Could not add to PATH: {set_result.stderr}")
                    else:
                        print(f"Already in {for_user}'s PATH")
            except Exception as e:
                print(f"Could not add to PATH: {e}")
        else:
            # Add to current user's PATH
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Environment", 0, 
                    winreg.KEY_READ | winreg.KEY_WRITE
                )
                try:
                    user_path, _ = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    user_path = ""
                
                if str(scripts_dir) not in user_path:
                    new_path = f"{user_path};{scripts_dir}" if user_path else str(scripts_dir)
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    print(f"Added to user PATH: {scripts_dir}")
                    print("Restart your terminal for PATH changes to take effect.")
                winreg.CloseKey(key)
            except Exception as e:
                print(f"Could not add to PATH: {e}")
