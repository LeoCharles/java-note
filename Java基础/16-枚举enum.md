# 枚举 enum

在没学枚举之前，表示「状态」通常用 `public static final int` 常量；有了**枚举（enum）**，一组有限的常量值有了自己的类型，编译器能帮你检查传参对不对、避免写错状态值。枚举的本质是一个继承自 `java.lang.Enum` 的 final 类，它天生线程安全、天生单例，是 Java 中实现常量集合、状态机、策略分发的首选工具。

> 💡 在阅读本篇前，建议先回顾 [10-面向对象基础](10-面向对象基础.md) 中「类与对象」的概念，枚举本质上就是一种特殊的类。

---

## 一、枚举的由来

### 1.1 静态常量的痛点

没有枚举之前，表示一组固定值用 `public static final` 常量：

```java
// ❌ 老写法：用 int 常量表示订单状态
public class OrderStatus {
    public static final int PENDING = 1;     // 待支付
    public static final int PAID = 2;        // 已支付
    public static final int SHIPPED = 3;     // 已发货
    public static final int COMPLETED = 4;   // 已完成
    public static final int CANCELLED = 5;   // 已取消
}

class OrderService {
    public void process(int status) {
        // ⚠️ 传参没有类型约束，传个 99 或 -1 编译器也不报错
        if (status == OrderStatus.PAID) { }
    }
}

class Test {
    public static void main(String[] args) {
        new OrderService().process(99);    // ❌ 编译通过，但 99 根本不是合法状态
        new OrderService().process(0);    // ❌ 同样编译通过
    }
}
```

这种 int 常量有三大问题：

1. **无类型安全**：传任何 int 都能编译，运行时才暴露错误
2. **无命名空间**：每个常量都要手动加前缀，容易重名
3. **无行为**：常量只是个数字，无法携带描述信息或逻辑

### 1.2 枚举的登场

```java
// ✅ 枚举写法
public enum OrderStatus {
    PENDING, PAID, SHIPPED, COMPLETED, CANCELLED
}

class OrderService {
    public void process(OrderStatus status) {   // 参数是枚举类型
        if (status == OrderStatus.PAID) { }
    }
}

class Test {
    public static void main(String[] args) {
        new OrderService().process(OrderStatus.PAID);        // ✅
        // new OrderService().process(99);                  // ❌ 编译错误，类型不匹配
        // new OrderService().process(OrderStatus.OTHER);   // ❌ 编译错误，无此枚举值
    }
}
```

> 💡 枚举把「一组固定值」变成一个**类型**，编译期就能拦截非法值，这是它最大的价值。

---

## 二、enum 关键字定义枚举

### 2.1 最简枚举

```java
public enum Color {
    RED, GREEN, BLUE     // 枚举常量，用逗号分隔，全大写命名
}
```

使用：

```java
Color c = Color.RED;
System.out.println(c);           // RED
System.out.println(c == Color.RED);  // true，枚举可用 == 比较
```

> 💡 枚举常量命名规范：全大写，下划线分隔（如 `WAITING_PAY`），与普通常量一致。

### 2.2 枚举的本质

枚举看似简单，实则编译器做了很多事。`enum` 关键字定义的枚举，本质是一个**继承自 `java.lang.Enum` 的 final 类**：

```java
// 你写的
public enum Color { RED, GREEN, BLUE }

// 编译器大致生成的等价代码
public final class Color extends java.lang.Enum<Color> {
    public static final Color RED = new Color("RED", 0);
    public static final Color GREEN = new Color("GREEN", 1);
    public static final Color BLUE = new Color("BLUE", 2);

    private Color(String name, int ordinal) { super(name, ordinal); }
    public static Color[] values() { ... }
    public static Color valueOf(String name) { ... }
}
```

关键点：

- 枚举类是 **final** 的，**不能被继承**
- 每个枚举常量是类的**静态 final 实例**，在类加载时创建
- 构造方法是**私有**的，外部无法 `new`
- 继承自 `java.lang.Enum`，不能再继承别的类（但可实现接口）

> ⚠️ 枚举不能 `new`：`new Color()` 会编译错误。枚举实例由 JVM 在类加载时创建，你只能用已有的几个。

