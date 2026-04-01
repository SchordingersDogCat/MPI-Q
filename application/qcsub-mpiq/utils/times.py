# utils/timer.py

import os
import time
from functools import wraps
from .print_utils import PCOLOR

pcolor = PCOLOR()


def timer_decorator_env(unit='s', verbose=True):
    """通过环境变量动态控制是否计时的装饰器
    
    Args:
        unit (str): 时间单位，可选 's' 或 'ms'
        verbose (bool): 是否打印耗时日志（默认为 True）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 读取环境变量控制开关（默认 True）
            if not os.getenv("ENABLE_TIMER"):
                return func(*args, **kwargs)
            else:
                enable = os.getenv("ENABLE_TIMER").lower()
                time_unit = os.getenv("TIME_UNIT").lower()
                if enable == 'false':
                    return func(*args, **kwargs)
                elif enable == 'true':
                    start = time.perf_counter()
                    result = func(*args, **kwargs)
                    elapsed = time.perf_counter() - start
                    
                    if time_unit == 'ms':
                        elapsed *= 1000
                        unit_str = 'ms'
                    elif time_unit == 's':
                        unit_str = 's'
                    
                    if verbose:
                        # 使用函数名 + 模块名确保唯一性
                        func_id = f"{func.__module__}.{func.__name__}"
                        print(f"{pcolor.RED_BOLD}#{pcolor.RESET}"*88)
                        print(f"{pcolor.RED_BOLD}[TIMER] {func_id} 耗时: {elapsed:.3f} {unit_str}{pcolor.RESET}")
                        print(f"{pcolor.RED_BOLD}#{pcolor.RESET}"*88)
            
            return result
        return wrapper
    return decorator
