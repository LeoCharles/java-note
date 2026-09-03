# Apache DBUtils

前面 JDBC 篇和连接池篇你写了大量样板代码：`getConnection` → `prepareStatement` → `setXxx` → `executeQuery` → `while(rs.next())` 遍历 `rs.getXxx` 填对象 → 关闭一堆资源。每查一次写一遍，枯燥且易错。能不能简化？**Apache DBUtils** 就是这个轻量工具——`QueryRunner` 一行 CRUD，`ResultSetHandler` 自动映射。本篇讲清 DBUtils 的用法，以及它如何为 MyBatis 做铺垫。这是 Spring Boot `JdbcTemplate` 和 MyBatis `BaseMapper` 的前身。

> 💡 本篇建议用 DBUtils 重写 JDBC 篇的查询代码，对比行数——你会看到从 20 行样板缩到 3 行。亲手感受"工具简化样板"的价值，这正是 JdbcTemplate/MyBatis 的进化方向。

---

## 一、为什么需要 DBUtils

### 1.1 JDBC 的样板代码

```java
// 裸 JDBC：查一个用户要写这么多
public User findById(int id) throws SQLException {
    Connection conn = null;
    PreparedStatement ps = null;
    ResultSet rs = null;
    User user = null;
    try {
        conn = HikariUtil.getConnection();
        ps = conn.prepareStatement("SELECT * FROM user WHERE id=?");
        ps.setInt(1, id);
        rs = ps.executeQuery();
        if (rs.next()) {
            user = new User();
            user.setId(rs.getInt("id"));
            user.setName(rs.getString("name"));
            user.setAge(rs.getInt("age"));
        }
    } finally {
        // 关三个资源，顺序还不能错
        if (rs != null) rs.close();
        if (ps != null) ps.close();
        if (conn != null) conn.close();
    }
    return user;
}
```

**痛点**：
- **样板重复**：每次查询都写"借连接→预编译→设参→执行→遍历→关资源"
- **资源管理繁琐**：rs/ps/conn 三层关闭，顺序错会出问题
- **结果集映射啰嗦**：手动 `rs.getXxx` 逐字段填对象，字段多时冗长
- **异常处理**：`SQLException` 是受检异常，到处 try-catch

### 1.2 DBUtils 的解法

**Apache Commons DbUtils** 把样板代码封装成几行：

```java
// DBUtils：查一个用户，3 行
QueryRunner qr = new QueryRunner(dataSource);
User user = qr.query("SELECT * FROM user WHERE id=?",
        new BeanHandler<>(User.class),   // 自动映射成 User 对象
        id);                              // 参数
```

| 对比项 | 裸 JDBC | DBUtils |
| :--- | :--- | :--- |
| 资源管理 | 手动关 rs/ps/conn | 自动关 |
| 结果映射 | 手动 rs.getXxx 填对象 | `BeanHandler` 自动映射 |
| 代码量 | 20+ 行 | 3 行 |
| 异常 | 受检 SQLException | 仍抛但样板少 |

> 💡 **DBUtils 的核心价值**：消除样板。资源自动关、结果自动映射、参数自动设——把"重复的体力活"封装掉，业务代码只写 SQL 和参数。**这是所有持久层工具的共同方向**（JdbcTemplate、MyBatis、JPA 都在简化样板）。

---

## 二、QueryRunner ⭐

### 2.1 核心 API

`QueryRunner` 是 DBUtils 的核心类，提供 CRUD 方法：

| 方法 | 作用 | 返回 |
| :--- | :--- | :--- |
| `query(sql, handler, params)` | 查询 | 由 handler 决定 |
| `update(sql, params)` | 增删改 | 受影响行数 |
| `batch(sql, params[][] )` | 批处理 | 每次影响行数数组 |
| `insert(sql, handler, params)` | 插入并取主键 | 主键 |

### 2.2 构造方式

