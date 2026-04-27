import fs from 'node:fs';
import path from 'node:path';

const WORKFLOW_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\//, '')), '..');
const DEFAULT_ANCHOR_IMAGE_BY_SPEAKER = {
  host: 'builtin-anchor-templates/default-news-duo-v1/visuals/anchors/female_solo.png',
  guest: 'builtin-anchor-templates/default-news-duo-v1/visuals/anchors/male_solo.png',
};
const DEFAULT_ANCHOR_IMAGE_BY_MODE = {
  female_solo: 'builtin-anchor-templates/default-news-duo-v1/visuals/anchors/female_solo.png',
  male_solo: 'builtin-anchor-templates/default-news-duo-v1/visuals/anchors/male_solo.png',
};
const DEFAULT_DUO_REFERENCE_IMAGE = 'builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png';
const DEFAULT_OPENING_LTX_IMAGES = ['builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png'];
const DEFAULT_MIDDLE_DUO_LTX_IMAGES = ['builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png'];
const DEFAULT_CLOSING_LTX_IMAGES = ['builtin-anchor-templates/default-news-duo-v1/visuals/anchors/duo_close.png'];
const DEFAULT_TARGET_DIMENSIONS = { width: 1536, height: 1024 };
const SOLO_CONTINUOUS_SECONDS_THRESHOLD = 15.0;
const LTX_MERGE_MAX_DURATION_SECONDS = 16.0;
const DOCUMENT_BLOCK_MAX_DURATION_SECONDS = 6.0;
const DOCUMENT_BLOCK_CONTINUE_SCORE_THRESHOLD = 5;
const DEFAULT_LTX_MAX_DURATION_SECONDS = 16.0;
const DEFAULT_LTX_AUDIO_START_TIME_SECONDS = 0.0;
const DEFAULT_LTX_AUDIO_INSERT_VIDEO_TIME_SECONDS = 0.5;
const DEFAULT_LTX_VIDEO_DURATION_PADDING_SECONDS = 1.0;
const DEFAULT_PAD_COLOR = '#000000';
const DEFAULT_LTX_NEGATIVE_PROMPT = 'text, subtitles, watermarks, logos, readable signage, overlay, titles, has blurbox, has subtitles, artifacts around text, unreadable text, incorrect lettering, incorrect slogan, camera shake, frame jitter';
const DATA_HEAVY_HINTS = ['数据', '图', '图表', '流程', '模型', '集群', 'gpu', '训练', '部署', '闭环', '算力', '性能', '架构', '框架', '发布', '现场', '签约', '仪式'];
const VISUAL_PREFERRED_SEGMENTS = new Set(['opening', 'closing', 'headline', 'discussion', 'summary', 'intro', 'technical', 'capability', 'outlook', 'background', 'explanation']);
const SPOKEN_DIALOGUE_PLACEHOLDER = '[[SPOKEN_DIALOGUE]]';
const DUO_SPEAKER_LABEL_PLACEHOLDER = '[[DUO_SPEAKER_LABEL]]';
const DUO_LISTENER_LABEL_PLACEHOLDER = '[[DUO_LISTENER_LABEL]]';
const OPENING_TEMPLATE = `Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. Only the ${DUO_SPEAKER_LABEL_PLACEHOLDER} speaks. ${SPOKEN_DIALOGUE_PLACEHOLDER} The ${DUO_SPEAKER_LABEL_PLACEHOLDER} shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and subtle blinking with very small head motion. The ${DUO_LISTENER_LABEL_PLACEHOLDER} listens attentively, remains silent and mostly still, with restrained micro-reactions and no visible speaking motion. Both anchors maintain formal professional posture. Both anchors remain visible in the same frame at all times. The shot stays a fixed two-anchor composition for the entire clip with no cut to a solo shot, no reframing, and no change in shot size. The camera remains fully locked and stable throughout. The overall feeling is calm, steady, and professional.`;
const MIDDLE_TEMPLATE_SOLO = `Middle shot, tight close-up on one anchor in a clean modern studio with neutral lighting, stable framing, and clear face visibility. The anchor is speaking directly to the camera. ${SPOKEN_DIALOGUE_PLACEHOLDER} The anchor keeps a steady eyeline and clearly visible, active speech mouth movement synchronized to the spoken Chinese line. Mouth motion stays natural but obvious, with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, and active jaw movement on spoken syllables. Facial motion stays subtle and professional, with restrained blinking, minimal head movement, and calm posture so the speaking motion reads clearly. The camera remains fixed and stable throughout. The overall feeling is controlled, informative, formal, and professional.`;
const MIDDLE_TEMPLATE_DUO = `Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. Only the ${DUO_SPEAKER_LABEL_PLACEHOLDER} speaks. ${SPOKEN_DIALOGUE_PLACEHOLDER} The ${DUO_SPEAKER_LABEL_PLACEHOLDER} shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and natural delivery with subtle blinking and very small head motion. The ${DUO_LISTENER_LABEL_PLACEHOLDER} remains mostly still and silent, with restrained micro-reactions, minimal gaze shifts, and no visible speaking motion. Both anchors maintain formal professional posture. The camera remains fixed and stable with no noticeable drift. The overall feeling is calm, steady, and professional.`;
const OPENING_TEMPLATE_DUO_EXCHANGE = `Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. The two anchors speak in sequence during this clip. ${SPOKEN_DIALOGUE_PLACEHOLDER} Only the anchor delivering the current line shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and subtle blinking with very small head motion. The other anchor listens attentively, remains silent and mostly still, with restrained micro-reactions and no visible speaking motion. Both anchors maintain formal professional posture. Both anchors remain visible in the same frame at all times. The shot stays a fixed two-anchor composition for the entire clip with no cut to a solo shot, no reframing, and no change in shot size. The camera remains fully locked and stable throughout. The overall feeling is calm, steady, and professional.`;
const MIDDLE_TEMPLATE_DUO_EXCHANGE = `Middle shot, tight two-anchor composition in a clean modern studio with balanced framing, neutral lighting, and clear face visibility. ${SPOKEN_DIALOGUE_PLACEHOLDER} The currently speaking anchor shows clearly visible, active speech mouth movement synchronized to the spoken Chinese line, with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, active jaw movement on syllables, a steady eyeline, and natural delivery with subtle blinking and very small head motion. The non-speaking anchor remains mostly still and silent, with restrained micro-reactions, minimal gaze shifts, and no visible speaking motion. Both anchors maintain formal professional posture. The camera remains fixed and stable with no noticeable drift. The overall feeling is calm, steady, and professional.`;
const CLOSING_TEMPLATE_DUO_EXCHANGE = `Closing shot in a tight duo frame. Both anchors remain at the desk in a clean, quiet studio with stable framing and neutral lighting. ${SPOKEN_DIALOGUE_PLACEHOLDER} The currently speaking anchor keeps clearly visible, active speech mouth movement with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, active jaw movement on spoken syllables, steady gaze, subtle blinking, and calm professional posture. The non-speaking anchor remains silent, composed, and mostly still, with only slight natural listening reactions and no visible speaking motion. Both anchors may show very subtle sign-off behavior such as small posture adjustments, but movement stays minimal and controlled. The camera remains stable and the ending feels composed, polished, and naturally complete.`;
const CLOSING_TEMPLATE = `Closing shot in a tight duo frame. Both anchors remain at the desk in a clean, quiet studio with stable framing and neutral lighting. The ${DUO_SPEAKER_LABEL_PLACEHOLDER} delivers the closing line. ${SPOKEN_DIALOGUE_PLACEHOLDER} The ${DUO_SPEAKER_LABEL_PLACEHOLDER} keeps clearly visible, active speech mouth movement with distinct mouth opening and closing, clearly readable articulation, visible lip shaping, active jaw movement on spoken syllables, steady gaze, subtle blinking, and calm professional posture. The ${DUO_LISTENER_LABEL_PLACEHOLDER} remains silent, composed, and mostly still, with only slight natural listening reactions and no visible speaking motion. Both anchors may show very subtle sign-off behavior such as slight paper settling or small posture adjustment, but movement stays minimal and controlled. The camera remains stable and the ending feels composed, polished, and naturally complete.`;

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
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function round3(value) {
  return Math.round(Number(value) * 1000) / 1000;
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function tokenizeForMatch(value) {
  const normalized = normalizeText(value).toLowerCase();
  if (!normalized) return [];
  return Array.from(normalized.matchAll(/[a-z0-9]+|[\u4e00-\u9fff]{2,}/gu), (m) => m[0]).filter((t) => t.length >= 2);
}

function resolveRepoPath(relativePath) {
  return path.resolve(WORKFLOW_ROOT, relativePath.replaceAll('/', path.sep));
}

function resolveProjectPath(projectRoot, relativePath) {
  return path.resolve(projectRoot, relativePath.replaceAll('/', path.sep));
}

function readWavDurationSeconds(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') {
    throw new Error(`Unsupported WAV header: ${filePath}`);
  }
  let offset = 12;
  let sampleRate = 0;
  let blockAlign = 0;
  let dataSize = 0;
  while (offset + 8 <= buffer.length) {
    const chunkId = buffer.toString('ascii', offset, offset + 4);
    const chunkSize = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;
    if (chunkId === 'fmt ') {
      sampleRate = buffer.readUInt32LE(chunkStart + 4);
      blockAlign = buffer.readUInt16LE(chunkStart + 12);
    } else if (chunkId === 'data') {
      dataSize = chunkSize;
    }
    offset = chunkStart + chunkSize + (chunkSize % 2);
  }
  if (!sampleRate || !blockAlign || !dataSize) {
    throw new Error(`Failed to parse WAV duration: ${filePath}`);
  }
  return round3((dataSize / blockAlign) / sampleRate);
}

