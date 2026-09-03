# System 与 Runtime 类

`System` 和 `Runtime` 是 Java 提供的两个与「运行环境」打交道的核心工具类。`System` 提供静态方法操作标准 IO、系统属性、时间戳、数组复制、JVM 退出等；`Runtime` 则封装了 JVM 进程本身——CPU 核数、堆内存、外部命令执行、关闭钩子。它们都不需要我们 new（`System` 全静态、`Runtime` 是单例），却几乎出现在每个 Java 项目的某个角落：日志里的时间戳、性能测试的纳秒计时、容器里判断操作系统、优雅停机时关闭线程池……理解它们，就掌握了与 JVM「对话」的基本能力。

> 💡 在阅读本篇前，建议先了解 [02-JVM内存模型](02-JVM内存模型.md) 中堆内存的划分，理解 `maxMemory` / `totalMemory` / `freeMemory` 三者的区别会更容易。

---

## 一、System 类概述

`java.lang.System` 是 `final` 类，**构造方法私有**，不能实例化，所有成员都是 `static`。它相当于 JVM 与操作系统之间的「静态工具箱」：

| 功能分类 | 代表方法 | 用途 |
| :--- | :--- | :--- |
| 时间 | `currentTimeMillis()`、`nanoTime()` | 获取时间戳、测耗时 |
| 数组 | `arraycopy(...)` | 高效复制数组 |
| 属性 | `getProperty()`、`getProperties()`、`setProperty()` | 读写系统属性 |
| 环境变量 | `getenv()`、`getenv(String)` | 读取操作系统环境变量 |
| 标准 IO | `System.out`、`System.err`、`System.in` | 标准输出/错误/输入流 |
| 生命周期 | `exit(int)`、`gc()` | 退出 JVM、建议垃圾回收 |

> 💡 `System` 类的所有方法都通过 `System.方法名()` 直接调用，无需创建对象。

---

## 二、时间获取：currentTimeMillis 与 nanoTime

### 2.1 currentTimeMillis()：毫秒级时间戳

返回当前时间与 `1970-01-01 00:00:00 UTC` 之间的毫秒差，类型为 `long`。它是 Java 中最常用的时间基准。

```java
// 获取当前时间戳（毫秒）
long start = System.currentTimeMillis();  // 如：1700000000000

// ✅ 经典用法：计算方法耗时
long begin = System.currentTimeMillis();
Thread.sleep(50);  // 模拟耗时操作
long end = System.currentTimeMillis();
System.out.println("耗时：" + (end - begin) + " ms");  // 约 50 ms

// ✅ 生成唯一性 ID（单机简易方案）
String orderId = "ORD" + System.currentTimeMillis();
System.out.println(orderId);  // ORD1700000000123
```

> ⚠️ `currentTimeMillis()` 的精度依赖操作系统，Windows 下通常是 15ms 左右的粒度（即多次调用可能返回相同值）。**不要用它做高精度计时**，高精度请用 `nanoTime()`。

### 2.2 nanoTime()：纳秒级计时

返回一个 `long` 值，**只能用于计算时间差**，与任何绝对时间无关（可能是负数）。

```java
// ✅ 高精度性能测试
long t1 = System.nanoTime();
// 执行被测代码
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append("a");
}
long t2 = System.nanoTime();
System.out.println("耗时：" + (t2 - t1) + " ns");  // 如：1500000 ns
System.out.println("耗时：" + (t2 - t1) / 1_000_000.0 + " ms");
```

> ⚠️ **`nanoTime()` 的绝对值无意义**，它只保证「同一 JVM 内、同一次调用线程间」单调递增（多线程下不保证）。不要用它换算当前日期，那是 `currentTimeMillis()` 的活。

> 💡 **选择建议**：测耗时 > 100ms 用 `currentTimeMillis()`（直观、可读）；测微秒/纳秒级性能差异用 `nanoTime()`。

---

## 三、数组复制：arraycopy

`System.arraycopy(src, srcPos, dest, destPos, length)` 是**本地方法**，底层直接操作内存，比 `for` 循环快得多。`ArrayList` 的扩容、`Arrays.copyOf` 底层都靠它。

```java
// 方法签名
// public static native void arraycopy(Object src, int srcPos,
//                                    Object dest, int destPos, int length)

// ✅ 基本用法：把 src 从下标 2 开始的 3 个元素，复制到 dest 从下标 0 开始的位置
int[] src = {10, 20, 30, 40, 50};
int[] dest = new int[3];
System.arraycopy(src, 2, dest, 0, 3);
// dest = {30, 40, 50}

// ✅ 数组自我复制（src 和 dest 可以是同一个数组，但区间不能重叠到出错）
int[] arr = {1, 2, 3, 4, 5};
System.arraycopy(arr, 0, arr, 1, 4);
// arr = {1, 1, 2, 3, 4}，注意 srcPos < destPos 时从后往前复制
```

