"""Application center and shared platform domain. Local demo, no external calls."""
from copy import deepcopy
from datetime import datetime, timedelta
import ast
import fnmatch
import hashlib
import hmac
import json
import math
import re
import time
import uuid
import capabilities as cap
import platform_features as features
import message_bus
from capabilities import require, Invalid
from platform_seed import migrate, record

ADMIN_ROLES={'平台管理员','应用管理员','流程管理员','单位管理员','区划管理员','资源审批人员'}
APP_ENTITIES={'apps','scenes','sceneTemplates','widgets','widgetGroups'}
FLOW_ENTITIES={'models','forms','workflows','businessAssets','businessGroups','businessSystems','delegations','helpDocs'}
SYSTEM_ENTITIES={'organizations','authClients','bindings','routes','upstreams','eventSources','subscriptions','channels'}
ENTITIES=APP_ENTITIES|FLOW_ENTITIES|SYSTEM_ENTITIES
VERSIONED={'scenes','sceneTemplates','widgets','models','forms','workflows'}
ASSET_KINDS=['操作管理','知识库关联','常用语管理','上下班管理','模板管理','日历管理','签名管理','通用规则','业务规则','变量库','参数库','常量库']
FIELDS={
    'apps':'name type targetId category description region ownerOrgId owner icon screenshots terminal entry',
    'scenes':'name description logo thumbnail templateId config region ownerOrgId',
    'sceneTemplates':'name description logo thumbnail config region ownerOrgId',
    'widgets':'name groupId code icon description engine terminal mapState entry packageName params region',
    'widgetGroups':'name', 'businessGroups':'name', 'businessSystems':'name groupId',
    'models':'name category systemId formId workflowId ruleIds sceneId description region',
    'forms':'name type externalUrl fields region',
    'workflows':'name description nodes formId timePolicyId knowledgeIds region',
    'businessAssets':'name kind code value valueType description region ownerId',
    'helpDocs':'name category body',
    'delegations':'name ownerId agentId modelId validFrom validUntil enabled',
    'organizations':'name parentId region',
    'authClients':'name appId group mfa enabled protocol entry',
    'bindings':'name userId clientId account enabled',
    'routes':'name path requiredRole limit timeout upstreams enabled',
    'upstreams':'name enabled latency',
    'eventSources':'name type priority enabled sourceSystem schema defaults allowedRoles',
    'subscriptions':'name eventType recipientId channelId enabled topic tags sourceSystem contentMode rank',
    'channels':'name type enabled concurrency failMode queueLimit',
}


def now(): return datetime.now().isoformat(timespec='seconds')
def ident(prefix=''): return prefix+uuid.uuid4().hex[:12]
def find(rows,key): return next((r for r in rows if r['id']==key),None)
def text(v,limit=2000):
    require(isinstance(v,str) and len(v)<=limit,'文字内容过长或格式不正确')
    return v.strip()
def published(r): return deepcopy(r.get('published')) if r and r.get('status')!='已停用' else None
def widget_version(p,binding):
    current=find(p['widgets'],binding.get('id'))
    if not current or current.get('status')=='已停用':return None
    versions=current.get('versions',[])+([current['published']] if current.get('published') else [])
    return next((deepcopy(v) for v in versions if v['version']==binding.get('version')),None)

def snapshot(r): return deepcopy({k:v for k,v in r.items() if k not in ['published','versions','submission','commands']})
def is_admin(u): return u['role']=='平台管理员'
def in_region(u,r): return u['region']=='全区' or r.get('region','全区') in ['全区',u['region']]
def within_scope(u,region): return u['region']=='全区' or region==u['region']
def manage(u,entity):
    return is_admin(u) or (entity in APP_ENTITIES and u['role']=='应用管理员') or (entity in FLOW_ENTITIES and u['role']=='流程管理员') or (entity=='organizations' and u['role'] in ['区划管理员','单位管理员'])
def revision(row,p): require(row['rev']==p.get('rev'),'记录已更新，请刷新后重试',409)
def audit(p,u,action,row):
    p['audit'].append(dict(id=ident(),at=now(),actor=u['name'],userId=u['id'],action=action,targetId=row.get('id',''),name=row.get('name','')))


def can_case(u,c):
    return in_region(u,c) and (is_admin(u) or u['role']=='流程管理员' or c['userId']==u['id'] or c['assigneeId']==u['id'] or any(t['userId']==u['id'] for t in c.get('subtasks',[])) or any(h.get('userId')==u['id'] for h in c.get('history',[])))


def bootstrap(s,u,mode="front"):
    p=migrate(s);out={}
    for entity,rows in p.items():
        if entity in APP_ENTITIES:
            if mode=="admin" and manage(u,entity):out[entity]=deepcopy(rows)
            elif entity=='apps':out[entity]=[{**deepcopy(r['published']),'listed':True,'views':r.get('views',0)} for r in rows if r.get('listed') and r.get('published') and in_region(u,r['published'])]
            elif entity in ['scenes','sceneTemplates']:out[entity]=[]
            else:out[entity]=[published(r) for r in rows if published(r)]
        elif entity in FLOW_ENTITIES:
            if mode=="admin" and manage(u,entity):out[entity]=deepcopy(rows)
            elif entity in ['models','forms','workflows']:out[entity]=[published(r) for r in rows if published(r) and in_region(u,r)]
            elif entity=='delegations':out[entity]=[deepcopy(r) for r in rows if u['id'] in [r['ownerId'],r['agentId']]]
            elif entity=='businessAssets':out[entity]=[deepcopy(r) for r in rows if in_region(u,r) and r['kind'] not in ['签名管理'] or (r['kind']=='签名管理' and r.get('ownerId')==u['id'])]
            else:out[entity]=deepcopy(rows)
        elif entity in SYSTEM_ENTITIES:
            out[entity]=deepcopy(rows) if is_admin(u) else []
        elif entity=='cases':out[entity]=[{**deepcopy(r),'isTodo':features.todo(p,u,r),'projectType':(find(p['projects'],r['projectId']) or {}).get('type','其他项目')} for r in rows if can_case(u,r) or (in_region(u,r) and can_handle(p,u,r))]
        elif entity=='projects':out[entity]=[deepcopy(r) for r in rows if in_region(u,r) and (is_admin(u) or u['role']=='流程管理员' or r.get('ownerId')==u['id'] or any(c['projectId']==r['id'] and can_case(u,c) for c in p['cases']))]
        elif entity=='supervisions':out[entity]=[deepcopy(r) for r in rows if (c:=find(p['cases'],r['caseId'])) and can_case(u,c)]
        elif entity=='dashboards':out[entity]=[deepcopy(r) for r in rows if r['id']==u['id']]
        elif entity=='notifications':out[entity]=[deepcopy(r) for r in rows if r['recipientId']==u['id']]
        elif entity=='registrations':out[entity]=[deepcopy(r) for r in rows if is_admin(u) or r.get('createdBy')==u['id']]
        elif entity=='recentApps':out[entity]=[deepcopy(r) for r in rows if r['userId']==u['id']]
        elif entity in ['events','deliveries','audit','gatewayCalls','identitySync','loginEvents']:out[entity]=deepcopy(rows[-200:]) if is_admin(u) else []
        else:out[entity]=deepcopy(rows)
    # Runtime config / submission snapshots are only exposed by authorized runtime APIs.
    if not manage(u,'apps'):
        for app in out['apps']:
            for key in ['targetSnapshot','reviews','review','submission','commands']:app.pop(key,None)
    if u['role'] in ['单位管理员','区划管理员']:
        out['organizations']=[deepcopy(r) for r in p['organizations'] if org_scope(p,u,r['id'])]
    out['users']=[{k:v for k,v in row.items() if k in ['id','name','role','department','region','orgId','enabled','rev','internalAccess']} for row in s['users'] if is_admin(u) or (u['role'] in ['单位管理员','区划管理员'] and org_scope(p,u,row.get('orgId'))) or (row['enabled'] and row['role'] in ['平台管理员','资源审批人员','流程管理员','业务用户'])]
    out['permissions']={'manageApps':manage(u,'apps'),'manageFlows':manage(u,'workflows'),'manageIdentity':is_admin(u) or u['role'] in ['单位管理员','区划管理员'],'manageSystem':is_admin(u)}
    out['permissions']['grantRoles']=list(sorted(ADMIN_ROLES|{'业务用户'})) if is_admin(u) else ['业务用户','单位管理员','区划管理员'] if u['role']=='区划管理员' else ['业务用户','单位管理员'] if u['role']=='单位管理员' else []
    for client in out.get('authClients',[]):client.pop('secretHash',None)
    if is_admin(u):
        out['channelStats']=[]
        for channel in p['channels']:
            deliveries=[r for r in p['deliveries'] if r['channelId']==channel['id']]
            finished=[r for r in deliveries if r['status'] in ['已送达','已处理']]
            recent=[r for r in finished if (datetime.now()-datetime.fromisoformat(r.get('processedAt',r.get('deliveredAt',r['at'])))).total_seconds()<60]
            latencies=[max(0,(datetime.fromisoformat(r.get('processedAt',r.get('deliveredAt',r['at'])))-datetime.fromisoformat(r['at'])).total_seconds()) for r in finished]
            out['channelStats'].append(dict(id=channel['id'],name=channel['name'],total=len(deliveries),backlog=sum(r['status'] in ['待投递','等待重试','待拉取','消费中'] for r in deliveries),errors=sum(r['status']=='失败队列' for r in deliveries),perMinute=len(recent),latencySeconds=round(sum(latencies)/len(latencies),2) if latencies else 0))
    else:out['channelStats']=[]
    out['assetKinds']=ASSET_KINDS
    out['engines']=[dict(id='local-2d',name='本地二维地图',status='可运行',crs=['EPSG:4490']),dict(id='external-3d',name='三维引擎适配',status='待接入',crs=['EPSG:4490'])]
    out['quality']=[dict(id=r['id'],name=r['name'],status='元数据完整性通过' if not missing else '待补充',missing=missing) for r in s['resources'] if cap.visible(u,r) for missing in [[label for key,label in [('source','来源'),('crs','坐标系'),('frequency','更新频次'),('aliases','业务同义词')] if not r.get(key)]+(['字段解释'] if any(not f.get('description') for f in r.get('fields',[])) else [])]]
    return out


