# 43 - JPA 多数据源配置

> 对应项目模块：`demo-multi-datasource-jpa`
> 前置知识：已学完 `14-数据库操作_JPA`，了解 Spring Data JPA 的基本用法（Entity、Repository、自动配置）
> 学习目标：理解为什么需要多数据源、JPA 多数据源的核心配置套路（DataSource + EntityManagerFactory + TransactionManager 三件套）、`@Primary` 和 `@Qualifier` 的作用，能独立为项目配置多个数据库连接。

---

## 一、本模块要解决什么问题？

前面的 JPA 模块里，一个项目只连一个数据库，Spring Boot 的自动配置帮你把 `DataSource`、`EntityManagerFactory`、`TransactionManager` 全部建好，你只管用 `@Autowired` 注入 Repository 就行。

但实际开发中，单库远远不够，常见场景：

| 场景 | 说明 |
| --- | --- |
| 读写分离 | 主库写、从库读，分担主库压力 |
| 多业务库 | 用户库 + 订单库 + 积分库，业务隔离 |
| 跨系统对接 | 自己的库 + 第三方系统的库（只读） |
| 数据迁移 | 新旧库并行，双写过渡 |

一旦有多个数据库，Spring Boot 的自动配置就"懵了"——它不知道哪个 Repository 该连哪个库。**多数据源的本质，就是手动接管自动配置的工作**：为每个库单独建一套 `DataSource → EntityManagerFactory → TransactionManager`，再用 `@EnableJpaRepositories` 把不同的 Repository 包绑定到不同的库。

> 💡 前端类比：这就像你的前端项目要连两个后端——一个内部业务 API、一个第三方 API。你得为每个后端建独立的 axios 实例（不同的 baseURL、拦截器、超时配置），再用不同的实例发请求。JPA 多数据源就是后端版的"多 axios 实例"。

---

## 二、项目结构

```
demo-multi-datasource-jpa/
└── src/main/java/com/xkcoding/multi/datasource/jpa/
    ├── SpringBootDemoMultiDatasourceJpaApplication.java  # 启动类
    ├── config/
    │   ├── PrimaryDataSourceConfig.java   # 主库数据源
    │   ├── PrimaryJpaConfig.java          # 主库 JPA（EntityManager + 事务）
    │   ├── SecondDataSourceConfig.java    # 从库数据源
    │   ├── SecondJpaConfig.java           # 从库 JPA
    │   └── SnowflakeConfig.java           # 雪花算法（生成分布式唯一ID）
    ├── entity/
    │   ├── primary/PrimaryMultiTable.java # 主库实体
    │   └── second/SecondMultiTable.java   # 从库实体
    └── repository/
        ├── primary/PrimaryMultiTableRepository.java  # 主库 Repository
        └── second/SecondMultiTableRepository.java    # 从库 Repository
```

**关键设计：按数据源分包。** `entity/primary` 和 `entity/second` 分开，`repository/primary` 和 `repository/second` 分开。这不是随便分的——后面 `@EnableJpaRepositories` 要按包路径扫描，把不同包的 Repository 绑到不同数据源。这是多数据源配置的**核心约定**。

---

## 三、pom.xml 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
 <artifactId>spring-boot-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

注意这里用的是 `spring-boot-starter`（不是 `starter-web`），因为本模块只演示数据层，没有 Web 接口。核心依赖是 `spring-boot-starter-data-jpa`，它会传递引入 Hibernate、Spring Data JPA、HikariCP 连接池。

---

## 四、配置文件 application.yml