---

## 三、枚举常用方法

枚举继承自 `java.lang.Enum`，自带一套实用方法：

| 方法 | 作用 | 示例 |
| :--- | :--- | :--- |
| `values()` | 返回所有枚举值数组 | `Color[] cs = Color.values()` |
| `valueOf(String)` | 字符串转枚举（精确匹配名称） | `Color c = Color.valueOf("RED")` |
| `name()` | 返回枚举常量名称 | `Color.RED.name()` → `"RED"` |
| `ordinal()` | 返回声明顺序索引（从 0 开始） | `Color.RED.ordinal()` → `0` |
| `toString()` | 默认同 `name()`，可重写 | — |

```java
public enum OrderStatus {
    PENDING, PAID, SHIPPED, COMPLETED, CANCELLED
}

class TestEnum {
    public static void main(String[] args) {
        // values()：遍历所有枚举值
        for (OrderStatus s : OrderStatus.values()) {
            System.out.println(s.name() + " = " + s.ordinal());
            // PENDING = 0
            // PAID = 1
            // ...
        }

        // valueOf：字符串转枚举
        OrderStatus s = OrderStatus.valueOf("PAID");   // ✅
        // OrderStatus bad = OrderStatus.valueOf("PAID2"); // ❌ 运行时抛 IllegalArgumentException

        // name() 与 ordinal()
        System.out.println(OrderStatus.SHIPPED.name());     // SHIPPED
        System.out.println(OrderStatus.SHIPPED.ordinal());  // 2
    }
}
```

> ⚠️ **ordinal() 不要用于业务逻辑**！它依赖声明顺序，一旦调整枚举常量顺序，ordinal 就变了，会导致数据错乱。业务里用自定义 `code` 字段（见下文）。

> ⚠️ **valueOf 对大小写敏感**，且字符串必须精确匹配枚举名，否则抛 `IllegalArgumentException`。生产代码要 try-catch 或先校验。

---

## 四、枚举的属性与方法

枚举可以有自己的字段、构造方法、普通方法，让每个常量携带更多信息。

### 4.1 带属性的枚举

```java
public enum OrderStatus {
    // 枚举常量，必须放在第一行；括号内传参给构造方法
    PENDING(1, "待支付"),
    PAID(2, "已支付"),
    SHIPPED(3, "已发货"),
    COMPLETED(4, "已完成"),
    CANCELLED(5, "已取消");

    private final int code;          // 状态码（存数据库用）
    private final String desc;       // 中文描述（显示用）

    // 构造方法：默认就是 private，写 public 会报错
    OrderStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public int getCode() { return code; }
    public String getDesc() { return desc; }
}
```

```java
class Test {
    public static void main(String[] args) {
        OrderStatus s = OrderStatus.PAID;
        System.out.println(s.getCode());   // 2
        System.out.println(s.getDesc());   // 已支付

        // 通过 code 反查枚举（开发常用）
        OrderStatus fromDb = OrderStatus.fromCode(2);
        System.out.println(fromDb);        // PAID
    }
}
```

> 📌 **开发规范**：枚举常量带 `code` 字段，数据库存 code 而非 ordinal 或 name。name 改了影响小，ordinal 改了灾难，code 自主可控。

补充一个常用的 `fromCode` 反查方法：

```java
public enum OrderStatus {
    PENDING(1, "待支付"), PAID(2, "已支付"), SHIPPED(3, "已发货"),
    COMPLETED(4, "已完成"), CANCELLED(5, "已取消");

    private final int code;
    private final String desc;

    OrderStatus(int code, String desc) { this.code = code; this.desc = desc; }
    public int getCode() { return code; }
    public String getDesc() { return desc; }

    // 通过 code 反查枚举，找不到返回 null（或抛异常，看业务）
    public static OrderStatus fromCode(int code) {
        for (OrderStatus s : values()) {
            if (s.code == code) return s;
        }
        return null;
    }
}
```

### 4.2 构造方法的限制

```java
public enum Color {
    RED, GREEN;

    // ✅ 默认就是 private
    Color() { }

    // public Color() { }   // ❌ 编译错误：枚举构造方法不能是 public/protected
}
```

