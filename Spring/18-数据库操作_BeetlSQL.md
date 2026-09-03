# 18 - 数据库操作 BeetlSQL

> 对应项目模块：`demo-orm-beetlsql`
> 前置知识：已学完 ORM 系列（JdbcTemplate / JPA / MyBatis / 通用 Mapper / MyBatis-Plus）中的至少一篇，了解 Spring Boot 整合数据库的基本套路
> 学习目标：掌握 Spring Boot 整合 BeetlSQL 的方式，理解 BeetlSQL 的 BaseMapper、LambdaQuery、PageQuery 用法，并能横向对比各 ORM 框架的取舍。

---

## 一、本模块要解决什么问题？

前面我们已经用 JdbcTemplate、JPA、MyBatis、MyBatis-Plus 四种方式操作过同一张 `orm_user` 表。本模块引入第五种 ORM 方案——**BeetlSQL**。

BeetlSQL 是国产 ORM 框架（作者闲.大赋），主打"以文档数据库的方式操作关系型数据库"——既能像 MyBatis 一样写 SQL，也能像 JPA 一样用对象操作，还内置了 Markdown 风格的 SQL 模板（`.md` 文件）。

**为什么还要学它？**

1. **拓宽视野**：了解不同 ORM 的设计哲学，面试时能讲出"为什么选 A 不选 B"。
2. **国产框架生态**：国内不少老项目用了 BeetlSQL，维护时需要看懂。
3. **对比学习**：通过和前几个 ORM 对比，能更深刻理解 ORM 的核心概念（映射、主键、分页、命名转换）。

> 💡 前端类比：这就像你已经用过 Prisma、TypeORM、Knex、Sequelize 四种 ORM，再看第五种——核心概念都一样（实体映射、查询构建器、分页），只是 API 风格不同。

**本模块的最终效果**：通过 `UserDao` 接口（继承 `BaseMapper<User>`）实现增删改查、批量插入、分页查询，并用单元测试验证。

---

## 二、项目结构

```
demo-orm-beetlsql/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/orm/beetlsql/
    │   ├── SpringBootDemoOrmBeetlsqlApplication.java  # 启动类
    │   ├── config/
    │   │   └── BeetlConfig.java                        # 数据源手动配置（关键！）
    │   ├── entity/
    │   │   └── User.java                              # 实体类
    │   ├── dao/
    │   │   └── UserDao.java                           # DAO 接口（继承 BaseMapper）
    │   └── service/
    │       ├── UserService.java                        # Service 接口
    │       └── impl/UserServiceImpl.java              # Service 实现
    └── resources/
        ├── application.yml                            # 配置
        └── db/
            ├── schema.sql                             # 建表脚本
            └── data.sql                               # 初始数据
```

注意：本模块**没有 Controller**，所有操作通过单元测试验证。这是 ORM 演示模块的常见做法——专注数据层，不引入 Web 层干扰。

---

## 三、逐行拆解 pom.xml

```xml
<properties>
    <ibeetl.version>1.1.68.RELEASE</ibeetl.version>
</properties>

<dependencies>
    <!-- 1. 基础起步依赖（不含 Web） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. JDBC 起步依赖（提供数据源、JdbcTemplate） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-jdbc</artifactId>
    </dependency>

    <!-- 3. BeetlSQL 起步依赖 -->
    <dependency>
        <groupId>com.ibeetl</groupId>
        <artifactId>beetl-framework-starter</artifactId>
        <version>${ibeetl.version}</version>
    </dependency>

    <!-- 4. MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- 5. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 6. 测试、Hutool、Guava -->
    ...
</dependencies>
```

**关键点：**

- 用的是 `spring-boot-starter`（不带 web），不是 `spring-boot-starter-web`，因为本模块不暴露 HTTP 接口，只跑测试。
- `beetl-framework-starter` 是 Beetl 官方提供的 Spring Boot 集成包，**注意它没有进入 Spring Boot 的 BOM 管理**，所以这里必须手写版本号 `<version>${ibeetl.version}</version>`。这和前面用 MyBatis-Plus（也不在 BOM 里）是一样的情况。
- `spring-boot-starter-jdbc` 提供 HikariCP 数据源连接池。

