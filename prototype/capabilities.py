"""Executable local demo capabilities. No remote model or production connectors."""
import ast
import csv
import io
import json
import math
import operator
import re
import sqlite3
import unicodedata
from collections import Counter
from copy import deepcopy
from datetime import datetime

class Invalid(Exception):
    def __init__(self, message, status=400): self.message, self.status = message, status

def require(ok, message, status=400):
    if not ok: raise Invalid(message, status)

def find(rows, ident): return next((r for r in rows if r['id'] == ident), None)
def published(r): return deepcopy(r.get('published')) if r and r.get('status') != '已停用' and not r.get('suspended') else None
def active(s, e): return [p for r in s[e] if (p := published(r))]
def ids(value): return [v.strip() for v in str(value or '').split(',') if v.strip()]
def visible(u, r):
    return u['role'] == '平台管理员' or (r.get('visibility', '业务用户') != '管理员' and (not ids(r.get('departments')) or u['department'] in ids(r.get('departments'))) and (u['region']=='全区' or r.get('region','全区') in ['全区',u['region']]))
def sharing_policy(r):
    # Legacy “已授权” was an open-use policy, never a personal grant.
    return r.get('sharingPolicy') or ('开放使用' if r.get('access')=='已授权' else '申请使用')

def grant_valid(g,u,r):
    return (g['userId']==u['id'] and g['resourceId']==r['id']
            and g.get('status','有效')=='有效'
            and g['validUntil']>=datetime.now().date().isoformat())

def authorized(s,u,r):
    return visible(u,r) and (u['role']=='平台管理员' or (sharing_policy(r)!='限制使用' and (sharing_policy(r)=='开放使用' or any(grant_valid(g,u,r) for g in s['grants']))))

def knowledge_channel(row, channel):
    if not row or row.get('status')=='已停用' or row.get('suspended'):return None
    channels=row.get('channels')
    return deepcopy(channels.get(channel)) if channels is not None else published(row)

def vector(text):
    text=re.sub(r'\s+', '', text.lower())
    return dict(Counter(text[i:i+2] for i in range(len(text)-1)))
def similarity(a,b):
    den=math.sqrt(sum(v*v for v in a.values()) * sum(v*v for v in b.values()))
    return sum(v*b.get(k,0) for k,v in a.items())/den if den else 0

def clean_document(body):
    require(isinstance(body,str) and len(body.encode('utf-8'))<=200*1024,'正文不能超过 200KB（UTF-8）')
    original=body
    body=unicodedata.normalize('NFKC',body.replace('\r\n','\n').replace('\r','\n')).replace('\u200b','').replace('\ufeff','')
    blocks=[];seen=set();duplicates=0
    for block in re.split(r'\n\s*\n',body):
        block='\n'.join(line.strip() for line in block.splitlines()).strip()
        if not block: continue
        if block in seen: duplicates+=1;continue
        blocks.append(block);seen.add(block)
    body='\n\n'.join(blocks)
    return dict(body=body,before=len(original),after=len(body),duplicates=duplicates,changed=body!=original)

def graph(row):
    nodes=[];edges=[]
    for line in row.get('entities','').splitlines():
        if not line.strip(): continue
        parts=[x.strip() for x in line.split('|')];require(len(parts)==3 and all(parts),'实体格式：标识|名称|类型')
        require(re.fullmatch(r'[A-Za-z0-9_-]+',parts[0]),'实体标识只能包含字母数字、下划线或短横线')
        require(parts[0] not in [n['id'] for n in nodes],'实体标识重复')
        nodes.append(dict(id=parts[0],name=parts[1],type=parts[2]))
    for line in row.get('edges','').splitlines():
        if not line.strip():continue
        parts=[x.strip() for x in line.split('|')];require(len(parts)==3 and all(parts),'关系格式：起点标识|关系名称|终点标识')
        require(parts[0] in [n['id'] for n in nodes] and parts[2] in [n['id'] for n in nodes],'关系端点必须是已有实体')
        edges.append(dict(source=parts[0],label=parts[1],target=parts[2]))
    require(len(nodes)<=60 and len(edges)<=120,'图谱最多 60 个实体、120 条关系')
    return dict(nodes=nodes,edges=edges)

