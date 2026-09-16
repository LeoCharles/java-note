# 49 - Spring Boot 动态数据源

> 对应项目模块：`demo-dynamic-datasource`
> 前置知识：已学过多数据源模块（`43-多数据源_JPA`、`44-多数据源_MyBatis`）、AOP 模块（`06-AOP请求日志_LogAop`）、MyBatis 通用 Mapper 模块（`16-MyBatis通用Mapper与分页`）
> 学习目标：理解动态数据源与静态多数据源的本质区别，掌握运行时动态添加/删除/切换数据源的完整实现，能看懂 ThreadLocal + AOP + 自定义 DataSource 的协作机制。

---

## 一、本模块要解决什么问题？

前面 `43`、`44` 两个模块讲的是**静态多数据源**——数据源在项目启动时就确定好，写死在 `application.yml` 里，数量固定。但实际业务中有这样的场景：

- **SaaS 多租户**：每个租户一个独立数据库，租户数量动态增长，新签一个客户就要加一个库，不可能每次都改配置文件重启服务。
- **数据采集/ETL**：需要连接用户在页面上临时填写的数据库地址，拉取数据。
- **运维巡检**：管理员输入任意数据库连接信息，测试连通性、查询数据。

这些场景的共同点是：**数据源的连接信息在运行时才知道，数量不固定，需要动态增删**。本模块就演示如何通过接口动态添加/删除数据源、通过请求头动态切换数据源，并用 MyBatis 查询切换后的库。

> 💡 前端类比：静态多数据源像前端写死的多个 `baseURL`（`axios.create({baseURL: '/api-a'})`），动态数据源像运行时根据用户输入动态创建 axios 实例——地址是用户在页面上填的，数量不限。

### 1.1 动态 vs 静态多数据源对比

| 维度 | 静态多数据源（模块 43/44） | 动态数据源（本模块） |
| --- | --- | --- |
| 数据源数量 | 启动时固定 | 运行时动态增删 |
| 连接信息来源 | `application.yml` 写死 | 数据库表 / 接口传入 |
| 切换方式 | `@DS` 注解 / 分包 | 请求头 `Datasource-Config-Id` |
| 新增数据源 | 改配置 + 重启 | 调接口，热生效 |
| 实现复杂度 | 低（starter 搞定） | 高（自己实现路由） |
| 适用场景 | 读写分离、固定多库 | 多租户、数据采集 |

---

## 二、项目结构

```
demo-dynamic-datasource/
├── pom.xml
├── db/
│   ├── init.sql          # 建表 + 数据源配置初始数据
│   └── user.sql          # 各业务库的用户表数据
└── src/main/
    ├── java/com/xkcoding/dynamic/datasource/
    │   ├── SpringBootDemoDynamicDatasourceApplication.java  # 启动类（实现 CommandLineRunner）
    │   ├── annotation/
    │   │   └── DefaultDatasource.java       # 标记方法只用默认数据源
    │   ├── aspect/
    │   │   └── DatasourceSelectorAspect.java # AOP 切面：从请求头取数据源 id
    │   ├── config/
    │   │   ├── DatasourceConfiguration.java  # 注册自定义 DynamicDataSource
    │   │   ├── MybatisConfiguration.java      # 配置 SqlSessionFactory
    │   │   └── MyMapper.java                 # 通用 Mapper 基接口
    │   ├── controller/
    │   │   ├── DatasourceConfigController.java # 增删数据源配置
    │   │   └── UserController.java             # 查询用户（按数据源切换）
    │   ├── datasource/
    │   │   ├── DatasourceConfigContextHolder.java # ThreadLocal 存当前数据源 id
    │   │   ├── DynamicDataSource.java              # 自定义数据源（继承 HikariDataSource）
    │   │   ├── DatasourceHolder.java               # 数据源缓存 + 超时清理
    │   │   ├── DatasourceManager.java              # 单个数据源 + 最后使用时间
    │   │   ├── DatasourceConfigCache.java          # 数据源配置缓存
    │   │   └── DatasourceScheduler.java            # 定时清理调度器
    │   ├── mapper/
    │   │   ├── DatasourceConfigMapper.java
    │   │   └── UserMapper.java
    │   ├── model/
    │   │   ├── DatasourceConfig.java   # 数据源配置实体
    │   │   └── User.java
    │   └── utils/
    │       └── SpringUtil.java         # 静态获取 Spring Bean
    └── resources/
        └── application.yml
```

结构比前几个模块复杂不少，因为动态数据源需要自己实现一整套"路由 + 缓存 + 清理"机制。核心分为四层：

1. **配置层**（config）：把自定义的 `DynamicDataSource` 注册成 Spring Bean。
2. **路由层**（datasource）：ThreadLocal 记录当前线程要用哪个库，`DynamicDataSource` 在获取连接时按 id 路由。
3. **缓存层**（datasource）：用枚举单例缓存已创建的数据源和配置，定时清理超时的。
4. **切面层**（aspect）：AOP 拦截 Controller，从请求头取数据源 id 设到 ThreadLocal。

