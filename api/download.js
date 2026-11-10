export default function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }

  // The executable is committed to public/downloads by the reviewed
  // download-publication PR. No Blob, Vercel environment variables, or
  // server-side proxy is required at runtime.
  res.setHeader("Cache-Control", "public, max-age=300, must-revalidate");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Location", "/downloads/ItsGiving.exe");
  return res.status(307).end();
}
