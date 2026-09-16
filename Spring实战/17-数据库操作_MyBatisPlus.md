# 17 - 数据库操作：MyBatis-Plus

> 对应项目模块：`demo-orm-mybatis-plus`
> 前置知识：已学完 `15-数据库操作_MyBatis`，理解 MyBatis 的 Mapper 接口 + XML/注解 SQL 的基本用法
> 学习目标：理解 MyBatis-Plus 在 MyBatis 之上做了哪些增强，掌握 BaseMapper、IService、条件构造器、自动填充、分页插件、ActiveRecord 模式，能独立用 MyBatis-Plus 完成单表 CRUD。

---

## 一、本模块要解决什么问题？

上一篇 `15-数据库操作_MyBatis` 里，我们写一个用户表的 CRUD 要：定义 Mapper 接口 → 写 `@Insert/@Update/@Select/@Delete` 注解或 XML SQL → 在 Service 里调 Mapper。每个表都要重复写一遍"增删改查"的样板 SQL，枯燥且容易出错。

**MyBatis-Plus（简称 MP）** 就是为了消灭这些样板代码而生的。它是一个 MyBatis 的增强工具，核心承诺是：**只做增强不做改变，引入它不会对现有工程产生任何影响**。简单说：

- MyBatis 能做的，MP 都能做（完全兼容）
- MyBatis 里要手写的单表 CRUD，MP 内置好了，继承一个接口就白嫖
- 还附带条件构造器、分页插件、代码生成、自动填充、逻辑删除、乐观锁等一揽子增强

> 💡 前端类比：MP 之于 MyBatis，有点像 Prisma 之于原生 SQL —— 你不用手写 `SELECT * FROM user WHERE id = ?`，调一个 `getById(1L)` 就行。但 MP 不像 Prisma 那样自己接管数据库 schema，它依然跑在 MyBatis 之上，SQL 仍可见可控。

本模块演示两种操作姿势：
1. **Mapper/Service 模式**（主流）：`UserMapper extends BaseMapper<User>` + `UserService extends IService<User>`
2. **ActiveRecord 模式**（可选）：`Role extends Model<Role>`，实体对象自己就能 `insert()/updateById()/selectById()`

---

## 二、项目结构

```
demo-orm-mybatis-plus/
├── pom.xml
└── src/
    ├── main/java/com/xkcoding/orm/mybatis/plus/
    │   ├── SpringBootDemoOrmMybatisPlusApplication.java   # 启动类
    │   ├── config/
    │   │   ├── MybatisPlusConfig.java                     # MP 配置（分页/性能插件 + @MapperScan）
    │   │   └── CommonFieldHandler.java                    # 自动填充处理器
    │   ├── entity/
    │   │   ├── User.java                                  # 普通实体（Mapper 模式）
    │   │   └── Role.java                                  # ActiveRecord 实体
    │   ├── mapper/
    │   │   ├── UserMapper.java                            # extends BaseMapper<User>
    │   │   └── RoleMapper.java                            # extends BaseMapper<Role>
    │   └── service/
    │       ├── UserService.java                           # extends IService<User>
    │       └── impl/UserServiceImpl.java                  # extends ServiceImpl<UserMapper,User>
    └── main/resources/
        ├── application.yml                                # 数据源 + mybatis-plus 配置
        └── db/
            ├── schema.sql                                 # 建表
            └── data.sql                                  # 初始数据
    └── test/java/.../
        ├── SpringBootDemoOrmMybatisPlusApplicationTests.java  # 测试基类
        ├── service/UserServiceTest.java                     # Service 模式 CRUD 测试
        └── activerecord/ActiveRecordTest.java               # ActiveRecord 测试
```

注意：本模块**没有 Controller**，所有操作通过**单元测试**演示。这是因为 MP 的能力集中在数据层，用测试验证最直接。真实项目里你会在 Controller → Service → Mapper 的链路里调用它们。

---

## 三、逐行拆解 pom.xml

