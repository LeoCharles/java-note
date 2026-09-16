# 44 - MyBatis 多数据源（dynamic-datasource）

> 对应项目模块：`demo-multi-datasource-mybatis`
> 前置知识：已学完 `15-数据库操作_MyBatis`、`17-数据库操作_MyBatisPlus`、`43-多数据源_JPA`
> 学习目标：理解多数据源的使用场景，掌握基于 `dynamic-datasource-spring-boot-starter` 用一个 `@DS` 注解优雅切换数据源的方式，并能对比上一篇 JPA 多数据源的"手动配置"方案理解两种路线的差异。

---

## 一、本模块要解决什么问题？

### 1.1 什么是多数据源？

前面的数据库模块（JdbcTemplate / JPA / MyBatis / MyBatis-Plus）都只连了一个数据库。但真实业务里，一个应用常常需要**同时连多个数据库**，典型场景：

| 场景 | 说明 |
| --- | --- |
| **读写分离** | 主库（master）负责写（INSERT/UPDATE/DELETE），从库（slave）负责读（SELECT），分摊压力 |
| **多业务库** | 用户库、订单库、商品库分开，各自独立部署 |
| **新旧系统并行** | 老系统 MySQL + 新系统 PostgreSQL，过渡期要同时访问 |
| **跨库统计** | 把多个业务库的数据汇总到一张报表 |

> 💡 前端类比：这就像前端一个应用同时请求多个后端域名——你可能有 `api.user.com`、`api.order.com`、`api.pay.com` 三个不同的 baseURL，根据调用场景切换。多数据源就是后端版的"多 baseURL 切换"。

### 1.2 两种实现路线对比

Spring Boot 集成多数据源，主流有两条路：

| 路线 | 代表方案 | 特点 | 本模块 |
| --- | --- | --- | --- |
| **手动配置** | 自己写多个 `DataSource` + `SqlSessionFactory` + `@MapperScan` 分包 | 灵活但代码量大，每加一个数据源要写一堆配置类 | 上一篇 `43-多数据源_JPA` |
| **注解切换** | `dynamic-datasource-spring-boot-starter` | 配置文件声明数据源，一个 `@DS("xxx")` 注解切换，零配置类 | **本模块** |

本模块用的是 MyBatis-Plus 官方提供的 `dynamic-datasource-spring-boot-starter`，它的核心卖点：**在 yml 里声明多个数据源，用 `@DS` 注解在类或方法上指定走哪个库，框架用 AOP 自动切换，不用写任何配置类。**

> ⚠️ 注意：本模块用的是"注解切换"路线，它的本质是**运行时动态切换同一个连接**，而不是每个数据源独立的 SqlSessionFactory。这和上一篇 JPA 多数据源的"分包独立配置"是两种完全不同的思路，后面会详细对比。

---

## 二、项目结构

```
demo-multi-datasource-mybatis/
├── pom.xml
├── sql/db.sql                          # 建表脚本（主从两个库都要执行）
└── src/main/java/com/xkcoding/multi/datasource/mybatis/
    ├── SpringBootDemoMultiDatasourceMybatisApplication.java  # 启动类（@MapperScan）
    ├── mapper/
    │   └── UserMapper.java              # Mapper 接口（继承 BaseMapper）
    ├── model/
    │   └── User.java                    # 实体类
    └── service/
        ├── UserService.java             # 服务接口
        └── impl/
            └── UserServiceImpl.java     # 实现（@DS 切换数据源的核心）
```

相比上一篇 JPA 多数据源，这里**没有 `config` 包、没有多个 DataSourceConfig 配置类**——这正是注解切换方案的简洁之处。整个项目只有一个普通的 MyBatis-Plus 三层结构（Mapper → Service → 实体），多数据源的能力完全由 starter + 注解提供。

---

## 三、逐行拆解 `pom.xml`

```xml
<dependencies>
    <!-- 1. Spring Boot 基础 starter（注意：不是 starter-web，本模块无 Web 层） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 3. MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- 4. 核心：动态数据源 starter -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>dynamic-datasource-spring-boot-starter</artifactId>
        <version>2.5.0</version>
    </dependency>

    <!-- 5. MyBatis-Plus -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-boot-starter</artifactId>
        <version>3.1.0</version>
    </dependency>

    <!-- 6. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 7. Hutool + Guava 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>
</dependencies>
```

**关键依赖解读：**

