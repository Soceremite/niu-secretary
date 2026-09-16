from pathlib import Path
from html import escape

items = {
'domestic': [
 ('“平陆运河战队”何以能成（前沿观察）','https://news.china.com/domestic/945/20260915/49741539.html','平陆运河建设与通航准备持续推进，工程组织和协同保障成为观察重点。','前沿观察'),
 ('万米高空，“网上冲浪”咋实现','https://news.china.com/domestic/945/20260915/49741527.html','万米高空通信服务如何实现连接，相关技术保障和应用场景受到关注。','通信服务'),
 ('2026年国家网络安全宣传周开幕式在山东济南举行','https://news.china.com/domestic/945/20260915/49741515.html','国家网络安全宣传周开幕式在济南举行，网络安全宣传与治理议题再次受到关注。','网络安全'),
],
'international': [
 ('韩国民众对美好感度为何急转直下？','https://news.china.com/international/1000/20260915/49741610.html','韩国民众对美国的观感变化成为舆论观察点，背后涉及双边关系与社会情绪。','国际关系'),
 ('抵制美国货，加拿大超市货架大洗牌','https://news.china.com/international/1000/20260915/49741598.html','加拿大市场出现抵制美国货相关变化，消费选择与贸易关系的互动值得观察。','贸易与消费'),
 ('中瑞自贸协定升级，意义为何不一般','https://news.china.com/international/1000/20260915/49741566.html','中瑞自贸协定升级释放经贸合作信号，双方贸易便利化与产业合作空间受到关注。','经贸合作'),
],
'finance': [
 ('特朗普称愿与伊朗谈判 提出美方要收“护航补偿”','https://finance.eastmoney.com/a/202609153873817559.html','美国与伊朗谈判及航运安排相关表态，可能影响能源、航运与风险资产预期。','全球市场'),
 ('电子信息制造业发展“十五五”规划发布','https://finance.eastmoney.com/a/202609153874146570.html','电子信息制造业发展规划发布，产业升级、技术创新和供应链布局成为市场关注焦点。','产业政策'),
 ('国家统计局：8月份各线城市商品住宅销售价格同比降幅继续收窄','https://finance.eastmoney.com/a/202609153874278588.html','国家统计局公布房地产价格信息，各线城市商品住宅销售价格同比降幅继续收窄。','房地产'),
],
' tech': [
 ('5999 元起华为 Pura X View 阔直板手机正式上市：16:9.5 比例面板、麒麟 9030S 处理器','https://www.ithome.com/0/999/348.htm','华为 Pura X View 正式上市，阔直板形态与麒麟 9030S 处理器成为产品看点。','手机硬件'),
 ('华为史上最强处理器！麒麟 9050 Pro 官宣，Mate XT 2 非凡大师全新展翼三折叠手机首发搭载','https://www.ithome.com/0/999/294.htm','麒麟 9050 Pro 与 Mate XT 2 三折叠手机的组合亮相，国产芯片和高端终端协同推进。','国产芯片'),
 ('小米 18 Fold 中折叠手机发布：首发玄戒 O3 芯片，10999 元起','https://www.ithome.com/0/999/441.htm','小米发布中折叠手机并首发玄戒 O3 芯片，折叠屏高端市场竞争继续升温。','折叠屏'),
],
'ai': [
 ('曝 Glass Imaging 被 OpenAI 收购：前苹果员工创办，其影像技术已用于荣耀手机','https://www.ithome.com/1/002/359.htm','报道称 OpenAI 收购 Glass Imaging，这家由前苹果员工创办的公司曾提供用于荣耀手机的影像技术。','AI产业'),
 ('OpenAI 联合创始人布罗克曼：人类已迈入通用人工智能时代','https://www.ithome.com/1/002/341.htm','OpenAI 联合创始人布罗克曼发表对通用人工智能阶段的判断，行业发展边界再次引发讨论。','大模型'),
 ('德国称暂停 AI 开发对欧洲而言不可行，呼吁中美参与 AI 治理','https://www.ithome.com/1/002/301.htm','德国方面表示暂停 AI 开发对欧洲不可行，并呼吁中美参与人工智能治理。','AI治理'),
],
}
items['tech'] = items.pop(' tech')
colors={'domestic':'tag-green','international':'tag-red','finance':'tag-purple','tech':'tag-blue','ai':'tag-orange'}
emojis={'domestic':'🏛️','international':'🌍','finance':'📈','tech':'📱','ai':'🤖'}
for cat, arr in items.items():
 out=[]
 for i,(title,url,summary,tag) in enumerate(arr,1):
  t=escape(title); s=escape(summary); u=escape(url, quote=True); c=colors[cat]
  out.append(f'''<a class="card-link" onclick="openDetail('{cat}-{i}'); return false;" href="#"><div class="news-card"><span class="tag {c}">{tag}</span><div class="emoji-icon">{emojis[cat]}</div><h3>{t}</h3><p class="card-summary">{s}</p><div class="expand-hint">点击查看详情 →</div></div></a>
<template id="detail-{cat}-{i}"><div class="detail-meta"><span>📅 2026-09-15</span><span>📰 {'东方财富网' if cat=='finance' else ('IT之家' if cat in ('tech','ai') else '中国网')}</span><span class="tag {c}">{tag}</span></div><div class="detail-visual"></div><h2>{t}</h2><div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{s}</strong></div><div class="keypoint-card"><span>影响</span><strong>相关进展将影响行业预期与公众关注。</strong></div><div class="keypoint-card"><span>数据</span><strong>具体数字以原文披露为准。</strong></div><div class="keypoint-card"><span>后续</span><strong>继续关注官方信息和后续进展。</strong></div></div><p>{s}</p><p>本文信息来自公开报道，关键细节请以原文为准。</p><a class="external-btn" href="{u}" target="_blank" rel="noopener">阅读原文</a></template>''')
 Path('dist/sections',).mkdir(parents=True,exist_ok=True)
 Path(f'dist/sections/{cat}.html').write_text('\n'.join(out),encoding='utf-8')
print({k:len(v) for k,v in items.items()})
