# static 关键字与代码块

`static` 是 Java 中最容易让新手困惑的关键字之一。它打破了「属性属于对象」的常识——被 `static` 修饰的成员**属于类本身**，而不是某个对象。理解 `static` 是看懂工具类、单例模式、类加载机制的钥匙，而代码块的执行顺序更是面试的高频考点。

> 💡 本篇会涉及「类加载」「方法区」等内存概念，建议结合 [02-JVM内存模型](02-JVM内存模型.md) 一起理解。

---

## 一、static 修饰变量（静态变量 / 类变量）

### 1.1 什么是静态变量

被 `static` 修饰的成员变量叫**静态变量**（也叫**类变量**）。它与普通成员变量（实例变量）的本质区别：

- **实例变量**：属于对象，每个对象一份，存在堆中
- **静态变量**：属于类，所有对象共享一份，存在方法区（JDK 8 后在堆中）

```java
public class Student {
    String name;            // 实例变量：每个对象一份
    static String school;   // 静态变量：所有对象共享一份
}

Student.school = "清华";    // ✅ 通过类名访问（推荐）
Student s1 = new Student();
s1.name = "张三";
Student s2 = new Student();
s2.name = "李四";

System.out.println(s1.school);   // 清华
System.out.println(s2.school);   // 清华 ← 所有对象共享同一个 school
```

### 1.2 内存图解

```
方法区（JDK8 后在堆）
┌─────────────────────────┐
│  Student.class          │
│  school = "清华"         │  ← 静态变量，类只有一份
└─────────────────────────┘

堆
┌──────────────┐  ┌──────────────┐
│ s1 对象       │  │ s2 对象       │
│ name = "张三" │  │ name = "李四" │  ← 实例变量，各管各的
└──────────────┘  └──────────────┘
   ↑ s1 引用           ↑ s2 引用
栈
```

### 1.3 两种访问方式

```java
// ✅ 推荐方式：通过类名访问（体现「属于类」）
Student.school = "北大";

// ⚠️ 可以但不推荐：通过对象访问
Student s = new Student();
s.school = "复旦";   // 编译器会转成 Student.school = "复旦"
```

> ⚠️ **规范**：静态变量一律用 `类名.变量名` 访问。通过对象访问虽然不报错，但容易让人误以为是实例变量，IDEA 会给出警告。

### 1.4 静态变量 vs 实例变量对比

| 对比项 | 实例变量 | 静态变量 |
| :--- | :--- | :--- |
| 归属 | 属于对象 | 属于类 |
| 内存 | 堆（每个对象一份） | 方法区/堆（类一份） |
| 创建时机 | `new` 对象时 | 类加载时 |
| 销毁时机 | 对象被 GC 回收 | 类卸载时（几乎等于程序结束） |
| 访问方式 | 对象名.变量 | 类名.变量（推荐） |
| 默认值 | 有（int→0、引用→null） | 有（同实例变量） |

### 1.5 静态变量的典型用途

**用途一：所有对象共享的常量**

```java
public class MathUtil {
    public static final double PI = 3.141592653589793;   // 常量
}
// Math.PI 就是 JDK 自带的静态常量
```

**用途二：所有对象共享的状态**

```java
public class Config {
    public static String env = "dev";   // 全局环境标识
}
```

---

## 二、static 修饰方法（静态方法）

### 2.1 静态方法的特点

被 `static` 修饰的方法叫**静态方法**（类方法）：

- 属于类，不属于某个对象
- 可以通过类名直接调用（推荐），无需创建对象
- 可以通过对象调用（不推荐）

```java
public class MathUtil {
    // 静态方法：工具方法
    public static int abs(int n) {
        return n < 0 ? -n : n;
    }
}

// ✅ 类名调用（推荐）
int result = MathUtil.abs(-5);   // 5

// ⚠️ 对象调用（不推荐）
MathUtil m = new MathUtil();
int r2 = m.abs(-5);
```

> 💡 JDK 的 `Math.abs()`、`Math.max()`、`Arrays.sort()`、`Collections.sort()` 都是静态方法，你一直在用。

