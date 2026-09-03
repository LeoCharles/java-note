# Request 请求对象

上一篇讲了 HTTP 请求报文的结构（请求行/头/空行/体）。在 Servlet 里，这份报文被封装成 `HttpServletRequest` 对象——你通过它的方法读取请求的所有信息。本篇讲清如何用 Request 取参数、取请求头、解决中文乱码、做请求转发，以及 request 域对象。这些是 Spring MVC `@RequestParam`/`@RequestBody`/`@RequestHeader` 的底层封装对象。

> 💡 本篇建议边读边写：建一个 Servlet，把每个取参数的方法都试一遍，用浏览器 F12 对照请求报文，看 Java 代码取到的值和报文里的值如何对应。

---

## 一、HttpServletRequest 概述

### 1.1 它是什么

`HttpServletRequest` 是 Servlet 规范的接口（`javax.servlet.http`），**Tomcat 在每次请求时创建一个实例**，传给你的 `doGet`/`doPost` 方法参数里：

```java
protected void doGet(HttpServletRequest req, HttpServletResponse resp) {
    // req 就是这次 HTTP 请求报文的 Java 封装
}
```

它封装了 HTTP 请求的全部信息：

| HTTP 报文部分 | Request 对应方法 |
| :--- | :--- |
| 请求行（方法/URI/协议） | `getMethod()` / `getRequestURI()` / `getProtocol()` |
| 请求头 | `getHeader()` / `getHeaderNames()` |
| 请求参数（查询串+表单） | `getParameter()` / `getParameterMap()` |
| 请求体（流） | `getReader()` / `getInputStream()` |
| 其他（Cookie/路径/域） | `getCookies()` / `getRequestURL()` / `setAttribute()` |

> 💡 **Request 的生命周期**：一次请求创建一个，请求结束就销毁。所以它是**线程安全**的——每个请求有自己的 Request，不会串数据。

---

## 二、获取请求行信息

```java
@WebServlet("/line")
public class LineServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 假设请求：GET /line?name=张三 HTTP/1.1
        String method = req.getMethod();          // GET
        String uri = req.getRequestURI();         // /line
        String queryString = req.getQueryString(); // name=张三
        String url = req.getRequestURL().toString(); // http://localhost:8080/line
        String proto = req.getProtocol();         // HTTP/1.1
        String contextPath = req.getContextPath(); // ""（无项目名时）

        resp.getWriter().write(method + " " + uri + "?" + queryString);
    }
}
```

> ⚠️ **URI vs URL**：URI 是路径部分（`/line`），URL 是完整地址（`http://localhost:8080/line`）。`getRequestURI()` 不含查询参数，`getQueryString()` 单独取参数串。

---

## 三、获取请求头

```java
@WebServlet("/header")
public class HeaderServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 取单个头
        String ua = req.getHeader("User-Agent");     // Mozilla/5.0 ...
        String referer = req.getHeader("Referer");   // 来源页面

        // 遍历所有头
        Enumeration<String> names = req.getHeaderNames();
        while (names.hasMoreElements()) {
            String name = names.nextElement();
            String value = req.getHeader(name);
            System.out.println(name + ": " + value);
        }
    }
}
```

常用请求头获取：

| 请求头 | 方法 | 用途 |
| :--- | :--- | :--- |
| `User-Agent` | `getHeader("User-Agent")` | 判断浏览器/设备类型 |
| `Referer` | `getHeader("Referer")` | 防盗链、统计来源 |
| `Content-Type` | `getContentType()` | 判断请求体格式 |
| `Content-Length` | `getContentLength()` | 请求体长度 |
| `Cookie` | `getCookies()`（专用方法） | 取会话 Cookie |

> 💡 **防盗链原理**：检查 `Referer` 是否来自自己的域名，不是就拒绝——这是 Filter/拦截器常做的事。

---

## 四、获取请求参数 ⭐

取参数是 Request 最核心的功能。无论 GET（查询串）还是 POST（表单体），都用同一套方法。

### 4.1 基本方法

