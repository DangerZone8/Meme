const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn, execFile } = require("node:child_process");
const path = require("node:path");

let win;
let worker = null;
let workerLog = [];

function send(channel, payload) {
  if (win && !win.isDestroyed()) win.webContents.send(channel, payload);
}
function addLog(line) {
  const clean = String(line).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "").trim();
  if (!clean) return;
  workerLog.push(clean);
  workerLog = workerLog.slice(-120);
  send("app:log", clean);
}
function createWindow() {
  win = new BrowserWindow({
    width: 900, height: 680, minWidth: 760, minHeight: 580,
    backgroundColor: "#101018",
    title: "ScreenFilter",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true, nodeIntegration: false, sandbox: true
    }
  });
  win.on("close", () => { if (worker) worker.kill(); });
  win.loadFile(path.join(__dirname, "index.html"));
}
function executablePath() {
  return app.isPackaged
    ? path.join(process.resourcesPath, "ItsGiving.exe")
    : path.resolve(__dirname, "resources", "ItsGiving.exe");
}
function startEngine(options = {}) {
  if (worker) return { ok: false, message: "Meme camera is already running." };
  const exe = executablePath();
  const fs = require("node:fs");
  if (!fs.existsSync(exe)) return { ok: false, message: "ItsGiving.exe is missing. Rebuild the desktop package." };
  const args = [];
  if (Number.isInteger(options.camera) && options.camera >= 0 && options.camera <= 9) args.push("--camera", String(options.camera));
  if (options.size === "640x480") args.push("--size", "640x480");
  if (options.noVirtualCamera) args.push("--no-vcam");
  try {
    worker = spawn(exe, args, { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
    send("app:state", { running: true });
    worker.stdout.on("data", chunk => chunk.toString().split(/\r?\n/).forEach(addLog));
    worker.stderr.on("data", chunk => chunk.toString().split(/\r?\n/).forEach(addLog));
    worker.on("error", err => { addLog("Launch error: " + err.message); worker = null; send("app:state", { running: false }); });
    worker.on("exit", (code, signal) => {
      addLog("Meme engine stopped (code " + code + (signal ? ", signal " + signal : "") + ").");
      worker = null; send("app:state", { running: false });
    });
    return { ok: true, message: "Meme engine starting." };
  } catch (error) {
    worker = null;
    return { ok: false, message: error.message };
  }
}
function setupVirtualCamera() {
  const fs = require("node:fs");
  const script = app.isPackaged
    ? path.join(process.resourcesPath, "VirtualCameraSetup.ps1")
    : path.resolve(__dirname, "../scripts/setup_virtual_camera.ps1");
  if (!fs.existsSync(script)) return Promise.resolve({ ok: false, message: "Virtual-camera setup script is missing. Reinstall ScreenFilter." });
  return new Promise(resolve => {
    execFile("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
      { windowsHide: true, timeout: 15 * 60 * 1000, maxBuffer: 1024 * 1024 },
      (error, stdout, stderr) => {
        const output = [stdout, stderr].filter(Boolean).join("\\n").trim();
        if (output) addLog(output);
        resolve(error ? { ok: false, message: output || error.message } :
          { ok: true, message: "Virtual-camera setup completed. Restart ScreenFilter and select OBS Virtual Camera in your meeting app." });
      });
  });
}
function stopEngine() {
  if (!worker) return { ok: true, message: "Meme engine is not running." };
  worker.kill();
  return { ok: true, message: "Stop requested." };
}
app.whenReady().then(() => {
  ipcMain.handle("engine:start", (_event, options) => startEngine(options));
  ipcMain.handle("engine:stop", () => stopEngine());
  ipcMain.handle("engine:status", () => ({ running: !!worker, logs: workerLog }));
  ipcMain.handle("app:virtual-camera-setup", () => setupVirtualCamera());
  createWindow();
});
app.on("before-quit", () => { if (worker) worker.kill(); });
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
