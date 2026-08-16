#!/usr/bin/env node
// agentcollab.mjs — JavaScript reference implementation of the AgentCollab
// handshake. Implements Handshake.md §2–§3 (bundle root, protocol ID) and §5
// verification (L1 integrity always; L2 authenticity via the system
// `ssh-keygen`, when available). Node >= 18, standard library only. The shell
// scripts in bin/ remain the normative reference; this module must produce
// byte-identical IDs — CI enforces parity (tests/run-impl-parity.sh).
//
// CLI (mirrors bin/agentcollab-id.sh and bin/agentcollab-verify.sh):
//   agentcollab.mjs id      [--root DIR]            print the protocol ID
//   agentcollab.mjs root    [--root DIR]            print the 64-hex bundle root
//   agentcollab.mjs verify  [--root DIR] [--no-sig] verify: exit 0 ok, 1 failed
//
// Exports: bundleRoot(rootDir), protocolId(rootDir),
//          verify(rootDir, {checkSig}) -> {ok, level, errors}
//
// Exit codes: 0 ok · 1 verification failed · 2 usage/environment error

import { createHash } from "node:crypto";
import { readFileSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const NAMESPACE = "agentcollab-manifest";
const MANIFEST = "PROTOCOL_MANIFEST.yaml";

class ManifestError extends Error {}

function readManifest(rootDir) {
  const path = join(rootDir, MANIFEST);
  if (!existsSync(path)) throw new ManifestError(`${MANIFEST} not found in ${rootDir}`);
  let version = null, declaredRoot = null, declaredId = null, current = null;
  const files = [];
  for (const line of readFileSync(path, "utf8").split("\n")) {
    let m;
    if ((m = line.match(/^version: (\S+)$/))) version = m[1];
    else if ((m = line.match(/^  - path: (\S+)$/))) current = m[1];
    else if ((m = line.match(/^    sha256: ([0-9a-f]{64})$/))) {
      if (current === null) throw new ManifestError("sha256 line without a preceding path");
      files.push([current, m[1]]);
      current = null;
    } else if ((m = line.match(/^bundle_root: ([0-9a-f]{64})$/))) declaredRoot = m[1];
    else if ((m = line.match(/^id: (\S+)$/))) declaredId = m[1];
  }
  if (version === null || files.length === 0)
    throw new ManifestError(`${MANIFEST} is missing version or file entries`);
  return { version, files, bundleRoot: declaredRoot, id: declaredId };
}

const fileSha256 = (path) =>
  createHash("sha256").update(readFileSync(path)).digest("hex");

export function bundleRoot(rootDir) {
  // Handshake §2: sha256 over the path-sorted "<hash>  <path>" listing.
  const manifest = readManifest(rootDir);
  const lines = manifest.files.map(([rel]) => {
    const target = join(rootDir, rel);
    if (!existsSync(target)) throw new ManifestError(`bundle file missing: ${rel}`);
    return `${fileSha256(target)}  ${rel}`;
  });
  // Byte-wise path sort, matching `LC_ALL=C sort -k 2` on ASCII paths.
  lines.sort((a, b) =>
    Buffer.compare(Buffer.from(a.split("  ")[1]), Buffer.from(b.split("  ")[1])));
  const listing = lines.map((l) => l + "\n").join("");
  return createHash("sha256").update(listing).digest("hex");
}

export function protocolId(rootDir) {
  const manifest = readManifest(rootDir);
  return `AgentCollab/${manifest.version}#sha256:${bundleRoot(rootDir).slice(0, 16)}`;
}

function verifySignature(rootDir, errors) {
  const sig = join(rootDir, `${MANIFEST}.sig`);
  const signers = join(rootDir, "keys", "allowed_signers");
  if (!existsSync(sig)) {
    errors.push(`signature ${MANIFEST}.sig not found (use checkSig: false for L1)`);
    return;
  }
  if (!existsSync(signers)) {
    errors.push("trust store keys/allowed_signers not found");
    return;
  }
  // During key rotation allowed_signers lists several principals; the
  // signature is valid if it verifies for any of them.
  const principals = [...new Set(readFileSync(signers, "utf8").split("\n")
    .filter((l) => l.trim() && !l.startsWith("#"))
    .map((l) => l.split(/\s+/)[0]))];
  if (principals.length === 0) {
    errors.push("no principal found in keys/allowed_signers");
    return;
  }
  const manifestBytes = readFileSync(join(rootDir, MANIFEST));
  for (const principal of principals) {
    const result = spawnSync("ssh-keygen",
      ["-Y", "verify", "-f", signers, "-I", principal, "-n", NAMESPACE, "-s", sig],
      { input: manifestBytes });
    if (result.error && result.error.code === "ENOENT") {
      errors.push("ssh-keygen not available: L2 cannot be checked on this host " +
        "(rerun with --no-sig for L1, or verify on a host with OpenSSH >= 8.1)");
      return;
    }
    if (result.status === 0) return;
  }
  errors.push("manifest signature INVALID for every listed principal");
}

export function verify(rootDir, { checkSig = true } = {}) {
  const errors = [];
  const manifest = readManifest(rootDir);
  for (const [rel, declared] of manifest.files) {
    const target = join(rootDir, rel);
    if (!existsSync(target)) errors.push(`MISSING ${rel}`);
    else if (fileSha256(target) !== declared) errors.push(`MISMATCH ${rel}`);
  }
  if (errors.length === 0) {
    const computed = bundleRoot(rootDir);
    if (computed !== manifest.bundleRoot)
      errors.push(`bundle root mismatch: computed ${computed}, ` +
        `manifest declares ${manifest.bundleRoot}`);
    const expectedId = `AgentCollab/${manifest.version}#sha256:${computed.slice(0, 16)}`;
    if (expectedId !== manifest.id)
      errors.push(`id/version/root disagree: manifest id '${manifest.id}', ` +
        `derived '${expectedId}'`);
  }
  const level = checkSig ? "L2" : "L1";
  if (checkSig) verifySignature(rootDir, errors);
  return { ok: errors.length === 0, level, errors };
}

// ------------------------------- CLI -----------------------------------------

function main(argv) {
  const cmd = argv[0];
  if (!["id", "root", "verify"].includes(cmd)) {
    process.stderr.write("usage: agentcollab.mjs id|root|verify [--root DIR] [--no-sig]\n");
    return 2;
  }
  let rootDir = ".", checkSig = true;
  const rest = argv.slice(1);
  while (rest.length) {
    const arg = rest.shift();
    if (arg === "--root") {
      if (!rest.length) { process.stderr.write("agentcollab: --root needs a value\n"); return 2; }
      rootDir = rest.shift();
    } else if (arg === "--no-sig") checkSig = false;
    else { process.stderr.write(`agentcollab: unknown option ${arg}\n`); return 2; }
  }
  try {
    if (cmd === "id") console.log(protocolId(rootDir));
    else if (cmd === "root") console.log(bundleRoot(rootDir));
    else {
      const { ok, level, errors } = verify(rootDir, { checkSig });
      for (const err of errors) process.stderr.write(`agentcollab: FAIL: ${err}\n`);
      if (!ok) { console.log(`agentcollab: RESULT: FAILED (${level})`); return 1; }
      console.log(`agentcollab: RESULT: VERIFIED [${level}] ${protocolId(rootDir)}`);
    }
  } catch (exc) {
    if (exc instanceof ManifestError) {
      process.stderr.write(`agentcollab: ${exc.message}\n`);
      return 2;
    }
    throw exc;
  }
  return 0;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.exit(main(process.argv.slice(2)));
}
