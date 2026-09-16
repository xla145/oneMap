"""Exports are built from exactly the saved result snapshot."""
import csv
import html
import io
import json
from capabilities import require

def export(job,format):
    result=json.loads(job['result']);esc=lambda v:html.escape(str(v))
    if format=='geojson':
        return dict(filename='分析冲突结果.geojson',mime='application/geo+json',content=json.dumps(result['conflicts'],ensure_ascii=False,indent=2))
    if format=='csv':
        f=io.StringIO();w=csv.writer(f);w.writerow(['地块','核查项','状态','空间关系','面积（平方米）','比例（%）','说明'])
        for r in result['rows']:
            cells=[r['name'],r['rule'],r['state'],r['relation'],r['area'],r['percent'],r['reason']]
            w.writerow(["'"+x if isinstance(x,str) and x.startswith(('=','+','-','@','\t','\r','\n')) else x for x in cells])
        return dict(filename='核查明细.csv',mime='text/csv',content='\ufeff'+f.getvalue())
    require(format=='html','不支持的导出格式')
    rows=''.join('<tr>'+''.join('<td>'+esc('—' if r[k] is None else round(r[k],4) if isinstance(r[k],float) else r[k])+'</td>' for k in ['name','rule','state','relation','area','percent','reason'])+'</tr>' for r in result['rows'])
    # A self-contained geographic sketch keeps the report usable offline.
    features=result['input']['features'];bounds=[]
    def rings(g):return g['coordinates'] if g['type']=='Polygon' else [ring for p in g['coordinates'] for ring in p] if g['type']=='MultiPolygon' else [ring for part in g.get('geometries',[]) for ring in rings(part)] if g['type']=='GeometryCollection' else []
    for f in features:
        for ring in rings(f['geometry']):bounds.extend(ring)
    xmin=min(p[0] for p in bounds);xmax=max(p[0] for p in bounds);ymin=min(p[1] for p in bounds);ymax=max(p[1] for p in bounds)
    scale=min(700/max(xmax-xmin,.001),320/max(ymax-ymin,.001))
    def path(g,color):
        d=' '.join('M '+' L '.join(f'{20+(x-xmin)*scale:.2f},{350-(y-ymin)*scale:.2f}' for x,y in ring)+' Z' for ring in rings(g))
        return f'<path d="{d}" fill="{color}" fill-opacity=".3" stroke="{color}" fill-rule="evenodd"/>'
    svg=''.join(path(f['geometry'],'#276ce0') for f in features)+''.join(path(f['geometry'],'#c43a36') for f in result['conflicts']['features'])
    content=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>地块核查报告</title><style>body{{font:14px sans-serif;margin:32px;color:#20342d}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:8px;text-align:left}}svg{{max-width:100%;border:1px solid #ddd}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}@media print{{button{{display:none}}}}</style><h1>{esc(job['name'])} · 核查报告</h1><p>{esc(result['label'])}</p><h2>{esc(result['state'])}</h2><p>任务：{esc(job['id'])} · 创建：{esc(job['created'])}</p><p>数据/规则：{esc(result['version'])} · 算法：analysis-v1 · 面积：EPSG:6933 等积投影，平方米</p><svg viewBox="0 0 760 380" aria-label="地块与冲突示意图">{svg}</svg><p>蓝色：输入地块；红色：冲突范围。位置示意图，无底图。</p><table><thead><tr><th>地块</th><th>核查项</th><th>状态</th><th>关系</th><th>面积㎡</th><th>比例%</th><th>说明</th></tr></thead><tbody>{rows}</tbody></table><h2>输入与去重面积汇总</h2><pre>{esc(json.dumps(result['parcels'],ensure_ascii=False,indent=2))}</pre><details><summary>可追溯数据与规则快照</summary><pre>{esc(json.dumps(result,ensure_ascii=False,indent=2))}</pre></details><p>可使用浏览器打印功能保存 PDF。</p></html>'''
    return dict(filename='地块核查报告.html',mime='text/html',content=content)
