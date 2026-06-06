"""Capability registry for the Niu Secretary Action Protocol."""

API_VERSION = "2026-05-29"

CAPABILITIES = [
    {
        "name": "fitness.nutrition.create",
        "title": "记录一餐",
        "module": "fitness",
        "description": "写入塑形馆营养日志。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["food", "date"],
            "properties": {
                "food": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "calories": {"type": "number"},
                "proteinG": {"type": "number"},
                "carbsG": {"type": "number"},
                "fatG": {"type": "number"},
                "source": {"type": "string"},
            },
        },
    },
    {
        "name": "fitness.nutrition.today_summary",
        "title": "今日营养汇总",
        "module": "fitness",
        "description": "读取指定日期的营养合计。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": ["date"],
            "properties": {"date": {"type": "string", "format": "date"}},
        },
    },
    {
        "name": "fitness.nutrition.list",
        "title": "营养日志列表",
        "module": "fitness",
        "description": "按日期范围读取塑形馆营养日志。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {
                "from": {"type": "string", "format": "date"},
                "to": {"type": "string", "format": "date"},
                "limit": {"type": "number"},
            },
        },
    },
    {
        "name": "fitness.nutrition.delete",
        "title": "删除营养日志",
        "module": "fitness",
        "description": "删除指定营养日志。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
    },
    {
        "name": "fitness.nutrition.recognize_photo",
        "title": "餐食图片识别",
        "module": "fitness",
        "description": "识别餐食图片并返回可编辑营养估算。当前由塑形馆图片识别服务承载。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["photo"],
            "properties": {
                "photo": {"type": "file"},
                "description": {"type": "string"},
            },
        },
    },
    {
        "name": "schedule.event.create",
        "title": "创建日程",
        "module": "schedule",
        "description": "写入时务局日程事件。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["title", "date"],
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "time": {"type": "string"},
                "note": {"type": "string"},
                "source": {"type": "string"},
            },
        },
    },
    {
        "name": "schedule.todo.create",
        "title": "创建待办",
        "module": "schedule",
        "description": "写入时务局待办。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "priority": {"type": "string"},
                "source": {"type": "string"},
            },
        },
    },
    {
        "name": "schedule.event.list",
        "title": "日程列表",
        "module": "schedule",
        "description": "按日期范围读取时务局日程。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {
                "from": {"type": "string", "format": "date"},
                "to": {"type": "string", "format": "date"},
                "limit": {"type": "number"},
            },
        },
    },
    {
        "name": "schedule.event.delete",
        "title": "删除日程",
        "module": "schedule",
        "description": "删除指定日程事件。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
    },
    {
        "name": "schedule.todo.list",
        "title": "待办列表",
        "module": "schedule",
        "description": "读取时务局待办，可按日期范围与完成状态过滤。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {
                "from": {"type": "string", "format": "date"},
                "to": {"type": "string", "format": "date"},
                "includeDone": {"type": "boolean"},
                "limit": {"type": "number"},
            },
        },
    },
    {
        "name": "schedule.todo.toggle",
        "title": "切换待办完成",
        "module": "schedule",
        "description": "标记待办完成或未完成。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "done": {"type": "boolean"},
            },
        },
    },
    {
        "name": "schedule.todo.delete",
        "title": "删除待办",
        "module": "schedule",
        "description": "删除指定待办。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
    },
    {
        "name": "schedule.today_summary",
        "title": "今日日程汇总",
        "module": "schedule",
        "description": "读取指定日期的日程和待办。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": ["date"],
            "properties": {"date": {"type": "string", "format": "date"}},
        },
    },
    {
        "name": "profile.get",
        "title": "读取用户画像",
        "module": "profile",
        "description": "读取某板块用户画像；不传 module 则返回全部。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {
                "module": {"type": "string"},
            },
        },
    },
    {
        "name": "profile.update",
        "title": "更新用户画像",
        "module": "profile",
        "description": "合并更新某板块画像字段（patch 语义），并记录变更历史。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["module", "patch"],
            "properties": {
                "module": {"type": "string"},
                "patch": {"type": "object"},
                "summary": {"type": "string"},
                "source": {"type": "string"},
            },
        },
    },
    {
        "name": "profile.reset",
        "title": "重置用户画像",
        "module": "profile",
        "description": "将某板块画像重置为默认值。",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["module"],
            "properties": {"module": {"type": "string"}},
        },
    },
    {
        "name": "profile.changes",
        "title": "画像变更历史",
        "module": "profile",
        "description": "读取画像变更历史，可按板块过滤。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {
                "module": {"type": "string"},
                "limit": {"type": "number"},
            },
        },
    },
    {
        "name": "fitness.recommend",
        "title": "塑形馆个性化推荐",
        "module": "fitness",
        "description": "根据塑形馆画像生成今日饮食/训练建议。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {"date": {"type": "string", "format": "date"}},
        },
    },
    {
        "name": "schedule.recommend",
        "title": "时务局个性化推荐",
        "module": "schedule",
        "description": "根据时务局画像生成今日时间安排与提醒建议。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {"date": {"type": "string", "format": "date"}},
        },
    },
    {
        "name": "news.recommend",
        "title": "新闻社个性化推荐",
        "module": "news",
        "description": "根据新闻社画像，从今日新闻中筛选并排序你关注的话题。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {"limit": {"type": "number"}},
        },
    },
    {
        "name": "leisure.recommend",
        "title": "闲趣集个性化推荐",
        "module": "leisure",
        "description": "根据闲趣集画像，从影视/音乐/播客/小说库中筛选并排序推荐。",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": [],
            "properties": {"limit": {"type": "number"}},
        },
    },
]


def capabilities_response():
    return {"version": API_VERSION, "capabilities": CAPABILITIES}


def get_capability(name):
    return next((item for item in CAPABILITIES if item["name"] == name), None)
