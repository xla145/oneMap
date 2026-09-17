"""Local, persistent intelligence-center prototype. No real AI or government API."""
import argparse
import gzip
import json
import re
import sqlite3
import threading
import uuid
import time
import portal_management as portal_admin
import portal_operations
import portal_keys
import admin_design
import centers
import operations_center
import integration
from copy import deepcopy
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from seed import seed, REGIONS, TYPES
import capabilities as cap
import qa_comparison
import platform_domain as platform
import platform_store
import spatial
import public_portal
import analysis_jobs
from news_content import migrate as migrate_news
from platform_seed import migrate as migrate_platform
from capabilities import Invalid, require

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'demo.sqlite3'
LOCK = threading.RLock()
ENTITIES = {'resources', 'knowledge', 'indicators', 'corpora', 'agents', 'templates', 'dictionaries'}

def now(): return datetime.now().isoformat(timespec='seconds')
def uid(): return uuid.uuid4().hex[:12]

def find(rows, id):
    return next((x for x in rows if x['id'] == id), None)

def user_for(s, id):
    u = find(s['users'], id)
    require(u and u['enabled'], '演示身份不可用', 403)
    return u

def admin(u): require(u['role'] == '平台管理员', '需要平台管理员身份', 403)
def asset_admin(u,entity,row=None):
    if entity=='knowledge' and u['role']=='流程管理员':
        require(not row or platform.within_scope(u,row.get('region','全区')),'知识记录超出管理区划',403)
    else:admin(u)
def published(row):
    if row and row['status'] != '已停用' and not row.get('suspended'): return deepcopy(row.get('published'))
    return None

def active(s, entity): return [p for r in s[entity] if (p := published(r))]
def allowed(u, r):
    return cap.visible(u,r)

def resource_status(s,u,r):
    if cap.sharing_policy(r)=='限制使用':return '限制使用'
    if cap.sharing_policy(r)=='开放使用' or any(cap.grant_valid(g,u,r) for g in s['grants']): return '已授权'
    if any(a['userId']==u['id'] and a['status']!='已撤回' and any(i['resourceId']==r['id'] and i['status']=='待审核' for i in a['items']) for a in s['applications']): return '申请中'
    return '可申请'

def public_resources(s,u):
    out=[]
    for r in active(s,'resources'):
        if allowed(u,r):
            r['access']=resource_status(s,u,r)
            if r['type']=='工具服务':r['applicationCount']=sum(any(i['resourceId']==r['id'] for i in a['items']) for a in s['applications'])
            if r['access']!='已授权': r.pop('sample',None)
            r['hasServiceUrl']=bool(r.get('serviceUrl'));r['hasDownloadUrl']=bool(r.get('downloadUrl'))
            r.pop('serviceUrl',None);r.pop('downloadUrl',None)
            r.pop('dataRows',None)
            r['fields']=[f for f in r.get('fields',[]) if f.get('display',True)]
            out.append(r)
    return out

