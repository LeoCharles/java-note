# Spring MVC 架构与请求流程

前面 12 篇学了 IoC、DI、AOP、事务——这些是 Spring 的"内核"。从本篇开始进入 Spring MVC，它是 Spring 的 Web 框架模块，负责把 HTTP 请求变成 Java 方法的调用。在 Spring Boot 时代你不需要手动配置 `DispatcherServlet`，但理解它的完整请求流程，会让你在调接口、写拦截器、排 Bug 时更有底气。

> 💡 一个经典的面试题：「一个 HTTP 请求到达 Spring Boot 后，经历了什么？」——本篇的回答就是标准答案。

---

## 一、Spring MVC 是什么

### 1.1 定位

Spring MVC 是 Spring Framework 的 **Web 模块**，实现了 **MVC 设计模式**：

| MVC 角色 | Spring MVC 对应 | 职责 |
| :--- | :--- | :--- |
| Model | Service + Repository | 业务数据 + 业务逻辑 |
| View | Thymeleaf / JSON 序列化 | 展示数据 |
| Controller | `@Controller` / `@RestController` | 接收请求，调用业务，返回响应 |

### 1.2 前端控制器模式

Spring MVC 的核心设计是**前端控制器（Front Controller）模式**：所有请求都经过一个统一的 `DispatcherServlet`，由它分发给具体的 Controller 方法。

```
                          ┌────────────────────┐
                          │   DispatcherServlet │ ← 所有请求的入口（前端控制器）
                          └────────┬───────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              /users/1       /orders/2       /products/3
                    │              │              │
                    ▼              ▼              ▼
              UserController  OrderController ProductController
```

对比 JavaWeb 原生模式：

| | 原生 Servlet | Spring MVC |
| :--- | :--- | :--- |
| **请求入口** | 每个 Servlet 一个 url-pattern | 统一 `DispatcherServlet` |
| **路由方式** | `@WebServlet("/xxx")` 分散配置 | `@RequestMapping` 集中管理 |
| **参数获取** | `req.getParameter("name")` | `@RequestParam String name` |
| **响应输出** | `resp.getWriter().write(json)` | `return object` + Jackson 自动序列化 |

---

## 二、Spring MVC 请求完整流程 ⭐⭐

### 2.1 核心流程图

```
HTTP 请求 GET /users/1
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ 1. DispatcherServlet（前端控制器）                        │
│    所有请求的第一个到达点                                   │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 2. HandlerMapping（处理器映射器）                         │
│    根据请求 URL 找到对应的 Handler（Controller 方法）       │
│    GET /users/1 → UserController.getById(Long id)        │
└────────────────────┬─────────────────────────────────────┘
                     │ 返回 Handler + Interceptors
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 3. HandlerAdapter（处理器适配器）                         │
│    调用 Handler，处理参数绑定、返回值处理                   │
│    @PathVariable("id") Long id → 1                       │
└────────────────────┬─────────────────────────────────────┘
                     │ 调 Controller 方法
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 4. HandlerInterceptor（拦截器）                           │
│    preHandle → Controller → postHandle → afterCompletion │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 5. Controller 执行                                       │
│    @GetMapping("/users/{id}")                            │
│    public User getById(@PathVariable Long id) { ... }    │
└────────────────────┬─────────────────────────────────────┘
                     │ 返回 ModelAndView / Object
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 6. ViewResolver（视图解析器）                             │
│    逻辑视图名 → 物理视图页面 / JSON 序列化                  │
│    @RestController → 跳过 ViewResolver，直接序列化 JSON    │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
                返回 HTTP Response（JSON / HTML）
```

### 2.2 关键组件详解

#### HandlerMapping：URL → Controller 方法

```java
@RestController
@RequestMapping("/users")
public class UserController {

    @GetMapping("/{id}")         // GET /users/1
    public User getById(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping                // POST /users
    public User create(@RequestBody User user) {
        return userService.save(user);
    }
}
```

Spring MVC 启动时，扫描所有 `@RequestMapping` 注解，建立 **URL ↔ Controller 方法** 的映射表。请求到来时，查表找到对应方法。

#### HandlerAdapter：调用 Controller 方法

HandlerAdapter 负责：
1. **参数解析**：`@RequestParam`、`@PathVariable`、`@RequestBody` 等注解的参数绑定
2. **调用方法**：反射调用 Controller 方法
3. **返回值处理**：如果是 `@RestController`，把 Java 对象序列化为 JSON

