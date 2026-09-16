// Local business illustrations are fallback covers; approved uploads take priority.
export function previewSource(record) {
  const safe = value => typeof value === 'string' && (/^data:image\/(png|jpeg|webp|gif);base64,/i.test(value) || /^\/assets\/[\w/.-]+$/.test(value));
  const uploaded = (Array.isArray(record.screenshots) ? record.screenshots : []).find(safe);
  if (uploaded) return uploaded;
  if (safe(record.cover)) return record.cover;
  if (safe(record.icon)) return record.icon;
  const label = [record.name, record.category, record.type].join(' ');
  const kind = /会商/.test(label) ? 'consult' : /审查|审批|workflow/.test(label) ? 'project' : /知识|政策|规范|文档/.test(label) ? 'knowledge' : /智能|助手|agent/.test(label) ? 'assistant' : /地灾/.test(label) ? 'hazard' : /耕地/.test(label) ? 'cropland' : /图层|scene|地图/.test(label) ? 'map' : 'data';
  return `/assets/previews/${kind}.svg`;
}
document.addEventListener('error', event => {
  const img = event.target;
  if (img instanceof HTMLImageElement && img.hasAttribute('data-preview') && !img.dataset.fallback) {
    img.dataset.fallback = 'true';
    img.src = '/assets/previews/data.svg';
  }
}, true);
