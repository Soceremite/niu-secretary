from pathlib import Path
from html import escape

items = {
'domestic': [
('洗涤用品新国标出台：上市须安全评估','新标准要求相关洗涤用品上市前开展安全评估，消费品安全监管进一步前移。','中华网','2026-08-27','政策'),
('澳琴跨境陆空联运业务今天开通','澳琴跨境陆空联运业务正式开通，为琴澳人员往来和区域协同增加新的交通选择。','中华网','2026-08-27','民生'),
('筑牢技术底座 “人工智能+”加出新速度','报道聚焦人工智能与实体产业融合，技术底座建设正成为推动应用落地的重要支撑。','中华网','2026-08-27','科技'),
('充电桩也有身份证了 电车充电桩强制3C认证落地','电动汽车充电桩强制性产品认证落地，设备安全与质量追溯将进一步加强。','中华网','2026-08-27','产业'),
('携带先进设备 应急救援包机起飞前往西藏日喀则','一架携带先进设备的应急救援包机飞往西藏日喀则，为当地救援工作提供支持。','中华网','2026-08-27','应急'),
],
'international': [
('大量预约“无故”取消，美叫停全球移民签证审理','美国暂停全球移民签证审理，预约取消情况引发对其移民政策走向的关注。','中华网','2026-08-27','移民'),
('特朗普回应美国中情局局长访俄：“半例行公事”','特朗普回应美国中情局局长访问俄罗斯，称此举属于“半例行公事”。','中华网','2026-08-27','外交'),
('税率分为三档，加拿大宣布对美征收反制关税','加拿大宣布按三档税率对美国采取反制关税措施，美加贸易关系再添变量。','中华网','2026-08-27','贸易'),
('硬件短板让美国机器人行业担忧','报道指出硬件供应和制造能力不足，正成为美国机器人产业继续扩张需要面对的短板。','中华网','2026-08-27','产业'),
('伊朗阿曼拟在霍尔木兹建安全通道','伊朗与阿曼拟在霍尔木兹海峡建设安全通道，地区航运安全议题持续受到关注。','中华网','2026-08-27','地缘'),
],
'finance': [
('英伟达业绩大超预期！Q2营收利润双双翻倍 下一财年预计营收再涨70%！','英伟达季度营收和利润均实现翻倍，市场同时关注公司对下一财年的增长预期。','东方财富网','2026-08-27','市场','https://finance.eastmoney.com/a/202608273855299898.html'),
('中金：玻璃基板有望成为下一代先进封装的重要材料平台 关注核心设备放量','中金研报认为玻璃基板可能成为先进封装的重要材料平台，产业链设备需求值得跟踪。','东方财富网','2026-08-27','芯片','https://finance.eastmoney.com/a/202608273855534815.html'),
('中信证券：千亿项目全链条落地 国产算力产业链迎来明确增长机遇','中信证券研报聚焦国产算力项目落地，认为产业链相关环节或迎来更清晰的增长机会。','东方财富网','2026-08-27','算力','https://finance.eastmoney.com/a/202608273855534022.html'),
('中信建投：国际原油价格涨势延续 全球冬季能源安全风险提升','中信建投研报判断国际油价上涨趋势仍在延续，并提示冬季能源安全风险变化。','东方财富网','2026-08-27','能源','https://finance.eastmoney.com/a/202608273855317483.html'),
('苹果秋季发布会 定档9月10日凌晨','苹果秋季发布会时间公布，市场将关注新一代硬件和系统产品的发布安排。','东方财富网','2026-08-27','消费','https://finance.eastmoney.com/a/202608273855271470.html'),
],
'tech': [
('苹果秋季发布会定档 9 月 10 日','苹果官宣秋季发布会将于9月10日举行，新品发布和生态更新成为市场关注焦点。','IT之家','2026-08-27','硬件','https://www.ithome.com/0/994/787.htm'),
('苹果首款折叠手机：iPhone Ultra 主板曝光，内置最强 A20 Pro 芯片','报道称苹果首款折叠手机相关主板信息曝光，传闻中的芯片与产品形态受到关注。','IT之家','2026-08-27','硬件','https://www.ithome.com/0/994/490.htm'),
('工信部：鸿蒙手机操作系统成为世界第三大手机操作系统，开源鸿蒙生态设备累计超 13.5 亿台','工信部公布鸿蒙手机操作系统及开源鸿蒙生态发展信息，生态设备规模持续扩大。','IT之家','2026-08-27','国产','https://www.ithome.com/0/994/630.htm'),
('小米澎湃 OS 4 相机美学焕新：深度对齐系统设计体系，非 Xiaomi 17 Ultra 徕卡版机型可体验','小米澎湃OS 4带来相机界面和体验调整，部分非徕卡版机型也可体验相关更新。','IT之家','2026-08-27','系统','https://www.ithome.com/0/994/573.htm'),
('小米澎湃 OS 4 Beta 版第二批机型开启用户招募','小米澎湃OS 4 Beta第二批招募覆盖小米15系列手机和REDMI K Pad 2平板等设备。','IT之家','2026-08-27','系统','https://www.ithome.com/0/994/419.htm'),
],
'ai': [
('英伟达黄仁勋：AI 已迈过商业化拐点，全球产业进入 AI 变现时代','英伟达黄仁勋表示，AI产业正进入商业化和变现阶段，产业应用价值成为讨论重点。','IT之家','2026-08-27','大模型','https://www.ithome.com/0/994/795.htm'),
('Cloudflare 称 AI 智能体已占 60% 互联网流量，同比激增 1700%','Cloudflare公布数据显示，AI智能体流量占比和增速显著上升，互联网流量结构正在变化。','IT之家','2026-08-27','Agent','https://www.ithome.com/0/994/571.htm'),
('24 个调试补丁、18 次内核启动：Linux 之父托瓦兹借助 AI 定位 Intel Xe 黑屏故障','Linux内核开发者托瓦兹分享借助AI定位Intel Xe黑屏故障的过程，展示AI辅助调试的实际用法。','IT之家','2026-08-27','开源','https://www.ithome.com/0/994/499.htm'),
('商业史最庞大叙事：Anthropic 冲击全球最大 IPO，称 AI 潜在市场收入规模超 30 万亿美元','报道关注Anthropic上市计划及其对AI潜在市场规模的判断，AI公司的资本化进程继续升温。','IT之家','2026-08-27','融资','https://www.ithome.com/0/994/327.htm'),
('AI 竞赛升温：曝 OpenAI 已预训练 Bel 模型：超 10T 参数，冲击通用人工智能','报道援引消息称OpenAI正在预训练Bel模型，相关说法尚待公司或更多权威信息进一步确认。','IT之家','2026-08-27','大模型','https://www.ithome.com/0/994/296.htm'),
]
}
urls_dom = ['https://news.china.com/domestic/945/20260827/49701369.html','https://news.china.com/domestic/945/20260827/49701337.html','https://news.china.com/domestic/945/20260827/49701322.html','https://news.china.com/domestic/945/20260827/49701285.html','https://news.china.com/domestic/945/20260827/49701245.html']
urls_int = ['https://news.china.com/international/1000/20260827/49701497.html','https://news.china.com/international/1000/20260827/49701480.html','https://news.china.com/international/1000/20260827/49701470.html','https://news.china.com/international/1000/20260827/49701450.html','https://news.china.com/international/1000/20260827/49701440.html']
for k, urls in [('domestic',urls_dom),('international',urls_int)]:
    items[k] = [x + (u,) for x,u in zip(items[k],urls)]