```yaml
spring:
  datasource:
    primary:                          # 主库
      url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?...
      username: root
      password: root
      driver-class-name: com.mysql.cj.jdbc.Driver
      type: com.zaxxer.hikari.HikariDataSource
      hikari:
        minimum-idle: 5
        maximum-pool-size: 20
        pool-name: PrimaryHikariCP     # 连接池名，方便排查
        ...
    second:                           # 从库
      url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo-2?...
      username: root
      password: root
      driver-class-name: com.mysql.cj.jdbc.Driver
      type: com.zaxxer.hikari.HikariDataSource
      hikari:
        pool-name: SecondHikariCP
        ...
  jpa:
    primary:                          # 主库 JPA 配置
      show-sql: true
      hibernate:
        ddl-auto: update              # 自动建表/更新表结构
      properties:
        hibernate:
          dialect: org.hibernate.dialect.MySQL57InnoDBDialect
    second:                           # 从库 JPA 配置
      show-sql: true
      hibernate:
        ddl-auto: update
      properties:
        hibernate:
          dialect: org.hibernate.dialect.MySQL57InnoDBDialect
```

**关键点：**

1. **数据源配置用自定义前缀** `spring.datasource.primary` 和 `spring.datasource.second`，而不是默认的 `spring.datasource`。因为一旦有多个库，默认前缀的自动配置会失效，你要用 `@ConfigurationProperties(prefix = "...")` 手动绑定。
2. **两个库连不同的数据库**：主库是 `spring-boot-demo`，从库是 `spring-boot-demo-2`。
3. **连接池名分开**：`PrimaryHikariCP` 和 `SecondHikariCP`，方便在日志和监控里区分。
4. **JPA 配置也分开**：`spring.jpa.primary` 和 `spring.jpa.second`，每个库可以有不同的方言、DDL 策略。

> 💡 前端类比：这就像在 `.env` 里定义 `VITE_API_BASE_URL` 和 `VITE_ADMIN_API_BASE_URL` 两个前缀，分别给两个 axios 实例用。

---

## 五、主数据源配置 PrimaryDataSourceConfig

```java
@Configuration
public class PrimaryDataSourceConfig {

    @Primary
    @Bean(name = "primaryDataSourceProperties")
    @ConfigurationProperties(prefix = "spring.datasource.primary")
    public DataSourceProperties dataSourceProperties() {
        return new DataSourceProperties();
    }

    @Primary
    @Bean(name = "primaryDataSource")
    public DataSource dataSource(@Qualifier("primaryDataSourceProperties") DataSourceProperties dataSourceProperties) {
        return dataSourceProperties.initializeDataSourceBuilder().build();
    }

    @Primary
    @Bean(name = "primaryJdbcTemplate")
    public JdbcTemplate jdbcTemplate(@Qualifier("primaryDataSource") DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
```

逐个方法看：

### 5.1 `dataSourceProperties()` —— 绑定配置

- `@ConfigurationProperties(prefix = "spring.datasource.primary")`：把 yml 里 `spring.datasource.primary` 下的配置（url、username、password 等）绑定到 `DataSourceProperties` 对象。
- `@Bean(name = "primaryDataSourceProperties")`：注册成 Bean，名字是 `primaryDataSourceProperties`，后面要用名字引用它。

### 5.2 `dataSource()` —— 创建数据源

- 参数 `@Qualifier("primaryDataSourceProperties")`：按名字注入上面那个配置 Bean（因为容器里现在有两个 DataSourceProperties，必须用名字区分）。
- `dataSourceProperties.initializeDataSourceBuilder().build()`：用配置信息构建一个真正的 `DataSource`（HikariCP 连接池）。
- `@Primary`：**标记为主数据源**。当容器里有多个同类型 Bean 时，`@Autowired` 默认注入带 `@Primary` 的那个。这是多数据源的关键——必须有一个"默认"的，否则 Spring 不知道该用哪个。

### 5.3 `jdbcTemplate()` —— 可选的 JdbcTemplate

- 如果你想用 JdbcTemplate 而不是 JPA 操作这个库，可以注入这个 Bean。本模块主要用 JPA，这个是附赠的。

> 💡 前端类比：`@Primary` 就像 axios 实例的"默认导出"——当你 `import axios from 'axios'` 时拿到的是默认实例。`@Qualifier` 就像 `import { adminAxios } from './instances'`，按名字精确取。

