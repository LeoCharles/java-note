# 14 - Spring Boot 集成 JPA 操作数据库

> 对应项目模块：`demo-orm-jpa`
> 前置知识：已学完前 13 个模块，掌握 Spring Boot 基础、配置注入、分层结构
> 学习目标：理解 JPA/Hibernate 的核心概念，掌握用 Spring Data JPA 实现单表 CRUD、分页排序、关联关系（一对多/多对多）、审计字段自动填充，能独立用 JPA 完成一个业务模块的数据库操作。

---

## 一、本模块要解决什么问题？

前面所有模块的数据都是写死在代码或配置文件里的，没有真正和数据库打交道。真实业务系统几乎都离不开数据库——用户、订单、商品都要持久化存储。本模块就是解决"Java 程序怎么操作关系型数据库"这个问题。

操作数据库的方式有很多，本模块用的是 **JPA（Java Persistence API）**，它是 Java 官方定义的 ORM（对象关系映射）标准，Spring Boot 通过 `spring-boot-starter-data-jpa` 集成了它的主流实现 **Hibernate**。

> 💡 前端类比：JPA 之于 Java，就像 **Prisma / TypeORM** 之于 Node.js。你定义一个实体类（类似 Prisma 的 `model`），框架帮你把它映射成数据库表；你调用 `repository` 的方法（类似 Prisma 的 `prisma.user.findMany()`），框架帮你生成 SQL 并执行。你操作的是 Java 对象，不用手写 SQL。

本模块的最终效果：定义 `User`、`Department` 两个实体，用 `UserDao`、`DepartmentDao` 两个接口（注意：是接口，没有实现类）完成增删改查、分页排序、多对多关联，并通过审计基类自动填充创建/更新时间。

---

## 二、先看项目结构

```
demo-orm-jpa/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/orm/jpa/
    │   ├── SpringBootDemoOrmJpaApplication.java   # 启动类
    │   ├── config/
    │   │   └── JpaConfig.java                      # JPA 手动配置类（数据源、EntityManager、事务）
    │   ├── entity/
    │   │   ├── User.java                            # 用户实体（多对多关联部门）
    │   │   ├── Department.java                     # 部门实体（一对多自关联）
    │   │   └── base/
    │   │       └── AbstractAuditModel.java         # 实体基类（主键 + 审计时间字段）
    │   └── repository/
    │       ├── UserDao.java                         # 用户 DAO（继承 JpaRepository）
    │       └── DepartmentDao.java                   # 部门 DAO（含方法名派生查询）
    └── resources/
        ├── application.yml                          # 数据源 + JPA 配置
        └── db/
            ├── schema.sql                           # 建表脚本
            └── data.sql                             # 初始数据
```

这是一个标准的 JPA 分层结构：`entity`（实体，对应表）→ `repository`（数据访问，操作实体）→ `config`（配置）。注意本模块没有 `service` 和 `controller`，因为测试类直接调用 DAO 验证效果——真实项目会在 DAO 之上加 Service 封装业务逻辑，再加 Controller 暴露接口。

---

## 三、pom.xml 依赖

```xml
<dependencies>
    <!-- 1. JPA 起步依赖（包含 Spring Data JPA + Hibernate） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>

    <!-- 2. 基础起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 3. MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- 4. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 5. 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>

    <!-- 6. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**关键依赖解读：**

- `spring-boot-starter-data-jpa`：这一个依赖传递引入了 Spring Data JPA（Repository 抽象）、Hibernate（JPA 实现）、JPA API（`javax.persistence.*`）。你不需要手写 SQL，框架全包了。
- `mysql-connector-java`：MySQL 的 JDBC 驱动，让 Java 能连上 MySQL。版本由父 POM 统一管理（8.0.21）。
- `lombok`：实体类用 `@Data`、`@Builder` 等注解生成 getter/setter/构造器，省去样板代码。

> 💡 前端类比：这像在 Node 项目里同时装 `prisma`（ORM 抽象）+ 底层数据库驱动（如 `mysql2`）。Spring Data JPA 是抽象层，Hibernate 是具体实现，MySQL 驱动是最底层的连接器。

---

## 四、配置文件 `application.yml`

```yaml
spring:
  datasource:
    jdbc-url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?useUnicode=true&characterEncoding=UTF-8&useSSL=false&autoReconnect=true&failOverReadOnly=false&serverTimezone=GMT%2B8
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
  jpa:
    show-sql: true
    hibernate:
      ddl-auto: validate
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQL57InnoDBDialect
    open-in-view: true
logging:
  level:
    com.xkcoding: debug
    org.hibernate.SQL: debug
    org.hibernate.type: trace
