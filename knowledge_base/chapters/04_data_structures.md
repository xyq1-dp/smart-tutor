# 第 4 章：数据结构

## 4.1 列表

列表是 Python 中最常用的数据结构，是有序、可变的元素集合。

```python
# 创建列表
numbers = [1, 2, 3, 4, 5]
fruits = ["苹果", "香蕉", "橘子"]
mixed = [1, "hello", 3.14, True]  # 可以混合类型

# 索引和切片（和字符串一样）
fruits[0]       # '苹果'
fruits[-1]      # '橘子'
fruits[0:2]     # ['苹果', '香蕉']
```

### 常用方法
```python
nums = [3, 1, 4, 1, 5]

nums.append(9)       # 末尾添加 → [3, 1, 4, 1, 5, 9]
nums.insert(0, 10)   # 在索引 0 插入 → [10, 3, 1, 4, ...]
nums.remove(1)       # 删除第一个 1
popped = nums.pop()  # 弹出最后一个（返回 9）
popped = nums.pop(0) # 弹出索引 0
nums.sort()          # 原地排序
nums.reverse()       # 原地反转
len(nums)            # 长度
nums.count(1)        # 计数 1 出现次数
nums.index(4)        # 查找 4 的索引
```

---

## 4.2 元组

元组和列表类似，但是**不可变**（创建后不能修改）。

```python
point = (3, 4)
rgb = (255, 128, 0)
single = (1,)        # 单元素元组必须有逗号！

x, y = point         # 元组解包
# x=3, y=4
```

**什么时候用元组？**
- 数据不需要修改的场景（如坐标、RGB 值）
- 函数返回多个值（本质是返回元组）
- 作为字典的键（列表不能做键，元组可以）

---

## 4.3 字典

字典是**键值对**的集合，通过键快速查找值（O(1) 时间复杂度）。

```python
student = {
    "name": "张三",
    "age": 20,
    "scores": {"math": 90, "python": 95},
}

# 访问
student["name"]            # '张三'
student.get("gender", "未知")  # 安全访问，不存在返回默认值

# 增删改
student["gender"] = "男"   # 添加
student["age"] = 21        # 修改
del student["gender"]      # 删除
popped = student.pop("age")  # 弹出

# 遍历
for key in student:
    print(key, student[key])

for key, value in student.items():
    print(f"{key}: {value}")

for value in student.values():
    print(value)
```

### 字典推导式
```python
squares = {x: x**2 for x in range(5)}
# {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}
```

---

## 4.4 集合

集合是**无序、不重复**的元素集合，基于哈希表实现。

```python
# 创建
s = {1, 2, 3, 3, 3}  # {1, 2, 3} 自动去重
empty = set()          # 空集合（不能用 {}，那是空字典）

# 操作
s.add(4)               # 添加
s.remove(1)            # 删除（元素不存在报错）
s.discard(10)          # 安全删除（不存在不报错）

# 集合运算
a = {1, 2, 3}
b = {2, 3, 4}

a | b   # 并集 → {1, 2, 3, 4}
a & b   # 交集 → {2, 3}
a - b   # 差集 → {1}
a ^ b   # 对称差集 → {1, 4}
```

**适用场景**：去重、成员检测（比列表快很多）、集合运算。

---

## 4.5 列表推导式

Python 的特色语法，一行代码生成列表。

```python
# 基本形式
squares = [x**2 for x in range(10)]
# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 带条件
evens = [x for x in range(10) if x % 2 == 0]
# [0, 2, 4, 6, 8]

# if-else（写在前面）
labels = ["偶" if x % 2 == 0 else "奇" for x in range(5)]
# ['偶', '奇', '偶', '奇', '偶']

# 嵌套 for
pairs = [(x, y) for x in [1, 2] for y in [3, 4]]
# [(1, 3), (1, 4), (2, 3), (2, 4)]
```

---

## 4.6 嵌套数据结构

```python
# 列表套字典
students = [
    {"name": "张三", "scores": [85, 90, 78]},
    {"name": "李四", "scores": [92, 88, 95]},
]

# 访问：第二个学生的第二门成绩
students[1]["scores"][1]  # 88

# 字典套列表
grades = {
    "math": [85, 90, 78],
    "python": [92, 88, 95],
}

# 遍历嵌套结构
for student in students:
    avg = sum(student["scores"]) / len(student["scores"])
    print(f"{student['name']} 平均分：{avg:.1f}")
```

---

## 4.7 数据结构选择指南

| 场景 | 选择 | 理由 |
|------|------|------|
| 有序、需要修改 | `list` | 可变、索引访问 |
| 有序、不可修改 | `tuple` | 更快、更安全 |
| 键值查询 | `dict` | O(1) 查找 |
| 去重、集合运算 | `set` | O(1) 成员检测 |
| 先进先出 | `collections.deque` | 双端队列 |
| 计数器 | `collections.Counter` | 专门计数 |

---

## 本章常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `IndexError` | 列表索引越界 | 检查索引范围，或用 `.get()` |
| `KeyError` | 字典键不存在 | 用 `dict.get(key, default)` |
| `TypeError: unhashable` | 用列表做字典键 | 改用元组 |
| 修改遍历中的列表 | `for x in lst: lst.remove(x)` | 创建副本 `for x in lst[:]` |

---

## 本章练习
1. 输入 5 个数字存入列表，输出它们的和、平均、最大、最小值
2. 统计一段文本中每个单词出现的次数（用字典）
3. 两个列表 `[1,2,3,4]` 和 `[3,4,5,6]`，用集合找出它们的交集和差集
4. 用列表推导式生成 1~100 中所有能被 3 或 5 整除的数
