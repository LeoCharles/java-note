# Session

上一篇的 Cookie 把数据存在浏览器端，但不安全、可被篡改、大小受限。如果登录态、购物车这些数据存服务器呢？这就是 **Session**（会话）。它把数据存在服务器，靠 Cookie 传一个 ID 来"认人"——既安全又能存大对象。本篇讲清 Session 的原理、创建读取、销毁超时、URL 重写，以及与 Cookie 的对比选型。这是 Spring Session + Redis 解决分布式会话的底层基础。

> 💡 本篇建议用浏览器 F12 观察 JSESSIONID 这个 Cookie：访问一个创建 Session 的 Servlet，看响应头里的 `Set-Cookie: JSESSIONID=xxx`，再刷新看请求头自动带上它——亲眼看到 Session 是怎么"认人"的。

---

## 一、Session 是什么

### 1.1 定义

**Session** 是服务器端的会话对象，每个客户端对应一个 Session，存在服务器内存里。它解决的核心问题：**HTTP 无状态下，如何在多次请求间保持客户端状态**。

```
浏览器 ──请求──▶ 服务器（创建 Session，分配 ID）
浏览器 ◀──响应── 服务器（Set-Cookie: JSESSIONID=abc123）

浏览器 ──请求（带 Cookie: JSESSIONID=abc123）──▶ 服务器
                                                服务器根据 ID 找到对应 Session → 取出数据
```

### 1.2 Session 与 Cookie 的关系 ⭐

Session **依赖 Cookie 传 ID**，这是理解 Session 的关键：

| 维度 | Cookie | Session |
| :--- | :--- | :--- |
| 存储位置 | **浏览器端** | **服务器端** |
| 安全性 | 低（可查看篡改） | 高（数据在服务器） |
| 大小 | 4KB 限制 | 无限制（受服务器内存） |
| 生命周期 | 由 maxAge 控制 | 由超时/手动销毁控制 |
| 传输 | 每次请求自动带 | 靠 Cookie 传 JSESSIONID |

> 💡 **一句话理解**：Cookie 是"客户端存数据"，Session 是"服务器存数据 + Cookie 传 ID"。Session 的数据安全地躺在服务器，浏览器只拿着一个不透明的 ID（JSESSIONID）来认领——即使 ID 被看到也无所谓，因为真正的数据不在浏览器。

> ⚠️ **Session 的 ID 仍存在 Cookie 里**：JSESSIONID 本身是个 Cookie（会话级，浏览器关了就没）。所以 Session **依赖 Cookie**——如果浏览器禁用 Cookie，Session 默认失效（需 URL 重写救，见第五节）。

---

## 二、Session 的 API

### 2.1 获取 Session

```java
@WebServlet("/session")
public class SessionServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // 获取当前请求的 Session（没有就创建）
        HttpSession session = req.getSession();        // 等价 getSession(true)

        // 获取但不创建（没有返回 null）
        HttpSession session2 = req.getSession(false);  // 没有则 null
    }
}
```

| 方法 | 行为 |
| :--- | :--- |
| `getSession()` / `getSession(true)` | 没有就**创建**，有就返回 |
| `getSession(false)` | 没有返回 **null**，有就返回 |

> 💡 **登录判断的常见用法**：登录后 `getSession()` 创建 Session 存用户信息；访问受保护页面时 `getSession(false)` 取，若为 null 说明没登录，跳登录页。

### 2.2 存取数据

Session 是个域对象，用 `setAttribute`/`getAttribute`：

```java
// 存
session.setAttribute("user", new User("张三", 20));
session.setAttribute("cart", Arrays.asList("商品1", "商品2"));

// 取
User user = (User) session.getAttribute("user");

// 删
session.removeAttribute("user");
```

> 💡 **Session 域的作用范围**：整个会话（跨多次请求），只要浏览器没关、Session 没超时，数据一直在。这是它和 request 域（一次请求）的区别——四大域对象里 Session 是"会话级"。

### 2.3 完整登录示例

```java
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        req.setCharacterEncoding("utf-8");
        String username = req.getParameter("username");
        String password = req.getParameter("password");

        resp.setContentType("text/html;charset=utf-8");
        if ("admin".equals(username) && "123456".equals(password)) {
            // 登录成功：创建 Session，存用户信息
            HttpSession session = req.getSession();
            session.setAttribute("user", username);
            resp.getWriter().write("登录成功");
        } else {
            resp.getWriter().write("登录失败");
        }
    }
}

@WebServlet("/home")
public class HomeServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        HttpSession session = req.getSession(false);   // 不创建，只取
        if (session != null && session.getAttribute("user") != null) {
            String user = (String) session.getAttribute("user");
            resp.getWriter().write("欢迎 " + user);
        } else {
            resp.sendRedirect("/login.html");   // 没登录，跳登录页
        }
    }
}
```

