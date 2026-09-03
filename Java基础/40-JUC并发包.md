# JUC并发包

Java 从 1.0 版本提供了 `synchronized` 关键字和 `volatile` 实现线程同步，但基于「锁」的同步机制在高并发场景下性能瓶颈明显。Java 5（JDK 1.5）由 Doug Lea 大神主导引入了 `java.util.concurrent`（简称 JUC）包，提供了一大批经过充分优化的并发工具：线程安全的集合、原子类、同步工具类、阻塞队列等，极大简化了并发编程。掌握 JUC 是从「会写多线程」到「写好高并发程序」的必经之路。

> 💡 在阅读本篇前，建议先看 [38-多线程基础](38-多线程基础.md) 和 [39-锁与volatile](39-锁与volatile.md)，理解线程生命周期、`synchronized`/`volatile` 的基本原理，再来学习 JUC 会更顺畅。

---

## 一、JUC 包概述

`java.util.concurrent` 包结构：

```
java.util.concurrent
├── 并发集合
│   ├── ConcurrentHashMap      // 线程安全的 HashMap
│   ├── CopyOnWriteArrayList   // 写时复制的 ArrayList
│   ├── ConcurrentLinkedQueue  // 无锁并发队列
│   └── BlockingQueue 接口      // 阻塞队列（生产者消费者）
│       ├── ArrayBlockingQueue
│       └── LinkedBlockingQueue
├── 原子类（java.util.concurrent.atomic）
│   ├── AtomicInteger / AtomicLong / AtomicBoolean
│   ├── AtomicReference
│   └── AtomicStampedReference
├── 同步工具类
│   ├── CountDownLatch         // 倒计时锁存器
│   ├── CyclicBarrier          // 循环栅栏
│   ├── Semaphore              // 信号量
│   └── Exchanger              // 交换器
└── 并发工具
    ├── TimeUnit               // 时间单位枚举
    └── ThreadLocalRandom     // 并发安全的随机数
```

> 💡 JUC 的核心设计思想：**尽量减小锁的粒度**（甚至无锁化），用 CAS（Compare-And-Swap）等硬件级原语替代重量级锁，从而在高并发下获得更好的吞吐量。

---

## 二、ConcurrentHashMap ⭐⭐⭐⭐

`ConcurrentHashMap` 是 JUC 中最重要的并发容器，是**线程安全的 HashMap**。面试高频、开发高频，必须吃透。

### 2.1 为什么不用 HashMap 和 Hashtable？

先看 `HashMap` 在多线程下的问题：

```java
import java.util.HashMap;
import java.util.Map;

// ❌ HashMap 多线程下会死循环（JDK 1.7 扩容时链表成环）
//    或数据丢失（JDK 1.8 并发 put 覆盖）
Map<String, String> map = new HashMap<>();
for (int i = 0; i < 10; i++) {
    new Thread(() -> {
        for (int j = 0; j < 1000; j++) {
            map.put(Thread.currentThread().getName() + "-" + j, "v");
        }
    }).start();
}
// 结果：数据丢失、甚至抛 ConcurrentModificationException
```

再看 `Hashtable`（或 `Collections.synchronizedMap`）：

```java
import java.util.Hashtable;
// Hashtable 用 synchronized 修饰每个方法，锁的是整个表对象
Hashtable<String, String> table = new Hashtable<>();
// put 时：public synchronized V put(K key, V value) → 整个表加锁
// 问题：100 个线程只要有一个在 put，其余 99 个全阻塞，效率极低
```

| 对比项 | HashMap | Hashtable | ConcurrentHashMap |
| :--- | :--- | :--- | :--- |
| 线程安全 | ❌ 不安全 | ✅ 安全 | ✅ 安全 |
| 并发性能 | — | 差（整表锁） | 好（分段锁/CAS） |
| null key/value | 允许 | 不允许 | 不允许 |
| 推荐使用 | 单线程 | 不推荐 | **多线程首选** |

