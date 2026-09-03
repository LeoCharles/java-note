# MySQL 学习文档

> SQL 是所有关系型数据库的通用语言。本篇以 **MySQL 8.0** 为基准，从连接、建库建表到查询、事务、索引，覆盖 Java 后端开发最高频的知识点。
> 思路：概念 → 语法 → 代码实例 → 易错点 → 实战案例 → Spring Boot 衔接。
> 带 ⭐ 的是开发高频/面试重点。

---

## 一、数据库与 SQL 概述

### 1.1 什么是关系型数据库

数据库（Database）是持久化存储数据的仓库。关系型数据库以**二维表**形式组织数据，表与表之间通过关系（主外键）关联。主流产品：MySQL、PostgreSQL、Oracle、SQL Server。

### 1.2 SQL 语句分类

| 分类 | 全称 | 作用 | 关键字 |
| :--- | :--- | :--- | :--- |
| DDL | 数据定义语言 | 操作库/表结构 | CREATE、ALTER、DROP |
| DML | 数据操作语言 | 操作表中的行数据 | INSERT、UPDATE、DELETE |
| DQL | 数据查询语言 | 查询数据 | SELECT |
| DCL | 数据控制语言 | 权限与事务控制 | GRANT、REVOKE、COMMIT |

### 1.3 MySQL 安装与连接

- 下载：<https://dev.mysql.com/downloads/>
- 命令行连接：`mysql -u 用户名 -p`（回车后输入密码），远程加 `-h IP地址 -P 端口`
- 退出：`exit` 或 `quit`

### 1.4 语法约定

- 每条语句以分号 `;` 结尾，关键字不区分大小写（习惯上关键字大写、表名列名小写）。
- 三种注释：
  - `-- 单行注释`（`--` 后必须有空格）
  - `/* 多行注释 */`
  - `# MySQL 特有单行注释`

---

## 二、DDL 操作数据库与表

### 2.1 操作数据库

```sql
-- 创建（带判断、指定字符集）
CREATE DATABASE IF NOT EXISTS my_test DEFAULT CHARACTER SET utf8mb4;

-- 查看
SHOW DATABASES;              -- 所有库
SHOW CREATE DATABASE my_test; -- 建库语句

-- 修改字符集
ALTER DATABASE my_test DEFAULT CHARACTER SET utf8mb4;

-- 删除
DROP DATABASE IF EXISTS my_test;

-- 使用 / 查看当前库
USE my_test;
SELECT DATABASE();
```

> ⚠️ **字符集务必用 `utf8mb4` 而非 `utf8`**：MySQL 的 `utf8` 最多存 3 字节，存不了 emoji（4 字节），`utf8mb4` 才是真正的 UTF-8。

### 2.2 常用数据类型

| 类型 | 说明 | 实际开发建议 |
| :--- | :--- | :--- |
| `TINYINT` | 1 字节整数 | 状态字段（0/1）常用 |
| `INT` / `BIGINT` | 4/8 字节整数 | 主键自增用 `BIGINT` 更稳妥 |
| `DECIMAL(M,D)` | 定点数 | **金额必须用 DECIMAL**，不能用 FLOAT/DOUBLE |
| `CHAR(M)` | 定长字符串 | 长度固定（如手机号）效率高 |
| `VARCHAR(M)` | 变长字符串 | 最常用字符串类型 |
| `TEXT` / `LONGTEXT` | 大文本 | 文章内容等 |
| `DATE` / `DATETIME` | 日期 / 日期时间 | `DATETIME` 最常用 |
| `TIMESTAMP` | 时间戳 | 自动更新时间常用 |

### 2.3 操作数据表

```sql
-- 创建表
CREATE TABLE student (
  id        BIGINT       PRIMARY KEY AUTO_INCREMENT,
  name      VARCHAR(20) NOT NULL,
  age       INT,
  sex       VARCHAR(2)   DEFAULT '男',
  balance   DECIMAL(10,2) DEFAULT 0.00,
  create_time DATETIME   DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_name UNIQUE(name)   -- 唯一约束
);

-- 查看表
SHOW TABLES;              -- 所有表
DESC student;            -- 表结构
SHOW CREATE TABLE student; -- 建表语句

-- 修改表
ALTER TABLE student ADD COLUMN email VARCHAR(50);     -- 加列
ALTER TABLE student DROP COLUMN age;                  -- 删列
ALTER TABLE student CHANGE name username VARCHAR(30); -- 改列名+类型
ALTER TABLE student MODIFY username VARCHAR(50);      -- 只改类型
RENAME TABLE student TO stu;                          -- 改表名

-- 删除表
DROP TABLE IF EXISTS student;
```

