# Collections 工具类与排序

`java.util.Collections` 是一个**工具类**，专门对集合进行批量操作：排序、查找、反转、打乱、包装成不可变或线程安全集合等。它和 `Collection` 接口名字很像，但完全是两个东西——一个是工具类（静态方法），一个是接口（单列集合的根）。掌握 `Collections` 的同时，必须搞懂两个排序核心接口：`Comparable`（自然排序）和 `Comparator`（定制排序），它们是 Java 排序体系的基石。

> 💡 在阅读本篇前，建议先看 [28-集合框架体系](28-集合框架体系.md) 和 [29-List与Set](29-List与Set.md)，对 List/Set/Map 的整体结构有基本认识后再来看工具类操作会更顺。

---

## 一、Collections 与 Collection 的区别

新手最容易把这两个名字搞混，先彻底区分：

| 对比项 | `Collection` 接口 | `Collections` 工具类 |
| :--- | :--- | :--- |
| 类型 | 接口 | 类 |
| 包 | java.util | java.util |
| 作用 | 单列集合的**根接口**（List/Set 的父） | 操作集合的**静态工具方法集合** |
| 是否可实例化 | 不能直接 new（接口） | 不能 new（构造私有，全是静态方法） |
| 典型用法 | `Collection<Integer> c = new ArrayList<>();` | `Collections.sort(list);` |

```java
import java.util.ArrayList;
import java.util.Collection;    // 接口
import java.util.Collections;   // 工具类
import java.util.List;

// Collection 是接口，用来声明变量
Collection<String> col = new ArrayList<>();   // ✅ 多态
// Collections c = new Collections();        // ❌ 构造私有，不能实例化

List<Integer> list = new ArrayList<>();
Collections.sort(list);   // ✅ 工具类调用静态方法
```

> ⚠️ **记忆技巧**：带 `s` 的是工具类（Collections = 集合 + s，表示一堆操作集合的工具方法）；不带 `s` 的是接口。

---

## 二、Collections 常用方法

### 2.1 批量添加 addAll

`addAll(Collection<? super T> c, T... elements)`：一次性往集合里塞多个元素，比循环 `add` 简洁。

```java
List<String> list = new ArrayList<>();
// 传统写法
list.add("a");
list.add("b");
list.add("c");

// ✅ addAll 一行搞定
Collections.addAll(list, "d", "e", "f");
System.out.println(list);  // [a, b, c, d, e, f]
```

> 💡 `Collections.addAll` 性能通常比 `list.addAll(Arrays.asList(...))` 更好，因为后者要先创建数组和包装对象，前者直接遍历可变参数。

### 2.2 打乱顺序 shuffle

`shuffle(List<?> list)`：随机打乱 List 中元素顺序，常用于抽奖、洗牌。

```java
List<Integer> cards = new ArrayList<>();
for (int i = 1; i <= 54; i++) {
    cards.add(i);
}
Collections.shuffle(cards);   // ✅ 洗牌
System.out.println(cards.subList(0, 5));  // 随机 5 张
```

> 💡 可传入第二个参数 `Random` 对象来固定随机种子，便于测试时复现结果：`Collections.shuffle(list, new Random(42));`

### 2.3 自然排序 sort

`sort(List<T> list)`：要求元素实现 `Comparable`，默认升序。

```java
List<Integer> nums = new ArrayList<>();
Collections.addAll(nums, 5, 1, 9, 3, 7);
Collections.sort(nums);     // ✅ 升序
System.out.println(nums);   // [1, 3, 5, 7, 9]

List<String> strs = new ArrayList<>();
Collections.addAll(strs, "banana", "apple", "cherry");
Collections.sort(strs);     // ✅ 字典序
System.out.println(strs);   // [apple, banana, cherry]
```

### 2.4 定制排序 sort(List, Comparator)

当元素没实现 `Comparable`，或想换一种排序规则时，传入 `Comparator`：

```java
List<Integer> nums = new ArrayList<>();
Collections.addAll(nums, 5, 1, 9, 3, 7);
// 降序：传入比较器
Collections.sort(nums, new Comparator<Integer>() {
    @Override
    public int compare(Integer o1, Integer o2) {
        return o2 - o1;   // o2-o1 降序
    }
});
System.out.println(nums);  // [9, 7, 5, 3, 1]
```

