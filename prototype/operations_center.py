"""Operations workspace: additive records referencing existing center/resource IDs.
All execution is local. External connectors are never reported as connected.
"""
from copy import deepcopy
from datetime import datetime
import csv
import io
import centers as c
import capabilities as cap
from capabilities import require, Invalid

ENTITIES = ('tasks', 'orders', 'models', 'qualityTasks', 'imports', 'directories', 'catalogs', 'domains', 'alertRules', 'alerts')

def migrate(s):
    c.migrate(s)
    o = s.setdefault('operations', {})
    for key in ENTITIES: o.setdefault(key, [])
    if not o.get('initialized'):
        o['directories'].append(dict(c.record('op-dir', '技术资产总目录', parentId='', kind='公共目录'), id='op-dir-root', status='启用'))
        o['domains'].append(dict(c.record('domain', '本地示例数仓', parentId='', kind='业务域', sourceId='source-local'), id='domain-local', status='本地演示'))
        for kind in ['质检异常', '交付失败', '服务依赖异常']:
            o['alertRules'].append(dict(c.record('alert-rule', kind, kind=kind, enabled=True, assigneeId='admin', level='警告'), id='op-rule-'+str(len(o['alertRules'])+1), status='启用'))
        o['initialized'] = True
    return o

def todos(s, u):
    o = migrate(s); rows = []; admin = u['role'] == '平台管理员'
    for r in o['orders']:
        own = r['assigneeId'] == u['id']
        if own and r['status'] in ['待填报', '草稿', '已退回'] or admin and r['status'] == '待审核':
            rows.append(dict(r, source='运营中心·登记审核' if r['status']=='待审核' else '运营中心·数据报送', userId=u['id'], entry='#/'+('admin' if admin else 'front')+'/operations/collection/orders/'+r['id']))
    for r in c.migrate(s)['issues']:
        if r['assigneeId'] == u['id'] and r['status'] in ['待处理','已退回'] or admin and r['status']=='待复核':
            rows.append(dict(r, source='运营中心·数据治理', userId=u['id'], entry='#/'+('admin' if admin else 'front')+'/operations/quality/orders/'+r['id']))
    for r in o['alerts']:
        if r['assigneeId']==u['id'] and r['status']!='已关闭':
            rows.append(dict(r, source='运营中心·告警处置', userId=u['id'], entry='#/admin/operations/monitoring/alerts/'+r['id']))
    return rows

def bootstrap(s, u, mode):
    o=migrate(s); full=mode=='admin' and u['role']=='平台管理员'
    out={key:deepcopy(value) if full else [] for key,value in o.items() if key in ENTITIES}
    if not full:
        out['orders']=[deepcopy(r) for r in o['orders'] if r['assigneeId']==u['id']]
        for order in out['orders']:
            order['sourceName']=(c.find(s['centers']['sources'],order['sourceId']) or {}).get('name','数源已失效')
            standard=c.find(s['centers']['standards'],order['standardId'])
            order.setdefault('standardSnapshot',deepcopy(standard))
        task_ids={r.get('taskId') for r in out['orders']}
        out['tasks']=[deepcopy(r) for r in o['tasks'] if r['id'] in task_ids]
    out.update(canManage=full,todos=todos(s,u))
    return out

