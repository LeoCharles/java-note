# 字符串 String 与 StringBuilder

字符串是 Java 开发中**使用频率最高**的数据类型——日志、参数、配置、SQL、JSON、HTTP 响应，无一不是字符串。Java 用 `String` 类表示字符串，它是 `final` 修饰的**不可变**类，底层用一个 `final` 的 `char[]`（Java 9 后是 `byte[]`）存储。理解 String 的不可变性、字符串常量池、`==` 与 `equals` 的坑，以及何时该用 `StringBuilder` 替代拼接，是写出正确且高效代码的前提——很多新手在循环里用 `+` 拼字符串导致性能灾难，或用 `==` 比字符串导致永远 false，根因都在这里。

> 💡 在阅读本篇前，建议先看 [02-JVM内存模型](02-JVM内存模型.md) 理解「栈存引用、堆存对象、方法区/元空间存常量池」，再看 [17-Object类与Objects](17-Object类与Objects.md) 理解 `equals` 重写，会更容易理解下面的常量池和字符串比较。

---

## 一、String 类与不可变性

### 1.1 String 是什么

`String` 是 `java.lang` 包下的类，代表**不可变**的字符序列。所有字符串字面量（如 `"hello"`）都是 String 对象。

```java
String s = "hello";   // 字面量创建
String s2 = new String("hello");  // 构造方法创建
```

> 📌 **重要认知**：`String` 是**引用类型**，不是基本类型！比较内容要用 `.equals()`，不能用 `==`（这是新手第一坑，详见重点 1）。

### 1.2 不可变性的本质

`String` 的不可变性来自两个设计：

```java
// String 源码（Java 8）
public final class String {           // ① 类被 final 修饰，不可被继承
    private final char value[];       // ② value 数组被 final 修饰，不可重新指向
    // ... 没有提供修改 value 数组元素的方法
}
```

- `final class`：不能被继承，防止子类破坏不可变性
- `final char[] value`：数组引用不可变，且 String 没有暴露修改数组的方法

所有「看起来修改了字符串」的操作，实际都是**创建新对象**：

```java
String s = "hello";
s = s + " world";   // 不是在原对象上追加，而是 new 了一个新 String "hello world"
System.out.println(s);  // hello world

String s2 = "Java";
s2 = s2.replace('a', 'o');  // 返回新对象 "Jovo"，原 "Java" 不变
System.out.println(s2);  // Jovo
```

> ⚠️ **不可变的好处**：
> 1. **线程安全**：多线程共享同一 String 无需加锁
> 2. **安全性**：作为 HashMap 的 key 不会被篡改（hashCode 可缓存）
> 3. **字符串常量池**：相同字面量可复用同一对象，节省内存
>
> 代价是「修改」字符串会产生大量临时对象，循环拼接时性能差——这就是 `StringBuilder` 存在的理由。

---

## 二、String 的创建与字符串常量池

### 2.1 两种创建方式

```java
// 方式一：字面量，存入字符串常量池
String s1 = "hello";

// 方式二：new 构造方法，在堆中创建对象
String s2 = new String("hello");
```

这两种方式的内存分布完全不同：

```
栈                         堆                          字符串常量池（堆中）
┌──────┐                ┌──────────────┐          ┌──────────────┐
│ s1   │ ──────────────────────────────────────→  │ "hello"      │
└──────┘                │  (无独立对象) │          │ 地址：0x100   │
                        └──────────────┘          └──────────────┘
┌──────┐                ┌──────────────┐          ┌──────────────┐
│ s2   │ ────────────→  │ String 对象  │ ───────→  │ "hello" 复用 │
└──────┘                │ 地址：0x200   │          │ 0x100        │
                        └──────────────┘          └──────────────┘
```

- `s1 = "hello"`：直接引用常量池中的对象
- `s2 = new String("hello")`：在堆中 new 一个 String 对象，其内部 value 指向常量池的 "hello"

```java
String s1 = "hello";
String s2 = "hello";
String s3 = new String("hello");

System.out.println(s1 == s2);   // true，常量池同一对象
System.out.println(s1 == s3);   // false，s3 是堆中新对象
System.out.println(s1.equals(s3)); // true，内容相同
```

> ⚠️ `new String("hello")` 实际创建了**两个**对象：堆中的 String 对象 + 常量池的 "hello"（若常量池没有的话）。实际开发中**几乎不用** `new String()`，直接字面量即可。

### 2.2 字符串常量池的位置变迁

字符串常量池（String Pool）的位置在不同 JDK 版本有变化：

| JDK 版本 | 常量池位置 | 说明 |
| :--- | :--- | :--- |
| JDK 1.6 及以前 | 方法区（PermGen，永久代） | 容易 OOM：`PermGen space` |
| JDK 1.7 | 堆（Heap） | 移到堆，降低 OOM 风险 |
| JDK 1.8+ | 堆（Heap） | 永久代被元空间（Metaspace）取代，常量池仍在堆 |

> 💡 **为什么要移到堆？** 永久代空间小且不可回收，大量 `intern()` 调用会撑爆永久代。移到堆后，常量池里的无用字符串可被 GC 回收，更灵活。

### 2.3 intern() 方法

`intern()` 是一个 native 方法：如果常量池中已有等值字符串，返回常量池中的引用；否则把当前字符串放入常量池并返回引用。

