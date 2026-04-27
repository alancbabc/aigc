#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const DEFAULT_MAX_TTS_DURATION_SECONDS = 15.0;
const DEFAULT_CJK_CHARS_PER_SECOND = 3.6;
const DEFAULT_LATIN_WORDS_PER_SECOND = 2.8;
const DEFAULT_BASE_PAUSE_SECONDS = 0.35;
const STRONG_BREAK_CHARS = '。！？!?；;\n';
const SOFT_BREAK_CHARS = '，、,:：';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

function loadBuiltinAnchorTemplate(seriesProfile) {
  const templateId = seriesProfile?.anchor_defaults?.builtin_anchor_template_id;
  if (!templateId) return null;
  const templatePath = path.resolve(__dirname, '..', 'builtin-anchor-templates', `${templateId}.json`);
  if (!fs.existsSync(templatePath)) return null;
  return loadJson(templatePath);
}

function inferPlannedAudioPath(entryId, speaker, audioFormat = 'wav') {
  return `audio/${speaker}/${entryId}.${audioFormat}`;
}

function buildVoiceSourceBySpeaker(seriesProfile, builtinTemplate) {
  const defaults = seriesProfile?.anchor_defaults;
  const templateAnchors = builtinTemplate?.anchors;
  if ((!defaults || typeof defaults !== 'object') && (!templateAnchors || typeof templateAnchors !== 'object')) {
    return {};
  }

  const result = {};
  for (const speaker of ['host', 'guest']) {
    const templateAnchor = templateAnchors?.[speaker] || {};
    const ttsVoiceId = defaults?.[`${speaker}_tts_voice_id`] || templateAnchor.tts_voice_id;
    const voiceReferenceAudio = defaults?.[`${speaker}_voice_reference_audio`] || defaults?.[`${speaker}_voice_reference_audio`] || templateAnchor.voice_reference_audio;
    const localTts = templateAnchor.local_tts || {};
    if (!ttsVoiceId && !voiceReferenceAudio) continue;

    let mode = 'mixed';
    if (ttsVoiceId && !voiceReferenceAudio) mode = 'tts_voice_id';
    if (!ttsVoiceId && voiceReferenceAudio) mode = 'voice_reference_audio';

    result[speaker] = {
      mode,
      ...(ttsVoiceId ? { tts_voice_id: ttsVoiceId } : {}),
      ...(voiceReferenceAudio ? { voice_reference_audio: voiceReferenceAudio } : {}),
      ...(builtinTemplate?.template_id ? { template_id: builtinTemplate.template_id } : {}),
      ...(localTts.speaker ? { local_tts_speaker: localTts.speaker } : {}),
      ...(localTts.language ? { local_tts_language: localTts.language } : {}),
      ...(localTts.instruction ? { local_tts_instruction: localTts.instruction } : {}),
    };
  }

  return result;
}

function normalizeText(text) {
  return String(text).replace(/\s+/g, ' ').trim();
}

function round3(value) {
  return Math.round(value * 1000) / 1000;
}

