import fs from 'fs';

const code = (n) => fs.readFileSync(new URL(`./code/${n}.js`, import.meta.url), 'utf8');
let fails = 0;
const check = (cond, what) => { console.log(`${cond ? '  ✅' : '  ❌'} ${what}`); if (!cond) fails++; };

// A tiny stand-in for n8n's Code node: $('Node'), $input, $json.
function run(name, nodes, input) {
  const $ = (n) => {
    if (!(n in nodes)) throw new Error(`Referenced node is unexecuted: ${n}`);
    return { first: () => ({ json: nodes[n] }), all: () => [{ json: nodes[n] }] };
  };
  const $input = { first: () => ({ json: input }), all: () => [{ json: input }] };
  const fn = new Function('$', '$input', '$json', code(name));
  return fn($, $input, input);
}

const LABELS = ['🎬 Make a Short', '🔁 Make a loop Short', '🎞 Make a 15-minute history movie', '🔥 Find a viral topic and make it',
  '⬆️ Upload a finished video to YouTube', '🔄 Remake or 🗑 discard a finished video', '💡 Save an idea for later',
  '📊 See my progress', '⏯ Pause or resume daily videos'];
const ROUTES = ['make', 'make', 'make', 'trend', 'upload', 'fix', 'idea', 'progress', 'pause'];

const real = JSON.parse(fs.readFileSync(new URL('../state/app.json', import.meta.url), 'utf8'));
const state = structuredClone(real);
state.videos.waiting = [
  { id: '20261127-great-stink', kind: 'story', title: 'When Sewage Shut Down Parliament <1858>', topic: 'The Great Stink', seconds: 58,
    description: 'The Great Stink of 1858: London’s Thames smelled so bad Parliament fled.\nWould you have stayed?',
    tags: ['great stink', 'london history', 'victorian london', 'history shorts', 'the great stink of 1858', 'parliament', 'a,b'],
    pinned_comment: 'Would you have survived the smell? 👇', release: 459736323, assets: { 'video.mp4': 111, 'thumbnail.jpg': 112 } },
  { id: '20261127-movie', kind: 'movie', title: 'The Fall of Rome in 15 Minutes', seconds: 905, description: 'x', tags: [],
    pinned_comment: '', release: 459748236, assets: { 'video.mp4': 221 } },
];
state.runs = { story: { at: '2026-11-26T15:21:00+00:00', ok: true, title: 'Explosion with no crater', id: 'x' },
  movie: { at: '2026-11-26T16:50:00+00:00', ok: false, title: '', error: 'Gemini daily allowance used up' } };
const ytOk = { kind: 'youtube#channelListResponse', items: [{ id: 'UC8eZyrH9ANRhpPFGDLL6OLQ', snippet: { title: 'History with Me' },
  statistics: { subscriberCount: '522', viewCount: '43951', videoCount: '12', hiddenSubscriberCount: false } }] };
const ytOther = { items: [{ id: 'UCsomethingelse', snippet: { title: 'Manzil Vlogs' }, statistics: { subscriberCount: '3' } }] };

