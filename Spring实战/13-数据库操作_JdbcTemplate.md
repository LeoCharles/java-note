# 13 - Spring Boot 数据库操作之 JdbcTemplate

> 对应项目模块：`demo-orm-jdbctemplate`
> 前置知识：已学完配置读取（`@ConfigurationProperties`）、Web 控制器、分层结构
> 学习目标：掌握 Spring Boot 连接数据库的方式，理解 JdbcTemplate 的增删改查用法，看懂本模块用反射+注解封装的通用 BaseDao，建立"Controller-Service-Dao"三层架构的认知。

---

## 一、本模块要解决什么问题？

任何后端应用都绕不开数据库。前端同学可以这么理解：你用 `axios` 调后端接口拿数据，后端则是用代码去数据库里查数据。本模块就是讲后端怎么连数据库、怎么执行 SQL、怎么把查询结果变成 Java 对象。

Java 操作数据库最底层的方式是 JDBC（Java Database Connectivity）——一套 JDK 自带的数据库访问标准。但原生 JDBC 很啰嗦：要手动开连接、写 SQL、拼参数、遍历 `ResultSet`、一个字段一个字段地取值赋给对象、最后还要记得关连接、处理异常。写一个查询动辄 30 行代码。

`JdbcTemplate` 是 Spring 对 JDBC 的轻量封装：它帮你管连接（从连接池取）、帮你处理异常（统一转成 `DataAccessException`）、帮你关闭资源、帮你把参数填进 SQL、帮你把查询结果映射成对象。你只需要提供 SQL 和参数。

本模块不仅演示 `JdbcTemplate` 的基本用法，还**用反射+自定义注解封装了一个通用 `BaseDao`**，实现"传一个对象进去就能自动生成 INSERT/UPDATE/DELETE/SELECT 语句"——这其实就是简易版 MyBatis-Plus。理解了这个封装，后面学 MyBatis、MyBatis-Plus 会非常轻松。

> 💡 前端类比：原生 JDBC 像你手写 `XMLHttpRequest` 发请求；`JdbcTemplate` 像 `axios`——封装了底层细节，你只管传配置。而本模块的 `BaseDao` 更进一步，像 `axios` + 一个通用 CRUD 工具，传个对象自动生成请求。

---

## 二、项目结构

```
demo-orm-jdbctemplate/
└── src/main/java/com/xkcoding/orm/jdbctemplate/
    ├── SpringBootDemoOrmJdbctemplateApplication.java   # 启动类
    ├── annotation/                  # 自定义注解（ORM 映射）
    │   ├── Table.java               #   标记表名
    │   ├── Column.java              #   标记列名
    │   ├── Pk.java                  #   标记主键
    │   └── Ignore.java             #   标记忽略字段
    ├── constant/Const.java          # 常量（加密盐前缀、分隔符）
    ├── entity/User.java             # 实体类（对应 orm_user 表）
    ├── dao/
    │   ├── base/BaseDao.java        # 通用 Dao 基类（反射+注解拼 SQL）
    │   └── UserDao.java             # User 的 Dao，继承 BaseDao
    ├── service/
    │   ├── IUserService.java         # Service 接口
    │   └── impl/UserServiceImpl.java # Service 实现
    └── controller/UserController.java # REST 接口
```

这是一个标准的**三层架构**：

| 层 | 包 | 职责 | 前端类比 |
| --- | --- | --- | --- |
| Controller | `controller` | 接收 HTTP 请求，返回响应 | 路由处理函数 |
| Service | `service` | 业务逻辑（加密、校验等） | 业务 hook/store |
| Dao (Repository) | `dao` | 数据库访问 | 调 axios 的 api 层 |
| Entity | `entity` | 数据载体（对应表行） | TS interface/type |

数据流向：`HTTP 请求 → Controller → Service → Dao → 数据库`，返回时反向。

---

## 三、pom.xml 与依赖

