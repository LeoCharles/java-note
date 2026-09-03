# ThreadLocal 与异步编程

多线程环境下，**共享变量**的并发安全是核心难题（见 [40-多线程基础](40-多线程基础与线程安全.md)）。但有些场景我们并不需要「共享」，而是希望每个线程**各自拥有一份独立的副本**——这就是 `ThreadLocal` 的用武之地。再进一步，当任务需要拆分、编排、异步组合时，`ForkJoinPool` 和 `CompletableFuture` 提供了比裸线程池更强大的能力。本篇将这三者串联起来，讲透「线程隔离」与「异步编排」两条主线。

> 💡 阅读本篇前，建议先掌握 [40-多线程基础](40-多线程基础与线程安全.md) 的线程创建与同步机制，以及 [41-线程池与并发工具](41-线程池与并发工具.md) 的 `Executor` 框架，理解线程复用后，再看 `ThreadLocal` 的线程隔离会更顺畅。

---

## 一、ThreadLocal 是什么

`ThreadLocal` 叫**线程本地变量**——它的作用是：为每个使用该变量的线程提供一份**独立的副本**，线程之间互不干扰。

通俗理解：就像银行柜台的笔，每个柜台一支，各用各的，不存在抢笔的问题。`ThreadLocal` 不是「为了共享而同步」，而是「干脆不共享，各搞各的」。

```java
ThreadLocal<String> threadLocal = new ThreadLocal<>();
threadLocal.set("hello");              // 当前线程存值
System.out.println(threadLocal.get()); // hello，当前线程取值
threadLocal.remove();                  // 用完清理
```

> 💡 **常见误解**：`ThreadLocal` 不是用来解决多线程共享变量的同步问题的，它是用来**避免共享**的。每个线程操作的是自己的副本，天然无竞争。

---

## 二、ThreadLocal 的基本用法

### 2.1 set / get / remove

```java
ThreadLocal<Integer> tl = new ThreadLocal<>();

// ✅ 存值：绑定到当前线程
tl.set(100);

// ✅ 取值：取出当前线程的副本
Integer val = tl.get();
System.out.println(val);  // 100

// ✅ 清理：移除当前线程的副本（非常重要，后文详述）
tl.remove();

// ⚠️ get 在未 set 时返回 null（不是抛异常）
ThreadLocal<String> tl2 = new ThreadLocal<>();
System.out.println(tl2.get());  // null
```

### 2.2 初始值：重写 initialValue

有些场景希望第一次 `get` 时就有默认值，可以重写 `initialValue()`：

```java
// 方式一：匿名内部类重写 initialValue
ThreadLocal<SimpleDateFormat> tl = new ThreadLocal<SimpleDateFormat>() {
    @Override
    protected SimpleDateFormat initialValue() {
        return new SimpleDateFormat("yyyy-MM-dd");  // 每个线程一个实例
    }
};

// 方式二：Java 8 提供 withInitial（推荐，更简洁）
ThreadLocal<SimpleDateFormat> tl2 =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

SimpleDateFormat sdf = tl.get();  // 首次 get 时调用 initialValue 创建
```

### 2.3 线程隔离演示

下面这个例子最能体现「线程隔离」：两个线程各自 set/get，互不影响。

```java
ThreadLocal<String> tl = new ThreadLocal<>();

Thread t1 = new Thread(() -> {
    tl.set("线程1的数据");
    System.out.println("t1 取出：" + tl.get());  // 线程1的数据
    tl.remove();
});

Thread t2 = new Thread(() -> {
    tl.set("线程2的数据");
    System.out.println("t2 取出：" + tl.get());  // 线程2的数据
    tl.remove();
});

t1.start();
t2.start();
// 两个线程取出的都是各自 set 的值，互不干扰 ✅
```

---

## 三、ThreadLocal 的使用场景

### 3.1 场景一：SimpleDateFormat 线程安全

`SimpleDateFormat` 是**非线程安全**的，多线程共用一个实例会日期解析错乱：

```java
// ❌ 错误：多线程共享一个 SimpleDateFormat
SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
// 多个线程同时调用 sdf.parse(...) 会出现解析结果错乱、NumberFormatException

// ✅ 方案一：每个线程一个实例（用 ThreadLocal）
ThreadLocal<SimpleDateFormat> tl =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));
SimpleDateFormat mySdf = tl.get();  // 当前线程独占，无并发问题
```

