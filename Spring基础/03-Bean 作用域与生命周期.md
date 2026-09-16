# Bean 作用域与生命周期

前两篇学了 IoC 思想（为什么要用容器）和 Bean 注册（怎么把对象放进容器）。本篇深入一个 Bean 从"出生"到"销毁"的完整过程，以及**不同作用域下的 Bean 的行为差异**——这是理解 Spring 很多"不可思议行为"（比如 prototype 注入 singleton 失效、内部调用事务不生效）的关键。

> 💡 如果把前两篇比作"容器怎么存对象"，这篇就是"对象的档案管理"——什么时候生、生几个、什么时候死、死前要交代什么。

---

## 一、Bean 作用域

### 1.1 五种作用域

| 作用域 | 常量 | 含义 |
| :--- | :--- | :--- |
| **singleton** | `ConfigurableBeanFactory.SCOPE_SINGLETON` | **默认**。整个容器只有一个实例 |
| **prototype** | `ConfigurableBeanFactory.SCOPE_PROTOTYPE` | 每次获取都创建新实例 |
| **request** | `WebApplicationContext.SCOPE_REQUEST` | 每个 HTTP 请求一个实例（仅 Web 环境） |
| **session** | `WebApplicationContext.SCOPE_SESSION` | 每个 HTTP Session 一个实例（仅 Web 环境） |
| **application** | `WebApplicationContext.SCOPE_APPLICATION` | 整个 ServletContext 一个实例（仅 Web 环境） |

**指定作用域**：

```java
@Component
@Scope("prototype")  // 或 @Scope(ConfigurableBeanFactory.SCOPE_PROTOTYPE)
public class PrototypeBean { }

@Bean
@Scope("prototype")
public PrototypeBean prototypeBean() {
    return new PrototypeBean();
}
```

### 1.2 Singleton vs Prototype（核心对比）

```java
@Component
public class SingletonBean {
    public SingletonBean() {
        System.out.println("SingletonBean 构造了");
    }
}

@Component
@Scope("prototype")
public class PrototypeBean {
    public PrototypeBean() {
        System.out.println("PrototypeBean 构造了");
    }
}
```

```java
ApplicationContext ctx = ...;

// 每次 getBean 拿 singleton，都是同一个对象
SingletonBean s1 = ctx.getBean(SingletonBean.class);
SingletonBean s2 = ctx.getBean(SingletonBean.class);
System.out.println(s1 == s2);  // true —— 同一实例

// 每次 getBean 拿 prototype，都是新对象
PrototypeBean p1 = ctx.getBean(PrototypeBean.class);
PrototypeBean p2 = ctx.getBean(PrototypeBean.class);
System.out.println(p1 == p2);  // false —— 不同实例
```

> ⚠️ **易错点**：Singleton 在**容器启动时**就创建（预加载，ApplicationContext 的特性），Prototype 在**每次 getBean 时**才创建（懒加载）。如果你只在类上标了 `@Scope("prototype")` 但全程没 getBean，它的构造方法一次都不会执行。

### 1.3 大坑：Prototype 注入 Singleton ⭐

这是 Spring 新手最容易踩的坑之一：

```java
@Component
@Scope("prototype")
public class PrototypeBean { }

@Component
public class SingletonBean {
    @Autowired
    private PrototypeBean prototypeBean;  // ← 坑在这里

    public PrototypeBean getPrototypeBean() {
        return prototypeBean;
    }
}
```

```java
SingletonBean singleton = ctx.getBean(SingletonBean.class);
PrototypeBean p1 = singleton.getPrototypeBean();
PrototypeBean p2 = singleton.getPrototypeBean();
System.out.println(p1 == p2);  // true！说好的 prototype 每次获取新实例呢？！
```

**原因**：`SingletonBean` 是单例的，在容器启动时只**创建了一次**、只**注入了一次** `PrototypeBean`。之后每次调 `getPrototypeBean()` 返回的都是**创建时注入的那一个实例**。

**解决方案**：

