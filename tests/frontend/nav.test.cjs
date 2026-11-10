const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function load() {
  const c = vm.createContext({document: {addEventListener() {}}, window: {addEventListener() {}}, location: {hash: ''}});
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../app/static/nav.js'), 'utf8'), c);
  return (code) => vm.runInContext(code, c);
}

test('routes default to Today, and an old Solve link lands there too', () => {
  const run = load();
  assert.deepEqual({...run(`route('')`)}, {view: 'today', key: ''});
  assert.deepEqual({...run(`route('#/map')`)}, {view: 'map', key: ''});
  assert.deepEqual({...run(`route('#/learn/stack')`)}, {view: 'learn', key: 'stack'});
  assert.deepEqual({...run(`route('#/solve')`)}, {view: 'today', key: ''});
});

test('weeks come in order and keep roadmap order inside a week', () => {
  const run = load();
  const weeks = run(`byWeek([{key:'a',week:2},{key:'b',week:1},{key:'c',week:2}])`);
  assert.deepEqual(JSON.parse(JSON.stringify(weeks)), [[1, [{key: 'b', week: 1}]], [2, [{key: 'a', week: 2}, {key: 'c', week: 2}]]]);
});

test('list progress reads as done/total, and nothing for an empty list', () => {
  const run = load();
  assert.equal(run(`listsText({blind75:{done:1,total:4}, nc150:{done:2,total:6}})`), 'Blind 75 1/4 · NeetCode 150 2/6');
  assert.equal(run(`listsText({blind75:{done:0,total:0}, nc150:{done:0,total:3}})`), 'NeetCode 150 0/3');
  assert.equal(run(`statusLabel('practicing')`), 'Practising');
});

test('explainer prompts name the pattern, the file and the feedback', () => {
  const run = load();
  const p = `({key: 'stack', name: 'Stack', explainer: 'concepts/stack/stack-derived.html'})`;
  assert.match(run(`explainerPrompt(${p})`), /Write the interactive explainer for Stack \(stack\).*artifact add --concept stack/);
  assert.match(run(`explainerPrompt(${p}, 'show equal heights')`),
    /Revise .* at notebook\/concepts\/stack\/stack-derived\.html.*"show equal heights"/);
});