### 2.2 静态方法的使用场景

**场景一：工具方法**

不依赖对象状态、只做纯计算的方法，最适合做静态方法：

```java
public class StringUtils {
    public static boolean isEmpty(String s) {
        return s == null || s.length() == 0;
    }

    public static String reverse(String s) {
        return new StringBuilder(s).reverse().toString();
    }
}

// 调用：StringUtils.isEmpty("")   → true
// 不用 new 对象，直接用
```

**场景二：main 方法为什么是 static**

```java
public static void main(String[] args) { ... }
```

JVM 启动时还没有创建任何对象，无法通过对象调用 main 方法。所以 main 必须是 static，JVM 通过 `类名.main()` 直接调用。

**场景三：工厂方法**

```java
public class Product {
    private String name;
    private double price;

    private Product(String name, double price) {   // 构造私有
        this.name = name;
        this.price = price;
    }

    // 静态工厂方法
    public static Product create(String name, double price) {
        return new Product(name, price);
    }
}

Product p = Product.create("书", 99.0);
```

### 2.3 静态方法的限制（重点）⭐⭐

静态方法**没有 `this`**，因为它不属于对象。这带来两条硬限制：

1. **不能直接访问实例变量 / 实例方法**（它们属于对象，静态方法里没有对象）
2. **不能使用 `this` / `super`**

```java
public class Student {
    String name;            // 实例变量
    static int count;       // 静态变量

    public void study() { }              // 实例方法
    public static void showCount() {     // 静态方法
        // System.out.println(name);    // ❌ 编译错误：不能访问实例变量
        // study();                      // ❌ 编译错误：不能调用实例方法
        // System.out.println(this);    // ❌ 编译错误：没有 this

        System.out.println(count);      // ✅ 可以访问静态变量
        System.out.println(Student.count);  // ✅
    }
}
```

> ⚠️ **记忆口诀**：静态只能访问静态。实例方法啥都能访问（静态 + 实例）。

| 调用方 | 能否访问实例成员 | 能否访问静态成员 |
| :--- | :---: | :---: |
| 静态方法 | ❌ | ✅ |
| 实例方法 | ✅ | ✅ |

> 💡 **为什么**：静态方法在类加载时就存在，而对象可能还没创建。一个不存在的东西怎么能访问一个还没创建的东西？反过来，实例方法运行时对象已存在，自然能访问静态成员。

---

## 三、静态代码块 static {}

### 3.1 语法与执行时机

```java
public class Config {
    static {
        // 静态代码块：类加载时执行一次
        System.out.println("静态代码块执行");
    }
}
```

特点：

- 由 `static { }` 包裹，没有方法名
- **类加载时执行一次**，且只执行一次
- 用于初始化静态变量（尤其是需要复杂逻辑的初始化）

```java
public class Config {
    static String dbUrl;
    static String dbUser;

    static {
        // 模拟从配置文件读取（实际用 Properties）
        dbUrl = "jdbc:mysql://localhost:3306/test";
        dbUser = "root";
        System.out.println("静态代码块：初始化数据库配置");
    }

    public static void main(String[] args) {
        System.out.println("main 方法执行");
        System.out.println(Config.dbUrl);
    }
}
// 输出：
// 静态代码块：初始化数据库配置
// main 方法执行
// jdbc:mysql://localhost:3306/test
```

> 💡 **执行顺序**：静态代码块在 main 方法之前执行。因为 main 方法被调用前，类必须先被加载，而类加载就会触发静态代码块。

### 3.2 多个静态代码块

一个类可以有多个静态代码块，按**书写顺序**执行：

```java
public class Demo {
    static { System.out.println("静态块 1"); }
    static { System.out.println("静态块 2"); }
    static { System.out.println("静态块 3"); }

    public static void main(String[] args) {
        System.out.println("main");
    }
}
// 输出：静态块 1 → 静态块 2 → 静态块 3 → main
```

### 3.3 静态代码块 vs 直接赋值

