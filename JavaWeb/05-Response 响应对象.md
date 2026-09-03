# Response 响应对象

上一篇讲了如何用 `HttpServletRequest` 读取请求。本篇讲它的对偶——`HttpServletResponse`，即如何用 Java 代码生成 HTTP 响应报文。设置状态码、响应头、写响应体、做重定向，以及中文乱码解决，都在这里。这是 Spring MVC `@ResponseBody`/`ResponseEntity`/`RedirectView` 的底层封装对象。

> 💡 本篇和上一篇是一对：Request 读请求，Response 写响应。建议边读边写一个 Servlet，把每个设置响应的方法都试一遍，用浏览器 F12 看响应报文的变化。

---

## 一、HttpServletResponse 概述

### 1.1 它是什么

`HttpServletResponse` 是 Servlet 规范的接口（`javax.servlet.http`），**Tomcat 在每次请求时创建一个实例**，传给你的 `doGet`/`doPost` 参数里：

```java
protected void doGet(HttpServletRequest req, HttpServletResponse resp) {
    // resp 就是这次 HTTP 响应报文的 Java 封装
}
```

它封装了 HTTP 响应的三部分：

| HTTP 响应部分 | Response 对应方法 |
| :--- | :--- |
| 响应行（状态码） | `setStatus()` / `sendError()` |
| 响应头 | `setHeader()` / `setContentType()` |
| 响应体（字符流） | `getWriter()` |
| 响应体（字节流） | `getOutputStream()` |

> 💡 **Response 的生命周期**：和 Request 一样，一次请求一个，请求结束销毁。你往里写的所有内容，Tomcat 在请求结束时打包成 HTTP 响应报文发给浏览器。

---

## 二、设置响应行（状态码）

```java
@WebServlet("/status")
public class StatusServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 设置成功状态码
        resp.setStatus(200);          // OK

        // 设置错误状态码（会返回 Tomcat 默认错误页）
        resp.sendError(404, "资源不存在");
        resp.sendError(500, "服务器异常");
    }
}
```

| 方法 | 作用 |
| :--- | :--- |
| `setStatus(int)` | 设置成功状态码（2xx/3xx） |
| `sendError(int, String)` | 设置错误状态码（4xx/5xx）+ 提示信息 |

> ⚠️ **`setStatus` vs `sendError`**：`setStatus` 只设状态码，不中断流程；`sendError` 会提交响应并返回错误页，**之后不能再写响应体**。报错用 `sendError`，正常返回用 `setStatus`。

---

## 三、设置响应头

```java
@WebServlet("/header")
public class HeaderServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 单值头
        resp.setHeader("Content-Type", "application/json;charset=utf-8");
        resp.setHeader("Cache-Control", "no-cache");

        // 专用方法（等价于 setHeader）
        resp.setContentType("text/html;charset=utf-8");
        resp.setContentLength(123);

        // 重定向相关
        resp.setHeader("Location", "/login");
    }
}
```

常用响应头：

| 响应头 | 作用 | 设置方法 |
| :--- | :--- | :--- |
| `Content-Type` | 响应体类型（最重要） | `setContentType()` |
| `Content-Length` | 响应体长度 | `setContentLength()` |
| `Set-Cookie` | 写 Cookie（下篇讲） | `addCookie()` |
| `Location` | 重定向地址 | `setHeader("Location", ...)` |
| `Cache-Control` | 缓存策略 | `setHeader("Cache-Control", ...)` |
| `Content-Disposition` | 下载文件名 | `setHeader("Content-Disposition", ...)` |

> 💡 **`Content-Type` 是响应头里最重要的**：它告诉浏览器"我返回的是什么类型的数据，用什么编码解析"。返回 HTML 就 `text/html`，返回 JSON 就 `application/json`，返回图片就 `image/jpeg`。

---

## 四、写响应体 ⭐

响应体是返回给浏览器的实际内容。Response 提供两个流：

| 流 | 方法 | 适用场景 |
| :--- | :--- | :--- |
| 字符流 | `getWriter()` | 写文本（HTML/JSON） |
| 字节流 | `getOutputStream()` | 写二进制（图片/文件下载） |

### 4.1 字符流写文本

```java
@WebServlet("/text")
public class TextServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");   // 必须在 write 之前
        PrintWriter writer = resp.getWriter();
        writer.write("<h1>Hello, Response!</h1>");
        writer.write("<p>这是响应体</p>");
    }
}
```

### 4.2 字节流写二进制

