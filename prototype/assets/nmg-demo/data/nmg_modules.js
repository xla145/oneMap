// 内蒙古自然资源一张图 —— 四大业务模块功能清单
// 每项功能含：业务定义 / 法规依据 / 业务流程 / 输入输出 / 关联图层 / 统计口径 / AI 标准问句
// 数据来源：NMG_NR（28 图层 1018 要素）、NMG_POI（矿产地 / 保护地 / 河湖 / 修复 / 执法图斑）
(function () {

  /* 通用：指标聚合声明
     count  : 图层要素计数            { t:'count', layer:'xxx' }
     sum    : 面积求和（亩→万亩/万m²）{ t:'sum', layer:'xxx', f:'area_mu', div:10000 }
     appr   : 审批状态计数            { t:'appr', layer:'xxx', v:'已备案' }
     series : 时序最新值              { t:'series', k:'forestCover' }
     static : 静态值                  { t:'static', v:'21.98' }
  */

  const MODULES = [

    /* ============================================================
       一、调查监测（DC）
       ============================================================ */
    {
      key: 'dc', code: 'DC', name: '调查监测', en: 'Survey & Monitoring', color: '#0f7b6c',
      goal: '构建"统一底图、统一标准、统一规划、统一平台"的自然资源调查监测体系，实现"一查多用、一库多能"，为自然资源管理提供现势性数据底座。',
      basis: '《自然资源调查监测体系构建总体方案》（自然资发〔2020〕15号）、《国土空间调查、规划、用途管制用地用海分类指南》、《国土变更调查技术规程》TD/T 1055',
      groups: [
        {
          g: '基础调查', items: [
            {
              id: 'DC-01', n: '年度国土变更调查', tag: '核心', period: '年度', owner: '调查监测处 / 自治区国土空间规划院', status: '已建',
              desc: '以年度遥感影像为底图，对上一年度土地利用现状库进行全地类变化更新，形成年度土地利用现状数据库与地类流量表，是自然资源管理统一的底数、底版。',
              basis: 'TD/T 1055《国土变更调查技术规程》；《土地调查条例》',
              flow: ['遥感影像统筹与正射纠正', '内业全地类变化信息提取', '外业互联网+举证核查', '县级数据库更新与自检', '市级复核', '自治区级核查', '国家级核查确认', '地类流量核算与成果入库'],
              io: {
                in: ['年度优于 1m 分辨率遥感影像', '上一年度土地利用现状库', '用地审批、供地、登记等管理信息', '林草湿专项调查成果'],
                out: ['年度土地利用现状数据库', '年度地类流向流量表', '年度土地利用现状图', '变更调查分析报告']
              },
              layers: ['changeSurvey', 'landUsePatch'],
              mets: [
                { l: '变更图斑', u: '个', agg: { t: 'count', layer: 'changeSurvey' } },
                { l: '涉及面积', u: '万亩', agg: { t: 'sum', layer: 'changeSurvey', f: 'area_mu', div: 10000 } },
                { l: '已备案图斑', u: '个', agg: { t: 'appr', layer: 'changeSurvey', v: '已备案' } }
              ],
              chart: { t: 'pie', layer: 'changeSurvey', by: 'type', title: '变更图斑类型构成' },
              table: { layer: 'changeSurvey', cols: ['name', 'type', 'city', 'county', 'area_mu', 'surveyType', 'approval', 'updateTime'] },
              asks: ['2025年度国土变更调查图斑有多少个、涉及多少面积', '变更调查图斑按变更类型分布如何', '哪些旗县的变更图斑最多']
            },
            {
              id: 'DC-02', n: '遥感影像统筹与覆盖监测', tag: '核心', period: '季度', owner: '调查监测处 / 遥感中心', status: '已建',
              desc: '统筹全区遥感影像获取计划，管理影像档案与覆盖状态，按季度/月度统计影像现势性，支撑变更调查、执法督察、生态监测共用同一影像底图。',
              basis: '《自然资源遥感影像统筹管理办法》；《遥感影像共享应用规定》',
              flow: ['需求征集与获取计划编制', '影像采购 / 自主获取', '正射纠正与融合镶嵌', '质量检查与入库', '分区域分时相发布', '覆盖度与时相统计', '按需分发共享'],
              io: {
                in: ['年度影像需求清单', '卫星/航空影像原始数据', 'DEM 与像控点成果'],
                out: ['影像覆盖一张图', '影像时相与现势性统计表', '分幅影像服务']
              },
              layers: ['landUsePatch', 'relief'],
              mets: [
                { l: '季度影像覆盖', u: '%', agg: { t: 'static', v: '100.0' } },
                { l: '优于1m 分辨率占比', u: '%', agg: { t: 'static', v: '86.4' } },
                { l: '当年新增影像', u: '景', agg: { t: 'static', v: '12480' } }
              ],
              chart: { t: 'line', s: ['forestCover', 'grassCover'], title: '影像支撑的年度观测指标' },
              table: { layer: 'landUsePatch', cols: ['name', 'type', 'city', 'county', 'area_mu', 'year', 'updateTime'] },
              asks: ['全区遥感影像覆盖情况如何', '最近一期影像的现势性统计']
            },
            {
              id: 'DC-03', n: '变化图斑智能提取与人工复核', tag: '新建', period: '持续', owner: '调查监测处 / 信息中心', status: '在建',
              desc: '基于深度学习变化检测模型自动提取疑似变化图斑，经人工复核confirm后进入变更调查流程，替代传统全人工目视解译，提升提取效率与一致性。',
              basis: '《自然资源部关于加强变化检测技术应用的通知》',
              flow: ['双时相影像配准', 'AI 变化检测模型推理', '疑似图斑自动矢量化', '置信度分级', '人工内业复核', '外业举证确认', '成果入库与模型迭代'],
              io: { in: ['前后时相正射影像', '上一年度现状库'], out: ['疑似变化图斑成果', '模型精度评价报告', '复核确认记录'] },
              layers: ['changeSurvey', 'construction'],
              mets: [
                { l: 'AI 提取图斑', u: '个', agg: { t: 'count', layer: 'changeSurvey' } },
                { l: '人工复核通过', u: '个', agg: { t: 'appr', layer: 'changeSurvey', v: '已备案' } },
                { l: '提取准确率', u: '%', agg: { t: 'static', v: '91.2' } }
              ],
              chart: { t: 'appr', layer: 'changeSurvey', title: '图斑复核状态分布' },
              table: { layer: 'changeSurvey', cols: ['name', 'type', 'city', 'area_mu', 'approval', 'updateTime', 'control'] },
              asks: ['AI 提取的变化图斑复核通过率是多少', '按盟市统计变化图斑数量']
            }
          ]
        },
        {
          g: '专项调查与分析评价', items: [
            {
              id: 'DC-04', n: '地类流向与流量分析', tag: '核心', period: '年度', owner: '调查监测处', status: '已建',
              desc: '基于两年度土地利用现状库叠加，生成地类转移矩阵，分析耕地、林地、草地、建设用地之间的相互转化规模与方向，识别非农化、非粮化趋势。',
              basis: '《国土变更调查地类流量分析技术要求》',
              flow: ['两年度现状库叠加求交', '生成地类转移矩阵', '流向归并（农用地/建设用地/未利用地）', '重点流向筛查（耕地流出）', '原因标注与举证关联', '形成流量分析报告'],
              io: { in: ['T 年与 T-1 年现状库', '用地审批与执法数据'], out: ['地类转移矩阵表', '主要流向桑基图', '耕地流出专题分析'] },
              layers: ['landUsePatch', 'construction', 'unused'],
              mets: [
                { l: '地类图斑总量', u: '个', agg: { t: 'count', layer: 'landUsePatch' } },
                { l: '建设用地', u: '个', agg: { t: 'count', layer: 'construction' } },
                { l: '未利用地', u: '个', agg: { t: 'count', layer: 'unused' } }
              ],
              chart: { t: 'pie', layer: 'landUsePatch', by: 'type', title: '现状地类构成' },
              table: { layer: 'landUsePatch', cols: ['name', 'type', 'city', 'county', 'area_mu', 'year', 'approval'] },
              asks: ['分析全区地类流向与流量', '哪些盟市耕地流出较多', '建设用地增加主要来自哪些地类']
            },
            {
              id: 'DC-05', n: '森林草原湿地专项调查监测', tag: '核心', period: '年度', owner: '林草局 / 调查监测处', status: '已建',
              desc: '开展森林、草原、湿地资源的种类、数量、质量、结构、分布及动态变化调查，与国土调查协同形成统一的林草湿资源底数，支撑林长制考核与碳汇核算。',
              basis: '《森林法》《草原法》《湿地保护法》；《全国森林草原湿地调查监测技术规程》',
              flow: ['样地布设与外业调查', '遥感解译与类型区划', '蓄积量/生物量建模', '植被盖度与生物量反演', '与国土调查协同衔接', '成果统计与出表', '数据发布与共享'],
              io: { in: ['样地调查数据', '多光谱/激光雷达数据', '国土调查地类界线'], out: ['林草湿资源数据库', '森林覆盖率与蓄积量表', '草原植被盖度专题图'] },
              layers: ['forest', 'grassland', 'wetland'],
              mets: [
                { l: '森林覆盖率', u: '%', agg: { t: 'series', k: 'forestCover' } },
                { l: '草原植被盖度', u: '%', agg: { t: 'series', k: 'grassCover' } },
                { l: '湿地保护率', u: '%', agg: { t: 'series', k: 'wetlandRate' } }
              ],
              chart: { t: 'line', s: ['forestCover', 'grassCover', 'wetlandRate'], title: '林草湿核心指标五年变化' },
              table: { layer: 'forest', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'updateTime'] },
              asks: ['对比呼伦贝尔和锡林郭勒的草原植被盖度并分析差异', '近五年森林覆盖率变化趋势', '各盟市湿地保护率排名']
            },
            {
              id: 'DC-06', n: '耕地质量等级调查评价', tag: '核心', period: '年度', owner: '耕地保护监督处 / 土地整理中心', status: '已建',
              desc: '通过土壤采样化验与样点监测，评定耕地质量等别（1—15 等），建立耕地质量等别数据库，为占补平衡、提质改造与耕地保护责任考核提供依据。',
              basis: '《耕地质量等级》GB/T 33469；《耕地质量调查监测与评价办法》',
              flow: ['样点布设与土壤采样', '理化指标化验', '等别指数计算', '等别评定与制图', '年度更新与变化分析', '与占补平衡挂钩应用'],
              io: { in: ['土壤采样化验数据', '耕地质量监测样点', '土地利用现状图'], out: ['耕地质量等别数据库', '耕地质量等别图', '年度质量变化分析'] },
              layers: ['farmlandQuality', 'farmlandRedline', 'primeFarmland'],
              mets: [
                { l: '监测样点', u: '个', agg: { t: 'count', layer: 'farmlandQuality' } },
                { l: '平均质量等别', u: '等', agg: { t: 'series', k: 'farmlandGrade' } },
                { l: '永久基本农田', u: '万亩', agg: { t: 'series', k: 'primeFarmland' } }
              ],
              chart: { t: 'barCityStat', f: 'geoHazards', title: '各盟市监测样点分布（示意口径）' },
              table: { layer: 'farmlandQuality', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'updateTime'] },
              asks: ['全区耕地质量平均等别是多少', '耕地质量监测样点覆盖哪些旗县', '永久基本农田近五年变化情况']
            },
            {
              id: 'DC-07', n: '全民所有自然资源资产清查', tag: '常规', period: '年度', owner: '所有者权益处', status: '在建',
              desc: '清查全民所有土地、矿产、森林、草原、湿地、水等自然资源的实物量与价值量，编制自然资源资产负债表，支撑领导干部自然资源资产离任审计。',
              basis: '《关于统筹推进自然资源资产产权制度改革的指导意见》；《自然资源资产负债表编制制度》',
              flow: ['清查范围与分类体系确定', '实物量清查（面积/储量/蓄积）', '价格体系建设', '价值量核算', '资产负债表编制', '成果审核与汇交'],
              io: { in: ['各类资源调查成果', '矿产储量数据库', '价格信号与基准价'], out: ['自然资源资产清查数据库', '自然资源资产负债表', '资产核算报告'] },
              layers: ['mineralBlock', 'forest', 'grassland', 'wetland'],
              mets: [
                { l: '矿产区块', u: '个', agg: { t: 'count', layer: 'mineralBlock' } },
                { l: '林地斑块', u: '个', agg: { t: 'count', layer: 'forest' } },
                { l: '草原斑块', u: '个', agg: { t: 'count', layer: 'grassland' } }
              ],
              chart: { t: 'pie', layer: 'mineralBlock', by: 'type', title: '矿产资源类型构成' },
              table: { layer: 'mineralBlock', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval'] },
              asks: ['全区矿产区块数量与主要矿种构成', '各类自然资源资产实物量汇总']
            },
            {
              id: 'DC-08', n: '生态状况监测评价', tag: '常规', period: '年度', owner: '国土空间生态修复处 / 生态环境厅', status: '已建',
              desc: '构建"天—空—地"一体化生态状况监测网络，评价生态格局、生态功能、生物多样性、生态胁迫等维度，形成年度生态状况监测评价报告。',
              basis: '《生态保护红线生态状况监测技术指南》；《区域生态状况评价技术规范》',
              flow: ['监测指标与权重体系构建', '遥感生态参数反演', '地面样方与样带观测', '生态状况指数计算', '分级评价与制图', '年际变化对比', '报告编制与发布'],
              io: { in: ['多源遥感数据', '生态监测样点', '气象与水土数据'], out: ['生态状况指数分布图', '年度生态状况评价报告', '生态胁迫预警清单'] },
              layers: ['ecoFunctionZone', 'forest', 'grassland', 'desert'],
              mets: [
                { l: '重点生态功能区', u: '个', agg: { t: 'count', layer: 'ecoFunctionZone' } },
                { l: '沙化土地斑块', u: '个', agg: { t: 'count', layer: 'desert' } },
                { l: '森林覆盖率', u: '%', agg: { t: 'series', k: 'forestCover' } }
              ],
              chart: { t: 'barCity', layer: 'ecoFunctionZone', by: 'area_mu', title: '各盟市重点生态功能区面积' },
              table: { layer: 'ecoFunctionZone', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['全区生态状况评价结果如何', '重点生态功能区在各盟市的分布', '沙化土地治理情况统计']
            },
            {
              id: 'DC-09', n: '地下水与土壤环境地质监测', tag: '常规', period: '月度', owner: '地质勘查管理处 / 地质环境监测院', status: '已建',
              desc: '对地下水水位、水质及土壤环境质量进行长期定位监测，开展地质灾害隐患点排查与风险评价，落实"隐患点+风险区"双控。',
              basis: '《地质环境监测管理办法》；《地下水管理条例》；《土壤污染防治法》',
              flow: ['监测网点布设与维护', '定期采样与自动传输', '数据质检与入库', '水位/水质动态分析', '污染风险评价', '预警发布与处置'],
              io: { in: ['监测井与自动监测设备数据', '土壤采样化验结果'], out: ['地下水动态监测年报', '土壤环境质量评价图', '监测预警信息'] },
              layers: ['groundwater', 'soilMonitor', 'geoHazard', 'geoRiskZone'],
              mets: [
                { l: '地下水监测点', u: '个', agg: { t: 'count', layer: 'groundwater' } },
                { l: '土壤监测点', u: '个', agg: { t: 'count', layer: 'soilMonitor' } },
                { l: '地灾隐患点', u: '处', agg: { t: 'series', k: 'geoHazard' } }
              ],
              chart: { t: 'pie', layer: 'geoHazard', by: 'type', title: '地质灾害隐患类型构成' },
              table: { layer: 'geoHazard', cols: ['name', 'type', 'city', 'county', 'scale', 'threat', 'monitor', 'approval'] },
              asks: ['全区地质灾害隐患点有多少处', '按类型统计地质灾害隐患点', '地下水与土壤监测点覆盖情况']
            },
            {
              id: 'DC-10', n: '调查监测成果质检与汇交', tag: '常规', period: '持续', owner: '调查监测处 / 信息中心', status: '已建',
              desc: '对各类调查监测成果进行拓扑检查、逻辑一致性检查、属性完整性检查，合格后汇交入库并向各业务系统分发，保证"一数一源、一源多用"。',
              basis: '《自然资源数据管理办法》；《调查监测成果汇交规范》',
              flow: ['成果接收与登记', '自动化质检（拓扑/属性/逻辑）', '人工复核与问题反馈', '整改复检', '成果入库与版本登记', '分发共享与元数据发布'],
              io: { in: ['各类调查监测成果数据集'], out: ['质检报告', '合格成果数据库', '元数据目录'] },
              layers: ['changeSurvey', 'farmlandQuality', 'landUsePatch'],
              mets: [
                { l: '待检成果', u: '个', agg: { t: 'count', layer: 'changeSurvey' } },
                { l: '质检通过', u: '个', agg: { t: 'appr', layer: 'changeSurvey', v: '已备案' } },
                { l: '一次通过率', u: '%', agg: { t: 'static', v: '87.5' } }
              ],
              chart: { t: 'appr', layer: 'changeSurvey', title: '成果汇交状态分布' },
              table: { layer: 'farmlandQuality', cols: ['name', 'type', 'city', 'county', 'approval', 'updateTime', 'control'] },
              asks: ['调查监测成果质检通过情况', '哪些成果尚未完成汇交']
            }
          ]
        }
      ]
    },

    /* ============================================================
       二、空间规划（GH）
       ============================================================ */
    {
      key: 'gh', code: 'GH', name: '国土空间规划', en: 'Territorial Spatial Planning', color: '#1a6fa8',
      goal: '建立"五级三类"国土空间规划体系，实现"一张图"管到底：规划编制、审批、实施、监督全流程数字化，三条控制线精准落地、刚性管控。',
      basis: '《中共中央 国务院关于建立国土空间规划体系并监督实施的若干意见》（中发〔2019〕18号）、《国土空间规划法（草案）》、《全国国土空间规划纲要（2021—2035年）》',
      groups: [
        {
          g: '规划成果与三条控制线', items: [
            {
              id: 'GH-01', n: '国土空间规划成果一张图', tag: '核心', period: '长期', owner: '国土空间规划局', status: '已建',
              desc: '集成自治区、盟市、旗县、乡镇四级总体规划与专项规划、详细规划成果，形成坐标一致、边界吻合、上下贯通的规划成果"一张图"。',
              basis: '《国土空间规划"一张图"建设指南》',
              flow: ['规划成果汇交', '坐标转换与接边处理', '成果质检与入库', '版本登记与发布', '成果叠加展示', '规划符合性调用'],
              io: { in: ['各级各类规划成果（gdb/shp/数据库）'], out: ['规划成果一张图数据库', '规划成果目录', '规划图件服务'] },
              layers: ['ecoRedline', 'farmlandRedline', 'landUsePatch'],
              mets: [
                { l: '生态保护红线', u: '个', agg: { t: 'count', layer: 'ecoRedline' } },
                { l: '耕地保护红线', u: '个', agg: { t: 'count', layer: 'farmlandRedline' } },
                { l: '红线面积', u: '万km²', agg: { t: 'series', k: 'redline' } }
              ],
              chart: { t: 'barCity', layer: 'ecoRedline', by: 'area_mu', title: '各盟市生态保护红线面积' },
              table: { layer: 'ecoRedline', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['生态保护红线在各盟市的分布情况', '国土空间规划成果覆盖了哪些旗县', '生态保护红线面积变化趋势']
            },
            {
              id: 'GH-02', n: '"三区三线"划定成果管理', tag: '核心', period: '长期', owner: '国土空间规划局', status: '已建',
              desc: '管理生态、农业、城镇三类空间与生态保护红线、永久基本农田、城镇开发边界三条控制线的划定成果，实现上图入库、精准落地、矢量化管控。',
              basis: '《关于在国土空间规划中统筹划定落实三条控制线的指导意见》（厅字〔2019〕48号）',
              flow: ['资源环境承载能力与国土空间开发适宜性评价', '三线初步划定', '矛盾冲突协调', '上下联动校核', '成果论证与报批', '上图入库'],
              io: { in: ['双评价成果', '现状调查数据', '各类保护地范围'], out: ['三条控制线矢量成果', '划定说明与技术报告', '管控规则表'] },
              layers: ['ecoRedline', 'farmlandRedline', 'construction'],
              mets: [
                { l: '生态红线斑块', u: '个', agg: { t: 'count', layer: 'ecoRedline' } },
                { l: '永久基本农田', u: '万亩', agg: { t: 'series', k: 'primeFarmland' } },
                { l: '城镇开发边界', u: '个', agg: { t: 'count', layer: 'construction' } }
              ],
              chart: { t: 'barCity', layer: 'farmlandRedline', by: 'area_mu', title: '各盟市耕地保护红线面积' },
              table: { layer: 'farmlandRedline', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'control'] },
              asks: ['三条控制线的划定规模和分布', '永久基本农田在各盟市的数量', '城镇开发边界覆盖情况']
            },
            {
              id: 'GH-03', n: '三条控制线冲突检测与处置', tag: '核心', period: '持续', owner: '国土空间规划局 / 信息中心', status: '已建',
              desc: '自动检测三条控制线之间、控制线与现状地类/矿权/建设项目之间的空间重叠冲突，生成冲突图斑清单并跟踪处置，保障管控规则刚性执行。',
              basis: '《三条控制线划定技术规程》；《国土空间规划冲突检测规则》',
              flow: ['控制线图层叠加求交', '冲突类型判定（重叠/压占/交叉）', '冲突图斑生成与编号', '冲突等级评定', '处置方案拟定', '处置结果回填与销号'],
              io: { in: ['三条控制线成果', '现状地类数据', '矿业权与建设项目数据'], out: ['冲突图斑清单', '冲突分析报告', '处置台账'] },
              layers: ['ecoRedline', 'farmlandRedline', 'construction', 'primeFarmland'],
              mets: [
                { l: '参与检测图层', u: '个', agg: { t: 'static', v: '4' } },
                { l: '疑似冲突图斑', u: '个', agg: { t: 'count', layer: 'construction' } },
                { l: '已处置', u: '个', agg: { t: 'appr', layer: 'construction', v: '已备案' } }
              ],
              chart: { t: 'appr', layer: 'construction', title: '冲突图斑处置状态' },
              table: { layer: 'construction', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'control'] },
              asks: ['三条控制线存在哪些冲突图斑', '冲突图斑处置进度如何']
            },
            {
              id: 'GH-04', n: '建设项目选址合规性审查', tag: '核心', period: '持续', owner: '用途管制处 / 行政审批处', status: '已建',
              desc: '对拟选址地块自动叠加生态保护红线、永久基本农田、城镇开发边界、自然保护地、矿权等管控要素，一键输出合规性审查意见与限制性清单。',
              basis: '《关于以"多规合一"为基础推进规划用地"多审合一、多证合一"改革的通知》（自然资规〔2019〕2号）',
              flow: ['导入选址范围（绘制/上传）', '多图层叠加分析', '管控规则匹配判定', '生成限制性因素清单', '出具审查意见', '意见归档与复用'],
              io: { in: ['选址范围矢量', '三条控制线与管控图层'], out: ['合规性审查报告', '限制性因素清单', '审查意见书'] },
              layers: ['construction', 'ecoRedline', 'primeFarmland', 'natureReserve'],
              mets: [
                { l: '审查项目', u: '个', agg: { t: 'count', layer: 'construction' } },
                { l: '压占红线项目', u: '个', agg: { t: 'appr', layer: 'construction', v: '待报批' } },
                { l: '自然保护地', u: '个', agg: { t: 'count', layer: 'natureReserve' } }
              ],
              chart: { t: 'pie', layer: 'construction', by: 'type', title: '审查项目类型构成' },
              table: { layer: 'construction', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'control'] },
              asks: ['建设项目选址是否压占生态保护红线', '哪些项目存在限制性因素']
            }
          ]
        },
        {
          g: '实施监督与用途管制', items: [
            {
              id: 'GH-05', n: '规划实施监测网络与年度体检', tag: '核心', period: '年度', owner: '国土空间规划局 / CSPON 专班', status: '在建',
              desc: '依托国土空间规划实施监测网络（CSPON），按年度对规划实施情况开展"体检评估"，形成指标完成情况、偏差预警与改进建议。',
              basis: '《国土空间规划城市体检评估规程》TD/T 1063；《全国国土空间规划实施监测网络建设工作方案》',
              flow: ['指标体系与数据源配置', '指标自动采集计算', '与规划目标值比对', '偏差识别与预警', '成因分析', '体检报告编制', '成果上报与公开'],
              io: { in: ['年度调查监测数据', '规划目标与指标表', '经济社会统计数据'], out: ['年度体检评估报告', '指标完成情况表', '预警清单'] },
              layers: ['landUsePatch', 'construction'],
              mets: [
                { l: '体检指标', u: '项', agg: { t: 'static', v: '122' } },
                { l: '达标率', u: '%', agg: { t: 'static', v: '93.4' } },
                { l: '预警指标', u: '项', agg: { t: 'static', v: '8' } }
              ],
              chart: { t: 'line', s: ['farmland', 'primeFarmland', 'miningRights'], title: '约束性指标年度变化' },
              table: { layer: 'construction', cols: ['name', 'type', 'city', 'county', 'area_mu', 'year', 'approval'] },
              asks: ['国土空间规划年度体检结果如何', '哪些约束性指标未达标', '耕地保有量完成情况']
            },
            {
              id: 'GH-06', n: '建设用地审批与用途管制', tag: '核心', period: '持续', owner: '用途管制处', status: '已建',
              desc: '办理农用地转用、土地征收、成片开发方案审批及规划许可，实现"审—批—供—用—登"全链条业务协同与图数一致性校验。',
              basis: '《土地管理法》；《建设用地审查报批管理办法》；《国土空间用途管制制度》',
              flow: ['项目受理与材料审查', '规划符合性核查', '占补平衡与征地情况核验', '会审与公示', '报批与批复', '供地与规划许可', '批后监管'],
              io: { in: ['项目申报材料', '规划与现状数据', '占补平衡指标库'], out: ['批复文件', '用地红线', '批后监管台账'] },
              layers: ['construction', 'linkLedger'],
              mets: [
                { l: '在办项目', u: '个', agg: { t: 'count', layer: 'construction' } },
                { l: '增减挂钩项目', u: '个', agg: { t: 'count', layer: 'linkLedger' } },
                { l: '已批准备案', u: '个', agg: { t: 'appr', layer: 'construction', v: '已备案' } }
              ],
              chart: { t: 'barCity', layer: 'linkLedger', by: 'area_mu', title: '各盟市增减挂钩项目规模' },
              table: { layer: 'linkLedger', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval'] },
              asks: ['建设用地审批项目有多少在办', '增减挂钩项目规模统计']
            },
            {
              id: 'GH-07', n: '规划约束性指标管控与传导', tag: '常规', period: '年度', owner: '国土空间规划局', status: '已建',
              desc: '对耕地保有量、永久基本农田保护面积、生态保护红线面积、城乡建设用地规模等约束性指标进行层层分解、逐级传导与年度考核。',
              basis: '《国土空间规划纲要指标分解方案》；《耕地保护责任目标考核办法》',
              flow: ['自治区指标分解到盟市', '盟市分解到旗县', '年度执行监测', '指标预警', '调整与占补平衡', '考核与问责'],
              io: { in: ['上级下达指标', '年度现状数据'], out: ['指标分解表', '年度执行监测报告', '考核结果'] },
              layers: ['primeFarmland', 'farmlandRedline', 'construction'],
              mets: [
                { l: '耕地保有量', u: '万亩', agg: { t: 'series', k: 'farmland' } },
                { l: '永久基本农田', u: '万亩', agg: { t: 'series', k: 'primeFarmland' } },
                { l: '生态红线', u: '万km²', agg: { t: 'series', k: 'redline' } }
              ],
              chart: { t: 'line', s: ['farmland', 'primeFarmland'], title: '耕地保护约束性指标五年走势' },
              table: { layer: 'primeFarmland', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['耕地保有量和永久基本农田完成情况', '各盟市约束性指标分解情况']
            },
            {
              id: 'GH-08', n: '详细规划与村庄规划管理', tag: '常规', period: '持续', owner: '国土空间规划局 / 村镇处', status: '已建',
              desc: '管理城镇开发边界内控制性详细规划与边界外"多规合一"实用性村庄规划，保障规划许可有据可依，服务乡村振兴与农牧区建设。',
              basis: '《关于加强村庄规划促进乡村振兴的通知》（自然资办函〔2019〕2275号）',
              flow: ['规划编制委托与现状调研', '村民意见征集与公示', '成果编制与审查', '人民政府审批', '成果入库上图', '规划许可应用'],
              io: { in: ['村庄现状调查数据', '上位规划管控要求'], out: ['村庄规划成果库', '规划图则', '规划许可依据'] },
              layers: ['settle', 'town', 'construction'],
              mets: [
                { l: '居民点', u: '个', agg: { t: 'count', layer: 'settle' } },
                { l: '乡镇驻地', u: '个', agg: { t: 'count', layer: 'town' } },
                { l: '在建项目', u: '个', agg: { t: 'count', layer: 'construction' } }
              ],
              chart: { t: 'pie', layer: 'settle', by: 'type', title: '居民点类型构成' },
              table: { layer: 'settle', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval'] },
              asks: ['村庄规划覆盖情况如何', '按盟市统计居民点分布']
            },
            {
              id: 'GH-09', n: '规划修改调整与版本管理', tag: '常规', period: '持续', owner: '国土空间规划局', status: '已建',
              desc: '对确需修改的规划成果按法定程序开展评估论证、公示报批，实现修改前后版本对照、历史可追溯、成果可回滚。',
              basis: '《国土空间规划修改调整规则》',
              flow: ['修改必要性评估', '方案编制与论证', '公示与听证', '报原审批机关批准', '成果更新入库', '版本归档与对照'],
              io: { in: ['修改申请与论证材料'], out: ['修改方案', '批复文件', '版本对照成果'] },
              layers: ['landUsePatch', 'ecoRedline'],
              mets: [
                { l: '在库版本', u: '个', agg: { t: 'static', v: '36' } },
                { l: '当年修改', u: '次', agg: { t: 'static', v: '7' } },
                { l: '涉及图斑', u: '个', agg: { t: 'count', layer: 'landUsePatch' } }
              ],
              chart: { t: 'appr', layer: 'landUsePatch', title: '修改涉及图斑状态' },
              table: { layer: 'ecoRedline', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'updateTime'] },
              asks: ['本年度规划修改了多少次', '修改涉及哪些盟市']
            },
            {
              id: 'GH-10', n: '规划实施监督指标看板', tag: '常规', period: '实时', owner: '信息中心', status: '已建',
              desc: '面向领导决策与业务处室，提供规划实施核心指标的可视化看板，支持下钻到盟市、旗县与具体图斑，实现"用数据说话、用数据决策"。',
              basis: '《自然资源信息化总体建设方案》',
              flow: ['指标口径配置', '数据自动抽取', '可视化建模', '看板发布', '权限分发', '定期更新'],
              io: { in: ['各业务数据库'], out: ['指标看板', '专题图表', '导出报告'] },
              layers: ['landUsePatch', 'ecoRedline', 'construction'],
              mets: [
                { l: '接入指标', u: '项', agg: { t: 'static', v: '12' } },
                { l: '覆盖盟市', u: '个', agg: { t: 'static', v: '12' } },
                { l: '更新频率', u: '—', agg: { t: 'static', v: '日' } }
              ],
              chart: { t: 'line', s: ['redline', 'wetlandRate', 'farmlandGrade'], title: '核心监督指标走势' },
              table: { layer: 'landUsePatch', cols: ['name', 'type', 'city', 'county', 'area_mu', 'year'] },
              asks: ['展示国土空间规划实施监督核心指标', '各盟市规划实施情况对比']
            }
          ]
        }
      ]
    },

    /* ============================================================
       三、生态修复（XF）
       ============================================================ */
    {
      key: 'xf', code: 'XF', name: '国土空间生态修复', en: 'Ecological Restoration', color: '#3f8e4f',
      goal: '统筹山水林田湖草沙一体化保护和系统修复，构建"规划—项目—实施—监测—评估—管护"全生命周期闭环，支撑"北方重要生态安全屏障"建设。',
      basis: '《全国重要生态系统保护和修复重大工程总体规划（2021—2035年）》、《山水林田湖草生态保护修复工程指南》、《三北工程六期规划》、《内蒙古自治区国土空间生态修复规划》',
      groups: [
        {
          g: '重大工程与专项治理', items: [
            {
              id: 'XF-01', n: '山水林田湖草沙一体化保护修复', tag: '核心', period: '长期', owner: '国土空间生态修复处', status: '已建',
              desc: '以流域与地貌单元为整体，统筹山上山下、地上地下、岸上岸下、上游下游，实施一体化保护修复，破解"山水林田湖草沙"分割治理难题。',
              basis: '《山水林田湖草生态保护修复工程指南》（自然资办函〔2020〕1216号）',
              flow: ['本底调查与问题识别', '保护修复单元划定', '工程总体方案编制', '项目库入库与立项', '年度任务分解', '工程实施与监理', '绩效评估与验收'],
              io: { in: ['生态本底调查成果', '生态问题诊断报告'], out: ['一体化保护修复方案', '工程项目库', '绩效评估报告'] },
              layers: ['ecoRestoreZone', 'mineRestore'],
              mets: [
                { l: '修复治理区', u: '个', agg: { t: 'count', layer: 'ecoRestoreZone' } },
                { l: '治理面积', u: '万亩', agg: { t: 'sum', layer: 'ecoRestoreZone', f: 'area_mu', div: 10000 } },
                { l: '矿山修复区', u: '个', agg: { t: 'count', layer: 'mineRestore' } }
              ],
              chart: { t: 'barCity', layer: 'ecoRestoreZone', by: 'area_mu', title: '各盟市修复治理区面积' },
              table: { layer: 'ecoRestoreZone', cols: ['name', 'type', 'city', 'county', 'area_mu', 'target', 'owner', 'approval'] },
              asks: ['山水林田湖草沙一体化修复工程有多少个项目', '各盟市修复治理面积对比', '修复治理区的目标与责任主体']
            },
            {
              id: 'XF-02', n: '三北工程与防沙治沙攻坚战', tag: '核心', period: '长期', owner: '林草局 / 生态修复处', status: '已建',
              desc: '推进三北工程六期建设，打好黄河"几字弯"攻坚战、科尔沁和浑善达克沙地歼灭战、河西走廊—塔克拉玛干边缘阻击战三大标志性战役。',
              basis: '《三北工程六期规划》；《关于加强荒漠化综合防治和推进"三北"等重点生态工程建设的意见》',
              flow: ['沙化土地本底调查', '治理任务分解到旗县', '作业设计与招投标', '工程实施（工程固沙/造林种草）', '进度月报与遥感核查', '成效监测与验收'],
              io: { in: ['沙化土地监测成果', '年度治理任务'], out: ['治理任务台账', '进度统计图', '成效监测报告'] },
              layers: ['ecoRestoreZone', 'desert'],
              mets: [
                { l: '攻坚战片区', u: '个', agg: { t: 'count', layer: 'ecoRestoreZone' } },
                { l: '沙化土地斑块', u: '个', agg: { t: 'count', layer: 'desert' } },
                { l: '沙化面积', u: '万亩', agg: { t: 'sum', layer: 'desert', f: 'area_mu', div: 10000 } }
              ],
              chart: { t: 'barCity', layer: 'desert', by: 'area_mu', title: '各盟市沙化土地分布' },
              table: { layer: 'desert', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['三北工程三大标志性战役覆盖哪些区域', '沙化土地在各盟市的分布', '防沙治沙治理任务完成情况']
            },
            {
              id: 'XF-03', n: '历史遗留矿山生态修复', tag: '核心', period: '年度', owner: '生态修复处 / 地勘处', status: '已建',
              desc: '对责任人灭失的历史遗留矿山开展地形地貌重塑、植被重建、土地复垦与污染治理，消除地质环境隐患，恢复矿区生态功能与土地利用价值。',
              basis: '《矿山生态修复技术规范》；《关于探索利用市场化方式推进矿山生态修复的意见》（自然资规〔2019〕6号）',
              flow: ['矿山摸底调查与建档', '修复单元划分', '方案编制与审查', '组织实施（削坡/覆土/复绿）', '过程监测', '验收与移交', '后期管护'],
              io: { in: ['矿山调查成果', '遥感影像与地形数据'], out: ['矿山修复档案', '修复治理工程成果', '验收报告'] },
              layers: ['mineRestore', 'mineralBlock'],
              mets: [
                { l: '修复区', u: '个', agg: { t: 'count', layer: 'mineRestore' } },
                { l: '修复面积', u: '万亩', agg: { t: 'sum', layer: 'mineRestore', f: 'area_mu', div: 10000 } },
                { l: '矿产区块', u: '个', agg: { t: 'count', layer: 'mineralBlock' } }
              ],
              chart: { t: 'pie', layer: 'mineRestore', by: 'type', title: '矿山修复类型构成' },
              table: { layer: 'mineRestore', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval'] },
              asks: ['历史遗留矿山修复项目有多少', '矿山修复面积按盟市统计', '修复区责任主体是谁']
            },
            {
              id: 'XF-04', n: '生产矿山"边采边治"与绿色矿山', tag: '常规', period: '年度', owner: '矿业权管理处 / 地勘处', status: '已建',
              desc: '落实矿山企业"边开采、边治理、边恢复"主体责任，推进绿色矿山建设与遴选，对矿山地质环境保护与土地复垦方案执行情况进行监管。',
              basis: '《绿色矿山评价指标》；《矿山地质环境保护规定》；《土地复垦条例》',
              flow: ['方案编报与审查', '基金计提与专户管理', '年度治理任务下达', '分期治理实施', '遥感与现场核查', '绿色矿山评估遴选', '公示与公告'],
              io: { in: ['开发利用方案', '地质环境治理与复垦方案'], out: ['年度治理任务台账', '绿色矿山名录', '监管核查记录'] },
              layers: ['miningRight', 'mineRestore', 'mineralBlock'],
              mets: [
                { l: '采矿权', u: '个', agg: { t: 'series', k: 'miningRights' } },
                { l: '在册矿权', u: '个', agg: { t: 'count', layer: 'miningRight' } },
                { l: '审批中', u: '个', agg: { t: 'appr', layer: 'miningRight', v: '审批中' } }
              ],
              chart: { t: 'pie', layer: 'miningRight', by: 'scale', title: '矿山规模构成' },
              table: { layer: 'miningRight', cols: ['name', 'type', 'city', 'county', 'scale', 'rightType', 'validUntil', 'approval'] },
              asks: ['全区采矿权数量与矿种构成', '哪些采矿权即将到期', '绿色矿山建设情况']
            },
            {
              id: 'XF-05', n: '全域土地综合整治与增减挂钩', tag: '常规', period: '年度', owner: '耕地保护监督处 / 土地整理中心', status: '已建',
              desc: '以乡镇或村为基本实施单元，统筹农用地整理、建设用地整理和乡村生态保护修复，优化"三生"空间，通过增减挂钩指标流转反哺乡村。',
              basis: '《关于开展全域土地综合整治试点工作的通知》（自然资发〔2019〕194号）；《城乡建设用地增减挂钩管理办法》',
              flow: ['潜力调查与单元划定', '整治方案编制', '项目立项与批复', '工程实施', '指标核定与交易', '验收与后期管护'],
              io: { in: ['土地利用现状与村庄数据', '整治潜力评价成果'], out: ['整治项目库', '增减挂钩指标台账', '验收成果'] },
              layers: ['linkLedger', 'settle', 'town'],
              mets: [
                { l: '挂钩项目', u: '个', agg: { t: 'count', layer: 'linkLedger' } },
                { l: '项目规模', u: '万亩', agg: { t: 'sum', layer: 'linkLedger', f: 'area_mu', div: 10000 } },
                { l: '涉及居民点', u: '个', agg: { t: 'count', layer: 'settle' } }
              ],
              chart: { t: 'barCity', layer: 'linkLedger', by: 'area_mu', title: '各盟市整治项目规模' },
              table: { layer: 'linkLedger', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval'] },
              asks: ['全域土地综合整治项目有多少', '增减挂钩指标规模统计']
            },
            {
              id: 'XF-06', n: '耕地占补平衡与提质改造', tag: '核心', period: '年度', owner: '耕地保护监督处', status: '已建',
              desc: '落实"占一补一、占优补优、占水田补水田"，对建设占用耕地实行指标核销与补充耕地项目挂钩，推进耕地提质改造与产能提升。',
              basis: '《耕地保护法（草案）》；《关于改进耕地占补平衡管理的通知》',
              flow: ['占用耕地核定', '补充耕地项目匹配', '指标核销与台账登记', '新增耕地核定与入库', '提质改造实施', '后期种植管护与核查'],
              io: { in: ['建设用地审批数据', '补充耕地项目库'], out: ['占补平衡台账', '新增耕地核定成果', '指标使用情况表'] },
              layers: ['farmlandQuality', 'landUsePatch', 'unused'],
              mets: [
                { l: '质量监测样点', u: '个', agg: { t: 'count', layer: 'farmlandQuality' } },
                { l: '宜耕后备资源', u: '个', agg: { t: 'count', layer: 'unused' } },
                { l: '耕地保有量', u: '万亩', agg: { t: 'series', k: 'farmland' } }
              ],
              chart: { t: 'barCity', layer: 'unused', by: 'area_mu', title: '各盟市宜耕后备资源' },
              table: { layer: 'farmlandQuality', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'updateTime'] },
              asks: ['耕地占补平衡指标使用情况', '宜耕后备资源分布如何', '耕地质量提升情况']
            },
            {
              id: 'XF-07', n: '湿地保护修复与退化湿地治理', tag: '常规', period: '年度', owner: '林草局 / 湿地管理处', status: '已建',
              desc: '对重要湿地实施保护与退化湿地修复，开展湿地生态补水、植被恢复、外来入侵物种防控，提升湿地保护率与生态功能。',
              basis: '《湿地保护法》；《全国湿地保护规划（2022—2030年）》',
              flow: ['湿地资源调查与名录管理', '退化湿地诊断', '修复方案编制', '生态补水与植被恢复', '监测评估', '保护小区与管护'],
              io: { in: ['湿地调查监测数据', '水文与水质数据'], out: ['湿地修复工程成果', '湿地保护率统计', '监测评估报告'] },
              layers: ['wetland', 'natureReserve'],
              mets: [
                { l: '湿地斑块', u: '个', agg: { t: 'count', layer: 'wetland' } },
                { l: '湿地面积', u: '万亩', agg: { t: 'series', k: 'wetland' } },
                { l: '湿地保护率', u: '%', agg: { t: 'series', k: 'wetlandRate' } }
              ],
              chart: { t: 'barCity', layer: 'wetland', by: 'area_mu', title: '各盟市湿地面积' },
              table: { layer: 'wetland', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['湿地面积与保护率是多少', '各盟市湿地分布对比', '退化湿地修复项目情况']
            }
          ]
        },
        {
          g: '项目管理与成效评估', items: [
            {
              id: 'XF-08', n: '生态修复项目全生命周期管理', tag: '核心', period: '持续', owner: '生态修复处 / 项目办', status: '在建',
              desc: '对修复项目实行"储备—立项—设计—实施—监理—验收—移交—管护"全流程台账管理与节点预警，实现项目进度、资金、质量、档案一体化管控。',
              basis: '《中央生态环保资金项目管理办法》；《国土空间生态修复项目管理规程》',
              flow: ['项目储备入库', '立项批复', '设计与预算评审', '招投标与施工', '监理与进度款支付', '竣工验收', '资产移交与后期管护'],
              io: { in: ['项目申报材料', '设计与预算文件'], out: ['项目台账', '进度与资金报表', '验收档案'] },
              layers: ['ecoRestoreZone', 'mineRestore', 'linkLedger'],
              mets: [
                { l: '在库项目', u: '个', agg: { t: 'count', layer: 'ecoRestoreZone' } },
                { l: '已立项', u: '个', agg: { t: 'appr', layer: 'ecoRestoreZone', v: '已备案' } },
                { l: '待报批', u: '个', agg: { t: 'appr', layer: 'ecoRestoreZone', v: '待报批' } }
              ],
              chart: { t: 'appr', layer: 'ecoRestoreZone', title: '项目审批状态分布' },
              table: { layer: 'ecoRestoreZone', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval', 'updateTime'] },
              asks: ['生态修复项目审批进度如何', '哪些项目尚未完成立项', '项目责任主体与时间节点']
            },
            {
              id: 'XF-09', n: '生态修复成效监测评估', tag: '常规', period: '年度', owner: '生态修复处 / 监测院', status: '已建',
              desc: '基于修复前后多时相影像与地面样方，评估植被盖度、生物量、水土保持、碳汇增量等修复成效，形成可量化、可对比的成效评估报告。',
              basis: '《生态保护修复成效评估技术指南（试行）》TD/T 1070',
              flow: ['评估指标与基线确定', '修复前后影像对比', '植被盖度与生物量反演', '样方实测验证', '综合评分', '成效分级与报告'],
              io: { in: ['多时相遥感影像', '样方调查数据'], out: ['成效评估报告', '修复前后对比图', '碳汇增量核算'] },
              layers: ['forest', 'grassland', 'desert'],
              mets: [
                { l: '林地斑块', u: '个', agg: { t: 'count', layer: 'forest' } },
                { l: '草原斑块', u: '个', agg: { t: 'count', layer: 'grassland' } },
                { l: '植被盖度', u: '%', agg: { t: 'series', k: 'grassCover' } }
              ],
              chart: { t: 'line', s: ['forestCover', 'grassCover'], title: '修复成效核心指标变化' },
              table: { layer: 'grassland', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['生态修复成效如何评估', '修复前后植被盖度变化', '各盟市林草资源恢复情况']
            },
            {
              id: 'XF-10', n: '生态产品价值实现与保护补偿', tag: '新建', period: '年度', owner: '所有者权益处 / 生态修复处', status: '规划',
              desc: '开展生态产品总值（GEP）核算与林草碳汇计量，探索生态保护补偿、碳汇交易与生态产业化经营，推动"绿水青山"向"金山银山"转化。',
              basis: '《关于建立健全生态产品价值实现机制的意见》；《生态保护补偿条例》',
              flow: ['生态产品目录编制', 'GEP 核算体系构建', '实物量与价值量核算', '碳汇计量与核证', '补偿标准测算', '交易与兑现机制设计'],
              io: { in: ['调查监测成果', '碳汇计量参数', '市场价格数据'], out: ['GEP 核算报告', '碳汇计量成果', '补偿方案'] },
              layers: ['forest', 'grassland', 'wetland'],
              mets: [
                { l: '森林覆盖率', u: '%', agg: { t: 'series', k: 'forestCover' } },
                { l: '草原盖度', u: '%', agg: { t: 'series', k: 'grassCover' } },
                { l: '湿地保护率', u: '%', agg: { t: 'series', k: 'wetlandRate' } }
              ],
              chart: { t: 'line', s: ['forestCover', 'grassCover', 'wetlandRate'], title: '生态资产核心指标走势' },
              table: { layer: 'wetland', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner'] },
              asks: ['全区生态产品价值核算结果', '林草碳汇潜力分析', '生态保护补偿覆盖情况']
            }
          ]
        }
      ]
    },

    /* ============================================================
       四、执法督察（ZF）
       ============================================================ */
    {
      key: 'zf', code: 'ZF', name: '执法督察', en: 'Law Enforcement & Supervision', color: '#b0432c',
      goal: '构建"早发现、早制止、严查处"的执法督察闭环，实现卫片执法、例行督察、专项督察、日常巡查一体化，违法行为发现在初始、解决在萌芽。',
      basis: '《土地管理法》《矿产资源法》《测绘法》；《自然资源执法监督规定》；《土地卫片执法检查工作规范》；《国家自然资源督察工作规则》',
      groups: [
        {
          g: '卫片执法与案件查处', items: [
            {
              id: 'ZF-01', n: '卫片执法图斑核查', tag: '核心', period: '季度', owner: '执法局 / 自然资源督察办', status: '已建',
              desc: '按季度接收国家下发卫片执法图斑，开展内业比对、外业核查、合法性判定与整改处置，形成"图斑—判定—查处—整改"闭环。',
              basis: '《土地卫片执法检查工作规范》；《关于完善早发现早制止严查处工作机制的意见》（自然资发〔2023〕41号）',
              flow: ['卫片图斑接收与分发', '内业叠合比对', '外业实地核查取证', '合法性判定（合法/违法/其他）', '立案查处或督促整改', '整改复垦复绿', '销号与归档'],
              io: { in: ['季度卫片影像与图斑', '用地审批与供地数据'], out: ['核查结果表', '违法图斑清单', '整改销号台账'] },
              layers: ['landUsePatch', 'construction'],
              mets: [
                { l: '卫片图斑', u: '个', agg: { t: 'poiCount', poi: 'ENFORCE' } },
                { l: '已整改', u: '个', agg: { t: 'poiAppr', poi: 'ENFORCE', v: '已整改' } },
                { l: '整改中', u: '个', agg: { t: 'poiAppr', poi: 'ENFORCE', v: '整改中' } }
              ],
              chart: { t: 'poiPie', poi: 'ENFORCE', by: 'status', title: '卫片图斑处置状态' },
              table: { poi: 'ENFORCE', cols: ['n', 'city', 'type', 'area', 'period', 'status', 'diffDays'] },
              asks: ['本季度卫片执法图斑有多少', '卫片图斑处置状态分布', '哪些盟市违法图斑最多']
            },
            {
              id: 'ZF-02', n: '违法用地案件查处与过程留痕', tag: '核心', period: '持续', owner: '执法局', status: '已建',
              desc: '对违法用地行为依法立案调查、作出行政处罚决定并监督执行，实现案件全流程电子化、文书标准化、过程可追溯。',
              basis: '《自然资源行政处罚办法》；《自然资源执法监督规定》',
              flow: ['线索登记与初查', '立案审批', '调查取证（勘测/询问/拍照）', '案件审理与法制审核', '告知与听证', '作出处罚决定', '执行与结案', '移送与公开'],
              io: { in: ['违法线索与证据材料'], out: ['行政处罚决定书', '案件卷宗', '执行与结案记录'] },
              layers: ['construction', 'landUsePatch'],
              mets: [
                { l: '在建项目', u: '个', agg: { t: 'count', layer: 'construction' } },
                { l: '疑似违法', u: '个', agg: { t: 'appr', layer: 'construction', v: '待报批' } },
                { l: '结案率', u: '%', agg: { t: 'static', v: '92.6' } }
              ],
              chart: { t: 'pie', layer: 'construction', by: 'type', title: '疑似违法用地类型构成' },
              table: { layer: 'construction', cols: ['name', 'type', 'city', 'county', 'area_mu', 'approval', 'control'] },
              asks: ['违法用地案件查处情况', '哪些项目涉嫌未批先建', '案件结案率统计']
            },
            {
              id: 'ZF-03', n: '农村乱占耕地建房专项整治', tag: '核心', period: '持续', owner: '执法局 / 耕地保护监督处', status: '已建',
              desc: '对农村乱占耕地建房（含住宅类、公共管理服务类、产业类）进行摸排与分类处置，坚决遏制耕地"非农化"、防止"非粮化"。',
              basis: '《关于农村乱占耕地建房问题摸排工作方案》；《关于坚决制止耕地"非农化"行为的通知》',
              flow: ['疑似图斑提取与下发', '村级摸排与登记', '分类认定（住宅/公共服务/产业）', '处置意见拟定', '整改拆除或补办手续', '销号与复核'],
              io: { in: ['卫片与变更调查图斑', '村庄地籍与户籍数据'], out: ['摸排台账', '分类处置清单', '整改销号记录'] },
              layers: ['settle', 'primeFarmland', 'town'],
              mets: [
                { l: '涉及居民点', u: '个', agg: { t: 'count', layer: 'settle' } },
                { l: '永久基本农田', u: '个', agg: { t: 'count', layer: 'primeFarmland' } },
                { l: '乡镇单元', u: '个', agg: { t: 'count', layer: 'town' } }
              ],
              chart: { t: 'barCity', layer: 'settle', by: 'area_mu', title: '各盟市涉及居民点规模' },
              table: { layer: 'settle', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'approval'] },
              asks: ['农村乱占耕地建房摸排情况', '哪些居民点位于永久基本农田范围内']
            },
            {
              id: 'ZF-04', n: '矿产执法监察与越界开采监测', tag: '核心', period: '季度', owner: '执法局 / 矿业权管理处', status: '已建',
              desc: '对无证开采、越界开采、破坏性开采等违法行为开展监测与查处，通过矿权范围与采掘工程实测比对自动识别越界行为。',
              basis: '《矿产资源法》；《矿业权人勘查开采信息公示办法》',
              flow: ['矿权范围与影像比对', '疑似越界图斑提取', '实地测量核查', '立案调查', '处罚与没收违法所得', '生态修复责任落实', '公示与信用惩戒'],
              io: { in: ['采矿权范围数据', '采掘工程实测与影像'], out: ['越界开采核查报告', '处罚决定', '修复责任书'] },
              layers: ['miningRight', 'exploreRight', 'mineralBlock'],
              mets: [
                { l: '采矿权', u: '个', agg: { t: 'count', layer: 'miningRight' } },
                { l: '探矿权', u: '个', agg: { t: 'count', layer: 'exploreRight' } },
                { l: '审批中', u: '个', agg: { t: 'appr', layer: 'miningRight', v: '审批中' } }
              ],
              chart: { t: 'barCity', layer: 'miningRight', by: 'area_mu', title: '各盟市采矿权规模' },
              table: { layer: 'miningRight', cols: ['name', 'type', 'city', 'county', 'scale', 'rightType', 'validUntil', 'approval'] },
              asks: ['采矿权与探矿权数量统计', '哪些矿业权涉嫌越界开采', '矿业权到期预警']
            },
            {
              id: 'ZF-05', n: '林草湿执法监管', tag: '常规', period: '季度', owner: '林草局执法处 / 林长办', status: '已建',
              desc: '查处违法毁林毁草、擅自占用林地草地湿地、违规放牧等行为，结合林长制网格落实属地监管责任。',
              basis: '《森林法》《草原法》《湿地保护法》；《林长制督查考核办法》',
              flow: ['线索受理与核查', '现场勘验与损毁鉴定', '立案与处罚', '植被恢复监督', '林长制考核挂钩', '销号与公示'],
              io: { in: ['林草湿调查监测成果', '卫片与巡查线索'], out: ['处罚决定', '植被恢复方案', '考核结果'] },
              layers: ['forest', 'grassland', 'wetland'],
              mets: [
                { l: '林地斑块', u: '个', agg: { t: 'count', layer: 'forest' } },
                { l: '草原斑块', u: '个', agg: { t: 'count', layer: 'grassland' } },
                { l: '湿地斑块', u: '个', agg: { t: 'count', layer: 'wetland' } }
              ],
              chart: { t: 'pie', layer: 'grassland', by: 'type', title: '草原类型构成' },
              table: { layer: 'forest', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['林草湿违法案件查处情况', '违法占用林草资源分布']
            }
          ]
        },
        {
          g: '督察整改与综合监管', items: [
            {
              id: 'ZF-06', n: '国家自然资源督察（例行/专项/审核）', tag: '核心', period: '年度', owner: '自然资源督察办', status: '已建',
              desc: '配合国家自然资源督察机构开展例行督察、专项督察与日常督察，对耕地保护、生态红线、能源资源保障等重大事项实施监督。',
              basis: '《国家自然资源督察工作规则》；《自然资源督察发现问题整改办法》',
              flow: ['督察准备与资料提供', '督察组驻点核查', '问题清单反馈', '整改方案编制', '整改实施与调度', '整改结果报送', '审核销号'],
              io: { in: ['督察要求与资料清单', '各类管理数据'], out: ['整改方案', '整改情况报告', '销号证明材料'] },
              layers: ['ecoRedline', 'primeFarmland', 'miningRight'],
              mets: [
                { l: '督察事项', u: '项', agg: { t: 'static', v: '18' } },
                { l: '涉及红线', u: '个', agg: { t: 'count', layer: 'ecoRedline' } },
                { l: '涉及矿权', u: '个', agg: { t: 'count', layer: 'miningRight' } }
              ],
              chart: { t: 'barCity', layer: 'ecoRedline', by: 'area_mu', title: '各盟市督察关注区域分布' },
              table: { layer: 'primeFarmland', cols: ['name', 'type', 'city', 'county', 'area_mu', 'owner', 'control'] },
              asks: ['国家自然资源督察发现哪些问题', '督察涉及的重点区域分布', '耕地保护督察整改情况']
            },
            {
              id: 'ZF-07', n: '督察反馈问题整改销号台账', tag: '核心', period: '持续', owner: '自然资源督察办 / 执法局', status: '已建',
              desc: '对督察反馈问题、审计指出问题、巡视移交问题建立统一台账，明确责任单位、整改措施、完成时限与销号标准，实行挂账销号管理。',
              basis: '《自然资源督察发现问题整改销号办法》',
              flow: ['问题登记与编号', '责任单位与措施明确', '整改时限设定', '进度月调度', '整改材料审核', '现场复核', '销号确认与归档'],
              io: { in: ['督察意见书', '整改方案与证明材料'], out: ['整改台账', '进度报表', '销号确认单'] },
              layers: ['landUsePatch', 'construction'],
              mets: [
                { l: '台账问题', u: '项', agg: { t: 'static', v: '86' } },
                { l: '已销号', u: '项', agg: { t: 'static', v: '71' } },
                { l: '销号率', u: '%', agg: { t: 'static', v: '82.6' } }
              ],
              chart: { t: 'poiPie', poi: 'ENFORCE', by: 'status', title: '整改任务状态分布' },
              table: { poi: 'ENFORCE', cols: ['n', 'city', 'type', 'area', 'status', 'diffDays'] },
              asks: ['督察问题整改销号率是多少', '还有多少问题未销号', '超期未整改的问题有哪些']
            },
            {
              id: 'ZF-08', n: '动态巡查与网格化监管', tag: '常规', period: '实时', owner: '执法局 / 基层所', status: '已建',
              desc: '划分执法监管网格，落实"田长制""林长制"网格责任人，通过移动端开展日常巡查、线索上报与轨迹管理，实现违法行为的早发现。',
              basis: '《关于推行田长制的意见》；《自然资源执法巡查工作规范》',
              flow: ['网格划分与责任人配置', '巡查计划制定', '移动端巡查打卡', '线索拍照上报', '线索分办处置', '巡查统计与考核'],
              io: { in: ['网格与责任人台账', '巡查轨迹数据'], out: ['巡查记录', '线索清单', '考核统计'] },
              layers: ['town', 'settle', 'road'],
              mets: [
                { l: '网格单元', u: '个', agg: { t: 'count', layer: 'town' } },
                { l: '居民点', u: '个', agg: { t: 'count', layer: 'settle' } },
                { l: '交通干线', u: '条', agg: { t: 'count', layer: 'road' } }
              ],
              chart: { t: 'barCity', layer: 'town', by: 'count', title: '各盟市监管网格单元数' },
              table: { layer: 'town', cols: ['name', 'type', 'city', 'county', 'owner', 'updateTime'] },
              asks: ['执法监管网格划分情况', '各盟市巡查网格数量对比']
            },
            {
              id: 'ZF-09', n: '执法统计分析与通报', tag: '常规', period: '月度', owner: '执法局综合处', status: '已建',
              desc: '按盟市、类型、时限维度统计立案率、结案率、整改率与追责情况，生成月度与年度执法通报，支撑形势研判与考核问责。',
              basis: '《自然资源执法统计制度》；《执法通报与约谈办法》',
              flow: ['数据来源口径统一', '指标自动汇总', '同比环比分析', '异常预警', '通报稿生成', '发布与约谈'],
              io: { in: ['案件与整改台账'], out: ['执法统计报表', '月度通报', '考核排名'] },
              layers: ['construction', 'landUsePatch'],
              mets: [
                { l: '立案率', u: '%', agg: { t: 'static', v: '100.0' } },
                { l: '结案率', u: '%', agg: { t: 'static', v: '92.6' } },
                { l: '整改率', u: '%', agg: { t: 'static', v: '88.3' } }
              ],
              chart: { t: 'poiPie', poi: 'ENFORCE', by: 'type', title: '违法行为类型构成' },
              table: { poi: 'ENFORCE', cols: ['n', 'city', 'type', 'area', 'period', 'status'] },
              asks: ['执法立案率、结案率、整改率统计', '违法行为类型构成分析', '各盟市执法成效排名']
            },
            {
              id: 'ZF-10', n: '信访举报与违法线索管理', tag: '常规', period: '实时', owner: '执法局信访办', status: '已建',
              desc: '统一受理 12345、12336、网上信访、群众来访等渠道的举报线索，进行登记、分办、核查、反馈与归档，做到件件有落实、事事有回音。',
              basis: '《信访工作条例》；《自然资源违法线索举报办理办法》',
              flow: ['多渠道线索汇聚', '线索登记与去重', '分级分办', '属地核查', '结果反馈', '满意度回访', '归档与分析'],
              io: { in: ['各渠道举报信息'], out: ['线索台账', '核查反馈单', '线索分析报告'] },
              layers: ['changeSurvey', 'construction'],
              mets: [
                { l: '线索总量', u: '条', agg: { t: 'static', v: '1268' } },
                { l: '已办结', u: '条', agg: { t: 'static', v: '1187' } },
                { l: '办结率', u: '%', agg: { t: 'static', v: '93.6' } }
              ],
              chart: { t: 'poiPie', poi: 'ENFORCE', by: 'city', title: '线索属地分布（示意口径）' },
              table: { poi: 'ENFORCE', cols: ['n', 'city', 'type', 'area', 'period', 'status', 'diffDays'] },
              asks: ['信访举报线索办理情况', '线索办结率与超期情况', '举报高发的违法行为类型']
            }
          ]
        }
      ]
    }
  ];

  window.NMG_MODULES = MODULES;
})();