def org_scope(p,u,org_id):
    if is_admin(u):return True
    current=find(p['organizations'],org_id)
    if not current:return False
    if u['role']=='区划管理员' and not within_scope(u,current.get('region')):return False
    if u['role'] not in ['单位管理员','区划管理员']:return False
    seen=set()
    while current and current['id'] not in seen:
        if current['id']==u.get('orgId'):return True
        seen.add(current['id']);current=find(p['organizations'],current.get('parentId'))
    return False


def scene_validate(s,row):
    p=s['platform'];c=row.get('config',{})
    require(isinstance(c,dict),'场景配置必须是对象')
    require(c.get('engine') in ['local-2d','external-3d'],'请选择地图引擎')
    require(c.get('crs')=='EPSG:4490','本地原型仅支持 EPSG:4490；其他坐标系需适配')
    bases=c.get('basemaps',[]);layers=c.get('layers',[]);widgets=c.get('widgets',[])
    require(isinstance(bases,list) and 0<len(bases)<=20,'至少配置一个底图，最多20个')
    require(len({b.get('id') for b in bases})==len(bases),'底图标识重复')
    require(all(b.get('name') and b.get('category') and b.get('crs')==c['crs'] for b in bases),'底图必须填写分类、名称，且坐标系一致')
    require(c.get('defaultBase') in [b.get('id') for b in bases],'必须选择一个默认底图')
    require(isinstance(layers,list) and len(layers)<=50,'图层数量超出范围')
    require(len({r.get('id') for r in layers})==len(layers),'图层标识不能重复')
    for layer in layers:
        resource=cap.published(find(s['resources'],layer.get('resourceId')))
        require(resource and resource['type']=='图层服务','关联图层资源不存在或未发布')
        require(resource.get('crs') in ['CGCS2000','EPSG:4490','CGCS2000 / EPSG:4490'],'图层坐标系必须与场景一致（EPSG:4490 / CGCS2000）')
        require(isinstance(layer.get('opacity',1),(int,float)) and 0<=layer.get('opacity',1)<=1,'透明度应在0到1之间')
        require(isinstance(layer.get('group',''),str),'图层目录格式错误')
    require(isinstance(widgets,list) and len(widgets)<=20,'控件配置不正确')
    for binding in widgets:
        w=widget_version(p,binding)
        require(w and w.get('version')==binding.get('version'),'控件未发布、已停用或版本不匹配')
        require(w.get('engine')==c['engine'],'控件与地图引擎不兼容')
        require(binding.get('terminal') in ['桌面','移动','桌面/移动'],'控件终端不正确')
        if w['code']=='assistant':
            require(cap.published(find(s['agents'],binding.get('params',{}).get('agentId'))),'请选择已发布智能体')
    extent=c.get('extent',[])
    require(isinstance(extent,list) and len(extent)==4 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in extent),'初始范围需要4个有效数字')
    require(-180<=extent[0]<extent[2]<=180 and -90<=extent[1]<extent[3]<=90,'地图范围不正确')
    panorama=c.get('panorama',extent)
    require(isinstance(panorama,list) and len(panorama)==4 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in panorama) and -180<=panorama[0]<panorama[2]<=180 and -90<=panorama[1]<panorama[3]<=90,'全景范围不正确')
    camera=c.get('camera',[111.7,40.8,100000]);require(isinstance(camera,list) and len(camera)==3 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in camera) and -180<=camera[0]<=180 and -90<=camera[1]<=90 and camera[2]>0,'相机位置需要经度、纬度和正高度')
    require(c.get('theme','forest') in ['forest','gray'],'主题不支持')
    for key,default in [('pointSize',5),('lineWidth',2),('labelSize',9)]:
        require(isinstance(c.get(key,default),(int,float)) and 1<=c.get(key,default)<=32,'点线文字尺寸必须在1到32之间')
    require(sorted(c.get('panelOrder',['layers','map','inspector']))==['inspector','layers','map'],'场景布局必须各包含一个目录、地图和属性区')
    for key in ['highlight','drawing']:require(re.fullmatch(r'#[0-9a-fA-F]{6}',c.get(key,'')),'请选择有效颜色')
    return {'valid':True,'warnings':['目录超过5级，建议精简层级'] if any(len(r.get('group','').split('/'))>5 for r in layers) else [],'engineStatus':'本地二维可运行' if c['engine']=='local-2d' else '三维引擎尚未接入'}