```java
// ❌ 常见错误：目标数组太小
int[] src = {1, 2, 3, 4, 5};
int[] dest = new int[2];
System.arraycopy(src, 0, dest, 0, 5);
// 运行时抛出：ArrayIndexOutOfBoundsException

// ❌ 类型不匹配
String[] strs = {"a", "b"};
int[] nums = new int[2];
System.arraycopy(strs, 0, nums, 0, 2);
// 运行时抛出：ArrayStoreException
```

> 📌 **规范**：`arraycopy` 会做类型检查——源数组和目标数组的**元素类型必须兼容**（基本类型必须完全一致，引用类型需满足父子关系），否则抛 `ArrayStoreException`。

---

## 四、系统属性：getProperty / getProperties / setProperty

系统属性是 JVM 启动时从操作系统和启动参数中读取的一组「键值对」，用 `getProperty` 读取。

### 4.1 常用系统属性

| 属性键 | 含义 | 示例值 |
| :--- | :--- | :--- |
| `java.version` | Java 运行时版本 | `1.8.0_301` |
| `java.home` | JDK 安装目录 | `C:\Program Files\Java\jdk1.8.0_301` |
| `os.name` | 操作系统名称 | `Windows 10` / `Linux` |
| `os.arch` | 操作系统架构 | `amd64` |
| `os.version` | 操作系统版本 | `10.0` |
| `user.dir` | 当前工作目录 | `F:\Java Learning` |
| `user.home` | 用户主目录 | `C:\Users\Leo` |
| `user.name` | 用户账户名 | `Leo` |
| `file.separator` | 文件分隔符 | `\`（Win）/ `/`（Linux） |
| `line.separator` | 行分隔符 | `\r\n`（Win）/ `\n`（Linux） |
| `path.separator` | 路径分隔符 | `;`（Win）/ `:`（Linux） |

```java
// ✅ 读取单个属性
String javaVersion = System.getProperty("java.version");
String osName = System.getProperty("os.name");
String userDir = System.getProperty("user.dir");
System.out.println("Java 版本：" + javaVersion);
System.out.println("操作系统：" + osName);
System.out.println("工作目录：" + userDir);

// ✅ 读取所有属性
Properties props = System.getProperties();
props.list(System.out);  // 打印全部系统属性
```

### 4.2 setProperty 与启动参数 -D

```java
// ✅ 程序内设置自定义系统属性
System.setProperty("app.env", "production");
System.setProperty("app.name", "order-service");
String env = System.getProperty("app.env");  // production
```

更常见的做法是启动时通过 `-D` 参数注入：

```bash
# 启动时注入系统属性（-Dkey=value）
java -Dapp.env=production -Dconfig.path=/etc/app MyApp
```

```java
// 程序内读取
String env = System.getProperty("app.env");        // production
String path = System.getProperty("config.path");   // /etc/app

// ✅ 带默认值：属性不存在时返回默认值
String timeout = System.getProperty("db.timeout", "5000");  // 5000
```

> 💡 `-D` 参数是配置化部署的常用手段：把数据库地址、环境标识、配置路径等通过 `-D` 注入，代码用 `getProperty` 读取，实现「同一份代码跑不同环境」。

---

## 五、环境变量：getenv

环境变量是**操作系统层面**的变量（如 `PATH`、`JAVA_HOME`），与系统属性不同：系统属性是 JVM 内的，环境变量是 OS 的。

```java
// ✅ 读取单个环境变量
String javaHome = System.getenv("JAVA_HOME");
String path = System.getenv("PATH");
System.out.println("JAVA_HOME：" + javaHome);

// ✅ 读取所有环境变量
Map<String, String> env = System.getenv();
for (Map.Entry<String, String> entry : env.entrySet()) {
    System.out.println(entry.getKey() + " = " + entry.getValue());
}
```

> ⚠️ **`getenv` 返回的 Map 是只读的**，尝试 `put` 会抛 `UnsupportedOperationException`。Java **没有提供修改环境变量的 API**——环境变量在进程启动时就固定了。

| 区别 | 系统属性 `getProperty` | 环境变量 `getenv` |
| :--- | :--- | :--- |
| 所属层级 | JVM 内部 | 操作系统 |
| 是否可修改 | ✅ `setProperty` 可改 | ❌ 只读 |
| 启动注入方式 | `-Dkey=value` | OS 层设置 |
| 跨进程共享 | ❌ 仅当前 JVM | ✅ 子进程可继承 |
| 典型用途 | 应用配置 | `PATH`、`JAVA_HOME` |

---

## 六、标准 IO 流：System.out / err / in

`System` 提供三个静态字段，代表 JVM 的标准输入输出：

| 字段 | 类型 | 含义 |
| :--- | :--- | :--- |
| `System.out` | `PrintStream` | 标准输出（控制台正常输出） |
| `System.err` | `PrintStream` | 标准错误（控制台错误输出，常显示为红色） |
| `System.in` | `InputStream` | 标准输入（键盘输入） |

```java
// ✅ 标准输出
System.out.println("普通信息");   // 黑色