```java
// 方式一：直接赋值
public class A {
    static int x = 10;
}

// 方式二：静态代码块（适合复杂逻辑）
public class B {
    static int x;
    static {
        x = loadFromConfig();   // 需要调用方法、读文件等
    }
}
```

> 💡 简单赋值用 `static int x = 10`，需要复杂初始化逻辑（读配置、算值）才用静态代码块。

---

## 四、构造代码块 {}

### 4.1 语法与执行时机

去掉 `static` 的 `{ }` 就是构造代码块（实例初始化块）：

```java
public class Student {
    String name;

    {
        // 构造代码块：每次创建对象前执行
        System.out.println("构造代码块执行");
    }

    public Student() {
        System.out.println("无参构造执行");
    }

    public Student(String name) {
        this.name = name;
        System.out.println("有参构造执行");
    }
}

new Student();
// 输出：构造代码块执行 → 无参构造执行

new Student("张三");
// 输出：构造代码块执行 → 有参构造执行
```

特点：

- 每次 `new` 对象时执行，**在构造方法之前**
- 每创建一个对象执行一次
- 用于多个构造方法的公共初始化逻辑

### 4.2 实际开发很少用

> ⚠️ 构造代码块在实际开发中几乎不用。原因：
> 1. 它的执行时机不直观，降低可读性
> 2. 多个构造方法的公共逻辑，更推荐用 `this(...)` 调用公共构造方法，或抽取成 `init()` 方法
> 3. IDEA 也会给出「可以内联到构造方法」的提示

```java
// ❌ 不推荐：用构造代码块做公共初始化
public class Student {
    { init(); }
    public Student() {}
    public Student(String n) { this.name = n; }
    private void init() { /* ... */ }
}

// ✅ 推荐：抽取 init 方法，构造方法里显式调用
public class Student {
    public Student() { init(); }
    public Student(String n) { this(); this.name = n; }  // this() 复用无参构造
    private void init() { /* ... */ }
}
```

---

## 五、局部代码块 {}

### 5.1 语法与作用

方法内部的 `{ }` 就是局部代码块，用于限定变量的作用域：

```java
public void test() {
    {
        int a = 10;
        System.out.println(a);   // ✅ 10
    }
    // System.out.println(a);   // ❌ a 已出作用域，编译错误
}
```

> 💡 局部代码块在现代开发中几乎不用。它的初衷是「提前释放变量、节省内存」，但 JVM 的即时编译（JIT）已经足够智能，手动限制作用域意义不大，反而降低可读性。了解即可。

---

## 六、完整初始化顺序（重点 ⭐⭐⭐）

这是面试必考、开发必懂的硬核知识点。当有继承关系时，完整的初始化顺序如下：

### 6.1 单个类的初始化顺序

```java
public class Demo {
    static { System.out.println("1. 静态代码块"); }
    { System.out.println("2. 构造代码块"); }

    public Demo() {
        System.out.println("3. 构造方法");
    }

    public static void main(String[] args) {
        System.out.println("4. main 方法");
        new Demo();
        System.out.println("5. 第二次 new");
        new Demo();
    }
}
```

```
输出：
1. 静态代码块       ← 类加载时，只执行一次
4. main 方法
2. 构造代码块       ← 每次 new 都执行
3. 构造方法
5. 第二次 new
2. 构造代码块
3. 构造方法
```

**单类顺序**：静态代码块（一次）→ main → 构造代码块 → 构造方法（每次 new）

### 6.2 有继承时的完整顺序 ⭐⭐⭐

```java
class Father {
    static { System.out.println("1. 父类静态代码块"); }
    { System.out.println("3. 父类构造代码块"); }

    public Father() {
        System.out.println("4. 父类构造方法");
    }
}

class Son extends Father {
    static { System.out.println("2. 子类静态代码块"); }
    { System.out.println("5. 子类构造代码块"); }

    public Son() {
        System.out.println("6. 子类构造方法");
    }
}

public class Test {
    public static void main(String[] args) {
        System.out.println("--- 第一次 new Son() ---");
        new Son();
        System.out.println("--- 第二次 new Son() ---");
        new Son();
    }
}
```