#### ViewResolver / HttpMessageConverter

| 场景 | 使用的组件 | 返回格式 |
| :--- | :--- | :--- |
| `@Controller` + Thymeleaf | `ViewResolver` | HTML 页面 |
| `@RestController` / `@ResponseBody` | `HttpMessageConverter`（Jackson） | JSON |

```java
// @Controller → 返回视图名，经 ViewResolver 解析为 HTML
@Controller
public class PageController {
    @GetMapping("/page")
    public String page() {
        return "user/list";  // Thymeleaf 解析为 templates/user/list.html
    }
}

// @RestController → 返回对象，经 Jackson 序列化为 JSON
@RestController
public class ApiController {
    @GetMapping("/api/user")
    public User api() {
        return new User("张三", 20);  // → {"name":"张三","age":20}
    }
}
```

---

## 三、@Controller 与 @RestController

### 3.1 @Controller：返回视图

```java
@Controller
@RequestMapping("/pages")
public class PageController {

    @GetMapping("/home")
    public String home(Model model) {
        model.addAttribute("message", "欢迎");
        return "home";  // → 解析为 templates/home.html（Thymeleaf）
    }
}
```

### 3.2 @RestController：返回 JSON

```java
@RestController  // = @Controller + @ResponseBody
@RequestMapping("/api/users")
public class UserApiController {

    @GetMapping("/{id}")
    public User getById(@PathVariable Long id) {
        return userService.findById(id);  // → Jackson 序列化为 JSON
    }
}
```

```java
// @RestController 源码
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Controller         // ← 首先是 @Controller
@ResponseBody       // ← 所有方法默认 @ResponseBody
public @interface RestController {
    @AliasFor(annotation = Controller.class)
    String value() default "";
}
```

> 💡 前后端分离时代，99% 的场景用 `@RestController`。`@Controller` 只在服务端渲染（Thymeleaf 等模板引擎）时使用。

---

## 四、Spring MVC 与 Servlet 的关系

```
Tomcat 接收请求
    │
    ▼
Filter 链（编码/鉴权等）
    │
    ▼
DispatcherServlet（本质是一个 Servlet！）
    │
    ├── 继承自 FrameworkServlet ← HttpServletBean ← HttpServlet ← GenericServlet ← Servlet
    │
    └── 内部流程：HandlerMapping → HandlerAdapter → Controller → 返回
```

```java
// DispatcherServlet 的继承链（简化）
public class DispatcherServlet extends FrameworkServlet {
    @Override
    protected void doService(HttpServletRequest request, HttpServletResponse response) {
        // ... 这就是之前 JavaWeb 学的 Servlet 的 service 方法
        doDispatch(request, response);
    }

    protected void doDispatch(HttpServletRequest request, HttpServletResponse response) {
        // 1. 获取 Handler（HandlerMapping：URL → Controller方法）
        HandlerExecutionChain handler = getHandler(request);

        // 2. 获取 HandlerAdapter
        HandlerAdapter adapter = getHandlerAdapter(handler);

        // 3. 调用拦截器 preHandle
        handler.applyPreHandle(request, response);

        // 4. 执行 Controller 方法
        ModelAndView mv = adapter.handle(request, response, handler);

        // 5. 调用拦截器 postHandle
        handler.applyPostHandle(request, response, mv);

        // 6. 处理视图 / 返回值
        processDispatchResult(request, response, handler, mv);
    }
}
```

> 💡 回顾 [JavaWeb/02-Servlet 入门](../JavaWeb/02-Servlet%20入门.md)：DispatcherServlet 本身就是一个 Servlet——它是 Spring MVC 的入口，负责所有请求的分发。在 Spring Boot 中，内嵌 Tomcat 启动时会自动注册 DispatcherServlet。

---

## 💻 实战案例

### 案例：手写迷你 DispatcherServlet

