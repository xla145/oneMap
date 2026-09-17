"""Fictional, versioned fixtures for application/platform demonstrations."""
from copy import deepcopy
from datetime import datetime, timedelta


def record(ident, name, **fields):
    return dict(id=ident, name=name, rev=1, version=1, status='已发布', updated=datetime.now().isoformat(timespec='seconds'), **fields)


def versioned(ident, name, **fields):
    row = record(ident, name, **fields)
    row['published'] = deepcopy(row)
    row['versions'] = []
    return row


def fixtures():
    config = dict(engine='local-2d', crs='EPSG:4490', theme='forest', defaultBase='base-terrain',
                  basemaps=[dict(id='base-terrain', name='自然地理', category='基础底图', crs='EPSG:4490'), dict(id='base-gray', name='浅色底图', category='基础底图', crs='EPSG:4490')],
                  layers=[dict(id='layer_demo', resourceId='r_scene_demo', name='耕地监测示例', group='耕地保护/监测数据', visible=True, opacity=0.8), dict(id='layer_farmland', resourceId='r11', name='永久基本农田', group='耕地保护/管控边界', visible=True, opacity=0.7)],
                  widgets=[dict(id='w_layers', version=1, terminal='桌面/移动', params={}), dict(id='w_query', version=1, terminal='桌面/移动', params={}), dict(id='w_measure', version=1, terminal='桌面', params={}), dict(id='w_ai', version=1, terminal='桌面/移动', params={'agentId': 'a3'})],
                  extent=[96, 36, 127, 54], camera=[111.7, 40.8, 100000], highlight='#d8983b', drawing='#287963', serviceSearch='', serviceSpatial='', serviceGeometry='')
    template = versioned('st_cropland', '耕地保护标准模板', description='二三维场景的可复用配置起点；当前运行本地二维示例。', logo='', config=deepcopy(config), region='全区', ownerOrgId='org_hall')
    scenes = [versioned('scene_cropland', '耕地保护专题', description='汇聚耕地监测、管控边界和指标知识，在地图中开展业务分析。', templateId=template['id'], config=deepcopy(config), region='全区', ownerOrgId='org_hall')]
    form = versioned('form_project', '项目辅助审查表单', type='内部表单', externalUrl='', fields=[dict(key='projectName', label='项目名称', type='text', required=True), dict(key='area', label='用地面积（公顷）', type='number', required=True), dict(key='purpose', label='建设用途', type='textarea', required=True)], region='全区')
    workflow = versioned('wf_review', '项目审查流程', description='顺序人工办理；已发布版本固定到新实例。', nodes=[dict(id='initial', name='材料初审', assigneeId='reviewer', hours=8), dict(id='final', name='业务复核', assigneeId='admin', hours=16)], formId=form['id'], timePolicyId='ba_hours', knowledgeIds=['k1'], region='全区', deployed=True)
    models = [versioned('bm_project', '项目辅助审查', category='业务审批', systemId='bs_land', formId=form['id'], workflowId=workflow['id'], ruleIds=['ba_rule'], sceneId='scene_cropland', description='核对项目材料、用地面积与业务依据。', region='全区'), versioned('bm_consult', '耕地保护数字会商', category='数字会商', systemId='bs_land', formId=form['id'], workflowId=workflow['id'], ruleIds=[], sceneId='scene_cropland', description='围绕耕地保护事项发起部门协同会商。', region='全区')]
    apps = []
    for ident, name, typ, target, category, description in [
        ('app_cropland','耕地保护专题','scene','scene_cropland','耕地保护','在一张地图中查看耕地监测、管控边界与指标分析。'),
        ('app_project','项目辅助审查','workflow','bm_project','用途管制','从材料填报到业务复核，跟踪每一步办理进度。'),
        ('app_consult','数字会商工作台','workflow','bm_consult','协同会商','汇聚事项、知识与地图，开展跨岗位协同办理。'),
        ('app_agent','自然资源检索助手','agent','a1','智能服务','用自然语言发现库表、图层、工具与知识资源。')]:
        row = record(ident,name,type=typ,targetId=target,category=category,description=description,region='全区',ownerOrgId='org_hall',owner='自然资源业务服务组',icon='',screenshots='',terminal='桌面/移动',entry='',listed=True,views=0,reviews=[])
        row['status']='已上架'
        row['published']=deepcopy(row)
        if typ=='scene': row['published']['targetSnapshot']=deepcopy(scenes[0])
        apps.append(row)
    widgets=[]
    for ident,name,kind,desc in [('w_layers','图层控制','layers','切换图层显示与隐藏'),('w_query','属性查询','query','点击图斑查看示例属性'),('w_measure','面积量算','measure','绘制范围计算球面近似面积'),('w_ai','智能辅助','assistant','将区域与场景带入已发布智能体')]:
        widgets.append(versioned(ident,name,groupId='wg_common',code=kind,description=desc,engine='local-2d',terminal='桌面/移动',mapState='二维',entry='builtin:'+kind,packageName='',params={},region='全区'))
    now=datetime.now()
    cases=[]
    for n,model in enumerate(models):
        case=record('case_demo_'+str(n+1), ['黄河沿岸示例项目辅助审查','耕地保护联合会商'][n], modelId=model['id'], category=model['category'], projectId='project_demo_'+str(n+1), userId='u1', region='包头市', formData={'projectName':['黄河沿岸示例项目','耕地保护会商'][n], 'area':128.6+n*20,'purpose':'用于展示事项流转与统计口径'}, workflow=deepcopy(workflow['published']),form=deepcopy(form['published']),nodeIndex=0,assigneeId='reviewer',createdAt=(now-timedelta(days=1)).isoformat(timespec='seconds'),dueAt=(now+timedelta(hours=8)).isoformat(timespec='seconds'),history=[dict(at=now.isoformat(timespec='seconds'),actor='林晓',action='提交',text='提交示例材料，进入材料初审')],commands={},compliance='待核查',subtasks=[],pausedAt=None,completedAt=None,ruleResults=[])
        case['status']='在办';cases.append(case)
    return dict(meta=[dict(id='schema',version=3)], sceneTemplates=[template], scenes=scenes, widgets=widgets, widgetGroups=[record('wg_common','通用地图控件')], apps=apps,
        businessGroups=[record('bg_land','自然资源业务')], businessSystems=[record('bs_land','用途管制与耕地保护',groupId='bg_land')],models=models, forms=[form],workflows=[workflow],cases=cases,delegations=[],
        businessAssets=[record('ba_hours','标准工作时段',kind='上下班管理',code='office_hours',value='09:00-12:00,14:00-18:00',description='周一至周五；节假日/调休由日历管理补充',region='全区'),record('ba_phrase','材料符合要求',kind='常用语管理',code='approved_phrase',value='材料齐全，符合本节点办理要求。',region='全区'),record('ba_rule','用地面积有效性',kind='业务规则',code='area_valid',value='area > 0',description='校验用地面积为正值；演示规则不替代真实业务审查。',region='全区'),record('ba_param','面积提醒阈值',kind='参数库',code='area_threshold',value='200',region='全区'),record('ba_var','项目用地面积',kind='变量库',code='project_area',value='area',region='全区'),record('ba_constant','面积单位',kind='常量库',code='area_unit',value='公顷',region='全区'),record('ba_template','办理意见文书',kind='模板管理',code='case_note',value='项目：{{projectName}}\n用地面积：{{area}} 公顷\n用途：{{purpose}}',region='全区'),record('ba_op','节点办理通过',kind='操作管理',code='complete',value='complete',region='全区'),record('ba_signature','管理员演示签名',kind='签名管理',code='admin_signature',value='管理员',ownerId='admin',region='全区')],
        organizations=[record('org_hall','自治区自然资源厅（演示）',parentId='',region='全区'),record('org_cropland','耕地保护处',parentId='org_hall',region='全区'),record('org_geo','地灾防治处',parentId='org_hall',region='呼和浩特市')],
        authClients=[record('client_portal','统一门户',appId='portal',key='demo_portal',mfa=False,enabled=True,protocol='本地演示会话',entry='#/front/home'),record('client_map','场景应用',appId='app_cropland',key='demo_map',mfa=False,enabled=True,protocol='本地演示会话',entry='#/front/scenes/scene_cropland')],bindings=[],loginEvents=[],identitySync=[],
        routes=[record('gw_resources','资源检索接口',path='/resources/search',requiredRole='业务用户',limit=10,timeout=1000,upstreams=['up_a','up_b'],enabled=True)],upstreams=[record('up_a','本地资源实例 A',enabled=True,latency=24),record('up_b','本地资源实例 B',enabled=True,latency=42)],gatewayCalls=[],
        eventSources=[record('es_app','应用运营事件',type='app.*',priority=2,enabled=True),record('es_workflow','业务流程事件',type='workflow.*',priority=1,enabled=True),record('es_resource','资源申请事件',type='resource.*',priority=2,enabled=True),record('es_identity','权限变更事件',type='identity.*',priority=1,enabled=True)],
        subscriptions=[record('sub_work','我的办件动态',eventType='workflow.*',recipientId='u1',channelId='ch_inbox',enabled=True),record('sub_apps','应用发布动态',eventType='app.*',recipientId='u1',channelId='ch_inbox',enabled=True)],
        channels=[record('ch_inbox','站内消息',type='站内消息',enabled=True,concurrency=1,failMode=False),record('ch_webhook','本地 Webhook 示例',type='本地示例接收端',enabled=True,concurrency=1,failMode=True)],events=[],deliveries=[],notifications=[],audit=[],recentApps=[])