```java
@WebServlet("/image")
public class ImageServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("image/jpeg");
        // 读图片文件，用字节流写出
        InputStream in = getServletContext().getResourceAsStream("/img/logo.jpg");
        ServletOutputStream out = resp.getOutputStream();
        byte[] buf = new byte[1024];
        int len;
        while ((len = in.read(buf)) != -1) {
            out.write(buf, 0, len);
        }
        in.close();
    }
}
```

> ⚠️ **字符流和字节流不能同时用**：一个响应里只能选 `getWriter()` 或 `getOutputStream()` 之一，同时调用会抛 `IllegalStateException`。文本用字符流，二进制用字节流。

> ⚠️ **`setContentType` 必须在 `getWriter` 之前**：流一旦获取，编码就定了，之后再设 `setContentType` 不生效。这是乱码的常见原因。

### 4.3 中文乱码解决 ⭐

响应中文乱码分两种：

**字符流乱码**：Tomcat 默认用 ISO-8859-1 编码响应体，中文会乱码。解决：

```java
// 方式一：setContentType 带编码（推荐）
resp.setContentType("text/html;charset=utf-8");
resp.getWriter().write("中文");

// 方式二：分别设
resp.setCharacterEncoding("utf-8");   // 设流的编码
resp.setHeader("Content-Type", "text/html;charset=utf-8");  // 告诉浏览器编码
```

**字节流乱码**：字节流写文本时，要手动把字符串按 UTF-8 编码成字节：

```java
resp.getOutputStream().write("中文".getBytes("utf-8"));
```

> 💡 **最佳实践**：写文本统一用 `resp.setContentType("text/html;charset=utf-8")` + `getWriter()`，一行解决编码。这是最不容易出错的写法。

> 💡 **这就是 `@ResponseBody` 的底层**：Spring MVC 的 `@ResponseBody` 返回字符串/对象，底层就是 `getWriter().write(...)` + Jackson 序列化。`@RestController` 返回 JSON，底层就是设 `Content-Type: application/json` + 写序列化后的 JSON 字符串。

---

## 五、重定向

重定向是让浏览器**重新发一次请求**到新地址，地址栏会变。和上一篇的"转发"是对比关系。

### 5.1 重定向语法

```java
@WebServlet("/old")
public class OldServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 方式一：手动设状态码 + Location 头
        resp.setStatus(302);
        resp.setHeader("Location", "/new");

        // 方式二：专用方法（推荐，等价于上面两行）
        resp.sendRedirect("/new");
    }
}

@WebServlet("/new")
public class NewServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        resp.getWriter().write("这是新地址");
    }
}
```

访问 `/old`，浏览器地址栏变成 `/new`，显示"这是新地址"。

### 5.2 重定向 vs 转发 ⭐

这是面试高频，务必分清：

| 对比项 | 请求转发（forward） | 重定向（redirect） |
| :--- | :--- | :--- |
| 请求次数 | **1 次**（服务器内部） | **2 次**（浏览器重新发） |
| 地址栏 | **不变** | **变**（显示新地址） |
| Request 域 | 共享（同一 Request） | 不共享（新 Request） |
| 能否访问外部 | 不能（只能内部） | 能（可跳外部域名） |
| 方法 | `RequestDispatcher.forward()` | `response.sendRedirect()` |
| 使用场景 | 内部页面跳转、传数据 | 登录后跳首页、PRG 模式 |

> 💡 **PRG 模式（Post-Redirect-Get）**：表单 POST 提交后，不要直接返回页面，而是重定向到 GET 请求——这样用户刷新不会重复提交表单。这是 Web 开发的经典模式，Spring MVC 的 `redirect:` 前缀就是做这个。

> ⚠️ **转发和重定向的根因**：转发是**服务器内部**行为，浏览器不知情，所以地址栏不变、Request 共享；重定向是**服务器告诉浏览器"去新地址"**，浏览器重新发请求，所以地址栏变、Request 不共享。理解了"谁在跳"，就不会记混。

---

## 六、文件下载

文件下载是 Response 的典型应用：设响应头 + 用字节流写文件。

```java
@WebServlet("/download")
public class DownloadServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 1. 找到文件
        String filename = "报告.pdf";
        String realPath = getServletContext().getRealPath("/download/" + filename);
        FileInputStream in = new FileInputStream(realPath);

        // 2. 设响应头：告诉浏览器这是下载（Content-Disposition）
        //    attachment 表示附件下载，filename 指定下载文件名
        resp.setHeader("Content-Disposition", "attachment;filename=" + filename);
        resp.setContentType("application/octet-stream");   // 二进制流

        // 3. 字节流写出
        ServletOutputStream out = resp.getOutputStream();
        byte[] buf = new byte[1024];
        int len;
        while ((len = in.read(buf)) != -1) {
            out.write(buf, 0, len);
        }
        in.close();
    }
}
```

