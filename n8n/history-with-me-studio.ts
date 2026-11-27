import { workflow, node, trigger, sticky, newCredential, ifElse, switchCase, expr } from '@n8n/workflow-sdk';

const REPO_API = 'https://api.github.com/repos/manzilwbgb-max/ManzilBiswas-e8d-youtube-channel';
const STUDIO_URL = 'https://manzil1234.app.n8n.cloud/form/history-with-me-studio';
const githubLogin = newCredential('GitHub (History with Me)');
const youtubeLogin = { id: 'sHtQA2FA2lSr7b6u', name: 'YouTube account' };
const studioCss = ':root{--font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;--color-background:#0e1014;--color-card-bg:#161a21;--color-card-border:#2a303b;--color-card-shadow:rgba(0,0,0,.35);--color-header:#f6efe0;--color-header-subtext:#b9b2a2;--color-label:#efe7d6;--color-input-border:#3a414e;--color-input-text:#f6efe0;--color-focus-border:#f2b134;--color-submit-btn-bg:#f2b134;--color-submit-btn-text:#14110a;--color-required:#f2b134;--color-html-text:#d9d2c3;--color-html-link:#f2b134;--color-link:#b9b2a2;--color-clear-button-bg:#3a414e;--font-size-label:16px;--font-size-input:16px;--font-size-header:24px;--font-size-paragraph:15px;--font-size-html-h3:18px;--border-radius-card:14px;--border-radius-input:10px;--border-radius-button:12px;--submit-btn-height:54px}input,textarea,select{background:#0e1014!important;color:#f6efe0!important}';
const routeOptions = { caseSensitive: true, leftValue: '', typeValidation: 'strict' };

const openStudio = trigger({
  type: 'n8n-nodes-base.formTrigger',
  version: 2.7,
  config: {
    name: 'Open the Studio',
    parameters: {
      authentication: 'n8nUserAuth',
      requireExecuteAccess: true,
      formTitle: '🎬 History with Me Studio',
      formDescription: '<p>Your private control room. Pick what to do: your agent on GitHub makes it, and you upload with one tap.</p>',
      formFields: {
        values: [
          {
            fieldLabel: 'What do you want to do?',
            fieldName: 'action',
            fieldType: 'radio',
            requiredField: true,
            defaultValue: '🎬 Make a Short',
            fieldOptions: {
              values: [
                { option: '🎬 Make a Short' },
                { option: '🔁 Make a loop Short' },
                { option: '🎞 Make a 15-minute history movie' },
                { option: '🔥 Find a viral topic and make it' },
                { option: '⬆️ Upload a finished video to YouTube' },
                { option: '🔄 Remake or 🗑 discard a finished video' },
                { option: '💡 Save an idea for later' },
                { option: '📊 See my progress' },
                { option: '⏯ Pause or resume daily videos' },
              ],
            },
          },
        ],
      },
      options: {
        appendAttribution: false,
        buttonLabel: 'Next ›',
        path: 'history-with-me-studio',
        ignoreBots: true,
        customCss: studioCss,
      },
    },
  },
  output: [{ action: '🎬 Make a Short', submittedAt: '2026-11-27T13:45:00.000+05:30', formMode: 'production' }],
});

const checkChannel = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Check YouTube channel',
    onError: 'continueRegularOutput',
    parameters: {
      method: 'GET',
      url: 'https://www.googleapis.com/youtube/v3/channels',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'youTubeOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: { parameters: [{ name: 'part', value: 'snippet,statistics' }, { name: 'mine', value: 'true' }] },
      options: { timeout: 30000 },
    },
    credentials: { youTubeOAuth2Api: youtubeLogin },
  },
  output: [{ items: [{ id: 'UC8eZyrH9ANRhpPFGDLL6OLQ', snippet: { title: 'History with Me' }, statistics: { subscriberCount: '522', viewCount: '43951', videoCount: '12' } }] }],
});

const readState = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Read agent state',
    onError: 'continueErrorOutput',
    parameters: {
      method: 'GET',
      url: REPO_API + '/contents/state/app.json?ref=main',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'githubApi',
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: { parameters: [{ name: 'Accept', value: 'application/vnd.github.raw+json' }, { name: 'X-GitHub-Api-Version', value: '2022-11-28' }] },
      options: { response: { response: { responseFormat: 'json' } }, timeout: 30000 },
    },
    credentials: { githubApi: githubLogin },
  },
  output: [{ deadline: '2027-02-01', agent: { paused: false, paid_key: false, free_video: true }, budget: { spent: 0, cap: 10 }, runs: {}, videos: { waiting: [], recent: [] }, ideas: { story: [{ topic: 'The Great Stink' }] } }],
});

