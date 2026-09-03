# 标准 IO、RandomAccessFile 与 Properties

Java 的 I/O 体系中，有三个「老牌劲旅」经常被新手忽略，却贯穿真实开发：`System.in/out/err` 是 JVM 与外界交互的三条标准通道；`RandomAccessFile` 是唯一能「随机定位读写」文件的类，断点续传、多线程下载都靠它；`Properties` 是 Java 配置文件的事实标准，从 JDBC 连接信息到 Spring Boot 的 `application.properties`，底层都是它。本篇把三者放一起讲，因为它们都是「文件与程序之间的桥梁」——理解它们，就掌握了 Java 处理配置、键盘输入、文件随机读写的核心能力。

> 💡 在阅读本篇前，建议先看 [22-System与Runtime类](22-System与Runtime类.md) 中关于 `System.out/err/in` 的基本介绍，以及 [27-Map](27-Map：HashMap底层与TreeMap.md)——`Properties` 继承自 `Hashtable`，理解 Map 再看 Properties 会很自然。

---

## 一、标准输入输出流

JVM 启动时会自动打开三条「标准通道」，它们都是 `System` 类的静态字段：

| 字段 | 类型 | 方向 | 默认指向 |
| :--- | :--- | :--- | :--- |
| `System.in` | `InputStream` | 输入 | 键盘（控制台） |
| `System.out` | `PrintStream` | 输出 | 控制台（黑色文字） |
| `System.err` | `PrintStream` | 错误输出 | 控制台（红色文字） |

> 💡 **记忆要点**：`out` 和 `err` 都是 `PrintStream`（高级流，自带 `println`、自动 flush），而 `in` 是「裸」的 `InputStream`（字节流，得自己包装成 `Scanner` 或 `BufferedReader` 才好用）。

### 1.1 System.out 与 System.err

```java
// ✅ 标准输出：普通信息
System.out.println("这是普通日志，控制台默认黑色");

// ✅ 标准错误：错误信息（IDE 控制台通常显示红色）
System.err.println("这是错误日志，控制台默认红色");

// ⚠️ out 和 err 是两个独立的流，输出顺序不保证
System.out.println("第一行");
System.err.println("第二行");
// 实际运行可能先打印"第二行"（红色），因为两个流刷新时机不同
```

> ⚠️ **常见坑**：`System.out` 和 `System.err` 是两个独立的流，混用时输出顺序可能与代码顺序不一致。调试时如果看到日志乱序，多半是这个原因。建议同一逻辑块内只用一个流。

### 1.2 System.in：读取键盘输入

`System.in` 是字节流，直接读不方便，通常用 `Scanner` 或 `BufferedReader` 包装：

```java
import java.util.Scanner;
import java.io.BufferedReader;
import java.io.InputStreamReader;

// ✅ 方式一：Scanner（最常用，简单场景首选）
Scanner scanner = new Scanner(System.in);
System.out.print("请输入用户名：");
String name = scanner.nextLine();   // 读整行
System.out.print("请输入年龄：");
int age = scanner.nextInt();        // 读整数
System.out.println("你好，" + name + "，年龄 " + age);
scanner.close();  // ⚠️ System.in 被关闭后不能再打开，慎用

// ✅ 方式二：BufferedReader（大文本、按行读效率高）
BufferedReader reader = new BufferedReader(
        new InputStreamReader(System.in, "UTF-8"));
System.out.print("请输入命令：");
String command = reader.readLine();  // 读一行
System.out.println("执行命令：" + command);
```

> ⚠️ **不要随便 close Scanner(System.in)**：`Scanner.close()` 会关闭底层的 `System.in`，而 `System.in` 关闭后整个 JVM 内无法再读键盘。如果多处用到 `System.in`，建议不要 close，或用单独的「共享 Scanner」。

### 1.3 重定向标准流：setIn / setOut / setErr

`System` 提供三个静态方法可以「换掉」标准流的方向，常用于日志采集、自动化测试：

```java
import java.io.PrintStream;
import java.io.FileOutputStream;
import java.io.FileInputStream;

// ✅ 把 System.out 重定向到日志文件（程序日志落盘）
PrintStream fileOut = new PrintStream(
        new FileOutputStream("app.log", true), true, "UTF-8");
System.setOut(fileOut);
System.out.println("这行会写入 app.log，而不是控制台");

// ✅ 把 System.err 重定向到错误日志
PrintStream fileErr = new PrintStream(
        new FileOutputStream("error.log", true), true, "UTF-8");
System.setErr(fileErr);
System.err.println("这行会写入 error.log");

// ✅ 把 System.in 重定向到文件（模拟键盘输入，常用于自动化测试）
System.setIn(new FileInputStream("input.txt"));
Scanner sc = new Scanner(System.in);
while (sc.hasNextLine()) {
    System.out.println("读到：" + sc.nextLine());
}

// ⚠️ 恢复前先保存原流
PrintStream originalOut = System.out;  // 先保存
// ... 重定向操作 ...
System.setOut(originalOut);            // 恢复
```

> 📌 **规范**：重定向后务必在合适时机**恢复原流**（先保存 `System.out` 再 set，用完再 set 回去），否则后续所有 `println` 都会「消失」到文件里，排查问题会很困惑。生产环境一般用日志框架（Logback/Log4j2）而非直接重定向 `System.out`。

---

## 二、RandomAccessFile 概述

`java.io.RandomAccessFile` 是 Java 中**唯一**支持「随机读写」的文件类——其他流（`FileInputStream`、`FileWriter` 等）只能从头到尾顺序读或写，而 `RandomAccessFile` 可以通过指针任意跳转到文件的任意位置，既能读又能写。

