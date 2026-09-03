# 16 - MyBatis 通用 Mapper 与分页插件

> 对应项目模块：`demo-orm-mybatis-mapper-page`
> 前置知识：已学完前序 MyBatis 模块（`demo-orm-mybatis`），了解 MyBatis 基本用法、`@Mapper`、XML 映射
> 学习目标：掌握通用 Mapper（tk.mybatis）如何"零 SQL"完成单表 CRUD，掌握 PageHelper 分页插件的使用与原理，能用它们快速搭建后端列表查询接口。

---

## 一、本模块要解决什么问题？

在原生 MyBatis 模块里，每张表都要手写一套 `insert`、`delete`、`update`、`select` 的 XML 映射——这些单表操作高度重复，写起来枯燥又容易出错。本模块引入两个插件解决这个痛点：

| 插件 | 解决的问题 | 一句话类比 |
| --- | --- | --- |
| **通用 Mapper（tk.mybatis）** | 单表 CRUD 的重复 SQL 全自动生成，继承一个接口就拥有几十个方法 | 像 React 的自定义 Hook，把重复逻辑抽成一行调用 |
| **PageHelper** | 物理分页（limit）全自动拼接，不用手写 `limit` 子句 | 像前端表格组件传 `page`/`size` 就自动分页 |

最终效果：`UserMapper` 接口里**一行方法都不用写**，就能完成增删改查、批量保存、条件查询、分页排序——这是 MyBatis 开发体验的大幅提升。

---

## 二、项目结构

```
demo-orm-mybatis-mapper-page/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/xkcoding/orm/mybatis/MapperAndPage/
    │   │   ├── SpringBootDemoOrmMybatisMapperPageApplication.java  # 启动类
    │   │   ├── entity/
    │   │   │   └── User.java                  # 实体类（JPA 注解）
    │   │   └── mapper/
    │   │       └── UserMapper.java             # Mapper 接口（继承通用 Mapper）
    │   └── resources/
    │       ├── application.yml                  # 数据源 + MyBatis + 通用Mapper + PageHelper 配置
    │       └── db/
    │           ├── schema.sql                   # 建表脚本
    │           └── data.sql                     # 初始数据
    └── test/java/.../mapper/
        └── UserMapperTest.java                 # 全部功能演示（重点看这个）
```

注意：本模块**没有 Controller 和 Service**，所有功能在 `UserMapperTest` 里通过单元测试演示。这是因为重点在"数据访问层"，先验证 Mapper 能力，后续再组装到 Web 层。

---

## 三、pom.xml 依赖

```xml
<!-- 通用Mapper -->
<dependency>
    <groupId>tk.mybatis</groupId>
    <artifactId>mapper-spring-boot-starter</artifactId>
    <version>${mybatis.mapper.version}</version>
</dependency>

<!-- 分页助手 -->
<dependency>
    <groupId>com.github.pagehelper</groupId>
    <artifactId>pagehelper-spring-boot-starter</artifactId>
    <version>${mybatis.pagehelper.version}</version>
</dependency>
```

- `mapper-spring-boot-starter`：通用 Mapper 的 Spring Boot 整合包，自动配置好 tk.mybatis 的 `SqlSessionFactory`，并扫描 `@MapperScan` 注解的包。
- `pagehelper-spring-boot-starter`：PageHelper 分页插件的整合包，自动把分页拦截器装进 MyBatis 执行链。
- 注意本模块用的是 `spring-boot-starter`（不是 web），因为只演示数据层，不需要 Web 容器。但保留了 MySQL 驱动、Hikari 连接池（由通用 Mapper starter 传递引入）、Lombok、Hutool、Guava。

> 💡 前端类比：通用 Mapper 就像你装了一个 npm 包，`import { CRUD } from 'tk-mybatis'`，继承一下就拿到全套方法，不用自己写实现。

---

## 四、实体类 User：用 JPA 注解描述表结构

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Table(name = "orm_user")
public class User implements Serializable {
    private static final long serialVersionUID = -1840831686851699943L;