---

## 六、从数据源配置 SecondDataSourceConfig

```java
@Configuration
public class SecondDataSourceConfig {

    @Bean(name = "secondDataSourceProperties")
    @ConfigurationProperties(prefix = "spring.datasource.second")
    public DataSourceProperties dataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean(name = "secondDataSource")
    public DataSource dataSource(@Qualifier("secondDataSourceProperties") DataSourceProperties dataSourceProperties) {
        return dataSourceProperties.initializeDataSourceBuilder().build();
    }

    @Bean(name = "secondJdbcTemplate")
    public JdbcTemplate jdbcTemplate(@Qualifier("secondDataSource") DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
```

和主数据源几乎一模一样，**唯一区别是没有 `@Primary`**。前缀改成 `spring.datasource.second`，Bean 名字都带 `second`。

> ⚠️ 注意：从数据源的任何 Bean 都不能加 `@Primary`，否则主从就反了。一个项目里同类型 Bean 只能有一个 `@Primary`。

---

## 七、主 JPA 配置 PrimaryJpaConfig（核心）

数据源只是"连上数据库"，JPA 还需要 `EntityManagerFactory`（管理实体）和 `TransactionManager`（管理事务）。这才是 JPA 多数据源配置的重头戏。

```java
@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
    basePackages = PrimaryJpaConfig.REPOSITORY_PACKAGE,
    entityManagerFactoryRef = "primaryEntityManagerFactory",
    transactionManagerRef = "primaryTransactionManager")
public class PrimaryJpaConfig {
    static final String REPOSITORY_PACKAGE = "com.xkcoding.multi.datasource.jpa.repository.primary";
    private static final String ENTITY_PACKAGE = "com.xkcoding.multi.datasource.jpa.entity.primary";
    ...
}
```

### 7.1 `@EnableJpaRepositories` —— 把 Repository 包绑定到数据源

这是多数据源配置的**灵魂注解**：

| 参数 | 作用 |
| --- | --- |
| `basePackages` | 扫描哪个包下的 Repository 接口 |
| `entityManagerFactoryRef` | 这些 Repository 用哪个 EntityManagerFactory（对应哪个库） |
| `transactionManagerRef` | 这些 Repository 用哪个事务管理器 |

这里把 `repository.primary` 包下的 Repository 绑到主库的 `primaryEntityManagerFactory` 和 `primaryTransactionManager`。**这就是为什么要按数据源分包**——靠包路径区分哪个 Repository 归哪个库。

### 7.2 `jpaProperties()` —— 绑定 JPA 配置

```java
@Primary
@Bean(name = "primaryJpaProperties")
@ConfigurationProperties(prefix = "spring.jpa.primary")
public JpaProperties jpaProperties() {
    return new JpaProperties();
}
```

把 yml 里 `spring.jpa.primary` 下的配置（show-sql、ddl-auto、dialect）绑定成 Bean。

### 7.3 `entityManagerFactory()` —— 创建实体管理工厂

```java
@Primary
@Bean(name = "primaryEntityManagerFactory")
public LocalContainerEntityManagerFactoryBean entityManagerFactory(
        @Qualifier("primaryDataSource") DataSource primaryDataSource,
        @Qualifier("primaryJpaProperties") JpaProperties jpaProperties,
        EntityManagerFactoryBuilder builder) {
    return builder
        .dataSource(primaryDataSource)              // 绑定主库数据源
        .properties(jpaProperties.getProperties()) // JPA 配置
        .packages(ENTITY_PACKAGE)                  // 扫描哪个包下的实体类
        .persistenceUnit("primaryPersistenceUnit") // 持久化单元名
        .build();
}
```

