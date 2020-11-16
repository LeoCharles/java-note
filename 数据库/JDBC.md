# JDBC

JDBC(Java DataBase Connectivity) Java 数据库连接

JDBC 定义了操作所以关系型数据库的规范（接口）

使用 Java 程序访问数据库时，并不是直接通过 TCP 连接去访问数据库，而是通过 JDBC 接口来访问，而 JDBC 接口则通过 JDBC 驱动来实现真正对数据库的访问

使用 JDBC 步骤：

1. 导入 MySQL 或 Oracle 驱动包

2. 注册驱动

3. 获取数据库连接对象 Connection

4. 获取可以执行 SQL 语句的对象 Statement/PreparedStatement

5. 执行 SQL 语句，接收返回结果

6. 处理结果

7. 释放资源

```java
  //1. 导入驱动jar包
  //2. 注册驱动
  Class.forName("com.mysql.jdbc.Driver");
  //3. 获取数据库连接对象
  Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/my_test", "root", "root");
  //4.定义sql语句
  String sql = "update account set balance = 500 where id = 1";
  //5.获取执行sql的对象 Statement
  Statement stmt = conn.createStatement();
  //6.执行sql
  int count = stmt.executeUpdate(sql);
  //7.处理结果
  System.out.println(count);
  //8.释放资源
  stmt.close();
  conn.close();
```

## JDBC 的核心对象

- `DriverManager`：驱动管理对象，管理和注册数据库驱动，获取数据库连接对象

- `Connection`：数据库连接对象，获取执行 SQL 的对象，管理事务

- `Statement`：执行静态SQL对象，用于执行静态SQL语句并返回其生成的结果的对象

- `PreparedStatement`：预编译 SQL 语句对象，用于执行 SQL 语句，是 Statement 的子接口

- `ResultSet`：结果集对象，数据库查询的结果集

### DriverManager 驱动管理对象

- `Connection getConnection (String url, String user, String password)`：通过连接字符串，用户名，密码来得到数据库的连接对象

- `Connection getConnection (String url, Properties info)`： 通过连接字符串，属性对象来得到连接对象

连接数据库的 URL 地址格式：协议名:子协议://服务器名或 IP 地址:端口号/数据库名?参数=参数值

MySQL的 URL 格式：`jdbc:mysql://localhost:3306/test?useSSL=false&characterEncoding=utf8`

### Connection 数据库连接对象

- `Statement createStatement()`：创建 SQL 语句对象

- `PreparedStatement prepareStatement(String sql)`：指定预编译的 SQL 语句，SQL 语句中使用占位符 ? 创建一个语句对象

- `oid setAutoCommit(boolean autoCommit)`：如果为 false，表示关闭自动提交，相当于开启事务

- `void rollback()`：回滚事务

### Statement 执行静态SQL对象

- `int executeUpdate(String sql)`：执行 DML(INSERT、UPDATE、DELETE)、DDL(CREATE、ALTER、DROP)语句。返回对数据库影响的行数

- `ResultSet executeQuery(String sql)`：执行 DQL(SELECT) 语句。返回查询的结果集

### PreparedStatement 预编译 SQL 语句对象

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

### ResultSet 结果集对象

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

数据库连接池就是一个容器，用来存放数据库连接的容器。

当容器被创建，容器中会申请一些连接对象，当用户来访问数据库时，从容器中获取连接对象，用户访问完之后，会将连接对象归还给容器。

`javax.sql.DataSource`： 标准的数据库连接池接口

- `getConnection()`: 获取连接

- `Connection.close()`：归还连接

一般我们不去实现该接口，而是由数据库厂商来实现：C3P0、Druid

### C3P0

使用步骤：

1. 导入 jar 包 c3p0-0.9.5.2.jar 和 mchange-commons-java-0.2.12.jar

2. 定义配置文件
   - 名称：c3p0.properties 或者 c3p0-config.xml
   - 位置：根目录

3. 创建数据库连接池对象 `ComboPooledDataSource()`

4. 获取连接 `getConnection()`

```java
public class C3P0Demo {
  public static void main(String[] args) throws SQLException {

    // 创建数据库连接池对象，使用指定名称的配置
    DataSource ds = new ComboPooledDataSource("my_test");

    // 获取连接对象
    Connection conn =  ds.getConnection();

    System.out.println(conn);
  }
}
```

### Druid

使用步骤：

1. 导入jar包 druid-1.0.9.jar

2. 定义配置文件：任意名称的 properties 文件，可以放在任意位置

