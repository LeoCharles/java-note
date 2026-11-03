# Object 类与 Objects 工具类

`Object` 是 Java 中**所有类的根类**：每一个类都直接或间接继承自 `Object`，即使你没写 `extends Object`，编译器也会默认加上。这意味着 `Object` 中定义的方法，**任何 Java 对象都能调用**——`toString()`、`equals()`、`hashCode()`、`getClass()`、`clone()` 这些方法贯穿了整个 Java 开发生涯。理解它们，才能写出能正确打印、正确比较、正确放进集合的对象；不理解它们，就会踩「对象比较用 == 出 bug」「重写 equals 忘了重写 hashCode 导致 HashMap 丢数据」这类经典坑。

> 💡 在阅读本篇前，建议先看 [02-JVM内存模型](02-JVM内存模型.md)，理解「栈存引用、堆存对象」的内存模型，会更容易理解 `==` 比地址、`equals` 比内容的本质区别。

---

## 一、Object 类概述

### 1.1 所有类的根类

Java 的类继承体系最顶端就是 `Object`，位于 `java.lang` 包下（无需 import）。任何类都默认继承它：

```java
// 你写的类
public class Person {
    private String name;
}

// 等价于编译器自动补全
public class Person extends Object {
    private String name;
}
```

> 💡 **单继承的语言特性**：Java 只支持单继承（一个类只能有一个直接父类），但所有类最终都汇聚到 `Object` 这一个根上，形成一棵「类树」。`Object` 本身没有父类。

### 1.2 Object 的 11 个方法

`Object` 一共定义了 11 个方法（Java 8 视角），其中 9 个是普通方法，2 个是 `protected` 的 `clone` 和 `finalize`，还有 5 个 `final` 的线程相关方法（不可重写）：

| 方法签名 | 作用 | 可否重写 |
| :--- | :--- | :---: |
| `String toString()` | 返回对象的字符串表示 | ✅ 常重写 |
| `boolean equals(Object obj)` | 判断是否相等 | ✅ 常重写 |
| `int hashCode()` | 返回哈希值 | ✅ 常重写 |
| `Class<?> getClass()` | 返回运行时类对象 | ❌ final |
| `Object clone()` | 克隆对象 | ✅ 需实现 Cloneable |
| `void finalize()` | GC 回收前调用（已过时） | ✅ 但别重写 |
| `void wait()` | 线程等待 | ❌ final |
| `void wait(long timeout)` | 带超时的等待 | ❌ final |
| `void wait(long, int)` | 带纳秒精度的等待 | ❌ final |
| `void notify()` | 唤醒一个等待线程 | ❌ final |
| `void notifyAll()` | 唤醒所有等待线程 | ❌ final |

> 📌 **开发中高频接触的只有前 4 个**：`toString`、`equals`、`hashCode`、`getClass`。线程通信的 5 个方法留到多线程篇详讲，`finalize` 已过时不建议重写。

---

## 二、toString() 方法

### 2.1 默认实现：类名@十六进制地址

`Object` 的 `toString()` 默认返回 `类名@十六进制哈希码`，几乎没什么可读性：

```java
// Object 源码中的默认实现
public String toString() {
    return getClass().getName() + "@" + Integer.toHexString(hashCode());
}

public class Person {
    String name = "张三";
}

Person p = new Person();
System.out.println(p);            // Person@1540e19d
System.out.println(p.toString()); // Person@1540e19d，两者等价
```

> 💡 **直接打印对象会自动调用 toString()**：`System.out.println(p)` 等价于 `System.out.println(p.toString())`。这就是为什么打印数组得到 `[I@xxx`（数组没重写 toString），而打印 `ArrayList` 能得到 `[a, b, c]`（ArrayList 重写了 toString）。

### 2.2 重写 toString：返回对象内容

实际开发中，默认实现毫无意义，必须重写为「能看出对象里存了什么」的格式：

```java
public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    // ✅ 重写 toString，返回有意义的内容
    @Override
    public String toString() {
        return "Person{name='" + name + "', age=" + age + "}";
    }
}

Person p = new Person("张三", 20);
System.out.println(p);  // Person{name='张三', age=20}
```

### 2.3 IDEA 一键生成

手写 toString 太繁琐，IDEA 提供快捷生成：`Alt + Insert` → 选择 `toString()` → 勾选字段 → 完成。

```java
// IDEA 自动生成的标准格式
@Override
public String toString() {
    return "Person{" +
            "name='" + name + '\'' +
            ", age=" + age +
            '}';
}
```

> 📌 **开发规范**：每个实体类（POJO/DTO/Entity）都要重写 `toString()`。它在日志打印、调试、异常信息中无处不在——没有 toString，日志里全是 `User@1b6d3586`，排查问题寸步难行。

