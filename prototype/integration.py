"""Integrated portal: published presentation, personal desk and local exchange/tenant workflows.
External peers are never marked connected by local validation or file exchange.
"""
from copy import deepcopy
from collections import Counter
from datetime import datetime
import re
import json
import centers as c
import capabilities as cap
import portal_management as pm
import integration_plus as xp
import integration_admin as ia
import integration_results as results

THEMES=['自然资源大管家','国土空间规划','耕地保护和国土绿化空间','要素保障','矿产资源','生态修复','督察执法','灾害防治']
KINDS=['数据','服务','工具','知识','智能体','应用场景']
PERMS=['read','write','members','children']
DEFAULT_PREF=dict(rev=1,order=[],groups={},todoStatus='全部',notify=True,popup=True,quietStart='',quietEnd='',refreshSeconds=60,metrics=['待办','正常','逾期','预警','已办','消息'],taskPopup=False,taskReminderStatuses=['逾期','预警'])

def migrate(s):
    c.migrate(s);p=s.setdefault('integration',{})
    for e in ['contents','announcements','events','checks','mapHistory','exchanges','received','tenants','members','tenantAssets','peers']:p.setdefault(e,[])
    for key in ['preferences','reads','placements']:p.setdefault(key,{})
    if not p.get('initialized'):
        p['settings']=dict(rev=1,title='一张图',subtitle='成果、资源与工作，一处连接',theme='green',background='',published=dict(title='一张图',subtitle='成果、资源与工作，一处连接',theme='green',background=''),version=1)
        for name,kind,url in [('资源中心','nav','#/front/shared-resources'),('工具中心','nav','#/front/capabilities'),('应用中心','nav','#/front/app-center'),('智能中心','nav','#/front/intelligence'),('运营中心','nav','#/admin/center-operations')]:
            r=c.record('content',name,kind=kind,description='进入'+name,url=url,image='',media='image',audience='平台管理员' if name=='运营中心' else '全部',startsAt='',endsAt='',order=len(p['contents']),color='#ffffff',button='进入',version=1)
            r['status']='已发布';r['published']=deepcopy(r);p['contents'].append(r)
        root=c.record('tenant','一张图·内蒙古',level='自治区',parentId='',region='全区',permissions=PERMS[:],enabled=True);root['id']='tenant-province';p['tenants'].append(root)
        for key,name,kind,direction in [('national','国家一张图节点','国家对接','双向'),('data-bureau','自治区公共数据平台','横向联动','双向'),('government','自治区政务服务平台','横向联动','双向')]:
            r=c.record('peer',name,kind=kind,direction=direction,endpoint='',authClientId='',contact='',mapping={'id':'id','name':'name','kind':'kind','url':'url'},statusNote='等待外部协议与联调');r['id']=key;r['status']='待配置';p['peers'].append(r)
        p['initialized']=True
    p['settings'].setdefault('maxAreaHa',1000000)
    p['settings']['published'].setdefault('maxAreaHa',1000000)
    for key,value in [('roleAreaLimits',{}),('bannerAutoplay',False),('bannerSeconds',6)]:
        p['settings'].setdefault(key,deepcopy(value));p['settings']['published'].setdefault(key,deepcopy(value))
    for row in [p['settings']]+p['contents']+p['announcements']:
        row.setdefault('versions',[])
        if row.get('published') and not row['versions']:
            row['versions'].append(dict(version=row.get('version',1),at=row.get('updated',''),actor='历史发布版本',snapshot=snapshot(row['published'])))
    xp.migrate(p)
    ia.migrate(s)
    return p

def is_admin(u):return u['role']=='平台管理员'
def text(v,n=2000):return c.text(v,n)
def values(p):
    v=p.get('values',{});cap.require(isinstance(v,dict),'字段格式错误');return v

def date_value(v):
    v=text(v,30)
    if v:
        try:d=datetime.fromisoformat(v);cap.require(d.tzinfo is None,'请使用不带时区的本地日期');v=d.isoformat(timespec='seconds')
        except ValueError:raise cap.Invalid('日期格式无效')
    return v

def scoped(r,u,s=None):
    if not (r.get('audience','全部') in ['全部',u['role']] and (not r.get('startsAt') or r['startsAt']<=c.now()) and (not r.get('endsAt') or c.now()<r['endsAt'])):return False
    if r.get('departments') and u['department'] not in r['departments']:return False
    if r.get('tenantIds'):
        if not s:return False
        p=s['integration'];ok=False
        for tenantId in r['tenantIds']:
            try:
                hierarchy=chain(p,tenantId)
                if not all(t['enabled'] for t in hierarchy):continue
                if not any(m['userId']==u['id'] and m['tenantId'] in [t['id'] for t in hierarchy] and 'read' in m['permissions'] for m in p['members']):continue
                tenant_access(p,u,tenantId);ok=True
            except cap.Invalid:pass
        if not ok:return False
    return True

def active(rows,u,s=None):
    return [deepcopy(r['published']) for r in rows if r.get('published') and r['status']!='已停用' and scoped(r['published'],u,s)]

