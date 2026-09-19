const src = $('Compose YT prompt').item.json;
const gem = $json;
function clean(s){ return (s||'').toString().replace(/\s+/g,' ').trim(); }
let g = {};
let raw = (gem.content && gem.content.parts && gem.content.parts[0] && gem.content.parts[0].text) || gem.text || gem.response || gem.output || '';
raw = (raw||'').toString().replace(/```json|```/g,'').trim();
try { g = JSON.parse(raw); } catch(e) { const m = raw.match(/\{[\s\S]*\}/); if (m) { try { g = JSON.parse(m[0]); } catch(_){} } }
const meta = src.metadata || {};
// EEC policy (2026): vertical clips <=3min are auto-classified as Shorts by YouTube
// regardless of the hashtag, and custom thumbnails on Shorts require YouTube Partner
// Program (1000+ subs). Channel is pre-YPP, so we lean into Shorts for growth/reach.
// We still generate + attempt the branded thumbnail (it shows in search/channel/
// playlists and will apply automatically once the channel reaches YPP). Short by
// default; treat >3min (or explicit long) as regular long-form.
// PRIMARY signal (EEC rule): orientation from the probe service — vertical => Short, horizontal => Long.
// Fail-soft to sidecar meta, then default Short.
let isShort = true;
let orient = '';
try { const pr = $('Probe orientation').item.json; if (pr && pr.ok === true && pr.orientation) orient = String(pr.orientation); } catch(e) { orient = ''; }
if (orient === 'horizontal') isShort = false;
else if (orient === 'vertical' || orient === 'square') isShort = true;
else {
  if (meta.is_long === true || String(meta.format||'').toLowerCase()==='long' || String(meta.format||'').toLowerCase()==='longform') isShort = false;
  else if (meta.duration !== undefined && meta.duration !== null) { const d = Number(meta.duration); if (!isNaN(d) && d > 180) isShort = false; }
}
const fmt = isShort ? 'short' : 'long';
let title = clean(g.title || (meta.video_title_for_youtube_short || meta.title) || 'تعلّم الإنجليزي بثقة مع Empire English 🚀');
// 2026 best practice: Shorts titles are truncated on mobile ~40-50 chars -> keep tight, then append #Shorts.
function cut(s, n){ if (s.length <= n) return s; let t = s.slice(0, n); const sp = t.lastIndexOf(' '); if (sp > n * 0.6) t = t.slice(0, sp); return t.trim(); }
if (isShort) { title = cut(title, 50); if (!/#shorts/i.test(title)) title = (title + ' #Shorts'); }
else { title = title.replace(/\s*#shorts/ig,'').trim(); title = cut(title, 95); }
// keyword-rich opening line (search/Google read the first line first). Fallback to caption's essence.
let firstLine = clean(g.first_line || '');
let caption = clean(g.caption || meta.caption || 'درس إنجليزي سريع يفرق معاك! 💪 اتفرّج للآخر وطبّق النهارده.');
if (!firstLine) firstLine = caption.split(/[.!؟\n]/)[0].slice(0,90).trim();
const cta = 'قولنا في الكومنتات: إيه أصعب كلمة نطقتها النهاردة؟ 👇🔥';
// topic (normalize to one of 5 keys; default 'tips')
const VALID=['pronunciation','grammar','vocabulary','conversation','tips'];
let topic=(g.topic||'').toString().toLowerCase().trim();
if(!VALID.includes(topic)) topic='tips';
let hashtags = Array.isArray(meta.hashtags) ? meta.hashtags.map(h=>h.replace(/^#/,'')) : [];
const BRAND = isShort ? ['تعلم_الإنجليزية','إنجليزي','LearnEnglish','EmpireEnglish','Shorts'] : ['تعلم_الإنجليزية','إنجليزي','LearnEnglish','EmpireEnglish','English'];
for (const t of BRAND){ if(!hashtags.some(h=>h.toLowerCase()===t.toLowerCase())) hashtags.push(t); }
hashtags = hashtags.slice(0,5);
const hashtagBlock = hashtags.map(t=>'#'+t).join(' ');
const tags = ['تعلم الانجليزية','English pronunciation','learn English','Empire English','English for Arabic speakers','English tips'].slice(0,6);
// --- Long-form chapters (timestamps) — boosts watch-time navigation + SEO. Only for long videos. ---
let chapterBlock = '';
if (!isShort && Array.isArray(g.chapters) && g.chapters.length >= 2) {
  const lines = [];
  let hasZero = false;
  for (const c of g.chapters) {
    const t = clean((c && c.t) || ''); const label = clean((c && c.label) || '');
    if (!/^\d{1,2}:\d{2}(:\d{2})?$/.test(t) || !label) continue;
    if (t === '0:00' || t === '00:00') hasZero = true;
    lines.push(t + ' ' + label);
  }
  // YouTube requires the first chapter to start at 0:00 to render chapters
  if (lines.length >= 2 && hasZero) chapterBlock = ['⏱️ الفصول:'].concat(lines).join('\n');
}
// --- EEC standardized funnel block (added 2026-09): subscribe + community + placement test ---
const FUNNEL = [
  '🔔 اشترك في القناة عشان توصلك كل دروس Empire English.',
  '',
  '📲 انضم لمجتمعنا على تليجرام: https://t.me/Empire_English_Community',
  '🧪 اعرف مستواك الحقيقي — اختبار تحديد المستوى مجاني (٣٠ دقيقة): https://assessment.empireenglish.online',
  '',
  'إنجليزي حقيقي، نظام مش حيل. Forged in Language. Crowned in Mastery. 👑'
].join('\n');
// Description order: keyword-first line -> value caption -> chapters(long) -> comment CTA -> funnel -> hashtags -> signature
const parts = [firstLine, '', caption];
if (chapterBlock) { parts.push('', chapterBlock); }
parts.push('', cta, '', FUNNEL, '', hashtagBlock, '', '— Empire English Community 👑');
const description = parts.join('\n').trim();
const PIN=['ما أصعب كلمة إنجليزية في النطق بالنسبة لك؟ اكتبها 👇🔥','إيه أكتر حاجة بتقفلك وإنت بتتعلم إنجليزي؟ 🤔 قولنا 👇','جرّب تنطقها وقولنا نتيجتك في الكومنتات! 🎯','عايز فيديو عن موضوع معيّن؟ اطلبه تحت 👇✨','قيّم نطقك من 10 وإحنا نساعدك تتحسّن! 💪'];
let seed=0; const fid=(src.file_id||title); for(let i=0;i<fid.length;i++) seed=(seed+fid.charCodeAt(i))%PIN.length;
// append the community funnel to the pinned comment (subscribe + telegram)
const pinComment = PIN[seed] + '\n\n📲 انضم لمجتمعنا وابدأ رحلتك: https://t.me/Empire_English_Community 👑';
let publishAt=''; const wantSchedule=(meta.schedule===true)||src.yt_schedule===true;
if(wantSchedule){ const now=new Date(); const t=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate(),17,0,0)); if(t.getTime()<=now.getTime()) t.setUTCDate(t.getUTCDate()+1); publishAt=t.toISOString(); }
// Privacy: YouTube requires a video to be PRIVATE when a publishAt (schedule) is set —
// it then auto-goes-public at that time. With NO schedule, an auto-dropped clip must go
// PUBLIC immediately, otherwise it stays private forever (Studio shows "Oops" on the
// public edit page and nobody can see it). So privacy is data-driven: scheduled=>private,
// otherwise=>public. An explicit meta.privacy overrides ('public'|'private'|'unlisted').
const VALID_PRIV=['public','private','unlisted'];
let privacy = publishAt ? 'private' : 'public';
if (meta && typeof meta.privacy==='string' && VALID_PRIV.includes(meta.privacy.toLowerCase())) privacy = meta.privacy.toLowerCase();
return [{ json: Object.assign({}, src, { yt_title:title, yt_description:description, yt_tags:tags, yt_hashtags:hashtagBlock, yt_pin_comment:pinComment, yt_publish_at:publishAt, yt_privacy:privacy, yt_format:fmt, yt_topic:topic }), binary: $('Compose YT prompt').item.binary }];
