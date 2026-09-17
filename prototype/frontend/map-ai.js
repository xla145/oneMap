// Embedded map conversation. SQL and permission decisions stay on the server.
export function createMapAI(ctx){
  const {esc,api,mapUI,toast}=ctx,$=s=>host?.querySelector(s);
  let host=null,owner='',scene='',controller=null,epoch=0,busy=false,previousId='',scope=null,scopeLabel='',scopeRadius=null,chosenLayer='all',scopeKey='',active=null,items=[],messages=[],history=[];
  const state=()=>mapUI.getState(),button=(label,op,id='')=>`<button class="btn small" type="button" data-ai="${op}" data-id="${esc(id)}">${esc(label)}</button>`;
  function reset(){epoch++;busy=false;previousId='';active=null;items=[];messages=[];scope=null;scopeLabel='';scopeRadius=null;chosenLayer='all';scopeKey='';history=[];}
  function status(message){if($('#mai-status'))$('#mai-status').textContent=message;}
  function context(){
    const s=state(),chosen=$('#mai-layers')?.value||chosenLayer;
    const layerIds=chosen==='visible'?s.layers.filter(l=>l.visible&&l.access==='已授权').map(l=>l.id):chosen==='all'?[]:[chosen];
    if(chosen==='visible'&&!layerIds.length)throw Error('请先启用图层，或选择全部已授权图层');
    return {sceneId:s.scene.id,extraLayers:s.scene.extraLayers||[],layerIds,region:s.region.id==='150000'?'':s.region.name,...(scope?{geometry:scope,...(scopeRadius?{radiusMeters:scopeRadius}:{})}:{})};
  }
  function paint(){if(!controller)return;for(const r of items){controller.setAssistantFeatures(r.queryId,r.mapResult.features);controller.setAssistantVisible(r.queryId,r.visible!==false);}}
  function output(){
    if(!host)return;
    $('#mai-messages').innerHTML=messages.map(m=>`<article class="mai-message ${m.role}"><small>${m.role==='user'?'我的提问':'查询回复'}</small><p>${esc(m.text)}</p></article>`).join('')||'<div class="mai-welcome"><h3>用业务语言查地图</h3><p><strong>当前使用预置演示数据，可直接试问下方示例。</strong></p><p>查找图斑、筛选属性、汇总登记面积。结果会直接显示在当前地图。</p></div>';
    $('#mai-messages').scrollTop=$('#mai-messages').scrollHeight;
    $('#mai-scope').textContent=scopeLabel||'未指定几何范围';
    $('#mai-mode').textContent=active?.mode||'';
    $('#mai-results').innerHTML=active?`<div class="mai-result-title"><h3>本轮查询结果</h3><span>${active.total} 项</span></div><p>${esc(active.summary)}</p><p>地图显示当前页 ${active.loaded} 个对象 · 第 ${active.page} / ${Math.max(1,Math.ceil(active.total/active.pageSize))} 页</p><div class="actions">${button('定位结果','fit')}${button(active.visible===false?'显示图层':'隐藏图层','visible',active.queryId)}${button('移除图层','remove',active.queryId)}${button('下载本页','export')}${active.page>1?button('上一页','page',String(active.page-1)):''}${active.page*active.pageSize<active.total?button('下一页','page',String(active.page+1)):''}</div>${active.statistics.length?`<div class="mai-groups">${active.statistics.map(g=>`<p><strong>${esc(g.name||'未登记')}</strong><span>${g.count} 项 · ${g.areaHa.toFixed(2)} 公顷</span></p>`).join('')}</div>`:''}<div class="mai-table"><table><thead><tr><th>对象 / 图层</th><th>地区 / 年份</th><th>面积（公顷）</th></tr></thead><tbody>${active.rows.map(r=>`<tr tabindex="0" data-ai="locate" data-id="${esc(r.fid)}" aria-selected="false"><td>${esc(r.name)}<small>${esc(r.layer_name)}${r.hasGeometry?'':' · 无几何'}</small></td><td>${esc(r.county||r.region)}<small>${esc(r.year??'未登记')}</small></td><td>${r.area_ha==null?'—':r.area_ha.toFixed(2)}</td></tr>`).join('')||'<tr><td colspan="3">没有匹配对象，请调整条件。</td></tr>'}</tbody></table></div><details><summary>查询条件与 SQL 依据</summary><ul>${active.interpretedFilters.map(f=>`<li>${esc(f)}</li>`).join('')||'<li>当前授权范围内全部对象</li>'}</ul><pre>${esc(active.sql)}</pre><pre>${esc(JSON.stringify(active.parameters,null,2))}</pre><p>执行耗时：${active.durationMs} ms</p><p>来源：${esc(active.sources.map(s=>s.name).join('、')||'当前授权场景')}</p></details><div class="mai-notes">${active.warnings.map(w=>`<p>${esc(w)}</p>`).join('')}</div>`:'';
    $('#mai-result-layers').innerHTML=items.map(r=>`<div><span>${esc(r.question)}</span>${button(r.visible===false?'显示':'隐藏','visible',r.queryId)}${button('查看','show',r.queryId)}${button('移除','remove',r.queryId)}</div>`).join('')||'<p>查询后生成独立临时图层。</p>';
    $('#mai-history').innerHTML=history.filter(r=>r.sceneId===scene).map(r=>button(r.question+' · '+r.created,'restore',r.id)).join('')||'<p>当前场景暂无本人历史查询。</p>';
    $('#mai-submit').disabled=busy;$('#mai-stop').hidden=!busy;
  }
  function accept(r,fit=true){
    const old=items.findIndex(x=>x.queryId===r.queryId);r.visible=true;if(old>=0)items[old]=r;else items.push(r);
    if(items.length>5){const removed=items.shift();controller?.removeAssistantLayer(removed.queryId);}
    active=r;previousId=r.queryId;paint();output();if(fit&&r.mapResult.features.length)controller.fitGeometry(r.mapResult);
  }
  async function loadHistory(){const token=epoch;try{const r=await api('integration.ai.history');if(token===epoch&&host){history=r;output();}}catch(error){if(token===epoch)status(error.message);}}
  async function ask(question){
    if(busy||!host)return;const q=question.trim();if(!q)return;
    let c;try{c=context();}catch(error){status(error.message);return;}
    const key=JSON.stringify(c);if(key!==scopeKey){previousId='';scopeKey=key;}
    const token=++epoch;busy=true;messages.push({role:'user',text:q});$('#mai-question').value='';output();status('正在解析业务条件并执行只读查询…');
    try{
      const r=await api('integration.ai.ask',{question:q,context:c,previousId});
      if(token!==epoch||!host||scene!==state().scene?.id){if(r.queryId)api('integration.ai.cancel',{id:r.queryId}).catch(()=>{});return;}
      if(JSON.stringify(context())!==key)throw Error('地图范围已变化，请按新范围重新提问');
      if(r.status==='clarification'){messages.push({role:'assistant',text:r.message});status('请补充条件后继续提问');}
      else {messages.push({role:'assistant',text:r.summary});accept(r);scopeRadius=r.context.radiusMeters||null;scopeKey=JSON.stringify(context());status('查询完成，点击表格行可定位地图对象。');}
    }catch(error){if(token===epoch&&host){messages.push({role:'assistant',text:'查询未完成：'+error.message});status('没有生成新的地图结果');}}
    finally{if(token===epoch&&host){busy=false;output();loadHistory();}}
  }
  async function fetchResult(id,page=1,restore=false){
    if(busy)return;const token=++epoch;busy=true;output();status('正在校验当前授权并读取结果…');
    try{const r=await api('integration.ai.result',{id,page});if(token!==epoch||!host)return;if(r.context.sceneId!==scene)throw Error('请切换到历史查询对应的地图场景');accept(r);if(restore){previousId='';scopeKey='';}status(restore?'已读取历史结果；下次提问使用地图当前范围，开启新一轮查询。':'已读取当前查询的分页结果，可继续追问。');}
    catch(error){if(token===epoch&&host)status(error.message);}
    finally{if(token===epoch&&host){busy=false;output();}}
  }
  async function exportPage(){if(!active||busy)return;const selected=active,token=epoch;const fresh=await api('integration.ai.result',{id:selected.queryId,page:selected.page});if(token!==epoch||!host||active!==selected)return;active=fresh;const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({question:active.question,filters:active.interpretedFilters,page:active.page,total:active.total,rows:active.rows,map:active.mapResult},null,2)],{type:'application/json'}));a.href=url;a.download='地图问数-第'+active.page+'页.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function setScope(geometry,label){scope=geometry;scopeRadius=null;scopeLabel=label;previousId='';output();status('已更新空间范围，下次提问将使用此范围。');}
  async function action(e){
    const b=e.target.closest('[data-ai]');if(!b)return;const op=b.dataset.ai,id=b.dataset.id;
    try{
      if(op==='close'){ctx.close();return;}
      if(op==='example'){await ask(id);return;}
      if(op==='stop'){epoch++;busy=false;status('已停止等待；服务端完成后，本页不会加载该结果。');output();return;}
      if(op==='new'){epoch++;busy=false;previousId='';messages=[];output();status('已开启新对话，现有结果图层保留。');}
      if(op==='clear-scope'){setScope(null,'');mapUI.rangeHandler(null);controller?.cancelSelection();}
      if(op==='selected'){
        const f=state().feature;if(!f)throw Error('请先在地图上选择对象');let geometry=f.geometry;if(!geometry&&f.coordinates?.length){const ring=f.coordinates.map(p=>[...p]);if(JSON.stringify(ring[0])!==JSON.stringify(ring.at(-1)))ring.push([...ring[0]]);geometry={type:'Polygon',coordinates:[ring]};}if(!geometry)throw Error('该对象没有几何');setScope(geometry,'选中对象：'+f.name);
      }
      if(op==='draw'){host.closest('.mw-right')?.classList.add('mai-drawing');mapUI.rangeHandler(g=>{host?.closest('.mw-right')?.classList.remove('mai-drawing');setScope(g,'地图绘制范围');mapUI.rangeHandler(null);});controller.startSelection('polygon');status('在地图上绘制范围，双击结束；关闭助手将取消绘制。');}
      if(op==='fit'&&active?.mapResult.features.length)controller.fitGeometry(active.mapResult);
      if(op==='locate'){
        const feature=active?.mapResult.features.find(f=>f.properties.id===id);if(!feature)throw Error('该记录没有可定位几何');active.visible=true;controller.locateAssistantFeature(active.queryId,id);highlight(id);
      }
      if(op==='visible'){const r=items.find(x=>x.queryId===id);if(r){r.visible=r.visible===false;controller.setAssistantVisible(id,r.visible);output();}}
      if(op==='remove'){controller.removeAssistantLayer(id);items=items.filter(x=>x.queryId!==id);if(active?.queryId===id)active=items.at(-1)||null;output();}
      if(op==='show'){const r=items.find(x=>x.queryId===id);if(r){active=r;output();}}
      if(op==='restore')await fetchResult(id,1,true);
      if(op==='page')await fetchResult(active.queryId,Number(id));
      if(op==='export')await exportPage();
    }catch(error){status(error.message);}
  }
  function highlight(id){host?.querySelectorAll('[data-ai=locate]').forEach(el=>{el.setAttribute('aria-selected',String(el.dataset.id===id));if(el.dataset.id===id)el.scrollIntoView({block:'nearest'});});}
  function mount(element){
    const s=state(),user=ctx.state().D.user.id;
    if(user!==owner||s.scene?.id!==scene||controller!==mapUI.controller()){destroy();owner=user;scene=s.scene.id;}
    controller=mapUI.controller();host=element;
    host.innerHTML=`<div class="mai-heading"><div><small>MAP ASSISTANT</small><h2>AI 地图助手</h2></div>${button('关闭','close')}</div><p id="mai-mode" class="mai-mode"></p><label class="mai-field">查询图层<select id="mai-layers"><option value="all">全部已授权图层</option><option value="visible">当前启用图层</option>${s.layers.filter(l=>l.access==='已授权').map(l=>`<option value="${esc(l.id)}">${esc(l.name)}</option>`).join('')}</select></label><div class="mai-scope"><strong id="mai-region">${esc(s.region.name)}</strong><span id="mai-scope"></span><div class="actions">${button('绘制范围','draw')}${button('使用选中对象','selected')}${button('清除范围','clear-scope')}</div></div><div class="mai-examples">${['查询呼和浩特市的永久基本农田','按旗县统计','只看未审批的'].map(q=>button(q,'example',q)).join('')}</div><div id="mai-messages" aria-live="polite"></div><form id="mai-form"><label class="mai-field"><span>业务问题</span><textarea id="mai-question" rows="3" maxlength="1000" required placeholder="例如：查询2025年面积超过20亩的建设用地"></textarea></label><div class="actions"><button id="mai-submit" type="submit" class="btn primary">查询并上图</button>${button('新对话','new')}<button id="mai-stop" type="button" class="btn" data-ai="stop" hidden>停止等待</button></div></form><p id="mai-status" role="status">可按地区、年份、面积和审批状态查询；地图结果为紫色。</p><section id="mai-results"></section><details><summary>本次结果图层（最多5个）</summary><div id="mai-result-layers"></div></details><details><summary>我的最近查询</summary><div id="mai-history"></div></details>`;
    host.onclick=action;host.onkeydown=e=>{if(e.key==='Enter'&&e.target.matches('[data-ai=locate]')){e.preventDefault();action(e);}};
    $('#mai-form').onsubmit=e=>{e.preventDefault();ask($('#mai-question').value);};
    $('#mai-layers').value=chosenLayer;
    $('#mai-layers').onchange=()=>{chosenLayer=$('#mai-layers').value;previousId='';status('查询图层已调整，下次提问将使用新范围。');};
    paint();output();loadHistory();
  }
  function sync(s){
    if(!controller)return;
    if(controller!==mapUI.controller()||scene!==s.scene?.id){destroy();ctx.close();return;}
    if(!host)return;
    if($('#mai-region'))$('#mai-region').textContent=s.region.name;
    if(s.feature?.aiQueryId){const r=items.find(x=>x.queryId===s.feature.aiQueryId);if(r){active=r;output();highlight(s.feature.id);}}
  }
  function unmount(){epoch++;busy=false;mapUI.rangeHandler(null);controller?.cancelSelection();host?.closest('.mw-right')?.classList.remove('mai-drawing');host=null;}
  function destroy(){for(const r of items)controller?.removeAssistantLayer(r.queryId);unmount();reset();controller=null;scene='';}
  return {mount,unmount,destroy,sync};
}