```java
// JDK 1.8 的行为
String s1 = new String("hello");   // 堆中对象 + 常量池 "hello"
String s2 = "hello";               // 直接引用常量池
System.out.println(s1 == s2);      // false，s1 是堆对象

String s3 = s1.intern();           // s1.intern() 返回常量池中的 "hello"
System.out.println(s3 == s2);      // true，都是常量池中的对象
System.out.println(s3 == s1);      // false，s1 仍是堆对象

// 经典面试题
String a = "ab";                   // 常量池
String b = "a" + "b";              // 编译期常量折叠，等价于 "ab"
System.out.println(a == b);        // true，都是常量池 "ab"

String c = "a";
String d = c + "b";                // 变量拼接，运行期生成，在堆
System.out.println(a == d);        // false，d 是堆对象
String e = d.intern();
System.out.println(a == e);        // true，intern 后回到常量池
```

> ⚠️ **intern 在 JDK 1.6 和 1.7 的区别**：
> - 1.6：把字符串**复制**一份到常量池（永久代）
> - 1.7+：常量池在堆，只存**引用**，指向堆中已有对象，节省内存
>
> 实际开发中**不要滥用 `intern()`**——虽然能省内存，但常量池也是堆的一部分，过多 intern 仍可能 OOM，且会降低 GC 效率。

### 2.4 String 的构造方法

String 有多个构造方法，用于不同场景：

```java
// 字面量（最常用）
String s1 = "hello";

// 从字符数组构造
char[] chars = {'h', 'e', 'l', 'l', 'o'};
String s2 = new String(chars);          // "hello"
String s3 = new String(chars, 1, 3);    // "ell"，从索引 1 取 3 个字符

// 从字节数组构造（IO 场景常见）
byte[] bytes = {97, 98, 99};           // ASCII: a, b, c
String s4 = new String(bytes);          // "abc"
String s5 = new String(bytes, "UTF-8"); // 指定字符集解码

// 从 StringBuilder 构造
StringBuilder sb = new StringBuilder("hi");
String s6 = new String(sb);            // "hi"

// 从另一个 String 构造（几乎不用）
String s7 = new String("hello");        // 多此一举，直接字面量即可
```

> 💡 **byte[] 转 String 必须注意字符集**：网络传输、文件读取得到的是字节流，转字符串时必须指定字符集（如 UTF-8），否则用系统默认字符集可能乱码。这是 Web 开发中乱码问题的根源。

---

## 三、字符串比较

### 3.1 == 的坑

`==` 比较的是**引用地址**，对 String 来说就是「是否指向同一对象」。由于常量池的存在，有时 `==` 为 true，有时为 false，极易出错：

```java
String s1 = "hello";
String s2 = "hello";
String s3 = new String("hello");
String s4 = "hel" + "lo";      // 编译期常量折叠
String s5 = "hel";
String s6 = s5 + "lo";         // 变量拼接，运行期

System.out.println(s1 == s2);  // true，常量池同一对象
System.out.println(s1 == s3);  // false，s3 是堆对象
System.out.println(s1 == s4);  // true，编译期折叠成 "hello"
System.out.println(s1 == s6);  // false，变量拼接在堆
```

> ⚠️ **结论：永远不要用 `==` 比较字符串内容！** 它有时碰巧为 true（常量池复用），有时为 false（堆对象），是埋在代码里的定时炸弹。一律用 `equals()`。

### 3.2 equals / equalsIgnoreCase

```java
String a = "Hello";
String b = "hello";

System.out.println(a.equals(b));             // false，区分大小写
System.out.println(a.equalsIgnoreCase(b));   // true，忽略大小写

// 安全写法：用 Objects.equals 防 null
String c = null;
// System.out.println(c.equals(b));          // ❌ NPE
System.out.println(java.util.Objects.equals(c, b));  // false，安全

// 或把常量放前面（常量不会 NPE）
System.out.println("hello".equals(c));       // false，安全
```

> 📌 **开发规范**：
> - 字符串内容比较一律用 `.equals()`，不用 `==`
> - 可能 null 的变量用 `Objects.equals(a, b)` 或把常量放前面 `"常量".equals(变量)`
> - 忽略大小写用 `.equalsIgnoreCase()`（如验证码、邮箱比较）

---

## 四、String 常用方法

### 4.1 获取类

```java
String s = "HelloJava";

int len = s.length();          // 9，长度
char c = s.charAt(4);          // 'o'，指定索引的字符
int idx = s.indexOf('a');      // 6，第一次出现的位置
int idx2 = s.indexOf("Java");  // 5，子串第一次出现的位置
int last = s.lastIndexOf('a'); // 8，最后一次出现的位置
boolean empty = s.isEmpty();   // false，是否为空串 ""
```

> ⚠️ `length()` 是方法（带括号），数组的 `length` 是属性（不带括号）——新手常混淆。

### 4.2 截取与转换

```java
String s = "HelloJava";

String sub1 = s.substring(5);       // "Java"，从索引 5 到末尾
String sub2 = s.substring(0, 5);   // "Hello"，[0,5) 左闭右开

char[] chars = s.toCharArray();    // 转 char 数组
byte[] bytes = s.getBytes();       // 转 byte 数组（用系统默认字符集）
String upper = s.toUpperCase();    // "HELLOJAVA"
String lower = s.toLowerCase();    // "hellojava"
String trimmed = "  hi  ".trim();  // "hi"，去掉首尾空白
```

> ⚠️ `substring` 在 JDK 1.7+ 会**新建数组**（不再共享原数组），所以截取后原字符串可被 GC 回收。1.6 及以前共享 value 数组，可能内存泄漏。