| 特性 | 说明 |
| :--- | :--- |
| **可读可写** | 一个对象既能读又能写（其他流要么读要么写） |
| **随机定位** | `seek(long)` 跳到任意字节位置 |
| **指针跟踪** | `getFilePointer()` 返回当前指针位置 |
| **支持多种类型** | `readInt/writeInt`、`readUTF/writeUTF`、`readDouble` 等 |
| **直接操作文件** | 不经过缓冲流，适合大文件分块 |

### 2.1 构造方法与模式

```java
import java.io.RandomAccessFile;
import java.io.File;

// 构造方法：RandomAccessFile(File file, String mode) 或 (String name, String mode)
RandomAccessFile raf = new RandomAccessFile("data.dat", "rw");  // 读写模式
RandomAccessFile raf2 = new RandomAccessFile(new File("data.dat"), "r");  // 只读模式
```

| 模式 | 含义 |
| :--- | :--- |
| `r` | 只读。文件不存在会抛 `FileNotFoundException` |
| `rw` | 读写。文件不存在会自动创建；打开时不强制同步 |
| `rws` | 读写，且每次写操作都**同步**刷新到存储（内容+元数据） |
| `rwd` | 读写，且每次写操作都同步刷新**内容**（不保证元数据） |

> ⚠️ `rws`/`rwd` 模式每次写都刷盘，数据安全但**性能差**，仅用于关键数据（如金融交易日志）。普通场景用 `rw` 即可，由 OS 决定何时落盘。

### 2.2 指针操作：seek / getFilePointer / length

```java
RandomAccessFile raf = new RandomAccessFile("data.dat", "rw");

// ✅ 写入一些数据
raf.writeUTF("Hello");   // 写一个 UTF 字符串
raf.writeInt(12345);     // 写一个 int（4 字节）
raf.writeDouble(3.14);   // 写一个 double（8 字节）

System.out.println("当前指针：" + raf.getFilePointer());  // 指向末尾
System.out.println("文件长度：" + raf.length());

// ✅ 跳回开头重新读
raf.seek(0);  // 指针移到文件开头
System.out.println("读字符串：" + raf.readUTF());   // Hello
System.out.println("读 int：" + raf.readInt());     // 12345
System.out.println("读 double：" + raf.readDouble()); // 3.14

// ✅ 跳到任意位置读写（断点续传的核心）
raf.seek(5);  // 跳到第 5 字节，覆盖原来的 int
raf.writeInt(99999);

raf.close();
```

> 💡 **核心记忆**：`RandomAccessFile` 像一个「带光标的文件」——`seek` 移动光标，`getFilePointer` 看光标在哪，`length` 看文件多长。读写操作都从光标位置开始，读完光标自动后移。

### 2.3 读写各种类型的方法

| 写方法 | 读方法 | 字节数 |
| :--- | :--- | :--- |
| `write(int)` | `read()` | 1（只取低 8 位） |
| `writeByte(int)` | `readByte()` | 1 |
| `writeShort(int)` | `readShort()` | 2 |
| `writeInt(int)` | `readInt()` | 4 |
| `writeLong(long)` | `readLong()` | 8 |
| `writeFloat(float)` | `readFloat()` | 4 |
| `writeDouble(double)` | `readDouble()` | 8 |
| `writeBoolean(boolean)` | `readBoolean()` | 1 |
| `writeChar(int)` | `readChar()` | 2（UTF-16） |
| `writeUTF(String)` | `readUTF()` | 变长（前 2 字节是长度） |
| `write(byte[])` | `readFully(byte[])` | 按数组长度 |

```java
RandomAccessFile raf = new RandomAccessFile("record.dat", "rw");

// ✅ 写入一条「记录」：id(int) + 姓名(UTF) + 余额(double) + 是否VIP(boolean)
raf.writeInt(1001);
raf.writeUTF("张三");
raf.writeDouble(9999.50);
raf.writeBoolean(true);

// ✅ 读取时必须按写入顺序、对应类型读，否则数据错乱
raf.seek(0);
int id = raf.readInt();           // 1001
String name = raf.readUTF();      // 张三
double balance = raf.readDouble(); // 9999.5
boolean isVip = raf.readBoolean(); // true
System.out.printf("id=%d, name=%s, balance=%.2f, vip=%s%n", id, name, balance, isVip);

raf.close();
```

> ⚠️ **读写顺序必须严格对应**：`writeInt` 写的必须用 `readInt` 读，`writeUTF` 写的必须用 `readUTF` 读。用错类型读出来的数据全是乱码，这是 `RandomAccessFile` 最容易踩的坑。

### 2.4 定长记录：实现「按记录随机读取」

`RandomAccessFile` 的精髓在于**定长记录**——如果每条记录占用固定字节数，就能用 `seek(记录序号 * 记录长度)` 直接跳到第 N 条记录，无需遍历前面所有数据。这是数据库索引的基础思想。

```java
import java.io.RandomAccessFile;
import java.io.IOException;

// ✅ 定长记录：每条记录固定 32 字节（id=4 + name=20 + age=4 + salary=8 - 实际用 writeUTF 不定长）
// 为保证定长，姓名用固定字节数组存储
public class FixedRecordFile {
    private static final int NAME_LEN = 20;  // 姓名固定 20 字节
    private static final int RECORD_LEN = 4 + NAME_LEN + 4 + 8;  // 36 字节/条

    // 写一条记录到指定位置
    public static void writeRecord(RandomAccessFile raf, int index,
                                   int id, String name, int age, double salary) throws IOException {
        raf.seek((long) index * RECORD_LEN);  // 跳到第 index 条
        raf.writeInt(id);

        // 姓名补成定长 20 字节
        byte[] nameBytes = new byte[NAME_LEN];
        byte[] src = name.getBytes("UTF-8");
        System.arraycopy(src, 0, nameBytes, 0, Math.min(src.length, NAME_LEN));
        raf.write(nameBytes);

        raf.writeInt(age);
        raf.writeDouble(salary);
    }

    // 读第 index 条记录
    public static String readRecord(RandomAccessFile raf, int index) throws IOException {
        raf.seek((long) index * RECORD_LEN);
        int id = raf.readInt();
        byte[] nameBytes = new byte[NAME_LEN];
        raf.readFully(nameBytes);
        String name = new String(nameBytes, "UTF-8").trim();
        int age = raf.readInt();
        double salary = raf.readDouble();
        return String.format("id=%d, name=%s, age=%d, salary=%.2f", id, name, age, salary);
    }

    public static void main(String[] args) throws IOException {
        try (RandomAccessFile raf = new RandomAccessFile("users.dat", "rw")) {
            writeRecord(raf, 0, 1, "张三", 28, 15000.0);
            writeRecord(raf, 1, 2, "李四", 35, 25000.0);
            writeRecord(raf, 2, 3, "王五", 22, 8000.0);

            // ✅ 直接读第 2 条，无需遍历前两条
            System.out.println(readRecord(raf, 2));  // 王五
            System.out.println(readRecord(raf, 0));  // 张三
        }
    }
}
```

