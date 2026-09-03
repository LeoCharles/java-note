# 30 - Zookeeper 分布式锁

> 对应项目模块：`demo-zookeeper`
> 前置知识：已学完 AOP 模块（`06-AOP请求日志_LogAop`）、配置注入模块（`02-读取配置文件_Properties`）
> 学习目标：理解分布式锁为什么存在、Zookeeper 怎么实现分布式锁，并能用 `@ZooLock` 注解 + AOP 给任意方法加锁。

---

## 一、本模块要解决什么问题？

### 1.1 先理解"锁"为什么需要

前端同学对"锁"可能比较陌生，因为 JavaScript 是单线程的。但在后端，一个服务会被成百上千个请求**同时**访问。看本模块测试类里的经典场景：

```java
private Integer count = 10000;   // 库存 1 万
public void doBuy() {
    count--;                     // 扣减库存
}
```

如果 10000 个线程同时执行 `doBuy()`，你期望最终 `count = 0`。但实际结果很可能不是 0，而是某个不为 0 的数（比如 37）。原因：`count--` 不是原子操作，它分三步——读值、减一、写回。多个线程交错执行时会丢更新。

> 💡 前端类比：这就像多个浏览器标签页同时往 `localStorage` 写同一个 key，没有锁的话后写的覆盖先写的。只是前端并发少，问题不明显；后端是高并发场景，问题被放大。

### 1.2 单机锁为什么不够用？

在单机（一个 JVM 进程）里，可以用 Java 自带的 `synchronized` 或 `ReentrantLock` 解决：

```java
public synchronized void doBuy() { count--; }   // 单机锁
```

但现代后端基本都是**集群部署**（多个实例 + 负载均衡），如下图：

```
用户请求 → Nginx → ┬→ 实例A (JVM1, 自己的 count)
                   ├→ 实例B (JVM2, 自己的 count)
                   └→ 实例C (JVM3, 自己的 count)
```

`synchronized` 只能锁住**当前 JVM**，三个实例各锁各的，依然会丢更新。这时需要一个**所有实例都能看到的"第三方"锁**——这就是**分布式锁**。

### 1.3 分布式锁的三种主流实现

| 实现方式 | 依赖 | 特点 |
| --- | --- | --- |
| **数据库** | 一张表 / 唯一索引 | 最简单，性能差，适合低频 |
| **Redis** | `SETNX` / Redisson | 性能高，最常用，但一致性不如 ZK |
| **Zookeeper** | 临时顺序节点 | 强一致性，可靠性最高，性能略低 |

本模块用 **Zookeeper + AOP** 实现，核心思路：给方法加个 `@ZooLock` 注解，AOP 自动拦截加锁/释放，业务代码零侵入。

---

## 二、先搞懂 Zookeeper 是什么

Zookeeper（简称 ZK）是一个**分布式协调服务**，可以理解为一个"可靠的树形文件系统"。前端同学可以把它想象成一个**所有服务都能连上的远程 key-value 存储**，但它有几个独特能力：

| 特性 | 说明 | 为什么对锁很重要 |
| --- | --- | --- |
| **树形节点** | 数据按路径组织，如 `/lock/buy` | 锁就是创建一个节点 |
| **临时节点** | 创建它的客户端连接断开，节点自动删除 | 客户端崩溃时锁自动释放，防死锁 |
| **顺序节点** | 节点名自动加递增序号，如 `lock000001` | 排队加锁，防"惊群" |
| **监听机制** | 可以监听节点变化 | 前一个节点释放，下一个自动被唤醒 |

> 💡 前端类比：ZK 有点像一个共享的 EventTarget，所有实例都能往上面注册事件、监听变化。它的强一致性来自 **ZAB 协议**（类似 Raft），任何写操作都要过半节点同意才生效。

### Curator 客户端