---

## 三、equals() 方法

### 3.1 默认实现：用 == 比地址

`Object` 的 `equals()` 默认就是 `==`，比较的是**内存地址**：

```java
// Object 源码中的默认实现
public boolean equals(Object obj) {
    return (this == obj);
}

public class Person {
    String name;
    public Person(String name) { this.name = name; }
}

Person p1 = new Person("张三");
Person p2 = new Person("张三");

System.out.println(p1 == p2);       // false，两个 new 是两个对象，地址不同
System.out.println(p1.equals(p2));  // false，默认 equals 就是 ==，还是比地址
```

### 3.2 重写 equals：比较内容

两个 `new Person("张三")` 在业务上应该是「同一个人」，但默认 equals 说它们不相等——这会导致集合去重、查找全部失效。必须重写为「按内容比较」：

```java
public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    // ✅ 重写 equals，按 name 和 age 比较内容
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;                          // 同一对象，直接 true
        if (o == null || getClass() != o.getClass()) return false; // null 或类型不同
        Person person = (Person) o;
        return age == person.age && name.equals(person.name); // 逐字段比较
    }

    public static void main(String[] args) {
        Person p1 = new Person("张三", 20);
        Person p2 = new Person("张三", 20);
        System.out.println(p1.equals(p2));  // true，内容相等
    }
}
```

### 3.3 equals 重写的五大规范

`equals` 重写不是随便写写，必须满足 JDK 文档规定的**自反性、对称性、传递性、一致性、null 处理**五条契约：

| 规范 | 含义 | 说明 |
| :--- | :--- | :--- |
| 自反性 | `x.equals(x)` 必须为 true | 自己等于自己 |
| 对称性 | `x.equals(y)` 为 true，则 `y.equals(x)` 必须为 true | 不能 A 认识 B 而 B 不认识 A |
| 传递性 | `x.equals(y)` 且 `y.equals(z)` 为 true，则 `x.equals(z)` 为 true | 相等关系可传递 |
| 一致性 | 多次调用 `x.equals(y)` 结果必须一致 | 只要对象未修改，结果不变 |
| null 处理 | `x.equals(null)` 必须为 false | 任何对象都不等于 null |

```java
// ❌ 违反对称性的反面教材
public class CaseInsensitiveString {
    private String value;
    public CaseInsensitiveString(String v) { this.value = v; }

    @Override
    public boolean equals(Object o) {
        if (o instanceof CaseInsensitiveString) {
            return value.equalsIgnoreCase(((CaseInsensitiveString) o).value);
        }
        if (o instanceof String) {  // ❌ 允许和 String 比较，埋下不对称的雷
            return value.equalsIgnoreCase((String) o);
        }
        return false;
    }
}

CaseInsensitiveString cis = new CaseInsensitiveString("Java");
String s = "java";
System.out.println(cis.equals(s));   // true
System.out.println(s.equals(cis));   // false！String 的 equals 区分大小写
// cis.equals(s) 为 true，但 s.equals(cis) 为 false —— 对称性被破坏
```

> ⚠️ **重写 equals 的标准模板**（IDEA 生成的就是这个套路）：
> 1. `if (this == o) return true;` —— 优化：同一对象直接返回
> 2. `if (o == null || getClass() != o.getClass()) return false;` —— null 处理 + 类型检查
> 3. 强转后逐字段比较（基本类型用 `==`，引用类型用 `Objects.equals`）

### 3.4 用 instanceof 还是 getClass

类型检查有两种写法，各有取舍：

```java
// 写法 A：getClass（严格类型，不允许子类与父类相等）
if (o == null || getClass() != o.getClass()) return false;

// 写法 B：instanceof（允许子类与父类相等，但有对称性风险）
if (!(o instanceof Person)) return false;
```

| 写法 | 特点 | 适用场景 |
| :--- | :--- | :--- |
| `getClass() != o.getClass()` | 严格：父类和子类永远不等 | 大多数业务实体类 |
| `o instanceof X` | 宽松：子类可被当作父类比较 | 有继承关系且需多态比较时 |

> 📌 **Effective Java 建议**：优先用 `getClass()` 严格判断，避免子类破坏对称性。除非确实需要「父类 equals 子类」的多态语义（如时间日期类），才用 `instanceof`。

---

## 四、hashCode() 方法

### 4.1 与 equals 的契约

`hashCode` 返回一个 int 哈希值，它和 `equals` 之间有**严格的契约关系**：

