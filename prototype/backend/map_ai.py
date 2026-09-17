"""Permission-scoped map question answering with compiled, parameterized SQL.

No model-supplied SQL is executed. An optional JSON planning gateway produces
the same closed query-plan schema as the explicit local demo interpreter.
"""
import hashlib
import json
import math
import os
import re
import sqlite3
import time
import uuid
from copy import deepcopy
from datetime import datetime
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlparse
from urllib.error import URLError
from shapely.geometry import shape, mapping, Point, Polygon
from shapely.ops import transform
from shapely.prepared import prep
from pyproj import Transformer
import capabilities as cap
import integration_admin as ia
import integration_results as results

FIELDS={'name':'对象名称','layer_id':'图层标识','layer_name':'图层名称','region':'盟市','county':'旗县','year':'年份','area_ha':'登记面积（公顷）','approval':'审批状态','kind':'业务类型','risk':'风险等级'}
GROUPS=['region','county','layer_name','approval']
ALIASES=[('永久基本农田','永久基本农田'),('基本农田','永久基本农田'),('地灾隐患','地质灾害隐患点'),('地质灾害隐患','地质灾害隐患点'),('风险区','地质灾害风险分区'),('建设用地','建设用地'),('采矿权','采矿权'),('探矿权','探矿权'),('矿产','矿产分布'),('生态红线','生态保护红线'),('生态保护红线','生态保护红线'),('耕地','土地利用现状'),('林地','林地分布'),('草原','草原类型'),('湿地','湿地斑块'),('变更调查','年度变更'),('乡镇','乡镇驻地'),('修复','生态修复'),('土壤','土壤质量'),('地下水','地下水监测')]
PAGE_SIZE=100

def require(*args):return cap.require(*args)
def store(s):return s['integration'].setdefault('aiQueries',[])
def text(value,limit=1000):
    require(isinstance(value,str) and len(value)<=limit,'文本格式或长度不正确');return value.strip()
def number(value):return type(value) in (int,float) and math.isfinite(value)
def geometry(f):
    if f.get('geometry'):return f['geometry']
    ring=f.get('coordinates')
    if ring and isinstance(ring[0],list):return mapping(Polygon(ring))
    return None

def dataset(s,u,context):
    require(isinstance(context,dict),'地图上下文无效')
    runtime=results.map_runtime(s,u,{'sceneId':text(context.get('sceneId',''),100),'extraLayers':context.get('extraLayers',[])})
    layers=[l for l in runtime['config']['layers'] if l.get('access')=='已授权']
    requested=context.get('layerIds',[])
    require(isinstance(requested,list) and len(requested)<=50 and all(isinstance(x,str) for x in requested),'图层范围无效')
    require(set(requested)<={l['id'] for l in layers},'所选图层已下架或未授权',403)
    if requested:layers=[l for l in layers if l['id'] in requested]
    rows=[]
    for l in layers:
        for f in l.get('features',[]):
            p=f.get('properties') or {};area=f.get('area');unit=f.get('unit','公顷')
            if number(area):area=area/15 if unit=='亩' else area/10000 if unit in ['平方米','㎡'] else area if unit in ['公顷','ha'] else None
            else:area=None
            year=p.get('year')
            try:year=int(year) if year is not None else None
            except (ValueError,TypeError):year=None
            rows.append(dict(fid=l['id']+'::'+str(f['id']),name=str(f.get('name','')),layer_id=l['id'],layer_name=l['name'],region=f.get('region') or p.get('city') or '',county=f.get('county') or p.get('county') or '',year=year,area_ha=area,approval=str(p.get('approval') or ''),kind=str(p.get('type') or p.get('luClass') or p.get('kind') or ''),risk=str(p.get('riskLevel') or ''),geometry=geometry(f),source=f.get('source') or l['name'],resourceId=l.get('resourceId',''),originalId=str(f['id'])))
    require(len(rows)<=20000,'当前查询范围超过2万个对象，请缩小图层范围')
    fingerprint=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return runtime,layers,rows,fingerprint