- 注入主库的 `DataSource` 和 `JpaProperties`。
- `.packages(ENTITY_PACKAGE)`：告诉 Hibernate 去哪个包扫描 `@Entity` 注解的实体类。**主库实体在 `entity.primary` 包，从库实体在 `entity.second` 包，必须分开**，否则两个库会扫描到对方的实体，建表时乱套。
- `.persistenceUnit("primaryPersistenceUnit")`：给这个工厂起个名字，用 `@PersistenceContext` 手动获取 EntityManager 时能指定。

### 7.4 `entityManager()` 和 `transactionManager()`

```java
@Primary
@Bean(name = "primaryEntityManager")
public EntityManager entityManager(...) { ... }

@Primary
@Bean(name = "primaryTransactionManager")
public PlatformTransactionManager transactionManager(...) {
    return new JpaTransactionManager(factory);
}
```

- `EntityManager`：JPA 操作实体的核心 API，一般不直接用，Repository 底层靠它。
- `JpaTransactionManager`：这个库专属的事务管理器。`@Transactional` 默认用 `@Primary` 的事务管理器，但跨库操作时要手动指定。

---

## 八、从 JPA 配置 SecondJpaConfig

```java
@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
    basePackages = SecondJpaConfig.REPOSITORY_PACKAGE,
    entityManagerFactoryRef = "secondEntityManagerFactory",
    transactionManagerRef = "secondTransactionManager")
public class SecondJpaConfig {
    static final String REPOSITORY_PACKAGE = "com.xkcoding.multi.datasource.jpa.repository.second";
    private static final String ENTITY_PACKAGE = "com.xkcoding.multi.datasource.jpa.entity.second";
    ...
}
```

结构和主配置完全对称，区别是：

- 扫描 `repository.second` 包的 Repository。
- 实体包是 `entity.second`。
- 持久化单元名是 `secondPersistenceUnit`。
- **没有 `@Primary`**。

> 💡 配置套路总结：每个数据源 = 1 个 DataSourceConfig + 1 个 JpaConfig，JpaConfig 里用 `@EnableJpaRepositories(basePackages=..., entityManagerFactoryRef=..., transactionManagerRef=...)` 把 Repository 包绑到对应的库。主库加 `@Primary`，从库不加。这是 JPA 多数据源的"标准模板"，记住这个套路就行。

---

## 九、实体类与 Repository

### 9.1 实体类

`entity/primary/PrimaryMultiTable.java`：

```java
@Data
@Entity
@Table(name = "multi_table")
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PrimaryMultiTable {
    @Id
    private Long id;
    private String name;
}
```

`entity/second/SecondMultiTable.java` 结构一模一样，只是包不同。

- `@Entity` / `@Table(name = "multi_table")`：标记为 JPA 实体，对应表 `multi_table`。
- 两个库的表名都是 `multi_table`，但因为在不同数据库（`spring-boot-demo` 和 `spring-boot-demo-2`），互不影响。
- `@Id`：主键。这里主键由雪花算法生成，不用 `@GeneratedValue`（自增），而是外部传入。

### 9.2 Repository

```java
@Repository
public interface PrimaryMultiTableRepository extends JpaRepository<PrimaryMultiTable, Long> {
}
```

```java
@Repository
public interface SecondMultiTableRepository extends JpaRepository<SecondMultiTable, Long> {
}
```

两个 Repository 都只是空接口继承 `JpaRepository`，但**它们在不同包**，所以会被不同的 `@EnableJpaRepositories` 扫描，绑到不同的库。`PrimaryMultiTableRepository` 操作主库，`SecondMultiTableRepository` 操作从库。

---

## 十、雪花算法配置 SnowflakeConfig

```java
@Configuration
public class SnowflakeConfig {
    @Bean
    public Snowflake snowflake() {
        return IdUtil.createSnowflake(1, 1);
    }
}
```