### 4.3 替换与分割

```java
String s = "Hello World Java";

String r1 = s.replace(' ', '-');           // "Hello-World-Java"
String r2 = s.replace("World", "Java");    // "Hello Java Java"
String r3 = s.replaceAll("\\s", "_");      // "Hello_World_Java"，支持正则
String r4 = s.replaceFirst("\\s", "_");    // 只替换第一个匹配

String[] parts = s.split(" ");             // ["Hello", "World", "Java"]
String[] parts2 = s.split(" ", 2);         // ["Hello", "World Java"]，限制分 2 段
```

> ⚠️ `split` 的参数是**正则表达式**，`.`、`|`、`$` 等特殊字符要转义：
> ```java
> "a.b.c".split(".");     // ❌ 返回空数组，. 是正则的任意字符
> "a.b.c".split("\\.");   // ✅ ["a", "b", "c"]
> "192.168.1.1".split("\\.");
> ```

### 4.4 查找与拼接

```java
String s = "HelloJava";

boolean c1 = s.contains("Java");      // true，是否包含子串
boolean c2 = s.startsWith("Hello");   // true，是否以某串开头
boolean c3 = s.endsWith("Java");      // true，是否以某串结尾

String joined = String.join("-", "a", "b", "c");  // "a-b-c"，Java 8+
String joined2 = String.join("/", "2024", "01", "01"); // "2024/01/01"

String concat = "Hello".concat(" ").concat("World"); // "Hello World"
// 实际开发中拼接更多用 + 或 StringBuilder
```

### 4.5 方法速查表

| 方法 | 作用 | 示例 |
| :--- | :--- | :--- |
| `length()` | 字符串长度 | `"abc".length()` → 3 |
| `charAt(i)` | 第 i 个字符 | `"abc".charAt(1)` → 'b' |
| `indexOf(str)` | 子串首次出现位置 | `"abcabc".indexOf("bc")` → 1 |
| `lastIndexOf(str)` | 子串最后出现位置 | `"abcabc".lastIndexOf("bc")` → 4 |
| `substring(b)` | 从 b 到末尾 | `"abcde".substring(2)` → "cde" |
| `substring(b, e)` | [b, e) | `"abcde".substring(1, 3)` → "bc" |
| `toCharArray()` | 转 char[] | - |
| `getBytes()` | 转 byte[] | - |
| `toUpperCase()` | 转大写 | - |
| `toLowerCase()` | 转小写 | - |
| `trim()` | 去首尾空白 | `" a ".trim()` → "a" |
| `replace(old, new)` | 替换所有 | - |
| `replaceAll(regex, new)` | 正则替换 | - |
| `split(regex)` | 正则分割 | - |
| `contains(str)` | 是否包含 | - |
| `startsWith(str)` | 是否以...开头 | - |
| `endsWith(str)` | 是否以...结尾 | - |
| `equals(str)` | 内容相等 | - |
| `equalsIgnoreCase(str)` | 忽略大小写相等 | - |
| `concat(str)` | 拼接 | - |
| `isEmpty()` | 是否为空串 | `"".isEmpty()` → true |
| `join(delim, ...)` | 静态拼接 | `String.join("-", "a","b")` → "a-b" |

---

## 五、字符串拼接的底层

### 5.1 + 拼接的编译期优化

```java
// 源代码
String s = "a" + "b" + "c";

// 编译期常量折叠，等价于
String s = "abc";   // 常量池中只有一个对象 "abc"
```

纯字面量拼接，编译器会在编译期直接合并成一个常量，**不会创建 StringBuilder**。

### 5.2 变量拼接会创建 StringBuilder

一旦涉及变量，`+` 会被编译器翻译成 `StringBuilder.append`：

```java
// 源代码
String a = "a";
String b = "b";
String c = a + b + "c";

// 编译器等价翻译成
String c = new StringBuilder()
    .append(a)
    .append(b)
    .append("c")
    .toString();
```

### 5.3 循环拼接的灾难 ⭐

**在循环里用 `+` 拼字符串，是性能杀手**——每次循环都 new 一个 StringBuilder，再 toString 生成新 String：

```java
// ❌ 灾难写法：循环里用 +
String result = "";
for (int i = 0; i < 10000; i++) {
    result += i;   // 每次循环：new StringBuilder + append + toString
}
// 等价于每次循环：
// result = new StringBuilder().append(result).append(i).toString();
// 10000 次循环 = 10000 个 StringBuilder + 10000 个临时 String

// ✅ 正确写法：循环外建一个 StringBuilder
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(i);   // 复用同一个 StringBuilder
}
String result = sb.toString();  // 只生成一个最终 String
```

> ⚠️ **性能差距可达数百倍**：循环 1 万次，`+` 写法要创建约 2 万个临时对象，而 StringBuilder 只需 1 个。这是实际开发中最常见的性能反模式。

---

## 六、StringBuilder 与 StringBuffer

### 6.1 StringBuilder：可变字符序列

`StringBuilder` 是可变的字符序列，专为**高效拼接**设计。它在内部维护一个可扩容的 `char[]`（Java 9 后 `byte[]`），append 时直接在原数组追加，不创建新对象：

```java
StringBuilder sb = new StringBuilder();
sb.append("Hello");
sb.append(" ");
sb.append("World");
String result = sb.toString();  // "Hello World"

// 链式调用（append 返回 this）
String s = new StringBuilder()
    .append("name=")
    .append("张三")
    .append(", age=")
    .append(20)
    .toString();
```

