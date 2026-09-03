# 54 - 数据库版本控制 Flyway

> 对应项目模块：`demo-flyway`
> 前置知识：已学完前面数据库相关模块（13-18），了解 Spring Boot 如何连接数据库、执行 SQL
> 学习目标：理解数据库迁移（Migration）解决什么问题，掌握 Flyway 的脚本命名规则、执行机制、配置项，能独立为项目添加版本化的数据库脚本。

---

## 一、本模块要解决什么问题？

### 1.1 没有 Flyway 之前，数据库变更是怎么管理的？

前端同学可能没接触过这个痛点，先描述一个真实场景：

一个项目从开发到上线，数据库表结构会不断变化。比如用户表 `t_user`：

- 第一版：建表，有 `id`、`username`、`password` 三个字段
- 第二版：加个 `email` 字段
- 第三版：把 `password` 改成 `password_hash`，长度从 32 变 64
- 第四版：加索引
- ……

这些变更怎么落到**所有环境**（开发、测试、生产）的数据库上？传统做法是：

1. DBA 手动执行 SQL，或开发者把 SQL 脚本丢进群里，谁谁谁去执行一下
2. 用一个 `init.sql` 文件维护所有建表语句，每次变更直接改这个文件
3. 用 Navicat 之类的工具手动改表结构

这些做法的致命问题：

- **不可追溯**：生产环境的表结构是怎么一步步变成现在这样的？没人知道
- **环境不一致**：开发改了表忘了同步给测试，测试环境跑不起来
- **重复执行**：同一个 `ADD COLUMN` 脚本执行两次就报错（列已存在）
- **协作冲突**：两个人同时改表，SQL 脚本合并冲突，谁先谁后乱套
- **回滚困难**：上线后发现表改错了，怎么退回上一个版本？

### 1.2 Flyway 的解决方案

Flyway 是一个**数据库版本控制工具**，它把数据库的每一次结构变更当成一次"迁移"（migration），用版本化的 SQL 脚本管理，并在数据库里建一张元数据表记录"哪些脚本执行过"。

> 💡 前端类比：Flyway 之于数据库，就像 Git 之于代码——每次变更有版本号、有记录、可追溯、可回滚。如果你用过 Prisma 的 `prisma migrate`，或者 Rails 的 `db:migrate`、Django 的 `migrations`，那就是一模一样的概念。Flyway 是 Java 生态里最主流的实现。

核心思路一句话：**把数据库 schema 也当代码一样做版本控制**。

### 1.3 Flyway vs Liquibase

Java 生态两大数据库迁移工具：

| 维度 | Flyway | Liquibase |
| --- | --- | --- |
| 脚本格式 | 原生 SQL | XML/YAML/JSON（也支持 SQL） |
| 学习成本 | 低（会写 SQL 就行） | 中（要学 Liquibase 的 XML 标签） |
| 灵活性 | SQL 直接，所见即所得 | 跨数据库能力强（同一份 XML 生成不同方言） |
| 社区活跃度 | 高 | 高 |
| 推荐场景 | 单一数据库、追求简单 | 需要支持多种数据库（MySQL+Oracle+PG） |

本模块用 Flyway，因为它对新手最友好——你只需要会写 SQL。

---

## 二、项目结构

```
demo-flyway/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/xkcoding/flyway/
    │   │   └── SpringBootDemoFlywayApplication.java   # 启动类（无业务代码）
    │   └── resources/
    │       ├── application.yml                         # 配置（数据源 + Flyway）
    │       └── db/migration/                           # ★ Flyway 默认扫描目录
    │           ├── V1_0__INIT.sql                      # 版本 1.0：初始化建表
    │           └── V1_1__ALTER.sql                      # 版本 1.1：修改表注释
    └── test/java/com/xkcoding/
        └── AppTest.java                                # 占位测试
```