def prefs(p,u):return deepcopy({**DEFAULT_PREF,**p['preferences'].get(u['id'],{})})
def quiet(pref):
    a,b=pref['quietStart'],pref['quietEnd'];t=datetime.now().strftime('%H:%M')
    return bool(a and b and (a<=t<b if a<b else t>=a or t<b))

def category(row):return {'数据库表':'数据','知识文档':'知识','图层服务':'服务','工具服务':'工具'}.get(row['kind'],row['kind'])
def catalog(s,u):
    p=migrate(s);rows=c.catalog(s,u)
    for r in rows:
        r['group']=category(r);r['placement']=deepcopy(p['placements'].get(r['id'],{}))
    return rows

def messages(s,u):
    p=migrate(s);read=set(p['reads'].get(u['id'],[]));out=[]
    for a in active(p['announcements'],u,s):
        key=a['id']+':'+str(a['version']);out.append(dict(id=key,name=a['name'],body=a['body'],at=a['updated'],kind=a['kind'],read=key in read,popup=a['popup'],style=a['style'],target=a['url'],announcement=True))
    for n in s['platform'].get('notifications',[]):
        if n['recipientId']==u['id']:out.append(dict(id='message:'+n['id'],name=n['title'],body=n['body'],at=n['at'],kind=n.get('category','系统通知'),read=n['read'],popup=False,target=n.get('target',''),announcement=False))
    pref=prefs(p,u)
    for t in xp.task_rows(s,u):
        if t['status'] not in ['待办','在办','已挂起'] or t['timeliness'] not in pref['taskReminderStatuses']:continue
        key='task:'+c.digest(json.dumps([t['id'],t['status'],t.get('dueAt',''),t['timeliness']],ensure_ascii=False))[:24]
        out.append(dict(id=key,name=t['name']+' · '+t['timeliness'],body='来源：'+t['source']+'；截止时间：'+(t.get('dueAt') or '未提供'),at=t.get('createdAt') or t.get('receivedAt',''),kind='任务提醒',read=key in read,popup=pref['taskPopup'],style='重点',target=t.get('entry',''),announcement=False,task=True))
    return sorted(out,key=lambda x:x['at'],reverse=True)

def chain(p,id):
    out=[];seen=set()
    while id:
        cap.require(id not in seen,'租户关系循环');seen.add(id);r=c.find(p['tenants'],id);cap.require(r,'租户不存在',404);out.append(r);id=r['parentId']
    return out

def tenant_access(p,u,id,permission='read'):
    rows=chain(p,id)
    if is_admin(u):return True
    cap.require(all(r['enabled'] for r in rows),'租户或上级已停用',403)
    cap.require(all(permission in r['permissions'] for r in rows),'超出上级开放权限',403)
    cap.require(any(m['userId']==u['id'] and m['tenantId'] in [r['id'] for r in rows] and permission in m['permissions'] for m in p['members']),'无租户操作权限',403)
    return True

def visible_tenants(p,u):
    out=[]
    for r in p['tenants']:
        try:tenant_access(p,u,r['id']);out.append(deepcopy(r))
        except cap.Invalid:pass
    return out

def metrics(s,u):
    rows=catalog(s,u);keys={r['id']:r for r in rows};events=migrate(s)['events'];month=c.now()[:7]
    hits=Counter(e['target'] for e in events if e['kind']=='open' and e['target'] in keys)
    words=Counter(e['query'] for e in events if e['kind']=='search' and e['userId']==u['id'] and e['query'])
    return dict(counts={k:sum(r['group']==k for r in rows) for k in KINDS},mostVisited=[dict(keys[k],count=n) for k,n in hits.most_common(8)],hotwords=[dict(name=k,count=n) for k,n in words.most_common(5)],monthOpens=sum(e['kind']=='open' and e['at'].startswith(month) and e['target'] in keys for e in events),**xp.popularity(s,u,rows))

