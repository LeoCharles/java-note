# Servlet 入门

上一篇你把 Tomcat 跑起来了，知道它能"接收请求、调用程序处理、返回响应"。但 Tomcat 调用的那个"程序"到底是什么？它怎么知道哪个请求该交给哪个程序？这个"程序"就是 **Servlet**——它是整个 Java Web 的核心，也是 Spring MVC 的底层。本篇讲清 Servlet 的体系结构、生命周期、配置方式，让你理解"一个 HTTP 请求是如何被 Servlet 接住的"。

> 💡 本篇是 Java Web 的心脏。建议边读边动手：写一个 Servlet、用 `@WebServlet` 配置路由、在浏览器访问它、在生命周期方法里打断点观察调用时机——理解了这些，Spring MVC 的 `@RestController` 对你就不再神秘。

---

## 一、Servlet 是什么

### 1.1 定义

**Servlet**（Server Applet）是运行在服务器端的 Java 小程序，它接收 HTTP 请求、处理业务、返回 HTTP 响应。它是 Java EE 的一套**规范（接口）**，定义在 `javax.servlet` 包（Tomcat 10+ 为 `jakarta.servlet`）中。

```
浏览器  ──HTTP 请求──▶  Tomcat（容器）  ──调用──▶  Servlet（你写的代码）
浏览器  ◀──HTTP 响应──  Tomcat（容器）  ◀──返回──  Servlet（你写的代码）
```

> 💡 **关键认知**：**Servlet 是接口，Tomcat 是容器**。你写的 Servlet 类不自己运行，而是被 Tomcat 实例化、调用。这和"JDBC 是接口、MySQL 驱动是实现"完全一个套路——面向接口编程，容器负责实现。

### 1.2 Servlet 的作用

Servlet 干三件事：

1. **接收**请求参数（表单数据、URL 参数、请求头）；
2. **处理**业务逻辑（查数据库、调服务、算结果）；
3. **生成**响应（写 HTML / JSON / 图片等返回给浏览器）。

> 💡 **Servlet vs Spring MVC 的 Controller**：Spring MVC 的 `@RestController` 方法本质也是干这三件事，只是把"取参数、写响应"的样板代码用 `@RequestParam`/`@ResponseBody` 封装了。底层请求仍由 DispatcherServlet（一个 Servlet）接收分发。

---

## 二、Servlet 体系结构 ⭐

Servlet 不是只有一个接口，而是一套继承体系。理解这个体系，才能看懂 Tomcat 源码和 Spring MVC 的设计。

### 2.1 继承链

```
javax.servlet.Servlet          ← 顶层接口，定义三个生命周期方法
    ↑ implements
GenericServlet                 ← 抽象类，通用实现（与协议无关）
    ↑ extends
HttpServlet                    ← 抽象类，针对 HTTP 协议封装（实际用它）
    ↑ extends
你写的 MyServlet               ← 具体类，重写 doGet/doPost
```

### 2.2 Servlet 接口

顶层接口，定义了五个方法，其中三个是**生命周期方法**：

| 方法 | 调用时机 | 作用 |
| :--- | :--- | :--- |
| `init(ServletConfig)` | **只调一次**，Servlet 被创建时 | 初始化（加载配置、连数据库等） |
| `service(req, resp)` | **每次请求**都调 | 处理请求、返回响应 |
| `destroy()` | **只调一次**，Servlet 被销毁时 | 释放资源（关连接、清理） |
| `getServletConfig()` | — | 获取配置信息 |
| `getServletInfo()` | — | 返回作者/版本等信息 |

### 2.3 GenericServlet

`Servlet` 接口与协议无关（可处理任意协议），`GenericServlet` 提供了通用实现：把 `init`/`destroy` 简化为空实现，让你只重写 `service`。但它仍不区分请求方法。

### 2.4 HttpServlet（实际开发用它）⭐

`HttpServlet` 针对 **HTTP 协议**做了封装：它重写了 `service()` 方法，内部根据**请求方法**（GET/POST/PUT/DELETE）分发到对应的 `doXxx` 方法：

