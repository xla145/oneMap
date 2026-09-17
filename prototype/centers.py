"""Executable integration, sharing, tool and governance workflows for local data.
External connectors are registered and validated, never reported as live connections.
"""
import csv
import io
import json
import math
import re
import hashlib
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, date
from urllib.parse import urlparse
import capabilities as cap
import portal_management as pm
from capabilities import require, Invalid

ENTITIES=('systems','nodes','syncRuns','externalTodos','sources','ingestions','rules','qualityRuns','issues','directories','standards','datasets','publications','deliveries','subscriptions','inspections','toolReviews','toolTrials')
SYSTEMS=['测绘地理信息时空大数据服务平台','全区不动产登记信息管理平台','地质灾害防治平台','地质调查监测管理系统','国土空间规划“一张图”实施监督信息系统','土地资源信息储备系统','耕地保护与监测监管信息系统','多级一体化电子政务平台','自然资源厅门户网站']
METHODS=['数据下载','数据订阅','定时推送','数据服务','功能接口','离线获取','数据访问']

def now():return datetime.now().isoformat(timespec='seconds')
def ident(prefix):return prefix+'-'+uuid.uuid4().hex[:12]
def text(value,limit=2000):return pm.text(value,limit)
def find(rows,key):return next((r for r in rows if r['id']==key),None)
def record(prefix,name,**kw):return dict(id=ident(prefix),name=name,rev=1,status='草稿',createdAt=now(),updated=now(),history=[],**kw)
def admin(u):require(u['role']=='平台管理员','需要平台管理员身份',403)
def sharing_admin(u):require(u['role'] in ['平台管理员','资源审批人员'],'需要资源管理身份',403)
def changed(r,u,action,note=''):
    r['rev']+=1;r['updated']=now();r.setdefault('history',[]).append(dict(at=now(),actor=u['name'],action=action,note=note))
def revision(r,p):require(r and r['rev']==p.get('rev'),'记录不存在或已更新，请刷新',409)
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def json_value(value,typ):
    if isinstance(value,str):
        try:value=json.loads(value)
        except (ValueError,TypeError):raise Invalid('请输入有效 JSON')
    require(isinstance(value,typ),'JSON 结构不正确');return value

def safe_entry(value):
    value=text(value,1000)
    require(not value or value.startswith('#/front/') or (urlparse(value).scheme=='https' and urlparse(value).hostname and not urlparse(value).username and not urlparse(value).password),'入口应为 HTTPS 地址或本站前台路由')
    require(not any(c.isspace() for c in value),'入口地址不能包含空白');return value

def migrate(s):
    c=s.setdefault('centers',{})
    for e in ENTITIES:c.setdefault(e,[])
    c.setdefault('favorites',{});c.setdefault('sharing',{})
    if not c.get('initialized'):
        for i,name in enumerate(SYSTEMS):
            r=record('sys',name,entry='',authClientId='',appId='',contact='',adapter='外部待接入',todoEnabled=i in [4,6],requiresSso=i<8,mapping={'id':'id','name':'name','userId':'userId','status':'status','dueAt':'dueAt','entry':'entry'},lastCheck=None)
            r.update(id='system-'+str(i+1),status='待配置');c['systems'].append(r)
        c['sources'].append(dict(record('source','本地 CSV 数据源',kind='CSV文件',provider='自然资源示例数据中心',region='全区',endpoint='',description='支持在线填报和 UTF-8 CSV 上传',lastCheck=None),id='source-local',status='可用'))
        c['directories'].extend([dict(record('dir',name,parentId='',kind=kind,tags=''),id=key,status='启用') for key,name,kind in [('dir-data','数据资源','数据库表'),('dir-layer','图层服务','图层服务'),('dir-tool','工具服务','工具服务')]])
        for field,kind,name in [('id','唯一','记录标识唯一'),('name','必填','名称必填'),('area','非负数','面积非负')]:
            c['rules'].append(dict(record('rule',name,field=field,kind=kind,argument='',enabled=True),id='rule-'+field,status='启用'))
        c['standards'].append(dict(record('standard','基础数据标准',fields=[dict(name='id',label='标识',type='text',required=True),dict(name='name',label='名称',type='text',required=True),dict(name='region',label='行政区',type='text',required=True),dict(name='area',label='面积',type='number',required=True)],version=1,versions=[]),id='standard-basic',status='已发布'))
        c['nodes'].append(dict(record('node','一张图·内蒙古',level='自治区',parentId='',region='全区',domain='',direction='双向',contact=''),id='node-province',status='待联调'))
        c['initialized']=True
    for system in c['systems']:
        system.setdefault('requiresSso',system['id'] in ['system-'+str(i) for i in range(1,9)])
        system['mapping'].setdefault('createdAt','createdAt')
    return c

