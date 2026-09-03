# 集合框架体系与 Collection

Java 集合是存放对象的「容器」，类似仓库货架——区别于数组的是，集合的容量可动态伸缩、能存任意类型对象、提供丰富的增删查改方法。几乎所有业务代码都离不开集合：购物车、订单列表、用户标签、缓存数据……掌握集合框架是 Java 工程师的必修课。

> 💡 在阅读本篇前，建议先回顾 [04-数据类型与类型转换](04-数据类型与类型转换.md) 中「引用类型」一节，理解对象存于堆、变量存地址的概念，会更容易理解集合存储的是对象引用而非对象本身。

---

## 一、集合的由来

### 1.1 数组的局限性

数组是 Java 最基本的数据容器，但它有明显短板：

```java
// 数组的痛点：长度固定、类型单一
String[] arr = new String[3];
arr[0] = "商品A";
arr[1] = "商品B";
arr[2] = "商品C";
// arr[3] = "商品D";  // ❌ ArrayIndexOutOfBoundsException，长度写死了

// 想加第 4 个商品？只能新建数组再拷贝
String[] newArr = new String[4];
System.arraycopy(arr, 0, newArr, 0, arr.length);
newArr[3] = "商品D";
```

数组的三大痛点：

| 痛点 | 说明 |
| :--- | :--- |
| 长度固定 | 初始化后容量不可变，增删元素需手动扩容拷贝 |
| 类型单一 | 同一数组只能存同一类型（虽可存 Object 但失去类型安全） |
| 方法匮乏 | 只有 `length` 属性和索引访问，增删查改全靠手写 |

### 1.2 集合的诞生

集合框架（Collections Framework）就是为了解决数组的痛点而生：**自动扩容、丰富 API、多种数据结构（线性表、链表、哈希表、树）**，开发者无需关心底层如何搬运数据。

```java
import java.util.ArrayList;
import java.util.List;

// ✅ 集合：容量自动伸缩，API 丰富
List<String> list = new ArrayList<>();
list.add("商品A");
list.add("商品B");
list.add("商品C");
list.add("商品D");   // ✅ 无需关心容量，自动扩容
System.out.println(list.size());  // 4
list.remove("商品B");  // ✅ 一行删除
System.out.println(list);  // [商品A, 商品C, 商品D]
```

> 💡 集合只能存**对象**，不能存基本类型。存 `int` 时会自动装箱为 `Integer`（详见 [19-包装类](19-包装类Integer与自动装箱拆箱.md)）。

---

## 二、集合框架体系图 ⭐⭐

Java 集合框架分两大体系：**Collection（单列）** 和 **Map（双列）**。这是整个集合体系的总纲，务必牢记。

```
Collection（单列集合，存一个个对象）
├── List（有序、有索引、允许重复）
│   ├── ArrayList      // 数组实现，查询快，最常用
│   ├── LinkedList     // 链表实现，增删快
│   └── Vector         // 数组实现，线程安全（已淘汰）
└── Set（无序、无索引、不允许重复）
    ├── HashSet        // 哈希表实现，最常用
    ├── LinkedHashSet  // 哈希表 + 链表，保持插入顺序
    └── TreeSet        // 红黑树实现，自动排序

Map（双列集合，存 key-value 键值对）
├── HashMap           // 哈希表实现，最常用
├── LinkedHashMap     // 哈希表 + 链表，保持插入顺序
└── TreeMap           // 红黑树实现，按 key 排序
```

### 2.1 两大体系对比

| 特性 | Collection | Map |
| :--- | :--- | :--- |
| 存储结构 | 单列，存一个个对象 | 双列，存 key-value 对 |
| 继承关系 | 继承 `Iterable`，可迭代 | 独立接口，不继承 Collection |
| 典型实现 | ArrayList、HashSet | HashMap、TreeMap |
| 适用场景 | 一组数据（用户列表、商品列表） | 映射关系（配置项、字典、计数） |

> ⚠️ 注意：`Map` **不是** `Collection` 的子接口，二者是平行的两大体系。但 Map 也提供了 `keySet()`、`values()`、`entrySet()` 方法，可以转成 Collection 来遍历。

### 2.2 接口与实现的关系

集合框架采用「接口 + 实现」分离设计，同一接口有多种实现，开发者按需选择：

```java
// 接口引用指向实现类——面向接口编程（开发规范）
List<String> list = new ArrayList<>();   // ✅ 推荐
// ArrayList<String> list = new ArrayList<>();  // ⚠️ 不推荐，写死实现类

// 想换实现？改一行即可
List<String> list2 = new LinkedList<>();  // ✅ 切换为链表，上层代码无需改动
```

