# Cookie

前五篇你掌握了请求和响应的完整流程，但有个问题没解决：HTTP 是**无状态**的——服务器记不住"你登没登录"。你刚登录成功，点下一个页面，服务器又把你当陌生人。怎么让服务器"记住"你？答案就是**会话管理**，而 Cookie 是其中一种方案。本篇讲清 Cookie 的原理、创建读取、生命周期、安全局限，为下一篇 Session 打基础。

> 💡 本篇建议用浏览器 F12 → Application → Cookies 边读边看：每学一个操作，都在浏览器里观察 Cookie 的变化，亲眼看到"服务器发了什么、浏览器存了什么、下次请求带了什么"。

---

## 一、会话管理概述

### 1.1 为什么需要会话管理

HTTP 是**无状态协议**：服务器处理完一个请求就"忘了"，下一个请求要重新识别客户端。这导致：

- 登录后点其他页面 → 服务器不知道你登录了 → 又要登录
- 加购物车后刷新 → 服务器不知道购物车里有啥 → 购物车空了

**会话管理**就是让服务器"记住"客户端状态的技术。两种方案：

| 方案 | 存储位置 | 特点 |
| :--- | :--- | :--- |
| **Cookie** | **浏览器端** | 数据存客户端，每次请求自动带 |
| **Session** | **服务器端** | 数据存服务器，靠 Cookie 传 ID（下篇讲） |

> 💡 **Cookie 和 Session 的关系**：Cookie 是客户端方案（数据在浏览器），Session 是服务器方案（数据在服务器，靠 Cookie 传 ID 找到对应数据）。下篇 07 会讲 Session 如何依赖 Cookie。

---

## 二、Cookie 原理

### 2.1 工作流程

```
1. 首次请求（无 Cookie）
   浏览器 ──请求──▶ 服务器
   浏览器 ◀──响应── 服务器（响应头带 Set-Cookie: user=张三）

2. 浏览器保存 Cookie：user=张三

3. 再次请求（自动带 Cookie）
   浏览器 ──请求（请求头带 Cookie: user=张三）──▶ 服务器
   服务器读到 Cookie，识别出用户
```

### 2.2 两个关键响应头/请求头

| 方向 | 头字段 | 作用 |
| :--- | :--- | :--- |
| 响应 → 浏览器 | `Set-Cookie: name=value` | 服务器让浏览器存 Cookie |
| 浏览器 → 请求 | `Cookie: name=value` | 浏览器请求时自动带上存的 Cookie |

> 💡 **Cookie 的本质就是 HTTP 头**：服务器通过 `Set-Cookie` 响应头"种"Cookie，浏览器通过 `Cookie` 请求头"回"Cookie。理解了这两个头，Cookie 的原理就通了。

---

## 三、Cookie 的 API

### 3.1 创建并发送 Cookie

```java
@WebServlet("/setCookie")
public class SetCookieServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 1. 创建 Cookie 对象
        Cookie cookie = new Cookie("user", "张三");

        // 2. 设置属性（可选）
        cookie.setMaxAge(60 * 60);   // 存活 1 小时（秒）
        cookie.setPath("/");          // 对整个站点有效

        // 3. 通过 Response 发送（加到 Set-Cookie 响应头）
        resp.addCookie(cookie);

        resp.setContentType("text/html;charset=utf-8");
        resp.getWriter().write("Cookie 已设置");
    }
}
```

> ⚠️ **Cookie 的值不能直接存中文**（旧版规范）。Tomcat 8+ 支持部分中文，但**最佳实践是存英文/数字/编码后的值**，中文用 `URLEncoder.encode()` 编码：

```java
Cookie cookie = new Cookie("user", URLEncoder.encode("张三", "utf-8"));
// 读取时解码
String value = URLDecoder.decode(cookie.getValue(), "utf-8");
```

### 3.2 读取 Cookie

浏览器请求时自动带 Cookie，服务器用 `req.getCookies()` 读取：

```java
@WebServlet("/getCookie")
public class GetCookieServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        Cookie[] cookies = req.getCookies();

        if (cookies != null) {
            for (Cookie c : cookies) {
                String name = c.getName();
                String value = URLDecoder.decode(c.getValue(), "utf-8");
                resp.getWriter().write(name + " = " + value + "<br>");
            }
        } else {
            resp.getWriter().write("没有 Cookie");
        }
    }
}
```

