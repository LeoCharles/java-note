# 15 - 数据库操作之 MyBatis

> 对应项目模块：`demo-orm-mybatis`
> 前置知识：已学完配置注入（`@ConfigurationProperties`）、分层结构（Controller/Service/Mapper）
> 学习目标：理解 MyBatis 是什么、它和 JdbcTemplate/JPA 的区别，能看懂并写出 Mapper 接口 + XML 的增删改查，掌握启动初始化数据库、连接池配置、驼峰映射等实战要点。

---

## 一、本模块要解决什么问题？

前面几个 ORM 模块里，我们已经见过两种操作数据库的方式：JdbcTemplate（手写 SQL，但样板代码多）和 JPA（全自动 ORM，写接口名就能查，但复杂查询不灵活）。本模块引入 **MyBatis**——一个介于两者之间的"半自动 ORM"。

**MyBatis 的定位**：

- 像 JdbcTemplate 一样，SQL 由你自己写，你有完全的控制力；
- 但它把"执行 SQL、把结果集映射成 Java 对象"这套样板代码全自动化了，不用再手写 `RowMapper`；
- SQL 和 Java 代码分离（写在 XML 或注解里），便于维护和调优。

> 💡 前端类比：MyBatis 有点像前端的 Prisma 或 TypeORM，但更贴近 SQL——Prisma 让你写 schema 自动生成查询，MyBatis 让你手写 SQL 自动映射结果。可以理解为"带对象映射能力的 SQL 模板引擎"。

本模块的最终效果：启动时自动建表、插数据，然后通过 `UserMapper` 接口完成对 `orm_user` 表的查询、新增、删除。

---

## 二、项目结构

```
demo-orm-mybatis/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/orm/mybatis/
    │   ├── SpringBootDemoOrmMybatisApplication.java   # 启动类（@MapperScan）
    │   ├── entity/
    │   │   └── User.java                             # 实体类
    │   └── mapper/
    │       └── UserMapper.java                        # Mapper 接口（SQL 在注解 + XML）
    └── resources/
        ├── application.yml                            # 数据源 + MyBatis 配置
        ├── db/
        │   ├── schema.sql                            # 建表脚本
        │   └── data.sql                              # 初始化数据
        └── mappers/
            └── UserMapper.xml                        # SQL 映射 XML
```

注意分层：`entity`（实体）→ `mapper`（数据访问）。本 demo 没有写 `service` 和 `controller`，直接在测试类里调 Mapper 验证，重点放在"MyBatis 怎么用"上。

---

## 三、pom.xml 依赖

```xml
<properties>
    <mybatis.version>1.3.2</mybatis.version>
</properties>

<dependencies>
    <!-- MyBatis 官方脚手架 -->
    <dependency>
        <groupId>org.mybatis.spring.boot</groupId>
        <artifactId>mybatis-spring-boot-starter</artifactId>
        <version>${mybatis.version}</version>
    </dependency>

    <!-- MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- Lombok、Hutool、Guava、test -->
    ...
</dependencies>
```

**关键依赖解读：**

- `mybatis-spring-boot-starter`：MyBatis 官方为 Spring Boot 做的整合包。引一个就等于引入了 MyBatis 核心 + MyBatis-Spring（把 MyBatis 接入 Spring 容器的桥）+ 自动配置。注意它的 groupId 是 `org.mybatis.spring.boot`，不是 Spring 官方的 `org.springframework.boot`——这是第三方（MyBatis 团队）维护的 starter。
- `mysql-connector-java`：MySQL 的 JDBC 驱动，让 Java 能连 MySQL。版本由父 POM 管（8.0.21）。
- 没有引 `spring-boot-starter-web`：本模块不暴露 HTTP 接口，纯数据访问，所以不需要 Web 依赖。

> 💡 注意版本号：`mybatis.version` 写在本模块的 `<properties>` 里（1.3.2），而不是父 POM。因为 MyBatis 的 starter 不在 Spring Boot 的 BOM 管理范围内，需要自己锁版本。这是和前面模块（依赖版本全交给父 POM）的一个小区别。

---

## 四、启动类：`@MapperScan` 扫描 Mapper

```java
@MapperScan(basePackages = {"com.xkcoding.orm.mybatis.mapper"})
@SpringBootApplication
public class SpringBootDemoOrmMybatisApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoOrmMybatisApplication.class, args);
    }
}
```

