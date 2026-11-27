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
    parameters: { mode: 'runOnceForAllItems', jsCode: __WORK_OUT__ },
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
    parameters: { mode: 'runOnceForAllItems', jsCode: __TREND_PAGE__ },
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
    parameters: { mode: 'runOnceForAllItems', jsCode: __UPLOAD_CHECK__ },
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
    parameters: { mode: 'runOnceForAllItems', jsCode: __WRITE_REQUEST__ },
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