function readImageSize(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (filePath.toLowerCase().endsWith('.png')) {
    if (buffer.length >= 24 && buffer.subarray(0, 8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]))) {
      return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
    }
  }
  throw new Error(`Unsupported image format or unreadable image: ${filePath}`);
}

function inferAudioPath(entry) {
  if (entry.planned_audio_path) return entry.planned_audio_path;
  return `audio/${entry.speaker}/${entry.entry_id}.wav`;
}

function buildTimeline(ttsPlan, projectRoot) {
  return {
    schema_version: '1.0',
    title: ttsPlan.title || 'news-commentary-audio-timeline',
    audio_format: 'wav',
    entries: ttsPlan.entries.map((entry) => {
      const relativeAudioPath = inferAudioPath(entry).replaceAll('\\', '/');
      const absoluteAudioPath = resolveProjectPath(projectRoot, relativeAudioPath);
      const duration_seconds = readWavDurationSeconds(absoluteAudioPath);
      return {
        entry_id: entry.entry_id,
        script_line_id: entry.script_line_id,
        segment_no: entry.segment_no,
        segment_type: entry.segment_type,
        line_no: entry.line_no,
        speaker: entry.speaker,
        text: entry.text,
        ...(entry.emotion ? { emotion: entry.emotion } : {}),
        audio_path: relativeAudioPath,
        duration_seconds,
        pause_before: Number(entry.pause_before || 0),
        pause_after: Number(entry.pause_after || 0),
        split_part_no: Number(entry.split_part_no || 1),
        split_part_total: Number(entry.split_part_total || 1),
        ...(entry.split_group_id ? { split_group_id: entry.split_group_id } : {}),
        source_line_text: entry.source_line_text,
        resynthesis_round: Number(entry.resynthesis_round || 0),
        needs_resynthesis: duration_seconds > 15.0,
        ...(duration_seconds > 15.0 ? { resynthesis_reason: 'actual generated audio exceeds 15 seconds' } : {}),
        voice_source: entry.voice_source,
      };
    }),
  };
}

function segmentLookup(script) {
  return new Map(script.segments.map((segment) => [segment.segment_no, segment]));
}

function lineLookup(script) {
  const map = new Map();
  for (const segment of script.segments) {
    for (const line of segment.lines) map.set(line.line_id, line);
  }
  return map;
}

function entryDuration(entry) {
  return round3(Number(entry.duration_seconds || entry.estimated_duration_seconds || 0) + Number(entry.pause_before || 0) + Number(entry.pause_after || 0));
}