```java
/**
 * 迷你 DispatcherServlet：理解 Spring MVC 的请求分发原理
 */
@WebServlet("/mvc/*")  // 拦截所有 /mvc/ 开头的请求
public class MiniDispatcherServlet extends HttpServlet {

    // 模拟 HandlerMapping：URL → Controller 方法
    private Map<String, Method> handlerMapping = new HashMap<>();

    @Override
    public void init() throws ServletException {
        try {
            // 扫描 Controller（简化：手动注册）
            UserController controller = new UserController();
            Method method = UserController.class.getMethod("getById", Long.class);
            handlerMapping.put("/mvc/users/get", method);
        } catch (Exception e) {
            throw new ServletException(e);
        }
    }

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        String uri = req.getRequestURI();
        Method handler = handlerMapping.get(uri);  // 1. 找 Handler

        if (handler == null) {
            resp.sendError(404, "Not Found: " + uri);
            return;
        }

        try {
            // 2. 解析参数（简化：从 URL 参数获取 id）
            Long id = Long.valueOf(req.getParameter("id"));

            // 3. 调用 Controller 方法
            Object result = handler.invoke(new UserController(), id);

            // 4. 写响应（简化：输出字符串）
            resp.setContentType("application/json;charset=utf-8");
            resp.getWriter().write("{\"id\":" + id + ",\"name\":\"用户" + id + "\"}");

        } catch (Exception e) {
            throw new ServletException(e);
        }
    }
}
```

> 💡 这就是 DispatcherServlet 的极简版：URL 映射 → 找处理器 → 解析参数 → 调方法 → 写响应。Spring MVC 真实版本多了参数解析器、返回值处理器、拦截器、异常处理器、视图解析器等一系列组件，但核心流程就是这几步。

---

## 🎯 面试高频

### Q1：Spring MVC 的完整请求流程是怎样的？

**答**：一个 HTTP 请求到达后的处理流程：

1. 到达 **DispatcherServlet**（前端控制器）
2. **HandlerMapping** 根据 URL 找到对应的 Controller 方法（Handler）
3. **HandlerAdapter** 调用 Handler：解析参数（`@RequestParam`/`@PathVariable`/`@RequestBody`）→ 反射调用 → 处理返回值
4. 前后会经过 **HandlerInterceptor** 的 preHandle / postHandle / afterCompletion
5. 如果是 `@RestController`，**HttpMessageConverter**（Jackson）将返回值序列化为 JSON
6. 如果是 `@Controller` + 视图名，**ViewResolver** 解析为具体 HTML 页面
7. 返回 HTTP Response

### Q2：@RestController 和 @Controller 有什么区别？

**答**：`@RestController` = `@Controller` + `@ResponseBody`。`@Controller` 的方法返回视图名（经 ViewResolver 解析）；`@RestController` 的方法返回 Java 对象（经 Jackson 序列化为 JSON）。前后端分离的 API 接口统一用 `@RestController`。

---

## 📌 在 Spring Boot 中

- Spring Boot 通过 `DispatcherServletAutoConfiguration` 自动注册 DispatcherServlet，默认映射到 `/`
- `spring.mvc.servlet.path` 可更改 DispatcherServlet 的映射路径
- `@SpringBootApplication` 包含 `@EnableWebMvc`（Spring Boot 2.x 通过自动配置生效），自动注册了 `RequestMappingHandlerMapping` 和 `RequestMappingHandlerAdapter`
- Spring Boot 默认使用 Jackson 作为 JSON 序列化框架，`JacksonAutoConfiguration` 自动配置了 `ObjectMapper`

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 前端控制器模式 | 所有请求统一由 DispatcherServlet 接收并分发 |
| 请求流程 | DispatcherServlet → HandlerMapping → HandlerAdapter → Controller → 返回 |
| DispatcherServlet | 本质是一个继承自 HttpServlet 的 Servlet |
| @Controller | 返回视图名，经 ViewResolver 解析 |
| @RestController | 返回对象，经 Jackson 序列化为 JSON（前后端分离主力） |
| HandlerMapping | URL → Controller 方法 的映射关系 |

---

## 学习建议

1. **画出请求流程图**：从"HTTP 请求到达"画到"JSON 返回"，包含 DispatcherServlet → HandlerMapping → HandlerAdapter → Controller → HttpMessageConverter/ViewResolver——面试必备。
2. **Debug 跟踪一次请求**：在 DispatcherServlet 的 `doDispatch` 方法打断点，跟踪一次真实的请求，看 HandlerMapping 怎么找到 Controller、HandlerAdapter 怎么调用方法、Jackson 怎么序列化返回值。
3. **对比 JavaWeb 的 Servlet 模式**：回忆 [JavaWeb/02-Servlet 入门](../JavaWeb/02-Servlet%20入门.md)，想清楚 DispatcherServlet 怎么替代了"每个 URL 写一个 Servlet"的笨重模式。