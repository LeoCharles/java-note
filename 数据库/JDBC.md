# JDBC

> JDBC（Java DataBase Connectivity）是 Java 操作关系型数据库的**标准接口**，定义在 `java.sql` / `javax.sql` 包中。
> 本篇以 **MySQL 8.0 + JDBC 4.0** 为基准，用 `try-with-resources` 自动管理资源、`PreparedStatement` 防 SQL 注入、**HikariCP** 连接池（Spring Boot 默认）。
> 思路：概念 → API → 代码实例 → 易错点 → 实战案例 → Spring Boot 衔接。
> 带 ⭐ 的是开发高频/面试重点。

---

## 一、JDBC 概述

### 1.1 什么是 JDBC

JDBC 是一套**接口规范**（接口 + 抽象类），由 Sun 公司定义。各数据库厂商提供**驱动实现**（Driver），Java 程序通过统一接口操作不同数据库，实现"一套代码，多库通用"。

```
Java 程序  →  JDBC 接口（标准）  →  MySQL 驱动 / Oracle 驱动 / ...  →  数据库
```

> 关键认知：**我们写代码面向 JDBC 接口，不面向具体数据库**。换数据库只需换驱动 jar 包和 URL，业务代码不动——这就是 JDBC 的意义。

### 1.2 核心对象一览 ⭐

| 对象 | 作用 | 对应概念 |
| :--- | :--- | :--- |
| `DriverManager` | 驱动管理，获取连接 | 工厂角色 |
| `Connection` | 数据库连接 | 一次会话 |
| `Statement` / `PreparedStatement` | 执行 SQL | 语句对象 |
| `ResultSet` | 查询结果集 | 游标遍历 |

### 1.3 引入驱动

Maven 引入 MySQL 8 驱动（注意是新版坐标）：

```xml
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>8.3.0</version>
</dependency>
```

> ⚠️ **MySQL 5 与 8 的关键差异**：
> - 驱动类：MySQL 5 是 `com.mysql.jdbc.Driver`；MySQL 8 是 **`com.mysql.cj.jdbc.Driver`**。
> - URL：MySQL 8 需加时区参数 `serverTimezone=Asia/Shanghai`，否则报时区错误。
> - 坐标：旧版 `mysql:mysql-connector-java` 已废弃，新版是 `com.mysql:mysql-connector-j`。

---

## 二、JDBC 六步流程 ⭐

### 2.1 标准 CRUD 模板（try-with-resources）

```java
import java.sql.*;

public class JdbcDemo {
    // MySQL 8 的 URL 与驱动
    private static final String URL =
        "jdbc:mysql://localhost:3306/my_test?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=utf8";
    private static final String USER = "root";
    private static final String PASSWORD = "123456";

    public static void main(String[] args) {
        queryAll();
    }

    // 查询：用 try-with-resources 自动关闭资源
    public static void queryAll() {
        // Connection / PreparedStatement / ResultSet 都实现了 AutoCloseable
        try (Connection conn = DriverManager.getConnection(URL, USER, PASSWORD);
             PreparedStatement ps = conn.prepareStatement("SELECT id, name FROM student WHERE age > ?")) {

            ps.setInt(1, 18);   // 占位符从 1 开始

            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    // 按列号（从 1 开始）或列名取值
                    int id = rs.getInt("id");
                    String name = rs.getString("name");
                    System.out.println(id + " : " + name);
                }
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

    // 增删改：返回影响行数
    public static int insert(String name, int age) {
        String sql = "INSERT INTO student(name, age) VALUES(?, ?)";
        try (Connection conn = DriverManager.getConnection(URL, USER, PASSWORD);
             PreparedStatement ps = conn.prepareStatement(sql)) {

            ps.setString(1, name);
            ps.setInt(2, age);
            return ps.executeUpdate();   // 返回影响行数
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return 0;
    }
}
```

> ⚠️ **为什么用 `PreparedStatement` 而非 `Statement`**：
> 1. **防 SQL 注入**：参数预编译，用户输入 `' OR 1=1 --` 也会被当作普通字符串。
> 2. **性能更好**：SQL 预编译后可缓存执行计划，重复执行更快。
> 3. **可读性好**：参数与 SQL 分离。**生产环境禁用 `Statement` 拼接 SQL**。

### 2.2 为什么不再需要 Class.forName

```java
// MySQL 5 旧写法：手动注册驱动
Class.forName("com.mysql.jdbc.Driver");

// MySQL 8 / JDBC 4.0+：无需手动注册
Connection conn = DriverManager.getConnection(URL, USER, PASSWORD);
```

JDBC 4.0 起支持**自动加载驱动**：驱动 jar 包的 `META-INF/services/java.sql.Driver` 文件声明了驱动类，`DriverManager` 启动时自动发现并注册，无需 `Class.forName`。

---

