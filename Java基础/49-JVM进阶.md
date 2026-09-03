# JVM 进阶

[02-JVM内存模型](02-JVM内存模型.md) 讲了 JVM 把内存切成哪几块、每块存什么。本篇是它的进阶：**对象什么时候被回收、类什么时候被加载、多线程下内存怎么保证可见**——这三件事是 JVM 调优、并发编程、OOM 排查的地基。理解了 GC 和 JMM，你才能写出不漏内存的代码、看懂 `volatile`/`synchronized` 的本质、在 OOM 时知道往哪查。

> 💡 本篇呼应 [02-JVM内存模型](02-JVM内存模型.md)（内存区域）和 [37-线程基础](37-线程基础.md)/[38-线程同步](38-线程同步.md)（并发）。建议先回顾 02 篇的五大区域，再来读本篇。

---

## 一、运行时数据区回顾

[02 篇](02-JVM内存模型.md) 已详述，这里只做索引式回顾，重点放在和 GC/类加载相关的部分。

```
┌──────────────────────────────────────────────────────┐
│                  JVM 运行时数据区                     │
│  ┌────────────────────────────────────────────────┐  │
│  │   堆（Heap）            ← 线程共享，GC 主战场  │  │
│  │   方法区（Method Area）  ← 线程共享，存类信息   │  │
│  └────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 虚拟机栈      │  │ 本地方法栈    │  │程序计数器(PC)│ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│         ↑               ↑                ↑           │
│      线程私有        线程私有         线程私有       │
└──────────────────────────────────────────────────────┘
```

| 区域 | 存什么 | GC 关系 | OOM 类型 |
| :--- | :--- | :--- | :--- |
| **堆** | 对象实例、数组 | **GC 主战场**，分新生代/老年代 | `java.lang.OutOfMemoryError: Java heap space` |
| **方法区** | 类信息、常量池、静态变量 | 回收类信息、卸载类（条件苛刻） | `OutOfMemoryError: Metaspace`（JDK8+） |
| **虚拟机栈** | 栈帧、局部变量表 | 不归 GC 管，方法出栈即释放 | `StackOverflowError` / `OutOfMemoryError` |
| **本地方法栈** | native 方法栈帧 | 同虚拟机栈 | 同上 |
| **程序计数器** | 当前字节码行号 | 无 GC | **唯一不会 OOM** |

> 📌 **JDK 8 的关键变化**：永久代（PermGen）被移除，类信息改存**元空间（Metaspace）**，使用本地内存（堆外）。这意味着方法区溢出从「永久代溢出」变成了「Metaspace 溢出」，且默认只受物理内存限制。

### 堆的分代结构（GC 的物理基础）

堆是 GC 的主战场，JDK 8 默认把堆分为新生代和老年代：

```
┌──────────────────────────────────────────────┐
│                    堆（Heap）                │
│  ┌────────────────────────┬────────────────┐│
│  │      新生代（Young）     │  老年代（Old）  ││
│  │  ┌──────┬─────┬─────┐  │                ││
│  │  │ Eden │ S0  │ S1  │  │                ││
│  │  │      │urv  │urv  │  │                ││
│  │  └──────┴─────┴─────┘  │                ││
│  └────────────────────────┴────────────────┘│
└──────────────────────────────────────────────┘
```

- **新生代**：Eden + 两个 Survivor（S0/S1），占比默认 **8:1:1**（`-XX:SurvivorRatio=8`）
- **老年代**：存长期存活的对象
- **新生代:老年代** 默认 **1:2**（`-XX:NewRatio=2`）

> 💡 **为什么有两个 Survivor？** 为了用复制算法时不碎片化：Eden 满了，存活对象复制到 S0；下次 Eden 满，Eden + S0 的存活对象一起复制到 S1，S0 清空。S0/S1 轮流当「幸存区」和「空区」，始终有一块是空的。

---

## 二、垃圾回收 GC ⭐⭐⭐⭐

GC 要回答两个问题：① 哪些对象是垃圾（该回收）？② 怎么回收？这是 JVM 进阶的核心。

### 2.1 判断对象存活：可达性分析

**引用计数法（不用）**：给对象加个计数器，被引用 +1，断开 -1，为 0 就回收。看似简单，但**循环引用**会让它失效：

```java
class Node {
    Node next;
}
Node a = new Node();   // a 计数=1
Node b = new Node();   // b 计数=1
a.next = b;            // b 计数=2
b.next = a;            // a 计数=2
a = null;              // a 计数=1（b.next 还指着）
b = null;              // b 计数=1（a.next 还指着）
// 此时 a、b 计数都是 1，但外部已无法访问它们 → 内存泄漏！
// 引用计数法回收不了，Java 不用这个方法。
```

**可达性分析（Java 实际用的）**：从一组叫 **GC Roots** 的根对象出发，顺着引用链往下找，**能被找到的对象存活，找不到的是垃圾**。

```
GC Roots
   │
   ├── objA ──→ objB ──→ objC     ✅ objA/B/C 都可达，存活
   │
   └── objD ──→ objE               objD/E 可达，存活

objF ──→ objG                       ❌ objF/G 从 GC Roots 走不到，是垃圾
（objF 只被 objG 引用，但 objG 本身不可达，互相引用也没用）
```

> 💡 **关键**：循环引用不可怕，只要从 GC Roots 走不到这堆对象，它们就是垃圾。可达性分析完美避开了引用计数法的循环引用问题。

### 2.2 GC Roots：哪些是根对象

可作为 GC Roots 的对象（JVM 规范未严格穷举，常见有）：

| GC Root 来源 | 说明 |
| :--- | :--- |
| **虚拟机栈中的局部变量** | 方法里正在用的对象、方法参数 |
| **静态变量** | 类的 `static` 字段引用的对象 |
| **常量引用** | 方法区/元空间中常量池引用的对象 |
| **本地方法栈（JNI）** | native 方法引用的对象 |
| **同步锁持有的对象** | `synchronized` 持有的对象 |
| **JVM 内部引用** | 基本类型 Class、常驻异常对象、类加载器 |

```java
public class GcRootsDemo {
    // ✅ 静态变量：GC Root，cache 引用的对象不会被回收
    private static final Map<String, byte[]> CACHE = new HashMap<>();

    public void process() {
        // ✅ 局部变量：方法执行期间是 GC Root
        List<String> list = new ArrayList<>();
        list.add("临时数据");

        // 方法结束后，list 不再是 GC Root，它指向的 ArrayList 成了垃圾
    }
}
```

