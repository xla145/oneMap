import test from 'node:test';
import assert from 'node:assert/strict';
import {csvColumns, mappingValues, collectionStage} from '../frontend/operations-workflow.js';
import {operationSection, operationMenu} from '../frontend/operations-center.js';

test('CSV mapping preserves quoted commas, escaped quotes and CRLF headers',()=>{
  assert.deepEqual(csvColumns('\uFEFFid,"parcel,name","a""b",area\r\n1,x,2,3'),['id','parcel,name','a"b','area']);
  const form=entries=>({querySelectorAll:()=>entries.map(([name,value])=>({dataset:{mapField:name},value}))});
  assert.deepEqual(mappingValues(form([['id','编号'],['area','面积']])),{id:'编号',area:'面积'});
  assert.throws(()=>mappingValues(form([['id',''],['area','面积']])),/每个目标字段/);
  assert.throws(()=>mappingValues(form([['id','编号'],['area','编号']])),/不能重复/);
});

test('review approval and completed execution never imply data is ready for import',()=>{
  assert.equal(collectionStage({status:'待审核'}).step,1);
  const batch={status:'待质检',dataRevision:2};
  assert.equal(collectionStage({status:'已通过'},batch).step,2);
  const report={passed:true,dataRevision:2};
  assert.equal(collectionStage(null,batch,report).step,2);
  batch.status='待登记';
  assert.equal(collectionStage(null,batch,{passed:false,dataRevision:2}).step,2);
  assert.equal(collectionStage(null,batch,{passed:true,dataRevision:1}).step,2);
  assert.equal(collectionStage(null,batch,report,[{status:'待复核'}]).step,2);
  assert.equal(collectionStage(null,batch,report,[{status:'已办结'}]).step,3);
  batch.status='已入库';assert.equal(collectionStage(null,batch,report).step,4);
});

test('old detail routes still belong to one of the five daily navigation entries',()=>{
  assert.equal(operationMenu.length,5);
  for(const [route,section] of [['collection/orders','collection/tasks'],['quality/results','collection/tasks'],['quality/models','settings'],['warehouse/domains','settings'],['publishing/apis','catalog/assets'],['monitoring/inspections','monitoring/alerts'],['todos','overview']])assert.equal(operationSection(route),'operations/'+section);
});
