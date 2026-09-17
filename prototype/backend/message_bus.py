"""Local event ingress and leased pull consumption. No external broker calls."""
from copy import deepcopy
from datetime import datetime, timedelta
import fnmatch
import re
from capabilities import require, Invalid


def matches(subscription, event):
    return (fnmatch.fnmatchcase(event['type'], subscription['eventType']) and
            (not subscription.get('topic') or subscription['topic'] == event.get('topic')) and
            (not subscription.get('sourceSystem') or subscription['sourceSystem'] == event.get('sourceSystem')) and
            set(subscription.get('tags', [])).issubset(event.get('tags', [])))


def specificity(sub):
    return (sub.get('rank', 100), sub['eventType'].count('*'),
            -sum(bool(sub.get(k)) for k in ['topic', 'sourceSystem', 'tags']), sub['id'])


def allowed(s, user, delivery):
    import platform_domain as d
    p=s['platform'];event=d.find(p['events'],delivery['eventId'])
    if not event or event.get('denyAll') or not user['enabled'] or not d.in_region(user,event):return False
    roles=event.get('allowedRoles',[])
    if roles and user['role'] not in roles:return False
    if not any((sub:=d.find(p['subscriptions'],sid)) and sub.get('enabled') and sub['recipientId']==user['id'] and sub['channelId']==delivery['channelId'] and matches(sub,event) for sid in delivery.get('subscriptionIds',[delivery['subscriptionId']])):return False
    if event['type'].startswith('workflow.'):
        case=d.find(p['cases'],event['aggregateId'])
        return bool(case and (d.can_case(user,case) or (d.in_region(user,case) and d.can_handle(p,user,case))))
    return True


def execute(s,u,action,payload):
    import platform_domain as d
    p=s['platform']
    if action=='platform.ingestEvent':
        require(d.is_admin(u),'当前演示接入需要平台管理员',403)
        source=d.find(p['eventSources'],payload.get('sourceId'));require(source and source.get('enabled'),'事件源不可用')
        event_type=payload.get('eventType',source['type'].replace('*','received'))
        require(isinstance(event_type,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',event_type) and fnmatch.fnmatchcase(event_type,source['type']),'事件类型不匹配')
        data=deepcopy(payload.get('data',{}));require(isinstance(data,dict),'事件数据必须为对象')
        schema=source.get('schema',{});defaults=source.get('defaults',{})
        for key,value in defaults.items():data.setdefault(key,deepcopy(value))
        kinds={'string':str,'number':(int,float),'boolean':bool,'object':dict,'array':list}
        for key,kind in schema.items():
            require(key in data and isinstance(data[key],kinds[kind]) and not (kind=='number' and isinstance(data[key],bool)),'事件字段缺失或类型错误：'+key)
        event_id=d.text(payload.get('eventId',''),100);require(event_id,'来源事件ID必填，用于去重')
        region=payload.get('region',u['region']);require(region in ['全区','呼和浩特市','包头市','鄂尔多斯市','赤峰市','呼伦贝尔市'],'事件区域无效')
        tags=payload.get('tags',[]);require(isinstance(tags,list) and len(tags)<=20 and all(isinstance(t,str) and len(t)<=50 for t in tags),'标签格式无效')
        row=dict(id='ingress_'+source['id']+'_'+event_id,name=d.text(payload.get('name',event_id),100),rev=1,region=region,category='外部事件',topic=d.text(payload.get('topic',''),100),tags=tags,sourceSystem=source.get('sourceSystem',source['id']),data=data)
        d.emit(p,u,event_type,row)
        return next(deepcopy(e) for e in p['events'] if e['aggregateId']==row['id'] and e['type']==event_type)
    if action=='platform.pull':
        user=d.find(s['users'],payload.get('userId',u['id']))
        require(user and (user['id']==u['id'] or d.is_admin(u)),'不能代替此用户拉取',403)
        channel=d.find(p['channels'],payload.get('channelId'))
        require(channel and channel.get('enabled') and channel['type']=='拉取队列','通道不是有效拉取队列')
        limit=payload.get('limit',5);require(isinstance(limit,int) and 1<=limit<=20,'每次拉取1至20条')
        d.dispatch(s);items=[]
        ordered=sorted(p['deliveries'],key=lambda r:((d.find(p['events'],r['eventId']) or {}).get('priority',99),r['at']))
        for delivery in ordered:
            if len(items)>=limit:break
            if delivery['channelId']!=channel['id'] or delivery['recipientId']!=user['id'] or delivery['status']!='待拉取':continue
            if not allowed(s,user,delivery):delivery.update(status='已取消',error='消费权限已失效');continue
            delivery.update(status='消费中',attempt=delivery['attempt']+1,receiptToken=d.ident('receipt_'),leaseUntil=(datetime.now()+timedelta(seconds=30)).isoformat(timespec='seconds'))
            event=deepcopy(d.find(p['events'],delivery['eventId']));sub=d.find(p['subscriptions'],delivery['subscriptionId'])
            if sub and sub.get('contentMode')=='摘要':event.pop('data',None)
            items.append(dict(deliveryId=delivery['id'],receiptToken=delivery['receiptToken'],leaseUntil=delivery['leaseUntil'],event=event))
        return dict(items=items,note='30秒内提交业务ACK；租约过期进入重试，消费者应按事件ID幂等处理。')
    if action=='platform.ack':
        delivery=d.find(p['deliveries'],payload.get('deliveryId'));require(delivery,'投递不存在',404)
        user=d.find(s['users'],delivery['recipientId'])
        require(user and (user['id']==u['id'] or d.is_admin(u)) and allowed(s,user,delivery),'没有消费此消息的权限',403)
        require(payload.get('receiptToken') and payload['receiptToken']==delivery.get('receiptToken'),'回执令牌无效',409)
        outcome=payload.get('outcome');require(outcome in ['成功','失败'],'请选择业务处理结果')
        if delivery.get('ackToken')==payload['receiptToken']:
            require(delivery.get('ackOutcome')==outcome,'同一回执不能更改处理结果',409)
            return dict(ok=True,status=delivery['status'],duplicate=True)
        require(delivery['status']=='消费中' and delivery['leaseUntil']>d.now(),'消费租约已过期，请重新拉取',409)
        delivery.update(ackToken=payload['receiptToken'],ackOutcome=outcome,ackNote=d.text(payload.get('note',''),1000))
        if outcome=='成功':delivery.update(status='已处理',processedAt=d.now(),error='')
        else:delivery.update(status='失败队列' if delivery['attempt']>=3 else '等待重试',nextRetryAt=(datetime.now()+timedelta(seconds=2**delivery['attempt'])).isoformat(timespec='seconds'),error='消费方业务处理失败')
        return dict(ok=True,status=delivery['status'])
    return None