> ⚠️ **中文文件名乱码**：`Content-Disposition` 的 filename 中文在不同浏览器会乱码，需用 URL 编码：
> ```java
> filename = URLEncoder.encode(filename, "utf-8");
> resp.setHeader("Content-Disposition", "attachment;filename=" + filename);
> ```

> 💡 **这就是 `MultipartFile` 下载的底层**：Spring Boot 的文件下载，底层就是设 `Content-Disposition` 头 + 字节流写出。文件上传/下载在阶段六 15 详解。

---

## ⚠️ 重点

1. **Response 一次请求一个**：和 Request 成对，请求结束销毁。
2. **`setContentType` 必须在 `getWriter` 之前**：流获取后编码已定，再设无效。
3. **字符流和字节流二选一**：同时用抛 `IllegalStateException`。文本用字符流，二进制用字节流。
4. **响应乱码用 `setContentType("text/html;charset=utf-8")`**：一行解决，最不易错。
5. **`sendError` 后不能写响应体**：它会提交响应并返回错误页。
6. **重定向是 2 次请求、地址栏变**；转发是 1 次请求、地址栏不变——这是核心区别。
7. **PRG 模式**：表单 POST 后重定向到 GET，防止刷新重复提交。
8. **文件下载设 `Content-Disposition: attachment`**：告诉浏览器这是下载而非打开。

---

## 💻 实战案例：返回 JSON 接口

需求：写一个返回用户信息 JSON 的接口，模拟前后端分离的后端 API。

```java
@WebServlet("/api/user/info")
public class UserInfoServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 1. 设响应类型为 JSON + UTF-8（必须在 write 之前）
        resp.setContentType("application/json;charset=utf-8");

        // 2. 模拟查数据
        User user = new User(1, "张三", 20);

        // 3. 用 Jackson 序列化为 JSON
        ObjectMapper mapper = new ObjectMapper();
        String json = mapper.writeValueAsString(user);
        // {"id":1,"name":"张三","age":20}

        // 4. 字符流写出
        resp.getWriter().write(json);
    }
}
```

访问 `/api/user/info`，浏览器收到 JSON：`{"id":1,"name":"张三","age":20}`。

> 💡 **这就是 `@RestController` 的底层**：上面四步（设 JSON 类型 → 查数据 → 序列化 → 写流），Spring Boot 用一个 `@RestController` + 返回对象就搞定了：
> ```java
> @RestController
> public class UserInfoController {
>     @GetMapping("/api/user/info")
>     public User info() {
>         return new User(1, "张三", 20);  // 自动序列化为 JSON
>     }
> }
> ```
> 底层仍设 `Content-Type: application/json` + Jackson 序列化 + `getWriter().write()`，只是全自动了。

---

## 🚀 新版本补充

- **Servlet 3.1**：`getContentLengthLong()` 支持大响应体；非阻塞 IO（`WriteListener`）。
- **Servlet 4.0**：支持 HTTP/2 响应头、服务器推送（`PushBuilder`）。
- **Tomcat 8+**：默认 UTF-8，响应中文乱码大幅减少。

---

## 📌 在 Spring Boot 中

> 本篇讲的设状态码、响应头、写响应体、重定向、乱码、文件下载，在 Spring Boot 中用 `@ResponseBody`/`ResponseEntity` 封装。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 Response 原理排查"。实际开发你不用手动 `getWriter`/`setHeader`，但理解了 Response，返回 JSON、控制状态码、做下载、重定向时才知道底层在干什么。

### 1. 写响应体：从"getWriter().write"到"@ResponseBody 自动序列化"

**原生**：`resp.setContentType("application/json;charset=utf-8")` + `resp.getWriter().write(json)`，手动拼 JSON 字符串。
**Spring Boot**：`@RestController` 返回对象，自动序列化为 JSON。

```java
@RestController   // = @Controller + @ResponseBody，方法返回值自动写响应体
public class UserController {

    @GetMapping("/users/{id}")
    public User get(@PathVariable Long id) {
        return userService.findById(id);   // 返回 User 对象
        // 底层：Jackson 序列化为 JSON → 设 Content-Type: application/json → getWriter().write
    }

    @GetMapping("/users")
    public List<User> list() {
        return userService.findAll();      // 返回集合，自动序列化为 JSON 数组
    }
}
```

