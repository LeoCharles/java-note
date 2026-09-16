# 28 - Spring Boot 统一 Session 管理

> 对应项目模块：`demo-session`
> 前置知识：已学完前置模块，了解 `application.yml`、`@Controller`、Thymeleaf 模板引擎基本用法
> 学习目标：理解为什么单机 Session 在集群下会失效，掌握用 Spring Session + Redis 实现 Session 共享，理解拦截器做登录校验的套路。

---

## 一、本模块要解决什么问题？

### 1.1 先搞懂 Session 是什么

HTTP 是**无状态**协议——服务器处理完一个请求就忘了你是谁，下一个请求服务器不认识你了。为了"记住"用户登录状态，需要一种机制把多次请求关联起来，这就是 **Session（会话）**。

**Session 的工作流程：**

1. 用户第一次访问，服务器创建一个 Session 对象，分配一个唯一 `JSESSIONID`。
2. 服务器通过 `Set-Cookie` 响应头把 `JSESSIONID` 写进浏览器 Cookie。
3. 用户后续请求，浏览器自动带上这个 Cookie。
4. 服务器根据 `JSESSIONID` 找到对应的 Session 对象，从而"认出"用户。

> 💡 前端类比：Session 类似前端的 `sessionStorage`，但 Session 的数据存在**服务器**，浏览器只存一个 ID（Cookie）。可以理解为：服务器开了一个"储物柜"（Session），给你一把"钥匙"（JSESSIONID Cookie），下次你带钥匙来，服务器帮你取出对应的东西。

### 1.2 单机 Session 在集群下为什么会失效？

传统单机部署，Session 存在 Tomcat 内存里，没问题。但生产环境通常是**集群部署**（多台服务器 + 负载均衡）：

```
用户 ──> Nginx 负载均衡 ──> 服务器A（Session 存在这）
                          ──> 服务器B（Session 没存）
```

用户登录请求打到服务器 A，Session 存在 A 的内存。下一个请求被负载均衡分到服务器 B，B 的内存里没有这个 Session，用户就被"踢回"登录页。这就是**集群下 Session 失效**问题。

### 1.3 解决方案：Session 集中存储

把 Session 从"各服务器内存"搬到"集中存储"（通常是 Redis），所有服务器都去 Redis 读写 Session，这样无论请求打到哪台服务器，都能找到同一个 Session。

```
用户 ──> Nginx ──> 服务器A ──┐
              ──> 服务器B ──┼──> Redis（统一存 Session）
              ──> 服务器C ──┘
```

**Spring Session** 就是 Spring 提供的"把 Session 搬到外部存储"的方案，它对开发者透明——你依然用 `request.getSession()` 这套 API，但底层 Session 已经不在 Tomcat 内存，而在 Redis 里了。本模块演示的就是这个方案。

---

## 二、项目结构

```
demo-session/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/session/
    │   ├── SpringBootDemoSessionApplication.java   # 启动类
    │   ├── config/
    │   │   └── WebMvcConfig.java                  # Web 配置：注册拦截器
    │   ├── constants/
    │   │   └── Consts.java                        # 常量：Session key
    │   ├── controller/
    │   │   └── PageController.java                # 页面跳转控制器
    │   └── interceptor/
    │       └── SessionInterceptor.java            # 登录校验拦截器
    └── resources/
        ├── application.yml                         # 配置（Redis + Session）
        └── templates/
            ├── index.html                          # 首页（显示 token）
            └── login.html                          # 登录页
```

相比之前的模块，这里多了 `config`、`constants`、`interceptor` 三个包——这是典型的"登录鉴权"分层结构，后续做权限控制时这种结构会反复出现。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. Spring Session + Redis：核心依赖 -->
    <dependency>
        <groupId>org.springframework.session</groupId>
        <artifactId>spring-session-data-redis</artifactId>
    </dependency>

    <!-- 3. Redis 起步依赖：提供 Redis 连接 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>

    <!-- 4. 对象池，使用 redis 时必须引入 -->
    <dependency>
        <groupId>org.apache.commons</groupId>
        <artifactId>commons-pool2</artifactId>
    </dependency>

    <!-- 5. Thymeleaf：渲染登录页和首页 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-thymeleaf</artifactId>
    </dependency>

    <!-- 6. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 7. Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
