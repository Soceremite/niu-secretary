from pathlib import Path
from html import escape

D='2026-09-14'
items={
'domestic':[
('平陆运河16日通航 准备工作进展如何','https://news.china.com/domestic/945/20260914/49738658.html','重大工程','平陆运河即将通航，相关准备工作和通航安排受到关注。'),
('16日启航！平陆运河首批外贸货物顺利通关','https://news.china.com/domestic/945/20260914/49738637.html','开放通道','平陆运河首批外贸货物顺利通关，西部陆海新通道建设取得新进展。'),
('多领域达成丰硕成果 2026服贸会交出亮眼成绩单','https://news.china.com/domestic/945/20260914/49738560.html','服务贸易','2026服贸会集中呈现多领域合作成果，服务贸易开放与创新继续推进。')],
'international':[
('莱茵河低水位或致德国巨额经济损失','https://news.china.com/international/1000/20260914/49738505.html','欧洲经济','莱茵河水位偏低可能影响德国航运和产业运输，极端天气的经济外溢效应受到关注。'),
('克罗地亚布拉奇岛发生山火 近700人被疏散','https://news.china.com/international/1000/20260914/49738495.html','灾害救援','克罗地亚布拉奇岛发生山火，近700人被疏散，火情处置和人员安全是当前重点。'),
('伊拉克逐步重新开放与伊朗接壤边境口岸','https://news.china.com/international/1000/20260914/49738485.html','地区安全','伊拉克开始逐步重新开放部分边境口岸，地区局势对人员与物流往来的影响值得观察。')],
'finance':[
('清晨集体杀跌！伊朗突发爆炸！美股、黄金、白银下挫','https://finance.eastmoney.com/a/202609143872942391.html','全球市场','地缘局势消息引发避险资产与风险资产同步波动，美股、黄金和白银盘中走弱。'),
('AI利空突袭！三大巨头罕见联手呼吁：放缓！','https://finance.eastmoney.com/a/202609143872945253.html','产业投资','AI产业相关风险讨论升温，行业巨头对发展节奏的表态可能影响市场预期。'),
('罕见！广汽集团A股停牌港股大幅高开 中国汽车行业重大重组传闻升温','https://finance.eastmoney.com/a/202609143872985064.html','汽车产业','广汽集团A股停牌、港股走高，汽车行业重组预期受到资本市场关注。'),
('美联储9月加息概率逼近90%！特朗普再度施压：美国利率应全球最低','https://finance.eastmoney.com/a/202609143872953521.html','利率政策','美联储议息会议临近，市场利率预期与政策表态交织，全球资产定价面临重新调整。'),
('两只PCB大牛股双双澄清：未向英伟达供货 无业务合作','https://finance.eastmoney.com/a/202609143872947024.html','上市公司','两家PCB公司就与英伟达的供货及合作关系作出澄清，市场应区分公司公告与传闻。')],
'tech':[
('5999 元起华为 Pura X View 阔直板手机正式上市：16:9.5 比例面板、麒麟 9030S 处理器','https://www.ithome.com/0/999/348.htm','手机硬件','华为Pura X View正式上市，采用阔直板形态并搭载麒麟9030S处理器。'),
('华为史上最强处理器！麒麟 9050 Pro 官宣，Mate XT 2 非凡大师全新展翼三折叠手机首发搭载','https://www.ithome.com/0/999/294.htm','国产芯片','麒麟9050 Pro与Mate XT 2三折叠手机成为焦点，国产芯片与高端终端协同推进。'),
('小米 18 Fold 中折叠手机发布：首发玄戒 O3 芯片，10999 元起','https://www.ithome.com/0/999/441.htm','折叠屏','小米发布中折叠手机并首发玄戒O3芯片，折叠屏高端市场竞争进一步加剧。')],
'ai':[
('DeepSeek 官宣明日 flash 系列 AI 模型降价：输出为每百万 Token 4 元','https://www.ithome.com/0/999/953.htm','模型价格','DeepSeek宣布下调flash系列模型输出价格，开发者调用成本有望下降。'),
('谷歌 DeepMind 推出 AlphaGenome Atlas，覆盖人类基因组全部 90 亿种单核苷酸变异预测','https://www.ithome.com/0/999/937.htm','生物AI','AlphaGenome Atlas将模型能力用于基因组变异预测，AI与生物医学研究的结合进一步深化。'),
('微软升级盖茨愿景：要让每个家庭每张办公桌都拥有不受限制的智能','https://www.ithome.com/0/999/874.htm','AI愿景','微软提出面向家庭和办公场景的智能化愿景，AI产品的普及路径受到关注。'),
('微软纳德拉发布 Opal：用户只需提目标，AI 跑全流程交付成品','https://www.ithome.com/0/999/797.htm','智能体','Opal强调从目标理解到流程执行和结果交付，AI Agent继续向端到端自动化发展。')]
}
meta={'domestic':('国内','tag-green','中国网'),'international':('国际','tag-red','中国网'),'finance':('财经','tag-purple','东方财富网'),'tech':('科技','tag-blue','IT之家'),'ai':('AI','tag-orange','IT之家')}
root=Path(__file__).resolve().parent.parent/'dist'/'sections'; root.mkdir(parents=True,exist_ok=True)
for cat,rows in items.items():
    section,color,source=meta[cat]; out=[]
    for i,(title,url,tag,summary) in enumerate(rows,1):
        oid=f'{cat}-{i}'; t=escape(title); s=escape(summary); u=escape(url,quote=True); tg=escape(tag)
        out.append(f'''<a class="card-link" onclick="openDetail('{oid}'); return false;" href="#"><div class="news-card"><span class="tag {color}">{tg}</span><div class="emoji-icon">📰</div><h3>{t}</h3><p class="card-summary">{s}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{oid}"><div class="detail-meta"><span>📅 {D}</span><span>📰 {source}</span><span class="tag {color}">{tg}</span></div><div class="detail-visual"></div><h2>{t}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{t}</strong></div><div class="keypoint-card"><span>影响</span><strong>{s}</strong></div><div class="keypoint-card"><span>数据</span><strong>原文报道披露相关最新进展</strong></div><div class="keypoint-card"><span>后续</span><strong>后续影响仍需结合权威信息持续观察</strong></div></div><p>{s}</p><p>这条消息反映出{section}领域的最新动向，相关进展值得持续关注。</p><a class="external-btn" href="{u}" target="_blank" rel="noopener">阅读原文</a></template>''')
    (root/f'{cat}.html').write_text('\n'.join(out),encoding='utf-8')
print('generated',sum(map(len,items.values())))