---

## 四、配置文件 application.yml（含一个大坑）

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?useUnicode=true&characterEncoding=UTF-8&useSSL=false&autoReconnect=true&failOverReadOnly=false&serverTimezone=GMT%2B8
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
#### beetlsql starter不能开启下面选项
#    type: com.zaxxer.hikari.HikariDataSource
#    initialization-mode: always
#    continue-on-error: true
#    schema:
#    - "classpath:db/schema.sql"
#    data:
#    - "classpath:db/data.sql"
#    hikari:
#      ...
logging:
  level:
    com.xkcoding: debug
    com.xkcoding.orm.beetlsql: trace
beetl:
  enabled: false
beetlsql:
  enabled: true
  sqlPath: /sql
  daoSuffix: Dao
  basePackage: com.xkcoding.orm.beetlsql.dao
  dbStyle: org.beetl.sql.core.db.MySqlStyle
  nameConversion: org.beetl.sql.core.UnderlinedNameConversion
beet-beetlsql:
  dev: true
```

### 4.1 被注释掉的数据源配置—— BeetlSQL 的"大坑"

注意 `spring.datasource` 下只配了 4 项基础信息（url/username/password/driver），而 `type`、`initialization-mode`、`schema`、`data`、`hikari` 全被注释掉了，注释明确写着"**beetlsql starter 不能开启下面选项**"。

**为什么？** 因为 `beetl-framework-starter` 这个起步依赖和 Spring Boot 原生的数据源自动配置有冲突——如果开启 `type: com.zaxxer.hikari.HikariDataSource` 让 Spring Boot 自动创建 HikariDataSource，BeetlSQL 启动时会拿不到数据源而报错。所以必须**手动用 JavaConfig 配置数据源**（见下一节 `BeetlConfig`）。

这也是 README 里说的"集成过程不是十分顺利，没有其他的 orm 框架集成的便捷"——其他 ORM（JPA/MyBatis/MyBatis-Plus）都能直接用 Spring Boot 自动配置的数据源，唯独 BeetlSQL 要手动配。

**副作用**：因为不能用 `schema`/`data` 自动执行建表和初始化脚本，所以 `db/schema.sql` 和 `db/data.sql` 需要**手动在数据库里执行**。

### 4.2 BeetlSQL 专属配置

```yaml
beetl:
  enabled: false          # 关闭 Beetl 模板引擎（BeetlSQL 的 SQL 模板用的是另一套，不是 Beetl）
beetlsql:
  enabled: true           # 开启 BeetlSQL
  sqlPath: /sql           # SQL 模板文件根路径（classpath 下的 /sql 目录）
  daoSuffix: Dao          # DAO 接口后缀，用于自动扫描
  basePackage: com.xkcoding.orm.beetlsql.dao   # DAO 接口所在包
  dbStyle: org.beetl.sql.core.db.MySqlStyle    # 数据库方言（MySQL）
  nameConversion: org.beetl.sql.core.UnderlinedNameConversion  # 命名转换策略
beet-beetlsql:
  dev: true               # 开发模式，SQL 模板修改后热加载
```

**重点理解 `nameConversion`（命名转换）**：Java 实体类的字段是驼峰（`phoneNumber`），数据库表字段是下划线（`phone_number`）。`UnderlinedNameConversion` 负责两者互转——这和 MyBatis-Plus 的 `map-underscore-to-camel-case`、JPA 的命名策略是同一回事。

---

## 五、BeetlConfig：手动配置数据源（本模块的关键）

```java
@Configuration
public class BeetlConfig {

