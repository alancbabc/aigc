import fs from 'node:fs';
import path from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';

const repoRoot = process.cwd();
const ignoreDirs = new Set(['node_modules', '.git']);

const requiredGenerationContracts = [
  { dir: 'generation/flux-text-to-image', artifact: 'flux-text-to-image' },
  { dir: 'generation/flux-image-edit', artifact: 'flux-image-edit' },
  { dir: 'generation/qwen-image-2512', artifact: 'qwen-image-2512' },
  { dir: 'generation/qwen2.5-vl', artifact: 'qwen2.5-vl' },
  { dir: 'generation/step-audio-tts', artifact: 'step-audio-tts' }
];

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ignoreDirs.has(entry.name)) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath, files);
    } else {
      files.push(fullPath);
    }
  }
  return files;
}

function rel(filePath) {
  return path.relative(repoRoot, filePath).replace(/\\/g, '/');
}

function readJson(filePath, errors) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    errors.push(`${rel(filePath)}: invalid JSON (${error.message})`);
    return null;
  }
}

const allFiles = walk(repoRoot);
const schemaFiles = allFiles.filter((file) => file.endsWith('.schema.json'));
const exampleFiles = allFiles.filter((file) => file.endsWith('.example.json'));

const errors = [];
const schemaMap = new Map(schemaFiles.map((file) => [rel(file).replace(/\.schema\.json$/, ''), file]));
const exampleMap = new Map(exampleFiles.map((file) => [rel(file).replace(/\.example\.json$/, ''), file]));

for (const [base, schemaPath] of schemaMap.entries()) {
  if (!exampleMap.has(base)) {
    errors.push(`${rel(schemaPath)}: missing matching .example.json`);
  }
}

for (const [base, examplePath] of exampleMap.entries()) {
  if (!schemaMap.has(base)) {
    errors.push(`${rel(examplePath)}: missing matching .schema.json`);
  }
}

const ajv = new Ajv2020({ allErrors: true, strict: false });

for (const [base, schemaPath] of schemaMap.entries()) {
  const examplePath = exampleMap.get(base);
  if (!examplePath) continue;

  const schema = readJson(schemaPath, errors);
  const example = readJson(examplePath, errors);
  if (!schema || !example) continue;

  let validate;
  try {
    validate = ajv.compile(schema);
  } catch (error) {
    errors.push(`${rel(schemaPath)}: schema compilation failed (${error.message})`);
    continue;
  }

  const valid = validate(example);
  if (!valid) {
    const details = (validate.errors || [])
      .map((item) => `${item.instancePath || '/'} ${item.message}`.trim())
      .join('; ');
    errors.push(`${rel(examplePath)}: schema validation failed (${details})`);
  }
}

for (const contract of requiredGenerationContracts) {
  const skillDir = path.join(repoRoot, contract.dir);
  const skillDocPath = path.join(skillDir, 'SKILL.md');
  const schemaPath = path.join(skillDir, `${contract.artifact}.schema.json`);
  const examplePath = path.join(skillDir, `${contract.artifact}.example.json`);

  if (!fs.existsSync(skillDocPath)) {
    errors.push(`${contract.dir}: missing SKILL.md`);
    continue;
  }

  if (!fs.existsSync(schemaPath)) {
    errors.push(`${contract.dir}: missing ${contract.artifact}.schema.json`);
  }

  if (!fs.existsSync(examplePath)) {
    errors.push(`${contract.dir}: missing ${contract.artifact}.example.json`);
  }

  const skillDoc = fs.readFileSync(skillDocPath, 'utf8');
  for (const requiredReference of [`${contract.artifact}.schema.json`, `${contract.artifact}.example.json`]) {
    if (!skillDoc.includes(requiredReference)) {
      errors.push(`${rel(skillDocPath)}: missing contract reference ${requiredReference}`);
    }
  }
}

if (errors.length > 0) {
  console.error('Skill validation failed:');
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log(`Skill validation passed: ${schemaFiles.length} schema file(s), ${exampleFiles.length} example file(s).`);