def schema(layers,rows):
    return dict(fields=FIELDS,layers=[dict(id=l['id'],name=l['name']) for l in layers],enums={key:sorted({r[key] for r in rows if r[key] not in (None,'')},key=str)[:200] for key in ['region','county','year','approval','kind','risk']},groupBy=GROUPS,operators=['eq','in','gt','gte','lt','lte','contains'],sort=['name','area_desc'],schemaVersion=1)

def valid_plan(value,layers):
    require(isinstance(value,dict) and set(value)<={'filters','groupBy','sort','clarification'},'查询计划格式无效')
    if value.get('clarification'):return {'clarification':text(value['clarification'])}
    filters=value.get('filters',[]);require(isinstance(filters,list) and len(filters)<=20,'筛选条件最多20项')
    clean=[]
    for f in filters:
        require(isinstance(f,dict) and set(f)=={'field','op','value'},'筛选格式无效')
        key=f['field'];op=f['op'];v=f['value']
        require(key in FIELDS and op in ['eq','in','gt','gte','lt','lte','contains'],'不支持的字段或运算符')
        vals=v if op=='in' else [v]
        require(isinstance(vals,list) and 0<len(vals)<=50,'筛选值数量无效')
        if key in ['year','area_ha']:require(op!='contains' and all(number(x) and 0<=x<=1e12 for x in vals),'年份、面积应为有效非负数值')
        else:require(op in ['eq','in','contains'] and all(isinstance(x,str) and 0<len(x)<=200 for x in vals),'文本筛选格式无效')
        if key=='layer_id':require(op in ['eq','in'] and set(vals)<={l['id'] for l in layers},'查询计划包含未授权图层',403)
        clean.append(dict(field=key,op=op,value=v))
    group=value.get('groupBy','');require(group in ['',*GROUPS],'不支持的统计维度')
    sort=value.get('sort','name');require(sort in ['name','area_desc'],'排序无效')
    return dict(filters=clean,groupBy=group,sort=sort)

