"""
视频作品信息生成器
为每个视频作品自动生成适合不同平台的标题、描述和标签
"""

import os
import json
from typing import Dict, List
from dataclasses import dataclass, asdict


@dataclass
class VideoMetadata:
    """视频元数据"""
    title: str
    description: str
    tags: List[str]
    hashtags: List[str]
    
    def to_dict(self):
        return asdict(self)


class MetadataGenerator:
    """元数据生成器"""
    
    def __init__(self):
        # 类目关键词映射
        self.category_keywords = {
            "儿童绘本": {
                "keywords": ["儿童故事", "童话", "绘本", "亲子", "早教", "睡前故事"],
                "hashtags": ["儿童绘本", "童话故事", "亲子时光", "育儿", "早教启蒙"]
            },
            "成语故事": {
                "keywords": ["成语故事", "成语", "传统文化", "国学", "语文学习", "历史典故"],
                "hashtags": ["成语故事", "成语", "国学", "传统文化", "中小学语文", "早教启蒙"]
            },
            "英语绘本": {
                "keywords": ["英语启蒙", "英文绘本", "双语", "英语学习", "磨耳朵"],
                "hashtags": ["英语启蒙", "英文绘本", "儿童英语", "双语教育", "英语学习"]
            },
            "历史故事": {
                "keywords": ["历史故事", "传统文化", "国学", "成语", "历史人物"],
                "hashtags": ["历史故事", "传统文化", "国学启蒙", "文化传承", "古代故事"]
            },
            "睡前故事": {
                "keywords": ["睡前故事", "哄睡", "晚安", "助眠", "冥想"],
                "hashtags": ["睡前故事", "哄睡神器", "晚安故事", "儿童助眠", "亲子陪伴"]
            }
        }
    
    def generate_for_douyin(self, topic: str, category: str, summary: str = None) -> VideoMetadata:
        """
        生成抖音平台的元数据
        
        Args:
            topic: 作品主题（如"三只小猪"）
            category: 类目（如"儿童绘本"）
            summary: 可选的内容摘要
        """
        # 标题: 简短有力，带emoji
        title = f"🎨【{category}】{topic} | 智绘童梦"
        
        # 描述: 吸引点击 + 引导互动
        cat_info = self.category_keywords.get(category, {})
        keywords = cat_info.get("keywords", [])
        
        description_parts = [
            f"✨ {topic}的故事来啦！",
            f"📚 {category}系列，每天陪伴孩子成长",
            "",
            "🌟 关注@智绘童梦，每天分享优质儿童内容",
            "💕 记得点赞+收藏，和孩子一起看故事",
            "",
        ]
        
        if summary:
            description_parts.insert(2, f"📖 {summary}")
            description_parts.insert(3, "")
        
        description = "\n".join(description_parts)
        
        # 标签
        tags = [topic, category] + keywords[:3]
        hashtags = ["#" + tag for tag in cat_info.get("hashtags", [])[:5]]
        
        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            hashtags=hashtags
        )
    
    def generate_for_xiaohongshu(self, topic: str, category: str, summary: str = None) -> VideoMetadata:
        """生成小红书平台的元数据"""
        # 标题: 适合笔记形式，加emoji和亮点
        emojis = {"儿童绘本": "📚", "英语绘本": "🌍", "历史故事": "🏛️", "睡前故事": "🌙"}
        emoji = emojis.get(category, "✨")
        
        title = f"{emoji} {topic} | {category}精选推荐"
        
        # 描述: 种草式文案，强调价值
        cat_info = self.category_keywords.get(category, {})
        
        description_parts = [
            f"🎬 今天分享一个超赞的{category}👇",
            f"",
            f"📖 主题：{topic}",
        ]
        
        if summary:
            description_parts.append(f"💡 内容：{summary}")
        
        description_parts.extend([
            "",
            "✅ 适合3-8岁宝宝",
            "✅ AI精美画面",
            "✅ 生动有趣",
            "✅ 寓教于乐",
            "",
            "🌟 关注@智绘童梦",
            "每天分享优质儿童内容",
            "",
            "💬 评论区告诉我你家宝宝喜欢什么故事～",
        ])
        
        description = "\n".join(description_parts)
        
        # 标签
        tags = [topic, category, "育儿好物", "亲子教育"] + cat_info.get("keywords", [])[:2]
        hashtags = ["#" + tag for tag in cat_info.get("hashtags", [])[:6]]
        
        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            hashtags=hashtags
        )
    
    def generate_for_youtube(self, topic: str, category: str, summary: str = None) -> VideoMetadata:
        """生成YouTube平台的元数据（双语）"""
        # 标题: 中英双语
        category_en = {
            "儿童绘本": "Children's Storybook",
            "英语绘本": "English Picture Book",
            "历史故事": "History Story",
            "睡前故事": "Bedtime Story"
        }
        
        title = f"{topic} | {category} - {category_en.get(category, 'Kids Story')} - SmartArt Kids 智绘童梦"
        
        # 描述: 详细专业，SEO友好
        cat_info = self.category_keywords.get(category, {})
        
        description_parts = [
            f"🎬 {topic}",
            f"📚 Category: {category} / {category_en.get(category, 'Kids Story')}",
            "",
        ]
        
        if summary:
            description_parts.append(f"📖 Story Summary:\n{summary}")
            description_parts.append("")
        
        description_parts.extend([
            "🌟 About SmartArt Kids (智绘童梦):",
            "We create AI-powered children's video content with:",
            "✅ Beautiful illustrations",
            "✅ Engaging narration",
            "✅ Educational value",
            "✅ Safe & appropriate for kids",
            "",
            "🔔 Subscribe for more stories!",
            "👍 Like if you enjoyed this video",
            "💬 Comment your favorite part",
            "",
            "🎵 Music: Royalty-free background music",
            "🎨 Images: AI-generated illustration",
            "",
            "© SmartArt Kids 智绘童梦",
            "AI-Driven Children's Video Creation Platform",
            "",
            "#" + " #".join(cat_info.get("hashtags", [])[:5])
        ])
        
        description = "\n".join(description_parts)
        
        # 标签
        tags = [
            topic,
            category,
            "智绘童梦",
            "SmartArt Kids",
            "kids story",
            "children's video",
            "educational content"
        ] + cat_info.get("keywords", [])[:3]
        
        hashtags = ["#" + tag for tag in cat_info.get("hashtags", [])[:8]]
        
        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            hashtags=hashtags
        )
    
    def generate_all_platforms(self, topic: str, category: str, summary: str = None) -> Dict[str, VideoMetadata]:
        """生成所有平台的元数据"""
        return {
            "douyin": self.generate_for_douyin(topic, category, summary),
            "xiaohongshu": self.generate_for_xiaohongshu(topic, category, summary),
            "youtube": self.generate_for_youtube(topic, category, summary)
        }
    
    def save_metadata(self, output_dir: str, topic: str, category: str, summary: str = None):
        """
        生成并保存所有平台的元数据到JSON文件
        
        Args:
            output_dir: 输出目录（视频所在文件夹）
            topic: 作品主题
            category: 类目
            summary: 内容摘要
        """
        metadata = self.generate_all_platforms(topic, category, summary)
        
        # 保存为JSON
        json_path = os.path.join(output_dir, "metadata.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json_data = {
                platform: meta.to_dict()
                for platform, meta in metadata.items()
            }
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 同时保存为可读的Markdown
        md_path = os.path.join(output_dir, "metadata.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {topic} - 作品发布信息\n\n")
            f.write(f"**类目**: {category}\n\n")
            if summary:
                f.write(f"**内容摘要**: {summary}\n\n")
            f.write("---\n\n")
            
            for platform, meta in metadata.items():
                platform_names = {
                    "douyin": "抖音",
                    "xiaohongshu": "小红书",
                    "youtube": "YouTube"
                }
                
                f.write(f"## {platform_names[platform]}\n\n")
                f.write(f"### 标题\n```\n{meta.title}\n```\n\n")
                f.write(f"### 描述\n```\n{meta.description}\n```\n\n")
                f.write(f"### 标签\n{', '.join(meta.tags[:10])}\n\n")
                f.write(f"### 话题标签\n{' '.join(meta.hashtags)}\n\n")
                f.write("---\n\n")
        
        return json_path, md_path


# 示例使用
if __name__ == "__main__":
    generator = MetadataGenerator()
    
    # 生成"三只小猪"的元数据
    topic = "三只小猪"
    category = "儿童绘本"
    summary = "三只小猪各自建房，勤劳的小猪用砖头建了坚固的房子，成功抵御了大灰狼的攻击。故事告诉孩子们勤劳和智慧的重要性。"
    
    output_dir = "products/儿童绘本/三只小猪"
    
    json_path, md_path = generator.save_metadata(output_dir, topic, category, summary)
    
    print(f"✅ 元数据已生成:")
    print(f"  - JSON: {json_path}")
    print(f"  - Markdown: {md_path}")