function imageKeywords(image) {
  return tokenizeForMatch([image.caption || '', image.context_hint || '', image.asset_type || '', path.parse(image.path || '').name].join(' '));
}

function normalizeSourceImages(sourceVisualAssets) {
  const raw = Array.isArray(sourceVisualAssets?.images) ? sourceVisualAssets.images : [];
  return raw.filter((image) => image && typeof image === 'object').map((image, index) => ({
    image_id: String(image.image_id || image.filename || `legacy_img_${String(index + 1).padStart(2, '0')}`),
    source_id: String(image.source_id || 'source'),
    path: String(image.path || image.source_path || image.filename || '').replaceAll('\\', '/'),
    asset_type: String(image.asset_type || 'embedded_image'),
    width: Number.isInteger(image.width) ? image.width : null,
    height: Number.isInteger(image.height) ? image.height : null,
    is_usable_for_video: typeof image.is_usable_for_video === 'boolean' ? image.is_usable_for_video : Boolean(image.path || image.filename),
    video_usage_reason: String(image.video_usage_reason || ''),
    caption: String(image.caption || image.filename || image.image_id || image.id || `legacy_img_${String(index + 1).padStart(2, '0')}`),
    context_hint: String(image.context_hint || image.video_usage_reason || image.source_path || ''),
    preferred_segment_types: Array.isArray(image.preferred_segment_types) && image.preferred_segment_types.length ? image.preferred_segment_types : Array.from(VISUAL_PREFERRED_SEGMENTS),
  }));
}

function entryMatchText(entry, segment, line) {
  return [entry.text || '', line.text || '', segment.segment_goal || '', segment.takeaway || '', segment.visual_hint || ''].join(' ');
}

function scoreImageForEntry(image, entry, segment, line) {
  if (!image.is_usable_for_video) return -999;
  const textBlob = entryMatchText(entry, segment, line).toLowerCase();
  let score = 0;
  for (const token of imageKeywords(image)) {
    if (token && textBlob.includes(token)) score += token.length >= 4 ? 4 : 2;
    else if (token && token.includes(textBlob)) score += 1;
  }
  if (new Set(image.preferred_segment_types || []).has(segment.type)) score += 2;
  if (VISUAL_PREFERRED_SEGMENTS.has(segment.type) && line.speaker === 'guest') score += 2;
  if (DATA_HEAVY_HINTS.some((hint) => textBlob.includes(hint))) score += 2;
  const caption = String(image.caption || '');
  const contextHint = String(image.context_hint || '');
  if (['发布', '现场'].some((word) => (caption + contextHint).includes(word)) && ['发布', '联合', '新闻'].some((word) => textBlob.includes(word))) score += 4;
  if (['模型', '流程', '集群', 'gpu', '训练', '算力'].some((word) => (caption + contextHint).includes(word)) && ['模型', '流程', '集群', 'gpu', '训练', '算力', '性能', '数据'].some((word) => textBlob.includes(word))) score += 5;
  return score;
}

function chooseVisualAssignment(entry, segment, line, sourceImages, blockedImageIds) {
  const segmentType = String(segment.type || '');
  if (!VISUAL_PREFERRED_SEGMENTS.has(segmentType)) {
    return ['ltx', null, 'Opening/closing defaults to anchor-led delivery.', `Use ${line.speaker} anchor shot for on-camera delivery.`];
  }
  const scored = sourceImages.filter((image) => !blockedImageIds.has(image.image_id)).map((image) => [scoreImageForEntry(image, entry, segment, line) + 1, image]).sort((a, b) => b[0] - a[0]);
  const [bestScore, bestImage] = scored[0] || [-999, null];
  if (bestImage && bestScore >= 7) {
    return ['image_audio_ffmpeg', bestImage, 'Source image carries the informational payload better than a talking-head shot for this line.', `Matched source image '${bestImage.caption || bestImage.image_id}' to this line based on caption/context overlap.`];
  }
  if (bestImage && bestScore >= 5 && line.speaker === 'guest') {
    return ['image_audio_ffmpeg', bestImage, 'Guest explanation is data/process-heavy, so a source image is preferred over repeated anchor footage.', `Selected source image '${bestImage.caption || bestImage.image_id}' for a technical explanation beat.`];
  }
  return ['ltx', null, 'Anchor shot keeps persona continuity for this beat.', `Use ${line.speaker} anchor shot because no source image strongly matches this line.`];
}

function shouldContinueDocumentBlock(entry, segment, line, activeImage, currentBlockDuration) {
  if (segment.type === 'opening' || segment.type === 'closing') return false;
  const nextDuration = Number(entry._computed_duration || entry.duration_seconds || 0);
  if (currentBlockDuration + nextDuration > DOCUMENT_BLOCK_MAX_DURATION_SECONDS) return false;
  return scoreImageForEntry(activeImage, entry, segment, line) >= DOCUMENT_BLOCK_CONTINUE_SCORE_THRESHOLD;
}

function ltxReferenceKey(entry, anchorBinding) {
  if (anchorBinding === 'duo') return DEFAULT_DUO_REFERENCE_IMAGE;
  return DEFAULT_ANCHOR_IMAGE_BY_SPEAKER[String(entry.speaker || '')] || '';
}

function canMergeLtxEntries(currentEntries, candidate) {
  if (!currentEntries.length) return true;
  const firstEntry = currentEntries[0];
  const firstBinding = String(firstEntry._anchor_binding || 'duo');
  const candidateBinding = String(candidate._anchor_binding || 'duo');
  if (firstBinding !== candidateBinding) return false;
  if (ltxReferenceKey(firstEntry, firstBinding) !== ltxReferenceKey(candidate, candidateBinding)) return false;
  const currentDuration = currentEntries.reduce((sum, entry) => sum + Number(entry._computed_duration), 0);
  return currentDuration + Number(candidate._computed_duration) <= LTX_MERGE_MAX_DURATION_SECONDS;
}

