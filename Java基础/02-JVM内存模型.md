# JVM 内存模型

Java 程序运行时，JVM 会把内存划分为若干区域，每个区域存不同的东西、有不同的生命周期。理解 JVM 内存划分，是搞懂「为什么 `==` 比较引用是比地址」「为什么方法参数传递后互相影响」「为什么对象有默认值」的钥匙——这些看似无关的现象，根子都在内存布局上。

> 💡 本篇是 Java 内存视角的入门。建议配合 [04-数据类型与类型转换](04-数据类型与类型转换.md) 一起看：基本类型存值、引用类型存地址，这个差异正源于 JVM 把它们放在了不同的内存区域。

---

## 一、JVM 内存划分总览

JVM 运行时数据区分为五大区域。其中方法区和堆是**线程共享**的，虚拟机栈、本地方法栈、程序计数器是**线程私有**的。

```
┌──────────────────────────────────────────────────────┐
│                  JVM 运行时数据区                     │
│  ┌────────────────────────────────────────────────┐  │
│  │   堆（Heap）            ← 线程共享，存 new 对象 │  │
│  │   方法区（Method Area）  ← 线程共享，存类信息     │  │
│  └────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 虚拟机栈      │  │ 本地方法栈    │  │程序计数器(PC)│ │
│  │ (VM Stack)   │  │(Native Stack)│  │  Register   │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│         ↑               ↑                ↑           │
│      每个线程一份     每个线程一份     每个线程一份     │
└──────────────────────────────────────────────────────┘
```

| 区域 | 作用 | 线程共享 | 存什么 |
| :--- | :--- | :---: | :--- |
| **堆** | 存对象实例 | ✅ 共享 | `new` 出来的所有对象、数组 |
| **方法区** | 存类信息 | ✅ 共享 | 类信息、常量池、静态变量、方法字节码 |
| **虚拟机栈** | 方法执行 | ❌ 私有 | 栈帧（局部变量表、操作数栈、方法出口） |
| **本地方法栈** | native 方法执行 | ❌ 私有 | 服务于 C/C++ 写的 native 方法 |
| **程序计数器** | 记录执行位置 | ❌ 私有 | 当前线程执行到的字节码行号 |

> 💡 **记忆口诀**：**两共享（堆、方法区）+ 三私有（栈、本地栈、PC）**。面试常问「哪些区域线程共享」，答堆和方法区即可。

---

## 二、程序计数器（PC 寄存器）

程序计数器（Program Counter Register）是一块很小的内存区域，记录**当前线程正在执行的字节码行号**。

```java
public class PCDemo {
    public static void main(String[] args) {   // PC 指向第 1 行
        int a = 10;                            // PC 指向第 2 行
        int b = 20;                            // PC 指向第 3 行
        int c = a + b;                         // PC 指向第 4 行
        System.out.println(c);                 // PC 指向第 5 行
    }
}
```

- **线程私有**：每个线程有自己的 PC，互不干扰。线程切换回来时能从上次位置继续执行。
- **唯一不会 OOM 的区域**：PC 占用空间极小，JVM 规范中它是唯一不会发生 `OutOfMemoryError` 的区域。

> 💡 如果执行的是 native 方法，PC 的值为 `undefined`（未定义）。

---

## 三、虚拟机栈（VM Stack）

虚拟机栈描述的是 **Java 方法执行的内存模型**：每个方法调用时创建一个**栈帧**压入栈，方法返回时栈帧出栈。

### 3.1 栈帧结构

```
┌─────────────────────────────┐
│          栈帧（Frame）        │
│  ┌─────────────────────────┐ │
│  │  局部变量表              │ │  ← 存方法参数和方法内局部变量
│  │  (Local Variable Table) │ │     （基本类型直接存值，引用类型存地址）
│  ├─────────────────────────┤ │
│  │  操作数栈                │ │  ← 方法执行过程中的临时数据栈
│  │  (Operand Stack)        │ │     （如 a + b 的中间结果）
│  ├─────────────────────────┤ │
│  │  动态链接                │ │  ← 指向运行时常量池中方法的引用
│  ├─────────────────────────┤ │
│  │  方法返回地址            │ │  ← 方法结束后跳回调用者的位置
│  │  (Return Address)       │ │
│  └─────────────────────────┘ │
└─────────────────────────────┘
```