```

### 4.1 数据源配置（`spring.datasource`）

| 配置项 | 含义 |
| --- | --- |
| `jdbc-url` | 数据库连接地址，含库名 `spring-boot-demo`、时区 `GMT%2B8`（即 GMT+8）等参数 |
| `username` / `password` | 数据库账号密码 |
| `driver-class-name` | JDBC 驱动类，MySQL 8.x 用 `com.mysql.cj.jdbc.Driver`（注意有 `cj`） |
| `type` | 连接池实现，Spring Boot 2.x 默认用 **HikariCP**（号称最快的连接池） |
| `initialization-mode: always` | 每次启动都执行 schema.sql 和 data.sql |
| `continue-on-error: true` | 执行 SQL 出错时继续（避免重复建表报错中断启动） |
| `schema` / `data` | 指定建表脚本和初始数据脚本路径 |
| `hikari.*` | 连接池参数：最小空闲连接、最大连接数、超时时间等 |

> 💡 前端类比：连接池（HikariCP）像一个"数据库连接的缓存池"。每次查询都新建/关闭连接很慢（像前端每次请求都重新建 TCP 连接），连接池预先建好一批连接复用，大幅提升性能。`maximum-pool-size: 20` 表示最多同时 20 个连接。

### 4.2 JPA 配置（`spring.jpa`）

| 配置项 | 含义 |
| --- | --- |
| `show-sql: true` | 控制台打印 Hibernate 生成的 SQL（开发调试用） |
| `ddl-auto: validate` | 启动时校验实体类和表结构是否一致，不一致就报错（不改表） |
| `dialect` | 数据库方言，告诉 Hibernate 用 MySQL 5.7 的 SQL 语法 |
| `open-in-view: true` | 是否在 Web 视图层延迟打开 Session（后面详细讲） |

**`ddl-auto` 的几个取值（重要，新手必知）：**

| 值 | 行为 | 适用场景 |
| --- | --- | --- |
| `none` | 什么都不做 | 生产环境 |
| `validate` | 只校验，不改表 | 生产/测试（本模块用这个） |
| `update` | 表不存在就建，字段变化就更新 | 开发环境（方便但不可控） |
| `create` | 每次启动都删表重建（数据全丢！） | 仅本地测试 |
| `create-drop` | 启动建表、退出删表 | 仅单元测试 |

> ⚠️ **生产环境绝对不要用 `create` / `create-drop`，会清空数据！** 本模块用 `validate`，配合 `schema.sql` 手动建表，最安全可控。

### 4.3 日志配置

```yaml
logging:
  level:
    org.hibernate.SQL: debug      # 打印执行的 SQL 语句
    org.hibernate.type: trace     # 打印 SQL 参数的绑定值（? 占位符的实际值）
```

这两行让你在控制台看到 Hibernate 生成的完整 SQL 和参数，调试时非常有用。

---

## 五、JPA 配置类 `JpaConfig.java`

```java
@Configuration
@EnableTransactionManagement
@EnableJpaAuditing
@EnableJpaRepositories(basePackages = "com.xkcoding.orm.jpa.repository", transactionManagerRef = "jpaTransactionManager")
public class JpaConfig {
    @Bean
    @ConfigurationProperties(prefix = "spring.datasource")
    public DataSource dataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    public LocalContainerEntityManagerFactoryBean entityManagerFactory() {
        HibernateJpaVendorAdapter japVendor = new HibernateJpaVendorAdapter();
        japVendor.setGenerateDdl(false);
        LocalContainerEntityManagerFactoryBean entityManagerFactory = new LocalContainerEntityManagerFactoryBean();
        entityManagerFactory.setDataSource(dataSource());
        entityManagerFactory.setJpaVendorAdapter(japVendor);
        entityManagerFactory.setPackagesToScan("com.xkcoding.orm.jpa.entity");
        return entityManagerFactory;
    }