> ⚠️ **静态集合是内存泄漏重灾区**：`static Map` 一直当 GC Root，往里塞的 key/value 永远不被回收。做缓存要么用 `WeakReference`/`SoftReference`，要么用有界缓存（如 Guava `Cache`）。

### 2.3 四种引用类型

JDK 1.2 起把引用分四级，影响 GC 回收时机：

| 引用类型 | 类 | GC 时机 | 典型用途 |
| :--- | :--- | :--- | :--- |
| **强引用** | 普通赋值 `Object o = new ...` | **永不回收**（哪怕 OOM） | 日常代码 99% 是这个 |
| **软引用** | `SoftReference` | **内存不足时**回收 | 内存敏感缓存（图片缓存） |
| **弱引用** | `WeakReference` | **下一次 GC 就回收** | ThreadLocal、WeakHashMap |
| **虚引用** | `PhantomReference` | 随时回收，**get 总返回 null** | 跟踪对象被回收的时机（配合 ReferenceQueue） |

```java
import java.lang.ref.*;

// 强引用：最常见
Object strong = new Object();

// 软引用：内存敏感缓存
SoftReference<byte[]> softRef = new SoftReference<>(new byte[1024 * 1024]);
byte[] data = softRef.get();   // 内存足时能拿到，不足时被回收返回 null

// 弱引用：下一次 GC 就没
WeakReference<Object> weakRef = new WeakReference<>(new Object());
System.gc();                   // 建议 GC（不保证立即执行）
System.out.println(weakRef.get());   // 通常为 null

// 虚引用：get 永远返回 null，只用来收通知
ReferenceQueue<Object> queue = new ReferenceQueue<>();
PhantomReference<Object> phantomRef = new PhantomReference<>(new Object(), queue);
System.out.println(phantomRef.get());   // 永远 null
```

> 💡 **记忆口诀**：强→软→弱→虚，回收紧迫度递增。强不回收、软缺内存回收、弱下次 GC 回收、虚等于没引用。

### 2.4 分代收集理论

JVM 基于一个经验事实：**绝大多数对象朝生夕灭**（方法内的临时对象），**少数对象长期存活**（缓存、配置）。所以分代用不同算法：

- **新生代**：对象死亡率高 → 用**复制算法**（存活少，复制成本低）
- **老年代**：对象存活率高 → 用**标记-清除**或**标记-整理**（复制成本高）

### 2.5 对象晋升流程

```
new 对象
   │
   ▼
Eden 区分配
   │
   ├── Eden 满 → Minor GC（复制算法）
   │       │
   │       ├── 存活对象 → Survivor 区（年龄 +1）
   │       └── 死亡对象 → 直接清除
   │
   ├── Survivor 区年龄到阈值（默认 15）→ 晋升老年代
   │
   ├── 大对象（如大数组）→ 直接进老年代（避免 Eden 来回复制）
   │
   └── 老年代满 → Full GC（整堆回收）
```

```java
// 大对象直接进老年代（-XX:PretenureSizeThreshold 控制阈值）
// 比如分配一个 10MB 的数组，可能跳过 Eden 直达老年代
byte[] bigArray = new byte[10 * 1024 * 1024];
```

> 📌 **晋升年龄**：默认 15（`-XX:MaxTenuringThreshold=15`）。对象每熬过一次 Minor GC，年龄 +1，到阈值进老年代。动态年龄判断：Survivor 中相同年龄对象总大小 > Survivor 空间的 50%，年龄 ≥ 该年龄的对象直接晋升。

### 2.6 GC 算法

| 算法 | 过程 | 优点 | 缺点 | 用在哪 |
| :--- | :--- | :--- | :--- | :--- |
| **复制** | 存活对象从 From 复制到 To，From 全清 | 简单、无碎片 | 牺牲一半空间 | 新生代 |
| **标记-清除** | 标记垃圾 → 清除 | 不移动对象 | **碎片化** | 老年代（CMS） |
| **标记-整理** | 标记垃圾 → 清除 → 存活对象向一端移动 | 无碎片 | 移动对象慢 | 老年代 |

```
复制算法：           标记-清除：         标记-整理：
[存活|存活|空|空]    [存活|垃圾|存活|垃圾]  [存活|垃圾|存活|垃圾]
   ↓ 复制              ↓ 清除垃圾            ↓ 清除 + 整理
[空|空|存活|存活]    [存活|空  |存活|空  ]  [存活|存活|空  |空  ]
```

> 💡 **为什么新生代用复制？** 新生代 98% 的对象都是垃圾，存活的少，复制成本低，且复制天然无碎片。代价是浪费 10% 空间（Eden:S0:S1 = 8:1:1，只用 9 份），但值得。

### 2.7 Minor GC / Major GC / Full GC

| 名称 | 回收区域 | 频率 | 耗时 |
| :--- | :--- | :--- | :--- |
| **Minor GC** | 新生代（Eden + 一个 Survivor） | 频繁 | 短（毫秒级） |
| **Major GC** | 老年代（部分收集器才有） | 较少 | 较长 |
| **Full GC** | 整个堆 + 方法区 | 最少 | 最长（STW 明显） |

> ⚠️ **Full GC 是性能杀手**：会 Stop-The-World（暂停所有用户线程）。生产中要尽量减少 Full GC，常见诱因：老年代空间不足、Metaspace 不足、`System.gc()` 被显式调用、内存泄漏。

### 2.8 垃圾收集器

JDK 8 默认 Parallel GC，不同收集器是不同算法的实现：

| 收集器 | 作用区域 | 算法 | 特点 | JDK 8 默认 |
| :--- | :--- | :--- | :--- | :---: |
| **Serial** | 新生代/老年代 | 复制/标记整理 | 单线程，STW，适合客户端 | ❌ |
| **ParNew** | 新生代 | 复制 | Serial 多线程版，配合 CMS | ❌ |
| **Parallel Scavenge** | 新生代 | 复制 | 关注**吞吐量**，自适应调节 | ✅ 新生代 |
| **Parallel Old** | 老年代 | 标记整理 | Parallel 的老年代版 | ✅ 老年代 |
| **CMS** | 老年代 | 标记清除 | **低延迟**，并发标记，碎片化 | ❌（可配） |
| **G1** | 整堆 | 分区+标记整理 | 可预测停顿，JDK 9+ 默认 | ❌（JDK8 可用） |

