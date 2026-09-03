# 异步 Servlet

前面十五篇的 Servlet 都是**同步**的：一个请求占用一个线程，从开始处理到响应返回，线程一直被占用。如果处理慢（如调外部 API、查大数据），线程被占着，Tomcat 线程池（默认 200）很快耗尽，新请求排队超时。能不能让线程先释放，等慢操作完了再写响应？这就是 **Servlet 3.0 异步处理**。本篇讲清 `AsyncContext` 的原理、异步 Servlet 的适用场景，以及 WebSocket 的引入。这是 Spring Boot `@Async`/`DeferredResult`/`WebFlux` 的底层。

> 💡 本篇建议写一个同步 Servlet（`Thread.sleep(5000)`）和一个异步 Servlet，用浏览器各发一个请求，观察 Tomcat 线程占用——同步的线程被卡 5 秒，异步的线程立即释放。亲手感受"异步释放线程"的价值。

---

## 一、为什么需要异步 Servlet

### 1.1 同步 Servlet 的问题

Tomcat 用线程池处理请求（默认 200 线程）。同步模式下，一个请求占一个线程，直到响应返回：

```
请求1 → 线程1（处理 5 秒，调外部 API）→ 线程1 占用 5 秒
请求2 → 线程2（处理 5 秒）
...
请求201 → 线程池满，排队 → 超时
```

> ⚠️ **线程池是瓶颈**：200 个慢请求就把 Tomcat 线程占满，第 201 个请求排队超时。**同步 Servlet 的线程在等待慢操作（IO、外部调用）时是"空转"的**——没干活但占着线程，浪费资源。

### 1.2 异步 Servlet 的解法

Servlet 3.0 异步处理：线程开始处理后，**把慢操作交给其他线程**，当前线程立即释放回池子，等慢操作完了再写响应：

```
请求1 → 线程1（启动异步，立即释放）→ 线程1 回池子接新请求
              ↓ 异步线程处理 5 秒
              ↓ 完成后写响应
请求2 → 线程1（已释放，可接手）→ ...
```

> 💡 **异步的核心价值是"释放线程"**：不是让请求更快（总耗时不变），而是让 Tomcat 线程池不被慢请求占满——**吞吐量提升**。理解这点，就不会误以为"异步 = 更快"。

> ⚠️ **异步不是万能**：异步只对"IO 密集、有大量等待"的场景有效（调外部 API、查大数据、推送）。CPU 密集型（计算）异步没用——CPU 在算，线程还是要等。**异步解决的是"线程在等 IO 时空转"的浪费**。

---

## 二、AsyncContext 异步处理 ⭐

### 2.1 基本用法

```java
// 正确写法：开启异步支持
@WebServlet(urlPatterns = "/async", asyncSupported = true)
public class AsyncServlet extends HttpServlet {

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) {
        // 1. 开启异步，拿到 AsyncContext
        AsyncContext asyncContext = req.startAsync();

        // 2. 提交到线程池执行慢操作（Tomcat 线程立即释放）
        ExecutorService executor = (ExecutorService) req.getServletContext()
                .getAttribute("executor");
        executor.submit(() -> {
            try {
                // 慢操作（如调外部 API）
                Thread.sleep(5000);

                // 3. 慢操作完成，写响应
                resp.setContentType("text/html;charset=utf-8");
                asyncContext.getResponse().getWriter().write("异步处理完成");

            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                // 4. ★ 必须调用 complete()，告诉容器响应结束
                asyncContext.complete();
            }
        });

        // doGet 方法返回，Tomcat 线程释放回池子
    }
}
```

> ⚠️ **异步 Servlet 三要素**：
> 1. `asyncSupported = true`：`@WebServlet` 开启异步支持
> 2. `req.startAsync()`：开启异步，拿到 `AsyncContext`
> 3. `asyncContext.complete()`：**必须调用**，告诉容器响应结束——不调，容器以为响应没完成，请求超时

### 2.2 异步的执行流程

```
1. 请求到达 → Tomcat 线程调 doGet
2. doGet 里 startAsync() → 开启异步
3. 提交任务到线程池 → doGet 返回 → Tomcat 线程释放回池子（接新请求）
4. 线程池执行慢操作（5 秒）
5. 慢操作完 → 写响应 → complete() → 容器发送响应
```

> 💡 **Tomcat 线程 vs 业务线程**：Tomcat 线程（少而贵，默认 200）负责接请求；业务线程（线程池，可多可少）负责慢操作。异步把两者解耦——Tomcat 线程快速交接给业务线程后释放，不被慢操作拖住。

