// Shared pure view helpers. Filtering semantics are tested independently of DOM.
export function periodMatches(value, period, now = new Date()) {
  if (period === '全部时间') return true;
  if (!value) return false;
  const date = new Date(value), start = new Date(now), end = new Date(now);
  start.setHours(0, 0, 0, 0);
  if (period === '本周') start.setDate(start.getDate() - (start.getDay() + 6) % 7);
  else if (period === '本月') start.setDate(1);
  else if (period === '上月') { start.setDate(1); end.setTime(start.getTime()); start.setMonth(start.getMonth() - 1); }
  else start.setDate(start.getDate() - Number(period.replace(/\D/g, '')) + 1);
  return date >= start && (period === '上月' ? date < end : date <= end);
}

export function selectCases(cases, f, now = new Date()) {
  return cases.filter(c => periodMatches(c[f.dateBasis], f.timeWindow, now) &&
    (f.category === '全部' || c.category === f.category) &&
    (f.status === '全部' || (f.status === '待办' ? c.isTodo : c.status === f.status)) &&
    (f.compliance === '全部' || c.compliance === f.compliance) &&
    (!f.query || [c.name, c.projectId, c.category, c.workflow.nodes[c.nodeIndex]?.name].join(' ').includes(f.query)));
}

export function summarize(cases) {
  const active = cases.filter(c => !['已作废', '已撤回'].includes(c.status));
  const done = active.filter(c => c.status === '已办结');
  return {total: active.length, todo: active.filter(c => c.isTodo).length, done: done.length,
    rate: active.length ? Math.round(done.length / active.length * 100) + '%' : '—',
    ontime: done.filter(c => new Date(c.completedAt) <= new Date(c.dueAt)).length,
    projects: new Set(cases.map(c => c.projectId)).size,
    area: cases.reduce((sum, c) => sum + (Number(c.formData.area) || 0), 0)};
}

export function layerTree(layers, {esc, btn}, canLayers = true) {
  const root = {children: new Map(), layers: []};
  layers.forEach(layer => {
    let node = root;
    (layer.group || '业务图层').split('/').map(s => s.trim()).filter(Boolean).forEach(part => {
      if (!node.children.has(part)) node.children.set(part, {children: new Map(), layers: []});
      node = node.children.get(part);
    });
    node.layers.push(layer);
  });
  const descendants = n => [...n.layers, ...[...n.children.values()].flatMap(descendants)];
  const render = node => [...node.children].map(([name, child]) => {
    const leaves = descendants(child).filter(l => l.access === '已授权');
    const ids = leaves.map(l => l.id).join(',');
    const checked = leaves.length && leaves.every(l => l.visible);
    return `<details open class="pc-tree-node"><summary><input type="checkbox" aria-label="切换目录 ${esc(name)}" data-layer-group="${esc(ids)}" ${checked ? 'checked' : ''} ${!canLayers || !leaves.length ? 'disabled' : ''}><span>${esc(name)}</span><small>${descendants(child).length}</small></summary>${render(child)}</details>`;
  }).join('') + node.layers.map(l => `<div class="pc-tree-leaf"><label><input data-scene-layer="${esc(l.id)}" type="checkbox" ${l.visible ? 'checked' : ''} ${l.access !== '已授权' || !canLayers ? 'disabled' : ''}>${esc(l.name)}</label><small>${l.access === '已授权' ? '已授权' : btn('申请资源', 'resource', l.resourceId, 'text small')}</small></div>`).join('');
  return render(root);
}

