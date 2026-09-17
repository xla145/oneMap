// Live configuration workspace. Saves and publication use existing business APIs.
export const configurationTypes = [
  ['standards','数据标准','规定报送字段和建表结构','centers'],
  ['models','质检模板','组合检查规则，供数据质检选择','operations'],
  ['rules','检查规则','定义必填、唯一和取值检查','centers'],
  ['sources','数据来源','登记提供单位及接入方式','centers'],
  ['directories','资产目录','维护资产分类及层级','operations'],
  ['domains','存储位置','设置建表时可以选择的存放位置','operations'],
  ['alertRules','告警规则','指定异常级别与处理人员','operations'],
];

export function modelReadiness(model, rules) {
  if (!model.published) return '尚未发布';
  if (!model.published.rules?.length || model.published.rules.some(snapshot=>{
    const current=rules.find(rule=>rule.id===snapshot.id);
    return !current || !current.enabled || current.rev!==snapshot.rev;
  })) return '规则已变化，需重新发布';
  return model.status==='草稿'?'已发布版本可用，有待发布修改':'已发布版本可用';
}

export function configurationReadiness(data) {
  const c=data.centers,o=data.operations;
  const standards=c.standards.filter(x=>x.status==='已发布');
  const local=c.sources.filter(x=>x.kind==='CSV文件');
  const domains=o.domains.filter(x=>local.some(s=>s.id===x.sourceId));
  const models=o.models.filter(x=>modelReadiness(x,c.rules).startsWith('已发布版本可用'));
  const alerts=o.alertRules.filter(x=>x.enabled&&data.accounts.some(a=>a.id===x.assigneeId&&a.enabled!==false&&a.role==='平台管理员'));
  return [
    {key:'standards',label:'报送标准',count:standards.length,ready:!!standards.length,detail:standards.length?'新建归集任务时可选择已发布标准':'尚无已发布标准，归集任务和按标准建表会受阻'},
    {key:'models',label:'质检模板',count:models.length,ready:!!models.length,detail:models.length?'规则版本有效，可在报送详情选择':'尚无有效模板；现有批次仍可按绑定规则检查'},
    {key:'domains',label:'入库存储',count:domains.length,ready:!!domains.length,detail:domains.length?'已配置本地存放位置，可继续按标准建表':'尚无本地存放位置；外部地址登记不代表可写入'},
    {key:'alertRules',label:'异常处置',count:alerts.length,ready:!!alerts.length,detail:alerts.length?'启用规则已指定可用处理人员':'尚无启用且处理人有效的规则，请检查告警配置'},
  ];
}

export function validateStandardFields(fields) {
  if(!fields.length||fields.length>100)throw new Error('请配置 1～100 个字段');
  const seen=new Set();
  for(const [index,f] of fields.entries()){
    if(!/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(f.name))throw new Error(`第 ${index+1} 行字段标识需以字母或下划线开头，最多 64 位`);
    if(seen.has(f.name))throw new Error(`字段标识 ${f.name} 重复，请修改`);
    if(!f.label.trim())throw new Error(`第 ${index+1} 行请填写中文名称`);
    if(!['text','number','date'].includes(f.type))throw new Error(`第 ${index+1} 行字段类型无效`);
    seen.add(f.name);
  }
  return fields;
}

