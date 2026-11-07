const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../app/static/app.js'), 'utf8');

function harness() {
  const nodes = new Map(), storage = new Map(), messages = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {value: '', textContent: '', innerHTML: '', hidden: false, dataset: {},
      querySelector: () => null, querySelectorAll: () => [], append() {}, replaceChildren(...children) { this.children = children; },
      setAttribute() {}, addEventListener() {}, select() {}});
    return nodes.get(id);
  }
  const c = vm.createContext({console, Promise, Event: class {constructor(type) {this.type = type;}},
    setTimeout: () => 1, clearTimeout() {}, setInterval() {},
    document: {getElementById: node, createElement: () => ({...node(Symbol())}), addEventListener() {}},
    window: {addEventListener() {}},
    navigator: {clipboard: {writeText: async (text) => messages.push(text)}},
    localStorage: {getItem: (k) => storage.get(k) ?? null, setItem: (k,v) => storage.set(k,v), removeItem: (k) => storage.delete(k),
      get length() {return storage.size;}, key: (i) => [...storage.keys()][i]},
    messages,
  });
  vm.runInContext(source, c);
  const run = (code) => vm.runInContext(code, c);
  run(`state = {notebook_id: 'book', live: {session_id: 'A', stage: 1, file: 'a.py'}};
    attempt = {session_id: 'A', file: 'a.py', path: '/a.py', text: 'old', revision: 'r1', mtime: 1};
    editor = {value: 'old', getValue() {return this.value;}, setValue(v) {this.value=v;}, clearHistory() {},
      getAllMarks() {return [];}, getLine() {return '';}, markText() {return {on() {}};}};
    view = 1;
    banner = (message) => messages.push(message);
    refresh = async () => {};
    renderBar = () => {};
    renderResults = (result) => messages.push(result);
  `);
  return {c, run, node, storage, messages};
}
function deferred() {let resolve; const promise = new Promise(r => {resolve = r;}); return {promise, resolve};}
function saved(text, session_id='A') {return {session_id, file:'a.py', path:'/a.py', text, revision:'r2', mtime:2};}

for (const mode of ['code', 'examples', 'both']) test(`Run saves ${mode} before execution without advancing stage`, async () => {
  const h = harness(), calls=[];
  h.c.calls=calls;
  h.c.saveReply = saved('new');
  h.run(`api = async (method, path, body) => { calls.push({path, body}); return path === '/api/run' ? {session_id: 'A', rows: []} : saveReply; };
    savePanel = async () => { calls.push({path:'panel'}); panelDirty=false; };`);
  if (mode !== 'examples') h.run(`editor.value='new'; markDirty(true);`);
  if (mode !== 'code') h.run(`panelDirty=true;`);
  await h.run('runTests()');
  assert.deepEqual(calls.map(x=>x.path), mode === 'code' ? ['/api/attempt','/api/run'] : mode === 'examples' ? ['panel','/api/run'] : ['/api/attempt','panel','/api/run']);
  assert.equal(h.run('state.live.stage'),1);
});

test('Run stops after conflict or invalid examples', async () => {
  for (const failure of ['code','examples']) {
    const h=harness(); h.c.calls=[];
    h.run(`api=async()=>{calls.push('run');};`);
    if (failure==='code') h.run(`dirty=true; save=async()=>false;`);
    else h.run(`panelDirty=true; savePanel=async()=>{throw new Error('invalid examples');};`);
    if (failure==='code') await h.run('runTests()');
    else await assert.rejects(h.run('runTests()'), /invalid examples/);
    assert.equal(h.c.calls.length,0);
  }
});

test('typing during parts save survives response and prevents Run', async () => {
  const h=harness(), wait=deferred(); h.c.wait=wait.promise; h.c.calls=[];
  h.run(`api=async(method,path)=>{calls.push(path); return await wait;};
    panelDirty=true; savePanel=async()=>{await saveParts({examples: []}); panelDirty=false;};`);
  const running=h.run('runTests()');
  await Promise.resolve();
  h.run(`editor.value='newer typing'; markDirty(true);`);
  wait.resolve(saved('server merged examples'));
  await running;
  assert.equal(h.run('getCode()'),'newer typing');
  assert.equal(h.run('dirty'),true);
  assert.deepEqual([...h.c.calls],['/api/attempt/parts']);
  assert.match(h.messages.at(-1),/inputs changed/);
});

test('typing examples while Run prepares inputs prevents execution', async () => {
  const h=harness(), wait=deferred(); h.c.wait=wait.promise; h.c.calls=[];
  h.run(`panelDirty=true; savePanel=async()=>await wait; api=async()=>calls.push('run');`);
  const running=h.run('runTests()'); h.run('panelEdited()'); wait.resolve(); await running;
  assert.equal(h.c.calls.length,0);
});

