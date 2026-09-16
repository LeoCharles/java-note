# Spring 整合 MyBatis

前 15 篇把 Spring 的核心机制走了一遍——IoC、DI、AOP、事务、MVC。从本篇开始把这些能力"接上数据库"，让 Spring 和 MyBatis 协同工作。学完这篇你就知道：Spring Boot 自动配置的 `SqlSessionFactory` 和 `MapperScanner` 到底做了什么，为阅读 [Spring实战/15-数据库操作_MyBatis](../Spring实战/15-数据库操作_MyBatis.md) 铺平道路。

> 💡 如果你是先学 Spring Boot 直接用的 MyBatis，这篇帮你理解"那些自动配置到底帮你做了什么"。如果你是先学的原生 MyBatis，这篇帮你理解"Spring 怎么代理了那些样板代码"。

---

## 一、原生 MyBatis vs Spring 整合 MyBatis

### 1.1 原生 MyBatis 的写法

```java
// 原生 MyBatis：自己管理 SqlSession
public User findById(Long id) {
    // 1. 读取配置文件，构建 SqlSessionFactory
    SqlSessionFactory factory = new SqlSessionFactoryBuilder()
            .build(Resources.getResourceAsStream("mybatis-config.xml"));

    // 2. 打开 SqlSession
    try (SqlSession session = factory.openSession()) {
        // 3. 调用 Mapper
        UserMapper mapper = session.getMapper(UserMapper.class);
        return mapper.findById(id);
    }
    // 4. 关闭 session
}
```

**问题**：每查一次数据库都要走这 4 步，SqlSessionFactory 每次新建也很浪费。

### 1.2 Spring 整合后的写法

```java
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserMapper userMapper;  // ← 直接注入 Mapper，和普通 Bean 一样用

    public User findById(Long id) {
        return userMapper.findById(id);   // 不用管 SqlSession 了！
    }
}
```

**Spring 帮你做了什么**：
1. SqlSessionFactory → 作为 Spring Bean 管理（单例，启动时创建一次）
2. SqlSession → 交给 Spring 的事务管理器管理（`@Transactional` 自动打开/关闭/提交/回滚）
3. Mapper 接口 → 自动扫描、自动生成代理对象、自动注入

---

## 二、Spring 整合 MyBatis 的核心组件

### 2.1 SqlSessionFactoryBean：工厂交给 Spring

```java
@Configuration
public class MyBatisConfig {

    @Bean
    public SqlSessionFactory sqlSessionFactory(DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factoryBean = new SqlSessionFactoryBean();

        // 1. 设置数据源
        factoryBean.setDataSource(dataSource);

        // 2. 设置 MyBatis 配置文件（可选）
        factoryBean.setConfigLocation(
                new ClassPathResource("mybatis-config.xml"));

        // 3. 设置 Mapper XML 位置
        factoryBean.setMapperLocations(
                new PathMatchingResourcePatternResolver()
                        .getResources("classpath:mapper/*.xml"));

        // 4. 设置别名包
        factoryBean.setTypeAliasesPackage("com.example.entity");

        return factoryBean.getObject();
    }
}
```

> 💡 `SqlSessionFactoryBean` 不是一个普通的 Bean，它实现了 Spring 的 `FactoryBean` 接口。Spring 调用 `getObject()` 拿到的是 `SqlSessionFactory`，而不是 `SqlSessionFactoryBean` 本身。

### 2.2 MapperScannerConfigurer：扫描 Mapper 接口

```java
@Bean
public MapperScannerConfigurer mapperScannerConfigurer() {
    MapperScannerConfigurer scanner = new MapperScannerConfigurer();
    // 扫描指定包下所有带有 @Mapper 的接口
    scanner.setBasePackage("com.example.mapper");
    return scanner;
}
```

**扫描原理**：

1. `MapperScannerConfigurer` 扫描指定包下所有接口
2. 对每个接口，用 `MapperFactoryBean` 生成一个代理对象
3. 把这个代理对象注册到 Spring 容器中（Bean 名 = 接口名首字母小写）

```java
@Mapper
public interface UserMapper {
    User findById(Long id);
}

// Spring 容器中注册：
// Bean 名: userMapper
// Bean 类型: org.apache.ibatis.binding.MapperProxy@xxxx（代理对象）
// 代理逻辑: 调 findById → 获取 SqlSession → sqlSession.selectOne("findById", id)
```

