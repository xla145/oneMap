"""Tool catalogue metadata and local spatial component interfaces."""
import json
import math
import re
from copy import deepcopy
from shapely import wkt
from shapely.geometry import shape, mapping, Point, Polygon
from shapely.ops import transform
from shapely.validation import explain_validity
from pyproj import CRS, Transformer
from capabilities import require, Invalid

POLYGON = {'type':'Polygon','coordinates':[[[111.7,40.75],[111.76,40.75],[111.76,40.81],[111.7,40.81],[111.7,40.75]]]}
MODULES = {'coordinate':'坐标转换','overlay':'叠加分析','area':'面积核算','buffer':'缓冲分析','compliance':'合规核查','spatial-check':'空间检查','spatial-query':'空间查询','spatial-store':'空间入库','spatial-edit':'空间编辑','external':'外部服务'}

def contract(engine):
    examples = {
      'external':{},
      'coordinate': {'source':'EPSG:4490','target':'EPSG:4546','geometry':'POINT (111.7 40.8)'},
      'spatial-check': {'geometry':POLYGON,'boundary':POLYGON,'neighbors':[]},
      'spatial-query': {'resourceId':'r3','q':'','region':'','coordinate':[111.72,40.77]},
      'spatial-store': {'resourceId':'r3','featureId':'parcel-1','revision':1,'geometry':POLYGON,'properties':{'name':'示例地块','region':'呼和浩特市'}},
      'spatial-edit': {'resourceId':'r3','featureId':'parcel-1','revision':2,'operation':'update','geometry':POLYGON},
      'buffer': {'x':111.7,'y':40.8,'distance':1000},
      'overlay': {'geometry':{'type':'FeatureCollection','features':[{'type':'Feature','geometry':POLYGON,'properties':{'id':'a'}},{'type':'Feature','geometry':POLYGON,'properties':{'id':'b'}}]},'operation':'intersection'},
    }
    fields = {
      'external':[],
      'coordinate':[('source / target','string','是','EPSG 坐标系；支持 4326、3857、4490 和 CGCS2000 高斯投影'),('geometry / x,y','WKT、GeoJSON、坐标文本 / number','是','几何输入或单点 X、Y；坐标文件支持每行 x,y 或 点号,x,y')],
      'spatial-check':[('geometry','WKT / GeoJSON / 坐标文本','是','被检查面'),('boundary','WKT / GeoJSON','否','行政区边界；未提供时该项返回未检查'),('neighbors','array','否','相邻图形，共边检查依据')],
      'spatial-query':[('resourceId','string','是','本地工作图层对应资源 ID'),('q / region / coordinate','string / string / [x,y]','否','关键词、行政区与坐标定位可组合筛选')],
      'spatial-store':[('resourceId / featureId','string','是','目标工作图层与唯一要素 ID'),('revision','integer','是','先查询取得的最新图层版本'),('geometry / properties','几何 / object','是 / 否','图形与业务属性')],
      'spatial-edit':[('resourceId / revision','string / integer','是','目标工作图层与最新版本'),('featureId / name','string','是','按 ID 或唯一名称定位'),('operation','string','是','update 或 delete'),('geometry','几何','更新时必填','替换图形')],
      'buffer':[('x / y','number','是','WGS84 经度、纬度'),('distance','number','是','缓冲距离，单位米，范围大于0且不超过100000')],
      'overlay':[('geometry','GeoJSON / WKT数组','是','相交、差集输入两个面，按 A、B 顺序'),('operation','string','是','intersection / difference / union / buffer / area'),('crs / distance','string / number','否','坐标系与缓冲距离（米）')],
    }
    outputs={
      'external':('按提供方登记的接口协议返回，未配置的返回结构不作推定。',{}),
      'buffer':('返回 GeoJSON Feature，geometry 为缓冲多边形，properties.distanceMeters 为缓冲距离（米）。',{'type':'Feature','geometry':POLYGON,'properties':{'distanceMeters':1000}}),
      'compliance':('返回示例规则版本、逐项 rows、地块 parcels、冲突范围 conflicts 与整体 state。',{'state':'无法判定','rows':[],'parcels':[],'conflicts':{'type':'FeatureCollection','features':[]}}),
      'coordinate':('source、target 为坐标系；geometry 为目标几何；wkt 为目标坐标串；单点另返回 x、y。',{'source':'EPSG:4326','target':'EPSG:3857','x':0,'y':0,'geometry':{'type':'Point','coordinates':[0,0]},'wkt':'POINT (0 0)'}),
      'spatial-check':('valid 为拓扑有效性；checks 逐项返回通过、不通过、已检查或未检查；complete 表示是否具备全部检查依据。',{'valid':True,'checks':[{'name':'行政区范围','status':'未检查','detail':'未提供行政区边界'}],'complete':False}),
      'spatial-query':('features 为匹配要素列表；total 为结果数量；revision 为图层当前版本。',{'type':'FeatureCollection','features':[],'total':0,'revision':1}),
      'spatial-store':('revision 为写入后的版本；count 为图层要素数量；scope 标识本地操作范围。',{'revision':2,'count':1,'scope':'仅变更本地工具工作图层，未写入生产GIS'}),
      'spatial-edit':('revision 为编辑后的版本；count 为剩余要素数量。',{'revision':3,'count':0}),
    }
    output,return_example=outputs.get(engine,('返回 GeoJSON 几何与计算属性；面积运算另返回 areaSquareMeters（平方米）。',{'type':'FeatureCollection','features':[],'areaSquareMeters':0,'empty':True}))
    return dict(parameters=[dict(name=n,type=t,required=r,description=d) for n,t,r,d in fields.get(engine,[('geometry','WKT / GeoJSON / 坐标文本','是','输入图形'),('crs','string','否','默认 EPSG:4326')])], example=examples.get(engine,{'geometry':POLYGON}), output=output,returnExample=return_example)