本模块不直接操作 ZK 原生 API，而是用 **Apache Curator**——ZK 的高级客户端封装，把复杂的操作简化成一行代码。pom 里的 `curator-recipes` 还提供了现成的分布式锁实现 `InterProcessMutex`，我们直接用。

---

## 三、项目结构

```
demo-zookeeper/
├── pom.xml
└── src/main/java/com/xkcoding/zookeeper/
    ├── SpringBootDemoZookeeperApplication.java   # 启动类
    ├── annotation/
    │   ├── ZooLock.java            # 分布式锁注解（标在方法上）
    │   └── LockKeyParam.java      # 动态 key 注解（标在参数上）
    ├── aspectj/
    │   └── ZooLockAspect.java     # AOP 切面：加锁/释放锁的核心
    └── config/
        ├── ZkConfig.java          # 注册 CuratorFramework Bean
        └── props/ZkProps.java     # ZK 连接配置
```

注意分层：`annotation` 放自定义注解，`aspectj` 放切面，`config` 放配置。这是注解 + AOP 模式的标准结构。

---

## 四、逐行拆解 pom.xml

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>

<!-- curator 版本4.1.0 对应 zookeeper 版本 3.5.x -->
<dependency>
    <groupId>org.apache.curator</groupId>
    <artifactId>curator-recipes</artifactId>
    <version>4.1.0</version>
</dependency>
```

- `spring-boot-starter-aop`：启用 Spring AOP，让 `@Aspect` 切面生效。
- `curator-recipes`：Curator 的"配方"包，包含 `InterProcessMutex`（可重入锁）等现成的分布式数据结构实现。

> ⚠️ **版本对应关系很重要**：Curator 4.1.0 对应 ZK 3.5.x。版本不匹配会启动报错，对应关系见 https://curator.apache.org/zk-compatibility.html

---

## 五、配置类：注册 ZK 客户端

### 5.1 配置属性 `ZkProps.java`

```java
@Data
@ConfigurationProperties(prefix = "zk")
public class ZkProps {
    private String url;            // 连接地址
    private int timeout = 1000;    // 超时时间(毫秒)
    private int retry = 3;          // 重试次数
}
```

用 `@ConfigurationProperties(prefix = "zk")` 把 `application.yml` 里 `zk.*` 的配置绑定到这个类（复习 `02-Properties` 模块）。

### 5.2 配置文件 `application.yml`

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo

zk:
  url: 127.0.0.1:2181     # ZK 默认端口 2181
  timeout: 1000
  retry: 3
```

### 5.3 配置类 `ZkConfig.java`

```java
@Configuration
@EnableConfigurationProperties(ZkProps.class)
public class ZkConfig {
    private final ZkProps zkProps;

    @Autowired
    public ZkConfig(ZkProps zkProps) {
        this.zkProps = zkProps;
    }

    @Bean
    public CuratorFramework curatorFramework() {
        RetryPolicy retryPolicy = new ExponentialBackoffRetry(zkProps.getTimeout(), zkProps.getRetry());
        CuratorFramework client = CuratorFrameworkFactory.newClient(zkProps.getUrl(), retryPolicy);
        client.start();
        return client;
    }
}
```

- `@EnableConfigurationProperties(ZkProps.class)`：启用 `ZkProps` 的属性绑定（因为 `ZkProps` 没加 `@Component`，需要在这里显式启用）。
- `@Bean curatorFramework()`：往 Spring 容器注册一个 `CuratorFramework`（ZK 客户端实例），后面切面里注入它。
- `ExponentialBackoffRetry`：指数退避重试策略——第一次失败等 1000ms，再失败等 2000ms、4000ms……避免疯狂重试压垮 ZK。
- `client.start()`：启动客户端连接。

> 💡 前端类比：这就像在应用启动时创建一个全局的 WebSocket 连接，所有模块共享这一个连接。

---

## 六、自定义注解：`@ZooLock` 和 `@LockKeyParam`

### 6.1 `@ZooLock` —— 标记需要加锁的方法

