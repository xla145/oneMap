"""Portal publishing, registration review and durable request audit for the local demo."""
import base64
import binascii
import json
import re
import sqlite3
import uuid
from collections import Counter
from copy import deepcopy
from datetime import datetime
from urllib.parse import urlparse
from capabilities import require, published, authorized, visible, knowledge_channel
from platform_seed import versioned


def now(): return datetime.now().isoformat(timespec='milliseconds')
def ident(): return uuid.uuid4().hex

def text(v, limit=1000):
    require(isinstance(v,str) and len(v)<=limit,'文本格式或长度不正确')
    return v.strip()

def admin(u): require(u['role']=='平台管理员','需要平台管理员身份',403)
def find(rows, key): return next((r for r in rows if r['id']==key),None)
def https(v):
    p=urlparse(v)
    require(not v or (p.scheme=='https' and p.hostname and not p.username and not p.password and not any(c.isspace() for c in v)),'服务地址必须为不含账号密码的 HTTPS 地址')
    return v

TOOLS=[
 ('coordinate','坐标转换','基础空间工具','map','WGS84 经纬度与 Web Mercator 之间的投影转换。'),
 ('area','面积量算','基础空间工具','layers','输入或绘制多边形，计算球面近似面积。'),
 ('buffer','点缓冲区分析','基础空间工具','tool','输入经纬度和距离，生成球面近似缓冲范围。'),
 ('overlay','叠加分析','空间分析','layers','多地块相交、差集、融合、面积量算与面缓冲。'),
 ('compliance','项目选址与合规性审查','业务分析','shield','上传或绘制地块，以示例管控数据核查并导出报告。')]
ENGINES={r[0] for r in TOOLS}|{'external','spatial-check','spatial-query','spatial-store','spatial-edit'}


def migrate(s):
    p=s.setdefault('portalManagement',{})
    if 'tools' not in p:
        p['tools']=[versioned(i,n,category=c,icon=icon,description=d,engine=i,url='',order=k+1) for k,(i,n,c,icon,d) in enumerate(TOOLS)]
    for key in ['materials','registrations','events']:p.setdefault(key,[])
    return p


def live(r):
    return published(r) if r and not r.get("suspended") else None


def public_row(r):
    r=deepcopy(r)
    for x in [r,r.get('published',{}),*r.get('versions',[])]:
        x.pop('fileData',None)
    return r


def can_material(s,u,r):
    content=knowledge_channel(find(s["knowledge"],r.get("contentId")),"portal") if r.get("contentId") else None
    return not r.get("contentId") or bool(content and visible(u,content))

def bootstrap(s,u,mode):
    p=migrate(s); full=mode=='admin' and u['role']=='平台管理员'
    result={e:[public_row(r) for row in p[e] if (r:=deepcopy(row) if full else live(row)) and (full or (can_tool(u,r,s) if e=='tools' else can_material(s,u,r)))] for e in ['tools','materials']}
    from tool_center import enrich
    if not full:result['tools']=[enrich(s,r) for r in result['tools']]
    if full:result['toolPermissions']=deepcopy(p.get('toolPermissions',[]));result['toolPermissionsRev']=p.get('toolPermissionsRev',1)
    result['registrations']=[deepcopy(r) for r in p['registrations'] if full or r['createdBy']==u['id']]
    import portal_keys
    result['apiKeys']=portal_keys.bootstrap(s,u,mode)
    result['activeAlerts']=sum(not r.get('resolvedAt') for r in p.get('alerts',[])) if full else 0
    return result


def event(s,u,kind,action,target='',name='',**extra):
    row=dict(id=ident(),at=now(),kind=kind,action=action,targetId=target,name=name,userId=u['id'],actor=u['name'],department=u['department'],**extra)
    migrate(s)['events'].append(row)
    return row


def portal_role(u):
    return "管理员" if u["role"]=="平台管理员" else u.get("portalRole","普通用户")

def can_tool(u,r,s=None):
    if u['role']=='平台管理员':return True
    if r.get('audience','全部用户') not in ['全部用户',portal_role(u)]:return False
    from tool_center import MODULES
    return not any(rule['role']==portal_role(u) and rule['category'] in ['*',r.get('category')] and rule['module'] in ['*',r.get('module') or MODULES.get(r['engine'],'外部服务')] for rule in (s or {}).get('portalManagement',{}).get('toolPermissions',[]))

