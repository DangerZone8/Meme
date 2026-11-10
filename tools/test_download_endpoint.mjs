import test from "node:test";
import assert from "node:assert/strict";
import handler from "../api/download.js";

function response() {
  return { headers: {}, code: 200, body: undefined,
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; return this; },
    status(code) { this.code = code; return this; },
    send(body) { this.body = body; return this; },
    end(body) { this.body = body; return this; }
  };
}

const validUrl = "https://screenfilter.public.blob.vercel-storage.com/its-giving/ItsGiving-Desktop-0.3.0-Windows.exe?download=1";
test("GET redirects directly to the public portable Windows EXE", () => {
  process.env.WINDOWS_APP_URL = validUrl;
  const res = response(); handler({ method: "GET" }, res);
  assert.equal(res.code, 302); assert.equal(res.headers.location, validUrl);
  assert.match(res.headers["cache-control"], /max-age=60/);
});
test("HEAD uses the same direct EXE URL", () => {
  process.env.WINDOWS_APP_URL = validUrl;
  const res = response(); handler({ method: "HEAD" }, res);
  assert.equal(res.code, 302); assert.equal(res.headers.location, validUrl);
});
test("returns a clear 503 until the direct EXE URL is configured", () => {
  delete process.env.WINDOWS_APP_URL;
  const res = response(); handler({ method: "GET" }, res);
  assert.equal(res.code, 503);
  assert.equal(res.body, "The direct Windows download is not configured yet.");
  assert.equal(res.headers["cache-control"], "no-store");
});
test("rejects non-HTTPS, non-Blob, and non-EXE download targets", () => {
  for (const invalid of ["http://screenfilter.public.blob.vercel-storage.com/app.exe", "https://example.com/app.exe", "https://screenfilter.public.blob.vercel-storage.com/app.zip"]) {
    process.env.WINDOWS_APP_URL = invalid;
    const res = response(); handler({ method: "GET" }, res); assert.equal(res.code, 503, invalid);
  }
  delete process.env.WINDOWS_APP_URL;
});
test("rejects methods other than GET and HEAD", () => {
  const res = response(); handler({ method: "POST" }, res);
  assert.equal(res.code, 405); assert.equal(res.headers.allow, "GET, HEAD");
});