const workOut = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Work out the choice',
    parameters: { mode: 'runOnceForAllItems', jsCode: "const CHANNEL = 'UC8eZyrH9ANRhpPFGDLL6OLQ';\nconst form = $('Open the Studio').first().json || {};\nconst state = $('Read agent state').first().json || {};\nconst yt = $('Check YouTube channel').first().json || {};\n\nconst esc = (s) => String(s ?? '').replace(/[&<>\"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' }[c]));\nconst pick = (o, keys) => {\n  for (const k of keys) {\n    const v = o ? o[k] : undefined;\n    if (v !== undefined && v !== null && String(v).trim() !== '') return v;\n  }\n  return '';\n};\nconst num = (n) => Number(n || 0).toLocaleString('en-IN');\nconst IST = 5.5 * 3600e3;\nconst MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];\nconst istText = (iso) => {\n  const t = Date.parse(iso || '');\n  if (!t) return '';\n  const d = new Date(t + IST);\n  let h = d.getUTCHours();\n  const m = String(d.getUTCMinutes()).padStart(2, '0');\n  const ap = h >= 12 ? 'pm' : 'am';\n  h = h % 12 || 12;\n  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${h}:${m} ${ap}`;\n};\nconst dur = (s) => {\n  s = Math.round(Number(s) || 0);\n  return s >= 90 ? `${Math.round(s / 60)} min` : `${s} s`;\n};\nconst radio = (label, name, options, def) => ({\n  fieldLabel: label, fieldName: name, fieldType: 'radio', requiredField: true, defaultValue: def || options[0],\n  fieldOptions: { values: options.map((o) => ({ option: o })) },\n});\n\n// 1. What did the owner tap?\nconst choice = String(pick(form, ['action', 'What do you want to do?']));\nconst has = (w) => choice.toLowerCase().includes(w);\nlet key = 'story';\nif (has('loop')) key = 'loop';\nelse if (has('movie')) key = 'movie';\nelse if (has('viral')) key = 'trend';\nelse if (has('upload')) key = 'upload';\nelse if (has('remake') || has('discard')) key = 'fix';\nelse if (has('idea')) key = 'idea';\nelse if (has('progress')) key = 'progress';\nelse if (has('pause') || has('resume')) key = 'pause';\n\n// 2. Which YouTube channel is n8n's login for?\nconst ch = (yt.items || [])[0] || null;\nconst channelId = ch ? ch.id : '';\nconst channelName = ch && ch.snippet ? ch.snippet.title : '';\nconst st = (ch && ch.statistics) || {};\nconst subs = ch && !st.hiddenSubscriberCount ? Number(st.subscriberCount || 0) : null;\nconst channelOk = channelId === CHANNEL;\nconst ytError = yt.error ? String(yt.error.message || yt.error.description || 'YouTube did not answer') : '';\n\n// 3. Finished videos waiting for the owner\nconst KIND = { story: 'Short', loop: 'loop Short', movie: 'history movie' };\nconst waiting = (((state.videos || {}).waiting) || []).filter((v) => v && v.id).map((v, i) => {\n  const title = String(v.title || v.topic || 'Untitled').replace(/\\s+/g, ' ').trim();\n  return {\n    n: i + 1, id: v.id, kind: v.kind || 'story', title, topic: v.topic || '', seconds: v.seconds || 0,\n    description: v.description || '', tags: v.tags || [], pinned_comment: v.pinned_comment || '',\n    release: v.release || null, assets: v.assets || {}, made: v.made || '',\n    label: `${i + 1}. ${title.slice(0, 80)} (${KIND[v.kind] || 'video'}${v.seconds ? ', ' + dur(v.seconds) : ''})`,\n  };\n});\n\nlet route = ['story', 'loop', 'movie'].includes(key) ? 'make' : key;\nif ((route === 'upload' || route === 'fix') && !waiting.length) route = 'nothing';\nif (route === 'upload' && !channelOk) route = 'wrongChannel';\n\nconst ag = state.agent || {};\nconst days = Math.max(0, Math.ceil((Date.parse('2027-02-01T00:00:00+05:30') - Date.now()) / 86400000));\n\n// 4. Make page\nconst ideaKind = key === 'loop' ? 'loop' : key === 'movie' ? 'movie' : 'story';\nconst what = { story: 'Short', loop: 'loop Short', movie: '15-minute history movie' }[ideaKind];\nconst ideas = [];\nfor (const c of ((state.ideas || {})[ideaKind] || [])) {\n  const t = String((c && c.topic) || '').replace(/\\s+/g, ' ').trim().slice(0, 150);\n  if (t && !ideas.some((x) => x.topic === t)) ideas.push({ topic: t, series: (c && c.series) || '' });\n}\nconst STRATEGIST = '🧠 Strategist picks the most viral one';\nconst STYLES = ['🧠 Let the strategist choose', '👁 POV, you are there', '🎬 Epic movie trailer', '⏳ Time-traveller vlog'];\nconst makeFields = [];\nconst notes = [];\nif (ideas.length) {\n  notes.push('<p><b>Strategist’s picks right now</b></p><ul>' +\n    ideas.slice(0, 5).map((c) => `<li>${esc(c.topic)}${c.series ? ` <i>· ${esc(c.series)}</i>` : ''}</li>`).join('') + '</ul>');\n}\nif (!ag.paid_key) {\n  notes.push('<p><i>Free AI plan: if Google’s free daily allowance is used up, Telegram tells you and it works again after 1:30 pm IST.</i></p>');\n}\nif (notes.length) makeFields.push({ fieldType: 'html', html: notes.join('') });\nmakeFields.push({\n  fieldLabel: 'Topic', fieldName: 'pick', fieldType: 'dropdown', requiredField: true, defaultValue: STRATEGIST,\n  fieldOptions: { values: [STRATEGIST, ...ideas.slice(0, 6).map((c) => c.topic)].map((o) => ({ option: o })) },\n});\nmakeFields.push({\n  fieldLabel: '…or type your own topic', fieldName: 'own', fieldType: 'text', requiredField: false,\n  placeholder: 'e.g. Why the Great Wall was never one wall',\n});\nif (ideaKind !== 'movie') makeFields.push(radio('Style', 'style', STYLES));\n\n// 5. Upload, fix and pause pages\nconst videoField = {\n  fieldLabel: 'Which video?', fieldName: 'video', fieldType: 'dropdown', requiredField: true,\n  defaultValue: waiting.length ? waiting[0].label : '',\n  fieldOptions: { values: waiting.map((v) => ({ option: v.label })) },\n};\nconst WHEN = ['🚀 Publish now', '🗓 Schedule for the best time (Shorts 7 pm · loops 12:30 pm · movies 6:30 pm IST)', '🔒 Upload as private, I’ll publish it myself'];\nconst uploadFields = [\n  { fieldType: 'html', html: '<p>Your agent already wrote the SEO title, description, tags and the comment to pin. You check them on the next page before anything goes to YouTube.</p>' },\n  videoField,\n  radio('When should it go live?', 'when', WHEN, WHEN[1]),\n];\nconst FIX = ['🔄 Remake it with fresh AI shots', '🗑 Discard it, never upload'];\nconst fixFields = [videoField, radio('What should happen?', 'what', FIX)];\nconst PAUSE = ['⏸ Pause the daily videos', '▶️ Resume the daily videos'];\nconst pauseFields = [\n  { fieldType: 'html', html: `<p>Daily videos are <b>${ag.paused ? 'paused' : 'on'}</b> right now${ag.schedule && ag.schedule.shorts ? ` (${esc(ag.schedule.shorts)})` : ''}.</p>` },\n  radio('Daily videos', 'state', PAUSE, ag.paused ? PAUSE[1] : PAUSE[0]),\n];\n\n// 6. Progress page\nconst rules = state.rules || {};\nconst ypp = rules.before || { subs: 1000, watch_hours_12m: 4000, shorts_views_90d: 10000000 };\nconst fan = rules.fan_funding || { subs: 500, uploads_90d: 3, watch_hours_12m: 3000, shorts_views_90d: 3000000 };\nconst p = [];\np.push(`<h3>⏳ ${days} days to 1 Feb 2027</h3>`);\nif (channelOk) {\n  p.push(`<p><b>${esc(channelName)}</b><br>${subs === null ? 'Subscriber count hidden' : num(subs) + ' subscribers'} · ${num(st.viewCount)} views · ${num(st.videoCount)} videos</p>`);\n} else {\n  p.push(`<p>⚠️ ${esc(ytError || `n8n’s YouTube login is for “${channelName || 'another channel'}”, not History with Me.`)}</p>`);\n}\nconst need = subs === null ? null : Math.max(0, ypp.subs - subs);\np.push('<p><b>Full monetization (until 31 Jan 2027)</b><br>' +\n  `Subscribers: ${subs === null ? '?' : num(subs)} of ${num(ypp.subs)}` +\n  (need === null ? '' : need > 0 ? `, ${num(need)} to go (about ${Math.ceil(need / Math.max(days, 1))} a day)` : ' ✅') +\n  `<br>Plus ${num(ypp.watch_hours_12m)} public watch hours in 12 months, or ${num(ypp.shorts_views_90d)} Shorts views in 90 days.</p>`);\np.push('<p><b>Fan funding (memberships, Super Thanks)</b><br>' +\n  `Subscribers: ${subs === null ? '?' : num(subs)} of ${num(fan.subs)}${subs !== null && subs >= fan.subs ? ' ✅' : ''}` +\n  `<br>Plus ${fan.uploads_90d} public uploads in 90 days, and ${num(fan.watch_hours_12m)} watch hours or ${num(fan.shorts_views_90d)} Shorts views.</p>`);\np.push('<p><i>Watch hours and 90-day Shorts views are in YouTube Studio → Earn.</i></p>');\nconst b = state.budget || {};\np.push(`<p><b>Your agent</b><br>Daily videos: ${ag.paused ? '⏸ paused' : '▶️ on'} · Free AI video: ${ag.free_video ? 'on' : 'off'} · Paid Google key: ${ag.paid_key ? 'added' : 'not added'}` +\n  `<br>Paid AI this month: $${Number(b.spent || 0).toFixed(2)} of $${Number(b.cap || 10).toFixed(0)}</p>`);\nconst sch = ag.schedule || {};\nif (sch.shorts || sch.movies) p.push(`<p><b>Schedule</b><br>Shorts: ${esc(sch.shorts || '')}<br>Movies: ${esc(sch.movies || '')}</p>`);\np.push(`<p><b>Waiting for you</b><br>${waiting.length ? waiting.map((v) => esc(v.title)).join('<br>') : 'Nothing right now.'}</p>`);\nconst runs = Object.entries(state.runs || {}).map(([k, r]) =>\n  `${r.ok ? '✅' : '❌'} ${esc(k)}, ${esc(istText(r.at))}${r.title ? ': ' + esc(r.title) : ''}${!r.ok && r.error ? ' (' + esc(String(r.error).slice(0, 140)) + ')' : ''}`);\nif (runs.length) p.push(`<p><b>Latest runs (IST)</b><br>${runs.join('<br>')}</p>`);\nconst recent = (((state.videos || {}).recent) || []).filter((v) => v && v.video_id).slice(0, 5);\nif (recent.length) {\n  p.push('<p><b>Recently uploaded</b><br>' + recent.map((v) => `<a href=\"https://youtu.be/${esc(v.video_id)}\">${esc(v.title)}</a>`).join('<br>') + '</p>');\n}\n\nreturn [{\n  json: {\n    route, key, choice, what, channelOk, channelId, channelName, subs, waiting, paused: !!ag.paused, daysLeft: days,\n    makeTitle: `${key === 'movie' ? '🎞' : key === 'loop' ? '🔁' : '🎬'} Make a ${what}`,\n    makeForm: JSON.stringify(makeFields),\n    uploadForm: JSON.stringify(uploadFields),\n    fixForm: JSON.stringify(fixFields),\n    pauseForm: JSON.stringify(pauseFields),\n    progressForm: JSON.stringify([{ fieldType: 'html', html: p.join('') }]),\n    nothingText: 'No finished video is waiting for you. New Shorts arrive every day at 2:11 pm IST, or make one now from the Studio.',\n    wrongChannelText: ytError\n      ? `n8n couldn’t check your YouTube login (${ytError.slice(0, 160)}). Open n8n → Credentials → YouTube account and reconnect it.`\n      : `n8n’s YouTube login is for “${channelName || 'another channel'}”, not History with Me. Open n8n → Credentials → YouTube account, reconnect it and choose the History with Me channel.`,\n  },\n}];\n" },
  },
  output: [{ route: 'make', key: 'story', what: 'Short', makeTitle: '🎬 Make a Short', makeForm: '[]', uploadForm: '[]', fixForm: '[]', pauseForm: '[]', progressForm: '[]', waiting: [], nothingText: 'x', wrongChannelText: 'x' }],
});

