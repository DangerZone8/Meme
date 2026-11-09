const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn } = require("node:child_process");
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
    title: "It's Giving",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true, nodeIntegration: false, sandbox: true
    }
  });
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
function stopEngine() {
  if (!worker) return { ok: true, message: "Meme engine is not running." };
  worker.kill();
  return { ok: true, message: "Stop requested." };
}
app.whenReady().then(() => {
  ipcMain.handle("engine:start", (_event, options) => startEngine(options));
  ipcMain.handle("engine:stop", () => stopEngine());
  ipcMain.handle("engine:status", () => ({ running: !!worker, logs: workerLog }));
  ipcMain.handle("app:obs-help", async () => {
    await dialog.showMessageBox(win, {
      type: "info", title: "Use It's Giving in a call",
      message: "Select OBS Virtual Camera in Zoom, Google Meet, Teams, or Discord.",
      detail: "Install OBS Studio once to register its Virtual Camera device. Close OBS before starting It's Giving: the app sends its processed frames directly to OBS Virtual Camera. Do not also click Start Virtual Camera inside OBS while It's Giving is using the device. If the camera is missing, install or repair OBS Studio, then restart It's Giving and the meeting app. Close other apps using the webcam if the physical camera is unavailable."
    });
  });
  createWindow();
});
app.on("before-quit", () => { if (worker) worker.kill(); });
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