```java
// 查看当前用的收集器（运行时）
// java -XX:+PrintFlagsFinal -version | grep -i UseG1GC
// java -XX:+PrintFlagsFinal -version | grep -i UseParallelGC
```

**CMS（Concurrent Mark Sweep）**：老年代收集器，分四步：初始标记（STW）→ 并发标记 → 重新标记（STW）→ 并发清除。STW 时间短，适合对延迟敏感的 Web 服务。缺点是碎片化、浮动垃圾。

**G1（Garbage First）**：把堆切成 2048 个 Region，每次优先回收垃圾最多的 Region（Garbage First）。可设期望停顿时间（`-XX:MaxGCPauseMillis=200`），适合大堆、低延迟场景。JDK 9 起为默认。

> 💡 **JDK 8 选收集器**：默认 Parallel（吞吐量优先）。Web 服务要低延迟可手动开 G1：`-XX:+UseG1GC`。CMS 在 JDK 9 被标记废弃，JDK 14 移除。

---

## 三、类加载过程 ⭐⭐⭐

呼应 [02 篇](02-JVM内存模型.md) 的方法区——类信息就存在那。类从 `.class` 文件到可用，分三步：

### 3.1 加载 → 链接 → 初始化

```
.class 文件
    │
    ▼
1. 加载（Loading）
   │  - 通过类全限定名找到二进制字节流（从 jar/网络/动态生成）
   │  - 转为方法区的运行时数据结构
   │  - 在堆中生成 Class 对象，作为方法区数据的访问入口
   ▼
2. 链接（Linking）——分三小步
   │  2.1 验证（Verification）：检查字节码格式、语义、合法性，防恶意 class
   │  2.2 准备（Preparation）：为静态变量分配内存并赋**默认值**（0/null/false）
   │  2.3 解析（Resolution）：常量池中的符号引用 → 直接引用（地址）
   ▼
3. 初始化（Initialization）
   │  - 执行类构造器 <clinit>()：合并所有 static 变量赋值 + static 代码块
   │  - 此时静态变量才被赋**实际值**
   ▼
   类就绪，可被使用
```

### 3.2 准备 vs 初始化：静态变量的值变化

```java
public class InitOrderDemo {
    // 准备阶段：value = 0（默认值）
    // 初始化阶段：value = 123（执行 <clinit> 里的赋值）
    public static int value = 123;

    public static String name;       // 准备：null，初始化：null（没赋值）
    public static String city = "北京"; // 准备：null，初始化："北京"

    static {
        System.out.println("static 块执行，value=" + value);   // 123
        name = "张三";   // static 块也能赋静态变量
    }
}
```

> ⚠️ **关键区分**：准备阶段给的是**零值**（int=0、引用=null），初始化阶段才执行你的赋值语句和 static 块。这是为什么 static 块里能读到「已赋值的 value」——因为赋值语句在 static 块之前执行。

### 3.3 类初始化时机

什么情况会触发类的初始化（`<clinit>` 执行）：

```java
// ✅ 主动引用（触发初始化）
new InitOrderDemo();              // 1. new 实例
InitOrderDemo.value = 5;         // 2. 读/写静态字段（非 final 的）
InitOrderDemo.staticMethod();    // 3. 调静态方法
Class.forName("InitOrderDemo");  // 4. 反射
new SubClass();                  // 5. 初始化子类，父类先初始化

// ❌ 被动引用（不触发初始化）
SubClass.staticFromParent;       // 通过子类访问父类静态字段，只初始化父类
InitOrderDemo[] arr = new InitOrderDemo[10];  // 创建数组，不初始化类
final int x = InitOrderDemo.CONSTANT;         // 访问 static final 常量（编译期已知）
```

> 💡 **static final 常量**在编译期就存入调用方的常量池，运行时根本不引用定义类，所以不触发初始化。这是常量传播优化。

### 3.4 类加载器与双亲委派

```
       ┌──────────────────┐
       │ Bootstrap（启动） │  ← 加载 rt.jar（java.lang.* 等），C++ 实现，无 Java 对象
       └────────┬─────────┘
                │ 父加载器
       ┌────────┴─────────┐
       │ Extension（扩展） │  ← 加载 ext 目录（JDK8），JDK9+ 改为 PlatformClassLoader
       └────────┬─────────┘
                │ 父加载器
       ┌────────┴─────────┐
       │ Application（应用）│  ← 加载 classpath，我们写的类大多它加载
       └────────┬─────────┘
                │ 父加载器
       ┌────────┴─────────┐
       │ 自定义 ClassLoader│  ← Tomcat、SPI、热部署等场景
       └──────────────────┘
```

**双亲委派模型**：收到加载请求时，**先委托父加载器**，父加载不到自己才加载。

```java
// 自定义类加载器破坏双亲委派（慎用）
class MyClassLoader extends ClassLoader {
    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        // 先委托父加载器（默认行为，super.loadClass 已做）
        // 父加载不到，才走这里自定义加载逻辑
        byte[] bytes = loadClassData(name);   // 从自定义来源读字节码
        return defineClass(name, bytes, 0, bytes.length);
    }
    private byte[] loadClassData(String name) { /* ... */ return null; }
}
```

> 📌 **双亲委派的意义**：保证 `java.lang.String` 一定被 Bootstrap 加载，你写个同名类也抢不走——**保证核心 API 不被篡改**，类型安全。Tomcat 等 Web 容器为了隔离多个应用，会打破它（每个应用一个独立类加载器）。

---

## 四、Java 内存模型 JMM ⭐⭐⭐

JMM（Java Memory Model）和 JVM 内存区域是**两个层面**：内存区域讲数据放哪，JMM 讲**多线程下数据怎么可见、怎么有序**。这是理解 `volatile`/`synchronized` 的钥匙。

### 4.1 主内存与工作内存

JMM 规定每个变量在主内存，每个线程有自己的**工作内存**（对应 CPU 缓存/寄存器）：

```
┌────────────────────────────────────────────┐
│                  主内存                      │
│   sharedVar = 0    ← 所有线程共享的变量      │
└──────┬───────────────┬─────────────────────┘
       │ read/write     │ read/write
┌──────┴──────┐  ┌──────┴──────┐
│ 线程A 工作内存│  │ 线程B 工作内存│
│ sharedVar=0 │  │ sharedVar=0 │  ← 各线程的本地副本
└─────────────┘  └─────────────┘
```

