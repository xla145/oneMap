import {createBootstrapCache} from './frontend/bootstrap-cache.js?v=20260917-1';
import {createOperationsCenter,operationMenu,operationLabels,operationSection} from './frontend/operations-center.js?v=20260917-config1';
import {integrationNav,legacyIntegration} from './frontend/integration-routes.js';
import {createIntelligenceAdmin} from './frontend/intelligence-admin.js?v=20260916-ops5';
import {indexState} from './frontend/intelligence-links.js';
import {integrationSections} from './frontend/integration-admin.js?v=20260916-results-round2-final';
import { createIntegration } from './frontend/integration.js?v=20260917-gis-tab-1';
import { createCenters } from './frontend/centers.js?v=20260916-centers';
import { createPortalOperations } from './frontend/portal-operations.js';
import { createPortalAdmin } from './frontend/portal-admin.js?v=20260916-intelligence-links';
import { createPublicPortal } from './frontend/public-portal.js?v=20260917-tool-entry2';
import { renderNews, newsCategory, newsCategories, searchNews, recommendedNews, newsDownloadText } from './frontend/news.js?v=20260915-1';
import { previewSource } from './frontend/previews.js';
import { randomUUID } from './frontend/uuid.js';
import { createPlatform } from './frontend/platform.js?v=20260916-workspace-apps-r2';
const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const paths = {
  sparkles:
    "m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3M20 2v4m-2-2h4",
  home: "m3 10 9-7 9 7v10H3V10m6 10v-7h6v7",
  grid: "M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z",
  database:
    "M20 6c0 2-3.6 3-8 3S4 8 4 6s3.6-3 8-3 8 1 8 3ZM4 6v12c0 4 16 4 16 0V6M4 12c0 4 16 4 16 0",
  layers: "m12 3 10 6-10 6L2 9l10-6m-10 12 10 6 10-6M2 15l10 6 10-6",
  tool: "m14 5 5 5m-9 0L3 17l4 4 7-7M14 3a7 7 0 0 0-4 11 7 7 0 0 0 11-4l-5 2-4-4 2-5",
  book: "M12 5C9 2 4 3 2 4v16c4-2 7-2 10 0m0-15c3-3 8-2 10-1v16c-4-2-7-2-10 0V5",
  chart: "M4 3v18h18M8 16v-4m5 4V7m5 9v-7",
  file: "M5 3h9l5 5v13H5V3m9 0v6h5M8 13h8m-8 4h6",
  user: "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2",
  search: "M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0Zm-2 4 7 7",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  up: "M12 19V5m-6 6 6-6 6 6",
  chevron: "m9 5 7 7-7 7",
  plus: "M12 4v16M4 12h16",
  check: "m5 12 4 4L19 6",
  x: "m6 6 12 12M6 18 18 6",
  clock: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v5l3 2",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-6v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
  shield: "m12 2 9 4v6c0 6-9 10-9 10S3 18 3 12V6l9-4m-4 10 3 3 5-6",
  message: "M3 3h18v14H8l-5 4V3m4 5h10M7 12h7",
  bell: "M5 17h14l-2-4V8a5 5 0 0 0-10 0v5l-2 4m5 3h4",
  refresh: "M20 7a9 9 0 1 0 1 9M20 2v6h-6",
  logout: "M10 3H3v18h7m-2-9h13m-5-5 5 5-5 5",
  menu: "M3 6h18M3 12h18M3 18h18",
  copy: "M8 8h13v13H8V8M4 16H2V2h14v2",
  edit: "m15 3 6 6L9 21H3v-6L15 3m-3 3 6 6",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7",
  download: "M12 3v12m-5-5 5 5 5-5M3 16v5h18v-5",
  link: "m9 15 6-6m-6-4 2-2a5 5 0 0 1 7 7l-2 2m-8 0-2 2a5 5 0 0 0 7 7l2-2",
  brain:
    "M12 3v18M12 5C5-2 0 10 5 12c-5 7 5 12 7 6m0-13c7-7 12 5 7 7 5 7-5 12-7 6M5 12h3m8 0h3",
  code: "m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18",
  filter: "M3 4h18l-7 8v8l-4-2v-6L3 4",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
  leaf: "M20 3C8 1 0 10 7 17S23 14 20 3ZM4 21 16 9",
  stop: "M6 6h12v12H6z",
};
const icon = (name = "grid", cls = "") =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.grid}"/></svg>`;
const btn = (label, action, id = "", style = "", ico = "") =>
  `<button type="button" class="btn ${style}" data-action="${action}" data-id="${esc(id)}">${ico ? icon(ico) : ""}${label}</button>`;
const tag = (s) =>
  `<span class="tag ${["已授权", "已通过", "已发布", "可用", "已处理", "完成"].includes(s) ? "success" : ["已驳回", "已停用", "失败"].includes(s) ? "danger" : ["待审核", "申请中", "待处理", "草稿", "待改进", "部分通过"].includes(s) ? "warm" : ""}">${esc(s)}</span>`;
const fmt = (v) =>
  v
    ? new Date(v).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "—";
const typeIcon = (t) =>
  ({
    数据库表: "database",
    图层服务: "layers",
    工具服务: "tool",
    知识文档: "book",
  })[t] || "file";
const empty = (
  text = "暂无符合条件的记录",
  sub = "试试调整筛选条件，或新增一条记录。",
) =>
  `<div class="empty">${icon("search")}<h3>${esc(text)}</h3><p>${esc(sub)}</p></div>`;
const opts = (values, current) =>
  values
    .map(
      (v) =>
        `<option value="${esc(Array.isArray(v) ? v[0] : v)}" ${(Array.isArray(v) ? v[0] : v) === current ? "selected" : ""}>${esc(Array.isArray(v) ? v[1] : v)}</option>`,
    )
    .join("");