```xml
<dependencies>
    <!-- 1. JDBC 起步依赖：引入 JdbcTemplate + HikariCP 连接池 + spring-jdbc -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-jdbc</artifactId>
    </dependency>
    <!-- 2. Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <!-- 3. MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>
    <!-- 4. Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
    <!-- 5. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**关键依赖说明：**

- `spring-boot-starter-jdbc`：这是本模块的核心。它传递引入了 `spring-jdbc`（含 `JdbcTemplate`）、`HikariCP`（Spring Boot 2.x 默认连接池）、`spring-tx`（事务支持）。引一个，数据库访问的全套都齐了。
- `mysql-connector-java`：MySQL 的 JDBC 驱动，负责和 MySQL 通信。版本由父 POM 统一管（8.0.21）。注意 MySQL 8.x 驱动类名是 `com.mysql.cj.jdbc.Driver`（多了个 `.cj`），和 5.x 的 `com.mysql.jdbc.Driver` 不同。
- 没有引 `spring-boot-starter-data-jpa`——本模块是纯 JdbcTemplate，不用 JPA/Hibernate（那是后面 `demo-orm-jpa` 的内容）。

> 💡 前端类比：`mysql-connector-java` 像数据库的"网卡驱动"，`HikariCP` 像"连接复用管理器"（类似前端用 `axios` 复用 HTTP 连接 keep-alive），`JdbcTemplate` 像"请求封装库"。

---

## 四、配置文件 application.yml —— 数据源配置

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?useUnicode=true&characterEncoding=UTF-8&useSSL=false&autoReconnect=true&failOverReadOnly=false&serverTimezone=GMT%2B8
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
    type: com.zaxxer.hikari.HikariDataSource
    initialization-mode: always
    continue-on-error: true
    schema:
    - "classpath:db/schema.sql"
    data:
    - "classpath:db/data.sql"
    hikari:
      minimum-idle: 5
      connection-test-query: SELECT 1 FROM DUAL
      maximum-pool-size: 20
      auto-commit: true
      idle-timeout: 30000
      pool-name: SpringBootDemoHikariCP
      max-lifetime: 60000
      connection-timeout: 30000
logging:
  level:
    com.xkcoding: debug
```

### 4.1 数据源连接信息

| 配置项 | 含义 |
| --- | --- |
| `url` | 数据库连接地址。格式 `jdbc:mysql://主机:端口/库名?参数`。`serverTimezone=GMT%2B8` 指定时区（`%2B` 是 `+` 的 URL 编码），MySQL 8 必须配时区否则报错 |
| `username` / `password` | 数据库账号密码 |
| `driver-class-name` | 驱动类全限定名，MySQL 8 是 `com.mysql.cj.jdbc.Driver` |
| `type` | 连接池实现类，显式指定用 HikariCP |

### 4.2 初始化脚本（schema + data）

```yaml
initialization-mode: always       # 总是执行初始化脚本
continue-on-error: true           # 执行出错继续（不阻断启动）
schema:
- "classpath:db/schema.sql"       # 建表脚本
data:
- "classpath:db/data.sql"         # 初始数据脚本
```

Spring Boot 启动时会自动执行 `schema.sql`（建表）和 `data.sql`（插数据）。`initialization-mode` 有三个值：`always`（始终执行）、`embedded`（仅内嵌库执行，默认）、`never`（从不）。

> 💡 前端类比：这像项目启动时自动跑 `db:migrate` 和 `db:seed`，保证数据库表结构和初始数据就绪。本模块靠这个机制，即使你本地没建库，启动时也会自动建表插数据（前提是 `spring-boot-demo` 库已存在且能连上）。

### 4.3 HikariCP 连接池配置

