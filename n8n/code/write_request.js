const base = $('Work out the choice').first().json;
const route = base.route;
const a = $input.first().json || {};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pick = (o, keys) => {
  for (const k of keys) {
    const v = o ? o[k] : undefined;
    if (v !== undefined && v !== null && String(v).trim() !== '') return v;
  }
  return '';
};
const clean = (s) => String(s || '').replace(/\s+/g, ' ').trim().slice(0, 200);
const styleFormat = (s) => {
  s = String(s || '');
  if (s.includes('POV')) return 'pov';
  if (s.includes('trailer')) return 'trailer';
  if (s.includes('Time')) return 'timetraveler';
  return '';
};
const STYLE_NAME = { pov: 'POV', trailer: 'movie-trailer', timetraveler: 'time-traveller' };
const video = (answer) => {
  const choice = String(pick(answer, ['video', 'Which video?']));
  const v = (base.waiting || [])[parseInt(choice, 10) - 1];
  if (!v || !choice.startsWith(`${v.n}. `)) throw new Error('That video is no longer waiting for you. Open the Studio again.');
  return v;
};
const TELEGRAM = '<p>📲 Your agent confirms on Telegram in a minute.</p>';

let command;
let title;
let html;
let details;

if (route === 'make') {
  const chosen = String(pick(a, ['pick', 'Topic']));
  const own = clean(pick(a, ['own', '…or type your own topic']));
  const topic = own || (chosen && !chosen.startsWith('🧠') ? clean(chosen) : '');
  const kind = ['story', 'loop', 'movie'].includes(base.key) ? base.key : 'story';
  const fmt = kind === 'movie' ? '' : styleFormat(pick(a, ['style', 'Style']));
  command = kind === 'movie' ? { action: 'movie', kind: 'movie', topic } : { action: 'make', kind, topic };
  if (fmt) command.format = fmt;
  title = `${kind === 'movie' ? '🎞' : '🎬'} Your ${base.what} is on its way`;
  html = `<p>Your agent is making a ${esc(base.what)}${topic ? ` about <b>${esc(topic)}</b>` : ' on the strategist’s most viral pick'}` +
    `${fmt ? ` in ${STYLE_NAME[fmt]} style` : ''}.</p>` +
    `<p>📲 It arrives on Telegram in about ${kind === 'movie' ? 40 : 10} minutes. Then open the Studio and tap <b>Upload a finished video</b>.</p>`;
  details = `${kind}: ${topic || 'strategist pick'}${fmt ? ' (' + fmt + ')' : ''}`;
} else if (route === 'trend') {
  const page = $('Trend: build the page').first().json;
  const choice = String(pick(a, ['trend', 'Which trend?']));
  const p = (page.picks || [])[parseInt(choice, 10) - 1];
  const angle = clean(pick(a, ['angle', 'Your angle (optional)', 'Topic']));
  let topic = p ? p.title : angle;
  if (p && angle) topic = `${p.title}, ${angle}`;
  topic = clean(topic);
  if (!topic) throw new Error('No trend or topic was chosen.');
  const fmt = styleFormat(pick(a, ['style', 'Style']));
  command = { action: 'make', kind: 'story', topic };
  if (fmt) command.format = fmt;
  title = '🔥 Making it while it’s hot';
  html = `<p>Your agent is making an original Short about <b>${esc(topic)}</b>${fmt ? ` in ${STYLE_NAME[fmt]} style` : ''}.</p>` +
    '<p>📲 It arrives on Telegram in about 10 minutes. Then open the Studio and tap <b>Upload a finished video</b>.</p>';
  details = `trend: ${topic}`;
} else if (route === 'upload') {
  const up = $('Upload: check the choice').first().json;
  const res = $('Upload to YouTube').first().json || {};
  const vid = String(res.uploadId || res.id || '');
  const ok = (name) => {
    try {
      const j = $(name).first().json;
      return !!(j && !j.error && (j.id || j.kind));
    } catch (e) {
      return false;
    }
  };
  const ai = ok('Label it as AI-made');
  const posted = ok('Post the comment to pin');
  const thumb = ok('Set the thumbnail');
  command = {
    action: 'uploaded', id: up.id, via: 'n8n', video_id: vid, privacy: up.privacy, publish_at: up.publishAt || '',
    ai_label: ai, comment_posted: posted, thumbnail: thumb,
  };
  const todo = [];
  todo.push(ai ? 'Labelled as AI-made ✔' : '⚠️ In YouTube Studio, set <b>Altered or synthetic content</b> to Yes');
  if (posted) todo.push('Comment posted. Pin it in YouTube Studio → Comments (YouTube doesn’t let apps pin)');
  else if (up.comment) todo.push(`Add this comment and pin it: <i>${esc(up.comment)}</i>`);
  if (thumb) todo.push('Thumbnail set ✔');
  title = '✅ Uploaded to YouTube';
  html = `<p><b>${esc(up.title)}</b> ${esc(up.whenText)}.</p>` +
    (vid ? `<p><a href="https://youtu.be/${esc(vid)}">Open the video</a> · <a href="https://studio.youtube.com/video/${esc(vid)}/edit">Open it in YouTube Studio</a></p>` : '') +
    `<ul>${todo.map((t) => `<li>${t}</li>`).join('')}</ul>`;
  details = `${up.title} → ${vid || 'no id'} (${up.publishAt || up.privacy})`;
} else if (route === 'fix') {
  const v = video(a);
  const remake = String(pick(a, ['what', 'What should happen?'])).includes('Remake');
  command = { action: remake ? 'remake' : 'discard', id: v.id };
  title = remake ? '🔄 Remaking it' : '🗑 Discarded';
  html = remake
    ? `<p>Your agent drops the old version of <b>${esc(v.title)}</b> and makes a fresh one with new AI shots. It arrives on Telegram in about ${v.kind === 'movie' ? 40 : 10} minutes.</p>`
    : `<p><b>${esc(v.title)}</b> is discarded. Nothing goes to YouTube.</p>${TELEGRAM}`;
  details = `${command.action}: ${v.title}`;
} else if (route === 'idea') {
  const topic = clean(pick(a, ['idea', 'Your idea']));
  if (!topic) throw new Error('The idea was empty.');
  const forWhat = String(pick(a, ['kind', 'Make it as'])).toLowerCase();
  const kind = forWhat.includes('loop') ? 'loop' : forWhat.includes('movie') ? 'movie' : 'story';
  const angle = clean(pick(a, ['angle', 'Hook or angle (optional)']));
  command = { action: 'idea', kind, topic };
  if (angle) command.angle = angle;
  title = '💡 Idea saved';
  html = `<p><b>${esc(topic)}</b> is saved. The strategist uses it for an upcoming ${kind === 'movie' ? 'movie' : kind === 'loop' ? 'loop Short' : 'Short'}.</p>${TELEGRAM}`;
  details = `idea (${kind}): ${topic}`;
} else if (route === 'pause') {
  const pause = String(pick(a, ['state', 'Daily videos'])).includes('Pause');
  command = { action: pause ? 'pause' : 'resume' };
  title = pause ? '⏸ Daily videos paused' : '▶️ Daily videos back on';
  html = pause
    ? '<p>Your agent stops making the daily videos until you resume them. You can still make videos from the Studio.</p>'
    : '<p>Your agent makes the daily Short again (2:11 pm IST) and movies on Wednesdays and Sundays.</p>';
  html += TELEGRAM;
  details = command.action;
} else {
  throw new Error(`Nothing to send to your agent for “${route}”.`);
}

const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, '').replace('T', '-');
const file = `commands/${stamp}-${command.action}-${Math.random().toString(36).slice(2, 8)}.json`;
const commitMessage = `Studio (n8n): ${command.action}${command.topic ? ' - ' + command.topic.slice(0, 60) : ''}`;
return [{
  json: {
    command, file, content: JSON.stringify(command, null, 2) + '\n', commitMessage,
    doneTitle: title, doneForm: JSON.stringify([{ fieldType: 'html', html }]), logAction: command.action, logDetails: clean(details),
  },
}];
