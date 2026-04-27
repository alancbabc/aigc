#!/usr/bin/env node
import { readFileSync, createWriteStream, mkdirSync } from 'fs';
import path from 'node:path';
import http from 'node:http';
import https from 'node:https';

const BASE_URL = process.env.LTX23_BASE_URL || 'http://10.0.180.14:80';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const t = argv[i];
    if (!t.startsWith('--')) continue;
    args[t.slice(2)] = argv[++i];
  }
  return args;
}

function submit(audioPath, prompt, height, width, numFrames, frameRate, steps, pipeline, audioType, audioStart, insertTime, images, negative, seed) {
  const boundary = `----ltx23-${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
  const chunks = [];
  const addField = (name, value) => {
    chunks.push(Buffer.from(`--${boundary}\r\n`, 'utf8'));
    chunks.push(Buffer.from(`Content-Disposition: form-data; name="${name}"\r\n\r\n`, 'utf8'));
    chunks.push(Buffer.from(String(value), 'utf8'));
    chunks.push(Buffer.from('\r\n', 'utf8'));
  };
  const audioBytes = readFileSync(audioPath);
  chunks.push(Buffer.from(`--${boundary}\r\n`, 'utf8'));
  chunks.push(Buffer.from(`Content-Disposition: form-data; name="a2v_audio_path"; filename="${path.basename(audioPath)}"\r\nContent-Type: ${audioType}\r\n\r\n`, 'utf8'));
  chunks.push(audioBytes);
  chunks.push(Buffer.from('\r\n', 'utf8'));
  addField('prompt', prompt);
  addField('height', height);
  addField('width', width);
  addField('num_frames', numFrames);
  addField('frame_rate', frameRate);
  addField('num_inference_steps', steps);
  addField('pipeline_name', pipeline);
  addField('a2v_audio_start_time', audioStart);
  addField('a2v_audio_insert_video_time', insertTime);
  if (seed) addField('seed', seed);
  if (negative) addField('negative_prompt', negative);
  if (images && images.length) {
    for (let i = 0; i < images.length; i++) {
      const imgBytes = readFileSync(images[i]);
      chunks.push(Buffer.from(`--${boundary}\r\n`, 'utf8'));
      chunks.push(Buffer.from(`Content-Disposition: form-data; name="images"; filename="${path.basename(images[i])}"\r\nContent-Type: image/png\r\n\r\n`, 'utf8'));
      chunks.push(imgBytes);
      chunks.push(Buffer.from('\r\n', 'utf8'));
      addField('image_idxs', i === 0 ? '0' : String(numFrames - 1));
      addField('image_strengths', '1.0');
      addField('image_crfs', '0');
    }
  }
  chunks.push(Buffer.from(`--${boundary}--\r\n`, 'utf8'));
  const body = Buffer.concat(chunks);
  const base = BASE_URL.replace(/\/$/, '');
  const url = new URL(`${base}/submit`);
  const mod = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const req = mod.request({ hostname: url.hostname, port: url.port, path: url.pathname, method: 'POST', headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}`, 'Content-Length': body.length } }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        if (res.statusCode !== 200) return reject(new Error(`Submit failed: ${res.statusCode} ${data}`));
        resolve(JSON.parse(data));
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function poll(taskId) {
  const base = BASE_URL.replace(/\/$/, '');
  const url = new URL(`${base}/status/${taskId}`);
  const mod = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    function check() {
      const req2 = mod.request({ hostname: url.hostname, port: url.port, path: url.pathname, method: 'GET' }, (res) => {
        let data = '';
        res.on('data', (c) => { data += c; });
        res.on('end', () => {
          if (res.statusCode !== 200) return reject(new Error(`Poll failed: ${res.statusCode} ${data}`));
          const result = JSON.parse(data);
          console.error(`  Status: ${result.status}`);
          if (result.status === 'done') return resolve(result);
          if (result.status === 'error') return reject(new Error(`Task error: ${JSON.stringify(result)}`));
          setTimeout(check, 10000);
        });
      });
      req2.on('error', reject);
      req2.end();
    }
    check();
  });
}

function download(taskId, outputPath) {
  const base = BASE_URL.replace(/\/$/, '');
  const url = new URL(`${base}/download/${taskId}`);
  const mod = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const req = mod.request({ hostname: url.hostname, port: url.port, path: url.pathname, method: 'GET' }, (res) => {
      if (res.statusCode !== 200) {
        let data = '';
        res.on('data', (c) => { data += c; });
        res.on('end', () => reject(new Error(`Download failed: ${res.statusCode} ${data}`)));
        return;
      }
      const out = createWriteStream(outputPath);
      res.pipe(out);
      out.on('finish', () => resolve());
      out.on('error', reject);
    });
    req.on('error', reject);
    req.end();
  });
}

const args = parseArgs(process.argv);
const height = parseInt(args.height || '1024', 10);
const width = parseInt(args.width || '1536', 10);
const fps = parseInt(args.fps || '24', 10);
const duration = parseFloat(args.duration || '5');
const totalFrames = Math.round(duration * fps);
const numFrames = Math.floor(totalFrames / 8) * 8 + 1;
const steps = parseInt(args.steps || '30', 10);
const audioType = args['audio-type'] || 'audio/wav';
const audioStart = args['audio-start'] || '0';
const insertTime = args['insert-time'] || '0.5';
const images = args.images ? args.images.split(',') : [];
const negative = args.negative || '';
const seed = args.seed || '';

console.error(`Submitting to ${BASE_URL}...`);
console.error(`  Prompt: ${args.prompt.slice(0, 60)}...`);
console.error(`  Audio: ${args.audio}`);
console.error(`  Frames: ${numFrames} (${width}x${height} @ ${fps}fps)`);

try {
  const taskResult = await submit(args.audio, args.prompt, height, width, numFrames, fps, steps, 'a2vid_two_stage', audioType, audioStart, insertTime, images, negative, seed);
  console.error(`Task submitted: ${taskResult.task_id}`);
  console.error('Waiting for completion...');
  const pollResult = await poll(taskResult.task_id);
  console.error(`Downloading to ${args.output}...`);
  mkdirSync(path.dirname(args.output), { recursive: true });
  await download(pollResult.task_id, args.output);
  console.error(`Done: ${args.output}`);
} catch (e) {
  console.error(e.message);
  process.exit(1);
}