# Filter 过滤器

前面七篇你学了请求、响应、会话。但有个需求没解决：每个 Servlet 都要自己判登录、自己处理乱码——能不能在请求到达 Servlet **之前**统一处理？这就是 **Filter**（过滤器）。它像一道关卡，所有请求先过它再进 Servlet，响应出来再过它。本篇讲清 Filter 的接口、生命周期、过滤器链、注解配置，以及统一编码/登录鉴权/敏感词过滤三大实战。这是 Spring Security 过滤链的底层。

> 💡 本篇建议写一个 Filter，在 `doFilter` 里打断点，观察"请求 → Filter → Servlet → Filter → 响应"的执行顺序，亲眼看到过滤器链的拦截过程。

---

## 一、Filter 是什么

### 1.1 定义

**Filter** 是 Servlet 规范的接口（`javax.servlet`），它拦截请求和响应，在目标 Servlet 执行**前后**插入通用逻辑。

```
浏览器 ──请求──▶ Filter1 ──▶ Filter2 ──▶ Servlet（处理）
浏览器 ◀──响应── Filter1 ◀── Filter2 ◀── Servlet（处理）
```

Filter 的典型用途：
- **统一编码**：所有请求设 UTF-8，不用每个 Servlet 写
- **登录鉴权**：未登录的请求拦截跳登录页
- **日志记录**：记录每个请求的访问信息
- **敏感词过滤**：替换请求参数里的敏感词
- **CORS 处理**：跨域响应头统一加

> 💡 **Filter vs Servlet**：Servlet 处理业务，Filter 处理"所有业务都要做的事"。Filter 是横切逻辑（cross-cutting concern），这正是 AOP（面向切面编程）的雏形——Spring AOP 的 `@Aspect` 思想源于此。

---

## 二、Filter 接口与生命周期

### 2.1 Filter 接口

`javax.servlet.Filter` 接口有三个方法，对应三个生命周期阶段：

| 方法 | 调用时机 | 作用 |
| :--- | :--- | :--- |
| `init(FilterConfig)` | **只调一次**，Filter 创建时 | 初始化 |
| `doFilter(req, resp, chain)` | **每次请求**都调 | 拦截处理（核心） |
| `destroy()` | **只调一次**，Filter 销毁时 | 释放资源 |

### 2.2 doFilter 的核心：放行

```java
@WebFilter("/*")   // 拦截所有请求
public class MyFilter implements Filter {
    @Override
    public void init(FilterConfig filterConfig) { }

    @Override
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        System.out.println("请求到达，Servlet 执行前");

        // ★ 放行：让请求继续到下一个 Filter 或 Servlet
        chain.doFilter(req, resp);

        System.out.println("Servlet 执行完，响应返回前");
    }

    @Override
    public void destroy() { }
}
```

> ⚠️ **`chain.doFilter()` 是放行的关键**：不调它，请求就被"卡住"，永远到不了 Servlet。Filter 的拦截能力就来自"调不调 doFilter"——不调即拒绝，调即放行。

> 💡 **doFilter 前后的代码**：`chain.doFilter()` 之前的代码在 Servlet 执行**前**运行（处理请求），之后的代码在 Servlet 执行**后**运行（处理响应）。这就是 Filter 能"前后夹击"的原理。

### 2.3 生命周期

和 Servlet 类似，Filter 也是单例，由 Tomcat 创建管理：

```
Tomcat 启动 → 创建 Filter 实例 → init()（一次）
         → 每次请求 → doFilter()（多次）
Tomcat 关闭 → destroy()（一次）
```

> ⚠️ **Filter 是单例**：和 Servlet 一样，不要用实例变量存请求状态，会有线程安全问题。

---

## 三、Filter 的配置

### 3.1 注解配置（推荐）

```java
@WebFilter("/*")                              // 拦截所有
@WebFilter("/user/*")                          // 拦截 /user 下
@WebFilter(urlPatterns = "/*",                 // 路径
           initParams = @WebInitParam(name="encoding", value="utf-8"))  // 初始化参数
public class MyFilter implements Filter { }
```

> 💡 **`@WebFilter` 的路径规则**和 Servlet 的 url-pattern 一样：精确、路径、扩展名、默认。`/*` 拦截所有请求。

### 3.2 web.xml 配置（了解）

```xml
<filter>
    <filter-name>encodingFilter</filter-name>
    <filter-class>com.example.EncodingFilter</filter-class>
</filter>
<filter-mapping>
    <filter-name>encodingFilter</filter-name>
    <url-pattern>/*</url-pattern>
</filter-mapping>
```