> 💡 这就是数据库「按主键随机查询」的雏形——B+ 树的叶子节点存的是「文件偏移量」，定位后用类似 `seek + read` 的方式读取记录。理解定长记录，就理解了为什么数据库要规定字段最大长度。

---

## 三、Properties 概述

`java.util.Properties` 是 `Hashtable` 的子类，专门用于存储**字符串键值对**配置。它是 Java 处理 `.properties` 配置文件的标准工具，从 JDBC 连接配置到 Spring Boot 的 `application.properties`，底层都是它。

### 3.1 Properties 的本质

```java
import java.util.Properties;
import java.util.Map;

// ✅ Properties 继承自 Hashtable<Object,Object>，但约定 key 和 value 都是 String
Properties props = new Properties();

// ✅ 推荐用 setProperty / getProperty（类型安全，强制 String）
props.setProperty("url", "jdbc:mysql://localhost:3306/db");
props.setProperty("user", "root");
props.setProperty("password", "123456");

String url = props.getProperty("url");         // jdbc:mysql://...
String timeout = props.getProperty("timeout", "5000");  // 不存在给默认值 ✅ 防空指针

// ⚠️ 也可以用 put/get（继承自 Hashtable），但不推荐
props.put("count", 123);          // ❌ 能编译运行，但 value 不是 String
Object count = props.get("count"); // 返回 Object，类型不安全
// props.getProperty("count");     // 返回 null！getProperty 只认 String value
```

> ⚠️ **Properties 的 key 和 value 约定都是 String**。虽然继承 `Hashtable` 可以 `put` 任意对象，但 `getProperty` 只能读出 String 类型的 value，非 String 的 value 用 `getProperty` 会返回 `null`。**永远只用 `setProperty` / `getProperty`**，不要用 `put` / `get`。

| 方法 | 说明 |
| :--- | :--- |
| `setProperty(String key, String value)` | 设置键值对（等价于 `put` 但限定 String） |
| `getProperty(String key)` | 取值，不存在返回 `null` |
| `getProperty(String key, String defaultValue)` | 取值，不存在返回默认值 |
| `stringPropertyNames()` | 返回所有 key 的 `Set<String>` |
| `load(InputStream)` | 从字节流加载 `.properties` |
| `load(Reader)` | 从字符流加载（Java 6+，支持指定编码） |
| `store(OutputStream, String comment)` | 写入 `.properties`，第二参数是注释 |
| `store(Writer, String comment)` | 用字符流写入 |
| `loadFromXML(InputStream)` | 从 XML 加载 |
| `storeToXML(OutputStream, String comment)` | 写入 XML 格式 |
| `list(PrintStream)` | 打印到输出流（调试用） |

### 3.2 .properties 文件格式

```properties
# 这是注释，以 # 或 ! 开头
# 数据库连接配置（JDBC 经典场景）
url = jdbc:mysql://localhost:3306/order_db
user = root
password = 123456

# 等号两边空格会被忽略
pool.size = 10
timeout = 5000

# 多行不用引号，值就是等号后面的全部内容（去除首尾空格）
app.name = 订单服务

# 特殊字符：= 和 : 是分隔符，值里要用就得转义
formula = 1\=1
path = C\:\\Java\\jdk
```

> 💡 **`.properties` 文件规则**：① 注释以 `#` 或 `!` 开头；② 分隔符是 `=` 或 `:`（推荐 `=`）；③ 等号两边的空格自动去除；④ 值里的 `=`、`:`、`#` 要用 `\` 转义；⑤ 默认用 ISO-8859-1 编码（Java 6 起支持 `load(Reader)` 指定编码）。

### 3.3 读取 .properties 文件：load

```java
import java.util.Properties;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;

// ✅ 方式一：从字节流加载（默认 ISO-8859-1，中文会乱码）
try (InputStream in = new FileInputStream("config.properties")) {
    Properties props = new Properties();
    props.load(in);
    String url = props.getProperty("url");
    System.out.println("url = " + url);
}

// ✅ 方式二：用 Reader 加载，指定 UTF-8（解决中文乱码，推荐）
try (InputStreamReader reader = new InputStreamReader(
        new FileInputStream("config.properties"), "UTF-8")) {
    Properties props = new Properties();
    props.load(reader);
    String appName = props.getProperty("app.name");
    System.out.println("app.name = " + appName);  // 订单服务
}