    @Id
    @KeySql(useGeneratedKeys = true)
    private Long id;

    private String name;
    private String password;
    private String salt;
    private String email;
    private String phoneNumber;
    private Integer status;
    private Date createTime;
    private Date lastLoginTime;
    private Date lastUpdateTime;
}
```

通用 Mapper 不读 XML，它靠**注解**推断表结构：

- `@Table(name = "orm_user")`：JPA 注解，声明实体对应 `orm_user` 表。如果不写，默认用类名作为表名。
- `@Id`：标记 `id` 是主键字段。通用 Mapper 的 `selectByPrimaryKey`、`deleteByPrimaryKey` 等方法就是靠它定位主键。
- `@KeySql(useGeneratedKeys = true)`：tk.mybatis 的注解，表示主键由数据库自增生成，插入后回写到实体对象的 `id` 字段（即"主键回写"）。
- 其他字段没有注解，默认按"字段名 = 属性名"（配合下划线转驼峰）映射。比如 `phone_number` 列 ↔ `phoneNumber` 属性。
- `@Data`、`@Builder`、`@NoArgsConstructor`、`@AllArgsConstructor` 都是 Lombok 注解，生成 getter/setter/构造器/链式构建。

> 💡 前端类比：这像用 TypeScript 接口 + 装饰器描述数据库表，`@Table` 相当于"这个类对应哪张表"的元信息。

---

## 五、Mapper 接口：继承即拥有全部能力

```java
@Component
public interface UserMapper extends Mapper<User>, MySqlMapper<User> {
}
```

这是本模块最核心的一行代码——**接口体是空的**，但继承了 `Mapper<User>` 和 `MySqlMapper<User>`，瞬间拥有几十个现成方法。

### 5.1 `Mapper<User>` 提供的方法

继承 `tk.mybatis.mapper.common.Mapper` 后，自动获得：

| 方法 | 功能 |
| --- | --- |
| `insert(entity)` | 插入（null 字段也插入） |
| `insertSelective(entity)` | 插入（只插非 null 字段） |
| `insertUseGeneratedKeys(entity)` | 插入并回写自增主键 |
| `insertList(list)` | 批量插入 |
| `deleteByPrimaryKey(id)` | 按主键删除 |
| `delete(entity)` | 按实体非 null 字段条件删除 |
| `updateByPrimaryKey(entity)` | 按主键更新（全字段） |
| `updateByPrimaryKeySelective(entity)` | 按主键更新（只更新非 null 字段） |
| `selectByPrimaryKey(id)` | 按主键查 |
| `selectAll()` | 查全部 |
| `select(entity)` | 按实体非 null 字段条件查 |
| `selectCount(entity)` | 按条件计数 |
| `selectByExample(example)` | 按 Example 条件查（复杂条件） |

### 5.2 `MySqlMapper<User>` 提供的方法

额外提供 MySQL 特有的批量插入 `insertList`，用一条 `INSERT ... VALUES (),(),()` 完成，比循环单条插入快得多。

### 5.3 为什么接口能"继承就有实现"？

通用 Mapper 利用 MyBatis 的**动态 SQL 机制**：启动时扫描实体类的注解，根据 `@Table`、`@Id` 等元信息，用模板动态生成对应的 SQL 语句并注册到 MyBatis，所以你不用写 XML，运行时调用这些方法就能执行对应 SQL。

> 💡 前端类比：这像 ORM 工具（如 Prisma）根据 schema 自动生成 CRUD API，你只定义模型，操作方法自动来。

---

## 六、启动类：注意 `@MapperScan` 的包

```java
@SpringBootApplication
@MapperScan(basePackages = {"com.xkcoding.orm.mybatis.MapperAndPage.mapper"})
public class SpringBootDemoOrmMybatisMapperPageApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoOrmMybatisMapperPageApplication.class, args);
    }
}
```

**关键细节**：这里的 `@MapperScan` 是 `tk.mybatis.spring.annotation.MapperScan`，**不是** MyBatis 官方的 `org.mybatis.spring.annotation.MapperScan`。

为什么？因为通用 Mapper 需要用自己的扫描器，在扫描时把通用接口的方法注册成动态 SQL。如果用错包，通用 Mapper 的方法调用会报"找不到语句"。

> ⚠️ 这是新手最常踩的坑：import 错 `@MapperScan`，导致通用 Mapper 方法全部失效。务必确认是 `tk.mybatis.spring.annotation.MapperScan`。

---

## 七、application.yml 配置详解

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
    com.xkcoding.orm.mybatis.MapperAndPage.mapper: trace
mybatis:
  configuration:
    map-underscore-to-camel-case: true
  mapper-locations: classpath:mappers/*.xml
  type-aliases-package: com.xkcoding.orm.mybatis.MapperAndPage.entity
mapper:
  mappers:
  - tk.mybatis.mapper.common.Mapper
  not-empty: true
  style: camelhump
  wrap-keyword: "`{0}`"
  safe-delete: true
  safe-update: true
  identity: MYSQL
pagehelper:
  auto-dialect: true
  helper-dialect: mysql
  reasonable: true
  params: count=countSql
```