> 💡 **这就是登录鉴权的雏形**：登录存 Session，访问时取 Session 判断。Spring Security 的 `@PreAuthorize`、Filter 链鉴权，底层就是这个模式——只是把判断逻辑封装到框架里了。

---

## 三、Session 的原理：JSESSIONID ⭐

### 3.1 ID 是怎么来的

1. 浏览器首次访问 `getSession()`，服务器**创建一个 Session 对象**，分配唯一 ID；
2. 服务器通过响应头 `Set-Cookie: JSESSIONID=abc123` 把 ID 发给浏览器；
3. 浏览器存下这个 Cookie（会话级，浏览器关了就没）；
4. 后续请求浏览器自动带 `Cookie: JSESSIONID=abc123`；
5. 服务器根据 ID 找到对应 Session，取出数据。

### 3.2 验证 JSESSIONID

```java
@WebServlet("/showId")
public class ShowIdServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        HttpSession session = req.getSession();
        String id = session.getId();   // 这个会话的 ID
        resp.getWriter().write("JSESSIONID = " + id);
    }
}
```

首次访问看响应头：`Set-Cookie: JSESSIONID=abc123; Path=/demo; HttpOnly`。再次访问看请求头：`Cookie: JSESSIONID=abc123`。

> 💡 **JSESSIONID 默认是会话级 Cookie**：浏览器关闭即丢失，下次访问又是新 Session。这就是"关浏览器要重新登录"的原因。要跨浏览器保持，需把 JSESSIONID 改成持久 Cookie（一般不做，改用持久化 Token）。

---

## 四、Session 的销毁与超时 ⭐

Session 不能无限存在，否则服务器内存会被撑爆。销毁有两种方式：

### 4.1 手动销毁

```java
// 注销登录：销毁当前 Session
HttpSession session = req.getSession(false);
if (session != null) {
    session.invalidate();   // 立即销毁，里面所有数据清空
}
```

### 4.2 超时自动销毁

Session 有**默认超时时间**（Tomcat 默认 30 分钟），超过这个时间没访问就自动销毁：

```java
// 设置单个 Session 的超时（秒）
session.setMaxInactiveInterval(60 * 30);   // 30 分钟

// web.xml 设置全局默认（分钟）
<session-config>
    <session-timeout>30</session-timeout>
</session-config>
```

> ⚠️ **超时时间是"空闲超时"**：不是"创建后 30 分钟销毁"，而是"30 分钟没访问才销毁"。每次访问会重置计时器。理解这一点，就不会疑惑"为什么我一直在操作却没被踢下线"。

> 💡 **为什么默认 30 分钟**：平衡安全与体验。太短用户操作慢就被踢，太长占用内存。银行类系统常设更短（5-10 分钟），普通系统 30 分钟。Spring Boot 用 `server.servlet.session.timeout` 配置。

### 4.3 Session 销毁的时机

| 触发条件 | 方式 |
| :--- | :--- |
| 调用 `invalidate()` | 手动立即销毁 |
| 超过超时时间未访问 | 服务器自动销毁 |
| 服务器非正常关闭 | 内存清空（重启后所有 Session 没了） |
| 浏览器关闭 | **JSESSIONID 没了**，但服务器端 Session 还在（等超时才销毁） |

> ⚠️ **关浏览器 ≠ 销毁 Session**：浏览器关闭只是丢了 JSESSIONID Cookie，服务器端的 Session 对象还在内存，要等超时才回收。这就是为什么重启 Tomcat 后要重新登录——内存里的 Session 全没了。

---

## 五、URL 重写：Cookie 禁用时的救星

如果浏览器禁用 Cookie，JSESSIONID 无法通过 Cookie 传，Session 就失效。解决方法：**URL 重写**，把 ID 拼到 URL 里。

```java
// 把 ID 拼到 URL 后面（;jsessionid=xxx）
String url = resp.encodeURL("/home");
// 生成：/home;jsessionid=abc123

// 重定向时重写
String redirectUrl = resp.encodeRedirectURL("/login");
```

生成的链接带 `;jsessionid=xxx`，即使没 Cookie 也能传 ID。

> 💡 **现代开发几乎不用 URL 重写**：现代浏览器默认开 Cookie，禁用 Cookie 的场景极少。Spring Boot 也不推荐 URL 重写（URL 丑陋、易泄露 ID）。了解原理即可，实际项目遇到禁用 Cookie 直接提示用户开启。