def enrich(s,row):
    import portal_management as pm
    from capabilities import published
    r=deepcopy(row); resource=published(pm.find(s['resources'],r.get('resourceId')))
    sharing=s.get('centers',{}).get('sharing',{}).get(r.get('resourceId'),{})
    directory=pm.find(s.get('centers',{}).get('directories',[]),sharing.get('directoryId') or r.get('directoryId'))
    source=(resource or {}).get('source') or r.get('provider') or '自然资源示例数据中心'
    r.update(sourceUnit=source,provider=r.get('provider') or source,region=(resource or {}).get('region') or r.get('region') or '全区',directoryName=(directory or {}).get('name','未编目'),interfaceType=r.get('interfaceType') or 'JSON / HTTPS',module=r.get('module') or MODULES.get(r['engine'],'外部服务'))
    r['applicationCount']=sum(any(i['resourceId']==r.get('resourceId') for i in a['items']) for a in s['applications'])
    r['publishedAt']=r.get('publishedAt') or r.get('updated','')
    r['publisher']=r.get('publisher') or r['provider']
    r['contract']=contract(r['engine'])
    for key,target,kind in [('requestParameters','parameters',list),('outputExample','returnExample',dict)]:
        if r.get(key):
            try:value=json.loads(r[key])
            except (ValueError,TypeError):continue
            if isinstance(value,kind):r['contract'][target]=value
    return r

def crs(value):
    require(isinstance(value,str) and re.fullmatch(r'EPSG:\d{4,5}',value),'请使用 EPSG 坐标系编号')
    code=int(value.split(':')[1]);require(code in (4326,3857,4490) or 4491<=code<=4554,'支持 WGS84、Web Mercator 与 CGCS2000 经纬度 / 高斯投影')
    return CRS.from_user_input(value)

def geometry(value):
    if isinstance(value,str):
        require(len(value)<=200000,'几何输入不能超过 200KB')
        value=value.strip()
        if value.startswith(('{','[')):
            try:value=json.loads(value)
            except ValueError:raise Invalid('几何 JSON 格式错误')
        elif re.match(r'^(POINT|MULTIPOINT|LINESTRING|MULTILINESTRING|POLYGON|MULTIPOLYGON)\s*[Z M(]',value,re.I):
            try:return checked(wkt.loads(value))
            except (ValueError,TypeError):raise Invalid('WKT 格式错误')
        else:
            points=[]
            for line in value.splitlines():
                if not line.strip():continue
                cells=re.split(r'[,，\s]+',line.strip())
                require(len(cells) in (2,3),'坐标文件每行应为 x,y 或 点号,x,y，不含表头')
                try:points.append([float(x) for x in cells[-2:]])
                except ValueError:raise Invalid('坐标文件包含非数值坐标')
            require(len(points)>=3,'坐标文件至少包含三个界址点')
            return checked(Polygon(points))
    if isinstance(value,list):value={'type':'Polygon','coordinates':[value]}
    require(isinstance(value,dict),'请提供 WKT、GeoJSON 或界址点坐标文本')
    if value.get('type')=='Feature':value=value.get('geometry')
    try:return checked(shape(value))
    except (ValueError,TypeError,KeyError,AttributeError):raise Invalid('几何结构错误')

def checked(g):
    require(g.geom_type in ('Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon'),'仅支持点、线、面几何')
    require(not g.is_empty and not g.has_z,'几何不能为空，只支持二维坐标')
    count=0
    def walk(v):
        nonlocal count
        if isinstance(v[0],(int,float)):
            count+=1;require(all(math.isfinite(x) for x in v),'坐标必须为有限数值')
        else:
            for item in v:walk(item)
    walk(mapping(g)['coordinates']);require(count<=50000,'顶点不能超过50000个')
    return g