## 三、核心 API 详解

### 3.1 DriverManager

```java
// 三种获取连接的重载
Connection getConnection(String url, String user, String password)
Connection getConnection(String url, Properties info)
Connection getConnection(String url)   // user/password 写在 url 里
```

URL 格式：`协议:子协议://主机:端口/数据库?参数=值&参数=值`
MySQL 8 典型 URL：
```
jdbc:mysql://localhost:3306/my_test?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=utf8
```

### 3.2 Connection

```java
Statement createStatement();
PreparedStatement prepareStatement(String sql);   // 推荐
void setAutoCommit(boolean autoCommit);  // false 开启事务
void commit();    // 提交
void rollback();  // 回滚
```

### 3.3 PreparedStatement

```java
int executeUpdate();          // 增删改，返回影响行数
ResultSet executeQuery();     // 查询，返回结果集
boolean execute();            // 不确定类型时用，返回是否有结果集

// setXxx(int 参数索引, 值) —— 索引从 1 开始
void setString(int i, String x);
void setInt(int i, int x);
void setObject(int i, Object x);   // 通用，类型自动推断
```

### 3.4 ResultSet

```java
boolean next();   // 游标下移一行，有数据返回 true
// getXxx(列名) 或 getXxx(列号) —— 列号从 1 开始
int getInt(String columnLabel);
String getString(String columnLabel);
```

> ⚠️ **ResultSet 用完必须关闭**，否则连接归还后游标资源泄漏。用 try-with-resources 一并管理最稳妥。

---

## 四、事务处理 ⭐

JDBC 事务绑定在 `Connection` 上：关闭自动提交 → 执行多条 SQL → 全成功 commit / 出错 rollback。

```java
public static void transfer(String from, String to, double amount) {
    String sql = "UPDATE account SET balance = balance + ? WHERE name = ?";
    // try-with-resources 只管关闭，事务需手动 commit/rollback
    try (Connection conn = DriverManager.getConnection(URL, USER, PASSWORD);
         PreparedStatement ps = conn.prepareStatement(sql)) {

        conn.setAutoCommit(false);   // 开启事务（关键！）

        ps.setDouble(1, -amount);
        ps.setString(2, from);
        ps.executeUpdate();

        // 模拟异常
        // if (true) throw new RuntimeException("转账失败");

        ps.setDouble(1, amount);
        ps.setString(2, to);
        ps.executeUpdate();

        conn.commit();   // 全部成功，提交
        System.out.println("转账成功");
    } catch (SQLException e) {
        e.printStackTrace();
        // 注意：这里 conn 已被 try 自动关闭，rollback 需在关闭前调用
        // 正确做法见下方"事务模板"
    }
}
```

> ⚠️ **事务的正确模板**：rollback 必须在连接关闭**之前**调用。标准写法是把事务逻辑放在 try 块内、catch 块内 rollback：

```java
Connection conn = DriverManager.getConnection(URL, USER, PASSWORD);
try {
    conn.setAutoCommit(false);
    // ... 多条 SQL ...
    conn.commit();
} catch (SQLException e) {
    conn.rollback();   // 出错回滚
    throw e;
} finally {
    conn.setAutoCommit(true);  // 恢复默认
    conn.close();
}
```

---

## 五、数据库连接池 ⭐

### 5.1 为什么需要连接池

每次 `DriverManager.getConnection` 都新建 TCP 连接、认证、销毁，**开销巨大**。连接池预先创建一批连接复用，用完归还而非销毁，大幅提升性能。

```
没有连接池：每次请求 → 建连接 → 用 → 销毁（慢）
有连接池  ：启动时建 N 个连接 → 借一个 → 用 → 归还（快）
```

### 5.2 DataSource 接口

`javax.sql.DataSource` 是连接池标准接口。从池中获取连接用 `getConnection()`，**调用 `close()` 不是真关闭，而是归还连接**。

### 5.3 HikariCP（Spring Boot 默认）⭐

HikariCP 是目前性能最高的连接池，Spring Boot 默认内嵌。

**Maven 依赖**：

```xml
<dependency>
    <groupId>com.zaxxer</groupId>
    <artifactId>HikariCP</artifactId>
    <version>5.1.0</version>
</dependency>
```

**配置文件 `hikari.properties`**：

```properties
jdbcUrl=jdbc:mysql://localhost:3306/my_test?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=utf8
username=root
password=123456
driverClassName=com.mysql.cj.jdbc.Driver
maximumPoolSize=10          # 最大连接数
minimumIdle=2               # 最小空闲连接
connectionTimeout=30000     # 获取连接超时（ms）
```

**使用**：

```java
public class HikariUtil {
    private static final HikariDataSource DS;

    static {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://localhost:3306/my_test?useSSL=false&serverTimezone=Asia/Shanghai");
        config.setUsername("root");
        config.setPassword("123456");
        config.setMaximumPoolSize(10);
        DS = new HikariDataSource(config);
    }

    public static Connection getConnection() throws SQLException {
        return DS.getConnection();   // 借连接
    }
}
```