```java
// 方式一：传 DataSource（推荐，自动管连接）
QueryRunner qr = new QueryRunner(dataSource);
// 每次操作自动从池借连接、用完还

// 方式二：不传 DataSource，手动传 Connection（用于事务）
QueryRunner qr = new QueryRunner();
// 手动 conn = dataSource.getConnection()，qr.update(conn, sql, params)
// 一个 conn 跑多个操作 = 事务
```

> 💡 **两种构造对应两种用法**：传 DataSource 的 `QueryRunner` 每次操作独立（自动借还连接，无事务）；不传的手动传 Connection（多个操作共用一个连接，构成事务）。**事务要手动管连接**——这是 JDBC 篇讲的事务原理。

---

## 三、ResultSetHandler 结果映射 ⭐

`ResultSetHandler` 接口负责把 `ResultSet` 转成你想要的对象。DBUtils 提供几个常用实现：

### 3.1 BeanHandler（单对象）

```java
// 查一个用户，自动映射成 User 对象
User user = qr.query("SELECT * FROM user WHERE id=?",
        new BeanHandler<>(User.class),   // 单个对象
        1);
```

> 💡 **BeanHandler 的原理**：它用反射，按列名（`id`/`name`/`age`）找到 User 对应的 setter（`setId`/`setName`/`setAge`），调 setter 填值。**要求列名和属性名一致**（或用别名匹配）。

### 3.2 BeanListHandler（对象列表）

```java
// 查多个用户，自动映射成 List<User>
List<User> users = qr.query("SELECT * FROM user",
        new BeanListHandler<>(User.class));   // 列表
```

### 3.3 ScalarHandler（单值）

```java
// 查总数（COUNT 返回单值）
Long count = qr.query("SELECT COUNT(*) FROM user",
        new ScalarHandler<Long>());   // 单值

// 取自增主键
Long id = qr.insert("INSERT INTO user(name,age) VALUES(?,?)",
        new ScalarHandler<Long>(),     // 取生成的主键
        "张三", 20);
```

### 3.4 MapHandler / MapListHandler

```java
// 查成 Map（不建实体类时用）
Map<String, Object> map = qr.query("SELECT * FROM user WHERE id=?",
        new MapHandler(), 1);
// {id=1, name=张三, age=20}

List<Map<String, Object>> list = qr.query("SELECT * FROM user",
        new MapListHandler());   // List<Map>
```

### 3.5 速记表

| Handler | 返回类型 | 用途 |
| :--- | :--- | :--- |
| `BeanHandler` | 单对象 | 查一条 |
| `BeanListHandler` | `List<对象>` | 查多条 |
| `ScalarHandler` | 单值 | COUNT/主键 |
| `MapHandler` | `Map` | 查一条（无实体类） |
| `MapListHandler` | `List<Map>` | 查多条（无实体类） |
| `ColumnListHandler` | `List<某列>` | 只取一列 |

> 💡 **BeanHandler 要求列名 = 属性名**：SQL 返回的列名要和实体类属性名一致，反射才能映射。不一致用别名：`SELECT username AS name FROM user`（`username` 列映射到 `name` 属性）。这是 MyBatis `resultMap` 的前身——MyBatis 用 `resultMap` 解决列名和属性名不一致，DBUtils 用别名。

---

## 四、CRUD 完整示例

### 4.1 查询

```java
// 查单个
User user = qr.query("SELECT * FROM user WHERE id=?",
        new BeanHandler<>(User.class), id);

// 查列表
List<User> users = qr.query("SELECT * FROM user WHERE age>?",
        new BeanListHandler<>(User.class), 18);

// 查总数
Long count = qr.query("SELECT COUNT(*) FROM user",
        new ScalarHandler<Long>());
```

### 4.2 增删改

```java
// 新增
int rows = qr.update("INSERT INTO user(name,age) VALUES(?,?)",
        "张三", 20);

// 新增并取主键
Long id = qr.insert("INSERT INTO user(name,age) VALUES(?,?)",
        new ScalarHandler<Long>(), "张三", 20);

// 修改
int rows = qr.update("UPDATE user SET name=? WHERE id=?", "李四", 1);

// 删除
int rows = qr.update("DELETE FROM user WHERE id=?", 1);
```

### 4.3 事务