```
输出：
--- 第一次 new Son() ---
1. 父类静态代码块       ← 类加载阶段：父类静态 → 子类静态
2. 子类静态代码块
--- 第二次 new Son() ---  ← 注意：静态代码块只执行一次
3. 父类构造代码块       ← 对象创建阶段：父类构造 → 子类构造
4. 父类构造方法
5. 子类构造代码块
6. 子类构造方法
3. 父类构造代码块       ← 第二次 new，静态代码块不再执行
4. 父类构造方法
5. 子类构造代码块
6. 子类构造方法
```

### 6.3 顺序口诀 ⭐⭐⭐

> **静态优先、父类优先、静态只一次**

完整顺序（首次创建子类对象时）：

```
1. 父类静态代码块 / 静态变量赋值   ┐
2. 子类静态代码块 / 静态变量赋值   ┘ 类加载阶段，只一次
3. 父类构造代码块
4. 父类构造方法                    ┐
5. 子类构造代码块                   │ 对象创建阶段，每次 new 都执行
6. 子类构造方法                    ┘
```

> ⚠️ **细节**：静态变量赋值和静态代码块是**同等级别**的，按**书写顺序**执行。构造代码块和实例变量赋值也是同等级别，按书写顺序执行。

```java
class A {
    static int x = initX();        // 静态变量赋值
    static { x = 20; }             // 静态代码块
    // 如果把上面两行调换位置，x 的最终值会不同！
    static int initX() { return 10; }
}
```

### 6.4 静态变量赋值与静态代码块的顺序

```java
public class Order {
    static int a = method1();      // 先执行，返回 10
    static { a = 20; }              // 后执行，a 改成 20
    static int b = method2();      // 最后执行，返回 30

    static int method1() {
        System.out.println("method1");
        return 10;
    }
    static int method2() {
        System.out.println("method2");
        return 30;
    }

    public static void main(String[] args) {
        System.out.println("a=" + a + ", b=" + b);
    }
}
// 输出：method1 → method2 → a=20, b=30
```

> 💡 **结论**：静态变量赋值和静态代码块按**源码书写顺序**从上到下执行，不是「代码块永远优先」。

---

## 七、静态导包 import static

### 7.1 语法

`import static` 可以静态导入类的静态成员，使用时不用写类名：

```java
// 普通导入
import java.lang.Math;
// double r = Math.sqrt(2);

// 静态导入
import static java.lang.Math.*;
// 直接用 sqrt，不用写 Math.
double r = sqrt(2);        // ✅
double p = PI;             // ✅
```

### 7.2 实际用途

静态导入常用于测试代码（JUnit 的 `assertEquals`）和数学计算：

```java
import static org.junit.Assert.*;
import static java.lang.Math.*;

public class TestDemo {
    public void test() {
        assertEquals(2, 1 + 1);     // 不用写 Assert.assertEquals
        double area = PI * pow(2, 2);   // 不用写 Math.PI
    }
}
```

> ⚠️ **慎用**：过度使用静态导入会让代码失去「这个方法来自哪个类」的上下文，降低可读性。只对测试断言、数学公式等场景适度使用。

---

## 八、static 的常见误用与注意事项

### 8.1 在静态方法中使用 this ⭐

```java
public class Demo {
    static int x = 1;
    int y = 2;

    public static void test() {
        // System.out.println(this.y);   // ❌ 静态方法没有 this
        // System.out.println(y);        // ❌ 不能访问实例变量
        System.out.println(x);            // ✅ 只能访问静态
    }
}
```

### 8.2 静态方法访问非静态成员的「绕过」方式

静态方法不能「直接」访问实例成员，但可以通过「创建对象」间接访问：

```java
public class Demo {
    int y = 2;

    public static void test() {
        // System.out.println(y);        // ❌ 没有对象
        Demo d = new Demo();             // ✅ 自己 new 一个
        System.out.println(d.y);         // ✅ 通过对象访问
    }
}
```

> 💡 本质：静态方法里没有「现成的 this」，但你可以自己 new 一个对象来用。

