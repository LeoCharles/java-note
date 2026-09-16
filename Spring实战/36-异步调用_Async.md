# 36 - Spring Boot 异步调用

> 对应项目模块：`demo-async`
> 前置知识：已学完前序模块，了解启动类、`@Component`、配置文件基本用法
> 学习目标：理解 Spring Boot 异步任务的完整套路——`@EnableAsync` + `@Async` + 线程池配置，能独立为项目添加异步能力，并避开自调用失效、异常吞没等常见坑。

---

## 一、本模块要解决什么问题？

### 1.1 同步 vs 异步：一个直观的例子

假设你有 3 个耗时任务，分别需要 5 秒、2 秒、3 秒：

- **同步执行**：一个接一个跑，总耗时 = 5 + 2 + 3 = **10 秒**。主线程被一直阻塞，期间什么都干不了。
- **异步执行**：3 个任务同时开跑（各占一个线程），总耗时 ≈ 最长的那个 = **5 秒**。主线程提交完任务就可以干别的去了。

本模块就是用 Spring Boot 原生的异步支持，把耗时任务从主线程剥离出去并行执行，提升吞吐、减少用户等待。

> 💡 前端类比：这就像 JavaScript 里的 `Promise.all([task1(), task2(), task3()])`——三个异步操作并行，等最慢的那个完成。区别是 JS 是单线程事件循环，而 Java 是真·多线程并行。

### 1.2 什么时候需要异步？

实际开发中这些场景常用异步：

| 场景 | 说明 |
| --- | --- |
| 发送邮件/短信 | 用户注册后发欢迎邮件，不该让用户等邮件发完才返回注册成功 |
| 生成报表/导出 | 大数据量导出 Excel，异步生成后通知用户下载 |
| 调用第三方接口 | 调多个无依赖的外部 API，并行调用缩短总时间 |
| 日志记录 | 把审计日志异步落库，不阻塞主业务 |
| 消息推送 | WebSocket/SSE 推送给多个客户端 |

> ⚠️ 注意：异步不是万能药。如果任务之间有依赖（B 需要 A 的结果），或者任务本身极快（几毫秒），异步反而因线程切换开销变慢。**异步适合"耗时长、彼此独立、结果不立即需要"的任务。**

---

## 二、项目结构

```
demo-async/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/xkcoding/async/
    │   │   ├── SpringBootDemoAsyncApplication.java   # 启动类（@EnableAsync）
    │   │   └── task/
    │   │       └── TaskFactory.java                  # 任务工厂（@Async 方法 + 同步方法）
    │   └── resources/
    │       └── application.yml                        # 线程池配置
    └── test/java/com/xkcoding/async/
        ├── SpringBootDemoAsyncApplicationTests.java   # 测试基类
        └── task/
            └── TaskFactoryTest.java                   # 对比同步 vs 异步耗时
```

注意这个模块**没有 `spring-boot-starter-web`**，只引了 `spring-boot-starter`，因为它演示的是纯异步任务，不需要 HTTP 接口。测试类直接调用任务方法验证效果。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Spring Boot 基础起步依赖（不含 Web） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 3. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**关键点**：

- 用的是 `spring-boot-starter` 而不是 `spring-boot-starter-web`。前者只包含 Spring 核心上下文、自动配置，没有内嵌 Tomcat 和 Spring MVC。本模块不需要起 Web 服务，所以用更轻量的 starter。
- 异步支持（`@EnableAsync`、`@Async`）来自 `spring-context`，而 `spring-context` 包含在 `spring-boot-starter` 里，所以**不需要额外引依赖**——Spring Boot 自带异步能力。
- Lombok 的 `@Slf4j` 用于自动生成 `log` 对象，方便打印日志。

---

## 四、逐行拆解启动类

```java
@EnableAsync
@SpringBootApplication
public class SpringBootDemoAsyncApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoAsyncApplication.class, args);
    }
}
```

核心是 `@EnableAsync` 这个注解。

### 4.1 `@EnableAsync` 是做什么的？

它开启 Spring 的异步方法支持。原理是：它注册一个 `AsyncAnnotationBeanPostProcessor`（异步注解后置处理器），这个后置处理器会扫描容器里所有带 `@Async` 注解的方法，给这些方法所在的 Bean 创建**AOP 代理**。调用代理方法时，不直接执行，而是把任务提交到线程池异步执行。

