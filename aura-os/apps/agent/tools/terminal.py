import subprocess
from tools.base import registry

@registry.register(
    name="execute_command",
    description="Executes a command line instruction in the Windows PowerShell shell and returns its stdout/stderr output.",
    risk_level="DANGEROUS",
    required_permission="execution"
)
def execute_command(command: str = None, **kwargs) -> str:
    cmd = command or kwargs.get("cmd") or kwargs.get("script") or kwargs.get("command_line") or kwargs.get("terminal_command")
    if not cmd:
        return "Error: No command string provided."
    try:
        # Run PowerShell command
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=30 # Prevent hangs
        )
        output = ""
        if result.stdout:
            output += f"Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Errors:\n{result.stderr}\n"
            
        if not output.strip():
            return f"Command executed successfully (exit code: {result.returncode}), but returned no output."
            
        return output
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Failed to execute command: {e}"