```java
@Target({ElementType.METHOD})        // 只能标在方法上
@Retention(RetentionPolicy.RUNTIME)  // 运行时保留（AOP 才能读到）
@Documented
@Inherited
public @interface ZooLock {
    String key();                                          // 锁的键
    long timeout() default 5 * 1000;                       // 锁等待超时，默认5秒
    TimeUnit timeUnit() default TimeUnit.MILLISECONDS;     // 时间单位，默认毫秒
}
```

**注解三要素理解**：

- `@Target(ElementType.METHOD)`：这个注解只能打在方法上，打在类上会报错。
- `@Retention(RetentionPolicy.RUNTIME)`：注解保留到运行时。如果改成 `SOURCE`，编译后就没了，AOP 运行时读不到。**自定义注解配合 AOP，必须用 RUNTIME**。
- 三个属性：`key`（锁名，必填）、`timeout`（等多久，超时放弃）、`timeUnit`（时间单位）。

### 6.2 `@LockKeyParam` —— 让锁 key 动态化

```java
@Target({ElementType.PARAMETER})       // 标在参数上
@Retention(RetentionPolicy.RUNTIME)
public @interface LockKeyParam {
    String[] fields() default {};     // 如果参数是对象，指定取它的哪个字段
}
```

为什么需要它？看两个场景：

```java
// 场景1：锁 key 固定，所有请求互斥
@ZooLock(key = "buy")
public void buy() { ... }

// 场景2：锁 key 要带参数，按用户互斥（不同用户不互斥，同一用户才互斥）
@ZooLock(key = "buy")
public void buy(@LockKeyParam String userId) { ... }
// userId=1 → key = /DISTRIBUTED_LOCK_buy/1
// userId=2 → key = /DISTRIBUTED_LOCK_buy/2
```

`@LockKeyParam` 标记的参数值会被拼接到锁 key 里，实现**细粒度锁**。如果参数是对象，还可以用 `fields` 指定取哪个字段：

```java
@ZooLock(key = "buy")
public void buy(@LockKeyParam({"id"}) User user) { ... }   // 取 user.id 拼到 key
```

---

## 七、AOP 切面：加锁/释放的核心

`ZooLockAspect.java` 是整个模块的核心，逐段看。

### 7.1 类声明与依赖注入

```java
@Aspect
@Component
@Slf4j
public class ZooLockAspect {
    private final CuratorFramework zkClient;
    private static final String KEY_PREFIX = "DISTRIBUTED_LOCK_";
    private static final String KEY_SEPARATOR = "/";

    @Autowired
    public ZooLockAspect(CuratorFramework zkClient) {
        this.zkClient = zkClient;
    }
}
```

- `@Aspect`：标记为切面类。
- `@Component`：注册成 Bean，让 Spring 管理。
- 构造器注入 `CuratorFramework`（第五节注册的 ZK 客户端）。
- 两个常量：锁 key 前缀 `DISTRIBUTED_LOCK_` 和分隔符 `/`（ZK 路径用 `/` 分隔）。

### 7.2 切点：拦截 `@ZooLock` 注解

```java
@Pointcut("@annotation(com.xkcoding.zookeeper.annotation.ZooLock)")
public void doLock() { }
```

切点表达式 `@annotation(...)` 表示：**所有标注了 `@ZooLock` 注解的方法**都是切点。这样不用一个个指定方法，加注解就自动被拦截。

### 7.3 环绕通知：加锁 → 执行 → 释放

```java
@Around("doLock()")
public Object around(ProceedingJoinPoint point) throws Throwable {
    MethodSignature signature = (MethodSignature) point.getSignature();
    Method method = signature.getMethod();
    Object[] args = point.getArgs();
    ZooLock zooLock = method.getAnnotation(ZooLock.class);
    if (StrUtil.isBlank(zooLock.key())) {
        throw new RuntimeException("分布式锁键不能为空");
    }
    String lockKey = buildLockKey(zooLock, method, args);
    InterProcessMutex lock = new InterProcessMutex(zkClient, lockKey);
    try {
        if (lock.acquire(zooLock.timeout(), zooLock.timeUnit())) {
            return point.proceed();         // 执行原方法
        } else {
            throw new RuntimeException("请勿重复提交");
        }
    } finally {
        lock.release();                    // 无论成功失败都释放
    }
}
```

