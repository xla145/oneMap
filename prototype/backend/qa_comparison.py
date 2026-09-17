"""Rule-based comparisons calculated from published, authorized demo indicators."""
import re
import capabilities as cap


def compare(s, u, agent, question, context, regions):
    if '耕地' not in question or not re.search('对比|比较|变化|增长|同比', question):
        return None
    selected = [r for r in regions if r in question] or [context.get('region', '全区')]
    years = sorted(set(re.findall(r'20\d{2}(?=年)', question)))
    periods = [y + '年' for y in years] or [context.get('period', '全部时间')]
    if periods == ['全部时间'] or periods == ['最近30天']:
        return dict(name='耕地数据对比', rows=[], answer='请指定统计年份，例如：对比2026年呼和浩特市和包头市的耕地面积。')
    metric_ids = ['i_rate'] if '指数' in question else ['i_area', 'i_target'] if '目标' in question else ['i_area']
    scope = cap.ids(agent.get('indicatorIds'))
    results = []
    try:
        for ident in metric_ids:
            row = cap.published(cap.find(s['indicators'], ident))
            cap.require(row and (not scope or ident in scope), '对比指标未发布或不在当前智能体范围内')
            cap.require(row.get('dataMode') in ['table', 'composite'], '对比需要按区域和年度统计的数据')
            for region in selected:
                for period in periods:
                    results.append(cap.calculate(s, row, u, dict(region=region, period=period)))
    except cap.Invalid as e:
        return dict(name='耕地数据对比', rows=[], answer='本次未生成对比：' + e.message + '。请调整区域、年份或访问权限。')
    rows = [{'地区':r['region'], '年份':r['period'], '指标':r['name'], '数值':r['value'], '单位':r['unit']} for r in results]
    answer = '虚构演示数据，不代表实际统计或考核结果。'
    if len(results) == 2:
        a, b = results
        if len(metric_ids) == 2:
            delta = round(a['value'] - b['value'], 2)
            answer += f"面积较目标差额 {delta:+g} 公顷（面积 − 目标）。"
            answer += f"达成比例 {a['value']/b['value']*100:.2f}%。" if b['value'] else '目标为零，无法计算达成比例。'
        else:
            delta = round(b['value'] - a['value'], 2)
            unit = '个百分点' if a['unit'] == '%' else a['unit']
            label_a=a['period'] if len(periods)>1 else a['region']
            label_b=b['period'] if len(periods)>1 else b['region']
            answer += f"{label_b}较{label_a}差额 {delta:+g} {unit}。"
            if a['unit'] != '%':
                answer += f"变化率 {delta/a['value']*100:+.2f}%（以第一项为基期）。" if a['value'] else '基期为零，变化率不适用。'
    answer += '\n' + '\n'.join(dict.fromkeys(f"{r['name']} v{r['version']}：{r['caliber']} 来源：{r['source']}。" for r in results))
    return dict(name='耕地数据对比 · 演示', rows=rows, answer=answer)
