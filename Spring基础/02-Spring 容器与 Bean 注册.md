# Spring 容器与 Bean 注册

上一篇你理解了 IoC 的思想——容器像个"超级 Map"，统一管理所有对象。本篇进入具体操作：**怎么把对象放进容器？怎么配置？容器本身有哪些类型？** 学完这篇，你就会用三种方式（XML、注解、Java Config）向 Spring 注册 Bean，并理解 `BeanFactory` 与 `ApplicationContext` 的区别。

> 💡 这篇是 Spring 基础中"最实用"的一篇——无论你写 Spring Boot 还是看老项目，注册 Bean 的操作每天都在发生。

---

## 一、Spring 容器体系

### 1.1 两个核心接口

Spring 容器有两个核心接口，经常被混淆：

```
BeanFactory（接口）                  ← 最底层的 IoC 容器接口
    ↑ extends
ApplicationContext（接口）            ← 应用上下文，继承 BeanFactory，增加企业级功能
    ↑ implements
ClassPathXmlApplicationContext      ← 从 XML 加载（经典 Spring）
AnnotationConfigApplicationContext  ← 从注解配置加载（现代 Spring）
```

| | `BeanFactory` | `ApplicationContext` |
| :--- | :--- | :--- |
| **定位** | 最基础的 IoC 容器 | 完整的企业级容器 |
| **Bean 实例化** | **懒加载**（用到才创建） | **预加载**（启动时全部创建 singleton Bean） |
| **国际化（i18n）** | ❌ | ✅ `MessageSource` |
| **事件发布** | ❌ | ✅ `ApplicationEventPublisher` |
| **资源加载** | ❌ | ✅ `ResourceLoader` |
| **AOP** | 需手动注册后处理器 | 自动支持 |
| **实际使用** | 几乎不用 | ✅ 这就是你每天用的容器 |

### 1.2 常用的 ApplicationContext 实现

```java
// 方式一：从 XML 配置文件加载（传统 Spring 项目）
ApplicationContext ctx = new ClassPathXmlApplicationContext("applicationContext.xml");

// 方式二：从注解配置类加载（现代 Spring / Spring Boot 底层）
ApplicationContext ctx = new AnnotationConfigApplicationContext(AppConfig.class);

// 方式三：Spring Boot 启动（最常用的方式）
// SpringApplication.run() 返回的就是一个 ApplicationContext
ApplicationContext ctx = SpringApplication.run(MyApp.class, args);
```

> 💡 **Spring Boot 的容器**：`SpringApplication.run()` 内部创建的就是 `AnnotationConfigApplicationContext`（Servlet 环境下是 `AnnotationConfigServletWebServerApplicationContext`，一个子类）。Boot 没有发明新容器，只是**自动往这个容器里注册 Bean**——这就是"自动配置"的本质。

---

## 二、三种 Bean 注册方式

Spring 提供了三种方式向容器注册 Bean，代表了三个历史阶段：XML → 注解 → Java Config。现代开发以**注解为主、Java Config 为辅**，XML 用于理解老项目。

### 2.1 方式一：XML 配置（传统方式，了解即可）

**步骤 1**：写一个普通的类

```java
public class UserDao {
    public void save(User user) {
        System.out.println("保存用户：" + user.getName());
    }
}
```

**步骤 2**：在 `applicationContext.xml` 中用 `<bean>` 标签声明

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
           http://www.springframework.org/schema/beans/spring-beans.xsd">

    <!-- 一个 <bean> = 一个对象 -->
    <bean id="userDao" class="com.example.dao.UserDao" />

    <!-- 带属性注入的 Bean -->
    <bean id="userService" class="com.example.service.UserService">
        <property name="userDao" ref="userDao" />  <!-- ref 引用另一个 Bean -->
    </bean>

