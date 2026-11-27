import fs from 'fs';

const dir = new URL('.', import.meta.url);
const read = (p) => fs.readFileSync(new URL(p, dir), 'utf8');
let ts = read('studio.template.ts');
const parts = { __WORK_OUT__: 'work_out', __TREND_PAGE__: 'trend_page', __UPLOAD_CHECK__: 'upload_check', __WRITE_REQUEST__: 'write_request' };
for (const [mark, name] of Object.entries(parts)) {
  if (!ts.includes(mark)) throw new Error(`missing ${mark}`);
  ts = ts.replace(mark, () => JSON.stringify(read(`code/${name}.js`)));
}
fs.writeFileSync(new URL('history-with-me-studio.ts', dir), ts);
for (const [mark, name] of Object.entries(parts)) {
  const lit = JSON.stringify(read(`code/${name}.js`));
  if (!ts.includes(lit)) throw new Error(`embedded ${name} differs from its tested file`);
}
console.log('built', ts.length, 'chars, all code blocks identical to the tested files');
