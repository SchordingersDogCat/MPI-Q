# my_package/__init__.py
from .supercomputing import superConfig  # 从同级模块导入

# 可选：将类添加到包的命名空间
__all__ = ['superConfig']  # 控制 from my_package import * 时导出的内容