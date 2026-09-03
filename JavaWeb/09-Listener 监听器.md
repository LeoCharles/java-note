# Listener 监听器

上一篇的 Filter 是"请求来了我拦截"，本篇的 **Listener**（监听器）是"发生了某件事我响应"——它是 Servlet 规范的**事件驱动**机制。应用启动时干点初始化、Session 创建时统计在线人数、属性被改了记个日志，这些都用 Listener。本篇讲清八大监听器的分类、`@WebListener` 注解、以及在线人数统计和启动初始化两大实战。这是 Spring Boot `@EventListener`/`CommandLineRunner` 的底层。

> 💡 本篇建议写一个 `HttpSessionListener`，在 `sessionCreated` 里打印"有人上线了"，在 `sessionDestroyed` 里打印"有人下线了"，访问几个页面观察 Session 的创建和销毁——亲眼看到事件驱动的过程。

---

## 一、Listener 是什么

### 1.1 定义

**Listener** 是 Servlet 规范的**监听器接口**，它监听三类事件：**域对象的创建与销毁**、**域对象属性的增删改**、**Session 相关的特殊事件**。事件发生时，容器自动调用监听器对应的方法。

```
某事件发生（如应用启动/Session创建/属性修改）
        ↓
容器感知到事件
        ↓
自动调用对应 Listener 的方法（你写的逻辑在这里执行）
```

> 💡 **Listener vs Filter**：Filter 拦截的是**请求**（每个请求都过），Listener 监听的是**事件**（特定事件发生才触发）。Filter 是"关卡"，Listener 是"观察者"。两者都是 Servlet 规范的组件，但触发机制不同。

> 💡 **这是"观察者模式"的官方实现**：Listener 就是观察者模式（Observer Pattern）——被观察者是域对象（ServletContext/Session/Request），观察者是你的 Listener。Spring 的 `ApplicationEvent`/`@EventListener` 也是这个模式的延伸。

---

## 二、八大监听器分类 ⭐

Servlet 规范定义了 **8 个监听器接口**，按监听对象分三类。不用死记，记住"监听什么"就懂了。

### 2.1 第一类：域对象的创建与销毁（3 个）

监听三大域对象（ServletContext/HttpSession/ServletRequest）何时被创建和销毁：

| 监听器接口 | 监听对象 | 触发时机 |
| :--- | :--- | :--- |
| `ServletContextListener` | 应用域（全局） | 应用启动/关闭 |
| `HttpSessionListener` | 会话域 | Session 创建/销毁 |
| `ServletRequestListener` | 请求域 | 每次请求开始/结束 |

```java
// 应用启动/关闭监听（最常用）
@WebListener
public class AppListener implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        // 应用启动时执行：初始化配置、加载缓存、连数据库
        System.out.println("应用启动了");
    }
    @Override
    public void contextDestroyed(ServletContextEvent sce) {
        // 应用关闭时执行：释放资源
        System.out.println("应用关闭了");
    }
}
```

> 💡 **ServletContextListener 是最重要的监听器**：它在应用启动时触发，是"做全局初始化"的标准位置——加载配置文件、初始化连接池、预热缓存。Spring Boot 的 `CommandLineRunner`/`@PostConstruct` 就是这个角色的工程化。

### 2.2 第二类：域对象属性的增删改（3 个）

监听三大域对象的 `setAttribute`/`removeAttribute` 操作：

| 监听器接口 | 监听对象 | 触发时机 |
| :--- | :--- | :--- |
| `ServletContextAttributeListener` | 应用域属性 | 全局属性增/删/改 |
| `HttpSessionAttributeListener` | 会话域属性 | Session 属性增/删/改 |
| `ServletRequestAttributeListener` | 请求域属性 | request 属性增/删/改 |

```java
@WebListener
public class SessionAttrListener implements HttpSessionAttributeListener {
    @Override
    public void attributeAdded(HttpSessionBindingEvent se) {
        // Session 里 setAttribute 了
        System.out.println("Session 加了属性: " + se.getName() + " = " + se.getValue());
    }
    @Override
    public void attributeRemoved(HttpSessionBindingEvent se) {
        System.out.println("Session 删了属性: " + se.getName());
    }
    @Override
    public void attributeReplaced(HttpSessionBindingEvent se) {
        System.out.println("Session 改了属性: " + se.getName());
    }
}
```