def save(s,u,p):
    o=migrate(s); entity=p.get('entity'); require(entity in ['tasks','models','qualityTasks','imports','directories','catalogs','domains','alertRules'],'不支持的配置类型')
    old=c.find(o[entity],p.get('id'))
    if p.get('id'): c.revision(old,p)
    v=p.get('values'); require(isinstance(v,dict),'配置格式错误')
    name=c.text(v.get('name',''),100); require(name,'名称必填')
    r=deepcopy(old) if old else c.record('op-'+entity,name,ownerId=u['id'])
    r['name']=name
    if entity=='tasks':
        require(not old or old['status']=='草稿','已下发任务保留原配置，请新建任务')
        assignees=v.get('assigneeIds',[]); require(isinstance(assignees,list) and assignees and len(assignees)<=50,'请选择1～50名报送人员')
        require(all((x:=c.find(s['users'],key)) and x['enabled'] for key in assignees),'报送人员无效')
        due=c.text(v.get('dueAt','')); require(due,'请填写截止时间')
        try: datetime.fromisoformat(due)
        except ValueError: raise Invalid('截止时间格式不正确')
        standard=c.find(s['centers']['standards'],v.get('standardId')); require(standard and standard['status']=='已发布','请选择已发布标准')
        source=c.find(s['centers']['sources'],v.get('sourceId')); require(source,'数源不存在')
        r.update(assigneeIds=list(dict.fromkeys(assignees)),dueAt=due,sourceId=source['id'],standardId=standard['id'],standardVersion=standard['version'],description=c.text(v.get('description','')),status='草稿')
    elif entity=='models':
        rules=v.get('ruleIds',[]); require(isinstance(rules,list),'规则列表格式错误')
        require(rules and all(c.find(s['centers']['rules'],key) for key in rules),'请选择有效质检规则')
        r.update(kind='本地规则模型',ruleIds=list(dict.fromkeys(rules)),version=r.get('version',0),status='草稿')
    elif entity=='qualityTasks':
        model=c.find(o['models'],v.get('modelId')); require(model and model.get('published'),'请选择已发布模型')
        ingestion=c.find(s['centers']['ingestions'],v.get('ingestionId')); require(ingestion,'请选择归集批次')
        r.update(modelId=model['id'],modelSnapshot=deepcopy(model['published']),ingestionId=ingestion['id'],status='待执行',schedule='手动执行',runIds=r.get('runIds',[]))
    elif entity=='imports':
        require(not old or old['status'] in ['草稿','失败'],'已执行入库任务不能编辑')
        ingestion=c.find(s['centers']['ingestions'],v.get('ingestionId')); require(ingestion and ingestion['status']!='已入库','请选择未入库批次')
        target=c.find(s['centers']['datasets'],v.get('datasetId')); require(target and target['rowCount']==0,'首批仅支持导入已有空表，避免覆盖在库数据')
        mapping=c.json_value(v.get('mapping',{}),dict)
        fields,_=c.csv_data(ingestion['dataRows']); require(set(mapping)==set(target['fields']) and all(isinstance(x,str) and x in fields for x in mapping.values()),'映射需覆盖全部目标字段，值为有效来源字段')
        require(len(set(mapping.values()))==len(mapping),'来源字段不能重复映射')
        r.update(ingestionId=ingestion['id'],datasetId=target['id'],resourceId=target['resourceId'],mapping=mapping,status='草稿',attempts=r.get('attempts',[]))
    elif entity in ['directories','domains']:
        parent=c.text(v.get('parentId','')); visited={r['id']}; cursor=parent
        while cursor:
            require(cursor not in visited,'上级关系不能形成循环'); visited.add(cursor)
            node=c.find(o[entity],cursor); require(node,'上级节点不存在'); cursor=node.get('parentId','')
        r.update(parentId=parent,kind=c.text(v.get('kind','公共目录' if entity=='directories' else '业务域')),status='启用')
        require(r['kind'] in (['公共目录','数据库表','图层服务','工具服务','知识文档'] if entity=='directories' else ['业务域','数仓层','数据库','数据空间']),'节点类型无效')
        if entity=='domains':
            source=c.find(s['centers']['sources'],v.get('sourceId'));require(source,'请选择目标数源');r['sourceId']=source['id']
    elif entity=='catalogs':
        resource=c.find(s['resources'],v.get('resourceId')); require(resource,'资源不存在')
        require(not old or old['resourceId']==resource['id'],'编目记录不可更换关联资产')
        require(not any(x['resourceId']==resource['id'] and x['id']!=r['id'] for x in o['catalogs']),'该资产已编目，请编辑原记录')
        directory=c.find(o['directories'],v.get('directoryId')); require(directory and directory['kind'] in ['公共目录',resource['type']],'请选择匹配资产类型的技术目录')
        r.update(resourceId=resource['id'],directoryId=directory['id'],department=c.text(v.get('department','')),tags=c.text(v.get('tags','')),status='已编目')
        require(r['department'],'责任单位必填')
    elif entity=='alertRules':
        kind=v.get('kind'); require(kind in ['质检异常','交付失败','服务依赖异常'],'仅支持本地业务巡检指标')
        holder=c.find(s['users'],v.get('assigneeId')); require(holder and holder['enabled'] and holder['role']=='平台管理员','首批处置人员请选择平台管理员')
        require(v.get('level') in ['提示','警告','严重'],'告警级别无效')
        r.update(kind=kind,assigneeId=holder['id'],level=v['level'],enabled=v.get('enabled') is True,status='启用' if v.get('enabled') is True else '停用')
    c.changed(r,u,'保存配置')
    if old: o[entity][o[entity].index(old)]=r
    else: o[entity].append(r)
    return deepcopy(r)

