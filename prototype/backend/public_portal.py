"""Public portal content and citizen feedback, persisted with the legacy state."""
from copy import deepcopy
from datetime import datetime
import csv
import io
import json
import uuid
from urllib.parse import urlparse
import capabilities as cap
from capabilities import require, Invalid
from platform_seed import versioned


def now(): return datetime.now().isoformat(timespec='seconds')
def find(rows, key): return next((r for r in rows if r['id'] == key), None)
def text(value, limit=5000):
    require(isinstance(value, str) and len(value) <= limit, '文本格式或长度不正确')
    return value.strip()
def admin(user): require(user['role'] == '平台管理员', '需要平台管理员身份', 403)
def active(rows): return [deepcopy(r['published']) for r in rows if r.get('published') and r['status'] != '已停用' and not r.get('suspended')]


def migrate(state):
    if 'publicPortal' in state:
        return state['publicPortal']
    topics = []
    for ident, name, category, summary, body, cover in [
        ('landscape','自然地理风光','自然地理','从草原到沙漠，认识北疆的自然之美。','内蒙古横跨东北、华北和西北，草原、森林、沙漠、河流与湖泊共同构成多样的自然地理景观。\n\n本专题以行政区地图提供空间认知入口。具体景观位置、影像和专题数据由管理人员补充发布。','map'),
        ('planning','国土空间规划','空间规划','了解空间格局，查阅规划成果与公开信息。','从生态、农业与城镇空间理解国土空间规划。查阅规划成果时，请核对成果版本、适用范围及发布单位。\n\n当前展示为专题介绍示例，正式规划图集和管控数据待发布。','project'),
        ('energy','重要能源保障基地','能源资源','认识煤炭、稀土、风能与太阳能等资源。','能源资源专题围绕重要能源与战略资源的空间分布、开发利用和绿色转型组织内容。\n\n正式资源分布图与统计指标待业务单位提供，当前不展示虚构储量。','data'),
        ('public','社会公众服务','便民服务','发现身边的自然资源公共服务。','汇集公共服务站点、地质灾害避险场所等便民信息，通过地图与办事入口提供服务。\n\n站点和避险场所的实际位置与开放信息待业务单位核实后发布。','consult'),
        ('ecology','北疆安全生态屏障','生态保护','了解生态工程与绿色发展。','围绕“三北”防护林、京津风沙源治理、湿地保护恢复等生态工程，介绍生态保护与修复。\n\n工程范围、成效图表和专题影像待正式资料发布。','cropland')]:
        topics.append(versioned(ident,name,category=category,summary=summary,body=body,cover=cover,resourceIds=[],url='',source='门户专题示例',order=len(topics)+1))
    services=[]
    for ident,name,category,summary,body,kind in [
        ('estate','不动产登记信息查询','不动产','查询权属、面积和抵押状态。','正式查询需接入自治区不动产登记平台并完成身份核验。当前可查看服务说明和提交咨询。','external'),
        ('progress','用地审批进度查询','用途管制','按项目编号查询本人办件进度。','原型可查询当前演示身份可访问的项目办件；正式用地审批数据待接入。\n示例项目编号：project_demo_1。','progress'),
        ('mining','矿业权信息查询','矿产资源','了解矿业权基本信息和有效期。','矿业权登记查询接口待接入。可先查阅数据服务中的矿业权目录并按需申请。','external'),
        ('notice','国土空间规划公示','规划公示','查看规划信息，提交公众意见。','本条为公示互动流程示例，不是正式规划公示。可提交意见并在“我的咨询与意见”中查看受理和回复。\n正式公示应由管理人员发布公示正文、图件、期限和联系信息。','notice'),
        ('price','地价查询','土地利用','查询基准地价、监测地价信息。','地价数据与查询接口待接入。可通过服务咨询说明需要查询的地区和用途。','external'),
        ('guide','办事指南','办事指南','了解申请流程、材料与办理要求。','数据申请：查找资源 → 查看元数据与使用限制 → 填写用途和期限 → 等待审核 → 在我的申请中查看结果。\n\n政务事项：查阅对应事项指南，按提供方要求准备材料；具体材料、办理时限和咨询电话由业务单位维护。','guide')]:
        services.append(versioned(ident,name,category=category,summary=summary,body=body,kind=kind,url='',source='本地演示服务',order=len(services)+1))
    portal=dict(topics=topics,services=services,tickets=[],downloads=[],settings=versioned('home','公共门户首页',title='自然资源一张图，让数据与服务触手可及',subtitle='面向公众、企事业单位与科研院所，提供数据共享、空间工具、办事服务和资讯下载。',resourceIds=[]))
    state['publicPortal']=portal
    return portal


def bootstrap(state,user,mode):
    p=migrate(state); full=mode=='admin' and user['role']=='平台管理员'
    return dict(topics=deepcopy(p['topics']) if full else active(p['topics']),services=deepcopy(p['services']) if full else active(p['services']),settings=deepcopy(p['settings']) if full else deepcopy(p['settings']['published']),tickets=[deepcopy(t) for t in p['tickets'] if full or t['userId']==user['id']],downloads=[deepcopy(d) for d in p['downloads'] if full or d['userId']==user['id']])