test('queued actions retain their original session and are not replayed', async () => {
  const h=harness(), wait=deferred(); h.c.wait=wait.promise; h.c.calls=[];
  h.run(`chain=wait;`);
  const queued=h.run(`change(async()=>calls.push('mutated'))`);
  h.run(`state.live.session_id='B';`); wait.resolve(); await queued;
  assert.equal(h.c.calls.length,0);
  assert.match(h.messages[0],/solve ended or changed/);
});

test('serialized repeated Run clicks do not overlap', async () => {
  const h=harness(), wait=deferred(); h.c.wait=wait.promise; h.c.calls=[];
  h.run(`api=async()=>{calls.push('start'); await wait; calls.push('end'); return {session_id:'A',rows:[]};};`);
  const one=h.run('change(runTests)'), two=h.run('change(runTests)');
  await Promise.resolve(); await Promise.resolve();
  assert.deepEqual([...h.c.calls],['start']); wait.resolve(); await Promise.all([one,two]);
  assert.deepEqual([...h.c.calls],['start','end','start','end']);
});

test('late result and save responses cannot replace another session', async () => {
  const h=harness(), wait=deferred(); h.c.wait=wait.promise;
  h.run(`api=async()=>await wait;`); const run=h.run('runTests()');
  h.run(`state.live.session_id='B';`); wait.resolve({session_id:'A',rows:[]}); await run;
  assert.equal(h.messages.length,0);
  h.c.reply=saved('old response');
  assert.throws(()=>h.run('acceptSavedAttempt(reply,editGeneration)'),/solve changed/);
  assert.equal(h.run('getCode()'),'old');
});

test('API includes captured session in writes and explicit session in reads', async()=>{
  const h=harness(), requests=[];
  h.c.fetch=async (url, options)=>{requests.push({url,body:options.body});return {ok:true,json:async()=>({})};};
  h.run(`activeSession='A'; state.live.session_id='B';`);
  await h.run(`api('POST','/api/solve/stage',{n:2})`);
  await h.run(`api('GET','/api/attempt?session_id=B')`);
  assert.equal(JSON.parse(requests[0].body).session_id,'A');
  assert.equal(requests[1].url,'/api/attempt?session_id=B');
});

function controls(h, values) {
  const fields=Object.entries(values).map(([name,value])=>({dataset:{draftField:name},value,dispatchEvent(){}}));
  h.node('panel').querySelectorAll=()=>fields;
  return fields;
}

test('draft stores code, examples, edge flags, plan and reflection fields, finish, and statement',()=>{
  const h=harness();
  const fields=controls(h, {restate:'return whether repeated', 'plan:State':'set', 'reflection:0':'seen before', 'finish:outcome':'partial','finish:lesson':'check duplicates'});
  const table={rows:[{}, {querySelector(sel){return sel==='.args'?{value:'[1, 1]'}:sel==='.expected'?{value:'True'}:{checked:true};}}]};
  h.node('panel').querySelector=(sel)=>sel==='table.examples'?table:null;
  h.node('desc').querySelector=(sel)=>sel==='.problem textarea'?{value:'statement draft'}:null;
  h.run(`beginDraft(); editor.value='my code'; markDirty(true); panelDirty=true; persistDraft();`);
  const d=JSON.parse([...h.storage.values()][0]);
  assert.equal(d.code.text,'my code'); assert.equal(d.code.revision,'r1');
  assert.equal(d.stages['1'].fields['plan:State'],'set');
  assert.equal(d.stages['1'].fields['reflection:0'],'seen before');
  assert.equal(d.stages['1'].fields['finish:lesson'],'check duplicates');
  assert.deepEqual(d.stages['1'].examples,[{args:'[1, 1]',expected:'True',edge:true}]);
  assert.equal(d.statement,'statement draft');
});

test('code acknowledgement preserves unsaved stage fields and finish values',()=>{
  const h=harness(); controls(h, {'finish:outcome':'solved','finish:lesson':'loop invariant',answer:'notes'});
  h.run(`beginDraft(); panelDirty=true; editor.value='code'; markDirty(true); persistDraft();`);
  h.c.reply=saved('code'); h.run('acceptSavedAttempt(reply,editGeneration)');
  const d=JSON.parse([...h.storage.values()][0]);
  assert.equal(d.code,undefined); assert.equal(d.stages['1'].fields.answer,'notes');
  h.run(`acknowledgePanel(1,capturePanel()); panelDirty=false; persistDraft();`);
  const after=JSON.parse([...h.storage.values()][0]);
  assert.equal(after.stages['1'].fields.answer,undefined);
  assert.equal(after.stages['1'].fields['finish:lesson'],'loop invariant');
});

