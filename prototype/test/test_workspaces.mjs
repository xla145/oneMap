import assert from 'node:assert/strict';
import {periodMatches,selectCases,summarize,layerTree} from '../frontend/workspaces.js';
const now=new Date('2026-09-15T12:00:00');
assert.equal(periodMatches('2026-09-02T00:00:00','近14天',now),true);
assert.equal(periodMatches('2026-09-01T23:59:59','近14天',now),false);
assert.equal(periodMatches('2026-08-31T23:59:59','上月',now),true);
assert.equal(periodMatches('2026-09-01T00:00:00','上月',now),false);
const base={projectId:'p1',category:'业务审批',name:'项目',formData:{area:20},workflow:{nodes:[{name:'复核'}]},nodeIndex:0,compliance:'合规',isTodo:false};
const cases=[{...base,id:'a',createdAt:'2026-08-01',completedAt:'2026-09-14',dueAt:'2026-09-15',status:'已办结'},
 {...base,id:'b',createdAt:'2026-09-10',completedAt:null,status:'在办',isTodo:true}];
const filters={dateBasis:'completedAt',timeWindow:'近7天',category:'全部',status:'全部',compliance:'全部',query:''};
assert.deepEqual(selectCases(cases,filters,now).map(c=>c.id),['a']);
assert.deepEqual(selectCases(cases,{...filters,dateBasis:'createdAt'},now).map(c=>c.id),['b']);
const result=summarize(cases);assert.equal(result.projects,1);assert.equal(result.area,40);assert.equal(result.todo,1);assert.equal(result.ontime,1);
const tree=layerTree([{id:'x',name:'layer',group:'根/子/叶',access:'已授权',visible:true}],{esc:x=>x,btn:()=>''});
assert.equal((tree.match(/<details/g)||[]).length,3);assert.ok(tree.includes('data-layer-group="x"'));
console.log('Workspace checks passed: period boundaries, completion dates, shared projects, todo totals, recursive tree.');
