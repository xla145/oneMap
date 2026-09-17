"""Additional local integration workflows. Sources and scope are server allowlisted."""
from copy import deepcopy
from collections import Counter
from datetime import datetime,timedelta
import math
import centers as c
import capabilities as cap
import portal_management as pm

SOURCES=[dict(id=k,name=n,filters=f) for k,n,f in [
 ('tasks','本人待办与办理记录',['status','timeliness','source']),
 ('resources','当前可见资源目录',['group','region','category']),
 ('deliveries','本人资源交付',['status','method']),
 ('subscriptions','本人资源订阅',['status']),
 ('mapQueries','本人地图查询',['mode','sceneName'])]]
BASE_METRICS=['待办','正常','逾期','预警','已办','消息','收藏']

def migrate(p):
    for k in ['boards','bookmarks','plans']:p.setdefault(k,[])
    p.setdefault('layerMetadata',{})
    for row in [p['settings'],p['settings']['published']]:
        row.setdefault('announcementAutoplay',False);row.setdefault('announcementSeconds',6)

def task_rows(s,u):return c.bootstrap(s,u,'front')['todos']

def board_definitions(s,u):
    return [r for r in s['integration']['boards'] if r['enabled'] and r['audience'] in ['全部',u['role']]]

def sources(s,u):
    import integration as ig
    own=c.bootstrap(s,u,'front')
    return dict(tasks=own['todos'],resources=ig.catalog(s,u),deliveries=own['deliveries'],subscriptions=own['subscriptions'],mapQueries=[r for r in s['integration']['mapHistory'] if r['userId']==u['id']])

def dashboard(s,u):
    defs=board_definitions(s,u);data=sources(s,u);out=[]
    for r in defs:
        rows=data[r['source']]
        rows=[x for x in rows if all(str(x.get(k,''))==v for k,v in r['filters'].items())]
        value=len(rows) if r['aggregate']=='count' else round(sum(float(x.get('areaHa',0)) for x in rows),4)
        out.append(dict(id=r['id'],name=r['name'],value=value,source=r['source'],sourceName=next(x['name'] for x in SOURCES if x['id']==r['source']),unit='项' if r['aggregate']=='count' else '公顷'))
    return out

def record_call(s,u,target,request_id):
    # Only called by successful server execution paths, never by a browser action.
    import integration as ig
    p=ig.migrate(s)
    if not any(e.get('requestId')==request_id and e['kind']=='call' for e in p['events']):
        p['events'].append(dict(id=c.ident('call'),kind='call',at=c.now(),target=target,requestId=request_id,userId=u['id'],department=u['department']))

def popularity(s,u,rows):
    p=s['integration'];keys={r['id']:r for r in rows};cut=(datetime.now()-timedelta(days=30)).isoformat(timespec='seconds')
    events=[e for e in p['events'] if e['at']>=cut];searches=Counter();calls=Counter();words=Counter();word_users={}
    for e in events:
        if e['kind']=='search':
            ids=set(e.get('matchedIds',[]));searches.update(ids&keys.keys())
            # Aggregate only multi-user searches whose recorded hits remain visible.
            if ids and ids<=keys.keys():words[e['query']]+=1;word_users.setdefault(e['query'],set()).add(e['userId'])
        if e['kind']=='call' and e['target'] in keys:calls[e['target']]+=1
    ranked=sorted(set(searches)|set(calls),key=lambda k:(-(searches[k]+calls[k]),-calls[k],k))[:8]
    return dict(popular=[dict(keys[k],count=searches[k]+calls[k],searchCount=searches[k],callCount=calls[k]) for k in ranked],globalHotwords=[dict(name=k,count=n) for k,n in words.most_common() if len(word_users[k])>=2][:5],popularityScope='近30天：搜索命中次数 + 服务端成功调用次数；入口访问和浏览器上报不计入调用量。')

