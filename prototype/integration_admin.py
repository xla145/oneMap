"""Integration operations: explicit result permissions and auditable local task exchange."""
from copy import deepcopy
import json
from datetime import datetime
import centers as c
import capabilities as cap


def migrate(s):
    p=s.setdefault('integration',{})
    for key in ['resultAccess','taskAdapters']:p.setdefault(key,{})
    for key in ['taskRuns','taskReceipts']:p.setdefault(key,[])
    if not p.get('internalAdmissionMigrated'):
        # Only known internal seed identities and existing management identities migrate.
        import platform_domain as pd
        for user in s['users']:
            user.setdefault('internalAccess', user['id'] in {'u1','u2','admin','reviewer'} or user['role'] in pd.ADMIN_ROLES)
        p['internalAdmissionMigrated']=True
    return p


def internal_access(s,u):
    migrate(s)
    return bool(u.get('enabled',True) and (u.get('internalAccess',False) or rights(s,u)['view']))


def rights(s,u):
    if u['role']=='平台管理员':return dict(view=True,analyze=True)
    row=migrate(s)['resultAccess'].get(u['id'],{})
    enabled=u.get('enabled',True)
    return dict(view=enabled and row.get('view',False),analyze=enabled and row.get('view',False) and row.get('analyze',False))


def adapter(s,system_id):
    return deepcopy(migrate(s)['taskAdapters'].get(system_id,dict(rev=0,userMap={},statusMap={'待办':'待办','已办':'已办'},versionField='version')))


def system_issues(s):
    out=[]
    for r in c.migrate(s)['systems']:
        missing=[]
        if not r['entry']:missing.append('访问入口未配置')
        if r.get('requiresSso') and not r.get('authClientId'):missing.append('单点登录客户端未配置')
        if r.get('authClientId') and not (c.find(s['platform']['authClients'],r['authClientId']) or {}).get('enabled',False):missing.append('认证客户端已失效')
        if missing:out.append(dict(id=r['id'],name=r['name'],owner=r.get('contact') or '未指定',reason='；'.join(missing)))
    return out


def bootstrap(s,u,full):
    p=migrate(s);out=dict(resultPermissions=rights(s,u),internalAccess=internal_access(s,u))
    if not full:return out
    tasks=c.migrate(s)['externalTodos'];runs=p['taskRuns']
    # Resolve an old failure only when a successful descendant explicitly retries it.
    resolved={r.get('retryOf') for r in runs if r['status']=='已完成'}
    changed=True
    while changed:
        before=len(resolved)
        resolved.update(r.get('retryOf') for r in runs if r['id'] in resolved)
        changed=len(resolved)!=before
    summary=[]
    for r in runs:
        summary.append({**{k:deepcopy(v) for k,v in r.items() if k not in ['payload','errors']},'errorCount':len(r['errors']),'resolved':r['id'] in resolved,'archived':bool(r.get('resolution'))})
    receipts=[]
    for t in tasks:
        matches=[r for r in p['taskReceipts'] if r['taskId']==t['id'] and r['taskRev']==t['rev']]
        last=matches[-1] if matches else None
        receipts.append(dict(taskId=t['id'],taskRev=t['rev'],systemId=t['systemId'],name=t['name'],externalId=t['externalId'],localStatus=t['status'],sourceVersion=t.get('sourceVersion'),status=last['status'] if last else '待核对',last=deepcopy(last)))
    out['administration']=dict(access=deepcopy(p['resultAccess']),adapters={r['id']:adapter(s,r['id']) for r in c.migrate(s)['systems'] if r['todoEnabled']},runs=summary,receipts=receipts,systemIssues=system_issues(s))
    return out