def validate(s,e,r):
    p=s['platform']
    require(text(r.get('name',''),100),'名称必填')
    for image_key in ['logo','thumbnail','icon']:
        value=r.get(image_key,'');require(isinstance(value,str),'图片字段无效')
        if value.startswith('data:'):features.image_value(value)
    if e=='apps' and isinstance(r.get('screenshots'),list):
        require(len(r['screenshots'])<=3,'最多上传3张截图')
        for value in r['screenshots']:features.image_value(value)
    if 'region' in r:require(r['region'] in ['全区','呼和浩特市','包头市','鄂尔多斯市','赤峰市','呼伦贝尔市'],'区域无效')
    if e in ['scenes','sceneTemplates']:scene_validate(s,r)
    if e=='scenes':require(not r.get('templateId') or find(p['sceneTemplates'],r['templateId']),'地图模板不存在')
    if e=='widgets':
        require(find(p['widgetGroups'],r.get('groupId')),'请选择控件分组')
        require(re.fullmatch(r'[a-zA-Z][\w-]{0,40}',r.get('code','')),'控件编码格式无效')
        require(r.get('entry','').startswith(('builtin:','package:')),'仅支持内置控件或登记包')
        require(r.get('engine') in ['local-2d','external-3d'],'引擎无效')
    if e=='apps':
        require(r.get('type') in ['scene','workflow','agent','external'],'应用类型无效')
        group={'scene':p['scenes'],'workflow':p['models'],'agent':s['agents'],'external':p['authClients']}[r['type']]
        require(find(group,r.get('targetId')),'目标场景、事项、智能体或接入客户端不存在')
        require(r.get('owner') and r.get('description'),'负责人和应用说明必填')
    if e=='forms':
        require(r.get('type') in ['内部表单','外部表单','虚拟表单'],'表单类型无效')
        fields=r.get('fields',[]);require(isinstance(fields,list) and len(fields)<=30,'表单字段无效')
        require(len({f.get('key') for f in fields})==len(fields),'字段编码重复')
        for f in fields:require(re.fullmatch(r'[a-zA-Z]\w{0,40}',f.get('key','')) and f.get('label') and f.get('type') in ['text','textarea','number','date'],'字段编码、名称或类型无效')
        if r['type']=='内部表单':require(fields,'内部表单至少需要一个字段')
    if e=='workflows':
        require(find(p['forms'],r.get('formId')),'表单不存在')
        nodes=r.get('nodes',[]);require(isinstance(nodes,list) and 0<len(nodes)<=12,'流程需要1至12个顺序节点')
        require(len({n.get('id') for n in nodes})==len(nodes),'节点标识重复')
        for n in nodes:
            user=find(s['users'],n.get('assigneeId'))
            require(n.get('name') and user and user['enabled'],'节点名称或办理人无效')
            require(isinstance(n.get('hours'),(int,float)) and 0<n['hours']<=240,'节点时限应在0至240个工作小时之间')
    if e=='models':
        require(find(p['forms'],r.get('formId')) and find(p['workflows'],r.get('workflowId')),'请选择表单与流程')
        require(r.get('category') in ['业务审批','数字会商'],'请选择业务分类')
        require(find(p['businessSystems'],r.get('systemId')),'业务体系不存在')
        require(all(find(p['businessAssets'],k) for k in r.get('ruleIds',[])),'规则引用不存在')
    if e=='businessSystems':require(find(p['businessGroups'],r.get('groupId')),'业务分组不存在')
    if e=='businessAssets':
        require(r.get('kind') in ASSET_KINDS,'业务资源类型无效');require(r.get('code'),'资源编码必填')
        if r['kind'] in ['业务规则','通用规则']:features.validate_rule(s,r.get('value',''))
        if r['kind'] in ['变量库','参数库','常量库']:
            require(re.fullmatch(r'[A-Za-z]\w{0,40}',r['code']),'库编码格式无效')
            require(not any(x['id']!=r['id'] and x.get('code')==r['code'] and x['kind'] in ['变量库','参数库','常量库'] for x in p[e]),'库编码重复')
        if r['kind']=='上下班管理':work_intervals(r['value'])
        if r['kind']=='日历管理':
            for line in r.get('value','').splitlines():
                parts=line.split(':');require(len(parts)==2 and parts[1] in ['休息','上班'],'日历格式：YYYY-MM-DD:休息 或 上班')
                try:datetime.strptime(parts[0],'%Y-%m-%d')
                except ValueError:raise Invalid('日历日期不正确')
    if e=='organizations':
        parent=r.get('parentId');seen={r['id']}
        while parent:
            require(parent not in seen,'组织不能循环关联');seen.add(parent)
            item=find(p['organizations'],parent);require(item,'上级组织不存在');parent=item.get('parentId')
    if e=='delegations':
        require(r.get('ownerId')!=r.get('agentId') and find(s['users'],r.get('ownerId')) and find(s['users'],r.get('agentId')),'委托人与代理人无效')
        require(r.get('validFrom','')<=r.get('validUntil','') and r.get('validUntil'),'委托有效期无效')
    if e=='subscriptions':
        require(find(s['users'],r.get('recipientId')) and find(p['channels'],r.get('channelId')),'接收用户或通道不存在')
        require(isinstance(r.get('eventType'),str) and re.fullmatch(r'[A-Za-z0-9_.*?:-]{1,100}',r['eventType']),'事件类型格式无效')
        require(isinstance(r.get('tags',[]),list) and all(isinstance(t,str) for t in r.get('tags',[])),'订阅标签无效')
        require(r.get('contentMode','全量') in ['全量','摘要'] and isinstance(r.get('rank',100),int),'订阅匹配策略无效')
        require(not any(x['id']!=r['id'] and all(x.get(k)==r.get(k) for k in ['eventType','recipientId','channelId','topic','tags','sourceSystem']) and x.get('enabled') and r.get('enabled') for x in p[e]),'该接收人和通道已有相同订阅')
    if e=='eventSources':
        require(isinstance(r.get('priority'),int) and 1<=r['priority']<=9,'优先级为1至9，1最高')
        require(isinstance(r.get('type'),str) and re.fullmatch(r'[A-Za-z0-9_.*?:-]{1,100}',r['type']),'事件类型格式无效')
        require(isinstance(r.get('schema',{}),dict) and all(v in ['string','number','boolean','object','array'] for v in r.get('schema',{}).values()),'Schema需为字段名到类型的JSON对象')
        require(isinstance(r.get('defaults',{}),dict),'默认字段需为JSON对象')
        require(isinstance(r.get('allowedRoles',[]),list) and all(role in ADMIN_ROLES|{'业务用户'} for role in r.get('allowedRoles',[])),'事件接收角色无效')
    if e=='routes':
        require(isinstance(r.get('limit'),int) and 1<=r['limit']<=1000,'每分钟限额应为1至1000')
        require(isinstance(r.get('timeout'),int) and 1<=r['timeout']<=30000,'超时时间应为1至30000毫秒')
        require(r.get('upstreams') and all(find(p['upstreams'],i) for i in r['upstreams']),'请选择合法上游')
    if e=='channels':
        require(r.get('type') in ['站内消息','本地示例接收端','拉取队列'] and isinstance(r.get('concurrency'),int) and 1<=r['concurrency']<=8,'通道类型或并发数无效')
        require(isinstance(r.get('queueLimit',1000),int) and 1<=r.get('queueLimit',1000)<=100000,'队列长度需要1至100000')
    if e=='upstreams':require(isinstance(r.get('latency'),int) and 0<=r['latency']<=10000,'示例延时无效')
    if e=='bindings':require(find(s['users'],r.get('userId')) and find(p['authClients'],r.get('clientId')),'绑定用户或应用无效')