```yaml
hikari:
  minimum-idle: 5                 # 最小空闲连接数
  maximum-pool-size: 20           # 最大连接数
  auto-commit: true              # 自动提交事务
  idle-timeout: 30000            # 空闲连接超时（30秒）
  max-lifetime: 60000            # 连接最大存活时间（60秒）
  connection-timeout: 30000      # 获取连接超时（30秒）
  connection-test-query: SELECT 1 FROM DUAL  # 连接存活测试 SQL
  pool-name: SpringBootDemoHikariCP
```

**连接池是干什么的？** 每次查询都新建/关闭数据库连接开销很大（TCP 握手、权限校验）。连接池预先建好一批连接放池子里，用时借一个、用完还回去，复用连接。HikariCP 是 Spring Boot 默认且性能最高的连接池。

> 💡 前端类比：像浏览器对 HTTP 连接做 keep-alive 复用，而不是每次请求都重新 TCP 握手。`maximum-pool-size: 20` 类似并发请求上限。

### 4.4 日志级别

```yaml
logging:
  level:
    com.xkcoding: debug
```

把 `com.xkcoding` 包的日志级别设为 `debug`，这样 BaseDao 里 `log.debug("【执行SQL】...")` 才会在控制台打印，方便看实际执行的 SQL。

---

## 五、实体类与自定义注解（ORM 映射）

### 5.1 实体类 User.java

```java
@Data
@Table(name = "orm_user")
public class User implements Serializable {
    @Pk
    private Long id;
    private String name;
    private String password;
    private String salt;
    private String email;
    @Column(name = "phone_number")
    private String phoneNumber;
    private Integer status;
    @Column(name = "create_time")
    private Date createTime;
    @Column(name = "last_login_time")
    private Date lastLoginTime;
    @Column(name = "last_update_time")
    private Date lastUpdateTime;
}
```

- `@Table(name = "orm_user")`：标记这个类对应数据库表 `orm_user`。
- `@Pk`：标记 `id` 是主键（`auto=true` 默认自增）。
- `@Column(name = "phone_number")`：标记字段 `phoneNumber` 对应列 `phone_number`（驼峰转下划线）。
- 不加 `@Column` 的字段，默认用属性名作为列名（如 `name`、`password`）。
- `implements Serializable`：可序列化，便于网络传输/缓存。
- `@Data`：Lombok 生成 getter/setter。

### 5.2 四个自定义注解

```java
@Retention(RetentionPolicy.RUNTIME)   // 运行时保留（反射能读到）
@Target({ElementType.TYPE})            // 只能标在类上
public @interface Table {
    String name();                     // 表名
}

@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD})           // 只能标在字段上
public @interface Column {
    String name();                     // 列名
}

@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD})
public @interface Pk {
    boolean auto() default true;       // 是否自增，默认 true
}

@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD})
public @interface Ignore {}            // 标记不映射到数据库的字段
```

**注解三要素：**

1. `@Retention`：保留策略。`RUNTIME` 表示运行时存在（反射可读），`SOURCE` 表示只存源码（编译后丢弃，如 `@Override`），`CLASS` 表示存进 class 但运行时不可见（默认）。
2. `@Target`：能标在哪里。`TYPE`（类/接口）、`FIELD`（字段）、`METHOD`（方法）等。
3. 注解属性：用方法形式声明（`String name()`），用 `default` 给默认值。

> 💡 前端类比：Java 注解像 TS 的装饰器（`@Table`、`@Column`），运行时通过反射读取元信息。本模块的注解就是"对象↔表/列"的映射元数据，和 Prisma 的 schema、TypeORM 的 `@Entity()`/`@Column()` 一个意思。

---

## 六、核心：BaseDao 通用基类

这是本模块最精华的部分。`BaseDao<T, P>` 用反射读取泛型类型和注解，自动拼出 SQL，实现通用 CRUD。`T` 是实体类型，`P` 是主键类型。

### 6.1 构造方法：反射获取泛型类型