</beans>
```

**步骤 3**：用 ClassPathXmlApplicationContext 加载

```java
ApplicationContext ctx = new ClassPathXmlApplicationContext("applicationContext.xml");
UserService service = ctx.getBean(UserService.class);
```

**XML 方式的致命缺陷**：
- 每加一个类就要写一段 `<bean>` 配置，工程大了 XML 会膨胀到几千行
- Bean 之间的依赖关系散落在 XML 中，IDE 无法检查类型安全
- 重构时改类名，XML 里的 `class` 属性不会自动更新，运行时才报 ClassNotFoundException

> 💡 Spring Boot 时代几乎不用 XML 配置 Bean，但**偶尔用 `@ImportResource` 导入遗留 XML 配置**。理解即可，不深究。

### 2.2 方式二：注解注册（现代主力）⭐

**核心机制**：在类上标注型注解 + `@ComponentScan` 自动扫描。

#### 2.2.1 @Component 系列注解

| 注解 | 含义 | 适用层 |
| :--- | :--- | :--- |
| `@Component` | 通用组件，"这是一个 Spring Bean" | 任意层 |
| `@Service` | 业务逻辑层组件（语义化） | Service 层 |
| `@Repository` | 数据访问层组件（语义化 + 自动异常翻译） | DAO/Repository 层 |
| `@Controller` | 控制层组件（Spring MVC） | Controller 层 |
| `@RestController` | REST 控制层组件（`@Controller` + `@ResponseBody`） | REST API 层 |

```java
// @Service 内部就是 @Component，只是多了一层语义
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Component  // ← @Service 本质就是 @Component
public @interface Service {
    @AliasFor(annotation = Component.class)
    String value() default "";
}
```

> ⚠️ **这五个注解在功能上完全等价**——用 `@Component` 和用 `@Service` 效果一模一样。分层注解是**语义化标签**，让人一眼看出这是哪一层的代码。特殊之处在于 `@Repository`：Spring 会自动将数据库异常转换为 `DataAccessException`。

#### 2.2.2 @ComponentScan 扫描机制

```java
@Configuration
@ComponentScan("com.example")   // 扫描 com.example 包及其所有子包
public class AppConfig { }
```

```java
// Spring Boot 的启动类自带 @ComponentScan
@SpringBootApplication  // ← 内部包含 @ComponentScan，默认扫描当前类所在包及子包
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyApplication.class, args);
    }
}
```

**扫描规则**：

```
com.example
    ├── service/
    │   ├── UserService.java      ← @Service → ✅ 扫描到，注册为 userService
    │   └── impl/
    │       └── UserServiceImpl.java ← @Service → ✅ 扫描到
    ├── dao/
    │   └── UserDao.java          ← @Repository → ✅ 扫描到
    └── util/
        └── StringUtils.java      ← 无注解 → ❌ 不会注册（除非被 @Bean 方法创建）
```

> ⚠️ **注意**：`@ComponentScan` 只扫描类上有 `@Component`（或其衍生注解）的类。没有标注解的普通类不会被注册。

#### 2.2.3 注解注册的完整示例

```java
// 接口
public interface UserDao {
    void save(User user);
}

// 实现类 → 用 @Repository 注册
@Repository
public class UserDaoImpl implements UserDao {
    public void save(User user) {
        System.out.println("保存用户：" + user.getName());
    }
}

// Service → 用 @Service 注册
@Service
public class UserService {
    @Autowired
    private UserDao userDao;   // 容器自动注入 UserDaoImpl

    public void register(User user) {
        userDao.save(user);
    }
}
```

```java
// 启动验证
public static void main(String[] args) {
    ApplicationContext ctx =
        new AnnotationConfigApplicationContext("com.example");
    UserService service = ctx.getBean(UserService.class);
    service.register(new User("张三", "123456"));
}
```

### 2.3 方式三：Java Config + @Bean（最灵活）⭐

当 Bean 的创建逻辑比较复杂（需要拼接参数、条件判断、第三方库对象）时，注解扫描不够用，需要 `@Configuration` + `@Bean` 手动控制。

```java
@Configuration   // ← 声明"这是一个配置类"，替代了 XML 配置文件
public class AppConfig {

    // @Bean 方法返回的对象会被放入容器
    @Bean
    public UserDao userDao() {
        return new UserDaoImpl();
    }