def save_record(s,u,payload):
    p=s['platform'];e=payload.get('entity');require(e in ENTITIES,'业务类型不存在')
    require(manage(u,e),'没有此模块的管理权限',403)
    old=find(p[e],payload.get('id'))
    if payload.get('id'):require(old,'记录不存在',404);revision(old,payload)
    if old and e=='apps':require(old.get('status')!='待审核','待审核版本请先撤回后编辑',409)
    r=deepcopy(old) if old else record(ident(e+'_'),'')
    values=payload.get('values',{});require(isinstance(values,dict) and len(json.dumps(values))<1500000,'配置过大或格式无效')
    for k in FIELDS[e].split():
        if k in values:r[k]=text(values[k],350000 if k in ['logo','thumbnail','icon'] else 30000) if isinstance(values[k],str) else deepcopy(values[k])
    if not is_admin(u) and e=='organizations':
        require((old and org_scope(p,u,old['id'])) or org_scope(p,u,r.get('parentId')),'不能管理其他组织',403)
        require(within_scope(u,r.get('region')),'不能扩大区划范围',403)
    validate(s,e,r)
    r.update(rev=(old['rev']+1 if old else 1),updated=now())
    if e in VERSIONED or e=='apps':r['status']='草稿'
    if e=='apps':r.setdefault('listed',False);r.setdefault('reviews',[]);r.setdefault('views',0)
    secret=None
    if e=='authClients':
        r.setdefault('key','demo_'+r['id'])
        if not old:
            secret=uuid.uuid4().hex+uuid.uuid4().hex;r['secretHash']=hashlib.sha256(secret.encode()).hexdigest()
    if e=='workflows':r['deployed']=False
    if old:p[e][p[e].index(old)]=r
    else:p[e].append(r)
    audit(p,u,'保存'+e,r)
    if secret:return {**deepcopy(r),'appSecret':secret}
    return r


def emit(p,u,event_type,row,recipient=None):
    key=event_type+':'+row['id']+':'+str(row.get('rev',1))+(':'+recipient if recipient else '')
    if find(p['events'],key):return
    sources=[s for s in p['eventSources'] if s.get('enabled') and fnmatch.fnmatchcase(event_type,s['type'])]
    if not sources:return
    event=dict(id=key,type=event_type,aggregateId=row['id'],aggregateVersion=row.get('rev',1),name=row.get('name',''),category=row.get('category','应用动态'),region=row.get('region','全区'),actor=u['name'],at=now(),priority=min(s['priority'] for s in sources),recipientId=recipient,traceId=ident('trace_'))
    event.update(topic=row.get('topic',''),tags=row.get('tags',[]),sourceSystem=row.get('sourceSystem','local'),data=deepcopy(row.get('data',{})))
    restricted=[set(source['allowedRoles']) for source in sources if source.get('allowedRoles')]
    event['allowedRoles']=sorted(set.intersection(*restricted)) if restricted else []
    event['denyAll']=bool(restricted) and not event['allowedRoles']
    p['events'].append(event)
    for sub in sorted(p['subscriptions'],key=message_bus.specificity):
        if not sub.get('enabled') or not message_bus.matches(sub,event):continue
        if recipient and sub['recipientId']!=recipient:continue
        existing=next((d for d in p['deliveries'] if d['eventId']==key and d['channelId']==sub['channelId'] and d['recipientId']==sub['recipientId']),None)
        if existing:
            existing.setdefault('subscriptionIds',[existing['subscriptionId']]).append(sub['id']);continue
        delivery=dict(id=ident('delivery_'),eventId=key,subscriptionId=sub['id'],channelId=sub['channelId'],recipientId=sub['recipientId'],status='待投递',attempt=0,at=now(),nextRetryAt=now(),error='')
        delivery['subscriptionIds']=[sub['id']]
        channel=find(p['channels'],sub['channelId'])
        queued=sum(d['channelId']==sub['channelId'] and d['status'] in ['待投递','等待重试','待拉取','消费中'] for d in p['deliveries'])
        if channel and queued>=channel.get('queueLimit',1000):delivery.update(status='失败队列',error='通道队列已满，请释放容量后重试')
        p['deliveries'].append(delivery)


def dispatch(s):
    p=s['platform'];stamp=datetime.now();processed={}
    ordered=sorted(p['deliveries'],key=lambda d:((find(p['events'],d['eventId']) or {}).get('priority',99),d.get('at','')))
    for d in ordered:
        if d['status']=='消费中' and d.get('leaseUntil','')<=now():d.update(status='失败队列' if d['attempt']>=3 else '等待重试',nextRetryAt=(stamp+timedelta(seconds=2**d['attempt'])).isoformat(timespec='seconds'),error='消费租约过期，未收到业务ACK')
        if d['status'] not in ['待投递','等待重试'] or d.get('nextRetryAt','')>stamp.isoformat(timespec='seconds'):continue
        event=find(p['events'],d['eventId']);channel=find(p['channels'],d['channelId']);user=find(s['users'],d['recipientId'])
        subscriptions=[find(p['subscriptions'],sid) for sid in d.get('subscriptionIds',[d['subscriptionId']])]
        valid=event and not event.get('denyAll') and any(sub and sub.get('enabled') and sub['recipientId']==d['recipientId'] and sub['channelId']==d['channelId'] and message_bus.matches(sub,event) for sub in subscriptions)
        if event and event.get('allowedRoles') and user and user['role'] not in event['allowedRoles']:valid=False
        if not user or not user['enabled'] or not valid or not in_region(user,event):d.update(status='已取消',error='用户、订阅或当前访问范围已失效');continue
        if event['type'].startswith('workflow.'):
            case=find(p['cases'],event['aggregateId'])
            if not case or not (can_case(user,case) or (in_region(user,case) and can_handle(p,user,case))):d.update(status='已取消',error='办件已不可访问');continue
        capacity=channel.get('concurrency',1) if channel else 1
        if processed.get(d['channelId'],0)>=capacity:continue
        processed[d['channelId']]=processed.get(d['channelId'],0)+1
        if channel and channel.get('enabled') and channel['type']=='拉取队列' and not channel.get('failMode'):
            d.update(status='待拉取',error='');continue
        d['attempt']+=1
        if not channel or not channel.get('enabled') or channel.get('failMode'):
            d.update(status='失败队列' if d['attempt']>=3 else '等待重试',error='通道停用或示例接收端返回失败',nextRetryAt=(stamp+timedelta(seconds=2**d['attempt'])).isoformat(timespec='seconds'))
            continue
        d.update(status='已送达',error='',deliveredAt=now())
        if channel['type']=='站内消息' and not any(n['eventId']==d['eventId'] and n['recipientId']==d['recipientId'] and n.get('channelId','ch_inbox')==d['channelId'] for n in p['notifications']):
            target='/front/cases/'+event['aggregateId'] if event['type'].startswith('workflow.') else '/front/applications' if event['type'].startswith('resource.') else '/front/app-center/'+event['aggregateId'] if find(p['apps'],event['aggregateId']) else '/front/messages'
            body={'app.listed':'应用已审核上架','app.delisted':'应用已下架','workflow.task.created':'您有新的办理任务','workflow.task.complete':'事项流转到您的办理节点','workflow.progress.created':'申请已提交','workflow.progress.complete':'事项办理进度已更新','workflow.supervision.created':'您有新的督办提醒','workflow.compliance.changed':'合规核查结果已更新','resource.request.decided':'资源申请已有办理结果'}.get(event['type'],'办理任务已更新' if event['type'].startswith('workflow.task.') else '事项状态已更新')
            p['notifications'].append(dict(id=ident('msg_'),eventId=event['id'],subscriptionId=d['subscriptionId'],channelId=d['channelId'],category=event.get('category','应用动态'),recipientId=user['id'],title=event['name'],body=body,at=now(),read=False,target=target))