- 用 Hutool 的 `Snowflake` 生成分布式唯一 ID。
- `IdUtil.createSnowflake(1, 1)`：参数是机器 ID 和数据中心 ID，分布式环境下每台机器要不同。
- **为什么多数据源要用雪花 ID？** 多个库各自自增主键会冲突（主键都是 1、2、3），做数据同步/合并时主键打架。雪花算法生成全局唯一的长整型 ID，避免冲突。

> 💡 前端类比：类似前端用 `uuid` 或 `nanoid` 生成唯一 key，而不是用数组的 index——多份数据合并时 index 会冲突，UUID 不会。

---

## 十一、测试类

```java
@RunWith(SpringRunner.class)
@SpringBootTest
@Slf4j
public class SpringBootDemoMultiDatasourceJpaApplicationTests {
    @Autowired
    private PrimaryMultiTableRepository primaryRepo;
    @Autowired
    private SecondMultiTableRepository secondRepo;
    @Autowired
    private Snowflake snowflake;

    @Test
    public void testInsert() {
        PrimaryMultiTable primary = new PrimaryMultiTable(snowflake.nextId(), "测试名称-1");
        primaryRepo.save(primary);

        SecondMultiTable second = new SecondMultiTable();
        BeanUtil.copyProperties(primary, second);
        secondRepo.save(second);
    }
    ...
}
```

- 注入两个 Repository，分别操作各自的库。
- `testInsert`：用雪花算法生成 ID，往主库插一条，再用 `BeanUtil.copyProperties` 把主库对象复制成从库对象，往从库插一条。这就是"双写"——主从库都写同一份数据。
- `testSelect`：分别查两个库，验证数据隔离。

---

## 十二、运行与验证

1. 准备两个 MySQL 数据库：`spring-boot-demo` 和 `spring-boot-demo-2`（不用建表，`ddl-auto: update` 会自动建）。
2. 运行测试类，观察日志：会看到两组 SQL，分别连不同的库。
3. 检查两个库的 `multi_table` 表，各有数据。

---

## 十三、动手练习

1. **加第三个数据源**：照着主/从的模板，加一个 `third` 数据源，配一套 DataSourceConfig + JpaConfig，建 `entity.third` 和 `repository.third` 包，验证三库隔离。
2. **测试事务**：在 `testInsert` 里故意在 `secondRepo.save` 后抛异常，观察主库的数据是否回滚（默认不会，因为跨库事务）。然后加 `@Transactional(transactionManager = "primaryTransactionManager")` 试试。
3. **只读从库**：把从库的 `ddl-auto` 改成 `none`，`show-sql` 留着，模拟只读场景。
4. **用 JdbcTemplate**：注入 `primaryJdbcTemplate`，手写 SQL 查询，对比 JPA 的便捷性。
5. **主键冲突实验**：把两个实体的 `@Id` 改成 `@GeneratedValue(strategy = IDENTITY)`（自增），往两个库各插几条，然后把从库数据导到主库，观察主键冲突。

---

## 十四、本模块知识点总结（结合实际开发详解）

JPA 多数据源是实际项目的中高级配置，下面把核心知识点放到真实开发场景里讲透。

### 14.1 多数据源的三种实现方案对比

**实际开发中，多数据源有三种主流方案：**

| 方案 | 原理 | 优点 | 缺点 | 适用场景 |
| --- | --- | --- | --- | --- |
| **手动配置多套 Bean**（本模块） | 每个库一套 DataSource + EMF + TM，按包绑定 | 直观、可控、调试简单 | 配置繁琐，加库要改代码 | 库少（2-3个）、固定不变 |
| **动态数据源（dynamic-datasource）** | 一个 AbstractRoutingDataSource，运行时切换 key | 加库只改配置、注解切换 | AOP 切换有坑、跨库事务难 | 库多、频繁变化（见 `demo-dynamic-datasource`） |
| **分库分表中间件（ShardingSphere）** | SQL 解析层路由 | 透明、支持分片 | 学习成本高、复杂查询受限 | 海量数据分片（见 `demo-sharding-jdbc`） |

**最佳实践**：