```xml
<properties>
    <mybatis.plus.version>3.1.0</mybatis.plus.version>
</properties>

<dependencies>
    <!-- 1. Spring Boot 基础起步依赖（注意：不是 starter-web，本模块无 Web 层） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. MyBatis-Plus 起步依赖（核心） -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-boot-starter</artifactId>
        <version>${mybatis.plus.version}</version>
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

    <!-- 5. Hutool 工具类（测试里用 IdUtil 生成 UUID、SecureUtil.md5 加密） -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 6. Guava（测试里用 Lists.newArrayList） -->
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>

    <!-- 7. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**关键点：**

1. **`mybatis-plus-boot-starter` 已经包含了 MyBatis**：引入 MP 后不要再单独引 `mybatis-spring-boot-starter`，否则会冲突。MP 的 starter 内部把 MyBatis、MyBatis-Spring 都带进来了。
2. **本模块用 `spring-boot-starter` 而非 `spring-boot-starter-web`**：因为只演示数据层，没有 HTTP 接口。如果你要做 Web 接口，换成 `starter-web` 即可。
3. **版本号 `3.1.0`**：MP 版本和 Spring Boot 版本有对应关系，本工程 Spring Boot 2.1.0 配 MP 3.1.0。升级时要注意兼容矩阵（MP 3.x 对应 Spring Boot 2.x；MP 3.5+ 才较好支持 Spring Boot 2.5+）。

> 💡 前端类比：MP 的 starter 像一个"全家桶"npm 包，装它就等于装了 MyBatis + 整合包 + 增强功能，不要重复装底层依赖。

---

## 四、配置文件 application.yml

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
    com.xkcoding.orm.mybatis.plus.mapper: trace   # 打印 Mapper 执行的 SQL
mybatis-plus:
  mapper-locations: classpath:mappers/*.xml       # 自定义 SQL 的 XML 位置
  typeAliasesPackage: com.xkcoding.orm.mybatis.plus.entity  # 实体别名包
  global-config:
    db-config:
      id-type: auto              # 主键策略：数据库自增
      field-strategy: not_empty  # 字段策略：非空判断
      table-underline: true      # 驼峰转下划线
      db-type: mysql             # 数据库类型
    refresh: true                # 热加载 Mapper（调试用）
  configuration:
    map-underscore-to-camel-case: true   # 下划线转驼峰
    cache-enabled: true                 # 开启二级缓存
```

### 4.1 数据源 + 自动建表

- `type: com.zaxxer.hikari.HikariDataSource`：指定用 HikariCP 连接池（Spring Boot 2.x 默认就是它，可省略）。
- `initialization-mode: always` + `schema`/`data`：**每次启动都执行建表和初始数据脚本**。`continue-on-error: true` 表示脚本出错也继续（方便演示）。生产环境一般不用这个，改用 Flyway（见 `demo-flyway` 模块）。
- `hikari.*`：连接池调优参数。`maximum-pool-size: 20` 最大连接数，`connection-timeout: 30000` 获取连接超时 30 秒。

### 4.2 mybatis-plus 专属配置

| 配置项 | 作用 |
| --- | --- |
| `mapper-locations` | 自定义 SQL 的 XML 文件位置（MP 内置 CRUD 不需要 XML） |
| `typeAliasesPackage` | 实体类包，配了后 XML 里可以用类名简写（如 `parameterType="User"`） |
| `global-config.db-config.id-type` | 主键策略：`auto`(自增)/`input`(手动输入)/`id_worker`(雪花ID)/`uuid` |
| `global-config.db-config.field-strategy` | 字段插入/更新策略：`not_empty` 表示空值字段不参与 SQL |
| `global-config.db-config.table-underline` | 驼峰转下划线：Java `createTime` ↔ DB `create_time` |
| `configuration.map-underscore-to-camel-case` | 结果集下划线转驼峰 |
| `configuration.cache-enabled` | 开启 MyBatis 二级缓存 |

> 💡 前端类比：`logging.level.com.xkcoding.orm.mybatis.plus.mapper: trace` 像开了 SQL 的 console.log，能把每条执行的 SQL、参数、结果打出来，调试必备。

---

## 五、核心：实体类 User

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@TableName("orm_user")
public class User implements Serializable {
    private static final long serialVersionUID = -1840831686851699943L;

