# JDBC

JDBC(Java DataBase Connectivity) 是 Java 程序访问数据库的标准接口。

使用 Java 程序访问数据库时，并不是直接通过 TCP 连接去访问数据库，而是通过 JDBC 接口来访问，而 JDBC 接口则通过 JDBC 驱动来实现真正对数据库的访问。

## JDBC 连接

Connection 代表一个 JDBC 连接，它相当于 Java 程序到数据库的连接。

打开一个 Connection 时，需要准备URL、用户名和口令，才能成功连接到数据库。

URL 是由数据库厂商指定的格式，例如，MySQL的 URL 是：

`jdbc:mysql://<hostname>:<port>/<db>?key1=value1&key2=value2`

假设数据库运行在本机 localhost，端口使用标准的 3306，数据库名称是 test ，那么 URL 如下：

`jdbc:mysql://localhost:3306/test?useSSL=false&characterEncoding=utf8`

使用 Java 代码连接数据库

```java
// JDBC连接的 URL, 不同数据库有不同的格式
String JDBC_URL = "jdbc:mysql://localhost:3306/test";
String JDBC_USER = "root";
String JDBC_PASSWORD = "123456";

// 获取连接
Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD);
// TODO: 访问数据库

// 关闭连接:
conn.close();
```

因为 JDBC 连接是一种昂贵的资源，所以使用后要及时释放。

使用 `try (resource)` 来自动释放 JDBC 连接：

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  // TODO
}
```

## JDBC 查询

查询数据库分以下几步：

1. 通过 `Connection` 提供的 `createStatement()` 方法创建一个 `Statement` 对象，用于执行一个查询；

2. 执行 `Statement` 对象提供的 `executeQuery("SELECT * FROM students")` 并传入 SQL 语句，执行查询并获得返回的结果集，使用 `ResultSet` 来引用这个结果集；

3. 反复调用 `ResultSet` 的 `next()` 方法并读取每一行结果。

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  try (Statement stmt = conn.createStatement()) {
    try (ResultSet rs = stmt.executeQuery("SELECT id, name, gender FROM students WHERE gender=1")) {
      while (rs.next()) {
        int id = rs.getInt(1); // 索引从1开始
        String name = rs.getString(2);
        String gender = rs.getString(3);
      }
    }
  }
}
```

必须根据 SELECT 的列的对应位置来调用 `getInt(1)`，`getString(2)` 这些方法，否则对应位置的数据类型不对，将报错。

使用 `Statement` 拼字符串非常容易引发 SQL 注入的问题，使用 `PreparedStatement` 可以避免 SQL 注入的问题

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  try (PreparedStatement ps = conn.prepareStatement("SELECT id, name, gender FROM students WHERE gender=?")) {

    ps.setObject(1, "female"); // 注意：索引从1开始

    try (ResultSet rs = ps.executeQuery()) {
      while (rs.next()) {
        int id = rs.getInt("id");
        String name = rs.getString("name");
        String gender = rs.getString("gender");
      }
    }
  }
}
```

## JDBC 更新

### 插入数据

插入操作是 `INSERT`，即插入一条新记录。通过JDBC进行插入数据使用 `executeUpdate()`

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  try (PreparedStatement ps = conn.prepareStatement("INSERT INTO students (id, name, gender) VALUES (?,?,?)")) {
    ps.setObject(1, 11); // id
    ps.setObject(2, "Bob"); // name
    ps.setObject(3, 'male'); // gender
    int n = ps.executeUpdate(); // 1
  }
}
```

当成功执行 `executeUpdate()` 后，返回值是 int，表示插入的记录数量。

如果数据库的表设置了自增主键，那么在执行 `INSERT` 语句时，并不需要指定主键，数据库会自动分配主键。

要获取自增主键，需要指定一个 `RETURN_GENERATED_KEYS` 标志位，表示 JDBC 驱动必须返回插入的自增主键。

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  try (PreparedStatement ps = conn.prepareStatement("INSERT INTO students (name, gender) VALUES (?,?)", Statement.RETURN_GENERATED_KEYS)) {
    ps.setObject(1, "Bob"); // name
    ps.setObject(2, 'male'); // gender
    int n = ps.executeUpdate(); // 1
    try (ResultSet rs = ps.getGeneratedKeys()) {
      if (rs.next()) {
        int id = rs.getInt(1);
      }
    }
  }
}
```

### 更新数据

更新操作是 `UPDATE`，可以一次更新若干列的记录。

更新操作和插入操作在 JDBC 代码的层面上实际上没有区别，都使用 `executeUpdate()`

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  try (PreparedStatement ps = conn.prepareStatement("UPDATE students SET name=? WHERE id=?")) {
    ps.setObject(1, "Bob");
    ps.setObject(2, 999);
    int n = ps.executeUpdate(); // 返回更新的行数
  }
}
```

### 删除数据

删除操作是 `DELETE`，可以一次删除若干列。

```java
try (Connection conn = DriverManager.getConnection(JDBC_URL, JDBC_USER, JDBC_PASSWORD)) {
  try (PreparedStatement ps = conn.prepareStatement("DELETE FROM students WHERE id=?")) {
    ps.setObject(1, 9);
    int n = ps.executeUpdate(); // 删除的行数
  }
}
```

## JDBC 事务

数据库事务特性：原子性（Atomicity）、一致性（Consistency）、隔离性（Isolation）、持久性（Durability）

要在 JDBC 中执行事务，本质上就是如何把多条SQL包裹在一个数据库事务中执行。

```java
Connection conn = openConnection();
try {
  // 关闭自动提交:
  conn.setAutoCommit(false);
  // 执行多条SQL语句:
  insert();
  update();
  delete();
  // 提交事务:
  conn.commit();
} catch (SQLException e) {
  // 回滚事务:
  conn.rollback();
} finally {
  conn.setAutoCommit(true);
  conn.close();
}
```

## JDBC Batch

SQL语句相同，只有参数不同的若干语句可以进行批量执行，这种操作速度快于循环执行每个SQL。

在 JDBC 代码中，可以把同一个 SQL 但参数不同的若干次操作合并为一个 batch 执行。

```java
try (PreparedStatement ps = conn.prepareStatement("INSERT INTO students (name, gender, grade, score) VALUES (?, ?, ?, ?)")) {
  // 对同一个PreparedStatement反复设置参数并调用 addBatch():
  for (String name : names) {
    ps.setString(1, name);
    ps.setBoolean(2, gender);
    ps.setInt(3, grade);
    ps.setInt(4, score);
    ps.addBatch(); // 添加到batch
  }
  // 执行 batch:
  int[] ns = ps.executeBatch();
  for (int n : ns) {
    System.out.println(n + " inserted."); // batch中每个SQL执行的结果数量
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