---

## 六、Cookie 与 Session 对比与选型 ⭐

| 对比项 | Cookie | Session |
| :--- | :--- | :--- |
| 存储位置 | 浏览器端 | 服务器端 |
| 安全性 | 低 | 高 |
| 数据大小 | 4KB | 受服务器内存 |
| 生命周期 | maxAge 控制 | 超时/invalidate |
| 服务器压力 | 小（数据在客户端） | 大（数据在服务器） |
| 分布式 | 天然支持（数据在客户端） | **需共享**（多服务器要同步） |
| 典型场景 | 偏好设置、记住我 | 登录态、购物车 |

> 💡 **选型建议**：
> - **不敏感的小数据**（主题、语言、记住我）→ Cookie
> - **敏感数据/大对象**（登录态、购物车）→ Session
> - **分布式部署**→ Session 要共享（见下方 Spring Boot 对应）

> ⚠️ **Session 的分布式难题**：单机 Session 存内存，多台服务器时用户请求可能打到不同机器，Session 找不到。解决方案：Session 粘性（Nginx 按用户固定转发）、Session 共享（Redis 存）、JWT（无状态 Token）。这就是 Spring Session + Redis 要解决的。

---

## ⚠️ 重点

1. **Session 存服务器，靠 Cookie 传 JSESSIONID 认人**：数据安全，浏览器只拿 ID。
2. **`getSession()` 创建，`getSession(false)` 只取不创建**：登录判断用 false。
3. **Session 域范围是整个会话**：跨多次请求共享，比 request 域大。
4. **超时是"空闲超时"**：30 分钟没访问才销毁，每次访问重置计时。
5. **关浏览器只丢 JSESSIONID，不销毁服务器 Session**：服务器 Session 等超时才回收。
6. **`invalidate()` 手动销毁**：注销登录用它，清空所有数据。
7. **Session 依赖 Cookie**：禁用 Cookie 默认失效，URL 重写可救但不推荐。
8. **分布式下 Session 要共享**：多机部署需 Redis 存 Session，这是 Spring Session 的用途。

---

## 💻 实战案例：完整的登录注销流程

需求：登录存 Session，首页鉴权，注销销毁 Session。

```java
@WebServlet("/login")
public class LoginServlet extends HttpServlet {
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        req.setCharacterEncoding("utf-8");
        String username = req.getParameter("username");
        String password = req.getParameter("password");
        resp.setContentType("text/html;charset=utf-8");

        if ("admin".equals(username) && "123456".equals(password)) {
            HttpSession session = req.getSession();
            session.setAttribute("user", username);
            session.setMaxInactiveInterval(60 * 30);   // 30 分钟超时
            resp.sendRedirect("/home");
        } else {
            resp.getWriter().write("登录失败，<a href='/login.html'>重试</a>");
        }
    }
}

@WebServlet("/home")
public class HomeServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("text/html;charset=utf-8");
        HttpSession session = req.getSession(false);   // 只取不创建
        if (session == null || session.getAttribute("user") == null) {
            resp.sendRedirect("/login.html");
            return;
        }
        String user = (String) session.getAttribute("user");
        resp.getWriter().write(
            "<h1>欢迎 " + user + "</h1>" +
            "<a href='/logout'>注销</a>"
        );
    }
}

@WebServlet("/logout")
public class LogoutServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        HttpSession session = req.getSession(false);
        if (session != null) {
            session.invalidate();   // 销毁 Session
        }
        resp.sendRedirect("/login.html");
    }
}
```

> 💡 **这就是 Spring Security 登录注销的底层**：`/login` 存 Session、`/home` 鉴权、`/logout` 销毁 Session——Spring Security 把这套流程封装成 `formLogin()`/`logout()` 配置。但底层 Session 的创建、存取、销毁机制完全一样。

---

## 🚀 新版本补充

- **Servlet 3.1+**：Session 可配置为非持久化（`<distributable/>`），支持集群同步。
- **Spring Session**：用 `HttpSession` 的替代实现，底层存 Redis，解决分布式会话。Spring Boot 一行依赖 + 配置即启用。
- **JWT（JSON Web Token）**：无状态方案，Token 存客户端，服务器不存 Session，适合微服务/跨域。

---

## 📌 在 Spring Boot 中

> 本篇讲的 Session 创建读取、超时、销毁、JSESSIONID，在 Spring Boot 中仍可用 `HttpSession`，但分布式场景要用 Spring Session + Redis。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 Session 原理排查"。实际开发登录态多用 Session 或 JWT，理解了本篇的 JSESSIONID、超时、单机 vs 分布式，才能选对方案、定位问题。