- 线程不能直接读写主内存，必须经过工作内存
- 线程 A 改了工作内存的副本，**不立刻同步主内存**，线程 B 也**看不到**

> ⚠️ 这就是可见性问题的根源：线程 A `flag = true`，线程 B 可能一直看到 `false`。

### 4.2 三大特性

| 特性 | 含义 | 谁保证 |
| :--- | :--- | :--- |
| **原子性** | 操作不可分割，要么全做要么不做 | `synchronized`、`Lock`、`Atomic*` |
| **可见性** | 一个线程改了变量，其他线程立刻能看到 | `volatile`、`synchronized`、`final` |
| **有序性** | 代码执行顺序符合预期（防指令重排） | `volatile`、`synchronized` |

### 4.3 可见性问题演示

```java
public class VisibilityDemo {
    // ❌ 不加 volatile：子线程可能永远看不到 flag 变 true
    private static boolean flag = false;

    // ✅ 加 volatile：保证可见性
    // private static volatile boolean flag = false;

    public static void main(String[] args) throws InterruptedException {
        new Thread(() -> {
            System.out.println("子线程启动，等待 flag=true...");
            while (!flag) {
                // 死循环等 flag 变 true
                // ❌ 不加 volatile 时，JIT 可能优化成只读一次 flag，永远循环
            }
            System.out.println("子线程退出");
        }).start();

        Thread.sleep(1000);
        flag = true;   // 主线程改 flag
        System.out.println("主线程设置 flag=true");
    }
}
```

> ⚠️ 不加 `volatile`，这个程序**可能永远不退出**（取决于 JIT 优化和 CPU 缓存）。这是可见性失效的经典案例。加了 `volatile` 后，主线程的写立刻对子线程可见。

### 4.4 有序性与指令重排

编译器和 CPU 为了性能会**重排指令**，单线程下结果不变（as-if-serial），多线程下可能出问题：

```java
// 重排前的代码          // 可能被重排成
int x = 1;              int y = 2;     // y 先赋值
int y = 2;              int x = 1;     // x 后赋值
int z = x + y;          int z = x + y; // 单线程结果一样
```

经典的重排坑——双重检查锁单例：

```java
public class Singleton {
    // ❌ 不加 volatile：可能拿到「半初始化」的对象
    // private static Singleton instance;

    // ✅ 加 volatile：禁止重排，保证构造完成才对其他线程可见
    private static volatile Singleton instance;

    private Singleton() { }

    public static Singleton getInstance() {
        if (instance == null) {                   // 第一次检查
            synchronized (Singleton.class) {
                if (instance == null) {            // 第二次检查
                    instance = new Singleton();    // 非原子：分3步
                    // 1. 分配内存  2. 初始化对象  3. 引用指向内存
                    // 不加 volatile，可能重排成 1→3→2
                    // 别的线程在外层 if 看到 instance != null，拿到的却是未初始化完的对象！
                }
            }
        }
        return instance;
    }
}
```

> 📌 **双重检查锁必须用 volatile**：这不是保证可见性（synchronized 已保证），而是**禁止对象初始化的重排**。这是面试高频题，务必记住。

### 4.5 happens-before 规则

JMM 用 happens-before 描述操作间的可见性：**A happens-before B，则 A 的结果对 B 可见**。核心规则：

| 规则 | 说明 |
| :--- | :--- |
| 程序顺序规则 | 同一线程内，代码顺序在前的操作 happens-before 后面的 |
| 锁规则 | 一个锁的 unlock happens-before 后续对同一锁的 lock |
| volatile 规则 | volatile 变量的写 happens-before 后续对它的读 |
| 线程启动规则 | `Thread.start()` happens-before 该线程的所有操作 |
| 线程终止规则 | 线程的所有操作 happens-before `Thread.join()` 返回 |
| 传递性 | A happens-before B，B happens-before C → A happens-before C |

```java
// volatile 规则的应用
class Config {
    volatile boolean ready = false;
    int data;

    void writer() {        // 线程A
        data = 42;          // 1. 普通写
        ready = true;       // 2. volatile 写
    }

    void reader() {         // 线程B
        if (ready) {        // 3. volatile 读
            // 由 volatile 规则：2 happens-before 3
            // 由程序顺序：1 happens-before 2，3 happens-before 4
            // 由传递性：1 happens-before 4 → data 一定可见为 42
            System.out.println(data);   // 4. 一定读到 42，不是 0
        }
    }
}
```

> 💡 **volatile 的妙用**：它本身只保证可见性和禁止重排，不保证原子性（`i++` 仍不安全）。但配合 happens-before，可以让它前面的普通写也对其他线程可见——上面 `data` 不是 volatile 却也能被正确读到。

### 4.6 volatile vs synchronized

| 维度 | volatile | synchronized |
| :--- | :--- | :--- |
| 原子性 | ❌ 不保证（`i++` 不安全） | ✅ 保证 |
| 可见性 | ✅ 保证 | ✅ 保证 |
| 有序性 | ✅ 禁止重排 | ✅ 保证 |
| 是否阻塞 | 不阻塞 | 可能阻塞（抢锁） |
| 轻量级 | 轻（不抢锁） | 重（monitor） |
| 适用场景 | 状态标志、单次读写 | 复合操作、临界区 |

```java
// ❌ volatile 不能保证 i++ 原子性
volatile int count = 0;
count++;   // 读-改-写三步，非原子，多线程下丢更新

// ✅ 复合操作用 synchronized 或 Atomic
synchronized (this) { count++; }
// 或
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();   // CAS，原子
```

> 📌 **选型口诀**：纯状态标志（true/false）用 volatile；复合操作（++、check-then-act）用 synchronized 或 Atomic*。详见 [38-线程同步](38-线程同步.md) 和 [40-JUC并发包](40-JUC并发包.md)。

---

## 五、JVM 常用参数

### 5.1 堆大小参数