    /**
     * Beetl需要显示的配置数据源，方可启动项目，大坑，切记！
     */
    @Bean(name = "datasource")
    public DataSource getDataSource(Environment env) {
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setDriverClassName(env.getProperty("spring.datasource.driver-class-name"));
        dataSource.setJdbcUrl(env.getProperty("spring.datasource.url"));
        dataSource.setUsername(env.getProperty("spring.datasource.username"));
        dataSource.setPassword(env.getProperty("spring.datasource.password"));
        return dataSource;
    }
}
```

**逐行解读：**

- `@Configuration`：标记为配置类，里面的 `@Bean` 方法会被 Spring 调用，返回值注册为 Bean。
- `@Bean(name = "datasource")`：手动创建一个 `HikariDataSource`，Bean 名字叫 `datasource`。BeetlSQL 启动时会按这个名字找到数据源。
- `Environment env`：Spring 的环境抽象，能读取 `application.yml` 里的配置值。这里用 `env.getProperty("spring.datasource.url")` 读取 yml 配置，再手动 set 到 HikariDataSource 上。

**为什么不直接 `@ConfigurationProperties` 绑定？** 因为 BeetlSQL 要的是一个"独立创建"的 DataSource Bean，而不是 Spring Boot 自动配置的那个。手动 `new HikariDataSource()` 并注册，绕开了自动配置的冲突。

> 💡 前端类比：这就像某个第三方库不兼容 Vite 的自动 alias 解析，你只能手动 `resolve.alias` 显式配置。BeetlSQL 的 starter 和 Spring Boot 自动配置的"不兼容"，就是这个手动配置的根本原因。

---

## 六、实体类 User

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Table(name = "orm_user")
public class User implements Serializable {
    private static final long serialVersionUID = -1840831686851699943L;

    private Long id;            // 主键
    private String name;        // 用户名
    private String password;    // 加密密码
    private String salt;        // 盐
    private String email;       // 邮箱
    private String phoneNumber;// 手机号（驼峰，对应 phone_number）
    private Integer status;     // 状态
    private Date createTime;    // 创建时间
    private Date lastLoginTime; // 上次登录时间
    private Date lastUpdateTime;// 更新时间
}
```

**注解解读：**

| 注解 | 作用 | 来源 |
| --- | --- | --- |
| `@Data` | getter/setter/toString 等 | Lombok |
| `@NoArgsConstructor` | 无参构造器 | Lombok |
| `@AllArgsConstructor` | 全参构造器 | Lombok |
| `@Builder` | 链式构造器 `User.builder().name("x").build()` | Lombok |
| `@Table(name = "orm_user")` | 指定对应的数据库表名 | BeetlSQL |

- `serialVersionUID`：序列化版本号，实现 `Serializable` 是为了支持缓存、分布式传输等场景。
- 字段名 `phoneNumber`（驼峰）通过 `UnderlinedNameConversion` 自动映射到表的 `phone_number`（下划线）。

**对比其他 ORM 的实体注解：**

| ORM | 表映射注解 |
| --- | --- |
| JPA | `@Entity` + `@Table(name="orm_user")` |
| MyBatis-Plus | `@TableName("orm_user")` |
| BeetlSQL | `@Table(name="orm_user")` |

概念完全一样，只是注解全限定名不同。

---

## 七、DAO 层：UserDao（继承 BaseMapper）

```java
@Component
public interface UserDao extends BaseMapper<User> {
}
```

**就这一行，已经具备了完整的单表 CRUD 能力。** 这和 MyBatis-Plus 的 `extends BaseMapper<T>` 如出一辙。

`BaseMapper<User>` 提供的方法（本模块用到的）：

| 方法 | 作用 |
| --- | --- |
| `insert(user, true)` | 插入，第二个参数 true 表示回填自增主键 |
| `insertBatch(users)` | 批量插入 |
| `deleteById(id)` | 根据主键删除 |
| `updateTemplateById(user)` | 模板更新（只更新非 null 字段） |
| `single(id)` | 根据主键查询单条 |
| `all()` | 查询全部 |
| `createLambdaQuery()` | 创建 Lambda 查询器（链式查询） |

> 💡 前端类比：这就像 Prisma 的 `prisma.user.create()` / `.findMany()` / `.delete()`——框架替你生成了基础 CRUD，你只写业务特有的查询。

**`@Component` 的作用**：让 Spring 扫描到这个接口。BeetlSQL 会为它生成动态代理实现类（类似 MyBatis 的 Mapper 动态代理）。