function estimateSpokenDurationSeconds(text) {
  const normalized = normalizeText(text);
  if (!normalized) return 0;

  const cjkCount = Array.from(normalized).filter((char) => char >= '\u4e00' && char <= '\u9fff').length;
  const latinWordCount = (normalized.match(/[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*/g) || []).length;
  const punctuationCount = Array.from(normalized).filter((char) => STRONG_BREAK_CHARS.includes(char) || SOFT_BREAK_CHARS.includes(char)).length;

  let duration = DEFAULT_BASE_PAUSE_SECONDS;
  if (cjkCount) duration += cjkCount / DEFAULT_CJK_CHARS_PER_SECOND;
  if (latinWordCount) duration += latinWordCount / DEFAULT_LATIN_WORDS_PER_SECOND;
  duration += punctuationCount * 0.12;

  return round3(duration);
}

function splitByPunctuation(text) {
  const normalized = normalizeText(text);
  const chunks = [];
  let current = '';

  for (const char of normalized) {
    current += char;
    if (STRONG_BREAK_CHARS.includes(char) || SOFT_BREAK_CHARS.includes(char)) {
      const chunk = normalizeText(current);
      if (chunk) chunks.push(chunk);
      current = '';
    }
  }

  const trailing = normalizeText(current);
  if (trailing) chunks.push(trailing);
  return chunks.length ? chunks : [normalized];
}

function hardSplitChunk(text, maxChars) {
  let remaining = normalizeText(text);
  const parts = [];

  while (remaining.length > maxChars) {
    const candidate = remaining.slice(0, maxChars);
    let splitIndex = -1;

    for (const breakChar of `${STRONG_BREAK_CHARS}${SOFT_BREAK_CHARS}`) {
      const position = candidate.lastIndexOf(breakChar);
      if (position > Math.floor(maxChars / 2)) {
        splitIndex = Math.max(splitIndex, position + 1);
      }
    }

    if (splitIndex === -1) splitIndex = maxChars;

    const part = normalizeText(remaining.slice(0, splitIndex));
    if (part) parts.push(part);
    remaining = normalizeText(remaining.slice(splitIndex));
  }

  if (remaining) parts.push(remaining);
  return parts;
}

function splitTextForTts(text, maxDurationSeconds) {
  const normalized = normalizeText(text);
  if (estimateSpokenDurationSeconds(normalized) <= maxDurationSeconds) {
    return [normalized];
  }

  const maxChars = Math.max(18, Math.floor(maxDurationSeconds * DEFAULT_CJK_CHARS_PER_SECOND));
  const atomicChunks = [];

  for (const chunk of splitByPunctuation(normalized)) {
    if (estimateSpokenDurationSeconds(chunk) <= maxDurationSeconds) {
      atomicChunks.push(chunk);
    } else {
      atomicChunks.push(...hardSplitChunk(chunk, maxChars));
    }
  }

  const parts = [];
  let current = '';

  for (const chunk of atomicChunks) {
    const candidate = current ? `${current}${chunk}` : chunk;
    if (current && estimateSpokenDurationSeconds(candidate) > maxDurationSeconds) {
      parts.push(current);
      current = chunk;
    } else {
      current = candidate;
    }
  }

  if (current) parts.push(current);

  const finalParts = [];
  for (const part of parts) {
    if (estimateSpokenDurationSeconds(part) <= maxDurationSeconds) {
      finalParts.push(part);
    } else {
      finalParts.push(...hardSplitChunk(part, maxChars));
    }
  }

  return finalParts.map(normalizeText).filter(Boolean);
}

function buildTtsEntries(scriptPayload, maxDurationSeconds, voiceSourceBySpeaker = {}) {
  const entries = [];

  for (const segment of scriptPayload.segments || []) {
    const segmentNo = Number(segment.segment_no);
    const segmentType = segment.type;

    for (const line of segment.lines || []) {
      const lineNo = Number(line.line_no);
      const splitParts = splitTextForTts(line.text, maxDurationSeconds);
      const splitTotal = splitParts.length;

      splitParts.forEach((splitText, partIndex) => {
        const splitPartNo = partIndex + 1;
        let entryId = `seg${String(segmentNo).padStart(2, '0')}_line${String(lineNo).padStart(2, '0')}`;
        if (splitTotal > 1) {
          entryId = `${entryId}_part${String(splitPartNo).padStart(2, '0')}`;
        }

        entries.push({
          entry_id: entryId,
          script_line_id: line.line_id || `seg${String(segmentNo).padStart(2, '0')}_line${String(lineNo).padStart(2, '0')}`,
          segment_no: segmentNo,
          segment_type: segmentType,
          line_no: lineNo,
          speaker: line.speaker,
          text: splitText,
          emotion: line.emotion || 'neutral',
          estimated_duration_seconds: estimateSpokenDurationSeconds(splitText),
          planned_audio_path: inferPlannedAudioPath(entryId, line.speaker, 'wav'),
          pause_before: splitPartNo === 1 ? Number(line.pause_before || 0) : 0,
          pause_after: splitPartNo === splitTotal ? Number(line.pause_after ?? 0.5) : 0,
          split_part_no: splitPartNo,
          split_part_total: splitTotal,
          ...(voiceSourceBySpeaker[line.speaker] ? { voice_source: voiceSourceBySpeaker[line.speaker] } : {}),
          ...(line.split_group_id ? { split_group_id: line.split_group_id } : {}),
          source_line_text: normalizeText(line.text),
        });
      });
    }
  }

  return entries;
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.script || !args.output) {
    throw new Error('Usage: node build_tts_plan.mjs --script <project>/script.json --output <project>/audio/tts-plan.json [--series-profile <project>/series-profile.json] [--max-duration-seconds 15.0]');
  }

  const scriptPath = path.resolve(args.script);
  const outputPath = path.resolve(args.output);
  const maxDurationSeconds = Number(args['max-duration-seconds'] || DEFAULT_MAX_TTS_DURATION_SECONDS);
  const scriptPayload = loadJson(scriptPath);
  const seriesProfile = args['series-profile'] ? loadJson(path.resolve(args['series-profile'])) : null;
  const builtinTemplate = loadBuiltinAnchorTemplate(seriesProfile);
  const voiceSourceBySpeaker = buildVoiceSourceBySpeaker(seriesProfile, builtinTemplate);
  const entries = buildTtsEntries(scriptPayload, maxDurationSeconds, voiceSourceBySpeaker);

  const payload = {
    schema_version: '1.0',
    title: scriptPayload.title || 'news-commentary-tts-plan',
    source_script_ref: args.script.replace(/\\/g, '/'),
    max_target_duration_seconds: maxDurationSeconds,
    entries,
    estimated_total_duration_seconds: round3(
      entries.reduce(
        (total, entry) => total + Number(entry.estimated_duration_seconds || 0) + Number(entry.pause_before || 0) + Number(entry.pause_after || 0),
        0,
      ),
    ),
  };

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

main();