```java
// 事务：手动管连接，多个操作共用一个 Connection
public void transfer(int from, int to, double amount) throws SQLException {
    Connection conn = null;
    try {
        conn = dataSource.getConnection();
        conn.setAutoCommit(false);   // 开启事务

        QueryRunner qr = new QueryRunner();   // 不传 DataSource
        qr.update(conn, "UPDATE account SET balance=balance-? WHERE id=?", amount, from);
        qr.update(conn, "UPDATE account SET balance=balance+? WHERE id=?", amount, to);

        conn.commit();   // 提交
    } catch (SQLException e) {
        if (conn != null) conn.rollback();   // 回滚
        throw e;
    } finally {
        if (conn != null) {
            conn.setAutoCommit(true);   // 恢复
            conn.close();   // 还回池
        }
    }
}
```

> 💡 **事务的连接管理没被 DBUtils 简化**：事务要手动借连接、关自动提交、提交/回滚、还连接。**DBUtils 简化的是 SQL 执行，不是事务管理**——事务还是要按 JDBC 篇讲的手动管。Spring 的 `@Transactional` 才把事务也封装了。

---

## 五、DBUtils 的局限与 MyBatis 的进化

### 5.1 DBUtils 的局限

| 局限 | 说明 |
| :--- | :--- |
| 仍写 SQL | 每个查询手写 SQL，SQL 散在 Java 代码里 |
| 无动态 SQL | 条件查询要手动拼 SQL 字符串（`if name!=null` 拼 `WHERE`） |
| 无缓存 | 每次都查 DB |
| 映射简单 | 只支持列名=属性名，复杂映射（多表关联）要手写 |
| 无 ORM | 不是对象关系映射，只是 JDBC 简化 |

### 5.2 MyBatis 的进化

**MyBatis** 在 DBUtils 基础上进一步：
- **SQL 集中管理**：SQL 写在 XML/注解，不散在 Java 里
- **动态 SQL**：`<if>`/`<foreach>` 标签，条件查询不用拼字符串
- **复杂映射**：`resultMap` 支持多表关联、嵌套
- **接口代理**：定义接口，MyBatis 自动生成实现（`BaseMapper` 思路）

```java
// MyBatis：定义接口，不用写实现
public interface UserMapper {
    @Select("SELECT * FROM user WHERE id=#{id}")
    User findById(int id);

    @Select("SELECT * FROM user WHERE age>#{age}")
    List<User> findByAge(int age);
}
```

> 💡 **DBUtils → MyBatis → MyBatis-Plus 的进化**：
> - **DBUtils**：简化 JDBC 样板，但仍写 SQL、无动态 SQL
> - **MyBatis**：SQL 集中、动态 SQL、复杂映射、接口代理
> - **MyBatis-Plus**：通用 CRUD（`BaseMapper` 提供 `selectById` 等，连 SQL 都不写）
>
> 每一步都在"把更多体力活交给框架"。理解了 DBUtils 的简化方向，MyBatis/MyBatis-Plus 的设计就不神秘。

---

## ⚠️ 重点

1. **DBUtils 消除 JDBC 样板**：资源自动关、结果自动映射、参数自动设。
2. **`QueryRunner` 是核心**：`query`/`update`/`insert`/`batch` 四个方法。
3. **`ResultSetHandler` 决定返回类型**：`BeanHandler` 单对象、`BeanListHandler` 列表、`ScalarHandler` 单值。
4. **`BeanHandler` 要求列名=属性名**：反射按列名找 setter，不一致用别名。
5. **传 DataSource 自动管连接**：每次操作独立，无事务。
6. **不传 DataSource 手动管连接**：多个操作共用 Connection 构成事务。
7. **事务没被简化**：仍要手动 setAutoCommit/commit/rollback。
8. **DBUtils 是 MyBatis 的前身**：简化样板的方向一脉相承。

---

## 💻 实战案例：DBUtils 版 UserDAO

需求：用 DBUtils 重写 JDBC 篇的 UserDAO，对比代码量。

