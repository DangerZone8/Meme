export default async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }

  const target = process.env.WINDOWS_APP_URL;
  if (!target) {
    return res.status(503).send("The portable Windows app is not published yet.");
  }

  let url;
  try {
    url = new URL(target);
  } catch {
    return res.status(500).send("Windows app URL is misconfigured.");
  }
  if (url.protocol !== "https:") {
    return res.status(500).send("Windows app URL must use HTTPS.");
  }

  try {
    const upstream = await fetch(url, { method: req.method, redirect: "follow" });
    if (!upstream.ok) return res.status(502).send("The Windows app is temporarily unavailable.");
    res.setHeader("Content-Type", "application/vnd.microsoft.portable-executable");
    res.setHeader("Content-Disposition", 'attachment; filename="ItsGiving.exe"');
    res.setHeader("Cache-Control", "public, max-age=300, s-maxage=300");
    const length = upstream.headers.get("content-length");
    if (length) res.setHeader("Content-Length", length);
    if (req.method === "HEAD") return res.status(200).end();
    return res.status(200).send(Buffer.from(await upstream.arrayBuffer()));
  } catch {
    return res.status(502).send("Could not retrieve the portable Windows app.");
  }
}