```java
public class BaseDao<T, P> {
    private JdbcTemplate jdbcTemplate;
    private Class<T> clazz;

    @SuppressWarnings(value = "unchecked")
    public BaseDao(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        clazz = (Class<T>) ((ParameterizedType) getClass().getGenericSuperclass()).getActualTypeArguments()[0];
    }
}
```

- 子类 `UserDao extends BaseDao<User, Long>`，构造时调用 `super(jdbcTemplate)`。
- `getClass().getGenericSuperclass()` 拿到父类的泛型信息（`BaseDao<User, Long>`）。
- `.getActualTypeArguments()[0]` 取第一个泛型参数，即 `User.class`，存进 `clazz`。
- 这样基类就知道自己要操作哪个实体类了——这是 Java 反射的经典用法。

### 6.2 通用插入 insert

```java
protected Integer insert(T t, Boolean ignoreNull) {
    String table = getTableName(t);              // 1. 读 @Table 拿表名
    List<Field> filterField = getField(t, ignoreNull);  // 2. 过滤字段
    List<String> columnList = getColumns(filterField);  // 3. 读 @Column 拿列名
    String columns = StrUtil.join(",", columnList);     // 4. 拼列名 "a,b,c"
    String params = StrUtil.repeatAndJoin("?", columnList.size(), ",");  // 5. 拼 "? ? ?"
    Object[] values = filterField.stream().map(field -> ReflectUtil.getFieldValue(t, field)).toArray();  // 6. 取值
    String sql = StrUtil.format("INSERT INTO {table} ({columns}) VALUES ({params})", ...);
    return jdbcTemplate.update(sql, values);     // 7. 执行
}
```

执行流程：传一个 `User` 对象 → 反射读出表名 `orm_user`、列名列表、字段值 → 拼出 `INSERT INTO orm_user (name,password,...) VALUES (?,?,...)` → 用 `?` 占位符传参（防 SQL 注入）→ `jdbcTemplate.update` 执行。

`ignoreNull=true` 表示值为 null 的字段不插入（用数据库默认值），很实用。

### 6.3 通用查询 findOneById

```java
public T findOneById(P pk) {
    String sql = StrUtil.format("SELECT * FROM {table} where id = ?", ...);
    RowMapper<T> rowMapper = new BeanPropertyRowMapper<>(clazz);  // 关键：行映射器
    return jdbcTemplate.queryForObject(sql, new Object[]{pk}, rowMapper);
}
```

- `BeanPropertyRowMapper<T>`：Spring 提供的行映射器，把 `ResultSet` 的一行数据按列名映射到 `T` 的属性上（列名 `phone_number` 自动映射到属性 `phoneNumber`，支持驼峰转换）。
- `queryForObject`：查询单条记录，返回一个对象。

### 6.4 通用查询 findByExample

```java
public List<T> findByExample(T t) {
    // 根据对象非空字段拼 WHERE 条件
    List<String> columns = columnList.stream().map(s -> " and " + s + " = ? ").collect(...);
    String where = StrUtil.join(" ", columns);
    String sql = StrUtil.format("SELECT * FROM {table} where 1=1 {where}", ...);
    List<Map<String, Object>> maps = jdbcTemplate.queryForList(sql, values);
    // 把每行 Map 转成对象
    maps.forEach(map -> ret.add(BeanUtil.fillBeanWithMap(map, ReflectUtil.newInstance(clazz), true, false)));
    return ret;
}
```

传一个 `User` 对象作为查询条件，非空字段拼成 `WHERE` 子句。`where 1=1` 是个技巧，方便后面统一加 `and xxx`，避免处理首个条件的 `and/or` 问题。

### 6.5 辅助方法

