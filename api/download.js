export default async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }

  const target = process.env.WINDOWS_INSTALLER_URL;
  if (!target) {
    return res.status(503).send("Windows installer is not published yet. Please try again later.");
  }

  let url;
  try {
    url = new URL(target);
  } catch {
    return res.status(500).send("Windows installer URL is misconfigured.");
  }
  if (url.protocol !== "https:" || !url.hostname.endsWith(".blob.vercel-storage.com")) {
    return res.status(500).send("Windows installer URL must be a public Vercel Blob URL.");
  }

  try {
    const upstream = await fetch(url, { method: req.method, redirect: "follow" });
    if (!upstream.ok) {
      return res.status(502).send("The Windows installer is temporarily unavailable.");
    }
    res.setHeader("Content-Type", "application/vnd.microsoft.portable-executable");
    res.setHeader("Content-Disposition", 'attachment; filename="ItsGiving-Setup.exe"');
    res.setHeader("Cache-Control", "public, max-age=300, s-maxage=300");
    const length = upstream.headers.get("content-length");
    if (length) res.setHeader("Content-Length", length);
    if (req.method === "HEAD") return res.status(200).end();
    const buffer = Buffer.from(await upstream.arrayBuffer());
    return res.status(200).send(buffer);
  } catch {
    return res.status(502).send("Could not retrieve the Windows installer.");
  }
}
