"""
示例任务模板 - 给 0 基础用户"拿来即用"的现成任务

用法 (CLI 中):
  在"请描述任务"提示处直接输入模板序号 (如 2), 即可使用对应示例;
  也可以基于示例改写, 或完全自己描述。

模板覆盖常见场景, 提示词刻意写得口语化、具体,
让第一次使用的人一眼就懂"我能让它做什么"。
"""

TASK_TEMPLATES = [
    {
        "name": "看看桌面",
        "prompt": "查看云手机桌面上有什么文件或文件夹，列出所有内容，并简要说明每项是什么",
    },
    {
        "name": "打开抖音搜美食",
        "prompt": "打开抖音，搜索「美食」，看看有哪些热门视频，简单介绍前三个",
    },
    {
        "name": "看看附近有什么吃的",
        "prompt": "打开地图应用，搜索我附近的餐厅，列出距离最近的 3 家以及它们的评分",
    },
    {
        "name": "打开微信发消息",
        "prompt": "打开微信，给「文件传输助手」发一条消息：你好，这条消息来自云端手机",
    },
    {
        "name": "查一下今天天气",
        "prompt": "打开浏览器，查询今天北京的天气，告诉我温度和适不适合出门",
    },
]


def resolve_template(choice: str):
    """把用户的输入解析为任务提示词

    输入为 1~N 的序号时返回对应模板的提示词, 否则原样返回。
    (配合"输入序号用示例"的引导, 0 基础用户无需理解即可上手)

    Args:
        choice: 用户在"请描述任务"处输入的内容

    Returns:
        (提示词, 模板名或 None)
    """
    choice = (choice or "").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(TASK_TEMPLATES):
            tpl = TASK_TEMPLATES[idx - 1]
            return tpl["prompt"], tpl["name"]
    return choice, None


def format_template_menu(max_items: int = 5) -> str:
    """生成模板菜单文本 (用于任务输入前的引导)

    Args:
        max_items: 最多展示前几个模板

    Returns:
        多行文本, 如 "  1) 看看桌面  2) 打开抖音搜美食 ..."
    """
    lines = ["第一次不知道说什么？直接输入序号，用现成的例子："]
    row = []
    for i, tpl in enumerate(TASK_TEMPLATES[:max_items], start=1):
        row.append(f"{i}) {tpl['name']}")
    # 每行放 3 个, 避免单行过长
    for i in range(0, len(row), 3):
        lines.append("    " + "  ".join(row[i:i + 3]))
    return "\n".join(lines)