- `dynamic-datasource-spring-boot-starter`：这是本模块的灵魂。它做了三件事：①读取 yml 里的多数据源配置并创建多个 `DataSource`；②提供一个 `DynamicRoutingDataSource`（动态路由数据源）作为主数据源；③提供 `@DS` 注解 + AOP 切面，在方法调用时根据注解值把对应数据源"塞进"当前线程。
- `mybatis-plus-boot-starter`：MyBatis-Plus 的整合包，提供 `BaseMapper`、`IService` 等通用 CRUD 能力。注意它和 dynamic-datasource 是**同一个团队（baomidou/苞米豆）**出品，所以天然兼容，配置项里有 `mp-enabled: true` 就是给 MyBatis-Plus 开的开关。
- `spring-boot-starter`（不是 web）：本模块没有 Controller，用测试类验证，所以只引基础 starter。

> 💡 前端类比：`dynamic-datasource` 就像一个"数据源路由器"，类比前端 axios 的请求拦截器——你在调用时打个标签（`@DS("slave")`），拦截器自动把请求路由到对应的 baseURL。你不用为每个后端单独建一个 axios 实例。

---

## 四、配置文件 `application.yml`

```yaml
spring:
  datasource:
    dynamic:
      datasource:
        master:                                    # 主库
          username: root
          password: root
          url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?useUnicode=true&characterEncoding=UTF-8&useSSL=false&autoReconnect=true&failOverReadOnly=false&serverTimezone=GMT%2B8
          driver-class-name: com.mysql.cj.jdbc.Driver
        slave:                                     # 从库
          username: root
          password: root
          url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo-2?useUnicode=true&characterEncoding=UTF-8&useSSL=false&autoReconnect=true&failOverReadOnly=false&serverTimezone=GMT%2B8
          driver-class-name: com.mysql.cj.jdbc.Driver
      mp-enabled: true                             # 开启 MyBatis-Plus 兼容
logging:
  level:
    com.xkcoding.multi.datasource.mybatis: debug   # 开启 debug 日志
```

**逐层解读：**

1. **数据源声明在 `spring.datasource.dynamic.datasource` 下**：这是 dynamic-datasource 的固定前缀。`master`、`slave` 是数据源的名字（自定义），每个下面是标准的连接四要素（url、username、password、driver）。

2. **两个库的区别**：注意 URL 里数据库名不同——主库是 `spring-boot-demo`，从库是 `spring-boot-demo-2`。这是两个独立的数据库实例（本 demo 为了演示，用同一个 MySQL 起了两个 schema）。

3. **`mp-enabled: true`**：开启与 MyBatis-Plus 的集成，让 `@DS` 能和 MyBatis-Plus 的 `BaseMapper`、`ServiceImpl` 协作。

4. **没有 `spring.datasource.url`**：注意这里**没有**传统的单数据源配置（`spring.datasource.url`），所有数据源都收在 `dynamic` 下。如果同时写了传统配置和 dynamic 配置，框架会以 dynamic 为准。

> ⚠️ 命名约定：`master` 是框架的默认数据源名（不写 `@DS` 时走它）。`slave` 是自定义名，你可以叫 `order-db`、`user-db` 任意名字，只要 `@DS` 里的值和这里对应即可。

---

## 五、逐行拆解启动类

```java
@SpringBootApplication
@MapperScan(basePackages = "com.xkcoding.multi.datasource.mybatis.mapper")
public class SpringBootDemoMultiDatasourceMybatisApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoMultiDatasourceMybatisApplication.class, args);
    }
}
```

- `@SpringBootApplication`：标准启动注解。
- `@MapperScan(basePackages = "...mapper")`：告诉 MyBatis 扫描哪个包下的 Mapper 接口。注意这里**只有一个 mapper 包**——不像 JPA 多数据源要按数据源分包（`dao.master`、`dao.slave`），注解切换方案下，所有 Mapper 可以放一起，因为切换靠 `@DS` 注解，不靠包路径。

> 💡 这是两种方案的核心差异：JPA 多数据源靠"分包"区分走哪个库，dynamic-datasource 靠"注解"区分。前者是静态绑定，后者是动态切换。

---

## 六、逐行拆解实体类 `User.java`

```java
@Data
@TableName("multi_user")
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User implements Serializable {
    private static final long serialVersionUID = -1923859222295750467L;

    @TableId(type = IdType.ID_WORKER)
    private Long id;

    private String name;

    private Integer age;
}
```