def validate_report(s, ingestion):
    report=c.find(s['centers']['qualityRuns'],ingestion.get('qualityRunId'))
    require(report and report['passed'] and report['inputHash']==c.digest(ingestion['dataRows']) and report['dataRevision']==ingestion['dataRevision'],'数据变化或未通过质检，请重新检查')
    require(set(ingestion['ruleIds'])=={x['id'] for x in report['ruleSnapshots']},'批次质检规则已变化，请重新质检')
    require(ingestion.get('standardId','')==(report.get('standardSnapshot') or {}).get('id',''),'批次标准已变化，请重新质检')
    require(all((rule:=c.find(s['centers']['rules'],x['id'])) and rule['rev']==x['rev'] and rule['enabled'] for x in report['ruleSnapshots']),'规则已变化，请重新质检')
    standard=report.get('standardSnapshot')
    if standard:
        current=c.find(s['centers']['standards'],standard['id']); require(current and current['status']=='已发布' and current['version']==standard['version'],'标准已变化，请重新质检')
    require(not any(x['ingestionId']==ingestion['id'] and x['status']!='已办结' for x in s['centers']['issues']),'请先办结整改工单')
    return report

def execute(s,u,action,p,hooks):
    o=migrate(s); op=action.removeprefix('operations.'); cc=s['centers']
    # Submitters may edit and submit only their own assigned orders, never approve.
    if op in ['order.save','order.submit']:
        r=c.find(o['orders'],p.get('id')); require(r and r['assigneeId']==u['id'],'只能办理本人归集工单',403); c.revision(r,p)
        require(r['status'] in ['待填报','草稿','已退回'],'当前状态不能修改或提交')
        if op=='order.save':
            body=c.text(p.get('dataRows',''),200000); c.csv_data(body)
            r.update(dataRows=body,status='草稿',dataRevision=r.get('dataRevision',0)+1)
            c.changed(r,u,'保存报送草稿')
        else:
            c.csv_data(r.get('dataRows',''))
            r.setdefault('submissions',[]).append(dict(at=c.now(),dataRevision=r['dataRevision'],dataRows=r['dataRows']))
            r['status']='待审核';c.changed(r,u,'提交登记审核')
        return deepcopy(r)
    c.admin(u)
    if op=='save': return save(s,u,p)
    if op=='delete':
        entity=p.get('entity');require(entity in ['tasks','models','imports','directories','domains','catalogs'],'此对象不支持删除')
        r=c.find(o[entity],p.get('id'));c.revision(r,p)
        if entity=='tasks':require(r['status']=='草稿' and not any(x['taskId']==r['id'] for x in o['orders']),'已下发任务不能删除')
        if entity=='models':require(not r.get('published') and not any(x['modelId']==r['id'] for x in o['qualityTasks']),'已发布或被任务引用的模型不能删除')
        if entity=='imports':require(not r['attempts'],'执行记录需保留，不能删除')
        if entity in ['directories','domains']:
            require(not any(x.get('parentId')==r['id'] for x in o[entity]),'请先处理下级节点')
            refs=o['catalogs'] if entity=='directories' else cc['datasets'];key='directoryId' if entity=='directories' else 'domainId'
            require(not any(x.get(key)==r['id'] for x in refs),'节点仍被资产或库表引用，不能删除')
        o[entity].remove(r)
        import portal_management as pm
        pm.event(s,u,'operation','解除技术编目' if entity=='catalogs' else '删除运营草稿或空节点',r['id'],r['name'])
        return dict(id=r['id'],status='已解除' if entity=='catalogs' else '已删除')
    if op=='dataset.create':
        domain=c.find(o['domains'],p.get('domainId'));require(domain,'请选择目标数仓节点')
        source=c.find(cc['sources'],domain['sourceId']);require(source and source['kind']=='CSV文件','外部建库尚未接入，请选择本地数仓节点')
        result=c.execute(s,u,'centers.dataset.create',p,hooks)
        row=c.find(cc['datasets'],result['id']);row.update(domainId=domain['id'],domainSnapshot=deepcopy(domain));c.changed(row,u,'关联目标数仓',domain['name']);return deepcopy(row)
    if op=='task.dispatch':
        r=c.find(o['tasks'],p.get('id'));c.revision(r,p);require(r['status']=='草稿','任务已经下发')
        for key in r['assigneeIds']:
            holder=c.find(s['users'],key);require(holder and holder['enabled'],'报送人员已停用')
        for key in r['assigneeIds']:
            holder=c.find(s['users'],key)
            order=c.record('order',r['name']+' · '+holder['department'],taskId=r['id'],assigneeId=key,assigneeName=holder['name'],department=holder['department'],dueAt=r['dueAt'],sourceId=r['sourceId'],standardId=r['standardId'],standardVersion=r['standardVersion'],standardSnapshot=deepcopy(c.find(cc['standards'],r['standardId'])),dataRows='',dataRevision=0,submissions=[])
            order['status']='待填报';c.changed(order,u,'下发归集工单');o['orders'].append(order)
        r['status']='已下发';c.changed(r,u,'下发任务');return deepcopy(r)
    if op=='order.review':
        r=c.find(o['orders'],p.get('id'));c.revision(r,p);require(r['status']=='待审核','该登记不在待审核状态')
        decision=p.get('decision');require(decision in ['通过','退回'],'审核结论无效')
        note=c.text(p.get('note',''));require(note,'审核意见必填')
        if decision=='退回':r['status']='已退回'
        else:
            standard=c.find(cc['standards'],r['standardId']);require(standard and standard['status']=='已发布' and standard['version']==r['standardVersion'],'任务采用的标准已变化，请退回并按新标准重新下发任务')
            batch=c.save(s,u,dict(entity='ingestions',values=dict(name=r['name'],sourceId=r['sourceId'],standardId=r['standardId'],ruleIds=[x['id'] for x in cc['rules'] if x['enabled'] and x['field'] in c.csv_data(r['dataRows'])[0]],dataRows=r['dataRows'],mode='在线填报')))
            current=c.find(cc['ingestions'],batch['id']);current.update(orderId=r['id'],status='待质检');c.changed(current,u,'登记审核通过',note)
            r.update(status='已通过',ingestionId=current['id'])
        c.changed(r,u,'登记'+decision,note)
        task=c.find(o['tasks'],r['taskId']);task['status']='已完成' if all(x['status']=='已通过' for x in o['orders'] if x['taskId']==task['id']) else '进行中';c.changed(task,u,'更新报送进度')
        return deepcopy(r)
    if op=='model.publish':
        r=c.find(o['models'],p.get('id'));c.revision(r,p);require(r['status']=='草稿','请先保存新的模型草稿')
        rules=[c.find(cc['rules'],key) for key in r['ruleIds']];require(all(x and x['enabled'] for x in rules),'模型引用的规则不可用')
        r['version']+=1;r['published']=dict(id=r['id'],name=r['name'],version=r['version'],rules=deepcopy(rules));r['status']='已发布';c.changed(r,u,'发布质检模型');return deepcopy(r)
    if op=='quality.run':
        r=c.find(o['qualityTasks'],p.get('id'));c.revision(r,p)
        batch=c.find(cc['ingestions'],r['ingestionId']);require(batch and batch['status'] in ['待质检','待整改','待登记'],'批次尚未进入质检或已经入库')
        snapshots=r['modelSnapshot']['rules'];require(all((rule:=c.find(cc['rules'],x['id'])) and rule['rev']==x['rev'] and rule['enabled'] for x in snapshots),'模型的规则版本已变化，请重新发布模型并更新任务')
        batch['ruleIds']=[x['id'] for x in snapshots]
        run=c.quality(s,u,batch);run.update(taskId=r['id'],modelSnapshot=deepcopy(r['modelSnapshot']),executionStatus='已完成')
        r['runIds'].append(run['id']);r.update(status='已完成',lastRunAt=run['createdAt']);c.changed(r,u,'执行质检',run['id']);return deepcopy(run)
    if op=='import.run':
        r=c.find(o['imports'],p.get('id'));c.revision(r,p);require(r['status'] in ['草稿','失败'],'任务已执行，不能重复入库')
        attempt=dict(id=c.ident('import-run'),at=c.now(),status='执行中')
        try:
            batch=c.find(cc['ingestions'],r['ingestionId']);require(batch and batch['status']=='待登记','批次需质检通过且未入库')
            report=validate_report(s,batch)
            ds=c.find(cc['datasets'],r['datasetId']);require(ds and ds['rowCount']==0,'目标表已有数据，不允许重复或覆盖导入')
            resource=c.find(s['resources'],ds['resourceId']);require(resource and not resource.get('published'),'目标必须为未发布的本地空表')
            target_standard=c.find(cc['standards'],ds['standardId']);require(target_standard and target_standard['status']=='已发布' and target_standard['version']==ds['standardVersion'],'目标表标准已变化，请核对结构并重新建表')
            fields,rows=c.csv_data(batch['dataRows']);mapping=r['mapping'];require(set(mapping)==set(ds['fields']) and all(x in fields for x in mapping.values()),'字段结构变化，请重新配置映射')
            mapped=[{target:row[source] for target,source in mapping.items()} for row in rows]
            require(not c.rule_issues(ds['fields'],mapped,[],target_standard),'映射后数据不符合目标标准')
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=ds['fields']);writer.writeheader();writer.writerows(mapped)
            saved=hooks['save'](s,u,dict(entity='resources',id=resource['id'],rev=resource['rev'],values=dict(dataRows=stream.getvalue())))
            ds.update(rowCount=len(mapped),ingestionId=batch['id'],status='已入库');c.changed(ds,u,'映射入库')
            batch.update(status='已入库',resourceId=saved['id']);c.changed(batch,u,'映射入库',r['id'])
            attempt.update(status='成功',rowCount=len(mapped),qualityRunId=report['id'],resourceId=saved['id']);r['status']='成功'
        except Invalid as error:
            attempt.update(status='失败',error=error.message);r['status']='失败'
        r['attempts'].append(attempt);c.changed(r,u,'执行入库',attempt.get('error','成功'));return deepcopy(r)
    if op=='inspection.run':
        result=c.execute(s,u,'centers.inspection.run',{},hooks);active=set()
        for failure in result['failures']:
            for existing in o['alerts']:
                if existing['status']!='已关闭' and existing['targetId']==failure['targetId'] and existing['kind']==failure['kind'] and existing.get('recoveredAt'):
                    existing['recoveredAt']='';c.changed(existing,u,'异常再次发生')
            for rule in o['alertRules']:
                if not rule['enabled'] or rule['kind']!=failure['kind']:continue
                key=(rule['id'],failure['targetId']);active.add(key)
                alert=next((x for x in o['alerts'] if (x['ruleId'],x['targetId'])==key and x['status']!='已关闭'),None)
                if alert:
                    alert.update(lastSeenAt=c.now(),count=alert['count']+1,recoveredAt='',inspectionId=result['id']);c.changed(alert,u,'巡检再次发现异常')
                else:
                    alert=c.record('alert',failure['name']+' · '+failure['kind'],ruleId=rule['id'],targetId=failure['targetId'],kind=failure['kind'],level=rule['level'],assigneeId=rule['assigneeId'],reason=failure['reason'],inspectionId=result['id'],count=1,lastSeenAt=c.now(),recoveredAt='',notification='待接入：未发送外部通知')
                    alert['status']='待确认';c.changed(alert,u,'业务巡检触发告警');o['alerts'].append(alert)
        failures={(x['kind'],x['targetId']) for x in result['failures']}
        for alert in o['alerts']:
            if alert['status']!='已关闭' and (alert['kind'],alert['targetId']) not in failures and not alert['recoveredAt']:
                alert['recoveredAt']=c.now();c.changed(alert,u,'巡检确认指标恢复')
        return deepcopy(result)
    if op=='alert.transition':
        r=c.find(o['alerts'],p.get('id'));c.revision(r,p);target=p.get('status')
        transitions={'待确认':['处理中'],'处理中':['待验证'],'待验证':['处理中','已关闭'],'已关闭':['处理中']}
        require(target in transitions[r['status']],'不允许的告警状态流转')
        note=c.text(p.get('note',''));require(note,'请填写处置或验证说明')
        if target=='已关闭':
            require(r.get('recoveredAt'),'指标尚未恢复，请修复后重新巡检并验证')
            verification=c.execute(s,u,'centers.inspection.run',{},hooks)
            require(not any(x['targetId']==r['targetId'] and x['kind']==r['kind'] for x in verification['failures']),'验证发现异常再次发生，不能关闭')
            r['verificationId']=verification['id'];r['closedAt']=c.now()
        r['status']=target;c.changed(r,u,'告警'+target,note);return deepcopy(r)
    raise Invalid('未知运营操作',404)