### 5.4 Druid（阿里，带监控）

国内项目常用 Druid，特点是自带 SQL 监控面板。

```xml
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid</artifactId>
    <version>1.2.20</version>
</dependency>
```

```java
public class DruidUtil {
    private static final DataSource DS;
    static {
        Properties prop = new Properties();
        try (InputStream is = DruidUtil.class.getClassLoader()
                .getResourceAsStream("druid.properties")) {
            prop.load(is);
            DS = DruidDataSourceFactory.createDataSource(prop);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
    public static Connection getConnection() throws SQLException {
        return DS.getConnection();
    }
}
```

> ⚠️ **HikariCP vs Druid**：HikariCP 性能极致、代码极简，是 Spring Boot 默认；Druid 监控强、SQL 防火墙，国内企业常用。**新项目选 HikariCP，需要监控选 Druid**。

---

## 六、JDBC 工具类封装

把连接获取、资源释放、事务封装成工具类，避免重复代码：

```java
public final class JdbcUtils {
    private static final DataSource DS = buildDataSource();

    private static DataSource buildDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://localhost:3306/my_test?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=utf8");
        config.setUsername("root");
        config.setPassword("123456");
        config.setMaximumPoolSize(10);
        return new HikariDataSource(config);
    }

    public static Connection getConnection() throws SQLException {
        return DS.getConnection();
    }

    /** 通用更新（增删改） */
    public static int update(String sql, Object... params) {
        try (Connection conn = DS.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            for (int i = 0; i < params.length; i++) {
                ps.setObject(i + 1, params[i]);   // 通用设参
            }
            return ps.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    /** 通用查询：把 ResultSet 映射成对象列表（需传映射函数） */
    public static <T> List<T> query(String sql, RowMapper<T> mapper, Object... params) {
        List<T> list = new ArrayList<>();
        try (Connection conn = DS.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            for (int i = 0; i < params.length; i++) {
                ps.setObject(i + 1, params[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    list.add(mapper.map(rs));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
        return list;
    }

    @FunctionalInterface
    public interface RowMapper<T> {
        T map(ResultSet rs) throws SQLException;
    }
}
```

**使用**：

```java
// 增
JdbcUtils.update("INSERT INTO student(name, age) VALUES(?, ?)", "赵六", 20);

// 查
List<Student> students = JdbcUtils.query(
    "SELECT id, name, age FROM student WHERE age > ?",
    rs -> new Student(rs.getInt("id"), rs.getString("name"), rs.getInt("age")),
    18
);
```

> 这个 `RowMapper` 思路就是 **MyBatis / Spring JdbcTemplate 的雏形**——把"取结果集映射成对象"抽象成接口，业务只关心 SQL 和映射。

---

## 七、Spring JdbcTemplate（过渡）

Spring 对 JDBC 的薄封装，省去资源管理和 ResultSet 遍历样板代码，是手写 JDBC → MyBatis 的过渡桥梁。

```java
JdbcTemplate template = new JdbcTemplate(dataSource);

// 增删改
int rows = template.update("UPDATE student SET age=? WHERE id=?", 20, 1);

// 查询映射成对象
List<Student> list = template.query(
    "SELECT id, name, age FROM student",
    (rs, rowNum) -> new Student(rs.getInt("id"), rs.getString("name"), rs.getInt("age"))
);

// 聚合查询
Integer total = template.queryForObject("SELECT COUNT(*) FROM student", Integer.class);
```

> JdbcTemplate 的 `RowMapper` 与上面工具类的 `RowMapper` 思路一致。Spring Boot 中 `spring-boot-starter-jdbc` 自动配置 JdbcTemplate Bean，直接注入即可用。

---

## ⚠️ 重点

1. **用 `PreparedStatement` 不用 `Statement`**：防 SQL 注入 + 性能更好。
2. **用 `try-with-resources`**：`Connection`/`PreparedStatement`/`ResultSet` 都实现了 `AutoCloseable`，自动关闭，告别手动 close 漏关。
3. **MySQL 8 驱动类是 `com.mysql.cj.jdbc.Driver`**，URL 必须加 `serverTimezone`。
4. **JDBC 4.0+ 无需 `Class.forName`**，自动加载驱动。
5. **事务绑定在 `Connection` 上**：`setAutoCommit(false)` 开启，rollback 必须在连接关闭前调用。
6. **连接池 `close()` 是归还不是销毁**：从池借的连接，close 后回到池中复用。
7. **HikariCP 是 Spring Boot 默认连接池**，性能最优；Druid 监控强，国内常用。
8. **占位符索引从 1 开始**，不是 0。

---