console.log('Work out the choice');
LABELS.forEach((label, i) => {
  const out = run('work_out', { 'Open the Studio': { action: label, submittedAt: 'x' }, 'Read agent state': state, 'Check YouTube channel': ytOk })[0].json;
  check(out.route === ROUTES[i], `“${label}” → ${out.route}`);
});
const w = run('work_out', { 'Open the Studio': { 'What do you want to do?': LABELS[1] }, 'Read agent state': state, 'Check YouTube channel': ytOk })[0].json;
check(w.key === 'loop' && w.what === 'loop Short', 'label key works when n8n keys answers by label');
const mk = JSON.parse(w.makeForm);
check(mk.some((f) => f.fieldName === 'pick' && f.fieldOptions.values.length >= 2) && mk.some((f) => f.fieldName === 'style'), 'make page: idea dropdown + style');
check(mk[0].fieldType === 'html' && mk[0].html.includes('Strategist') && mk[0].html.includes('1:30 pm'), 'make page: picks + free-plan note');
const movie = run('work_out', { 'Open the Studio': { action: LABELS[2] }, 'Read agent state': state, 'Check YouTube channel': ytOk })[0].json;
check(!JSON.parse(movie.makeForm).some((f) => f.fieldName === 'style') && movie.key === 'movie', 'movie page has no style');
const up = JSON.parse(w.uploadForm);
check(up[1].fieldOptions.values.length === 2 && up[1].fieldOptions.values[0].option.startsWith('1. When Sewage'), 'upload page lists waiting videos');
check(!w.progressForm.includes('<1858>') && w.progressForm.includes('&lt;1858&gt;'), 'titles are escaped in HTML');
check(w.progressForm.includes('478 to go') && w.progressForm.includes('Gemini daily allowance'), 'progress: subs to go + failed run reason');
const other = run('work_out', { 'Open the Studio': { action: LABELS[4] }, 'Read agent state': state, 'Check YouTube channel': ytOther })[0].json;
check(other.route === 'wrongChannel' && other.wrongChannelText.includes('Manzil Vlogs'), 'upload blocked when n8n is logged in to another channel');
const err = run('work_out', { 'Open the Studio': { action: LABELS[7] }, 'Read agent state': state, 'Check YouTube channel': { error: { message: 'Forbidden' } } })[0].json;
check(err.route === 'progress' && err.progressForm.includes('Forbidden'), 'progress still works when YouTube fails');
const empty = run('work_out', { 'Open the Studio': { action: LABELS[5] }, 'Read agent state': real, 'Check YouTube channel': ytOk })[0].json;
check(empty.route === 'nothing', 'remake with nothing waiting → nothing page');

console.log('Trend page');
const scout = { format: 'short', top: [
  { title: 'The day the Thames stank #history #shorts', views: 1200000, viewsPerDay: 240000, ageDays: 5, outlier: 120, url: 'https://youtu.be/abc' },
  { title: 'The day the Thames STANK! #shorts', views: 9, viewsPerDay: 1, outlier: 1, url: 'https://youtu.be/dup' },
  { title: 'Rome <script>alert(1)</script>', views: 50000, viewsPerDay: 9000, outlier: 3.2, url: 'javascript:alert(1)' }] };
const tp = run('trend_page', {}, scout)[0].json;
const tf = JSON.parse(tp.trendForm);
check(tp.picks.length === 2 && tf[1].fieldOptions.values[0].option === '1. The day the Thames stank', 'trends cleaned and de-duplicated');
check(!tf[0].html.includes('<script>') && !tf[0].html.includes('javascript:'), 'trend HTML is safe');
const tnone = JSON.parse(run('trend_page', {}, { top: [] })[0].json.trendForm);
check(tnone.some((f) => f.fieldLabel === 'Topic' && f.requiredField), 'no trends → own topic page');

console.log('Upload check');
const base = run('work_out', { 'Open the Studio': { action: LABELS[4] }, 'Read agent state': state, 'Check YouTube channel': ytOk })[0].json;
const pickVideo = JSON.parse(base.uploadForm)[1].fieldOptions.values[0].option;
const when = JSON.parse(base.uploadForm)[2].fieldOptions.values;
const sch = run('upload_check', { 'Work out the choice': base }, { video: pickVideo, when: when[1].option })[0].json;
const t = Date.parse(sch.publishAt);
const ist = new Date(t + 5.5 * 3600e3);
check(sch.privacy === 'private' && ist.getUTCHours() === 19 && ist.getUTCMinutes() === 0 && t > Date.now() + 40 * 60e3, `scheduled for 7 pm IST: ${sch.whenText}`);
check(sch.status.containsSyntheticMedia === true && sch.status.publishAt === sch.publishAt && sch.notify === false, 'AI label + schedule in status');
check(!sch.tags.includes('a,b') && sch.tags.split(',').includes('a b') && sch.videoAsset === '111' && sch.thumbAsset === '112', 'tags cleaned, file ids passed');
check(!sch.title.includes('<'), 'angle brackets removed from title (YouTube rejects them)');
const pub = run('upload_check', { 'Work out the choice': base }, { 'Which video?': pickVideo, 'When should it go live?': when[0].option })[0].json;
check(pub.privacy === 'public' && !pub.publishAt && pub.notify === true, 'publish now');
const prv = run('upload_check', { 'Work out the choice': base }, { video: JSON.parse(base.uploadForm)[1].fieldOptions.values[1].option, when: when[2].option })[0].json;
check(prv.privacy === 'private' && !prv.publishAt && prv.kind === 'movie' && prv.thumbAsset === '', 'private movie without thumbnail');
let threw = '';
try { run('upload_check', { 'Work out the choice': base }, { video: '7. Gone', when: when[0].option }); } catch (e) { threw = e.message; }
check(threw.includes('no longer waiting'), 'stale choice is refused');