> 💡 **属性监听器用于审计/日志**：记录"谁在什么时候改了什么数据"。比如登录态存进 Session（`setAttribute("user", ...)`）时触发，可记录上线日志。

### 2.3 第三类：Session 相关特殊事件（2 个）

这两个监听器**不需要注册**（不用 `@WebListener`），而是让**被监听的对象自己实现接口**：

| 监听器接口 | 触发时机 | 特殊之处 |
| :--- | :--- | :--- |
| `HttpSessionBindingListener` | 对象被绑定到 Session / 从 Session 移除 | **对象实现接口**，不需注册 |
| `HttpSessionActivationListener` | Session 钝化（存磁盘）/ 活化（读回内存） | **对象实现接口**，用于集群 |

```java
// 让实体类实现 HttpSessionBindingListener
public class User implements HttpSessionBindingListener {
    private String name;
    // 省略构造/getter/setter

    @Override
    public void valueBound(HttpSessionBindingEvent event) {
        // 这个 User 对象被放进 Session 了
        System.out.println(name + " 被绑定到 Session");
    }
    @Override
    public void valueUnbound(HttpSessionBindingEvent event) {
        // 这个 User 对象被移出 Session 了（或 Session 销毁了）
        System.out.println(name + " 从 Session 解绑");
    }
}
```

```java
// 用法：setAttribute 时自动触发 valueBound
session.setAttribute("user", new User("张三"));   // 触发 valueBound
session.removeAttribute("user");                    // 触发 valueUnbound
```

> ⚠️ **BindingListener 不用注册**：前 6 个监听器要 `@WebListener` 注册，但 `HttpSessionBindingListener` 和 `HttpSessionActivationListener` 是让**对象自己实现接口**——对象被绑进 Session 时，容器检测到它实现了接口就自动回调。这是"被动触发"而非"主动监听"。

> 💡 **钝化/活化（Activation）**：Session 太多时，容器把不活跃的 Session 序列化到磁盘（钝化），用到再读回内存（活化）。`HttpSessionActivationListener` 让对象在钝化前/活化后做处理（如重新连接资源）。分布式集群场景才用到，单机开发几乎不碰。

### 2.4 八大监听器速记表

| 类别 | 监听器 | 监听什么 | 需注册 |
| :--- | :--- | :--- | :--- |
| 域创建销毁 | `ServletContextListener` | 应用启动/关闭 | ✅ |
| 域创建销毁 | `HttpSessionListener` | Session 创建/销毁 | ✅ |
| 域创建销毁 | `ServletRequestListener` | 请求开始/结束 | ✅ |
| 属性变更 | `ServletContextAttributeListener` | 全局属性增删改 | ✅ |
| 属性变更 | `HttpSessionAttributeListener` | Session 属性增删改 | ✅ |
| 属性变更 | `ServletRequestAttributeListener` | request 属性增删改 | ✅ |
| Session 特殊 | `HttpSessionBindingListener` | 对象绑入/移出 Session | ❌（对象实现） |
| Session 特殊 | `HttpSessionActivationListener` | Session 钝化/活化 | ❌（对象实现） |

> 💡 **记忆口诀**：6 个要注册（3 域创建销毁 + 3 属性变更），2 个不用注册（对象自己实现接口）。要注册的用 `@WebListener`，不用注册的让实体类实现接口。

---

## 三、@WebListener 注解配置

Servlet 3.0 后用 `@WebListener` 注解注册监听器，无需 `web.xml`：

```java
@WebListener
public class MyListener implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        ServletContext ctx = sce.getServletContext();
        // 读全局初始化参数
        String dbUrl = ctx.getInitParameter("dbUrl");
        System.out.println("启动，数据库地址：" + dbUrl);
    }
    @Override
    public void contextDestroyed(ServletContextEvent sce) { }
}
```

> ⚠️ **@WebListener 只能标在类上**：和 `@WebFilter`/`@WebServlet` 一样，注解配置取代了 `web.xml` 里的 `<listener>` 标签。一个应用可注册多个监听器，按注册顺序执行。

> 💡 **从事件对象取信息**：每个监听方法都传一个事件对象（`ServletContextEvent`/`HttpSessionEvent` 等），从中可取到域对象本身：`sce.getServletContext()`、`se.getSession()`。这是监听器操作域对象的入口。

