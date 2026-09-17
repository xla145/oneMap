"""Versioned synthetic-data analysis. Never a regulatory approval service."""
import json
import math
from copy import deepcopy
from shapely.geometry import shape, mapping, box
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
from pyproj import Transformer
import pyproj
import shapely
from capabilities import require

VERSION = 'synthetic-2026-09-v1'
CRS = 'EPSG:4326'
PROJECT = Transformer.from_crs(CRS, 'EPSG:6933', always_xy=True).transform
UNPROJECT = Transformer.from_crs('EPSG:6933', CRS, always_xy=True).transform
LABEL = '人工构造示例数据与规则，仅供功能体验，不是正式管控数据或审批结论'

def feature(geom, **props):
    return {'type':'Feature','geometry':mapping(geom),'properties':props}

def catalog():
    return {'version':VERSION,'algorithm':'analysis-v1','engineVersions':{'shapely':shapely.__version__,'pyproj':pyproj.__version__},'label':LABEL,'coverage':mapping(box(111.5,40.5,112,41)),
      'layers':[
        {'id':'redline','name':'示例生态红线','geometry':mapping(box(111.65,40.7,111.73,40.79)),'kind':'exclude'},
        {'id':'farmland','name':'示例永久基本农田','geometry':mapping(box(111.71,40.76,111.79,40.85)),'kind':'exclude'},
        {'id':'planning','name':'示例规划允许建设范围','geometry':mapping(box(111.6,40.6,111.9,40.95)),'kind':'inside'}],
      'sample':{'type':'FeatureCollection','features':[feature(box(111.7,40.75,111.76,40.81),id='parcel-1',name='冲突示例地块'),feature(box(111.82,40.86,111.85,40.89),id='parcel-2',name='无冲突示例地块')]}}

def normalize(value, crs):
    require(crs in ('EPSG:4326','EPSG:3857'),'请选择 EPSG:4326 或 EPSG:3857；暂不支持其他测绘基准')
    if isinstance(value,str):
        require(len(value.encode())<=10*1024*1024,'输入不能超过 10 MB',413)
        try:value=json.loads(value)
        except (ValueError,TypeError):require(False,'请输入有效 GeoJSON 或坐标数组')
    if isinstance(value,list): value={'type':'Polygon','coordinates':[value]}
    require(isinstance(value,dict),'输入必须是 GeoJSON 或坐标数组')
    require('crs' not in value,'请移除旧版 GeoJSON crs 字段，并在页面明确选择坐标系')
    rows=value.get('features') if value.get('type')=='FeatureCollection' else [value if value.get('type')=='Feature' else {'type':'Feature','geometry':value}]
    require(isinstance(rows,list) and 0<len(rows)<=100,'需包含 1～100 个地块')
    output=[]; count=0; ids=set()
    convert=Transformer.from_crs(crs,CRS,always_xy=True).transform
    for index,row in enumerate(rows):
        prefix=f'第 {index+1} 个地块：'
        require(isinstance(row,dict) and row.get('type')=='Feature',prefix+'要素格式错误')
        geom=row.get('geometry');require(isinstance(geom,dict) and geom.get('type') in ('Polygon','MultiPolygon'),prefix+'仅支持 Polygon/MultiPolygon')
        def coordinates(v):
            nonlocal count
            require(isinstance(v,list) and v,prefix+'坐标不能为空')
            if isinstance(v[0],(int,float)):
                count+=1
                require(len(v)==2 and all(type(n) in (int,float) and math.isfinite(n) for n in v),prefix+'坐标必须是两个有限数值')
                require(count<=50000,'总顶点不能超过 50000')
                if crs==CRS:require(abs(v[0])<=180 and abs(v[1])<=85,prefix+'经纬度超出范围')
                else:require(abs(v[0])<=20037508.35 and abs(v[1])<=19971868.89,prefix+'Web Mercator 坐标超出范围')
            else:
                for c in v:coordinates(c)
        coordinates(geom.get('coordinates'))
        polygons=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
        for poly in polygons:
            require(isinstance(poly,list) and poly,prefix+'多边形必须包含环')
            for ring in poly:
                require(isinstance(ring,list) and all(isinstance(point,list) and len(point)==2 for point in ring),prefix+'环结构无效')
                require(len(ring)>=4 and ring[0]==ring[-1],prefix+'环必须闭合且至少含 4 个坐标')
        try:g=shape(geom)
        except Exception:require(False,prefix+'几何结构无效')
        require(not g.is_empty and g.is_valid,prefix+'几何无效：'+explain_validity(g))
        g=transform(convert,g)
        require(not g.is_empty and all(math.isfinite(v) for v in g.bounds),prefix+'转换后坐标无效')
        require(g.is_valid and g.bounds[2]-g.bounds[0]<180,prefix+'转换后几何无效或跨日期变更线')
        require(transform(PROJECT,g).area>0.01,prefix+'面积必须大于 0.01 平方米')
        props=row.get('properties') or {};require(isinstance(props,dict),prefix+'属性格式错误')
        ident=str(props.get('id',row.get('id',f'parcel-{index+1}')))[:100]
        require(ident not in ids,prefix+'地块 ID 重复');ids.add(ident)
        output.append(feature(g,id=ident,name=str(props.get('name',ident))[:100]))
    return {'type':'FeatureCollection','features':output}