def transition(s,u,payload):
    p=s['platform'];e=payload.get('entity');require(e in ENTITIES,'类型无效');require(manage(u,e),'没有管理权限',403)
    r=find(p[e],payload.get('id'));require(r,'记录不存在',404);revision(r,payload);command=payload.get('command')
    if command=='copy':
        require(e in ['scenes','sceneTemplates','forms','workflows','models'],'不支持复制')
        values={k:deepcopy(r[k]) for k in FIELDS[e].split() if k in r};values['name']=r['name']+'（副本）'
        return save_record(s,u,dict(entity=e,values=values))
    if command=='delete':
        require(not (e=='apps' and r.get('listed')),'上架应用应先下架')
        ref_fields={'widgetGroups':('widgets','groupId'),'sceneTemplates':('scenes','templateId'),'businessGroups':('businessSystems','groupId'),'businessSystems':('models','systemId'),'forms':('models','formId'),'workflows':('models','workflowId'),'channels':('subscriptions','channelId')}
        if e in ref_fields:
            group,field=ref_fields[e];require(not any(x.get(field)==r['id'] for x in p[group]),'存在关联记录，请先解除引用')
        if e in VERSIONED and e!='sceneTemplates':require(not r.get('published'),'已发布记录请停用，保留历史')
        p[e].remove(r);audit(p,u,'删除'+e,r);return {'ok':True}
    if e=='apps':
        if command=='submit':
            require(r['status'] in ['草稿','已驳回','已下架'],'当前状态不能提交审核',409);validate(s,e,r)
            target=find(p['scenes'],r['targetId']) if r['type']=='scene' else None
            if target:scene_validate(s,target)
            r['submission']=snapshot(r)
            if target:r['submission']['targetSnapshot']=snapshot(target)
            features.ensure_app(s,r['submission'])
            r['status']='待审核'
        elif command=='withdraw':require(r['status']=='待审核','当前不是待审核状态',409);r['status']='草稿';r.pop('submission',None)
        elif command in ['approve','reject']:
            require(is_admin(u),'上架审核需要平台审核权限',403);require(r['status']=='待审核' and r.get('submission'),'应用不在待审核状态',409)
            note=text(payload.get('note',''));require(note,'请填写审核意见')
            r['reviews'].append(dict(at=now(),actor=u['name'],decision=command,note=note,revision=r['submission']['rev']))
            if command=='approve':
                validate(s,e,r['submission'])
                if r['type']=='scene':scene_validate(s,r['submission']['targetSnapshot'])
                features.ensure_app(s,r['submission'])
                r['version']=r.get('version',0)+1;r['published']=deepcopy(r['submission']);r['published'].update(version=r['version'],status='已上架');r.update(status='已上架',listed=True)
            else:r['status']='已驳回'
            r.pop('submission',None)
        elif command=='disable':
            require(r.get('listed'),'应用尚未上架');require(text(payload.get('note','')),'请填写下架原因');r.update(status='已下架',listed=False,delistReason=text(payload['note']))
        else:raise Invalid('不支持的应用操作')
        r['rev']+=1;r['updated']=now();audit(p,u,'应用'+command,r)
        if command in ['approve','disable']:emit(p,u,'app.listed' if command=='approve' else 'app.delisted',r)
        return r
    if command=='deploy':require(e=='workflows','仅流程支持部署');validate(s,e,r);r['deployed']=True
    elif command=='publish':
        require(e in VERSIONED,'此记录无需发布');validate(s,e,r)
        if e=='workflows':require(r.get('deployed'),'请先校验并部署流程')
        if e=='widgets':require(r.get('entry','').startswith('builtin:'),'外部控件包已登记；隔离运行适配器尚未接入，不能发布为可运行')
        if r.get('published'):r.setdefault('versions',[]).append(deepcopy(r['published']))
        r.update(status='已发布',version=r.get('version',0)+1);r['published']=snapshot(r)
    elif command=='disable':
        r['status']='已停用'
        if e in ['scenes','models']:
            for app in p['apps']:
                if app.get('listed') and app.get('published',{}).get('targetId')==r['id']:
                    app.update(listed=False,status='已下架',delistReason='关联目标已停用',rev=app['rev']+1)
                    audit(p,u,'关联停用自动下架',app);emit(p,u,'app.delisted',app)
    else:raise Invalid('不支持的状态变更')
    r['rev']+=1;r['updated']=now();audit(p,u,command+' '+e,r);return r


def work_intervals(value):
    intervals=[]
    try:
        for part in value.split(','):
            start,end=part.strip().split('-');a=datetime.strptime(start,'%H:%M');b=datetime.strptime(end,'%H:%M')
            intervals.append((a.hour*60+a.minute,b.hour*60+b.minute))
    except (ValueError,AttributeError):raise Invalid('工作时段格式为09:00-12:00,14:00-18:00')
    intervals.sort();require(intervals and all(a<b for a,b in intervals) and all(intervals[i-1][1]<=intervals[i][0] for i in range(1,len(intervals))),'工作时段不能重叠或倒置')
    return intervals


def deadline(p,hours,policy_id='',start=None):
    policy=find(p['businessAssets'],policy_id);intervals=work_intervals(policy['value'] if policy else '09:00-12:00,14:00-18:00')
    exceptions={}
    for row in p['businessAssets']:
        if row['kind']=='日历管理' and row.get('status')!='已停用':
            for line in row['value'].splitlines():
                date,kind=line.split(':');exceptions[date]=kind
    t=(start or datetime.now()).replace(second=0,microsecond=0);left=math.ceil(hours*60)
    for _ in range(365*24*60):
        day=t.date().isoformat();working=exceptions.get(day,'上班' if t.weekday()<5 else '休息')=='上班'
        minute=t.hour*60+t.minute
        if working and any(a<=minute<b for a,b in intervals):left-=1
        t+=timedelta(minutes=1)
        if left<=0:return t.isoformat(timespec='seconds')
    raise Invalid('日历没有足够工作时段')


def safe_rule(expression,context):
    tree=features.rule_tree(expression)
    require(len(list(ast.walk(tree)))<=80,'规则过于复杂')
    ops={ast.Gt:lambda a,b:a>b,ast.GtE:lambda a,b:a>=b,ast.Lt:lambda a,b:a<b,ast.LtE:lambda a,b:a<=b,ast.Eq:lambda a,b:a==b,ast.NotEq:lambda a,b:a!=b,ast.Add:lambda a,b:a+b,ast.Sub:lambda a,b:a-b,ast.Mult:lambda a,b:a*b,ast.Div:lambda a,b:a/b,ast.Mod:lambda a,b:a%b}
    def run(n):
        if isinstance(n,ast.Expression):return run(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(str,int,float,bool)):return n.value
        if isinstance(n,ast.Name):require(n.id in context,'规则变量不存在：'+n.id);return context[n.id]
        if isinstance(n,ast.UnaryOp):return not run(n.operand) if isinstance(n.op,ast.Not) else -run(n.operand) if isinstance(n.op,ast.USub) else +run(n.operand)
        if isinstance(n,ast.BinOp) and type(n.op) in ops:return ops[type(n.op)](run(n.left),run(n.right))
        if isinstance(n,ast.Compare) and all(type(o) in ops for o in n.ops):
            values=[run(n.left)]+[run(c) for c in n.comparators];return all(ops[type(op)](values[i],values[i+1]) for i,op in enumerate(n.ops))
        if isinstance(n,ast.BoolOp):return all(run(v) for v in n.values) if isinstance(n.op,ast.And) else any(run(v) for v in n.values)
        raise Invalid('只支持字段、数字、比较和受控算术条件')
    try:return bool(run(tree))
    except (TypeError,ValueError,ZeroDivisionError,OverflowError):raise Invalid('规则数据类型不匹配或算术结果无效')


