# 第 2 章：流程控制

## 2.1 条件判断

### if / elif / else
```python
score = 85

if score >= 90:
    print("优秀")
elif score >= 80:
    print("良好")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

### 条件表达式（三元运算符）
```python
result = "通过" if score >= 60 else "不通过"
```

### 多条件组合
```python
if age >= 18 and has_id:
    print("可以进入")

if is_weekend or is_holiday:
    print("不用上课")
```

---

## 2.2 for 循环

```python
# 遍历列表
fruits = ["苹果", "香蕉", "橘子"]
for fruit in fruits:
    print(fruit)

# range() 函数
range(5)         # 0, 1, 2, 3, 4
range(2, 6)      # 2, 3, 4, 5
range(1, 10, 2)  # 1, 3, 5, 7, 9（步长 2）

# 遍历字典
student = {"name": "张三", "age": 20}
for key, value in student.items():
    print(f"{key}: {value}")

# enumerate() 同时获取索引和值
for i, fruit in enumerate(fruits):
    print(f"{i}: {fruit}")
```

---

## 2.3 while 循环

```python
# 基本用法
count = 0
while count < 5:
    print(count)
    count += 1

# 无限循环（需用 break 退出）
while True:
    user_input = input("输入 'quit' 退出：")
    if user_input == "quit":
        break
```

**for vs while 的选择**：
- 知道循环次数 → `for`
- 不知道循环次数（等待某个条件）→ `while`

---

## 2.4 break 与 continue

```python
# break：直接退出整个循环
for i in range(10):
    if i == 5:
        break  # 输出 0~4
    print(i)

# continue：跳过本次循环的剩余部分
for i in range(5):
    if i == 2:
        continue  # 跳过 2，输出 0, 1, 3, 4
    print(i)
```

---

## 2.5 循环嵌套

```python
# 九九乘法表
for i in range(1, 10):
    for j in range(1, i + 1):
        print(f"{j}×{i}={i*j}", end="\t")
    print()  # 换行
```

注意事项：
- 嵌套循环的复杂度是 O(n²)，数据量大时注意性能
- 内层循环的变量名不要和外层重复
- 可以用 `break` 配合标志变量跳出多层循环

---

## 2.6 综合练习

### 练习 1：猜数字游戏
```python
import random

target = random.randint(1, 100)
guess = 0
attempts = 0

while guess != target:
    guess = int(input("猜一个 1~100 的数字："))
    attempts += 1
    if guess > target:
        print("太大了！")
    elif guess < target:
        print("太小了！")

print(f"猜对了！你用了 {attempts} 次。")
```

### 练习 2：判断素数
```python
n = int(input("输入一个正整数："))
is_prime = True

for i in range(2, int(n ** 0.5) + 1):
    if n % i == 0:
        is_prime = False
        break

print(f"{n} {'是' if is_prime else '不是'}素数")
```

---

## 本章常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 死循环 | while 条件永远为 True | 确保循环条件会变为 False |
| 缩进错误 | if/for 内部的代码没缩进 | 统一用 4 个空格缩进 |
| 忘记冒号 | if/for/while 行尾少 `:` | 每条控制语句后面都要加冒号 |
| 等于号写成赋值 | `if x = 5:` | 判断相等用 `==` |
