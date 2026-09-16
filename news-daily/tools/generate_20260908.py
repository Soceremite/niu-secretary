from pathlib import Path
from html import escape
from datetime import datetime
D='2026-09-08'
items={
'domestic':[
('2027春夏北京时装周拉开帷幕','https://news.china.com/domestic/945/20260908/49725984.html','文化产业','北京时装周启动，时尚产业与城市文化消费的融合继续展开。'),
('白露的田野','https://news.china.com/domestic/945/20260908/49725958.html','节气民生','白露时节各地呈现秋收、农事与生态景观，季节性生产生活进入新阶段。'),
('在自然“课堂”，小动物学什么？','https://news.china.com/domestic/945/20260908/49725764.html','生态科普','报道关注自然观察与生态科普，让公众从真实环境理解动物与自然关系。'),
('流量面前守住边界（民生观）','https://news.china.com/domestic/945/20260908/49725752.html','社会治理','文章讨论流量传播中的边界意识，强调公共表达仍需尊重事实与规则。'),
('北斗规模应用从“天边”到“身边”','https://news.china.com/domestic/945/20260908/49725727.html','卫星应用','北斗系统持续进入交通、农业等日常场景，卫星导航的规模化应用不断深化。')],
'international':[
('日本冲绳县知事选举在即 民调显示选情胶着','https://news.china.com/international/1000/20260908/49726050.html','日本政治','冲绳县知事选举临近，民调显示竞争胶着，地方议题与政策取向受到关注。'),
('特朗普要给新墨西哥州改名“新美国州”？','https://news.china.com/international/1000/20260908/49726086.html','美国政治','特朗普提出更改新墨西哥州名称的说法，引发对其政治表达和地方反应的讨论。'),
('巴拿马运河：为保障水资源安全或将再减通航量','https://news.china.com/international/1000/20260908/49725942.html','全球航运','巴拿马运河面临水资源管理压力，通航量调整可能影响全球航运安排。'),
('霍尔木兹海峡通航量降至5月来最低','https://news.china.com/international/1000/20260907/49724364.html','中东局势','霍尔木兹海峡通航量下降，地区安全风险对能源运输与国际市场的影响受到关注。'),
('欧盟委员会主席访问丹麦格陵兰岛','https://news.china.com/international/1000/20260907/49723108.html','北极事务','欧盟委员会主席访问格陵兰岛，北极事务、地区合作与战略关注度继续上升。')],
'finance':[
('“黑天鹅”突袭！市场猛烈抛售！德国传来大消息','https://finance.eastmoney.com/a/202609083867184697.html','全球市场','全球市场出现剧烈波动，德国方面的新消息进一步牵动风险资产定价。'),
('华为时隔六年再次发布高性能芯片','https://finance.eastmoney.com/a/202609073866641930.html','产业资本','华为发布高性能芯片，国产半导体产业链和相关资本市场预期受到关注。'),
('5年投资3.8万亿！工信部：有序部署万卡、十万卡及以上智算集群','https://finance.eastmoney.com/a/202609073866977064.html','算力产业','工信部披露智算基础设施部署方向，算力投资和通信产业链迎来长期规划信号。'),
('A股三大指数走势分化 创业板指涨超3% CPO概念股爆发','https://finance.eastmoney.com/a/202609073866639128.html','A股市场','A股主要指数表现分化，创业板指走强，CPO等算力相关概念成为市场热点。'),
('3家A股券商9月15日起停牌！中金公司重组获证监会批复','https://finance.eastmoney.com/a/202609073867020110.html','证券行业','券商重组事项获得监管批复，相关公司停牌安排和行业整合进程值得关注。')],
'tech':[
('20.99万元起小米澎程系列汽车发布','https://www.ithome.com/0/999/456.htm','智能汽车','小米澎程系列汽车公布售价并发布，新能源车市场竞争延伸至更细分的产品布局。'),
('华为史上最强麒麟芯9050 Pro登场','https://www.ithome.com/0/999/416.htm','芯片硬件','华为发布麒麟9050 Pro，国产高性能移动芯片的产品竞争继续升温。'),
('5999元起华为 Pura X View 阔直板手机正式上市','https://www.ithome.com/0/999/348.htm','消费电子','华为Pura X View正式上市，阔直板屏幕形态和定价成为新品关注重点。'),
('小米18 Fold中折叠手机发布：首发玄戒O3芯片','https://www.ithome.com/0/999/441.htm','折叠屏','小米发布中折叠手机并搭载玄戒O3芯片，折叠屏市场的产品形态持续丰富。'),
('欧洲商业航天取得突破：德国“光谱”火箭首次成功入轨','https://www.ithome.com/0/998/882.htm','商业航天','德国伊萨尔“光谱”运载火箭首次成功入轨，欧洲商业航天出现新的进展。')],
'ai':[
('科技巨头密集更新AI模型，“模型疲劳”问题凸显','https://www.ithome.com/0/999/036.htm','模型产业','多家科技公司密集更新模型，行业开始讨论产品同质化、成本与用户注意力问题。'),
('微软借力AI重塑Win11应用生态：30分钟即可生成WinUI原生应用','https://www.ithome.com/0/999/015.htm','AI开发','微软展示利用AI生成WinUI原生应用的路径，软件开发门槛和工具链正在变化。'),
('开源安卓应用商店F-Droid考虑效仿Debian AI政策','https://www.ithome.com/0/998/895.htm','开源治理','F-Droid讨论允许使用AI但由贡献者承担最终责任，开源项目的AI协作规范受到关注。'),
('微软发布MAI-Image-2.6-Flash：生图速度是全球最佳AI模型的2倍','https://www.ithome.com/0/998/747.htm','生成式AI','微软发布MAI-Image-2.6-Flash并开放预览，图像生成模型的速度竞争继续加剧。'),
('微软给Copilot AI智能体加“刹车”：发邮件等操作可先请求审批','https://www.ithome.com/0/998/252.htm','Agent安全','微软为Copilot智能体加入高风险操作审批机制，智能体的权限控制与可审计性更加重要。')]
}
meta={'domestic':('国内','tag-green','中国网'),'international':('国际','tag-red','中国网'),'finance':('财经','tag-purple','东方财富网'),'tech':('科技','tag-blue','IT之家'),'ai':('AI','tag-orange','IT之家')}
root=Path(__file__).resolve().parent.parent; out=root/'dist/sections'; out.mkdir(parents=True,exist_ok=True)
for cat,rows in items.items():
 label,color,source=meta[cat]; chunks=[]
 for n,(title,url,tag,summary) in enumerate(rows,1):
  oid=f'{cat}-{n}'; t=escape(title); s=escape(summary); u=escape(url,quote=True)
  chunks.append(f'''<a class="card-link" onclick="openDetail('{oid}'); return false;" href="#"><div class="news-card"><span class="tag {color}">{escape(tag)}</span><div class="emoji-icon">📰</div><h3>{t}</h3><p class="card-summary">{s}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{oid}"><div class="detail-meta"><span>📅 {D}</span><span>📰 {source}</span><span class="tag {color}">{escape(tag)}</span></div><div class="detail-visual"></div><h2>{t}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{s}</strong></div><div class="keypoint-card"><span>影响</span><strong>{escape(tag)}领域出现新的值得关注变化</strong></div><div class="keypoint-card"><span>数据</span><strong>原文标题披露了事件核心信息</strong></div><div class="keypoint-card"><span>后续</span><strong>关注后续公开信息与实际推进情况</strong></div></div><p>{s}</p><p>这条消息反映出当前{label}领域的最新动向，后续进展仍值得持续关注。</p><a class="external-btn" href="{u}" target="_blank" rel="noopener">阅读原文</a></template>''')
 (out/f'{cat}.html').write_text('\n'.join(chunks)+'\n',encoding='utf-8')
print('generated',sum(len(v) for v in items.values()),'articles')