> ⚠️ **`getCookies()` 可能返回 null**：首次访问没有 Cookie 时返回 null，遍历前必须判空，否则 NullPointerException。

### 3.3 删除 Cookie

Cookie 没有"删除"方法，**靠覆盖同名同路径的 Cookie，设 `setMaxAge(0)`** 让其立即过期：

```java
Cookie cookie = new Cookie("user", "");   // 同名
cookie.setMaxAge(0);                       // 立即过期
cookie.setPath("/");                       // 同路径（必须一致）
resp.addCookie(cookie);                    // 覆盖
```

> ⚠️ **删除 Cookie 的两个关键**：`name` 和 `path` 必须与原 Cookie **完全一致**，否则不会覆盖而是新增。这是初学者常踩的坑——删了发现没删掉，多半是 path 不一致。

---

## 四、Cookie 的属性 ⭐

### 4.1 核心属性

| 属性 | 方法 | 作用 |
| :--- | :--- | :--- |
| `name` / `value` | 构造方法 | Cookie 的键值 |
| `maxAge` | `setMaxAge(int)` | 存活时间（秒），决定持久化 |
| `path` | `setPath(String)` | 有效路径 |
| `domain` | `setDomain(String)` | 有效域名 |
| `httpOnly` | `setHttpOnly(true)` | 禁止 JS 读取（防 XSS） |
| `secure` | `setSecure(true)` | 仅 HTTPS 传输 |
| `sameSite` | — | 跨站携带策略（防 CSRF） |

### 4.2 maxAge：会话级 vs 持久级 ⭐

这是 Cookie 最重要的属性，决定 Cookie 的存活时间：

| maxAge 值 | 类型 | 行为 |
| :--- | :--- | :--- |
| **正数** | 持久 Cookie | 存到磁盘，到时间才删除（关闭浏览器仍在） |
| **负数（默认 -1）** | 会话 Cookie | 存内存，**浏览器关闭即删除** |
| **0** | 删除 | 立即过期删除 |

```java
// 会话级：浏览器关了就没了
cookie.setMaxAge(-1);

// 持久级：存 7 天
cookie.setMaxAge(60 * 60 * 24 * 7);

// 删除
cookie.setMaxAge(0);
```

> 💡 **"记住我"功能**：登录页勾选"记住我"，就是给登录 Cookie 设一个较长的 `maxAge`（如 7 天），下次打开浏览器仍登录。不勾选则是会话级 Cookie，关浏览器即退出。

### 4.3 path：有效路径

Cookie 只在匹配的路径下才发送：

```java
cookie.setPath("/");          // 整个站点都带（最常用）
cookie.setPath("/user");     // 只有 /user 及子路径带
```

> ⚠️ **path 不一致导致 Cookie 读不到**：如果设 Cookie 时 `path="/user"`，访问 `/order` 时浏览器不会带这个 Cookie，服务器读不到。**默认设 `path="/"` 最省心**。

### 4.4 安全属性

```java
cookie.setHttpOnly(true);    // JS 的 document.cookie 读不到（防 XSS 偷 Cookie）
cookie.setSecure(true);       // 仅 HTTPS 下传输（防中间人窃听）
```

> 💡 **HttpOnly 防的是什么**：XSS 攻击注入恶意 JS，`document.cookie` 可读到用户 Cookie 发给攻击者。设了 `HttpOnly`，JS 就读不到，Cookie 只用于 HTTP 传输。**敏感 Cookie（登录态）务必设 HttpOnly**。

> 💡 **SameSite 防的是什么**：CSRF 攻击诱导用户在第三方网站点击，浏览器自动带目标站 Cookie 发请求。`SameSite=Strict/Lax` 限制跨站携带，是现代浏览器防 CSRF 的手段。Spring Security 默认开启 CSRF Token 也是为此。

---

## 五、Cookie 的局限

| 局限 | 说明 |
| :--- | :--- |
| 大小有限 | 单个 Cookie 一般 4KB，每个域名约 20 个 |
| 不安全 | 存客户端，可被查看/篡改，**不能存敏感信息**（密码、金额） |
| 可被禁用 | 用户可关闭浏览器 Cookie 功能，需有降级方案 |
| 增加流量 | 每次请求都带所有匹配 Cookie，浪费带宽 |