### 3.2 方法调用 = 压栈，方法返回 = 出栈

```java
public class StackDemo {
    public static void main(String[] args) {   // 栈帧 1 压栈
        int x = 10;
        int r = add(x, 5);                      // 调用 add，栈帧 2 压栈
        System.out.println(r);                  // add 返回后，栈帧 2 出栈
    }

    public static int add(int a, int b) {       // 栈帧 2
        int sum = a + b;                        // 局部变量 sum 存在栈帧的局部变量表
        return sum;                             // 返回，栈帧 2 出栈
    }
}
```

执行过程：

```
调用 main：    栈 [main]
调用 add：     栈 [main, add]
add 返回：     栈 [main]
main 返回：    栈 []   （栈空，程序结束）
```

> 💡 **栈是后进先出（LIFO）**。方法调用越深，栈帧越多，栈空间占用越大。递归太深会 `StackOverflowError`。

### 3.3 局部变量表存什么

```java
public void demo(int num, String name) {
    // num、name、flag、arr 都存在本方法栈帧的局部变量表里
    boolean flag = true;
    int[] arr = {1, 2, 3};

    // 基本类型 num、flag：直接存值
    // 引用类型 name、arr：存的是堆中对象的地址
}
```

| 变量 | 类型 | 局部变量表存的内容 |
| :--- | :--- | :--- |
| `num` | int | `10`（值本身） |
| `flag` | boolean | `true`（值本身） |
| `name` | String | `0x7F3A`（堆中 String 对象的地址） |
| `arr` | int[] | `0x8B2C`（堆中数组对象的地址） |

### 3.4 栈溢出与栈深度

```java
// ❌ 无限递归，最终 StackOverflowError
public static void loop() {
    loop();   // 没有终止条件，栈帧无限压栈
}
// Exception in thread "main" java.lang.StackOverflowError

// ✅ 递归必须有终止条件
public static int factorial(int n) {
    if (n == 1) return 1;          // 终止条件
    return n * factorial(n - 1);   // 递归调用
}
```

> ⚠️ 默认栈大小约 512KB~1MB（不同平台不同），可用 `-Xss` 参数调整，如 `java -Xss256k StackDemo`。栈越大，能支持的递归深度越深，但每个线程占的内存也越多。

---

## 四、本地方法栈

本地方法栈与虚拟机栈作用相同，区别在于：虚拟机栈执行 Java 方法，本地方法栈执行 **native 方法**（C/C++ 写的、用 `native` 关键字修饰的方法）。

```java
public class NativeDemo {
    // native 方法：Java 声明，C/C++ 实现
    // 它的具体实现在本地方法栈中执行
    public native void start();

    public static void main(String[] args) {
        // Object.getClass()、Thread.start0()、System.currentTimeMillis()
        // 底层都是 native 方法
        long t = System.currentTimeMillis();   // ✅ 调用 native 方法
    }
}
```

> 💡 日常开发几乎不直接写 native 方法，知道「它服务于 native 方法、和虚拟机栈结构一样」即可。HotSpot 把虚拟机栈和本地方法栈合二为一实现。

---

## 五、堆（Heap）

堆是 JVM 管理的最大一块内存，**所有 `new` 出来的对象和数组都在堆里**。堆是线程共享的，也是垃圾回收（GC）的主战场。

### 5.1 堆存什么

```java
public class HeapDemo {
    public static void main(String[] args) {
        // new 出来的对象都在堆里
        Student s1 = new Student("张三", 20);   // ✅ Student 对象在堆
        Student s2 = new Student("李四", 22);   // ✅ 另一个 Student 对象在堆
        int[] arr = new int[3];                // ✅ 数组也是对象，在堆里

        // s1、s2、arr 这些引用变量本身在 main 栈帧的局部变量表里
        // 它们存的是堆中对象的地址
    }
}

class Student {
    String name;
    int age;
    // Student 类的类信息（字段结构、方法字节码）在方法区
    // 但每个 Student 实例的 name/age 值在堆里
}
```

内存图：

