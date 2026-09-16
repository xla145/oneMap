"""Published result projections and object-scoped telemetry. No fabricated connection status."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import capabilities as cap
import centers as c
import portal_management as pm


def catalog(s,u):
    import integration as ig
    p=s['integration'];rows=ig.catalog(s,u);out=[]
    for item in rows:
        kind=item['id'].split(':',1)[0];key=item['id'].split(':',1)[1]
        entity={'resource':'resources','knowledge':'knowledge','agent':'agents'}.get(kind)
        raw=c.find(s[entity],key) if entity else c.find(s['platform']['apps'],key) if kind=='app' else c.find(pm.migrate(s)['tools'],key)
        live=(raw or {}).get('published') or {};placement=item['placement'];meta=p.get('layerMetadata',{}).get(key,{}) if item['kind']=='图层服务' else {}
        # Read only published primary metadata; placement is a separate managed taxonomy.
        row=dict(item,description=live.get('description',''),provider=placement.get('department') or live.get('provider') or live.get('source') or live.get('owner') or '未登记',publisher=live.get('publisher') or live.get('owner') or live.get('source') or live.get('provider') or '未登记',publishedAt=live.get('publishedAt') or (live.get('updated','') if kind=='tool' else ''),updated=live.get('updated',item.get('updated','')),manual=placement.get('manual',''),frequency=live.get('frequency','未登记'),version=live.get('version'),theme=placement.get('theme',''),toolCategory=live.get('category') or '未分类',appType=live.get('type',''),metadata=deepcopy(meta))
        if item['group']=='应用场景' and not row['theme']:
            row['theme']={'耕地保护':'耕地保护和国土绿化空间','国土空间规划':'国土空间规划','矿产资源':'矿产资源','生态修复':'生态修复','灾害防治':'灾害防治','督察执法':'督察执法'}.get(item['category'],'')
            row['themeSource']='按原应用分类归入' if row['theme'] else '未归类'
        else:row['themeSource']='展示分类配置' if row['theme'] else '未归类'
        if item['kind']=='图层服务':
            row.update(layerTheme=meta.get('theme') or item['category'] or '未分类',provider=meta.get('department') or row['provider'],cities=meta.get('cities') or [item.get('region') or '未登记'],hotspots=meta.get('hotspots') or [],dataKind=meta.get('dataKind','未登记'),sourceScope=meta.get('sourceScope','未登记'),capacityBytes=meta.get('capacityBytes'),collectionState=meta.get('collectionState','未登记'))
        out.append(row)
    return out


def systems(s,u,rows):
    visible_apps={r['id'].split(':',1)[1] for r in rows if r['group']=='应用场景'};out=[]
    for system in c.migrate(s)['systems']:
        cfg=s['integration'].get('resultSystems',{}).get(system['id'],{})
        if not cfg.get('enabled') or (u['role']!='平台管理员' and u['role'] not in cfg.get('roles',[])):continue
        if system.get('appId') and system['appId'] not in visible_apps:continue
        out.append(dict(id=system['id'],name=system['name'],theme=cfg['theme'],provider=cfg.get('provider') or '未登记',entry=system.get('entry',''),status='入口已配置' if system.get('entry') else '待配置入口',requiresSso=system.get('requiresSso',False)))
    return out


def bootstrap(s,u):
    import integration_admin as ia
    if not ia.rights(s,u)['view']:return None
    rows=catalog(s,u)
    import platform_domain as pd
    refs={}
    for app in rows:
        if app['group']!='应用场景' or app['appType']!='scene':continue
        source=c.find(s['platform']['apps'],app['id'].split(':',1)[1]);scene_id=source['published'].get('targetId')
        try:scene=pd.scene_runtime(s,u,dict(id=scene_id))
        except cap.Invalid:continue
        for layer in scene['config']['layers']:
            refs.setdefault(layer['resourceId'],[]).append(dict(id=scene['id'],name=scene['name'],layerId=layer['id']))
    for row in rows:
        if row['kind']=='图层服务':row['scenes']=refs.get(row['resourceId'],[])
    return dict(layers=[r for r in rows if r['kind']=='图层服务'],tools=[r for r in rows if r['group']=='工具'],scenes=[r for r in rows if r['group']=='应用场景'],systems=systems(s,u,rows))


def map_runtime(s,u,arg,strict=True):
    """Compose published, authorized scene layers without accepting client geometry."""
    import integration_admin as ia
    import platform_domain as pd
    cap.require(ia.rights(s,u)['view'],'需要成果查看权限',403)
    if arg.get('sceneId')=='nmg-reference-demo':
        import nmg_demo
        cap.require(not arg.get('extraLayers'),'参考demo不接受额外业务图层')
        return nmg_demo.runtime()
    base=pd.scene_runtime(s,u,dict(id=arg.get('sceneId')))
    refs=arg.get('extraLayers',[])
    cap.require(isinstance(refs,list) and len(refs)<=50,'最多叠加50个图库图层')
    available={r['resourceId']:r for r in bootstrap(s,u)['layers']} if refs else {}
    known={l['resourceId'] for l in base['config']['layers']};accepted=[];dropped=0
    for ref in refs:
        cap.require(isinstance(ref,dict) and isinstance(ref.get('resourceId'),str) and isinstance(ref.get('sceneId'),str),'叠加图层引用无效')
        row=available.get(ref['resourceId'])
        try:
            cap.require(row and row['authorized'] and any(x['id']==ref['sceneId'] for x in row['scenes']),'叠加来源已不可访问',403)
            source=pd.scene_runtime(s,u,dict(id=ref['sceneId']))
            layer=next((x for x in source['config']['layers'] if x['resourceId']==ref['resourceId'] and x['access']=='已授权'),None)
            cap.require(layer,'叠加图层未授权或已移除',403)
        except cap.Invalid:
            if strict:raise
            dropped+=1;continue
        if layer['resourceId'] in known:continue
        known.add(layer['resourceId']);layer=deepcopy(layer)
        layer.update(id='overlay:'+layer['resourceId'],visible=True,sourceSceneId=source['id'],sourceSceneName=source['name'])
        base['config']['layers'].append(layer);accepted.append(dict(resourceId=ref['resourceId'],sceneId=ref['sceneId']))
    base['extraLayers']=accepted;base['droppedLayers']=dropped
    return base


def stats(s,u,arg):
    import integration_admin as ia
    cap.require(ia.rights(s,u)['view'],'需要成果查看权限',403)
    domain=arg.get('domain','layers');cap.require(domain in ['layers','tools','scenes'],'统计对象无效')
    period=arg.get('period','day');cap.require(period in ['day','week','month'],'趋势粒度无效')
    start=arg.get('start','');end=arg.get('end','')
    for d in [start,end]:
        cap.require(isinstance(d,str),'日期格式错误')
        if d:
            try:datetime.strptime(d,'%Y-%m-%d')
            except ValueError:raise cap.Invalid('日期需为YYYY-MM-DD')
    cap.require(not start or not end or start<=end,'起始日期不能晚于结束日期')
    projection=bootstrap(s,u);all_rows=projection[domain];resource=arg.get('resource','');department=arg.get('department','')
    cap.require(isinstance(resource,str) and isinstance(department,str),'筛选参数格式错误')
    cap.require(not resource or resource in {r['id'] for r in all_rows},'统计对象不可见',403)
    rows=[r for r in all_rows if not resource or r['id']==resource];keys={r['id']:r for r in rows}
    kinds={'layers':{'open','call','layerQuery'},'tools':{'open','call'},'scenes':{'open'}}[domain]
    events=[e for e in s['integration']['events'] if e.get('target') in keys and e['kind'] in kinds]
    selected=[e for e in events if (not start or e['at'][:10]>=start) and (not end or e['at'][:10]<=end) and (not department or e.get('department')==department)]
    def counts(es):return dict(opens=sum(e['kind']=='open' for e in es),calls=sum(e['kind']=='call' for e in es),queries=sum(e['kind']=='layerQuery' for e in es),users=len({e['userId'] for e in es if e['kind']==activity}))
    def bucket(e):
        if period=='week':year,week,_=datetime.strptime(e['at'][:10],'%Y-%m-%d').isocalendar();return f'{year}-W{week:02d}'
        return e['at'][:7] if period=='month' else e['at'][:10]
    def distribution(field):
        counts=Counter(r.get(field) or '未登记' for r in rows)
        return [dict(name=k,count=n,percent=round(n/len(rows)*100,1) if rows else 0) for k,n in counts.most_common()]
    activity=arg.get('activity') or ('open' if domain=='scenes' else 'layerQuery' if domain=='layers' else 'call')
    cap.require(activity in kinds,'统计事件类型无效')
    ranks=Counter(e['target'] for e in selected if e['kind']==activity)
    departments=Counter(e.get('department') or '历史记录未登记' for e in selected if e['kind']==activity)
    trend=Counter(bucket(e) for e in selected if e['kind']==activity)
    data_tables=[r for r in catalog(s,u) if r['kind']=='数据库表']
    scale=dict(dataTables=len(data_tables),vectorLayers=sum(r.get('dataKind')=='矢量' for r in all_rows),rasterLayers=sum(r.get('dataKind')=='栅格' for r in all_rows),certificateLayers=sum(r.get('dataKind')=='证照' for r in all_rows),unclassifiedLayers=sum(r.get('dataKind')=='未登记' for r in all_rows)) if domain=='layers' else None
    capacity=[r['capacityBytes'] for r in rows if r.get('capacityBytes') is not None]
    return dict(domain=domain,scale=scale,systems=projection['systems'] if domain=='scenes' else [],total=len(rows),providers=len({r['provider'] for r in rows if r['provider']!='未登记'}),cumulative=counts(events),month=counts([e for e in events if e['at'].startswith(c.now()[:7])]),filtered=counts(selected),classification=distribution('dataKind' if domain=='layers' else 'toolCategory' if domain=='tools' else 'theme'),providerDistribution=distribution('provider'),sourceScopes=distribution('sourceScope') if domain=='layers' else [],collectionStates=distribution('collectionState') if domain=='layers' else [],capacityBytes=sum(capacity) if capacity else None,capacityKnown=len(capacity),rankings=[dict(id=k,name=keys[k]['name'],count=n) for k,n in ranks.most_common(20)],departmentRanks=[dict(name=k,count=n) for k,n in departments.most_common(20)],trend=[dict(name=k,count=n) for k,n in sorted(trend.items())],departments=sorted({e.get('department') for e in events if e.get('department')}),resources=[dict(id=r['id'],name=r['name']) for r in all_rows],activity=activity,scope='目录规模为当前可见已发布对象；累计和本月按所选对象统计，不受日期及调用部门筛选影响。趋势及排行遵循日期、调用部门和对象筛选。空间查询、成功调用、入口访问及使用人数均按所选活动口径统计；容量及接入状态来自登记，不代表实时外部监测。')


def execute(s,u,op,arg):
    import integration as ig
    import integration_admin as ia
    if op=='stats':return stats(s,u,arg)
    if op=='map.runtime':return map_runtime(s,u,arg,strict=False)
    if op=='system.open':
        cap.require(ia.rights(s,u)['view'],'需要成果查看权限',403)
        row=next((r for r in systems(s,u,catalog(s,u)) if r['id']==arg.get('id')),None)
        cap.require(row and row['entry'],'系统未配置入口或无访问权限',403)
        return dict(target=row['entry'],external=row['entry'].startswith('https://'))
    pm.admin(u)
    cap.require(op=='system.save','未知成果操作',404)
    key=arg.get('id');cap.require(c.find(c.migrate(s)['systems'],key),'系统不存在')
    configs=s['integration'].setdefault('resultSystems',{});old=configs.get(key,dict(rev=0));cap.require(arg.get('rev')==old['rev'],'关联配置已更新',409)
    v=ig.values(arg);theme=v.get('theme');roles=v.get('roles',[])
    cap.require(theme in ig.THEMES,'请选择八类主题');cap.require(isinstance(roles,list) and all(r in {x['role'] for x in s['users']} for r in roles),'可用角色无效')
    cap.require(type(v.get('enabled')) is bool,'启用状态无效')
    configs[key]=dict(rev=old['rev']+1,theme=theme,roles=list(dict.fromkeys(roles)),enabled=v['enabled'],provider=ig.text(v.get('provider',''),200),at=c.now(),actor=u['name'])
    return deepcopy(configs[key])