const routeChoice = switchCase({
  version: 3.2,
  config: {
    name: 'Route the choice',
    parameters: {
      rules: {
        values: [
          { renameOutput: true, outputKey: 'Make', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'make', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Trend', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'trend', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Upload', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'upload', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Remake or discard', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'fix', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Idea', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'idea', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Progress', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'progress', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Pause or resume', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'pause', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Nothing waiting', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'nothing', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
          { renameOutput: true, outputKey: 'Wrong YouTube login', conditions: { options: routeOptions, conditions: [{ leftValue: expr('{{ $json.route }}'), rightValue: 'wrongChannel', operator: { type: 'string', operation: 'equals' } }], combinator: 'and' } },
        ],
      },
      options: {},
    },
  },
});

const makePage = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Make a video',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.makeForm }}'),
      options: { formTitle: expr('{{ $json.makeTitle }}'), buttonLabel: '🎬 Make it', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ pick: '🧠 Strategist picks the most viral one', own: '', style: '🧠 Let the strategist choose' }],
});

const scanTrends = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.2,
  config: {
    name: 'Scan YouTube trends',
    onError: 'continueErrorOutput',
    parameters: {
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: '5xFuzZIALzyJUa0f', cachedResultName: 'History trend scout' },
      workflowInputs: {
        mappingMode: 'defineBelow',
        value: { format: 'short', days: 14, queries: '', maxQueries: 6 },
        matchingColumns: [],
        schema: [
          { id: 'format', displayName: 'format', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
          { id: 'days', displayName: 'days', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'number' },
          { id: 'queries', displayName: 'queries', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
          { id: 'maxQueries', displayName: 'maxQueries', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'number' },
        ],
        attemptToConvertTypes: false,
        convertFieldsToString: true,
      },
      mode: 'once',
      options: { waitForSubWorkflow: true },
    },
  },
  output: [{ format: 'short', scannedAt: '2026-11-27T08:00:00Z', count: 1, top: [{ title: 'The day the Thames stank', views: 1200000, viewsPerDay: 240000, outlier: 120, url: 'https://youtu.be/abc' }] }],
});