> ⚠️ `ConcurrentHashMap` 的 key 和 value 都**不能为 null**。`HashMap` 允许 null 是因为单线程下不会有歧义；而并发场景下 `get(key)` 返回 null 时无法区分「不存在」还是「值为 null」（这是 `ConcurrentHashMap` 设计者有意为之）。

### 2.2 JDK 1.7：分段锁 Segment

JDK 1.7 的 `ConcurrentHashMap` 采用**分段锁（Segment）**设计：

```
ConcurrentHashMap（JDK 1.7）
├── Segment[]（默认 16 个段，每个段是一把锁）
│   ├── Segment 0 → HashEntry[]（一个小 HashMap）
│   ├── Segment 1 → HashEntry[]
│   └── ... Segment 15
```

- 整个表被分成 16 个 `Segment`，每个 `Segment` 是一把独立的锁
- 线程 A 操作 Segment 0，线程 B 操作 Segment 1，**互不阻塞**
- 理论并发度 = Segment 数量（默认 16），即最多 16 个线程同时写

> 💡 JDK 1.7 的分段锁是「锁分离」思想的经典实现，但在极端高并发（超过 16 线程同时写）时仍会竞争。

### 2.3 JDK 1.8：CAS + synchronized 锁单个桶

JDK 1.8 做了重大重构，**废弃 Segment**，改为 `CAS + synchronized` 锁单个桶节点：

```
ConcurrentHashMap（JDK 1.8）
├── Node[] table（一个数组，每个位置叫一个"桶"）
│   ├── 桶 0 → Node → Node → Node（链表）
│   ├── 桶 1 → null
│   ├── 桶 2 → TreeBin（红黑树，链表长度 ≥ 8 转树）
│   └── ...
```

- **put 流程**：
  1. 计算 hash，定位到桶
  2. 桶为空 → CAS 写入（无锁）
  3. 桶非空 → `synchronized` 锁住桶头节点，链表/红黑树插入
  4. 链表长度 ≥ 8 且数组容量 ≥ 64 → 转红黑树

- **get 流程**：全程无锁，用 `volatile` 保证可见性

> ⚠️ **JDK 1.8 的关键改进**：锁粒度从 Segment（一段）细化到 Node（一个桶），并发度从 16 提升到数组长度；空桶用 CAS 完全无锁；读操作全程无锁。这是面试重点。

### 2.4 常用 API

```java
import java.util.concurrent.ConcurrentHashMap;

ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();

// 基本操作（和 HashMap 一样）
map.put("a", 1);
map.putIfAbsent("b", 2);      // 不存在才放入 ✅
map.putIfAbsent("b", 99);     // 已存在，不覆盖，值仍为 2
System.out.println(map.get("b"));  // 2

// 原子复合操作（线程安全）
map.computeIfAbsent("c", k -> k.length());  // 不存在则计算
map.compute("a", (k, v) -> v + 10);          // 原子更新
map.merge("a", 5, Integer::sum);             // 原子合并：a = a + 5
System.out.println(map.get("a"));  // 16

// ❌ 不能存 null
// map.put("x", null);  // 抛 NullPointerException
```

> 📌 **规范**：多线程下需要 `HashMap` 功能时，一律用 `ConcurrentHashMap`，不要用 `Hashtable`（已过时）或 `Collections.synchronizedMap`（性能差）。

---

## 三、原子类 ⭐⭐⭐

`java.util.concurrent.atomic` 包提供了一系列基于 CAS 的原子操作类，替代 `synchronized` 做基本类型的线程安全操作。

### 3.1 基本原子类

```java
import java.util.concurrent.atomic.*;

// AtomicInteger：原子 int
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();   // ++i，原子操作 ✅
count.getAndIncrement();    // i++，原子操作
count.addAndGet(10);        // 加 10
count.compareAndSet(11, 100);  // 如果当前值==11，则设为100，返回 true ✅
System.out.println(count.get());  // 100

// AtomicLong：原子 long（如统计接口调用次数）
AtomicLong total = new AtomicLong(0);
total.addAndGet(1000L);

// AtomicBoolean：原子布尔（如初始化标志）
AtomicBoolean initialized = new AtomicBoolean(false);

// AtomicReference：原子引用（任意对象）
AtomicReference<String> ref = new AtomicReference<>("hello");
ref.compareAndSet("hello", "world");  // ✅
System.out.println(ref.get());  // world
```