> 📌 **开发规范**：变量声明一律用接口类型（`List`、`Set`、`Map`），实例化时才指定实现类。这样切换实现只改一行，符合「面向接口编程」原则。

---

## 三、Collection 接口通用方法

`Collection` 是所有单列集合的根接口，定义了通用的增删查改方法。**List、Set、Queue 都继承自它**，所以下面这些方法所有单列集合都能用。

### 3.1 增删改查方法

```java
import java.util.ArrayList;
import java.util.Collection;

Collection<String> c = new ArrayList<>();

// —— 增 ——
c.add("Java");            // 添加元素
c.add("Python");
c.add("Go");
System.out.println(c);     // [Java, Python, Go]

Collection<String> more = new ArrayList<>();
more.add("Rust");
more.add("Swift");
c.addAll(more);           // 批量添加
System.out.println(c);    // [Java, Python, Go, Rust, Swift]

// —— 删 ——
c.remove("Go");           // 删除指定元素（依赖 equals）
System.out.println(c);    // [Java, Python, Rust, Swift]
c.removeAll(more);        // 批量删除（移除交集）
System.out.println(c);    // [Java, Python]

// —— 查 ——
System.out.println(c.contains("Java"));   // true，是否包含
System.out.println(c.contains("C++"));    // false
System.out.println(c.containsAll(more));  // false，是否包含全部
System.out.println(c.isEmpty());          // false，是否为空
System.out.println(c.size());             // 2，元素个数

// —— 清空 ——
c.clear();
System.out.println(c);    // []
System.out.println(c.size());  // 0
```

### 3.2 转数组方法

```java
Collection<String> c = new ArrayList<>();
c.add("A");
c.add("B");
c.add("C");

// 方式 1：转 Object[]
Object[] arr1 = c.toArray();
System.out.println(Arrays.toString(arr1));  // [A, B, C]

// 方式 2：转指定类型数组（推荐）
String[] arr2 = c.toArray(new String[0]);
System.out.println(arr2[0]);  // A
```

> 💡 `toArray(new String[0])` 是惯用写法，传入长度为 0 的数组让集合自己分配合适大小。如果传入的数组够大，元素会直接填入该数组。

### 3.3 方法速查表

| 方法 | 说明 | 返回值 |
| :--- | :--- | :--- |
| `add(E e)` | 添加元素 | boolean |
| `addAll(Collection c)` | 批量添加 | boolean |
| `remove(Object o)` | 删除元素（依赖 equals） | boolean |
| `removeAll(Collection c)` | 批量删除（移除交集） | boolean |
| `retainAll(Collection c)` | 取交集（保留交集） | boolean |
| `contains(Object o)` | 是否包含 | boolean |
| `containsAll(Collection c)` | 是否全包含 | boolean |
| `isEmpty()` | 是否为空 | boolean |
| `size()` | 元素个数 | int |
| `clear()` | 清空 | void |
| `toArray()` | 转数组 | Object[] |
| `iterator()` | 获取迭代器 | Iterator |

---

## 四、集合的遍历方式

集合有四种主流遍历方式，各有适用场景。

### 4.1 迭代器 Iterator

最底层的遍历方式，所有 Collection 都支持。**唯一能在遍历中安全删除元素的方式**。

```java
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;

Collection<String> c = new ArrayList<>();
c.add("Java");
c.add("Python");
c.add("Go");

Iterator<String> it = c.iterator();
while (it.hasNext()) {           // 是否有下一个
    String s = it.next();        // 取出下一个
    System.out.println(s);
}
// Java
// Python
// Go
```

> ⚠️ 每次调用 `iterator()` 都会生成一个**新的迭代器**，迭代器内部维护一个游标 cursor，记录当前遍历到哪个位置。

### 4.2 增强 for 循环（foreach）

语法糖，底层其实就是迭代器，代码更简洁：

```java
for (String s : c) {
    System.out.println(s);
}
```

> ⚠️ 增强 for **不能**在遍历中用 `c.remove()` 删除元素，会抛 `ConcurrentModificationException`。要删除只能用迭代器的 `it.remove()`（详见 [25-List](25-List：ArrayList与LinkedList.md)）。

### 4.3 Java 8 forEach + Lambda

