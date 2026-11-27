# History with Me Studio — phone version (n8n, SDK format)

`history-with-me-studio.ts` is the **n8n Workflow SDK** source of the "History with Me Studio" workflow in your
n8n (https://manzil1234.app.n8n.cloud/workflow/ohaKyPczNitUxQas). It is the same Studio as the Claude app, as a
private web page that works in any phone browser:

https://manzil1234.app.n8n.cloud/form/history-with-me-studio

Only you can open it: it asks for your n8n login.

## What the buttons do

| Button | What happens |
| --- | --- |
| 🎬 Make a Short / 🔁 loop Short / 🎞 15-minute movie | Pick one of the strategist's ideas or type your own, choose a style. Your agent makes it and sends it to Telegram. |
| 🔥 Find a viral topic | Runs the *History trend scout* workflow, shows history Shorts rising on YouTube right now, and makes your own original version. |
| ⬆️ Upload a finished video | Shows the SEO pack (title, description, tags, comment), then uploads straight to YouTube with your n8n YouTube login: Education category, not made for kids, **labelled as AI-made** (altered or synthetic content), thumbnail set, comment posted. Publish now, schedule for the best time, or private. |
| 🔄 Remake or 🗑 discard | Throws away a finished video, or makes a fresh one with new AI shots. |
| 💡 Save an idea | Goes into the strategist's inbox. |
| 📊 See my progress | Subscribers, days left to 1 Feb 2027, the monetization targets, budget, last runs. |
| ⏯ Pause or resume | Stops or restarts the daily videos. |

Every request is written into `commands/` in this repo (the agent's `commands.yml` runs it within a minute) and logged
in the n8n data table *History with Me Studio log*.

## Set up once

1. **An active n8n plan.** n8n only runs workflows on a paid plan (Starter is €24/month, or €20/month paid yearly);
   the free trial has ended.
2. **GitHub login for n8n.** On github.com: Settings → Developer settings → Personal access tokens → Fine-grained
   tokens → Generate new token. Repository access: *Only select repositories* → `ManzilBiswas-e8d-youtube-channel`.
   Permissions → Repository permissions → **Contents: Read and write**. Generate, copy the token.
   In n8n: Credentials → Add credential → **GitHub API** → paste it as *Access Token*, name it
   `GitHub (History with Me)`. It is used by *Read agent state*, *Send to the agent*, *Download the video* and
   *Download the thumbnail*.
3. **Publish** the workflow in n8n, open the link above on your phone, and use *Add to Home screen*.

The YouTube steps use your existing n8n credential *YouTube account*. The Studio checks it belongs to the
History with Me channel before it uploads anything.

## Changing it

The four Code steps live in `code/*.js` and are tested by `node test.mjs`. `node build.mjs` puts them into
`studio.template.ts` and writes `history-with-me-studio.ts`, the file n8n is built from.