```java
// HttpServlet 的 service 方法（简化版逻辑）
protected void service(req, resp) {
    String method = req.getMethod();   // 获取请求方法
    if ("GET".equals(method))      doGet(req, resp);
    else if ("POST".equals(method)) doPost(req, resp);
    else if ("PUT".equals(method))  doPut(req, resp);
    else if ("DELETE".equals(method)) doDelete(req, resp);
    // ...
}
```

**所以你写 Servlet 时**：继承 `HttpServlet`，**只重写 `doGet`/`doPost`** 即可，不用自己判断请求方法。

```java
@WebServlet("/hello")   // 注解配置访问路径
public class HelloServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        resp.setContentType("text/html;charset=utf-8");
        resp.getWriter().write("<h1>Hello, Servlet!</h1>");
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        // POST 请求通常调 doGet 统一处理，或单独写逻辑
        doGet(req, resp);
    }
}
```

> ⚠️ **不要重写 `service()` 方法**：`HttpServlet` 的 `service` 负责分发到 `doGet`/`doPost`，你重写它会破坏分发逻辑。**只重写 `doGet`/`doPost`**。

> 💡 **为什么 `doPost` 常调 `doGet`**：表单 POST 提交后，处理逻辑往往和 GET 查询一样，直接调 `doGet(req, resp)` 复用逻辑，避免重复代码。

---

## 三、Servlet 生命周期 ⭐

Servlet 对象由 Tomcat **创建和管理**，你 `new` 不出来。它的生命周期分三阶段，对应三个方法：

### 3.1 三个阶段

```
Tomcat 启动 / 首次请求
       │
       ▼
   1. 创建 Servlet 实例（构造方法，只一次）
   2. 调用 init()（只一次）—— 初始化
       │
       ▼
   3. 每次请求 → 调用 service() → 分发到 doGet/doPost（多次）
       │
       ▼
   4. Tomcat 关闭 → 调用 destroy()（只一次）—— 释放资源
```

| 阶段 | 方法 | 调用次数 | 说明 |
| :--- | :--- | :---: | :--- |
| 创建 | 构造方法 | 1 | Tomcat 反射创建实例 |
| 初始化 | `init()` | 1 | 加载配置、初始化资源 |
| 处理请求 | `service()` → `doGet/doPost` | N | 每次请求都调 |
| 销毁 | `destroy()` | 1 | 关闭连接、释放资源 |

### 3.2 验证生命周期的代码

```java
@WebServlet("/life")
public class LifeCycleServlet extends HttpServlet {
    public LifeCycleServlet() {
        System.out.println("1. 构造方法执行（只一次）");
    }

    @Override
    public void init() throws ServletException {
        System.out.println("2. init 执行（只一次）");
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        System.out.println("3. doGet 执行（每次请求都调）");
        resp.getWriter().write("check console");
    }

    @Override
    public void destroy() {
        System.out.println("4. destroy 执行（只一次，Tomcat 关闭时）");
    }
}
```

启动 Tomcat → 访问 `/life` 三次 → 关闭 Tomcat，控制台输出：

```
1. 构造方法执行（只一次）
2. init 执行（只一次）
3. doGet 执行（每次请求都调）
3. doGet 执行（每次请求都调）
3. doGet 执行（每次请求都调）
4. destroy 执行（只一次，Tomcat 关闭时）
```

### 3.3 何时创建 Servlet

默认情况下，Servlet 是**懒加载**——**第一次被访问时**才创建和 init。这意味着第一次访问会稍慢（要创建+初始化），后续访问复用同一个实例。

可用 `@WebServlet` 的 `loadOnStartup` 属性改为**启动时创建**：

```java
@WebServlet(urlPatterns = "/life", loadOnStartup = 1)   // 正数：Tomcat 启动时就创建
public class LifeCycleServlet extends HttpServlet { ... }
```

> 💡 **`loadOnStartup` 的值**：正数表示启动时创建（值越小优先级越高）；负数或不写表示首次访问时创建。Spring 的 DispatcherServlet 就是 `loadOnStartup=1`。

> ⚠️ **Servlet 是单例的**：整个 Web 应用中一个 Servlet 类只有一个实例，多个请求并发调用同一个实例的 `service`。**因此 Servlet 中不要用实例变量存请求状态**，会有线程安全问题——这就是"Servlet 非线程安全"的根源。