    @Bean
    public PlatformTransactionManager jpaTransactionManager(EntityManagerFactory entityManagerFactory) {
        JpaTransactionManager transactionManager = new JpaTransactionManager();
        transactionManager.setEntityManagerFactory(entityManagerFactory);
        return transactionManager;
    }
}
```

这是一个手动配置类，逐个看注解和 Bean：

### 5.1 类上的四个注解

- `@Configuration`：标记为配置类，里面的 `@Bean` 方法会被 Spring 调用，返回值注册为 Bean。
- `@EnableTransactionManagement`：开启注解式事务管理，让 `@Transactional` 注解生效。
- `@EnableJpaAuditing`：开启 JPA 审计功能，让实体上的 `@CreatedDate`、`@LastModifiedDate` 自动填充时间。
- `@EnableJpaRepositories`：告诉 Spring Data JPA 去哪个包扫描 Repository 接口（`com.xkcoding.orm.jpa.repository`），并指定用哪个事务管理器。

### 5.2 三个 Bean

| Bean | 作用 |
| --- | --- |
| `dataSource` | 数据源，用 `@ConfigurationProperties` 把 yml 里 `spring.datasource` 的配置绑定进来，创建 HikariCP 连接池 |
| `entityManagerFactory` | EntityManager 工厂，Hibernate 的核心，负责管理实体的生命周期；`setPackagesToScan` 指定实体类所在包 |
| `jpaTransactionManager` | 事务管理器，负责事务的开启、提交、回滚 |

> 💡 **重要说明**：其实 Spring Boot 的自动配置已经帮你做好了这些（引了 `spring-boot-starter-data-jpa` 后，数据源、EntityManager、事务管理器都会自动创建）。本模块**手动写一遍**是为了让你理解底层原理。**真实项目中，除非需要自定义（多数据源、特殊方言），否则不用写这个类**，靠自动配置即可。

---

## 六、实体基类 `AbstractAuditModel.java`

```java
@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
@Data
public abstract class AbstractAuditModel implements Serializable {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "create_time", nullable = false, updatable = false)
    @CreatedDate
    private Date createTime;

    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "last_update_time", nullable = false)
    @LastModifiedDate
    private Date lastUpdateTime;
}
```

这是一个**实体基类**，所有实体都继承它，避免每个实体都重复定义主键和时间字段。

### 6.1 关键注解

| 注解 | 含义 |
| --- | --- |
| `@MappedSuperclass` | 表示这个类本身不对应数据库表，但它的字段会被子类继承并映射到子类的表里 |
| `@EntityListeners(AuditingEntityListener.class)` | 注册审计监听器，在实体增删改时触发回调 |
| `@Id` | 标记主键 |
| `@GeneratedValue(strategy = GenerationType.IDENTITY)` | 主键自增（用数据库的 auto_increment） |
| `@Column(...)` | 映射列名、是否可空、是否可更新 |
| `@CreatedDate` | 插入时自动填充当前时间（配合 `@EnableJpaAuditing`） |
| `@LastModifiedDate` | 更新时自动填充当前时间 |
| `@Temporal(TemporalType.TIMESTAMP)` | 指定 Date 类型映射为数据库的 TIMESTAMP（JPA 2.0 必需，Hibernate 6 已废弃） |

> 💡 前端类比：这像 Prisma 里定义一个 `BaseModel`，所有 model 都继承 `id`、`createdAt`、`updatedAt`。JPA 的 `@CreatedDate` / `@LastModifiedDate` 相当于 Prisma 的 `@default(now())` 和 `@updatedAt`，自动填充时间，不用你手动 set。

---

## 七、用户实体 `User.java`

```java
@EqualsAndHashCode(callSuper = true)
@NoArgsConstructor
@AllArgsConstructor
@Data
@Builder
@Entity
@Table(name = "orm_user")
@ToString(callSuper = true)
public class User extends AbstractAuditModel {
    private String name;
    private String password;
    private String salt;
    private String email;

    @Column(name = "phone_number")
    private String phoneNumber;

    private Integer status;

    @Column(name = "last_login_time")
    private Date lastLoginTime;

    @ManyToMany(cascade = CascadeType.ALL, fetch = FetchType.EAGER)
    @JoinTable(name = "orm_user_dept",
        joinColumns = @JoinColumn(name = "user_id", referencedColumnName = "id"),
        inverseJoinColumns = @JoinColumn(name = "dept_id", referencedColumnName = "id"))
    private Collection<Department> departmentList;
}
```

### 7.1 类上的注解

- `@Entity`：标记这是一个 JPA 实体，会被 Hibernate 管理。
- `@Table(name = "orm_user")`：映射到数据库表 `orm_user`（不写则默认用类名）。
- `@Data` / `@Builder` / `@NoArgsConstructor` / `@AllArgsConstructor`：Lombok 注解，生成全套方法 + 链式构造器（`User.builder().name("x").build()`）。
- `@EqualsAndHashCode(callSuper = true)` / `@ToString(callSuper = true)`：生成方法时包含父类字段。

### 7.2 字段映射

- 默认情况下，字段名 `name` 自动映射到列 `name`。
- `phoneNumber`（驼峰）→ 用 `@Column(name = "phone_number")` 映射到下划线列名（数据库习惯用下划线，Java 习惯用驼峰）。

### 7.3 多对多关联（重点）

```java
@ManyToMany(cascade = CascadeType.ALL, fetch = FetchType.EAGER)
@JoinTable(name = "orm_user_dept",
    joinColumns = @JoinColumn(name = "user_id", referencedColumnName = "id"),
    inverseJoinColumns = @JoinColumn(name = "dept_id", referencedColumnName = "id"))