def tool(s,key,engine=None,u=None):
    r=live(find(migrate(s)['tools'],key))
    require(r,'工具已下架或尚未发布',403)
    require(u is None or can_tool(u,r,s),'当前用户没有工具使用权限',403)
    if r.get('resourceId'):
        resource=published(find(s['resources'],r['resourceId']))
        require(resource and resource['type']=='工具服务' and (u is None or authorized(s,u,resource)),'关联工具资源已停用或当前用户未获授权',403)
    require(engine is None or r['engine']==engine,'工具与执行能力不匹配',403)
    return r


def execute(s,u,action,p):
    require(isinstance(p,dict),'参数格式错误');m=migrate(s)
    if action=='portal.visit':
        route=text(p.get('route',''),200)
        require(re.fullmatch(r'/front/[A-Za-z0-9_/-]+',route),'访问路径无效')
        event(s,u,'visit','浏览页面',route,route)
        return {'ok':True}
    if action=='portal.toolCheck':
        r=tool(s,p.get('id'),u=u);return public_row(r)
    if action=='portal.toolRun':
        import centers
        from shapely.errors import GEOSException
        from pyproj.exceptions import ProjError
        r=tool(s,p.get('id'),u=u);payload=p.get('payload',{})
        require(isinstance(payload,dict) and len(json.dumps(payload))<=200000,'请求 JSON 不能超过200KB')
        require(r['engine']!='external','外部工具请使用登记入口')
        if r['engine'] in ['spatial-store','spatial-edit']:admin(u)
        if r['engine'] in ['spatial-store','spatial-edit','spatial-query']:
            resource=published(find(s['resources'],payload.get('resourceId')))
            require(resource and authorized(s,u,resource),'目标图层未授权或已下架',403)
        start=datetime.now()
        try:output=centers.run_tool(s,r,payload)
        except (ValueError,TypeError,KeyError,GEOSException,ProjError) as error:
            require(False,'空间请求无效：'+str(error)[:200])
        event(s,u,'tool','在线接口测试',r['id'],r['name'],status='成功',durationMs=round((datetime.now()-start).total_seconds()*1000,2))
        return output
    if action=='portal.toolResult':
        r=tool(s,p.get('id'),u=u);status=p.get('status')
        require(status in ['成功','失败','打开入口'],'调用结果无效')
        duration=p.get('durationMs',0);require(type(duration) in [int,float] and 0<=duration<=3600000,'耗时无效')
        event(s,u,'tool','浏览器工具调用',r['id'],r['name'],status=status,durationMs=round(duration,2),error=text(p.get('error',''),300))
        return {'ok':True}
    if action=='portal.resourceAccess':
        r=published(find(s['resources'],p.get('id')))
        require(r and authorized(s,u,r),'资源未授权、已过期或已下架',403)
        kind=p.get('kind');require(kind in ['serviceUrl','downloadUrl'],'入口类型无效')
        url=r.get(kind,'');require(url,'尚未绑定外部服务入口');https(url)
        event(s,u,'download' if kind=='downloadUrl' else 'operation','打开数据入口',r['id'],r['name'])
        return {'url':url}
    if action=='portal.newsDownload':
        r=knowledge_channel(find(s['knowledge'],p.get('id')),'portal');require(r and visible(u,r),'资讯已下架或不可访问',404)
        event(s,u,'download','下载资讯正文',r['id'],r['name'],version=r['version'])
        return deepcopy(r)
    if action=='portal.materialDownload':
        r=live(find(m['materials'],p.get('id')));require(r and can_material(s,u,r),'资料已下架、未发布或不可访问',404)
        event(s,u,'download','下载资料',r['id'],r['name'],version=r['version'])
        return dict(filename=r['filename'],content=r['fileData'],encoding='base64',mime='application/octet-stream')
    if action=='portal.register':
        key=text(p.get('requestId',''),100);require(key,'缺少提交标识')
        old=next((r for r in m['registrations'] if r['createdBy']==u['id'] and r['requestId']==key),None)
        if old:return deepcopy(old)
        name=text(p.get('name',''),100);department=text(p.get('department',''),100);contact=text(p.get('contact',''),100);reason=text(p.get('reason',''),1000)
        require(name and department and contact and reason,'请填写姓名、单位、联系方式和申请用途')
        require(not any(r['contact']==contact and r['status'] in ['待审核','已通过'] for r in m['registrations']),'该联系方式已有待审或已通过申请')
        row=dict(id=ident(),name=name,department=department,contact=contact,reason=reason,requestId=key,createdBy=u['id'],status='待审核',rev=1,createdAt=now(),history=[])
        m['registrations'].append(row);event(s,u,'operation','提交注册申请',row['id'],name);return deepcopy(row)
    if action.startswith('portal.key'):
        import portal_keys
        return portal_keys.execute(s,u,action,p)
    admin(u)
    if action=='portal.toolPermissions':
        from tool_center import MODULES
        require(p.get('rev')==m.get('toolPermissionsRev',1),'权限配置已更新，请刷新',409)
        rows=p.get('rules');require(isinstance(rows,list) and len(rows)<=100,'权限规则最多100条')
        result=[]
        for rule in rows:
            require(isinstance(rule,dict),'权限规则格式错误')
            role=rule.get('role');category=text(rule.get('category','*'),300);module=rule.get('module','*')
            require(role in ['普通用户','企业用户'] and category and module in ['*',*MODULES.values()],'权限规则无效')
            result.append(dict(role=role,category=category,module=module))
        m['toolPermissions']=result;m['toolPermissionsRev']=m.get('toolPermissionsRev',1)+1
        event(s,u,'operation','更新工具类型与功能模块权限');return {'ok':True}
    if action=='portal.userRole':
        r=find(s['users'],p.get('id'));require(r,'用户不存在',404)
        require(r.get('rev',1)==p.get('rev'),'用户已更新，请刷新',409)
        role=p.get('role');require(role in ['普通用户','企业用户','管理员'],'门户角色无效')
        require(r['id']!=u['id'] or role=='管理员','不能在当前会话取消自己的管理权限')
        require(r['role'] in ['业务用户','平台管理员'],'内部专用角色请在组织权限页面维护')
        r.update(portalRole=role,role='平台管理员' if role=='管理员' else '业务用户',rev=r.get('rev',1)+1)
        event(s,u,'operation','分配门户角色',r['id'],r['name']+'：'+role);return deepcopy(r)
    if action=='portal.review':
        r=find(m['registrations'],p.get('id'));require(r,'申请不存在',404)
        require(r['rev']==p.get('rev') and r['status']=='待审核','申请已处理，请刷新',409)
        status=p.get('status');require(status in ['已通过','已驳回'],'审核状态无效')
        note=text(p.get('note',''),1000);require(note,'请填写审核意见')
        if status=='已通过':
            org=find(s['platform']['organizations'],p.get('orgId'));require(org,'请选择所属组织')
            region=text(p.get('region','全区'),100)
            from seed import REGIONS
            require(region in REGIONS,'区域无效')
            portalRole=p.get('portalRole','普通用户');require(portalRole in ['普通用户','企业用户'],'注册用户类型无效')
            user=dict(portalRole=portalRole,id='portal_'+ident(),name=r['name'],department=org['name'],orgId=org['id'],region=region,role='业务用户',enabled=True,rev=1)
            s['users'].append(user);r['userId']=user['id']
        r.update(status=status,rev=r['rev']+1,reviewedAt=now())
        r['history'].append(dict(at=now(),actor=u['name'],status=status,note=note))
        event(s,u,'operation','注册'+status,r['id'],r['name']);return deepcopy(r)
    if action in ['portal.save','portal.publish','portal.disable','portal.delete']:
        entity=p.get('entity');require(entity in ['tools','materials'],'管理类型无效')
        old=find(m[entity],p.get('id'))
        if p.get('id'):require(old,'记录不存在',404)
        if old:require(old['rev']==p.get('rev'),'内容已更新，请刷新后重试',409)
        if action=='portal.delete':
            require(old,'记录不存在',404)
            require(old['status']=='已停用' or not old.get('published'),'请先下架再删除')
            m[entity].remove(old);event(s,u,'operation','删除内容',old['id'],old['name']);return {'ok':True}
        if action=='portal.save':
            v=p.get('values');require(isinstance(v,dict),'内容格式无效')
            r=deepcopy(old) if old else dict(id=ident(),rev=0,version=0,status='草稿',versions=[])
            for key in ['name','category','description','source','engine','url','audience','contentId','resourceId','provider','publisher','apiDescription','inputExample','outputDescription','requestParameters','outputExample','directoryId','region','interfaceType','module','usageMode']:
                if key in v:r[key]=text(v[key],2000 if key in ['description','apiDescription','inputExample','outputDescription','requestParameters','outputExample'] else 300)
            require(r.get('name') and r.get('category'),'名称和分类必填')
            try:r['order']=int(v.get('order',r.get('order',1)))
            except (TypeError,ValueError):require(False,'排序必须为整数')
            require(0<=r['order']<=9999,'排序范围为 0–9999')
            if entity=='tools':
                from tool_center import MODULES
                for key,kind in [('requestParameters',list),('inputExample',dict),('outputExample',dict)]:
                    if r.get(key):
                        try:value=json.loads(r[key])
                        except (ValueError,TypeError):require(False,'参数定义与请求 / 返回示例需为有效 JSON')
                        require(isinstance(value,kind),'参数定义应为数组；请求和返回示例应为 JSON 对象')
                        if key=='requestParameters':require(len(value)<=30 and all(isinstance(x,dict) and all(isinstance(x.get(k),str) for k in ['name','type','required','description']) for x in value),'每个参数需包含 name、type、required、description 四个文本字段，最多30项')
                r.setdefault('module',MODULES.get(r.get('engine'),'外部服务'))
                require(r['module'] in MODULES.values(),'功能模块无效')
                require(r.get('usageMode','直接使用') in ['直接使用','申请授权'],'使用方式无效')
                require(r.get('usageMode')!='申请授权' or r.get('resourceId'),'申请授权工具必须关联资源中心的工具资源')
                if r.get('directoryId'):
                    directory=find(s.get('centers',{}).get('directories',[]),r['directoryId'])
                    require(directory and directory['kind'] in ['公共目录','工具服务'],'请选择工具共享目录')
                if 'screenshot' in v:
                    value=v['screenshot'];require(isinstance(value,str) and len(value)<2800000,'截图不能超过2MB')
                    if value:
                        match=re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)',value);require(match,'截图支持 PNG、JPEG、WebP')
                        try:raw=base64.b64decode(match[2],validate=True)
                        except (ValueError,binascii.Error):require(False,'截图编码无效')
                        valid=(match[1]=='png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (match[1]=='jpeg' and raw.startswith(b'\xff\xd8\xff')) or (match[1]=='webp' and raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')
                        require(valid and len(raw)<=2*1024*1024,'截图格式或大小无效')
                    r['screenshot']=value
                require(r.get('engine') in ENGINES,'请选择执行能力')
                if old and old['id'] in ENGINES:require(r['engine']==old['id'],'内置工具的执行能力不能变更')
                require(r.get('audience','全部用户') in ['全部用户','普通用户','企业用户','管理员'],'工具访问范围无效')
                r['url']=https(r.get('url',''));require(r['engine']!='external' or r['url'],'外部工具必须填写入口地址')
                if r.get('resourceId'):
                    resource=find(s['resources'],r['resourceId'])
                    require(resource and resource['type']=='工具服务','请选择工具服务类型的资源')
                    require(not any(x['id']!=r['id'] and (x.get('resourceId')==r['resourceId'] or (x.get('published') or {}).get('resourceId')==r['resourceId']) for x in m['tools']),'该工具资源已有能力登记，请编辑已有记录')
                if r['engine'] in ['spatial-store','spatial-edit']:require(r.get('audience')=='管理员','写入类工具只能配置为管理员使用')
                r.update(reviewState='未提交',approvedHash='')
                r['icon']='tool'
            else:
                require(not r.get('contentId') or find(s['knowledge'],r['contentId']),'关联资讯不存在')
                if 'fileData' in v:
                    encoded=v['fileData'];require(isinstance(encoded,str) and len(encoded)<=7*1024*1024,'附件不能超过 5 MB')
                    try:raw=base64.b64decode(encoded,validate=True)
                    except (ValueError,binascii.Error):require(False,'附件编码无效')
                    require(0<len(raw)<=5*1024*1024,'附件不能为空或超过 5 MB')
                    filename=text(v.get('filename',''),180)
                    require(re.fullmatch(r'[^/\\\x00-\x1f]+\.(pdf|docx?|xlsx?|pptx?|mp4|zip|csv|txt|geojson)',filename,re.I),'支持 PDF、Word、Excel、PPT、MP4、ZIP、CSV、TXT、GeoJSON 文件')
                    r.update(filename=filename,fileData=encoded,size=len(raw))
                require(r.get('fileData'),'请上传资料附件')
            r.update(rev=r['rev']+1,updated=now(),status='草稿')
            if entity=='tools':
                for review in s.get('centers',{}).get('toolReviews',[]):
                    if review['toolId']==r['id'] and review['status']=='待审核':review.update(status='配置变更已撤回',note='配置发生修改，需重新提交审核')
            if old:m[entity][m[entity].index(old)]=r
            else:m[entity].append(r)
        else:
            require(old,'记录不存在',404);r=old
            if action=='portal.publish':
                if entity=='tools':
                    from centers import tool_signature
                    require(r.get('reviewState')=='已通过' and r.get('approvedHash')==tool_signature(r),'请先完成工具上架审核，修改配置后需重新审核')
                if entity=='tools' and r.get('resourceId'):
                    resource=published(find(s['resources'],r['resourceId']))
                    require(resource and resource['type']=='工具服务','关联工具资源尚未发布或已停用')
                if r.get('published'):r.setdefault('versions',[]).append(deepcopy(r['published']))
                r.update(version=r['version']+1,status='已发布',suspended=False,updated=now())
                if entity=='tools':r['publishedAt']=now()
                r['published']={k:deepcopy(v) for k,v in r.items() if k not in ['published','versions']}
            else:r.update(status='已停用',suspended=True)
            r.update(rev=r['rev']+1,updated=now())
        event(s,u,'operation',{'portal.save':'保存草稿','portal.publish':'发布','portal.disable':'下架'}[action],r['id'],r['name'])
        return public_row(r)
    require(False,'未知门户管理操作',404)