---

## 八、Service 层

### 8.1 接口 UserService

定义了 7 个方法：新增、批量新增、删除、更新、查单条、查全部、分页查询。标准的服务接口设计。

### 8.2 实现 UserServiceImpl

```java
@Service
@Slf4j
public class UserServiceImpl implements UserService {

    private final UserDao userDao;

    @Autowired
    public UserServiceImpl(UserDao userDao) {
        this.userDao = userDao;
    }

    @Override
    public User saveUser(User user) {
        userDao.insert(user, true);   // true = 回填主键
        return user;
    }

    @Override
    public void saveUserList(List<User> users) {
        userDao.insertBatch(users);
    }

    @Override
    public void deleteUser(Long id) {
        userDao.deleteById(id);
    }

    @Override
    public User updateUser(User user) {
        if (ObjectUtil.isNull(user)) {
            throw new RuntimeException("用户id不能为null");
        }
        userDao.updateTemplateById(user);   // 模板更新：只更新非 null 字段
        return userDao.single(user.getId());
    }

    @Override
    public User getUser(Long id) {
        return userDao.single(id);
    }

    @Override
    public List<User> getUserList() {
        return userDao.all();
    }

    @Override
    public PageQuery<User> getUserByPage(Integer currentPage, Integer pageSize) {
        return userDao.createLambdaQuery().page(currentPage, pageSize);
    }
}
```

**重点方法解读：**

1. **构造器注入**：和前几个模块一致，`final` 字段 + 构造器注入，Spring 官方推荐写法。
2. **`insert(user, true)`**：第二个参数 `true` 表示插入后回填自增主键到 `user.id`，这样调用方能拿到新插入的 id。
3. **`updateTemplateById(user)`**："模板更新"——只更新对象中非 null 的字段。比如你只想改名字，就只 set name，其他字段保持 null，SQL 只会 `SET name=?` 而不会把其他字段覆盖成 null。这和 MyBatis-Plus 的 `updateById` 配合"忽略 null"策略、JPA 的 `@DynamicUpdate` 是同一个理念。
4. **`createLambdaQuery().page(currentPage, pageSize)`**：Lambda 链式查询 + 分页。`createLambdaQuery()` 返回一个查询构建器，可以 `.andEq(User::getName, "x").page(1, 10)` 链式拼接条件和分页。`PageQuery` 封装了当前页数据、总条数、总页数。

> 💡 前端类比：`createLambdaQuery()` 就像 Prisma 的 `prisma.user.findMany({ where: {...}, skip, take })`——链式构建查询条件，最后执行。`Lambda` 的好处是 `User::getName` 是类型安全的，字段名写错编译就报错，不像字符串 `"name"` 写错了运行时才发现。

---

## 九、SQL 脚本

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
  `status` INT(2) NOT NULL DEFAULT 1 COMMENT '状态',
  `create_time` DATETIME NOT NULL DEFAULT NOW() COMMENT '创建时间',
  `last_login_time` DATETIME DEFAULT NULL COMMENT '上次登录时间',
  `last_update_time` DATETIME NOT NULL DEFAULT NOW() COMMENT '上次更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Spring Boot Demo Orm 系列示例表';