---

## 三、DML 操作表数据

```sql
-- 插入
INSERT INTO student(name, age) VALUES ('张三', 20), ('李四', 22);  -- 批量插入
INSERT INTO student SET name='王五', age=19;                       -- 单行插入

-- 修改
UPDATE student SET age = 21 WHERE name = '张三';   -- 务必带 WHERE！

-- 删除
DELETE FROM student WHERE id = 1;   -- 删指定行，可回滚
TRUNCATE TABLE student;              -- 清空整表，不可回滚，自增重置
```

> ⚠️ **UPDATE/DELETE 不带 WHERE 是灾难**：会更新/删除全表数据。生产环境务必先 `SELECT` 确认范围，再执行 DML。
>
> ⚠️ **DELETE 与 TRUNCATE 区别**：DELETE 逐行删除、可回滚、不重置自增；TRUNCATE 直接清空、不可回滚、重置自增、速度快。

---

## 四、DQL 查询（核心）⭐

查询是 SQL 的重中之重，完整语法结构：

```sql
SELECT 字段列表
FROM 表名
WHERE 条件
GROUP BY 分组字段
HAVING 分组后过滤
ORDER BY 排序字段
LIMIT 分页;
```

**执行顺序**：FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT（理解这个顺序能解释很多"为什么别名在 WHERE 里不能用"的问题）。

### 4.1 基础查询

```sql
SELECT * FROM student;                         -- 全字段
SELECT name, age FROM student;                 -- 指定字段
SELECT name AS 姓名, age 年龄 FROM student;     -- 别名（AS 可省略）
SELECT DISTINCT address FROM student;          -- 去重
SELECT name, IFNULL(math, 0) + IFNULL(english, 0) AS total FROM student; -- 处理 NULL
```

### 4.2 条件查询

```sql
-- 比较与逻辑
SELECT * FROM student WHERE age > 18 AND sex = '男';
SELECT * FROM student WHERE age <> 20;          -- <> 等价于 !=

-- 范围与集合
SELECT * FROM student WHERE age BETWEEN 18 AND 25;   -- 含两端
SELECT * FROM student WHERE id IN (1, 3, 5);

-- 空值判断（不能用 = null）
SELECT * FROM student WHERE address IS NULL;
SELECT * FROM student WHERE address IS NOT NULL;

-- 模糊查询：_ 匹配单字符，% 匹配任意字符
SELECT * FROM student WHERE name LIKE '张%';     -- 姓张的
SELECT * FROM student WHERE name LIKE '张_';     -- 姓张且名字两个字
```

### 4.3 排序

```sql
SELECT * FROM student ORDER BY age DESC;                 -- 降序
SELECT * FROM student ORDER BY age DESC, math ASC;       -- 多字段：年龄降序，同年龄按数学升序
```

### 4.4 聚合函数

聚合函数对一列纵向计算，**自动忽略 NULL 值**。

| 函数 | 作用 |
| :--- | :--- |
| `COUNT(字段)` | 统计行数 |
| `SUM(字段)` | 求和 |
| `AVG(字段)` | 平均 |
| `MAX(字段)` | 最大 |
| `MIN(字段)` | 最小 |

```sql
SELECT COUNT(*) AS 总人数 FROM student;
SELECT AVG(math) AS 数学平均分, MAX(math) AS 最高分 FROM student;
```

> ⚠️ **`COUNT(*)` vs `COUNT(字段)`**：`COUNT(*)` 统计所有行（含 NULL）；`COUNT(字段)` 只统计该字段非 NULL 的行。统计总行数用 `COUNT(*)`。

### 4.5 分组查询

```sql
-- 按性别分组，统计各组数学平均分
SELECT sex, AVG(math) AS math_avg FROM student GROUP BY sex;

-- 先过滤（math>70）再分组
SELECT sex, AVG(math) AS math_avg FROM student WHERE math > 70 GROUP BY sex;

-- 分组后再过滤（平均分>60）
SELECT address, AVG(math) AS math_avg
FROM student
WHERE age > 16
GROUP BY address
HAVING math_avg > 60
ORDER BY math_avg DESC;
```

> ⚠️ **WHERE 与 HAVING 的区别**：
> - WHERE 在分组前过滤，**不能用聚合函数**；
> - HAVING 在分组后过滤，**可以用聚合函数**。

### 4.6 分页查询