### 8.3 静态变量与实例变量的混淆 ⭐

```java
public class Counter {
    int instanceCount = 0;    // ❌ 实例变量：每个对象一份，无法累加
    static int staticCount = 0;  // ✅ 静态变量：所有对象共享

    public Counter() {
        instanceCount++;
        staticCount++;
    }
}

new Counter();
new Counter();
new Counter();
// Counter.instanceCount 还是 1（每个对象自己的）
// Counter.staticCount 是 3（共享累加）
```

> ⚠️ **典型错误**：想统计创建了多少个对象，却把计数器声明成实例变量——每个对象自己从 0 开始，永远统计不到。必须用 static。

### 8.4 静态方法不能被覆盖（重写）⭐

```java
class Father {
    public static void hello() { System.out.println("Father"); }
    public void hi() { System.out.println("Father hi"); }
}

class Son extends Father {
    // 这不是重写，只是「隐藏」
    public static void hello() { System.out.println("Son"); }

    // 实例方法才是真正的重写
    @Override
    public void hi() { System.out.println("Son hi"); }
}

Father f = new Son();
f.hello();   // Father ← 静态方法看引用类型，不体现多态
f.hi();      // Son hi ← 实例方法看对象类型，体现多态
```

> ⚠️ 静态方法属于类，不存在「重写」概念，只有「隐藏」。`@Override` 注解对静态方法无效。这是多态篇的前置知识，先记住结论。

### 8.5 静态变量过多导致内存泄漏风险

静态变量的生命周期与类相同，类不卸载，静态变量就不释放。如果静态集合持有大量对象引用，这些对象永远无法被 GC：

```java
public class Cache {
    // ❌ 危险：静态 Map 持有大量对象，永不释放
    private static java.util.Map<String, Object> cache = new java.util.HashMap<>();

    public static void put(String k, Object v) {
        cache.put(k, v);   // 对象被静态 Map 引用，GC 回收不了
    }
}
```

> ⚠️ 实际开发中，静态集合是内存泄漏的高发区。要么用 `WeakHashMap`，要么提供清理机制，要么用专门的缓存框架（Caffeine、Guava Cache）。

---

## ⚠️ 重点

### 重点 1：静态方法只能访问静态成员 ⭐⭐

```java
public class Demo {
    int a;            // 实例变量
    static int b;      // 静态变量

    public static void test() {
        // System.out.println(a);   // ❌
        System.out.println(b);       // ✅
    }
}
```

> 💡 口诀：**静态只能访问静态**。这是 static 最核心的限制，面试必问。

### 重点 2：静态代码块只在类加载时执行一次 ⭐⭐

```java
public class Demo {
    static { System.out.println("静态块"); }
    public Demo() { System.out.println("构造"); }

    public static void main(String[] args) {
        new Demo();
        new Demo();
    }
}
// 输出：静态块 → 构造 → 构造  ← 静态块只一次
```

### 重点 3：完整初始化顺序 ⭐⭐⭐

> **静态优先、父类优先、静态只一次**

```
父类静态 → 子类静态 → 父类构造块/构造 → 子类构造块/构造
```

这是面试最高频的 static 考点，务必能默写执行顺序。

### 重点 4：静态变量属于类，所有对象共享 ⭐⭐

```java
public class Student {
    static int count = 0;   // 所有 Student 对象共享
    public Student() { count++; }
}
new Student(); new Student();
System.out.println(Student.count);   // 2
```

### 重点 5：静态方法不能被重写，只能被隐藏 ⭐

```java
Father f = new Son();
f.staticMethod();   // 调的是 Father 的（看引用类型）
f.instanceMethod(); // 调的是 Son 的（看对象类型，多态）
```

### 重点 6：main 方法为什么必须是 static ⭐

JVM 启动时还没有任何对象，只能通过 `类名.main()` 调用。如果 main 不是 static，JVM 就得先 new 一个对象才能调，但 new 对象又需要执行 main 之前的初始化——死循环。所以 main 必须是 static。

---

## 💻 实战案例

