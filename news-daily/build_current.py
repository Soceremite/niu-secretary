from pathlib import Path
from html import escape
from datetime import date
import json
D='2026-08-30'
items={
'domestic':[
('多种专业设备集结全力抢通G216线受损路段','多种专业设备投入抢通G216线受损路段，灾后交通恢复工作加快推进。','https://news.china.com/domestic/945/20260830/49707602.html','道路抢修','中国网'),
('群众就医负担持续减轻 全国医疗卫生机构超110万个','报道显示，全国医疗卫生机构数量已超过110万个，就医保障与医疗服务能力持续改善。','https://news.china.com/domestic/945/20260830/49707590.html','民生保障','中国网'),
('首个S弯道打通 西藏吉隆道路抢修持续进行','西藏吉隆道路抢修取得新进展，首个S弯道打通，救援通行条件继续改善。','https://news.china.com/domestic/945/20260830/49707576.html','应急救援','中国网')],
'international':[
('美称与委内瑞拉达成石油协议 被批“公然盗窃”','美国方面称与委内瑞拉达成石油协议，但相关做法遭到批评，能源与地区政治矛盾持续升温。','https://news.china.com/international/1000/20260830/49707731.html','地缘政治','中国网'),
('因发帖“嘲讽”比利时官员，美国大使再被召见','美国大使因社交媒体言论被比利时方面再次召见，美欧外交摩擦受到关注。','https://news.china.com/international/1000/20260830/49707722.html','外交摩擦','中国网'),
('日本学者称民众不满致高市内阁支持率走低','日本学者分析认为，民众不满情绪正在影响高市内阁支持率，日本政局走向仍待观察。','https://news.china.com/international/1000/20260830/49707713.html','日本政局','中国网')],
'finance':[
('霍尔木兹海峡最新消息！伊朗：完全关闭！英国考虑对石油公司征收暴利税！世界银行警告！','霍尔木兹海峡局势牵动能源市场，伊朗表态、英国税制讨论与世界银行警告共同增加原油供给和价格预期的不确定性。','https://finance.eastmoney.com/a/202608303859339716.html','能源市场','东方财富网'),
('500亿半导体大牛股筹划重大资产重组 明起停牌','一家市值约500亿元的半导体公司筹划重大资产重组并公告停牌，半导体产业整合预期升温。','https://finance.eastmoney.com/a/202608303859340222.html','资本运作','东方财富网'),
('沃什为9月加息打开大门 美联储或面临巨大政治压力','相关表态为9月加息可能性打开讨论空间，美联储政策与政治压力继续成为全球市场焦点。','https://finance.eastmoney.com/a/202608303859333870.html','货币政策','东方财富网'),
('六大行半年营收首破2万亿元：净利润全员正增长 净息差呈现“两升四降”','六大行上半年营收首次突破2万亿元，净利润均实现增长，但净息差表现出现分化。','https://finance.eastmoney.com/a/202608303859344770.html','银行业','东方财富网'),
('环球下周看点：8月非农数据重磅来袭 博通财报接棒英伟达','下周美国非农数据和博通财报将陆续公布，宏观数据与科技公司业绩可能继续影响市场定价。','https://finance.eastmoney.com/a/202608303859334765.html','市场前瞻','东方财富网')],
'tech':[
('余承东展示华为 Mate XT 2 真机','余承东展示华为Mate XT 2三折叠手机真机，华为折叠屏新品发布节奏进一步明确。','https://www.ithome.com/0/995/910.htm','折叠屏','IT之家'),
('小米 18 Fold 首发长鑫 LPDDR6 内存','小米18 Fold将首发长鑫LPDDR6内存，国产存储器在终端新品中的应用受到关注。','https://www.ithome.com/0/995/869.htm','国产芯片','IT之家'),
('网友建议取消 ETC 设备使用改为扫车牌支付，交通运输部回应','针对取消ETC改用车牌支付的建议，交通运输部作出回应，智慧交通支付方式再次引发讨论。','https://www.ithome.com/0/995/905.htm','智慧交通','IT之家')],
'ai':[
('AI 人才争夺加码：台积电 2026Q2 奖金约为 360 亿新台币，同比增 50.6%','台积电公布的季度奖金信息显示，AI相关需求正在加剧芯片产业人才竞争。','https://www.ithome.com/0/996/073.htm','AI产业','IT之家'),
('少 1 个展开步骤：部分谷歌搜索测试默认进入 AI 模式，下移传统蓝链搜索结果','谷歌测试让部分搜索默认进入AI模式，传统蓝链结果位置下移，搜索产品交互继续变化。','https://www.ithome.com/0/996/062.htm','AI搜索','IT之家'),
('苹果首款 AI 眼镜有望 2027 年亮相：首代无显示屏，瞄准语音与视觉识别','消息称苹果首款AI眼镜或在2027年亮相，首代产品重点可能放在语音与视觉识别能力。','https://www.ithome.com/0/996/053.htm','AI硬件','IT之家'),
('Anthropic 推出 MHS 标准，首度重拳杀入物理 AI 领域','Anthropic推出MHS标准并涉足物理AI，模型能力向现实世界设备与任务延伸的趋势受到关注。','https://www.ithome.com/0/995/514.htm','物理AI','IT之家'),
('Cerebras 揭秘 CS-6 晶圆级进化：颠覆性 3D 堆叠，首次垂直集成 DRAM','Cerebras公布CS-6晶圆级方案，3D堆叠与垂直集成DRAM成为AI算力硬件的新看点。','https://www.ithome.com/0/995/404.htm','AI算力','IT之家')]
}
colors={'domestic':'tag-green','international':'tag-red','finance':'tag-purple','tech':'tag-blue','ai':'tag-orange'}
secname={'domestic':'国内要闻','international':'国际焦点','finance':'财经快讯','tech':'科技动态','ai':'人工智能'}
root=Path(__file__).parent; out=root/'dist/sections'; out.mkdir(parents=True,exist_ok=True)
for cat,rows in items.items():
 c=colors[cat]; chunks=[]
 for i,(title,summary,url,tag,source) in enumerate(rows,1):
  ident=f'{cat}-{i}'; t=escape(title); s=escape(summary); u=escape(url,quote=True)
  chunks.append(f'''<a class="card-link" onclick="openDetail('{ident}'); return false;" href="#"><div class="news-card"><span class="tag {c}">{escape(tag)}</span><div class="emoji-icon">📰</div><h3>{t}</h3><p class="card-summary">{s}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{ident}"><div class="detail-meta"><span>📅 {D}</span><span>📰 {source}</span><span class="tag {c}">{escape(tag)}</span></div><div class="detail-visual"></div><h2>{t}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{s}</strong></div><div class="keypoint-card"><span>影响</span><strong>{escape(tag)}领域出现新的关注点</strong></div><div class="keypoint-card"><span>数据</span><strong>具体数据以原文披露为准</strong></div><div class="keypoint-card"><span>后续</span><strong>关注后续公开信息与实际推进</strong></div></div><p>{s}</p><p>这条消息反映出相关领域的最新变化，后续影响仍需结合更多公开信息观察。</p><a class="external-btn" href="{u}" target="_blank" rel="noopener">阅读原文</a></template>''')
 (out/f'{cat}.html').write_text('\n'.join(chunks)+'\n',encoding='utf-8')
print('wrote',sum(len(x) for x in items.values()))
