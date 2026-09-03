# Set：HashSet 与 TreeSet

`Set` 是 Java 集合框架中用于存储**不重复元素**的容器。它继承自 `Collection` 接口，最大的特点是「不允许重复」——这正是日常开发中「去重」场景的利器：用户标签去重、商品 SKU 合并、黑名单过滤等都离不开它。

> 💡 在阅读本篇前，建议先看 [24-集合框架体系与Collection](24-集合框架体系与Collection.md) 了解 Set 在集合体系中的位置，以及 [17-Object类与Objects](17-Object类与Objects.md) 中 `equals`/`hashCode` 的重写规范——Set 的去重完全依赖这两个方法。

---

## 一、Set 接口特点

`Set` 接口继承自 `Collection`，但有几个鲜明的特征：

| 特点 | 说明 |
| :--- | :--- |
| **无索引** | 不能像 `List` 那样用 `get(i)` 按下标取元素（无序集合） |
| **不允许重复** | 添加重复元素时，新元素不会被存入（依赖 `equals`/`hashCode`） |
| **最多一个 null** | 大部分实现允许存一个 `null`（TreeSet 除外） |
| **遍历方式** | 增强 for、迭代器（不能用普通 for + 下标） |

```java
import java.util.HashSet;
import java.util.Set;

Set<String> set = new HashSet<>();
set.add("Java");
set.add("Java");          // 重复元素，不会被存入
set.add("Python");
set.add(null);            // HashSet 允许一个 null
System.out.println(set);  // [Java, Python, null]（顺序不固定）
System.out.println(set.size());  // 3
```

> ⚠️ **注意**：`Set` 没有 `get(int index)` 方法！这是它与 `List` 最直观的区别。想取元素只能遍历。

```java
Set<String> set = new HashSet<>();
set.add("A");
// String s = set.get(0);  // ❌ 编译错误：Set 没有 get(int) 方法
for (String s : set) {    // ✅ 只能遍历
    System.out.println(s);
}
```

---

## 二、HashSet（重点 ⭐⭐⭐）

`HashSet` 是 `Set` 接口最常用的实现类，它基于哈希表实现，**查询和增删的时间复杂度接近 O(1)**，是开发中默认的 Set 选择。

### 2.1 底层结构：HashMap

`HashSet` 的底层其实就是一个 `HashMap`——Set 中的元素被当作 `HashMap` 的 **key** 存储，而所有 key 共用一个固定的 value 对象（一个名为 `PRESENT` 的 `Object` 占位符）。

```java
// HashSet 源码核心（简化版）
public class HashSet<E> {
    private transient HashMap<E,Object> map;
    private static final Object PRESENT = new Object();  // 共享的假 value

    public HashSet() {
        map = new HashMap<>();
    }

    public boolean add(E e) {
        return map.put(e, PRESENT) == null;  // key 重复时 put 返回旧 value，add 返回 false
    }
}
```

> 💡 **理解关键**：`HashSet` 的所有特性（无序、不重复、允许 null、扩容机制）都来自 `HashMap` 的 key。学透 HashMap，HashSet 也就懂了（HashMap 底层详见 [27-Map](27-Map.md)）。

### 2.2 哈希值与 hashCode 方法

每个对象都有一个**哈希值**，由 `hashCode()` 方法计算得出。HashSet 用哈希值决定元素存放的「桶」位置。

```java
// Object 类的默认 hashCode：基于对象内存地址
Object obj = new Object();
System.out.println(obj.hashCode());  // 一个 int 值（如 12345678）

// String 重写了 hashCode：基于内容
String s1 = new String("hello");
String s2 = new String("hello");
System.out.println(s1.hashCode());  // 99162322
System.out.println(s2.hashCode());  // 99162322，内容相同则 hashCode 相同 ✅
```

> ⚠️ **哈希值与地址的关系**：`Object` 的默认 `hashCode` 与内存地址有关（但不是地址本身），所以两个 `new` 出来的不同对象哈希值通常不同；但 `String` 等重写了 `hashCode`，只要内容相同，哈希值就相同。

### 2.3 存储自定义对象必须重写 equals 和 hashCode ⭐⭐

