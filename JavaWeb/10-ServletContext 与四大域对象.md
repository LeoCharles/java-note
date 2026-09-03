# ServletContext 与四大域对象

前面几篇你反复见到 `setAttribute`/`getAttribute`——Request 有、Session 有、本篇讲的 ServletContext 也有。这些"存数据、取数据"的容器统称**域对象**（Scope Object）。本篇把四大域对象一次性讲清：它们各自的作用范围、生命周期、何时该用哪个，以及 `ServletContext` 这个"全局域"的特殊地位。最后落到一个关键认知——**ServletContext 的"容器管全局对象"思想，正是 Spring IoC 容器的雏形**。

> 💡 本篇建议写四个 Servlet，分别往 request/Session/ServletContext 域存数据，然后转发/重定向/新会话，观察数据在什么范围能取到——亲手验证四大域的边界。

---

## 一、域对象是什么

### 1.1 定义

**域对象**就是"在一定范围内能存取数据"的容器，本质是一组 `setAttribute`/`getAttribute`/`removeAttribute` 方法。不同域对象的区别就是**作用范围**和**生命周期**不同。

```java
// 所有域对象都有这三组方法
void setAttribute(String name, Object value);   // 存
Object getAttribute(String name);                // 取
void removeAttribute(String name);               // 删
Enumeration<String> getAttributeNames();         // 遍历
```

> 💡 **域对象 = 数据共享范围**：选哪个域，取决于"数据要共享给谁"。只给本次请求用 → request 域；给整个会话用 → Session 域；给全应用用 → ServletContext 域。理解了"范围"，就理解了域对象的本质。

### 1.2 四大域对象总览 ⭐

| 域对象 | 接口 | 作用范围 | 生命周期 | 典型用途 |
| :--- | :--- | :--- | :--- | :--- |
| **PageContext** | `javax.servlet.jsp.PageContext` | 当前 JSP 页面（最小） | 页面执行完销毁 | JSP 页内临时变量（现代少用） |
| **HttpServletRequest** | `javax.servlet.http.HttpServletRequest` | **一次请求**（转发链共享） | 请求结束销毁 | Controller→View 传值 |
| **HttpSession** | `javax.servlet.http.HttpSession` | **一次会话**（跨多次请求） | 超时/invalidate 销毁 | 登录态、购物车 |
| **ServletContext** | `javax.servlet.ServletContext` | **整个 Web 应用**（全局） | 应用启动到关闭 | 全局配置、共享资源 |

> ⚠️ **范围从小到大**：PageContext < request < Session < ServletContext。范围越大共享越广，但占用资源越久——**能用小范围就用小范围**，这是域对象选型的原则。

> 💡 **PageContext 现代少用**：它只在 JSP 页面内有效，前后端分离时代 JSP 本身就少用了。本篇重点讲后三个域（request/Session/ServletContext），PageContext 在 11-JSP 篇再细讲。

---

## 二、ServletContext 全局域 ⭐

### 2.1 它是什么

`ServletContext` 是整个 Web 应用的**全局上下文对象**，一个应用只有一个。它在应用启动时创建、关闭时销毁，所有 Servlet 共享这一个实例。

```java
// 在 Servlet 里获取 ServletContext
ServletContext ctx = getServletContext();   // HttpServlet 自带的方法

// 存全局数据
ctx.setAttribute("dataSource", ds);
// 取全局数据
DataSource ds = (DataSource) ctx.getAttribute("dataSource");
```

> 💡 **ServletContext 是"应用级单例"**：全应用一个，所有 Servlet 共享。它像应用的"公共仓库"——放连接池、全局配置、共享缓存。09 篇的 `ServletContextListener` 就是在它创建/销毁时触发。

### 2.2 获取方式

```java
// 方式一：HttpServlet 继承的 GenericServlet 提供
ServletContext ctx1 = getServletContext();

// 方式二：从 ServletConfig 获取
ServletContext ctx2 = getServletConfig().getServletContext();

// 方式三：从 Request 获取（推荐，最通用）
ServletContext ctx3 = req.getServletContext();

// 方式四：从 Session 获取
ServletContext ctx4 = session.getServletContext();
```

> 💡 **四种方式拿到的是同一个对象**：ServletContext 是应用级单例，无论从哪取都是它。实际开发从 Request 取最通用（Request 总能拿到）。

### 2.3 核心功能

ServletContext 不只是存数据，它还承担"应用级信息"的提供者：

