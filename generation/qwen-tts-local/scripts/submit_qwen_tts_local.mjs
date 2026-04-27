import { writeFile } from 'node:fs/promises';

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

async function main() {
  const args = parseArgs(process.argv);
  const baseUrl = args['base-url'];
  const text = args.text;
  const pipelineName = args['pipeline-name'];
  const language = args.language;

  if (!baseUrl || !text || !pipelineName || !language) {
    throw new Error('Usage: node submit_qwen_tts_local.mjs --base-url <url> --text <text> --pipeline-name <name> --language <language> [--instruct <value>] [--speaker <value>]');
  }

  const boundary = `----qwen-tts-local-${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
  const chunks = [];
  appendField(chunks, boundary, 'text', text);
  appendField(chunks, boundary, 'pipeline_name', pipelineName);
  appendField(chunks, boundary, 'language', language);
  if (args.instruct) appendField(chunks, boundary, 'instruct', args.instruct);
  if (args.speaker) appendField(chunks, boundary, 'speaker', args.speaker);
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

  if (!response.ok) {
    const textBody = await response.text();
    throw new Error(`Submit failed: ${response.status} ${response.statusText} ${textBody}`);
  }

  const result = await response.text();
  process.stdout.write(result);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exit(1);
});
