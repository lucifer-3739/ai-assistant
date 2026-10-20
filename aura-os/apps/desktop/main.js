const { app, BrowserWindow } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let backendProcess = null;
let frontendProcess = null;
let isShuttingDown = false;

// Helper: Kills entire process tree by PID on Windows
function killProcessTree(pid) {
  if (!pid) return;
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /F /T /PID ${pid}`, { stdio: 'ignore' });
    } else {
      process.kill(-pid, 'SIGKILL');
    }
  } catch (e) {
    // Ignore already terminated processes
  }
}

// Helper: Clean up any lingering processes on ports 8000 and 3000
function killPortOccupants(port) {
  if (process.platform !== 'win32') return;
  try {
    const output = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] });
    const lines = output.trim().split('\n');
    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      const pid = parts[parts.length - 1];
      if (pid && pid !== '0' && pid !== process.pid.toString()) {
        try {
          execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
          console.log(`[Lifecycle] Cleared process ${pid} on port ${port}`);
        } catch (_) {}
      }
    }
  } catch (_) {}
}

function cleanupAllProcesses() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log('[Lifecycle] Initiating complete shutdown & child process cleanup...');
  
  if (backendProcess && backendProcess.pid) {
    killProcessTree(backendProcess.pid);
    backendProcess = null;
  }
  if (frontendProcess && frontendProcess.pid) {
    killProcessTree(frontendProcess.pid);
    frontendProcess = null;
  }
  
  // Safety purge for ports 8000 and 3000
  killPortOccupants(8000);
  killPortOccupants(3000);
  console.log('[Lifecycle] All NOVA OS processes terminated cleanly.');
}

function checkPortOnline(port, pathName, callback) {
  const req = http.get({ host: '127.0.0.1', port: port, path: pathName }, (res) => {
    callback(true);
  });
  req.on('error', () => {
    callback(false);
  });
  req.setTimeout(800, () => {
    req.destroy();
    callback(false);
  });
}

function startBackend() {
  checkPortOnline(8000, '/', (isOnline) => {
    if (isOnline) {
      console.log('[Desktop Shell] Backend is already active on http://127.0.0.1:8000');
      return;
    }

    const backendPath = path.resolve(__dirname, '..', 'agent');
    const pythonExe = path.resolve(__dirname, '..', '..', '.venv', 'Scripts', 'python.exe');
    const scriptPath = path.resolve(backendPath, 'main.py');
    
    console.log(`[Desktop Shell] Starting backend engine: ${pythonExe}`);
    
    try {
      backendProcess = spawn(pythonExe, [scriptPath], {
        cwd: backendPath,
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
        stdio: 'ignore'
      });

      backendProcess.on('error', (err) => {
        console.error('[Backend Spawn Error]', err.message);
      });
    } catch (err) {
      console.error('[Backend Exception]', err.message);
    }
  });
}

function startFrontend() {
  checkPortOnline(3000, '/', (isOnline) => {
    if (isOnline) {
      console.log('[Desktop Shell] Frontend server active on http://localhost:3000');
      return;
    }

    const frontendPath = path.resolve(__dirname, '..', 'frontend');
    console.log(`[Desktop Shell] Starting Next.js frontend in background...`);
    
    try {
      frontendProcess = spawn('npm.cmd', ['run', 'dev'], {
        cwd: frontendPath,
        env: { ...process.env, PORT: '3000' },
        shell: true,
        stdio: 'ignore'
      });

      frontendProcess.on('error', (err) => {
        console.error('[Frontend Spawn Error]', err.message);
      });
    } catch (err) {
      console.error('[Frontend Exception]', err.message);
    }
  });
}

const loadingHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>NOVA OS - Loading</title>
  <style>
    body {
      background: #020610;
      color: #00f0ff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      user-select: none;
      overflow: hidden;
    }
    .core {
      width: 70px;
      height: 70px;
      border: 3px solid rgba(0, 240, 255, 0.2);
      border-top: 3px solid #00f0ff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      box-shadow: 0 0 30px rgba(0, 240, 255, 0.4);
      margin-bottom: 24px;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    h2 {
      margin: 0 0 8px 0;
      letter-spacing: 4px;
      font-size: 15px;
      font-weight: 900;
      text-shadow: 0 0 15px rgba(0, 240, 255, 0.8);
    }
    p {
      color: rgba(0, 240, 255, 0.7);
      font-size: 11px;
      letter-spacing: 2px;
      margin: 0;
    }
  </style>
</head>
<body>
  <div class="core"></div>
  <h2>STARK INDUSTRIES // NOVA OS</h2>
  <p id="status">CONNECTING NEURAL ENGINE & SERVICES...</p>
</body>
</html>
`;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: "NOVA OS - Stark Industries Cockpit",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    autoHideMenuBar: true,
    backgroundColor: '#020610'
  });

  // Load sleek loading screen first
  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(loadingHtml)}`);

  // Start background services
  startBackend();
  startFrontend();

  // Poll until frontend port 3000 is ready, then transition seamlessly
  let attempts = 0;
  const pollInterval = setInterval(() => {
    attempts++;
    checkPortOnline(3000, '/', (ready) => {
      if (ready && mainWindow) {
        clearInterval(pollInterval);
        mainWindow.loadURL('http://localhost:3000');
      } else if (attempts > 60) {
        // Fallback after 30s
        clearInterval(pollInterval);
        if (mainWindow) mainWindow.loadURL('http://localhost:3000');
      }
    });
  }, 500);

  mainWindow.webContents.on('did-fail-load', () => {
    setTimeout(() => {
      if (mainWindow) mainWindow.loadURL('http://localhost:3000');
    }, 1000);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    cleanupAllProcesses();
    app.exit(0);
  });
}

app.on('ready', () => {
  createWindow();
});

app.on('before-quit', cleanupAllProcesses);
app.on('will-quit', cleanupAllProcesses);
app.on('window-all-closed', () => {
  cleanupAllProcesses();
  app.exit(0);
});

process.on('SIGINT', () => {
  cleanupAllProcesses();
  process.exit(0);
});
process.on('SIGTERM', () => {
  cleanupAllProcesses();
  process.exit(0);
});