def process_document(row):
    cleaned=clean_document(row['body']); require(cleaned['body'],'清洗后文档不能为空')
    try: size=int(row.get('chunkSize') or 400)
    except (ValueError,TypeError): raise Invalid('切片长度应为 100–2000')
    require(100<=size<=2000,'切片长度应为 100–2000')
    row['body']=cleaned['body']; row['cleaning']=cleaned | {'body':None}
    chunks=[]
    for block in row['body'].split('\n\n'):
        for start in range(0,len(block),size):
            text=block[start:start+size];chunks.append(dict(id=f"{row['id']}-c{len(chunks)+1}",text=text,vector=vector(text)))
    row.update(chunks=chunks,graph=graph(row),process='可用',indexMode='本地字符二元特征向量',pipeline=[dict(name=n,status='完成') for n in ['读取','规范化与去重','切片','本地向量索引','图谱校验']])
    return row

def search_knowledge(s,u,q,bindings='',rows=None):
    query=vector(q);result=[]
    for d in (rows if rows is not None else [v for r in s['knowledge'] if (v:=knowledge_channel(r,'index'))]):
        if not visible(u,d) or (ids(bindings) and d['id'] not in ids(bindings)):continue
        chunks=[]
        for c in d.get('chunks',[]):
            score=similarity(query,c.get('vector') or vector(c['text']))
            if score>=0.065 or (q and q in c['text']):chunks.append({**c,'score':round(score,4)})
        if chunks:
            chunks.sort(key=lambda x:x['score'],reverse=True)
            result.append(dict(documentId=d['id'],name=d['name'],version=d.get('version',0),chunks=[{k:v for k,v in c.items() if k!='vector'} for c in chunks[:3]],score=chunks[0]['score']))
    return sorted(result,key=lambda x:x['score'],reverse=True)[:3]

def data_rows(resource):
    reader=csv.DictReader(io.StringIO(resource.get('dataRows','')))
    rows=list(reader);require(len(rows)<=2000,'示例表最多 2000 行')
    require(not rows or (reader.fieldnames and len(set(reader.fieldnames))==len(reader.fieldnames) and None not in reader.fieldnames),'数据列名重复或无效')
    require(all(None not in r and None not in r.values() for r in rows),'CSV 列数不一致')
    return rows