```java
@WebServlet("/param")
public class ParamServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 单值参数
        String name = req.getParameter("name");          // 张三
        String age = req.getParameter("age");            // 20

        // 多值参数（如复选框 checkbox，同名多值）
        String[] hobbies = req.getParameterValues("hobby"); // [read, code]

        // 所有参数（Map<参数名, 值数组>）
        Map<String, String[]> map = req.getParameterMap();
    }
}
```

> ⚠️ **`getParameter` 既能取 GET 查询串，也能取 POST 表单体**——它合并了两者。但**不能取 JSON 请求体**（JSON 要用 `getReader()` 读流，下文 4.4 讲）。

### 4.2 GET 与 POST 取参数

```java
// GET /param?name=张三 → getParameter("name") 直接取
// POST 表单 name=张三 → getParameter("name") 也能取（需先处理乱码）
```

> 💡 **为什么 GET 和 POST 用同一套方法**：Servlet 规范把查询串和表单体统一抽象成"参数"，底层 Tomcat 自动解析两种来源。这就是"面向接口"的好处——你不用关心参数从哪来。

### 4.3 中文乱码解决 ⭐

乱码是初学者必踩的坑，分 GET 和 POST：

**POST 乱码**：Tomcat 解析请求体默认用 ISO-8859-1，中文会乱码。解决：

```java
// 在取参数之前调用（只对请求体生效）
req.setCharacterEncoding("utf-8");
String name = req.getParameter("name");   // 正常中文
```

**GET 乱码**：GET 参数在 URL 里，Tomcat 解析 URL 用默认编码（Tomcat 8+ 默认 UTF-8，一般不乱码）。若乱码：

```java
// Tomcat 8+ 一般无需处理；老版本需手动转码
String name = req.getParameter("name");
name = new String(name.getBytes("iso-8859-1"), "utf-8");
```

> ⚠️ **乱码解决顺序**：`setCharacterEncoding` 必须在 **`getParameter` 之前**调用，否则已解析的参数不会重新编码。最佳实践是在 Servlet 开头第一行就调。

> 💡 **Tomcat 8+ 已默认 UTF-8**：解析 URL 用 UTF-8，GET 中文一般不乱码了。但 POST 请求体仍需 `setCharacterEncoding("utf-8")`。

### 4.4 读取 JSON 请求体

前后端分离时代，POST 常发 JSON 请求体（`Content-Type: application/json`）。`getParameter` 取不到 JSON，要用流读：

```java
protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
    req.setCharacterEncoding("utf-8");
    // 用字符流读请求体
    BufferedReader reader = req.getReader();
    String json = reader.lines().collect(Collectors.joining());
    // {"name":"张三","age":20}

    // 用 Jackson/Fastjson 解析成对象
    ObjectMapper mapper = new ObjectMapper();
    User user = mapper.readValue(json, User.class);
}
```

> ⚠️ **请求体只能读一次**：`getReader()` 和 `getInputStream()` 读完后流到尾，不能重读。Filter 里若先读了，Servlet 里就读不到了——这是 Spring MVC 的 `@RequestBody` 也只能用一次的原因。

> 💡 **这就是 `@RequestBody` 的底层**：Spring MVC 的 `@RequestBody User user`，底层就是用 `getReader()` 读 JSON 流 + Jackson 反序列化。理解了这个，`@RequestBody` 不再神秘。

---

## 五、请求转发

请求转发是服务器内部的跳转：当前 Servlet 处理一半，把请求**转发**给另一个 Servlet/JSP 继续处理，浏览器地址栏不变。

### 5.1 转发语法

```java
@WebServlet("/a")
public class ServletA extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        // 往 request 域存数据，传给下一个资源
        req.setAttribute("msg", "来自 A 的数据");

        // 请求转发到 /b（服务器内部跳转）
        req.getRequestDispatcher("/b").forward(req, resp);
    }
}

@WebServlet("/b")
public class ServletB extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 取 A 存的数据
        String msg = (String) req.getAttribute("msg");
        resp.getWriter().write("B 收到: " + msg);
    }
}
```

访问 `/a`，地址栏仍是 `/a`，但响应由 B 生成。

### 5.2 转发的特点

