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

const originalFetch = global.fetch;
test.afterEach(() => { global.fetch = originalFetch; });

test("GET finds latest successful public Electron artifact without secrets", async () => {
  delete process.env.WINDOWS_APP_URL;
  delete process.env.BLOB_READ_WRITE_TOKEN;
  delete process.env.VERCEL_TOKEN;
  const requested = [];
  global.fetch = async url => {
    requested.push(String(url));
    if (String(url).includes("/workflows/windows-app.yml/runs")) {
      return { ok: true, json: async () => ({ workflow_runs: [
        { id: 123, head_branch: "main", conclusion: "success" }
      ] }) };
    }
    return { ok: true, json: async () => ({ artifacts: [
      { id: 456, name: "ItsGiving-Electron-Portable-Windows-v0.3.0", expired: false,
        archive_download_url: "https://api.github.com/repos/DangerZone8/Meme/actions/artifacts/456/zip" }
    ] }) };
  };

  const res = response();
  await handler({ method: "GET" }, res);
  assert.equal(res.code, 302);
  assert.equal(res.headers.location, "https://api.github.com/repos/DangerZone8/Meme/actions/artifacts/456/zip");
  assert.equal(requested.length, 2);
  assert.match(res.headers["cache-control"], /max-age=60/);
});

test("skips expired artifacts and returns 503 when no current build exists", async () => {
  global.fetch = async url => String(url).includes("/workflows/")
    ? { ok: true, json: async () => ({ workflow_runs: [
        { id: 123, head_branch: "main", conclusion: "success" }
      ] }) }
    : { ok: true, json: async () => ({ artifacts: [
        { id: 456, name: "ItsGiving-Electron-Portable-Windows-v0.3.0", expired: true }
      ] }) };

  const res = response();
  await handler({ method: "GET" }, res);
  assert.equal(res.code, 503);
});

test("returns 502 when GitHub API is unavailable", async () => {
  global.fetch = async () => ({ ok: false, status: 503 });
  const res = response();
  await handler({ method: "GET" }, res);
  assert.equal(res.code, 502);
});

test("rejects methods other than GET and HEAD", async () => {
  const res = response();
  await handler({ method: "POST" }, res);
  assert.equal(res.code, 405);
  assert.equal(res.headers.allow, "GET, HEAD");
});
