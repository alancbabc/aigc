#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';

function parseArgs(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = value;
    index += 1;
  }
  return args;
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function resolveProjectRoot(ttsPlanPath) {
  return path.basename(path.dirname(ttsPlanPath)) === 'audio'
    ? path.dirname(path.dirname(ttsPlanPath))
    : path.dirname(ttsPlanPath);
}

function resolveOutputPath(projectRoot, entry) {
  if (typeof entry.planned_audio_path === 'string' && entry.planned_audio_path) {
    return path.resolve(projectRoot, entry.planned_audio_path);
  }
  return path.resolve(projectRoot, 'audio', entry.speaker, `${entry.entry_id}.wav`);
}

function localTtsConfig(entry) {
  const voiceSource = entry.voice_source || {};
  return {
    speaker: voiceSource.local_tts_speaker || (entry.speaker === 'host' ? 'Serena' : 'Ryan'),
    language: voiceSource.local_tts_language || 'chinese',
    instruction: voiceSource.local_tts_instruction || '',
  };
}

function main() {
  const args = parseArgs(process.argv);
  if (!args['tts-plan']) {
    throw new Error('Usage: node generate_local_tts_from_plan.mjs --tts-plan <project>/audio/tts-plan.json [--tts-script <path>] [--project-root <path>] [--fail-fast]');
  }

  const ttsPlanPath = path.resolve(args['tts-plan']);
  const projectRoot = args['project-root'] ? path.resolve(args['project-root']) : resolveProjectRoot(ttsPlanPath);
  const ttsScript = args['tts-script']
    ? path.resolve(args['tts-script'])
    : path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\//, '')), '..', '..', '..', 'generation', 'qwen-tts-local', 'scripts', 'generate_qwen_tts_local.sh');
  const plan = loadJson(ttsPlanPath);
  const entries = Array.isArray(plan.entries) ? plan.entries : [];
  const results = [];

  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index];
    const outputPath = resolveOutputPath(projectRoot, entry);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const { speaker, language, instruction } = localTtsConfig(entry);
    const command = [
      ttsScript,
      '--text', String(entry.text),
      '--language', String(language),
      '--speaker', String(speaker),
      '--output', outputPath,
    ];
    if (instruction) {
      command.push('--instruct', String(instruction));
    }

    process.stdout.write(`[${index + 1}/${entries.length}] ${entry.entry_id} -> ${outputPath}\n`);
    const completed = spawnSync('bash', command, { stdio: 'inherit' });
    if (completed.status === 0) {
      results.push({ entry_id: entry.entry_id, status: 'ok', output_path: outputPath.replace(/\\/g, '/') });
      continue;
    }

    results.push({ entry_id: entry.entry_id, status: 'failed', exit_code: completed.status });
    if (args['fail-fast']) {
      break;
    }
  }

  const manifestPath = path.resolve(projectRoot, 'audio', 'tts-local-manifest.json');
  fs.writeFileSync(manifestPath, `${JSON.stringify({ results }, null, 2)}\n`, 'utf8');
  if (results.some((item) => item.status !== 'ok')) {
    process.exit(1);
  }
}

main();
