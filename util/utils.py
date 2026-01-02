import re


def num_to_cn(num: str) -> str:
    """
    将阿拉伯数字（字符串）转为常见中文数字（支持 0-99），若本身已是中文数字则原样返回。
    """
    if not num:
        return ""
    if not num.isdigit():
        return num
    n = int(num)
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n < 20:
        return "十" if n == 10 else f"十{digits[n % 10]}"
    if n < 100:
        tens = digits[n // 10]
        ones = n % 10
        return f"{tens}十" if ones == 0 else f"{tens}十{digits[ones]}"
    return num


def extract_chapter_info(text: str) -> tuple[str, str, str]:
    """
    从文本中提取章节信息。
    返回：(章节号, 章节标题, 原始章节串)；提取不到则返回 ("", "", "")。
    """
    if not text:
        return "", "", ""
    # 支持：第一章 / 第1章
    m = re.search(r"(第(?P<num>[一二三四五六七八九十\d]+)章)\s*(?P<title>.+)?", text)
    if not m:
        return "", "", ""
    num = (m.group("num") or "").strip()
    title = (m.group("title") or "").strip()
    raw = (m.group(1) or "").strip()
    if title:
        raw = f"{raw} {title}"
    return num, title, raw


def extract_cover_title_from_topic(topic: str) -> str:
    """
    从 topic（内容主题）中尽量提取适合作为封面的大标题（通常是书名/主标题）。
    示例：'小狗钱钱第一版 第一章 ...' -> '小狗钱钱'
    """
    if not topic:
        return ""
    t = topic.strip()
    # 优先：如果存在“第X章”，取其前缀作为“书名/主标题”候选
    m_ch = re.search(r"第[一二三四五六七八九十\d]+章", t)
    prefix = t[: m_ch.start()].strip() if m_ch else t
    # 去掉“第X版”等版本信息（常见写法：第一版 / 第1版）
    prefix = re.sub(r"第[一二三四五六七八九十\d]+版\s*$", "", prefix).strip()
    return prefix or t


def format_cover_subtitle_from_chapter(num: str, chapter_title: str) -> str:
    """
    将“第一章 一只白色的拉布拉多犬”中的章节号与标题格式化为封面小标题：
    例如：num='一', title='一只白色的拉布拉多犬' -> '一、白色拉布拉多犬'
    """
    if not num and not chapter_title:
        return ""
    cn_num = num_to_cn(num)
    title = (chapter_title or "").strip()
    # 清理常见量词/开头（尽量温和，避免过拟合）
    for prefix in (
        "一只",
        "一条",
        "一頭",
        "一头",
        "一个",
        "一個",
        "一位",
        "一名",
        "一匹",
        "一群",
    ):
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
            break
    # 很短的章节标题里，“的”通常可去掉以更像封面小标题
    if title and len(title) <= 14:
        title = title.replace("的", "")
    return f"{cn_num}、{title}" if title else f"{cn_num}、"