</dependencies>
```

**关键依赖说明：**

| 依赖 | 作用 |
| --- | --- |
| `spring-session-data-redis` | Spring Session 的 Redis 实现，自动把 `HttpSession` 替换成 Redis 版本 |
| `spring-boot-starter-data-redis` | 提供 Redis 连接（Lettuce 客户端），Spring Session 底层用它连 Redis |
| `commons-pool2` | Lettuce 连接池依赖，不引会报警告且无法用连接池 |

> 💡 注意 `spring-session-data-redis` 是关键——引入它后，Spring Boot 的自动配置会把 Servlet 容器原本的 `HttpSession` 替换成 `RedisSession`，你代码里 `request.getSession()` 拿到的已经是 Redis 版本了，**完全透明**，业务代码不用改。

---

## 四、逐行拆解配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo

spring:
  session:
    store-type: redis          # Session 存储类型：redis
    redis:
      flush-mode: immediate    # 刷新模式：立即写入 Redis
      namespace: "spring:session"  # Redis key 的命名空间前缀
  redis:
    host: localhost
    port: 6379
    timeout: 10000ms           # 连接超时时间（必须带单位）
    lettuce:
      pool:
        max-active: 8          # 连接池最大连接数
        max-wait: -1ms         # 最大阻塞等待时间（-1 表示不限制）
        max-idle: 8             # 最大空闲连接
        min-idle: 0             # 最小空闲连接
```

### 4.1 `spring.session` 配置项

| 配置项 | 作用 |
| --- | --- |
| `store-type: redis` | 指定 Session 存到 Redis。还有 `none`（不存，用容器默认）、`jdbc`（存数据库）等 |
| `flush-mode: immediate` | Session 变更立即同步到 Redis。还有 `on-save`（请求结束时统一同步） |
| `namespace: "spring:session"` | Redis 里 key 的前缀，所有 Session 相关 key 都以 `spring:session:` 开头，便于隔离和排查 |

### 4.2 `spring.redis` 配置项

这是 Redis 连接配置，Spring Session 底层用它连 Redis。`lettuce.pool` 是连接池参数——Lettuce 是 Spring Boot 2.x 默认的 Redis 客户端（基于 Netty，线程安全，性能好）。

> 💡 前端类比：`namespace` 类似 localStorage 的 key 前缀约定（如 `myapp:token`），避免不同应用的数据冲突。`flush-mode` 类似前端的"立即写入"vs"防抖批量写入"。

> ⚠️ `timeout: 10000ms` 必须带单位（`ms`/`s`），不带会报错。这是 Spring Boot 2.x 的 `Duration` 类型配置的强制要求。

---

## 五、启动类

```java
@SpringBootApplication
public class SpringBootDemoSessionApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoSessionApplication.class, args);
    }
}
```

启动类很简洁，**没有显式加 `@EnableRedisHttpSession`**。这是因为引入 `spring-session-data-redis` 后，Spring Boot 的 `SessionAutoConfiguration` 会自动配置，不需要手动开启。如果需要自定义过期时间等参数，可以加 `@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 1800)`。

---

## 六、常量类 Consts

```java
public interface Consts {
    /**
     * session保存的key
     */
    String SESSION_KEY = "key:session:token";
}
```

**为什么用 `interface` 而不是 `class`？** 因为 interface 里的字段默认是 `public static final`，省得手写这些修饰符。这是 Java 定义常量的常见技巧。

> 💡 前端类比：这就像前端的 `constants.ts` 导出一堆常量。把 Session key 统一管理，避免在多个地方硬编码字符串导致拼写不一致。

> ⚠️ 实际开发中更推荐用 `class` + `private` 构造函数（防止实例化）来定义常量，或用枚举。interface 定义常量虽然方便，但可以被"实现"导致常量泄漏到子类，是个反模式。这里只是 demo 简化写法。

---

## 七、页面控制器 PageController

```java
@Controller
@RequestMapping("/page")
public class PageController {

    @GetMapping("/index")
    public ModelAndView index(HttpServletRequest request) {
        ModelAndView mv = new ModelAndView();
        String token = (String) request.getSession().getAttribute(Consts.SESSION_KEY);
        mv.setViewName("index");
        mv.addObject("token", token);
        return mv;
    }

    @GetMapping("/login")
    public ModelAndView login(Boolean redirect) {
        ModelAndView mv = new ModelAndView();
        if (ObjectUtil.isNotNull(redirect) && ObjectUtil.equal(true, redirect)) {
            mv.addObject("message", "请先登录！");
        }
        mv.setViewName("login");
        return mv;
    }

    @GetMapping("/doLogin")
    public String doLogin(HttpSession session) {
        session.setAttribute(Consts.SESSION_KEY, IdUtil.fastUUID());
        return "redirect:/page/index";
    }
}
```

