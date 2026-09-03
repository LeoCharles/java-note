# HTTP 协议

前两篇你跑通了 Tomcat、写了第一个 Servlet。但 Servlet 接收的"请求"和返回的"响应"到底是什么？答案就是 **HTTP 协议**——浏览器和服务器之间的通信语言。理解 HTTP 报文结构、请求方法、状态码，是写好 Web 接口的前提，也是 Spring MVC 的 `@GetMapping`/`@PostMapping`/`ResponseEntity` 的底层依据。本篇讲透 HTTP 协议，让你看懂每一次浏览器请求背后发生了什么。

> 💡 本篇建议配合浏览器开发者工具（F12 → Network）边读边看：随便打开一个网页，点一个请求，对照本篇讲的请求行/请求头/响应结构，亲眼看到真实的 HTTP 报文，比看十遍教程都管用。

---

## 一、HTTP 协议概述

### 1.1 什么是 HTTP

**HTTP**（HyperText Transfer Protocol，超文本传输协议）是浏览器与服务器之间通信的协议。它基于 **TCP/IP**，默认端口 80。

特点：
- **无状态**：服务器不记录客户端状态（每次请求都是"新"的，需 Cookie/Session 保持登录）。
- **请求-响应模型**：浏览器发请求，服务器回响应，一来一回。
- **明文传输**：HTTP 不加密，HTTPS（HTTP + SSL/TLS）才加密。

> 💡 **无状态是 HTTP 最重要的特性**：它意味着服务器默认"记不住"你登没登录——这就是为什么需要 Cookie/Session（阶段三会讲）。Spring Session、JWT 都是为了解决"无状态下的状态保持"。

### 1.2 HTTP 版本

| 版本 | 特点 |
| :--- | :--- |
| HTTP/1.0 | 每次请求新建 TCP 连接，效率低 |
| HTTP/1.1 | **默认长连接**（keep-alive），复用 TCP 连接，最广泛 |
| HTTP/2 | 多路复用，一个连接并发多个请求 |
| HTTP/3 | 基于 UDP（QUIC），更快 |

> 💡 Tomcat 9 支持 HTTP/2（需配 SSL），Spring Boot 内嵌 Tomcat 同样支持。

---

## 二、HTTP 请求报文 ⭐

浏览器发给服务器的数据叫**请求报文**，由四部分组成：

```
请求行          POST /user?id=1 HTTP/1.1
请求头          Host: localhost:8080
               Content-Type: application/x-www-form-urlencoded
               Content-Length: 21
               User-Agent: Mozilla/5.0 ...
               Cookie: JSESSIONID=abc123
空行           （一个空行，分隔头和体）
请求体          name=张三&age=20
```

### 2.1 请求行

格式：`请求方法 请求URL 协议版本`

```
POST /user?id=1 HTTP/1.1
 │     │        │
 │     │        └─ 协议版本
 │     └────────── 请求路径（含查询参数）
 └──────────────── 请求方法
```

### 2.2 请求头

常见请求头：

| 请求头 | 作用 | 示例 |
| :--- | :--- | :--- |
| `Host` | 服务器主机名 | `localhost:8080` |
| `User-Agent` | 浏览器信息 | `Mozilla/5.0 ...` |
| `Accept` | 能接受的响应类型 | `text/html, application/json` |
| `Content-Type` | 请求体的数据类型 | `application/json` |
| `Content-Length` | 请求体长度 | `21` |
| `Cookie` | 携带的 Cookie | `JSESSIONID=abc123` |
| `Referer` | 从哪个页面跳来的 | `http://localhost:8080/login` |
| `Authorization` | 认证信息 | `Bearer xxx`（JWT 常用） |

> 💡 **`Content-Type` 决定了请求体怎么解析**，是后端取参数的关键：
> - `application/x-www-form-urlencoded`：表单默认，体为 `name=张三&age=20`
> - `multipart/form-data`：文件上传，体为分块数据
> - `application/json`：JSON 数据，体为 `{"name":"张三","age":20}`

### 2.3 请求体