---

## 三、pom.xml 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-aop</artifactId>
    </dependency>
    <dependency>
        <groupId>tk.mybatis</groupId>
        <artifactId>mapper-spring-boot-starter</artifactId>
        <version>2.1.5</version>
    </dependency>
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
        <scope>runtime</scope>
    </dependency>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

关键依赖：

- `spring-boot-starter-aop`：动态数据源切换靠 AOP 拦截请求，必须引入。
- `mapper-spring-boot-starter`（tk.mybatis）：通用 Mapper，省去手写 SQL，`MyMapper<T>` 继承它就有 CRUD。
- 没有引 `spring-boot-starter-jdbc` 或 HikariCP——因为 tk.mybatis starter 间接引入了，且 Spring Boot 默认带 HikariCP。

> ⚠️ 注意：本模块**没有**用 `dynamic-datasource-spring-boot-starter`（模块 44 用的那个），而是**从零手写**动态数据源。这是为了让你理解底层原理——真正理解了本模块，再用 starter 就是"降维打击"。

---

## 四、配置文件与数据库脚本

### 4.1 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?useUnicode=true&characterEncoding=utf-8&useSSL=false
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
```

这里只配了**默认数据源**（存数据源配置表 `datasource_config` 的库）。其他数据源的连接信息不在 yml 里，而是存在默认库的 `datasource_config` 表里，启动时加载到缓存。

### 4.2 数据库脚本

`init.sql` 建配置表并插入两条数据源记录：

```sql
CREATE TABLE IF NOT EXISTS `datasource_config` (
    `id`       bigint(13)   NOT NULL AUTO_INCREMENT COMMENT '主键',
    `host`     varchar(255) NOT NULL COMMENT '数据库地址',
    `port`     int(6)       NOT NULL COMMENT '数据库端口',
    `username` varchar(100) NOT NULL COMMENT '数据库用户名',
    `password` varchar(100) NOT NULL COMMENT '数据库密码',
    `database` varchar(100) DEFAULT 0 COMMENT '数据库名称',
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8 COMMENT ='数据源配置表';

INSERT INTO `datasource_config`(`id`, `host`, `port`, `username`, `password`, `database`)
VALUES (1, '127.0.0.1', 3306, 'root', 'root', 'test');
INSERT INTO `datasource_config`(`id`, `host`, `port`, `username`, `password`, `database`)
VALUES (2, '192.168.239.4', 3306, 'dmcp', 'Dmcp321!', 'test');
```

`user.sql` 在每个业务库建用户表，插入不同数据以区分：

```sql
CREATE TABLE IF NOT EXISTS `test_user` (
    `id`   bigint(13)   NOT NULL AUTO_INCREMENT COMMENT '主键',
    `name` varchar(255) NOT NULL COMMENT '姓名',
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8 COMMENT ='用户表';

-- 默认数据库：默认数据库用户1/2
-- 测试库1：测试库1用户1/2
-- 测试库2：测试库2用户1/2
```

这样查询不同数据源时，返回的用户名不同，能直观验证切换生效。

---

## 五、逐行拆解核心代码

### 5.1 实体模型

`DatasourceConfig.java`（数据源配置实体）：

```java
@Data
@Table(name = "datasource_config")
public class DatasourceConfig implements Serializable {
    @Id
    @Column(name = "`id`")
    @GeneratedValue(generator = "JDBC")
    private Long id;
    @Column(name = "`host`")
    private String host;
    @Column(name = "`port`")
    private Integer port;
    @Column(name = "`username`")
    private String username;
    @Column(name = "`password`")
    private String password;
    @Column(name = "`database`")
    private String database;

    /**
     * 构造JDBC URL
     */
    public String buildJdbcUrl() {
        return String.format("jdbc:mysql://%s:%s/%s?useUnicode=true&characterEncoding=utf-8&useSSL=false",
                this.host, this.port, this.database);
    }
}
```

- `@Table` / `@Column` / `@Id` 是 JPA 注解，tk.mybatis 通用 Mapper 复用它们做表-实体映射。
- 字段名 `database` 是 SQL 关键字，用 `` `database` `` 反引号包裹避免冲突。
- `buildJdbcUrl()` 把 host/port/database 拼成标准 JDBC URL——这是动态建库的关键，配置表存的是散字段，用时拼成 URL。

`User.java` 同理，映射 `test_user` 表，字段简单（id + name）。

### 5.2 通用 Mapper 基接口

`MyMapper.java`：

```java
@RegisterMapper
public interface MyMapper<T> extends Mapper<T>, MySqlMapper<T> {
}
```

- 继承 tk.mybatis 的 `Mapper<T>` 和 `MySqlMapper<T>`，自动获得 `selectAll()`、`insertUseGeneratedKeys()`、`deleteByPrimaryKey()` 等通用方法。
- `@RegisterMapper` 让 tk.mybatis 扫描注册这个基接口，所有继承它的 Mapper 都自动有 CRUD。

具体 Mapper 只需空继承：

```java
@Mapper
public interface UserMapper extends MyMapper<User> {}
```

无需写任何 SQL，`userMapper.selectAll()` 直接查全表。

### 5.3 配置层：注册自定义数据源

`DatasourceConfiguration.java`：

```java
@Configuration
public class DatasourceConfiguration {
    @Bean
    @ConfigurationProperties(prefix = "spring.datasource")
    public DataSource dataSource() {
        DataSourceBuilder<?> dataSourceBuilder = DataSourceBuilder.create();
        dataSourceBuilder.type(DynamicDataSource.class);  // 关键：用自定义的 DynamicDataSource
        return dataSourceBuilder.build();
    }
}
```

- `@ConfigurationProperties(prefix = "spring.datasource")`：把 yml 里 `spring.datasource.*` 的 url/username/password 绑定到这个 Bean 的属性上。
- `DataSourceBuilder.create().type(DynamicDataSource.class)`：指定数据源类型为我们自定义的 `DynamicDataSource`（而不是默认的 HikariDataSource）。
- 这样 Spring 容器里的 `DataSource` 就是我们的 `DynamicDataSource`，MyBatis 用它获取连接时，会走我们重写的 `getConnection()`。

> 💡 这是整个动态数据源的核心 trick：**用一个自定义的 DataSource 包一层，在获取连接时根据 ThreadLocal 决定真正用哪个底层库**。前端类比：像写一个 `ProxyAxios`，`proxy.request()` 时根据上下文决定真正请求哪个 baseURL。

`MybatisConfiguration.java`：

```java
@Configuration
@MapperScan(basePackages = "com.xkcoding.dynamic.datasource.mapper", sqlSessionFactoryRef = "sqlSessionFactory")
public class MybatisConfiguration {
    @Bean(name = "sqlSessionFactory")
    @SneakyThrows
    public SqlSessionFactory getSqlSessionFactory(@Qualifier("dataSource") DataSource dataSource) {
        SqlSessionFactoryBean bean = new SqlSessionFactoryBean();
        bean.setDataSource(dataSource);
        return bean.getObject();
    }
}
```

- 手动配置 `SqlSessionFactory`，把上面的 `DynamicDataSource` 注入给它。
- `@MapperScan` 指定扫描 mapper 包，绑定到这个 SqlSessionFactory。
- `@SneakyThrows`（Lombok）把受检异常偷渡成运行时异常，省去 try-catch。

### 5.4 路由层：ThreadLocal 记录当前数据源

`DatasourceConfigContextHolder.java`：

```java
public class DatasourceConfigContextHolder {
    private static final ThreadLocal<Long> DATASOURCE_HOLDER =
            ThreadLocal.withInitial(() -> DatasourceHolder.DEFAULT_ID);

    public static void setDefaultDatasource() {
        DATASOURCE_HOLDER.remove();
        setCurrentDatasourceConfig(DatasourceHolder.DEFAULT_ID);
    }

    public static Long getCurrentDatasourceConfig() {
        return DATASOURCE_HOLDER.get();
    }

    public static void setCurrentDatasourceConfig(Long id) {
        DATASOURCE_HOLDER.set(id);
    }
}
```

- 用 `ThreadLocal<Long>` 存当前线程要用的数据源 id（默认 `-1L`，即默认库）。
- `ThreadLocal` 保证每个线程的值互不干扰——A 线程切到库 1，B 线程仍用默认库。
- `setDefaultDatasource()` 先 `remove()` 再 set，确保清理旧值。

> 💡 前端类比：`ThreadLocal` 像 Node.js 的 `AsyncLocalStorage`，或 React 的 `useContext`——每个请求（线程）有独立的"上下文"，切换数据源的设置只影响当前请求，不会串到别的请求。这是 Web 请求隔离的关键。

> ⚠️ **ThreadLocal 内存泄漏坑**：用完必须 `remove()`。本模块在 AOP 的 `@AfterReturning` 里调 `setDefaultDatasource()`（内部 remove）来清理。如果忘了清理，线程被线程池复用时，上一个请求的数据源设置会泄漏到下一个请求。这是 Tomcat 线程池场景下最经典的坑。

### 5.5 核心路由：DynamicDataSource

`DynamicDataSource.java`：

```java
@Slf4j
public class DynamicDataSource extends HikariDataSource {
    @Override
    public Connection getConnection() throws SQLException {
        // 1. 获取当前线程的数据源 id
        Long id = DatasourceConfigContextHolder.getCurrentDatasourceConfig();
        // 2. 根据 id 从缓存找数据源
        HikariDataSource datasource = DatasourceHolder.INSTANCE.getDatasource(id);
        // 3. 缓存没有就初始化一个
        if (null == datasource) {
            datasource = initDatasource(id);
        }
        // 4. 从底层真实数据源获取连接
        return datasource.getConnection();
    }

    private HikariDataSource initDatasource(Long id) {
        HikariDataSource dataSource = new HikariDataSource();
        if (DatasourceHolder.DEFAULT_ID.equals(id)) {
            // 默认库：从 application.yml 配置读
            DataSourceProperties properties = SpringUtil.getBean(DataSourceProperties.class);
            dataSource.setJdbcUrl(properties.getUrl());
            dataSource.setUsername(properties.getUsername());
            dataSource.setPassword(properties.getPassword());
            dataSource.setDriverClassName("com.mysql.cj.jdbc.Driver");
        } else {
            // 动态库：从配置缓存读
            DatasourceConfig datasourceConfig = DatasourceConfigCache.INSTANCE.getConfig(id);
            if (datasourceConfig == null) {
                throw new RuntimeException("无此数据源");
            }
            dataSource.setJdbcUrl(datasourceConfig.buildJdbcUrl());
            dataSource.setUsername(datasourceConfig.getUsername());
            dataSource.setPassword(datasourceConfig.getPassword());
            dataSource.setDriverClassName("com.mysql.cj.jdbc.Driver");
        }
        // 创建后放进缓存，下次直接命中
        DatasourceHolder.INSTANCE.addDatasource(id, dataSource);
        return dataSource;
    }
}
```

这是整个模块的"心脏"，逻辑分四步：

1. 从 ThreadLocal 拿当前请求要用的数据源 id。
2. 拿这个 id 去缓存（`DatasourceHolder`）找已创建好的 `HikariDataSource`。
3. 没找到就 `initDatasource` 创建一个：默认库读 yml 配置，动态库读配置缓存。
4. 从找到/创建的真实数据源获取 Connection 返回。

**关键设计：`DynamicDataSource` 本身不真正持有连接池，它是个"路由器"/"代理"。** 它继承 `HikariDataSource`（为了能被 `DataSourceBuilder` 创建），但重写了 `getConnection()`，把获取连接的职责委托给内部缓存的真正数据源。

> 💡 前端类比：这像写一个 `ProxyDataSource` 代理对象，对外暴露 `getConnection()`，内部根据上下文把调用转发到不同的真实实例。和前端的 Proxy 对象 / 拦截器思想完全一致。

> ⚠️ 注意 `SpringUtil.getBean(DataSourceProperties.class)`：在 `initDatasource` 里需要从 Spring 容器拿 `DataSourceProperties`，但 `DynamicDataSource` 是 `new` 出来的（不是 Spring 管理的），没法用 `@Autowired`。所以用 `SpringUtil` 这个工具类静态获取 Bean。

### 5.6 缓存层：数据源管理与超时清理

`DatasourceHolder.java`（数据源缓存，枚举单例）：

```java
public enum DatasourceHolder {
    INSTANCE;

    DatasourceHolder() {
        // 启动时定时清理，每5分钟一次
        DatasourceScheduler.INSTANCE.schedule(this::clearExpiredDatasource, 5 * 60 * 1000);
    }

    public static final Long DEFAULT_ID = -1L;
    private static final Map<Long, DatasourceManager> DATASOURCE_CACHE = new ConcurrentHashMap<>();

    public synchronized void addDatasource(Long id, HikariDataSource dataSource) {
        DATASOURCE_CACHE.put(id, new DatasourceManager(dataSource));
    }

    public synchronized HikariDataSource getDatasource(Long id) {
        if (DATASOURCE_CACHE.containsKey(id)) {
            DatasourceManager manager = DATASOURCE_CACHE.get(id);
            manager.refreshTime();  // 命中时刷新最后使用时间
            return manager.getDataSource();
        }
        return null;
    }

    public synchronized void clearExpiredDatasource() {
        DATASOURCE_CACHE.forEach((k, v) -> {
            if (!DEFAULT_ID.equals(k) && v.isExpired()) {  // 默认库不清理
                DATASOURCE_CACHE.remove(k);
            }
        });
    }

    public synchronized void removeDatasource(Long id) {
        if (DATASOURCE_CACHE.containsKey(id)) {
            DATASOURCE_CACHE.get(id).getDataSource().close();  // 关闭连接池
            DATASOURCE_CACHE.remove(id);
        }
    }
}
```

- 用**枚举单例**（`enum INSTANCE`）保证全局唯一的缓存实例。枚举单例是 Java 实现单例最安全的方式，天然防反射破坏、防序列化重建。
- `ConcurrentHashMap` 存数据源，`synchronizedynchronized` 方法保证线程安全。
- **超时清理机制**：启动时注册定时任务，每 5 分钟扫一遍，超过 10 分钟没用的非默认数据源会被 `close()` 并移除——避免大量临时数据源耗尽连接资源。

`DatasourceManager.java`（单个数据源 + 最后使用时间）：

```java
public class DatasourceManager {
    private static final Long DEFAULT_RELEASE = 10L;  // 10分钟不用就过期
    @Getter
    private HikariDataSource dataSource;
    private LocalDateTime lastUseTime;

    public DatasourceManager(HikariDataSource dataSource) {
        this.dataSource = dataSource;
        this.lastUseTime = LocalDateTime.now();
    }

    public boolean isExpired() {
        if (LocalDateTime.now().isBefore(this.lastUseTime.plusMinutes(DEFAULT_RELEASE))) {
            return false;  // 没过期
        }
        this.dataSource.close();  // 过期就关闭
        return true;
    }

    public void refreshTime() {
        this.lastUseTime = LocalDateTime.now();
    }
}
```

每次 `getDatasource` 命中时调 `refreshTime()` 续命，长期不用就 `close()` 释放。这是动态数据源**资源管理**的关键——动态创建的数据源不能无限堆积，必须有回收机制。

`DatasourceConfigCache.java`（配置缓存，同样枚举单例）：

```java
public enum DatasourceConfigCache {
    INSTANCE;
    private static final Map<Long, DatasourceConfig> CONFIG_CACHE = new ConcurrentHashMap<>();

    public synchronized void addConfig(Long id, DatasourceConfig config) { ... }
    public synchronized DatasourceConfig getConfig(Long id) { ... }
    public synchronized void removeConfig(Long id) {
        CONFIG_CACHE.remove(id);
        DatasourceHolder.INSTANCE.removeDatasource(id);  // 同步清理数据源
    }
}
```

缓存的是数据源**配置信息**（host/port/账号密码），用于 `initDatasource` 时拼 URL。删除配置时同步删除已创建的数据源。

`DatasourceScheduler.java`（定时调度器）：

```java
public enum DatasourceScheduler {
    INSTANCE;
    private ScheduledExecutorService scheduler;

    DatasourceScheduler() {
        create();
    }
    private void create() {
        this.scheduler = new ScheduledThreadPoolExecutor(10,
                r -> new Thread(r, "Datasource-Release-Task-" + ...));
    }
    public void schedule(Runnable task, long delay) {
        this.scheduler.scheduleAtFixedRate(task, delay, delay, TimeUnit.MILLISECONDS);
    }
}
```

用 `ScheduledThreadPoolExecutor` 做定时任务，每 5 分钟跑一次清理。这里没用 Spring 的 `@Scheduled`，因为这些类是 `new` 出来的（非 Spring Bean），用不了 Spring 注解，所以直接用 JDK 的调度器。

### 5.7 切面层：AOP 从请求头取数据源 id

`DatasourceSelectorAspect.java`：

```java
@Aspect
@Component
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class DatasourceSelectorAspect {
    @Pointcut("execution(public * com.xkcoding.dynamic.datasource.controller.*.*(..))")
    public void datasourcePointcut() {}

    @Before("datasourcePointcut()")
    public void doBefore(JoinPoint joinPoint) {
        Method method = ((MethodSignature) joinPoint.getSignature()).getMethod();
        // 1. 如果方法标了 @DefaultDatasource，强制用默认库
        DefaultDatasource annotation = method.getAnnotation(DefaultDatasource.class);
        if (null != annotation) {
            DatasourceConfigContextHolder.setDefaultDatasource();
            return;
        }
        // 2. 否则从请求头取 Datasource-Config-Id
        HttpServletRequest request = ((ServletRequestAttributes)
                RequestContextHolder.getRequestAttributes()).getRequest();
        String configIdInHeader = request.getHeader("Datasource-Config-Id");
        if (StringUtils.hasText(configIdInHeader)) {
            DatasourceConfigContextHolder.setCurrentDatasourceConfig(Long.parseLong(configIdInHeader));
        } else {
            DatasourceConfigContextHolder.setDefaultDatasource();  // 没传就用默认
        }
    }

    @AfterReturning("datasourcePointcut()")
    public void doAfter() {
        DatasourceConfigContextHolder.setDefaultDatasource();  // 用完清理 ThreadLocal
    }
}
```

这是动态切换的入口：

- `@Pointcut` 拦截 controller 包下所有方法。
- `@Before` 在方法执行前：先看方法有没有 `@DefaultDatasource` 注解，有就强制默认库；否则从 HTTP 请求头 `Datasource-Config-Id` 取数据源 id 设到 ThreadLocal。
- `@AfterReturning` 在方法返回后：清理 ThreadLocal，防止线程复用导致泄漏。

> 💡 前端类比：这像 axios 的请求拦截器——每个请求发出前，从请求配置里取一个标识，塞到"请求上下文"里，后端处理时就能读到。这里请求头 `Datasource-Config-Id` 就是前端传的"用哪个库"的标识。

`DefaultDatasource.java`（注解）：

```java
@Target({ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DefaultDatasource {
}
```

标记方法只能用默认数据源。比如"增删数据源配置"这种管理操作，必须操作默认库（配置表在默认库），不能被请求头切走，否则配置表都找不到了。

### 5.8 Controller 层

`UserController.java`（业务查询，可切换数据源）：

```java
@RestController
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class UserController {
    private final UserMapper userMapper;

    @GetMapping("/user")
    public List<User> getUserList() {
        return userMapper.selectAll();
    }
}
```

没标 `@DefaultDatasource`，所以会被请求头 `Datasource-Config-Id` 影响——传 1 查库 1，传 2 查库 2，不传查默认库。

`DatasourceConfigController.java`（数据源配置管理，强制默认库）：

```java
@RestController
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class DatasourceConfigController {
    private final DatasourceConfigMapper configMapper;

    @PostMapping("/config")
    @DefaultDatasource  // 强制默认库
    public DatasourceConfig insertConfig(@RequestBody DatasourceConfig config) {
        configMapper.insertUseGeneratedKeys(config);
        DatasourceConfigCache.INSTANCE.addConfig(config.getId(), config);  // 同步加缓存
        return config;
    }

    @DeleteMapping("/config/{id}")
    @DefaultDatasource
    public void removeConfig(@PathVariable Long id) {
        configMapper.deleteByPrimaryKey(id);
        DatasourceConfigCache.INSTANCE.removeConfig(id);  // 同步删缓存+数据源
    }
}
```

增删数据源配置时：写库 + 更新缓存，保证缓存与数据库一致。

### 5.9 启动类：预加载配置

`SpringBootDemoDynamicDatasourceApplication.java`：

```java
@SpringBootApplication
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class SpringBootDemoDynamicDatasourceApplication implements CommandLineRunner {
    private final DatasourceConfigMapper configMapper;

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoDynamicDatasourceApplication.class, args);
    }

    @Override
    public void run(String... args) {
        DatasourceConfigContextHolder.setDefaultDatasource();
        List<DatasourceConfig> datasourceConfigs = configMapper.selectAll();
        System.out.println("加载其余数据源配置列表: " + datasourceConfigs);
        datasourceConfigs.forEach(config ->
                DatasourceConfigCache.INSTANCE.addConfig(config.getId(), config));
    }
}
```

- 实现 `CommandLineRunner`，启动完成后执行 `run()`。
- 先设默认数据源，再从默认库查所有数据源配置，加载到 `DatasourceConfigCache` 缓存。
- 这样启动后所有已配置的数据源都可用，不用等第一次请求才加载。

### 5.10 SpringUtil：静态获取 Bean

`SpringUtil.java` 实现 `ApplicationContextAware`，在 Spring 启动时把 ApplicationContext 存到静态变量，之后任何地方（包括非 Spring 管理的对象，如 `DynamicDataSource`）都能用 `SpringUtil.getBean(Class)` 静态获取 Bean。这是动态数据源里 `initDatasource` 能拿到 `DataSourceProperties` 的关键。

---

## 六、运行与验证

### 6.1 环境准备

1. 建默认库 `spring-boot-demo`，执行 `init.sql`（建配置表 + 插数据源记录）。
2. 建业务库 `test`（id=1）、另一个库（id=2），各自执行 `user.sql`。
3. 启动项目，控制台应打印 `加载其余数据源配置列表: [...]`。

### 6.2 接口测试

| 操作 | 请求 | 说明 |
| --- | --- | --- |
| 查默认库用户 | `GET /demo/user` | 不带头，查默认库 |
| 查库1用户 | `GET /demo/user`，头 `Datasource-Config-Id: 1` | 查 id=1 的库 |
| 查库2用户 | `GET /demo/user`，头 `Datasource-Config-Id: 2` | 查 id=2 的库 |
| 新增数据源 | `POST /demo/config`，body `{"host":"...","port":3306,...}` | 加一条配置 + 缓存 |
| 删除数据源 | `DELETE /demo/config/1` | 删配置 + 缓存 + 已建数据源 |

不同库返回的用户名不同（默认库用户1/2、测试库1用户1/2…），可直观验证切换生效。

---

## 七、动手练习

1. **验证切换**：用同一个 `GET /user` 接口，分别带 `Datasource-Config-Id: 1` 和 `2`，对比返回数据。
2. **动态新增**：`POST /config` 加一个指向你本机其他库的数据源，立即用新 id 查询，验证热生效（不用重启）。
3. **验证超时清理**：把 `DatasourceManager.DEFAULT_RELEASE` 改成 1 分钟，等 6 分钟后看日志/缓存是否被清。
4. **加异常处理**：传一个不存在的数据源 id，当前会抛 `RuntimeException("无此数据源")`，改成返回友好 JSON 提示。
5. **改用注解切换**：仿照 `@DefaultDatasource`，写一个 `@Datasource("1")` 注解，在方法上指定固定数据源，AOP 里优先读注解。
6. **对比 starter**：理解本模块后，回头看模块 44 的 `dynamic-datasource-spring-boot-starter`，体会 starter 把这些手写逻辑封装成了什么。

---

## 八、本模块知识点总结（结合实际开发详解）

动态数据源是"多数据源"主题里最复杂的一种，它把 ThreadLocal、AOP、自定义 DataSource、单例缓存、定时清理这些技术点揉在一起。下面逐个讲透。

### 8.1 动态数据源的核心套路：路由 DataSource + ThreadLocal

**实际开发中，所有动态数据源方案的本质都是同一个套路：**

1. 写一个自定义 `DataSource`（继承或包装一个真实数据源），重写 `getConnection()`。
2. 用 `ThreadLocal` 存当前线程要用哪个库的标识。
3. 在 `getConnection()` 里读 ThreadLocal，路由到对应的真实数据源。
4. 用 AOP / 注解 / 拦截器在请求开始时设置 ThreadLocal，结束时清理。

Spring 提供的 `AbstractRoutingDataSource` 就是这个套路的官方实现——你只需继承它，实现 `determineCurrentLookupKey()` 返回当前 key，它帮你做路由。本模块没用它，而是自己继承 `HikariDataSource` 手写，但思想一致。

**最佳实践：**

- 如果只是简单的静态多库，用 `AbstractRoutingDataSource` 或 `dynamic-datasource-spring-boot-starter`，别手写。
- 如果有"运行时动态增删数据源"需求（多租户、数据采集），才需要像本模块这样手写缓存 + 清理机制。
- 路由 DataSource 要做成无状态的路由器，真正的连接池放在内部 Map 里按 key 存。

**常见坑：**

- 在 `getConnection()` 里直接 `new HikariDataSource()` 不缓存——每次请求都新建连接池，性能灾难且连接耗尽。必须缓存。
- 忘了清理 ThreadLocal，线程池复用线程导致数据源串用。务必在 `@AfterReturning` 或 `finally` 里清理。

### 8.2 ThreadLocal：请求级数据隔离的关键

**实际开发中 ThreadLocal 的典型用途：**

- 动态数据源切换（本模块）
- 链路追踪 traceId 传递
- 用户登录态传递（替代层层传参）
- 事务管理（Spring 的 `TransactionSynchronizationManager` 就用 ThreadLocal）

**最佳实践：**

- 用 `ThreadLocal.withInitial(() -> 默认值)` 带默认值，避免空指针。
- **用完一定 `remove()`**，尤其在 Web 容器线程池场景。推荐用 `try-finally` 或 AOP 后置通知保证清理。
- 不要往 ThreadLocal 放大对象，防止内存占用高。

**常见坑：**

- **内存泄漏**：`ThreadLocal` 的 Entry 是弱引用 key、强引用 value。key 被回收后 value 仍在，线程池线程长期存活导致 value 不释放。解决：用完 remove。
- **父子线程不传递**：普通 ThreadLocal 在线程池/异步场景下，子线程读不到父线程的值。需要 `InheritableThreadLocal` 或 `TransmittableThreadLocal`（阿里开源，解决线程池传递）。
- **异步场景失效**：`@Async` / CompletableFuture 切换线程后，ThreadLocal 值丢失。动态数据源在异步方法里会失效，需要手动传递或用 `TransmittableThreadLocal`。

### 8.3 枚举单例：Java 最安全的单例实现

本模块的 `DatasourceHolder`、`DatasourceConfigCache`、`DatasourceScheduler` 都用 `enum INSTANCE` 实现单例。

**为什么用枚举单例？**

- **天然线程安全**：JVM 保证枚举实例的初始化是线程安全的。
- **防反射破坏**：JVM 规范禁止反射创建枚举对象，`Constructor#newInstance` 对枚举直接抛异常。
- **防序列化重建**：枚举的序列化机制保证反序列化返回同一个实例，不会创建新对象。
- **代码简洁**：一行 `INSTANCE;` 搞定，不用写 `getInstance()`、双重检查锁。

**实际开发选择：**

| 单例实现 | 评价 | 适用 |
| --- | --- | --- |
| 枚举单例 | 最安全、最简洁 | 无依赖的纯逻辑单例 |
| `@Component` + Spring | 容器管理、可注入依赖 | 需要 Spring 依赖的单例 |
| 双重检查锁（DCL） | 经典但易写错 | 懒加载场景 |

**常见坑：**

- 枚举单例**没法注入 Spring 依赖**（因为不是 Spring 管理的），本模块用 `SpringUtil.getBean()` 绕过。如果单例需要大量 Spring 依赖，不如直接用 `@Component`。
- 枚举单例在单元测试时不好 Mock，测试友好度不如 Spring Bean。

### 8.4 自定义 DataSource：代理模式的运用

`DynamicDataSource extends HikariDataSource` 并重写 `getConnection()`，这是典型的**代理模式**——对外暴露相同接口，内部转发到不同真实对象。

**实际开发中的同类设计：**

- `AbstractRoutingDataSource`：Spring 提供的路由数据源基类。
- `LazyConnectionDataSourceProxy`：Spring 提供的延迟获取连接代理，事务开始时不立即拿连接，直到第一次 SQL 才拿，减少连接占用时间。
- 读写分离的 `MasterSlaveDataSource`：按操作类型路由主库/从库。

**最佳实践：**

- 代理 DataSource 要做成"瘦"路由器，不持有真实连接池，只做转发。
- 真实数据源放在 Map 里按 key 存，按需创建、超时回收。
- 重写 `getConnection()` 时注意事务：如果开了事务，一个事务内多次 getConnection 应返回同一连接，否则事务失效。Spring 的事务管理器会通过 `ConnectionHolder` 保证这一点，但要确保代理 DataSource 和事务管理器配合正确。

**常见坑：**

- 代理 DataSource + `@Transactional`：动态切换数据源必须在事务开启**之前**设置 ThreadLocal，否则事务已绑定了旧库的连接，切不动了。这也是为什么本模块用 `@Before`（请求最早期）设置，而不是在 Service 方法里设置。
- 忘记关闭真实数据源：动态删除数据源时只从 Map 移除，没调 `dataSource.close()`，连接池资源泄漏。本模块 `removeDatasource` 正确地先 close 再 remove。

### 8.5 资源回收：动态数据源的生命周期管理

动态创建的数据源不能无限堆积，必须有回收机制。本模块的做法：每个数据源记"最后使用时间"，定时扫描，超 10 分钟没用的就 close + 移除。

**实际开发中的资源回收策略：**

- **基于时间过期**（本模块）：空闲超时回收，适合临时数据源。
- **基于引用计数**：没人引用就回收，需配合引用队列。
- **基于容量上限**：缓存满时按 LRU 淘汰最久未用的。
- **手动删除**：用户主动删数据源时立即回收。

**最佳实践：**

- 默认库（核心配置库）永远不回收，只回收动态业务库。
- 回收时务必 `close()` 真实数据源，否则连接池线程、socket 都会泄漏。
- 定时任务用独立的 `ScheduledExecutorService`，不要和业务线程池混用，避免清理任务被业务阻塞。

**常见坑：**

- 回收时正在被使用的连接被中断：应在 `close()` 前等正在执行的查询完成，或用软关闭。HikariCP 的 `close()` 会优雅等待活跃连接结束。
- 清理任务自己抛异常导致调度停止：`scheduleAtFixedRate` 任务里必须 try-catch，否则后续不再执行。

### 8.6 AOP + 注解：声明式数据源切换

本模块用 `@DefaultDatasource` 注解标记"只能用默认库"的方法，AOP 优先读注解。这是声明式控制的典型用法。

**实际开发中更常见的注解设计：**

```java
@DS("slave")          // 指定用 slave 库
@DS("#tenantId")      // SpEL 动态表达式，从参数取
@Master               // 强制主库
@Slave                // 强制从库
```

`dynamic-datasource-spring-boot-starter` 就提供了 `@DS` 注解，支持 SpEL、类级/方法级优先级、嵌套切换等。

**最佳实践：**

- 注解优先级：方法级 > 类级 > 默认。
- 注解 + AOP 适合"静态已知"的切换（方法上写死用哪个库）；运行时动态的（请求头传 id）还是用本模块这种 AOP 读请求头的方式。
- 切换注解加在 Service 层而非 Controller 层更合适，因为数据源选择是业务逻辑，Controller 不该感知。本模块加在 Controller 是为了演示，实际项目应挪到 Service。

**常见坑：**

- AOP 自调用失效：同类里 A 方法调 B 方法，B 上的 `@DS` 不生效（没走代理）。和 `@Async`、`@Transactional` 同样的坑。解决：拆到两个类，或注入自身代理。
- `@DS` + `@Transactional` 顺序：事务先于数据源切换生效会导致切换失败，需要确保 AOP 顺序正确（数据源切面优先级高于事务切面）。

### 8.7 动态数据源 vs 配置中心 vs 多租户中间件

**实际开发中，"动态数据源"需求往往有更成熟的方案：**

| 方案 | 适用场景 | 代表 |
| --- | --- | --- |
| 本模块手写 | 学习原理、简单动态库 | - |
| `dynamic-datasource-starter` | 静态多库 + 简单动态 | mybatis-plus 团队 |
| 配置中心 + 热更新 | 数据源信息集中管理 | Nacos / Apollo |
| 多租户中间件 | SaaS 多租户隔离 | 飞致云 `Tenant-Manager` |
| ShardingSphere | 分库分表 + 读写分离 | Apache ShardingSphere |

**选型建议：**

- 如果只是读写分离或固定几个库，用 `dynamic-datasource-starter` + `@DS`，别手写。
- 如果是 SaaS 多租户，每租户独立库，用专门的多租户中间件，它们处理了租户识别、数据源路由、资源隔离、租户上下文传递等完整问题。
- 如果是"用户临时输入库地址查数据"这种工具场景，本模块的手写方案反而最合适——轻量、可控。

**本模块的学习价值：** 不在于让你在生产手写动态数据源，而在于让你**理解底层原理**——ThreadLocal 隔离、代理 DataSource 路由、AOP 声明式切换、资源回收。理解了这些，用任何 starter 或中间件都能知其然且知其所以然。

---

> 📌 **学习建议**：动态数据源是前面多个知识点的"综合应用"——ThreadLocal（请求隔离）、AOP（声明式切换）、自定义 DataSource（代理模式）、枚举单例（缓存管理）、定时任务（资源回收）。如果某个点没看懂，回头补对应的前 sleep 模块。作为前端转后端的同学，重点体会"代理 + 上下文"这个后端高频套路：用一个代理对象对外暴露统一接口，内部根据上下文（ThreadLocal/请求头/注解）路由到不同实现。这个套路在事务、缓存、数据源、日志、权限里反复出现，掌握它就掌握了后端设计的半壁江山。