| 特点 | 说明 |
| :--- | :--- |
| 一次请求 | 转发前后是同一个 Request 对象（地址栏不变） |
| 服务器内部 | 浏览器不知道被转发了 |
| 共享数据 | 通过 request 域（`setAttribute`）传数据 |
| 只能转发内部资源 | 不能转发到外部域名 |

> ⚠️ **转发后不要写响应**：`forward()` 之后当前 Servlet 不应再调用 `resp.getWriter().write()`，否则可能抛异常（响应已提交）。

---

## 六、request 域对象

域对象就是"存数据、共享数据"的容器。**request 域**的作用范围是**一次请求**（转发链中共享）。

```java
// 存
req.setAttribute("user", new User("张三", 20));
// 取
User user = (User) req.getAttribute("user");
// 删
req.removeAttribute("user");
```

> 💡 **四大域对象的作用范围**（阶段四 10 详解）：
> - **PageContext**：当前 JSP 页面（最小）
> - **request**：一次请求（转发链共享）
> - **Session**：一次会话（跨多次请求，登录状态）
> - **ServletContext**：整个 Web 应用（全局共享，最大）

> 💡 **request 域用于转发传值**：A Servlet 查了数据，转发给 JSP 渲染页面，数据就放 request 域。这就是 MVC 中 Controller → View 传数据的雏形——Spring MVC 的 `Model`/`ModelMap` 底层就是往 request 域塞数据。

---

## ⚠️ 重点

1. **Request 一次请求一个实例**：线程安全，请求结束销毁。
2. **`getParameter` 合并 GET 查询串和 POST 表单**：一套方法取两种来源参数。
3. **POST 乱码用 `setCharacterEncoding("utf-8")`**：必须在 `getParameter` 之前调。
4. **GET 乱码 Tomcat 8+ 基本不存在**：默认 UTF-8 解析 URL。
5. **JSON 请求体用 `getReader()` 读流**：`getParameter` 取不到 JSON。
6. **请求体只能读一次**：流读完即尽，`@RequestBody` 也只能用一次。
7. **请求转发是服务器内部跳转**：一次请求、地址栏不变、request 域共享数据。
8. **转发 vs 重定向**：转发一次请求（forward），重定向两次请求（redirect，下一篇讲）。

---

## 💻 实战案例：登录参数接收

需求：前端表单 POST 提交用户名密码，Servlet 接收参数、校验、转发到结果页。

**前端 `login.html`**：

```html
<form action="/login" method="post">
    用户名：<input type="text" name="username"><br>
    密码：<input type="password" name="password"><br>
    <button type="submit">登录</button>
</form>
```

**后端 `LoginServlet`**：

```java
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        // 1. 解决 POST 乱码（必须在取参前）
        req.setCharacterEncoding("utf-8");

        // 2. 取参数
        String username = req.getParameter("username");
        String password = req.getParameter("password");

        // 3. 校验（模拟）
        if ("admin".equals(username) && "123456".equals(password)) {
            req.setAttribute("user", username);
            req.getRequestDispatcher("/success").forward(req, resp);
        } else {
            req.setAttribute("error", "用户名或密码错误");
            req.getRequestDispatcher("/fail").forward(req, resp);
        }
    }
}

@WebServlet("/success")
public class SuccessServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        req.setCharacterEncoding("utf-8");
        String user = (String) req.getAttribute("user");
        resp.setContentType("text/html;charset=utf-8");
        resp.getWriter().write("<h1>欢迎 " + user + "</h1>");
    }
}
```

> 💡 **这个登录流程的四步**（取参 → 校验 → 转发 → 渲染）就是 Web 请求处理的通用骨架。Spring MVC 用注解封装了：
> ```java
> @PostMapping("/login")
> public String login(@RequestParam String username,
>                     @RequestParam String password,
>                     Model model) {
>     if (service.login(username, password)) {
>         model.addAttribute("user", username);  // 等价 setAttribute
>         return "success";                       // 等价转发到视图
>     }
>     model.addAttribute("error", "登录失败");
>     return "fail";
> }
> ```

---

## 🚀 新版本补充

