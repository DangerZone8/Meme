import { createReadStream, statSync } from "node:fs";
import { put } from "@vercel/blob";

const file = "desktop/dist/ItsGiving-Desktop-0.3.0-Windows.exe";
const token = process.env.BLOB_READ_WRITE_TOKEN;
if (!token) throw new Error("BLOB_READ_WRITE_TOKEN is required.");
const info = statSync(file);
if (info.size < 50_000_000) throw new Error("Portable EXE is unexpectedly small; refusing to publish.");
const pathname = "its-giving/ItsGiving-Desktop-0.3.0-Windows.exe";
console.log("Publishing", file, "(" + info.size + " bytes) to Vercel Blob…");
const blob = await put(pathname, createReadStream(file), {
  access: "public", token, addRandomSuffix: false, allowOverwrite: true, multipart: true,
  contentType: "application/vnd.microsoft.portable-executable", cacheControlMaxAge: 60
});
const downloadUrl = blob.downloadUrl || (blob.url + "?download=1");
const parsed = new URL(downloadUrl);
if (parsed.protocol !== "https:" || !parsed.hostname.endsWith(".public.blob.vercel-storage.com")) throw new Error("Vercel Blob returned an unexpected public download URL.");
console.log("DIRECT_WINDOWS_EXE_URL=" + downloadUrl);
console.log("Add this URL as the Vercel project Production environment variable WINDOWS_APP_URL.");
console.log("::notice title=Direct Windows EXE published::" + downloadUrl);
