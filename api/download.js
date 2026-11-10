const DOWNLOAD_URL = "https://nightly.link/DangerZone8/Meme/workflows/windows-app/main/ItsGiving-Electron-Portable-Windows-v0.3.0.zip";

export default function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }

  // nightly.link brokers anonymous downloads of public GitHub Actions
  // artifacts. It resolves the latest successful artifact from this workflow
  // and branch, so the website needs no GitHub or Vercel credentials.
  res.setHeader("Cache-Control", "public, max-age=60, stale-while-revalidate=300");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Location", DOWNLOAD_URL);
  return res.status(302).end();
}