```

`db/data.sql`（初始数据）：

```sql
INSERT INTO `orm_user`(`id`,`name`,`password`,`salt`,`email`,`phone_number`) VALUES (1, 'user_1', 'ff342e862e7c3285cdc07e56d6b8973b', '412365a109674b2dbb1981ed561a4c70', 'user1@xkcoding.com', '17300000001');
INSERT INTO `orm_user`(`id`,`name`,`password`,`salt`,`email`,`phone_number`) VALUES (2, 'user_2', '6c6bf02c8d5d3d128f34b1700cb1e32c', 'fcbdd0e8a9404a5585ea4e01d0e4d7a0', 'user2@xkcoding.com', '17300000002');
```

**注意**：因为 BeetlSQL 的数据源配置坑（见第四节），这两个脚本**不会自动执行**，需要你手动在 MySQL 里跑一遍。这也是 README 反复强调的点。

---

## 十、测试类 UserServiceTest

测试类继承自 `SpringBootDemoOrmBeetlsqlApplicationTests`（基础测试类，加了 `@SpringBootTest`），用 `@Autowired` 注入 `UserService`，对每个方法做断言验证。

典型测试（新增）：

```java
@Test
public void saveUser() {
    String salt = IdUtil.fastSimpleUUID();
    User user = User.builder()
        .name("testSave3")
        .password(SecureUtil.md5("123456" + salt))   // MD5 加盐
        .salt(salt)
        .email("testSave3@xkcoding.com")
        .phoneNumber("17300000003")
        .status(1)
        .lastLoginTime(new DateTime())
        .createTime(new DateTime())
        .lastUpdateTime(new DateTime())
        .build();

    user = userService.saveUser(user);
    Assert.assertTrue(ObjectUtil.isNotNull(user.getId()));   // 验证主键回填
}
```

**值得学的点：**

1. **密码加盐 MD5**：`SecureUtil.md5("123456" + salt)`——明文密码 + 随机盐再 MD5，比直接 MD5 安全（防彩虹表）。Hutool 的 `SecureUtil` 和 `IdUtil` 在这里很方便。
2. **`@Builder` 链式构造**：`User.builder().name("x").build()` 比一连串 `setXxx` 清晰，是 Lombok 的常用技巧。
3. **分页测试**：`getUserByPage(1, 5)` 返回 `PageQuery`，断言 `list.size()==5` 且 `totalRow==全部条数`——验证分页和总数统计都正确。

---

## 十一、运行与验证

### 11.1 准备数据库

1. 本机装 MySQL，创建数据库 `spring-boot-demo`。
2. 手动执行 `db/schema.sql` 建表。
3. 手动执行 `db/data.sql` 插入初始数据。
4. 修改 `application.yml` 的数据库连接信息（账号密码）。

### 11.2 运行测试

在 IDE 里右键运行 `UserServiceTest`，或在命令行执行：

```sh
mvn test -pl demo-orm-beetlsql
```

所有测试通过即说明 BeetlSQL 整合成功。

---

## 十二、动手练习

1. **加一个条件查询**：在 `UserServiceImpl` 加一个 `findByName(String name)` 方法，用 `userDao.createLambdaQuery().andEq(User::getName, name).single()` 实现。
2. **体验模板更新**：新建一个只 set 了 `email` 的 User（id 给定），调用 `updateTemplateById`，观察 SQL 日志是否只更新了 email 字段（开启 `logging.level: trace` 查看）。
3. **写一个 SQL 模板**：在 `resources/sql/user.md` 里写一个 BeetlSQL 的 markdown SQL 模板，在 `UserDao` 里用 `@Sql` 注解或方法名约定调用，体验 BeetlSQL 的 SQL 文件管理。
4. **对比 MyBatis-Plus**：把本模块的 `UserDao` 和 demo-orm-mybatis-plus 的 `UserMapper` 对比，列出两者 BaseMapper 提供的方法差异。
5. **改命名转换**：把 `nameConversion` 换成别的实现（如 `DefaultNameConversion`），观察驼峰字段是否还能正确映射，体会命名转换的作用。

---

## 十三、本模块知识点总结（结合实际开发详解）

BeetlSQL 是 ORM 系列的最后一个，学完它你应该能对"Spring Boot 如何整合一个 ORM"形成完整方法论。下面把核心知识点结合实际开发讲透。

### 13.1 BeetlSQL 的定位与设计哲学

**BeetlSQL 是什么？** 它是介于 JPA（全自动）和 MyBatis（半自动）之间的 ORM——既提供 BaseMapper 的零 SQL 单表操作，又支持 Markdown 风格的 SQL 模板文件，还能用 Lambda 链式查询。

**和其他 ORM 的定位对比：**

| ORM | 自动化程度 | SQL 控制力 | 典型场景 |
| --- | --- | --- | --- |
| JPA/Hibernate | 全自动（HQL/方法名） | 弱 | 简单 CRUD、快速开发 |
| MyBatis-Plus | 高（BaseMapper + 条件构造器） | 中（可写 XML） | 主流业务开发 |
| BeetlSQL | 中高（BaseMapper + md 模板） | 中高 | 喜欢模板管理 SQL 的团队 |
| MyBatis | 低（手写 XML） | 强 | 复杂 SQL、性能极致优化 |
| JdbcTemplate | 最低（纯 SQL） | 最强 | 极致控制、报表 |

**实际开发怎么选？** 国内主流是 MyBatis / MyBatis-Plus，JPA 在外企和部分中台项目用得多，BeetlSQL 相对小众。学 BeetlSQL 的价值在于"对比"——理解不同设计哲学，面试时能讲清楚取舍。

**常见坑：** 不要因为某个框架"功能多"就盲目选。BeetlSQL 功能全，但生态、社区、文档量都不如 MyBatis-Plus，遇到问题排查成本更高。选型要综合考虑团队能力和生态。

### 13.2 BeetlSQL 整合的"数据源大坑"及启示

本模块最值得记住的就是 `BeetlConfig` 里那句注释"**Beetl 需要显式配置数据源，方可启动项目，大坑，切记！**"

**为什么会有这个坑？** `beetl-framework-starter` 的自动配置和 Spring Boot 原生的 `DataSourceAutoConfiguration` 在某些版本下会冲突——Spring Boot 自动创建的 HikariDataSource，BeetlSQL 拿不到或拿到的不对，导致启动失败。解法是手动 `new HikariDataSource()` 并注册成名为 `datasource` 的 Bean。

**实际开发的启示：**

1. **第三方 starter 的兼容性不保证**：Spring Boot 官方能保证自家 starter 互相兼容，但第三方 starter（尤其小众的）可能和自动配置打架。遇到"明明配置对了却启动失败"，要怀疑自动配置冲突。
2. **手动配置是终极退路**：当自动配置出问题，回退到 `@Configuration` + `@Bean` 手动创建，是最可靠的解法。这也是为什么 Spring Boot 老手都懂"自动配置是方便，但要知道怎么手动配"。
3. **看官方 issue 和 README**：本模块 README 明确写了"集成过程不是十分顺利"——用第三方框架前先看它的已知问题，能少踩很多坑。

**常见坑：** 升级 BeetlSQL 版本后，原来要手动配数据源的坑可能修复了（也可能引入新坑）。所以升级时要在测试环境充分验证，别直接上生产。

### 13.3 BaseMapper 模式：ORM 框架的通用设计

BeetlSQL、MyBatis-Plus、JPA 的 Repository 都用了同一个设计——**给一个泛型基类，子类继承即获得单表 CRUD**。这不是巧合，而是 ORM 框架的最佳实践：

```java
// BeetlSQL
public interface UserDao extends BaseMapper<User> {}