```
栈（main 栈帧局部变量表）         堆
┌──────────────────┐           ┌─────────────────────┐
│ s1 = 0x1000      │ ─────→   │ Student@0x1000      │
│ s2 = 0x2000      │ ─────→   │  name = "张三"       │
│ arr = 0x3000     │ ─────→   │  age  = 20          │
└──────────────────┘           ├─────────────────────┤
                               │ Student@0x2000      │
                               │  name = "李四"       │
                               │  age  = 22          │
                               ├─────────────────────┤
                               │ int[3]@0x3000       │
                               │  [0]=0 [1]=0 [2]=0  │
                               └─────────────────────┘
```

### 5.2 堆的分代（了解）

现代 JVM（HotSpot）把堆分为新生代和老年代：

```
┌──────────────────────────────────────┐
│                  堆                   │
│  ┌─────────────────┐  ┌────────────┐ │
│  │   新生代（Young） │  │ 老年代（Old）│ │
│  │  Eden + S0 + S1  │  │            │ │
│  └─────────────────┘  └────────────┘ │
│  新对象先在 Eden，GC 后存活进 Survivor │  长期存活的对象晋升老年代
└──────────────────────────────────────┘
```

```java
// 新对象一般先分配在新生代 Eden 区
Student s = new Student();   // ✅ Eden 区分配

// 大对象（如大数组）可能直接进老年代，避免在新生代来回复制
byte[] big = new byte[1024 * 1024 * 10];   // 10MB，可能直接进老年代
```

> 💡 堆分代是 GC 优化的基础，本篇只做了解。后续学垃圾回收会详细展开。

### 5.3 堆溢出

```java
// ❌ 不断 new 对象且不被回收，最终堆溢出
import java.util.ArrayList;
import java.util.List;

public class OOMDemo {
    public static void main(String[] args) {
        List<Student> list = new ArrayList<>();
        while (true) {
            list.add(new Student());   // 无限添加，堆迟早撑爆
        }
        // Exception in thread "main" java.lang.OutOfMemoryError: Java heap space
    }
}
```

> ⚠️ 堆大小用 `-Xms`（初始）、`-Xmx`（最大）设置，如 `java -Xms256m -Xmx512m OOMDemo`。生产环境建议 `-Xms` 和 `-Xmx` 设成一样，避免运行时动态扩容带来性能抖动。

---

## 六、方法区（Method Area）

方法区存的是**类信息、常量池、静态变量、方法字节码**——它是「类的图纸仓库」。方法区是线程共享的。

### 6.1 方法区存什么

| 内容 | 例子 |
| :--- | :--- |
| 类信息 | 类名、父类、接口、字段定义、方法定义 |
| 运行时常量池 | 字符串常量、`final` 常量、方法/字段符号引用 |
| 静态变量 | `static` 修饰的成员变量 |
| 方法字节码 | 每个方法编译后的指令 |
| 类的类对象 | `Class` 对象（反射用） |

```java
public class MethodAreaDemo {
    // static 变量存在方法区
    static int count = 0;                    // ✅ 方法区
    static final String APP_NAME = "MyApp";  // ✅ 方法区常量池

    String name;   // 实例字段定义在方法区，但每个对象的 name 值在堆里

    public void run() { }   // 方法的字节码存在方法区
}
```

> ⚠️ **关键区分**：**静态变量（`static`）存在方法区**，**实例变量（非 static）存在堆**（跟着每个对象走）。这是新手最容易混淆的点。

### 6.2 方法区的实现变迁

| JDK 版本 | 方法区实现 | 别名 |
| :--- | :--- | :--- |
| JDK 7 及以前 | 永久代（PermGen），在堆中 | Perm Space |
| **JDK 8 起** | **元空间（Metaspace）**，使用本地内存 | Meta Space |

```bash
# JDK 7 调整永久代大小
-XX:PermSize=64m -XX:MaxPermSize=256m

# JDK 8 调整元空间大小（用本地内存，不占堆）
-XX:MetaspaceSize=64m -XX:MaxMetaspaceSize=256m
```

> 💡 **为什么 JDK 8 把永久代换成元空间？** 永久代大小固定、容易 OOM（`OutOfMemoryError: PermGen space`），而且难以调优。元空间用本地内存，大小随系统内存动态扩展，大大降低了类加载导致的 OOM。

