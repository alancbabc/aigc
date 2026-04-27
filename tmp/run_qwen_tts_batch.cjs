const fs = require('fs');
const cp = require('child_process');

const [,, planPath, outputDir, hostSpeaker = 'Serena', guestSpeaker = 'Ryan', language = 'chinese'] = process.argv;

if (!planPath || !outputDir) {
  console.error('Usage: node tmp/run_qwen_tts_batch.cjs <tts-plan.json> <outputDir> [hostSpeaker] [guestSpeaker] [language]');
  process.exit(1);
}

const script = 'C:/Users/jyfa/.config/opencode/skills/aigc/generation/qwen-tts-local/scripts/generate_qwen_tts_local.sh';
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));

fs.mkdirSync(outputDir, { recursive: true });

for (const entry of plan.entries || []) {
  const speaker = entry.speaker === 'host' ? hostSpeaker : guestSpeaker;
  const out = `${outputDir}/${entry.entry_id}.wav`;
  console.log(`Synthesizing ${entry.entry_id} -> ${speaker}`);
  const res = cp.spawnSync('bash', [
    script,
    '--text', entry.text,
    '--speaker', speaker,
    '--language', language,
    '--output', out,
  ], { stdio: 'inherit' });

  if (res.status !== 0) {
    console.error(`Failed on ${entry.entry_id}`);
    process.exit(res.status || 1);
  }
}

console.log('Batch synthesis completed.');