    private Long id;          // 主键
    private String name;      // 用户名
    private String password;  // 密码
    private String salt;      // 盐
    private String email;
    private String phoneNumber;
    private Integer status;   // 状态：-1逻辑删除,0禁用,1启用

    @TableField(fill = INSERT)
    private Date createTime;          // 创建时自动填充

    private Date lastLoginTime;

    @TableField(fill = INSERT_UPDATE)
    private Date lastUpdateTime;      // 插入和更新时自动填充
}
```

### 5.1 `@TableName("orm_user")` —— 表名映射

告诉 MP 这个实体对应数据库的 `orm_user` 表。如果不写，MP 默认把类名转下划线当表名（`User` → `user`）。这里表名带 `orm_` 前缀，所以必须显式指定。

### 5.2 `@TableField(fill = ...)` —— 自动填充标记

- `fill = INSERT`：插入时填充（如 `createTime`）
- `fill = INSERT_UPDATE`：插入和更新都填充（如 `lastUpdateTime`）

光标记还不够，还要配一个填充处理器（见第七节 `CommonFieldHandler`），MP 才知道填什么值。

### 5.3 Lombok 注解

- `@Data`：getter/setter/toString 等
- `@NoArgsConstructor` / `@AllArgsConstructor`：无参和全参构造器
- `@Builder`：链式构造，测试里 `User.builder().name("x").password("y").build()` 就是它提供的

> 💡 `serialVersionUID` 是 Java 序列化版本号。实体实现 `Serializable` 是为了在分布式/缓存场景下能序列化传输。前端没有直接对应物，可以理解为"给对象加了个版本戳，结构变了能识别"。

---

## 六、Mapper 层：BaseMapper 的魔法

```java
@Component
public interface UserMapper extends BaseMapper<User> {
}
```

**就这一行，你已经拥有了 User 表的全部单表 CRUD 能力。** `BaseMapper<User>` 内置了这些方法（不用写任何 SQL）：

| 方法 | 等价 SQL |
| --- | --- |
| `insert(User)` | `INSERT INTO orm_user ...` |
| `deleteById(1L)` | `DELETE FROM orm_user WHERE id = 1` |
| `updateById(user)` | `UPDATE orm_user SET ... WHERE id = ?` |
| `selectById(1L)` | `SELECT * FROM orm_user WHERE id = 1` |
| `selectList(null)` | `SELECT * FROM orm_user` |
| `selectList(QueryWrapper)` | `SELECT * FROM orm_user WHERE ...` |
| `selectPage(page, wrapper)` | 分页查询 |
| `selectCount(wrapper)` | `SELECT COUNT(*) FROM ... WHERE ...` |
| ... 还有十几个 | |

`@Component` 让它注册成 Bean（其实 MP 的 `@MapperScan` 已经扫描注册了，这里加 `@Component` 是冗余保险）。

> 💡 前端类比：这像一个"自带 CRUD 的基类 Repository"，类似 Prisma 的 `prisma.user.findMany()` / `prisma.user.create()`——你只声明实体，CRUD 方法自动有。区别是 MP 用接口继承，Prisma 用代码生成。

---

## 七、Service 层：IService + ServiceImpl

MP 提供了比 BaseMapper 更丰富的 Service 层封装。套路是三步：

### 7.1 接口继承 IService

```java
public interface UserService extends IService<User> {
}
```

`IService<T>` 在 BaseMapper 之上又封装了一批**业务级**方法：`saveBatch`(批量插入)、`saveOrUpdate`、`removeByIds`、`list`、`page` 等，还自带事务和批处理优化。

### 7.2 实现类继承 ServiceImpl

```java
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {
}
```

`ServiceImpl<M, T>` 是 MP 提供的实现类，泛型 `<UserMapper, User>` 告诉它用哪个 Mapper、操作哪个实体。它内部已经把 `IService` 的方法全实现了，所以**实现类一行代码都不用写**就拥有全部能力。需要扩展自定义业务方法时，再往里加。

### 7.3 为什么不直接用 Mapper，还要套一层 Service？

这是分层架构的规范：

- **Mapper 层**：只管"和数据库对话"，单表 CRUD。
- **Service 层**：管"业务逻辑"，组合多个 Mapper、加事务、加校验。前端调接口打交道的通常是 Service。

MP 的 `IService` 让简单 Service 也免写样板，但复杂业务（多表联查、跨服务协作）还是要自己写。

---

## 八、配置类 MybatisPlusConfig

```java
@Configuration
@MapperScan(basePackages = {"com.xkcoding.orm.mybatis.plus.mapper"})
@EnableTransactionManagement
public class MybatisPlusConfig {