这是 Set 使用中最容易踩的坑。如果不重写，会使用 `Object` 默认实现，导致**内容相同的两个对象被认为不同**：

```java
import java.util.HashSet;
import java.util.Set;
import java.util.Objects;

class User {
    String name;
    int age;

    public User(String name, int age) {
        this.name = name;
        this.age = age;
    }

    // ✅ 必须重写 equals 和 hashCode
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return age == user.age && Objects.equals(name, user.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, age);  // 用所有参与 equals 的字段计算
    }
}

public class Demo {
    public static void main(String[] args) {
        Set<User> set = new HashSet<>();
        set.add(new User("张三", 25));
        set.add(new User("张三", 25));  // 内容相同，应被去重
        System.out.println(set.size());  // ✅ 1（重写了 equals/hashCode）

        // ❌ 若不重写，size 会是 2——因为两个 new 出来的对象地址不同
    }
}
```

> 📌 **铁律**：**重写 `equals` 必须同时重写 `hashCode`**，且参与计算的字段要一致。否则 HashSet 去重会失效，是开发中极隐蔽的 bug 来源。IDEA 中可用 `Alt + Insert` → `equals() and hashCode()` 自动生成。

### 2.4 JDK 1.8 后的底层：数组 + 链表 + 红黑树

HashSet（即 HashMap 的 key）在 JDK 1.8 的存储结构：

```
哈希表（数组 + 链表 + 红黑树）
┌─────────────────────────────────────────────────┐
│  桶数组 table[]                                  │
│  [0] → null                                      │
│  [1] → Node1 → Node2 → Node3 → ... （链表）      │
│  [2] → null                                      │
│  [3] → TreeNode（红黑树，链表树化后）             │
│  ...                                             │
└─────────────────────────────────────────────────┘
```

**树化条件（两个都要满足）**：
1. 某个桶的链表长度 **> 8**
2. 数组长度 **>= 64**

**退化条件**：红黑树节点数 **<= 6** 时，退化回链表。

```java
// JDK 1.7：数组 + 链表（链表过长时查询退化为 O(n)）
// JDK 1.8：数组 + 链表 + 红黑树（链表超 8 且数组够大时转树，查询优化为 O(log n)）
```

> 💡 **为什么是 8？** 这是基于泊松分布的统计学选择：哈希分布均匀时，一个桶达到 8 个元素的概率约为 0.00000006，几乎不会发生；一旦发生说明哈希冲突严重，此时用红黑树保证最坏情况性能。

### 2.5 无序性：存取顺序不一致

`HashSet` 不保证元素的存储顺序和取出顺序一致，更不保证顺序恒定不变：

```java
import java.util.HashSet;

HashSet<String> set = new HashSet<>();
set.add("C");
set.add("A");
set.add("B");
set.add("D");
System.out.println(set);  // 输出顺序可能是 [A, B, C, D]，也可能不是

// ⚠️ 不要依赖 HashSet 的顺序做业务逻辑！
// 如果需要按存入顺序取出，用 LinkedHashSet
```

> ⚠️ **真实事故**：曾有用例把 HashSet 遍历结果拼成 SQL 的 `IN (...)` 子句，因为顺序不稳定导致 SQL 缓存命中率极低。需要稳定顺序时务必用 `LinkedHashSet`。

---

## 三、LinkedHashSet

`LinkedHashSet` 是 `HashSet` 的子类，在 HashSet 基础上维护了一条**双向链表**，记录元素的插入顺序（或访问顺序），从而保证**存取顺序一致**。

```
HashSet 内部结构 + 一条贯穿所有节点的双向链表

  节点A ⇄ 节点B ⇄ 节点C ⇄ 节点D
   ↑                    ↑
  head                  tail（按插入顺序串联）
```

```java
import java.util.LinkedHashSet;
import java.util.HashSet;

// ❌ HashSet 无序
HashSet<String> hs = new HashSet<>();
hs.add("C"); hs.add("A"); hs.add("B");
System.out.println(hs);  // [A, B, C]（不保证）

// ✅ LinkedHashSet 按插入顺序
LinkedHashSet<String> lhs = new LinkedHashSet<>();
lhs.add("C"); lhs.add("A"); lhs.add("B");
System.out.println(lhs);  // [C, A, B]（稳定保持插入顺序）
```