### 6.3 运行时常量池

```java
public class ConstantPoolDemo {
    public static void main(String[] args) {
        // 字符串字面量在编译期进入 class 文件常量池
        // 类加载后进入方法区的运行时常量池
        String s1 = "hello";          // "hello" 在常量池
        String s2 = "hello";          // 复用常量池中的 "hello"
        System.out.println(s1 == s2); // ✅ true，同一常量池对象

        String s3 = new String("hello");  // new 在堆里新建对象
        System.out.println(s1 == s3);      // ❌ false，堆对象 vs 常量池对象
    }
}
```

> ⚠️ 字符串 `==` 比较的坑，根源就在常量池和堆的区别。详见 [18-字符串](18-字符串String与StringBuilder.md)。

### 6.4 方法区溢出

```java
// ❌ 不断加载新类，元空间溢出（CGLIB 等动态字节码工具常见）
// Exception in thread "main" java.lang.OutOfMemoryError: Metaspace
```

> 💡 实际开发中，Spring、MyBatis、CGLIB 等框架动态生成类，如果元空间太小可能 OOM。生产环境建议显式设置 `-XX:MaxMetaspaceSize`。

---

## 七、基本类型 vs 引用类型在内存中的差异

这是本篇最核心的内容，理解了它，后续的参数传递、`==` 比较、数组操作都通了。

### 7.1 基本类型：变量直接存值

```java
int a = 10;
int b = a;     // 值拷贝
b = 20;
System.out.println(a);   // 10，a 不受影响
```

内存图：

```
栈（局部变量表）
┌─────────┐
│ a = 10  │   ← a 直接存值 10
│ b = 20  │   ← b 拷贝了 a 的值后独立修改
└─────────┘
```

### 7.2 引用类型：变量存的是堆地址

```java
int[] arr1 = {1, 2, 3};
int[] arr2 = arr1;     // 地址拷贝
arr2[0] = 99;
System.out.println(arr1[0]);   // 99，arr1 被影响！
```

内存图：

```
栈                          堆
┌──────────────┐          ┌──────────────┐
│ arr1 = 0x100 │ ───────→ │ {99, 2, 3}   │  ← 同一个数组对象
│ arr2 = 0x100 │ ───────→ │              │
└──────────────┘          └──────────────┘
   两个引用存同一地址
```

> ⚠️ **这就是「引用类型赋值 = 地址拷贝」**。两个引用指向堆里同一个对象，任一个修改都会影响对方。

### 7.3 对比总结

| 特性 | 基本类型 | 引用类型 |
| :--- | :--- | :--- |
| 变量存什么 | 值本身 | 堆中对象的地址 |
| 赋值操作 | 值拷贝，互不影响 | 地址拷贝，互相影响 |
| 存储位置 | 栈（局部变量表） | 对象在堆，地址在栈 |
| 默认值 | 有（int=0、boolean=false） | 有（null） |
| `==` 比较 | 比值 | 比地址 |

---

## 八、数组在内存中的存储

数组也是对象，`new` 出来的数组在堆里，引用变量在栈里存地址。

### 8.1 动态初始化的数组

```java
int[] arr = new int[3];    // 堆里创建长度 3 的数组
arr[0] = 10;
arr[1] = 20;
// arr[2] 没赋值，默认 0
```

内存图：

```
栈                        堆
┌──────────┐            ┌─────────────────┐
│ arr=0x100│ ─────────→ │ int[3] @0x100   │
└──────────┘            │ [0]=10 [1]=20 [2]=0 │
                        └─────────────────┘
```

> 💡 **数组的默认值从哪来？** `new int[3]` 在堆里分配空间时，JVM 会把每个元素初始化为默认值（int=0、boolean=false、引用类型=null）。这就是「对象有默认值」的根源——堆内存初始化。

### 8.2 静态初始化的数组

```java
int[] arr = {1, 2, 3};    // 等价于 new int[]{1, 2, 3}
// 底层仍是 new 一个数组对象在堆里
```

### 8.3 引用类型数组

```java
String[] strs = new String[3];
strs[0] = "A";
strs[1] = "B";
// strs[2] 未赋值，默认 null
```

