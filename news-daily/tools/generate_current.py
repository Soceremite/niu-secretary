from pathlib import Path
from html import escape
from datetime import datetime
import json
D='2026-09-06'
items={
'domestic':[
('“川味”出圈 “电影+”让传统文化“活”起来','https://news.china.com/domestic/945/20260906/49721897.html','文化产业','报道关注影视与地方文化结合，展示传统文化借助电影内容获得新表达和传播空间。'),
('我国商业航天迸发新动能','https://news.china.com/domestic/945/20260906/49721885.html','商业航天','报道聚焦我国商业航天发展动能，产业化和市场化探索继续推进。'),
('台风“科罗旺”影响我国多地沿海区域','https://news.china.com/domestic/945/20260906/49721873.html','防灾减灾','台风“科罗旺”影响我国多地沿海区域，相关地区需关注风雨和强对流天气变化。')],
'international':[
('调查报告显示日本尼得科公司存在大规模造假行为','https://news.china.com/international/1000/20260906/49722012.html','企业治理','调查报告指向日本尼得科公司存在大规模造假行为，企业治理和信息披露再次受到关注。'),
('五角大楼“史无前例”对美军高官启动测谎测试','https://news.china.com/international/1000/20260906/49722003.html','美国国防','美国国防部门据报道对高级军官启动测谎测试，相关做法及其背景引发关注。'),
('美再次威胁打击伊核设施 但对升级冲突仍存顾忌','https://news.china.com/international/1000/20260906/49721994.html','中东局势','美国再次发出打击伊核设施的威胁，但报道同时指出其对冲突升级仍有顾忌。'),
('英国外交大臣：加沙当前局势“骇人听闻”','https://news.china.com/international/1000/20260906/49721984.html','地区冲突','英国外交大臣评价加沙局势严峻，中东人道和安全局势仍在持续受到国际关注。'),
('尼泊尔泥石流灾害中1名受困中国公民获救','https://news.china.com/international/1000/20260906/49721975.html','领事保护','尼泊尔泥石流灾害中，一名受困中国公民获救，救援和后续安置工作受到关注。')],
'finance':[
('美伊互袭油轮 伊朗军方称或对美进行更大规模打击','https://finance.eastmoney.com/a/202609063866050824.html','国际市场','美伊互袭油轮消息冲击能源和风险资产预期，伊朗军方释放进一步回应信号。'),
('俄总统助理：普京与美总统特使会见超3小时','https://finance.eastmoney.com/a/202609063866050059.html','地缘经济','普京与美国总统特使会见超过三小时，俄美关系及其对市场的潜在影响受到关注。'),
('减仓泛科技 加仓低位赛道！百亿私募持仓再平衡 AI投资现分歧','https://finance.eastmoney.com/a/202609063866051598.html','投资策略','百亿私募持仓出现再平衡，泛科技与低位赛道之间的配置分歧浮现。'),
('经济日报：为什么说存储周期不会消失','https://finance.eastmoney.com/a/202609063866047327.html','产业周期','评论围绕存储产业周期展开分析，产业需求、供给和技术迭代仍是市场关注重点。'),
('“大缓和”时代终结！全球范式重构 A股迎来重估时刻！底层逻辑何在？','https://finance.eastmoney.com/a/202609063866053086.html','资本市场','市场讨论全球范式变化对A股估值和资产定价逻辑的影响，风险偏好仍受外部环境牵动。')],
'tech':[
('TCL 华星展示全球首款 IJP OLED 可折叠便携显示器：三折叠设计，16~28英寸变化','https://www.ithome.com/0/998/885.htm','显示技术','TCL华星展示三折叠IJP OLED便携显示器，屏幕尺寸可在16至28英寸之间变化。'),
('晶存科技发布 96GB 9600MT/s 规格 LPDDR5X LPCAMM2 内存模组','https://www.ithome.com/0/998/883.htm','存储硬件','晶存科技发布高容量、高速率LPDDR5X LPCAMM2内存模组，面向新一代移动和计算设备。'),
('欧洲商业航天取得突破：德国伊萨尔“光谱”运载火箭首次成功入轨','https://www.ithome.com/0/998/882.htm','商业航天','德国伊萨尔“光谱”运载火箭首次成功入轨，欧洲商业航天竞争出现新进展。'),
('OpenAI 将建立全新框架，承诺未来将更加透明地披露 AI 智能体失控情况','https://www.ithome.com/0/998/859.htm','人工智能治理','OpenAI据报道将建立新框架，承诺更透明地披露AI智能体失控情况，安全治理成为焦点。'),
('联通反诈大模型揪出涉诈 VOIP 黑盒','https://www.ithome.com/0/998/877.htm','网络安全','中国联通反诈大模型用于识别涉诈VOIP黑盒，报道提醒公众警惕可疑人员上门“维修网络”。')],
'ai':[
('微软发布 MAI-Image-2.6-Flash：生图速度是全球最佳 AI 模型的 2 倍','https://www.ithome.com/0/998/747.htm','生成式AI','微软发布自研图像生成模型MAI-Image-2.6-Flash，并通过Microsoft Foundry开放公开预览。'),
('微软预告 Excel 新增 AI 画布，打造可视化交互式数据看板','https://www.ithome.com/0/998/693.htm','AI办公','微软计划为Excel推出Copilot Canvas，把图表、指标和分析洞察整合为可交互视图。'),
('美国加州登山者轻信谷歌 Gemini 路线信息，最终被困山上','https://www.ithome.com/0/998/684.htm','AI安全','报道显示AI给出的登山路线和耗时存在严重偏差，事件凸显AI在高风险场景中的局限。'),
('奥尔特曼致歉“GPT-6 Astra AI 上线混乱”，现已面向所有 Plus / Pro 等用户推出','https://www.ithome.com/0/998/661.htm','模型发布','奥尔特曼就GPT-6 Astra上线过程致歉，并称该模型已面向更多付费用户推出。'),
('谷歌最强音乐 AI Lyria 3.5 塞进 Gemini：一键生成 3 分钟完整歌曲','https://www.ithome.com/0/998/647.htm','AI创作','谷歌宣布在Gemini应用和API中上线Lyria 3.5，可生成最长三分钟的完整歌曲。')]
}
meta={'domestic':('国内','国内要闻','tag-green','中华网'),'international':('国际','国际焦点','tag-red','中华网'),'finance':('财经','财经快讯','tag-purple','东方财富网'),'tech':('科技','科技动态','tag-blue','IT之家'),'ai':('AI','人工智能','tag-orange','IT之家')}
root=Path(__file__).resolve().parent.parent; out=root/'dist/sections'; out.mkdir(parents=True,exist_ok=True)
for cat,rows in items.items():
 sec,name,color,source=meta[cat]; chunks=[]
 for n,(title,url,tag,summary) in enumerate(rows,1):
  oid=f'{cat}-{n}'; te=escape(title); se=escape(summary); ue=escape(url,quote=True)
  chunks.append(f'''<a class="card-link" onclick="openDetail('{oid}'); return false;" href="#"><div class="news-card"><span class="tag {color}">{escape(tag)}</span><div class="emoji-icon">📰</div><h3>{te}</h3><p class="card-summary">{se}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{oid}"><div class="detail-meta"><span>📅 {D}</span><span>📰 {source}</span><span class="tag {color}">{escape(tag)}</span></div><div class="detail-visual"></div><h2>{te}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{se}</strong></div><div class="keypoint-card"><span>影响</span><strong>{escape(tag)}领域出现新的值得关注变化</strong></div><div class="keypoint-card"><span>数据</span><strong>原文标题与摘要披露了相关进展</strong></div><div class="keypoint-card"><span>后续</span><strong>后续影响取决于实际推进和公开信息</strong></div></div><p>{se}</p><p>这条消息反映出当前{sec}领域的最新动向，后续进展仍值得持续关注。</p><a class="external-btn" href="{ue}" target="_blank" rel="noopener">阅读原文</a></template>''')
 (out/f'{cat}.html').write_text('\n'.join(chunks),encoding='utf-8')
print('generated',sum(len(v) for v in items.values()),'items')