```java
// Java 8 新增的 forEach 方法，配合 Lambda
c.forEach(s -> System.out.println(s));
// 方法引用更简洁
c.forEach(System.out::println);
```

### 4.4 Java 8 Stream 流

```java
// 流式遍历 + 过滤 + 操作
c.stream()
 .filter(s -> s.length() > 2)
 .forEach(System.out::println);  // Java, Python
```

### 4.5 四种方式对比

| 方式 | 简洁度 | 能否删除元素 | 适用场景 |
| :--- | :---: | :---: | :--- |
| 迭代器 | 一般 | ✅ `it.remove()` | 遍历中需删除元素 |
| 增强 for | 高 | ❌ | 只读遍历 |
| forEach + Lambda | 高 | ❌ | 只读遍历（Java 8+） |
| Stream | 高 | ❌ | 过滤、映射、统计等链式操作 |

> 💡 **选择建议**：只读遍历用增强 for 或 forEach；遍历中删除元素用迭代器；需要过滤/统计用 Stream。

---

## 五、存储自定义对象时重写 equals 和 hashCode ⭐⭐

这是集合最易踩坑的点。集合的 `contains`、`remove` 等方法都依赖 `equals` 判断元素是否相等，而 `HashSet`/`HashMap` 还依赖 `hashCode` 定位元素位置。

### 5.1 不重写 equals 的后果

```java
import java.util.ArrayList;
import java.util.Collection;

class User {
    String name;
    int age;
    User(String name, int age) { this.name = name; this.age = age; }
    // ❌ 没有重写 equals，默认用 == 比较地址
}

Collection<User> users = new ArrayList<>();
users.add(new User("张三", 25));

// ❌ 问题来了：contains 返回 false！
System.out.println(users.contains(new User("张三", 25)));  // false
// 原因：两个 new User("张三", 25) 是不同对象，地址不同，equals 默认比地址
```

### 5.2 重写 equals 和 hashCode 后

```java
import java.util.Objects;

class User {
    String name;
    int age;
    User(String name, int age) { this.name = name; this.age = age; }

    // ✅ 重写 equals：按 name 和 age 判断相等
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return age == user.age && Objects.equals(name, user.name);
    }

    // ✅ 重写 hashCode：equals 相等的对象 hashCode 必须相同
    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }
}

Collection<User> users = new ArrayList<>();
users.add(new User("张三", 25));
System.out.println(users.contains(new User("张三", 25)));  // ✅ true
System.out.println(users.remove(new User("张三", 25)));   // ✅ true
System.out.println(users.size());  // 0
```

> ⚠️ **铁律**：重写 `equals` 必须同时重写 `hashCode`！否则 HashSet/HashMap 中会出现「equals 相等但 hashCode 不同」的对象，导致元素丢失。这是 Java 规范要求，IDE 可一键生成。

> 📌 **规范**：用 IDE（IDEA 快捷键 Alt+Insert）自动生成 equals 和 hashCode，不要手写，避免遗漏字段。

---

## 六、Collection 与 Collections 的区别

名字相似但完全不同，面试常考：

```java
import java.util.Collections;
import java.util.ArrayList;
import java.util.List;

// Collection：接口，是单列集合的根接口
// Collections：工具类，提供静态方法操作集合

List<Integer> list = new ArrayList<>();
list.add(3);
list.add(1);
list.add(2);

// Collections 是工具类，全是静态方法
Collections.sort(list);              // 排序
System.out.println(list);           // [1, 2, 3]
Collections.reverse(list);          // 反转
System.out.println(list);           // [3, 2, 1]
Collections.shuffle(list);          // 随机打乱
System.out.println(Collections.max(list));  // 3，最大值
System.out.println(Collections.min(list));  // 1，最小值

// Collections 还能返回线程安全的集合（底层加 synchronized）
List<Integer> syncList = Collections.synchronizedList(new ArrayList<>());
```

| 对比项 | Collection | Collections |
| :--- | :--- | :--- |
| 性质 | 接口 | 工具类 |
| s 结尾 | 无 s | 有 s |
| 作用 | 定义集合的通用方法 | 提供操作集合的静态工具方法 |
| 典型方法 | add、remove、contains | sort、reverse、shuffle、synchronizedList |

> 💡 **记忆口诀**：带 `s` 的是工具类（Collections 工具类，Arrays 工具类，Objects 工具类），不带 `s` 的是接口/类。

---

## ⚠️ 重点

### 重点 1：集合存的是对象引用，不是对象本身 ⭐⭐