> ⚠️ **绝对不要在 Cookie 里存明文密码、金额、权限等敏感数据**。Cookie 存客户端，用户可随意查看修改。要存就存一个**不透明的 ID**（如 Session ID），真正的数据放服务器（这就是 Session 的思路）。

---

## ⚠️ 重点

1. **Cookie 存客户端（浏览器）**，每次请求自动通过 `Cookie` 请求头带上。
2. **两个关键头**：`Set-Cookie`（响应，种 Cookie）、`Cookie`（请求，带 Cookie）。
3. **`getCookies()` 可能返回 null**：首次访问无 Cookie，遍历前判空。
4. **maxAge 三种值**：正数持久、负数会话级（默认）、0 删除。
5. **删除 Cookie 靠覆盖**：同名同 path + `setMaxAge(0)`，path 不一致删不掉。
6. **中文用 URL 编解码**：`URLEncoder.encode` / `URLDecoder.decode`。
7. **path 默认设 `/`**：否则其他路径读不到 Cookie。
8. **敏感 Cookie 设 HttpOnly + Secure**：防 XSS 偷取、防窃听。
9. **不存敏感数据**：Cookie 可被查看篡改，只存 ID 类不透明值。

---

## 💻 实战案例：记住我登录

需求：登录页勾选"记住我"，下次访问自动显示用户名。

**前端 `login.html`**：

```html
<form action="/login" method="post">
    用户名：<input type="text" name="username" value=""><br>
    密码：<input type="password" name="password"><br>
    <input type="checkbox" name="remember"> 记住我<br>
    <button>登录</button>
</form>
```

**后端 `LoginServlet`**：

```java
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        req.setCharacterEncoding("utf-8");
        String username = req.getParameter("username");
        String password = req.getParameter("password");
        String remember = req.getParameter("remember");

        resp.setContentType("text/html;charset=utf-8");

        if ("admin".equals(username) && "123456".equals(password)) {
            // 登录成功
            if ("on".equals(remember)) {
                // 勾选记住我：存持久 Cookie（7 天）
                Cookie c = new Cookie("username", URLEncoder.encode(username, "utf-8"));
                c.setMaxAge(60 * 60 * 24 * 7);   // 7 天
                c.setPath("/");
                c.setHttpOnly(true);
                resp.addCookie(c);
            }
            resp.getWriter().write("<h1>登录成功</h1>");
        } else {
            resp.getWriter().write("<h1>登录失败</h1>");
        }
    }
}
```

**回显用户名**：访问登录页时读 Cookie 自动填充：

```java
@WebServlet("/loginPage")
public class LoginPageServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        String savedUser = "";
        Cookie[] cookies = req.getCookies();
        if (cookies != null) {
            for (Cookie c : cookies) {
                if ("username".equals(c.getName())) {
                    savedUser = URLDecoder.decode(c.getValue(), "utf-8");
                }
            }
        }
        resp.getWriter().write(
            "<form action='/login' method='post'>" +
            "用户名：<input type='text' name='username' value='" + savedUser + "'><br>" +
            "密码：<input type='password' name='password'><br>" +
            "<input type='checkbox' name='remember'> 记住我<br>" +
            "<button>登录</button></form>"
        );
    }
}
```

> 💡 **这就是 `@CookieValue` 的底层**：Spring MVC 的 `@CookieValue("username") String user`，底层就是遍历 `req.getCookies()` 找同名的。理解了本篇，`@CookieValue` 就是语法糖。

---

## 🚀 新版本补充

- **RFC 6265（现代标准）**：Cookie 规范统一，支持 `HttpOnly`、`SameSite`。
- **SameSite 属性**：`Strict`（完全不跨站带）、`Lax`（部分跨站带，默认）、`None`（随意带，需 Secure）。现代浏览器默认 `Lax`，防 CSRF。
- **Cookie 前缀**：`__Host-` 和 `__Secure-` 前缀强制安全属性，防子域名伪造。

---

## 📌 在 Spring Boot 中

> 本篇讲的 Cookie 创建读取、maxAge、path、HttpOnly，在 Spring Boot 中用 `ResponseCookie` 和 `@CookieValue` 封装。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 Cookie 原理排查"。实际开发你很少直接手写 Cookie——登录态多用 Session/JWT，但记住我、偏好设置、跨域 Cookie 仍要用到，理解了本篇原理才不会踩坑。