function forceMinimumDocumentClip(evaluatedEntries, scriptSegments, scriptLines, sourceImages, consumedImageIds) {
  const hasDocumentEntry = evaluatedEntries.some((entry) => entry._render_mode === 'image_audio_ffmpeg' && entry._chosen_image);
  if (hasDocumentEntry || !sourceImages.length) return;

  const candidates = [];
  for (const entry of evaluatedEntries) {
    const segment = scriptSegments.get(entry.segment_no);
    const line = scriptLines.get(entry.script_line_id);
    if (segment.type === 'opening' || segment.type === 'closing') continue;
    if (Number(entry._computed_duration || 0) > DOCUMENT_BLOCK_MAX_DURATION_SECONDS) continue;
    let bestScore = -999;
    let bestImage = null;
    for (const image of sourceImages) {
      if (consumedImageIds.has(image.image_id)) continue;
      const score = scoreImageForEntry(image, entry, segment, line);
      if (score > bestScore) {
        bestScore = score;
        bestImage = image;
      }
    }
    if (bestImage) candidates.push([bestScore, entry, bestImage]);
  }
  if (!candidates.length) throw new Error('Usable source images exist, but no entry could be matched to a document clip within the 6s limit.');
  candidates.sort((a, b) => b[0] - a[0]);
  const [, chosenEntry, chosenImage] = candidates[0];
  consumedImageIds.add(chosenImage.image_id);
  chosenEntry._render_mode = 'image_audio_ffmpeg';
  chosenEntry._chosen_image = chosenImage;
  chosenEntry._render_reason = 'Usable source images exist, so at least one document-led clip is mandatory for the program.';
  chosenEntry._image_selection_reason = `Forced source-image binding to satisfy minimum document-clip requirement using '${chosenImage.caption || chosenImage.image_id}'.`;
}

function forceAllSourceImagesUsed(evaluatedEntries, scriptSegments, scriptLines, sourceImages) {
  if (!sourceImages.length) return;
  const assignedImageIds = new Set(evaluatedEntries.map((entry) => entry?._chosen_image?.image_id).filter(Boolean));
  const reservedEntryIds = new Set(evaluatedEntries.filter((entry) => entry._render_mode === 'image_audio_ffmpeg').map((entry) => entry.entry_id));

  for (const image of sourceImages) {
    if (assignedImageIds.has(image.image_id)) continue;
    const candidates = [];
    for (const entry of evaluatedEntries) {
      if (reservedEntryIds.has(entry.entry_id)) continue;
      if (Number(entry._computed_duration || 0) > DOCUMENT_BLOCK_MAX_DURATION_SECONDS) continue;
      const segment = scriptSegments.get(entry.segment_no);
      if (segment.type === 'opening' || segment.type === 'closing') continue;
      const line = scriptLines.get(entry.script_line_id);
      candidates.push([scoreImageForEntry(image, entry, segment, line), entry]);
    }
    if (!candidates.length) throw new Error(`Source image ${image.image_id} could not be assigned within the ${DOCUMENT_BLOCK_MAX_DURATION_SECONDS}s document-image limit.`);
    candidates.sort((a, b) => b[0] - a[0]);
    const [, chosenEntry] = candidates[0];
    chosenEntry._render_mode = 'image_audio_ffmpeg';
    chosenEntry._chosen_image = image;
    chosenEntry._render_reason = `Forced source-image binding so image '${image.caption || image.image_id}' is used exactly once in the program.`;
    chosenEntry._image_selection_reason = `Assigned source image '${image.caption || image.image_id}' to the best available <= ${DOCUMENT_BLOCK_MAX_DURATION_SECONDS}s anchor-led entry because every source image must appear once.`;
    assignedImageIds.add(image.image_id);
    reservedEntryIds.add(chosenEntry.entry_id);
  }
}

function computeAnchorBindingPlan(anchorEntries) {
  const binding = new Map();
  let runStart = 0;
  while (runStart < anchorEntries.length) {
    let runEnd = runStart + 1;
    const runSpeaker = anchorEntries[runStart].speaker;
    let runDuration = anchorEntries[runStart]._computed_duration;
    while (runEnd < anchorEntries.length && anchorEntries[runEnd].speaker === runSpeaker) {
      runDuration += anchorEntries[runEnd]._computed_duration;
      runEnd += 1;
    }
    const runBinding = runDuration > SOLO_CONTINUOUS_SECONDS_THRESHOLD ? 'solo' : 'duo';
    for (let i = runStart; i < runEnd; i += 1) binding.set(anchorEntries[i].entry_id, runBinding);
    runStart = runEnd;
  }
  return binding;
}

function buildLtxClip(entries, segment, line, anchorBinding, renderReason, imageSelectionReason, durationSource) {
  const firstEntry = entries[0];
  const speaker = firstEntry.speaker;
  const clipId = firstEntry.entry_id.includes('line') ? firstEntry.entry_id.replace('line', 'clip') : `${firstEntry.entry_id}_clip`;
  const duration = round3(entries.reduce((sum, entry) => sum + Number(entry._computed_duration), 0));
  const audioPaths = entries.map((entry) => entry.audio_path);
  const audioEntryIds = entries.map((entry) => entry.entry_id);
  const lineRefs = entries.map((entry) => entry.line_no);
  const uniqueSpeakers = new Set(entries.map((entry) => String(entry.speaker || '')));
  const speakerFocus = uniqueSpeakers.size === 1 ? speaker : 'duo';
  const groupingReason = entries.length > 1
    ? 'Consecutive spoken units share one anchor reference image, so they stay inside one continuous anchor-led clip.'
    : 'Keep one spoken unit per clip for stable lip-sync and simple review.';
  if (anchorBinding === 'duo') {
    return {
      clip_id: clipId,
      segment_no: segment.segment_no,
      segment_type: segment.type,
      render_mode: 'ltx',
      anchor_binding: 'duo',
      character_bindings: ['host', 'guest'],
      visual_asset_paths: [DEFAULT_ANCHOR_IMAGE_BY_SPEAKER.host, DEFAULT_ANCHOR_IMAGE_BY_SPEAKER.guest],
      composite_visual_asset_path: DEFAULT_DUO_REFERENCE_IMAGE,
      speaker_focus: speakerFocus,
      image_mode: 'duo_frame',
      audio_entry_ids: audioEntryIds,
      audio_paths: audioPaths,
      line_refs: lineRefs,
      computed_duration_seconds: duration,
      duration_source: durationSource,
      grouping_reason: groupingReason,
      render_reason: renderReason,
      image_selection_reason: imageSelectionReason,
      target_dimensions: DEFAULT_TARGET_DIMENSIONS,
      image_fit_mode: 'match_image',
      transition_in: segment.type === 'opening' && line.line_no === 1 ? 'cold_open' : 'cut',
      transition_out: 'cut',
    };
  }
  const imageMode = speaker === 'host' ? 'female_solo' : 'male_solo';
  return {
    clip_id: clipId,
    segment_no: segment.segment_no,
    segment_type: segment.type,
    render_mode: 'ltx',
    anchor_binding: 'solo',
    character_bindings: [speaker],
    visual_asset_paths: [DEFAULT_ANCHOR_IMAGE_BY_SPEAKER[speaker]],
    speaker_focus: speakerFocus,
    image_mode: imageMode,
    audio_entry_ids: audioEntryIds,
    audio_paths: audioPaths,
    line_refs: lineRefs,
    computed_duration_seconds: duration,
    duration_source: durationSource,
    grouping_reason: groupingReason,
    render_reason: renderReason,
    image_selection_reason: imageSelectionReason,
    target_dimensions: DEFAULT_TARGET_DIMENSIONS,
    image_fit_mode: 'match_image',
    transition_in: 'cut',
    transition_out: 'cut',
  };
}