```java
List<StringBuilder> list = new ArrayList<>();
StringBuilder sb = new StringBuilder("hello");
list.add(sb);

sb.append(" world");           // 修改了原对象
System.out.println(list.get(0));  // hello world，集合里的也变了！
// 原因：集合存的是 sb 的引用，指向堆中同一个对象
```

> ⚠️ 集合存的是**引用地址**，修改原对象，集合里的内容也跟着变。要存「快照」需深拷贝。

### 重点 2：集合只能存对象，不能存基本类型 ⭐

```java
// ✅ 集合存包装类型
List<Integer> list = new ArrayList<>();
list.add(1);    // 自动装箱：int → Integer
list.add(2);

// ❌ 不能这样
// List<int> bad = new ArrayList<>();  // 编译错误：泛型不能是基本类型
```

> ⚠️ 自动装箱有性能开销。大量添加基本类型时（如循环 add 100 万个 int），装箱会消耗额外内存和时间，可考虑用 `IntStream` 或基本类型数组。

### 重点 3：contains/remove 依赖 equals ⭐⭐⭐

```java
List<String> list = new ArrayList<>();
list.add("Java");
list.add("Python");

// String 重写了 equals，按内容比较
System.out.println(list.contains("Java"));   // ✅ true
System.out.println(list.remove("Java"));    // ✅ true

// 自定义对象不重写 equals，contains/remove 全部失效
List<User> users = new ArrayList<>();
users.add(new User("张三", 25));  // User 未重写 equals
System.out.println(users.contains(new User("张三", 25)));  // ❌ false
```

> 📌 **铁律**：自定义类放入集合前，必须重写 equals 和 hashCode（尤其 HashSet/HashMap）。这是开发中最易忽略的 bug 来源。

### 重点 4：集合与数组的选择 ⭐

| 场景 | 推荐容器 | 原因 |
| :--- | :--- | :--- |
| 长度已知、基本类型、性能敏感 | 数组 | 无装箱开销、无扩容开销 |
| 长度可变、需要增删查改 | 集合 | API 丰富、自动扩容 |
| 元素不重复 | Set | 自动去重 |
| 键值映射 | Map | 天然映射结构 |
| 有序有索引 | List | 支持索引访问 |

### 重点 5：泛型约束元素类型 ⭐⭐

```java
// ✅ 泛型约束，编译期类型检查
List<String> list = new ArrayList<>();
list.add("Java");
// list.add(123);  // ❌ 编译错误，只能存 String
String s = list.get(0);  // ✅ 无需强转

// ⚠️ 裸集合（不写泛型）默认存 Object，丢失类型安全
List rawList = new ArrayList();
rawList.add("Java");
rawList.add(123);     // ✅ 能编译，但取出来是 Object，运行时易 ClassCastException
String str = (String) rawList.get(1);  // ❌ 运行时 ClassCastException
```

> 📌 **规范**：集合声明一律加泛型，禁止使用裸类型（raw type），这是阿里巴巴 Java 开发规约的明确要求。

---

## 💻 实战案例

### 案例 1：电商购物车（List 存商品）⭐⭐

```java
import java.util.ArrayList;
import java.util.List;

class Product {
    String id;
    String name;
    double price;
    int quantity;

    Product(String id, String name, double price, int quantity) {
        this.id = id;
        this.name = name;
        this.price = price;
        this.quantity = quantity;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Product p = (Product) o;
        return id.equals(p.id);  // 同 id 视为同一商品
    }

    @Override
    public int hashCode() {
        return id.hashCode();
    }

    @Override
    public String toString() {
        return name + " x" + quantity + " = " + (price * quantity) + "元";
    }
}

public class ShoppingCart {
    private List<Product> cart = new ArrayList<>();

    // 加入购物车：相同商品累加数量
    public void addToCart(Product p) {
        int idx = cart.indexOf(p);  // 依赖 equals
        if (idx >= 0) {
            Product existing = cart.get(idx);
            existing.quantity += p.quantity;  // 累加数量
        } else {
            cart.add(p);
        }
    }

    // 从购物车移除
    public void removeFromCart(String productId) {
        cart.remove(new Product(productId, "", 0, 0));  // 依赖 equals
    }

    // 计算总价
    public double getTotal() {
        double total = 0;
        for (Product p : cart) {
            total += p.price * p.quantity;
        }
        return total;
    }

    // 展示购物车
    public void showCart() {
        System.out.println("=== 购物车 ===");
        cart.forEach(System.out::println);
        System.out.println("总计：" + getTotal() + "元");
    }

    public static void main(String[] args) {
        ShoppingCart cart = new ShoppingCart();
        cart.addToCart(new Product("P001", "Java编程思想", 108.0, 1));
        cart.addToCart(new Product("P002", "机械键盘", 399.0, 1));
        cart.addToCart(new Product("P001", "Java编程思想", 108.0, 2));  // 同 id，累加
        cart.showCart();
        // === 购物车 ===
        // Java编程思想 x3 = 324.0元
        // 机械键盘 x1 = 399.0元
        // 总计：723.0元

        cart.removeFromCart("P002");
        cart.showCart();
        // === 购物车 ===
        // Java编程思想 x3 = 324.0元
        // 总计：324.0元
    }
}
```