---

## 四、实战一：在线人数统计 ⭐

经典应用：用 `HttpSessionListener` 统计当前在线人数。

```java
@WebListener
public class OnlineCountListener implements HttpSessionListener {

    // 在线人数（用原子类保证线程安全）
    public static final AtomicInteger onlineCount = new AtomicInteger(0);

    @Override
    public void sessionCreated(HttpSessionEvent se) {
        int count = onlineCount.incrementAndGet();
        System.out.println("有人上线，当前在线：" + count + " 人");
        // 把人数存进 ServletContext，供页面读取
        se.getSession().getServletContext()
          .setAttribute("onlineCount", count);
    }

    @Override
    public void sessionDestroyed(HttpSessionEvent se) {
        int count = onlineCount.decrementAndGet();
        System.out.println("有人下线，当前在线：" + count + " 人");
        se.getSession().getServletContext()
          .setAttribute("onlineCount", count);
    }
}
```

```java
// 显示在线人数的 Servlet
@WebServlet("/online")
public class OnlineServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        Integer count = (Integer) req.getServletContext().getAttribute("onlineCount");
        resp.getWriter().write("当前在线人数：" + (count == null ? 0 : count));
    }
}
```

> ⚠️ **线程安全**：Session 可能被多请求并发操作，人数计数用 `AtomicInteger` 而非 `int`。本篇强调：监听器是单例，共享状态要注意线程安全——这和 02 篇讲的"Servlet 单例非线程安全"同理。

> 💡 **在线人数的"准"与"不准"**：`sessionCreated` 在 Session 创建时触发，但用户可能只是访问了首页就走了（Session 还没销毁）。所以"在线人数"其实是"未超时的 Session 数"，是个近似值。要精确统计需配合前端心跳，这是原理层面的局限。

---

## 五、实战二：应用启动初始化 ⭐

另一个经典应用：用 `ServletContextListener` 在应用启动时做初始化（加载配置、建连接池）。

```java
@WebListener
public class StartupListener implements ServletContextListener {

    @Override
    public void contextInitialized(ServletContextEvent sce) {
        ServletContext ctx = sce.getServletContext();
        // 1. 加载配置文件
        String configPath = ctx.getInitParameter("configLocation");
        // 2. 初始化连接池（伪代码）
        // DataSource ds = DruidUtil.createDataSource(configPath);
        // 3. 存进 ServletContext，全局共享
        // ctx.setAttribute("dataSource", ds);
        System.out.println("应用启动初始化完成");
    }

    @Override
    public void contextDestroyed(ServletContextEvent sce) {
        // 关闭连接池等资源
        // DataSource ds = (DataSource) sce.getServletContext().getAttribute("dataSource");
        // ds.close();
        System.out.println("应用关闭，资源已释放");
    }
}
```

> 💡 **这就是 Spring Boot 启动流程的雏形**：Spring Boot 启动时加载配置（application.yml）、初始化 DataSource/Bean、注册组件——和这里的"启动初始化"本质一样，只是 Spring Boot 用 IoC 容器统一管理。`ServletContextListener` 是"应用级初始化"的原生方案。

> 💡 **全局初始化参数**：`web.xml` 里用 `<context-param>` 配置全局参数，监听器用 `ctx.getInitParameter("key")` 读取。这是"配置外部化"的雏形——Spring Boot 的 `application.yml` 是它的进化。

---

## ⚠️ 重点

1. **Listener 是事件驱动**：特定事件发生时容器自动回调，和 Filter 的"请求拦截"机制不同。
2. **八大监听器分三类**：3 个域创建销毁 + 3 个属性变更 + 2 个 Session 特殊。
3. **6 个要注册（@WebListener），2 个不用注册**（对象自己实现 `HttpSessionBindingListener`/`ActivationListener`）。
4. **ServletContextListener 最重要**：应用启动初始化的标准位置，是 `CommandLineRunner` 的前身。
5. **HttpSessionListener 统计在线人数**：Session 创建/销毁时增减计数。
6. **从事件对象取域对象**：`sce.getServletContext()`、`se.getSession()` 是操作域的入口。
7. **监听器是单例**：共享状态要注意线程安全，计数用 `AtomicInteger`。
8. **BindingListener 是被动触发**：对象实现接口，被绑进 Session 时自动回调，不用注册。