console.log('Write the request');
const req = (route, extra, answer, nodes = {}) => {
  const b = { ...base, route, ...extra };
  return run('write_request', { 'Work out the choice': b, ...nodes }, answer)[0].json;
};
const m1 = req('make', { key: 'story', what: 'Short' }, { pick: '🧠 Strategist picks the most viral one', own: '', style: '👁 POV, you are there' });
check(m1.command.action === 'make' && m1.command.kind === 'story' && m1.command.topic === '' && m1.command.format === 'pov', 'make: strategist pick, POV');
const m2 = req('make', { key: 'movie', what: '15-minute history movie' }, { pick: 'Napoleon was not short', own: '  The   fall of Rome ' });
check(m2.command.action === 'movie' && m2.command.topic === 'The fall of Rome' && !m2.command.format, 'movie: own topic wins');
check(/^commands\/\d{8}-\d{6}-movie-[a-z0-9]+\.json$/.test(m2.file) && JSON.parse(m2.content).topic === 'The fall of Rome', `file name ${m2.file}`);
const tr = req('trend', {}, { trend: '1. The day the Thames stank', angle: 'as a boatman', style: '🎬 Epic movie trailer' }, { 'Trend: build the page': tp });
check(tr.command.topic === 'The day the Thames stank, as a boatman' && tr.command.format === 'trailer', 'trend → make with angle');
const upNodes = { 'Upload: check the choice': sch, 'Upload to YouTube': { uploadId: 'abcDEF12345' }, 'Label it as AI-made': { id: 'abcDEF12345', kind: 'youtube#video' },
  'Post the comment to pin': { error: { message: 'commentsDisabled' } } };
const u = req('upload', {}, { kind: 'youtube#commentThread' }, upNodes);
check(u.command.action === 'uploaded' && u.command.video_id === 'abcDEF12345' && u.command.ai_label === true && u.command.comment_posted === false
  && u.command.thumbnail === false && u.command.publish_at === sch.publishAt, 'upload report: AI label yes, comment failed, no thumbnail run');
check(JSON.parse(u.doneForm)[0].html.includes('studio.youtube.com/video/abcDEF12345') && JSON.parse(u.doneForm)[0].html.includes('Add this comment'), 'upload done page links Studio and the comment chore');
const f1 = req('fix', {}, { video: pickVideo, what: '🗑 Discard it, never upload' });
check(f1.command.action === 'discard' && f1.command.id === '20261127-great-stink', 'discard');
const f2 = req('fix', {}, { 'Which video?': pickVideo, 'What should happen?': '🔄 Remake it with fresh AI shots' });
check(f2.command.action === 'remake', 'remake');
const i1 = req('idea', {}, { idea: 'Dancing plague of 1518', kind: '🔁 Loop Short', angle: '' });
check(i1.command.action === 'idea' && i1.command.kind === 'loop' && !('angle' in i1.command), 'idea for a loop');
const p1 = req('pause', {}, { state: '⏸ Pause the daily videos' });
const p2 = req('pause', {}, { 'Daily videos': '▶️ Resume the daily videos' });
check(p1.command.action === 'pause' && p2.command.action === 'resume', 'pause and resume');
let t2 = '';
try { req('idea', {}, { idea: '   ' }); } catch (e) { t2 = e.message; }
check(t2.includes('empty'), 'empty idea refused');

console.log(fails ? `\n${fails} FAILED` : '\nALL PASSED');
process.exit(fails ? 1 : 0);
