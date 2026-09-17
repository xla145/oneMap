import {parcelCollection,updateParcel} from './analysis-parcels.js?v=20260916-results-round2-final';
import {mountSceneMap} from './map.js?v=20260916-map-workspace-r2';
import {randomUUID} from './uuid.js';
export function analysisPage(){return `<header class="pub-tool-heading"><div><h1>项目选址与合规性审查</h1><p>上传地块、核查空间冲突、查看逐项依据与报告。</p></div></header><div id="analysis-workbench"><p class="pub-note">正在加载分析工作台…</p></div>`;}

export function mountAnalysis(host,ctx,mode='compliance'){
  const {api,esc}=ctx;let disposed=false,map=null,timer=null,current=null,catalog=null,input=null,busy=false,drawing=null,initialized=false;
  const $=s=>host.querySelector(s),message=t=>{if(!disposed&&$('#ana-status'))$('#ana-status').textContent=t;};
  function listParcels(){
    if(!$('#ana-draft-list'))return;
    try{if(initialized)ctx.onDraft?.(parcelCollection($('#ana-geometry').value),$('#ana-crs').value);}catch{}
    try{const d=parcelCollection($('#ana-geometry').value);$('#ana-draft-list').innerHTML=`<h3>待分析地块 · ${d.features.length} / 100</h3>`+d.features.map((f,i)=>`<div class="ana-draft-row"><strong>${esc(f.properties.name)}</strong><small>${esc(f.properties.id)}</small><div class="actions"><button type="button" class="btn small" data-analysis="parcel-edit" data-index="${i}">编辑坐标 / 名称</button><button type="button" class="btn small" data-analysis="parcel-redraw" data-index="${i}">重绘</button><button type="button" class="btn small" data-analysis="parcel-remove" data-index="${i}">删除</button></div></div>`).join('');}
    catch(e){$('#ana-draft-list').textContent='地块列表暂不可用：'+e.message;}
  }
  function invalidateDraft(){input=null;current=null;clearTimeout(timer);$('#ana-result').innerHTML='';$('#ana-cancel').hidden=true;if($('#ana-spatial-export'))$('#ana-spatial-export').hidden=true;host.spatialResult=null;}
  function setDraft(data){invalidateDraft();$('#ana-geometry').value=JSON.stringify(data,null,2);$('#ana-editor').hidden=true;listParcels();if($('#ana-crs').value==='EPSG:4326')paint(data);else map?.setAnalysisFeatures([]);if($('#ana-spatial-export'))$('#ana-spatial-export').hidden=true;host.spatialResult=null;}
  async function startDraw(index){
    if(!map)throw Error('地图正在加载，请稍后');
    let draft=parcelCollection($('#ana-geometry').value);
    if(draft.features.length&&$('#ana-crs').value!=='EPSG:4326'){
      const r=await validate();if(!r)return;$('#ana-crs').value='EPSG:4326';setDraft(r.normalized);draft=r.normalized;
    }
    if(index===null&&draft.features.length>=100)throw Error('最多 100 个地块');
    drawing={index,text:$('#ana-geometry').value,crs:$('#ana-crs').value};map.startSelection('polygon');
    message(index===null?'绘制新地块，双击完成后追加；已有地块保留。':'重绘所选地块，双击完成后替换该地块；Esc 取消。');
  }
  function download(r){const url=URL.createObjectURL(new Blob([r.content],{type:r.mime+';charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=r.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function paint(data,conflicts={features:[]}){if(!map)return;map.setAnalysisFeatures([...(mode==='overlay'?[]:catalog.layers).map(l=>({type:'Feature',geometry:l.geometry,properties:{kind:'constraint',name:l.name}})),...(data?.features||[]).map(f=>({...f,properties:{...f.properties,kind:'input'}})),...conflicts.features]);}
  function fit(data){map?.fitGeometry(data);}
  async function history(){const rows=await api('analysis.list');if(disposed)return;$('#ana-history').innerHTML=rows.map(r=>`<button type="button" class="btn" data-analysis="history" data-id="${esc(r.id)}">${esc(r.name)} · ${esc(r.status)}</button>`).join('')||'暂无任务';}
  function show(job){
    current=job;host.querySelectorAll('.ana-layout input,.ana-layout select,.ana-layout textarea,.ana-layout button').forEach(el=>{if(el.id!=='ana-cancel')el.disabled=['排队中','运行中'].includes(job.status);});message(`${job.name} · ${job.status}${job.error?'：'+job.error:''}`);
    $('#ana-cancel').hidden=!['排队中','运行中'].includes(job.status);
    if(!job.result){const p=job.progress;$('#ana-result').innerHTML=p?`<h3>地块进度 · ${p.completed} / ${p.total}</h3><progress max="${p.total}" value="${p.completed}"></progress><div class="ana-parcels">${p.parcels.map(r=>`<article class="panel"><strong>${esc(r.name)}</strong><p>${esc(job.status==='已取消'&&r.status!=='已完成'?'已取消':job.status==='失败'&&r.status!=='已完成'?'执行中断':r.status)}</p><small>${esc(r.state||'')}</small></article>`).join('')}</div>`:'';return;}

    const r=job.result;
    $('#ana-result').innerHTML=`<p>任务结果：${esc(job.name)} · ${esc(job.created)} · ${esc(job.id.slice(0,12))}</p><h2>${esc(r.state)}</h2><p>数据与规则：${esc(r.version)} · 等积投影面积，单位平方米。冲突面积按地块融合去重。</p><div class="ana-parcels">${r.parcels.map(p=>`<button type="button" class="panel" data-analysis="locate" data-id="${esc(p.id)}"><strong>${esc(p.name)}</strong><span>${esc(p.state)}</span><small>地块 ${(p.area/10000).toFixed(4)} 公顷 · 冲突 ${(p.conflictArea/10000).toFixed(4)} 公顷</small></button>`).join('')}</div><div class="ana-table"><table><thead><tr><th>地块</th><th>核查项</th><th>结论</th><th>空间关系</th><th>交叠面积㎡</th><th>占比</th><th>说明</th></tr></thead><tbody>${r.rows.map(x=>`<tr>${[x.name,x.rule,x.state,x.relation,x.area==null?'—':x.area.toFixed(2),x.percent==null?'—':x.percent.toFixed(4)+'%',x.reason].map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="form-footer">${[['html','下载可打印报告'],['csv','下载核查明细'],['geojson','下载冲突 GeoJSON']].map(([f,n])=>`<button type="button" class="btn" data-analysis="export" data-format="${f}">${n}</button>`).join('')}<button type="button" class="btn" data-analysis="rerun">载入输入重新运行</button></div>`;
    paint(r.input,r.conflicts);fit(r.input);ctx.onResult?.(r.conflicts.features.length?r.conflicts:r.input,{name:r.conflicts.features.length?'核查冲突范围':'核查地块',summary:r.state,key:'job:'+job.id});
  }
  async function poll(id){clearTimeout(timer);const job=await api('analysis.get',{id});if(disposed||current?.id!==id)return;show(job);if(['排队中','运行中'].includes(job.status))timer=setTimeout(()=>poll(id).catch(e=>message(e.message)),800);else await history();}
  async function validate(){input=null;$('#ana-result').innerHTML='';const geometry=$('#ana-geometry').value,crs=$('#ana-crs').value;const r=await api('analysis.input',{geometry,crs});if(disposed)return null;if(geometry!==$('#ana-geometry').value||crs!==$('#ana-crs').value)throw Error('输入已更改，请重新校验');input=r;ctx.onDraft?.(r.normalized,'EPSG:4326');paint(r.normalized);fit(r.normalized);message(`校验通过：${r.count} 个地块，已保存输入版本。`);return r;}
  function updateOperation(){
    const operation=$('#ana-operation')?.value;if(!operation)return;
    $('#ana-buffer-field').hidden=operation!=='buffer';
    $('#ana-operation-hint').textContent={intersection:'输入两个地块，提取共同覆盖的范围。',difference:'输入两个地块，从第一个地块中扣除第二个。',union:'合并全部地块，并去除重叠部分。',area:'计算全部地块融合去重后的面积。',buffer:'按指定距离向外扩展全部地块，合并输出范围。'}[operation];
  }
  host.addEventListener('input',e=>{input=null;if(e.target.id==='ana-geometry'){invalidateDraft();map?.setAnalysisFeatures([]);listParcels();$('#ana-editor').hidden=true;listParcels();}});
  host.addEventListener('change',async e=>{if(e.target.id==='ana-crs'){invalidateDraft();map?.setAnalysisFeatures([]);return;}if(e.target.id==='ana-operation'){updateOperation();$('#ana-spatial-export').hidden=true;host.spatialResult=null;return;}if(e.target.id!=='ana-file')return;try{const file=e.target.files[0];if(!file)return;if(file.size>10*1024*1024)throw Error('文件不能超过 10 MB');const value=await file.text();if(disposed)return;JSON.parse(value);$('#ana-geometry').value=value;invalidateDraft();map?.setAnalysisFeatures([]);listParcels();$('#ana-editor').hidden=true;message(`已读取 ${file.name}，请确认坐标系后校验。`);}catch(error){message(error.message);}});
  host.addEventListener('click',async e=>{
    const b=e.target.closest('[data-analysis]');if(!b||busy)return;
    busy=true;b.disabled=true;
    try{
      const action=b.dataset.analysis;if(['排队中','运行中'].includes(current?.status)&&!['cancel','history'].includes(action))throw Error('请等待当前任务完成或先取消任务');
      if(action==='sample'){$('#ana-geometry').value=JSON.stringify(catalog.sample,null,2);$('#ana-crs').value='EPSG:4326';input=null;setDraft(catalog.sample);fit(catalog.sample);message('已载入一块冲突地块和一块无冲突地块。');}
      else if(action==='sample-download')download({filename:'示例地块.geojson',mime:'application/geo+json',content:JSON.stringify(catalog.sample,null,2)});
      else if(action==='draw')await startDraw(null);
      else if(action==='parcel-redraw')await startDraw(Number(b.dataset.index));
      else if(action==='parcel-remove'){const d=parcelCollection($('#ana-geometry').value);d.features.splice(Number(b.dataset.index),1);setDraft(d);message('已删除地块，请重新校验。');}
      else if(action==='parcel-edit'){const d=parcelCollection($('#ana-geometry').value),i=Number(b.dataset.index),f=d.features[i];$('#ana-editor').hidden=false;$('#ana-editor').dataset.index=i;$('#ana-editor').dataset.source=$('#ana-geometry').value;$('#ana-editor-name').value=f.properties.name;$('#ana-editor-geometry').value=JSON.stringify(f.geometry,null,2);}
      else if(action==='parcel-edit-cancel')$('#ana-editor').hidden=true;
      else if(action==='parcel-edit-save'){if($('#ana-editor').dataset.source!==$('#ana-geometry').value)throw Error('输入已变更，请重新打开编辑');const d=parcelCollection($('#ana-geometry').value),g=JSON.parse($('#ana-editor-geometry').value),name=$('#ana-editor-name').value.trim();if(!name)throw Error('地块名称不能为空');setDraft(updateParcel(d,Number($('#ana-editor').dataset.index),g,name));message('已更新该地块，运行前将校验全部输入。');}
      else if(action==='validate')await validate();
      else if(action==='spatial'){
        const r=await api('analysis.spatial',{geometry:$('#ana-geometry').value,crs:$('#ana-crs').value,operation:$('#ana-operation').value,distance:Number($('#ana-distance').value)});
        if(disposed)return;host.spatialResult=r;map?.setAnalysisFeatures(r.features.map(f=>({...f,properties:{...f.properties,kind:'input'}})));if(r.features.length)fit(r);message(r.empty?'计算完成，结果为空。':`计算完成：融合去重面积 ${(r.areaSquareMeters/10000).toFixed(4)} 公顷。`);$('#ana-spatial-export').hidden=false;ctx.onResult?.(r,{name:$('#ana-operation').selectedOptions[0].textContent,summary:`${(r.areaSquareMeters/10000).toFixed(4)} 公顷 · 等积投影`});
      }
      else if(action==='spatial-export'&&host.spatialResult)download({filename:'空间运算结果.geojson',mime:'application/geo+json',content:JSON.stringify(host.spatialResult,null,2)});
      else if(action==='run'){
        const source=input||await validate();if(!source||disposed)return;
        const job=await api('analysis.create',{inputId:source.id,name:$('#ana-name').value,requestKey:randomUUID()});if(disposed)return;current=job;$('#ana-result').innerHTML='';await poll(job.id);
      }
      else if(action==='cancel'){await api('analysis.cancel',{id:current.id});await poll(current.id);}
      else if(action==='history'){current={id:b.dataset.id};await poll(current.id);}
      else if(action==='export')download(await api('analysis.export',{id:current.id,format:b.dataset.format}));
      else if(action==='locate'){const f=current.result.input.features.find(f=>f.properties.id===b.dataset.id);fit(f);}
      else if(action==='rerun'){$('#ana-geometry').value=JSON.stringify(current.result.input,null,2);$('#ana-crs').value='EPSG:4326';$('#ana-name').value=current.name+'（重算）';input=null;listParcels();$('#ana-editor').hidden=true;message('已载入历史输入，点击运行将生成独立新任务。');}
    }catch(error){message(error.message);}finally{busy=false;if(b.isConnected)b.disabled=['排队中','运行中'].includes(current?.status)&&b.dataset.analysis!=='cancel';}
  });
  (async()=>{
    catalog=await api('analysis.catalog');if(disposed)return;
    host.innerHTML=`<p class="pub-note">${esc(catalog.label)}。示例覆盖经度 111.5～112、纬度 40.5～41；范围外无法判定。</p><div class="ana-layout"><section class="panel pub-content ana-sidebar"><h2>1. 输入地块</h2><label>任务名称<input id="ana-name" maxlength="100" value="项目地块核查"></label><label>源坐标系<select id="ana-crs"><option value="EPSG:4326">WGS84（经度、纬度）</option><option value="EPSG:3857">Web Mercator（X、Y，米）</option></select></label><label>上传 GeoJSON<input id="ana-file" type="file" accept=".geojson,.json,application/geo+json,application/json"></label><p>支持 Polygon、MultiPolygon、孔洞和最多 100 个地块；上限 10 MB、50000 顶点。暂不支持 CAD、SHP 或测绘基准转换。</p><label>GeoJSON / 闭合坐标数组<textarea id="ana-geometry" rows="5" placeholder="上传文件、粘贴坐标，或载入示例"></textarea></label><div class="ana-input-actions"><button type="button" class="btn" data-analysis="sample">载入示例</button><button type="button" class="btn" data-analysis="sample-download">下载样例</button><button type="button" class="btn" data-analysis="draw">追加绘制地块</button></div><div id="ana-draft-list"></div><section id="ana-editor" hidden><h3>编辑所选地块</h3><label>地块名称<input id="ana-editor-name" maxlength="100"></label><label>几何坐标（沿用当前源坐标系）<textarea id="ana-editor-geometry" rows="6"></textarea></label><button type="button" class="btn" data-analysis="parcel-edit-save">保存地块</button><button type="button" class="btn" data-analysis="parcel-edit-cancel">取消编辑</button></section><div id="ana-rules"><h2>2. 核查规则</h2><ul>${catalog.layers.map(l=>`<li>${esc(l.name)}</li>`).join('')}</ul><p>本阶段固定运行全部三项示例规则；边界接触需复核，缺失、过期、无权限或不完整覆盖均无法判定。</p></div><div class="ana-run-actions"><button type="button" class="btn" data-analysis="validate">校验与预览</button><button type="button" class="btn primary" data-analysis="run">运行核查</button><button type="button" class="btn" id="ana-cancel" data-analysis="cancel" hidden>取消任务</button></div></section><section><div id="ana-map" class="pub-map pub-map-tall"></div><p>蓝色：输入地块 · 橙色：示例管控范围 · 红色：冲突范围</p><p id="ana-status" class="pub-note" role="status" aria-live="polite">请选择示例、上传文件或地图绘制。</p></section></div><section id="ana-result" class="panel pub-content"></section><section class="panel pub-content"><h2>我的最近 50 个任务</h2><div id="ana-history" class="form-footer"></div></section>`;
    if(mode==='overlay'){
      $('#ana-map').nextElementSibling.textContent='蓝色：当前输入 · 红色：保留的工作结果';
      $('#ana-name').closest('label').hidden=true;
      $('#ana-rules').innerHTML=`<h2>2. 空间运算</h2><label>运算类型<select id="ana-operation"><option value="intersection">相交</option><option value="difference">差集（第一个减第二个）</option><option value="union">融合去重</option><option value="area">多地块面积量算</option><option value="buffer">面缓冲</option></select></label><p id="ana-operation-hint" class="ana-field-hint"></p><label id="ana-buffer-field" hidden>缓冲距离（米）<input id="ana-distance" type="number" value="1000" min="1" max="100000"><small>大于 0，不超过 100000 米</small></label><details class="ana-method"><summary>计算说明</summary><p>支持多边形及多多边形。相交、差集要求两个地块，其他运算使用全部输入。缓冲使用局部等距投影，面积使用等积投影。</p></details>`;
      $('#ana-history').parentElement.hidden=true;
      const run=$('[data-analysis="run"]');run.dataset.analysis='spatial';run.textContent='运行运算';
      run.insertAdjacentHTML('afterend','<button type="button" class="btn" id="ana-spatial-export" data-analysis="spatial-export" hidden>导出运算 GeoJSON</button>');
      updateOperation();
    }
    const onRange=g=>{if(disposed||!drawing)return;try{const d=drawing;drawing=null;if(d.text!==$('#ana-geometry').value||d.crs!==$('#ana-crs').value)throw Error('绘制期间输入已变化，请重新绘制');const data=updateParcel(parcelCollection(d.text),d.index,g);$('#ana-crs').value='EPSG:4326';setDraft(data);message('地块已更新，共 '+data.features.length+' 个；请校验或运行。');}catch(e){message(e.message);}};
    if(ctx.attachMap){$('#ana-map').hidden=true;map=ctx.attachMap(onRange);}else{const config=await api('public.map',{});if(disposed)return;config.layers=[];map=await mountSceneMap($('#ana-map'),config,{onSelectRange:onRange});}
    if(disposed){map.destroy();return;}listParcels();paint(null);if(!ctx.attachMap)map.fitGeometry({type:'FeatureCollection',features:catalog.layers.filter(l=>l.geometry).map(l=>({type:'Feature',geometry:l.geometry,properties:{}}))});if(ctx.initialGeometry){$('#ana-crs').value='EPSG:4326';setDraft(ctx.initialGeometry);if(!ctx.preserveView)fit(ctx.initialGeometry);message('已载入地图选中地块，请校验或运行核查。');}if(ctx.initialDraft){const d=ctx.initialDraft;$('#ana-geometry').value=d.geometry;$('#ana-crs').value=d.crs;$('#ana-name').value=d.name||'项目地块核查';if($('#ana-operation')&&d.operation){$('#ana-operation').value=d.operation;$('#ana-distance').value=d.distance||'1000';updateOperation();}listParcels();try{if(d.crs==='EPSG:4326')paint(parcelCollection(d.geometry));}catch{}}initialized=true;listParcels();ctx.onReady?.();await history();
  })().catch(e=>{if(!disposed)host.innerHTML=`<p class="pub-note">${esc(e.message)}</p>`;});
  return ()=>{disposed=true;clearTimeout(timer);map?.destroy();};
}