const trendPage = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Trend: build the page',
    parameters: { mode: 'runOnceForAllItems', jsCode: "const res = $input.first().json || {};\nconst esc = (s) => String(s ?? '').replace(/[&<>\"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' }[c]));\nconst short = (n) => {\n  n = Number(n) || 0;\n  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\\.0$/, '') + 'M';\n  if (n >= 1e3) return Math.round(n / 1e3) + 'K';\n  return String(Math.round(n));\n};\nconst clean = (t) => String(t || '').replace(/#[\\p{L}\\p{N}_]+/gu, '').replace(/[|]+/g, ' ').replace(/\\s+/g, ' ').trim();\n\nconst seen = new Set();\nconst picks = [];\nfor (const r of (res.top || [])) {\n  const title = clean(r && r.title);\n  const k = title.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 40);\n  if (title.length < 8 || seen.has(k)) continue;\n  seen.add(k);\n  picks.push({\n    title, views: r.views || 0, viewsPerDay: r.viewsPerDay || 0, ageDays: r.ageDays || 0, outlier: r.outlier || 0,\n    channel: r.channel || '', url: /^https:\\/\\/(www\\.)?youtu(\\.be|be\\.com)\\//.test(String(r.url || '')) ? String(r.url) : '',\n  });\n  if (picks.length >= 8) break;\n}\n\nconst STYLES = ['🧠 Let the strategist choose', '👁 POV, you are there', '🎬 Epic movie trailer', '⏳ Time-traveller vlog'];\nconst style = {\n  fieldLabel: 'Style', fieldName: 'style', fieldType: 'radio', requiredField: true, defaultValue: STYLES[0],\n  fieldOptions: { values: STYLES.map((o) => ({ option: o })) },\n};\nlet fields;\nif (picks.length) {\n  const list = picks.map((p) => `<li><b>${esc(p.title)}</b><br>${short(p.viewsPerDay)} views a day · ${p.outlier}× its channel’s size` +\n    `${p.url ? ` · <a href=\"${esc(p.url)}\">watch</a>` : ''}</li>`).join('');\n  fields = [\n    { fieldType: 'html', html: `<p>History Shorts taking off on YouTube right now:</p><ol>${list}</ol><p>Pick one. Your agent makes its own original Short on that subject, with a fresh hook. Never a copy.</p>` },\n    {\n      fieldLabel: 'Which trend?', fieldName: 'trend', fieldType: 'dropdown', requiredField: true,\n      defaultValue: `1. ${picks[0].title.slice(0, 90)}`,\n      fieldOptions: { values: picks.map((p, i) => ({ option: `${i + 1}. ${p.title.slice(0, 90)}` })) },\n    },\n    { fieldLabel: 'Your angle (optional)', fieldName: 'angle', fieldType: 'text', requiredField: false, placeholder: 'e.g. Tell it as a soldier who was there' },\n    style,\n  ];\n} else {\n  fields = [\n    { fieldType: 'html', html: '<p>YouTube didn’t return rising history Shorts just now (its daily search allowance may be used up). Type a topic and your agent makes it anyway.</p>' },\n    { fieldLabel: 'Topic', fieldName: 'angle', fieldType: 'text', requiredField: true, placeholder: 'e.g. The emu war of 1932' },\n    style,\n  ];\n}\nreturn [{ json: { picks, scannedAt: res.scannedAt || '', trendForm: JSON.stringify(fields) } }];\n" },
  },
  output: [{ picks: [{ title: 'The day the Thames stank' }], trendForm: '[]' }],
});

const pickTrend = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Pick a trend',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.trendForm }}'),
      options: { formTitle: '🔥 Viral right now', buttonLabel: '🎬 Make my version', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ trend: '1. The day the Thames stank', angle: '', style: '🧠 Let the strategist choose' }],
});

const chooseUpload = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Choose a video to upload',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.uploadForm }}'),
      options: { formTitle: '⬆️ Upload to YouTube', buttonLabel: 'Next ›', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ video: '1. When Sewage Shut Down Parliament (Short, 58 s)', when: '🚀 Publish now' }],
});