    @Bean
    public PerformanceInterceptor performanceInterceptor(){
        return new PerformanceInterceptor();   // 性能分析拦截器
    }

    @Bean
    public PaginationInterceptor paginationInterceptor() {
        return new PaginationInterceptor();   // 分页插件
    }
}
```

### 8.1 `@MapperScan` —— 扫描 Mapper 接口

指定 `mapper` 包下的接口都注册成 MyBatis 的 Mapper Bean。没有它，`UserMapper` 不会被 MyBatis 代理实现。

### 8.2 `@EnableTransactionManagement` —— 开启事务

启用注解式事务管理（配合 `@Transactional` 使用）。Spring Boot 默认已开启，这里显式声明更清晰。

### 8.3 两个拦截器（插件）

- **`PerformanceInterceptor`**：性能分析插件，打印每条 SQL 的执行耗时。**注释明确说"不建议生产使用"**，因为它有性能开销，开发调试用。
- **`PaginationInterceptor`**：分页插件。MP 的分页是**物理分页**（真的发 `LIMIT` SQL），必须配这个插件才生效，否则 `selectPage` 只是内存分页（查出全部再截取，数据量大时灾难）。

> ⚠️ MP 3.4+ 分页插件改名为 `MybatisPlusInterceptor`，需要把分页和性能插件一起加进去。本模块用的是 3.1.0 的老写法。

---

## 九、自动填充处理器 CommonFieldHandler

```java
@Slf4j
@Component
public class CommonFieldHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        log.info("start insert fill ....");
        this.setFieldValByName("createTime", new Date(), metaObject);
        this.setFieldValByName("lastUpdateTime", new Date(), metaObject);
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        log.info("start update fill ....");
        this.setFieldValByName("lastUpdateTime", new Date(), metaObject);
    }
}
```

它和实体上的 `@TableField(fill = ...)` 配合使用：

1. 实体 `createTime` 标了 `fill = INSERT` → 插入时触发 `insertFill`
2. 实体 `lastUpdateTime` 标了 `fill = INSERT_UPDATE` → 插入触发 `insertFill`，更新触发 `updateFill`
3. 处理器里 `setFieldValByName("createTime", new Date(), metaObject)` 把当前时间填进去

**效果**：你 `userService.save(user)` 时不用手动 `setCreateTime`，MP 自动填上当前时间；`updateById` 时自动刷新 `lastUpdateTime`。这就是"审计字段"的自动化。

> 💡 前端类比：像数据库层面的"自动 updatedAt"，类似 MongoDB 的 timestamp 选项或 Sequelize 的 `timestamps: true`。

---

## 十、ActiveRecord 模式：Role 实体

```java
@Data
@TableName("orm_role")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = true)
public class Role extends Model<Role> {
    private Long id;
    private String name;