### 2.5 反转与交换

```java
List<Integer> list = new ArrayList<>();
Collections.addAll(list, 1, 2, 3, 4, 5);

Collections.reverse(list);   // ✅ 反转
System.out.println(list);     // [5, 4, 3, 2, 1]

Collections.swap(list, 0, 4); // ✅ 交换下标 0 和 4 的元素
System.out.println(list);     // [1, 4, 3, 2, 5]
```

### 2.6 求极值 max / min

```java
List<Integer> list = new ArrayList<>();
Collections.addAll(list, 5, 1, 9, 3, 7);
System.out.println(Collections.max(list));  // 9
System.out.println(Collections.min(list));  // 1

// 传入 Comparator：按字符串长度求最长
List<String> strs = new ArrayList<>();
Collections.addAll(strs, "a", "bbb", "cc");
String longest = Collections.max(strs, Comparator.comparing(String::length));
System.out.println(longest);  // bbb
```

### 2.7 出现次数 frequency 与无交集 disjoint

```java
List<String> list = new ArrayList<>();
Collections.addAll(list, "a", "b", "a", "c", "a");
System.out.println(Collections.frequency(list, "a"));  // 3

List<String> other = new ArrayList<>();
Collections.addAll(other, "x", "y");
System.out.println(Collections.disjoint(list, other));  // true，无交集
```

### 2.8 不可变集合 unmodifiableXxx

返回一个**只读视图**，调用修改方法会抛 `UnsupportedOperationException`。

```java
List<String> list = new ArrayList<>();
Collections.addAll(list, "a", "b", "c");
List<String> readOnly = Collections.unmodifiableList(list);
// readOnly.add("d");   // ❌ 抛 UnsupportedOperationException
// readOnly.set(0, "z"); // ❌ 同样抛异常
```

> 📌 **开发规范**：配置类、常量集合应包装成不可变集合，防止他人误改。如系统支持的支付方式列表，一旦初始化就不应再变。

### 2.9 线程安全集合 synchronizedXxx

把普通 ArrayList/HashMap 包装成**线程安全**的集合（每个方法加 synchronized）。

```java
List<String> list = Collections.synchronizedList(new ArrayList<>());
// ✅ 多线程下 add/get 安全（但迭代时仍需手动加锁）
```

> ⚠️ `synchronizedList` 只保证**单个操作**原子，复合操作（如「先判断再添加」）仍需外部加锁。并发场景推荐直接用 `java.util.concurrent` 下的 `CopyOnWriteArrayList`、`ConcurrentHashMap`。

### 2.10 空集合与单元素集合 emptyXxx / singletonXxx

```java
List<Object> empty = Collections.emptyList();   // ✅ 返回全局共享的空 List（不可变）
Set<String> one = Collections.singleton("only"); // ✅ 只含一个元素的不可变 Set

// 常用于返回值，避免返回 null
public List<String> getNames() {
    // return null;          // ❌ 调用方还要判空
    return Collections.emptyList();  // ✅ 安全，调用方直接遍历不报错
}
```

> 💡 `emptyList()`、`emptyMap()`、`emptySet()` 返回的是**全局共享的不可变空对象**，不会每次 new，性能好。

---

## 三、Comparable 接口（自然排序）⭐⭐

`Comparable` 是「自己跟别人比」的接口。一个类实现它，就定义了该类的**固有排序规则**，称为**自然排序**。

### 3.1 compareTo 方法

```java
public interface Comparable<T> {
    int compareTo(T o);
}
```

返回值含义（记住「this 减 o」）：

| 返回值 | 含义 | 排序结果 |
| :---: | :--- | :--- |
| 负数 | this < o | this 排前面 |
| 0 | this == o | 相等 |
| 正数 | this > o | this 排后面 |

### 3.2 实现示例

```java
public class Student implements Comparable<Student> {
    String name;
    int score;

    public Student(String name, int score) {
        this.name = name;
        this.score = score;
    }

    @Override
    public int compareTo(Student o) {
        return this.score - o.score;  // ✅ 按分数升序
    }

    @Override
    public String toString() {
        return name + ":" + score;
    }
}
```

