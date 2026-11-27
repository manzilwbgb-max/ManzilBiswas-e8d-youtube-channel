const base = $('Work out the choice').first().json;
const a = $input.first().json || {};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pick = (o, keys) => {
  for (const k of keys) {
    const v = o ? o[k] : undefined;
    if (v !== undefined && v !== null && String(v).trim() !== '') return v;
  }
  return '';
};
const IST = 5.5 * 3600e3;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const istText = (iso) => {
  const d = new Date(Date.parse(iso) + IST);
  let h = d.getUTCHours();
  const m = String(d.getUTCMinutes()).padStart(2, '0');
  const ap = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${h}:${m} ${ap}`;
};
const nextSlot = (hh, mm) => {
  const now = Date.now();
  const ist = new Date(now + IST);
  let t = Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate(), hh, mm) - IST;
  if (t < now + 45 * 60e3) t += 86400e3;
  return new Date(t).toISOString();
};

const choice = String(pick(a, ['video', 'Which video?']));
const v = (base.waiting || [])[parseInt(choice, 10) - 1];
if (!v || !choice.startsWith(`${v.n}. `)) throw new Error('That video is no longer waiting for you. Open the Studio again.');
const assets = v.assets || {};
if (!assets['video.mp4']) throw new Error('The video file is missing on GitHub. Use “Remake or discard” to make it again.');

const when = String(pick(a, ['when', 'When should it go live?']));
const slot = { story: [19, 0], loop: [12, 30], movie: [18, 30] }[v.kind] || [19, 0];
let privacy = 'public';
let publishAt = '';
if (when.includes('Schedule')) {
  privacy = 'private';
  publishAt = nextSlot(slot[0], slot[1]);
} else if (when.includes('private')) {
  privacy = 'private';
}

const title = String(v.title || 'History with Me').replace(/[<>]/g, '').replace(/\s+/g, ' ').trim().slice(0, 100);
const description = String(v.description || '').replace(/[<>]/g, '').slice(0, 4900);
const tags = [];
let total = 0;
for (const t of (v.tags || [])) {
  const c = String(t).replace(/[<>,"]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 60);
  if (!c || tags.includes(c)) continue;
  const cost = c.length + (c.includes(' ') ? 2 : 0) + 1;
  if (total + cost > 480) break;
  tags.push(c);
  total += cost;
}
const comment = String(v.pinned_comment || '').trim().slice(0, 1000);
const status = {
  privacyStatus: privacy, embeddable: true, license: 'youtube', publicStatsViewable: true,
  selfDeclaredMadeForKids: false, containsSyntheticMedia: true,
};
if (publishAt) status.publishAt = publishAt;
const whenText = publishAt ? `goes live ${istText(publishAt)} IST`
  : privacy === 'public' ? 'goes live right away' : 'uploads as private, you publish it later in YouTube Studio';

const shownDesc = esc(description.length > 700 ? description.slice(0, 700) + '…' : description).replace(/\n/g, '<br>');
const html = `<p><b>${esc(title)}</b><br>It ${esc(whenText)}.</p>` +
  (shownDesc ? `<p><b>Description</b><br>${shownDesc}</p>` : '') +
  (tags.length ? `<p><b>Tags</b><br>${esc(tags.join(', '))}</p>` : '') +
  (comment ? `<p><b>Comment to pin</b><br>${esc(comment)}</p>` : '') +
  '<p>✔ Education category · Not made for kids · Labelled as AI-made (altered or synthetic content), as YouTube requires.</p>';

return [{
  json: {
    id: v.id, kind: v.kind, title, description, tags: tags.join(','), privacy, publishAt, notify: privacy === 'public' && !publishAt,
    status, videoAsset: String(assets['video.mp4']), thumbAsset: assets['thumbnail.jpg'] ? String(assets['thumbnail.jpg']) : '',
    comment, whenText, confirmForm: JSON.stringify([{ fieldType: 'html', html }]),
  },
}];