### 2.3 FactoryBean：为什么 getObject() 返回的是 SqlSessionFactory

```java
// FactoryBean 模式（Spring 中大量使用）
public interface FactoryBean<T> {
    T getObject() throws Exception;    // 创建目标对象
    Class<?> getObjectType();          // 目标对象类型
    boolean isSingleton();             // 是否单例
}

// SqlSessionFactoryBean 实现了 FactoryBean<SqlSessionFactory>
// Spring 调用 getObject() → 拿到 SqlSessionFactory
// 所以容器中 "sqlSessionFactory" 的类型是 SqlSessionFactory，不是 SqlSessionFactoryBean
```

> 💡 `FactoryBean` 是 Spring 的设计模式应用之一，用来封装复杂对象的创建过程。类似的有 `JdbcTemplate`、`RestTemplate` 等的工厂 Bean。

---

## 三、纯注解整合（不用 XML）

```java
@Configuration
@MapperScan("com.example.mapper")  // ← 替代 MapperScannerConfigurer
public class MyBatisConfig {

    @Bean
    public SqlSessionFactory sqlSessionFactory(DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factoryBean = new SqlSessionFactoryBean();
        factoryBean.setDataSource(dataSource);

        // 纯注解模式：不需要 XML 配置 MyBatis 全局设置
        org.apache.ibatis.session.Configuration config = new org.apache.ibatis.session.Configuration();
        config.setMapUnderscoreToCamelCase(true);  // 下划线转驼峰
        config.setLogImpl(StdOutImpl.class);       // 日志
        factoryBean.setConfiguration(config);

        return factoryBean.getObject();
    }
}
```

```java
// Mapper 接口
@Mapper
public interface UserMapper {
    @Select("SELECT * FROM user WHERE id = #{id}")
    User findById(Long id);

    @Insert("INSERT INTO user(name, age) VALUES(#{name}, #{age})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(User user);
}
```

---

## 四、整合后的事务管理

Spring 整合 MyBatis 后，`@Transactional` 自动接管 SqlSession：

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderMapper orderMapper;

    @Transactional  // ← 这个方法执行时自动管理 SqlSession
    public void createOrder(Order order) {
        orderMapper.insert(order);
        // 如果这里抛异常，上面的 insert 自动回滚
    }
}
```

**内部流程压缩版**：

```
@Transactional 方法开始
    → Spring 事务拦截器：开启事务，绑定 SqlSession 到当前线程（ThreadLocal）
    → 执行 orderMapper.insert(order)
        → MapperProxy 从 ThreadLocal 获取当前线程的 SqlSession
        → sqlSession.insert("insert", order)
    → 方法正常结束 → 提交事务 → 关闭 SqlSession
    → 方法异常 → 回滚事务 → 关闭 SqlSession
```

> 💡 整个过程中你不需要写一句 `sqlSession.open()` / `commit()` / `close()`。Spring 的事务管理器通过 ThreadLocal 自动把 SqlSession 绑定到当前线程，同一个事务中多次调用 Mapper 共享同一个 SqlSession。

---

## 五、@Mapper 和 @MapperScan

```java
// 方式一：每个 Mapper 接口都贴 @Mapper（繁琐）
@Mapper
public interface UserMapper { }
@Mapper
public interface OrderMapper { }

// 方式二：在配置类上统一扫描（推荐）
@Configuration
@MapperScan("com.example.mapper")  // 一次扫描全部 Mapper
public class MyBatisConfig { }
```

`@MapperScan` 相当于在指定包下给每个接口贴了 `@Mapper`。

---

## 💻 实战案例

### 案例：整合后的完整配置

```java
@Configuration
@MapperScan("com.example.mapper")        // 1. 扫描 Mapper
@EnableTransactionManagement             // 2. 开启事务管理
public class MyBatisConfig {

    @Bean
    public DataSource dataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://localhost:3306/mydb");
        config.setUsername("root");
        config.setPassword("123456");
        config.setMaximumPoolSize(20);
        return new HikariDataSource(config);
    }

    @Bean
    public SqlSessionFactory sqlSessionFactory(DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factory = new SqlSessionFactoryBean();
        factory.setDataSource(dataSource);
        // 如果还有 XML Mapper
        factory.setMapperLocations(
            new PathMatchingResourcePatternResolver()
                .getResources("classpath:mapper/*.xml"));
        return factory.getObject();
    }

    @Bean
    public PlatformTransactionManager transactionManager(DataSource dataSource) {
        return new DataSourceTransactionManager(dataSource);
    }
}
```

### Mapper 和 Service 的完整链路

```java
// 1. Mapper 接口
@Mapper
public interface UserMapper {
    @Select("SELECT * FROM user WHERE id = #{id}")
    User findById(Long id);
}