关键点：**`src/main/resources/db/migration/` 是 Flyway 约定的默认脚本目录**，放这里的 `.sql` 文件会被自动扫描执行。这个目录名是约定，不是随便起的。

> 💡 前端类比：这就像 Vite 约定 `src/` 是源码目录、`public/` 是静态资源目录——Flyway 约定 `db/migration/` 是迁移脚本目录。约定优于配置。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Web 起步依赖（本模块其实没写 Web 接口，但保留它方便后续扩展） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. ★ Flyway 核心依赖 -->
    <dependency>
        <groupId>org.flywaydb</groupId>
        <artifactId>flyway-core</artifactId>
    </dependency>

    <!-- 3. JDBC 起步依赖（提供数据源、JdbcTemplate） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jdbc</artifactId>
    </dependency>

    <!-- 4. MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
        <scope>runtime</scope>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

逐个看：

- **`flyway-core`**：Flyway 的核心库。注意它**没有**对应的 `spring-boot-starter-flyway`，Spring Boot 通过 `flyway-autoconfigure` 模块（包含在 starter 里）自动装配 Flyway，只要 classpath 上有 `flyway-core`，启动时就会自动触发迁移。
- **`spring-boot-starter-data-jdbc`**：提供数据源（HikariCP）、JdbcTemplate。Flyway 需要一个数据源来连接数据库、执行 SQL、写历史记录表。这里没用 JPA 是因为本模块只演示建表，不需要 ORM。
- **`mysql-connector-java`**：MySQL JDBC 驱动，`<scope>runtime</scope>` 表示只在运行时需要（编译期不需要 JDBC API）。

> ⚠️ 注意：Flyway 的版本由 Spring Boot 的 BOM（`spring-boot-dependencies`）统一管理。本模块 pom 里没写 `flyway-core` 的版本号，版本由父 POM 锁定（Spring Boot 2.1.0 对应 Flyway 5.2.1）。**不要手动改 Flyway 版本**，否则可能和 Spring Boot 不兼容。

---

## 四、逐行拆解 application.yml

```yaml
spring:
  flyway:
    enabled: true                    # ① 启用 Flyway
    validate-on-migrate: true       # ② 迁移前校验脚本
    clean-disabled: true            # ③ 禁用 clean（生产必关）
    check-location: false           # ④ 不检查脚本路径是否存在
    baseline-on-migrate: true       # ⑤ 已有库时建立基线
    baseline-version: 0             # ⑥ 基线版本号
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/flyway-test?useSSL=false
    username: root
    password: root
    type: com.zaxxer.hikari.HikariDataSource
```

### 4.1 Flyway 配置项详解

| 配置项 | 作用 | 本模块取值 | 实际开发建议 |
| --- | --- | --- | --- |
| `enabled` | 是否启用 Flyway 自动迁移 | `true` | 生产可设 `false` 临时跳过，或用 Profile 区分 |
| `validate-on-migrate` | 迁移前校验已执行脚本是否被篡改 | `true` | **保持 true**，防止有人偷偷改了老脚本 |
| `clean-disabled` | 是否禁用 `flyway clean`（删库重建） | `true` | **生产必须 true**，否则误执行 clean 会删全表 |
| `check-location` | 启动时检查脚本目录是否存在 SQL 文件 | `false` | 项目初期没脚本时设 false 避免报错 |
| `baseline-on-migrate` | 已有表结构的库上首次运行时，建立基线 | `true` | **老项目接入 Flyway 必须设 true** |
| `baseline-version` | 基线版本号 | `0` | 表示"0 版本之前的变更不管，从 0 之后开始管" |

### 4.2 重点理解 `baseline-on-migrate`

这是最容易让新手困惑的配置。场景：

- 你的数据库已经存在一堆表（之前手动建的），但没有 `flyway_schema_history` 表
- 这时启动 Flyway，它发现"库里已经有表了，但我没有迁移记录"，默认会**报错拒绝执行**
- 设 `baseline-on-migrate: true` 后，Flyway 会在当前状态打一个"基线"（baseline），版本号为 `baseline-version`（这里是 0），表示"0 版本之前的表结构我不管，从 0 之后的脚本才开始执行"