> 💡 前端类比：`@EnableAsync` 类似在 Vue 应用入口 `app.use(plugin)` 注册一个全局插件——不注册，插件提供的指令（`@Async`）就不生效。没有它，`@Async` 注解只是个普通标记，方法仍然是同步执行的。

**不加 `@EnableAsync` 会怎样？** `@Async` 注解完全失效，方法还是同步跑，不会报错，但也不会异步——这是新手最常踩的坑之一。

---

## 五、逐行拆解 TaskFactory（核心）

`task/TaskFactory.java` 是本模块的核心，定义了 3 个异步任务和 3 个同步任务做对比：

```java
@Component
@Slf4j
public class TaskFactory {

    /**
     * 模拟5秒的异步任务
     */
    @Async
    public Future<Boolean> asyncTask1() throws InterruptedException {
        doTask("asyncTask1", 5);
        return new AsyncResult<>(Boolean.TRUE);
    }

    @Async
    public Future<Boolean> asyncTask2() throws InterruptedException {
        doTask("asyncTask2", 2);
        return new AsyncResult<>(Boolean.TRUE);
    }

    @Async
    public Future<Boolean> asyncTask3() throws InterruptedException {
        doTask("asyncTask3", 3);
        return new AsyncResult<>(Boolean.TRUE);
    }

    /**
     * 模拟5秒的同步任务
     */
    public void task1() throws InterruptedException {
        doTask("task1", 5);
    }

    public void task2() throws InterruptedException {
        doTask("task2", 2);
    }

    public void task3() throws InterruptedException {
        doTask("task3", 3);
    }

    private void doTask(String taskName, Integer time) throws InterruptedException {
        log.info("{}开始执行，当前线程名称【{}】", taskName, Thread.currentThread().getName());
        TimeUnit.SECONDS.sleep(time);
        log.info("{}执行成功，当前线程名称【{}】", taskName, Thread.currentThread().getName());
    }
}
```

### 5.1 `@Component` + `@Slf4j`

- `@Component`：注册成 Spring Bean。**重要**：`@Async` 方法所在的类必须是 Spring 管理的 Bean，因为异步靠 AOP 代理实现，只有 Spring 创建的 Bean 才会被代理。自己 `new` 出来的对象，`@Async` 不生效。
- `@Slf4j`：Lombok 注解，自动生成 `private static final Logger log = ...`，可以直接用 `log.info(...)`。

### 5.2 `@Async` 注解

```java
@Async
public Future<Boolean> asyncTask1() throws InterruptedException {
    doTask("asyncTask1", 5);
    return new AsyncResult<>(Boolean.TRUE);
}
```

- `@Async` 标记在方法上，表示这个方法异步执行。
- 调用方调用 `asyncTask1()` 时，**立即返回**（不会等 5 秒），实际任务被提交到线程池，由另一个线程执行。
- 方法内部该阻塞还是阻塞（`TimeUnit.SECONDS.sleep(5)` 阻塞的是**工作线程**，不是调用方线程）。

### 5.3 返回值 `Future<Boolean>` 和 `AsyncResult`

异步方法有两种返回值写法：

| 返回类型 | 含义 | 适用场景 |
| --- | --- | --- |
| `void` | 调用方不关心结果，"fire and forget" | 发邮件、记日志、推送通知 |
| `Future<T>` | 调用方可以后续取结果 | 需要结果、或需要知道是否成功 |

本模块用 `Future<Boolean>`，返回 `new AsyncResult<>(Boolean.TRUE)`：

- `Future` 是 Java 并发包的接口，代表"未来的结果"。
- `AsyncResult` 是 Spring 提供的 `Future` 实现类，用于包装 `@Async` 方法的返回值。
- 调用方拿到 `Future` 后，可以调 `future.get()` 阻塞等待结果，或 `future.isDone()` 查询是否完成。

> 💡 前端类比：`Future` 类似 JavaScript 的 `Promise`。`future.get()` 像 `await promise`（阻塞直到完成），`AsyncResult` 像已经 resolve 的 `Promise.resolve(value)`。