这是标准的 MyBatis-Plus 实体（在 `17-MyBatisPlus` 模块详细讲过）：

- `@TableName("multi_user")`：表名是 `multi_user`（实体叫 `User`，不满足驼峰下划线互转，所以显式指定）。
- `@TableId(type = IdType.ID_WORKER)`：主键用雪花算法生成（分布式唯一 ID）。
- `@Data` / `@NoArgsConstructor` / `@AllArgsConstructor` / `@Builder`：Lombok 注解，生成 getter/setter/构造器/链式构造。
- `implements Serializable`：实现序列化。多数据源场景下，对象可能在数据源间传递，实现序列化是好习惯。

> 💡 前端类比：`@Builder` 的链式构造类似 JS 的对象展开 `({...user, name: 'x'})`，`User.builder().name("主库添加").age(20).build()` 写起来很清爽。

---

## 七、逐行拆解 Mapper 与 Service

### 7.1 Mapper 接口

```java
public interface UserMapper extends BaseMapper<User> {
}
```

空接口，继承 `BaseMapper<User>` 就自动拥有了 `insert`、`deleteById`、`updateById`、`selectList` 等单表 CRUD 方法。这是 MyBatis-Plus 的核心能力（详见 `17-MyBatisPlus` 模块）。

### 7.2 Service 接口

```java
public interface UserService extends IService<User> {
    void addUser(User user);
}
```

继承 `IService<User>` 获得 `save`、`list`、`page` 等通用服务方法，自己额外声明了 `addUser`。

### 7.3 Service 实现 —— `@DS` 的核心

```java
@Service
@DS("slave")
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @DS("master")
    @Override
    public void addUser(User user) {
        baseMapper.insert(user);
    }
}
```

**这是整个模块最关键的类，逐行看：**

- `@Service`：注册为 Spring Bean。
- `@DS("slave")`（类上）：**类级别默认走 `slave` 从库**。这个类里所有方法，如果没有方法级 `@DS` 覆盖，都走 slave。
- `extends ServiceImpl<UserMapper, User>`：MyBatis-Plus 的服务实现基类，提供 `save`、`list` 等方法实现，并暴露 `baseMapper` 字段（就是注入的 `UserMapper`）。
- `@DS("master")`（方法上）：**这个方法走 `master` 主库**。方法级注解**优先级高于**类级注解，所以 `addUser` 走主库，而 `save`、`list` 等继承来的方法走从库。
- `baseMapper.insert(user)`：调用 Mapper 的插入方法。

**切换逻辑总结：**

| 方法 | 来源 | 走哪个库 | 原因 |
| --- | --- | --- | --- |
| `addUser` | 自定义 | **master** | 方法上有 `@DS("master")` |
| `save` | IService 继承 | **slave** | 方法上无注解，用类级 `@DS("slave")` |
| `list` | IService 继承 | **slave** | 同上 |

> 💡 前端类比：这就像给一个类的方法打"路由标签"。类上的 `@DS("slave")` 是默认 baseURL，方法上的 `@DS("master")` 是针对特定方法的覆盖——和 axios 实例 + 单独请求配置 baseURL 的思路一模一样。

---

## 八、测试类：验证主从切换

`UserServiceImplTest.java`：

```java
@Slf4j
public class UserServiceImplTest extends SpringBootDemoMultiDatasourceMybatisApplicationTests {
    @Autowired
    private UserService userService;

    @Test
    public void addUser() {
        User userMaster = User.builder().name("主库添加").age(20).build();
        userService.addUser(userMaster);   // 走 master（方法级 @DS）

        User userSlave = User.builder().name("从库添加").age(20).build();
        userService.save(userSlave);        // 走 slave（类级 @DS）
    }

    @Test
    public void testListUser() {
        List<User> list = userService.list(new QueryWrapper<>());  // 走 slave
        log.info("【list】= {}", JSONUtil.toJsonStr(list));
    }
}
```

- 继承 `SpringBootDemoMultiDatasourceMybatisApplicationTests`（里面有 `@SpringBootTest`），复用上下文配置。
- `addUser` 测试：分别往主库和从库插入数据。`addUser` 走 master，`save`（IService 默认实现）走 slave。
- `testListUser` 测试：从从库查询，验证读操作走 slave。

启动时控制台会看到数据源加载日志：