### 案例 1：统计创建对象个数（static 计数器）⭐⭐

统计某个类创建了多少个对象，是 static 最经典的用途：

```java
public class User {
    private static int count = 0;    // 静态计数器，所有对象共享
    private String name;

    public User() {
        count++;                      // 每创建一个对象 +1
        System.out.println("创建第 " + count + " 个用户");
    }

    public User(String name) {
        this();
        this.name = name;
    }

    public static int getCount() {   // 静态方法访问静态变量
        return count;
    }

    public static void main(String[] args) {
        new User();
        new User("张三");
        new User("李四");
        System.out.println("总共创建：" + User.getCount() + " 个用户");
    }
}
// 输出：
// 创建第 1 个用户
// 创建第 2 个用户
// 创建第 3 个用户
// 总共创建：3 个用户
```

> 💡 **注意**：`this()` 调用无参构造会再次触发 `count++`，所以有参构造里不要再单独 `count++`，否则会重复计数。

### 案例 2：自动生成学号 / 订单号 ⭐⭐

利用 static 计数器自动生成唯一编号，是后台系统的常见需求：

```java
public class Student {
    private static int nextId = 1000;   // 学号自增起点
    private int studentId;             // 学号
    private String name;

    public Student(String name) {
        this.studentId = nextId++;      // ✅ 先取值再自增，保证唯一
        this.name = name;
    }

    public int getStudentId() { return studentId; }
    public String getName() { return name; }

    public static void main(String[] args) {
        Student s1 = new Student("张三");
        Student s2 = new Student("李四");
        Student s3 = new Student("王五");
        System.out.println(s1.getStudentId() + " " + s1.getName());  // 1000 张三
        System.out.println(s2.getStudentId() + " " + s2.getName());  // 1001 李四
        System.out.println(s3.getStudentId() + " " + s3.getName());  // 1002 王五
    }
}
```

订单号生成（实际开发用时间戳 + 序列号，更严谨）：

```java
public class OrderService {
    private static int sequence = 0;

    // 生成订单号：时间戳 + 自增序列
    public static String generateOrderId() {
        long timestamp = System.currentTimeMillis();
        int seq = ++sequence;
        return "ORD" + timestamp + String.format("%04d", seq);
    }

    public static void main(String[] args) {
        System.out.println(generateOrderId());  // ORD17000000000000001
        System.out.println(generateOrderId());  // ORD17000000000000002
    }
}
```

> ⚠️ **多线程注意**：上面的自增在多线程下不安全。实际开发要用 `AtomicInteger` 或加锁，后续并发篇章会讲。

### 案例 3：工具类设计（Arrays / Collections 模式）⭐⭐

JDK 的 `Arrays`、`Collections`、`Math` 全是静态方法，是工具类的标准范式：

```java
public final class ArrayUtils {

    // 私有构造：工具类不应该被实例化
    private ArrayUtils() {
        throw new UnsupportedOperationException("工具类不可实例化");
    }

    public static int max(int[] arr) {
        if (arr == null || arr.length == 0) {
            throw new IllegalArgumentException("数组不能为空");
        }
        int m = arr[0];
        for (int i = 1; i < arr.length; i++) {
            if (arr[i] > m) m = arr[i];
        }
        return m;
    }

    public static int sum(int[] arr) {
        if (arr == null) return 0;
        int total = 0;
        for (int x : arr) total += x;
        return total;
    }

    public static int[] reverse(int[] arr) {
        if (arr == null) return null;
        int[] result = new int[arr.length];
        for (int i = 0; i < arr.length; i++) {
            result[i] = arr[arr.length - 1 - i];
        }
        return result;
    }

    public static void main(String[] args) {
        int[] arr = {3, 1, 4, 1, 5, 9};
        System.out.println(max(arr));         // 9
        System.out.println(sum(arr));          // 23
        int[] r = reverse(arr);
        System.out.println(java.util.Arrays.toString(r));  // [9, 5, 1, 4, 1, 3]
    }
}
```