def bootstrap(s,u,mode):
    cap.migrate(s)
    spatial.migrate(s)
    admin_design.migrate(s)
    a = mode=='admin'
    require(not a or u['role'] in platform.ADMIN_ROLES or integration.ia.internal_access(s,u), '该身份没有后台访问权限',403)
    full = a and u['role']=='平台管理员'
    result = {e:deepcopy(s[e]) if full else active(s,e) for e in ENTITIES}
    if not full:
        result['resources']=public_resources(s,u)
        result['knowledge']=[v for r in s['knowledge'] if (v:=cap.knowledge_channel(r,'index'))]
        for e in ['knowledge','indicators','agents']: result[e]=[r for r in result[e] if cap.visible(u,r)]
        for row in result['indicators']:
            for key in ['values','expression','field','resourceId']:row.pop(key,None)
        for d in result['knowledge']:
            for chunk in d.get('chunks',[]): chunk.pop('vector',None)
        # Internal configuration is never included in business bootstrap.
        for e in ['templates','dictionaries','corpora']: result[e]=[]
        for ag in result['agents']:
            for k in ['steps','resourceIds','templateIds','knowledgeIds','indicatorIds']: ag.pop(k,None)
    if a and u['role']=='流程管理员':
        result['knowledge']=[deepcopy(r) for r in s['knowledge'] if platform.within_scope(u,r.get('region','全区'))]
    result.update(user=deepcopy(u),accounts=[{k:v for k,v in x.items() if k in ['id','name','role','department']} for x in s['users'] if x['enabled']],regions=REGIONS,
        batches=deepcopy(s.get('batches',[])) if full else [], evaluations=deepcopy(s.get('evaluations',[])) if full else [], feedbackDrafts=deepcopy(s.get('feedbackDrafts',[])) if full else [],
        users=deepcopy(s['users']) if full else [], memories=deepcopy(s['memories']) if full else [deepcopy(x) for x in s['memories'] if x['id']==u['id']],
        sessions=spatial.sanitize_sessions(s,u,[deepcopy(x) for x in s['sessions'] if x['userId']==u['id']]),
        memorySessions=[dict(id=x['id'],userId=x['userId'],name=x['name'],context=deepcopy(x['context']),updated=x['updated'],turns=len(x['messages'])//2) for x in s['sessions']] if full else [],
        applications=[deepcopy(x) for x in s['applications'] if (a and u['role'] in ['平台管理员','资源审批人员']) or x['userId']==u['id']],
        feedback=[deepcopy(x) for x in s['feedback'] if full or x['userId']==u['id']],
        calls=deepcopy(s['calls'][-100:]) if full else [],audit=deepcopy(s['audit'][-100:]) if full else [],serverTime=now(),platform=platform.bootstrap(s,u,mode))
    result['grants']=admin_design.grant_rows(s,u)
    result['portalArticles']=[v for r in s['knowledge'] if (v:=cap.knowledge_channel(r,'portal')) and cap.visible(u,v)]
    for article in result['portalArticles']:
        for key in ['chunks','graph','entities','edges','pipeline']:article.pop(key,None)
    result['publicPortal']=public_portal.bootstrap(s,u,mode)
    result['portalManagement']=portal_admin.bootstrap(s,u,mode)
    result['operations']=operations_center.bootstrap(s,u,mode)
    result['centers']=centers.bootstrap(s,u,mode)
    result['integration']=integration.bootstrap(s,u,mode)
    return result

def log(s,u,action,name):
    row=portal_admin.event(s,u,'operation',action,name=name)
    s['audit'].append(dict(row))
    s['audit']=s['audit'][-300:]

def clean_text(v,limit=10000):
    require(isinstance(v,str) and len(v)<=limit,'文本格式或长度不正确')
    return v.strip()

def validate(s,e,v):
    require(v.get('name') and len(v['name'])<=100,'名称必填，且最多100字')
    if e=='resources':
        for key in ['serviceUrl','downloadUrl']:portal_admin.https(v.get(key,''))
        require(v.get('type') in TYPES,'资源类型不正确')
        require(v.get('region') in REGIONS,'请选择覆盖区域')
        require(cap.sharing_policy(v) in ['开放使用','申请使用','限制使用'],'请选择共享策略')
        require(v.get('visibility') in ['业务用户','管理员'],'请选择可发现范围')
        require(isinstance(v.get('fields',[]),list),'字段列表格式错误')
        for f in v.get('fields',[]): require(f.get('name') and f.get('label'),'字段名和中文名称必填')
        names=[f['name'] for f in v.get('fields',[])]
        require(len(names)==len(set(names)),'字段名称不能重复')
        require(all(find(s['resources'],x) and x!=v.get('id') for x in v.get('relations',[])),'关系资源不存在或关联了自身')
        require(not v.get('templateId') or find(s['templates'],v['templateId']),'元数据模板不存在')
        cap.relation_edges(s,v);cap.data_rows(v)
        for f in v.get('fields',[]):
            require(not f.get('dictionary') or any(f['dictionary'] in [d['id'],d['name'],d['code']] for d in s['dictionaries']),'字段字典不存在')
        if v.get('sqlName'): require(re.fullmatch(r'[A-Za-z_]\w*',v['sqlName']) and not any(r['id']!=v.get('id') and r.get('sqlName')==v['sqlName'] for r in s['resources']),'示例 SQL 表名无效或重复')
    if e=='knowledge':
        require(v.get('body'),'文档正文不能为空');cap.clean_document(v['body']);cap.graph(v)
    if e=='indicators':
        require(find(s['resources'],v.get('resourceId')),'请选择关联数据资源')
        require(v.get('caliber') and v.get('unit'),'指标单位和统计口径必填')
        cap.calculate(s,v)
        require(all(find(s['knowledge'],i) for i in cap.ids(v.get('knowledgeIds'))),'知识依据不存在')
    if e=='dictionaries': cap.dictionary_items(v)
    if e=='templates': template_fields(v)
    if e=='corpora':
        require(v.get('type') in ['问答样例','提示词模板','SQL 模板','API 模板'],'语料类型不正确')
        require(v.get('body'),'语料内容不能为空')
        require(v.get('type')!='问答样例' or v.get('answer'),'问答样例需要标准答案')
        expected=set(re.findall(r'\{\{\s*(\w+)\s*\}\}|:(\w+)',v['body']))
        expected={a or b for a,b in expected}
        actual=set(filter(None,[x.strip() for x in v.get('variables','').split(',')]))
        require(expected<=actual,'模板包含未定义的参数：'+','.join(expected-actual))
        if v.get('outputTemplate'):
            cap.render_template(v['outputTemplate'],dict(question='',region='',count=0,resources='',topic='',answer=''))
        require(all(find(s['resources'],i) for i in cap.ids(v.get('expectedResources'))),'预期资源不存在')
    if e=='agents':
        require(type(v.get('mapEnabled',False)) is bool,'地图启用状态无效')
        if v.get('mapEnabled'):
            scene=published(find(s['platform']['scenes'],v.get('mapSceneId')));require(scene,'请选择已发布地图场景')
            require(set(cap.ids(v.get('mapResourceIds'))) <= {l['resourceId'] for l in scene['config']['layers']},'地图资源需属于所选场景')
            require(cap.ids(v.get('mapResourceIds')) and all((r:=published(find(s['resources'],i))) and r['type']=='图层服务' for i in cap.ids(v.get('mapResourceIds'))),'地图资源必须是已发布图层')
        require(v.get('category') in ['资源检索','知识问答','指标分析'],'智能体场景不正确')
        steps=v.get('steps','').splitlines()
        valid={'识别条件','检索资源','展示结果','发起申请','理解问题','检索知识','回答并引用','识别指标','核对口径','示例试算','调用知识智能体','调用指标智能体','执行语料模板'}
        require(steps and len(steps)<=20 and all(x in valid for x in steps),'请选择支持的编排步骤（最多20步）')
        for key in ['knowledgeAgentId','indicatorAgentId']:
            require(not v.get(key) or (find(s['agents'],v[key]) and v[key]!=v.get('id')),'协作智能体不存在或引用自身')
        for key,target in [('resourceIds','resources'),('knowledgeIds','knowledge'),('indicatorIds','indicators'),('templateIds','corpora')]:
            require(all(find(s[target],x.strip()) for x in v.get(key,'').split(',') if x.strip()),'绑定的资源或模板不存在')

FIELDS={
 'resources':'name type category region aliases frequency access sharingPolicy visibility source description crs fields relations templateId documentId date subtype sourceType relationRules departments dataRows sqlName serviceUrl downloadUrl dataSource serviceProtocol',
 'knowledge':'name category source tags body relations entities edges chunkSize visibility departments region',
 'indicators':'name category unit formula values caliber period region resourceId field description dataMode expression knowledgeIds visibility departments',
 'corpora':'name type scene body variables answer resourceIds category outputTemplate expectedAnswer expectedResources expectedSteps agentId',
 'agents':'name category description icon color question steps resourceIds knowledgeIds templateIds indicatorIds memory knowledgeAgentId indicatorAgentId visibility departments region mapEnabled mapSceneId mapResourceIds',
 'templates':'name type description fields fieldSchema',
 'dictionaries':'name code aliases items',
}

def save_record(s,u,p):
    e=p.get('entity');asset_admin(u,e);require(e in ENTITIES,'未知业务类型')
    old=find(s[e],p.get('id'))
    if old:asset_admin(u,e,old)
    if p.get('id'): require(old,'记录不存在',404)
    if old: require(old['rev']==p.get('rev'),'记录已更新，请关闭编辑器并刷新后重试',409)
    values=p.get('values',{});require(isinstance(values,dict),'数据格式错误')
    v=deepcopy(old) if old else dict(id=uid(),version=0,rev=0,versions=[],status='草稿')
    if old and old['status']=='已停用':v['suspended']=True
    for k,val in values.items():
        if k in FIELDS[e].split():
            if isinstance(val,str):
                if e=='knowledge' and k=='body':cap.clean_document(val)
                else:val=clean_text(val,200000 if k=='dataRows' else 10000)
            v[k]=val
    if e=='resources' and 'sharingPolicy' in values:
        v['access']='已授权' if v['sharingPolicy']=='开放使用' else '可申请'
    asset_admin(u,e,v);validate(s,e,v)
    if e=='knowledge': cap.process_document(v)
    if e=='dictionaries': v['entries']=cap.dictionary_items(v)
    if e=='resources': v['relationEdges']=cap.relation_edges(s,v)
    v.update(rev=v['rev']+1,updated=now(),status='草稿')
    if old: s[e][s[e].index(old)]=v
    else: s[e].append(v)
    log(s,u,'保存草稿',v['name']);return v

def scope_ids(rows, ag, key):
    ids=[x.strip() for x in ag.get(key,'').split(',') if x.strip()]
    return [r for r in rows if not ids or r['id'] in ids]

def parse_context(q,ctx):
    for region in REGIONS:
        if region in q:ctx['region']=region
    if '最近' in q or '近一个月' in q:ctx['period']='最近30天'
    if '全部时间' in q:ctx['period']='全部时间'
    year=re.search(r'20\d{2}年',q)
    if year:ctx['period']=year.group()
    topics=['地灾','地质灾害','耕地','农田','矿权','矿产','生态','植被','草原','国土','规划']
    matched=[w for w in topics if w in q]
    if matched:ctx['topic']=matched[0]
    typ=next((t for t,words in [('数据库表',['库表','记录表','数据表']),('图层服务',['图层']),('工具服务',['工具']),('知识文档',['文档'])] if any(w in q for w in words)),None)
    if typ:ctx['type']=typ
    if '所有类型' in q or '一起' in q:ctx.pop('type',None)
    return matched

def chat(s,u,p):
    q=clean_text(p.get('question',''),1000);require(q,'请输入问题')
    ag=published(find(s['agents'],p.get('agentId','a1')));require(ag and cap.visible(u,ag),'智能体不可访问或未发布',404)
    sess=find(s['sessions'],p.get('sessionId'));require(not sess or sess['userId']==u['id'],'不能访问其他用户会话',403)
    mem=find(s['memories'],u['id']) or {};enabled=mem.get('enabled') and ag.get('memory',False)
    if not sess:
        ctx=dict(region=mem.get('region','全区') if enabled else '全区',period='全部时间',topic=mem.get('domain','') if enabled else '')
        if enabled and mem.get('summary'):parse_context(mem['summary'],ctx)
        source=None
        if p.get('resumeFrom'):
            source=find(s['sessions'],p['resumeFrom']);require(source and source['userId']==u['id'],'无法接续其他用户任务',403)
        elif enabled and re.search('继续上次|接续|接力',q): source=find(s['sessions'],mem.get('sourceSession'))
        if source:ctx=deepcopy(source['context'])
        sess=dict(id=uid(),userId=u['id'],agentId=ag['id'],name=q[:24],messages=[],context=ctx,updated=now(),parentSession=source['id'] if source else '',memorySource=mem.get('summary','') if enabled else '')
        if source and source.get('spatialContext'):sess['spatialContext']=deepcopy(source['spatialContext'])
        s['sessions'].append(sess)
    require(sess['agentId']==ag['id'],'请选择本会话的智能体')
    ctx=sess['context']
    business=p.get('businessContext') or sess.get('businessContext')
    if business:
        verified=platform.validate_context(s,u,business)
        sess['businessContext']=verified
        ctx.update(region=verified['region'],period=verified.get('period','全部时间'))
    if isinstance(p.get('context'),dict):
        c=p['context'];require(c.get('region','全区') in REGIONS,'查询区域无效');period=c.get('period','全部时间')
        require(period in ['全部时间','最近30天'] or re.fullmatch(r'20\d{2}年',period),'查询时间无效');ctx.update(region=c.get('region',ctx['region']),period=period)
    if 'spatialContext' in p and p['spatialContext'] is None:sess.pop('spatialContext',None)
    map_input=p.get('spatialContext',sess.get('spatialContext'))
    spatial_result=None
    if map_input is not None:
        parse_context(q,ctx)
        spatial_result=spatial.analyze(s,u,ag,map_input,ctx,q)
        sess['spatialContext']=deepcopy(spatial_result['context'])
    def run(agent,chain=()):
        require(agent['id'] not in chain and len(chain)<4,'智能体存在循环调用或调用过深')
        require(cap.visible(u,agent),'无权调用该智能体',403)
        out=dict(resourceIds=[],citations=[],indicators=[],text='',trace=[],sampleIds=[],templateRuns=[],canApply=False)
        terms=[q];results=[];answer='';display=False
        for step in agent['steps'].splitlines():
            trace=dict(step=step,agent=agent['name'],version=agent['version'],status='完成',input=q,output='')
            if step in ['识别条件','理解问题','识别指标']:
                matched=parse_context(q,ctx);terms=[q]+matched
                if re.search('只看|仅看|相关|一起|所有类型|适合我的|继续|接续|分析',q) and ctx.get('topic'):terms+= [ctx['topic']]
                trace['output']=dict(ctx)
            elif step=='检索资源':
                base=scope_ids(active(s,'resources'),agent,'resourceIds');base=[r for r in base if allowed(u,r)]
                base=[r for r in base if (ctx['region']=='全区' or r['region'] in ['全区',ctx['region']]) and (not ctx.get('type') or r['type']==ctx['type'])]
                if ctx['period']=='最近30天':base=[r for r in base if r.get('date',r['updated'][:10])>=(date.today()-timedelta(days=30)).isoformat()]
                def score(r):
                    text,aliases=cap.semantic_text(s,r)
                    return sum(2 for t in terms if t and t in text)+sum(3 for a in aliases if a and a in q)
                results=sorted([r for r in base if score(r)],key=score,reverse=True)[:8]
                out['resourceIds']=[r['id'] for r in results];trace['output']=out['resourceIds']
            elif step=='检索知识':
                out['citations']=cap.search_knowledge(s,u,q,agent.get('knowledgeIds',''));trace['output']=[d['name'] for d in out['citations']]
            elif step=='回答并引用':
                answer='\n'.join(d['chunks'][0]['text'] for d in out['citations']);display=True;trace['output']=answer or '没有可引用片段'
            elif step=='核对口径':trace['output']='按已发布指标定义，检查关联资源授权与字段'
            elif step=='示例试算':
                if spatial_result and (spatial_result['context']['mode']!='region' or not any(w in q for w in ['指标','目标','达标'])):
                    trace['output']='当前为图斑查询，行政区指标不混入本次图斑统计';out['trace'].append(trace);continue
                comparison=qa_comparison.compare(s,u,agent,q,ctx,REGIONS)
                if comparison is not None:
                    out['templateRuns'].append(comparison)
                    answer='已按同一统计口径生成对比，请查看明细与差额。' if comparison['rows'] else comparison['answer']
                    trace['output']=comparison;out['trace'].append(trace);continue
                rows=scope_ids(active(s,'indicators'),agent,'indicatorIds');errors=[]
                for row in rows:
                    if not cap.visible(u,row) or not any(w in row['name']+row.get('category','') for w in terms):continue
                    try:
                        context={'region':ctx['region']}
                        if re.fullmatch(r'20\d{2}年',ctx['period']):context['period']=ctx['period']
                        out['indicators'].append(cap.calculate(s,row,u,context))
                    except Invalid as e:errors.append(dict(name=row['name'],error=e.message))
                trace['output']=dict(results=out['indicators'],errors=errors)
                if errors and not out['indicators']:trace['status']='无可计算结果'
                if out['indicators']:answer='已按发布口径计算指标，可查看数据来源、依赖版本与统计结果。'
            elif step in ['调用知识智能体','调用指标智能体']:
                key,default=('knowledgeAgentId','a2') if step=='调用知识智能体' else ('indicatorAgentId','a3')
                child=published(find(s['agents'],agent.get(key) or default));require(child,'协作智能体未发布')
                child=deepcopy(child)
                for key in ['resourceIds','knowledgeIds','indicatorIds']:
                    parent_ids=cap.ids(agent.get(key));child_ids=cap.ids(child.get(key))
                    if parent_ids:child[key]=','.join(i for i in parent_ids if not child_ids or i in child_ids) or '__none__'
                nested=run(child,chain+(agent['id'],))
                out['templateRuns']+=nested['templateRuns'];out['citations']+=nested['citations'];out['indicators']+=nested['indicators'];out['resourceIds']=list(dict.fromkeys(out['resourceIds']+nested['resourceIds']))
                if nested['text']:answer+='\n'+nested['text']
                trace['children']=nested['trace'];trace['output']=dict(agent=child['name'],resources=len(nested['resourceIds']),citations=len(nested['citations']),indicators=len(nested['indicators']))
            elif step=='执行语料模板':
                for template in scope_ids(active(s,'corpora'),agent,'templateIds'):
                    if template['type'] not in ['SQL 模板','API 模板']:continue
                    result=cap.template_trial(s,u,template,dict(question=q,region=ctx['region']))
                    out['templateRuns'].append(dict(name=template['name'],version=template['version'],**result))
                trace['output']=out['templateRuns']
            elif step=='展示结果':display=True;trace['output']=dict(resources=len(out['resourceIds']),indicators=len(out['indicators']),citations=len(out['citations']))
            elif step=='发起申请':out['canApply']=bool(out['resourceIds']);trace['output']='可在回答内填写申请用途与期限' if out['canApply'] else '没有待申请资源'
            out['trace'].append(trace)
        samples=scope_ids(active(s,'corpora'),agent,'templateIds')
        samples += [r for r in active(s,'corpora') if r.get('sourceAgent')==agent['id'] and r not in samples]
        exact=next((r for r in reversed(samples) if r['type']=='问答样例' and r['body']==q),None)
        if display and out['resourceIds']:
            if exact:answer=exact['answer']+ ('\n'+answer if answer else '');out['sampleIds'].append(exact['id'])
            else:
                template=next((r for r in samples if r['type']=='提示词模板' and r.get('outputTemplate')),None)
                names=[published(find(s['resources'],i))['name'] for i in out['resourceIds']]
                params=dict(question=q,region=ctx['region'],count=len(names),resources='、'.join(names),topic=ctx.get('topic',''),answer=answer)
                if template:
                    answer=cap.render_template(template['outputTemplate'],params)+ ('\n'+answer if answer else '')
                    out['trace'].append(dict(step='应用提示词',agent=agent['name'],status='完成',input=cap.render_template(template['body'],params),output=answer,version=template['version']))
                elif not answer:answer=f"找到 {len(names)} 项相关资源，可查看详情或申请使用。"
        if display and '检索资源' in agent['steps'] and not answer:
            service_terms={'estate':'不动产|房产|权属','progress':'进度|办件|审批','guide':'数据申请|材料|流程'}
            guides=[r for r in public_portal.active(s.get('publicPortal',{}).get('services',[])) if re.search(service_terms.get(r['id'],r'(?!)'),q)]
            if guides:
                answer='\n\n'.join(r['name']+'：'+r['body']+'\n来源：'+r['source']+'（演示）' for r in guides)
                out['trace'].append(dict(step='查阅已发布办事指南',status='完成',input=q,output=[r['id'] for r in guides]))
        if not display:out.update(resourceIds=[],citations=[],indicators=[],templateRuns=[],canApply=False);answer='执行已结束，编排未配置结果展示节点。'
        out['text']=answer.strip() or ('模板已执行，请查看结果。' if out['templateRuns'] else '暂未找到匹配内容。请调整区域、时间或业务关键词。')
        return out
    result=run(ag)
    if spatial_result:
        result['analysisResult']=spatial_result
        if not result['resourceIds'] and not result['citations'] and not result['indicators'] and not result['templateRuns']:result['text']='地图查询已完成，请查看本轮地图结果与统计口径。'
        result['trace'].append(dict(step='地图范围查询',status=spatial_result['status'],input=spatial_result['context'],output=dict(count=(spatial_result['statistics'] or {}).get('count'),caliber=spatial_result['caliber'])))
    if enabled:
        if mem.get('skill')=='入门':result['text']+='\n业务说明：库表用于查数据，图层用于看位置；指标口径说明数字的统计范围。'
        elif mem.get('skill')=='专家':result['text']+='\n专业核验：请结合统计口径、来源版本和空间参考使用结果。'
        if mem.get('detail')=='详细':result['text']+='\n请核对资源更新时间、适用范围、单位与引用版本。'
    msg=dict(id=uid(),role='assistant',kind=ag['category'],context=deepcopy(ctx),at=now(),agentVersion=ag['version'],**result)
    sess['messages'] += [dict(id=uid(),role='user',text=q,at=now()),msg];sess['updated']=now()
    if enabled:
        questions=[x['text'] for x in sess['messages'] if x['role']=='user'][-6:]
        resources=list(dict.fromkeys(i for x in sess['messages'] if x['role']=='assistant' for i in x.get('resourceIds',[])))[:12]
        indicators=list(dict.fromkeys(i['name'] for x in sess['messages'] if x['role']=='assistant' for i in x.get('indicators',[])))[:6]
        facts=dict(sessionId=sess['id'],topic=ctx.get('topic',''),region=ctx['region'],period=ctx['period'],questions=questions,resourceIds=resources,indicators=indicators,nextAction='继续筛选或申请资源' if resources else '继续分析业务问题')
        mem['facts']=[f for f in mem.get('facts',[]) if f['sessionId']!=sess['id']][-9:]+[facts]
        mem['recentSummary']=f"主题：{facts['topic']}；区域：{ctx['region']}；时间：{ctx['period']}。关键追问：{'；'.join(questions)}。涉及资源 {len(resources)} 项；指标：{'、'.join(indicators) or '无'}。下一步：{facts['nextAction']}。"
        mem.update(sourceSession=sess['id'],summaryUpdated=now())
    s['calls'].append(dict(id=uid(),at=now(),userId=u['id'],user=u['name'],agent=ag['name'],version=ag['version'],question=q,status='完成' if msg['resourceIds'] or msg['citations'] or msg['indicators'] or msg['templateRuns'] else '无结果',resourceIds=msg['resourceIds'],citations=[d['documentId'] for d in msg['citations']],sampleIds=msg['sampleIds'],steps=ag['steps'].splitlines(),trace=deepcopy(msg['trace']),mode='本地执行'))
    return spatial.sanitize_sessions(s,u,[deepcopy(sess)])[0]

def execute(s,u,action,p):
    cap.migrate(s)
    spatial.migrate(s)
    admin_design.migrate(s)
    require(isinstance(p,dict),'参数格式错误')
    if isinstance(action,str) and action.startswith('integration.'):
        return integration.execute(s,u,action,p)
    if isinstance(action,str) and action.startswith('operations.'):
        return operations_center.execute(s,u,action,p,{'save':save_record,'publish':lambda state,user,payload:execute(state,user,'publish',payload)})
    if isinstance(action,str) and action.startswith('centers.'):
        return centers.execute(s,u,action,p,{'save':save_record,'publish':lambda state,user,payload:execute(state,user,'publish',payload)})
    if isinstance(action,str) and action.startswith('portal.'):
        if action=='portal.report':return portal_admin.report(DB,s,u,p)
        if action in ['portal.securityGet','portal.securitySave','portal.backup','portal.monitor']:return portal_operations.execute(DB,s,u,action,p)
        return portal_admin.execute(s,u,action,p)
    if isinstance(action,str) and action.startswith('public.'):
        result=public_portal.execute(s,u,action,p)
        if action not in ['public.map','public.progress']:
            log(s,u,action,result.get('name') or result.get('title') or result.get('filename') or result.get('id','门户操作'))
        return result
    if isinstance(action,str) and action.startswith('platform.'):
        return platform.execute(s,u,action,p)
    if action=='mapRuntime':return spatial.runtime(s,u,p.get('agentId','a1'),p.get('sceneId'))
    if action in EXTRA_ACTIONS: return extra_action(s,u,action,p)
    if action=='grant.revoke':
        require(u['role'] in ['平台管理员','资源审批人员'],'无授权管理权限',403)
        g=find(s['grants'],p.get('id'));require(g,'授权不存在',404)
        require(g['rev']==p.get('rev'),'授权已更新，请刷新',409)
        require(g['status']=='有效','授权已撤销')
        reason=clean_text(p.get('reason',''),1000);require(len(reason)>=5,'撤销原因至少5个字')
        g.update(status='已撤销',rev=g['rev']+1,revokedAt=now(),revokedBy=u['id'])
        g['history'].append(dict(at=now(),actor=u['name'],action='撤销授权',note=reason))
        log(s,u,'撤销授权',g['id']);return deepcopy(g)
    if action=='knowledge.channel':
        r=find(s['knowledge'],p.get('id'));require(r,'文档不存在',404);asset_admin(u,'knowledge',r)
        channel=p.get('channel');require(channel in ['portal','index'],'发布渠道无效')
        require(channel!='portal' or u['role']=='平台管理员','无门户发布权限',403)
        require(r['rev']==p.get('rev'),'文档已更新，请刷新',409)
        require(type(p.get('enabled')) is bool,'请选择发布或退出')
        if 'channels' not in r:
            r['channels']={c:cap.published(r) for c in ['portal','index']}
        if p['enabled']:
            validate(s,'knowledge',r)
            r.update(version=r['version']+1,status='已发布',suspended=False,updated=now())
            snapshot={k:deepcopy(v) for k,v in r.items() if k not in ['channels','channelHistory','published','versions']}
            r['channels'][channel]=snapshot
            if r.get('published'):r['versions'].append(deepcopy(r['published']))
            r['published']=deepcopy(snapshot)
        else:r['channels'][channel]=None
        r['rev']+=1
        r.setdefault('channelHistory',[]).append(dict(at=now(),actor=u['name'],channel=channel,enabled=p['enabled'],version=r['version']))
        log(s,u,'更新内容渠道',r['name']+':'+channel);return {'ok':True}
    if action=='save': return save_record(s,u,p)
    if action in ['publish','disable','delete','duplicate']:
        e=p.get('entity');asset_admin(u,e);require(e in ENTITIES,'未知类型')
        r=find(s[e],p.get('id'));require(r,'记录不存在',404)
        asset_admin(u,e,r)
        require(r['rev']==p.get('rev'),'记录已更新，请刷新后重试',409)
        if action=='delete':
            require(not r.get('published') or (e=='knowledge' and r['status']=='已停用'),'已发布内容请先停用；数据资产保留历史不能直接删除')
            refs=[str(x) for entity in ENTITIES for x in s[entity] if x['id']!=r['id']]
            require(not any(r['id'] in x for x in refs),'记录被关联，不能删除')
            s[e].remove(r)
        elif action=='duplicate':
            copy={k:deepcopy(v) for k,v in r.items() if k in FIELDS[e].split()};copy['name']+='（副本）'
            return save_record(s,u,dict(entity=e,values=copy))
        elif action=='publish':
            require(e!='knowledge' or 'channels' not in r,'请分别发布门户资讯或更新知识索引')
            validate(s,e,r)
            if r.get('published'): r['versions'].append(deepcopy(r['published']))
            r.update(status='已发布',suspended=False,version=r['version']+1,rev=r['rev']+1,updated=now())
            r['published']={k:deepcopy(v) for k,v in r.items() if k not in ['published','versions','channels','channelHistory']}
        else:
            r.update(status='已停用',suspended=True,rev=r['rev']+1,updated=now())
            if e=='knowledge' and 'channels' in r:
                r['channels']={'portal':None,'index':None}
                r.setdefault('channelHistory',[]).append(dict(at=now(),actor=u['name'],channel='all',enabled=False,version=r['version']))
        log(s,u,{'publish':'发布版本','disable':'停用','delete':'删除草稿'}[action],r['name']);return {'ok':True}
    if action=='trial':
        admin(u);e=p.get('entity');r=find(s.get(e,[]),p.get('id'));require(r,'记录不存在')
        if e=='indicators': return cap.calculate(s,r,u)
        if e=='knowledge':
            q=clean_text(p.get('question',''));return {'chunks':[c for d in cap.search_knowledge(s,u,q,rows=[r]) for c in d['chunks']]}
        if e=='agents':
            work=deepcopy(s);draft=find(work['agents'],r['id']);draft['published']=deepcopy(r);draft['status']='已发布';draft['suspended']=False
            result=chat(work,user_for(work,p.get('userId','u1')),dict(agentId=r['id'],question=p.get('question') or r.get('question','地灾巡查')))
            return result['messages'][-1]
        require(e=='corpora','该模块不支持试运行')
        return cap.template_trial(s,u,r,p.get('params',{}))
    if action=='chat': return chat(s,u,p)
    if action=='apply':
        ids=list(dict.fromkeys(p.get('resourceIds',[])));require(ids,'请先选择资源')
        purpose=clean_text(p.get('purpose',''),1000);require(len(purpose)>=5,'用途至少填写5个字')
        until=p.get('validUntil','')
        try: end=date.fromisoformat(until)
        except (ValueError,TypeError): raise Invalid('请选择有效的使用截止日期')
        require(date.today()<end<=date.today()+timedelta(days=365),'使用期限应在未来一年以内')
        old=next((a for a in s['applications'] if a['userId']==u['id'] and a['requestId']==p.get('requestId') and p.get('requestId')),None)
        if old: return old
        resources=public_resources(s,u)
        rows=[find(resources,id) for id in ids]
        require(all(rows),'部分资源已停用或不可访问')
        require(all(r['access']=='可申请' for r in rows),'部分资源已授权或已申请，请刷新清单')
        methods={r['id']:centers.method_for(r,clean_text(p.get('method',''),100)) for r in rows}
        a=dict(id='SQ-'+datetime.now().strftime('%Y%m%d')+'-'+uid()[:5].upper(),userId=u['id'],user=u['name'],purpose=purpose,validUntil=until,status='待审核',requestId=p.get('requestId',uid()),at=now(),rev=1,items=[dict(resourceId=r['id'],name=r['name'],type=r['type'],method=methods[r['id']],status='待审核',note='') for r in rows],history=[dict(at=now(),actor=u['name'],text='已提交资源使用申请')])
        s['applications'].append(a);log(s,u,'提交申请',a['id']);return a
    if action in ['decide','cancel','supplement']:
        a=find(s['applications'],p.get('id'));require(a,'申请不存在',404);require(a['rev']==p.get('rev'),'申请已更新，请刷新',409)
        if action=='decide':
            require(u['role'] in ['平台管理员','资源审批人员'],'无审批权限',403)
            require(a['status']!='已撤回','申请已撤回')
            i=next((x for x in a['items'] if x['resourceId']==p.get('resourceId')),None);require(i and i['status']=='待审核','该资源已处理')
            decision=p.get('decision');require(decision in ['已通过','已驳回'],'请选择审批结果')
            note=clean_text(p.get('note',''),1000);require(len(note)>=5,'办理说明至少5个字')
            r=published(find(s['resources'],i['resourceId']));require(decision=='已驳回' or r,'该资源已停用，不能授权')
            approved_until=a['validUntil']
            if decision=='已通过':
                require(cap.sharing_policy(r)!='限制使用','资源已限制使用，不能新增授权')
                approved_until=p.get('approvedUntil') or a['validUntil']
                try: approved_date=date.fromisoformat(approved_until)
                except (ValueError,TypeError): raise Invalid('核准截止日期无效')
                require(date.today()<=approved_date<=date.fromisoformat(a['validUntil']),'核准期限不能超过申请期限或早于今天')
            i.update(status=decision,note=note,approvedUntil=approved_until if decision=='已通过' else '')
            if decision=='已通过':
                s['grants'].append(dict(id='grant-'+uid(),userId=a['userId'],resourceId=i['resourceId'],validUntil=approved_until,status='有效',rev=1,sourceApplicationId=a['id'],sourceItemId=i['resourceId'],deliveryStatus='已生效',createdAt=now(),history=[dict(at=now(),actor=u['name'],action='审批授权',note=note)]))
            if decision=='已通过':centers.on_grant(s,u,s['grants'][-1],a,i)
            states=[x['status'] for x in a['items']]
            a['status']='待审核' if '待审核' in states else '已通过' if all(x=='已通过' for x in states) else '已驳回' if all(x=='已驳回' for x in states) else '部分通过'
            text=i['name']+'：'+decision+'。'+note
        else:
            require(a['userId']==u['id'],'不能修改其他人的申请',403)
            require(any(x['status']=='待审核' for x in a['items']),'申请已办理完成')
            if action=='cancel':
                require(all(x['status']=='待审核' for x in a['items']),'已有明细办理，不能整单撤回')
                a['status']='已撤回'
                for i in a['items']: i['status']='已撤回'
                text='申请人撤回申请'
            else:
                text=clean_text(p.get('note',''),1000);require(len(text)>=5,'补充说明至少5个字')
        a['history'].append(dict(at=now(),actor=u['name'],text=text));a['rev']+=1;log(s,u,action,a['id'])
        if action=='decide':
            pl=migrate_platform(s);platform.emit(pl,u,'resource.request.decided',dict(id=a['id'],name=a['id'],rev=a['rev']),a['userId'])
        return a
    if action=='preferences':
        target=p.get('userId',u['id']);require(target==u['id'] or u['role']=='平台管理员','不能修改其他用户记忆',403)
        m=find(s['memories'],target);require(m,'用户记忆不存在');require(m['rev']==p.get('rev'),'记忆已更新，请刷新',409)
        require(p.get('region') in REGIONS,'区域不正确');require(p.get('detail') in ['简洁','详细'],'回答偏好不正确')
        require(p.get('skill',m.get('skill','业务熟悉')) in ['入门','业务熟悉','专家'],'技能等级无效')
        m.setdefault('history',[]).append({k:deepcopy(v) for k,v in m.items() if k!='history'})
        m['skill']=p.get('skill',m.get('skill','业务熟悉'))
        m.update(region=p['region'],domain=clean_text(p.get('domain',''),100),detail=p['detail'],summary=clean_text(p.get('summary',''),2000),enabled=bool(p.get('enabled')),rev=m['rev']+1)
        log(s,u,'修改记忆偏好',m['name']);return m
    if action=='feedback':
        sess=find(s['sessions'],p.get('sessionId'));require(sess and sess['userId']==u['id'],'会话不存在',404)
        msg=find(sess['messages'],p.get('messageId'));require(msg and msg['role']=='assistant','回答不存在')
        require(not any(f['messageId']==msg['id'] and f['userId']==u['id'] for f in s['feedback']),'此回答已提交反馈')
        f=dict(id=uid(),userId=u['id'],user=u['name'],sessionId=sess['id'],messageId=msg['id'],question=next(x['text'] for x in reversed(sess['messages'][:sess['messages'].index(msg)]) if x['role']=='user'),answer=msg['text'],note=clean_text(p.get('note',''),2000),status='待处理',at=now())
        require(f['note'],'请填写反馈');s['feedback'].append(f);return f
    if action in ['feedbackConvert','feedbackResolve']:
        admin(u);f=find(s['feedback'],p.get('id'));require(f,'反馈不存在')
        if action=='feedbackConvert':
            require(not f.get('sampleId'),'已转为样例，请在语料管理中修改')
            r=save_record(s,u,dict(entity='corpora',values=dict(name=f['question'][:40],type='问答样例',scene='资源检索',body=f['question'],answer=f['answer'],variables='',resourceIds='',category='反馈改进')))
            r['sourceAgent']=find(s['sessions'],f['sessionId'])['agentId']
            f.update(status='待改进',sampleId=r['id'])
        else: f['status']='已处理'
        return f
    if action=='userScope':
        admin(u);target=find(s['users'],p.get('id'));require(target and target['role']=='业务用户','仅支持调整演示业务用户')
        require(p.get('region') in REGIONS,'请选择区域');target['region']=p['region'];log(s,u,'调整访问范围',target['name']);return target
    if action=='reset':
        admin(u);require(p.get('confirm')=='重置演示数据','请填写确认文本');s.clear();s.update(seed());return {'ok':True}
    raise Invalid('未知操作',404)


def template_fields(row):
    fields=[]
    for line in row.get('fieldSchema','').splitlines():
        if not line.strip():continue
        p=[x.strip() for x in line.split('|')];require(len(p)==4 and all(p[:3]),'模板字段格式：字段名|中文名|类型|同义词')
        require(p[0] not in [x['name'] for x in fields],'模板字段名重复')
        fields.append(dict(name=p[0],label=p[1],type=p[2],alias=p[3],query=True,display=True,statistic=p[2] in ['decimal','int','float'],aggregate=p[2] in ['decimal','int','float'],unit='',dictionary='',location='无',topic='',description=''))
    return fields

EXTRA_ACTIONS={'cleanPreview','templateApply','annotationSuggest','importBatch','indicatorCompare','evaluate','evaluationExport','invoke','feedbackDraft','feedbackApply'}
def extra_action(s,u,action,p):
    if action=='invoke':
        require(p.get('apiVersion','v1')=='v1','不支持的接口版本')
        session=chat(s,u,p);return dict(apiVersion='v1',sessionId=session['id'],traceId=s['calls'][-1]['id'],message=session['messages'][-1],mode='本地演示能力接口')
    admin(u)
    if action=='cleanPreview':return cap.clean_document(p.get('body',''))
    if action=='templateApply':
        t=find(s['templates'],p.get('id'));require(t,'模板不存在');return dict(fields=template_fields(t))
    if action=='annotationSuggest':
        fields=deepcopy(p.get('fields',[]));require(isinstance(fields,list),'字段格式错误')
        for f in fields:
            name=f.get('name','');hints={'area':('面积','用地面积','公顷'),'region_code':('行政区代码','区划编码',''),'target':('目标面积','保护目标','公顷'),'updated_at':('更新时间','采集日期','')}
            label,alias,unit=hints.get(name,(name.replace('_',' '),name.replace('_',' '),''))
            f.update(label=f.get('label') or label,alias=f.get('alias') or alias,unit=f.get('unit') or unit)
            if f.get('type') in ['decimal','int','float']:f.update(statistic=True,aggregate=True)
        return dict(fields=fields,mode='根据字段名与类型生成规则建议，保存前请核对')
    if action=='importBatch':
        files=p.get('files',[]);require(isinstance(files,list) and 0<len(files)<=20,'每批支持 1–20 个文件')
        batch=dict(id=uid(),at=now(),source=clean_text(p.get('source','本地批量导入'),100),items=[])
        for f in files:
            try:
                require(isinstance(f,dict),'文件格式错误');name=clean_text(f.get('name',''),100)
                require(re.search(r'\.(txt|md)$',name,re.I),'仅支持 TXT / Markdown')
                require(not f.get('error'),f.get('error','读取失败'))
                body=f.get('body','');cap.clean_document(body)
                row=save_record(s,u,dict(entity='knowledge',values=dict(name=re.sub(r'\.[^.]+$','',name),category=p.get('category','业务手册'),source=batch['source'],tags=p.get('tags',''),body=body,chunkSize=p.get('chunkSize',400),entities='',edges='',visibility=p.get('visibility','业务用户'),region='全区')))
                batch['items'].append(dict(name=name,status='完成',documentId=row['id'],chunks=len(row['chunks']),pipeline=row['pipeline'],cleaning=row['cleaning']))
            except Invalid as e:batch['items'].append(dict(name=f.get('name','未知文件') if isinstance(f,dict) else '未知文件',status='失败',error=e.message))
        batch['status']='部分完成' if any(x['status']=='失败' for x in batch['items']) else '完成'
        s['batches'].append(batch);log(s,u,'批量导入知识',batch['id']);return batch
    if action=='indicatorCompare':
        r=find(s['indicators'],p.get('id'));require(r,'指标不存在');user=user_for(s,p.get('userId','u1'))
        periods=cap.ids(p.get('periods','2025年,2026年'));regions=cap.ids(p.get('regions','呼和浩特市,包头市'))
        require(0<len(periods)<=8 and 0<len(regions)<=6 and all(x in REGIONS for x in regions),'比较范围无效')
        rows=[]
        for reg in regions:
            previous=None
            for period in periods:
                try:
                    value=cap.calculate(s,r,user,dict(region=reg,period=period));value['change']=round((value['value']-previous)/abs(previous)*100,2) if previous else None;previous=value['value'];rows.append(value)
                except Invalid as e:rows.append(dict(region=reg,period=period,error=e.message))
        return dict(name=r['name'],unit=r['unit'],rows=rows,mode='本地数据按输入周期顺序比较')
    if action=='evaluate':
        agent=find(s['agents'],p.get('agentId','a1'));require(agent,'智能体不存在')
        cases=[r for r in s['corpora'] if r['type']=='问答样例' and (not p.get('caseIds') or r['id'] in p['caseIds']) and (not r.get('agentId') or r['agentId']==agent['id'])]
        require(cases,'请先创建适用此智能体的问答评测样例')
        results=[];versions=['published','draft'] if p.get('compare',True) else [p.get('version','published')]
        for version in versions:
            for case in cases:
                work=deepcopy(s)
                if version=='draft':
                    for e in ENTITIES:
                        for r in work[e]:
                            if r['status']=='草稿' or (e=='agents' and r['id']==agent['id']):r['published']={k:deepcopy(v) for k,v in r.items() if k not in ['published','versions','channels','channelHistory']};r['status']='已发布'
                expected=dict(answer=case.get('expectedAnswer') or case.get('answer',''),resources=cap.ids(case.get('expectedResources') or case.get('resourceIds')),steps=case.get('expectedSteps','').splitlines())
                # A test case must not supply its own answer at runtime (training/test leakage).
                work['corpora']=[r for r in work['corpora'] if r['id'] not in {c['id'] for c in cases}]
                try:
                    actual=chat(work,user_for(work,p.get('userId','u1')),dict(agentId=agent['id'],question=case['body']))['messages'][-1]
                    steps=[t['step'] for t in actual['trace']];reasons=[]
                    if expected['answer'] and expected['answer'] not in actual['text']:reasons.append('未包含预期答案片段')
                    if expected['resources'] and set(expected['resources'])!=set(actual['resourceIds']):reasons.append('资源集合与预期不一致')
                    cursor=0
                    for step in steps:
                        if cursor<len(expected['steps']) and step==expected['steps'][cursor]:cursor+=1
                    if cursor<len(expected['steps']):reasons.append('预期操作序列未按顺序执行')
                    results.append(dict(caseId=case['id'],name=case['name'],version=version,status='失败' if reasons else '通过',reasons=reasons,expected=expected,actual=dict(answer=actual['text'],resources=actual['resourceIds'],steps=steps),agentVersion=actual['agentVersion']))
                except Invalid as e:results.append(dict(caseId=case['id'],name=case['name'],version=version,status='失败',reasons=[e.message],expected=expected))
        run=dict(id=uid(),at=now(),agent=agent['name'],agentId=agent['id'],userId=p.get('userId','u1'),results=results,passed=sum(r['status']=='通过' for r in results),total=len(results),scope='已发布资产 vs 当前草稿资产；规则评测，测试样例不参与回答')
        s['evaluations'].append(run);log(s,u,'语料回归评测',agent['name']);return run
    if action=='evaluationExport':
        rows=[dict(messages=[dict(role='user',content=r['body']),dict(role='assistant',content=r['answer'])],metadata=dict(id=r['id'],version=r['version'],expectedResources=cap.ids(r.get('expectedResources')),expectedSteps=r.get('expectedSteps','').splitlines())) for r in s['corpora'] if r['type']=='问答样例']
        return dict(filename='智能中心训练样例.jsonl',content='\n'.join(json.dumps(r,ensure_ascii=False) for r in rows),count=len(rows))
    if action=='feedbackDraft':
        f=find(s['feedback'],p.get('id'));require(f,'反馈不存在');kind=p.get('kind');require(kind in ['metadata','memory'],'请选择改进目标')
        target=p.get('targetId') if kind=='metadata' else f['userId'];require(find(s['resources'] if kind=='metadata' else s['memories'],target),'改进目标不存在')
        text=clean_text(p.get('text',''),2000);require(text,'请填写人工确认的改进内容')
        d=dict(id=uid(),feedbackId=f['id'],kind=kind,targetId=target,text=text,status='待确认',at=now());s['feedbackDrafts'].append(d);return d
    if action=='feedbackApply':
        d=find(s['feedbackDrafts'],p.get('id'));require(d and d['status']=='待确认','改进草稿已处理或不存在')
        if d['kind']=='metadata':
            r=find(s['resources'],d['targetId']);saved=save_record(s,u,dict(entity='resources',id=r['id'],rev=r['rev'],values=dict(aliases=','.join(dict.fromkeys(cap.ids(r.get('aliases'))+cap.ids(d['text']))))))
            d['assetId']=saved['id']
        else:
            m=find(s['memories'],d['targetId']);m.setdefault('history',[]).append({k:deepcopy(v) for k,v in m.items() if k!='history'});m['summary']=d['text'];m['rev']+=1
        d['status']='已应用';log(s,u,'反馈改进'+('元数据草稿' if d['kind']=='metadata' else '用户记忆'),d['targetId']);return d

def read_state(connection):
    state=json.loads(connection.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
    platform_store.load(connection,state)
    migrate_platform(state)
    migrate_news(state)
    public_portal.migrate(state)
    portal_admin.migrate(state)
    return state


def init_db():
    DB.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
        platform_store.initialize(c)
        old=c.execute('SELECT body FROM state WHERE id=1').fetchone()
        if not old:c.execute('INSERT INTO state VALUES(1,?)',(json.dumps(seed(),ensure_ascii=False),))
        state=read_state(c);cap.migrate(state);integration.migrate(state);operations_center.migrate(state);platform_store.save(c,state)
    analysis_jobs.initialize(DB)
    portal_admin.initialize(DB)


def deliver_events():
    """Short, local outbox transactions; no external network work under the lock."""
    while True:
        try:
            with LOCK,sqlite3.connect(DB) as c:
                state=read_state(c)
                platform.dispatch(state)
                centers.tick(state)
                platform_store.save(c,state)
        except Exception as e: print('outbox:',type(e).__name__,str(e),flush=True)
        threading.Event().wait(2)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):
            # The client may close the connection while a response is being sent.
            self.close_connection=True
    def handle_one_request(self):
        self.audit_id=portal_admin.ident();self.audit_start=time.perf_counter();self.audit_status=500;self.audit_action='';self.audit_target='';self.audit_user=None;self.audit_error=''
        try:
            super().handle_one_request()
        finally:
            if getattr(self,'path','').startswith('/api/'):
                user=self.audit_user or {}
                try:
                    portal_admin.record_request(DB,(self.audit_id,portal_admin.now(),user.get('id',''),user.get('name','未验证身份'),getattr(self,'command',''),urlparse(self.path).path,self.audit_action,self.audit_target,self.audit_status,round((time.perf_counter()-self.audit_start)*1000,2),self.client_address[0],self.audit_error))
                except sqlite3.Error as error: print('请求日志写入失败',type(error).__name__,flush=True)
    def send_response(self,code,message=None):
        self.audit_status=code
        super().send_response(code,message)
        self.send_header('X-Request-ID',self.audit_id)
    def log_message(self,fmt,*args): pass
    def reply(self,status,data):
        if status>=400:self.audit_error=str(data.get('error',''))[:300]
        body=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
        encodings={}
        for item in self.headers.get('Accept-Encoding','').lower().split(','):
            encoding,*params=item.strip().split(';')
            quality=1.0
            for param in params:
                key,_,value=param.strip().partition('=')
                if key=='q':
                    try:quality=float(value)
                    except ValueError:quality=0.0
            encodings[encoding]=quality
        compressed=len(body)>=1024 and encodings.get('gzip',encodings.get('*',0))>0
        if compressed:body=gzip.compress(body,compresslevel=5)
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Vary','Accept-Encoding')
        if compressed:self.send_header('Content-Encoding','gzip')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def enforce_security(self):
        with LOCK,sqlite3.connect(DB) as c:portal_operations.check_request(read_state(c),self.client_address[0],self.headers.get('User-Agent',''))
    def do_GET(self):
        try:self.enforce_security()
        except Invalid as e:self.reply(e.status,{'error':e.message});return
        path=urlparse(self.path).path
        if path=='/api/bootstrap':
            try:
                with LOCK,sqlite3.connect(DB) as c:
                    s=read_state(c)
                # read_state returns an independent snapshot. Neither building the
                # response nor writing to a slow client needs the shared state lock.
                u=user_for(s,self.headers.get('X-Demo-User','u1'));self.audit_user=u
                self.reply(200,bootstrap(s,u,self.headers.get('X-Demo-Mode','front')))
            except Invalid as e: self.reply(e.status,{'error':e.message})
            return
        if path in ['/','/index.html','/app.js','/style.css','/assets/inner-mongolia.geojson'] or (path.startswith('/frontend/') and Path(path).suffix in ['.js','.css'] and '..' not in path and (ROOT/path.lstrip('/')).resolve().is_relative_to(ROOT/'frontend')):
            return super().do_GET()
        # New map-first workspace: only its bundled static assets are exposed.
        if path.startswith('/gis/'):
            from urllib.parse import unquote
            decoded = unquote(path)
            target = (ROOT / decoded.lstrip('/')).resolve()
            gis_root = (ROOT / 'gis').resolve()
            allowed_suffixes = {'.html', '.js', '.css', '.json', '.geojson', '.png', '.jpg', '.webp', '.svg', '.md', '.csv'}
            if '..' not in decoded.split('/') and target.is_relative_to(gis_root) and target.is_file() and target.suffix.lower() in allowed_suffixes:
                return super().do_GET()
            return self.send_error(404)
        if path.startswith('/assets/nmg-demo/') and Path(path).suffix in ['.html','.js','.json','.geojson','.png'] and '..' not in path and (ROOT/path.lstrip('/')).resolve().is_relative_to(ROOT/'assets'/'nmg-demo'):
            return super().do_GET()
        if path.startswith('/assets/previews/') and Path(path).suffix == '.svg' and '..' not in path and (ROOT/path.lstrip('/')).resolve().is_relative_to(ROOT/'assets'/'previews'):
            return super().do_GET()
        if path.startswith('/assets/photos/') and Path(path).suffix in ['.jpg','.html'] and '..' not in path and (ROOT/path.lstrip('/')).resolve().is_relative_to(ROOT/'assets'/'photos'):
            return super().do_GET()
        self.send_error(404)
    def do_POST(self):
        try:
            self.enforce_security()
            path=urlparse(self.path).path
            require(path in ['/api/action','/api/v1/agents/invoke','/api/v1/tools/invoke','/api/v1/data/query'],'接口不存在',404)
            origin=self.headers.get('Origin')
            require(not origin or urlparse(origin).netloc==self.headers.get('Host'),'请求来源无效',403)
            length=int(self.headers.get('Content-Length','0'));require(0<length<=11000000,'请求过大',413)
            try: body=json.loads(self.rfile.read(length))
            except (ValueError,UnicodeError): raise Invalid('JSON 格式错误')
            require(isinstance(body,dict),'请求格式错误')
            if path in ['/api/v1/tools/invoke','/api/v1/data/query']:
                kind='tool' if path=='/api/v1/tools/invoke' else 'data'
                key=body.get('toolId' if kind=='tool' else 'resourceId')
                self.audit_action='tools.invoke' if kind=='tool' else 'data.query';self.audit_target=str(key or '')[:200]
                with LOCK,sqlite3.connect(DB) as c:
                    s=read_state(c);u,credential,target=portal_keys.authenticate(s,self.headers.get('Authorization',''),kind,key);self.audit_user=u
                    result=portal_keys.invoke(target,body.get('parameters',{})) if kind=='tool' else public_portal.execute(s,u,'public.download',{'id':key})
                    portal_admin.event(s,u,'operation','密钥调用',credential['id'],target['name'])
                    integration.xp.record_call(s,u,('tool:' if kind=='tool' else 'resource:')+str(key),self.audit_id)
                    platform_store.save(c,s);c.commit()
                self.reply(200,dict(requestId=self.audit_id,result=result));return
            self.audit_action=str(body.get('action','invoke'))[:100]
            payload=body.get('payload',{})
            require(isinstance(payload,dict),'参数格式错误')
            self.audit_target=str(payload.get('toolId',payload.get('id',payload.get('resourceId',payload.get('entity','')))))[:200]
            if body.get('action')=='portal.restore':
                with LOCK:
                    with sqlite3.connect(DB) as c:s=read_state(c);u=user_for(s,self.headers.get('X-Demo-User','u1'));self.audit_user=u
                    result=portal_operations.execute(DB,s,u,'portal.restore',payload)
                    with sqlite3.connect(DB) as c:
                        s=read_state(c);portal_admin.event(s,u,'operation','还原数据库',payload.get('id',''),result['safetyBackup']);platform_store.save(c,s);c.commit()
                self.reply(200,result);return
            if path=='/api/action' and body.get('action')=='integration.ai.ask':
                import map_ai
                with LOCK,sqlite3.connect(DB) as c:
                    snapshot=read_state(c);u=user_for(snapshot,self.headers.get('X-Demo-User','u1'));self.audit_user=u
                    integration.migrate(snapshot)
                result=map_ai.execute(snapshot,u,'ask',payload)
                if result.get('queryId'):
                    row=map_ai.own(snapshot,u,result['queryId'])
                    with LOCK,sqlite3.connect(DB) as c:
                        current=read_state(c);current_user=user_for(current,u['id']);integration.migrate(current)
                        map_ai.save_query(current,current_user,row)
                        platform_store.save(c,current);c.commit()
                self.reply(200,result);return
            if path=='/api/action' and isinstance(body.get('action'),str) and body['action'].startswith(('analysis.','integration.analysis.')):
                action=body['action'].replace('integration.analysis.','analysis.');area_limit=None
                with LOCK,sqlite3.connect(DB) as c:
                    s=read_state(c);u=user_for(s,self.headers.get('X-Demo-User','u1'));self.audit_user=u
                    if body['action'].startswith('integration.analysis.'):
                        require(integration.ia.rights(s,u)['analyze'],'需要成果空间分析授权',403)
                        settings=integration.migrate(s)['settings']['published'];area_limit=min(settings['maxAreaHa'],settings.get('roleAreaLimits',{}).get(u['role'],settings['maxAreaHa']))
                    if action in ['analysis.spatial','analysis.create']:

                        engine='overlay' if action=='analysis.spatial' else 'compliance'
                        key=payload.get('toolId',engine);portal_admin.tool(s,key,engine,u);self.audit_target=key
                result=analysis_jobs.dispatch(DB,u['id'],action,body.get('payload',{}),area_limit=area_limit)
                if action=='analysis.spatial':
                    with LOCK,sqlite3.connect(DB) as c:
                        s=read_state(c);integration.xp.record_call(s,u,'tool:'+str(key),self.audit_id);platform_store.save(c,s);c.commit()
                if action=='analysis.get' and result.get('status') in ['成功','部分完成'] and result.get('result'):
                    with LOCK,sqlite3.connect(DB) as c:
                        s=read_state(c);integration.xp.record_call(s,u,'tool:compliance','analysis-job:'+result['id']);platform_store.save(c,s);c.commit()
                self.reply(200,result)
                return
            with LOCK,sqlite3.connect(DB) as c:
                s=read_state(c);u=user_for(s,self.headers.get('X-Demo-User','u1'));self.audit_user=u
                result=execute(s,u,'invoke' if path=='/api/v1/agents/invoke' else body.get('action'),body if path=='/api/v1/agents/invoke' else body.get('payload',{}));platform_store.save(c,s);c.commit()
            self.reply(200,result)
        except Invalid as e: self.reply(e.status,{'error':e.message})
        except (ConnectionResetError, BrokenPipeError):
            raise
        except Exception as e:
            print(type(e).__name__,str(e),flush=True);self.reply(500,{'error':'服务处理失败，请检查输入后重试'})

def operations_worker():
    while True:
        try:portal_operations.maintenance(DB,read_state,platform_store.save,LOCK)
        except Exception as error:print('监控与备份任务失败',type(error).__name__,flush=True)
        time.sleep(60)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='0.0.0.0');parser.add_argument('--port',type=int,default=5190);parser.add_argument('--db');args=parser.parse_args()
    if args.db: DB=Path(args.db).resolve()
    init_db()
    threading.Thread(target=deliver_events,daemon=True).start()
    threading.Thread(target=operations_worker,daemon=True).start()
    threading.Thread(target=analysis_jobs.worker,args=(DB,),daemon=True).start()
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    with sqlite3.connect(DB) as c:security=portal_operations.settings(read_state(c))
    if security['tlsEnabled']:
        import ssl
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(security['certPath'],security['keyPath']);server.socket=context.wrap_socket(server.socket,server_side=True)
        print('HTTPS 已启用，请通过 https:// 地址访问',flush=True)
    scheme='https' if security['tlsEnabled'] else 'http'
    print(f'一张图服务门户：{scheme}://127.0.0.1:{args.port}/  后台：{scheme}://127.0.0.1:{args.port}/#/admin/overview',flush=True)
    print(f'监听地址：{args.host}:{args.port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止。',flush=True)
    finally:
        server.server_close()