```
DynamicRoutingDataSource : 初始共加载 2 个数据源
DynamicRoutingDataSource : 动态数据源-加载 slave 成功
DynamicRoutingDataSource : 动态数据源-加载 master 成功
DynamicRoutingDataSource : 当前的默认数据源是单数据源，数据源名为 master
```

README 里强调的实践原则：**主库建议只做写（INSERT/UPDATE/DELETE），从库建议只做读（SELECT）**。这是读写分离的标准用法——本 demo 的 `@DS` 分布正好符合：写走 master，读走 slave。

---

## 九、动手练习

1. **加一个从库查询方法**：在 `UserServiceImpl` 里加一个 `@DS("master")` 的 `listFromMaster` 方法，对比从主库和从库查询的结果差异。
2. **加第三个数据源**：在 yml 里加一个 `log-db` 数据源（指向第三个库），写一个方法 `@DS("log-db")` 往里插数据，验证多数据源扩展。
3. **测试默认数据源**：写一个既没有类级也没有方法级 `@DS` 的 Service，验证它默认走 `master`。
4. **用 `@DS` 在方法内动态切换**：研究 `DynamicDataSourceContextHolder` 手动 push/poll 数据源的 API（不推荐，但了解原理）。
5. **对比 JPA 多数据源**：回顾 `43-多数据源_JPA`，把同一个"主写从读"需求用 JPA 分包方案实现一遍，体会两种方案的代码量差异。
6. **制造一个跨库事务**：在一个 `@Transactional` 方法里同时写 master 和 slave，观察事务是否生效（预期：不生效，跨库事务需要 XA/Seata）。

---

## 十、本模块知识点总结（结合实际开发详解）

多数据源是中大型项目的常见需求，但也是容易踩坑的地方。下面把核心知识点放到真实开发场景里讲透。

### 10.1 两种多数据源方案的本质区别

这是理解本模块的关键。两种方案不是"哪种更好"，而是**适用场景不同**：

| 维度 | 手动分包（JPA 多数据源） | 注解切换（dynamic-datasource） |
| --- | --- | --- |
| **切换时机** | 启动时静态绑定，每个 Mapper 固定属于一个库 | 运行时动态切换，同一个 Mapper 可走不同库 |
| **配置量** | 每个数据源一个配置类（DataSource + Factory + 包扫描） | yml 声明 + 一个 `@DS` 注解 |
| **灵活性** | 低（Mapper 和库强绑定） | 高（方法级切换） |
| **事务** | 各库独立事务，相对好控制 | 跨库事务难，`@Transactional` 只对当前切换的库生效 |
| **适合场景** | 库职责固定、长期不变 | 读写分离、需要动态路由 |
| **代表框架** | 手写 / Spring Data JPA 分包 | dynamic-datasource / AbstractRoutingDataSource |

**实际开发怎么选？**

- **读写分离** → 用注解切换（本模块方案）。因为同一个表的读写在 Service 层就要分流，注解最方便。
- **多业务库（用户库/订单库）** → 用手动分包。因为不同业务的表在不同库，且长期不变，静态绑定更清晰、事务更好管。
- **需要运行时动态决定走哪个库**（比如按租户路由） → 注解切换 + 编程式 `DynamicDataSourceContextHolder`。

**常见坑：**

- 混用两种方案：既用了 dynamic-datasource，又自己配了 `DataSource` Bean，导致冲突启动报错。**原则：用了 starter 就别再手动配数据源。**
- 以为 `@DS` 能解决跨库事务：在一个 `@Transactional` 方法里 `@DS("master")` 写 A 库、`@DS("slave")` 写 B 库，B 库的写操作不在事务里，失败不会回滚。跨库事务要用 Seata 等分布式事务框架。

> 💡 前端类比：手动分包像"每个后端一个 axios 实例，各自独立"，注解切换像"一个 axios 实例 + 请求拦截器动态改 baseURL"。前者实例隔离清晰，后者灵活但要注意"一个请求里别反复切 baseURL"。

### 10.2 `@DS` 注解的优先级与作用域

**作用域规则：**

1. **方法级 > 类级**：方法上有 `@DS` 就用方法的，没有就用类的，类也没有就走默认（master）。
2. **类级设置默认**：在 Service 类上打 `@DS("slave")`，整个类默认走从库，只有显式标 `@DS("master")` 的方法走主库。本 demo 就是这个用法。
3. **可以打在 Mapper 上**：`@DS` 也能加在 Mapper 接口或方法上，但一般打在 Service 层更合适（业务逻辑在哪层切换更清晰）。