内存图：

```
栈                          堆
┌───────────┐             ┌────────────────────┐
│ strs=0x200│ ──────────→ │ String[3] @0x200   │
└───────────┘             │ [0]→"A"  [1]→"B"   │
                          │ [2]=null           │
                          └─────┬──────┬───────┘
                                 │      │
                              ┌──▼─┐  ┌─▼─┐
                              │ "A"│  │"B"│  ← 字符串对象（在堆/常量池）
                              └────┘  └───┘
```

> ⚠️ 引用类型数组的元素存的是**对象的地址**，不是对象本身。未赋值的元素是 `null`，访问会抛 `NullPointerException`。

---

## 九、两个引用指向同一个对象

这是理解「引用」概念的关键案例，也是方法参数传递的基础。

### 9.1 基本场景

```java
class Phone {
    String brand;
    int price;
}

Phone p1 = new Phone();   // 堆里建对象，p1 存其地址
p1.brand = "Apple";
p1.price = 8999;

Phone p2 = p1;            // p2 拷贝了 p1 的地址，指向同一对象
p2.price = 7999;          // 通过 p2 修改

System.out.println(p1.price);   // 7999，p1 也变了！
System.out.println(p1 == p2);   // true，同一地址
```

内存图：

```
栈                         堆
┌──────────┐             ┌──────────────────┐
│ p1=0x300 │ ──────→     │ Phone@0x300       │
│ p2=0x300 │ ──────→     │  brand = "Apple"  │
└──────────┘             │  price = 7999     │  ← 被 p2 改了
                         └──────────────────┘
```

### 9.2 为什么 `==` 比较引用类型是比地址

```java
String s1 = new String("hi");
String s2 = new String("hi");
System.out.println(s1 == s2);        // ❌ false，两个不同堆对象
System.out.println(s1.equals(s2));   // ✅ true，比较内容

String s3 = "hi";
String s4 = "hi";
System.out.println(s3 == s4);        // ✅ true，常量池同一对象
```

> ⚠️ **`==` 比较的是栈里存的地址**，`equals` 比较的是堆里对象的内容（String 重写了 equals）。这就是为什么引用类型内容比较必须用 `equals`。

---

## ⚠️ 重点

### 重点 1：栈存局部变量，堆存对象，方法区存类信息 ⭐⭐⭐

```
栈：方法内的局部变量（基本类型存值、引用类型存地址）
堆：new 出来的对象、数组
方法区：类信息、静态变量、常量池、方法字节码
```

> 💡 这是 JVM 内存的三层模型，务必刻进脑子。后续所有内存相关问题都围绕这三层展开。

### 重点 2：基本类型直接存值，引用类型存地址 ⭐⭐⭐

```java
int a = 10;          // 栈里直接存 10
int[] arr = {1,2};   // 栈里存堆地址，数组对象在堆
```

### 重点 3：两个引用指向同一对象，修改互相影响 ⭐⭐⭐

```java
Student s1 = new Student();
Student s2 = s1;        // 同一对象
s2.name = "张三";
System.out.println(s1.name);   // 张三，被影响了
```

### 重点 4：方法调用压栈，返回出栈 ⭐⭐

```java
main() → A() → B()   // 栈：[main, A, B]
B 返回                // 栈：[main, A]
A 返回                // 栈：[main]
main 返回             // 栈：[]，程序结束
```

### 重点 5：静态变量在方法区，实例变量在堆 ⭐⭐

```java
class Config {
    static int timeout = 30;   // 方法区，全类共享一份
    String env;                // 堆，每个对象一份
}
```

### 重点 6：对象的默认值来自堆内存初始化 ⭐

```java
int[] arr = new int[3];     // 堆里 [0,0,0]，JVM 初始化默认值
String[] strs = new String[2];  // 堆里 [null, null]
```

| 类型 | 默认值 |
| :--- | :--- |
| byte/short/int/long | 0 |
| float/double | 0.0 |
| char | ''（空字符） |
| boolean | false |
| 引用类型 | null |

> ⚠️ **局部变量没有默认值**！方法内的局部变量必须先赋值才能用，否则编译报错。只有堆里的成员变量才有默认值。