| 契约 | 说明 |
| :--- | :--- |
| 一致性 1 | `equals` 相等的两个对象，`hashCode` **必须**相等 |
| 一致性 2 | `equals` 不等的两个对象，`hashCode` **可以**相等（哈希冲突），也可以不等 |

> ⚠️ **最致命的坑**：重写了 `equals` 却不重写 `hashCode`，会导致 `HashMap`、`HashSet` 找不到本应相等的对象！

```java
public class Person {
    private String name;
    private int age;
    // 构造方法省略

    // ✅ 重写了 equals
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Person person = (Person) o;
        return age == person.age && name.equals(person.name);
    }
    // ❌ 没重写 hashCode！
}

Person p1 = new Person("张三", 20);
Person p2 = new Person("张三", 20);
System.out.println(p1.equals(p2));  // true

// 灾难来了
java.util.HashSet<Person> set = new java.util.HashSet<>();
set.add(p1);
System.out.println(set.contains(p2));  // false！明明相等却查不到
// 原因：p1.hashCode() 和 p2.hashCode() 不同（Object 默认按地址算）
// HashSet 先按 hashCode 找桶，找不到就认为不存在
```

### 4.2 为什么重写 equals 必须重写 hashCode

`HashMap`、`HashSet` 的查找逻辑是「**先比 hashCode，再比 equals**」：

```
查找流程：
1. 先算 key.hashCode()，定位到数组中的某个桶（bucket）
2. 桶里若没有元素 → 不存在
3. 桶里有元素 → 再用 equals 逐个比较
```

如果两个 `equals` 相等的对象 `hashCode` 不同，它们会被分到**不同的桶**，第 2 步就直接判「不存在」了，根本走不到 equals 这一步。

### 4.3 标准重写模板

IDEA `Alt+Insert` → `equals() and hashCode()` 一键生成。手写的话，核心思想是「把参与 equals 的每个字段算出一个哈希，再组合」：

```java
@Override
public int hashCode() {
    int result = name != null ? name.hashCode() : 0;  // String 的 hashCode
    result = 31 * result + age;                       // 31 是个质数，减少冲突
    return result;
}

// 或者用 Objects.hash（更简洁，Java 7+）
@Override
public int hashCode() {
    return java.util.Objects.hash(name, age);
}
```

> 💡 **为什么是 31？** 它是一个奇质数，且 `31 * i == (i << 5) - i`，JVM 会自动优化成位移运算，性能好。如果用偶数，乘法左移会丢低位信息，容易冲突。

---

## 五、getClass() 方法

`getClass()` 返回对象的**运行时类**（`Class` 对象），是 `final` 方法，不可重写。常用于反射、类型判断：

```java
public class Animal {}
public class Dog extends Animal {}

Animal a = new Dog();   // 父类引用指向子类对象
System.out.println(a.getClass().getName());  // Dog，返回的是实际类型
System.out.println(a instanceof Animal);     // true
System.out.println(a instanceof Dog);        // true

// 对比：getClass 比 instanceof 更严格
Animal a2 = new Animal();
System.out.println(a.getClass() == a2.getClass());  // false，Dog != Animal
System.out.println(a2 instanceof Dog);              // false，Animal 不是 Dog
```

> 💡 `getClass()` 返回的是**运行时实际类型**，不受声明类型影响。在 `equals` 中用 `getClass() != o.getClass()` 可以严格区分父子类型。

---

## 六、clone() 方法

### 6.1 浅拷贝

`clone()` 用于创建对象的副本。默认是**浅拷贝**：基本类型复制值，引用类型只复制地址（新旧对象共享同一个内部引用对象）。

```java
public class Address {
    String city;
    public Address(String city) { this.city = city; }
}

public class Person implements Cloneable {  // 必须实现 Cloneable 标记接口
    String name;
    Address address;  // 引用类型字段

    public Person(String name, Address address) {
        this.name = name;
        this.address = address;
    }

    @Override
    protected Object clone() throws CloneNotSupportedException {
        return super.clone();  // Object 的默认浅拷贝
    }

    public static void main(String[] args) throws Exception {
        Person p1 = new Person("张三", new Address("北京"));
        Person p2 = (Person) p1.clone();

        System.out.println(p1 == p2);                  // false，两个对象
        System.out.println(p1.address == p2.address);  // true！共享同一个 Address
        p2.address.city = "上海";
        System.out.println(p1.address.city);  // 上海 —— p1 的地址被改了！
    }
}
```

> ⚠️ **浅拷贝的陷阱**：引用类型字段不会真正复制，新旧对象共享内部对象。改一个，另一个跟着变——这在订单包含商品列表、用户包含地址等场景下极其危险。

### 6.2 深拷贝

深拷贝要求**所有引用类型也递归复制**，实现方式有两种：