**实际开发的最佳实践：**

1. **读写分离的标准姿势**：类上 `@DS("slave")`（默认读从库），写方法上 `@DS("master")`（写走主库）。这样读多写少的场景，大部分方法不用加注解，只有少数写方法要标注。
2. **避免在方法内部切换**：不要在一个方法里先 `@DS("a")` 再 `@DS("b")`——注解是方法级的，整个方法只会用进入时确定的那个数据源。要在方法内切，得用编程式 API。
3. **`@DS` 和 `@Transactional` 的顺序**：`@DS` 靠 AOP 切面切换数据源，`@Transactional` 靠 AOP 开启事务。如果事务切面先执行（绑定了一个数据源），`@DS` 再切换可能不生效。**建议：跨库操作不要放一个事务里。**

**常见坑：**

- `@DS` 加在 `private` 方法上不生效：Spring AOP 基于动态代理，`private` 方法不会被代理，注解失效。`@DS` 必须加在 `public` 方法上。
- `@DS` 的自调用失效：同一个类里 A 方法调 B 方法（B 上有 `@DS`），B 的注解不生效——因为自调用不走代理。和 `@Transactional`、`@Async` 是同一个坑。
- `@DS` 值写错：注解里写 `@DS("slaves")` 但 yml 里只有 `slave`，运行时报找不到数据源。

### 10.3 `DynamicRoutingDataSource` 的原理

dynamic-datasource 的核心是 `DynamicRoutingDataSource`，它继承自 Spring 的 `AbstractRoutingDataSource`。

**工作原理（简化版）：**

1. 启动时，starter 读取 yml，为每个数据源（master、slave）创建一个 `DataSource` 对象，存进一个 `Map<String, DataSource>`。
2. 它自己作为一个"门面" `DataSource` 注册进 Spring 容器，MyBatis 用的是这个门面。
3. 每次获取连接时，门面调用 `determineCurrentLookupKey()` 拿到一个 key（比如 "slave"），再从 Map 里取出对应的真实 `DataSource`，向它要连接。
4. `@DS` 的 AOP 切面在方法进入前，把 key（注解的值）放进一个 `ThreadLocal`（`DynamicDataSourceContextHolder`），方法结束后清理。`determineCurrentLookupKey()` 就是从这个 `ThreadLocal` 读 key。

> 💡 前端类比：这像一个"连接池路由器"——它本身不存连接，只是根据当前线程的"标签"（ThreadLocal 里的 key）把请求转发给真实的连接池。类比 Express 的路由中间件，根据 URL 把请求分发到不同 handler。

**关键点：ThreadLocal 隔离。** 每个线程有自己的数据源标签，互不干扰。这意味着：

- 在异步线程里（`@Async`、线程池）切换的数据源，不会影响主线程。
- 但如果父子线程要用同一数据源，需要手动传递（`DynamicDataSourceContextHolder` 提供了 push/poll 方法）。

### 10.4 读写分离的工程实践

读写分离听起来美好，但生产环境有几个关键点：

**1. 主从延迟问题：**

主库写入后，数据同步到从库有延迟（毫秒到秒级）。如果"写完立刻读"，可能读到从库的旧数据。解决方案：

- **强制读主库**：写完后的读操作临时 `@DS("master")`，绕过从库。
- **半同步复制**：MySQL 配置半同步，主库写入后至少等一个从库确认才返回，降低延迟。
- **业务容忍**：对延迟不敏感的场景（如报表、历史查询）直接走从库。

**2. 从库负载均衡：**

一个主库可能挂多个从库，读请求要在从库间分流。dynamic-datasource 支持用 `,` 分隔多从库：

```yaml
spring:
  datasource:
    dynamic:
      datasource:
        master: ...
        slave_1: ...
        slave_2: ...
```

配合 `@DS("slave")` 时，框架会在 `slave_1`、`slave_2` 间负载均衡（用 `slave` 作为组名前缀）。

**3. 主从一致性：**

生产环境的从库是真正的 MySQL 主从复制，不是本 demo 里的两个独立库。本 demo 为了演示，用两个 schema 模拟，数据完全不互通——这在真实环境是不对的，真实读写分离的前提是主从数据同步。

**常见坑：**