## 💻 实战案例

用 JDBC + HikariCP 完成学生表的完整 CRUD（配合 [MySQL学习文档.md](MySQL学习文档.md) 的 school 库）：

```java
public class StudentDao {
    private final JdbcTemplate template;

    public StudentDao(DataSource ds) {
        this.template = new JdbcTemplate(ds);
    }

    // 增
    public int insert(Student s) {
        return template.update("INSERT INTO student(name, age, sex) VALUES(?, ?, ?)",
                s.getName(), s.getAge(), s.getSex());
    }

    // 删
    public int deleteById(int id) {
        return template.update("DELETE FROM student WHERE id = ?", id);
    }

    // 改
    public int update(Student s) {
        return template.update("UPDATE student SET name=?, age=?, sex=? WHERE id=?",
                s.getName(), s.getAge(), s.getSex(), s.getId());
    }

    // 查全部
    public List<Student> findAll() {
        return template.query("SELECT id, name, age, sex FROM student",
                (rs, n) -> new Student(rs.getInt("id"), rs.getString("name"),
                        rs.getInt("age"), rs.getString("sex")));
    }

    // 查单个
    public Student findById(int id) {
        return template.queryForObject(
                "SELECT id, name, age, sex FROM student WHERE id = ?",
                (rs, n) -> new Student(rs.getInt("id"), rs.getString("name"),
                        rs.getInt("age"), rs.getString("sex")),
                id);
    }

    // 分页查询（对应 MySQL 的 LIMIT）
    public List<Student> findPage(int page, int size) {
        int offset = (page - 1) * size;
        return template.query("SELECT id, name, age, sex FROM student LIMIT ?, ?",
                (rs, n) -> new Student(rs.getInt("id"), rs.getString("name"),
                        rs.getInt("age"), rs.getString("sex")),
                offset, size);
    }

    // 事务：批量转学分
    public void transferCredit(int fromId, int toId, double credit) {
        template.execute((ConnectionCallback<Void>) conn -> {
            try {
                conn.setAutoCommit(false);
                try (PreparedStatement ps = conn.prepareStatement(
                        "UPDATE score SET mark = mark + ? WHERE student_id = ?")) {
                    ps.setDouble(1, -credit);
                    ps.setInt(2, fromId);
                    ps.executeUpdate();
                    ps.setDouble(1, credit);
                    ps.setInt(2, toId);
                    ps.executeUpdate();
                }
                conn.commit();
            } catch (SQLException e) {
                conn.rollback();
                throw e;
            }
            return null;
        });
    }
}
```

---

## 🚀 新版本补充

- **JDBC 4.0+**：自动加载驱动，无需 `Class.forName`。
- **try-with-resources**（Java 7+）：`Connection`/`Statement`/`ResultSet` 均实现 `AutoCloseable`，自动关闭。
- **HikariCP 5.x**：目前性能最强的连接池，Spring Boot 2.x+ 默认内嵌。
- **JDBC 4.3**（Java 9+）：支持 `ShardingKey` 分片键，配合分库分表中间件使用。

---

## 📌 在 Spring Boot 中

| 本篇概念 | Spring Boot 中的对应 |
| :--- | :--- |
| `DriverManager.getConnection` | **自动配置 DataSource**，`spring.datasource.*` 配置 |
| HikariCP 手动配置 | **默认内嵌 HikariCP**，`spring.datasource.hikari.*` 调参 |
| 手写工具类 CRUD | `JdbcTemplate` 自动注入，或直接用 MyBatis-Plus |
| `setAutoCommit/commit/rollback` | **`@Transactional` 注解**，声明式事务 |
| `PreparedStatement` + `?` 占位符 | MyBatis 的 `#{}` 占位符，底层仍是 PreparedStatement |
| `RowMapper` 手动映射 | MyBatis-Plus 自动映射 / JPA 实体自动映射 |
| 连接池配置 | `application.yml` 中 `spring.datasource.*` 一行搞定 |

> 一句话：**JDBC 是所有 Java 持久层框架的基石。** MyBatis、JPA、Spring Data 全部建立在 JDBC 之上——理解了 Connection、PreparedStatement、事务、连接池，用这些框架时才不会被"魔法"迷惑，出了问题（连接泄漏、事务不生效、SQL 注入）才知道往哪查。

---

## 本章小结

本篇从 JDBC 接口规范出发，掌握了六步流程、PreparedStatement 防 SQL 注入、try-with-resources 资源管理、事务处理、HikariCP 连接池，以及工具类封装。核心是理解"Java 程序如何通过标准接口操作数据库"，这是后续 MyBatis、JPA、Spring Data 的共同底层。配合 [MySQL学习文档.md](MySQL学习文档.md) 的 SQL 知识，你已具备手写 JDBC 持久层的能力——下一篇进入 Java Web 的 Servlet 世界。