- **Servlet 3.1**：`getContentLengthLong()` 支持大请求体；非阻塞 IO（`ReadListener`）。
- **Servlet 4.0**：`getTrailerFields()` 支持 HTTP/2 尾部字段。
- **Tomcat 8+**：URL 默认 UTF-8 解析，GET 中文基本不乱码。

---

## 📌 在 Spring Boot 中

> 本篇讲的取参数、读请求头、读 JSON 体、转发、乱码，在 Spring Boot 中用注解全部封装。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 Request 原理排查"。实际开发你不用手动 `getParameter`/`getReader`，但理解了 Request，参数绑定失败、JSON 解析错、乱码时才知道怎么查。

### 1. 取请求参数：从"getParameter"到"@RequestParam"

**原生**：`req.getParameter("name")` 手动取，还要判空、转类型。
**Spring Boot**：`@RequestParam` 自动注入，类型转换+判空全自动。

```java
@GetMapping("/search")
public List<User> search(
        @RequestParam String name,                          // 必传，缺则 400
        @RequestParam(required = false) Integer age,        // 可选
        @RequestParam(defaultValue = "1") int page,         // 默认值
        @RequestParam(required = false) List<String> ids) { // 多值（ids=1&ids=2）
    // name/age/page/ids 已是强类型，直接用
}
```

> 💡 **原理对应**：`@RequestParam` 底层就是 `req.getParameter()`，只是自动做了类型转换（字符串→int/Long）、判空（required）、设默认值。本篇 4.1 节讲的"单值/多值参数"，Spring Boot 用 `List<String>` 接收多值。

> 💡 **原理排查**：接口报 400 "Required request parameter 'name' is not present"？某个 `@RequestParam` 没加 `required=false` 但前端没传。回到 Request 原理：`getParameter` 取到 null，Spring 判定必传参数缺失。

### 2. 路径参数：从"手写解析 URL"到"@PathVariable"

**原生**：URL 里的 `/user/1` 要手动 split 解析，或用 `getPathInfo()`。
**Spring Boot**：`@PathVariable` 直接提取路径变量。

```java
@GetMapping("/users/{id}")
public User get(@PathVariable Long id) { ... }

@GetMapping("/users/{userId}/orders/{orderId}")
public Order get(@PathVariable Long userId, @PathVariable Long orderId) { ... }
```

> 💡 **原理对应**：`@PathVariable` 底层是 DispatcherServlet 解析 URL 模板 `{id}`，从请求路径提取对应部分。这是对原生"路径参数解析"的封装——原生要手写正则/split，Spring Boot 用模板语法声明。

### 3. JSON 请求体：从"getReader 读流"到"@RequestBody"

**原生**：`req.getReader()` 读流 + Jackson 手动反序列化（本篇 4.4 节）。
**Spring Boot**：`@RequestBody` 自动反序列化。

```java
@PostMapping("/users")
public User create(@RequestBody User user) {   // JSON → User 对象，自动完成
    return userService.save(user);
}

@PostMapping("/users/batch")
public List<User> batch(@RequestBody List<User> users) {  // JSON 数组 → List
    return userService.saveAll(users);
}
```

> 💡 **原理对应**：`@RequestBody` 底层就是本篇 4.4 节的 `getReader()` + Jackson `readValue()`，只是全自动。**本篇强调的"请求体只能读一次"，Spring Boot 同样适用**——`@RequestBody` 只能用一次，Filter 里若先读了 body，Controller 的 `@RequestBody` 就拿不到。

> 💡 **原理排查**：报 415 Unsupported Media Type？前端 `Content-Type` 不是 `application/json`。报 400 Bad Request？JSON 字段名和实体类对不上、类型转换失败（如 age 传了字符串"abc"）。回到 Request 原理：`Content-Type` 决定解析方式，类型不对就解析不了。

### 4. 请求头：从"getHeader"到"@RequestHeader"

**原生**：`req.getHeader("User-Agent")`。
**Spring Boot**：`@RequestHeader` 自动注入（详见 03 篇 Spring Boot 小节）。

```java
@GetMapping("/info")
public String info(@RequestHeader("Authorization") String token) { ... }
```