- 以为本 demo 的两个库会自动同步：不会。`spring-boot-demo` 和 `spring-boot-demo-2` 是两个独立库，写 master 的数据 slave 看不到。真实环境靠 MySQL binlog 复制。
- 从库挂了导致读全失败：生产要从库要有多个 + 健康检查，挂了自动剔除。

### 10.5 多数据源与事务的纠葛

这是多数据源最复杂的部分。Spring 的 `@Transactional` 管的是**一个数据源**的事务，多数据源下：

- 一个事务方法里切换了数据源，只有"进入事务时绑定的那个数据源"的操作在事务里，其他数据源的操作不在。
- 要实现跨库事务（A 库写成功 + B 库写成功，任一失败都回滚），需要**分布式事务**：

| 方案 | 特点 |
| --- | --- |
| **XA 协议**（两阶段提交） | 强一致，但性能差，MySQL 支持但很少用 |
| **Seata AT 模式** | 阿里开源，无侵入，性能较好，主流选择 |
| **Seata TCC/SAGA** | 业务侵入，适合复杂场景 |
| **最终一致（消息表）** | 本地消息表 + MQ，保证最终一致，最常用 |

**实际开发建议：**

1. **能不跨库就不跨库**：把强相关的表放一个库，避免跨库事务。
2. **必须跨库用最终一致**：用本地消息表 + MQ，A 库写业务 + 写消息表（同一事务），消息表异步发 MQ 通知 B 库，B 库消费后写。失败重试，保证最终一致。
3. **别指望 `@Transactional` 管多数据源**：它管不了，会埋雷。

### 10.6 dynamic-datasource 的高级能力

除了 `@DS`，这个框架还提供几个实用功能：

| 能力 | 用法 | 场景 |
| --- | --- | --- |
| **加载数据源** | 编程式 `dataSource.addDataSource(...)` | 运行时动态加库（多租户） |
| **移除数据源** | `dataSource.removeDataSource(...)` | 租户下线 |
| **`@DS` 加在类上做默认** | 本 demo 的用法 | 读写分离默认从库 |
| **嵌套切换** | `@DSTransactional` | 跨库事务（框架提供的简化版） |
| **Druid 监控集成** | 配置 `druid` 下各项 | 每个数据源独立监控面板 |

**实际开发应用：SaaS 多租户**

每个租户一个独立数据库，登录时根据租户 ID 动态加载数据源：

```java
// 租户登录时
DynamicRoutingDataSource ds = ...;
ds.addDataSource("tenant_" + tenantId, buildDataSource(tenantId));
// 后续请求带 @DS("tenant_xxx") 或用拦截器自动设置
```

这是 dynamic-datasource 相对手动分包的最大优势——**运行时动态增减数据源**，手动分包做不到。

### 10.7 MyBatis-Plus 与 dynamic-datasource 的协同

两者同属 baomidou 团队，集成度很高：

- `mp-enabled: true`：让 dynamic-datasource 兼容 MyBatis-Plus 的 `BaseMapper`、`ServiceImpl`。
- `BaseMapper` 的 CRUD 方法（`insert`、`selectList`）和 `@DS` 协作正常——`@DS` 切换数据源后，`BaseMapper` 的操作就走切换后的库。
- `ServiceImpl` 继承的方法（`save`、`list`）也能继承类上的 `@DS`，不用每个方法重写。

**常见坑：**

- `@MapperScan` 漏配：启动报 `Invalid bound statement` 或 Mapper 没注入。多数据源下 `@MapperScan` 还是只扫一个包（所有 Mapper 放一起），不用按库分包。
- MyBatis-Plus 版本和 dynamic-datasource 版本不匹配：两者要版本兼容，建议都用较新版本，老版本有已知 bug。

---

> 📌 **学习建议**：多数据源的核心不是"怎么配"，而是"什么时候该用、用了之后事务怎么办"。作为前端转后端的工程师，重点理解两点：一是 `@DS` 注解 + AOP + ThreadLocal 的动态切换原理（和前端 axios 拦截器改 baseURL 是同构思想），二是多数据源下事务的局限性（`@Transactional` 只管一个库，跨库要分布式事务）。建议把本模块和上一篇 `43-多数据源_JPA` 对照着看，一个"手动分包"、一个"注解切换"，理解透这两种方案，多数据源就入门了。生产环境记住一条：**读写分离用注解切换，多业务库用分包，跨库事务用最终一致**。