---

## 💻 实战案例：完整的启动初始化 + 在线统计

需求：应用启动时加载配置并打印、统计在线人数、用户登录时记录上线日志。

```java
// 1. 启动初始化监听器
@WebListener
public class StartupListener implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        ServletContext ctx = sce.getServletContext();
        ctx.setAttribute("appStartTime", System.currentTimeMillis());  // 记录启动时间
        System.out.println("=== 应用启动 ===");
    }
    @Override
    public void contextDestroyed(ServletContextEvent sce) {
        System.out.println("=== 应用关闭 ===");
    }
}

// 2. 在线人数监听器
@WebListener
public class OnlineCountListener implements HttpSessionListener {
    public static final AtomicInteger online = new AtomicInteger(0);
    @Override
    public void sessionCreated(HttpSessionEvent se) {
        int c = online.incrementAndGet();
        se.getSession().getServletContext().setAttribute("online", c);
    }
    @Override
    public void sessionDestroyed(HttpSessionEvent se) {
        se.getSession().getServletContext()
          .setAttribute("online", online.decrementAndGet());
    }
}

// 3. Session 属性监听（记录登录日志）
@WebListener
public class LoginLogListener implements HttpSessionAttributeListener {
    @Override
    public void attributeAdded(HttpSessionBindingEvent se) {
        if ("user".equals(se.getName())) {
            System.out.println("[登录日志] 用户上线: " + se.getValue()
                + "，SessionID=" + se.getSession().getId());
        }
    }
    @Override
    public void attributeRemoved(HttpSessionBindingEvent se) {
        if ("user".equals(se.getName())) {
            System.out.println("[登录日志] 用户下线: " + se.getValue());
        }
    }
    @Override
    public void attributeReplaced(HttpSessionBindingEvent se) { }
}
```

```java
// 测试 Servlet
@WebServlet("/test")
public class TestServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        HttpSession session = req.getSession();   // 触发 sessionCreated
        session.setAttribute("user", "张三");      // 触发 attributeAdded
        Integer online = (Integer) req.getServletContext().getAttribute("online");
        resp.getWriter().write("当前在线：" + online);
    }
}
```

> 💡 **三个监听器协作**：启动初始化、在线统计、登录日志——这是"事件驱动"在 Web 里的典型落地。Spring Boot 里这些全部由 `CommandLineRunner`、`@EventListener`、Spring Security 的事件机制接管，但事件驱动的思想完全一样。

---

## 🚀 新版本补充

- **Servlet 3.0+**：`@WebListener` 注解配置，无需 `web.xml`。
- **Servlet 4.0**：监听器接口未新增，但与 HTTP/2 兼容性更好。
- **Spring 事件**：Spring 的 `ApplicationEvent`/`ApplicationListener` 是 Listener 思想在 Spring 容器层面的扩展——监听的是容器事件而非 Servlet 域事件。

---

## 📌 在 Spring Boot 中

> 本篇讲的八大监听器、`@WebListener`、启动初始化、Session 事件，在 Spring Boot 中用 `@EventListener`/`ApplicationListener`/`CommandLineRunner` 接管。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 Listener 原理排查"。实际开发你几乎不写 Servlet 监听器——启动初始化用 `CommandLineRunner`，事件监听用 Spring 事件机制，但理解了本篇，Spring 的事件体系、Bean 生命周期对你就是透明的。

### 1. 启动初始化：从"ServletContextListener"到"CommandLineRunner / ApplicationRunner"

**原生**：本篇第五节用 `ServletContextListener.contextInitialized` 做启动初始化。
**Spring Boot**：`CommandLineRunner`/`ApplicationRunner`，在容器就绪后执行。

```java
@Component
public class StartupRunner implements CommandLineRunner {
    @Override
    public void run(String... args) {
        // 应用启动、容器就绪后执行（等价 contextInitialized）
        System.out.println("=== Spring Boot 启动完成 ===");
        // 加载缓存、预热数据、初始化配置
        cacheService.preheat();
    }
}

// ApplicationRunner：参数解析更友好（区分 --key=value）
@Component
public class MyAppRunner implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) {
        String profile = args.getOptionValues("spring.profiles.active").get(0);
        System.out.println("当前环境：" + profile);
    }
}
```