    // @Bean 可以灵活配置创建参数
    @Bean
    public DataSource dataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://localhost:3306/mydb");
        config.setUsername("root");
        config.setPassword("123456");
        config.setMaximumPoolSize(20);
        return new HikariDataSource(config);   // 第三方对象也能放进容器
    }

    // @Bean 方法的参数会自动从容器中注入
    @Bean
    public UserService userService(UserDao userDao) {  // userDao 自动注入
        return new UserService(userDao);
    }
}
```

> 💡 **`@Bean` 方法参数自动注入**：`userService(UserDao userDao)` 中，Spring 会自动从容器中取出 `userDao` Bean 传进来。这和 `@Autowired` 是同一种机制。

```java
// 加载配置类
ApplicationContext ctx = new AnnotationConfigApplicationContext(AppConfig.class);
UserService service = ctx.getBean(UserService.class);
```

### 2.4 三种方式的对比与选型

| | XML | 注解（@Component） | Java Config（@Bean） |
| :--- | :--- | :--- | :--- |
| **配置方式** | `<bean>` 标签 | 类上标注型 | `@Bean` 方法 |
| **侵入性** | 无侵入（类不知道被 Spring 管） | 侵入（类上贴了 Spring 注解） | 无侵入（类源码不改） |
| **创建逻辑** | 简单 | 简单 | ✅ 支持复杂逻辑和条件判断 |
| **适用场景** | 遗留系统 | ✅ 自己写的业务类（日常主力） | ✅ 第三方库对象 / 复杂初始化 |
| **类型安全** | ❌ 字符串，运行时才报错 | ✅ 编译期可检查 | ✅ 编译期可检查 |
| **现代使用** | 几乎不用 | ✅ 每天都用 | ✅ 配置类和 Starter 里常用 |

> 💡 **实际项目中的分工**：自己写的 Service/Controller/Repository → 用 `@Service`/`@Controller`/`@Repository`；第三方库对象（如 RestTemplate、DataSource、RedisTemplate）→ 在 `@Configuration` 类中用 `@Bean` 注册。

---

## 三、Bean 的命名规则

### 3.1 默认命名

| 注册方式 | 默认 Bean 名称 | 示例 |
| :--- | :--- | :--- |
| `@Component` / `@Service` 等 | 类名首字母小写 | `UserServiceImpl` → `userServiceImpl` |
| `@Bean` 方法 | 方法名 | `@Bean public DataSource dataSource()` → `dataSource` |
| XML `<bean>` | `id` 属性 | `<bean id="myDao" ...>` → `myDao` |

### 3.2 显式命名

```java
@Service("userService")         // 指定名称
public class UserServiceImpl implements UserService { }

@Bean(name = "myDataSource")    // 指定名称（也可用 value）
public DataSource dataSource() { return new HikariDataSource(); }

@Bean("appConfig, applicationConfig")  // 多个别名
public AppConfig appConfig() { return new AppConfig(); }
```

> ⚠️ **Bean 名称冲突**：同一容器中，同一个名称只能对应一个 Bean。如果两个类扫描出同样的名字（比如不同包下都有 `UserService`），Spring 会报 `ConflictingBeanDefinitionException`。

---

## 四、getBean 的几种方式

```java
ApplicationContext ctx = ...;

// 1. 按名称获取（需要强转）
UserService service1 = (UserService) ctx.getBean("userService");

// 2. 按类型获取（最常用，同名 Bean 有多个会报错）
UserService service2 = ctx.getBean(UserService.class);

// 3. 按名称 + 类型（最严谨）
UserService service3 = ctx.getBean("userService", UserService.class);

// 4. 获取同类型的所有 Bean
Map<String, UserService> beans = ctx.getBeansOfType(UserService.class);
```

> ⚠️ **开发中很少直接写 `getBean`**——因为你有 `@Autowired` / 构造器注入，依赖自动就来了。`getBean` 主要在**工具类、启动初始化、测试代码**中使用。

---

## 💻 实战案例

### 案例 1：三种注册方式的对比演示

```java
// ===== 方式一：XML 注册 =====
// applicationContext.xml
// <bean id="xmlDao" class="com.example.dao.UserDaoImpl" />