> 💡 前端类比：这就像给一个没有 Git 的老项目执行 `git init` 然后 `git commit` 作为初始提交——已有的代码（表结构）当作基线，之后的每次变更才纳入版本控制。

### 4.3 数据源配置

```yaml
datasource:
  url: jdbc:mysql://127.0.0.1:3306/flyway-test?useSSL=false
  username: root
  password: root
  type: com.zaxxer.hikari.HikariDataSource
```

- 数据库 `flyway-test` 需要提前创建好（Flyway 不会帮你建库，只建表）
- `type` 显式指定 HikariCP 连接池（其实 Spring Boot 2.x 默认就是它，不写也行）

> ⚠️ 实际开发中密码不要明文写，用 `${DB_PASSWORD}` 从环境变量注入，参考 02-Properties 模块。

---

## 五、SQL 迁移脚本：命名规则是核心

Flyway 的灵魂在于**脚本命名规则**。放在 `db/migration/` 下的 SQL 文件，文件名必须遵循：

```
V<版本号>__<描述>.sql
```

### 5.1 命名规则拆解

本模块有两个脚本：

| 文件名 | 拆解 | 含义 |
| --- | --- | --- |
| `V1_0__INIT.sql` | `V` + `1_0` + `__` + `INIT` | 版本 1.0，初始化建表 |
| `V1_1__ALTER.sql` | `V` + `1_1` + `__` + `ALTER` | 版本 1.1，修改表 |

详细规则：

- **`V`**：固定前缀，表示 Versioned（版本化迁移，只执行一次）
- **版本号**：`1_0`、`1_1`，多段用 `_` 分隔，等价于 `1.0`、`1.1`。也可以用 `V1`、`V2`、`V20200305` 等
- **`__`（两个下划线）**：版本号和描述之间的分隔符，**必须是两个下划线**，一个都不行
- **描述**：可读说明，如 `INIT`、`ADD_EMAIL_COLUMN`
- **`.sql`**：扩展名

> ⚠️ 命名错误是最常见的坑：
> - `V1_0_INIT.sql`（只有一个下划线）→ Flyway 不认，脚本不执行
> - `v1_0__init.sql`（小写 v）→ 默认不认（Flyway 6.x 前区分大小写）
> - `V1.0__INIT.sql`（版本号用点）→ 部分版本解析异常，建议用 `_`

### 5.2 `V` vs `R`：执行一次 vs 每次执行

| 前缀 | 含义 | 执行时机 | 能否修改 |
| --- | --- | --- | --- |
| `V` | Versioned（版本迁移） | 版本号递增时执行**一次** | **不可修改**，改了启动报错 |
| `R` | Repeatable（可重复迁移） | 内容变化时**每次重新执行** | 可修改（如视图、存储过程） |

- `V` 脚本：建表、加字段、改字段这类**不可逆的结构变更**，执行一次就完事
- `R` 脚本：视图、存储过程、函数这类"重建一遍结果一样"的对象，内容变了就重新执行

> 💡 前端类比：`V` 脚本像 Git 的 commit（不可变，改了就乱），`R` 脚本像 Git 的分支指针（可移动）。

### 5.3 拆解 `V1_0__INIT.sql`

```sql
DROP TABLE IF EXISTS `t_user`;
CREATE TABLE `t_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username` varchar(32) NOT NULL COMMENT '用户名',
  `password` varchar(32) NOT NULL COMMENT '加密后的密码',
  `salt` varchar(32) NOT NULL COMMENT '加密使用的盐',
  `email` varchar(32) NOT NULL COMMENT '邮箱',
  `phone_number` varchar(15) NOT NULL COMMENT '手机号码',
  `status` int(2) NOT NULL DEFAULT '1' COMMENT '状态，-1：逻辑删除，0：禁用，1：启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_login_time` datetime DEFAULT NULL COMMENT '上次登录时间',
  `last_update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上次更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `phone_number` (`phone_number`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8 COMMENT='1.0-用户表';
```

