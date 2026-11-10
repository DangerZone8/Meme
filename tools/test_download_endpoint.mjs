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

test("GET redirects to the latest anonymous Windows artifact without secrets", () => {
  delete process.env.WINDOWS_APP_URL;
  delete process.env.BLOB_READ_WRITE_TOKEN;
  delete process.env.VERCEL_TOKEN;
  const res = response();
  handler({ method: "GET" }, res);
  assert.equal(res.code, 302);
  assert.equal(
    res.headers.location,
    "https://nightly.link/DangerZone8/Meme/workflows/windows-app/main/ItsGiving-Electron-Portable-Windows-v0.3.0.zip"
  );
  assert.match(res.headers["cache-control"], /max-age=60/);
});

test("HEAD uses the same anonymous download URL", () => {
  const res = response();
  handler({ method: "HEAD" }, res);
  assert.equal(res.code, 302);
  assert.match(res.headers.location, /^https:\/\/nightly\.link\//);
});

test("rejects methods other than GET and HEAD", () => {
  const res = response();
  handler({ method: "POST" }, res);
  assert.equal(res.code, 405);
  assert.equal(res.headers.allow, "GET, HEAD");
});
