"""Detailed requirement support; local business behavior, without external adapters."""
import ast
import base64
import json
import re
from copy import deepcopy
from datetime import datetime
from capabilities import Invalid, require


def image_value(value):
    if not value:
        return
    require(isinstance(value, str) and len(value) <= 350000, '单张图片不能超过约250KB')
    match = re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)', value)
    require(match, '仅支持PNG、JPEG、WebP图片')
    try:
        raw = base64.b64decode(match[2], validate=True)
    except ValueError:
        raise Invalid('图片编码无效')
    valid = (match[1] == 'png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (match[1] == 'jpeg' and raw.startswith(b'\xff\xd8\xff')) or (match[1] == 'webp' and raw.startswith(b'RIFF') and raw[8:12] == b'WEBP')
    require(valid, '图片类型与内容不符')


def rule_tree(expression):
    try:
        tree = ast.parse(expression, mode='eval')
    except (SyntaxError, TypeError):
        raise Invalid('规则表达式无效')
    permitted = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.Compare,
                 ast.BoolOp, ast.And, ast.Or, ast.BinOp, ast.UnaryOp, ast.Not,
                 ast.USub, ast.UAdd, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq,
                 ast.NotEq, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)
    nodes = list(ast.walk(tree))
    require(len(nodes) <= 80 and all(isinstance(n, permitted) for n in nodes), '规则只支持字段、常量、比较、布尔和受控算术')
    return tree


def validate_rule(s, expression):
    tree = rule_tree(expression)
    names = {f['key'] for form in s['platform']['forms'] for f in form.get('fields', [])}
    names |= {r['code'] for r in s['platform']['businessAssets'] if r['kind'] in ['变量库', '参数库', '常量库']}
    missing = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - names
    require(not missing, '规则变量未定义：' + '、'.join(sorted(missing)))


def rule_context(p, data, expression):
    context = dict(data)
    library = {r['code']: r for r in p['businessAssets'] if r['kind'] in ['变量库', '参数库', '常量库'] and r.get('status') != '已停用'}

    def resolve(name, path):
        if name in context:
            return context[name]
        require(name not in path, '变量循环引用：' + name)
        item = library.get(name)
        require(item, '规则变量不存在：' + name)
        if item['kind'] == '变量库':
            value = resolve(item['value'].strip(), path + [name])
        else:
            typ = item.get('valueType', '自动')
            try:
                value = json.loads(item['value']) if typ != '文本' else item['value']
            except (ValueError, TypeError):
                require(typ in ['自动', '文本'], '库值与类型不符：' + name)
                value = item['value']
        context[name] = value
        return value

    for n in ast.walk(rule_tree(expression)):
        if isinstance(n, ast.Name):
            resolve(n.id, [])
    return context


def todo(p, u, case):
    import platform_domain as d
    return case['status'] == '在办' and d.in_region(u, case) and (
        case['assigneeId'] == u['id'] or any(t['userId'] == u['id'] and t['status'] == '待办' for t in case.get('subtasks', [])) or
        (not d.is_admin(u) and d.can_handle(p, u, case)))


def ensure_app(s, app, strict=True):
    import platform_domain as d
    p = s['platform']
    typ = app['type']
    source = {'scene': p['scenes'], 'workflow': p['models'], 'agent': s['agents'], 'external': p['authClients']}[typ]
    target = d.find(source, app['targetId'])
    require(target and target.get('status') != '已停用', '目标已停用或不存在，不能上架/运行')
    if typ == 'scene':
        scene = app.get('targetSnapshot', target)
        if strict:
            d.scene_validate(s, scene)
        require(scene['config']['engine'] == 'local-2d', '三维引擎未接入，不能发布为可运行应用')
    elif typ == 'workflow':
        model = d.published(target)
        require(model, '关联事项未发布')
        form = d.published(d.find(p['forms'], model['formId']))
        flow = d.published(d.find(p['workflows'], model['workflowId']))
        require(form and flow, '关联表单或流程未发布')
        require(form['type'] != '外部表单', '外部表单运行适配器未接入')
    elif typ == 'agent':
        require(d.cap.published(target), '关联智能体未发布')
    else:
        require(target.get('enabled') and target.get('protocol') == '本地演示会话', '外部认证协议未接入或客户端已停用')