def make(cat, arr):
    out=[]
    colors=['tag-red','tag-blue','tag-green','tag-orange','tag-purple']
    icons=['📰','🌏','📈','⚙️','🤖']
    for i,item in enumerate(arr,1):
        title,summary,source,date,tag = item[:5]
        url = item[5] if len(item) > 5 else ''
        ident=f'{cat}-{i}'; c=colors[(i-1)%len(colors)]
        out.append(f'''<a class="card-link" onclick="openDetail('{ident}'); return false;" href="#"><div class="news-card"><span class="tag {c}">{escape(tag)}</span><div class="emoji-icon">{icons[(i-1)%5]}</div><h3>{escape(title)}</h3><p class="card-summary">{escape(summary)}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{ident}"><div class="detail-meta"><span>📅 {date}</span><span>📰 {escape(source)}</span><span class="tag {c}">{escape(tag)}</span></div><div class="detail-visual"></div><h2>{escape(title)}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{escape(summary)}</strong></div><div class="keypoint-card"><span>影响</span><strong>相关政策、产业或市场变化值得持续关注。</strong></div><div class="keypoint-card"><span>数据</span><strong>具体数据以原文及后续官方信息为准。</strong></div><div class="keypoint-card"><span>后续</span><strong>关注后续落地进展与权威信息更新。</strong></div></div><p>{escape(summary)}</p><p>这条消息反映出相关领域正在出现新的变化，后续影响仍需结合更多公开信息观察。</p><a class="external-btn" href="{url}" target="_blank" rel="noopener">阅读原文</a></template>''')
    return '\n'.join(out)+'\n'

p=Path('dist/sections'); p.mkdir(parents=True,exist_ok=True)
for cat,arr in items.items(): (p/f'{cat}.html').write_text(make(cat,arr),encoding='utf-8')
print('wrote', sum(map(len,items.values())), 'articles')
