import {landscapePhotos} from './landscape-photos.js';
// Editorial introductions; these are not official boundaries, statistics or service locations.
export const topicGuides={
 landscape:{cover:'nature',kicker:'山川之间 · 认识北疆',intro:'沿着草原、森林与沙漠，理解不同景观中的水、土壤和生命。',sections:[
 {title:'草原：读懂开阔的绿色',text:'草原不只有风景。草本植被、土壤和放牧活动相互联系，认识草原时可以从植被类型、季节变化与合理利用三个角度观察。进入草原游览，请沿开放线路行走，避免碾压植被。'},
 {title:'森林：山地中的生态联系',text:'森林为野生生物提供栖息空间，也参与水源涵养和土壤保持。观察森林景观，可以关注林地与河流、湿地、草原之间的联系；防火期和保护地开放要求以当地公告为准。'},
 {title:'沙漠：看见地貌与适应',text:'沙丘形态随风与地表条件变化，荒漠植物则展现出适应干旱环境的方式。沙漠与沙地并非完全相同，理解其环境背景，有助于认识防沙治沙为何需要因地制宜。'},
 {title:'河流与湖泊：循水认识自然',text:'河流、湖泊与周边湿地连接着流域中的生态过程。观察水域时，不只看水面，也要关注岸带植被与季节变化；不要将景观介绍中的范围当作保护区法定边界。'}],needs:'已配草原实景照片；经核实的景点位置与短视频待补充。'},
 planning:{cover:'planning',kicker:'空间有序 · 生活有章',intro:'从公开规划成果出发，认识生态、农业与城镇空间之间的关系。',sections:[
 {title:'先认识规划的层次',text:'阅读国土空间规划，先确认规划层级、适用地区和期限。总体规划与详细规划承担不同任务，不能用一张概念示意图替代所在地的具体规划要求。'},
 {title:'如何阅读规划图集',text:'先看图名与图例，再核对比例尺、坐标系和编制时间。相似颜色在不同图集中未必代表同一用途；具体空间范围应结合正式图件及说明阅读。'},
 {title:'查询所在地的要求',text:'查询时需要明确行政区或地块位置，并核对已批准且有效的公开成果。当前尚未接入所在地管控查询数据，可先进入规划公示查阅公开信息；本页不生成地块合规结论。'},
 {title:'参与规划公示',text:'关注公示期限、发布单位与反馈渠道，结合公示材料提出具体意见。公开征求意见的草案与已经批准的成果应分别识别。'}],needs:'正式规划摘要、图集附件及所在地管控查询服务待接入。'},
 energy:{cover:'energy',kicker:'资源禀赋 · 绿色转型',intro:'从不同资源类型出发，认识能源保障、战略资源与生态保护的关系。',sections:[
 {title:'煤炭：从资源到利用',text:'阅读煤炭资源专题，应区分资源分布、勘查成果、矿业权和生产项目。它们的范围和含义不同，开发利用情况还需结合公开规划、许可与统计资料。'},
 {title:'稀土：认识战略矿产',text:'稀土属于矿产资源范畴，是许多材料和产业链的重要组成部分。理解稀土专题时，应区分资源禀赋、开采、加工和综合利用，不将其直接等同于能源产量。'},
 {title:'风能：理解风与空间',text:'风能开发需要结合风资源条件、土地利用、生态约束和电网接入等因素。地图中的项目位置不能仅依据风速推断，应以公开项目与规划信息为依据。'},
 {title:'太阳能：从光照到应用',text:'太阳能利用有多种形式。阅读基地资料时，注意项目阶段、统计年份与指标单位，区分规划规模、已建规模和实际发电量。'}],needs:'资源分布图、基地资料和有出处的统计图表待发布。'},
 public:{cover:'public',kicker:'服务身边 · 便民可达',intro:'了解自然资源公共服务的使用方式，从所需事项找到对应入口。',sections:[
 {title:'先找事项，再找服务地点',text:'办理前确认服务事项、受理单位与适用地区，再核对地址、开放时间和材料。服务点位尚未核实时，不以地图中的示意位置指引现场办理。'},
 {title:'不动产与用地相关服务',text:'可通过下方入口查看不动产登记信息查询、用地审批进度等服务说明。涉及个人或企业办件的信息，应在具备权限的系统中查询。'},
 {title:'认识地灾避险信息',text:'避险场所、路线及开放状态需要由业务单位核实并及时更新。发生险情时以属地部门发布的预警和现场指引为准；本栏目当前不提供实时避险导航。'}],needs:'公共服务站点、地灾避险场所的核实位置与开放信息待补充。'},
 ecology:{cover:'ecology',kicker:'生态优先 · 共同守护',intro:'从重大生态工程的目标与措施出发，理解保护修复如何作用于山水林田湖草沙。',sections:[
 {title:'“三北”防护林：认识防护体系',text:'防护林建设需要结合气候、水资源和立地条件，综合理解林、草与其他防护措施的作用。认识工程时应同时关注建设位置、适宜性和长期管护。'},
 {title:'退牧还草：关注草原恢复',text:'草原保护修复与利用方式、植被恢复和管护措施密切相关。评价变化应采用同一统计口径和可比时期，不能只凭某一时点的照片判断工程成效。'},
 {title:'京津风沙源治理：因地制宜',text:'防沙治沙并非把所有区域都种成森林。应根据自然条件选择适宜措施，并关注水土资源承载能力、植被恢复与长期维护。'},
 {title:'湿地保护恢复：维护生态过程',text:'湿地保护需要关注水文过程、生境及周边活动的影响。展示恢复成效时，宜结合经核实的工程范围、监测记录及同季节影像，注明时间和来源。'}],needs:'工程实施边界、分年度成效和可比影像待业务单位核实发布。'}
};
export function guideFor(topic){const d=topicGuides[topic.id]||{cover:'nature',kicker:'专题导读',intro:topic.summary,sections:[],needs:'专题资料以发布内容为准。'};return {...d,intro:topic.summary||d.intro,sections:Array.isArray(topic.sections)?topic.sections:d.sections};}
export function topicPhoto(topic){return landscapePhotos[topic.cover]||landscapePhotos[guideFor(topic).cover]||landscapePhotos.nature;}
export function topicCover(topic){return topic.coverUrl||`/assets/photos/${topicPhoto(topic).file}`;}
export function topicCoverAlt(topic){return topic.coverUrl?`${topic.name}封面`:topicPhoto(topic).label+'实景照片';}
function photoCredit(topic,esc){const p=topicPhoto(topic);return topic.coverUrl?esc(topic.coverCredit||'专题配置封面'):`${esc(p.label)} · 摄影 ${esc(p.artist)} · ${esc(p.license)}`;}
function photoLinks(topic,esc){const p=topicPhoto(topic);return topic.coverUrl?'':`<a href="${esc(p.page)}" target="_blank" rel="noopener noreferrer">照片来源 ↗</a><a href="${esc(p.licenseUrl)}" target="_blank" rel="noopener noreferrer">${esc(p.license)}</a>`;}
export function landscapePage(id,{topics,services,resources,esc,icon}){
 const ordered=[...topics].sort((a,b)=>(a.order||0)-(b.order||0));
 const link=t=>`#/front/landscape/${encodeURIComponent(t.id)}`;
 if(!id)return `<section class="scenic-intro"><div><span class="pub-eyebrow">生态优先 · 绿色发展</span><h1>大美内蒙古</h1><p>从一张地图出发，认识自然之美、空间格局与绿色发展。</p><div class="scenic-topic-nav">${ordered.map(t=>`<a href="${link(t)}">${esc(t.name)} ${icon('arrow')}</a>`).join('')}</div></div><img src="/assets/photos/scenic-nature.jpg" alt="呼伦贝尔草原实景"><small>呼伦贝尔草原 · 摄影 Emmazzye · CC BY-SA 4.0</small></section><section class="scenic-overview"><div><span class="pub-eyebrow">在地图上认识北疆</span><h2>从空间认识自然与发展</h2><p>浏览自治区与盟市位置，再选择专题深入了解。当前地图展示行政区底图，不表示景观、工程或服务站点的分布。</p><div class="scenic-region-links">${['呼伦贝尔市','锡林郭勒盟','阿拉善盟'].map(region=>`<button type="button" class="btn" data-action="pub-topic-region" data-id="${region}">${region} ${icon('arrow')}</button>`).join('')}</div></div><div id="pub-landscape-map" class="pub-map"></div></section><section class="pub-section"><div class="pub-section-head"><div><h2>五个专题，读懂内蒙古</h2><p>自然景观、规划成果、资源禀赋、公众服务与生态保护。</p></div></div><div class="scenic-catalog">${ordered.map((t,i)=>`<a class="scenic-story" href="${link(t)}"><div class="scenic-cover"><img src="${esc(topicCover(t))}" alt="${esc(topicCoverAlt(t))}" loading="lazy"><span>${String(i+1).padStart(2,'0')} / ${esc(t.category)}</span></div><div><h3>${esc(t.name)} ${icon('arrow')}</h3><p>${esc(guideFor(t).intro)}</p><small>${photoCredit(t,esc)}</small></div></a>`).join('')}</div><p class="scenic-photo-sources"><a href="/assets/photos/credits.html" target="_blank" rel="noopener noreferrer">实景图片来源与授权 ↗</a></p></section>`;
 const t=ordered.find(t=>t.id===id);if(!t)return '<div class="pub-note">专题尚未发布或已下架。<a href="#/front/landscape">返回大美内蒙古</a></div>';
 const g=guideFor(t),related=(t.resourceIds||[]).map(id=>resources.find(r=>r.id===id)).filter(Boolean),media=t.media||[];
 return `<div class="scenic-subnav"><a href="#/front/landscape">全部专题</a>${ordered.map(x=>`<a href="${link(x)}" ${x.id===id?'class="active" aria-current="page"':''}>${esc(x.name)}</a>`).join('')}</div><section class="scenic-detail-head"><div><span class="pub-eyebrow">${esc(g.kicker)}</span><h1>${esc(t.name)}</h1><p>${esc(g.intro)}</p><small>${esc(t.source)} · 更新 ${esc(t.updated?.slice(0,10)||'—')}</small></div><img src="${esc(topicCover(t))}" alt="${esc(topicCoverAlt(t))}"><span>${photoCredit(t,esc)}</span></section><div class="scenic-photo-sources">${photoLinks(t,esc)}</div><div class="scenic-reading"><section><div id="pub-topic-map" class="pub-map"></div><div id="pub-map-info" role="status"></div><div class="scenic-map-note"><strong>专题资料状态</strong><p>${esc(g.needs)}</p>${related.length?`<p>已关联 ${related.length} 项目录资源，可按当前权限查看；关联不代表正式专题数据已齐备。</p>`:''}</div></section><section class="scenic-reader"><div class="scenic-reader-heading"><span class="pub-eyebrow">专题导读</span><h2>了解这一主题</h2></div><div class="scenic-chapters">${g.sections.map((s,i)=>`<details ${i===0?'open':''}><summary><span>${String(i+1).padStart(2,'0')}</span>${esc(s.title)}</summary><p>${esc(s.text)}</p></details>`).join('')||'<p>分节内容待发布。</p>'}</div><details class="scenic-original"><summary>查看发布说明</summary><p>${esc(t.body).replace(/\n/g,'<br>')}</p></details></section></div><section class="scenic-bottom"><div><h2>影像与资料</h2>${media.length?`<div class="scenic-media">${media.map(m=>`<article>${m.type==='image'?`<img src="${esc(m.url)}" loading="lazy" alt="${esc(m.title)}">`:m.type==='video'?`<video src="${esc(m.url)}" controls preload="none" aria-label="${esc(m.title)}"></video>`:''}<a href="${esc(m.url)}" target="_blank" rel="noopener noreferrer">${esc(m.title)} ↗</a><small>来源：${esc(m.source)}</small></article>`).join('')}</div>`:`<p class="muted">${t.coverUrl?'本专题已配置封面。':'本专题配图为'+esc(topicPhoto(t).label)+'实景。'}更多影像、视频与图集待补充；配图不作为规划、服务站点或工程成效依据。</p>`}${t.url?`<a class="btn" href="${esc(t.url)}" target="_blank" rel="noopener noreferrer">查看已发布专题资料 ↗</a>`:''}</div><div><h2>${id==='public'?'相关便民入口':id==='planning'?'规划查询与参与':'继续探索'}</h2><div class="scenic-related">${related.map(r=>`<a href="#/front/data/${encodeURIComponent(r.id)}">${esc(r.name)} ${icon('arrow')}</a>`).join('')}${services.filter(s=>id==='public'||id==='planning'&&s.id==='notice').map(s=>`<a href="#/front/services/${encodeURIComponent(s.id)}">${esc(s.name)} ${icon('arrow')}</a>`).join('')}<a href="#/front/data">查找相关数据 ${icon('arrow')}</a><a href="#/front/knowledge">查阅政策与资料 ${icon('arrow')}</a></div></div></section>`;
}