### 5.4 `doTask` 私有方法

```java
private void doTask(String taskName, Integer time) throws InterruptedException {
    log.info("{}开始执行，当前线程名称【{}】", taskName, Thread.currentThread().getName());
    TimeUnit.SECONDS.sleep(time);
    log.info("{}执行成功，当前线程名称【{}】", taskName, Thread.currentThread().getName());
}
```

- `Thread.currentThread().getName()`：获取当前线程名。异步任务会打印 `async-task-1`、`async-task-2` 等（线程名前缀在 yml 配置），同步任务打印 `main`。这是验证异步是否生效的关键证据。
- `TimeUnit.SECONDS.sleep(time)`：模拟耗时操作。注意它抛 `InterruptedException`，是受检异常必须声明或捕获。

### 5.5 同步方法对比

`task1()`、`task2()`、`task3()` 没有 `@Async`，是普通同步方法，用于和异步方法做耗时对比。

---

## 六、配置文件：线程池参数

`application.yml`：

```yaml
spring:
  task:
    execution:
      pool:
        # 最大线程数
        max-size: 16
        # 核心线程数
        core-size: 16
        # 存活时间
        keep-alive: 10s
        # 队列大小
        queue-capacity: 100
        # 是否允许核心线程超时
        allow-core-thread-timeout: true
      # 线程名称前缀
      thread-name-prefix: async-task-
```

这是 Spring Boot 2.1.0 引入的 `spring.task.execution` 配置，用于定制 `@Async` 默认使用的线程池。

### 6.1 各参数含义

| 参数 | 作用 | 本模块值 |
| --- | --- | --- |
| `core-size` | 核心线程数（线程池常驻线程） | 16 |
| `max-size` | 最大线程数（队列满后才会创建到这个数） | 16 |
| `queue-capacity` | 任务队列容量（核心线程忙时，任务先进队列） | 100 |
| `keep-alive` | 非核心线程空闲多久后回收 | 10s |
| `allow-core-thread-timeout` | 是否允许核心线程也超时回收 | true |
| `thread-name-prefix` | 线程名前缀（日志里能看到） | `async-task-` |

### 6.2 线程池工作流程（重要）

提交任务到线程池时，处理顺序是：

1. 若当前线程数 < `core-size`，创建新线程执行。
2. 若线程数已达 `core-size`，任务进队列等待。
3. 若队列满了，且线程数 < `max-size`，创建非核心线程执行。
4. 若队列满且线程数达 `max-size`，按拒绝策略处理（默认抛异常）。

> 💡 前端类比：线程池像一个客服中心。`core-size` 是常驻客服，`queue-capacity` 是候客区座位，`max-size` 是忙时临时加的客服。常驻客服都忙 → 进候客区排队 → 候客区满 → 加临时客服 → 还不够 → 拒绝接待（拒绝策略）。

本模块 `core-size = max-size = 16`，意味着没有"临时扩容"空间，队列满（100个任务）后直接拒绝。

---

## 七、测试类：对比同步 vs 异步

`TaskFactoryTest.java`：

```java
@Slf4j
public class TaskFactoryTest extends SpringBootDemoAsyncApplicationTests {
    @Autowired
    private TaskFactory task;

    /**
     * 测试异步任务
     */
    @Test
    public void asyncTaskTest() throws InterruptedException, ExecutionException {
        long start = System.currentTimeMillis();
        Future<Boolean> asyncTask1 = task.asyncTask1();
        Future<Boolean> asyncTask2 = task.asyncTask2();
        Future<Boolean> asyncTask3 = task.asyncTask3();

        // 调用 get() 阻塞主线程
        asyncTask1.get();
        asyncTask2.get();
        asyncTask3.get();
        long end = System.currentTimeMillis();

        log.info("异步任务全部执行结束，总耗时：{} 毫秒", (end - start));
    }

    /**
     * 测试同步任务
     */
    @Test
    public void taskTest() throws InterruptedException {
        long start = System.currentTimeMillis();
        task.task1();
        task.task2();
        task.task3();
        long end = System.currentTimeMillis();

        log.info("同步任务全部执行结束，总耗时：{} 毫秒", (end - start));
    }
}
```

### 7.1 异步测试的关键逻辑