```java
// 方式一：手动递归 clone
public class Person implements Cloneable {
    String name;
    Address address;

    @Override
    protected Object clone() throws CloneNotSupportedException {
        Person p = (Person) super.clone();     // 先浅拷贝
        p.address = (Address) address.clone(); // 再把引用字段也克隆一份
        return p;
    }
}

// 方式二：序列化（推荐，更通用）
// 通过 Serializable 把对象转成字节流再读回来，天然深拷贝
```

> 📌 **开发规范**：实际项目中**几乎不用 `clone()`**，它设计上有缺陷（要实现标记接口、要处理异常、浅拷贝易出 bug）。深拷贝优先用**序列化**（如 JSON 序列化往返、`Serializable` + `ObjectOutputStream`），或直接 `new` 一个新对象手动赋值。

### 6.3 Cloneable 标记接口

`Cloneable` 是一个**标记接口**（marker interface），里面没有任何方法，只是用来「标记」这个类允许被 clone。不实现它直接调 `clone()` 会抛 `CloneNotSupportedException`：

```java
public class Person {}  // 没实现 Cloneable
Person p = new Person();
p.clone();  // ❌ CloneNotSupportedException
```

> 💡 标记接口是 Java 早期的一种设计模式，类似 `Serializable`、`RandomAccess`，靠 `instanceof` 判断能力，没有强制方法约束。现代开发更倾向用注解。

---

## 七、finalize() 方法（已过时）

`finalize()` 在对象被 GC 回收前由 JVM 调用，原本用于释放资源。但它**严重不可靠**，Java 9 已标记 `@Deprecated`，Java 18 开始标记为 `Deprecated for removal`：

```java
@Override
protected void finalize() throws Throwable {
    // ❌ 不要依赖它做资源释放
    // 1. 不保证执行（JVM 退出时可能不调）
    // 2. 执行时间不确定（GC 时机不可控）
    // 3. 可能导致对象"复活"
    // 4. 性能差，GC 延迟可达数百倍
    super.finalize();
}
```

> ⚠️ **替代方案**：资源释放用 `try-with-resources`（实现 `AutoCloseable`），不要用 `finalize`。Java 9+ 用 `Cleaner` 类（`java.lang.ref.Cleaner`）替代 finalizer，更安全。

---

## 八、wait/notify/notifyAll（线程通信）

这 5 个方法定义在 `Object` 上而非 `Thread` 上，因为**任意对象都可以作为锁**。它们是 `final` 的，不可重写：

```java
public class WaitNotifyDemo {
    public static void main(String[] args) {
        final Object lock = new Object();
        new Thread(() -> {
            synchronized (lock) {
                try {
                    System.out.println("等待中...");
                    lock.wait();  // 释放锁，进入等待，直到被 notify 唤醒
                    System.out.println("被唤醒了");
                } catch (InterruptedException e) { }
            }
        }).start();

        try { Thread.sleep(1000); } catch (Exception e) { }
        synchronized (lock) {
            lock.notify();  // 唤醒一个在 lock 上等待的线程
            System.out.println("已发送唤醒信号");
        }
    }
}
```

> 💡 这三个方法**必须在 `synchronized` 块内调用**，否则抛 `IllegalMonitorStateException`。`wait` 会释放锁、线程阻塞；`notify` 唤醒一个等待线程但不立即释放锁（要等 synchronized 块结束）。详细原理留到多线程篇。

---

## 九、java.util.Objects 工具类

`java.util.Objects`（注意带 s，是工具类，Java 7+ 引入）提供了一组**空指针安全**的静态方法，弥补了 `Object` 的不足。

### 9.1 Objects.equals：防空指针

`Objects.equals(a, b)` 内部做了 null 检查，避免手动写 `a != null && a.equals(b)` 的繁琐：

```java
String a = null;
String b = "hello";

// ❌ 直接调 equals 可能 NPE
// boolean r = a.equals(b);  // NullPointerException

// ✅ 旧写法：先判空
boolean r1 = (a != null) && a.equals(b);  // false

// ✅ Objects.equals：一行搞定
boolean r2 = java.util.Objects.equals(a, b);  // false，不抛异常
```

看一眼源码，逻辑非常清晰：

```java
// Objects.equals 源码
public static boolean equals(Object a, Object b) {
    return (a == b) || (a != null && a.equals(b));
}
```

> 📌 **开发规范**：比较两个对象内容时，优先用 `Objects.equals(a, b)` 而非 `a.equals(b)`，尤其当对象可能为 null 时。它可读性高、且天然防 NPE。

### 9.2 requireNonNull：参数校验