> 💡 **性能取舍**：`LinkedHashSet` 比 `HashSet` 多维护一条链表，内存略增、增删略慢，但遍历性能更好（链表顺序遍历，不受桶分布影响）。**需要保留插入顺序的去重场景，首选 LinkedHashSet。**

---

## 四、TreeSet

`TreeSet` 基于 `TreeMap`（红黑树）实现，最大特点是**会对元素自动排序**。适合需要有序遍历、范围查询的场景。

### 4.1 底层：TreeMap（红黑树）

```
红黑树结构（自平衡二叉查找树）

              [5]
             /    \
          [2]      [8]
          / \      / \
       [1] [3]  [6] [9]
```

红黑树是一棵**自平衡二叉查找树**：左子树 < 根 < 右子树，插入/删除时通过旋转和变色保持平衡，保证查询/插入/删除都是 **O(log n)**。

### 4.2 自然排序（Comparable）

`TreeSet` 默认使用**自然排序**：元素必须实现 `Comparable` 接口。Java 内置类型（`Integer`、`String`、`Date` 等）都已实现：

```java
import java.util.TreeSet;

// Integer 自然排序（升序）
TreeSet<Integer> nums = new TreeSet<>();
nums.add(5); nums.add(1); nums.add(3); nums.add(2);
System.out.println(nums);  // [1, 2, 3, 5]（自动排序）

// String 自然排序（字典序）
TreeSet<String> strs = new TreeSet<>();
strs.add("banana"); strs.add("apple"); strs.add("cherry");
System.out.println(strs);  // [apple, banana, cherry]
```

**自定义对象必须实现 Comparable**，否则会抛 `ClassCastException`：

```java
import java.util.TreeSet;

class Product implements Comparable<Product> {
    String name;
    double price;

    public Product(String name, double price) {
        this.name = name;
        this.price = price;
    }

    // ✅ 实现 Comparable，按价格升序排
    @Override
    public int compareTo(Product other) {
        return Double.compare(this.price, other.price);
    }

    @Override
    public String toString() {
        return name + "(" + price + ")";
    }
}

public class Demo {
    public static void main(String[] args) {
        TreeSet<Product> set = new TreeSet<>();
        set.add(new Product("鼠标", 99));
        set.add(new Product("键盘", 199));
        set.add(new Product("耳机", 49));
        System.out.println(set);  // [耳机(49.0), 鼠标(99.0), 键盘(199.0)]

        // ❌ 若 Product 不实现 Comparable：
        // java.lang.ClassCastException: Product cannot be cast to java.lang.Comparable
    }
}
```

> ⚠️ **TreeSet 不允许 null**：因为 null 无法与其它元素比较，`add(null)` 会抛 `NullPointerException`。这是它与 HashSet/LinkedHashSet 的显著区别。

### 4.3 定制排序（Comparator）

如果不想用元素的「自然排序」，或者元素类没实现 `Comparable`，可以在创建 TreeSet 时传入 `Comparator`：

```java
import java.util.TreeSet;
import java.util.Comparator;

// 按 price 降序
TreeSet<Product> set = new TreeSet<>(new Comparator<Product>() {
    @Override
    public int compare(Product a, Product b) {
        return Double.compare(b.price, a.price);  // 注意 a b 顺序反了 → 降序
    }
});
set.add(new Product("鼠标", 99));
set.add(new Product("键盘", 199));
set.add(new Product("耳机", 49));
System.out.println(set);  // [键盘(199.0), 鼠标(99.0), 耳机(49.0)]
```

Java 8 起可用 Lambda 简化（Comparator 属基准内容）：

```java
// ✅ Lambda 写法（Java 8）
TreeSet<Product> set = new TreeSet<>((a, b) -> Double.compare(b.price, a.price));
// 或用 Comparator 静态方法
TreeSet<Product> set2 = new TreeSet<>(Comparator.comparingDouble((Product p) -> -p.price));
```