| 参数 | 作用 | 常用值 |
| :--- | :--- | :--- |
| `-Xms` | 堆初始大小 | 与 Xmx 设一样，避免动态扩容 |
| `-Xmx` | 堆最大大小 | 生产建议 2~4G 起步 |
| `-Xmn` | 新生代大小 | 通常让 JVM 自调 |
| `-XX:NewRatio=2` | 新生代:老年代 = 1:2 | 默认值 |
| `-XX:SurvivorRatio=8` | Eden:S0:S1 = 8:1:1 | 默认值 |
| `-XX:MetaspaceSize=256m` | 元空间初始大小，触发 GC 阈值 | 防止启动期频繁 Full GC |
| `-XX:MaxMetaspaceSize=512m` | 元空间上限 | 防止类加载泄漏撑爆 |

```bash
# 生产典型配置（4G 堆的 Web 服务）
java -Xms4g -Xmx4g -XX:NewRatio=2 -XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m -XX:+UseG1GC -jar app.jar
```

> 📌 **Xms 和 Xmx 设一样**：避免 JVM 动态扩容/缩容时的性能抖动。生产环境这是铁律。

### 5.2 GC 日志参数

```bash
# JDK 8 打印 GC 日志
java -XX:+PrintGCDetails -XX:+PrintGCDateStamps -Xloggc:gc.log -jar app.jar

# JDK 9+ 统一日志（Xlog）
java -Xlog:gc*=info:file=gc.log:time,uptime,level,tags -jar app.jar
```

GC 日志示例（Minor GC）：

```
2026-09-03T10:00:00.000+0800: 1.234: [GC (Allocation Failure)
  [PSYoungGen: 76288K->8192K(89152K)] 76288K->8300K(294400K), 0.0123 secs]
```

解读：新生代从 76288K 降到 8192K，整堆从 76288K 降到 8300K，耗时 12.3ms。

