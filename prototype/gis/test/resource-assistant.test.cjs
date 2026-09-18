const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const {webcrypto}=require('node:crypto');

function setup(crypto=webcrypto){
 const events={},downloads=[],nodes={};
 let identity='u1';
 const state={messages:[],requests:[],region:'',active:new Set(),route:'map'};
 const ctx={state,crypto,Date,Set,FormData:class{constructor(form){this.form=form}get(name){return this.form.values[name]}},
  $:s=>nodes[s]||null,esc:s=>String(s??'').replaceAll('<','&lt;').replaceAll('>','&gt;'),
  NMG_GEO:{cities:{features:['呼和浩特市','包头市'].map(name=>({properties:{name}}))}},
  document:{addEventListener:(name,fn)=>events[name]=fn},
  requestDetail(){},showAI(){},log(){},stamp:()=> '2026-09-18',renderSidebar(){},
  selectRegion:r=>state.region=r,refreshMap(){},openTool(){},geometryFeature:f=>f,
  byId:{primeFarmland:{features:[{region:'呼和浩特市',id:'one'},{region:'包头市',id:'two'}]}},
  download:(...args)=>downloads.push(args)};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(require.resolve('../resource-assistant.js'),'utf8')+'\nglobalThis.copilot=ResourceCopilot;',ctx);
 const ai=ctx.copilot;ai.configure({render(){},identity:()=>identity});
 function click(action,value=''){events.click({target:{closest:()=>({dataset:{resourceAi:action,value}})}});}
 function fill(purpose='用于季度耕地监测',region='呼和浩特市',days='30'){
  const form={id:'resource-ai-form',values:{purpose,region,days},matches:()=>false};
  nodes['#resource-ai-form']=form;events.submit({target:form,preventDefault(){}});delete nodes['#resource-ai-form'];
 }
 return {ai,state,click,fill,downloads,events,setIdentity:v=>identity=v,token:()=>state.messages.findLast(m=>m.draftToken)?.draftToken};
}
test('resource search, tool bundle, region clarification and no-match preserve intent',()=>{
 const t=setup();
 assert.equal(t.ai.handle('找最近的地灾巡查记录表'),true);
 assert.match(t.ai.html(t.state.messages.at(-1)),/巡查时间/);
 t.click('export-patrol');assert.equal(JSON.parse(t.downloads[0][1]).rows.length,3);
 t.ai.handle('推荐合适的耕地监测工具');assert.equal(t.state.messages.at(-1).resources.length,2);
 t.ai.handle('调出某盟市永久基本农田图层');assert.equal(t.state.messages.at(-1).regionChoices,true);
 t.ai.handle('包头市');assert.match(t.state.messages.at(-1).text,/包头市/);
 t.ai.handle('查询 2000 年海洋保护区现场照片');assert.match(t.state.messages.at(-1).text,/未检索到/);
 assert.equal(t.ai.handle('查询呼和浩特市的永久基本农田'),false,'SQL questions go to query service');
});
test('applications require valid details and explicit confirmation; stale submit cannot duplicate',()=>{
 const t=setup();t.click('apply','satellite,field');const token=t.token();
 t.click('submit',token);assert.equal(t.state.requests.length,0);
 t.fill('短');t.click('submit',token);assert.equal(t.state.requests.length,0);
 t.fill();assert.equal(t.state.requests.length,0);
 t.click('submit',token);t.click('submit',token);
 assert.equal(t.state.requests.length,1);assert.equal(t.state.requests[0].resourceIds.length,2);
 assert.equal(t.state.requests[0].status,'待审核');
});
test('cancel and withdraw prevent granting; resubmit produces a fresh confirmation',()=>{
 const t=setup();t.click('apply','farmland');const token=t.token();
 t.click('cancel',token);t.click('submit',token);assert.equal(t.state.requests.length,0);
 t.click('apply','farmland');t.fill();t.click('submit',t.token());const r=t.state.requests[0];
 t.click('withdraw',r.id);assert.equal(r.status,'已撤回');
 t.setIdentity('admin');t.click('approve',r.id);assert.equal(r.status,'已撤回');
 t.click('reapply',r.id);assert.match(t.ai.html(t.state.messages.at(-1)),/用于季度耕地监测/);
 assert.equal(t.state.requests.length,1);
});
test('review requires explicit admin identity; downloads require unexpired matching grant and respect scope',()=>{
 const t=setup();t.click('apply','farmland');t.fill();t.click('submit',t.token());const r=t.state.requests[0];
 t.click('approve',r.id);assert.equal(r.status,'待审核');
 t.click('download',r.id+'|farmland');assert.equal(t.downloads.length,0);
 t.setIdentity('admin');t.click('approve',r.id);assert.equal(r.status,'已通过');
 t.click('download',r.id+'|farmland');assert.equal(JSON.parse(t.downloads[0][1]).features.length,1);
 t.click('download',r.id+'|patrol');assert.equal(t.downloads.length,1);
 r.expires=Date.now()-1;t.click('download',r.id+'|farmland');assert.equal(t.downloads.length,1);
});
test('reject records review and allows revised application without overwriting original',()=>{
 const t=setup();t.click('apply','field');t.fill();t.click('submit',t.token());const r=t.state.requests[0];
 const form={id:'',dataset:{requestId:r.id},values:{review:'请补充外业核查范围'},matches:()=>true};
 t.events.submit({target:form,preventDefault(){}});assert.equal(r.status,'待审核');
 t.setIdentity('admin');t.events.submit({target:form,preventDefault(){}});
 assert.equal(r.status,'已退回');assert.equal(r.review,'请补充外业核查范围');
 t.click('reapply',r.id);t.fill('用于指定范围的外业复核');t.click('submit',t.token());
 assert.equal(t.state.requests.length,2);assert.equal(r.status,'已退回');assert.equal(t.state.requests[1].status,'待审核');
});
test('historical resource card keeps its region and patrol grants do not export outside scope',()=>{
 const t=setup();t.click('region','呼和浩特市');
 const first=t.state.messages.at(-1);
 t.click('region','包头市');
 assert.ok(t.ai.html(first).includes('farmland|呼和浩特市'));
 t.click('apply','patrol|包头市');t.fill('用于本市地灾巡查','包头市');t.click('submit',t.token());
 const r=t.state.requests[0];t.setIdentity('admin');t.click('approve',r.id);t.click('download',r.id+'|patrol');
 assert.equal(JSON.parse(t.downloads[0][1]).rows.length,0);
});

test('HTTP without crypto.randomUUID supports application draft, submission and unique IDs',()=>{
 const t=setup({getRandomValues:array=>webcrypto.getRandomValues(array)});
 const tokens=new Set(),ids=new Set();
 for(let i=0;i<10;i++){
  t.click('apply','patrol');const token=t.token();
  assert.match(token,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  tokens.add(token);t.fill();t.click('submit',token);ids.add(t.state.requests.at(-1).id);
 }
 assert.equal(t.state.requests.length,10);assert.equal(tokens.size,10);assert.equal(ids.size,10);
});
