export default async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }

  const configuredUrl = process.env.WINDOWS_APP_URL;
  if (!configuredUrl) {
    return res.status(503).send("The portable Windows app has not been published yet.");
  }

  let downloadUrl;
  try {
    downloadUrl = new URL(configuredUrl);
  } catch {
    return res.status(500).send("Windows app URL is misconfigured.");
  }

  // Only redirect to the public Vercel Blob store used by the publishing
  // workflow. This prevents WINDOWS_APP_URL from becoming an open redirect.
  if (
    downloadUrl.protocol !== "https:" ||
    !downloadUrl.hostname.endsWith(".public.blob.vercel-storage.com") ||
    !downloadUrl.pathname.endsWith("/ItsGiving.exe")
  ) {
    return res.status(500).send("Windows app URL must point to the published ItsGiving.exe Vercel Blob.");
  }

  // Vercel Blob's downloadUrl adds this query parameter so browsers receive
  // Content-Disposition: attachment instead of trying to display the file.
  if (!downloadUrl.searchParams.has("download")) {
    downloadUrl.searchParams.set("download", "1");
  }

  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Location", downloadUrl.toString());
  return res.status(307).end();
}
