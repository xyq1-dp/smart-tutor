# 第 6 章：综合项目实战

## 6.1 文件读写操作

```python
# 写文件
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")
    f.writelines(["第三行\n", "第四行\n"])

# 读文件
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()          # 一次性读全部
    # f.readline()              # 逐行读
    # for line in f:            # 逐行遍历（推荐）
    #     print(line.strip())

# 追加
with open("data.txt", "a", encoding="utf-8") as f:
    f.write("追加的内容\n")
```

### 文件模式
| 模式 | 含义 |
|------|------|
| `"r"` | 只读（文件必须存在）|
| `"w"` | 写入（覆盖，不存在则创建）|
| `"a"` | 追加 |
| `"r+"` | 读写 |
| `"rb"` / `"wb"` | 二进制读写 |

**最佳实践**：永远用 `with` 语句，自动关闭文件。

---

## 6.2 常用标准库

### os — 操作系统接口
```python
import os

os.getcwd()             # 当前工作目录
os.listdir(".")         # 列出目录内容
os.path.exists("a.txt") # 检查文件/目录是否存在
os.path.join("dir", "file.txt")  # 跨平台路径拼接
os.makedirs("a/b/c", exist_ok=True)  # 递归创建目录
```

### datetime — 日期时间
```python
from datetime import datetime, timedelta

now = datetime.now()                    # 当前时间
print(now.strftime("%Y-%m-%d %H:%M"))  # 格式化输出

future = now + timedelta(days=7)        # 7 天后
diff = future - now                     # 时间差对象

date_str = "2024-01-15"
parsed = datetime.strptime(date_str, "%Y-%m-%d")  # 字符串解析
```

### random — 随机数
```python
import random

random.randint(1, 100)   # 随机整数
random.random()          # 0~1 随机浮点
random.choice([...])     # 随机选一个
random.shuffle(lst)      # 原地打乱
random.sample(lst, 3)    # 不重复抽 3 个
```

### json — JSON 处理
```python
import json

# Python → JSON
data = {"name": "张三", "scores": [85, 90]}
json_str = json.dumps(data, ensure_ascii=False, indent=2)

# JSON → Python
parsed = json.loads(json_str)

# 读写 JSON 文件
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
```

---

## 6.3 第三方库的安装与使用

```bash
# 安装
pip install requests      # HTTP 请求
pip install numpy          # 数值计算
pip install pandas         # 数据分析
pip install matplotlib     # 数据可视化
```

```python
# requests 示例
import requests

resp = requests.get("https://api.example.com/data")
if resp.status_code == 200:
    data = resp.json()
```

---

## 6.4 项目实战 1：学生成绩管理系统

```python
import json
import os

DATA_FILE = "students.json"

def load_students():
    """从文件加载学生数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_students(students):
    """保存学生数据到文件"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=2)

def add_student(students, name):
    if name not in students:
        students[name] = {"scores": {}}
        save_students(students)
        print(f"已添加学生：{name}")

def add_score(students, name, subject, score):
    if name in students:
        students[name]["scores"][subject] = score
        save_students(students)
        print(f"已记录 {name} 的 {subject} 成绩：{score}")

def report(students, name):
    if name not in students:
        print("学生不存在")
        return
    scores = students[name]["scores"]
    if not scores:
        print(f"{name} 暂无成绩")
        return
    avg = sum(scores.values()) / len(scores)
    print(f"=== {name} 的成绩单 ===")
    for sub, score in scores.items():
        print(f"  {sub}: {score}")
    print(f"平均分：{avg:.1f}")
```

---

## 6.5 项目实战 2：简易图书管理系统

```python
class Book:
    def __init__(self, title, author, isbn):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.is_borrowed = False

    def __str__(self):
        status = "已借出" if self.is_borrowed else "可借"
        return f"《{self.title}》 {self.author} [{status}]"

class Library:
    def __init__(self):
        self.books = []

    def add_book(self, title, author, isbn):
        book = Book(title, author, isbn)
        self.books.append(book)
        print(f"入库：{book}")

    def borrow(self, isbn):
        for book in self.books:
            if book.isbn == isbn:
                if book.is_borrowed:
                    print("该书已被借出！")
                else:
                    book.is_borrowed = True
                    print(f"借出：{book.title}")
                return
        print("未找到该书")

    def return_book(self, isbn):
        for book in self.books:
            if book.isbn == isbn:
                book.is_borrowed = False
                print(f"归还：{book.title}")
                return
        print("未找到该书")

    def list_all(self):
        print("=== 图书馆藏书 ===")
        for book in self.books:
            print(f"  {book}")
```

---

## 6.6 代码调试技巧

```python
# 1. print 调试（最直接）
def complex_calc(x):
    print(f"DEBUG: 输入 x={x}")  # 看中间值
    result = x * 2 + 1
    print(f"DEBUG: 结果={result}")
    return result

# 2. 使用断言
def divide(a, b):
    assert b != 0, "除数不能为 0"
    return a / b

# 3. try/except 捕获异常
try:
    risky_operation()
except Exception as e:
    import traceback
    traceback.print_exc()  # 打印完整堆栈

# 4. pdb 交互式调试
# import pdb; pdb.set_trace()  # 程序会在此暂停，进入交互调试
```

### 常见 Bug 排查思路
1. **读报错信息**：错误类型 + 行号已经给了大半答案
2. **最小化复现**：简化到能复现 bug 的最短代码
3. **二分法**：注释掉一半代码，确定 bug 在哪个范围
4. **橡皮鸭法**：逐行向别人解释代码逻辑，往往自己就发现问题了

---

## 6.7 代码规范与注释

### PEP 8 核心规则
```python
# ✅ 函数名：小写 + 下划线
def calculate_average(scores):
    pass

# ✅ 类名：大驼峰
class StudentManager:
    pass

# ✅ 常量：全大写
MAX_SIZE = 100
DEFAULT_TIMEOUT = 30

# ✅ 每行不超过 79 字符（宽松到 100）
# ✅ 运算符两边加空格
x = a + b  # 不是 x=a+b

# ✅ 逗号后面加空格
items = [1, 2, 3]  # 不是 [1,2,3]
```

### 注释原则
```python
# ❌ 废话注释
x = x + 1  # x 加 1

# ✅ 解释 WHY，不是 WHAT
x = x + 1  # 补偿 off-by-one 误差，因为 range() 不包含终点值

# ✅ 好函数名比注释更好
def is_valid_email(email):  # 函数名已经说明了功能
    return "@" in email
```

---

## 本章练习
1. 完善学生成绩管理系统，增加排序、科目统计功能
2. 写一个 To-Do 列表应用，支持添加、完成、删除、保存到文件
3. 用 requests 库爬取一个网页的标题（`<title>` 标签）
4. 给图书管理系统添加按书名/作者搜索的功能
