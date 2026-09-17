import {test} from 'node:test';
import assert from 'node:assert/strict';
import {featurePropertyRows} from '../frontend/feature-properties.js';
test('layer-specific fields retain zero, false and missing values',()=>{
 const rows=featurePropertyRows({id:'x',properties:{reserve:0,demo:false,quality:null,custom:'自定义'}});
 assert.equal(rows.find(r=>r.key==='reserve').value,'0');
 assert.equal(rows.find(r=>r.key==='demo').value,'否');
 assert.equal(rows.find(r=>r.key==='quality').value,'未登记');
 assert.equal(rows.find(r=>r.key==='custom').value,'自定义');
});
test('business fields are labeled and geometry and layer internals are excluded',()=>{
 const rows=featurePropertyRows({geometry:{type:'Point'},layer:{features:[]},properties:{geom:[1,2],c:[1,2],luClass:'耕地',ph:7}});
 assert.deepEqual(rows.map(r=>r.label),['土地利用类型','pH 值']);
});
