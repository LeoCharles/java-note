# PostgreSQL 学习文档

> 📅 创建时间：2026-09  
> 🎯 目标读者：有前端开发基础，希望快速掌握 PostgreSQL 数据库的工程师  
> 📌 文档定位：数据库基础 + SQL 语法速查 + Spring Boot 集成实战 + 性能排查  
> 📌 配套文档：[Spring Boot 快速上手文档](../Spring/Spring%20Boot%20快速上手文档.md)

---

## 📖 目录

- [第一章：数据库基础概念](#第一章数据库基础概念)
- [第二章：PostgreSQL 环境搭建](#第二章postgresql-环境搭建)
- [第三章：SQL 基础语法速查](#第三章sql-基础语法速查)
- [第四章：SQL 进阶查询](#第四章sql-进阶查询)
- [第五章：表设计与索引优化](#第五章表设计与索引优化)
- [第六章：事务与并发控制](#第六章事务与并发控制)
- [第七章：PostgreSQL 高级特性](#第七章postgresql-高级特性)
- [第八章：Spring Boot 集成 PostgreSQL](#第八章spring-boot-集成-postgresql)
- [第九章：实战案例——完整 CRUD 开发](#第九章实战案例完整-crud-开发)
- [第十章：SQL 调试与性能排查](#第十章sql-调试与性能排查)
- [第十一章：常见问题与避坑指南](#第十一章常见问题与避坑指南)

---

# 第一章：数据库基础概念

## 1.1 什么是关系型数据库

关系型数据库将数据组织成**表（Table）**，表之间通过**外键（Foreign Key）**建立关联。

```
┌──────────────────────────────────────────────────────────┐
│                      数据库 (Database)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  users 表    │  │  orders 表   │  │ products 表  │       │
│  │             │  │             │  │             │       │
│  │ id  name    │  │ id  user_id │  │ id  title   │       │
│  │ 1   张三    │──│ 1   1       │  │ 1   手机    │       │
│  │ 2   李四    │  │ 2   2       │  │ 2   电脑    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                         ↑                                 │
│                    user_id 是外键，引用 users.id            │
└──────────────────────────────────────────────────────────┘
```

### 前端开发者的对照理解

| 前端概念 | 数据库概念 | 说明 |
|---|---|---|
| 对象数组 `[{id:1,name:"张三"},...]` | 表 Table | 同一类数据的集合 |
| 对象的属性 `{id: 1, name: "张三"}` | 列 Column / 字段 Field | 数据的属性 |
| 一个对象 `{id: 1, name: "张三"}` | 行 Row / 记录 Record | 一条数据 |
| TypeScript 类型 `interface User { id: number; name: string }` | 表结构 Schema | 定义数据的形状 |
| `arr.find(x => x.id === 1)` | 主键查询 | 通过唯一标识查找 |
| `arr.filter(x => x.age > 20)` | WHERE 条件查询 | 按条件过滤 |

## 1.2 PostgreSQL 简介

PostgreSQL（简称 PG）是世界上最先进的开源关系型数据库，以其**稳定性、扩展性和标准兼容性**著称。

**PostgreSQL 的核心优势：**

| 特性 | 说明 | 实际价值 |
|---|---|---|
| **ACID 完全支持** | 事务严格可靠 | 金融、订单等场景数据零丢失 |
| **丰富的数据类型** | JSONB、数组、范围、地理空间等 | 在数据库层面处理复杂数据 |
| **强大的索引** | B-Tree、GIN、GiST、BRIN 等 | 各种查询场景都能优化 |
| **MVCC 并发控制** | 读写互不阻塞 | 高并发场景性能优异 |
| **JSONB 支持** | 原生 JSON 存储和查询，性能优于 MongoDB 很多场景 | 兼顾关系型和文档型数据库 |
| **窗口函数** | 排名、移动平均、累计等 | 复杂报表直接在 SQL 中完成 |
| **CTE（公共表表达式）** | WITH 递归查询 | 树形结构（部门、评论）轻松处理 |

> **💡 前端类比**：如果 MySQL 是 Express.js（简单好用），那 PostgreSQL 就是 Next.js（功能强大、生态丰富，同时保持高标准）。

## 1.3 核心概念速查

### 1.3.1 Schema（模式）

Schema 是数据库中的逻辑分组，类似命名空间。一个数据库可以包含多个 Schema。

```sql
-- PostgreSQL 默认有一个 public schema
-- 以下两条语句等价：
SELECT * FROM users;
SELECT * FROM public.users;  -- 完整写法：schema.table

-- 创建自定义 schema
CREATE SCHEMA inventory;
CREATE TABLE inventory.products (id SERIAL PRIMARY KEY, name TEXT);
```

> **💡 前端类比**：Schema 就像代码中的目录/文件夹，用于组织和管理表。

### 1.3.2 主键（Primary Key）

主键是表中**唯一标识**每一行数据的列，不可重复、不可为 NULL。

```sql
-- 常见主键类型
-- 1. 自增整数（最常用）
CREATE TABLE users (
    id SERIAL PRIMARY KEY,   -- PostgreSQL 的 SERIAL 是自增整数
    name TEXT
);

-- 2. UUID（分布式系统常用）
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT
);

-- 3. 雪花 ID（分布式系统，需要扩展）
-- 实际项目中常用 MyBatis-Plus 的 IdType.ASSIGN_ID
```

### 1.3.3 外键（Foreign Key）

外键用于建立表之间的关联关系，保证数据完整性。

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    -- 外键约束：user_id 必须存在于 users 表中
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE  -- 用户删除时，其订单也删除
);
```

### 1.3.4 索引（Index）

索引就像书的目录，加速数据查找。没有索引，数据库需要全表扫描。

```sql
-- 创建索引
CREATE INDEX idx_users_name ON users(name);          -- 单列索引
CREATE INDEX idx_users_name_age ON users(name, age); -- 复合索引
CREATE UNIQUE INDEX idx_users_email ON users(email); -- 唯一索引（email 不能重复）
```

> **💡 前端类比**：索引就像 JS 对象中用 Map 替代 Array 查找——O(1) vs O(n)。

---

# 第二章：PostgreSQL 环境搭建

## 2.1 安装方式

### 方式一：Windows 安装包

1. 官网下载：https://www.postgresql.org/download/windows/
2. 运行安装程序，按向导安装
3. 记住安装过程中设置的两个关键信息：
   - **端口**：默认 5432
   - **超级用户 postgres 的密码**（务必记住！）

### 方式二：Docker（推荐，一命令启动）

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=mydb \
  -p 5432:5432 \
  postgres:16
```

### 方式三：公司已有的开发环境

如果公司已经提供了数据库环境，你只需要拿到连接信息：
- 主机地址（Host）
- 端口（Port，默认 5432）
- 数据库名（Database）
- 用户名（Username）
- 密码（Password）

## 2.2 客户端工具

### psql（命令行）

```bash
# 连接数据库
psql -h localhost -p 5432 -U postgres -d mydb

# 常用命令
\l          -- 列出所有数据库
\c dbname   -- 切换数据库
\dt         -- 列出当前数据库的所有表
\d tablename -- 查看表结构
\di         -- 列出所有索引
\du         -- 列出所有用户
\q          -- 退出
```

### 图形化工具推荐

| 工具 | 说明 | 推荐度 |
|---|---|---|
| **DBeaver** | 免费开源，功能强大，支持多种数据库 | ⭐⭐⭐⭐⭐ |
| **DataGrip** | JetBrains 出品，和 IDEA 深度集成 | ⭐⭐⭐⭐⭐ |
| **Navicat** | 老牌工具，界面友好（收费） | ⭐⭐⭐⭐ |
| **pgAdmin** | PostgreSQL 官方工具 | ⭐⭐⭐ |

## 2.3 创建测试数据库

```sql
-- 创建数据库
CREATE DATABASE testdb;

-- 创建用户
CREATE USER testuser WITH PASSWORD 'test123';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE testdb TO testuser;

-- 切换到 testdb 后，授予 Schema 权限
\c testdb
GRANT ALL ON SCHEMA public TO testuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO testuser;
```

---

# 第三章：SQL 基础语法速查

## 3.1 SQL 语句分类

```
SQL 语句
├── DDL（数据定义语言）—— 操作表结构
│   ├── CREATE  —— 创建数据库/表/索引
│   ├── ALTER   —— 修改表结构
│   ├── DROP    —— 删除数据库/表/索引
│   └── TRUNCATE —— 清空表数据
│
├── DML（数据操作语言）—— 操作数据
│   ├── SELECT  —— 查询数据（最常用！）
│   ├── INSERT  —— 插入数据
│   ├── UPDATE  —— 更新数据
│   └── DELETE  —— 删除数据
│
└── DCL（数据控制语言）—— 权限管理
    ├── GRANT   —— 授予权限
    └── REVOKE  —— 撤销权限
```

## 3.2 创建表（CREATE TABLE）

```sql
-- 创建一个完整的用户表
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,              -- 自增主键
    username    VARCHAR(50) NOT NULL UNIQUE,     -- 用户名，非空且唯一
    email       VARCHAR(100) NOT NULL UNIQUE,    -- 邮箱
    password    VARCHAR(255) NOT NULL,           -- 密码（加密后存储）
    age         INTEGER CHECK (age >= 0 AND age <= 150),  -- 年龄，带检查约束
    status      VARCHAR(20) DEFAULT 'active',    -- 状态，默认值 'active'
    role        VARCHAR(20) NOT NULL DEFAULT 'user',  -- 角色
    created_at  TIMESTAMP DEFAULT NOW(),         -- 创建时间，默认当前时间
    updated_at  TIMESTAMP DEFAULT NOW()          -- 更新时间
);

-- 创建订单表（与用户表关联）
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_no    VARCHAR(32) NOT NULL UNIQUE,     -- 订单号
    amount      DECIMAL(10, 2) NOT NULL,         -- 金额，总共10位，小数2位
    status      VARCHAR(20) DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### PostgreSQL 常用数据类型

| 数据类型 | 说明 | 示例 | 前端类比 |
|---|---|---|---|
| `INTEGER` / `INT` | 整数 | `25` | `number` |
| `BIGINT` | 大整数 | `9007199254740991` | `bigint` |
| `SERIAL` | 自增整数 | 自动生成 1,2,3... | `autoIncrement` |
| `BIGSERIAL` | 自增大整数 | 自动生成 | `autoIncrement` |
| `VARCHAR(n)` | 变长字符串 | `'张三'` | `string` |
| `TEXT` | 不限长文本 | `'很长的内容...'` | `string` |
| `BOOLEAN` | 布尔值 | `true` / `false` | `boolean` |
| `DATE` | 日期 | `'2026-09-01'` | `Date` |
| `TIMESTAMP` | 日期时间 | `'2026-09-01 10:00:00'` | `Date` |
| `TIMESTAMPTZ` | 带时区的日期时间 | 自动处理时区 | `Date` |
| `DECIMAL(10,2)` | 精确小数 | `99.99` | `number` |
| `JSONB` | JSON 数据（二进制存储） | `'{"key": "value"}'` | `Record<string, any>` |
| `UUID` | 全局唯一标识 | `gen_random_uuid()` | `crypto.randomUUID()` |
| `INTEGER[]` | 整数数组 | `'{1,2,3}'` | `number[]` |
| `ENUM` | 枚举（需先创建类型） | `'active'` | `enum` |

## 3.3 查询数据（SELECT）

```sql
-- ===== 基本查询 =====

-- 查询所有列（生产环境不推荐 SELECT *，性能差）
SELECT * FROM users;

-- 查询指定列（推荐）
SELECT id, username, email, status FROM users;

-- 去重查询
SELECT DISTINCT status FROM users;

-- 限制返回行数
SELECT * FROM users LIMIT 10;               -- 前 10 条
SELECT * FROM users LIMIT 10 OFFSET 20;     -- 跳过 20 条，取 10 条（分页）

-- 别名
SELECT u.id AS user_id, u.username AS name FROM users u;
```

### WHERE 条件查询

```sql
-- ===== 比较运算符 =====
SELECT * FROM users WHERE age > 18;          -- 大于
SELECT * FROM users WHERE age >= 18;         -- 大于等于
SELECT * FROM users WHERE age = 25;          -- 等于
SELECT * FROM users WHERE age <> 25;         -- 不等于（也可用 !=）
SELECT * FROM users WHERE age BETWEEN 20 AND 30;  -- 范围

-- ===== 逻辑运算符 =====
SELECT * FROM users WHERE age > 18 AND status = 'active';
SELECT * FROM users WHERE age < 18 OR age > 60;
SELECT * FROM users WHERE NOT status = 'deleted';
SELECT * FROM users WHERE status IN ('active', 'pending');  -- 在列表中
SELECT * FROM users WHERE status NOT IN ('deleted', 'banned');

-- ===== 模糊搜索 =====
SELECT * FROM users WHERE username LIKE '张%';   -- 以"张"开头
SELECT * FROM users WHERE email LIKE '%@gmail.com';  -- Gmail 邮箱
SELECT * FROM users WHERE username LIKE '%三%';  -- 包含"三"
SELECT * FROM users WHERE username ILIKE 'zhang%';  -- 忽略大小写（PG 特有）

-- ===== NULL 判断 =====
SELECT * FROM users WHERE email IS NULL;        -- email 为空
SELECT * FROM users WHERE email IS NOT NULL;    -- email 不为空
-- 注意：不能用 = NULL，必须用 IS NULL！

-- ===== 正则表达式（PG 特有） =====
SELECT * FROM users WHERE email ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$';
```

### 排序和分页

```sql
-- 排序
SELECT * FROM users ORDER BY created_at DESC;         -- 降序（最新的在前）
SELECT * FROM users ORDER BY age ASC, name DESC;     -- 先按年龄升序，再按名字降序

-- 分页（前端列表常用）
-- 第 1 页，每页 10 条
SELECT * FROM users ORDER BY id LIMIT 10 OFFSET 0;

-- 第 2 页，每页 20 条
SELECT * FROM users ORDER BY id LIMIT 20 OFFSET 20;

-- 分页公式：OFFSET = (page - 1) * pageSize
-- 第 3 页，每页 15 条 → OFFSET = (3-1) * 15 = 30
SELECT * FROM users ORDER BY id LIMIT 15 OFFSET 30;
```

## 3.4 插入数据（INSERT）

```sql
-- 插入单条（指定列）
INSERT INTO users (username, email, password, age)
VALUES ('张三', 'zhang@test.com', 'hashed_password', 25);

-- 插入单条（所有列，按表定义顺序）
INSERT INTO users VALUES
(DEFAULT, '李四', 'li@test.com', 'hashed_password', 30, 'active', 'user', NOW(), NOW());

-- 插入多条
INSERT INTO users (username, email, password, age) VALUES
('王五', 'wang@test.com', 'hashed_pwd', 28),
('赵六', 'zhao@test.com', 'hashed_pwd', 35),
('钱七', 'qian@test.com', 'hashed_pwd', 22);

-- 插入并返回（PG 特有，非常实用！）
INSERT INTO users (username, email, password, age)
VALUES ('孙八', 'sun@test.com', 'hashed_pwd', 40)
RETURNING id, username, created_at;  -- 返回刚插入的 id 和时间
```

## 3.5 更新数据（UPDATE）

```sql
-- ⚠️ 更新前一定先用 SELECT 确认 WHERE 条件！

-- 更新单条
UPDATE users SET age = 26, updated_at = NOW() WHERE id = 1;

-- 批量更新
UPDATE users SET status = 'active' WHERE status = 'pending';

-- 基于其他表更新
UPDATE orders SET status = 'cancelled'
WHERE user_id IN (SELECT id FROM users WHERE status = 'banned');

-- 更新并返回（PG 特有）
UPDATE users SET age = age + 1 WHERE id = 1
RETURNING id, username, age;  -- 返回更新后的值
```

> **⚠️ 危险操作**：`UPDATE users SET status = 'active';` 如果不加 WHERE，会更新全表！

## 3.6 删除数据（DELETE）

```sql
-- ⚠️ 删除前一定先用 SELECT 确认 WHERE 条件！

-- 删除单条
DELETE FROM users WHERE id = 1;

-- 批量删除
DELETE FROM users WHERE status = 'deleted' AND updated_at < NOW() - INTERVAL '30 days';

-- 清空表（删除所有数据，保留表结构，比 DELETE 快）
TRUNCATE TABLE users CASCADE;  -- CASCADE 同时清空关联表的外键引用
```

---

# 第四章：SQL 进阶查询

## 4.1 聚合函数与分组

```sql
-- ===== 聚合函数 =====
SELECT COUNT(*) FROM users;                          -- 总行数
SELECT COUNT(DISTINCT status) FROM users;            -- 去重计数
SELECT AVG(age) FROM users;                          -- 平均年龄
SELECT SUM(amount) FROM orders;                      -- 总金额
SELECT MAX(amount), MIN(amount) FROM orders;         -- 最大/最小金额
SELECT STRING_AGG(username, ', ') FROM users;       -- 字符串拼接（PG 特有）

-- ===== GROUP BY 分组 =====
-- 按状态统计用户数
SELECT status, COUNT(*) AS count
FROM users
GROUP BY status
ORDER BY count DESC;

-- 按日期统计订单金额
SELECT DATE(created_at) AS order_date, SUM(amount) AS total
FROM orders
GROUP BY DATE(created_at)
ORDER BY order_date DESC;

-- ===== HAVING 过滤分组结果 =====
-- WHERE 过滤行，HAVING 过滤组
-- 找出订单总金额 > 1000 的用户
SELECT user_id, SUM(amount) AS total_amount
FROM orders
GROUP BY user_id
HAVING SUM(amount) > 1000
ORDER BY total_amount DESC;
```

### SQL 执行顺序（理解这个很重要！）

```sql
SELECT   ...   -- 5. 选择要返回的列
FROM     ...   -- 1. 确定数据来源
JOIN     ...   -- 2. 关联其他表
WHERE    ...   -- 3. 过滤行（在分组前）
GROUP BY ...   -- 4. 分组
HAVING   ...   -- 6. 过滤组（在分组后）
ORDER BY ...   -- 7. 排序
LIMIT    ...   -- 8. 限制返回行数
```

> **💡 前端类比**：这就像 Array 的链式操作顺序——`source.filter(where).groupBy(groupBy).filter(having).map(select).sort(orderBy).slice(limit)`

## 4.2 表连接（JOIN）

JOIN 是 SQL 最强大的功能之一，用于将多个表的数据关联起来。

```
JOIN 类型图解（假设 users 有 3 条数据，orders 有 2 条匹配 1 条不匹配）：

INNER JOIN：只返回两表都匹配的行
  users: [1] [2] [3]    orders: [1] [2] [x]
  结果: [1] [2]          ← 只保留匹配的

LEFT JOIN：返回左表所有行，右表匹配不上填 NULL
  users: [1] [2] [3]    orders: [1] [2] [x]
  结果: [1] [2] [3→NULL] ← 左表全保留

RIGHT JOIN：返回右表所有行，左表匹配不上填 NULL
  结果: [1] [2] [x→NULL] ← 右表全保留

FULL JOIN：两表所有行都保留，匹配不上填 NULL
  结果: [1] [2] [3→NULL] [x→NULL] ← 全保留
```

### JOIN 实战示例

```sql
-- 初始化测试数据
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    dept_id INTEGER REFERENCES departments(id),
    salary DECIMAL(10,2)
);

INSERT INTO departments VALUES (1, '技术部'), (2, '产品部'), (3, '市场部');
INSERT INTO employees VALUES
(1, '张三', 1, 15000),
(2, '李四', 1, 18000),
(3, '王五', 2, 12000),
(4, '赵六', NULL, 10000);  -- 没有部门

-- INNER JOIN：只查有部门的员工
SELECT e.name AS 员工, d.name AS 部门, e.salary AS 薪资
FROM employees e
INNER JOIN departments d ON e.dept_id = d.id;
-- 结果：张三|技术部|15000, 李四|技术部|18000, 王五|产品部|12000

-- LEFT JOIN：查所有员工（包括没部门的）
SELECT e.name AS 员工, COALESCE(d.name, '未分配') AS 部门
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id;
-- 结果：张三|技术部, 李四|技术部, 王五|产品部, 赵六|未分配

-- 多表 JOIN
SELECT o.id AS 订单号, u.username AS 用户名, p.name AS 商品名, oi.quantity AS 数量
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON oi.product_id = p.id
WHERE o.created_at > NOW() - INTERVAL '7 days';
```

## 4.3 子查询

```sql
-- 标量子查询：返回单个值
SELECT * FROM users
WHERE age > (SELECT AVG(age) FROM users);

-- 行子查询：返回一行
SELECT * FROM users
WHERE (age, status) = (SELECT age, status FROM users WHERE id = 1);

-- 列子查询：返回一列（配合 IN）
SELECT * FROM users
WHERE id IN (SELECT user_id FROM orders WHERE amount > 1000);

-- EXISTS 子查询：检查是否存在
SELECT * FROM users u
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id);

-- 关联子查询：子查询引用外层
SELECT u.username, (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count
FROM users u;
```

## 4.4 窗口函数（PostgreSQL 强项）

窗口函数在不合并行的情况下进行聚合计算，是复杂报表的利器。

```sql
-- 测试数据
INSERT INTO employees (name, dept_id, salary) VALUES
('孙七', 1, 20000), ('周八', 2, 14000), ('吴九', 3, 16000);

-- ROW_NUMBER：行号（排名不重复）
SELECT name, dept_id, salary,
       ROW_NUMBER() OVER (ORDER BY salary DESC) AS rank
FROM employees;

-- RANK：排名（有并列时跳过）
-- DENSE_RANK：排名（有并列时不跳过）
SELECT name, dept_id, salary,
       RANK() OVER (ORDER BY salary DESC) AS rank,
       DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank
FROM employees;

-- 部门内排名（PARTITION BY 分组）
SELECT name, dept_id, salary,
       RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS dept_rank
FROM employees;
-- 结果：每个部门内部按薪资排名

-- 累计和
SELECT name, salary,
       SUM(salary) OVER (ORDER BY salary DESC) AS running_total
FROM employees;

-- 移动平均（前后各一行）
SELECT name, salary,
       AVG(salary) OVER (ORDER BY salary ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS moving_avg
FROM employees;
```

## 4.5 CTE（公共表表达式）

CTE 让复杂查询可读性大幅提升，支持递归查询树形结构。

```sql
-- 基础 CTE：将子查询提取为命名临时表
WITH high_salary_users AS (
    SELECT * FROM employees WHERE salary > 15000
)
SELECT d.name AS 部门, COUNT(h.*) AS 高薪人数
FROM departments d
LEFT JOIN high_salary_users h ON h.dept_id = d.id
GROUP BY d.name;

-- 递归 CTE：查询树形结构（部门层级、评论嵌套等）
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    parent_id INTEGER REFERENCES categories(id)
);

INSERT INTO categories VALUES
(1, '电子产品', NULL),
(2, '手机', 1),
(3, '电脑', 1),
(4, '苹果手机', 2),
(5, '安卓手机', 2);

-- 递归查询：找出"电子产品"及其所有子分类
WITH RECURSIVE category_tree AS (
    -- 基础查询：起点
    SELECT id, name, parent_id, 1 AS level
    FROM categories WHERE id = 1

    UNION ALL

    -- 递归查询：找子节点
    SELECT c.id, c.name, c.parent_id, ct.level + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT REPEAT('  ', level - 1) || name AS 分类层级
FROM category_tree
ORDER BY level, id;
-- 结果：
-- 电子产品
--   手机
--     苹果手机
--     安卓手机
--   电脑
```

---

# 第五章：表设计与索引优化

## 5.1 数据库设计范式

### 三大范式速记

| 范式 | 核心要求 | 反例 |
|---|---|---|
| **1NF** | 列不可再分，每个字段是原子值 | `tags: "手机,数码,电子"` → 应该拆成标签表 |
| **2NF** | 非主键列完全依赖主键（不能部分依赖） | 订单明细表中存了商品名称（应只存 product_id） |
| **3NF** | 非主键列不依赖其他非主键列 | 表中存了 `birth_year` 和 `age`（age 可计算） |

### 实际项目中的权衡

```sql
-- 严格范式设计（多表关联）
CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT);
CREATE TABLE user_profiles (user_id INT PRIMARY KEY REFERENCES users(id), bio TEXT);
CREATE TABLE user_settings (user_id INT PRIMARY KEY REFERENCES users(id), theme TEXT);

-- 实际中常常适当反范式，减少 JOIN
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT,
    bio TEXT,          -- 合并在用户表
    theme TEXT,        -- 合并在用户表
    tags JSONB         -- 用 JSONB 存标签，避免多表 JOIN
);
```

## 5.2 常用字段设计模式

```sql
-- 企业项目中的标准表模板
CREATE TABLE products (
    -- 主键
    id              BIGSERIAL PRIMARY KEY,

    -- 业务字段
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    stock           INTEGER NOT NULL DEFAULT 0,

    -- 状态字段
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,  -- 软删除标记

    -- JSON 扩展字段（避免频繁改表结构）
    extra_info      JSONB DEFAULT '{}',

    -- 审计字段
    created_by      BIGINT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by      BIGINT,
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP  -- 软删除时间
);

-- 常用索引
CREATE INDEX idx_products_status ON products(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_products_name ON products USING gin(name gin_trgm_ops);  -- 模糊搜索
CREATE INDEX idx_products_extra ON products USING gin(extra_info);  -- JSONB 索引
```

## 5.3 索引优化实战

### B-Tree 索引（默认，最常用）

```sql
-- 单列索引：等值查询、范围查询
CREATE INDEX idx_users_email ON users(email);

-- 复合索引：最左前缀原则
CREATE INDEX idx_users_status_age ON users(status, age);
-- 命中索引：WHERE status = 'active'（使用索引第一列）
-- 命中索引：WHERE status = 'active' AND age > 20（使用两列）
-- 不命中：  WHERE age > 20（跳过了第一列！）

-- 部分索引：只索引部分数据
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';

-- 降序索引（PG 10+）
CREATE INDEX idx_users_created_desc ON users(created_at DESC);
```

### 索引使用原则

| 原则 | 说明 |
|---|---|
| **选择性高的列加索引** | 性别的选择性低（只有男/女），不适合加索引 |
| **WHERE/JOIN/ORDER BY 的列加索引** | 看查询条件 |
| **复合索引注意列顺序** | 等值查询的列放前面，范围查询的列放后面 |
| **不要过度索引** | 索引会减慢 INSERT/UPDATE/DELETE，占用空间 |
| **定期分析** | 用 EXPLAIN ANALYZE 检查索引是否被使用 |

### 查看索引使用情况

```sql
-- 查看表上的所有索引
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'users';

-- 查看索引大小
SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes WHERE tablename = 'users';

-- 查看未使用的索引
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

# 第六章：事务与并发控制

## 6.1 事务基础

事务是一组要么全部成功、要么全部失败的操作。ACID 是事务的四个核心特性。

```
┌─────────────────────────────────────────────────┐
│                    ACID                          │
│  A - Atomicity（原子性）：要么全做，要么全不做      │
│  C - Consistency（一致性）：事务前后数据一致       │
│  I - Isolation（隔离性）：并发事务互不干扰         │
│  D - Durability（持久性）：提交后数据永久保存      │
└─────────────────────────────────────────────────┘
```

```sql
-- 事务示例：转账操作
BEGIN;  -- 开始事务

-- 扣款
UPDATE accounts SET balance = balance - 100 WHERE id = 1;

-- 加款
UPDATE accounts SET balance = balance + 100 WHERE id = 2;

-- 检查余额不能为负
SELECT balance FROM accounts WHERE id = 1;
-- 如果余额 < 0，则 ROLLBACK，否则 COMMIT

COMMIT;  -- 提交事务（或 ROLLBACK 回滚）
```

## 6.2 Spring Boot 中的事务

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;
    private final InventoryRepository inventoryRepository;

    @Transactional  // 这个方法在事务中执行
    public Order createOrder(CreateOrderRequest request) {
        // 1. 创建订单
        Order order = new Order();
        order.setUserId(request.getUserId());
        order.setAmount(request.getAmount());
        order = orderRepository.save(order);

        // 2. 扣减库存
        for (OrderItemRequest item : request.getItems()) {
            int updated = inventoryRepository.decreaseStock(
                item.getProductId(), item.getQuantity());
            if (updated == 0) {
                // 库存不足，抛出异常 → 事务自动回滚！
                throw new BusinessException("库存不足，商品ID: " + item.getProductId());
            }
        }

        // 3. 保存订单明细
        // ... 如果这里抛异常，前面的订单和库存操作都会回滚

        return order;
    }
}
```

### @Transactional 关键属性

```java
// 默认：只回滚 RuntimeException 和 Error
@Transactional
public void method1() { ... }

// 指定回滚的异常
@Transactional(rollbackFor = Exception.class)
public void method2() { ... }

// 只读事务（优化性能，不能有写操作）
@Transactional(readOnly = true)
public List<User> listUsers() { ... }

// 事务传播行为
@Transactional(propagation = Propagation.REQUIRES_NEW)  // 新开事务
public void method3() { ... }

// 超时设置（秒）
@Transactional(timeout = 30)
public void method4() { ... }
```

## 6.3 事务隔离级别

```sql
-- PostgreSQL 默认隔离级别：READ COMMITTED
-- 查看当前隔离级别
SHOW transaction_isolation;

-- 设置隔离级别
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | PG 默认 |
|---|---|---|---|---|
| READ UNCOMMITTED | 可能 | 可能 | 可能 | ❌ PG 不支持 |
| READ COMMITTED | 不会 | 可能 | 可能 | ✅ 默认 |
| REPEATABLE READ | 不会 | 不会 | 可能 | |
| SERIALIZABLE | 不会 | 不会 | 不会 | 最严格 |

## 6.4 乐观锁与悲观锁

```sql
-- 悲观锁：查询时锁定行，其他人无法修改
SELECT * FROM products WHERE id = 1 FOR UPDATE;  -- 排他锁
SELECT * FROM products WHERE id = 1 FOR SHARE;   -- 共享锁

-- 乐观锁：用版本号检测冲突
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    stock INTEGER,
    version INTEGER DEFAULT 0  -- 版本号
);

-- 更新时检查版本号
UPDATE products
SET stock = stock - 1, version = version + 1
WHERE id = 1 AND version = 0;  -- 只有版本号匹配才更新
-- 如果返回 0 行，说明被别人改过了，需要重试
```

```java
// Spring Data JPA 乐观锁
@Entity
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Integer stock;

    @Version  // JPA 乐观锁注解
    private Integer version;
}
// 当 version 不匹配时，JPA 自动抛出 OptimisticLockException
```

---

# 第七章：PostgreSQL 高级特性

## 7.1 JSONB 操作

JSONB 是 PostgreSQL 的核心竞争力之一，让你在关系型数据库中像使用 MongoDB 一样操作 JSON。

```sql
-- 创建包含 JSONB 列的表
CREATE TABLE event_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    payload JSONB,  -- JSONB 列
    created_at TIMESTAMP DEFAULT NOW()
);

-- 插入 JSON 数据
INSERT INTO event_logs (event_type, payload) VALUES
('user_login', '{"user_id": 1, "ip": "192.168.1.1", "device": "chrome"}'),
('page_view', '{"user_id": 1, "page": "/home", "duration_ms": 3500}'),
('purchase', '{"user_id": 2, "product": {"id": 100, "name": "手机"}, "amount": 4999}');

-- JSONB 查询操作符
-- ->  返回 JSON 对象
-- ->> 返回文本
-- @>  包含运算符（左侧是否包含右侧）
-- ?   键是否存在

-- 查询 payload 中 user_id 为 1 的记录
SELECT * FROM event_logs WHERE payload->>'user_id' = '1';

-- 查询 payload 包含指定键的记录
SELECT * FROM event_logs WHERE payload ? 'device';

-- 查询 payload 包含指定子对象的记录
SELECT * FROM event_logs WHERE payload @> '{"user_id": 1}';

-- 提取嵌套 JSON 字段
SELECT
    id,
    event_type,
    payload->>'user_id' AS user_id,
    payload->'product'->>'name' AS product_name,
    payload->>'amount' AS amount
FROM event_logs
WHERE event_type = 'purchase';

-- JSONB 索引
CREATE INDEX idx_event_payload ON event_logs USING gin(payload);
-- 加速 @>, ?, ?|, ?& 操作符的查询

-- 更新 JSONB 字段
UPDATE event_logs
SET payload = payload || '{"updated": true}'  -- 合并 JSON
WHERE id = 1;

UPDATE event_logs
SET payload = jsonb_set(payload, '{device}', '"firefox"')  -- 修改嵌套字段
WHERE id = 1;
```

## 7.2 数组类型

```sql
-- 创建包含数组列的表
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    tags TEXT[]  -- 字符串数组
);

-- 插入数组
INSERT INTO articles (title, tags) VALUES
('PostgreSQL 教程', ARRAY['数据库', 'SQL', 'PG']),
('Spring Boot 教程', ARRAY['Java', '框架', '后端']);

-- 数组查询
SELECT * FROM articles WHERE 'SQL' = ANY(tags);  -- 包含 SQL 标签
SELECT * FROM articles WHERE tags @> ARRAY['Java'];  -- 包含 Java
SELECT * FROM articles WHERE tags && ARRAY['SQL', 'Java'];  -- 有交集

-- 数组操作
SELECT title, array_length(tags, 1) AS tag_count FROM articles;
SELECT title, UNNEST(tags) AS tag FROM articles;  -- 展开数组为行
```

## 7.3 全文搜索

```sql
-- 创建全文搜索配置
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    body TEXT,
    -- tsvector 是全文搜索向量
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', COALESCE(title, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(body, '')), 'B')
    ) STORED
);

-- 创建 GIN 索引加速全文搜索
CREATE INDEX idx_documents_search ON documents USING gin(search_vector);

-- 全文搜索查询
SELECT title,
       ts_rank(search_vector, query) AS rank  -- 相关性排名
FROM documents,
     plainto_tsquery('simple', 'PostgreSQL 数据库') AS query
WHERE search_vector @@ query
ORDER BY rank DESC;
```

## 7.4 常用内置函数

```sql
-- 字符串函数
SELECT UPPER('hello');              -- 'HELLO'
SELECT LOWER('HELLO');              -- 'hello'
SELECT LENGTH('你好');              -- 2
SELECT TRIM('  hello  ');          -- 'hello'
SELECT REPLACE('hello world', 'world', 'PG');  -- 'hello PG'
SELECT SPLIT_PART('a,b,c', ',', 2); -- 'b'（按分隔符取第n部分）
SELECT CONCAT('a', '-', 'b');       -- 'a-b'
SELECT FORMAT('用户：%s，年龄：%s', '张三', 25);  -- 格式化字符串

-- 日期函数
SELECT NOW();                              -- 当前时间戳
SELECT CURRENT_DATE;                       -- 当前日期
SELECT DATE_TRUNC('month', NOW());         -- 截断到月初
SELECT EXTRACT(YEAR FROM NOW());           -- 提取年份
SELECT AGE(NOW(), '2026-01-01');           -- 时间差
SELECT NOW() + INTERVAL '7 days';          -- 7天后
SELECT NOW() - INTERVAL '1 month';         -- 1个月前
SELECT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS');  -- 格式化输出

-- 数学函数
SELECT ABS(-10);                    -- 10
SELECT ROUND(3.14159, 2);           -- 3.14
SELECT CEIL(3.14);                  -- 4（向上取整）
SELECT FLOOR(3.14);                 -- 3（向下取整）
SELECT RANDOM();                    -- 0~1 随机数
SELECT GREATEST(10, 20, 5);         -- 20（最大值）
SELECT LEAST(10, 20, 5);            -- 5（最小值）

-- 类型转换
SELECT CAST('123' AS INTEGER);      -- 强制转换
SELECT '123'::INTEGER;              -- PG 简写（推荐）
SELECT COALESCE(NULL, NULL, '默认值');  -- 返回第一个非 NULL 值
SELECT NULLIF(0, 0);                -- 相等返回 NULL，否则返回第一个值
```

---

# 第八章：Spring Boot 集成 PostgreSQL

## 8.1 添加依赖

```xml
<!-- pom.xml -->
<dependencies>
    <!-- Spring Data JPA -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>

    <!-- PostgreSQL 驱动 -->
    <dependency>
        <groupId>org.postgresql</groupId>
        <artifactId>postgresql</artifactId>
    </dependency>

    <!-- 连接池（HikariCP，Spring Boot 默认，性能最好） -->
    <!-- 已包含在 spring-boot-starter-data-jpa 中，无需额外添加 -->
</dependencies>
```

## 8.2 配置 application.yml

```yaml
spring:
  datasource:
    # PostgreSQL 连接 URL 格式：jdbc:postgresql://主机:端口/数据库名
    url: jdbc:postgresql://localhost:5432/mydb
    username: myuser
    password: mypassword
    driver-class-name: org.postgresql.Driver

    # HikariCP 连接池配置（Spring Boot 默认连接池）
    hikari:
      minimum-idle: 5                       # 最小空闲连接数
      maximum-pool-size: 20                 # 最大连接数
      idle-timeout: 300000                  # 空闲超时（毫秒）
      max-lifetime: 1200000                 # 连接最大生命周期
      connection-timeout: 30000             # 连接超时
      pool-name: HikariPool                 # 连接池名称

  jpa:
    # 数据库方言（PostgreSQL 专用）
    database-platform: org.hibernate.dialect.PostgreSQLDialect

    # DDL 策略（开发用 update，生产用 validate 或 none）
    hibernate:
      ddl-auto: update

    # 打印 SQL（开发环境开启，生产环境关闭）
    show-sql: true
    properties:
      hibernate:
        format_sql: true                    # 格式化 SQL
        # 批量操作优化
        jdbc:
          batch_size: 20                    # 批量插入大小
        order_inserts: true                 # 排序插入语句
        order_updates: true                 # 排序更新语句

# 日志配置
logging:
  level:
    org.hibernate.SQL: DEBUG                # 打印 SQL
    org.hibernate.type.descriptor.sql: TRACE  # 打印 SQL 参数绑定值
    org.hibernate.engine.transaction: DEBUG # 打印事务日志
```

## 8.3 Entity 实体类映射

```java
package com.example.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "users")           // 映射到 users 表
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@DynamicUpdate                   // 只更新变化的字段
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)  // 自增主键
    private Long id;

    @Column(nullable = false, length = 50, unique = true)
    private String username;

    @Column(nullable = false, length = 100, unique = true)
    private String email;

    @Column(nullable = false)
    private String password;

    @Column(columnDefinition = "VARCHAR(20) DEFAULT 'active'")
    private String status;

    // JSONB 映射
    @Column(columnDefinition = "JSONB DEFAULT '{}'")
    @JdbcTypeCode(SqlTypes.JSON)  // Hibernate 6+ 需要
    private Map<String, Object> extraInfo;

    // 软删除标记
    @Column(nullable = false)
    @Builder.Default
    private Boolean isDeleted = false;

    @CreationTimestamp  // 自动设置创建时间
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp    // 自动设置更新时间
    private LocalDateTime updatedAt;

    @Column
    private LocalDateTime deletedAt;
}
```

## 8.4 Repository 接口

```java
package com.example.demo.repository;

import com.example.demo.entity.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long>,
                                         JpaSpecificationExecutor<User> {  // 支持动态查询

    // ===== 方法命名查询（Spring Data JPA 自动生成 SQL） =====

    // 精确匹配
    Optional<User> findByEmail(String email);
    Optional<User> findByUsername(String username);

    // 模糊搜索
    List<User> findByUsernameContaining(String keyword);

    // 多条件 AND
    List<User> findByStatusAndAgeGreaterThan(String status, int age);

    // IN 查询
    List<User> findByIdIn(List<Long> ids);

    // 排序
    List<User> findByStatusOrderByCreatedAtDesc(String status);

    // 分页
    Page<User> findByStatus(String status, Pageable pageable);

    // 存在性判断
    boolean existsByEmail(String email);

    // 计数
    long countByStatus(String status);

    // ===== JPQL 查询（面向实体，不是表） =====

    @Query("SELECT u FROM User u WHERE u.email LIKE %:domain%")
    List<User> findByEmailDomain(@Param("domain") String domain);

    @Query("SELECT u FROM User u WHERE u.createdAt > :since")
    List<User> findRecentlyCreated(@Param("since") LocalDateTime since);

    // ===== 原生 SQL 查询 =====

    @Query(value = "SELECT * FROM users WHERE age BETWEEN :min AND :max",
           nativeQuery = true)
    List<User> findByAgeRange(@Param("min") int min, @Param("max") int max);

    // ===== 更新操作（需要 @Modifying） =====

    @Modifying
    @Transactional
    @Query("UPDATE User u SET u.status = :status WHERE u.id = :id")
    int updateStatus(@Param("id") Long id, @Param("status") String status);

    @Modifying
    @Transactional
    @Query("UPDATE User u SET u.isDeleted = true, u.deletedAt = NOW() WHERE u.id = :id")
    int softDelete(@Param("id") Long id);
}
```

## 8.5 动态查询（Specification）

当前端传多个可选筛选条件时，需要动态拼接查询条件。

```java
// 在 Service 中使用 Specification 动态查询
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;

    public Page<User> searchUsers(UserSearchRequest request) {
        Specification<User> spec = (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();

            // 条件拼接：只有传了值才加条件
            if (StringUtils.hasText(request.getUsername())) {
                predicates.add(cb.like(root.get("username"),
                    "%" + request.getUsername() + "%"));
            }

            if (StringUtils.hasText(request.getEmail())) {
                predicates.add(cb.like(root.get("email"),
                    "%" + request.getEmail() + "%"));
            }

            if (request.getStatus() != null) {
                predicates.add(cb.equal(root.get("status"), request.getStatus()));
            }

            if (request.getMinAge() != null) {
                predicates.add(cb.greaterThanOrEqualTo(root.get("age"),
                    request.getMinAge()));
            }

            if (request.getMaxAge() != null) {
                predicates.add(cb.lessThanOrEqualTo(root.get("age"),
                    request.getMaxAge()));
            }

            // 软删除过滤
            predicates.add(cb.equal(root.get("isDeleted"), false));

            return cb.and(predicates.toArray(new Predicate[0]));
        };

        Pageable pageable = PageRequest.of(
            request.getPage(),
            request.getSize(),
            Sort.by(Sort.Direction.DESC, "createdAt")
        );

        return userRepository.findAll(spec, pageable);
    }
}
```

## 8.6 JSONB 字段的 Spring Data JPA 处理

```java
// Entity
@Entity
@Table(name = "event_logs")
@Data
public class EventLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String eventType;

    @Column(columnDefinition = "JSONB")
    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> payload;

    private LocalDateTime createdAt;
}

// Repository：JSONB 查询需要使用原生 SQL
@Repository
public interface EventLogRepository extends JpaRepository<EventLog, Long> {

    // 查询 JSONB 中的字段
    @Query(value = "SELECT * FROM event_logs WHERE payload->>'user_id' = :userId",
           nativeQuery = true)
    List<EventLog> findByUserId(@Param("userId") String userId);

    // JSONB 包含查询
    @Query(value = "SELECT * FROM event_logs WHERE payload @> CAST(:json AS JSONB)",
           nativeQuery = true)
    List<EventLog> findByPayloadContains(@Param("json") String json);
    // 调用：findByPayloadContains("{\"user_id\": 1}")
}
```

---

# 第九章：实战案例——完整 CRUD 开发

本章用一个完整的"商品管理"案例，串联前面所有知识点。

## 9.1 数据库初始化 SQL

```sql
-- 创建商品表
CREATE TABLE products (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    price       DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category    VARCHAR(50),
    tags        JSONB DEFAULT '[]',
    status      VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_deleted  BOOLEAN NOT NULL DEFAULT FALSE,
    created_by  BIGINT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by  BIGINT,
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_products_status ON products(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_name ON products USING gin(name gin_trgm_ops);
CREATE INDEX idx_products_tags ON products USING gin(tags);

-- 创建商品操作日志表
CREATE TABLE product_logs (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT NOT NULL REFERENCES products(id),
    action      VARCHAR(20) NOT NULL,  -- CREATE, UPDATE, DELETE, STATUS_CHANGE
    old_data    JSONB,
    new_data    JSONB,
    operated_by BIGINT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_logs_product ON product_logs(product_id, created_at DESC);

-- 插入测试数据
INSERT INTO products (name, description, price, stock, category, tags, status) VALUES
('iPhone 15', '苹果最新款手机', 6999.00, 100, '电子产品', '["手机","苹果","5G"]', 'active'),
('MacBook Pro', '苹果笔记本电脑', 14999.00, 50, '电子产品', '["电脑","苹果","M3芯片"]', 'active'),
('华为 Mate 60', '华为旗舰手机', 5999.00, 80, '电子产品', '["手机","华为","5G"]', 'active'),
('小米 14', '小米数字旗舰', 3999.00, 120, '电子产品', '["手机","小米","徕卡"]', 'active'),
('索尼 WH-1000XM5', '降噪耳机', 2499.00, 200, '电子产品', '["耳机","索尼","降噪"]', 'active');
```

## 9.2 Spring Boot 完整代码

### Entity

```java
@Entity
@Table(name = "products")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@DynamicUpdate
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 200)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal price;

    @Column(nullable = false)
    @Builder.Default
    private Integer stock = 0;

    @Column(length = 50)
    private String category;

    @Column(columnDefinition = "JSONB DEFAULT '[]'")
    @JdbcTypeCode(SqlTypes.JSON)
    private List<String> tags;

    @Column(nullable = false, length = 20)
    @Builder.Default
    private String status = "draft";

    @Column(nullable = false)
    @Builder.Default
    private Boolean isDeleted = false;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    @Column
    private LocalDateTime deletedAt;
}
```

### DTO

```java
@Data
public class ProductSearchRequest {
    private String keyword;      // 商品名称模糊搜索
    private String category;     // 分类筛选
    private BigDecimal minPrice; // 最低价格
    private BigDecimal maxPrice; // 最高价格
    private String status;       // 状态筛选
    private String tag;          // 标签筛选
    @Builder.Default
    private int page = 0;
    @Builder.Default
    private int size = 20;
}

@Data
@Builder
public class ProductResponse {
    private Long id;
    private String name;
    private String description;
    private BigDecimal price;
    private Integer stock;
    private String category;
    private List<String> tags;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

### Repository

```java
@Repository
public interface ProductRepository extends JpaRepository<Product, Long>,
                                           JpaSpecificationExecutor<Product> {

    // 分类查询
    Page<Product> findByCategoryAndIsDeletedFalse(String category, Pageable pageable);

    // 价格范围
    List<Product> findByPriceBetweenAndIsDeletedFalse(BigDecimal min, BigDecimal max);

    // 库存不足
    @Query("SELECT p FROM Product p WHERE p.stock < :threshold AND p.isDeleted = false")
    List<Product> findLowStock(@Param("threshold") int threshold);

    // 原生 SQL：JSONB 标签查询
    @Query(value = "SELECT * FROM products WHERE tags @> CAST(:tag AS JSONB) AND is_deleted = false",
           nativeQuery = true)
    List<Product> findByTag(@Param("tag") String tag);
    // 调用：findByTag("[\"手机\"]")

    // 统计
    @Query("SELECT p.category, COUNT(p), AVG(p.price) FROM Product p " +
           "WHERE p.isDeleted = false GROUP BY p.category")
    List<Object[]> getCategoryStats();
}
```

### Service

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class ProductService {
    private final ProductRepository productRepository;

    @Transactional(readOnly = true)
    public Page<ProductResponse> search(ProductSearchRequest request) {
        Specification<Product> spec = buildSpecification(request);
        Pageable pageable = PageRequest.of(
            request.getPage(), request.getSize(),
            Sort.by(Sort.Direction.DESC, "createdAt"));
        return productRepository.findAll(spec, pageable).map(this::toResponse);
    }

    @Transactional(readOnly = true)
    public ProductResponse findById(Long id) {
        Product product = productRepository.findById(id)
            .filter(p -> !p.getIsDeleted())
            .orElseThrow(() -> new NotFoundException("商品不存在，ID: " + id));
        return toResponse(product);
    }

    @Transactional
    public ProductResponse create(ProductCreateRequest request) {
        Product product = Product.builder()
            .name(request.getName())
            .description(request.getDescription())
            .price(request.getPrice())
            .stock(request.getStock())
            .category(request.getCategory())
            .tags(request.getTags())
            .status("active")
            .build();
        return toResponse(productRepository.save(product));
    }

    @Transactional
    public ProductResponse update(Long id, ProductUpdateRequest request) {
        Product product = productRepository.findById(id)
            .filter(p -> !p.getIsDeleted())
            .orElseThrow(() -> new NotFoundException("商品不存在，ID: " + id));

        if (request.getName() != null) product.setName(request.getName());
        if (request.getDescription() != null) product.setDescription(request.getDescription());
        if (request.getPrice() != null) product.setPrice(request.getPrice());
        if (request.getStock() != null) product.setStock(request.getStock());
        if (request.getCategory() != null) product.setCategory(request.getCategory());
        if (request.getTags() != null) product.setTags(request.getTags());

        return toResponse(productRepository.save(product));
    }

    @Transactional
    public void delete(Long id) {
        Product product = productRepository.findById(id)
            .filter(p -> !p.getIsDeleted())
            .orElseThrow(() -> new NotFoundException("商品不存在，ID: " + id));
        product.setIsDeleted(true);
        product.setDeletedAt(LocalDateTime.now());
        productRepository.save(product);
    }

    private Specification<Product> buildSpecification(ProductSearchRequest request) {
        return (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();
            predicates.add(cb.equal(root.get("isDeleted"), false));

            if (StringUtils.hasText(request.getKeyword())) {
                predicates.add(cb.like(root.get("name"), "%" + request.getKeyword() + "%"));
            }
            if (StringUtils.hasText(request.getCategory())) {
                predicates.add(cb.equal(root.get("category"), request.getCategory()));
            }
            if (StringUtils.hasText(request.getStatus())) {
                predicates.add(cb.equal(root.get("status"), request.getStatus()));
            }
            if (request.getMinPrice() != null) {
                predicates.add(cb.greaterThanOrEqualTo(root.get("price"), request.getMinPrice()));
            }
            if (request.getMaxPrice() != null) {
                predicates.add(cb.lessThanOrEqualTo(root.get("price"), request.getMaxPrice()));
            }
            return cb.and(predicates.toArray(new Predicate[0]));
        };
    }

    private ProductResponse toResponse(Product p) {
        return ProductResponse.builder()
            .id(p.getId()).name(p.getName()).description(p.getDescription())
            .price(p.getPrice()).stock(p.getStock()).category(p.getCategory())
            .tags(p.getTags()).status(p.getStatus())
            .createdAt(p.getCreatedAt()).updatedAt(p.getUpdatedAt())
            .build();
    }
}
```

---

# 第十章：SQL 调试与性能排查

## 10.1 EXPLAIN ANALYZE——性能分析利器

```sql
-- 基础用法：查看执行计划
EXPLAIN SELECT * FROM products WHERE category = '电子产品';

-- 实际执行并统计（推荐）
EXPLAIN ANALYZE SELECT * FROM products WHERE category = '电子产品';

-- 更详细的输出
EXPLAIN (ANALYZE, BUFFERS, TIMING, FORMAT JSON)
SELECT p.*, u.username
FROM products p
JOIN users u ON p.created_by = u.id
WHERE p.price > 1000;
```

### 执行计划解读

```sql
-- 示例输出
EXPLAIN ANALYZE
SELECT * FROM products WHERE category = '电子产品' AND price > 5000;

-- 输出解读：
-- Seq Scan on products (cost=0.00..25.00 rows=3 width=500)
--   (actual time=0.050..0.120 rows=3 loops=1)
--   Filter: (price > 5000)
--   Rows Removed by Filter: 2
-- Planning Time: 0.150 ms
-- Execution Time: 0.140 ms

-- 关键指标：
-- Seq Scan        → 全表扫描（没有用到索引，需要优化）
-- Index Scan      → 索引扫描（用到了索引）
-- Bitmap Index Scan → 位图索引扫描（适合返回较多行）
-- cost=0.00..25.00 → 启动成本..总成本（越小越好）
-- rows=3          → 预估返回行数
-- actual rows=3   → 实际返回行数（差距大说明统计信息不准）
-- Execution Time  → 实际执行时间
```

### 常见慢查询模式

| 执行计划关键词 | 含义 | 优化方向 |
|---|---|---|
| `Seq Scan` | 全表扫描 | 加索引 |
| `Nested Loop` | 嵌套循环 JOIN | 加索引或改写 SQL |
| `Hash Join` | 哈希 JOIN | 通常没问题 |
| `Sort` | 排序 | 加索引覆盖排序字段 |
| `Rows Removed by Filter` 很大 | 过滤了大量数据 | 加更精准的索引 |

## 10.2 慢查询定位

```sql
-- 1. 开启慢查询日志（postgresql.conf 或会话级别）
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 超过 1 秒的查询记录日志
SELECT pg_reload_conf();  -- 重新加载配置

-- 2. 查看当前正在执行的查询
SELECT pid, now() - pg_stat_activity.query_start AS duration,
       query, state
FROM pg_stat_activity
WHERE state != 'idle' AND pid != pg_backend_pid()
ORDER BY duration DESC;

-- 3. 杀掉长时间运行的查询
SELECT pg_terminate_backend(pid);  -- 替换 pid 为实际进程 ID

-- 4. 查看锁等待
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_locks blocked_locks
JOIN pg_locks blocking_locks
    ON blocked_locks.lock_type = blocking_locks.lock_type
    AND blocked_locks.relation = blocking_locks.relation
    AND blocked_locks.pid != blocking_locks.pid
JOIN pg_stat_activity blocked_activity
    ON blocked_locks.pid = blocked_activity.pid
JOIN pg_stat_activity blocking_activity
    ON blocking_locks.pid = blocking_activity.pid
WHERE NOT blocked_locks.granted;
```

## 10.3 常见性能问题及解决方案

### 问题一：N+1 查询

```java
// ❌ 错误写法：N+1 查询
// 查询所有订单，然后每个订单再查一次用户
List<Order> orders = orderRepository.findAll();
for (Order order : orders) {
    User user = userRepository.findById(order.getUserId()).orElse(null);
    // 如果 orders 有 100 条，这里会执行 101 次 SQL！
}

// ✅ 正确写法1：JOIN 查询
@Query("SELECT o FROM Order o JOIN FETCH o.user WHERE o.status = :status")
List<Order> findOrdersWithUser(@Param("status") String status);

// ✅ 正确写法2：EntityGraph
@Entity
@NamedEntityGraph(name = "Order.user", attributeNodes = @NamedAttributeNode("user"))
public class Order { ... }

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    @EntityGraph("Order.user")
    List<Order> findByStatus(String status);
}
```

### 问题二：批量插入慢

```java
// ❌ 循环单条插入（100 条数据 = 100 次 SQL）
for (Product product : products) {
    productRepository.save(product);
}

// ✅ 批量插入（100 条数据 = 1 次 SQL）
productRepository.saveAll(products);
```

```yaml
# 同时在 application.yml 中配置批量操作优化
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 50
        order_inserts: true
```

### 问题三：忘记加索引

```sql
-- 查找缺少索引的慢查询
-- 1. 查看全表扫描的表
SELECT schemaname, tablename,
       seq_scan, seq_tup_read,
       idx_scan, idx_tup_fetch,
       seq_scan / NULLIF(idx_scan + 1, 0) AS ratio
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_scan DESC;
-- ratio 越高，说明全表扫描越多，越需要加索引

-- 2. 查看哪些查询走了全表扫描
-- 通过 EXPLAIN ANALYZE 逐个分析慢查询
```

## 10.4 数据库维护

```sql
-- 更新统计信息（查询计划优化依赖准确的统计信息）
ANALYZE products;

-- 查看表大小
SELECT pg_size_pretty(pg_total_relation_size('products'));

-- 查看所有表大小
SELECT tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 重建索引（索引膨胀时）
REINDEX INDEX idx_products_name;

-- 清理死元组（PG 的 MVCC 会产生死元组，定期清理）
VACUUM ANALYZE products;
-- 或使用自动清理（默认开启）
```

---

# 第十一章：常见问题与避坑指南

## 11.1 前端开发者的 SQL 常见错误

| 错误 | 原因 | 正确做法 |
|---|---|---|
| `WHERE email = NULL` | NULL 不能用等号比较 | `WHERE email IS NULL` |
| `WHERE id = '123'` | 字符串和数字比较 | `WHERE id = 123`（类型匹配） |
| `DELETE FROM users` 忘加 WHERE | 删了全表！ | 先 `SELECT` 确认，再 `DELETE` |
| `UPDATE users SET status='active'` 忘加 WHERE | 更新了全表！ | 先 `SELECT` 确认，加 `WHERE id = ?` |
| `SELECT * FROM users LIMIT 100` 没有 ORDER BY | 返回结果不确定 | 加 `ORDER BY id`，保证分页一致性 |
| 字符串拼接 SQL | SQL 注入风险！ | 用参数化查询（JPA 自动处理） |
| `varchar(255)` 存中文超长 | 中文占多个字节 | 用 `TEXT` 类型，或增大 varchar 长度 |
| 忘记事务 | 操作一半失败，数据不一致 | Service 方法加 `@Transactional` |

## 11.2 Spring Data JPA 常见坑

### 坑一：save 方法不一定是 INSERT

```java
// save() 的行为：
// - 如果 Entity 的 id 为 null → INSERT
// - 如果 Entity 的 id 不为 null → 先 SELECT 再 INSERT 或 UPDATE
// 批量操作时用 saveAll() 更好
```

### 坑二：getOne vs findById

```java
// getOne() 返回代理对象，延迟加载。如果不存在，调用 getXxx() 时才报错
User user = userRepository.getOne(999L);  // 不报错
user.getName();  // 这里才报 EntityNotFoundException！

// findById() 返回 Optional，立即查询
Optional<User> user = userRepository.findById(999L);  // 立即查询
// 推荐始终使用 findById()
```

### 坑三：@Transactional 自调用失效

```java
@Service
public class UserService {

    // 直接调用 methodB() 事务不生效！
    public void methodA() {
        this.methodB();  // 直接调用，绕过了 AOP 代理
    }

    @Transactional
    public void methodB() {
        // 事务不会生效！
    }
}

// 解决方案：注入自己，通过代理调用
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserService self;  // 注入自己（需要 @Lazy）

    public void methodA() {
        self.methodB();  // 通过代理调用，事务生效
    }

    @Transactional
    public void methodB() { ... }
}
```

## 11.3 PostgreSQL 特有注意事项

```sql
-- 1. 引号：单引号是字符串，双引号是标识符
SELECT * FROM "Users" WHERE name = '张三';
-- "Users" 表示表名严格区分大小写，'张三' 是字符串

-- 2. PostgreSQL 默认将未加引号的标识符转为小写
CREATE TABLE MyTable (...);  -- 实际创建的是 mytable
SELECT * FROM MyTable;       -- 实际查询的是 mytable
-- 建议：始终用小写命名表名和列名

-- 3. SERIAL 不是真正的类型
-- SERIAL 等价于：INTEGER + 自动创建序列 + 设置默认值

-- 4. 序列问题
-- 手动插入 id 后，序列不会自动更新
SELECT setval('products_id_seq', (SELECT MAX(id) FROM products));
-- 或使用 IDENTITY 列（PG 10+）
-- id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
```

## 11.4 调试 SQL 的快速检查清单

```
遇到数据库相关问题时，按以下顺序排查：

□ 1. 看控制台 SQL 日志
   → 确认 SQL 是否正确执行了
   → 看参数值是否正确

□ 2. 复制 SQL 到数据库工具中执行
   → 看 SQL 本身是否有语法错误
   → 看执行结果是否符合预期

□ 3. 用 EXPLAIN ANALYZE 分析
   → 看是否走了索引
   → 看执行时间是否正常

□ 4. 检查数据
   → 数据是否存在（SELECT COUNT(*) ...）
   → 数据是否正确（字段值、关联关系）
   → 是否有脏数据

□ 5. 检查连接
   → 数据库是否可达（ping / telnet）
   → 连接池是否耗尽（HikariCP 日志）
   → 连接数是否超限（pg_stat_activity）

□ 6. 检查事务
   → 是否有未提交的事务锁住了数据
   → 事务隔离级别是否合适
   → 是否有死锁
```

---

## 📋 附录：常用 SQL 速查表

```sql
-- ===== 表操作 =====
CREATE TABLE t (id SERIAL PRIMARY KEY, name TEXT);
ALTER TABLE t ADD COLUMN age INTEGER;
ALTER TABLE t ALTER COLUMN name TYPE VARCHAR(100);
ALTER TABLE t DROP COLUMN age;
DROP TABLE t;
TRUNCATE TABLE t;

-- ===== 索引操作 =====
CREATE INDEX idx_name ON t(name);
CREATE UNIQUE INDEX idx_name ON t(name);
CREATE INDEX idx_name ON t USING gin(name gin_trgm_ops);
DROP INDEX idx_name;

-- ===== 数据操作 =====
INSERT INTO t (name) VALUES ('test') RETURNING id;
SELECT * FROM t WHERE id = 1;
UPDATE t SET name = 'new' WHERE id = 1;
DELETE FROM t WHERE id = 1;

-- ===== 聚合 =====
SELECT COUNT(*), AVG(age), SUM(amount), MAX(price), MIN(price) FROM t;
SELECT category, COUNT(*) FROM t GROUP BY category;
SELECT category, COUNT(*) FROM t GROUP BY category HAVING COUNT(*) > 5;

-- ===== 日期 =====
SELECT NOW(), CURRENT_DATE, DATE_TRUNC('month', NOW());
SELECT NOW() - INTERVAL '7 days';
SELECT EXTRACT(YEAR FROM NOW());
SELECT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS');

-- ===== JSONB =====
SELECT payload->>'key' FROM t;
SELECT * FROM t WHERE payload @> '{"key": "value"}';
SELECT * FROM t WHERE payload ? 'key';
UPDATE t SET payload = payload || '{"new_key": "value"}';

-- ===== 事务 =====
BEGIN;
UPDATE ...;
COMMIT;  -- 或 ROLLBACK;

-- ===== 查询当前活动 =====
SELECT * FROM pg_stat_activity WHERE state = 'active';
SELECT pg_terminate_backend(pid);
```

---

> 📝 **最后的话**：学习数据库最好的方式就是多写 SQL。建议安装 DBeaver 或 DataGrip，连接到公司的开发数据库，把本文档中的 SQL 示例都跑一遍。遇到慢查询就用 `EXPLAIN ANALYZE` 分析，慢慢就能培养出 SQL 感觉。数据库是后端开发的基石，值得花时间深入掌握。