新增了 `@MapperScan(basePackages = {...})`，这是 MyBatis 的关键注解。

**`@MapperScan` 做了什么？**

它告诉 MyBatis：去 `com.xkcoding.orm.mybatis.mapper` 包下扫描所有接口，为每个接口生成一个代理实现类并注册成 Spring Bean。这样你在 Service/Controller 里 `@Autowired` 一个 `UserMapper` 接口，就能直接用——虽然接口没有实现类，MyBatis 在运行时用动态代理帮你生成了。

> 💡 前端类比：这有点像 Vue 的自动注册全局组件——你只要把组件放到指定目录，框架自动帮你注册，不用一个个 `components: { MyComponent }`。`@MapperScan` 就是告诉 MyBatis"Mapper 接口都在这个包，帮我自动实现"。

**`@MapperScan` vs `@Mapper`：**

- `@MapperScan`：写在启动类上，扫描整个包，包下所有接口一次性全注册。**推荐用于真实项目。**
- `@Mapper`：写在单个接口上，只注册这一个。本模块的 `UserMapper` 接口上同时加了 `@Mapper` 和 `@Component`，其实有了 `@MapperScan` 后这两个注解是多余的，但加上也无害，属于"双保险"写法。

**常见坑：** 忘了加 `@MapperScan`，或者 `basePackages` 路径写错，导致 Mapper 接口没被扫描，`@Autowired` 时报 `NoSuchBeanDefinitionException`。

---

## 五、实体类 `User.java`

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User implements Serializable {
    private static final long serialVersionUID = -1840831686851699943L;

    private Long id;
    private String name;
    private String password;
    private String salt;
    private String email;
    private String phoneNumber;   // 对应数据库 phone_number
    private Integer status;
    private Date createTime;       // 对应 create_time
    private Date lastLoginTime;    // 对应 last_login_time
    private Date lastUpdateTime;   // 对应 last_update_time
}
```

**要点：**

- Lombok 四件套：`@Data`（getter/setter 等）+ `@NoArgsConstructor`（无参构造）+ `@AllArgsConstructor`（全参构造）+ `@Builder`（链式构造，测试里用 `User.builder().name(...).build()`）。
- `implements Serializable`：实现序列化接口。MyBatis 缓存（二级缓存）可能需要把对象序列化存起来，所以实体类建议实现 `Serializable`。
- 字段名用驼峰（`phoneNumber`），数据库列名用下划线（`phone_number`）——这是 MyBatis 的经典映射场景，靠配置 `map-underscore-to-camel-case` 自动转换（见第七节）。

---

## 六、Mapper 接口与 SQL：注解 + XML 混合写法

`mapper/UserMapper.java`：

```java
@Mapper
@Component
public interface UserMapper {

    // 注解写法：直接把 SQL 写在注解里
    @Select("SELECT * FROM orm_user")
    List<User> selectAllUser();

    @Select("SELECT * FROM orm_user WHERE id = #{id}")
    User selectUserById(@Param("id") Long id);

    // XML 写法：SQL 写在 UserMapper.xml 里，接口只声明方法签名
    int saveUser(@Param("user") User user);

    int deleteById(@Param("id") Long id);
}
```

本模块故意混用了两种写法，正好对比讲解。

### 6.1 注解写法（`@Select`）

```java
@Select("SELECT * FROM orm_user WHERE id = #{id}")
User selectUserById(@Param("id") Long id);
```

- `@Select` 注解里直接写 SQL，简单查询用这个最快。
- `#{id}` 是 MyBatis 的参数占位符，它会从方法参数里取。`@Param("id")` 给参数起个名字，让 `#{id}` 能对应上。
- 返回值 `User`：MyBatis 自动把查询结果的一行映射成 `User` 对象（靠列名→字段名映射，下划线转驼峰）。

> ⚠️ `#{id}` 和 `${id}` 的区别（非常重要）：
> - `#{id}`：预编译参数，会被替换成 JDBC 的 `?` 占位符，再通过 `PreparedStatement.setString` 填值。**防 SQL 注入，永远优先用这个。**
> - `${id}`：字符串拼接，直接把值塞进 SQL 字符串里。有 SQL 注入风险，**只在需要动态拼表名/列名/排序字段时才用**（这些不能用 `?` 占位）。

### 6.2 XML 写法（`UserMapper.xml`）