export function createOperationsSettings(ctx) {
  const {esc,field,tag,api,data,head,table,tr,submit}=ctx;
  const current=()=>{
    const params=new URLSearchParams(location.hash.split('?')[1]);
    const type=configurationTypes.find(x=>x[0]===params.get('config'))||configurationTypes[0];
    const rows=data()[type[3]==='centers'?'centers':'operations'][type[0]]||[];
    const requested=params.get('record');
    return {type,rows,record:requested==='new'?null:requested?rows.find(x=>x.id===requested):rows[0],missing:requested&&requested!=='new'&&!rows.some(x=>x.id===requested),creating:requested==='new'||!rows.length};
  };
  const href=(key,id)=>'#/admin/operations/settings?'+new URLSearchParams({config:key,...(id?{record:id}:{})});
  const control=(text,action,extra='')=>`<button type="button" class="btn small" data-config-action="${action}" ${extra}>${text}</button>`;
  function references(key,r){
    const d=data(),c=d.centers,o=d.operations;
    const groups={
      standards:[['归集任务',o.tasks,'standardId','collection/tasks'],['数据批次',c.ingestions,'standardId','collection/batches'],['数据表',c.datasets,'standardId','warehouse/tables']],
      models:[['质检任务',o.qualityTasks,'modelId','quality/tasks']],
      rules:[['质检模板',o.models.filter(x=>x.ruleIds.includes(r.id)||x.published?.rules.some(rule=>rule.id===r.id)),null,'quality/models'],['数据批次',c.ingestions.filter(x=>x.ruleIds.includes(r.id)),null,'collection/batches']],
      sources:[['归集任务',o.tasks,'sourceId','collection/tasks'],['数据批次',c.ingestions,'sourceId','collection/batches'],['存储位置',o.domains,'sourceId','warehouse/domains']],
      directories:[['编目资产',o.catalogs,'directoryId','catalog/assets']],
      domains:[['数据表',c.datasets,'domainId','warehouse/tables']],
      alertRules:[['告警事件',o.alerts,'ruleId','monitoring/alerts']],
    };
    return (groups[key]||[]).map(([label,rows,foreign,path])=>({label,rows:foreign?rows.filter(x=>x[foreign]===r.id):rows,path}));
  }
  function description(key,r){
    const d=data(),c=d.centers,o=d.operations;
    if(key==='standards')return `${r.fields.length} 个字段 · 版本 ${r.version}`;
    if(key==='models')return `${r.ruleIds.length} 项检查 · ${modelReadiness(r,c.rules)}`;
    if(key==='rules')return `${r.field} · ${r.kind}`;
    if(key==='sources')return `${r.provider} · ${r.kind==='CSV文件'?'本地文件报送':'外部接入待联调'}`;
    if(key==='directories')return `${r.kind} · ${o.catalogs.filter(x=>x.directoryId===r.id).length} 项资产`;
    if(key==='domains')return `${r.kind} · ${c.sources.find(s=>s.id===r.sourceId)?.name||'来源已失效'}`;
    return `${r.kind} · ${r.level} · ${d.accounts.find(a=>a.id===r.assigneeId)?.name||'处理人已失效'}`;
  }
  function fieldRow(f={}){
    return `<div class="oc-standard-row" data-standard-row><label>字段标识<input data-column="name" aria-label="字段标识" value="${esc(f.name||'')}" placeholder="例如 area" maxlength="64" required></label><label>中文名称<input data-column="label" aria-label="中文名称" value="${esc(f.label||'')}" placeholder="例如 面积" required></label><label>类型<select data-column="type" aria-label="字段类型">${[['text','文本'],['number','数字'],['date','日期']].map(([v,label])=>`<option value="${v}" ${f.type===v?'selected':''}>${label}</option>`).join('')}</select></label><label class="oc-check"><input data-column="required" type="checkbox" ${f.required?'checked':''}>必填</label>${control('移除','remove-field','aria-label="移除字段"')}</div>`;
  }
  function fields(key,r){
    const d=data(),c=d.centers,o=d.operations;
    const f=(key,label,fallback='',type='text',options=[])=>field(key,label,r[key]??fallback,type,options);
    let html=f('name','名称 *');
    if(key==='standards')html+=`<section class="ct-full oc-standard-editor"><div class="oc-section-title"><h3>报送字段</h3>${control('添加字段','add-field')}</div><p class="muted">每行定义一个字段；字段标识用于数据匹配，中文名称供报送人阅读。</p><div id="oc-standard-fields">${(r.fields||[{name:'',label:'',type:'text',required:true}]).map(fieldRow).join('')}</div></section>`;
    if(key==='models')html+=`<fieldset class="ct-full oc-rule-picker"><legend>选择要执行的检查</legend>${c.rules.map(rule=>`<label class="oc-rule-option"><input type="checkbox" name="ruleIds" value="${esc(rule.id)}" ${(r.ruleIds||[]).includes(rule.id)?'checked':''} ${!rule.enabled?'disabled':''}><span><strong>${esc(rule.name)}</strong><small>${esc(rule.field)} · ${esc(rule.kind)}${!rule.enabled?' · 已停用':''}</small></span></label>`).join('')||'<p>还没有检查规则，请先添加规则。</p>'}</fieldset>`;
    if(key==='rules')html+=f('field','检查哪个字段 *')+f('kind','检查方式','必填','select',['必填','唯一','非负数','枚举','日期'])+f('argument','允许值（仅枚举填写，逗号分隔）')+f('enabled','启用此规则',true,'checkbox');
    if(key==='sources')html+=f('provider','提供单位 *',d.user.department)+f('kind','接入类型','CSV文件','select',['CSV文件','Oracle','PostgreSQL','空间数据库','ArcGISService','GeoServer','Geoscene'])+f('region','所属区划','全区','select',d.regions)+f('endpoint','服务地址（外部接入填写 HTTPS 地址）')+f('description','来源说明','','textarea');
    if(['directories','domains'].includes(key)){
      html+=f('parentId','上级节点','','select',[['','根节点'],...o[key].filter(x=>x.id!==r.id).map(x=>[x.id,x.name])]);
      html+=f('kind','节点类型',key==='domains'?'数据库':'公共目录','select',key==='domains'?['业务域','数仓层','数据库','数据空间']:['公共目录','数据库表','图层服务','工具服务','知识文档']);
      if(key==='domains')html+=f('sourceId','数据来源 *','','select',c.sources.map(x=>[x.id,x.name+(x.kind==='CSV文件'?' · 可本地建表':' · 待外部联调')]));
    }
    if(key==='alertRules')html+=f('kind','关注的异常','质检异常','select',['质检异常','交付失败','服务依赖异常'])+f('level','告警级别','警告','select',['提示','警告','严重'])+f('assigneeId','由谁处理 *','','select',d.accounts.filter(x=>x.role==='平台管理员'&&x.enabled!==false).map(x=>[x.id,x.name]))+f('enabled','启用此告警',true,'checkbox');
    return html;
  }
  function detail(key,r){
    const editable=r||{},draftType=['standards','models'].includes(key);
    const notes={standards:'保存后成为草稿，发布后才能供新任务和建表选择。修改正在使用的标准可能要求关联任务重新校验；旧表结构与历史报告不自动改写。',models:'保存后成为草稿，已发布的规则快照仍保留。发布新版本后，已有质检任务仍采用原快照，需单独更新。',rules:'保存立即生效。修改或停用被模板引用的规则后，需要重新发布模板；旧质检报告也可能需要重新校验。',sources:'CSV 可用于本地报送。外部数据库或 GIS 仅登记配置；检查配置不会尝试远程连接。',directories:'目录用于技术编目。修改分类不增加或撤销共享授权。',domains:'只有关联本地 CSV 来源的位置支持当前原型建表；外部库仍需接入。',alertRules:'启用后在下次手动巡检时参与匹配。修改不会重写已产生的告警；短信、钉钉通知尚未接入。'};
    let html=`<section class="panel oc-config-detail"><div class="oc-section-title"><div><small>${r?'维护现有配置':'创建配置'}</small><h2>${esc(r?.name||'新增'+configurationTypes.find(t=>t[0]===key)[1])}</h2></div>${r?tag(r.status):tag('未保存')}</div><p class="oc-config-notice">${notes[key]}</p>`;
    if(r){
      const refs=references(key,r);html+=`<details class="oc-config-impact"><summary>使用情况 · ${refs.reduce((n,g)=>n+g.rows.length,0)} 条关联记录</summary>${refs.map(g=>`<p><strong>${g.label} ${g.rows.length}</strong></p><div class="oc-links">${g.rows.slice(0,10).map(x=>`<a class="btn small" href="#/admin/operations/${g.path}/${encodeURIComponent(key==='directories'?x.resourceId:x.id)}">${esc(x.name)}</a>`).join('')||'<span class="muted">暂无关联</span>'}${g.rows.length>10?`<a class="btn small" href="#/admin/operations/${g.path}">查看全部记录</a>`:''}</div>`).join('')}</details>`;
    }
    html+=`<form id="oc-config-form"><div class="ct-form-grid">${fields(key,editable)}</div><p class="ct-error" role="alert"></p><div class="oc-config-save"><button class="btn primary" type="submit">${draftType?'保存草稿':'保存配置'}</button>${r&&draftType&&r.status==='草稿'?control('发布供业务使用','publish','data-pristine-action'):''}${r&&key==='sources'?control('检查配置','check-source','data-pristine-action'):''}<span id="oc-config-save-state" role="status">${r?'正在查看已保存配置':'填写后保存'}</span></div></form>`;
    if(r?.history?.length)html+=`<details><summary>最近修改记录</summary>${table(['时间','操作人','操作'],r.history.slice(-5).reverse().map(x=>tr(esc(x.at),esc(x.actor),esc(x.action))))}</details>`;
    return html+'</section>';
  }
  function render(){
    const {type,rows,record,creating,missing}=current(),[key,label,intro]=type;
    const status=configurationReadiness(data());
    return head('配置管理','先看业务准备情况，再直接维护配置。保存的内容会用于归集、质检、建表和告警。')+`<div id="oc-settings"><section class="oc-config-readiness" aria-label="业务准备情况">${status.map(x=>`<a href="${href(x.key)}" class="${x.ready?'ready':'needs-work'}"><span>${x.label}</span><strong>${x.count} <small>${x.ready?'项可用':'项可用 · 待准备'}</small></strong><p>${x.detail}</p></a>`).join('')}</section><nav class="oc-config-tabs" aria-label="配置类别">${configurationTypes.map(([type,name,,scope])=>`<a href="${href(type)}" ${type===key?'aria-current="page"':''}>${name}<span>${data()[scope==='centers'?'centers':'operations'][type].length}</span></a>`).join('')}</nav><div class="oc-config-workspace"><section class="panel oc-config-list"><div class="oc-section-title"><h2>${label}</h2><a class="btn small" href="${href(key,'new')}">新增</a></div><p>${intro}</p><label class="oc-config-search">查找配置<input id="oc-config-search" type="search" placeholder="按名称或内容查找"></label><div id="oc-config-records">${rows.map(row=>`<a class="oc-config-record ${record?.id===row.id&&!creating?'selected':''}" href="${href(key,row.id)}" data-config-search="${esc((row.name+' '+descriptionFor(row)).toLowerCase())}"><strong>${esc(row.name)}</strong><span>${esc(descriptionFor(row))}</span>${tag(row.status)}</a>`).join('')}<p id="oc-config-empty" ${rows.length?'hidden':''}>尚无配置，点击“新增”开始维护。</p></div></section>${missing?'<section class="panel oc-config-detail"><h2>配置不存在</h2><p>请从左侧选择现有配置。</p></section>':detail(key,creating?null:record)}</div><details class="oc-config-advanced"><summary>来源系统与专业台账</summary><p>这些入口用于接入和查询，不参与以上配置就绪判断。</p><div class="oc-setting-links">${[['catalog/systems','来源系统'],['standards/changes','标准变更记录'],['quality/tasks','质检任务'],['quality/results','质检报告'],['quality/reports','质量统计'],['collection/imports','入库记录'],['catalog/relations','资产关系']].map(([path,name])=>`<a class="btn" href="#/admin/operations/${path}">${name}</a>`).join('')}<a class="btn" href="#/admin/resources">资源与元数据</a><a class="btn" href="#/admin/quality">元数据质量检查</a><a class="btn" href="#/admin/portal-monitor">主机与请求监控</a><a class="btn" href="#/admin/portal-audit">统一日志</a></div></details></div>`;
    function descriptionFor(row){return description(key,row);}
  }
  async function refresh(key,id,message){
    ctx.setDirty(false);await ctx.load();
    if(location.hash===href(key,id))ctx.render();else location.hash=href(key,id);
    ctx.toast(message);
  }
  function bind(){
    const container=document.getElementById('oc-settings');if(!container)return;
    const {type,record,creating}=current(),[key,,,scope]=type;
    const row=creating?null:record,form=document.getElementById('oc-config-form');
    const changed=()=>{
      ctx.setDirty(true);
      const status=document.getElementById('oc-config-save-state');if(status)status.textContent='有未保存修改';
      form?.querySelectorAll('[data-pristine-action]').forEach(x=>x.disabled=true);
    };
    form?.addEventListener('input',changed);form?.addEventListener('change',changed);
    document.getElementById('oc-config-search')?.addEventListener('input',e=>{
      let count=0;container.querySelectorAll('[data-config-search]').forEach(x=>{x.hidden=!x.dataset.configSearch.includes(e.target.value.trim().toLowerCase());if(!x.hidden)count++;});
      const empty=document.getElementById('oc-config-empty');empty.hidden=count>0;empty.textContent='没有匹配的配置，可以调整关键词或新增。';
    });
    form?.addEventListener('submit',e=>{e.preventDefault();submit(form,async()=>{
      const values=Object.fromEntries(new FormData(form));
      form.querySelectorAll('input[type=checkbox][name]').forEach(x=>{if(x.name!=='ruleIds')values[x.name]=x.checked;});
      if(key==='standards')values.fields=validateStandardFields([...form.querySelectorAll('[data-standard-row]')].map(el=>Object.fromEntries([...el.querySelectorAll('[data-column]')].map(input=>[input.dataset.column,input.type==='checkbox'?input.checked:input.value.trim()]))));
      if(key==='models'){
        values.ruleIds=[...form.querySelectorAll('[name=ruleIds]:checked:not(:disabled)')].map(x=>x.value);
        if(!values.ruleIds.length)throw new Error('请至少选择一条已启用的检查规则');
      }
      const result=await api(scope+'.save',{entity:key,id:row?.id,rev:row?.rev,values});
      await refresh(key,result.id,['standards','models'].includes(key)?'草稿已保存，发布后供业务使用':'配置已保存');
    });});
    container.addEventListener('click',async e=>{
      const button=e.target.closest('[data-config-action]');if(!button||button.disabled)return;
      const action=button.dataset.configAction;
      if(action==='add-field'){
        if(form.querySelectorAll('[data-standard-row]').length>=100){ctx.toast('最多配置 100 个字段');return;}
        document.getElementById('oc-standard-fields').insertAdjacentHTML('beforeend',fieldRow());changed();return;
      }
      if(action==='remove-field'){button.closest('[data-standard-row]').remove();changed();return;}
      button.disabled=true;
      try{
        const operation=action==='check-source'?'centers.source.check':key==='standards'?'centers.standard.publish':'operations.model.publish';
        await api(operation,{id:row.id,rev:row.rev});
        await refresh(key,row.id,action==='check-source'?(row.kind==='CSV文件'?'本地配置可用':'配置已登记，外部连接仍待联调'):'已发布，可在业务中选择');
      }catch(error){form.querySelector('[role=alert]').textContent=error.message;ctx.toast(error.message);button.disabled=false;}
    });
  }
  return {render,bind};
}
