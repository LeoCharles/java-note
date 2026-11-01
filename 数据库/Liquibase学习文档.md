# Liquibase 学习文档

> 数据库表结构（Schema）也是一种**代码**。它有版本、有变更、有回滚需求，却常常游离于 Git 之外——靠"我本地改完发你 SQL"来同步。
> **Liquibase** 就是用来把数据库变更加入版本控制的工具：变更写成 changelog 文件，随代码一起提交、评审、发布、回滚。
> 本篇以 **Liquibase 4.x + Spring Boot 3.x** 为基准，从"为什么要做"讲到"生产怎么安全地做"，包含 Flyway 对比、存量库接入、多环境、团队协作与踩坑清单。

---

## 📖 目录

1. [没有版本控制时，我们在做什么](#一没有版本控制时我们在做什么)
2. [Liquibase 是什么](#二liquibase-是什么)
3. [Liquibase vs Flyway vs ddl-auto](#三liquibase-vs-flyway-vs-ddl-auto)
4. [核心概念：Changelog / ChangeSet / Change](#四核心概念changelog--changeset--change)
5. [快速上手：Spring Boot 集成](#五快速上手spring-boot-集成)
6. [Changelog 的四种格式](#六changelog-的四种格式)
7. [常用 Change 类型](#七常用-change-类型)
8. [ChangeSet 的关键属性 ⭐⭐](#八changeset-的关键属性-)
9. [组织方式：master + include / includeAll ⭐](#九组织方式master--include--includeall-)
10. [回滚 ⭐⭐](#十回滚-)
11. [Preconditions：让变更"可重复执行"](#十一preconditions让变更可重复执行)
12. [Contexts 与 Labels：多环境管理](#十二contexts-与-labels多环境管理)
13. [存量库接入：baseline 与 changelogSync ⭐](#十三存量库接入baseline-与-changelogsync-)
14. [生产安全执行流程 ⭐⭐](#十四生产安全执行流程-)
15. [常用命令与 Maven 插件](#十五常用命令与-maven-插件)
16. [团队协作规范](#十六团队协作规范)
17. [实际项目案例：学生管理系统](#十七实际项目案例学生管理系统)
18. [与 MyBatis / JPA 的配合](#十八与-mybatis--jpa-的配合)
19. [踩坑清单](#十九踩坑清单)
20. [📌 在 Spring Boot 中](#-在-spring-boot-中)
21. [本章小结](#本章小结)

---

## 一、没有版本控制时，我们在做什么

### 1.1 一个典型的故事

**周一**：张三在本地给 `student` 表加了 `email` 字段，发到群里："大家更新一下"。
**周三**：李四在测试库手动执行了 `ALTER TABLE`，但**打错了一个字**（`emial`），自己也没发现。
**周五**：王五从别的分支合并代码，启动服务报 `Unknown column 'email'`——他的本地库没有这个字段。
**下周一**：生产发布，DBA 问："这次要执行哪些 SQL？" 没人说得清，最后翻了半小时聊天记录。

**根因不是粗心，而是缺少机制**：

| 问题 | 结果 |
| :--- | :--- |
| SQL 不在代码仓库里 | 无法 Code Review、无法追溯"谁改的、为什么改" |
| 各环境手工执行 | 开发/测试/生产结构不一致 |
| 执行顺序靠记忆 | 依赖关系错乱，补数据脚本在改表之前执行 |
| 没有"是否已执行"的记录 | 重复执行报错，或干脆漏执行 |
| 无法回滚 | 上线出问题只能硬扛 |

### 1.2 数据库变更管理的三个层次

| 层次 | 做法 | 问题 |
| :--- | :--- | :--- |
| L0 | 手工执行 SQL，口头/群里通知 | 完全靠人，必然出错 |
| L1 | SQL 文件放 Git，按目录排序，发布时人工执行 | 有记录，但"执行到哪一步"仍靠人 |
| L2 | **工具自动管理**（Liquibase / Flyway），执行有台账、失败可回滚 | 推荐 |

> 💡 **一句话**：Liquibase 解决的不是"怎么写 SQL"，而是"**怎么保证每个环境的数据库都处于同一个已知状态**"。

### 1.3 版本控制的"物理定律"

1. **已经执行过的变更，永远不允许修改**（改了校验和会不一致，别人也对不上）
2. **变更只能追加，不能删除**（`V1.0` 执行过，就不能从仓库里删掉，否则新同事拉代码建库会缺表）
3. **变更脚本必须幂等可重跑**（或被工具保证"只跑一次"）
4. **结构性变更与数据变更要分开**（DDL 和 DML 的失败影响不同）

> ⚠️ **第 1 条是新手最容易违反的**。在已有 changeset 上补一行，本地没事（已执行），同事/生产直接校验和报错。

---

## 二、Liquibase 是什么

Liquibase 是一个开源的**数据库变更管理工具**（Apache 2.0），由 Datical（现 Liquibase Inc.）维护，2012 年发布至今。

**核心工作方式**：

```text
changelog 文件（XML/YAML/JSON/SQL）
        ↓  liquibase update
逐条执行未执行过的 changeset
        ↓
在数据库的 DATABASECHANGELOG 表里记录"已经跑过哪些"
```

**它能做什么**：

- 用**声明式**文件描述表、列、索引、约束、数据变更
- 自动判断"哪些还没执行"，只跑增量
- 记录执行历史（谁、什么时候、是否成功、校验和）
- **支持回滚**（自动或手写）
- 支持多环境（contexts）、前置条件（preconditions）、数据库方言适配
- 能从现有库**反向生成** changelog（`generateChangeLog`）
- 能对比两个库差异（`diffChangeLog`）

**它不做什么**：

- 不替代 JPA/MyBatis 的 ORM 功能
- 不做数据同步/备份
- 不做在线 DDL（大型表改结构仍需 gh-ost / pt-online-schema-change，见第十四章）

---

## 三、Liquibase vs Flyway vs ddl-auto

| 维度 | Liquibase | Flyway | Hibernate `ddl-auto` |
| :--- | :--- | :--- | :--- |
| 变更格式 | XML/YAML/JSON/SQL | 纯 SQL（及 Java） | 无（从实体推导） |
| 数据库无关性 | **强**（同一变更适配多方言） | 弱（每个库写一套 SQL） | 强（但生成 SQL 不可控） |
| 可读性 | XML 较啰嗦，SQL 格式直接 | **最直观** | — / |
| 回滚 | **支持**（自动 + 手写） | 有限（需另写 undo 脚本，团队版更强） | 无 |
| 学习成本 | 中高（概念多） | 低 | 最低 |
| 生态/社区 | 大 | 大 | 随 ORM |
| 适合 | 企业级、多数据库、需要回滚与审计 | 单一数据库、追求简单直接 | **仅开发环境** |

### 3.1 怎么选

```text
只有一个数据库（MySQL） + 团队偏好纯 SQL + 不需要回滚？
    → Flyway

多数据库（MySQL + PostgreSQL + Oracle） + 需要回滚 + 需要审计报告？
    → Liquibase

只是本地快速建表 / 原型验证？
    → ddl-auto=update（生产禁用）
```

> ⚠️ **`ddl-auto=update` 生产禁用**：它会静默改表（加列不删列、从不改类型），且没有执行记录。很多事故是"本地开了 update，误连测试库"。

### 3.2 二者可以共存吗

技术上可以（Liquibase 只管结构，Flyway 管……也管结构），但**同一张表被两个工具管必然打架**。**一个项目只用一个**。

---

## 四、核心概念：Changelog / ChangeSet / Change

### 4.1 三层结构

```text
Changelog（变更日志文件）
 ├─ ChangeSet（一个原子变更单元）
 │    ├─ Change（具体操作：createTable / addColumn / sql ...）
 │    └─ Change（可包含多个）
 ├─ ChangeSet
 └─ ...
```

| 概念 | 说明 | 对应文件 |
| :--- | :--- | :--- |
| **Changelog** | 变更日志文件本身，可以是 master 或子文件 | `db.changelog-master.yaml` |
| **ChangeSet** | **最小执行单元**，由 `id + author + 文件名` 唯一标识 | 一次 `ALTER TABLE` |
| **Change** | changeset 内的单个操作 | `addColumn`、`insert` |

### 4.2 ChangeSet 的唯一标识

```text
唯一键 = id + author + filename
```

- `id`：**由你决定**，不要求是数字，不要求全局唯一，但**在同一个文件内必须唯一**
- `author`：通常是 Git 用户名或姓名
- `filename`：changelog 的相对路径

> ⚠️ **不要用 `id="1"`、`id="2"` 这种纯序号**。两个人同时写 `id=5` 不会报错，但永远分不清谁是谁的。推荐 `20261101-01-create-student-table` 或直接用时间戳。

### 4.3 执行记录表

Liquibase 会在库中建两张表：

**DATABASECHANGELOG**（变更台账）：

| 列 | 说明 |
| :--- | :--- |
| `ID` / `AUTHOR` / `FILENAME` | changeset 唯一标识 |
| `DATEEXECUTED` | 执行时间 |
| `ORDEREXECUTED` | 全局执行顺序 |
| `EXECTYPE` | `EXECUTED` / `RERAN` / `MARK_RAN` / `SKIPPED` / `FAILED` |
| `MD5SUM` | 校验和 |
| `DESCRIPTION` / `COMMENTS` | 描述 |
| `TAG` | 标签（配合 rollback 到 tag） |
| `LIQUIBASE` | 执行时的 Liquibase 版本 |
| `CONTEXTS` / `LABELS` | 上下文与标签 |
| `DEPLOYMENT_ID` | 部署批次 |

**DATABASECHANGELOGLOCK**（锁表）：防止多个实例并发执行变更，`LOCKED=1` 表示有人在跑。

```sql
SELECT * FROM DATABASECHANGELOG ORDER BY ORDEREXECUTED DESC LIMIT 10;
```

> 💡 **排查"这个字段到底在哪个版本加的"**，直接查这张表，比翻 Git 历史快得多。

### 4.4 一个最小的 ChangeSet

```xml
<changeSet id="20261101-01" author="leo">
    <createTable tableName="student">
        <column name="id" type="BIGINT" autoIncrement="true">
            <constraints primaryKey="true" nullable="false"/>
        </column>
        <column name="name" type="VARCHAR(20)">
            <constraints nullable="false"/>
        </column>
    </createTable>
</changeSet>
```

**执行逻辑**：

1. 计算 changeset 的 MD5 校验和
2. 查 `DATABASECHANGELOG` 是否有 `(id, author, filename)`
3. **没有** → 执行，插入记录
4. **有且校验和一致** → 跳过
5. **有但校验和不同** → **报错 `Validation Failed: change sets check sum`**

---

## 五、快速上手：Spring Boot 集成

### 5.1 依赖

```xml
<dependency>
    <groupId>org.liquibase</groupId>
    <artifactId>liquibase-core</artifactId>
</dependency>
<!-- Spring Boot 的 dependencyManagement 已管理版本，无需写 version -->
```

> Spring Boot 3.x 已管理 Liquibase 版本；需要升级时在 `properties` 里覆盖 `liquibase.version`。

### 5.2 目录结构

```text
src/main/resources/
└── db/
    └── changelog/
        ├── db.changelog-master.yaml      # 主文件
        ├── 001-create-student.yaml       # 子文件
        ├── 002-add-email.yaml
        └── 003-insert-dict-data.yaml
```

Spring Boot 的默认 `change-log` 就是 `classpath:/db/changelog/db.changelog-master.yaml`，**放对位置可以零配置**。

### 5.3 application.yml

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/study?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver

  liquibase:
    enabled: true                                  # 默认 true
    change-log: classpath:/db/changelog/db.changelog-master.yaml
    contexts: dev                                   # 按环境过滤（可选）
    # labels: base                                  # 标签过滤（可选）
    default-schema: study                           # 目标 schema（可选）
    # liquibase-schema: public                      # 台账表放哪个 schema
    drop-first: false                               # 危险：启动前清库！仅用于测试
```

### 5.4 启动

启动应用，控制台会看到：

```text
liquibase.lockservice.StandardLockService : Successfully acquired change log lock
liquibase.changelog.StandardChangeLogHistoryService : Creating database history table with name: study.DATABASECHANGELOG
liquibase.changelog.StandardChangeLogHistoryService : Reading from study.DATABASECHANGELOG
liquibase.changelog.ChangeSet : Table student created
liquibase.lockservice.StandardLockService : Successfully released change log lock
```

复查：

```sql
SELECT ID, AUTHOR, FILENAME, DATEEXECUTED, EXECTYPE, MD5SUM
FROM DATABASECHANGELOG;
```

### 5.5 关闭自动执行（生产常用）

如果你的流程是"**DBA 审核后手动执行**"，可以关闭自动执行：

```yaml
spring:
  liquibase:
    enabled: false
```

或者按 profile 控制：

```yaml
spring:
  config:
    activate:
      on-profile: prod
  liquibase:
    enabled: true          # 生产反而要开——由应用启动时统一执行
```

> 💡 **两种模式**：
> - **应用启动时执行**（`spring.liquibase.enabled=true`）：简单，适合中小团队；但要考虑多实例并发（有锁表保护）
> - **CI/CD 独立执行**（`enabled=false` + Maven/Gradle 插件或 CLI）：可控，适合有发布平台的团队

---

## 六、Changelog 的四种格式

### 6.1 XML（功能最全）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
        xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-latest.xsd">

    <changeSet id="20261101-01" author="leo">
        <comment>创建学生表</comment>
        <createTable tableName="student">
            <column name="id" type="BIGINT" autoIncrement="true">
                <constraints primaryKey="true" nullable="false" primaryKeyName="pk_student"/>
            </column>
            <column name="name" type="VARCHAR(20)">
                <constraints nullable="false"/>
            </column>
            <column name="age" type="INT"/>
        </createTable>
    </changeSet>

</databaseChangeLog>
```

**优点**：IDE 有 XSD 提示和校验、能力最全、官方示例最多
**缺点**：啰嗦，一个字段 5 行；Git diff 噪音大

> 💡 `dbchangelog-latest.xsd` 会让 IDE 总是校验最新语法。**想让构建更稳定，可以固定为具体版本**（如 `dbchangelog-4.29.xsd`），避免升级 Liquibase 后语法校验突变。

### 6.2 YAML（推荐、简洁）

```yaml
databaseChangeLog:
  - changeSet:
      id: 20261101-01
      author: leo
      comment: 创建学生表
      changes:
        - createTable:
            tableName: student
            columns:
              - column:
                  name: id
                  type: BIGINT
                  autoIncrement: true
                  constraints:
                    primaryKey: true
                    nullable: false
                    primaryKeyName: pk_student
              - column:
                  name: name
                  type: VARCHAR(20)
                  constraints:
                    nullable: false
              - column:
                  name: age
                  type: INT
```

> ⚠️ **YAML 对缩进极度敏感**，一个空格错位就是 `class liquibase.exception.ChangeLogParseException`。**建议配 IDE 的 YAML 插件并关闭自动格式化对 changelog 目录的影响**。
>
> ⚠️ Liquibase 4.23+ 对 YAML 解析器做了切换，**新版本支持更简洁的列表写法**（`- createTable:` 直接作为 `changes` 列表项）。混用新旧写法可能导致解析失败，团队内统一即可。

### 6.3 JSON

```json
{
  "databaseChangeLog": [
    {
      "changeSet": {
        "id": "20261101-01",
        "author": "leo",
        "changes": [
          {
            "createTable": {
              "tableName": "student",
              "columns": [
                { "column": { "name": "id", "type": "BIGINT", "autoIncrement": true } }
              ]
            }
          }
        ]
      }
    }
  ]
}
```

**实际项目很少用**——比 YAML 更啰嗦。

### 6.4 原生 SQL（DBA 友好）

```sql
--liquibase formatted sql

--changeset leo:20261101-01
CREATE TABLE student (
    id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20) NOT NULL,
    age  INT
);

--changeset leo:20261101-02
ALTER TABLE student ADD COLUMN email VARCHAR(50);
```

**要点**：

1. 文件**第一行必须是 `--liquibase formatted sql`**（MySQL），Oracle 用 `-- liquibase formatted sql`（同样有效）
2. `--changeset author:id` 标记变更开始，**id 中不能有空格**（用连字符）
3. 每个 changeset 默认一条语句；**多条语句要用 `--splitStatements:false` 或 `--endDelimiter`** 调整
4. 回滚用 `--rollback ...`

```sql
--liquibase formatted sql

--changeset leo:20261101-03 splitStatements:false endDelimiter:/
CREATE PROCEDURE proc_sync_score()
BEGIN
    UPDATE student SET score = 0 WHERE score IS NULL;
END
/

--rollback DROP PROCEDURE proc_sync_score;
```

**优点**：DBA 能直接审、能直接执行、语法高亮完善
**缺点**：失去数据库无关性；回滚必须手写

> 💡 **实际项目最常见的组合：YAML/XML 管 DDL，SQL 文件管复杂 DML 和存储过程**（工程里两者混用完全合法，见第九章）。

### 6.5 格式选择建议

| 团队情况 | 推荐 |
| :--- | :--- |
| 单一 MySQL，DBA 强参与 | **SQL 格式** |
| 多数据库、需要方言适配 | **YAML** |
| 需要 IDE 强校验、复杂变更 | **XML** |
| 混合 | master 用 YAML，复杂 SQL 用 `sql` change 或独立 SQL 文件 |

> ⚠️ **一个项目的 master changelog 与子文件格式可以不同**，但**同一个 changeset 内部不要混**。

---

## 七、常用 Change 类型

### 7.1 表与列

```yaml
changes:
  # 建表
  - createTable:
      tableName: student
      columns:
        - column: { name: id, type: BIGINT, autoIncrement: true,
                    constraints: { primaryKey: true, nullable: false } }
        - column: { name: name, type: VARCHAR(20),
                    constraints: { nullable: false } }

  # 加列
  - addColumn:
      tableName: student
      columns:
        - column: { name: email, type: VARCHAR(50) }

  # 删列
  - dropColumn:
      tableName: student
      columnName: email

  # 改列类型 / 重命名
  - modifyDataType:
      tableName: student
      columnName: name
      newDataType: VARCHAR(50)

  - renameColumn:
      tableName: student
      oldColumnName: name
      newColumnName: full_name
      columnDataType: VARCHAR(50)

  # 改表名 / 删表
  - renameTable: { oldTableName: student, newTableName: sys_student }
  - dropTable: { tableName: sys_student }
```

### 7.2 索引与约束

```yaml
changes:
  - createIndex:
      tableName: student
      indexName: idx_student_class_id
      columns:
        - column: { name: class_id }

  # 唯一索引
  - createIndex:
      tableName: student
      indexName: uk_student_no
      unique: true
      columns:
        - column: { name: student_no }

  # 加唯一约束
  - addUniqueConstraint:
      tableName: student
      columnNames: student_no
      constraintName: uk_student_no

  # 外键
  - addForeignKeyConstraint:
      baseTableName: student
      baseColumnNames: class_id
      referencedTableName: clazz
      referencedColumnNames: id
      constraintName: fk_student_class
      onDelete: RESTRICT

  # 删除
  - dropIndex: { indexName: idx_student_class_id, tableName: student }
  - dropForeignKeyConstraint:
      baseTableName: student
      constraintName: fk_student_class
```

> ⚠️ **MySQL 中 `createIndex` 的 `indexName` 在同一个库内是全局唯一的**（不是每个表独立）。多表都叫 `idx_create_time` 会冲突。**命名规范：`idx_表名_列名`**。

### 7.3 数据变更

```yaml
changes:
  # 插入
  - insert:
      tableName: sys_dict
      columns:
        - column: { name: code, value: "SEX" }
        - column: { name: name, value: "性别" }

  # 更新
  - update:
      tableName: student
      columns:
        - column: { name: sex, value: "1" }
      where: "sex IS NULL"

  # 删除
  - delete:
      tableName: student
      where: "deleted = 1"

  # 原生 SQL（最灵活）
  - sql:
      sql: "UPDATE student SET score = 0 WHERE score IS NULL"

  # 从 CSV 导入
  - loadData:
      tableName: sys_dict
      file: data/dict.csv
      separator: ","
      encoding: UTF-8
```

> ⚠️ **`update` 的 `where` 是直接拼进 SQL 的**，不要放外部输入。它只用于 changelog 内部的静态条件。
>
> ⚠️ **批量数据变更不要写在一个 changeset 里执行几十万行**：会锁表、撑大事务。**用分批 `sql` + 每批一个 changeset，或放在应用层的迁移任务里**。

### 7.4 标签与发布标记

```yaml
changes:
  # 打 tag：后续可 rollback 到此 tag
  - tagDatabase:
      tag: release-1.0.0
```

```yaml
# 或作为独立 changeset
- changeSet:
    id: tag-1.0.0
    author: leo
    changes:
      - tagDatabase:
          tag: release-1.0.0
```

### 7.5 其他常用

| Change | 用途 |
| :--- | :--- |
| `addDefaultValue` | 给列加默认值 |
| `dropDefaultValue` | 删除默认值 |
| `addNotNullConstraint` | 加非空约束（可指定默认值回填） |
| `dropNotNullConstraint` | 去非空 |
| `addAutoIncrement` | 加自增 |
| `createSequence` | 创建序列（Oracle/PG） |
| `createView` / `dropView` | 视图 |
| `createProcedure` | 存储过程 |
| `renameSequence` | 重命名序列 |
| `empty` | 空变更（占位、配合 `MARK_RAN`） |
| `executeCommand` | 执行系统命令（**生产禁用**） |
| `customChange` | 自定义 Java 迁移逻辑（复杂数据清洗） |

### 7.6 `modifySql`：方言适配

```yaml
- createIndex:
    tableName: student
    indexName: idx_student_name
    columns:
      - column: { name: name }
  modifiers:
    - modifySql:
        dbms: mysql
        append: " USING BTREE"
```

用于"同一变更在不同数据库上加数据库特有语法"，这是 Liquibase 数据库无关性的关键机制。

---

## 八、ChangeSet 的关键属性 ⭐⭐

### 8.1 属性总览

```yaml
- changeSet:
    id: 20261101-04
    author: leo
    comment: 添加 email 字段
    context: dev,test          # 只在指定上下文执行
    labels: feature-a          # 标签过滤
    runAlways: false           # 每次启动都执行
    runOnChange: false         # 内容变化后才重新执行
    runInTransaction: true     # 是否包在事务里（DDL 在 MySQL 无效）
    failOnError: true          # 出错是否中断
    dbms: mysql,postgresql     # 只在指定数据库执行
    ignore: false              # 跳过该 changeset
    validCheckSum: ANY         # 允许某个校验和通过
    changes: [...]
    rollback: [...]
    preConditions: [...]
```

### 8.2 `runAlways` vs `runOnChange`

| 属性 | 行为 | 典型用途 |
| :--- | :--- | :--- |
| 默认 | **只执行一次**，之后跳过 | 绝大多数 DDL |
| `runOnChange: true` | 内容（校验和）变了就**重新执行** | 视图、存储过程、可重入的初始化数据 |
| `runAlways: true` | **每次都执行** | 极少用（如清理临时表） |

```yaml
- changeSet:
    id: 20261101-06
    author: leo
    runOnChange: true
    changes:
      - createView:
          viewName: v_student_detail
          replaceIfExists: true
          selectQuery: "SELECT s.id, s.name, c.name AS class_name
                         FROM student s LEFT JOIN clazz c ON c.id = s.class_id"
```

> 💡 **视图/存储过程最适合 `runOnChange: true`**：修改定义后，下次启动自动重建，不用新写一个 changeset。
>
> ⚠️ **`runAlways: true` 配 `insert` 会造成数据重复**，除非有唯一约束。

### 8.3 `runInTransaction`

```yaml
- changeSet:
    id: 20261101-07
    author: leo
    runInTransaction: false
    changes:
      - sql:
          sql: "CREATE INDEX idx_student_age ON student(age)"
```

**为什么需要 `runInTransaction: false`**：

- **MySQL 的 DDL 会隐式提交**，`ALTER TABLE` 根本没法回滚，事务包着只是心理安慰
- **Oracle/PostgreSQL 的部分语句**（如 `CREATE INDEX CONCURRENTLY`）不能在事务中执行
- **大表 DDL 不希望持有长事务**

> ⚠️ **`runInTransaction: false` 意味着失败后可能处于中间状态**，必须配合 `preConditions` + 幂等设计。

### 8.4 `dbms`

```yaml
- changeSet:
    id: 20261101-08
    author: leo
    dbms: postgresql
    changes:
      - sql:
          sql: "COMMENT ON COLUMN student.name IS '姓名'"
```

取值：`mysql`、`postgresql`、`oracle`、`mssql`、`h2`、`db2`、`derby` 等，可用 `!mysql` 表示"非 MySQL"。

### 8.5 `failOnError`

```yaml
- changeSet:
    id: 20261101-09
    author: leo
    failOnError: false        # 出错只记 WARN，继续执行
    changes:
      - sql:
          sql: "DROP INDEX idx_old ON student"
```

> ⚠️ **`failOnError: false` 是"掩盖问题"的捷径**，会让失败被静默吞掉。**只在确实"失败也没关系"的场景使用**（如删除可能不存在的索引）。

### 8.6 `validCheckSum`

误改了已执行的 changeset 后：

```yaml
- changeSet:
    id: 20261101-01
    author: leo
    validCheckSum: ANY        # 认可任何校验和（不推荐，掩盖问题）
    # 或精确指定：validCheckSum: 9:xxxxx
```

> ⚠️ **这是"止血"手段，不是解决方案**。正确做法：**新建一个 changeset 做增量修改**。`clearCheckSums` 命令会清空所有校验和，**生产慎用**。

### 8.7 `ignore`

```yaml
- changeSet:
    id: 20261101-10
    author: leo
    ignore: true
    changes: [...]
```

临时跳过某个 changeset（对已执行过的没有影响）。**生产不建议**——会造成各环境漂移。

---

## 九、组织方式：master + include / includeAll ⭐

### 9.1 为什么要有 master

如果所有 changeset 都塞进一个文件：

- 文件几千行、Git 冲突频繁
- 多人同时改同一文件必然冲突

**标准做法**：`master` 文件只负责"**按顺序引用**"，真正的变更分散在子文件。

### 9.2 YAML 版 master

```yaml
# db/changelog/db.changelog-master.yaml
databaseChangeLog:
  - include:
      file: db/changelog/001-create-student.yaml
      relativeToChangelogFile: false
  - include:
      file: db/changelog/002-create-score.yaml
  - include:
      file: db/changelog/003-add-email.yaml
  - include:
      file: db/changelog/004-insert-dict.yaml
```

**关键规则**：

1. **`include` 的顺序就是执行顺序**
2. 新变更**追加到文件末尾**，不要插在中间
3. 新版本的**日期/序号必须递增**

### 9.3 `includeAll`：自动扫描目录

```yaml
databaseChangeLog:
  - includeAll:
      path: db/changelog/changes/
      relativeToChangelogFile: false
      errorIfMissingOrEmpty: true
```

目录：

```text
db/changelog/changes/
├── 20261101-001-create-student.yaml
├── 20261101-002-create-score.yaml
├── 20261102-001-add-email.yaml
└── 20261102-002-insert-dict.yaml
```

**`includeAll` 按**文件名的**字典序**执行**——所以文件名前缀必须能保证顺序（日期或递增序号）。

> ⚠️ **`includeAll` 的排序是字符串排序**：`10-xxx` 会排在 `2-xxx` 前面。**必须补零**（`001`、`002`、`010`）。
>
> ⚠️ **`includeAll` 无法控制单个文件的 `context`**，需要按环境分离时用多个目录 + 多个 `includeAll`。

### 9.4 XML 版 master

```xml
<databaseChangeLog xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
                    http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-latest.xsd">

    <include file="db/changelog/001-create-student.xml"/>
    <include file="db/changelog/002-create-score.xml"/>
    <includeAll path="db/changelog/changes/"/>
</databaseChangeLog>
```

### 9.5 分模块组织（大型项目）

```text
db/changelog/
├── db.changelog-master.yaml
├── base/
│   ├── 001-schema.yaml
│   └── 002-dict-data.yaml
├── module-student/
│   ├── 001-create.yaml
│   └── 002-index.yaml
├── module-score/
│   └── 001-create.yaml
└── patch/
    └── 20261101-hotfix.yaml
```

```yaml
# master
databaseChangeLog:
  - includeAll:
      path: db/changelog/base/
  - includeAll:
      path: db/changelog/module-student/
  - includeAll:
      path: db/changelog/module-score/
  - includeAll:
      path: db/changelog/patch/
```

> 💡 **微服务架构下，每个服务管自己的 schema**。**不要让多个服务操作同一个库的同一张表**——这是共享数据库反模式的开始。跨服务的数据通过 API 或消息同步。

### 9.6 `relativeToChangelogFile`

```yaml
- include:
    file: 001-create-student.yaml
    relativeToChangelogFile: true      # 相对当前 changelog 文件解析
```

- `false`（默认）：相对 classpath 根
- `true`：相对当前文件所在目录

> ⚠️ **混用两种写法是路径错误的高发区**。团队内统一一种（推荐 `relativeToChangelogFile: true` + 相对路径，移动目录时不会崩）。

---

## 十、回滚 ⭐⭐

### 10.1 回滚的三种方式

```bash
# 1. 回滚到某个 tag
liquibase rollback release-1.0.0

# 2. 回滚最近 N 个 changeset
liquibase rollback-count --count=3

# 3. 回滚到某个时间点
liquibase rollback-to-date 2026-11-01T10:00:00
```

### 10.2 自动回滚

Liquibase 对部分 change **内置了反向操作**：

| Change | 自动回滚 |
| :--- | :--- |
| `createTable` | `DROP TABLE` |
| `addColumn` | `DROP COLUMN` |
| `createIndex` | `DROP INDEX` |
| `addForeignKeyConstraint` | 删除外键 |
| `createView` | `DROP VIEW` |
| `insert` | 按主键 `DELETE` |
| `addUniqueConstraint` | 删除约束 |
| **`sql`** | **无**（必须手写） |
| **`update` / `delete`** | **无**（数据不可逆） |
| `dropTable` / `dropColumn` | **无**（数据没了） |

> ⚠️ **`dropTable`、`dropColumn` 这类破坏性变更永远无法真正"自动回滚"**——表结构能建回来，数据回不来。**必须先备份**。

### 10.3 手写 rollback

```yaml
- changeSet:
    id: 20261101-11
    author: leo
    changes:
      - addColumn:
          tableName: student
          columns:
            - column: { name: nickname, type: VARCHAR(50) }
      - sql:
          sql: "UPDATE student SET nickname = name WHERE nickname IS NULL"
    rollback:
      - dropColumn:
          tableName: student
          columnName: nickname
```

SQL 格式：

```sql
--liquibase formatted sql

--changeset leo:20261101-12
ALTER TABLE student ADD COLUMN nickname VARCHAR(50);
UPDATE student SET nickname = name WHERE nickname IS NULL;
--rollback ALTER TABLE student DROP COLUMN nickname;
```

### 10.4 回滚的"能力边界"（必须知道）

| 场景 | 能回滚吗 |
| :--- | :--- |
| 加了一个字段 | ✅ 结构可回滚，但**字段里的数据丢失** |
| 删了一个字段 | ❌ 数据永久丢失 |
| 改了字段类型（`VARCHAR(20)` → `VARCHAR(5)`） | ⚠️ 改回去，但被截断的数据回不来 |
| 插入了字典数据 | ✅ 可按主键删除 |
| 批量 `UPDATE` | ❌ 改之前的原值没记录，回不去 |
| 存储过程/视图 | ✅ `runOnChange` + 重建 |

> ⚠️ **回滚≠时间机器**。回滚只保证"结构回到之前的状态"，**数据恢复必须靠备份**。
>
> 💡 **生产环境的"回滚"通常是"用新的正向变更修复"**（forward fix），而不是执行 `rollback`。**尤其是已经发布一段时间、写入了新数据的场景**——盲目回滚会删掉这些新数据。

### 10.5 一个安全实践：破坏性变更分两次发布

```text
版本 A（先发）：
  1. 新增 nickname 字段（可空）
  2. 应用双写 name + nickname
  3. 数据回填任务

版本 B（后发，确认无问题）：
  4. 应用只读 nickname
  5. 删除 name 字段
```

这叫**扩展-收缩模式（Expand-Contract）**，是大型系统在线改表的标配。

---

## 十一、Preconditions：让变更"可重复执行"

### 11.1 基本用法

```yaml
- changeSet:
    id: 20261101-13
    author: leo
    preConditions:
      - onFail: MARK_RAN
      - tableExists:
          tableName: student
    changes:
      - addColumn:
          tableName: student
          columns:
            - column: { name: phone, type: VARCHAR(20) }
```

**`onFail` 的取值**：

| 值 | 行为 |
| :--- | :--- |
| `HALT`（默认） | 校验失败，中断整个 update |
| `CONTINUE` | 跳过当前 changeset，继续下一个 |
| `MARK_RAN` | 标记为已执行，跳过实际变更 |
| `WARN` | 打警告日志，继续执行 |

### 11.2 常用 precondition

```yaml
preConditions:
  - tableExists: { tableName: student }
  - columnExists: { tableName: student, columnName: email }
  - indexExists: { tableName: student, indexName: idx_name }
  - viewExists: { viewName: v_student }
  - sequenceExists: { sequenceName: seq_student }
  - foreignKeyConstraintExists: { foreignKeyName: fk_student_class }
  - sqlCheck: { expectedResult: "0", sql: "SELECT COUNT(*) FROM student WHERE email IS NULL" }
  - changeSetExecuted:
      id: 20261101-01
      author: leo
      changeLogFile: db/changelog/db.changelog-master.yaml
  - dbms: { type: mysql }
  - runningAs: { username: root }
```

**组合逻辑**：

```yaml
preConditions:
  - and:
      - tableExists: { tableName: student }
      - not:
          - columnExists: { tableName: student, columnName: email }
```

### 11.3 为什么它这么重要

**场景**：测试环境已经手工加过 `email` 字段，现在 changelog 也要加。

- 没有 precondition：`Column 'email' already exists` → 启动失败
- 有 precondition：`MARK_RAN` 跳过，标记为已执行 → 启动成功

**场景**：`CREATE INDEX` 在 MySQL 上没有 `IF NOT EXISTS`，重复执行报错。

```yaml
- changeSet:
    id: 20261101-14
    author: leo
    preConditions:
      - onFail: MARK_RAN
      - not:
          - indexExists: { tableName: student, indexName: idx_student_age }
    changes:
      - createIndex:
          tableName: student
          indexName: idx_student_age
          columns:
            - column: { name: age }
```

> ⚠️ **不要滥用 `MARK_RAN`**：它会把"实际没执行"的变更标记成"已执行"，**可能掩盖真正的问题**。只在明确的"环境已有人工变更"场景使用。

> ⚠️ **preconditions 是有性能成本的**（要查元数据），但对一次迁移几十条来说是纳秒级，可以忽略。

---

## 十二、Contexts 与 Labels：多环境管理

### 12.1 Contexts：环境维度

```yaml
- changeSet:
    id: 20261101-15
    author: leo
    context: dev
    changes:
      - insert:
          tableName: sys_user
          columns:
            - column: { name: username, value: "test_user" }
            - column: { name: password, value: "123456" }
```

```yaml
# application-dev.yml
spring:
  liquibase:
    contexts: dev
```

| 命令 | 效果 |
| :--- | :--- |
| `contexts: dev` | 只执行 `context: dev` 的（以及没写 context 的） |
| `contexts: dev,test` | 执行 dev 或 test |
| `contexts: "!dev"` | 执行除 dev 外的 |
| 不设置 | **执行所有**（包括 dev 的测试数据！） |

> ⚠️ **没写 `context` 的 changeset 在任何环境下都会执行**。所以**测试数据必须显式标 `context: dev`**，否则上线时把测试数据带到生产。**这是真实出现过的事故**。

### 12.2 Labels：业务维度

```yaml
- changeSet:
    id: 20261101-16
    author: leo
    labels: feature-score-v2
    changes: [...]
```

```bash
liquibase update --labels="feature-score-v2"
```

**区别**：

| | Context | Label |
| :--- | :--- | :--- |
| 用途 | **环境**（dev/test/prod） | **业务/功能/发布批次** |
| 典型值 | `dev`、`test`、`prod` | `release-1.2`、`feature-x` |
| 表达式 | 同 Label（AND/OR/NOT） | 同 Context |

> 💡 **实际项目里 context 用得更多**，label 适合"按特性开关分批次上线"。

### 12.3 多环境配置示例

```yaml
# application-dev.yml
spring:
  liquibase:
    contexts: dev
    drop-first: false

# application-test.yml
spring:
  liquibase:
    contexts: test

# application-prod.yml
spring:
  liquibase:
    contexts: prod
```

```yaml
# changelog 里
- changeSet:
    id: 20261101-17
    author: leo
    context: dev,test          # 测试数据只在开发/测试
    changes:
      - insert: { tableName: sys_dict, ... }
```

---

## 十三、存量库接入：baseline 与 changelogSync ⭐

### 13.1 问题

你接手一个已有生产库，现在想引入 Liquibase。**如果直接让 Liquibase 从 `001-create-table` 开始跑，它会试图创建已存在的表 → 失败。**

### 13.2 三种接入策略

| 策略 | 做法 | 适用 |
| :--- | :--- | :--- |
| **A. 生成基线** | `generateChangeLog` 从现有库导出结构，作为 `001-baseline` | **推荐**，后续变更有完整历史 |
| **B. changelogSync** | 把一份"代表当前状态"的 changelog 标记为"已执行" | 简单、快速，但没有基线文件 |
| **C. 空 baseline + 新变更** | 一个空的 `mark-ran` changeset，之后只追加新变更 | 只有新变更需要管 |

### 13.3 策略 A：generateChangeLog

```bash
liquibase --changeLogFile=db/changelog/000-baseline.yaml \
          --url="jdbc:mysql://127.0.0.1:3306/study" \
          --username=root --password=root \
          generateChangeLog
```

生成的文件会包含所有表、列、索引、约束。

```yaml
# 000-baseline.yaml
databaseChangeLog:
  - changeSet:
      id: baseline
      author: leo
      changes: [ ... 完整结构 ... ]
```

**然后在已有库上标记为已执行**（否则它会尝试重建表）：

```bash
liquibase --changeLogFile=db/changelog/db.changelog-master.yaml \
          changelogSync
```

> ⚠️ `changelogSync` 会把**当前 master 里所有 changeset** 都标记为已执行，所以**必须确保 baseline 已包含当前库的全部结构**。

### 13.4 策略 B：changelogSync 的版本化用法

```yaml
# master
databaseChangeLog:
  - include:
      file: db/changelog/000-baseline.yaml
  - includeAll:
      path: db/changelog/changes/
```

```bash
# 1. 在已有库上，把 baseline 和历史的 changeset 全部标记为已执行
liquibase --changeLogFile=db/changelog/db.changelog-master.yaml changelogSync

# 2. 之后新增的 changeset 会被正常执行
liquibase --changeLogFile=db/changelog/db.changelog-master.yaml update
```

> 💡 **生产一次性操作**：**先备份库**，再 `changelogSync`，再校验 `DATABASECHANGELOG` 里记录是否完整。

### 13.5 策略 C：空 baseline

```yaml
- changeSet:
    id: 20261101-baseline
    author: leo
    changes:
      - empty: {}
```

```bash
liquibase --changeLogFile=... update
# 第一次 update 把 baseline 标记为已执行
```

之后所有变更都是"新增"。

> ⚠️ **C 的代价**：新同事拉代码建空库时，`update` 只会跑 baseline 之后的变更，**建不出完整的表结构**。**必须同时提供一份完整的建库 SQL 或 baseline 文件**。

### 13.6 各环境状态对齐检查

```bash
# 查看每个 changeset 的状态：是否执行、校验和是否一致
liquibase --changeLogFile=... status
liquibase --changeLogFile=... validate
```

**`status` 输出**：

```text
N change sets have not been applied to root@jdbc:mysql://.../study
     db/changelog/003-add-email.yaml::20261101-03::leo
```

---

## 十四、生产安全执行流程 ⭐⭐

### 14.1 推荐流程

```text
开发提交 changelog
    ↓
CI 校验（liquibase validate + updateSql 预览）
    ↓
Code Review（结构变更 + 回滚脚本）
    ↓
DBA/发布平台审核生成的 SQL
    ↓
低环境执行（dev → test → staging）
    ↓
生产执行（应用启动时 or 独立步骤）
    ↓
校验：查 DATABASECHANGELOG + 业务验证
```

### 14.2 生成 SQL 给 DBA 审核

```bash
liquibase --changeLogFile=db/changelog/db.changelog-master.yaml \
          --url="jdbc:mysql://.../study" \
          --username=root --password=root \
          updateSql > preview.sql
```

**输出的是"还没执行的"变更对应的 SQL**。DBA 可以直接审核。

### 14.3 大表 DDL 的注意事项

| 操作 | MySQL 行为 | 风险 |
| :--- | :--- | :--- |
| `ADD COLUMN`（末尾，可空） | 8.0 支持 `INSTANT`，秒级 | 低 |
| `ADD COLUMN`（中间位置） | `INPLACE`，需重建 | 中 |
| `MODIFY COLUMN`（改类型） | 通常 `COPY`，锁表 | **高** |
| `DROP COLUMN` | `INSTANT` 或 `INPLACE` | 中 |
| `ADD INDEX` | `INPLACE`，允许并发 DML | 中 |
| `CHANGE COLUMN` | 可能重建 | 高 |

> ⚠️ **千万级以上的表，结构变更应使用 `gh-ost` 或 `pt-online-schema-change`**。Liquibase 只是"生成并记录 SQL"，**不负责在线变更**。
>
> 💡 **配合策略**：Liquibase 里写 `--changeset ... runInTransaction:false`，实际执行交给平台（或人工用 gh-ost）。

### 14.4 多实例并发启动

多个应用实例同时启动时，都尝试执行迁移：

- `DATABASECHANGELOGLOCK` 保证**同一时刻只有一个在执行**
- 其他实例**等待锁释放**后重新检查（发现已执行则跳过）

> ⚠️ **锁超时/进程崩溃可能留下 `LOCKED=1`**，导致后续启动一直等待或报错。手动解锁：
>
> ```sql
> UPDATE DATABASECHANGELOGLOCK SET LOCKED = 0, LOCKGRANTED = NULL, LOCKEDBY = NULL
> WHERE ID = 1;
> ```

### 14.5 生产真正会翻车的几件事

| 风险 | 防范 |
| :--- | :--- |
| changelog 被误改（校验和冲突） | **已执行的 changeset 禁止修改**；CI 检查 |
| 测试数据带到生产 | 测试数据必须 `context: dev` |
| 破坏性变更无备份 | `dropTable`/`dropColumn` 前强制备份 |
| 大表 DDL 锁表 | 用 gh-ost / 低峰期 / 分批 |
| 迁移失败导致应用无法启动 | 迁移与应用启动解耦（独立 Job） |
| 回滚脚本没测过 | 在 staging 演练一次 `rollback` |
| 多环境结构漂移 | 每次发布后 `liquibase diff` 对比 |

---

## 十五、常用命令与 Maven 插件

### 15.1 核心命令

```bash
liquibase update                        # 执行所有未执行的 changeset
liquibase update-sql                    # 只输出 SQL，不执行
liquibase rollback <tag>                # 回滚到 tag
liquibase rollback-count --count=2      # 回滚最近 2 个
liquibase status                        # 查看未执行的变更
liquibase validate                      # 校验 changelog 合法性
liquibase history                       # 执行历史
liquibase diff                          # 对比两个库
liquibase diffChangeLog                 # 把差异生成 changelog
liquibase generateChangeLog             # 从现有库生成 changelog
liquibase changelogSync                 # 标记为已执行
liquibase tag release-1.0.0             # 打 tag
liquibase clearCheckSums                # 清空校验和（慎用）
liquibase releaseLocks                  # 释放锁
liquibase dropAll                       # 清空库（危险！）
```

### 15.2 CLI 安装

```bash
# 下载
wget https://github.com/liquibase/liquibase/releases/download/v4.29.2/liquibase-4.29.2.zip
unzip liquibase-4.29.2.zip -d /opt/liquibase
export PATH=$PATH:/opt/liquibase

liquibase --version
```

> ⚠️ Liquibase CLI 需要 JDK 8+（新版需 JDK 17+），且需要把数据库驱动放到 `lib/` 目录。

### 15.3 Maven 插件

```xml
<plugin>
    <groupId>org.liquibase</groupId>
    <artifactId>liquibase-maven-plugin</artifactId>
    <version>4.29.2</version>
    <configuration>
        <changeLogFile>src/main/resources/db/changelog/db.changelog-master.yaml</changeLogFile>
        <url>jdbc:mysql://127.0.0.1:3306/study</url>
        <username>root</username>
        <password>root</password>
        <driver>com.mysql.cj.jdbc.Driver</driver>
    </configuration>
    <dependencies>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <version>8.4.0</version>
        </dependency>
    </dependencies>
</plugin>
```

```bash
mvn liquibase:update
mvn liquibase:updateSQL
mvn liquibase:validate
mvn liquibase:rollback -Dliquibase.rollbackCount=1
```

> 💡 **Maven 插件适合 CI/CD**：流水线里执行 `liquibase:updateSQL` 生成预览给审批，再执行 `liquibase:update`。

### 15.4 Gradle

```groovy
plugins {
    id 'org.liquibase.gradle' version '2.2.0'
}

dependencies {
    liquibaseRuntime 'org.liquibase:liquibase-core:4.29.2'
    liquibaseRuntime 'com.mysql:mysql-connector-j:8.4.0'
}

liquibase {
    activities {
        main {
            changeLogFile 'src/main/resources/db/changelog/db.changelog-master.yaml'
            url 'jdbc:mysql://127.0.0.1:3306/study'
            username 'root'
            password 'root'
        }
    }
}
```

```bash
./gradlew update
```

---

## 十六、团队协作规范

### 16.1 命名规范

```text
{日期或递增序号}-{作者缩写}-{简短描述}.yaml
```

```text
20261101-leo-create-student-table.yaml
20261102-zhang-add-student-email.yaml
20261103-wang-create-score-index.yaml
```

或者按版本号：

```text
v1.0.0-001-create-student.yaml
v1.0.0-002-create-score.yaml
v1.1.0-001-add-email.yaml
```

> ⚠️ **`id` 必须全局唯一**（配合 `author`）。**推荐 `日期-序号`，如 `20261101-01`**，天然有序且不会冲突。

### 16.2 提交规范

```text
feat(db): 学生表增加 email 字段

- changelog: 20261102-leo-add-student-email.yaml
- 影响表: student
- 回滚: 新增字段，可回滚（数据丢失需备份）
```

### 16.3 Code Review 检查清单

- [ ] changeset 的 `id` 是否唯一、`author` 是否真实
- [ ] 是否修改了**已执行**的 changeset（**禁止**）
- [ ] 是否有对应的 `rollback`
- [ ] 破坏性变更（drop/rename/类型变更）是否做了兼容设计
- [ ] 测试数据是否标了 `context: dev`
- [ ] 索引命名是否规范、是否与业务查询匹配
- [ ] 大表 DDL 是否评估了锁表风险
- [ ] 是否在低环境验证过

### 16.4 分支与合并

| 做法 | 说明 |
| :--- | :--- |
| 每个功能分支带自己的 changelog | 合并时 master 文件必然冲突 |
| **master 只追加**，冲突手动解决 | 合并后按合并顺序重排 |
| **CI 检查** | `liquibase validate` + `updateSql` 在临时库上跑 |

> ⚠️ **两个分支都用了 `id=20261101-05`** → 合并后同名不同内容，**后执行的会被跳过**（因为唯一键相同）。**用 `日期-序号-描述` 里带作者/日期能大幅降低概率**，但根本解法是**合并后 review master 的 include 顺序**。

### 16.5 版本发布

```yaml
# 每次发版打一个 tag
- changeSet:
    id: 20261101-tag-1.0.0
    author: leo
    changes:
      - tagDatabase:
          tag: v1.0.0
```

```bash
liquibase rollback v1.0.0
```

---

## 十七、实际项目案例：学生管理系统

### 17.1 版本 1.0：基础表

```yaml
# db/changelog/001-create-student.yaml
databaseChangeLog:
  - changeSet:
      id: 20260901-01
      author: leo
      comment: 创建班级表
      changes:
        - createTable:
            tableName: clazz
            remarks: 班级
            columns:
              - column:
                  name: id
                  type: BIGINT
                  autoIncrement: true
                  remarks: 主键
                  constraints: { primaryKey: true, nullable: false }
              - column:
                  name: name
                  type: VARCHAR(50)
                  remarks: 班级名称
                  constraints: { nullable: false }
              - column:
                  name: create_time
                  type: DATETIME
                  defaultValueComputed: CURRENT_TIMESTAMP

  - changeSet:
      id: 20260901-02
      author: leo
      comment: 创建学生表
      changes:
        - createTable:
            tableName: student
            remarks: 学生
            columns:
              - column:
                  name: id
                  type: BIGINT
                  autoIncrement: true
                  constraints: { primaryKey: true, nullable: false }
              - column:
                  name: name
                  type: VARCHAR(20)
                  constraints: { nullable: false }
              - column:
                  name: age
                  type: INT
              - column:
                  name: sex
                  type: CHAR(1)
                  defaultValue: "1"
              - column:
                  name: class_id
                  type: BIGINT
              - column:
                  name: score
                  type: DECIMAL(5,2)
              - column:
                  name: create_time
                  type: DATETIME
                  defaultValueComputed: CURRENT_TIMESTAMP
              - column:
                  name: update_time
                  type: DATETIME

        - addForeignKeyConstraint:
            baseTableName: student
            baseColumnNames: class_id
            referencedTableName: clazz
            referencedColumnNames: id
            constraintName: fk_student_clazz

        - createIndex:
            tableName: student
            indexName: idx_student_class_id
            columns:
              - column: { name: class_id }
```

### 17.2 版本 1.1：加字段（带数据回填）

```yaml
# db/changelog/002-add-student-email.yaml
databaseChangeLog:
  - changeSet:
      id: 20261101-01
      author: leo
      comment: 学生表增加 email 字段（先可空，避免锁表与默认值问题）
      changes:
        - addColumn:
            tableName: student
            columns:
              - column:
                  name: email
                  type: VARCHAR(100)
                  remarks: 邮箱

  - changeSet:
      id: 20261101-02
      author: leo
      comment: 回填 email 为学号@school.edu
      changes:
        - sql:
            sql: "UPDATE student SET email = CONCAT(id, '@school.edu') WHERE email IS NULL"
      rollback:
        - sql:
            sql: "UPDATE student SET email = NULL"

  - changeSet:
      id: 20261101-03
      author: leo
      comment: email 加唯一约束
      changes:
        - addUniqueConstraint:
            tableName: student
            columnNames: email
            constraintName: uk_student_email
```

> 💡 **为什么分三个 changeset**：加字段、回填、加约束是三件独立的事，任何一步失败都能准确定位、精确重试。

### 17.3 版本 1.2：改列名（扩展-收缩）

```yaml
# 阶段 1：新增字段 + 双写（应用层改）
- changeSet:
    id: 20261102-01
    author: leo
    comment: 新增 nickname 字段
    changes:
      - addColumn:
          tableName: student
          columns:
            - column: { name: nickname, type: VARCHAR(50) }

- changeSet:
    id: 20261102-02
    author: leo
    comment: 把 name 回填到 nickname
    changes:
      - sql:
          sql: "UPDATE student SET nickname = name WHERE nickname IS NULL"
```

```yaml
# 阶段 2：确认应用只读 nickname、且已上线一段时间后，才能删 name
- changeSet:
    id: 20261115-01
    author: leo
    comment: 删除旧字段 name（应用已完全切换）
    changes:
      - dropColumn:
          tableName: student
          columnName: name
    rollback:
      - addColumn:
          tableName: student
          columns:
            - column: { name: name, type: VARCHAR(20) }
```

### 17.4 版本 1.3：字典数据 + 测试数据分离

```yaml
# 生产也需要的基础字典
- changeSet:
    id: 20261102-03
    author: leo
    changes:
      - insert:
          tableName: sys_dict
          columns:
            - column: { name: type, value: "SEX" }
            - column: { name: code, value: "1" }
            - column: { name: label, value: "男" }
      - insert:
          tableName: sys_dict
          columns:
            - column: { name: type, value: "SEX" }
            - column: { name: code, value: "2" }
            - column: { name: label, value: "女" }
    rollback:
      - delete:
          tableName: sys_dict
          where: "type = 'SEX'"
```

```yaml
# 仅开发/测试环境的测试数据
- changeSet:
    id: 20261102-04
    author: leo
    context: dev,test
    changes:
      - insert:
          tableName: student
          columns:
            - column: { name: name, value: "张三" }
            - column: { name: age, value: 20 }
            - column: { name: class_id, value: 1 }
```

### 17.5 版本 1.4：索引优化

```yaml
- changeSet:
    id: 20261103-01
    author: leo
    comment: 成绩查询走 (class_id, score) 联合索引
    changes:
      - createIndex:
          tableName: student
          indexName: idx_student_class_score
          columns:
            - column: { name: class_id }
            - column: { name: score }
```

> ⚠️ **加索引前先看 `EXPLAIN`**，确认能命中。Liquibase 只负责"加"，不负责"判断该不该加"。

### 17.6 master 文件

```yaml
databaseChangeLog:
  - include:
      file: db/changelog/001-create-student.yaml
  - include:
      file: db/changelog/002-add-student-email.yaml
  - include:
      file: db/changelog/003-alter-student-name.yaml
  - include:
      file: db/changelog/004-dict-data.yaml
  - include:
      file: db/changelog/005-student-index.yaml
```

### 17.7 一个完整的工程目录

```text
demo-liquibase/
├── pom.xml
└── src/main/
    ├── java/com/example/demo/
    │   ├── DemoApplication.java
    │   ├── entity/Student.java
    │   ├── mapper/StudentMapper.java
    │   └── controller/StudentController.java
    └── resources/
        ├── application.yml
        ├── application-dev.yml
        ├── application-prod.yml
        └── db/changelog/
            ├── db.changelog-master.yaml
            ├── 001-create-student.yaml
            ├── 002-add-student-email.yaml
            ├── 003-alter-student-name.yaml
            ├── 004-dict-data.yaml
            └── 005-student-index.yaml
```

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/study?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf8
    username: root
    password: root
  liquibase:
    change-log: classpath:/db/changelog/db.changelog-master.yaml
    contexts: dev
  jpa:
    hibernate:
      ddl-auto: none            # 必须关掉！结构交给 Liquibase
```

> ⚠️ **`spring.jpa.hibernate.ddl-auto` 必须设为 `none` 或 `validate`**。`update` 会和 Liquibase 打架。

---

## 十八、与 MyBatis / JPA 的配合

### 18.1 职责划分

| 组件 | 职责 |
| :--- | :--- |
| **Liquibase** | 表结构（DDL）、基础字典数据、索引、约束 |
| **MyBatis / MyBatis-Plus** | 业务数据读写 |
| **JPA（如果使用）** | `ddl-auto: none`，只做 ORM 映射 |

### 18.2 与 MyBatis-Plus 的典型组合

```yaml
spring:
  datasource:
    url: jdbc:mysql://...
  liquibase:
    change-log: classpath:/db/changelog/db.changelog-master.yaml
  sql:
    init:
      mode: never              # 不要用 schema.sql/data.sql，统一交给 Liquibase

mybatis-plus:
  mapper-locations: classpath*:mapper/**/*.xml
  global-config:
    db-config:
      logic-delete-field: deleted
```

### 18.3 与 JPA 的校验模式

```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: validate       # 启动时校验实体与表是否一致
```

> 💡 `validate` 是很好的"防漂移"机制：**如果 Liquibase 漏加字段，启动直接失败**，而不是等到运行时 `Unknown column`。

### 18.4 实体类与表结构的同步

- **表结构以 Liquibase 为准**，实体类跟随
- 新增字段要**同时**提交：changelog + 实体类
- Code Review 检查二者是否一致
- 可以用 `liquibase diff` 对比"实体推导的库"和"实际库"

---

## 十九、踩坑清单

| # | 坑 | 现象 | 解决 |
| :--- | :--- | :--- | :--- |
| 1 | 修改已执行的 changeset | `Validation Failed: check sum` | 新建 changeset；不要改历史 |
| 2 | changeset `id` 重复 | 后者被跳过 | 用 `日期-序号` |
| 3 | 测试数据没标 `context` | 生产被插入测试数据 | 显式 `context: dev,test` |
| 4 | `includeAll` 文件名没补零 | 执行顺序错乱 | `001/002/010` |
| 5 | include 顺序错 | 建表前加索引 | master 按依赖排序 |
| 6 | MySQL DDL 无法回滚 | rollback 失败 | 接受现实，靠备份 + forward fix |
| 7 | `sql` change 没写 rollback | 回滚报 `No inverse` | 手写 `rollback` |
| 8 | 大表 `MODIFY` 锁表 | 生产卡死 | gh-ost / 低峰 / 扩展-收缩 |
| 9 | 多实例启动抢锁 | 启动慢/锁残留 | 检查 `DATABASECHANGELOGLOCK` |
| 10 | `drop-first: true` 误配 | **库被清空** | 只在 test profile 配 |
| 11 | YAML 缩进错 | `ChangeLogParseException` | 统一格式化规则 |
| 12 | `dbms` 写错 | changeset 从不执行 | 用正确的小写标识 |
| 13 | 路径写错 | `does not exist` | `relativeToChangelogFile` 统一 |
| 14 | 与 `ddl-auto: update` 混用 | 表结构漂移 | `ddl-auto: none/validate` |
| 15 | 存量库直接 `update` | 表已存在报错 | `changelogSync` / baseline |
| 16 | `defaultValueComputed` 与 `defaultValue` 混用 | 默认值不对 | 函数用 Computed，常量用 defaultValue |
| 17 | 主键自增在 PostgreSQL 不生效 | 插入报主键 null | 用 `bigSerial`/序列 |
| 18 | 索引名重复 | `Duplicate key name` | `idx_表名_列名` |
| 19 | `runOnChange` 用在 `insert` | 数据重复 | 仅用于视图/存储过程 |
| 20 | 生产 `enabled: false` 忘了执行 | 字段不存在 | CI 流程保证执行 |
| 21 | changelog 打包丢失 | `ChangeLogParseException` | resources 目录 + 构建检查 |
| 22 | `validate` 在 CI 中未跑 | 语法错误上线才暴露 | 流水线加 `liquibase validate` |
| 23 | 中文注释乱码 | 表注释乱码 | 连接串 `characterEncoding=utf8` |
| 24 | 环境间手动执行不一致 | 结构漂移 | `liquibase diff` 定期对比 |

---

## 📌 在 Spring Boot 中

| 本篇概念 | Spring Boot 中的对应 |
| :--- | :--- |
| 自动执行 | `spring.liquibase.enabled` + 启动时 `SpringLiquibase` Bean |
| changelog 路径 | `spring.liquibase.change-log`（默认 `classpath:/db/changelog/db.changelog-master.yaml`） |
| 环境过滤 | `spring.liquibase.contexts` / `labels` |
| schema | `spring.liquibase.default-schema` / `liquibase-schema` |
| 台账表名 | `spring.liquibase.database-change-log-table` |
| 测试清库 | `spring.liquibase.drop-first`（**仅测试**） |
| 回滚文件 | `spring.liquibase.rollback-file` |
| 与 JPA | `spring.jpa.hibernate.ddl-auto: none/validate` |
| 与 MyBatis | 无冲突，结构由 Liquibase 管，SQL 由 MyBatis 管 |
| CI/CD | `liquibase-maven-plugin` 或 Liquibase CLI |

**和本仓库其他文档的关系**：

- [MySQL 学习文档](MySQL学习文档.md) → Liquibase 输出的就是这些 SQL
- [MyBatis学习文档](MyBatis学习文档.md) → 结构由 Liquibase 管，SQL 由 MyBatis 写
- [Redis学习文档](Redis学习文档.md) → 无关，但同属基础设施
- [54-数据库版本控制_Flyway](../Spring实战/54-数据库版本控制_Flyway.md) → **Flyway 的姐妹篇**，可对照阅读
- [PostgreSQL学习文档](PostgreSQL学习文档.md) → 多方言场景下 Liquibase 的优势更明显

> 一句话：**Liquibase 把"改数据库"从一次口头通知，变成了一次可评审、可追溯、可回滚的代码提交。**

---

## 本章小结

1. **核心价值**：把数据库变更纳入 Git，让每个环境的 schema 处于同一条已知版本线上。
2. **三层概念**：Changelog（文件）→ ChangeSet（原子单元）→ Change（操作）；ChangeSet 由 `id + author + filename` 唯一标识。
3. **禁止修改历史**：已执行的 changeset 改动会产生校验和冲突，**增量必须新建 changeset**。
4. **组织方式**：master 只做 `include`，变更按日期/序号拆分文件；`includeAll` 要求文件名能正确排序。
5. **回滚**：结构化变更可自动回滚，**数据变更基本不可回滚**；生产更常用 forward fix + Expand-Contract。
6. **Preconditions**：让变更对"环境已有人工修改"的现状容错；`MARK_RAN` 要慎用。
7. **Contexts**：区分环境，**测试数据不标 context 会带到生产**。
8. **存量接入**：`generateChangeLog` 生成基线 + `changelogSync` 标记已执行。
9. **生产安全**：`updateSql` 预览 + DBA 审核 + 低环境验证 + 大表 DDL 特殊处理。
10. **协作**：命名规范、只追加不修改、CI 校验、Review 回滚脚本。

**动手练习**：

1. 用 Spring Boot + Liquibase 从零建一张 `student` 表，启动后查 `DATABASECHANGELOG` 验证记录。
2. 新增一个 `email` 字段并回填数据，写对应的 `rollback`，然后在测试库执行一次回滚并验证。
3. 故意修改一个已执行的 changeset，复现校验和错误，再用"新建 changeset"的方式修复。
4. 用 `context: dev` 插入一条测试数据，分别在 dev/prod 的 context 下启动，验证生产不执行。
5. 用 `generateChangeLog` 把一个已有库导出成 baseline，再用 `changelogSync` 接入。
6. 用 `liquibase-maven-plugin` 的 `updateSQL` 生成发布 SQL，并解释为什么生产要"先生成再执行"。
7. 模拟两个分支写了相同 `id` 的 changeset，合并后观察执行结果并解释原因。