```java
ServletContext ctx = req.getServletContext();

// 1. 全局初始化参数（web.xml 的 <context-param>）
String dbUrl = ctx.getInitParameter("dbUrl");

// 2. 资源路径（读 Web 目录下的文件）
String realPath = ctx.getRealPath("/WEB-INF/config.xml");
// D:\tomcat\webapps\myapp\WEB-INF\config.xml

// 3. 读资源流（读 classpath 下的文件）
InputStream in = ctx.getResourceAsStream("/WEB-INF/config.xml");

// 4. 应用信息
String ctxName = ctx.getServletContextName();  // 应用名
String serverInfo = ctx.getServerInfo();        // Tomcat/9.0.x
```

> 💡 **全局初始化参数**：`web.xml` 里用 `<context-param>` 配置，所有 Servlet 都能读，是"应用级配置"的方案。这就是 Spring Boot `application.yml` 的前身——把配置外部化、全局可读。

> ⚠️ **`getRealPath` 的局限**：它返回的是部署后的物理路径，在 war 部署时可用，但 jar 包运行（如 Spring Boot 内嵌 Tomcat）时路径不存在。所以**读资源优先用 `getResourceAsStream`**（读流不依赖物理路径），这是更可移植的写法。

### 2.4 全局共享数据

ServletContext 最典型的用途：存全局共享对象（连接池、缓存）。

```java
// 启动监听器里初始化并存入（09 篇讲过）
@WebListener
public class StartupListener implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        ServletContext ctx = sce.getServletContext();
        // 初始化连接池，存进全局域
        DataSource ds = createDataSource();
        ctx.setAttribute("dataSource", ds);   // 全应用共享
    }
}

// 任意 Servlet 取用
@WebServlet("/users")
public class UserServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) {
        ServletContext ctx = getServletContext();
        DataSource ds = (DataSource) ctx.getAttribute("dataSource");
        // 用 ds 查数据库
    }
}
```

> 💡 **这就是"容器管对象"的雏形**：连接池不在每个 Servlet 里 new，而是由"启动监听器"创建、存进 ServletContext、所有 Servlet 共享——**对象的生命周期交给容器管，业务代码只取用**。这正是 Spring IoC 容器的核心思想：对象的创建和注入由容器负责，业务代码不 new、只接收。Spring 的 `ApplicationContext` 就是 ServletContext 这个角色的进化。

---

## 三、四大域对象对比与选型 ⭐

### 3.1 作用范围对比

```
PageContext    ──────▶ 当前 JSP 页面（最小，页面结束即销毁）
request        ──────▶ 一次请求（转发链共享，请求结束销毁）
HttpSession    ──────▶ 一次会话（跨多次请求，超时/invalidate 销毁）
ServletContext ──────▶ 整个应用（全局，应用运行期间一直在）
```

### 3.2 数据可见性实验

写一个 Servlet，往四个域各存一份数据，然后用不同方式访问，看哪些能取到：

```java
@WebServlet("/scope")
public class ScopeServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        req.setAttribute("reqKey", "请求域数据");
        req.getSession().setAttribute("sessionKey", "会话域数据");
        getServletContext().setAttribute("appKey", "应用域数据");

        // 转发到另一个 Servlet（同一次请求）
        req.getRequestDispatcher("/scope2").forward(req, resp);
    }
}

@WebServlet("/scope2")
public class Scope2Servlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        // 转发链内：request 域能取到（同一次请求）
        resp.getWriter().write("reqKey=" + req.getAttribute("reqKey") + "<br>");
        // Session 域：能取到（同会话）
        resp.getWriter().write("sessionKey=" + req.getSession().getAttribute("sessionKey") + "<br>");
        // 应用域：能取到（全局）
        resp.getWriter().write("appKey=" + getServletContext().getAttribute("appKey"));
    }
}
```

| 访问方式 | request 域 | Session 域 | ServletContext 域 |
| :--- | :--- | :--- | :--- |
| 转发（同请求） | ✅ 能取 | ✅ | ✅ |
| 重定向（新请求） | ❌ 取不到 | ✅ | ✅ |
| 新会话（换浏览器） | ❌ | ❌ | ✅ |

> ⚠️ **request 域只在转发链内共享**：重定向是 2 次请求、新 Request，request 域数据丢失。这是 04 篇讲过的——重定向传数据要用 Session 或参数，不能用 request 域。

