# JDBC

JDBC(Java DataBase Connectivity) Java 数据库连接

JDBC 定义了操作所以关系型数据库的规范（接口）

使用 Java 程序访问数据库时，并不是直接通过 TCP 连接去访问数据库，而是通过 JDBC 接口来访问，而 JDBC 接口则通过 JDBC 驱动来实现真正对数据库的访问

使用 JDBC 步骤：

1. 导入 MySQL 或 Oracle 驱动包
2. 注册驱动
3. 获取数据库连接对象 Connection
4. 获取可以执行 SQL 语句的对象 Statement/PreparedStatement
5. 执行 SQL 语句
6. 释放资源

## JDBC 的核心 API

- `DriverManager`：驱动管理对象，管理和注册数据库驱动，获取数据库连接对象
- `Connection`：数据库连接对象，获取执行 SQL 的对象，管理事务
- `Statement`：执行静态SQL对象，用于执行静态SQL语句并返回其生成的结果的对象
- `PreparedStatement`：预编译 SQL 语句对象，用于执行 SQL 语句，是 Statement 的子接口
- `ResultSet`：结果集对象，数据库查询的结果集

### DriverManager

- `Connection getConnection (String url, String user, String password)`：通过连接字符串，用户名，密码来得到数据库的连接对象
- `Connection getConnection (String url, Properties info)`： 通过连接字符串，属性对象来得到连接对象

连接数据库的 URL 地址格式：协议名:子协议://服务器名或 IP 地址:端口号/数据库名?参数=参数值

MySQL的 URL 格式：`jdbc:mysql://localhost:3306/test?useSSL=false&characterEncoding=utf8`

### Connection

- `Statement createStatement()`：创建 SQL 语句对象
- `PreparedStatement prepareStatement(String sql)`：指定预编译的 SQL 语句，SQL 语句中使用占位符 ? 创建一个语句对象
- `oid setAutoCommit(boolean autoCommit)`：如果为 false，表示关闭自动提交，相当于开启事务
- `void rollback()`：回滚事务

### Statement

- `int executeUpdate(String sql)`：执行 DML(INSERT、UPDATE、DELETE)、DDL(CREATE、ALTER、DROP)语句。返回对数据库影响的行数
- `ResultSet executeQuery(String sql)`：执行 DQL(SELECT) 语句。返回查询的结果集

### PreparedStatement

使用 `PreparedStatement` 可以避免 SQL 注入的问题

在 SQL 语句中使用 ? 占位符

- `int executeUpdate()`：执行 DML(INSERT、UPDATE、DELETE)，增删改的操作，返回影响的行数
- `ResultSet executeQuery()`：执行 DQL，查询的操作，返回结果集
- `void setDouble(int parameterIndex, double x)`：将指定参数设置为给定 Java double 值
- `void setFloat(int parameterIndex, float x)`：将指定参数设置为给定 Java REAL 值
- `void setInt(int parameterIndex, int x)`：将指定参数设置为给定 Java int 值
- `void setLong(int parameterIndex, long x)`：将指定参数设置为给定 Java long 值
- `void setObject(int parameterIndex, Object x)`：使用给定对象设置指定参数的值
- `void setString(int parameterIndex, String x)`：将指定参数设置为给定 Java String 值

### ResultSet

- `boolean next()`：游标向下移动 1 行，返回 boolean 类型，如果还有下一条记录，返回 true，否则返回 false
- `数据类型 getXxx()`：通过字段名，参数是 String 类型。返回不同的类型；通过列号，参数是整数，从 1 开始。返回不同的类型