def analyze(data, snapshot, progress_callback=None):
    coverage=shape(snapshot['coverage']); rows=[]; conflicts=[]; parcels=[]
    for parcel in data['features']:
        if progress_callback:progress_callback(deepcopy(parcels),parcel['properties']['id'])
        g=shape(parcel['geometry']); projected=transform(PROJECT,g); area=projected.area; all_conflicts=[]; states=[]
        for layer in snapshot['layers']:
            state='未发现所选规则冲突'; amount=None; ratio=None; relation='未计算'; conflict=None
            if not layer.get('geometry'): state='无法判定';reason='缺少管控数据'
            elif layer.get('authorized',True) is not True:state='无法判定';reason='无数据使用权限'
            elif layer.get('current',True) is not True:state='无法判定';reason='数据已过期'
            elif not coverage.covers(g):state='无法判定';reason='地块超出示例数据完整覆盖范围'
            else:
                boundary=shape(layer['geometry']); subject=g.difference(boundary) if layer['kind']=='inside' else g.intersection(boundary)
                conflict=transform(PROJECT,subject);amount=conflict.area;ratio=amount/area*100
                relation='面积相交' if amount>0.01 else '边界接触' if g.touches(boundary) else '无面积冲突'
                state='发现冲突' if amount>0.01 else '需人工复核' if relation=='边界接触' else state
                reason='示例规则：规划允许范围外为冲突' if layer['kind']=='inside' else '示例规则：与管控范围有面积交叠为冲突，边界接触需复核'
                if amount>0.01:
                    all_conflicts.append(conflict)
                    conflicts.append(feature(subject,parcelId=parcel['properties']['id'],rule=layer['name'],kind='conflict'))
            states.append(state)
            rows.append(dict(parcelId=parcel['properties']['id'],name=parcel['properties']['name'],rule=layer['name'],state=state,reason=reason,relation=relation,area=amount,percent=ratio))
        conclusion=next((s for s in ['无法判定','发现冲突','需人工复核'] if s in states),'未发现所选规则冲突') if states else '无法判定'
        parcels.append(dict(**parcel['properties'],area=area,conflictArea=unary_union(all_conflicts).area if all_conflicts else 0,state=conclusion))
        if progress_callback:progress_callback(deepcopy(parcels),None)
    states=[p['state'] for p in parcels]
    conclusion=next((s for s in ['无法判定','发现冲突','需人工复核'] if s in states),'未发现所选规则冲突')
    return dict(version=snapshot['version'],label=LABEL,calculationCRS='EPSG:6933',state=conclusion,rows=rows,parcels=parcels,conflicts={'type':'FeatureCollection','features':conflicts},input=deepcopy(data),snapshot=snapshot)

def spatial_tool(data,operation,distance=0):
    """Polygon tools use complete geometries (including holes), not outer rings."""
    require(operation in ('intersection','difference','union','area','buffer'),'不支持的空间运算')
    geometries=[shape(f['geometry']) for f in data['features']]
    if operation in ('intersection','difference'):require(len(geometries)==2,'相交与差集需输入两个地块，按输入顺序计算 A 与 B')
    if operation=='intersection':result=geometries[0].intersection(geometries[1])
    elif operation=='difference':result=geometries[0].difference(geometries[1])
    else:result=unary_union(geometries)
    if operation=='buffer':
        require(type(distance) in (int,float) and math.isfinite(distance) and 0<distance<=100000,'缓冲距离应大于 0 且不超过 100000 米')
        center=result.centroid
        local=f'+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m'
        require(result.bounds[2]-result.bounds[0]<=2 and result.bounds[3]-result.bounds[1]<=2,'面缓冲体验限经纬跨度各不超过 2 度，较大区域需正式计算方案')
        forward=Transformer.from_crs(CRS,local,always_xy=True).transform
        backward=Transformer.from_crs(local,CRS,always_xy=True).transform
        result=transform(backward,transform(forward,result).buffer(distance))
    area=transform(PROJECT,result).area
    return {'type':'FeatureCollection','features':[] if result.is_empty else [feature(result,operation=operation,areaSquareMeters=area,algorithm='spatial-v1',inputCRS=CRS,calculationCRS='EPSG:6933',note='空间计算体验；面缓冲使用局部等距投影')], 'areaSquareMeters':area,'empty':result.is_empty}