### 7.1 三个接口的职责

| 接口 | 作用 |
| --- | --- |
| `GET /page/index` | 首页：从 Session 取 token，传给页面显示 |
| `GET /page/login` | 登录页：带 `redirect=true` 参数时显示"请先登录"提示 |
| `GET /page/doLogin` | 模拟登录：往 Session 里塞一个随机 UUID 作为 token，重定向回首页 |

### 7.2 关键点：Session 操作

```java
// 读 Session
request.getSession().getAttribute(Consts.SESSION_KEY);

// 写 Session
session.setAttribute(Consts.SESSION_KEY, IdUtil.fastUUID());
```

注意：**这里用的还是标准 Servlet API**（`request.getSession()`、`session.setAttribute()`），但因为引入了 Spring Session，底层 `getSession()` 返回的已经是 `RedisSession`，`setAttribute` 会把数据写到 Redis。业务代码完全无感知——这就是 Spring Session 的"透明替换"。

> 💡 前端类比：这像前端的"适配器模式"——你调用的 API 长一样（`sessionStorage.getItem`），但底层存储换了（从内存换成 IndexedDB）。Spring Session 把 `HttpSession` 接口的实现从 Tomcat 内存版换成了 Redis 版。

### 7.3 `ModelAndView` 与重定向

- `ModelAndView`：同时承载视图名和数据，`setViewName("index")` 指定模板，`addObject("token", token)` 传数据给模板。
- `return "redirect:/page/index"`：返回 `redirect:` 前缀的字符串，Spring MVC 会发一个 302 重定向，浏览器跳转到 `/page/index`。

> 💡 前端类比：`redirect:` 类似前端 `window.location.href = '/page/index'`，是让浏览器发起新请求，而不是服务端内部转发。

---

## 八、登录校验拦截器 SessionInterceptor

```java
@Component
public class SessionInterceptor extends HandlerInterceptorAdapter {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        HttpSession session = request.getSession();
        if (session.getAttribute(Consts.SESSION_KEY) != null) {
            return true;   // 已登录，放行
        }
        // 未登录，跳转到登录页
        String url = "/page/login?redirect=true";
        response.sendRedirect(request.getContextPath() + url);
        return false;      // 拦截
    }
}
```

### 8.1 拦截器的工作原理

`HandlerInterceptorAdapter` 是 Spring MVC 提供的拦截器适配器，有三个回调时机：

| 方法 | 时机 | 用途 |
| --- | --- | --- |
| `preHandle` | Controller 方法执行**前** | 登录校验、权限检查，返回 false 则中断请求 |
| `postHandle` | Controller 方法执行**后**、视图渲染**前** | 修改 ModelAndView |
| `afterCompletion` | 视图渲染**后** | 资源清理 |

本模块只用 `preHandle`：检查 Session 里有没有 token，没有就重定向到登录页并返回 `false`（中断后续流程）。

> 💡 前端类比：拦截器非常像 Vue Router 的**全局前置守卫** `router.beforeEach((to, from, next) => { if (已登录) next(); else next('/login') })`。都是"在到达目标前先检查权限，不通过就跳转"。

### 8.2 `request.getContextPath()` 的作用

```java
response.sendRedirect(request.getContextPath() + url);
```

`getContextPath()` 返回应用上下文路径（本例是 `/demo`），拼出完整重定向地址 `/demo/page/login?redirect=true`。如果不拼 context-path，浏览器会跳到 `/page/login`，少了 `/demo` 前缀导致 404。

> ⚠️ 这是新手常踩的坑：配置了 `context-path` 后，所有重定向、静态资源路径都要带上它，否则路径对不上。

---

## 九、Web 配置类 WebMvcConfig