> 💡 **自然排序 vs 定制排序**：自然排序写在「元素类」里（`Comparable`），是元素自身的默认排序规则；定制排序写在「集合」里（`Comparator`），是临时覆盖排序规则。定制排序优先级更高。

### 4.4 TreeSet 特有方法

得益于有序性，TreeSet 提供了一系列范围查询方法：

```java
TreeSet<Integer> set = new TreeSet<>();
set.add(10); set.add(20); set.add(30); set.add(40); set.add(50);

set.first();              // 10，最小元素
set.last();               // 50，最大元素
set.headSet(30);          // [10, 20]，小于 30 的元素
set.tailSet(30);          // [30, 40, 50]，大于等于 30 的
set.subSet(20, 40);       // [20, 30]，[20, 40) 区间
set.ceiling(25);          // 30，大于等于 25 的最小元素
set.floor(25);            // 20，小于等于 25 的最大元素
set.higher(30);           // 40，严格大于 30 的最小元素
set.lower(30);            // 20，严格小于 30 的最大元素
```

> 💡 这些方法在「排行榜取前 N 名」「价格区间筛选」等场景非常实用。

---

## 五、HashSet vs LinkedHashSet vs TreeSet

| 特性 | HashSet | LinkedHashSet | TreeSet |
| :--- | :--- | :--- | :--- |
| **底层结构** | HashMap（数组+链表+红黑树） | HashSet + 双向链表 | TreeMap（红黑树） |
| **是否有序** | 无序 | ✅ 插入顺序 | ✅ 排序（自然/定制） |
| **是否允许 null** | ✅ 一个 | ✅ 一个 | ❌ 不允许 |
| **去重依据** | equals + hashCode | equals + hashCode | compareTo / compare |
| **增删查复杂度** | O(1) | O(1) | O(log n) |
| **线程安全** | ❌ | ❌ | ❌ |
| **适用场景** | 通用去重，性能优先 | 需保留插入顺序的去重 | 需要排序/范围查询 |
| **自定义对象要求** | 重写 equals + hashCode | 重写 equals + hashCode | 实现 Comparable 或传 Comparator |

> 📌 **选型建议**：默认用 `HashSet`；需要稳定遍历顺序用 `LinkedHashSet`；需要排序或范围查询用 `TreeSet`。

---

## 六、Set 去重原理详解 ⭐

理解去重原理是掌握 Set 的关键。HashSet 添加元素时的判断流程：

```
add(element) 流程：
1. 计算 element.hashCode()
2. 用 hash & (n-1) 定位桶（n 是数组长度）
3. 该桶为空 → 直接放入 ✅
4. 该桶非空 → 遍历桶内元素：
   a. 先比 hashCode：若不同，说明不是同一元素，追加到链表/树
   b. 若 hashCode 相同，再用 equals 比较：
      - true  → 重复，不加入 ❌（add 返回 false）
      - false → 不重复，加入链表/树
```

**为什么先比 hashCode 再比 equals？** 因为 `hashCode` 是 int 比较，速度极快；而 `equals` 可能涉及多字段逐个比较，较慢。先用 hashCode 快速排除大部分不同对象，只有哈希冲突时才用 equals 精确比较——这是性能优化的经典设计。

```java
// 验证去重流程
class Person {
    String name;
    Person(String name) { this.name = name; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Person)) return false;
        return this.name.equals(((Person) o).name);
    }

    @Override
    public int hashCode() {
        System.out.println("调用 hashCode: " + name);  // 观察调用时机
        return Objects.hash(name);
    }
}

Set<Person> set = new HashSet<>();
set.add(new Person("张三"));  // 调用 hashCode
set.add(new Person("李四"));  // 调用 hashCode
set.add(new Person("张三"));  // 调用 hashCode + equals（hashCode 相同才调 equals）
System.out.println(set.size());  // 2
```

> ⚠️ **致命错误：重写 equals 不重写 hashCode**。若两个对象 `equals` 为 true 但 `hashCode` 不同，HashSet 会把它们分到不同桶里，**永远无法触发 equals 比较，导致去重失效**。这是「重写 equals 必须重写 hashCode」的根本原因。

---

## ⚠️ 重点

### 重点 1：Set 没有索引，不能用普通 for 循环 ⭐