> 📌 **工具类三要素**：
> 1. `final` 修饰类（不允许继承，避免子类改行为）
> 2. 构造方法私有（不允许 new，纯静态调用）
> 3. 全静态方法

### 案例 4：配置参数静态加载（static 块读配置）⭐

后台系统启动时，常用静态代码块加载配置文件，全局共享：

```java
import java.io.InputStream;
import java.util.Properties;

public class AppConfig {
    private static final Properties props = new Properties();

    // 静态代码块：类加载时读取配置，只读一次
    static {
        try (InputStream is = AppConfig.class.getClassLoader()
                .getResourceAsStream("application.properties")) {
            if (is != null) {
                props.load(is);
                System.out.println("配置加载完成");
            } else {
                System.out.println("配置文件不存在，使用默认值");
            }
        } catch (Exception e) {
            throw new RuntimeException("加载配置失败", e);
        }
    }

    public static String get(String key) {
        return props.getProperty(key);
    }

    public static String get(String key, String defaultValue) {
        return props.getProperty(key, defaultValue);
    }

    public static void main(String[] args) {
        System.out.println(AppConfig.get("db.url", "jdbc:mysql://localhost"));
        System.out.println(AppConfig.get("app.name", "myapp"));
    }
}
```

对应的 `application.properties`（放 resources 目录）：

```properties
db.url=jdbc:mysql://localhost:3306/test
db.username=root
app.name=电商后台
```

> 💡 这就是 Spring `@Value`、`@ConfigurationProperties` 的底层思路——启动时加载配置到静态/单例对象，全局共享。

### 案例 5：单例模式（static 的经典应用）⭐⭐

单例模式保证一个类只有一个实例，是 static + 私有构造的典型组合：

```java
public class Logger {
    // 静态变量持有唯一实例
    private static final Logger INSTANCE = new Logger();

    // 私有构造：外部不能 new
    private Logger() {}

    // 静态方法返回实例
    public static Logger getInstance() {
        return INSTANCE;
    }

    public void log(String msg) {
        System.out.println("[LOG] " + msg);
    }

    public static void main(String[] args) {
        Logger l1 = Logger.getInstance();
        Logger l2 = Logger.getInstance();
        System.out.println(l1 == l2);   // true，同一个对象
        l1.log("系统启动");
    }
}
```

> 💡 单例模式在后续「设计模式」篇章会详细讲，这里只演示 static 的作用：静态变量持有实例 + 静态方法提供访问入口。

### 案例 6：初始化顺序面试题 ⭐⭐⭐

经典面试题，综合考查初始化顺序：

```java
class A {
    static {
        System.out.println("A static");
    }
    {
        System.out.println("A block");
    }
    public A() {
        System.out.println("A constructor");
    }
}

class B extends A {
    static {
        System.out.println("B static");
    }
    {
        System.out.println("B block");
    }
    public B() {
        System.out.println("B constructor");
    }
}

public class Test {
    public static void main(String[] args) {
        System.out.println("--- first new ---");
        new B();
        System.out.println("--- second new ---");
        new B();
    }
}
```

```
输出：
A static        ← 父类静态
B static        ← 子类静态
--- first new ---
A block         ← 父类构造块
A constructor   ← 父类构造方法
B block         ← 子类构造块
B constructor   ← 子类构造方法
--- second new ---
A block         ← 静态代码块不再执行
A constructor
B block
B constructor
```

> 📌 **答题套路**：先答「静态优先、父类优先、静态只一次」的口诀，再按「父静态→子静态→父构造块/构造→子构造块/构造」逐步写出，基本不会错。

### 案例 7：静态集合做全局缓存（含风险提示）⭐

```java
import java.util.concurrent.ConcurrentHashMap;

public class TokenCache {
    // 静态 Map 做全局缓存
    private static final ConcurrentHashMap<String, Long> tokenMap = new ConcurrentHashMap<>();
    // token -> 过期时间戳

    public static void put(String token, long expireTime) {
        tokenMap.put(token, expireTime);
    }

    public static boolean isValid(String token) {
        Long expire = tokenMap.get(token);
        if (expire == null) return false;
        if (System.currentTimeMillis() > expire) {
            tokenMap.remove(token);   // 过期清理
            return false;
        }
        return true;
    }

    // 定期清理过期 token（实际用定时任务）
    public static void cleanExpired() {
        long now = System.currentTimeMillis();
        tokenMap.entrySet().removeIf(e -> e.getValue() < now);
    }
}
```

