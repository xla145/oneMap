"""Additive admin design migration. Preserve legacy grants and publication snapshots."""
from copy import deepcopy
from uuid import uuid5, NAMESPACE_URL
from datetime import date
import capabilities as cap


def migrate(s):
    for i,g in enumerate(s['grants']):
        g.setdefault('id','grant-'+uuid5(NAMESPACE_URL,f"{i}:{g['userId']}:{g['resourceId']}:{g['validUntil']}").hex[:12])
        g.setdefault('status','有效');g.setdefault('rev',1)
        g.setdefault('sourceApplicationId','');g.setdefault('sourceItemId','')
        g.setdefault('deliveryStatus','已生效');g.setdefault('history',[])
    return s


def grant_rows(s,u):
    manage=u['role'] in ['平台管理员','资源审批人员']
    rows=[]
    for g in s['grants']:
        if not manage and g['userId']!=u['id']:continue
        r=next((r for r in s['resources'] if r['id']==g['resourceId']),None)
        user=next((x for x in s['users'] if x['id']==g['userId']),{})
        status=g['status'] if g['status']!='有效' else ('已过期' if g['validUntil']<date.today().isoformat() else '有效')
        rows.append(dict(deepcopy(g),deliveryStatus=('已停止' if status=='已撤销' else '已到期' if status=='已过期' else g['deliveryStatus']),displayStatus=status,userName=user.get('name',g['userId']),resourceName=(r or {}).get('name',g['resourceId']),resourceAvailable=bool(cap.published(r)) and cap.sharing_policy(cap.published(r))!='限制使用'))
    return rows
