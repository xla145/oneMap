// Presentation helpers: backend remains authoritative for quality and import validation.
export function csvColumns(text = '') {
  const fields = []; let value = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') { value += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && char === ',') { fields.push(value.trim()); value = ''; }
    else if (!quoted && (char === '\n' || char === '\r')) break;
    else value += char;
  }
  fields.push(value.trim().replace(/^\uFEFF/, ''));
  return fields.filter(Boolean);
}

export function mappingValues(form) {
  const pairs = [...form.querySelectorAll('[data-map-field]')].map(el => [el.dataset.mapField, el.value]);
  if (!pairs.length || pairs.some(([, source]) => !source)) throw new Error('请为每个目标字段选择来源字段');
  if (new Set(pairs.map(([, source]) => source)).size !== pairs.length) throw new Error('同一个来源字段不能重复映射');
  return Object.fromEntries(pairs);
}

export function collectionStage(order, batch, report, issues = []) {
  if (!batch) return {step: order?.status === '待审核' ? 1 : 0, label: order?.status === '待审核' ? '待审核材料' : order?.status === '已退回' ? '材料已退回' : '等待报送'};
  if (batch.status === '已入库') return {step: 4, label: '入库完成'};
  if (issues.some(row => row.status !== '已办结')) return {step: 2, label: '整改与复核中'};
  if (!report) return {step: 2, label: '等待质检'};
  if (report.dataRevision !== batch.dataRevision || ['草稿','已退回','待质检'].includes(batch.status)) return {step: 2, label: '需要重新质检'};
  if (!report.passed) return {step: 2, label: '质量不通过'};
  return {step: 3, label: '待入库校验'};
}