export function workbenchView(v) {
  const {D, tab, filters, esc, btn, tag, fmt, title, metric, tabs, opts, table, notice} = v;
  const p = D.platform, cases = selectCases(p.cases, filters), summary = summarize(cases);
  const select = (id, label, options, value) => `<label>${label}<select id="${id}">${opts(options, value)}</select></label>`;
  let html = title(v.admin ? '办件台账' : '业务工作台', '申请、办理、核查与督办，围绕同一项目协同处理。', btn('发起业务', 'pc-start', '', 'primary', 'plus'));
  html += tabs([['overview','工作概览'],['todo','我的待办'],['all','办件台账'],['statistics','统计分析'],['supervision','任务督办'],['guides','法规与帮助']]);
  if (tab === 'guides') return html + `<div class="pc-two-column"><section class="panel pc-padding"><h2>法律法规</h2>${D.knowledge.map(k => btn(k.name,'portalKnowledge',k.id,'pc-guide-link')).join('')}</section><section class="panel pc-padding"><h2>帮助文档</h2>${p.helpDocs.map(d => `<details class="pc-help"><summary>${esc(d.name)}</summary><div class="pc-document">${esc(d.body)}</div></details>`).join('')}</section></div>`;
  html += `<section class="panel pc-filter-grid">${select('pc-date-basis','时间口径',[['createdAt','创建时间'],['completedAt','办结时间']],filters.dateBasis)}${select('pc-time-window','时间范围',['全部时间','本周','本月','上月','近7天','近14天','近30天'],filters.timeWindow)}${select('pc-case-category','业务类别',['全部','业务审批','数字会商'],filters.category)}${select('pc-case-status','办件状态',['全部','待办','在办','已办结','已挂起','已作废','已撤回'],filters.status)}${select('pc-case-compliance','合规状态',['全部','待核查','合规','不合规'],filters.compliance)}</section>`;
  html += `<div class="pc-metrics">${metric('有效办件',summary.total,'不含已撤回/已作废')}${metric('我的待办',summary.todo,'主任务、协办与有效代理')}${metric('已办结',summary.done)}${metric('完成率',summary.rate,'当前条件下的有效办件')}</div>`;
  if (tab === 'statistics' || tab === 'overview') {
    const groupRows = (key, project = false) => [...new Set(cases.map(key))].map(name => {
      const items = cases.filter(c => key(c) === name), n = project ? new Set(items.map(c => c.projectId)).size : items.length;
      const total = project ? summary.projects : cases.length;
      return `<div class="pc-stat-bar"><div><span>${esc(name)}</span><strong>${n} ${project ? '项目' : '件'} · ${total ? (n / total * 100).toFixed(1) : 0}%</strong></div><div><i style="width:${total ? n / total * 100 : 0}%"></i></div></div>`;
    }).join('') || '<p class="muted">当前条件无记录</p>';
    html += `<div class="pc-two-column"><section class="panel pc-padding"><h2>按业务概览</h2>${['业务审批','数字会商'].map(category => {const n=summarize(cases.filter(c=>c.category===category));return `<div class="pc-summary-line"><strong>${category}</strong><span>${n.total} 件</span><span>${n.todo} 待办</span><span>完成 ${n.rate}</span></div>`;}).join('')}<h3>项目类型与占比</h3>${groupRows(c=>c.projectType || '其他项目',true)}</section><section class="panel pc-padding"><h2>事项阶段与状态</h2>${groupRows(c=>c.workflow.nodes[c.nodeIndex]?.name || '未分类')}<h3>办件状态</h3>${groupRows(c=>c.status)}</section></div>`;
    html += `<section class="panel pc-padding pc-section-space"><h2>监管与面积</h2><div class="pc-metrics compact">${metric('项目数量',summary.projects,'按项目ID去重')}${metric('办件登记面积',summary.area.toFixed(2)+' 公顷','按匹配办件求和，非项目去重面积')}${metric('按时 / 超时办结',summary.ontime+' / '+(summary.done-summary.ontime))}${metric('合规 / 不合规',cases.filter(c=>c.compliance==='合规').length+' / '+cases.filter(c=>c.compliance==='不合规').length)}</div><h3>业务事项分布</h3>${groupRows(c=>p.models.find(m=>m.id===c.modelId)?.name || c.modelId)}</section>`;
    html += `<section class="panel pc-padding pc-section-space"><h2>按状态统计项目和面积</h2><div class="table-scroll"><table><thead><tr><th>状态</th><th>办件数量</th><th>项目数量</th><th>登记面积（公顷）</th></tr></thead><tbody>${['在办','已办结','已挂起','已撤回','已作废'].map(status=>{const r=cases.filter(c=>c.status===status),n=summarize(r);return `<tr><td>${status}</td><td>${r.length}</td><td>${n.projects}</td><td>${n.area.toFixed(2)}</td></tr>`;}).join('')}</tbody></table></div></section>`;
    return html;
  }
  if (tab === 'supervision') {
    const visibleIds = new Set(cases.map(c=>c.id));
    return html + notice('流程管理员可从办件详情发起督办；处理完成后登记解除说明。') + table(p.supervisions.filter(r=>visibleIds.has(r.caseId)),[['事项','name'],['督办说明','note'],['状态',r=>tag(r.status)],['发起时间',r=>fmt(r.createdAt)]],r=>`<a class="btn text small" href="#/${v.admin?'admin':'front'}/cases/${r.caseId}">查看事项</a>${r.status==='督办中'&&p.permissions.manageFlows?btn('解除督办','pc-supervise-close',r.id,'text small'):''}`);
  }
  const data = tab === 'todo' ? cases.filter(c=>c.isTodo) : cases;
  return html + table(data,[['事项',c=>`<strong>${esc(c.name)}</strong><small class="pc-cell-sub">${esc(c.category)} · ${esc(c.projectType || '其他项目')} · ${esc(c.projectId)}</small>`],['区域','region'],['当前节点',c=>esc(c.workflow.nodes[c.nodeIndex]?.name)],['状态',c=>tag(c.status)],['合规状态','compliance'],['截止时间',c=>fmt(c.dueAt)]],c=>`<a class="btn text small" href="#/${v.admin?'admin':'front'}/cases/${c.id}">查看 / 办理</a>`);
}