```java
Set<String> set = new HashSet<>();
set.add("A"); set.add("B");

// ❌ Set 没有 get(int) 方法
// for (int i = 0; i < set.size(); i++) { set.get(i); }

// ✅ 只能用增强 for 或迭代器
for (String s : set) { System.out.println(s); }
// 或
Iterator<String> it = set.iterator();
while (it.hasNext()) { System.out.println(it.next()); }
// 或 Java 8
set.forEach(System.out::println);
```

### 重点 2：自定义对象存 HashSet/LinkedHashSet 必须重写 equals 和 hashCode ⭐⭐⭐

```java
class Student {
    String id;
    Student(String id) { this.id = id; }
    // ❌ 不重写：两个 new Student("1") 会被当成不同对象，去重失效
}

// ✅ 必须重写
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Student)) return false;
    Student s = (Student) o;
    return Objects.equals(id, s.id);
}
@Override
public int hashCode() {
    return Objects.hash(id);  // 字段与 equals 保持一致
}
```

> 📌 **规范**：`equals` 用哪些字段，`hashCode` 就用哪些字段。IDEA 快捷键 `Alt + Insert` 自动生成最稳妥。

### 重点 3：TreeSet 元素必须可比较 ⭐⭐

```java
// ❌ 自定义对象未实现 Comparable 且未传 Comparator
TreeSet<MyClass> set = new TreeSet<>();
set.add(new MyClass());  // ClassCastException

// ✅ 方式一：实现 Comparable
class MyClass implements Comparable<MyClass> {
    public int compareTo(MyClass o) { /* ... */ }
}

// ✅ 方式二：构造时传 Comparator
TreeSet<MyClass> set = new TreeSet<>(Comparator.comparingInt(m -> m.x));
```

### 重点 4：TreeSet 不允许 null ⭐

```java
TreeSet<String> set = new TreeSet<>();
set.add(null);  // ❌ NullPointerException（null 无法比较）

HashSet<String> set2 = new HashSet<>();
set2.add(null);  // ✅ HashSet 允许一个 null
```

### 重点 5：HashSet 的「无序」不是「随机」 ⭐

```java
HashSet<Integer> set = new HashSet<>();
for (int i = 1; i <= 8; i++) set.add(i);
System.out.println(set);  // 输出看似有序，但这是哈希分布的巧合，不是保证
// 当元素增多或扩容后，顺序会变
// ⚠️ 永远不要依赖 HashSet 的输出顺序做业务判断
```

### 重点 6：重写 hashCode 时避免只用一个字段 ⭐

```java
// ❌ 不好的写法：只用 name 算 hashCode，age 不同也会被分到同一桶
@Override
public int hashCode() { return name.hashCode(); }

// ✅ 用所有参与 equals 的字段
@Override
public int hashCode() { return Objects.hash(name, age); }
```

> 💡 好的 `hashCode` 应尽量分散，减少哈希冲突，提升性能。`Objects.hash(...)` 是 JDK 推荐的便捷写法。

---

## 💻 实战案例

### 案例 1：用户标签去重（电商系统）⭐⭐

电商系统中，一个用户可能有多个来源的标签（注册标签、行为标签、运营标签），需要合并去重：

```java
import java.util.*;

public class TagDedup {
    public static void main(String[] args) {
        // 不同来源的标签
        List<String> regTags  = Arrays.asList("新用户", "手机注册");
        List<String> behaTags = Arrays.asList("高频购买", "新用户", "价格敏感");
        List<String> opTags   = Arrays.asList("VIP", "价格敏感", "新用户");

        // ✅ 用 HashSet 一行去重
        Set<String> allTags = new HashSet<>();
        allTags.addAll(regTags);
        allTags.addAll(behaTags);
        allTags.addAll(opTags);
        System.out.println("用户标签: " + allTags);
        // [新用户, 手机注册, 高频购买, 价格敏感, VIP]

        // 需要保留来源顺序 → 用 LinkedHashSet
        Set<String> orderedTags = new LinkedHashSet<>();
        orderedTags.addAll(regTags);
        orderedTags.addAll(behaTags);
        orderedTags.addAll(opTags);
        System.out.println("有序标签: " + orderedTags);
        // [新用户, 手机注册, 高频购买, 价格敏感, VIP]
    }
}
```