`Objects.requireNonNull(obj)` 用于方法入口校验参数非空，为 null 直接抛 `NullPointerException`，比手动 `if + throw` 更简洁：

```java
public class UserService {
    public void process(User user) {
        // ✅ 旧写法
        // if (user == null) throw new NullPointerException("user");

        // ✅ Objects.requireNonNull
        java.util.Objects.requireNonNull(user, "user 不能为 null");
        // 后续逻辑可以放心用 user，不用处处判空
    }
}

// 三个重载
Objects.requireNonNull(obj);                    // 抛 NPE，无消息
Objects.requireNonNull(obj, "错误信息");        // 抛 NPE 带消息
Objects.requireNonNull(obj, () -> "懒加载消息"); // Supplier 延迟构造消息（省性能）
```

> 💡 `requireNonNull` 是 Java 8 函数式编程的好搭档——`Stream`、`Optional` 内部大量用它做非空校验。它让「契约式编程」的参数校验变得优雅。

### 9.3 isNull / nonNull

`isNull` 和 `nonNull` 是 `!= null` / `== null` 的语义化封装，在 Stream 的 filter 中特别好用：

```java
String s = null;
System.out.println(Objects.isNull(s));   // true，等价于 s == null
System.out.println(Objects.nonNull(s));  // false，等价于 s != null

// 在 Stream 中作为方法引用使用，非常简洁
java.util.List<String> list = java.util.Arrays.asList("a", null, "b", null, "c");
long count = list.stream().filter(Objects::nonNull).count();  // 3
```

### 9.4 其他常用方法

```java
// toString 防空指针
String s = null;
System.out.println(Objects.toString(s));         // "null"，不抛异常
System.out.println(Objects.toString(s, "默认值")); // "默认值"

// hashCode 防空指针
int h = Objects.hashCode(s);  // 0（s 为 null 时返回 0，不抛异常）

// hash：组合多个字段算哈希（用于重写 hashCode）
int code = Objects.hash("张三", 20);  // 组合多字段
```

---

## ⚠️ 重点

### 重点 1：== 与 equals 的区别 ⭐⭐

这是 Java 面试**必考题**，也是新手最容易踩的坑：

```java
String s1 = "hello";
String s2 = "hello";
String s3 = new String("hello");

System.out.println(s1 == s2);        // true，常量池同一对象
System.out.println(s1 == s3);        // false，new 出来的在堆，地址不同
System.out.println(s1.equals(s3));   // true，内容相同
```

| 比较方式 | 比较内容 | 适用场景 |
| :--- | :--- | :--- |
| `==` | 基本类型比值；引用类型比**内存地址** | 判断是否为同一对象 |
| `equals` | 默认也比地址（Object 默认实现）；**重写后比内容** | 判断内容是否相等 |

> ⚠️ **核心结论**：
> - **基本类型**（int/double/char...）用 `==` 比较值
> - **引用类型**（String/自定义类...）用 `equals` 比较内容
> - `equals` 没重写时和 `==` 一样比地址——所以**自定义类必须重写 equals**
> - `String`、`Integer` 等常用类已重写 equals，可直接用

### 重点 2：重写 equals 必须重写 hashCode ⭐⭐

```java
// ❌ 只重写 equals，没重写 hashCode
Person p1 = new Person("张三", 20);
Person p2 = new Person("张三", 20);
System.out.println(p1.equals(p2));  // true

java.util.HashMap<Person, String> map = new java.util.HashMap<>();
map.put(p1, "VIP");
System.out.println(map.get(p2));  // null！查不到
// p1.hashCode 和 p2.hashCode 不同，被分到不同桶，永远找不到
```

> 📌 **铁律**：`equals` 相等的对象必须 `hashCode` 相等。重写 `equals` 时，IDEA 会强制提示同时生成 `hashCode`，**两个一起重写，缺一不可**。

### 重点 3：Objects.equals 防空指针 ⭐

```java
String a = null;
String b = "hello";

// ❌ 危险：a 可能为 null
boolean r1 = a.equals(b);  // NullPointerException

// ✅ 安全：Objects.equals 内部判空
boolean r2 = java.util.Objects.equals(a, b);  // false
```

> 💡 **养成习惯**：任何可能为 null 的对象比较，都用 `Objects.equals`。它一行代码消除 NPE 风险，可读性也比 `a != null && a.equals(b)` 强。

### 重点 4：toString 必须重写 ⭐

```java
// ❌ 没重写 toString
System.out.println(user);  // User@1b6d3586，日志里全是这种鬼东西

// ✅ 重写后
System.out.println(user);  // User{id=1001, name='张三', phone='138****8888'}
```

> 📌 实体类（POJO/DTO/Entity/VO）一律重写 toString。日志排查、单元测试断言、调试打印都依赖它。

