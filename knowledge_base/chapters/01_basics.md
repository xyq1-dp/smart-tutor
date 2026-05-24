# 第 1 章：Python 基础语法

## 1.1 Python 语言简介

Python 由 Guido van Rossum 于 1991 年发布，是一种**解释型、面向对象**的
高级编程语言。设计哲学强调代码的可读性和简洁的语法。

**Python 的特点**：
- 语法简洁，接近自然语言，适合初学者
- 丰富的标准库和第三方库（超过 30 万个包）
- 跨平台（Windows / macOS / Linux）
- 应用领域广泛：Web 开发、数据科学、AI、自动化运维

**环境搭建**：
- 访问 python.org 下载最新版 Python（推荐 3.10+）
- 安装时勾选 "Add Python to PATH"
- 验证安装：终端输入 `python --version`

---

## 1.2 变量与基本数据类型

### 变量
Python 是动态类型语言，变量不需要声明类型：

```python
name = "张三"      # 字符串
age = 20           # 整数
score = 95.5       # 浮点数
is_passed = True   # 布尔值
```

### 基本数据类型

| 类型 | 示例 | 说明 |
|------|------|------|
| `int` | `42`, `-10`, `0` | 整数 |
| `float` | `3.14`, `-0.5`, `1.0` | 浮点数 |
| `str` | `"hello"`, `'你好'` | 字符串 |
| `bool` | `True`, `False` | 布尔值 |
| `NoneType` | `None` | 空值 |

### 类型检查
```python
print(type(42))      # <class 'int'>
print(type(3.14))    # <class 'float'>
print(type("hello")) # <class 'str'>
```

---

## 1.3 输入与输出

### print() — 输出
```python
print("Hello, World!")
print("姓名：", name, "年龄：", age)  # 逗号自动加空格
print(f"姓名：{name}，年龄：{age}")   # f-string 格式化（推荐）
```

### input() — 输入
```python
name = input("请输入你的名字：")  # 返回值始终是字符串
age = int(input("请输入你的年龄："))  # 需要转整数
```

---

## 1.4 运算符与表达式

### 算术运算符
```python
a + b      # 加法
a - b      # 减法
a * b      # 乘法
a / b      # 除法（返回 float）
a // b     # 整除（向下取整）
a % b      # 取余
a ** b     # 幂运算
```

### 比较运算符
```python
a == b     # 等于
a != b     # 不等于
a > b      # 大于
a < b      # 小于
a >= b     # 大于等于
a <= b     # 小于等于
```

### 逻辑运算符
```python
and        # 与：全真才真
or         # 或：有真即真
not        # 非：取反
```

---

## 1.5 字符串基本操作

```python
s = "Hello, Python"

# 索引（从 0 开始）
s[0]       # 'H'
s[-1]      # 'n' （负索引从末尾算）

# 切片 [起始:结束:步长]
s[0:5]     # 'Hello'
s[7:]      # 'Python'
s[::-1]    # 'nohtyP ,olleH' （反转）

# 常用方法
s.upper()       # 全大写
s.lower()       # 全小写
s.replace("Python", "World")  # 替换
s.split(",")    # 分割成列表
len(s)          # 字符串长度
s.strip()       # 去除首尾空格
```

---

## 1.6 类型转换

```python
int("42")      # 字符串 → 整数：42
float("3.14")  # 字符串 → 浮点数：3.14
str(100)       # 数字 → 字符串："100"
bool(0)        # → False
bool("hello")  # → True
```

---

## 本章常见错误

| 错误类型 | 示例 | 原因 |
|---------|------|------|
| `NameError` | 使用未定义的变量 | 变量名写错或未赋值 |
| `TypeError` | `"3" + 5` | 类型不匹配 |
| `SyntaxError` | 少写括号或引号 | 语法格式错误 |
| `IndentationError` | 缩进不正确 | Python 用缩进区分代码块 |

---

## 本章练习
1. 写一个程序，输入姓名和年龄，输出 "你好 XXX，你今年 XX 岁"
2. 输入两个数字，计算它们的和、差、积、商
3. 输入一个字符串，判断它是否是回文（正着读反着读一样）
4. 输入一个 3 位数，输出它每个位上的数字之和