```java
List<Student> students = new ArrayList<>();
students.add(new Student("张三", 85));
students.add(new Student("李四", 92));
students.add(new Student("王五", 78));

Collections.sort(students);   // ✅ 调用自然排序（按分数升序）
System.out.println(students); // [王五:78, 张三:85, 李四:92]
```

### 3.3 JDK 内置实现

`String`、所有包装类（`Integer`/`Double`/...）都实现了 `Comparable`，所以可以直接 `sort`：

```java
System.out.println("a".compareTo("b"));  // -1，a < b
System.out.println("b".compareTo("a"));  // 1
System.out.println(Integer.valueOf(3).compareTo(5));  // -2，负数表示 3 < 5
```

> ⚠️ **一个类只能定义一种自然排序**。如果 Student 既想按分数排、又想按姓名排，自然排序只能选一个（通常是「最常用」的那个），其他排序需求交给 `Comparator`。

---

## 四、Comparator 接口（定制排序）⭐⭐

`Comparator` 是「第三方裁判」接口：当对象本身没有自然顺序，或你想用**另一种**规则排序时，单独写一个比较器。

### 4.1 compare 方法

```java
@FunctionalInterface
public interface Comparator<T> {
    int compare(T o1, T o2);
}
```

返回值含义和 `compareTo` 一致：负数表示 o1 排前面。

### 4.2 使用示例

```java
// Student 不实现 Comparable，改用外部 Comparator
List<Student> students = new ArrayList<>();
students.add(new Student("张三", 85));
students.add(new Student("李四", 92));
students.add(new Student("王五", 78));

// ✅ 按分数降序
Collections.sort(students, new Comparator<Student>() {
    @Override
    public int compare(Student s1, Student s2) {
        return s2.score - s1.score;  // 降序：s2 - s1
    }
});
System.out.println(students);  // [李四:92, 张三:85, 王五:78]
```

### 4.3 用于 TreeSet / TreeMap 定制排序

`TreeSet` 和 `TreeMap` 底层是红黑树，元素必须有序。当元素没实现 `Comparable`，或想覆盖自然排序时，构造时传入 `Comparator`：

```java
// TreeSet 按字符串长度排序（而非字典序）
Set<String> set = new TreeSet<>(new Comparator<String>() {
    @Override
    public int compare(String s1, String s2) {
        int len = s1.length() - s2.length();
        return len != 0 ? len : s1.compareTo(s2);  // 长度相同再按字典序
    }
});
Collections.addAll(set, "apple", "hi", "cat", "banana");
System.out.println(set);  // [hi, cat, apple, banana]
```

> ⚠️ **TreeSet 的陷阱**：如果 Comparator 只比较长度，两个长度相同的元素会被当成「相等」而丢弃。上面的代码特意加了 `s1.compareTo(s2)` 兜底，否则 "cat" 和 "dog" 只能存进去一个。

---

## 五、Comparator 链式 API（Java 8）

Java 8 给 `Comparator` 加了一组静态/默认方法，可以优雅地实现**多字段排序**：

| 方法 | 作用 |
| :--- | :--- |
| `comparing(keyExtractor)` | 提取排序键 |
| `thenComparing(keyExtractor)` | 主键相同时按次键排 |
| `reversed()` | 反转整个比较器 |
| `nullsFirst/nullsLast` | 处理 null 值 |

```java
List<Student> students = new ArrayList<>();
students.add(new Student("张三", 85));
students.add(new Student("李四", 92));
students.add(new Student("王五", 85));
students.add(new Student("赵六", 92));

// ✅ 先按分数降序，分数相同按姓名升序
students.sort(Comparator.comparing(Student::getScore)   // 主键：分数
        .reversed()                                        // 降序
        .thenComparing(Student::getName));                 // 次键：姓名
System.out.println(students);
// [李四:92, 赵六:92, 张三:85, 王五:85]
```

> 💡 注意 `reversed()` 的位置：它反转的是**前面已构造的比较器**。`comparing(score).reversed()` 表示分数降序；如果写在最后则反转整个链。容易写错，建议调试确认。

---

## 六、Comparable vs Comparator 对比