本系列默认用注解，不写 web.xml。

---

## 四、过滤器链 ⭐

多个 Filter 组成**过滤器链**，按顺序依次执行。请求时按顺序进，响应时逆序出：

```
请求 →  Filter1.doFilter(前)  →  Filter2.doFilter(前)  →  Servlet
响应 ←  Filter1.doFilter(后)  ←  Filter2.doFilter(后)  ←  Servlet
```

### 4.1 执行顺序

```java
@WebFilter("/*")
class FilterA implements Filter {
    public void doFilter(req, resp, chain) {
        System.out.println("A 前");
        chain.doFilter(req, resp);
        System.out.println("A 后");
    }
}
@WebFilter("/*")
class FilterB implements Filter {
    public void doFilter(req, resp, chain) {
        System.out.println("B 前");
        chain.doFilter(req, resp);
        System.out.println("B 后");
    }
}
```

输出顺序：`A 前 → B 前 → Servlet → B 后 → A 后`。

> 💡 **像洋葱模型**：请求从外到内（A→B→Servlet），响应从内到外（Servlet→B→A）。这就是过滤器链的"洋葱"结构，和 Spring AOP 的环绕通知一模一样。

### 4.2 执行顺序的确定

- **注解配置**：顺序**不确定**（按类名字母序，但规范未强制）。要控制顺序得用 web.xml 的 `<filter-mapping>` 顺序。
- **web.xml**：按 `<filter-mapping>` 的声明顺序执行。

> ⚠️ **注解 Filter 顺序不可靠**：多个 `@WebFilter` 的执行顺序由容器决定（通常按类名），不保证业务期望顺序。**需要严格顺序时用 web.xml 或 Spring Boot 的 `FilterRegistrationBean`**。

---

## 五、实战一：统一编码过滤器

每个 Servlet 都写 `setCharacterEncoding` 太烦，用 Filter 统一处理：

```java
@WebFilter("/*")
public class EncodingFilter implements Filter {
    private String encoding;

    @Override
    public void init(FilterConfig config) {
        // 读初始化参数
        encoding = config.getInitParameter("encoding");
        if (encoding == null) encoding = "utf-8";   // 默认
    }

    @Override
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        // 请求和响应统一编码
        req.setCharacterEncoding(encoding);
        resp.setCharacterEncoding(encoding);

        chain.doFilter(req, resp);   // 放行
    }
}
```

> 💡 **这就是 Spring Boot 的 `CharacterEncodingFilter`**：Spring Boot 默认配了一个编码过滤器，所以你不用手动处理乱码。底层就是上面这段逻辑。

---

## 六、实战二：登录鉴权过滤器

未登录的请求拦截跳登录页，已登录的放行：

```java
@WebFilter("/*")
public class AuthFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) req;
        HttpServletResponse response = (HttpServletResponse) resp;

        // 放行登录相关路径（否则死循环）
        String uri = request.getRequestURI();
        if (uri.contains("/login") || uri.contains(".html")
                || uri.contains(".css") || uri.contains(".js")) {
            chain.doFilter(req, resp);
            return;
        }

        // 检查 Session 是否登录
        HttpSession session = request.getSession(false);
        if (session == null || session.getAttribute("user") == null) {
            response.sendRedirect("/login.html");   // 未登录跳登录页
            return;   // ★ 不调 chain.doFilter，请求到此为止
        }

        chain.doFilter(req, resp);   // 已登录放行
    }
}
```

> ⚠️ **放行名单很重要**：登录页、静态资源必须放行，否则用户没登录时连登录页都打不开——请求被 Filter 拦截跳登录页，登录页又被拦截……死循环。

> 💡 **这就是 Spring Security 的底层**：Spring Security 本质就是一条 Filter 链（`FilterChainProxy`），`UsernamePasswordAuthenticationFilter` 处理登录、`FilterSecurityInterceptor` 做鉴权。你手写的这个 AuthFilter，就是 Spring Security 过滤链里某一环的简化版。

---

## 七、实战三：敏感词过滤

替换请求参数里的敏感词：

```java
@WebFilter("/*")
public class SensitiveFilter implements Filter {
    private List<String> words = Arrays.asList("坏话", "脏话");

    @Override
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        // 用包装器增强 Request（替换参数里的敏感词）
        HttpServletRequestWrapper wrapper = new HttpServletRequestWrapper((HttpServletRequest) req) {
            @Override
            public String getParameter(String name) {
                String value = super.getParameter(name);
                if (value != null) {
                    for (String w : words) value = value.replace(w, "***");
                }
                return value;
            }
        };
        chain.doFilter(wrapper, resp);   // 传增强后的 Request 给 Servlet
    }
}
```