def project(g,source,target):
    src=crs(source);dst=crs(target)
    if src.is_geographic:require(-180<=g.bounds[0]<=g.bounds[2]<=180 and -90<=g.bounds[1]<=g.bounds[3]<=90,'经纬度超出范围')
    elif source=='EPSG:3857':require(all(abs(x)<=20037508.35 for x in g.bounds),'Web Mercator 坐标超出范围')
    return checked(transform(Transformer.from_crs(src,dst,always_xy=True,allow_ballpark=True).transform,g))

def datum_note(source,target='EPSG:4326'):
    # PROJ has no exact CGCS2000↔WGS84 datum operation without local parameters.
    crosses=(source not in ('EPSG:4326','EPSG:3857')) != (target not in ('EPSG:4326','EPSG:3857'))
    return 'CGCS2000 与 WGS84 间使用近似基准转换；未提供地方控制点 / 七参数，不能作为测绘成果。' if crosses else ''

def normalize(value,source='EPSG:4326'):
    import analysis_engine as ae
    if isinstance(value,str) and value.strip().startswith(('{','[')):
        try:value=json.loads(value)
        except ValueError:raise Invalid('几何 JSON 格式错误')
    if isinstance(value,dict) and value.get('type')=='FeatureCollection':rows=value.get('features',[])
    elif isinstance(value,list) and value and isinstance(value[0],str):rows=value
    else:rows=[value]
    require(isinstance(rows,list) and 0<len(rows)<=100,'需包含1～100个图形')
    result=[]
    for i,row in enumerate(rows):
        props=(row.get('properties') or {}) if isinstance(row,dict) else {};require(isinstance(props,dict),'要素属性必须为对象')
        result.append(dict(type='Feature',geometry=mapping(project(geometry(row),source,'EPSG:4326')),properties={**props,'id':str(props.get('id',i+1))}))
    out=ae.normalize(json.loads(json.dumps(dict(type='FeatureCollection',features=result))),'EPSG:4326')
    if datum_note(source):out['coordinateNote']=datum_note(source)
    return out

def coordinate(p):
    source=p.get('source','EPSG:4326');target=p.get('target','EPSG:3857')
    if 'geometry' in p:g=geometry(p['geometry'])
    else:
        require(all(type(p.get(k)) in (int,float) and math.isfinite(p[k]) for k in ('x','y')),'X、Y 必须为有限数值')
        g=Point(p['x'],p['y'])
    out=project(g,source,target)
    result=dict(source=source,target=target,geometry=mapping(out),wkt=out.wkt,note='按已声明坐标系进行投影转换；不包含地方测绘控制点拟合或七参数校正')
    result['approximateDatum']=bool(datum_note(source,target))
    if result['approximateDatum']:result['note']=datum_note(source,target)
    if out.geom_type=='Point':result.update(x=out.x,y=out.y)
    return result

def check(p):
    g=geometry(p.get('geometry'));require(g.geom_type in ('Polygon','MultiPolygon'),'需输入面图形')
    parts=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
    duplicate=[]
    for index,poly in enumerate(parts):
        for ring_index,ring in enumerate([poly.exterior,*poly.interiors]):
            points=list(ring.coords)[:-1];seen=set()
            for point in points:
                if point in seen:duplicate.append(dict(polygon=index+1,ring=ring_index+1,point=point))
                seen.add(point)
    reason=explain_validity(g)
    checks=[dict(name='是否成图',status='通过' if g.area>0 else '不通过',detail='非空面及正面积'),dict(name='空间拓扑',status='通过' if g.is_valid else '不通过',detail=reason),dict(name='自相交',status='不通过' if 'self-intersection' in reason.lower() else '通过',detail=reason),dict(name='重复点',status='不通过' if duplicate else '通过',detail=duplicate)]
    boundary=p.get('boundary');neighbors=p.get('neighbors')
    if boundary is not None:
        b=geometry(boundary);require(b.is_valid and b.geom_type in ('Polygon','MultiPolygon'),'行政区边界必须为有效面')
        checks.append(dict(name='行政区范围',status=('通过' if b.covers(g) else '不通过') if g.is_valid else '未检查',detail='按传入的同坐标系行政区边界检查'))
    else:checks.append(dict(name='行政区范围',status='未检查',detail='未提供行政区边界'))
    require(neighbors is None or isinstance(neighbors,list) and len(neighbors)<=100,'相邻图形最多100个')
    shared=[]
    for i,item in enumerate(neighbors or []):
        n=geometry(item);require(n.is_valid,'相邻图形无效')
        if g.is_valid and g.boundary.intersection(n.boundary).length>0:shared.append(i+1)
    checks.append(dict(name='共边',status='已检查' if neighbors is not None and g.is_valid else '未检查',detail={'neighborIndexes':shared,'note':'共边为关系结果，不自动判定为错误'}))
    return dict(valid=g.is_valid,reason=reason,bounds=list(g.bounds),checks=checks,complete=all(x['status']!='未检查' for x in checks),scope='按输入图形及同坐标系边界检查；缺少依据的项目明确标为未检查')