### 重点 5：浅拷贝 vs 深拷贝 ⭐

```java
// 浅拷贝：引用字段共享
Person p2 = (Person) p1.clone();
p2.address.city = "上海";
System.out.println(p1.address.city);  // 上海，p1 被牵连

// 深拷贝：引用字段也复制
Person p3 = deepCopy(p1);
p3.address.city = "广州";
System.out.println(p1.address.city);  // 不受影响
```

> ⚠️ 默认 `clone()` 是浅拷贝，引用类型字段会共享。涉及嵌套对象时必须手动深拷贝，否则改副本会污染原对象。

### 重点 6：getClass 返回运行时类型 ⭐

```java
Animal a = new Dog();
System.out.println(a.getClass().getName());  // Dog（实际类型），不是 Animal
```

> 💡 `getClass()` 返回的是 `new` 出来的实际类，不受声明类型 `Animal` 影响。在 `equals` 中用它做严格类型判断比 `instanceof` 更安全。

---

## 💻 实战案例

### 案例 1：重写 User 的 toString/equals/hashCode ⭐⭐

电商后台的 User 实体类，IDEA `Alt+Insert` 一键生成的标准三件套：

```java
import java.util.Objects;

public class User {
    private Long id;          // 用户 ID
    private String username;  // 用户名
    private String phone;     // 手机号
    private Integer age;

    public User(Long id, String username, String phone, Integer age) {
        this.id = id;
        this.username = username;
        this.phone = phone;
        this.age = age;
    }

    // ✅ 重写 toString
    @Override
    public String toString() {
        return "User{" +
                "id=" + id +
                ", username='" + username + '\'' +
                ", phone='" + phone + '\'' +
                ", age=" + age +
                '}';
    }

    // ✅ 重写 equals：按 id 判断同一用户（业务主键）
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return Objects.equals(id, user.id) &&
               Objects.equals(username, user.username);
    }

    // ✅ 重写 hashCode：与 equals 用相同的字段
    @Override
    public int hashCode() {
        return Objects.hash(id, username);
    }

    public static void main(String[] args) {
        User u1 = new User(1001L, "zhangsan", "13800001111", 25);
        User u2 = new User(1001L, "zhangsan", "13900002222", 25);
        // phone 不同，但 equals 只比 id + username
        System.out.println(u1.equals(u2));  // true

        java.util.HashSet<User> set = new java.util.HashSet<>();
        set.add(u1);
        System.out.println(set.contains(u2));  // true，hashCode 一致才能找到
    }
}
```

> 📌 **业务主键原则**：`equals`/`hashCode` 应基于**业务主键**（如 id）而非全部字段。这样从 DB 查出的同一用户（其他字段可能不同）仍能判等，放进 Set 能正确去重。

### 案例 2：Objects.equals 避免空指针 ⭐⭐

金融系统中，比较两个可能为 null 的账户号：

```java
import java.util.Objects;

public class AccountCompare {
    // ❌ 危险写法：参数可能为 null
    public static boolean sameAccountBad(String a1, String a2) {
        return a1.equals(a2);  // a1 为 null 时 NPE
    }

    // ✅ 安全写法：Objects.equals
    public static boolean sameAccountGood(String a1, String a2) {
        return Objects.equals(a1, a2);  // 任一为 null 都不抛异常
    }

    public static void main(String[] args) {
        String accountA = "6228480012345678";
        String accountB = null;  // 从外部系统取到的空值

        // System.out.println(sameAccountBad(accountB, accountA));  // ❌ NPE
        System.out.println(sameAccountGood(accountB, accountA));  // false，安全
        System.out.println(sameAccountGood(null, null));          // true
    }
}
```

> 💡 对接外部系统（HTTP/RPC）时，返回值随时可能为 null。所有对象比较一律走 `Objects.equals`，是防御性编程的基本素养。

### 案例 3：实体类比较与集合去重 ⭐

后台系统中，对订单列表按订单号去重：

```java
import java.util.*;
import java.util.Objects;

public class Order {
    private String orderNo;   // 订单号（业务主键）
    private Double amount;
    private String status;

    public Order(String orderNo, Double amount, String status) {
        this.orderNo = orderNo;
        this.amount = amount;
        this.status = status;
    }

    // 只按 orderNo 判等
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Order order = (Order) o;
        return Objects.equals(orderNo, order.orderNo);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(orderNo);
    }

    @Override
    public String toString() {
        return "Order{" + orderNo + ", " + amount + "元, " + status + "}";
    }

    public static void main(String[] args) {
        List<Order> orders = Arrays.asList(
            new Order("NO20240101", 199.0, "PAID"),
            new Order("NO20240102", 88.0, "UNPAID"),
            new Order("NO20240101", 199.0, "PAID"),  // 重复订单
            new Order("NO20240103", 299.0, "PAID")
        );

        // 用 HashSet 去重（依赖 equals + hashCode）
        Set<Order> unique = new HashSet<>(orders);
        for (Order o : unique) {
            System.out.println(o);
        }
        // 输出 3 条，NO20240101 只保留一条
    }
}
```