// 2. Service：直接注入 Mapper，加 @Transactional
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserMapper userMapper;

    @Transactional
    public User getById(Long id) {
        return userMapper.findById(id);  // 代理自动获取 SqlSession
    }
}

// 3. Controller
@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping("/{id}")
    public User getById(@PathVariable Long id) {
        return userService.getById(id);
    }
}
```

---

## 🎯 面试高频

### Q1：Spring 整合 MyBatis 后，SqlSession 是怎么管理的？

**答**：Spring 通过 `SqlSessionTemplate`（`SqlSession` 的实现类）管理 SqlSession。它是线程安全的，内部使用 `SqlSessionHolder` 和 ThreadLocal 把 SqlSession 绑定到当前线程。在 `@Transactional` 方法中，同一事务内所有 Mapper 调用共享同一个 SqlSession，事务结束后自动关闭。

### Q2：@Mapper 和 @MapperScan 的区别？

**答**：`@Mapper` 标注在单个 Mapper 接口上，需要每个接口都贴一次。`@MapperScan` 标注在配置类上，指定包路径，批量扫描该路径下所有接口。实际项目推荐用 `@MapperScan`，统一管理。

### Q3：SqlSessionFactoryBean 为什么能返回 SqlSessionFactory？

**答**：`SqlSessionFactoryBean` 实现了 Spring 的 `FactoryBean<SqlSessionFactory>` 接口。Spring 容器在处理 `FactoryBean` 类型的 Bean 时，会调用其 `getObject()` 方法获取真正的目标对象（此处是 `SqlSessionFactory`）并注册到容器中，而不是注册 FactoryBean 本身。

---

## 📌 在 Spring Boot 中

- **Spring Boot 整合 MyBatis 更简单**：引入 `mybatis-spring-boot-starter`，写个 `@Mapper` 接口，在 `application.yml` 中配好数据源，三件事搞定。
- **Boot 自动配置了 `SqlSessionFactory`**：`MybatisAutoConfiguration` 类自动创建 SqlSessionFactory、SqlSessionTemplate、MapperScanner
- **但理解本篇的原理能让你排 Bug 时找到方向**：如果 MyBatis 报"找不到 Mapper"——检查 `@MapperScan` 路径；如果报"SqlSession 已关闭"——检查 `@Transactional` 是否失效；如果多数据源时 Mapper 调错库——检查 SqlSessionFactory 的注入（`@Qualifier`）

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| SqlSessionFactoryBean | FactoryBean 模式，getObject() 返回 SqlSessionFactory |
| MapperScannerConfigurer | 扫描 Mapper 接口，为每个接口生成代理并注册到容器 |
| @MapperScan | 替代 MapperScannerConfigurer 的注解方式，推荐 |
| 事务整合 | @Transactional 自动管理 SqlSession 的打开/提交/回滚/关闭 |
| Mapper 代理 | `MapperProxy` + `MapperMethod`，调接口方法 → 实际调 SqlSession |

---

## 学习建议

1. **先写好原生 MyBatis，再加 Spring 整合**：用原生 MyBatis 写一个 DAO，体会 SqlSessionFactory/SqlSession/Mapper 三个对象的创建和生命周期。然后加上 Spring 整合，看这三件事怎么被 Spring "收编"。
2. **Debug 跟踪一次 Mapper 调用**：在 `MapperProxy.invoke()` 方法打断点，看 Mapper 接口方法调用时，代理内部怎么获取 SqlSession、怎么执行 SQL。看完会发现——所谓的"MyBatis 魔法"其实就是"接口对应的代理类调了 SqlSession 的方法"。
3. **理解 FactoryBean 模式**：它是 Spring 中封装复杂创建逻辑的标准方式。看懂了 FactoryBean，以后碰到 `JpaTransactionManager`、`HikariDataSource` 等需要复杂初始化的 Bean 就知道为什么不直接 new。