> ⚠️ 枚举的构造方法只能是 `private`（或不写，默认 private）。因为枚举实例只在类内部创建，外部不能 new。

---

## 五、枚举实现接口

枚举可以实现接口。有两种方式：统一实现，或每个枚举值各自实现。

### 5.1 统一实现

所有枚举值共享同一套实现：

```java
public interface Describable {
    String describe();
}

public enum Color implements Describable {
    RED, GREEN, BLUE;

    @Override
    public String describe() {       // 所有枚举值共用
        return "颜色：" + name();
    }
}

Color.RED.describe();   // 颜色：RED
Color.GREEN.describe(); // 颜色：GREEN
```

### 5.2 每个枚举值独立实现（策略模式雏形）⭐

每个枚举值用匿名类方式各自实现接口方法，这是**策略模式 + 枚举**的经典写法：

```java
public interface PayStrategy {
    void pay(String orderId, double amount);
}

public enum PayType implements PayStrategy {
    ALIPAY {
        @Override
        public void pay(String orderId, double amount) {
            System.out.println("支付宝支付：" + orderId + "，金额：" + amount);
        }
    },
    WECHAT {
        @Override
        public void pay(String orderId, double amount) {
            System.out.println("微信支付：" + orderId + "，金额：" + amount);
        }
    },
    BANK_CARD {
        @Override
        public void pay(String orderId, double amount) {
            System.out.println("银行卡支付：" + orderId + "，金额：" + amount);
        }
    };
    // 注意：这里分号结尾，没有统一实现
}

class Test {
    public static void main(String[] args) {
        PayType.ALIPAY.pay("ORD001", 99.9);   // 支付宝支付：ORD001，金额：99.9
        PayType.WECHAT.pay("ORD002", 50.0);   // 微信支付：ORD002，金额：50.0
    }
}
```

> 💡 每个枚举值其实是枚举类的一个**匿名子类实例**，可以各自重写方法。这种写法替代了繁琐的 if-else/switch 分发，扩展时加个枚举值即可，符合开闭原则。

---

## 六、枚举与 switch

`switch` 语句天然支持枚举，这是枚举最常见的用法之一：

```java
public enum OrderStatus {
    PENDING, PAID, SHIPPED, COMPLETED, CANCELLED
}

class OrderService {
    public void handle(OrderStatus status) {
        switch (status) {
            case PENDING:    // 注意：case 里直接写常量名，不加 OrderStatus.
                System.out.println("提醒用户支付");
                break;
            case PAID:
                System.out.println("通知仓库发货");
                break;
            case SHIPPED:
                System.out.println("更新物流信息");
                break;
            case COMPLETED:
                System.out.println("订单完成，邀请评价");
                break;
            case CANCELLED:
                System.out.println("退款处理");
                break;
            default:
                System.out.println("未知状态");
        }
    }
}
```

> ⚠️ **case 标签不能加枚举类前缀**：写 `case OrderStatus.PAID:` 会编译错误，只能写 `case PAID:`。因为编译器已从 switch 的类型推断出枚举类。

> 💡 Java 8 的 switch 不要求 default，但建议加上以防遗漏。配合策略模式（每个枚举值实现接口），可以完全消除 switch，更优雅。

---

## 七、枚举单例模式 ⭐⭐

单例模式有多种实现（饿汉、懒汉、双重检查锁、静态内部类），但**枚举单例是最简洁、最安全的方式**。

### 7.1 枚举单例写法

```java
public enum Singleton {
    INSTANCE;   // 唯一实例

    // 可以有字段和方法
    private int count = 0;

    public void increment() {
        count++;
        System.out.println("当前计数：" + count);
    }
}

class Test {
    public static void main(String[] args) {
        Singleton s1 = Singleton.INSTANCE;
        Singleton s2 = Singleton.INSTANCE;
        System.out.println(s1 == s2);   // true，同一个实例
        s1.increment();                 // 当前计数：1
        s2.increment();                 // 当前计数：2（同一个实例）
    }
}
```

### 7.2 为什么枚举单例最优

