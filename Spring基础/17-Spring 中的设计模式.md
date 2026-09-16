# Spring 中的设计模式

学了 16 篇 Spring 核心原理，你会发现 Spring 代码写得很"舒服"——扩展容易、替换方便、测试友好。这种舒服感不是偶然的，是 Spring 大量应用设计模式的结果。本篇帮你梳理 Spring 中用到了哪些设计模式——这也是面试的经典题："Spring 中用了哪些设计模式？"

> 💡 学完这篇，你不仅能答上面试题，还把前面 16 篇的零散知识用"设计模式"这条线串起来，对 Spring 的设计哲学有一个整体认知。

---

## 一、工厂模式（Factory Pattern）

### 1.1 BeanFactory：简单工厂

```java
// 这就是你每天都用的工厂
ApplicationContext ctx = ...;
UserService service = ctx.getBean(UserService.class);  // 工厂方法，产品 = Bean
```

**Spring 中的应用**：
- `BeanFactory` / `ApplicationContext`：核心容器本身就是一个巨大的工厂
- `FactoryBean<T>`：封装复杂对象的创建逻辑（如 `SqlSessionFactoryBean`）

### 1.2 FactoryBean：工厂方法模式

```java
// 普通 Bean：Spring 反射 new 一下就行
@Component
public class UserService { }

// 复杂 Bean：创建过程需要很多步骤，用 FactoryBean 封装
@Component
public class SqlSessionFactoryBean implements FactoryBean<SqlSessionFactory> {
    @Override
    public SqlSessionFactory getObject() throws Exception {
        // 复杂创建逻辑：读配置、构建、设置属性...
        return new SqlSessionFactoryBuilder().build(...);
    }

    @Override
    public Class<?> getObjectType() {
        return SqlSessionFactory.class;
    }
}
// 用户拿的是 getObject() 的返回值，而不是 FactoryBean 本身
```

---

## 二、单例模式（Singleton Pattern）

### 2.1 Spring 单例 vs 传统单例

```java
// 传统单例：代码级别约束
public class UserService {
    private static volatile UserService instance;
    private UserService() {}
    public static UserService getInstance() { ... }
}

// Spring 单例：容器级别约束
@Component
public class UserService { }  // 默认 scope = singleton
// 你不需要写任何单例代码，容器保证全局只有一个实例
```

**区别**：传统单例是"自己保证自己只有一个"，Spring 单例是"容器保证这个名称下只有一个"。前者靠代码（private 构造 + static 变量），后者靠约定（默认作用域 + 一级缓存）。

---

## 三、代理模式（Proxy Pattern）⭐⭐

### 3.1 AOP：动态代理

```java
@Service
public class OrderService {
    @Transactional
    public void createOrder(Order order) { ... }
}

// 实际注入的是 CGLIB 代理对象：
// OrderService$$EnhancerBySpringCGLIB$$abc12345@xxxx
```

Spring AOP 本质就是动态代理模式：
- **JDK 动态代理**：`Proxy.newProxyInstance()` + `InvocationHandler`，要求实现接口
- **CGLIB 代理**：`Enhancer.create()` + `MethodInterceptor`，通过继承生成子类

详见 [08-AOP 概念与代理机制](08-AOP%20概念与代理机制.md)。

### 3.2 @Lazy：虚拟代理

```java
@Service
public class OrderService {
    @Autowired
    @Lazy  // ← 注入的是代理，不是真正的 HeavyService
    private HeavyService heavyService;
}
```

`@Lazy` 注入的是一个 CGLIB 代理对象，真正调 `heavyService.xxx()` 时才去容器中获取目标对象——延迟初始化 + 打破循环依赖。

---

## 四、模板方法模式（Template Method Pattern）

### 4.1 JdbcTemplate

```java
@Repository
public class UserDao {
    @Autowired
    private JdbcTemplate jdbcTemplate;

    public User findById(Long id) {
        // 模板方法：你只写 SQL 和结果映射，连接获取/关闭/异常处理全由模板处理
        return jdbcTemplate.queryForObject(
                "SELECT * FROM user WHERE id = ?",
                new BeanPropertyRowMapper<>(User.class),
                id
        );
    }
}
```

**模板方法模式的体现**：

```
JdbcTemplate.query(sql, params, rowMapper)
    │
    ├── ① 获取连接        ← 模板定好的
    ├── ② 创建 PreparedStatement  ← 模板定好的
    ├── ③ 设置参数        ← 模板定好的
    ├── ④ 执行 SQL        ← 模板定好的
    ├── ⑤ 映射结果        ← ★ 你定的（RowMapper）
    ├── ⑥ 处理异常        ← 模板定好的
    └── ⑦ 关闭连接        ← 模板定好的
```