### 2.3 异步监听器

`AsyncListener` 监听异步事件：

```java
asyncContext.addListener(new AsyncListener() {
    @Override
    public void onComplete(AsyncEvent event) { System.out.println("异步完成"); }
    @Override
    public void onError(AsyncEvent event) { System.out.println("异步出错"); }
    @Override
    public void onStartAsync(AsyncEvent event) { System.out.println("异步开始"); }
    @Override
    public void onTimeout(AsyncEvent event) { System.out.println("异步超时"); }
});

// 设置超时（毫秒）
asyncContext.setTimeout(10000);   // 10 秒超时
```

> 💡 **超时必须设**：异步操作可能卡死，不设超时请求永远不结束。`setTimeout` 防止异步任务挂起导致连接泄漏。

---

## 三、异步 Servlet 的适用场景

### 3.1 适合异步的场景

| 场景 | 为什么异步有效 |
| :--- | :--- |
| 调外部 API（HTTP 调用） | 等待外部响应时线程空转，异步释放 |
| 查大数据 / 慢 SQL | 数据库返回前线程等待，异步释放 |
| 服务端推送（SSE） | 长连接等待事件，异步不占线程 |
| 聚合多个服务调用 | 并行调多个服务，异步等全部完成 |

### 3.2 不适合异步的场景

| 场景 | 为什么异步无效 |
| :--- | :--- |
| CPU 密集计算 | CPU 在算，线程必须等，异步没用 |
| 简单 CRUD（快） | 本来就快，异步的开销反而拖累 |
| 同步阻塞调用且无法并行 | 异步只是换线程等，不省总时间 |

> 💡 **异步的判断标准**：操作里有没有"大量等待"（IO、网络、数据库）？有就适合异步（释放线程）；没有（纯计算）就不适合。**异步优化的是吞吐量（线程利用率），不是单请求延迟**。

---

## 四、服务器推送（SSE）

异步 Servlet 的典型应用：**Server-Sent Events**（SSE），服务器主动推送数据到浏览器。

```java
@WebServlet(urlPatterns = "/sse", asyncSupported = true)
public class SseServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        resp.setContentType("text/event-stream");   // SSE 专用类型
        resp.setCharacterEncoding("utf-8");

        AsyncContext asyncContext = req.startAsync();

        new Thread(() -> {
            try {
                for (int i = 0; i < 5; i++) {
                    Thread.sleep(1000);
                    // SSE 格式：data: 内容\n\n
                    asyncContext.getResponse().getWriter()
                            .write("data: 消息" + i + "\n\n");
                    asyncContext.getResponse().getWriter().flush();
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                asyncContext.complete();
            }
        }).start();
    }
}
```

```javascript
// 前端接收 SSE
let source = new EventSource("/sse");
source.onmessage = function(event) {
    console.log("收到：" + event.data);   // 每秒打印一条消息
};
```

> 💡 **SSE 是异步 Servlet 的典型应用**：服务器持续推送，连接保持打开，但用异步不占 Tomcat 线程。**聊天、实时通知、股票行情**等推送场景用 SSE。WebSocket（下节）是更全双工的方案。

---

## 五、WebSocket 引入

SSE 是单向（服务器→客户端），**WebSocket** 是双向全双工通信——服务器和客户端都能主动发消息。

```java
// WebSocket 端点（Java API，@ServerEndpoint）
@ServerEndpoint("/ws/chat")
public class ChatEndpoint {

    @OnOpen
    public void onOpen(Session session) {
        System.out.println("连接打开：" + session.getId());
    }

    @OnMessage
    public void onMessage(String message, Session session) throws IOException {
        System.out.println("收到：" + message);
        session.getBasicRemote().sendText("服务器回复：" + message);   // 主动推送
    }

    @OnClose
    public void onClose(Session session) { System.out.println("连接关闭"); }

    @OnError
    public void onError(Session session, Throwable t) { t.printStackTrace(); }
}
```

```javascript
// 前端 WebSocket
let ws = new WebSocket("ws://localhost:8080/ws/chat");
ws.onmessage = function(event) { console.log("收到：" + event.data); };
ws.onopen = function() { ws.send("你好服务器"); };
```

> 💡 **WebSocket vs SSE vs AJAX**：
> - **AJAX**：客户端主动请求，服务器响应，单向、短连接
> - **SSE**：服务器主动推送，单向、长连接（基于 HTTP）
> - **WebSocket**：双向全双工、长连接（独立协议，握手后升级）
>
> 聊天室、多人协作、实时游戏用 WebSocket；简单推送用 SSE；普通查询用 AJAX。