def local_plan(question,meta,previous):
    q=question;plan=deepcopy(previous or dict(filters=[],groupBy='',sort='name'));plan.pop('clarification',None)
    if re.search('重新|重置|清空条件',q):plan=dict(filters=[],groupBy='',sort='name')
    recognized=False
    def put(field,op,value):
        nonlocal recognized
        plan['filters']=[x for x in plan['filters'] if x['field']!=field];plan['filters'].append(dict(field=field,op=op,value=value));recognized=True
    if re.search(r'人口|收入|产值|负责人|投资|同比|环比|平均|中位数|前\d+|不在|排除|除外|不是|不含|未批复|已审批|未批准',q):return {'clarification':'当前本地解析尚不支持该指标、否定条件或状态别名，请使用明确的地区、年份、面积阈值及数据中的审批状态。'}
    if re.search('新增建设用地|违法|合规|是否.*红线|占用.*红线',q):return {'clarification':'该问题需要新增认定、执法或叠加分析口径。当前可查询登记属性；请明确业务字段，或使用地块核查工具进行空间叠加。'}
    matches=[l for l in meta['layers'] if l['name'] in q]
    if not matches:
        for word,target in ALIASES:
            if word in q:
                matches=[l for l in meta['layers'] if target in l['name']]
                if matches:break
    if matches:
        put('layer_id','in',[l['id'] for l in matches]);plan['filters']=[f for f in plan['filters'] if f['field'] not in ['kind','risk']]
        if '耕地' in q and not re.search('基本农田|红线|质量',q):put('kind','contains','耕地')
    elif any(w in q for w,_ in ALIASES):return {'clarification':'当前授权图层中没有匹配的业务数据。请选择可用图层或调整业务对象。'}
    for field in ['region','county']:
        matched=[v for v in meta['enums'][field] if v in q or (field=='region' and v.endswith('市') and v[:-1] in q)]
        if matched:
            matched=[v for v in matched if not any(v!=other and v in other for other in matched)]
            put(field,'eq' if len(matched)==1 else 'in',matched[0] if len(matched)==1 else matched)
    location_text=q
    for value in sorted(meta['enums']['region']+meta['enums']['county'],key=len,reverse=True):
        location_text=location_text.replace(value,' ').replace(value[:-1] if value.endswith('市') else value,' ')
    location_text=re.sub(r'按.*?(?:盟市|地区|市|旗县|县)统计',' ',location_text)
    if re.search(r'[\u4e00-\u9fff]{2,}(?:市|县|旗)',location_text):return {'clarification':'问题包含当前数据中未识别的地区，请使用可用数据的盟市或旗县名称。'}
    if '全区' in q or '所有地区' in q:plan['filters']=[f for f in plan['filters'] if f['field'] not in ['region','county']];recognized=True
    years=re.findall(r'(20\d{2})年?',q)
    if years:put('year','in',list(dict.fromkeys(map(int,years))))
    elif '去年' in q:put('year','eq',datetime.now().year-1)
    elif '今年' in q:put('year','eq',datetime.now().year)
    if '不限年份' in q:plan['filters']=[f for f in plan['filters'] if f['field']!='year'];recognized=True
    amount=re.search(r'(不超过|不少于|超过|大于|至少|小于|低于|至多)\s*(\d+(?:\.\d+)?)\s*(亩|公顷|平方米)',q)
    if amount:
        word,n,unit=amount.groups();n=float(n)/(15 if unit=='亩' else 10000 if unit=='平方米' else 1)
        put('area_ha',{'超过':'gt','大于':'gt','不少于':'gte','至少':'gte','小于':'lt','低于':'lt','不超过':'lte','至多':'lte'}[word],n)
    if '未审批' in q:
        vals=[v for v in meta['enums']['approval'] if v in ['待报批','未报批','未审批','待审批']]
        if not vals:return {'clarification':'当前数据没有可用于判断未审批的状态，不能把缺少审批记录当作未审批。'}
        put('approval','in',vals)
    else:
        statuses=[v for v in meta['enums']['approval'] if v in q]
        if statuses:put('approval','in',statuses)
    if '高风险' in q:
        vals=[v for v in meta['enums']['risk'] if v in ['高','高风险','高风险区','高易发区']]
        if not vals:return {'clarification':'当前图层没有已登记的高风险等级，请选择风险分区图层。'}
        put('risk','in',vals)
    if re.search('按.*(盟市|地区|市)统计',q):plan['groupBy']='region';recognized=True
    elif re.search('按.*(旗县|县)统计',q):plan['groupBy']='county';recognized=True
    elif '按图层' in q:plan['groupBy']='layer_name';recognized=True
    elif '按审批' in q:plan['groupBy']='approval';recognized=True
    if re.search('面积.*(排序|最大|降序)|从大到小',q):plan['sort']='area_desc';recognized=True
    if re.search('查看|查询|显示|找出|统计|多少|范围内|周边|全部',q):recognized=True
    # Fail closed on phrases the local interpreter did not consume. In particular,
    # an unsupported range/negation must never silently broaden the SQL query.
    remaining=re.sub(r'高风险区?',' ',q)
    vocabulary=[l['name'] for l in meta['layers']]+[w for w,_ in ALIASES]
    for field in ['region','county','approval']:
        vocabulary+=meta['enums'][field]
    vocabulary += [v[:-1] for v in meta['enums']['region'] if v.endswith('市')]
    for value in sorted(set(vocabulary),key=len,reverse=True):remaining=remaining.replace(value,' ')
    for pattern in [r'(不超过|不少于|超过|大于|至少|小于|低于|至多)\s*\d+(?:\.\d+)?\s*(亩|公顷|平方米)',r'周边\s*\d+(?:\.\d+)?\s*(公里|千米|米)',r'20\d{2}年?',r'按(?:盟市|地区|市|旗县|县|图层|审批)(?:统计)?',r'面积(?:从大到小排序|从大到小|降序排序|降序|排序|最大)',r'重新|重置|清空条件|不限年份|所有地区|全区|去年|今年|未审批|高风险|范围内|选中对象|绘制范围|圈选范围|周边|从大到小|登记面积|面积合计|合计面积']:
        remaining=re.sub(pattern,' ',remaining)
    remaining=re.sub(r'查询|查看|显示|找出|统计|多少|所有|全部|只看|换成|改成|筛选|帮我|请|一下|对象|地块|图斑|数量|面积|合计|总共|一共|这些|以及|并且|和|中的|的|有|个|为|是|[\s，。、？?！!：:]+','',remaining)
    if remaining:return {'clarification':'本地解析尚不能确认“'+remaining[:80]+'”的含义，请改用明确的图层、地区、年份、面积阈值或登记审批状态。'}
    if not recognized:return {'clarification':'请说明要查的图层、地区或条件，例如“查询呼和浩特市的永久基本农田”，或“按旗县统计”。'}
    return plan

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def model_plan(question,meta,previous):
    url=os.environ.get('MAP_AI_PLANNER_URL','')
    if not url:return local_plan(question,meta,previous),''
    p=urlparse(url);require(p.scheme=='https' or (p.scheme=='http' and p.hostname in ['127.0.0.1','localhost']),'模型规划服务须使用 HTTPS 或本机 HTTP')
    require(not p.username and not p.password,'模型地址不能包含凭据')
    body=dict(question=question,schema=meta,previousPlan=previous,instruction='只返回符合 schema 的查询计划 JSON：filters、groupBy、sort；不能确定时返回 clarification。禁止生成 SQL。')
    headers={'Content-Type':'application/json'}
    if os.environ.get('MAP_AI_PLANNER_TOKEN'):headers['Authorization']='Bearer '+os.environ['MAP_AI_PLANNER_TOKEN']
    try:
        with build_opener(NoRedirect()).open(Request(url,data=json.dumps(body,ensure_ascii=False).encode(),headers=headers),timeout=8) as response:
            data=response.read(128001);require(len(data)<=128000,'模型响应过大')
            answer=json.loads(data)
    except (URLError,TimeoutError,ValueError):raise cap.Invalid('模型规划服务未完成请求，请稍后重试；未执行查询',502)
    return answer,'模型规划服务'