### 案例 2：商品 SKU 去重（自定义对象）⭐⭐

同一商品可能有多个渠道来源的 SKU 记录，需要按「商品编码」去重：

```java
import java.util.*;

class Sku {
    String code;   // 商品编码（唯一标识）
    String name;
    double price;

    public Sku(String code, String name, double price) {
        this.code = code; this.name = name; this.price = price;
    }

    // ✅ 去重依据：code 相同即视为同一 SKU
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Sku)) return false;
        return Objects.equals(code, ((Sku) o).code);
    }
    @Override
    public int hashCode() {
        return Objects.hash(code);  // 只用 code
    }
    @Override
    public String toString() { return code + ":" + name; }
}

public class SkuDedup {
    public static void main(String[] args) {
        // 三个渠道来的 SKU，有重复
        Set<Sku> skuSet = new HashSet<>();
        skuSet.add(new Sku("SKU001", "iPhone", 5999));
        skuSet.add(new Sku("SKU002", "iPad", 3999));
        skuSet.add(new Sku("SKU001", "iPhone", 5999));  // 重复，被去重
        skuSet.add(new Sku("SKU003", "AirPods", 1299));
        skuSet.add(new Sku("SKU002", "iPad", 3999));     // 重复，被去重

        System.out.println("去重后 SKU 数量: " + skuSet.size());  // 3
        for (Sku sku : skuSet) {
            System.out.println(sku);
        }
    }
}
```

> ⚠️ **坑**：如果不重写 `equals`/`hashCode`，上面 5 个对象会被全部保留（size=5），因为 `new` 出来的对象地址都不同。这是真实开发中最常见的去重失效原因。

### 案例 3：LinkedHashSet 实现 LRU 缓存雏形 ⭐

LRU（Least Recently Used）缓存淘汰最近最少使用的元素。LinkedHashMap 可直接开启访问顺序模式实现 LRU，这里用 LinkedHashSet 模拟一个简化版「最近访问的 N 个用户」：

```java
import java.util.LinkedHashSet;
import java.util.Set;

public class RecentUsers {
    // 维护最近访问的 5 个用户（FIFO 风格的简化 LRU）
    private static final int MAX = 5;
    private Set<String> recent = new LinkedHashSet<>();

    public void access(String user) {
        // 若已存在，先删除再添加，使其移到末尾（最近访问）
        if (recent.contains(user)) {
            recent.remove(user);
        }
        recent.add(user);
        // 超过容量，淘汰最早的（链表头部）
        while (recent.size() > MAX) {
            String oldest = recent.iterator().next();
            recent.remove(oldest);
            System.out.println("淘汰: " + oldest);
        }
    }

    public void show() {
        System.out.println("最近访问: " + recent);
    }

    public static void main(String[] args) {
        RecentUsers cache = new RecentUsers();
        cache.access("user1");
        cache.access("user2");
        cache.access("user3");
        cache.access("user4");
        cache.access("user5");
        cache.show();  // [user1, user2, user3, user4, user5]
        cache.access("user3");  // user3 移到末尾
        cache.show();  // [user1, user2, user4, user5, user3]
        cache.access("user6");  // 淘汰 user1
        cache.show();  // [user2, user4, user5, user3, user6]
    }
}
```

> 💡 **生产环境**真正实现 LRU 用 `LinkedHashMap` 的 `accessOrder=true` + 重写 `removeEldestEntry` 更优雅，这里仅为演示 LinkedHashSet 的链表特性。

### 案例 4：TreeSet 按价格排序商品（电商后台）⭐⭐

后台管理系统需要按价格对商品排序，并支持区间查询：