**执行流程**（重点理解）：

1. 通过 `point` 拿到方法签名、参数、`@ZooLock` 注解。
2. 校验 `key` 非空。
3. `buildLockKey` 拼出完整锁路径（如 `/DISTRIBUTED_LOCK_buy/1`）。
4. `new InterProcessMutex(zkClient, lockKey)` 创建一把锁（对应 ZK 上一个临时顺序节点）。
5. `lock.acquire(timeout)` 尝试获取锁，超时未拿到返回 `false`。
6. 拿到锁 → `point.proceed()` 执行原方法；没拿到 → 抛"请勿重复提交"。
7. `finally` 里 `lock.release()` 释放锁——**无论正常返回还是抛异常都释放，防死锁**。

> 💡 前端类比：这就像 axios 拦截器——请求发出前（加锁）、请求返回后（释放）统一处理，业务代码不用管。`@Around` = 拦截器，`point.proceed()` = `next()` 放行。

### 7.4 构造动态锁 key

```java
private String buildLockKey(ZooLock lock, Method method, Object[] args) {
    StringBuilder key = new StringBuilder(KEY_SEPARATOR + KEY_PREFIX + lock.key());
    Annotation[][] parameterAnnotations = method.getParameterAnnotations();

    for (int i = 0; i < parameterAnnotations.length; i++) {
        for (Annotation annotation : parameterAnnotations[i]) {
            if (!annotation.annotationType().isInstance(LockKeyParam.class)) {
                continue;
            }
            String[] fields = ((LockKeyParam) annotation).fields();
            if (ArrayUtil.isEmpty(fields)) {
                // 基本类型参数：直接拼接值
                key.append(KEY_SEPARATOR).append(args[i]);
            } else {
                // 对象类型参数：反射取指定字段值
                for (String field : fields) {
                    Class<?> clazz = args[i].getClass();
                    Field declaredField = clazz.getDeclaredField(field);
                    declaredField.setAccessible(true);
                    Object value = declaredField.get(clazz);
                    key.append(KEY_SEPARATOR).append(value);
                }
            }
        }
    }
    return key.toString();
}
```

逻辑：
1. 先拼前缀：`/DISTRIBUTED_LOCK_buy`。
2. 遍历方法的每个参数的注解（`getParameterAnnotations()` 返回二维数组，每个参数可能有多个注解）。
3. 找到标了 `@LockKeyParam` 的参数：
   - 如果没指定 `fields`（基本类型如 String）→ 直接把参数值拼上。
   - 如果指定了 `fields`（对象类型如 User）→ 用**反射**取对象里指定字段的值拼上。

> ⚠️ 这里有个**隐藏 bug**：`declaredField.get(clazz)` 传的是 `Class` 对象而不是实例 `args[i]`，取静态字段才该传 Class，取实例字段应该传 `args[i]`。本 demo 对象字段场景会取到 null。真实使用时需修正为 `declaredField.get(args[i])`。

---

## 八、测试类：验证锁效果

测试类用"扣库存"场景验证三种情况：

### 8.1 不加锁（对照组）

```java
@Test
public void test() throws InterruptedException {
    IntStream.range(0, 10000).forEach(i -> executorService.execute(this::doBuy));
    TimeUnit.MINUTES.sleep(1);
    log.error("count值为{}", count);   // 结果不是 0，丢更新
}
```

10000 个线程并发 `count--`，结果不为 0。

### 8.2 手动加锁

