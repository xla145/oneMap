"""Local security controls, SQLite backup/restore, and host/service health."""
import ipaddress
import json
import os
import shutil
import sqlite3
import ssl
import subprocess
import sys
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
import threading
from capabilities import require
import portal_management as pm

ROOT=Path(__file__).resolve().parent
START=time.monotonic()
RATE=defaultdict(deque)
RATE_LOCK=threading.Lock()
HEALTH_LOCK=threading.Lock()
HEALTH_CACHE={'at':0,'value':None}


def settings(s):
    m=pm.migrate(s)
    return m.setdefault('security',dict(rev=1,tlsEnabled=False,certPath='',keyPath='',whitelistEnabled=False,networks=[],rateEnabled=False,requestsPerMinute=120,blockedAgents=[],backupEnabled=False,backupIntervalHours=24,backupKeep=7,cpuThreshold=90,memoryThreshold=90,diskThreshold=90,responseThresholdMs=2000))


def check_request(s,ip,agent):
    cfg=settings(s);addr=ipaddress.ip_address(ip)
    # A local recovery route remains available for a mistaken whitelist.
    if cfg['whitelistEnabled'] and not addr.is_loopback:
        require(any(addr in ipaddress.ip_network(n,strict=False) for n in cfg['networks']),'来源 IP 不在白名单',403)
    require(not any(x.lower() in agent.lower() for x in cfg['blockedAgents']),'请求被访问策略拒绝',403)
    if cfg['rateEnabled']:
        with RATE_LOCK:
            current=time.monotonic();hits=RATE[ip]
            while hits and hits[0]<current-60:hits.popleft()
            require(len(hits)<cfg['requestsPerMinute'],'请求过于频繁，请稍后重试',429)
            hits.append(current)
            if len(RATE)>10000:
                for key in list(RATE):
                    if not RATE[key] or RATE[key][-1]<current-60:del RATE[key]


def backup_dir(db):
    folder=Path(db).parent/(Path(db).stem+'-backups');folder.mkdir(parents=True,exist_ok=True);return folder