| 方案 | 做法 | 适用场景 |
| :--- | :--- | :--- |
| **方案一：注入 ApplicationContext** | 每次手动 `ctx.getBean(PrototypeBean.class)` | 全年通用，但代码依赖 Spring API |
| **方案二：@Lookup 注解** | 在方法上标 `@Lookup`，Spring 通过 CGLIB 代理每次返回新实例 | 推荐，不依赖 Spring API |
| **方案三：ObjectFactory** | 注入 `ObjectFactory<PrototypeBean>`，调 `getObject()` 获取新实例 | Spring 原生支持 |
| **方案四：换作用域** | 用 request/session 作用域 + `@Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)` | Web 环境 |

```java
// 方案二：@Lookup（推荐）
@Component
public class SingletonBean {
    @Lookup  // ← Spring 会通过 CGLIB 代理重写这个方法
    public PrototypeBean getPrototypeBean() {
        return null;  // 方法体不重要，代理会覆盖
    }
}

// 方案三：ObjectFactory
@Component
public class SingletonBean {
    @Autowired
    private ObjectFactory<PrototypeBean> factory;

    public PrototypeBean getPrototypeBean() {
        return factory.getObject();  // 每次调都返回新实例
    }
}
```

> 💡 **认识本质**：这个坑的根源是"注入"只发生一次（单例 Bean 创建时）。注入的是引用，不是"获取逻辑"。要每次获取新实例，你需要的是"懒获取"机制（`@Lookup` / `ObjectFactory` / `getBean`），而不是"注入"。

---

## 二、Bean 生命周期全流程 ⭐⭐

这是 Spring 面试的超级大热门。一个 Bean 从创建到销毁，要经历以下阶段：

```
┌──────────────────────────────────────────────────────────────┐
│                     Bean 生命周期全景图                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 实例化（Instantiation）                                   │
│     constructor.newInstance()  调用构造方法创建对象              │
│                         │                                    │
│  2. 属性填充（Populate Properties）                            │
│     @Autowired 字段注入 / Setter 注入                          │
│                         │                                    │
│  3. BeanNameAware.setBeanName()                              │
│                         │                                    │
│  4. BeanFactoryAware.setBeanFactory()                        │
│                         │                                    │
│  5. ApplicationContextAware.setApplicationContext()           │
│                         │                                    │
│  6. BeanPostProcessor.postProcessBeforeInitialization()      │
│     ← 初始化前的后处理（@PostConstruct 也是在这被调用的）         │
│                         │                                    │
│  7. @PostConstruct 方法                                       │
│                         │                                    │
│  8. InitializingBean.afterPropertiesSet()                    │
│                         │                                    │
│  9. 自定义 init-method（@Bean(initMethod = "xxx")）            │
│                         │                                    │
│ 10. BeanPostProcessor.postProcessAfterInitialization()       │
│     ← 初始化后的后处理（AOP 代理在这里生成！）                    │
│                         │                                    │
│  ★★  Bean 就绪，可使用 ★★                                     │
│                         │                                    │
│ 11. @PreDestroy 方法                                          │
│                         │                                    │
│ 12. DisposableBean.destroy()                                 │
│                         │                                    │
│ 13. 自定义 destroy-method（@Bean(destroyMethod = "xxx")）      │
│                         │                                    │
│  ▼  Bean 销毁                                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 三个阶段：创建 → 初始化 → 销毁

```java
@Component
public class LifeCycleBean implements InitializingBean, DisposableBean,
        BeanNameAware, ApplicationContextAware {

    // ===== 阶段一：创建 =====
    public LifeCycleBean() {
        System.out.println("1. 构造方法");
    }

    @Autowired
    public void setDependency(SomeBean bean) {
        System.out.println("2. 属性填充 / @Autowired 注入");
    }

    // ===== Aware 接口（可选） =====
    @Override
    public void setBeanName(String name) {
        System.out.println("3. BeanNameAware: " + name);
    }

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        System.out.println("4. ApplicationContextAware");
    }

    // ===== 阶段二：初始化 =====
    @PostConstruct
    public void postConstruct() {
        System.out.println("5. @PostConstruct");
    }

    @Override
    public void afterPropertiesSet() {
        System.out.println("6. InitializingBean.afterPropertiesSet()");
    }

    public void customInit() {
        System.out.println("7. 自定义 init-method");
    }

    // ===== 阶段三：销毁 =====
    @PreDestroy
    public void preDestroy() {
        System.out.println("8. @PreDestroy");
    }

    @Override
    public void destroy() {
        System.out.println("9. DisposableBean.destroy()");
    }

    public void customDestroy() {
        System.out.println("10. 自定义 destroy-method");
    }
}
```

```java
@Configuration
public class AppConfig {
    @Bean(initMethod = "customInit", destroyMethod = "customDestroy")
    public LifeCycleBean lifeCycleBean() {
        return new LifeCycleBean();
    }
}
```

**输出顺序**：
```
1. 构造方法
2. 属性填充 / @Autowired 注入
3. BeanNameAware: lifeCycleBean
4. ApplicationContextAware
5. @PostConstruct
6. InitializingBean.afterPropertiesSet()
7. 自定义 init-method
（容器关闭时...）
8. @PreDestroy
9. DisposableBean.destroy()
10. 自定义 destroy-method
```

### 2.2 初始化回调的三种方式

| 方式 | 用法 | 优先级 | 推荐度 |
| :--- | :--- | :--- | :--- |
| `@PostConstruct` | 注解在方法上 | 最先执行 | ⭐⭐⭐ 推荐，与 Spring 耦合度最低 |
| `InitializingBean` | 实现接口的 `afterPropertiesSet()` | 中间 | ⭐ 不推荐，代码侵入 Spring 接口 |
| `@Bean(initMethod)` | 配置 `initMethod` 属性 | 最后执行 | ⭐⭐ 适合第三方类无法加注解时 |

```java
// ✅ 推荐：@PostConstruct
@Component
public class DataSourcePool {
    @PostConstruct
    public void init() {
        // 初始化连接池
    }
}

