// Shared names and route mapping for the internal integration workspace.
export const integrationNav=[['integration-results','一张图成果','layers'],['integration-resources','数字资源','database'],['integration-workbench','个人工作台','grid'],['integration-settings','集成配置','settings']];
export const settingsGroups=[['portal','门户展示',['presentation','announcements','placement']],['connections','系统接入',['systems','national','vertical','horizontal']],['maintenance','运行维护',['overview','exceptions','monitor']],['access','权限与租户',['access','policy','tenants']]];
export const sectionFor=tab=>settingsGroups.find(g=>g[2].includes(tab))?.[0]||'connections';
export function settingsPath(tab='presentation',values={}){return '/admin/integration-settings?'+new URLSearchParams({section:sectionFor(tab),tab,...values});}
export function legacyIntegration(hash){
  const [path,search='']=hash.replace(/^#/, '').split('?'),p=new URLSearchParams(search);
  const aliases={'/front/integrated-portal':'integration-resources','/front/internal-home':'integration-resources','/front/integrated-workbench':'integration-workbench','/front/integration-results':'integration-results'};
  const safe=Object.fromEntries([...p].filter(([k])=>['tab','filter','system','id','query','kind','theme','department','page','status','source','view','unread','messageKind'].includes(k)));
  if(aliases[path])return '/admin/'+aliases[path]+(Object.keys(safe).length?'?'+new URLSearchParams(safe):'');
  if(path==='/admin/center-integration')return settingsPath(p.get('tab')||'overview',safe);
  return null;
}
