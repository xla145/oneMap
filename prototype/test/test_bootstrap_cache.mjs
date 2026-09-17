import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createBootstrapCache} from '../frontend/bootstrap-cache.js';

test('navigation and concurrent requests reuse data; consumers cannot mutate cache', async () => {
  const cache = createBootstrapCache(); let calls = 0;
  const fetcher = async () => {calls++; return {user: {id: 'admin'}};};
  const [a,b] = await Promise.all([cache.get('admin', fetcher),cache.get('admin', fetcher)]);
  a.user.id = 'edited';
  assert.equal(b.user.id, 'admin');
  assert.equal((await cache.get('admin',fetcher)).user.id,'admin');
  assert.equal(calls,1);
});
test('TTL, explicit refresh, identity and mode have independent lifecycles', async () => {
  let clock=0,calls=0; const cache=createBootstrapCache({now:()=>clock});
  const fetcher=async()=>({version:++calls});
  await cache.get('admin/admin',fetcher);
  clock=29999;await cache.get('admin/admin',fetcher);assert.equal(calls,1);
  clock=30000;await cache.get('admin/admin',fetcher);assert.equal(calls,2);
  await cache.get('admin/admin',fetcher,{force:true});assert.equal(calls,3);
  await cache.get('u1/admin',fetcher);await cache.get('admin/front',fetcher);assert.equal(calls,5);
  cache.invalidate();await cache.get('admin/admin',fetcher);assert.equal(calls,6);
});
test('failed requests can retry', async () => {
  const cache=createBootstrapCache();
  await assert.rejects(cache.get('u1',()=>Promise.reject(Error('offline'))));
  assert.equal(await cache.get('u1',async()=>42),42);
});
test('an old in-flight response cannot repopulate an invalidated cache', async () => {
  const cache=createBootstrapCache();let resolve;
  const old=cache.get('admin',()=>new Promise(r=>resolve=r));
  await Promise.resolve();cache.invalidate();
  assert.equal(await cache.get('admin',async()=>2),2);
  resolve(1);await old;
  assert.equal(await cache.get('admin',async()=>3),2);
});
