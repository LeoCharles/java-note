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

