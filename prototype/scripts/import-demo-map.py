"""Extract the supplied demo's public map configuration and administrative data."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'bak' / '内蒙古一张图demo'
html = (SOURCE / '内蒙古自然资源一张图.html').read_text()
match = re.search(r"const\s+TK\s*=\s*(['\"])([^'\"]+)\1", html)
if not match:
    raise RuntimeError('Demo browser map key was not found')


def forward(lng, lat):
    if lng < 72.004 or lng > 137.8347 or lat < .8293 or lat > 55.8271:
        return lng, lat
    x, y = lng - 105, lat - 35
    a = -100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*math.sqrt(abs(x))
    b = 300 + x + 2*y + .1*x*x + .1*x*y + .1*math.sqrt(abs(x))
    common = (20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    a += common + (20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3 + (160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
    b += common + (20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3 + (150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
    rad = lat / 180 * math.pi
    magic = 1 - .00669342162296594323 * math.sin(rad)**2
    a = a*180 / ((6378245*(1-.00669342162296594323))/(magic*math.sqrt(magic))*math.pi)
    b = b*180 / (6378245/math.sqrt(magic)*math.cos(rad)*math.pi)
    return lng+b, lat+a


def inverse(point):
    # Source labels these administrative coordinates as GCJ-02. TianDiTu is
    # geographic/Web Mercator, not GCJ-02; remove the demo's offset assumption.
    lng, lat = point[:2]
    x, y = lng, lat
    for _ in range(4):
        a, b = forward(x, y)
        x -= a-lng
        y -= b-lat
    return [round(x, 8), round(y, 8), *point[2:]]


def coordinates(value):
    if isinstance(value[0], (int, float)):
        return inverse(value)
    return [coordinates(child) for child in value]


data = {}
for name, filename in [('province','nmg_province.geojson'),('cities','nmg_cities.geojson'),('counties','nmg_counties.geojson'),('centers','nmg_centers.geojson')]:
    fc = json.loads((SOURCE / filename).read_text())
    for feature in fc['features']:
        feature['geometry']['coordinates'] = coordinates(feature['geometry']['coordinates'])
    data[name] = fc
out = ROOT / 'frontend/demo-map-data.js'
out.write_text('// Extracted from 内蒙古一张图demo; approximate GCJ-02 to geographic conversion.\nexport const demoMapData = '+json.dumps(data, ensure_ascii=False, separators=(',',':'))+';\n')
(ROOT / 'frontend/demo-map-config.js').write_text('// Reuses the supplied demo public browser map key.\nexport const demoMapKey = '+json.dumps(match.group(2))+';\n')
print('Imported demo TianDiTu configuration and administrative features:', {k:len(v['features']) for k,v in data.items()})