def csv_data(body,allow_empty=False):
    body=text(body,200000);reader=csv.DictReader(io.StringIO(body));fields=reader.fieldnames or []
    require(fields and len(fields)<=100 and len(set(fields))==len(fields) and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',f or '') for f in fields),'CSV 列名需为不重复的英文标识，最多100列')
    rows=list(reader);require(len(rows)<=2000 and (allow_empty or rows),'CSV 需有1～2000行数据')
    require(all(None not in r and None not in r.values() for r in rows),'CSV 列数不一致')
    return fields,rows

def rule_issues(fields,rows,rules,standard=None):
    issues=[]
    def add(row,field,rule,message):issues.append(dict(row=row,field=field,rule=rule,message=message))
    for f in (standard or {}).get('fields',[]):
        if f['name'] not in fields:add(0,f['name'],'标准字段','缺少标准字段');continue
        for i,row in enumerate(rows,1):
            value=row[f['name']]
            if f.get('required') and not value.strip():add(i,f['name'],'标准必填','不能为空')
            if value and f['type']=='date':
                try:date.fromisoformat(value)
                except ValueError:add(i,f['name'],'标准类型','应为 YYYY-MM-DD 日期')
            if value and f['type']=='number':
                try:ok=math.isfinite(float(value))
                except ValueError:ok=False
                if not ok:add(i,f['name'],'标准类型','应为有限数值')
    for rule in rules:
        f=rule['field'];kind=rule['kind'];seen=set()
        if f not in fields:add(0,f,rule['name'],'规则字段不存在');continue
        for i,row in enumerate(rows,1):
            val=row[f].strip();error=False
            if kind=='必填':error=not val
            elif kind=='唯一':error=val in seen;seen.add(val)
            elif kind=='非负数':
                try:error=not math.isfinite(float(val)) or float(val)<0
                except ValueError:error=True
            elif kind=='枚举':error=val not in rule['argument'].split(',')
            elif kind=='日期':
                try:date.fromisoformat(val)
                except ValueError:error=True
            if error:add(i,f,rule['name'],f'{kind}校验失败')
    return issues

def quality(s,u,r):
    c=migrate(s);fields,rows=csv_data(r['dataRows'])
    rules=[find(c['rules'],key) for key in r['ruleIds']]
    require(all(x and x['enabled'] for x in rules),'质检规则已停用或不存在')
    standard=find(c['standards'],r.get('standardId'));require(not r.get('standardId') or (standard and standard['status']=='已发布'),'数据标准未发布')
    issues=rule_issues(fields,rows,rules,standard)
    run=record('qc',r['name']+' · 质检',ingestionId=r['id'],inputHash=digest(r['dataRows']),dataRevision=r['dataRevision'],total=len(rows),issues=issues,ruleSnapshots=deepcopy(rules),standardSnapshot=deepcopy(standard),passed=not issues)
    run['status']='通过' if not issues else '不通过';c['qualityRuns'].append(run)
    r['qualityRunId']=run['id'];r['status']='待登记' if not issues else '待整改';changed(r,u,'执行质检',f'{len(rows)}行，{len(issues)}项问题')
    return run

def catalog(s,u):
    rows=[]
    for r in cap.active(s,'resources'):
        if cap.visible(u,r):rows.append(dict(id='resource:'+r['id'],name=r['name'],kind=r['type'],category=r.get('category',''),source=r.get('source',''),region=r.get('region','全区'),target='/front/data/'+r['id'],resourceId=r['id'],updated=r.get('updated',''),authorized=cap.authorized(s,u,r)))
    for r in s['knowledge']:
        v=cap.knowledge_channel(r,'portal')
        if v and cap.visible(u,v):rows.append(dict(id='knowledge:'+r['id'],name=v['name'],kind='知识',category=v.get('category',''),source=v.get('source',''),target='/front/knowledge',objectId=r['id'],updated=v.get('updated','')))
    for r in cap.active(s,'agents'):
        if cap.visible(u,r):rows.append(dict(id='agent:'+r['id'],name=r['name'],kind='智能体',category=r.get('category',''),target='/front/agents',updated=r.get('updated','')))
    for r in s['platform']['apps']:
        v=r.get('published')
        if v and r.get('listed') and cap.visible(u,v):rows.append(dict(id='app:'+r['id'],name=v['name'],kind='应用场景',category=v.get('category',''),target='/front/app-center/'+r['id'],updated=v.get('updated','')))
    for r in pm.migrate(s)['tools']:
        v=cap.published(r)
        if v and pm.can_tool(u,v,s):rows.append(dict(id='tool:'+r['id'],name=v['name'],kind='工具',category=v.get('category',''),target='/front/capabilities/'+r['id'],updated=v.get('updated','')))
    return rows

def bootstrap(s,u,mode):
    c=migrate(s);full=mode=='admin' and u['role']=='平台管理员';review=mode=='admin' and u['role'] in ['平台管理员','资源审批人员']
    out={e:deepcopy(c[e]) if full else [] for e in ENTITIES}
    for e in ['deliveries','subscriptions']:out[e]=[deepcopy(r) for r in c[e] if review or r['userId']==u['id']]
    # CSV payloads, generated packages and check snapshots are fetched through explicit actions.
    for d in out['deliveries']:d.pop('content',None)
    out['catalog']=catalog(s,u);out['directories']=deepcopy(c['directories']);out['sharing']=deepcopy(c['sharing']) if full else {k:deepcopy(v) for k,v in c['sharing'].items() if any(r.get('resourceId')==k for r in out['catalog'])}
    if not full:
        out['issues']=[deepcopy(r) for r in c['issues'] if r['assigneeId']==u['id']]
        assigned={r['ingestionId'] for r in out['issues']}
        out['ingestions']=[deepcopy(r) for r in c['ingestions'] if r['id'] in assigned]
    out['favorites']=c['favorites'].get(u['id'],[])
    import platform_features
    todos=[dict(id='case:'+r['id'],name=r['name'],source='本地业务流程',status=r['status'],createdAt=r.get('createdAt',''),dueAt=r.get('dueAt',''),entry='#/front/cases/'+r['id'],userId=r.get('assigneeId')) for r in s['platform']['cases'] if r.get('assigneeId')==u['id'] or platform_features.todo(s['platform'],u,r)]
    todos += [dict(r,createdAt=r.get('sourceCreatedAt',''),receivedAt=r.get('receivedAt',r.get('updated','')),source=(find(c['systems'],r['systemId']) or {}).get('name','外部系统')) for r in c['externalTodos'] if full or r['userId']==u['id']]
    import operations_center
    todos += operations_center.todos(s,u)
    for r in todos:
        r['timeliness']='已办' if r['status'] in ['已办','已办结'] else '逾期' if r.get('dueAt') and r['dueAt']<now() else '预警' if r.get('dueAt') and r['dueAt']<(datetime.now()+timedelta(days=1)).isoformat() else '正常'
    out['todos']=todos;out['todoCounts']=todo_counts(todos);out['canManage']=full;out['canDeliver']=review
    out['counts']={kind:sum(r['kind']==kind for r in out['catalog']) for kind in ['数据库表','图层服务','工具服务','知识','智能体','应用场景','工具']}
    return out

def method_for(r,method=''):
    defaults={'数据库表':'数据下载','图层服务':'数据服务','工具服务':'功能接口','知识文档':'数据下载'}
    method=method or defaults[r['type']]
    allowed={'数据库表':['数据下载','数据订阅','定时推送','离线获取','数据访问'],'图层服务':['数据下载','数据服务','离线获取'],'工具服务':['功能接口'],'知识文档':['数据下载','离线获取']}
    require(method in allowed[r['type']],'所选获取方式不适用于资源：'+r['name']);return method

def on_grant(s,u,g,application,item):
    c=migrate(s);method=item.get('method') or method_for(cap.find(s['resources'],g['resourceId']))
    if any(d.get('grantId')==g['id'] for d in c['deliveries']):return
    d=record('delivery',item['name']+' · '+method,userId=g['userId'],resourceId=g['resourceId'],grantId=g['id'],method=method,region='全区',fields=[],sourceApplicationId=application['id'],attempts=0,receipt='',error='',pickupPlace='',pickupAt='')
    d['status']='待准备';c['deliveries'].append(d)

def holder_resource(s,d):
    u=cap.find(s['users'],d['userId']);r=cap.published(cap.find(s['resources'],d['resourceId']))
    require(u and u['enabled'] and r and cap.authorized(s,u,r),'接收人授权已失效、资源限制使用或已下架',403)
    if d.get('grantId'):
        g=cap.find(s['grants'],d['grantId']);require(g and cap.grant_valid(g,u,r),'交付关联的授权已撤销或到期',403)
    return u,r

def delivery_rows(s,d):
    u,r=holder_resource(s,d)
    require(r['type']=='数据库表','当前生成器支持本地库表 CSV；图层请使用数据服务中的 GeoJSON 下载')
    rows=cap.data_rows(r) or r.get('sample',[])
    if u['region']!='全区':rows=[row for row in rows if row.get('region',row.get('行政区'))==u['region']]
    if d.get('region','全区')!='全区':rows=[row for row in rows if row.get('region',row.get('行政区'))==d['region']]
    hidden={k for f in r.get('fields',[]) if not f.get('display',True) for k in [f.get('name'),f.get('label')] if k}
    columns=list(dict.fromkeys(k for row in rows for k in row if k not in hidden))
    if d.get('fields'):
        require(set(d['fields'])<=set(columns),'交付字段不存在或不可显示');columns=d['fields']
    require(rows and columns,'当前筛选范围没有可交付记录')
    return r,rows,columns

def package(s,d):
    r,rows,columns=delivery_rows(s,d)
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=columns);writer.writeheader()
    for row in rows:
        writer.writerow({k:("'"+str(row.get(k,'')) if str(row.get(k,'')).lstrip().startswith(('=','+','-','@')) else row.get(k,'')) for k in columns})
    return dict(content='\ufeff'+out.getvalue(),filename=r['name']+'.csv',mime='text/csv',rowCount=len(rows),resourceVersion=r['version'])