---

## 四、Servlet 的配置：url-pattern 匹配规则 ⭐

Tomcat 怎么知道哪个请求交给哪个 Servlet？靠 **url-pattern**（访问路径）匹配。Servlet 3.0+ 用 `@WebServlet` 注解配置，不再写 web.xml。

### 4.1 注解配置

```java
@WebServlet("/hello")                    // 精确匹配
@WebServlet(urlPatterns = "/hello")      // 等价写法
@WebServlet(urlPatterns = {"/hello", "/hi"})  // 多路径映射一个 Servlet
@WebServlet(urlPatterns = "/api/*", loadOnStartup = 1)  // 路径匹配 + 启动加载
```

### 4.2 匹配规则（优先级从高到低）

| 规则 | 写法 | 示例 | 说明 |
| :--- | :--- | :--- | :--- |
| 精确匹配 | `/xxx` | `/hello` | 路径完全一致才匹配 |
| 路径匹配 | `/xxx/*` | `/api/*` | `/api/` 下任意路径都匹配 |
| 扩展名匹配 | `*.xxx` | `*.do` | 以 `.do` 结尾都匹配 |
| 默认匹配 | `/` | `/` | 匹配所有未命中的请求 |

匹配优先级：**精确 > 路径 > 扩展名 > 默认**。

```java
// 优先级示例
@WebServlet("/api/user")      // 精确：只匹配 /api/user
@WebServlet("/api/*")         // 路径：匹配 /api/ 下所有
@WebServlet("*.do")           // 扩展名：匹配所有 .do 结尾
@WebServlet("/")              // 默认：兜底所有未命中的
```

> ⚠️ **扩展名匹配不能以 `/` 开头**：`*.do` 正确，`/*.do` 错误。这是初学者高频错误。
>
> ⚠️ **路径匹配和扩展名匹配不能混用**：`/api/*.do` 是非法写法，Tomcat 启动会报错。要么 `/api/*`，要么 `*.do`，二选一。

> 💡 **Spring MVC 怎么处理路由**：Spring MVC 的 DispatcherServlet 映射 `/`（拦截所有），然后内部用 `@GetMapping`/`@PostMapping` 精确匹配到 Controller 方法。本质还是这套 url-pattern 规则，只是把匹配逻辑从 Tomcat 移到了框架内部。

---

## 五、Servlet 3.0 注解 vs web.xml

### 5.1 传统 web.xml 方式（了解）

Servlet 3.0 之前，配置 Servlet 要写 `web.xml`：

```xml
<servlet>
    <servlet-name>helloServlet</servlet-name>
    <servlet-class>com.example.HelloServlet</servlet-class>
</servlet>
<servlet-mapping>
    <servlet-name>helloServlet</servlet-name>
    <url-pattern>/hello</url-pattern>
</servlet-mapping>
```

一个 Servlet 要写两段配置，繁琐且易错。

### 5.2 注解方式（推荐）

```java
@WebServlet("/hello")
public class HelloServlet extends HttpServlet { ... }
```

一行注解搞定。本系列默认用注解，不再写 web.xml。

> 💡 **注解配置的前提**：Servlet 3.0+ 且 Tomcat 7+。需确保 `web.xml` 的 `version` 是 3.0+，或干脆不建 web.xml（Tomcat 自动用注解扫描）。Maven 项目里 Servlet API 用 3.1+ 即可。

📌 **Spring Boot 对应**：Spring Boot 完全抛弃了 web.xml，连 `@WebServlet` 都很少手写——用 `@RestController` + `@GetMapping` 配置路由，底层 DispatcherServlet 统一接管。但"URL 匹配到处理逻辑"这个核心思想，从 url-pattern 到 `@GetMapping` 一脉相承。

---

## 六、ServletConfig 与初始化参数

每个 Servlet 有一个 `ServletConfig`，用于读取**该 Servlet 自己的初始化参数**。

### 6.1 注解配置初始化参数