### 3.3 选型原则 ⭐

| 数据特征 | 选哪个域 | 理由 |
| :--- | :--- | :--- |
| 只给本次请求/转发链用 | **request** | 范围最小，用完即销毁，不占资源 |
| 跨请求但限于一个用户 | **Session** | 会话级，登录态、购物车 |
| 全应用共享、所有用户可见 | **ServletContext** | 全局，配置、连接池、缓存 |
| JSP 页内临时变量 | **PageContext** | 最小，现代少用 |

> 💡 **选型铁律：能用小范围就不用大范围**。数据只在本次请求用，绝不放 Session（占内存）；只在会话内用，绝不放 ServletContext（全局污染）。范围越大，资源占用越久、线程安全风险越大。

> ⚠️ **ServletContext 域的线程安全**：全局域被所有用户共享，多线程并发读写同一属性会出问题。放进去的对象要么是只读的（配置）、要么是线程安全的（`AtomicInteger`、连接池），**不要放可变业务状态**。

---

## 四、域对象的线程安全

| 域对象 | 线程安全 | 原因 |
| :--- | :--- | :--- |
| **request** | ✅ 安全 | 一次请求一个实例，不共享 |
| **Session** | ⚠️ 不安全 | 同一用户多请求并发操作同一 Session |
| **ServletContext** | ❌ 不安全 | 全应用共享，多用户并发访问 |
| **PageContext** | ✅ 安全 | 单页面单线程执行 |

> ⚠️ **域越大越不安全**：request 域天然线程安全（每请求一个），Session 域要防并发（同一用户 AJAX 并发），ServletContext 域最危险（全用户共享）。**放共享可变数据必须加同步或用线程安全类**。

> 💡 **Spring 的解法**：Spring 的 Bean 默认单例（类似 ServletContext 域），多线程共享——所以 Spring 要求**单例 Bean 不要存可变状态**（用 `ThreadLocal`、方法局部变量、原型作用域）。这正是本篇"全局域线程不安全"思想在 Spring 里的体现。

---

## 五、ServletContext 与 Spring 容器的关系 ⭐

这是本篇最关键的认知：**ServletContext 的"容器管全局对象"思想，是 Spring IoC 容器的直接前身**。

### 5.1 原生方案：ServletContext 管全局对象

```java
// 启动时创建，存进 ServletContext
ctx.setAttribute("dataSource", createDataSource());
ctx.setAttribute("userService", new UserService());

// 用时取出
UserService service = (UserService) ctx.getAttribute("userService");
```

**痛点**：
- 取对象要手动强转 `ctx.getAttribute`，类型不安全
- 对象之间的依赖（UserService 依赖 UserDao）要手动 new、手动注入
- 没有统一的生命周期管理

### 5.2 Spring 方案：ApplicationContext 管全局对象

```java
// Spring 容器（ApplicationContext）接管全局对象
@Configuration
public class AppConfig {
    @Bean
    public DataSource dataSource() { return createDataSource(); }
    @Bean
    public UserService userService(UserDao dao) { return new UserService(dao); }
}

// 用时注入，不用手动取
@RestController
public class UserController {
    @Autowired           // Spring 自动注入，类型安全
    private UserService userService;
}
```

> 💡 **ServletContext → ApplicationContext 的进化**：
> - **存取方式**：`ctx.getAttribute("key")` 强转 → `@Autowired` 类型安全注入
> - **依赖管理**：手动 new + 手动注入 → Spring 自动装配（DI）
> - **生命周期**：手动 init/destroy → `@PostConstruct`/`@PreDestroy` 容器管
> - **全局共享**：ServletContext 一个应用一个 → ApplicationContext 一个 Spring 容器一个
>
> **核心思想没变**：都是"对象交给容器管，业务代码只取用"。ServletContext 是这个思想的雏形，Spring 把它工程化、类型安全化、声明化了。

> ⚠️ **Spring 的 ApplicationContext 就注册在 ServletContext 里**：Spring MVC 启动时，把 `ApplicationContext` 存进 `ServletContext` 的一个属性（`setAttribute(WebApplicationContext.ROOT, ctx)`）。所以 Spring 容器本质就是"挂在 ServletContext 上的一个全局对象"——**Spring 没有脱离 Servlet 规范，而是在其之上封装**。

---

## ⚠️ 重点

