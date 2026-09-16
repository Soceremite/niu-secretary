from pathlib import Path
from html import escape
from datetime import date
D='2026-09-09'
items={
'domestic':[
('捕捉宇宙古老信标 中国天眼绘就最大宇宙气体图谱','https://news.china.com/domestic/945/20260909/49728482.html','科学发现','中国天眼捕捉宇宙古老信标，绘制出规模更大的宇宙气体图谱，为研究星系演化提供新观测资料。'),
('中国天眼构建世界最大中性氢星系样本库','https://news.china.com/domestic/945/20260909/49728468.html','航天科技','中国天眼持续积累中性氢观测数据，样本库规模取得新进展，天文学研究基础进一步夯实。'),
('科技创新有力助推，中国外贸增势稳定','https://news.china.com/domestic/945/20260909/49728443.html','外贸产业','报道关注科技创新对外贸发展的支撑作用，相关产业的产品竞争力和出口韧性受到关注。')],
'international':[
('天然气、电力双涨价打击日本经济','https://news.china.com/international/1000/20260909/49728912.html','日本经济','天然气和电力价格上涨增加日本经济运行成本，也加重企业和居民端的支出压力。'),
('当气候变化成为影响地缘政治的力量','https://news.china.com/international/1000/20260909/49728892.html','全球治理','气候变化正在通过资源、能源和安全议题影响地缘政治，相关风险的跨区域传导值得关注。'),
('英国宣布制裁约旦河西岸以色列定居点','https://news.china.com/international/1000/20260909/49728840.html','中东局势','英国宣布针对约旦河西岸以色列定居点采取制裁措施，中东局势与外交立场变化继续受到关注。')],
'finance':[
('统计局：8月CPI同比上涨0.8% PPI同比上涨3.8%','https://finance.eastmoney.com/a/202609093868929083.html','宏观数据','国家统计局发布8月价格数据，CPI和PPI同比变化为观察消费需求与工业品价格的重要指标。'),
('A股三大指数涨跌不一 农化制品与石油石化板块大涨','https://finance.eastmoney.com/a/202609083868000213.html','A股市场','A股主要指数表现分化，农化制品与石油石化板块走强，市场资金继续围绕周期和产业线索寻找机会。'),
('瑞银：芯片繁荣趋势未变 存储短缺料持续至明年！','https://finance.eastmoney.com/a/202609093868712413.html','半导体产业','瑞银判断芯片景气趋势仍在延续，并关注存储供需紧张可能持续到明年的产业影响。')],
'tech':[
('高通第六代骁龙 8 超级至尊版实物图','https://www.ithome.com/0/999/649.htm','芯片硬件','高通新一代骁龙8系列芯片实物图曝光，旗舰移动平台的产品节奏和性能竞争继续升温。'),
('华为官宣鸿蒙 HarmonyOS 7 发布 24 小时后累计升级终端设备数突破 500 万','https://www.ithome.com/0/999/895.htm','国产系统','华为公布鸿蒙HarmonyOS 7升级进展，终端生态的系统更新速度和用户覆盖受到关注。'),
('豆包输入法推出 Windows 版，现已覆盖 PC、Mac、iOS、Android 和鸿蒙五大平台','https://www.ithome.com/0/999/934.htm','软件生态','豆包输入法推出Windows版本，覆盖平台进一步扩大，跨设备输入与软件生态布局继续推进。')],
'ai':[
('DeepSeek 官宣明日 flash 系列 AI 模型降价：输出为每百万 Token 4 元','https://www.ithome.com/0/999/953.htm','大模型','DeepSeek宣布flash系列模型将调整价格，模型调用成本变化可能影响开发者选型和AI应用商业化。'),
('谷歌 DeepMind 推出 AlphaGenome Atlas，覆盖人类基因组全部 90 亿种单核苷酸变异预测','https://www.ithome.com/0/999/937.htm','AI科研','谷歌DeepMind推出面向基因组变异预测的工具，人工智能与生命科学研究的结合继续深入。'),
('微软纳德拉发布 Opal：用户只需提目标，AI 跑全流程交付成品','https://www.ithome.com/0/999/797.htm','AI智能体','微软发布Opal相关能力，用户以目标驱动AI完成流程并交付成品，智能体产品化趋势更加明显。')]
}
meta={'domestic':('国内要闻','中国网','tag-green','📰'),'international':('国际焦点','中国网','tag-red','🌏'),'finance':('财经快讯','东方财富网','tag-purple','📈'),'tech':('科技动态','IT之家','tag-blue','⚙️'),'ai':('人工智能','IT之家','tag-orange','🤖')}
root=Path(__file__).resolve().parent.parent; out=root/'dist/sections'; out.mkdir(parents=True,exist_ok=True); all_items=[]
for cat,rows in items.items():
 sec,source,color,icon=meta[cat]; chunks=[]
 for n,(title,url,tag,summary) in enumerate(rows,1):
  ident=f'{cat}-{n}'; t=escape(title); s=escape(summary); u=escape(url,quote=True)
  chunks.append(f'''<a class="card-link" onclick="openDetail('{ident}'); return false;" href="#"><div class="news-card"><span class="tag {color}">{escape(tag)}</span><div class="emoji-icon">{icon}</div><h3>{t}</h3><p class="card-summary">{s}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{ident}"><div class="detail-meta"><span>📅 {D}</span><span>📰 {source}</span><span class="tag {color}">{escape(tag)}</span></div><div class="detail-visual"></div><h2>{t}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{s}</strong></div><div class="keypoint-card"><span>影响</span><strong>{escape(tag)}领域出现新的变化</strong></div><div class="keypoint-card"><span>数据</span><strong>原文标题披露了相关进展</strong></div><div class="keypoint-card"><span>后续</span><strong>关注权威信息与后续落地情况</strong></div></div><p>{s}</p><p>这条消息反映出当前{sec}领域的最新动向，后续影响仍需结合公开信息观察。</p><a class="external-btn" href="{u}" target="_blank" rel="noopener">阅读原文</a></template>''')
  all_items.append({'id':f'detail-{ident}','openId':ident,'section':cat,'sectionName':sec,'title':title,'summary':summary,'dateText':f'📅 {D} 📰 {source} {tag}','sourceName':source,'sourceUrl':url,'tags':[tag]})
 (out/f'{cat}.html').write_text('\n'.join(chunks)+'\n',encoding='utf-8')
(root/'dist/news.json').write_text(__import__('json').dumps({'date':D,'generatedAt':D+'T10:00:00+08:00','version':1,'items':all_items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('generated',len(all_items))
