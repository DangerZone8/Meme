import { put } from "@vercel/blob";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";

const filePath = process.argv[2];
if (!filePath) {
  throw new Error("Usage: node scripts/publish_vercel_app.mjs <portable-exe-path>");
}
if (!process.env.BLOB_READ_WRITE_TOKEN) {
  throw new Error("BLOB_READ_WRITE_TOKEN secret is required.");
}

const fileInfo = await stat(filePath);
if (!fileInfo.isFile() || fileInfo.size < 50_000_000) {
  throw new Error("The portable Windows executable is missing or unexpectedly small.");
}

const blob = await put("ItsGiving.exe", createReadStream(filePath), {
  access: "public",
  addRandomSuffix: false,
  allowOverwrite: true,
  contentType: "application/vnd.microsoft.portable-executable",
  multipart: true,
  token: process.env.BLOB_READ_WRITE_TOKEN
});

if (!blob.downloadUrl || !blob.downloadUrl.startsWith("https://")) {
  throw new Error("Vercel Blob did not return a valid download URL.");
}

console.log("WINDOWS_APP_URL=" + blob.downloadUrl);