> ⚠️ 如果没重写 `equals`/`hashCode`，`HashSet` 会用地址判等，4 条全保留，去重失效。这是实际开发中「集合去重不生效」的头号原因。

### 案例 4：深拷贝订单对象 ⭐

电商系统中，复制一个订单做修改，不能影响原订单：

```java
import java.util.ArrayList;
import java.util.List;

class Product {
    String name;
    double price;

    public Product(String name, double price) {
        this.name = name;
        this.price = price;
    }
    // 深拷贝构造方法
    public Product(Product p) {
        this.name = p.name;
        this.price = p.price;
    }
    @Override
    public String toString() {
        return name + "(" + price + ")";
    }
}

class Order implements Cloneable {
    String orderNo;
    List<Product> products = new ArrayList<>();

    public Order(String orderNo) { this.orderNo = orderNo; }
    public void addProduct(Product p) { products.add(p); }

    // 浅拷贝
    public Order shallowCopy() {
        Order copy = new Order(this.orderNo);
        copy.products = this.products;  // ❌ 共享同一个 List
        return copy;
    }

    // 深拷贝：List 和每个 Product 都复制
    public Order deepCopy() {
        Order copy = new Order(this.orderNo);
        for (Product p : this.products) {
            copy.products.add(new Product(p));  // 每个 Product 也新建
        }
        return copy;
    }

    @Override
    public String toString() {
        return orderNo + products;
    }

    public static void main(String[] args) {
        Order original = new Order("NO20240101");
        original.addProduct(new Product("手机", 2999));
        original.addProduct(new Product("耳机", 199));

        // 浅拷贝的灾难
        Order shallow = original.shallowCopy();
        shallow.products.get(0).price = 0.01;  // 改副本
        System.out.println(original);  // 原订单的手机也变 0.01 了！

        // 深拷贝的安全
        Order original2 = new Order("NO20240102");
        original2.addProduct(new Product("电脑", 5999));
        Order deep = original2.deepCopy();
        deep.products.get(0).price = 0.01;
        System.out.println(original2);  // 电脑还是 5999，不受影响
    }
}
```

> 📌 **开发规范**：涉及嵌套对象（订单含商品列表、用户含地址）的复制，必须用深拷贝。最稳妥的方式是**序列化往返**（如 Jackson 转 JSON 再转回对象），或用拷贝构造方法逐层 new。

### 案例 5：requireNonNull 做参数校验 ⭐

后台 Service 层方法入口校验参数：

```java
import java.util.Objects;

public class OrderService {
    // ❌ 旧写法：手动判空
    public void createOrderBad(Order order) {
        if (order == null) {
            throw new IllegalArgumentException("订单不能为空");
        }
        if (order.getOrderNo() == null) {
            throw new IllegalArgumentException("订单号不能为空");
        }
        // ... 业务逻辑
    }

    // ✅ 新写法：requireNonNull 简洁
    public void createOrderGood(Order order) {
        Objects.requireNonNull(order, "订单不能为空");
        Objects.requireNonNull(order.getOrderNo(), "订单号不能为空");
        // 后续放心用，不用处处判空
        System.out.println("创建订单：" + order.getOrderNo());
    }

    public static void main(String[] args) {
        OrderService service = new OrderService();
        try {
            service.createOrderGood(null);  // 抛 NPE：订单不能为空
        } catch (NullPointerException e) {
            System.out.println("校验拦截：" + e.getMessage());
        }
    }
}

class Order {
    private String orderNo;
    public Order(String orderNo) { this.orderNo = orderNo; }
    public String getOrderNo() { return orderNo; }
}
```

> 💡 `requireNonNull` 让「快速失败」更优雅。Spring 等框架的 `@NonNull` 注解底层也是类似思路——尽早暴露问题，而不是让 null 一路传到深处才爆 NPE。

### 案例 6：打印日志时 toString 的价值 ⭐

模拟后台系统打印用户操作日志：