private Collection<Department> departmentList;
```

一个用户可以属于多个部门，一个部门可以有多个用户——这是多对多关系。JPA 用**中间表** `orm_user_dept` 来维护：

- `@ManyToMany`：声明多对多关系。
- `cascade = CascadeType.ALL`：级联操作，保存用户时连带保存关联的部门（实际开发慎用 ALL，后面讲）。
- `fetch = FetchType.EAGER`：立即加载，查用户时连带查出部门（N+1 问题隐患，后面讲）。
- `@JoinTable`：配置中间表。
  - `name = "orm_user_dept"`：中间表名。
  - `joinColumns`：指向自身（User）的外键 `user_id`。
  - `inverseJoinColumns`：指向对方（Department）的外键 `dept_id`。

> 💡 前端类比：多对多就像用户和角色的关系。Prisma 里你会建一个隐式中间表 `UserDepartment`。JPA 用 `@JoinTable` 显式声明中间表，原理一样。

---

## 八、部门实体 `Department.java`

```java
@Entity
@Table(name = "orm_department")
public class Department extends AbstractAuditModel {

    @Column(name = "name", columnDefinition = "varchar(255) not null")
    private String name;

    @ManyToOne(cascade = {CascadeType.REFRESH}, optional = true)
    @JoinColumn(name = "superior", referencedColumnName = "id")
    private Department superior;

    @Column(name = "levels", columnDefinition = "int not null default 0")
    private Integer levels;

    @Column(name = "order_no", columnDefinition = "int not null default 0")
    private Integer orderNo;

    @OneToMany(cascade = {CascadeType.REFRESH, CascadeType.REMOVE}, fetch = FetchType.EAGER, mappedBy = "superior")
    private Collection<Department> children;

    @ManyToMany(mappedBy = "departmentList")
    private Collection<User> userList;
}
```

部门实体演示了**一对多自关联**（树形结构）和**多对多的被维护端**：

### 8.1 一对多自关联（树形结构）

部门有上级部门，也有子部门，这是典型的树形结构：

```java
@ManyToOne(cascade = {CascadeType.REFRESH}, optional = true)
@JoinColumn(name = "superior", referencedColumnName = "id")
private Department superior;       // 上级部门（多对一）