这是一个标准的 MySQL 建表脚本。注意几点：

- 开头 `DROP TABLE IF EXISTS`：保证幂等（重复执行不报错），但**注意**：这只在第一次执行时有意义，因为 Flyway 保证 `V` 脚本只执行一次，第二次启动根本不会再跑这个脚本
- 字段都有 `COMMENT`：好习惯，方便团队协作
- 三个唯一键（username、email、phone_number）：业务约束
- `ENGINE=InnoDB`：支持事务的存储引擎

### 5.4 拆解 `V1_1__ALTER.sql`

```sql
ALTER TABLE t_user COMMENT = '用户 v1.1';
```

版本 1.1 只做了一件小事：改表注释。这是为了演示"增量迁移"——不碰已有结构，只做增量变更。实际开发中，这类脚本通常是 `ALTER TABLE t_user ADD COLUMN xxx`、`CREATE INDEX` 等。

---

## 六、启动类：为什么几乎没有代码？

```java
@SpringBootApplication
public class SpringBootDemoFlywayApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoFlywayApplication.class, args);
    }
}
```

启动类和 HelloWorld 一模一样，没有任何 Flyway 相关代码。**这就是 Flyway 的自动配置魅力**：

1. classpath 上有 `flyway-core`
2. 配置文件里有数据源
3. Spring Boot 的 `FlywayAutoConfiguration` 自动检测到这两个条件，在应用启动时自动创建 `Flyway` Bean、扫描 `db/migration/`、执行迁移

你不需要写任何一行 Java 代码来触发迁移——**启动即迁移**。

> 💡 前端类比：这像 Vite 的插件自动加载——你装了 `@vitejs/plugin-vue`，它就自动处理 `.vue` 文件，不用你在 `vite.config.ts` 里手动调。Spring Boot 的自动配置是同样的"条件化装配"思路。

---

## 七、运行与验证

### 7.1 准备数据库

先在 MySQL 里建库（Flyway 不建库，只建表）：

```sql
CREATE DATABASE flyway_test DEFAULT CHARACTER SET utf8mb4;
```

### 7.2 启动项目

```sh
mvn spring-boot:run
```

启动日志会看到 Flyway 的输出：

```
Flyway Community Edition 5.2.1 by Boxfuse
HikariPool-1 - Starting...
HikariPool-1 - Start completed.
Database: jdbc:mysql://127.0.0.1:3306/flyway-test (MySQL 5.7)
Successfully validated 1 migration (execution time 00:00.015s)
Creating Schema History table: `flyway-test`.`flyway_schema_history`
Current version of schema `flyway-test`: << Empty Schema >>
Migrating schema `flyway-test` to version 1.0 - INIT
Successfully applied 1 migration to schema `flyway-test`
```

### 7.3 验证结果

启动后检查数据库，会有**两张表**：

1. **`flyway_schema_history`**（Flyway 自动建的元数据表）：记录每个脚本的版本号、文件名、校验和、执行时间、是否成功
2. **`t_user`**（我们的业务表）：按 `V1_0__INIT.sql` 建的

`flyway_schema_history` 表结构大致：

| installed_rank | version | description | type | script | checksum | installed_on | success |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.0 | INIT | SQL | V1_0__INIT.sql | 1234567890 | 2026-... | true |
| 2 | 1.1 | ALTER | SQL | V1_1__ALTER.sql | 9876543210 | 2026-... | true |

### 7.4 再次启动：验证幂等

第二次启动，日志变成：

```
Successfully validated 2 migrations
Current version of schema `flyway-test`: 1.1
Schema `flyway-test` is up to date. No migration necessary.
```