> 💡 **WebSocket 和异步 Servlet 的关系**：WebSocket 是独立协议（握手升级后脱离 HTTP），不依赖异步 Servlet。但两者都解决"长连接不占线程"的问题——WebSocket 用独立连接管理，异步 Servlet 用 `AsyncContext` 释放线程。Spring Boot 的 WebSocket 支持底层是容器提供的。

---

## ⚠️ 重点

1. **异步 Servlet 解决"线程空转"**：释放 Tomcat 线程，提升吞吐量，不是让单请求更快。
2. **异步三要素**：`asyncSupported=true` + `startAsync()` + `complete()`（必须调）。
3. **Tomcat 线程 vs 业务线程**：Tomcat 线程（少）接请求，业务线程（多）跑慢操作。
4. **适合 IO 密集场景**：外部 API、慢 SQL、SSE 推送；不适合 CPU 密集。
5. **`setTimeout` 必须设**：防异步任务挂起导致连接泄漏。
6. **SSE 是服务器单向推送**：`text/event-stream`，基于异步 Servlet。
7. **WebSocket 是双向全双工**：聊天/协作场景，独立协议。
8. **AJAX/SSE/WebSocket 选型**：查询用 AJAX，推送用 SSE，双向用 WebSocket。

---

## 💻 实战案例：异步调用外部 API

需求：Servlet 收到请求后，异步调用一个慢外部 API（模拟 5 秒），不阻塞 Tomcat 线程。

```java
@WebServlet(urlPatterns = "/weather", asyncSupported = true)
public class WeatherServlet extends HttpServlet {

    // 业务线程池（独立于 Tomcat 线程池）
    private final ExecutorService executor = Executors.newFixedThreadPool(20);

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        String city = req.getParameter("city");
        AsyncContext asyncContext = req.startAsync();
        asyncContext.setTimeout(10000);   // 10 秒超时

        executor.submit(() -> {
            try {
                // 慢操作：调外部天气 API（模拟 5 秒）
                Thread.sleep(5000);
                String weather = "晴天 25°C";

                asyncContext.getResponse().setContentType("application/json;charset=utf-8");
                asyncContext.getResponse().getWriter()
                        .write("{\"city\":\"" + city + "\",\"weather\":\"" + weather + "\"}");
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                asyncContext.complete();   // ★ 必须调
            }
        });
        // doGet 返回，Tomcat 线程释放
    }
}
```

> 💡 **对比同步版**：如果用同步 Servlet，`Thread.sleep(5000)` 期间 Tomcat 线程被占——20 个并发请求就把 200 线程池占 20%。异步版 Tomcat 线程立即释放，200 线程池能接更多请求。**这就是异步的价值——吞吐量提升**。

> ⚠️ **业务线程池要独立**：异步 Servlet 的慢操作要用自己的线程池，不能复用 Tomcat 线程池——否则异步把 Tomcat 线程又占满了，失去意义。Spring Boot 的 `@Async` 配 `@EnableAsync` + `ThreadPoolTaskExecutor` 就是这个独立线程池。

---

## 🚀 新版本补充

- **Servlet 3.1**：非阻塞 IO（`ReadListener`/`WriteListener`），异步时 IO 也不阻塞线程。
- **Servlet 4.0**：HTTP/2 服务器推送（`PushBuilder`），主动推送资源。
- **Spring WebFlux**：响应式编程（Reactor），全异步非阻塞，比传统异步 Servlet 更彻底——用少量线程处理大量并发。

---

## 📌 在 Spring Boot 中

> 本篇讲的 `AsyncContext`、异步释放线程、SSE、WebSocket，在 Spring Boot 中由 `@Async`/`DeferredResult`/`WebFlux`/Spring WebSocket 接管。下面逐一对照，给出实际开发代码，以及"出问题怎么回到异步原理排查"。实际开发你几乎不手写 `AsyncContext`——Spring Boot 的 `@Async`/`DeferredResult` 更简洁，但理解了本篇，异步不生效、线程池满、响应不返回问题时才知道怎么查。

### 1. 异步处理：从"AsyncContext + 线程池"到"DeferredResult / @Async"

**原生**：本篇 2.1 用 `req.startAsync()` + 手动线程池 + `complete()`。
**Spring Boot**：`DeferredResult`（异步响应）或 `@Async`（异步方法）。