@OneToMany(cascade = {CascadeType.REFRESH, CascadeType.REMOVE}, fetch = FetchType.EAGER, mappedBy = "superior")
private Collection<Department> children;   // 子部门集合（一对多）
```

- `@ManyToOne`：多个子部门指向一个上级，外键列是 `superior`。
- `@OneToMany` + `mappedBy = "superior"`：声明这是 `superior` 字段对应的反向关系。**`mappedBy` 表示这一方不维护外键**，外键由对方（`superior` 字段）维护。
- `CascadeType.REMOVE`：删上级部门时级联删除子部门。

### 8.2 多对多的被维护端

```java
@ManyToMany(mappedBy = "departmentList")
private Collection<User> userList;
```

User 那边用 `@JoinTable` 维护中间表，Department 这边用 `mappedBy = "departmentList"` 表示"我不维护中间表，关系由 User 那边的 `departmentList` 字段维护"。

> 💡 **关系维护端 vs 被维护端**：多对多关系中，只有"维护端"（有 `@JoinTable` 的一方）操作中间表才生效。本模块测试类里 `user.setDepartmentList(...)` 能更新中间表，但 `department.setUserList(...)` 不会生效——这就是为什么测试注释里写"关联关系由 user 维护中间表"。

---

## 九、Repository 接口（DAO 层）

### 9.1 `UserDao.java`

```java
@Repository
public interface UserDao extends JpaRepository<User, Long> {
}
```

**就这一行，你已经有了完整的单表 CRUD 能力！** 因为继承的 `JpaRepository<User, Long>` 已经定义好了这些方法（`User` 是实体类型，`Long` 是主键类型）：

| 方法 | 功能 |
| --- | --- |
| `save(entity)` | 新增或更新（有 id 就更新，没 id 就新增） |
| `findById(id)` | 按主键查，返回 `Optional<User>` |
| `findAll()` | 查全部 |
| `findAll(pageable)` | 分页查询 |
| `count()` | 计数 |
| `deleteById(id)` | 按主键删 |
| `delete(entity)` | 删除实体 |
| ... | 还有几十个 |

> 💡 前端类比：这就像 Prisma 的 `prisma.user.findUnique()` / `findMany()` / `create()`，框架帮你实现了通用 CRUD。区别是 Prisma 是实例方法，JPA 是接口方法——**你只定义接口，Spring Data JPA 在运行时自动生成实现类**（动态代理）。这是 Spring Data 最"魔法"的地方。

### 9.2 `DepartmentDao.java` —— 方法名派生查询

```java
@Repository
public interface DepartmentDao extends JpaRepository<Department, Long> {
    List<Department> findDepartmentsByLevels(Integer level);
}
```

这里多了一个方法 `findDepartmentsByLevels`，但**没有实现**！这是 Spring Data JPA 的"方法名派生查询"：只要方法名符合命名规范，框架会自动解析并生成 SQL。

- `findBy` → `SELECT ... WHERE`
- `Departments` → 实体（可省略）
- `ByLevels` → `levels = ?`

所以 `findDepartmentsByLevels(0)` 会生成 `SELECT * FROM orm_department WHERE levels = 0`。

**更多方法名派生示例：**

```java
findByName(String name)              // WHERE name = ?
findByNameAndStatus(name, status)   // WHERE name = ? AND status = ?
findByNameOrEmail(name, email)      // WHERE name = ? OR email = ?
findByStatusIn(List<Integer> list)   // WHERE status IN (...)
findByNameLike(name)                 // WHERE name LIKE ?
findByLastLoginTimeAfter(date)      // WHERE last_login_time > ?
findByOrderByNameDesc()             // ORDER BY name DESC
findTop10ByOrderByCreateTimeDesc()   // 取前10条，按创建时间降序
```

> 💡 前端类比：这像 Prisma 的 `where` 过滤，但 JPA 用方法名表达条件。简单查询用方法名很方便，复杂查询（多表关联、动态条件）后面会用 `@Query` 或 Specification。

---

## 十、测试类：验证 CRUD 与关联

### 10.1 `UserDaoTest` —— 单表 CRUD + 分页

```java
@Test
public void testSave() {
    String salt = IdUtil.fastSimpleUUID();
    User testSave3 = User.builder()
        .name("testSave3")
        .password(SecureUtil.md5("123456" + salt))
        .salt(salt)
        .email("testSave3@xkcoding.com")
        .phoneNumber("17300000003")
        .status(1)
        .lastLoginTime(new DateTime())
        .build();
    userDao.save(testSave3);    // 新增
    Assert.assertNotNull(testSave3.getId());
}
```

- 用 `User.builder()` 链式构造对象（Lombok 的 `@Builder`）。
- `userDao.save(entity)`：新增（无 id）或更新（有 id）。
- 密码用 MD5 + 盐加密（Hutool 的 `SecureUtil.md5`）。

**分页排序查询：**

```java
@Test
public void testQueryPage() {
    initData();
    Integer currentPage = 0;   // JPA 分页页码从 0 开始！
    Integer pageSize = 5;
    Sort sort = Sort.by(Sort.Direction.DESC, "id");
    PageRequest pageRequest = PageRequest.of(currentPage, pageSize, sort);
    Page<User> userPage = userDao.findAll(pageRequest);

    Assert.assertEquals(5, userPage.getSize());
    Assert.assertEquals(userDao.count(), userPage.getTotalElements());
}
```

- `PageRequest.of(page, size, sort)`：构造分页参数（页码从 **0** 开始，不是 1）。
- `Page<User>`：包含当前页数据、总条数、总页数等信息。

> ⚠️ **JPA 分页页码从 0 开始**，这是新手常踩的坑，和很多前端分页组件（从 1 开始）不一样。

### 10.2 `DepartmentDaoTest` —— 关联关系操作

```java
@Test
@Transactional
public void testSave() {
    // 1. 建树形部门结构
    Department testSave1 = Department.builder().name("testSave1").orderNo(0).levels(0).superior(null).build();
    Department testSave1_1 = Department.builder().name("testSave1_1").orderNo(0).levels(1).superior(testSave1).build();
    // ...
    departmentDao.saveAll(departmentList);

    // 2. 给用户关联部门（多对多，由 User 维护中间表）
    userDao.findById(1L).ifPresent(user -> {
        user.setDepartmentList(departmentList);
        userDao.save(user);   // 保存用户时，中间表自动更新
    });

    // 3. 清空用户的部门关联
    userDao.findById(1L).ifPresent(user -> {
        user.setDepartmentList(null);
        userDao.save(user);
    });
}
```

- `@Transactional`：标记测试方法为事务，测试结束默认回滚（不污染数据库）。
- 给 `user.setDepartmentList(...)` 后 `userDao.save(user)`，Hibernate 自动往中间表 `orm_user_dept` 插入关联记录。
- 设为 `null` 后保存，自动删除中间表关联记录。

---

## 十一、运行与验证

### 11.1 准备数据库

1. 本地启动 MySQL，创建数据库 `spring-boot-demo`：

```sql
CREATE DATABASE `spring-boot-demo` DEFAULT CHARACTER SET utf8mb4;
```

2. 修改 `application.yml` 里的 `username` / `password` 为你的 MySQL 账号。

3. 建表脚本和初始数据由 `schema.sql` / `data.sql` 在启动时自动执行（`initialization-mode: always`）。

### 11.2 运行测试

```sh
cd demo-orm-jpa
mvn test
```

观察控制台输出的 SQL 日志，验证 CRUD 和关联操作。

> 💡 本模块没有 Controller，所以不能通过 HTTP 访问，只能跑测试。真实项目会加 Controller 暴露接口。

---

## 十二、动手练习

1. **加一个查询方法**：在 `UserDao` 加 `findByName(String name)`，写测试验证按用户名查询。
2. **加一个组合查询**：加 `findByNameAndStatus(String name, Integer status)`，测试多条件查询。
3. **体验分页页码**：把 `currentPage` 从 0 改成 1，观察查到的是第几页数据。
4. **改 ddl-auto**：临时改成 `update`，删一个表字段，重启观察 Hibernate 自动加列（理解 `update` 的便利与风险）。
5. **加一个 Controller**：写一个 `UserController`，注入 `UserDao`，暴露 `GET /users` 返回所有用户，体会"接口→DAO"的链路。
6. **体验 N+1 问题**：把 `User` 的 `departmentList` 的 fetch 改成 `LAZY`，在非事务环境里访问 `user.getDepartmentList()`，观察报错（理解延迟加载和 Session 生命周期）。

---

## 十三、本模块知识点总结（结合实际开发详解）

JPA 是 Spring Boot 操作数据库的"正统"方式，理解它的核心概念和常见坑，对后续所有数据库相关模块至关重要。

### 13.1 JPA / Hibernate / Spring Data JPA 的关系

很多人把这三个概念混为一谈，实际是三层：

| 层 | 是什么 | 作用 |
| --- | --- | --- |
| **JPA** | Java 官方的 ORM 标准（规范） | 定义了一套 API 接口（`javax.persistence.*`），本身不能运行 |
| **Hibernate** | JPA 的实现（最主流） | 把 JPA 接口变成能跑的代码，负责生成 SQL、管理实体 |
| **Spring Data JPA** | Spring 对 JPA 的封装 | 提供 `Repository` 接口，让你只写接口就有 CRUD，不用写实现 |

> 💡 前端类比：JPA 像 ECMAScript 规范，Hibernate 像 V8 引擎（实现），Spring Data JPA 像封装了一层让你用得更爽的库。你写代码时用 Spring Data 的 `JpaRepository`，底层执行靠 Hibernate，标准遵循 JPA。

### 13.2 Repository 接口体系：继承哪个？

Spring Data JPA 提供了多个接口，按功能递增：

| 接口 | 能力 |
| --- | --- |
| `Repository` | 最基础，仅标记 |
| `CrudRepository` | 增删改查 |
| `PagingAndSortingRepository` | 分页 + 排序 |
| `JpaRepository` | 以上全部 + 批量操作 + 刷新（最常用） |

**实际开发建议**：直接继承 `JpaRepository`，它已经包含所有常用能力。本模块的 `UserDao`、`DepartmentDao` 就是这么做的。

### 13.3 查询方式的三种选择

**① 方法名派生查询**（本模块用的）：

```java
List<User> findByNameAndStatus(String name, Integer status);
```

- 优点：零 SQL，写接口即可。
- 缺点：方法名会很长，复杂查询表达不了。
- 适用：简单单表查询。

**② `@Query` 注解（JPQL 或原生 SQL）**：

```java
@Query("SELECT u FROM User u WHERE u.name LIKE %:keyword%")
List<User> searchByName(@Param("keyword") String keyword);