    @Override
    protected Serializable pkVal() {
        return this.id;   // 必须实现，否则 xxById 方法失效
    }
}
```

### 10.1 什么是 ActiveRecord 模式？

ActiveRecord 是一种 ORM 模式：**实体对象本身就能操作数据库**，不需要单独的 Mapper/Repository。Ruby on Rails、Laravel 的 Eloquent 都是这种风格。

继承 `Model<Role>` 后，`Role` 对象自带方法：

```java
Role role = new Role();
role.setName("VIP");
role.insert();              // 直接插入，返回 boolean
role.setId(1L).setName("管理员").updateById();   // 链式更新
new Role().setId(1L).selectById();   // 查询
new Role().setId(1L).deleteById();  // 删除
new Role().selectAll();             // 查全部
```

### 10.2 关键注解

- `@Accessors(chain = true)`：开启链式调用，`setId()` 返回 `this` 而非 void，所以能 `.setId(1L).setName("x").updateById()`。
- `@EqualsAndHashCode(callSuper = true)`：生成 equals/hashCode 时把父类 `Model` 的字段也算进去（Lombok 规范要求继承时显式声明）。
- `pkVal()`：返回主键值。ActiveRecord 的 `xxById` 方法靠它定位记录，不实现就失效。

### 10.3 一个隐蔽的坑（注释里强调了）

> "即使使用 ActiveRecord 不会用到 RoleMapper，RoleMapper 这个接口也必须创建"

MP 的 ActiveRecord 底层依然依赖 Mapper 接口（`Model` 内部通过反射找对应的 Mapper）。所以 `RoleMapper extends BaseMapper<Role>` 必须存在，哪怕你从不直接调用它。删了它，ActiveRecord 操作会报找不到 Mapper。

---

## 十一、测试：Service 模式 CRUD（UserServiceTest）

测试类继承 `SpringBootDemoOrmMybatisPlusApplicationTests`（带 `@SpringBootTest` 的基类），复用 Spring 上下文。核心用例：

### 11.1 新增 + ID 回显

```java
User testSave3 = User.builder().name("testSave3").password(...).build();
boolean save = userService.save(testSave3);
log.debug("【测试id回显#testSave3.getId()】= {}", testSave3.getId());
```

`save()` 后，传入的实体 `testSave3` 的 `id` 字段会被自动回填（因为 `id-type: auto`，MP 拿到数据库生成的主键设回对象）。这是非常实用的特性——插入后立刻能拿到自增 ID。

### 11.2 批量新增

```java
userService.saveBatch(userList);
```

一条 SQL 批量插入，比循环单条 `save` 快得多。MP 内部会按批次（默认 1000 条）分批提交。

### 11.3 条件构造器 QueryWrapper

```java
QueryWrapper<User> wrapper = new QueryWrapper<>();
wrapper.like("name", "Save1").or().eq("phone_number", "17300000001").orderByDesc("id");
```

`QueryWrapper` 是 MP 的条件构造器，链式 API 拼 WHERE 条件：

| 方法 | SQL |
| --- | --- |
| `eq("name", "x")` | `name = 'x'` |
| `ne("name", "x")` | `name != 'x'` |
| `like("name", "Save1")` | `name LIKE '%Save1%'` |
| `or()` | `OR` |
| `orderByDesc("id")` | `ORDER BY id DESC` |
| `gt("age", 18)` | `age > 18` |
| `between("id", 1, 10)` | `id BETWEEN 1 AND 10` |
| `isNull("email")` | `email IS NULL` |

> ⚠️ 字符串字段名 `"phone_number"` 是**数据库列名**，不是 Java 属性名。写错列名 SQL 会报错。MP 3.x 后推荐用 Lambda 版本（见下）避免硬编码列名。

### 11.4 分页查询

```java
Page<User> userPage = new Page<>(1, 5);   // 第1页，每页5条
userPage.setDesc("id");
IPage<User> page = userService.page(userPage, new QueryWrapper<>());
page.getRecords();   // 当前页数据
page.getTotal();     // 总记录数
page.getSize();       // 每页大小
```

`Page(1, 5)` 表示第 1 页、每页 5 条。`userService.page()` 配合分页插件，会自动执行 `COUNT` 查总数 + `LIMIT` 查分页数据，返回的 `IPage` 里有记录列表和总数。

### 11.5 Lambda 条件构造器（ActiveRecord 测试里出现）

```java
new QueryWrapper<Role>().lambda().eq(Role::getId, 2)
```

`.lambda()` 切换到 Lambda 模式，用方法引用 `Role::getId` 代替字符串列名。**好处**：编译期检查、重构改名自动跟、不怕列名写错。这是实际开发中**强烈推荐**的写法。

---

## 十二、SQL 脚本

`schema.sql` 建表，`data.sql` 初始化数据。注意表名带 `orm_` 前缀，和实体的 `@TableName("orm_user")` 对应。`status` 字段用 -1/0/1 表示逻辑删除/禁用/启用——这是逻辑删除的约定（MP 支持配置自动逻辑删除，本模块注释里留了配置示例但没启用）。

---

## 十三、运行与验证

本模块没有 HTTP 接口，通过运行单元测试验证。在模块目录下：

```sh
mvn test
```

或用 IDE 右键 `UserServiceTest` / `ActiveRecordTest` 运行单个测试方法。前提：本地 MySQL 跑在 127.0.0.1:3306，有 `spring-boot-demo` 库（脚本会自动建表插数据）。

测试通过说明：BaseMapper 的 CRUD、IService 的批量/分页、自动填充、ActiveRecord 全链路正常。

---

## 十四、动手练习

1. **加一个自定义查询**：在 `UserMapper` 里用 `@Select` 写一个按邮箱查用户的方法，在 Service 调用，测试验证。
2. **体验 Lambda Wrapper**：把 `UserServiceTest.testQueryByCondition` 里的字符串列名 `wrapper.like("name", ...)` 改成 Lambda 版 `wrapper.lambda().like(User::getName, ...)`，对比可读性。
3. **开启逻辑删除**：在 yml 里取消注释 `logic-delete-value: 1` / `logic-not-delete-value: 0`，给 `User.status` 加 `@TableLogic`，然后 `removeById(1L)`，观察 SQL 变成 `UPDATE ... SET status = -1` 而非真删。
4. **加一个 Controller**：引入 `spring-boot-starter-web`，写 `UserController` 调 `UserService`，暴露 `GET /users` 列表接口，把数据层串到 Web 层。
5. **对比 MyBatis**：回顾 `15-数据库操作_MyBatis` 模块，同样一个用户表 CRUD，MP 少写了多少 SQL？体会"增强"的含义。
6. **测试自动填充**：故意在 `save` 时不设 `createTime`，查询回来验证它被 `CommonFieldHandler` 填了当前时间。

---

## 十五、本模块知识点总结（结合实际开发详解）

MyBatis-Plus 是国内 Spring Boot 项目里最流行的 ORM 增强工具，掌握它能极大提升数据层开发效率。下面把核心知识点放到真实开发场景里讲透。

### 15.1 MyBatis vs MyBatis-Plus vs JPA：怎么选？

**三者定位：**

| 框架 | 定位 | SQL 控制力 | 开发效率 | 学习曲线 |
| --- | --- | --- | --- | --- |
| JPA（Hibernate） | 全自动 ORM，面向对象操作 | 低（SQL 自动生成，复杂查询要 JPQL） | 高（单表几乎零代码） | 中高 |
| MyBatis | 半自动 ORM，SQL 手写 | 高 | 中（要写 SQL） | 低 |
| MyBatis-Plus | MyBatis + 单表增强 | 高（复杂查询仍写 SQL） | 高（单表零代码 + 复杂查询可控） | 低 |

**实际开发选型建议：**

- **国内项目、对 SQL 性能敏感、团队熟 MyBatis** → MyBatis-Plus 是首选。单表用内置 CRUD，多表联查写 XML/注解 SQL，兼顾效率和可控性。
- **面向对象建模重、表结构简单、团队熟 JPA** → JPA。但 JPA 的 N+1 问题、复杂查询难调优，国内用得相对少。
- **纯 MyBatis** → 除非历史项目，新项目直接上 MP，没有理由不用。

**常见坑：**

- 同时引 `mybatis-spring-boot-starter` 和 `mybatis-plus-boot-starter` 导致冲突：**只引 MP 的 starter**，它已包含 MyBatis。
- MP 版本和 Spring Boot 版本不匹配：升级前查 MP 官方兼容矩阵，别盲目升。

### 15.2 BaseMapper + IService：分层使用的正确姿势

**实际开发的标准分层：**

```
Controller → Service(IService) → Mapper(BaseMapper) → DB
```

- **简单单表 CRUD**：直接用 `IService` 的方法，Controller 调 Service，Service 调 `ServiceImpl`（MP 实现），一行业务代码不写。
- **复杂业务**：在 `UserServiceImpl` 里写自定义方法，组合多个 Mapper、加 `@Transactional` 事务。
- **多表联查**：在 `UserMapper` 写 `@Select` 注解或 XML SQL，Service 调这个自定义方法。

**最佳实践：**

1. **Service 层别直接暴露 Mapper**：Controller 永远调 Service，不直接调 Mapper。这样事务、缓存、校验都在 Service 层收口。
2. **DTO 隔离**：Controller 用 DTO 和前端交互，Service 内部用实体，别把实体直接返回给前端（暴露表结构、字段名耦合）。
3. **批量操作用 `saveBatch`**：循环 `save` 一条条插性能差，`saveBatch` 一条 SQL 批量插，效率差几个数量级。

**常见坑：**

- `ServiceImpl` 的方法默认不带事务的批处理可能失败一半：批量操作要自己加 `@Transactional` 保证原子性。
- `saveOrUpdate` 的判断逻辑：MP 根据主键是否有值决定 save 还是 update，理解错了会导致本该 update 的变成 insert。

### 15.3 条件构造器：QueryWrapper vs LambdaQueryWrapper

**两种写法对比：**

```java
// 字符串列名（易出错）
new QueryWrapper<User>().eq("name", "x").like("email", "a");