```sql
-- 语法：LIMIT 每页条数 OFFSET 起始位置
-- 简写：LIMIT 起始位置, 每页条数
-- 起始位置 = (当前页 - 1) * 每页条数

SELECT * FROM student LIMIT 0, 10;   -- 第 1 页，每页 10 条
SELECT * FROM student LIMIT 10, 10;  -- 第 2 页
```

> ⚠️ 分页公式：`起始索引 = (页码 - 1) * 每页条数`。这是后端分页接口的核心，Spring Boot 的 PageHelper / MyBatis-Plus 分页插件底层就是拼这条 LIMIT。

### 4.7 组合查询

```sql
-- UNION 自动去重，UNION ALL 保留重复
SELECT name FROM student WHERE class_id = 1
UNION
SELECT name FROM student WHERE class_id = 2;
```

---

## 五、多表查询 ⭐

### 5.1 连接查询

```sql
-- 隐式内连接（WHERE）
SELECT * FROM student s, class c WHERE s.class_id = c.id;

-- 显式内连接（INNER JOIN ... ON）—— 推荐
SELECT s.name, c.class_name
FROM student s
INNER JOIN class c ON s.class_id = c.id;

-- 左外连接：左表全保留，右表匹配不上的补 NULL
SELECT s.name, c.class_name
FROM student s
LEFT JOIN class c ON s.class_id = c.id;

-- 右外连接：右表全保留
SELECT s.name, c.class_name
FROM student s
RIGHT JOIN class c ON s.class_id = c.id;
```

> ⚠️ **内连接 vs 外连接**：内连接只返回两表都匹配的行；左外连接左表全保留，右表无匹配补 NULL。**查"某表全部，含未关联的"必须用外连接**。

### 5.2 子查询

查询中嵌套查询，按结果分类：

```sql
-- 单行单列：作条件，用 = > <
SELECT * FROM student WHERE age = (SELECT MAX(age) FROM student);

-- 多行单列：作条件，用 IN
SELECT * FROM student WHERE class_id IN (SELECT id FROM class WHERE name LIKE '%班');

-- 多行多列：作虚拟表
SELECT * FROM (SELECT name, age FROM student WHERE age > 18) t WHERE t.age < 25;
```

---

## 六、约束

约束保证数据的正确性、完整性。

| 约束 | 关键字 | 作用 |
| :--- | :--- | :--- |
| 主键 | `PRIMARY KEY` | 唯一且非空，一张表一个 |
| 非空 | `NOT NULL` | 不能为 NULL |
| 唯一 | `UNIQUE` | 不能重复 |
| 默认 | `DEFAULT` | 无值时填默认值 |
| 自增 | `AUTO_INCREMENT` | 自动递增，配合主键 |
| 外键 | `FOREIGN KEY` | 关联两表，保证参照完整性 |

```sql
CREATE TABLE score (
  id        BIGINT PRIMARY KEY AUTO_INCREMENT,
  student_id BIGINT NOT NULL,
  score     DECIMAL(5,2),
  CONSTRAINT fk_student FOREIGN KEY (student_id) REFERENCES student(id)
    ON UPDATE CASCADE ON DELETE CASCADE   -- 级联更新/删除
);
```

> ⚠️ **实际开发中慎用外键**：外键会带来性能开销和级联风险，互联网项目通常在**应用层（Java 代码）保证数据一致性**，而非数据库外键。MyBatis/JPA 实体关系 ≠ 数据库外键。

---

## 七、事务 ⭐

### 7.1 什么是事务

事务是把多条 SQL 作为一个整体执行，**要么全部成功，要么全部失败**。典型场景：转账（A 扣钱 + B 加钱，不能只成功一半）。

```sql
-- 手动事务
BEGIN;   -- 或 START TRANSACTION
UPDATE account SET balance = balance - 100 WHERE id = 1;
UPDATE account SET balance = balance + 100 WHERE id = 2;
COMMIT;  -- 提交；出错则 ROLLBACK;
```

> MySQL 默认对每条 DML 自动提交（autocommit=1）。手动事务用 `BEGIN` 开启后，需显式 `COMMIT` 或 `ROLLBACK`。

### 7.2 ACID 特性

| 特性 | 含义 |
| :--- | :--- |
| 原子性 Atomicity | 事务不可分割，要么全成功要么全失败 |
| 一致性 Consistency | 事务前后数据总量保持一致 |
| 隔离性 Isolation | 多事务并发时相互隔离 |
| 持久性 Durability | 提交后数据永久保存 |