export function personalView({D,esc,btn,tag}) {
  const p=D.platform, modules=p.dashboards[0]?.modules || ['apps','overview','todo','supervision','messages','guides'];
  const visible=key=>modules.includes(key), recent=p.recentApps.slice().reverse().map(r=>p.apps.find(a=>a.id===r.appId)).filter(Boolean);
  const apps=recent.length?recent:p.apps.slice(0,4);
  return `<section class="portal-container pc-personal"><div class="pc-panel-head"><div><span class="portal-kicker">MY WORKSPACE</span><h2>${esc(D.user.name)}的工作空间</h2></div>${btn('配置我的首页','pc-dashboard','','small')}</div><div class="pc-two-column">${visible('apps')?`<section class="panel pc-padding"><h3>我的应用</h3>${apps.map(a=>btn(a.name,'pc-enter',a.id,'pc-guide-link')).join('')}<small class="muted">优先展示最近使用的应用</small></section>`:''}${visible('overview')?`<section class="panel pc-padding"><h3>工作概览</h3>${['业务审批','数字会商'].map(category=>{const n=summarize(p.cases.filter(c=>c.category===category));return `<p>${category}：${n.total} 件 · ${n.todo} 待办 · 完成 ${n.rate}</p>`;}).join('')}<a href="#/front/workbench">进入工作台 →</a></section>`:''}${visible('todo')?`<section class="panel pc-padding"><h3>我的待办</h3>${p.cases.filter(c=>c.isTodo).slice(0,4).map(c=>`<a class="pc-guide-link" href="#/front/cases/${c.id}">${esc(c.name)} ${tag(c.status)}</a>`).join('')||'<p class="muted">暂无待办</p>'}</section>`:''}${visible('supervision')?`<section class="panel pc-padding"><h3>任务督办</h3>${p.supervisions.filter(s=>s.status==='督办中').map(s=>`<a class="pc-guide-link" href="#/front/cases/${s.caseId}">${esc(s.name)}</a>`).join('')||'<p class="muted">暂无待处理督办</p>'}</section>`:''}${visible('messages')?`<section class="panel pc-padding"><h3>最新消息</h3>${['业务审批','数字会商','应用动态'].map(category=>`<details open><summary>${category}</summary>${p.notifications.filter(n=>(n.category||'应用动态')===category).slice(-3).reverse().map(n=>btn(n.title+' · '+n.body,'pc-message',n.id,'pc-guide-link')).join('')||'<p class="muted">暂无消息</p>'}</details>`).join('')}<a href="#/front/messages">全部消息 →</a></section>`:''}${visible('guides')?`<section class="panel pc-padding"><h3>法规与帮助</h3>${D.knowledge.slice(0,3).map(k=>btn(k.name,'portalKnowledge',k.id,'pc-guide-link')).join('')}<a href="#/front/workbench">查看工作台帮助 →</a></section>`:''}</div></section>`;
}

export function imageField(key,label,value='',multiple=false) {
  const images=Array.isArray(value)?value:(typeof value==='string'&&value.startsWith('data:image/')?[value]:[]);
  return `<div class="pc-field full pc-image-field" data-image-key="${key}"><span>${label}（PNG/JPEG/WebP${multiple?'，最多3张':''}）</span><input type="file" aria-label="${label}" accept="image/png,image/jpeg,image/webp" data-image-upload="${key}" ${multiple?'multiple':''}><input type="hidden" name="${key}" value="${encodeURIComponent(JSON.stringify(multiple?images:images[0]||''))}"><div class="pc-image-previews">${images.map(src=>`<img alt="已上传图片" src="${src.replace(/"/g,'&quot;')}">`).join('')}</div><button type="button" class="btn text small" data-action="pc-clear-image" data-id="${key}">移除图片</button><small class="muted">图片自动缩放并压缩后保存到本地原型。</small></div>`;
}

export async function loadImage(file) {
  if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size>8*1024*1024) throw Error('请选择8MB以内的PNG/JPEG/WebP图片');
  const bitmap=await createImageBitmap(file),scale=Math.min(1,800/Math.max(bitmap.width,bitmap.height));
  const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));
  canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
  let result=canvas.toDataURL('image/webp',.8);
  if(result.length>350000)result=canvas.toDataURL('image/jpeg',.55);
  if(result.length>350000)throw Error('压缩后仍过大，请选择尺寸较小的图片');
  return result;
}