def spatial_filter(context,question,s,u):
    value=context.get('geometry');radius=context.get('radiusMeters')
    match=re.search(r'周边\s*(\d+(?:\.\d+)?)\s*(公里|千米|米)',question)
    if match:radius=float(match[1])*(1000 if match[2] in ['公里','千米'] else 1)
    if value is None:
        require(not radius and not re.search('范围内|周边|圈选|选中',question),'请先绘制范围或使用地图选中对象，再查询范围内 / 周边对象')
        return None,None
    import tool_center as tc
    from shapely.errors import GEOSException
    try:g=tc.geometry(value)
    except (ValueError,GEOSException):raise cap.Invalid('选区几何无效')
    require(g.is_valid and -180<=g.bounds[0]<=g.bounds[2]<=180 and -85<=g.bounds[1]<=g.bounds[3]<=85,'选区需为有效经纬度几何')
    if radius is not None:
        require(number(radius) and 0<radius<=100000,'周边距离须大于0且不超过100公里')
        center=g.centroid;local=f'+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m'
        forward=Transformer.from_crs('EPSG:4326',local,always_xy=True).transform;back=Transformer.from_crs(local,'EPSG:4326',always_xy=True).transform
        g=transform(back,transform(forward,g).buffer(radius))
    else:require(g.geom_type in ['Polygon','MultiPolygon'],'点对象请指定周边距离，例如“周边1公里”')
    import analysis_engine as ae
    settings=s['integration']['settings']['published'];limit=min(settings['maxAreaHa'],settings.get('roleAreaLimits',{}).get(u['role'],settings['maxAreaHa']))
    require(transform(ae.PROJECT,g).area/10000<=limit,'选区超出当前角色面积上限，请缩小范围')
    return mapping(g),radius