// ✅ 方式三：从 classpath 加载（最常用，配置文件随 jar 打包）
try (InputStream in = MyApp.class.getClassLoader()
        .getResourceAsStream("config.properties")) {
    if (in != null) {
        Properties props = new Properties();
        props.load(in);
        // ...
    }
}
```

> ⚠️ **中文乱码坑**：`load(InputStream)` 默认用 ISO-8859-1 编码，`.properties` 文件里有中文会乱码。解决办法：① 用 `load(Reader)` 包装 `InputStreamReader(in, "UTF-8")`；② 或文件里用 `native2ascii` 转成 `\uXXXX` 形式（老式做法）。Java 9+ 的 `.properties` 默认 UTF-8，见文末新版本补充。

### 3.4 写入 .properties 文件：store

```java
import java.util.Properties;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.IOException;

Properties props = new Properties();
props.setProperty("url", "jdbc:mysql://localhost:3306/db");
props.setProperty("user", "root");
props.setProperty("password", "123456");
props.setProperty("pool.size", "10");

// ✅ 写入文件（第二参数是文件头注释，会自动加时间戳）
try (FileOutputStream out = new FileOutputStream("db.properties")) {
    props.store(out, "Database Configuration");
    // 文件内容：
    // #Database Configuration
    // #Thu Sep 03 10:00:00 CST 2026
    // url=jdbc:mysql://localhost:3306/db
    // user=root
    // password=123456
    // pool.size=10
}

// ✅ 用 Writer 写入，指定 UTF-8（避免中文乱码）
try (OutputStreamWriter writer = new OutputStreamWriter(
        new FileOutputStream("db.properties"), "UTF-8")) {
    props.store(writer, "Database Configuration");
}
```

> 💡 `store` 会自动在文件头加一行时间戳注释（如 `#Thu Sep 03 10:00:00 CST 2026`），这是它的特性。如果不想要时间戳，只能自己用 `BufferedWriter` 手写键值对。

### 3.5 读取 XML 格式配置：loadFromXML

```java
import java.util.Properties;
import java.io.FileInputStream;
import java.io.InputStream;

// ✅ 从 XML 加载（XML 文件天然支持 UTF-8，无中文乱码问题）
try (InputStream in = new FileInputStream("config.xml")) {
    Properties props = new Properties();
    props.loadFromXML(in);
    String url = props.getProperty("url");
}
```

XML 格式示例（`config.xml`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <comment>数据库配置</comment>
    <entry key="url">jdbc:mysql://localhost:3306/db</entry>
    <entry key="user">root</entry>
    <entry key="password">123456</entry>
</properties>
```

```java
// ✅ 写成 XML
try (FileOutputStream out = new FileOutputStream("config.xml")) {
    props.storeToXML(out, "数据库配置", "UTF-8");
}
```

> 💡 XML 格式的好处是天然支持 UTF-8、结构清晰，但体积比 `.properties` 大，实际开发中 `.properties` 更主流，XML 格式较少见。

### 3.6 System.getProperties()：JVM 系统属性

`System.getProperties()` 返回的就是一个 `Properties` 对象，包含 JVM 启动时的所有系统属性：

```java
import java.util.Properties;

// ✅ 获取 JVM 系统属性
Properties sysProps = System.getProperties();
String javaVersion = sysProps.getProperty("java.version");     // 1.8.0_301
String osName = sysProps.getProperty("os.name");               // Windows 10
String userDir = sysProps.getProperty("user.dir");             // 当前工作目录

// ✅ 打印所有系统属性（调试用）
sysProps.list(System.out);

// ✅ 直接用 System.getProperty 更简洁
String v = System.getProperty("java.version");
String env = System.getProperty("app.env", "dev");  // 带默认值
```

> 💡 这就是 [22-System与Runtime类](22-System与Runtime类.md) 中 `System.getProperty` 的底层——它返回的 `Properties` 就是 `Hashtable` 子类，所以可以用 `getProperty`、`stringPropertyNames` 等。

### 3.7 Properties 与 Map 的关系

```
Map<String,String> 接口
    ↑
Hashtable<Object,Object>（线程安全，遗留集合）
    ↑
Properties（key/value 约定 String，支持 load/store）
```

```java
import java.util.Properties;
import java.util.Enumeration;

// ✅ 遍历方式一：stringPropertyNames（推荐，Java 6+）
Properties props = new Properties();
props.setProperty("a", "1");
props.setProperty("b", "2");
for (String key : props.stringPropertyNames()) {
    System.out.println(key + " = " + props.getProperty(key));
}

// ✅ 遍历方式二：entrySet（继承自 Hashtable）
for (Object o : props.entrySet()) {
    java.util.Map.Entry<?, ?> entry = (java.util.Map.Entry<?, ?>) o;
    System.out.println(entry.getKey() + " = " + entry.getValue());
}

// ✅ 遍历方式三：Enumeration（老式，Java 1.0）
Enumeration<?> names = props.propertyNames();
while (names.hasMoreElements()) {
    String key = (String) names.nextElement();
    System.out.println(key + " = " + props.getProperty(key));
}
```

> ⚠️ **Properties 是线程安全的**（继承 `Hashtable`），但性能较差。高并发配置读取场景，通常用 `ConcurrentHashMap` 或 Spring 的 `Environment` 抽象，而非直接用 `Properties`。`Properties` 主要用于「启动时加载一次」的场景。

---

## ⚠️ 重点

### 重点 1：RandomAccessFile 的读写顺序必须严格对应 ⭐⭐⭐

```java
RandomAccessFile raf = new RandomAccessFile("d.dat", "rw");
raf.writeInt(100);
raf.writeUTF("hello");
raf.writeDouble(3.14);

raf.seek(0);
// ✅ 必须按写入顺序和类型读
int n = raf.readInt();        // 100
String s = raf.readUTF();     // hello
double d = raf.readDouble();  // 3.14