对比其他单例实现，枚举单例有两大天然优势：

| 特性 | 枚举单例 | 双重检查锁（DCL） | 静态内部类 |
| :--- | :--- | :--- | :--- |
| 线程安全 | ✅ 天然（JVM 保证） | 需手动写对 volatile + synchronized | ✅ 类加载保证 |
| 防反射破解 | ✅ 枚举不能反射创建 | ❌ 反射可破私有构造 | ❌ 反射可破 |
| 防反序列化破解 | ✅ 天然防 | ❌ 需实现 readResolve | ❌ 需实现 readResolve |
| 代码量 | 极简 | 较复杂 | 中等 |

```java
// ❌ 反射破解普通单例（演示攻击）
class HungrySingleton {
    private static HungrySingleton instance = new HungrySingleton();
    public static HungrySingleton getInstance() { return instance; }
    private HungrySingleton() { }
}

class Attack {
    public static void main(String[] args) throws Exception {
        HungrySingleton s1 = HungrySingleton.getInstance();
        // 反射强行调私有构造
        java.lang.reflect.Constructor<HungrySingleton> c =
            HungrySingleton.class.getDeclaredConstructor();
        c.setAccessible(true);
        HungrySingleton s2 = c.newInstance();
        System.out.println(s1 == s2);   // false，单例被破坏！
    }
}
```

```java
// ✅ 枚举单例：反射攻击直接抛异常
class AttackEnum {
    public static void main(String[] args) throws Exception {
        // java.lang.reflect.Constructor<Singleton> c =
        //     Singleton.class.getDeclaredConstructor();
        // c.setAccessible(true);
        // c.newInstance();   // ❌ 抛 IllegalArgumentException：不能反射创建枚举
    }
}
```

> ⚠️ 反序列化时，枚举的 `readObject` 是通过 `valueOf(name)` 返回已有实例，不会 new 新对象，所以**天然防反序列化破解**。

> 📌 **Effective Java 推荐**：实现单例首选枚举方式。这是 Joshua Bloch 在《Effective Java》中明确建议的。

---

## 八、枚举的线程安全性

枚举实例在**类加载阶段**由 JVM 创建，类加载本身就是线程安全的（JVM 保证每个类只初始化一次）。所以：

- 枚举常量的创建是线程安全的
- 枚举单例天然线程安全，无需任何同步机制

```java
public enum Config {
    INSTANCE;

    private java.util.Map<String, String> config = new java.util.concurrent.ConcurrentHashMap<>();

    public String get(String key) { return config.get(key); }
    public void put(String key, String value) { config.put(key, value); }
}
```

> 💡 枚举实例本身线程安全，但如果枚举内部有**可变字段**，对可变字段的访问仍需自己保证线程安全（如上例用 ConcurrentHashMap）。

---

## 九、枚举集合：EnumSet 与 EnumMap

JDK 专门为枚举提供了两个高性能集合，内部用位向量/数组实现，效率远超 HashSet/HashMap。

### 9.1 EnumSet

`EnumSet` 是专为枚举设计的 Set，内部用位向量（bit vector）实现，极其高效：

```java
import java.util.EnumSet;

enum Day { MON, TUE, WED, THU, FRI, SAT, SUN }

class Test {
    public static void main(String[] args) {
        // 工作日
        EnumSet<Day> workdays = EnumSet.range(Day.MON, Day.FRI);
        System.out.println(workdays);   // [MON, TUE, WED, THU, FRI]

        // 周末
        EnumSet<Day> weekend = EnumSet.of(Day.SAT, Day.SUN);
        System.out.println(weekend);    // [SAT, SUN]

        // 全部
        EnumSet<Day> all = EnumSet.allOf(Day.class);
        System.out.println(all);         // [MON, TUE, WED, THU, FRI, SAT, SUN]

        // 补集
        EnumSet<Day> rest = EnumSet.complementOf(workdays);
        System.out.println(rest);        // [SAT, SUN]
    }
}
```

> 💡 EnumSet 是抽象类，用静态工厂方法（`of`、`range`、`allOf`、`complementOf`）创建实例。当枚举值 ≤ 64 时用 RegularEnumSet（一个 long 的位向量），超过 64 用 JumboEnumSet（long 数组）。