@Query(value = "SELECT * FROM orm_user WHERE status = 1", nativeQuery = true)
List<User> findActiveUsersNative();
```

- 优点：能写复杂查询，灵活。
- 适用：方法名表达不了的复杂查询。

**③ Specification / QueryDSL（动态查询）**：

```java
// 动态拼接条件（类似前端构造 where 对象）
Specification<User> spec = (root, query, cb) ->
    cb.and(cb.equal(root.get("status"), 1), cb.like(root.get("name"), "%test%"));
List<User> users = userDao.findAll(spec);
```

- 优点：条件动态拼接，最灵活。
- 适用：查询条件不固定（高级搜索）。

> 💡 前端类比：方法名查询像 Prisma 的简单 `where`，`@Query` 像写原生 SQL，Specification 像动态构造查询对象。实际项目按复杂度选，简单用方法名，中等用 `@Query`，复杂动态用 Specification。

### 13.4 关联关系：四种类型与最佳实践

JPA 用注解表达实体间关系，四种基本类型：

| 关系 | 注解 | 示例 |
| --- | --- | --- |
| 一对一 | `@OneToOne` | 用户-用户详情 |
| 一对多 / 多对一 | `@OneToMany` / `@ManyToOne` | 部门-子部门、用户-部门 |
| 多对多 | `@ManyToMany` + `@JoinTable` | 用户-角色 |

**实际开发的最佳实践与坑：**

1. **双向关系要设 `mappedBy`**：避免两边都维护外键，导致冗余 update。一方维护（有 `@JoinColumn`/`@JoinTable`），另一方用 `mappedBy` 指向维护方。本模块的 `Department.children` 用 `mappedBy = "superior"`，`Department.userList` 用 `mappedBy = "departmentList"`。
2. **级联（cascade）要克制**：`CascadeType.ALL` 看着方便，但删一个用户可能级联删掉一堆部门，风险极大。生产环境通常只用 `REFRESH`/`PERSIST`，删除级联交给数据库外键 `ON DELETE CASCADE` 或在业务层显式处理。
3. **抓取策略（fetch）默认要懒加载**：`@ManyToOne` / `@OneToOne` 默认 `EAGER`（立即加载），`@OneToMany` / `@ManyToMany` 默认 `LAZY`（延迟加载）。本模块把 `@ManyToMany` 设成了 `EAGER`，**实际不推荐**，会引发 N+1 问题（下面讲）。生产建议全用 `LAZY`，需要时用 `fetch join` 或 `@EntityGraph` 一次性查出来。
4. **双向关系要同步两边**：设 `user.setDepartmentList(depts)` 后，如果业务需要，也要 `dept.getUserList().add(user)`，否则对象内存状态不一致（虽然中间表只看维护端，但内存里两边不同步会出 bug）。

### 13.5 N+1 问题：JPA 最经典的性能坑

**什么是 N+1？** 查 10 个用户，再查每个用户的部门，本来应该 1 次查用户 + 1 次查部门（2 条 SQL），但 JPA 默认会查 1 次用户 + 10 次部门（11 条 SQL），这就是 N+1。

**怎么产生的？** `fetch = EAGER` 或在 Session 关闭后访问懒加载属性，Hibernate 只能逐条查。

**解决方案：**

1. **用 `fetch join`**：在 `@Query` 里写 `SELECT u FROM User u JOIN FETCH u.departmentList`，一条 SQL 全查出来。
2. **用 `@EntityGraph`**：声明要抓取的关联，一条 SQL 解决。
3. **用 DTO 投影**：不查实体，直接查需要的字段（`SELECT new com.xx.UserDTO(u.name, d.name) FROM ...`），避免关联加载。

> 💡 前端类比：N+1 像前端循环里发请求（`users.forEach(u => fetchDept(u.id))`），应该改成批量查询（`fetchDepts(userIds)`）。JPA 的 `fetch join` 就是批量查询的等价物。

### 13.6 事务管理：`@Transactional` 的使用

JPA 的增删改要在事务里进行。Spring 用 `@Transactional` 声明事务边界：

```java
@Service
public class UserService {
    @Transactional
    public void transferMoney(Long from, Long to, BigDecimal amount) {
        // 多个 DAO 操作在同一事务里，要么全成功，要么全回滚
        userDao.deduct(from, amount);
        userDao.add(to, amount);   // 如果这步报错，上一步的扣款也回滚
    }
}
```

**实际开发的最佳实践：**

1. **事务加在 Service 层，不加在 Controller 或 DAO**：Service 是业务逻辑的边界，一个业务方法对应一个事务。
2. **只读查询用 `@Transactional(readOnly = true)`**：告诉 Hibernate 这是只读，可以优化（不写脏检查、可走读库）。
3. **指定回滚异常**：默认只回滚 `RuntimeException`，检查异常不回滚。需要时用 `@Transactional(rollbackFor = Exception.class)`。
4. **事务传播行为**：`@Transactional(propagation = Propagation.REQUIRES_NEW)` 表示新开一个事务（不依赖外层），用于日志记录等独立操作。
5. **避免大事务**：事务里不要做 RPC 调用、文件 IO 等慢操作，会长时间占用数据库连接。

> ⚠️ **常见坑**：`@Transactional` 加在 `private` 方法上不生效（Spring AOP 基于代理，代理只能拦截 public 方法）；同类内部方法自调用也不生效（没经过代理）。

### 13.7 `open-in-view`：一个有争议的配置

```yaml
spring:
  jpa:
    open-in-view: true   # 默认 true
