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

test("GET redirects to the repository-hosted static Windows executable without env vars", () => {
  delete process.env.WINDOWS_APP_URL;
  delete process.env.BLOB_READ_WRITE_TOKEN;
  delete process.env.VERCEL_TOKEN;
  const res = response();
  handler({ method: "GET" }, res);
  assert.equal(res.code, 307);
  assert.equal(res.headers.location, "/downloads/ItsGiving.exe");
  assert.match(res.headers["cache-control"], /public/);
});

test("HEAD uses the same static download destination", () => {
  const res = response();
  handler({ method: "HEAD" }, res);
  assert.equal(res.code, 307);
  assert.equal(res.headers.location, "/downloads/ItsGiving.exe");
});

test("rejects methods other than GET and HEAD", () => {
  const res = response();
  handler({ method: "POST" }, res);
  assert.equal(res.code, 405);
  assert.equal(res.headers.allow, "GET, HEAD");
});
