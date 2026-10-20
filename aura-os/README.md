# AURA OS — AI-Native Voice-Controlled Computer Agent (Phase 1)

AURA OS is an AI-native computer assistant designed to understand natural-language commands, formulate step-by-step task plans, execute local actions (system apps, filesystem operations, power options), programmatically verify outcomes, and manage security parameters safely.

---

## 1. What was Implemented in Phase 1

- **Core Agent & Planning Loop**:
  - `AIProvider` abstractions enabling swappable cloud/local LLM providers. Currently uses Gemini 3.5 Flash via official `google-genai` SDK.
  - `Planner` that maps user queries into sequential JSON plans (step descriptions, tools, arguments).
  - `Verifier` implementing programmatic state checks (e.g., verifying if files/folders were created or apps are running on Windows) rather than trusting command output.
  - `Executor` running tools, managing security gates, and recording logs.
  - `Orchestrator` leading the lifecycle of planning, executing, and observing state machine updates.
- **SQLite Database Integration**:
  - Automatically initializes tables for tracking `tasks`, `plan_steps`, `audit_log`, and `memory`.
- **Security Checkpoints & Auditing**:
  - Categorizes tools by risk levels (`SAFE`, `MODERATE`, `DANGEROUS`, `CRITICAL`).
  - Asynchronously suspends thread execution (`asyncio.Event`) when dangerous/critical tools are requested, awaiting user confirmation before executing.
  - Securely logs all operations in an `audit_log` database table with sensitive key redactions.
- **Local Tools catalog**:
  - **Filesystem**: create/read/write/copy/move/delete files, create folders, list directories, search files.
  - **System**: open/close Windows applications (Notepad, Chrome, calc, Spotify, File Explorer), query system specs.
  - **Terminal**: execute arbitrary PowerShell commands (requires security approval).
- **FastAPI Backend Server & WebSockets**:
  - Implements REST endpoints for commands, tasks lookup, permission approvals, and security audit logs.
  - Exposes `/api/ws` WebSockets gateway for pushing real-time state machine updates to UI.
- **Next.js React standalone Client**:
  - Built with TypeScript and Tailwind CSS v4 using Next.js App Router.
  - Displays connection indicators, live system telemetries (CPU, RAM load gauges), tools directory, dynamic plan checkpoints, and auditing records.
- **Electron Container Shell**:
  - Spawns Python FastAPI on startup, loads Next.js dev server (on port 3000) in a standalone window, and kills the python backend cleanly upon closing.

---

## 2. Directory Structure

```
aura-os/
├── apps/
│   ├── desktop/                 # Electron shell wrapper container
│   │   ├── main.js
│   │   └── package.json
│   ├── frontend/                # Next.js standalone cockpit UI
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── page.tsx     # Main cockpit client view
│   │   │   │   ├── globals.css  # Tailwind imports
│   │   │   │   └── layout.tsx
│   │   ├── next.config.ts
│   │   └── package.json
│   └── agent/                   # Python agent backend
│       ├── core/                # Orchestrator, Planner, Executor, Verifier
│       ├── tools/               # Registry, Filesystem, System, Terminal
│       ├── security/            # Permission manager, Audit logger
│       ├── database/            # SQLite connector and schemas
│       ├── config/              # Configuration loaders
│       ├── tests/               # Unit and E2E integration tests
│       ├── main.py              # FastAPI WebSockets entrypoint
│       └── requirements.txt     # Python backend dependencies
├── start-aura.bat               # One-click startup script
├── run.txt                      # Short run instructions
└── README.md
```

---

## 3. Installation Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.14 on Windows)
- Node.js & npm (Tested on Node 20+)
- Windows OS (target platform for Phase 1 automation commands)

### Steps
1. Navigate to the project root directory:
   ```powershell
   cd "D:\Ai Voice assistant\aura-os"
   ```
2. The start script will automatically check, compile, and configure the application. Alternatively, to prepare directories manually:
   - **Backend**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\pip install -r apps/agent/requirements.txt
     ```
   - **Frontend & Electron**:
     ```powershell
     cd apps/frontend
     npm install
     cd ../desktop
     npm install
     ```

---

## 4. How to Run

1. Open [apps/agent/.env](file:///d:/Ai%20Voice%20assistant/aura-os/apps/agent/.env) and configure your `GEMINI_API_KEY`.
2. Double click the **`start-aura.bat`** script in the project root:
   ```powershell
   .\start-aura.bat
   ```
   This compiles the Next.js client, opens the Electron application window, and launches the local Python API backend in the background.

---

## 5. Tests Available

- **Unit tests**: Tests registries, permission gates, and verifier logic.
  ```powershell
  .venv\Scripts\python apps/agent/tests/test_agent.py
  ```
- **E2E Integration tests**: Starts a mock backend server, sends an actual `"Open Notepad"` request, polls progress, verifies process detection on Windows, and queries SQLite audit logs.
  ```powershell
  .venv\Scripts\python apps/agent/tests/test_e2e.py
  ```

---

## 6. Known Limitations in Phase 1

1. **Platform Lock**: OS integration commands (process listing, program spawning) are targeted at Windows APIs and terminals.
2. **Text-only Inputs**: Interaction is limited to typing instructions in the UI text box. Wake words and Speech-to-text recognition are scheduled for Phase 2.
3. **Mock Telemetries**: Telemetry graphs on the React panel are mocked for design visuals. Real hardware probes will be added in system tools later.
4. **Local LLM**: Abstractions are designed, but standard config assumes Cloud APIs. Local models (Ollama/Llama.cpp) require setting up local wrappers.

---

## 7. Recommended Next Phase

### Phase 2: Voice Pipeline Implementation
- Implement the voice abstractions (`SpeechToTextProvider`, `TextToSpeechProvider`, `WakeWordProvider`).
- Integrate a local wake-word trigger engine (e.g. using Porcupine or simple pocketsphinx).
- Hook microphone capture and streaming client into FastAPI via WebSockets.
- Add support for interruption ("Stop" command) to cancel active orchestrator tasks safely.
