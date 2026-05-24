# 第 3 章：函数与模块

## 3.1 函数定义与调用

```python
# 定义函数
def greet(name):
    """向指定的人打招呼（这是文档字符串 docstring）"""
    print(f"你好，{name}！")

# 调用函数
greet("张三")  # 输出：你好，张三！
greet("李四")  # 输出：你好，李四！
```

**函数的好处**：
- 代码复用：避免重复写相同的代码
- 模块化：把复杂问题拆成小函数，每个函数做一件事
- 可读性：好的函数名本身就是注释

---

## 3.2 参数传递

### 位置参数（必须按顺序传）
```python
def describe(name, age, city):
    print(f"{name} 今年 {age} 岁，来自 {city}")

describe("张三", 20, "北京")
```

### 默认参数
```python
def describe(name, age, city="未知"):
    print(f"{name} 今年 {age} 岁，来自 {city}")

describe("张三", 20)  # city 使用默认值
```

### 关键字参数（按名称传参，不需要记顺序）
```python
describe(age=20, name="张三", city="北京")
```

### 可变参数：*args 和 **kwargs
```python
# *args：接收任意数量位置参数 → 元组
def sum_all(*numbers):
    return sum(numbers)

print(sum_all(1, 2, 3, 4, 5))  # 15

# **kwargs：接收任意数量关键字参数 → 字典
def print_info(**info):
    for key, value in info.items():
        print(f"{key}: {value}")

print_info(name="张三", age=20, city="北京")
```

---

## 3.3 返回值

```python
def add(a, b):
    return a + b

result = add(3, 5)  # result = 8
```

- `return` 后面的代码不会执行
- 没有 `return` 的函数返回 `None`
- 可以返回多个值（实际是返回元组）

```python
def divide(a, b):
    if b == 0:
        return None, "除数不能为零"
    return a / b, "计算成功"

result, msg = divide(10, 2)  # 5.0, "计算成功"
```

---

## 3.4 变量的作用域

```python
x = 10  # 全局变量

def foo():
    y = 20  # 局部变量
    print(x)  # 可以读取全局变量
    # x = 30  # 这会创建局部变量 x，覆盖全局变量！

def bar():
    global x  # 声明要修改全局变量
    x = 30

foo()  # 输出 10
bar()
print(x)  # 输出 30
```

**LEGB 规则**（变量查找顺序）：
Local → Enclosing → Global → Built-in

---

## 3.5 模块的导入与使用

```python
# 导入整个模块
import math
print(math.sqrt(16))  # 4.0

# 导入特定函数
from math import sqrt, pi
print(sqrt(16), pi)  # 不需要写 math.

# 导入所有内容（不推荐）
from math import *

# 给模块起别名
import numpy as np
```

### 创建自己的模块

**文件 `my_utils.py`**：
```python
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
```

**使用**：
```python
import my_utils
print(my_utils.add(3, 5))
```

---

## 3.6 常用内置函数

| 函数 | 作用 | 示例 |
|------|------|------|
| `len()` | 获取长度 | `len("hello")` → 5 |
| `range()` | 生成整数序列 | `range(5)` → 0,1,2,3,4 |
| `type()` | 查看类型 | `type(42)` → int |
| `max()` / `min()` | 最大值/最小值 | `max(1,2,3)` → 3 |
| `sum()` | 求和 | `sum([1,2,3])` → 6 |
| `sorted()` | 排序 | `sorted([3,1,2])` → [1,2,3] |
| `abs()` | 绝对值 | `abs(-5)` → 5 |
| `enumerate()` | 带索引遍历 | `enumerate(["a","b"])` |
| `zip()` | 并行遍历 | `zip([1,2],["a","b"])` |
| `map()` / `filter()` | 函数式编程 | `map(str, [1,2,3])` |

---

## 3.7 Lambda 表达式

```python
# 普通函数
def add(a, b):
    return a + b

# Lambda 写法（匿名函数）
add = lambda a, b: a + b

# 常用于排序、过滤等
students = [("张三", 85), ("李四", 92), ("王五", 78)]
students.sort(key=lambda s: s[1], reverse=True)  # 按分数降序

# 与 map/filter 配合
numbers = [1, 2, 3, 4, 5]
squares = list(map(lambda x: x**2, numbers))  # [1, 4, 9, 16, 25]
evens = list(filter(lambda x: x % 2 == 0, numbers))  # [2, 4]
```

---

## 本章常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `UnboundLocalError` | 在函数内给全局变量赋值 | 使用 `global` 关键字 |
| `TypeError: missing argument` | 缺少必需参数 | 检查函数签名 |
| `RecursionError` | 递归无终止条件 | 确保有 base case |
| `ModuleNotFoundError` | 模块未安装或路径错误 | 检查安装和导入路径 |

---

## 本章练习
1. 写一个函数 `is_palindrome(s)` 判断字符串是否回文
2. 写一个函数 `fibonacci(n)` 返回第 n 个斐波那契数
3. 写一个计算器模块 `calculator.py`，包含加减乘除四个函数
4. 用 lambda 和 filter 找出列表中所有的偶数