const uploadCheck = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Upload: check the choice',
    onError: 'continueErrorOutput',
    parameters: { mode: 'runOnceForAllItems', jsCode: "const base = $('Work out the choice').first().json;\nconst a = $input.first().json || {};\nconst esc = (s) => String(s ?? '').replace(/[&<>\"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' }[c]));\nconst pick = (o, keys) => {\n  for (const k of keys) {\n    const v = o ? o[k] : undefined;\n    if (v !== undefined && v !== null && String(v).trim() !== '') return v;\n  }\n  return '';\n};\nconst IST = 5.5 * 3600e3;\nconst MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];\nconst DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];\nconst istText = (iso) => {\n  const d = new Date(Date.parse(iso) + IST);\n  let h = d.getUTCHours();\n  const m = String(d.getUTCMinutes()).padStart(2, '0');\n  const ap = h >= 12 ? 'pm' : 'am';\n  h = h % 12 || 12;\n  return `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${h}:${m} ${ap}`;\n};\nconst nextSlot = (hh, mm) => {\n  const now = Date.now();\n  const ist = new Date(now + IST);\n  let t = Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate(), hh, mm) - IST;\n  if (t < now + 45 * 60e3) t += 86400e3;\n  return new Date(t).toISOString();\n};\n\nconst choice = String(pick(a, ['video', 'Which video?']));\nconst v = (base.waiting || [])[parseInt(choice, 10) - 1];\nif (!v || !choice.startsWith(`${v.n}. `)) throw new Error('That video is no longer waiting for you. Open the Studio again.');\nconst assets = v.assets || {};\nif (!assets['video.mp4']) throw new Error('The video file is missing on GitHub. Use “Remake or discard” to make it again.');\n\nconst when = String(pick(a, ['when', 'When should it go live?']));\nconst slot = { story: [19, 0], loop: [12, 30], movie: [18, 30] }[v.kind] || [19, 0];\nlet privacy = 'public';\nlet publishAt = '';\nif (when.includes('Schedule')) {\n  privacy = 'private';\n  publishAt = nextSlot(slot[0], slot[1]);\n} else if (when.includes('private')) {\n  privacy = 'private';\n}\n\nconst title = String(v.title || 'History with Me').replace(/[<>]/g, '').replace(/\\s+/g, ' ').trim().slice(0, 100);\nconst description = String(v.description || '').replace(/[<>]/g, '').slice(0, 4900);\nconst tags = [];\nlet total = 0;\nfor (const t of (v.tags || [])) {\n  const c = String(t).replace(/[<>,\"]/g, ' ').replace(/\\s+/g, ' ').trim().slice(0, 60);\n  if (!c || tags.includes(c)) continue;\n  const cost = c.length + (c.includes(' ') ? 2 : 0) + 1;\n  if (total + cost > 480) break;\n  tags.push(c);\n  total += cost;\n}\nconst comment = String(v.pinned_comment || '').trim().slice(0, 1000);\nconst status = {\n  privacyStatus: privacy, embeddable: true, license: 'youtube', publicStatsViewable: true,\n  selfDeclaredMadeForKids: false, containsSyntheticMedia: true,\n};\nif (publishAt) status.publishAt = publishAt;\nconst whenText = publishAt ? `goes live ${istText(publishAt)} IST`\n  : privacy === 'public' ? 'goes live right away' : 'uploads as private, you publish it later in YouTube Studio';\n\nconst shownDesc = esc(description.length > 700 ? description.slice(0, 700) + '…' : description).replace(/\\n/g, '<br>');\nconst html = `<p><b>${esc(title)}</b><br>It ${esc(whenText)}.</p>` +\n  (shownDesc ? `<p><b>Description</b><br>${shownDesc}</p>` : '') +\n  (tags.length ? `<p><b>Tags</b><br>${esc(tags.join(', '))}</p>` : '') +\n  (comment ? `<p><b>Comment to pin</b><br>${esc(comment)}</p>` : '') +\n  '<p>✔ Education category · Not made for kids · Labelled as AI-made (altered or synthetic content), as YouTube requires.</p>';\n\nreturn [{\n  json: {\n    id: v.id, kind: v.kind, title, description, tags: tags.join(','), privacy, publishAt, notify: privacy === 'public' && !publishAt,\n    status, videoAsset: String(assets['video.mp4']), thumbAsset: assets['thumbnail.jpg'] ? String(assets['thumbnail.jpg']) : '',\n    comment, whenText, confirmForm: JSON.stringify([{ fieldType: 'html', html }]),\n  },\n}];\n" },
  },
  output: [{ id: '20261127-great-stink', kind: 'story', title: 'When Sewage Shut Down Parliament', description: 'x', tags: 'great stink', privacy: 'public', publishAt: '', notify: true, status: { privacyStatus: 'public', containsSyntheticMedia: true }, videoAsset: '111', thumbAsset: '112', comment: 'x', whenText: 'goes live right away', confirmForm: '[]' }],
});

const confirmUpload = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Ready to upload?',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.confirmForm }}'),
      options: { formTitle: 'Ready to upload?', buttonLabel: '⬆️ Upload to YouTube', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ submittedAt: '2026-11-27T13:46:00.000+05:30' }],
});

const downloadVideo = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Download the video',
    onError: 'continueErrorOutput',
    parameters: {
      method: 'GET',
      url: expr(REPO_API + '/releases/assets/{{ $("Upload: check the choice").first().json.videoAsset }}'),
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'githubApi',
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: { parameters: [{ name: 'Accept', value: 'application/octet-stream' }, { name: 'X-GitHub-Api-Version', value: '2022-11-28' }] },
      options: { response: { response: { responseFormat: 'file', outputPropertyName: 'data' } }, timeout: 300000 },
    },
    credentials: { githubApi: githubLogin },
  },
  output: [{}],
});

const uploadVideo = node({
  type: 'n8n-nodes-base.youTube',
  version: 1,
  config: {
    name: 'Upload to YouTube',
    onError: 'continueErrorOutput',
    parameters: {
      resource: 'video',
      operation: 'upload',
      title: expr('{{ $("Upload: check the choice").first().json.title }}'),
      regionCode: 'IN',
      categoryId: '27',
      binaryProperty: 'data',
      options: {
        description: expr('{{ $("Upload: check the choice").first().json.description }}'),
        tags: expr('{{ $("Upload: check the choice").first().json.tags }}'),
        privacyStatus: expr('{{ $("Upload: check the choice").first().json.privacy }}'),
        publishAt: expr('{{ $("Upload: check the choice").first().json.publishAt }}'),
        notifySubscribers: expr('{{ $("Upload: check the choice").first().json.notify }}'),
        embeddable: true,
        publicStatsViewable: true,
        selfDeclaredMadeForKids: false,
        license: 'youtube',
        defaultLanguage: 'en',
      },
    },
    credentials: { youTubeOAuth2Api: youtubeLogin },
  },
  output: [{ uploadId: 'abcDEF12345' }],
});

const labelAi = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Label it as AI-made',
    onError: 'continueRegularOutput',
    parameters: {
      method: 'PUT',
      url: 'https://www.googleapis.com/youtube/v3/videos',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'youTubeOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: { parameters: [{ name: 'part', value: 'status' }] },
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ id: $json.uploadId || $json.id, status: $("Upload: check the choice").first().json.status }) }}'),
      options: { timeout: 30000 },
    },
    credentials: { youTubeOAuth2Api: youtubeLogin },
  },
  output: [{ id: 'abcDEF12345', kind: 'youtube#video', status: { containsSyntheticMedia: true } }],
});

const hasThumb = ifElse({
  version: 2.2,
  config: {
    name: 'Has a thumbnail?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $("Upload: check the choice").first().json.thumbAsset }}'), rightValue: '', operator: { type: 'string', operation: 'notEmpty', singleValue: true } }],
        combinator: 'and',
      },
    },
  },
});