### 5. 乱码：从"手动 setCharacterEncoding"到"自动 UTF-8"

**原生**：每个 Servlet 开头写 `req.setCharacterEncoding("utf-8")`（本篇 4.3 节）。
**Spring Boot**：默认配置 `CharacterEncodingFilter`，全局 UTF-8，无需手动处理。

```yaml
server:
  servlet:
    encoding:
      charset: UTF-8        # 默认就是 UTF-8
      force: true           # 强制请求和响应都用 UTF-8
```

> 💡 **原理对应**：Spring Boot 的 `CharacterEncodingFilter` 就是一个 Filter（08 篇讲），在请求到达 Controller 前统一调 `setCharacterEncoding("utf-8")`。**你本篇手动写的乱码解决代码，Spring Boot 用一个 Filter 全局搞定了**。

> 💡 **原理排查**：中文参数乱码？检查 `server.servlet.encoding.force=true`、前端表单 `accept-charset` 或 AJAX 的 `Content-Type` 是否带 `charset=utf-8`。乱码问题永远回到"请求编码 vs 解码编码不一致"这个本篇原理。

### 6. 请求转发与域传值：从"RequestDispatcher.forward + setAttribute"到"Model + 视图名"

**原生**：`req.setAttribute("user", user)` + `req.getRequestDispatcher("/page").forward(req, resp)`。
**Spring Boot**：`Model.addAttribute` + 返回视图名。

```java
@GetMapping("/user/{id}")
public String show(@PathVariable Long id, Model model) {
    User user = userService.findById(id);
    model.addAttribute("user", user);   // 等价 setAttribute，存进 request 域
    return "user/detail";                // 等价转发到模板 user/detail
}
```

> 💡 **原理对应**：`Model.addAttribute` 底层就是往 request 域 `setAttribute`；`return "user/detail"` 底层就是 `RequestDispatcher.forward` 到 Thymeleaf 模板。**本篇讲的"request 域用于转发传值"，Spring MVC 用 Model 封装了，但数据流转路径完全一样**：Controller → request 域 → 模板渲染。

> 💡 **原理排查**：模板里取不到值？检查 `Model.addAttribute` 的 key 和模板里的引用名是否一致、视图名是否拼对。回到 Request 原理：转发链共享 request 域，key 对不上就取 null。

### 7. 直接注入 HttpServletRequest

少数场景需要原生 Request 对象（如手动读流、获取真实 IP），可直接注入：

```java
@GetMapping("/ip")
public String ip(HttpServletRequest request) {
    String ip = request.getHeader("X-Forwarded-For");  // 经过代理的真实 IP
    if (ip == null) ip = request.getRemoteAddr();       // 直连 IP
    return ip;
}
```

> 💡 **原理对应**：Spring MVC 允许直接注入 `HttpServletRequest`，底层就是 Tomcat 传给 DispatcherServlet 的那个 Request 对象。**本篇学的所有 Request 方法，在 Spring Boot 里仍可用**——注解只是封装，原生对象随时可取。

---

> 一句话：**Spring MVC 把 Request 的取参、读体、转发全部注解化了**。`@RequestParam` 取参数、`@PathVariable` 取路径变量、`@RequestBody` 读 JSON、`@RequestHeader` 取头、`Model` 存转发数据——每个注解都对应本篇的一个 Request 方法。乱码更是默认解决。但底层操作的还是这个 `HttpServletRequest`，**出参数绑定失败（400）、JSON 解析错（415）、乱码问题时，你仍要回到 Request 原理排查**：参数名对不对、`Content-Type` 对不对、编码一不一致。

## 本章小结

本篇讲清了 `HttpServletRequest` 的核心用法：获取请求行（方法/URI）、请求头、请求参数（GET/POST 统一取、JSON 用流读）、中文乱码解决（POST 用 `setCharacterEncoding`）、请求转发（`RequestDispatcher.forward`，一次请求内部跳转）、request 域对象（转发链共享数据）。下一篇 [05-Response 响应对象](05-Response%20响应对象.md) 讲如何用 `HttpServletResponse` 生成 HTTP 响应——和本篇是一对。