```java
@WebServlet(urlPatterns = "/config",
            initParams = @WebInitParam(name = "encoding", value = "UTF-8"))
public class ConfigServlet extends HttpServlet {
    @Override
    public void init() throws ServletException {
        String encoding = getInitParameter("encoding");   // 读初始化参数
        System.out.println("encoding = " + encoding);
    }
}
```

### 6.2 全局参数：ServletContext

`ServletContext` 是整个 Web 应用共享的上下文对象（下一篇 10 详解），存全局参数：

```java
// web.xml 配置全局参数（或注解）
<context-param>
    <param-name>dbUrl</param-name>
    <param-value>jdbc:mysql://localhost:3306/test</param-value>
</context-param>

// 代码读取
String dbUrl = getServletContext().getInitParameter("dbUrl");
```

> 💡 **ServletConfig vs ServletContext**：Config 是单个 Servlet 的配置（私有）；Context 是整个 Web 应用的配置（全局共享）。这就像 Spring 的 `@Value`（单个 Bean 配置）vs `Environment`（全局环境配置）。

---

## ⚠️ 重点

1. **Servlet 是接口，Tomcat 是容器**：你写的 Servlet 被 Tomcat 实例化和调用，不是自己 `new`。
2. **继承 HttpServlet，只重写 doGet/doPost**：不要重写 `service()`，它会破坏请求方法分发。
3. **生命周期三阶段**：构造+init（一次）→ service/doGet（多次）→ destroy（一次）。
4. **Servlet 是单例，非线程安全**：不要用实例变量存请求状态，并发会串数据。
5. **默认懒加载**：首次访问才创建；`loadOnStartup` 正数改为启动时创建。
6. **url-pattern 优先级**：精确 > 路径 > 扩展名 > 默认。
7. **扩展名匹配不以 `/` 开头**：`*.do` 对，`/*.do` 错；路径和扩展名不能混用。
8. **Servlet 3.0+ 用注解**：`@WebServlet` 取代 web.xml，本系列默认注解。

---

## 💻 实战案例：一个完整的 Servlet

需求：写一个处理用户查询的 Servlet，GET 请求传 `id` 参数，返回用户信息（模拟）。

```java
@WebServlet("/user")
public class UserServlet extends HttpServlet {

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        // 1. 接收参数
        String idStr = req.getParameter("id");
        resp.setContentType("text/html;charset=utf-8");

        // 2. 参数校验
        if (idStr == null || idStr.isEmpty()) {
            resp.getWriter().write("<h1>缺少 id 参数</h1>");
            return;
        }

        // 3. 处理业务（模拟查数据库）
        int id = Integer.parseInt(idStr);
        String name = "用户" + id;   // 实际应调 Service/DAO
        int age = 20 + id;

        // 4. 生成响应
        resp.getWriter().write(
            "<h1>用户信息</h1>" +
            "<p>ID: " + id + "</p>" +
            "<p>姓名: " + name + "</p>" +
            "<p>年龄: " + age + "</p>"
        );
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        doGet(req, resp);   // POST 统一交给 GET 处理
    }
}
```

访问 `http://localhost:8080/user?id=5`，看到用户信息页面。

> 💡 **这个 Servlet 的四步结构**（取参 → 校验 → 业务 → 响应）就是所有 Web 请求处理的通用骨架。Spring MVC 的 `@GetMapping` 方法也是这四步，只是用注解把"取参"和"响应"简化了：
> ```java
> @GetMapping("/user")
> public User getUser(@RequestParam int id) {  // 取参+校验
>     return userService.findById(id);          // 业务
>     // 响应自动序列化为 JSON（@ResponseBody）
> }
> ```

---

## 🚀 新版本补充

- **Servlet 3.0**：注解配置（`@WebServlet`/`@WebFilter`）、异步 Servlet、文件上传（`@MultipartConfig`）。
- **Servlet 3.1**：非阻塞 IO、`ReadListener`/`WriteListener`，提升吞吐量。
- **Servlet 4.0**：支持 HTTP/2。
- **Tomcat 10 / Jakarta EE 9+**：包名从 `javax.servlet` 改为 `jakarta.servlet`，Spring Boot 3.x 已跟进。

---

## 📌 在 Spring Boot 中