```java
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {
    @Autowired
    private SessionInterceptor sessionInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        InterceptorRegistration sessionInterceptorRegistry = registry.addInterceptor(sessionInterceptor);
        // 排除不需要拦截的路径
        sessionInterceptorRegistry.excludePathPatterns("/page/login");
        sessionInterceptorRegistry.excludePathPatterns("/page/doLogin");
        sessionInterceptorRegistry.excludePathPatterns("/error");

        // 需要拦截的路径
        sessionInterceptorRegistry.addPathPatterns("/**");
    }
}
```

### 9.1 `WebMvcConfigurer` 自定义 Spring MVC

实现 `WebMvcConfigurer` 并加 `@Configuration`，就能自定义 Spring MVC 的各种行为：拦截器、跨域、静态资源映射、参数解析器等。这是 Spring Boot 2.x 推荐的定制方式（不再用继承 `WebMvcConfigurationSupport` 的方式，那样会覆盖太多默认配置）。

### 9.2 拦截路径配置

```java
sessionInterceptorRegistry.addPathPatterns("/**");              // 拦截所有
sessionInterceptorRegistry.excludePathPatterns("/page/login");  // 排除登录页
sessionInterceptorRegistry.excludePathPatterns("/page/doLogin"); // 排除登录接口
sessionInterceptorRegistry.excludePathPatterns("/error");        // 排除错误页
```

逻辑很清晰：**拦截所有请求，但放行登录相关页面和错误页**。否则未登录用户连登录页都进不去（死循环：访问任何页面 → 未登录 → 跳登录页 → 登录页也被拦 → 跳登录页……）。

> 💡 前端类比：这像 Vue Router 守卫里的 `meta: { requiresAuth: true }` 标记 + 白名单。`excludePathPatterns` 就是白名单，`addPathPatterns("/**")` 就是"默认全部需要登录"。

> ⚠️ `excludePathPatterns` 的路径是相对于 context-path 的。本例 context-path 是 `/demo`，所以写 `/page/login` 而不是 `/demo/page/login`。

---

## 十、模板页面

### 10.1 登录页 login.html

```html
<!DOCTYPE html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
<head><meta charset="UTF-8"><title>spring-boot-demo-session</title></head>
<body>
<h1 th:text="${message}" style="background-color: red"></h1>
<button><a th:href="@{'/page/doLogin'}">登录</a></button>
</body>
</html>
```

- `th:text="${message}"`：把后端传来的 `message`（"请先登录！"）渲染到 `<h1>` 里。
- `th:href="@{'/page/doLogin'}"`：Thymeleaf 的链接表达式，会自动加上 context-path，生成 `/demo/page/doLogin`。

### 10.2 首页 index.html

```html
<body>
token的值: <h1 th:text="${token}"></h1>
</body>
```

显示从 Session 取出的 token，用于验证登录态。

---

## 十一、运行与验证

### 11.1 前置条件

需要先启动一个本地 Redis（默认端口 6379）。可以用 Docker：

```sh
docker run -d --name redis -p 6379:6379 redis
```

### 11.2 启动与测试流程

1. 启动应用：`mvn spring-boot:run`
2. 访问首页 `http://localhost:8080/demo/page/index` → 未登录，被拦截器重定向到登录页 `http://localhost:8080/demo/page/login?redirect=true`，显示红色"请先登录！"
3. 点击"登录"按钮 → 调用 `/page/doLogin`，往 Session 写入随机 UUID，重定向回首页
4. 首页显示 token 值 → 登录成功
5. **重启应用**，不关闭浏览器，刷新首页 → **仍然显示 token，不需要重新登录**！

### 11.3 验证 Session 在 Redis 里

重启应用后 Session 仍在，是因为 Session 存在 Redis 而不是应用内存。可以用 `redis-cli` 查看：

```sh
redis-cli
> keys spring:session:*
```

会看到类似 `spring:session:sessions:xxxx` 的 key，证明 Session 确实存在 Redis。

> 💡 这就是"重启程序 Session 不失效"的原理——Session 的生命周期和应用程序解耦了，只要 Redis 不重启，Session 就在。集群部署时，多台应用共享同一个 Redis，也就实现了 Session 共享。

---

## 十二、动手练习

