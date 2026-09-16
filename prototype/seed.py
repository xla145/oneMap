"""Deterministic, fictional natural-resource demo fixtures."""
from copy import deepcopy
from capabilities import migrate
from datetime import date, timedelta

REGIONS = ['全区', '呼和浩特市', '包头市', '鄂尔多斯市', '赤峰市', '呼伦贝尔市']
TYPES = ['数据库表', '图层服务', '工具服务', '知识文档']

def seed():
    today = date.today().isoformat()
    def record(id, name, **kw):
        r = dict(id=id, name=name, status='已发布', version=1, rev=1, updated=today, **kw)
        r['published'] = deepcopy(r)
        r['versions'] = []
        return r
    fields = [dict(name='region_code', label='行政区代码', alias='区划编码', type='varchar', unit='', query=True, display=True, aggregate=False, dictionary='行政区划', location='行政区', topic='基础信息', statistic=False, description='对应资源覆盖的行政区'), dict(name='area', label='面积', alias='用地面积', type='decimal', unit='公顷', query=True, display=True, aggregate=True, dictionary='', location='无', topic='耕地保护', statistic=True, description='示例统计面积'), dict(name='updated_at', label='更新时间', alias='采集日期', type='date', unit='', query=True, display=True, aggregate=False, dictionary='', location='无', topic='基础信息', statistic=False, description='记录最近一次维护日期')]
    specs = [
        ('r1','地质灾害巡查记录表','数据库表','地灾防治','呼和浩特市','地灾巡查,隐患点,巡查记录,地质灾害','每日','可申请'),
        ('r2','耕地保护监测数据集','数据库表','耕地保护','全区','耕地,农田,保护,面积,土地','每月','已授权'),
        ('r3','地灾隐患点分布图层','图层服务','地灾防治','呼和浩特市','地灾,隐患点,分布,巡查','每周','可申请'),
        ('r4','耕地变化监测工具','工具服务','耕地保护','全区','耕地,监测,工具,变化,农田','每月','可申请'),
        ('r5','耕地占补平衡业务指南','知识文档','耕地保护','全区','耕地,占补平衡,政策,指南','每年','已授权'),
        ('r6','矿业权基础信息表','数据库表','矿产资源','鄂尔多斯市','矿权,矿产,到期,采矿','每日','可申请'),
        ('r7','生态修复项目分布图层','图层服务','生态修复','赤峰市','生态,修复,项目,植被','每月','已授权'),
        ('r8','地灾风险辅助评估工具','工具服务','地灾防治','全区','地灾,巡查,评估,风险,工具','每周','可申请'),
        ('r9','国土空间规划技术指引','知识文档','国土规划','全区','国土,空间,规划,技术,规范','每年','已授权'),
        ('r10','草原植被覆盖监测数据','数据库表','生态修复','呼伦贝尔市','植被,草原,覆盖率,生态','每月','已授权'),
        ('r11','永久基本农田示例图层','图层服务','耕地保护','全区','耕地,农田,保护,边界','每年','可申请'),
        ('r12','内部不可发现资源','数据库表','地灾防治','全区','保密数据','每日','可申请'),
    ]
    resources = [record(id, name, type=typ, category=cat, region=reg, aliases=aliases, frequency=freq, access=access, visibility='管理员' if id=='r12' else '业务用户', source='自治区自然资源示例数据中心', description=f'面向{cat}业务提供的{typ}，支持资源发现、业务理解与协同使用。数据为原型演示编制。', crs='CGCS2000', fields=deepcopy(fields), relations=['r3'] if id=='r1' else [], templateId='mt1', documentId='k1' if id=='r5' else 'k2' if id=='r9' else '', sample=[{'行政区':'呼和浩特市','记录':'示例记录 01','面积（公顷）':128.6},{'行政区':'呼和浩特市','记录':'示例记录 02','面积（公顷）':96.4}], date=today) for id,name,typ,cat,reg,aliases,freq,access in specs]
    docs = [record('k1','耕地占补平衡业务指南',category='政策法规',source='自然资源业务示例知识库',tags='耕地,占补平衡,政策',body='耕地占补平衡是指建设占用耕地时，应按相关要求补充数量和质量相当的耕地。\n\n开展业务核查时，应核对占用与补充地块的位置、面积及质量，并保留相关依据。\n\n本指南为原型演示编写，不作为实际行政审批或政策解释依据。',relations='耕地保护 → 占补平衡 → 数量与质量',process='可用'),record('k2','国土空间规划技术指引',category='技术规范',source='规划管理示例知识库',tags='国土,空间,规划,技术',body='国土空间规划统筹生态、农业和城镇空间，结合区域资源环境条件组织空间布局。\n\n数据检索需核对成果版本、适用范围和坐标系，并以批准成果为依据。\n\n本文为演示素材。',relations='规划成果 → 空间布局 → 数据版本',process='可用')]
    for d in docs:
        d['chunks']=[{'id':f"{d['id']}-c{i+1}",'text':s} for i,s in enumerate(d['body'].split('\n\n'))]
        d['published']=deepcopy({k:v for k,v in d.items() if k not in ['published','versions']})
    indicators=[record('i1','耕地保有量',category='耕地保护',unit='公顷',formula='sum',values='128.6,96.4,175',caliber='同一统计期内有效耕地图斑面积求和；示例数据不含重叠地块。',period='2026年',region='呼和浩特市',resourceId='r2',field='area',description='衡量区域内纳入统计的耕地面积。'),record('i2','植被覆盖率',category='生态修复',unit='%',formula='average',values='61,68,72',caliber='对三个示例监测单元的覆盖率取算术平均值。',period='2026年',region='呼伦贝尔市',resourceId='r10',field='area',description='示例监测单元的平均植被覆盖情况。')]
    corpora=[record('c1','资源检索意图识别',type='提示词模板',scene='资源检索',body='请在 {{region}} 范围检索 {{question}}，返回资源名称、类型、更新频次和使用状态。',variables='region,question',answer='',resourceIds='r1,r3',category='资源检索'),record('c2','地灾巡查标准问答',type='问答样例',scene='资源检索',body='找最近的地灾巡查记录表',answer='建议优先查阅地质灾害巡查记录表，并结合隐患点分布图层核对位置。',variables='',resourceIds='r1,r3',category='地灾防治'),record('c3','耕地面积汇总',type='SQL 模板',scene='指标分析',body='SELECT SUM(area) AS total_area FROM demo_cropland WHERE region = :region',variables='region',answer='',resourceIds='r2',category='耕地保护')]
    agents=[record('a1','资源检索助手',category='资源检索',description='一句话找到库表、图层、工具与知识，让资源获取更简单。',icon='sparkles',color='green',question='找最近的地灾巡查记录表',steps='识别条件\n检索资源\n展示结果\n发起申请',resourceIds='',knowledgeIds='',templateIds='c1,c2',indicatorIds='',memory=True),record('a2','政策知识助手',category='知识问答',description='理解自然资源业务知识，回答有依据，引用可追溯。',icon='book',color='blue',question='什么是耕地占补平衡？',steps='理解问题\n检索知识\n回答并引用',resourceIds='',knowledgeIds='k1,k2',templateIds='',indicatorIds='',memory=True),record('a3','指标分析助手',category='指标分析',description='看懂业务指标与统计口径，让每个数字都有出处。',icon='chart',color='purple',question='查询耕地保有量指标',steps='识别指标\n核对口径\n示例试算\n展示结果',resourceIds='r2,r10',knowledgeIds='',templateIds='c3',indicatorIds='i1,i2',memory=True)]
    users=[dict(id='u1',name='林晓',role='业务用户',department='耕地保护处',region='全区',enabled=True),dict(id='u2',name='陈远',role='业务用户',department='地灾防治处',region='呼和浩特市',enabled=True),dict(id='admin',name='管理员',role='平台管理员',department='智能中心管理组',region='全区',enabled=True),dict(id='reviewer',name='审批员',role='资源审批人员',department='资源服务中心',region='全区',enabled=True)]
    state = dict(resources=resources,knowledge=docs,indicators=indicators,corpora=corpora,agents=agents,templates=[record('mt1','自然资源通用元数据模板',type='数据库表',description='适用于资源目录与库表描述',fields='名称,同义词,业务解释,行政区,坐标系,更新频次')],dictionaries=[record('dt1','行政区划',code='REGION',aliases='地区,区划',items='150100:呼和浩特市\n150200:包头市\n150600:鄂尔多斯市')],users=users,memories=[dict(id='u1',name='林晓的业务偏好',region='全区',domain='耕地保护',detail='简洁',enabled=True,summary='关注耕地保护业务，偏好简洁说明。',rev=1),dict(id='u2',name='陈远的业务偏好',region='呼和浩特市',domain='地灾防治',detail='详细',enabled=True,summary='关注地灾隐患与巡查数据。',rev=1)],sessions=[],applications=[],grants=[],feedback=[],calls=[],audit=[])

    return migrate(state)
