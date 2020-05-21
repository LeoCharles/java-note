# MySQL 基础

## SQL 的概念

SQL(Structured Query Language) 结构化查询语言

SQL 是所有关系型数据库的查询规范，不同的数据库 SQL 语句有一些区别

### SQL 语句分类

1. Data Definition Language (DDL 数据定义语言) 如：建库，建表
2. Data Manipulation Language(DML 数据操作语言)，如：对表中的记录操作增删改
3. Data Query Language(DQL 数据查询语言)，如：对表中的查询操作
4. Data Control Language(DCL 数据控制语言)，如：对用户权限的设置

## MySQL

### 登录

- 本地登录：`mysql -u 用户名 -p 密码`

- 远程登录：`mysql -h IP地址 -u 用户名 -p 密码`

- 退出登录：`quit 或 exit`

### 语法

每条语句以分号结尾，不区分大小写

三种注释：

- `--`: 单行注释，注意，`--` 后面需要有空格
- `/* */`：多行注释
- `#`：MySQL 特有的注释方式

## DDL 操作数据库

### 创建数据库

- 创建数据库: `CREATE DATABASE 数据库名;`

- 判断数据库是否存在，不存才创建：`CREATE DATABASE IF NOT EXISTS 数据库名;`

- 创建数据库并指定字符集：`CREATE DATABASE 数据库名 CHARACTER SET 字符集;`

### 查询数据库

- 查看数据库：`SHOW DATABASES;`

- 查看某个数据库的定义信息：`SHOW CREATE DATABASE 数据库名;`

### 修改数据库

- 修改数据库默认字符集：`ALTER DATABASE 数据库名 DEFAULT CHARACTER SET 字符集;`

### 删除数据库

- 删除数据库：`DROP DATABASE 数据库名;`

### 使用数据库

- 使用数据库：`USE 数据库名;`

- 查看正在使用的数据库: `SELECT DATABASE();`

## DDL 操作数据表

### MySQL 数据类型

- 整数
  - TINYINT：微整型
  - SMALLINT：小整型
  - MEDIUMINT：小整型
  - INT：整型
  - BIGINT：大整型
- 小数
  - FLOAT：单精度浮点数
  - DOUBLE：双精度浮点数
  - DECIMAL(M,D)：可变长度小数，依赖于 M 和 D 的值
- 日期/时间
  - YEAR：年，YYYY
  - TIME：时间，HH:MM:SS
  - DATE: 日期，YYYY-MM-DD
  - DATETIME：日期时间，YYYY-MM-DD HH:MM:SS
  - TIMESTAMP：时间戳
- 字符串
  - CHAR(M)：定长字符串
  - VARCHAR(M)：变长字符串
- 文本
  - TINYTEXT：小文本
  - TEXT：文本
  - MEDIUMTEX：中文本
  - LONGTEXT：文本
  - TEXT：文本
- 二进制数据
  - BINARY(M)：定长二进制数据
  - VARBINARY(M)：变长二进制数据
  - TINYBLOB：小的二进制大对象
  - BLOB：二进制大对象
  - MEDIUMBLOB：中等二进制大对象
  - LONGBLOB：大的二进制大对象

### 创建表

- 创建表：

```SQL
CREATE TABLE 表名 (
字段名 1 字段类型 1,
字段名 2 字段类型 2
);

CREATE TABLE STUDENTS (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(20),
  age INT,
  sex VARCHAR(5),
  address VARCHAR(100),
  math INT,
  english INT,
  PRIMARY KEY(`id`)); -- 设置主键
```

- 创建一个表结构相同的表：`CREATE TABLE 新表名 LIKE 旧表名;`

### 查看表

- 查看表：`SHOW TABLES;`

- 查看表结构：`DESC 表名;`

- 查看创建表的 SQL 语句：`SHOW CREATE TABLE 表名;`

### 修改表

- 修改表名：`RENAME TABLE 表名 TO 新表名;`

- 修改字符集：`ALTER TABLE 表名 character set 字符集;`

- 添加列：`ALTER TABLE 表名 ADD 列名 类型;`

- 删除列： `ALTER TABLE 表名 DROP COLUMN 列名;`

- 修改列名：`ALTER TABLE 表名 CHANGE 旧列名 新列名 类型;`

- 修改列类型：`ALTER TABLE 表名 MODIFY 列名 新的类型;`

### 删除表

- 删除表：`DROP TABLE 表名;`

- 先判断再删除表：`DROP TABLE IF EXISTS 表名;`

## DML 操作表中的数据

### 插入数据

- 插入数据：`INSERT INTO 表名(字段1, 字段2, ...) VALUES (值1, 值2, ...);`

- 将已存在的表的所有列插入到一个新表：`CREATE TABLE 表1 SELECT * FROM 表2;`

- 插入检索出来的数据: `INSERT INTO 表1(字段1, 字段2) SELECT 字段1, 字段2 FROM 表2;`

### 修改数据

- 更新数据：`UPDATE 表名 SET 列名=值 [WHERE 条件表达式];`