function buildDocumentClip(entries, segment, chosenImage, durationSource) {
  const firstEntry = entries[0];
  const clipId = firstEntry.entry_id.includes('line') ? firstEntry.entry_id.replace('line', 'clip') : `${firstEntry.entry_id}_clip`;
  const duration = round3(entries.reduce((sum, entry) => sum + Number(entry._computed_duration), 0));
  return {
    clip_id: clipId,
    segment_no: segment.segment_no,
    segment_type: segment.type,
    render_mode: 'image_audio_ffmpeg',
    anchor_binding: 'document',
    character_bindings: [],
    visual_asset_paths: [],
    speaker_focus: firstEntry.speaker,
    image_mode: 'document_image',
    audio_entry_ids: entries.map((entry) => entry.entry_id),
    audio_paths: entries.map((entry) => entry.audio_path),
    line_refs: entries.map((entry) => entry.line_no),
    computed_duration_seconds: duration,
    duration_source: durationSource,
    grouping_reason: entries.length > 1 ? 'Consecutive spoken units share one source image, so they stay inside one continuous document-led visual block.' : 'Single audio entry remains one clip, but visual payload is carried by source imagery.',
    render_reason: entries.length === 1 ? entries[0]._render_reason : 'One source image is used once as a continuous visual block across consecutive matching audio units.',
    image_selection_reason: entries.length === 1 ? entries[0]._image_selection_reason : `Reused source image '${chosenImage.image_id}' only inside one continuous block, then retire it for the rest of the program.`,
    source_image_ids: [chosenImage.image_id],
    source_image_paths: [chosenImage.path],
    target_dimensions: { width: Number.isInteger(chosenImage.width) ? chosenImage.width : DEFAULT_TARGET_DIMENSIONS.width, height: Number.isInteger(chosenImage.height) ? chosenImage.height : DEFAULT_TARGET_DIMENSIONS.height },
    image_fit_mode: 'scale_pad',
    transition_in: 'cut',
    transition_out: 'cut',
  };
}

