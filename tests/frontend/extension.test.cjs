const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const shared = require('../../extensions/dsa-coach/shared.js');

test('server settings cannot point at remote sites, credentials or paths', () => {
  assert.equal(shared.serverOrigin('http://localhost:8768/'), 'http://localhost:8768');
  for (const url of ['https://127.0.0.1:8765', 'http://evil.test', 'http://localhost.evil.test',
    'http://user:pass@localhost:8765', 'http://localhost:8765/api/map', 'http://localhost:8765/?foo=1']) {
    assert.throws(() => shared.serverOrigin(url));
  }
});

test('the extension asks for no access to the pages beside it', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '../../extensions/dsa-coach/manifest.json'), 'utf8'));
  assert.deepEqual(manifest.permissions, ['sidePanel', 'storage']);
  assert.deepEqual(manifest.host_permissions, ['http://127.0.0.1/*', 'http://localhost/*']);
  assert.equal(manifest.content_scripts, undefined);
  assert.equal(manifest.optional_host_permissions, undefined);
});
