from html import escape
from pathlib import Path

items = {
'domestic': [
 ('山河有约 风景正好——文旅新“县”象一线观察','文旅','2026-08-28','中国网','https://news.china.com/domestic/945/20260828/49704438.html','多地以县域为载体推进文旅融合，新的文旅消费场景正在基层展开。'),
 ('洗涤用品新国标出台：上市须安全评估','民生','2026-08-27','央视新闻','https://news.china.com/domestic/945/20260827/49701369.html','洗涤用品新国标提出上市前安全评估要求，消费者使用安全与行业规范进一步受到关注。'),
 ('充电桩也有身份证了 电车充电桩强制3C认证落地','产业','2026-08-27','央视新闻','https://news.china.com/domestic/945/20260827/49701285.html','电动汽车充电桩强制3C认证落地，充电设施的安全和质量管理将更受重视。'),
],
'international': [
 ('中国新能源靠实力深耕欧洲腹地','产业','2026-08-28','中国网','https://news.china.com/international/1000/20260828/49704613.html','中国新能源产品和产业链持续进入欧洲市场，全球绿色产业竞争与合作仍在推进。'),
 ('军事手段能压住狂飙的美债吗？','地缘','2026-08-28','中国网','https://news.china.com/international/1000/20260828/49704600.html','美国债务问题与地缘安全议题交织，市场对财政可持续性和政策工具的讨论升温。'),
 ('美加贸易谈判破裂后，卡尼欲找欧盟“抱团”','外交','2026-08-28','中国网','https://news.china.com/international/1000/20260828/49704553.html','美加贸易谈判出现破裂后，加拿大寻求与欧盟加强协调，北美贸易关系面临新的变量。'),
],
'finance': [
 ('商务部回应美考虑对华额外加征7.5%关税','宏观','2026-08-27','东方财富网','https://finance.eastmoney.com/a/202608273856302435.html','商务部就美国考虑对华额外加征关税作出回应，贸易政策变化仍是市场关注焦点。'),
 ('沪指涨逾1% 科创50指数大涨近4% 半导体板块爆发','市场','2026-08-27','东方财富网','https://finance.eastmoney.com/a/202608273856285573.html','A股主要指数走强，科创50涨幅突出，半导体板块成为当日市场热点。'),
 ('存储芯片牛股公布“炸裂”业绩：净赚超36亿元 同比增长超2200%！','行业','2026-08-28','东方财富网','https://finance.eastmoney.com/a/202608283857027470.html','存储芯片企业披露亮眼业绩，行业景气度和企业盈利弹性再次受到投资者关注。'),
],
'tech': [
 ('苹果秋季发布会定档 9 月 10 日','硬件','2026-08-28','IT之家','https://www.ithome.com/0/994/787.htm','苹果秋季发布会日期公布，新品发布节奏和后续产品动向值得关注。'),
 ('小米澎湃 OS 4 新特性：双持小米手机可跨设备接听来电、接收验证码','国产','2026-08-28','IT之家','https://www.ithome.com/0/994/944.htm','澎湃OS 4新增跨设备接听来电、接收验证码等能力，手机协同体验继续深化。'),
 ('古尔曼解读苹果 iPhone 18 Pro / Max 邀请函：可变光圈、新天蓝色','硬件','2026-08-28','IT之家','https://www.ithome.com/0/994/909.htm','围绕iPhone 18 Pro系列的邀请函解读指向可变光圈和新配色，苹果影像与设计路线引发讨论。'),
],
'ai': [
 ('黄仁勋驳斥“循环融资”质疑：AI 行业需要巨额资金，英伟达投资风险很低','大模型','2026-08-28','IT之家','https://www.ithome.com/0/994/943.htm','黄仁勋回应AI产业融资争议，强调行业建设需要大量资本投入，AI商业化与投资风险仍在博弈。'),
 ('Cloudflare 称 AI 智能体已占 60% 互联网流量，同比激增 1700%','Agent','2026-08-28','IT之家','https://www.ithome.com/0/994/571.htm','Cloudflare披露AI智能体流量占比及增速数据，智能体对网络基础设施和流量结构的影响正在扩大。'),
 ('24 个调试补丁、18 次内核启动：Linux 之父托瓦兹借助 AI 定位 Intel Xe 黑屏故障','开源','2026-08-28','IT之家','https://www.ithome.com/0/994/499.htm','托瓦兹借助AI辅助定位Intel Xe黑屏故障，案例展示了AI在复杂软件调试中的实际作用。'),
]
}
colors={'国内':'tag-green','国际':'tag-red','财经':'tag-purple','科技':'tag-blue','AI':'tag-orange'}
labels={'domestic':'国内','international':'国际','finance':'财经','tech':'科技','ai':'AI'}
icons={'domestic':'🏮','international':'🌍','finance':'📈','tech':'💻','ai':'🧠'}
for cat, rows in items.items():
    out=[]
    color=colors[labels[cat]]
    for n,(title,tag,date,source,url,summary) in enumerate(rows,1):
        aid=f'{cat}-{n}'
        out.append(f'''<a class="card-link" onclick="openDetail('{aid}'); return false;" href="#"><div class="news-card"><span class="tag {color}">{escape(tag)}</span><div class="emoji-icon">{icons[cat]}</div><h3>{escape(title)}</h3><p class="card-summary">{escape(summary)}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{aid}"><div class="detail-meta"><span>📅 {date}</span><span>📰 {escape(source)}</span><span class="tag {color}">{escape(tag)}</span></div><div class="detail-visual"></div><h2>{escape(title)}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{escape(summary)}</strong></div><div class="keypoint-card"><span>影响</span><strong>相关行业与市场关注度上升。</strong></div><div class="keypoint-card"><span>数据</span><strong>页面标题披露了事件核心信息。</strong></div><div class="keypoint-card"><span>后续</span><strong>关注后续政策、市场和产业进展。</strong></div></div><p>{escape(summary)}</p><p>以上信息据原文标题及页面摘要整理，具体细节以原文为准。</p><a class="external-btn" href="{url}" target="_blank" rel="noopener">阅读原文</a></template>''')
    Path('dist/sections').mkdir(parents=True,exist_ok=True)
    Path(f'dist/sections/{cat}.html').write_text('\n'.join(out)+'\n',encoding='utf-8')
