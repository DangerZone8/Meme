const WINDOWS_EXE_URL = "https://github.com/DangerZone8/Meme/releases/latest/download/ItsGiving-Desktop-0.3.0-Windows.exe";

export default function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Location", WINDOWS_EXE_URL);
  return res.status(302).end();
}