### 7.1 数据源 + 自动建表

- `initialization-mode: always`：每次启动都执行 `schema.sql` 和 `data.sql`，自动建表+插初始数据，省去手动建库。`always` 适合 demo，生产用 `one`（首次）或 `never`。
- `continue-on-error: true`：建表语句报错也继续（比如表已存在），避免重复启动失败。
- `hikari` 连接池参数：控制连接数、超时、空闲回收，生产要按并发调优。

### 7.2 MyBatis 配置

- `map-underscore-to-camel-case: true`：下划线列名自动转驼峰属性名，`phone_number` ↔ `phoneNumber`。
- `mapper-locations: classpath:mappers/*.xml`：加载自定义 XML 映射（本模块没用，但保留入口，复杂 SQL 仍可写 XML）。
- `type-aliases-package`：实体包，XML 里可直接写类名不用全限定名。

### 7.3 通用 Mapper 配置（`mapper:` 段）

| 配置项 | 作用 |
| --- | --- |
| `mappers` | 注册基础通用 Mapper 接口，自定义 Mapper 继承它 |
| `not-empty: true` | 字符串字段空时当作 null，不参与条件查询 |
| `style: camelhump` | SQL 字段风格用驼峰转下划线 |
| `wrap-keyword: \`{0}\`` | 关键字用反引号包裹（MySQL 语法） |
| `safe-delete: true` | 删除必须带条件，防止全表删除 |
| `safe-update: true` | 更新必须带条件，防止全表更新 |
| `identity: MYSQL` | 主键策略用 MySQL 自增 |

`safe-delete`/`safe-update` 是重要的安全开关：忘记加 where 的 delete/update 会被拦截报错，避免误删全表。

### 7.4 PageHelper 配置（`pagehelper:` 段）

| 配置项 | 作用 |
| --- | --- |
| `auto-dialect: true` | 自动检测数据库方言 |
| `helper-dialect: mysql` | 指定 MySQL 方言（生成 `limit` 子句） |
| `reasonable: true` | 合理化分页：页码 ≤0 查第一页，>总页数查最后一页 |
| `params: count=countSql` | count 查询的参数标识 |

---

## 八、功能演示：UserMapperTest 逐个讲解

测试类继承 `SpringBootDemoOrmMybatisMapperPageApplicationTests`（带 `@SpringBootTest`），所以能注入 `UserMapper` 跑真实 SQL。

### 8.1 插入 + 主键回写

```java
@Test
public void testInsert() {
    String salt = IdUtil.fastSimpleUUID();
    User testSave3 = User.builder().name("testSave3")
        .password(SecureUtil.md5("123456" + salt)).salt(salt)
        .email("testSave3@xkcoding.com").phoneNumber("17300000003")
        .status(1).lastLoginTime(new DateTime())
        .createTime(new DateTime()).lastUpdateTime(new DateTime()).build();
    userMapper.insertUseGeneratedKeys(testSave3);
    Assert.assertNotNull(testSave3.getId());
}
```