```java
public class UserDao {
    private final QueryRunner qr = new QueryRunner(HikariUtil.getDataSource());

    // 查单个：3 行（JDBC 版 20+ 行）
    public User findById(int id) throws SQLException {
        return qr.query("SELECT * FROM user WHERE id=?",
                new BeanHandler<>(User.class), id);
    }

    // 查列表
    public List<User> findAll() throws SQLException {
        return qr.query("SELECT * FROM user",
                new BeanListHandler<>(User.class));
    }

    // 条件查询
    public List<User> findByAge(int minAge) throws SQLException {
        return qr.query("SELECT * FROM user WHERE age>?",
                new BeanListHandler<>(User.class), minAge);
    }

    // 查总数
    public long count() throws SQLException {
        return qr.query("SELECT COUNT(*) FROM user",
                new ScalarHandler<Long>());
    }

    // 新增并取主键
    public long add(User u) throws SQLException {
        return qr.insert("INSERT INTO user(name,age) VALUES(?,?)",
                new ScalarHandler<Long>(), u.getName(), u.getAge());
    }

    // 修改
    public int update(User u) throws SQLException {
        return qr.update("UPDATE user SET name=?,age=? WHERE id=?",
                u.getName(), u.getAge(), u.getId());
    }

    // 删除
    public int delete(int id) throws SQLException {
        return qr.update("DELETE FROM user WHERE id=?", id);
    }
}
```

> 💡 **对比 JDBC 版**：每个方法从 20+ 行缩到 3 行，样板代码消失。**这就是工具的价值——把重复体力活封装掉**。Spring Boot 的 `JdbcTemplate` 和 MyBatis 都是这个方向的进一步。做完这个案例，你会感受到"手动写 SQL、手动映射"仍繁琐——这正是 MyBatis 要解决的。

---

## 🚀 新版本补充

- **DBUtils 1.7**：稳定版本，功能足够用。
- **现代替代**：实际项目多用 MyBatis/MyBatis-Plus 或 Spring Data JPA，DBUtils 在新项目已少见——但它是最轻量的 JDBC 简化工具，学习它理解"简化样板"的思路。
- **虚拟线程（JDK 21）**：可能改变 JDBC 工具的设计，但 DBUtils 这种轻量封装不会消失。

---

## 📌 在 Spring Boot 中

> 本篇讲的 `QueryRunner` + `ResultSetHandler` 简化 JDBC 样板，在 Spring Boot 中由 `JdbcTemplate`（轻量）和 MyBatis/MyBatis-Plus（重量）接管。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 DBUtils 原理排查"。实际开发你几乎不用 DBUtils——Spring Boot 的 `JdbcTemplate` 或 MyBatis 更主流，但理解了本篇，JdbcTemplate、MyBatis 的设计对你就是透明的。

### 1. JdbcTemplate：从"QueryRunner"到"JdbcTemplate"

**原生**：本篇用 `QueryRunner.query(sql, BeanHandler, params)`。
**Spring Boot**：`JdbcTemplate`，API 类似但 Spring 风格。

```java
@Service
public class UserDao {
    private final JdbcTemplate jdbc;

    public UserDao(JdbcTemplate jdbc) {   // Spring 自动注入
        this.jdbc = jdbc;
    }

    // 查单个：BeanPropertyRowMapper 自动映射（对应 BeanHandler）
    public User findById(int id) {
        return jdbc.queryForObject("SELECT * FROM user WHERE id=?",
                new BeanPropertyRowMapper<>(User.class), id);
    }

    // 查列表
    public List<User> findAll() {
        return jdbc.query("SELECT * FROM user",
                new BeanPropertyRowMapper<>(User.class));
    }

    // 查总数
    public long count() {
        return jdbc.queryForObject("SELECT COUNT(*) FROM user", Long.class);
    }

    // 增删改
    public int add(User u) {
        return jdbc.update("INSERT INTO user(name,age) VALUES(?,?)",
                u.getName(), u.getAge());
    }
}
```

