"""Static integration checks for the Electron controller and Python engine contract."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class DesktopContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads(read("desktop/package.json"))
        cls.main = read("desktop/main.cjs")
        cls.preload = read("desktop/preload.cjs")
        cls.renderer = read("desktop/renderer.js")
        cls.html = read("desktop/index.html")
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
        channels = {
            "start": "engine:start",
            "stop": "engine:stop",
            "status": "engine:status",
            "obsHelp": "app:obs-help",
        }
        for method, channel in channels.items():
            self.assertRegex(self.preload, rf"{method}:.*ipcRenderer\\.invoke\\(\"{re.escape(channel)}\"")
            self.assertIn(f'ipcMain.handle("{channel}"', self.main)
        for method in ("start", "stop", "status", "obsHelp", "onState", "onLog"):
            self.assertIn(f"window.itsGiving.{method}", self.renderer)
        self.assertIn('ipcRenderer.on("app:state"', self.preload)
        self.assertIn('ipcRenderer.on("app:log"', self.preload)

    def test_controller_html_contains_every_renderer_target(self):
        ids = set(re.findall(r'\\bid="([^"]+)"', self.html))
        self.assertTrue({"status", "camera", "size", "start", "stop", "obs", "logs"}.issubset(ids))

    def test_obs_instructions_match_direct_backend_usage(self):
        text = (self.html + self.main + self.help).lower()
        self.assertIn("close obs before starting", text)
        self.assertIn("obs virtual camera", text)
        self.assertNotIn("open obs and start its virtual camera", text)
        self.assertNotIn("start obs virtual camera; choose", text)


if __name__ == "__main__":
    unittest.main()
