# MySQL 基础

## SQL 的概念

SQL(Structured Query Language) 结构化查询语言

SQL 是所有关系型数据库的查询规范，不同的数据库 SQL 语句有一些区别

SQL 语句分类:

1. Data Definition Language (DDL 数据定义语言) 如：建库，建表
2. Data Manipulation Language(DML 数据操作语言)，如：对表中的记录操作增删改
3. Data Query Language(DQL 数据查询语言)，如：对表中的查询操作
4. Data Control Language(DCL 数据控制语言)，如：对用户权限的设置

## DDL 操作数据库、表

常用的操作：CRUD

- Create 创建
- Retrieve 查询
- Update 修改
- Delete 删除

### 创建数据库

- 创建数据库: `CREATE DATABASE my_database;`

- 判断数据库是否存在，不存才创建：`CREATE DATABASE IF NOT EXISTS my_database;`

- 创建数据库并指定字符集：`CREATE DATABASE my_database CHARACTER SET 字符集;`

### 查询数据库

- 查看数据库：`SHOW DATABASES;`

- 查看某个数据库的定义信息：`SHOW CREATE DATABASE my_database;`

### 修改数据库

- 修改数据库默认字符集：`ALTER DATABASE my_database DEFAULT CHARACTER SET 字符集;`

### 删除数据库

- 删除数据库：`DROP DATABASE my_database;`

### 使用数据库

- 使用数据库：`USE my_database;`

- 查看正在使用的数据库: `SELECT DATABASE();`

### 查看表

- 查看表：`SHOW TABLES;`

- 查看表结构：`DESC my_table;`

### 创建表

- 创建表：

```SQL
CREATE TABLE my_table (
  id INT NOT NULL AUTO_INCREMENT,
  age INT NOT NULL DEFAULT 10,
  nick VARCHAR(45) NULL,
  score DOUBLE(5, 2),
  create_at DATE NULL,
  PRIMARY KEY (`id`));
```

### 修改表

- 添加列：`ALTER TABLE my_table ADD col CHAR(20);`

- 删除列： `ALTER TABLE my_table DROP COLUMN col;`

### 删除表

- 删除表：`DROP TABLE my_table;`

- 清空表： `TRUNCATE TABLE my_table;`

## 操作数据

### 插入数据

- 插入数据：`INSERT INTO my_table(col1, col2) VALUES(val1, val2);`

- 插入检索出来的数据: `INSERT INTO my_table1(col1, col2) SELECT col1, col2 FROM my_table2;`

- 将一个表的内容插入到一个新表：`CREATE TABLE new_table AS SELECT * FROM my_table;`

### 修改数据

- 更新数据：`UPDATE my_table SET col = val WHERE id = 1;`

### 删除数据

- 删除数据：`DELETE FROM my_table WHERE id = 1;`

## 查询数据

### 基本查询

- 基本查询： `SELECT * FROM my_table;`

### 条件查询

- 条件查询： `SELECT * FROM my_table WHERE id = 1;`

`WHERE` 子句可用的操作符：`=`、`<`、`>`、`!=`、`<=`、`>=`

`BETWEEN` 操作符用于匹配两个值之间

`IN` 操作符用于匹配一组值，其后也可以接一个 `SELECT` 子句

`AND`、 `OR` 用于连接多个查询条件

`NOT` 操作符用于否定一个查询条件

### 排序

`ASC`：升序(默认); `DESC`：降序

- 排序：`SELECT * FROM my_table ORDER BY col1 DESC, col2 ASC;`

### 通配符

使用 `Like` 来进行通配符匹配，通配符只能用于文本字段

`%` ：匹配任意字符

`_` ：匹配 1 个任意字符

`[ ]` ：匹配集合内的字符， `^` 可以对其进行否定，也就是不匹配集合内的字符

`SELECT * FROM my_table WHERE col LIKE '[^AB]%';` 不以 A 和 B 开头的任意文本

### 投影查询

让结果集仅包含指定列

- 投影查询：`SELECT col1, col2, col3 FROM my_table;`

### 分页查询

`LIMIT`：每页查询的数量；`OFFSET`：查询起始位置

查询起始位置 = 每页查询数量 \* (当前页数 - 1)

- 分页查询：`SELECT * FROM my_table LIMIT 10 OFFSET 0;`

### 聚合查询

聚合函数进行查询，可以快速获得结果

- 统计数量： `SELECT COUNT(*) count FROM my_table;`

- 合计： `SELECT SUM(score) sum FROM my_table;`

- 平均数：`SELECT AVG(score) avg FROM my_table;`

- 最大值：`SELECT MAX(score) max FROM my_table;`

- 最小值：`SELECT MIN(score) min FROM my_table;`

### 分组

- 分组： `SELECT col, COUNT(*) AS num FROM my_table GROUP BY col;`

分组规定：

`GROUP BY` 子句出现在 `WHERE` 子句之后，`ORDER BY` 子句之前

除了聚合函数外，`SELECT` 语句中的每一字段都必须在 `GROUP BY` 子句中给出

`NULL` 的行会单独分为一组

### 组合查询

使用 `UNION` 关键字来组合两个查询

默认会去除相同行，如果需要保留相同行，使用 `UNION ALL`

只能包含一个 `ORDER BY` 子句，并且必须位于语句的最后

```SQL
SELECT col
FROM my_table
WHERE col = 1
UNION
SELECT col
FROM my_table
WHERE col =2;
```

### 多表查询

- 多表查询：`SELECT * FROM table1, table2;`

结果集的列数是表 1 和表 2 的列数之和，行数是表 1 和表 2 的行数之积

### 连接查询

用于连接多个表，使用 `JOIN` 关键字，条件语句使用 `ON` 而不是 `WHERE`

#### 内连接

先确定主表 `FROM table_a`

再确定需要连接的表 `INNER JOIN table_b`

然后确定连接条件 `ON A.key = B.key`,

可以加上 `WHERE` 、`ORDER BY` 等子句

```SQL
SELECT A.value, B.value
FROM table_a AS A INNER JOIN table_b AS B
ON A.key = B.key;
```

#### 外连接

外连接分为左外连接，右外连接以及全外连接，外连接保留了没有连接的那些行

`LEFT OUTER JOIN`：左外连接，筛选出左表都存在的记录

`RIGHT OUTER JOIN`：右外连接，筛选出右表都存在的记录

`FULL OUTER JOIN`：全外连接，筛选出左右表都存在的记录

```SQL
# 左外连接
SELECT s.id, s.name, s.class_id, c.name class_name, s.gender, s.score
FROM students s
LEFT OUTER JOIN classes c
ON s.class_id = c.id;

# 右外连接
SELECT s.id, s.name, s.class_id, c.name class_name, s.gender, s.score
FROM students s
RIGHT OUTER JOIN classes c
ON s.class_id = c.id;

# 全外连接
SELECT s.id, s.name, s.class_id, c.name class_name, s.gender, s.score
FROM students s
FULL OUTER JOIN classes c
ON s.class_id = c.id;
```