3. 加载配置文件

4. 获取数据库连接池对象：通过工厂类来获取 `DruidDataSourceFactor`y

5. 获取连接：`getConnection()`

```java
public class DruidDemo {
  public static void main(String[] args) throws Exception {

    // 加载配置文件
    Properties prop = new Properties();
    InputStream is = DruidDemo.class.getClassLoader().getResourceAsStream("druid.properties");
    prop.load(is);

    // 获取连接池对象
    DataSource ds = DruidDataSourceFactory.createDataSource(prop);

    // 获取连接对象
    Connection conn = ds.getConnection();

    System.out.println(conn);
  }
}
```

定义 Druid 连接池工具类

```java
public class JDBCUtils {
  // 定义成员变量
  private static DataSource ds;

  static {
    try {
      // 加载配置文件
      Properties prop = new Properties();
      prop.load(JDBCUtils.class.getClassLoader().getResourceAsStream("druid.properties"));

      // 获取连接池对象
      ds = DruidDataSourceFactory.createDataSource(prop);
    } catch (Exception e) {
      e.printStackTrace();
    }
  }

    // 获取连接池
    public static DataSource getDataSource() {
      return ds;
    }

    // 获取链接
    public static Connection getConnection() throws SQLException {
      return ds.getConnection();
    }

    // 释放资源
    public static void close(ResultSet rs, Statement stmt, Connection conn) {
      if (rs != null) {
        try {
          rs.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }

      if (stmt != null) {
        try {
          stmt.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }

      if (conn != null) {
        try {
          conn.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }
    }

    public static void close(Statement stmt, Connection conn) {
      close(null, stmt, conn);
    }
}
```

## Spring JDBC

Spring 框架对 JDBC 的简单封装，提供了一个 `JDBCTemplate` 对象简化JDBC的开发

使用步骤

1. 导入 jar 包

2. 创建 `JDBCTemplate` 对象，依赖于数据源 `DataSource`

   - `JdbcTemplate template = new JdbcTemplate(ds)`

3. 调用 JDBCTemplate 里的方法来完成 CRUD 操作

   - `update()`: 执行 DML 语句。用于增、删、改操作
  
   - `queryForMap()`: 将查询结果集封装为 Map 集合，将列名作为 key，将值作为 value，将这条记录封装为一个 Map 集合

   - `queryForList()`: 将查询结果封装为 List 集合，先将每一条记录封装为一个 Map 集合，再将 Map 集合装载到 List 集合

   - `query()`: 将查询结果封装为 JavaBean 对象，一般使用 `BeanPropertyRowMapper` 实现类，完成 JavaBean 自动封装
      - `new BeanPropertyRowMapper<类型>(类型.class)`

   - `queryForObject()`：查询结果，将结果封装为对象。一般用于聚合函数查询

```java
public class JDBCTemplateDemo {
  public static void main(String[] args) {
    update();
    queryForMap();
    queryForList();
    query();
    queryForObject();
  }

  // 创建 JDBCTemplate 对象，需要传入 DataSource
  private static JdbcTemplate template = new JdbcTemplate(JDBCUtils.getDataSource());

  // update，用于增、删、改
  public static void update() {
    String sql = "UPDATE account SET balance = 5000 WHERE id = ?";

    int count = template.update(sql, 1);
    System.out.println(count);
  }

  // queryForMap，将查询结果封装为 Map，查询的结果集长度为 1
  public static void queryForMap() {
    String sql = "SELECT * FROM account WHERE id =?";

    Map<String, Object> map = template.queryForMap(sql, 1);
    System.out.println(map);
  }

    // queryForList，将查询结果封装为 Map 集合，再将 Map 集合装载到 List 集合
    public static void queryForList() {
      String sql  = "SELECT * FROM account";

      List<Map<String, Object>> list = template.queryForList(sql);
      System.out.println(list);
    }

    // query，将查询结果封装到 JavaBean 对象，再装载到 List 集合
    public static void query() {
      String sql  = "SELECT * FROM student";

      // 需要传入 RowMapper 接口
      List<Student> list = template.query(sql, new BeanPropertyRowMapper<Student>(Student.class));

      for (Object student : list) {
          System.out.println(student);
      }
    }

    // queryForObject，将查询结果封装为对象，一般用于聚合函数
    public static void queryForObject() {
      String sql = "Select count(id) from student";

      Long total = template.queryForObject(sql, Long.class);
      System.out.println(total);
    }
}
```