> 💡 **`HttpServletRequestWrapper` 是装饰器模式**：它包装原 Request，重写 `getParameter` 方法替换敏感词，Servlet 拿到的就是过滤后的值。这是 Filter 增强 Request 的标准手法。

---

## ⚠️ 重点

1. **Filter 拦截请求和响应**：在 Servlet 前后插入通用逻辑，是横切逻辑（AOP 雏形）。
2. **`chain.doFilter()` 是放行开关**：不调即拒绝，调即放行；前后代码分别处理请求和响应。
3. **Filter 是单例**：不要用实例变量存请求状态。
4. **过滤器链是洋葱模型**：请求顺序进（A→B→Servlet），响应逆序出（Servlet→B→A）。
5. **注解 Filter 顺序不可靠**：需严格顺序用 web.xml 或 `FilterRegistrationBean`。
6. **放行名单要全**：登录鉴权 Filter 必须放行登录页和静态资源，否则死循环。
7. **`HttpServletRequestWrapper` 增强 Request**：装饰器模式，修改参数/头的标准手法。

---

## 💻 实战案例：组合多个 Filter

需求：编码 + 鉴权 + 日志三个 Filter 协同工作。

```java
// 1. 编码 Filter
@WebFilter(urlPatterns = "/*")
public class EncodingFilter implements Filter {
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        req.setCharacterEncoding("utf-8");
        resp.setCharacterEncoding("utf-8");
        chain.doFilter(req, resp);
    }
}

// 2. 日志 Filter
@WebFilter(urlPatterns = "/*")
public class LogFilter implements Filter {
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) req;
        long start = System.currentTimeMillis();
        System.out.println("[LOG] 请求开始: " + request.getRequestURI());

        chain.doFilter(req, resp);

        System.out.println("[LOG] 请求结束: " + request.getRequestURI()
                + " 耗时 " + (System.currentTimeMillis() - start) + "ms");
    }
}

// 3. 鉴权 Filter（放行登录相关，其他需登录）
@WebFilter(urlPatterns = "/*")
public class AuthFilter implements Filter {
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) req;
        String uri = request.getRequestURI();
        if (uri.contains("/login") || uri.contains(".")) {
            chain.doFilter(req, resp); return;
        }
        if (request.getSession(false) == null
                || request.getSession().getAttribute("user") == null) {
            ((HttpServletResponse) resp).sendRedirect("/login.html");
            return;
        }
        chain.doFilter(req, resp);
    }
}
```

> 💡 **这就是 Spring Boot 的 Filter 链**：Spring Boot 用 `FilterRegistrationBean` 注册 Filter 并控制顺序，Spring Security 更是用一条长达十几环的 Filter 链做认证授权。你手写的这三个 Filter，就是 Spring Security Filter 链的微缩版。

---

## 🚀 新版本补充

- **Servlet 3.0+**：`@WebFilter` 注解配置，可省 web.xml。
- **异步 Filter**：`AsyncListener` 支持异步请求的过滤。
- **Spring Boot**：`FilterRegistrationBean` 注册 Filter，可精确控制顺序和匹配规则。

---

## 📌 在 Spring Boot 中

> 本篇讲的 Filter 接口、过滤器链、`chain.doFilter` 放行、`HttpServletRequestWrapper` 增强，在 Spring Boot 中用 `FilterRegistrationBean` 注册、用 Spring Security 管理过滤链。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 Filter 原理排查"。实际开发你很少手写 Filter——编码/日志框架自动配、鉴权用 Spring Security，但理解了本篇，过滤链、AOP、Spring Security 的底层对你就是透明的。

### 1. 注册 Filter：从"@WebFilter"到"FilterRegistrationBean"

**原生**：`@WebFilter("/*")` 注解配置，但**顺序不可靠**（本篇 4.2 节）。
**Spring Boot**：`FilterRegistrationBean` 注册，可精确控制顺序和匹配规则。

```java
@Configuration
public class FilterConfig {

    @Bean
    public FilterRegistrationBean<LogFilter> logFilter() {
        FilterRegistrationBean<LogFilter> reg = new FilterRegistrationBean<>();
        reg.setFilter(new LogFilter());
        reg.addUrlPatterns("/*");          // 拦截路径
        reg.setOrder(1);                   // ★ 顺序：数字越小越先执行
        reg.setName("logFilter");
        return reg;
    }

    @Bean
    public FilterRegistrationBean<AuthFilter> authFilter() {
        FilterRegistrationBean<AuthFilter> reg = new FilterRegistrationBean<>();
        reg.setFilter(new AuthFilter());
        reg.addUrlPatterns("/api/*");
        reg.setOrder(2);                   // 在 LogFilter 之后执行
        return reg;
    }
}
```