```java
Future<Boolean> asyncTask1 = task.asyncTask1();  // 立即返回，不阻塞
Future<Boolean> asyncTask2 = task.asyncTask2();  // 立即返回
Future<Boolean> asyncTask3 = task.asyncTask3();  // 立即返回

asyncTask1.get();  // 阻塞，等 asyncTask1 完成
asyncTask2.get();  // 此时 asyncTask2 可能已完成，get 立即返回
asyncTask3.get();  // 同理
```

- 三次 `task.asyncTaskX()` 调用几乎瞬间完成（只是把任务提交给线程池）。
- 三个任务在各自的工作线程里并行跑。
- `future.get()` 阻塞主线程直到对应任务完成。
- 因为三个任务并行，总耗时 ≈ 最长的 5 秒。

### 7.2 `Future.get()` 的两个细节

1. **阻塞**：`get()` 会阻塞调用线程直到任务完成。如果想限时等待，用 `get(long timeout, TimeUnit unit)`。
2. **异常**：如果异步任务里抛了异常，`get()` 会把它包装成 `ExecutionException` 抛出。这是无返回值异步方法拿不到异常的原因之一（见第九章坑）。

### 7.3 运行结果对比

**异步任务**（总耗时 ≈ 5000 毫秒）：

```
asyncTask1开始执行，当前线程名称【async-task-1】
asyncTask2开始执行，当前线程名称【async-task-2】
asyncTask3开始执行，当前线程名称【async-task-3】
asyncTask2执行成功，当前线程名称【async-task-2】   ← 2秒后
asyncTask3执行成功，当前线程名称【async-task-3】   ← 3秒后
asyncTask1执行成功，当前线程名称【async-task-1】   ← 5秒后
异步任务全部执行结束，总耗时：5015 毫秒
```

**同步任务**（总耗时 ≈ 10000 毫秒）：

```
task1开始执行，当前线程名称【main】   ← 全程 main 线程
task1执行成功，当前线程名称【main】   ← 5秒后
task2开始执行，当前线程名称【main】
task2执行成功，当前线程名称【main】   ← 7秒后
task3开始执行，当前线程名称【main】
task3执行成功，当前线程名称【main】   ← 10秒后
同步任务全部执行结束，总耗时：10023 毫秒
```

**关键观察点**：
- 异步任务线程名是 `async-task-X`（来自 yml 配置的前缀），同步任务是 `main`。
- 异步任务三个"开始执行"几乎同时打印，说明并行；同步任务一个完了才开始下一个。
- 异步总耗时 5 秒（取最长），同步总耗时 10 秒（累加）。

---

## 八、运行与验证

本模块没有 Web 接口，通过单元测试验证：

```sh
# 在 demo-async 目录下
mvn test -Dtest=TaskFactoryTest
```

观察控制台日志，对比两个测试方法的耗时输出，验证异步确实生效。

---

## 九、动手练习

1. **去掉 `@EnableAsync`**：把启动类的 `@EnableAsync` 注释掉，重跑异步测试，观察线程名变成 `main`、耗时变成 10 秒——验证 `@EnableAsync` 的作用。
2. **改线程池大小**：把 `core-size` 改成 `1`，重跑异步测试，观察任务变成串行（因为只有一个工作线程），耗时接近 10 秒。
3. **改返回值为 void**：把某个 `@Async` 方法改成返回 `void`，测试时去掉 `get()` 调用，观察主线程不等任务完成就结束——体会"fire and forget"。
4. **制造超时**：把 `future.get()` 改成 `future.get(1, TimeUnit.SECONDS)`，观察 `TimeoutException`——学习限时等待。
5. **制造异常**：在某个 `@Async` 方法里手动抛 `RuntimeException`，观察 `get()` 抛 `ExecutionException`——学习异步异常传播。
6. **自调用测试**：在 `TaskFactory` 里加一个普通方法 `caller()`，内部调用 `this.asyncTask1()`，从测试类调 `caller()`，观察异步失效——这是最重要的坑（见第十章详解）。

---

## 十、本模块知识点总结（结合实际开发详解）

异步是提升系统吞吐的常用手段，但用错地方反而添乱。下面把核心知识点放到真实开发场景里讲透。