// ✅ 适合第三方库：initMethod
@Bean(initMethod = "start")
public SomeThirdPartyService someService() {
    return new SomeThirdPartyService();
}
```

### 2.3 BeanPostProcessor：Spring 最强大的扩展点 ⭐

`BeanPostProcessor`（Bean 后处理器）是 Spring 留给开发者的**最重要的扩展点**。它作用于**所有 Bean**，在初始化前后拦截：

```java
public interface BeanPostProcessor {
    // 在 @PostConstruct / afterPropertiesSet / initMethod 之前调用
    default Object postProcessBeforeInitialization(Object bean, String beanName) {
        return bean;  // 可以返回原对象，也可以返回代理对象
    }

    // 在初始化之后调用——AOP 代理就是在这里生成的！
    default Object postProcessAfterInitialization(Object bean, String beanName) {
        return bean;
    }
}
```

Spring 内部的多个重要机制都是 `BeanPostProcessor` 的子类实现的：

| 实现类 | 功能 |
| :--- | :--- |
| `AutowiredAnnotationBeanPostProcessor` | 处理 `@Autowired`、`@Value` 注入 |
| `CommonAnnotationBeanPostProcessor` | 处理 `@PostConstruct`、`@PreDestroy`、`@Resource` |
| `AnnotationAwareAspectJAutoProxyCreator` | **AOP 代理创建**（这里生成代理对象！） |
| `AsyncAnnotationBeanPostProcessor` | 处理 `@Async` 异步 |
| `TransactionAnnotationBeanPostProcessor` | 处理 `@Transactional` |

> 💡 **关键认知**：`@Autowired` 的注入、`@PostConstruct` 的调用、AOP 代理的生成——这些你以为的"Spring 魔法"，全都是一个个 `BeanPostProcessor` 干的。Spring 的设计哲学是"把功能拆成插件"，每个插件就是一个后处理器。

**自定义 BeanPostProcessor 示例**：

```java
@Component
public class MyBeanPostProcessor implements BeanPostProcessor {
    @Override
    public Object postProcessBeforeInitialization(Object bean, String beanName) {
        if (bean instanceof MyService) {
            System.out.println(">>> 初始化前拦截：" + beanName);
        }
        return bean;
    }

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        if (bean instanceof MyService) {
            System.out.println(">>> 初始化后拦截：" + beanName);
        }
        return bean;  // 如果要对 MyService 加代理，在这里返回代理对象
    }
}
```

### 2.4 销毁回调的三种方式

```java
@Component
public class ResourceCleaner {
    @PreDestroy  // ← 推荐
    public void cleanUp() {
        System.out.println("释放资源");
    }
}
```

```java
// 方式二：实现 DisposableBean
@Component
public class ResourceCleaner implements DisposableBean {
    @Override
    public void destroy() {
        System.out.println("释放资源");
    }
}