| 对比项 | Comparable | Comparator |
| :--- | :--- | :--- |
| 所属包 | java.lang | java.util |
| 方法 | `compareTo(T o)` | `compare(T o1, T o2)` |
| 比较者 | 自己跟别人比（this vs o） | 第三方比较两个对象 |
| 实现方式 | 修改类本身（implements） | 外部单独定义 |
| 排序规则数 | 一个类只能定义一种 | 可定义任意多种 |
| 调用方式 | `Collections.sort(list)` | `Collections.sort(list, cmp)` |
| 适用场景 | 类的固有/默认排序 | 临时排序、多字段、无法改类源码时 |

> 💡 **一句话记忆**：`Comparable` 是「我自带排序规则」（内置），`Comparator` 是「我临时指定排序规则」（外置）。

---

## 七、排序稳定性

**稳定性**：相等元素排序后是否保持原相对顺序。

- **稳定排序**：相等元素的相对顺序不变。Java 中 `Collections.sort` / `List.sort` 用的是 **TimSort**（归并排序变种），是**稳定**的。
- **不稳定排序**：相等元素顺序可能变。`TreeSet` 基于红黑树，不保证稳定。

```java
// Student 按分数排，分数相同应保持原顺序（稳定）
List<Student> list = new ArrayList<>();
list.add(new Student("A", 80));
list.add(new Student("B", 90));
list.add(new Student("C", 80));   // C 和 A 同分
list.add(new Student("D", 90));

list.sort(Comparator.comparing(Student::getScore));
// 稳定排序结果：A(80) 在 C(80) 前，B(90) 在 D(90) 前
System.out.println(list);  // [A:80, C:80, B:90, D:90]
```

> 📌 **开发规范**：涉及多字段排序时，利用稳定性可以简化代码——先按次要字段排，再按主要字段排，最终主要字段相同者会保持次要字段的顺序。但更推荐显式用 `thenComparing`，意图更清晰。

---

## ⚠️ 重点

### 重点 1：Collections 与 Collection 别搞混 ⭐

```java
Collection<String> c = new ArrayList<>();   // ✅ 接口，声明变量
Collections.sort(list);                       // ✅ 工具类，调用静态方法
// Collection.sort(list);   // ❌ 接口没有静态 sort 方法
```

### 重点 2：compareTo 返回值方向 ⭐⭐

最常见的错误是搞反升降序。口诀：**`this - o` 升序，`o - this` 降序**。

```java
// 升序
public int compareTo(Student o) {
    return this.score - o.score;   // this 小返回负数 → this 排前
}
// 降序
public int compareTo(Student o) {
    return o.score - this.score;   // 反过来
}
```

> ⚠️ 用减法有**整数溢出**风险：两个相差极大的 int 相减可能溢出。生产代码推荐用 `Integer.compare(a, b)`：`return Integer.compare(this.score, o.score);`

### 重点 3：TreeSet 比较器返回 0 会丢元素 ⭐⭐

```java
Set<Student> set = new TreeSet<>((s1, s2) -> s1.score - s2.score);
set.add(new Student("A", 80));
set.add(new Student("B", 80));   // ❌ 与 A 比较返回 0，被当成重复元素丢弃！
System.out.println(set.size());  // 1
```

> ⚠️ TreeSet/TreeMap 判重**只看 Comparator 返回 0**，与 `equals` 无关。比较器必须区分所有「业务上不同」的对象。

### 重点 4：Comparator 链中 reversed 的作用域 ⭐

```java
// ✅ 只反转分数
Comparator.comparing(Student::getScore).reversed()
          .thenComparing(Student::getName)   // 姓名仍是升序

// ❌ 反转整个链（姓名也变降序）
Comparator.comparing(Student::getScore)
          .thenComparing(Student::getName)
          .reversed()
```

### 重点 5：不可变集合的「视图」特性 ⭐

`unmodifiableList` 返回的是原集合的**视图**，原集合改动仍会反映到只读视图上：

```java
List<String> list = new ArrayList<>(Arrays.asList("a", "b"));
List<String> readOnly = Collections.unmodifiableList(list);
list.add("c");                  // 改原集合
System.out.println(readOnly);   // [a, b, c]  只读视图也变了！
// readOnly.add("d");           // ❌ 仍不能通过 readOnly 改
```

> 💡 若要彻底独立，应先复制再包装：`Collections.unmodifiableList(new ArrayList<>(list));`

---

## 💻 实战案例

### 案例 1：电商商品多字段排序 ⭐⭐

商品列表先按价格升序，价格相同按销量降序，销量也相同按好评率降序：