对比 `synchronized` 做计数：

```java
// ❌ 用 synchronized：重，性能差
class Counter1 {
    private int count = 0;
    public synchronized void increment() { count++; }
}

// ✅ 用 AtomicInteger：轻，无锁
class Counter2 {
    private AtomicInteger count = new AtomicInteger(0);
    public void increment() { count.incrementAndGet(); }
}
```

### 3.2 CAS 原理（Compare-And-Swap）

CAS 是原子类的底层原理，也是整个 JUC 无锁编程的基石：

```
CAS(V, Expected, New)
  V：内存中的值
  Expected：期望值（旧值）
  New：要写入的新值

当且仅当 V == Expected 时，才将 V 更新为 New，返回 true
否则说明已被别的线程改过，返回 false（这次 CAS 失败）
```

```java
// AtomicInteger.incrementAndGet() 的 CAS 伪流程
public final int incrementAndGet() {
    int oldValue;
    do {
        oldValue = get();        // 读取当前值
    } while (!compareAndSet(oldValue, oldValue + 1));  // CAS 自旋
    return oldValue + 1;
}
// 如果 CAS 失败（别的线程先改了），就重新读、再 CAS，直到成功
```

> 💡 CAS 是**乐观锁**思想：假设没有冲突，先操作，冲突了就重试。`synchronized` 是**悲观锁**：先加锁再操作。CAS 没有线程阻塞/唤醒开销，竞争不激烈时性能远超锁。

> ⚠️ CAS 的三个问题：
> 1. **ABA 问题**（见 3.3）
> 2. **自旋开销**：竞争激烈时 CAS 不断失败重试，CPU 空转
> 3. **只能保证一个变量的原子性**：多个变量要用 `AtomicReference` 包成对象

### 3.3 ABA 问题与 AtomicStampedReference

ABA 问题：值从 A → B → A，CAS 检查时以为没变过，其实变过两次：

```java
import java.util.concurrent.atomic.AtomicInteger;

// 模拟 ABA 问题
AtomicInteger ai = new AtomicInteger(1);

// 线程1
new Thread(() -> {
    int a = ai.get();           // 读到 1（A）
    try { Thread.sleep(100); } catch (Exception e) {}
    // 此时线程2已经把 1→2→1
    boolean success = ai.compareAndSet(a, 10);  // 以为没变，CAS 成功
    System.out.println("线程1 CAS: " + success);  // true，但中间发生了变化
}).start();

// 线程2：A→B→A
new Thread(() -> {
    ai.compareAndSet(1, 2);   // A→B
    ai.compareAndSet(2, 1);   // B→A
}).start();
```

用 `AtomicStampedReference` 加版本号解决：

```java
import java.util.concurrent.atomic.AtomicStampedReference;

// 每次更新带一个 stamp（版本号）
AtomicStampedReference<Integer> asr = new AtomicStampedReference<>(1, 0);
// 初始值 1，初始版本 0

int[] stampHolder = new int[1];
Integer value = asr.get(stampHolder);  // 同时取值和版本号
int stamp = stampHolder[0];

// 更新时必须同时匹配值和版本号
asr.compareAndSet(value, 2, stamp, stamp + 1);  // ✅ 值1→2，版本0→1

// 此时别人再拿旧版本号去 CAS 会失败
asr.compareAndSet(1, 10, 0, 1);  // ❌ false，版本号已变
```

> 💡 **ABA 什么时候才有害？** 大部分计数场景 ABA 无害（结果还是对的）。但在「用 CAS 做无锁栈/队列」等场景，ABA 会导致节点被误用，必须加版本号。

### 3.4 字段更新器

`AtomicIntegerFieldUpdater` / `AtomicReferenceFieldUpdater` 可以让**普通 volatile 字段**获得原子操作能力，无需把字段声明为 `AtomicInteger`（节省内存）：

