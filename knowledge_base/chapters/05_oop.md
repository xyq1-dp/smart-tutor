# 第 5 章：面向对象编程

## 5.1 面向对象思想概述

面向对象编程（OOP）的核心思想是把**数据**和**操作数据的方法**封装在一起。

**三个基本概念**：
- **封装**：把数据和方法包在类里面，隐藏内部细节
- **继承**：子类复用父类的代码，减少重复
- **多态**：同一个方法名，不同类有不同行为

**什么时候用 OOP？**
- 代码中有明显"对象"概念（学生、商品、用户）
- 需要管理复杂的状态
- 多个地方用相似的数据结构

---

## 5.2 类的定义与对象的创建

```python
class Student:
    """学生类"""

    def __init__(self, name, age, major="计算机"):
        self.name = name      # 实例属性
        self.age = age
        self.major = major
        self.scores = []      # 默认值

    def add_score(self, score):
        """添加成绩"""
        self.scores.append(score)

    def average(self):
        """计算平均分"""
        if not self.scores:
            return 0
        return sum(self.scores) / len(self.scores)

# 创建对象（实例化）
s1 = Student("张三", 20)
s2 = Student("李四", 21, "数学")

s1.add_score(85)
s1.add_score(90)
print(s1.average())  # 87.5
```

**类 vs 实例**：
- 类是模板（设计图）
- 实例是按模板造出来的具体对象
- 每个实例有自己独立的属性值

---

## 5.3 `__init__` 构造方法

```python
class Book:
    def __init__(self, title, author, pages=0):
        """
        构造方法：创建对象时自动调用
        self 指向新创建的对象本身
        """
        self.title = title
        self.author = author
        self.pages = pages

b = Book("Python入门", "张三", 300)
# __init__ 被自动调用，b 就是 self
```

---

## 5.4 实例属性与方法

```python
class Counter:
    count = 0  # 类属性（所有实例共享）

    def __init__(self):
        Counter.count += 1  # 每创建一个实例，类属性 +1
        self.id = Counter.count  # 实例属性（每个实例独立）

    def report(self):
        """实例方法：需要 self，可访问实例和类"""
        print(f"我是 {self.id} 号计数器")

    @classmethod
    def total(cls):
        """类方法：不需要实例，只能访问类属性"""
        print(f"共有 {cls.count} 个计数器")

    @staticmethod
    def help():
        """静态方法：不需要 self 也不需要 cls"""
        print("这是个计数器类")
```

---

## 5.5 继承与多态

```python
# 父类（基类）
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "...（动物叫声）"

# 子类（派生类）
class Dog(Animal):
    def speak(self):  # 重写父类方法
        return "汪汪！"

class Cat(Animal):
    def speak(self):
        return "喵喵！"

# 多态：同一个方法名，不同行为
animals = [Dog("旺财"), Cat("咪咪"), Animal("未知")]
for a in animals:
    print(f"{a.name}: {a.speak()}")
# 旺财: 汪汪！
# 咪咪: 喵喵！
# 未知: ...（动物叫声）
```

### super() 调用父类
```python
class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)  # 调用父类的 __init__
        self.breed = breed
```

---

## 5.6 魔法方法

以双下划线开头和结尾的方法，Python 内部调用。

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        """print() 或 str() 时调用"""
        return f"Vector({self.x}, {self.y})"

    def __repr__(self):
        """交互环境显示时调用（通常和 __str__ 一样）"""
        return self.__str__()

    def __add__(self, other):
        """+ 运算符"""
        return Vector(self.x + other.x, self.y + other.y)

    def __eq__(self, other):
        """== 运算符"""
        return self.x == other.x and self.y == other.y

    def __len__(self):
        """len() 函数"""
        return 2

v1 = Vector(1, 2)
v2 = Vector(3, 4)
print(v1 + v2)        # Vector(4, 6)
print(v1 == v2)       # False
print(v1 == Vector(1, 2))  # True
```

### 常用魔法方法一览

| 方法 | 触发方式 | 说明 |
|------|---------|------|
| `__init__` | `obj = Class()` | 构造 |
| `__str__` | `print(obj)` | 字符串表示 |
| `__len__` | `len(obj)` | 长度 |
| `__getitem__` | `obj[key]` | 索引访问 |
| `__setitem__` | `obj[key] = val` | 索引赋值 |
| `__iter__` | `for x in obj` | 迭代 |
| `__enter__`/`__exit__` | `with obj:` | 上下文管理 |

---

## 5.7 异常处理

```python
# 基本结构
try:
    num = int(input("输入一个数字："))
    result = 100 / num
    print(f"100 ÷ {num} = {result}")

except ValueError:
    print("输入的不是数字！")
except ZeroDivisionError:
    print("不能除以零！")
except Exception as e:
    print(f"未知错误：{e}")
else:
    print("计算成功！")  # 无异常时执行
finally:
    print("程序结束。")  # 无论如何都执行
```

### 自定义异常
```python
class ScoreError(Exception):
    """成绩异常"""
    def __init__(self, score, msg="成绩不合法"):
        self.score = score
        self.msg = msg
        super().__init__(f"{msg}：{score}")

def set_score(score):
    if score < 0 or score > 100:
        raise ScoreError(score)
    print(f"成绩设定为 {score}")

# try:
#     set_score(150)
# except ScoreError as e:
#     print(e)  # 成绩不合法：150
```

---

## 本章常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 忘记 `self` | 实例方法没写 self 参数 | 实例方法第一个参数必须是 self |
| `AttributeError` | 访问不存在的属性 | 检查属性名，或在 `__init__` 中初始化 |
| 可变默认参数 | `def f(lst=[])` | 改成 `def f(lst=None)` + 内部初始化 |
| 缩进混用 | 类体内缩进不统一 | 类内统一用 4 个空格 |

---

## 本章练习
1. 定义一个 `BankAccount` 类，支持存款、取款、查询余额
2. 继承上题的类，创建 `SavingsAccount`（加利息功能）
3. 定义一个 `Fraction` 类（分数），实现 `__add__` 和 `__str__`
4. 写一个函数 `safe_divide(a, b)`，用异常处理除零和类型错误