// MyBatis-Plus
public interface UserMapper extends BaseMapper<User> {}

// JPA
public interface UserRepository extends JpaRepository<User, Long> {}
```

**为什么这个设计好？**

1. **零样板**：单表 CRUD 不用写任何方法，继承即用。
2. **类型安全**：泛型 `<User>` 保证编译期类型检查。
3. **可扩展**：基类方法不够时，在子接口加自定义方法。

**实际开发最佳实践：**

- 单表操作用 BaseMapper 提供的方法，不要手写 SQL。
- 多表关联、复杂统计，再写自定义方法（BeetlSQL 用 md 模板，MyBatis 用 XML，JPA 用 `@Query`）。
- 不要为了"统一"把所有查询都塞进 BaseMapper 的扩展方法，那样接口会膨胀难维护。

**常见坑：** 误以为 BaseMapper 是"万能"的——它只擅长单表。多表 join 用它会很别扭，这时候应该用框架推荐的 SQL 模板/XML/原生 SQL。

### 13.4 命名转换：驼峰与下划线的桥梁

本模块配了 `UnderlinedNameConversion`，把 Java 的 `phoneNumber` 映射到数据库的 `phone_number`。这是所有 ORM 都要解决的问题：

| ORM | 命名转换配置 |
| --- | --- |
| BeetlSQL | `nameConversion: UnderlinedNameConversion` |
| MyBatis | `map-underscore-to-camel-case: true` |
| MyBatis-Plus | `map-underscore-to-camel-case: true` |
| JPA | `spring.jpa.hibernate.naming.physical-strategy` |

**为什么需要？** Java 社区习惯驼峰命名（`phoneNumber`），SQL 社区习惯下划线命名（`phone_number`），两边不一致，ORM 框架要做转换。

**实际开发的坑：**

1. **转换没生效**：配错了转换策略，导致字段映射不上，查出来是 null。排查时开 SQL 日志，看生成的 SQL 字段名。
2. **特殊字段名**：有些字段既不是驼峰也不是下划线（如数据库字段叫 `phoneNo`），转换策略可能处理不了，要用 `@Column`/`@TableField` 显式指定。
3. **数据库表名大小写**：Linux 下 MySQL 默认区分表名大小写，Windows 不区分。跨平台部署时表名大小写不一致会踩坑。

### 13.5 模板更新与 Lambda 查询：BeetlSQL 的两个亮点

**模板更新 `updateTemplateById`**：只更新非 null 字段，避免把不想改的字段覆盖成 null。

实际场景：前端只传了要改的字段（如只改邮箱），后端用模板更新，SQL 只 `SET email=?`，不会动 name、password 等。这比"全字段更新"安全得多。

**Lambda 查询 `createLambdaQuery()`**：用方法引用（`User::getName`）代替字符串字段名，类型安全。

```java
// Lambda 写法（类型安全，重构友好）
userDao.createLambdaQuery().andEq(User::getName, "x").page(1, 10);

