import { put } from "@vercel/blob";
import { readFile } from "node:fs/promises";

const filePath = process.argv[2];
if (!filePath) throw new Error("Usage: node scripts/publish_vercel_installer.mjs <installer-path>");
if (!process.env.BLOB_READ_WRITE_TOKEN) throw new Error("BLOB_READ_WRITE_TOKEN secret is required.");

const file = await readFile(filePath);
const blob = await put("ItsGiving-Setup.exe", file, {
  access: "public",
  addRandomSuffix: false,
  allowOverwrite: true,
  contentType: "application/vnd.microsoft.portable-executable",
  token: process.env.BLOB_READ_WRITE_TOKEN
});
console.log("VERCEL_INSTALLER_URL=" + blob.url);