```java
public class Product {
    String name;
    double price;
    int sales;
    double rating;   // 好评率 0~5

    public Product(String name, double price, int sales, double rating) {
        this.name = name;
        this.price = price;
        this.sales = sales;
        this.rating = rating;
    }

    public double getPrice() { return price; }
    public int getSales() { return sales; }
    public double getRating() { return rating; }

    @Override
    public String toString() {
        return name + "(¥" + price + ",销" + sales + ",评" + rating + ")";
    }
}
```

```java
List<Product> products = new ArrayList<>();
products.add(new Product("手机", 2999, 500, 4.8));
products.add(new Product("耳机", 299, 2000, 4.9));
products.add(new Product("手机壳", 299, 8000, 4.5));   // 与耳机同价
products.add(new Product("充电器", 299, 8000, 4.7));   // 同价同销量

// ✅ 价格升序 → 销量降序 → 好评降序
products.sort(Comparator
        .comparingDouble(Product::getPrice)            // 价格升序
        .thenComparing(Product::getSales, Comparator.reverseOrder())  // 销量降序
        .thenComparing(Product::getRating, Comparator.reverseOrder()));// 好评降序

for (Product p : products) {
    System.out.println(p);
}
// 耳机(¥299.0,销2000,评4.9)
// 充电器(¥299.0,销8000,评4.7)   ← 销量更高排前
// 手机壳(¥299.0,销8000,评4.5)   ← 同销量，好评低的排后
// 手机(¥2999.0,销500,评4.8)
```

> 📌 **真实场景**：电商搜索结果页的「综合排序」就是多字段加权，规则比这复杂得多，但底层都是 Comparator 的组合。

### 案例 2：抽奖系统——shuffle 随机抽取 ⭐

```java
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class Lottery {
    public static void main(String[] args) {
        List<String> users = new ArrayList<>();
        Collections.addAll(users, "用户A", "用户B", "用户C", "用户D", "用户E", "用户F");

        // ✅ 打乱后取前 3 名为中奖者
        Collections.shuffle(users);
        List<String> winners = users.subList(0, 3);
        System.out.println("一等奖：" + winners.get(0));
        System.out.println("二等奖：" + winners.get(1));
        System.out.println("三等奖：" + winners.get(2));
    }
}
```

> 💡 生产环境抽奖通常还要记录随机种子、时间戳，便于审计和复现。`Collections.shuffle(list, new Random(seed))` 固定种子可复现结果。

### 案例 3：求班级最高分与最低分

```java
List<Integer> scores = new ArrayList<>();
Collections.addAll(scores, 78, 95, 62, 88, 71, 100, 55);

int max = Collections.max(scores);
int min = Collections.min(scores);
System.out.println("最高分：" + max);  // 100
System.out.println("最低分：" + min);  // 55
```

### 案例 4：不可变集合做系统配置 ⭐

系统支持的支付方式一旦启动就不应被修改，用不可变集合保护：

```java
public class PayConfig {
    // ✅ 全局不可变，防止任何代码误改
    public static final List<String> SUPPORTED_PAY =
            Collections.unmodifiableList(
                    new ArrayList<>(java.util.Arrays.asList("ALIPAY", "WECHAT", "UNIONPAY")));

    public static void main(String[] args) {
        System.out.println(SUPPORTED_PAY);
        // SUPPORTED_PAY.add("BANK");  // ❌ 抛异常，配置被保护
    }
}
```

### 案例 5：统计关键词出现频率

后台系统统计日志中各错误关键词出现次数，用 `frequency`：

```java
List<String> logs = new ArrayList<>();
Collections.addAll(logs, "TIMEOUT", "NPE", "TIMEOUT", "OOM", "NPE", "TIMEOUT");

System.out.println("TIMEOUT 出现：" + Collections.frequency(logs, "TIMEOUT"));  // 3
System.out.println("NPE 出现：" + Collections.frequency(logs, "NPE"));          // 2
System.out.println("OOM 出现：" + Collections.frequency(logs, "OOM"));          // 1
```

### 案例 6：金融系统按金额对账单排序