const csvIds = (v) =>
  String(v || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
let D,
  route,
  routeId = "",
  businessContext = null,
  mode = "front",
  userId = "u1",
  query = "",
  filter = "全部",
  page = 1,
  sessionId = "",
  selectedAgent = "a1",
  cart = [],
  pending = null,
  busy = false,
  toastTimer,
  modalFocus,
  adminTab = "";
let requestKey = randomUUID();
const platformUI = createPlatform({navigateEmbedded:path=>route==='integration-results'&&integrationUI.navigateApplication(path),
  $, esc, icon, btn, tag, fmt, modal, closeModal, toast, api, nav, empty,
  state: () => ({D, mode, route, id: routeId}),
  render: () => renderPage(),
  loadOnly: () => load(),
  reload: async () => {await load();renderPage();},
  landscape: () => portalLandscape(),
  agentCard: a => agentCard(a),
  identity: (id,resultPermissions={}) => {
    pending?.controller.abort();pending=null;
    bootstrapCache.invalidate();
    sessionStorage.setItem('onemap-user',id);
    sessionStorage.setItem('intelligence-front',id);
    sessionStorage.setItem('intelligence-admin',id);
    sessionId='';cart=[];businessContext=null;
    const account=D.accounts.find(u=>u.id===id);
    if(mode==='admin' && account?.role==='业务用户'){const target=resultPermissions.internalAccess?'/admin/integration-workbench':resultPermissions.view?'/admin/integration-results':'/front/home';if(location.hash==='#'+target)routeChange();else nav(target);}
    else routeChange();
  },
  launch: async (question, context={}, agent='a1') => {
    if(route==='integration-results'&&integrationUI.launchInWorkspace(agent,context,question))return;
    pending?.controller.abort();pending=null;
    businessContext=Object.keys(context).length?context:null;
    selectedAgent=agent;sessionId='';resumeFrom='';closeModal();
    nav('/front/assistant');
    for(let i=0;i<80;i++){if(route==='assistant' && document.querySelector('#chat-form'))break;await new Promise(r=>setTimeout(r,50));}
    if(question)await sendQuestion(question);
  },
});

const operationsCenterUI = createOperationsCenter({$,esc,btn,tag,api,modal,closeModal,toast,state:()=>({D,mode,route}),load:()=>load(),reload:async()=>{await load();renderPage();}});
const operationsUI = createPortalOperations({$,esc,icon,btn,tag,api,modal,closeModal,toast,state:()=>({D,mode,route}),loadOnly:()=>load(),reload:async()=>{await load();renderPage();}});
const managementUI = createPortalAdmin({$,esc,icon,btn,tag,api,nav,modal,closeModal,toast,state:()=>({D,mode,route,id:routeId}),reload:async()=>{await load();renderPage();}});
const integrationUI = createIntegration({renderApplicationCase:(host,id)=>platformUI.renderCase(host,id),$,esc,icon,btn,tag,api,nav,canAdminRoute:key=>permittedAdminNav().some(n=>n[0]===key),modal,closeModal,toast,perform:(a,id)=>perform(a,id),loadOnly:()=>load(),state:()=>({D,mode,route,id:routeId}),reload:async()=>{await load();renderPage();}});
const centersUI = createCenters({$,esc,icon,btn,tag,api,nav,modal,closeModal,toast,state:()=>({D,mode,route,id:routeId}),reload:async()=>{await load();renderPage();}});
const intelligenceUI = createIntelligenceAdmin({esc,btn,heading,tag,nav,state:()=>({D,mode,route}),allowed:()=>permittedAdminNav(),perform:(a,id)=>perform(a,id),edit:editor,evaluate:evaluationsDialog,resourceTab:id=>designAction('design-tab',id)});
const publicUI = createPublicPortal({$,esc,icon,btn,tag,api,nav,modal,closeModal,toast, state:()=>({D,mode,route,id:routeId}), cart:()=>cart, landscape:()=>portalLandscape(), loadOnly:()=>load(), reload:async()=>{await load();renderPage();}});

const frontNav = [
  ["home", "首页", "home"],
  ["assistant", "资源检索助手", "sparkles"],
  ["agents", "智能体广场", "grid"],
  ["catalog", "资源中心", "database"],
  ["applications", "我的申请", "file"],
  ["profile", "个人中心", "user"],
];
const adminNav = [
  ...integrationNav,
  ["operations","运营中心","layers"],
  ["center-resources","共享目录与交付","database"],
  ["center-tools","工具台账与审核","tool"],
  ["center-operations","数据治理工作区","layers"],
  ["overview", "管理工作台", "home"],
  ["grants", "授权台账", "shield"],
  ["articles", "资讯发布", "book"],
  ["public-portal", "公共门户运营", "home"],
  ["portal-tools", "能力服务管理", "tool"],
  ["portal-keys", "API 密钥审核", "code"],
  ["portal-roles", "门户角色分配", "user"],
  ["portal-security", "安全配置", "shield"],
  ["portal-monitor", "系统监控", "chart"],
  ["portal-materials", "下载资料管理", "file"],
  ["portal-users", "注册申请审核", "user"],
  ["portal-analytics", "门户统计分析", "chart"],
  ["portal-audit", "统一日志审计", "shield"],
  ["app-registry", "应用注册与运营", "grid"],
  ["scene-templates", "场景构建", "layers"],
  ["widgets", "控件与分组", "tool"],
  ["business-models", "业务体系与事项", "file"],
  ["workflows", "流程与表单", "link"],
  ["cases", "办件台账", "file"],
  ["business-assets", "业务配置资源", "settings"],
  ["agents", "智能体管理", "grid"],
  ["metadata-annotation", "元数据标注", "database"],
  ["intelligence-links", "关联与影响", "link"],
  ["intelligence-evaluations", "评测与回归", "chart"],
  ["resources", "资源与元数据", "database"],
  ["indicators", "指标知识管理", "chart"],
  ["knowledge", "AI 知识库", "book"],
  ["corpora", "语料管理", "code"],
  ["memories", "用户记忆管理", "brain"],
  ["calls", "调用与反馈", "message"],
  ["approvals", "资源使用审核", "file"],
  ["quality", "元数据完整性检查", "shield"],
  ["identity", "用户组织与权限", "user"],
  ["auth-clients", "统一登录接入", "link"],
  ["gateway", "服务网关", "code"],
  ["message-bus", "消息总线", "bell"],
  ["settings", "日志与演示设置", "settings"],
];
const meta = {
  resources: [
    "资源与元数据",
    "维护资源语义，让每一份数据都能被理解。",
    "database",
  ],
  indicators: [
    "指标知识管理",
    "统一业务定义与计算口径，让每个数字都有依据。",
    "chart",
  ],
  knowledge: ["资讯与知识管理", "维护政策法规、行业动态、技术标准和培训资源，发布后同步资讯中心与知识检索。", "book"],
  corpora: ["语料管理", "沉淀高质量样例，持续优化智能对话体验。", "code"],
  agents: [
    "智能体管理",
    "连接资源、知识与工具，编排可复用的智能能力。",
    "grid",
  ],
  templates: ["元数据模板", "统一资源描述结构与字段要求。", "file"],
  dictionaries: ["枚举字典", "维护编码、名称与业务别名。", "book"],
};
const bootstrapCache = createBootstrapCache();
// These reads/telemetry do not change the bootstrap business snapshot.
const bootstrapReads = new Set(['portal.visit', 'integration.results.map.runtime',
  'integration.map.query', 'integration.results.stats', 'mapRuntime', 'public.map',
  'platform.sceneRuntime', 'integration.preview', 'integration.search',
  'integration.inspect', 'integration.monitor', 'integration.versions',
  'integration.workbench', 'portal.monitor', 'portal.report', 'portal.securityGet',
  'analysis.catalog', 'analysis.get', 'analysis.list', 'integration.ai.history',
  'integration.ai.result']);
async function api(action, payload = {}, signal) {
  if (!action) return getBootstrap(true);
  const invalidates = !bootstrapReads.has(action);
  if (invalidates) bootstrapCache.invalidate();
  try { return await requestAPI(action, payload, signal); }
  finally { if (invalidates) bootstrapCache.invalidate(); }
}
function getBootstrap(force = false) {
  const identity = {userId, mode};
  return bootstrapCache.get(JSON.stringify(identity),
    () => requestAPI(null, {}, undefined, identity), {force});
}
async function requestAPI(action, payload = {}, signal, identity = {userId, mode}) {
  const r = await fetch(action ? "/api/action" : "/api/bootstrap", {
    method: action ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User": identity.userId,
      "X-Demo-Mode": identity.mode,
    },
    body: action ? JSON.stringify({ action, payload }) : undefined,
    signal,
  });
  const data = await r.json();
  if (!r.ok) throw Error(data.error || "连接失败");
  return data;
}
function toast(text) {
  $("#toast").textContent = text;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 4000);
}
async function load(force = true) {
  const owner = userId, scope = mode, version = routeVersion;
  const fresh = await getBootstrap(force);
  if (owner !== userId || scope !== mode || version !== routeVersion) return;
  D = fresh;
  cart = cart.filter((id) =>
    D.resources.some((r) => r.id === id && r.access === "可申请"),
  );
}
function nav(target) {
  location.hash = target;
}
function heading(title, description, actions = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${mode === "front" ? "INTELLIGENCE CENTER" : "MANAGEMENT CONSOLE"}</div><h1>${title}</h1><p>${description}</p></div><div class="actions">${actions}</div></div>`;
}
function stats(items) {
  return `<div class="stats">${items.map(([label, value, sub, ico, target]) => `<button class="stat" data-action="navigate" data-id="${target}"><div><span>${label}</span><strong>${value}<small> ${sub}</small></strong></div><div class="stat-icon">${icon(ico)}</div></button>`).join("")}</div>`;
}
function adminLinkAttributes(key){
  return key==='integration-results'
    ? 'href="/gis/index.html" target="_blank" rel="noopener noreferrer"'
    : `href="#/admin/${key}"`;
}
function adminMenu(navs){
  let saved={};try{saved=JSON.parse(localStorage.getItem('onemap-admin-menu')||'{}');}catch{}
  const current=route==='operations'?operationSection(location.hash.split('?')[0].split('/').slice(3,5).join('/')):['public-portal','center-integration'].includes(route)?route+'?tab='+(new URLSearchParams(location.hash.split('?')[1]).get('tab')||(route==='public-portal'?'topics':'overview')):route;
  const groups=[
    ['integration','综合集成','grid',integrationNav.map(n=>n[0])],
    ['resources','资源中心','database',['center-resources','approvals','grants']],
    ['operations','运营中心','layers',operationMenu],
    ['tools','工具中心','tool',['center-tools','portal-tools','portal-keys']],
    ['apps','应用中心','grid',['app-registry','scene-templates','widgets','business-models','workflows','cases','business-assets']],
    ['intelligence','智能中心','sparkles',['agents','metadata-annotation','knowledge','indicators','corpora','intelligence-evaluations','memories','calls','intelligence-links']],
    ['portal','门户运营','home',['public-portal?tab=settings','articles','portal-materials','public-portal?tab=services','public-portal?tab=tickets','public-portal?tab=topics','portal-users','portal-analytics']],
    ['system','平台管理','settings',['identity','portal-roles','gateway','portal-security','settings']]
  ];
  const labels={...operationLabels,...Object.fromEntries(integrationSections.map(([key,label])=>['center-integration?tab='+key,label])),'public-portal?tab=settings':'公众门户首页配置','public-portal?tab=services':'办事服务管理','public-portal?tab=tickets':'咨询与公众意见','public-portal?tab=topics':'大美内蒙古专题','resources':'资源与元数据','settings':'基础与演示设置'};
  const item=key=>{const n=navs.find(n=>n[0]===key.split('?')[0].split('/')[0]);return n?`<a ${adminLinkAttributes(key)} class="${current===key?'active':''}" aria-label="${esc(labels[key]||n[1])}" title="${esc(labels[key]||n[1])}" ${current===key?'aria-current="page"':''}>${icon(n[2])}<span>${esc(labels[key]||n[1])}${key==='portal-monitor'&&D.portalManagement?.activeAlerts?' · '+D.portalManagement.activeAlerts+' 项告警':''}</span></a>`:'';};
  const last=sessionStorage.getItem('onemap-admin-menu-route');sessionStorage.setItem('onemap-admin-menu-route',current);
  const containsCurrent=items=>items.some(entry=>Array.isArray(entry)?containsCurrent(entry[3]):entry===current);
  const group=([key,name,i,items])=>{
    const links=items.map(entry=>Array.isArray(entry)?group(entry):item(entry)).join('');
    if(!links)return '';
    const active=containsCurrent(items),open=(active&&last!==current)||saved[key]===true||(saved[key]===undefined&&(active||(['portal','data'].includes(key)&&route==='overview')));
    return `<details class="admin-nav-group ${active?'contains-active':''}" data-menu-group="${key}" ${open?'open':''}><summary aria-label="${esc(name)}" title="${esc(name)}">${icon(i)}<span>${name}</span><span class="nav-caret">${icon('chevron')}</span></summary><div class="admin-submenu">${links}</div></details>`;
  };
  return item('overview')+groups.map(group).join('');
}
document.addEventListener('click',e=>{
  const summary=e.target.closest?.('.admin-nav-group > summary');
  if(summary)summary.parentElement.dataset.userToggle='1';
},true);
document.addEventListener('toggle',e=>{
  const group=e.target;if(!group.matches?.('[data-menu-group]')||!group.isConnected||group.dataset.userToggle!=='1')return;
  delete group.dataset.userToggle;
  try{const saved=JSON.parse(localStorage.getItem('onemap-admin-menu')||'{}');saved[group.dataset.menuGroup]=group.open;localStorage.setItem('onemap-admin-menu',JSON.stringify(saved));}catch{}
},true);
function shell() {
  document.body.classList.toggle("portal-mode", mode === "front");
  document.body.classList.toggle("admin-mode", mode !== "front");
  document.body.classList.remove("portal-menu-open");
  if (mode === "front") return portalShell();
  const navs = mode === 'admin' ? permittedAdminNav() : frontNav;
  const integrationTitle=route==='center-integration'?integrationSections.find(([key])=>key===(new URLSearchParams(location.hash.split('?')[1]).get('tab')||'overview'))?.[1]:'';
  const title = integrationTitle || navs.find((n) => n[0] === route)?.[1] || ({"template-preview":"地图模板预览","scenes":"场景预览","cases":"办件详情","workbench":"业务工作台"})[route] || "一张图服务平台";
  $("#app").innerHTML =
    `<aside class="sidebar"><a class="brand" href="#/${mode}/${mode === "admin" ? "overview" : "home"}"><span class="brand-symbol">${icon("leaf")}</span><span>一张图<small>一张图服务平台 ONE MAP</small></span></a><div class="workspace-label">${mode === "front" ? "业务工作空间" : "平台管理空间"}<span>DEMO</span></div><nav aria-label="主导航">${adminMenu(navs)}</nav><div class="sidebar-bottom"><div class="mini-card">${icon("shield")}<div>让知识连接业务<small>让智能服务自然资源</small></div></div><button class="mode-switch" data-action="switchMode">${icon(mode === "front" ? "settings" : "logout")}<span>${mode === "front" ? "后台管理平台" : "返回门户首页"}</span>${icon("arrow")}</button><div class="sidebar-foot"><span class="online-dot"></span>本地演示服务已连接 <span>V1.0</span></div></div></aside><div class="workspace"><header class="topbar"><div class="breadcrumb"><button class="icon-btn mobile-menu" aria-label="展开导航" data-action="menu">${icon("menu")}</button><span>内蒙古自治区</span><i>/</i><strong>${title}</strong></div><div class="top-tools"><span class="demo-badge"><span></span>演示环境</span><button class="icon-btn" data-action="refresh" title="刷新数据" aria-label="刷新数据">${icon("refresh")}</button><button class="icon-btn" data-action="notifications" title="查看申请动态" aria-label="查看申请动态">${icon("bell")}</button><button class="identity" data-action="identity"><span class="avatar">${esc(D.user.name[0])}</span><span>${esc(D.user.name)}<small>${esc(D.user.department)}</small></span>${icon("chevron")}</button></div></header><main id="main"></main><footer class="footer">自然资源一张图管理平台 <span>·</span> 连接数据与知识，释放业务价值 <span class="right">示例数据 · 仅用于原型演示</span></footer></div>`;
  renderPage();
}
function searchbox(placeholder) {
  return `<div class="search-control">${icon("search")}<input id="list-search" aria-label="搜索列表" placeholder="${placeholder}" value="${esc(query)}"></div>`;
}
function toolbar(types, extra = "") {
  return `<div class="toolbar">${searchbox("搜索名称、业务分类或关键词")}<select id="list-filter" aria-label="筛选类型">${opts(types, filter)}</select>${extra}<span class="toolbar-tip">${icon("filter")}筛选</span></div>`;
}
function filtered(rows) {
  return rows.filter(
    (r) =>
      (filter === "全部" || [r.type, r.category, r.status].includes(filter)) &&
      (!query || JSON.stringify(r).toLowerCase().includes(query.toLowerCase())),
  );
}
function pagination(rows) {
  let total = Math.max(1, Math.ceil(rows.length / 8));
  page = Math.min(page, total);
  return `<div class="pagination"><span>共 ${rows.length} 条记录</span><div>${btn("上一页", "prev", "", "small")}<span>${page} / ${total}</span>${btn("下一页", "next", String(total), "small")}</div></div>`;
}
function resourceCard(r) {
  return `<article class="resource-card"><button class="portal-resource-cover" data-action="resource" data-id="${esc(r.id)}" aria-label="查看${esc(r.name)}"><img data-preview src="${esc(previewSource(r))}" alt="${esc(r.name)}业务预览" loading="lazy" decoding="async"></button><div class="card-top"><span class="tile ${r.type === "图层服务" ? "blue" : r.type === "工具服务" ? "purple" : r.type === "知识文档" ? "gold" : ""}">${icon(typeIcon(r.type))}</span>${tag(r.access)}</div><h3><button class="text-button" data-action="resource" data-id="${r.id}">${esc(r.name)}</button></h3><p>${esc(r.description)}</p><div class="chips"><span>${esc(r.type)}</span><span>${esc(r.region)}</span></div><div class="card-foot"><span>${icon("clock")}${esc(r.frequency)}更新</span><button class="icon-btn" aria-label="查看${esc(r.name)}" data-action="resource" data-id="${r.id}">${icon("arrow")}</button></div></article>`;
}
function agentCard(a) {
  return `<article class="agent-card"><div class="portal-agent-cover"><img data-preview src="${esc(previewSource({...a,type:"agent"}))}" alt="${esc(a.name)}业务示意" loading="lazy" decoding="async"></div><div class="card-top"><span class="tile ${esc(a.color)}">${icon(a.icon || "sparkles")}</span><span class="mini-label">${esc(a.category)}</span></div><h3>${esc(a.name)}</h3><p>${esc(a.description)}</p><div class="agent-meta"><span class="online-dot"></span>已发布 <span>v${a.version}.0</span></div><div class="agent-card-bottom">${btn("了解能力", "agentDetail", a.id, "text")}${btn("立即使用", "useAgent", a.id, "small", "arrow")}</div></article>`;
}
function renderHome() { renderPortalHome(); }
function renderCatalog() {
  const rows = filtered(D.resources);
  $("#main").innerHTML =
    heading(
      "资源中心",
      "发现库表、图层、工具与知识，找到业务所需的每一份资源。",
      btn(
        `申请清单 <span class="count">${cart.length}</span>`,
        "cart",
        "",
        "primary",
        "file",
      ),
    ) +
    toolbar(["全部", ...["数据库表", "图层服务", "工具服务", "知识文档"]]) +
    `<div class="result-summary">可发现资源 <strong>${rows.length}</strong> 项 <span>按当前身份访问范围展示</span></div><div class="resource-grid">${
      rows
        .slice((page - 1) * 8, page * 8)
        .map(resourceCard)
        .join("") || empty()
    }</div>` +
    pagination(rows);
}
function renderAgents() {
  const rows = filtered(D.agents);
  $("#main").innerHTML =
    heading("智能体广场", "专注专业场景，让每一项智能能力都触手可及。") +
    `<div class="banner"><span class="tile">${icon("sparkles")}</span><div><h3>找到你的下一位业务搭档</h3><p>资源检索、政策解读、指标分析，从这里开启一次专业探索。</p></div><span class="banner-number">${D.agents.length}<small>个可用智能体</small></span></div>` +
    toolbar(["全部", "资源检索", "知识问答", "指标分析"]) +
    `<div class="agent-grid">${rows.map(agentCard).join("") || empty()}</div>`;
}
function currentSession() {
  return D.sessions.find((s) => s.id === sessionId);
}
function serviceGuidance(messages) {
  const question = pending?.question || [...messages].reverse().find(m=>m.role==='user')?.text || '';
  const terms = [['estate', /不动产|房产|权属|抵押/], ['progress', /进度|办件|审批/], ['mining', /矿业|矿产/], ['notice', /公示|公众意见|规划/], ['price', /地价/], ['guide', /指南|材料|流程|怎么办|如何.*申请/]];
  const rows = (D.publicPortal?.services || []).filter(s=>terms.some(([id,re])=>id===s.id&&re.test(question)));
  return rows.length ? `<section class="service-guidance" aria-label="相关办事指南"><strong>${icon('file')}与你的问题相关的办事服务</strong>${rows.map(s=>`<details open><summary>${esc(s.name)}</summary><p>${esc(s.body).replace(/\n/g,'<br>')}</p><small>来源：${esc(s.source)}</small><a class="btn primary small" href="#/front/services/${encodeURIComponent(s.id)}">${s.kind==='progress'?'查询进度':s.kind==='notice'?'查看公示 / 提交意见':'查看指南 / 提交咨询'} ${icon('arrow')}</a></details>`).join('')}</section>` : '';
}
function renderAssistant() {

  const session = currentSession(),
    agent = D.agents.find((a) => a.id === (session?.agentId || selectedAgent)),
    messages = session?.messages || [];
  if (!agent) {
    $("#main").innerHTML =
      heading("智能体暂不可用", "当前智能体未发布或已停用。") +
      empty("请到智能体广场选择其他能力");
    return;
  }
  selectedAgent = agent.id;
  $("#main").innerHTML =
    `<div class="service-workspace-bar"><div class="service-workspace-title"><h1>智能助手</h1></div><a class="service-feedback-link" href="#/front/requests">${icon('message')}我的咨询与意见</a></div><div class="chat-layout service-chat-workspace"><aside class="session-panel"><div class="session-heading"><span>${icon("message")}我的会话</span><span class="session-count">${D.sessions.length}</span></div><div class="session-actions">${btn("开启新对话", "newChat", "", "new-chat", "plus")}</div><div class="session-caption"><span>历史记录</span>${D.sessions.length ? btn("接续任务", "handoffList", "", "resume-task", "link") : ""}</div><div class="session-list">${
      D.sessions
        .slice()
        .reverse()
        .map(
          (s) =>
            `<button class="session-item ${s.id === sessionId ? "active" : ""}" title="${esc(s.name)}" data-action="resume" data-id="${s.id}">${icon("message")}<span>${esc(s.name)}</span></button>`,
        )
        .join("") || '<p class="muted">你的会话将在这里显示</p>'
    }</div><details class="service-sidebar-links"><summary>${icon('file')}直接办理</summary><div>${(D.publicPortal?.services||[]).map(s=>`<a href="#/front/services/${encodeURIComponent(s.id)}">${esc(s.name)} ${icon('arrow')}</a>`).join('')}</div></details><div class="session-help">${icon("shield")}会话按演示用户独立保存</div></aside><section class="chat-main"><div class="chat-header"><span class="tile ${agent.color}">${icon(agent.icon)}</span><div><h2>办事问答</h2><small>当前能力：${esc(agent.name)}</small></div>${btn(`申请清单 (${cart.length})`, "cart", "", "small", "file")}</div><div class="chat-scroll" id="chat-scroll">${serviceGuidance(messages)}${
      !messages.length
        ? `<div class="chat-welcome"><div class="large-sparkle">${icon(agent.icon)}</div><h2>有什么可以帮你？</h2><p>查询办事指南、了解政策，或找到需要的数据。</p><div class="prompt-grid">${[
            "用地审批进度怎么查？",
            "不动产登记信息如何查询？",
            "数据申请需要什么材料？",
            "什么是耕地占补平衡？",
          ]
            .filter((v, i, a) => a.indexOf(v) === i)
            .map(
              (q) =>
                `<button data-action="prompt" data-id="${esc(q)}">${icon("message")}<span>${esc(q)}</span>${icon("arrow")}</button>`,
            )
            .join("")}</div></div>`
        : messages
            .map((m) =>
              m.role === "user"
                ? `<div class="user-message"><span>${esc(m.text)}</span><span class="avatar">${esc(D.user.name[0])}</span></div>`
                : renderMessage(m, agent),
            )
            .join("")
    }${pending ? `<div class="user-message"><span>${esc(pending.question)}</span></div><div class="thinking"><span class="loader"></span>正在理解问题并检索演示资源…${btn("停止", "stop", "", "small")}</div>` : ""}</div><div class="composer-wrap"><form id="chat-form"><div class="context-bar"><span>${icon("filter")}查询条件</span><select name="region" aria-label="查询区域">${opts(D.regions, session?.context.region || businessContext?.region || (D.memories[0]?.enabled && D.memories[0]?.region) || "全区")}</select><select name="period" aria-label="查询时间">${opts(["全部时间", "最近30天", "2025年", "2026年"], session?.context.period || "全部时间")}</select>${session?.context.type ? `<span class="chip">${esc(session.context.type)}</span>` : ""}</div><div class="composer"><textarea name="question" aria-label="输入问题" placeholder="描述你的需求，或继续追问…" rows="2" maxlength="1000" required ${pending ? "disabled" : ""}></textarea><button type="submit" class="send-btn" aria-label="发送问题" ${pending ? "disabled" : ""}>${icon("up")}</button></div></form><div class="composer-note">${icon("sparkles")}使用预设场景与规则演示，回答及数据仅用于原型体验</div></div></section></div>`;
  const activeContext=session?.businessContext || businessContext;
  if(activeContext){
    const target=activeContext.sceneId?'/front/scenes/'+activeContext.sceneId:activeContext.caseId?'/front/cases/'+activeContext.caseId:'';
    $('.chat-header')?.insertAdjacentHTML('afterend',`<div class="pc-context-banner">${icon('link')}<span>业务上下文：${esc(activeContext.sceneName||activeContext.caseName||activeContext.sceneId||activeContext.caseId)} · ${esc(activeContext.region||'全区')}</span>${target?`<a href="#${target}">返回业务</a>`:''}</div>`);
  }
  if (messages.length || pending)
    $("#chat-scroll").scrollTop = $("#chat-scroll").scrollHeight;
}
function renderMessage(m, agent) {
  const rows = m.resourceIds
    .map((id) => D.resources.find((r) => r.id === id))
    .filter(Boolean);
  return `<div class="assistant-message"><span class="ai-avatar">${icon(agent.icon)}</span><div class="message-content"><div class="message-author">${esc(agent.name)} <small>v${m.agentVersion}.0</small></div><p>${esc(m.text)}</p><div class="answer-context">${tag(m.context.region)}${tag(m.context.period)}${m.context.type ? tag(m.context.type) : ""}</div>${rows.length ? `<div class="answer-resources">${rows.map((r) => `<div class="answer-resource"><span class="tile">${icon(typeIcon(r.type))}</span><div><button class="text-button" data-action="resource" data-id="${r.id}">${esc(r.name)}</button><small>${esc(r.type)} · ${esc(r.region)} · ${esc(r.frequency)}更新</small></div>${tag(r.access)}${btn("详情", "resource", r.id, "small")}${r.access === "可申请" ? btn(cart.includes(r.id) ? "已加入" : "加入清单", "addCart", r.id, "small") : ""}</div>`).join("")}</div>` : ""}${m.citations.map((c, i) => `<button class="citation" data-action="citation" data-id="${m.id}:${i}">${icon("book")}<span><b>[${i + 1}] ${esc(c.name)}</b><small>版本 v${c.version}.0 · 点击查阅引用片段</small></span>${icon("arrow")}</button>`).join("")}${m.indicators.map(renderIndicatorResult).join("")}${(m.templateRuns || []).map(resultTable).join("")}${m.trace ? traceView(m.trace) : ""}${m.canApply && rows.some(r => r.access === "可申请") ? btn("申请本次结果", "applyMessage", m.id, "primary", "file") : ""}<div class="answer-actions"><span>${fmt(m.at)}</span>${btn("复制", "copyAnswer", m.id, "text small", "copy")}${btn("反馈", "feedback", m.id, "text small", "message")}</div></div></div>`;
}
function renderIndicatorResult(i) {
  const max = Math.max(...i.values, 1);
  return `<div class="indicator-result"><div><span>${esc(i.name)}</span><strong>${i.value.toLocaleString()} <small>${esc(i.unit)}</small></strong><p>${esc(i.region || "")} · ${esc(i.period)} · v${i.version}.0 · 本地计算</p></div><div class="mini-chart">${i.values.slice(0,12).map((v, n) => `<div><span>${v}</span><i style="height:${Math.max(8, (v / max) * 75)}px"></i><small>单元 ${n + 1}</small></div>`).join("")}</div><div class="caliber">统计口径：${esc(i.caliber)}<br>数据来源：${esc(i.source || "历史示例试算")}${i.dependencies?.length ? `<br>依赖版本：${i.dependencies.map(d=>`${esc(d.name)} v${d.version} = ${d.value}`).join("；")}` : ""}${(i.knowledgeIds || []).map(id=>D.knowledge.find(d=>d.id===id)).filter(Boolean).map(d=>`<details><summary>知识依据：${esc(d.name)} · v${d.version}</summary><p>${esc(d.body)}</p></details>`).join("")}</div></div>`;
}
function applicationList(admin = false) {
  const rows = filtered(D.applications.slice().reverse());
  $("#main").innerHTML =
    heading(
      admin ? "资源使用审核" : "我的申请",
      admin
        ? "逐项处理资源申请，审批结果同步业务工作台。"
        : "每一份申请，都有清晰可见的办理进度。",
      admin
        ? tag("模拟审批")
        : btn(`申请清单 (${cart.length})`, "cart", "", "primary", "plus"),
    ) +
    stats([
      ["全部申请", D.applications.length, "单", "file", `/${mode}/${route}`],
      [
        "待审核",
        D.applications.filter((a) => a.status === "待审核").length,
        "单",
        "clock",
        `/${mode}/${route}`,
      ],
      [
        "已通过",
        D.applications.filter((a) => a.status === "已通过").length,
        "单",
        "check",
        `/${mode}/${route}`,
      ],
      [
        "部分通过",
        D.applications.filter((a) => a.status === "部分通过").length,
        "单",
        "layers",
        `/${mode}/${route}`,
      ],
    ]) +
    `<section class="panel table-panel">${toolbar(["全部", "待审核", "已通过", "部分通过", "已驳回", "已撤回"])}<div class="table-scroll"><table><thead><tr><th>申请编号 / 用途</th><th>申请人</th><th>资源数量</th><th>申请时间</th><th>办理状态</th><th>操作</th></tr></thead><tbody>${
      rows
        .slice((page - 1) * 8, page * 8)
        .map(
          (a) =>
            `<tr><td><button class="text-button" data-action="application" data-id="${a.id}">${a.id}</button><small>${esc(a.purpose)}</small></td><td>${esc(a.user)}</td><td>${a.items.length} 项</td><td>${fmt(a.at)}</td><td>${tag(a.status)}</td><td>${btn(admin ? "办理详情" : "查看详情", "application", a.id, "text small")}</td></tr>`,
        )
        .join("") ||
      `<tr><td colspan="6">${empty("还没有资源申请", "从资源检索助手发现资源，加入清单后即可提交。")}</td></tr>`
    }</tbody></table></div>${pagination(rows)}</section>`;
}
function preferenceForm(m, admin = false) {
  return `<form id="preferences-form" data-id="${m.id}" data-rev="${m.rev}" class="settings-form"><div class="form-grid"><label>常用区域<select name="region">${opts(D.regions, m.region)}</select></label><label>常用业务领域<input name="domain" value="${esc(m.domain)}" maxlength="100" required></label><label>技能等级<select name="skill">${opts(["入门", "业务熟悉", "专家"], m.skill || "业务熟悉")}</select></label><label>回答详略<select name="detail">${opts(["简洁", "详细"], m.detail)}</select></label><label class="switch-label"><span>启用个性化记忆</span><input name="enabled" type="checkbox" ${m.enabled ? "checked" : ""}></label><label class="full">历史摘要<textarea name="summary" rows="4" maxlength="2000">${esc(m.summary)}</textarea><small>用于新会话的默认偏好；当前明确指定的条件优先。${m.recentSummary ? "近期摘要：" + esc(m.recentSummary) : ""}</small>${(m.facts || []).map(f => `<div class="memory-fact"><strong>${esc(f.topic)} · ${esc(f.region)}</strong><p>${esc(f.questions.join("；"))}</p><small>${esc(f.nextAction)} · 来源 ${esc(f.sessionId)}</small>${mode === "front" ? btn("在新会话中接续", "handoff", f.sessionId, "small") : ""}</div>`).join("")}</label></div><div class="form-footer">${btn("清除摘要", "clearSummary", m.id, "text", "trash")}<button class="btn primary" type="submit">${icon("check")}保存偏好</button></div></form>`;
}
function renderProfile() {
  const m = D.memories[0];
  $("#main").innerHTML =
    heading("个人中心", "保留有价值的上下文，让下一次对话更懂你的业务。") +
    `<div class="profile-banner"><span class="avatar large">${esc(D.user.name[0])}</span><div><h2>${esc(D.user.name)}</h2><p>${esc(D.user.department)} · ${esc(D.user.role)}</p></div><span class="right">访问范围 ${tag(D.user.region)}</span></div><div class="tabs">${["偏好与记忆", "会话记录", "我的反馈"].map((t, i) => `<button class="${(adminTab || "偏好与记忆") === t ? "active" : ""}" data-action="tab" data-id="${t}">${t}</button>`).join("")}</div><section class="panel">${
      !adminTab || adminTab === "偏好与记忆"
        ? `<div class="section-title"><h2>我的业务偏好</h2>${tag("仅自己可见")}</div>${m ? preferenceForm(m) : empty("当前身份没有业务记忆")}`
        : adminTab === "会话记录"
          ? D.sessions
              .slice()
              .reverse()
              .map(
                (s) =>
                  `<button class="activity-row" data-action="resume" data-id="${s.id}"><span class="tile">${icon("message")}</span><div><strong>${esc(s.name)}</strong><small>${s.messages.length / 2} 轮对话 · ${fmt(s.updated)}</small></div>${icon("arrow")}</button>`,
              )
              .join("") || empty("暂无会话记录")
          : D.feedback
              .slice()
              .reverse()
              .map(
                (f) =>
                  `<div class="activity-row"><span class="tile">${icon("message")}</span><div><strong>${esc(f.question)}</strong><p>${esc(f.note)}</p><small>${fmt(f.at)}</small></div>${tag(f.status)}</div>`,
              )
              .join("") || empty("暂无反馈记录")
    }</section>`;
}
function renderOverview() {
  const all = D.resources,
    published = all.filter((r) => r.status === "已发布").length;
  $("#main").innerHTML =
    heading(
      "管理总览",
      "从知识生产到能力调用，掌握智能中心的每一步。",
      btn("配置智能体", "navigate", "/admin/agents", "primary", "plus"),
    ) +
    stats([
      ["已编目资源", all.length, "项", "database", "/admin/resources"],
      [
        "已发布智能体",
        D.agents.filter((a) => a.status === "已发布").length,
        "个",
        "grid",
        "/admin/agents",
      ],
      ["知识文档", D.knowledge.length, "篇", "book", "/admin/knowledge"],
      [
        "待处理申请",
        D.applications.filter((a) => a.status === "待审核").length,
        "单",
        "file",
        "/admin/approvals",
      ],
    ]) +
    `<div class="admin-overview-grid"><section class="panel"><div class="section-title"><h2>能力建设进度</h2><span class="muted">基于当前演示数据</span></div><div class="capability-grid">${[
      ["resources", "元数据标注", "database"],
      ["indicators", "指标知识", "chart"],
      ["knowledge", "知识库", "book"],
      ["corpora", "语料资产", "code"],
      ["memories", "用户记忆", "brain"],
    ]
      .map(
        ([e, t, i]) =>
          `<a href="#/admin/${e}" class="capability"><span class="tile">${icon(i)}</span><h3>${t}</h3><strong>${D[e].length}<small> ${e === "memories" ? "位用户" : "项资产"}</small></strong><div class="progress"><i style="width:${Math.round((D[e].filter((r) => (e === "memories" ? r.enabled : r.status === "已发布")).length / Math.max(D[e].length, 1)) * 100)}%"></i></div><small>${e === "memories" ? "个性化启用" : "已发布版本"} ${D[e].filter((r) => (e === "memories" ? r.enabled : r.status === "已发布")).length} 项</small></a>`,
      )
      .join(
        "",
      )}</div></section><section class="panel"><div class="section-title"><h2>资源发布概况</h2></div><div class="donut" style="--percent:${(published / Math.max(1, all.length)) * 100}%"><div><strong>${published}</strong><small>已发布资源</small></div></div><div class="legend"><span><i></i>已发布 ${published}</span><span><i class="gray"></i>待发布 / 停用 ${all.length - published}</span></div></section></div><div class="bottom-grid"><section class="panel"><div class="section-title"><h2>最近操作</h2><a href="#/admin/settings">操作日志 ${icon("arrow")}</a></div>${
      D.audit
        .slice(-5)
        .reverse()
        .map(
          (a) =>
            `<div class="activity-row"><span class="soft-icon">${icon("clock")}</span><div><strong>${esc(a.action)} · ${esc(a.name)}</strong><small>${esc(a.actor)} · ${fmt(a.at)}</small></div></div>`,
        )
        .join("") || empty("暂无操作记录", "保存配置、发布版本后将在这里显示。")
    }</section><section class="panel"><div class="section-title"><h2>调用与反馈</h2><a href="#/admin/calls">查看详情 ${icon("arrow")}</a></div><div class="call-summary"><div><strong>${D.calls.length}</strong><span>演示调用</span></div><div><strong>${D.feedback.filter((f) => f.status !== "已处理").length}</strong><span>待改进反馈</span></div></div><div class="notice">${icon("sparkles")}演示采用预设规则，真实大模型与生产接口尚未接入。</div></section></div>`;
}
function entityForRoute() {
  if(route==="articles")return "knowledge";
  if (route === "resources" && adminTab === "templates") return "templates";
  if (route === "resources" && adminTab === "dictionaries")
    return "dictionaries";
  return route;
}
function adminList() {
  let e = entityForRoute(),
    m = meta[e],
    rows = e === "knowledge" && route === "knowledge" ? D[e].filter(r=>{const v=indexState(r);return (filter==="全部"||(filter==="检索已启用"&&v.enabled)||(filter==="未纳入检索"&&!v.enabled)||(filter==="索引待更新"&&v.pending)||r.category===filter)&&(!query||[r.name,r.body,r.source].join(" ").toLowerCase().includes(query.toLowerCase()));}) : filtered(D[e]);
  const tabs =
    route === "resources"
      ? [
          ["resources", "资源目录"],
          ["templates", "元数据模板"],
          ["dictionaries", "枚举字典"],
        ]
      : route === "corpora"
        ? [
            ["全部", "全部语料"],
            ["问答样例", "问答样例"],
            ["提示词模板", "提示词模板"],
            ["SQL 模板", "SQL 模板"],
            ["API 模板", "API 模板"],
          ]
        : [];
  $("#main").innerHTML =
    heading(
      e === "knowledge" ? (route === "articles" ? "资讯发布" : "AI 知识库") : m[0],
      e === "knowledge" ? "共用原始文档，门户发布与知识索引分别管理，互不自动更新。" : m[1],
      `${route === "articles" ? "" : managementTools(e)}${e === "knowledge" ? btn("导入文档", "importDoc", "", "", "download") : ""}${btn(e === "resources" ? "新增资源" : e === "knowledge" ? "新建文档" : "新建" + m[0].replace("管理", ""), "new", e, "primary", "plus")}`,
    ) +
    `<div class="management-intro"><span class="tile">${icon(m[2])}</span><div><strong>${e === "resources" ? "资源描述越完整，智能检索越准确。" : e === "knowledge" ? "保存文档后，分别发布到门户或纳入 AI 检索。" : e === "corpora" ? "每一次高质量交互，都可以成为可复用的能力。" : e === "indicators" ? "统一定义、统一口径、统一版本。" : e === "agents" ? "从资源与知识出发，组合你的智能能力。" : "维护统一的业务描述规范。"}</strong><p>${e==="knowledge"&&route==="knowledge"?`共 ${D[e].length} 项 · 检索已启用 ${D[e].filter(r=>indexState(r).enabled).length} 项 · 索引待更新 ${D[e].filter(r=>indexState(r).pending).length} 项`:`共 ${D[e].length} 项 · 已发布 ${D[e].filter((r) => r.status === "已发布").length} 项 · 草稿修改在发布后生效`}</p></div></div>${tabs.length ? `<div class="tabs">${tabs.map(([k, t]) => `<button data-action="${route === "corpora" ? "corpusTab" : "tab"}" data-id="${k}" class="${(route === "corpora" ? filter : adminTab || "resources") === k ? "active" : ""}">${t}</button>`).join("")}</div>` : ""}<section class="panel table-panel">${toolbar(["全部", ...(e==="knowledge"&&route==="knowledge"?["检索已启用","未纳入检索","索引待更新"]:["已发布", "草稿", "已停用"]), ...(route === "corpora" ? ["问答样例", "提示词模板", "SQL 模板", "API 模板"] : e === "knowledge" ? [...new Set(D.knowledge.map(r=>r.category))] : [])])}<div class="table-scroll"><table><thead><tr><th>${e === "resources" ? "资源名称 / 来源" : "名称 / 描述"}</th><th>类型 / 分类</th><th>版本</th><th>状态</th><th>更新时间</th><th class="operation-col">操作</th></tr></thead><tbody>${
      rows
        .slice((page - 1) * 8, page * 8)
        .map(
          (r) =>
            `<tr><td><div class="name-cell"><span class="tile small">${icon(e === "resources" ? typeIcon(r.type) : m[2])}</span><div><button class="text-button" data-action="edit" data-id="${e}:${r.id}">${esc(r.name)}</button><small>${esc(r.source || r.description || r.scene || r.code || r.id)}</small></div></div></td><td>${esc(r.type || r.category || "通用配置")}</td><td><span class="version">v${r.version}.0</span>${r.status === "草稿" && r.published ? "<small>有未发布修改</small>" : ""}</td><td>${e === "knowledge" ? contentChannelStatus(r) : tag(r.status)}</td><td>${fmt(r.updated)}</td><td><div class="row-actions">${btn("配置", "edit", `${e}:${r.id}`, "text small")}${e === "knowledge" ? contentChannelButtons(r) : (r.status !== "已发布" ? btn("发布", "publish", `${e}:${r.id}`, "text small") : btn("停用", "disable", `${e}:${r.id}`, "text small"))}${e === "indicators" ? btn("趋势对比", "compare", r.id, "text small") : e === "knowledge" && route !== "articles" ? btn("图谱", "graph", r.id, "text small") : ""}${permittedAdminNav().some(n=>n[0]==="intelligence-links")?`<a class="btn text small" href="#/admin/intelligence-links?asset=${encodeURIComponent(e+":"+r.id)}">关联与影响</a>`:""}${e==="agents"?btn("评测","ia-evaluate",r.id,"text small"):""}${btn("历史", "versions", `${e}:${r.id}`, "text small")}${route !== "articles" && ["indicators", "knowledge", "corpora", "agents"].includes(e) ? btn("试运行", "trial", `${e}:${r.id}`, "text small") : ""}${btn("复制", "duplicate", `${e}:${r.id}`, "icon-btn", "copy")}${!r.published || (e === "knowledge" && r.status === "已停用") ? btn("删除", "delete", `${e}:${r.id}`, "icon-btn", "trash") : ""}</div></td></tr>`,
        )
        .join("") || `<tr><td colspan="6">${empty()}</td></tr>`
    }</tbody></table></div>${pagination(rows)}</section>`;
}
function renderMemories() {
  if (adminTab === "summaries" || adminTab === "sessions")
    return renderMemoryRecords();
  const rows = filtered(D.memories);
  $("#main").innerHTML =
    heading(
      "用户记忆管理",
      "管理演示用户的画像与摘要，建立连贯、可控的个性化体验。",
    ) +
    `<div class="notice">${icon("shield")}仅展示已授权的虚构演示用户记录。画像偏好与资源访问范围分别维护。</div>` +
    memoryTabs() +
    toolbar(["全部"]) +
    `<div class="memory-grid">${rows.map((m) => `<section class="panel memory-card"><div class="memory-heading"><span class="avatar">${esc(m.name[0])}</span><div><h3>${esc(m.name)}</h3><small>${esc(D.users.find((u) => u.id === m.id)?.department)}</small></div>${tag(m.enabled ? "已启用" : "已停用")}</div><dl class="detail-grid"><dt>常用区域</dt><dd>${esc(m.region)}</dd><dt>关注领域</dt><dd>${esc(m.domain)}</dd><dt>回答偏好</dt><dd>${esc(m.detail)}</dd></dl><div class="summary-block"><small>历史摘要</small><p>${esc(m.summary || "暂无长期摘要")}</p></div>${btn("管理记忆", "memory", m.id, "", "edit")}</section>`).join("")}</div>`;
}
function memoryTabs() {
  return `<div class="tabs">${[
    ["profiles", "用户画像"],
    ["summaries", "历史摘要"],
    ["sessions", "会话状态"],
  ]
    .map(
      ([k, t]) =>
        `<button data-action="tab" data-id="${k}" class="${(adminTab || "profiles") === k ? "active" : ""}">${t}</button>`,
    )
    .join("")}</div>`;
}
function renderMemoryRecords() {
  const summary = adminTab === "summaries";
  $("#main").innerHTML =
    heading(
      "用户记忆管理",
      "查看已授权虚构用户的摘要与会话条件，保留必要的业务上下文。",
    ) +
    memoryTabs() +
    `<section class="panel">${
      summary
        ? D.memories
            .map(
              (m) =>
                `<div class="activity-row"><span class="tile">${icon("brain")}</span><div><strong>${esc(m.name)}</strong><p>${esc(m.summary || "暂无手动摘要")}</p><p>${esc(m.recentSummary || "暂无自动生成的近期摘要")}</p><small>来源会话：${esc(m.sourceSession || "—")} · ${fmt(m.summaryUpdated)}</small></div>${btn("修正摘要", "memory", m.id, "small")}</div>`,
            )
            .join("")
        : `<div class="table-scroll"><table><thead><tr><th>会话主题</th><th>用户</th><th>当前区域</th><th>时间条件</th><th>轮次</th><th>最近更新</th></tr></thead><tbody>${
            (D.memorySessions || [])
              .slice()
              .reverse()
              .map(
                (x) =>
                  `<tr><td>${esc(x.name)}</td><td>${esc(D.users.find((u) => u.id === x.userId)?.name)}</td><td>${esc(x.context.region)}</td><td>${esc(x.context.period)}</td><td>${x.turns}</td><td>${fmt(x.updated)}</td></tr>`,
              )
              .join("") ||
            `<tr><td colspan="6">${empty("暂无会话状态")}</td></tr>`
          }</tbody></table></div>`
    }</section>`;
}
function renderCalls() {
  const tab = adminTab || "calls";
  $("#main").innerHTML =
    heading("调用与反馈", "追溯能力调用，持续改善智能服务质量。", btn("改进草稿", "feedbackDrafts", "", "small")) +
    `<div class="tabs">${[
      ["calls", "调用记录"],
      ["feedback", "用户反馈"],
      ["interfaces", "能力接口"],
    ]
      .map(
        ([k, t]) =>
          `<button class="${tab === k ? "active" : ""}" data-action="tab" data-id="${k}">${t}</button>`,
      )
      .join("")}</div><section class="panel">${
      tab === "feedback"
        ? D.feedback
            .slice()
            .reverse()
            .map(
              (f) =>
                `<div class="feedback-row"><div><h3>${esc(f.question)}</h3><p>${esc(f.note)}</p><small>${esc(f.user)} · ${fmt(f.at)} · 关联回答 ${f.messageId}</small></div>${tag(f.status)}${btn("标注 / 记忆改进", "improveFeedback", f.id, "small")}${!f.sampleId ? btn("转为待审样例", "feedbackConvert", f.id, "small") : btn("编辑改进样例", "edit", `corpora:${f.sampleId}`, "small")}${f.status !== "已处理" ? btn("标记已处理", "feedbackResolve", f.id, "small") : ""}</div>`,
            )
            .join("") || empty("暂无用户反馈")
        : tab === "interfaces"
          ? `<div class="interface-card"><span class="tile">${icon("code")}</span><div><h3>智能体对话接口</h3><p>本地能力接口 · POST /api/v1/agents/invoke</p><pre>${esc(JSON.stringify({ apiVersion: "v1", agentId: "a1", question: "找地灾巡查记录表" }, null, 2))}</pre><p>输出：会话标识、消息、资源标识、引用、查询条件。</p>${btn("查看契约并试调用", "interfaceTest", "", "primary")}</div></div><div class="interface-card"><span class="tile blue">${icon("link")}</span><div><h3>资源中心审批接口</h3><p>真实资源中心尚未接入，当前通过模拟审批工作区演示。</p>${tag("待接入")}</div></div>`
          : `${toolbar(["全部", "完成", "无结果"])}<div class="table-scroll"><table><thead><tr><th>调用问题</th><th>智能体 / 版本</th><th>用户</th><th>时间</th><th>结果</th><th>追踪</th></tr></thead><tbody>${
              filtered(D.calls.slice().reverse())
                .map(
                  (c) =>
                    `<tr><td>${esc(c.question)}</td><td>${esc(c.agent)}<small>v${c.version}.0 · ${c.mode}</small></td><td>${esc(c.user)}</td><td>${fmt(c.at)}</td><td>${tag(c.status)}</td><td>${btn("查看", "callDetail", c.id, "text small")}</td></tr>`,
                )
                .join("") ||
              `<tr><td colspan="6">${empty("暂无调用记录", "在前台发送一次问题，即可查看调用记录。")}</td></tr>`
            }</tbody></table></div>`
    }</section>`;
}
function renderSettings() {
  const tab = adminTab || "users";
  $("#main").innerHTML =
    heading("基础管理", "维护演示访问范围，查看关键操作记录。") +
    `<div class="tabs">${[
      ["users", "角色与访问范围"],
      ["audit", "操作日志"],
      ["demo", "演示设置"],
    ]
      .map(
        ([k, t]) =>
          `<button class="${tab === k ? "active" : ""}" data-action="tab" data-id="${k}">${t}</button>`,
      )
      .join("")}</div><section class="panel">${
      tab === "users"
        ? `<div class="table-scroll"><table><thead><tr><th>用户</th><th>部门</th><th>角色</th><th>访问区域</th><th>操作</th></tr></thead><tbody>${D.users.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.department)}</td><td>${tag(u.role)}</td><td>${esc(u.region)}</td><td>${u.role === "业务用户" ? btn("调整范围", "scope", u.id, "text small") : "内置演示角色"}</td></tr>`).join("")}</tbody></table></div><div class="notice">业务用户访问前台；审批人员仅访问申请办理；平台管理员维护所有后台配置。演示身份可直接切换，不是生产身份认证。</div>`
        : tab === "audit"
          ? `<div class="table-scroll"><table><thead><tr><th>操作人</th><th>操作</th><th>对象</th><th>时间</th></tr></thead><tbody>${
              D.audit
                .slice()
                .reverse()
                .map(
                  (a) =>
                    `<tr><td>${esc(a.actor)}</td><td>${esc(a.action)}</td><td>${esc(a.name)}</td><td>${fmt(a.at)}</td></tr>`,
                )
                .join("") ||
              `<tr><td colspan="4">${empty("暂无操作记录")}</td></tr>`
            }</tbody></table></div>`
          : `<div class="settings-section"><h2>演示数据与运行方式</h2><p>前后台共用本地 SQLite 数据库。修改保存后可刷新同步，重启服务保留数据。</p><p>AI 采用确定性规则与预置场景；未接入真实大模型、向量数据库和生产审批系统。</p><div class="danger-zone"><h3>重置演示数据</h3><p>清空当前原型中的对话、申请及自定义配置，恢复初始演示数据。</p>${btn("重置演示数据", "reset", "", "danger", "refresh")}</div></div>`
    }</section>`;
}
function permittedAdminNav(){
  if(D.user.role==='平台管理员')return adminNav;
  const p=D.platform?.permissions||{},allowed=new Set(['overview']);
  if(D.user.role==='资源审批人员'){allowed.add('approvals');allowed.add('grants');allowed.add('center-resources');}
  if(p.manageApps)['app-registry','scene-templates','widgets'].forEach(x=>allowed.add(x));
  if(p.manageFlows)['business-models','workflows','cases','business-assets','knowledge'].forEach(x=>allowed.add(x));
  if(p.manageIdentity)allowed.add('identity');
  if(D.integration?.internalAccess)['integration-resources','integration-workbench'].forEach(x=>allowed.add(x));
  if(D.integration?.resultPermissions?.view)allowed.add('integration-results');
  return adminNav.filter(n=>allowed.has(n[0]));
}
function renderPage() {
  if(mode==='admin'){
    const extra={'template-preview':'scene-templates','scenes':'scene-templates','forms':'workflows','workbench':'cases'};
    if(!permittedAdminNav().some(n=>n[0]===(extra[route]||route))){$('#main').innerHTML=heading('暂无管理权限','当前身份不能管理此模块。')+'<a class="btn" href="#/admin/overview">返回工作台</a>';return;}
    if(route==='overview'){renderDesignOverview();return;}
    if(route==='grants'){renderGrantLedger();return;}
    if(route==='articles'){adminList();bindForms();return;}
    if(intelligenceUI.render()){bindForms();return;}
  }
  if(operationsCenterUI.render())return;
  if(integrationUI.render())return;
  if(centersUI.render())return;
  const handledOps=operationsUI.render();
  const handledManagement=managementUI.render();
  if(handledOps||handledManagement)return;
  if(publicUI.render()){bindForms();return;}
  if(platformUI.render())return;
  if (mode === "front")
    (
      ({
        home: renderHome,
        tools: renderPortalTools,
        knowledge: renderPortalKnowledge,
        catalog: renderCatalog,
        agents: renderAgents,
        assistant: renderAssistant,
        applications: () => applicationList(false),
        profile: renderProfile,
      })[route] || renderHome
    )();
  else if (meta[route]) adminList();
  else
    (
      ({
        overview: renderOverview,
        memories: renderMemories,
        calls: renderCalls,
        approvals: () => applicationList(true),
        settings: renderSettings,
      })[route] || renderOverview
    )();
  bindForms();
}
function modal(title, html, wide = false) {
  const d = $("#dialog");
  if (!d.open) modalFocus = document.activeElement;
  d.className = wide ? "wide" : "";
  d.innerHTML = `<div class="dialog-head"><div><span class="eyebrow">${mode === "admin" ? "MANAGEMENT" : "WORKSPACE"}</span><h2 id="dialog-title">${esc(title)}</h2></div><button class="icon-btn" data-action="close" aria-label="关闭弹窗">${icon("x")}</button></div><div class="dialog-body">${html}</div>`;
  if (!d.open) d.showModal();
  bindForms();
}
function closeModal() {
  $("#dialog").close();
  if (modalFocus?.isConnected) modalFocus.focus();
}
function detailGrid(pairs) {
  return `<dl class="detail-grid">${pairs.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v || "—")}</dd>`).join("")}</dl>`;
}
function resourceDetail(id) {
  const r = D.resources.find((r) => r.id === id);
  if (!r) return toast("资源已停用或不可访问");
  modal(
    r.name,
    `<div class="resource-detail-head"><span class="tile large">${icon(typeIcon(r.type))}</span><div><div class="chips"><span>${esc(r.type)}</span><span>${esc(r.category)}</span></div><p>${esc(r.description)}</p></div>${tag(r.access)}</div>${detailGrid(
      [
        ["提供单位", r.source],
        ["覆盖范围", r.region],
        ["坐标系", r.crs],
        ["更新频次", r.frequency],
        ["更新时间", fmt(r.updated)],
        ["资源版本", `v${r.version}.0`],
        ["资源标识", r.id],
        ["业务同义词", r.aliases],
      ],
    )}<h3>字段与元数据</h3><div class="table-scroll"><table><thead><tr><th>字段</th><th>中文名称</th><th>类型</th><th>单位</th><th>业务说明</th></tr></thead><tbody>${(r.fields || []).map((f) => `<tr><td><code>${esc(f.name)}</code></td><td>${esc(f.label)}</td><td>${esc(f.type)}</td><td>${esc(f.unit || "—")}</td><td>${esc(f.description || f.alias)}</td></tr>`).join("")}</tbody></table></div>${
      r.relations?.length
        ? `<h3>关联资源</h3><div class="relations">${r.relations
            .map((id) => D.resources.find((r) => r.id === id))
            .filter(Boolean)
            .map((r) => btn(esc(r.name), "resource", r.id, "", "link"))
            .join("")}</div>`
        : ""
    }${(r.relationEdges || []).length ? `<h3>结构化资源关系</h3>${r.relationEdges.map(e=>`<p>${esc(e.type)}：${esc(e.sourceField || "图层")} → ${esc(D.resources.find(x=>x.id===e.target)?.name || "受限资源")} ${esc(e.targetField)}</p>`).join("")}` : ""}<div class="notice">${icon("shield")}${r.access === "已授权" ? "当前身份可查看此资源的演示内容。" : "可查看目录元数据；实际数据使用需经资源申请授权。"}</div><div class="form-footer">${r.access === "已授权" ? btn("打开示例内容", "preview", r.id, "primary", "eye") : r.access === "可申请" ? btn(cart.includes(id) ? "已加入申请清单" : "加入申请清单", "addCart", r.id, "primary", "plus") : tag("申请正在办理中")}${btn("查看申请清单", "cart", "", "", "file")}</div>`,
    true,
  );
}
function previewResource(id) {
  const r = D.resources.find((r) => r.id === id);
  if (!r || r.access !== "已授权") return toast("资源尚未授权或已停用");
  let content = "";
  if (r.type === "知识文档") {
    const d = D.knowledge.find((d) => d.id === r.documentId);
    content = d
      ? `<p class="muted">${esc(d.source)} · v${d.version}.0</p>${d.chunks.map((c) => `<p class="document-paragraph">${esc(c.text)}</p>`).join("")}`
      : empty("文档未发布或已停用");
  } else if (r.type === "图层服务") {
    content = `<div class="map-preview"><div class="map-grid"></div><svg viewBox="0 0 500 220" role="img" aria-label="示例图层覆盖范围"><path d="M60 130 100 80 170 100 220 60 270 85 340 50 440 100 410 155 325 145 260 180 195 160 125 175Z" fill="#aecbb9" stroke="#33836c" stroke-width="2"/><path d="m100 125 110 18 70-40 130 20" fill="none" stroke="white" stroke-width="4"/><circle cx="220" cy="110" r="6" fill="#1a6858"/></svg><span>${esc(r.region)} · 示例范围预览</span></div>`;
  } else if (r.type === "工具服务") {
    content = `<p>${esc(r.description)}</p><div class="notice">工具使用示例：选择监测区域后，查看预置分析结果。</div><form id="tool-form"><label>监测区域<select name="region">${opts(D.regions, D.user.region)}</select></label><button class="btn primary">运行示例分析</button></form><div id="tool-result"></div>`;
  } else {
    const sample = r.sample || [];
    content = `<div class="table-scroll"><table><thead><tr>${Object.keys(
      sample[0] || {},
    )
      .map((k) => `<th>${esc(k)}</th>`)
      .join("")}</tr></thead><tbody>${sample
      .map(
        (row) =>
          `<tr>${Object.values(row)
            .map((v) => `<td>${esc(v)}</td>`)
            .join("")}</tr>`,
      )
      .join("")}</tbody></table></div>`;
  }
  modal(
    r.name + " · 示例内容",
    content + `<p class="muted">仅展示虚构样例，不作为实际业务依据。</p>`,
    true,
  );
}
function cartDialog() {
  const rows = cart
    .map((id) => D.resources.find((r) => r.id === id && r.access === "可申请"))
    .filter(Boolean);
  cart = rows.map((r) => r.id);
  const end = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
  modal(
    "资源申请清单",
    rows.length
      ? `<p class="muted">统一提交 ${rows.length} 项资源的使用申请，办理结果按资源逐项显示。</p><div class="cart-list">${rows.map((r) => `<div class="activity-row"><span class="tile">${icon(typeIcon(r.type))}</span><div><strong>${esc(r.name)}</strong><small>${esc(r.type)} · ${esc(r.region)}</small></div><button class="icon-btn" data-action="removeCart" data-id="${r.id}" aria-label="移除${esc(r.name)}">${icon("x")}</button></div>`).join("")}</div><form id="apply-form"><div class="form-grid"><label>申请人<input value="${esc(D.user.name)} · ${esc(D.user.department)}" disabled></label><label>使用截止日期<input name="validUntil" type="date" value="${end}" min="${new Date(Date.now() + 864e5).toISOString().slice(0, 10)}" max="${new Date(Date.now() + 365 * 864e5).toISOString().slice(0, 10)}" required></label>${input("method","获取方式（混合资源可自动匹配）","","select",[["","按资源类型自动匹配"],"数据下载","数据订阅","定时推送","数据服务","功能接口","离线获取","数据访问"])}<label class="full">使用用途 <em>*</em><textarea name="purpose" rows="3" required minlength="5" maxlength="1000" placeholder="请说明业务场景和使用目的，至少5个字"></textarea></label></div><div class="notice">${icon("file")}本原型使用模拟审批，结果可在“我的申请”中查看。</div><div class="form-footer"><button class="btn primary" type="submit">提交申请 ${icon("arrow")}</button></div></form>`
      : empty("申请清单还是空的", "在资源详情或检索结果中点击“加入申请清单”。"),
    true,
  );
}
function applicationDetail(id) {
  const a = D.applications.find((a) => a.id === id);
  if (!a) return toast("申请不存在");
  modal(
    a.id,
    `<div class="detail-status">${tag(a.status)}<span>${fmt(a.at)} 提交</span></div>${detailGrid(
      [
        ["申请人", a.user],
        ["使用期限", a.validUntil],
        ["使用用途", a.purpose],
      ],
    )}<h3>申请资源 · ${a.items.length} 项</h3>${a.items.map((i) => `<div class="application-item"><div><strong>${esc(i.name)}</strong><small>${esc(i.type)}${i.note ? " · " + esc(i.note) : ""}</small></div>${tag(i.status)}${mode === "admin" && i.status === "待审核" && a.status !== "已撤回" ? btn("办理", "decision", `${a.id}:${i.resourceId}`, "small primary") : ""}</div>`).join("")}<h3>办理时间线</h3><ol class="timeline">${a.history.map((h) => `<li><span></span><div><strong>${esc(h.text)}</strong><small>${esc(h.actor)} · ${fmt(h.at)}</small></div></li>`).join("")}</ol>${mode === "front" && a.status === "待审核" ? `<div class="form-footer">${btn("补充说明", "supplement", a.id)}${a.items.every((i) => i.status === "待审核") ? btn("撤回申请", "cancel", a.id, "danger") : ""}</div>` : ""}`,
    true,
  );
}
const input = (
  key,
  label,
  value = "",
  type = "text",
  options = [],
  full = false,
) =>
  `<label class="${full ? "full" : ""}">${label}${type === "textarea" ? `<textarea name="${key}" rows="${["body", "steps"].includes(key) ? 5 : 3}" maxlength="${key === "body" || key === "dataRows" ? 204800 : 10000}">${esc(value)}</textarea>` : type === "select" ? `<select name="${key}">${opts(options, value)}</select>` : type === "check" ? `<input name="${key}" type="checkbox" ${value ? "checked" : ""}>` : `<input name="${key}" type="${type}" value="${esc(value)}" ${key === "name" ? 'required maxlength="100"' : 'maxlength="1000"'}>`}</label>`;
function binding(key, label, entity, value) {
  const ids = csvIds(value);
  const hint =
    key === "mapResourceIds"
      ? "仅选择地图图层；启用地图能力时至少绑定一个图层，且仍需用户授权。"
      : key === "relations"
      ? "可多选；留空表示未建立资源关联，不会自动关联全部资源。"
      : route === "corpora"
        ? "可多选；关联资源用于记录该语料的业务来源。"
        : "可多选；留空表示可使用全部已发布且当前用户有权访问的内容。";
  return `<label class="full">${label}<select name="${key}" multiple size="${Math.min(4, Math.max(2, D[entity].length))}">${D[entity].filter(x=>key!=="mapResourceIds"||x.type==="图层服务").map((x) => `<option value="${x.id}" ${ids.includes(x.id) ? "selected" : ""}>${esc(x.name)} (${x.id})</option>`).join("")}</select><small>${hint}</small></label>`;
}
function resourceFields(fields) {
  return fields
    .map(
      (f, n) =>
        `<details class="field-row" open><summary><b>${esc(f.label || "新字段")}</b><code>${esc(f.name)}</code><button type="button" class="icon-btn" data-action="removeField" aria-label="删除字段">${icon("trash")}</button></summary><div class="form-grid field-inputs">${[
          ["name", "字段名"],
          ["label", "中文名称"],
          ["alias", "同义词"],
          ["type", "数据类型"],
          ["unit", "字段单位"],
          ["dictionary", "枚举字典"],
          ["location", "定位类型"],
          ["topic", "专题字段"],
          ["description", "业务解释"],
        ]
          .map(
            ([k, t]) =>
              k === "dictionary" ? `<label>${t}<select data-field="dictionary"><option value="">无枚举字典</option>${D.dictionaries.map(d=>`<option value="${esc(d.id)}" ${[d.id,d.name,d.code].includes(f.dictionary)?"selected":""}>${esc(d.name)} (${esc(d.code)})</option>`).join("")}</select></label>` : `<label>${t}<input data-field="${k}" value="${esc(f[k] || "")}" ${["name", "label"].includes(k) ? "required" : ""}></label>`,
          )
          .join("")}<div class="full check-group">${[
          ["query", "AI 查询"],
          ["display", "显示字段"],
          ["statistic", "统计字段"],
          ["aggregate", "汇总字段"],
        ]
          .map(
            ([k, t]) =>
              `<label><input data-field="${k}" type="checkbox" ${f[k] ? "checked" : ""}>${t}</label>`,
          )
          .join("")}</div></div></details>`,
    )
    .join("");
}
function editor(entity, id = "", prefill = {}) {
  const r = D[entity].find((x) => x.id === id) || { name: "", ...prefill };
  let html = input("name", "名称 <em>*</em>", r.name);
  const text = (k, l, def = "", full = false) =>
      input(k, l, r[k] ?? def, "text", [], full),
    area = (k, l, def = "", full = true) =>
      input(k, l, r[k] ?? def, "textarea", [], full),
    select = (k, l, values, def) =>
      input(k, l, r[k] ?? def ?? values[0], "select", values);
  if (entity === "resources") html = resourceEditorHtml(r);
  if (entity === "knowledge")
    html +=
      select("category", "资讯栏目 / 知识分类", [
        ...newsCategories,
        "技术规范",
        "业务手册",
        "案例经验",
        "数据字典",
      ]) +
      text("source", "发布单位 / 来源", "业务示例知识库") +
      text("tags", "分类标签（英文逗号分隔）") +
      area("body", "文档正文（空行分段生成切片）") +
      area("relations", "关系说明（实体网络在下方维护）", "") +
      `<div class="full"><div class="section-title"><h3>切片预览</h3>${btn("刷新切片预览", "previewChunks", "", "small", "eye")}</div><div id="chunk-preview">${(r.chunks || []).map((c, i) => `<div class="chunk"><small>片段 ${i + 1}</small><p>${esc(c.text)}</p></div>`).join("") || '<p class="muted">填写正文后可预览切片，修改正文即可调整切片内容。</p>'}</div></div>`;
  if (entity === "indicators")
    html +=
      text("category", "业务分类", "耕地保护") +
      text("unit", "指标单位", "公顷") +
      select(
        "formula",
        "计算模型",
        [
          ["sum", "求和 SUM"],
          ["average", "平均值 AVG"],
          ["count", "计数 COUNT"],
          ["max", "最大值 MAX"],
        ],
        "sum",
      ) +
      text("values", "示例数据（英文逗号分隔）", "128.6,96.4,175") +
      select("region", "统计区域", D.regions) +
      text("period", "统计周期", "2026年") +
      select(
        "resourceId",
        "关联库表",
        D.resources.map((x) => [x.id, x.name]),
      ) +
      text("field", "关联字段", "area") +
      area("caliber", "统计口径与计算说明") +
      area("description", "指标业务定义");
  if (entity === "corpora")
    html +=
      select("type", "语料类型", ["问答样例", "提示词模板", "SQL 模板", "API 模板"]) +
      text("scene", "适用场景", "资源检索") +
      text("category", "业务分类", "地灾防治") +
      area("body", "问题 / 模板内容") +
      text("variables", "参数定义（英文逗号分隔）", "", true) +
      area("answer", "标准答案（问答样例必填）") +
      binding("resourceIds", "关联资源", "resources", r.resourceIds || "");
  if (entity === "agents")
    html +=
      select("category", "能力场景", ["资源检索", "知识问答", "指标分析"]) +
      area("description", "能力描述") +
      text("question", "推荐问题", "找最近的地灾巡查记录表", true) +
      select(
        "icon",
        "能力图标",
        [
          ["sparkles", "智能检索"],
          ["book", "知识问答"],
          ["chart", "指标分析"],
        ],
        "sparkles",
      ) +
      select(
        "color",
        "卡片配色",
        [
          ["green", "青绿"],
          ["blue", "天空蓝"],
          ["purple", "浅紫"],
        ],
        "green",
      ) +
      `<div class="full"><div class="section-title"><h3>能力编排</h3>${btn("添加步骤", "addStep", "", "small", "plus")}</div><div id="agent-steps">${(
        r.steps || "识别条件\n检索资源\n展示结果\n发起申请"
      )
        .split("\n")
        .map((step) => stepRow(step))
        .join(
          "",
        )}</div><small class="muted">按顺序实际执行；没有检索节点将没有检索结果，没有展示节点将不返回结果。协作节点可调用其他智能体。</small></div>` +
      binding("resourceIds", "可用资源", "resources", r.resourceIds || "") +
      binding("knowledgeIds", "关联知识", "knowledge", r.knowledgeIds || "") +
      binding("indicatorIds", "关联指标", "indicators", r.indicatorIds || "") +
      binding("templateIds", "关联语料", "corpora", r.templateIds || "") +
      input("memory", "启用用户记忆", r.memory ?? true, "check");
  if (entity === "templates")
    html +=
      select("type", "适用资源类型", [
        "数据库表",
        "图层服务",
        "工具服务",
        "知识文档",
      ]) +
      area("description", "说明") +
      area("fields", "模板字段（英文逗号分隔）", "名称,同义词,业务解释");
  if (entity === "dictionaries")
    html +=
      text("code", "字典编码", "REGION") +
      text("aliases", "字典别名") +
      area("items", "字典项（每行：编码:名称:值）", "150100:呼和浩特市:150100");
  if(entity!=="resources")html += advancedEditor(entity, r);
  modal(
    (id ? "配置" : "新建") + " · " + meta[entity][0],
    `<div class="editor-info">${tag(r.status || "草稿")}<span>${id ? `当前 v${r.version}.0 · ` : ""}保存草稿后，需发布才能影响前台</span></div>${id?intelligenceUI.impact(entity,id):""}<form id="editor-form" data-entity="${entity}" data-id="${id}" data-rev="${r.rev || 0}"><div class="form-grid">${html}</div><div class="form-footer sticky"><span class="muted">版本与发布状态独立管理</span><button type="button" class="btn" data-action="close">取消</button><button type="submit" class="btn primary">${icon("check")}保存草稿</button></div></form>`,
    true,
  );
  if(entity==="resources")$("#dialog").classList.add("resource-workspace");
  if(entity==="knowledge" && route==="articles"){
    ['relations','entities','edges','chunkSize'].forEach(key=>$('#editor-form [name='+key+']')?.closest('label')?.setAttribute('hidden',''));
    ['chunk-preview','clean-output','graph-output'].forEach(key=>$('#'+key)?.closest('.full')?.setAttribute('hidden',''));
    $$('#editor-form h3').filter(h=>h.textContent==='知识处理与图谱').forEach(h=>h.hidden=true);
  }
}
function stepRow(step = "识别条件") {
  return `<div class="step-row"><span class="step-dot"></span><select data-step>${opts(["识别条件", "检索资源", "展示结果", "发起申请", "理解问题", "检索知识", "回答并引用", "识别指标", "核对口径", "示例试算", "调用知识智能体", "调用指标智能体", "执行语料模板"], step)}</select>${btn("上移", "upStep", "", "small", "up")}${btn("移除", "removeStep", "", "small", "x")}</div>`;
}
function versionsDialog(entity, id) {
  const r = D[entity].find((x) => x.id === id),
    versions = [
      ...(r.versions || []),
      ...(r.published ? [r.published] : []),
    ].reverse();
  modal(
    r.name + " · 版本记录",
    versions.length
      ? versions
          .map(
            (v) =>
              `<details class="version-block"><summary><span class="version">v${v.version}.0</span> ${esc(v.name)} <small>${fmt(v.updated)}</small></summary>${detailGrid(
                Object.entries(v)
                  .filter(([k, v]) =>
                    [
                      "unit",
                      "caliber",
                      "body",
                      "aliases",
                      "description",
                      "steps",
                      "period",
                      "values",
                      "source",
                    ].includes(k),
                  )
                  .map(([k, v]) => [
                    {
                      unit: "单位",
                      caliber: "统计口径",
                      body: "正文/模板",
                      aliases: "同义词",
                      description: "说明",
                      steps: "编排步骤",
                      period: "周期",
                      values: "试算数据",
                      source: "来源",
                    }[k],
                    v,
                  ]),
              )}</details>`,
          )
          .join("")
      : empty("尚未发布版本"),
    true,
  );
  if(entity==='knowledge' && r.channelHistory?.length){
    $('#dialog .dialog-body').insertAdjacentHTML('afterbegin',`<h3>渠道变更记录</h3>${r.channelHistory.slice().reverse().map(h=>`<p>${esc(h.at)} · ${esc(h.actor)} · ${{portal:'门户资讯',index:'知识索引',all:'全部渠道'}[h.channel]||esc(h.channel)} · ${h.enabled?'发布':'退出'} v${h.version}</p>`).join('')}<h3>文档版本</h3>`);
  }
}
function trialDialog(entity, id) {
  const r = D[entity].find((x) => x.id === id);
  modal(
    "试运行 · " + r.name,
    `<div class="notice">${icon("sparkles")}使用当前配置运行本地示例数据与规则；不调用生产数据库或真实模型。</div><form id="trial-form" data-entity="${entity}" data-id="${id}">${
      ["knowledge", "agents"].includes(entity)
        ? input("question", "检索关键词", "耕地")
        : entity === "corpora"
          ? csvIds(r.variables)
              .map((k) =>
                input(
                  k,
                  esc(k),
                  k === "region" ? "呼和浩特市" : "找地灾巡查记录表",
                ),
              )
              .join("")
          : ""
    }<div class="form-footer"><button class="btn primary" type="submit">运行示例 ${icon("arrow")}</button></div></form><div id="trial-output"></div>`,
    true,
  );
}
let resumeFrom = "";
async function sendQuestion(question, context) {
  if (pending) return;
  let targetAgent = selectedAgent;
  if (!sessionId && !resumeFrom && selectedAgent === "a1") {
    if (/什么是|政策|解释/.test(question)) targetAgent = "a2";
    else if (/指标/.test(question)) targetAgent = "a3";
  }
  const agent = D.agents.find((a) => a.id === targetAgent);
  if (!agent) return toast("该智能体已停用");
  selectedAgent = targetAgent;
  if(pending)return;
  const controller = new AbortController();
  pending = { question, controller };
  renderAssistant();
  bindForms();
  try {
    await new Promise((r) => setTimeout(r, 500));
    if (controller.signal.aborted) return;
    const result = await api(
      "chat",
      { question, context, sessionId, agentId: selectedAgent, resumeFrom, businessContext, spatialContext:null },
      controller.signal,
    );
    if(controller.signal.aborted||pending?.controller!==controller)return;
    sessionId = result.id;
    resumeFrom = "";
    const fresh=await api();
    if(controller.signal.aborted||pending?.controller!==controller)return;
    D=fresh;
    if (/加入.*申请|加入.*清单/.test(question)) {
      for (const id of result.messages.at(-1).resourceIds) {
        if (
          D.resources.some((r) => r.id === id && r.access === "可申请") &&
          !cart.includes(id)
        )
          cart.push(id);
      }
      toast("相关可申请资源已加入清单，请核对后提交");
    }
  } catch (e) {
    if (e.name !== "AbortError") {
      toast(e.message);
      modal(
        "本次检索未完成",
        `<p>${esc(e.message)}</p>${btn("重新尝试", "prompt", question, "primary", "refresh")}`,
      );
    }
  } finally {
    if (pending?.controller === controller) pending = null;
    if (route === "assistant") {
      renderAssistant();
      bindForms();
    }
  }
}
async function mutate(action, payload, done = "已保存") {
  const result = await api(action, payload);
  await load();
  renderPage();
  if (done) toast(done);
  return result;
}
async function perform(action, id, el) {
  if(await intelligenceUI.action(action,id))return;
  if(["newChat","useAgent","resume"].includes(action)){pending?.controller.abort();pending=null;}
  if(await integrationUI.action(action,id,el))return;
  if(await operationsCenterUI.action(action,id,el))return;
  if(await centersUI.action(action,id,el))return;
  if(await operationsUI.action(action,id,el))return;
  if(await managementUI.action(action,id,el))return;
  if(await publicUI.action(action,id,el))return;
  if(await platformUI.action(action,id,el))return;
  if (await portalAction(action, id, el)) return;
  if (await advancedAction(action, id, el)) return;
  if(await designAction(action,id,el))return;
  switch (action) {
    case "navigate":
      nav(id);
      break;
    case "menu":
      document.body.classList.toggle("nav-open");
      break;
    case "close":
      closeModal();
      break;
    case "refresh":
      await load();
      shell();
      toast("数据已更新");
      break;
    case "notifications":
      nav(`/${mode}/${mode === "admin" ? (permittedAdminNav().some(n=>n[0]==="approvals")?"approvals":"overview") : "applications"}`);
      break;
    case "switchMode":
      nav(mode === "front" ? "/admin/overview" : "/front/home");
      break;
    case "identity":
      platformUI.loginDialog();
      break;
    case "selectUser":
      platformUI.loginDialog(id);
      break;
    case "resource":
      resourceDetail(id);
      break;
    case "preview":
      previewResource(id);
      break;
    case "tc-apply":
      if(!cart.includes(id))cart.push(id);
      cartDialog();
      break;
    case "addCart":
      if (!cart.includes(id)) cart.push(id);
      toast("已加入申请清单");
      if (route === "assistant") { renderAssistant(); bindForms(); }
      else renderPage();
      if ($("#dialog").open) resourceDetail(id);
      break;
    case "removeCart":
      if(mode==='admin'&&route==='integration'){
      const last=sessionStorage.getItem('ig-last-'+D.user.id)||'/admin/integration-workbench';
      const valid=integrationNav.slice(0,3).some(([key])=>last.split('?')[0]==='/admin/'+key&&permittedAdminNav().some(n=>n[0]===key));
      location.replace('#'+(valid?last:'/admin/integration-workbench'));return;
    }
    if(mode==='admin'&&integrationNav.slice(0,3).some(n=>n[0]===route)&&permittedAdminNav().some(n=>n[0]===route))sessionStorage.setItem('ig-last-'+D.user.id,location.hash.slice(1));
    cart = cart.filter((x) => x !== id);
      requestKey = randomUUID();
      cartDialog();
      break;
    case "cart":
      cartDialog();
      break;
    case "application":
      applicationDetail(id);
      break;
    case "decision": {
      const [aid, rid] = id.split(":"),
        a = D.applications.find((a) => a.id === aid),
        r = a.items.find((i) => i.resourceId === rid);
      modal(
        "模拟审批 · " + r.name,
        `<form id="decision-form" data-id="${aid}" data-resource="${rid}" data-rev="${a.rev}">${input("decision", "审批结果", "已通过", "select", ["已通过", "已驳回"])}${input("approvedUntil", "核准截止日期（不得超过申请期限）", a.validUntil, "date")}${input("note", "办理说明（至少5个字）", "", "textarea")}<div class="form-footer"><button class="btn primary">确认办理</button></div></form>`,
      );
      break;
    }
    case "supplement": {
      const a = D.applications.find((a) => a.id === id);
      modal(
        "补充申请说明",
        `<form id="supplement-form" data-id="${id}" data-rev="${a.rev}">${input("note", "补充说明", "", "textarea")}<div class="form-footer"><button class="btn primary">保存说明</button></div></form>`,
      );
      break;
    }
    case "cancel":
      modal(
        "撤回申请",
        `<p>撤回后，本次申请将结束，可重新选择资源发起申请。</p>${btn("确认撤回", "confirmCancel", id, "danger")}`,
      );
      break;
    case "confirmCancel":
      await mutate(
        "cancel",
        { id, rev: D.applications.find((a) => a.id === id).rev },
        "申请已撤回",
      );
      closeModal();
      break;
    case "agentDetail": {
      const a = D.agents.find((a) => a.id === id);
      modal(
        a.name,
        `<div class="agent-detail"><span class="tile large ${esc(a.color)}">${icon(a.icon)}</span><p>${esc(a.description)}</p>${detailGrid(
          [
            ["能力场景", a.category],
            ["已发布版本", `v${a.version}.0`],
            ["试试这样问", a.question],
          ],
        )}${btn("开始使用", "useAgent", a.id, "primary", "arrow")}</div>`,
      );
      break;
    }
    case "useAgent":
      businessContext=null;
      selectedAgent = id;
      sessionId = "";
      closeModal();
      if (route === "assistant") renderPage();
      else nav("/front/assistant");
      break;
    case "newChat":
      businessContext=null;
      sessionId = "";
      renderPage();
      break;
    case "resume": {
      const s = D.sessions.find((s) => s.id === id);
      if (!s) return;
      sessionId = id;
      businessContext = s.businessContext || null;
      selectedAgent = s.agentId;
      if (route === "assistant") renderPage();
      else nav("/front/assistant");
      break;
    }
    case "prompt":
      closeModal();
      if (route !== "assistant") {
        nav("/front/assistant");
        await new Promise((r) => setTimeout(r, 100));
      }
      await sendQuestion(id);
      break;
    case "stop":
      pending?.controller.abort();
      pending = null;
      renderPage();
      toast("已停止本次响应");
      break;
    case "copyAnswer": {
      const m = currentSession()?.messages.find((m) => m.id === id);
      await navigator.clipboard.writeText(m.text);
      toast("回答已复制");
      break;
    }
    case "citation": {
      const [mid, index] = id.split(":"),
        c = currentSession()?.messages.find((m) => m.id === mid).citations[
          +index
        ];
      modal(
        c.name,
        `<p class="muted">本次回答引用的版本：v${c.version}.0 · 历史引用快照</p>${c.chunks.map((chunk, i) => `<div class="chunk"><small>片段 ${i + 1} · ${esc(chunk.id)}</small><p>${esc(chunk.text)}</p></div>`).join("")}`,
        true,
      );
      break;
    }
    case "feedback":
      modal(
        "回答反馈",
        `<form id="feedback-form" data-id="${id}"><p>你的反馈将进入后台改进队列。</p>${input("note", "请描述问题或改进建议", "", "textarea")}<div class="form-footer"><button class="btn primary">提交反馈</button></div></form>`,
      );
      break;
    case "tab":
      adminTab = id;
      query = "";
      filter = "全部";
      page = 1;
      renderPage();
      break;
    case "corpusTab":
      filter = id;
      page = 1;
      renderPage();
      break;
    case "prev":
      page = Math.max(1, page - 1);
      renderPage();
      break;
    case "next":
      page = Math.min(+id, page + 1);
      renderPage();
      break;
    case "new":
      editor(id);
      break;
    case "edit": {
      const [e, rid] = id.split(":");
      editor(e, rid);
      break;
    }
    case "versions": {
      const [e, rid] = id.split(":");
      versionsDialog(e, rid);
      break;
    }
    case "trial": {
      const [e, rid] = id.split(":");
      trialDialog(e, rid);
      break;
    }
    case "publish":
    case "disable":
    case "delete": {
      const [e, rid] = id.split(":"),
        r = D[e].find((x) => x.id === rid);
      modal(
        action === "publish"
          ? "发布新版本"
          : action === "disable"
            ? "停用确认"
            : "删除草稿",
        `<p>${esc(r.name)}</p>${intelligenceUI.impact(e,rid)}${e==="agents"&&action==="publish"?`<p>发布前请核对关联资产和评测结果。${btn("评测此智能体","ia-evaluate",rid,"small")}</p>`:""}<p class="muted">${action === "publish" ? "发布后，新查询将使用当前配置。" : action === "disable" ? "停用后前台无法继续访问此能力，历史记录仍保留。" : "删除后无法恢复，请确认草稿未被引用。"}</p>${btn(action === "publish" ? "确认发布" : action === "disable" ? "确认停用" : "确认删除", "confirmMutation", `${action}:${id}`, action === "publish" ? "primary" : "danger")}`,
      );
      break;
    }
    case "confirmMutation": {
      const [act, e, rid] = id.split(":");
      await mutate(
        act,
        { entity: e, id: rid, rev: D[e].find((r) => r.id === rid).rev },
        act === "publish" ? "版本已发布，前台刷新后生效" : "操作已完成",
      );
      closeModal();
      break;
    }
    case "duplicate": {
      const [e, rid] = id.split(":");
      await mutate(
        "duplicate",
        { entity: e, id: rid, rev: D[e].find((r) => r.id === rid).rev },
        "已创建草稿副本",
      );
      break;
    }
    case "addField":
      $("#field-rows").insertAdjacentHTML(
        "beforeend",
        resourceFields([
          { name: "", label: "", type: "varchar", query: true, display: true },
        ]),
      );
      break;
    case "removeField":
      el.closest(".field-row").remove();
      break;
    case "suggestFields": {
      const result = await api("annotationSuggest", { fields: readFields() });
      $("#field-rows").innerHTML = resourceFields(result.fields);
      toast(result.mode);
      break;
    }
    case "previewChunks": {
      const cleaned = await api("cleanPreview", { body: $('[name="body"]').value });
      const size = Math.min(2000, Math.max(100, +$('[name="chunkSize"]').value || 400));
      const chunks = cleaned.body.split(/\n\s*\n/).flatMap(block => Array.from({length:Math.ceil(block.length/size)}, (_,i) => block.slice(i*size,(i+1)*size)));
      $("#chunk-preview").innerHTML = chunks.map((s,i)=>`<div class="chunk"><small>片段 ${i+1}</small><p>${esc(s)}</p></div>`).join("");
      break;
    }
    case "addStep":
      $("#agent-steps").insertAdjacentHTML("beforeend", stepRow());
      break;
    case "upStep": {
      const row = el.closest(".step-row");
      if (row.previousElementSibling)
        row.parentNode.insertBefore(row, row.previousElementSibling);
      break;
    }
    case "removeStep":
      if ($$(".step-row").length > 1) el.closest(".step-row").remove();
      else toast("至少保留一个步骤");
      break;
    case "importDoc":
      importDialog();
      break;
    case "memory": {
      const m = D.memories.find((m) => m.id === id);
      modal(m.name, preferenceForm(m, true), true);
      break;
    }
    case "clearSummary":
      $('#preferences-form [name="summary"]').value = "";
      toast("摘要已清空，保存偏好后生效");
      break;
    case "feedbackConvert":
    case "feedbackResolve":
      await mutate(
        action,
        { id },
        action === "feedbackConvert"
          ? "已创建待审样例，请修正答案后发布"
          : "反馈已标记为已处理",
      );
      break;
    case "callDetail": {
      const c = D.calls.find((c) => c.id === id);
      modal(
        "调用详情",
        detailGrid([
          ["调用问题", c.question],
          ["智能体", c.agent],
          ["版本", `v${c.version}.0`],
          ["结果", c.status],
          ["资源标识", c.resourceIds.join(", ")],
          ["知识引用", c.citations.join(", ")],
          ["命中样例", c.sampleIds.join(", ")],
        ]) +
          `${c.trace ? traceView(c.trace,true) : `<p>历史记录：${esc(c.steps.join(" → "))}</p>`}<p class="muted">显示本地规则执行结果，不是模型思维过程。</p>`,
      );
      break;
    }
    case "scope": {
      const u = D.users.find((u) => u.id === id);
      modal(
        "调整访问范围 · " + u.name,
        `<form id="scope-form" data-id="${id}">${input("region", "可访问区域", u.region, "select", D.regions)}<div class="form-footer"><button class="btn primary">保存访问范围</button></div></form>`,
      );
      break;
    }
    case "reset":
      modal(
        "重置演示数据",
        `<p>此操作将清除当前原型所有自定义记录，恢复初始数据。</p><form id="reset-form">${input("confirm", "输入“重置演示数据”确认")}<div class="form-footer"><button class="btn danger">确认重置</button></div></form>`,
      );
      break;
  }
  bindForms();
}
function valuesOf(form) {
  return Object.fromEntries(new FormData(form));
}
function handleForm(selector, fn) {
  const form = $(selector);
  if (!form) return;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const b =
      form.querySelector('[type="submit"]') ||
      form.querySelector('button:not([type="button"])');
    if (form.dataset.saving) return;
    form.dataset.saving = "1";
    if (b) b.disabled = true;
    form.querySelector(".form-error")?.remove();
    try {
      await fn(form);
    } catch (err) {
      const error = document.createElement("p");
      error.className = "form-error";
      error.setAttribute("role", "alert");
      error.textContent = err.message;
      form.append(error);
      toast(err.message);
    } finally {
      delete form.dataset.saving;
      if (b) b.disabled = false;
    }
  };
}
function bindForms() {
  handleForm("#portal-search", async (form) => { await portalAsk(valuesOf(form).question); });
  bindAdvancedForms();
  const search = $("#list-search");
  if (search)
    search.oninput = () => {
      const pos = search.selectionStart;
      query = search.value;
      page = 1;
      renderPage();
      $("#list-search")?.focus();
      $("#list-search")?.setSelectionRange(pos, pos);
    };
  const filt = $("#list-filter");
  if (filt)
    filt.onchange = () => {
      filter = filt.value;
      page = 1;
      renderPage();
    };
  handleForm("#home-ask", async (form) => {
    const q = valuesOf(form).question;
    nav("/front/assistant");
    await new Promise((r) => setTimeout(r, 100));
    await sendQuestion(q);
  });
  handleForm("#service-ask-form", async (form) => {
    const question=valuesOf(form).question.trim();
    if(!question)return toast("请先描述你的办事需求");
    businessContext=null;
    await portalAsk(question);
  });
  handleForm("#chat-form", async (form) => {
    const v = valuesOf(form);
    await sendQuestion(v.question, !sessionId && /继续上次|接续/.test(v.question) ? undefined : { region: v.region, period: v.period });
  });
  const textarea = $("#chat-form textarea");
  if (textarea)
    textarea.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        textarea.form.requestSubmit();
      }
    };
  handleForm("#apply-form", async (form) => {
    const a = await mutate(
      "apply",
      { ...valuesOf(form), resourceIds: cart, requestId: requestKey },
      "申请已提交",
    );
    cart = [];
    requestKey = randomUUID();
    closeModal();
    if (route === "assistant") { renderPage(); applicationDetail(a.id); }
    else { nav("/front/applications"); setTimeout(() => applicationDetail(a.id), 150); }
  });
  handleForm("#decision-form", async (form) => {
    await mutate(
      "decide",
      {
        ...valuesOf(form),
        id: form.dataset.id,
        rev: +form.dataset.rev,
        resourceId: form.dataset.resource,
      },
      "办理结果已同步",
    );
    applicationDetail(form.dataset.id);
  });
  handleForm("#supplement-form", async (form) => {
    await mutate(
      "supplement",
      { ...valuesOf(form), id: form.dataset.id, rev: +form.dataset.rev },
      "补充说明已保存",
    );
    applicationDetail(form.dataset.id);
  });
  handleForm("#preferences-form", async (form) => {
    await mutate(
      "preferences",
      {
        ...valuesOf(form),
        userId: form.dataset.id,
        rev: +form.dataset.rev,
        enabled: form.enabled.checked,
      },
      "偏好已保存，新会话将采用最新配置",
    );
    if ($("#dialog").open) closeModal();
  });
  handleForm("#feedback-form", async (form) => {
    await mutate(
      "feedback",
      { ...valuesOf(form), sessionId, messageId: form.dataset.id },
      "反馈已提交",
    );
    closeModal();
  });
  handleForm("#editor-form", async (form) => {
    let v = valuesOf(form),
      entity = form.dataset.entity;
    for (const select of form.querySelectorAll("select[multiple]"))
      v[select.name] = [...select.selectedOptions]
        .map((o) => o.value)
        .join(",");
    if (entity === "resources") {
      v.relations = csvIds(v.relations);
      v.fields = $$(".field-row").map((row) =>
        Object.fromEntries(
          [...row.querySelectorAll("[data-field]")].map((x) => [
            x.dataset.field,
            x.type === "checkbox" ? x.checked : x.value,
          ]),
        ),
      );
    }
    if (entity === "agents") {
      v.steps = $$("[data-step]")
        .map((x) => x.value)
        .join("\n");
      v.memory = form.memory.checked;
    }
    await mutate(
      "save",
      {
        entity,
        id: form.dataset.id || undefined,
        rev: +form.dataset.rev,
        values: v,
      },
      "草稿已保存，请发布版本使前台生效",
    );
    closeModal();
  });
  handleForm("#trial-form", async (form) => {
    const v = valuesOf(form),
      entity = form.dataset.entity;
    const result = await api("trial", {
      entity,
      id: form.dataset.id,
      question: v.question,
      params: v,
    });
    $("#trial-output").innerHTML =
      entity === "indicators"
        ? renderIndicatorResult(result)
        : entity === "knowledge"
          ? result.chunks
              .map(
                (c, i) =>
                  `<div class="chunk"><small>命中片段 ${i + 1}</small><p>${esc(c.text)}</p></div>`,
              )
              .join("") || empty("没有命中片段", "修改关键词后再次测试。")
          : entity === "agents"
            ? `<p>${esc(result.text)}</p>${traceView(result.trace, true)}${result.indicators.map(renderIndicatorResult).join("")}`
            : resultTable(result);
  });
  handleForm("#import-form", async (form) => {
    const files = [...form.file.files];
    if (!files.length || files.length > 20) throw Error("请选择 1–20 个文件");
    const entries = await Promise.all(files.map(async file => file.size > 200*1024 ? {name:file.name,error:"文件超过 200KB"} : {name:file.name,body:await file.text()}));
    const result = await api("importBatch", {...valuesOf(form), files:entries});
    await load(); renderPage(); showBatch(result);
  });
  handleForm("#scope-form", async (form) => {
    await mutate(
      "userScope",
      { id: form.dataset.id, ...valuesOf(form) },
      "访问范围已更新",
    );
    closeModal();
  });
  handleForm("#reset-form", async (form) => {
    await mutate("reset", valuesOf(form), "已恢复初始演示数据");
    sessionId = "";
    cart = [];
    closeModal();
    shell();
  });
  handleForm("#tool-form", async (form) => {
    $("#tool-result").innerHTML =
      `<div class="notice">示例分析已完成：${esc(valuesOf(form).region)}，识别 3 个演示变化单元。真实算法尚未接入。</div>`;
  });
}
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-action]");
  if (!el || el.disabled) return;
  if (el.tagName === "A") e.preventDefault();
  try {
    await perform(el.dataset.action, el.dataset.id || "", el);
  } catch (err) {
    toast(err.message);
  }
});
$("#dialog").addEventListener("click", (e) => {
  if (e.target === $("#dialog")) {
    const r = e.target.getBoundingClientRect();
    if (
      e.clientX < r.left ||
      e.clientX > r.right ||
      e.clientY < r.top ||
      e.clientY > r.bottom
    )
      closeModal();
  }
});
let routeVersion = 0;
async function routeChange() {
  const version = ++routeVersion;
  window.appReady = false;
  const parts = location.hash.split("?")[0].replace(/^#\/?/, "").split("/");
  const previous = mode;
  mode = parts[0] === "admin" ? "admin" : "front";
  route = parts[1] || (mode === "admin" ? "overview" : "home");
  routeId = decodeURIComponent(parts[2] || "");
  if(mode==='front') route=({catalog:"data",tools:"capabilities"})[route]||route;
  if(mode==='front' && route==='services' && !routeId && new URLSearchParams(location.hash.split('?')[1]).get('tab')==='assistant'){
    location.replace('#/front/assistant');
    return;
  }
  if(route==='center-operations'){location.replace('#/admin/operations/overview');return;}
  const migrated=legacyIntegration(location.hash);
  if(migrated){location.replace('#'+migrated);return;}
  closeModal();
  integrationUI.reset();
  publicUI.reset();
  platformUI.reset();
pending?.controller.abort();pending=null;
  query = "";
  filter = "全部";
  page = 1;
  adminTab = "";
  document.body.classList.remove("nav-open");
  userId = sessionStorage.getItem("onemap-user") || "u1";

  if (previous !== mode) {
    pending?.controller.abort();
    pending = null;
  }
  try {
    const routeData = await getBootstrap();
    if (version !== routeVersion) return;
    D = routeData;
    if(mode==='admin'&&route==='integration'){
      const last=sessionStorage.getItem('ig-last-'+D.user.id)||'/admin/integration-workbench';
      const valid=integrationNav.slice(0,3).some(([key])=>last.split('?')[0]==='/admin/'+key&&permittedAdminNav().some(n=>n[0]===key));
      location.replace('#'+(valid?last:'/admin/integration-workbench'));return;
    }
    if(mode==='admin'&&integrationNav.slice(0,3).some(n=>n[0]===route)&&permittedAdminNav().some(n=>n[0]===route))sessionStorage.setItem('ig-last-'+D.user.id,location.hash.slice(1));
    cart = cart.filter((id) => D.resources.some((r) => r.id === id && r.access === "可申请"));
    if (
      mode === "admin" &&
      D.user.role === "资源审批人员" &&
      route === "overview"
    ) {
      nav("/admin/approvals");
      return;
    }
    shell();
    if (mode === "front") {window.scrollTo(0, 0);api("portal.visit",{route:"/front/"+route+(routeId?"/"+routeId:"")}).catch(()=>{});}
    window.appReady = true;
  } catch (e) {
    if (version !== routeVersion) return;
    if(!D){try{const r=await fetch("/api/bootstrap",{headers:{"X-Demo-User":userId,"X-Demo-Mode":"front"}});D=await r.json();}catch{}}
    $("#app").innerHTML =
      `<div class="boot"><h2>无法进入当前页面</h2><p>${esc(e.message)}</p>${btn("选择演示身份", "identity", "", "primary", "user")}<a href="#/front/home" class="btn">返回门户</a></div>`;
  }
}
window.addEventListener("hashchange", routeChange);
window.addEventListener("focus", async () => {
  if (!D || $("#dialog").open || pending) return;
  try {
    await load(false);
    if (["applications", "approvals"].includes(route)) renderPage();
  } catch {}
});
routeChange();

// Capability workspaces share the existing modal, form and request lifecycle.
function advancedEditor(entity, r) {
  const text=(k,l,d="")=>input(k,l,r[k]??d), area=(k,l,d="")=>input(k,l,r[k]??d,"textarea",[],true), select=(k,l,options,d)=>input(k,l,r[k]??d??options[0],"select",options);
  let html="";
  if (["resources","knowledge","indicators","agents"].includes(entity)) {
    html+=`<h3 class="full">资产访问控制</h3>`;
    if(entity!=="resources") html+=select("visibility","访问范围",["业务用户","管理员"]);
    html+=text("departments","可访问部门（逗号分隔，空表示全部）");
    if(["knowledge","agents"].includes(entity))html+=select("region","适用区域",D.regions,"全区");
  }
  if(entity==="resources") html+=`<h3 class="full">标准描述与数据来源</h3>`+
    select("subtype","资源子类型",["属性表","空间表","视图","图层服务","工具服务","知识文档"])+select("sourceType","来源类型",["库表","服务","接口","文件"])+
    `<div class="full">${btn("应用所选模板字段", "applyTemplate", "", "small", "layers")}<small>按字段名合并，保留已填写字段；保存后发布生效。</small></div>`+
    area("relationRules","关系规则：类型|目标资源标识|本字段|目标字段","")+
    `<p class="full muted">例如：表关联|r2|region_code|region_code；图层数据源|r2||。资源标识见目录详情。</p>`+
    text("dataSource","数据源名称 / 提供方系统","")+select("serviceProtocol","服务类型",["本地示例","OGC WMS","OGC WMTS","OGC WFS","REST","文件下载"])+text("serviceUrl","服务 HTTPS 地址（授权后可打开）","")+text("downloadUrl","数据包 HTTPS 下载地址（可空）","")+
    text("sqlName","本地示例 SQL 表名","")+area("dataRows","示例数据 CSV（首行为列名；period、region 用于筛选）","");
  if(entity==="knowledge") html+=`<h3 class="full">知识处理与图谱</h3>`+
    input("chunkSize","切片长度（100–2000 字）",r.chunkSize||400,"number")+
    `<div class="full">${btn("清洗与标准化预览", "cleanDoc", "", "small", "sparkles")}<small>规范全半角、空白与重复段落；确认后替换正文。</small><div id="clean-output"></div></div>`+
    area("entities","实体（每行：标识|名称|类型）","")+area("edges","关系（每行：起点标识|关系名称|终点标识）","")+
    `<div class="full">${btn("预览关系网络", "previewGraph", "", "small", "link")}<div id="graph-output">${r.graph?graphView(r.graph):""}</div>${r.pipeline?pipelineView(r.pipeline):""}<small>向量索引采用本地字符二元特征，可执行相似度检索；未接入语义嵌入模型。</small></div>`;
  if(entity==="indicators") html+=`<h3 class="full">动态计算与业务依据</h3>`+
    select("dataMode","数据来源",[["manual","手动试算"],["table","关联示例数据表"],["composite","复合指标表达式"]],"manual")+
    text("expression","复合表达式（使用指标标识）","")+
    `<p class="full muted">例如 i_area / i_target * 100。表模式读取已发布资源的 CSV；复合模式依赖已发布指标；手动模式保留上方示例数字。</p>`+
    binding("knowledgeIds","指标知识依据","knowledge",r.knowledgeIds||"");
  if(entity==="corpora") html+=`<h3 class="full">执行与质量验证</h3>`+
    area("outputTemplate","规则回答模板（提示词类型使用）","")+
    `<p class="full muted">可用变量：{{question}}、{{region}}、{{count}}、{{resources}}、{{topic}}、{{answer}}。提示词正文作为执行指令记录，回答模板控制本地规则输出。API 模板正文填写 resources.search；SQL 仅执行本地授权表的 SELECT。</p>`+
    select("agentId","适用评测智能体",[["","任意智能体"],...D.agents.map(a=>[a.id,a.name])],"")+
    area("expectedAnswer","预期答案片段（空则使用标准答案）","")+text("expectedResources","预期资源标识集合（英文逗号分隔）","")+area("expectedSteps","预期操作序列（每行一个步骤）","");
  if(entity==="agents") html+=`<h3 class="full">协作节点绑定</h3>`+
    select("knowledgeAgentId","调用知识智能体",[["","默认政策知识助手"],...D.agents.filter(a=>a.id!==r.id).map(a=>[a.id,a.name])],"")+
    select("indicatorAgentId","调用指标智能体",[["","默认指标分析助手"],...D.agents.filter(a=>a.id!==r.id).map(a=>[a.id,a.name])],"");
  if(entity==="templates") html+=area("fieldSchema","字段定义（每行：字段名|中文名|类型|同义词）","region_code|行政区代码|varchar|区划编码\narea|面积|decimal|用地面积");
  return html;
}
function managementTools(e) {
  if(e==="knowledge")return btn("处理批次","batches","","small","clock");
  if(e==="agents")return `<a class="btn small" href="#/admin/intelligence-evaluations">评测与回归</a>`;
  if(e==="corpora")return btn("评测与回归","evaluations","","small","chart")+btn("导出训练样例","exportCorpus","","small","download");
  return "";
}
function readFields(){return $$("#field-rows .field-row").map(row=>Object.fromEntries([...row.querySelectorAll("[data-field]")].map(x=>[x.dataset.field,x.type==="checkbox"?x.checked:x.value])));}
function pipelineView(rows){return `<div class="pipeline">${rows.map((r,i)=>`<span><b>${i+1}</b>${esc(r.name)} ${tag(r.status)}</span>`).join("")}</div>`;}
function traceView(trace,open=false){return `<details class="execution-trace" ${open?"open":""}><summary>执行过程 · ${trace.length} 个节点</summary>${trace.map((t,i)=>`<div class="trace-node"><div><b>${i+1}. ${esc(t.step)}</b>${tag(t.status)}<small>${esc(t.agent)} · v${t.version||1}</small></div><details><summary>输入 / 输出</summary><pre>${esc(typeof t.input==="string"?t.input:JSON.stringify(t.input,null,2))}</pre><pre>${esc(typeof t.output==="string"?t.output:JSON.stringify(t.output,null,2))}</pre></details>${t.children?traceView(t.children):""}</div>`).join("")}</details>`;}
function resultTable(r){return `<div class="chunk"><small>${esc(r.name||r.mode)}</small>${r.preview?`<pre>${esc(r.preview)}</pre>`:""}${r.rows?simpleTable(r.rows):""}${r.answer?`<p>${esc(r.answer)}</p>`:""}${r.truncated?'<small>仅展示前 100 行</small>':""}</div>`;}
function simpleTable(rows){if(!rows.length)return empty("暂无结果");const keys=Object.keys(rows[0]);return `<div class="table-scroll"><table><thead><tr>${keys.map(k=>`<th>${esc(k)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${keys.map(k=>`<td>${esc(typeof r[k]==="object"?JSON.stringify(r[k]):r[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;}
function graphView(g){
  if(!g.nodes.length)return empty("尚未建立实体网络","填写实体与关系后预览。");
  const width=720,height=Math.max(230,Math.ceil(g.nodes.length/3)*150),positions=Object.fromEntries(g.nodes.map((n,i)=>[n.id,{x:125+(i%3)*235,y:65+Math.floor(i/3)*150}]));
  return `<div class="knowledge-graph"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="知识实体关系图"><defs><marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#428576"/></marker></defs>${g.edges.map(e=>{const a=positions[e.source],b=positions[e.target];if(!a||!b)return "";const offset=a.y===b.y?42:0;return `<path d="M${a.x} ${a.y+25} Q${(a.x+b.x)/2} ${(a.y+b.y)/2+offset+45} ${b.x} ${b.y+30}" fill="none" stroke="#86afa3" stroke-width="2" marker-end="url(#graph-arrow)"/><text x="${(a.x+b.x)/2}" y="${(a.y+b.y)/2+offset+35}" text-anchor="middle" class="edge-label">${esc(e.label)}</text>`;}).join("")}${g.nodes.map(n=>{const p=positions[n.id];return `<g><rect x="${p.x-98}" y="${p.y-30}" width="196" height="60" rx="12" fill="#edf6f1" stroke="#80b6a1"/><text x="${p.x}" y="${p.y-4}" text-anchor="middle">${esc(n.name.slice(0,13))}</text><text x="${p.x}" y="${p.y+17}" text-anchor="middle" class="node-type">${esc(n.type)} · ${esc(n.id)}</text><title>${esc(n.name)}</title></g>`;}).join("")}</svg></div><div class="graph-legend">${g.nodes.length} 个实体 · ${g.edges.length} 条关系</div>`;
}
function importDialog(){modal("批量导入知识",`<p>每批最多 20 个 TXT / Markdown 文件，单文件最大 200KB（UTF-8）。逐项清洗、切片和创建本地索引，保存为草稿；失败文件可修正后重新导入。</p><form id="import-form"><div class="form-grid"><label class="full">选择文档<input type="file" name="file" accept=".txt,.md" multiple required></label>${input("source","来源 / 发布单位","本地批量导入")}${input("category","知识分类","业务手册","select",[...newsCategories,"技术规范","业务手册","案例经验","数据字典"])}${input("tags","标签（英文逗号分隔）","")}${input("chunkSize","切片长度",400,"number")}${input("visibility","访问范围","业务用户","select",["业务用户","管理员"])}</div><div class="form-footer"><button class="btn primary">开始导入与处理</button></div></form>`,true);}
function showBatch(batch){modal("知识处理批次 · "+batch.id,`<p>${esc(batch.source)} · ${fmt(batch.at)} ${tag(batch.status)}</p>${batch.items.map(r=>`<section class="batch-item"><h3>${esc(r.name)} ${tag(r.status)}</h3>${r.error?`<p class="error-text">${esc(r.error)}</p>`:`<p>${r.chunks} 个切片 · 去重 ${r.cleaning.duplicates} 段 · ${r.cleaning.before} → ${r.cleaning.after} 字符</p>${pipelineView(r.pipeline)}${btn("检查草稿并发布","edit",`knowledge:${r.documentId}`,"small")}`}</section>`).join("")}${btn("导入其他 / 重试文件","importDoc","","primary")}`,true);}
function evaluationView(run){return `<div class="notice">${esc(run.scope)} · ${run.passed}/${run.total} 通过</div>${run.results.map(r=>`<details class="evaluation-case"><summary>${tag(r.status)} ${esc(r.name)} · ${r.version==="draft"?"当前草稿":"已发布"}</summary><p>${esc(r.reasons.join("；")||"符合预期")}</p><h4>预期</h4><pre>${esc(JSON.stringify(r.expected,null,2))}</pre><h4>实际</h4><pre>${esc(JSON.stringify(r.actual||{},null,2))}</pre></details>`).join("")}`;}
function evaluationsDialog(agentId="a1"){modal("语料评测与版本回归",`<p>按样例预期答案片段、资源集合和操作序列评测。对比包含当前各项资产草稿，不只比较智能体。测试样例不参与回答，不写入用户会话。</p><form id="evaluation-form"><div class="form-grid">${input("agentId","待测智能体",agentId,"select",D.agents.map(a=>[a.id,a.name]))}${input("userId","使用身份","u1","select",D.accounts.filter(u=>u.role==="业务用户").map(u=>[u.id,u.name]))}</div><div class="form-footer"><button class="btn primary">运行已发布 / 草稿对比</button>${btn("导出训练样例","exportCorpus","","small")}</div></form><div id="evaluation-output"></div><h3>历史运行</h3>${D.evaluations.slice().reverse().map(r=>`<div class="activity-row"><div><strong>${esc(r.agent)}</strong><small>${fmt(r.at)} · ${r.passed}/${r.total} 通过</small></div>${btn("查看结果","evaluationResult",r.id,"small")}</div>`).join("")||'<p class="muted">尚无评测记录</p>'}`,true);}
async function advancedAction(action,id,el){
  switch(action){
    case "applyTemplate":{const result=await api("templateApply",{id:$('[name="templateId"]').value});const fields=readFields();for(const f of result.fields)if(!fields.some(x=>x.name===f.name))fields.push(f);$("#field-rows").innerHTML=resourceFields(fields);toast("模板字段已合并，请核对并保存");return true;}
    case "cleanDoc":{const result=await api("cleanPreview",{body:$('[name="body"]').value});window.cleanPreview=result;$("#clean-output").innerHTML=`<p>${result.before} → ${result.after} 字符，删除重复段落 ${result.duplicates} 个</p><pre>${esc(result.body.slice(0,1800))}</pre>${btn("确认替换正文","applyClean","","small primary")}`;return true;}
    case "applyClean":$('[name="body"]').value=window.cleanPreview.body;toast("已替换正文，请保存草稿");return true;
    case "previewGraph":{const nodes=$('[name="entities"]').value.split("\n").filter(x=>x.trim()).map(l=>{const [id,name,type]=l.split("|").map(x=>x.trim());if(!id||!name||!type)throw Error("实体格式：标识|名称|类型");return {id,name,type};});const edges=$('[name="edges"]').value.split("\n").filter(x=>x.trim()).map(l=>{const [source,label,target]=l.split("|").map(x=>x.trim());if(!nodes.some(n=>n.id===source)||!nodes.some(n=>n.id===target))throw Error("关系端点不存在");return {source,label,target};});$("#graph-output").innerHTML=graphView({nodes,edges});return true;}
    case "graph":{const d=D.knowledge.find(x=>x.id===id);modal(d.name+" · 知识图谱",graphView(d.graph||{nodes:[],edges:[]})+pipelineView(d.pipeline||[])+btn("维护实体关系","edit",`knowledge:${id}`,"primary"),true);return true;}
    case "batches":modal("知识处理批次",D.batches.slice().reverse().map(b=>`<div class="activity-row"><div><strong>${esc(b.source)}</strong><small>${fmt(b.at)} · ${b.items.length} 个文件</small></div>${tag(b.status)}${btn("处理详情","batch",b.id,"small")}</div>`).join("")||empty("暂无处理批次"),true);return true;
    case "batch":showBatch(D.batches.find(x=>x.id===id));return true;
    case "compare":{const r=D.indicators.find(x=>x.id===id);modal(r.name+" · 趋势与区域比较",`<form id="compare-form" data-id="${id}"><div class="form-grid">${input("periods","统计周期（按比较顺序，逗号分隔）","2025年,2026年")}${input("regions","比较区域（逗号分隔）","呼和浩特市,包头市")}${input("userId","计算身份","u1","select",D.accounts.filter(u=>u.role==="业务用户").map(u=>[u.id,u.name]))}</div><div class="form-footer"><button class="btn primary">计算并比较</button></div></form><div id="compare-output"></div>`,true);return true;}
    case "evaluations":evaluationsDialog();return true;
    case "evaluationResult":modal("回归评测结果",evaluationView(D.evaluations.find(r=>r.id===id)),true);return true;
    case "exportCorpus":{const r=await api("evaluationExport",{});const url=URL.createObjectURL(new Blob([r.content],{type:"application/x-ndjson"}));const a=document.createElement("a");a.href=url;a.download=r.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`已导出 ${r.count} 条训练样例`);return true;}
    case "handoffList":modal("选择要接续的历史任务",D.sessions.slice().reverse().map(s=>`<div class="activity-row"><div><strong>${esc(s.name)}</strong><small>${esc(s.context.region)} · ${esc(s.context.topic)}</small></div>${btn("新会话接续","handoff",s.id,"small")}</div>`).join(""),true);return true;
    case "handoff":{const s=D.sessions.find(x=>x.id===id);if(!s)throw Error("任务不存在或不属于当前用户");resumeFrom=id;sessionId="";selectedAgent=s.agentId;closeModal();if(route!=="assistant"){nav("/front/assistant");await new Promise(r=>setTimeout(r,150));}await sendQuestion("接续上次任务");return true;}
    case "applyMessage":{const m=currentSession().messages.find(x=>x.id===id);cart=[...new Set([...cart,...m.resourceIds.filter(i=>D.resources.some(r=>r.id===i&&r.access==="可申请"))])];cartDialog();return true;}
    case "interfaceTest":modal("能力调用契约 · v1",`<p><code>POST /api/v1/agents/invoke</code> · JSON 请求 / 响应</p><p>演示身份头：X-Demo-User。此接口只面向本机演示，生产身份需另行接入。</p><pre>${esc(JSON.stringify({apiVersion:"v1",agentId:"a1",question:"地灾巡查",sessionId:"可选：继续会话",resumeFrom:"可选：接续任务"},null,2))}</pre><p>响应：apiVersion、sessionId、traceId、message（回答、资源、引用、指标、执行追踪）。错误：400 参数，403 权限，404 不可用，409 版本冲突。</p><form id="invoke-form"><div class="form-grid">${input("agentId","智能体","a1","select",D.agents.map(a=>[a.id,a.name]))}${input("userId","演示身份","u1","select",D.accounts.filter(u=>u.role==="业务用户").map(u=>[u.id,u.name]))}${input("question","调用问题","地灾巡查")}</div><div class="form-footer"><button class="btn primary">试调用接口</button></div></form><div id="invoke-output"></div>`,true);return true;
    case "improveFeedback":{const f=D.feedback.find(x=>x.id===id);modal("反馈反哺标注与记忆",`<p>${esc(f.note)}</p><form id="improve-form" data-id="${id}">${input("kind","改进目标","metadata","select",[["metadata","资源元数据同义词"],["memory","反馈用户的历史摘要"]])}${input("targetId","资源（仅元数据改进使用）",D.resources[0]?.id,"select",D.resources.map(r=>[r.id,r.name]))}${input("text","人工确认的改进内容",f.note,"textarea")}<div class="form-footer"><button class="btn primary">创建待确认改进草稿</button></div></form>`);return true;}
    case "feedbackDrafts":modal("标注与记忆改进草稿",D.feedbackDrafts.map(d=>`<div class="batch-item"><strong>${d.kind==="metadata"?"元数据同义词":"用户摘要"} · ${esc(d.targetId)}</strong><p>${esc(d.text)}</p>${tag(d.status)}${d.status==="待确认"?btn("确认应用","applyFeedbackDraft",d.id,"small primary"):""}<small>元数据更新写入资产草稿，需再发布；记忆更新在确认后生效。</small></div>`).join("")||empty("暂无改进草稿"),true);return true;
    case "applyFeedbackDraft":await mutate("feedbackApply",{id},"已应用改进");await advancedAction("feedbackDrafts");return true;
    default:return false;
  }
}
function bindAdvancedForms(){
  handleForm("#evaluation-form",async form=>{const r=await api("evaluate",{...valuesOf(form),compare:true});await load();$("#evaluation-output").innerHTML=evaluationView(r);});
  handleForm("#compare-form",async form=>{const r=await api("indicatorCompare",{...valuesOf(form),id:form.dataset.id});const valid=r.rows.filter(x=>!x.error),max=Math.max(1,...valid.map(x=>Math.abs(x.value)));$("#compare-output").innerHTML=`<div class="comparison-chart">${valid.map(x=>`<div><span>${esc(x.region)} · ${esc(x.period)}</span><i style="width:${Math.max(1,Math.abs(x.value)/max*100)}%"></i><strong>${x.value} ${esc(r.unit)}</strong></div>`).join("")}</div>`+simpleTable(r.rows.map(x=>({区域:x.region,周期:x.period,结果:x.error||`${x.value} ${r.unit}`,较上一期:x.change==null?"—":`${x.change}%`,来源:x.source||"—"})));});
  handleForm("#invoke-form",async form=>{const v=valuesOf(form);const response=await fetch("/api/v1/agents/invoke",{method:"POST",headers:{"Content-Type":"application/json","X-Demo-User":v.userId},body:JSON.stringify({apiVersion:"v1",agentId:v.agentId,question:v.question})});const r=await response.json();if(!response.ok)throw Error(r.error);await load();$("#invoke-output").innerHTML=`<p>调用完成 · 追踪 ${esc(r.traceId)}</p><p>${esc(r.message.text)}</p>${traceView(r.message.trace,true)}`;});
  handleForm("#improve-form",async form=>{await mutate("feedbackDraft",{...valuesOf(form),id:form.dataset.id},"已创建改进草稿");await advancedAction("feedbackDrafts");});
}

// Public-facing portal shell; operational administration keeps its own layout.
const portalNav = [["home","首页"],["data","数据服务"],["capabilities","能力服务"],["services","办事服务"],["knowledge","资讯下载"],["landscape","大美内蒙古"]];
function portalShell() {
  const activeRoute=({map:"data",search:"",agents:"capabilities",assistant:"services",intelligence:"capabilities","app-center":"capabilities",requests:"services"})[route]??route;
  const current=portalNav.find(([r])=>r===route)?.[1] || {"internal-home":"综合门户","integrated-portal":"综合门户","integration-results":"一张图成果","integrated-workbench":"个人工作台",search:"综合搜索",map:"地图浏览",requests:"我的咨询与意见","app-center":"应用目录",intelligence:"智能辅助",assistant:"办事服务 · 智能问答",applications:"我的资源申请",profile:"个人中心",agents:"智能体广场",tools:"智能服务",scenes:"场景应用",workbench:"业务工作台",cases:"办件详情",messages:"我的消息"}[route] || "首页";
  $("#app").innerHTML=`<div class="portal-site"><div class="portal-utility"><div class="portal-container"><span>内蒙古自治区 · 自然资源一张图服务门户</span><span>数据共享 · 便民办事 · 北疆风貌</span></div></div><header class="portal-header"><div class="portal-container portal-header-inner"><a class="portal-brand" href="#/front/home" aria-label="一张图首页"><span class="portal-mark">${icon("leaf")}</span><span>一张图<small>NATURAL RESOURCES · ONE MAP</small></span></a><nav class="portal-nav" aria-label="门户导航">${portalNav.map(([r,t])=>`<a href="#/front/${r}" class="${activeRoute===r?"active":""}" ${activeRoute===r?'aria-current="page"':""}>${t}</a>`).join("")}<a href="/gis/index.html" target="_blank" rel="noopener noreferrer" title="在新标签页打开一张图">进入一张图</a></nav><div class="portal-header-tools"><button class="portal-account" data-action="portalAccount" aria-label="打开个人服务"><span class="avatar">${esc(D.user.name[0])}</span><span>${esc(D.user.name)}</span>${icon("chevron")}</button><button class="icon-btn portal-menu-toggle" data-action="portalMenu" aria-label="展开门户导航" aria-expanded="false">${icon("menu")}</button></div></div></header>${route!=="home"?`<div class="portal-container portal-breadcrumb"><a href="#/front/home">首页</a><span aria-hidden="true">/</span>${route==='assistant'?'<a href="#/front/services">办事服务</a><span aria-hidden="true">/</span><span aria-current="page">智能助手</span>':portalNav.some(([r])=>r===route)?`<a href="#/front/${route}">${esc(current)}</a>`:`<span>${esc(current)}</span>`}</div>`:""}<main id="main" class="portal-main ${route==="home"?"portal-home":""} ${route==="assistant"?"portal-conversation":""}"></main><footer class="portal-footer"><div class="portal-container portal-footer-top"><div><a class="portal-footer-brand" href="#/front/home">${icon("leaf")}一张图</a><p>面向公众、企事业单位与科研院所的自然资源公共服务。</p></div><div class="portal-footer-links"><a href="#/front/data">数据服务</a><a href="#/front/knowledge">资讯下载</a><button data-action="portalGuide">使用指南</button><a href="#/admin/overview">后台管理</a></div></div><div class="portal-container portal-footer-bottom"><span>内蒙古自治区 · 自然资源一张图服务门户</span><span>原型演示 · 数据与内容仅供体验</span></div></footer></div>`;
  renderPage();
}
function portalSectionTitle(kicker,title,description,link,label="查看全部") {return `<div class="portal-section-title"><div><span class="portal-kicker">${kicker}</span><h2>${title}</h2>${description?`<p>${description}</p>`:""}</div>${link?`<a href="${link}">${label} ${icon("arrow")}</a>`:""}</div>`;}
function portalLandscape(){return `<div class="portal-landscape" aria-hidden="true"><svg viewBox="0 0 680 480"><defs><linearGradient id="portal-land-fill" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#bdd5ae"/><stop offset="1" stop-color="#456e53"/></linearGradient><linearGradient id="portal-water" x1="0" x2="1"><stop stop-color="#e0eee3"/><stop offset="1" stop-color="#a2c6b8"/></linearGradient></defs><ellipse cx="370" cy="346" rx="243" ry="77" fill="#2f634b" opacity=".06"/><path d="M85 259 319 133 581 265 360 403Z" fill="#91ae84"/><path d="M85 238 319 112 581 244 360 382Z" fill="#d1dfb8"/><path d="M85 216 319 90 581 222 360 360Z" fill="url(#portal-land-fill)"/><path d="m130 214 111-53 60 25-113 60Z" fill="#e2e8c7"/><path d="m203 252 113-59 65 28-115 64Z" fill="#b9cd9f"/><path d="m282 291 116-62 77 33-119 73Z" fill="#dce2ae"/><path d="M297 118q-15 62 48 72t39 78q-11 27 57 40" fill="none" stroke="url(#portal-water)" stroke-width="22"/>${Array.from({length:9},(_,i)=>`<path d="M${111+i*18} ${210+i*10}q27 -69 87 -45t103 -14 167 77" fill="none" stroke="#eff6e6" opacity=".45" stroke-width="1"/>`).join("")}<path d="m255 138 42-76 41 76-40 23Z" fill="#608a60"/><path d="m297 62 41 76-40 23Z" fill="#335f46"/><path d="m426 196 32-59 32 59-31 18Z" fill="#416e4c"/><path d="m458 137 32 59-31 18Z" fill="#254f3d"/><g fill="#f7faf2" stroke="#55816a"><circle cx="215" cy="216" r="7"/><circle cx="381" cy="276" r="7"/><circle cx="421" cy="199" r="7"/></g><path d="m215 216 166 60 40-77" stroke="#fbfff2" stroke-dasharray="5 5" fill="none" stroke-width="2"/></svg><div class="portal-map-label portal-map-label-one">${icon("layers")}空间数据</div><div class="portal-map-label portal-map-label-two">${icon("book")}业务知识</div><div class="portal-map-caption"><span></span>连接每一份数据，理解每一寸土地</div></div>`;}
function renderPortalHome(){
  const resources=D.resources.slice(0,4), agents=[...D.agents].sort((a,b)=>{const preferred=["a1","a2","a3","a_team"];return (preferred.includes(a.id)?preferred.indexOf(a.id):9)-(preferred.includes(b.id)?preferred.indexOf(b.id):9);}).slice(0,4), knowledge=(D.portalArticles||D.knowledge).slice(0,3);
  $("#main").innerHTML=`<section class="portal-hero"><div class="portal-container portal-hero-inner"><div class="portal-hero-copy"><div class="portal-hero-eyebrow"><span></span>自然资源 · 智能服务</div><h1>汇聚资源与知识<br>开启<span>智能服务</span>新体验</h1><p>找数据、查政策、问指标，让自然资源业务更简单。<br>从一句话开始，发现你需要的专业能力。</p><form id="portal-search" class="portal-search"><label for="portal-question" class="sr-only">搜索资源或向智能助手提问</label>${icon("search")}<input id="portal-question" name="question" placeholder="输入关键词，或试试“找最近的地灾巡查记录表”" required maxlength="1000"><button type="submit">智能搜索 ${icon("arrow")}</button></form><div class="portal-hot-search"><span>热门探索</span>${["地灾巡查","耕地保护","矿业权"].map(q=>`<button data-action="portalQuestion" data-id="${q}">${q}</button>`).join("")}<a href="#/front/catalog">浏览资源目录 ${icon("arrow")}</a></div></div>${portalLandscape()}</div><div class="portal-container portal-resource-strip">${[["database","数据库表"],["layers","图层服务"],["tool","工具服务"],["book","知识文档"]].map(([i,t])=>`<a href="#/front/catalog" data-action="portalCategory" data-id="${t}"><span class="portal-strip-icon">${icon(i)}</span><span>${t}<small>${D.resources.filter(r=>r.type===t).length} 项可发现资源</small></span>${icon("arrow")}</a>`).join("")}</div></section><div class="portal-container"><section class="portal-section">${portalSectionTitle("INTELLIGENT SERVICES","发现你的专业智能助手","围绕业务场景，连接数据检索、知识问答与指标分析。","#/front/agents","进入智能体广场")}<div class="portal-agent-grid">${agents.map(agentCard).join("")||empty("暂无已发布智能体")}</div></section><section class="portal-section portal-resource-section">${portalSectionTitle("RESOURCE DISCOVERY","探索自然资源数据","库表、图层与服务集中发现，资源用途与使用权限一目了然。","#/front/catalog","浏览资源中心")}<div class="portal-resource-grid">${resources.map(resourceCard).join("")||empty()}</div></section><section class="portal-service-band"><div><span class="portal-kicker">TOOLS & SERVICES</span><h2>从发现资源，到完成业务</h2><p>五类配套服务，让数据理解、分析和知识使用连贯起来。</p><a href="#/front/tools">探索全部工具 ${icon("arrow")}</a></div><div class="portal-service-shortcuts">${portalToolItems().map(t=>`<button data-action="${t.action}" data-id="${esc(t.id)}"><span>${icon(t.icon)}</span>${t.name}${icon("arrow")}</button>`).join("")}</div></section><section class="portal-section portal-bottom-sections"><div>${portalSectionTitle("NEWS & RESOURCES","资讯与资料，随时查阅","政策法规、行业动态、技术标准与培训资源。","#/front/knowledge","更多资讯")}<div class="portal-knowledge-list">${knowledge.map(portalKnowledgeRow).join("")||empty("暂无已发布知识")}</div></div><aside class="portal-guide-card"><span class="portal-kicker">GET STARTED</span><h2>第一次使用？<br>从这里开始。</h2><ol><li><b>01</b><div>描述你的需求<small>输入业务关键词，或直接向助手提问</small></div></li><li><b>02</b><div>了解资源与依据<small>查看资源详情、指标口径和知识引用</small></div></li><li><b>03</b><div>申请并使用资源<small>提交用途与期限，在个人中心跟踪进度</small></div></li></ol><button data-action="portalGuide">查看使用指南 ${icon("arrow")}</button></aside></section></div>`;
}
function portalToolItems(){return [
  {name:"资源语义解读",category:"元数据服务",icon:"database",description:"查看资源字段、业务解释、坐标系与关联关系，理解数据后再使用。",action:"navigate",id:"/front/catalog",cta:"查找资源"},
  {name:"指标分析",category:"指标知识服务",icon:"chart",description:"查询业务指标、统计口径和计算结果，了解指标的数据来源与依赖。",action:"useAgent",id:"a3",cta:"开始分析"},
  {name:"业务知识问答",category:"知识库服务",icon:"book",description:"查阅业务指南与政策知识，让每一次回答都有可追溯的来源。",action:"useAgent",id:"a2",cta:"向知识助手提问"},
  {name:"场景提问",category:"语料应用服务",icon:"message",description:"从常见业务问题出发，一键进入适合的助手，减少重复输入。",action:"portalScenarios",id:"",cta:"选择业务场景"},
  {name:"个性化服务",category:"用户记忆服务",icon:"brain",description:"设置常用领域和回答偏好，查看历史任务，让后续对话更连贯。",action:"navigate",id:"/front/profile",cta:"管理我的偏好"}
];}
function renderPortalTools(){
  $("#main").innerHTML=heading("工具与服务","围绕自然资源业务，选择适合你的数据与知识服务。")+`<div class="portal-tools-grid">${portalToolItems().map((t,i)=>`<article class="portal-tool-card"><div class="portal-tool-top"><span class="tile ${["","purple","blue","gold",""][i]}">${icon(t.icon)}</span><span>0${i+1}</span></div><small>${t.category}</small><h2>${t.name}</h2><p>${t.description}</p>${btn(t.cta,t.action,t.id,"", "arrow")}</article>`).join("")}</div><section class="portal-scenarios"><h2>从一个具体问题开始</h2><p>选择业务场景，直接体验对应的智能服务。</p><div>${D.agents.map(a=>`<button data-action="portalQuestion" data-agent="${a.id}" data-id="${esc(a.question)}">${icon(a.icon)}<span>${esc(a.question)}<small>${esc(a.name)}</small></span>${icon("arrow")}</button>`).join("")}</div></section>`;
}
function portalKnowledgeRow(d){return `<button class="portal-knowledge-row" data-action="portalKnowledge" data-id="${d.id}"><img class="portal-list-thumb" data-preview src="${esc(previewSource({...d,type:"知识文档"}))}" alt="${esc(d.name)}业务示意" loading="lazy"><span><small>${esc(d.category)}</small><strong>${esc(d.name)}</strong><span>${esc(d.source)} · v${d.version}.0</span></span>${icon("arrow")}</button>`;}
function renderPortalKnowledge(){
  const records=D.portalArticles||D.knowledge;
  page=Math.max(1,Math.min(page,Math.max(1,Math.ceil(searchNews(records,query,filter).length/8))));
  const memory=D.memories.find(m=>m.id===D.user.id&&m.enabled);
  $("#main").innerHTML=renderNews({records,query,category:filter,page,domain:memory?.domain||'',esc,icon,btn,empty}) + managementUI.materialCards();
}
async function portalAsk(question,agent){
  if(pending)return toast("请先等待当前回答完成，或进入助手停止本次响应");
  
  selectedAgent=agent||(/什么是|政策|解释/.test(question)?"a2":/指标/.test(question)?"a3":"a1");sessionId="";resumeFrom="";closeModal();
  if(route!=="assistant"){
    nav("/front/assistant");
    for(let i=0;i<60;i++){if(route==="assistant"&&$("#chat-form")&&window.appReady)break;await new Promise(r=>setTimeout(r,50));}
  }
  await sendQuestion(question);
}
async function portalAction(action,id,el){
  switch(action){
    case "portalMenu":{const open=document.body.classList.toggle("portal-menu-open");el.setAttribute("aria-expanded",String(open));return true;}
    case "portalAssistant":businessContext=null;selectedAgent="a1";sessionId="";resumeFrom="";if(route==="assistant")renderPage();else nav("/front/assistant");return true;
    case "portalAccount":modal("我的服务",`<div class="portal-account-heading"><span class="avatar large">${esc(D.user.name[0])}</span><div><h3>${esc(D.user.name)}</h3><p>${esc(D.user.department)}</p></div></div><div class="portal-account-links"><a href="#/front/integrated-portal" data-action="portalAccountNavigate" data-id="/front/integrated-portal">${icon("grid")}综合门户 ${icon("arrow")}</a><a href="#/front/integrated-workbench" data-action="portalAccountNavigate" data-id="/front/integrated-workbench">${icon("grid")}个人工作台 ${icon("arrow")}</a><a href="#/front/shared-resources" data-action="portalAccountNavigate" data-id="/front/shared-resources">${icon("database")}资源与交付 ${icon("arrow")}</a><a href="#/front/api-keys" data-action="portalAccountNavigate" data-id="/front/api-keys">${icon("code")}我的 API 密钥 ${icon("arrow")}</a><a href="#/front/register" data-action="portalAccountNavigate" data-id="/front/register">${icon("user")}门户账号申请 ${icon("arrow")}</a><a href="#/front/requests" data-action="portalAccountNavigate" data-id="/front/requests">${icon("message")}我的咨询与意见 ${icon("arrow")}</a><a href="#/front/internal-home" data-action="portalAccountNavigate" data-id="/front/internal-home">${icon("file")}内部业务工作台 ${icon("arrow")}</a><a href="#/front/app-center" data-action="portalAccountNavigate" data-id="/front/app-center">${icon("grid")}我的应用 ${icon("arrow")}</a><a href="#/front/messages" data-action="portalAccountNavigate" data-id="/front/messages">${icon("bell")}我的消息 ${icon("arrow")}</a><a href="#/front/applications" data-action="portalAccountNavigate" data-id="/front/applications">${icon("file")}我的申请 ${icon("arrow")}</a><a href="#/front/profile" data-action="portalAccountNavigate" data-id="/front/profile">${icon("user")}个人中心与历史会话 ${icon("arrow")}</a><button data-action="identity">${icon("refresh")}切换演示身份 ${icon("arrow")}</button></div>`);return true;
    case "portalAccountNavigate":closeModal();nav(id);return true;
    case "portalQuestion":businessContext=null;await portalAsk(id,el?.dataset.agent);return true;
    case "portalCategory":{
      nav(id==="工具服务"?"/front/capabilities":id==="知识文档"?"/front/knowledge":"/front/data?type="+encodeURIComponent(id));return true;
    }
    case "newsCategory":filter=id;query="";page=1;renderPage();return true;
    case "newsReset":filter="全部";query="";page=1;renderPage();return true;
    case "newsDownload":{
      const d=await api("portal.newsDownload",{id});if(!d)throw Error("资讯已下架或当前不可访问");
      const url=URL.createObjectURL(new Blob(["\ufeff",newsDownloadText(d)],{type:"text/plain;charset=utf-8"}));
      const link=document.createElement('a');link.href=url;link.download=d.name.replace(/[\\/:*?"<>|]/g,'_')+'.txt';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast("已下载资讯正文（TXT）");return true;
    }
    case "portalKnowledge":{
      const d=(D.portalArticles||D.knowledge).find(d=>d.id===id);if(!d)throw Error("资讯已下架或当前不可访问");
      const related=recommendedNews(D.portalArticles||D.knowledge,{category:newsCategory(d),excludeId:d.id});
      modal(d.name,`<div class="portal-document-meta">${tag(newsCategory(d))}<span>来源：${esc(d.source)}</span><span>更新：${esc(String(d.updated||'').slice(0,10))}</span><span>版本 v${d.version}.0</span></div><div class="portal-document-body news-document">${d.body.split(/\n\s*\n/).map(p=>`<p>${esc(p)}</p>`).join("")}</div><div class="news-related"><h3>关联资料</h3>${(D.portalManagement?.materials||[]).filter(r=>r.contentId===d.id).map(r=>btn(esc(r.name),"pm-download",r.id,"small","download")).join("")||"<p>暂无关联附件</p>"}</div><div class="news-related"><h3>相关阅读</h3>${related.map(r=>`<button data-action="portalKnowledge" data-id="${esc(r.id)}">${esc(r.name)} ${icon('arrow')}</button>`).join('')||'<p class="muted">暂无相关资讯</p>'}</div><div class="form-footer">${btn("下载正文（TXT）","newsDownload",d.id,"","download")}${btn("就此内容提问","portalQuestion","解释"+d.name,"primary","sparkles")}</div>`,true);return true;
    }
    case "portalScenarios":modal("选择业务场景",`<div class="portal-scenario-dialog">${D.agents.map(a=>`<button data-action="portalQuestion" data-agent="${a.id}" data-id="${esc(a.question)}"><span class="tile">${icon(a.icon)}</span><span><strong>${esc(a.name)}</strong><small>${esc(a.question)}</small></span>${icon("arrow")}</button>`).join("")}</div>`,true);return true;
    case "portalGuide":modal("门户使用指南",`<div class="portal-guide-content"><h3>发现资源</h3><p>首页搜索会展示数据、工具和资讯结果。也可在数据服务中按主题、地区和类型筛选，详情页提供字段、地图和获取方式。</p><h3>使用智能服务</h3><p>工具中心提供坐标转换、面积量算和点缓冲区分析，办事服务内的智能问答支持资源检索、知识问答与指标分析，并提供相关办事指南与办理入口。</p><h3>申请资源</h3><p>将可申请资源加入清单，填写用途和使用期限后提交。在右上角“我的申请”中查看办理进度；授权后可查看或下载已有的示例数据；实际下载能力以资源绑定情况为准。</p><h3>接续任务</h3><p>个人中心保留历史会话和偏好。进入助手后点击“接续任务”，可以在新会话中继续之前的查询。</p></div>`,true);return true;
    default:return false;
  }
}

// Admin workflows: shared objects, independent publication channels and scoped navigation.
function contentChannelStatus(r){
  const channel=route==='articles'?'portal':'index',snapshot=r.channels ? r.channels[channel] : (r.status==='已停用'?null:r.published);
  return `${tag(snapshot?(channel==='portal'?'门户已发布':'检索已启用'):(channel==='portal'?'未对外发布':'未纳入检索'))}<small>${snapshot?`渠道 v${snapshot.version} · `:''}文档${esc(r.status)}${channel==="index"&&indexState(r).pending?" · 索引待更新":""}</small>`;
}
function contentChannelButtons(r){
  const channel=route==='articles'?'portal':'index',snapshot=r.channels ? r.channels[channel] : (r.status==='已停用'?null:r.published);
  return btn(channel==='portal'?'发布到门户':'更新知识索引','design-channel',`${r.id}:${channel}:on`,'text small')+(snapshot?btn(channel==='portal'?'门户下架':'退出检索','design-channel',`${r.id}:${channel}:off`,'text small'):'');
}
function resourceEditorHtml(r){
  const f=(k,l,d='',type='text',options=[])=>input(k,l,r[k]??d,type,options),select=(k,l,options,d)=>f(k,l,d??options[0],'select',options);
  const sections=[
    ['basic','基本信息',f('name','名称 <em>*</em>')+select('type','资源类型',['数据库表','图层服务','工具服务','知识文档'])+f('category','业务分类','地灾防治')+select('region','覆盖区域',D.regions)+f('source','提供单位','自治区自然资源示例数据中心')+select('frequency','更新频次',['每日','每周','每月','每年'])+f('date','数据更新日期',new Date().toISOString().slice(0,10),'date')+f('description','业务说明','','textarea')],
    ['metadata','技术元数据',f('crs','坐标系','CGCS2000')+select('subtype','资源子类型',['属性表','空间表','视图','图层服务','工具服务','知识文档'])+select('sourceType','来源类型',['库表','服务','接口','文件'])+select('templateId','元数据模板',[['','不使用模板'],...D.templates.map(x=>[x.id,x.name])],'')+`<div class="full">${btn('应用模板字段','applyTemplate','','small')} ${btn('添加字段','addField','','small')} ${btn('辅助标注','suggestFields','','small')}</div><div class="full" id="field-rows">${resourceFields(r.fields||[])}</div>`],
    ['semantic','AI 语义与关联',f('aliases','业务同义词（英文逗号分隔）','','textarea')+select('documentId','关联知识文档',[['','无关联文档'],...D.knowledge.map(x=>[x.id,x.name])],'')+binding('relations','关联资源','resources',(r.relations||[]).join(','))+`<details class="full"><summary>高级关联规则</summary>${f('relationRules','关系规则：类型|目标资源标识|本字段|目标字段','','textarea')}<p class="muted">例如：表关联|r2|region_code|region_code。保存时校验目标资源和字段。</p></details>`],
    ['sharing','共享与服务',input('sharingPolicy','共享策略',r.sharingPolicy||(r.access==='已授权'?'开放使用':'申请使用'),'select',['申请使用','开放使用','限制使用'])+select('visibility','可发现范围',['业务用户','管理员'])+input('departments','可访问部门（不选表示全部）',r.departments||'','select',[])+`<p class="full notice">开放使用：可见范围内用户无需申请。申请使用：须有有效个人授权。限制使用：暂停普通用户使用。个人授权请在授权台账办理。</p>`+f('dataSource','数据源名称 / 提供方系统')+select('serviceProtocol','服务类型',['本地示例','OGC WMS','OGC WMTS','OGC WFS','REST','文件下载'])+f('serviceUrl','服务 HTTPS 地址')+f('downloadUrl','数据包 HTTPS 下载地址')],
    ['history','授权与版本',`<div class="full"><p>当前资源标识：${esc(r.id||'保存后生成')} · 已发布版本：v${r.version||0}</p><a href="#/admin/grants" class="btn" data-action="design-open-grants">查看授权台账</a><p class="muted">共享策略和服务地址随资源版本发布生效；撤销个人授权立即影响后续使用。</p>${(r.versions||[]).map(v=>`<p>v${v.version} · ${esc(v.updated||'')} · ${esc(v.name)}</p>`).join('')||'<p class="muted">暂无历史发布版本</p>'}</div>`],
    ['demo','高级演示配置',`<p class="full notice">用于本地原型试算，非生产数据源连接。配置真实接入时请维护技术服务与数据源。</p>`+f('sqlName','本地示例 SQL 表名')+f('dataRows','示例数据 CSV（首行为列名）','','textarea')]
  ];
  const html=`<div class="full editor-tabs" role="tablist" aria-label="资源配置">${sections.map(([key,label],i)=>`<button type="button" role="tab" id="resource-tab-${key}" aria-controls="resource-pane-${key}" aria-selected="${i===0}" data-action="design-tab" data-id="${key}">${label}</button>`).join('')}</div>`+sections.map(([key,label,body],i)=>`<section class="full resource-pane" id="resource-pane-${key}" role="tabpanel" aria-labelledby="resource-tab-${key}" ${i?'hidden':''}><h3>${label}</h3><div class="form-grid">${body}</div></section>`).join('');
  // Keep legacy department values selectable while using the current organization names.
  const container=document.createElement('div');container.innerHTML=html;
  const depts=container.querySelector('[name=departments]');depts.multiple=true;depts.size=5;
  const selected=csvIds(r.departments),names=[...new Set([...(D.platform?.organizations||[]).map(x=>x.name),...selected])];
  depts.innerHTML=names.map(n=>`<option value="${esc(n)}" ${selected.includes(n)?'selected':''}>${esc(n)}</option>`).join('');
  return container.innerHTML;
}
function renderGrantLedger(){
  const rows=D.grants||[];
  $('#main').innerHTML=heading('授权台账','逐用户查看授权来源、期限与生效状态。开放使用由资源共享策略控制，不属于个人授权。')+`<section class="panel table-panel"><div class="table-scroll"><table><thead><tr><th>授权 / 资源</th><th>使用人</th><th>来源申请</th><th>有效期</th><th>授权 / 交付状态</th><th>操作</th></tr></thead><tbody>${rows.slice().reverse().map(g=>`<tr><td>${esc(g.resourceName)}<small>${esc(g.id)}</small></td><td>${esc(g.userName)}</td><td>${g.sourceApplicationId?btn(esc(g.sourceApplicationId),'application',g.sourceApplicationId,'text small'):'历史授权（来源未记录）'}</td><td>${esc(g.validUntil)}</td><td>${tag(g.displayStatus)}<small>${esc(g.deliveryStatus)}${g.resourceAvailable?'':' · 资源已下架或限制使用'}</small></td><td>${btn('记录','design-grant-history',g.id,'text small')}${g.displayStatus==='有效'?btn('撤销','design-grant-revoke',g.id,'text small'):''}</td></tr>`).join('')||'<tr><td colspan="6">暂无个人授权；通过资源申请后自动生成。</td></tr>'}</tbody></table></div></section>`;
}
function renderDesignOverview(){
  const navs=permittedAdminNav(),allowed=key=>navs.some(n=>n[0]===key),pending=(D.applications||[]).filter(a=>a.status==='待审核').length;
  const cards=[['app-registry','已上架应用',(D.platform?.apps||[]).filter(a=>a.listed).length],['scene-templates','地图场景',(D.platform?.scenes||[]).length],['message-bus','待处理投递',(D.platform?.deliveries||[]).filter(d=>d.status!=='已送达').length],['approvals','待审资源申请',pending],['grants','有效个人授权',(D.grants||[]).filter(g=>g.displayStatus==='有效').length],['portal-users','待审注册',(D.portalManagement?.registrations||[]).filter(r=>r.status==='待审核').length],['quality','待补充元数据',(D.platform?.quality||[]).filter(r=>r.missing.length).length],['portal-monitor','当前告警',D.portalManagement?.activeAlerts||0],['cases','在办事项',(D.platform?.cases||[]).filter(c=>c.status==='在办').length]].filter(([key])=>allowed(key));
  $('#main').innerHTML=heading('管理工作台',`${D.user.name} · ${D.user.role}；按当前身份展示待办与常用入口。`)+`<div class="stats">${cards.map(([key,label,value])=>`<a class="stat" href="#/admin/${key}"><div><span>${label}</span><strong>${value}</strong></div></a>`).join('')}</div><section class="panel" style="padding:24px"><h2>我的管理入口</h2><div class="pc-support-links">${navs.filter(n=>['integration-results','center-integration','center-resources','center-tools','center-operations','resources','approvals','grants','portal-tools','articles','knowledge','app-registry','workflows','identity','portal-monitor','message-bus'].includes(n[0])).map(([key,label,i])=>`<a ${adminLinkAttributes(key)}>${icon(i)}<span>${esc(label)}</span></a>`).join('')}</div></section>`;
}
async function designAction(action,id){
  if(!action.startsWith('design-'))return false;
  if(action==='design-tab'){
    $$('.resource-pane').forEach(p=>p.hidden=p.id!=='resource-pane-'+id);
    $$('.editor-tabs [role=tab]').forEach(t=>t.setAttribute('aria-selected',String(t.dataset.id===id)));
  }else if(action==='design-open-grants'){closeModal();nav('/admin/grants');}
  else if(action==='design-grant-history'){
    const g=D.grants.find(g=>g.id===id);modal('授权变更记录',`<p>${esc(g.resourceName)} · ${esc(g.userName)}</p>${g.history.map(h=>`<p>${esc(h.at)} · ${esc(h.actor)} · ${esc(h.action)}<br>${esc(h.note)}</p>`).join('')||'<p>历史授权没有记录办理过程。</p>'}`);
  }else if(action==='design-grant-revoke'){
    const g=D.grants.find(g=>g.id===id);modal('撤销个人授权',`<p>撤销 ${esc(g.userName)} 对 ${esc(g.resourceName)} 的授权。若资源为开放使用，撤销个人授权不会关闭开放策略。</p><form id="design-revoke-form">${input('reason','撤销原因（至少5字）','','textarea')}<button class="btn danger">确认撤销</button></form>`);
    $('#design-revoke-form').addEventListener('submit',async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{await mutate('grant.revoke',{id,rev:g.rev,reason:new FormData(e.target).get('reason')},'授权已撤销');closeModal();}catch(error){toast(error.message);}finally{button.disabled=false;}});
  }else if(action==='design-channel'){
    const [key,channel,op]=id.split(':'),r=D.knowledge.find(r=>r.id===key);
    modal('确认更新发布渠道',`<p>${esc(r.name)}</p>${channel==='index'?intelligenceUI.impact('knowledge',key):''}<p>${op==='on'?'将当前文档版本发布到':'将当前版本退出'}${channel==='portal'?'门户资讯':'AI 知识检索'}。另一个渠道保持原有版本和状态。</p>${btn('确认','design-channel-confirm',id,'primary')}`);
  }else if(action==='design-channel-confirm'){
    const [key,channel,op]=id.split(':'),r=D.knowledge.find(r=>r.id===key);
    await mutate('knowledge.channel',{id:key,rev:r.rev,channel,enabled:op==='on'},'渠道状态已更新');closeModal();
  }
  return true;
}
document.addEventListener('invalid',e=>{
  const pane=e.target.closest('.resource-pane');if(pane?.hidden)designAction('design-tab',pane.id.replace('resource-pane-',''));
},true);
