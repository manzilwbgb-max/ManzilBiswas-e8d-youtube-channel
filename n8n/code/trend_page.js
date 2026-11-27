const res = $input.first().json || {};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const short = (n) => {
  n = Number(n) || 0;
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1e3) return Math.round(n / 1e3) + 'K';
  return String(Math.round(n));
};
const clean = (t) => String(t || '').replace(/#[\p{L}\p{N}_]+/gu, '').replace(/[|]+/g, ' ').replace(/\s+/g, ' ').trim();

const seen = new Set();
const picks = [];
for (const r of (res.top || [])) {
  const title = clean(r && r.title);
  const k = title.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 40);
  if (title.length < 8 || seen.has(k)) continue;
  seen.add(k);
  picks.push({
    title, views: r.views || 0, viewsPerDay: r.viewsPerDay || 0, ageDays: r.ageDays || 0, outlier: r.outlier || 0,
    channel: r.channel || '', url: /^https:\/\/(www\.)?youtu(\.be|be\.com)\//.test(String(r.url || '')) ? String(r.url) : '',
  });
  if (picks.length >= 8) break;
}

const STYLES = ['🧠 Let the strategist choose', '👁 POV, you are there', '🎬 Epic movie trailer', '⏳ Time-traveller vlog'];
const style = {
  fieldLabel: 'Style', fieldName: 'style', fieldType: 'radio', requiredField: true, defaultValue: STYLES[0],
  fieldOptions: { values: STYLES.map((o) => ({ option: o })) },
};
let fields;
if (picks.length) {
  const list = picks.map((p) => `<li><b>${esc(p.title)}</b><br>${short(p.viewsPerDay)} views a day · ${p.outlier}× its channel’s size` +
    `${p.url ? ` · <a href="${esc(p.url)}">watch</a>` : ''}</li>`).join('');
  fields = [
    { fieldType: 'html', html: `<p>History Shorts taking off on YouTube right now:</p><ol>${list}</ol><p>Pick one. Your agent makes its own original Short on that subject, with a fresh hook. Never a copy.</p>` },
    {
      fieldLabel: 'Which trend?', fieldName: 'trend', fieldType: 'dropdown', requiredField: true,
      defaultValue: `1. ${picks[0].title.slice(0, 90)}`,
      fieldOptions: { values: picks.map((p, i) => ({ option: `${i + 1}. ${p.title.slice(0, 90)}` })) },
    },
    { fieldLabel: 'Your angle (optional)', fieldName: 'angle', fieldType: 'text', requiredField: false, placeholder: 'e.g. Tell it as a soldier who was there' },
    style,
  ];
} else {
  fields = [
    { fieldType: 'html', html: '<p>YouTube didn’t return rising history Shorts just now (its daily search allowance may be used up). Type a topic and your agent makes it anyway.</p>' },
    { fieldLabel: 'Topic', fieldName: 'angle', fieldType: 'text', requiredField: true, placeholder: 'e.g. The emu war of 1932' },
    style,
  ];
}
return [{ json: { picks, scannedAt: res.scannedAt || '', trendForm: JSON.stringify(fields) } }];
