/* GIS copilot: use the existing permission-scoped query service and Leaflet map. */
(()=>{
 const legacyAsk=ask;
 let busy=false,epoch=0,previous='',contextKey='',mode='demo',identity='u1',expanded=false;
 let result=null,resultLayer=null,scopeLayer=null,phase='',error='',controller=null;
 const button=(label,action,value='')=>`<button type="button" data-copilot="${action}" data-value="${esc(value)}">${esc(label)}</button>`;
 const snapshot=()=>JSON.stringify([state.region,state.scene,[...state.active].sort(),state.selected?.id,state.drawGeometry,identity,mode]);
 const numeric=n=>Number(n||0).toLocaleString('zh-CN',{maximumFractionDigits:2});
 async function api(op,payload={},signal){
  const response=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Demo-User':identity},body:JSON.stringify({action:'integration.ai.'+op,payload}),signal});
  const raw=await response.text();let data;try{data=JSON.parse(raw)}catch{throw Error('问数需要启动 Python 服务；静态预览仍可使用图层、量算和任务操作。')}
  if(!response.ok)throw Error(response.status===403?(data.error+'。原型演示可在上方显式切换为演示管理员；正式账号需由后台授权。'):(data.error||'请求失败'));return data;
 }
 function stop(){epoch++;controller?.abort();controller=null;busy=false;}
 function reset(){stop();ResourceCopilot.reset();previous='';contextKey='';state.messages=[];state.aiRows=null;state.assistantDraft='';if($('#chat-input'))$('#chat-input').value='';result=null;phase='';error='';}
 function featureFor(f){const p=f.properties;return {id:p.fid, name:p.name,layerId:p.layer_id.replace(/^nmg:/,''),layerName:p.layer_name,region:p.region,county:p.county,area:p.area_ha,unit:'公顷',geometry:f.geometry,properties:{year:p.year,approval:p.approval}};}
 function selectResult(fid){const f=result?.mapResult.features.find(x=>x.properties.fid===fid);if(!f){toast('该对象没有可定位几何');return}const item=featureFor(f);state.active.add(item.layerId);refreshMap();selectFeature(item);map.fitBounds(L.geoJSON(f).getBounds(),{padding:[70,70],maxZoom:11});}
 function paint(r){
  if(resultLayer)map.removeLayer(resultLayer);if(scopeLayer)map.removeLayer(scopeLayer);
  resultLayer=L.geoJSON(r.mapResult,{style:{color:'#7852b0',weight:3,fillOpacity:.22},pointToLayer:(f,ll)=>L.circleMarker(ll,{radius:7,color:'#7852b0',weight:2,fillOpacity:.7}),onEachFeature:(f,l)=>{l.bindTooltip(esc(f.properties.name));l.on('click',()=>selectResult(f.properties.fid))}}).addTo(map);
  scopeLayer=r.scope?L.geoJSON(r.scope,{interactive:false,style:{color:'#7852b0',dashArray:'6 5',weight:2,fillOpacity:.05}}).addTo(map):null;
  if(r.loaded||scopeLayer)map.fitBounds((r.loaded?resultLayer:scopeLayer).getBounds(),{paddingTopLeft:[35,80],paddingBottomRight:[innerWidth>680?(expanded?600:440):35,70],maxZoom:10});
 }
 function resultsHTML(){
  if(!result)return '';const r=result,max=Math.max(1,...r.statistics.map(x=>x.count));
  return `<section class="copilot-result"><div class="copilot-section-title"><strong>最近成功查询结果</strong><span>${esc(r.mode)}</span></div><p class="copilot-note">${esc(r.question)}</p><div class="copilot-chips">${r.interpretedFilters.map(x=>`<span>${esc(x.replace(/nmg:([A-Za-z]+)/g,(_,id)=>byId[id]?.name||id).replace('图层标识','图层'))}</span>`).join('')||'<span>全部授权示例数据</span>'}${r.scope?'<span>已应用空间范围</span>':''}</div><div class="copilot-metrics"><div><b>${numeric(r.total)}</b><small>匹配对象</small></div><div><b>${numeric(r.areaHa)}</b><small>登记面积 / 公顷</small></div><div><b>${r.statistics.length||'—'}</b><small>统计分组</small></div></div>
  ${r.statistics.length?`<div class="copilot-chart" aria-label="按分组统计对象数量">${r.statistics.map(g=>`<div><span>${esc(g.name||'未登记')}</span><i><em style="width:${g.count/max*100}%"></em></i><b>${g.count} 个</b><small>${numeric(g.areaHa)} 公顷</small></div>`).join('')}</div>`:''}
  <div class="copilot-actions">${button('地图定位','fit')}${button('清除结果图层','clear-map')}${button('导出本页','export')}</div><p class="copilot-note">总计 ${r.total} 个 · 地图显示当前页 ${r.loaded} 个 · 第 ${r.page}/${Math.max(1,Math.ceil(r.total/r.pageSize))} 页</p>
  <div class="copilot-table"><table><thead><tr><th>对象 / 地区</th><th>登记面积（公顷）</th><th>状态</th></tr></thead><tbody>${r.rows.map(row=>`<tr><td>${button(row.name,'locate',row.fid)}<small>${esc(row.county||row.region)}</small></td><td>${row.area_ha==null?'—':numeric(row.area_ha)}</td><td>${esc(row.approval||'未登记')}</td></tr>`).join('')||'<tr><td colspan="3">没有符合条件的对象。请修改地区或筛选条件。</td></tr>'}</tbody></table></div>
  <div class="copilot-actions">${r.page>1?button('上一页','page',r.page-1):''}${r.page*r.pageSize<r.total?button('下一页','page',r.page+1):''}</div>
  <details class="copilot-evidence" open><summary>查询依据 · SQL与数据来源</summary><pre>${esc(r.sql)}</pre><p>参数：${esc(JSON.stringify(r.parameters))}</p><p>SQL执行：${r.durationMs} ms · 来源：${esc(r.sources.map(s=>s.name).join('、')||'当前授权示例场景')}</p>${r.warnings.map(w=>`<p>${esc(w)}</p>`).join('')}</details>
  <div class="copilot-actions copilot-followups">${button('按旗县统计','prompt','按旗县统计')}${button('面积超过100亩','prompt','只看面积超过100亩的')}${button('创建核查任务','prompt','创建核查任务')}</div></section>`;
 }
 showAI=function(){
  ResourceCopilot.capture();
  state.assistantDraft=$('#chat-input')?.value??state.assistantDraft??'';state.assistantOpen=true;
  const dock=$('#assistant-dock');dock.hidden=false;dock.classList.add('copilot-dock');dock.classList.toggle('expanded',expanded);
  dock.innerHTML=`<header class="copilot-header"><div><small>SPATIAL INTELLIGENCE</small><h2>AI 空间助手 <span>示例数据</span></h2></div><div>${button(expanded?'收窄':'展开','expand')}${button('关闭','close')}</div></header><div class="copilot-settings"><label>运行模式<select id="copilot-mode"><option value="demo">演示规则模式</option><option value="model">AI模型模式</option></select></label><label>演示身份<select id="copilot-user"><option value="u1">业务用户</option><option value="admin">演示管理员</option></select></label></div><div id="assistant-context" class="assistant-context"></div><div class="copilot-body"><div class="copilot-welcome"><h3>从一个问题，找到空间答案</h3><p>检索资源、推荐工具、查询数据，并在对话中申请使用。资源目录与审批为本地示例；问数执行本地 SQL，AI 模式需配置模型服务。</p><div class="copilot-actions">${button('查询基本农田','prompt','查询呼和浩特市的永久基本农田')}${button('找巡查记录','prompt','找最近的地灾巡查记录表')}${button('推荐监测工具','prompt','推荐合适的耕地监测工具')}${button('调出农田图层','prompt','调出某盟市永久基本农田图层')}${button('我的申请','prompt','我的申请')}${button('分析当前范围','prompt','查询范围内的永久基本农田')}${button('选中对象周边','prompt','查询选中对象周边10公里的地质灾害隐患点')}</div></div><div id="chat-messages">${state.messages.map(m=>`<div class="chat-message ${m.role}"><small>${m.role==='user'?'我的问题':'处理结果'}</small>${esc(m.text).replace(/\n/g,'<br>')}${ResourceCopilot.html(m)}</div>`).join('')}</div><div class="copilot-progress" role="status">${esc(phase)}${busy?button('停止等待','stop'):''}</div>${error?`<div class="copilot-error" role="alert">${esc(error)}${mode==='model'?button('切换演示模式','demo'):''}</div>`:''}${resultsHTML()}</div><form id="chat-form" class="chat-composer"><textarea id="chat-input" maxlength="1000" aria-label="输入地图查询问题" placeholder="例如：查询基本农田，按旗县统计…"></textarea><div>${button('新会话','new')}<span>${busy?'查询进行中':'文字 → 查询 → 整理 → 上图'}</span><button type="submit" class="primary" ${busy?'disabled':''}>发送 ↗</button></div></form>`;
  $('#chat-input').value=state.assistantDraft;$('#copilot-mode').value=mode;$('#copilot-user').value=identity;updateAssistantContext();$('#assistant-trigger').setAttribute('aria-expanded','true');
  if(phase)requestAnimationFrame(()=>{if(state.assistantOpen)$('#assistant-dock .copilot-progress')?.scrollIntoView({block:'start'});});
 };
 const localCommand=q=>/^(?:请)?(?:叠加|加载|显示图层|隐藏|移除|关闭)/.test(q)||/(?:创建|新建|发起).*(?:核查|任务)|申请.*(?:数据|资源|图层)|申请当前|(?:打开|进入|切换).*(?:场景|大管家|矿业|耕地|规划|要素)|(?:打开|开始|进行).*(?:量算|测量)|测量面积|测量距离/.test(q);
 ask=async function(question){
  const q=question.trim();if(!q||busy)return;
  if(ResourceCopilot.handle(q)){previous='';contextKey='';result=null;phase='';error='';showAI();requestAnimationFrame(()=>{const body=$('#assistant-dock .copilot-body');if(body)body.scrollTop=body.scrollHeight;});return}
  if(localCommand(q)){if($('#chat-input'))$('#chat-input').value='';if(/核查|任务/.test(q)&&result?.scope)state.drawGeometry=result.scope;phase='已执行地图 / 业务操作';error='';legacyAsk(q);return}
  let geometry=null;
  if(/周边|选中对象/.test(q)){if(!state.selected){error='请先在地图或查询结果中选择一个对象，再分析周边。';showAI();return}geometry=state.selected.geometry;}
  else if(/范围|选区/.test(q)){geometry=state.drawGeometry;if(!geometry){error='请先使用范围查询工具绘制多边形，再提问。';showAI();openTool('query');return}}
  // Preserve the previous spatial scope for follow-up filters, unless map context changed.
  const key=snapshot();if(key!==contextKey){previous='';contextKey=key}
  if(!geometry&&previous)geometry=result?.scope||null;
  const context={sceneId:'nmg-reference-demo',region:state.region,...(geometry?{geometry}:{})};
  if(previous&&result?.context.layerIds)context.layerIds=[...result.context.layerIds];
  if(geometry&&!matchAssistantLayers(q).length&&!previous){context.layerIds=[...state.active].map(id=>'nmg:'+id);if(!context.layerIds.length){error='请先加载一个图层再做范围分析。';showAI();return}}
  const query=/^(分析当前范围|查询当前范围|查询选区|分析选区)$/.test(q)?'查询范围内全部对象':geometry?q.replace(/^分析/,'查询'):q;
  state.assistantDraft='';if($('#chat-input'))$('#chat-input').value='';state.messages.push({role:'user',text:q});if(/永久基本农田|基本农田/.test(q))ResourceCopilot.sqlMetadata();busy=true;error='';phase='正在理解问题并执行数据查询…';const token=++epoch;controller=new AbortController();showAI();
  const timer=setTimeout(()=>controller?.abort(),20000);
  try{
   const r=await api('ask',{question:query,context,previousId:previous,mode},controller.signal);
   if(token!==epoch)return;if(snapshot()!==key)throw Error('地图上下文已变化，本次结果未加载，请重新提问。');
   if(r.status==='clarification'){state.messages.push({role:'assistant',text:r.message});phase='需要补充查询条件';}
   else{result=r;previous=r.queryId;contextKey=snapshot();state.messages.push({role:'assistant',text:r.summary});paint(r);phase='✓ 条件已识别  →  ✓ SQL已执行  →  ✓ 统计已整理  →  ✓ 地图已更新';}
  }catch(e){if(token===epoch){error=e.name==='AbortError'?'请求超时，请重试或切换演示模式。':e.message;phase='查询未完成，未生成新结果';}}
  finally{clearTimeout(timer);if(token===epoch){busy=false;controller=null;if(state.assistantOpen)showAI();}}
 };
 async function page(n){if(busy||!result)return;const token=++epoch;busy=true;error='';phase='正在读取分页结果…';showAI();try{const r=await api('result',{id:result.queryId,page:n});if(token!==epoch)return;result=r;paint(r);phase='已加载本页，统计仍基于完整查询结果';}catch(e){if(token===epoch)error=e.message}finally{if(token===epoch){busy=false;if(state.assistantOpen)showAI()}}}
 document.addEventListener('change',e=>{if(e.target.id==='copilot-mode'||e.target.id==='copilot-user'){const value=e.target.value;reset();if(e.target.id==='copilot-mode')mode=value;else {identity=value;if(resultLayer)map.removeLayer(resultLayer);if(scopeLayer)map.removeLayer(scopeLayer);}showAI();}});
 document.addEventListener('click',e=>{
  if(e.target.closest('#tool-clear-map')){if(resultLayer)map.removeLayer(resultLayer);if(scopeLayer)map.removeLayer(scopeLayer);}
  const b=e.target.closest('[data-copilot]');if(!b)return;const action=b.dataset.copilot,v=b.dataset.value;
  if(action==='close'){closeAI();return}if(action==='expand'){expanded=!expanded;showAI();return}if(action==='stop'){stop();phase='已停止等待，未加载本次结果';showAI();return}if(action==='new'){reset();showAI();return}
  if(action==='demo'){reset();mode='demo';showAI();return}if(action==='prompt'){ask(v);return}if(action==='page'){page(Number(v));return}
  if(action==='locate')selectResult(v);
  if(action==='fit'&&result){paint(result);}
  if(action==='clear-map'){if(resultLayer)map.removeLayer(resultLayer);if(scopeLayer)map.removeLayer(scopeLayer);}
  if(action==='export'&&result)download('AI问数-第'+result.page+'页.json',JSON.stringify({question:result.question,total:result.total,page:result.page,rows:result.rows,statistics:result.statistics,scope:result.scope},null,2));
 });
 ResourceCopilot.configure({render:()=>{showAI();requestAnimationFrame(()=>{const body=$('#assistant-dock .copilot-body');if(body)body.scrollTop=body.scrollHeight;});},identity:()=>identity});
 if(state.assistantOpen)showAI();
})();