### 10.1 `@EnableAsync` + `@Async` 的代理原理

**它是怎么生效的？**

`@Async` 本质是 AOP 代理。Spring 启动时，`AsyncAnnotationBeanPostProcessor` 给含 `@Async` 方法的 Bean 创建代理对象。调用 `@Async` 方法时，实际走的是代理，代理把方法体包装成 `Runnable` 提交到线程池，然后立即返回。

**这意味着两个关键约束：**

1. **必须是 Spring Bean**：`@Async` 方法所在的类要用 `@Component` 等注解注册。自己 `new` 出来的对象没有代理，`@Async` 失效。
2. **必须从外部调用**：同一个类里方法 A 调用方法 B（B 有 `@Async`），B 不会异步——因为 `this.B()` 走的是原始对象，不是代理对象。这就是著名的**自调用失效**问题。

**自调用失效的解决方法：**

- 把 `@Async` 方法拆到独立的类里（推荐，职责清晰）。
- 自己注入自己：`@Autowired private TaskFactory self;` 然后 `self.asyncTask1()`（能生效但不够优雅）。
- 用 `AopContext.currentProxy()` 获取当前代理（需要开启 `@EnableAspectJAutoProxy(exposeProxy = true)`）。

> 💡 前端类比：这像 Vue 里用 `this.method()` 调用未代理的方法 vs 通过 `proxy.method()` 调用被劫持的方法。Spring AOP 的代理只对外部调用生效，内部 `this` 调用绕过代理。

**常见坑**：新手把 `@Async` 加在 `private` 方法上——代理无法拦截私有方法（动态代理基于接口/继承，私有方法不可见），导致失效。**`@Async` 方法必须是 `public`。**

### 10.2 返回值设计：`void` vs `Future`

**实际开发中怎么选？**

| 场景 | 返回值 | 说明 |
| --- | --- | --- |
| 发邮件、记日志、推送 | `void` | 不关心结果，失败有日志即可 |
| 需要知道成功/失败 | `Future<Boolean>` | `get()` 取结果，异常也会传播 |
| 需要返回业务数据 | `Future<DTO>` | 取计算结果 |
| 需要超时控制 | `Future` + `get(timeout)` | 避免无限等待 |

**最佳实践：**

- 大多数"fire and forget"场景用 `void`，配合异步异常处理（见 10.3）。
- 需要结果聚合时用 `Future`，像本模块一样 `Future.get()` 等待。
- Spring 5+ 支持 `CompletableFuture` 作为返回值，比 `Future` 更灵活（支持回调、组合），实际项目更推荐：

  ```java
  @Async
  public CompletableFuture<User> findUser(Long id) {
      return CompletableFuture.completedFuture(userService.getById(id));
  }
  ```

> 💡 前端类比：`CompletableFuture` 类似 JavaScript 的 `Promise`，支持 `.thenApply()`（类似 `.then()`）、`CompletableFuture.allOf()`（类似 `Promise.all()`）等链式操作。

**常见坑**：返回 `void` 的异步方法如果抛异常，异常会被吞掉（默认只打日志），调用方完全无感知。这是线上问题难排查的元凶之一。

### 10.3 异步异常处理：`AsyncUncaughtExceptionHandler`

**返回 `void` 的异步方法异常怎么处理？**

默认情况下，`void` 返回的 `@Async` 方法抛异常会被 Spring 捕获并打日志，但调用方拿不到。要自定义处理，实现 `AsyncConfigurer`：

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return (ex, method, params) -> {
            log.error("异步任务异常: method={}, msg={}", method.getName(), ex.getMessage());
            // 可以发告警、记数据库等
        };
    }
}
```

**返回 `Future` 的方法异常**：会被包装进 `Future`，调用 `get()` 时抛 `ExecutionException`，`getCause()` 能拿到原始异常。

**最佳实践：**

- 关键异步任务用 `Future` 返回，让调用方能感知失败。
- 不重要的异步任务用 `void` + 全局异常处理器，统一记日志告警。
- 异步方法内部尽量 try-catch，不要把异常抛出去"听天由命"。

### 10.4 线程池配置：别用默认的

**Spring Boot 默认线程池是什么？**

如果不配 `spring.task.execution`，`@Async` 用的是 `SimpleAsyncTaskTargetExecutor`——**它不是真正的线程池**，每次调用都创建新线程，高并发下会创建大量线程导致 OOM。

**实际开发必须配置线程池**，两种方式：

**方式一：yml 配置（Spring Boot 2.1+，本模块用法）**

```yaml
spring:
  task:
    execution:
      pool:
        core-size: 8
        max-size: 32
        queue-capacity: 200
      thread-name-prefix: my-async-