Flyway 校验了两个脚本（没被篡改），发现当前版本已经是 1.1，没有新脚本，于是什么都不执行。**这就是幂等性**——启动多少次都不会重复执行已迁移的脚本。

### 7.5 加新脚本：验证增量

在 `db/migration/` 下新建 `V1_2__ADD_AGE.sql`：

```sql
ALTER TABLE t_user ADD COLUMN age int(3) DEFAULT 0 COMMENT '年龄';
```

重启，Flyway 会自动执行这个新脚本，把版本推进到 1.2。

---

## 八、动手练习

1. **体验命名规则**：故意把新脚本命名为 `V1_2_ADD_AGE.sql`（一个下划线），启动，观察 Flyway 是否执行它（应该不认）。
2. **体验篡改检测**：启动成功后，修改 `V1_0__INIT.sql`（比如加个字段），再启动，观察 `validate-on-migrate` 报错（checksum 不匹配）。
3. **加增量脚本**：新建 `V1_2__ADD_AGE.sql` 加 age 字段，启动验证。
4. **体验 R 脚本**：新建 `R__create_view.sql`，写一个建视图语句，启动执行；修改视图内容，再启动，观察是否重新执行。
5. **老库接入**：手动建一个库（不通过 Flyway），然后开启 Flyway，用 `baseline-on-migrate: true` 接入，观察基线建立过程。
6. **多环境配置**：用 Profile 让 dev 环境 `clean-disabled: false`（可清库重建），prod 环境 `clean-disabled: true`，体会配置分层。

---

## 九、本模块知识点总结（结合实际开发详解）

数据库迁移是工程化的基础设施，几乎所有正规项目都会用。下面把核心知识点放到真实开发场景里讲透。

### 9.1 为什么必须做数据库版本控制？

**实际开发中的痛点（没有迁移工具时）：**

- 多人协作时，A 改了表结构，B 拉代码后跑不起来（B 的库里没那个字段）
- 新人入职，本地数据库怎么初始化？给个 `init.sql`？但 `init.sql` 每次变更都要手动同步
- 生产部署时，DBA 要手动执行一堆 SQL，容易漏执行、重复执行
- 线上出问题要回滚代码，但表结构已经变了，回滚后代码和新表结构不兼容

**Flyway 解决了什么：**

1. **环境一致性**：所有环境执行同一套脚本，开发/测试/生产的表结构保证一致
2. **自动化**：应用启动时自动执行未跑过的脚本，无需人工干预
3. **可追溯**：`flyway_schema_history` 记录了每次变更的版本、时间、内容
4. **幂等**：每个脚本只执行一次，重复启动不会重复执行
5. **协作友好**：新增变更只需加一个新版本脚本，不碰老脚本

> 💡 前端类比：这就像把数据库 schema 也纳入了"构建产物"的一部分。前端构建产物是 JS/CSS bundle，后端构建产物除了 jar 包，还包括"数据库应该长什么样"——Flyway 让这个状态可复现、可追溯。

### 9.2 脚本命名规则：Flyway 的契约

**命名规则是 Flyway 最核心的约定**，必须牢记：

```
V{版本号}__{描述}.sql   ← 版本迁移（执行一次）
R{描述}.sql             ← 可重复迁移（内容变就重新执行）
```

**版本号排序规则：**

- `V1` < `V1_1` < `V1_2` < `V2` < `V2_1` < `V10`
- 多段用 `_` 分隔，按数字比较（不是字符串比较，所以 `V2` 在 `V10` 前）
- 也可以用日期版本号：`V20260903__xxx`，适合按日期组织

**实际开发最佳实践：**

1. **版本号递增，不跳号**：`V1`、`V2`、`V3`，不要 `V1`、`V3`、`V5`（虽然能跑，但看着乱）
2. **描述要语义化**：`V3__add_user_age_column` 比 `V3__update` 好得多
3. **一个脚本只做一件事**：不要把"加字段"+"改索引"+"建表"塞一个脚本里，方便回滚定位
4. **脚本一旦提交，绝不修改**：要改就加新脚本。比如想改 `V1` 建的表，不要回去改 `V1_0__INIT.sql`，而是加 `V1_3__modify_xxx.sql`

