"""Reviewed scoped API keys; secrets are returned once and only hashes are persisted."""
import hashlib
import secrets
from copy import deepcopy
from datetime import date, timedelta
import portal_management as pm
from capabilities import require, published, authorized


def rows(s):return pm.migrate(s).setdefault('apiKeys',[])
def safe(r):return {k:deepcopy(v) for k,v in r.items() if k!='secretHash'}
def bootstrap(s,u,mode):return [safe(r) for r in rows(s) if (mode=='admin' and u['role']=='平台管理员') or r['userId']==u['id']]


def target(s,u,kind,key):
    if kind=='tool':return pm.tool(s,key,u=u)
    require(kind=='data','密钥用途类型无效')
    r=published(pm.find(s['resources'],key));require(r and r['type'] in ['数据库表','图层服务'] and authorized(s,u,r),'数据未授权或不可使用',403);return r


def execute(s,u,action,p):
    entries=rows(s)
    if action=='portal.keyApply':
        kind=p.get('kind');key=p.get('targetId');r=target(s,u,kind,key)
        purpose=pm.text(p.get('purpose',''),1000);require(purpose,'请填写申请用途')
        require(not any(k['userId']==u['id'] and k['kind']==kind and k['targetId']==key and k['status'] in ['待审核','已通过','已启用'] and k['validUntil']>=date.today().isoformat() for k in entries),'已有有效或待审核密钥申请')
        try:days=int(p.get('days',30))
        except (TypeError,ValueError):require(False,'有效天数格式错误')
        require(1<=days<=365,'有效天数为 1–365')
        out=dict(id=pm.ident(),userId=u['id'],userName=u['name'],kind=kind,targetId=key,name=r['name'],purpose=purpose,status='待审核',rev=1,createdAt=pm.now(),validUntil=(date.today()+timedelta(days=days)).isoformat(),history=[])
        entries.append(out);pm.event(s,u,'operation','申请 API 密钥',out['id'],out['name']);return safe(out)
    r=pm.find(entries,p.get('id'));require(r,'密钥申请不存在',404)
    require(r['rev']==p.get('rev'),'密钥已更新，请刷新',409)
    if action=='portal.keyActivate':
        require(r['userId']==u['id'],'不能领取他人的密钥',403)
        require(r['status']=='已通过' and not r.get('secretHash'),'密钥不可重复领取',409)
        require(r['validUntil']>=date.today().isoformat(),'密钥申请已过期')
        target(s,u,r['kind'],r['targetId'])
        secret='omp_'+secrets.token_urlsafe(32);r.update(secretHash=hashlib.sha256(secret.encode()).hexdigest(),status='已启用',rev=r['rev']+1)
        pm.event(s,u,'operation','领取 API 密钥',r['id'],r['name']);return dict(secret=secret,record=safe(r))
    pm.admin(u)
    if action=='portal.keyReview':
        require(r['status']=='待审核','申请已经处理',409)
        status=p.get('status');require(status in ['已通过','已驳回'],'审核状态无效')
        note=pm.text(p.get('note',''),1000);require(note,'审核意见必填')
        if status=='已通过':
            owner=pm.find(s['users'],r['userId']);require(owner and owner['enabled'],'申请用户已停用');target(s,owner,r['kind'],r['targetId'])
            require(r['validUntil']>=date.today().isoformat(),'申请已过期')
        r.update(status=status,rev=r['rev']+1);r['history'].append(dict(status=status,note=note,actor=u['name'],at=pm.now()))
    elif action=='portal.keyToggle':
        require(r['status'] in ['已启用','已停用'] and r.get('secretHash'),'密钥尚未领取')
        r.update(status='已停用' if r['status']=='已启用' else '已启用',rev=r['rev']+1)
    else:require(False,'密钥操作无效')
    pm.event(s,u,'operation','API 密钥'+r['status'],r['id'],r['name']);return safe(r)


def authenticate(s,bearer,kind,key):
    require(isinstance(bearer,str) and bearer.startswith('Bearer '),'请提供 Bearer API 密钥',401)
    digest=hashlib.sha256(bearer[7:].encode()).hexdigest()
    r=next((r for r in rows(s) if secrets.compare_digest(r.get('secretHash',''),digest)),None)
    require(r and r['status']=='已启用' and r['validUntil']>=date.today().isoformat(),'密钥无效、已停用或已过期',401)
    require(r['kind']==kind and r['targetId']==key,'密钥没有此服务的调用权限',403)
    u=pm.find(s['users'],r['userId']);require(u and u['enabled'],'密钥所属用户已停用',403)
    tool=target(s,u,kind,key)
    return u,r,tool


def invoke(tool,params):
    """Same local execution capabilities as the portal, behind a scoped API key."""
    import math
    import analysis_engine as engine
    require(isinstance(params,dict),'参数必须为对象')
    name=tool['engine']
    if name=='coordinate':
        try:x=float(params['x']);y=float(params['y'])
        except (ValueError,TypeError,KeyError):require(False,'坐标参数无效')
        require(math.isfinite(x) and math.isfinite(y),'坐标必须为有限数值')
        direction=params.get('direction','forward');require(direction in ['forward','inverse'],'转换方向无效')
        if direction=='forward':
            require(abs(x)<=180 and abs(y)<=85,'经纬度超出支持范围')
            return dict(x=6378137*math.radians(x),y=6378137*math.log(math.tan(math.pi/4+math.radians(y)/2)),crs='EPSG:3857')
        require(abs(x)<=20037508.35 and abs(y)<=19971868.89,'投影坐标超出支持范围')
        return dict(x=math.degrees(x/6378137),y=math.degrees(2*math.atan(math.exp(y/6378137))-math.pi/2),crs='EPSG:4326')
    if name=='buffer':
        try:x=float(params['x']);y=float(params['y']);distance=float(params['distance'])
        except (ValueError,TypeError,KeyError):require(False,'缓冲参数无效')
        require(all(math.isfinite(v) for v in [x,y,distance]) and abs(x)<=180 and abs(y)<=85 and 0<distance<=100000,'缓冲参数超出范围')
        lon,lat=math.radians(x),math.radians(y);angle=distance/6378137;ring=[]
        for i in range(65):
            bearing=2*math.pi*i/64
            destlat=math.asin(math.sin(lat)*math.cos(angle)+math.cos(lat)*math.sin(angle)*math.cos(bearing))
            destlon=lon+math.atan2(math.sin(bearing)*math.sin(angle)*math.cos(lat),math.cos(angle)-math.sin(lat)*math.sin(destlat))
            ring.append([math.degrees(destlon),math.degrees(destlat)])
        ring[-1]=ring[0]
        return dict(type='Feature',geometry=dict(type='Polygon',coordinates=[ring]),properties=dict(distance=distance,calculation='球面近似'))
    if name=='external':return dict(url=tool['url'],mode='外部入口')
    geometry=engine.normalize(params.get('geometry'),params.get('crs','EPSG:4326'))
    if name=='compliance':return engine.analyze(geometry,engine.catalog())
    return engine.spatial_tool(geometry,'area' if name=='area' else params.get('operation','intersection'),params.get('distance',0))