// ✅ 标准错误（IDE 控制台通常显示红色）
System.err.println("错误信息");

// ✅ 标准输入：读取键盘输入
Scanner scanner = new Scanner(System.in);
System.out.print("请输入姓名：");
String name = scanner.nextLine();
System.out.println("你好，" + name);
scanner.close();
```

### 6.1 重定向标准流

可以通过 `setOut` / `setErr` / `setIn` 重定向到文件或其他流，常用于日志采集：

```java
// ✅ 把 System.out 重定向到文件
PrintStream fileOut = new PrintStream(
    new FileOutputStream("app.log", true), true, "UTF-8");
System.setOut(fileOut);
System.out.println("这行会写入 app.log 而非控制台");

// ✅ 把 System.err 重定向到单独的错误日志
PrintStream fileErr = new PrintStream(
    new FileOutputStream("error.log", true), true, "UTF-8");
System.setErr(fileErr);
System.err.println("这行会写入 error.log");

// ⚠️ 恢复前先保存原流
PrintStream originalOut = System.out;  // 先保存
// ... 重定向操作 ...
System.setOut(originalOut);           // 恢复
```

> ⚠️ 重定向后别忘了在合适时机**恢复原流**，否则后续所有 `System.out.println` 都会「消失」（实际写到了文件里），排查问题时会很困惑。

---

## 七、JVM 退出与垃圾回收：exit 与 gc

### 7.1 exit(int)：退出 JVM

```java
// ✅ 正常退出（状态码 0 表示正常）
System.exit(0);

// ✅ 异常退出（非 0 表示异常，常用于启动失败）
System.exit(1);
```

> ⚠️ `System.exit(n)` 会立即终止 JVM，**不会执行后续任何代码**，也不会执行 `finally` 块。它本质上调用了 `Runtime.getRuntime().exit(n)`。在 Web 应用、被容器管理的程序中**慎用**——会直接干掉整个进程。

> 📌 **规范**：`exit(0)` 表示正常结束；非 0 状态码表示异常退出，Shell 脚本可通过 `$?` 获取该码判断成败。

### 7.2 gc()：建议垃圾回收

```java
// ✅ 建议 JVM 进行垃圾回收（只是建议，不保证立即执行）
System.gc();
```

> ⚠️ `System.gc()` **只是给 JVM 一个「建议」**，JVM 可以选择忽略。它等价于 `Runtime.getRuntime().gc()`。生产环境**不要主动调用**——Full GC 会造成停顿，影响性能。它主要用于测试场景下触发 GC 以观察内存回收。

---

## 八、Runtime 类概述

`java.lang.Runtime` 封装了「JVM 运行时环境」，是**单例**——每个 JVM 只有一个 `Runtime` 实例，通过 `getRuntime()` 获取：

```java
// ✅ 获取 Runtime 单例
Runtime runtime = Runtime.getRuntime();

// ❌ 不能直接 new：构造方法私有
// Runtime r = new Runtime();  // 编译错误
```

`Runtime` 与 `System` 功能有重叠（`System.gc()` 内部就是调 `Runtime.gc()`，`System.exit()` 内部调 `Runtime.exit()`），但 `Runtime` 多了**内存查询、CPU 核数、执行外部命令、关闭钩子**等独有能力。

---

## 九、CPU 核心数：availableProcessors

```java
// ✅ 获取可用 CPU 核心数（逻辑核数，含超线程）
int processors = Runtime.getRuntime().availableProcessors();
System.out.println("CPU 核心数：" + processors);  // 如：8
```

这是设置线程池大小的关键依据。Doug Lea 给出的经验公式：

```java
// ✅ CPU 密集型任务：线程数 = 核心数 + 1
int cpuThreads = processors + 1;

// ✅ IO 密集型任务：线程数 = 核心数 * 2（或更大）
int ioThreads = processors * 2;

// 实际开发中常这样初始化线程池
ExecutorService pool = Executors.newFixedThreadPool(processors * 2);
```

> 💡 `availableProcessors()` 返回的是**逻辑核数**（含超线程），不是物理核数。8 核 16 线程的 CPU 返回 16。容器环境下返回的是容器限制的核数（Java 8u131+ 开始支持容器感知）。

---

## 十、堆内存信息：maxMemory / totalMemory / freeMemory

这三个方法最容易混淆，务必理解三者的层级关系：

```
┌─────────────────────────────────────────────┐
│           maxMemory（最大堆上限）              │  ← -Xmx 设定的上限
│  ┌───────────────────────────────────────┐  │
│  │      totalMemory（已分配堆）            │  │  ← JVM 当前向 OS 申请的内存
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   used（已使用）= total - free   │  │  │
│  │  ├─────────────────────────────────┤  │  │
│  │  │   freeMemory（堆内空闲）          │  │  │  ← 已分配但未使用
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│         （未分配的保留空间）                    │  ← 需要时 JVM 再向 OS 申请
└─────────────────────────────────────────────┘
```

```java
Runtime rt = Runtime.getRuntime();