def compile_sql(plan,spatial):
    where=[];params=[]
    for f in plan['filters']:
        key=f['field'];op=f['op'];v=f['value']
        if op=='in':where.append('"'+key+'" IN ('+','.join('?' for _ in v)+')');params+=v
        elif op=='contains':where.append('instr("'+key+'", ?) > 0');params.append(v)
        else:where.append('"'+key+'" '+{'eq':'=','gt':'>','gte':'>=','lt':'<','lte':'<='}[op]+' ?');params.append(v)
    if spatial:where.append('spatial_match(geometry) = 1')
    condition=' WHERE '+' AND '.join(where) if where else ''
    return condition,params

def run(rows,plan,scope,page=1):
    require(type(page) is int and 1<=page<=200,'页码无效')
    condition,params=compile_sql(plan,scope is not None);order='area_ha DESC, fid' if plan['sort']=='area_desc' else 'name, fid'
    sql='SELECT fid, '+', '.join(FIELDS)+', geometry, source FROM map_features'+condition+' ORDER BY '+order+' LIMIT ? OFFSET ?'
    start=time.monotonic()
    with sqlite3.connect(':memory:') as conn:
        conn.row_factory=sqlite3.Row
        keys=['fid',*FIELDS,'geometry','source']
        conn.execute('CREATE TABLE map_features ('+', '.join('"'+k+'" '+('REAL' if k=='area_ha' else 'INTEGER' if k=='year' else 'TEXT') for k in keys)+')')
        conn.executemany('INSERT INTO map_features VALUES ('+','.join('?' for _ in keys)+')',[[json.dumps(r[k]) if k=='geometry' and r[k] is not None else r.get(k) for k in keys] for r in rows])
        if scope:
            boundary=prep(shape(scope))
            conn.create_function('spatial_match',1,lambda raw: int(bool(raw) and boundary.intersects(shape(json.loads(raw)))))
        conn.execute('PRAGMA query_only=ON')
        conn.set_progress_handler(lambda:int(time.monotonic()-start>3),1000)
        totals=dict(conn.execute('SELECT COUNT(*) AS total, COALESCE(SUM(area_ha),0) AS areaHa, COUNT(area_ha) AS areaKnown FROM map_features'+condition,params).fetchone())
        records=[dict(r) for r in conn.execute(sql,[*params,PAGE_SIZE,(page-1)*PAGE_SIZE])]
        groups=[]
        if plan['groupBy']:
            key=plan['groupBy'];groups=[dict(r) for r in conn.execute('SELECT "'+key+'" AS name, COUNT(*) AS count, COALESCE(SUM(area_ha),0) AS areaHa FROM map_features'+condition+' GROUP BY "'+key+'" ORDER BY count DESC',params)]
    features=[]
    for r in records:
        geom=json.loads(r.pop('geometry')) if r.get('geometry') else None
        r['hasGeometry']=geom is not None
        if geom:features.append(dict(type='Feature',geometry=geom,properties=dict(r,id=r['fid'],aiQuery=True)))
    return dict(rows=records,mapResult=dict(type='FeatureCollection',features=features),statistics=groups,sql=sql,parameters=[*params,PAGE_SIZE,(page-1)*PAGE_SIZE],page=page,pageSize=PAGE_SIZE,loaded=len(features),durationMs=round((time.monotonic()-start)*1000,2),**totals)

def own(s,u,key):
    r=next((x for x in store(s) if x['id']==key and x['userId']==u['id']),None);require(r,'查询不存在或不可访问',404);return r

