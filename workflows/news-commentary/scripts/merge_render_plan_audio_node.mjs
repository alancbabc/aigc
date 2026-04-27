import fs from 'node:fs';
import path from 'node:path';

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const part = argv[i];
    if (!part.startsWith('--')) continue;
    args[part.slice(2)] = argv[i + 1];
    i += 1;
  }
  return args;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function round3(value) {
  return Math.round(Number(value) * 1000) / 1000;
}

function resolveProjectPath(projectRoot, value) {
  const candidate = path.normalize(value);
  if (path.isAbsolute(candidate)) return candidate;
  return path.resolve(projectRoot, candidate);
}

function parseWav(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') {
    throw new Error(`Unsupported WAV file: ${filePath}`);
  }

  let offset = 12;
  let fmtChunk = null;
  let dataChunk = null;
  while (offset + 8 <= buffer.length) {
    const chunkId = buffer.toString('ascii', offset, offset + 4);
    const chunkSize = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;
    const chunkEnd = chunkStart + chunkSize;
    if (chunkEnd > buffer.length) break;
    if (chunkId === 'fmt ') fmtChunk = buffer.subarray(chunkStart, chunkEnd);
    if (chunkId === 'data') dataChunk = buffer.subarray(chunkStart, chunkEnd);
    offset = chunkEnd + (chunkSize % 2);
  }

  if (!fmtChunk || !dataChunk) throw new Error(`Invalid WAV structure: ${filePath}`);
  const audioFormat = fmtChunk.readUInt16LE(0);
  const numChannels = fmtChunk.readUInt16LE(2);
  const sampleRate = fmtChunk.readUInt32LE(4);
  const byteRate = fmtChunk.readUInt32LE(8);
  const blockAlign = fmtChunk.readUInt16LE(12);
  const bitsPerSample = fmtChunk.readUInt16LE(14);
  return {
    filePath,
    audioFormat,
    numChannels,
    sampleRate,
    byteRate,
    blockAlign,
    bitsPerSample,
    fmtChunk,
    dataChunk,
    durationSeconds: round3(dataChunk.length / byteRate),
  };
}

function assertCompatibleWave(base, candidate) {
  const keys = ['audioFormat', 'numChannels', 'sampleRate', 'byteRate', 'blockAlign', 'bitsPerSample'];
  for (const key of keys) {
    if (base[key] !== candidate[key]) {
      throw new Error(`Incompatible WAV params for merge: ${base.filePath} vs ${candidate.filePath} on ${key}`);
    }
  }
}

function buildSilenceBuffer(wavInfo, seconds) {
  const byteLength = Math.max(0, Math.round(wavInfo.byteRate * seconds));
  const alignedLength = byteLength - (byteLength % wavInfo.blockAlign);
  return Buffer.alloc(alignedLength, 0);
}

function writeMergedWav(outputPath, wavInfos, silenceSeconds) {
  const base = wavInfos[0];
  for (const wavInfo of wavInfos.slice(1)) assertCompatibleWave(base, wavInfo);
  const silenceBuffer = buildSilenceBuffer(base, silenceSeconds);
  const parts = [];
  wavInfos.forEach((wavInfo, index) => {
    if (index > 0 && silenceBuffer.length) parts.push(silenceBuffer);
    parts.push(wavInfo.dataChunk);
  });
  const dataBuffer = Buffer.concat(parts);

  const header = Buffer.alloc(44);
  header.write('RIFF', 0, 'ascii');
  header.writeUInt32LE(36 + dataBuffer.length, 4);
  header.write('WAVE', 8, 'ascii');
  header.write('fmt ', 12, 'ascii');
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(base.audioFormat, 20);
  header.writeUInt16LE(base.numChannels, 22);
  header.writeUInt32LE(base.sampleRate, 24);
  header.writeUInt32LE(base.byteRate, 28);
  header.writeUInt16LE(base.blockAlign, 32);
  header.writeUInt16LE(base.bitsPerSample, 34);
  header.write('data', 36, 'ascii');
  header.writeUInt32LE(dataBuffer.length, 40);

  fs.writeFileSync(outputPath, Buffer.concat([header, dataBuffer]));
  return round3(dataBuffer.length / base.byteRate);
}

function maybeUpdateLtxRequest(renderItem, mergedPath, mergedDuration) {
  if (!renderItem.ltx_request) return;
  renderItem.ltx_request.audio = mergedPath;
  renderItem.ltx_request.audio_paths = [mergedPath];
  renderItem.ltx_request.duration_seconds = round3(mergedDuration + 1.0);
}

function maybeUpdateFfmpegRequest(renderItem, mergedPath) {
  if (!renderItem.ffmpeg_request) return;
  renderItem.ffmpeg_request.audio_paths = [mergedPath];
}

function main() {
  const args = parseArgs(process.argv);
  const projectDir = args['project-dir'];
  if (!projectDir) throw new Error('Provide --project-dir');
  const silenceSeconds = Number(args['silence-seconds'] || 1.0);
  const projectRoot = path.resolve(projectDir);
  const renderPlanPath = path.join(projectRoot, 'video', 'render-plan.json');
  const renderPlan = readJson(renderPlanPath);
  const mergedDirRelative = 'audio/merged-clips';
  const mergedDirAbsolute = path.join(projectRoot, 'audio', 'merged-clips');
  ensureDir(mergedDirAbsolute);

  const mergedSummary = [];
  for (const renderItem of renderPlan.render_items || []) {
    const audioPaths = Array.isArray(renderItem.audio_paths) ? renderItem.audio_paths : [];
    if (audioPaths.length <= 1) continue;
    const resolvedAudioPaths = audioPaths.map((audioPath) => resolveProjectPath(projectRoot, audioPath));
    const wavInfos = resolvedAudioPaths.map(parseWav);
    const mergedRelativePath = `${mergedDirRelative}/${renderItem.clip_id}.wav`.replaceAll('\\', '/');
    const mergedAbsolutePath = path.join(mergedDirAbsolute, `${renderItem.clip_id}.wav`);
    const mergedDuration = writeMergedWav(mergedAbsolutePath, wavInfos, silenceSeconds);
    renderItem.audio_paths = [mergedRelativePath];
    renderItem.computed_duration_seconds = mergedDuration;
    maybeUpdateLtxRequest(renderItem, mergedRelativePath, mergedDuration);
    maybeUpdateFfmpegRequest(renderItem, mergedRelativePath);
    mergedSummary.push({
      clip_id: renderItem.clip_id,
      render_mode: renderItem.render_mode,
      source_audio_paths: audioPaths,
      merged_audio_path: mergedRelativePath,
      merged_duration_seconds: mergedDuration,
    });
  }

  writeJson(renderPlanPath, renderPlan);
  writeJson(path.join(mergedDirAbsolute, 'merge-summary.json'), { silence_seconds: silenceSeconds, merged_items: mergedSummary });
  process.stdout.write(JSON.stringify({ renderPlan: renderPlanPath, mergedDir: mergedDirAbsolute, mergedCount: mergedSummary.length }, null, 2));
}

main();