- `getTableName`：读 `@Table` 注解拿表名，没有就用类名小写，外面包反引号 `` ` `` 防止关键字冲突。
- `getColumns`：读每个字段的 `@Column` 注解拿列名，没有就用属性名。
- `getField`：用 `ReflectUtil.getFields` 拿所有字段（含父类），过滤掉 `@Ignore` 和 `@Pk`（主键自增不参与插入/更新），可选过滤 null 值。

### 6.6 UserDao：继承即获得 CRUD

```java
@Repository
public class UserDao extends BaseDao<User, Long> {
    @Autowired
    public UserDao(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }
    public Integer insert(User user) { return super.insert(user, true); }
    public Integer delete(Long id) { return super.deleteById(id); }
    public Integer update(User user, Long id) { return super.updateById(user, id, true); }
    public User selectById(Long id) { return super.findOneById(id); }
    public List<User> selectUserList(User user) { return super.findByExample(user); }
}
```

`@Repository` 标记为 DAO 层 Bean。继承 `BaseDao<User, Long>` 后，一行 `super.insert(user, true)` 就完成插入——这就是通用基类的威力。新增一个 `Order` 实体，写个 `OrderDao extends BaseDao<Order, Long>`，立刻拥有全套 CRUD。

---

## 七、Service 层：业务逻辑

### 7.1 接口与实现分离

`IUserService` 是接口，`UserServiceImpl` 是实现。**为什么用接口？**

- 解耦：Controller 依赖接口而非实现，换实现类不影响 Controller。
- 可测试：测试时可以 mock 接口。
- 规范：接口定义"能做什么"，实现定义"怎么做"。

> 💡 前端类比：像 TS 里 `interface UserService { save(u: User): boolean }` + 一个实现类。但 Java 的接口比 TS 更重，是架构分层的标配。

### 7.2 密码加密逻辑

```java
public Boolean save(User user) {
    String rawPass = user.getPassword();
    String salt = IdUtil.simpleUUID();                          // 随机盐
    String pass = SecureUtil.md5(rawPass + Const.SALT_PREFIX + salt);  // MD5(密码+固定盐+随机盐)
    user.setPassword(pass);
    user.setSalt(salt);
    return userDao.insert(user) > 0;
}
```

- `IdUtil.simpleUUID()`：生成随机 UUID 作为盐。
- `SecureUtil.md5(...)`：MD5 加密。加盐（salt）是为了防彩虹表攻击——即使两个用户密码相同，因盐不同，加密结果也不同。
- `Const.SALT_PREFIX` 是固定盐 `::SpringBootDemo::`，和随机盐叠加，双重保险。
- `userDao.insert(user) > 0`：插入返回影响行数，>0 表示成功。

> ⚠️ 实际生产中 MD5 已不够安全（可被暴力破解），推荐用 BCrypt/SCrypt。本模块用 MD5 仅作演示。

### 7.3 更新的 copyProperties 技巧

```java
public Boolean update(User user, Long id) {
    User exist = getUser(id);   // 先查出库里的旧数据
    // ... 密码处理 ...
    BeanUtil.copyProperties(user, exist, CopyOptions.create().setIgnoreNullValue(true));  // 把新值拷到旧对象，忽略 null
    exist.setLastUpdateTime(new DateTime());
    return userDao.update(exist, id) > 0;
}
```

`BeanUtil.copyProperties(user, exist, ignoreNullValue=true)`：把 `user` 的非空属性拷贝到 `exist`。这是"部分更新"的经典写法——前端只传要改的字段，null 字段保留旧值。

---

## 八、Controller 层：RESTful 接口

```java
@RestController
public class UserController {
    @PostMapping("/user")           public Dict save(@RequestBody User user) {...}
    @DeleteMapping("/user/{id}")   public Dict delete(@PathVariable Long id) {...}
    @PutMapping("/user/{id}")      public Dict update(@RequestBody User user, @PathVariable Long id) {...}
    @GetMapping("/user/{id}")       public Dict getUser(@PathVariable Long id) {...}
    @GetMapping("/user")            public Dict getUser(User user) {...}
}
```

**RESTful 设计：**

| 方法 | 路径 | 语义 |
| --- | --- | --- |
| POST | `/user` | 新增 |
| DELETE | `/user/{id}` | 删除 |
| PUT | `/user/{id}` | 更新 |
| GET | `/user/{id}` | 查单个 |
| GET | `/user?name=xx` | 查列表（条件查询） |

- `@RequestBody`：把请求体 JSON 反序列化成 `User` 对象。
- `@PathVariable`：取路径里的 `{id}`。
- `GET /user` 的 `getUser(User user)`：没有 `@RequestBody`，Spring 自动把查询参数绑定到 `User` 对象属性上（如 `?name=xkcoding` 绑定到 `user.name`）。
- 返回 `Dict`（Hutool 字典）封装成 `{code, msg, data}` 统一格式。

---

## 九、运行与验证

### 9.1 准备数据库

需要本地 MySQL，建库 `spring-boot-demo`（表和初始数据启动时自动建）。配置里账号密码默认 `root/root`，按你实际情况改 `application.yml`。

### 9.2 启动

```sh
mvn spring-boot:run
```

启动时会看到日志打印建表 SQL 和插入数据。控制台开 debug 级别后，每次操作都会打印 `【执行SQL】` 和参数。

### 9.3 测试接口

```sh
# 新增用户
curl -X POST http://localhost:8080/demo/user -H "Content-Type: application/json" -d '{"name":"test","password":"123456","email":"t@t.com","phoneNumber":"13800000000"}'