> 💡 **原理对应**：`CommandLineRunner` 在 Spring Boot 启动末尾、容器刷新完成后执行，和 `ServletContextListener.contextInitialized` 的时机对应——都是"应用就绪，开始干活"的钩子。**你本篇写的启动初始化，Spring Boot 用 `CommandLineRunner` 接管，还能注入任何 Bean**（原生 Listener 拿不到 Spring 容器的对象）。

> 💡 **原理排查**：`CommandLineRunner` 没执行？检查类是否加了 `@Component`、是否在 Spring Boot 的扫描包下、启动过程是否在它之前就报错了。回到本篇原理：启动钩子要容器加载到才触发。

### 2. 应用关闭：从"contextDestroyed"到"@PreDestroy / DisposableBean"

**原生**：`ServletContextListener.contextDestroyed` 释放资源。
**Spring Boot**：`@PreDestroy`/`DisposableBean`/`@Bean(destroyMethod=...)`。

```java
@Component
public class ResourceHolder {
    @PreDestroy   // Bean 销毁前执行（等价 contextDestroyed）
    public void cleanup() {
        System.out.println("释放连接池、关闭文件句柄");
    }
}

// 或实现 DisposableBean
@Component
public class MyBean implements DisposableBean {
    @Override
    public void destroy() {
        System.out.println("Bean 销毁");
    }
}
```

> 💡 **原理对应**：Spring 容器关闭时，对每个 Bean 调 `@PreDestroy`/`destroy()`，和 `contextDestroyed` 对应——都是"应用要关了，赶紧释放资源"。**本篇的销毁监听，Spring 用 Bean 生命周期方法接管**，粒度更细（每个 Bean 单独管理自己的资源）。

### 3. Session 事件：从"HttpSessionListener"到"Spring Session 事件"

**原生**：本篇第四节用 `HttpSessionListener` 统计在线人数。
**Spring Boot**：Spring Session 提供等价事件（`SessionCreatedEvent`/`SessionDestroyedEvent`）。

```java
@Component
public class SessionEventListener {

    @EventListener
    public void onSessionCreated(SessionCreatedEvent event) {
        // Session 创建（等价 sessionCreated）
        String sessionId = event.getSessionId();
        System.out.println("有人上线：" + sessionId);
    }

    @EventListener
    public void onSessionDestroyed(SessionDestroyedEvent event) {
        System.out.println("有人下线：" + event.getSessionId());
    }
}
```

> 💡 **原理对应**：Spring Session 把原生 `HttpSessionListener` 的事件转发成 Spring 事件，用 `@EventListener` 监听。**本篇的 Session 监听机制没变，只是从"实现接口"改成"注解监听事件"**——更解耦、更 Spring 风格。

> 💡 **原理排查**：`@EventListener` 不触发？检查是否用了 Spring Session（原生 HttpSession 事件不会转发成 Spring 事件）、`@EventListener` 方法是否在 Spring Bean 里、事件类型是否匹配。回到本篇原理：Session 事件靠容器感知 Session 创建/销毁触发。

### 4. 自定义事件：从"无"到"@EventListener + ApplicationEvent"

**原生**：Servlet 监听器只能监听规范预定义的 8 类事件，不能自定义事件。
**Spring Boot**：可发布任意自定义事件，`@EventListener` 监听——这是 Spring 对 Listener 思想的扩展。

```java
// 1. 定义事件
public class OrderCreatedEvent {
    private final Long orderId;
    public OrderCreatedEvent(Long orderId) { this.orderId = orderId; }
    public Long getOrderId() { return orderId; }
}

// 2. 发布事件（在业务代码里）
@Service
public class OrderService {
    @Autowired
    private ApplicationEventPublisher publisher;   // Spring 的事件发布器

    public void createOrder(Order order) {
        // 保存订单...
        publisher.publishEvent(new OrderCreatedEvent(order.getId()));  // 发布事件
    }
}

// 3. 监听事件（可多个监听器，互不干扰）
@Component
public class OrderEventListener {
    @EventListener
    public void sendNotification(OrderCreatedEvent event) {
        System.out.println("发短信通知，订单：" + event.getOrderId());
    }
    @EventListener
    public void updateStatistics(OrderCreatedEvent event) {
        System.out.println("更新统计，订单：" + event.getOrderId());
    }
}
```