def task_events(s, u, case, command='created'):
    import platform_domain as d
    p = s['platform']
    d.emit(p, u, 'workflow.progress.' + command, case, case['userId'])
    if case['status'] != '在办':
        return
    receivers = {case['assigneeId']}
    receivers |= {t['userId'] for t in case.get('subtasks', []) if t['status'] == '待办'}
    for user in s['users']:
        if user['enabled'] and not d.is_admin(user) and d.can_handle(p, user, case) and d.in_region(user, case):
            receivers.add(user['id'])
    for receiver in sorted(receivers):
        # Direct user tasks always have a local inbox subscription. External systems
        # still require explicit subscriptions and do not receive this implicitly.
        if not any(r.get('enabled') and r['recipientId'] == receiver and r['channelId'] == 'ch_inbox' and r['eventType'] in ['workflow.*', '*'] for r in p['subscriptions']):
            p['subscriptions'].append(dict(id=d.ident('auto_sub_'), name='我的办理任务', rev=1, version=1, status='已发布', eventType='workflow.*', recipientId=receiver, channelId='ch_inbox', enabled=True, automatic=True, updated=d.now()))
        d.emit(p, u, 'workflow.task.' + command, case, receiver)


def execute(s, u, action, payload):
    import platform_domain as d
    p = s['platform']
    if action == 'platform.compliance':
        case = d.find(p['cases'], payload.get('id'))
        require(case and d.can_case(u, case), '办件不可访问', 404)
        require(d.is_admin(u) or u['role'] == '流程管理员' or d.can_handle(p, u, case), '没有核查权限', 403)
        d.revision(case, payload)
        require(case['status'] not in ['已撤回', '已作废'], '终止事项不能核查')
        value = payload.get('compliance'); note = d.text(payload.get('note', ''))
        require(value in ['待核查', '合规', '不合规'] and note, '请选择核查结果并填写依据')
        case.update(compliance=value, rev=case['rev'] + 1, updated=d.now())
        case['history'].append(dict(at=d.now(), actor=u['name'], userId=u['id'], action='compliance', text=value + '：' + note))
        d.audit(p, u, '合规核查', case)
        d.emit(p, u, 'workflow.compliance.changed', case, case['userId'])
        return case
    if action == 'platform.supervise':
        require(d.is_admin(u) or u['role'] == '流程管理员', '督办需要流程管理权限', 403)
        case = d.find(p['cases'], payload.get('caseId'))
        require(case and d.can_case(u, case), '办件不可访问', 404)
        note = d.text(payload.get('note', '')); require(note, '请填写督办说明')
        current = d.find(p['supervisions'], payload.get('id'))
        if current:
            require(current['caseId'] == case['id'], '督办与办件不匹配')
            d.revision(current, payload)
            current.update(status='已解除', result=note, rev=current['rev'] + 1, completedAt=d.now())
        else:
            require(case['status'] in ['在办', '已挂起'], '已结束事项无需督办')
            current = dict(id=d.ident('supervise_'), caseId=case['id'], name=case['name'], status='督办中', note=note, createdAt=d.now(), ownerId=u['id'], assigneeId=case['assigneeId'], rev=1)
            p['supervisions'].append(current)
            d.emit(p, u, 'workflow.supervision.created', case, case['assigneeId'])
        d.audit(p, u, '维护督办', current)
        return current
    if action == 'platform.dashboard':
        allowed = ['apps', 'overview', 'todo', 'supervision', 'messages', 'guides']
        modules = payload.get('modules', allowed)
        require(isinstance(modules, list) and len(modules) == len(set(modules)) and all(x in allowed for x in modules), '首页组件不正确')
        row = d.find(p['dashboards'], u['id'])
        value = dict(id=u['id'], modules=modules)
        if row: row.update(value)
        else: p['dashboards'].append(value)
        return value
    if action == 'platform.flowCheck':
        require(d.manage(u, 'workflows'), '无流程管理权限', 403)
        workflow = deepcopy(payload.get('workflow') or d.find(p['workflows'], payload.get('id')))
        require(workflow, '流程不存在')
        d.validate(s, 'workflows', workflow)
        return dict(valid=True, nodes=workflow['nodes'], checks=['节点编码唯一', '办理人有效', '节点时限有效', '关联表单存在'], warnings=[] if d.published(d.find(p['forms'], workflow['formId'])) else ['表单尚未发布，事项暂不可运行'])
    return None
