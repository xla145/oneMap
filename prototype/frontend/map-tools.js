import {mountAnalysis} from './analysis-workbench.js?v=20260916-shared-tools-r2';
import {convert,buffer} from './public-tools.js';

// One map, reusable inputs, and temporary results scoped to the current user.
export function createMapTools(ctx){
  const {esc,api,mapUI}=ctx,empty=()=>({type:'FeatureCollection',features:[]});
  let owner='',host=null,cleanup=null,active='coordinate',input=empty(),results=[],serial=0,epoch=0,busy=false,overlay=[],drafts={},basic={x:'111.7',y:'40.8',distance:'1000',direction:'forward'},sourceIds=[];
  const $=s=>host?.querySelector(s),state=()=>ctx.state().D,info=()=>state().integration;
  const available=()=> (state().portalManagement?.tools||[]).filter(t=>info().results.tools.some(r=>r.id==='tool:'+t.id));
  const tool=()=>available().find(t=>t.id===active),engine=()=>tool()?.engine;
  const clone=v=>JSON.parse(JSON.stringify(v));
  function resetOwner(){if(owner===state().user.id)return;owner=state().user.id;input=empty();results=[];drafts={};sourceIds=[];serial=0;active='coordinate';basic={x:'111.7',y:'40.8',distance:'1000',direction:'forward'};}
  function notice(text){if($('#mt-status'))$('#mt-status').textContent=text;}
  function download(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/geo+json'})),a=document.createElement('a');a.href=url;a.download=name+'.geojson';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function normalize(value){
    if(Array.isArray(value))value={type:'Polygon',coordinates:[value]};
    const rows=value?.type==='FeatureCollection'?value.features:[value?.type==='Feature'?value:{type:'Feature',geometry:value,properties:{}}];
    if(!Array.isArray(rows)||rows.length>100)throw Error('输入最多支持 100 个对象');
    let vertices=0;
    function coordinates(v){if(!Array.isArray(v)||!v.length)throw Error('坐标不能为空');if(typeof v[0]==='number'){if(v.length<2||!v.every(Number.isFinite)||Math.abs(v[0])>180||Math.abs(v[1])>85)throw Error('共享对象须为 WGS84 经纬度；请先转换坐标');if(++vertices>50000)throw Error('最多支持 50000 个顶点');}else v.forEach(coordinates);}
    return {type:'FeatureCollection',features:rows.map((f,i)=>{if(f?.type!=='Feature'||!['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon'].includes(f.geometry?.type))throw Error('共享输入支持点、线和多边形');coordinates(f.geometry.coordinates);const g=f.geometry,point=p=>Array.isArray(p)&&p.length>=2&&p.every(Number.isFinite),line=l=>Array.isArray(l)&&l.length>=2&&l.every(point),ring=r=>line(r)&&r.length>=4&&r[0][0]===r.at(-1)[0]&&r[0][1]===r.at(-1)[1],polygon=p=>Array.isArray(p)&&p.length>0&&p.every(ring);const valid={Point:()=>point(g.coordinates),MultiPoint:()=>g.coordinates.every(point),LineString:()=>line(g.coordinates),MultiLineString:()=>g.coordinates.every(line),Polygon:()=>polygon(g.coordinates),MultiPolygon:()=>g.coordinates.every(polygon)}[g.type]();if(!valid)throw Error('几何结构无效；多边形每个环至少四个坐标且首尾闭合');return {...clone(f),properties:{...f.properties,id:'input-'+(i+1),name:f.properties?.name||'对象 '+(i+1)}};})};
  }
  function paint(){if(!state()?.user||owner!==state().user.id)return;mapUI.controller()?.setAnalysisFeatures([...results.filter(r=>r.visible).flatMap(r=>r.data.features.map(f=>({...f,properties:{...f.properties,kind:'conflict'}}))),...overlay]);}
  function list(){if(!$('#mt-results'))return;$('#mt-input-count').textContent=input.features.length+' 个共享对象';$('#mt-results').innerHTML=results.slice().reverse().map(r=>`<article class="mt-result"><label><input type="checkbox" data-mt="visible" data-id="${r.id}" ${r.visible?'checked':''}><strong>${esc(r.name)}</strong></label><small>${esc(r.summary)} · ${r.data.features.length} 个对象${r.sources.length?' · 来源 '+esc(r.sources.join('、')):''}</small><div class="actions">${button('作为输入','use',r.id)}${button('追加输入','append',r.id)}${button('定位','locate',r.id)}${button('导出','export',r.id)}${button('移除','remove',r.id)}</div></article>`).join('')||'<p class="mw-empty">计算结果保留在这里，可继续交给其他工具。</p>';}
  function button(label,action,id=''){return `<button type="button" class="btn small" data-mt="${action}" data-id="${id}">${label}</button>`;}
  function addResult(data,name,summary='',key=''){
    if(!host||!data?.features?.length)return;
    if(key&&results.some(r=>r.key===key))return;
    const normalized=normalize(data),row={id:'R'+(++serial),name:name+' · '+serial,data:normalized,summary,sources:[...sourceIds],visible:true,key};
    results.push(row);list();paint();notice('已保存 '+row.name+'；选择“作为输入”可继续计算。');
  }
  function saveDraft(){
    if(!host)return;const g=$('#ana-geometry');
    if(g){drafts[active]={geometry:g.value,crs:$('#ana-crs').value,operation:$('#ana-operation')?.value,distance:$('#ana-distance')?.value,name:$('#ana-name')?.value};try{if($('#ana-crs').value==='EPSG:4326'){input=normalize(JSON.parse(g.value));}}catch{}}
    for(const k of Object.keys(basic)){const el=$('[name="mt-'+k+'"]');if(el)basic[k]=el.value;}
  }
  function stop(save=true){if(save)saveDraft();epoch++;busy=false;cleanup?.();cleanup=null;mapUI.rangeHandler(null);mapUI.controller()?.cancelSelection?.();overlay=[];}
  function setInput(value,append=false,source='地图 / 文件'){
    saveDraft();const next=normalize(value);input=normalize(append?{type:'FeatureCollection',features:[...input.features,...next.features]}:next);sourceIds=append?[...new Set([...sourceIds,source])]:[source];
    // Explicitly choosing an input replaces each tool's old geometry, retaining its parameters.
    for(const d of Object.values(drafts)){d.geometry=JSON.stringify(input);d.crs='EPSG:4326';}
    const point=input.features.find(f=>f.geometry.type==='Point');if(point){basic.x=String(point.geometry.coordinates[0]);basic.y=String(point.geometry.coordinates[1]);basic.direction='forward';}
    if($('#ana-geometry')){$('#ana-geometry').value=JSON.stringify(input);$('#ana-crs').value='EPSG:4326';}if($('#mt-json'))$('#mt-json').value=JSON.stringify(input,null,2);
    renderTool();list();notice('已载入 '+input.features.length+' 个对象，切换工具可继续使用。');
  }
  function selected(){const f=mapUI.getState().feature;if(!f)throw Error('请先在地图上选择对象');let geometry=f.geometry;if(!geometry&&f.coordinates){const c=clone(f.coordinates);geometry=typeof c[0]==='number'?{type:'Point',coordinates:c}:{type:'Polygon',coordinates:[c]};}if(!geometry)throw Error('所选对象没有可用几何');return {type:'Feature',geometry,properties:{name:f.name,id:f.id}};}
  function renderTool(){
    stop(false);if(!host)return;const token=epoch,t=tool(),e=t?.engine;$('#mt-choice').value=active;list();
    if(!t){$('#mt-body').innerHTML='<p>当前身份没有可用工具。</p>';return;}
    if(['overlay','compliance','area'].includes(e)){
      if(input.features.some(f=>!['Polygon','MultiPolygon'].includes(f.geometry.type))){$('#mt-body').innerHTML='<p class="notice">此工具需要面对象。请先用缓冲区将点生成范围，再将结果作为输入。</p>';paint();return;}
      if(e==='compliance'&&!info().resultPermissions.analyze){$('#mt-body').innerHTML='<p>需要成果空间分析授权。</p>';return;}
      $('#mt-body').innerHTML='<div id="mt-analysis" class="mw-shared-analysis"></div>';
      const draft=drafts[active],overlayTool=available().find(t=>t.engine==='overlay');
      if(e==='area'&&!overlayTool){$('#mt-body').innerHTML='<p>多地块量算需要已授权的叠加分析工具。</p>';return;}
      cleanup=mountAnalysis($('#mt-analysis'),{esc,preserveView:true,initialGeometry:input.features.length?clone(input):null,initialDraft:draft,onDraft(value,crs){if(token!==epoch)return;try{if(crs==='EPSG:4326'){input=normalize(value);for(const [id,d] of Object.entries(drafts)){if(id!==active){d.geometry=JSON.stringify(input);d.crs=crs;}}}list();}catch{}},onResult(data,meta){if(token===epoch)addResult(data,meta.name,meta.summary,meta.key);},api:(action,payload={})=>api(e==='compliance'&&action.startsWith('analysis.')?'integration.'+action:action,{...payload,toolId:e==='area'?overlayTool.id:t.id}),attachMap(callback){mapUI.rangeHandler(callback);return {startSelection:kind=>{mapUI.rangeHandler(callback);mapUI.controller()?.startSelection(kind);},setAnalysisFeatures:features=>{if(token===epoch){overlay=features;paint();}},fitGeometry:g=>mapUI.controller()?.fitGeometry(g),destroy(){mapUI.rangeHandler(null);}};},onReady(){if(token!==epoch)return;if(e==='area'&&!draft?.operation){$('#ana-operation').value='area';$('#ana-operation').dispatchEvent(new Event('change',{bubbles:true}));}}},e==='compliance'?'compliance':'overlay');
    }else if(['coordinate','buffer'].includes(e)){
      $('#mt-body').innerHTML=`<h3>${esc(t.name)}</h3><form id="mt-basic">${e==='coordinate'?`<label>转换方向<select name="mt-direction"><option value="forward">经纬度 → Web Mercator</option><option value="inverse">Web Mercator → 经纬度</option></select></label>`:''}<label>${e==='coordinate'?'经度 / X':'经度'}<input name="mt-x" type="number" step="any" value="${esc(basic.x)}" required></label><label>${e==='coordinate'?'纬度 / Y':'纬度'}<input name="mt-y" type="number" step="any" value="${esc(basic.y)}" required></label>${e==='buffer'?`<label>距离（米）<input name="mt-distance" type="number" value="${esc(basic.distance)}" min="1" max="100000" required></label><p>这里生成点缓冲区。对地块缓冲请使用“叠加分析 → 面缓冲”。</p>`:''}<button class="btn primary" type="submit">运行计算</button></form><p>共享地图对象统一采用 WGS84；转换输出保留在结果属性中。近似计算仅用于分析体验。</p><div id="mt-calculation"></div>`;
      if($('[name=mt-direction]'))$('[name=mt-direction]').value=basic.direction;
      $('#mt-basic').onsubmit=async ev=>{ev.preventDefault();if(busy)return;saveDraft();busy=true;const run=ev.target.querySelector('button');run.disabled=true;const started=performance.now();let checked=false;try{
        await api('portal.toolCheck',{id:t.id});checked=true;if(token!==epoch)return;
        let data,summary;
        if(e==='coordinate'){const r=convert(basic.x,basic.y,basic.direction),coordinates=basic.direction==='inverse'?[r.x,r.y]:[Number(basic.x),Number(basic.y)];data={type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'Point',coordinates},properties:{name:'转换点',outputCRS:r.crs,outputX:r.x,outputY:r.y}}]};summary=`${r.crs}：${r.x.toFixed(6)}, ${r.y.toFixed(6)}`;}
        else{const ring=buffer(basic.x,basic.y,basic.distance);data={type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'Polygon',coordinates:[ring]},properties:{name:'点缓冲区',distanceMeters:Number(basic.distance)}}]};summary=basic.distance+' 米 · 球面近似缓冲';}
        addResult(data,t.name,summary);$('#mt-calculation').textContent=summary;mapUI.controller()?.fitGeometry(data);await api('portal.toolResult',{id:t.id,status:'成功',durationMs:performance.now()-started});
      }catch(err){if(token===epoch)notice(err.message);if(checked)await api('portal.toolResult',{id:t.id,status:'失败',error:err.message.slice(0,300),durationMs:performance.now()-started}).catch(()=>{});}finally{if(token===epoch){busy=false;if(run.isConnected)run.disabled=false;}}};
      overlay=input.features.map(f=>({...f,properties:{...f.properties,kind:'input'}}));paint();
    }else{$('#mt-body').innerHTML=`<p>此工具由外部服务提供，可从工具目录查看入口。</p>${button('工具目录','catalog')}`;}
  }
  function mount(element,id){
    resetOwner();host=element;const choices=available();if(id&&choices.some(t=>t.id===id))active=id;if(!choices.some(t=>t.id===active))active=choices[0]?.id||'';
    host.innerHTML=`<div class="mw-panel-heading"><h2>地图工具</h2>${button('业务信息','close')}</div><label class="mt-field">选择工具<select id="mt-choice">${choices.map(t=>`<option value="${esc(t.id)}">${esc(t.name)}</option>`).join('')}</select></label><section class="mt-input"><h3>共享输入 <small id="mt-input-count"></small></h3><div class="actions">${button('取地图选中对象','selected')}${button('追加选中对象','selected-append')}${button('绘制地块','draw')}${button('清空输入','clear')}</div><details><summary>上传 / 编辑 GeoJSON</summary><label>WGS84 经纬度<input id="mt-file" type="file" accept=".json,.geojson"></label><textarea id="mt-json" rows="4" aria-label="共享输入 GeoJSON"></textarea>${button('载入输入','json')}</details></section><p id="mt-status" role="status">各工具共用地图与输入；结果可继续作为下一步输入。</p><div id="mt-body"></div><section class="mt-results"><h3>本次工作结果</h3><div id="mt-results"></div></section><details><summary>其他工具与资源</summary><div id="mt-catalog"></div></details>`;
    $('#mt-catalog').innerHTML=info().results.tools.filter(r=>!r.id.startsWith('tool:')).map(r=>`<button class="btn small" data-action="ig-open" data-id="${esc(r.id)}">${esc(r.name)}</button>`).join('')||'<p>暂无其他工具。</p>';
    $('#mt-choice').onchange=e=>{saveDraft();cleanup?.();cleanup=null;active=e.target.value;renderTool();};
    $('#mt-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>10*1024*1024)throw Error('文件不能超过 10 MB');const origin=host,token=epoch,text=await file.text();if(!host?.isConnected||host!==origin||token!==epoch)return;setInput(JSON.parse(text));}catch(err){notice(err.message);}};
    host.onclick=ev=>{const b=ev.target.closest('[data-mt]');if(!b)return;try{
      const op=b.dataset.mt,r=results.find(r=>r.id===b.dataset.id);
      if(op==='close'){ctx.close();return;}
      if(op==='selected'||op==='selected-append')setInput(selected(),op==='selected-append');
      if(op==='clear')setInput(empty(),false,'手动清空');
      if(op==='json')setInput(JSON.parse($('#mt-json').value));
      if(op==='draw'){mapUI.rangeHandler(g=>{try{setInput({type:'Feature',geometry:g,properties:{name:'绘制地块'}},true,'地图绘制');}catch(err){notice(err.message);}});mapUI.controller()?.startSelection('polygon');notice('在地图上绘制，双击结束；结果追加到共享输入。');}
      if(op==='use'||op==='append'){if(!r)throw Error('结果已移除');setInput(r.data,op==='append',r.id);}
      if(op==='visible'){r.visible=b.checked;paint();}
      if(op==='locate')mapUI.controller()?.fitGeometry(r.data);
      if(op==='export')download(r.data,r.name);
      if(op==='remove'){results=results.filter(x=>x!==r);list();paint();}
      if(op==='catalog')$('#mt-catalog').parentElement.open=true;
    }catch(err){notice(err.message);}};
    $('#mt-json').value=JSON.stringify(input,null,2);renderTool();
  }
  function destroy(){stop();paint();host=null;}
  function show(id){if(!host)return;saveDraft();cleanup?.();cleanup=null;active=id;renderTool();}
  return {mount,destroy,show,setInput,paint};
}