**方式一：`DeferredResult`（异步响应，最贴合本篇）**

```java
@RestController
public class WeatherController {

    @Autowired
    private WeatherService weatherService;

    @GetMapping("/weather")
    public DeferredResult<String> weather(@RequestParam String city) {
        // DeferredResult 等价 AsyncContext，Tomcat 线程立即释放
        DeferredResult<String> result = new DeferredResult<>(10000L);   // 10 秒超时
        result.onTimeout(() -> result.setErrorResult("超时"));

        // 异步调用，完成后 setResult（等价 complete + 写响应）
        weatherService.getWeatherAsync(city, result::setResult);
        return result;   // Tomcat 线程释放，result 有值时才写响应
    }
}
```

**方式二：`@Async`（异步方法）**

```java
@Service
public class WeatherService {

    @Async   // 异步执行，调用方不阻塞
    public void getWeatherAsync(String city, Consumer<String> callback) {
        try {
            Thread.sleep(5000);   // 慢操作
            callback.accept("晴天 25°C");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

// 开启异步（配置类）
@EnableAsync
@Configuration
public class AsyncConfig {
    @Bean
    public TaskExecutor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(20);     // 独立线程池（对应本篇的业务线程池）
        executor.setMaxPoolSize(50);
        return executor;
    }
}
```

> 💡 **原理对应**：`DeferredResult` 等价本篇的 `AsyncContext`——返回 `DeferredResult` 时 Tomcat 线程释放，等 `setResult` 被调时才写响应（等价 `complete()`）。`@Async` 等价本篇的"提交到业务线程池"——方法异步执行，调用方不阻塞。**本篇手动 `startAsync` + 线程池 + `complete`，Spring Boot 用 `DeferredResult`/`@Async` + `@EnableAsync` 封装**。

> 💡 **原理排查**：`@Async` 不生效（方法同步执行）？检查是否加了 `@EnableAsync`、异步方法是否在 Spring Bean 里、是否同类内部调用（同类调用 `@Async` 不生效，要走代理）。回到异步原理：`@Async` 靠 AOP 代理，同类调用绕过代理。`DeferredResult` 不返回？检查 `setResult` 是否被调、是否超时。回到本篇原理：`complete()` 不调响应永远不返回。

### 2. 线程池配置：从"手动 ExecutorService"到"ThreadPoolTaskExecutor"

**原生**：本篇实战手动 `Executors.newFixedThreadPool(20)`。
**Spring Boot**：`ThreadPoolTaskExecutor` + yml 配置。

```yaml
spring:
  task:
    execution:
      pool:
        core-size: 20          # 核心线程数
        max-size: 50           # 最大线程数
        queue-capacity: 100    # 队列容量
      thread-name-prefix: async-
```

> 💡 **原理对应**：`spring.task.execution.pool.*` 配置的就是本篇的业务线程池——独立于 Tomcat 线程池。**本篇强调的"业务线程池要独立"，Spring Boot 用 `ThreadPoolTaskExecutor` 显式配置**，避免和 Tomcat 线程池混淆。

> 💡 **原理排查**：异步任务堆积、线程池满？检查 `core-size`/`max-size`/`queue-capacity` 配置、是否有任务泄漏（`complete`/`setResult` 没调）。回到异步原理：线程池满会拒绝任务，慢操作要有超时。

### 3. SSE 推送：从"AsyncContext + text/event-stream"到"SseEmitter"

**原生**：本篇第四节手写 `AsyncContext` + `text/event-stream`。
**Spring Boot**：`SseEmitter` 封装。

```java
@RestController
@RequestMapping("/sse")
public class SseController {

    @GetMapping("/events")
    public SseEmitter events() {
        SseEmitter emitter = new SseEmitter(0L);   // 不超时

        // 异步推送
        new Thread(() -> {
            try {
                for (int i = 0; i < 5; i++) {
                    Thread.sleep(1000);
                    emitter.send(SseEmitter.event().data("消息" + i));   // 推送
                }
                emitter.complete();   // 等价 asyncContext.complete()
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        }).start();

        return emitter;   // Tomcat 线程释放
    }
}
```

> 💡 **原理对应**：`SseEmitter` 底层就是本篇的 `AsyncContext` + `text/event-stream`——返回 `SseEmitter` 时 Tomcat 线程释放，`emitter.send` 推送数据，`emitter.complete()` 结束（等价 `asyncContext.complete()`）。**本篇手写的 SSE，Spring Boot 用 `SseEmitter` 封装**。

