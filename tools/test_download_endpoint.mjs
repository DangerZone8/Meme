import test from "node:test";
import assert from "node:assert/strict";
import handler from "../api/download.js";

function response() {
  return {
    headers: {},
    code: 200,
    body: undefined,
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; return this; },
    status(code) { this.code = code; return this; },
    send(body) { this.body = body; return this; },
    end(body) { this.body = body; return this; }
  };
}

const originalUrl = process.env.WINDOWS_APP_URL;

test.afterEach(() => {
  if (originalUrl === undefined) delete process.env.WINDOWS_APP_URL;
  else process.env.WINDOWS_APP_URL = originalUrl;
});

test("GET redirects to the public Blob download URL with attachment mode", () => {
  process.env.WINDOWS_APP_URL =
    "https://store.public.blob.vercel-storage.com/ItsGiving.exe";

  const res = response();
  handler({ method: "GET" }, res);

  assert.equal(res.code, 307);
  assert.equal(
    res.headers.location,
    "https://store.public.blob.vercel-storage.com/ItsGiving.exe?download=1"
  );
  assert.equal(res.headers["cache-control"], "no-store");
  assert.equal(res.body, undefined);
});

test("HEAD uses the same download redirect", () => {
  process.env.WINDOWS_APP_URL =
    "https://store.public.blob.vercel-storage.com/ItsGiving.exe?download=1";

  const res = response();
  handler({ method: "HEAD" }, res);

  assert.equal(res.code, 307);
  assert.equal(res.headers.location, process.env.WINDOWS_APP_URL);
});

test("missing published URL returns 503", () => {
  delete process.env.WINDOWS_APP_URL;
  const res = response();
  handler({ method: "GET" }, res);
  assert.equal(res.code, 503);
});

test("rejects non-Blob and non-HTTPS redirect targets", () => {
  for (const value of [
    "https://example.com/ItsGiving.exe",
    "http://store.public.blob.vercel-storage.com/ItsGiving.exe",
    "https://store.public.blob.vercel-storage.com/other.exe"
  ]) {
    process.env.WINDOWS_APP_URL = value;
    const res = response();
    handler({ method: "GET" }, res);
    assert.equal(res.code, 500, value);
  }
});

test("rejects methods other than GET and HEAD", () => {
  process.env.WINDOWS_APP_URL =
    "https://store.public.blob.vercel-storage.com/ItsGiving.exe";
  const res = response();
  handler({ method: "POST" }, res);
  assert.equal(res.code, 405);
  assert.equal(res.headers.allow, "GET, HEAD");
});