def backup(db, prefix='manual'):
    path=backup_dir(db)/(prefix+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
    with sqlite3.connect(db) as source,sqlite3.connect(path) as dest:source.backup(dest)
    os.chmod(path,0o600)
    return dict(id=path.name,size=path.stat().st_size,at=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds'))


def backups(db):
    return [dict(id=p.name,size=p.stat().st_size,at=datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds')) for p in sorted(backup_dir(db).glob('*.sqlite3'),reverse=True)]


def execute(db,s,u,action,p):
    pm.admin(u);cfg=settings(s)
    if action=='portal.securityGet':return dict(config=cfg,backups=backups(db))
    if action=='portal.securitySave':
        require(p.get('rev')==cfg['rev'],'配置已更新，请刷新',409);v=p.get('values',{});require(isinstance(v,dict),'配置格式无效');out=dict(cfg)
        for k in ['tlsEnabled','whitelistEnabled','rateEnabled','backupEnabled']:
            require(type(v.get(k,False)) is bool,'开关值无效');out[k]=v.get(k,False)
        for k in ['certPath','keyPath']:out[k]=pm.text(v.get(k,''),1000)
        for k,lo,hi in [('requestsPerMinute',10,10000),('backupIntervalHours',1,720),('backupKeep',1,100),('cpuThreshold',1,100),('memoryThreshold',1,100),('diskThreshold',1,100),('responseThresholdMs',10,600000)]:
            require(type(v.get(k,cfg[k])) is int and lo<=v.get(k,cfg[k])<=hi,'配置数值超出范围：'+k);out[k]=v.get(k,cfg[k])
        for k in ['networks','blockedAgents']:
            val=v.get(k,[]);require(isinstance(val,list) and len(val)<=100 and all(isinstance(x,str) and 0<len(x)<=200 for x in val),'白名单或客户端规则格式无效');out[k]=val
        try:out['networks']=[str(ipaddress.ip_network(x,strict=False)) for x in out['networks']]
        except ValueError:require(False,'IP 白名单需填写有效 IP 或 CIDR 网段')
        require(not out['whitelistEnabled'] or out['networks'],'启用白名单前请填写 IP 或网段')
        if out['tlsEnabled']:
            try:
                context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(out['certPath'],out['keyPath'])
            except (OSError,ssl.SSLError):require(False,'证书或私钥无法加载，请核对服务器上的 PEM 路径及证书匹配关系')
        out['rev']+=1;pm.migrate(s)['security']=out;pm.event(s,u,'operation','保存安全与监控配置',name='系统安全配置');return out
    if action=='portal.backup':
        row=backup(db);pm.event(s,u,'operation','创建数据库备份',row['id'],row['id']);return row
    if action=='portal.restore':
        name=p.get('id');require(isinstance(name,str) and name in [b['id'] for b in backups(db)],'备份不存在',404)
        require(p.get('confirm')==name,'请输入完整备份名称确认还原')
        path=backup_dir(db)/name
        with sqlite3.connect(path) as source:
            require(source.execute('PRAGMA integrity_check').fetchone()[0]=='ok','备份完整性检查失败')
            require(source.execute("SELECT name FROM sqlite_master WHERE name='state'").fetchone(),'备份不是本平台数据库')
            # Verify the recovery operator still exists and remains an administrator in this backup.
            snapshot=json.loads(source.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
            require(any(x['id']==u['id'] and x.get('enabled') and x['role']=='平台管理员' for x in snapshot.get('users',[])),'备份中没有当前管理员账号，不能还原')
            safety=backup(db,'before-restore')
            with sqlite3.connect(db) as dest:source.backup(dest)
        # Older backups are upgraded before the next request is served.
        import platform_store
        import analysis_jobs
        with sqlite3.connect(db) as c:platform_store.initialize(c)
        pm.initialize(db);analysis_jobs.initialize(db)
        return dict(ok=True,safetyBackup=safety['id'])
    if action=='portal.monitor':return monitor(db,s,u)
    require(False,'未知运维操作',404)


def system_metrics(db):
    # Prefer psutil if available; keep an OS-specific fallback for the existing runtime.
    cpu=memory=None;source='系统采样'
    try:
        import psutil
        cpu=psutil.cpu_percent(interval=.15);memory=psutil.virtual_memory().percent
    except ImportError:
        try:
            if sys.platform=='darwin':
                output=subprocess.run(['top','-l','1','-n','0'],capture_output=True,text=True,timeout=3).stdout
                import re
                found=re.search(r'CPU usage:.*?([\d.]+)% idle',output)
                if found:cpu=100-float(found.group(1))
                vm=subprocess.run(['vm_stat'],capture_output=True,text=True,timeout=3).stdout
                nums={k.strip():int(v) for k,v in re.findall(r'([^\n:]+):\s+(\d+)',vm)}
                total=int(subprocess.run(['sysctl','-n','hw.memsize'],capture_output=True,text=True,timeout=3).stdout)
                page=int(re.search(r'page size of (\d+)',vm).group(1))
                free=(nums.get('Pages free',0)+nums.get('Pages inactive',0)+nums.get('Pages speculative',0))*page
                memory=100*(1-free/total)
            elif sys.platform.startswith('linux'):
                def tick():return [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
                a=tick();time.sleep(.1);b=tick();cpu=100*(1-(b[3]-a[3]+b[4]-a[4])/max(1,sum(b)-sum(a)))
                values={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
                memory=100*(1-values['MemAvailable']/values['MemTotal'])
        except (OSError,ValueError,AttributeError,subprocess.TimeoutExpired):source='部分指标不可用'
    usage=shutil.disk_usage(Path(db).parent)
    return dict(cpu=round(cpu,1) if cpu is not None else None,memory=round(max(0,min(100,memory)),1) if memory is not None else None,disk=round(usage.used/usage.total*100,1),diskFreeGB=round(usage.free/1024**3,2),source=source)


def monitor(db,s,u):
    with HEALTH_LOCK:
        if time.monotonic()-HEALTH_CACHE['at']>10 or not HEALTH_CACHE['value']:
            HEALTH_CACHE.update(at=time.monotonic(),value=system_metrics(db))
        metrics=dict(HEALTH_CACHE['value'])
    with sqlite3.connect(db) as c:
        rows=c.execute("SELECT status,duration FROM portal_requests WHERE at>=?",(datetime.fromtimestamp(time.time()-3600).isoformat(timespec='seconds'),)).fetchall()
    metrics.update(responseMs=round(sum(r[1] for r in rows)/len(rows),2) if rows else 0,requests=len(rows),errors=sum(r[0]>=500 for r in rows),uptimeSeconds=int(time.monotonic()-START),sampledAt=pm.now())
    return dict(metrics=metrics,alerts=pm.migrate(s).get('alerts',[])[-100:][::-1])


def maintenance(db,load,save,lock):
    """Called from the server worker; alerts are local admin notifications, never external messages."""
    with lock,sqlite3.connect(db) as c:
        s=load(c);m=pm.migrate(s);cfg=settings(s);changed=False
        metrics=system_metrics(db)
        requests=c.execute('SELECT duration FROM portal_requests WHERE at>=?',(datetime.fromtimestamp(time.time()-300).isoformat(timespec='seconds'),)).fetchall()
        metrics['response']=sum(r[0] for r in requests)/len(requests) if requests else 0
        alerts=m.setdefault('alerts',[])
        for kind,label,key in [('cpu','CPU 使用率','cpuThreshold'),('memory','内存使用率','memoryThreshold'),('disk','磁盘使用率','diskThreshold'),('response','服务响应时间','responseThresholdMs')]:
            active=next((a for a in reversed(alerts) if a['metric']==kind and not a.get('resolvedAt')),None)
            if metrics[kind] is None:continue
            if metrics[kind]>=cfg[key] and not active:
                alerts.append(dict(id=pm.ident(),metric=kind,name=label+'超过阈值',value=round(metrics[kind],2),threshold=cfg[key],at=pm.now(),status='告警中'))
                changed=True
            elif metrics[kind]<cfg[key] and active:active.update(status='已恢复',resolvedAt=pm.now());changed=True
        if changed:save(c,s)
    if cfg['backupEnabled']:
        autos=sorted(backup_dir(db).glob('auto-*.sqlite3'),key=lambda p:p.stat().st_mtime,reverse=True)
        if not autos or time.time()-autos[0].stat().st_mtime>=cfg['backupIntervalHours']*3600:
            backup(db,'auto')
            # Only scheduled backups are subject to configured retention; manual/safety backups stay intact.
            autos=sorted(backup_dir(db).glob('auto-*.sqlite3'),key=lambda p:p.stat().st_mtime,reverse=True)
            for old in autos[cfg['backupKeep']:]:old.unlink()