```java
import java.util.concurrent.atomic.AtomicIntegerFieldUpdater;

class User {
    volatile int age;  // 必须是 volatile，否则报错
    String name;
    User(String n, int a) { name = n; age = a; }
}

// 对 User 的 age 字段做原子更新
AtomicIntegerFieldUpdater<User> updater =
    AtomicIntegerFieldUpdater.newUpdater(User.class, "age");

User user = new User("Tom", 18);
updater.incrementAndGet(user);   // age → 19 ✅
System.out.println(user.age);    // 19
```

> ⚠️ 字段更新器要求：
> 1. 字段必须是 `volatile`
> 2. 字段不能是 `private`（updater 基于反射，跨类访问需可见）
> 3. 类型必须严格匹配

---

## 四、同步工具类

JUC 提供了四个经典的同步工具类，用于协调多个线程的执行。

### 4.1 CountDownLatch ⭐⭐

**倒计时锁存器**：让一个或多个线程等待，直到计数器减到 0。

```java
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

// 主线程等待 3 个子线程完成
CountDownLatch latch = new CountDownLatch(3);  // 计数 3

for (int i = 0; i < 3; i++) {
    final int taskId = i;
    new Thread(() -> {
        System.out.println("子任务 " + taskId + " 完成");
        latch.countDown();  // 计数 -1
    }).start();
}

latch.await();  // 阻塞，直到计数归 0
System.out.println("所有子任务完成，主线程继续");

// 带超时，避免子任务卡死
// latch.await(5, TimeUnit.SECONDS);
```

> ⚠️ **CountDownLatch 不可重置**：计数到 0 后就不能再用，是「一次性」的。需要重置用 `CyclicBarrier`。

> 💡 **典型场景**：主线程等待多个子任务并行完成后汇总结果（如多线程查询多个数据源，全部查完再合并）。

### 4.2 CyclicBarrier

**循环栅栏**：所有线程到达屏障点后一起放行，可循环使用。

```java
import java.util.concurrent.CyclicBarrier;

CyclicBarrier barrier = new CyclicBarrier(3, () -> {
    // 所有线程到达屏障后执行的动作
    System.out.println("三个线程都到了，一起放行！");
});

for (int i = 0; i < 3; i++) {
    final int id = i;
    new Thread(() -> {
        System.out.println("线程 " + id + " 到达屏障");
        try {
            barrier.await();  // 等待其他线程
        } catch (Exception e) {}
        System.out.println("线程 " + id + " 继续执行");
    }).start();
}
```

| 对比 | CountDownLatch | CyclicBarrier |
| :--- | :--- | :--- |
| 语义 | 等待 N 个事件完成 | N 个线程互相等待 |
| 重置 | 一次性，不可重置 | 可 `reset()` 重置，循环使用 |
| 计数方向 | 减到 0 | 加到 N |
| 触发者 | 子线程 countDown，主线程 await | 所有线程都 await |

### 4.3 Semaphore

**信号量**：控制同时访问的线程数量，常用于**限流**。

```java
import java.util.concurrent.Semaphore;

// 只允许 3 个线程同时访问
Semaphore semaphore = new Semaphore(3);

for (int i = 0; i < 10; i++) {
    final int id = i;
    new Thread(() -> {
        try {
            semaphore.acquire();  // 获取许可，获取不到就阻塞
            System.out.println("线程 " + id + " 获取许可，执行中");
            Thread.sleep(1000);
        } catch (InterruptedException e) {
        } finally {
            semaphore.release();  // 释放许可
        }
    }).start();
}
// 任何时刻最多 3 个线程在执行
```

> 💡 **典型场景**：数据库连接池（连接数有限）、接口限流（限制并发数）、停车场车位。

### 4.4 Exchanger

**交换器**：两个线程之间交换数据。