// ❌ 错误：类型读错，后续全部错乱
raf.seek(0);
// String wrong = raf.readUTF();  // 把 int 的 4 字节当 UTF 长度读，结果乱码或抛异常
```

> ⚠️ `RandomAccessFile` 不记录字段边界，它只认字节。你写什么类型就必须读什么类型，顺序也不能乱。这是它和序列化（`ObjectOutputStream`）的区别——序列化会记录对象结构，`RandomAccessFile` 不会。

### 重点 2：seek 跳转后读写覆盖原内容 ⭐⭐

```java
RandomAccessFile raf = new RandomAccessFile("d.dat", "rw");
raf.writeBytes("ABCDEFGHIJ");  // 10 字节
raf.seek(3);                   // 跳到第 3 字节（D 的位置）
raf.writeBytes("XYZ");         // 覆盖 DEF，变成 ABCXYZGHIJ
// ⚠️ 不是插入，是覆盖！seek + write 不会把后面的数据后移
raf.close();
```

> ⚠️ `RandomAccessFile` 的写是**覆盖**，不是插入。想在中间插入数据，必须先把后面的数据读出来，写完新数据再写回去。这是实现「文件编辑器」的难点。

### 重点 3：Properties 的 getProperty 与 get 的区别 ⭐⭐

```java
Properties props = new Properties();
props.put("count", 123);          // ❌ 用了 put，value 是 Integer

// ⚠️ getProperty 只认 String value，非 String 返回 null
String c1 = props.getProperty("count");  // null！
Object c2 = props.get("count");          // 123（Hashtable.get 返回 Object）

// ✅ 正确做法：永远用 setProperty，保证 value 是 String
props.setProperty("count", "123");
String c3 = props.getProperty("count");  // 123
```

> 📌 **规范**：操作 `Properties` 永远只用 `setProperty` / `getProperty`，不要用继承来的 `put` / `get` / `putAll`。否则 value 类型混乱，`store` 时可能抛 `ClassCastException`。

### 重点 4：load(InputStream) 默认 ISO-8859-1 导致中文乱码 ⭐⭐

```java
// ❌ 错误：load(InputStream) 默认 ISO-8859-1，中文乱码
Properties props = new Properties();
try (FileInputStream in = new FileInputStream("config.properties")) {
    props.load(in);
}
System.out.println(props.getProperty("app.name"));  // ???

// ✅ 正确：用 load(Reader) 指定 UTF-8
try (InputStreamReader reader = new InputStreamReader(
        new FileInputStream("config.properties"), "UTF-8")) {
    Properties props2 = new Properties();
    props2.load(reader);
}
```

> ⚠️ 这是 `Properties` 最经典的坑。Java 8 的 `load(InputStream)` 强制用 ISO-8859-1，中文必须用 `\uXXXX` 转义或用 `load(Reader)`。Java 9 才把 `.properties` 默认编码改成 UTF-8。

### 重点 5：RandomAccessFile 的 rws/rwd 模式性能差 ⭐

```java
// ❌ 关键数据才用 rws/rwd，普通场景别用
RandomAccessFile raf = new RandomAccessFile("data.dat", "rws");  // 每次写都刷盘，极慢

// ✅ 普通场景用 rw，由 OS 决定刷盘时机
RandomAccessFile raf2 = new RandomAccessFile("data.dat", "rw");

// ✅ 金融交易日志等关键数据才用 rwd
RandomAccessFile raf3 = new RandomAccessFile("txn.log", "rwd");
```

> 💡 `rws` 每次写都同步刷内容和元数据，`rwd` 只刷内容。两者都比 `rw` 慢一个数量级。只有「绝对不能丢」的数据才用，如交易流水、WAL 日志。

### 重点 6：System.in 关闭后无法重开 ⭐

```java
Scanner sc = new Scanner(System.in);
String line = sc.nextLine();
sc.close();  // ⚠️ 关闭了 System.in

// ❌ 再读就抛 IllegalStateException: System.in closed
Scanner sc2 = new Scanner(System.in);
sc2.nextLine();  // 异常
```

> ⚠️ `System.in` 是 JVM 级别的单例流，关闭后整个 JVM 内无法再读键盘。如果多处要用，建议封装一个共享的 Scanner，或在程序退出前才 close。

---

## 💻 实战案例

### 案例 1：RandomAccessFile 实现断点续传 ⭐⭐⭐

下载大文件时网络中断，重新下载从头开始太浪费。用 `RandomAccessFile` 记录已下载位置，下次从断点继续：

```java
import java.io.RandomAccessFile;
import java.io.InputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.File;

// ✅ 断点续传下载器（这里用本地文件模拟"网络源"）
public class ResumeDownloader {
    private final File targetFile;       // 下载目标文件
    private final long chunkSize;        // 每次下载的块大小

    public ResumeDownloader(String targetPath, long chunkSize) {
        this.targetFile = new File(targetPath);
        this.chunkSize = chunkSize;
    }

    public void download(String sourcePath) throws IOException {
        File source = new File(sourcePath);
        long totalSize = source.length();

        // ✅ 用 rw 模式打开目标文件，不存在会自动创建
        try (RandomAccessFile raf = new RandomAccessFile(targetFile, "rw");
             InputStream in = new FileInputStream(source)) {

            // ✅ 关键：从已下载位置继续（这里用文件长度判断已下载量）
            long downloaded = targetFile.length();
            if (downloaded > 0) {
                System.out.println("检测到已下载 " + downloaded + " 字节，从断点续传");
                // 源流也要跳过已下载部分（真实场景是 HTTP Range 请求）
                in.skip(downloaded);
                raf.seek(downloaded);  // 目标文件指针移到断点
            } else {
                raf.setLength(totalSize);  // ✅ 预分配文件大小，防止碎片
            }

            byte[] buffer = new byte[(int) chunkSize];
            int len;
            while ((len = in.read(buffer)) != -1) {
                raf.write(buffer, 0, len);
                downloaded += len;
                // ✅ 打印进度
                System.out.printf("下载进度：%.1f%%%n", downloaded * 100.0 / totalSize);
            }
            System.out.println("下载完成，总大小：" + downloaded);
        }
    }

