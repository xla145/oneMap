"""Bounded spatial tools for the existing fictional scene; no external GIS calls."""
from copy import deepcopy
import math
import re
from datetime import datetime
import capabilities as cap
import platform_domain as platform
from platform_seed import migrate as migrate_platform

EPS = 1e-9


def migrate(s):
    migrate_platform(s)
    for agent in s['agents']:
        for row in [agent] + ([agent['published']] if agent.get('published') else []):
            row.setdefault('mapEnabled', agent['id'] in ['a1', 'a3', 'a_team'])
            row.setdefault('mapSceneId', 'scene_cropland')
            row.setdefault('mapResourceIds', 'r_scene_demo,r11' if row['mapEnabled'] else '')


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on_segment(p, a, b):
    return abs(cross(a,b,p)) <= EPS and min(a[0],b[0])-EPS <= p[0] <= max(a[0],b[0])+EPS and min(a[1],b[1])-EPS <= p[1] <= max(a[1],b[1])+EPS


def segments(a,b,c,d,strict=False):
    x,y,z,w=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    if ((x>EPS and y<-EPS) or (x<-EPS and y>EPS)) and ((z>EPS and w<-EPS) or (z<-EPS and w>EPS)):
        return True
    return not strict and any([on_segment(c,a,b),on_segment(d,a,b),on_segment(a,c,d),on_segment(b,c,d)])


def inside(p, ring):
    hit=False
    for a,b in zip(ring,ring[1:]):
        if on_segment(p,a,b):return True
        if (a[1]>p[1]) != (b[1]>p[1]) and p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:hit=not hit
    return hit


def intersects(a,b):
    return inside(a[0],b) or inside(b[0],a) or any(segments(p,q,r,t) for p,q in zip(a,a[1:]) for r,t in zip(b,b[1:]))


def contained(feature, selection):
    return all(inside(p,selection) for p in feature) and all(inside([(a[0]+b[0])/2,(a[1]+b[1])/2],selection) for a,b in zip(feature,feature[1:])) and not any(segments(a,b,c,d,True) for a,b in zip(feature,feature[1:]) for c,d in zip(selection,selection[1:]))


def valid_ring(geometry):
    cap.require(isinstance(geometry,dict) and geometry.get('type')=='Polygon','仅支持多边形范围')
    rings=geometry.get('coordinates')
    cap.require(isinstance(rings,list) and len(rings)==1,'选区暂不支持孔洞或多部件')
    ring=rings[0]
    cap.require(isinstance(ring,list) and 4<=len(ring)<=101,'选区需有3至100个顶点并闭合')
    cap.require(all(isinstance(p,list) and len(p)==2 and all(type(v) in [int,float] and math.isfinite(v) for v in p) and -180<=p[0]<=180 and -90<=p[1]<=90 for p in ring),'选区坐标无效')
    cap.require(ring[0]==ring[-1] and len({tuple(p) for p in ring[:-1]})==len(ring)-1,'选区必须闭合且顶点不能重复')
    edges=list(zip(ring,ring[1:]))
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges):
            if j<=i+1 or (i==0 and j==len(edges)-1):continue
            cap.require(not segments(a,b,c,d),'选区存在自相交，请重新绘制')
    cap.require(abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in edges))>EPS,'选区面积必须大于零')
    return deepcopy(ring)


def runtime(s,u,agent_id,scene_id=None):
    migrate(s)
    agent=cap.published(cap.find(s['agents'],agent_id))
    cap.require(agent and cap.visible(u,agent) and agent.get('mapEnabled'),'当前智能体未启用地图能力',403)
    scene_id=scene_id or agent['mapSceneId']
    cap.require(scene_id==agent['mapSceneId'],'场景不在智能体发布配置内',403)
    scene=platform.scene_runtime(s,u,dict(id=scene_id))
    allowed=set(cap.ids(agent.get('mapResourceIds')))
    scene['config']['layers']=[l for l in scene['config']['layers'] if l['resourceId'] in allowed]
    for layer in scene['config']['layers']:
        resource=cap.published(cap.find(s['resources'],layer['resourceId']))
        layer['features']=[{**f,'resourceId':resource['id'],'layerId':layer['id'],'period':'2026年','version':resource['version']} for f in layer['features'] if resource.get('region','全区') in ['全区',f['region']]]
    scene['config']['widgets']=[{'code':'query'},{'code':'measure'}]
    scene['periods']=['2026年']
    return scene