1. **四大域对象**：PageContext（页面）/ request（请求）/ Session（会话）/ ServletContext（应用），范围从小到大。
2. **选型铁律：能用小范围就不用大范围**——本次请求用 request，会话用 Session，全局才用 ServletContext。
3. **request 域只在转发链共享**：重定向是新请求，request 域数据丢失。
4. **ServletContext 是全局单例**：一个应用一个，存全局配置、连接池、缓存。
5. **读资源优先 `getResourceAsStream`**：`getRealPath` 在 jar 运行时不可用。
6. **域越大越不安全**：request 安全、Session 要防并发、ServletContext 最危险。
7. **全局初始化参数**：`<context-param>` 配置，`getInitParameter` 读取，是 `application.yml` 的前身。
8. **ServletContext 是 Spring 容器的雏形**：容器管对象、全局共享——`ApplicationContext` 就是它的进化。

---

## 💻 实战案例：用域对象实现数据流转

需求：登录后把用户名存 Session，把"欢迎信息"存 request 域转发到结果页，把"应用启动时间"存 ServletContext 全局展示。

```java
// 1. 启动监听器：存全局启动时间
@WebListener
public class StartupListener implements ServletContextListener {
    @Override
    public void contextInitialized(ServletContextEvent sce) {
        sce.getServletContext().setAttribute("appStart", new Date());
    }
    @Override
    public void contextDestroyed(ServletContextEvent sce) { }
}

// 2. 登录 Servlet：Session 存用户，request 存欢迎信息，转发
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        req.setCharacterEncoding("utf-8");
        String username = req.getParameter("username");
        String password = req.getParameter("password");
        if ("admin".equals(username) && "123456".equals(password)) {
            // Session 域：存登录态（跨请求）
            req.getSession().setAttribute("user", username);
            // request 域：存欢迎信息（仅本次转发链）
            req.setAttribute("msg", "登录成功，欢迎 " + username);
            req.getRequestDispatcher("/home").forward(req, resp);
        } else {
            req.setAttribute("error", "用户名或密码错误");
            req.getRequestDispatcher("/login.html").forward(req, resp);
        }
    }
}

// 3. 首页：取三个域的数据展示
@WebServlet("/home")
public class HomeServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        PrintWriter out = resp.getWriter();
        // Session 域：登录用户
        String user = (String) req.getSession().getAttribute("user");
        // request 域：欢迎信息（转发链传来）
        String msg = (String) req.getAttribute("msg");
        // ServletContext 域：全局启动时间
        Date appStart = (Date) getServletContext().getAttribute("appStart");
        out.write("<h1>" + (msg != null ? msg : "欢迎 " + user) + "</h1>");
        out.write("<p>应用启动于：" + appStart + "</p>");
    }
}
```

> 💡 **三个域各司其职**：Session 存登录态（跨请求保持）、request 存一次性欢迎信息（转发链内）、ServletContext 存全局启动时间（全应用共享）。这就是域对象选型的标准用法——按数据特征选范围。Spring MVC 里 `Model` 对应 request 域、`HttpSession` 对应 Session 域、`@Component` 单例 Bean 对应 ServletContext 全局共享。

---

## 🚀 新版本补充

- **Servlet 3.0+**：`ServletContext` 可编程式注册 Servlet/Filter（`addServlet`/`addFilter`），Spring Boot 正是用这个动态注册 DispatcherServlet。
- **Servlet 3.1+**：`getResourceAsStream` 支持异步加载、`addClassMapping` 动态映射。
- **Spring Boot**：`ApplicationContext` 完全接管 ServletContext 的全局对象管理角色，并把它注册到 ServletContext 上（`WebApplicationContext.ROOT`）。

---

## 📌 在 Spring Boot 中

> 本篇讲的四大域对象、ServletContext 全局域、全局初始化参数、容器管对象的思想，在 Spring Boot 中由 `ApplicationContext` + `@Autowired` + `application.yml` 接管。下面逐一对照，给出实际开发代码，以及"出问题怎么回到域对象原理排查"。实际开发你几乎不直接操作 ServletContext——对象交给 Spring 容器管、配置用 yml、传值用 Model，但理解了本篇，Spring 的 IoC 容器、Bean 作用域、配置外部化对你就是透明的。

### 1. 全局对象管理：从"ServletContext.setAttribute"到"Spring 容器 @Bean"

**原生**：本篇 2.4 节把连接池存进 `ctx.setAttribute("dataSource", ds)`，用时 `getAttribute` 强转。
**Spring Boot**：`@Bean` 注册、`@Autowired` 注入，类型安全。

