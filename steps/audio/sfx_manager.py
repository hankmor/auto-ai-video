import os
import requests
from config.config import config
from util.logger import logger

class SFXManager:
    """
    """
    
    def __init__(self):
        self.sfx_dir = os.path.join(config.ASSETS_DIR, "sfx")
        os.makedirs(self.sfx_dir, exist_ok=True)
    
    def get_sfx(self, keyword: str) -> str:
        """
        返回给定关键词的 SFX 文件的本地路径。
        不再自动下载，而是生成占位符文件供用户替换。
        """
        if not keyword:
            return None
            
        keyword = keyword.lower().strip()
        filename = f"{keyword}.mp3"
        local_path = os.path.join(self.sfx_dir, filename)

        # 1. 检查本地是否存在
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        # 2. 如果不存在，创建占位符
        logger.warning(f"⚠️ SFX '{keyword}' not found locally.")
        self._create_placeholder(local_path)
        logger.warning(f"Created placeholder at: {local_path}")
        logger.warning(f"👉 Please replace '{filename}' with your own audio file.")
        
        return local_path

    def _create_placeholder(self, target_path: str):
        """
        创建一个有效的占位符 MP3 文件。
        尝试复制现有的 MP3，如果没有任何 MP3，则创建一个空的（可能会导致 ffmpeg 警告，但好过崩溃）。
        """
        # 尝试寻找目录里任何现存的 MP3 作为模板
        existing_files = [f for f in os.listdir(self.sfx_dir) if f.endswith(".mp3")]
        if existing_files:
            import shutil
            src = os.path.join(self.sfx_dir, existing_files[0])
            shutil.copy(src, target_path)
            logger.info(f"Copied placeholder from {existing_files[0]}")
        else:
            # 如果完全没有文件，写入一个极简的 MP3 Header 或者空文件
            # 为防止 ffmpeg 报错，写入一个 1kb 的空数据也不太好。
            # 这里简单创建一个空文件，但在实际合成时可能需要通过 Validation 这里的逻辑。
            # 更稳妥的是写入一个硬编码的静音帧，或者只创建一个文本说明。
            # 鉴于用户说"我来下载替换"，创建一个空文件作为标记即可。
            with open(target_path, "wb") as f:
                # 写入一些伪造的二进制数据以免被视为空文件
                f.write(b'ID3' + b'\x00'*10) 
            logger.info("Created empty placeholder file.")