def execute(s,u,op,arg):
    c.admin(u);p=migrate(s);v=arg.get('values',{})
    if op=='access.save':
        who=c.find(s['users'],arg.get('id'));cap.require(who and who['enabled'],'用户不存在或已停用')
        cap.require(who['role']!='平台管理员','平台管理员已有管理权限')
        old=p['resultAccess'].get(who['id'],dict(rev=0));cap.require(arg.get('rev')==old['rev'],'授权已变更，请刷新',409)
        cap.require(type(v.get('view')) is bool and type(v.get('analyze')) is bool,'权限格式错误')
        cap.require(not v['analyze'] or v['view'],'分析权限须同时授予成果查看权限')
        row=dict(rev=old['rev']+1,view=v['view'],analyze=v['analyze'],at=c.now(),actor=u['name'],history=deepcopy(old.get('history',[]))+[dict(at=c.now(),actor=u['name'],view=v['view'],analyze=v['analyze'])])
        p['resultAccess'][who['id']]=row;return deepcopy(row)
    if op=='task.adapter':
        system=c.find(c.migrate(s)['systems'],arg.get('id'));cap.require(system and system['todoEnabled'],'系统未启用待办')
        old=adapter(s,system['id']);cap.require(arg.get('rev')==old['rev'],'映射已变更，请刷新',409)
        user_map=v.get('userMap',{});status_map=v.get('statusMap',{})
        cap.require(isinstance(user_map,dict) and len(user_map)<=200,'用户映射无效')
        cap.require(all(isinstance(k,str) and 0<len(k)<=100 and isinstance(x,str) and (a:=c.find(s['users'],x)) and a['enabled'] for k,x in user_map.items()),'映射用户不存在或已停用')
        cap.require(isinstance(status_map,dict) and 0<len(status_map)<=30 and all(isinstance(k,str) and 0<len(k)<=100 and x in ['待办','已办'] for k,x in status_map.items()),'状态映射无效')
        version=c.text(v.get('versionField','version'),100);cap.require(version,'来源版本字段必填')
        row=dict(rev=old['rev']+1,userMap=deepcopy(user_map),statusMap=deepcopy(status_map),versionField=version)
        p['taskAdapters'][system['id']]=row;return deepcopy(row)
    if op=='task.archive':
        run=c.find(p['taskRuns'],arg.get('id'));c.revision(run,arg)
        cap.require(run['status']=='校验失败' and not run.get('resolution'),'仅能处置未归档的失败批次')
        reason=c.text(v.get('reason',''),1000);kind=v.get('kind')
        cap.require(len(reason)>=5 and kind in ['来源撤回','已另批修正'],'请填写处置方式及至少5字依据')
        replacement=v.get('replacement','')
        if kind=='已另批修正':
            other=c.find(p['taskRuns'],replacement)
            cap.require(other and other['systemId']==run['systemId'] and other['status']=='已完成','请选择同一系统已完成的替代批次')
        else:replacement=''
        run['resolution']=dict(kind=kind,reason=reason,replacement=replacement,actor=u['name'],at=c.now())
        c.changed(run,u,'人工归档失败批次',reason);return dict(ok=True)
    if op=='task.detail':
        run=c.find(p['taskRuns'],arg.get('id'));cap.require(run,'同步批次不存在',404);return deepcopy(run)
    if op in ['task.import','task.retry']:
        parent=None
        if op=='task.retry':
            parent=c.find(p['taskRuns'],arg.get('id'));cap.require(parent and parent['status']=='校验失败' and not parent.get('resolution'),'只能重试失败批次')
            c.revision(parent,arg)
            cap.require(not any(r.get('retryOf')==parent['id'] and r['status']=='已完成' for r in p['taskRuns']),'该批次已成功重试')
            system_id=parent['systemId'];payload=parent['payload']
        else:system_id=arg.get('systemId');payload=arg.get('payload')
        system=c.find(c.migrate(s)['systems'],system_id);cap.require(system and system['todoEnabled'],'该系统未启用待办')
        # Bound retained payloads before creating a durable failure record.
        if isinstance(payload,str):cap.require(len(payload)<=200000,'单批数据不能超过200KB')
        else:cap.require(len(json.dumps(payload,ensure_ascii=False))<=200000,'单批数据不能超过200KB')
        run=c.record('task-run',system['name']+' · 本地同步',systemId=system_id,payload=deepcopy(payload),errors=[],added=0,updatedCount=0,skipped=0,retryOf=parent['id'] if parent else '',adapterRev=adapter(s,system_id)['rev'],scope='本地批量导入；未向来源系统发起网络请求')
        try:
            raw_rows=c.json_value(payload,list);cap.require(0<len(raw_rows)<=200,'每批1～200条')
            config=adapter(s,system_id);prepared=[];seen=set()
            for index,raw in enumerate(raw_rows,1):
                try:
                    cap.require(isinstance(raw,dict),'待办应为对象')
                    row={k:raw.get(field,'') for k,field in system['mapping'].items()}
                    cap.require(all(isinstance(x,str) for x in row.values()),'待办字段须为文本')
                    cap.require(row.get('id') and row.get('name'),'缺少任务标识或名称')
                    cap.require(row['id'] not in seen,'同批任务标识重复');seen.add(row['id'])
                    source_user=row.get('userId','');row['userId']=config['userMap'].get(source_user,source_user)
                    who=c.find(s['users'],row['userId']);cap.require(who and who['enabled'],'接收人无法匹配：'+source_user)
                    cap.require(row.get('status') in config['statusMap'],'来源状态未映射：'+row.get('status',''))
                    row['status']=config['statusMap'][row['status']]
                    ver=raw.get(config['versionField']);cap.require(type(ver) is int and ver>=1,'来源版本须为正整数')
                    for key in ['createdAt','dueAt']:
                        if row.get(key):
                            try:
                                stamp=datetime.fromisoformat(row[key]);cap.require(stamp.tzinfo is None,'时间不能带时区');row[key]=stamp.isoformat(timespec='seconds')
                            except ValueError:raise cap.Invalid('日期格式无效')
                    row['entry']=c.safe_entry(row.get('entry',''))
                    fingerprint=c.digest(json.dumps(row,ensure_ascii=False,sort_keys=True))
                    old=next((t for t in s['centers']['externalTodos'] if t['systemId']==system_id and t['externalId']==row['id']),None)
                    old_ver=old.get('sourceVersion',0) if old else 0
                    cap.require(ver>=old_ver,'来源版本落后，拒绝覆盖较新任务')
                    if old and ver==old_ver:
                        cap.require(old.get('sourceFingerprint')==fingerprint,'相同版本内容冲突，请更新来源版本')
                        run['skipped']+=1;continue
                    prepared.append((row,ver,fingerprint,old))
                except cap.Invalid as exc:run['errors'].append(dict(row=index,externalId=str(raw.get(system['mapping']['id'],''))[:100] if isinstance(raw,dict) else '',reason=exc.message))
            cap.require(not run['errors'],'整批校验失败，任务未写入')
            for row,ver,fingerprint,old in prepared:
                if old is None:
                    old=c.record('todo',row['name'],systemId=system_id,externalId=row['id']);s['centers']['externalTodos'].append(old);run['added']+=1
                else:run['updatedCount']+=1
                old.update({k:value for k,value in row.items() if k not in ['id','createdAt']})
                old.update(sourceCreatedAt=row.get('createdAt',''),receivedAt=c.now(),sourceVersion=ver,sourceFingerprint=fingerprint,lastRunId=run['id'])
                c.changed(old,u,'本地版本同步','来源版本 '+str(ver))
            run['status']='已完成'
        except cap.Invalid as exc:
            run['status']='校验失败'
            if not run['errors']:run['errors'].append(dict(row=0,externalId='',reason=exc.message))
        p['taskRuns'].append(run)
        if parent:c.changed(parent,u,'重试本地同步',run['id'])
        return {k:deepcopy(value) for k,value in run.items() if k!='payload'}
    if op=='task.history':
        task=c.find(c.migrate(s)['externalTodos'],arg.get('id'));cap.require(task,'任务不存在',404)
        return dict(task=deepcopy(task),receipts=[deepcopy(r) for r in p['taskReceipts'] if r['taskId']==task['id']])
    if op=='task.receipt':
        task=c.find(c.migrate(s)['externalTodos'],arg.get('id'));c.revision(task,arg)
        status=v.get('sourceStatus');evidence=c.text(v.get('evidence',''),2000)
        cap.require(status in ['待办','已办'] and len(evidence)>=5,'请选择来源状态并填写至少5字核对依据')
        row=c.record('receipt',task['name'],taskId=task['id'],taskRev=task['rev'],sourceStatus=status,localStatus=task['status'],evidence=evidence,actor=u['name'],scope='人工核对记录，不代表自动回传成功')
        row['status']='人工核对一致' if status==task['status'] else '状态不一致';p['taskReceipts'].append(row);return deepcopy(row)
    raise cap.Invalid('未知管理操作',404)