> 📌 **开发规范**：`SimpleDateFormat` 几乎是 ThreadLocal 最经典的用法。也可以用 Java 8 的 `DateTimeFormatter`（天然线程安全）替代。

### 3.2 场景二：数据库连接管理

每个线程从连接池取一个连接，绑定到 ThreadLocal，整个方法调用链复用同一个连接，便于事务控制：

```java
// 简化版：数据库连接绑定到 ThreadLocal
public class ConnectionManager {
    private static ThreadLocal<Connection> connectionHolder = new ThreadLocal<>();

    public static Connection getConnection() throws SQLException {
        Connection conn = connectionHolder.get();
        if (conn == null) {           // 当前线程还没有连接，从池里取一个
            conn = DriverManager.getConnection("jdbc:mysql://localhost/db", "root", "123456");
            connectionHolder.set(conn);
        }
        return conn;                  // 同一线程内多次获取的是同一个连接 ✅
    }

    public static void close() throws SQLException {
        Connection conn = connectionHolder.get();
        if (conn != null) {
            conn.close();
            connectionHolder.remove();  // ⚠️ 用完必须 remove！
        }
    }
}
```

### 3.3 场景三：用户登录上下文（全链路传递）

Web 开发中，登录后要把当前用户信息贯穿整个请求链路（Controller → Service → DAO），用 ThreadLocal 存最方便：

```java
// 用户上下文
public class UserContext {
    private static final ThreadLocal<LoginUser> holder = new ThreadLocal<>();

    public static void set(LoginUser user) { holder.set(user); }
    public static LoginUser get() { return holder.get(); }
    public static void clear() { holder.remove(); }
}

class LoginUser {
    Long userId;
    String username;
    // 省略构造/getter
}

// 拦截器中设置（Spring 场景）
public class LoginInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse resp, Object h) {
        LoginUser user = parseToken(req.getHeader("token"));
        UserContext.set(user);   // 绑定到当前请求线程 ✅
        return true;
    }
    @Override
    public void afterCompletion(HttpServletRequest req, HttpServletResponse resp, Object h, Exception e) {
        UserContext.clear();     // ⚠️ 请求结束必须清理，否则内存泄漏！
    }
}

// 任意一层都能取到当前用户
class OrderService {
    void createOrder(Order order) {
        LoginUser user = UserContext.get();   // 无需层层传参 ✅
        order.setUserId(user.getUserId());
    }
}
```

> 💡 这就是「全链路上下文传递」的核心思想。Spring 的 `RequestContextHolder`、`SecurityContextHolder`（Spring Security）底层都是 ThreadLocal。

### 3.4 场景四：Session 管理

```java
// 简化版 Session 容器
public class SessionManager {
    private static final ThreadLocal<HttpSession> sessionHolder = new ThreadLocal<>();

    public static void bind(HttpSession session) { sessionHolder.set(session); }
    public static HttpSession current() { return sessionHolder.get(); }
    public static void unbind() { sessionHolder.remove(); }
}
```

---

## 四、ThreadLocalMap 内部结构

理解 ThreadLocal 的原理，关键是搞懂 **ThreadLocalMap**。

### 4.1 每个 Thread 持有自己的 ThreadLocalMap

`Thread` 类内部有一个字段 `threadLocals`：

```java
// Thread 类源码（简化）
class Thread {
    ThreadLocal.ThreadLocalMap threadLocals = null;  // 每个线程一个
}
```

当我们调用 `threadLocal.set(value)` 时，实际是**把值存进了当前线程的 `ThreadLocalMap`**，而不是存在 `ThreadLocal` 对象本身：

```
Thread 对象
  └── threadLocals (ThreadLocalMap)
        ├── Entry: key=threadLocal1（弱引用）, value=value1（强引用）
        ├── Entry: key=threadLocal2（弱引用）, value=value2（强引用）
        └── ...
```

> 💡 **关键认知**：`ThreadLocal` 只是个「钥匙」，真正的存储在每个线程自己的 `ThreadLocalMap` 里。所以不同线程用同一个 `ThreadLocal` 取到的值不同。

### 4.2 ThreadLocalMap 的 Entry

```java
// ThreadLocalMap 内部（简化）
static class ThreadLocalMap {
    static class Entry extends WeakReference<ThreadLocal<?>> {
        Object value;                       // value 是强引用！
        Entry(ThreadLocal<?> k, Object v) {
            super(k);   // key（ThreadLocal）是弱引用
            value = v;  // value 是强引用
        }
    }
}
```