- **GET 请求**：一般**无请求体**，参数在 URL 的查询串里（`?id=1&name=张三`）。
- **POST 请求**：参数在请求体里，格式由 `Content-Type` 决定。

> ⚠️ **GET 不是绝对没有 body**：HTTP 规范没禁止 GET 带 body，但**实际开发别这么干**——很多服务器/代理会忽略 GET 的 body，参数会丢。GET 的参数放 URL 查询串。

---

## 三、HTTP 响应报文 ⭐

服务器返回给浏览器的数据叫**响应报文**，也是四部分：

```
响应行          HTTP/1.1 200 OK
响应头          Content-Type: text/html;charset=utf-8
               Content-Length: 123
               Set-Cookie: JSESSIONID=abc123; Path=/
空行           （一个空行）
响应体          <html><body>Hello</body></html>
```

### 3.1 响应行

格式：`协议版本 状态码 状态描述`

```
HTTP/1.1 200 OK
 │        │   │
 │        │   └─ 状态描述（OK / Not Found）
 │        └───── 状态码
 └────────────── 协议版本
```

### 3.2 常见响应头

| 响应头 | 作用 |
| :--- | :--- |
| `Content-Type` | 响应体类型（HTML/JSON/图片） |
| `Content-Length` | 响应体长度 |
| `Set-Cookie` | 让浏览器保存 Cookie |
| `Location` | 重定向目标地址（配合 302） |
| `Cache-Control` | 缓存策略 |

---

## 四、请求方法 ⭐

HTTP 定义了多种请求方法，最常用的是 GET 和 POST。

| 方法 | 语义 | 幂等 | 安全 | 典型场景 |
| :--- | :---: | :---: | :---: | :--- |
| **GET** | 查询 | ✅ | ✅ | 查询数据、打开页面 |
| **POST** | 新增 | ❌ | ❌ | 提交表单、创建资源 |
| **PUT** | 修改 | ✅ | ❌ | 更新整个资源 |
| **DELETE** | 删除 | ✅ | ❌ | 删除资源 |
| **PATCH** | 局部修改 | ❌ | ❌ | 更新部分字段 |
| **HEAD** | 取头 | ✅ | ✅ | 只要响应头，不要体 |
| **OPTIONS** | 预检 | ✅ | ✅ | 跨域预检、查支持的方法 |

> 💡 **幂等**：同一个请求执行一次和多次效果相同。GET/PUT/DELETE 是幂等的，POST 不是。
>
> 💡 **安全**：指不修改服务器数据。GET/HEAD 是安全的，POST/PUT/DELETE 不是。

### 4.1 GET 与 POST 的本质区别 ⭐

| 维度 | GET | POST |
| :--- | :--- | :--- |
| 参数位置 | URL 查询串 | 请求体 |
| 长度限制 | 有（URL 长度限制，约 2KB） | 无（受服务器配置限制） |
| 安全性 | 参数暴露在 URL，不安全 | 相对安全（但明文 HTTP 仍可抓包） |
| 缓存 | 可被浏览器缓存 | 不缓存 |
| 历史记录 | URL 保留在历史 | 不保留 |
| 幂等 | 幂等 | 不幂等 |

> ⚠️ **"GET 有长度限制"是浏览器/服务器限制，不是 HTTP 协议限制**。但实际开发仍遵循：查询用 GET（参数短），提交大量数据/文件用 POST。
>
> ⚠️ **GET 参数在 URL 不等于"不安全"是 POST**：HTTP 明文下 POST body 同样可被抓包。真正的安全靠 HTTPS 加密，不是靠 GET/POST。

📌 **Spring Boot 对应**：Spring MVC 用 `@GetMapping`/`@PostMapping`/`@PutMapping`/`@DeleteMapping` 对应这些方法，这就是 **RESTful API** 的基础——用 HTTP 方法表达对资源的操作语义。

---

## 五、状态码 ⭐

状态码是三位数字，表示请求的处理结果。分类：

