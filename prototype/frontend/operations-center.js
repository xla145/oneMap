import {createOperationsSettings} from './operations-settings.js?v=20260917-config1';
import {createCollectionWorkflow, mappingValues, collectionStage} from './operations-workflow.js?v=20260917-simple1';
// Dedicated operations pages; existing center records remain the system of record.
export const operationGroups = [
  ['work','运营工作台',[['overview','运营总览','O01'],['todos','我的运营待办','O02']]],
  ['collection','数据归集管理',[['collection/overview','归集概览','G01'],['collection/tasks','归集任务','G02'],['collection/orders','归集工单','G03'],['collection/registrations','登记审核','G05'],['collection/imports','数据入库任务','G06']]],
  ['quality','数据质检管理',[['quality/models','质检模型与规则','Q01'],['quality/tasks','质检任务','Q02'],['quality/results','质检结果','Q03'],['quality/reports','数据质量报告','Q04'],['quality/orders','治理工单','Q05']]],
  ['catalog','数据编目管理',[['catalog/systems','来源系统','C01'],['catalog/sources','数源登记','C02'],['catalog/directories','技术资产目录','C03'],['catalog/assets','资产编目','C04'],['catalog/relations','资产关系','C05']]],
  ['standards','数据标准管理',[['standards/definitions','标准定义','S01'],['standards/changes','标准变更记录','S03']]],
  ['warehouse','数据建库管理',[['warehouse/domains','数据分域与数仓分层','B01'],['warehouse/tables','库表设计','B02']]],
  ['publishing','数据发布管理',[['publishing/apis','数据接口','P02'],['publishing/layers','图层服务登记','P04']]],
  ['monitoring','运行情况监控',[['monitoring/overview','运行总览','M01'],['monitoring/collection','归集监测','M03'],['monitoring/calls','服务调用','M04'],['monitoring/inspections','服务巡检','M05'],['monitoring/rules','告警规则','M06'],['monitoring/alerts','告警事件','M08']]],
];
export const operationMenu = ['operations/overview','operations/collection/tasks','operations/catalog/assets','operations/monitoring/alerts','operations/settings'];
export const operationLabels = {...Object.fromEntries(operationGroups.flatMap(g=>g[2].map(([path,label])=>['operations/'+path,label]))),'operations/overview':'工作台','operations/collection/tasks':'数据归集','operations/catalog/assets':'数据资产','operations/monitoring/alerts':'运行监控','operations/settings':'配置管理'};
export function operationSection(path) {
  if(['overview','todos','collection/overview'].includes(path))return 'operations/overview';
  if(path==='settings'||['quality/models','catalog/systems','catalog/sources','catalog/directories','standards/definitions','standards/changes','warehouse/domains'].includes(path))return 'operations/settings';
  if(path.startsWith('monitoring/'))return 'operations/monitoring/alerts';
  if(path.startsWith('catalog/')||path.startsWith('publishing/')||path.startsWith('warehouse/'))return 'operations/catalog/assets';
  return 'operations/collection/tasks';
}
const descriptors = {
  'collection/batches':['ingestions','centers','历史批次和报送数据统一办理；保留各自来源及执行记录。'],
  'collection/tasks':['tasks','operations','将任务下发给指定报送人员；每人独立工单，审核进度分别追踪。'],
  'collection/orders':['orders','operations','归集工单保留提交版本、审核意见和后续批次；报送人只能办理本人工单。'],
  'collection/registrations':['orders','operations','登记审核只确认材料；质量结论、入库和共享状态分别维护。'],
  'collection/imports':['imports','operations','将合格 CSV 按字段映射导入本地空表。每次失败与重试都有独立执行编号。'],
  'quality/models':['models','operations','本地模型组合必填、唯一、非负数、枚举和日期规则；发布后任务绑定模型版本。'],
  'quality/tasks':['qualityTasks','operations','任务定义与每次质检运行分离。首批支持手动执行；SQL、第三方模型与定时调度待接入。'],
  'quality/results':['qualityRuns','centers','执行完成不代表质量通过。报告保留数据版本、规则快照和标准版本。'],
  'quality/orders':['issues','centers','从质检报告派单，责任人反馈修正数据，复检通过后办结。'],
  'catalog/systems':['systems','centers','复用综合集成的来源系统记录，关联应用登记和归口联系人。'],
  'catalog/sources':['sources','centers','支持本地 CSV；数据库与 GIS 地址仅登记，连接和自动元数据采集仍待适配。'],
  'catalog/directories':['directories','operations','技术资产目录与资源中心共享目录分开维护，资产标识保持一致。'],
  'catalog/assets':['resources','root','已有资产可以直接编目，无须重新归集；技术编目不改变共享授权。'],
  'standards/definitions':['standards','centers','发布字段标准并保存版本。标准升级不自动改写已有表结构和质检报告。'],
  'warehouse/domains':['domains','operations','维护业务域、数仓层、数据库与数据空间的目录关系；本地配置不代表外部建库成功。'],
  'warehouse/tables':['datasets','centers','按已发布标准创建本地空表，完成字段映射后从入库任务导入数据。'],
  'publishing/apis':['publications','centers','发布本地查询接口，沿用资源使用授权。修改资源后需重新发布服务版本。'],
  'publishing/layers':['publications','centers','登记已有 WMS、MapService 等服务地址；未接入 GIS 引擎，不模拟发布成功。'],
  'monitoring/inspections':['inspections','centers','检查本地归集、交付和发布依赖状态，生成可处置的业务告警；不探测远程端点。'],
  'monitoring/rules':['alertRules','operations','配置本地巡检异常类型、级别和处置人；外部短信、钉钉通知尚未接入。'],
  'monitoring/alerts':['alerts','operations','确认 → 处理 → 验证关闭。指标恢复与人工关闭分别留痕。'],
};
const labels={name:'名称',id:'标识',status:'状态',createdAt:'创建时间',updated:'更新时间',rev:'配置修订',version:'发布版本',kind:'类型',sourceId:'数源',standardId:'标准',standardVersion:'采用标准版本',domainId:'数仓节点',dueAt:'截止时间',description:'说明',assigneeId:'处理人',assigneeName:'处理人',department:'责任单位',dataRevision:'数据版本',ingestionId:'归集批次',taskId:'来源任务',orderId:'归集工单',modelId:'质检模型',datasetId:'目标表',resourceId:'资产',resourceVersion:'发布的资源版本',qualityRunId:'质检报告',directoryId:'技术目录',parentId:'上级目录',tags:'标签',region:'区划',provider:'数源单位',endpoint:'服务地址',protocol:'协议',layer:'数仓分层',rowCount:'记录数',total:'检查条数',schedule:'执行方式',lastRunAt:'最近执行',level:'级别',count:'触发次数',lastSeenAt:'最近发生',recoveredAt:'恢复时间',notification:'通知状态',closedAt:'关闭时间',verificationId:'关闭验证巡检',reason:'异常原因',feedback:'整改说明',evidence:'处理依据',scope:'检查范围',field:'字段',argument:'规则参数',contact:'联系人',entry:'入口',adapter:'接入方式',appId:'应用登记',error:'失败原因',executionStatus:'执行状态',ruleId:'触发规则',targetId:'监控对象',inspectionId:'最近巡检',runId:'问题报告',reviewRunId:'复检报告'};
export function createOperationsCenter(ctx) {
  const {$,esc,btn,tag,api,toast}=ctx;
  const D=()=>ctx.state().D,C=()=>D().centers||{},O=()=>D().operations||{};
  const state=()=>{const [hash,search='']=location.hash.split('?');const parts=hash.replace(/^#\//,'').split('/').slice(2);let path=parts.slice(0,2).join('/');if(['overview','todos','settings'].includes(parts[0]))path=parts[0];const n=path.includes('/')?2:1;return {path:path||'overview',id:decodeURIComponent(parts[n]||''),edit:parts[n+1]==='edit',params:new URLSearchParams(search)};};
  const base=()=>'/'+ctx.state().mode+'/operations/';
  const href=(path,id='',edit=false)=>{
    const current=state(),params=new URLSearchParams(current.params);
    if(path!==current.path){
      for(const key of ['q','status','page','view','type','directory','config','record'])params.delete(key);
      if(current.id&&current.id!=='new'){const source=new URLSearchParams(current.params);source.delete('back');params.set('back',location.hash.split('?')[0]+(source.toString()?'?'+source:''));}
    }
    return '#'+base()+path+(id?'/'+encodeURIComponent(id):'')+(edit?'/edit':'')+(params.toString()?'?'+params:'');
  };
  const link=(path,label,id='',style='')=>`<a class="btn ${style}" href="${esc(href(path,id))}">${esc(label)}</a>`;
  const button=(label,action,id='',style='')=>btn(label,'oc-'+action,id,style);
  const pages=operationGroups.flatMap(g=>g[2]).concat([['collection/batches','数据批次','G07']]);
  const head=(title,desc,actions='')=>`<div class="page-heading"><div><div class="eyebrow">OPERATIONS CENTER · 运营中心</div><h1>${esc(title)}</h1><p>${esc(desc)}</p></div><div class="actions">${actions}</div></div>`;
  const table=(heads,rows)=>`<div class="table-scroll"><table><thead><tr>${heads.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${heads.length}"><div class="empty">暂无记录。可新建业务对象，或调整筛选条件。</div></td></tr>`}</tbody></table></div>`;
  const tr=(...values)=>`<tr>${values.map(v=>`<td>${v??'—'}</td>`).join('')}</tr>`;
  const options=(rows)=>rows.map(r=>[r.id,r.name]);
  const accountOptions=()=>D().accounts.map(r=>[r.id,r.name+' · '+r.department]);
  const workflow=createCollectionWorkflow({esc,tag,btn,field,table,tr,link,api,submit,reload:async()=>{dirty=false;await ctx.reload();},data:D,toast});
  const settingsUI=createOperationsSettings({esc,field,tag,api,data:D,head,table,tr,submit,load:()=>ctx.load(),render:()=>render(),setDirty:value=>{dirty=value;},toast});
  function localNav(path){
    if(!O().canManage)return '';
    const section=operationSection(path);
    const groups={
      'operations/overview':[['overview','工作台'],['todos','我的待办']],
      'operations/collection/tasks':[['collection/tasks','归集任务'],['collection/orders','报送记录'],['collection/batches','数据批次'],['quality/orders','整改待办']],
      'operations/catalog/assets':[['catalog/assets','数据资产'],['publishing/apis','数据接口'],['publishing/layers','已有图层服务'],['warehouse/tables','数据表']],
      'operations/monitoring/alerts':[['monitoring/alerts','异常处理'],['monitoring/inspections','巡检记录'],['monitoring/collection','归集状态'],['monitoring/calls','服务调用']]
    };
    if(section==='operations/settings')return path==='settings'?'':`<nav class="oc-local-nav" aria-label="配置导航">${link('settings','返回配置管理')}</nav>`;
    return `<nav class="oc-local-nav" aria-label="运营业务导航">${groups[section].map(([p,label])=>link(p,label,'',path===p?'active':'')).join('')}</nav>`;
  }
  function settingsView(){return settingsUI.render();}
  function rowsFor(path) {
    const [entity,scope]=descriptors[path]||[];let rows=scope==='root'?D()[entity]||[]:scope==='operations'?O()[entity]||[]:C()[entity]||[];
    if(path==='publishing/apis')rows=rows.filter(r=>r.protocol==='本地数据接口');
    if(path==='publishing/layers')rows=rows.filter(r=>r.protocol!=='本地数据接口');
    return rows;
  }
  function refName(key,id){
    const map={resourceId:D().resources,standardId:C().standards,sourceId:C().sources,domainId:O().domains,ruleId:O().alertRules,assigneeId:D().accounts,modelId:O().models,ingestionId:C().ingestions,taskId:[...(O().tasks||[]),...(O().qualityTasks||[])],datasetId:C().datasets,directoryId:O().directories,orderId:O().orders,qualityRunId:C().qualityRuns,runId:C().qualityRuns,reviewRunId:C().qualityRuns,appId:D().platform?.apps};
    return map[key]?.find(r=>r.id===id)?.name||id||'—';
  }
  function associations(r){
    if(!O().canManage)return '';
    const paths={ruleId:'monitoring/rules',inspectionId:'monitoring/inspections',verificationId:'monitoring/inspections',domainId:'warehouse/domains',resourceId:'catalog/assets',standardId:'standards/definitions',sourceId:'catalog/sources',ingestionId:'quality/results',orderId:'collection/orders',modelId:'quality/models',datasetId:'warehouse/tables',qualityRunId:'quality/results',runId:'quality/results',reviewRunId:'quality/results',directoryId:'catalog/directories'};
    let html=Object.entries(paths).filter(([key])=>r[key]).map(([key,path])=>key==='ingestionId'?link('collection/batches','报送办理 · '+refName(key,r[key]),r[key],'small'):link(path,labels[key]+' · '+refName(key,r[key]),r[key],'small')).join('');
    if(r.taskId){const path=O().tasks?.some(x=>x.id===r.taskId)?'collection/tasks':'quality/tasks';html+=link(path,'来源任务',r.taskId,'small');}
    return `<div class="oc-links">${html}</div>`;
  }
  const editable=new Set(['tasks','models','qualityTasks','imports','directories','catalogs','domains','alertRules','systems','sources','standards','publications']);
  function actions(path,r){
    const entity=descriptors[path]?.[0], manage=O().canManage;let out='';
    if(manage && editable.has(entity) && !(entity==='tasks'&&r.status!=='草稿') && !(entity==='imports'&&!['草稿','失败'].includes(r.status)))out+=`<a class="btn small text" href="${esc(href(path,r.id,true))}">编辑</a>`;
    if(manage && (entity==='tasks'&&r.status==='草稿'||entity==='models'&&!r.published||entity==='imports'&&!r.attempts.length||['directories','domains'].includes(entity)))out+=button('删除检查','delete',r.id,'small text');
    if(manage && entity==='tasks'&&r.status==='草稿')out+=button('下发','dispatch',r.id,'small primary');
    if(entity==='orders'){
      if(r.assigneeId===D().user.id && ['待填报','草稿','已退回'].includes(r.status))out+=link('collection/orders','填报',r.id+'/fill','small');
      if(manage && r.status==='待审核')out+=button('审核','review',r.id,'small primary');
    }
    if(manage && entity==='models'&&r.status==='草稿')out+=button('发布模型','publish-model',r.id,'small');
    if(manage && entity==='qualityTasks')out+=button('立即执行','run-quality',r.id,'small primary');
    if(manage && entity==='imports'&&['草稿','失败'].includes(r.status))out+=button(r.status==='失败'?'重试入库':'执行入库','run-import',r.id,'small primary');
    if(manage && entity==='qualityRuns'&&r.issues?.length)out+=btn('发起治理','ct-create-issue',r.id,'small');
    if(entity==='issues'){
      if(r.assigneeId===D().user.id&&['待处理','已退回'].includes(r.status))out+=button('整改反馈','feedback',r.id,'small primary');
      if(manage&&r.status==='待复核')out+=btn('复检复核','ct-review-issue',r.id,'small');
    }
    if(manage && entity==='standards'&&r.status==='草稿')out+=btn('发布标准','ct-publish-standard',r.id,'small');
    if(manage && entity==='sources')out+=btn('检查配置','ct-check-source',r.id,'small');
    if(manage && entity==='publications'&&r.protocol==='本地数据接口'){
      out+=button('发布检查','publish-service',r.id,'small');
      if(r.status==='已发布')out+=btn('试查询','ct-query-service',r.id,'small')+button('停用检查','disable-service',r.id,'small');
    }
    if(manage && entity==='alerts')out+=button(({待确认:'确认告警',处理中:'提交处理',待验证:'验证关闭',已关闭:'重新打开'})[r.status],'alert',r.id,'small');
    return out;
  }
  function row(path,r){
    const e=descriptors[path][0];let info='',status=tag(r.status||'草稿');
    if(e==='tasks')info=`${r.assigneeIds.length} 名报送人 · ${esc(r.dueAt)}<small>已通过 ${O().orders.filter(x=>x.taskId===r.id&&x.status==='已通过').length} / ${O().orders.filter(x=>x.taskId===r.id).length} 份登记</small>`;
    else if(e==='orders')info=`${esc(r.assigneeName)} · ${esc(r.department)}<small>提交 ${r.submissions?.length||0} 次 · 数据 v${r.dataRevision}</small>`;
    else if(e==='ingestions'){const report=C().qualityRuns.find(x=>x.id===r.qualityRunId);info='数据 v'+r.dataRevision;status=tag(collectionStage(null,r,report,C().issues.filter(x=>x.ingestionId===r.id)).label);}
    else if(e==='models')info=`${r.ruleIds.length} 条规则 · 发布 v${r.published?.version||0}<small>${esc(r.kind)}</small>`;
    else if(e==='qualityTasks')info=`${esc(refName('ingestionId',r.ingestionId))}<small>模型 v${r.modelSnapshot.version} · ${r.runIds.length} 次执行</small>`;
    else if(e==='qualityRuns'){info=`${r.total} 行 · ${r.issues.length} 项问题<small>数据 v${r.dataRevision} · 标准 v${r.standardSnapshot?.version||'—'}</small>`;status=tag('已完成')+' '+tag(r.passed?'质量通过':'质量不通过');}
    else if(e==='imports')info=`${esc(refName('datasetId',r.datasetId))}<small>${r.attempts.length} 次执行 · ${esc(r.attempts.at(-1)?.error||'字段映射至本地空表')}</small>`;
    else if(e==='resources'){const cat=O().catalogs?.find(x=>x.resourceId===r.id);info=`${esc(r.type)} · ${esc(r.region)}<small>${esc(cat?.department||r.source||'待确认责任单位')}</small>`;status=tag(cat?'已编目':'未编目')+' '+tag(r.status==='已停用'||r.suspended?'资源已停用':r.published?'有发布版本':'未发布');}
    else if(e==='datasets')info=`${esc(r.layer)} · ${r.rowCount} 行<small>标准 v${r.standardVersion} · ${esc(r.resourceId)}</small>`;
    else if(e==='standards')info=`${r.fields.length} 项字段 · v${r.version}`;
    else if(e==='publications')info=`${esc(r.protocol)} · 资源 v${r.resourceVersion||'—'}<small>${esc(refName('resourceId',r.resourceId))}</small>`;
    else if(e==='issues')info=`${esc(r.assigneeName)}<small>${esc(refName('ingestionId',r.ingestionId))}</small>`;
    else if(e==='alerts')info=`${esc(r.level)} · ${r.count} 次<small>${esc(r.reason)} · ${r.recoveredAt?'指标已恢复':'待巡检确认恢复'}</small>`;
    else if(e==='inspections')info=`${r.failures.length} 项异常<small>${esc(r.scope)}</small>`;
    else info=esc(r.provider||r.kind||r.adapter||'')+(r.parentId?`<small>上级：${esc(rowsFor(path).find(x=>x.id===r.parentId)?.name||r.parentId)}</small>`:'');
    if(e==='orders'){const b=C().ingestions.find(x=>x.id===r.ingestionId);if(O().canManage)status=tag(collectionStage(r,b,C().qualityRuns.find(x=>x.id===b?.qualityRunId),C().issues.filter(x=>b&&x.ingestionId===b.id)).label);}
    if(e==='tasks'&&r.status==='已完成')status=tag('报送审核已完成');
    return tr(`<a class="oc-record" href="${esc(href(path,r.id))}">${esc(r.name)}</a><small>${esc(r.id)}</small>`,info,status,esc(r.updated||r.createdAt||'—'),`<div class="oc-actions">${link(path,'详情',r.id,'small text')}${actions(path,r)}</div>`);
  }
  function filterRows(rows){const p=state().params,q=p.get('q')||'',status=p.get('status')||'';return rows.filter(r=>(!q||JSON.stringify(r).toLowerCase().includes(q.toLowerCase()))&&(!p.get('type')||r.type===p.get('type'))&&(!p.get('directory')||O().catalogs.some(c=>c.resourceId===r.id&&c.directoryId===p.get('directory')))&&(!status||(status==='未办结'?r.status!=='已办结':status==='未关闭'?r.status!=='已关闭':r.status===status)));}
  function search(rows){const p=state().params;const assetFilters=state().path==='catalog/assets'?`<select name="type" aria-label="资产类型"><option value="">全部类型</option>${[...new Set(rows.map(r=>r.type))].map(t=>`<option value="${esc(t)}" ${p.get('type')===t?'selected':''}>${esc(t)}</option>`).join('')}</select><select name="directory" aria-label="技术目录"><option value="">全部目录</option>${O().directories.map(d=>`<option value="${esc(d.id)}" ${p.get('directory')===d.id?'selected':''}>${esc(d.name)}</option>`).join('')}</select>`:'';return `<form id="oc-search" class="ct-search"><input name="q" aria-label="搜索运营记录" placeholder="搜索名称、编号、单位" value="${esc(p.get('q')||'')}"><select name="status" aria-label="业务状态"><option value="">全部状态</option>${[...new Set([...(rows.some(r=>r.status==='已办结')?['未办结']:[]),...(rows.some(r=>r.status==='已关闭')?['未关闭']:[]),p.get('status'),...rows.map(r=>r.status)].filter(Boolean))].map(s=>`<option ${p.get('status')===s?'selected':''}>${esc(s)}</option>`).join('')}</select>${assetFilters}<button class="btn primary">查询</button>${button('重置','reset')}</form>`;}
  function list(path){
    const [entity,,desc]=descriptors[path];let top='';
    if(O().canManage&&editable.has(entity))top=link(path,'新增','new','primary');
    if(path==='warehouse/tables')top=link(path,'按标准建表','new','primary');
    if(path==='catalog/assets')top=link('catalog/assets','选择资产编目','new','primary')+'<a class="btn" href="#/admin/resources">登记已有资产</a>';
    if(path==='monitoring/alerts')top=button('执行巡检','inspect','','primary');
    if(path==='collection/batches')top=btn('登记历史批次','ct-edit','ingestions:','primary');
    if(path==='monitoring/inspections')top=button('执行本地巡检','inspect','','primary');
    const all=rowsFor(path),filtered=filterRows(all).slice().reverse(),page=Math.min(Math.max(1,Number(state().params.get('page'))||1),Math.max(1,Math.ceil(filtered.length/10)));
    let html=head(({'collection/tasks':'数据归集','catalog/assets':'数据资产','monitoring/alerts':'运行监控'})[path]||pages.find(x=>x[0]===path)?.[1]||path,desc,top)+search(all)+`<section class="panel">${table(['名称 / 标识','业务信息','状态','更新时间','操作'],filtered.slice((page-1)*10,page*10).map(r=>row(path,r)))}</section><div class="pagination"><span>共 ${filtered.length} 条 · ${page} / ${Math.max(1,Math.ceil(filtered.length/10))} 页</span><div>${page>1?button('上一页','page',String(page-1)):''}${page*10<filtered.length?button('下一页','page',String(page+1)):''}${button('导出当前筛选','export')}</div></div>`;
    if(path==='quality/models')html+=`<section class="panel oc-panel"><div class="oc-section-title"><h2>模型可复用的规则</h2>${btn('新增规则','ct-edit','rules:','small')}</div>${table(['规则','字段','校验方式','状态','操作'],(C().rules||[]).map(r=>tr(esc(r.name),esc(r.field),esc(r.kind),tag(r.status),btn('编辑','ct-edit','rules:'+r.id,'small'))))}</section>`;
    if(path==='collection/tasks')html+=`<p class="muted">任务按报送人分别跟踪。审核通过后，在报送详情继续质检、整改和入库。</p>`;
    return html;
  }
  function batchList(){return `<section class="panel oc-panel"><h2>归集批次 · 质检与入库准备</h2><p class="muted">登记通过的工单与历史批次汇聚于此。先质检，再选择空表配置映射；旧批次仍可使用原有登记入库入口。</p>${btn('新增管理员批次','ct-edit','ingestions:','small')}${table(['批次','数据版本 / 质量','状态','操作'],(C().ingestions||[]).slice().reverse().map(r=>tr(link('collection/batches',r.name,r.id,'text'),`v${r.dataRevision} · ${r.qualityRunId?link('quality/results','查看报告',r.qualityRunId,'small'):'尚未质检'}`,tag(r.status),(['草稿','已退回'].includes(r.status)?btn('编辑','ct-edit','ingestions:'+r.id,'small')+btn('提交质检','ct-submit-ingestion',r.id,'small'):'')+(['待质检','待整改','待登记'].includes(r.status)?btn('执行质检','ct-check-ingestion',r.id,'small'):'')+link('collection/batches','继续办理',r.id,'small'))))}</section>`;}
  function cards(items){return `<div class="oc-metrics">${items.map(([label,value,path,desc,status])=>`<a href="#${base()+path}${status?'?status='+encodeURIComponent(status):''}"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(desc)}</small></a>`).join('')}</div>`;}
  function overview(path){
    const admin=O().canManage;if(!admin)return todoView();
    const quality=C().qualityRuns||[],ingestions=C().ingestions||[];
    let title=path==='overview'?'工作台':pages.find(p=>p[0]===path)?.[1]||'工作台';
    let html=head(title,'收好数据、管清资产、处理异常 · 更新于 '+(D().serverTime||'') ,link('collection/tasks','新建归集任务','new','primary')+button('执行业务巡检','inspect'));
    html+=cards([
      ['待审核登记',O().orders.filter(r=>r.status==='待审核').length,'collection/registrations','口径：待审核工单数','待审核'],
      ['未办结治理工单',C().issues.filter(r=>r.status!=='已办结').length,'quality/orders','口径：未办结工单数','未办结'],
      ['入库失败',O().imports.filter(r=>r.status==='失败').length,'collection/imports','口径：最近一次执行失败的任务','失败'],
      ['未关闭业务告警',O().alerts.filter(r=>r.status!=='已关闭').length,'monitoring/alerts','口径：尚未人工关闭的事件','未关闭'],
    ]);
    if(path.startsWith('monitoring')){
      html+=`<section class="panel oc-panel"><h2>运行观测范围</h2><p>业务异常来自本地巡检记录。主机和请求指标复用系统监控；远端数据库、GIS 引擎及中间件暂无采样数据。</p><div class="actions"><a class="btn" href="#/admin/portal-monitor">主机与请求监控</a><a class="btn" href="#/admin/portal-audit">统一日志</a>${link('monitoring/inspections','查看巡检记录')}${link('monitoring/alerts','处置业务告警')}</div></section>`;
      html+=table(['最近巡检','异常数','结果','检查范围'],C().inspections.slice(-8).reverse().map(r=>tr(link('monitoring/inspections',r.name,r.id,'text'),r.failures.length,tag(r.status),esc(r.scope))));
    }else{
      html+=todoView(true);
      html+=`<details class="oc-record-details"><summary>业务说明与历史统计</summary><section class="panel oc-panel"><h2>新增成果数据</h2><div class="oc-flow">${[['collection/tasks','1 下发任务'],['collection/registrations','2 登记审核'],['quality/tasks','3 质检整改'],['collection/imports','4 映射入库'],['catalog/assets','5 技术编目'],['publishing/apis','6 发布接口']].map(([p,l])=>link(p,l)).join('')}</div><p class="muted">技术发布后，共享申请、授权与交付继续在资源中心办理。</p></section><section class="panel oc-panel"><h2>已有资产纳管</h2><p>登记数源或已有服务 → 确认来源与责任单位 → 技术编目 → 共享与监控。已有资产不要求重新归集入库。</p><div class="actions">${link('catalog/sources','登记数源')}${link('catalog/assets','资产编目')}<a class="btn" href="#/admin/center-resources">资源中心共享管理</a></div></section>`;
      html+=cards([['归集批次',ingestions.length,'collection/imports','口径：全部历史批次'],['质检通过率',quality.length?Math.round(quality.filter(r=>r.passed).length/quality.length*100)+'%':'暂无数据','quality/reports',`分母：${quality.length} 次运行（含复检）`],['已编目资产',O().catalogs.length,'catalog/assets','口径：技术目录挂接数'],['已发布本地接口',C().publications.filter(r=>r.protocol==='本地数据接口'&&r.status==='已发布').length,'publishing/apis','口径：服务发布状态']])+'</details>';
    }
    return html;
  }
  function todoView(compact=false){const rows=O().todos||[];return (compact?'<section class="panel oc-panel"><h2>今天需要办理</h2>':head('我的运营待办','查看本人需要办理的报送、审核、整改和告警。'))+(rows.length?table(['待办','来源','截止时间','状态','办理'],rows.map(r=>tr(esc(r.name),esc(r.source),esc(r.dueAt||'未设置'),tag(r.status),`<a class="btn small primary" href="${esc(r.entry)}">进入办理</a>`))):'<div class="empty">当前没有需要你办理的事项。</div>')+(compact?'</section>':'');}
  function reportView(){const runs=filterRows(C().qualityRuns||[]);return head('数据质量报告','统计全部符合筛选条件的运行，含复检；问题记录数按检查项计数，同一行可以产生多项问题。')+search(C().qualityRuns||[])+cards([['检查次数',runs.length,'quality/results','分母：当前筛选运行次数'],['通过次数',runs.filter(r=>r.passed).length,'quality/results','质量通过的运行数'],['问题项总数',runs.reduce((sum,r)=>sum+r.issues.length,0),'quality/results','历史运行问题总数，不等于当前未治理数'],['未办结工单',C().issues.filter(r=>r.status!=='已办结').length,'quality/orders','全部当前未办结工单，不随报告筛选']])+table(['报告','检查行数','问题项','质量结论'],runs.map(r=>tr(link('quality/results',r.name,r.id,'text'),r.total,r.issues.length,tag(r.status))));}
  function detail(path,r){
    let html=head(r.name||'对象详情',(pages.find(x=>x[0]===path)?.[1]||'')+' · '+r.id,link(path,'返回列表')+actions(path,r));
    const back=state().params.get('back');if(back&&/^#\/(admin|front)\/operations\/[a-z-]+\/[a-z-]+\/[^/?#]+(?:\?[^#]*)?$/.test(back))html+=`<div class="oc-links"><a class="btn" href="${esc(back)}">返回来源办理页</a></div>`;
    if(path==='catalog/assets')return assetDetail(r,html);
    const hasWorkflow=['collection/orders','collection/batches'].includes(path);
    if(hasWorkflow){const batch=path==='collection/batches'?r:C().ingestions.find(x=>x.id===r.ingestionId);html+=workflow.render(path==='collection/orders'?r:null,batch);}
    if(hasWorkflow)html+=`<details class="oc-record-details" ${!O().canManage||r.status==='待审核'?'open':''}><summary>基本信息、材料与处理记录</summary>`;
    html+=`<section class="panel oc-panel"><div class="oc-status">${tag(r.status)}${path==='quality/results'?tag('执行已完成')+' '+tag('数据 v'+r.dataRevision):''}</div><dl class="detail-grid">${Object.entries(labels).filter(([key])=>r[key]!==undefined && typeof r[key]!=='object' && !['id','name'].includes(key)).map(([key,label])=>`<dt>${esc(label)}</dt><dd>${esc(key.endsWith('Id')?refName(key,r[key]):r[key]||'—')}</dd>`).join('')}</dl>${associations(r)}</section>`;
    if(path==='collection/tasks')html+=`<section class="panel oc-panel"><h2>单位报送工单</h2>${table(['报送记录','报送人','审核状态','后续办理'],O().orders.filter(x=>x.taskId===r.id).map(x=>tr(link('collection/orders',x.name,x.id,'text'),esc(x.assigneeName),tag(x.status),x.ingestionId?link('collection/orders','继续质检 / 入库',x.id,'small'):esc('等待材料审核'))))}</section>`;
    if(path==='collection/orders'&&r.assigneeId===D().user.id&&['待填报','草稿','已退回'].includes(r.status))html+=orderForm(r);
    if(path==='collection/orders'&&r.standardSnapshot)html+=`<section class="panel oc-panel"><h2>报送采用标准 · ${esc(r.standardSnapshot.name)} v${r.standardVersion}</h2>${table(['字段','中文名','类型','必填'],r.standardSnapshot.fields.map(f=>tr(esc(f.name),esc(f.label),esc(f.type),f.required?'是':'否')))}</section>`;
    if(r.issues)html+=`<section class="panel oc-panel"><h2>质量问题 · ${r.issues.length} 项</h2><p>标准：${esc(r.standardSnapshot?.name||'未关联')} v${r.standardSnapshot?.version||'—'}；模型 v${r.modelSnapshot?.version||'—'}；数据指纹 ${esc(r.inputHash||'—')}</p><p>规则依据：${(r.ruleSnapshots||[]).map(x=>esc(x.name)+' / 修订 '+x.rev).join('、')}</p>${table(['数据行','字段','规则','问题'],r.issues.map(x=>tr(esc(x.row||'表头'),esc(x.field),esc(x.rule),esc(x.message))))}${button('导出报告','export-record',r.id)}</section>`;
    if(r.ruleIds||r.modelSnapshot?.rules){const rules=r.modelSnapshot?.rules||r.ruleIds.map(id=>C().rules.find(x=>x.id===id)).filter(Boolean);html+=`<section class="panel oc-panel"><h2>${r.modelSnapshot?'任务绑定的规则快照':'模型编辑版规则'}</h2><p>${r.published?'当前已发布版本 v'+r.published.version+'；草稿编辑不会覆盖已绑定任务的模型快照。':''}</p>${table(['规则','字段','检查类型','配置修订'],rules.map(x=>tr(esc(x.name),esc(x.field),esc(x.kind),x.rev)))}</section>`;}
    if(r.versions?.length)html+=`<section class="panel oc-panel"><h2>历史标准版本</h2>${r.versions.slice().reverse().map(v=>`<details><summary>v${v.version} · ${esc(v.at)}</summary>${table(['字段','中文名','类型','必填'],(v.fields||[]).map(f=>tr(esc(f.name),esc(f.label),esc(f.type),f.required?'是':'否')))}</details>`).join('')}</section>`;
    if(path==='monitoring/alerts'){const batch=C().ingestions.find(x=>x.id===r.targetId);html+=`<section class="panel oc-panel"><h2>异常来源</h2>${batch?link('collection/batches','处理该批次异常',batch.id):r.kind==='服务依赖异常'?link('publishing/apis','查看异常服务',r.targetId):'<a class="btn" href="#/admin/center-resources">查看交付台账</a>'}<a class="btn" href="#/admin/portal-audit">统一日志审计</a></section>`;}
    if(r.fields?.length)html+=`<section class="panel oc-panel"><h2>表结构 / 标准字段</h2>${table(['字段','中文名','类型','必填'],r.fields.map(f=>typeof f==='string'?tr(esc(f),'—','见采用标准','—'):tr(esc(f.name),esc(f.label),esc(f.type),f.required?'是':'否')))}</section>`;
    if(r.mapping)html+=`<section class="panel oc-panel"><h2>入库字段映射</h2>${table(['目标字段','来源字段'],Object.entries(r.mapping).map(([a,b])=>tr(esc(a),esc(b))))}</section>`;
    if(r.attempts)html+=`<section class="panel oc-panel"><h2>执行历史</h2>${table(['执行编号','时间','结果','记录数 / 原因'],r.attempts.slice().reverse().map(x=>tr(esc(x.id),esc(x.at),tag(x.status),esc(x.error||x.rowCount))))}</section>`;
    if(r.runIds)html+=`<section class="panel oc-panel"><h2>质检运行历史</h2>${r.runIds.slice().reverse().map(id=>link('quality/results',id,id)).join('')||'<p>尚未执行</p>'}</section>`;
    if(r.failures)html+=`<section class="panel oc-panel"><h2>异常明细</h2>${table(['类型','对象','原因'],r.failures.map(x=>tr(esc(x.kind),esc(x.name),esc(x.reason))))}</section>`;
    if(r.submissions?.length)html+=`<section class="panel oc-panel"><h2>历次报送材料</h2>${r.submissions.slice().reverse().map(x=>`<details><summary>${esc(x.at)} · 数据 v${x.dataRevision}</summary><pre class="ct-json">${esc(x.dataRows)}</pre></details>`).join('')}</section>`;
    if(r.dataRows)html+=`<section class="panel oc-panel"><details><summary>当前 CSV 数据</summary><pre class="ct-json">${esc(r.dataRows)}</pre></details></section>`;
    html+=history(r);if(hasWorkflow)html+='</details>';return html;
  }
  function history(r){return `<section class="panel oc-panel"><h2>操作轨迹</h2><div class="ct-history">${(r.history||[]).slice().reverse().map(h=>`<p><small>${esc(h.at)} · ${esc(h.actor)}</small><strong>${esc(h.action)}</strong> ${esc(h.note||'')}</p>`).join('')||'<p class="muted">暂无操作记录</p>'}</div></section>`;}
  function assetDetail(r,html){
    const catalog=O().catalogs.find(x=>x.resourceId===r.id),datasets=C().datasets.filter(x=>x.resourceId===r.id),services=C().publications.filter(x=>x.resourceId===r.id),q=C().qualityRuns.filter(x=>datasets.some(d=>d.ingestionId===x.ingestionId));
    const sections=['基本信息','质量与更新','服务与共享','关联与历史'];const old=state().params.get('view');const selected=({'技术元数据':'基本信息','标准与质量':'质量与更新','来源与关系':'关联与历史','发布与共享':'服务与共享','AI 标注':'关联与历史','版本与记录':'关联与历史'})[old]||old||sections[0];
    html+=`<div class="tabs oc-tabs">${sections.map(t=>button(t,'asset-tab',t,t===selected?'active':'')).join('')}</div><section class="panel oc-panel"><div class="oc-status">${tag(catalog?'已编目':'未编目')}${tag(r.status==='已停用'||r.suspended?'资源已停用':r.published?'资源有线上 v'+r.published.version:'资源未发布')}${tag(services.some(x=>x.status==='已发布')?'技术服务已发布':'技术服务未发布')}${tag('共享：'+(r.sharingPolicy||'申请使用'))}</div>`;
    if(selected==='基本信息')html+=`<dl class="detail-grid"><dt>资产类型</dt><dd>${esc(r.type)}</dd><dt>责任单位</dt><dd>${esc(catalog?.department||r.source||'待确认')}</dd><dt>区划</dt><dd>${esc(r.region)}</dd><dt>技术目录</dt><dd>${esc(O().directories.find(x=>x.id===catalog?.directoryId)?.name||'未挂接')}</dd><dt>标签</dt><dd>${esc(catalog?.tags||'未设置')}</dd><dt>来源</dt><dd>${esc(r.dataSource||r.source||'—')}</dd></dl>${button(catalog?'编辑技术编目':'挂接技术目录','catalog',r.id)}${catalog?button('解除技术编目','uncatalog',catalog.id):''}`;
    if(selected==='基本信息')html+=table(['字段','中文名','类型','说明'],(r.fields||[]).map(f=>tr(esc(f.name),esc(f.label),esc(f.type),esc(f.description))))+`<p>坐标系：${esc(r.crs||'未填写')}</p>${button('预览本地数据','preview',r.id)}`;
    if(selected==='质量与更新')html+=datasets.map(d=>associations(d)).join('')+table(['报告','采用标准','质量结论'],q.map(x=>tr(link('quality/results',x.name,x.id,'text'),esc(x.standardSnapshot?.name||'—')+' v'+(x.standardSnapshot?.version||'—'),tag(x.status))));
    if(selected==='关联与历史')html+=datasets.map(d=>link('warehouse/tables',d.name,d.id)).join('')+services.map(x=>link(x.protocol==='本地数据接口'?'publishing/apis':'publishing/layers',x.name,x.id)).join('')+`<p>资源关系：${(r.relations||[]).map(id=>esc(refName('resourceId',id))).join('、')||'暂无'}</p><a class="btn" href="#/admin/intelligence-links?asset=${encodeURIComponent('resources:'+r.id)}&view=draft">跨中心关联与影响</a>`;
    if(selected==='服务与共享')html+=`<div class="oc-links"><a class="btn" href="${esc(href(r.type==='数据库表'?'publishing/apis':'publishing/layers','new')+(href(r.type==='数据库表'?'publishing/apis':'publishing/layers','new').includes('?')?'&':'?')+'resourceId='+encodeURIComponent(r.id))}">登记服务</a></div>`;
    if(selected==='服务与共享')html+=`<p>技术编目、服务发布、共享策略与个人授权分别管理。当前共享策略：${esc(r.sharingPolicy||'申请使用')}。</p>${services.map(x=>link(x.protocol==='本地数据接口'?'publishing/apis':'publishing/layers',x.name,x.id)).join('')}${btn('维护共享目录','ct-sharing',r.id)}<a class="btn" href="#/admin/grants">查看授权台账</a>`;
    if(selected==='关联与历史')html+=`<p>语义别名：${esc(r.aliases||'尚未标注')}</p><p>${esc(r.description||'尚无语义说明')}</p><a class="btn primary" href="#/admin/metadata-annotation?resourceId=${encodeURIComponent(r.id)}">前往智能中心标注同一资产</a>`;
    if(selected==='关联与历史')html+=`<p>编辑修订 ${r.rev} · 已发布版本 ${r.published?.version||'无'}</p><details><summary>查看版本技术信息</summary><pre class="ct-json">${esc(JSON.stringify(r.versions||[],null,2))}</pre></details>`;
    return html+'</section>'+(catalog?history(catalog):'');
  }
  function field(key,label,value='',type='text',choices=[]){return `<label class="ct-field ${['textarea','json'].includes(type)?'ct-full':''}"><span>${esc(label)}</span>${type==='select'||type==='multi'?`<select name="${key}" ${type==='multi'?'multiple size="4"':''}>${choices.map(o=>{let [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${esc(v)}" ${(Array.isArray(value)?value:[String(value)]).includes(String(v))?'selected':''}>${esc(t)}</option>`;}).join('')}</select>`:type==='checkbox'?`<input type="checkbox" name="${key}" ${value?'checked':''}>`:type==='textarea'||type==='json'?`<textarea name="${key}" rows="${type==='json'?9:6}" maxlength="200000">${esc(typeof value==='object'?JSON.stringify(value,null,2):value)}</textarea>`:`<input name="${key}" type="${type}" value="${esc(value)}" ${key==='name'?'required maxlength="100"':''}>`}</label>`;}
  function schema(path,r){
    const f=(key,label,type='text',choices=[],fallback='')=>field(key,label,r[key]??fallback,type,choices);let html=f('name','名称 *');
    if(path==='collection/tasks')html+=f('assigneeIds','报送人员 *（可多选，按账号所在单位生成工单）','multi',accountOptions())+f('dueAt','截止时间 *','datetime-local')+f('sourceId','数源 *','select',options(C().sources),'source-local')+f('standardId','已发布标准 *','select',options(C().standards.filter(x=>x.status==='已发布')),'standard-basic')+f('description','任务说明','textarea');
    if(path==='quality/models')html+=f('ruleIds','模型引用规则 *（按住 Ctrl / Command 多选）','multi',options(C().rules),['rule-id','rule-name','rule-area']);
    if(path==='quality/tasks')html+=f('ingestionId','待检数据批次 *','select',options(C().ingestions.filter(x=>['待质检','待整改','待登记'].includes(x.status))))+f('modelId','已发布模型 *','select',O().models.filter(x=>x.published).map(x=>[x.id,x.name+' · v'+x.published.version]));
    if(path==='collection/imports')html+=f('ingestionId','来源批次 *','select',options(C().ingestions.filter(x=>x.status!=='已入库')))+f('datasetId','目标本地空表 *','select',options(C().datasets.filter(x=>x.rowCount===0)))+'<div id="oc-editor-mapping" class="ct-full"></div>'+'<p class="ct-full notice">首批只导入空表；不执行全量覆盖。Excel、GDB、MDB 解析和外部数据库写入尚未接入。</p>';
    if(path==='catalog/directories'||path==='warehouse/domains'){const entity=descriptors[path][0];html+=f('parentId','上级节点','select',[['','根节点'],...options(O()[entity].filter(x=>x.id!==r.id))])+f('kind','节点类型','select',entity==='domains'?['业务域','数仓层','数据库','数据空间']:['公共目录','数据库表','图层服务','工具服务','知识文档']);if(entity==='domains')html+=f('sourceId','目标数源','select',options(C().sources),'source-local');}
    if(path==='catalog/assets')html+=f('resourceId','现有资产 *','select',options(D().resources))+f('directoryId','技术目录 *','select',options(O().directories),'op-dir-root')+f('department','责任单位 *','text',[],D().user.department)+f('tags','标签（逗号分隔）');
    if(path==='catalog/sources')html+=f('kind','数源类型','select',['CSV文件','Oracle','PostgreSQL','空间数据库','ArcGISService','GeoServer','Geoscene'],'CSV文件')+f('provider','数源单位 *','text',[],D().user.department)+f('region','区划','select',D().regions,'全区')+f('endpoint','外部登记地址（HTTPS）')+f('description','描述','textarea');
    if(path==='catalog/systems')html+=f('entry','访问入口（HTTPS）')+f('adapter','适配方式','select',['外部待接入','本地演示'],'外部待接入')+f('contact','联系人')+f('appId','关联应用登记','select',[['','不关联'],...options(D().platform?.apps||[])])+f('authClientId','认证客户端','select',[['','不关联'],...options(D().platform?.authClients||[])])+f('requiresSso','需要单点登录','checkbox')+f('todoEnabled','启用外部待办集成','checkbox')+f('mapping','待办字段映射','json',[],{id:'id',name:'name',userId:'userId',status:'status',dueAt:'dueAt',entry:'entry'});
    if(path==='standards/definitions')html+=f('fields','标准字段 *（name、label、type：text / number / date、required）','json',[],[{name:'id',label:'标识',type:'text',required:true},{name:'name',label:'名称',type:'text',required:true},{name:'region',label:'行政区',type:'text',required:true},{name:'area',label:'面积',type:'number',required:true}]);
    if(path==='warehouse/tables')html+=f('domainId','目标数仓节点 *','select',options(O().domains),'domain-local')+f('standardId','已发布标准 *','select',options(C().standards.filter(x=>x.status==='已发布')),'standard-basic')+f('layer','数仓层','select',['原始层','基础层','专题层'],'基础层')+f('category','业务分类','text',[],'基础数据');
    if(path.startsWith('publishing/'))html+=f('resourceId','来源资产 *','select',options(D().resources.filter(x=>path.endsWith('apis')?x.type==='数据库表':x.type==='图层服务')))+f('protocol','协议','select',path.endsWith('apis')?['本地数据接口']:['WMS','MapService','WMTS','WFS','REST'],path.endsWith('apis')?'本地数据接口':'WMS')+f('endpoint','外部登记地址（本地接口留空）')+f('description','说明','textarea');
    if(path==='monitoring/rules')html+=f('kind','巡检异常类型','select',['质检异常','交付失败','服务依赖异常'])+f('level','告警级别','select',['提示','警告','严重'],'警告')+f('assigneeId','处置人员','select',accountOptions().filter(([id])=>D().accounts.find(x=>x.id===id)?.role==='平台管理员'),'admin')+f('enabled','启用','checkbox',[],true);
    return html;
  }
  function formPage(path,r){return head(r.id?'编辑 · '+r.name:'新建 · '+(pages.find(x=>x[0]===path)?.[1]||''),'保存后返回详情；填写错误会保留当前输入。',link(path,'返回列表'))+`<section class="panel oc-panel"><form id="oc-editor" data-path="${path}" data-record="${esc(r.id||'')}"><div class="ct-form-grid">${schema(path,r)}</div><div id="oc-form-preview"></div><p class="ct-error" role="alert"></p><div class="form-footer"><button class="btn primary" type="submit">${path==='warehouse/tables'?'创建本地空表':'保存'}</button></div></form></section>`;}
  function orderForm(r){return `<section class="panel oc-panel"><h2>报送数据 · 先保存草稿，再提交审核</h2><form id="oc-order" data-id="${esc(r.id)}"><label class="ct-field"><span>导入 UTF-8 CSV（最大200KB）</span><input type="file" id="oc-csv" accept=".csv"></label>${field('dataRows','CSV 数据 *',r.dataRows||'id,name,region,area\n1,示例地块,呼和浩特市,3','textarea')}<p class="ct-error" role="alert"></p><div class="form-footer"><button class="btn primary" type="submit">保存报送草稿</button>${r.dataRows?button('提交登记审核','submit-order',r.id):''}</div></form></section>`;}
  function extraView(path){
    if(path==='catalog/relations')return head('资产关系','直接读取同一资源的关系与运营链路；完整 AI、工具和应用关系在跨中心关联页查看。')+table(['资产','来源批次 / 标准','发布服务','关联与影响'],D().resources.map(r=>tr(link('catalog/assets',r.name,r.id,'text'),C().datasets.filter(d=>d.resourceId===r.id).map(d=>associations(d)).join('')||'无归集批次（已有资产）',C().publications.filter(x=>x.resourceId===r.id).map(x=>esc(x.name)).join('、')||'暂无',`<a class="btn small" href="#/admin/intelligence-links?asset=${encodeURIComponent('resources:'+r.id)}&view=draft">查看引用</a>`)));
    if(path==='standards/changes')return head('标准变更记录','标准历史快照及操作轨迹，不改写采用旧版本的库表。')+table(['标准','当前版本','操作','时间 / 人员'],C().standards.flatMap(r=>(r.history||[]).slice().reverse().map(h=>tr(link('standards/definitions',r.name,r.id,'text'),'v'+r.version,esc(h.action),esc(h.at+' · '+h.actor)))));
    if(path==='monitoring/calls')return head('服务调用','调用记录与请求指标复用统一日志，不将页面访问计作技术服务调用。','<a class="btn primary" href="#/admin/portal-audit">打开统一日志</a><a class="btn" href="#/admin/portal-monitor">请求指标</a>')+table(['服务','协议','状态','发布版本'],C().publications.map(r=>tr(link(r.protocol==='本地数据接口'?'publishing/apis':'publishing/layers',r.name,r.id,'text'),esc(r.protocol),tag(r.status),'v'+(r.resourceVersion||'—'))));
    return head('归集监测','展示本地批次实际状态；实时采集、定时抽取和外部执行趋势暂无数据。')+batchList();
  }
  let pending=false,dirty=false;
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#"]');if(dirty&&a&&!confirm('当前表单尚未保存，确定离开？')){e.preventDefault();e.stopImmediatePropagation();}else if(a)dirty=false;},true);
  function render(){
    if(ctx.state().route!=='operations')return false;
    const {path,id,edit}=state();let html='';
    if(!D().operations){$('#main').innerHTML=head('运营中心正在准备','请重新加载后端服务。');return true;}
    const userAllowed=['todos','collection/orders','quality/orders'];
    if(!O().canManage&&!userAllowed.includes(path)){html=head('暂无管理权限','当前身份仅可办理本人的报送和整改工单。',link('todos','我的待办'));}
    else if(id==='new'||edit){
      const record=id==='new'?{resourceId:state().params.get('resourceId')||undefined}:rowsFor(path).find(x=>x.id===id);
      html=O().canManage&&record&&(editable.has(descriptors[path]?.[0])||['warehouse/tables','catalog/assets'].includes(path))?formPage(path,path==='catalog/assets'&&id!=='new'?{...O().catalogs.find(x=>x.resourceId===id),id:record.id,resourceId:record.id,name:record.name}:record):head('无法编辑','对象不存在或当前身份无管理权限。',link(path,'返回列表'));
    }else if(id){const realId=id.replace(/\/fill$/,'');const r=rowsFor(path).find(x=>x.id===realId);html=r?detail(path,r):head('记录不存在或不可访问','请返回列表刷新后再试。',link(path,'返回列表'));}
    else if(path==='settings')html=settingsView();
    else if(path==='todos')html=todoView();
    else if(['overview','collection/overview','monitoring/overview'].includes(path))html=overview(path);
    else if(path==='quality/reports')html=reportView();
    else if(descriptors[path])html=list(path);
    else if(['catalog/relations','standards/changes','monitoring/collection','monitoring/calls'].includes(path))html=extraView(path);
    else html=head('页面不存在','请选择运营中心已开放的页面。',link('overview','返回总览'));
    $('#main').innerHTML=`<div class="ct-workspace oc-workspace">${localNav(path)}${html}</div>`;bind();return true;
  }
  function values(form){const data=Object.fromEntries(new FormData(form));form.querySelectorAll('select[multiple]').forEach(x=>data[x.name]=[...x.selectedOptions].map(o=>o.value));form.querySelectorAll('input[type=checkbox]').forEach(x=>data[x.name]=x.checked);return data;}
  async function submit(form,fn){const submit=form.querySelector('[type=submit]');if(submit.disabled)return;submit.disabled=true;try{await fn();dirty=false;}catch(e){form.querySelector('[role=alert]').textContent=e.message;toast(e.message);}finally{submit.disabled=false;}}
  function bind(){
    const current=state();
    if(current.path==='settings')settingsUI.bind();
    const batch=current.path==='collection/batches'?C().ingestions.find(x=>x.id===current.id):current.path==='collection/orders'?C().ingestions.find(x=>x.id===O().orders.find(r=>r.id===current.id)?.ingestionId):null;
    workflow.bind(batch);
    document.querySelectorAll('.oc-inline-form').forEach(form=>{form.addEventListener('input',()=>dirty=true);form.addEventListener('change',()=>dirty=true);});
    $('#oc-search')?.addEventListener('submit',e=>{e.preventDefault();const p=new URLSearchParams(values(e.target));p.delete('page');location.hash='#'+base()+state().path+'?'+p;});
    const preview=()=>{
      const form=$('#oc-editor'),box=$('#oc-form-preview');if(!form||!box)return;
      const path=state().path;
      if(path==='warehouse/tables'){
        const standard=C().standards.find(r=>r.id===form.elements.standardId.value);
        box.innerHTML=standard?`<h3>建表结构预览 · 标准 v${standard.version}</h3>${table(['字段','名称','类型','必填'],standard.fields.map(f=>tr(esc(f.name),esc(f.label),esc(f.type),f.required?'是':'否')))}`:'';
      }
      if(path==='collection/imports'){
        const batch=C().ingestions.find(r=>r.id===form.elements.ingestionId.value),target=C().datasets.find(r=>r.id===form.elements.datasetId.value);
        const existing=O().imports.find(x=>x.id===state().id);$('#oc-editor-mapping').innerHTML=workflow.mapping(batch,target,existing?.datasetId===target?.id&&existing?.ingestionId===batch?.id?existing.mapping:{});
        box.innerHTML=`<h3>映射前检查</h3><p>来源列：${esc(batch?.dataRows?.split('\n')[0]||'请选择批次')}</p><p>目标列：${esc(target?.fields?.join(', ')||'请选择目标表')}</p><p>当前批次：${esc(batch?.status||'未选择')} · 目标 ${target?.rowCount??'—'} 行。执行时还会校验最新报告和目标标准。</p>`;
      }
    };
    preview();$('#oc-editor')?.addEventListener('change',e=>{if(['datasetId','ingestionId','standardId'].includes(e.target.name))preview();});
    $('#oc-editor')?.addEventListener('input',()=>dirty=true);
    $('#oc-editor')?.addEventListener('change',()=>dirty=true);
    $('#oc-editor')?.addEventListener('submit',e=>{e.preventDefault();submit(e.target,async()=>{const {path,id}=state(),[entity,scope]=descriptors[path],v=values(e.target),r=rowsFor(path).find(x=>x.id===id);let result;
      if(path==='collection/imports')v.mapping=mappingValues(e.target);
      if(path==='warehouse/tables')result=await api('operations.dataset.create',v);
      else if(path==='catalog/assets'){const catalog=O().catalogs.find(x=>x.resourceId===v.resourceId);result=await api('operations.save',{entity:'catalogs',id:catalog?.id,rev:catalog?.rev,values:v});}
      else result=await api((scope==='operations'?'operations.':'centers.')+'save',{entity,id:r?.id,rev:r?.rev,values:v});
      dirty=false;await ctx.load();const target=href(path,path==='catalog/assets'?result.resourceId:result.id);if(location.hash===target)render();else location.hash=target;toast('已保存');
    });});
    $('#oc-order')?.addEventListener('input',()=>dirty=true);
    $('#oc-order')?.addEventListener('submit',e=>{e.preventDefault();submit(e.target,async()=>{const r=O().orders.find(x=>x.id===e.target.dataset.id);await api('operations.order.save',{id:r.id,rev:r.rev,...values(e.target)});dirty=false;await ctx.reload();toast('草稿已保存，可以提交登记审核');});});
    $('#oc-csv')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(file.size>200000){toast('CSV 文件不能超过200KB');return;}$('#oc-order [name=dataRows]').value=(await file.text()).replace(/^\ufeff/,'');dirty=true;});
  }
  async function dialog(title,fields,run){ctx.modal(title,`<form id="oc-dialog"><div class="ct-form-grid">${fields}</div><p class="ct-error" role="alert"></p><div class="form-footer"><button type="submit" class="btn primary">确认</button></div></form>`,true);$('#oc-dialog').addEventListener('submit',e=>{e.preventDefault();submit(e.target,async()=>{await run(values(e.target));ctx.closeModal();await ctx.reload();toast('操作已完成');});});}
  async function mutate(op,r,extra={}){await api('operations.'+op,{id:r?.id,rev:r?.rev,...extra});await ctx.reload();toast('操作已完成');}
  function download(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  async function action(a,id){
    if(!a.startsWith('oc-'))return false;
    const op=a.slice(3),{path,params}=state();
    if(op==='reset'){location.hash='#'+base()+path;return true;}
    if(op==='page'||op==='asset-tab'){params.set(op==='page'?'page':'view',id);location.hash=location.hash.split('?')[0]+'?'+params;return true;}
    if(op==='export'){download(filterRows(rowsFor(path)),'运营中心-'+path.replaceAll('/','-'));return true;}
    if(op==='export-record'){download(rowsFor(path).find(x=>x.id===id),'质检报告-'+id);return true;}
    if(pending)return true;pending=true;
    try{
      if(op==='delete'||op==='uncatalog'){
        const entity=op==='uncatalog'?'catalogs':descriptors[path][0],r=O()[entity].find(x=>x.id===id);
        await dialog(op==='uncatalog'?'解除技术编目':'删除检查',`<p class="ct-full">对象：${esc(r.name)}。${op==='uncatalog'?'解除技术目录挂接，不删除资源或改变共享授权。':'仅允许删除未发起草稿或无下级、无引用的节点；执行过的记录必须保留。'}</p>`,async()=>{await api('operations.delete',{entity,id,rev:r.rev});if(op==='delete')location.hash=href(path);});
      }
      if(op==='dispatch')await mutate('task.dispatch',O().tasks.find(x=>x.id===id));
      if(op==='submit-order'){if(dirty){toast('请先保存当前报送草稿');return true;}await mutate('order.submit',O().orders.find(x=>x.id===id));}
      if(op==='review'){const r=O().orders.find(x=>x.id===id);await dialog('登记审核 · '+r.name,field('decision','审核结论','通过','select',['通过','退回'])+field('note','审核意见 *','','textarea'),v=>api('operations.order.review',{id,rev:r.rev,...v}));}
      if(op==='publish-model')await mutate('model.publish',O().models.find(x=>x.id===id));
      if(op==='run-quality'){const r=O().qualityTasks.find(x=>x.id===id),run=await api('operations.quality.run',{id,rev:r.rev});await ctx.load();location.hash=href('quality/results',run.id);}
      if(op==='run-import'){const r=O().imports.find(x=>x.id===id);await mutate('import.run',r);location.hash=href('collection/imports',id);}
      if(op==='inspect'){await mutate('inspection.run');location.hash=href('monitoring/inspections');}
      if(op==='alert'){const r=O().alerts.find(x=>x.id===id),target=({待确认:'处理中',处理中:'待验证',待验证:'已关闭',已关闭:'处理中'})[r.status];await dialog('告警处置 · '+target,`<p class="ct-full">${esc(r.reason)}。${r.recoveredAt?'最近巡检已确认指标恢复。':'指标尚未恢复，修复后请重新巡检。'}</p>`+field('note','处置 / 验证说明 *','','textarea'),v=>api('operations.alert.transition',{id,rev:r.rev,status:target,...v}));}
      if(op==='feedback'){const r=C().issues.find(x=>x.id===id),b=C().ingestions.find(x=>x.id===r.ingestionId);await dialog('整改反馈',field('note','整改说明 *','','textarea')+field('evidence','处理依据 *','','textarea')+field('dataRows','修正后的 CSV *',b?.dataRows||'','textarea'),v=>api('centers.issue.feedback',{id,rev:r.rev,...v}));}
      if(op==='catalog')location.hash=href('catalog/assets',id,true);
      if(op==='preview'){const r=D().resources.find(x=>x.id===id);ctx.modal('本地数据预览',`<pre class="ct-json">${esc(r.dataRows||'暂无本地数据；外部服务尚未读取')}</pre>`);}
      if(op==='publish-service'||op==='disable-service'){const r=C().publications.find(x=>x.id===id),resource=D().resources.find(x=>x.id===r.resourceId);await dialog(op==='publish-service'?'发布本地技术接口':'停用技术接口',`<p class="ct-full">${esc(r.name)} · 来源资产：${esc(resource?.name||'已失效')}。${op==='publish-service'?'将发布当前资源草稿并绑定新的资源版本；使用者仍需相应授权。':'只停用此接口，关联应用可能受影响，请先检查引用。'}</p><p class="ct-full"><a class="btn" href="#/admin/intelligence-links?asset=${encodeURIComponent('resources:'+r.resourceId)}&view=online">查看线上引用与影响</a></p>`,()=>api(op==='publish-service'?'centers.publication.publish':'centers.publication.disable',{id,rev:r.rev}));}
    }finally{pending=false;}
    return true;
  }
  return {render,action};
}