> 💡 **原理对应**：`JdbcTemplate` 就是本篇 `QueryRunner` 的 Spring 版——`query`/`queryForObject`/`update` 对应 `QueryRunner` 的方法，`BeanPropertyRowMapper` 对应 `BeanHandler`（反射映射）。**本篇的 DBUtils，Spring 用 `JdbcTemplate` 重新实现，且自动注入 DataSource、自动管事务**。

> 💡 **原理排查**：`JdbcTemplate` 查不到（`EmptyResultDataAccessException`）？SQL 没结果但用了 `queryForObject`（期望单条）。映射失败？检查列名和属性名（`BeanPropertyRowMapper` 要求一致，和本篇 `BeanHandler` 同理）。回到 DBUtils 原理：反射映射靠列名=属性名。

### 2. 自动配置：从"手动 QueryRunner"到"自动注入 JdbcTemplate"

**原生**：本篇手动 `new QueryRunner(dataSource)`。
**Spring Boot**：自动配置 `JdbcTemplate`，注入即用。

```yaml
spring:
  datasource:   # 配 DataSource（17 篇讲过，自动建 HikariCP）
    url: jdbc:mysql://localhost:3306/test
    username: root
    password: 123456
```

```java
@Service
public class UserDao {
    @Autowired
    private JdbcTemplate jdbcTemplate;   // Spring 自动建好（依赖 DataSource）
}
```

> 💡 **原理对应**：Spring Boot 的 `JdbcTemplateAutoConfiguration` 检测到有 DataSource，自动建 `JdbcTemplate` Bean。**本篇手动 `new QueryRunner(dataSource)`，Spring Boot 自动建 `JdbcTemplate` 注入**，DataSource 也自动配（17 篇讲过）。

### 3. 事务：从"手动管连接"到"@Transactional"

**原生**：本篇第四节手动 `setAutoCommit(false)` + `commit`/`rollback`。
**Spring Boot**：`@Transactional` 注解。

```java
@Service
public class TransferService {
    @Autowired
    private JdbcTemplate jdbc;

    @Transactional   // Spring 自动管事务（借连接、关自动提交、提交/回滚）
    public void transfer(int from, int to, double amount) {
        jdbc.update("UPDATE account SET balance=balance-? WHERE id=?", amount, from);
        jdbc.update("UPDATE account SET balance=balance+? WHERE id=?", amount, to);
        // 两个操作同一事务，异常自动回滚
    }
}
```

> 💡 **原理对应**：`@Transactional` 底层就是本篇第四节的"手动管连接 + setAutoCommit + commit/rollback"——Spring 用 AOP 拦截方法，自动从 DataSource 借连接、关自动提交、方法正常 commit/异常 rollback。**本篇没简化的事务管理，Spring 用 `@Transactional` 彻底封装**。理解了本篇的事务原理，`@Transactional` 对你就是透明的。

> 💡 **原理排查**：`@Transactional` 不生效？检查方法是否 public、是否同类调用（AOP 代理失效）、异常是否被 catch 吞（Spring 不知道该回滚）。回到事务原理：事务靠代理拦截 + 异常触发回滚。

### 4. MyBatis：从"DBUtils 写 SQL"到"接口 + 注解/XML"

**原生**：本篇每个方法手写 SQL 在 Java 代码里。
**MyBatis**：定义接口，SQL 写注解或 XML，MyBatis 生成实现。

```java
// MyBatis：接口即 DAO，不用写实现
@Mapper
public interface UserMapper {
    @Select("SELECT * FROM user WHERE id=#{id}")
    User findById(int id);   // MyBatis 自动实现，返回 User

    @Select("SELECT * FROM user WHERE age>#{minAge}")
    List<User> findByAge(int minAge);

    @Insert("INSERT INTO user(name,age) VALUES(#{name},#{age})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int add(User user);   // 参数是对象，#{name} 取属性
}
```

```java
@Service
public class UserService {
    @Autowired
    private UserMapper userMapper;   // 注入接口，MyBatis 生成代理实现

    public User get(int id) {
        return userMapper.findById(id);   // 像调普通方法
    }
}
```

