import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TTS_BASE_URL = 'http://10.42.1.2:9200';
const POLL_INTERVAL_MS = 5000;

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

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

async function submitTts(text, pipelineName, language, speaker) {
  const response = await fetch(`${TTS_BASE_URL}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, pipeline_name: pipelineName, language, speaker })
  });

  if (!response.ok) {
    const textBody = await response.text();
    throw new Error(`Submit failed: ${response.status} ${textBody}`);
  }

  return response.json();
}

async function pollStatus(taskId) {
  while (true) {
    const response = await fetch(`${TTS_BASE_URL}/status/${taskId}`);
    const result = await response.json();
    console.log(`  Status: ${result.status}`);
    
    if (result.status === 'done') {
      return result;
    }
    if (result.status === 'error') {
      throw new Error(`Task failed`);
    }
    
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

async function downloadAudio(taskId, outputPath) {
  const response = await fetch(`${TTS_BASE_URL}/download/${taskId}`);
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }
  
  const buffer = await response.arrayBuffer();
  fs.writeFileSync(outputPath, Buffer.from(buffer));
  console.log(`  Saved: ${outputPath}`);
}

async function generateTts(text, speaker, outputPath) {
  console.log(`Generating: ${text.substring(0, 30)}...`);
  
  const result = await submitTts(text, 'qwen_tts_customvoice', 'zh', speaker);
  console.log(`  Task ID: ${result.task_id}`);
  
  await pollStatus(result.task_id);
  await downloadAudio(result.task_id, outputPath);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args['tts-plan'] || !args['output-dir']) {
    throw new Error('Usage: node batch_tts_generator.mjs --tts-plan <plan.json> --output-dir <audio_dir>');
  }

  const ttsPlan = loadJson(args['tts-plan']);
  const outputDir = args['output-dir'];
  
  const speakerMap = {
    'host': 'Vivian',
    'guest': 'Dylan'
  };

  let successCount = 0;
  let failCount = 0;

  for (const entry of ttsPlan.entries) {
    const speaker = speakerMap[entry.speaker] || entry.speaker;
    const outputPath = path.join(outputDir, entry.speaker, `${entry.entry_id}.wav`);
    
    try {
      await generateTts(entry.text, speaker, outputPath);
      successCount++;
    } catch (error) {
      console.error(`  Error: ${error.message}`);
      failCount++;
    }
  }

  console.log(`\n=== Summary ===`);
  console.log(`Success: ${successCount}`);
  console.log(`Failed: ${failCount}`);
}

main().catch(error => {
  console.error(error.message);
  process.exit(1);
});