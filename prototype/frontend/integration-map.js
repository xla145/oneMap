import {mountSceneMap} from './map.js?v=20260916-map-workspace';

// Own the map lifecycle separately from portal rendering: pending responses must
// never draw into a new scene or restore results after layers have been hidden.
export function createIntegrationMap(ctx){
  const {$,esc,api,toast,field,form,closeModal,B,table,tr,tag}=ctx;
  const colors=['#287e67','#ae6b23','#526fc4','#a0568a','#73863c','#258395'];
  let controller=null,scene=null,epoch=0,queryEpoch=0,rows=[],result=null,selectedScene='',filter='',group='all',scope='scene',expanded=false,pointMode='inspect';
  const data=()=>ctx.state().D, info=()=>data().integration;
  const apps=()=>[{targetId:'nmg-reference-demo',name:'内蒙古自然资源全域图（demo）'},...data().platform.apps.filter(a=>a.listed).map(a=>a.published||a).filter(a=>a.type==='scene')];
  const publishedSettings=()=>info().settings.published||info().settings;
  const layers=()=>scene?.config.layers||[];
  const enabled=()=>layers().filter(l=>l.access==='已授权'&&l.visible);
  const busy=()=>!controller;
  function history(){return (info().mapHistory||[]).slice().reverse().map(r=>B(r.sceneName+' · '+({point:'单点',penetrate:'穿透',nearby:'周边',polygon:'多边形',box:'拉框'}[r.mode]||r.mode)+' · '+r.count+'项 · '+r.at,'map-history',r.id)).join('')||'<p class="muted">暂无查询记录</p>';}
  let savedOwner='',rangeHandler=null,selectedFeature=null;
  let region={id:'150000',name:'内蒙古自治区',city:'',county:''};
  const changed=()=>ctx.onChange?.({scene,layers:layers(),region,feature:selectedFeature,rows,result});
  const storageKey=()=> 'ig-map-state-'+data().user.id;
  function saved(){try{const s=JSON.parse(sessionStorage.getItem(storageKey())||'null');if(!s||typeof s.sceneId!=='string'||!Array.isArray(s.layers))return null;const v=s.view;if(!v||!Array.isArray(v.center)||v.center.length!==2||!v.center.every(Number.isFinite)||!Number.isFinite(v.resolution)||v.resolution<=0||!Number.isFinite(v.rotation))s.view=null;return {...s,filter:typeof s.filter==='string'?s.filter:'',group:['all','department','cities','theme','hotspots'].includes(s.group)?s.group:'all'};}catch{return null;}}
  function remember(){if(!controller||!scene||savedOwner!==data().user.id)return;try{sessionStorage.setItem(storageKey(),JSON.stringify({datasetVersion:'nmg-v1',sceneId:scene.id,extraLayers:scene.extraLayers||[],filter,group,region,view:controller.getViewState(),layers:layers().map(l=>({id:l.id,visible:l.visible,opacity:l.opacity}))}));}catch{/* View restoration is best effort when browser storage is unavailable. */}}
  function html(){
    if(savedOwner!==data().user.id){savedOwner=data().user.id;selectedScene=saved()?.datasetVersion==='nmg-v1'?saved().sceneId:'nmg-reference-demo';filter='';group='theme';}
    if(!apps().some(a=>a.targetId===selectedScene))selectedScene=apps()[0]?.targetId||'';
    return `<section class="ig-map-workspace mw-map-shell"><div class="ig-map-toolbar"><div class="mw-context"><span class="mw-live-dot"></span><strong id="mw-region-label">内蒙古自治区</strong><span class="mw-context-divider">/</span><span id="mw-context-label">综合资源视图</span></div><div class="mw-scene-select">${field('scene','当前成果',selectedScene,'select',apps().map(s=>[s.targetId,s.name]))}${B('刷新','load-map')}${B('保存方案','map-bookmark-save')}${B('放大工作区','map-expand')}</div></div><div class="ig-map-grid"><section id="ig-layers" class="panel ct-panel"><p>正在读取授权图层…</p></section><div class="ig-map-center"><div class="mw-map-top"><span class="mw-map-label">自然资源空间底图 <small>二维</small></span><div class="mw-panel-toggles"><button type="button" data-mw="left" aria-label="收起图层目录" aria-expanded="true">图层目录</button><button type="button" data-mw="right" aria-label="收起业务面板" aria-expanded="true">业务面板</button></div></div><div class="ig-map-actions"><label>点选<select name="mapPointMode"><option value="inspect">查看属性</option><option value="point">单点查询</option><option value="penetrate">穿透查询</option></select></label>${B('多边形','select-polygon')}${B('拉框查询','select-box')}${B('周边查询','query-point')}<details class="mw-more-tools"><summary>更多工具</summary><div>${B('拉框缩放','map-zoom-box')}${B('清空地图','map-empty')}${B('清除结果','map-clear')}${B('指北复位','map-north')}${B('导出地图','map-export')}</div></details></div><div id="ig-map" class="panel"></div><div id="ig-map-legend" class="ig-map-legend"></div><div class="mw-map-bottom"><div id="ig-map-position" class="ig-map-position" aria-live="off">加载后可平移、滚轮缩放；绘制时按 Esc 取消。</div><span>示例图斑 · 仅供演示</span></div></div><aside class="mw-right"><div id="mw-business-panel"></div><div id="ig-feature" class="panel ct-panel"><h3>属性与查询</h3><p>点选地图对象，查看空间信息与关联成果。</p></div></aside></div><div class="mw-bottom-dock"><details class="ig-map-bookmarks"><summary>地图方案 <b>${(info().bookmarks||[]).length}</b></summary><div id="ig-bookmarks">${bookmarks()}</div></details><details class="ig-map-history"><summary>查询历史 <b>${(info().mapHistory||[]).length}</b></summary><div id="ig-map-history">${history()}</div></details><details class="mw-object-ledger"><summary>对象台账 <b id="mw-object-count">0</b></summary><div id="mw-object-list"></div></details><div id="ig-map-state" role="status">${selectedScene?'正在加载场景…':'暂无已上架且可访问的地图场景。'}</div></div></section>`;
  }
  function destroy(){remember();rangeHandler=null;selectedFeature=null;epoch++;queryEpoch++;controller?.destroy();controller=null;scene=null;rows=[];result=null;expanded=false;document.removeEventListener('keydown',onKey);}
  function mount(){if(!info().resultPermissions?.analyze){document.querySelectorAll('[data-action=ig-select-polygon],[data-action=ig-select-box],[data-action=ig-query-point],[data-action=ig-map-history],[name=mapPointMode]').forEach(el=>{el.disabled=true;el.title='需要空间分析授权';});document.querySelector('.ig-map-toolbar a')?.remove();}document.addEventListener('keydown',onKey);$('[name=scene]')?.addEventListener('change',()=>load().catch(fail));$('[name=mapPointMode]')?.addEventListener('change',e=>{pointMode=e.target.value;controller?.clearGraphics();invalidate();});pointMode='inspect';return load().catch(fail);}
  function onKey(e){if(e.key==='Escape'&&expanded&&!$('#dialog')?.open)expand();}
  function fail(e){if($('#ig-map-state'))$('#ig-map-state').textContent=e.message;toast(e.message);}
  function status(){if(!scene)return;$('#ig-map-state').textContent=scene.name+' · 发布 v'+scene.version+' · '+layers().length+'个可见目录图层 / '+enabled().length+'个已启用 · 当前角色查询面积上限 '+Math.min(publishedSettings().maxAreaHa,publishedSettings().roleAreaLimits?.[data().user.role]??publishedSettings().maxAreaHa)+' 公顷';}
  function invalidate(){queryEpoch++;rows=[];result=null;selectedFeature=null;controller?.clearGraphics();if($('#ig-feature'))$('#ig-feature').innerHTML='<h3>属性与查询</h3><p>点击图斑或绘制范围查看结果。</p>';changed();}
  function legend(){if(!$('#ig-map-legend'))return;$('#ig-map-legend').innerHTML='<strong>当前图例</strong>'+enabled().map(l=>`<span><i style="background:${l.displayColor}"></i>${esc(l.name)}</span>`).join('')+(enabled().length?'':'<span>未启用图层</span>')+'<span><i class="ig-query-symbol"></i>查询范围</span><span><i style="background:#167968"></i>查询命中</span>';status();changed();}
  function bookmarks(){return (info().bookmarks||[]).map(r=>`<div class="ig-attention"><strong>${esc(r.name)}</strong><small>${esc(r.sceneName)} · ${r.layerIds.length} 个图层</small>${B('恢复','map-bookmark-restore',r.id)}${B('删除','map-bookmark-delete',r.id)}</div>`).join('')||'<p class="muted">尚未收藏，可保存当前场景的图层组合和视角。</p>';}
  function layerMetadata(l){if(l.resourceId?.startsWith('nmg:'))return {department:'内蒙古参考demo',theme:l.theme||'未分类',cities:[...new Set((l.features||[]).map(f=>f.region))],hotspots:['参考演示']};const row=info().results?.layers.find(r=>r.resourceId===l.resourceId);const raw=data().resources.find(r=>r.id===l.resourceId),r=raw?.published||raw;return {department:row?.provider||r?.source||'未登记来源',theme:row?.layerTheme||r?.category||'未分类',cities:row?.cities||[r?.region||'未登记'],hotspots:row?.hotspots?.length?row.hotspots:['未登记热点']};}
  function directoryLayers(){return scope==='scene'?layers():[...layers().filter(l=>l.resourceId?.startsWith('nmg:')),...(info().results?.layers||[]).map(r=>({id:'catalog:'+r.resourceId,resourceId:r.resourceId,name:r.name,access:r.authorized?'已授权':'需申请',global:true,scenes:r.scenes}))];}
  function renderLayers(){
    $('#ig-layers').innerHTML=`<div class="mw-panel-heading"><div><small>DATA LAYERS</small><h3>空间资源目录</h3></div><span class="mw-count">${layers().length}</span><button type="button" class="mw-left-close" data-mw="left" aria-label="关闭图层目录">×</button></div>${field('layerScope','资源范围',scope,'select',[['scene','当前地图场景'],['all','全部可见图库']])}${field('layerSearch','搜索图层、主题、部门或地区',filter)}${field('layerGroup','分组方式',group,'select',[['all','全部图层'],['theme','主题目录'],['department','提供部门'],['cities','盟市'],['hotspots','热点']])}<div class="actions">${B('全部启用','show-layers')}${B('全部关闭','hide-layers')}</div><div id="ig-layer-list"></div><details class="ig-region-picker" open><summary>行政区定位</summary>${field('mapCity','自治区 / 盟市','','select',[['','内蒙古自治区'],...controller.regions('cities').map(r=>[r.id,r.name])])}${field('mapCounty','旗县','','select',[['','全部旗县']])}</details>`;
    $('#ig-layers .mw-panel-heading').after($('#ig-layers .ig-region-picker'));
    $('[name=layerScope]').onchange=e=>{scope=e.target.value;renderLayerList();};
    $('[name=layerSearch]').oninput=e=>{filter=e.target.value;renderLayerList();};$('[name=layerGroup]').onchange=e=>{group=e.target.value;renderLayerList();};
    $('[name=mapCity]').onchange=e=>{const id=e.target.value;const select=$('[name=mapCounty]');select.innerHTML='<option value="">全部旗县</option>'+controller.regions('counties',id||'none').map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('');controller.locateRegion(id?'cities':'province',id||'150000');region={id:id||'150000',name:e.target.selectedOptions[0].textContent,city:id,county:''};invalidate();remember();};
    $('[name=mapCounty]').onchange=e=>{if(e.target.value)controller.locateRegion('counties',e.target.value);else {const id=$('[name=mapCity]').value;controller.locateRegion(id?'cities':'province',id||'150000');}region={id:e.target.value||$('[name=mapCity]').value||'150000',name:e.target.value?e.target.selectedOptions[0].textContent:$('[name=mapCity]').selectedOptions[0].textContent,city:$('[name=mapCity]').value,county:e.target.value};invalidate();remember();};
    $('[name=mapCity]').value=region.city;
    $('[name=mapCounty]').innerHTML='<option value="">全部旗县</option>'+controller.regions('counties',region.city||'none').map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('');$('[name=mapCounty]').value=region.county;
    renderLayerList();
  }
  function layerItem(l){return `<article class="ig-layer-item">${l.global?`<strong>${esc(l.name)}</strong>`:`<label><input type="checkbox" data-ig-layer="${esc(l.id)}" ${l.visible&&l.access==='已授权'?'checked':''} ${l.access!=='已授权'?'disabled':''}><i style="background:${l.displayColor}"></i><strong>${esc(l.name)}</strong></label>`}<small>${esc(l.access)} · ${l.global?'图库目录对象':l.access==='已授权'?l.features.length+'个示例要素':'获取授权后查看图斑'}</small>${l.resourceId?.startsWith('nmg:')?'<details class="mw-layer-options"><summary>图层操作</summary>':''}${B('图层详情',l.resourceId?.startsWith('nmg:')?'map-demo-detail':'result-detail',l.resourceId?.startsWith('nmg:')?l.id:'resource:'+l.resourceId)}${l.global?(l.access!=='已授权'?`<a class="btn small" href="#/front/data/${encodeURIComponent(l.resourceId)}">申请使用</a>`:l.scenes?.length?B(layers().some(x=>x.resourceId===l.resourceId)?'定位已加载图层':'叠加到当前地图','map-resource',l.resourceId):'<small>尚未编入可访问的地图场景</small>'):l.access==='已授权'?`<label class="ig-opacity">透明度<input aria-label="${esc(l.name)}透明度" data-ig-opacity="${esc(l.id)}" type="range" min="0" max="1" step="0.1" value="${l.opacity??1}"></label>${B('定位图层','map-layer',l.id)}${l.sourceSceneId?B('移除叠加','map-remove-overlay',l.resourceId):''}`:`<a class="btn small" href="#/front/data/${encodeURIComponent(l.resourceId)}">详情 / 申请</a>`}${l.resourceId?.startsWith('nmg:')?'</details>':''}</article>`;}
  function renderLayerList(){
    const all=directoryLayers(),filtered=all.filter(l=>(l.name+' '+Object.values(layerMetadata(l)).flat().join(' ')).toLowerCase().includes(filter.trim().toLowerCase()));
    function tree(list,depth=0){const buckets=new Map();for(const l of list){const m=layerMetadata(l);let keys=group==='all'?['全部图层']:group==='theme'?[m.theme.split('/')[depth]||'本级图层']:Array.isArray(m[group])?m[group]:[m[group]];for(const k of new Set(keys)){if(!buckets.has(k))buckets.set(k,[]);buckets.get(k).push(l);}}return [...buckets].map(([k,items])=>`<details open><summary>${esc(k)}（${items.length}）</summary>${group==='theme'&&depth<3&&items.some(l=>layerMetadata(l).theme.split('/').length>depth+1)?tree(items,depth+1):items.map(layerItem).join('')}</details>`).join('');}
    $('#ig-layer-list').innerHTML=`<p class="muted">匹配 ${filtered.length} / ${all.length} 个图层；多标签可在多个分组出现，各组按图层去重。检索不改变已启用图层。</p>`+tree(filtered);
    document.querySelectorAll('[data-ig-layer]').forEach(e=>e.onchange=()=>{layers().find(l=>l.id===e.dataset.igLayer).visible=e.checked;controller.setLayers(layers());invalidate();legend();renderLayerList();remember();});
    document.querySelectorAll('[data-ig-opacity]').forEach(e=>e.oninput=()=>{layers().find(l=>l.id===e.dataset.igOpacity).opacity=Number(e.value);controller.setLayers(layers());document.querySelectorAll('[data-ig-opacity]').forEach(x=>{if(x.dataset.igOpacity===e.dataset.igOpacity)x.value=e.value;});remember();});
  }
  function showFeature(f){selectedFeature=f;$('#ig-feature').innerHTML=`${result?B('返回查询列表','map-results'):''}<h3>${esc(f.name)}</h3><dl class="ig-feature-fields"><dt>所属图层</dt><dd>${esc(f.layer?.name||f.layerName||'')}</dd><dt>行政区</dt><dd>${esc(f.region||'未登记')}</dd><dt>来源</dt><dd>${esc(f.source||'虚构示例图斑')}</dd><dt>示例业务面积</dt><dd>${esc(f.area??'—')} ${esc(f.unit||'公顷')}</dd></dl><p class="muted">业务面积为示例属性，不等同地图绘制面积。</p>${f.properties?'<dl class="ig-feature-fields">'+Object.entries(f.properties).filter(([k,v])=>['type','county','owner','approval','updateTime','control','year'].includes(k)&&v!=null).map(([k,v])=>'<dt>'+esc(({type:'类型',county:'旗县',owner:'责任单位',approval:'来源状态',updateTime:'更新时间',control:'管控说明',year:'年份'})[k])+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl>':''}${f.coordinates?.length&&info().resultPermissions?.analyze?'<button class="btn primary" type="button" data-mw="analyze-feature">以此地块进行核查 →</button>':''}`;changed();}
  function showResults(){if(!result)return;$('#ig-feature').innerHTML=`<h3>查询结果 · ${result.total}项</h3><p>查询范围 ${result.areaHa} 公顷 · 场景 v${result.sceneVersion}</p>${rows.length?B('定位全部结果','map-fit-results'): '<p>当前范围与已启用图层没有相交要素，可调整范围或图层重试。</p>'}<div class="ig-result-list">${rows.map((r,i)=>`<button class="ig-result-item" data-action="ig-map-result" data-id="${i}"><strong>${esc(r.name)}</strong><span>${esc(r.layerName)} · ${esc(r.region)}</span><small>定位并查看属性 →</small></button>`).join('')}</div><small>${esc(result.scope)}</small>`;changed();}
  async function query(request){
    if(!info().resultPermissions?.analyze)throw Error('当前仅有成果查看权限，请申请空间分析授权');
    if(busy())throw Error('请先加载可用地图场景');
    if(request.sceneId&&request.sceneId!==scene.id)throw Error('场景已切换，请重新查询');
    const ids=request.layerIds||enabled().map(l=>l.id);if(!ids.length)throw Error('请先启用至少一个已授权图层');
    const token=++queryEpoch,g=epoch;$('#ig-feature').innerHTML='<p role="status">正在查询授权图层…</p>';
    controller.setResultFeatures([]);rows=[];result=null;
    try{
      const r=await api('integration.map.query',{...request,sceneId:scene.id,extraLayers:scene.extraLayers||[],layerIds:ids});if(g!==epoch||token!==queryEpoch)return;
      result=r;rows=r.rows;controller.setResultFeatures(rows);controller.setSelection(r.queryGeometry);showResults();
      if(r.history){info().mapHistory.push(r.history);$('#ig-map-history').innerHTML=history();}
    }catch(e){if(g===epoch&&token===queryEpoch){controller.setSelection(null);$('#ig-feature').innerHTML='<h3>查询未完成</h3><p>'+esc(e.message)+'</p>';throw e;}}
  }
  async function load(extraOverride=null){
    const id=$('[name=scene]')?.value;if(!id){$('#ig-layers').innerHTML='<p>请先在应用中心发布可访问的二维地图场景。</p>';return;}
    remember();selectedScene=id;const restore=saved()?.sceneId===id?saved():null;filter=restore?.filter||'';group=restore?.group||'theme';region=restore?.region||{id:'150000',name:'内蒙古自治区',city:'',county:''};const token=++epoch;queryEpoch++;controller?.destroy();controller=null;scene=null;rows=[];result=null;
    $('#ig-map').replaceChildren();$('#ig-map-state').textContent='正在加载授权场景…';$('#ig-layers').innerHTML='<p>正在读取授权图层…</p>';$('#ig-feature').innerHTML='<p>场景加载后可查看属性和查询结果。</p>';$('#ig-map-legend').innerHTML='';
    try{
      const next=await api('integration.results.map.runtime',{sceneId:id,extraLayers:extraOverride??restore?.extraLayers??[]});if(token!==epoch)return;scene=next;
      next.config.layers.forEach((l,i)=>{l.displayColor=l.displayColor||colors[i%colors.length];const old=restore?.layers?.find(x=>x.id===l.id);if(old&&l.access==='已授权'){l.visible=!!old.visible;l.opacity=Number.isFinite(old.opacity)?Math.max(0,Math.min(1,old.opacity)):1;}if(l.access!=='已授权')l.visible=false;});
      const host=document.createElement('div');host.className='pc-map-host';$('#ig-map').replaceChildren(host);
      const mounted=await mountSceneMap(host,next.config,{
        onSelect:f=>{if(token===epoch)showFeature(f);},
        onMeasure:r=>{if(token===epoch)$('#ig-feature').innerHTML=`<h3>面积量算</h3><p>${esc(r.area)} 公顷</p><small>按绘制范围近似计算；不作为业务审批结论。</small>`;},
        onSelectRange:(geometry,mode)=>mode==='zoom'?controller.fitGeometry(geometry):rangeHandler?rangeHandler(geometry,mode):query({sceneId:id,mode:mode==='box'?'box':'polygon',geometry}).catch(fail),
        onMapClick:coordinates=>{if(pointMode==='inspect')return false;query({sceneId:id,mode:pointMode,x:coordinates[0],y:coordinates[1]}).catch(fail);return true;},
        onViewChange:v=>{if(token===epoch)remember();if(token===epoch&&$('#ig-map-position'))$('#ig-map-position').textContent=`中心经纬度 ${v.center.map(x=>x.toFixed(4)).join(', ')} · 缩放 ${v.zoom.toFixed(1)} · 旋转 ${(v.rotation*180/Math.PI).toFixed(0)}°`;}
      });
      if(token!==epoch){mounted?.destroy();return;}controller=mounted;if(next.droppedLayers)toast('已移除 '+next.droppedLayers+' 个失效或未授权的叠加来源');if(restore?.view)controller.restoreViewState(restore.view);if(!info().resultPermissions?.analyze)host.querySelector('[data-map=draw]')?.remove();renderLayers();legend();
      $('#ig-feature').innerHTML='<h3>属性与查询</h3><p>在左侧定位图层可放大到示例图斑，点击图斑查看属性。单点/穿透查询可直接点击地图。</p>';remember();changed();ctx.onReady?.();
    }catch(e){if(token!==epoch)return;$('#ig-map-state').textContent='加载失败：'+e.message;$('#ig-layers').innerHTML='<p>场景不可用，可选择其他场景或重新加载。</p>';throw e;}
  }
  function expand(){expanded=!expanded;$('.ig-map-workspace').classList.toggle('ig-map-expanded',expanded);$('[data-action=ig-map-expand]').textContent=expanded?'退出放大（Esc）':'放大工作区';}
  async function action(op,id){
    if(op==='map-demo-detail'){const l=layers().find(l=>l.id===id);if(l)ctx.modal(l.name,'<p>来源：用户提供的内蒙古一张图demo</p><p>业务分类：'+esc(l.theme)+' · 数据年份：2025</p><p>'+l.features.length+' 个模拟要素；保留原始属性，显示几何经过近似坐标转换。仅供演示。</p>');return true;}
    if(op==='map-bookmark-save'){const token=epoch;if(busy())throw Error('请先加载地图');form('收藏图层与视角',field('name','收藏名称',scene.name),async v=>{const r=await api('integration.bookmark.save',{values:{name:v.name,sceneId:scene.id,extraLayers:scene.extraLayers||[],layerIds:enabled().map(l=>l.id),view:controller.getViewState(),kind:'layers'}});if(token!==epoch)return;info().bookmarks.push(r);closeModal();$('#ig-bookmarks').innerHTML=bookmarks();toast('已收藏当前图层与视角');});return true;}
    if(op==='map-bookmark-delete'){const token=epoch;const row=info().bookmarks.find(r=>r.id===id);await api('integration.bookmark.delete',{id,rev:row.rev});if(token!==epoch)return true;info().bookmarks=info().bookmarks.filter(r=>r.id!==id);$('#ig-bookmarks').innerHTML=bookmarks();return true;}
    if(op==='map-bookmark-restore'){const token=epoch,r=await api('integration.bookmark.restore',{id});if(token!==epoch)return true;if(!apps().some(a=>a.targetId===r.bookmark.sceneId))throw Error('收藏场景已不可访问');$('[name=scene]').value=r.bookmark.sceneId;await load(r.bookmark.extraLayers||[]);if(scene?.id!==r.bookmark.sceneId)return true;layers().forEach(l=>l.visible=l.access==='已授权'&&r.layerIds.includes(l.id));controller.setLayers(layers());controller.restoreViewState(r.bookmark.view);invalidate();renderLayers();legend();remember();toast(r.removedCount?'已剔除 '+r.removedCount+' 个失效或未授权图层':'已恢复收藏');return true;}
    if(op==='map-resource'&&id.startsWith('nmg:'))return action('map-layer',id);
    if(op==='map-resource'){if(busy())throw Error('请先加载地图');const row=info().results.layers.find(r=>r.resourceId===id),target=row?.scenes?.[0];if(!target)throw Error('没有可访问场景');const existing=layers().find(l=>l.resourceId===id);if(!existing)await load([...(scene.extraLayers||[]),{resourceId:id,sceneId:target.id}]);if(!scene)return true;scope='scene';filter='';renderLayers();const added=layers().find(l=>l.resourceId===id);if(!added)throw Error('图层已不可访问，请刷新目录');return action('map-layer',added.id);}
    if(op==='map-remove-overlay'){if(busy())throw Error('请先加载地图');await load((scene.extraLayers||[]).filter(r=>r.resourceId!==id));return true;}
    if(op==='map-zoom-box'){if(busy())throw Error('请先加载地图');controller.startSelection('zoom');return true;}
    if(op==='map-empty'){if(busy())throw Error('请先加载地图');layers().forEach(l=>l.visible=false);controller.setLayers(layers());invalidate();renderLayerList();legend();return true;}

    if(op==='map-export'){if(busy())throw Error('请先加载地图');await controller.exportImage({title:region.name+' · 一张图成果',subtitle:scene.name+' · v'+scene.version+' · 示例数据，仅供演示',legend:enabled().map(l=>l.name).join(' / ')});return true;}
    if(op==='load-map'){await load();return true;}
    if(op==='map-expand'){expand();return true;}
    if(!['map-history','query-point','select-polygon','select-box','hide-layers','show-layers','map-clear','map-north','map-layer','map-result','map-results','map-fit-results'].includes(op))return false;
    if(!info().resultPermissions?.analyze&&['map-history','query-point','select-polygon','select-box'].includes(op))throw Error('需要空间分析授权');
    if(busy())throw Error('请先加载可用地图场景');
    if(op==='map-clear'){controller.clearGraphics();invalidate();}
    if(op==='map-north')controller.north();
    if(op==='map-results')showResults();
    if(op==='map-result'){const row=rows[Number(id)];if(row)controller.locateFeature(row.layerId,row.id);}
    if(op==='map-fit-results'&&rows.length)controller.fitGeometry({type:'FeatureCollection',features:rows.map(r=>({type:'Feature',properties:{},geometry:r.geometry||{type:'Polygon',coordinates:[[...r.coordinates,r.coordinates[0]]]}}))});
    if(op==='map-layer'){const l=layers().find(l=>l.id===id);if(!l||l.access!=='已授权')throw Error('图层未授权');if(!l.visible){l.visible=true;controller.setLayers(layers());invalidate();renderLayerList();legend();}if(!controller.fitLayer(id))toast('该图层在当前授权范围内暂无要素');remember();}
    if(op==='show-layers'||op==='hide-layers'){layers().forEach(l=>l.visible=op==='show-layers'&&l.access==='已授权');controller.setLayers(layers());invalidate();renderLayerList();legend();}
    if(op==='select-polygon'||op==='select-box'){if(!enabled().length)throw Error('请先启用至少一个已授权图层');invalidate();controller.startSelection(op==='select-box'?'box':'polygon');}
    if(op==='query-point'){const center=controller.getViewState().center;form('坐标查询',field('mode','方式','point','select',[['point','单点（首个命中）'],['penetrate','穿透（全部命中）'],['nearby','周边']])+field('x','经度',Number(center[0].toFixed(5)),'number')+field('y','纬度',Number(center[1].toFixed(5)),'number')+field('radius','周边半径（米）',1000,'number'),async v=>{await query(v);closeModal();if(result?.queryGeometry)controller.fitGeometry(result.queryGeometry);});}
    if(op==='map-history'){
      const r=info().mapHistory.find(r=>r.id===id);if(!r)return;
      if(!apps().some(a=>a.targetId===r.request.sceneId))throw Error('历史场景已下架或当前不可访问');
      $('[name=scene]').value=r.request.sceneId;await load(r.request.extraLayers||[]);if(scene?.id!==r.request.sceneId)return;
      const ids=r.request.layerIds||[];layers().forEach(l=>l.visible=l.access==='已授权'&&(!ids.length||ids.includes(l.id)));controller.setLayers(layers());renderLayerList();legend();
      await query(r.request);if(result?.queryGeometry)controller.fitGeometry(result.queryGeometry);
    }
    return true;
  }
  return {html,mount,destroy,action,getState:()=>({scene,layers:layers(),region,feature:selectedFeature,rows,result}),controller:()=>controller,setActiveLayers(ids){if(!controller)return;layers().forEach(l=>l.visible=l.access==='已授权'&&ids.includes(l.resourceId));controller.setLayers(layers());invalidate();renderLayerList();legend();remember();},rangeHandler(fn){rangeHandler=fn;},selectObject(layerId,id){controller?.locateFeature(layerId,id);},async activateResources(ids){for(const id of ids){await action('map-resource',id);}},showSummary(){selectedFeature=null;changed();}};
}