// ✅ 三个核心方法（单位：字节）
long max = rt.maxMemory();       // JVM 堆最大上限（-Xmx）
long total = rt.totalMemory();   // JVM 当前已分配的堆
long free = rt.freeMemory();    // 已分配堆中的空闲部分

// 已使用内存 = 已分配 - 空闲
long used = total - free;

// JVM 还能再申请的内存 = 最大上限 - 已使用
long available = max - used;

System.out.println("最大堆：" + max / 1024 / 1024 + " MB");
System.out.println("已分配：" + total / 1024 / 1024 + " MB");
System.out.println("已使用：" + used / 1024 / 1024 + " MB");
System.out.println("空闲  ：" + free / 1024 / 1024 + " MB");
```

> ⚠️ **`freeMemory` 不是「堆还剩多少」**！它是「已分配的那部分堆里还没用的空间」。真正能用的上限是 `maxMemory - (totalMemory - freeMemory)`。新手常把 `freeMemory` 当成「剩余可用内存」，导致监控数据误判。

> 💡 启动参数 `-Xms`（初始堆）影响 `totalMemory` 初始值，`-Xmx`（最大堆）决定 `maxMemory` 上限：`java -Xms256m -Xmx1024m MyApp`。

---

## 十一、执行外部命令：exec

`Runtime.exec` 可以启动子进程执行系统命令或脚本。

```java
// ✅ 执行简单命令
Process p = Runtime.getRuntime().exec("notepad.exe");  // Windows 打开记事本

// ✅ 执行带参数的命令（用数组形式，避免空格解析问题）
String[] cmd = {"cmd", "/c", "dir", "C:\\"};
Process p2 = Runtime.getRuntime().exec(cmd);

// ✅ 读取子进程输出
Process proc = Runtime.getRuntime().exec("ipconfig");
try (BufferedReader reader = new BufferedReader(
        new InputStreamReader(proc.getInputStream(), "GBK"))) {
    String line;
    while ((line = reader.readLine()) != null) {
        System.out.println(line);
    }
}
int exitCode = proc.waitFor();  // 等待子进程结束，返回退出码
System.out.println("退出码：" + exitCode);
```

```java
// ❌ 经典坑：不读取错误流会导致子进程挂起
Process p = Runtime.getRuntime().exec("java -version");
// 子进程的输出/错误流有缓冲区，满了会阻塞，父进程不读就死锁
p.waitFor();  // 可能永远不返回

// ✅ 正确做法：必须读取输出流和错误流
Process proc = Runtime.getRuntime().exec("java -version");
// 用两个线程分别读 stdout 和 stderr，避免阻塞
new Thread(() -> readStream(proc.getInputStream())).start();
new Thread(() -> readStream(proc.getErrorStream())).start();
proc.waitFor();
```

> ⚠️ **`exec` 的两个大坑**：① 命令含空格时必须用数组或 `ProcessBuilder`，否则会被当成一个整体命令名找不到；② **必须读取子进程的输出流和错误流**，否则缓冲区满后子进程会挂起，`waitFor()` 永远不返回。

> 📌 **规范**：Java 5+ 推荐用 `ProcessBuilder` 替代 `exec`，它支持设置工作目录、环境变量、合并输出流，更灵活安全：
> ```java
> ProcessBuilder pb = new ProcessBuilder("java", "-version");
> pb.redirectErrorStream(true);  // 合并 stderr 到 stdout
> Process proc = pb.start();
> ```

---

## 十二、关闭钩子：addShutdownHook

关闭钩子是 JVM 在**正常退出**（`exit`、`Ctrl+C`、`kill -15`、所有非守护线程结束）时执行的线程，用于做资源清理。

```java
// ✅ 注册关闭钩子：JVM 退出时自动执行
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    System.out.println("正在关闭数据库连接...");
    // closeConnection();
    System.out.println("正在关闭线程池...");
    // shutdownPool();
    System.out.println("正在刷写日志...");
    // flushLogs();
    System.out.println("清理完成，再见！");
}));
```

> ⚠️ **关闭钩子不会在以下情况执行**：
> - `kill -9`（强制杀进程，SIGKILL）
> - JVM 崩溃（`OutOfMemoryError` 导致进程直接挂掉）
> - 操作系统断电
>
> 因此关闭钩子是「尽力而为」的清理，不能作为唯一保障——关键数据仍需及时落盘。

> 📌 **规范**：关闭钩子里不要做耗时操作（JVM 默认有超时），不要调用 `System.exit`（会死锁），不要新建非守护线程。Spring Boot 的优雅停机底层就是基于关闭钩子实现的。

---

## ⚠️ 重点

### 重点 1：currentTimeMillis 与 nanoTime 的使用场景 ⭐

```java
// ✅ 测几十毫秒以上的耗时：用 currentTimeMillis（直观可读）
long t1 = System.currentTimeMillis();
doWork();
long t2 = System.currentTimeMillis();
System.out.println((t2 - t1) + " ms");