export function createCollectionWorkflow(ctx) {
  const {esc, tag, btn, field, table, tr, link, api, submit, reload, data} = ctx;
  const get = () => {const d = data(); return {d, c:d.centers, o:d.operations};};
  const wrapForm = (id, title, body, action) => `<form id="${id}" class="oc-inline-form"><h3>${title}</h3><div class="ct-form-grid">${body}</div><p class="ct-error" role="alert"></p><button class="btn primary" type="submit">${action}</button></form>`;
  function mapping(batch, target, saved = {}) {
    const columns = csvColumns(batch?.dataRows);
    if (!target) return '<p class="muted">请先选择目标空表，或在下方按标准建表。</p>';
    return table(['目标字段','来源字段'],target.fields.map(name=>tr(esc(name),`<select aria-label="${esc(name)} 的来源字段" data-map-field="${esc(name)}" required><option value="">请选择来源字段</option>${columns.map(col=>`<option value="${esc(col)}" ${(saved[name] ?? (columns.includes(name)?name:''))===col?'selected':''}>${esc(col)}</option>`).join('')}</select>`)));
  }
  function render(order, batch) {
    const {d,c,o} = get();
    const report = c.qualityRuns.find(x=>x.id===batch?.qualityRunId);
    const issues = c.issues.filter(x=>batch && x.ingestionId===batch.id);
    const stage = collectionStage(order,batch,report,issues);
    let html = `<section class="panel oc-panel oc-journey"><div class="oc-section-title"><div><h2>报送办理进度</h2><p>当前：<strong>${esc(stage.label)}</strong></p></div>${tag(batch?.status==='已入库'?'已入库':order?.status||batch?.status||'待报送')}</div><ol class="oc-steps">${['材料报送','登记审核','质检与整改','确认入库'].map((name,i)=>`<li class="${i<stage.step?'done':i===stage.step?'current':''}" ${i===stage.step?'aria-current="step"':''}><span>${i<stage.step?'✓':i+1}</span>${name}</li>`).join('')}</ol>`;
    if (!o.canManage) return html+'<p>在下方提交本人材料或查看审核记录；后续检查和入库由管理员办理。</p></section>';
    if (!batch) return html+`<p>${order?.status==='待审核'?'请核对下方报送材料。审核通过后，在此继续质检和入库。':'等待报送人提交材料。退回意见和历次材料保留在下方。'}</p>${order?.status==='待审核'?btn('审核材料','oc-review',order.id,'primary'):''}</section>`;
    html+=`<p class="muted">${esc(batch.name)} · 数据版本 ${batch.dataRevision}。审核、质量和入库结果分别记录。</p>`;
    if (batch.status==='已入库') return html+`<p>数据已成功入库。下一步可完善资产目录，按需发布接口。</p>${link('catalog/assets','查看并完善资产',batch.resourceId,'primary')}</section>`;
    if (['草稿','已退回'].includes(batch.status)) return html+`<p>请先完善批次材料并提交质检。</p>${btn('编辑材料','ct-edit','ingestions:'+batch.id)}${btn('提交质检','ct-submit-ingestion',batch.id,'primary')}</section>`;
    if (report) {
      html+=`<div class="oc-quality-summary">${tag(report.passed?'最近质量通过':'最近质量不通过')}<span>${report.total} 行 · ${report.issues.length} 项问题</span>${link('quality/results','完整报告',report.id,'small')}</div>`;
      if(report.issues.length) html+=table(['数据行','字段','问题'],report.issues.slice(0,10).map(x=>tr(esc(x.row||'表头'),esc(x.field),esc(x.message))))+`<p class="muted">显示前 ${Math.min(10,report.issues.length)} 项；完整问题见报告。</p>`;
      if(report.issues.length&&!issues.some(x=>x.status!=='已办结')) html+=btn('派发整改','ct-create-issue',report.id,'primary');
    }
    if(issues.length) html+=table(['整改工单','处理人','状态','办理'],issues.map(x=>tr(esc(x.name),esc(x.assigneeName),tag(x.status),(x.assigneeId===d.user.id&&['待处理','已退回'].includes(x.status)?btn('提交整改','oc-feedback',x.id):'')+(x.status==='待复核'?btn('复检并办结','ct-review-issue',x.id,'primary'):'')+link('quality/orders','记录',x.id,'small'))));
    const models=o.models.filter(x=>x.published);
    const qualityBody=models.length?field('modelId','采用质检模板',models[0].id,'select',models.map(x=>[x.id,x.name+' · v'+x.published.version])):'<p>尚无已发布模板，将按该批次已绑定的规则检查。</p>';
    html+=wrapForm('oc-flow-quality','检查当前数据',qualityBody,report?'重新质检':'执行质检');
    if(stage.step===3) {
      const targets=c.datasets.filter(x=>x.rowCount===0 && !d.resources.find(r=>r.id===x.resourceId)?.published);
      const previous=o.imports.filter(x=>x.ingestionId===batch.id&&['草稿','失败'].includes(x.status)).at(-1);
      const chosen=targets.find(x=>x.id===previous?.datasetId)||targets[0];
      html+=wrapForm('oc-flow-import','确认目标与字段对应关系',field('datasetId','目标空表',chosen?.id||'','select',[['','请选择目标空表'],...targets.map(x=>[x.id,x.name])])+`<div id="oc-flow-mapping" class="ct-full">${mapping(batch,chosen,previous?.mapping)}</div><p class="ct-full muted">同名字段已预填，请核对。执行前会再次检查最新数据、标准、规则及整改状态。</p>`,'校验并入库');
      const attempts=o.imports.filter(x=>x.ingestionId===batch.id).flatMap(x=>x.attempts);
      if(attempts.length) html+=`<details><summary>入库执行记录（${attempts.length} 次）</summary>${table(['时间','结果','说明'],attempts.slice().reverse().map(x=>tr(esc(x.at),tag(x.status),esc(x.error||'已写入 '+x.rowCount+' 行'))))}</details>`;
      html+=`<details ${targets.length?'':'open'}><summary>没有合适的空表？按标准新建</summary>${wrapForm('oc-flow-table','准备入库表',field('name','表名称',batch.name+' · 数据表')+field('standardId','采用标准',batch.standardId,'select',c.standards.filter(x=>x.status==='已发布').map(x=>[x.id,x.name]))+field('domainId','存放位置','','select',o.domains.filter(x=>c.sources.find(s=>s.id===x.sourceId)?.kind==='CSV文件').map(x=>[x.id,x.name])),'创建空表并返回')}</details>`;
    } else html+='<p class="oc-blocked">完成当前材料检查及整改复核后，这里会显示入库操作。</p>';
    return html+'</section>';
  }
  function bind(batch) {
    if(!batch) return;
    const {d,c,o}=get();
    const bindForm=(id,fn)=>{const form=document.getElementById(id);form?.addEventListener('submit',e=>{e.preventDefault();submit(form,()=>fn(form));});};
    bindForm('oc-flow-quality',async form=>{
      const modelId=form.elements.modelId?.value;
      if(modelId){
        const model=o.models.find(x=>x.id===modelId);
        let task=o.qualityTasks.filter(x=>x.ingestionId===batch.id&&x.modelId===modelId&&x.modelSnapshot.version===model.published.version).at(-1);
        if(!task) task=await api('operations.save',{entity:'qualityTasks',values:{name:batch.name+' · 质检',ingestionId:batch.id,modelId}});
        await api('operations.quality.run',{id:task.id,rev:task.rev});
      } else await api('centers.ingestion.check',{id:batch.id,rev:batch.rev});
      await reload();
    });
    document.querySelector('#oc-flow-import [name=datasetId]')?.addEventListener('change',e=>{
      document.getElementById('oc-flow-mapping').innerHTML=mapping(batch,c.datasets.find(x=>x.id===e.target.value));
    });
    bindForm('oc-flow-import',async form=>{
      const datasetId=form.elements.datasetId.value;
      if(!datasetId)throw new Error('请选择目标空表');
      const values={name:batch.name+' · 入库',ingestionId:batch.id,datasetId,mapping:mappingValues(form)};
      const previous=o.imports.filter(x=>x.ingestionId===batch.id&&['草稿','失败'].includes(x.status)).at(-1);
      const task=await api('operations.save',{entity:'imports',id:previous?.id,rev:previous?.rev,values});
      const result=await api('operations.import.run',{id:task.id,rev:task.rev});
      // Failures are persisted business results, not HTTP errors; refresh the attempt log first.
      await reload();
      if(result.status==='失败')ctx.toast(result.attempts.at(-1)?.error||'入库失败，请查看执行记录');
    });
    bindForm('oc-flow-table',async form=>{
      await api('operations.dataset.create',Object.fromEntries(new FormData(form)));
      await reload();
    });
  }
  return {render,bind,mapping};
}