> 💡 **GC 日志是调优的第一手资料**。看「GC 频率」和「回收后剩余」。频繁 Full GC 且回收后剩余仍很高 → 内存泄漏。用 [GCViewer](https://github.com/chewiebug/GCViewer) 或 GCEasy.io 可视化分析。

### 5.3 其他实用参数

| 参数 | 作用 |
| :--- | :--- |
| `-XX:+PrintFlagsFinal` | 打印所有参数最终值（看默认配置） |
| `-XX:+HeapDumpOnOutOfMemoryError` | OOM 时自动 dump 堆（排查必备） |
| `-XX:HeapDumpPath=/path/dump.hprof` | dump 文件路径 |
| `-XX:+PrintCommandLineFlags` | 启动时打印命令行参数 |

---

## 六、OOM 类型与排查

### 6.1 四种典型 OOM

| OOM 类型 | 报错信息 | 触发场景 |
| :--- | :--- | :--- |
| **堆溢出** | `java.lang.OutOfMemoryError: Java heap space` | 对象太多、内存泄漏、大对象 |
| **栈溢出** | `java.lang.StackOverflowError` | 递归太深、栈帧太大 |
| **方法区/Metaspace 溢出** | `OutOfMemoryError: Metaspace` | 动态生成类太多（CGLIB、反射） |
| **直接内存溢出** | `OutOfMemoryError: Direct buffer memory` | NIO 的 ByteBuffer.allocateDirect 用太多 |

### 6.2 堆溢出演示

```java
import java.util.ArrayList;
import java.util.List;

// ❌ 内存泄漏：静态集合持有对象不释放
public class HeapOOMDemo {
    public static void main(String[] args) {
        List<byte[]> list = new ArrayList<>();
        int i = 0;
        try {
            while (true) {
                list.add(new byte[1024 * 1024]);   // 每次塞 1MB
                i++;
            }
        } catch (OutOfMemoryError e) {   // 注意是 Error 不是 Exception
            System.out.println("撑爆堆，共塞了 " + i + "MB");
            e.printStackTrace();
        }
    }
}
// 运行：java -Xmx32m -XX:+HeapDumpOnOutOfMemoryError HeapOOMDemo
// 结果：撑爆堆，共塞了 28MB 左右（32M 减去 JVM 自身开销）
```

> ⚠️ `OutOfMemoryError` 是 `Error` 不是 `Exception`，`catch (Exception)` 抓不到，要 `catch (Throwable)` 或 `catch (OutOfMemoryError)`。

### 6.3 栈溢出演示

```java
public class StackOverflowDemo {
    static int depth = 0;

    public static void recursion() {
        depth++;
        recursion();   // 无限递归，无终止条件
    }

    public static void main(String[] args) {
        try {
            recursion();
        } catch (StackOverflowError e) {
            System.out.println("递归深度：" + depth);   // 默认栈大小下约 1万次
        }
    }
}
// 运行：java -Xss256k StackOverflowDemo   ← 减小栈空间，递归深度变小
```

> 💡 `-Xss` 设置线程栈大小（默认 512k~1m）。栈越大递归越深，但能开的线程数越少（总内存有限）。Web 服务高并发时栈别设太大。

### 6.4 Metaspace 溢出

```java
// 动态生成大量类（CGLIB/反射场景）
// java -XX:MaxMetaspaceSize=64m MetaspaceOOMDemo
// 报错：OutOfMemoryError: Metaspace
```

> 📌 Spring 的 CGLIB 代理、MyBatis 的 Mapper 动态代理、反射大量生成类时，Metaspace 可能撑爆。设 `-XX:MaxMetaspaceSize` 给个上限。

### 6.5 排查工具速查

| 工具 | 用途 | 命令 |
| :--- | :--- | :--- |
| **jps** | 列出 Java 进程 | `jps -l` |
| **jstack** | 打印线程栈（查死锁、死循环） | `jstack <pid>` |
| **jmap** | 堆内存快照、对象统计 | `jmap -histo <pid>` / `jmap -dump:format=b,file=d.hprof <pid>` |
| **jstat** | GC 统计（看各区使用率） | `jstat -gcutil <pid> 1000` |
| **jhat** | 分析 dump（已过时，用 MAT） | `jhat dump.hprof` |
| **MAT/Visual VM** | 图形化分析堆 dump | 打开 .hprof 文件 |

```bash
# 典型排查流程
jps -l                          # 1. 找到卡住的 Java 进程 PID
jstack <pid> > stack.txt        # 2. dump 线程栈，找 BLOCKED / 死循环
jmap -histo:live <pid> | head -20   # 3. 看对象占用 Top20
jmap -dump:format=b,file=heap.hprof <pid>   # 4. dump 堆
# 5. 用 MAT 打开 heap.hprof，找 GC Root 引用链，定位泄漏源
```

> 💡 `jstat -gcutil <pid> 1000` 每秒打印一次各区使用率（E/S/O/M 占比 + GC 次数/耗时），是判断「是不是 GC 问题」的最快手段。

---

## ⚠️ 重点

### 重点 1：可达性分析与 GC Roots ⭐⭐⭐

```java
// GC Roots 是「起点」，从它们走不到的对象就是垃圾
public class GcRootDemo {
    private static Object staticCache = new Object();   // ✅ 静态变量是 GC Root

    public void method() {
        Object local = new Object();   // ✅ 局部变量是 GC Root（方法执行期间）
        // 方法返回后，local 不再是 Root，它指的对象可被回收
    }
}
```

> ⚠️ **静态集合 = 内存泄漏温床**。`static Map` 里的对象永远可达，不会被 GC。做缓存务必用 `WeakReference`/`SoftReference` 或有界缓存。

### 重点 2：四种引用的回收时机 ⭐⭐

```java
// 软引用：内存敏感缓存（图片、配置）
SoftReference<byte[]> cache = new SoftReference<>(new byte[1024 * 1024]);
byte[] data = cache.get();   // 内存够时拿到，不够时被回收返回 null
if (data == null) { /* 重新加载 */ }

// 弱引用：ThreadLocal 内部用 WeakEntry，key 是弱引用
WeakHashMap<Object, String> weakMap = new WeakHashMap<>();
Object key = new Object();
weakMap.put(key, "v");
key = null;                  // key 失去强引用
System.gc();                 // 下次 GC，WeakHashMap 里的 entry 被清除
```

> 💡 **ThreadLocal 内存泄漏**：ThreadLocalMap 的 key 是弱引用（ThreadLocal 对象），但 value 是强引用。ThreadLocal 被回收后 key 变 null，但 value 还在 → 泄漏。所以用完务必 `remove()`。详见 [42-ThreadLocal](42-ThreadLocal与异步编程.md)。

### 重点 3：分代收集与晋升 ⭐⭐⭐

```
对象先在 Eden 分配 → Minor GC 存活进 Survivor（年龄+1）→ 年龄到15进老年代
大对象直接进老年代 → 老年代满 Full GC
```

> 📌 **减少 Full GC 的关键**：① 别让短命对象意外晋升（Survivor 太小会直接进老年代，调 `-XX:SurvivorRatio`）；② 大对象控制（分页查询别一次查百万条）；③ 防内存泄漏（静态集合、未关闭的资源）。

### 重点 4：volatile 只保证可见性不保证原子性 ⭐⭐⭐

```java
volatile int count = 0;
// 多线程下 count++ 仍丢更新！
// count++ = 读 + 改 + 写，三步非原子，volatile 只保证每步可见

// ✅ 解决方案
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();   // CAS 原子操作
// 或 synchronized
```

> ⚠️ 这是面试和实战最高频的坑。`volatile` 适合「一个线程写、多线程读」的纯状态标志。一旦涉及 `++` 或 `check-then-act`，必须上 `synchronized` 或 `Atomic*`。

### 重点 5：双重检查锁单例必须用 volatile ⭐⭐⭐

```java
public class Singleton {
    private static volatile Singleton instance;   // ✅ 必须 volatile

    public static Singleton getInstance() {
        if (instance == null) {
            synchronized (Singleton.class) {
                if (instance == null) {
                    instance = new Singleton();   // 非原子，防重排
                }
            }
        }
        return instance;
    }
}
```

> 💡 这里 volatile 的作用不是可见性（synchronized 已保证），而是**禁止 `new Singleton()` 的指令重排**，防止别的线程拿到半初始化对象。这是 `volatile` 最经典的高级用法。

### 重点 6：happens-before 是可见性的理论基石 ⭐⭐

```java
// volatile 写 happens-before volatile 读 → 后续能看到前面的普通写
int a = 1;            // 普通写
volatile boolean flag = true;   // volatile 写，对后续读可见
// 线程B 读 flag==true 后，一定能看到 a==1（传递性）
```

> 📌 理解 happens-before 才能真正理解 `volatile`/`synchronized` 的内存语义，而不是死记「volatile 保证可见性」。

---

## 💻 实战案例

### 案例 1：观察 GC 日志 ⭐

写个程序制造垃圾，观察 Minor GC：

```java
public class GcLogDemo {
    public static void main(String[] args) {
        // 运行参数：-Xms20m -Xmx20m -XX:+PrintGCDetails -XX:+PrintGCDateStamps
        for (int i = 0; i < 200; i++) {
            // 每次分配 1MB，Eden 满了触发 Minor GC
            byte[] data = new byte[1024 * 1024];
            // data 作用域结束，下次循环被回收
        }
        System.out.println("结束");
    }
}
// 日志会看到多次 [GC (Allocation Failure) ... PSYoungGen: ...]
// 每次回收后新生代占用骤降，说明临时对象被清掉了
```

> 💡 配合 `-Xloggc:gc.log` 把日志写文件，丢到 [GCEasy.io](https://gceasy.io) 在线分析，一键看吞吐量、平均/最大停顿、各代占用曲线。

### 案例 2：软引用做图片缓存 ⭐⭐

内存敏感的缓存，OOM 前自动释放：

```java
import java.lang.ref.SoftReference;
import java.util.HashMap;
import java.util.Map;

public class ImageCache {
    // 软引用缓存：内存不足时 JVM 自动回收 value
    private final Map<String, SoftReference<byte[]>> cache = new HashMap<>();

    public void put(String key, byte[] imageBytes) {
        cache.put(key, new SoftReference<>(imageBytes));
    }

    public byte[] get(String key) {
        SoftReference<byte[]> ref = cache.get(key);
        if (ref == null) return null;
        byte[] data = ref.get();
        if (data == null) {
            // 内存不足被回收了，需要重新加载
            cache.remove(key);   // 清理失效条目
            System.out.println(key + " 被回收，需重新加载");
        }
        return data;
    }

    public static void main(String[] args) {
        ImageCache cache = new ImageCache();
        // 模拟缓存 10 张 1MB 图片
        for (int i = 0; i < 10; i++) {
            cache.put("img" + i, new byte[1024 * 1024]);
        }
        // -Xmx32m 运行：内存不足时软引用被回收，get 返回 null
        System.out.println(cache.get("img0") != null ? "命中" : "被回收");
    }
}
```

> 📌 软引用缓存适合「有更好、没有也能重新加载」的场景（图片缩略图、配置缓存）。生产中更推荐 Guava `CacheBuilder().softValues()` 或 Caffeine，封装了失效和重建逻辑。

### 案例 3：弱引用做 ThreadLocal 防泄漏 ⭐⭐

呼应 [42-ThreadLocal](42-ThreadLocal与异步编程.md)，理解为什么 ThreadLocal 用弱引用做 key：

```java
import java.lang.ref.WeakReference;

public class WeakRefDemo {
    public static void main(String[] args) {
        // 模拟 ThreadLocal 的弱引用 key
        Object strongRef = new Object();
        WeakReference<Object> weakRef = new WeakReference<>(strongRef);

        System.out.println("GC 前：" + weakRef.get());   // 非 null

        strongRef = null;   // 去掉强引用
        System.gc();        // 建议回收
        System.out.println("GC 后：" + weakRef.get());    // 通常 null

        // ThreadLocal 原理：ThreadLocalMap 的 key 是弱引用
        // ThreadLocal 对象本身被回收后，key 自动变 null
        // 但 value 仍是强引用 → 需手动 remove()
    }
}
```

> ⚠️ **ThreadLocal 用完必须 `remove()`**：线程池的线程会复用，ThreadLocal 的 value 不清会一直留在 Thread 的 ThreadLocalMap 里，导致内存泄漏。这是线程池场景最隐蔽的坑。

### 案例 4：内存泄漏——静态集合持有对象 ⭐⭐

电商后台典型泄漏：把用户对象塞进静态 Map 当缓存，永不清理：

```java
import java.util.HashMap;
import java.util.Map;

public class UserCacheLeak {
    // ❌ 静态 Map 永远是 GC Root，里面的对象永不回收
    private static final Map<Integer, User> CACHE = new HashMap<>();

    public User getUser(int id) {
        User u = CACHE.get(id);
        if (u == null) {
            u = loadFromDb(id);
            CACHE.put(id, u);   // 塞进去就出不来了
        }
        return u;
    }

    private User loadFromDb(int id) { return new User(id, "user" + id); }

    static class User { int id; String name; User(int id, String name) { this.id = id; this.name = name; } }

    public static void main(String[] args) {
        UserCacheLeak cache = new UserCacheLeak();
        // 模拟 10 万用户查询，每个都进缓存
        for (int i = 0; i < 100000; i++) {
            cache.getUser(i);
        }
        // CACHE 持有 10 万个 User，永不释放 → 内存泄漏
        // -Xmx64m 运行会 OOM
    }
}
```

**修复方案**：用有界缓存或弱引用：

```java
// ✅ 方案1：弱引用 Map，key 失去强引用后自动清除
private static final Map<Integer, WeakReference<User>> CACHE = new HashMap<>();

// ✅ 方案2：有界缓存（Guava，推荐）
// Cache<Integer, User> cache = CacheBuilder.newBuilder()
//     .maximumSize(1000)
//     .expireAfterAccess(10, TimeUnit.MINUTES)
//     .build();
```

### 案例 5：OOM 自动 dump 与排查 ⭐⭐

生产环境必备配置，OOM 时自动留现场：

```bash
# 启动参数
java -Xmx512m \
     -XX:+HeapDumpOnOutOfMemoryError \
     -XX:HeapDumpPath=/var/log/app/oom-$(date +%s).hprof \
     -jar app.jar
```

模拟并排查：

```java
import java.util.ArrayList;
import java.util.List;

public class OomDemo {
    static class Order {
        String orderId;
        byte[] detail = new byte[1024];   // 每个订单 1KB
        Order(String id) { this.orderId = id; }
    }

    public static void main(String[] args) {
        List<Order> orders = new ArrayList<>();
        try {
            for (int i = 0; i < 1000000; i++) {
                orders.add(new Order("ORDER" + i));   // 不断塞
            }
        } catch (OutOfMemoryError e) {
            System.err.println("OOM！订单数：" + orders.size());
        }
    }
}
```

排查步骤：

```bash
# 1. OOM 后会在指定路径生成 .hprof 文件
# 2. 用 Eclipse MAT 打开
# 3. 点击 "Leak Suspects Report" → 自动分析泄漏点
# 4. 看 "Dominator Tree" → 哪个对象占内存最大
# 5. "Path to GC Roots" → 找到 GC Root 引用链
#    本例会显示：ArrayList -> Order[] -> Order -> byte[] 被 main 方法持有
```

> 💡 **MAT 的 Path to GC Roots** 是定位泄漏的杀手锏：它告诉你「这个本该被回收的对象，是被谁一直抓着不放」。顺着引用链往上找，就是泄漏源。

### 案例 6：用 jstack 排查 CPU 飙高/死锁 ⭐⭐

```java
// 死锁演示
public class DeadLockDemo {
    private static final Object lockA = new Object();
    private static final Object lockB = new Object();

    public static void main(String[] args) {
        new Thread(() -> {
            synchronized (lockA) {
                try { Thread.sleep(100); } catch (Exception e) {}
                synchronized (lockB) { System.out.println("拿到B"); }
            }
        }, "thread-1").start();

        new Thread(() -> {
            synchronized (lockB) {
                try { Thread.sleep(100); } catch (Exception e) {}
                synchronized (lockA) { System.out.println("拿到A"); }
            }
        }, "thread-2").start();
    }
}
```

排查：

```bash
jps -l                          # 找到 PID
jstack <pid>                    # dump 级程栈
# 日志末尾会自动检测并打印：
# "Found one Java-level deadlock:"
# ==================
# "thread-1" waiting to lock monitor 0x...(lockA)...
# "thread-2" waiting to lock monitor 0x...(lockB)...
# 死锁链一目了然
```

CPU 飙高排查：

```bash
top -Hp <pid>                   # 找到 CPU 最高的线程 ID（十进制）
printf "%x\n" <tid>             # 转成十六进制
jstack <pid> | grep <hex_tid> -A 30   # 在栈里找该线程在干什么
# 通常会看到某个线程在跑某个方法（死循环/正则爆炸/频繁GC）
```

> 📌 `top -Hp` 看线程级 CPU，`jstack` 看栈，两者配合是排查 CPU 飙高的标准动作。

### 案例 7：JVM 参数调优实战 ⭐

电商秒杀场景，高并发短延迟：

```bash
# 初始配置（4核8G 服务器）
java -Xms4g -Xmx4g \
     -XX:NewRatio=1 \                              # 新生代调大，短命对象多
     -XX:SurvivorRatio=8 \
     -XX:+UseG1GC \                                # G1 收集器，低延迟
     -XX:MaxGCPauseMillis=200 \                    # 目标停顿 200ms
     -XX:+HeapDumpOnOutOfMemoryError \
     -XX:HeapDumpPath=/data/logs/oom.hprof \
     -XX:+PrintGCDetails -Xloggc:/data/logs/gc.log \
     -jar seckill.jar
```

调优思路：

1. **看 GC 日志**：用 GCEasy 分析，看吞吐量（应 >95%）和最大停顿（应 <200ms）
2. **频繁 Minor GC** → 新生代太小，调大 `-Xmn` 或 `-XX:NewRatio`
3. **频繁 Full GC 且回收后剩余仍高** → 内存泄漏，先排查代码
4. **停顿太长** → 换 G1/ZGC（JDK 11+），或减小堆（停顿和堆大小正相关）
5. **老年代涨得快** → Survivor 太小，对象过早晋升，调 `-XX:SurvivorRatio`

> ⚠️ **调优不是玄学**：先有监控（GC 日志 + APM），再有依据地调。盲目加参数只会越调越乱。80% 的问题靠合理堆大小 + 避免内存泄漏就能解决。

---

## 🚀 新版本补充

### Java 9+：G1 成为默认收集器

JDK 9 起，默认收集器从 Parallel 改为 **G1**。G1 把堆切成 Region，可预测停顿时间，适合大堆低延迟场景。

```bash
# JDK 9+ 不用显式指定，默认就是 G1
java -Xmx4g -XX:MaxGCPauseMillis=200 -jar app.jar
```

### Java 11+：ZGC 与 Shenandoah（实验性→稳定）

低延迟收集器，停顿时间 <10ms（与堆大小无关）：

```bash
# JDK 11（实验性）
java -XX:+UnlockExperimentalVMOptions -XX:+UseZGC -Xmx16g -jar app.jar

# JDK 15+ ZGC 转正
java -XX:+UseZGC -Xmx16g -jar app.jar
```

> 💡 ZGC 着色指针 + 读屏障实现并发整理，停顿亚毫秒级。适合超大堆（几十 G）且对延迟极度敏感的金融交易系统。

### Java 10+：统一 JVM 日志（Xlog）

JDK 9 引入统一日志框架，取代混乱的 `-XX:+PrintGCDetails`：

```bash
# JDK 10+
java -Xlog:gc*=info:file=gc.log:time,uptime,level,tags -Xmx4g -jar app.jar
# gc*=info：所有 gc 相关 tag，info 级别
# file=gc.log：输出到文件
# time,uptime,level,tags：输出格式
```

### Java 11：Epsilon GC（No-OP）

只分配不回收的「假」收集器，用于性能测试（测纯负载，排除 GC 干扰）：

```bash
java -XX:+UnlockExperimentalVMOptions -XX:+UseEpsilonGC -Xmx4g -jar app.jar
# 4G 用完直接 OOM，中间无任何 GC 开销
```

### Java 14：移除 CMS

CMS 在 JDK 9 标记 deprecated，JDK 14 正式移除。低延迟场景改用 G1 或 ZGC。

### Java 16+：ZGC 生成代（分代 ZGC）

ZGC 引入分代，吞吐量进一步提升。JDK 21 起默认开启分代 ZGC。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 内存区域 | 堆/方法区/栈/本地栈/PC，呼应 02 篇 |
| 堆分代 | 新生代（Eden+S0+S1）+ 老年代，默认 1:2 |
| 判断存活 | 可达性分析（GC Roots），不用引用计数 |
| GC Roots | 栈局部变量、静态变量、常量、JNI、锁 |
| 四种引用 | 强（不回收）/软（内存不足回收）/弱（下次GC回收）/虚（跟踪回收） |
| 分代收集 | 新生代复制算法，老年代标记清除/整理 |
| 对象晋升 | Eden→Survivor→年龄15→老年代；大对象直接老年代 |
| GC 类型 | Minor GC（新生代）/ Major GC（老年代）/ Full GC（整堆，STW） |
| 收集器 | Serial/ParNew/Parallel/CMS/G1，JDK8 默认 Parallel |
| 类加载 | 加载→链接（验证/准备/解析）→初始化，执行 `<clinit>` |
| 双亲委派 | 先委托父加载器，保证核心 API 不被篡改 |
| JMM 三性 | 原子性/可见性/有序性 |
| happens-before | 描述可见性传递规则 |
| volatile | 保证可见性 + 禁止重排，不保证原子性 |
| synchronized | 保证三性，但重 |
| JVM 参数 | -Xms/-Xmx（堆）/ -Xss（栈）/ -XX:NewRatio / -XX:+PrintGCDetails |
| OOM 类型 | 堆溢出/栈溢出/Metaspace 溢出/直接内存溢出 |
| 排查工具 | jps/jstack/jmap/jstat/MAT |

---

## 学习建议

1. **先用 GC 日志建立直觉**：写个循环分配 byte[] 的程序，加 `-Xmx32m -XX:+PrintGCDetails` 跑，肉眼看 Minor GC 怎么把新生代清空。比读十遍理论都直观。再把日志丢 GCEasy.io 分析。
2. **把四种引用的代码各跑一遍**：软引用做缓存、弱引用看被回收、ThreadLocal 的 remove 习惯。并发编程的内存泄漏 80% 和引用类型有关，必须手熟。
3. **volatile 的双重检查锁单例背下来**：这是 JMM 最经典的综合应用，面试必考。理解「为什么 volatile 不是为了可见性而是为了防重排」，你就真正懂 JMM 了。
4. **掌握 jstack + jmap 的排查流程**：死锁用 jstack（看末尾自动检测）、CPU 飙高用 top -Hp + jstack、OOM 用 HeapDumpOnOutOfMemoryError + MAT。这三个场景覆盖了 90% 的线上 JVM 问题。
5. **调优先看监控再动参数**：别一上来就调 `-XX`。先有 GC 日志和 APM，确认是 GC 问题（频繁 Full GC？停顿太长？），再针对性调堆大小/分代比例/换收集器。80% 的问题靠「合理堆大小 + 修内存泄漏」就解决了，参数是最后手段。