def analyze(s,u,agent,raw,ctx,question):
    cap.require(isinstance(raw,dict),'地图查询条件格式不正确')
    cap.require(raw.get('crs','EPSG:4490')=='EPSG:4490','地图查询仅支持 EPSG:4490')
    region=ctx['region']
    cap.require(platform.within_scope(u,region),'地图查询区域超出权限',403)
    mode=raw.get('mode','region');cap.require(mode in ['region','features','polygon'],'地图范围类型无效')
    cap.require(mode=='region' or raw.get('region',region)==region,'问题区域与当前选区不同，请清除选区后重试',409)
    scene=runtime(s,u,agent['id'],raw.get('sceneId'))
    available={l['id']:l for l in scene['config']['layers']}
    ids=raw.get('layerIds',list(available))
    cap.require(isinstance(ids,list) and len(ids)<=30 and all(isinstance(i,str) and i in available for i in ids),'图层不可访问',403)
    cap.require(len(ids)==len(set(ids)),'图层不能重复')
    chosen=[available[i] for i in ids]
    authorized=[l for l in chosen if l['access']=='已授权']
    topic=next((t for t in ['地灾','矿产','生态','耕地','农田'] if t in question),None)
    if topic:
        terms={'地灾':['地灾','地质灾害'],'矿产':['矿产','矿业','矿权'],'生态':['生态','修复'],'耕地':['耕地','农田'],'农田':['耕地','农田']}[topic]
        authorized=[l for l in authorized if any(t in str(cap.published(cap.find(s['resources'],l['resourceId']))) for t in terms)]
    records=[deepcopy(f) for l in authorized for f in l['features'] if region=='全区' or f['region']==region]
    context=dict(mode=mode,region=region,period=ctx['period'],sceneId=scene['id'],layerIds=ids,crs='EPSG:4490')
    ring=None
    if mode=='polygon':
        ring=valid_ring(raw.get('geometry'));context['geometry']={'type':'Polygon','coordinates':[ring]}
    if mode=='features':
        refs=raw.get('featureRefs',[])
        cap.require(isinstance(refs,list) and 1<=len(refs)<=100 and all(isinstance(r,dict) and isinstance(r.get('layerId'),str) and isinstance(r.get('id'),str) for r in refs),'请选择有效图斑')
        keys={(f['layerId'],f['id']) for f in records}
        selected={(r['layerId'],r['id']) for r in refs}
        cap.require(selected<=keys,'所选图斑不可访问或不在当前区域',403)
        context['featureRefs']=[dict(layerId=a,id=b) for a,b in sorted(selected)]
        records=[f for f in records if (f['layerId'],f['id']) in selected]
    if ring:
        hits=[]
        for f in records:
            feature=f['coordinates']+[f['coordinates'][0]]
            if intersects(feature,ring):f['fullyContained']=contained(feature,ring);hits.append(f)
        records=hits
    else:
        for f in records:f['fullyContained']=True
    period=ctx['period']
    temporal=period not in ['全部时间','2026年']
    if temporal:records=[]
    unsupported=bool(re.search(r'缓冲|叠加面积|交叠面积|预测|变化率|风险预测',question))
    if unsupported:records=[]
    full=[f for f in records if f['fullyContained']]
    show_area=any(w in question for w in ['面积','统计','汇总','分析','多少'])
    stats=dict(count=len(records),fullCount=len(full),partialCount=len(records)-len(full),attributeArea=round(sum(f['area'] for f in full),2) if show_area and (full or not records) else None,unit='公顷')
    status='unsupported' if unsupported else 'no_data' if temporal else 'ok' if records else 'empty'
    note='完整图斑面积为演示属性值汇总；部分相交图斑仅计数，不计算交叠面积。'
    if unsupported:summary='当前工具尚不支持该空间分析，请使用图斑查询或属性面积统计。'
    elif temporal:summary='该地图示例仅提供2026年数据，当前时间条件下没有可用数据。'
    else:summary=f"当前范围找到 {len(records)} 个已授权示例图斑。"+(f"完整图斑属性面积合计 {stats['attributeArea']} 公顷。" if show_area and stats['attributeArea'] is not None else '全部为部分相交图斑，未计算交叠面积。' if show_area and records else '')
    if any(l['access']!='已授权' for l in chosen):summary+=' 部分图层未授权，未参与本次查询。'
    versions=[dict(resourceId=l['resourceId'],version=cap.published(cap.find(s['resources'],l['resourceId']))['version']) for l in authorized]
    return dict(status=status,summary=summary,context=context,features=records,statistics=None if temporal or unsupported else stats,caliber=note,sourceVersions=versions,sceneVersion=scene['version'],agentId=agent['id'],at=datetime.now().isoformat(timespec='seconds'),partial=any(l['access']!='已授权' for l in chosen))


def sanitize_sessions(s,u,sessions):
    """Historical snapshots never bypass current resource or agent permissions."""
    scene_permissions={}
    for sess in sessions:
        agent=cap.published(cap.find(s['agents'],sess['agentId']))
        for msg in sess.get('messages',[]):
            result=msg.get('analysisResult')
            if not result:continue
            allowed=bool(agent and cap.visible(u,agent) and agent.get('mapEnabled'))
            if allowed:
                key=(agent['id'],result.get('context',{}).get('sceneId'))
                if key not in scene_permissions:
                    try:runtime(s,u,*key);scene_permissions[key]=True
                    except cap.Invalid:scene_permissions[key]=False
                allowed=scene_permissions[key]
            for ref in result.get('sourceVersions',[]):
                resource=cap.published(cap.find(s['resources'],ref['resourceId']))
                allowed=allowed and bool(resource and cap.authorized(s,u,resource) and ref['resourceId'] in cap.ids(agent.get('mapResourceIds')))
            allowed=allowed and all(u['region']=='全区' or f['region']==u['region'] for f in result.get('features',[]))
            if not allowed:
                msg['analysisResult']={'status':'unavailable','summary':'该历史地图结果的访问权限已变化，请重新查询。','features':[],'statistics':None}
                msg['trace']=[dict(step='地图范围查询',status='不可用',output='权限已变化，请重新查询') if t.get('step')=='地图范围查询' else t for t in msg.get('trace',[])]
                sess.pop('spatialContext',None)
    return sessions