def create_case(s,u,payload):
    p=s['platform'];key=text(payload.get('requestId',''),100);require(key,'提交标识必填')
    old=next((c for c in p['cases'] if c.get('requestId')==key and c['userId']==u['id']),None)
    if old:return old
    model=published(find(p['models'],payload.get('modelId')));require(model and in_region(u,model),'事项未发布或不可访问',404)
    workflow=published(find(p['workflows'],model['workflowId']));form=published(find(p['forms'],model['formId']));require(workflow and form,'流程或表单尚未发布')
    require(form['type']!='外部表单','外部表单运行适配器尚未接入')
    values=payload.get('formData',{});require(isinstance(values,dict),'表单数据无效');data={}
    for f in form['fields']:
        v=values.get(f['key'],'');require(not f.get('required') or v not in ['',None],f['label']+'必填')
        if v not in ['',None] and f['type']=='number':
            try:v=float(v)
            except (ValueError,TypeError):raise Invalid(f['label']+'必须是数字')
            require(math.isfinite(v) and abs(v)<1e12,'数值超出范围')
        elif v is not None:v=text(v)
        data[f['key']]=v
    region=payload.get('region',u['region']);require(region in ['全区','呼和浩特市','包头市','鄂尔多斯市','赤峰市','呼伦贝尔市'] and within_scope(u,region),'事项区域超出权限',403)
    checks=[]
    for key in model.get('ruleIds',[]):
        rule=find(p['businessAssets'],key);require(rule and rule.get('status')!='已停用','绑定规则不可用')
        result=safe_rule(rule['value'],features.rule_context(p,data,rule['value']));checks.append(dict(name=rule['name'],passed=result,expression=rule['value'],rev=rule['rev']));require(result,'表单不符合规则：'+rule['name'])
    project=find(p['projects'],payload.get('projectId'))
    if payload.get('projectId'):
        require(project and project['region']==region and (is_admin(u) or project.get('ownerId')==u['id']),'项目不存在、区域不一致或不属于当前用户',403)
    else:
        project_type=payload.get('projectType','其他项目');require(project_type in ['建设用地','耕地保护','生态修复','地灾防治','其他项目'],'项目类型无效')
        project=record(ident('project_'),text(data.get('projectName') or model['name'],100),type=project_type,region=region,ownerId=u['id']);p['projects'].append(project)
    node=workflow['nodes'][0];case=record(ident('case_'),text(data.get('projectName') or model['name'],100),modelId=model['id'],category=model['category'],projectId=ident('project_'),userId=u['id'],region=region,formData=data,workflow=workflow,form=form,nodeIndex=0,assigneeId=node['assigneeId'],dueAt=deadline(p,node['hours'],workflow.get('timePolicyId')),createdAt=now(),completedAt=None,pausedAt=None,compliance='待核查',ruleResults=checks,subtasks=[],commands={},history=[dict(at=now(),actor=u['name'],action='提交',text='材料已提交，进入'+node['name'])],requestId=payload['requestId'])
    case.update(status='在办',projectId=project['id']);p['cases'].append(case);audit(p,u,'发起办件',case);features.task_events(s,u,case);return case


def can_handle(p,u,c):
    if not in_region(u,c):return False
    if is_admin(u) or c['assigneeId']==u['id']:return True
    day=datetime.now().date().isoformat()
    return any(d.get('enabled') and d['ownerId']==c['assigneeId'] and d['agentId']==u['id'] and d.get('validFrom','')<=day<=d.get('validUntil','') and (not d.get('modelId') or d['modelId']==c['modelId']) for d in p['delegations'])


def case_action(s,u,payload):
    p=s['platform'];c=find(p['cases'],payload.get('id'));require(c and (can_case(u,c) or can_handle(p,u,c)),'办件不存在或不可访问',404)
    key=text(payload.get('requestId',''),100);require(key,'操作标识必填');key=u['id']+':'+key
    if key in c['commands']:return deepcopy(c['commands'][key])
    revision(c,payload);command=payload.get('command');note=text(payload.get('note',''));require(note,'请填写办理说明')
    require(c['status'] in ['在办','已挂起'],'办件已结束，不能继续操作',409)
    manager=is_admin(u) or u['role']=='流程管理员';handler=can_handle(p,u,c)
    if command=='suspend':require(manager and c['status']=='在办','仅流程管理员可挂起在办事项',403);c.update(status='已挂起',pausedAt=now())
    elif command=='resume':
        require(manager and c['status']=='已挂起','不能恢复此事项',403)
        pause=datetime.now()-datetime.fromisoformat(c['pausedAt']);c['dueAt']=(datetime.fromisoformat(c['dueAt'])+pause).isoformat(timespec='seconds');c.update(status='在办',pausedAt=None)
    elif command=='void':require(manager,'作废需要流程管理权限',403);c.update(status='已作废',completedAt=now())
    elif command=='withdraw':require(c['userId']==u['id'] and c['nodeIndex']==0 and len(c['history'])==1,'已有办理动作，不能撤回');c.update(status='已撤回',completedAt=now())
    elif command=='assistComplete':
        sub=find(c['subtasks'],payload.get('subtaskId'));require(c['status']=='在办' and sub and sub['userId']==u['id'] and sub['status']=='待办','协办任务不可操作',403);sub.update(status='完成',note=note)
    else:
        require(c['status']=='在办' and handler,'当前节点没有办理权限或实例已挂起',403)
        if command=='complete':
            require(not any(t['status']=='待办' for t in c['subtasks']),'协办尚未完成')
            if c['nodeIndex']+1==len(c['workflow']['nodes']):c.update(status='已办结',completedAt=now())
            else:
                c['nodeIndex']+=1;node=c['workflow']['nodes'][c['nodeIndex']];c['assigneeId']=node['assigneeId'];c['dueAt']=deadline(p,node['hours'],c['workflow'].get('timePolicyId'))
        elif command=='return':
            target=payload.get('nodeIndex',c['nodeIndex']-1);require(isinstance(target,int) and 0<=target<c['nodeIndex'],'只能回退至已办理的前序节点')
            c['nodeIndex']=target;node=c['workflow']['nodes'][target];c['assigneeId']=node['assigneeId'];c['dueAt']=deadline(p,node['hours'],c['workflow'].get('timePolicyId'))
            for t in c['subtasks']:
                if t['status']=='待办':t['status']='已取消'
        elif command in ['delegate','assist']:
            target=find(s['users'],payload.get('userId'));require(target and target['enabled'] and target['id']!=c['assigneeId'] and in_region(target,c),'请选择不同且有区划权限的用户')
            if command=='delegate':c['assigneeId']=target['id']
            else:c['subtasks'].append(dict(id=ident('assist_'),userId=target['id'],status='待办',at=now(),nodeIndex=c['nodeIndex']))
        else:raise Invalid('不支持的实例操作')
    if c['status'] in ['已办结','已作废','已撤回']:
        for t in c['subtasks']:
            if t['status']=='待办':t['status']='已取消'
    c['rev']+=1;c['updated']=now();c['history'].append(dict(at=now(),actor=u['name'],userId=u['id'],action=command,text=note,nodeIndex=c['nodeIndex']))
    audit(p,u,'办件'+command,c)
    features.task_events(s,u,c,command)
    c['commands'][key]={'ok':True,'id':c['id'],'status':c['status'],'rev':c['rev']}
    return deepcopy(c['commands'][key])