> 💡 这个案例体现了 `indexOf`、`remove` 依赖 `equals` 的实际价值：重写后，按 `id` 判断同一商品，购物车才能正确累加/移除。

### 案例 2：用户标签去重（Set）⭐

```java
import java.util.HashSet;
import java.util.Set;

public class UserTags {
    public static void main(String[] args) {
        // 后台系统：给用户打标签，自动去重
        Set<String> tags = new HashSet<>();

        // 从多个来源收集标签
        tags.add("VIP");
        tags.add("活跃用户");
        tags.add("高消费");
        tags.add("VIP");       // 重复，自动忽略
        tags.add("活跃用户");   // 重复，自动忽略

        System.out.println(tags);  // [高消费, VIP, 活跃用户]（无序）
        System.out.println("标签数：" + tags.size());  // 3

        // 判断是否有某标签
        System.out.println("是否VIP：" + tags.contains("VIP"));  // true

        // 批量添加
        Set<String> more = new HashSet<>();
        more.add("新用户");
        more.add("高消费");    // 交集
        tags.addAll(more);
        System.out.println(tags);  // [高消费, VIP, 活跃用户, 新用户]

        // 取两个用户的共同标签
        Set<String> user1Tags = new HashSet<>();
        user1Tags.add("VIP");
        user1Tags.add("活跃用户");
        Set<String> user2Tags = new HashSet<>();
        user2Tags.add("VIP");
        user2Tags.add("高消费");
        user1Tags.retainAll(user2Tags);  // 取交集
        System.out.println("共同标签：" + user1Tags);  // [VIP]
    }
}
```

> 💡 Set 的 `retainAll` 方法取交集，常用于「共同好友」「共同兴趣」等场景。

### 案例 3：Collection 通用方法演示（后台数据管理）

```java
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;

public class AdminDemo {
    public static void main(String[] args) {
        // 后台系统：管理员列表管理
        Collection<String> admins = new ArrayList<>();

        // 1. 批量添加管理员
        Collections.addAll(admins, "admin01", "admin02", "admin03", "admin04");
        System.out.println("管理员：" + admins);  // [admin01, admin02, admin03, admin04]

        // 2. 查询
        System.out.println("管理员数量：" + admins.size());       // 4
        System.out.println("包含admin02：" + admins.contains("admin02"));  // true
        System.out.println("是否为空：" + admins.isEmpty());      // false

        // 3. 转数组（传给需要数组的接口）
        String[] arr = admins.toArray(new String[0]);
        System.out.println("数组：" + arr[0]);  // admin01

        // 4. 批量删除离职管理员
        Collection<String> removed = new ArrayList<>();
        removed.add("admin03");
        removed.add("admin04");
        admins.removeAll(removed);
        System.out.println("删除后：" + admins);  // [admin01, admin02]

        // 5. 只保留有权限的管理员（取交集）
        Collection<String> activeAdmins = new ArrayList<>();
        activeAdmins.add("admin01");
        activeAdmins.add("admin05");
        admins.retainAll(activeAdmins);
        System.out.println("有权限的：" + admins);  // [admin01]

        // 6. 清空
        admins.clear();
        System.out.println("清空后：" + admins);  // []
    }
}
```

### 案例 4：集合存自定义对象（学生管理系统）

