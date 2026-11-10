const $ = id => document.getElementById(id);
const log = line => { const box=$("logs"); box.textContent += "\n"+line; box.scrollTop=box.scrollHeight; };
function state(running) {
  $("status").textContent = running ? "Running" : "Stopped";
  $("status").classList.toggle("running", running);
  $("start").disabled = running; $("stop").disabled = !running;
}
$("start").addEventListener("click", async () => {
  const result = await window.itsGiving.start({
    camera: Number($("camera").value), size: $("size").value
  });
  log(result.message); if (!result.ok) log("Check the executable and camera permissions.");
});
$("stop").addEventListener("click", async () => { const result=await window.itsGiving.stop(); log(result.message); });
$("obs").addEventListener("click", () => window.itsGiving.obsHelp());
window.itsGiving.onState(value => state(value.running));
window.itsGiving.onLog(log);
window.itsGiving.status().then(value => { state(value.running); value.logs.forEach(log); });