> 💡 **原理对应**：`@ResponseBody` 底层就是本篇 4.3 节的"设 Content-Type + getWriter().write"，只是用 Jackson 自动序列化对象为 JSON。**你本篇手动拼 JSON 的样板代码，Spring Boot 一个注解搞定**。

> 💡 **原理排查**：返回的 JSON 字段名不对？检查实体类的 `@JsonProperty("name")` 或 Jackson 命名策略（`spring.jackson.property-naming-strategy`）。返回 null 字段被过滤？检查 `@JsonInclude(JsonInclude.Include.NON_NULL)`。回到 Response 原理：响应体内容由序列化器决定。

### 2. 状态码与响应头：从"setStatus + setHeader"到"ResponseEntity"

**原生**：`resp.setStatus(201)` + `resp.setHeader("Location", "/users/1")`。
**Spring Boot**：`ResponseEntity` 链式 API 精确控制。

```java
@PostMapping("/users")
public ResponseEntity<User> create(@RequestBody User user) {
    User saved = userService.save(user);
    return ResponseEntity
            .status(HttpStatus.CREATED)              // 201
            .header("Location", "/users/" + saved.getId())  // 自定义响应头
            .body(saved);                            // 响应体
}

@GetMapping("/users/{id}")
public ResponseEntity<User> get(@PathVariable Long id) {
    User user = userService.findById(id);
    if (user == null) {
        return ResponseEntity.notFound().build();    // 404，无响应体
    }
    return ResponseEntity.ok(user);                   // 200 + body
}

@DeleteMapping("/users/{id}")
public ResponseEntity<Void> delete(@PathVariable Long id) {
    userService.delete(id);
    return ResponseEntity.noContent().build();       // 204 No Content
}
```

> 💡 **原理对应**：`ResponseEntity.status(201)` 底层就是 `resp.setStatus(201)`；`.header(...)` 就是 `resp.setHeader(...)`。本篇讲的响应行/响应头，Spring Boot 用 `ResponseEntity` 统一封装。

> 💡 **原理排查**：想返回特定状态码但用了 `@RestController` 默认 200？改用 `ResponseEntity` 包裹返回值，或加 `@ResponseStatus(HttpStatus.CREATED)`。回到 Response 原理：状态码由响应行控制。

### 3. 重定向：从"sendRedirect"到"redirect: 前缀"

**原生**：`resp.sendRedirect("/new")`，302 + Location 头，2 次请求地址栏变。
**Spring Boot**：返回 `redirect:` 前缀的视图名。

```java
@PostMapping("/login")
public String login(@RequestParam String username, @RequestParam String password) {
    if (authService.login(username, password)) {
        return "redirect:/home";     // 重定向到 /home（地址栏变，2 次请求）
    }
    return "redirect:/login?error";  // PRG 模式：表单提交后重定向，防刷新重复提交
}
```

```java
// 也可用 ResponseEntity 重定向
@GetMapping("/old")
public ResponseEntity<Void> old() {
    return ResponseEntity.status(302)
            .header("Location", "/new")
            .build();
}
```

> 💡 **原理对应**：`redirect:/home` 底层就是 `resp.sendRedirect("/home")`——设 302 状态码 + Location 头。**本篇 5.2 节讲的重定向 vs 转发区别，在 Spring Boot 里用 `redirect:` vs `forward:`（或视图名）区分**。

> 💡 **原理排查**：重定向后 Session 数据丢失？因为重定向是 2 次请求、新 Request，request 域不共享（本篇 5.2 节）。要跨请求传数据用 Session 或重定向参数（`redirect:/home?msg=ok`）。回到 Response 原理：重定向是两次独立请求。

### 4. 转发：从"RequestDispatcher.forward"到"forward: 前缀 / 视图名"

**原生**：`req.getRequestDispatcher("/page").forward(req, resp)`，1 次请求地址栏不变。
**Spring Boot**：返回视图名（默认转发到模板）或 `forward:` 前缀。

```java
@GetMapping("/user/{id}")
public String show(@PathVariable Long id, Model model) {
    model.addAttribute("user", userService.findById(id));
    return "user/detail";        // 转发到 Thymeleaf 模板 user/detail.html（1 次请求）
    // return "forward:/other";  // 显式转发到另一个 Controller 路径
}
```

> 💡 **原理对应**：返回视图名底层就是 `RequestDispatcher.forward` 到模板文件。**本篇讲的"转发是 1 次请求、request 域共享"，Spring MVC 的 Model.addAttribute 就是往 request 域塞数据给模板用**。

### 5. 乱码：从"setContentType charset"到"默认 UTF-8"