这张表本质是一个 `Entry[]` 数组，key 是 `ThreadLocal` 对象的**弱引用**，value 是**强引用**。这个设计直接关系到内存泄漏问题，下一节详述。

---

## 五、内存泄漏问题（重点 ⭐⭐）

### 5.1 为什么会内存泄漏

梳理引用链：

```
Thread（强）→ ThreadLocalMap（强）→ Entry
                                  ├── key = ThreadLocal（弱引用）
                                  └── value = 实际值（强引用）
```

假设 `ThreadLocal` 外部没有强引用了（比如方法栈里的局部变量出了作用域）：

1. key 是弱引用，GC 时被回收，Entry 的 key 变成 `null`。
2. 但 **value 仍是强引用**，只要 Thread 还活着（线程池里线程长期存活），value 就不会被回收。
3. 这些 `key=null` 的 Entry 一直占着内存，形成**内存泄漏**。

```
Thread（长期存活）→ ThreadLocalMap → Entry(key=null, value=大对象)
                                       ↑ value 回收不掉，泄漏！
```

> ⚠️ **核心矛盾**：线程池场景下线程是长期存活的，ThreadLocalMap 也会长期存在。如果用完不 remove，value 永远回收不掉，最终 OOM。

### 5.2 JDK 的自救措施

`ThreadLocalMap` 在 `set`/`get` 时会顺带清理 `key=null` 的 Entry（称为「过期清理」），但这只是**被动清理**，不能完全依赖。如果之后再也不调用该 ThreadLocal 的 set/get，value 就永远泄漏。

### 5.3 正确做法：用完 remove

```java
ThreadLocal<BigObject> tl = new ThreadLocal<>();
try {
    tl.set(new BigObject());
    // 使用 tl.get() ...
} finally {
    tl.remove();   // ✅ 用完一定 remove，放在 finally 里
}
```

> 📌 **开发铁律**：ThreadLocal 的 `remove()` 必须放在 `finally` 块里调用，就像关流一样。Web 场景下通常在拦截器的 `afterCompletion` 里清理。

---

## 六、InheritableThreadLocal

普通 `ThreadLocal` 有个局限：**子线程拿不到父线程 set 的值**。

```java
ThreadLocal<String> tl = new ThreadLocal<>();
tl.set("父线程的值");
Thread child = new Thread(() -> {
    System.out.println(tl.get());  // null ❌ 子线程取不到
});
child.start();
```

`InheritableThreadLocal` 解决这个问题——子线程创建时会**拷贝**父线程的值：

```java
InheritableThreadLocal<String> itl = new InheritableThreadLocal<>();
itl.set("父线程的值");
Thread child = new Thread(() -> {
    System.out.println(itl.get());  // 父线程的值 ✅
});
child.start();
```

> ⚠️ **局限**：`InheritableThreadLocal` 只在**创建子线程时**拷贝一次。如果用线程池（线程提前创建好、被复用），后续父线程 set 的新值，线程池里的线程是拿不到的。线程池场景需要用阿里开源的 `TransmittableThreadLocal`（TTL）解决全链路传递。

---

## 七、ForkJoinPool 分治框架

`ForkJoinPool`（Java 7 引入）是专门处理**分治任务**的线程池，核心思想是把大任务拆成小任务，最后合并结果。

### 7.1 分治思想

```
大任务（1~100 求和）
  ├── fork：拆成 1~50 和 51~100
  │     ├── 1~50 再拆成 1~25 和 26~50
  │     └── 51~100 再拆成 51~75 和 76~100
  └── join：把子任务结果合并
```

### 7.2 work-stealing 工作窃取

普通线程池：所有线程共享一个任务队列，存在竞争。
ForkJoinPool：**每个线程有自己的双端队列**，线程把自己 fork 的子任务压入自己队列的一端，从另一端取任务执行（LIFO，利于缓存命中）。当自己的队列空了，就去**别的线程队列的另一端偷任务**（FIFO），这叫工作窃取。

```
线程A的队列：[t1, t2, t3] ← 自己从这头取（LIFO）
                          ← 别的线程从这头偷（FIFO）
```

> 💡 工作窃取的好处：充分利用空闲线程，减少竞争，特别适合子任务量不均匀的分治场景。

### 7.3 RecursiveTask 与 RecursiveAction

- `RecursiveTask<V>`：有返回值的分治任务，需重写 `compute()`。
- `RecursiveAction`：无返回值的分治任务。

经典例子：大数组求和