// ✅ 测微秒/纳秒级差异：用 nanoTime（精度高）
long n1 = System.nanoTime();
doWork();
long n2 = System.nanoTime();
System.out.println((n2 - n1) + " ns");
```

> ⚠️ `nanoTime()` 返回值**不是当前时间的纳秒**，绝对值无意义，只能做差。`currentTimeMillis()` 才是「当前时间戳」，可换算日期。

### 重点 2：arraycopy 的参数顺序 ⭐⭐

`arraycopy` 有 5 个参数，顺序极易记混：

```java
System.arraycopy(src, srcPos, dest, destPos, length);
//              源,  源起点,  目标,  目标起点,  长度
```

> 💡 **记忆口诀**：「源、源位、目、目位、长」——先源后目标，先位置后长度。

```java
// ❌ 参数填反的典型错误
int[] src = {1, 2, 3, 4, 5};
int[] dest = new int[5];
System.arraycopy(src, 0, dest, 0, 5);  // ✅ 正确
// System.arraycopy(dest, 0, src, 0, 5);  // 方向反了，虽然这里巧合不出错
```

### 重点 3：maxMemory / totalMemory / freeMemory 三者关系 ⭐⭐⭐

这是面试高频题，也是监控告警的基础：

```java
Runtime rt = Runtime.getRuntime();
long max = rt.maxMemory();      // 堆上限（-Xmx）
long total = rt.totalMemory();  // 已分配堆
long free = rt.freeMemory();    // 已分配堆中空闲
long used = total - free;       // 实际已使用

// ⚠️ 错误理解：freeMemory 就是剩余内存
// ✅ 正确：真正可用 = max - used
long realFree = max - used;
```

> ⚠️ **`freeMemory` 只是「已分配堆里没用到的部分」**，JVM 需要时还会向 OS 申请更多内存（直到 `maxMemory`）。监控 JVM 内存时，关注 `used / max` 的比值，而不是 `free`。

### 重点 4：exec 必须读取子进程输出流 ⭐⭐

```java
// ❌ 死锁写法
Process p = Runtime.getRuntime().exec("dir");
p.waitFor();  // 子进程输出缓冲区满，永远阻塞

// ✅ 正确写法：读取输出流
Process p = Runtime.getRuntime().exec("cmd /c dir");
try (BufferedReader reader = new BufferedReader(
        new InputStreamReader(p.getInputStream(), "GBK"))) {
    String line;
    while ((line = reader.readLine()) != null) {
        System.out.println(line);
    }
}
p.waitFor();
```

> ⚠️ 子进程的 stdout 和 stderr 各有缓冲区（通常 4KB），满了不读就阻塞。**最稳妥的做法是用两个线程分别读 stdout 和 stderr**，或用 `ProcessBuilder.redirectErrorStream(true)` 合并。

### 重点 5：exit 会跳过 finally ⭐

```java
try {
    System.out.println("try");
    System.exit(0);   // ⚠️ JVM 直接退出
    System.out.println("不会执行");
} finally {
    System.out.println("finally 也不会执行！");  // ❌ 不会输出
}
```

> ⚠️ `System.exit()` 是「立即终止 JVM」，`finally` 块、后续代码全部跳过。但**关闭钩子会执行**（在 `exit` 触发的关闭流程中）。Web 应用里绝对不要随便调 `exit`，会干掉整个服务器进程。

### 重点 6：关闭钩子的执行条件 ⭐

```java
// ✅ 会触发关闭钩子的场景
// 1. 所有非守护线程结束（main 方法正常跑完）
// 2. System.exit(n)
// 3. Ctrl+C（SIGINT）
// 4. kill -15（SIGTERM）

// ❌ 不会触发的场景
// 1. kill -9（SIGKILL，强制杀）
// 2. OOM 崩溃、JVM 异常终止
// 3. 断电
```

> 📌 **规范**：关键资源（如数据库连接、文件句柄）不要只依赖关闭钩子释放，应在使用完毕后及时关闭。关闭钩子是「兜底」而非「主路径」。

---

## 💻 实战案例

### 案例 1：用 currentTimeMillis 计算方法耗时（性能监控）⭐⭐

电商系统中，接口耗时是核心指标。封装一个简易耗时统计工具：

```java
// ✅ 方法耗时统计工具
public class TimerUtil {
    private final long start;

    private TimerUtil() {
        this.start = System.currentTimeMillis();
    }

    public static TimerUtil start() {
        return new TimerUtil();
    }

    public long elapsed() {
        return System.currentTimeMillis() - start;
    }

    public void print(String tag) {
        System.out.println(tag + " 耗时：" + elapsed() + " ms");
    }
}