### 4. WebSocket：从"@ServerEndpoint"到"Spring WebSocket"

**原生**：本篇第五节用 `@ServerEndpoint`（Java API）。
**Spring Boot**：Spring WebSocket 或 STOMP。

```java
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(new ChatHandler(), "/ws/chat");
    }
}

@Component
public class ChatHandler extends TextWebSocketHandler {
    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        session.sendMessage(new TextMessage("服务器回复：" + message.getPayload()));
    }
}
```

> 💡 **原理对应**：Spring WebSocket 底层还是容器的 WebSocket 支持，只是用 Spring 的 Handler 体系封装。**本篇的 `@ServerEndpoint`/`@OnMessage`，Spring Boot 用 `WebSocketHandler`/`handleMessage` 表达**，原理一样——双向全双工长连接。

> 💡 **选型**：简单推送用 SSE（`SseEmitter`），双向实时用 WebSocket（聊天/协作）。两者底层都依赖异步机制（释放 Tomcat 线程），理解了本篇的 `AsyncContext`，Spring 的 `SseEmitter`/WebSocket 就不神秘。

### 5. 响应式：从"异步 Servlet"到"Spring WebFlux"

**原生**：本篇的异步 Servlet 是"半异步"——Tomcat 线程释放了，但业务线程还在阻塞等 IO。
**Spring WebFlux**：全异步非阻塞，用少量线程 + 响应式流（Reactor）处理大量并发。

```java
// WebFlux（响应式，全异步）
@RestController
public class WeatherFluxController {

    @GetMapping("/weather")
    public Mono<String> weather(@RequestParam String city) {
        // Mono 是响应式流，订阅时才执行，全程不阻塞任何线程
        return Mono.fromCallable(() -> {
            Thread.sleep(5000);   // 这里应该用非阻塞 HTTP 客户端，而非 sleep
            return "晴天 25°C";
        }).subscribeOn(Schedulers.boundedElastic());
    }
}
```

> 💡 **原理对应**：WebFlux 是本篇异步思想的极致——不仅 Tomcat 线程释放，业务线程也不阻塞（用响应式流 + 非阻塞 IO）。**本篇的异步 Servlet 是"释放 Tomcat 线程"，WebFlux 是"几乎不占任何线程"**。理解了本篇的异步原理，WebFlux 的"全异步非阻塞"就是它的进化方向。

> ⚠️ **WebFlux 不是银弹**：全异步要求全程非阻塞（DB/HTTP 都要用响应式客户端），学习曲线陡、调试难。**传统 Spring MVC + `@Async`/`DeferredResult` 已能满足大多数异步场景**，WebFlux 适合超高并发（如网关、流式处理）。

---

> 一句话：**异步 Servlet 解决"线程在 IO 等待时空转"的浪费，释放 Tomcat 线程提升吞吐量**。Spring Boot 里你几乎不手写 `AsyncContext`——`@Async` 异步方法、`DeferredResult` 异步响应、`SseEmitter` 推送、Spring WebSocket 双向通信封装了它，WebFlux 把异步推到极致。但底层都是本篇的"释放线程 + 完成回调"原理。理解了本篇，异步不生效、线程池满、响应不返回、超时泄漏问题对你就是透明的。**出 `@Async` 不生效、`DeferredResult` 不返回、线程池满问题时，你仍要回到本篇原理排查**：`@EnableAsync` 开了吗、`complete`/`setResult` 调了吗、线程池独立吗、超时设了吗。

## 本章小结

本篇讲清了异步 Servlet：它通过 `AsyncContext`（`startAsync` + `complete`）释放 Tomcat 线程，解决慢操作占线程的问题，提升吞吐量。重点掌握异步三要素（`asyncSupported=true`/`startAsync()`/`complete()`）、Tomcat 线程 vs 业务线程的分离、适合 IO 密集不适合 CPU 密集、`setTimeout` 防泄漏、SSE 单向推送、WebSocket 双向全双工。核心认知：**异步优化吞吐量而非单请求延迟，Spring Boot 的 `@Async`/`DeferredResult`/`SseEmitter`/WebFlux 是本篇 `AsyncContext` 的进化**。至此阶段六完成，AJAX/JSON、文件上传、异步 Servlet 你已掌握。下一篇 [17-数据库连接池](17-数据库连接池.md) 进入阶段七，讲连接池原理与 HikariCP——理解 Spring Boot 默认连接池的底层。