```java
@Configuration
public class AppConfig {
    @Bean                   // 等价 ctx.setAttribute("dataSource", ds)
    public DataSource dataSource() {
        return DataSourceBuilder.create()
                .url("jdbc:mysql://localhost:3306/test")
                .username("root").password("123456")
                .build();
    }
}

@RestController
public class UserController {
    @Autowired              // 等价 (DataSource) ctx.getAttribute("dataSource")，但类型安全
    private DataSource dataSource;
    // 或注入 Service（Spring 自动找依赖）
    @Autowired
    private UserService userService;
}
```

> 💡 **原理对应**：Spring 的 `ApplicationContext` 就是本篇 ServletContext 的进化——`@Bean` 等价 `setAttribute`（存全局对象），`@Autowired` 等价 `getAttribute`（取全局对象）。区别是 Spring 自动管理依赖（UserService 依赖 UserDao，Spring 自动注入），而原生要手动 new。**本篇的"容器管对象"思想，Spring 把它做到了极致**。

> 💡 **原理排查**：`@Autowired` 注入失败（NoSuchBeanDefinitionException）？检查类是否加了 `@Component`/`@Service`、是否在扫描包下、`@Bean` 方法是否在 `@Configuration` 类里。回到本篇原理：对象要先存进"容器"（ServletContext/ApplicationContext）才能取出来。

### 2. 全局配置：从"context-param"到"application.yml"

**原生**：`web.xml` 的 `<context-param>` + `ctx.getInitParameter("key")`。
**Spring Boot**：`application.yml` + `@Value`/`@ConfigurationProperties`。

```yaml
# application.yml（等价 <context-param>）
app:
  name: 学生管理系统
  db-url: jdbc:mysql://localhost:3306/test
  upload-path: D:/files
```

```java
@Component
public class AppConfig {
    @Value("${app.name}")           // 等价 ctx.getInitParameter("name")
    private String appName;

    @Value("${app.upload-path}")
    private String uploadPath;
}

// 批量绑定（推荐，类型安全）
@Component
@ConfigurationProperties(prefix = "app")
public class AppProperties {
    private String name;
    private String dbUrl;
    private String uploadPath;
    // getter/setter
}
```

> 💡 **原理对应**：`application.yml` 就是本篇 `<context-param>` 的进化——都是"配置外部化、全局可读"。`@Value`/`@ConfigurationProperties` 等价 `getInitParameter`，但类型安全、支持嵌套。**本篇的"全局初始化参数"，Spring Boot 用 yml + 注解绑定接管**。

> 💡 **原理排查**：`@Value` 注入 null 或启动报错？检查 yml 的 key 是否拼写一致、缩进是否正确（yml 严格缩进）、`@Value` 的 `${key}` 是否带默认值 `${key:default}`。回到本篇原理：配置要先在"全局配置源"里定义，才能读到。

### 3. request 域传值：从"setAttribute + forward"到"Model + 视图名"

**原生**：`req.setAttribute("user", user)` + `req.getRequestDispatcher("/page").forward`。
**Spring Boot**：`Model.addAttribute` + 返回视图名。

```java
@GetMapping("/user/{id}")
public String show(@PathVariable Long id, Model model) {
    User user = userService.findById(id);
    model.addAttribute("user", user);   // 等价 req.setAttribute
    return "user/detail";                 // 等价 forward 到模板
}
```

> 💡 **原理对应**：`Model` 底层就是往 request 域 `setAttribute`，返回视图名底层就是 `forward` 到模板。**本篇讲的"request 域用于转发链传值"，Spring MVC 用 Model 封装，数据流转路径完全一样**：Controller → request 域 → 模板。

### 4. Session 域：从"session.setAttribute"到"HttpSession / @SessionAttribute"

**原生**：`session.setAttribute("user", user)`。
**Spring Boot**：仍用 `HttpSession`，或 `@SessionAttribute`。

```java
@GetMapping("/profile")
public String profile(HttpSession session) {
    // 直接用 HttpSession，和原生一样
    User user = (User) session.getAttribute("user");
    return "profile";
}

// 或用 @SessionAttribute 自动注入
@GetMapping("/profile")
public String profile(@SessionAttribute("user") User user) {
    // user 自动从 Session 域取
    return "profile";
}
```