test('reload offers recovery without applying it and restores old revision for conflict checks',()=>{
  const h=harness(); controls(h,{answer:'draft answer'});
  h.run(`beginDraft(); editor.value='draft code'; markDirty(true); panelDirty=true; persistDraft();`);
  h.run(`editor.value='disk changed'; dirty=false; panelDirty=false; attempt.revision='new-disk'; beginDraft();`);
  assert.equal(h.run('recoveryPending'),true); assert.equal(h.run('getCode()'),'disk changed');
  h.run(`renderPanel=()=>{}; restoreDraft(recoveryChoice);`);
  assert.equal(h.run('getCode()'),'draft code'); assert.equal(h.run('attempt.revision'),'r1');
});

test('stage restoration restores named controls and example edge flags',()=>{
  const h=harness(), fields=controls(h,{restate:''}); h.c.examples=[];
  h.run(`beginDraft(); draftData.stages[1]={fields:{restate:'kept'},examples:[{args:'[]',expected:'False',edge:true}]};
    restoreExamples=(rows)=>examples.push(...rows); applyStageDraft(1);`);
  assert.equal(fields[0].value,'kept'); assert.equal(h.c.examples[0].edge,true); assert.equal(h.run('panelDirty'),true);
});

test('drafts are scoped to notebook and session; earlier sessions are copy-only',()=>{
  const h=harness(); h.run(`beginDraft(); editor.value='draft'; markDirty(true); persistDraft();`);
  h.run(`state.live.session_id='B'; attempt.session_id='B'; beginDraft(); offerRecovery();`);
  assert.equal(h.run('recoveryPending'),false);
  const labels=h.node('recovery').children.map(x=>x.textContent);
  assert.ok(labels.includes('Copy draft')); assert.ok(!labels.includes('Restore draft'));
  h.run(`state.notebook_id='different'; recoveryShown=null;`); h.node('recovery').children=[];
  h.run('offerRecovery()'); assert.deepEqual(h.node('recovery').children,[]);
});

test('late save acknowledgement keeps newer code in the recovery draft',()=>{
  const h=harness(); h.run(`beginDraft(); editor.value='latest'; markDirty(true);`); h.c.reply=saved('older');
  h.run('acceptSavedAttempt(reply, editGeneration-1)');
  assert.equal(JSON.parse([...h.storage.values()][0]).code.text,'latest');
});

test('storage errors and unreadable versions leave editing functional',()=>{
  const h=harness();
  for(const raw of ['{broken', JSON.stringify({version:99})]) {
    h.storage.set('bad',raw); assert.equal(h.run(`readDraft('bad')`),null); assert.equal(h.storage.get('bad'),raw);
  }
  h.run(`localStorage.setItem=()=>{throw new Error('quota');}; beginDraft(); editor.value='retained'; markDirty(true); persistDraft();`);
  assert.equal(h.run('getCode()'),'retained'); assert.match(h.node('draft-status').textContent,/unavailable/);
});

test('discarding an earlier session preserves nonvisible drafts of the current solve',()=>{
  const h=harness();
  h.run(`beginDraft(); draftData.stages[6]={fields:{'plan:Invariant':'kept invariant'}}; persistDraft();`);
  h.c.old={key:'dsa-coach:draft:book:OLD',data:{session_id:'OLD'}};
  h.storage.set(h.c.old.key,'old');
  h.run('discardDraft(old)');
  assert.equal(h.run(`draftData.stages[6].fields['plan:Invariant']`),'kept invariant');
  assert.equal(JSON.parse(h.storage.get('dsa-coach:draft:book:A')).stages['6'].fields['plan:Invariant'],'kept invariant');
});

test('acknowledged saves update the base of notes-only recovery',()=>{
  const h=harness(); controls(h,{answer:'notes'});
  h.run(`beginDraft(); panelDirty=true; persistDraft();`); h.c.reply=saved('saved code');
  h.run('acceptSavedAttempt(reply,editGeneration)');
  assert.equal(JSON.parse(h.storage.get('dsa-coach:draft:book:A')).base_revision,'r2');
});

test('an unreadable current draft is preserved until explicit discard',()=>{
  const h=harness(), key='dsa-coach:draft:book:A'; h.storage.set(key,'{bad');
  h.run(`beginDraft(); editor.value='new typing'; markDirty(true); persistDraft(); offerRecovery();`);
  assert.equal(h.storage.get(key),'{bad'); assert.equal(h.run('getCode()'),'new typing');
  assert.equal(h.run('recoveryPending'),true);
  h.run('discardDraft(recoveryChoice)');
  assert.equal(JSON.parse(h.storage.get(key)).code.text,'new typing');
});

test('textarea fallback preserves and restores code without CodeMirror',()=>{
  const h=harness();
  h.run(`editor=null; beginDraft(); setCode('fallback draft'); markDirty(true); persistDraft();`);
  assert.equal(h.node('editor-fallback').value,'fallback draft');
  h.run(`setCode('disk copy'); beginDraft(); renderPanel=()=>{}; restoreDraft(recoveryChoice);`);
  assert.equal(h.node('editor-fallback').value,'fallback draft');
  assert.equal(h.run('dirty'),true);
  assert.equal(h.run('attempt.revision'),'r1');
});