```java
public void demo() {
    int x;   // 局部变量
    // System.out.println(x);  // ❌ 编译错误：可能尚未初始化变量 x
    x = 10;
    System.out.println(x);     // ✅
}
```

---

## 💻 实战案例

### 案例 1：通过内存图解释「为什么 `==` 比较引用类型是比地址」⭐⭐⭐

电商系统里判断两个订单是否是同一单，新手常踩坑：

```java
class Order {
    String orderId;
    double amount;

    Order(String orderId, double amount) {
        this.orderId = orderId;
        this.amount = amount;
    }
}

public class OrderCompare {
    public static void main(String[] args) {
        Order o1 = new Order("ORD001", 199.0);
        Order o2 = new Order("ORD001", 199.0);   // 内容一样，但是两个对象

        // ❌ 用 == 比较，比的是栈里存的地址
        System.out.println(o1 == o2);   // false，两个不同堆对象

        // ✅ 业务上要比较内容，必须自己写 equals（或用 orderId 比对）
        System.out.println(o1.orderId.equals(o2.orderId));   // true
    }
}
```

内存图：

```
栈                              堆
┌──────────┐                  ┌──────────────────────┐
│ o1=0x100 │ ──────→         │ Order@0x100          │
│ o2=0x200 │ ──────→         │  orderId="ORD001"    │
└──────────┘                  │  amount=199.0        │
                              ├──────────────────────┤
                              │ Order@0x200          │
                              │  orderId="ORD001"    │
                              │  amount=199.0        │
                              └──────────────────────┘
   两个引用地址不同（0x100 ≠ 0x200），所以 == 是 false
   但内容相同，业务上应判为「同一单」
```

> 📌 **规范**：业务对象比较永远用 `equals`，并在类里重写 `equals` 和 `hashCode`（IDEA 用 `Alt+Insert` 生成）。这是 Java 开发的铁律。

### 案例 2：方法参数传递的内存变化 ⭐⭐⭐

后台系统里「修改入参」的经典 bug：

```java
class User {
    String name;
    int age;
    User(String name, int age) { this.name = name; this.age = age; }
}

public class ParamPassDemo {
    // 基本类型参数：值传递，方法内修改不影响外部
    public static void changeInt(int x) {
        x = 999;   // 改的是 x 这个副本
    }

    // 引用类型参数：地址值传递，方法内通过地址修改对象，外部能看到
    public static void changeUser(User u) {
        u.age = 999;   // 通过地址改堆里对象，外部受影响
    }

    // 引用类型参数：重新指向新对象，不影响外部引用
    public static void reassignUser(User u) {
        u = new User("新用户", 0);   // u 这个副本指向新对象，原引用不变
    }

    public static void main(String[] args) {
        int n = 10;
        changeInt(n);
        System.out.println(n);   // 10，不变

        User user = new User("张三", 20);
        changeUser(user);
        System.out.println(user.age);   // 999，被改了！

        reassignUser(user);
        System.out.println(user.name);  // 张三，不变（user 仍指向原对象）
    }
}
```

> ⚠️ **Java 只有值传递**。基本类型传的是值的副本，引用类型传的是地址的副本。但通过地址副本去修改堆里对象，外部能看到——因为指向的是同一个堆对象。

`changeUser` 的内存变化：

```
调用前：
栈(main)         堆
┌──────────┐    ┌──────────────────┐
│ user=0x100│ → │ User@0x100        │
└──────────┘    │  name="张三"      │
                │  age=20           │
                └──────────────────┘

调用 changeUser(user)：
栈(main + changeUser)
┌──────────┐    ┌──────────────────┐
│ user=0x100│ → │ User@0x100        │
│ u   =0x100│ → │  name="张三"      │
└──────────┘    │  age=999 ← 被改  │  ← 同一对象，外部可见
                └──────────────────┘

changeUser 返回后：u 出栈，但堆里对象已被改
```

> 📌 **开发规范**：方法内不要直接修改入参对象的内部状态（除非方法名明确表示 modify/update）。如果要返回修改后的结果，建议返回新对象，避免副作用。

### 案例 3：数组引用赋值后互相影响 ⭐⭐

金融系统里，误把原数组赋给新变量导致数据污染：