> 💡 **原理对应**：`@SessionAttribute` 底层就是 `session.getAttribute`。**本篇讲的 Session 域作用范围（跨请求、会话级），Spring Boot 完全一样**——Session 还是那个 Session，只是取值方式多了注解。

### 5. 全局共享：从"ServletContext.setAttribute"到"Spring 单例 Bean"

**原生**：`ctx.setAttribute("cache", cacheMap)` 全应用共享。
**Spring Boot**：`@Component` 单例 Bean 天然全局共享。

```java
@Component   // 单例，全应用共享（等价 ctx.setAttribute）
public class CacheManager {
    private final Map<String, Object> cache = new ConcurrentHashMap<>();

    public void put(String key, Object value) { cache.put(key, value); }
    public Object get(String key) { return cache.get(key); }
}

@RestController
public class UserController {
    @Autowired
    private CacheManager cacheManager;   // 任何地方注入都是同一个实例
}
```

> 💡 **原理对应**：Spring 单例 Bean 就是本篇 ServletContext 全局域的替代——`@Component` 标记的 Bean 全应用共享一个实例，等价 `ctx.setAttribute` 存全局对象。**但 Spring 的 Bean 是类型安全的、依赖自动注入的、生命周期由容器管的**，比手动 `getAttribute` 强转优雅得多。

> 💡 **原理排查**：全局缓存被多线程改坏？Spring 单例 Bean 共享，多线程并发访问可变状态不安全——本篇第四节强调的"全局域线程不安全"对 Spring 单例同样适用。**解法**：用 `ConcurrentHashMap`、`AtomicInteger`，或把可变状态放 `ThreadLocal`，或用 `@Scope("prototype")` 原型作用域。

### 6. 直接注入 ServletContext

少数场景需要原生 ServletContext（如读 `webapp` 下资源），可直接注入：

```java
@Component
public class ResourceReader {
    @Autowired
    private ServletContext servletContext;   // Spring 注入原生 ServletContext

    public String readConfig() throws IOException {
        // 读 webapp/WEB-INF/ 下的资源（jar 运行时可能不可用，优先用 classpath）
        try (InputStream in = servletContext.getResourceAsStream("/WEB-INF/config.xml")) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }
}
```

> 💡 **原理对应**：Spring 允许直接注入 `ServletContext`，底层就是本篇讲的那个全局对象。**本篇学的 ServletContext 方法（getRealPath/getResourceAsStream/getInitParameter），在 Spring Boot 里仍可用**——Spring 没有废弃它，只是提供了更优雅的替代（classpath 读资源、yml 配置、Bean 注入）。

> 💡 **原理排查**：`getRealPath` 返回 null？Spring Boot jar 包运行时没有解压目录，`getRealPath` 不可用——回到本篇 2.3 节强调的"读资源优先用 `getResourceAsStream` 或 classpath"。这是原生原理在 Spring Boot 部署模式下的直接体现。

---

> 一句话：**四大域对象是"数据共享范围"的分层**。Spring Boot 里你几乎不直接操作域——request 域用 `Model`、Session 域用 `HttpSession`/`@SessionAttribute`、全局域用 Spring 单例 Bean、配置用 `application.yml`。但底层还是这四个域，`ApplicationContext` 就挂在 ServletContext 上。理解了本篇的"选小不选大""全局域线程不安全""容器管对象"，Spring 的 IoC 容器、Bean 作用域、配置外部化对你就是顺理成章。**出 Bean 注入失败、配置读不到、全局状态被改坏问题时，你仍要回到本篇原理排查**：对象存进容器了吗、配置在全局源里吗、共享状态线程安全吗。

## 本章小结

本篇讲清了四大域对象：PageContext（页面，最小）、request（请求，转发链共享）、Session（会话，跨请求）、ServletContext（应用，全局）。重点掌握选型铁律（能用小范围就不用大范围）、request 域只在转发链共享（重定向丢失）、ServletContext 全局单例的用途与线程安全风险、读资源优先用 `getResourceAsStream`。最关键的认知：**ServletContext 的"容器管全局对象"思想是 Spring IoC 容器的直接前身**——`ApplicationContext` 就是它的类型安全、依赖注入、声明化进化。至此阶段四完成，Filter/Listener/ServletContext 三大组件你已掌握。下一篇 [11-JSP 基础与原理](11-JSP%20基础与原理.md) 进入阶段五，讲 JSP 的本质（编译为 Servlet）与模板引擎原理，理解 Spring MVC 视图解析的前身。