**原生**：`resp.setContentType("text/html;charset=utf-8")` 手动设（本篇 4.3 节）。
**Spring Boot**：默认 UTF-8，无需手动处理。

```yaml
server:
  servlet:
    encoding:
      charset: UTF-8
      force: true    # 强制响应也用 UTF-8
```

> 💡 **原理对应**：Spring Boot 的 `CharacterEncodingFilter` 在响应写出前统一设编码。**你本篇手动设的 `setContentType("...;charset=utf-8")`，Spring Boot 全局自动完成**。

> 💡 **原理排查**：返回中文乱码？检查 `force: true`、Jackson 编码、响应头 `Content-Type` 是否带 `charset`。回到 Response 原理：响应体编码由响应头 `Content-Type` 的 charset 决定。

### 6. 文件下载：从"setHeader Content-Disposition + 字节流"到"ResponseEntity<Resource>"

**原生**：`resp.setHeader("Content-Disposition", "attachment;filename=xx")` + `getOutputStream()` 写字节（本篇第六节）。
**Spring Boot**：`ResponseEntity` + `Resource` 封装。

```java
@GetMapping("/download/{filename}")
public ResponseEntity<Resource> download(@PathVariable String filename) throws IOException {
    Resource file = new FileSystemResource("D:/files/" + filename);
    if (!file.exists()) {
        return ResponseEntity.notFound().build();
    }
    // 文件名中文需 URL 编码（对应本篇第六节的 URLEncoder）
    String encoded = URLEncoder.encode(filename, "utf-8").replace("+", "%20");
    return ResponseEntity.ok()
            .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=" + encoded)
            .contentType(MediaType.APPLICATION_OCTET_STREAM)
            .body(file);   // 框架自动用字节流写出 Resource
}
```

> 💡 **原理对应**：`Content-Disposition` 头 + 字节流写出，和本篇第六节完全一样，只是用 `Resource` 抽象文件源、框架自动写流。**本篇学的下载原理（attachment 头、字节流、中文文件名编码），Spring Boot 一个都没少**。

> 💡 **原理排查**：下载文件名乱码？检查 `URLEncoder.encode` + `replace("+","%20")`（本篇第六节讲过）。下载内容损坏？检查 `Content-Type` 是否 `application/octet-stream`、是否用了字符流写二进制（本篇 4 节强调字符流字节流不能混用）。

### 7. 返回非 JSON：从"手动设 Content-Type"到"produces"

**原生**：`resp.setContentType("text/html")` 或 `image/jpeg` 手动设。
**Spring Boot**：`produces` 属性指定响应类型。

```java
@GetMapping(value = "/html", produces = "text/html")
public String html() {
    return "<h1>Hello</h1>";   // 返回 HTML 而非 JSON
}

@GetMapping(value = "/image/{id}", produces = "image/jpeg")
public ResponseEntity<byte[]> image(@PathVariable Long id) throws IOException {
    byte[] bytes = Files.readAllBytes(Path.of("D:/img/" + id + ".jpg"));
    return ResponseEntity.ok().body(bytes);   // 返回二进制图片
}
```

> 💡 **原理对应**：`produces` 底层就是设 `Content-Type` 响应头。本篇 4 节讲的"字符流写文本、字节流写二进制"，Spring Boot 用返回类型 + produces 自动选择。

---

> 一句话：**Spring MVC 把 Response 的设状态码、设头、写体、重定向、下载全部封装了**。`@ResponseBody` 自动写 JSON、`ResponseEntity` 精确控制状态码和头、`redirect:`/`forward:` 处理跳转、`Resource` 做下载。但底层操作的还是这个 `HttpServletResponse`——理解了本篇，Spring Boot 的响应处理对你就是透明的。**出乱码、下载损坏、状态码不对、重定向丢数据问题时，你仍要回到 Response 原理排查**：编码看 Content-Type 的 charset、下载看 Content-Disposition 和字节流、重定向看 2 次请求特性。

## 本章小结

本篇讲清了 `HttpServletResponse` 的核心用法：设置状态码（`setStatus`/`sendError`）、响应头（`setContentType` 等）、写响应体（字符流 `getWriter` 写文本、字节流 `getOutputStream` 写二进制）、中文乱码解决（`setContentType("...;charset=utf-8")`）、重定向（`sendRedirect`，2 次请求地址栏变）与转发的区别、文件下载（`Content-Disposition` 头）。至此阶段二完成，Request 和 Response 这对核心对象你已掌握。下一篇 [06-Cookie](06-Cookie.md) 进入会话管理——解决 HTTP 无状态下的状态保持问题。