```java
public class Bill implements Comparable<Bill> {
    String id;
    long amount;   // 金额（分），避免浮点误差

    public Bill(String id, long amount) {
        this.id = id;
        this.amount = amount;
    }

    @Override
    public int compareTo(Bill o) {
        // ✅ 用 Long.compare 避免溢出
        return Long.compare(this.amount, o.amount);
    }

    @Override
    public String toString() {
        return id + ":" + (amount / 100.0) + "元";
    }
}
```

```java
List<Bill> bills = new ArrayList<>();
bills.add(new Bill("B001", 12500));   // 125 元
bills.add(new Bill("B002", 9900));    // 99 元
bills.add(new Bill("B003", 880000));  // 8800 元

Collections.sort(bills);   // ✅ 自然排序：按金额升序
bills.forEach(System.out::println);
// B002:99.0元
// B001:125.0元
// B003:8800.0元
```

> 📌 **金融规范**：金额用 `long` 存「分」或用 `BigDecimal`，绝不用 `double`。比较时用 `Long.compare` / `BigDecimal.compareTo`，避免减法溢出。

---

## 🚀 新版本补充

### Java 9：List.of / Map.of 不可变集合

Java 9 提供了更简洁的创建**真正不可变**集合的工厂方法，替代 `Collections.unmodifiableList` + `Arrays.asList` 的繁琐写法：

```java
// Java 8 写法
List<String> old = Collections.unmodifiableList(new ArrayList<>(Arrays.asList("a", "b")));

// Java 9+ 写法
List<String> list = List.of("a", "b", "c");   // 不可变，add 抛异常
Set<String> set = Set.of("x", "y");
Map<String, Integer> map = Map.of("a", 1, "b", 2);

// list.add("d");  // ❌ UnsupportedOperationException
```

> ⚠️ `List.of` 与 `Arrays.asList` 的关键区别：前者**完全不可变**，后者只是固定大小（`set` 可以，`add` 抛异常）。

### Java 9：List.copyOf 防御性拷贝

```java
List<String> original = new ArrayList<>(Arrays.asList("a", "b"));
List<String> copy = List.copyOf(original);   // 不可变副本
original.add("c");
System.out.println(copy);   // [a, b]，原集合改动不影响副本
```

### Java 10+：不可变集合收集

```java
// Java 10 起，Stream 可直接收集为不可变集合
List<String> immutable = stream.toList();   // Java 16 正式
// Java 8 只能 Collectors.toUnmodifiableList()（Java 10）
```

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Collections vs Collection | 工具类（静态方法） vs 接口（集合根） |
| addAll | 批量添加，比循环 add 简洁 |
| shuffle | 随机打乱，用于抽奖/洗牌 |
| sort(List) | 自然排序，需实现 Comparable |
| sort(List, Comparator) | 定制排序 |
| reverse / swap | 反转 / 交换指定位置 |
| max / min | 求极值，可传 Comparator |
| frequency / disjoint | 出现次数 / 是否无交集 |
| unmodifiableXxx | 返回不可变视图 |
| synchronizedXxx | 返回线程安全包装 |
| emptyXxx / singletonXxx | 空 / 单元素不可变集合 |
| Comparable | 自然排序，compareTo，一个类一种规则 |
| Comparator | 定制排序，compare，可定义多种 |
| 链式 API | comparing → thenComparing → reversed |
| 排序稳定性 | TimSort 稳定；TreeSet 不保证稳定 |

---

## 学习建议

1. **先区分两个名字**：把 `Collections`（工具类，带 s）和 `Collection`（接口）彻底分清，这是后续所有集合代码的基础，混淆会寸步难行。
2. **手写 Comparable 和 Comparator 各一遍**：找个 Student/Product 类，先让它 implements Comparable 按分数排，再写一个外部 Comparator 按姓名排，亲手敲一遍比看十遍都管用。
3. **重点练多字段排序**：电商场景的「价格升序 + 销量降序 + 好评降序」是面试和开发高频题，务必用 `comparing().thenComparing().reversed()` 链式写法练熟，注意 `reversed()` 的作用域。
4. **警惕 TreeSet 返回 0 丢元素**：这是最隐蔽的 bug，比较器一定要能区分所有业务上不同的对象，不能只比单个字段。
5. **不可变集合要会用**：配置、常量、方法返回值都推荐用不可变集合保护，Java 8 用 `Collections.unmodifiableXxx`，Java 9+ 优先用 `List.of` / `Map.of`，养成「不该变的就锁死」的习惯。