```java
public class JDBCTest {
  public static void main(String[] args) throws Exception {
    useJDBC();
    executeQuery();
    loginSafe();
  }
  // 使用 JDBC
  public static void useJDBC() throws ClassNotFoundException, SQLException {
    // 注册驱动，MySQL 5 以后不需要手动注册
    Class.forName("com.mysql.jdbc.Driver");

    // 获取数据库连接对象
    Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/my_test?useSSL=false", "root", "123456");

    // 获取执行 SQL 语句对象 Statement
    Statement stmt = conn.createStatement();

    // 定义 SQL 语句，执行 SQL
    String sql = "SELECT * FROM teacher";
    ResultSet rs = stmt.executeQuery(sql);

    // 遍历结果集，获取数据
    while (rs.next()) {
      System.out.println(rs.getInt(1) + ". " + rs.getString(2));
    }
  }

  // executeQuery查询数据
  public static void executeQuery() {
    Connection conn = null;
    Statement stmt = null;
    String url = "jdbc:mysql://localhost:3306/my_test?useSSL=false&characterEncoding=utf8";

    try {
      // 创建连接
      conn = DriverManager.getConnection(url, "root", "123456");
      // 通过连接对象得到语句对象
      stmt = conn.createStatement();

      // 执行 SQL 语句
      ResultSet rs = stmt.executeQuery("SELECT id, name FROM teacher");

      while (rs.next()) {
          // 通过序号获取数据，从 1 开始
          int id = rs.getInt(1);
          // 通过字段名获取数据
          String name = rs.getString("name");
          System.out.println(id + ":" + name);
      }
      rs.close();

    } catch (SQLException e) {
      e.printStackTrace();
    } finally {
      // 释放资源
      if (stmt != null) {
        try {
          stmt.close();
          conn.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }
    }
  }

  // executeUpdate 更新数据（增、删、改）
  public static void executeUpdate() {
    Connection conn = null;
    Statement stmt = null;
    String url = "jdbc:mysql://localhost:3306/my_test?useSSL=false&characterEncoding=utf8";

    try {
      // 创建连接
      conn = DriverManager.getConnection(url, "root", "123456");

      // 通过连接对象获取语句对象
      stmt = conn.createStatement();

      // SQL 语句
      String CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS teacher (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(20) NOT NULL, course VARCHAR(20) NOT NULL)";

      // 执行 SQL
      stmt.executeUpdate(CREATE_TABLE_SQL);
      stmt.executeUpdate("INSERT INTO teacher VALUES(null, '李雷', 'match')");

    } catch (SQLException e) {
      e.printStackTrace();
    } finally {
      // 释放资源
      if (stmt != null) {
        try {
          stmt.close();
          conn.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }
    }
  }

  // 使用 PreparedStatement 防止 SQL 注入
  public static void loginSafe(String name, String pwd) {

    Connection conn = null;
    PreparedStatement ps = null;
    ResultSet rs = null;

    try {

        // 连接对象
        conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/my_test?useSSL=false&characterEncoding=utf8", "root", "123456");

        // SQL 语句
        String sql = "SELECT * FROM user WHERE name = ? AND password = ?";

        // 获取预处理 SQL 语句对象
        ps = conn.prepareStatement(sql);

        // 设置参数
        ps.setString(1, name);
        ps.setString(2, pwd);

        // 执行 SQL，注意不用再传入 sql
        rs = ps.executeQuery();

        if (rs.next()) {
            System.out.println("登录成功，欢迎您！" + name);
        } else {
            System.out.println("登录失败，用户名或密码不正确");
        }
    } catch (SQLException e) {
        e.printStackTrace();
    } finally {
      // 释放资源
    }
  }

  // 开启事务
  public static void transaction() {
    Connection conn = null;
    PreparedStatement ps = null;

    try {
      // 获取连接
      conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/my_test?useSSL=false&characterEncoding=utf8", "root", "123456");

      // 开启事务
      conn.setAutoCommit(false);

      // 获取 prepareStatement
      ps = conn.prepareStatement("UPDATE account SET balance = balance - ? WHERE name = ?");

      ps.setInt(1, 500);
      ps.setString(2, "Leo");
      ps.executeUpdate();

      ps = conn.prepareStatement("UPDATE account SET balance = balance + ? WHERE name = ?");
      ps.setInt(1, 500);
      ps.setString(2, "Rex");
      ps.executeUpdate();

      // 提交事务
      conn.commit();
      System.out.println("转载成功！");

    } catch (SQLException e) {
      e.printStackTrace();

      try {
        if (conn != null) {
          // 回滚事务
          conn.rollback();
        }
      } catch (SQLException ex) {
        ex.printStackTrace();
      }

      System.out.println("转账失败！");
    }
  }
}
```

## JDBC 连接池

JDBC连接池有一个标准的接口 `javax.sql.DataSource`，注意这个类位于Java标准库中，但仅仅是接口。

要使用 JDBC 连接池，必须选择一个 JDBC 连接池的实现。常用的 JDBC 连接池有：

+ HikariCP
+ C3P0
+ BoneCP
+ Druid

```java
// 使用 HikariCP 连接池
HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:mysql://localhost:3306/test");
config.setUsername("root");
config.setPassword("password");
config.addDataSourceProperty("connectionTimeout", "1000"); // 连接超时：1秒
config.addDataSourceProperty("idleTimeout", "60000"); // 空闲超时：60秒
config.addDataSourceProperty("maximumPoolSize", "10"); // 最大连接数：10
DataSource ds = new HikariDataSource(config);
```

有了连接池以后，把 `DriverManage.getConnection()` 改为 `ds.getConnection()`