| 分类 | 含义 | 典型 |
| :--- | :--- | :--- |
| 1xx | 信息性 | 101 切换协议（WebSocket） |
| 2xx | 成功 | **200 OK** |
| 3xx | 重定向 | **302 跳转**、304 缓存 |
| 4xx | 客户端错误 | **404 未找到**、**400 参数错**、403 禁止、401 未认证 |
| 5xx | 服务器错误 | **500 内部错误**、502 网关错、503 不可用 |

### 5.1 高频状态码

| 状态码 | 含义 | 何时出现 |
| :--- | :--- | :--- |
| **200** | OK | 请求成功 |
| **302** | Found | 重定向（临时） |
| **304** | Not Modified | 资源未修改，用浏览器缓存 |
| **400** | Bad Request | 参数错误/格式错 |
| **401** | Unauthorized | 未登录/认证失败 |
| **403** | Forbidden | 已登录但无权限 |
| **404** | Not Found | 路径不存在 |
| **405** | Method Not Allowed | 请求方法不支持（如只允许 GET 却发 POST） |
| **500** | Internal Server Error | 服务器代码异常 |
| **502** | Bad Gateway | 网关/代理收到无效响应 |
| **503** | Service Unavailable | 服务不可用（过载/维护） |

> ⚠️ **401 vs 403**：401 是"你是谁？"（没登录）；403 是"我知道你是谁，但你不能进"（登录了但没权限）。Spring Security 用这两个码做认证授权。

> 💡 **405 的典型场景**：Servlet 只重写了 `doGet`，浏览器发 POST 请求，Tomcat 返回 405。Spring MVC 里 `@GetMapping` 的接口收到 POST 请求也会 405。

📌 **Spring Boot 对应**：Spring MVC 用 `ResponseEntity` 自定义状态码：
```java
return ResponseEntity.status(404).body("not found");
// 或用注解
@ResponseStatus(HttpStatus.NOT_FOUND)
```

---

## 六、在 Servlet 中操作 HTTP

Servlet 的 `HttpServletRequest` 和 `HttpServletResponse` 就是 HTTP 报文的 Java 封装（下两篇详解）。这里先建立对应关系：

### 6.1 请求 → HttpServletRequest

```java
// 请求行
String method = req.getMethod();           // GET / POST
String uri = req.getRequestURI();         // /user
String queryString = req.getQueryString(); // id=1

// 请求头
String ua = req.getHeader("User-Agent");
Enumeration<String> names = req.getHeaderNames();

// 请求参数（GET 查询串 + POST 表单体）
String id = req.getParameter("id");
Map<String, String[]> map = req.getParameterMap();
```

### 6.2 响应 → HttpServletResponse

```java
// 响应行（状态码）
resp.setStatus(200);
resp.sendError(404, "not found");

// 响应头
resp.setHeader("Content-Type", "application/json;charset=utf-8");
resp.setHeader("Location", "/login");   // 配合 302 重定向

// 响应体
resp.getWriter().write("{\"name\":\"张三\"}");
```

> 💡 **对应关系记牢**：请求行/头/体 ↔ `HttpServletRequest` 的方法；响应行/头/体 ↔ `HttpServletResponse` 的方法。下一篇 [04-Request](04-Request%20请求对象.md) 和 [05-Response](05-Response%20响应对象.md) 会逐个细讲。

---

## ⚠️ 重点

1. **HTTP 无状态**：服务器不记客户端状态，需 Cookie/Session 保持登录——这是会话管理的根本动因。
2. **请求报文四部分**：请求行、请求头、空行、请求体；响应报文同样四部分。
3. **空行不能少**：头和体之间必须有一个空行，服务器靠它判断头结束。
4. **`Content-Type` 决定请求体解析方式**：表单、JSON、文件上传各不同。
5. **GET 参数在 URL，POST 参数在体**：这是最本质区别，不是"GET 不安全 POST 安全"。
6. **幂等性**：GET/PUT/DELETE 幂等，POST 不幂等——RESTful 设计依据。
7. **状态码分类**：2xx 成功、3xx 重定向、4xx 客户端错、5xx 服务器错。
8. **401 vs 403**：401 未认证（没登录），403 未授权（登录了没权限）。