- `User.builder()...build()`：Lombok `@Builder` 的链式构造，比 `new` + 一堆 `set` 清晰。
- `insertUseGeneratedKeys`：插入并把数据库生成的自增 id 回写到 `testSave3.getId()`。这就是 `@KeySql(useGeneratedKeys = true)` 的作用。
- 密码用 `SecureUtil.md5(密码+盐)` 加密，盐用 UUID——这是用户密码存储的标准做法。

### 8.2 批量插入

```java
@Test
public void testInsertList() {
    List<User> userList = Lists.newArrayList();
    for (int i = 4; i < 14; i++) { ... userList.add(user); }
    int i = userMapper.insertList(userList);
    Assert.assertEquals(userList.size(), i);
    List<Long> ids = userList.stream().map(User::getId).collect(Collectors.toList());
}
```

`insertList` 来自 `MySqlMapper`，一条 SQL 插入 10 条数据，效率远高于循环单条插入。批量插入后每个对象的 id 也会回写。

### 8.3 删除 / 更新

```java
userMapper.deleteByPrimaryKey(1L);              // 按主键删
userMapper.updateByPrimaryKeySelective(user);    // 按主键更新非 null 字段
```

`updateByPrimaryKeySelective` 只更新非 null 字段——比如只想改名字，其他字段设 null 就不会被覆盖，避免误清空。

### 8.4 分页 + 排序查询（PageHelper 核心）

```java
@Test
public void testQueryByPageAndSort() {
    initData();
    int currentPage = 1;
    int pageSize = 5;
    String orderBy = "id desc";
    int count = userMapper.selectCount(null);
    PageHelper.startPage(currentPage, pageSize, orderBy);
    List<User> users = userMapper.selectAll();
    PageInfo<User> userPageInfo = new PageInfo<>(users);
    Assert.assertEquals(5, userPageInfo.getSize());
    Assert.assertEquals(count, userPageInfo.getTotal());
}
```

**PageHelper 的使用三步曲**：

1. `PageHelper.startPage(页码, 每页条数, 排序)`：设置分页参数（ThreadLocal 存储）。
2. 紧接着执行一次查询：`userMapper.selectAll()`。
3. 用 `new PageInfo<>(结果)` 包装，获得分页信息（总条数、总页数、当前页数据等）。

**原理**：`PageHelper.startPage` 把分页参数存到 ThreadLocal，MyBatis 执行下一条查询时，分页拦截器拦截 SQL，自动在后面拼 `limit` 和 `order by`，并额外执行一次 `count(*)` 查总数。所以你写的还是普通查询，分页由插件自动完成。

> 💡 前端类比：这像前端表格组件，你只管调 `getList()`，组件内部自动加 `page`/`size` 参数并算总页数。区别是 PageHelper 在 SQL 层做拦截。

### 8.5 条件查询（Example）

```java
@Test
public void testQueryByCondition() {
    initData();
    Example example = new Example(User.class);
    example.createCriteria()
        .andLike("name", "%Save1%")
        .orEqualTo("phoneNumber", "17300000001");
    example.setOrderByClause("id desc");
    int count = userMapper.selectCountByExample(example);
    PageHelper.startPage(1, 3);
    List<User> userList = userMapper.selectByExample(example);
    PageInfo<User> userPageInfo = new PageInfo<>(userList);
}
```

`Example` 是通用 Mapper 的条件构造器，链式拼条件：

- `andLike("name", "%Save1%")`：name like '%Save1%'
- `orEqualTo("phoneNumber", "17300000001")`：或 phone = '17300000001'

生成的 SQL 类似：`WHERE name LIKE '%Save1%' OR phone_number = '17300000001' ORDER BY id DESC`。

> 💡 前端类比：`Example` 像前端构造查询参数对象，`createCriteria()` 相当于开启一个条件组，链式调用拼 `and`/`or`。

---

## 九、运行与验证

本模块是数据层 demo，没有 Web 接口，通过单元测试验证：

```sh
# 在模块目录下
mvn test
```

