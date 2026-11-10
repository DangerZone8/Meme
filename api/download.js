function resolveDownloadUrl() {
  const raw = process.env.WINDOWS_APP_URL;
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || !url.hostname.endsWith(".public.blob.vercel-storage.com") || !url.pathname.toLowerCase().endsWith(".exe")) return null;
    return url.toString();
  } catch { return null; }
}

export default function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }
  const downloadUrl = resolveDownloadUrl();
  if (!downloadUrl) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(503).end("The direct Windows download is not configured yet.");
  }
  res.setHeader("Cache-Control", "public, max-age=60, stale-while-revalidate=300");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Location", downloadUrl);
  return res.status(302).end();
}