    public static void main(String[] args) throws IOException {
        // 模拟：把大文件分块下载到目标
        ResumeDownloader downloader = new ResumeDownloader("downloaded.bin", 1024);
        downloader.download("source.bin");
        // 中断后再次运行，会从断点继续
    }
}
```

> 💡 真实的断点续传（如迅雷、IDM）通过 HTTP `Range: bytes=1000-` 请求服务端返回指定范围的数据，再用 `RandomAccessFile.seek` 写到对应位置。核心思想完全一致：**记录已下载位置，下次从断点继续**。

### 案例 2：多线程下载分块写入 ⭐⭐⭐

大文件分块下载，每个线程负责一块，用 `RandomAccessFile.seek` 写到各自位置，互不干扰：

```java
import java.io.RandomAccessFile;
import java.io.InputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.File;

// ✅ 多线程分块下载器
public class MultiThreadDownloader {
    private final String sourcePath;
    private final String targetPath;
    private final int threadCount;

    public MultiThreadDownloader(String sourcePath, String targetPath, int threadCount) {
        this.sourcePath = sourcePath;
        this.targetPath = targetPath;
        this.threadCount = threadCount;
    }

    public void download() throws IOException, InterruptedException {
        File source = new File(sourcePath);
        long fileSize = source.length();
        long chunkSize = fileSize / threadCount;  // 每块大小

        // ✅ 关键：预分配目标文件大小
        try (RandomAccessFile raf = new RandomAccessFile(targetPath, "rw")) {
            raf.setLength(fileSize);
        }

        Thread[] threads = new Thread[threadCount];
        for (int i = 0; i < threadCount; i++) {
            final int index = i;
            final long start = i * chunkSize;
            // 最后一块要包含剩余所有字节
            final long end = (i == threadCount - 1) ? fileSize : (start + chunkSize);

            threads[i] = new Thread(() -> {
                try (RandomAccessFile raf = new RandomAccessFile(targetPath, "rw");
                     InputStream in = new FileInputStream(source)) {
                    // ✅ 源流跳到本块起点
                    in.skip(start);
                    // ✅ 目标文件指针也跳到本块起点
                    raf.seek(start);

                    byte[] buffer = new byte[8192];
                    long remaining = end - start;
                    while (remaining > 0) {
                        int toRead = (int) Math.min(buffer.length, remaining);
                        int len = in.read(buffer, 0, toRead);
                        if (len == -1) break;
                        raf.write(buffer, 0, len);
                        remaining -= len;
                    }
                    System.out.println("线程 " + index + " 完成块 [" + start + ", " + end + ")");
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }, "downloader-" + index);
            threads[i].start();
        }

        // ✅ 等待所有线程完成
        for (Thread t : threads) t.join();
        System.out.println("全部下载完成");
    }

    public static void main(String[] args) throws Exception {
        new MultiThreadDownloader("source.bin", "downloaded.bin", 4).download();
    }
}
```

> ⚠️ **多线程写同一文件的关键**：每个线程用**独立的 `RandomAccessFile` 实例**（不能共享），各自 `seek` 到自己的块起点，写互不重叠的区域。如果共享一个 `RandomAccessFile`，`seek` 会被其他线程打乱，数据错乱。

### 案例 3：Properties 读取 JDBC 数据库配置 ⭐⭐⭐

这是 `Properties` 最经典的应用场景——把数据库连接信息从代码中剥离到配置文件：

`db.properties`（放在 classpath 下，如 `src/main/resources/`）：

```properties
# 数据库连接配置
url = jdbc:mysql://localhost:3306/order_db?useSSL=false&serverTimezone=Asia/Shanghai
user = root
password = 123456
driver = com.mysql.jdbc.Driver
pool.size = 10
pool.timeout = 5000
```

```java
import java.util.Properties;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

// ✅ 配置加载 + JDBC 连接工具类
public class JdbcUtil {
    private static final Properties props = new Properties();

    // 静态块：类加载时读一次配置
    static {
        // ✅ 从 classpath 加载，用 Reader 指定 UTF-8 避免中文乱码
        try (InputStream in = JdbcUtil.class.getClassLoader()
                .getResourceAsStream("db.properties");
             InputStreamReader reader = new InputStreamReader(in, "UTF-8")) {
            props.load(reader);
            // ✅ 加载驱动（Java 8 必须显式加载，Java 6 起可省略但建议保留）
            Class.forName(props.getProperty("driver"));
        } catch (Exception e) {
            throw new RuntimeException("加载 db.properties 失败", e);
        }
    }

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(
                props.getProperty("url"),
                props.getProperty("user"),
                props.getProperty("password"));
    }

    public static int getPoolSize() {
        return Integer.parseInt(props.getProperty("pool.size", "10"));
    }

    public static void main(String[] args) throws SQLException {
        try (Connection conn = getConnection()) {
            System.out.println("连接成功：" + conn);
            System.out.println("连接池大小：" + getPoolSize());
        }
    }
}
```

> 📌 **规范**：① 配置文件放 `src/main/resources/`，Maven 打包后会进 classpath；② 用 `getResourceAsStream` 而非 `new FileInputStream`，保证 jar 包能找到配置；③ 用 `load(Reader)` 指定 UTF-8。Spring Boot 的 `@Value("${url}")` 底层就是这套机制。

### 案例 4：System.out 重定向到日志文件（简易日志采集）⭐⭐

老系统改造时，第三方库只往 `System.out` 打日志，想收集到文件：

```java
import java.io.PrintStream;
import java.io.FileOutputStream;
import java.io.IOException;

// ✅ 把 System.out 重定向到日志文件，同时保留控制台输出（双写）
public class DualOutputLogger {
    private static PrintStream fileStream;
    private static PrintStream consoleStream;