function buildClipPlan(script, audioTimeline, sourceVisualAssets, options = {}) {
  const entries = audioTimeline.entries || [];
  const scriptSegments = segmentLookup(script);
  const scriptLines = lineLookup(script);
  const sourceImages = normalizeSourceImages(sourceVisualAssets).filter((image) => image.is_usable_for_video);
  const consumedImageIds = new Set();
  const evaluatedEntries = [];
  const anchorEntries = [];
  let activeDocumentImage = null;
  let activeDocumentDuration = 0.0;
  for (const entry of entries) {
    const segment = scriptSegments.get(entry.segment_no);
    const line = scriptLines.get(entry.script_line_id);
    const computedDuration = entryDuration(entry);
    let renderMode = 'ltx';
    let chosenImage = null;
    let renderReason = 'Anchor shot keeps persona continuity for this beat.';
    let imageSelectionReason = `Use ${line.speaker} anchor shot because no source image strongly matches this line.`;
    if (segment.type === 'opening' || segment.type === 'closing') {
      activeDocumentImage = null;
      activeDocumentDuration = 0.0;
    } else if (activeDocumentImage && shouldContinueDocumentBlock({ ...entry, _computed_duration: computedDuration }, segment, line, activeDocumentImage, activeDocumentDuration)) {
      renderMode = 'image_audio_ffmpeg';
      chosenImage = activeDocumentImage;
      renderReason = 'Continue the same source image block so one news image appears only once in one uninterrupted visual run.';
      imageSelectionReason = `Continue source image '${activeDocumentImage.image_id}' across consecutive matching audio units instead of cutting away and later reusing it.`;
      activeDocumentDuration = round3(activeDocumentDuration + computedDuration);
    } else {
      activeDocumentImage = null;
      activeDocumentDuration = 0.0;
      [renderMode, chosenImage, renderReason, imageSelectionReason] = chooseVisualAssignment(entry, segment, line, sourceImages, consumedImageIds);
      if (renderMode === 'image_audio_ffmpeg' && computedDuration > DOCUMENT_BLOCK_MAX_DURATION_SECONDS) {
        renderMode = 'ltx';
        chosenImage = null;
        renderReason = `Anchor shot keeps persona continuity because a source image may stay on screen for at most ${DOCUMENT_BLOCK_MAX_DURATION_SECONDS} seconds continuously.`;
        imageSelectionReason = `Do not start source image usage on this entry because its audio duration already exceeds the ${DOCUMENT_BLOCK_MAX_DURATION_SECONDS}s document-image limit.`;
      }
      if (renderMode === 'image_audio_ffmpeg' && chosenImage) {
        consumedImageIds.add(chosenImage.image_id);
        activeDocumentImage = chosenImage;
        activeDocumentDuration = computedDuration;
      }
    }
    const evaluatedEntry = { ...entry, _computed_duration: computedDuration, _render_mode: renderMode, _chosen_image: chosenImage, _render_reason: renderReason, _image_selection_reason: imageSelectionReason };
    if (segment.type === 'opening' || segment.type === 'closing') {
      evaluatedEntry._anchor_binding = 'duo';
      evaluatedEntry._render_mode = 'ltx';
      evaluatedEntry._chosen_image = null;
      evaluatedEntry._render_reason = segment.type === 'opening' ? 'Opening beats must stay in duo frame to establish the show before moving into explanation clips.' : 'Closing beats must stay in duo frame so the program signs off with both anchors on screen.';
      evaluatedEntry._image_selection_reason = segment.type === 'opening' ? 'Opening beats should prioritize program identity over source visuals.' : 'Closing beats should preserve the duo-anchor sign-off instead of switching to source visuals.';
      activeDocumentImage = null;
      activeDocumentDuration = 0.0;
    }
    if (evaluatedEntry._render_mode === 'ltx') anchorEntries.push(evaluatedEntry);
    evaluatedEntries.push(evaluatedEntry);
  }
  forceMinimumDocumentClip(evaluatedEntries, scriptSegments, scriptLines, sourceImages, consumedImageIds);
  forceAllSourceImagesUsed(evaluatedEntries, scriptSegments, scriptLines, sourceImages);
  const anchorBindingByEntryId = computeAnchorBindingPlan(anchorEntries);
  for (const entry of evaluatedEntries) {
    if (entry._render_mode === 'ltx' && !entry._anchor_binding) entry._anchor_binding = anchorBindingByEntryId.get(entry.entry_id) || 'duo';
  }
  const clips = [];
  let index = 0;
  while (index < evaluatedEntries.length) {
    const entry = evaluatedEntries[index];
    if (entry._render_mode === 'image_audio_ffmpeg' && entry._chosen_image) {
      const documentEntries = [entry];
      const imageId = entry._chosen_image.image_id;
      let nextIndex = index + 1;
      while (nextIndex < evaluatedEntries.length) {
        const candidate = evaluatedEntries[nextIndex];
        const candidateImage = candidate._chosen_image;
        if (candidate._render_mode === 'image_audio_ffmpeg' && candidateImage && candidateImage.image_id === imageId) {
          documentEntries.push(candidate);
          nextIndex += 1;
          continue;
        }
        break;
      }
      clips.push(buildDocumentClip(documentEntries, scriptSegments.get(entry.segment_no), entry._chosen_image, 'audio_timeline'));
      index = nextIndex;
      continue;
    }
    const ltxEntries = [entry];
    let nextIndex = index + 1;
    while (nextIndex < evaluatedEntries.length) {
      const candidate = evaluatedEntries[nextIndex];
      if (candidate._render_mode !== 'ltx') break;
      if (!canMergeLtxEntries(ltxEntries, candidate)) break;
      ltxEntries.push(candidate);
      nextIndex += 1;
    }
    clips.push(buildLtxClip(ltxEntries, scriptSegments.get(entry.segment_no), scriptLines.get(entry.script_line_id), entry._anchor_binding, entry._render_reason, entry._image_selection_reason, 'audio_timeline'));
    index = nextIndex;
  }
  return {
    schema_version: '1.0',
    title: script.title || audioTimeline.title || 'news-commentary-clip-plan',
    source_visual_assets_ref: 'source-assets/source-visual-assets.json',
    aggregation_rules: {
      default_grouping_policy: 'Prefer one spoken unit per clip for stable lip-sync and easier render routing.',
      duo_frame_policy: 'Merge consecutive anchor-led units when they keep the same anchor reference image and total duration stays within the LTX limit; otherwise split conservatively.',
      max_lines_per_clip: Math.max(...clips.map((clip) => (clip.line_refs || []).length), 1),
      split_on_speaker_change: false,
      split_on_long_duration_seconds: 15.0,
      short_dialogue_duo_max_seconds: 15.0,
      long_single_speaker_solo_min_seconds: 15.0,
      ltx_max_duration_seconds: LTX_MERGE_MAX_DURATION_SECONDS,
      source_image_reuse_policy: `Each source image must appear exactly once in the program, only as one continuous document-led visual block, and that block must stay within ${DOCUMENT_BLOCK_MAX_DURATION_SECONDS} seconds before cutting back to anchor-led shots.`,
      duration_source: 'audio_timeline',
    },
    clips,
  };
}

function indexAudioEntries(audioTimeline) {
  return new Map((audioTimeline.entries || []).map((entry) => [entry.entry_id, entry]));
}

function indexSourceImages(sourceVisualAssets) {
  const map = new Map();
  for (const image of sourceVisualAssets?.images || []) {
    if (!image || typeof image !== 'object') continue;
    const imageId = String(image.image_id || image.filename || image.id || '');
    const imagePath = String(image.path || image.source_path || image.filename || '').replaceAll('\\', '/');
    map.set(imageId, { ...image, image_id: imageId, path: imagePath });
  }
  return map;
}

function determineTemplateType(index, total) {
  if (total <= 0 || index === 0) return 'opening';
  if (index === total - 1) return 'closing';
  return 'middle';
}

function buildTemplatePrompt(clip, templateType, imageMode, speakerFocus) {
  if (imageMode === 'duo_frame' && speakerFocus === 'duo') {
    if (templateType === 'opening') return OPENING_TEMPLATE_DUO_EXCHANGE;
    if (templateType === 'middle') return MIDDLE_TEMPLATE_DUO_EXCHANGE;
    return CLOSING_TEMPLATE_DUO_EXCHANGE;
  }
  if (templateType === 'opening') return OPENING_TEMPLATE;
  if (templateType === 'middle') return imageMode === 'duo_frame' || speakerFocus === 'duo' ? MIDDLE_TEMPLATE_DUO : MIDDLE_TEMPLATE_SOLO;
  return CLOSING_TEMPLATE;
}