> 💡 **原理对应**：Spring 的 `ApplicationEventPublisher`/`@EventListener` 是本篇"观察者模式"的通用化——**本篇只能监听 Servlet 规范定义的 8 类事件，Spring 让你能监听任意业务事件**。下单后发短信、记日志、更新统计，不用互相调用，靠事件解耦。这是本篇思想在业务层的延伸。

> 💡 **原理排查**：`@EventListener` 收不到事件？检查发布者和监听者是否都是 Spring Bean、事件类型是否匹配（子类事件也会触发父类监听器）、是否异步执行（`@Async` 的事件异常不会抛回发布者）。回到本篇原理：事件驱动靠"发布-订阅"，两边都要在容器里。

### 5. 属性变更：从"AttributeListener"到"Spring 不直接监听域属性"

**原生**：本篇 2.2 节用 `HttpSessionAttributeListener` 监听 Session 属性增删改。
**Spring Boot**：很少直接监听域属性——属性变更逻辑用业务代码显式处理，而非监听。

```java
// Spring Boot 里不推荐监听 Session 属性，而是显式处理
@PostMapping("/login")
public String login(String username, HttpSession session) {
    // 登录逻辑显式写在这里，而非靠 attributeAdded 监听
    session.setAttribute("user", username);
    logService.recordLogin(username);   // 显式调用，而非事件触发
    return "登录成功";
}
```

> 💡 **原理对应**：Spring Boot 倾向"显式调用"而非"隐式事件"——属性变更的副作用（记日志、发通知）直接在业务方法里写，不靠 `AttributeListener`。**本篇的属性监听器在 Spring Boot 里很少用**，因为 Spring 的设计哲学是"流程清晰可见"而非"隐式触发"。但理解了本篇，你才知道 Spring 为什么这么选。

### 6. 对象绑定：从"HttpSessionBindingListener"到"Spring 不常用"

**原生**：本篇 2.3 节让对象实现 `HttpSessionBindingListener`，绑进 Session 时触发。
**Spring Boot**：极少用——对象的生命周期由 Spring 容器管理，不靠 Session 绑定触发逻辑。

> 💡 **原理对应**：`HttpSessionBindingListener` 的"对象感知自己被放进 Session"在 Spring Boot 里几乎不用——Spring 的 Bean 生命周期由容器管（`@PostConstruct`/`@PreDestroy`），不依赖 Session 绑定。**但理解了本篇的"被动触发"机制，Spring 的 Bean 生命周期回调就不难懂**——都是"对象感知自身状态变化"。

---

> 一句话：**Listener 是 Servlet 规范的事件驱动机制**。Spring Boot 里你几乎不写 Servlet 监听器——启动初始化用 `CommandLineRunner`，关闭释放用 `@PreDestroy`，Session 事件用 Spring Session 事件，业务解耦用 `@EventListener` + 自定义事件。但所有这些，底层都是本篇讲的"观察者模式"——事件发生、容器感知、自动回调。理解了本篇的八大监听器、事件对象、注册机制，Spring 的事件体系、Bean 生命周期、启动钩子对你就是透明的。**出启动钩子不执行、事件监听不到、Session 统计不准问题时，你仍要回到本篇原理排查**：注册了吗、时机对吗、事件类型匹配吗、线程安全了吗。

## 本章小结

本篇讲清了 Listener：Servlet 规范的 8 个监听器接口，分三类——域创建销毁（`ServletContextListener`/`HttpSessionListener`/`ServletRequestListener`）、属性变更（3 个 `AttributeListener`）、Session 特殊（`BindingListener`/`ActivationListener`，对象自己实现不用注册）。重点掌握 `@WebListener` 注解配置、`ServletContextListener` 做启动初始化、`HttpSessionListener` 统计在线人数、从事件对象取域对象、监听器单例的线程安全。至此阶段四的三大组件（Filter/Listener/ServletContext）你已学了两个，下一篇 [10-ServletContext 与四大域对象](10-ServletContext%20与四大域对象.md) 收尾阶段四，讲清四大域对象的作用范围与"容器管理组件"的思想雏形。