- 更新所有的数据：`UPDATE 表名 SET 字段名=值;`

### 删除数据

- 删除数据：`DELETE FROM 表名 [WHERE 条件表达式];`

- 清空表： `TRUNCATE TABLE 表名;`

## DQL 查询表中的数据

```SQL
SELECT 字段名 FROM 表名
WHERE 条件列表
GROUP BY 分组字段
HAVING 分组后过滤
ORDER BY 排序
LIMIT 分页
```

### 基本查询

- 基本查询： `SELECT * FROM 表名;`

- 查询指定列：`SELECT 字段1, 字段2, 字段3, ... FROM 表名;`

- 指定列的别名进行查询：`SELECT 字段1 AS 别名1, 字段2 AS 别名2, ... FROM 表名;` AS 可以省略

- 指定表别名：`SELECT 字段1 AS 别名1, 字段2 AS 别名2, ... FROM 表名 AS 表别名;`

- 去除重复值：`SELECT DISTINCT 字段名 FROM 表名;`

- 查询结果参与运算：`SELECT 字段1 + 固定值 FROM 表名;`

- 判断是否为NULL：`SELECT 字段1 + IFNULL(字段2, 0) FROM 表名;`

```SQL
-- 计算总成绩
SELECT name, math, english, IFNULL(math,0) + IFNULL(english, 0) AS sum FROM students;
```

### 条件查询

条件查询： `SELECT 字段名 FROM 表名 WHERE 条件;`

- 比较运算符

`=`、`<`、`>`、`!=`、`<>`、 `<=`、`>=`

- 逻辑运算符

`OR`、`AND` 、`NOT`

- IN 关键字

`SELECT 字段名 FROM 表名 WHERE 字段 IN (值1, 值2, ...);`：匹配集合中的每一个值作为查询条件

- 范围查询

`SELECT 字段名 FROM 表名 WHERE 字段 BETWEEN 值1 AND 值2;`：在一个范围之内匹配，头和尾都包含

- 判断为空或不为空

`SELECT 字段名 FROM 表名 WHERE 字段 IS NULL;`

`SELECT 字段名 FROM 表名 WHERE 字段 IS NOT NULL;`

- 模糊查询

`SELECT * FROM 表名 WHERE 字段名 LIKE '通配符字符串';`：模糊查询，通配符只能用于文本字段

`%` ：匹配任意字符；`_` ：匹配一个字符

```SQL
-- 查询 age 不等于 20 岁的学生，注：不等于有两种写法
SELECT * FROM STUDENTS WHERE age <> 20;
SELECT * FROM STUDENTS WHERE age != 20;

-- 查询 age 大于 35 且性别为男的学生
SELECT * FROM students WHERE age > 35 AND sex = '男';
-- 查询 math 不为 NULL
SELECT * FROM students WHERE english IS NOT NULL;

-- 查询 id 是 1 或 3 或 5 的学生
SELECT * FROM students WHERE id IN(1, 3, 5);
-- 查询 id 不是 1 或 3 或 5 的学生
SELECT * FROM students WHERE id NOT IN(1, 3, 5);

-- 查询 english 成绩大于等于 75，且小于等于 90 的学生
SELECT * FROM students WHERE english BETWEEN 75 AND 90;

-- 查询姓刘的学生
SELECT * FROM students WHERE name LIKE '刘%';

-- 查询姓刘，且姓名有两个字的学生
SELECT * FROM students WHERE name LIKE '刘_';
```

### 排序

`SELECT * FROM 表名 ORDER BY 字段名 [ASC|DESC];`： 将查询的结果按指定的字段进行排序

`SELECT * FROM 表名 ORDER BY 字段1 [ASC|DESC], 字段2 [ASC|DESC];`：组合排序，如果第 1 个字段相等，则按第 2 个字段排序

`ASC`：升序(默认); `DESC`：降序

```SQL
-- 查询所有学生，年龄降序排序
SELECT * FROM students ORDER BY age DESC;

-- 查询所有学生，在年龄降序排序的基础上，再以数学成绩升序排序
SELECT * FROM students ORDER BY age DESC, math ASC;
```

### 聚合函数

聚合函数将一列数据作为一个整体进行纵向的计算。

聚合函数会排除 NULL 值， 可以使用 `IFNULL()` 函数设置一个默认值在计算

- `COUNT(字段名)`：统计数量

- `SUM(字段名)`：总和

- `AVG(字段名)`：平均数

- `MAX(字段名)`：最大值

- `MIN(字段名)`：最小值

```SQL
-- 查询学生总数
SELECT COUNT(*) AS total FROM students;

-- 统计 id 字段，如果为 null，则使用 0 代替
SELECT COUNT(IFNULL(id, 0)) AS total FROM students;

-- 查询数学成绩最高分
SELECT MAX(math) FROM students;
```

### 分组

`SELECT 分组字段 FROM 表名 GROUP BY 分组字段 [HAVING 条件];`

将查询结果按照指定的字段进行分组，并且返回每组的第一条数据

