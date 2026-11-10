const REPOSITORY = "DangerZone8/Meme";
const WORKFLOW = "windows-app.yml";
const ARTIFACT_NAME = "ItsGiving-Electron-Portable-Windows-v0.3.0";
const API_ROOT = "https://api.github.com";

async function githubJson(path) {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "its-giving-website-download"
    }
  });
  if (!response.ok) throw new Error(`GitHub artifact lookup failed with HTTP ${response.status}`);
  return response.json();
}

export default async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).end("Method not allowed");
  }

  try {
    const runs = await githubJson(`/repos/${REPOSITORY}/actions/workflows/${WORKFLOW}/runs?branch=main&status=success&per_page=10`);
    for (const run of runs.workflow_runs ?? []) {
      if (run.conclusion !== "success" || run.head_branch !== "main") continue;
      const artifacts = await githubJson(`/repos/${REPOSITORY}/actions/runs/${run.id}/artifacts?per_page=100`);
      const artifact = (artifacts.artifacts ?? []).find(item => item.name === ARTIFACT_NAME && !item.expired);
      if (!artifact) continue;
      const archiveUrl = new URL(artifact.archive_download_url);
      if (archiveUrl.protocol !== "https:" || archiveUrl.hostname !== "api.github.com" || archiveUrl.pathname !== `/repos/${REPOSITORY}/actions/artifacts/${artifact.id}/zip`) {
        throw new Error("GitHub returned an unexpected artifact download URL");
      }
      res.setHeader("Cache-Control", "public, max-age=60, stale-while-revalidate=300");
      res.setHeader("Referrer-Policy", "no-referrer");
      res.setHeader("Location", archiveUrl.toString());
      return res.status(302).end();
    }
    return res.status(503).send("The Windows app is not available yet. Please try again after a successful Windows build.");
  } catch (error) {
    console.error("Windows download lookup failed:", error);
    return res.status(502).send("The Windows download service is temporarily unavailable. Please try again shortly.");
  }
}
