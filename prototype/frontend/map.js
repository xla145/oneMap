import {Map, View, Feature, GeoJSON, Projection, addProjection, VectorLayer, VectorSource, Draw, Point, Polygon, Style, Fill, Stroke, CircleStyle, Text, TileLayer, XYZ, addCoordinateTransforms, fromLonLat, toLonLat, transformExtent, createBox} from './vendor/openlayers.js?v=agent-map-v1';
import {demoMapData} from './demo-map-data.js';
import {demoMapKey} from './demo-map-config.js?v=nmg-extracted';

const escape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cities=demoMapData.centers.features.map(f=>[f.properties.name,...f.geometry.coordinates]);
const metersPerDegree=6378137*Math.PI/180;
// Keep CGCS2000 coordinates in their original CRS; no implicit WGS84 conversion.
const projection = new Projection({code:'EPSG:4490',units:'degrees',extent:[-180,-90,180,90],worldExtent:[-180,-90,180,90],global:true,axisOrientation:'enu'});
addProjection(projection);

// Demo CGCS2000 longitude/latitude is projected to Web Mercator numerically.
// This is visualization only, not a survey-grade datum transformation.
addCoordinateTransforms(projection,'EPSG:3857',c=>fromLonLat(c),c=>toLonLat(c));

// Spherical approximation for a user-drawn longitude/latitude ring, in hectares.
export function measureRing(coordinates) {
  const rad=Math.PI/180;let area=0;
  for(let i=0;i<coordinates.length;i++) {
    const a=coordinates[i],b=coordinates[(i+1)%coordinates.length];
    area+=(b[0]-a[0])*rad*(2+Math.sin(a[1]*rad)+Math.sin(b[1]*rad));
  }
  return Math.abs(area)*6371008.8**2/2/10000;
}