> ⚠️ **风险**：静态 Map 不会自动释放，如果只 put 不 remove，内存会持续增长。实际开发用 Caffeine、Guava Cache 等带过期淘汰机制的缓存框架，不要手写静态 Map 当缓存。

---

## 🚀 新版本补充

### Java 9+：接口中的 private 静态方法

Java 8 允许接口有 `static` 方法，Java 9 进一步允许接口中有 `private static` 方法，供接口内部复用：

```java
// Java 9+
public interface Calculator {
    static int add(int a, int b) {
        return a + b;
    }

    // Java 9 新增：私有静态方法，供接口内部复用
    private static int log(int x) {
        return x;   // 内部辅助逻辑
    }
}
```

> 💡 Java 8 接口可以有 `static` 方法，但不能有 `private static`。本篇以 Java 8 为基准，了解 Java 9+ 的增强即可。

### Java 8：接口静态方法与默认方法

Java 8 开始接口可以定义 `static` 方法（属于接口，不可被继承）和 `default` 方法：

```java
public interface MathOperation {
    // 静态方法：属于接口，用接口名调用
    static int abs(int x) {
        return x < 0 ? -x : x;
    }

    // 默认方法：可被实现类继承/重写
    default int compute(int a, int b) {
        return a + b;
    }
}
// 调用：MathOperation.abs(-5)  → 5
```

> 💡 接口的 static 方法属于 Java 8 基准内容，但因为它和接口关系更紧密，放在后续接口篇章详讲。

### Java 15+：密封类对静态成员的影响预告

Java 15（预览）/17（正式）的密封类（`sealed`）会限制哪些类可以继承它，间接影响静态成员的「隐藏」行为。Java 8 环境不涉及，了解趋势即可。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| static 修饰变量 | 属于类，所有对象共享，类名访问 |
| static 修饰方法 | 类名调用，不能访问实例成员，没有 this |
| 静态方法限制 | 静态只能访问静态；不能 this/super |
| 静态代码块 | 类加载时执行一次，初始化静态变量 |
| 构造代码块 | 每次 new 前执行，实际开发很少用 |
| 局部代码块 | 方法内限定作用域，几乎不用 |
| 初始化顺序 | 父静态→子静态→父构造块/构造→子构造块/构造 |
| 静态导包 | `import static`，省略类名，慎用 |
| 工具类规范 | final 类 + 私有构造 + 全静态方法 |
| 静态变量风险 | 生命周期长，静态集合易内存泄漏 |

---

## 学习建议

1. **手写初始化顺序面试题**：把案例 6 的代码原样敲进 IDE 运行，对照输出逐行标注「为什么这行先执行」。再删掉某个静态块/构造块，预测并验证输出变化。这是 static 最值钱的练习。
2. **写一个完整的工具类**：照案例 3 写一个 `StringUtils` 或 `DateUtils`，包含私有构造、3-5 个静态方法、参数校验。体会「工具类不需要 new」的设计哲学。
3. **理解「静态只能访问静态」的根源**：不要死记规则，要问「为什么」。答案是「静态方法属于类，类加载时可能还没有对象」。想通这一点，所有限制都顺理成章。
4. **警惕 static 的滥用**：static 不是「方便访问」的工具，而是「逻辑上属于类」的成员。如果只是嫌 new 对象麻烦就加 static，会破坏面向对象设计，后续测试、多线程都会出问题。
5. **结合内存模型理解**：静态变量在方法区（JDK 8 后在堆的元数据区）、实例变量在堆的对象里——这个内存位置差异决定了它们的生命周期和共享性。回头复习 [02-JVM内存模型](02-JVM内存模型.md)，把 static 放进内存图里理解。