// 使用：监控下单接口各环节耗时
public class OrderService {
    public void createOrder() {
        TimerUtil timer = TimerUtil.start();

        // 1. 校验库存
        checkStock();
        timer.print("校验库存");

        // 2. 扣减库存
        deductStock();
        timer.print("扣减库存");

        // 3. 创建订单
        saveOrder();
        timer.print("创建订单");

        // 4. 发送消息
        sendMessage();
        timer.print("发送消息");
    }
}
```

> 💡 生产环境用 Micrometer、Arthas 等专业工具做性能监控，但理解 `currentTimeMillis` 的原理是基础。

### 案例 2：arraycopy 实现数组扩容（模拟 ArrayList）⭐⭐

`ArrayList` 的核心就是 `arraycopy` 做的扩容。手写一个简化版：

```java
// ✅ 简化版动态数组
public class SimpleList<E> {
    private Object[] elementData;
    private int size;

    public SimpleList(int capacity) {
        this.elementData = new Object[capacity];
    }

    public void add(E e) {
        // 容量不足时扩容 1.5 倍
        if (size == elementData.length) {
            grow();
        }
        elementData[size++] = e;
    }

    private void grow() {
        // ✅ 核心就是 arraycopy
        int newCapacity = elementData.length + (elementData.length >> 1);
        Object[] newArr = new Object[newCapacity];
        System.arraycopy(elementData, 0, newArr, 0, size);
        elementData = newArr;
        System.out.println("扩容：" + size + " -> " + newCapacity);
    }

    @SuppressWarnings("unchecked")
    public E get(int index) {
        return (E) elementData[index];
    }

    public int size() {
        return size;
    }
}

// 使用
SimpleList<String> list = new SimpleList<>(2);
list.add("A");
list.add("B");
list.add("C");  // 触发扩容：2 -> 3
list.add("D");
list.add("E");  // 触发扩容：3 -> 4（实际 ArrayList 是 1.5 倍）
```

> 💡 `Arrays.copyOf`、`ArrayList.grow`、`HashMap.resize` 底层都依赖 `System.arraycopy`，它是集合框架的「地基」。

### 案例 3：读取系统属性判断操作系统（跨平台兼容）⭐⭐

不同操作系统的路径分隔符、换行符不同，写跨平台代码要动态获取：

```java
// ✅ 跨平台工具类
public class OsUtil {
    private static final String OS = System.getProperty("os.name").toLowerCase();

    public static boolean isWindows() {
        return OS.contains("win");
    }

    public static boolean isLinux() {
        return OS.contains("nux");
    }

    public static boolean isMac() {
        return OS.contains("mac");
    }

    // ✅ 跨平台拼接路径（不要硬编码 \ 或 /）
    public static String path(String... parts) {
        return String.join(File.separator, parts);
    }
}

// 使用：根据系统选择不同脚本
public class DeployService {
    public void startService() {
        if (OsUtil.isWindows()) {
            Runtime.getRuntime().exec("cmd /c start.bat");
        } else if (OsUtil.isLinux()) {
            Runtime.getRuntime().exec("sh /opt/app/start.sh");
        }
    }

    // ✅ 用系统属性拼接路径，而非硬编码
    public void loadConfig() {
        // ❌ 错误：硬编码路径分隔符
        // String path = "config" + "\\" + "app.properties";

        // ✅ 正确：用 File.separator
        String path = "config" + File.separator + "app.properties";
        // 或用 OsUtil.path
        String path2 = OsUtil.path("config", "app.properties");
    }
}
```

> 📌 **规范**：永远不要在代码里硬编码 `\` 或 `/`，用 `File.separator` 或 `Paths.get()`。换行符用 `System.lineSeparator()` 或 `System.getProperty("line.separator")`，不要硬编码 `\r\n`。

### 案例 4：Runtime 执行外部脚本（运维自动化）⭐⭐

后台系统常需要调用 Shell 脚本完成部署、备份等运维任务：

```java
// ✅ 执行 Shell 脚本并获取结果（Linux 备份数据库）
public class BackupService {
    public int backupDatabase() throws Exception {
        String[] cmd = {"/bin/sh", "-c",
            "mysqldump -u root -p123456 order_db > /backup/order_$(date +%Y%m%d).sql"};

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);  // 合并错误流到输出流
        Process proc = pb.start();

        // 读取输出（必须读，否则可能阻塞）
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(proc.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[backup] " + line);
            }
        }

        int code = proc.waitFor();
        if (code == 0) {
            System.out.println("备份成功");
        } else {
            System.err.println("备份失败，退出码：" + code);
        }
        return code;
    }
}
```

```java
// ✅ Windows 下调用 PowerShell 脚本
public class WinTaskService {
    public void runScript() throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            "powershell", "-ExecutionPolicy", "Bypass",
            "-File", "C:\\scripts\\cleanup.ps1"
        );
        pb.directory(new File("C:\\scripts"));  // 设置工作目录
        Process proc = pb.start();

        // 必须读取输出流
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(proc.getInputStream(), "GBK"))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }
        }
        proc.waitFor();
    }
}
```

> ⚠️ **安全警告**：如果命令参数来自用户输入，务必防范**命令注入**！不要直接拼接字符串执行，用参数数组形式（`ProcessBuilder`）并做白名单校验。金融系统尤其要注意。

### 案例 5：关闭钩子做资源清理（优雅停机）⭐⭐⭐

Spring Boot、Netty 等框架的优雅停机底层都是关闭钩子。模拟一个后台服务的优雅停机：

```java
// ✅ 后台服务：注册关闭钩子做资源清理
public class OrderServiceBootstrap {
    private ExecutorService threadPool;
    private Connection dbConnection;
    private BufferedWriter logWriter;