    public static void redirectToFile(String logPath) throws IOException {
        consoleStream = System.out;  // 保存原流
        fileStream = new PrintStream(new FileOutputStream(logPath, true), true, "UTF-8");

        // ✅ 自定义 PrintStream：同时写文件和控制台
        PrintStream dual = new PrintStream(fileStream, true, "UTF-8") {
            @Override
            public void println(String x) {
                fileStream.println(x);      // 写文件
                consoleStream.println(x);   // 写控制台
            }
            @Override
            public void print(String x) {
                fileStream.print(x);
                consoleStream.print(x);
            }
        };
        System.setOut(dual);
    }

    public static void restore() {
        if (consoleStream != null) {
            System.setOut(consoleStream);
            fileStream.close();
        }
    }

    public static void main(String[] args) throws IOException {
        redirectToFile("app.log");
        System.out.println("这行同时出现在控制台和 app.log");
        System.out.println("第三方库的日志也会被捕获");
        restore();
        System.out.println("恢复后只在控制台");
    }
}
```

> 💡 生产环境用 Logback/Log4j2 的 `ConsoleAppender + FileAppender` 做双写，但理解 `System.setOut` 的原理，对调试老系统和理解日志框架底层很有帮助。

### 案例 5：键盘输入读取命令（简易命令行交互）⭐⭐

后台运维工具常需要交互式命令行：

```java
import java.util.Scanner;

// ✅ 简易命令行交互程序
public class AdminConsole {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        System.out.println("=== 运维控制台 ===");
        System.out.println("命令：status / deploy <app> / restart <app> / exit");

        while (true) {
            System.out.print("> ");
            if (!scanner.hasNextLine()) break;
            String line = scanner.nextLine().trim();

            if (line.isEmpty()) continue;
            if ("exit".equalsIgnoreCase(line)) {
                System.out.println("再见");
                break;
            }

            String[] parts = line.split("\\s+");
            String cmd = parts[0].toLowerCase();
            try {
                switch (cmd) {
                    case "status":
                        System.out.println("系统状态：运行中，CPU 12%，内存 45%");
                        break;
                    case "deploy":
                        if (parts.length < 2) {
                            System.err.println("用法：deploy <app>");
                        } else {
                            System.out.println("部署应用：" + parts[1]);
                        }
                        break;
                    case "restart":
                        if (parts.length < 2) {
                            System.err.println("用法：restart <app>");
                        } else {
                            System.out.println("重启应用：" + parts[1]);
                        }
                        break;
                    default:
                        System.err.println("未知命令：" + cmd);
                }
            } catch (Exception e) {
                System.err.println("执行失败：" + e.getMessage());
            }
        }
    }
}
```

### 案例 6：Properties 实现简易配置中心 ⭐⭐

多个微服务共享一份配置，启动时加载，运行时支持热更新：

```java
import java.util.Properties;
import java.io.InputStreamReader;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.File;

// ✅ 简易配置中心：监听配置文件变化，自动重新加载
public class ConfigCenter {
    private static volatile Properties config = new Properties();
    private static File configFile;
    private static long lastModified;

    // 初始化：加载配置并启动监听线程
    public static void init(String path) {
        configFile = new File(path);
        reload();
        // ✅ 守护线程定时检查文件是否变化
        Thread watcher = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Thread.sleep(5000);
                    if (configFile.lastModified() != lastModified) {
                        reload();
                        System.out.println("[配置中心] 检测到配置变化，已重新加载");
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }, "config-watcher");
        watcher.setDaemon(true);
        watcher.start();
    }

    private static void reload() {
        try (InputStreamReader reader = new InputStreamReader(
                new FileInputStream(configFile), "UTF-8")) {
            Properties newProps = new Properties();
            newProps.load(reader);
            config = newProps;  // ✅ volatile 保证可见性
            lastModified = configFile.lastModified();
        } catch (IOException e) {
            System.err.println("加载配置失败：" + e.getMessage());
        }
    }

    public static String get(String key, String defaultValue) {
        return config.getProperty(key, defaultValue);
    }

    public static void main(String[] args) {
        init("app.properties");
        System.out.println("应用名：" + get("app.name", "unknown"));
        // 修改 app.properties 后会自动重新加载
    }
}
```

> 💡 这是 Apollo、Nacos 等配置中心的雏形——监听配置变化 + volatile 保证可见性。真实配置中心用长连接推送而非轮询，但思想一致。

### 案例 7：RandomAccessFile 实现简易日志追加与按时间范围查询 ⭐⭐

```java
import java.io.RandomAccessFile;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;

// ✅ 定长日志文件：每条 64 字节（时间戳 8 + 级别 4 + 内容 52）
public class LogFile {
    private static final int RECORD_LEN = 64;
    private final String path;

    public LogFile(String path) {
        this.path = path;
    }

    // 追加一条日志
    public void append(long timestamp, String level, String msg) throws IOException {
        try (RandomAccessFile raf = new RandomAccessFile(path, "rw")) {
            raf.seek(raf.length());  // 跳到末尾追加
            raf.writeLong(timestamp);
            raf.writeBytes(pad(level, 4));
            raf.writeBytes(pad(msg, 52));
        }
    }

