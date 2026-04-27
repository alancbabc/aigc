import { readFile } from 'node:fs/promises';
import path from 'node:path';

function parseArgs(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`Missing value for --${key}`);
    }
    args[key] = value;
    index += 1;
  }
  return args;
}

function appendField(chunks, boundary, name, value) {
  chunks.push(Buffer.from(`--${boundary}\r\n`, 'utf8'));
  chunks.push(Buffer.from(`Content-Disposition: form-data; name="${name}"\r\n\r\n`, 'utf8'));
  chunks.push(Buffer.from(String(value), 'utf8'));
  chunks.push(Buffer.from('\r\n', 'utf8'));
}

async function appendFileField(chunks, boundary, name, filePath, contentType) {
  const filename = path.basename(filePath);
  const fileBytes = await readFile(filePath);
  chunks.push(Buffer.from(`--${boundary}\r\n`, 'utf8'));
  chunks.push(
    Buffer.from(
      `Content-Disposition: form-data; name="${name}"; filename="${filename}"\r\nContent-Type: ${contentType}\r\n\r\n`,
      'utf8',
    ),
  );
  chunks.push(fileBytes);
  chunks.push(Buffer.from('\r\n', 'utf8'));
}

function parseCsv(value) {
  if (!value) return [];
  return String(value)
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function defaultImageIdx(index, totalImages, numFrames) {
  if (index === 0) return '0';
  if (index === totalImages - 1) return String(Math.max(numFrames - 1, 0));
  if (totalImages <= 1) return '0';
  return String(Math.floor((index * Math.max(numFrames - 1, 0)) / (totalImages - 1)));
}

async function main() {
  const args = parseArgs(process.argv);
  const baseUrl = args['base-url'];
  const prompt = args.prompt;
  const audioPath = args['audio-path'];
  const audioType = args['audio-type'];

  if (!baseUrl || !prompt || !audioPath || !audioType) {
    throw new Error(
      'Usage: node submit_ltx_transport.mjs --base-url <url> --prompt <text> --audio-path <file> --audio-type <mime> --height <n> --width <n> --num-frames <n> --frame-rate <n> --num-inference-steps <n> --pipeline-name <name> --audio-start <seconds> --insert-time <seconds> [--seed <n>] [--negative <text>] [--audio-max <seconds>] [--images <csv>] [--image-idxs <csv>] [--image-strengths <csv>]',
    );
  }

  const boundary = `----ltx23-video-${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
  const chunks = [];

  appendField(chunks, boundary, 'prompt', prompt);
  appendField(chunks, boundary, 'height', args.height);
  appendField(chunks, boundary, 'width', args.width);
  appendField(chunks, boundary, 'num_frames', args['num-frames']);
  appendField(chunks, boundary, 'frame_rate', args['frame-rate']);
  appendField(chunks, boundary, 'num_inference_steps', args['num-inference-steps']);
  appendField(chunks, boundary, 'pipeline_name', args['pipeline-name']);
  await appendFileField(chunks, boundary, 'a2v_audio_path', audioPath, audioType);
  appendField(chunks, boundary, 'a2v_audio_start_time', args['audio-start']);
  appendField(chunks, boundary, 'a2v_audio_insert_video_time', args['insert-time']);

  if (args.seed) appendField(chunks, boundary, 'seed', args.seed);
  if (args.negative) appendField(chunks, boundary, 'negative_prompt', args.negative);
  if (args['audio-max']) appendField(chunks, boundary, 'a2v_audio_max_duration', args['audio-max']);

  const imagePaths = parseCsv(args.images);
  const imageIdxs = parseCsv(args['image-idxs']);
  const imageStrengths = parseCsv(args['image-strengths']);
  const numFrames = Number.parseInt(args['num-frames'] ?? '0', 10);
  for (let index = 0; index < imagePaths.length; index += 1) {
    await appendFileField(chunks, boundary, 'images', imagePaths[index], 'image/png');
    appendField(chunks, boundary, 'image_idxs', imageIdxs[index] ?? defaultImageIdx(index, imagePaths.length, numFrames));
    appendField(chunks, boundary, 'image_strengths', imageStrengths[index] ?? '1.0');
    appendField(chunks, boundary, 'image_crfs', '0');
  }

  chunks.push(Buffer.from(`--${boundary}--\r\n`, 'utf8'));
  const body = Buffer.concat(chunks);
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': `multipart/form-data; boundary=${boundary}`,
      'Content-Length': String(body.length),
    },
    body,
  });

  const result = await response.text();
  if (!response.ok) {
    throw new Error(`Submit failed: ${response.status} ${response.statusText} ${result}`);
  }

  process.stdout.write(result);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exit(1);
});