### 9.2 EnumMap

`EnumMap` 是以枚举为 key 的 Map，内部用数组实现，下标即 ordinal，查询 O(1)：

```java
import java.util.EnumMap;

enum OrderStatus { PENDING, PAID, SHIPPED, COMPLETED, CANCELLED }

class Test {
    public static void main(String[] args) {
        EnumMap<OrderStatus, String> descMap = new EnumMap<>(OrderStatus.class);
        descMap.put(OrderStatus.PENDING, "待支付");
        descMap.put(OrderStatus.PAID, "已支付");
        descMap.put(OrderStatus.SHIPPED, "已发货");

        System.out.println(descMap.get(OrderStatus.PAID));   // 已支付
    }
}
```

> 📌 **选用建议**：当 key 是枚举类型时，优先用 `EnumMap` 而非 `HashMap`，性能更好、内存更省。同理 Set 用 `EnumSet`。

---

## ⚠️ 重点

### 重点 1：枚举比较用 == 还是 equals？⭐

```java
OrderStatus s1 = OrderStatus.PAID;
OrderStatus s2 = OrderStatus.PAID;
System.out.println(s1 == s2);         // ✅ true
System.out.println(s1.equals(s2));    // ✅ true
```

> 💡 两者都对，但**推荐用 `==`**。枚举实例是有限且固定的，同一个枚举值全局只有一个实例，`==` 比 `equals` 更快（直接比引用地址），且能避免 NullPointerException（`null == OrderStatus.PAID` 不报错，`null.equals(...)` 会 NPE）。Enum 的 equals 内部其实就是 `==`。

### 重点 2：ordinal() 不要用于业务 ⭐⭐

```java
// ❌ 危险：用 ordinal 当数据库存的值
OrderStatus.PAID.ordinal();   // 1

// 一旦有人在 PENDING 前面插入一个新状态，所有 ordinal 都变了
// 数据库里存的 1 原来是 PAID，现在变成别的了 → 数据错乱
```

```java
// ✅ 正确：用自定义 code 字段
OrderStatus.PAID.getCode();   // 2，与声明顺序解耦
```

> ⚠️ ordinal 只适合内部使用（如 EnumMap 的下标），**绝不能用于持久化、接口传输、业务判断**。

### 重点 3：valueOf 的异常处理 ⭐

```java
// ❌ 直接 valueOf，非法字符串会抛异常
OrderStatus s = OrderStatus.valueOf(input);   // input="ABC" → IllegalArgumentException

// ✅ 安全转换：先校验
public static OrderStatus safeValueOf(String name) {
    if (name == null) return null;
    for (OrderStatus s : values()) {
        if (s.name().equals(name)) return s;
    }
    return null;
}
```

> 💡 从外部输入（HTTP 参数、数据库）转枚举时，一定要做容错，别让一个非法字符串搞崩整个服务。

### 重点 4：枚举常量必须放第一行 ⭐

```java
public enum OrderStatus {
    // ✅ 枚举常量必须在最前面，分号结尾
    PENDING(1, "待支付"), PAID(2, "已支付");

    private final int code;
    // ❌ 如果在常量前写字段，编译错误

    OrderStatus(int code) { this.code = code; }
}
```

> ⚠️ 枚举常量列表必须是类的**第一条语句**，用逗号分隔，最后分号结尾。没有常量时（空枚举）也要写分号。

### 重点 5：枚举不能被继承 ⭐

```java
// public enum Base { }
// class Sub extends Base { }   // ❌ 编译错误：枚举是 final，不能继承
```

> 💡 枚举是 final 类，设计上就是为了固定实例集合。要「扩展」就用「实现接口 + 每个值各自重写」的方式，而非继承。

---

## 💻 实战案例

### 案例 1：订单状态枚举（电商核心）⭐⭐

电商订单状态是最典型的枚举应用，带 code、描述、流转判断：