    // 按序号读一条
    public String read(int index) throws IOException {
        try (RandomAccessFile raf = new RandomAccessFile(path, "r")) {
            raf.seek((long) index * RECORD_LEN);
            long ts = raf.readLong();
            byte[] levelBytes = new byte[4];
            raf.readFully(levelBytes);
            byte[] msgBytes = new byte[52];
            raf.readFully(msgBytes);
            return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date(ts))
                    + " [" + new String(levelBytes).trim() + "] "
                    + new String(msgBytes).trim();
        }
    }

    public int size() throws IOException {
        try (RandomAccessFile raf = new RandomAccessFile(path, "r")) {
            return (int) (raf.length() / RECORD_LEN);
        }
    }

    private String pad(String s, int len) {
        byte[] bytes = s.getBytes();
        String truncated = new String(bytes, 0, Math.min(bytes.length, len));
        return String.format("%-" + len + "s", truncated);
    }

    public static void main(String[] args) throws IOException {
        LogFile log = new LogFile("app.logf");
        log.append(System.currentTimeMillis(), "INFO", "服务启动");
        log.append(System.currentTimeMillis(), "ERROR", "数据库连接失败");
        log.append(System.currentTimeMillis(), "WARN", "内存使用率 85%");

        // ✅ 直接读第 2 条，无需遍历
        System.out.println(log.read(2));  // ERROR 数据库连接失败
        System.out.println("共 " + log.size() + " 条日志");
    }
}
```

> 💡 这就是日志检索的底层思想——定长记录让 `seek(index * len)` 直接定位，无需遍历。真实的 ELK 用倒排索引，但「定长 + 偏移定位」是所有存储系统的基础。

---

## 🚀 新版本补充

### Java 9：Properties 默认 UTF-8

Java 8 的 `load(InputStream)` 强制 ISO-8859-1，中文必须转义或用 `load(Reader)`。Java 9 起，`.properties` 文件默认用 UTF-8 编码：

```java
// Java 9+：load(InputStream) 默认 UTF-8，中文不再乱码
Properties props = new Properties();
try (InputStream in = Files.newInputStream(Paths.get("config.properties"))) {
    props.load(in);
    System.out.println(props.getProperty("app.name"));  // 中文正常显示
}
```

> ⚠️ 从 Java 8 升级到 Java 9 时，如果 `.properties` 文件原本用了 ISO-8859-1 + `\uXXXX` 转义，迁移到 UTF-8 后可能需要重新编码。建议统一用 UTF-8 存储。

### Java 9：Properties.loadFromXML 支持 UTF-8

```java
// Java 9+：loadFromXML 默认 UTF-8，storeToXML 也默认 UTF-8（Java 8 需显式指定）
props.storeToXML(out, "配置", "UTF-8");  // Java 8 必须传编码
// Java 9 起可省略编码参数，默认 UTF-8
```

### Java 7+：try-with-resources 自动关闭 RandomAccessFile

```java
// ✅ Java 7+：RandomAccessFile 实现了 Closeable，可用 try-with-resources
try (RandomAccessFile raf = new RandomAccessFile("d.dat", "rw")) {
    raf.writeInt(100);
}  // 自动 close，无需 finally

// ❌ Java 6 及以前必须手动 finally
RandomAccessFile raf = null;
try {
    raf = new RandomAccessFile("d.dat", "rw");
    raf.writeInt(100);
} finally {
    if (raf != null) raf.close();
}
```

### Java 8：Properties 没有新增方法

Java 8 对 `Properties` 本身没有新增方法，但 `System.getProperties()` 返回的 `Properties` 可以配合 Java 8 的 Stream 使用：

```java
// Java 8：用 Stream 处理系统属性
System.getProperties().stringPropertyNames().stream()
    .filter(k -> k.startsWith("java."))
    .sorted()
    .forEach(k -> System.out.println(k + " = " + System.getProperty(k)));
```

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| `System.in` | `InputStream`，标准输入（键盘），用 `Scanner` 包装 |
| `System.out` / `System.err` | `PrintStream`，标准输出/错误，IDE 红色显示 err |
| `setIn/setOut/setErr` | 重定向标准流，用完要恢复 |
| `RandomAccessFile` | 唯一支持随机读写的文件类，可读可写 |
| 构造模式 | `r` 只读、`rw` 读写、`rws/rwd` 同步刷盘（慢） |
| `seek(long)` | 移动指针到任意位置 |
| `getFilePointer()` | 当前指针位置 |
| `length()` | 文件长度 |
| 读写类型对应 | `writeInt`↔`readInt`，顺序类型必须严格对应 |
| 定长记录 | `seek(index * len)` 实现按记录随机读取 |
| `Properties` | `Hashtable` 子类，key/value 约定 String |
| `load(InputStream/Reader)` | 加载 `.properties`，`Reader` 可指定编码 |
| `store(OutputStream, comment)` | 写入 `.properties`，自动加时间戳 |
| `getProperty/setProperty` | 只操作 String，勿用 `put/get` |
| `System.getProperties()` | 返回 JVM 系统属性的 `Properties` |

---

## 学习建议

1. **手写一次断点续传**：用 `RandomAccessFile` 实现一个本地文件的「分块下载 + 断点续传」，故意中途退出再重跑，体会 `seek` 跳到断点继续写的威力——这是理解多线程下载、HTTP Range 请求的基础。
2. **牢记读写类型对应**：`RandomAccessFile` 不记字段边界，`writeInt` 必须配 `readInt`，顺序也不能乱。建议写一个「写一条记录 → 读一条记录」的小程序，故意用错类型读，看看乱码长什么样，加深印象。
3. **用 Properties 重构 JDBC 配置**：把硬编码的数据库连接信息抽到 `db.properties`，用 `getResourceAsStream` 加载，体会「配置与代码分离」的好处。这是 Spring Boot `application.properties` 的雏形，理解它对学 Spring 很有帮助。
4. **警惕中文乱码**：Java 8 的 `Properties.load(InputStream)` 默认 ISO-8859-1，中文会乱码。养成「永远用 `load(Reader)` + UTF-8」的习惯，能省掉一半的配置乱码问题。升级到 Java 9+ 后默认 UTF-8，但代码规范要统一。
5. **理解定长记录的价值**：`RandomAccessFile` 的精髓是「定长记录 + seek 定位」，这是数据库索引、日志检索的底层思想。建议手写一个定长日志文件，实现「直接读第 N 条」，对比「顺序遍历」的效率差异，体会为什么数据库要规定字段最大长度。