```java
import java.util.concurrent.Exchanger;

Exchanger<String> exchanger = new Exchanger<>();

new Thread(() -> {
    String data = "来自线程A的数据";
    try {
        String received = exchanger.exchange(data);  // 交换
        System.out.println("A 收到: " + received);    // 来自线程B的数据
    } catch (Exception e) {}
}).start();

new Thread(() -> {
    String data = "来自线程B的数据";
    try {
        String received = exchanger.exchange(data);
        System.out.println("B 收到: " + received);    // 来自线程A的数据
    } catch (Exception e) {}
}).start();
```

> 💡 Exchanger 用得少，了解即可。典型场景是遗传算法、管道设计。

---

## 五、并发集合

### 5.1 CopyOnWriteArrayList

**写时复制**的线程安全 List：写时复制一份新数组，读完全无锁。

```java
import java.util.concurrent.CopyOnWriteArrayList;

CopyOnWriteArrayList<String> list = new CopyOnWriteArrayList<>();
list.add("a");  // 写：复制出新数组，加元素，替换引用
list.add("b");

// 读：直接读，无锁
System.out.println(list.get(0));  // a
```

原理：
- **写操作**（add/set/remove）：先加锁，复制出新数组，修改新数组，最后把 `array` 引用指向新数组
- **读操作**（get/iterator）：无锁，读的是旧数组的快照

> ⚠️ **适用场景**：**读多写少**。如监听器列表、配置列表——读远多于写。
> **不适用**：写频繁的场景，每次写都复制整个数组，性能差且可能撑爆内存。

> ⚠️ **弱一致性**：迭代器遍历的是创建时的快照，遍历期间的修改不可见，也不会抛 `ConcurrentModificationException`。

### 5.2 ConcurrentLinkedQueue

**无锁并发队列**，基于 CAS 实现，非阻塞。

```java
import java.util.concurrent.ConcurrentLinkedQueue;

ConcurrentLinkedQueue<String> queue = new ConcurrentLinkedQueue<>();
queue.offer("a");   // 入队（CAS）
queue.offer("b");
System.out.println(queue.poll());  // a，出队（CAS）
System.out.println(queue.peek()); // b，查看队头不出队
```

> 💡 适合高并发下的非阻塞队列场景。和 `BlockingQueue` 的区别：`ConcurrentLinkedQueue` 不会阻塞，队列空时 poll 返回 null；`BlockingQueue` 会阻塞等待。

### 5.3 BlockingQueue 阻塞队列

阻塞队列是**生产者-消费者模型**的核心工具：队列满时 put 阻塞，队列空时 take 阻塞。

| 实现类 | 特点 | 常用场景 |
| :--- | :--- | :--- |
| `ArrayBlockingQueue` | 有界，数组实现，一把锁 | 生产者消费者 |
| `LinkedBlockingQueue` | 可选有界，链表实现，两把锁 | 线程池默认队列 |
| `SynchronousQueue` | 容量 0，直接交付 | `newCachedThreadPool` 用 |
| `PriorityBlockingQueue` | 带优先级 | 优先级任务 |

```java
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

BlockingQueue<String> queue = new ArrayBlockingQueue<>(3);  // 容量 3

// 四组 API
queue.put("a");     // 队列满时阻塞 ✅ 常用
queue.offer("b");   // 队列满时返回 false，不阻塞
queue.add("c");     // 队列满时抛异常
// queue.add("d");  // ❌ 队列满，抛 IllegalStateException

String s1 = queue.take();   // 队列空时阻塞 ✅ 常用
String s2 = queue.poll();   // 队列空时返回 null
```

> 💡 **四组 API 对比**：
>
> | 操作 | 抛异常 | 返回特殊值 | 阻塞 | 超时 |
> | :--- | :--- | :--- | :--- | :--- |
> | 入队 | `add` | `offer` | `put` | `offer(e, timeout)` |
> | 出队 | `remove` | `poll` | `take` | `poll(timeout)` |
> | 查看 | `element` | `peek` | — | — |

---

## 六、并发工具类

### 6.1 TimeUnit

`TimeUnit` 枚举替代 `Thread.sleep(毫秒)`，可读性更好：