```xml
<mapper namespace="com.xkcoding.orm.mybatis.mapper.UserMapper">

    <insert id="saveUser">
        INSERT INTO `orm_user` (`name`, `password`, `salt`, `email`, `phone_number`,
                                `status`, `create_time`, `last_login_time`, `last_update_time`)
        VALUES (#{user.name}, #{user.password}, #{user.salt}, #{user.email},
                #{user.phoneNumber}, #{user.status}, #{user.createTime},
                #{user.lastLoginTime}, #{user.lastUpdateTime})
    </insert>

    <delete id="deleteById">
        DELETE FROM `orm_user` WHERE `id` = #{id}
    </delete>
</mapper>
```

**关键点：**

- `namespace` 必须等于对应 Mapper 接口的全限定名 `com.xkcoding.orm.mybatis.mapper.UserMapper`，MyBatis 靠这个把 XML 和接口方法绑定。
- `<insert id="saveUser">` 的 `id` 必须等于接口方法名 `saveUser`，MyBatis 靠方法名匹配。
- `#{user.name}`：方法参数是 `@Param("user") User user`，所以用 `user` 作为对象名，`.` 取属性。MyBatis 用反射读 `user.getName()`。
- 列名 `phone_number` 对应 `#{user.phoneNumber}`——MyBatis 把 `phoneNumber` 当属性名，通过 getter 取值，和列名无关。

### 6.3 注解 vs XML，实际开发怎么选？

| 维度 | 注解（`@Select` 等） | XML |
| --- | --- | --- |
| 适用场景 | 简单查询、单表 CRUD | 复杂查询、动态条件、多表关联 |
| 动态 SQL | 支持（`@SelectProvider`，但难写） | 强（`<if>`、`<foreach>`、`<choose>` 等标签） |
| 可读性 | 简单 SQL 清晰 | 复杂 SQL 结构化、好维护 |
| SQL 和代码 | 耦合在一起 | 分离，DBA 可独立维护 |
| 实际项目主流 | 少量简单查询用 | **复杂业务用 XML 居多** |

**最佳实践**：简单查询用注解图方便，复杂查询（带条件拼接、分页、多表）用 XML。两者可以在同一个 Mapper 里混用，本模块就是这么做的。

---

## 七、配置文件 `application.yml`

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
    com.xkcoding.orm.mybatis.mapper: trace
