export function createPortalOperations(ctx){
  const {$,esc,btn,tag,api,modal,closeModal,toast}=ctx;
  const D=()=>ctx.state().D,M=()=>D().portalManagement;
  let generation=0,timer=null,security=null;
  const field=(name,label,value='',type='text',options=[])=>`<label class="pm-field"><span>${esc(label)}</span>${type==='select'?`<select name="${name}">${options.map(o=>{const [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${esc(v)}" ${value===v?'selected':''}>${esc(t)}</option>`;}).join('')}</select>`:type==='textarea'?`<textarea name="${name}" rows="3">${esc(value)}</textarea>`:`<input name="${name}" type="${type}" ${type==='checkbox'?`value="1" ${value?'checked':''}`:`value="${esc(value)}"`} ${type==='number'?'step="1"':''}>`}</label>`;
  const title=(name,description,actions='')=>`<div class="page-heading"><div><div class="eyebrow">PORTAL MANAGEMENT</div><h1>${esc(name)}</h1><p>${esc(description)}</p></div><div class="actions">${actions}</div></div>`;
  const table=(heads,rows)=>`<div class="table-scroll"><table><thead><tr>${heads.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${heads.length}"><div class="empty">暂无记录</div></td></tr>`}</tbody></table></div>`;
  function render(){
    const token=++generation;clearTimeout(timer);
    const {mode,route}=ctx.state();
    if(!(['portal-keys','portal-security','portal-monitor','portal-roles'].includes(route)&&mode==='admin')&&!(mode==='front'&&route==='api-keys'))return false;
    const admin=mode==='admin';if(admin&&D().user.role!=='平台管理员'){$('#main').innerHTML=title('暂无管理权限','请使用平台管理员身份。');return true;}
    if(route==='portal-roles'){
      $('#main').innerHTML=title('门户角色分配','维护普通用户、企业用户和管理员角色；部门与区域范围沿用组织权限。','<a class="btn" href="#/admin/identity">组织与权限</a>')+`<section class="panel">${table(['用户','所属单位','门户角色','状态','操作'],D().users.map(u=>`<tr><td>${esc(u.name)}</td><td>${esc(u.department)}</td><td>${esc(u.role==='平台管理员'?'管理员':u.portalRole||'普通用户')}</td><td>${tag(u.enabled?'启用':'停用')}</td><td>${['业务用户','平台管理员'].includes(u.role)?btn('分配角色','ops-role',u.id,'text small'):'内部专用角色'}</td></tr>`))}</section>`;return true;
    }
    if(route==='portal-keys'||route==='api-keys'){
      const keys=M().apiKeys||[];
      $('#main').innerHTML=title(admin?'API 密钥审核':'我的 API 密钥',admin?'审核工具和数据接口调用申请，管理密钥启停及有效期。':'申请指定服务的调用权限，审核通过后领取一次性展示的密钥。',admin?'':btn('申请 API 密钥','ops-key-apply','','primary','plus'))+`<section class="panel">${table(['服务 / 申请人','类型 / 用途','状态','有效期','操作'],keys.slice().reverse().map(k=>`<tr><td>${esc(k.name)}<small>${esc(k.userName)}</small></td><td>${k.kind==='tool'?'工具':'数据'}<small>${esc(k.purpose)}</small></td><td>${tag(k.status)}</td><td>${esc(k.validUntil)}</td><td><div class="actions">${admin&&k.status==='待审核'?btn('审核','ops-key-review',k.id,'text small'):''}${admin&&['已启用','已停用'].includes(k.status)?btn(k.status==='已启用'?'停用':'启用','ops-key-toggle',k.id,'text small'):''}${!admin&&k.status==='已通过'?btn('领取密钥','ops-key-activate',k.id,'primary small'):''}${btn('详情','ops-key-detail',k.id,'text small')}</div></td></tr>`))}</section><section class="panel pm-panel" style="margin-top:22px"><h2>接口调用说明</h2><p>工具接口：<code>POST /api/v1/tools/invoke</code>；数据接口：<code>POST /api/v1/data/query</code>。</p><p>请求头使用 <code>Authorization: Bearer &lt;密钥&gt;</code>，内容类型为 <code>application/json</code>。数据权限、工具使用范围、密钥期限和服务上下架状态均在调用时检查。</p><pre class="pm-log-detail">${esc(JSON.stringify({toolId:'coordinate',parameters:{x:111.7,y:40.8,direction:'forward'}},null,2))}</pre><p>数据请求示例：<code>{"resourceId":"资源标识"}</code>。本地接口返回授权示例数据；外部工具返回入口地址。</p></section>`;return true;
    }
    if(route==='portal-security'){
      $('#main').innerHTML=title('安全配置','管理 HTTPS、IP 访问范围、请求频率与数据库备份。')+'<div id="ops-content" aria-live="polite">正在加载安全配置…</div>';
      loadSecurity(token);return true;
    }
    $('#main').innerHTML=title('系统监控','采集当前服务器资源与近一小时接口状态，每 30 秒刷新；阈值告警每分钟检查。',btn('刷新监控','ops-refresh','','','refresh')+'<a class="btn" href="#/admin/portal-security">设置告警阈值</a>')+'<div id="ops-content" aria-live="polite">正在读取监控指标…</div>';
    loadMonitor(token);return true;
  }
  async function loadSecurity(token){
    try{const r=await api('portal.securityGet');if(token!==generation)return;security=r;const c=r.config;
      $('#ops-content').innerHTML=`<form id="ops-security" data-rev="${c.rev}"><section class="panel pm-panel"><h2>证书与访问策略</h2><div class="pm-form-grid">${field('tlsEnabled','启用 HTTPS（重启服务后生效）',c.tlsEnabled,'checkbox')}${field('certPath','服务器证书 PEM 文件路径',c.certPath)}${field('keyPath','服务器私钥 PEM 文件路径',c.keyPath)}${field('whitelistEnabled','启用 IP 白名单',c.whitelistEnabled,'checkbox')}${field('networks','允许的 IP / CIDR 网段（每行一个）',c.networks.join('\n'),'textarea')}${field('rateEnabled','启用请求频率限制',c.rateEnabled,'checkbox')}${field('requestsPerMinute','每 IP 每分钟最大请求数（10–10000）',c.requestsPerMinute,'number')}${field('blockedAgents','拦截的 User-Agent 关键词（每行一个）',c.blockedAgents.join('\n'),'textarea')}</div><p class="muted">证书保存时会校验与私钥是否匹配。IP 白名单保留本机回环访问，用于配置恢复；请求频率及客户端规则保存后立即生效。</p></section><section class="panel pm-panel"><h2>自动备份与监控告警</h2><div class="pm-form-grid">${field('backupEnabled','启用自动数据库备份',c.backupEnabled,'checkbox')}${field('backupIntervalHours','自动备份间隔（小时，1–720）',c.backupIntervalHours,'number')}${field('backupKeep','保留自动备份份数（1–100）',c.backupKeep,'number')}${field('cpuThreshold','CPU 告警阈值 %',c.cpuThreshold,'number')}${field('memoryThreshold','内存告警阈值 %',c.memoryThreshold,'number')}${field('diskThreshold','磁盘告警阈值 %',c.diskThreshold,'number')}${field('responseThresholdMs','平均响应告警阈值 ms',c.responseThresholdMs,'number')}</div><p class="muted">告警显示在系统监控页和后台菜单。手动备份及还原前备份不参与自动清理。</p><button class="btn primary">保存安全配置</button></section></form><section class="panel pm-panel"><div class="section-title"><h2>数据库备份与还原</h2>${btn('立即备份','ops-backup','','primary','plus')}</div><p class="muted">备份包含本地业务数据、配置、附件和日志。还原前自动创建安全备份；服务器证书文件不包含在数据库中。</p>${table(['备份文件','大小','创建时间','操作'],r.backups.map(b=>`<tr><td>${esc(b.id)}</td><td>${(b.size/1024/1024).toFixed(2)} MB</td><td>${esc(b.at)}</td><td>${btn('还原','ops-restore',b.id,'text small')}</td></tr>`))}</section>`;
    }catch(e){if(token===generation)$('#ops-content').innerHTML=`<p class="notice">${esc(e.message)}</p>`;}
  }
  async function loadMonitor(token){
    try{const r=await api('portal.monitor');if(token!==generation)return;const m=r.metrics;
      const metric=(name,value,suffix='')=>`<div class="pm-metric"><span>${name}</span><strong>${value==null?'暂无数据':esc(value)+suffix}</strong></div>`;
      $('#ops-content').innerHTML=`<div class="pm-metrics">${metric('CPU 使用率',m.cpu,'%')}${metric('内存使用率',m.memory,'%')}${metric('磁盘使用率',m.disk,'%')}${metric('近一小时平均响应',m.responseMs,' ms')}</div><section class="panel pm-panel"><h2>服务状态</h2><p>服务已运行 ${Math.floor(m.uptimeSeconds/60)} 分钟 · 磁盘剩余 ${m.diskFreeGB} GB · 近一小时 ${m.requests} 次接口请求 · ${m.errors} 次服务器异常</p><p class="muted">采样时间：${esc(m.sampledAt)} · ${esc(m.source)}</p></section><section class="panel pm-panel"><h2>告警通知</h2>${table(['时间','告警','触发值 / 阈值','状态','恢复时间'],r.alerts.map(a=>`<tr><td>${esc(a.at)}</td><td>${esc(a.name)}</td><td>${a.value} / ${a.threshold}</td><td>${tag(a.status)}</td><td>${esc(a.resolvedAt||'—')}</td></tr>`))}</section>`;
    }catch(e){if(token===generation&&$('#ops-content'))$('#ops-content').innerHTML=`<p class="notice">${esc(e.message)}</p>`;}
    if(token===generation)timer=setTimeout(()=>loadMonitor(token),30000);
  }
  async function action(action,id){
    if(!action.startsWith('ops-'))return false;
    const key=(M().apiKeys||[]).find(k=>k.id===id);
    if(action==='ops-key-apply'){
      const scopes=[...M().tools.map(t=>['tool:'+t.id,'工具 · '+t.name]),...D().resources.filter(r=>r.access==='已授权'&&['数据库表','图层服务'].includes(r.type)).map(r=>['data:'+r.id,'数据 · '+r.name])];
      modal('申请 API 密钥',`<form id="ops-key-apply">${field('scope','指定服务',scopes[0]?.[0]||'','select',scopes)}${field('purpose','使用用途','','textarea')}${field('days','有效天数（1–365）',30,'number')}<button class="btn primary">提交审核</button></form>`);
    }else if(action==='ops-key-review')modal('审核 API 密钥',`<p>${esc(key.userName)} · ${esc(key.name)}</p><p>${esc(key.purpose)}</p><form id="ops-key-review" data-id="${id}" data-rev="${key.rev}">${field('status','审核结果','已通过','select',['已通过','已驳回'])}${field('note','审核意见','','textarea')}<button class="btn primary">提交审核</button></form>`);
    else if(action==='ops-key-toggle'){await api('portal.keyToggle',{id,rev:key.rev});await ctx.reload();toast('密钥状态已更新');}
    else if(action==='ops-key-activate'){
      const r=await api('portal.keyActivate',{id,rev:key.rev});await ctx.loadOnly();modal('保存 API 密钥',`<p>密钥仅本次展示，请复制并妥善保存。关闭后无法再次查看。</p><textarea class="pm-secret" readonly aria-label="API 密钥">${esc(r.secret)}</textarea><p>服务：${esc(key.name)} · 有效期至 ${esc(key.validUntil)}</p>`);render();
    }else if(action==='ops-key-detail'){
      const report=ctx.state().mode==='admin'?await api('portal.report',{}):null;
      modal('密钥申请详情',`<p>服务标识：<code>${esc(key.targetId)}</code></p><p>申请用途：${esc(key.purpose)}</p><p>状态：${esc(key.status)} · 有效期：${esc(key.validUntil)}</p>${report?`<p>成功调用次数：${report.stats.keyCalls[key.id]||0}</p>`:''}${key.history.map(h=>`<blockquote>${esc(h.status)}：${esc(h.note)}<small>${esc(h.actor)} · ${esc(h.at)}</small></blockquote>`).join('')}`);
    }else if(action==='ops-role'){
      const u=D().users.find(x=>x.id===id);modal('分配门户角色',`<p>${esc(u.name)} · ${esc(u.department)}</p><form id="ops-role" data-id="${id}" data-rev="${u.rev||1}">${field('role','门户角色',u.role==='平台管理员'?'管理员':u.portalRole||'普通用户','select',['普通用户','企业用户','管理员'])}<button class="btn primary">保存角色</button></form>`);
    }else if(action==='ops-backup'){const r=await api('portal.backup');toast('备份已创建：'+r.id);render();}
    else if(action==='ops-restore')modal('还原数据库',`<p>将用所选备份替换当前本地数据库。还原前会自动备份当前数据。</p><p><code>${esc(id)}</code></p><form id="ops-restore" data-id="${esc(id)}">${field('confirm','输入完整备份文件名确认')}<button class="btn danger">确认还原</button></form>`);
    else if(action==='ops-refresh')render();
    return true;
  }
  document.addEventListener('submit',async e=>{
    const f=e.target;if(!f.id.startsWith('ops-'))return;e.preventDefault();const button=f.querySelector('button');if(button?.disabled)return;if(button)button.disabled=true;
    const v=Object.fromEntries(new FormData(f));
    try{
      if(f.id==='ops-security'){
        for(const k of ['tlsEnabled','whitelistEnabled','rateEnabled','backupEnabled'])v[k]=f.elements[k].checked;
        for(const k of ['requestsPerMinute','backupIntervalHours','backupKeep','cpuThreshold','memoryThreshold','diskThreshold','responseThresholdMs'])v[k]=Number(v[k]);
        for(const k of ['networks','blockedAgents'])v[k]=v[k].split('\n').map(x=>x.trim()).filter(Boolean);
        await api('portal.securitySave',{rev:Number(f.dataset.rev),values:v});toast('配置已保存；HTTPS 变更需重启服务');render();
      }else if(f.id==='ops-key-apply'){
        const [kind,targetId]=v.scope.split(':');await api('portal.keyApply',{kind,targetId,purpose:v.purpose,days:Number(v.days)});closeModal();await ctx.reload();toast('密钥申请已提交');
      }else if(f.id==='ops-key-review'){await api('portal.keyReview',{...v,id:f.dataset.id,rev:Number(f.dataset.rev)});closeModal();await ctx.reload();toast('审核完成');}
      else if(f.id==='ops-role'){await api('portal.userRole',{...v,id:f.dataset.id,rev:Number(f.dataset.rev)});closeModal();await ctx.reload();toast('角色已更新');}
      else if(f.id==='ops-restore'){const r=await api('portal.restore',{id:f.dataset.id,confirm:v.confirm});closeModal();await ctx.reload();toast('还原完成；已保留还原前备份 '+r.safetyBackup);}
    }catch(e){toast(e.message);}finally{if(button?.isConnected)button.disabled=false;}
  });
  return {render,action};
}