### 1. Session 基本用法：从"req.getSession"到"直接注入 HttpSession"

**原生**：`req.getSession()` 创建、`setAttribute` 存、`getAttribute` 取（本篇 2.2 节）。
**Spring Boot**：Controller 直接注入 `HttpSession`，API 完全一样。

```java
@RestController
public class CartController {

    @PostMapping("/cart/add")
    public String addToCart(@RequestParam Long productId, HttpSession session) {
        // HttpSession 由 Spring 自动注入，底层就是 req.getSession()
        List<Long> cart = (List<Long>) session.getAttribute("cart");
        if (cart == null) {
            cart = new ArrayList<>();
            session.setAttribute("cart", cart);
        }
        cart.add(productId);
        return "购物车有 " + cart.size() + " 件商品";
    }

    @GetMapping("/cart")
    public List<Long> cart(HttpSession session) {
        List<Long> cart = (List<Long>) session.getAttribute("cart");
        return cart != null ? cart : Collections.emptyList();
    }
}
```

> 💡 **原理对应**：`HttpSession` 底层就是 `req.getSession()`，`setAttribute`/`getAttribute` 完全一样。**本篇讲的所有 Session API，在 Spring Boot 里原样可用**——Spring 没有重新发明 Session，只是让你不用手动 `getSession()`。

> 💡 **原理排查**：Session 取到 null？检查是否调了 `getSession(false)`（不创建）、Session 是否超时、JSESSIONID Cookie 是否被禁用。回到本篇原理：Session 靠 JSESSIONID 认人，ID 丢了就找不到 Session。

### 2. 登录鉴权：从"手写 Session 判断"到"Spring Security"