const downloadThumb = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Download the thumbnail',
    onError: 'continueRegularOutput',
    parameters: {
      method: 'GET',
      url: expr(REPO_API + '/releases/assets/{{ $("Upload: check the choice").first().json.thumbAsset }}'),
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'githubApi',
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: { parameters: [{ name: 'Accept', value: 'application/octet-stream' }, { name: 'X-GitHub-Api-Version', value: '2022-11-28' }] },
      options: { response: { response: { responseFormat: 'file', outputPropertyName: 'data' } }, timeout: 60000 },
    },
    credentials: { githubApi: githubLogin },
  },
  output: [{}],
});

const setThumb = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Set the thumbnail',
    onError: 'continueRegularOutput',
    parameters: {
      method: 'POST',
      url: 'https://www.googleapis.com/upload/youtube/v3/thumbnails/set',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'youTubeOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: { parameters: [{ name: 'videoId', value: expr('{{ $("Upload to YouTube").first().json.uploadId }}') }, { name: 'uploadType', value: 'media' }] },
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: { parameters: [{ name: 'Content-Type', value: 'image/jpeg' }] },
      sendBody: true,
      contentType: 'binaryData',
      inputDataFieldName: 'data',
      options: { timeout: 60000 },
    },
    credentials: { youTubeOAuth2Api: youtubeLogin },
  },
  output: [{ kind: 'youtube#thumbnailSetResponse', items: [] }],
});

const postComment = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Post the comment to pin',
    onError: 'continueRegularOutput',
    executeOnce: true,
    parameters: {
      method: 'POST',
      url: 'https://www.googleapis.com/youtube/v3/commentThreads',
      authentication: 'predefinedCredentialType',
      nodeCredentialType: 'youTubeOAuth2Api',
      sendQuery: true,
      specifyQuery: 'keypair',
      queryParameters: { parameters: [{ name: 'part', value: 'snippet' }] },
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ snippet: { videoId: $("Upload to YouTube").first().json.uploadId, topLevelComment: { snippet: { textOriginal: $("Upload: check the choice").first().json.comment || "Which moment in history should we visit next? 👇" } } } }) }}'),
      options: { timeout: 30000 },
    },
    credentials: { youTubeOAuth2Api: youtubeLogin },
  },
  output: [{ id: 'UgxComment', kind: 'youtube#commentThread' }],
});

const fixPage = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Choose a video to fix',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.fixForm }}'),
      options: { formTitle: '🔄 Remake or 🗑 discard', buttonLabel: 'Do it', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ video: '1. When Sewage Shut Down Parliament (Short, 58 s)', what: '🔄 Remake it with fresh AI shots' }],
});

const ideaPage = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Save an idea',
    parameters: {
      operation: 'page',
      defineForm: 'fields',
      formFields: {
        values: [
          { fieldLabel: 'Your idea', fieldName: 'idea', fieldType: 'textarea', requiredField: true, placeholder: 'e.g. The dancing plague of 1518' },
          { fieldLabel: 'Make it as', fieldName: 'kind', fieldType: 'radio', requiredField: true, defaultValue: '🎬 a Short', fieldOptions: { values: [{ option: '🎬 a Short' }, { option: '🔁 a loop Short' }, { option: '🎞 a 15-minute movie' }] } },
          { fieldLabel: 'Hook or angle (optional)', fieldName: 'angle', fieldType: 'text', requiredField: false, placeholder: 'e.g. Told by a doctor who was there' },
        ],
      },
      options: { formTitle: '💡 Save an idea', buttonLabel: '💾 Save it', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ idea: 'The dancing plague of 1518', kind: '🎬 a Short', angle: '' }],
});

const progressPage = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Your progress',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.progressForm }}'),
      limitWaitTime: true,
      limitType: 'afterTimeInterval',
      resumeAmount: 10,
      resumeUnit: 'minutes',
      options: { formTitle: '📊 Your progress', buttonLabel: '🏠 Back to the Studio', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ submittedAt: '2026-11-27T13:46:00.000+05:30' }],
});

const pausePage = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Pause or resume',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $json.pauseForm }}'),
      options: { formTitle: '⏯ Daily videos', buttonLabel: 'Save', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ state: '⏸ Pause the daily videos' }],
});