### 1. 读 Cookie：从"getCookies 遍历"到"@CookieValue"

**原生**：`req.getCookies()` 遍历找同名 Cookie（本篇 3.2 节），还要判空。
**Spring Boot**：`@CookieValue` 自动注入。

```java
@GetMapping("/profile")
public String profile(@CookieValue(value = "username", defaultValue = "guest") String username) {
    // username Cookie 不存在时用默认值 "guest"
    return "欢迎 " + username;
}
```

> 💡 **原理对应**：`@CookieValue` 底层就是遍历 `req.getCookies()` 找同名的，只是自动注入+判空+设默认值。本篇 3.2 节的手动遍历代码，Spring Boot 一个注解搞定。

> 💡 **原理排查**：`@CookieValue` 报 400 "Missing cookie"？没加 `defaultValue` 且前端没带这个 Cookie。回到 Cookie 原理：Cookie 不存在时 `getCookies()` 返回 null 或找不到对应项。

### 2. 写 Cookie：从"new Cookie + addCookie"到"ResponseCookie"

**原生**：`new Cookie("user", value)` + `setMaxAge` + `setPath` + `resp.addCookie`（本篇 3.1 节）。
**Spring Boot**：`ResponseCookie` 构建器，更现代、类型安全。

```java
@PostMapping("/login")
public String login(@RequestParam String username, HttpServletResponse response) {
    // 用 ResponseCookie 构建器（推荐，比 new Cookie 更现代）
    ResponseCookie cookie = ResponseCookie.from("username", URLEncoder.encode(username, "utf-8"))
            .maxAge(Duration.ofDays(7))     // 持久化 7 天（对应 setMaxAge）
            .path("/")                       // 全站有效（对应 setPath）
            .httpOnly(true)                  // 防 XSS（对应 setHttpOnly）
            .secure(true)                    // 仅 HTTPS（对应 setSecure）
            .sameSite("Lax")                 // 防 CSRF（原生 Cookie API 不支持，需 ResponseCookie）
            .build();
    response.addHeader("Set-Cookie", cookie.toString());
    return "登录成功";
}
```

> 💡 **原理对应**：`ResponseCookie` 底层仍是 `Set-Cookie` 响应头，和本篇 2.2 节讲的完全一样。只是用构建器 API 替代了 `new Cookie` + 一串 setter，且支持 `SameSite`（原生 `javax.servlet.http.Cookie` 不支持 SameSite，这是 `ResponseCookie` 的优势）。

> 💡 **原理排查**：Cookie 设了但浏览器不存？检查 `path` 是否覆盖当前路径、`secure=true` 时是否用了 HTTPS、`SameSite=Strict` 是否阻断了跨站请求。回到 Cookie 原理：path/domain/secure/sameSite 任一不满足，浏览器就不存或不带。

### 3. 删 Cookie：从"同名同 path + maxAge(0)"到"ResponseCookie maxAge(0)"

**原生**：`new Cookie("user","")` + `setMaxAge(0)` + `setPath("/")` + `addCookie` 覆盖（本篇 3.3 节）。
**Spring Boot**：同样思路，用 `ResponseCookie` 覆盖。

```java
@GetMapping("/logout")
public String logout(HttpServletResponse response) {
    ResponseCookie cookie = ResponseCookie.from("username", "")
            .maxAge(0)         // 立即过期（对应 setMaxAge(0)）
            .path("/")          // ★ 必须和设值时同 path，否则删不掉
            .build();
    response.addHeader("Set-Cookie", cookie.toString());
    return "已注销";
}
```

> 💡 **原理排查**：注销后 Cookie 还在？检查 `path` 是否和设值时**完全一致**——本篇 3.3 节强调过，name 和 path 不一致不会覆盖而是新增。这是 Cookie 删除最常见的坑，Spring Boot 里同样适用。

### 4. "记住我"功能：从"手写 Cookie"到"Spring Security remember-me"

**原生**：本篇实战案例手写 `username` Cookie + maxAge 7 天。
**Spring Boot**：Spring Security 内置 `remember-me` 配置，自动管理记住我 Cookie。

