import requests
import time
import json
import sys
import subprocess
import os

# Start the backend server locally as a separate process for testing
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_python = os.path.join(backend_dir, "..", "..", ".venv", "Scripts", "python.exe")
main_script = os.path.join(backend_dir, "main.py")

print("[Test Launcher] Spinning up FastAPI backend server...")
server_process = subprocess.Popen(
    [venv_python, main_script],
    cwd=backend_dir,
    env={**os.environ, "AURA_PORT": "8080"} # run on port 8080 to avoid collision
)

# Wait for server startup
time.sleep(4)

BASE_URL = "http://127.0.0.1:8080"

try:
    print("\n--- [Step 1: Check server operational status] ---")
    status_res = requests.get(f"{BASE_URL}/")
    print(f"Status Response: {status_res.json()}")
    assert status_res.status_code == 200

    print("\n--- [Step 2: Submit natural language command: 'Open Notepad'] ---")
    cmd_payload = {"command": "Open Notepad"}
    cmd_res = requests.post(f"{BASE_URL}/api/command", json=cmd_payload)
    print(f"Submit Command Response: {cmd_res.json()}")
    assert cmd_res.status_code == 200
    task_id = cmd_res.json()["task_id"]

    print(f"\n--- [Step 3: Polling task progress for ID {task_id}] ---")
    max_polls = 10
    success = False
    
    for i in range(max_polls):
        time.sleep(2)
        task_res = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
        task_data = task_res.json()
        print(f"Poll #{i+1}: State: {task_data['state']}, Steps: {len(task_data['steps'])}")
        
        for step in task_data["steps"]:
            print(f"  - Step {step['step_number']}: {step['description']} (Status: {step['status']})")
            if step["result"]:
                print(f"    Result: {step['result']}")
                
        if task_data["state"] in ("COMPLETED", "FAILED"):
            if task_data["state"] == "COMPLETED":
                success = True
            break
            
    print(f"\nTask Finished: Success = {success}")

    print("\n--- [Step 4: Verify SQLite Audit Log records] ---")
    audit_res = requests.get(f"{BASE_URL}/api/audit")
    logs = audit_res.json()
    print(f"Total Audit entries: {len(logs)}")
    for l in logs[:3]:
        print(f"  - [{l['timestamp']}] Tool: {l['tool_name']}, Risk: {l['risk_level']}, Status: {l['permission_status']}")

    print("\n--- [Step 5: Verify SQLite Task History records] ---")
    tasks_history_res = requests.get(f"{BASE_URL}/api/tasks")
    history = tasks_history_res.json()
    print(f"Total History entries: {len(history)}")
    for t in history[:3]:
        print(f"  - Task ID: {t['id']}, Request: '{t['user_request']}', State: {t['state']}")

    # Clean up notepad process if we started it
    print("\nCleaning up notepad process...")
    subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)

    # Assert logic
    assert success == True
    print("\nE2E INTEGRATION TEST PASSED SUCCESSFULLY!")

except Exception as e:
    print(f"\nE2E TEST FAILED: {e}")
    sys.exit(1)
finally:
    print("\n[Test Launcher] Shutting down backend server process...")
    server_process.kill()
    server_process.wait()