def execute(s,u,action,p,hooks):
    c=migrate(s);op=action.removeprefix('centers.') if hasattr(str,'removeprefix') else action[len('centers.'):]
    require(isinstance(p,dict),'参数格式无效')
    if op=='service.query':return service_query(s,u,p)
    if op=='favorite':
        key=text(p.get('id',''));require(any(r['id']==key for r in catalog(s,u)),'对象已下架或不可见',404)
        values=c['favorites'].setdefault(u['id'],[])
        if key in values:values.remove(key)
        else:values.append(key)
        return {'ok':True}
    if op in ['delivery.download','delivery.receive','delivery.endpoint']:
        d=find(c['deliveries'],p.get('id'));require(d and (d['userId']==u['id'] or u['role']=='平台管理员'),'交付记录不可访问',403)
        _,resource=holder_resource(s,d)
        if op=='delivery.endpoint':
            require(d['status'] in ['可领取','已领取'] and d['method'] in ['数据服务','功能接口'],'服务交付尚未准备')
            require(resource.get('serviceUrl'),'服务入口未配置');return {'url':pm.https(resource['serviceUrl'])}
        if op=='delivery.download':
            require(d['status'] in ['可领取','已领取'] and d.get('content'),'数据包尚未生成')
            # Re-check scope against the current published resource; never leak a stale package after field restrictions change.
            current=package(s,d);require(current['resourceVersion']==d['resourceVersion'],'资源已更新，请重新生成数据包')
            require(current['content']==d['content'],'资源或字段范围已变化，请重新生成')
            changed(d,u,'领取数据包');d['status']='已领取';return {k:d[k] for k in ['filename','content','mime']}
        revision(d,p);require(d['status']=='可领取','当前交付不能确认领取');d['status']='已领取';d['receipt']=text(p.get('note','已领取'));changed(d,u,'确认领取',d['receipt']);return deepcopy(d)
    if op=='delivery.request':
        r=cap.published(cap.find(s['resources'],p.get('resourceId')));require(r and cap.authorized(s,u,r),'请先取得资源使用授权',403)
        method=method_for(r,text(p.get('method','')))
        require(method in ['数据下载','数据访问','离线获取'],'订阅和服务交付请使用对应申请方式')
        d=record('delivery',r['name']+' · '+method,userId=u['id'],resourceId=r['id'],grantId='',method=method,region=text(p.get('region','全区')),fields=cap.ids(p.get('fields','')),sourceApplicationId='',attempts=0,receipt='',error='',pickupPlace='',pickupAt='')
        d['status']='待准备';c['deliveries'].append(d);return deepcopy(d)
    if op in ['subscription.pause','subscription.resume']:
        r=find(c['subscriptions'],p.get('id'));require(r and (r['userId']==u['id'] or u['role']=='平台管理员'),'订阅不可访问',403);revision(r,p)
        if op.endswith('resume'):holder_resource(s,r)
        r['status']='已暂停' if op.endswith('pause') else '运行中';r['nextRunAt']=now();changed(r,u,op);return deepcopy(r)
    if op=='issue.feedback':
        issue=find(c['issues'],p.get('id'));require(issue and (issue['assigneeId']==u['id'] or u['role']=='平台管理员'),'只能反馈本人受派工单',403)
    elif op.startswith('delivery.') or op.startswith('subscription.'):
        sharing_admin(u)
    else:admin(u)
    if op=='save':return save(s,u,p)
    if op=='delete':
        entity=p.get('entity');require(entity in ['sources','rules','directories','standards','systems','nodes'],'该类记录保留历史，不能删除')
        r=find(c[entity],p.get('id'));revision(r,p)
        references=[json.dumps(x,ensure_ascii=False) for e in ENTITIES for x in c[e] if x is not r]
        references.append(json.dumps(c['sharing'],ensure_ascii=False))
        require(not any(r['id'] in value for value in references),'记录已被引用，请停用或解除关联后删除')
        c[entity].remove(r);pm.event(s,u,'operation','删除中心配置',r['id'],r['name']);return {'ok':True}
    if op=='system.check':
        r=find(c['systems'],p.get('id'));revision(r,p)
        missing=[]
        if not r['entry']:missing.append('访问入口')
        if r.get('requiresSso') and not r.get('authClientId'):missing.append('单点登录客户端')
        if r.get('authClientId') and not find(s['platform']['authClients'],r['authClientId']):missing.append('有效认证客户端')
        r['lastCheck']=dict(at=now(),missing=missing,scope='仅检查配置，不发起外部连接')
        r['status']='待配置' if missing else '本地配置可用' if r['adapter']=='本地演示' else '配置通过·待联调';changed(r,u,'配置校验');return deepcopy(r)
    if op=='todos.import':
        system=find(c['systems'],p.get('systemId'));require(system and system['todoEnabled'],'该系统未启用待办集成')
        rows=json_value(p.get('payload'),list);require(0<len(rows)<=200,'每批导入1～200条待办')
        prepared=[];mapping=system['mapping'];keys=set()
        for raw in rows:
            require(isinstance(raw,dict),'待办应为对象');r={k:raw.get(v,'') for k,v in mapping.items()}
            require(all(isinstance(v,str) for v in r.values()),'待办字段需为文本');require(r.get('id') and r.get('name'),'待办缺少标识或名称')
            require(r['id'] not in keys,'同批待办标识重复');keys.add(r['id'])
            require(not any(t['systemId']==system['id'] and t['externalId']==r['id'] and t.get('sourceVersion') for t in c['externalTodos']),'该任务已启用版本同步，请在综合集成待办同步中导入')
            require((account:=cap.find(s['users'],r.get('userId'))) and account['enabled'],'待办处理人不存在或已停用')
            require(r.get('status') in ['待办','已办'],'待办状态应为待办或已办')
            for timestamp in ['createdAt','dueAt']:
                if r.get(timestamp):
                    try:stamp=datetime.fromisoformat(r[timestamp]);require(stamp.tzinfo is None,'日期请使用本地时间，不带时区');r[timestamp]=stamp.isoformat(timespec='seconds')
                    except ValueError:raise Invalid('待办日期格式无效')
            if r.get('dueAt'):
                try:stamp=datetime.fromisoformat(r['dueAt']);require(stamp.tzinfo is None,'日期请使用本地时间，不带时区');r['dueAt']=stamp.isoformat(timespec='seconds')
                except ValueError:raise Invalid('待办截止时间无效')
            r['entry']=safe_entry(r.get('entry',''));prepared.append(r)
        added=updated=0
        for r in prepared:
            old=next((x for x in c['externalTodos'] if x['systemId']==system['id'] and x['externalId']==r['id']),None)
            if not old:old=record('todo',r['name'],systemId=system['id'],externalId=r['id']);c['externalTodos'].append(old);added+=1
            else:updated+=1
            old.update({k:v for k,v in r.items() if k not in ['id','createdAt']});old['sourceCreatedAt']=r.get('createdAt','');old['receivedAt']=now();changed(old,u,'同步待办')
        run=record('sync',system['name']+' · 待办导入',systemId=system['id'],added=added,updatedCount=updated,scope='本地导入，不代表外部接口联通');run['status']='已完成';c['syncRuns'].append(run);return deepcopy(run)
    if op=='node.export':
        r=find(c['nodes'],p.get('id'));require(r,'节点不存在',404);require(r['direction'] in ['导出','双向'],'当前节点未启用导出')
        payload=[dict(id=x['id'],name=x['name'],kind=x['kind'],category=x.get('category','')) for x in catalog(s,u)]
        run=record('sync',r['name']+' · 目录导出',nodeId=r['id'],count=len(payload),scope='生成本地交换清单，未向外部节点发送');run['status']='已生成';c['syncRuns'].append(run)
        return dict(filename='目录交换-'+r['id']+'.json',content=json.dumps(dict(node=r['name'],at=now(),resources=payload),ensure_ascii=False,indent=2),mime='application/json')
    if op=='source.check':
        r=find(c['sources'],p.get('id'));revision(r,p);r['status']='可用' if r['kind']=='CSV文件' else '待外部联调';r['lastCheck']=now();changed(r,u,'检查数源配置');return deepcopy(r)
    if op in ['ingestion.submit','ingestion.check','ingestion.return','ingestion.register']:
        r=find(c['ingestions'],p.get('id'));revision(r,p)
        if op=='ingestion.submit':
            require(r['status'] in ['草稿','已退回'],'当前状态不能提交');csv_data(r['dataRows']);r['status']='待质检';changed(r,u,'提交归集')
        elif op=='ingestion.check':
            require(r['status'] in ['待质检','待整改','待登记'],'当前状态不能质检');return quality(s,u,r)
        elif op=='ingestion.return':
            require(r['status'] in ['待质检','待整改','待登记'],'当前状态不能退回');note=text(p.get('note',''));require(note,'请填写退回原因');r['status']='已退回';changed(r,u,'退回归集',note)
        else:
            require(r['status']=='待登记','需质检通过后才能登记入库')
            run=find(c['qualityRuns'],r.get('qualityRunId'));require(run and run['passed'] and run['inputHash']==digest(r['dataRows']),'数据已变化，请重新质检')
            require(all((current:=find(c['rules'],x['id'])) and current['rev']==x['rev'] for x in run['ruleSnapshots']),'规则已变化，请重新质检')
            if run.get('standardSnapshot'):
                current=find(c['standards'],r['standardId']);require(current and current['status']=='已发布' and current['version']==run['standardSnapshot']['version'],'标准已变化，请重新质检')
            require(not any(x['ingestionId']==r['id'] for x in c['issues'] if x['status']!='已办结'),'请先复检并办结治理工单')
            fields,rows=csv_data(r['dataRows']);source=find(c['sources'],r['sourceId'])
            values=dict(name=r['name'],type='数据库表',category=r['category'],region=r['region'],source=source['provider'],frequency='每月',sharingPolicy='申请使用',access='可申请',visibility='业务用户',crs=r.get('crs','CGCS2000'),fields=[dict(name=f,label=f,type='varchar',description=f+' 字段',display=True,query=True) for f in fields],relations=[],aliases=r['name'],description='来自归集批次 '+r['id'],dataRows=r['dataRows'],dataSource=source['name'],sourceType='文件',subtype='属性表')
            resource=hooks['save'](s,u,dict(entity='resources',values=values))
            ds=record('dataset',r['name'],ingestionId=r['id'],resourceId=resource['id'],standardId=r.get('standardId',''),standardVersion=(run.get('standardSnapshot') or {}).get('version'),rowCount=len(rows),fields=fields,layer=r['layer'],region=r['region']);ds['status']='已入库';c['datasets'].append(ds)
            r.update(status='已入库',resourceId=resource['id']);changed(r,u,'登记入库',resource['id'])
        return deepcopy(r)
    if op=='quality.issue':
        run=find(c['qualityRuns'],p.get('id'));require(run and run['issues'],'该报告没有待治理问题');r=find(c['ingestions'],run['ingestionId'])
        require(run['id']==r.get('qualityRunId'),'请基于最新报告发起治理')
        require(not any(x['runId']==run['id'] and x['status']!='已办结' for x in c['issues']),'该报告已有未办结工单')
        assignee=cap.find(s['users'],p.get('assigneeId'));require(assignee and assignee['enabled'],'请选择处理人')
        issue=record('issue',r['name']+' · 数据整改',ingestionId=r['id'],runId=run['id'],assigneeId=assignee['id'],assigneeName=assignee['name'],note='',evidence='',feedback='');issue['status']='待处理';c['issues'].append(issue);return deepcopy(issue)
    if op in ['issue.feedback','issue.review']:
        issue=find(c['issues'],p.get('id'));revision(issue,p);r=find(c['ingestions'],issue['ingestionId'])
        if op=='issue.feedback':
            require(issue['status'] in ['待处理','已退回'],'当前工单不可反馈');note=text(p.get('note',''));require(note,'请填写整改说明')
            body=text(p.get('dataRows',''),200000);csv_data(body);r['dataRows']=body;r['dataRevision']+=1;r['status']='待质检';changed(r,u,'整改数据',note)
            issue.update(status='待复核',feedback=note,evidence=text(p.get('evidence','')));changed(issue,u,'提交整改反馈',note)
        else:
            require(issue['status']=='待复核','当前工单不可复核');run=quality(s,u,r)
            issue['status']='已办结' if run['passed'] else '已退回';issue['reviewRunId']=run['id'];changed(issue,u,'复检复核',run['status'])
        return deepcopy(issue)
    if op=='standard.publish':
        r=find(c['standards'],p.get('id'));revision(r,p);r['status']='已发布';r['version']+=1;r['versions'].append(dict(at=now(),version=r['version'],fields=deepcopy(r['fields'])));changed(r,u,'发布标准');return deepcopy(r)
    if op=='dataset.create':
        standard=find(c['standards'],p.get('standardId'));require(standard and standard['status']=='已发布','请选择已发布标准')
        name=text(p.get('name',''),100);require(name,'名称必填')
        fields=[dict(name=f['name'],label=f['label'],type='decimal' if f['type']=='number' else 'varchar',description=f['label'],display=True,query=True) for f in standard['fields']]
        row=hooks['save'](s,u,dict(entity='resources',values=dict(name=name,type='数据库表',category=text(p.get('category','标准建库')),region='全区',source=u['department'],frequency='每月',sharingPolicy='申请使用',access='可申请',visibility='业务用户',fields=fields,relations=[],dataRows=','.join(f['name'] for f in standard['fields'])+'\n',crs='CGCS2000',aliases=name)))
        ds=record('dataset',name,ingestionId='',resourceId=row['id'],standardId=standard['id'],standardVersion=standard['version'],rowCount=0,fields=[f['name'] for f in fields],layer=text(p.get('layer','基础层')),region='全区');ds['status']='已建表';c['datasets'].append(ds);return deepcopy(ds)
    if op=='publication.publish':
        r=find(c['publications'],p.get('id'));revision(r,p);resource=cap.find(s['resources'],r['resourceId']);require(resource,'资源已删除')
        require(r['protocol']=='本地数据接口','外部 GIS 服务只登记，不在本地伪造发布')
        require(resource['type']=='数据库表','本地数据接口仅支持库表')
        csv_data(resource.get('dataRows',''),allow_empty=True)
        hooks['publish'](s,u,dict(entity='resources',id=resource['id'],rev=resource['rev']))
        r.update(status='已发布',resourceVersion=resource['version'],endpoint='/api/action · centers.service.query');changed(r,u,'发布技术服务');return deepcopy(r)
    if op=='publication.disable':
        r=find(c['publications'],p.get('id'));revision(r,p);r['status']='已停用';changed(r,u,'停用技术服务');return deepcopy(r)
    if op=='sharing.save':
        r=cap.find(s['resources'],p.get('resourceId'));require(r,'资源不存在')
        old=c['sharing'].get(r['id']);require(not old or old['rev']==p.get('rev'),'编目记录已更新',409)
        directory=find(c['directories'],p.get('directoryId'));require(directory and directory['kind'] in ['公共目录',r['type']],'请选择匹配资源类型的目录')
        value=dict(resourceId=r['id'],directoryId=directory['id'],tags=text(p.get('tags','')),rev=(old or {}).get('rev',0)+1,updated=now())
        c['sharing'][r['id']]=value;pm.event(s,u,'operation','资源编目',r['id'],r['name']);return deepcopy(value)
    if op=='delivery.create':
        target=cap.find(s['users'],p.get('userId'));resource=cap.published(cap.find(s['resources'],p.get('resourceId')))
        require(target and resource and cap.authorized(s,target,resource),'接收人没有有效资源授权')
        d=record('delivery',resource['name']+' · 分发',userId=target['id'],resourceId=resource['id'],grantId='',method=method_for(resource,text(p.get('method','数据下载'))),region=text(p.get('region','全区')),fields=cap.ids(p.get('fields','')),sourceApplicationId='',attempts=0,receipt='',error='',pickupPlace=text(p.get('pickupPlace','')),pickupAt=text(p.get('pickupAt','')))
        d['status']='待准备';c['deliveries'].append(d);return deepcopy(d)
    if op in ['delivery.run','delivery.pickup']:
        d=find(c['deliveries'],p.get('id'));revision(d,p);d['attempts']+=1
        try:
            holder,resource=holder_resource(s,d)
            if d['method']=='离线获取':
                place=text(p.get('pickupPlace',d.get('pickupPlace','')));stamp=text(p.get('pickupAt',d.get('pickupAt','')))
                require(place and stamp,'请填写领取地点及时间');datetime.fromisoformat(stamp)
                d.update(pickupPlace=place,pickupAt=stamp,status='可领取',receipt='领取通知已准备')
            elif d['method'] in ['数据服务','功能接口']:
                require(resource.get('serviceUrl'),'资源未绑定实际服务地址');d.update(status='可领取',receipt='已准备资源服务入口；使用时再次校验授权',resourceVersion=resource['version'])
            elif d['method'] in ['数据订阅','定时推送']:
                require(False,'请先注册订阅，生成批次后在交付记录中领取')
            else:d.update(package(s,d));d['status']='可领取'
            d['error']=''
        except (Invalid,ValueError) as error:d['status']='失败';d['error']=getattr(error,'message',str(error))
        changed(d,u,'执行交付',d['error'] or d['status']);return {k:deepcopy(v) for k,v in d.items() if k!='content'}
    if op=='subscription.create':
        d=find(c['deliveries'],p.get('deliveryId'));require(d and d['method'] in ['数据订阅','定时推送'],'请选择订阅类交付记录');holder_resource(s,d)
        require(not any(x['deliveryId']==d['id'] for x in c['subscriptions']),'该交付已有订阅')
        interval=p.get('intervalSeconds',3600);require(type(interval) is int and 60<=interval<=86400,'周期需为60～86400秒')
        r=record('subscription',d['name'],userId=d['userId'],resourceId=d['resourceId'],grantId=d.get('grantId',''),deliveryId=d['id'],region=d['region'],fields=d['fields'],intervalSeconds=interval,nextRunAt=now(),lastRunAt='',error='',receiver='本地交付箱')
        r['status']='运行中';c['subscriptions'].append(r);d['status']='订阅运行中';changed(d,u,'注册本地订阅');return deepcopy(r)
    if op=='subscription.run':
        r=find(c['subscriptions'],p.get('id'));revision(r,p);require(r['status']=='运行中','订阅已暂停');return run_subscription(s,u,r)
    if op=='inspection.run':
        failures=[]
        for d in c['deliveries']:
            if d['status']=='失败':failures.append(dict(kind='交付失败',targetId=d['id'],name=d['name'],reason=d['error']))
        for r in c['ingestions']:
            if r['status']=='待整改':failures.append(dict(kind='质检异常',targetId=r['id'],name=r['name'],reason='归集数据存在未治理问题'))
        for r in c['publications']:
            if r['status']=='已发布' and not cap.published(cap.find(s['resources'],r['resourceId'])):failures.append(dict(kind='服务依赖异常',targetId=r['id'],name=r['name'],reason='底层资源已停用'))
        row=record('inspection','业务链路巡检',failures=failures,scope='检查本地任务与依赖状态，外部端点未做网络探测');row['status']='有异常' if failures else '正常';c['inspections'].append(row);return deepcopy(row)
    if op.startswith('tool.'):return tool_action(s,u,op,p)
    raise Invalid('未知中心操作',404)