> 💡 **原理对应**：MyBatis 的 `@Mapper` 接口对应本篇的 DAO 类——但**你只定义接口和 SQL，MyBatis 用动态代理生成实现**（自动执行 SQL + 映射结果）。**本篇手写的 `QueryRunner.query`，MyBatis 用接口代理自动化**，SQL 还是你写（集中管理）。`#{id}` 对应本篇的 `?` 参数，但 MyBatis 用命名参数更清晰。

> 💡 **原理排查**：MyBatis 报 "Invalid bound statement"？SQL 没找到——检查 `@Select` 注解或 XML 映射文件路径、`mybatis.mapper-locations` 配置。映射失败？检查 `resultType`/`resultMap`、列名和属性名。回到 DBUtils 原理：映射靠列名=属性名（MyBatis 用 resultMap 解决不一致）。

### 5. MyBatis-Plus：从"写 SQL"到"通用 CRUD"

**原生**：本篇每个 CRUD 都手写 SQL。
**MyBatis-Plus**：继承 `BaseMapper`，通用 CRUD 连 SQL 都不写。

```java
// MyBatis-Plus：继承 BaseMapper，自带 CRUD
public interface UserMapper extends BaseMapper<User> {
    // 不用写任何方法，BaseMapper 提供：
    // insert / deleteById / updateById / selectById / selectList ...
}

// 使用
@Service
public class UserService {
    @Autowired
    private UserMapper userMapper;

    public User get(int id) {
        return userMapper.selectById(id);   // 不用写 SQL
    }
    public List<User> list() {
        return userMapper.selectList(null);   // 查全部
    }
}
```

> 💡 **原理对应**：MyBatis-Plus 的 `BaseMapper` 是本篇 DAO 的极致简化——**连 SQL 都不写，框架根据实体类自动生成**。这是"简化样板"方向的终点：DBUtils 简化资源管理 → JdbcTemplate 简化映射 → MyBatis 集中 SQL → MyBatis-Plus 不写 SQL。理解了本篇的进化方向，MyBatis-Plus 的 `BaseMapper` 就是它的自然终点。

> 💡 **选型**：轻量简单用 `JdbcTemplate`（对应 DBUtils）；SQL 复杂、要灵活用 MyBatis；通用 CRUD 为主用 MyBatis-Plus。**DBUtils 在 Spring Boot 新项目已少见**，但它的"简化样板"思路活在 JdbcTemplate/MyBatis 里。

---

> 一句话：**DBUtils 是 JDBC 样板代码的轻量简化工具**。Spring Boot 里你几乎不用 DBUtils——`JdbcTemplate`（对应 `QueryRunner`）、MyBatis（接口+SQL 集中）、MyBatis-Plus（`BaseMapper` 通用 CRUD）是它的进化。但"简化资源管理、自动映射结果、集中管理 SQL"的思路一脉相承。理解了本篇，JdbcTemplate、MyBatis、`@Transactional` 对你就是透明的。**出映射失败、事务不生效、SQL 找不到问题时，你仍要回到本篇原理排查**：列名=属性名吗、事务连接管对了吗、SQL 在哪管理。

## 本章小结

本篇讲清了 Apache DBUtils：它用 `QueryRunner`（`query`/`update`/`insert`）+ `ResultSetHandler`（`BeanHandler`/`BeanListHandler`/`ScalarHandler`）简化 JDBC 样板——资源自动关、结果自动映射、参数自动设。重点掌握 `QueryRunner` 两种构造（传 DataSource 自动管连接 vs 不传手动管事务）、`BeanHandler` 要求列名=属性名、事务仍需手动管理、DBUtils 是 MyBatis 的前身。核心认知：**DBUtils → JdbcTemplate → MyBatis → MyBatis-Plus 是"简化样板"的进化链，Spring Boot 用 JdbcTemplate/MyBatis 接管**。至此阶段七完成，数据库与持久层（MySQL/JDBC/连接池/DBUtils）你已掌握。下一篇 [21-综合案例：学生管理系统](21-综合案例：学生管理系统.md) 用原生技术栈完成完整项目，把前七个阶段全部串起来。
