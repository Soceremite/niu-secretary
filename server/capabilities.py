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
]


def capabilities_response():
    return {"version": API_VERSION, "capabilities": CAPABILITIES}


def get_capability(name):
    return next((item for item in CAPABILITIES if item["name"] == name), None)
