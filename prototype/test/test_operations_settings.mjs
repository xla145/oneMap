import test from 'node:test';
import assert from 'node:assert/strict';
import {configurationReadiness,modelReadiness,validateStandardFields} from '../frontend/operations-settings.js';

function fixture(){return {centers:{standards:[{status:'已发布'}],sources:[{id:'remote',kind:'PostgreSQL'}],rules:[{id:'r',enabled:true,rev:2}]},operations:{domains:[{sourceId:'remote'}],models:[{status:'已发布',published:{rules:[{id:'r',rev:1}]}}],alertRules:[{enabled:true,assigneeId:'disabled'}]},accounts:[{id:'disabled',enabled:false,role:'平台管理员'}]};}

test('readiness does not count registered external storage, stale models or disabled assignees as usable',()=>{
  const data=fixture(),result=Object.fromEntries(configurationReadiness(data).map(x=>[x.key,x.ready]));
  assert.deepEqual(result,{standards:true,models:false,domains:false,alertRules:false});
  data.centers.sources.push({id:'local',kind:'CSV文件'});data.operations.domains.push({sourceId:'local'});
  data.operations.models[0].published.rules[0].rev=2;
  data.accounts[0].enabled=true;
  assert.ok(configurationReadiness(data).every(x=>x.ready));
});

test('model draft preserves usable published snapshot, but changed or disabled rules invalidate readiness',()=>{
  const rules=[{id:'r',enabled:true,rev:2}],model={status:'草稿',published:{rules:[{id:'r',rev:2}]}};
  assert.match(modelReadiness(model,rules),/已发布版本可用/);
  assert.match(modelReadiness({...model,published:undefined},rules),/尚未发布/);
  rules[0].enabled=false;assert.match(modelReadiness(model,rules),/需重新发布/);
  assert.match(modelReadiness(model,[]),/需重新发布/);
});

test('visual field editor rejects duplicate/invalid names and empty schemas while preserving optional numeric fields',()=>{
  const field={name:'area',label:'面积',type:'number',required:false};
  assert.deepEqual(validateStandardFields([field]),[field]);
  assert.throws(()=>validateStandardFields([]),/1～100/);
  assert.throws(()=>validateStandardFields([field,field]),/重复/);
  assert.throws(()=>validateStandardFields([{...field,name:'1area'}]),/字段标识/);
  assert.throws(()=>validateStandardFields([{...field,label:''}]),/中文名称/);
});