```java
public enum OrderStatus {
    PENDING(1, "待支付"),
    PAID(2, "已支付"),
    SHIPPED(3, "已发货"),
    COMPLETED(4, "已完成"),
    CANCELLED(5, "已取消");

    private final int code;
    private final String desc;

    OrderStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public int getCode() { return code; }
    public String getDesc() { return desc; }

    // 通过 code 反查
    public static OrderStatus fromCode(int code) {
        for (OrderStatus s : values()) {
            if (s.code == code) return s;
        }
        throw new IllegalArgumentException("非法订单状态码：" + code);
    }

    // 判断是否允许取消
    public boolean canCancel() {
        return this == PENDING;   // 只有待支付可取消
    }

    // 判断是否允许发货
    public boolean canShip() {
        return this == PAID;     // 只有已支付可发货
    }
}
```

```java
class OrderService {
    public void cancelOrder(OrderStatus status) {
        if (!status.canCancel()) {
            throw new IllegalStateException("当前状态[" + status.getDesc() + "]不可取消");
        }
        System.out.println("订单已取消");
    }

    public void shipOrder(OrderStatus status) {
        if (!status.canShip()) {
            throw new IllegalStateException("当前状态[" + status.getDesc() + "]不可发货");
        }
        System.out.println("订单已发货");
    }
}

class Test {
    public static void main(String[] args) {
        OrderService service = new OrderService();
        service.cancelOrder(OrderStatus.PENDING);     // 订单已取消
        // service.cancelOrder(OrderStatus.SHIPPED);  // 抛异常：已发货不可取消
        service.shipOrder(OrderStatus.PAID);          // 订单已发货
    }
}
```

> 📌 把状态流转规则封装进枚举，比散落在各处 if-else 清晰得多，改规则只改枚举一处。

### 案例 2：支付方式枚举（策略模式 + 枚举）⭐⭐

不同支付方式走不同逻辑，用枚举实现策略分发，彻底消灭 switch：

```java
// 支付策略接口
public interface Payment {
    boolean pay(String orderId, long amountCent);   // 金额用分（long），避免浮点
    String getName();
}

// 支付方式枚举，每个值独立实现
public enum PayType implements Payment {
    ALIPAY("支付宝") {
        @Override
        public boolean pay(String orderId, long amountCent) {
            System.out.println("调用支付宝SDK，订单：" + orderId + "，金额：" + amountCent + "分");
            return true;
        }
    },
    WECHAT("微信支付") {
        @Override
        public boolean pay(String orderId, long amountCent) {
            System.out.println("调用微信支付API，订单：" + orderId + "，金额：" + amountCent + "分");
            return true;
        }
    },
    BANK_CARD("银行卡") {
        @Override
        public boolean pay(String orderId, long amountCent) {
            System.out.println("调用银联接口，订单：" + orderId + "，金额：" + amountCent + "分");
            return true;
        }
    },
    BALANCE("余额支付") {
        @Override
        public boolean pay(String orderId, long amountCent) {
            System.out.println("扣减账户余额，订单：" + orderId + "，金额：" + amountCent + "分");
            return true;
        }
    };

    private final String displayName;

    PayType(String displayName) { this.displayName = displayName; }

    @Override
    public String getName() { return displayName; }

    // 从字符串安全转换
    public static PayType fromName(String name) {
        if (name == null) return null;
        for (PayType p : values()) {
            if (p.name().equalsIgnoreCase(name)) return p;
        }
        return null;
    }
}
```

```java
// 支付服务
class PaymentService {
    public void processPay(String payTypeStr, String orderId, long amountCent) {
        PayType payType = PayType.fromName(payTypeStr);
        if (payType == null) {
            throw new IllegalArgumentException("不支持的支付方式：" + payTypeStr);
        }
        System.out.println("使用" + payType.getName() + "处理");
        boolean success = payType.pay(orderId, amountCent);
        if (success) {
            System.out.println("支付成功");
        }
    }
}

class Test {
    public static void main(String[] args) {
        new PaymentService().processPay("ALIPAY", "ORD001", 9999);   // 99.99 元
        new PaymentService().processPay("wechat", "ORD002", 5000);  // 50.00 元
    }
}
```

