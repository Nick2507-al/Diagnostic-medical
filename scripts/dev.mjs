// Starts the MediAI backend (FastAPI, auto-reload) and frontend (Next.js dev) together.
// Usage from the project root: npm run dev   — Ctrl+C stops both.
// No dependency on purpose: only Node built-ins.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const frontend = join(root, "frontend");
const isWin = process.platform === "win32";
const venvBin = join(backend, ".venv", isWin ? "Scripts" : "bin");
const python = join(venvBin, isWin ? "python.exe" : "python");

function fail(message) {
  console.error(`\x1b[31m[dev] ${message}\x1b[0m`);
  process.exit(1);
}

if (!existsSync(python)) fail("Environnement Python absent (backend/.venv). Voir README.md, section Installation.");
if (!existsSync(join(frontend, "node_modules"))) fail('Dépendances du frontend absentes : lancez "npm ci" dans frontend/.');
if (!existsSync(join(backend, ".env"))) fail("Fichier backend/.env absent : copiez backend/.env.example et complétez-le.");

/**
 * Frees a port held by a stale MediAI server (e.g. after the terminal was closed without Ctrl+C).
 * Only processes whose command line belongs to this project — or uvicorn's reload worker, whose
 * command line names its dead parent — are stopped; anything else aborts with a clear message.
 */
function freePort(port) {
  if (!isWin) return; // POSIX: Ctrl+C / closing the terminal already stops the whole process group
  const ps = (script) =>
    spawnSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { encoding: "utf8" }).stdout.trim();
  const owners = ps(
    `Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | ` +
    "Select-Object -ExpandProperty OwningProcess -Unique",
  ).split(/\s+/).filter(Boolean);
  for (const pid of owners) {
    if (!/^\d+$/.test(pid)) continue;
    const candidates = ps(
      "Get-CimInstance Win32_Process | Where-Object { " +
      `$_.ProcessId -eq ${pid} -or $_.CommandLine -like '*parent_pid=${pid}*' } | ` +
      "ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }",
    ).split(/\r?\n/).filter(Boolean);
    if (!candidates.length) fail(`Le port ${port} est occupé (processus ${pid}) et ne peut pas être libéré automatiquement.`);
    for (const line of candidates) {
      const [cpid, ...rest] = line.split("|");
      const cmd = rest.join("|");
      const ours = cmd.toLowerCase().includes(root.toLowerCase()) || cmd.includes(`parent_pid=${pid}`);
      if (!ours) fail(`Le port ${port} est utilisé par une autre application (PID ${cpid}). Fermez-la puis relancez.`);
      spawnSync("taskkill", ["/pid", cpid, "/T", "/F"], { stdio: "ignore" });
      console.log(`[dev] Ancien serveur MediAI arrêté sur le port ${port} (PID ${cpid}).`);
    }
  }
}
freePort(8000);
freePort(3000);

console.log("[dev] Migrations de la base de données…");
const migrate = spawnSync(python, ["-m", "alembic", "upgrade", "head"], { cwd: backend, stdio: "inherit" });
if (migrate.status !== 0) fail("Migration impossible : PostgreSQL est-il démarré ?");

const children = [];

function run(name, color, command, args, cwd) {
  const child = spawn(command, args, { cwd, shell: false, env: { ...process.env, FORCE_COLOR: "1" } });
  const prefix = `\x1b[${color}m[${name}]\x1b[0m `;
  const pipe = (stream, out) => {
    let buffer = "";
    stream.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) out.write(prefix + line + "\n");
    });
  };
  pipe(child.stdout, process.stdout);
  pipe(child.stderr, process.stderr);
  child.on("exit", (code, signal) => {
    console.log(`${prefix}arrêté (${signal ?? `code ${code}`})`);
    shutdown(code ?? 1);
  });
  children.push(child);
}

let stopping = false;
function shutdown(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode !== null) continue;
    if (isWin) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    else child.kill("SIGTERM");
  }
  setTimeout(() => process.exit(code), 300);
}
process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

run("api", "36", python,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload", "--reload-dir", "app"],
  backend);

// npm is a .cmd shim on Windows: call it through node to avoid shell: true.
const npmCli = process.env.npm_execpath;
if (npmCli) run("web", "35", process.execPath, [npmCli, "run", "dev"], frontend);
else run("web", "35", isWin ? "npm.cmd" : "npm", ["run", "dev"], frontend);

console.log("[dev] API : http://127.0.0.1:8000/api/docs · Interface : http://localhost:3000 · Ctrl+C pour arrêter");