// 方式三：@Bean(destroyMethod)
@Bean(destroyMethod = "close")
public DataSource dataSource() {
    return new HikariDataSource();
}
```

> ⚠️ **注意**：prototype 作用域的 Bean **不会**触发销毁回调。Spring 只管理 singleton Bean 的完整生命周期，prototype Bean 创建后交给调用方，Spring 不再跟踪。需要释放资源的 prototype Bean，你得自己手动调销毁方法。

---

## 💻 实战案例

### 案例 1：观察完整生命周期

```java
@Component
public class OrderProcessor implements InitializingBean, DisposableBean,
        BeanNameAware, ApplicationContextAware {

    private DataSource dataSource;

    public OrderProcessor() {
        System.out.println("[1/9] ① 构造方法——对象实例化");
    }

    @Autowired
    public void setDataSource(DataSource ds) {
        this.dataSource = ds;
        System.out.println("[2/9] ② @Autowired 属性填充");
    }

    @Override
    public void setBeanName(String name) {
        System.out.println("[3/9] ③ BeanNameAware → " + name);
    }

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        System.out.println("[4/9] ④ ApplicationContextAware");
    }

    @PostConstruct
    public void postConstruct() {
        System.out.println("[5/9] ⑤ @PostConstruct——初始化");
    }

    @Override
    public void afterPropertiesSet() {
        System.out.println("[6/9] ⑥ InitializingBean.afterPropertiesSet()");
    }

    public void process() {
        System.out.println("[7/9] ⑦ ★ Bean 就绪，执行业务方法 ★");
    }

    @PreDestroy
    public void preDestroy() {
        System.out.println("[8/9] ⑧ @PreDestroy——即将销毁");
    }

    @Override
    public void destroy() {
        System.out.println("[9/9] ⑨ DisposableBean.destroy()——已销毁");
    }
}
```

### 案例 2：用 @Scope 注解配合 proxyMode 解决 Web 场景下的作用域问题

```java
// 场景：singleton 的 Controller 中注入 request 作用域的 LoginUser
@Component
@Scope(value = WebApplicationContext.SCOPE_REQUEST,
       proxyMode = ScopedProxyMode.TARGET_CLASS)
public class LoginUser {
    private String username;
    // getter/setter...
}

@RestController
public class OrderController {
    @Autowired
    private LoginUser loginUser;  // ← 实际注入的是代理对象