> 💡 新增支付方式只需加一个枚举值并实现 `pay`，**无需改 PaymentService 任何代码**——这就是开闭原则。如果用 switch，每加一种支付就要改 switch。

### 案例 3：错误码枚举（code + message）⭐

后台系统统一错误码，枚举是最佳载体：

```java
public enum ErrorCode {
    SUCCESS(0, "成功"),
    PARAM_ERROR(400, "参数错误"),
    UNAUTHORIZED(401, "未授权"),
    FORBIDDEN(403, "禁止访问"),
    NOT_FOUND(404, "资源不存在"),
    INTERNAL_ERROR(500, "服务器内部错误"),

    // 业务错误码
    USER_NOT_FOUND(1001, "用户不存在"),
    USER_PASSWORD_ERROR(1002, "用户名或密码错误"),
    ORDER_NOT_FOUND(2001, "订单不存在"),
    ORDER_STATUS_ERROR(2002, "订单状态异常"),
    STOCK_NOT_ENOUGH(3001, "库存不足");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() { return code; }
    public String getMessage() { return message; }
}
```

```java
// 统一返回结果
class Result<T> {
    private int code;
    private String message;
    private T data;

    public Result(int code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(ErrorCode.SUCCESS.getCode(), ErrorCode.SUCCESS.getMessage(), data);
    }

    public static <T> Result<T> error(ErrorCode errorCode) {
        return new Result<>(errorCode.getCode(), errorCode.getMessage(), null);
    }
}

class UserController {
    public Result<String> login(String username, String password) {
        if (username == null || password == null) {
            return Result.error(ErrorCode.PARAM_ERROR);
        }
        if (!"admin".equals(username)) {
            return Result.error(ErrorCode.USER_NOT_FOUND);
        }
        return Result.success("登录成功");
    }
}

class Test {
    public static void main(String[] args) {
        UserController c = new UserController();
        System.out.println(c.login(null, null).message);       // 参数错误
        System.out.println(c.login("guest", "1").message);     // 用户不存在
        System.out.println(c.login("admin", "123").message);   // 登录成功
    }
}
```

> 📌 错误码集中管理在枚举里，全系统共享，避免硬编码字符串和数字散落各处。

### 案例 4：枚举单例——全局配置管理器 ⭐

```java
public enum AppConfig {
    INSTANCE;

    private final java.util.Properties props = new java.util.Properties();

    // 初始化（实际可从配置文件加载）
    {
        props.setProperty("app.name", "电商系统");
        props.setProperty("app.version", "1.0.0");
        props.setProperty("db.url", "jdbc:mysql://localhost:3306/shop");
    }

    public String get(String key) {
        return props.getProperty(key);
    }

    public String get(String key, String defaultValue) {
        return props.getProperty(key, defaultValue);
    }
}

class Test {
    public static void main(String[] args) {
        // 全局唯一，任意位置获取配置
        String appName = AppConfig.INSTANCE.get("app.name");
        System.out.println(appName);   // 电商系统

        // 多线程下也是同一个实例
        for (int i = 0; i < 10; i++) {
            new Thread(() -> {
                System.out.println(AppConfig.INSTANCE.get("db.url"));
            }).start();
        }
    }
}
```

> 💡 枚举单例代码极简，且天然线程安全、防反射、防反序列化，是单例首选。

### 案例 5：EnumMap 管理状态处理器 ⭐

用 EnumMap 为每个订单状态注册对应处理器，替代冗长的 if-else：