```java
import java.util.concurrent.*;

// 有返回值的分治任务
class SumTask extends RecursiveTask<Long> {
    private final int[] array;
    private final int start;
    private final int end;
    private static final int THRESHOLD = 10000;  // 拆分阈值

    SumTask(int[] array, int start, int end) {
        this.array = array;
        this.start = start;
        this.end = end;
    }

    @Override
    protected Long compute() {
        int length = end - start;
        if (length <= THRESHOLD) {
            // 任务足够小，直接计算
            long sum = 0;
            for (int i = start; i < end; i++) sum += array[i];
            return sum;
        }
        // 拆分
        int mid = start + length / 2;
        SumTask left = new SumTask(array, start, mid);
        SumTask right = new SumTask(array, mid, end);
        left.fork();            // 异步执行左任务
        long rightResult = right.compute();  // 同步执行右任务（当前线程不闲着）
        long leftResult = left.join();       // 等待左任务完成
        return leftResult + rightResult;     // 合并结果 ✅
    }
}

// 使用
public class ForkJoinDemo {
    public static void main(String[] args) throws Exception {
        int[] array = new int[100_0000];
        for (int i = 0; i < array.length; i++) array[i] = i + 1;

        ForkJoinPool pool = new ForkJoinPool();
        SumTask task = new SumTask(array, 0, array.length);
        Long result = pool.invoke(task);   // 提交并等待
        System.out.println("总和：" + result);  // 500000500000
        pool.shutdown();
    }
}
```

> 💡 `fork()` 是异步提交，`join()` 是阻塞等待结果。`compute()` 里一边 fork 一边直接 compute 另一半，是为了让当前线程不闲着，这是 ForkJoin 的常见写法。

---

## 八、CompletableFuture 异步编排

`CompletableFuture`（Java 8）是异步编排的利器，相比 `Future` 只能阻塞 `get()`，它可以**链式组合**多个异步任务。本篇侧重「组合编排」，基础创建见 [41-线程池与并发工具](41-线程池与并发工具.md)。

### 8.1 串行编排 thenCompose

任务 A 完成后，把结果传给任务 B，B 也返回 `CompletableFuture`：

```java
// 查用户 → 查订单（依赖用户ID）
CompletableFuture<User> getUser = CompletableFuture.supplyAsync(() -> findUser(1L));
CompletableFuture<Order> orderFuture = getUser.thenCompose(user ->
    CompletableFuture.supplyAsync(() -> findOrder(user.getId()))
);
Order order = orderFuture.get();  // 串行：先查用户，再查订单 ✅
```

> 💡 `thenCompose` 的回调返回的是 `CompletableFuture`，会「拍平」成单一 future，避免 `CompletableFuture<CompletableFuture<Order>>` 的嵌套。

### 8.2 并行合并 thenCombine

两个独立任务并行执行，完成后合并各自结果：

```java
// 并行查商品信息和库存，合并成详情
CompletableFuture<Product> productFuture =
    CompletableFuture.supplyAsync(() -> getProduct(1L));
CompletableFuture<Integer> stockFuture =
    CompletableFuture.supplyAsync(() -> getStock(1L));

CompletableFuture<ProductDetail> detailFuture =
    productFuture.thenCombine(stockFuture, (product, stock) -> {
        ProductDetail detail = new ProductDetail();
        detail.setProduct(product);
        detail.setStock(stock);
        return detail;
    });
ProductDetail detail = detailFuture.get();  // 两个任务并行，合并结果 ✅
```

### 8.3 多任务 allOf / anyOf

```java
// allOf：等所有任务都完成
CompletableFuture<String> f1 = CompletableFuture.supplyAsync(() -> queryServiceA());
CompletableFuture<String> f2 = CompletableFuture.supplyAsync(() -> queryServiceB());
CompletableFuture<String> f3 = CompletableFuture.supplyAsync(() -> queryServiceC());

CompletableFuture<Void> all = CompletableFuture.allOf(f1, f2, f3);
all.join();  // 阻塞等三个都完成
// 此时三个 future 都已完成，分别取结果
String r1 = f1.get();
String r2 = f2.get();
String r3 = f3.get();

// anyOf：任一任务完成即返回
CompletableFuture<Object> any = CompletableFuture.anyOf(f1, f2, f3);
Object firstResult = any.get();  // 最先完成的那个的结果 ✅
```

> ⚠️ `allOf`/`anyOf` 本身返回的 future 不携带结果（`allOf` 返回 `Void`），需要从各个子 future 分别 `get()` 取结果。

