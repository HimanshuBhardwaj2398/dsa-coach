const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const shared = require('../../extensions/dsa-coach/shared.js');

test('problem context accepts exact LeetCode origin and problem paths only', () => {
  assert.equal(shared.problemSlug('https://leetcode.com/problems/two-sum/description/?x=1'), 'two-sum');
  for (const url of ['https://leetcode.com.evil.test/problems/two-sum', 'http://leetcode.com/problems/two-sum',
    'https://leetcode.com/discuss/two-sum', 'https://leetcode.com/problems/%2e%2e', 'invalid', null]) {
    assert.equal(shared.problemSlug(url), null);
  }
});

test('server settings cannot point at remote sites, credentials or paths', () => {
  assert.equal(shared.serverOrigin('http://localhost:8768/'), 'http://localhost:8768');
  for (const url of ['https://127.0.0.1:8765', 'http://evil.test', 'http://localhost.evil.test',
    'http://user:pass@localhost:8765', 'http://localhost:8765/api/run', 'http://localhost:8765/?foo=1']) {
    assert.throws(() => shared.serverOrigin(url));
  }
});

test('opening from an app link preserves the user gesture and rejects other senders', async () => {
  const calls = [];
  let listener;
  const context = vm.createContext({URL, console, importScripts() {}, CoachExtension: shared,
    chrome: {
      sidePanel: {setPanelBehavior: async () => {}, open: options => {calls.push(['open', options.windowId]); return Promise.resolve();}},
      storage: {local: {set: async value => {calls.push(['store', value.server]);}}},
      runtime: {onMessage: {addListener: callback => {listener = callback;}}},
    }});
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../extensions/dsa-coach/background.js'), 'utf8'), context);
  const message = {type: 'dsa-coach:open', url: 'https://leetcode.com/problems/two-sum/'};
  listener(message, {tab: {windowId: 7}, url: 'https://evil.test'}, () => {});
  assert.equal(calls.length, 0);
  let reply;
  assert.equal(listener(message, {tab: {windowId: 7}, url: 'http://localhost:8768/'}, value => {reply = value;}), true);
  assert.deepEqual(calls, [['open', 7]]); // no await before open()
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, [['open', 7], ['store', 'http://localhost:8768']]);
  assert.equal(reply.ok, true);
});