```

这个配置开启后，HTTP 请求处理期间一直保持 JPA 的 Session 打开，这样在 Controller/视图层也能触发懒加载（访问 `user.getDepartmentList()` 不会报错）。

**争议点：**

- 优点：开发方便，Controller 里直接访问懒加载属性不会报 `LazyInitializationException`。
- 缺点：Session 持续时间长，数据库连接占用久，高并发下连接池容易耗尽；而且把数据访问泄漏到视图层，破坏分层。

**实际开发建议**：

- 开发阶段可以开 `true`（方便）。
- 生产环境建议关掉（`false`），在 Service 层就把需要的数据查好（用 DTO 或 fetch join），Controller 只做展示。Spring Boot 2.x 起启动时如果开着 `open-in-view` 会打印警告提示你关注这个问题。

### 13.8 审计功能：自动填充时间字段

本模块的 `AbstractAuditModel` 用 `@CreatedDate` / `@LastModifiedDate` 自动填充创建/更新时间，配合 `@EnableJpaAuditing` 生效。

**实际开发价值**：几乎所有业务表都有 `create_time`、`update_time`、`create_by`、`update_by` 字段，手写 set 太繁琐。审计功能让这些字段自动填充，开发者不用关心。

**扩展：填充操作人**

```java
@CreatedBy   // 自动填充创建人（需实现 AuditorAware）
private String createBy;