```java
public class ArrayRefBug {
    public static void main(String[] args) {
        // ❌ 错误：直接赋值，两个引用同一数组
        int[] q1Revenue = {100, 200, 300};
        int[] q2Revenue = q1Revenue;        // 不是复制！是地址拷贝
        q2Revenue[0] = 999;
        System.out.println(q1Revenue[0]);   // 999，一季度数据被污染了！

        // ✅ 正确：要复制数组，用 clone 或 System.arraycopy
        int[] q3Revenue = {100, 200, 300};
        int[] q4Revenue = q3Revenue.clone();   // 堆里新建数组
        q4Revenue[0] = 999;
        System.out.println(q3Revenue[0]);   // 100，原数据安全
    }
}
```

内存图（错误场景）：

```
栈                          堆
┌──────────────┐          ┌──────────────────┐
│ q1Revenue=0x100│ ──────→│ {999, 200, 300}  │  ← 同一数组，被 q2 改了
│ q2Revenue=0x100│ ──────→│                  │
└──────────────┘          └──────────────────┘
```

> 📌 **规范**：需要独立副本时，用 `clone()`、`Arrays.copyOf()` 或 `System.arraycopy()`，不要直接 `=` 赋值。这是金融/数据系统的高频 bug 源。

### 案例 4：静态变量 vs 实例变量的内存差异 ⭐

后台系统配置管理：

```java
class AppConfig {
    // 静态变量：方法区，全类共享一份
    static String serverUrl = "http://api.example.com";
    static int maxConn = 100;

    // 实例变量：堆，每个对象一份
    String moduleName;
    int moduleOrder;

    AppConfig(String name, int order) {
        this.moduleName = name;
        this.moduleOrder = order;
    }
}

public class StaticVsInstance {
    public static void main(String[] args) {
        AppConfig a = new AppConfig("用户模块", 1);
        AppConfig b = new AppConfig("订单模块", 2);

        // 实例变量各自独立（在堆里，每个对象一份）
        System.out.println(a.moduleName);   // 用户模块
        System.out.println(b.moduleName);   // 订单模块

        // 静态变量共享（在方法区，全类一份）
        AppConfig.maxConn = 200;            // 通过 a 改，b 看到的也是 200
        System.out.println(AppConfig.maxConn);   // 200，建议用类名访问
    }
}
```

内存图：

```
栈                              堆
┌──────────┐                  ┌──────────────────────┐
│ a=0x100  │ ──────→         │ AppConfig@0x100      │
│ b=0x200  │ ──────→         │  moduleName="用户模块"│
└──────────┘                  │  moduleOrder=1       │
                              ├──────────────────────┤
                              │ AppConfig@0x200      │
                              │  moduleName="订单模块"│
                              │  moduleOrder=2       │
                              └──────────────────────┘

方法区
┌──────────────────────────────┐
│ AppConfig 类信息              │
│  serverUrl="http://..."       │  ← 静态变量，全类共享一份
│  maxConn=200                  │
└──────────────────────────────┘
```

> 📌 **规范**：静态变量用类名访问（`AppConfig.maxConn`），不要用对象引用访问（`a.maxConn` 虽然能编译，但容易误导。静态变量属于类，不属于对象。

### 案例 5：递归调用与栈深度 ⭐

后台任务调度里递归遍历组织树，层级太深导致栈溢出：

```java
class OrgNode {
    String name;
    OrgNode parent;
    OrgNode(String name) { this.name = name; }
}

public class RecursionDemo {
    // ❌ 递归太深会 StackOverflowError
    public static void printUp(OrgNode node) {
        if (node == null) return;
        System.out.println(node.name);
        printUp(node.parent);   // 层层向上递归
    }

    // ✅ 改为循环，避免栈溢出
    public static void printUpLoop(OrgNode node) {
        while (node != null) {
            System.out.println(node.name);
            node = node.parent;
        }
    }

    public static void main(String[] args) {
        // 构造 10000 层的组织树
        OrgNode cur = new OrgNode("level0");
        for (int i = 1; i < 10000; i++) {
            OrgNode next = new OrgNode("level" + i);
            next.parent = cur;
            cur = next;
        }
        // printUp(cur);       // ❌ 可能 StackOverflowError
        printUpLoop(cur);       // ✅ 循环版本安全
    }
}
```