### 6.2 StringBuilder 常用方法

```java
StringBuilder sb = new StringBuilder("Hello");

sb.append(" World");     // 追加，"Hello World"
sb.insert(5, "Java");   // 在索引 5 插入，"HelloJava World"
sb.delete(5, 9);        // 删除 [5,9)，"Hello World"
sb.deleteCharAt(0);     // 删除索引 0 的字符，"ello World"
sb.reverse();           // 反转，"dlroW olle"
sb.replace(0, 5, "Hi"); // 替换 [0,5)，"Hi World"
int len = sb.length();  // 长度
char c = sb.charAt(0);  // 指定位置字符
String s = sb.toString(); // 转回 String
```

> 💡 **StringBuilder 与 String 的转换**：`StringBuilder` → `String` 用 `toString()`；`String` → `StringBuilder` 用 `new StringBuilder(str)`。StringBuilder 完成拼接后应转回 String 使用。

### 6.3 容量与扩容

```java
StringBuilder sb = new StringBuilder();        // 默认容量 16
StringBuilder sb2 = new StringBuilder(100);    // 指定初始容量 100
StringBuilder sb3 = new StringBuilder("Hi");   // 初始容量 16 + 2 = 18

sb.append("很长的字符串...");
int cap = sb.capacity();   // 当前容量
sb.ensureCapacity(200);    // 保证至少 200 容量
sb.trimToSize();           // 缩减到实际长度，省内存
```

> 📌 **预分配容量**：拼接大量字符串时，用 `new StringBuilder(预估长度)` 预分配容量，避免频繁扩容（扩容是 `Arrays.copyOf`，要复制数组）。这是性能优化的小技巧。

### 6.4 StringBuffer：线程安全版

`StringBuffer` 是 `StringBuilder` 的**线程安全**版本，方法用 `synchronized` 修饰：

```java
StringBuffer sb = new StringBuffer();
sb.append("a");   // 方法签名：public synchronized StringBuffer append(...)
```

| 对比项 | String | StringBuilder | StringBuffer |
| :--- | :--- | :--- | :--- |
| 可变性 | 不可变 | 可变 | 可变 |
| 线程安全 | 是（不可变天然安全） | 否 | 是（synchronized） |
| 性能 | 最低（每次修改 new 对象） | 最高 | 较低（锁开销） |
| 适用场景 | 少量拼接、字符串不变 | 单线程大量拼接 | 多线程大量拼接 |

> ⚠️ **实际开发中几乎不用 StringBuffer**——多线程下拼接字符串的场景极少，真要线程安全用 `StringJoiner` 或加锁。JDK 文档也建议优先用 StringBuilder。

---

## 七、StringJoiner（Java 8+）

`StringJoiner` 是 Java 8 引入的拼接工具，支持**分隔符、前缀、后缀**，特别适合拼接 CSV、JSON：

```java
import java.util.StringJoiner;

// 基本用法：指定分隔符
StringJoiner sj = new StringJoiner(",");
sj.add("张三").add("李四").add("王五");
System.out.println(sj);  // 张三,李四,王五

// 带前后缀
StringJoiner sj2 = new StringJoiner(",", "[", "]");
sj2.add("a").add("b").add("c");
System.out.println(sj2);  // [a,b,c]

// 拼接 JSON 数组
StringJoiner json = new StringJoiner(",", "[", "]");
json.add("\"张三\"").add("\"李四\"");
System.out.println(json);  // ["张三","李四"]

// 空值处理
StringJoiner sj3 = new StringJoiner(",").setEmptyValue("空");
System.out.println(sj3);  // 空（没 add 任何元素时）
```

> 💡 `String.join(",", list)` 底层就是用 `StringJoiner` 实现的。Stream 的 `Collectors.joining(",")` 也是。它是 Java 8 字符串拼接的推荐方式之一。

---

## 八、正则表达式入门

### 8.1 matches：匹配校验

`String.matches(regex)` 判断整个字符串是否匹配正则：

```java
// 手机号校验：1 开头，第二位 3-9，共 11 位
String phone = "13812345678";
boolean valid = phone.matches("1[3-9]\\d{9}");
System.out.println(valid);  // true

// 邮箱校验（简化版）
String email = "test@example.com";
boolean emailOk = email.matches("\\w+@\\w+\\.\\w+");
System.out.println(emailOk);  // true

// 身份证号（18 位，最后一位可能是 X）
String id = "11010119900101001X";
boolean idOk = id.matches("\\d{17}[\\dXx]");
System.out.println(idOk);  // true
```

### 8.2 replaceAll：正则替换

```java
// 敏感词替换
String content = "这里有广告词和违禁词";
String filtered = content.replaceAll("广告词|违禁词", "***");
System.out.println(filtered);  // 这里有***和***

// 去除所有非数字
String dirty = "电话：138-1234-5678";
String clean = dirty.replaceAll("[^0-9]", "");
System.out.println(clean);  // 13812345678
```

### 8.3 split：正则分割

```java
// 按多种分隔符分割
String line = "张三,李四;王五|赵六";
String[] names = line.split("[,;|]");
System.out.println(java.util.Arrays.toString(names));
// [张三, 李四, 王五, 赵六]

// 按一个或多个空格分割
String text = "hello   world  java";
String[] words = text.split("\\s+");
System.out.println(java.util.Arrays.toString(words));
// [hello, world, java]
```

