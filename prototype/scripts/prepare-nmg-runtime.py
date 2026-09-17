"""Normalize the extracted demo geometry; retain unmodified originals alongside it."""
import runpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
conversion=runpy.run_path(str(root/'scripts/import-demo-map.py'))
convert=conversion['coordinates']
p=root/'assets/nmg-demo/data'
n=json.loads((p/'nmg_nr.json').read_text())
meta={l['id']:l for l in n['LAYERS']}
layers=[]
towns=json.loads((p/'nmg_town.json').read_text())
for m in n['LAYERS']:
    records=[]
    for f in n['FEATURES']:
        if f['layer']!=m['id']:continue
        shape={'type':'Point','coordinates':convert(f['c'])} if m['geom']=='point' else {'type':'LineString' if m['geom']=='line' else 'Polygon','coordinates':convert(f['geom']) if m['geom']=='line' else [convert(f['geom'])]}
        records.append(dict(id=f['id'],name=f['name'],geometry=shape,coordinates=shape['coordinates'][0] if shape['type']=='Polygon' else [],region=f['city'],county=f.get('county',''),source='内蒙古一张图demo · 模拟演示数据',area=f.get('area_mu'),unit='亩',properties=f))
    if m['id']=='town':
        for t in towns:
            records.append(dict(id=t['id'],name=t['name'],geometry=dict(type='Point',coordinates=convert(t['c'])),coordinates=[],region=t['city'],county=t['county'],source='内蒙古一张图demo · 乡镇演示点位',area=None,unit='',properties=t))
    layers.append(dict(id='nmg:'+m['id'],resourceId='nmg:'+m['id'],name=m['name'],displayColor=m['color'],access='已授权',visible=m['id'] in ['landUsePatch','mineralBlock','ecoRedline','geoHazard'],opacity=.8,features=records,theme=m['module'],year=2025,source='内蒙古一张图demo'))
result=dict(id='nmg-reference-demo',name='内蒙古自然资源全域图（demo）',version=1,referenceDemo=True,extraLayers=[],droppedLayers=0,config=dict(defaultBase='demo-img',extent=[97,37,126.1,53.5],panorama=[97,37,126.1,53.5],crs='EPSG:4326',layers=layers,widgets=[dict(code='measure')],basemaps=[dict(id='base-gray',name='浅色底图',style='gray'),dict(id='base-terrain',name='自然地理',style='forest')]),reference=dict(meta=n['META'],stats=json.loads((p/'nmg_stats.json').read_text()),series=n['SERIES'],countyStats=n['COUNTY_STATS'],modules=json.loads((p/'nmg_modules.json').read_text())))
(p/'runtime.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
print('Prepared reference runtime:',len(layers),'layers;',sum(len(l['features']) for l in layers),'features')