> ⚠️ **生产环境教训**：递归深度不可控时（如用户构造的树结构），优先用循环代替递归。递归的栈深度等于调用深度，栈空间有限。必要时用显式栈（`Stack`/`Deque`）模拟递归。

---

## 🚀 新版本补充

### Java 8：元空间取代永久代

Java 8 是方法区实现的分水岭：

| 版本 | 方法区实现 | 存储位置 | 调参参数 |
| :--- | :--- | :--- | :--- |
| JDK 7 及以前 | 永久代（PermGen） | JVM 进程内（堆中） | `-XX:PermSize` / `-XX:MaxPermSize` |
| **JDK 8+** | **元空间（Metaspace）** | **本地内存** | `-XX:MetaspaceSize` / `-XX:MaxMetaspaceSize` |

> 💡 Java 8 把方法区从「永久代」搬到「元空间」是基准内容，不属于新版本补充。这里列出是为了强调它从 Java 8 开始生效。

### Java 10：堆内存分配方式优化

```bash
# Java 10 引入 G1 作为默认垃圾收集器（Java 8 默认 Parallel）
# 对堆内存分配和 GC 有影响，但内存区域划分本身不变
java -XX:+UseG1GC MyApp
```

### Java 15：ZGC 生产可用

ZGC 是低延迟垃圾收集器，堆内存划分逻辑不变，但 GC 停顿时间可降到 1ms 以内，适合超大堆场景。

> 💡 本篇讲的是 JVM 规范定义的「运行时数据区」，这是稳定的抽象模型。不同 JDK 版本和垃圾收集器只是实现细节不同，五大区域划分本身从 Java 8 到 21 都没变。

---

## 本章小结

| 区域 | 存什么 | 线程共享 | 常见异常 |
| :--- | :--- | :---: | :--- |
| 程序计数器 | 当前线程字节码行号 | ❌ | 无（不会 OOM） |
| 虚拟机栈 | 栈帧（局部变量、操作数栈、返回地址） | ❌ | StackOverflowError、OOM |
| 本地方法栈 | native 方法的栈帧 | ❌ | StackOverflowError、OOM |
| 堆 | new 出来的对象、数组 | ✅ | OutOfMemoryError: Java heap space |
| 方法区 | 类信息、常量池、静态变量、方法字节码 | ✅ | OOM: Metaspace（JDK8+） |

| 知识点 | 要点 |
| :--- | :--- |
| 三层模型 | 栈存局部变量、堆存对象、方法区存类信息 |
| 基本类型 vs 引用类型 | 基本存值、引用存地址 |
| 两个引用同一对象 | 修改互相影响 |
| 方法调用 | 压栈执行，返回出栈 |
| 静态 vs 实例变量 | 静态在方法区，实例在堆 |
| 对象默认值 | 堆内存初始化，局部变量无默认值 |
| Java 参数传递 | 只有值传递（基本传值，引用传地址副本） |

---

## 学习建议

1. **画内存图，不要只看文字**：本篇每个案例都配了内存图，建议自己拿纸笔重新画一遍。把栈、堆、方法区画成三个框，箭头标出引用指向，理解会瞬间清晰。这是学 JVM 内存最有效的方法。
2. **写代码验证「引用互相影响」**：把案例 1、2、3 的代码敲进 IDE，打断点看变量值，亲眼看到 `p2.price = 7999` 后 `p1.price` 也变了。亲手验证比看十遍文字都管用。
3. **牢记「Java 只有值传递」**：这是面试高频题，也是参数传递理解的钥匙。基本类型传值副本，引用类型传地址副本——但都是「副本」，所以方法内重新指向新对象不影响外部。
4. **区分静态变量和实例变量的存储**：静态在方法区全类共享，实例在堆里每个对象一份。看到 `static` 就想到方法区，看到 `new` 就想到堆，这个直觉要立刻建立。
5. **不要纠结分代和 GC 细节**：本篇重点是五大区域的划分和存储内容，堆分代、GC 算法是后续专题的内容。先把「什么存在哪」搞清楚，再深入「怎么回收」。