**原生**：本篇实战案例手写 `getSession(false)` + `getAttribute("user")` 判断登录（本篇 2.3 节）。
**Spring Boot**：Spring Security 全自动管理登录态。

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/login", "/css/**").permitAll()  // 放行登录页和静态资源
                .anyRequest().authenticated())                      // 其他需登录
            .formLogin(form -> form
                .loginPage("/login")
                .defaultSuccessUrl("/home", true)
                .permitAll())
            .logout(logout -> logout
                .logoutUrl("/logout")
                .logoutSuccessUrl("/login")
                .invalidateHttpSession(true)   // ★ 注销时销毁 Session（对应 invalidate()）
                .deleteCookies("JSESSIONID")); // 同时删 JSESSIONID Cookie
        return http.build();
    }
}
```

> 💡 **原理对应**：Spring Security 的登录流程就是本篇实战案例的工程化——`UsernamePasswordAuthenticationFilter` 处理登录、`SecurityContext` 存登录态（底层用 Session）、`LogoutFilter` 注销时 `invalidateHttpSession`。**你手写的 `getSession`/`setAttribute`/`invalidate`，Spring Security 全部封装了**。

> 💡 **原理排查**：登录后访问受保护页面仍跳登录？检查 Session 是否生效、`SecurityContext` 是否存进去、Session 超时是否太短。回到本篇原理：Session 靠 JSESSIONID 认人，登录态存在 Session 域，ID 或 Session 任一丢失就鉴权失败。

### 3. 超时配置：从"setMaxInactiveInterval / web.xml"到"application.yml"

**原生**：`session.setMaxInactiveInterval(1800)` 或 `web.xml` 的 `<session-timeout>30</session-timeout>`（本篇 4.2 节）。
**Spring Boot**：`application.yml` 一行配置。

```yaml
server:
  servlet:
    session:
      timeout: 30m          # 30 分钟超时（对应 setMaxInactiveInterval）
      cookie:
        name: JSESSIONID   # Cookie 名（可改）
        http-only: true     # 防 XSS
        secure: false       # 生产环境配 true（仅 HTTPS）
```

> 💡 **原理对应**：`server.servlet.session.timeout` 底层就是 `setMaxInactiveInterval`。本篇 4.2 节强调的"超时是空闲超时，每次访问重置计时"，Spring Boot 完全一样——30 分钟没访问才销毁。

> 💡 **原理排查**：用户频繁被踢下线？检查 `timeout` 是否太短、是否有请求没带 JSESSIONID（导致服务器以为是新会话）。回到本篇原理：超时是空闲计时，每次有效请求重置。

### 4. 分布式会话：从"单机 Session 失效"到"Spring Session + Redis"⭐

这是本篇最重要的实战场景。**单机 Session 存内存，多台服务器时用户请求打到不同机器，Session 找不到**——本篇第六节讲的分布式难题。Spring Boot 用 Spring Session + Redis 解决：

```xml
<!-- 引入 Spring Session + Redis -->
<dependency>
    <groupId>org.springframework.session</groupId>
    <artifactId>spring-session-data-redis</artifactId>
</dependency>
```

```yaml
spring:
  redis:
    host: 192.168.1.100
    port: 6379
  session:
    store-type: redis          # Session 存 Redis，多机共享
    timeout: 30m
```

```java
@SpringBootApplication
@EnableRedisHttpSession        // ★ 开启 Redis 共享 Session
public class App {
    public static void main(String[] args) {
        SpringApplication.run(App.class, args);
    }
}
```

启用后，**代码完全不用改**——`HttpSession` 的 `setAttribute`/`getAttribute` 照常用，底层自动存到 Redis：

```
单机：Session 存 Tomcat 内存 → 多机不共享
Redis：Session 存 Redis → 所有机器共享，用户请求打到哪台都认得出
```

> 💡 **原理对应**：Spring Session 用一个**装饰器**替换了原生 `HttpSession`，`setAttribute` 时自动序列化存 Redis，`getAttribute` 时从 Redis 取。**JSESSIONID 仍通过 Cookie 传**（本篇第三章讲的机制不变），只是数据从"服务器内存"换成了"Redis"。理解了本篇的 JSESSIONID 认人原理，Spring Session 就是"把存储从内存换 Redis"的升级。

> 💡 **原理排查**：多机部署登录态丢失？检查是否加了 `@EnableRedisHttpSession`、Redis 连通性、Session 序列化配置（对象需 `Serializable`）。回到本篇原理：分布式下 Session 必须共享，否则用户打到不同机器就找不到 Session。

### 5. 无状态方案：JWT（替代 Session）

前后端分离、微服务场景，常用 JWT 替代 Session——Token 存客户端，服务器不存状态：

```java
@RestController
public class AuthController {

    @PostMapping("/login")
    public String login(@RequestParam String username, @RequestParam String password) {
        if (authService.login(username, password)) {
            // 登录成功，签发 JWT（不存 Session）
            return jwtService.generateToken(username);
        }
        throw new RuntimeException("登录失败");
    }

    @GetMapping("/profile")
    public String profile(@RequestHeader("Authorization") String token) {
        // 每次请求带 Token，服务器解析验证（不查 Session）
        return jwtService.validate(token).getSubject();
    }
}
```

> 💡 **Session vs JWT 选型**：
> - **传统 Web 应用**（有页面、同域）→ Session（Spring Security formLogin）
> - **前后端分离 / 跨域 / 微服务** → JWT（无状态、易扩展）
> - **分布式传统应用** → Spring Session + Redis（Session 共享）
>
> 理解了本篇 Session 的"数据存服务器、靠 ID 认人"原理，才能理解 JWT 为什么"数据存 Token、服务器不存状态"——它把状态从服务器搬到 Token，省了 Session 存储和共享的麻烦。

### 6. Session 的线程安全

> ⚠️ **Session 不是线程安全的**：同一用户的多个请求（如 AJAX 并发）可能同时操作同一 Session。本篇强调的"Servlet 单例非线程安全"对 Session 域同样适用——**不要依赖 Session 的瞬时读写一致性**，关键操作加锁或用数据库。

---

> 一句话：**Session 是服务器端会话方案，解决了 Cookie 不安全的问题**。Spring Boot 里你仍能用 `HttpSession`，但分布式部署时单机 Session 不够用——Spring Session + Redis 把 Session 存到 Redis，多机共享，代码不用改。理解了本篇的 JSESSIONID、超时、销毁、分布式共享原理，Spring Session 的"内存换 Redis"升级对你就是顺理成章。**出登录态丢失、频繁掉线、多机不共享问题时，你仍要回到本篇原理排查**：JSESSIONID 带了吗、超时配多长、分布式是否共享了。

## 本章小结

本篇讲清了 Session：数据存服务器端，靠 Cookie 传 JSESSIONID 认领客户端。重点掌握 `getSession()`/`getSession(false)` 的区别、Session 域的会话级作用范围、超时是"空闲超时"、`invalidate()` 手动销毁、关浏览器只丢 ID 不销毁服务器 Session、Session 依赖 Cookie 及分布式共享难题。至此阶段三完成，Cookie 和 Session 这对会话管理方案你已掌握。下一篇 [08-Filter 过滤器](08-Filter%20过滤器.md) 进入三大组件——Filter、Listener、ServletContext，理解 Spring Security 的过滤链底层。