**常见坑：**

- 两个开发者同时提交 `V2__xxx.sql`，版本号冲突 → 约定版本号分配规则（如按日期、按工单号）
- 脚本写错（语法错误）执行失败 → Flyway 会在 `flyway_schema_history` 留一条 `success=false` 记录，**下次启动不会自动重试**，需要手动删掉这条失败记录、修复脚本后再启动
- 老脚本被篡改（如改了内容）→ `validate-on-migrate` 检测到 checksum 变化，启动报错。解决：要么恢复脚本原样，要么用 `flyway repair` 更新 checksum（慎用）

### 9.3 `flyway_schema_history` 表：迁移的"账本"

Flyway 在目标库里自动建这张表，它是整个迁移机制的基石：

| 字段 | 含义 |
| --- | --- |
| `installed_rank` | 执行顺序（排名） |
| `version` | 脚本版本号（如 1.0、1.1） |
| `description` | 脚本描述 |
| `type` | 迁移类型（SQL、JDBC 等） |
| `script` | 脚本文件名 |
| `checksum` | 脚本内容校验和（用于检测篡改） |
| `installed_on` | 执行时间 |
| `execution_time` | 执行耗时 |
| `success` | 是否成功 |

**实际开发要点：**

1. **这张表不要手动改**，除非你确切知道在做什么（如清理失败记录）
2. **不要删这张表**，删了等于丢失所有迁移历史，Flyway 会以为是个空库，重新执行所有脚本（可能因为表已存在而报错）
3. **多模块/多数据源时**，每个数据源都有自己的 `flyway_schema_history`
4. **表名可自定义**：`spring.flyway.table=my_migration_history`，但一般保持默认

### 9.4 关键配置项的实际开发策略

**`baseline-on-migrate`：老项目接入 Flyway 的关键**

实际开发中，很多老项目中途接入 Flyway。这时数据库已经有表了，直接启动 Flyway 会报错（"库非空但没有历史表"）。正确做法：

1. 设 `baseline-on-migrate: true`、`baseline-version: 0`
2. 启动，Flyway 建历史表，打一条基线记录（版本 0）
3. 之后只写版本号 > 0 的新脚本，Flyway 只执行新脚本，不管老表

**`clean-disabled`：生产环境的生命线**

`flyway clean` 会**删除整个 schema 的所有表**然后重建。这在开发环境很爽（一键重置），但在生产是灾难。**生产环境必须 `clean-disabled: true`**，防止误操作。

**`validate-on-migrate`：防止偷偷改脚本**

开启后，每次启动会校验已执行脚本的 checksum。如果有人偷偷改了老脚本（比如加个字段），启动会报错。**保持 true**，这是团队协作的保障。

**多环境配置策略：**

```yaml
spring:
  flyway:
    # 开发环境可以 clean 重建
    clean-disabled: false
    baseline-on-migrate: true
  profiles: dev
---
spring:
  flyway:
    # 生产环境严格
    clean-disabled: true
    validate-on-migrate: true
  profiles: prod
```

### 9.5 Flyway 的执行流程

启动时 Flyway 做的事：

1. 连接数据源，检查 `flyway_schema_history` 表是否存在，不存在则创建
2. 扫描 `db/migration/`（或配置的 `locations`），解析所有脚本，按版本号排序
3. 查询历史表，得到已执行的版本列表
4. 校验：已执行脚本的 checksum 是否和文件一致（`validate-on-migrate`）
5. 对比：找出"文件里有、但历史表里没执行过"的脚本
6. 按版本号顺序，逐个执行未执行的脚本，每执行完写一条历史记录
7. 全部成功，应用继续启动；某个失败，启动中断（默认）