def migrate(state):
    if 'platform' not in state or not state['platform'].get('meta'):
        state['platform']=fixtures()
    platform=state['platform']
    for entity in ['sceneTemplates','scenes','widgets','widgetGroups','apps','businessGroups','businessSystems','models','forms','workflows','cases','delegations','businessAssets','organizations','authClients','bindings','loginEvents','identitySync','routes','upstreams','gatewayCalls','eventSources','subscriptions','channels','events','deliveries','notifications','audit','recentApps','registrations']:
        platform.setdefault(entity,[])
    for user in state['users']:
        user.setdefault('orgId','org_cropland' if user['id']=='u1' else 'org_geo' if user['id']=='u2' else 'org_hall')
        user.setdefault('rev',1)
    extra=[dict(id='org_admin',name='单位管理员',role='单位管理员',department='地灾防治处',region='呼和浩特市',orgId='org_geo',enabled=True,rev=1),dict(id='app_manager',name='应用管理员',role='应用管理员',department='应用服务组',region='全区',orgId='org_hall',enabled=True,rev=1),dict(id='flow_manager',name='流程管理员',role='流程管理员',department='业务协同组',region='全区',orgId='org_hall',enabled=True,rev=1)]
    existing={u['id'] for u in state['users']}
    for user in extra:
        if user['id'] not in existing: state['users'].append(user)
    for entity in ['projects', 'supervisions', 'dashboards', 'helpDocs']:
        platform.setdefault(entity, [])
    for case in platform['cases']:
        if not any(r['id'] == case['projectId'] for r in platform['projects']):
            platform['projects'].append(record(case['projectId'], case['formData'].get('projectName', case['name']), type='其他项目', region=case['region'], ownerId=case['userId']))
    if not any(r.get('id') == 'detailed-requirements-v1' for r in platform['meta']):
        for key, name, body in [
            ('overview', '产品概括', '应用中心连接地图场景、业务事项与智能助手。应用通过审核后在门户提供服务，资源访问仍独立校验授权。'),
            ('guide', '使用指南', '1. 应用中心选择场景或事项。\n2. 选择已有项目或新建项目，填写申请材料。\n3. 提交后在我的待办/办件台账查看节点、时限和办理历史。\n4. 办理人填写意见并完成节点；代理、协办和督办均保留轨迹。'),
            ('integration', '接入流程', '地图：配置模板→预览→创建场景→应用注册→提交审核。\n业务：创建表单→发布→检查/部署流程→发布→关联事项→注册应用。\n外部认证和三维引擎显示待接入，不会被当作可运行应用上架。'),
            ('api', '接口文档', '本地接口 POST /api/action，Content-Type: application/json。\n演示身份头 X-Demo-User: u1（仅本地原型）。\n请求：{"action":"platform.caseDetail","payload":{"id":"case_demo_1"}}\n响应：办件对象，包含 id/status/formData/workflow/history/rev。\n更新需携带 rev；办理需 requestId 保证幂等。400 参数无效，403 无权限，404 不存在，409 版本冲突。\n示例场景读取：platform.sceneRuntime，payload 为 {"id":"scene_cropland"}。'),
            ('faq', '常见问题', '应用进入失败：检查上架状态及目标是否停用。\n图层不可见：先申请资源权限。\n待办为空：确认当前办理身份或代理有效期。\n保存冲突：刷新并重新检查最新配置后提交。\n外部服务待接入：当前未连接真实提供方。'),
            ('manual', '操作手册', '申请人可在无办理动作时撤回；办理人可完成、协办、委办或回退前序节点；流程管理员可挂起、恢复、作废、发起/解除督办并核查合规状态。\n时间统计可按创建时间或办结时间筛选；项目按项目ID去重，面积为匹配办件登记面积之和。')]:
            platform['helpDocs'].append(record('help_'+key, name, body=body, category=key))
        platform['meta'].append(dict(id='detailed-requirements-v1', version=1))
    if not any(r['id']=='r_scene_demo' for r in state['resources']):
        state['resources'].append(versioned('r_scene_demo','耕地监测示例图层',type='图层服务',subtype='图层服务',sourceType='服务',category='耕地保护',region='全区',aliases='耕地,监测,图斑',frequency='每月',access='已授权',visibility='业务用户',source='本地编制的虚构演示数据',description='用于场景运行和权限验证的示例图斑，不对应真实地块。',crs='CGCS2000',fields=[dict(name='area',label='面积',type='decimal',display=True,query=True,aggregate=True,statistic=True,unit='公顷',description='演示地块面积')],relations=[],templateId='',documentId='',dataRows='',sample=[],date=datetime.now().date().isoformat()))
    return platform