---

## 💻 实战案例：用 Servlet 模拟 RESTful 接口

需求：写一个 `/api/user` 接口，GET 查询用户返回 JSON，POST 创建用户，用状态码表达结果。

```java
@WebServlet("/api/user")
public class UserApiServlet extends HttpServlet {

    // GET /api/user?id=1 → 查询，返回 JSON
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        String id = req.getParameter("id");
        resp.setContentType("application/json;charset=utf-8");

        if (id == null) {
            resp.setStatus(400);   // 参数错误
            resp.getWriter().write("{\"error\":\"缺少 id\"}");
            return;
        }
        // 模拟查询
        String json = "{\"id\":" + id + ",\"name\":\"张三\"}";
        resp.setStatus(200);
        resp.getWriter().write(json);
    }

    // POST /api/user，请求体 JSON → 创建用户
    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        // 读请求体（简化，实际用 Jackson 解析）
        BufferedReader reader = req.getReader();
        String body = reader.lines().collect(Collectors.joining());

        resp.setContentType("application/json;charset=utf-8");
        resp.setStatus(201);   // 201 Created：资源创建成功
        resp.getWriter().write("{\"msg\":\"创建成功\",\"data\":" + body + "}");
    }

    // 不支持的方法 → 405
    @Override
    protected void doDelete(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        resp.sendError(405, "Method Not Allowed");
    }
}
```

测试：
- `GET /api/user?id=1` → 200，返回 `{"id":1,"name":"张三"}`
- `POST /api/user`（body: `{"name":"李四"}`）→ 201，返回创建成功
- `DELETE /api/user` → 405

> 💡 **这就是 RESTful API 的雏形**：用 URL 表示资源（`/api/user`）、用 HTTP 方法表示操作（GET 查/POST 增）、用状态码表示结果（200/201/400/405）。Spring Boot 的 `@RestController` 把这套用注解优雅封装了：
> ```java
> @RestController
> @RequestMapping("/api/user")
> public class UserApiController {
>     @GetMapping        // GET → 查
>     public User get(@RequestParam int id) { ... }
>     @PostMapping       // POST → 增
>     public User create(@RequestBody User user) { ... }
> }
> ```

---

## 🚀 新版本补充

- **HTTP/2**（2015）：多路复用、头部压缩、服务器推送，Tomcat 9+ 支持。
- **HTTP/3**（2022）：基于 QUIC（UDP），更快建连，抗丢包。
- **HTTPS**：HTTP + TLS 加密，现代网站标配，Spring Boot 可一键配 SSL（见 [52-HTTPS配置](../Spring/52-HTTPS配置_HTTPS.md)）。

---

## 📌 在 Spring Boot 中

> 本篇讲的 HTTP 报文结构、请求方法、状态码，在 Spring Boot 中用注解和 `ResponseEntity` 封装。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 HTTP 原理排查"。实际开发你不用手动拼报文，但理解了 HTTP，写 RESTful 接口、调参、定位 4xx/5xx 错误才有底气。

### 1. 请求方法：从"HTTP 方法"到"@XxxMapping"

**原生**：HTTP 方法由报文请求行决定，Servlet 用 `doGet`/`doPost` 区分。
**Spring Boot**：注解直接对应 HTTP 方法，这是 RESTful API 的基础。

```java
@RestController
@RequestMapping("/api/users")
public class UserApiController {

    @GetMapping("/{id}")          // GET    /api/users/{id}   → 查询
    public User get(@PathVariable Long id) { ... }

    @GetMapping                   // GET    /api/users         → 列表查询
    public List<User> list() { ... }

    @PostMapping                 // POST   /api/users         → 创建
    public User create(@RequestBody User user) { ... }

    @PutMapping("/{id}")         // PUT    /api/users/{id}    → 全量更新
    public User update(@PathVariable Long id, @RequestBody User user) { ... }

    @DeleteMapping("/{id}")      // DELETE /api/users/{id}    → 删除
    public void delete(@PathVariable Long id) { ... }

    @PatchMapping("/{id}")       // PATCH  /api/users/{id}    → 局部更新
    public User patch(@PathVariable Long id, @RequestBody Map<String,Object> fields) { ... }
}
```

