import {assetKinds, assets, assetGraph, references, onlineSnapshot, indexState} from './intelligence-links.js';

export function createIntelligenceAdmin(ctx) {
  const {esc,btn,heading,tag} = ctx;
  const state = () => ctx.state(), data = () => state().D;
  const allowed = route => ctx.allowed().some(n => n[0] === route);
  const url = key => '#/admin/intelligence-links?asset=' + encodeURIComponent(key);
  const link = (key, label) => `<a class="btn text small" href="${url(key)}">${esc(label)}</a>`;
  const version = (kind,row) => {
    const live = onlineSnapshot(kind,row);
    return `${live ? '线上 v'+live.version : '未生效'}${row.status === '草稿' ? ' · 有草稿' : ''}`;
  };
  const ownedLink = (route,label) => allowed(route) ? `<a class="btn small" href="#/admin/${route}">${esc(label)}</a>` : '';
  function impact(entity,id) {
    if (!allowed('intelligence-links')) return '';
    const key = `${entity}:${id}`, graph = assetGraph(data()), result = references(graph,key);
    const evaluation=entity==='agents'?(data().evaluations||[]).filter(r=>r.agentId===id).at(-1):null;
    return `${entity==='agents'?`<p>最近评测：${evaluation?esc(evaluation.at)+' · '+evaluation.passed+'/'+evaluation.total+' 通过（历史结果，变更后请重新评测）':'尚无记录'}</p>`:''}<div class="notice">线上引用：${result.incoming.filter(e=>!e.potential).length} 条明确关联，${result.incoming.filter(e=>e.potential).length} 条动态范围关联，${result.indirect.length} 项间接关联。发布或停用前请核对使用位置。${link(key,'查看关联与影响')}</div>`;
  }
  function renderMetadata() {
    const params = new URLSearchParams(location.hash.split('?')[1]), q = params.get('q') || '';
    const rows = (data().resources || []).filter(r => (!params.get('resourceId') || r.id === params.get('resourceId')) && [r.name,r.source,r.aliases].join(' ').toLowerCase().includes(q.toLowerCase()));
    document.querySelector('#main').innerHTML = heading('元数据标注','复用运营中心的资源记录，维护业务同义词、字段语义与关联依据。保存为资源草稿，发布后供智能检索使用。') +
      `<div class="ia-actions">${ownedLink('resources','资源与技术元数据')}${ownedLink('center-resources','共享目录与交付')}${ownedLink('grants','资源授权台账')}</div><form id="ia-search" class="ia-search"><label>资源名称、来源或同义词<input name="q" value="${esc(q)}" placeholder="搜索待标注资源"></label><button class="btn primary">查询</button><a class="btn" href="#/admin/metadata-annotation">重置</a></form><section class="panel table-panel"><div class="table-scroll"><table><thead><tr><th>资源 / 来源</th><th>业务同义词</th><th>字段语义</th><th>发布状态</th><th>操作</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.name)}<small>${esc(r.source)}</small></td><td>${esc(r.aliases || '待补充')}</td><td>${(r.fields||[]).filter(f=>f.alias || f.description).length} / ${(r.fields||[]).length} 个字段有别名或解释</td><td>${esc(version('resources',r))}</td><td><div class="row-actions">${btn('语义标注','ia-annotate',r.id,'text small')}${btn('字段标注','ia-fields',r.id,'text small')}${r.status==='草稿'?btn('发布资源','publish','resources:'+r.id,'text small'):''}${link('resources:'+r.id,'关联与影响')}</div></td></tr>`).join('') || '<tr><td colspan="5">没有匹配资源，请调整搜索条件。</td></tr>'}</tbody></table></div></section>`;
    document.querySelector('#ia-search').addEventListener('submit',e=>{e.preventDefault();ctx.nav('/admin/metadata-annotation?q='+encodeURIComponent(new FormData(e.target).get('q')));});
  }
  function renderLinks() {
    const params = new URLSearchParams(location.hash.split('?')[1]), mode = params.get('view') === 'draft' ? 'draft' : 'online';
    const graph = assetGraph(data(),mode), key = params.get('asset') || graph.nodes.find(n=>n.kind==='agents')?.key, node = graph.byKey.get(key);
    const choice = `<form id="ia-object" class="ia-search"><label>关联对象<select name="asset">${Object.entries(assetKinds).map(([kind,[label]])=>`<optgroup label="${label}">${graph.nodes.filter(n=>n.kind===kind).map(n=>`<option value="${esc(n.key)}" ${n.key===key?'selected':''}>${esc(n.row.name)} · ${esc(n.row.id)}</option>`).join('')}</optgroup>`).join('')}</select></label><label>分析范围<select name="view"><option value="online" ${mode==='online'?'selected':''}>线上生效版本</option><option value="draft" ${mode==='draft'?'selected':''}>当前编辑配置</option></select></label><button class="btn primary">查看关联</button></form>`;
    let body = '<section class="panel ia-panel">对象不存在或当前身份不可见，请重新选择。</section>';
    if (node) {
      const {kind,row} = node, [label,owner,route] = assetKinds[kind], live = onlineSnapshot(kind,row), ref = references(graph,key);
      const table = (title,edges,incoming=false) => `<section class="panel ia-panel"><h2>${title} <small>${edges.length} 条</small></h2><div class="table-scroll"><table><thead><tr><th>对象 / 所属模块</th><th>关联用途</th><th>当前线上状态</th><th>操作</th></tr></thead><tbody>${edges.map(e=>{
        const targetKey=incoming?e.from:e.to,n=graph.byKey.get(targetKey);
        return `<tr><td>${esc(n?.row.name || targetKey)}<small>${esc(n?assetKinds[n.kind][1]:'对象缺失或不可见')}</small></td><td>${esc(e.label)}</td><td>${n?esc(version(n.kind,n.row)):'无法确认'}</td><td>${n?link(n.key,'查看关联'):''}</td></tr>`;
      }).join('') || '<tr><td colspan="4">此范围没有记录到直接关联。</td></tr>'}</tbody></table></div></section>`;
      body = `<section class="panel ia-panel"><div class="ia-heading"><div><h2>${esc(row.name)}</h2><p>${esc(owner)} · ${esc(label)} · ${esc(row.id)}</p></div>${tag(live?'线上 v'+live.version:'未生效')}</div><p>当前编辑状态：${esc(row.status||'—')}。${mode==='online'?'下方按线上快照分析；尚未发布的修改不计入。':'下方按当前编辑配置分析，不代表已经上线。'}</p><div class="ia-actions">${ownedLink(route,'进入'+owner+'管理')}${allowed(route)?btn(kind==='apps'?'查看应用详情':'编辑当前对象','ia-edit',key,'small'):''}${kind==='agents'?btn('评测此智能体','ia-evaluate',row.id,'small primary'):''}${kind==='resources'?ownedLink('grants','查看授权台账')+ownedLink('center-resources','共享目录与交付'):''}${kind==='knowledge'?ownedLink('articles','门户资讯发布'):''}${kind==='agents'?ownedLink('center-integration','综合集成入口配置')+ownedLink('identity','用户组织与权限'):''}</div>${kind==='knowledge'?`<p>AI 检索：${live?'v'+live.version:'未纳入'}；门户发布：${onlineSnapshot(kind,row,'portal')?'v'+onlineSnapshot(kind,row,'portal').version:'未发布'}。${indexState(row).pending?'原文有更新，知识索引待核对。':'两个渠道分别发布。'}</p>`:''}${kind==='agents'?'<p>智能体发布与应用上架分别管理；关联工具资源用于发现和授权，不代表已接通工具执行接口。综合集成汇聚已发布且用户可见的智能体。</p>':''}${graph.scopes.filter(s=>s.from===key).map(s=>`<p class="notice">${esc(s.label)}</p>`).join('')}</section>`+
        table('使用的对象',ref.outgoing)+table('被哪些对象引用',ref.incoming,true)+
        `<section class="panel ia-panel"><h2>间接关联 <small>${ref.indirect.length} 项</small></h2><p class="muted">用于核对变更影响；配置引用不等于已发生调用，实际执行还取决于用户权限、运行路径和应用绑定版本。</p>${ref.indirect.map(r=>`<div class="ia-path">${r.path.map(k=>link(k,graph.byKey.get(k)?.row.name||k)).join('<span>→</span>')}${r.potential?'<small>含动态范围</small>':''}</div>`).join('')||'<p>没有记录到间接关联。</p>'}</section>`;
    }
    document.querySelector('#main').innerHTML=heading('关联与影响','查看资源、知识、指标、智能体、工具和应用之间的配置关系，核对各模块的生效版本。')+choice+body;
    document.querySelector('#ia-object').addEventListener('submit',e=>{e.preventDefault();ctx.nav('/admin/intelligence-links?'+new URLSearchParams(new FormData(e.target)));});
  }
  function renderEvaluations() {
    document.querySelector('#main').innerHTML=heading('评测与回归','比较线上资产与当前草稿资产的回答、资源和执行步骤。评测结果供发布核对，不会自动发布。',btn('新建评测','ia-evaluate','','primary'))+
      '<p class="notice">当前对比范围包含关联资产的草稿变化，并非只比较智能体本身。结果属于本地规则评测。</p>'+
      `<section class="panel table-panel"><div class="table-scroll"><table><thead><tr><th>智能体</th><th>时间</th><th>通过 / 总数</th><th>比较范围</th><th>操作</th></tr></thead><tbody>${(data().evaluations||[]).slice().reverse().map(r=>`<tr><td>${esc(r.agent)}</td><td>${esc(r.at)}</td><td>${r.passed} / ${r.total}</td><td>${esc(r.scope)}</td><td>${btn('查看报告','evaluationResult',r.id,'text small')}${link('agents:'+r.agentId,'关联资产')}</td></tr>`).join('')||'<tr><td colspan="5">暂无评测，选择智能体开始。</td></tr>'}</tbody></table></div></section>`;
  }
  return {
    impact,
    render() {
      const route=state().route;
      if(route==='metadata-annotation')renderMetadata();
      else if(route==='intelligence-links')renderLinks();
      else if(route==='intelligence-evaluations')renderEvaluations();
      else return false;
      return true;
    },
    async action(action,id) {
      if(!action.startsWith('ia-'))return false;
      if(!allowed('intelligence-links'))return true;
      if(action==='ia-annotate'||action==='ia-fields') {ctx.edit('resources',id);ctx.resourceTab(action==='ia-fields'?'metadata':'semantic');}
      if(action==='ia-edit'){const [kind,key]=id.split(':');if(assetKinds[kind]&&allowed(assetKinds[kind][2])){if(kind==='apps')await ctx.perform('pc-review',key);else if(['scenes','models','workflows'].includes(kind))await ctx.perform('pc-edit',id);else if(kind==='tools')await ctx.perform('pm-edit','tools:'+key);else ctx.edit(kind,key);}}
      if(action==='ia-evaluate')ctx.evaluate(id || undefined);
      return true;
    }
  };
}