```

**方式二：自定义 `ThreadPoolTaskExecutor` Bean（更灵活）**

```java
@Bean("myExecutor")
public ThreadPoolTaskExecutor myExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(8);
    executor.setMaxPoolSize(32);
    executor.setQueueCapacity(200);
    executor.setThreadNamePrefix("my-async-");
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
    executor.initialize();
    return executor;
}
```

用 `@Async("myExecutor")` 指定用哪个线程池，可以**为不同业务配不同池**（发邮件一个池、导出报表一个池，互不影响）。

**线程池参数怎么定？**

- **CPU 密集型**（计算为主）：核心线程数 ≈ CPU 核数 + 1，队列小，避免过多线程抢占 CPU。
- **IO 密集型**（网络/数据库等待）：核心线程数可以大些（CPU 核数 × 2 或更多），因为线程大多在等待，不占 CPU。
- **任务耗时差异大**：用较大队列缓冲，避免短任务挤占长任务的线程。

**常见坑：**

- 用默认线程池导致线上 OOM——**生产环境必须显式配置**。
- 队列设得太大（如 `Integer.MAX_VALUE`），任务堆积导致内存溢出——队列要有上限。
- 拒绝策略没考虑：默认 `AbortPolicy`（抛异常），生产可能希望 `CallerRunsPolicy`（让调用线程自己跑，做背压）。

### 10.5 异步 vs 多线程 vs 消息队列：怎么选？

| 方案 | 适用场景 | 局限 |
| --- | --- | --- |
| `@Async` | 单机、轻量、任务即时执行 | 重启会丢失任务、不能跨节点 |
| 手写 `Thread`/`ExecutorService` | 需要精细控制线程 | 重复造轮子、缺 Spring 集成 |
| 消息队列（RabbitMQ/Kafka） | 跨节点、需持久化、削峰填谷 | 架构复杂、有延迟 |

**选择建议：**

- 单机、任务丢了无所谓（如发邮件）→ `@Async` 足够。
- 任务必须可靠完成、系统多节点 → 用消息队列。
- 需要定时触发 → 用定时任务（`@Scheduled` / Quartz / XXL-JOB）。
- 需要返回结果给前端 → 异步 + 轮询/WebSocket 推送结果。

> 💡 前端类比：`@Async` 像前端的 `setTimeout`/`Worker`（单机、进程内）；消息队列像用 Redis/消息服务做跨页签通信（持久、跨进程）。前者简单但局限，后者可靠但重。

### 10.6 异步与事务的冲突

**经典坑：异步方法 + `@Transactional`**

如果 `@Async` 方法上同时有 `@Transactional`，事务是在**工作线程**里开启和提交的，和调用方线程不是同一个事务。常见问题：

- 调用方想让异步任务看到自己刚插入的数据，但调用方事务还没提交，异步任务看不到。
- 异步任务里异常，不会回滚调用方的事务（两个独立事务）。

**最佳实践：**

- 异步方法用 `@Transactional(propagation = Propagation.REQUIRES_NEW)` 开新事务，独立提交。
- 调用方先提交事务，再调异步方法（把异步调用放到事务提交后，用 `TransactionSynchronizationManager.registerSynchronization()`）。
- 别指望异步方法和调用方在同一个事务里——它们在不同线程，Spring 事务是线程绑定的。

---

> 📌 **学习建议**：异步编程是后端提升性能的利器，但它的坑比想象中多——自调用失效、异常吞没、默认线程池 OOM、事务跨线程失效。建议先把本模块的"动手练习"全部做一遍，特别是自调用测试和异常测试，亲手踩一遍坑比看十遍文档都管用。记住一个原则：**异步方法必须是 public、必须是外部调用、必须有异常处理、必须配线程池**——这四条满足，基本不会出大问题。