function speakerLabelFromFocus(templatePrompt, speakerFocus, imageMode) {
  const isDuo = imageMode === 'duo_frame' || templatePrompt.toLowerCase().includes('two-anchor') || templatePrompt.toLowerCase().includes('duo frame');
  if (speakerFocus === 'host') return isDuo ? 'left female speaker' : 'female anchor';
  if (speakerFocus === 'guest') return isDuo ? 'right male speaker' : 'male anchor';
  return isDuo ? 'left female speaker' : 'speaking anchor';
}

function listenerLabelFromFocus(templatePrompt, speakerFocus, imageMode) {
  const isDuo = imageMode === 'duo_frame' || templatePrompt.toLowerCase().includes('two-anchor') || templatePrompt.toLowerCase().includes('duo frame');
  if (!isDuo) return 'listener';
  if (speakerFocus === 'host') return 'right male listener';
  if (speakerFocus === 'guest') return 'left female listener';
  return 'right male listener';
}

function resolvePromptSpeakerFocus(clip, audioEntryMap) {
  if (clip.image_mode !== 'duo_frame') return clip.speaker_focus || 'host';
  const ids = clip.audio_entry_ids || [];
  const speakers = new Set(ids.map((entryId) => String(audioEntryMap.get(entryId)?.speaker || '')).filter(Boolean));
  if (speakers.size > 1) return 'duo';
  if (ids.length === 1) {
    const entry = audioEntryMap.get(ids[0]);
    if (entry && (entry.speaker === 'host' || entry.speaker === 'guest')) return entry.speaker;
  }
  return clip.speaker_focus === 'host' || clip.speaker_focus === 'guest' ? clip.speaker_focus : 'host';
}

function assembleLtxPrompt(templatePrompt, spokenText, speakerFocus, imageMode) {
  if (imageMode === 'duo_frame' && speakerFocus === 'duo') {
    const dialogueSentence = spokenText ? `${spokenText}` : '';
    return templatePrompt.replaceAll(SPOKEN_DIALOGUE_PLACEHOLDER, dialogueSentence).replace(/\s+/g, ' ').trim();
  }
  const speakerLabel = speakerLabelFromFocus(templatePrompt, speakerFocus, imageMode);
  const listenerLabel = listenerLabelFromFocus(templatePrompt, speakerFocus, imageMode);
  const dialogueSentence = spokenText ? `The ${speakerLabel} says in Chinese: "${spokenText.replaceAll('"', '\\"')}".` : '';
  return templatePrompt.replaceAll(SPOKEN_DIALOGUE_PLACEHOLDER, dialogueSentence).replaceAll(DUO_SPEAKER_LABEL_PLACEHOLDER, speakerLabel).replaceAll(DUO_LISTENER_LABEL_PLACEHOLDER, listenerLabel).replace(/\s+/g, ' ').trim();
}

function collectClipSpokenText(clip, audioEntryMap) {
  return (clip.audio_entry_ids || []).map((entryId) => audioEntryMap.get(entryId)?.text || '').join(' ').trim();
}

function collectOrderedDuoDialogue(clip, audioEntryMap) {
  return (clip.audio_entry_ids || []).map((entryId, index) => {
    const entry = audioEntryMap.get(entryId);
    if (!entry) return '';
    const speakerLabel = entry.speaker === 'host' ? 'left female anchor' : 'right male anchor';
    const intro = index === 0 ? `The ${speakerLabel} says in Chinese:` : `Then the ${speakerLabel} says in Chinese:`;
    return `${intro} \"${String(entry.text || '').replaceAll('"', '\\"')}\".`;
  }).filter(Boolean).join(' ');
}

function resolveAudioPaths(clip, audioEntryMap) {
  const resolved = (clip.audio_entry_ids || []).map((entryId) => {
    const entry = audioEntryMap.get(entryId);
    if (!entry) throw new Error(`Missing audio entry ${entryId}`);
    return entry.audio_path;
  });
  if (clip.audio_paths?.length && resolved.length && JSON.stringify(clip.audio_paths) !== JSON.stringify(resolved)) {
    throw new Error(`Clip ${clip.clip_id} has stale audio_paths`);
  }
  return resolved.length ? resolved : (clip.audio_paths || []);
}

function clipDurationFromAudioEntries(clip, audioEntryMap) {
  return round3((clip.audio_entry_ids || []).reduce((sum, entryId) => {
    const entry = audioEntryMap.get(entryId);
    if (!entry) throw new Error(`Missing audio entry ${entryId}`);
    return sum + Number(entry.duration_seconds || 0) + Number(entry.pause_before || 0) + Number(entry.pause_after || 0);
  }, 0));
}

function resolveSourceImagePaths(clip, sourceImageMap) {
  const ids = clip.source_image_ids || [];
  const resolved = ids.map((imageId) => {
    const image = sourceImageMap.get(imageId);
    if (!image) throw new Error(`Missing source image ${imageId}`);
    return image.path;
  });
  return [ids, resolved.length ? resolved : (clip.source_image_paths || [])];
}

function resolveLtxImagePaths(clip, ltxClipIndex) {
  if (ltxClipIndex === 0 && clip.segment_type === 'opening' && clip.image_mode === 'duo_frame') return DEFAULT_OPENING_LTX_IMAGES;
  if (clip.segment_type === 'closing' && clip.image_mode === 'duo_frame') return DEFAULT_CLOSING_LTX_IMAGES;
  if (clip.image_mode === 'duo_frame') return DEFAULT_MIDDLE_DUO_LTX_IMAGES;
  return [DEFAULT_ANCHOR_IMAGE_BY_MODE[clip.image_mode]];
}