### 8.4 自定义线程池运行

默认 `supplyAsync` 用 `ForkJoinPool.commonPool()`，**线程数 = CPU 核数 - 1**，高并发下不够用。生产环境必须传自定义线程池：

```java
ExecutorService pool = Executors.newFixedThreadPool(10);

CompletableFuture<String> f = CompletableFuture.supplyAsync(() -> {
    // 这个任务跑在自定义线程池里
    return doWork();
}, pool);   // ✅ 第二个参数指定线程池

// 链式调用也会沿用这个线程池（或调用线程）
CompletableFuture<String> f2 = f.thenApplyAsync(s -> s + "!", pool);

pool.shutdown();
```

> 📌 **生产规范**：IO 密集型异步任务（查库、调远程接口）不要用默认 commonPool，务必自定义线程池，线程数按 `CPU 核数 * 2` 或更高估算，否则任务会排队甚至饥饿。

---

## ⚠️ 重点

### 重点 1：ThreadLocal 的本质是「不共享」⭐⭐⭐

```java
// ThreadLocal 不是给所有线程共享一个值，而是每个线程各一份
ThreadLocal<Integer> tl = new ThreadLocal<>();
// 线程A set(1)，线程B set(2)，互不影响 ✅
```

> 💡 面试常问「ThreadLocal 怎么解决并发安全」——答：它**不解决共享**，而是**避免共享**，每个线程操作自己的副本，从源头消除竞争。

### 重点 2：ThreadLocalMap 的 key 是弱引用、value 是强引用 ⭐⭐⭐

```java
// ThreadLocalMap.Entry
//   key = ThreadLocal（弱引用）→ 外部无强引用时被 GC
//   value = 实际值（强引用）→ Thread 活着就不会被回收 → 泄漏！
```

> ⚠️ 这就是内存泄漏的根源。线程池场景下线程长期存活，value 回收不掉，最终可能 OOM。

### 重点 3：用完必须 remove ⭐⭐⭐

```java
ThreadLocal<BigObject> tl = new ThreadLocal<>();
try {
    tl.set(new BigObject());
    // 业务逻辑
} finally {
    tl.remove();   // ✅ finally 里清理，铁律
}
```

> 📌 不 remove 的后果：① 内存泄漏；② 线程池复用线程时，下一个任务会读到上一个任务残留的脏数据，产生诡异 bug。

### 重点 4：InheritableThreadLocal 在线程池下失效 ⭐⭐

```java
InheritableThreadLocal<String> itl = new InheritableThreadLocal<>();
itl.set("父值");

ExecutorService pool = Executors.newFixedThreadPool(2);
// 线程池预先创建好线程，创建时拷贝了父值
pool.submit(() -> System.out.println(itl.get()));  // 父值（首次可能取到）

itl.set("新父值");  // 之后父线程改了
pool.submit(() -> System.out.println(itl.get()));  // ❌ 可能还是旧值，因为线程已被复用
```

> ⚠️ 线程池场景的全链路上下文传递，要用 `TransmittableThreadLocal`（阿里 TTL 框架），它通过装饰 Runnable 在任务提交时快照、执行前重放、执行后清理。

### 重点 5：ForkJoin 适合可分治的 CPU 密集任务 ⭐⭐

```java
// ✅ 适合：大数组求和、归并排序、矩阵运算（任务可均匀拆分）
// ❌ 不适合：IO 密集任务（查库、调接口），线程会大量阻塞，工作窃取优势丧失
```

### 重点 6：CompletableFuture 默认用 commonPool ⭐⭐

```java
// ❌ 默认 commonPool 线程数 = CPU-1，IO 任务会排队
CompletableFuture.supplyAsync(() -> httpCall());

// ✅ 传自定义线程池
CompletableFuture.supplyAsync(() -> httpCall(), myPool);
```

---

## 💻 实战案例

### 案例 1：ThreadLocal 全链路传递用户上下文（电商后台）⭐⭐⭐

电商系统中，登录用户信息要从网关一路传到 DAO。用 ThreadLocal 避免层层传参：

