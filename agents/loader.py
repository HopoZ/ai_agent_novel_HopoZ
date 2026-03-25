# 负责加载设定文件并构建创作百科全书的上下文信息

import os

class LoreLoader:
    def __init__(self, data_path="settings"):
        self.data_path = data_path

    def get_all_lore(self):
        """扫描目录并读取所有设定文件"""
        full_context = "### 创作百科全书 (Lorebook) ###\n"
        if not os.path.exists(self.data_path):
            return ""

        for file in os.listdir(self.data_path):
            if file.endswith(".md"):
                with open(os.path.join(self.data_path, file), "r", encoding="utf-8") as f:
                    # 获取文件名作为标签，例如 [怪物大全]
                    tag = file.replace(".md", "")
                    full_context += f"\n【{tag}】:\n{f.read()}\n"
        return full_context