> 💡 **原理对应**：`@GetMapping` 底层仍是判断 `req.getMethod()=="GET"`，和 `HttpServlet.service()` 的分发逻辑一致。**RESTful 的核心就是用 HTTP 方法表达对资源的操作语义**——这正是本篇 4.1 节讲的"方法语义"的工程化落地。

> 💡 **原理排查**：接口返回 405 Method Not Allowed？检查请求方法和注解是否匹配——比如前端用 POST 调了 `@GetMapping` 的接口。这就是本篇讲的"405 请求方法不支持"。

### 2. 请求头：从"getHeader"到"@RequestHeader"

**原生**：`req.getHeader("User-Agent")` 手动取。
**Spring Boot**：`@RequestHeader` 自动注入。

```java
@GetMapping("/info")
public Map<String, String> info(
        @RequestHeader("User-Agent") String userAgent,
        @RequestHeader(value = "Authorization", required = false) String token,
        @RequestHeader(value = "X-Forwarded-For", required = false) String ip) {
    return Map.of("ua", userAgent, "token", token, "ip", ip);
}
```

> 💡 **原理对应**：`@RequestHeader("User-Agent")` 底层就是 `req.getHeader("User-Agent")`，只是自动注入省去手动取值。`required=false` 对应"头可能不存在"，避免 400。

> 💡 **原理排查**：接口报 400 Bad Request "Missing request header"？某个 `@RequestHeader` 没加 `required=false` 但前端没传。回到 HTTP 原理：请求头缺失，服务器无法解析。

### 3. 请求参数：从"getParameter"到"@RequestParam / @RequestBody"

**原生**：表单用 `getParameter`，JSON 用 `getReader()` 读流。
**Spring Boot**：按 `Content-Type` 自动选择解析方式。

```java
// GET 查询串 ?name=张三&age=20 → @RequestParam
@GetMapping("/search")
public List<User> search(
        @RequestParam String name,
        @RequestParam(defaultValue = "0") int age) { ... }

// POST 表单 application/x-www-form-urlencoded → @RequestParam 也行
@PostMapping("/form")
public User form(@RequestParam String name, @RequestParam int age) { ... }

// POST JSON application/json → @RequestBody 自动反序列化
@PostMapping("/json")
public User json(@RequestBody User user) { ... }

// 文件上传 multipart/form-data → @RequestPart / MultipartFile
@PostMapping("/upload")
public String upload(@RequestPart("file") MultipartFile file) { ... }
```

> 💡 **原理对应**：`@RequestParam` 底层是 `req.getParameter()`；`@RequestBody` 底层是 `req.getReader()` 读流 + Jackson 反序列化。**Spring Boot 按 `Content-Type` 决定用哪个**——本篇 2.2 节讲的"`Content-Type` 决定请求体解析方式"，Spring Boot 自动化了。

> 💡 **原理排查**：`@RequestBody` 报 415 Unsupported Media Type？前端 `Content-Type` 不是 `application/json`。报 400 Bad Request？JSON 格式错或字段对不上。回到 HTTP 原理：`Content-Type` 决定解析方式，类型不对就解析不了。

### 4. 状态码：从"setStatus"到"ResponseEntity"

**原生**：`resp.setStatus(200)` / `resp.sendError(404)`。
**Spring Boot**：`ResponseEntity` 精确控制状态码和响应头。

```java
@GetMapping("/{id}")
public ResponseEntity<User> get(@PathVariable Long id) {
    User user = userService.findById(id);
    if (user == null) {
        return ResponseEntity.status(404).body(null);   // 404
    }
    return ResponseEntity.ok(user);                      // 200
}

@PostMapping
public ResponseEntity<User> create(@RequestBody User user) {
    User saved = userService.save(user);
    return ResponseEntity.status(201).body(saved);       // 201 Created
}

@DeleteMapping("/{id}")
public ResponseEntity<Void> delete(@PathVariable Long id) {
    userService.delete(id);
    return ResponseEntity.noContent().build();           // 204 No Content
}
```