// ===== 方式二：注解注册（@Repository） =====
@Repository
public class AnnotationDao implements UserDao {
    @Override
    public void save(User user) {
        System.out.println("[注解注册] 保存用户：" + user.getName());
    }
}

// ===== 方式三：Java Config 注册（@Bean） =====
@Configuration
public class AppConfig {
    @Bean
    public UserDao configDao() {
        return new UserDao() {
            @Override
            public void save(User user) {
                System.out.println("[Java Config 注册] 保存用户：" + user.getName());
            }
        };
    }
}

// ===== 验证三种方式都能拿到 Bean =====
public class BeanRegisterDemo {
    public static void main(String[] args) {
        // XML 方式
        ApplicationContext xmlCtx =
            new ClassPathXmlApplicationContext("applicationContext.xml");
        UserDao xmlDao = xmlCtx.getBean("xmlDao", UserDao.class);
        xmlDao.save(new User("张三", "123456"));

        // 注解方式
        ApplicationContext annotationCtx =
            new AnnotationConfigApplicationContext("com.example.dao");
        UserDao annotationDao = annotationCtx.getBean(AnnotationDao.class);
        annotationDao.save(new User("李四", "654321"));

        // Java Config 方式
        ApplicationContext configCtx =
            new AnnotationConfigApplicationContext(AppConfig.class);
        UserDao configDao = configCtx.getBean("configDao", UserDao.class);
        configDao.save(new User("王五", "111111"));
    }
}
```

### 案例 2：理解 @Configuration 的"全配置"模式

被 `@Configuration` 标注的类本身也是一个 Bean（会被 CGLIB 代理），**多次调用同一个 @Bean 方法，返回的是同一个实例**（单例保证）：

```java
@Configuration
public class AppConfig {
    @Bean
    public UserDao userDao() {
        System.out.println(">>> 创建 UserDao");
        return new UserDaoImpl();
    }

    @Bean
    public UserService userService() {
        // 注意：这里直接调用 userDao()，不是又创建了一个新的
        // CGLIB 代理会拦截，从容器拿已有的，保证单例
        return new UserService(userDao());
    }

    @Bean
    public OrderService orderService() {
        // 同样，这里也不会创建新的 UserDao
        return new OrderService(userDao());
    }
}
```

```java
// 验证
ApplicationContext ctx = new AnnotationConfigApplicationContext(AppConfig.class);
UserDao dao1 = ctx.getBean(UserDao.class);
UserDao dao2 = ctx.getBean(UserDao.class);
System.out.println(dao1 == dao2); // true —— 同一个实例
// 输出：
// >>> 创建 UserDao  ← 只打印了一次！只调了一次真正的 new UserDaoImpl()
```

> 💡 这就是 `@Configuration` 的 CGLIB 代理机制：代理类拦截了 `userDao()` 调用，如果容器里已经有了，直接返回，不再执行方法体。但如果把 `@Configuration` 换成 `@Component`，这个代理就不生效了，每次调 `userDao()` 都会真的 new 一个新对象。

---

## 🎯 面试高频

### Q1：@Component 和 @Bean 有什么区别？

**答**：

| | `@Component` | `@Bean` |
| :--- | :--- | :--- |
| **作用位置** | 类上 | 方法上 |
| **注册方式** | 自动扫描 + 反射创建 | 手动调用方法创建 |
| **控制力** | 低——容器帮你 new | 高——你自己 `new`，自己传参 |
| **适用** | 自己写的类 | 第三方库类、需要复杂初始化的类 |
| **侵入性** | 侵入（类上贴了 Spring 注解） | 无侵入（类源码不用改） |

### Q2：@Configuration 和 @Component 有什么区别？

**答**：

- `@Configuration` 内部包含 `@Component`，所以配置类本身也是 Spring Bean
- **关键区别**：`@Configuration` 的类会被 **CGLIB 动态代理**，保证 `@Bean` 方法的单例语义（多次调用同一方法只返回同一实例）。而 `@Component` 类里的 `@Bean` 方法是"轻量级模式"（Lite Mode），不会被代理，多次调用会真的多次创建

```java
@Configuration
public class AppConfig {
    @Bean public A a() { return new A(); }
    @Bean public B b() { return new B(a()); } // a() 被拦截，返回单例
}