```java
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.Objects;

class Student {
    String id;
    String name;
    double score;

    Student(String id, String name, double score) {
        this.id = id;
        this.name = name;
        this.score = score;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Student student = (Student) o;
        return Objects.equals(id, student.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return String.format("Student{id='%s', name='%s', score=%.1f}", id, name, score);
    }
}

public class StudentManager {
    private Collection<Student> students = new ArrayList<>();

    // 添加学生（学号不能重复）
    public boolean addStudent(Student s) {
        if (students.contains(s)) {  // 依赖 equals
            System.out.println("学号 " + s.id + " 已存在");
            return false;
        }
        students.add(s);
        return true;
    }

    // 按学号删除
    public boolean removeStudent(String id) {
        return students.remove(new Student(id, "", 0));  // 依赖 equals
    }

    // 按学号查询
    public Student findById(String id) {
        for (Student s : students) {
            if (s.id.equals(id)) {
                return s;
            }
        }
        return null;
    }

    // 统计及格人数
    public long countPassed() {
        long count = 0;
        for (Student s : students) {
            if (s.score >= 60) count++;
        }
        return count;
    }

    // Java 8 Stream 写法（更简洁）
    public long countPassedStream() {
        return students.stream().filter(s -> s.score >= 60).count();
    }

    // 展示所有学生
    public void showAll() {
        Iterator<Student> it = students.iterator();
        while (it.hasNext()) {
            System.out.println(it.next());
        }
    }

    public static void main(String[] args) {
        StudentManager mgr = new StudentManager();
        mgr.addStudent(new Student("S001", "张三", 85.5));
        mgr.addStudent(new Student("S002", "李四", 59.0));
        mgr.addStudent(new Student("S003", "王五", 72.0));
        mgr.addStudent(new Student("S001", "赵六", 90.0));  // 学号重复，添加失败

        mgr.showAll();
        System.out.println("及格人数：" + mgr.countPassed());  // 2

        mgr.removeStudent("S002");
        System.out.println("删除后及格人数：" + mgr.countPassed());  // 2
    }
}
```

> 💡 注意 `removeStudent` 中 `new Student(id, "", 0)` 的技巧：只需让 `equals` 按 id 判断相等，就能用 `remove` 删除，无需遍历查找。这就是重写 equals 的威力。

---

## 🚀 新版本补充

### Java 9：集合的不可变工厂方法

```java
// Java 9 新增 List.of / Set.of / Map.of，创建不可变集合
List<String> list = List.of("A", "B", "C");   // 不可变
Set<Integer> set = Set.of(1, 2, 3);           // 不可变
Map<String, Integer> map = Map.of("a", 1, "b", 2);  // 不可变

// list.add("D");  // ❌ UnsupportedOperationException

// ⚠️ 与 Arrays.asList 不同：List.of 不允许 null 元素
// List.of("A", null);  // ❌ NullPointerException
```

### Java 10：局部变量类型推断

```java
// Java 10 var，集合声明更简洁
var list = new ArrayList<String>();   // 推断为 ArrayList<String>
var set = Set.of(1, 2, 3);            // 推断为不可变 Set
```

> ⚠️ Java 8 环境下 `List.of` 不可用，需用 `Collections.unmodifiableList(Arrays.asList(...))` 替代。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 集合由来 | 数组长度固定、类型单一，集合解决变长存储 |
| 两大体系 | Collection（单列）、Map（双列），Map 不继承 Collection |
| Collection 体系 | List（有序可重复）、Set（无序不重复）、Queue（队列） |
| 通用方法 | add/remove/contains/size/isEmpty/clear/toArray/iterator |
| 遍历方式 | 迭代器（可删元素）、增强 for、forEach、Stream |
| equals/hashCode | 自定义对象入集合必须重写，否则 contains/remove 失效 |
| Collection vs Collections | 前者是接口，后者是工具类 |
| 泛型 | 集合必须加泛型，禁止裸类型 |

---

## 学习建议

1. **先画体系图再学细节**：把「Collection → List/Set」和「Map → HashMap/TreeMap」的体系图默写三遍，建立全局认知。后续每学一个实现类，就把它挂到体系图对应位置，不会乱。
2. **牢记 equals/hashCode 铁律**：自定义类放入集合前必须重写这两个方法。用 IDE 一键生成，养成习惯，能避免 90% 的集合相关 bug。
3. **区分四种遍历的使用场景**：只读用增强 for，删除用迭代器，链式操作用 Stream。尤其记住增强 for 中不能直接 remove，这是高频面试题。
4. **面向接口编程**：声明用 `List`、`Set`、`Map`，实例化才写 `ArrayList`、`HashSet`、`HashMap`。这是阿里规约要求，也方便切换实现。
5. **结合数组对比学习**：数组和集合各有适用场景，基本类型多、长度固定、性能敏感用数组；对象多、需增删、API 丰富用集合。理解差异才能选对容器。