def execute(s,u,op,p):
    require(ia.rights(s,u)['analyze'],'需要一张图空间分析权限',403)
    if op=='history':
        accessible=[]
        for r in reversed(store(s)):
            if r['userId']!=u['id'] or r.get('cancelled'):continue
            try:dataset(s,u,r['context'])
            except cap.Invalid:continue
            accessible.append(dict(id=r['id'],question=r['question'],created=r['created'],sceneId=r['context']['sceneId']))
            if len(accessible)==20:break
        return accessible
    if op=='cancel':
        r=own(s,u,p.get('id'));r['cancelled']=True;return {'ok':True}
    if op=='result':
        r=own(s,u,p.get('id'));require(not r.get('cancelled'),'查询已取消',409)
        runtime,layers,rows,fingerprint=dataset(s,u,r['context'])
        require(fingerprint==r['fingerprint'],'数据或授权已变化，请重新提问以生成新结果',409)
    elif op=='ask':
        q=text(p.get('question',''));require(q,'请输入业务问题')
        raw=p.get('context',{});require(isinstance(raw,dict),'地图上下文无效')
        context=deepcopy({k:v for k,v in raw.items() if k in ['sceneId','extraLayers','layerIds','region','geometry','radiusMeters']});runtime,layers,rows,fingerprint=dataset(s,u,context)
        previous=None
        if p.get('previousId'):
            old=own(s,u,p['previousId']);require(not old.get('cancelled'),'上一轮已取消')
            require(old['context']['sceneId']==context['sceneId'],'地图场景已变化，请开启新对话')
            previous=old['plan'];valid_plan(previous,layers)
        meta=schema(layers,rows)
        plan,mode=model_plan(q,meta,previous)
        plan=valid_plan(plan,layers)
        if plan.get('clarification'):return dict(status='clarification',message=plan['clarification'],mode=mode)
        # A map-region selection applies unless the question explicitly supplies a region.
        region=text(context.get('region',''),100)
        if region and not re.search('全区|所有地区',q) and not any(f['field'] in ['region','county'] for f in plan['filters']):
            key='county' if region in meta['enums']['county'] else 'region'
            plan['filters'].append(dict(field=key,op='eq',value=region))
        scope,radius=spatial_filter(context,q,s,u)
        if radius is not None:context['radiusMeters']=radius
        r=dict(id=uuid.uuid4().hex,userId=u['id'],question=q,context=context,scope=scope,plan=plan,mode=mode,fingerprint=fingerprint,created=datetime.now().isoformat(timespec='seconds'))
    else:raise cap.Invalid('未知地图问数操作',404)
    try:data=run(rows,r['plan'],r['scope'],p.get('page',1))
    except sqlite3.Error:raise cap.Invalid('查询超时或空间数据无法计算，请缩小范围或检查源数据',422)
    if op=='ask':save_query(s,u,r)
    labels=[FIELDS[f['field']]+' '+{'eq':'=','in':'属于','gt':'>','gte':'>=','lt':'<','lte':'<=','contains':'包含'}[f['op']]+' '+str(f['value']) for f in r['plan']['filters']]
    data.update(queryId=r['id'],status='completed',mode=r['mode'],question=r['question'],context=r['context'],interpretedFilters=labels,summary=f"基于演示数据，查询到 {data['total']} 个对象，登记面积合计 {data['areaHa']:.4f} 公顷。",warnings=['当前查询来自已授权地图场景的本地示例数据；不代表真实业务底数。','面积为对象登记属性之和，未做空间去重，也不是选区内裁剪面积。'],sources=[dict(id=l['id'],name=l['name']) for l in layers if any(x['layer_id']==l['id'] for x in data['rows'])])
    if data['areaKnown']<data['total']:data['warnings'].append(f"{data['total']-data['areaKnown']} 个对象没有可汇总的登记面积。")
    if data['loaded']<len(data['rows']):data['warnings'].append('部分对象没有可定位几何，仅在表格展示。')
    if data['total']>PAGE_SIZE:data['warnings'].append('地图仅显示当前页；总数和统计来自完整查询结果。')
    return data


def save_query(s,u,r):
    """Merge only this query into current state, rechecking access after planning."""
    require(ia.rights(s,u)['analyze'],'需要一张图空间分析权限',403)
    _,layers,_,fingerprint=dataset(s,u,r['context'])
    require(fingerprint==r['fingerprint'],'数据或授权已变化，请重新提问',409)
    valid_plan(r['plan'],layers)
    spatial_filter(r['context'],r['question'],s,u)
    store(s).append(deepcopy(r))
    mine=[x for x in store(s) if x['userId']==u['id']]
    for old in mine[:-50]:store(s).remove(old)
