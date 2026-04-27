import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname.replace(/^\//, ''));
const WORKFLOW_ROOT = path.resolve(SCRIPT_DIR, '..');
const DEFAULT_VARIANT_COUNT = 4;
const DEFAULT_MAX_CONCURRENT = 8;

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const part = argv[i];
    if (!part.startsWith('--')) continue;
    args[part.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : 'true';
    if (args[part.slice(2)] !== 'true') i += 1;
  }
  return args;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function deterministicSeed(clipId, variantIndex) {
  const digest = crypto.createHash('sha256').update(`${clipId}:v${variantIndex}`, 'utf8').digest();
  return digest.readUInt32BE(0);
}

function variantOutputPath(outputPath, variantIndex) {
  const parsed = path.parse(outputPath);
  return path.join(parsed.dir, `${parsed.name}_v${variantIndex}${parsed.ext}`);
}

function projectRootFromRenderPlan(renderPlanPath) {
  const parent = path.dirname(renderPlanPath);
  return path.basename(parent) === 'video' ? path.dirname(parent) : parent;
}

function resolveProjectPath(projectRoot, value) {
  return path.isAbsolute(value) ? value : path.resolve(projectRoot, value);
}

function resolveWorkflowPath(value) {
  return path.isAbsolute(value) ? value : path.resolve(WORKFLOW_ROOT, value);
}

function runVariant({ clipId, variantIndex, ltxScript, projectRoot, item, logDir, bashBin }) {
  return new Promise((resolve) => {
    const logPath = path.join(logDir, `stage11_render.${clipId}.v${variantIndex}.log`);
    const outputPath = variantOutputPath(resolveProjectPath(projectRoot, item.ltx_request.save_path), variantIndex);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    const seed = deterministicSeed(clipId, variantIndex);
    const audioPath = resolveProjectPath(projectRoot, item.ltx_request.audio || item.ltx_request.audio_paths?.[0]);
    const imageValues = Array.isArray(item.ltx_request.images) ? item.ltx_request.images : [];
    const resolvedImages = imageValues.map(resolveWorkflowPath);
    const args = [
      ltxScript,
      '-a', audioPath,
      '-p', item.optimized_prompt,
      '-o', outputPath,
      '-r', '24',
      '-d', String(item.ltx_request.duration_seconds),
      '--audio-start', String(item.ltx_request.a2v_audio_start_time ?? 0),
      '--insert-time', String(item.ltx_request.a2v_audio_insert_video_time ?? 0.5),
      '--seed', String(seed),
    ];
    if (item.ltx_request.negative_prompt) args.push('--negative', String(item.ltx_request.negative_prompt));
    if (resolvedImages.length) args.push('--images', resolvedImages.join(','));

    const child = spawn(bashBin, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += String(chunk); });
    child.stderr.on('data', (chunk) => { stderr += String(chunk); });
    child.on('close', (code) => {
      fs.writeFileSync(logPath, `COMMAND:\n${[bashBin, ...args].join(' ')}\n\nSTDOUT:\n${stdout}\nSTDERR:\n${stderr}\n`, 'utf8');
      if (code === 0) {
        resolve({ clip_id: clipId, variant: `v${variantIndex}`, status: 'ok', output_path: outputPath, log_path: logPath, seed });
      } else {
        resolve({ clip_id: clipId, variant: `v${variantIndex}`, status: 'failed', error: `exit ${code}`, log_path: logPath, seed });
      }
    });
  });
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args['render-plan']) throw new Error('Provide --render-plan');
  const renderPlanPath = path.resolve(args['render-plan']);
  const projectRoot = args['project-root'] ? path.resolve(args['project-root']) : projectRootFromRenderPlan(renderPlanPath);
  const logDir = args['log-dir'] ? path.resolve(args['log-dir']) : path.resolve(projectRoot, 'logs');
  const bashBin = args['bash-bin'] || 'bash';
  const ltxScript = args['ltx-script'] ? path.resolve(args['ltx-script']) : path.resolve(WORKFLOW_ROOT, '..', '..', 'generation', 'ltx23-video', 'scripts', 'generate_a2v.sh');
  const variantCount = Number(args['ltx-variants'] || DEFAULT_VARIANT_COUNT);
  const maxConcurrent = Number(args['max-concurrent'] || DEFAULT_MAX_CONCURRENT);
  const renderPlan = readJson(renderPlanPath);
  const ltxItems = (renderPlan.render_items || []).filter((item) => item.render_mode === 'ltx');
  const taskQueue = [];
  for (const item of ltxItems) {
    for (let variantIndex = 1; variantIndex <= variantCount; variantIndex += 1) {
      taskQueue.push({ item, clipId: item.clip_id, variantIndex });
    }
  }

  const perClipResults = new Map();
  let cursor = 0;
  async function worker() {
    while (cursor < taskQueue.length) {
      const currentIndex = cursor;
      cursor += 1;
      const task = taskQueue[currentIndex];
      const result = await runVariant({
        clipId: task.clipId,
        variantIndex: task.variantIndex,
        ltxScript,
        projectRoot,
        item: task.item,
        logDir,
        bashBin,
      });
      if (!perClipResults.has(task.clipId)) {
        perClipResults.set(task.clipId, []);
      }
      perClipResults.get(task.clipId).push(result);
    }
  }

  const workerCount = Math.max(1, Math.min(maxConcurrent, taskQueue.length || 1));
  await Promise.all(Array.from({ length: workerCount }, () => worker()));

  const results = ltxItems.map((item) => ({
    clip_id: item.clip_id,
    render_mode: 'ltx',
    variants: (perClipResults.get(item.clip_id) || []).sort((a, b) => a.variant.localeCompare(b.variant)),
  }));

  const summaryPath = path.join(logDir, 'stage11_render_ltx_only.summary.json');
  writeJson(summaryPath, { render_plan: renderPlanPath, project_root: projectRoot, total_ltx_items: ltxItems.length, variant_count: variantCount, max_concurrent: workerCount, results });
  const failed = results.flatMap((r) => r.variants).filter((v) => v.status !== 'ok');
  process.stdout.write(`${JSON.stringify({ summary_path: summaryPath, total_ltx_items: ltxItems.length, failed_variants: failed.length, max_concurrent: workerCount }, null, 2)}\n`);
  if (failed.length) process.exit(1);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