def scene_runtime(s,u,payload):
    p=s['platform'];collection='sceneTemplates' if payload.get('template') else 'scenes';scene=find(p[collection],payload.get('id'));require(scene,'场景不存在',404)
    preview=bool(payload.get('preview'))
    if preview:require(manage(u,'scenes'),'无预览权限',403);selected=deepcopy(scene)
    else:
        app=next((a for a in p['apps'] if a.get('listed') and a.get('published',{}).get('type')=='scene' and a['published'].get('targetId')==scene['id'] and in_region(u,a['published'])),None)
        require(app,'场景未上架或当前不可访问',404);features.ensure_app(s,app['published'],strict=False);selected=deepcopy(app['published']['targetSnapshot'])
    require(selected['config']['engine']=='local-2d','三维引擎尚未接入，目前只支持参数配置与校验')
    config=selected['config'];layers=[]
    for layer in config['layers']:
        resource=cap.published(find(s['resources'],layer['resourceId']))
        if not resource or not cap.visible(u,resource):continue
        item=deepcopy(layer);item['access']='已授权' if cap.authorized(s,u,resource) else '需申请';item['features']=[]
        if item['access']=='已授权':
            for i,(lon,lat,region,name,area) in enumerate([(110.1,40.6,'包头市','示例监测单元 A',128.6),(111.7,40.8,'呼和浩特市','示例监测单元 B',96.4),(109.8,39.6,'鄂尔多斯市','示例监测单元 C',175)]):
                if u['region'] not in ['全区',region]:continue
                item['features'].append(dict(id=resource['id']+'_'+str(i),name=name,region=region,area=area,unit='公顷',coordinates=[[lon-.25,lat-.12],[lon+.3,lat-.1],[lon+.22,lat+.2],[lon-.18,lat+.16]],source='虚构示例图斑'))
        layers.append(item)
    config['layers']=layers
    disabled=[];usable=[]
    for b in config['widgets']:
        w=widget_version(p,b)
        if not w or not w.get('entry','').startswith('builtin:'):disabled.append(b['id'])
        else:usable.append({**b,'code':w['code'],'name':w['name']})
    config['widgets']=usable;selected['disabledWidgets']=disabled
    return selected


def validate_context(s,u,context):
    require(isinstance(context,dict),'业务上下文格式不正确');p=migrate(s)
    result={}
    if context.get('sceneId'):
        scene=scene_runtime(s,u,{'id':context['sceneId']});result.update(sceneId=scene['id'],sceneName=scene['name'],sceneVersion=scene['version'])
    if context.get('caseId'):
        case=find(p['cases'],context['caseId']);require(case and can_case(u,case),'不能引用此办件',403);result.update(caseId=case['id'],caseName=case['name'],caseVersion=case['rev'])
    region=context.get('region',u['region']);require(region in ['全区','呼和浩特市','包头市','鄂尔多斯市','赤峰市','呼伦贝尔市'] and within_scope(u,region),'上下文区域超出权限',403);result['region']=region
    result['period']=text(context.get('period','全部时间'),80)
    return result


def gateway_trial(s,u,payload):
    p=s['platform'];r=find(p['routes'],payload.get('id'));require(r and r.get('enabled'),'路由不可用',404)
    target=find(s['users'],payload.get('userId',u['id']))
    require(target and target['enabled'],'调用用户无效');require(target['id']==u['id'] or is_admin(u),'不能模拟其他用户',403)
    stamp=datetime.now();recent=[c for c in p['gatewayCalls'] if c['routeId']==r['id'] and c['userId']==target['id'] and (stamp-datetime.fromisoformat(c['at'])).total_seconds()<60]
    call=dict(id=ident('trace_'),routeId=r['id'],name=r['name'],userId=target['id'],at=now(),durationMs=0,statusCode=200,upstream='',result=[],error='')
    started=time.perf_counter()
    upstreams=[find(p['upstreams'],key) for key in r['upstreams']];healthy=[v for v in upstreams if v and v['enabled']]
    if r.get('requiredRole') not in ['全部',target['role']] and not is_admin(target):call.update(statusCode=403,error='调用角色不符合路由策略')
    elif len(recent)>=r['limit']:call.update(statusCode=429,error='超过每分钟调用限额')
    elif not healthy:call.update(statusCode=503,error='无可用上游实例')
    else:
        offset=len([x for x in p['gatewayCalls'] if x['routeId']==r['id'] and x['statusCode']==200])%len(healthy)
        call['attempts']=[]
        for upstream in healthy[offset:]+healthy[:offset]:
            call['upstream']=upstream['name'];call['scenarioLatencyMs']=upstream['latency']
            if upstream['latency']>r['timeout']:
                call['attempts'].append(dict(upstream=upstream['name'],statusCode=504));call.update(statusCode=504,error='示例上游延时超过超时策略');continue
            question=text(payload.get('question',''),100)
            call['result']=[dict(id=row['id'],name=row['name']) for raw in s['resources'] if (row:=cap.published(raw)) and cap.visible(target,row) and (not question or question in cap.semantic_text(s,row)[0])]
            call['attempts'].append(dict(upstream=upstream['name'],statusCode=200));call.update(statusCode=200,error='');break
    call['durationMs']=round((time.perf_counter()-started)*1000,3);call['mode']='本地进程内上游示例';p['gatewayCalls'].append(call);return call