需要本地 MySQL，建库 `spring-boot-demo`，配置 `application.yml` 的账号密码。启动时会自动执行 `schema.sql` 建表、`data.sql` 插初始数据，然后跑测试。

观察控制台日志（因为配了 `logging.level ... trace`），能看到通用 Mapper 生成的实际 SQL，方便学习。

---

## 十、动手练习

1. **加一个按手机号查询**：用 `select` 方法传一个只设了 `phoneNumber` 的 User 实体，验证按非 null 字段条件查询。
2. **体验 safe-delete**：写一个 `userMapper.delete(null)`（无条件删除），观察是否被 `safe-delete` 拦截报错。
3. **改分页参数**：把 `testQueryByPageAndSort` 的 `pageSize` 改成 3，`reasonable` 设为 false，然后传一个超过总页数的页码，观察返回什么（体会 reasonable 的作用）。
4. **写一个 Controller**：给本模块加一个 `UserController`，暴露 `GET /users?page=1&size=5` 接口，返回 `PageInfo`，把数据层能力组装成 Web API。
5. **对比原生 MyBatis**：回想 `demo-orm-mybatis` 要手写 XML，本模块零 XML，体会通用 Mapper 省了多少代码。

---

## 十一、本模块知识点总结（结合实际开发详解）

通用 Mapper + PageHelper 是国内 MyBatis 项目的常见组合，下面把核心知识点放到真实开发场景讲透。

### 11.1 通用 Mapper：单表 CRUD 的"银弹"，但有边界

**实际开发中怎么用？**

- 单表的增删改查、按主键操作、按字段等值条件查询，全部用通用 Mapper，不写 XML。
- 多表关联查询、复杂统计报表，仍然写 XML 或自定义方法——通用 Mapper 不擅长 join。

**最佳实践：**

1. **每个实体配一个 Mapper 接口**，继承 `Mapper<T>`，单表能力立刻齐全。
2. **复杂查询用 `Example`**：链式拼条件，避免写 XML。但条件特别复杂时（多表 join、子查询），还是写 XML 更清晰。
3. **配合 `safe-delete`/`safe-update`**：开启这俩开关，防止误删/误更新全表，这是重要的安全防线。
4. **主键回写用 `insertUseGeneratedKeys`**：插入后能拿到 id，业务里常需要（比如插入用户后返回 id 给前端）。

**常见坑：**

1. **`@MapperScan` 用错包**：必须是 `tk.mybatis.spring.annotation.MapperScan`，用成官方的会导致通用方法失效。这是最高频的坑。
2. **实体没加 `@Id`**：通用 Mapper 不知道哪个是主键，`selectByPrimaryKey` 会报错。每个实体必须有 `@Id`。
3. **`@Table` 表名写错**：默认用类名当表名，类名和表名不一致（如 `User` vs `orm_user`）必须显式写 `@Table(name = "orm_user")`。
4. **字段映射不上**：列名 `phone_number` 属性名 `phoneNumber`，要开 `map-underscore-to-camel-case`，否则查出来是 null。
5. **`insert` vs `insertSelective`**：`insert` 会把 null 字段也插（数据库用默认值被覆盖成 null），`insertSelective` 只插非 null 字段。**生产推荐 `insertSelective`**，避免误清空有默认值的字段。

### 11.2 PageHelper：分页的"魔法"与陷阱

**实际开发中怎么用？**

```java
PageHelper.startPage(page, size);     // 设置分页
List<User> list = mapper.selectAll(); // 紧接着查
PageInfo<User> pageInfo = new PageInfo<>(list);  // 包装结果
```

`PageInfo` 包含前端分页组件需要的全部信息：`list`（当前页数据）、`total`（总条数）、`pageNum`（当前页）、`pages`（总页数）、`pageSize`（每页条数）等，直接序列化成 JSON 给前端表格用。

**最佳实践：**

1. **`startPage` 紧挨着查询**：分页参数存在 ThreadLocal，只对**紧接着的下一条**查询生效。中间插入其他查询会错乱。
2. **用 `PageInfo` 包装返回**：它提供标准分页响应结构，前端直接用。
3. **排序用 `startPage(page, size, "id desc")`**：在分页同时指定排序，比在 SQL 里写 `order by` 更统一。