### 7.3 并发问题与隔离级别

并发事务可能产生的问题：

| 问题 | 说明 |
| :--- | :--- |
| 脏读 | 读到别的事务**未提交**的数据 |
| 不可重复读 | 同一事务内两次读同一行，结果不同（别的事务 UPDATE 了） |
| 幻读 | 同一事务内两次查询，行数不同（别的事务 INSERT/DELETE 了） |

四种隔离级别（从低到高）：

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
| :--- | :---: | :---: | :---: |
| READ UNCOMMITTED 读未提交 | ✓ | ✓ | ✓ |
| READ COMMITTED 读已提交（Oracle 默认） | ✗ | ✓ | ✓ |
| REPEATABLE READ 可重复读（**MySQL 默认**） | ✗ | ✗ | ✓ |
| SERIALIZABLE 串行化 | ✗ | ✗ | ✗ |

```sql
-- 查看与设置隔离级别
SELECT @@transaction_isolation;
SET GLOBAL transaction_isolation = 'READ-COMMITTED';
```

> 隔离级别越高数据越安全，但并发性能越低。MySQL 默认 REPEATABLE READ，已能避免脏读和不可重复读。

---

## 八、索引 ⭐

> 索引是旧文档缺失但实际开发必备的内容，是 MySQL 性能优化的核心。

### 8.1 什么是索引

索引是帮助 MySQL **高效获取数据的数据结构**（默认 B+ 树）。类比字典的目录——没有目录要逐页翻，有目录直接定位。

- 优点：大幅提升查询速度。
- 缺点：占用磁盘空间；插入/更新/删除时需同步维护索引，降低写速度。

### 8.2 索引操作

```sql
-- 创建普通索引
CREATE INDEX idx_name ON student(name);

-- 创建唯一索引
CREATE UNIQUE INDEX uk_email ON student(email);

-- 查看索引
SHOW INDEX FROM student;

-- 删除索引
DROP INDEX idx_name ON student;
```

### 8.3 索引失效场景

```sql
-- ❌ 索引列上做运算/函数
SELECT * FROM student WHERE age + 1 = 20;        -- 失效，应改为 age = 19
-- ❌ 最左前缀原则：联合索引 (a,b,c) 没用 a 就失效
SELECT * FROM t WHERE b = 1;                      -- 失效
-- ❌ LIKE 以 % 开头
SELECT * FROM student WHERE name LIKE '%三';      -- 失效
-- ❌ 类型隐式转换
SELECT * FROM student WHERE name = 123;           -- 失效（name 是字符串）
```

> ⚠️ **索引使用原则**：
> 1. 频繁查询的字段建索引，频繁更新的字段少建。
> 2. 主键自动建索引，外键、WHERE/ORDER BY/GROUP BY 常用字段适合建。
> 3. 联合索引遵循**最左前缀原则**。
> 4. 用 `EXPLAIN` 分析 SQL 是否走索引：`EXPLAIN SELECT * FROM student WHERE name='张三';`

---

## 九、数据库设计与范式

### 9.1 表关系

- **一对多**：在"多"的一方加外键指向"一"的一方主键（部门-员工）。
- **多对多**：建中间表，含两个外键分别指向两表主键（学生-课程）。
- **一对一**：任意一方加唯一外键（用户-身份证）。

### 9.2 三大范式

| 范式 | 要求 | 通俗理解 |
| :--- | :--- | :--- |
| 1NF | 每列不可再分 | 字段不能塞集合/对象 |
| 2NF | 非主键列完全依赖主键 | 不能部分依赖（主要针对联合主键） |
| 3NF | 非主键列直接依赖主键 | 不能传递依赖（消除冗余） |

> ⚠️ 实际开发中**适度反范式**：为查询性能可保留少量冗余字段，不必死磕 3NF。性能与规范的平衡才是工程实践。

---

## ⚠️ 重点

1. **字符集用 `utf8mb4`**，否则存不了 emoji。
2. **金额用 `DECIMAL`**，FLOAT/DOUBLE 有精度丢失。
3. **UPDATE/DELETE 必带 WHERE**，否则全表遭殃。
4. **`COUNT(*)` 统计总行数**，`COUNT(字段)` 忽略 NULL。
5. **WHERE 不能用聚合函数**，过滤分组用 HAVING。
6. **分页公式**：`LIMIT (页码-1)*条数, 条数`。
7. **内连接只返回匹配行，外连接保留一侧全部**。
8. **索引不是越多越好**，写多读少的表慎建索引。
9. **事务四大特性 ACID、四种隔离级别**是面试高频。