> 💡 **原理对应**：`FilterRegistrationBean` 底层就是注册一个 Filter 到 Servlet 容器，和 `@WebFilter` 本质一样。优势是 `setOrder()` 精确控制顺序——**本篇 4.2 节强调的"注解 Filter 顺序不可靠"，Spring Boot 用 `setOrder` 解决了**。

> 💡 **原理排查**：Filter 没生效？检查 `FilterRegistrationBean` 是否注册成 Bean、`addUrlPatterns` 是否匹配请求路径、`@ServletComponentScan` 是否开启（用 `@WebFilter` 时需要）。回到本篇原理：Filter 要被容器加载才生效。

### 2. 过滤器链顺序：从"不可靠"到"setOrder 精确控制"

**原生**：多个 `@WebFilter` 顺序由容器决定（通常按类名），不保证业务期望。
**Spring Boot**：`setOrder(1)` / `setOrder(2)` 精确控制，数字小先执行。

```
请求 → LogFilter(order=1) → AuthFilter(order=2) → Controller
响应 ← LogFilter(order=1) ← AuthFilter(order=2) ← Controller
```

> 💡 **原理对应**：本篇第四节讲的"洋葱模型"（请求顺序进、响应逆序出）完全一样，只是顺序从"不可靠"变成"可控"。**Spring AOP 的 `@Around` 环绕通知也是这个洋葱模型**——`@Order` 决定切面顺序，和 Filter 的 `setOrder` 同构。

> 💡 **原理排查**：鉴权 Filter 在日志 Filter 之前执行了，导致未登录请求没记日志？调整 `setOrder`，让日志 Filter order 更小（先执行）。回到本篇原理：过滤器链顺序决定谁先拦截。

### 3. 编码 Filter：从"手写 EncodingFilter"到"CharacterEncodingFilter 自动配置"

**原生**：本篇第五节手写 `EncodingFilter`，每个 Servlet 不用再写 `setCharacterEncoding`。
**Spring Boot**：内置 `CharacterEncodingFilter`，默认开启 UTF-8，无需手写。

```yaml
server:
  servlet:
    encoding:
      charset: UTF-8       # 默认 UTF-8
      force: true          # 强制请求和响应都用 UTF-8
```

> 💡 **原理对应**：Spring Boot 的 `CharacterEncodingFilter` 就是本篇第五节那个 `EncodingFilter` 的官方版——在请求到达 Controller 前统一调 `setCharacterEncoding("utf-8")`。**你手写的编码 Filter，Spring Boot 默认就配好了**。

> 💡 **原理排查**：仍有乱码？检查 `force: true`、前端 `Content-Type` 是否带 `charset`、是否是 GET 参数乱码（Tomcat URI 编码）。回到本篇原理：编码 Filter 处理的是请求体，GET 参数看 Tomcat 的 URIEncoding。

### 4. 鉴权 Filter：从"手写 AuthFilter"到"Spring Security 过滤链"