const writeRequest = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Write the request for your agent',
    onError: 'continueErrorOutput',
    parameters: { mode: 'runOnceForAllItems', jsCode: "const base = $('Work out the choice').first().json;\nconst route = base.route;\nconst a = $input.first().json || {};\nconst esc = (s) => String(s ?? '').replace(/[&<>\"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' }[c]));\nconst pick = (o, keys) => {\n  for (const k of keys) {\n    const v = o ? o[k] : undefined;\n    if (v !== undefined && v !== null && String(v).trim() !== '') return v;\n  }\n  return '';\n};\nconst clean = (s) => String(s || '').replace(/\\s+/g, ' ').trim().slice(0, 200);\nconst styleFormat = (s) => {\n  s = String(s || '');\n  if (s.includes('POV')) return 'pov';\n  if (s.includes('trailer')) return 'trailer';\n  if (s.includes('Time')) return 'timetraveler';\n  return '';\n};\nconst STYLE_NAME = { pov: 'POV', trailer: 'movie-trailer', timetraveler: 'time-traveller' };\nconst video = (answer) => {\n  const choice = String(pick(answer, ['video', 'Which video?']));\n  const v = (base.waiting || [])[parseInt(choice, 10) - 1];\n  if (!v || !choice.startsWith(`${v.n}. `)) throw new Error('That video is no longer waiting for you. Open the Studio again.');\n  return v;\n};\nconst TELEGRAM = '<p>📲 Your agent confirms on Telegram in a minute.</p>';\n\nlet command;\nlet title;\nlet html;\nlet details;\n\nif (route === 'make') {\n  const chosen = String(pick(a, ['pick', 'Topic']));\n  const own = clean(pick(a, ['own', '…or type your own topic']));\n  const topic = own || (chosen && !chosen.startsWith('🧠') ? clean(chosen) : '');\n  const kind = ['story', 'loop', 'movie'].includes(base.key) ? base.key : 'story';\n  const fmt = kind === 'movie' ? '' : styleFormat(pick(a, ['style', 'Style']));\n  command = kind === 'movie' ? { action: 'movie', kind: 'movie', topic } : { action: 'make', kind, topic };\n  if (fmt) command.format = fmt;\n  title = `${kind === 'movie' ? '🎞' : '🎬'} Your ${base.what} is on its way`;\n  html = `<p>Your agent is making a ${esc(base.what)}${topic ? ` about <b>${esc(topic)}</b>` : ' on the strategist’s most viral pick'}` +\n    `${fmt ? ` in ${STYLE_NAME[fmt]} style` : ''}.</p>` +\n    `<p>📲 It arrives on Telegram in about ${kind === 'movie' ? 40 : 10} minutes. Then open the Studio and tap <b>Upload a finished video</b>.</p>`;\n  details = `${kind}: ${topic || 'strategist pick'}${fmt ? ' (' + fmt + ')' : ''}`;\n} else if (route === 'trend') {\n  const page = $('Trend: build the page').first().json;\n  const choice = String(pick(a, ['trend', 'Which trend?']));\n  const p = (page.picks || [])[parseInt(choice, 10) - 1];\n  const angle = clean(pick(a, ['angle', 'Your angle (optional)', 'Topic']));\n  let topic = p ? p.title : angle;\n  if (p && angle) topic = `${p.title}, ${angle}`;\n  topic = clean(topic);\n  if (!topic) throw new Error('No trend or topic was chosen.');\n  const fmt = styleFormat(pick(a, ['style', 'Style']));\n  command = { action: 'make', kind: 'story', topic };\n  if (fmt) command.format = fmt;\n  title = '🔥 Making it while it’s hot';\n  html = `<p>Your agent is making an original Short about <b>${esc(topic)}</b>${fmt ? ` in ${STYLE_NAME[fmt]} style` : ''}.</p>` +\n    '<p>📲 It arrives on Telegram in about 10 minutes. Then open the Studio and tap <b>Upload a finished video</b>.</p>';\n  details = `trend: ${topic}`;\n} else if (route === 'upload') {\n  const up = $('Upload: check the choice').first().json;\n  const res = $('Upload to YouTube').first().json || {};\n  const vid = String(res.uploadId || res.id || '');\n  const ok = (name) => {\n    try {\n      const j = $(name).first().json;\n      return !!(j && !j.error && (j.id || j.kind));\n    } catch (e) {\n      return false;\n    }\n  };\n  const ai = ok('Label it as AI-made');\n  const posted = ok('Post the comment to pin');\n  const thumb = ok('Set the thumbnail');\n  command = {\n    action: 'uploaded', id: up.id, via: 'n8n', video_id: vid, privacy: up.privacy, publish_at: up.publishAt || '',\n    ai_label: ai, comment_posted: posted, thumbnail: thumb,\n  };\n  const todo = [];\n  todo.push(ai ? 'Labelled as AI-made ✔' : '⚠️ In YouTube Studio, set <b>Altered or synthetic content</b> to Yes');\n  if (posted) todo.push('Comment posted. Pin it in YouTube Studio → Comments (YouTube doesn’t let apps pin)');\n  else if (up.comment) todo.push(`Add this comment and pin it: <i>${esc(up.comment)}</i>`);\n  if (thumb) todo.push('Thumbnail set ✔');\n  title = '✅ Uploaded to YouTube';\n  html = `<p><b>${esc(up.title)}</b> ${esc(up.whenText)}.</p>` +\n    (vid ? `<p><a href=\"https://youtu.be/${esc(vid)}\">Open the video</a> · <a href=\"https://studio.youtube.com/video/${esc(vid)}/edit\">Open it in YouTube Studio</a></p>` : '') +\n    `<ul>${todo.map((t) => `<li>${t}</li>`).join('')}</ul>`;\n  details = `${up.title} → ${vid || 'no id'} (${up.publishAt || up.privacy})`;\n} else if (route === 'fix') {\n  const v = video(a);\n  const remake = String(pick(a, ['what', 'What should happen?'])).includes('Remake');\n  command = { action: remake ? 'remake' : 'discard', id: v.id };\n  title = remake ? '🔄 Remaking it' : '🗑 Discarded';\n  html = remake\n    ? `<p>Your agent drops the old version of <b>${esc(v.title)}</b> and makes a fresh one with new AI shots. It arrives on Telegram in about ${v.kind === 'movie' ? 40 : 10} minutes.</p>`\n    : `<p><b>${esc(v.title)}</b> is discarded. Nothing goes to YouTube.</p>${TELEGRAM}`;\n  details = `${command.action}: ${v.title}`;\n} else if (route === 'idea') {\n  const topic = clean(pick(a, ['idea', 'Your idea']));\n  if (!topic) throw new Error('The idea was empty.');\n  const forWhat = String(pick(a, ['kind', 'Make it as'])).toLowerCase();\n  const kind = forWhat.includes('loop') ? 'loop' : forWhat.includes('movie') ? 'movie' : 'story';\n  const angle = clean(pick(a, ['angle', 'Hook or angle (optional)']));\n  command = { action: 'idea', kind, topic };\n  if (angle) command.angle = angle;\n  title = '💡 Idea saved';\n  html = `<p><b>${esc(topic)}</b> is saved. The strategist uses it for an upcoming ${kind === 'movie' ? 'movie' : kind === 'loop' ? 'loop Short' : 'Short'}.</p>${TELEGRAM}`;\n  details = `idea (${kind}): ${topic}`;\n} else if (route === 'pause') {\n  const pause = String(pick(a, ['state', 'Daily videos'])).includes('Pause');\n  command = { action: pause ? 'pause' : 'resume' };\n  title = pause ? '⏸ Daily videos paused' : '▶️ Daily videos back on';\n  html = pause\n    ? '<p>Your agent stops making the daily videos until you resume them. You can still make videos from the Studio.</p>'\n    : '<p>Your agent makes the daily Short again (2:11 pm IST) and movies on Wednesdays and Sundays.</p>';\n  html += TELEGRAM;\n  details = command.action;\n} else {\n  throw new Error(`Nothing to send to your agent for “${route}”.`);\n}\n\nconst stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\\.\\d+Z$/, '').replace('T', '-');\nconst file = `commands/${stamp}-${command.action}-${Math.random().toString(36).slice(2, 8)}.json`;\nconst commitMessage = `Studio (n8n): ${command.action}${command.topic ? ' - ' + command.topic.slice(0, 60) : ''}`;\nreturn [{\n  json: {\n    command, file, content: JSON.stringify(command, null, 2) + '\\n', commitMessage,\n    doneTitle: title, doneForm: JSON.stringify([{ fieldType: 'html', html }]), logAction: command.action, logDetails: clean(details),\n  },\n}];\n" },
  },
  output: [{ command: { action: 'make', kind: 'story', topic: '' }, file: 'commands/20261127-081500-make-abc123.json', content: '{}', commitMessage: 'Studio (n8n): make', doneTitle: '🎬 Your Short is on its way', doneForm: '[]', logAction: 'make', logDetails: 'story: strategist pick' }],
});

