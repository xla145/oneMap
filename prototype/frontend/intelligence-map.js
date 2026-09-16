import {mountSceneMap} from './map.js?v=agent-map-v1';

export function createIntelligenceMap({api,esc,toast}) {
  const states=new Map();
  let current=null,controller=null,abort=null,generation=0,ready=Promise.resolve();
  function savedView(key){try{return JSON.parse(sessionStorage.getItem('onemap-map-view:'+key)||'null');}catch{return null;}}
  function dispose() {
    generation++;abort?.abort();abort=null;
    if(controller&&current){current.view=controller.getViewState();try{sessionStorage.setItem('onemap-map-view:'+current.key,JSON.stringify(current.view));}catch{}}
    controller?.destroy();controller=null;
    if(current){delete current.layout;delete current.renderResult;delete current.updateScope;}
  }
  function clear() {dispose();for(const key of states.keys())if(key.endsWith(':new'))sessionStorage.removeItem('onemap-map-view:'+key);current=null;states.clear();}
  function scopeLabel(context) {
    return context.mode==='polygon'?'自定义选区':context.mode==='features'?`所选图斑 (${context.featureRefs?.length||0})`:context.region;
  }
  function mount({agent,session,user,regions,businessContext,pending}) {
    dispose();
    if(!agent.mapEnabled){current=null;return;}
    const key=user.id+':'+agent.id+':'+(session?.id||'new');
    if(!states.has(key))states.set(key,{context:session?.spatialContext?structuredClone(session.spatialContext):businessContext?.spatialContext?structuredClone(businessContext.spatialContext):{mode:'region',region:session?.context.region||businessContext?.region||(user.region==='全区'?'全区':user.region),period:session?.context.period||'全部时间',sceneId:businessContext?.sceneId||agent.mapSceneId,crs:'EPSG:4490'},view:session&&current?.key===user.id+':'+agent.id+':new'?current.view:savedView(key),result:null,lastMessage:null,key});
    const state=states.get(key);state.context.period??='全部时间';current=state;
    const latest=session?.messages.filter(m=>m.analysisResult).at(-1);
    if(latest&&(state.lastMessage!==latest.id||latest.analysisResult.status==='unavailable')){state.result=latest.analysisResult;state.lastMessage=latest.id;state.justReceived=true;if(latest.analysisResult.context)state.context=structuredClone(latest.analysisResult.context);}
    const layout=document.querySelector('.chat-layout');
    if(!layout)return;
    const chat=layout.querySelector('.chat-main'),history=layout.querySelector('.session-panel');
    layout.className='ai-workspace';layout.dataset.tab=state.tab||'map';layout.dataset.busy=String(!!pending);
    const allowedRegions=user.region==='全区'?regions:[user.region];
    layout.innerHTML=`<div class="ai-workspace-bar"><a href="#/front/intelligence">← 智能体中心</a><span>地图分析工作台</span><details class="ai-history"><summary>历史任务</summary></details><button type="button" data-ai="new">新建任务</button></div><div class="ai-mobile-tabs"><button type="button" data-ai-tab="chat">对话</button><button type="button" data-ai-tab="map">地图</button><button type="button" data-ai-tab="results">结果</button></div><div class="ai-conversation"></div><section class="ai-map-column"><div class="ai-map-toolbar"><div class="ai-scope-line"><strong>当前分析范围</strong><span id="ai-scope-label"></span><button type="button" data-ai="clear">清除选区</button></div><div class="ai-map-actions"><button type="button" data-ai="box">框选范围</button><button type="button" data-ai="polygon">绘制选区</button><button type="button" data-ai="ask">统计当前范围</button><button type="button" data-ai="retry">刷新图层</button></div><details class="ai-layers"><summary>参与分析的图层</summary><div id="ai-layer-list">正在读取授权图层…</div></details></div><div class="ai-data-caption">图斑为2026年示例数据 · 绿色描边表示本轮查询结果</div><div id="ai-map-host"><div class="empty">正在加载地图…</div></div><div class="ai-result-panel" id="ai-result-panel"></div></section><aside class="ai-feature-panel" hidden></aside>`;
    layout.querySelector('.ai-conversation').append(chat);
    layout.querySelector('.ai-history').append(history);
    const regionInput=chat.querySelector('[name=region]'),periodInput=chat.querySelector('[name=period]');
    regionInput.innerHTML=allowedRegions.map(r=>`<option ${r===state.context.region?'selected':''}>${esc(r)}</option>`).join('');
    periodInput.value=state.context.period;regionInput.disabled=periodInput.disabled=!!pending;
    function updateScope() {
      layout.querySelector('#ai-scope-label').textContent=scopeLabel(state.context)+' · '+state.context.period;
    }
    function changed() {
      state.result=null;controller?.setResultFeatures([]);renderResult();updateScope();
    }
    regionInput.onchange=()=>{
      state.context={...state.context,mode:'region',region:regionInput.value};delete state.context.geometry;delete state.context.featureRefs;
      controller?.setSelection(null);controller?.locate(regionInput.value);changed();
    };
    periodInput.onchange=()=>{state.context.period=periodInput.value;changed();};
    function showFeature(feature) {
      const panel=layout.querySelector('.ai-feature-panel');panel.hidden=false;
      panel.innerHTML=`<button type="button" data-ai="close-detail" class="ai-close">关闭</button><span class="eyebrow">图斑详情</span><h3>${esc(feature.name)}</h3><dl><dt>行政区</dt><dd>${esc(feature.region)}</dd><dt>属性面积</dt><dd>${esc(feature.area)} ${esc(feature.unit)}</dd><dt>数据年份</dt><dd>${esc(feature.period||'2026年')}</dd><dt>来源</dt><dd>${esc(feature.source)}</dd></dl><p>面积来自示例属性，不能替代实测面积。</p><button type="button" data-ai="use-feature">用此图斑提问</button>`;
      state.focused=feature;
      layout.querySelectorAll('[data-result-id]').forEach(row=>row.classList.toggle('selected',row.dataset.resultId===feature.id&&row.dataset.layer===feature.layerId));
    }
    function renderResult() {
      const panel=layout.querySelector('#ai-result-panel'),result=state.result;
      if(!result){panel.innerHTML='<div class="ai-result-empty"><strong>分析结果将在这里显示</strong><span>选择区域或绘制范围，再向左侧助手提问。</span></div>';return;}
      const stats=result.statistics;
      panel.innerHTML=`<div class="ai-result-heading"><strong>本轮地图结果</strong><span>${esc(result.context?scopeLabel(result.context)+' · '+result.context.period:'')}</span></div><p>${esc(result.summary)}</p>${stats?`<div class="ai-result-metrics"><span><b>${stats.count}</b> 命中图斑</span><span><b>${stats.partialCount}</b> 部分相交</span>${stats.attributeArea!==null?`<span><b>${stats.attributeArea}</b> 公顷 · 完整图斑属性</span>`:''}</div>`:''}<div class="ai-result-rows">${(result.features||[]).map(f=>`<button type="button" data-result-id="${esc(f.id)}" data-layer="${esc(f.layerId)}"><span>${esc(f.name)}<small>${esc(f.region)} · ${f.fullyContained?'完整图斑':'部分相交'}</small></span><strong>${esc(f.area)} 公顷</strong></button>`).join('')}</div>${result.caliber?`<details class="ai-result-caliber"><summary>统计口径与数据版本</summary><p>${esc(result.caliber)}</p><p>场景 v${esc(result.sceneVersion)} · ${(result.sourceVersions||[]).map(v=>`${esc(v.resourceId)} v${esc(v.version)}`).join('；')}</p></details>`:''}`;
    }
    const token=generation;
    function loadMap() {
      abort?.abort();abort=new AbortController();
      const signal=abort.signal;layout.dataset.ready='false';
      ready=(async()=>{
        try {
          const scene=await api('mapRuntime',{agentId:agent.id,sceneId:state.context.sceneId},signal);
          if(signal.aborted||token!==generation||!layout.isConnected)return;
          const config=scene.config;state.config=config;
          state.context.sceneId=scene.id;
          if(!state.context.layerIds)state.context.layerIds=config.layers.filter(l=>l.visible&&l.access==='已授权').map(l=>l.id);
          state.context.layerIds=state.context.layerIds.filter(id=>config.layers.some(l=>l.id===id&&l.access==='已授权'));
          for(const l of config.layers)l.visible=state.context.layerIds.includes(l.id);
          layout.querySelector('#ai-layer-list').innerHTML=config.layers.map(l=>`<label><input type="checkbox" data-ai-layer="${esc(l.id)}" ${l.visible?'checked':''} ${l.access!=='已授权'?'disabled':''}>${esc(l.name)}<small>${esc(l.access)}</small>${l.access!=='已授权'?`<button type="button" data-action="resource" data-id="${esc(l.resourceId)}">查看与申请</button>`:''}</label>`).join('')||'<p>该智能体未配置可用图层，请联系管理员。</p>';
          if(controller)state.view=controller.getViewState();controller?.destroy();
          const candidate=await mountSceneMap(layout.querySelector('#ai-map-host'),config,{onSelect:showFeature,onSelectRange:geometry=>{
            state.context={...state.context,mode:'polygon',geometry};delete state.context.featureRefs;changed();
          },onMeasure:r=>toast(`绘制范围近似面积：${r.area} 公顷；如需分析，请使用上方“绘制选区”。`)});
          if(token!==generation||signal.aborted){candidate?.destroy();return;}
          controller=candidate;
          if(state.view)controller.restoreViewState(state.view);else if(state.context.region!=='全区')controller.locate(state.context.region);
          if(state.context.geometry)controller.setSelection(state.context.geometry);
          const valid=new Set(config.layers.flatMap(l=>l.features.map(f=>l.id+':'+f.id)));
          if(state.result?.features?.some(f=>!valid.has(f.layerId+':'+f.id))){state.result={status:'unavailable',summary:'图层访问权限已变化，请重新查询。',features:[]};renderResult();}
          if(state.result?.features)controller.setResultFeatures(state.result.features);
          if(state.justReceived&&state.result?.features?.length){const points=state.result.features.flatMap(f=>f.coordinates);controller.fitBounds([Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1])),Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))]);state.justReceived=false;}
          layout.dataset.ready='true';updateScope();
        } catch(error) {
          if(error.name==='AbortError'||token!==generation)return;
          layout.querySelector('#ai-map-host').innerHTML=`<div class="empty"><h3>地图暂不可用</h3><p>${esc(error.message)}</p><button type="button" data-ai="retry">重新加载</button></div>`;
          layout.dataset.ready='error';
        }
      })();
    }
    layout.addEventListener('change',event=>{
      const id=event.target.dataset.aiLayer;if(!id||!state.config)return;
      const layer=state.config.layers.find(l=>l.id===id);layer.visible=event.target.checked;
      state.context.layerIds=state.config.layers.filter(l=>l.visible&&l.access==='已授权').map(l=>l.id);
      controller?.setLayers(state.config.layers);changed();
    });
    layout.addEventListener('click',event=>{
      const tab=event.target.closest('[data-ai-tab]');if(tab){layout.dataset.tab=state.tab=tab.dataset.aiTab;return;}
      const row=event.target.closest('[data-result-id]');if(row){controller?.locateFeature(row.dataset.layer,row.dataset.resultId);return;}
      const action=event.target.closest('[data-ai]')?.dataset.ai;
      if(action==='new'){document.querySelector('[data-action=newChat]')?.click();return;}
      if(action==='close-detail'){layout.querySelector('.ai-feature-panel').hidden=true;return;}
      if(action==='retry'){loadMap();return;}
      if(action==='box'||action==='polygon'){controller?.startSelection(action);return;}
      if(action==='clear'){state.context.mode='region';delete state.context.geometry;delete state.context.featureRefs;controller?.setSelection(null);changed();return;}
      if(action==='use-feature'){
        const f=state.focused;state.context.mode='features';state.context.featureRefs=[{layerId:f.layerId||f.layer.id,id:f.id}];delete state.context.geometry;
        controller?.setSelection({type:'Polygon',coordinates:[[...f.coordinates,f.coordinates[0]]]});changed();
        chat.querySelector('textarea').value='统计这个图斑的属性面积';layout.dataset.tab=state.tab='chat';chat.querySelector('textarea').focus();return;
      }
      if(action==='ask'){chat.querySelector('textarea').value='统计当前范围的耕地图斑数量和属性面积';chat.querySelector('form').requestSubmit();layout.dataset.tab=state.tab='chat';}
    });
    renderResult();updateScope();loadMap();
    state.layout=layout;state.updateScope=updateScope;state.renderResult=renderResult;
  }
  async function context() {
    if(!current)return undefined;
    const state=current;await ready;
    if(state!==current)throw Error('任务已切换，请重新提问');
    if(state.layout?.dataset.ready!=='true')throw Error('请先等待地图加载，或点击重新加载');
    return structuredClone(state.context);
  }
  function restore(result) {
    if(!current||!result?.context||result.status==='unavailable')return toast('该历史地图结果不可恢复，请重新查询');
    current.context=structuredClone(result.context);current.result=result;
    const layout=current.layout;
    layout.querySelector('[name=region]').value=result.context.region;layout.querySelector('[name=period]').value=result.context.period;
    controller?.setSelection(result.context.geometry||null);controller?.setResultFeatures(result.features||[]);
    current.updateScope();current.renderResult();layout.dataset.tab=current.tab='map';
    if(result.features?.length)controller?.locateFeature(result.features[0].layerId,result.features[0].id);
  }
  return {mount,dispose,clear,context,restore};
}