```java
import java.util.Objects;

public class LogDemo {
    static class User {
        Long id;
        String name;
        public User(Long id, String name) { this.id = id; this.name = name; }

        // 不重写 toString 的情况：注释掉这个方法试试
        @Override
        public String toString() {
            return "User[id=" + id + ", name=" + name + "]";
        }
    }

    public static void main(String[] args) {
        User user = new User(1001L, "张三");

        // ✅ 重写了 toString，日志清晰
        System.out.println("[INFO] 用户登录: " + user);
        // [INFO] 用户登录: User[id=1001, name=张三]

        // ❌ 若不重写 toString
        // [INFO] 用户登录: LogDemo$User@1b6d3586  —— 排查问题看不懂
    }
}
```

> 📌 日志是排查线上问题的第一现场。`toString` 重写得好，日志一目了然；不重写，日志全是地址哈希，等于没打。

---

## 🚀 新版本补充

### Java 9：finalize() 标记 @Deprecated

Java 9 起 `Object.finalize()` 被标记为 `@Deprecated`，Java 18 进一步标记 `Deprecated(forRemoval=true)`，未来版本将移除：

```java
// ❌ Java 9+ 不再推荐
@Override
protected void finalize() throws Throwable { ... }

// ✅ 替代方案：Cleaner（Java 9+）
import java.lang.ref.Cleaner;
// Cleaner 在对象被回收时回调，更安全、不阻塞 GC
```

### Java 16：record 类自动生成 equals/hashCode/toString

Java 16 正式发布 `record`，自动生成 `equals`、`hashCode`、`toString`，无需手写：

```java
// Java 16+ record，一行搞定实体类
public record User(Long id, String name, String phone) {}

User u1 = new User(1L, "张三", "13800001111");
User u2 = new User(1L, "张三", "13900002222");
System.out.println(u1.equals(u2));  // true，自动按所有字段判等
System.out.println(u1);             // User[id=1, name=张三, phone=13800001111]
System.out.println(u1.hashCode());  // 自动生成
```

> 💡 `record` 是不可变数据载体的最佳选择，Java 8 环境下不可用，但它是未来趋势。Lombok 的 `@Data` 注解在 Java 8 下能起到类似效果（编译期生成 equals/hashCode/toString）。

### Java 19+：Thread.ofVirtual 与对象锁（补充了解）

虚拟线程（Java 21 正式）让 `wait/notify` 的使用场景发生变化——虚拟线程下 `synchronized` 的 monitor 可能 pin 平台线程，官方建议用 `ReentrantLock` 替代。这属于多线程篇范畴，此处仅提及。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Object 地位 | 所有类的根类，默认继承，11 个方法 |
| toString() | 默认返回 类名@哈希，重写后返回内容，IDEA Alt+Insert 生成 |
| equals() | 默认用 == 比地址，重写后比内容；需满足五大规范 |
| hashCode() | 与 equals 契约：equals 相等则 hashCode 必须相等 |
| getClass() | 返回运行时实际类型，final 不可重写 |
| clone() | 默认浅拷贝，深拷贝需递归克隆或序列化 |
| Cloneable | 标记接口，无方法，不实现就 clone 抛异常 |
| finalize() | 已过时（Java 9+ Deprecated），用 try-with-resources 替代 |
| wait/notify | 线程通信，必须在 synchronized 块内调用 |
| Objects 工具类 | equals 防空指针、requireNonNull 校验、isNull/nonNull |
| == vs equals | == 比地址，equals 重写后比内容；基本类型用 ==，引用用 equals |

---

## 学习建议

1. **把 == 和 equals 的区别刻进 DNA**：这是 Java 最基础也最常考的知识点。记住口诀「基本类型用 ==，引用类型用 equals」，再理解 String 已重写 equals、自定义类必须自己重写。把本篇重点 1 的代码敲一遍，亲眼看 `s1 == s3` 为 false 而 `s1.equals(s3)` 为 true。
2. **equals 和 hashCode 永远成对重写**：只重写一个等于没重写——HashSet/HashMap 会丢数据。用 IDEA 的 `Alt+Insert → equals() and hashCode()` 一次性生成，绝不要只写一个。理解「先比 hashCode 定桶，再比 equals 定元素」的查找流程。
3. **用 Objects.equals 替代手写判空比较**：凡是可能为 null 的对象比较，一律 `Objects.equals(a, b)`，告别 NPE。同时掌握 `requireNonNull` 做方法入口校验，这是防御性编程的基本功。
4. **每个实体类都重写 toString**：不要让日志里出现 `User@1b6d3586`。toString 是排查问题的第一手信息，IDEA 一键生成，成本极低，收益极大。
5. **深拷贝优先用序列化而非 clone**：`clone()` 设计有缺陷，浅拷贝坑多。理解浅拷贝「引用字段共享」的危害，实际项目用 JSON 序列化往返或拷贝构造方法，更安全也更易读。