@LastModifiedBy   // 自动填充更新人
private String updateBy;
```

配合一个 `AuditorAware` 实现类，从 Security 上下文取当前登录用户，就能自动记录"谁创建/修改了这条数据"。

> 💡 前端类比：这像 Prisma 的 `@default(now())` + 中间件自动注入 `userId`。JPA 的审计是后端 ORM 层的等价物，省去手动 set 样板代码。

### 13.9 JPA vs MyBatis：怎么选？

这是 Java 后端永恒的话题，本模块用 JPA，后面 `demo-orm-mybatis` 会用 MyBatis。简单对比：

| 维度 | JPA/Hibernate | MyBatis |
| --- | --- | --- |
| 理念 | 全自动 ORM，操作对象 | 半自动 ORM，手写 SQL |
| 学习成本 | 高（概念多：实体状态、级联、N+1） | 低（会写 SQL 就行） |
| 简单 CRUD | 极快（继承接口即可） | 要写 XML/注解 |
| 复杂查询 | 较难（JPQL/Specification） | 灵活（直接写 SQL） |
| 性能优化 | 难（黑盒生成 SQL） | 易（SQL 可控） |
| 数据库移植性 | 好（方言切换） | 差（SQL 绑定具体库） |

**实际开发选择建议**：

- 业务简单、CRUD 为主、追求开发速度 → **JPA**（或 MyBatis-Plus，后面讲）。
- 业务复杂、多表关联、报表统计多、SQL 需要精细优化 → **MyBatis**。
- 国内大多数中大型项目用 **MyBatis**（或 MyBatis-Plus），因为 SQL 可控、好优化。JPA 在外企和部分中小项目更流行。

> 💡 前端类比：JPA 像 Prisma（全自动，省心但黑盒），MyBatis 像手写 SQL 的 query builder（灵活可控）。两者没有绝对优劣，看团队和场景。

---

> 📌 **学习建议**：JPA 是 Spring Boot 数据库操作的"正统"方案，概念多、坑也多。作为前端转后端的工程师，建议先把"实体映射表、Repository 接口自动实现 CRUD、方法名派生查询"这三件事跑通，建立"操作对象=操作数据库"的心智模型。关联关系（一对多/多对多）和 N+1 问题先理解原理，实际项目遇到再深挖。另外，JPA 的概念（实体状态、Session、一级缓存）比较抽象，多跑几次测试、看控制台打印的 SQL，是理解它最快的方式——SQL 是 JPA 行为的"真相"，看 SQL 就知道框架帮你做了什么。