def bootstrap(s,u,full):
    p=s['integration'];visible={r['id'] for r in cap.active(s,'resources') if cap.visible(u,r)}
    return dict(boards=deepcopy(p['boards']) if full else [],boardSources=deepcopy(SOURCES),dashboard=dashboard(s,u),layerMetadata={k:deepcopy(v) for k,v in p['layerMetadata'].items() if k in visible},bookmarks=[deepcopy(r) for r in p['bookmarks'] if r['userId']==u['id']],plans=deepcopy(p['plans']) if full else [],todoCounts=c.todo_counts(task_rows(s,u)))

def execute(s,u,op,arg):
    import integration as ig
    p=s['integration'];v=ig.values(arg)
    if op.startswith('bookmark.'):
        import integration_admin as ia
        cap.require(ia.rights(s,u)['view'],'需要成果查看权限',403)
        if op=='bookmark.delete':
            row=c.find(p['bookmarks'],arg.get('id'));cap.require(row and row['userId']==u['id'],'收藏不可访问',403);c.revision(row,arg);p['bookmarks'].remove(row);return dict(ok=True)
        import platform_domain as pd
        if op=='bookmark.restore':
            row=c.find(p['bookmarks'],arg.get('id'));cap.require(row and row['userId']==u['id'],'收藏不可访问',403)
            scene=ig.results.map_runtime(s,u,dict(sceneId=row['sceneId'],extraLayers=row.get('extraLayers',[])),strict=False);allowed={l['id'] for l in scene['config']['layers'] if l['access']=='已授权'}
            return dict(bookmark={**deepcopy(row),'extraLayers':scene['extraLayers']},layerIds=[x for x in row['layerIds'] if x in allowed],removedCount=len(set(row['layerIds'])-allowed))
        cap.require(op=='bookmark.save','未知收藏操作');scene=ig.results.map_runtime(s,u,dict(sceneId=v.get('sceneId'),extraLayers=v.get('extraLayers',[])));allowed={l['id'] for l in scene['config']['layers'] if l['access']=='已授权'}
        ids=v.get('layerIds',[]);cap.require(isinstance(ids,list) and all(isinstance(x,str) and x in allowed for x in ids),'包含未授权图层')
        state=v.get('view',{});cap.require(isinstance(state,dict),'视角格式错误');center=state.get('center',[])
        finite=lambda x:type(x) in [int,float] and math.isfinite(x)
        cap.require(isinstance(center,list) and len(center)==2 and all(finite(x) for x in center) and -180<=center[0]<=180 and -85<=center[1]<=85,'中心坐标无效')
        cap.require(finite(state.get('resolution')) and 0<state['resolution']<=2 and finite(state.get('rotation',0)) and abs(state.get('rotation',0))<=100,'视角参数无效')
        bases={r['id'] for r in scene['config']['basemaps']}|{'demo-img','demo-vec','demo-ter'};cap.require(state.get('basemapId') in bases,'底图无效')
        name=ig.text(v.get('name',''),60);cap.require(name,'收藏名称必填');cap.require(sum(r['userId']==u['id'] for r in p['bookmarks'])<50,'每人最多50个地图收藏')
        row=c.record('bookmark',name,userId=u['id'],sceneId=scene['id'],sceneName=scene['name'],sceneVersion=scene['version'],extraLayers=scene['extraLayers'],layerIds=list(dict.fromkeys(ids)),view={k:deepcopy(state[k]) for k in ['center','resolution','basemapId']},kind=v.get('kind','view'))
        cap.require(row['kind'] in ['view','layers'],'收藏类型无效');row['view']['rotation']=state.get('rotation',0);p['bookmarks'].append(row);return deepcopy(row)
    pm.admin(u)
    if op=='layer.metadata':
        key=arg.get('id');resource=cap.published(c.find(s['resources'],key));cap.require(resource and resource['type']=='图层服务' and cap.visible(u,resource),'图层资源不可用')
        old=p['layerMetadata'].get(key,dict(rev=0));cap.require(arg.get('rev',0)==old['rev'],'图层目录已更新',409)
        row={k:ig.text(v.get(k,''),200) for k in ['theme','department']}
        row['theme']='/'.join(x.strip() for x in row['theme'].split('/') if x.strip());cap.require(len(row['theme'].split('/'))<=4,'主题层级最多4级')
        for k in ['cities','hotspots']:
            values=v.get(k,[]);cap.require(isinstance(values,list) and len(values)<=30 and all(isinstance(x,str) and 0<len(x.strip())<=60 for x in values),'区域或热点标签格式错误');row[k]=list(dict.fromkeys(x.strip() for x in values))
        for field,options in [('dataKind',['未登记','矢量','栅格','证照']),('sourceScope',['未登记','厅内','厅外']),('collectionState',['未登记','待接入','接入中','已接入','异常'])]:
            row[field]=v.get(field,old.get(field,'未登记'));cap.require(row[field] in options,'登记分类无效')
        size=v.get('capacityBytes',old.get('capacityBytes'))
        cap.require(size is None or (type(size)is int and 0<=size<=10**18),'容量必须为非负整数或留空')
        row['capacityBytes']=size
        row['rev']=old['rev']+1;p['layerMetadata'][key]=row;return deepcopy(row)
    if op=='board.save':
        old=c.find(p['boards'],arg.get('id'))
        if arg.get('id'):c.revision(old,arg)
        source=next((r for r in SOURCES if r['id']==v.get('source')),None);cap.require(source,'请选择已授权的内置数据源')
        filters=v.get('filters',{});cap.require(isinstance(filters,dict) and all(k in source['filters'] and isinstance(val,str) and len(val)<=200 for k,val in filters.items()),'筛选字段无效')
        aggregate=v.get('aggregate','count');cap.require(aggregate=='count' or (aggregate=='sumArea' and source['id']=='mapQueries'),'该数据源不支持所选聚合')
        audience=v.get('audience','全部');cap.require(audience in ['全部']+[x['role'] for x in s['users']],'角色无效');enabled=v.get('enabled',True);cap.require(type(enabled)is bool,'启用状态无效')
        row=deepcopy(old) if old else c.record('board','');row.update(name=ig.text(v.get('name',''),60),source=source['id'],filters=filters,aggregate=aggregate,audience=audience,enabled=enabled);cap.require(row['name'],'指标名称必填');c.changed(row,u,'保存看板指标')
        if old:p['boards'][p['boards'].index(old)]=row
        else:p['boards'].append(row)
        return deepcopy(row)
    if op=='plan.save':
        old=c.find(p['plans'],arg.get('id'))
        if arg.get('id'):c.revision(old,arg)
        targets={r['id'] for r in c.migrate(s)['systems']}|{r['id'] for r in p['peers']};target=v.get('target');cap.require(target in targets,'接入对象不存在')
        row=deepcopy(old) if old else c.record('plan','');row.update({k:ig.text(v.get(k,''),1000 if k in ['note','evidence'] else 100) for k in ['name','owner','department','dueAt','phase','note','evidence']});row['target']=target
        cap.require(row['name'] and row['owner'] and row['phase'] in ['待准备','准备中','待联调','联调中','人工验收记录'],'计划名称、负责人或阶段无效')
        if row['dueAt']:
            try:datetime.strptime(row['dueAt'],'%Y-%m-%d')
            except ValueError:raise cap.Invalid('计划日期无效')
        cap.require(row['phase']!='人工验收记录' or len(row['evidence'])>=10,'请记录可追溯的人工验收依据')
        c.changed(row,u,'更新接入计划',row['phase']);row['scope']='人工计划与验收记录，不自动证明外部系统可用'
        if old:p['plans'][p['plans'].index(old)]=row
        else:p['plans'].append(row)
        return deepcopy(row)
    raise cap.Invalid('未知扩展操作',404)
