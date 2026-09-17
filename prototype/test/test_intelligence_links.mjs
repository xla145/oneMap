import assert from 'node:assert/strict';
import {assetGraph,references,indexState,onlineSnapshot} from '../frontend/intelligence-links.js';
const asset=(id,fields={})=>{const row={id,name:id,status:'已发布',version:1,...fields};return {...row,published:{...row}};};
const resource=asset('r1'), other=asset('r2');
const agent=asset('a1',{steps:'检索资源\n展示结果',resourceIds:'r1',templateIds:'c1'});
const data={resources:[resource,other],agents:[agent],knowledge:[],corpora:[asset('c1')],indicators:[],platform:{apps:[{...asset('app1',{type:'agent',targetId:'a1'}),listed:true}]}};
// A new draft must not erase the relationships still used by an online application.
agent.status='草稿';agent.resourceIds='r2';
assert.ok(assetGraph(data).edges.some(e=>e.from==='agents:a1'&&e.to==='resources:r1'));
assert.ok(!assetGraph(data).edges.some(e=>e.from==='agents:a1'&&e.to==='resources:r2'));
assert.ok(assetGraph(data,'draft').edges.some(e=>e.from==='agents:a1'&&e.to==='resources:r2'));
assert.deepEqual(references(assetGraph(data),'resources:r1').indirect.map(r=>r.key),['apps:app1']);
// Dynamic authorization scopes are potential references, never actual invocations.
agent.published.resourceIds='';
assert.equal(assetGraph(data).edges.find(e=>e.to==='resources:r2').potential,true);
other.status='已停用';
assert.ok(!assetGraph(data).edges.some(e=>e.to==='resources:r2'));
// Missing explicit targets remain visible for diagnosis.
agent.published.resourceIds='missing';
assert.ok(assetGraph(data).edges.some(e=>e.to==='resources:missing'));
// Portal and AI channel state are independent, even after raw document state changes.
const doc=asset('k1');doc.channels={portal:{version:2},index:{version:1}};doc.version=2;doc.status='已停用';
assert.equal(indexState(doc).enabled,true);assert.equal(indexState(doc).pending,true);
assert.equal(onlineSnapshot('knowledge',doc,'portal').version,2);
doc.channels.index=null;assert.equal(indexState(doc).enabled,false);
// Cycles terminate and report each indirectly affected object once.
data.indicators=[asset('i1',{dataMode:'composite',expression:'i2 + 1'}),asset('i2',{dataMode:'composite',expression:'i1 + 2'})];
assert.equal(references(assetGraph(data),'indicators:i1').incoming.length,1);
assert.equal(references(assetGraph(data),'indicators:i1').indirect.length,0);
// Inactive applications keep their draft reference, but have no online edge.
data.platform.apps[0].listed=false;
assert.ok(!assetGraph(data).edges.some(e=>e.from==='apps:app1'));
assert.ok(assetGraph(data,'draft').edges.some(e=>e.from==='apps:app1'));
// A published scene application may retain different bindings from its scene source.
data.platform.apps=[{...asset('map',{type:'scene',targetId:'scene1',targetSnapshot:{config:{layers:[{resourceId:'old-layer'}],widgets:[{params:{agentId:'old-agent'}}]}}}),listed:true}];
assert.ok(assetGraph(data).edges.some(e=>e.from==='apps:map'&&e.to==='agents:old-agent'));
// Legacy manual indicators still validate their associated table at runtime.
data.indicators.push(asset('manual',{resourceId:'r1'}));
assert.ok(assetGraph(data).edges.some(e=>e.from==='indicators:manual'&&e.to==='resources:r1'));
console.log('Intelligence dependency checks passed: draft isolation, channels, dynamic scope, missing targets, cycles, app snapshots and manual indicators.');