> 💡 前端类比：这像 Vite 启动时扫描 `src/`、解析依赖图、按拓扑排序编译——Flyway 是扫描 `db/migration/`、解析版本、按版本号顺序执行。

### 9.6 Flyway 与 JPA `ddl-auto` 的关系

前面 JPA 模块（14）讲过 `spring.jpa.hibernate.ddl-auto`，它能根据 Entity 自动建表/更新表。那和 Flyway 什么关系？

| 维度 | JPA `ddl-auto` | Flyway |
| --- | --- | --- |
| 谁写 SQL | 框架自动生成 | 开发者手写 |
| 可控性 | 低（自动生成的 SQL 不可控） | 高（所见即所得） |
| 版本控制 | 无 | 有（每次变更有记录） |
| 回滚 | 不支持 | 可通过加反向脚本实现 |
| 适合场景 | 开发期快速验证 Entity | 生产环境的结构变更 |

**实际开发最佳实践：**

- 开发期：`ddl-auto=update` 快速迭代（加字段自动同步），或 `ddl-auto=none` 完全交给 Flyway
- 生产期：`ddl-auto=none`，**全部用 Flyway 管理表结构**，绝不让 JPA 自动改生产表

> ⚠️ 坑：同时开 `ddl-auto=update` 和 Flyway，可能两者打架（JPA 自动加了字段，Flyway 脚本又加一遍，报字段已存在）。生产环境关掉 `ddl-auto`，让 Flyway 独占表结构管理。

### 9.7 回滚：Flyway 的弱项与补救

Flyway 是**前向迁移**（forward-only）工具——它只支持"往前加新脚本"，不自动回滚。这和 Liquibase 不同（Liquibase 每个变更可以配回滚 SQL）。

**实际开发怎么处理回滚？**

1. **写反向脚本**：上线后发现 `V5__add_column` 加错了，写 `V6__drop_column` 回滚，而不是删 `V5`
2. **代码层回滚 + 表结构保留**：很多时候表结构变了但代码回滚后仍能兼容（如加了字段，老代码不用这个字段不影响）
3. **数据库备份**：重大变更前先备份，出问题直接恢复备份（最稳妥）

**为什么不支持自动回滚？** 因为很多 SQL 操作不可逆（如 `DROP TABLE`、`DELETE`），无法自动生成反向操作。前向迁移更安全、更简单，是业界主流共识。

### 9.8 团队协作规范

实际项目用 Flyway，建议建立以下规范：

1. **脚本提交规范**：数据库变更必须通过提交 SQL 脚本，禁止手动用工具改表
2. **版本号分配**：约定版本号规则（如按日期 `V20260903_1`，或按工单号），避免冲突
3. **Code Review**：SQL 脚本也要 review，检查索引、字段类型、约束
4. **CI 集成**：CI 流程里跑一次 Flyway 迁移到测试库，保证脚本可执行
5. **生产发布流程**：生产部署前，先在测试环境完整跑一遍迁移，确认无误
6. **脚本目录组织**：复杂项目可按模块拆子目录（`db/migration/user/`、`db/migration/order/`），用 `spring.flyway.locations` 配置多路径

> 💡 前端类比：这就像前端团队的 Git commit 规范、ESLint 规则、CI 检查——数据库脚本也需要同样的工程化纪律。

---

> 📌 **学习建议**：Flyway 是你从"写能跑的代码"迈向"做工程化项目"的关键一环。作为前端转后端的工程师，你可能习惯了前端那种"状态在前端、数据库只是存储"的思维，但后端项目里，**数据库 schema 本身就是系统状态的一部分**，必须和代码一样做版本控制。建议把脚本命名规则、`baseline-on-migrate`、`clean-disabled` 这三个点吃透，然后在自己的练习项目里实际接入 Flyway，体验"启动即建表、加脚本即升级"的爽快感。这是后端工程化的基本功，也是区分"业余"和"专业"的分水岭。