def resource_map(state,user,resource_id=''):
    import platform_domain as platform
    layers=[];seen=set()
    if resource_id:
        r=cap.published(find(state['resources'],resource_id))
        require(r and cap.visible(user,r) and r['type']=='图层服务','图层不可访问',404)
    for app in state['platform']['apps']:
        snapshot=app.get('published') or {}
        if not app.get('listed') or snapshot.get('type')!='scene':continue
        try: runtime=platform.scene_runtime(state,user,{'id':snapshot['targetId']})
        except Invalid:continue
        for layer in runtime['config']['layers']:
            if (not resource_id or layer['resourceId']==resource_id) and layer['resourceId'] not in seen:
                seen.add(layer['resourceId']);layers.append(layer)
    return dict(engine='local-2d',extent=[96,36,127,54],basemaps=[dict(id='base-gray',name='行政区划底图',category='基础底图')],defaultBase='base-gray',widgets=[dict(code='query'),dict(code='measure')],layers=layers)


def execute(state,user,action,payload):
    p=migrate(state)
    if action=='public.map':return resource_map(state,user,payload.get('resourceId',''))
    if action=='public.download':
        r=cap.published(find(state['resources'],payload.get('id')))
        require(r and cap.visible(user,r),'资源不可访问',404)
        require(cap.authorized(state,user,r),'资源未授权或授权已过期',403)
        require(r['type'] in ['数据库表','图层服务'],'该资源不提供数据包下载')
        if r['type']=='图层服务':
            cfg=resource_map(state,user,r['id'])
            features=[dict(type='Feature',properties={k:v for k,v in f.items() if k!='coordinates'},geometry=dict(type='Polygon',coordinates=[f['coordinates']+[f['coordinates'][0]]])) for layer in cfg['layers'] if layer['access']=='已授权' for f in layer['features']]
            require(features,'此资源尚未绑定可下载的图层数据')
            content=json.dumps(dict(type='FeatureCollection',features=features),ensure_ascii=False);ext='geojson';mime='application/geo+json'
        else:
            rows=cap.data_rows(r) or r.get('sample',[])
            if user['region']!='全区':rows=[row for row in rows if row.get('region',row.get('行政区'))==user['region']]
            # Respect field display restrictions, including localized sample columns.
            hidden={key for f in r.get('fields',[]) if not f.get('display',True) for key in [f.get('name'),f.get('label')] if key}
            rows=[{k:v for k,v in row.items() if k not in hidden} for row in rows]
            require(rows and any(rows),'暂无可下载的授权示例记录')
            columns=list(dict.fromkeys(k for row in rows for k in row));stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
            for row in rows:
                writer.writerow({k: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items()})
            content='\ufeff'+stream.getvalue();ext='csv';mime='text/csv'
        record=dict(id=uuid.uuid4().hex[:12],userId=user['id'],resourceId=r['id'],name=r['name'],at=now(),version=r['version'],format=ext.upper());p['downloads'].append(record)
        return dict(filename=r['name']+'-示例数据.'+ext,content=content,mime=mime)
    if action=='public.ticket':
        service=find(active(p['services']),payload.get('serviceId'));require(service,'服务已下架或不存在',404)
        title=text(payload.get('title',''),100);body=text(payload.get('body',''),3000)
        require(title and body,'请填写标题和内容')
        kind='公示意见' if service['kind']=='notice' else '服务咨询'
        key=text(payload.get('requestId',''),100);require(key,'缺少提交标识，请刷新重试')
        old=next((r for r in p['tickets'] if r['userId']==user['id'] and r['requestId']==key),None)
        if old:return deepcopy(old)
        row=dict(id='T'+uuid.uuid4().hex[:10].upper(),requestId=key,userId=user['id'],userName=user['name'],serviceId=service['id'],serviceName=service['name'],kind=kind,title=title,body=body,status='待受理',rev=1,createdAt=now(),history=[])
        p['tickets'].append(row);return deepcopy(row)
    if action=='public.reply':
        admin(user);row=find(p['tickets'],payload.get('id'));require(row,'记录不存在',404)
        require(row['rev']==payload.get('rev'),'记录已更新，请刷新重试',409)
        status=payload.get('status');require(status in ['处理中','已回复'],'处理状态无效')
        require(row['status']!='已回复' or status=='已回复','已回复记录不能退回处理中')
        reply=text(payload.get('reply',''),3000);require(reply,'请填写受理说明或回复')
        row['history'].append(dict(at=now(),actor=user['name'],status=status,body=reply));row.update(status=status,rev=row['rev']+1);return deepcopy(row)
    if action=='public.progress':
        import platform_domain as platform
        key=text(payload.get('query',''),100);require(key,'请输入项目编号或办件编号')
        return [dict(id=c['id'],name=c['name'],projectId=c['projectId'],status=c['status'],updated=c['updated'],steps=[dict(name=n['name'],state='已完成' if c['status']=='已办结' or i<c['nodeIndex'] else '当前节点' if i==c['nodeIndex'] else '未开始') for i,n in enumerate(c['workflow']['nodes'])]) for c in state['platform']['cases'] if key in [c['id'],c['projectId']] and platform.can_case(user,c)]
    if action in ['public.save','public.publish','public.disable','public.delete']:
        admin(user);entity=payload.get('entity');require(entity in ['topics','services','settings'],'未知内容类型')
        row=p['settings'] if entity=='settings' else find(p[entity],payload.get('id'))
        if payload.get('id'):require(row,'内容不存在',404)
        if row:require(row['rev']==payload.get('rev'),'内容已更新，请刷新后重试',409)
        if action=='public.delete':
            require(entity!='settings','首页配置不能删除')
            require(row,'内容不存在',404)
            require(not row.get('published') or row.get('suspended') or row['status']=='已停用','请先下架再删除')
            p[entity].remove(row)
            return dict(id=row['id'],deleted=True)
        if action=='public.save':
            values=payload.get('values');require(isinstance(values,dict),'内容格式错误')
            out=deepcopy(row) if row else dict(id=uuid.uuid4().hex[:12],rev=0,version=0,status='草稿')
            if row and row['status']=='已停用':out['suspended']=True
            fields=['name','summary','body','category','source','url','cover','coverUrl','coverCredit'] if entity!='settings' else ['title','subtitle']
            if entity=='services':fields+=['process','materials','timeLimit','phone']
            for key in fields:
                if key in values:out[key]=text(values[key],10000 if key in ['body','process','materials'] else 300)
            if entity=='services':
                out['kind']=values.get('kind',out.get('kind','guide'));require(out['kind'] in ['guide','external','notice','progress'],'服务类型错误')
            if entity!='services':
                ids=values.get('resourceIds',out.get('resourceIds',[]));require(isinstance(ids,list) and len(ids)<=20 and all(isinstance(i,str) and find(state['resources'],i) for i in ids),'关联资源不存在');out['resourceIds']=list(dict.fromkeys(ids))
            try:out['order']=int(values.get('order',out.get('order',1)))
            except (ValueError,TypeError):raise Invalid('排序必须为整数')
            require(0<=out['order']<=9999,'排序范围为 0–9999')
            require(out.get('title') if entity=='settings' else out.get('name') and out.get('body'),'标题和正文不能为空')
            url=out.get('url','');parts=urlparse(url)
            require(not url or (parts.scheme=='https' and parts.netloc and not parts.username and not parts.password),'外部链接必须为有效 HTTPS 地址')
            if entity=='topics':
                require(out.get('cover','map') in ['nature','planning','energy','public','ecology','map','project','data','consult','cropland','hazard','knowledge'],'封面类型无效')
                def https(value):
                    parts=urlparse(value)
                    return parts.scheme=='https' and bool(parts.hostname) and not parts.username and not parts.password
                require(not out.get('coverUrl') or https(out['coverUrl']),'封面需使用有效 HTTPS 地址')
                require(not out.get('coverUrl') or out.get('coverCredit'),'请填写封面来源与授权说明')
                if 'sections' in values:
                    rows=values['sections'];require(isinstance(rows,list) and len(rows)<=6,'专题分节最多 6 项')
                    out['sections']=[]
                    for item in rows:
                        require(isinstance(item,dict),'分节格式错误')
                        title=text(item.get('title'),100);body=text(item.get('text'),4000)
                        require(title and body,'分节标题和正文需同时填写')
                        out['sections'].append(dict(title=title,text=body))
                if 'media' in values:
                    rows=values['media'];require(isinstance(rows,list) and len(rows)<=6,'媒体资料最多 6 项')
                    out['media']=[]
                    for item in rows:
                        require(isinstance(item,dict),'媒体格式错误')
                        title=text(item.get('title'),100);source=text(item.get('source'),300);url=text(item.get('url'),1000)
                        require(title and source and https(url),'资料标题、来源及有效 HTTPS 地址必填')
                        require(item.get('type') in ['image','video','document'],'媒体类型错误')
                        out['media'].append(dict(title=title,source=source,url=url,type=item['type']))
            out.update(status='草稿',rev=out['rev']+1,updated=now())
            if entity=='settings':p['settings']=out
            elif row:p[entity][p[entity].index(row)]=out
            else:p[entity].append(out)
            return deepcopy(out)
        require(row,'内容不存在',404)
        if action=='public.disable':require(entity!='settings','首页配置不能停用');row['status']='已停用';row['suspended']=True
        else:
            require(row['status']!='已发布','内容已发布，无需重复发布')
            row['version']+=1;row['status']='已发布';row['suspended']=False;row['published']={k:deepcopy(v) for k,v in row.items() if k!='published'}
        row['rev']+=1;row['updated']=now();return deepcopy(row)
    raise Invalid('未知门户操作',404)