def calculate(s,row,u=None,context=None,stack=()):
    require(row['id'] not in stack and len(stack)<8,'指标存在循环依赖或依赖过深')
    require(not u or visible(u,row),'无权访问该指标',403)
    ctx=dict(context or {}); mode=row.get('dataMode','manual');deps=[]
    if u and u['role']!='平台管理员' and u['region']!='全区':
        require(ctx.get('region','全区') in ['全区',u['region']],'不能计算权限区域之外的数据',403)
        ctx['region']=u['region']
    if mode=='composite':
        formula=row.get('expression','');require(0<len(formula)<=300,'请填写不超过 300 字的算术表达式')
        try: tree=ast.parse(formula,mode='eval')
        except SyntaxError: raise Invalid('表达式语法错误')
        operators={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
        def visit(n):
            if isinstance(n,ast.Expression):return visit(n.body)
            if isinstance(n,ast.Constant) and type(n.value) in (int,float):return n.value
            if isinstance(n,ast.Name):
                target=published(find(s['indicators'],n.id));require(target,'依赖指标未发布：'+n.id)
                r=calculate(s,target,u,ctx,stack+(row['id'],));deps.append(dict(id=n.id,name=r['name'],value=r['value'],version=r['version']));return r['value']
            if isinstance(n,ast.BinOp) and type(n.op) in operators:
                a,b=visit(n.left),visit(n.right)
                require(not isinstance(n.op,ast.Div) or b!=0,'指标表达式不能除以零')
                return operators[type(n.op)](a,b)
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return visit(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
            raise Invalid('仅支持指标标识、数字、括号和 + - * /')
        value=visit(tree);values=[d['value'] for d in deps] or [value];source='已发布指标依赖'
    else:
        r=published(find(s['resources'],row.get('resourceId')));require(r,'关联资源未发布')
        require(not u or authorized(s,u,r),'关联数据未授权',403)
        f=next((f for f in r.get('fields',[]) if f['name']==row.get('field')),None);require(f,'关联字段不存在')
        if mode=='table':
            require(f.get('statistic') or f.get('aggregate'),'该字段未启用统计或汇总')
            rows=data_rows(r);region=ctx.get('region',row.get('region','全区'));period=ctx.get('period',row.get('period',''))
            if u and u['role']!='平台管理员' and u['region']!='全区':
                require(region in ['全区',u['region']],'不能计算权限区域之外的数据',403)
                region=u['region']
            rows=[x for x in rows if (region=='全区' or x.get('region')==region) and (period in ['','全部时间','最近30天'] or x.get('period')==period)]
            require(rows,'所选区域/周期没有数据')
            try:values=[float(x[row['field']]) for x in rows]
            except (ValueError,KeyError):raise Invalid('数据字段缺失或包含非数字')
            source=r['name']+' / '+row['field']
        else:
            try:values=[float(x.strip()) for x in row.get('values','').split(',')]
            except ValueError:raise Invalid('请输入英文逗号分隔的数字')
            source='手动试算数据'
        require(values and all(math.isfinite(x) for x in values),'试算数据必须为有限数字')
        funcs={'sum':sum,'average':lambda a:sum(a)/len(a),'count':len,'max':max}
        require(row.get('formula') in funcs,'请选择受控计算模型');value=funcs[row['formula']](values)
    require(math.isfinite(value) and abs(value)<1e18,'指标结果超出支持范围')
    return dict(id=row['id'],name=row['name'],value=round(value,2),values=values,unit=row.get('unit',''),caliber=row.get('caliber',''),period=ctx.get('period',row.get('period','')),region=ctx.get('region',row.get('region','全区')),version=row.get('version',0),source=source,dependencies=deps,knowledgeIds=ids(row.get('knowledgeIds')))

def dictionary_items(row):
    out=[]
    for line in row.get('items','').splitlines():
        if not line.strip():continue
        parts=line.split(':',2);require(len(parts)>=2 and parts[0].strip() and parts[1].strip(),'字典项格式：编码:名称:值')
        out.append(dict(code=parts[0].strip(),name=parts[1].strip(),value=parts[2].strip() if len(parts)==3 else parts[0].strip()))
    require(len({x['code'] for x in out})==len(out),'字典项编码不能重复');return out

def relation_edges(s,row):
    out=[]
    for line in row.get('relationRules','').splitlines():
        if not line.strip():continue
        p=[x.strip() for x in line.split('|')];require(len(p)==4,'资源关系格式：类型|目标资源标识|本字段|目标字段')
        typ,target,left,right=p;r=find(s['resources'],target)
        require(typ in ['表关联','图层数据源'] and r and target!=row.get('id'),'关系类型或目标资源无效')
        if typ=='表关联':
            require(left in [f['name'] for f in row.get('fields',[])] and right in [f['name'] for f in r.get('fields',[])],'表关系关联字段不存在')
        else:require(row.get('type')=='图层服务' and r.get('type')=='数据库表','图层数据源必须由图层关联数据库表')
        out.append(dict(type=typ,target=target,sourceField=left,targetField=right))
    return out

def semantic_text(s,r):
    texts=[str(r.get(k,'')) for k in ['name','aliases','category','description']];aliases=ids(r.get('aliases'))
    for f in r.get('fields',[]):
        if not f.get('query'):continue
        texts += [str(f.get(k,'')) for k in ['name','label','alias','description','topic']]
        aliases+=ids(f.get('alias'))
        d=next((x for x in active(s,'dictionaries') if f.get('dictionary') in [x['id'],x['name'],x['code']]),None)
        if d:
            aliases+=ids(d.get('aliases'))
            for item in dictionary_items(d): aliases += list(item.values())
    return ' '.join(texts+aliases),aliases

def render_template(body,params):
    def sub(m):
        key=m.group(1);require(key in params,'缺少模板参数：'+key);return str(params[key])
    return re.sub(r'\{\{\s*(\w+)\s*\}\}',sub,body)

def template_trial(s,u,row,params):
    for key in ids(row.get('variables')):require(str(params.get(key,'')).strip(),'缺少参数：'+key)
    if row['type']=='API 模板':
        require(row.get('body')=='resources.search','仅支持本地 resources.search 接口')
        q=str(params.get('question',''));rows=[r for r in active(s,'resources') if visible(u,r) and (not ids(row.get('resourceIds')) or r['id'] in ids(row['resourceIds'])) and (params.get('region','全区')=='全区' or r['region'] in ['全区',params['region']]) and (q in semantic_text(s,r)[0] or any(a in q for a in semantic_text(s,r)[1]))]
        return dict(preview='resources.search',mode='本地 API 已执行',rows=[dict(id=r['id'],name=r['name'],type=r['type']) for r in rows])
    if row['type']!='SQL 模板':return dict(preview=render_template(row['body'],params),answer=row.get('answer',''),mode='模板参数已替换')
    sql=row['body'].strip();require(re.match(r'^SELECT\s',sql,re.I) and ';' not in sql,'仅支持单条只读 SELECT')
    with sqlite3.connect(':memory:') as conn:
        for r in active(s,'resources'):
            if not authorized(s,u,r) or (ids(row.get('resourceIds')) and r['id'] not in ids(row['resourceIds'])):continue
            name=r.get('sqlName','');rows=data_rows(r)
            if u['role']!='平台管理员' and u['region']!='全区':rows=[x for x in rows if x.get('region')==u['region']]
            if not name or not rows:continue
            require(re.fullmatch(r'[a-zA-Z_][\w]*',name),'数据表名格式错误')
            columns=list(rows[0]);require(all(re.fullmatch(r'[a-zA-Z_]\w*',k) for k in columns),'数据列名格式错误')
            conn.execute('CREATE TABLE "'+name+'" ('+','.join('"'+k+'"' for k in columns)+')')
            conn.executemany('INSERT INTO "'+name+'" VALUES ('+','.join('?' for _ in columns)+')',[[x[k] for k in columns] for x in rows])
        ticks=[0]
        def progress(): ticks[0]+=1;return ticks[0]>1000
        conn.set_progress_handler(progress,1000)
        conn.set_authorizer(lambda op,*args: sqlite3.SQLITE_OK if op in [sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION] and not (op==sqlite3.SQLITE_FUNCTION and args[1]=='load_extension') else sqlite3.SQLITE_DENY)
        try:
            cur=conn.execute(sql,params);data=[dict(zip([d[0] for d in cur.description],x)) for x in cur.fetchmany(101)]
        except sqlite3.Error as e:raise Invalid('SQL 试运行失败：'+str(e))
        finally:conn.set_authorizer(lambda *args: sqlite3.SQLITE_OK)
    return dict(preview=sql,mode='本地授权示例表只读查询',rows=data[:100],truncated=len(data)>100)

def migrate(s):
    """Additive, idempotent upgrade. Existing values and history are retained."""
    if s.get('schemaVersion',0)>=2:return s
    s.setdefault('batches',[]);s.setdefault('evaluations',[]);s.setdefault('feedbackDrafts',[])
    for entity in ['resources','knowledge','indicators','corpora','agents','templates','dictionaries']:
        for record in s[entity]:
            for r in [record]+([record['published']] if record.get('published') else []):
                if entity in ['knowledge','indicators','agents']:r.setdefault('visibility','业务用户');r.setdefault('departments','');r.setdefault('region','全区')
                if entity=='resources':
                    r.setdefault('subtype','属性表' if r['type']=='数据库表' else r['type']);r.setdefault('sourceType','库表' if r['type']=='数据库表' else '服务');r.setdefault('relationRules','');r.setdefault('departments','')
                    if r['id']=='r2':
                        r.setdefault('sqlName','demo_cropland');r.setdefault('dataRows','period,region,area,target\n2025年,呼和浩特市,350,420\n2026年,呼和浩特市,400,420\n2025年,包头市,250,300\n2026年,包头市,280,300')
                        if not any(f['name']=='target' for f in r['fields']):r['fields'].append(dict(name='target',label='保护目标',alias='目标面积',type='decimal',unit='公顷',query=True,display=True,statistic=True,aggregate=True))
                if entity=='knowledge':
                    r.setdefault('chunkSize',400)
                    if not r.get('entities'):
                        names=list(dict.fromkeys(x.strip() for x in r.get('relations','').split('→') if x.strip()))
                        r['entities']='\n'.join(f'n{i}|{name}|业务概念' for i,name in enumerate(names));r['edges']='\n'.join(f'n{i}|关联|n{i+1}' for i in range(len(names)-1))
                    original_body=r['body'];original_chunks=deepcopy(r.get('chunks',[]))
                    process_document(r)
                    r['body']=original_body
                    if original_chunks:r['chunks']=[{**c,'vector':vector(c['text'])} for c in original_chunks]
                if entity=='templates':r.setdefault('fieldSchema','region_code|行政区代码|varchar|区划编码\narea|面积|decimal|用地面积')
                if entity=='corpora':r.setdefault('outputTemplate','为你找到 {{count}} 项相关资源：{{resources}}。' if r['id']=='c1' else '')
                if entity=='indicators':r.setdefault('dataMode','manual')
    def add(e,ident,name,**kw):
        if find(s[e],ident):return
        r=dict(id=ident,name=name,status='已发布',rev=1,version=1,updated=datetime.now().isoformat(),**kw);r['published']=deepcopy(r);r['versions']=[];s[e].append(r)
    base=dict(category='耕地保护',unit='公顷',formula='sum',values='',caliber='按统计年度和行政区汇总示例表面积。',period='2026年',region='全区',resourceId='r2',field='area',dataMode='table',visibility='业务用户',knowledgeIds='k1')
    add('indicators','i_area','年度耕地面积',**base)
    add('indicators','i_target','耕地保护目标',**{**base,'field':'target'})
    add('indicators','i_rate','耕地保护达标指数',**{**base,'unit':'%','dataMode':'composite','expression':'i_area / i_target * 100','caliber':'实际耕地面积 ÷ 保护目标 × 100；示例绩效指标。'})
    add('corpora','c_api','耕地资源 API 查询',type='API 模板',scene='资源检索',body='resources.search',variables='question,region',answer='',resourceIds='r2,r4',category='耕地保护')
    add('agents','a_team','耕地保护协同助手',category='资源检索',description='串联资源、知识与指标，查看每一步的输入与输出。',icon='layers',color='blue',question='分析耕地保护',steps='识别条件\n检索资源\n调用知识智能体\n调用指标智能体\n展示结果\n发起申请',resourceIds='r2,r4,r5,r11',knowledgeIds='k1',templateIds='c1',indicatorIds='i_area,i_rate',knowledgeAgentId='a2',indicatorAgentId='a3',memory=True,visibility='业务用户')
    for r in s['agents']:
        if r['id']=='a3':
            for x in [r]+([r['published']] if r.get('published') else []):
                x['indicatorIds']=','.join(dict.fromkeys(ids(x.get('indicatorIds'))+['i_area','i_target','i_rate']))
    for m in s['memories']:m.setdefault('skill','业务熟悉');m.setdefault('facts',[]);m.setdefault('history',[])
    s['schemaVersion']=2;return s