> 💡 **原理对应**：`ResponseEntity.status(404)` 底层就是 `resp.setStatus(404)`，只是链式 API 更优雅。本篇 5.1 节的状态码分类，在 Spring Boot 里用 `HttpStatus` 枚举表达：`HttpStatus.NOT_FOUND`、`HttpStatus.CREATED` 等。

> 💡 **原理排查**：全局异常返回 500？看堆栈定位业务异常。403/401？检查 Spring Security 配置。状态码是 HTTP 协议的"结果语言"，理解了本篇的分类（2xx 成功/4xx 客户端错/5xx 服务器错），才能给前端返回准确的语义。

### 5. 响应头与响应体：从"setHeader + getWriter"到"@ResponseBody 自动序列化"

**原生**：`resp.setContentType("application/json")` + `resp.getWriter().write(json)`。
**Spring Boot**：`@RestController` 返回对象，自动序列化为 JSON。

```java
@RestController   // = @Controller + @ResponseBody，所有方法返回值自动序列化
public class UserController {
    @GetMapping("/{id}")
    public User get(@PathVariable Long id) {
        return userService.findById(id);   // 返回对象 → 自动 JSON
    }
}
```

底层流程：返回 `User` 对象 → Jackson 序列化为 JSON 字符串 → 设 `Content-Type: application/json` → `getWriter().write(json)`。**你本篇学的响应报文三部分（状态行/头/体），Spring Boot 全自动处理了**。

> 💡 **原理排查**：返回中文乱码？检查 Jackson 序列化编码（默认 UTF-8）、响应头 `Content-Type` 是否带 `charset=utf-8`。返回 JSON 字段名不对？检查实体类的 `@JsonProperty` 或 Jackson 命名策略。回到 HTTP 原理：响应体的编码和类型由响应头决定。

### 6. CORS 跨域：从"手动设响应头"到"@CrossOrigin"

**原生**：跨域需手动设 `Access-Control-Allow-Origin` 等响应头。
**Spring Boot**：`@CrossOrigin` 注解或全局配置。

```java
@CrossOrigin(origins = "http://localhost:3000")   // 方法/类级跨域
@GetMapping("/{id}")
public User get(@PathVariable Long id) { ... }
```

```java
// 全局跨域配置
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("http://localhost:3000")
                .allowedMethods("GET", "POST", "PUT", "DELETE");
    }
}
```

> 💡 **原理对应**：CORS 的本质就是 HTTP 响应头 `Access-Control-Allow-*`。本篇讲的"跨域与 CORS 基础"，Spring Boot 用注解封装了这些响应头的设置。理解了 HTTP 响应头，CORS 配置就不神秘。

---

> 一句话：**HTTP 协议是 Web 通信的底层语言**。Spring MVC 的所有注解——`@GetMapping`、`@RequestParam`、`@RequestBody`、`@ResponseBody`、`ResponseEntity`、`@CrossOrigin`——都是对 HTTP 报文各部分的封装。理解了请求行/头/体、方法语义、状态码、`Content-Type` 的作用，用 Spring Boot 写接口时就知道每个注解在操作 HTTP 的哪一部分，**出 400/404/405/415 错误时能立刻定位是请求方法、路径、参数还是类型的问题**。

## 本章小结

本篇讲透了 HTTP 协议：请求报文（请求行/头/空行/体）与响应报文的结构、七种请求方法及幂等性、常见状态码及分类、GET 与 POST 的本质区别。重点理解 HTTP 无状态特性（会话管理的动因）、`Content-Type` 对请求体解析的影响、RESTful 用方法表达操作语义的思想。下一篇 [04-Request 请求对象](04-Request%20请求对象.md) 将深入 `HttpServletRequest`，看 Servlet 如何用 Java 代码操作 HTTP 请求报文。