**Spring 中的模板方法模式**：

| 模板类 | 用途 |
| :--- | :--- |
| `JdbcTemplate` | JDBC 操作 |
| `RestTemplate` | HTTP 调用 |
| `TransactionTemplate` | 编程式事务 |
| `RedisTemplate` | Redis 操作 |
| `RabbitTemplate` | RabbitMQ 消息发送 |

> 💡 **"Template" 结尾的类都是模板方法模式**：骨架流程由模板固定，变化部分由回调（RowMapper/ResultSetExtractor/MessageConverter 等）定制。

---

## 五、观察者模式（Observer Pattern）

### 5.1 ApplicationEvent + @EventListener

```java
// 1. 定义事件
public class OrderCreatedEvent extends ApplicationEvent {
    private final Order order;
    public OrderCreatedEvent(Object source, Order order) {
        super(source);
        this.order = order;
    }
    public Order getOrder() { return order; }
}

// 2. 发布事件（发布者）
@Service
public class OrderService {
    @Autowired
    private ApplicationEventPublisher publisher;

    @Transactional
    public void createOrder(Order order) {
        orderDao.save(order);
        publisher.publishEvent(new OrderCreatedEvent(this, order));  // 发布
    }
}

// 3. 监听事件（观察者1：发短信）
@Component
public class SmsListener {
    @EventListener
    public void handleOrderCreated(OrderCreatedEvent event) {
        System.out.println("发短信：" + event.getOrder().getId());
    }
}

// 4. 监听事件（观察者2：记日志）
@Component
public class AuditListener {
    @EventListener
    public void handleOrderCreated(OrderCreatedEvent event) {
        System.out.println("记审计日志：" + event.getOrder().getId());
    }
}
```

**好处**：发布者和观察者完全解耦——新增一个监听者（如"发优惠券"），OrderService 一行都不改。

---

## 六、策略模式（Strategy Pattern）

### 6.1 PlatformTransactionManager

```java
// 策略接口
public interface PlatformTransactionManager {
    TransactionStatus getTransaction(TransactionDefinition definition);
    void commit(TransactionStatus status);
    void rollback(TransactionStatus status);
}

// 不同策略实现
DataSourceTransactionManager  → JDBC / MyBatis 事务策略
JpaTransactionManager         → JPA 事务策略
JtaTransactionManager         → 分布式事务策略
```

Spring 根据你使用的数据访问技术，自动选择对应的事务管理器实现——上层代码（`@Transactional`）不用关心用的是哪个策略。

### 6.2 ResourceLoader

```java
// 策略接口：统一资源加载
public interface ResourceLoader {
    Resource getResource(String location);
}

// 不同策略：从 classpath / 文件系统 / URL / ServletContext 加载
DefaultResourceLoader          → classpath: / file: / http:
ServletContextResourceLoader   → webapp 目录
```

---

## 七、适配器模式（Adapter Pattern）

### 7.1 HandlerAdapter

```java
// 不同的 Controller 有不同的调用方式，用适配器统一
public interface HandlerAdapter {
    boolean supports(Object handler);  // 我能处理这种 Handler 吗？
    ModelAndView handle(HttpServletRequest req, HttpServletResponse resp, Object handler);
}

// 适配器1：处理 @RequestMapping 注解的 Controller
RequestMappingHandlerAdapter → supports: 检查 handler 有没有 @RequestMapping

// 适配器2：处理实现了 Controller 接口的 Bean（老式）
SimpleControllerHandlerAdapter → supports: 检查 handler 是不是 Controller 接口的实现
```

### 7.2 AdvisorAdapter

```java
// 不同的通知类型（@Before/@After/@Around）需要不同的适配器
MethodBeforeAdviceAdapter  → 适配 @Before 通知
AfterReturningAdviceAdapter → 适配 @AfterReturning 通知
ThrowsAdviceAdapter        → 适配 @AfterThrowing 通知
```

---

## 八、责任链模式（Chain of Responsibility）

### 8.1 Filter 链

```java
// 单个 Filter
public class AuthFilter implements Filter {
    public void doFilter(req, resp, FilterChain chain) {
        if (checkAuth(req)) {
            chain.doFilter(req, resp);  // 通过 → 交给下一个
        } else {
            resp.sendError(401);        // 拦截 → 不往后走
        }
    }
}
```

### 8.2 Interceptor 链

```java
// 多个 HandlerInterceptor 按 @Order 组成责任链
LoginInterceptor → PermissionInterceptor → LogInterceptor
```

### 8.3 AOP 切面链

```
@Order(1) AuthorizationInterceptor
@Order(2) CachingAspect
@Order(3) TransactionInterceptor
@Order(4) LoggingAspect
    ↓
目标方法执行
```

---

## 九、Spring 设计模式全景表