    public void start() throws Exception {
        // 初始化资源
        threadPool = Executors.newFixedThreadPool(8);
        dbConnection = DriverManager.getConnection("jdbc:mysql://localhost/order", "root", "123456");
        logWriter = new BufferedWriter(new FileWriter("order.log", true));

        // ✅ 注册关闭钩子
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("\n=== 收到关闭信号，开始优雅停机 ===");

            // 1. 停止接收新任务
            threadPool.shutdown();
            System.out.println("线程池已停止接收新任务");

            // 2. 等待已提交任务完成
            try {
                if (threadPool.awaitTermination(30, TimeUnit.SECONDS)) {
                    System.out.println("所有任务已完成");
                } else {
                    System.out.println("超时，强制关闭");
                    threadPool.shutdownNow();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

            // 3. 关闭数据库连接
            try {
                if (dbConnection != null && !dbConnection.isClosed()) {
                    dbConnection.close();
                    System.out.println("数据库连接已关闭");
                }
            } catch (SQLException e) {
                e.printStackTrace();
            }

            // 4. 刷写并关闭日志
            try {
                if (logWriter != null) {
                    logWriter.flush();
                    logWriter.close();
                    System.out.println("日志已刷写");
                }
            } catch (IOException e) {
                e.printStackTrace();
            }

            System.out.println("=== 优雅停机完成 ===");
        }, "shutdown-hook"));

        // 启动业务线程
        for (int i = 0; i < 100; i++) {
            threadPool.submit(() -> processOrder());
        }
        System.out.println("订单服务已启动，按 Ctrl+C 退出");
    }

    private void processOrder() {
        // 处理订单逻辑...
    }
}
```

> 💡 Spring Boot 只需 `spring.boot.register-shutdown-hook=true`（默认开启），容器关闭时会自动调用 `@PreDestroy`、`DisposableBean` 等回调，底层就是 `Runtime.addShutdownHook`。

### 案例 6：JVM 内存监控（线上预警）⭐⭐

运维场景下，需要监控 JVM 堆内存使用率，超过阈值告警：

```java
// ✅ 内存监控守护线程
public class MemoryMonitor {
    private final double threshold;  // 告警阈值，如 0.8

    public MemoryMonitor(double threshold) {
        this.threshold = threshold;
    }

    public void start() {
        Thread monitor = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                Runtime rt = Runtime.getRuntime();
                long max = rt.maxMemory();
                long total = rt.totalMemory();
                long free = rt.freeMemory();
                long used = total - free;

                double usageRate = (double) used / max;  // 使用率

                System.out.printf("[监控] 已用：%dMB / 上限：%dMB，使用率：%.1f%%%n",
                        used / 1024 / 1024, max / 1024 / 1024, usageRate * 100);

                if (usageRate > threshold) {
                    System.err.printf("⚠️ 内存告警！使用率 %.1f%% 超过阈值 %.0f%%%n",
                            usageRate * 100, threshold * 100);
                    // 实际开发中：发送钉钉/邮件告警
                    // alertService.send("JVM 内存超阈值", usageRate);
                }

                try {
                    Thread.sleep(5000);  // 每 5 秒采样一次
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }, "memory-monitor");
        monitor.setDaemon(true);  // 设为守护线程，不阻止 JVM 退出
        monitor.start();
    }
}

// 使用
new MemoryMonitor(0.8).start();
```

> 💡 生产环境用 Prometheus + Grafana + JMX Exporter 做专业监控，但理解 `Runtime` 三个内存方法的含义是看懂监控图表的前提。

### 案例 7：用 nanoTime 对比两种字符串拼接性能 ⭐

```java
// ✅ 用 nanoTime 精确对比 StringBuilder 与 + 拼接的性能差异
public class StringBenchmark {
    public static void main(String[] args) {
        int count = 100000;

        // 方式一：StringBuilder
        long t1 = System.nanoTime();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < count; i++) {
            sb.append("a");
        }
        String result1 = sb.toString();
        long t2 = System.nanoTime();
        System.out.println("StringBuilder：" + (t2 - t1) / 1_000_000.0 + " ms");

