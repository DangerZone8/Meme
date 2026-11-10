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

const directExe = "https://github.com/DangerZone8/Meme/releases/latest/download/ItsGiving-Desktop-0.3.0-Windows.exe";
test("GET redirects directly to the portable Windows EXE release asset", () => {
  const res = response(); handler({ method: "GET" }, res);
  assert.equal(res.code, 302); assert.equal(res.headers.location, directExe);
  assert.equal(res.headers["cache-control"], "no-store");
});
test("HEAD redirects to the same direct EXE asset", () => {
  const res = response(); handler({ method: "HEAD" }, res);
  assert.equal(res.code, 302); assert.equal(res.headers.location, directExe);
});
test("does not require runtime environment variables or storage secrets", () => {
  assert.doesNotThrow(() => handler({ method: "GET" }, response()));
});
test("rejects methods other than GET and HEAD", () => {
  const res = response(); handler({ method: "POST" }, res);
  assert.equal(res.code, 405); assert.equal(res.headers.allow, "GET, HEAD");
});