```java
public void manualBuy() {
    InterProcessMutex lock = new InterProcessMutex(zkClient, "/buy");
    try {
        if (lock.acquire(1, TimeUnit.MINUTES)) {
            doBuy();
        }
    } finally {
        lock.release();
    }
}
```

手动 `new InterProcessMutex` + `acquire` + `release`，能用但**侵入业务代码**，每个要加锁的方法都得重复写。

### 8.3 AOP 注解加锁

```java
@ZooLock(key = "buy", timeout = 1, timeUnit = TimeUnit.MINUTES)
public void aopBuy(int userId) {
    doBuy();
}
```

只需一个注解，干净。但测试类里调用 AOP 有个坑——**测试类不是 Spring 代理对象，AOP 不生效**，需要手动代理：

```java
SpringBootDemoZookeeperApplicationTests target = new SpringBootDemoZookeeperApplicationTests();
AspectJProxyFactory factory = new AspectJProxyFactory(target);
factory.addAspect(new ZooLockAspect(zkClient));
SpringBootDemoZookeeperApplicationTests proxy = factory.getProxy();
IntStream.range(0, 10000).forEach(i -> executorService.execute(() -> proxy.aopBuy(i)));
```

> 💡 **为什么测试里要手动代理？** AOP 靠 Spring 创建代理对象实现，但 `this.aopBuy()` 是直接调原始对象，绕过代理。生产代码里只要从外部注入调用，Spring 自动用代理，不用手动处理。这是 AOP 最经典的坑（详见 `06-LogAop` 模块）。

---

## 九、运行与验证

### 9.1 准备 ZK 环境

```sh
# Docker 启动一个 ZK
docker run -d --name zk -p 2181:2181 zookeeper:3.5
```

### 9.2 运行测试

```sh
mvn test -Dtest=SpringBootDemoZookeeperApplicationTests#test
mvn test -Dtest=SpringBootDemoZookeeperApplicationTests#testAopLock
mvn test -Dtest=SpringBootDemoZookeeperApplicationTests#testManualLock
```

### 9.3 预期结果

| 测试 | count 最终值 | 说明 |
| --- | --- | --- |
| `test`（无锁） | ≠ 0 | 丢更新 |
| `testManualLock`（手动锁） | = 0 | 正确 |
| `testAopLock`（注解锁） | = 0 | 正确 |

---

## 十、动手练习

1. **观察丢更新**：把 `test` 方法的线程数改成 1000，看 count 偏差。
2. **加细粒度锁**：给 `aopBuy` 的 `userId` 加 `@LockKeyParam`，观察 ZK 节点路径变成 `/DISTRIBUTED_LOCK_buy/1`、`/buy/2`。
3. **模拟死锁释放**：在 `aopBuy` 里故意 `throw new RuntimeException()`，观察 `finally` 是否释放锁（ZK 节点是否删除）。
4. **修 bug**：把 `buildLockKey` 里 `declaredField.get(clazz)` 改成 `declaredField.get(args[i])`，测试对象参数场景。
5. **对比 Redis 锁**：思考如果改用 Redis 的 `SETNX` 实现同样功能，注解和切面要改哪里（提示：只换 `InterProcessMutex` 为 Redisson 的 `RLock`）。
6. **加可重入测试**：在 `aopBuy` 里再调一个 `@ZooLock(key="buy")` 的方法，验证 `InterProcessMutex` 是否支持可重入（同一线程可多次获取同一把锁）。

---

## 十一、本模块知识点总结（结合实际开发详解）

分布式锁是后端高并发场景的核心组件，本模块用 ZK + AOP 给出了优雅的实现。下面把关键知识点放到真实开发里讲透。

### 11.1 分布式锁的选型：ZK vs Redis vs 数据库

**实际开发中怎么选？**

