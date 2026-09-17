export function createCenters(ctx){
  const {$,esc,btn,tag,api,modal,closeModal,toast,nav}=ctx;
  const D=()=>ctx.state().D,C=()=>D().centers;
  let active='',query='',page=1,lastRoute='',trialResult=null;
  const routes={
    'center-integration':['综合集成','系统接入、目录汇聚与工作任务集成。',[['catalog','资源总览'],['systems','系统接入'],['todos','集成待办'],['nodes','纵向节点'],['syncRuns','同步记录']]],
    'center-resources':['资源中心','共享编目、使用审核与交付记录关联同一资源。',[['catalog','共享目录'],['deliveries','数据交付'],['subscriptions','订阅推送'],['directories','目录管理']]],
    'center-tools':['工具中心','区分上架审核与使用授权，保留接口试运行结果。',[['tools','工具台账'],['toolReviews','上架审核'],['toolTrials','接口试运行']]],
    'center-operations':['运营中心','从归集到质检、整改、入库和服务发布的完整本地流程。',[['summary','运行总览'],['sources','数源登记'],['ingestions','归集批次'],['rules','质检规则'],['qualityRuns','质检报告'],['issues','治理工单'],['standards','数据标准'],['datasets','建库管理'],['publications','技术发布'],['inspections','业务巡检']]],
    'integrated-workbench':['综合工作台','按当前身份汇聚资源、待办、收藏和交付结果。',[['catalog','综合资源'],['todos','我的待办'],['favorites','我的收藏'],['deliveries','我的交付'],['subscriptions','我的订阅'],['issues','我的治理工单']]],
    'shared-resources':['资源中心','查找共享资源，申请使用并跟踪交付结果。',[['catalog','共享目录'],['deliveries','我的交付'],['subscriptions','我的订阅']]]
  };
  const names={systems:'系统接入',nodes:'节点',sources:'数源',ingestions:'归集批次',rules:'质检规则',directories:'分类目录',standards:'数据标准',publications:'技术服务'};
  const f=(key,label,value='',type='text',options=[])=>`<label class="ct-field"><span>${esc(label)}</span>${type==='select'||type==='multi'?`<select name="${key}" ${type==='multi'?'multiple size="4"':''}>${options.map(o=>{const [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${esc(v)}" ${(type==='multi'?(Array.isArray(value)?value:[]):[String(value)]).includes(String(v))?'selected':''}>${esc(t)}</option>`;}).join('')}</select>`:type==='checkbox'?`<input type="checkbox" name="${key}" ${value?'checked':''}>`:type==='textarea'||type==='json'?`<textarea name="${key}" rows="${type==='json'?6:4}" maxlength="200000">${esc(type==='json'&&typeof value!=='string'?JSON.stringify(value,null,2):value)}</textarea>`:`<input name="${key}" type="${type}" value="${esc(value)}" ${key==='name'?'required maxlength="100"':''}>`}</label>`;
  const options=(entity)=>C()[entity].map(x=>[x.id,x.name]);
  const table=(heads,rows)=>`<div class="table-scroll"><table><thead><tr>${heads.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${heads.length}"><div class="empty">暂无记录，可通过上方操作开始。</div></td></tr>`}</tbody></table></div>`;
  const cell=(...values)=>values.map(v=>`<td>${v??'—'}</td>`).join('');
  const name=r=>`<strong>${esc(r.name)}</strong><small>${esc(r.id)}</small>`;
  const action=(label,op,id,style='text small')=>btn(label,'ct-'+op,id,style);
  const detail=(entity,r)=>action('详情','detail',entity+':'+r.id);
  const editButton=(entity,r)=>action('编辑','edit',entity+':'+r.id);
  const history=r=>`<section class="ct-history"><h3>操作记录</h3>${(r.history||[]).slice().reverse().map(h=>`<p><small>${esc(h.at)} · ${esc(h.actor)}</small><strong>${esc(h.action)}</strong> ${esc(h.note||'')}</p>`).join('')||'<p class="muted">暂无操作记录</p>'}</section>`;
  const title=(name,desc,actions='')=>`<div class="page-heading"><div><div class="eyebrow">ONE MAP</div><h1>${esc(name)}</h1><p>${esc(desc)}</p></div><div class="actions">${actions}</div></div>`;
  function download(r){const url=URL.createObjectURL(new Blob([r.content],{type:r.mime||'application/json'})),a=document.createElement('a');a.href=url;a.download=r.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  async function send(op,p={},show=false){const result=await api('centers.'+op,p);closeModal();await ctx.reload();if(show)viewResult(result);else toast('操作已完成');return result;}
  function form(title,html,submit){
    modal(title,`<form id="ct-form"><div class="ct-form-grid">${html}</div><div class="form-footer"><button type="submit" class="btn primary">确认提交</button></div><p class="ct-error" role="alert"></p></form>`,true);
    $('#ct-form').addEventListener('submit',async e=>{
      e.preventDefault();const form=e.target,button=form.querySelector('button[type=submit]');if(button.disabled)return;button.disabled=true;
      const values=Object.fromEntries(new FormData(form));form.querySelectorAll('input[type=checkbox]').forEach(x=>values[x.name]=x.checked);form.querySelectorAll('select[multiple]').forEach(x=>values[x.name]=[...x.selectedOptions].map(o=>o.value));
      try{await submit(values);}catch(error){if(form.isConnected)form.querySelector('.ct-error').textContent=error.message;toast(error.message);}finally{if(button.isConnected)button.disabled=false;}
    });
  }
  function editor(entity,id=''){
    const r=C()[entity].find(x=>x.id===id)||{},base=f('name','名称',r.name||'');let fields=base;
    if(entity==='systems')fields+=f('entry','访问入口（HTTPS 或本站前台路由）',r.entry)+f('adapter','适配方式',r.adapter||'外部待接入','select',['外部待接入','本地演示'])+f('contact','对接联系人',r.contact)+f('authClientId','认证客户端',r.authClientId||'','select',[['','仅入口接入'],...(D().platform.authClients||[]).map(x=>[x.id,x.name])])+f('appId','关联应用登记',r.appId||'','select',[['','未关联'],...(D().platform.apps||[]).map(x=>[x.id,x.name])])+f('requiresSso','需要单点登录集成',r.requiresSso||false,'checkbox')+f('todoEnabled','启用待办集成',r.todoEnabled||false,'checkbox')+f('mapping','待办字段映射',r.mapping||{id:'id',name:'name',userId:'userId',status:'status',createdAt:'createdAt',dueAt:'dueAt',entry:'entry'},'json');
    if(entity==='nodes')fields+=f('level','节点级别',r.level||'盟市','select',['国家','自治区','盟市','旗县'])+f('parentId','上级节点',r.parentId||'node-province','select',[['','无上级'],...options('nodes').filter(x=>x[0]!==id)])+f('region','行政区',r.region||'呼和浩特市')+f('domain','统一域名 / 入口',r.domain)+f('direction','交换方向',r.direction||'双向','select',['导入','导出','双向'])+f('contact','对接联系人',r.contact);
    if(entity==='sources')fields+=f('kind','数源类型',r.kind||'CSV文件','select',['CSV文件','Oracle','PostgreSQL','空间数据库','ArcGISService','GeoServer','Geoscene'])+f('provider','数源单位',r.provider||D().user.department)+f('region','行政区',r.region||'全区','select',D().regions)+f('endpoint','服务登记地址（外部连接待联调）',r.endpoint)+f('description','描述',r.description,'textarea');
    if(entity==='ingestions')fields+=f('sourceId','数源',r.sourceId||'source-local','select',options('sources'))+f('region','覆盖区域',r.region||'全区','select',D().regions)+f('category','业务分类',r.category||'基础数据')+f('layer','数仓分层',r.layer||'原始层','select',['原始层','基础层','专题层'])+f('mode','归集方式',r.mode||'在线填报','select',['在线填报','离线CSV'])+f('crs','坐标系',r.crs||'CGCS2000')+f('standardId','关联数据标准',r.standardId||'standard-basic','select',[['','不关联'],...options('standards')])+f('ruleIds','质检规则',r.ruleIds||['rule-id','rule-name','rule-area'],'multi',options('rules'))+`<label class="ct-field"><span>导入 UTF-8 CSV（可选，最多2000行）</span><input type="file" id="ct-csv" accept=".csv"></label>`+f('dataRows','归集数据 CSV（以下为可替换示例）',r.dataRows||'id,name,region,area\n1,示例地块甲,呼和浩特市,12.5\n2,示例地块乙,呼和浩特市,-3','textarea');
    if(entity==='rules')fields+=f('field','字段英文名',r.field||'area')+f('kind','校验规则',r.kind||'非负数','select',['必填','唯一','非负数','枚举','日期'])+f('argument','枚举值（英文逗号分隔）',r.argument)+f('enabled','启用规则',r.enabled??true,'checkbox');
    if(entity==='directories')fields+=f('parentId','父目录',r.parentId||'','select',[['','根目录'],...options('directories').filter(x=>x[0]!==id)])+f('kind','目录类型',r.kind||'公共目录','select',['公共目录','数据库表','图层服务','工具服务','知识文档'])+f('tags','标签（逗号分隔）',r.tags);
    if(entity==='standards')fields+=f('fields','标准字段（name、label、type、required）',r.fields||[{name:'id',label:'标识',type:'text',required:true},{name:'name',label:'名称',type:'text',required:true},{name:'area',label:'面积',type:'number',required:true}],'json');
    if(entity==='publications')fields+=f('resourceId','关联资源',r.resourceId||D().resources[0]?.id,'select',D().resources.map(x=>[x.id,x.name]))+f('protocol','服务协议',r.protocol||'本地数据接口','select',['本地数据接口','WMS','MapService','WMTS','WFS','REST'])+f('endpoint','外部服务地址（外部协议必填）',r.protocol==='本地数据接口'?'':r.endpoint)+f('description','说明',r.description,'textarea');
    form((id?'编辑':'新增')+names[entity],fields,values=>send('save',{entity,id:id||undefined,rev:r.rev,values}));
    if(entity==='ingestions')$('#ct-csv').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(file.size>200000){toast('CSV 文件不能超过200KB');return;}$('#ct-form [name=dataRows]').value=(await file.text()).replace(/^\ufeff/,'');$('#ct-form [name=mode]').value='离线CSV';});
  }
  function viewResult(result){
    if(result.filename&&result.content){download(result);return;}
    const labels={id:'业务标识',status:'状态',createdAt:'创建时间',updated:'更新时间',sourceId:'数源',resourceId:'资源标识',systemId:'来源系统',ingestionId:'归集批次',sourceApplicationId:'来源申请',grantId:'授权记录',method:'交付方式',scope:'执行范围',region:'行政区',kind:'类型',level:'节点级别',direction:'交换方向',domain:'域名 / 入口',entry:'访问入口',adapter:'适配方式',contact:'联系人',provider:'提供方',layer:'数仓分层',rowCount:'记录数',total:'检查 / 查询总数',dataRevision:'数据版本',version:'发布版本',resourceVersion:'资源版本',standardVersion:'标准版本',assigneeName:'处理人',feedback:'整改说明',evidence:'处理依据',note:'说明 / 审核意见',reviewer:'审核人',error:'失败原因',receipt:'领取信息',pickupPlace:'领取地点',pickupAt:'领取时间',receiver:'接收端',intervalSeconds:'生成周期（秒）',lastRunAt:'最近执行',nextRunAt:'下次执行',attempts:'执行次数',protocol:'协议',endpoint:'服务入口',description:'说明',added:'新增数量',updatedCount:'更新数量',count:'记录数量',durationMs:'耗时（毫秒）',engine:'执行能力',field:'规则字段',argument:'规则参数'};
    let html=`${result.status?tag(result.status):''}<dl class="detail-grid">${Object.entries(labels).filter(([key])=>result[key]!==undefined&&result[key]!==''&&typeof result[key]!=='object').map(([key,label])=>`<dt>${label}</dt><dd>${esc(result[key])}</dd>`).join('')}</dl>`;
    if(result.issues)html+='<h3>质量问题明细</h3>'+table(['行号','字段','规则','问题'],result.issues.map(x=>`<tr>${cell(esc(x.row||'表头'),esc(x.field),esc(x.rule),esc(x.message))}</tr>`));
    if(result.failures)html+='<h3>异常明细</h3>'+table(['类型','对象','原因'],result.failures.map(x=>`<tr>${cell(esc(x.kind),esc(x.name),esc(x.reason))}</tr>`));
    if(result.fields?.length&&typeof result.fields[0]==='object')html+='<h3>标准字段</h3>'+table(['字段','中文名','类型','必填'],result.fields.map(x=>`<tr>${cell(esc(x.name),esc(x.label),esc(x.type),x.required?'是':'否')}</tr>`));
    if(result.ruleSnapshots)html+=`<h3>检查依据</h3><p>${result.ruleSnapshots.map(x=>esc(x.name)+' · 配置版本 '+x.rev).join('、')||'仅检查关联标准'}</p><p>${esc(result.standardSnapshot?.name||'未关联标准')} ${result.standardSnapshot?'v'+result.standardSnapshot.version:''}</p>`;
    if(result.lastCheck&&typeof result.lastCheck==='object')html+=`<h3>配置校验</h3><p>${esc(result.lastCheck.scope)} · ${esc(result.lastCheck.at)}</p><p>${result.lastCheck.missing.length?'待补充：'+result.lastCheck.missing.map(esc).join('、'):'配置项完整'}</p>`;
    if(result.created)html+=`<p>已登记：${result.created.map(esc).join('、')||'所需组件已存在，无需重复创建'}</p>`;
    if(result.rows){const cols=[...new Set(result.rows.flatMap(x=>Object.keys(x)))];html+=table(cols,result.rows.map(r=>`<tr>${cell(...cols.map(k=>esc(r[k])))}</tr>`));}
    if(result.dataRows)html+=`<details><summary>查看原始 CSV</summary><pre class="ct-json">${esc(result.dataRows)}</pre></details>`;
    if(result.input||result.output)html+=`<details open><summary>接口请求与返回</summary><pre class="ct-json">${esc(JSON.stringify({request:result.input,response:result.output},null,2))}</pre></details>`;
    modal(result.name||'执行结果',html+history(result),true);
  }
  function renderCatalog(){
    const mode=ctx.state().mode,route=ctx.state().route,onlyResources=route.includes('resources');
    let rows=C().catalog.filter(r=>(!onlyResources||r.resourceId)&&(!query||[r.name,r.kind,r.category,r.source,r.region,(C().sharing[r.resourceId]||{}).tags].join(' ').includes(query)));
    if(active==='favorites')rows=rows.filter(r=>C().favorites.includes(r.id));
    const kind=$('#ct-kind')?.value||sessionStorage.getItem('ct-kind-'+route)||'全部';rows=rows.filter(r=>kind==='全部'||r.kind===kind);
    const sort=sessionStorage.getItem('ct-sort-'+route)||'最新';
    const popularity=r=>(D().applications||[]).reduce((n,a)=>n+a.items.filter(i=>i.resourceId===r.resourceId).length,0);
    rows.sort((a,b)=>sort==='申请次数'?popularity(b)-popularity(a):String(b.updated||'').localeCompare(String(a.updated||'')));
    const directory=sessionStorage.getItem('ct-directory-'+route)||'';
    const inDirectory=(key)=>{const seen=new Set();while(key&&!seen.has(key)){if(key===directory)return true;seen.add(key);key=C().directories.find(d=>d.id===key)?.parentId;}return false;};
    if(directory)rows=rows.filter(r=>inDirectory(C().sharing[r.resourceId]?.directoryId));
    const count=rows.length;rows=rows.slice((page-1)*12,page*12);
    return `<div class="ct-catalog-filters"><label>资源类型<select id="ct-kind">${['全部',...new Set(C().catalog.filter(r=>!onlyResources||r.resourceId).map(r=>r.kind))].map(k=>`<option ${k===kind?'selected':''}>${esc(k)}</option>`).join('')}</select></label><label>排序<select id="ct-sort">${['最新','申请次数'].map(k=>`<option ${k===sort?'selected':''}>${k}</option>`).join('')}</select></label><label>编目目录<select id="ct-directory"><option value="">全部目录</option>${C().directories.map(d=>`<option value="${esc(d.id)}" ${directory===d.id?'selected':''}>${esc(d.name)}（${C().catalog.filter(r=>C().sharing[r.resourceId]?.directoryId===d.id).length}）</option>`).join('')}</select></label><span>${count} 项可见资源</span></div><div class="ct-cards">${rows.map(r=>{
      const sharing=C().sharing[r.resourceId],directory=C().directories.find(x=>x.id===sharing?.directoryId);
      return `<article class="panel ct-card"><div>${tag(r.kind)}<small>${esc(r.region||r.category||'')}</small></div><h3>${esc(r.name)}</h3><p>${esc(r.source||r.category||'统一登记能力')}</p><small>${esc(directory?.name||'未编目')} ${esc(sharing?.tags||'')}</small><div class="actions"><a class="btn small" href="#${esc(r.target)}">查看 / 使用</a>${action(C().favorites.includes(r.id)?'取消收藏':'收藏','favorite',r.id)}${r.resourceId&&mode==='admin'&&C().canManage?action('编目','sharing',r.resourceId):''}${r.resourceId&&r.authorized?action('申请交付','request-delivery',r.resourceId):''}</div></article>`;
    }).join('')||'<div class="empty">没有符合条件的资源。</div>'}</div><div class="pagination"><span>第 ${page} 页 · 共 ${Math.max(1,Math.ceil(count/12))} 页</span>${page>1?action('上一页','page',String(page-1)):''}${page*12<count?action('下一页','page',String(page+1)):''}</div>`;
  }
  function summary(){
    const cards=[['归集批次',C().ingestions.length,'ingestions'],['待质检',C().ingestions.filter(r=>r.status==='待质检').length,'ingestions'],['未办结工单',C().issues.filter(r=>r.status!=='已办结').length,'issues'],['已入库数据集',C().datasets.length,'datasets'],['已发布接口',C().publications.filter(r=>r.status==='已发布').length,'publications'],['失败交付',C().deliveries.filter(r=>r.status==='失败').length,'inspections']];
    return `<div class="ct-metrics">${cards.map(([label,value,key])=>`<button data-action="ct-tab" data-id="${key}"><span>${label}</span><strong>${value}</strong></button>`).join('')}</div><section class="panel ct-panel"><h2>数据治理流程</h2><div class="ct-flow">${[['归集填报','ingestions'],['执行质检','qualityRuns'],['整改与复检','issues'],['登记入库','datasets'],['技术发布','publications'],['共享编目','@center-resources']].map(([label,key],i)=>`<button data-action="ct-tab" data-id="${key}"><b>${i+1}</b>${label}</button>`).join('')}</div><p>入库只生成资源草稿；技术发布后才能在资源目录中发现。共享策略及个人授权继续独立控制使用。</p></section><section class="panel ct-panel"><h2>运行与审计</h2><div class="actions"><a class="btn" href="#/admin/portal-monitor">主机与服务监控</a><a class="btn" href="#/admin/portal-audit">统一日志审计</a><a class="btn" href="#/admin/portal-analytics">访问与调用统计</a>${action('执行业务巡检','inspect','','primary')}</div></section>`;
  }
  function listing(entity,rows){
    if(entity==='systems')return table(['系统 / 标识','适配 / 状态','待办集成','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.adapter)+' '+tag(r.status),r.todoEnabled?'已启用':'未启用',editButton(entity,r)+action('配置校验','check-system',r.id)+(r.todoEnabled?action('导入待办','import-todos',r.id):'')+detail(entity,r))}</tr>`));
    if(entity==='nodes')return table(['节点 / 标识','级别 / 区域','上级 / 方向','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.level+' · '+r.region),esc((C().nodes.find(x=>x.id===r.parentId)?.name||'无上级')+' · '+r.direction),editButton(entity,r)+action('导出交换清单','export-node',r.id)+detail(entity,r))}</tr>`));
    if(entity==='todos')return table(['待办 / 来源','状态','截止时间','办理入口'],rows.map(r=>`<tr>${cell(`<strong>${esc(r.name)}</strong><small>${esc(r.source)}</small>`,tag(r.status)+' '+tag(r.timeliness),esc(r.dueAt||'未设置'),r.entry?`<a class="btn small" href="${esc(r.entry)}" ${r.entry.startsWith('https:')?'target="_blank" rel="noopener noreferrer"':''}>进入来源系统</a>`:'尚未配置入口')}</tr>`));
    if(entity==='sources')return table(['数源','类型 / 单位','状态','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.kind)+'<small>'+esc(r.provider)+'</small>',tag(r.status),editButton(entity,r)+action('检查配置','check-source',r.id)+detail(entity,r))}</tr>`));
    if(entity==='ingestions')return table(['批次 / 分层','归集方式 / 状态','数据版本','操作'],rows.map(r=>`<tr>${cell(name(r)+'<small>'+esc(r.layer)+'</small>',esc(r.mode)+' '+tag(r.status),'v'+r.dataRevision,(['草稿','已退回'].includes(r.status)?editButton(entity,r)+action('提交','submit-ingestion',r.id):'')+(['待质检','待整改','待登记'].includes(r.status)?action('执行质检','check-ingestion',r.id)+action('退回','return-ingestion',r.id):'')+(r.status==='待登记'?action('登记入库','register-ingestion',r.id):'')+detail(entity,r))}</tr>`));
    if(entity==='rules')return table(['规则','字段 / 类型','状态','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.field+' · '+r.kind),tag(r.status),editButton(entity,r)+detail(entity,r))}</tr>`));
    if(entity==='qualityRuns')return table(['质检报告','行数 / 问题数','结果','操作'],rows.map(r=>`<tr>${cell(name(r),r.total+' 行 / '+r.issues.length+' 项问题',tag(r.status),detail(entity,r)+(r.issues.length?action('发起治理','create-issue',r.id):''))}</tr>`));
    if(entity==='issues')return table(['工单','处理人','状态','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.assigneeName),tag(r.status),(['待处理','已退回'].includes(r.status)?action('整改反馈','feedback-issue',r.id):'')+(C().canManage&&r.status==='待复核'?action('复检复核','review-issue',r.id):'')+detail(entity,r))}</tr>`));
    if(entity==='standards')return table(['标准','字段数 / 版本','状态','操作'],rows.map(r=>`<tr>${cell(name(r),r.fields.length+' 项 / v'+r.version,tag(r.status),editButton(entity,r)+(r.status==='草稿'?action('发布','publish-standard',r.id):'')+detail(entity,r))}</tr>`));
    if(entity==='datasets')return table(['数据集','分层 / 数据量','资源关联','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.layer)+' · '+r.rowCount+' 行',esc(r.resourceId),`<a class="btn text small" href="#/admin/resources">维护资源</a>`+detail(entity,r))}</tr>`));
    if(entity==='publications')return table(['技术服务','协议 / 状态','资源版本','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.protocol)+' '+tag(r.status),'v'+(r.resourceVersion||'未发布'),editButton(entity,r)+(r.protocol==='本地数据接口'?action('发布','publish-service',r.id)+(r.status==='已发布'?action('试查询','query-service',r.id)+action('停用','disable-service',r.id):''):'')+detail(entity,r))}</tr>`));
    if(entity==='directories')return table(['目录','类型','上级目录','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.kind),esc(C().directories.find(x=>x.id===r.parentId)?.name||'根目录'),editButton(entity,r)+detail(entity,r))}</tr>`));
    if(entity==='deliveries')return table(['交付 / 使用人','方式 / 资源','状态 / 次数','操作'],rows.map(r=>`<tr>${cell(name(r)+'<small>'+esc(D().accounts.find(x=>x.id===r.userId)?.name||r.userId)+'</small>',esc(r.method)+'<small>'+esc(r.resourceId)+'</small>',tag(r.status)+'<small>'+r.attempts+' 次 · '+esc(r.error||r.receipt||'')+'</small>',(C().canDeliver?(!['数据订阅','定时推送'].includes(r.method)?action('准备 / 重试','run-delivery',r.id):action('注册订阅','register-subscription',r.id)):'')+(['可领取','已领取'].includes(r.status)&&r.filename?action('下载数据包','download-delivery',r.id):'')+(['可领取','已领取'].includes(r.status)&&['数据服务','功能接口'].includes(r.method)?action('服务入口','open-delivery',r.id):'')+(r.status==='可领取'&&!r.filename&&r.userId===D().user.id?action('确认领取','receive-delivery',r.id):'')+detail(entity,r))}</tr>`));
    if(entity==='subscriptions')return table(['订阅','接收端 / 周期','状态 / 下次运行','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.receiver)+' · '+r.intervalSeconds+' 秒',tag(r.status)+'<small>'+esc(r.nextRunAt)+'</small>',action(r.status==='运行中'?'暂停':'恢复',r.status==='运行中'?'pause-subscription':'resume-subscription',r.id)+(C().canDeliver&&r.status==='运行中'?action('立即生成批次','run-subscription',r.id):'')+detail(entity,r))}</tr>`));
    if(entity==='tools')return table(['工具 / 提供方','执行能力','发布 / 审核状态','操作'],rows.map(r=>`<tr>${cell(name(r)+'<small>'+esc(r.provider||'未填写提供方')+'</small>',esc(r.engine),tag(r.status)+' '+tag(r.reviewState||'历史已发布'),btn('配置','pm-edit','tools:'+r.id,'text small')+action('提交审核','submit-tool',r.id)+(r.reviewState==='待审核'?action('审核','review-tool',r.id):'')+(r.reviewState==='已通过'?btn('发布','pm-publish','tools:'+r.id,'text small'):'')+(r.published?btn('下架','pm-disable','tools:'+r.id,'text small'):'')+action('接口试运行','trial-tool',r.id))}</tr>`));
    if(entity==='toolReviews')return table(['审核记录','状态','审核意见','操作'],rows.map(r=>`<tr>${cell(name(r),tag(r.status),esc(r.note||'待填写'),(r.status==='待审核'?action('办理','review-tool',r.toolId):'')+detail(entity,r))}</tr>`));
    if(entity==='toolTrials')return table(['试运行记录','执行能力','结果 / 耗时','操作'],rows.map(r=>`<tr>${cell(name(r),esc(r.engine),tag(r.status)+' · '+r.durationMs+' ms',detail(entity,r))}</tr>`));
    if(entity==='inspections')return table(['巡检','异常数','状态','操作'],rows.map(r=>`<tr>${cell(name(r),r.failures.length,tag(r.status),detail(entity,r))}</tr>`));
    return table(['记录','状态','时间','操作'],rows.map(r=>`<tr>${cell(name(r),tag(r.status),esc(r.updated),detail(entity,r))}</tr>`));
  }
  function render(){
    const {route,mode}=ctx.state();if(!routes[route])return false;
    if(!C()){$('#main').innerHTML=title('中心功能尚未加载','请重启后端服务并刷新。');return true;}
    const [name,desc,tabs]=routes[route];if(lastRoute!==route){active=tabs[0][0];query='';page=1;lastRoute=route;}
    if(!tabs.some(x=>x[0]===active))active=tabs[0][0];
    if(mode==='admin'&&!C().canManage&&!(route==='center-resources'&&C().canDeliver)){$('#main').innerHTML=title('暂无管理权限','当前身份不能管理该中心。');return true;}
    const allowedTabs=!C().canManage&&mode==='admin'?tabs.filter(x=>['catalog','deliveries','subscriptions'].includes(x[0])):tabs;
    let top='';if(C().canManage&&names[active])top=action('新增'+names[active],'edit',active+':','primary');
    if(active==='datasets'&&C().canManage)top=action('按标准建表','create-dataset','','primary');
    if(active==='tools')top=btn('注册工具','pm-edit','tools:','primary')+action('登记内部组件模板','tool-templates','')+btn('类型与模块权限','pm-tool-permissions','','');
    if(active==='deliveries'&&C().canDeliver)top=action('新建分发','create-delivery','','primary');
    if(active==='inspections')top=action('执行巡检','inspect','','primary');
    let html=title(name,desc,top)+`<div class="tabs ct-tabs">${allowedTabs.map(([key,label])=>`<button data-action="ct-tab" data-id="${key}" class="${active===key?'active':''}">${label}</button>`).join('')}</div>`;
    if(route==='center-resources')html+=`<div class="ct-links"><a href="#/admin/approvals">资源使用审核</a><a href="#/admin/grants">授权台账</a><a href="#/front/shared-resources">使用端资源中心</a></div>`;
    if(active==='summary')html+=summary();
    else{
      html+=`<form id="ct-search" class="ct-search"><input name="q" aria-label="搜索当前中心" placeholder="搜索名称、状态或关键词" value="${esc(query)}"><button class="btn" type="submit">查询</button>${action('重置','reset','')}</form>`;
      if(['catalog','favorites'].includes(active))html+=renderCatalog();
      else{
        let rows=active==='tools'?D().portalManagement.tools:(C()[active]||[]);rows=rows.filter(r=>!query||JSON.stringify(r).includes(query));const count=rows.length;
        if(!['systems','nodes','sources','rules','directories','standards','tools'].includes(active))rows=rows.slice().reverse();
        html+=`<section class="panel">${listing(active,rows.slice((page-1)*12,page*12))}</section><div class="pagination"><span>共 ${count} 项 · 第 ${page} 页</span>${page>1?action('上一页','page',String(page-1)):''}${page*12<count?action('下一页','page',String(page+1)):''}</div>`;
      }
    }
    $('#main').innerHTML=`<div class="ct-workspace ${mode==='front'?'portal-container':''}">${html}</div>`;
    $('#ct-search')?.addEventListener('submit',e=>{e.preventDefault();query=new FormData(e.target).get('q').trim();page=1;render();});
    ['kind','sort','directory'].forEach(k=>$('#ct-'+k)?.addEventListener('change',e=>{sessionStorage.setItem('ct-'+k+'-'+route,e.target.value);page=1;render();}));
    return true;
  }
  async function actionHandler(a,id){
    if(!a.startsWith('ct-'))return false;const op=a.slice(3);
    if(op==='tab'){if(id.startsWith('@'))nav('/admin/'+id.slice(1));else{active=id;query='';page=1;render();}return true;}
    if(op==='page'){page=Number(id);render();return true;}
    if(op==='reset'){query='';page=1;render();return true;}
    if(op==='tool-templates'){await send('tool.templates',{},true);return true;}
    if(op==='favorite'){await send('favorite',{id});return true;}
    if(op==='edit'){const [entity,key]=id.split(':');editor(entity,key);return true;}
    if(op==='detail'){const [entity,key]=id.split(':');const r=C()[entity].find(x=>x.id===key);viewResult(r);return true;}
    const simple={
      'check-system':['system.check','systems'],'check-source':['source.check','sources'],
      'submit-ingestion':['ingestion.submit','ingestions'],'check-ingestion':['ingestion.check','ingestions'],'register-ingestion':['ingestion.register','ingestions'],
      'review-issue':['issue.review','issues'],'publish-standard':['standard.publish','standards'],'publish-service':['publication.publish','publications'],'disable-service':['publication.disable','publications'],
      'pause-subscription':['subscription.pause','subscriptions'],'resume-subscription':['subscription.resume','subscriptions'],'run-subscription':['subscription.run','subscriptions']
    };
    if(simple[op]){const [apiOp,entity]=simple[op],r=C()[entity].find(x=>x.id===id);await send(apiOp,{id,rev:r.rev},['check-system','check-source','check-ingestion','review-issue','run-subscription'].includes(op));return true;}
    if(op==='import-todos'){
      const sample=[{id:'external-demo-001',name:'示例规划事项待办',userId:'u1',status:'待办',dueAt:'2026-12-31T18:00:00',entry:'#/front/workbench'}];
      form('导入来源系统待办',`<p class="ct-full notice">按系统字段映射解析。同一来源标识重复导入会更新记录；导入完成不表示外部接口已联通。</p>`+f('payload','待办 JSON 数组（示例字段需与映射一致）',sample,'json'),v=>send('todos.import',{systemId:id,payload:v.payload},true));
    }else if(op==='export-node'){download(await api('centers.node.export',{id}));await ctx.reload();}
    else if(op==='return-ingestion'){
      const r=C().ingestions.find(x=>x.id===id);form('退回归集批次',f('note','退回原因','','textarea'),v=>send('ingestion.return',{id,rev:r.rev,...v}));
    }else if(op==='create-issue'){
      form('发起数据治理工单',f('assigneeId','处理人','admin','select',D().accounts.map(x=>[x.id,x.name+' · '+x.department])),v=>send('quality.issue',{id,...v}));
    }else if(op==='feedback-issue'){
      const issue=C().issues.find(x=>x.id===id),r=C().ingestions.find(x=>x.id===issue.ingestionId);
      form('整改反馈',f('note','整改说明','','textarea')+f('evidence','处理依据 / 证据说明','','textarea')+f('dataRows','整改后的 CSV（复核时重新执行质检）',r.dataRows,'textarea'),v=>send('issue.feedback',{id,rev:issue.rev,...v}));
    }else if(op==='create-dataset'){
      form('按标准创建库表',f('name','数据集名称')+f('standardId','已发布标准','standard-basic','select',C().standards.filter(x=>x.status==='已发布').map(x=>[x.id,x.name]))+f('layer','数仓分层','基础层','select',['原始层','基础层','专题层'])+f('category','业务分类','基础数据'),v=>send('dataset.create',v));
    }else if(op==='sharing'){
      const r=C().sharing[id]||{};form('共享资源编目',f('directoryId','所属目录',r.directoryId||'dir-data','select',options('directories'))+f('tags','资源标签（英文逗号分隔）',r.tags||''),v=>send('sharing.save',{resourceId:id,rev:r.rev,...v}));
    }else if(op==='query-service'){
      form('技术服务试查询',f('region','行政区过滤','全区','select',D().regions)+f('fields','返回字段（逗号分隔，留空使用可显示字段）')+f('q','业务关键词'),v=>send('service.query',{id,...v},true));
    }else if(op==='create-delivery'||op==='request-delivery'){
      const admin=op==='create-delivery';form(admin?'新建资源分发':'申请交付',
        (admin?f('userId','接收人','u1','select',D().accounts.map(x=>[x.id,x.name]))+f('resourceId','已发布资源',D().resources[0]?.id,'select',D().resources.filter(x=>x.published||x.status==='已发布').map(x=>[x.id,x.name])):'')+
        f('method','交付方式','数据下载','select',['数据下载','数据访问','离线获取'])+f('region','行政区筛选','全区','select',D().regions)+f('fields','交付字段（逗号分隔，可留空）')+`<p class="ct-full muted">接收人必须已获资源使用授权。字段筛选仅约束此交付包，不代替全平台字段级授权。</p>`,v=>send(admin?'delivery.create':'delivery.request',{...v,...(!admin?{resourceId:id}:{})}));
    }else if(op==='run-delivery'){
      const r=C().deliveries.find(x=>x.id===id);
      if(r.method==='离线获取')form('准备离线领取通知',f('pickupPlace','领取地点',r.pickupPlace)+f('pickupAt','领取时间',r.pickupAt,'datetime-local'),v=>send('delivery.run',{id,rev:r.rev,...v},true));
      else await send('delivery.run',{id,rev:r.rev},true);
    }else if(op==='download-delivery'){download(await api('centers.delivery.download',{id}));await ctx.reload();}
    else if(op==='open-delivery'){const r=await api('centers.delivery.endpoint',{id});modal('已授权的服务入口',`<a class="btn primary" href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">打开服务</a>`);}
    else if(op==='receive-delivery'){const r=C().deliveries.find(x=>x.id===id);await send('delivery.receive',{id,rev:r.rev,note:'使用人确认已领取'});}
    else if(op==='register-subscription'){
      form('注册订阅接收端',`<p class="ct-full notice">当前接收端为本地交付箱，定时生成可领取的数据批次；未向外部 HTTP 地址推送。</p>`+f('intervalSeconds','生成周期（60～86400秒）',3600,'number'),v=>send('subscription.create',{deliveryId:id,intervalSeconds:Number(v.intervalSeconds)}));
    }else if(op==='inspect')await send('inspection.run',{},true);
    else if(op==='submit-tool'){
      const r=D().portalManagement.tools.find(x=>x.id===id);await send('tool.submit',{id,rev:r.rev});
    }else if(op==='review-tool'){
      const r=D().portalManagement.tools.find(x=>x.id===id);form('工具上架审核 · '+r.name,f('decision','审核结果','通过','select',['通过','驳回'])+f('note','审核意见（至少5字）','','textarea'),v=>send('tool.review',{id,rev:r.rev,...v}));
    }else if(op==='trial-tool'){
      const r=D().portalManagement.tools.find(x=>x.id===id),geometry={type:'Polygon',coordinates:[[[111.7,40.75],[111.76,40.75],[111.76,40.81],[111.7,40.81],[111.7,40.75]]]};
      const defaults=r.engine==='coordinate'?{x:111.7,y:40.8,source:'EPSG:4326',target:'EPSG:3857'}:r.engine==='buffer'?{x:111.7,y:40.8,distance:100}:r.engine.startsWith('spatial-')?{resourceId:'r3',featureId:'feature-demo',revision:1,geometry,properties:{name:'测试地块'},operation:'update',q:''}:{geometry:r.engine==='overlay'?{type:'FeatureCollection',features:[{type:'Feature',geometry},{type:'Feature',geometry}]}:geometry,crs:'EPSG:4326',operation:'intersection'};
      let value=defaults;try{if(r.inputExample)value=JSON.parse(r.inputExample);}catch{}
      form('接口试运行 · '+r.name,`<p class="ct-full muted">执行能力：${esc(r.engine)}。结果保留输入、耗时及失败原因；写入类工具仅操作本地工作图层。</p>`+f('payload','接口请求 JSON',value,'json'),async v=>{trialResult=await send('tool.trial',{id,payload:v.payload},true);});
    }
    return true;
  }
  return {render,action:actionHandler};
}