> ⚠️ 正则的特殊字符（`. * + ? ^ $ | \ [ ( {`）在 split 中要转义。如按 `.` 分割用 `split("\\.")`，按 `|` 分割用 `split("\\|")`。

---

## ⚠️ 重点

### 重点 1：== 比较字符串的坑 ⭐⭐

```java
String a = "hello";
String b = "hello";
String c = new String("hello");

System.out.println(a == b);       // true，常量池复用，碰巧相等
System.out.println(a == c);       // false，c 是堆对象
System.out.println(a.equals(c));  // true，内容相等
```

> ⚠️ **铁律：字符串内容比较永远用 `equals()`，不用 `==`**。`==` 有时为 true（常量池复用）有时为 false（堆对象），是代码里的定时炸弹。这个坑在从外部读取字符串（数据库、文件、网络）时必现——这些字符串都在堆上，`==` 永远 false。

### 重点 2：循环拼接必须用 StringBuilder ⭐⭐

```java
// ❌ 循环用 +，每次都 new StringBuilder
String s = "";
for (int i = 0; i < 10000; i++) {
    s += i;  // 等价于 s = new StringBuilder().append(s).append(i).toString();
}

// ✅ 循环用 StringBuilder，只 new 一次
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(i);
}
String s = sb.toString();
```

> ⚠️ 循环 1 万次，`+` 写法创建约 2 万个临时对象，StringBuilder 只需 1 个。性能差异数百倍。这是实际开发中最常见的性能反模式，**循环拼接一律用 StringBuilder**。

### 重点 3：String 不可变，"修改"是创建新对象 ⭐

```java
String s = "hello";
s = s + " world";   // s 指向了新对象 "hello world"，原 "hello" 不变

// 作为方法参数，String 不可被修改
public static void appendWorld(String s) {
    s = s + " world";  // 只改了局部变量 s 的指向，外部不受影响
}
String str = "hello";
appendWorld(str);
System.out.println(str);  // hello，没变
```

> 💡 String 是**值传递 + 不可变**：方法内拿到的 s 是地址副本，`s = s + " world"` 让这个副本指向新对象，但外部的 str 仍指向原对象。理解这点，就不会写出「在方法里修改 String 参数」的 bug。

### 重点 4：split 的参数是正则 ⭐

```java
"a.b.c".split(".");     // ❌ []，. 是正则的任意字符
"a.b.c".split("\\.");   // ✅ [a, b, c]
"192.168.1.1".split("\\.");  // ✅ [192, 168, 1, 1]

"a|b|c".split("|");     // ❌ [a, |, b, |, c]，| 是正则的"或"
"a|b|c".split("\\|");   // ✅ [a, b, c]
```

> 📌 **split 的第一个参数是正则表达式**，`.`、`|`、`$`、`*`、`+`、`?` 等特殊字符必须用 `\\` 转义。这是解析 CSV、IP、路径时最常见的坑。

### 重点 5：substring 不影响原字符串 ⭐

```java
String s = "HelloWorld";
String sub = s.substring(5);   // "World"
System.out.println(s);         // HelloWorld，原字符串不变
// String 不可变，substring 返回新对象
```

### 重点 6：StringBuilder 非线程安全 ⭐

```java
// ❌ 多线程下用 StringBuilder 会出问题
StringBuilder sb = new StringBuilder();
// 线程 A 和 B 同时 append，可能丢数据或数组越界

// ✅ 多线程用 StringBuffer（但实际开发极少需要）
StringBuffer sbf = new StringBuffer();
```

> 💡 单线程拼接用 StringBuilder（绝大多数场景），多线程才考虑 StringBuffer。实际多线程下更推荐用 `StringJoiner` 或外部加锁，而非直接用 StringBuffer。

---

## 💻 实战案例

### 案例 1：字符串拼接性能对比（+ vs StringBuilder）⭐⭐

```java
public class ConcatBenchmark {
    public static void main(String[] args) {
        int n = 100000;

        // ❌ 用 + 循环拼接
        long start1 = System.currentTimeMillis();
        String s1 = "";
        for (int i = 0; i < n; i++) {
            s1 += i;
        }
        long end1 = System.currentTimeMillis();
        System.out.println("+ 拼接 " + n + " 次：" + (end1 - start1) + " ms");
        // 约 5000-8000 ms（每次循环都 new StringBuilder）

        // ✅ 用 StringBuilder
        long start2 = System.currentTimeMillis();
        StringBuilder sb = new StringBuilder(n * 2);  // 预分配容量
        for (int i = 0; i < n; i++) {
            sb.append(i);
        }
        String s2 = sb.toString();
        long end2 = System.currentTimeMillis();
        System.out.println("StringBuilder 拼接 " + n + " 次：" + (end2 - start2) + " ms");
        // 约 10-30 ms
    }
}
```

> ⚠️ 10 万次拼接，`+` 耗时数秒，StringBuilder 仅几十毫秒，差距可达百倍。循环拼接一律用 StringBuilder，这是性能优化的基本功。

### 案例 2：敏感信息脱敏（手机号中间四位）⭐⭐

金融/电商系统中，手机号、身份证号在日志和前端展示时必须脱敏：