function buildRenderPlan(clipPlan, audioTimeline, sourceVisualAssets, clipPlanRef, projectRoot, options = {}) {
  const audioEntryMap = indexAudioEntries(audioTimeline);
  const sourceImageMap = indexSourceImages(sourceVisualAssets);
  const clips = clipPlan.clips || [];
  const ltxClipIds = clips.filter((clip) => clip.render_mode === 'ltx').map((clip) => clip.clip_id);
  const ltxClipIndexMap = new Map(ltxClipIds.map((clipId, index) => [clipId, index]));
  const renderItems = clips.map((clip) => {
    const audioPaths = resolveAudioPaths(clip, audioEntryMap);
    const computedDurationSeconds = clipDurationFromAudioEntries(clip, audioEntryMap);
    const renderItem = {
      clip_id: clip.clip_id,
      render_mode: clip.render_mode,
      anchor_binding: clip.anchor_binding,
      character_bindings: clip.character_bindings,
      audio_paths: audioPaths,
      output_path: `video/segments/${clip.clip_id}.mp4`,
      computed_duration_seconds: computedDurationSeconds,
      duration_source: 'audio_timeline',
      pad_color: DEFAULT_PAD_COLOR,
    };
    if (clip.render_mode === 'ltx') {
      if (!options.ignoreDurationLimit && computedDurationSeconds > DEFAULT_LTX_MAX_DURATION_SECONDS) throw new Error(`LTX clip ${clip.clip_id} exceeds 15s`);
      const ltxImagePaths = resolveLtxImagePaths(clip, ltxClipIndexMap.get(clip.clip_id));
      const anchorImagePath = ltxImagePaths[0];
      const targetDimensions = readImageSize(resolveRepoPath(anchorImagePath));
      const speakerFocus = resolvePromptSpeakerFocus(clip, audioEntryMap);
      const templateType = determineTemplateType(ltxClipIndexMap.get(clip.clip_id) || 0, ltxClipIds.length);
      const templatePrompt = buildTemplatePrompt(clip, templateType, clip.image_mode, speakerFocus);
      const spokenText = speakerFocus === 'duo' ? collectOrderedDuoDialogue(clip, audioEntryMap) : collectClipSpokenText(clip, audioEntryMap);
      renderItem.anchor_image_path = anchorImagePath;
      renderItem.video_size_source = 'anchor_image';
      renderItem.target_dimensions = targetDimensions;
      renderItem.image_fit_mode = 'match_image';
      renderItem.optimized_prompt = assembleLtxPrompt(templatePrompt, spokenText, speakerFocus, clip.image_mode);
      renderItem.ltx_request = {
        mode: 'audio_to_video',
        ...(audioPaths.length === 1 ? { audio: audioPaths[0] } : {}),
        audio_paths: audioPaths,
        images: ltxImagePaths,
        save_path: `video/segments/${clip.clip_id}.mp4`,
        a2v_audio_start_time: DEFAULT_LTX_AUDIO_START_TIME_SECONDS,
        a2v_audio_insert_video_time: DEFAULT_LTX_AUDIO_INSERT_VIDEO_TIME_SECONDS,
        negative_prompt: DEFAULT_LTX_NEGATIVE_PROMPT,
        duration_seconds: round3(computedDurationSeconds + DEFAULT_LTX_VIDEO_DURATION_PADDING_SECONDS),
      };
      return renderItem;
    }
    const [sourceImageIds, sourceImagePaths] = resolveSourceImagePaths(clip, sourceImageMap);
    const firstImage = sourceImageMap.get(sourceImageIds[0]);
    const targetDimensions = Number.isInteger(firstImage?.width) && Number.isInteger(firstImage?.height)
      ? { width: firstImage.width, height: firstImage.height }
      : readImageSize(resolveProjectPath(projectRoot, sourceImagePaths[0]));
    renderItem.source_image_ids = sourceImageIds;
    renderItem.source_image_paths = sourceImagePaths;
    renderItem.video_size_source = 'source_image';
    renderItem.target_dimensions = targetDimensions;
    renderItem.image_fit_mode = 'scale_pad';
    renderItem.ffmpeg_request = {
      mode: 'image_audio_ffmpeg',
      image_paths: sourceImagePaths,
      audio_paths: audioPaths,
      save_path: `video/segments/${clip.clip_id}.mp4`,
      target_width: targetDimensions.width,
      target_height: targetDimensions.height,
      image_fit_mode: 'scale_pad',
      pad_color: DEFAULT_PAD_COLOR,
      motion_style: 'ken_burns',
      subtitle_mode: 'none',
    };
    return renderItem;
  });
  return {
    schema_version: '1.0',
    title: clipPlan.title || audioTimeline.title || 'news-commentary-render-plan',
    clip_plan_ref: clipPlanRef.replaceAll('\\', '/'),
    source_visual_assets_ref: 'source-assets/source-visual-assets.json',
    render_items: renderItems,
  };
}

function main() {
  const args = parseArgs(process.argv);
  const projectDir = args['project-dir'];
  if (!projectDir) throw new Error('Provide --project-dir');
  const ignoreDurationLimit = String(args['ignore-duration-limit'] || '').toLowerCase() === 'true';
  const projectRoot = path.resolve(projectDir);
  const ttsPlanPath = path.join(projectRoot, 'audio', 'tts-plan.json');
  const timelinePath = path.join(projectRoot, 'audio', 'timeline.json');
  const clipPlanPath = path.join(projectRoot, 'video', 'clip-plan.json');
  const renderPlanPath = path.join(projectRoot, 'video', 'render-plan.json');
  const scriptPath = path.join(projectRoot, 'script.json');
  const sourceVisualAssetsPath = path.join(projectRoot, 'source-assets', 'source-visual-assets.json');
  const ttsPlan = readJson(ttsPlanPath);
  const script = readJson(scriptPath);
  const sourceVisualAssets = readJson(sourceVisualAssetsPath);
  const timeline = buildTimeline(ttsPlan, projectRoot);
  writeJson(timelinePath, timeline);
  const clipPlan = buildClipPlan(script, timeline, sourceVisualAssets, { ignoreDurationLimit });
  writeJson(clipPlanPath, clipPlan);
  const renderPlan = buildRenderPlan(clipPlan, timeline, sourceVisualAssets, clipPlanPath, projectRoot, { ignoreDurationLimit });
  writeJson(renderPlanPath, renderPlan);
  process.stdout.write(JSON.stringify({ timeline: timelinePath, clipPlan: clipPlanPath, renderPlan: renderPlanPath, ignoreDurationLimit }, null, 2));
}

main();