1. **观察 Redis 里的 Session**：登录后用 `redis-cli` 执行 `keys spring:session:*`，找到 Session key，用 `type` 命令看它的数据类型（是 hash），用 `hgetall` 查看内容。
2. **手动删除 Session**：登录后，在 Redis 里删掉对应的 Session key（`del spring:session:sessions:xxx`），刷新首页，验证被踢回登录页——体会 Session 确实在 Redis。
3. **改 Session 过期时间**：在启动类加 `@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 60)`，登录后等 60 秒不操作，刷新页面，验证 Session 过期。
4. **模拟集群**：复制一份应用，改端口为 8081 启动（同一个 Redis），在 8080 登录后，访问 8081 的首页，验证 Session 共享（同一个 Redis，两台应用都能认出你）。
5. **加一个登出接口**：写一个 `/page/logout`，调用 `session.invalidate()` 销毁 Session，验证登出后访问首页被拦截。
6. **对比 Cookie**：用浏览器开发者工具查看 Cookie，观察 `JSESSIONID` 的值，理解它和 Redis 里 Session 的对应关系。

---

## 十三、本模块知识点总结（结合实际开发详解）

Session 管理是 Web 应用的核心基础设施，涉及登录态、集群部署、安全性。下面把核心知识点放到真实开发场景里讲透。

### 13.1 Session vs Cookie vs Token：三种会话方案怎么选？

**三种方案的对比：**

| 方案 | 存储位置 | 特点 | 适用场景 |
| --- | --- | --- | --- |
| Session（传统） | 服务器内存 | 简单，但集群需共享 | 单机或小型集群 |
| Session + Redis（Spring Session） | Redis | 集群友好，透明替换 | 传统前后端不分离、集群部署 |
| JWT Token | 客户端（Cookie/localStorage） | 无状态、易扩展、跨域友好 | 前后端分离、微服务、移动端 |

**实际开发怎么选？**

- **前后端不分离**（服务端渲染页面，如本模块）：用 Spring Session + Redis，配合拦截器，最自然。
- **前后端分离**（前端 SPA + 后端 API）：用 JWT Token 更合适。前端把 token 存 localStorage，每次请求带 `Authorization` 头，后端无状态校验。
- **微服务架构**：JWT + 网关统一鉴权，各服务无状态，水平扩展无障碍。

**常见坑：**

- 把 JWT 和 Session 混用，导致概念混乱。两者是不同的会话模型，选一个为主。
- 用了 Spring Session 还在前端存大量状态，没有真正利用服务端 Session。

> 💡 前端类比：Session 像后端开的"存包柜"（你拿钥匙/cookie 来取），JWT 像你自带"身份证"（token 自包含信息，后端只验签不存储）。前者后端有状态，后者无状态。

### 13.2 Spring Session 的透明替换原理

引入 `spring-session-data-redis` 后，为什么 `request.getSession()` 就自动变成 Redis 版本了？

**原理：** Spring Session 通过 `SessionRepositoryFilter` 这个 Servlet Filter，把原始的 `HttpServletRequest` 包装成 `SessionRepositoryRequestWrapper`，后者重写了 `getSession()` 方法，返回 `RedisSession`。整个调用链：

```
请求 → SessionRepositoryFilter（包装 request） → Controller 里 request.getSession() 返回 RedisSession
```

**实际开发的意义：**

- **业务代码零改动**：从单机 Session 迁移到 Redis Session，只需要加依赖 + 配置，Controller 代码不用改。
- **可扩展**：想换存储（如换成 Hazelcast、JDBC），换依赖和配置即可。

**常见坑：**

- 以为要手动写 Redis 读写代码来存 Session——不需要，Spring Session 全包了。
- Session 里存的对象必须**可序列化**（要实现 `Serializable`），因为要存进 Redis。存了不可序列化的对象会报错。

### 13.3 拦截器 vs Filter vs AOP：三种切面怎么选？

本模块用拦截器做登录校验，但 Spring 还有 Filter 和 AOP 也能做类似的事。三者的区别和选择：

| 机制 | 作用层 | 能拿到的信息 | 典型用途 |
| --- | --- | --- | --- |
| Filter | Servlet 容器层 | 原始 request/response | 编码转换、跨域、安全过滤 |
| Interceptor | Spring MVC 层 | 能拿到 Handler（Controller 方法） | 登录校验、权限检查 |
| AOP | 业务方法层 | 能拿到方法参数、返回值 | 日志、事务、缓存 |

**选择标准：**

