"""
浏览器智能体的提示词

定义系统提示词和路由关键词，用于浏览器自动化任务。
"""

SYSTEM_PROMPT = """你是一个专业的浏览器自动化助手，可以帮助用户在浏览器中完成各种任务。

## 你的能力
1. **网页导航** - 访问指定网站、搜索内容
2. **信息提取** - 从网页中提取文本、链接、图片等信息
3. **表单操作** - 填写表单、点击按钮、选择选项
4. **数据采集** - 批量获取网页数据
5. **自动化流程** - 执行多步骤的自动化任务

## 工作原则
1. **安全第一** - 不执行可能造成损害的操作
2. **隐私保护** - 不收集或泄露用户敏感信息
3. **透明操作** - 每一步操作都会告知用户
4. **错误处理** - 遇到问题时会尝试恢复或告知用户

## 任务执行流程
1. 理解用户的任务需求
2. 规划执行步骤
3. 逐步执行并反馈进度
4. 返回执行结果

## 注意事项
- 如果任务涉及登录，请确保用户已授权
- 对于复杂任务，会分步骤执行并汇报进度
- 如果遇到验证码或人机验证，会提示用户手动处理
"""

# 用于路由判断的关键词
ROUTING_KEYWORDS = [
    # 浏览器操作
    "浏览器", "打开网页", "访问网站", "打开网站", "上网",
    "browser", "open", "visit", "navigate",
    
    # 搜索相关
    "搜索", "查找", "百度", "谷歌", "google", "bing", "search",
    
    # 数据采集
    "爬取", "抓取", "采集", "提取", "获取网页", "爬虫",
    "scrape", "crawl", "extract", "fetch",
    
    # 自动化操作
    "自动", "自动化", "自动填写", "自动点击", "自动登录",
    "automate", "automation", "auto",
    
    # 网页交互
    "点击", "填写", "输入", "提交", "下载",
    "click", "fill", "input", "submit", "download",
    
    # 具体网站
    "淘宝", "京东", "天猫", "amazon", "ebay",
]

# 任务类型映射
TASK_TYPE_KEYWORDS = {
    "search": ["搜索", "查找", "search", "find", "百度", "谷歌"],
    "scrape": ["爬取", "抓取", "采集", "提取", "scrape", "crawl", "extract"],
    "form": ["填写", "表单", "登录", "注册", "fill", "form", "login", "register"],
    "navigate": ["打开", "访问", "浏览", "open", "visit", "navigate", "go to"],
    "download": ["下载", "保存", "download", "save"],
}


def detect_task_type(description: str) -> str:
    """从描述中检测任务类型"""
    description_lower = description.lower()
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in description_lower:
                return task_type
    return "general"