mybatis:
  configuration:
    map-underscore-to-camel-case: true
  mapper-locations: classpath:mappers/*.xml
  type-aliases-package: com.xkcoding.orm.mybatis.entity
```

分三块讲。

### 7.1 数据源配置（`spring.datasource`）

- `url`：JDBC 连接串。注意参数：`serverTimezone=GMT%2B8`（时区，MySQL 8 必须显式设，否则报时区错）、`useSSL=false`（不用 SSL）、`characterEncoding=UTF-8`（编码）。
- `type: com.zaxxer.hikari.HikariDataSource`：指定用 HikariCP 连接池（Spring Boot 2.x 默认就是它，可省略）。
- `schema` / `data`：启动时自动执行的 SQL 脚本——`schema.sql` 建表，`data.sql` 插数据。
- `initialization-mode: always`：每次启动都执行（还有 `embedded` 只对内嵌库执行、`never` 不执行）。
- `continue-on-error: true`：SQL 执行出错也继续（比如表已存在时 `CREATE` 报错，不中断启动）。

> 💡 这套"启动自动建表插数据"的机制非常适合 demo 和测试，真实项目一般用 Flyway/Liquibase 做版本化迁移（后续 `demo-flyway` 模块会讲）。

### 7.2 连接池配置（`hikari`）

HikariCP 是 Spring Boot 默认连接池，号称 Java 最快。关键参数：

| 参数 | 含义 | 本模块值 |
| --- | --- | --- |
| `minimum-idle` | 最小空闲连接数 | 5 |
| `maximum-pool-size` | 最大连接数 | 20 |
| `idle-timeout` | 空闲连接超时（毫秒） | 30000 |
| `max-lifetime` | 连接最大存活时间 | 60000 |
| `connection-timeout` | 获取连接超时 | 30000 |
| `connection-test-query` | 连接存活测试 SQL | `SELECT 1 FROM DUAL` |

> 💡 前端类比：连接池像一个"数据库连接的缓存池"，类似前端的 HTTP 连接复用（keep-alive）。预先建好一批连接放池子里，用的时候借一个、用完还回去，避免每次请求都新建连接（建连接很慢）。

### 7.3 MyBatis 配置（`mybatis`）

```yaml
mybatis:
  configuration:
    map-underscore-to-camel-case: true   # 下划线列名 → 驼峰属性名
  mapper-locations: classpath:mappers/*.xml   # XML 映射文件位置
  type-aliases-package: com.xkcoding.orm.mybatis.entity   # 实体类别名包
```

- `map-underscore-to-camel-case: true`：**最重要的配置**。让数据库 `phone_number` 自动映射到 Java `phoneNumber`，不用手写映射关系。这就是为什么 `User` 类字段是驼峰，却能自动对应下划线列名。
- `mapper-locations`：告诉 MyBatis 去 `classpath:mappers/` 下找 XML 映射文件。不配的话 XML 不会加载，`saveUser`/`deleteById` 会报找不到 SQL。
- `type-aliases-package`：给实体类起短别名。配了之后 XML 里 `resultType="User"` 就行，不用写全限定名 `com.xkcoding.orm.mybatis.entity.User`。

### 7.4 日志配置（`logging`）

```yaml
logging:
  level:
    com.xkcoding: debug
    com.xkcoding.orm.mybatis.mapper: trace   # Mapper 包用 trace，打印执行的 SQL
```

把 Mapper 包日志设成 `trace`，MyBatis 会打印每条执行的 SQL、参数、返回行数——**调试 SQL 的利器**。实际开发中排查"查不到数据""SQL 拼错"全靠它。

---

## 八、SQL 脚本：启动初始化

`db/schema.sql`（建表）：

```sql
DROP TABLE IF EXISTS `orm_user`;
CREATE TABLE `orm_user` (
  `id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  `name` VARCHAR(32) NOT NULL UNIQUE COMMENT '用户名',
  `password` VARCHAR(32) NOT NULL COMMENT '加密后的密码',
  `salt` VARCHAR(32) NOT NULL COMMENT '加密使用的盐',
  `email` VARCHAR(32) NOT NULL UNIQUE COMMENT '邮箱',
  `phone_number` VARCHAR(15) NOT NULL UNIQUE COMMENT '手机号码',
  `status` INT(2) NOT NULL DEFAULT 1 COMMENT '状态，-1：逻辑删除，0：禁用，1：启用',
  `create_time` DATETIME NOT NULL DEFAULT NOW() COMMENT '创建时间',
  `last_login_time` DATETIME DEFAULT NULL COMMENT '上次登录时间',
  `last_update_time` DATETIME NOT NULL DEFAULT NOW() COMMENT '上次更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Spring Boot Demo Orm 系列示例表';
```

`db/data.sql`（插两条初始数据）：

```sql
INSERT INTO `orm_user`(`id`,`name`,`password`,`salt`,`email`,`phone_number`) VALUES (1, 'user_1', 'ff342e862e7c3285cdc07e56d6b8973b', '412365a109674b2dbb1981ed561a4c70', 'user1@xkcoding.com', '17300000001');
INSERT INTO `orm_user`(`id`,`name`,`password`,`salt`,`email`,`phone_number`) VALUES (2, 'user_2', '6c6bf02c8d5d3d128f34b1700cb1e32c', 'fcbdd0e8a9404a5585ea4e01d0e4d7a0', 'user2@xkcoding.com', '17300000002');
```

注意列名是下划线（`phone_number`、`create_time`），和实体类的驼峰字段（`phoneNumber`、`createTime`）对应，靠 `map-underscore-to-camel-case` 自动映射。密码和盐是预先 MD5 加密好的值。

---

## 九、测试类：验证 CRUD

`UserMapperTest.java` 继承了启动测试类（拿到 Spring 上下文），注入 `UserMapper` 后测四个方法：

```java
@Slf4j
public class UserMapperTest extends SpringBootDemoOrmMybatisApplicationTests {
    @Autowired
    private UserMapper userMapper;

    @Test
    public void selectAllUser() {
        List<User> userList = userMapper.selectAllUser();
        Assert.assertTrue(CollUtil.isNotEmpty(userList));
        log.debug("【userList】= {}", userList);
    }

    @Test
    public void selectUserById() {
        User user = userMapper.selectUserById(1L);
        Assert.assertNotNull(user);
    }

    @Test
    public void saveUser() {
        String salt = IdUtil.fastSimpleUUID();
        User user = User.builder().name("testSave3")
            .password(SecureUtil.md5("123456" + salt)).salt(salt)
            .email("testSave3@xkcoding.com").phoneNumber("17300000003")
            .status(1).lastLoginTime(new DateTime())
            .createTime(new DateTime()).lastUpdateTime(new DateTime()).build();
        int i = userMapper.saveUser(user);
        Assert.assertEquals(1, i);
    }

    @Test
    public void deleteById() {
        int i = userMapper.deleteById(1L);
        Assert.assertEquals(1, i);
    }
}
```

**要点：**

- `@Autowired private UserMapper userMapper`：直接注入接口，MyBatis 代理实现类在背后工作。
- `saveUser` 用了 `User.builder()`（Lombok `@Builder`）链式构造对象，密码用 `SecureUtil.md5("123456" + salt)` 加盐加密——这是密码存储的标准做法（明文 + 随机盐 → MD5）。
- 返回值 `int` 表示影响行数，`1` 表示成功插入/删除 1 行。

---

## 十、运行与验证

### 10.1 前置准备

需要本地 MySQL，建库 `spring-boot-demo`：

```sql
CREATE DATABASE `spring-boot-demo` DEFAULT CHARACTER SET utf8mb4;
```

改 `application.yml` 里的 `username`/`password` 为你的 MySQL 账号。

### 10.2 运行测试

在模块目录执行：

```sh
mvn test -Dtest=UserMapperTest
```

或在 IDE 里右键 `UserMapperTest` 运行。因为 `initialization-mode: always`，每次启动会先 `DROP` 再建表、插数据，所以测试是幂等的。

### 10.3 观察日志

控制台会打印 MyBatis 执行的 SQL（因为 mapper 包日志是 trace）：

```
==>  Preparing: SELECT * FROM orm_user WHERE id = ?
==> Parameters: 1(Long)
<==      Total: 1
```

这是排查 SQL 问题的第一手信息。

---

## 十一、动手练习

1. **加一个更新方法**：在 `UserMapper` 接口加 `int updateUser(@Param("user") User user)`，在 XML 写 `<update>` 根据 id 更新 name 和 email，写测试验证。
2. **体验 `#{}` 和 `${}` 的区别**：写一个 `selectByOrder(@Param("field") String field)` 用 `${field}` 拼排序列，体会动态列名场景（注意这是 `${}` 的合法用途）。
3. **加动态条件查询**：在 XML 用 `<if>` 写一个"按 name/email 可选条件查询"的方法，体会 XML 动态 SQL 的威力。
4. **关闭驼峰映射**：把 `map-underscore-to-camel-case` 改成 `false`，重启跑 `selectAllUser`，观察 `phoneNumber` 等字段变成 null，体会这个配置的作用。
5. **把注解 SQL 改成 XML**：把 `selectAllUser` 的 `@Select` 去掉，改到 XML 里写 `<select>`，验证注解和 XML 可以互换。

---

## 十二、本模块知识点总结（结合实际开发详解）

MyBatis 是国内 Java 后端最流行的 ORM 框架（没有之一），掌握它对实际开发至关重要。下面把核心知识点放到真实场景里讲透。

### 12.1 MyBatis vs JPA vs JdbcTemplate：怎么选？

**三种方式定位对比：**

| 方式 | SQL 控制度 | 样板代码量 | 复杂查询 | 学习成本 |
| --- | --- | --- | --- | --- |
| JdbcTemplate | 完全手写 | 多（RowMapper） | 灵活 | 低 |
| MyBatis | 完全手写 | 少（自动映射） | 灵活 + 动态 SQL 强 | 中 |
| JPA | 不写 SQL | 极少 | 复杂查询吃力 | 高 |

**实际开发的选择标准：**

- **业务复杂、查询多变、对 SQL 性能要求高**（互联网公司大多数项目）→ **MyBatis**。国内主流，招聘认可度最高。
- **模型简单、CRUD 为主、想少写 SQL**（管理后台、中小项目）→ JPA，开发速度快。
- **极少数特殊场景**（存储过程、极简查询）→ JdbcTemplate。

**为什么国内主流是 MyBatis？**

1. 国内项目业务复杂度高，多表关联、动态条件多，JPA 的方法名查询和 JPQL 力不从心。
2. DBA 和后端分工协作时，XML 里的 SQL 方便 DBA 审查优化，JPA 的 SQL 是自动生成的不透明。
3. MyBatis 的动态 SQL（`<if>`/`<foreach>`）处理条件查询极其灵活，这是 JPA 的弱项。
4. 生态成熟：MyBatis-Plus（后续模块）在 MyBatis 上加了通用 CRUD、代码生成、分页，弥补了它"简单 CRUD 也要写 SQL"的短板。

### 12.2 Mapper 接口为什么不用写实现类就能用？

这是 MyBatis 最"魔法"的地方。`UserMapper` 是个接口，没有实现类，却能 `@Autowired` 注入并调用。原理是 **JDK 动态代理**：

1. `@MapperScan` 触发 MyBatis 扫描指定包的接口。
2. MyBatis 为每个接口用 `Proxy.newProxyInstance` 生成一个代理对象，注册成 Bean。
3. 你调用 `userMapper.selectAllUser()` 时，实际调用代理对象的 `invoke` 方法。
4. 代理对象根据方法名找到对应的 SQL（注解里的或 XML 里的），执行 JDBC，把结果映射成对象返回。

> 💡 前端类比：这像 Vue 的响应式——你写的是普通对象，框架在背后用 `Proxy` 拦截读写。MyBatis 用动态代理拦截"方法调用"，转成"执行 SQL"。你只定义接口（声明要做什么），实现（怎么做）由框架补全。

**实际开发的启示**：正因为是代理，所以 Mapper 接口的方法不能重载（同名不同参数），因为 MyBatis 靠方法名找 SQL，重载会导致歧义。这是新手常踩的坑。

### 12.3 `#{}` vs `${}`：SQL 注入的防线

**`#{}`（预编译占位）**：生成 `?` 占位符 + `PreparedStatement` 设值，防注入。**99% 场景用这个。**

```xml
SELECT * FROM orm_user WHERE id = #{id}
-- 实际执行：SELECT * FROM orm_user WHERE id = ?  然后 setLong(1, 1)
```

**`${}`（字符串拼接）**：直接把值塞进 SQL 字符串，有注入风险。**只在不能用 `?` 的地方用**：

```xml
SELECT * FROM orm_user ORDER BY ${orderField} ${orderDir}
-- 排序字段和方向不能用 ? 占位，只能 ${} 拼
```

**实际开发的最佳实践：**

1. 传值（where 条件、insert 值）一律用 `#{}`。
2. 表名、列名、排序方向、`IN` 的列表（用 `<foreach>` 配合 `#{}`）才考虑 `${}`，且必须做白名单校验。
3. 永远不要把用户输入直接 `${}` 拼进 SQL——这是 SQL 注入的典型漏洞。

**常见坑**：新手图省事全用 `${}`，导致系统存在 SQL 注入。务必养成"`#{}` 优先"的肌肉记忆。

### 12.4 动态 SQL：MyBatis 的杀手锏

XML 里用标签拼动态 SQL，是 MyBatis 比 JPA 强大的核心：

```xml
<select id="searchUser" resultType="User">
    SELECT * FROM orm_user
    <where>
        <if test="name != null and name != ''">
            AND name LIKE CONCAT('%', #{name}, '%')
        </if>
        <if test="email != null">
            AND email = #{email}
        </if>
        <if test="status != null">
            AND status = #{status}
        </if>
    </where>
    ORDER BY id DESC
</select>
```

常用标签：

| 标签 | 作用 |
| --- | --- |
| `<if>` | 条件成立才拼接 SQL 片段 |
| `<where>` | 自动加 WHERE，且去掉首个 AND/OR（避免 `WHERE AND ...`） |
| `<foreach>` | 遍历集合，常用于 `IN (...)` 和批量插入 |
| `<choose>`/`<when>`/`<otherwise>` | 类似 if-else if-else |
| `<set>` | 自动加 SET，去掉末尾逗号（用于动态 update） |
| `<trim>` | 自定义前缀后缀裁剪，`<where>`/`<set>` 的底层 |

**实际开发价值**：一个"多条件可选查询"接口（前端传哪几个条件就按哪几个查），用动态 SQL几行搞定，JPA 实现同样逻辑要写一堆 `Specification` 或 `@Query`，痛苦得多。

### 12.5 结果映射：下划线转驼峰与 `resultMap`

**简单映射**：靠 `map-underscore-to-camel-case` 自动把 `phone_number` → `phoneNumber`，单表查询够用。

**复杂映射**（多表关联）需要 `resultMap` 手动定义：

```xml
<resultMap id="userWithOrderMap" type="User">
    <id property="id" column="user_id"/>
    <result property="name" column="user_name"/>
    <!-- 一对多：一个用户多个订单 -->
    <collection property="orders" ofType="Order">
        <id property="id" column="order_id"/>
        <result property="amount" column="order_amount"/>
    </collection>
</resultMap>
```

**实际开发建议**：

1. 单表查询用自动映射（配驼峰转换），简单省事。
2. 多表关联用 `resultMap` + `<collection>`/`<association>`，结构清晰。
3. 复杂报表查询宁可用多次单表查询 + Service 层组装，也别写几百行的 `resultMap`——可维护性更重要。

### 12.6 启动初始化数据库 vs Flyway

本模块用 `schema.sql`/`data.sql` + `initialization-mode: always` 启动时建表插数据。

**适合场景**：demo、单元测试、本地开发。

**不适合生产**：因为每次启动 `DROP` 重建会丢数据，且没有版本管理。

**生产方案**：用 Flyway/Liquibase（后续 `demo-flyway` 模块），它记录每个 SQL 变更脚本版本，按顺序执行未应用的，已执行的不重复跑，支持回滚和团队协作。

### 12.7 连接池配置：HikariCP 调优要点

HikariCP 是 Spring Boot 默认连接池，性能极佳，但参数要按场景调：

| 参数 | 生产建议 | 说明 |
| --- | --- | --- |
| `maximum-pool-size` | CPU 核心数 × 2 + 1（经验值） | 不是越大越好，太大反而拖慢 DB |
| `minimum-idle` | 等于 maximum-pool-size | HikariCP 官方建议固定池大小 |
| `connection-timeout` | 30000ms | 获取连接超时，超时说明池满了 |
| `max-lifetime` | 1800000ms（30分钟） | 防止连接被 DB 端超时断开 |
| `idle-timeout` | 600000ms（10分钟） | 空闲连接回收 |

**常见坑**：

- `maximum-pool-size` 设太大（如 200），数据库连接数被打满，拖垮整个 DB。
- 不设 `max-lifetime`，连接被 MySQL 的 `wait_timeout`（默认 8 小时）断开后，池里的连接还以为是好的，下次用报错。

### 12.8 MyBatis 整合 Spring Boot 的几个关键配置

| 配置 | 作用 | 必须性 |
| --- | --- | --- |
| `@MapperScan` | 扫描 Mapper 接口 | 必须（或每个接口加 `@Mapper`） |
| `mybatis.mapper-locations` | XML 位置 | 用 XML 必须配 |
| `mybatis.type-aliases-package` | 实体短别名 | 可选，方便 XML 写短名 |
| `map-underscore-to-camel-case` | 驼峰映射 | 强烈建议开 |
| `logging.level.*.mapper=trace` | 打印 SQL | 开发调试必开 |

**常见坑汇总**：

1. XML 的 `namespace` 和接口全限定名不一致 → 找不到方法。
2. XML 的 `id` 和方法名不一致 → 找不到方法。
3. `mapper-locations` 路径写错（如 `mapper/*.xml` 漏了 `s`）→ XML 没加载。
4. `@MapperScan` 的包路径写错 → Mapper 没注册。
5. 接口方法重载 → MyBatis 报错（不支持重载）。
6. 多个 Mapper 有同名方法 → 冲突（因为靠方法名全局定位）。

---

> 📌 **学习建议**：MyBatis 是国内 Java 后端的"必修课"，建议把"Mapper 接口 + XML + 动态 SQL"这套组合练熟。重点掌握三件事：① `#{}` 防注入、② 动态 SQL 标签、③ 驼峰映射。后续 `demo-orm-mybatis-mapper-page` 会讲通用 Mapper（免写简单 CRUD），`demo-orm-mybatis-plus` 会讲 MyBatis-Plus（更强大的增强），它们都建立在原生 MyBatis 之上，所以本模块的基础一定要打牢。另外，写完 SQL 一定要开 trace 日志看实际执行的 SQL 和参数，这是排查一切 MyBatis 问题的第一步。