> 本篇讲的 Servlet 体系、生命周期、url-pattern、注解配置，在 Spring Boot 中被 `@RestController` + `@GetMapping` 全面封装。下面逐一对照，给出实际开发代码，以及"出问题怎么回到原理排查"。实际开发你几乎不手写 Servlet，但理解了本篇，Spring MVC 的路由、单例、生命周期对你就是透明的。

### 1. 从"继承 HttpServlet"到"@RestController"

**原生**：继承 `HttpServlet`，重写 `doGet`/`doPost`，手动取参、写响应。

```java
@WebServlet("/user")
public class UserServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        String id = req.getParameter("id");
        resp.setContentType("text/html;charset=utf-8");
        resp.getWriter().write("user " + id);
    }
}
```

**Spring Boot**：`@RestController` + `@GetMapping`，不继承任何类，注解搞定路由和参数。

```java
@RestController
@RequestMapping("/user")
public class UserController {

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);   // 返回对象，自动序列化为 JSON
    }

    @PostMapping
    public User create(@RequestBody User user) {
        return userService.save(user);
    }
}
```

> 💡 **原理对应**：Spring MVC 的 `DispatcherServlet` **本身就是一个 Servlet**（继承 `HttpServlet`），它映射 `/` 拦截所有请求，然后根据 `@GetMapping`/`@PostMapping` 把请求分发到对应 Controller 方法。你写的 Controller 不是 Servlet，但请求最终仍由 DispatcherServlet 这个 Servlet 接收和分发——**Servlet 的体系结构和生命周期，一个都没少**。

> 💡 **原理排查**：接口 404？原生查 `@WebServlet` 路径对不对，Spring Boot 查 `@GetMapping` 路径、`@RestController` 是否被组件扫描（`@ComponentScan` 范围）、`@RequestMapping` 前缀是否拼对。排查逻辑都是"请求路径 → 匹配规则 → 处理方法"。

### 2. 请求方法分发：从"doGet/doPost"到"@GetMapping/@PostMapping"

**原生**：`HttpServlet.service()` 根据请求方法分发到 `doGet`/`doPost`，你重写对应方法。
**Spring Boot**：注解直接声明方法。

| 原生方法 | Spring Boot 注解 | 语义 |
| :--- | :--- | :--- |
| `doGet` | `@GetMapping` | 查询 |
| `doPost` | `@PostMapping` | 新增 |
| `doPut` | `@PutMapping` | 修改 |
| `doDelete` | `@DeleteMapping` | 删除 |
| `doPatch` | `@PatchMapping` | 局部修改 |

> 💡 **原理对应**：`@GetMapping` 底层仍是判断 `req.getMethod()` 是否为 GET，只是从"重写方法"变成"注解标记"。DispatcherServlet 内部做的方法分发逻辑，和 `HttpServlet.service()` 的分发思路一致。

> 💡 **原理排查**：接口返回 405 Method Not Allowed？原生是"只重写了 doGet 却收到 POST"，Spring Boot 是"`@GetMapping` 的接口收到 POST 请求"。检查请求方法和注解是否匹配——这是 RESTful 设计的基本功。

### 3. 生命周期：从"init/service/destroy"到"Bean 生命周期"

**原生**：`init`（创建时）→ `service`（每次请求）→ `destroy`（销毁时）。
**Spring Boot**：Controller 是 Spring Bean，生命周期由 IoC 容器管理。

```java
@RestController
public class UserController {
    public UserController() { /* 构造方法，Bean 创建时 */ }

    @PostConstruct
    public void init() { /* 等价 Servlet 的 init()，Bean 初始化后调用 */ }

    @PreDestroy
    public void destroy() { /* 等价 Servlet 的 destroy()，容器关闭前调用 */ }

    @GetMapping("/user")
    public User get() { return ...; }   // 每次请求调用，等价 service()
}
```

> 💡 **原理对应**：Servlet 的 `init`/`destroy` 对应 Spring Bean 的 `@PostConstruct`/`@PreDestroy`；Servlet 单例对应 Spring Bean 默认单例。**两者都是"单例 + 多线程并发调用"**，所以 Controller 里同样不要用实例变量存请求状态——线程安全问题和 Servlet 一模一样。