def monitor(s,u,filters=None):
    pm.admin(u);p=migrate(s);rows=catalog(s,u);f=filters or {}
    start=text(f.get('start',''),10);end=text(f.get('end',''),10);department=text(f.get('department',''),200);period=f.get('period','day');eventType=f.get('eventType','all')
    for d in [start,end]:
        if d:
            try:datetime.strptime(d,'%Y-%m-%d')
            except ValueError:raise cap.Invalid('日期需为YYYY-MM-DD')
    cap.require(not start or not end or start<=end,'起始日期不能晚于结束日期')
    cap.require(period in ['day','week','month'] and eventType in ['all','success','failure','entry'],'统计粒度或事件类型无效')
    def selected(e):return (not start or e['at'][:10]>=start) and (not end or e['at'][:10]<=end) and (not department or e.get('department')==department)
    opens=[e for e in p['events'] if e['kind']=='open' and selected(e)] if eventType in ['all','entry'] else []
    allCalls=[dict(e,department=e.get('department') or '历史事件未记录部门') for e in pm.migrate(s)['events'] if e['kind']=='tool']
    calls=[e for e in allCalls if selected(e) and (eventType=='all' or e.get('status')=={'success':'成功','failure':'失败','entry':'打开入口'}[eventType])]
    def rank(items,key):return [dict(name=k,count=v) for k,v in Counter(x.get(key,'未登记') or '未登记' for x in items).most_common(20)]
    def bucket(e):
        d=datetime.strptime(e['at'][:10],'%Y-%m-%d')
        if period=='week':year,week,_=d.isocalendar();return f'{year}-W{week:02d}'
        return e['at'][:7] if period=='month' else e['at'][:10]
    trend=Counter(bucket(e) for e in opens)
    toolTrend=Counter(bucket(e) for e in calls)
    month=c.now()[:7]
    return dict(counts=metrics(s,u)['counts'],capacity=None,opens=len(opens),monthOpens=sum(e['at'].startswith(month) for e in opens),users=len({e['userId'] for e in opens}),tools=len(calls),monthTools=sum(e['at'].startswith(month) for e in calls),toolUsers=len({e['userId'] for e in calls}),toolSuccess=sum(e.get('status')=='成功' for e in calls),toolFailed=sum(e.get('status')=='失败' for e in calls),externalOpens=sum(e.get('status')=='打开入口' for e in calls),toolRanks=rank(calls,'name'),departmentRanks=rank(calls,'department'),resourceRanks=rank(opens,'name'),days=[dict(name=k,count=v) for k,v in sorted(trend.items())],toolTrend=[dict(name=k,count=v) for k,v in sorted(toolTrend.items())],themes=[dict(name=t,count=sum(r['placement'].get('theme')==t for r in rows)) for t in THEMES],providers=rank([dict(r,provider=r['placement'].get('department') or r.get('source')) for r in rows],'provider'),checks=deepcopy(p['checks'][-20:]),filters=dict(start=start,end=end,department=department,period=period,eventType=eventType),scope='事件统计遵循所选时间、调用部门及结果类型；成功、失败与外部入口打开分别统计。来源部门和主题数量是当前目录存量，不受事件筛选影响；容量未采集。')

def personal_workbench(s,u,filters=None):
    f=filters or {}; rows=xp.task_rows(s,u); counts=c.todo_counts(rows)
    status=f.get('status','全部'); source=f.get('source',''); query=text(f.get('query',''),200).lower()
    cap.require(status in ['全部','待办','正常','逾期','预警','已办'],'任务筛选无效')
    def match(r):
        pending=r['status'] in ['待办','在办','已挂起']
        return (status=='全部' or (status=='待办' and pending) or (status=='已办' and r['status'] in ['已办','已办结']) or (status in ['正常','逾期','预警'] and pending and r['timeliness']==status)) and (not source or r['source']==source) and (not query or query in r['name'].lower())
    return dict(todos=[r for r in rows if match(r)],counts=counts,sources=sorted({r['source'] for r in rows}),messages=messages(s,u),favorites=deepcopy(c.migrate(s)['favorites'].get(u['id'],[])),preferences=prefs(s['integration'],u))


def bootstrap(s,u,mode):
    p=migrate(s);full=mode=='admin' and is_admin(u);pref=prefs(p,u);tenants=visible_tenants(p,u);ids={r['id'] for r in tenants}
    result=dict(settings=deepcopy(p['settings'] if full else p['settings']['published']),contents=deepcopy(p['contents']) if full else active(p['contents'],u,s),announcements=deepcopy(p['announcements']) if full else [],preferences=pref,messages=messages(s,u),quiet=quiet(pref),catalog=catalog(s,u),metrics=metrics(s,u),themes=THEMES,canManage=full,tenants=tenants,tenantAssets=[deepcopy(r) for r in p['tenantAssets'] if r['tenantId'] in ids],members=[],permissions={},peers=deepcopy(p['peers']) if full else [],exchanges=deepcopy(p['exchanges'][-50:]) if full else [])
    for t in tenants:
        rights=[]
        for perm in PERMS:
            try:tenant_access(p,u,t['id'],perm);rights.append(perm)
            except cap.Invalid:pass
        result['permissions'][t['id']]=rights
        if 'members' in rights:result['members'] += [deepcopy(r) for r in p['members'] if r['tenantId']==t['id']]
    result['mapHistory']=[deepcopy(x) for x in p['mapHistory'] if x['userId']==u['id']][-20:]
    result['received']=deepcopy(p['received']) if full else []
    result.update(xp.bootstrap(s,u,full))
    result.update(ia.bootstrap(s,u,full))
    result['results']=results.bootstrap(s,u)
    if full:result['resultSystems']=deepcopy(p.get('resultSystems',{}))
    result['resourcePortal']=dict(settings=deepcopy(p['settings']['published']),contents=active(p['contents'],u,s),catalog=deepcopy(result['catalog']),metrics=deepcopy(result['metrics']))
    result['personalWorkbench']=personal_workbench(s,u)
    visible={r['id'] for r in result['catalog']}
    events=[e for e in p['events'] if e.get('target') in visible and e['kind'] in ['open','call']]
    result['resultUsage']=dict(counts=deepcopy(result['metrics']['counts']),opens=sum(e['kind']=='open' for e in events),calls=sum(e['kind']=='call' for e in events),users=len({e['userId'] for e in events}),scope='仅统计当前可见目录对象的入口访问与服务端成功调用；不代表外部系统运行情况。') if ia.rights(s,u)['view'] else None
    return result