```java
public class DesensitizeUtil {
    // 手机号脱敏：138****8888
    public static String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) {
            return phone;  // 长度不够，原样返回
        }
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    // 身份证脱敏：110101********001X
    public static String maskIdCard(String idCard) {
        if (idCard == null || idCard.length() < 10) {
            return idCard;
        }
        return idCard.substring(0, 6) + "********" + idCard.substring(idCard.length() - 4);
    }

    // 银行卡脱敏：6228 **** **** **** 8888
    public static String maskBankCard(String card) {
        if (card == null || card.length() < 8) {
            return card;
        }
        return card.substring(0, 4) + " **** **** " + card.substring(card.length() - 4);
    }

    // 邮箱脱敏：t***@example.com
    public static String maskEmail(String email) {
        if (email == null || !email.contains("@")) {
            return email;
        }
        int at = email.indexOf("@");
        if (at <= 1) return email;
        return email.charAt(0) + "***" + email.substring(at);
    }

    public static void main(String[] args) {
        System.out.println(maskPhone("13812345678"));    // 138****5678
        System.out.println(maskIdCard("11010119900101001X")); // 110101********001X
        System.out.println(maskBankCard("6228480012345678"));  // 6228 **** **** 5678
        System.out.println(maskEmail("test@example.com"));    // t***@example.com
    }
}
```

> 📌 **安全规范**：涉及个人隐私数据（手机号、身份证、银行卡、邮箱）在日志、异常信息、前端展示时一律脱敏。这是《个人信息保护法》和数据安全规范的基本要求。

### 案例 3：split 分割解析 CSV ⭐

后台系统中，解析 CSV 格式的订单数据：

```java
public class CsvParser {
    public static void main(String[] args) {
        // 模拟 CSV：订单号,商品名,数量,单价,状态
        String line = "NO20240101,iPhone 15,2,7999.00,PAID";

        // ✅ 按逗号分割
        String[] fields = line.split(",");
        if (fields.length >= 5) {
            String orderNo = fields[0];
            String product = fields[1];
            int qty = Integer.parseInt(fields[2]);
            double price = Double.parseDouble(fields[3]);
            String status = fields[4];
            System.out.printf("订单：%s，商品：%s，数量：%d，单价：%.2f，状态：%s%n",
                    orderNo, product, qty, price, status);
        }

        // ⚠️ 坑：字段中包含逗号时，CSV 用引号包裹
        String tricky = "NO20240102,\"iPhone 15, 256G\",1,7999.00,PAID";
        String[] bad = tricky.split(",");  // ❌ 会把引号内的逗号也分割
        System.out.println(java.util.Arrays.toString(bad));
        // [NO20240102, "iPhone 15,  256G", 1, 7999.00, PAID] —— 6 段，错误！

        // ✅ 正确：用正则处理引号，或用专门的 CSV 库（如 OpenCSV）
        // 简单场景可用 lookbehind：按不在引号内的逗号分割
        String[] good = tricky.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)");
        System.out.println(java.util.Arrays.toString(good));
        // [NO20240102, "iPhone 15, 256G", 1, 7999.00, PAID] —— 5 段，正确
    }
}
```

> ⚠️ **CSV 解析的坑**：字段含分隔符时需引号包裹，纯 `split(",")` 会分割错误。生产环境用 OpenCSV、Apache Commons CSV 等成熟库，不要自己手写正则。

### 案例 4：字符串反转 ⭐

```java
public class StringReverse {
    // 方式一：StringBuilder.reverse()
    public static String reverse1(String s) {
        return new StringBuilder(s).reverse().toString();
    }

    // 方式二：字符数组双指针
    public static String reverse2(String s) {
        char[] chars = s.toCharArray();
        for (int i = 0, j = chars.length - 1; i < j; i++, j--) {
            char temp = chars[i];
            chars[i] = chars[j];
            chars[j] = temp;
        }
        return new String(chars);
    }

    // 方式三：递归（仅作理解，性能差）
    public static String reverse3(String s) {
        if (s.length() <= 1) return s;
        return reverse3(s.substring(1)) + s.charAt(0);
    }

    public static void main(String[] args) {
        System.out.println(reverse1("Hello"));  // olleH
        System.out.println(reverse2("Java"));    // avaJ
        System.out.println(reverse3("World"));   // dlroW
    }
}
```

> 💡 实际开发用 `StringBuilder.reverse()` 一行搞定。手写反转是面试常考题，考察双指针和字符数组操作。

### 案例 5：用 StringBuilder 拼接 SQL ⭐

后台系统中，根据条件动态拼接查询 SQL：

```java
public class SqlBuilder {
    public static String buildQuery(String table, String name, Integer minAge, String city) {
        StringBuilder sql = new StringBuilder("SELECT * FROM ").append(table).append(" WHERE 1=1");

        if (name != null && !name.isEmpty()) {
            sql.append(" AND name = '").append(name).append("'");
        }
        if (minAge != null) {
            sql.append(" AND age >= ").append(minAge);
        }
        if (city != null && !city.isEmpty()) {
            sql.append(" AND city = '").append(city).append("'");
        }
        sql.append(" ORDER BY id DESC");

        return sql.toString();
    }

    public static void main(String[] args) {
        // 查全部
        System.out.println(buildQuery("users", null, null, null));
        // SELECT * FROM users WHERE 1=1 ORDER BY id DESC

        // 按条件查询
        System.out.println(buildQuery("users", "张三", 18, "北京"));
        // SELECT * FROM users WHERE 1=1 AND name = '张三' AND age >= 18 AND city = '北京' ORDER BY id DESC
    }
}
```

