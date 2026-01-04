import functools

def interactive_retry(func):
    """
    装饰器：当函数抛出异常时，打印错误并询问用户是否重试。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"\n❌ 执行出错: {e}")
                user_input = input("是否重试? (y/n): ").strip().lower()
                if user_input != 'y':
                    print("已取消操作，返回主菜单。")
                    return None  # 或者根据需要抛出异常
    return wrapper