# 查询单个
curl http://localhost:8080/demo/user/1

# 条件查询
curl "http://localhost:8080/demo/user?name=user_1"

# 更新
curl -X PUT http://localhost:8080/demo/user/1 -H "Content-Type: application/json" -d '{"email":"new@t.com"}'

# 删除
curl -X DELETE http://localhost:8080/demo/user/2
```

---

## 十、动手练习

1. **加一个字段**：给 `User` 加 `age` 字段，改 `schema.sql` 加列，重启验证插入/查询能带上新字段。
2. **写一个新实体的 CRUD**：建 `Order` 实体 + `OrderDao extends BaseDao<Order, Long>` + Service + Controller，验证通用 BaseDao 对新表也生效。
3. **观察 SQL 日志**：把 `logging.level.com.xkcoding` 改成 `info`，观察 SQL 不再打印，体会日志级别的作用。
4. **测试 ignoreNull**：插入时不传某字段，观察生成的 INSERT 是否跳过该列。
5. **故意制造 SQL 注入测试**：在 name 里传 `' OR 1=1 --`，观察因用 `?` 占位符而被当成普通字符串，体会预编译防注入。
6. **改连接池参数**：把 `maximum-pool-size` 改成 2，并发请求观察是否出现获取连接超时。

---

## 十一、本模块知识点总结（结合实际开发详解）

JdbcTemplate 是 Spring 数据访问的基石，理解它对后续学 MyBatis、JPA 都有帮助。下面把核心知识点放到真实开发里讲透。

### 11.1 数据源与连接池：性能的生命线

**实际开发中怎么用？**

Spring Boot 2.x 默认用 HikariCP，它号称"最快的连接池"。你基本不用改默认配置就能跑，但生产环境通常要调优：

| 参数 | 生产建议 | 说明 |
| --- | --- | --- |
| `maximum-pool-size` | 10~20（按业务） | 太大压垮数据库，太小并发不够。公式：`连接数 = (核心数 * 2 + 磁盘数)` 仅供参考 |
| `minimum-idle` | = maximum-pool-size | 固定池大小，避免频繁创建/销毁 |
| `max-lifetime` | 30分钟（默认偏小） | 防止长连接被 MySQL 的 `wait_timeout` 干掉导致报错 |
| `connection-timeout` | 30秒 | 获取连接超时，超时说明池满了，该告警 |
| `connection-test/valid-test-query` | MySQL 用 `SELECT 1` | 借出连接前验证有效性，避免拿到死连接 |

**常见坑：**