```java
// 登录用户上下文
public class UserContext {
    private static final ThreadLocal<LoginUser> HOLDER = new ThreadLocal<>();

    public static void set(LoginUser u) { HOLDER.set(u); }
    public static LoginUser get() { return HOLDER.get(); }
    public static Long getUserId() {
        LoginUser u = HOLDER.get();
        return u == null ? null : u.getUserId();
    }
    public static void clear() { HOLDER.remove(); }
}

class LoginUser {
    private Long userId;
    private String username;
    private String tenantId;   // 多租户
    public LoginUser(Long userId, String username, String tenantId) {
        this.userId = userId; this.username = username; this.tenantId = tenantId;
    }
    public Long getUserId() { return userId; }
    public String getTenantId() { return tenantId; }
}

// 网关过滤器：解析 token 后塞入上下文
public class AuthFilter {
    public void doFilter(HttpServletRequest req, HttpServletResponse resp) {
        try {
            String token = req.getHeader("Authorization");
            LoginUser user = parseToken(token);   // 解析 JWT
            UserContext.set(user);                // ✅ 绑定到当前线程
            // 后续业务...
        } finally {
            UserContext.clear();                  // ⚠️ 请求结束清理
        }
    }
}

// Service 层直接取，无需参数传递
class OrderService {
    public void createOrder(Order order) {
        Long uid = UserContext.getUserId();       // ✅ 任意层都能取
        order.setUserId(uid);
        order.setTenantId(UserContext.get().getTenantId());
        orderDao.insert(order);
    }
}
```

> 📌 这是真实后台系统最常见的 ThreadLocal 用法。Spring Security 的 `SecurityContextHolder`、Hibernate 的 `TenantIdentifier` 都是同款思路。

### 案例 2：ThreadLocal 存数据库连接（事务控制）⭐⭐

一个业务方法里调多个 DAO，要用同一个连接才能控制事务：

```java
public class TransactionManager {
    private static final ThreadLocal<Connection> CONN_HOLDER = new ThreadLocal<>();

    // 开启事务
    public static void begin() throws SQLException {
        Connection conn = DataSourceUtils.getConnection();
        conn.setAutoCommit(false);
        CONN_HOLDER.set(conn);    // 绑定到当前线程 ✅
    }

    // 获取当前线程的连接
    public static Connection current() {
        return CONN_HOLDER.get();
    }

    // 提交
    public static void commit() throws SQLException {
        Connection conn = CONN_HOLDER.get();
        if (conn != null) {
            conn.commit();
            conn.close();
        }
    }

    // 回滚
    public static void rollback() {
        try {
            Connection conn = CONN_HOLDER.get();
            if (conn != null) conn.rollback();
        } catch (SQLException ignored) {
        } finally {
            try {
                Connection conn = CONN_HOLDER.get();
                if (conn != null) conn.close();
            } catch (SQLException ignored) {}
        }
    }

    // 清理
    public static void close() {
        CONN_HOLDER.remove();   // ⚠️ 一定要清理
    }
}

// 使用：转账
class AccountService {
    public void transfer(Long from, Long to, double money) {
        try {
            TransactionManager.begin();
            accountDao.subtract(from, money);   // 用 TransactionManager.current()
            accountDao.add(to, money);
            TransactionManager.commit();
        } catch (Exception e) {
            TransactionManager.rollback();
        } finally {
            TransactionManager.close();   // ✅ 清理 ThreadLocal
        }
    }
}
```

> 💡 Spring 的 `@Transactional` 底层 `DataSourceTransactionManager` 正是用 ThreadLocal 绑定 `ConnectionHolder`，保证同事务内多 DAO 用同一连接。

### 案例 3：SimpleDateFormat 线程安全方案对比 ⭐⭐

```java
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.concurrent.*;

public class DateFormatDemo {
    // ❌ 方案一：共享实例，多线程下解析错乱
    static SimpleDateFormat unsafe = new SimpleDateFormat("yyyy-MM-dd");

    // ✅ 方案二：ThreadLocal 每线程一份
    static ThreadLocal<SimpleDateFormat> safe =
        ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(5);
        for (int i = 0; i < 5; i++) {
            pool.submit(() -> {
                try {
                    // ❌ 不安全
                    // Date d = unsafe.parse("2026-01-01");
                    // ✅ 安全
                    Date d = safe.get().parse("2026-01-01");
                    System.out.println(Thread.currentThread().getName() + " -> " + d);
                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    safe.remove();   // ⚠️ 清理
                }
            });
        }
        pool.shutdown();
    }
}
```

> 💡 Java 8+ 更推荐直接用 `DateTimeFormatter`，它本身线程安全，无需 ThreadLocal 包装。

### 案例 4：ForkJoin 计算大数组求和（金融风控批量计算）⭐⭐

金融风控要对百万级账户做批量计算，用 ForkJoin 并行加速：