def execute(s,u,action,payload):
    p=migrate(s)
    if action in ['platform.compliance','platform.supervise','platform.dashboard','platform.flowCheck']:
        return features.execute(s,u,action,payload)
    if action in ['platform.ingestEvent','platform.pull','platform.ack']:
        return message_bus.execute(s,u,action,payload)
    if action=='platform.save':return save_record(s,u,payload)
    if action=='platform.transition':return transition(s,u,payload)
    if action=='platform.sceneValidate':
        require(manage(u,'scenes'),'无配置权限',403);return scene_validate(s,{'config':payload.get('config')})
    if action=='platform.sceneRuntime':return scene_runtime(s,u,payload)
    if action=='platform.caseCreate':return create_case(s,u,payload)
    if action=='platform.caseAction':return case_action(s,u,payload)
    if action=='platform.caseDetail':
        c=find(p['cases'],payload.get('id'));require(c and (can_case(u,c) or can_handle(p,u,c)),'办件不可访问',404);return {**deepcopy(c),'canHandle':can_handle(p,u,c)}
    if action=='platform.appOpen':
        a=find(p['apps'],payload.get('id'));require(a and a.get('listed') and in_region(u,a['published']),'应用未上架或不可访问',404)
        features.ensure_app(s,a['published'],strict=False)
        a['views']=a.get('views',0)+1;p['recentApps']=[x for x in p['recentApps'] if not (x['appId']==a['id'] and x['userId']==u['id'])];p['recentApps'].append(dict(id=ident(),userId=u['id'],appId=a['id'],at=now()));audit(p,u,'访问应用',a)
        return {k:deepcopy(a['published'][k]) for k in ['id','name','type','targetId']}
    if action=='platform.flowExport':
        require(manage(u,'workflows'),'无流程管理权限',403);r=find(p['workflows'],payload.get('id'));require(r,'流程不存在',404)
        return dict(schemaVersion=1,workflow={k:deepcopy(r[k]) for k in FIELDS['workflows'].split() if k in r})
    if action=='platform.flowImport':
        data=payload.get('data',{});require(data.get('schemaVersion')==1,'不支持的流程格式版本');return save_record(s,u,dict(entity='workflows',values=data.get('workflow')))
    if action=='platform.ruleTrial':
        require(manage(u,'businessAssets'),'无业务配置权限',403);expression=payload.get('expression','');context=features.rule_context(p,payload.get('context',{}),expression);return dict(passed=safe_rule(expression,context),context=context)
    if action=='platform.document':
        c=find(p['cases'],payload.get('id'));require(c and can_case(u,c),'办件不可访问',404);r=find(p['businessAssets'],payload.get('templateId'));require(r and r['kind']=='模板管理','模板不存在')
        return dict(name=r['name'],body=re.sub(r'\{\{(\w+)\}\}',lambda m:str(c['formData'].get(m[1],'')),r['value']),version=r['rev'])
    if action=='platform.userSave':
        require(is_admin(u) or u['role'] in ['单位管理员','区划管理员'],'没有用户管理权限',403)
        old=find(s['users'],payload.get('id'));values=payload.get('values',{});require(isinstance(values,dict),'用户信息无效')
        if old:revision(old,payload);require(is_admin(u) or org_scope(p,u,old.get('orgId')),'不能管理其他单位用户',403)
        target=deepcopy(old) if old else dict(id=ident('user_'),rev=0,enabled=True,role='业务用户',internalAccess=False)
        for key in ['name','orgId','region','role','enabled']:
            if key in values:target[key]=values[key]
        if 'internalAccess' in values:
            require(is_admin(u) or values['internalAccess']==target.get('internalAccess',False),'仅平台管理员可修改内部工作空间准入',403)
            require(type(values['internalAccess']) is bool,'内部准入格式错误')
            target['internalAccess']=values['internalAccess']
        org=find(p['organizations'],target.get('orgId'));require(org and target.get('name'),'用户名称和所属组织必填')
        require(target.get('role') in ADMIN_ROLES|{'业务用户'},'角色无效')
        allowed_role=target['role']=='业务用户' or (target['orgId']!=u.get('orgId') and target['role']=='单位管理员') or (u['role']=='区划管理员' and target['orgId']!=u.get('orgId') and target['role']=='区划管理员')
        require(is_admin(u) or (org_scope(p,u,target['orgId']) and allowed_role and within_scope(u,target.get('region'))),'不能越级授权或扩大管理范围',403)
        if old and old['id']==u['id']:require(target.get('enabled') and target['role']==u['role'],'不能在当前会话停用自己或变更自身管理角色')
        target['department']=org['name'];target['rev']+=1
        if old:s['users'][s['users'].index(old)]=target
        else:s['users'].append(target)
        sync=record(ident('sync_'),target['name']+'权限同步',userId=target['id'],sourceVersion=target['rev'],targets=[c['id'] for c in p['authClients'] if c['enabled']],at=now());sync['status']='本地会话实时生效';p['identitySync'].append(sync)
        audit(p,u,'维护用户授权',target)
        p['audit'][-1]['changes']={key:{'before':old.get(key) if old else None,'after':target.get(key)} for key in ['role','orgId','region','enabled','internalAccess'] if not old or old.get(key)!=target.get(key)}
        emit(p,u,'identity.scope.changed',target,target['id']);return target
    if action=='platform.clientVerify':
        client=next((c for c in p['authClients'] if c.get('key')==payload.get('appKey')),None)
        require(client and client.get('enabled') and client.get('secretHash'),'客户端或凭据不可用',403)
        secret=text(payload.get('appSecret',''),200)
        require(hmac.compare_digest(client['secretHash'],hashlib.sha256(secret.encode()).hexdigest()),'AppKey/AppSecret 验证失败',403)
        require(client.get('protocol')=='本地演示会话','外部认证协议未接入')
        audit(p,u,'客户端凭据验证',client)
        return dict(ok=True,client=client['name'],entry=client['entry'],userId=u['id'],note='本地接入凭据已验证；不是第三方SSO令牌。')
    if action=='platform.rotateSecret':
        require(is_admin(u),'接入凭据需要平台管理权限',403)
        client=find(p['authClients'],payload.get('id'));require(client,'客户端不存在',404)
        secret=uuid.uuid4().hex+uuid.uuid4().hex
        client['secretHash']=hashlib.sha256(secret.encode()).hexdigest();client['rev']+=1
        audit(p,u,'轮换演示接入密钥',client)
        return dict(appKey=client['key'],appSecret=secret,note='仅此一次展示；服务端只保存摘要。仅用于本地接入示例。')
    if action=='platform.registration':
        kind=payload.get('kind');method=payload.get('method');require(kind in ['自然人','法人'],'请选择注册主体')
        allowed=['线上自主注册','线下窗口注册','第三方关联注册'] if kind=='自然人' else ['法定代表人激活','统一社会信用代码注册','线下窗口注册']
        require(method in allowed,'注册方式与主体不匹配')
        outcome=payload.get('outcome');require(outcome in ['通过','失败','待核验'],'请选择演示核验结果')
        r=record(ident('registration_'),text(payload.get('name',''),100),kind=kind,method=method,subjectCode=text(payload.get('subjectCode',''),80),createdBy=u['id'],at=now(),verification='已认证' if outcome=='通过' else '认证失败' if outcome=='失败' else '待核验')
        require(r['name'] and r['subjectCode'],'演示姓名/单位和虚构主体编码必填')
        existing=next((x for x in p['registrations'] if x['subjectCode']==r['subjectCode'] and x['kind']==kind),None)
        if existing:
            require(existing.get('createdBy')==u['id'] or is_admin(u),'主体编码已登记，请联系管理员',409)
            return existing
        if outcome=='通过':
            user=dict(id=ident('demo_registered_'),name=r['name'],role='业务用户',department='演示注册用户',orgId=u.get('orgId','org_hall'),region=u['region'],enabled=True,rev=1)
            s['users'].append(user);r['userId']=user['id']
        p['registrations'].append(r);audit(p,u,'演示实名注册',r)
        return r
    if action=='platform.login':
        target=find(s['users'],payload.get('userId'));client=find(p['authClients'],payload.get('clientId','client_portal'));require(target and client,'登录身份或客户端不存在')
        success=target['enabled'] and client['enabled'] and (not client.get('mfa') or payload.get('code')=='246810')
        log=dict(id=ident('login_'),userId=target['id'],name=target['name'],clientId=client['id'],at=now(),device=text(payload.get('device','浏览器演示'),200),ip='127.0.0.1',status='成功' if success else '失败',mode='演示身份验证')
        p['loginEvents'].append(log)
        import integration_admin
        return dict(ok=success,userId=target['id'] if success else None,error='' if success else '用户/客户端停用或演示验证码错误',client=client['name'],resultPermissions={**integration_admin.rights(s,target),'internalAccess':integration_admin.internal_access(s,target)} if success else {})
    if action=='platform.gatewayTrial':return gateway_trial(s,u,payload)
    if action=='platform.dispatch':require(is_admin(u),'无消息管理权限',403);dispatch(s);return {'ok':True}
    if action=='platform.retry':
        require(is_admin(u),'无消息管理权限',403);d=find(p['deliveries'],payload.get('id'));require(d and d['status'] in ['等待重试','失败队列'],'此投递不需要重试');d.update(status='待投递',nextRetryAt=now());dispatch(s);return d
    if action=='platform.notifyRead':
        n=find(p['notifications'],payload.get('id'));require(n and n['recipientId']==u['id'],'不能读取他人消息',403);n['read']=True;return n
    if action=='platform.testEvent':
        require(is_admin(u),'无事件管理权限',403);row=record(ident('demo_event_'),'消息总线投递演练',region='全区');emit(p,u,'app.test',row);return row
    raise Invalid('平台操作不存在',404)