---

## 💻 实战案例

设计一个学生-班级-成绩库，覆盖本篇所有知识点：

```sql
-- 建库
CREATE DATABASE IF NOT EXISTS school DEFAULT CHARACTER SET utf8mb4;
USE school;

-- 班级表
CREATE TABLE class (
  id    BIGINT PRIMARY KEY AUTO_INCREMENT,
  name  VARCHAR(20) NOT NULL
);

-- 学生表
CREATE TABLE student (
  id        BIGINT PRIMARY KEY AUTO_INCREMENT,
  name      VARCHAR(20) NOT NULL,
  age       INT,
  sex       VARCHAR(2) DEFAULT '男',
  class_id  BIGINT,
  INDEX idx_class (class_id)
);

-- 成绩表
CREATE TABLE score (
  id         BIGINT PRIMARY KEY AUTO_INCREMENT,
  student_id BIGINT NOT NULL,
  subject    VARCHAR(20),
  mark       DECIMAL(5,2),
  INDEX idx_student (student_id)
);

-- 插入数据
INSERT INTO class(name) VALUES ('一班'),('二班');
INSERT INTO student(name, age, sex, class_id) VALUES
  ('张三', 20, '男', 1), ('李四', 22, '女', 1), ('王五', 19, '男', 2);
INSERT INTO score(student_id, subject, mark) VALUES
  (1, '数学', 90), (1, '英语', 85), (2, '数学', 78), (3, '英语', 92);

-- 需求 1：查询每个班的数学平均分（多表 + 分组）
SELECT c.name AS 班级, AVG(s.mark) AS 数学平均分
FROM class c
JOIN student st ON st.class_id = c.id
JOIN score s ON s.student_id = st.id
WHERE s.subject = '数学'
GROUP BY c.name;

-- 需求 2：查询数学成绩高于平均分的学生（子查询）
SELECT st.name, s.mark
FROM student st
JOIN score s ON s.student_id = st.id
WHERE s.subject = '数学'
  AND s.mark > (SELECT AVG(mark) FROM score WHERE subject = '数学');

-- 需求 3：分页查询学生（第 1 页，每页 2 条）
SELECT * FROM student ORDER BY id LIMIT 0, 2;

-- 需求 4：事务——转学分
BEGIN;
UPDATE score SET mark = mark - 5 WHERE student_id = 1 AND subject = '数学';
UPDATE score SET mark = mark + 5 WHERE student_id = 2 AND subject = '数学';
COMMIT;
```

---

## 🚀 新版本补充

- **MySQL 8.0** 默认字符集已改为 `utf8mb4`，无需手动指定；隔离级别变量名从 `tx_isolation` 改为 `transaction_isolation`。
- **窗口函数**（MySQL 8.0+）：`ROW_NUMBER() OVER()`、`RANK() OVER()`，用于排名场景，比传统子查询简洁。
- **JSON 类型**：MySQL 8.0 原生支持 JSON 字段与函数，适合存储半结构化数据。

---

## 📌 在 Spring Boot 中

| 本篇概念 | Spring Boot 中的对应 |
| :--- | :--- |
| 建表/改表 | **Flyway/Liquibase** 数据库版本迁移（见 [54-数据库版本控制_Flyway](../Spring/54-数据库版本控制_Flyway.md)） |
| 增删改查 SQL | MyBatis-Plus 的 `BaseMapper` / JPA 的 `Repository` 自动生成 |
| 分页 LIMIT | **PageHelper** 或 MyBatis-Plus 分页插件，传页码即可 |
| 事务 | `@Transactional` 注解，底层就是 `BEGIN/COMMIT/ROLLBACK` |
| 连接配置 | `spring.datasource.*` 自动配置 |
| 索引 | 实体类 `@TableField` + 建表 SQL，仍需手动设计 |

> 一句话：**SQL 语法是地基，Spring Boot 是脚手架。** 地基不牢，用 MyBatis-Plus 时连 N+1 查询、索引失效都看不出来。

---

## 本章小结

本篇覆盖了 MySQL 从建库建表到查询、事务、索引的完整基础。重点掌握：DQL 查询（条件/排序/聚合/分组/分页）、多表连接、事务 ACID 与隔离级别、索引原理与失效场景。这些是后续 JDBC、MyBatis、Spring Data JPA 的共同基础。下一篇 [JDBC](JDBC.md) 将用 Java 代码操作这些 SQL。