def save(s,u,p):
    c=migrate(s);entity=p.get('entity');require(entity in ['systems','nodes','sources','ingestions','rules','directories','standards','publications'],'未知配置类型')
    v=p.get('values');require(isinstance(v,dict),'配置格式错误');old=find(c[entity],p.get('id'))
    if p.get('id'):revision(old,p)
    name=text(v.get('name',''),100);require(name,'名称必填')
    r=deepcopy(old) if old else record(entity[:-1],name);r['name']=name
    if entity=='systems':
        r.update(entry=safe_entry(v.get('entry','')),contact=text(v.get('contact','')),authClientId=text(v.get('authClientId','')),appId=text(v.get('appId','')),adapter=text(v.get('adapter','外部待接入')),todoEnabled=v.get('todoEnabled') is True,requiresSso=v.get('requiresSso',r.get('requiresSso',False)) is True,mapping=json_value(v.get('mapping',{}),dict),lastCheck=None,status='待配置')
        require(r['adapter'] in ['外部待接入','本地演示'],'适配方式无效')
        require(not r['authClientId'] or find(s['platform']['authClients'],r['authClientId']),'认证客户端不存在')
        require(not r['appId'] or find(s['platform']['apps'],r['appId']),'应用登记不存在')
        require({'id','name','userId','status','dueAt','entry'}<=set(r['mapping'])<= {'id','name','userId','status','dueAt','entry','createdAt'} and all(isinstance(x,str) and x and len(x)<=100 for x in r['mapping'].values()),'需配置全部六项待办字段映射')
    elif entity=='nodes':
        r.update(level=text(v.get('level','')),parentId=text(v.get('parentId','')),region=text(v.get('region','')),domain=safe_entry(v.get('domain','')),direction=text(v.get('direction','双向')),contact=text(v.get('contact','')),status='待联调')
        levels={'国家':0,'自治区':1,'盟市':2,'旗县':3};require(r['level'] in levels,'节点级别无效');require(r['direction'] in ['导入','导出','双向'],'同步方向无效')
        if r['parentId']:
            parent=find(c['nodes'],r['parentId']);require(parent and levels[parent['level']]<levels[r['level']],'父节点应为上级，不能循环或同级挂接')
        for child in c['nodes']:
            if child.get('parentId')==r['id']:require(levels[r['level']]<levels[child['level']],'修改级别会使下级节点关系失效')
    elif entity=='sources':
        r.update(kind=text(v.get('kind','CSV文件')),provider=text(v.get('provider','')),region=text(v.get('region','全区')),endpoint=safe_entry(v.get('endpoint','')),description=text(v.get('description','')),lastCheck=None)
        require(r['kind'] in ['CSV文件','Oracle','PostgreSQL','空间数据库','ArcGISService','GeoServer','Geoscene'],'数源类型无效');require(r['provider'],'提供单位必填')
        r['status']='可用' if r['kind']=='CSV文件' else '待外部联调'
    elif entity=='ingestions':
        require(not old or old['status'] in ['草稿','已退回'],'已提交批次请通过退回或治理工单修改')
        r.update(sourceId=text(v.get('sourceId','')),region=text(v.get('region','全区')),category=text(v.get('category','基础数据')),layer=text(v.get('layer','原始层')),standardId=text(v.get('standardId','')),ruleIds=v.get('ruleIds',[]),dataRows=text(v.get('dataRows',''),200000),crs=text(v.get('crs','CGCS2000')),mode=text(v.get('mode','在线填报')),status='草稿',dataRevision=(old or {}).get('dataRevision',0)+1)
        require(find(c['sources'],r['sourceId']),'请选择数源');require(r['mode'] in ['在线填报','离线CSV'],'本地支持在线填报或离线CSV，不模拟实时抽取')
        require(isinstance(r['ruleIds'],list) and all(find(c['rules'],x) for x in r['ruleIds']),'规则不存在')
        require(not r['standardId'] or find(c['standards'],r['standardId']),'标准不存在');require(r['standardId'] or r['ruleIds'],'至少选择一项质检规则或数据标准');csv_data(r['dataRows'])
    elif entity=='rules':
        r.update(field=text(v.get('field','')),kind=text(v.get('kind','')),argument=text(v.get('argument','')),enabled=v.get('enabled') is True)
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',r['field']),'字段标识无效');require(r['kind'] in ['必填','唯一','非负数','枚举','日期'],'规则类型无效')
        require(r['kind']!='枚举' or r['argument'],'枚举规则需填写逗号分隔值');r['status']='启用' if r['enabled'] else '停用'
    elif entity=='directories':
        r.update(parentId=text(v.get('parentId','')),kind=text(v.get('kind','公共目录')),tags=text(v.get('tags','')),status='启用')
        require(r['kind'] in ['公共目录','数据库表','图层服务','工具服务','知识文档'],'目录类型无效')
        parent=r['parentId'];visited={r['id']}
        while parent:
            require(parent not in visited,'目录存在循环');visited.add(parent);node=find(c['directories'],parent);require(node,'上级目录不存在');parent=node['parentId']
    elif entity=='standards':
        fields=json_value(v.get('fields',[]),list);require(0<len(fields)<=100,'标准包含1～100项字段');names=set()
        for f in fields:
            require(isinstance(f,dict) and isinstance(f.get('name'),str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',f['name']) and f['name'] not in names,'标准字段重复或无效');names.add(f['name'])
            require(f.get('type') in ['text','number','date'] and isinstance(f.get('required',False),bool),'字段类型或必填标识无效');require(isinstance(f.get('label'),str) and f['label'],'字段中文名必填')
        r.update(fields=deepcopy(fields),status='草稿',version=(old or {}).get('version',0),versions=(old or {}).get('versions',[]))
    elif entity=='publications':
        r.update(resourceId=text(v.get('resourceId','')),protocol=text(v.get('protocol','本地数据接口')),endpoint=safe_entry(v.get('endpoint','')),description=text(v.get('description','')),status='草稿')
        require(cap.find(s['resources'],r['resourceId']),'资源不存在');require(r['protocol'] in ['本地数据接口','WMS','MapService','WMTS','WFS','REST'],'协议无效')
        if r['protocol']!='本地数据接口':require(r['endpoint'],'外部服务需填写登记地址');r['status']='已登记·待联调'
    changed(r,u,'保存配置')
    if old:c[entity][c[entity].index(old)]=r
    else:c[entity].append(r)
    pm.event(s,u,'operation','保存中心配置',r['id'],r['name']);return deepcopy(r)

def run_subscription(s,u,r):
    c=migrate(s);r['lastRunAt']=now();r['nextRunAt']=(datetime.now()+timedelta(seconds=r['intervalSeconds'])).isoformat(timespec='seconds')
    try:
        result=package(s,r)
        d=record('delivery',r['name']+' · 批次',userId=r['userId'],resourceId=r['resourceId'],grantId=r.get('grantId',''),method='数据下载',region=r['region'],fields=r['fields'],subscriptionId=r['id'],attempts=1,receipt='',error='',sourceApplicationId='',**result)
        d['status']='可领取';c['deliveries'].append(d);r['error']='';r['lastDeliveryId']=d['id']
    except Invalid as e:r['status']='已暂停';r['error']=e.message
    changed(r,u,'执行本地订阅',r['error'] or '生成本地交付包');return deepcopy(r)

def tick(s):
    c=s.get('centers');u=next((u for u in s['users'] if u['role']=='平台管理员' and u['enabled']),None)
    if not c or not u:return
    for r in [x for x in c.get('subscriptions',[]) if x['status']=='运行中' and x['nextRunAt']<=now()][:5]:run_subscription(s,u,r)

def service_query(s,u,p):
    c=migrate(s);service=find(c['publications'],p.get('id'));require(service and service['status']=='已发布','技术服务未发布或已停用',404)
    r=cap.published(cap.find(s['resources'],service['resourceId']));require(r and cap.authorized(s,u,r),'资源未授权或已下架',403)
    require(r['version']==service['resourceVersion'],'资源版本已变化，请重新发布服务')
    request=dict(userId=u['id'],resourceId=r['id'],region=text(p.get('region','全区')),fields=cap.ids(p.get('fields','')))
    _,raw,columns=delivery_rows(s,request);rows=[{k:row.get(k,'') for k in columns} for row in raw]
    page=p.get('page',1);require(type(page) is int and page>0,'页码无效')
    q=text(p.get('q',''),100)
    if q:rows=[x for x in rows if q in ' '.join(str(v) for v in x.values())]
    pm.event(s,u,'api','本地数据接口调用',service['id'],service['name'],status='成功')
    return dict(total=len(rows),page=page,size=50,rows=rows[(page-1)*50:page*50],resourceVersion=r['version'])

def tool_signature(r):
    return digest(json.dumps({k:v for k,v in r.items() if k in ['name','category','description','engine','url','audience','resourceId','provider','publisher','apiDescription','inputExample','outputDescription','requestParameters','outputExample','directoryId','region','interfaceType','module','usageMode','screenshot']},ensure_ascii=False,sort_keys=True))

def tool_action(s,u,op,p):
    c=migrate(s);tools=pm.migrate(s)['tools']
    if op=='tool.templates':
        created=[]
        for engine,name in [('spatial-check','空间数据检查'),('spatial-query','空间数据查询'),('spatial-store','空间数据入库'),('spatial-edit','空间数据编辑')]:
            if any(x['engine']==engine for x in tools):continue
            row=record('tool',name,engine=engine,category='内部空间组件',provider=u['department'],description='本地工具工作图层能力，独立于生产GIS',audience='管理员',url='',order=len(tools)+1,icon='tool',version=0,versions=[],reviewState='未提交',approvedHash='',resourceId='')
            tools.append(row);created.append(row['name'])
        pm.event(s,u,'operation','登记内部工具模板',name='、'.join(created))
        return dict(name='内部组件登记结果',created=created,status='草稿，需审核后发布')
    r=find(tools,p.get('id'));require(r,'工具不存在',404)
    if op in ['tool.submit','tool.review']:revision(r,p)
    if op=='tool.submit':
        require(r.get('reviewState')!='待审核','工具已在审核中')
        if r.get('resourceId'):require(cap.published(cap.find(s['resources'],r['resourceId'])),'关联工具资源尚未发布')
        r.update(reviewState='待审核',submittedHash=tool_signature(r));r['rev']+=1
        review=record('tool-review',r['name'],toolId=r['id'],toolHash=r['submittedHash'],note='',reviewer='');review['status']='待审核';c['toolReviews'].append(review);return deepcopy(review)
    if op=='tool.review':
        require(r.get('reviewState')=='待审核','工具未提交审核');require(r['submittedHash']==tool_signature(r),'工具内容已变化，请重新提交')
        note=text(p.get('note',''));require(len(note)>=5,'审核意见至少5字');decision=p.get('decision');require(decision in ['通过','驳回'],'审核结果无效')
        review=next((x for x in reversed(c['toolReviews']) if x['toolId']==r['id'] and x['status']=='待审核'),None);require(review,'审核记录不存在')
        review.update(status='已通过' if decision=='通过' else '已驳回',note=note,reviewer=u['name']);changed(review,u,'审核',note)
        r.update(reviewState=review['status'],approvedHash=tool_signature(r) if decision=='通过' else '');r['rev']+=1
        return deepcopy(review)
    if op=='tool.trial':
        require(r['engine']!='external','外部工具请使用登记的实际入口联调，本地不伪造结果')
        payload=json_value(p.get('payload',{}),dict);require(len(json.dumps(payload))<=200000,'试运行参数不能超过200KB')
        from shapely.errors import GEOSException
        from pyproj.exceptions import ProjError
        start=datetime.now();trial=record('trial',r['name']+' · 接口试运行',toolId=r['id'],toolHash=tool_signature(r),engine=r['engine'],input=deepcopy(payload),output=None,error='')
        try:trial['output']=run_tool(s,r,payload);trial['status']='成功'
        except (Invalid,ValueError,TypeError,KeyError,GEOSException,ProjError) as e:trial['status']='失败';trial['error']=getattr(e,'message',str(e))
        trial['durationMs']=round((datetime.now()-start).total_seconds()*1000,2);c['toolTrials'].append(trial);pm.event(s,u,'tool','后台接口试运行',r['id'],r['name'],status=trial['status'],durationMs=trial['durationMs']);return deepcopy(trial)
    raise Invalid('未知工具操作')

def run_tool(s,r,p):
    import analysis_engine as ae
    from shapely.geometry import shape, mapping, Point
    from shapely.validation import explain_validity
    from pyproj import Transformer
    engine=r['engine']
    import prototype.test.tool_center as tc
    if engine=='coordinate':return tc.coordinate(p)
    if engine=='buffer':
        lon=p.get('x');lat=p.get('y');distance=p.get('distance',100)
        require(all(type(v) in [int,float] and math.isfinite(v) for v in [lon,lat,distance]) and abs(lon)<=180 and abs(lat)<=85 and 0<distance<=100000,'请输入有效经纬度及1～100000米缓冲距离')
        from shapely.ops import transform
        local=f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m'
        forward=Transformer.from_crs('EPSG:4326',local,always_xy=True).transform;back=Transformer.from_crs(local,'EPSG:4326',always_xy=True).transform
        geometry=transform(back,transform(forward,Point(lon,lat)).buffer(distance,resolution=32));return dict(type='Feature',geometry=mapping(geometry),properties={'distanceMeters':distance})
    if engine=='spatial-check':return tc.check(p)
    if engine in ['spatial-store','spatial-edit','spatial-query']:
        key=text(p.get('resourceId',''));resource=cap.find(s['resources'],key);require(resource and resource['type']=='图层服务','请选择图层资源作为本地工作图层')
        layers=migrate(s).setdefault('spatialLayers',{});layer=layers.setdefault(key,dict(rev=1,features=[]))
        if engine=='spatial-query':
            q=text(p.get('q','')).casefold();region=text(p.get('region',''));coordinate=p.get('coordinate');point=None
            if coordinate is not None:
                require(isinstance(coordinate,list) and len(coordinate)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in coordinate),'定位坐标应为两个有限数值')
                point=tc.project(Point(coordinate),p.get('crs','EPSG:4326'),'EPSG:4326')
            rows=[x for x in layer['features'] if q in json.dumps(x.get('properties',{}),ensure_ascii=False).casefold() and (not region or region==x.get('properties',{}).get('region')) and (point is None or shape(x['geometry']).covers(point))]
            return dict(type='FeatureCollection',features=deepcopy(rows),total=len(rows),revision=layer['rev'],scope='本地工具工作图层')
        require(p.get('revision')==layer['rev'],'工作图层版本已变化，请先查询获取最新版本',409)
        fid=text(p.get('featureId',''),100)
        if engine=='spatial-edit' and not fid:
            name=text(p.get('name',''),100);matches=[x for x in layer['features'] if name and x.get('properties',{}).get('name')==name]
            require(len(matches)==1,'名称不存在或不唯一，请使用要素 ID');fid=matches[0]['id']
        require(fid,'要素标识必填');old=next((x for x in layer['features'] if x['id']==fid),None)
        if engine=='spatial-edit':require(p.get('operation','update') in ['update','delete'],'编辑操作应为 update 或 delete')
        if engine=='spatial-edit' and p.get('operation')=='delete':require(old,'要素不存在');layer['features'].remove(old)
        else:
            features=tc.normalize(p.get('geometry'),p.get('crs','EPSG:4326'))['features'];require(len(features)==1,'一次写入一个图形')
            geom=features[0]['geometry'];props=json_value(p.get('properties',(old or {}).get('properties',{})),dict);require(len(json.dumps(props))<=10000,'属性过长')
            if engine=='spatial-store':require(not old and len(layer['features'])<1000,'要素已存在或工作图层超过1000项')
            else:require(old,'要素不存在')
            value=dict(type='Feature',id=fid,geometry=geom,properties=props)
            if tc.datum_note(p.get('crs','EPSG:4326')):value['coordinateNote']=tc.datum_note(p.get('crs','EPSG:4326'))
            if old:layer['features'][layer['features'].index(old)]=value
            else:layer['features'].append(value)
        layer['rev']+=1;return dict(revision=layer['rev'],count=len(layer['features']),scope='仅变更本地工具工作图层，未写入生产GIS',coordinateNote=tc.datum_note(p.get('crs','EPSG:4326')))
    data=tc.normalize(p.get('geometry'),p.get('crs','EPSG:4326'))
    if engine=='compliance':output=ae.analyze(data,ae.catalog())
    elif engine in ['area','overlay']:output=ae.spatial_tool(data,'area' if engine=='area' else p.get('operation','intersection'),p.get('distance',0))
    else:raise Invalid('不支持的执行能力')
    if data.get('coordinateNote'):output['coordinateNote']=data['coordinateNote']
    return output


def todo_counts(rows):
    pending=[r for r in rows if r['status'] in ['待办','在办','已挂起']]
    return {'待办':len(pending),'正常':sum(r['timeliness']=='正常' for r in pending),'逾期':sum(r['timeliness']=='逾期' for r in pending),'预警':sum(r['timeliness']=='预警' for r in pending),'已办':sum(r['status'] in ['已办','已办结'] for r in rows)}