```yaml
spring:
  security:
    remember-me:
      key: my-secret-key       # 加密 token 的密钥
      token-validity-seconds: 604800  # 7 天
```

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(auth -> auth
                .anyRequest().authenticated())
            .formLogin(form -> form
                .loginPage("/login").permitAll())
            .rememberMe(rm -> rm            // ★ 开启记住我
                .key("my-secret-key")
                .tokenValiditySeconds(7 * 24 * 3600));
        return http.build();
    }
}
```

> 💡 **原理对应**：Spring Security 的 `remember-me` 底层就是本篇实战案例的逻辑——登录成功后设一个持久 Cookie（maxAge 7 天），下次访问带这个 Cookie 自动登录。只是它用加密 token（而非明文用户名）+ `RememberMeAuthenticationFilter` 自动处理，更安全。

> 💡 **为什么不用明文 Cookie 存登录态**：本篇第五节强调过"不存敏感数据"。Spring Security 的 remember-me 存的是加密 token，不是明文用户名密码——即使被看到也无所谓。**理解了本篇的 Cookie 安全局限，才能理解为什么 Spring Security 要这么设计**。

### 5. Cookie 的安全配置（实际开发必配）

生产环境的 Cookie 必须配齐安全属性，`ResponseCookie` 一站式搞定：

```java
ResponseCookie cookie = ResponseCookie.from("token", jwtToken)
        .httpOnly(true)      // ✅ 防 XSS 偷 Cookie（JS 读不到）
        .secure(true)        // ✅ 仅 HTTPS 传输（防中间人窃听）
        .sameSite("Lax")     // ✅ 防 CSRF（现代浏览器默认 Lax）
        .maxAge(Duration.ofHours(2))
        .path("/")
        .build();
```

> 💡 **原理对应**：这三个安全属性正是本篇 4.4 节讲的 HttpOnly/Secure/SameSite。**生产环境 Cookie 必须配齐这三项**，否则有 XSS 偷 Cookie、中间人窃听、CSRF 跨站请求伪造的风险。理解了本篇的安全原理，才知道为什么 Spring Boot 文档反复强调要配这些。

### 6. Cookie vs Session vs JWT 的选型

实际开发登录态的三种方案，理解了本篇 Cookie 原理才能选对：

| 方案 | 存储位置 | 适用场景 |
| :--- | :--- | :--- |
| **Cookie** | 浏览器 | 偏好设置、记住我（非敏感） |
| **Session** | 服务器内存/Redis | 传统 Web 应用登录态（下篇讲） |
| **JWT** | 浏览器（Cookie/LocalStorage） | 前后端分离、微服务、跨域 |

```java
// JWT 方案：Token 存 Cookie（HttpOnly）或 LocalStorage
ResponseCookie cookie = ResponseCookie.from("token", jwtService.generate(user))
        .httpOnly(true).secure(true).sameSite("Lax")
        .maxAge(Duration.ofHours(2)).path("/")
        .build();
```

> 💡 **JWT 仍依赖 Cookie**：JWT Token 本质是个字符串，仍需通过 Cookie（或 Authorization 头）传给服务器。**本篇学的 Cookie 原理（Set-Cookie/Cookie 头、maxAge、path、HttpOnly），是 JWT 传输的基础**。

---

> 一句话：**Cookie 是会话管理的客户端方案**。Spring Boot 里你很少直接手写 Cookie——登录态用 Session（下篇）或 JWT，`@CookieValue` 读 Cookie 是语法糖，`ResponseCookie` 写 Cookie 更现代。但 Cookie 的原理（Set-Cookie/Cookie 头、maxAge 三种值、path 匹配、HttpOnly/Secure/SameSite 安全）是所有 Web 会话的基础，Spring Session、JWT 的传输都依赖它。**出 Cookie 删不掉、跨域不带、被 XSS 偷的问题时，你仍要回到本篇原理排查**：path 一致吗、secure/sameSite 配对了吗、HttpOnly 设了吗。

## 本章小结

本篇讲清了 Cookie：它是存浏览器端的小段数据，服务器通过 `Set-Cookie` 响应头种下，浏览器通过 `Cookie` 请求头自动带回。重点掌握 Cookie 的创建读取、maxAge 三种值（正数持久/负数会话/0删除）、path 有效路径、HttpOnly/Secure 安全属性、删除靠同名同路径覆盖。核心认知：Cookie 存客户端、不安全、不存敏感数据。下一篇 [07-Session](07-Session.md) 讲服务器端的会话方案——数据存服务器，靠 Cookie 传 ID 找回，解决了 Cookie 不安全的问题。