```java
import java.util.concurrent.TimeUnit;

// ❌ 不直观
Thread.sleep(5000);  // 5000 毫秒？要数零

// ✅ 清晰
TimeUnit.SECONDS.sleep(5);      // 睡 5 秒
TimeUnit.MINUTES.sleep(2);      // 睡 2 分钟
TimeUnit.MILLISECONDS.sleep(500);  // 睡 500 毫秒

// 时间换算
long millis = TimeUnit.SECONDS.toMillis(5);  // 5000
long seconds = TimeUnit.HOURS.toSeconds(1); // 3600
```

### 6.2 ThreadLocalRandom

`Math.random()` 和 `Random` 在多线程下用同一个 `Random` 实例会有竞争（CAS 自旋）。`ThreadLocalRandom` 每个线程独立一个随机数生成器，无竞争：

```java
import java.util.concurrent.ThreadLocalRandom;

// ❌ 多线程竞争
// Random r = new Random();
// r.nextInt(100);

// ✅ 无竞争
int n = ThreadLocalRandom.current().nextInt(100);  // 0~99
double d = ThreadLocalRandom.current().nextDouble();  // 0.0~1.0
```

> 💡 `ThreadLocalRandom` 是 Java 7 引入的，比 `ThreadLocal<Random>` 更高效。多线程随机数首选。

---

## ⚠️ 重点

### 重点 1：ConcurrentHashMap 不能存 null ⭐⭐

```java
ConcurrentHashMap<String, String> map = new ConcurrentHashMap<>();
// map.put("k", null);   // ❌ NullPointerException
// map.put(null, "v");   // ❌ NullPointerException
// 原因：并发下 get 返回 null 无法区分"不存在"和"值为null"
```

### 重点 2：CAS 的 ABA 问题 ⭐⭐⭐

CAS 只比较值，不感知中间变化。需要感知变化时用 `AtomicStampedReference` 加版本号。面试常考「什么是 ABA、怎么解决」。

### 重点 3：CountDownLatch 是一次性的 ⭐⭐

```java
CountDownLatch latch = new CountDownLatch(2);
latch.countDown();
latch.countDown();
latch.await();  // 通过
// latch 已经归 0，无法重置
// 需要循环等待用 CyclicBarrier
```

### 重点 4：CopyOnWriteArrayList 不适合写多 ⭐⭐⭐

每次写都复制整个数组，写多会导致：
1. 性能急剧下降
2. 内存占用翻倍，可能 OOM
3. 多个写线程互相等待（写时加锁）

> 📌 **选型**：读多写少 → `CopyOnWriteArrayList`；读写都多 → `ConcurrentHashMap`（如果是 Map）或加锁的 `Collections.synchronizedList`。

### 重点 5：BlockingQueue 的 put/take 会阻塞 ⭐⭐

```java
BlockingQueue<Integer> q = new ArrayBlockingQueue<>(2);
q.put(1);
q.put(2);
// q.put(3);  // ❌ 队列满，永久阻塞！必须用带超时的 offer
q.offer(3, 3, TimeUnit.SECONDS);  // ✅ 等 3 秒放不进去就放弃
```

### 重点 6：原子类不是万能的 ⭐⭐

`AtomicInteger` 只保证单个操作的原子性，**多个原子操作组合不保证原子性**：

```java
AtomicInteger a = new AtomicInteger(0);
AtomicInteger b = new AtomicInteger(0);
// a.set(1); b.set(2);  // 这两步之间可能被插入，不是原子的
// 要保证 a 和 b 一起更新，还是得用锁或 AtomicReference 封装成一个对象
```

---

## 💻 实战案例

### 案例 1：ConcurrentHashMap 做线程安全缓存 ⭐⭐⭐

电商系统中，商品信息缓存，多线程读写：