- 库少且固定 → 用本模块的手动配置，最稳。
- 库多或经常加 → 用 `dynamic-datasource-spring-boot-starter`，注解切换。
- 数据量巨大要分片 → 上 ShardingSphere。

**常见坑**：新手一上来就用动态数据源，结果跨库事务、AOP 自调用问题排查半天。库少时手动配置最省心。

### 14.2 `@Primary` 与 `@Qualifier`：多 Bean 共存的钥匙

多数据源下，容器里有多个 `DataSource`、多个 `EntityManagerFactory`、多个 `TransactionManager`。Spring 靠两个注解区分：

- **`@Primary`**：标记"默认的那个"。`@Autowired` 不指定名字时，优先注入它。**一个类型只能有一个 `@Primary`**。
- **`@Qualifier("beanName")`**：按名字精确指定注入哪个 Bean。

**实际开发怎么用？**

- 主库（写库）的所有 Bean 加 `@Primary`，这样 `@Transactional` 默认走主库事务，`@Autowired DataSource` 默认拿主库。
- 从库 Bean 不加 `@Primary`，需要时用 `@Qualifier("secondXxx")` 精确注入。

**常见坑**：

1. **忘了给主库加 `@Primary`**：Spring 启动报错 `NoUniqueBeanDefinitionException`，因为它不知道默认用哪个。
2. **两个库都加了 `@Primary`**：同样报错，`@Primary` 只能有一个。
3. **`@Qualifier` 名字写错**：注入失败，仔细核对 Bean 的 `name`。

> 💡 前端类比：`@Primary` 像默认导出 `export default`，`@Qualifier` 像具名导入 `import { secondDataSource }`。

### 14.3 `@EnableJpaRepositories`：Repository 与数据源的绑定契约

这个注解是多数据源的"路由器"：

```java
@EnableJpaRepositories(
    basePackages = "com.xxx.repository.primary",        // 扫描哪个包
    entityManagerFactoryRef = "primaryEntityManagerFactory",  // 用哪个工厂
    transactionManagerRef = "primaryTransactionManager")      // 用哪个事务
```

**核心逻辑**：`basePackages` 下的 Repository 接口，Spring 会为它们生成代理实现，代理内部用 `entityManagerFactoryRef` 指定的工厂操作数据库。

**实际开发的分包约定**：

```
repository/
├── primary/    ← 主库 Repository，绑 primaryEntityManagerFactory
└── second/     ← 从库 Repository，绑 secondEntityManagerFactory
```

**常见坑**：

1. **Repository 放错包**：把从库的 Repository 放到 `primary` 包，结果它操作了主库，数据写错地方。分包时要严格。
2. **实体类放错包**：`@EnableJpaRepositories` 没有直接指定实体包，实体包是在 `entityManagerFactory` 的 `.packages(ENTITY_PACKAGE)` 里指定的。如果主库工厂扫描了从库的实体，会在主库建从库的表。
3. **一个 Repository 接口想跨库**：JPA 多数据源下，一个 Repository 只能绑一个库。跨库查询要用 `JdbcTemplate` 手写 SQL，或拆成两个 Repository 分别查再合并。

### 14.4 跨库事务：多数据源最大的坑

本模块每个库有独立的事务管理器，`@Transactional` 默认只走主库事务。**跨库操作无法用一个事务保证原子性**：

```java
@Transactional  // 只走 primaryTransactionManager
public void crossDb() {
    primaryRepo.save(a);   // 主库插入
    secondRepo.save(b);    // 从库插入 —— 如果这里抛异常，主库不回滚！
}
```

**实际开发的解决方案：**

1. **尽量不跨库事务**：把跨库操作拆成消息队列 + 本地事务（最终一致性）。
2. **用 JTA 分布式事务**：引入 `atomikos` 或 `Bitronix`，但性能差，基本淘汰。
3. **Seata 等分布式事务框架**：微服务场景的主流方案，但配置复杂。