1. **连接泄漏**：忘了关连接（JdbcTemplate 已帮你关，但原生 JDBC 容易漏），池子被耗尽，新请求全卡住。
2. **max-lifetime < 数据库 wait_timeout**：如果 Hikari 的 `max-lifetime` 大于 MySQL 的 `wait_timeout`（默认 8 小时，但常被调成更小），MySQL 先掐断连接，Hikari 还以为连接活着，拿个死连接报错。**原则：Hikari 的 max-lifetime 要比数据库的 wait_timeout 小 30~60 秒。**
3. **生产用 `always` 初始化**：`initialization-mode: always` 会在每次启动都执行 schema.sql，生产环境可能误删数据！生产应设为 `never`，用 Flyway/Liquibase 做版本化迁移（后面 `demo-flyway` 会讲）。

> 💡 前端类比：连接池像前端的"请求队列/并发控制"。`maximum-pool-size: 20` 类似 `p-limit(20)` 限制并发。池满了新请求排队，超时就报错。

### 11.2 JdbcTemplate 的核心 API

**实际开发常用的方法：**

| 方法 | 用途 | 返回 |
| --- | --- | --- |
| `update(sql, args...)` | 增/删/改 | 影响行数 |
| `queryForObject(sql, type, args)` | 查单值/单对象 | 单个值/对象 |
| `queryForList(sql, args)` | 查多行 | `List<Map>` |
| `query(sql, RowMapper, args)` | 查多行映射成对象 | `List<T>` |
| `batchUpdate(sql, List<Object[]>)` | 批量操作 | 每条影响行数数组 |

**最佳实践：**

1. **永远用 `?` 占位符传参**，不要用字符串拼接 SQL——防 SQL 注入。本模块 BaseDao 全程用 `?`。
2. **用 `BeanPropertyRowMapper` 自动映射**，省去手写字段赋值。但注意它要求列名和属性名能对应（支持下划线转驼峰）。
3. **复杂查询写自定义 RowMapper**：当映射逻辑复杂（如嵌套对象、类型转换）时，实现 `RowMapper<T>` 手动映射。

**常见坑：**

- `queryForObject` 查不到数据会抛 `EmptyResultDataAccessException`，不是返回 null！用前要么 catch，要么先 `queryForList` 判断。
- `BeanPropertyRowMapper` 要求实体类有**无参构造**和 **setter**（用 `@Data` 就有），否则映射失败。
- 大量数据用 `queryForList` 一次性加载进内存会 OOM，应该用分页或流式查询。

### 11.3 三层架构：Controller-Service-Dao

本模块是教科书级的三层架构示范。

**为什么要分层？**

| 层 | 关注点 | 不该做的事 |
| --- | --- | --- |
| Controller | HTTP 协议（参数解析、响应格式） | 不该写业务逻辑 |
| Service | 业务规则（加密、校验、事务编排） | 不该关心 HTTP 细节 |
| Dao | 数据存取（SQL） | 不该写业务逻辑 |

**分层的好处：**

1. **单一职责**：每层只管自己的事，改一层不影响其他层。比如 Controller 从 `Dict` 换成统一响应体，Service 不用动。
2. **可测试**：Service 不依赖 HTTP，可以脱离 Web 容器单测。
3. **可替换**：Dao 从 JdbcTemplate 换成 MyBatis，Service 接口不变，Controller 无感知。

**实际开发的演进：**

- 小项目：Controller + Service + Dao 三层，够用。
- 中型项目：Service 上面加 Facade 层（对 RPC 暴露），Dao 细分 Repository。
- 大项目/微服务：每层再拆，引入领域模型（DDD），Dao 之上加防腐层。

> 💡 前端类比：这像前端 `组件层(View) - hooks/store 层(逻辑) - api 层(请求)` 的分层。Controller≈组件里的事件处理，Service≈业务 hooks，Dao≈api 请求封装。