- 需要在"路由到哪个 Controller 方法"之前做判断 → 用拦截器（能拿到 Handler）。
- 需要在请求进入 Spring 之前处理（如编码、CORS）→ 用 Filter。
- 需要围绕具体业务方法做切面（如日志、事务）→ 用 AOP。

**实际开发的登录校验：**

- 传统 Web 应用：拦截器（本模块做法）。
- 前后端分离 API：通常用 Filter（如 Spring Security 的 `JwtAuthenticationFilter`）或拦截器，配合自定义注解标记需要鉴权的接口。

**常见坑：**

- 拦截器里 `response.sendRedirect` 忘了拼 `context-path`，导致重定向到错误路径。
- 拦截器排除路径写错，把登录接口也拦了，造成死循环重定向。

### 13.4 Session 的过期与续期

**Session 过期机制：**

- 默认 30 分钟无操作过期（`maxInactiveIntervalInSeconds`）。
- Spring Session + Redis 底层用 Redis 的过期 key 机制实现。

**实际开发的坑：**

- **滑动续期**：用户一直在操作，但 Session 突然过期了？因为 Spring Session 默认的 `flush-mode` 和续期策略可能不及时更新过期时间。需要确认配置，或用 `on-save` 模式在请求结束时刷新。
- **强制下线**：管理员想踢掉某个用户，传统 Session 难做到（要遍历找 Session）。用 Redis 存 Session 后，可以直接删 Redis key 实现强制下线——这是集中存储的优势。

### 13.5 Session 安全：防劫持与 Cookie 加固

**Session 劫持风险：** 攻击者拿到 `JSESSIONID` 就能冒充用户。防护措施：

1. **HTTPS**：防止 Cookie 被中间人窃听（`demo-https` 模块会讲）。
2. **Cookie 加固标志**：
   - `HttpOnly`：禁止 JS 读取 Cookie，防 XSS 偷取。
   - `Secure`：只在 HTTPS 下传输。
   - `SameSite`：防 CSRF。
   
   配置方式（`application.yml` 或配置类）：
   ```yaml
   server:
     servlet:
       session:
         cookie:
           http-only: true
           secure: true
   ```
3. **登录后换发 Session ID**：防止"固定会话攻击"（攻击者预设 Session ID，等用户登录后复用）。Spring Security 默认做这个（`changeSessionId`）。

**常见坑：** 前后端分离用 Cookie 传 Session ID 时，跨域要配 `SameSite=None; Secure`，否则浏览器拒绝带 Cookie，导致登录态丢失。

### 13.6 集群 Session 的几种方案对比

除了 Spring Session + Redis，还有其他集群 Session 方案：

| 方案 | 原理 | 优缺点 |
| --- | --- | --- |
| **Session 不复制（无状态）** | 不用 Session，用 JWT | 最适合微服务，但注销难 |
| **Session 粘性（Sticky Session）** | 负载均衡把同一用户固定分到同一台 | 简单，但服务器宕机 Session 丢失 |
| **Session 复制（Tomcat 集群）** | 服务器间同步 Session | 浪费内存，扩展性差 |
| **Session 集中存储（Spring Session + Redis）** | 统一存 Redis | 集群友好，推荐 |

**实际开发的选择：**

- 新项目、前后端分离 → 直接 JWT，不引入 Session。
- 老项目改造、传统 Web 应用 → Spring Session + Redis，改造成本最低。
- 对性能极致要求、Session 读取频繁 → Redis 存 Session 有网络开销，可考虑本地缓存 + Redis 二级缓存。

**常见坑：** Redis 单点故障会导致所有用户掉线。生产环境 Redis 要做高可用（哨兵/集群），并配合降级策略。

---

> 📌 **学习建议**：Session 是理解后端"状态管理"的钥匙。作为前端工程师，你已经熟悉了浏览器端的 Cookie/localStorage/sessionStorage，现在要建立"服务端状态"的概念——Session 数据在服务器，浏览器只存 ID。本模块的核心收获是理解"为什么集群要共享 Session"和"Spring Session 如何透明地实现共享"。实际开发中，如果是新项目且前后端分离，更推荐直接用 JWT（无状态、更契合微服务），但理解 Session 机制是理解 JWT 的前提——JWT 本质上是把"Session 状态"打包进 token 携带，省去服务端存储。建议把拦截器这套登录校验套路练熟，它是后续 Spring Security 权限控制的基础。