def initialize(db):
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE IF NOT EXISTS portal_requests(id TEXT PRIMARY KEY, at TEXT NOT NULL, user_id TEXT, actor TEXT, method TEXT, path TEXT, action TEXT, target TEXT, status INTEGER, duration REAL, ip TEXT, error TEXT)')
        c.execute('CREATE INDEX IF NOT EXISTS portal_requests_at ON portal_requests(at)')


def record_request(db, row):
    with sqlite3.connect(db,timeout=10) as c:
        c.execute('INSERT INTO portal_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',row)


def report(db,s,u,p):
    admin(u);require(isinstance(p,dict),'查询参数无效')
    start=text(p.get('start',''),10);end=text(p.get('end',''),10);query=text(p.get('q',''),100).lower();kind=p.get('kind','all')
    require(kind in ['all','operation','visit','api','tool','download'],'日志类型无效')
    for d in [start,end]:
        if d:
            try:datetime.strptime(d,'%Y-%m-%d')
            except ValueError:require(False,'日期格式无效')
    require(not start or not end or start<=end,'开始日期不能晚于结束日期')
    events=deepcopy(migrate(s)['events'])
    # Existing audit streams remain accessible in one view.
    for row in s.get('audit',[])+s['platform'].get('audit',[])+s['platform'].get('loginEvents',[]):
        events.append(dict(row,kind='operation',actor=row.get('actor',row.get('name','')),action=row.get('action','登录'),status=row.get('status','完成')))
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        sql='SELECT * FROM portal_requests WHERE 1=1';args=[]
        if start:sql+=' AND at>=?';args.append(start)
        if end:sql+=' AND at<?';args.append(end+'T99')
        for row in c.execute(sql,args):
            row=dict(row)
            events.append(dict(id=row['id'],at=row['at'],kind='api',actor=row['actor'],userId=row['user_id'],action=row['action'] or row['method']+' '+row['path'],name=row['target'],status=str(row['status']),durationMs=row['duration'],ip=row['ip'],error=row['error'],path=row['path']))
    events=list({r['id']:r for r in events}.values())
    events=[r for r in events if (not start or r['at'][:10]>=start) and (not end or r['at'][:10]<=end)]
    visits=[r for r in events if r['kind']=='visit']
    tool_calls=[r for r in events if r['kind']=='tool' or (r['kind']=='api' and r['action'] in ['analysis.spatial','analysis.create','tools.invoke'])]
    tool_stats=[]
    for t in migrate(s)['tools']:
        rows=[r for r in tool_calls if r.get('targetId',r.get('name'))==t['id']]
        success=sum(r.get('status') in ['成功','200'] for r in rows)
        tool_stats.append(dict(id=t['id'],name=t['name'],total=len(rows),success=success,failed=sum(r.get('status')=='失败' or str(r.get('status','')).startswith(('4','5')) for r in rows),averageMs=round(sum(r.get('durationMs',0) for r in rows)/len(rows),2) if rows else 0))
    page_names={'home':'门户首页','data':'数据服务','capabilities':'能力服务','services':'办事服务','knowledge':'资讯下载','landscape':'大美内蒙古','register':'账号申请','api-keys':'API 密钥','assistant':'智能助手','profile':'个人中心','applications':'数据申请','requests':'咨询与意见','map':'地图浏览','app-center':'应用中心','internal-home':'内部工作台','messages':'消息中心'}
    def page_name(r):
        parts=r.get('name','').split('/');return page_names.get(parts[2] if len(parts)>2 else '', '其他页面')
    stats=dict(pv=len(visits),uv=len({r['userId'] for r in visits}),downloads=sum(r['kind']=='download' or (r['kind']=='api' and r['action'] in ['public.download','data.query'] and r['status']=='200') for r in events),toolCalls=len(tool_calls),users=[dict(name=k,count=v) for k,v in Counter(r['actor'] for r in visits).most_common()],pages=[dict(name=k,count=v) for k,v in Counter(page_name(r) for r in visits).most_common()],days=[dict(name=k,count=v) for k,v in sorted(Counter(r['at'][:10] for r in visits).items())],tools=tool_stats)
    applications=[a for a in s.get('applications',[]) if (not start or a.get('at','')[:10]>=start) and (not end or a.get('at','')[:10]<=end)]
    items=[i for a in applications for i in a.get('items',[])]
    reviewed=[i for i in items if i.get('status') in ['已通过','已驳回']]
    stats.update(resources=sum(r.get('type') in ['数据库表','图层服务'] for r in s['resources']),dataCalls=sum(r['kind']=='api' and r['action'] in ['public.download','public.map','portal.resourceAccess','data.query'] for r in events),applications=len(applications),reviewed=len(reviewed),approvalRate=round(sum(i['status']=='已通过' for i in reviewed)/len(reviewed)*100,1) if reviewed else None)
    hits=Counter()
    for r in events:
        if r['kind']=='visit' and r.get('name','').startswith('/front/data/'):hits[r['name'].split('/')[-1]]+=1
        elif r['kind']=='api' and r['action'] in ['public.download','data.query'] and r['status']=='200':hits[r['name']]+=1
    stats['popular']=[dict(id=k,name=(find(s['resources'],k) or {}).get('name',k),count=v) for k,v in hits.most_common(20)]
    stats['keyCalls']=dict(Counter(r.get('targetId') for r in events if r['kind']=='operation' and r['action']=='密钥调用'))
    rows=sorted([r for r in events if (kind=='all' or r['kind']==kind) and (not query or query in json.dumps(r,ensure_ascii=False).lower())],key=lambda r:r['at'],reverse=True)
    try:page=max(1,int(p.get('page',1)));size= min(5000,max(1,int(p.get('size',25))))
    except (ValueError,TypeError):require(False,'分页参数无效')
    return dict(rows=rows[(page-1)*size:page*size],total=len(rows),page=page,stats=stats)
