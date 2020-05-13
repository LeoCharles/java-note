# MySQL 基础

## SQL 的概念

SQL(Structured Query Language) 结构化查询语言

SQL 是所有关系型数据库的查询规范，不同的数据库 SQL 语句有一些区别

SQL 语句分类:

1. Data Definition Language (DDL 数据定义语言) 如：建库，建表
2. Data Manipulation Language(DML 数据操纵语言)，如：对表中的记录操作增删改
3. Data Query Language(DQL 数据查询语言)，如：对表中的查询操作
4. Data Control Language(DCL 数据控制语言)，如：对用户权限的设置

## DDL 操作数据库、表

常用的操作：CRUD

- Create 创建
- Retrieve 查询
- Update 修改
- Delete 删除

### 操作数据库

#### 创建数据库

- 创建数据库: `CREATE DATABASE 数据库名;`

- 判断数据库是否存在，不存才创建：`CREATE DATABASE IF NOT EXISTS 数据库名;`

- 创建数据库并指定字符集：`CREATE DATABASE 数据库名 CHARACTER SET 字符集;`

#### 查询数据库

- 查看数据库：`SHOW DATABASES;`

- 查看某个数据库的定义信息：`SHOW CREATE DATABASE 数据库名;`

#### 修改数据库

- 修改数据库默认字符集：`ALTER DATABASE 数据库名 DEFAULT CHARACTER SET 字符集;`

#### 删除数据库

- 删除数据库：`DROP DATABASE 数据库名;`

#### 使用数据库

- 使用数据库：`USE 数据库名;`

- 查看正在使用的数据库: `SELECT DATABASE();`