```java
import java.util.concurrent.ConcurrentHashMap;

class ProductCache {
    // 线程安全的本地缓存
    private final ConcurrentHashMap<String, String> cache = new ConcurrentHashMap<>();

    // 缓存查询：不存在则加载
    public String getProduct(String productId) {
        // computeIfAbsent 原子操作：不存在才执行加载函数
        return cache.computeIfAbsent(productId, this::loadFromDb);
    }

    private String loadFromDb(String productId) {
        System.out.println("从数据库加载: " + productId);
        return "Product-" + productId;
    }

    // 缓存更新
    public void refresh(String productId, String data) {
        cache.put(productId, data);
    }

    // 缓存失效
    public void invalidate(String productId) {
        cache.remove(productId);
    }
}

// 测试
ProductCache cache = new ProductCache();
for (int i = 0; i < 5; i++) {
    new Thread(() -> {
        System.out.println(cache.getProduct("P001"));  // 只加载一次
    }).start();
}
```

### 案例 2：AtomicInteger 统计接口访问量 ⭐⭐

后台系统统计接口 QPS：

```java
import java.util.concurrent.atomic.AtomicInteger;

class ApiCounter {
    private final AtomicInteger requestCount = new AtomicInteger(0);

    public void onRequest() {
        requestCount.incrementAndGet();  // 原子自增 ✅
    }

    public int getCount() {
        return requestCount.get();
    }

    // 重置并返回当前值
    public int getAndReset() {
        return requestCount.getAndSet(0);
    }
}
```

### 案例 3：CountDownLatch 等待子任务汇总 ⭐⭐⭐

电商首页聚合多个数据源（用户信息、推荐商品、优惠券），并行查询后汇总：

```java
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.Arrays;

class HomePageService {
    public static void main(String[] args) throws InterruptedException {
        CountDownLatch latch = new CountDownLatch(3);
        String[] results = new String[3];

        // 并行查询三个数据源
        new Thread(() -> {
            results[0] = queryUserInfo();       // 模拟查用户
            latch.countDown();
        }).start();
        new Thread(() -> {
            results[1] = queryRecommend();     // 模拟查推荐
            latch.countDown();
        }).start();
        new Thread(() -> {
            results[2] = queryCoupons();       // 模拟查优惠券
            latch.countDown();
        }).start();

        latch.await(2, TimeUnit.SECONDS);  // 最多等 2 秒
        System.out.println("首页数据: " + Arrays.toString(results));
    }

    static String queryUserInfo() { sleep(100); return "用户:Tom"; }
    static String queryRecommend() { sleep(150); return "推荐:商品A,B,C"; }
    static String queryCoupons() { sleep(80); return "优惠券:满100减20"; }
    static void sleep(long ms) { try { Thread.sleep(ms); } catch(Exception e){} }
}
```

### 案例 4：Semaphore 限流接口访问 ⭐⭐⭐

```java
import java.util.concurrent.Semaphore;

class RateLimiter {
    // 只允许 5 个并发请求
    private final Semaphore semaphore = new Semaphore(5);

    public String access(String userId) {
        try {
            if (!semaphore.tryAcquire()) {  // 非阻塞获取
                return "系统繁忙，请稍后重试";  // 快速失败
            }
            // 执行业务逻辑
            return doBusiness(userId);
        } finally {
            semaphore.release();
        }
    }

    private String doBusiness(String userId) {
        try { Thread.sleep(100); } catch(Exception e){}
        return "处理完成: " + userId;
    }
}
```

### 案例 5：BlockingQueue 实现生产者消费者 ⭐⭐⭐

```java
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ArrayBlockingQueue;

// 订单处理系统：生产者下单，消费者处理
class OrderSystem {
    private final BlockingQueue<String> orderQueue = new ArrayBlockingQueue<>(100);

    // 生产者：下单
    public void submitOrder(String orderId) {
        try {
            orderQueue.put(orderId);  // 队列满会阻塞
            System.out.println("订单已提交: " + orderId);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // 消费者：处理订单
    public void startConsumer() {
        new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    String orderId = orderQueue.take();  // 队列空会阻塞
                    System.out.println("处理订单: " + orderId);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }, "order-consumer").start();
    }
}
```

### 案例 6：CopyOnWriteArrayList 做监听器列表 ⭐⭐