**最佳实践**：多数据源项目里，**业务设计就避免跨库强一致**。比如读写分离场景，"写主库 + 读从库"本来就有延迟，接受最终一致。如果是双写（主从都写），用消息队列保证最终一致，而不是强求一个事务。

> 💡 前端类比：这就像你同时调两个后端 API，想让它们"要么都成功要么都失败"——HTTP 本身没有分布式事务，你只能用补偿/重试/对账来逼近一致。

### 14.5 连接池配置：每个库独立调优

本模块两个库各配了 HikariCP，参数可以不同：

```yaml
spring:
  datasource:
    primary:
      hikari:
        maximum-pool-size: 20      # 主库写多，连接数大
        pool-name: PrimaryHikariCP
    second:
      hikari:
        maximum-pool-size: 10      # 从库读少，连接数小
        pool-name: SecondHikariCP
```

**实际开发要点**：

1. **连接池名分开**（`pool-name`）：日志和监控里能区分是哪个库的连接。
2. **按负载调参**：写库并发高，连接数大；只读从库并发低，连接数小。
3. **总连接数有上限**：两个库的 `maximum-pool-size` 之和不能超过数据库服务器的 `max_connections`，否则连不上。
4. **连接泄漏排查**：用 `leak-detection-threshold` 检测连接没归还，多数据源下更容易泄漏。

### 14.6 雪花 ID vs 自增主键：多数据源的主键策略

本模块用雪花算法生成主键，不用数据库自增。为什么？

**自增主键（`@GeneratedValue(strategy = IDENTITY)`）在多数据源下的问题：**

- 主库和从库各自从 1 自增，ID 重复。
- 数据同步/合并时主键冲突。
- 分库分表时无法保证全局唯一。

**雪花算法的优势：**

- 生成全局唯一的长整型 ID（64 位：时间戳 + 机器ID + 序列号）。
- 趋势递增，对 B+ 树索引友好。
- 不依赖数据库，应用层生成。

**实际开发选型**：

| 场景 | 主键策略 |
| --- | --- |
| 单库单表 | 自增即可 |
| 多数据源/读写分离 | 雪花 ID 或 UUID |
| 分库分表 | 雪花 ID（推荐）或 ShardingSphere 内置的雪花 |
| 对外暴露 | UUID（无序但安全）或雪花转 Base62 |

**常见坑**：雪花算法依赖机器时钟，时钟回拨会生成重复 ID。生产环境要配 NTP 时钟同步，或用 Hutool/Leaf 的时钟回拨保护。

### 14.7 `ddl-auto` 在多数据源下的风险

本模块两个库都配了 `ddl-auto: update`，启动时自动建/改表。

**实际开发的风险：**

- `update` 会自动加列，但**不会删列**，表结构会和生产配置漂移。
- 多库自动建表，如果实体定义有误，会同时在多个库建错表。
- 生产环境用 `update` 是危险的，应该用 `validate`（只校验不改）或 `none`，配合 Flyway/Liquibase 管理表结构（见 `demo-flyway`）。

**最佳实践**：

| 环境 | ddl-auto | 说明 |
| --- | --- | --- |
| 开发 | `update` 或 `create` | 方便，自动建表 |
| 测试 | `create-drop` | 每次跑完清空 |
| 生产 | `validate` 或 `none` | 配合 Flyway，绝不自动改表 |

---

> 📌 **学习建议**：JPA 多数据源的配置看起来很长，但本质就是"复制粘贴 + 改名字"——每个库一套 DataSourceConfig + JpaConfig，按包绑定。建议你照着这个模板手写一遍三数据源的配置（而不是复制），写完你就彻底懂了。另外记住一个原则：**多数据源能不用就不用**，它带来的跨库事务、主键冲突、连接池管理都是额外复杂度。优先考虑是不是能合并成一个库，或者用读写分离中间件（如 ShardingSphere）透明处理，把复杂度交给框架。
