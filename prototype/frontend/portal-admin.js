import {randomUUID} from './uuid.js';
export function createPortalAdmin(ctx){
  const {$,esc,icon,btn,tag,api,nav,modal,closeModal,toast}=ctx;
  const D=()=>ctx.state().D,M=()=>D().portalManagement||{tools:[],materials:[],registrations:[]};
  let generation=0,report=null,filters={kind:'all',q:'',start:'',end:'',page:1},listQuery='';
  const names={'portal-tools':'能力服务管理','portal-materials':'下载资料管理','portal-users':'注册申请审核','portal-analytics':'门户统计分析','portal-audit':'统一日志审计'};
  const title=(name,desc,actions='')=>`<div class="page-heading"><div><div class="eyebrow">PORTAL MANAGEMENT</div><h1>${esc(name)}</h1><p>${esc(desc)}</p></div><div class="actions">${actions}</div></div>`;
  const field=(key,label,value='',type='text',options=[])=>`<label class="pm-field"><span>${esc(label)}</span>${type==='select'?`<select name="${key}">${options.map(o=>{const [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${esc(v)}" ${String(v)===String(value)?'selected':''}>${esc(t)}</option>`;}).join('')}</select>`:type==='textarea'?`<textarea name="${key}" rows="3" maxlength="2000">${esc(value)}</textarea>`:`<input name="${key}" type="${type}" value="${esc(value)}" ${type==='number'?'min="0" max="9999"':'maxlength="1000"'}>`}</label>`;
  const empty=()=>'<div class="empty"><h3>暂无记录</h3><p>新增内容或调整筛选条件。</p></div>';
  const table=(heads,rows)=>`<div class="table-scroll"><table><thead><tr>${heads.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${heads.length}">${empty()}</td></tr>`}</tbody></table></div>`;
  const metric=(name,value)=>`<div class="pm-metric"><span>${esc(name)}</span><strong>${esc(value)}</strong></div>`;
  const date=value=>esc(String(value||'').replace('T',' '));
  function saveFile(filename,content,mime='text/csv;charset=utf-8'){
    const url=URL.createObjectURL(new Blob([content],{type:mime})),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function materialCards(){
    const rows=[...M().materials].sort((a,b)=>(a.order||0)-(b.order||0));
    return `<section class="pm-downloads panel"><div class="section-title"><h2>资料附件下载</h2><span>${rows.length} 份已发布资料</span></div>${rows.length?`<div class="pm-material-grid">${rows.map(r=>`<article><span class="tile">${icon('file')}</span><div><small>${esc(r.category)} · v${r.version}</small><h3>${esc(r.name)}</h3><p>${esc(r.description||r.source||'')}</p><small>${esc(r.filename)} · ${(r.size/1024).toFixed(1)} KB</small></div>${btn('下载附件','pm-download',r.id,'small')}</article>`).join('')}</div>`:'<p class="muted">暂无已发布附件，可先下载上方资讯正文。</p>'}</section>`;
  }
  function render(){
    generation++;
    const {mode,route}=ctx.state();
    if(mode==='front'&&route==='register'){
      $('#main').innerHTML=title('门户账号申请','提交申请后由管理员审核，审核结果可在本页查看。')+`<div class="pm-columns"><section class="panel pm-panel"><h2>填写申请资料</h2><form id="pm-register">${field('name','姓名')}${field('department','工作单位')}${field('contact','联系方式')}${field('reason','申请用途','','textarea')}<p class="muted">当前为演示账号申请，请使用虚构资料。</p><button class="btn primary">提交申请</button></form></section><section class="panel pm-panel"><h2>我的申请记录</h2>${M().registrations.slice().reverse().map(r=>`<article class="pm-review-item"><h3>${esc(r.name)} ${tag(r.status)}</h3><p>${esc(r.department)} · ${date(r.createdAt)}</p>${r.history.map(h=>`<blockquote>${esc(h.note)}<small>${esc(h.actor)} · ${date(h.at)}</small></blockquote>`).join('')}${r.userId?'<p>账号已开通，可在个人服务中选择对应演示身份。</p>':''}</article>`).join('')||empty()}</section></div>`;
      return true;
    }
    if(mode!=='admin'||!names[route])return false;
    if(D().user.role!=='平台管理员'){$('#main').innerHTML=title('暂无管理权限','请使用平台管理员身份。');return true;}
    if(['portal-analytics','portal-audit'].includes(route)){
      $('#main').innerHTML=title(names[route],route==='portal-audit'?'按时间、类型、用户或追踪号查询操作、访问和接口记录。':'根据门户页面访问和工具调用记录汇总，可按日期查看。',route==='portal-audit'?btn('导出筛选结果','pm-export','','','download'):'')+`<form id="pm-report-filter" class="pm-filter">${field('start','开始日期',filters.start,'date')}${field('end','结束日期',filters.end,'date')}${route==='portal-audit'?field('kind','日志类型',filters.kind,'select',[['all','全部'],['operation','操作日志'],['visit','访问日志'],['api','API 调用'],['tool','浏览器工具'],['download','资料下载']])+field('q','用户 / 操作 / 追踪号',filters.q):''}<button class="btn primary">查询</button>${btn('重置','pm-reset','','')}</form><div id="pm-report" aria-live="polite"><p class="muted">正在读取记录…</p></div>`;
      loadReport(route,generation);return true;
    }
    const entity=route==='portal-tools'?'tools':route==='portal-materials'?'materials':'registrations';
    const rows=M()[entity].filter(r=>!listQuery||[r.name,r.category,r.contact,r.status].join(' ').includes(listQuery)).slice().sort((a,b)=>entity==='registrations'?b.createdAt.localeCompare(a.createdAt):(a.order||0)-(b.order||0));
    $('#main').innerHTML=title(names[route],entity==='tools'?'注册工具、绑定执行能力并发布。下架后门户入口和新的调用同步停用。':entity==='materials'?'上传和替换资料附件，保存草稿后发布到门户资讯下载。':'审核门户账号申请，通过后开通业务用户，并分配所属组织与访问区域。',entity!=='registrations'?btn(entity==='tools'?'注册工具':'新增资料','pm-edit',entity+':','primary','plus')+(entity==='tools'?btn('类型与模块权限','pm-tool-permissions','',''):''):'<a class="btn" href="#/admin/identity">用户与角色管理</a>')+`<form id="pm-list-filter" class="pm-filter">${field('q','搜索名称、分类或状态',listQuery)}<button class="btn">搜索</button>${btn('重置','pm-reset','','')}</form><section class="panel">`+(entity==='registrations'?table(['申请人 / 单位','联系方式','申请用途','状态','提交时间','操作'],rows.map(r=>`<tr><td>${esc(r.name)}<small>${esc(r.department)}</small></td><td>${esc(r.contact)}</td><td>${esc(r.reason)}</td><td>${tag(r.status)}</td><td>${date(r.createdAt)}</td><td>${btn(r.status==='待审核'?'审核':'查看结果','pm-review',r.id,'text small')}</td></tr>`)):table(['名称 / 分类',entity==='tools'?'执行能力':'附件','版本 / 状态','更新时间','操作'],rows.map(r=>`<tr><td><strong>${esc(r.name)}</strong><small>${esc(r.category)}</small></td><td>${esc(entity==='tools'?({coordinate:'坐标转换',area:'面积量算',buffer:'点缓冲区',overlay:'叠加分析',compliance:'项目合规核查',external:'外部工具入口'}[r.engine]||r.engine):r.filename)}${entity==='materials'?`<small>${(r.size/1024).toFixed(1)} KB</small>`:''}</td><td>v${r.version} ${tag(r.status)}${r.status==='草稿'&&r.published?'<small>前台仍使用已发布版本</small>':''}</td><td>${date(r.updated)}</td><td><div class="actions">${btn('编辑','pm-edit',entity+':'+r.id,'text small')}${entity==='tools'?`<a class="btn text small" href="#/admin/intelligence-links?asset=${encodeURIComponent('tools:'+r.id)}">关联与影响</a>`:''}${btn(r.status==='已停用'?'上架':'发布','pm-publish',entity+':'+r.id,'text small')}${r.versions?.length?btn('版本','pm-versions',entity+':'+r.id,'text small'):''}${r.status!=='已停用'&&r.published?btn('下架','pm-disable',entity+':'+r.id,'text small'):''}${r.status==='已停用'||!r.published?btn('删除','pm-delete',entity+':'+r.id,'text small'):''}</div></td></tr>`)))+'</section>'+(entity==='tools'?'<p class="muted">调用统计见 <a href="#/admin/portal-analytics">门户访问分析</a>。外部工具统计入口打开次数；本地工具记录执行结果。</p>':'');
    return true;
  }
  async function loadReport(route,token){
    try{const r=await api('portal.report',filters);if(token!==generation||ctx.state().route!==route)return;report=r;
      if(route==='portal-analytics'){
        const s=r.stats,series=(label,items)=>`<section class="panel pm-panel"><h2>${label}</h2>${items.length?items.map(x=>`<div class="pm-bar-row"><span>${esc(x.name)}</span><div><i style="width:${Math.max(2,x.count/Math.max(...items.map(a=>a.count))*100)}%"></i></div><b>${x.count}</b></div>`).join(''):empty()}</section>`;
        $('#pm-report').innerHTML=`<div class="pm-metrics">${metric('资源总数',s.resources)}${metric('数据服务调用',s.dataCalls)}${metric('数据申请次数',s.applications)}${metric('已审核明细通过率',s.approvalRate==null?'—':s.approvalRate+'%')}${metric('页面访问 PV',s.pv)}${metric('访问用户 UV',s.uv)}${metric('工具调用 / 入口打开',s.toolCalls)}${metric('资料与数据下载',s.downloads)}</div><div class="pm-columns">${series('栏目访问分布',s.pages)}${series('每日访问趋势',s.days)}</div>${series('用户访问次数',s.users)}${series('热门资源排行（详情浏览与数据下载）',s.popular)}<section class="panel pm-panel"><h2>工具使用统计</h2><p class="muted">浏览器工具记录计算结果；异步核查统计任务提交，200 表示已受理；外部工具仅统计入口打开。耗时为浏览器执行或接口响应时间。</p>${table(['工具','调用次数','成功 / 已受理','失败','平均耗时 ms'],s.tools.map(t=>`<tr><td>${esc(t.name)}</td><td>${t.total}</td><td>${t.success}</td><td>${t.failed}</td><td>${t.averageMs}</td></tr>`))}</section>`;
      }else $('#pm-report').innerHTML=`<section class="panel">${table(['时间','类型','用户','操作 / 对象','结果','详情'],r.rows.map((x,i)=>`<tr><td>${date(x.at)}</td><td>${esc(({operation:'操作',visit:'访问',api:'API',tool:'工具',download:'下载'})[x.kind])}</td><td>${esc(x.actor||'—')}</td><td>${esc(x.action)}<small>${esc(x.name||'')}</small></td><td>${esc(x.status||'完成')}</td><td>${btn('查看','pm-log',String(i),'text small')}</td></tr>`))}<div class="pagination"><span>共 ${r.total} 条 · 第 ${r.page} / ${Math.max(1,Math.ceil(r.total/25))} 页</span><div>${r.page>1?btn('上一页','pm-page',String(r.page-1),'small'):''}${r.page*25<r.total?btn('下一页','pm-page',String(r.page+1),'small'):''}</div></div></section>`;
    }catch(e){if(token===generation&&$('#pm-report'))$('#pm-report').innerHTML=`<p class="notice">${esc(e.message)}</p>`;}
  }
  const modules=['坐标转换','叠加分析','面积核算','缓冲分析','合规核查','空间检查','空间查询','空间入库','空间编辑','外部服务'];
  const moduleFor=engine=>({coordinate:'坐标转换',overlay:'叠加分析',area:'面积核算',buffer:'缓冲分析',compliance:'合规核查','spatial-check':'空间检查','spatial-query':'空间查询','spatial-store':'空间入库','spatial-edit':'空间编辑'})[engine]||'外部服务';
  let permissionDraft=[];
  function permissionDialog(){
    modal('工具类型与功能模块权限',`<p>在单工具角色与资源授权基础上，进一步限制指定角色的工具类型或功能模块。规则命中后禁止使用，管理员保留维护权限。</p><form id="pm-tool-permissions">${permissionDraft.map((r,i)=>`<div class="tc-permission-row">${field('role'+i,'限制角色',r.role,'select',['普通用户','企业用户'])}${field('category'+i,'工具类型',r.category,'select',[['*','全部类型'],...new Set(M().tools.map(t=>t.category))])}${field('module'+i,'功能模块',r.module,'select',[['*','全部模块'],...modules])}<button type="button" class="btn" data-action="pm-permission-remove" data-id="${i}">移除</button></div>`).join('')||'<p>尚未设置额外限制。</p>'}<div class="actions"><button class="btn" type="button" data-action="pm-permission-add">增加限制</button><button type="submit" class="btn primary">保存权限</button></div></form>`,true);
  }
  function readPermissions(){const f=document.querySelector('#pm-tool-permissions');if(f)permissionDraft=permissionDraft.map((r,i)=>({role:f.elements['role'+i].value,category:f.elements['category'+i].value,module:f.elements['module'+i].value}));}
  function edit(entity,id){
    const r=M()[entity].find(r=>r.id===id)||{};
    const engines=[['coordinate','坐标转换'],['area','面积量算'],['buffer','点缓冲区'],['overlay','叠加分析'],['compliance','项目合规核查'],['external','外部工具入口'],['spatial-check','空间几何检查'],['spatial-query','本地工作图层查询'],['spatial-store','本地工作图层入库'],['spatial-edit','本地工作图层编辑']];
    modal(entity==='tools'?'维护工具':'维护下载资料',`<form id="pm-editor" data-entity="${entity}" data-id="${esc(id)}" data-rev="${r.rev||0}"><div class="pm-form-grid">${field('name','名称',r.name)}${field('category','分类',r.category)}${field('description','介绍',r.description,'textarea')}${field('order','排序',r.order||1,'number')}${entity==='tools'?field('provider','提供方',r.provider||D().user.department)+field('publisher','发布单位',r.publisher||D().user.department)+field('region','数源单位所在地区',r.region||'全区','select',D().regions)+field('directoryId','共享目录',r.directoryId||'','select',[['','未编目'],...(D().centers?.directories||[]).filter(d=>['公共目录','工具服务'].includes(d.kind)).map(d=>[d.id,d.name])])+field('interfaceType','接口类型',r.interfaceType||'JSON / HTTPS')+field('module','功能模块',r.module||moduleFor(r.engine),'select',modules)+field('usageMode','使用方式',r.usageMode||(r.resourceId?'申请授权':'直接使用'),'select',['直接使用','申请授权'])+`<label class="pm-field"><span>工具截图（PNG / JPEG / WebP，最多2MB）</span><input name="screenshotFile" type="file" accept="image/png,image/jpeg,image/webp">${r.screenshot?'<small>已上传，留空保留现有截图</small><label><input name="removeScreenshot" type="checkbox">移除现有截图</label>':''}</label>`+field('apiDescription','接口说明',r.apiDescription||'','textarea')+field('requestParameters','请求参数 JSON 数组（name、type、required、description；留空使用组件默认值）',r.requestParameters||'','textarea')+field('inputExample','请求示例 JSON',r.inputExample||'','textarea')+field('outputExample','返回示例 JSON（留空使用组件默认值）',r.outputExample||'','textarea')+field('outputDescription','返回结构说明',r.outputDescription||'','textarea')+field('engine','执行能力',r.engine||'external','select',engines)+field('audience','允许使用的门户角色',r.audience||'全部用户','select',['全部用户','普通用户','企业用户','管理员'])+field('url','外部工具 HTTPS 入口',r.url)+field('resourceId','关联内部工具资源',r.resourceId||'','select',[['','独立门户工具'],...D().resources.filter(x=>x.type==='工具服务').map(x=>[x.id,x.name])]):field('source','发布单位 / 来源',r.source)+field('contentId','关联资讯 / 政策（可选）',r.contentId||'','select',[['','独立资料'],...D().knowledge.map(k=>[k.id,k.name])])+`<label class="pm-field"><span>${r.filename?'替换附件（留空保留现有文件）':'资料附件'}</span><input name="file" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.mp4,.zip,.csv,.txt,.geojson"><small>${esc(r.filename||'单个文件不超过 5 MB')}</small></label>`}</div><p class="muted">保存后为草稿，发布后门户才使用新版本。关联内部工具后，调用同时校验其使用授权及上下架状态。</p><div class="form-footer"><button class="btn primary">保存草稿</button></div></form>`,true);
  }
  async function action(action,id){
    if(!action.startsWith('pm-'))return false;
    if(action==='pm-tool-permissions'){permissionDraft=structuredClone(M().toolPermissions||[]);permissionDialog();}
    else if(action==='pm-permission-add'){readPermissions();permissionDraft.push({role:'普通用户',category:'*',module:'*'});permissionDialog();}
    else if(action==='pm-permission-remove'){readPermissions();permissionDraft.splice(Number(id),1);permissionDialog();}
    else if(action==='pm-edit'){const [entity,key]=id.split(':');edit(entity,key);}
    else if(action==='pm-publish'||action==='pm-disable'){
      const [entity,key]=id.split(':'),r=M()[entity].find(r=>r.id===key);
      if(entity==='tools'&&action==='pm-publish'&&r.reviewState!=='已通过'){toast('请先在工具台账提交上架审核');nav('/admin/center-tools');return true;}
      await api(action==='pm-publish'?'portal.publish':'portal.disable',{entity,id:key,rev:r.rev});await ctx.reload();toast(action==='pm-publish'?'发布成功，门户已更新':'已下架');
    }else if(action==='pm-versions'){
      const [entity,key]=id.split(':'),r=M()[entity].find(r=>r.id===key);modal('历史发布版本',table(['版本','名称','发布时间'],(r.versions||[]).slice().reverse().map(v=>`<tr><td>v${v.version}</td><td>${esc(v.name)}</td><td>${date(v.updated)}</td></tr>`)),true);
    }else if(action==='pm-delete'){
      const [entity,key]=id.split(':'),r=M()[entity].find(r=>r.id===key);
      modal('删除内容',`<p>确认删除“${esc(r.name)}”？操作日志将保留。</p>${btn('确认删除','pm-delete-confirm',id,'danger')}`);
    }else if(action==='pm-delete-confirm'){
      const [entity,key]=id.split(':'),r=M()[entity].find(r=>r.id===key);await api('portal.delete',{entity,id:key,rev:r.rev});closeModal();await ctx.reload();toast('内容已删除');
    }else if(action==='pm-review'){
      const r=M().registrations.find(r=>r.id===id);
      modal('注册申请审核',`<h3>${esc(r.name)} · ${esc(r.department)}</h3><p>${esc(r.reason)}</p>${r.history.map(h=>`<blockquote>${esc(h.status)}：${esc(h.note)}<small>${esc(h.actor)} · ${date(h.at)}</small></blockquote>`).join('')}${r.status==='待审核'?`<form id="pm-review" data-id="${r.id}" data-rev="${r.rev}">${field('status','审核结果','已通过','select',['已通过','已驳回'])}${field('orgId','通过后所属组织','','select',D().platform.organizations.map(o=>[o.id,o.name]))}${field('portalRole','通过后门户角色','普通用户','select',['普通用户','企业用户'])}${field('region','通过后访问区域','全区','select',D().regions)}${field('note','审核意见','','textarea')}<button class="btn primary">提交审核</button></form>`:tag(r.status)}`);
    }else if(action==='pm-download'){
      const r=await api('portal.materialDownload',{id}),bytes=Uint8Array.from(atob(r.content),c=>c.charCodeAt(0));saveFile(r.filename,bytes,r.mime);toast('资料已下载');
    }else if(action==='pm-page'){filters.page=Number(id);render();}
    else if(action==='pm-reset'){filters={kind:'all',q:'',start:'',end:'',page:1};listQuery='';render();}
    else if(action==='pm-log')modal('日志详情',`<pre class="pm-log-detail">${esc(JSON.stringify(report.rows[Number(id)],null,2))}</pre>`,true);
    else if(action==='pm-export'){
      const r=await api('portal.report',{...filters,page:1,size:5000}),keys=['id','at','kind','actor','action','name','status','durationMs','ip','error'];
      const csv=v=>{let value=String(v??'');if(/^[\s]*[=+@-]/.test(value))value="'"+value;return '"'+value.replace(/"/g,'""')+'"';};
      saveFile('门户审计日志.csv','\ufeff'+[keys.join(','),...r.rows.map(x=>keys.map(k=>csv(x[k])).join(','))].join('\r\n'));toast(`已导出 ${r.rows.length} 条${r.total>5000?'，请缩小日期范围导出其余记录':''}`);
    }
    return true;
  }
  document.addEventListener('submit',async e=>{
    const f=e.target;if(!f.id.startsWith('pm-'))return;e.preventDefault();
    const button=f.querySelector('button');if(button?.disabled)return;if(button)button.disabled=true;
    const v=Object.fromEntries(new FormData(f));
    try{
      if(f.id==='pm-tool-permissions'){readPermissions();await api('portal.toolPermissions',{rules:permissionDraft,rev:M().toolPermissionsRev||1});closeModal();await ctx.reload();toast('权限已生效');}
      else if(f.id==='pm-list-filter'){listQuery=v.q.trim();render();}
      else if(f.id==='pm-report-filter'){filters={...filters,...v,page:1};render();}
      else if(f.id==='pm-editor'){
        const file=f.querySelector('[name=file]')?.files[0];delete v.file;
        const screenshot=f.querySelector('[name=screenshotFile]')?.files[0];delete v.screenshotFile;
        if(v.removeScreenshot)v.screenshot='';delete v.removeScreenshot;
        if(screenshot){if(screenshot.size>2*1024*1024)throw Error('截图不能超过2MB');v.screenshot=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('截图读取失败'));reader.readAsDataURL(screenshot);});}
        if(file){if(file.size>5*1024*1024)throw Error('附件不能超过 5 MB');v.filename=file.name;v.fileData=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(Error('文件读取失败'));r.readAsDataURL(file);});}
        await api('portal.save',{entity:f.dataset.entity,id:f.dataset.id,rev:Number(f.dataset.rev),values:v});closeModal();await ctx.reload();toast('草稿已保存，请发布后查看前台');
      }else if(f.id==='pm-review'){await api('portal.review',{...v,id:f.dataset.id,rev:Number(f.dataset.rev)});closeModal();await ctx.reload();toast('审核完成');}
      else if(f.id==='pm-register'){f.dataset.requestId ||= randomUUID();await api('portal.register',{...v,requestId:f.dataset.requestId});await ctx.reload();toast('申请已提交');}
    }catch(e){toast(e.message);}finally{if(button?.isConnected)button.disabled=false;}
  });
  return {render,action,materialCards};
}
