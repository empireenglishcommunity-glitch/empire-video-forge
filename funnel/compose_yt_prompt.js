const base = $('Switch: brand branch').item.json;
// The clip binary is dropped by the Probe orientation HTTP node, so the Switch
// item no longer carries it. Pull it from the last node that still has it
// (Download clip (bytes)); fall back to the Switch item just in case.
let clipBin;
try { clipBin = $('Download clip (bytes)').item.binary; } catch(e) { clipBin = undefined; }
if (!clipBin || !clipBin.clip) { try { const sb = $('Switch: brand branch').item.binary; if (sb && sb.clip) clipBin = sb; } catch(e) {} }
let meta = {};
try {
  const b = $input.item.binary;
  if (b && b.sideMeta) {
    const buff = await this.helpers.getBinaryDataBuffer(0, 'sideMeta');
    const parsed = JSON.parse(buff.toString('utf8'));
    if (parsed && typeof parsed === 'object') meta = parsed;
  }
} catch(e) { meta = {}; }
const clip = (meta.title || meta.caption || meta.hook || '').toString().trim();
let hint = (base.file_name || '').replace(/\.[^.]+$/, '').replace(/^(subtitled_|hooked_|hook_|recut_|clip_)+/gi,'').replace(/[_\-]+/g,' ').trim();
const context = clip || hint || 'English learning tip';
// PRIMARY signal (EEC rule): orientation from the probe service — vertical => Short, horizontal => Long.
// Fail-soft: if the probe is unavailable/errored, fall back to sidecar meta, then default Short.
let isShort = true;
let orient = '';
try { const pr = $('Probe orientation').item.json; if (pr && pr.ok === true && pr.orientation) orient = String(pr.orientation); } catch(e) { orient = ''; }
if (orient === 'horizontal') isShort = false;
else if (orient === 'vertical' || orient === 'square') isShort = true;
else {
  // fallback: explicit meta flags, then duration
  if (meta.is_long === true || String(meta.format||'').toLowerCase()==='long' || String(meta.format||'').toLowerCase()==='longform') isShort = false;
  else if (meta.duration !== undefined && meta.duration !== null) { const d = Number(meta.duration); if (!isNaN(d) && d > 180) isShort = false; }
}

const common = [
'You write YouTube metadata for "Empire English Community" (EEC), an English TRANSFORMATION SYSTEM for Arabic speakers (Egypt/MENA). Brand voice: confident, warm, honest coach. NEVER use "hack", "secret", "fluent in X days", or "guaranteed". Prefer "system", "step by step", "real". Content language: Egyptian Arabic with the English term included.',
'Return STRICT JSON only, no markdown.'
];

let spec;
if (isShort) {
  spec = [
    'This is a SHORT (vertical, <=3 min). Keys: "title","first_line","caption","topic".',
    '- title: Arabic-first, curiosity-driven hook, FRONT-LOAD the topic/keyword, <= 50 chars (mobile truncates longer), exactly 1 relevant emoji.',
    '- first_line: ONE keyword-rich Arabic line (<=90 chars) that leads the description; must contain the main English term taught + the core benefit (this line is what search/Google read first).',
    '- caption: 2-3 short energetic Egyptian-Arabic lines: value promise + a question that sparks comments; include the English term; 2-4 emojis; NO hashtags.',
    '- topic: EXACTLY ONE of: "pronunciation","grammar","vocabulary","conversation","tips".'
  ];
} else {
  spec = [
    'This is a LONG-FORM video (16:9, >3 min). Keys: "title","first_line","caption","topic","chapters".',
    '- title: Arabic-first, clear + keyword-front-loaded, <= 70 chars, may include the English term; 0-1 emoji. Do NOT add #Shorts.',
    '- first_line: ONE keyword-rich Arabic line (<=100 chars) leading the description with the main topic + English term + benefit (search/Google read this first).',
    '- caption: 3-5 Egyptian-Arabic lines describing what the viewer will learn (value-packed, keyword-natural), include the English terms taught, end with a question to drive comments; NO hashtags.',
    '- topic: EXACTLY ONE of: "pronunciation","grammar","vocabulary","conversation","tips".',
    '- chapters: an array of 2-6 objects {"t":"M:SS","label":"short Arabic label"} for timestamped chapters; first chapter MUST be {"t":"0:00","label":"مقدمة"}. If you cannot infer real timings, return an empty array [].'
  ];
}

const prompt = common.concat(spec).concat([
  'Never use a raw filename. Clip topic/context:',
  JSON.stringify(context)
]).join('\n');

return [{ json: Object.assign({}, base, { metadata: meta, _yt_prompt: prompt, _yt_is_short: isShort }), binary: clipBin }];