```java
import java.util.concurrent.*;

class RiskSumTask extends RecursiveTask<Double> {
    private final double[] amounts;
    private final int start, end;
    private static final int THRESHOLD = 50000;

    RiskSumTask(double[] amounts, int start, int end) {
        this.amounts = amounts; this.start = start; this.end = end;
    }

    @Override
    protected Double compute() {
        if (end - start <= THRESHOLD) {
            double sum = 0;
            for (int i = start; i < end; i++) sum += amounts[i];
            return sum;
        }
        int mid = start + (end - start) / 2;
        RiskSumTask left = new RiskSumTask(amounts, start, mid);
        RiskSumTask right = new RiskSumTask(amounts, mid, end);
        left.fork();
        double rightVal = right.compute();
        double leftVal = left.join();
        return leftVal + rightVal;
    }
}

public class RiskBatchDemo {
    public static void main(String[] args) {
        double[] amounts = new double[500_0000];
        for (int i = 0; i < amounts.length; i++) amounts[i] = Math.random() * 1000;
        ForkJoinPool pool = new ForkJoinPool();
        try {
            double total = pool.invoke(new RiskSumTask(amounts, 0, amounts.length));
            System.out.println("总敞口：" + total);
        } finally {
            pool.shutdown();
        }
    }
}
```

### 案例 5：CompletableFuture 并行查询多个服务聚合结果（电商商品详情页）⭐⭐⭐

商品详情页要同时查商品基础信息、价格、库存、评价、推荐，串行查要 1 秒，并行查只要最慢的那个的时间：

```java
import java.util.concurrent.*;

class ProductDetailDemo {
    static ExecutorService pool = Executors.newFixedThreadPool(8);

    static String queryProduct(long id)   { sleep(100); return "商品" + id; }
    static String queryPrice(long id)      { sleep(150); return "¥99"; }
    static String queryStock(long id)      { sleep(80);  return "库存100"; }
    static String queryComment(long id)    { sleep(200); return "好评99%"; }
    static String queryRecommend(long id)  { sleep(120); return "猜你喜欢"; }

    public static void main(String[] args) throws Exception {
        long id = 1L;
        long start = System.currentTimeMillis();

        // 五个查询并行
        CompletableFuture<String> p1 = CompletableFuture.supplyAsync(() -> queryProduct(id), pool);
        CompletableFuture<String> p2 = CompletableFuture.supplyAsync(() -> queryPrice(id), pool);
        CompletableFuture<String> p3 = CompletableFuture.supplyAsync(() -> queryStock(id), pool);
        CompletableFuture<String> p4 = CompletableFuture.supplyAsync(() -> queryComment(id), pool);
        CompletableFuture<String> p5 = CompletableFuture.supplyAsync(() -> queryRecommend(id), pool);

        // 等全部完成
        CompletableFuture.allOf(p1, p2, p3, p4, p5).join();

        StringBuilder page = new StringBuilder();
        page.append(p1.get()).append("\n")
            .append(p2.get()).append("\n")
            .append(p3.get()).append("\n")
            .append(p4.get()).append("\n")
            .append(p5.get());
        System.out.println(page);
        System.out.println("耗时：" + (System.currentTimeMillis() - start) + "ms");
        // 串行要 650ms，并行约 200ms（最慢的那个）✅

        pool.shutdown();
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

> 📌 这是真实电商详情页的并行聚合模式。注意：外部接口超时要设兜底，避免某个服务慢拖垮整页——用 `orTimeout` 或 `completeExceptionally`（Java 9+）控制。

### 案例 6：CompletableFuture 串行+并行混合编排（订单创建流程）⭐⭐

下单流程：先校验用户（串行），再并行查优惠券和库存，最后合并创建订单：

```java
ExecutorService pool = Executors.newFixedThreadPool(8);

// 1. 串行：校验用户 → 得到 userId
CompletableFuture<Long> checkUser = CompletableFuture.supplyAsync(() -> {
    // 校验 token，返回 userId
    return 1001L;
}, pool);

// 2. 并行：拿到 userId 后，同时查优惠券和库存
CompletableFuture<String> couponFuture = checkUser.thenComposeAsync(uid ->
    CompletableFuture.supplyAsync(() -> "优惠券：满100减20", pool), pool);

CompletableFuture<Integer> stockFuture = checkUser.thenComposeAsync(uid ->
    CompletableFuture.supplyAsync(() -> 50, pool), pool);

