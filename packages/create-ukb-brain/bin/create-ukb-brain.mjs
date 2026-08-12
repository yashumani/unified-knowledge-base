#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const packageRoot = path.resolve(__dirname, "..");

function usage() {
  console.log(`
create-ukb-brain

Usage:
  npm create ukb-brain@latest <project-name> -- --template default --offline
  node packages/create-ukb-brain/bin/create-ukb-brain.mjs <project-name> --offline

Options:
  --template <name>   Template name. Current: default
  --offline           Generate an offline-first brain config
  --force             Allow writing into a non-empty directory
  --help              Show this help
`);
}

function parseArgs(argv) {
  const args = [...argv];
  if (args.includes("--help") || args.includes("-h")) {
    return { help: true };
  }

  const projectName = args.find((arg) => !arg.startsWith("--"));
  const templateIndex = args.indexOf("--template");
  const template = templateIndex >= 0 ? args[templateIndex + 1] : "default";

  return {
    help: false,
    projectName,
    template,
    offline: args.includes("--offline"),
    force: args.includes("--force"),
  };
}

function slugify(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function titleize(value) {
  return value
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function walkFiles(root) {
  const output = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      output.push(...walkFiles(fullPath));
    } else {
      output.push(fullPath);
    }
  }
  return output;
}

function replaceTokens(targetDir, tokens) {
  for (const file of walkFiles(targetDir)) {
    const buffer = fs.readFileSync(file);
    if (buffer.includes(0)) {
      continue;
    }
    let text = buffer.toString("utf8");
    for (const [key, value] of Object.entries(tokens)) {
      text = text.replaceAll(`{{${key}}}`, value);
    }
    fs.writeFileSync(file, text, "utf8");
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    usage();
    return;
  }

  if (!options.projectName) {
    usage();
    process.exitCode = 1;
    return;
  }

  const templateDir = path.join(packageRoot, "templates", options.template);
  if (!fs.existsSync(templateDir)) {
    console.error(`Template not found: ${options.template}`);
    process.exitCode = 1;
    return;
  }

  const targetDir = path.resolve(process.cwd(), options.projectName);
  if (fs.existsSync(targetDir) && fs.readdirSync(targetDir).length > 0 && !options.force) {
    console.error(`Target directory is not empty: ${targetDir}`);
    console.error("Use --force to write into an existing directory.");
    process.exitCode = 1;
    return;
  }

  fs.mkdirSync(targetDir, { recursive: true });
  fs.cpSync(templateDir, targetDir, { recursive: true });

  const projectBaseName = path.basename(targetDir);
  const slug = slugify(projectBaseName);
  const name = titleize(projectBaseName);

  replaceTokens(targetDir, {
    BRAIN_NAME: name,
    BRAIN_SLUG: slug,
    OFFLINE_MODE: options.offline ? "true" : "false",
  });

  console.log(`Created ${name} at ${targetDir}`);
  console.log("");
  console.log("Next steps:");
  console.log(`  cd ${path.relative(process.cwd(), targetDir) || "."}`);
  console.log("  review brain.config.yaml");
  console.log("  add synthetic or approved context only");
  console.log("");
  console.log("Then run it with the Unified Knowledge Base runtime.");
}

main();