def execute(s,u,action,payload):
    p=migrate(s);op=action.removeprefix('integration.');v=values(payload)
    if op.startswith('results.'):return results.execute(s,u,op[8:],payload)
    if op=='workbench':
        cap.require(ia.internal_access(s,u),'需要内部工作空间准入',403)
        return personal_workbench(s,u,payload)
    if op.startswith('admin.'):return ia.execute(s,u,op[6:],payload)
    if op=='map.query':
        cap.require(ia.rights(s,u)['analyze'],'需要成果空间分析授权',403)
        return map_query(s,u,payload)
    if op in ['bookmark.save','bookmark.restore','bookmark.delete','layer.metadata','board.save','plan.save']:return xp.execute(s,u,op,payload)
    if op=='preferences':
        old=prefs(p,u);cap.require(payload.get('rev')==old['rev'],'个人设置已变更，请刷新',409)
        row=dict(old);row.update({k:v[k] for k in DEFAULT_PREF if k!='rev' and k in v})
        cap.require(row['todoStatus'] in ['全部','待办','正常','已办','逾期','预警'],'任务筛选无效')
        cap.require(type(row['refreshSeconds']) is int and 30<=row['refreshSeconds']<=3600,'刷新周期为30～3600秒')
        for key in ['notify','popup','taskPopup']:cap.require(type(row[key]) is bool,'通知选项无效')
        cap.require(isinstance(row['taskReminderStatuses'],list) and all(x in ['正常','逾期','预警'] for x in row['taskReminderStatuses']),'任务提醒状态无效')
        for key in ['quietStart','quietEnd']:cap.require(isinstance(row[key],str) and (not row[key] or re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',row[key])),'免打扰时间无效')
        cap.require(bool(row['quietStart'])==bool(row['quietEnd']),'请完整填写免打扰起止时间')
        keys={r['id'] for r in catalog(s,u)}
        cap.require(isinstance(row['order'],list) and len(row['order'])<=200 and all(isinstance(k,str) and k in keys for k in row['order']) and len(set(row['order']))==len(row['order']),'排序包含不可见或重复资源')
        cap.require(isinstance(row['groups'],dict) and all(k in keys and isinstance(val,str) and len(val)<=30 for k,val in row['groups'].items()),'分组格式无效')
        cap.require(isinstance(row['metrics'],list) and all(x in xp.BASE_METRICS+[r['id'] for r in xp.board_definitions(s,u)] for x in row['metrics']),'看板指标无效')
        row['rev']+=1;p['preferences'][u['id']]=row;return deepcopy(row)
    if op=='message.read':
        key=text(payload.get('id',''));m=next((r for r in messages(s,u) if r['id']==key),None);cap.require(m,'消息不可访问',404)
        if m['announcement'] or m.get('task'):
            reads=p['reads'].setdefault(u['id'],[])
            if key not in reads:reads.append(key)
        else:c.find(s['platform']['notifications'],key.split(':',1)[1])['read']=True
        return dict(ok=True)
    if op in ['search','open']:
        rows=catalog(s,u);q=text(payload.get('query',''),100)
        target=next((r for r in rows if r['id']==payload.get('id')),None)
        if op=='open':cap.require(target,'资源已下架或无权访问',404)
        e=dict(id=c.ident('event'),at=c.now(),kind=op,query=q,target=target['id'] if target else '',name=target['name'] if target else '',userId=u['id'],department=u['department']);p['events'].append(e)
        if op=='open':
            if target['id'].startswith('knowledge:'):return dict(action='portalKnowledge',id=target['id'].split(':',1)[1])
            if target['id'].startswith('agent:'):return dict(action='agentDetail',id=target['id'].split(':',1)[1])
            return dict(target=target['target'])
        matches=[r for r in rows if q.lower() in json.dumps([r['name'],r['category'],r.get('source',''),r['placement']],ensure_ascii=False).lower()]
        e['matchedIds']=[r['id'] for r in matches] if q else []
        return dict(rows=matches,metrics=metrics(s,u))
    if op.startswith('tenant.'):
        return tenant_action(s,u,op,payload)
    pm.admin(u)
    if op in ['preview','versions','restore']:return publishing(s,u,op,payload)
    if op=='monitor':return monitor(s,u,payload)
    if op=='inspect':
        failures=[]
        for row in p['peers']:
            failures.append(dict(name=row['name'],status='待外部联调',reason='未配置端点' if not row['endpoint'] else '本地配置不能证明外部服务可用'))
        for row in c.migrate(s)['systems']:
            if not row['entry']:failures.append(dict(name=row['name'],status='配置缺失',reason='访问入口未配置'))
        available={r['id'] for r in catalog(s,u)}
        for key in p['placements']:
            if key not in available:failures.append(dict(name=key,status='资源不可用',reason='集成目录关联对象已下架或不可见'))
        row=dict(id=c.ident('check'),at=c.now(),name='集成依赖检查',failures=failures,scope='本地配置与引用检查，不执行外部网络探测');p['checks'].append(row);return deepcopy(row)
    if op in ['policy.save','policy.publish']:
        row=p['settings'];c.revision(row,payload)
        if op=='policy.save':
            limit=v.get('maxAreaHa');limits=v.get('roleAreaLimits',{})
            cap.require(type(limit) in [int,float] and 1<=limit<=10000000,'查询面积阈值为1～10000000公顷')
            cap.require(isinstance(limits,dict) and all(k in {x['role'] for x in s['users']} and type(n) in [int,float] and 1<=n<=limit for k,n in limits.items()),'角色面积限制无效')
            row.update(maxAreaHa=limit,roleAreaLimits=deepcopy(limits))
        else:
            for key in ['maxAreaHa','roleAreaLimits']:row['published'][key]=deepcopy(row[key])
            row['version']+=1;archive(row,u)
        row['rev']+=1;return deepcopy(row)
    if op=='settings.save':
        row=p['settings'];c.revision(row,payload);draft=dict(title=text(v.get('title',''),80),subtitle=text(v.get('subtitle',''),200),theme=v.get('theme','green'),background=media_value(v.get('background','')))
        cap.require(draft['title'] and draft['theme'] in ['green','blue'],'标题或主题无效');limit=v.get('maxAreaHa',row.get('maxAreaHa',1000000));cap.require(type(limit) in [int,float] and 1<=limit<=10000000,'查询面积阈值为1～10000000公顷');draft['maxAreaHa']=limit
        limits=v.get('roleAreaLimits',row.get('roleAreaLimits',{}));cap.require(isinstance(limits,dict),'角色面积限制格式错误')
        cap.require(all(k in {x['role'] for x in s['users']} and type(val) in [int,float] and 1<=val<=limit for k,val in limits.items()),'角色限制必须为1至门户上限，且角色存在')
        autoplay=v.get('bannerAutoplay',False);seconds=v.get('bannerSeconds',6);cap.require(type(autoplay) is bool and type(seconds) is int and 3<=seconds<=30,'轮播间隔为3～30整数秒')
        ann_auto=v.get('announcementAutoplay',row.get('announcementAutoplay',False));ann_secs=v.get('announcementSeconds',row.get('announcementSeconds',6));cap.require(type(ann_auto)is bool and type(ann_secs)is int and 3<=ann_secs<=30,'公告轮播间隔为3～30整数秒')
        draft.update(announcementAutoplay=ann_auto,announcementSeconds=ann_secs)
        draft.update(roleAreaLimits=limits,bannerAutoplay=autoplay,bannerSeconds=seconds);row.update(draft);row['rev']+=1;return deepcopy(row)
    if op=='settings.publish':
        row=p['settings'];c.revision(row,payload);row['published'].update({k:row[k] for k in ['title','subtitle','theme','background','bannerAutoplay','bannerSeconds','announcementAutoplay','announcementSeconds']});row['version']+=1;row['rev']+=1;archive(row,u);return deepcopy(row)
    if op=='placement':
        key=payload.get('id');cap.require(any(r['id']==key for r in catalog(s,u)),'资源不可见')
        old=p['placements'].get(key,dict(rev=0));cap.require(payload.get('rev',0)==old['rev'],'分类已变更',409)
        row={k:text(v.get(k,''),200) for k in ['theme','department','region','manual']};cap.require(not row['theme'] or row['theme'] in THEMES,'请选择八类场景主题');row['manual']=c.safe_entry(row['manual']);row['rev']=old['rev']+1;p['placements'][key]=row;return deepcopy(row)
    if op.startswith('peer.') or op.startswith('exchange.'):
        return exchange_action(s,u,op,payload)
    cap.require(op in ['save','publish','disable','delete'],'未知综合集成操作',404)
    entity=payload.get('entity');cap.require(entity in ['contents','announcements'],'对象类型无效')
    old=c.find(p[entity],payload.get('id'))
    if payload.get('id'):c.revision(old,payload)
    if op=='save':
        r=deepcopy(old) if old else c.record('portal',text(v.get('name',''),100),version=0)
        r.update(name=text(v.get('name',''),100),audience=text(v.get('audience','全部'),50),startsAt=date_value(v.get('startsAt','')),endsAt=date_value(v.get('endsAt','')),url=c.safe_entry(v.get('url','')) if not str(v.get('url','')).startswith('#/admin/') else text(v['url'],200))
        cap.require(r['name'] and r['audience'] in ['全部']+[x['role'] for x in s['users']],'名称或目标人群无效')
        cap.require(not r['url'].startswith('#/admin/') or r['audience']=='平台管理员','后台导航只允许向平台管理员发布')
        cap.require(not r['startsAt'] or not r['endsAt'] or r['startsAt']<r['endsAt'],'结束时间必须晚于开始时间')
        if entity=='contents':
            r.update(kind=v.get('kind','banner'),description=text(v.get('description',''),2000),image=media_value(v.get('image','')),media=v.get('media','image'),order=v.get('order',0),color=text(v.get('color','#ffffff'),7),button=text(v.get('button','查看'),30),symbol=text(v.get('symbol',''),10))
            cap.require(r['kind'] in ['banner','nav','secondary','advantage','promotion','dynamic'] and r['media'] in ['image','video'],'展示类型无效');cap.require(type(r['order']) is int and 0<=r['order']<=999,'排序需为0～999');cap.require(re.fullmatch(r'#[0-9a-fA-F]{6}',r['color']),'颜色需为六位十六进制')
        else:
            r.update(body=text(v.get('body',''),4000),kind=v.get('kind','门户更新'),popup=v.get('popup',True),style=v.get('style','普通'))
            cap.require(r['body'] and type(r['popup']) is bool and r['kind'] in ['门户更新','数据上新','功能更新','系统通知'] and r['style'] in ['普通','重点'],'公告内容或样式无效')
        for key,valid in [('departments',{x['department'] for x in s['users']}),('tenantIds',{x['id'] for x in p['tenants']})]:
            selected=v.get(key,[]);cap.require(isinstance(selected,list) and len(selected)<=200 and all(isinstance(x,str) and x in valid for x in selected),'目标部门或租户无效');r[key]=list(dict.fromkeys(selected))
        if entity=='contents' and r['media']=='video':cap.require(not r['image'].startswith('data:'),'视频只支持HTTPS地址，上传图片请选择图片类型')
        r['status']='草稿';c.changed(r,u,'保存草稿')
        if old:p[entity][p[entity].index(old)]=r
        else:p[entity].append(r)
    else:
        cap.require(old,'记录不存在',404);r=old
        if op=='publish':
            r['version']+=1;r['status']='已发布';c.changed(r,u,'发布');r['published']=snapshot(r);archive(r,u)
        elif op=='disable':r['status']='已停用';c.changed(r,u,'停用')
        else:cap.require(not r.get('published'),'已发布内容请停用，保留历史');p[entity].remove(r)
    pm.event(s,u,'operation','综合门户'+op,r['id'],r['name']);return deepcopy(r)

def tenant_action(s,u,op,arg):
    p=migrate(s);v=values(arg)
    if op=='tenant.save':
        old=c.find(p['tenants'],arg.get('id'));parent=v.get('parentId',old['parentId'] if old else 'tenant-province')
        if old:
            tenant_access(p,u,old['id'],'children');c.revision(old,arg);cap.require(parent==old['parentId'],'租户创建后不允许直接迁移上级')
        else:tenant_access(p,u,parent,'children')
        rights=v.get('permissions',['read']);cap.require(isinstance(rights,list) and 'read' in rights and all(k in PERMS for k in rights),'开放权限无效')
        if parent:cap.require(set(rights)<=set.intersection(*(set(x['permissions']) for x in chain(p,parent))),'不能超过上级权限模板')
        level=v.get('level','盟市');levels=['自治区','盟市','旗县'];cap.require(level in levels,'租户级别无效')
        if parent:cap.require(levels.index(level)==levels.index(c.find(p['tenants'],parent)['level'])+1,'下级租户必须逐级创建')
        else:cap.require(old and old['id']=='tenant-province' and level=='自治区','不能新增顶级租户')
        enabled=v.get('enabled',True);cap.require(type(enabled) is bool,'启用状态无效')
        row=deepcopy(old) if old else c.record('tenant','');row.update(name=text(v.get('name',''),100),parentId=parent,level=level,region=text(v.get('region',''),100),permissions=rights,enabled=enabled);cap.require(row['name'] and row['region'],'名称与行政区必填');c.changed(row,u,'保存租户')
        if old:p['tenants'][p['tenants'].index(old)]=row
        else:p['tenants'].append(row)
        return deepcopy(row)
    tenantId=arg.get('tenantId');perm='members' if op=='tenant.member' else 'write';tenant_access(p,u,tenantId,perm)
    if op=='tenant.member':
        user=cap.find(s['users'],v.get('userId'));cap.require(user and user['enabled'],'用户无效')
        rights=v.get('permissions',[]);cap.require(isinstance(rights,list) and all(x in PERMS for x in rights),'成员权限无效')
        cap.require(set(rights)<=set.intersection(*(set(x['permissions']) for x in chain(p,tenantId))),'成员不能超过租户模板')
        if not is_admin(u):
            for r in rights:tenant_access(p,u,tenantId,r)
        row=next((m for m in p['members'] if m['tenantId']==tenantId and m['userId']==user['id']),None)
        if row:cap.require(arg.get('rev')==row['rev'],'成员权限已变更',409);row.update(permissions=rights,rev=row['rev']+1)
        else:row=dict(id=c.ident('member'),tenantId=tenantId,userId=user['id'],permissions=rights,rev=1);p['members'].append(row)
        return deepcopy(row)
    cap.require(op=='tenant.asset','未知租户操作')
    old=c.find(p['tenantAssets'],arg.get('id'))
    if arg.get('id'):cap.require(old and old['tenantId']==tenantId,'不能跨租户写入',403);c.revision(old,arg)
    row=deepcopy(old) if old else c.record('tenant-asset','',tenantId=tenantId)
    row.update(name=text(v.get('name',''),100),description=text(v.get('description',''),4000),url=c.safe_entry(v.get('url','')));cap.require(row['name'],'资源名称必填');c.changed(row,u,'保存租户资源')
    if old:p['tenantAssets'][p['tenantAssets'].index(old)]=row
    else:p['tenantAssets'].append(row)
    return deepcopy(row)

def exchange_action(s,u,op,arg):
    p=migrate(s);v=values(arg)
    if op=='peer.save':
        old=c.find(p['peers'],arg.get('id'))
        if arg.get('id'):c.revision(old,arg)
        r=deepcopy(old) if old else c.record('peer','')
        r.update(name=text(v.get('name',''),100),kind=v.get('kind','横向联动'),direction=v.get('direction','双向'),endpoint=pm.https(text(v.get('endpoint',''),1000)),authClientId=text(v.get('authClientId',''),100),contact=text(v.get('contact',''),100),mapping=c.json_value(v.get('mapping',{'id':'id','name':'name','kind':'kind','url':'url'}),dict))
        cap.require(r['name'] and r['kind'] in ['国家对接','横向联动','纵向交换'] and r['direction'] in ['导入','导出','双向'],'接入类型或方向无效')
        cap.require(set(r['mapping'])=={'id','name','kind','url'} and all(isinstance(x,str) and x for x in r['mapping'].values()),'请映射id/name/kind/url字段')
        cap.require(not r['authClientId'] or c.find(s['platform']['authClients'],r['authClientId']),'认证客户端不存在')
        r['status']='配置完整·待联调' if r['endpoint'] and r['authClientId'] else '待配置';c.changed(r,u,'保存接入配置')
        if old:p['peers'][p['peers'].index(old)]=r
        else:p['peers'].append(r)
        return deepcopy(r)
    peer=c.find(p['peers'],arg.get('id'));cap.require(peer,'接入对象不存在',404)
    if op=='exchange.export':
        cap.require(peer['direction'] in ['导出','双向'],'该接入未开放导出')
        rows=[dict(id=r['id'],name=r['name'],kind=r['kind'],url='#'+r['target']) for r in catalog(s,u)]
        run=dict(id=c.ident('exchange'),peerId=peer['id'],name=peer['name'],at=c.now(),direction='导出',status='本地文件已生成',count=len(rows),error='',rows=rows);p['exchanges'].append(run)
        return dict(filename=peer['id']+'-目录交换.json',mime='application/json',content=json.dumps(rows,ensure_ascii=False,indent=2))
    cap.require(op=='exchange.import','未知交换操作');cap.require(peer['direction'] in ['导入','双向'],'该接入未开放导入')
    run=dict(id=c.ident('exchange'),peerId=peer['id'],name=peer['name'],at=c.now(),direction='导入',status='本地导入成功',count=0,error='',rows=[])
    try:
        rows=c.json_value(arg.get('rows',[]),list);cap.require(0<len(rows)<=200,'每批1～200条');seen=set();prepared=[]
        for item in rows:
            cap.require(isinstance(item,dict),'记录格式无效');row={k:text(item.get(key,''),500) for k,key in peer['mapping'].items()};cap.require(row['id'] and row['name'] and row['id'] not in seen,'标识/名称为空或同批标识重复');seen.add(row['id']);row['url']=c.safe_entry(row['url']);cap.require(row['kind'] in ['数据库表','图层服务','工具服务','知识','智能体','应用场景'],'资源类型无效');prepared.append(row)
        run['rows']=prepared;run['count']=len(prepared);run['added']=0;run['updatedCount']=0
        for item in prepared:
            old=next((x for x in p['received'] if x['peerId']==peer['id'] and x['externalId']==item['id']),None)
            if old:
                old.update(name=item['name'],kind=item['kind'],url=item['url'],updated=c.now(),rev=old['rev']+1);run['updatedCount']+=1
            else:
                p['received'].append(dict(id=c.ident('received'),peerId=peer['id'],externalId=item['id'],name=item['name'],kind=item['kind'],url=item['url'],updated=c.now(),rev=1));run['added']+=1
    except cap.Invalid as error:run['status']='导入失败';run['error']=error.message
    p['exchanges'].append(run);return deepcopy(run)


def map_query(s,u,arg):
    import platform_domain
    import analysis_engine as ae
    from shapely.geometry import Point,Polygon,shape,mapping
    from shapely.ops import transform
    from shapely.errors import GEOSException
    import math
    p=migrate(s);scene=results.map_runtime(s,u,arg)
    mode=arg.get('mode','polygon');cap.require(mode in ['point','penetrate','nearby','polygon','box'],'查询方式无效')
    layerIds=arg.get('layerIds',[]);cap.require(isinstance(layerIds,list) and all(isinstance(x,str) for x in layerIds),'图层格式无效')
    layers=[r for r in scene['config']['layers'] if r['access']=='已授权' and (not layerIds or r['id'] in layerIds)]
    cap.require(not layerIds or set(layerIds)<={r['id'] for r in layers},'包含未授权或不可用图层',403)
    if mode in ['point','penetrate','nearby']:
        x,y=arg.get('x'),arg.get('y');cap.require(all(type(v) in [int,float] and math.isfinite(v) for v in [x,y]) and -180<=x<=180 and -85<=y<=85,'请输入有效经纬度')
        point=Point(x,y);geom=point
        if mode=='nearby':
            radius=arg.get('radius',1000);cap.require(type(radius) in [int,float] and 1<=radius<=50000,'周边半径为1～50000米');geom=transform(ae.UNPROJECT,transform(ae.PROJECT,point).buffer(radius))
    else:
        data=ae.normalize(arg.get('geometry'),'EPSG:4326');cap.require(len(data['features'])==1,'范围查询一次选择一个多边形');geom=shape(data['features'][0]['geometry'])
    area=transform(ae.PROJECT,geom).area/10000
    limit=min(p['settings']['published']['maxAreaHa'],p['settings']['published'].get('roleAreaLimits',{}).get(u['role'],p['settings']['published']['maxAreaHa']));cap.require(area<=limit,'查询面积超过当前角色可用上限（'+str(limit)+'公顷）')
    rows=[]
    try:
        for layer in layers:
            for feature in layer['features']:
                if (shape(feature['geometry']) if feature.get('geometry') else Polygon(feature['coordinates'])).intersects(geom):rows.append(dict(feature,layerId=layer['id'],layerName=layer['name']))
    except GEOSException:raise cap.Invalid('空间查询范围计算失败')
    if mode=='point':rows=rows[:1]
    request={k:deepcopy(v) for k,v in arg.items() if k in ['sceneId','mode','layerIds','extraLayers','x','y','radius','geometry']}
    p['mapHistory'].append(dict(id=c.ident('query'),at=c.now(),userId=u['id'],sceneName=scene['name'],sceneVersion=scene['version'],mode=mode,count=len(rows),areaHa=round(area,4),request=request))
    for resource_id in {layer['resourceId'] for layer in layers}:
        p['events'].append(dict(id=c.ident('event'),kind='layerQuery',target='resource:'+resource_id,userId=u['id'],department=u['department'],at=c.now()))
    return dict(rows=rows,total=len(rows),queryGeometry=mapping(geom),areaHa=round(area,4),sceneVersion=scene['version'],history=deepcopy(p['mapHistory'][-1]),scope='本地示例图斑；经纬度使用现有场景近似基准，不作为测绘或审批结论')


def snapshot(row):
    return {k:deepcopy(v) for k,v in row.items() if k not in ['published','history','versions']}

def archive(row,u):
    row.setdefault('versions',[]).append(dict(version=row['version'],at=c.now(),actor=u['name'],snapshot=snapshot(row['published'])))

def media_value(value):
    value=text(value,350000)
    if value.startswith('data:'):
        from platform_features import image_value
        image_value(value)
    else:pm.https(value)
    return value

def publishing(s,u,op,arg):
    p=migrate(s);entity=arg.get('entity');cap.require(entity in ['settings','contents','announcements'],'发布对象无效')
    row=p['settings'] if entity=='settings' else c.find(p[entity],arg.get('id'));cap.require(row,'对象不存在',404)
    if op=='versions':return dict(entity=entity,id=row.get('id',''),rev=row['rev'],versions=deepcopy(row['versions']))
    c.revision(row,arg)
    if op=='preview':
        who=cap.find(s['users'],arg.get('userId',u['id']));cap.require(who and who['enabled'],'预览用户不可用')
        return dict(entity=entity,draft=snapshot(row),published=deepcopy(row.get('published')),visible=scoped(row,who,s) if entity!='settings' else True,user=who['name'],userId=who['id'],note='仅预览已保存草稿，不影响已发布版本。可见性同时检查角色、部门、租户及时间窗口。')
    target=next((x for x in row['versions'] if x['version']==arg.get('version')),None);cap.require(target,'历史版本不存在')
    preserved={'id','rev','version','published','versions','history','createdAt','updated','status'}
    for key in list(row):
        if key not in preserved:row.pop(key)
    row.update({k:deepcopy(v) for k,v in target['snapshot'].items() if k not in preserved})
    if entity=='settings':
        for key,default in [('roleAreaLimits',{}),('bannerAutoplay',False),('bannerSeconds',6),('maxAreaHa',1000000),('announcementAutoplay',False),('announcementSeconds',6)]:row.setdefault(key,deepcopy(default))
    else:row['status']='草稿'
    c.changed(row,u,'恢复历史版本到草稿','来源 v'+str(target['version']));pm.event(s,u,'operation','恢复门户草稿',row.get('id','settings'),row.get('name',row.get('title','')))
    return deepcopy(row)