**原生**：本篇第六节手写 `AuthFilter`，放行名单 + `getSession(false)` 判断。
**Spring Boot**：Spring Security 提供完整的过滤链，不用手写。

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/login", "/css/**", "/js/**").permitAll()  // 放行名单
                .requestMatchers("/admin/**").hasRole("ADMIN")                // 角色鉴权
                .anyRequest().authenticated())                                  // 其他需登录
            .formLogin(form -> form.loginPage("/login").permitAll())
            .csrf(csrf -> csrf.disable());  // 按需关闭 CSRF
        return http.build();
    }
}
```

> 💡 **原理对应**：Spring Security 本质就是一条 **Filter 链**（`FilterChainProxy`），里面有 `SecurityContextPersistenceFilter`（从 Session 取登录态）、`UsernamePasswordAuthenticationFilter`（处理登录）、`FilterSecurityInterceptor`（鉴权）等十几个 Filter。**你手写的 `AuthFilter`，就是这条链里某一环的简化版**——本篇第六节的"放行名单 + Session 判断"逻辑，Spring Security 用配置表达。

> 💡 **原理排查**：接口 403 Forbidden？检查 `hasRole` 配置、用户角色、`requestMatchers` 路径。401 Unauthorized？检查是否登录、Session 是否有效。回到本篇原理：鉴权 Filter 的"放行/拒绝"逻辑，Spring Security 用配置化表达。

### 5. 日志/性能 Filter：从"手写 LogFilter"到"Spring AOP / Actuator"

**原生**：本篇实战案例手写 `LogFilter`，记录请求耗时。
**Spring Boot**：用 AOP 切面或 Actuator 监控，更优雅。

```java
// 用 AOP 环绕通知记录接口耗时（等价 Filter 的前后夹击）
@Aspect
@Component
public class LogAspect {
    @Around("execution(* com.example.controller..*.*(..))")
    public Object log(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        String method = pjp.getSignature().toShortString();
        Object result = pjp.proceed();   // 等价 chain.doFilter() 放行
        System.out.println("[LOG] " + method + " 耗时 "
                + (System.currentTimeMillis() - start) + "ms");
        return result;
    }
}
```

> 💡 **原理对应**：AOP 的 `@Around` 环绕通知和 Filter 的 `doFilter` 前后夹击**完全同构**——`pjp.proceed()` 等价 `chain.doFilter()`，都是"放行+前后处理"。**本篇讲的洋葱模型，AOP 也是这个模型**。区别是 Filter 拦截所有请求，AOP 可按方法签名精确拦截。

> 💡 **选型**：Web 请求层（编码、跨域、鉴权）用 Filter；业务层（日志、事务、缓存）用 AOP。两者都是"横切逻辑"，只是作用层不同。

### 6. 增强 Request：从"HttpServletRequestWrapper"到"ContentCachingRequestWrapper"

**原生**：本篇第七节用 `HttpServletRequestWrapper` 装饰器增强 Request（如敏感词替换）。
**Spring Boot**：同样用 Wrapper，如内置的 `ContentCachingRequestWrapper` 缓存请求体（解决"body 只能读一次"问题）。

```java
@Component
public class MyFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse resp, FilterChain chain)
            throws IOException, ServletException {
        // 用 ContentCachingRequestWrapper 包装，让 body 可重复读
        ContentCachingRequestWrapper wrapper =
                new ContentCachingRequestWrapper((HttpServletRequest) req);
        chain.doFilter(wrapper, resp);
        // 请求后可重复读 body（原生 getReader 只能读一次）
        byte[] buf = wrapper.getContentAsByteArray();
    }
}
```

> 💡 **原理对应**：`ContentCachingRequestWrapper` 就是本篇第七节 `HttpServletRequestWrapper` 的官方应用——**装饰器模式增强 Request**，解决本篇 04 篇强调的"请求体只能读一次"问题。理解了本篇的装饰器原理，Spring 的各种 Wrapper 就不神秘。

### 7. 跨域 Filter：从"手动设响应头"到"CorsFilter / 全局配置"

**原生**：跨域需手动设 `Access-Control-Allow-Origin` 等响应头（03 篇讲过）。
**Spring Boot**：`CorsFilter` 或全局配置（03 篇 Spring Boot 小节已展示），本质就是一个 Filter。

> 💡 **原理对应**：`CorsFilter` 底层就是设 CORS 响应头的 Filter。**本篇学的 Filter 机制，是所有"在请求前后统一处理"功能的基础**——编码、跨域、鉴权、日志，都是 Filter。

---

> 一句话：**Filter 是 Web 层的横切逻辑容器**。Spring Boot 里你很少手写 Filter——编码自动配、鉴权用 Spring Security、日志用 AOP。但 Spring Security 的整条过滤链本质就是 Filter，Spring AOP 的环绕通知和过滤器链同构，`FilterRegistrationBean` 让顺序可控。理解了本篇的 `chain.doFilter` 放行、洋葱模型、Wrapper 增强，Spring Security 和 AOP 的底层对你就是透明的。**出 Filter 不生效、顺序不对、鉴权失败问题时，你仍要回到本篇原理排查**：注册了吗、order 对吗、放行名单全吗、chain.doFilter 调了吗。

## 本章小结

本篇讲清了 Filter：它拦截请求和响应，在 Servlet 前后插入通用逻辑（编码/鉴权/日志/敏感词）。重点掌握 Filter 接口三方法、`chain.doFilter` 放行机制、过滤器链洋葱模型、注解配置及顺序问题、`HttpServletRequestWrapper` 装饰器增强。核心认知：Filter 是横切逻辑，是 AOP 和 Spring Security 过滤链的底层。下一篇 [09-Listener 监听器](09-Listener%20监听器.md) 讲三大组件的最后一个——监听器，理解 Spring 的事件机制底层。