| 方案 | 一致性 | 性能 | 适用场景 |
| --- | --- | --- | --- |
| **Zookeeper** | 强（CP） | 中 | 对正确性要求极高，如金融扣款、库存 |
| **Redis（Redisson）** | 最终一致（AP） | 高 | 大多数互联网场景，性能优先 |
| **数据库** | 强 | 低 | 低频、简单场景，不想引入中间件 |

**关键区别——CAP 取舍：**
- ZK 是 **CP** 系统：写操作要过半节点同意，保证强一致，但分区时宁可拒绝服务也不丢数据。锁的语义最严格。
- Redis 是 **AP** 系统：主从异步复制，主节点挂了从节点可能还没同步到锁数据，有极小概率双主导致锁失效。Redisson 用看门狗续期缓解，但无法 100% 杜绝。

**最佳实践：**
- 电商秒杀、库存扣减 → Redis（Redisson）够用，性能是第一位。
- 资金转账、对账 → ZK 或数据库，正确性优先。
- 不要用"自己手写 Redis SETNX"做生产锁，用 Redisson（解决了续期、可重入、释放原子性等问题）。

**常见坑：**
- 用 ZK 锁但 ZK 集群只有单节点——单点故障，整个锁体系崩溃。ZK 至少 3 节点奇数部署。
- 用 Redis 锁不设过期时间——客户端崩溃后锁永不释放，死锁。

### 11.2 ZK 分布式锁的原理：临时顺序节点

**为什么 ZK 锁可靠？** 因为它用的是"临时顺序节点"：

1. 客户端 A 想加锁 → 在 `/lock` 下创建临时顺序节点 `/lock/node000001`。
2. 客户端 B 来 → 创建 `/lock/node000002`。
3. 每个客户端检查自己是不是序号最小的节点：
   - 是 → 获得锁。
   - 否 → 监听前一个节点，前一个删了（释放锁）自己才被唤醒。

**这个设计的精妙之处：**

- **临时节点**：客户端连接断开，节点自动删除 → **防死锁**（客户端崩溃不会锁永久不释放）。
- **顺序节点**：排队而非抢占 → **防惊群**（不会所有客户端同时争抢，只有前一个的后继被唤醒）。
- **监听机制**：前驱释放才唤醒后继 → **公平锁**，避免饥饿。

> 💡 `InterProcessMutex` 就是 Curator 对上述流程的封装，可重入（同一线程多次 acquire 计数器+1，release -1，归零才真正释放）。

**常见坑：**
- 误用**临时节点**（非顺序）实现锁——所有客户端监听同一个节点，节点释放时全部被唤醒争抢，产生"惊群"，高并发下 ZK 压力骤增。
- 锁路径设计不合理，所有业务用同一个 key，导致全局串行，并发度归零。

### 11.3 注解 + AOP：让锁零侵入

本模块最值得学习的是**设计模式**：把重复的"加锁-执行-释放"逻辑用注解 + AOP 统一处理，业务方法只写业务。

**实际开发中这种模式随处可见：**
- `@Transactional`：事务（开启-执行-提交/回滚）
- `@Cacheable`：缓存（查缓存-执行-写缓存）
- `@RateLimiter`：限流（`demo-ratelimit-*` 模块）
- `@ZooLock`：分布式锁（本模块）

套路一致：定义注解 → 写切面 → 在切点前后织入横切逻辑。

**最佳实践：**
1. **切面要处理异常**：`finally` 释放资源，别让异常导致锁不释放（本模块做到了）。
2. **key 要可配置**：支持静态 key 和动态参数（本模块用 `@LockKeyParam` 实现）。
3. **超时要合理**：太短→高并发下大量请求失败；太长→线程阻塞堆积。根据业务 RT 设定。
4. **失败要友好**：拿不到锁别直接抛 RuntimeException，封装成业务异常返回"操作太频繁"提示。