// 3. 合并：优惠券 + 库存 → 创建订单
CompletableFuture<String> orderFuture = couponFuture.thenCombine(stockFuture,
    (coupon, stock) -> "订单创建成功：" + coupon + "，库存" + stock);

System.out.println(orderFuture.get());  // ✅ 串行+并行混合编排
pool.shutdown();
```

---

## 🚀 新版本补充

### Java 9：CompletableFuture 超时与延迟

```java
// Java 9+：orTimeout 超时自动异常完成
CompletableFuture<String> f = CompletableFuture.supplyAsync(() -> slowCall())
    .orTimeout(2, TimeUnit.SECONDS);   // 2 秒没完成就抛 TimeoutException

// completeOnTimeout：超时给默认值
CompletableFuture<String> f2 = CompletableFuture.supplyAsync(() -> slowCall())
    .completeOnTimeout("默认值", 2, TimeUnit.SECONDS);

// delayedExecutor：延迟执行
CompletableFuture<String> delayed = CompletableFuture.supplyAsync(
    () -> "延迟1秒后执行",
    CompletableFuture.delayedExecutor(1, TimeUnit.SECONDS)
);
```

> 💡 Java 8 没有内置超时控制，需自己用 `get(timeout)` 或 `ScheduledExecutor` 兜底。

### Java 9：VarHandle 替代 Unsafe（ThreadLocal 底层）

ThreadLocalMap 内部在 Java 9+ 逐步用 `VarHandle` 替代 `sun.misc.Unsafe` 做原子操作，语义更安全，但对使用者 API 无影响。

### Java 19+：虚拟线程与 ThreadLocal

虚拟线程（`Thread.ofVirtual()`）下，每个虚拟线程也持有 ThreadLocal，但**虚拟线程数量可能极多（百万级）**，ThreadLocal 的内存开销会被放大。Java 19+ 提供了 `Scoped Values`（预览特性）作为 ThreadLocal 的轻量替代，适合虚拟线程场景。

```java
// Java 21+ ScopedValue（预览/孵化阶段，了解即可）
// private static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();
// ScopedValue.where(CURRENT_USER, user).run(() -> service.doWork());
```

> ⚠️ 虚拟线程场景下慎用 ThreadLocal，尤其不要给每个虚拟线程都塞大对象，百万线程 × 大 value = 灾难。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| ThreadLocal 本质 | 每个线程一份独立副本，避免共享 |
| 基本 API | `set` / `get` / `remove` / `withInitial` |
| 典型场景 | SimpleDateFormat、DB 连接、用户上下文、Session |
| 内部结构 | 每个 Thread 持有 ThreadLocalMap，key=ThreadLocal（弱引用），value（强引用） |
| 内存泄漏 | key 被 GC 后 value 仍强引用，线程池下泄漏 |
| 解决泄漏 | 用完 `finally` 里 `remove()` |
| InheritableThreadLocal | 子线程创建时拷贝父值；线程池下失效 |
| ForkJoinPool | 分治 + 工作窃取，适合 CPU 密集可分治任务 |
| RecursiveTask | 有返回值的分治任务，重写 `compute` |
| CompletableFuture 串行 | `thenCompose` 链式依赖 |
| CompletableFuture 并行 | `thenCombine` 合并两个、`allOf`/`anyOf` 合并多个 |
| 自定义线程池 | `supplyAsync(task, pool)`，IO 任务别用 commonPool |

---

## 学习建议

1. **先动手验证线程隔离**：写两个线程对同一个 ThreadLocal set 不同值，打印 get 结果，亲眼看到「互不影响」，比看十遍概念都管用。
2. **把内存泄漏画出来**：在纸上画出 Thread→Map→Entry(key 弱/value 强) 的引用链，标出 GC 后 key=null 但 value 还在的场景，理解了引用链就理解了为什么必须 remove。
3. **在项目里用一次用户上下文**：哪怕是个小 demo，也按「拦截器 set → Service get → finally remove」的完整链路写一遍，这是后台开发的高频操作，形成肌肉记忆。
4. **CompletableFuture 多写组合**：把 thenCompose、thenCombine、allOf 各写一个例子，再尝试串行+并行混合编排，体会「异步任务像流水线一样组合」的感觉，这是微服务并行聚合的核心技能。
5. **区分 ForkJoin 与普通线程池的适用边界**：ForkJoin 不是万能的，它适合可均匀拆分的 CPU 密集任务；IO 密集任务用普通线程池 + CompletableFuture 更合适，别为了用而用。