@Component  // Lite 模式
public class AppConfig {
    @Bean public A a() { return new A(); }
    @Bean public B b() { return new B(a()); } // a() 没被拦截，真调方法，每次 new A()
}
```

### Q3：@Repository 和 @Component 功能上一样吗？

**答**：功能上基本一样，都能让类被 Spring 扫描到并注册为 Bean。`@Repository` 额外有一个特性：**Spring 会将数据库操作抛出的原生异常（如 JDBC 的 SQLException）自动翻译为 Spring 统一的 `DataAccessException`**。这是通过 `PersistenceExceptionTranslationPostProcessor` 实现的。实际项目中建议 DAO 层用 `@Repository`。

---

## 📌 在 Spring Boot 中

- **Spring Boot 启动类上的 `@SpringBootApplication` 内部包含 `@ComponentScan`**，默认扫描启动类所在包及子包下的所有 `@Component`/`@Service`/`@Repository`/`@Controller`。这就是为什么你写个 `@Service` 不用做任何配置就能被自动注入——因为启动时它被扫描到了，放进了容器。
- **Spring Boot 的"自动配置"就是通过 `@Bean` 方式注册的**。Starter 里的 `XXXAutoConfiguration` 类用 `@Configuration` + `@Bean`，结合 `@ConditionalOnClass`/`@ConditionalOnMissingBean` 等条件注解，实现"引入了 jar 包就自动注册、你没自己配我才帮你配"的智能行为。
- **Spring Boot 不用写 `AnnotationConfigApplicationContext`**——`SpringApplication.run()` 一行就搞定了容器创建、扫描、启动 Web 服务器的全部流程。
- 学完本篇去读 [Spring实战/01-SpringBoot入门_HelloWorld](../Spring实战/01-SpringBoot入门_HelloWorld.md)，看 `@SpringBootApplication` 的三个核心注解：`@SpringBootConfiguration`（本质 `@Configuration`）、`@EnableAutoConfiguration`（自动配置入口）、`@ComponentScan`（组件扫描）。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| BeanFactory vs ApplicationContext | BeanFactory 是底层接口，ApplicationContext 是完整容器（预加载 + 事件 + 国际化 + AOP） |
| 三种注册方式 | XML `<bean>`（遗留）、注解 `@Component` 系列（日常主力）、Java Config `@Bean`（第三方/复杂对象） |
| @Component 衍生注解 | `@Service`/`@Repository`/`@Controller`/`@RestController`，功能等价，语义不同 |
| @ComponentScan | 自动扫描指定包下的 `@Component` 类并注册为 Bean |
| Bean 命名规则 | `@Component`：类名首字母小写；`@Bean`：方法名 |
| @Configuration 代理 | CGLIB 代理保证 `@Bean` 方法单例语义；@Component Lite 模式不代理 |
| getBean | 按名称/类型/名称+类型获取；开发中用 `@Autowired` 代替 |

---

## 学习建议

1. **三个 ApplicationContext 实现各跑一遍**：`ClassPathXmlApplicationContext`、`AnnotationConfigApplicationContext("包名")`、`AnnotationConfigApplicationContext(配置类.class)`——亲手感受三种加载方式的不同。
2. **刻意练习 @Bean 的使用场景**：写一个配置类，用 `@Bean` 注册一个带复杂构造参数的第三方对象（比如 HikariDataSource、RestTemplate），理解"为什么要用 @Bean 而不是 @Component"。
3. **记住分工规则**：自己写的类 → `@Service`/`@Repository`/`@Controller`；第三方库对象 → `@Configuration` + `@Bean`。不要在自己写的类上用 `@Bean`，也不要在第三方库类上贴 `@Component`。
4. **验证 @Configuration 的代理**：在配置类里 `@Bean` 方法中加 `System.out.println`，多次 getBean 观察打印几次；再把 `@Configuration` 换成 `@Component` 对比——亲眼验证 Lite 模式和 Full 模式的区别。