**常见坑：**
- **AOP 自调用失效**：同一个类里 `methodA()` 调 `methodB()`（B 有 `@ZooLock`），B 的锁不生效，因为 `this` 不是代理对象。解决：把 B 拆到另一个类，或注入自身代理。
- **注解只对 public 方法生效**：`@ZooLock` 标在 private 方法上，AOP 拦截不到。
- **key 冲突**：不同业务用了相同的 key，导致互相误锁。

### 11.4 Curator 客户端的使用要点

**实际开发中用 Curator 的注意事项：**

1. **`CuratorFramework` 是单例**：整个应用共享一个客户端，本模块用 `@Bean` 注册，正确。
2. **重试策略要合理**：`ExponentialBackoffRetry`（指数退避）优于 `RetryOneTime`（只重试一次），避免压垮 ZK。重试次数别设太大（3-5 次足够）。
3. **连接要 start**：`client.start()` 必须调，否则不连接 ZK。本模块在 `@Bean` 方法里调了。
4. **优雅关闭**：生产环境应在应用关闭时 `client.close()`，可以用 `@PreDestroy`。
5. **版本对应**：Curator 和 ZK 版本必须匹配，否则启动报 `NoClassDefFoundError`。

**常见坑：**
- 忘了 `start()`，运行时报连接异常。
- ZK 地址写错（如写成 `127.0.0.1:2182`），启动卡住或超时。
- 把 `CuratorFramework` 当多例每次 new，连接数暴涨。

### 11.5 锁的粒度设计

**锁粒度是分布式锁设计的核心权衡：粒度越细，并发越高，但实现越复杂。**

```java
// 粒度太粗：全局串行，并发度=1
@ZooLock(key = "buy")

// 粒度合适：按用户互斥，不同用户并发
@ZooLock(key = "buy")
public void buy(@LockKeyParam String userId) {}

// 粒度更细：按用户+商品互斥
@ZooLock(key = "buy")
public void buy(@LockKeyParam String userId, @LockKeyParam String skuId) {}
```

**最佳实践：**
- 锁要保护的最小临界区，key 尽量带业务唯一标识（用户ID、订单ID）。
- 锁内代码尽量短，不要在锁里做耗时操作（网络调用、大计算），否则锁成为瓶颈。
- 能用乐观锁（版本号）就别用悲观锁，乐观锁不阻塞，并发更高。

**常见坑：**
- 锁了整个方法但方法里大部分代码不需要锁——应该只锁临界区。
- key 用了可变对象（如 List），hashCode 变化导致同一业务锁不到同一把锁。key 必须用不可变值。

### 11.6 测试 AOP 的正确姿势

本模块测试类用 `AspectJProxyFactory` 手动创建代理，这是因为测试环境里 `this` 不是 Spring 代理。

**实际开发中如何测试 AOP？**

1. **集成测试**（推荐）：用 `@SpringBootTest` 启动完整上下文，从容器拿 Bean 调用，AOP 自动生效。但本模块测试是调自身方法，所以不行。
2. **手动代理**（本模块做法）：`AspectJProxyFactory` 手动织入切面，适合单元测试切面逻辑。
3. **直接测切面**：`new ZooLockAspect(zkClient).around(mockPoint)`，Mock 一个 `ProceedingJoinPoint`，纯测切面逻辑，不依赖 Spring。

**最佳实践：** 生产代码里，被 `@ZooLock` 标注的方法要**从外部 Bean 调用**（注入的 Service），而不是 `this.method()`，这样代理才生效。

---

> 📌 **学习建议**：分布式锁是后端区别于前端的核心知识点之一。作为前端转后端的工程师，建议你重点理解三件事：①为什么单机锁不够（集群部署）②ZK 锁的原理（临时顺序节点）③注解+AOP 的设计模式（横切关注点）。这套"注解+切面"的模式在 Spring 里反复出现（事务、缓存、限流、日志），掌握一次，受用全程。另外，本模块的 `@ZooLock` 是个很好的练手项目——试着把它改造成基于 Redisson 的 `@RedisLock`，你会对"抽象与实现分离"有更深的体会。
