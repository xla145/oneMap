/* Conversational resource catalog and application workflow for the local prototype. */
const ResourceCopilot=(()=>{
 // randomUUID requires HTTPS; getRandomValues also works on HTTP demo sites.
 function resourceUUID(){
  if(typeof globalThis.crypto?.randomUUID==='function')return globalThis.crypto.randomUUID();
  const bytes=globalThis.crypto.getRandomValues(new Uint8Array(16));
  bytes[6]=(bytes[6]&0x0f)|0x40;bytes[8]=(bytes[8]&0x3f)|0x80;
  const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
  return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
 }
 const catalog=[
  {id:'patrol',name:'地灾巡查记录表',type:'数据库业务表',fields:'巡查编号、巡查地点、灾害类型、巡查时间、坐标、隐患等级、巡查人',crs:'CGCS2000',frequency:'按巡查实时上报',purpose:'查询地质灾害现场巡查记录与隐患情况',access:'可导出示例'},
  {id:'satellite',name:'耕地卫片比对监测工具',type:'工具服务',purpose:'卫星影像比对，识别耕地非农化、非粮化变化图斑',frequency:'季度更新影像',access:'需申请'},
  {id:'field',name:'耕地地块外业核查工具',type:'工具服务',purpose:'现场核查地块边界、种植情况',crs:'CGCS2000',frequency:'按外业核查实时上报',access:'需申请'},
  {id:'farmland',name:'永久基本农田保护图层',type:'图层服务',fields:'地块编号、地类、保护等级、权属、管控要求',crs:'CGCS2000',frequency:'年度更新',purpose:'查看永久基本农田空间分布和保护要求',access:'需申请'}
 ];
 const patrolRows=[
  {巡查编号:'XC-DEMO-003',巡查地点:'呼和浩特市示例巡查点三',灾害类型:'滑坡',巡查时间:'2026-09-18 09:30',坐标:'111.71,40.84',隐患等级:'中',巡查人:'示例巡查员甲'},
  {巡查编号:'XC-DEMO-002',巡查地点:'呼和浩特市示例巡查点二',灾害类型:'崩塌',巡查时间:'2026-09-17 14:20',坐标:'111.65,40.88',隐患等级:'低',巡查人:'示例巡查员乙'},
  {巡查编号:'XC-DEMO-001',巡查地点:'呼和浩特市示例巡查点一',灾害类型:'泥石流',巡查时间:'2026-09-16 10:00',坐标:'111.68,40.91',隐患等级:'低',巡查人:'示例巡查员丙'}
 ];
 let context=[],region='',draft=null,chooseRegion=false,render=()=>showAI(),getIdentity=()=> 'u1';
 const get=id=>catalog.find(r=>r.id===id);
 const regions=()=>NMG_GEO.cities.features.map(f=>f.properties.name);
 const btn=(label,action,value='')=>`<button type="button" data-resource-ai="${action}" data-value="${esc(value)}">${esc(label)}</button>`;
 function say(text,extra={}){state.messages.push({role:'assistant',text,resourceRegion:region,...extra});}
 function user(text){state.messages.push({role:'user',text});state.assistantDraft='';if($('#chat-input'))$('#chat-input').value='';}
 function status(r){return r.status==='已通过'&&Date.now()>r.expires?'已到期':r.status;}
 function card(id,asTable=false,cardRegion=''){const r=get(id);return `<section class="resource-ai-card"><div class="copilot-section-title"><strong>${esc(r.name)}${asTable?'业务数据表':''}</strong><span>原型示例</span></div><dl><dt>资源类型</dt><dd>${asTable?'数据库表':esc(r.type)}</dd>${r.fields?`<dt>核心字段${asTable?'（目录设计）':''}</dt><dd>${esc(asTable?'地块编码、行政区划、权属单位、保护等级、地块面积、管控要求':r.fields)}</dd>`:''}<dt>用途</dt><dd>${esc(r.purpose)}</dd>${r.crs?`<dt>坐标系</dt><dd>${esc(r.crs)}（目录设计口径）</dd>`:''}<dt>更新频次</dt><dd>${esc(r.frequency)}</dd><dt>使用权限</dt><dd>${esc(r.access)}</dd></dl><div class="copilot-actions">${id==='patrol'?btn('一键导出数据','export-patrol'):''}${id==='farmland'?btn('预览示例图层','preview',cardRegion):''}${btn('一键发起资源使用申请','apply',id+'|'+cardRegion)}</div></section>`;}
 function requestHTML(r){const s=status(r);return `<section class="resource-ai-card"><strong>${esc(r.resourceName)}</strong><dl><dt>申请编号</dt><dd>${esc(r.id)}</dd><dt>申请状态</dt><dd>${esc(s)}</dd><dt>用途</dt><dd>${esc(r.purpose)}</dd><dt>范围 / 期限</dt><dd>${esc(r.region||'全自治区')} / ${r.days} 天</dd>${r.review?`<dt>审核意见</dt><dd>${esc(r.review)}</dd>`:''}${r.expires?`<dt>有效期至</dt><dd>${esc(new Date(r.expires).toLocaleString('zh-CN'))}</dd>`:''}</dl><p class="copilot-note">${s==='待审核'?'已进入本地资源中心申请记录。待资源管理员审核，审核结果可在本对话刷新查看。':s==='已通过'?'可在有效期内下载已授权示例数据或打开工具演示。':s==='已退回'?'请参考审核意见修改用途，然后重新申请。':s==='已到期'?'使用期限已结束，请重新申请。':'本次申请已撤回，可调整后重新申请。'}</p><div class="copilot-actions">${btn('刷新进度','status',r.id)}${s==='待审核'?btn('撤回申请','withdraw',r.id):''}${s==='待审核'&&getIdentity()==='admin'?btn('演示审核通过','approve',r.id)+btn('填写退回意见','review',r.id):''}${s==='已通过'?btn('获取已授权资源','access',r.id):''}${['已退回','已撤回','已到期'].includes(s)?btn('修改后重新申请','reapply',r.id):''}</div></section>`;}
 function draftHTML(token){if(!draft||draft.token!==token)return '<p class="copilot-note">此申请草稿已结束，请查看后续消息。</p>';const d=draft;return `<section class="resource-ai-card"><strong>${d.confirm?'确认提交本次资源使用申请？':'请补充资源申请信息'}</strong><p>${esc(d.ids.map(id=>get(id).name).join('、'))}</p>${d.confirm?`<dl><dt>用途</dt><dd>${esc(d.purpose)}</dd><dt>范围</dt><dd>${esc(d.region||'全自治区')}</dd><dt>期限</dt><dd>${d.days} 天</dd></dl><div class="copilot-actions">${btn('确认提交','submit',d.token)}${btn('修改信息','edit',d.token)}${btn('取消','cancel',d.token)}</div>`:`<form id="resource-ai-form"><label class="field">申请用途<textarea name="purpose" required minlength="4" maxlength="500" placeholder="例如：用于耕地季度监测与现场核查">${esc(d.purpose)}</textarea></label><label class="field">行政区范围<select name="region"><option value="">全自治区</option>${regions().map(r=>`<option ${d.region===r?'selected':''}>${esc(r)}</option>`).join('')}</select></label><label class="field">使用期限<select name="days">${[7,30,90].map(n=>`<option value="${n}" ${d.days===n?'selected':''}>${n} 天</option>`).join('')}</select></label><div class="copilot-actions"><button type="submit">下一步：核对申请</button>${btn('取消','cancel',d.token)}</div></form>`}<p class="copilot-note">本地流程演示；确认后保存到当前浏览器资源中心，不发送生产审批。</p></section>`;}
 function html(m){let out='';if(m.resources)out+=m.resources.map(id=>card(id,m.asTable,m.resourceRegion)).join('');if(m.bundle)out+=`<div class="copilot-actions">${btn('一键发起一揽子资源申请','apply',m.resources.join(',')+'|'+(m.resourceRegion||''))}</div>`;if(m.regionChoices)out+=`<div class="copilot-actions">${regions().map(r=>btn(r,'region',r)).join('')}${btn('全自治区','region','')}</div>`;if(m.draftToken)out+=draftHTML(m.draftToken);if(m.requestId){const r=state.requests.find(r=>r.id===m.requestId);if(r)out+=requestHTML(r);}if(m.reviewId)out+=`<form class="resource-ai-review" data-request-id="${esc(m.reviewId)}"><label class="field">退回意见<textarea name="review" required minlength="4" maxlength="500" placeholder="请说明需要补充的材料或用途"></textarea></label><div class="copilot-actions"><button type="submit">确认退回</button>${btn('取消退回','cancel-review',m.reviewId)}</div></form>`;return out;}
 function capture(){const f=$('#resource-ai-form');if(f&&draft&&!draft.confirm){const fd=new FormData(f);draft.purpose=String(fd.get('purpose'));draft.region=String(fd.get('region'));draft.days=Number(fd.get('days'));}}
 function begin(ids,prior){if(draft){say('您还有一份申请草稿，请先确认提交或取消，再发起其他申请。');return}const unique=[...new Set(ids)].filter(id=>get(id));if(!unique.length){say('请先检索并选择要申请的资源。');return}draft={token:resourceUUID(),ids:unique,region:prior?.region??region,purpose:prior?.purpose||'',days:prior?.days||30,confirm:false};say('已准备资源中心申请草稿。填写用途、范围和期限后，我会请您核对并确认提交。',{draftToken:draft.token});}
 function showStatus(id){const r=state.requests.find(r=>r.id===id&&r.resourceIds);if(r)say('以下是资源申请的最新进度。',{requestId:r.id});else say('未找到这条资源申请，请查看“我的申请”。');}
 function handle(q){
  if(draft&&/^(确认提交|提交|取消|取消申请|修改信息)$/.test(q)){user(q);action(q==='取消'||q==='取消申请'?'cancel':q==='修改信息'?'edit':'submit',draft.token);return true;}
  if(/^(我的申请|查看申请进度|查看进度|申请进度|刷新进度)$/.test(q)){user(q);const list=state.requests.filter(r=>r.resourceIds);if(!list.length)say('您还没有通过助手提交资源申请。请先检索资源，再点击申请。');else list.slice(-10).reverse().forEach(r=>showStatus(r.id));render();return true;}
  if(/(?:发起|申请|点击).*(?:资源使用申请|一揽子|资源申请)|^申请当前资源$/.test(q)){user(q);begin(context);render();return true;}
  if(chooseRegion&&regions().includes(q)){user(q);action('region',q);return true;}
  if(/地灾巡查|地质灾害巡查/.test(q)){user(q);context=['patrol'];region='';chooseRegion=false;say('已为您检索到匹配资源【地灾巡查记录表】。按巡查时间倒序整理了 3 条示例记录，最近一条为 2026-09-18 09:30。',{resources:context});render();return true;}
  if(/耕地/.test(q)&&/工具|服务推荐/.test(q)){user(q);context=['satellite','field'];region=state.region;chooseRegion=false;say('为您匹配到 2 项耕地监测工具服务。建议先用卫片比对发现变化，再开展外业核查；可单项申请或一揽子申请。',{resources:context,bundle:true});render();return true;}
  if(/永久基本农田|基本农田/.test(q)&&/图层|调出/.test(q)){user(q);context=['farmland'];region=regions().find(r=>q.includes(r))||state.region;chooseRegion=!region&&!/全区|全自治区/.test(q);if(chooseRegion)say('您想查看哪个盟市的永久基本农田图层？请选择范围，也可以直接输入盟市名称。',{regionChoices:true});else say(`检索到资源【永久基本农田保护图层】，范围：${region||'全自治区'}。可预览本地示例，正式使用需申请。`,{resources:context});render();return true;}
  if(/照片|海洋保护区|业务文档|记录表|推荐.*工具|检索.*资源|找.*资源/.test(q)){user(q);context=[];chooseRegion=false;say('当前资源库未检索到匹配资源。您可以调整查询条件，支持查询数据库表、图层服务、工具服务、业务文档。当前原型目录可演示：地灾巡查记录表、耕地监测工具、永久基本农田图层。');render();return true;}
  return false;
 }
 function action(a,v){capture();const r=state.requests.find(r=>r.id===v&&r.resourceIds);
  if(a==='apply'){const [ids,scope]=v.split('|');begin(ids.split(','),scope===undefined?undefined:{region:scope});}
  if(a==='region'){if(v&&!regions().includes(v))return;region=v;chooseRegion=false;context=['farmland'];say(`检索到资源【永久基本农田保护图层】，范围：${v||'全自治区'}。`,{resources:context});}
  if(a==='preview'){selectRegion(v);state.active.add('primeFarmland');refreshMap();say(`已在地图预览${v||'全自治区'}永久基本农田示例图层。预览使用现有演示几何，不作为真实 CGCS2000 测绘成果。`);}
  if(a==='cancel'&&draft?.token===v){draft=null;say('已取消本次申请，未生成申请记录。您可以继续检索其他资源。');}
  if(a==='edit'&&draft?.token===v)draft.confirm=false;
  if(a==='submit'&&draft?.token===v){if(!draft.confirm){say('请先填写申请信息，并点击“下一步：核对申请”。');}else{const d=draft;const request={id:'REQ-'+resourceUUID().slice(0,8).toUpperCase(),layer:'copilot:'+d.ids.join(','),resourceName:d.ids.map(id=>get(id).name).join('、'),resourceIds:d.ids,region:d.region,purpose:d.purpose,days:d.days,status:'待审核',time:stamp()};state.requests.push(request);log('助手提交资源申请 '+request.id);draft=null;say('申请已提交到本地资源中心，当前状态为“待审核”。您可以刷新进度或撤回申请。演示审核请在上方切换为演示管理员，再输入“我的申请”。',{requestId:request.id});if(state.route==='resources'||state.route==='tasks')renderSidebar();}}
  if(a==='status')showStatus(v);
  if(a==='withdraw'&&r?.status==='待审核'){r.status='已撤回';log('撤回 '+r.id);say('已撤回申请，未产生使用授权。',{requestId:r.id});}
  if(a==='reapply'&&r&&['已退回','已撤回','已到期'].includes(status(r)))begin(r.resourceIds,r);
  if(a==='approve'||a==='review'){if(getIdentity()!=='admin'){say('请在上方显式切换为演示管理员，才能进行本地审核。');}else if(r?.status==='待审核'){if(a==='review'){state.messages.forEach(m=>{if(m.reviewId===r.id)delete m.reviewId;});say('请填写退回原因，申请人可据此修改后重提。',{reviewId:r.id});}else{r.status='已通过';r.review='本地演示审核通过';r.expires=Date.now()+r.days*86400000;log('演示审核通过 '+r.id);say('申请已通过。可在授权期限内获取资源。',{requestId:r.id});}}}
  if(a==='cancel-review')state.messages.forEach(m=>{if(m.reviewId===v)delete m.reviewId;});
  if(a==='access'&&r){if(status(r)!=='已通过')say('该申请尚未通过或已到期，请先完成审批或重新申请。');else{say('请选择已授权资源的后续操作。');const m=state.messages.at(-1);m.accessId=r.id;}}
  if(a==='export-patrol')exportPatrol();
  if(a==='download'||a==='tool'){const [requestId,id]=v.split('|');const grant=state.requests.find(x=>x.id===requestId&&x.resourceIds?.includes(id));if(!grant||status(grant)!=='已通过'){say('授权已失效，请刷新申请状态。');}else if(id==='patrol'){exportPatrol(grant.region);}else if(id==='farmland'){const fs=byId.primeFarmland.features.filter(f=>!grant.region||f.region===grant.region);download('永久基本农田-授权示例.geojson',JSON.stringify({type:'FeatureCollection',notice:'本地演示数据，不作为真实测绘成果',features:fs.map(geometryFeature)},null,2),'application/geo+json');say(`已导出授权范围内 ${fs.length} 个示例对象。`);}else{openTool(id==='satellite'?'compare':'query');say(id==='satellite'?'已打开图层卷帘对照演示。可拖动分隔线查看图层差异；卫星影像自动变化识别服务待接入。':'已打开空间范围查询演示。请绘制核查地块，再通过“创建核查任务”填写任务；移动外业采集服务待接入。');}}
  render();
 }
 function exportPatrol(scope=''){const rows=patrolRows.filter(r=>!scope||r.巡查地点.startsWith(scope));download('地灾巡查记录表-示例.json',JSON.stringify({notice:'完全虚构的原型示例记录；按巡查时间倒序',coordinateSystem:'CGCS2000（示例目录口径）',region:scope||'全自治区',rows},null,2));say(`已导出 ${rows.length} 条示例巡查记录，按巡查时间倒序排列，包含巡查编号、地点、灾害类型、时间、坐标、隐患等级和巡查人。`);}
 function accessHTML(m){const r=state.requests.find(r=>r.id===m.accessId);if(!r||status(r)!=='已通过')return '';return `<div class="copilot-actions">${r.resourceIds.map(id=>btn(get(id).type==='工具服务'?'打开'+get(id).name+'演示':'下载'+get(id).name,id==='satellite'||id==='field'?'tool':'download',r.id+'|'+id)).join('')}</div>`;}
 document.addEventListener('click',e=>{const b=e.target.closest('[data-resource-ai]');if(b)action(b.dataset.resourceAi,b.dataset.value);});
 document.addEventListener('submit',e=>{if(e.target.id==='resource-ai-form'){e.preventDefault();capture();if(!draft||draft.purpose.trim().length<4||draft.purpose.length>500||![7,30,90].includes(draft.days)||draft.region&&!regions().includes(draft.region))return;draft.purpose=draft.purpose.trim();draft.confirm=true;render();}if(e.target.matches('.resource-ai-review')){e.preventDefault();const r=state.requests.find(r=>r.id===e.target.dataset.requestId&&r.resourceIds);const review=String(new FormData(e.target).get('review')).trim();if(getIdentity()!=='admin'||r?.status!=='待审核'||review.length<4||review.length>500)return;r.status='已退回';r.review=review;log('演示退回 '+r.id);state.messages.forEach(m=>{if(m.reviewId===r.id)delete m.reviewId;});say('申请已退回，审核意见已记录。可修改后重新申请。',{requestId:r.id});render();}});
 const oldRequestDetail=requestDetail;
 requestDetail=function(id,admin=false){const r=state.requests.find(r=>r.id===id);if(!r?.resourceIds)return oldRequestDetail(id,admin);showStatus(id);showAI();};
 return {configure(o){render=o.render;getIdentity=o.identity;},handle,html:m=>html(m)+accessHTML(m),capture,reset(){draft=null;context=[];region='';chooseRegion=false;},sqlMetadata(){context=['farmland'];say('已检索到目标资源：永久基本农田保护图层业务数据表。正在解析查询条件，生成并执行本地查询 SQL。',{resources:['farmland'],asTable:true});}};
})();