// Lambda（推荐）
new LambdaQueryWrapper<User>().eq(User::getName, "x").like(User::getEmail, "a");
// 或
new QueryWrapper<User>().lambda().eq(User::getName, "x");
```

**实际开发强烈推荐 Lambda 版：**

1. **编译期检查**：`User::getName` 写错了编译报错；字符串 `"name"` 写错运行时才报 SQL 错误。
2. **重构友好**：IDE 改字段名时方法引用自动跟着改，字符串列名不会。
3. **不怕列名记错**：不用记数据库列名是 `phone_number` 还是 `phoneNumber`。

**常见坑：**

- 字符串版用 Java 属性名还是数据库列名？**MP 的 QueryWrapper 用数据库列名**（`phone_number`），Lambda 版用属性名（`User::getPhoneNumber`）。混用会困惑。
- `or()` 的优先级：`eq("a",1).eq("b",2).or().eq("c",3)` 实际是 `a=1 AND b=2 OR c=3`，要 `a=1 AND (b=2 OR c=3)` 得用嵌套 `.and(w -> w.eq("b",2).or().eq("c",3))`。

### 15.4 分页插件：物理分页的配置与坑

**本模块配置：**

```java
@Bean
public PaginationInterceptor paginationInterceptor() {
    return new PaginationInterceptor();
}
```

**为什么必须配插件？** MP 的 `page()` 方法，没插件时是**内存分页**（查出全部再 `subList`），数据量大会 OOM；配了插件才是**物理分页**（自动拼 `LIMIT`，只查一页数据）。

**实际开发的分页规范：**

1. 统一封装分页响应：`{ records, total, current, size }`，前端按这套结构渲染表格。
2. 分页 + 排序一起做：`Page` 对象设 `setDesc("create_time")` 或用 `OrderItem`。
3. 深分页优化：`LIMIT 1000000, 10` 这种深分页很慢，用 `WHERE id > 上次最大id LIMIT 10` 的"游标分页"替代。

**常见坑：**

- 忘了配分页插件，分页查询 OOM：引入 MP 后第一件事就是配 `PaginationInterceptor`（或新版 `MybatisPlusInterceptor`）。
- 多表联查分页：`selectPage` 对自定义多表 SQL 分页时，COUNT 语句可能生成错误，要手写 `countSql` 或用插件配置优化。

### 15.5 自动填充：审计字段的自动化

**本模块实现：** 实体标 `@TableField(fill = ...)` + 配 `MetaObjectHandler`。

**实际开发常用场景：**

- `create_time` / `update_time`：插入/更新自动填当前时间
- `create_by` / `update_by`：自动填当前登录用户 ID（从 Security 上下文取）
- `deleted`：逻辑删除标记（配合 `@TableLogic`）

**最佳实践：**

1. 每张业务表都加 `create_time`、`update_time`、`create_by`、`update_by`、`deleted` 五个审计字段，用自动填充统一处理。
2. `MetaObjectHandler` 里取当前用户：`SecurityContextHolder.getContext().getAuthentication()` 拿登录用户，填 `createBy`。
3. 填充逻辑要轻：别在 `insertFill` 里做重操作（如远程查用户），它每次插入都执行。

**常见坑：**

- 只标 `@TableField(fill=...)` 不配 `MetaObjectHandler`：填充不生效，字段是 null。两者必须同时有。
- `updateById` 时 `updateFill` 不触发：检查是不是用了自定义 SQL 绕过了 MP 的更新方法。

### 15.6 ActiveRecord 模式：用不用？

**ActiveRecord 的特点：** 实体自己带数据库操作方法，省去 Mapper/Service 一层。

**实际开发评价：**

- **小项目/工具类项目**：ActiveRecord 简洁，`role.insert()` 一行搞定，爽。
- **中大型项目**：**不推荐**。它打破了"实体是纯数据对象"的分层原则，让实体耦合了持久层逻辑，测试和替换都变难。主流还是 Mapper/Service 模式。
- **MP 的 ActiveRecord 仍依赖 Mapper**：必须建 `RoleMapper`，否则失效（本模块注释强调过）。它本质是 Mapper 的语法糖，不是真正的独立模式。

**建议**：了解即可，实际项目用 Mapper/Service 模式。ActiveRecord 留给脚本、原型、简单工具。

### 15.7 主键策略：id-type 怎么选？

MP 的 `id-type` 配置主键生成方式：

| 策略 | 说明 | 适用 |
| --- | --- | --- |
| `AUTO` | 数据库自增 | 单库、无需分布式 |
| `INPUT` | 手动输入 | 业务主键（如订单号） |
| `ID_WORKER` | 雪花算法，数字型全局唯一 | 分布式、分库分表 |
| `UUID` | UUID 字符串 | 无序、索引差，少用 |

**实际开发建议：**

- 单体应用：`AUTO` 最简单。
- 微服务/分库分表：用 `ID_WORKER`（雪花 ID），全局唯一、趋势递增、对索引友好。
- 业务有自然主键（如身份证号）：`INPUT` 手动设。
- **避免 UUID 做主键**：UUID 无序，B+ 树索引插入时页分裂严重，性能差。

### 15.8 逻辑删除：软删除的配置

本模块 yml 注释里留了逻辑删除配置：

```yaml
logic-delete-value: 1          # 已删除值
logic-not-delete-value: 0       # 未删除值
```

配合实体字段 `@TableLogic`：

```java
@TableLogic
private Integer status;
```

**效果**：`removeById(1L)` 不再执行 `DELETE`，而是 `UPDATE orm_user SET status = 1 WHERE id = 1`；所有查询自动加 `WHERE status = 0` 过滤已删除数据。

**实际开发：**

- 重要业务数据（订单、用户）**永远逻辑删除**，不物理删，保留数据可追溯。
- 日志、临时数据可物理删除省空间。
- 逻辑删除字段要建索引，否则查询慢。

**常见坑：**

- 逻辑删除后唯一索引冲突：`name` 唯一，逻辑删了再插同名记录会冲突。解决：唯一索引带上 `deleted` 字段联合唯一，或删除时把 name 加后缀。
- 以为 `selectList` 能查到已删除数据：配了逻辑删除，查询自动过滤，要查已删除得用自定义 SQL 绕过。

---

> 📌 **学习建议**：MyBatis-Plus 是国内 Java 后端的"国民级"ORM 工具，实际项目里几乎必用。建议重点掌握三件事：① `BaseMapper` + `IService` 的分层套路（Controller→Service→Mapper）；② `LambdaQueryWrapper` 的条件构造（告别字符串列名）；③ 分页插件 + 自动填充的配置。把这三样练熟，你就能独立写数据层了。另外一定要对比着 `15-数据库操作_MyBatis` 来看——理解了"MP 在 MyBatis 上增强了什么"，你才算真正懂这两个框架的关系，而不是只会调 API。
