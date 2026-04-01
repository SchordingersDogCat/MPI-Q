class PCOLOR():
    '''
# 字体颜色
RED_BOLD = "\033[1;31m"      # 加粗红色
GREEN_BOLD = "\033[1;32m"    # 加粗绿色
YELLOW_BOLD = "\033[1;33m"   # 加粗黄色
BLUE_BOLD = "\033[1;34m"     # 加粗蓝色
MAGENTA_BOLD = "\033[1;35m"  # 加粗洋红色
CYAN_BOLD = "\033[1;36m"     # 加粗青色
WHITE_BOLD = "\033[1;37m"    # 加粗白色
BLACK_BOLD = "\033[1;30m"    # 加粗黑色
# 背景颜色
BG_RED = "\033[41m"      # 红色背景
BG_GREEN = "\033[42m"    # 绿色背景
BG_YELLOW = "\033[43m"   # 黄色背景
BG_BLUE = "\033[44m"     # 蓝色背景
BG_MAGENTA = "\033[45m"  # 洋红色背景
BG_CYAN = "\033[46m"     # 青色背景
BG_WHITE = "\033[47m"    # 白色背景
BG_BLACK = "\033[40m"    # 黑色背景
'''
    # 定义样式
    def __init__(self):
        self.RED_BOLD = "\033[1;31m"      # 加粗红色
        self.GREEN_BOLD = "\033[1;32m"    # 加粗绿色
        self.YELLOW_BOLD = "\033[1;33m"   # 加粗黄色
        self.BLUE_BOLD = "\033[1;34m"     # 加粗蓝色
        self.MAGENTA_BOLD = "\033[1;35m"  # 加粗洋红色
        self.CYAN_BOLD = "\033[1;36m"     # 加粗青色
        self.WHITE_BOLD = "\033[1;37m"    # 加粗白色
        self.BLACK_BOLD = "\033[1;30m"    # 加粗黑色
        self.RESET = "\033[0m"            # 重置样式