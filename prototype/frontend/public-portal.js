import {qaExamples} from './qa-examples.js';
import {createToolCenter} from './tool-center.js?v=20260917-tool-entry';
import {landscapePage,topicCover,topicCoverAlt,guideFor} from './landscape.js';
import {analysisPage,mountAnalysis} from './analysis-workbench.js';
import {mountSceneMap} from './map.js?v=public-v1';
import {convert,polygon,area,buffer} from './public-tools.js';
import {previewSource} from './previews.js';
import {randomUUID} from './uuid.js';
import {newsCategory} from './news.js?v=20260915-1';

export function createPublicPortal(ctx){
  const {$,esc,icon,btn,tag,api,nav,modal,closeModal,toast}=ctx;
  let analysisCleanup=null;
  let controller=null,generation=0,result=null,ticketKey=randomUUID();
  const D=()=>ctx.state().D,P=()=>D().publicPortal,params=()=>new URLSearchParams(location.hash.split('?')[1]||'');
  const tools=()=>ordered((D().portalManagement?.tools||[]).map(t=>({...t,available:true})));
  const data=()=>D().resources.filter(r=>['数据库表','图层服务'].includes(r.type));
  const byId=(rows,id)=>rows.find(r=>r.id===id);
  const ordered=rows=>[...rows].sort((a,b)=>(a.order||0)-(b.order||0));
  const href=(route,id='',query={})=>'#/front/'+route+(id?'/'+encodeURIComponent(id):'')+(Object.keys(query).length?'?'+new URLSearchParams(query):'');
  const link=(route,label,id='',style='btn',query={})=>`<a class="${style}" href="${esc(href(route,id,query))}">${label}</a>`;
  const para=value=>String(value||'').split(/\n\s*\n/).map(t=>`<p>${esc(t).replace(/\n/g,'<br>')}</p>`).join('');
  const empty=(message='暂无符合条件的内容')=>`<div class="empty"><h3>${esc(message)}</h3><p>请调整筛选条件，或稍后查看最新发布内容。</p></div>`;
  const title=(name,description='',actions='')=>`<header class="pub-heading"><div><span class="pub-eyebrow">自然资源 · 公共服务</span><h1>${esc(name)}</h1><p>${esc(description)}</p></div><div class="actions">${actions}</div></header>`;
  const section=(name,desc,route)=>`<div class="pub-section-head"><div><h2>${name}</h2><p>${desc}</p></div>${link(route,'查看全部 '+icon('arrow'),'','pub-more')}</div>`;
  const field=(name,label,value='',type='text',options=[])=>`<label class="pub-field"><span>${esc(label)}</span>${type==='textarea'?`<textarea name="${name}" rows="6">${esc(value)}</textarea>`:type==='select'?`<select name="${name}">${options.map(o=>{const [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${esc(v)}" ${String(value)===String(v)?'selected':''}>${esc(t)}</option>`;}).join('')}</select>`:`<input name="${name}" type="${type}" value="${esc(value)}" ${type==='number'?'step="any"':''}>`}</label>`;
  const note=(text)=>`<div class="pub-note">${icon('bell')}<span>${esc(text)}</span></div>`;
  const match=(r,q)=>!q||[r.name,r.summary,r.description,r.category,r.aliases,r.tags,r.body,r.source].filter(Boolean).join(' ').toLowerCase().includes(q.toLowerCase());
  const card=(r,route='data',kind=r.type||r.category)=>`<article class="pub-card">${link(route,`<img src="${esc(previewSource(r))}" alt="${esc(r.name)}内容示意" loading="lazy">`,r.id,'pub-card-image')}<div class="pub-card-body"><small>${esc(kind)}</small><h3>${link(route,esc(r.name),r.id,'')}</h3><p>${esc(r.description||r.summary||'查看详情与使用说明')}</p><div class="pub-card-meta"><span>${esc(r.region||r.source||'全区')}</span>${r.access?tag(r.access):''}</div>${link(route,'查看详情 '+icon('arrow'),r.id,'pub-more')}</div></article>`;
  const topicCard=r=>`<a class="pub-topic" href="${href('landscape',r.id)}"><img src="${esc(topicCover(r))}" alt="${esc(topicCoverAlt(r))}" loading="lazy"><span class="pub-topic-copy"><small>${esc(r.category)}</small><strong>${esc(r.name)}</strong><span>${esc(r.summary)}</span></span>${icon('arrow')}</a>`;
  function searchForm(q='',id='pub-search'){return `<form id="${id}" class="pub-search"><label class="sr-only" for="${id}-q">搜索数据、工具或资讯</label>${icon('search')}<input id="${id}-q" name="q" placeholder="搜索数据、工具或资讯，例如：耕地、矿业权" value="${esc(q)}" maxlength="100" required><button class="btn primary" type="submit">搜索</button></form>`;}
  function home(){
    const config=P().settings,resources=data(),selected=(config.resourceIds||[]).map(id=>byId(resources,id)).filter(Boolean);
    const recommended=selected.length?selected:resources.slice().sort((a,b)=>String(b.updated).localeCompare(String(a.updated))).slice(0,4);
    const news=[...(D().portalArticles||D().knowledge)].sort((a,b)=>String(b.updated).localeCompare(String(a.updated)));
    return `<section class="pub-hero"><div class="portal-container pub-hero-inner"><div><span class="pub-eyebrow">内蒙古自治区 · 自然资源公共服务</span><h1>${esc(config.title)}</h1><p>${esc(config.subtitle)}</p>${searchForm()}<div class="pub-hot"><span>热门主题</span>${['耕地','矿业权','生态修复'].map(q=>link('search',q,'','',{q})).join('')}${btn('智能帮办','portalAssistant','','text small','sparkles')}</div></div><div class="pub-hero-art">${ctx.landscape()}</div></div></section><div class="portal-container"><div class="pub-quick">${[['map','地图浏览','查看空间分布','layers'],['data','数据申请','发现与获取数据','database'],['capabilities','常用工具','在线分析与量算','tool'],['services','办事服务','查询、指南与咨询','file']].map(([r,n,d,i])=>link(r,`<span class="tile">${icon(i)}</span><span><strong>${n}</strong><small>${d}</small></span>${icon('arrow')}`,'','pub-quick-item')).join('')}</div><section class="pub-notifications"><strong>${icon('bell')}政策与通知</strong>${news.filter(r=>['政策法规','行业动态'].includes(newsCategory(r))).slice(0,2).map(r=>`<button data-action="portalKnowledge" data-id="${esc(r.id)}">${esc(r.name)}<time>${esc(r.updated?.slice(0,10))}</time></button>`).join('')||'<span>暂无已发布通知</span>'}</section><section class="pub-section">${section(selected.length?'推荐数据':'最新数据','按需获取权威资源，了解来源与使用方式。','data')}<div class="pub-grid">${recommended.map(r=>card(r)).join('')}</div></section><section class="pub-section pub-service-columns"><div>${section('常用能力','从坐标到空间范围，直接开始使用。','capabilities')}<div class="pub-tool-shortcuts">${tools().filter(t=>t.available).map(t=>link('capabilities',`<span class="tile">${icon(t.icon)}</span><span><strong>${esc(t.name)}</strong><small>${esc(t.description)}</small></span>${icon('arrow')}`,t.id,'pub-tool-shortcut')).join('')}</div></div><div>${section('便民办事','查询进度、查阅指南、提交意见。','services')}<div class="pub-service-links">${ordered(P().services).slice(0,6).map(s=>link('services',`${icon(s.kind==='notice'?'message':'file')}<span>${esc(s.name)}</span>${icon('arrow')}`,s.id,'')).join('')}</div></div></section><section class="pub-section">${section('大美内蒙古','生态优先、绿色发展，认识北疆自然与人文。','landscape')}<div class="pub-topics">${ordered(P().topics).map(topicCard).join('')}</div></section><section class="pub-section">${section('资讯与资料','政策法规、行业动态、技术标准和培训资源。','knowledge')}<div class="pub-news-list">${news.slice(0,4).map(r=>`<button data-action="portalKnowledge" data-id="${esc(r.id)}"><small>${esc(newsCategory(r))}</small><strong>${esc(r.name)}</strong><time>${esc(r.updated?.slice(0,10))}</time>${icon('arrow')}</button>`).join('')}</div></section></div>`;
  }
  function search(){
    const q=params().get('q')||'',category=params().get('category')||'全部';
    const collections=[['数据',data().map(r=>({...r,target:'data'}))],['工具',[...tools().map(r=>({...r,target:'capabilities'})),...D().resources.filter(r=>r.type==='工具服务').map(r=>({...r,target:'data'}))]],['资讯',(D().portalArticles||D().knowledge).map(r=>({...r,target:'news'}))]];
    const groups=collections.map(([type,rows])=>[type,rows.filter(r=>match(r,q))]),rows=groups.filter(([type])=>category==='全部'||type===category).flatMap(([,rows])=>rows);
    return title('综合搜索','检索已发布且当前身份可见的数据、工具与资讯。')+searchForm(q)+`<div class="pub-tabs">${[['全部',groups.reduce((n,[,r])=>n+r.length,0)],...groups.map(([t,r])=>[t,r.length])].map(([t,n])=>link('search',`${t} <b>${n}</b>`,'',category===t?'active':'',{q,category:t})).join('')}</div><p class="muted">${q?'关键词：'+esc(q):'全部内容'} · ${rows.length} 项结果</p><div class="pub-results">${pageRows(rows,r=>`<article><small>${esc(r.type||r.category)}</small><h2>${r.target==='news'?`<button data-action="portalKnowledge" data-id="${esc(r.id)}">${esc(r.name)}</button>`:link(r.target,esc(r.name),r.id,'')}</h2><p>${esc((r.summary||r.description||r.body||'').slice(0,180))}</p><span>${esc(r.source||r.region||'在线工具')}</span></article>`)}</div>`;
  }
  function pageRows(rows,render){const total=Math.max(1,Math.ceil(rows.length/8)),page=Math.max(1,Math.min(Number(params().get('page'))||1,total)),{route}=ctx.state();return rows.slice((page-1)*8,page*8).map(render).join('')+(rows.length?`<div class="pub-pagination"><span>共 ${rows.length} 项 · ${page}/${total}</span>${page>1?link(route,'上一页','','btn small',{...Object.fromEntries(params()),page:page-1}):''}${page<total?link(route,'下一页','','btn small',{...Object.fromEntries(params()),page:page+1}):''}</div>`:empty());}
  function catalog(){
    const q=params().get('q')||'',category=params().get('category')||'全部',region=params().get('region')||'全部',type=params().get('type')||'全部',sort=params().get('sort')||'最新';
    const rows=data().filter(r=>match(r,q)&&(category==='全部'||r.category===category)&&(region==='全部'||r.region===region)&&(type==='全部'||r.type===type)).sort((a,b)=>sort==='名称'?a.name.localeCompare(b.name,'zh'):String(b.updated).localeCompare(String(a.updated)));
    return title('数据服务','按主题查找数据集与图层，预览后申请使用。',btn('申请清单 '+ctx.cart().length,'cart','','primary','file')+link('applications','我的申请'))+`<form id="pub-data-filter" class="pub-filter"><label class="pub-field pub-filter-q"><span>关键词</span><input name="q" placeholder="资源名称、来源或关键词" value="${esc(q)}"></label>${field('category','主题',category,'select',['全部',...new Set(data().map(r=>r.category))])}${field('region','地区',region,'select',['全部',...new Set(data().map(r=>r.region))])}${field('type','类型',type,'select',['全部','数据库表','图层服务'])}${field('sort','排序',sort,'select',['最新','名称'])}<button class="btn primary">查询</button>${link('data','重置')}</form><div class="pub-grid">${pageRows(rows,r=>card(r))}</div>`;
  }
  function resource(id){
    const r=byId(D().resources,id);if(!r)return title('资源暂不可用','资源已下架或当前身份没有访问权限。',link('data','返回数据目录'));
    const map=r.type==='图层服务';return title(r.name,r.description,link('data','返回目录'))+`<div class="pub-detail-grid"><section class="panel pub-content"><div class="chips">${tag(r.type)}${tag(r.category)}${tag(r.access)}</div><h2>资源信息</h2><dl class="pub-definition">${[['提供单位',r.source],['数据源',r.dataSource||'本地示例'],['服务类型',r.serviceProtocol||'本地示例'],['覆盖范围',r.region],['坐标系',r.crs],['更新频次',r.frequency],['更新时间',r.updated?.slice(0,10)],['资源版本','v'+r.version],['使用限制','按授权范围和期限使用，当前数据为演示素材']].map(([k,v])=>`<dt>${k}</dt><dd>${esc(v)}</dd>`).join('')}</dl><h2>${map?'地图在线预览':'数据字段'}</h2>${map?'<div id="pub-resource-map" class="pub-map"></div><div id="pub-map-info" role="status"></div>':''}<div class="table-scroll"><table><thead><tr><th>字段</th><th>名称</th><th>类型</th><th>说明</th></tr></thead><tbody>${(r.fields||[]).map(f=>`<tr><td>${esc(f.name)}</td><td>${esc(f.label)}</td><td>${esc(f.type)}</td><td>${esc(f.description)}</td></tr>`).join('')}</tbody></table></div></section><aside><section class="panel pub-content pub-sticky"><h2>获取与使用</h2>${tag(r.access)}<p>查看来源、字段和使用范围，按需申请使用。</p>${r.access==='已授权'?btn('查看示例内容','preview',r.id,'primary','eye'):r.access==='可申请'?btn(ctx.cart().includes(r.id)?'已加入清单':'加入申请清单','addCart',r.id,'primary','plus'):link('applications','查看办理进度','','btn primary')}${r.access==='已授权'&&['数据库表','图层服务'].includes(r.type)?btn('下载示例数据','pub-download',r.id,'','download'):''}${r.access==='可申请'?btn('填写并提交申请','cart','','','file'):''}${link('applications','我的申请与授权')}<hr><h3>开发者服务</h3><p>外部服务由数据提供方运行，可能需要独立身份验证。</p>${r.access==='已授权'&&r.hasServiceUrl?btn('打开数据服务','pub-resource-link',r.id+':serviceUrl','','link'):''}${r.access==='已授权'&&r.hasDownloadUrl?btn('打开数据包下载','pub-resource-link',r.id+':downloadUrl','','download'):''}${!r.hasServiceUrl&&!r.hasDownloadUrl?'<p class="muted">尚未配置外部入口，可使用本地示例数据。</p>':''}${btn('了解资源内容','portalQuestion','介绍'+r.name,'text small','sparkles')}</section></aside></div>`;
  }
  const capabilityTitle=(name,description)=>`<header class="pub-tool-heading"><div><h1>${esc(name)}</h1><p>${esc(description)}</p></div></header>`;
  const toolCenter=createToolCenter(ctx);
  function capabilities(id){
    if(!id)return toolCenter.catalog();
    const t=toolCenter.find(id);if(!t)return capabilityTitle('工具已下架或不存在','请从目录选择可用工具。');
    const allowed=['直接使用','已授权'].includes(toolCenter.access(t));
    if(params().get('view')==='use'&&allowed&&!t.id.startsWith('resource:')&&!t.engine.startsWith('spatial-')){
      return `<div class="actions"><a class="btn" href="#/front/capabilities">返回工具目录</a>${link('capabilities','查看详情',id)}</div>`+capabilityRunner(id);
    }
    return toolCenter.detail(t)+(allowed&&!t.id.startsWith('resource:')&&!t.engine.startsWith('spatial-')?capabilityRunner(id).replaceAll('<h1>','<h2>').replaceAll('</h1>','</h2>'):'');
  }
  function capabilityRunner(id){
    if(!id)return title('工具中心','在线空间分析、项目选址核查与共享工具，按需使用专业能力。')+`<div class="pub-grid">${tools().map(t=>`<article class="panel pub-tool-card pub-capability-card"><div class="pub-capability-header"><span class="tile">${icon(t.icon)}</span><div><small>${esc(t.category)}</small><h2>${esc(t.name)}</h2></div></div><p>${esc(t.description)}</p><div class="pub-capability-footer">${tag(t.available?'可用':'待接入')}${link('capabilities',t.available?'开始使用':'查看说明',t.id,'btn '+(t.available?'primary':''))}</div></article>`).join('')}</div><section class="pub-section">${section('共享工具目录','已发布的工具资源，按权限申请使用。','search')}<div class="pub-grid">${D().resources.filter(r=>r.type==='工具服务').map(r=>card(r)).join('')}</div></section>`;
    const t=byId(tools(),id);if(!t)return capabilityTitle('工具已下架或不存在','请从工具中心选择已发布工具。');
    const engine=t.engine;
    if(['compliance','overlay'].includes(engine))return capabilityTitle(t.name,t.description)+'<div id="analysis-workbench"><p class="pub-note">正在加载分析工作台…</p></div>';
    if(engine==='external')return capabilityTitle(t.name,t.description)+`<section class="panel pub-content"><p>该工具由外部服务提供。</p>${btn('打开工具','pub-external',id,'primary')}</section>`;
    if(!t.available)return capabilityTitle(t.name,t.description)+`<section class="panel pub-content">${note('正式计算服务和业务数据尚未接入。')}<h2>使用前需要准备</h2><ul><li>输入范围、坐标系和必要参数。</li><li>已授权的业务图层及对应数据版本。</li><li>${id==='compliance'?'正式规划、生态红线、永久基本农田及审查规则。':'参与叠加的图层与所需空间关系。'}</li></ul>${link('map','浏览现有地图')}${link('services','查看办事与咨询')}</section>`;
    const sample='[[111.6,40.7],[111.8,40.7],[111.8,40.9],[111.6,40.9],[111.6,40.7]]';
    return capabilityTitle(t.name,t.description)+`<div class="pub-detail-grid"><section class="panel pub-content"><form id="pub-tool" data-tool="${engine}" data-tool-id="${esc(id)}">${engine==='coordinate'?field('direction','转换方向','forward','select',[['forward','WGS84 经纬度 → Web Mercator'],['inverse','Web Mercator → WGS84 经纬度']])+field('x','经度 / X','111.7','number')+field('y','纬度 / Y','40.8','number'):engine==='buffer'?field('x','经度','111.7','number')+field('y','纬度','40.8','number')+field('distance','缓冲距离（米）','1000','number'):field('geometry','坐标数组或 GeoJSON Polygon',sample,'textarea')+'<p class="muted">WGS84 经度、纬度，支持无孔洞、无自相交的单多边形。</p>'}<div class="form-footer"><button class="btn primary">运行计算</button>${engine==='area'?btn('在地图上绘制','pub-draw','','','layers'):''}</div></form><div id="pub-tool-result" aria-live="polite"></div></section><section><div id="pub-tool-map" class="pub-map"></div>${note(engine==='coordinate'?'仅作投影数值转换，不进行测绘基准转换。':'球面近似计算，仅用于分析体验，不作为测绘或审批依据。')}</section></div>`;
  }
  function service(id){
    if(!id)return title('办事服务','有问题先问，有事项直办，办理进度随时查。',link('requests','我的咨询与意见'))+`<section class="service-ask"><div class="service-ask-icon">${icon('sparkles')}</div><div class="service-ask-copy"><span class="pub-eyebrow">智能助手 · 为你指路</span><h2>想办什么事？先说说你的需求</h2><p>不知道从哪开始，可以问指南、找数据、查政策，也可以直接选择下方事项。</p><form id="service-ask-form"><label class="sr-only" for="service-question">描述办事需求</label><input id="service-question" name="question" required maxlength="1000" placeholder="例如：用地审批进度怎么查？"><button class="btn primary" type="submit">问问助手 ${icon('arrow')}</button></form><div class="service-examples"><span>常用问题与对比示例见下方</span>${link('assistant','继续上次对话','','pub-more')}</div></div></section>${qaExamples(esc,icon)}<div class="pub-section-head"><div><h2>常用办事事项</h2><p>选择事项，查看办理说明或提交咨询。</p></div>${link('applications','我的资源申请')}</div><div class="pub-grid">${ordered(P().services).map(s=>`<article class="panel pub-tool-card"><span class="tile">${icon(s.kind==='notice'?'message':'file')}</span><small>${esc(s.category)}</small><h2>${esc(s.name)}</h2><p>${esc(s.summary)}</p><div class="service-card-actions">${link('services',s.kind==='notice'?'查看公示':s.kind==='progress'?'查询进度':'查看服务',s.id,'btn primary')}${btn('问问助手','portalQuestion','我想了解'+s.name+'的办理流程和材料','text small','sparkles')}</div></article>`).join('')}</div>`;
    const s=byId(P().services,id);if(!s)return title('服务暂不可用','服务已下架或不存在。',link('services','返回办事服务'));
    return title(s.name,s.summary,link('services','返回办事服务'))+`<div class="pub-detail-grid"><section class="panel pub-content"><small>来源：${esc(s.source)} · ${esc(s.updated?.slice(0,10))}</small><div class="pub-prose">${para(s.body)}${['process','materials','timeLimit','phone'].map((key,i)=>s[key]?`<h3>${['办理流程','材料清单','办理时限','咨询电话'][i]}</h3>${para(s[key])}`:'').join('')}</div>${s.url?`<a class="btn primary" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">前往服务网站 ${icon('arrow')}</a>`:s.kind==='external'?note('正式查询入口待接入，可先提交咨询或查看相关数据目录。'):''}${s.kind==='progress'?`<form id="pub-progress">${field('query','项目编号或办件编号','','text')}<button class="btn primary">查询进度</button><p class="muted">仅查询当前演示身份可访问的办件。示例编号：project_demo_1。</p></form><div id="pub-progress-result" aria-live="polite"></div>`:''}</section><aside class="panel pub-content"><div class="service-detail-help"><span class="tile">${icon('sparkles')}</span><h2>办理前有疑问？</h2><p>让助手帮你找指南、了解办理步骤。</p>${btn('问问这个事项','portalQuestion','我想了解'+s.name+'的办理流程和材料','primary','sparkles')}</div><h2>${s.kind==='notice'?'提交公众意见':'服务咨询'}</h2><p>以当前演示身份提交，可在个人记录中跟踪受理与回复。</p><form id="pub-ticket" data-service="${esc(id)}">${field('title','标题')}${field('body',s.kind==='notice'?'意见内容':'咨询内容','','textarea')}<button class="btn primary">提交${s.kind==='notice'?'意见':'咨询'}</button></form>${link('requests','查看我的咨询与意见')}</aside></div>`;
  }
  function landscape(id){return landscapePage(id,{topics:P().topics,services:P().services,resources:data(),esc,icon});}
  function requests(){return title('我的咨询与意见','查看已提交记录、受理状态与回复。',link('services','发起新咨询'))+`<div class="pub-results">${P().tickets.slice().reverse().map(t=>`<article><div class="pub-section-head"><h2>${esc(t.title)}</h2>${tag(t.status)}</div><small>${esc(t.id)} · ${esc(t.serviceName)} · ${esc(t.createdAt)}</small>${para(t.body)}${t.history.map(h=>`<blockquote><strong>${esc(h.status)} · ${esc(h.actor)}</strong>${para(h.body)}<small>${esc(h.at)}</small></blockquote>`).join('')}</article>`).join('')||empty('暂无咨询或意见')}</div><section class="pub-section"><h2>我的数据下载</h2>${P().downloads.slice().reverse().map(d=>`<p>${esc(d.name)} · ${esc(d.format)} · v${d.version} · ${esc(d.at)}</p>`).join('')||'<p class="muted">暂无下载记录。</p>'}</section>`;}
  const contentNames={settings:'首页配置',services:'办事服务管理',tickets:'咨询与公众意见',topics:'大美内蒙古专题'};
  const contentTab=()=>Object.hasOwn(contentNames,params().get('tab'))?params().get('tab'):'topics';
  const online=r=>!!r.published&&!r.suspended&&r.status!=='已停用';
  const lifecycle=r=>`${tag(r.status)}<small>${online(r)?'线上 v'+r.version+(r.status==='草稿'?' · 有未发布修改':''):'前台不可见'}</small>`;
  function contentActions(entity,r){
    const key=entity+':'+r.id;
    return `<div class="actions">${btn('预览','pub-preview',key,'text small')}${btn('编辑','pub-edit',key,'text small')}${r.status!=='已发布'?btn(r.suspended?'上架发布':'发布','pub-publish',key,'text small'):''}${entity!=='settings'?(online(r)?btn('下架','pub-disable',key,'text small'):btn('删除','pub-delete',key,'text small')):''}</div>`;
  }
  function adminPage(){
    if(D().user.role!=='平台管理员')return title('暂无管理权限','请使用平台管理员身份管理公共门户。');
    const tab=contentTab(),q=(params().get('q')||'').trim(),status=params().get('status')||'';
    const heading=`<header class="page-heading"><div><div class="eyebrow">门户管理 / 内容管理</div><h1>${contentNames[tab]}</h1><p>${tab==='tickets'?'受理公众咨询与公示意见，处理结果仅对提交者可见。':'保存草稿后预览并发布，前台展示已发布版本。'}</p></div>${['topics','services'].includes(tab)?btn('新增'+(tab==='topics'?'专题':'服务'),'pub-edit',tab+':','primary','plus'):''}</header>`;
    if(tab==='settings'){
      const r=P().settings;
      return heading+`<section class="panel pub-content"><div class="pub-section-head"><h2>首页展示内容</h2><div>${lifecycle(r)}</div></div><h3>${esc(r.title)}</h3>${para(r.subtitle)}<p>推荐数据：${r.resourceIds?.length?esc(r.resourceIds.map(id=>byId(D().resources,id)?.name||'资源已移除').join('、')):'自动展示最新数据'}</p><p class="muted">推荐项按访问权限展示；草稿修改不会立即影响门户首页。</p>${contentActions(tab,r)}</section>`;
    }
    const statuses=tab==='tickets'?['待受理','处理中','已回复']:['草稿','已发布','已停用'];
    const all=tab==='tickets'?P().tickets.slice().reverse():ordered(P()[tab]);
    const rows=all.filter(r=>(!status||r.status===status)&&(!q||[r.name,r.title,r.category,r.serviceName,r.userName,r.id].join(' ').toLowerCase().includes(q.toLowerCase())));
    const count=Math.max(1,Math.ceil(rows.length/10)),page=Math.min(count,Math.max(1,Number.parseInt(params().get('page'),10)||1));
    const table=(heads,cells)=>`<div class="table-scroll"><table><thead><tr>${heads.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${cells.join('')||`<tr><td colspan="${heads.length}"><div class="empty"><h3>${all.length?'没有符合条件的记录':'暂无记录'}</h3><p>${tab==='tickets'?'公众在前台办事服务提交咨询或公示意见后，将显示在这里。':'请新增内容并保存草稿。'}</p></div></td></tr>`}</tbody></table></div>`;
    const visible=rows.slice((page-1)*10,page*10);
    const list=tab==='tickets'?table(['标题 / 编号','类型 / 关联事项','提交人','状态 / 时间','操作'],visible.map(t=>`<tr><td><strong>${esc(t.title)}</strong><small>${esc(t.id)}</small></td><td>${esc(t.kind)}<small>${esc(t.serviceName)}</small></td><td>${esc(t.userName)}</td><td>${tag(t.status)}<small>${esc(t.createdAt)}</small></td><td>${btn(t.status==='已回复'?'查看 / 补充回复':'受理 / 回复','pub-reply',t.id,'text small')}</td></tr>`)):table(['名称 / 分类','状态 / 线上版本','排序','更新时间','操作'],visible.map(r=>`<tr><td><strong>${esc(r.name)}</strong><small>${esc(r.category||'未分类')}</small></td><td>${lifecycle(r)}</td><td>${r.order??0}</td><td>${esc(r.updated||'—')}</td><td>${contentActions(tab,r)}</td></tr>`));
    return heading+`<form id="pub-admin-filter" class="pub-filter"><input type="hidden" name="tab" value="${tab}">${field('q',tab==='tickets'?'标题、事项、提交人或编号':'名称或分类',q)}${field('status','状态',status,'select',[['','全部状态'],...statuses])}<button class="btn primary">查询</button><a class="btn" href="#/admin/public-portal?tab=${tab}">重置</a></form><section class="panel pub-content-admin">${list}<div class="pagination"><span>共 ${rows.length} 条 · 第 ${page} / ${count} 页</span><div>${page>1?btn('上一页','pub-page',String(page-1),'small'):''}${page<count?btn('下一页','pub-page',String(page+1),'small'):''}</div></div></section>`;
  }
  function previewContent(entity,r){
    const guide=entity==='services'?['process','materials','timeLimit','phone'].map((key,i)=>r[key]?`<h3>${['办理流程','材料清单','办理时限','咨询电话'][i]}</h3>${para(r[key])}`:'').join(''):'';
    modal('草稿内容预览',`<div class="pub-content"><p class="muted">预览当前保存的内容，发布后才会更新前台。</p><h2>${esc(r.title||r.name)}</h2>${para(r.subtitle||r.summary)}${para(r.body)}${guide}${(r.sections||[]).map(x=>`<h3>${esc(x.title)}</h3>${para(x.text)}`).join('')}${r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">查看外部链接</a>`:''}${(r.media||[]).map(x=>`<p><a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)}</a> · ${esc(x.source)}</p>`).join('')}</div>`,true);
  }
  function reset(){analysisCleanup?.();analysisCleanup=null;generation++;controller?.destroy();controller=null;result=null;}
  async function mount(selector,resourceId='',topicResources=null){
    const token=generation,host=$(selector);if(!host)return;
    try{
      const config=await api('public.map',{resourceId});if(token!==generation||!host.isConnected)return;
      if(topicResources)config.layers=config.layers.filter(l=>topicResources.includes(l.resourceId));
      if(selector==='#pub-tool-map'){
        config.extent=[111.4,40.55,112,41.05];
        config.panorama=[...config.extent];
        config.cameraEnabled=false;
      }
      const mounted=await mountSceneMap(host,config,{onSelect:f=>{if($('#pub-map-info'))$('#pub-map-info').innerHTML=`<p>${esc(f.name)} · ${esc(f.region)} · ${esc(f.area)} ${esc(f.unit)} · ${esc(f.source)}</p>`;},onMeasure:r=>{if($('[name="geometry"]'))$('[name="geometry"]').value=JSON.stringify(r.coordinates);else if($('#pub-map-info'))$('#pub-map-info').textContent='球面近似面积：'+r.area+' 公顷';},onSelectRange:g=>{if($('[name="geometry"]'))$('[name="geometry"]').value=JSON.stringify(g);}});
      if(token!==generation||!host.isConnected){mounted?.destroy();return;}
      controller=mounted;
      if(result?.geometry)controller?.setSelection(result.geometry);
      if($('#pub-map-info'))$('#pub-map-info').innerHTML=note(config.layers.length?'专题图斑为授权的本地示例；可缩放、平移并点击图斑。':'当前未绑定可预览的专题图层，地图仅显示行政区划。');
      if($('#pub-map-layers'))$('#pub-map-layers').innerHTML=config.layers.map(l=>`<label><input type="checkbox" data-public-layer="${esc(l.id)}" ${l.visible?'checked':''} ${l.access!=='已授权'?'disabled':''}>${esc(l.name)} ${esc(l.access)}</label>`).join('')||'<p>暂无可用专题图层。</p>';
      if($('#pub-map-layers'))$('#pub-map-layers').onchange=e=>{const l=config.layers.find(l=>l.id===e.target.dataset.publicLayer);if(l){l.visible=e.target.checked;controller?.setLayers(config.layers);}};
    }catch(e){if(token===generation&&host.isConnected)host.innerHTML=note(e.message);}
  }
  function bindTool(id){
    reset();
    const currentTool=byId(tools(),id);
    if($('#analysis-workbench')&&currentTool&&['compliance','overlay'].includes(currentTool.engine))analysisCleanup=mountAnalysis($('#analysis-workbench'),{...ctx,api:(action,payload={})=>api(action,{...payload,toolId:id})},currentTool.engine);
    else if($('#pub-tool-map'))mount('#pub-tool-map','',[]);
  }
  function render(){
    reset();const {mode,route,id}=ctx.state();let html;
    if(mode==='admin'&&route==='public-portal')html=adminPage();
    else if(mode==='front'){
      if(route==='home')html=home();else if(route==='search')html=search();else if(route==='data')html=id?resource(id):catalog();else if(route==='capabilities')html=capabilities(id);else if(route==='services')html=service(id);else if(route==='landscape')html=landscape(id);else if(route==='requests')html=requests();else if(route==='map')html=title('地图浏览','浏览行政区划与已授权图层，点击图斑查看示例信息。',link('data','数据目录'))+'<div class="pub-map-layout"><aside class="panel pub-content"><h2>专题图层</h2><div id="pub-map-layers"></div></aside><div><div id="pub-main-map" class="pub-map pub-map-tall"></div><div id="pub-map-info" role="status"></div></div></div>';else return false;
    }else return false;
    $('#main').innerHTML=html;
    if(mode==='front'){
      if(route==='map')mount('#pub-main-map');
      if(route==='data'&&id)mount('#pub-resource-map',id);
      if(route==='landscape'&&!id)mount('#pub-landscape-map','',[]);
      if(route==='landscape'&&id)mount('#pub-topic-map','',byId(P().topics,id)?.resourceIds||[]);
      if(route==='capabilities'){bindTool(id);toolCenter.bind();if(params().get('view')==='use'&&$('#tc-test'))$('#tc-test').scrollIntoView({block:'start'});}
    }
    return true;
  }
  function download(filename,content,mime='application/json'){const url=URL.createObjectURL(new Blob([content],{type:mime+';charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=filename.replace(/[\\/:*?"<>|]/g,'_');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function edit(entity,id){
    const r=entity==='settings'?P().settings:byId(P()[entity],id)||{},settings=entity==='settings';
    modal(settings?'编辑首页配置':'编辑'+(entity==='topics'?'专题':'服务'),`<form id="pub-editor" data-entity="${entity}" data-id="${esc(id)}" data-rev="${r.rev||0}"><div class="pub-form-grid">${settings?field('title','首页标题',r.title)+field('subtitle','首页介绍',r.subtitle,'textarea'):field('name','名称',r.name)+field('category','分类',r.category)+field('summary','简介',r.summary,'textarea')+field('body','正文',r.body,'textarea')+field('source','来源',r.source)+field('url','外部资料 / 办理链接（HTTPS，可空）',r.url)}${entity==='topics'?field('cover','主题插画',r.cover||'nature','select',['nature','planning','energy','public','ecology','map','project','data','consult','cropland','hazard','knowledge'])+field('coverUrl','实景封面 HTTPS 地址（可空）',r.coverUrl)+field('coverCredit','封面来源 / 授权说明',r.coverCredit)+`<details class="scenic-editor"><summary>专题分节内容（最多 6 节）</summary>${Array.from({length:6},(_,i)=>{const item=guideFor(r).sections[i]||{};return `<div>${field('sectionTitle'+i,'第 '+(i+1)+' 节标题',item.title)}${field('sectionText'+i,'正文',item.text,'textarea')}</div>`;}).join('')}</details><details class="scenic-editor"><summary>影像与资料（最多 6 项；外部地址需有使用授权）</summary>${Array.from({length:6},(_,i)=>{const m=r.media?.[i]||{};return `<div>${field('mediaTitle'+i,'资料 '+(i+1)+' 标题',m.title)}${field('mediaType'+i,'类型',m.type||'image','select',[['image','图片'],['video','视频'],['document','图集 / 文档']])}${field('mediaUrl'+i,'HTTPS 地址',m.url)}${field('mediaSource'+i,'来源',m.source)}</div>`;}).join('')}</details>`:''}${entity==='services'?field('process','办理流程',r.process,'textarea')+field('materials','材料清单',r.materials,'textarea')+field('timeLimit','办理时限',r.timeLimit)+field('phone','咨询电话',r.phone)+field('kind','服务类型',r.kind||'guide','select',[['guide','办事指南'],['external','外部查询'],['notice','公示意见'],['progress','本人办件进度']]):`<fieldset class="pub-resource-picker"><legend>${settings?'首页推荐数据':'关联数据'}</legend>${data().map(item=>`<label><input type="checkbox" name="resourceIds" value="${esc(item.id)}" ${(r.resourceIds||[]).includes(item.id)?'checked':''}><span>${esc(item.name)}<small>${esc(item.type)} · ${esc(item.region)}</small></span></label>`).join('')}</fieldset>`}${!settings?field('order','排序',r.order??1,'number'):''}</div><p class="muted">保存为草稿后，点击发布才更新对外内容。未选择首页推荐数据时，首页自动展示最新数据。</p><div class="form-footer"><button class="btn primary">保存草稿</button></div></form>`,true);
  }
  async function action(action,id){
    if(action==='preview'&&ctx.state().mode==='front'&&byId(D().resources,id)?.type==='图层服务'){if(ctx.state().route==='data'&&ctx.state().id===id)$('#pub-resource-map')?.scrollIntoView({behavior:'smooth'});else nav('/front/data/'+encodeURIComponent(id));return true;}
    if(!action.startsWith('pub-'))return false;
    if(action==='pub-external'||action==='pub-resource-link'){
      const [key,kind]=id.split(':');const r=await api(action==='pub-external'?'portal.toolCheck':'portal.resourceAccess',action==='pub-external'?{id}:{id:key,kind});
      if(action==='pub-external')await api('portal.toolResult',{id,status:'打开入口',durationMs:0});
      modal('打开外部服务',`<p>服务由提供方运行。</p><a class="btn primary" href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">前往服务</a>`);
    }
    else if(action==='pub-topic-region'){controller?.locate(id);$('#pub-landscape-map')?.scrollIntoView({behavior:'smooth',block:'center'});}
    else if(action==='pub-download'){const r=await api('public.download',{id});download(r.filename,r.content,r.mime);await ctx.loadOnly();toast('已下载授权示例数据');}
    else if(action==='pub-draw')controller?.startSelection('polygon');
    else if(action==='pub-export'){if(result)download('空间分析结果.geojson',JSON.stringify(result,null,2),'application/geo+json');}
    else if(action==='pub-page'){const query=params();query.set('page',id);nav('/admin/public-portal?'+query);}
    else if(action==='pub-preview'){const [entity,key]=id.split(':');previewContent(entity,entity==='settings'?P().settings:byId(P()[entity],key));}
    else if(action==='pub-delete'){const [entity,key]=id.split(':'),r=byId(P()[entity],key);modal('删除内容',`<form id="pub-delete-confirm" data-entity="${entity}" data-id="${esc(key)}" data-rev="${r.rev}"><p>确认删除“${esc(r.name)}”？删除后无法在此页面恢复，已有咨询记录会保留。</p><button class="btn danger">确认删除</button></form>`);}
    else if(action==='pub-edit'){const [entity,key]=id.split(':');edit(entity,key);}
    else if(action==='pub-publish'||action==='pub-disable'){const [entity,key]=id.split(':'),r=entity==='settings'?P().settings:byId(P()[entity],key);await api(action==='pub-publish'?'public.publish':'public.disable',{entity,id:key,rev:r.rev});await ctx.reload();toast(action==='pub-publish'?'已发布，对外门户已更新':'已下架');}
    else if(action==='pub-reply'){const t=byId(P().tickets,id);modal('受理与回复',`<form id="pub-reply" data-id="${esc(id)}" data-rev="${t.rev}"><h3>${esc(t.title)}</h3><p>${esc(t.userName)} · ${esc(t.serviceName)} · ${esc(t.createdAt)}</p>${para(t.body)}${t.history.map(h=>`<blockquote><strong>${esc(h.status)} · ${esc(h.actor)} · ${esc(h.at)}</strong>${para(h.body)}</blockquote>`).join('')}${field('status','处理状态','已回复','select',t.status==='已回复'?['已回复']:['处理中','已回复'])}${field('reply','说明 / 回复','','textarea')}<div class="form-footer"><button class="btn primary">提交处理</button></div></form>`);}
    return true;
  }
  document.addEventListener('submit',async e=>{
    const f=e.target;if(!f.id.startsWith('pub-'))return;e.preventDefault();const v=Object.fromEntries(new FormData(f)),button=f.querySelector('button[type="submit"],button:not([type])');if(button?.disabled)return;if(button)button.disabled=true;
    try{
      if(f.id==='pub-admin-filter')nav('/admin/public-portal?'+new URLSearchParams(v));
      else if(f.id==='pub-delete-confirm'){await api('public.delete',{entity:f.dataset.entity,id:f.dataset.id,rev:Number(f.dataset.rev)});closeModal();await ctx.reload();toast('内容已删除');}
      else if(f.id==='pub-search')nav(href('search','',{q:v.q.trim()}).slice(1));
      else if(f.id==='pub-data-filter')nav(href('data','',v).slice(1));
      else if(f.id==='pub-progress'){const rows=await api('public.progress',{query:v.query});if(f.isConnected)$('#pub-progress-result').innerHTML=rows.map(c=>`<article><h3>${esc(c.name)} ${tag(c.status)}</h3><small>${esc(c.projectId)} · ${esc(c.id)}</small><ol class="pub-progress">${c.steps.map(s=>`<li>${esc(s.name)} ${tag(s.state)}</li>`).join('')}</ol></article>`).join('')||note('未找到可访问的办件，请核对编号与当前身份。');}
      else if(f.id==='pub-ticket'){await api('public.ticket',{...v,serviceId:f.dataset.service,requestId:ticketKey});ticketKey=randomUUID();toast('提交成功，可查看受理与回复');nav('/front/requests');}
      else if(f.id==='pub-reply'){await api('public.reply',{...v,id:f.dataset.id,rev:Number(f.dataset.rev)});closeModal();await ctx.reload();toast('处理结果已同步提交者');}
      else if(f.id==='pub-editor'){if(f.dataset.entity==='topics'){
        v.sections=Array.from({length:6},(_,i)=>({title:v['sectionTitle'+i],text:v['sectionText'+i]})).filter(x=>x.title?.trim()||x.text?.trim());
        v.media=Array.from({length:6},(_,i)=>({title:v['mediaTitle'+i],type:v['mediaType'+i],url:v['mediaUrl'+i],source:v['mediaSource'+i]})).filter(x=>x.title?.trim()||x.url?.trim()||x.source?.trim());
      }if(f.dataset.entity!=='services')v.resourceIds=new FormData(f).getAll('resourceIds');await api('public.save',{entity:f.dataset.entity,id:f.dataset.id,rev:Number(f.dataset.rev),values:v});closeModal();await ctx.reload();toast('草稿已保存，发布后对外生效');}
      else if(f.id==='pub-tool'){
        await api('portal.toolCheck',{id:f.dataset.toolId});f.dataset.started=String(performance.now());
        const output=$('#pub-tool-result');result=null;
        if(f.dataset.tool==='coordinate'){const r=convert(v.x,v.y,v.direction);const lon=v.direction==='forward'?Number(v.x):r.x,lat=v.direction==='forward'?Number(v.y):r.y;controller?.fitBounds([Math.max(-180,lon-.3),Math.max(-85,lat-.25),Math.min(180,lon+.3),Math.min(85,lat+.25)]);output.innerHTML=`<h2>转换结果</h2><dl class="pub-definition"><dt>目标坐标系</dt><dd>${r.crs}</dd><dt>X / 经度</dt><dd>${r.x.toFixed(6)}</dd><dt>Y / 纬度</dt><dd>${r.y.toFixed(6)}</dd><dt>单位</dt><dd>${r.unit}</dd></dl>`;}
        else {const ring=f.dataset.tool==='buffer'?buffer(v.x,v.y,v.distance):polygon(v.geometry),square=area(ring);result={type:'Feature',properties:{areaSquareMeters:square,calculation:'球面近似',inputCRS:'EPSG:4326'},geometry:{type:'Polygon',coordinates:[ring]}};controller?.setSelection(result.geometry);const xs=ring.map(p=>p[0]),ys=ring.map(p=>p[1]);controller?.fitBounds([Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]);output.innerHTML=`<h2>计算完成</h2><p class="pub-result-number">${(square/10000).toFixed(4)} <small>公顷</small></p><p>${square.toFixed(2)} 平方米 · ${(square/1000000).toFixed(6)} 平方千米</p>${btn('导出 GeoJSON','pub-export','','','download')}`;}
      }
        if(f.id==='pub-tool')await api('portal.toolResult',{id:f.dataset.toolId,status:'成功',durationMs:Math.max(0,performance.now()-Number(f.dataset.started))});
    }catch(error){toast(error.message);if(f.id==='pub-tool'){$('#pub-tool-result').innerHTML=note(error.message);if(f.dataset.started)await api('portal.toolResult',{id:f.dataset.toolId,status:'失败',error:error.message.slice(0,300),durationMs:Math.max(0,performance.now()-Number(f.dataset.started))}).catch(()=>{});}}
    finally{if(button?.isConnected)button.disabled=false;}
  });
  return {render,action,reset};
}