> ⚠️ **SQL 注入警告**：上面这种拼接方式有 SQL 注入风险（如 name 传 `' OR '1'='1`）。生产环境必须用 `PreparedStatement` 参数化查询，或 MyBatis 的 `#{}` 占位符。这里仅演示 StringBuilder 的拼接用法。

### 案例 6：用 StringBuilder 拼接 JSON ⭐

不依赖 JSON 库时，手动拼接简单 JSON：

```java
import java.util.Map;
import java.util.HashMap;

public class JsonBuilder {
    public static String toJson(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> e : map.entrySet()) {
            if (!first) sb.append(",");
            sb.append("\"").append(e.getKey()).append("\":");
            Object v = e.getValue();
            if (v instanceof String) {
                sb.append("\"").append(v).append("\"");
            } else {
                sb.append(v);
            }
            first = false;
        }
        sb.append("}");
        return sb.toString();
    }

    public static void main(String[] args) {
        Map<String, Object> user = new HashMap<>();
        user.put("id", 1001);
        user.put("name", "张三");
        user.put("age", 20);
        user.put("vip", true);
        System.out.println(toJson(user));
        // {"name":"张三","id":1001,"age":20,"vip":true}
    }
}
```

> 💡 实际开发用 Jackson、Gson 等库，不要手写 JSON 拼接（转义、嵌套、特殊字符处理太复杂）。这里演示 StringBuilder 的链式拼接和条件拼接技巧。

### 案例 7：用 StringJoiner 拼接 IN 条件 ⭐

```java
import java.util.StringJoiner;
import java.util.Arrays;

public class InClauseBuilder {
    // 拼接 SQL 的 IN 条件：('a','b','c')
    public static String buildInClause(String... values) {
        StringJoiner sj = new StringJoiner("','", "('", "')");
        for (String v : values) {
            sj.add(v);
        }
        return sj.toString();
    }

    public static void main(String[] args) {
        System.out.println(buildInClause("北京", "上海", "广州"));
        // ('北京','上海','广州')

        // 拼接日志
        String log = String.join(" | ", "INFO", "2024-01-01", "用户登录");
        System.out.println(log);  // INFO | 2024-01-01 | 用户登录
    }
}
```

### 案例 8：解析 URL 参数 ⭐

```java
public class UrlParser {
    public static java.util.Map<String, String> parseQuery(String query) {
        java.util.Map<String, String> params = new java.util.HashMap<>();
        if (query == null || query.isEmpty()) return params;

        String[] pairs = query.split("&");
        for (String pair : pairs) {
            String[] kv = pair.split("=", 2);  // 限制分 2 段，值里可能有 =
            if (kv.length == 2) {
                params.put(kv[0], kv[1]);
            }
        }
        return params;
    }

    public static void main(String[] args) {
        String url = "name=%E5%BC%A0%E4%B8%89&age=20&city=Beijing";
        java.util.Map<String, String> p = parseQuery(url);
        System.out.println(p);
        // {name=%E5%BC%A0%E4%B8%89, age=20, city=Beijing}

        // 简单的路径解析
        String path = "/api/v1/users/1001/orders";
        String[] parts = path.split("/");
        System.out.println(java.util.Arrays.toString(parts));
        // [, api, v1, users, 1001, orders]
        // 注意：开头有 /，所以第一个元素是空串
    }
}
```

> 💡 `split("=", 2)` 的第二个参数限制分割段数——值里若含 `=`（如 base64 编码）不会被误分割。这是 split 的进阶用法。

### 案例 9：字符串格式化与对齐 ⭐

```java
public class FormatDemo {
    public static void main(String[] args) {
        // String.format：类似 C 的 printf
        String s1 = String.format("姓名：%s，年龄：%d", "张三", 20);
        System.out.println(s1);  // 姓名：张三，年龄：20

        // 金额格式化
        String s2 = String.format("总价：%.2f 元", 199.5);
        System.out.println(s2);  // 总价：199.50 元

        // 对齐：%-10s 左对齐占 10 位，%10s 右对齐
        System.out.printf("%-10s%-10s%-10s%n", "商品", "数量", "单价");
        System.out.printf("%-10s%-10d%-10.2f%n", "iPhone", 2, 7999.00);
        System.out.printf("%-10s%-10d%-10.2f%n", "耳机", 3, 199.00);
        // 商品      数量      单价
        // iPhone    2         7999.00
        // 耳机      3         199.00

        // 补零：订单号
        String orderNo = String.format("NO%08d", 123);
        System.out.println(orderNo);  // NO00000123
    }
}
```

### 案例 10：验证码生成与校验 ⭐

```java
import java.util.Random;

public class CaptchaDemo {
    // 生成 6 位数字验证码
    public static String generateCode(int length) {
        StringBuilder sb = new StringBuilder();
        Random r = new Random();
        for (int i = 0; i < length; i++) {
            sb.append(r.nextInt(10));  // 0-9
        }
        return sb.toString();
    }

    // 校验验证码（忽略大小写）
    public static boolean verifyCode(String input, String expected) {
        if (input == null || expected == null) return false;
        return input.trim().equalsIgnoreCase(expected);
    }

    public static void main(String[] args) {
        String code = generateCode(6);
        System.out.println("生成的验证码：" + code);  // 如 382947

        // 用户输入（可能带空格、大小写不一）
        System.out.println(verifyCode("  382947  ", code));  // true
        System.out.println(verifyCode("382947", code));       // true
        System.out.println(verifyCode("123456", code));       // false
    }
}
```