| 设计模式 | Spring 中的应用 | 对应文档 |
| :--- | :--- | :--- |
| **工厂模式** | `BeanFactory`、`FactoryBean` | [02-容器与 Bean 注册](02-Spring%20容器与%20Bean%20注册.md) |
| **单例模式** | Bean 默认 scope=singleton | [03-Bean 作用域与生命周期](03-Bean%20作用域与生命周期.md) |
| **代理模式** | AOP（JDK / CGLIB）、@Lazy | [08-AOP 概念与代理机制](08-AOP%20概念与代理机制.md) |
| **模板方法** | `JdbcTemplate`、`RestTemplate`、`RedisTemplate` | 本篇 |
| **观察者模式** | `ApplicationEvent` + `@EventListener` | 本篇 |
| **策略模式** | `PlatformTransactionManager`、`ResourceLoader` | 本篇 |
| **适配器模式** | `HandlerAdapter`、`AdvisorAdapter` | [13-MVC 架构](13-Spring%20MVC%20架构与请求流程.md) |
| **责任链模式** | Filter 链、Interceptor 链、AOP 切面链 | [15-拦截器](15-拦截器与统一异常处理.md) |
| **装饰器模式** | `BeanWrapper` 包装 Bean | — |
| **建造者模式** | `RestTemplateBuilder`、Spring Security 配置链 | — |

---

## 🎯 面试高频

### Q1：Spring 中用到了哪些设计模式？

**答**：至少能说出这 6 个：

1. **工厂模式**：`BeanFactory` / `ApplicationContext` 是最大的工厂
2. **单例模式**：Bean 默认 scope=singleton（容器级别的单例，不同于传统单例）
3. **代理模式**：AOP 的核心实现（JDK 动态代理 + CGLIB 代理）
4. **模板方法模式**：`JdbcTemplate`、`RestTemplate` 等（骨架固定，细节回调）
5. **观察者模式**：`ApplicationEvent` / `@EventListener` 事件机制
6. **策略模式**：`PlatformTransactionManager` 不同事务管理器、`ResourceLoader` 不同资源加载策略

如果面试官继续追问，还可以提到**适配器模式**（`HandlerAdapter`）、**责任链模式**（Filter/Interceptor 链）、**建造者模式**（`RestTemplateBuilder`）。

### Q2：模板方法模式在 JdbcTemplate 中是怎么体现的？

**答**：`JdbcTemplate` 封装了 JDBC 操作的固定流程（获取连接 → 创建 Statement → 设置参数 → 执行 → 映射结果 → 处理异常 → 关闭连接），其中只有"设置参数"和"映射结果"两部分由调用者通过 `RowMapper`/`PreparedStatementSetter` 等回调接口指定。调用者只关心 SQL 和结果映射，不关心连接管理。

---

## 📌 在 Spring Boot 中

- Spring Boot 本身也是一个巨大的设计模式应用案例：自动配置 = 策略模式 + 条件装配，Starter = 工厂模式，内嵌 Tomcat = 适配器模式
- 理解了 Spring 的设计模式，你不仅能写好 Spring 代码，还能看懂 Spring 源码、写出类似的优雅框架
- 面试中这道题答得好，能直接让面试官对你有"框架理解深度不错"的印象

---

## 本章小结

| 设计模式 | 一句话 | Spring 中在哪 |
| :--- | :--- | :--- |
| 工厂 | 封装对象创建 | BeanFactory、FactoryBean |
| 单例 | 全局唯一 | Bean 默认 scope=singleton |
| 代理 | 方法拦截 | AOP、@Lazy、@Transactional |
| 模板方法 | 固定骨架 + 定制细节 | JdbcTemplate、RestTemplate |
| 观察者 | 发布-订阅解耦 | ApplicationEvent + @EventListener |
| 策略 | 算法可替换 | TransactionManager 实现 |
| 适配器 | 统一接口 | HandlerAdapter |
| 责任链 | 逐个处理 | Filter 链、Interceptor 链 |

---

## 学习建议

1. **把这张全景表背下来**：面试中"Spring 设计模式"是送分题——你不需要全部列出来，但工厂、单例、代理、模板方法、观察者这 5 个必须能脱口而出并各举一个 Spring 中的例子。
2. **读一遍 JdbcTemplate 源码**（不到 1000 行）：看它怎么把"获取连接-执行-映射-关连接"的流程定死，又怎么通过回调（`RowMapper`、`PreparedStatementCallback`）把变化部分暴露给你。
3. **在自己的项目中用 ApplicationEvent 解耦**。比如"创建订单"后你要做三件事（发短信、送积分、记日志），不要全写在 createOrder 方法里——发一个 `OrderCreatedEvent`，让三个 `@EventListener` 各管各的。