```java
import java.util.*;

class Goods implements Comparable<Goods> {
    String name;
    double price;

    Goods(String name, double price) { this.name = name; this.price = price; }

    // ✅ 自然排序：按价格升序
    @Override
    public int compareTo(Goods o) {
        return Double.compare(this.price, o.price);
    }
    @Override
    public String toString() { return name + "(" + price + ")"; }
}

public class GoodsSort {
    public static void main(String[] args) {
        TreeSet<Goods> goods = new TreeSet<>();
        goods.add(new Goods("鼠标", 99));
        goods.add(new Goods("显示器", 1299));
        goods.add(new Goods("键盘", 199));
        goods.add(new Goods("耳机", 49));
        goods.add(new Goods("主机", 3999));

        // ✅ 自动升序
        System.out.println("价格升序: " + goods);
        // [耳机(49.0), 鼠标(99.0), 键盘(199.0), 显示器(1299.0), 主机(3999.0)]

        // ✅ 最便宜 / 最贵
        System.out.println("最便宜: " + goods.first());  // 耳机(49.0)
        System.out.println("最贵: " + goods.last());     // 主机(3999.0)

        // ✅ 价格区间 [100, 2000)
        System.out.println("100~2000: " + goods.subSet(
            new Goods("", 100), new Goods("", 2000)));
        // [鼠标(99.0) 不在，键盘(199.0), 显示器(1299.0)]
        // 注意 subSet 是 [100, 2000)，左闭右开

        // ✅ 大于等于 199 的（tailSet）
        System.out.println(">=199: " + goods.tailSet(new Goods("", 199)));
        // [键盘(199.0), 显示器(1299.0), 主机(3999.0)]

        // ✅ 降序视图
        System.out.println("降序: " + goods.descendingSet());
        // [主机(3999.0), 显示器(1299.0), 键盘(199.0), 鼠标(99.0), 耳机(49.0)]
    }
}
```

### 案例 5：抽奖去重（活动运营）

运营抽奖活动，同一用户不能重复中奖：

```java
import java.util.*;

public class Lottery {
    public static void main(String[] args) {
        // 所有参与用户
        List<String> participants = Arrays.asList(
            "张三", "李四", "王五", "张三", "赵六", "李四", "钱七", "张三");

        // ✅ 先用 Set 去重，保证一人一次参与
        Set<String> unique = new LinkedHashSet<>(participants);
        System.out.println("有效参与: " + unique);
        // [张三, 李四, 王五, 赵六, 钱七]（保留首次出现顺序）

        // 从去重后的用户中随机抽 3 名
        List<String> pool = new ArrayList<>(unique);
        Collections.shuffle(pool);
        System.out.println("中奖: " + pool.subList(0, 3));
    }
}
```

### 案例 6：敏感词过滤（内容审核系统）⭐

内容审核系统中，用 HashSet 存储敏感词库，对用户输入做快速过滤：

```java
import java.util.*;

public class SensitiveFilter {
    // 敏感词库（启动时加载，HashSet 查询 O(1)）
    private static final Set<String> SENSITIVE = new HashSet<>(
        Arrays.asList("广告", "诈骗", "赌博", "色情", "违禁"));

    public static String filter(String content) {
        String result = content;
        for (String word : SENSITIVE) {
            if (result.contains(word)) {
                result = result.replace(word, "***");
            }
        }
        return result;
    }

    public static void main(String[] args) {
        String post = "这条是诈骗广告，请勿点击赌博链接";
        System.out.println(filter(post));  // 这条是******，请勿点击***链接
    }
}
```

> 💡 **为什么用 HashSet？** 敏感词匹配是高频查询，HashSet 的 `contains` 是 O(1)，比 List 的 O(n) 快得多。生产级敏感词过滤会用更专业的 AC 自动机/Trie 树，但 HashSet 是最直观的入门方案。

### 案例 7：求两个集合的交并差（权限系统）⭐

权限系统中，常需要对角色权限集合做交、并、差运算：