### 11.4 反射+注解封装通用 DAO：MyBatis-Plus 的雏形

本模块的 `BaseDao` 用反射读注解拼 SQL，这就是 MyBatis-Plus `BaseMapper` 的简化版。

**核心思路：**

1. 用 `@Table`/`@Column` 注解建立"对象↔表"映射元数据。
2. 用反射读取泛型类型，知道操作哪个实体。
3. 用反射遍历字段，拼出 SQL 列名和占位符。
4. 用 `BeanPropertyRowMapper` 把结果集映射回对象。

**实际开发中你会怎么选？**

- **不自己造轮子**：生产环境直接用 MyBatis-Plus，它已经把 `BaseDao` 做到了极致（条件构造器、分页、逻辑删除、自动填充），还经过大规模验证。本模块的 BaseDao 只是教学用，功能简陋（不支持复杂条件、排序、分页）。
- **但要理解原理**：理解了 BaseDao，用 MyBatis-Plus 时就知道 `baseMapper.insert(user)` 背后发生了什么，出问题能调试。

**本 BaseDao 的局限（常见坑）：**

1. 不支持分页——生产必备，这里没有。
2. 不支持复杂条件（`>`、`like`、`in`）——只支持 `=`。
3. 不支持事务——Service 方法没加 `@Transactional`，多步操作可能半成功。
4. 反射性能——每次操作都反射读注解，生产应缓存注解元数据（MyBatis-Plus 启动时解析一次缓存）。

### 11.5 事务管理：JdbcTemplate 默认没开

**本模块的一个隐藏问题**：`UserServiceImpl` 的方法没有加 `@Transactional`。如果某个业务方法里先删 A 再插 B，删成功插失败，A 就丢了——数据不一致。

**实际开发必须加事务：**

```java
@Service
public class UserServiceImpl implements IUserService {
    @Transactional(rollbackFor = Exception.class)   // 开启事务，任何异常都回滚
    public Boolean transfer(...) { ... }
}
```

`@Transactional` 是 Spring 声明式事务的核心。加了它，方法内的多个数据库操作要么全成功，要么全回滚。前提是引入了 `spring-boot-starter-jdbc`（已含事务支持）且启动类加了 `@EnableTransactionManagement`（Spring Boot 自动配置已开启，一般不用手动加）。

**常见坑：**

1. `@Transactional` 加在 private 方法上不生效——Spring 用 AOP 代理，private 方法无法被代理。
2. 同类内部方法自调用，事务失效——`this.method()` 走的是原对象不是代理对象。解决：把方法拆到另一个类，或注入自己。
3. 默认只对 `RuntimeException` 回滚，检查异常不回滚——建议加 `rollbackFor = Exception.class`。

### 11.6 密码加密：永远不要明文存

本模块用 `MD5(密码 + 固定盐 + 随机盐)`。思路对（加盐防彩虹表），但算法弱。

**生产推荐：BCrypt**

```java
// Spring Security 自带
PasswordEncoder encoder = new BCryptPasswordEncoder();
String hashed = encoder.encode("123456");           // 每次加密结果不同（内含随机盐）
encoder.matches("123456", hashed);                  // 验证
```

BCrypt 自带盐（存在哈希串里），且可调成本因子（慢哈希），抗暴力破解。这是行业标准。

---

> 📌 **学习建议**：JdbcTemplate 是 Spring 数据访问的"原点"——它最接近 SQL，让你看清每一步在干什么。建议先把本模块的 BaseDao 读懂（反射拼 SQL 的逻辑），再去看 MyBatis、MyBatis-Plus，你会发现它们只是把这套封装做得更完善。另外，作为前端转后端，重点建立"数据流向"的心智模型：一个 HTTP 请求如何穿过 Controller→Service→Dao→数据库，再原路返回。这个链路一旦想通，后面所有数据库相关模块（JPA、MyBatis、多数据源）都是同一个套路的不同实现。