**常见坑（PageHelper 的"著名"陷阱）：**

1. **`startPage` 后跟了多条查询**：只有第一条被分页，后续查询不分页或错乱。**务必保证 `startPage` 后紧跟目标查询。**
2. **线程复用导致分页参数泄漏**：ThreadLocal 用完没清，复用线程时上次的分页参数影响下次查询。PageHelper 内部会清理，但如果你在 `startPage` 后抛异常没执行查询，参数可能残留。**规范写法：确保 `startPage` 后一定执行查询。**
3. **`reasonable` 的双刃剑**：开启后页码越界自动修正，调试时可能掩盖前端传错页码的问题。生产可按需关闭。
4. **count 查询慢**：PageHelper 会额外执行 `count(*)`，大表 count 慢。可手动指定 count SQL 或用 `PageHelper.startPage(page, size, count=false)` 跳过。

### 11.3 通用 Mapper vs MyBatis-Plus：怎么选？

国内两大 MyBatis 增强工具，实际开发常面临选择：

| 维度 | 通用 Mapper (tk.mybatis) | MyBatis-Plus |
| --- | --- | --- |
| 核心思路 | 继承接口获方法 | 继承 BaseMapper |
| 条件构造 | `Example`（链式） | `QueryWrapper`（更强大） |
| 代码生成 | 需配合 generator | 内置代码生成器 |
| ActiveRecord | 不支持 | 支持（实体继承 Model） |
| 分页 | 配 PageHelper | 内置分页插件 |
| 社区活跃度 | 较低（维护放缓） | 高（主流选择） |

**建议**：新项目优先考虑 MyBatis-Plus（后续模块会讲），老项目维护遇到通用 Mapper 也要会用。两者思路相通，学会一个，另一个上手很快。

### 11.4 数据层到 Web 层的组装

本模块只演示了数据层，实际项目要组装成接口。标准三层结构：

```java
// Controller
@GetMapping("/users")
public PageInfo<User> list(@RequestParam(defaultValue = "1") int page,
                           @RequestParam(defaultValue = "10") int size) {
    return userService.list(page, size);
}

// Service
public PageInfo<User> list(int page, int size) {
    PageHelper.startPage(page, size, "id desc");
    List<User> list = userMapper.selectAll();
    return new PageInfo<>(list);
}
```

**最佳实践：**

1. **分页参数给默认值**：`defaultValue = "1"`，前端不传也不报错。
2. **Service 层调 `startPage`**：分页是业务逻辑，放 Service 而非 Controller，便于复用和测试。
3. **返回 `PageInfo` 或自定义分页 DTO**：`PageInfo` 字段多，生产常简化成 `{list, total, page, size}` 的统一响应体。

### 11.5 自动建表脚本的利弊

本模块用 `initialization-mode: always` 每次启动执行 SQL，方便 demo，但生产要慎用：

- **优点**：环境自包含，新人 clone 即可跑，不用手动建库。
- **缺点**：`schema.sql` 用 `DROP TABLE IF EXISTS` 会清空数据，生产用是灾难。

**生产做法：**

1. 用 `initialization-mode: never` 关闭自动执行。
2. 用 Flyway/Liquibase 做数据库版本管理（后续 `demo-flyway` 模块会讲），支持增量迁移、版本回滚。
3. demo/测试环境用 `always`，生产用 Flyway。

---

> 📌 **学习建议**：通用 Mapper + PageHandler 让你体会到"MyBatis 也能像 ORM 一样省事"。但要记住它们只解决单表问题，多表关联、复杂报表仍需手写 SQL——别指望一个插件包打天下。建议重点掌握三件事：① `@MapperScan` 用 tk 的包；② `startPage` 紧跟查询；③ `insertSelective` 优于 `insert`。这三点避坑，单表开发就顺畅了。下个模块会讲 MyBatis-Plus，思路类似但更强大，可以对比着学。
