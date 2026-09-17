// Application runtimes stay inside the results workspace, including follow-up cases.
export function createMapApplications(ctx){
  const {esc,api,nav}=ctx,D=()=>ctx.state().D;
  let generation=0,host=null;
  const sessions=new Map(),params=()=>new URLSearchParams(location.hash.split('?')[1]);
  function url(values={}){const p=params();p.set('tab','scenes');for(const [k,v] of Object.entries(values))v==null?p.delete(k):p.set(k,v);return '/admin/integration-results?'+p;}
  function html(){return `<div class="mw-app-toolbar"><a class="btn small" href="#${esc(url({app:null,case:null,agent:null,contextCase:null,question:null}))}">← 返回应用列表</a><span>应用场景 / 当前应用</span></div><section id="mw-app-content" aria-live="polite"><p class="notice">正在读取应用…</p></section>`;}
  function button(label,action,id){return `<button class="btn small" data-action="${action}" data-id="${esc(id)}">${label}</button>`;}
  async function bind(){
    const token=++generation;host=document.querySelector('#mw-app-content');if(!host)return;
    const id=params().get('app');
    try{
      if(!D().integration.results.scenes.some(r=>r.id==='app:'+id))throw Error('应用已下架或当前身份无权访问');
      const a=await api('platform.appOpen',{id});if(token!==generation||!host?.isConnected)return;
      const heading=`<div class="mw-app-heading"><h2>${esc(a.name)}</h2><p>${esc(a.description||'')}</p></div>`;
      if(params().get('agent')){renderAgent(params().get('agent'),heading,token);return;}
      if(params().get('case')){host.innerHTML=heading+'<div id="mw-app-case"></div>';await ctx.renderApplicationCase(document.querySelector('#mw-app-case'),params().get('case'));return;}
      if(a.type==='scene'){await ctx.mountMap(host,a.targetId);return;}
      if(a.type==='workflow'){
        const cases=(D().platform.cases||[]).filter(c=>c.modelId===a.targetId);
        host.innerHTML=heading+`<section class="panel pc-padding"><h3>业务办理</h3>${button('发起事项','pc-start-model',a.targetId)}<h3>可访问的办理记录</h3><div class="mw-app-cases">${cases.map(c=>`<a href="#${esc(url({case:c.id}))}"><strong>${esc(c.name)}</strong><span>${esc(c.status)} · ${esc(c.region)}</span></a>`).join('')||'<p>暂无可访问的办理记录。</p>'}</div></section>`;return;
      }
      if(a.type==='agent'){renderAgent(a.targetId,heading,token);return;}
      host.innerHTML=heading+`<section class="panel pc-padding"><p>该应用使用外部客户端接入；当前提供本地登录验证演示。</p>${button('验证接入','pc-auth-trial',a.targetId)}</section>`;
    }catch(e){if(token===generation&&host?.isConnected)host.innerHTML='<p class="notice">'+esc(e.message)+'</p>';}
  }
  function renderAgent(id,heading,token){
    const agent=D().agents.find(a=>a.id===id);if(!agent)throw Error('智能体已停用或无权访问');
    const contextCase=params().get('contextCase')||'',key=D().user.id+':'+params().get('app')+':'+id+':'+contextCase;
    let session=sessions.get(key)||null;
    host.innerHTML=heading+`<section class="mw-app-assistant"><h3>${esc(agent.name)}</h3><div id="mw-app-messages"></div><form id="mw-app-chat"><label for="mw-app-question">业务问题</label><textarea id="mw-app-question" name="question" rows="3" required maxlength="2000" placeholder="${esc(agent.question||'输入业务问题')}"></textarea><button class="btn primary">发送</button><span id="mw-app-chat-status" role="status"></span></form></section>`;
    const paint=()=>{const el=host?.querySelector('#mw-app-messages');if(!el)return;el.innerHTML=(session?.messages||[]).map(m=>`<article class="mw-app-message ${m.role==='user'?'is-user':''}"><strong>${m.role==='user'?'我':esc(agent.name)}</strong><p>${esc(m.text)}</p>${(m.resourceIds||[]).map(id=>button(D().resources.find(r=>r.id===id)?.name||'查看资源','resource',id)).join('')}${(m.citations||[]).map(c=>`<details><summary>${esc(c.name)} · v${esc(c.version)}</summary>${(c.chunks||[]).map(x=>`<p>${esc(x.text)}</p>`).join('')}</details>`).join('')}</article>`).join('')||'<p class="muted">在当前应用中提问，回答会保留资源入口和引用依据。</p>';};
    paint();const form=host.querySelector('#mw-app-chat');host.querySelector('#mw-app-question').value=params().get('question')||'';
    form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('button'),status=form.querySelector('#mw-app-chat-status');if(button.disabled)return;const question=new FormData(form).get('question').trim();if(!question)return;button.disabled=true;status.textContent='正在查询…';try{
      const result=await api('chat',{agentId:id,sessionId:session?.id||'',question,businessContext:contextCase?{caseId:contextCase}:null});sessions.set(key,result);if(token!==generation||!form.isConnected)return;session=result;paint();form.reset();status.textContent='已完成';
    }catch(err){if(form.isConnected)status.textContent=err.message;}finally{if(form.isConnected)button.disabled=false;}};
  }
  function navigate(path){
    if(!document.querySelector('.mw-workspace')||!params().get('app'))return false;
    let match=path.match(/^\/?(?:front|admin)\/cases\/([^/?]+)/);
    if(match){nav(url({case:decodeURIComponent(match[1]),agent:null,contextCase:null,question:null}));return true;}
    if(/^\/?(?:front|admin)\/workbench/.test(path)){nav(url({case:null,agent:null,contextCase:null,question:null}));return true;}
    match=path.match(/^\/?front\/scenes\/([^/?]+)/);
    if(match){const a=(D().platform.apps||[]).map(a=>a.published||a).find(a=>a.type==='scene'&&a.targetId===decodeURIComponent(match[1])&&D().integration.results.scenes.some(r=>r.id==='app:'+a.id));if(a){nav(url({app:a.id,case:null,agent:null}));}else ctx.toast('当前应用没有可访问的关联场景');return true;}
    return false;
  }
  function launch(agent,context,question){if(!params().get('app'))return false;nav(url({agent,contextCase:context?.caseId||null,question:question||null,case:null}));return true;}
  return {html,bind,navigate,launch,destroy(){generation++;host=null;}};
}