事件系统中，监听器注册/触发，读多写少：

```java
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.List;

interface EventListener {
    void onEvent(String event);
}

class EventBus {
    // 监听器列表：读多写少，用 CopyOnWriteArrayList
    private final List<EventListener> listeners = new CopyOnWriteArrayList<>();

    public void register(EventListener listener) {
        listeners.add(listener);  // 写时复制
    }

    public void unregister(EventListener listener) {
        listeners.remove(listener);
    }

    public void publish(String event) {
        // 遍历时无锁，即使别的线程在 register 也不影响
        for (EventListener listener : listeners) {
            listener.onEvent(event);
        }
    }
}

// 使用
EventBus bus = new EventBus();
bus.register(e -> System.out.println("监听器1收到: " + e));
bus.register(e -> System.out.println("监听器2收到: " + e));
bus.publish("用户登录");  // 触发所有监听器
```

---

## 🚀 新版本补充

### Java 8：LongAdder（高并发计数）

Java 8 引入 `LongAdder`，在竞争激烈时性能优于 `AtomicLong`（分段累加，读时合并）：

```java
import java.util.concurrent.atomic.LongAdder;

LongAdder counter = new LongAdder();
counter.increment();   // 高并发计数推荐
counter.add(10);
System.out.println(counter.sum());  // 汇总
// 适合写多读少的统计场景
```

> 💡 `LongAdder` 空间换时间：内部维护多个 Cell，写时分散到不同 Cell，读时累加。竞争越激烈优势越大。

### Java 9：ConcurrentHashMap 增强

Java 9 给 `ConcurrentHashMap` 增加了基于 Stream 的批量并行操作：

```java
// Java 9+
ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();
map.put("a", 1); map.put("b", 2); map.put("c", 3);

// 并行 search
String found = map.search(2, (k, v) -> v > 2 ? k : null);  // 并行搜索
// 并行 reduce
Integer sum = map.reduceValues(2, Integer::sum);  // 并行求和
```

### Java 9：VarHandle 原子操作

Java 9 引入 `VarHandle` 替代 `sun.misc.Unsafe`，提供更规范的内存级别原子操作，是原子类底层 `Unsafe` 的官方替代品。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| ConcurrentHashMap | 线程安全 HashMap，JDK1.8 用 CAS+synchronized 锁桶 |
| 原子类 | AtomicInteger 等，基于 CAS 无锁 |
| CAS | 比较并交换，乐观锁，有 ABA 问题 |
| ABA 解决 | AtomicStampedReference 加版本号 |
| CountDownLatch | 倒计时，一次性，等待 N 个完成 |
| CyclicBarrier | 循环栅栏，可重置，N 个互相等待 |
| Semaphore | 信号量，限流 |
| CopyOnWriteArrayList | 写时复制，读多写少 |
| BlockingQueue | 阻塞队列，生产者消费者 |
| LongAdder | 高并发计数，优于 AtomicLong |

---

## 学习建议

1. **重点吃透 ConcurrentHashMap**：它是面试和开发的双高频，务必理解 JDK 1.7 分段锁和 JDK 1.8 CAS+synchronized 的演进，能口述 put/get 流程。
2. **动手写 CAS 自旋**：用 `AtomicInteger.compareAndSet` 写一个自旋计数器，感受「失败重试」的乐观锁思想，理解 CAS 是 JUC 无锁编程的基石。
3. **对比记忆四个同步工具**：CountDownLatch（一次性等待）、CyclicBarrier（循环栅栏）、Semaphore（限流）、Exchanger（两线程交换），用表格对比语义差异，别混淆。
4. **生产者消费者亲手写一遍**：用 `ArrayBlockingQueue` 实现一个完整的生产者消费者程序，这是理解阻塞队列和线程池任务队列的基础。
5. **注意选型而非死记 API**：读多写少选 CopyOnWrite，高并发计数选 LongAdder，线程安全 Map 选 ConcurrentHashMap——理解每个工具的适用场景比背 API 重要得多。
