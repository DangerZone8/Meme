"""Static integration checks for the website, Electron shell, and engine contract."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class RepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads(read("desktop/package.json"))
        cls.web_package = json.loads(read("package.json"))
        cls.vercel = json.loads(read("vercel.json"))
        cls.engine_requirements = read("engine/requirements.txt")
        cls.main = read("desktop/main.cjs")
        cls.preload = read("desktop/preload.cjs")
        cls.renderer = read("desktop/renderer.js")
        cls.html = read("desktop/index.html")
        cls.website = read("index.html")
        cls.api = read("api/download.js")
        cls.help = read("README.md") + read("desktop/README.md")

    def test_packaged_files_and_engine_resource_are_declared(self):
        build = self.package["build"]
        self.assertEqual(self.package["main"], "main.cjs")
        self.assertTrue({"main.cjs", "preload.cjs", "index.html", "renderer.js"}.issubset(
            set(build["files"])
        ))
        self.assertIn(
            {"from": "resources/ItsGiving.exe", "to": "ItsGiving.exe"},
            build["extraResources"],
        )
        self.assertIn("dist:win", self.package["scripts"])

    def test_preload_renderer_and_main_share_the_same_ipc_contract(self):
        exposed_methods = {
            'start: options => ipcRenderer.invoke("engine:start", options)',
            'stop: () => ipcRenderer.invoke("engine:stop")',
            'status: () => ipcRenderer.invoke("engine:status")',
            'obsHelp: () => ipcRenderer.invoke("app:obs-help")',
        }
        for declaration in exposed_methods:
            self.assertIn(declaration, self.preload)
        for channel in ("engine:start", "engine:stop", "engine:status", "app:obs-help"):
            self.assertIn(f'ipcMain.handle("{channel}"', self.main)
        for method in ("start", "stop", "status", "obsHelp", "onState", "onLog"):
            self.assertIn(f"window.itsGiving.{method}", self.renderer)
        self.assertIn('ipcRenderer.on("app:state"', self.preload)
        self.assertIn('ipcRenderer.on("app:log"', self.preload)

    def test_controller_html_contains_every_renderer_target(self):
        ids = set(re.findall('id="([^"]+)"', self.html))
        self.assertTrue({"status", "camera", "size", "start", "stop", "obs", "logs"}.issubset(ids))

    def test_obs_instructions_match_direct_backend_usage(self):
        text = (self.html + self.main + self.help).lower()
        self.assertIn("close obs before starting", text)
        self.assertIn("obs virtual camera", text)
        self.assertNotIn("open obs and start its virtual camera", text)
        self.assertNotIn("start obs virtual camera; choose", text)

    def test_website_download_route_is_secretless_static_asset(self):
        rewrites = self.vercel.get("rewrites", [])
        self.assertIn(
            {"source": "/download", "destination": "/api/download"},
            rewrites,
        )
        self.assertIn('href="/download"', self.website)
        self.assertEqual(self.web_package.get("type"), "module")
        self.assertNotIn("WINDOWS_APP_URL", self.api)
        self.assertNotIn("BLOB_READ_WRITE_TOKEN", self.api)
        self.assertIn('"/downloads/ItsGiving.exe"', self.api)
        self.assertIn('res.status(307).end()', self.api)
        self.assertIn('req.method !== "GET" && req.method !== "HEAD"', self.api)
        download_headers = next(
            entry["headers"] for entry in self.vercel["headers"]
            if entry["source"] == "/downloads/(.*)"
        )
        header_values = {item["key"]: item["value"] for item in download_headers}
        self.assertIn("attachment", header_values["Content-Disposition"])
        self.assertEqual(
            header_values["Content-Type"],
            "application/vnd.microsoft.portable-executable",
        )

    def test_manual_publisher_uses_github_token_and_no_vercel_secrets(self):
        workflow = read(".github/workflows/windows-app.yml")
        self.assertIn("secrets.GITHUB_TOKEN", workflow)
        self.assertIn("gh pr create", workflow)
        self.assertIn("public/downloads/ItsGiving.exe", workflow)
        self.assertIn("95 * 1024 * 1024", workflow)
        for secret in (
            "BLOB_READ_WRITE_TOKEN", "VERCEL_TOKEN",
            "VERCEL_ORG_ID", "VERCEL_PROJECT_ID",
        ):
            self.assertNotIn(secret, workflow)

    def test_vercel_ignores_preview_deployments_but_builds_main(self):
        command = self.vercel.get("ignoreCommand", "")
        self.assertIn("VERCEL_GIT_COMMIT_REF", command)
        self.assertIn('= "main"', command)
        self.assertIn("then exit 1", command)
        self.assertIn("else exit 0", command)
        self.assertFalse((ROOT / "requirements.txt").exists())
        self.assertIn("mediapipe==0.10.21", self.engine_requirements)

    def test_vercel_publisher_matches_download_endpoint_contract(self):
        self.assertIn('put("ItsGiving.exe"', self.publisher)
        self.assertIn("createReadStream(filePath)", self.publisher)
        self.assertIn("multipart: true", self.publisher)
        self.assertIn("fileInfo.size < 50_000_000", self.publisher)
        self.assertIn('console.log("WINDOWS_APP_URL=" + blob.downloadUrl)', self.publisher)
        self.assertNotIn("VERCEL_INSTALLER_URL", self.publisher)
        self.assertNotIn("ItsGiving-Setup.exe", self.publisher)


if __name__ == "__main__":
    unittest.main()