> 💡 **原理排查**：Controller 里用了实例变量存请求数据，多用户并发会串数据？这是"Servlet 单例非线程安全"的同一个问题。解决：用方法局部变量或 `ThreadLocal`，和 Servlet 时代的做法一致。

### 4. url-pattern：从"@WebServlet 路径"到"@RequestMapping 路径"

**原生**：`@WebServlet("/user")` 配置访问路径，Tomcat 按 url-pattern 规则匹配。
**Spring Boot**：`@RequestMapping` + `@GetMapping` 配置路径，DispatcherServlet 映射 `/` 后内部按注解匹配。

```java
@RestController
@RequestMapping("/api/v1/user")    // 类级前缀
public class UserController {
    @GetMapping("/{id}")            // → GET /api/v1/user/{id}
    @GetMapping                     // → GET /api/v1/user
    @PostMapping("/batch")         // → POST /api/v1/user/batch
}
```

> 💡 **原理对应**：DispatcherServlet 映射 `/`（拦截所有，等价原生默认匹配），内部用 `@RequestMapping` 精确匹配到方法。**匹配优先级和原生 url-pattern 一致**：精确 > 路径变量 > 通配。

> 💡 **原理排查**：路径变量取不到值？检查 `@PathVariable` 名字和 URL `{id}` 是否一致；多个接口路径冲突？Spring 启动会报 `Ambiguous mapping`，和原生 url-pattern 冲突本质一样。

### 5. loadOnStartup：从"启动加载"到"DispatcherServlet 默认启动加载"

**原生**：`@WebServlet(loadOnStartup=1)` 让 Servlet 在 Tomcat 启动时就创建（而非首次访问）。
**Spring Boot**：DispatcherServlet 默认 `loadOnStartup=1`，启动时就初始化，所以第一个请求不会慢。

> 💡 **原理对应**：你本篇学的"懒加载 vs 启动加载"，Spring MVC 默认选了启动加载——保证第一个请求的响应速度。理解了这个，就不会疑惑"为什么 Spring Boot 启动慢一点但第一个请求快"。

### 6. ServletConfig 初始化参数：从"@WebInitParam"到"@Value"

**原生**：`@WebInitParam` 配 Servlet 私有参数，`getInitParameter` 读。
**Spring Boot**：`@Value` 注入配置，或 `@ConfigurationProperties` 批量绑定。

```java
@RestController
public class UserController {
    @Value("${user.default.name:guest}")   // 读 application.yml，默认 guest
    private String defaultName;
}
```

```yaml
# application.yml
user:
  default:
    name: 张三
```

> 💡 **原理对应**：`ServletConfig` 是单个 Servlet 的私有配置，对应 `@Value`（单个 Bean 的配置注入）；`ServletContext` 是全局配置，对应 `Environment`/`@ConfigurationProperties`（全局配置绑定）。

---

> 一句话：**Spring MVC 的 DispatcherServlet 本身就是一个 Servlet**，它把"接收所有请求 → 按 URL 分发到 Controller 方法 → 取参 → 调业务 → 写响应"这套流程，用注解优雅封装了。你手写 Servlet 时干的每一步——路由匹配、方法分发、生命周期、单例并发——Spring MVC 都帮你自动化了，但底层机制一个都没变。**出 404/405/线程安全问题时，你仍要回到 Servlet 原理排查**：路径匹配看 `@RequestMapping`、方法分发看 `@GetMapping`、单例并发不能存请求状态。

## 本章小结

本篇建立了 Servlet 的核心认知：它是运行在 Tomcat 容器中的 Java 类，通过继承 `HttpServlet` 重写 `doGet`/`doPost` 处理请求。重点掌握 Servlet 的继承体系（Servlet→GenericServlet→HttpServlet）、三阶段生命周期（init→service→destroy）、单例非线程安全特性、url-pattern 匹配规则与优先级、以及 `@WebServlet` 注解配置。下一篇 [03-HTTP 协议](03-HTTP%20协议.md) 将深入 HTTP 协议本身——Servlet 处理的请求和响应，本质就是 HTTP 报文。