// 字符串写法（不安全，字段名写错运行时才发现）
userDao.createQuery().andEq("name", "x").page(1, 10);
```

**实际开发最佳实践：** 优先用 Lambda/方法引用版本的查询 API。当 IDE 重命名字段时，Lambda 写法会跟着改，字符串写法不会——后者是 bug 温床。

**常见坑：** Lambda 查询在复杂多表 join 时力不从心，硬写会很别扭。这时候回退到 SQL 模板/原生 SQL，不要用 Lambda 硬撑。

### 13.6 ORM 框架整合的方法论（通用）

学完五个 ORM 模块，你应该总结出 Spring Boot 整合任何 ORM 的固定套路：

1. **引依赖**：ORM 的 starter + 数据库驱动 + 连接池（一般 starter 自带 HikariCP）。
2. **配数据源**：`spring.datasource` 四件套（url/username/password/driver）。
3. **配 ORM 专属项**：方言、命名转换、SQL 路径、扫描包等。
4. **写实体**：`@Table`/`@TableName`/`@Entity` + 字段映射。
5. **写 DAO**：继承 BaseMapper/Repository，获得 CRUD。
6. **写 Service**：组合 DAO，加业务逻辑，构造器注入。
7. **写测试**：验证 CRUD 和分页。

**遇到问题的排查顺序：**

1. 数据源连不上？→ 检查 url/账号密码/数据库是否启动。
2. 实体映射不上？→ 检查 `@Table` 表名、命名转换、字段注解。
3. DAO 注入失败？→ 检查包扫描（`@MapperScan`/`basePackage`）。
4. SQL 报错？→ 开 trace 日志看实际 SQL，对照数据库手动执行。

这个方法论适用于任何 ORM，是本系列 ORM 模块最核心的收获。

---

> 📌 **学习建议**：BeetlSQL 本身用不用看团队，但它作为 ORM 系列的收尾很有价值——它让你看到"BaseMapper + Lambda 查询 + SQL 模板"这种设计的另一种实现。学完五个 ORM，建议你停下来做个横向对比表（CRUD 写法、分页方式、命名转换、复杂 SQL 支持、生态），这个表比任何单篇文档都更能巩固理解。实际工作中，MyBatis-Plus 是国内最稳的选择，但知道 alternatives 能让你在技术选型时有底气。