单独使用分组没有用，一般配合聚合函数一起使用

`HAVING` 和 `WHERE` 的区别:

`WHERE` 子句：先过滤再分组，后面不可以使用聚合函数

`HAVING` 子句：先分组再过滤，后面可以使用聚合函数

执行顺序: `WHERE` -> `GROUP BY` -> `HAVING` -> `ORDER BY` -> `LIMIT`

```SQL
-- 按性别分组，并分别统计数学平均分
SELECT sex, AVG(math) AS math_avg FROM students GROUP BY sex;

-- 按性别分组, 低于70分不参与分组，再统计数学平均分
SELECT sex, AVG(math) math_avg FROM students WHERE math > 70 GROUP BY sex;

-- 查询年龄大于 16 的学生，按地址分组，计算每组学生的数学平均分，筛选平均分大于 60 的分组，按平均分降序排序
SELECT address, AVG(math) math_avg FROM students
WHERE age > 16
GROUP BY address
HAVING math_avg > 60
ORDER BY math_avg DESC;

-- 查询年龄大于 18 的学生，按性别分组，计算各组的人数，筛选人数大于 2 的分组，按升序排序
SELECT sex, COUNT(id) total FROM students
WHERE age > 18
GROUP BY sex
HAVING COUNT(id) > 2
ORDER BY total ASC;
```

### 分页查询

`SELECT * FROM 表名 LIMIT 每页条数 OFFSET 起始位置;`：分页查询，起始位置 = (当前页数 - 1) * 每页条数

OFFSET 可以省略，简写为 `LIMIT 查询起始位置, 每页条数;`

```SQL
-- 查询所有学生，从第 3 条开始查询，每页 5 条数据
SELECT * FROM students LIMIT 3, 5;
```

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

## 数据表的约束

约束是对表中的数据进行限制，保证数据的正确性、有效性和完整性

一个表如果添加了约束，不正确的数据将无法插入到表中

约束一般在创建表的时候添加

约束的种类：

- `PRIMARY KEY`：主键
- `NOT NULL`：非空
- `UNIQUE`: 唯一
- `FOREIGN KEY`: 外键

### 非空约束（NOT NULL）

在创建表时设置非空：`CREATE TABLE 表名 (字段名 字段类型  NOT NULL);`

### 设置默认值（DEFAULT）

在创建表时设置默认值：`CREATE TABLE 表名 (字段名 字段类型  DEFAULT 默认值);`

### 唯一约束（UNIQUE）

表中某一列不能出现重复的值

在创建表时设置唯一：`CREATE TABLE 表名 (字段名 字段类型  UNIQUE);`

### 主键约束（PRIMARY KEY）

主键是表中记录的唯一标识，一张表只能由一个主键，非空且唯一

通常不用业务字段作为主键，单独给每张表设计一个 id 的字段，把 id 作为主键。

在创建表时添加主键：`CREATE TABLE 表名 (id INT PRIMARY KEY);`

在已有表中添加主键：`ALTER TABLE 表名 MODIFY id INT PRIMARY KEY;`

删除主键：`ALTER TABLE 表名 DROP PRIMARY KEY;`

主键自增：`CREATE TABLE 表名(id INT PRIMARY KEY AUTO_INCREMENT);`

### 外键约束（FOREIGN KEY）

让表与表产生关联，保证数据的正确性

```SQL
CREATE TABLE 表名(
  字段名
  CONSTRAINT 外键名称
  FOREIGN KEY (外键列名称)
  REFERENCES 关联表名(关联表列名称)
);
```

新建表时增加外键：`CONSTRAINT 外键名称 FOREIGN KEY(外键字段名) REFERENCES 关联表名(关联表列名称);`

已有表增加外键：`ALTER TABLE 表名 ADD CONSTRAINT 外键名称 FOREIGN KEY (外键字段名) REFERENCES 关联表名(关联表列名称);`

删除外键：`ALTER TABLE 从表 DROP FOREIGN KEY 外键名称;`

在修改和删除主表的主键时，同时更新或删除副表的外键值，称为级联操作

- 联级更新：`ON UPDATE CASCADE`

- 联级删除：`ON DELETE CASCADE`

## 数据库设计

### 表与表之间的关系

- 一对多

在从表（多方）创建一个字段，字段作为外键指向主表（一方）的主键

- 多对多

需要创建第三张表，中间表中至少两个字段，这两个字段分别作为外键指向各自一方的主键

- 一对一

主表的主键和从表的主键，形成主外键关系

### 数据规范化

目前关系数据库有六种范式：

- `1NF`：第一范式
- `2NF`：第二范式
- `3NF`：第三范式
- `BCNF`：巴斯-科德范式
- `4NF`：第四范式
- `5NF`：第五范式

#### 1NF

原子性：表中每列不可再拆分

#### 2NF

表中的每一个字段都完全依赖于主键

一张表只描述一件事情

#### 3NF

不产生传递依赖，表中每一列都直接依赖于主键。而不是通过其它列间接依赖于主键

## 事务