```java
import java.util.EnumMap;

enum OrderStatus { PENDING, PAID, SHIPPED, COMPLETED, CANCELLED }

// 状态处理器接口
interface StatusHandler {
    void handle(String orderNo);
}

class OrderStateMachine {
    private final EnumMap<OrderStatus, StatusHandler> handlers =
        new EnumMap<>(OrderStatus.class);

    public OrderStateMachine() {
        handlers.put(OrderStatus.PENDING, orderNo ->
            System.out.println(orderNo + "：等待用户支付"));
        handlers.put(OrderStatus.PAID, orderNo ->
            System.out.println(orderNo + "：已支付，通知仓库"));
        handlers.put(OrderStatus.SHIPPED, orderNo ->
            System.out.println(orderNo + "：已发货，更新物流"));
        handlers.put(OrderStatus.COMPLETED, orderNo ->
            System.out.println(orderNo + "：已完成，邀请评价"));
        handlers.put(OrderStatus.CANCELLED, orderNo ->
            System.out.println(orderNo + "：已取消，执行退款"));
    }

    public void process(String orderNo, OrderStatus status) {
        StatusHandler handler = handlers.get(status);
        if (handler != null) {
            handler.handle(orderNo);
        } else {
            System.out.println(orderNo + "：无对应处理器");
        }
    }
}

class Test {
    public static void main(String[] args) {
        OrderStateMachine machine = new OrderStateMachine();
        machine.process("ORD001", OrderStatus.PAID);      // ORD001：已支付，通知仓库
        machine.process("ORD002", OrderStatus.CANCELLED); // ORD002：已取消，执行退款
    }
}
```

> 💡 EnumMap 查询 O(1)，新增状态只需注册一个 handler，是状态机/策略分发的优雅实现。

---

## 🚀 新版本补充

### Java 9+：EnumSet/EnumMap 无重大变化

枚举本身在 Java 8 之后没有语法层面的新增，但相关工具有小幅优化：

### Java 14：Switch 表达式（预览，16 正式）

Java 14+ 的 switch 表达式配合枚举，可以用 `->` 箭头语法，且无需 break：

```java
// Java 14+（Java 8 不可用，了解即可）
public String getAction(OrderStatus status) {
    return switch (status) {
        case PENDING -> "提醒支付";
        case PAID -> "通知发货";
        case SHIPPED -> "更新物流";
        case COMPLETED -> "邀请评价";
        case CANCELLED -> "执行退款";
    };
}
```

### Java 16：Record 与枚举配合

Java 16 的 record 类常与枚举搭配，用于携带数据的不可变对象：

```java
// Java 16+（Java 8 不可用）
public record OrderEvent(OrderStatus status, String orderNo, long timestamp) {}

// 配合枚举使用
OrderEvent event = new OrderEvent(OrderStatus.PAID, "ORD001", System.currentTimeMillis());
```

> ⚠️ 以上新特性 Java 8 环境均不可用，了解思想即可。Java 8 中枚举的 switch 仍需用传统 `case ...: break;` 语法。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 枚举本质 | 继承 `java.lang.Enum` 的 final 类，构造私有 |
| 常用方法 | `values()`、`valueOf(String)`、`name()`、`ordinal()` |
| 带属性枚举 | 加字段 + 私有构造 + getter，常配 `code`/`desc` |
| 实现接口 | 统一实现 或 每个枚举值各自重写（策略模式） |
| switch | case 直接写常量名，不加前缀 |
| 枚举单例 | 最优单例：线程安全 + 防反射 + 防反序列化 |
| 比较方式 | 推荐 `==`，也可 `equals` |
| ordinal() | 仅内部用，不可用于业务/持久化 |
| EnumSet | 位向量实现，枚举专用 Set |
| EnumMap | 数组实现，枚举做 key 的专用 Map |

---

## 学习建议

1. **用枚举替换项目里的 int 常量**：找出现有代码中 `public static final int` 表示状态的写法，改造成枚举，体会类型安全带来的好处——编译器帮你挡住非法值。
2. **重点掌握带属性的枚举**：实际开发中 90% 的枚举都带 `code` 和 `desc`，务必练熟「字段 + 私有构造 + getter + fromCode 反查」这套模板，这是基本功。
3. **理解枚举单例为何最优**：手写一个双重检查锁单例，再用反射破解它；再写一个枚举单例试试反射破解（会抛异常）。对比后你会明白 Effective Java 为什么首推枚举单例。
4. **用策略模式消灭 switch**：照着案例 2，把一个 switch 分发逻辑改写成「枚举实现接口 + 每个值各自重写」，体会开闭原则——新增分支不改老代码。
5. **牢记 ordinal 的陷阱**：ordinal 只能用于 EnumMap 内部下标，绝不能存数据库、不能做接口字段、不能做业务判断。所有需要持久化的场景一律用自定义 `code` 字段。
