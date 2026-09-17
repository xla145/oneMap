// Shared demo prompts: comparisons use the published demo_cropland table.
export const qaGroups = [
  {name:'常用办事', questions:['用地审批进度怎么查？','数据申请需要什么材料？','不动产登记信息如何查询？','什么是耕地占补平衡？']},
  {name:'数据对比 · 演示', questions:['对比2026年呼和浩特市和包头市的耕地面积','呼和浩特市2025年与2026年耕地面积变化多少？','对比2026年呼和浩特市的耕地面积和保护目标','对比2026年呼和浩特市和包头市的耕地保护达标指数']},
];
export function qaExamples(esc, icon) {
  return `<div class="qa-examples">${qaGroups.map(g=>`<section><h3>${esc(g.name)}</h3><div class="prompt-grid">${g.questions.map(q=>`<button data-action="portalQuestion" data-id="${esc(q)}">${icon('message')}<span>${esc(q)}</span>${icon('arrow')}</button>`).join('')}</div></section>`).join('')}<p class="muted">对比样本：呼和浩特市、包头市 · 2025—2026 年；虚构数据，仅供演示。点击问题即可查看结果和口径。</p></div>`;
}
