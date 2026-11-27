const CHANNEL = 'UC8eZyrH9ANRhpPFGDLL6OLQ';
const form = $('Open the Studio').first().json || {};
const state = $('Read agent state').first().json || {};
const yt = $('Check YouTube channel').first().json || {};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pick = (o, keys) => {
  for (const k of keys) {
    const v = o ? o[k] : undefined;
    if (v !== undefined && v !== null && String(v).trim() !== '') return v;
  }
  return '';
};
const num = (n) => Number(n || 0).toLocaleString('en-IN');
const IST = 5.5 * 3600e3;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const istText = (iso) => {
  const t = Date.parse(iso || '');
  if (!t) return '';
  const d = new Date(t + IST);
  let h = d.getUTCHours();
  const m = String(d.getUTCMinutes()).padStart(2, '0');
  const ap = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${h}:${m} ${ap}`;
};
const dur = (s) => {
  s = Math.round(Number(s) || 0);
  return s >= 90 ? `${Math.round(s / 60)} min` : `${s} s`;
};
const radio = (label, name, options, def) => ({
  fieldLabel: label, fieldName: name, fieldType: 'radio', requiredField: true, defaultValue: def || options[0],
  fieldOptions: { values: options.map((o) => ({ option: o })) },
});

// 1. What did the owner tap?
const choice = String(pick(form, ['action', 'What do you want to do?']));
const has = (w) => choice.toLowerCase().includes(w);
let key = 'story';
if (has('loop')) key = 'loop';
else if (has('movie')) key = 'movie';
else if (has('viral')) key = 'trend';
else if (has('upload')) key = 'upload';
else if (has('remake') || has('discard')) key = 'fix';
else if (has('idea')) key = 'idea';
else if (has('progress')) key = 'progress';
else if (has('pause') || has('resume')) key = 'pause';

// 2. Which YouTube channel is n8n's login for?
const ch = (yt.items || [])[0] || null;
const channelId = ch ? ch.id : '';
const channelName = ch && ch.snippet ? ch.snippet.title : '';
const st = (ch && ch.statistics) || {};
const subs = ch && !st.hiddenSubscriberCount ? Number(st.subscriberCount || 0) : null;
const channelOk = channelId === CHANNEL;
const ytError = yt.error ? String(yt.error.message || yt.error.description || 'YouTube did not answer') : '';

// 3. Finished videos waiting for the owner
const KIND = { story: 'Short', loop: 'loop Short', movie: 'history movie' };
const waiting = (((state.videos || {}).waiting) || []).filter((v) => v && v.id).map((v, i) => {
  const title = String(v.title || v.topic || 'Untitled').replace(/\s+/g, ' ').trim();
  return {
    n: i + 1, id: v.id, kind: v.kind || 'story', title, topic: v.topic || '', seconds: v.seconds || 0,
    description: v.description || '', tags: v.tags || [], pinned_comment: v.pinned_comment || '',
    release: v.release || null, assets: v.assets || {}, made: v.made || '',
    label: `${i + 1}. ${title.slice(0, 80)} (${KIND[v.kind] || 'video'}${v.seconds ? ', ' + dur(v.seconds) : ''})`,
  };
});

let route = ['story', 'loop', 'movie'].includes(key) ? 'make' : key;
if ((route === 'upload' || route === 'fix') && !waiting.length) route = 'nothing';
if (route === 'upload' && !channelOk) route = 'wrongChannel';

const ag = state.agent || {};
const days = Math.max(0, Math.ceil((Date.parse('2027-02-01T00:00:00+05:30') - Date.now()) / 86400000));

// 4. Make page
const ideaKind = key === 'loop' ? 'loop' : key === 'movie' ? 'movie' : 'story';
const what = { story: 'Short', loop: 'loop Short', movie: '15-minute history movie' }[ideaKind];
const ideas = [];
for (const c of ((state.ideas || {})[ideaKind] || [])) {
  const t = String((c && c.topic) || '').replace(/\s+/g, ' ').trim().slice(0, 150);
  if (t && !ideas.some((x) => x.topic === t)) ideas.push({ topic: t, series: (c && c.series) || '' });
}
const STRATEGIST = '🧠 Strategist picks the most viral one';
const STYLES = ['🧠 Let the strategist choose', '👁 POV, you are there', '🎬 Epic movie trailer', '⏳ Time-traveller vlog'];
const makeFields = [];
const notes = [];
if (ideas.length) {
  notes.push('<p><b>Strategist’s picks right now</b></p><ul>' +
    ideas.slice(0, 5).map((c) => `<li>${esc(c.topic)}${c.series ? ` <i>· ${esc(c.series)}</i>` : ''}</li>`).join('') + '</ul>');
}
if (!ag.paid_key) {
  notes.push('<p><i>Free AI plan: if Google’s free daily allowance is used up, Telegram tells you and it works again after 1:30 pm IST.</i></p>');
}
if (notes.length) makeFields.push({ fieldType: 'html', html: notes.join('') });
makeFields.push({
  fieldLabel: 'Topic', fieldName: 'pick', fieldType: 'dropdown', requiredField: true, defaultValue: STRATEGIST,
  fieldOptions: { values: [STRATEGIST, ...ideas.slice(0, 6).map((c) => c.topic)].map((o) => ({ option: o })) },
});
makeFields.push({
  fieldLabel: '…or type your own topic', fieldName: 'own', fieldType: 'text', requiredField: false,
  placeholder: 'e.g. Why the Great Wall was never one wall',
});
if (ideaKind !== 'movie') makeFields.push(radio('Style', 'style', STYLES));

// 5. Upload, fix and pause pages
const videoField = {
  fieldLabel: 'Which video?', fieldName: 'video', fieldType: 'dropdown', requiredField: true,
  defaultValue: waiting.length ? waiting[0].label : '',
  fieldOptions: { values: waiting.map((v) => ({ option: v.label })) },
};
const WHEN = ['🚀 Publish now', '🗓 Schedule for the best time (Shorts 7 pm · loops 12:30 pm · movies 6:30 pm IST)', '🔒 Upload as private, I’ll publish it myself'];
const uploadFields = [
  { fieldType: 'html', html: '<p>Your agent already wrote the SEO title, description, tags and the comment to pin. You check them on the next page before anything goes to YouTube.</p>' },
  videoField,
  radio('When should it go live?', 'when', WHEN, WHEN[1]),
];
const FIX = ['🔄 Remake it with fresh AI shots', '🗑 Discard it, never upload'];
const fixFields = [videoField, radio('What should happen?', 'what', FIX)];
const PAUSE = ['⏸ Pause the daily videos', '▶️ Resume the daily videos'];
const pauseFields = [
  { fieldType: 'html', html: `<p>Daily videos are <b>${ag.paused ? 'paused' : 'on'}</b> right now${ag.schedule && ag.schedule.shorts ? ` (${esc(ag.schedule.shorts)})` : ''}.</p>` },
  radio('Daily videos', 'state', PAUSE, ag.paused ? PAUSE[1] : PAUSE[0]),
];

// 6. Progress page
const rules = state.rules || {};
const ypp = rules.before || { subs: 1000, watch_hours_12m: 4000, shorts_views_90d: 10000000 };
const fan = rules.fan_funding || { subs: 500, uploads_90d: 3, watch_hours_12m: 3000, shorts_views_90d: 3000000 };
const p = [];
p.push(`<h3>⏳ ${days} days to 1 Feb 2027</h3>`);
if (channelOk) {
  p.push(`<p><b>${esc(channelName)}</b><br>${subs === null ? 'Subscriber count hidden' : num(subs) + ' subscribers'} · ${num(st.viewCount)} views · ${num(st.videoCount)} videos</p>`);
} else {
  p.push(`<p>⚠️ ${esc(ytError || `n8n’s YouTube login is for “${channelName || 'another channel'}”, not History with Me.`)}</p>`);
}
const need = subs === null ? null : Math.max(0, ypp.subs - subs);
p.push('<p><b>Full monetization (until 31 Jan 2027)</b><br>' +
  `Subscribers: ${subs === null ? '?' : num(subs)} of ${num(ypp.subs)}` +
  (need === null ? '' : need > 0 ? `, ${num(need)} to go (about ${Math.ceil(need / Math.max(days, 1))} a day)` : ' ✅') +
  `<br>Plus ${num(ypp.watch_hours_12m)} public watch hours in 12 months, or ${num(ypp.shorts_views_90d)} Shorts views in 90 days.</p>`);
p.push('<p><b>Fan funding (memberships, Super Thanks)</b><br>' +
  `Subscribers: ${subs === null ? '?' : num(subs)} of ${num(fan.subs)}${subs !== null && subs >= fan.subs ? ' ✅' : ''}` +
  `<br>Plus ${fan.uploads_90d} public uploads in 90 days, and ${num(fan.watch_hours_12m)} watch hours or ${num(fan.shorts_views_90d)} Shorts views.</p>`);
p.push('<p><i>Watch hours and 90-day Shorts views are in YouTube Studio → Earn.</i></p>');
const b = state.budget || {};
p.push(`<p><b>Your agent</b><br>Daily videos: ${ag.paused ? '⏸ paused' : '▶️ on'} · Free AI video: ${ag.free_video ? 'on' : 'off'} · Paid Google key: ${ag.paid_key ? 'added' : 'not added'}` +
  `<br>Paid AI this month: $${Number(b.spent || 0).toFixed(2)} of $${Number(b.cap || 10).toFixed(0)}</p>`);
const sch = ag.schedule || {};
if (sch.shorts || sch.movies) p.push(`<p><b>Schedule</b><br>Shorts: ${esc(sch.shorts || '')}<br>Movies: ${esc(sch.movies || '')}</p>`);
p.push(`<p><b>Waiting for you</b><br>${waiting.length ? waiting.map((v) => esc(v.title)).join('<br>') : 'Nothing right now.'}</p>`);
const runs = Object.entries(state.runs || {}).map(([k, r]) =>
  `${r.ok ? '✅' : '❌'} ${esc(k)}, ${esc(istText(r.at))}${r.title ? ': ' + esc(r.title) : ''}${!r.ok && r.error ? ' (' + esc(String(r.error).slice(0, 140)) + ')' : ''}`);
if (runs.length) p.push(`<p><b>Latest runs (IST)</b><br>${runs.join('<br>')}</p>`);
const recent = (((state.videos || {}).recent) || []).filter((v) => v && v.video_id).slice(0, 5);
if (recent.length) {
  p.push('<p><b>Recently uploaded</b><br>' + recent.map((v) => `<a href="https://youtu.be/${esc(v.video_id)}">${esc(v.title)}</a>`).join('<br>') + '</p>');
}

return [{
  json: {
    route, key, choice, what, channelOk, channelId, channelName, subs, waiting, paused: !!ag.paused, daysLeft: days,
    makeTitle: `${key === 'movie' ? '🎞' : key === 'loop' ? '🔁' : '🎬'} Make a ${what}`,
    makeForm: JSON.stringify(makeFields),
    uploadForm: JSON.stringify(uploadFields),
    fixForm: JSON.stringify(fixFields),
    pauseForm: JSON.stringify(pauseFields),
    progressForm: JSON.stringify([{ fieldType: 'html', html: p.join('') }]),
    nothingText: 'No finished video is waiting for you. New Shorts arrive every day at 2:11 pm IST, or make one now from the Studio.',
    wrongChannelText: ytError
      ? `n8n couldn’t check your YouTube login (${ytError.slice(0, 160)}). Open n8n → Credentials → YouTube account and reconnect it.`
      : `n8n’s YouTube login is for “${channelName || 'another channel'}”, not History with Me. Open n8n → Credentials → YouTube account, reconnect it and choose the History with Me channel.`,
  },
}];