> 💡 验证码校验要用 `equalsIgnoreCase` + `trim`，容忍用户输入的前后空格和大小写差异。这是用户体验的基本细节。

---

## 🚀 新版本补充

### Java 9：String 底层改为 byte[]

Java 9 起，`String` 内部用 `byte[]` 替代 `char[]`，配合 `coder` 字段标记编码方式（LATIN1 或 UTF16），纯 ASCII 字符串可省一半内存：

```java
// Java 8：private final char[] value;   每个 char 占 2 字节
// Java 9+：private final byte[] value;  ASCII 串每字节 1 字节
```

> 💡 这是 **Compact Strings** 优化，对开发者透明，但堆内存占用大幅下降（大量纯英文字符串的场景省 30%-50%）。

### Java 9：StringJoiner 与 Stream 配合

```java
import java.util.stream.Collectors;
import java.util.Arrays;

// Java 8+ Stream + Collectors.joining
String result = Arrays.asList("张三", "李四", "王五").stream()
    .collect(Collectors.joining(", ", "[", "]"));
System.out.println(result);  // [张三, 李四, 王五]
```

### Java 10：字符串拼接的字面量推断（补充）

Java 10+ 的 `var` 可用于局部字符串变量，但底层仍是 String：

```java
var s = "hello";  // Java 10+，推断为 String，与 String s = "hello" 等价
```

### Java 12：String.indent() 与 transform()（补充了解）

```java
// Java 12+ indent：批量缩进
String s = "line1\nline2".indent(4);
//     line1
//     line2

// Java 12+ transform：链式转换
String r = "  hello  ".transform(String::trim).transform(String::toUpperCase);
System.out.println(r);  // HELLO
```

### Java 15：String.strip() / stripLeading() / stripTrailing()

Java 11+ 引入 `strip()`，比 `trim()` 更强——能去除 Unicode 空白（如全角空格）：

```java
// Java 8 只有 trim()，只去 ASCII 空白（<= U+0020）
String s1 = "  hello  ".trim();  // "hello"

// Java 11+ strip()，去除所有 Unicode 空白
String s2 = "  hello  ".strip();  // "hello"
String s3 = "  hello".stripLeading();  // "hello"
String s4 = "hello  ".stripTrailing();  // "hello"

// Java 11+ repeat()：重复
String r = "ab".repeat(3);  // "ababab"

// Java 11+ isBlank()：是否为空白串（空或全空白）
boolean b = "   ".isBlank();  // true（trim 后为空）
boolean b2 = "".isEmpty();    // true
```

> ⚠️ Java 8 环境下 `strip()`、`repeat()`、`isBlank()` 不可用。处理国际化文本（含全角空格）时，Java 8 只能用 `trim()` 或 Apache Commons Lang 的 `StringUtils.strip()`。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| String 不可变 | final class + final value[]，"修改"即创建新对象 |
| 字面量创建 | `"abc"`，存入字符串常量池（堆中） |
| new String | 在堆中创建对象，内部 value 指向常量池 |
| 字符串常量池 | JDK 1.7+ 移到堆，相同字面量复用同一对象 |
| intern() | 返回常量池中的等值引用，1.7+ 存引用不复制 |
| == vs equals | == 比地址，equals 比内容；字符串一律用 equals |
| equalsIgnoreCase | 忽略大小写比较，用于验证码、邮箱 |
| 常用方法 | length/charAt/indexOf/substring/replace/split/trim/contains |
| + 拼接 | 纯字面量编译期折叠；变量拼接编译成 StringBuilder |
| 循环拼接 | 循环里用 + 是性能灾难，必须用 StringBuilder |
| StringBuilder | 可变字符序列，非线程安全，高效拼接 |
| StringBuffer | 线程安全（synchronized），性能低，实际少用 |
| StringJoiner | Java 8+，支持分隔符/前后缀，拼接 CSV/JSON |
| 正则入门 | matches 校验、replaceAll 替换、split 分割 |

---

## 学习建议

1. **把 == 和 equals 的区别刻进骨头里**：字符串内容比较永远用 `equals()`，不用 `==`。把本篇重点 1 的代码敲一遍，亲眼看 `a == c` 为 false。尤其从数据库、文件、网络读到的字符串都在堆上，`==` 永远是 false，这个 bug 极其隐蔽。
2. **循环拼接一律用 StringBuilder**：这是性能优化的第一条军规。把本篇案例 1 的性能对比跑一遍，亲眼看 `+` 写法耗时数秒、StringBuilder 仅几十毫秒。养成习惯：看到循环里有字符串拼接，立刻换成 StringBuilder。
3. **理解 String 不可变带来的连锁反应**：所有「修改」方法（substring、replace、concat）都返回新对象，原字符串不变。方法参数传 String 也不会被修改。理解这点，就不会写出 `str.replace(...)` 后忘记接收返回值的 bug。
4. **split 的正则陷阱要牢记**：`.`、`|`、`$` 等特殊字符必须 `\\` 转义。解析 CSV、IP、路径时这是高频坑。复杂 CSV 用专门的库，不要自己手写正则。
5. **掌握 StringJoiner 和 String.join**：Java 8 后拼接带分隔符的字符串，优先用 `String.join` 或 `StringJoiner`，比手动拼 + 处理末尾分隔符优雅得多。结合 Stream 的 `Collectors.joining`，是现代 Java 字符串处理的推荐姿势。