```java
import java.util.*;

public class PermissionMerge {
    public static void main(String[] args) {
        Set<String> roleA = new HashSet<>(Arrays.asList("read", "write", "delete"));
        Set<String> roleB = new HashSet<>(Arrays.asList("read", "export", "share"));

        // ✅ 并集：A 和 B 的所有权限
        Set<String> union = new HashSet<>(roleA);
        union.addAll(roleB);
        System.out.println("并集: " + union);  // [read, write, delete, export, share]

        // ✅ 交集：A 和 B 都有的权限
        Set<String> inter = new HashSet<>(roleA);
        inter.retainAll(roleB);
        System.out.println("交集: " + inter);  // [read]

        // ✅ 差集：A 有但 B 没有的权限
        Set<String> diff = new HashSet<>(roleA);
        diff.removeAll(roleB);
        System.out.println("差集(A-B): " + diff);  // [write, delete]

        // ✅ 对称差：A∪B - A∩B（只在其中一个集合出现的权限）
        Set<String> symDiff = new HashSet<>(union);
        symDiff.removeAll(inter);
        System.out.println("对称差: " + symDiff);  // [write, delete, export, share]
    }
}
```

> 📌 **API 速记**：`addAll` = 并集，`retainAll` = 交集，`removeAll` = 差集。这三个方法来自 `Collection` 接口，Set 和 List 都能用。

---

## 🚀 新版本补充

### Java 9：集合工厂方法 `Set.of()`

Java 9 起可用 `Set.of()` 创建**不可变 Set**（Immutable）：

```java
// Java 9+
Set<String> immutable = Set.of("A", "B", "C");
// immutable.add("D");  // ❌ UnsupportedOperationException

// ⚠️ Set.of 不允许 null，不允许重复元素
// Set.of("A", null);      // ❌ NullPointerException
// Set.of("A", "A");       // ❌ IllegalArgumentException
```

> 💡 Java 8 环境下不可用，可用 `Collections.unmodifiableSet(new HashSet<>(...))` 实现不可变 Set。

### Java 9：`Set.of` 与 `Arrays.asList` 的区别

```java
// Arrays.asList 返回的是固定大小的 List，可 set 不能 add
List<String> list = Arrays.asList("A", "B");

// Set.of 返回的是完全不可变 Set
Set<String> set = Set.of("A", "B");
```

### Java 10：`var` 与 Set 推断

```java
// Java 10+ 局部变量类型推断（Java 8 不可用，了解）
var set = new HashSet<String>();   // 推断为 HashSet<String>
var immutable = Set.of("A", "B"); // 推断为 Set<String>
```

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Set 接口 | 无索引、不重复、最多一个 null（TreeSet 除外） |
| HashSet 底层 | HashMap（数组+链表+红黑树），元素作 key |
| HashSet 特点 | 无序、允许 null、增删查 O(1) |
| 树化条件 | 链表 >8 且数组 >=64 转红黑树；节点 <=6 退化链表 |
| LinkedHashSet | HashSet + 双向链表，保留插入顺序 |
| TreeSet 底层 | TreeMap（红黑树），自动排序 |
| TreeSet 排序 | 自然排序 Comparable / 定制排序 Comparator |
| TreeSet 限制 | 不允许 null，元素必须可比较 |
| 去重原理 | 先比 hashCode 定桶，hashCode 相同再比 equals |
| 自定义对象 | 存 HashSet 必须重写 equals + hashCode |
| 集合运算 | addAll 并集、retainAll 交集、removeAll 差集 |

---

## 学习建议

1. **先吃透 hashCode 和 equals**：Set 的去重完全依赖这两个方法，务必结合 [17-Object类与Objects](17-Object类与Objects.md) 理解「equals 相等则 hashCode 必须相等」的契约，这是 Set 篇的核心。
2. **动手验证去重失效的坑**：写一个不重写 equals/hashCode 的类存进 HashSet，观察 size 不对；再重写后观察去重生效——亲眼看到 bug 比看十遍文字都深刻。
3. **对比三种 Set 的输出顺序**：把同样的元素分别加入 HashSet、LinkedHashSet、TreeSet，打印对比输出，直观感受「无序 / 插入序 / 排序」的区别。
4. **理解树化阈值的设计**：记住「链表 >8 且数组 >=64 才树化」这个组合条件，思考为什么是 8（泊松分布），这能帮你理解 HashMap 性能优化的设计哲学，为下一篇 Map 底层打基础。
5. **用 TreeSet 做一次范围查询**：写一个按价格排序的商品 TreeSet，练习 `subSet`/`headSet`/`tailSet`/`ceiling`/`floor`，这些方法在排行榜、价格筛选等真实业务中非常常用。