export async function mountSceneMap(container,config,{onSelect=()=>{},onMeasure=()=>{},onSelectRange=()=>{},onMapClick=null,onViewChange=()=>{},inspectEnabled=false}={}) {
  if(!container.isConnected)return;
  const baseOptions=[
    {id:'demo-img',name:'影像底图',category:'天地图',type:'img_w',label:'cia_w'},
    {id:'demo-vec',name:'矢量底图',category:'天地图',type:'vec_w',label:'cva_w'},
    {id:'demo-ter',name:'地形底图',category:'天地图',type:'ter_w',label:'cta_w'},
    ...config.basemaps.map(b=>({...b,category:'本地备用底图'}))
  ];
  let destroyed=false,base=config.defaultBase==='base-terrain'?'demo-img':config.defaultBase,selected=null,drawing=false;
  const businessLayers=new globalThis.Map();
  container.innerHTML=`<div class="pc-map-surface pc-openlayers" data-engine="openlayers" data-base="${escape(base)}"><div class="pc-ol-target" tabindex="0" role="region" aria-label="OpenLayers 二维地图，使用方向键平移，加减键缩放"></div><div class="pc-map-controls"><button type="button" data-map="in" title="放大" aria-label="放大地图">+</button><button type="button" data-map="out" title="缩小" aria-label="缩小地图">−</button><button type="button" data-map="reset" title="全景" aria-label="地图全景">⌖</button>${config.widgets.some(w=>w.code==='measure')?'<button type="button" data-map="draw" title="绘制量算" aria-label="绘制量算" aria-pressed="false">▱</button>':''}</div><div class="pc-map-base">${[...new Set(baseOptions.map(b=>b.category))].map(category=>`<details open><summary>${escape(category)}</summary>${baseOptions.filter(b=>b.category===category).map(b=>`<button type="button" data-base-id="${escape(b.id)}" class="${b.id===base?'active':''}">${escape(b.name)}</button>`).join('')}</details>`).join('')}</div><div class="pc-admin-switch"><label><input type="checkbox" data-admin="province" checked>自治区界</label><label><input type="checkbox" data-admin="cities" checked>盟市界</label><label><input type="checkbox" data-admin="counties">旗县界</label></div><div class="pc-map-source-status" role="status" hidden></div><div class="pc-map-caption"><span class="pc-map-dot"></span>底图：天地图 · OpenLayers <span>图斑为虚构数据</span></div><div class="pc-map-draw-hint" hidden>点击添加顶点 · 点击起点或双击完成 · Esc 取消</div></div>`;
  const surface=container.querySelector('.pc-map-surface'),target=container.querySelector('.pc-ol-target');
  const boundaryLayer=new VectorLayer({source:new VectorSource({features:new GeoJSON().readFeatures(demoMapData.province,{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'}),wrapX:false})});
  const cityLayer=new VectorLayer({source:new VectorSource({features:cities.map(([name,x,y])=>new Feature({geometry:new Point(fromLonLat([x,y])),name})),wrapX:false}),declutter:true,style:f=>new Style({image:new CircleStyle({radius:config.pointSize||4,fill:new Fill({color:'#52754f'})}),text:new Text({text:f.get('name'),font:`${Math.max(10,config.labelSize||11)}px sans-serif`,offsetY:-13,fill:new Fill({color:'#3d6040'}),stroke:new Stroke({color:'#ffffff',width:3})})})});
  const drawSource=new VectorSource({wrapX:false});
  const drawStyle=new Style({stroke:new Stroke({color:config.drawing||'#287963',width:2}),fill:new Fill({color:'rgba(40,121,99,.16)'}),image:new CircleStyle({radius:4,fill:new Fill({color:config.drawing||'#287963'})})});
  const drawLayer=new VectorLayer({source:drawSource,style:drawStyle,zIndex:100});
  const view=new View({projection:'EPSG:3857',center:fromLonLat([111.7,44]),zoom:4,minZoom:3,maxZoom:18});
  const map=new Map({target,view,layers:[boundaryLayer,cityLayer,drawLayer],controls:[]});
  const selectionSource=new VectorSource({wrapX:false});
  const selectionLayer=new VectorLayer({source:selectionSource,style:new Style({stroke:new Stroke({color:'#276ce0',width:2,lineDash:[6,4]}),fill:new Fill({color:'rgba(39,108,224,.10)'}),image:new CircleStyle({radius:7,fill:new Fill({color:'#276ce0'}),stroke:new Stroke({color:'#fff',width:2})})}),zIndex:110});
  const resultSource=new VectorSource({wrapX:false});
  const resultLayer=new VectorLayer({source:resultSource,style:f=>new Style({image:new CircleStyle({radius:6,fill:new Fill({color:'#167968'}),stroke:new Stroke({color:'#fff',width:2})}),stroke:new Stroke({color:f===selected?'#8e4711':'#167968',width:f===selected?4:3}),fill:new Fill({color:'rgba(28,154,123,.28)'})}),zIndex:105});
  const analysisSource=new VectorSource({wrapX:false});
  const analysisLayer=new VectorLayer({source:analysisSource,zIndex:106});
  const assistantLayers=new globalThis.Map();
  map.addLayer(selectionLayer);map.addLayer(resultLayer);map.addLayer(analysisLayer);
  let selectionDraw=null;
  function setSelection(geometry){selectionSource.clear();if(geometry)selectionSource.addFeature(new GeoJSON().readFeature({type:'Feature',geometry,properties:{}},{dataProjection:projection,featureProjection:'EPSG:3857'}));}
  function startSelection(kind){
    setDrawing(false);if(selectionDraw)map.removeInteraction(selectionDraw);
    selectionSource.clear();
    selectionDraw=new Draw({source:selectionSource,type:['box','zoom'].includes(kind)?'Circle':'Polygon',geometryFunction:['box','zoom'].includes(kind)?createBox():undefined,wrapX:false});
    map.addInteraction(selectionDraw);drawing=true;target.focus({preventScroll:true});
    const hint=container.querySelector('.pc-map-draw-hint');hint.hidden=false;hint.textContent=['box','zoom'].includes(kind)?'点击两个对角确定范围 · Esc 取消':'点击添加顶点 · 点击起点完成选区 · Esc 取消';
    selectionDraw.on('drawend',event=>{
      const geometry=event.feature.getGeometry().clone().transform('EPSG:3857',projection);
      onSelectRange({type:'Polygon',coordinates:geometry.getCoordinates()},kind);
      queueMicrotask(()=>{if(!destroyed){map.removeInteraction(selectionDraw);selectionDraw=null;drawing=false;hint.hidden=true;}});
    });
  }
  const format=new GeoJSON();
  const adminLayers={province:boundaryLayer};
  for(const name of ['cities','counties']) {
    const layer=new VectorLayer({source:new VectorSource({features:format.readFeatures(demoMapData[name],{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'}),wrapX:false}),visible:name==='cities',style:new Style({stroke:new Stroke({color:name==='cities'?'rgba(255,255,255,.85)':'#7f8c99',width:name==='cities'?1.1:.7,lineDash:name==='counties'?[2,2]:undefined})}),zIndex:2});
    adminLayers[name]=layer;map.addLayer(layer);
  }
  const tileLayers=new globalThis.Map(),failedSources=new Set();
  let fallbackReason='';
  function refreshTileStatus(){
    if(destroyed||!container.isConnected)return;
    const status=container.querySelector('.pc-map-source-status');
    const failed=[...tileLayers].some(([name,layer])=>layer.getVisible()&&failedSources.has(name));
    status.hidden=!failed&&!fallbackReason;status.textContent=fallbackReason||'天地图部分瓦片加载失败，可切换本地备用底图或稍后重试。';
  }
  function tileLayer(type){
    if(tileLayers.has(type))return tileLayers.get(type);
    const source=new XYZ({url:'https://t{0-7}.tianditu.gov.cn/DataServer?T='+type+'&x={x}&y={y}&l={z}&tk='+encodeURIComponent(demoMapKey),maxZoom:type==='ibo_w'?10:18,attributions:'天地图',wrapX:false,crossOrigin:'anonymous'});
    const layer=new TileLayer({source,zIndex:type==='ibo_w'?1:type.startsWith('c')?-10:-20});
    let failures=0,successes=0;
    source.on('tileloadend',()=>{successes++;});
    source.on('tileloaderror',()=>{
      if(destroyed)return;
      failures++;failedSources.add(type);
      if(failures>=1&&!successes&&baseOptions.find(b=>b.id===base)?.type===type){
        const local=config.basemaps.find(b=>b.id==='base-gray')||config.basemaps[0];
        if(local){setBase(local.id);fallbackReason='天地图在线底图加载失败，已显示 demo 本地行政区底图。';}
      }
      refreshTileStatus();
    });
    tileLayers.set(type,layer);map.addLayer(layer);return layer;
  }
  const draw=new Draw({source:drawSource,type:'Polygon',style:drawStyle,wrapX:false});
  map.addInteraction(draw);draw.setActive(false);
  function setDrawing(active) {
    drawing=active;draw.setActive(active);
    container.querySelector('.pc-map-draw-hint').hidden=!active;
    container.querySelector('[data-map="draw"]')?.setAttribute('aria-pressed',String(active));
    target.style.cursor=active?'crosshair':'';
  }
  draw.on('drawend',event=>{
    const coordinates=event.feature.getGeometry().clone().transform('EPSG:3857',projection).getCoordinates()[0];
    onMeasure({area:measureRing(coordinates).toFixed(2),coordinates,crs:'EPSG:4490'});
    queueMicrotask(()=>{if(!destroyed)setDrawing(false);});
  });
  const featureStyle=f=>{const displayColor=config.layers.find(l=>l.id===f.get('layerId'))?.displayColor;const color=displayColor||config.highlight||'#d8983b';return new Style({image:new CircleStyle({radius:f===selected?7:4,fill:new Fill({color}),stroke:new Stroke({color:'#fff',width:1})}),fill:new Fill({color:displayColor?color+'40':color}),stroke:new Stroke({color:f===selected?'#804615':displayColor||'#607f48',width:f===selected?3:config.lineWidth||1.5})});};
  function setLayers(layers) {
    let stillSelected=false;
    const ids=new Set();
    for(const [index,item] of layers.entries()) {
      // Never add unauthorized geometry, including invisible layers.
      if(item.access!=='已授权')continue;
      ids.add(item.id);
      let layer=businessLayers.get(item.id);
      if(!layer) {
        layer=new VectorLayer({source:new VectorSource({wrapX:false}),style:featureStyle});
        businessLayers.set(item.id,layer);map.addLayer(layer);
      }
      const features=(item.features||[]).map(record=>{
        if(record.geometry){const feature=format.readFeature({type:'Feature',geometry:record.geometry,properties:{}},{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'});feature.setProperties({record,layerId:item.id});if(item.visible&&selected?.get('layerId')===item.id&&selected?.get('record').id===record.id){selected=feature;stillSelected=true;}return feature;}
        const ring=record.coordinates.map(p=>[...p]);
        if(ring.length&&String(ring[0])!==String(ring[ring.length-1]))ring.push([...ring[0]]);
        const feature=new Feature({geometry:new Polygon([ring]).transform(projection,'EPSG:3857'),record,layerId:item.id});
        if(item.visible&&selected?.get('layerId')===item.id&&selected?.get('record').id===record.id){selected=feature;stillSelected=true;}
        return feature;
      });
      layer.getSource().clear();layer.getSource().addFeatures(features);
      layer.setVisible(!!item.visible);layer.setOpacity(item.opacity??1);layer.setZIndex(10+index);
    }
    for(const [id,layer] of businessLayers)if(!ids.has(id)){map.removeLayer(layer);layer.dispose();businessLayers.delete(id);}
    if(!stillSelected)selected=null;
  }
  function setBase(id) {
    base=id;surface.dataset.base=id;fallbackReason='';
    const option=baseOptions.find(b=>b.id===id)||baseOptions[0];
    const online=!!option.type;
    const gray=(option.style||(id==='base-gray'?'gray':'forest'))==='gray';
    surface.dataset.baseStyle=gray?'gray':'forest';
    for(const layer of tileLayers.values())layer.setVisible(false);
    if(online){tileLayer(option.type).setVisible(true);tileLayer(option.label).setVisible(true);tileLayer('ibo_w').setVisible(true);}
    boundaryLayer.setStyle(new Style({fill:online?undefined:new Fill({color:gray?'#d9dfd7':'#d0dfc4'}),stroke:new Stroke({color:online?'#f4f7e9':gray?'#aab5a6':'#0f6e5c',width:2,lineDash:[6,3]})}));
    container.querySelectorAll('[data-base-id]').forEach(b=>b.classList.toggle('active',b.dataset.baseId===id));
    container.querySelector('.pc-map-caption').innerHTML=`<span class="pc-map-dot"></span>底图：${online?'天地图':'本地行政区划'} · OpenLayers <span>专题图斑为虚构数据</span>`;
    refreshTileStatus();
  }
  function fitBounds(bounds) {view.fit(transformExtent(bounds,projection,'EPSG:3857'),{padding:[35,35,110,35],maxZoom:14});}
  function handleClick(event) {
    const button=event.target.closest('[data-map]');
    if(button){
      if(button.dataset.map==='in')view.setZoom(view.getZoom()+1);
      if(button.dataset.map==='out')view.setZoom(view.getZoom()-1);
      if(button.dataset.map==='reset')fitBounds(config.panorama||config.extent||[96,36,127,54]);
      if(button.dataset.map==='draw'){if(selectionDraw){map.removeInteraction(selectionDraw);selectionDraw=null;drawing=false;}if(!drawing)drawSource.clear();setDrawing(!drawing);target.focus();}
    }
    const admin=event.target.closest('[data-admin]');if(admin)adminLayers[admin.dataset.admin]?.setVisible(admin.checked);
    const baseButton=event.target.closest('[data-base-id]');
    if(baseButton)setBase(baseButton.dataset.baseId);
  }
  function handleKey(event) {if(event.key==='Escape'&&(drawing||selectionDraw)){event.stopPropagation();draw.abortDrawing();if(selectionDraw){map.removeInteraction(selectionDraw);selectionDraw=null;}setDrawing(false);}}
  container.addEventListener('click',handleClick);target.addEventListener('keydown',handleKey);
  map.on('singleclick',event=>{
    if(drawing)return;
    if(onMapClick?.(toLonLat(event.coordinate)))return;
    if(!inspectEnabled&&!config.widgets.some(w=>w.code==='query'))return;
    const feature=map.forEachFeatureAtPixel(event.pixel,f=>f.get('record')?f:undefined,{hitTolerance:5});
    selected=feature||null;businessLayers.forEach(layer=>layer.changed());resultLayer.changed();
    if(feature)onSelect({...feature.get('record'),layer:config.layers.find(l=>l.id===feature.get('layerId'))});
  });
  setLayers(config.layers);setBase(base);map.updateSize();fitBounds(config.extent||[96,36,127,54]);
  if(config.cameraEnabled&&config.camera){view.setCenter(fromLonLat(config.camera.slice(0,2)));view.setZoom(5+Math.log2(100000/config.camera[2]));}
  map.on('moveend',()=>onViewChange({center:toLonLat(view.getCenter()),zoom:view.getZoom(),rotation:view.getRotation()}));
  const observer=new ResizeObserver(()=>{if(!destroyed)map.updateSize();});observer.observe(container);
  return {
    locate(region){const city=cities.find(c=>c[0]===region);if(city){view.setCenter(fromLonLat(city.slice(1)));view.setZoom(8);}else fitBounds(config.extent||[96,36,127,54]);},
    setLayers,fitBounds,setSelection,startSelection,
    setAssistantFeatures(key,items){
      let layer=assistantLayers.get(key);
      if(!layer){layer=new VectorLayer({source:new VectorSource({wrapX:false}),zIndex:108,style:new Style({image:new CircleStyle({radius:7,fill:new Fill({color:'#7055ce'}),stroke:new Stroke({color:'#fff',width:2})}),stroke:new Stroke({color:'#7055ce',width:3}),fill:new Fill({color:'#7055ce35'})})});assistantLayers.set(key,layer);map.addLayer(layer);}
      layer.getSource().clear();
      layer.getSource().addFeatures(items.filter(x=>x.geometry).map(item=>{const f=format.readFeature(item,{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'});f.setProperties({record:{...item.properties,id:item.properties.id,geometry:item.geometry,coordinates:[],aiQueryId:key,area:item.properties.area_ha,unit:'公顷',layerName:item.properties.layer_name},layerId:'ai:'+key});return f;}));
      layer.setVisible(true);
    },
    locateAssistantFeature(key,id){const layer=assistantLayers.get(key);if(!layer)return;layer.setVisible(true);for(const f of layer.getSource().getFeatures()){const match=f.get('record')?.id===id;f.setStyle(match?new Style({image:new CircleStyle({radius:10,fill:new Fill({color:'#f2b544'}),stroke:new Stroke({color:'#fff',width:2})}),stroke:new Stroke({color:'#f2b544',width:5}),fill:new Fill({color:'#f2b54455'})}):undefined);if(match){view.fit(f.getGeometry().getExtent(),{padding:[60,60,60,60],maxZoom:15});selected=f;onSelect({...f.get('record')});}}},
    setAssistantVisible(key,visible){assistantLayers.get(key)?.setVisible(visible);},
    removeAssistantLayer(key){const l=assistantLayers.get(key);if(l){map.removeLayer(l);l.dispose();assistantLayers.delete(key);}},
    cancelSelection(){draw.abortDrawing();if(selectionDraw){map.removeInteraction(selectionDraw);selectionDraw=null;}setDrawing(false);},
    north(){view.setRotation(0);},
    clearGraphics(){draw.abortDrawing();if(selectionDraw){map.removeInteraction(selectionDraw);selectionDraw=null;}setDrawing(false);drawSource.clear();selectionSource.clear();resultSource.clear();selected=null;businessLayers.forEach(l=>l.changed());},
    fitLayer(id){const layer=businessLayers.get(id);if(!layer?.getSource().getFeatures().length)return false;view.fit(layer.getSource().getExtent(),{padding:[50,50,80,50],maxZoom:12});return true;},
    regions(level,parent=''){const features=demoMapData[level]?.features||[];return features.filter(f=>!parent||String(f.properties.cityAdcode||f.properties.parent?.adcode)===String(parent)).map(f=>({id:String(f.properties.adcode),name:f.properties.name}));},
    locateRegion(level,id){const feature=demoMapData[level]?.features.find(f=>String(f.properties.adcode)===String(id));if(!feature)return false;const f=format.readFeature(feature,{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'});view.fit(f.getGeometry().getExtent(),{padding:[40,40,70,40],maxZoom:13});return true;},
    fitGeometry(geojson){const features=format.readFeatures(geojson,{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'});const source=new VectorSource({features});if(features.length)view.fit(source.getExtent(),{padding:[45,45,45,45],maxZoom:15});},
    setAnalysisFeatures(features){
      analysisSource.clear();
      for(const item of features){if(!item.geometry)continue;const f=format.readFeature(item,{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'});const color=item.properties?.kind==='conflict'?'#c43a36':item.properties?.kind==='input'?'#276ce0':'#c78a26';f.setStyle(new Style({image:new CircleStyle({radius:6,fill:new Fill({color}),stroke:new Stroke({color:'#fff',width:2})}),stroke:new Stroke({color,width:2}),fill:new Fill({color:color+'30'})}));f.set('record',{id:item.properties?.id||'',name:item.properties?.name||item.properties?.rule||'',geometry:item.geometry,coordinates:[],layerId:'analysis'});analysisSource.addFeature(f);}
    },
    setResultFeatures(records){
      resultSource.clear();resultSource.addFeatures(records.map(record=>{
        if(record.geometry){const feature=format.readFeature({type:'Feature',geometry:record.geometry,properties:{}},{dataProjection:'EPSG:4326',featureProjection:'EPSG:3857'});feature.setProperties({record,layerId:record.layerId});return feature;}
        const ring=record.coordinates.map(p=>[...p]);if(String(ring[0])!==String(ring.at(-1)))ring.push([...ring[0]]);
        return new Feature({geometry:new Polygon([ring]).transform(projection,'EPSG:3857'),record,layerId:record.layerId});
      }));
    },
    locateFeature(layerId,id){
      const feature=resultSource.getFeatures().find(f=>f.get('layerId')===layerId&&f.get('record').id===id)||businessLayers.get(layerId)?.getSource().getFeatures().find(f=>f.get('record').id===id);
      if(!feature)return false;selected=feature;view.fit(feature.getGeometry().getExtent(),{padding:[60,60,120,60],maxZoom:11});businessLayers.forEach(l=>l.changed());resultLayer.changed();onSelect({...feature.get('record'),layer:config.layers.find(l=>l.id===layerId)});return true;
    },
    async exportImage({title='',subtitle='',legend=''}={}){
      map.renderSync();
      const [width,height]=map.getSize(),canvas=document.createElement('canvas');canvas.width=width;canvas.height=height+110;
      const context=canvas.getContext('2d');context.fillStyle='#edf1ea';context.fillRect(0,0,width,canvas.height);
      for(const source of target.querySelectorAll('.ol-layer canvas')){
        if(!source.width)continue;context.save();context.globalAlpha=Number(source.parentNode.style.opacity||source.style.opacity||1);
        const transform=source.style.transform;if(transform){const matrix=new DOMMatrix(transform);context.setTransform(matrix.a,matrix.b,matrix.c,matrix.d,matrix.e,matrix.f);}
        context.drawImage(source,0,0);context.restore();
      }
      context.fillStyle='#fff';context.fillRect(0,height,width,110);context.fillStyle='#165e50';context.font='bold 18px sans-serif';context.fillText(title,20,height+27,width-40);
      context.fillStyle='#52655f';context.font='12px sans-serif';context.fillText(subtitle,20,height+51,width-40);context.fillText('图层：'+legend,20,height+72,width-40);context.fillText('生成时间：'+new Date().toLocaleString('zh-CN'),20,height+93,width-40);
      const blob=await new Promise((resolve,reject)=>{try{canvas.toBlob(b=>b?resolve(b):reject(Error('地图导出失败')),'image/png');}catch{reject(Error('当前底图不允许导出，请切换本地底图后重试'));}});
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='一张图成果.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    },
    getViewState(){return {center:toLonLat(view.getCenter()),resolution:view.getResolution()/metersPerDegree,rotation:view.getRotation(),basemapId:base};},
    restoreViewState(state){view.setCenter(fromLonLat(state.center));view.setResolution(state.resolution*metersPerDegree);view.setRotation(state.rotation||0);setBase(state.basemapId||config.defaultBase);},
    destroy(){if(destroyed)return;destroyed=true;observer.disconnect();container.removeEventListener('click',handleClick);target.removeEventListener('keydown',handleKey);map.setTarget(undefined);map.dispose();}
  };
}