    @GetMapping("/order")
    public String getOrder() {
        // 每个请求的 LoginUser 都不同，但 Controller 是单例的
        // proxyMode = TARGET_CLASS 确保每次请求都拿到当前请求的 LoginUser
        return "用户 " + loginUser.getUsername() + " 的订单";
    }
}
```

> 💡 **proxyMode 原理**：`ScopedProxyMode.TARGET_CLASS` 会为 request/session 作用域的 Bean 生成一个 CGLIB 代理，注入到 singleton Bean 中的实际上是这个代理对象。每次调用代理的方法，代理都会去当前请求上下文中找真正的 Bean——这就是 Singleton 能注入 Request 作用域 Bean 的魔法。

---

## 🎯 面试高频

### Q1：Spring Bean 的生命周期是怎样的？

**答**：分三阶段——

1. **实例化**：调用构造方法创建对象
2. **初始化**：属性填充（`@Autowired`）→ Aware 接口 → `BeanPostProcessor.postProcessBeforeInitialization()` → `@PostConstruct` → `InitializingBean.afterPropertiesSet()` → `init-method` → `BeanPostProcessor.postProcessAfterInitialization()`（AOP 代理在这里生成）
3. **销毁**：`@PreDestroy` → `DisposableBean.destroy()` → `destroy-method`

### Q2：BeanPostProcessor 在什么时机执行？有什么作用？

**答**：在**每个 Bean 初始化前后**执行。`postProcessBeforeInitialization` 在 `@PostConstruct` 之前执行；`postProcessAfterInitialization` 在初始化完成后执行。

作用：是 Spring 最重要的扩展点。`@Autowired` 的注入、`@PostConstruct` 的调用、**AOP 代理的生成**、`@Async` 异步处理、`@Transactional` 事务处理——全部是各种 BeanPostProcessor 的实现类做的。

### Q3：prototype Bean 注入 singleton Bean 为什么无效？

**答**：因为 singleton Bean 只创建一次，它依赖的 prototype Bean 只在创建时注入一次。之后每次调 singleton 的方法访问的 prototype 字段，都是最初注入的那个实例。

解决：用 `@Lookup` 注解或注入 `ObjectFactory<PrototypeBean>`，让每次获取都走"懒获取"逻辑而不是用已注入的引用。

---

## 📌 在 Spring Boot 中

- **Spring Boot 大量使用 BeanPostProcessor**。你引入的每个 Starter，内部几乎都有 AutoConfiguration 类注册专用的 BeanPostProcessor——处理 `@Transactional`（`TransactionAnnotationBeanPostProcessor`）、处理 `@Async`（`AsyncAnnotationBeanPostProcessor`）、处理 `@Cacheable`（`CacheAnnotationBeanPostProcessor`）……
- **`@SpringBootApplication` 默认创建的都是 singleton Bean**。项目中 `@Service`、`@Controller`、`@Repository` 全部默认单例，无状态设计是 Spring Boot 的最佳实践——不要在 Bean 中存放请求级别的状态数据。
- **Spring Boot 的 `ApplicationRunner` / `CommandLineRunner`** 是在所有 Bean 初始化完成后、`@PostConstruct` 执行完毕后的回调，可用于启动后执行一次性任务。它本质是实现 `ApplicationListener<ApplicationReadyEvent>` 的简化版，执行时机在 Bean 完全就绪之后。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 五种作用域 | singleton（默认，全局唯一）、prototype（每次新建）、request/session/application（Web 环境） |
| Prototype 注入 Singleton 陷阱 | 单例只注入一次，prototype 形同虚设；用 @Lookup / ObjectFactory 解决 |
| 生命周期三阶段 | 实例化（构造）→ 初始化（@PostConstruct → afterPropertiesSet → initMethod）→ 销毁（@PreDestroy → destroy → destroyMethod） |
| 初始化回调三种方式 | @PostConstruct（推荐）> @Bean(initMethod)（第三方类）> InitializingBean（不推荐） |
| BeanPostProcessor | Spring 最强大的扩展点；AOP 代理、@Autowired、@Transactional 都是 BP 的子类实现 |
| 销毁回调 | singleton Bean 会触发；**prototype 不会**，需手动释放资源 |

---

## 学习建议

1. **把生命周期流程画出来**。拿出一张纸，从"构造方法"开始画到"destroy"，中间的每一步都标注"谁触发"和"什么用途"。这张图在面试中能直接默写出来。
2. **亲手触发 prototype 注入 singleton 的坑**：定义一个 @Scope("prototype") Bean，注入到 @Service 中，多次调用观察是否返回同一实例。再用 @Lookup 修复它。
3. **写一个自定义 BeanPostProcessor**：打印每个 Bean 在初始化前后的名称，观察 Spring Boot 启动时到底创建了多少 Bean、AOP 代理是何时生成的。
4. **prototype Bean 不触发 @PreDestroy 要记住**：代码 review 时看到 prototype Bean 里放了数据库连接的初始化逻辑、@PreDestroy 里写了关闭逻辑——直接指出来"这个 destroy 永远不会执行"。