        // 方式二：+ 拼接（循环内每次都 new StringBuilder，慢得多）
        long t3 = System.nanoTime();
        String result2 = "";
        for (int i = 0; i < count; i++) {
            result2 = result2 + "a";  // ❌ 每次循环都创建新对象
        }
        long t4 = System.nanoTime();
        System.out.println("+ 拼接：" + (t4 - t3) / 1_000_000.0 + " ms");

        // 对比：+ 拼接比 StringBuilder 慢几个数量级
    }
}
```

> 💡 这是 `nanoTime` 的典型场景——操作本身耗时在毫秒级以下，`currentTimeMillis` 的粒度不够，必须用纳秒计时。

---

## 🚀 新版本补充

### Java 9：ProcessHandle API

Java 9 新增 `ProcessHandle`，可以更方便地管理进程树、获取 PID、监听进程退出：

```java
// Java 9+：ProcessHandle
Process proc = new ProcessBuilder("notepad.exe").start();
ProcessHandle handle = proc.toHandle();

System.out.println("PID：" + handle.pid());
System.out.println("子进程：" + handle.descendants().count());

// 异步监听进程退出
handle.onExit().thenAccept(h -> {
    System.out.println("进程 " + h.pid() + " 已退出");
});
```

### Java 9：ProcessBuilder 更强的管道支持

```java
// Java 9+：支持管道符 |
ProcessBuilder pb = new ProcessBuilder("ls")
    .redirectOutput(new ProcessBuilder("grep", ".java")
        .redirectOutput(ProcessBuilder.Redirect.INHERIT)
        .start()
        .getInputStream()...);
// Java 9 的 startPipeline 方法支持多进程管道
List<Process> pipeline = new ProcessBuilder("ls")
        .command("grep", ".java")
        .startPipeline(...);
```

### Java 10+：容器感知增强

Java 8 早期版本在 Docker 容器里 `availableProcessors()` 会返回宿主机核数（而非容器限制），导致线程池配置错误。Java 8u131+ 和 Java 10+ 增强了容器感知：

```java
// Java 10+ 默认识别容器限制
int cores = Runtime.getRuntime().availableProcessors();
// 在 Docker --cpus=2 的容器里，Java 10+ 返回 2（Java 8 早期返回宿主机核数）
```

> ⚠️ Java 8 需加参数 `-XX:+UnlockExperimentalVMOptions -XX:+UseCGroupMemoryLimitForHeap` 才能识别容器内存限制，Java 8u191+ 默认支持。

### Java 18：System.getenv 的快照语义明确化

Java 18 明确了 `System.getenv()` 返回的是环境变量的**不可变快照**，并在文档中强调环境变量在进程生命周期内不可变（即使操作系统层面修改，JVM 内的快照也不会更新）。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| `System.currentTimeMillis()` | 毫秒时间戳，可换算日期，测粗粒度耗时 |
| `System.nanoTime()` | 纳秒计时，仅用于算差，绝对值无意义 |
| `System.arraycopy()` | 高效数组复制，5 参数：源、源位、目、目位、长 |
| `getProperty/setProperty` | 读写 JVM 系统属性，`-D` 启动注入 |
| `getenv` | 读取 OS 环境变量，只读不可改 |
| `System.out/err/in` | 标准输出/错误/输入流，可重定向 |
| `System.exit(n)` | 退出 JVM，0 正常，跳过 finally |
| `System.gc()` | 建议垃圾回收，不保证执行，生产慎用 |
| `Runtime.getRuntime()` | 单例获取，`System.gc/exit` 底层都调它 |
| `availableProcessors()` | 逻辑 CPU 核数，线程池大小依据 |
| `maxMemory/totalMemory/freeMemory` | 堆上限/已分配/已分配空闲，`used=total-free` |
| `exec` | 执行外部命令，必须读输出流，推荐 ProcessBuilder |
| `addShutdownHook` | 注册关闭钩子，kill -9/OOM 时不执行 |

---

## 学习建议

1. **动手跑一遍内存三方法**：写个程序打印 `maxMemory`、`totalMemory`、`freeMemory`，再调 `System.gc()` 后看变化，亲眼理解三者关系——这是面试高频题，光看文字记不牢。
2. **用 arraycopy 手写一次动态数组**：模仿 ArrayList 的扩容逻辑，理解 `System.arraycopy` 为什么比 `for` 循环快（本地方法、内存拷贝），这是集合框架的地基。
3. **写一个带关闭钩子的程序**：注册一个关闭钩子，分别用 `Ctrl+C`、`kill -15`、`kill -9` 测试，观察哪些场景钩子会执行——理解优雅停机的边界，对排查线上问题至关重要。
4. **警惕 exec 的两个坑**：命令含空格用数组、必须读子进程输出流。建议直接用 `ProcessBuilder` 而非 `exec`，养成习惯能避免一半的进程操作 bug。
5. **区分系统属性与环境变量**：记住「系统属性是 JVM 的、可改、用 `-D` 注入；环境变量是 OS 的、只读、跨进程共享」。配置中心、容器化部署中两者混用，搞混会排查很久。
