# 一张图 · 内蒙古：地图业务工作台（2026-09-17）

默认首页为公众门户，提供首页、数据服务、能力服务、办事服务、资讯下载与大美内蒙古等栏目。GIS 工作台独立访问，支持常驻地图、图层目录、对象属性、空间工具与任务办理；后台“一张图成果”入口在新标签页打开 GIS 工作台。地图工作台、专题介绍页与可视化需求说明位于本仓库 `prototype/gis/`。

- 公众门户（默认首页）：启动服务后打开 `http://127.0.0.1:5190/`。
- 地图工作台：`http://127.0.0.1:5190/gis/index.html`。
- 后台管理：`http://127.0.0.1:5190/#/admin/overview`。
- 专题介绍页：`http://127.0.0.1:5190/gis/portal.html`。
- 可视化需求与交互原型：`http://127.0.0.1:5190/gis/requirements.html`。
- [完整需求说明书](prototype/gis/docs/需求说明书与原型交互设计.md)、[功能追踪表](prototype/gis/docs/功能覆盖追踪表.md)、[验收记录](prototype/gis/docs/验收记录.md)。

```sh
prototype/.venv/bin/python prototype/server.py --host 127.0.0.1 --port 5190
node --test prototype/gis/test/spatial.test.cjs
```

新版静态页面也可直接打开 `prototype/gis/index.html`，或从仓库根 `index.html` 进入。地图依赖、DEM 与参考数据均在本地，无需地图密钥和运行时 CDN。完整后台仍需上述服务。新环境先按下文安装原项目依赖。

原 `/#/front/...`、`/#/admin/...` 路由保持兼容，可从新版右上角身份说明中的“完整业务模块”访问。

**数据与实现边界**：新版使用 28 个图层和 1,176 个模拟对象，资源申请/核查/归集为浏览器本地交互流程；尚未与原 SQLite 业务状态同步。助手为规则检索；空间分析采用近似计算，不代表正式测绘或合规结论。五大场景提供地图主线，专业审批及生产接口见需求文档中的待实现范围。

---

# 一张图成果第二轮补充（2026-09-16）

补充图库跨场景组合、多地块追加编辑、资源规模卡片与活动口径人数统计，优化手机端筛选布局。详见 [第二轮补充说明](docs/一张图成果第二轮补充说明.md)。

---

# 一张图成果补充（2026-09-16）

已补充四维图层目录、地图收藏、内嵌批量核查、工具分类、八主题场景和分域监测。入口：http://127.0.0.1:5190/#/admin/integration-results 。实现范围与尚待接入的三维、时序及正式专题见 [补充实现说明](docs/一张图成果补充实现说明.md)。

---

# 综合集成三域重构（2026-09-16）

现已统一为一张图成果、数字资源、个人工作台和管理员集成配置。入口：http://127.0.0.1:5190/#/admin/integration-workbench 。已修正发布态展示与本人待办边界，保留原管理流程及历史数据。详见 [三域重构实现说明](docs/综合集成三域重构实现说明.md)。

---

# 综合集成后台管理流程（2026-09-16）

新增分组导航、可下钻运行总览、成果查看/分析授权、待办版本同步与失败重试、人工核对和接入计划。入口：http://127.0.0.1:5190/#/admin/center-integration?tab=overview 。实现范围与验证见 [后台管理流程实现说明](docs/综合集成后台管理流程实现说明.md)。

---

# 综合集成深化（2026-09-16）

依据正文与附表合并分析，新增综合门户、成果地图工作区、个人工作台及对应后台发布、监测、交换和租户工作空间。入口：http://127.0.0.1:5190/#/front/integrated-portal 。功能与40项剩余范围见 [综合集成深化实现说明](docs/综合集成深化实现说明.md)。

---

# 四中心功能完善（2026-09-16）

综合集成、资源中心、工具中心、运营中心已补充可操作工作区，覆盖待办导入、授权交付、工具审核和数据治理闭环。入口：http://127.0.0.1:5190/#/admin/center-integration 。详见 [四中心功能完善说明](docs/四中心功能完善说明.md)。

---

# 对外门户更新

已按六大公共服务栏目完成首轮优化。访问 http://127.0.0.1:5190/ ，门户运营后台为 http://127.0.0.1:5190/#/admin/public-portal 。

新增综合搜索、数据详情与地图预览、授权示例数据下载、基础空间工具、公众咨询回复和五个特色专题。具体功能、验证结果和待接入范围见 [对外门户优化实施说明](docs/对外门户优化实施说明.md)。

---

# 当前原型：自然资源智能中心

已实现独立的前台业务工作台和后台管理平台，代码位于 [prototype](prototype/README.md)。

```sh
python3 prototype/server.py --port 5190
```

- 前台：http://127.0.0.1:5190/
- 后台：http://127.0.0.1:5190/#/admin/overview

前后台共用本地 SQLite 数据，覆盖检索助手、资源申请与五类 AI 配套工具。详细体验流程与演示边界见 [原型说明](prototype/README.md)。

---

# 内蒙古自然资源一张图多端工作区

## 目录与入口

| 应用 | 独立目录 | 本机入口 |
| --- | --- | --- |
| 原有公众门户 | nmg-onemap-portal | http://localhost:5180/portal/ |
| 后台管理 | nmg-onemap-admin | http://localhost:5180/admin/ |
| 业务一张图 | nmg-onemap-business | http://localhost:5180/business/ |
| 态势驾驶舱 | nmg-onemap-dashboard | http://localhost:5180/dashboard/ |
| 移动工作台 PWA | nmg-onemap-mobile | http://localhost:5180/mobile/ |

各端分别拥有 HTML、业务脚本和样式文件。公共库在 `nmg-onemap-shared`，共享 API 在 `nmg-onemap-service`，不安装全局依赖。

## 启动

旧工程已移至 `bak/`。在工作区根目录执行：

```sh
npm ci --prefix bak/nmg-onemap-shared --registry=https://registry.npmjs.org
python3 bak/nmg-onemap-service/server.py --port 5180
```

需要 Python 3.9+、Node.js/npm。若端口占用，修改 `--port` 后使用对应地址。数据自动保存在 `nmg-onemap-service/data/platform.sqlite3`，重启保留。服务仅监听本机，不直接对外开放。

## 当前交付范围

四个新增端是可交互、共用 SQLite 的本地协同版本，不是图片原型。含 CRUD、筛选分页、附件、状态流转、审计、空间计算、报表、移动取证与离线队列。

原有门户保持不变，仍使用原来的本地存储，尚未接入新 API。后台栏目、流程、参数配置目前保存配置记录，不会自动改变原有门户，也不是可执行 BPM 工作流引擎。

演示身份可直接选择，不是生产认证；空间范围和业务记录均为演示数据。移动端是 PWA，未生成 APK/IPA。正式上线仍需真实统一身份认证、数据权限分级、脱敏加密、正式 GIS 服务与审查规则、部署和安全测评。

详细交付边界与验证方式见 [docs/multi-client-delivery.md](docs/multi-client-delivery.md)，每个应用目录都有自己的 README。
