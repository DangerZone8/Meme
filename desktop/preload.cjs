const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("itsGiving", {
  start: options => ipcRenderer.invoke("engine:start", options),
  stop: () => ipcRenderer.invoke("engine:stop"),
  status: () => ipcRenderer.invoke("engine:status"),
  setupVirtualCamera: () => ipcRenderer.invoke("app:virtual-camera-setup"),
  onState: callback => ipcRenderer.on("app:state", (_event, value) => callback(value)),
  onLog: callback => ipcRenderer.on("app:log", (_event, value) => callback(value))
});