const sendToAgent = node({
  type: 'n8n-nodes-base.github',
  version: 1.1,
  config: {
    name: 'Send to the agent',
    onError: 'continueErrorOutput',
    parameters: {
      resource: 'file',
      operation: 'create',
      authentication: 'accessToken',
      owner: { __rl: true, mode: 'name', value: 'manzilwbgb-max' },
      repository: { __rl: true, mode: 'name', value: 'ManzilBiswas-e8d-youtube-channel' },
      filePath: expr('{{ $json.file }}'),
      binaryData: false,
      fileContent: expr('{{ $json.content }}'),
      commitMessage: expr('{{ $json.commitMessage }}'),
      additionalParameters: { branch: { branch: 'main' } },
    },
    credentials: { githubApi: githubLogin },
  },
  output: [{ content: { path: 'commands/20261127-081500-make-abc123.json' }, commit: { sha: 'abc123' } }],
});

const logIt = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Log it',
    onError: 'continueRegularOutput',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: '9sn1ZFOJhPtfhYIt', cachedResultName: 'History with Me Studio log' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          action: expr('{{ $("Write the request for your agent").first().json.logAction }}'),
          details: expr('{{ $("Write the request for your agent").first().json.logDetails }}'),
          result: expr('{{ "sent to GitHub: " + (($json.content && $json.content.path) || "") }}'),
        },
        matchingColumns: [],
        schema: [
          { id: 'action', displayName: 'action', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'details', displayName: 'details', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'result', displayName: 'result', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
        ],
      },
      options: {},
    },
  },
  output: [{ id: 1, createdAt: '2026-11-27T08:15:00.000Z' }],
});

const allSet = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'All set',
    parameters: {
      operation: 'page',
      defineForm: 'json',
      jsonOutput: expr('{{ $("Write the request for your agent").first().json.doneForm }}'),
      limitWaitTime: true,
      limitType: 'afterTimeInterval',
      resumeAmount: 10,
      resumeUnit: 'minutes',
      options: { formTitle: expr('{{ $("Write the request for your agent").first().json.doneTitle }}'), buttonLabel: '🏠 Back to the Studio', customCss: studioCss, appendAttribution: false },
    },
  },
  output: [{ submittedAt: '2026-11-27T13:47:00.000+05:30' }],
});

const backToStudio = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Back to the Studio',
    parameters: { operation: 'completion', respondWith: 'redirect', redirectUrl: STUDIO_URL },
  },
  output: [{}],
});

const nothingWaiting = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Nothing is waiting',
    parameters: { operation: 'completion', respondWith: 'text', completionTitle: '📭 Nothing is waiting', completionMessage: expr('{{ $json.nothingText }}') },
  },
  output: [{}],
});

const wrongChannel = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Wrong YouTube login',
    parameters: { operation: 'completion', respondWith: 'text', completionTitle: '⚠️ Check your YouTube login in n8n', completionMessage: expr('{{ $json.wrongChannelText }}') },
  },
  output: [{}],
});

const showProblem = node({
  type: 'n8n-nodes-base.form',
  version: 2.6,
  config: {
    name: 'Show a problem',
    parameters: {
      operation: 'completion',
      respondWith: 'text',
      completionTitle: '⚠️ Something went wrong',
      completionMessage: expr('{{ String((typeof $json.error === "string" ? $json.error : ($json.error && ($json.error.message || $json.error.description))) || $json.message || "Unknown error").slice(0, 300) }} · Tip: if it mentions GitHub or credentials, check the GitHub (History with Me) login in n8n. If a video was already uploaded, it is on YouTube, so tap ✅ I uploaded it on its Telegram message.'),
    },
  },
  output: [{}],
});

const setupNote = sticky('## Set up once\n1. Add the **GitHub (History with Me)** login: a fine-grained GitHub token for the repo *ManzilBiswas-e8d-youtube-channel* with **Contents: Read and write**.\n2. **Publish** this workflow.\n3. On your phone open **' + STUDIO_URL + '** and add it to your home screen.\n\nOnly you can open it: it asks for your n8n login.', [openStudio], { color: 5 });

export default workflow('history-with-me-studio', 'History with Me Studio', {
  settings: { timezone: 'Asia/Kolkata', executionOrder: 'v1', saveManualExecutions: true, callerPolicy: 'workflowsFromSameOwner' },
})
  .add(openStudio)
  .to(checkChannel)
  .to(readState)
  .to(workOut)
  .to(routeChoice
    .onCase(0, makePage.to(writeRequest.to(sendToAgent.to(logIt.to(allSet.to(backToStudio))))))
    .onCase(1, scanTrends.to(trendPage.to(pickTrend.to(writeRequest))))
    .onCase(2, chooseUpload.to(uploadCheck.to(confirmUpload.to(downloadVideo.to(uploadVideo.to(labelAi.to(hasThumb
      .onTrue(downloadThumb.to(setThumb.to(postComment.to(writeRequest))))
      .onFalse(postComment))))))))
    .onCase(3, fixPage.to(writeRequest))
    .onCase(4, ideaPage.to(writeRequest))
    .onCase(5, progressPage.to(backToStudio))
    .onCase(6, pausePage.to(writeRequest))
    .onCase(7, nothingWaiting)
    .onCase(8, wrongChannel))
  .add(readState.onError(showProblem))
  .add(scanTrends.onError(showProblem))
  .add(uploadCheck.onError(showProblem))
  .add(downloadVideo.onError(showProblem))
  .add(uploadVideo.onError(showProblem))
  .add(writeRequest.onError(showProblem))
  .add(sendToAgent.onError(showProblem))
  .add(setupNote)
  .group('Find a viral topic', [trendPage, pickTrend], { description: 'Turns the History trend scout results into a page where you pick a rising history Short to make your own version of' })
  .group('Polish the upload', [labelAi, hasThumb, downloadThumb, setThumb, postComment], { description: 'Labels the video AI-made, sets the thumbnail and posts the comment to pin. A failure here never undoes the upload' });
