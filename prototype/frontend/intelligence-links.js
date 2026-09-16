// Read-only dependency analysis. Draft references and online references never mix.
export const assetKinds = {
  agents: ['智能体', '智能中心', 'agents'],
  resources: ['资源', '运营中心', 'resources'],
  knowledge: ['知识文档', '智能中心', 'knowledge'],
  indicators: ['指标', '智能中心', 'indicators'],
  corpora: ['语料', '智能中心', 'corpora'],
  templates: ['元数据模板', '运营中心', 'resources'],
  dictionaries: ['枚举字典', '运营中心', 'resources'],
  apps: ['应用', '应用中心', 'app-registry'],
  scenes: ['地图场景', '应用中心', 'scene-templates'],
  models: ['业务事项', '应用中心', 'business-models'],
  workflows: ['业务流程', '应用中心', 'workflows'],
  tools: ['门户工具', '工具中心', 'portal-tools'],
};
export const ids = value => Array.isArray(value) ? value : String(value || '').split(',').map(x => x.trim()).filter(Boolean);
export function assets(data) {
  return Object.entries(assetKinds).flatMap(([kind]) => {
    const rows = kind === 'tools' ? data.portalManagement?.tools : ['apps','scenes','models','workflows'].includes(kind) ? data.platform?.[kind] : data[kind];
    return (rows || []).map(row => ({key: `${kind}:${row.id}`, kind, row}));
  });
}
export function onlineSnapshot(kind, row, channel = 'index') {
  if (kind === 'knowledge' && row.channels != null) return row.channels[channel] || null;
  if (kind === 'apps') return row.listed ? row.published || null : null;
  if (row.status === '已停用' || row.suspended) return null;
  return row.published || null;
}
export function assetGraph(data, mode = 'online') {
  const nodes = assets(data), byKey = new Map(nodes.map(n => [n.key, n])), edges = [], scopes = [];
  for (const node of nodes) {
    const row = mode === 'draft' ? node.row : onlineSnapshot(node.kind, node.row);
    if (!row) continue;
    const add = (kind, id, label, potential = false) => {
      if (!id) return;
      const edge = {from: node.key, to: `${kind}:${id}`, label, potential};
      if (!edges.some(e => e.from === edge.from && e.to === edge.to && e.label === label)) edges.push(edge);
    };
    const many = (kind, value, label) => ids(value).forEach(id => add(kind, id, label));
    if (node.kind === 'agents') {
      const steps = String(row.steps || '').split('\n');
      const bindings = [
        ['resources', 'resourceIds', '资源检索范围', steps.includes('检索资源')],
        ['knowledge', 'knowledgeIds', '知识检索范围', steps.includes('检索知识')],
        ['indicators', 'indicatorIds', '指标计算范围', steps.includes('示例试算')],
        ['corpora', 'templateIds', '语料范围', true],
      ];
      for (const [kind, field, label, used] of bindings) {
        const selected = ids(row[field]);
        if (selected.length) many(kind, selected, label + (used ? '' : '（已配置，当前无直接执行节点）'));
        else {
          scopes.push({from: node.key, kind, label: `${label}：全部已发布且调用用户有权访问的资产${used ? '' : '；当前无直接执行节点'}`});
          if (used) nodes.filter(n => n.kind === kind && onlineSnapshot(kind, n.row)).forEach(n => add(kind, n.row.id, `${label}（动态范围，实际由用户权限与查询决定）`, true));
        }
      }
      if (steps.includes('调用知识智能体')) add('agents', row.knowledgeAgentId || 'a2', '协作调用');
      if (steps.includes('调用指标智能体')) add('agents', row.indicatorAgentId || 'a3', '协作调用');
      if (row.mapEnabled) { add('scenes', row.mapSceneId, '地图能力'); many('resources', row.mapResourceIds, '地图图层'); }
    }
    if (node.kind === 'resources') {
      add('knowledge', row.documentId, '语义依据');
      add('templates', row.templateId, '元数据模板');
      many('resources', row.relations, '资源关联');
      for (const line of String(row.relationRules || '').split('\n')) { const [label, id] = line.split('|'); add('resources', id?.trim(), label || '关系规则'); }
      for (const field of row.fields || []) {
        const dict = nodes.find(n => n.kind === 'dictionaries' && [n.row.id,n.row.code,n.row.name].includes(field.dictionary));
        if (field.dictionary) add('dictionaries', dict?.row.id || field.dictionary, '字段枚举');
      }
    }
    if (node.kind === 'indicators') {
      if (row.dataMode !== 'composite') add('resources', row.resourceId, row.dataMode === 'table' ? '计算数据源' : '手动试算关联库表（用于授权与字段校验）');
      if (row.dataMode === 'composite') for (const id of String(row.expression || '').match(/[A-Za-z_][A-Za-z_0-9]*/g) || []) add('indicators', id, '复合计算依赖');
      many('knowledge', row.knowledgeIds, '指标口径依据');
    }
    if (node.kind === 'corpora') { many('resources', row.resourceIds, '语料业务来源'); add('agents', row.agentId, '适用评测对象'); }
    if (node.kind === 'agents') nodes.filter(n=>n.kind==='corpora').forEach(n=>{
      const sample=mode==='draft'?n.row:onlineSnapshot('corpora',n.row);
      if(sample?.sourceAgent===row.id)add('corpora',sample.id,'反馈改进样例');
    });
    if (node.kind === 'tools') add('resources', row.resourceId, '内部工具授权关联（不代表智能体已调用）');
    if (node.kind === 'apps') {
      add(({agent:'agents',scene:'scenes',workflow:'models'})[row.type], row.type === 'external' ? '' : row.targetId, row.type==='scene'?'场景来源（运行配置以应用绑定快照为准）':'应用入口');
      if(row.type==='scene'&&row.targetSnapshot){
        for(const layer of row.targetSnapshot.config?.layers||[])add('resources',layer.resourceId,'应用绑定快照图层');
        for(const widget of row.targetSnapshot.config?.widgets||[])add('agents',widget.params?.agentId,'应用绑定快照智能辅助');
      }
    }
    if (node.kind === 'scenes') {
      for (const layer of row.config?.layers || []) add('resources', layer.resourceId, '场景图层');
      for (const widget of row.config?.widgets || []) add('agents', widget.params?.agentId, '智能辅助控件');
    }
    if (node.kind === 'models') add('workflows', row.workflowId, '事项办理流程');
    if (node.kind === 'workflows') many('knowledge', row.knowledgeIds, '流程知识依据');
  }
  return {nodes, byKey, edges, scopes};
}
export function references(graph, key) {
  const outgoing = graph.edges.filter(e => e.from === key), incoming = graph.edges.filter(e => e.to === key);
  const seen = new Set([key, ...incoming.map(e => e.from)]), queue = incoming.map(e => ({key:e.from,path:[e.from,key],potential:e.potential})), indirect = [];
  while (queue.length) {
    const current = queue.shift();
    for (const edge of graph.edges.filter(e => e.to === current.key)) {
      if (seen.has(edge.from)) continue;
      seen.add(edge.from);
      const entry = {key:edge.from,path:[edge.from,...current.path],potential:current.potential || edge.potential};
      indirect.push(entry); queue.push(entry);
    }
  }
  return {outgoing,incoming,indirect};
}
export function indexState(row) {
  const snapshot = onlineSnapshot('knowledge', row);
  return {snapshot, enabled:!!snapshot, pending:!!snapshot && (row.status === '草稿' || snapshot.version !== row.version)};
}
