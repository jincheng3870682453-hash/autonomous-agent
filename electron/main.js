const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let apiProcess = null;

const API_PORT = 8000;
const DASHBOARD_URL = `http://localhost:${API_PORT}`;

function startApiServer() {
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  apiProcess = spawn(pythonPath, ['run.py', 'api'], {
    cwd: path.join(__dirname, '..'),
    stdio: 'pipe',
    shell: process.platform === 'win32'
  });

  apiProcess.stdout.on('data', (data) => {
    console.log(`[API] ${data}`);
  });

  apiProcess.stderr.on('data', (data) => {
    console.log(`[API] ${data}`);
  });

  apiProcess.on('error', (err) => {
    console.error(`[API] Failed to start: ${err.message}`);
  });

  apiProcess.on('close', (code) => {
    console.log(`[API] Process exited with code ${code}`);
  });
}

async function waitForServer(url, maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const http = require('http');
      await new Promise((resolve, reject) => {
        http.get(url, (res) => {
          if (res.statusCode < 500) resolve();
          else reject(new Error(`Status ${res.statusCode}`));
        }).on('error', reject);
      });
      console.log(`[Electron] Server ready at ${url}`);
      return true;
    } catch {
      await new Promise(r => setTimeout(r, 1000));
    }
  }
  console.error('[Electron] Server did not start in time');
  return false;
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'Autonomous Agent',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  startApiServer();
  const ready = await waitForServer(DASHBOARD_URL);

  if (ready) {
    mainWindow.loadURL(DASHBOARD_URL);
  } else {
    mainWindow.loadURL(`data:text/html,
      <h1>Server Failed to Start</h1>
      <p>Please ensure Python and dependencies are installed.</p>
    `);
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', createWindow);

app.on('window-all-closed', () => {
  if (apiProcess) {
    apiProcess.kill();
    apiProcess = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (apiProcess) {
    apiProcess.kill();
    apiProcess = null;
  }
});
