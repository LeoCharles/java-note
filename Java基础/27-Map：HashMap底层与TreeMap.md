# Map：HashMap 底层与 TreeMap

`Map` 是 Java 集合框架中用于存储**键值对（key-value）**的容器。与 `Collection` 不同，Map 不继承任何接口，独立成体系。它是开发中最高频的数据结构之一：商品缓存（id→商品）、配置项（key→value）、会话管理（sessionId→用户）……几乎所有业务系统都离不开 Map。

> 💡 在阅读本篇前，建议先看 [24-集合框架体系与Collection](24-集合框架体系与Collection.md) 了解 Map 在集合体系中的位置，以及 [26-Set](26-Set.md)——因为 HashSet 底层就是 HashMap，理解了 Set 再看 Map 会事半功倍。

---

## 一、Map 接口特点

`Map` 接口与 `Collection` 体系并列，存储的是「键值对」映射关系：

| 特点 | 说明 |
| :--- | :--- |
| **键值对存储** | 一个 entry = 一个 key + 一个 value |
| **键唯一** | key 不允许重复（重复 put 会覆盖旧 value） |
| **值可重复** | 多个 key 可以指向同一个 value |
| **一键一值** | 一个 key 只能对应一个 value（一个 value 可被多个 key 引用） |
| **无 Collection 继承** | Map 是独立接口，不继承 Collection |

```java
import java.util.HashMap;
import java.util.Map;

Map<String, Integer> map = new HashMap<>();
map.put("Java", 1);
map.put("Python", 2);
map.put("Java", 3);          // key 重复，覆盖旧值
System.out.println(map.get("Java"));  // 3（旧值 1 被覆盖）
System.out.println(map.size());       // 2（Python、Java）
```

> ⚠️ **注意**：`put` 返回的是**被覆盖的旧 value**，没有旧值则返回 `null`。这个返回值常被用来判断是否发生了覆盖。

```java
Map<String, Integer> map = new HashMap<>();
Integer old = map.put("A", 1);  // null（之前没有 A）
Integer old2 = map.put("A", 2); // 1（旧值被覆盖，返回旧值）
```

---

## 二、Map 常用方法

| 方法 | 说明 |
| :--- | :--- |
| `put(K, V)` | 添加/覆盖键值对，返回旧 value |
| `putIfAbsent(K, V)` | 仅当 key 不存在时才放入（Java 8） |
| `get(Object key)` | 按 key 取 value，不存在返回 null |
| `getOrDefault(K, V)` | 取 value，不存在返回默认值（Java 8） |
| `remove(Object key)` | 按 key 删除，返回被删的 value |
| `containsKey(Object key)` | 是否包含某 key |
| `containsValue(Object v)` | 是否包含某 value |
| `keySet()` | 返回所有 key 的 Set 视图 |
| `values()` | 返回所有 value 的 Collection 视图 |
| `entrySet()` | 返回所有键值对的 Set 视图 |
| `size()` | 键值对数量 |
| `isEmpty()` | 是否为空 |
| `clear()` | 清空 |

```java
import java.util.HashMap;
import java.util.Map;

Map<String, Integer> map = new HashMap<>();
map.put("A", 1);
map.put("B", 2);
map.put("C", 3);

map.get("A");                 // 1
map.get("D");                 // null（不存在）
map.getOrDefault("D", 0);    // 0（不存在给默认值）✅ 防空指针利器
map.containsKey("B");         // true
map.containsValue(2);         // true
map.remove("C");              // 删除 C，返回 3
map.size();                   // 2
map.isEmpty();                // false
map.clear();                  // 清空
```

> 💡 **开发建议**：取 value 时优先用 `getOrDefault`，避免拿到 null 后做运算时抛 `NullPointerException`。

---

## 三、Map.Entry 与键值对

`Map.Entry<K,V>` 是 Map 内部定义的接口，表示一个键值对条目。它提供三个核心方法：

| 方法 | 说明 |
| :--- | :--- |
| `getKey()` | 获取 key |
| `getValue()` | 获取 value |
| `setValue(V)` | 修改 value（会反映到原 Map） |

```java
import java.util.HashMap;
import java.util.Map;

Map<String, Integer> map = new HashMap<>();
map.put("A", 1);
map.put("B", 2);

// 通过 entrySet 获取每个 Entry
for (Map.Entry<String, Integer> entry : map.entrySet()) {
    String key = entry.getKey();
    Integer value = entry.getValue();
    System.out.println(key + " = " + value);

    // setValue 会直接修改 Map 中的值
    entry.setValue(value * 10);
}
System.out.println(map);  // {A=10, B=20}
```

> 💡 `entrySet()` 返回的是 Map 内部数据的「视图」，对 entry 调用 `setValue` 会直接改原 Map；但不要在遍历时 `put`/`remove`，会触发 `ConcurrentModificationException`（详见 [28-迭代器](28-迭代器与增强for.md)）。

---

## 四、Map 的遍历方式

### 4.1 方式一：keySet + get

```java
Map<String, Integer> map = new HashMap<>();
map.put("A", 1); map.put("B", 2); map.put("C", 3);

// 遍历 key，再用 get 取 value
for (String key : map.keySet()) {
    System.out.println(key + " = " + map.get(key));
}
```

> ⚠️ **性能问题**：对 HashMap 而言，`get(key)` 每次都要重新计算哈希定位桶，效率略低。对 TreeMap 更糟——每次 `get` 都是 O(log n) 查找。**不推荐在大数据量下用这种方式。**

### 4.2 方式二：entrySet + getKey/getValue（推荐）⭐

```java
// ✅ 推荐：一次拿到 key 和 value，无需二次查找
for (Map.Entry<String, Integer> entry : map.entrySet()) {
    System.out.println(entry.getKey() + " = " + entry.getValue());
}
```

> 💡 **为什么 entrySet 更高效？** 它一次遍历就同时拿到 key 和 value，不需要再用 key 去查 value。这是开发中最推荐的遍历方式。

### 4.3 方式三：Java 8 forEach + Lambda

```java
// Java 8 起，Map 提供了 forEach 方法
map.forEach((k, v) -> System.out.println(k + " = " + v));
```

### 4.4 只遍历 value

```java
// 只需要 value 时
for (Integer v : map.values()) {
    System.out.println(v);
}
```

> 📌 **遍历方式对比**：

| 方式 | 适用 | 性能 | 备注 |
| :--- | :--- | :--- | :--- |
| keySet + get | 只需 key | 一般 | HashMap 可用，TreeMap 慢 |
| entrySet | key+value 都要 | ✅ 最优 | **推荐** |
| forEach + Lambda | Java 8+ | ✅ 好 | 代码简洁 |
| values() | 只需 value | ✅ 好 | 无需 key |

---

## 五、HashMap 底层原理（重点 ⭐⭐⭐⭐）

`HashMap` 是 Map 最常用的实现，也是面试最高频考点。理解它的底层结构，是写出高性能代码和排查问题的关键。

### 5.1 JDK 1.8 的底层结构：数组 + 链表 + 红黑树

```
HashMap 内部结构（JDK 1.8）

table[]（Node 数组，初始长度 16）
┌────┬────┬────┬────┬────┬────┬────┬────┐
│null│ N1 │null│ N2 │null│null│null│... │   ← 桶数组
└────┴─┬──┴────┴─┬──┴────┴────┴────┴────┘
         │        │
         ▼        ▼
       N1→N3     N2→N4→N5    （链表，哈希冲突时）
                   │
                   ▼（链表 >8 且数组 >=64 时树化）
                 TreeNode（红黑树）
```

每个桶存的是 `Node<K,V>`（链表节点）或 `TreeNode<K,V>`（红黑树节点），都实现了 `Map.Entry`。

```java
// Node 源码（简化）
static class Node<K,V> implements Map.Entry<K,V> {
    final int hash;
    final K key;
    V value;
    Node<K,V> next;  // 链表下一个节点
}
```

### 5.2 核心参数：容量、负载因子、阈值

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| 初始容量 | **16** | table 数组初始长度（必须是 2 的幂） |
| 负载因子 | **0.75** | 触发扩容的填充比例 |
| 扩容阈值 | 容量 × 负载因子 = **12** | 元素数超过此值就扩容 |
| 扩容倍数 | **2 倍** | 每次扩容为原来的 2 倍 |

```java
// 默认构造：初始 16，负载因子 0.75
Map<String, String> map = new HashMap<>();

// 指定初始容量
Map<String, String> map2 = new HashMap<>(32);

// 指定容量和负载因子
Map<String, String> map3 = new HashMap<>(32, 0.8f);
```

> 💡 **为什么容量是 2 的幂？** 这样 `hash & (n-1)` 等价于 `hash % n`，位运算比取模快。扩容 2 倍也保证新容量仍是 2 的幂。

> ⚠️ **为什么负载因子是 0.75？** 这是空间和时间的折中：太小（如 0.5）浪费空间，太大（如 1.0）哈希冲突增多查询变慢。0.75 是时间和空间综合后的经验值。

> 📌 **开发建议**：如果预先知道元素数量，创建时指定初始容量 = 预期元素数 / 0.75 + 1，避免多次扩容。如存 100 个元素：`new HashMap<>(134)`。

### 5.3 put 流程详解 ⭐⭐

`put(key, value)` 是 HashMap 最核心的方法，流程如下：

```
put(K key, V value) 流程：

1. 计算 hash：hash = (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16)
   （扰动：高 16 位与低 16 位异或，减少冲突）

2. 定位桶：index = hash & (n-1)，n 是数组长度

3. 桶为空 → 直接放入新 Node ✅

4. 桶非空 → 遍历桶内元素（链表或树）：
   a. key 的 hash 相同 && key.equals(旧key) 为 true
      → 找到相同 key，覆盖旧 value，返回旧 value
   b. 遍历完都没找到相同 key
      → 追加到链表末尾（或插入树中）
      → 若是链表且插入后长度 >8 且数组 >=64，树化为红黑树

5. 检查是否需要扩容：
   size > 阈值（capacity × 0.75）→ 扩容为 2 倍并 rehash
```

```java
// 演示 hash 计算与定位
Map<String, Integer> map = new HashMap<>();
map.put("A", 1);
// 内部：
//   hash = "A".hashCode() ^ ("A".hashCode() >>> 16)
//   index = hash & (16 - 1) = hash & 15
//   table[index] 为空 → 放入
```

> 💡 **key 可以是 null**：HashMap 允许一个 key 为 null，其 hash 固定为 0，放在 table[0]。

### 5.4 树化与退化

| 过程 | 条件 | 说明 |
| :--- | :--- | :--- |
| 链表 → 红黑树 | 链表长度 **>8** 且数组长度 **>=64** | 两个条件都要满足 |
| 仅链表 >8 但数组 <64 | 只扩容，不树化 | 优先扩容解决冲突 |
| 红黑树 → 链表 | 树节点数 **<=6** | 退化回链表 |

```java
// 验证树化需要数组 >=64
// 如果数组只有 16，即使某桶链表有 9 个元素，也只会触发扩容，不会树化
// 因为扩容能重新分散元素，比树化更划算
```

> ⚠️ **常见误解**：「链表到 8 就树化」是错的！必须同时满足数组 >=64。设计者认为数组太小时，扩容比树化更能解决根本问题（冲突源于容量不足）。

### 5.5 扩容 rehash

当 `size > 阈值` 时触发扩容：

```
扩容流程：
1. 创建新数组，容量 = 旧容量 × 2
2. 遍历旧数组所有桶：
   - 对每个元素重新计算 index = hash & (newN - 1)
   - JDK 1.8 优化：元素要么留在原位置，要么移到「原位置 + 旧容量」
3. 迁移完成后，旧数组被 GC
```

```java
// 演示扩容
Map<Integer, String> map = new HashMap<>(4, 0.75f);  // 初始 4，阈值 3
map.put(1, "A");
map.put(2, "B");
map.put(3, "C");
// 此时 size=3 = 阈值，还没扩容
map.put(4, "D");
// size=4 > 阈值 3 → 扩容为 8，阈值变为 6，rehash
```

> 💡 **扩容代价大**：rehash 要遍历所有元素重新定位，是性能瓶颈。预先估算容量可避免频繁扩容，这是 HashMap 性能调优的关键。

### 5.6 自定义对象做 key 必须重写 equals 和 hashCode ⭐⭐⭐

这是 HashMap 使用中最关键的坑。和 HashSet 一样，HashMap 判断 key 重复依赖 `equals` 和 `hashCode`：

```java
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

class Student {
    String id;   // 学号
    String name;

    Student(String id, String name) { this.id = id; this.name = name; }

    // ✅ 必须重写，以 id 作为唯一标识
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Student)) return false;
        return Objects.equals(id, ((Student) o).id);
    }
    @Override
    public int hashCode() {
        return Objects.hash(id);  // 与 equals 字段一致
    }
}

public class Demo {
    public static void main(String[] args) {
        Map<Student, Integer> scores = new HashMap<>();
        scores.put(new Student("001", "张三"), 90);
        scores.put(new Student("001", "张三"), 95);  // 同一学号，应覆盖
        System.out.println(scores.size());           // ✅ 1
        System.out.println(scores.get(new Student("001", "张三")));  // ✅ 95
        // ❌ 若不重写：size=2，get 返回 null（因为 hash 不同，定位到不同桶）
    }
}
```

> ⚠️ **致命坑**：不重写时，`new Student("001","张三")` 每次的 hash 都不同（基于地址），会被分到不同桶，**永远 get 不到之前 put 的值**。这是「Map 存了但取不出来」的最常见原因。

> 📌 **不可变对象做 key 最安全**：String、Integer 等是不可变类，做 key 最稳妥。如果用可变对象做 key，put 后又修改了参与 hashCode 的字段，会导致 key「失踪」（hash 变了，定位不到原桶）。**强烈建议 key 用不可变类型。**

```java
// ❌ 危险：用可变对象做 key 后修改字段
Map<List<String>, Integer> map = new HashMap<>();
List<String> key = new ArrayList<>(Arrays.asList("A"));
map.put(key, 1);
key.add("B");  // 修改了 key 内容，hashCode 变了！
map.get(key);  // null，找不到了（定位到错误的桶）
```

---

## 六、LinkedHashMap

`LinkedHashMap` 继承自 `HashMap`，在 HashMap 基础上维护一条**双向链表**，记录插入顺序（或访问顺序）。

```
HashMap 结构 + 双向链表串联所有节点

  普通节点：Node + before/after 指针
  ┌──────────────────────────┐
  │ head → N1 ⇄ N2 ⇄ N3 ← tail │  （按插入顺序串联）
  └──────────────────────────┘
```

```java
import java.util.LinkedHashMap;
import java.util.Map;

// 默认：按插入顺序
Map<String, Integer> lhm = new LinkedHashMap<>();
lhm.put("C", 3);
lhm.put("A", 1);
lhm.put("B", 2);
System.out.println(lhm);  // {C=3, A=1, B=2}（保持插入顺序）

// 对比 HashMap（无序）
Map<String, Integer> hm = new HashMap<>();
hm.put("C", 3); hm.put("A", 1); hm.put("B", 2);
System.out.println(hm);  // {A=1, B=2, C=3}（不保证）
```

**访问顺序模式（LRU 基础）**：

```java
// accessOrder=true：按访问顺序排序（最近访问的在末尾）
Map<String, Integer> access = new LinkedHashMap<>(16, 0.75f, true);
access.put("A", 1);
access.put("B", 2);
access.put("C", 3);
System.out.println(access);  // {A=1, B=2, C=3}
access.get("A");             // 访问 A，A 移到末尾
System.out.println(access);  // {B=2, C=3, A=1}
```

> 💡 **LRU 缓存经典实现**：用 `accessOrder=true` 的 LinkedHashMap + 重写 `removeEldestEntry`，几行代码就能实现一个 LRU 缓存。

```java
import java.util.LinkedHashMap;
import java.util.Map;

// ✅ 经典 LRU 缓存（最多 100 个元素，淘汰最久未访问的）
class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;
    public LruCache(int capacity) {
        super(capacity, 0.75f, true);  // accessOrder=true
        this.capacity = capacity;
    }
    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity;  // 超容量时淘汰链表头部（最久未访问）
    }
}
```

---

## 七、TreeMap

`TreeMap` 基于红黑树实现，按 key 的自然顺序或定制顺序排序。和 TreeSet 一样，key 必须可比较。

```java
import java.util.TreeMap;
import java.util.Map;

// key 按自然顺序排序
Map<String, Integer> tm = new TreeMap<>();
tm.put("banana", 2);
tm.put("apple", 1);
tm.put("cherry", 3);
System.out.println(tm);  // {apple=1, banana=2, cherry=3}（按 key 排序）

// 定制排序：按 key 降序
Map<String, Integer> tm2 = new TreeMap<>((a, b) -> b.compareTo(a));
tm2.put("banana", 2); tm2.put("apple", 1); tm2.put("cherry", 3);
System.out.println(tm2);  // {cherry=3, banana=2, apple=1}
```

**TreeMap 特有方法**（得益于有序性）：

```java
TreeMap<Integer, String> tm = new TreeMap<>();
tm.put(10, "a"); tm.put(20, "b"); tm.put(30, "c"); tm.put(40, "d");

tm.firstKey();           // 10，最小 key
tm.lastKey();            // 40，最大 key
tm.headMap(30);          // {10=a, 20=b}，key < 30 的部分
tm.tailMap(30);          // {30=c, 40=d}，key >= 30 的部分
tm.subMap(20, 40);       // {20=b, 30=c}，[20, 40) 区间
tm.ceilingKey(25);       // 30，>= 25 的最小 key
tm.floorKey(25);         // 20，<= 25 的最大 key
tm.descendingMap();      // 逆序视图
```

> ⚠️ **TreeMap 的 key 不允许 null**（无法比较），这点与 HashMap 不同。自定义对象做 key 必须实现 `Comparable` 或构造时传 `Comparator`。

---

## 八、Properties

`Properties` 是 `Hashtable` 的子类，专门用于读取 `.properties` 配置文件。它的 key 和 value 都是 `String` 类型。

```java
import java.util.Properties;
import java.io.FileInputStream;

// ✅ 读取配置文件
Properties props = new Properties();
try (FileInputStream fis = new FileInputStream("config.properties")) {
    props.load(fis);  // 从输入流加载
}
String url = props.getProperty("db.url");
String timeout = props.getProperty("db.timeout", "3000");  // 带默认值

System.out.println(url);
System.out.println(timeout);
```

配置文件 `config.properties` 内容示例：

```
db.url=jdbc:mysql://localhost:3306/test
db.username=root
db.password=123456
db.timeout=5000
```

```java
// 设置和写出
props.setProperty("new.key", "value");
try (FileOutputStream fos = new FileOutputStream("config.properties")) {
    props.store(fos, "updated config");
}
```

> 💡 **Properties 的 key/value 都是 String**：虽然它继承 Hashtable（可存任意 Object），但规范上只用 String。`setProperty`/`getProperty` 方法强制了 String 类型。

> ⚠️ `Properties` 继承自 `Hashtable`，是**线程安全**的（方法 synchronized），但性能较差。现代项目多用 YAML/JSON 配置，Properties 仍是读取 `.properties` 文件的标准方式。

---

## 九、HashMap vs LinkedHashMap vs TreeMap vs Hashtable

| 特性 | HashMap | LinkedHashMap | TreeMap | Hashtable |
| :--- | :--- | :--- | :--- | :--- |
| **底层结构** | 数组+链表+红黑树 | HashMap+双向链表 | 红黑树 | 数组+链表 |
| **是否有序** | 无序 | ✅ 插入/访问顺序 | ✅ key 排序 | 无序 |
| **允许 null key** | ✅（1 个） | ✅（1 个） | ❌ | ❌ |
| **允许 null value** | ✅ | ✅ | ✅ | ❌ |
| **线程安全** | ❌ | ❌ | ❌ | ✅（synchronized） |
| **性能** | O(1) | O(1) | O(log n) | O(1)（有锁开销） |
| **适用场景** | 通用缓存 | 需保留顺序/LRU | 需排序/范围查询 | 遗留代码 |
| **JDK 版本** | 1.2 | 1.4 | 1.2 | 1.0（已过时） |

> ⚠️ **Hashtable 已过时**：它是 JDK 1.0 的古老类，方法级 synchronized 锁粒度太粗，并发性能差。**新代码不要用 Hashtable**，多线程场景用 `ConcurrentHashMap`（详见 [40-JUC并发包](40-JUC并发包.md)）。

> 📌 **选型建议**：默认用 `HashMap`；需要保留插入顺序或实现 LRU 用 `LinkedHashMap`；需要按 key 排序或范围查询用 `TreeMap`；多线程用 `ConcurrentHashMap`。

---

## 十、ConcurrentHashMap 简介

`HashMap` 是非线程安全的：多线程并发 put 可能导致数据丢失、结构破坏（JDK 1.7 甚至可能死循环）。多线程下应使用 `ConcurrentHashMap`：

```java
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

// ✅ 多线程安全的 Map
Map<String, Integer> map = new ConcurrentHashMap<>();
map.put("A", 1);
map.put("B", 2);
```

> 💡 `ConcurrentHashMap` 的底层在 JDK 1.8 后与 HashMap 类似（数组+链表+红黑树），但用 **CAS + synchronized** 锁单个桶，并发性能远优于 Hashtable 的全局锁。详细原理在 [40-JUC并发包](40-JUC并发包.md) 详讲，这里只需知道它的存在和用途。

> ⚠️ **ConcurrentHashMap 不允许 null key 和 null value**：因为多线程下无法区分「不存在」和「值为 null」，这点与 HashMap 不同。

---

## ⚠️ 重点

### 重点 1：HashMap 非线程安全 ⭐⭐⭐

```java
// ❌ 多线程并发 put 会导致数据丢失
Map<String, Integer> map = new HashMap<>();
Runnable task = () -> {
    for (int i = 0; i < 1000; i++) {
        map.put("key" + i, i);
    }
};
Thread t1 = new Thread(task);
Thread t2 = new Thread(task);
t1.start(); t2.start();
t1.join(); t2.join();
System.out.println(map.size());  // 可能小于 2000，甚至抛 ConcurrentModificationException

// ✅ 多线程用 ConcurrentHashMap
Map<String, Integer> safeMap = new ConcurrentHashMap<>();
```

> ⚠️ JDK 1.7 的 HashMap 多线程扩容可能形成环形链表导致死循环（100% CPU），JDK 1.8 修复了死循环但仍会丢数据。**生产环境多线程务必用 ConcurrentHashMap。**

### 重点 2：自定义对象做 key 必须重写 equals 和 hashCode ⭐⭐⭐

```java
class User {
    String id;
    User(String id) { this.id = id; }
    // ❌ 不重写：put 后 get 不到（hash 基于地址，每次不同）
}

// ✅ 重写后：相同 id 视为同一 key
@Override
public boolean equals(Object o) {
    if (!(o instanceof User)) return false;
    return Objects.equals(id, ((User) o).id);
}
@Override
public int hashCode() { return Objects.hash(id); }
```

> 📌 **铁律**：key 用不可变类型最安全（String、Integer）。用可变对象做 key 且 put 后修改字段，会导致 key「失踪」。

### 重点 3：get 返回 null 不一定是没存 ⭐⭐

```java
Map<String, String> map = new HashMap<>();
map.put("A", null);    // value 可以是 null
map.get("A");           // null（但 key 存在！）
map.get("B");           // null（key 不存在）

// ⚠️ 无法区分「value 是 null」和「key 不存在」
// ✅ 用 containsKey 区分
map.containsKey("A");   // true
map.containsKey("B");   // false

// ✅ 或用 getOrDefault
map.getOrDefault("A", "default");  // null（A 存在，value 是 null）
map.getOrDefault("B", "default");  // default（B 不存在）
```

### 重点 4：遍历时不能直接 put/remove ⭐⭐

```java
Map<String, Integer> map = new HashMap<>();
map.put("A", 1); map.put("B", 2);

// ❌ 遍历时删除，触发 ConcurrentModificationException
for (String key : map.keySet()) {
    if (key.equals("A")) {
        map.remove(key);  // ❌ 抛异常
    }
}

// ✅ 方式一：用迭代器的 remove
Iterator<Map.Entry<String, Integer>> it = map.entrySet().iterator();
while (it.hasNext()) {
    if (it.next().getKey().equals("A")) {
        it.remove();  // ✅ 迭代器自己的 remove
    }
}

// ✅ 方式二：Java 8 removeIf
map.entrySet().removeIf(e -> e.getKey().equals("A"));

// ✅ 方式三：Java 8 compute/remove 按条件删
map.remove("A", 1);  // 当 key=A 且 value=1 时删除
```

### 重点 5：初始容量估算避免扩容 ⭐⭐

```java
// ❌ 默认 16，存 100 个元素要扩容多次
Map<Integer, String> map = new HashMap<>();
for (int i = 0; i < 100; i++) map.put(i, "v" + i);

// ✅ 预估容量 = 元素数 / 0.75 + 1
Map<Integer, String> map2 = new HashMap<>(134);  // 100/0.75≈134
// Guava: new HashMap<>(Maps.newHashMapWithExpectedSize(100))
```

> 💡 **阿里规约**：初始化 HashMap 时指定容量 = 需要的元素数 / 0.75 + 1（向上取整），避免频繁扩容。

### 重点 6：HashMap 的 key 是 null 时存在 table[0] ⭐

```java
Map<String, Integer> map = new HashMap<>();
map.put(null, 100);     // null key 的 hash 固定为 0，存在 table[0]
System.out.println(map.get(null));  // 100
```

---

## 💻 实战案例

### 案例 1：用 HashMap 做商品缓存（电商系统）⭐⭐

电商系统中，频繁查询的商品信息用 HashMap 缓存，避免每次查数据库：

```java
import java.util.HashMap;
import java.util.Map;

class Product {
    Integer id;
    String name;
    double price;

    Product(Integer id, String name, double price) {
        this.id = id; this.name = name; this.price = price;
    }
    @Override
    public String toString() { return id + ":" + name + "(" + price + ")"; }
}

public class ProductCache {
    // 商品缓存：id → 商品对象
    private static final Map<Integer, Product> CACHE = new HashMap<>();

    // 模拟从数据库加载
    private static Product loadFromDb(int id) {
        // ... 实际查 DB
        return new Product(id, "商品" + id, id * 10.0);
    }

    // 先查缓存，没有再查 DB 并放入缓存
    public static Product getProduct(int id) {
        // ✅ getOrDefault 防空指针
        Product p = CACHE.get(id);
        if (p == null) {
            p = loadFromDb(id);
            CACHE.put(id, p);
        }
        return p;
    }

    // Java 8 更优雅：computeIfAbsent
    public static Product getProductJava8(int id) {
        return CACHE.computeIfAbsent(id, ProductCache::loadFromDb);
    }

    public static void main(String[] args) {
        System.out.println(getProduct(1));   // 1:商品1(10.0)
        System.out.println(getProduct(1));   // 第二次走缓存，不查 DB
        System.out.println(getProductJava8(2));  // 2:商品2(20.0)
    }
}
```

> 💡 `computeIfAbsent` 是 Java 8 新增方法，key 不存在时用函数计算 value 并放入，一行代码实现「缓存穿透加载」，比手写 if-null 更简洁。

### 案例 2：统计单词频率（文本分析）⭐⭐

统计一段文本中每个单词出现的次数，是 HashMap 最经典的应用：

```java
import java.util.HashMap;
import java.util.Map;

public class WordCount {
    public static void main(String[] args) {
        String text = "the quick brown fox jumps over the lazy dog the fox";
        String[] words = text.split(" ");

        // ✅ 方式一：传统写法
        Map<String, Integer> count1 = new HashMap<>();
        for (String word : words) {
            if (count1.containsKey(word)) {
                count1.put(word, count1.get(word) + 1);
            } else {
                count1.put(word, 1);
            }
        }
        System.out.println(count1);
        // {fox=2, dog=1, lazy=1, over=1, the=3, brown=1, jumps=1, quick=1}

        // ✅ 方式二：getOrDefault 简化
        Map<String, Integer> count2 = new HashMap<>();
        for (String word : words) {
            count2.put(word, count2.getOrDefault(word, 0) + 1);
        }

        // ✅ 方式三：Java 8 merge（最优雅）
        Map<String, Integer> count3 = new HashMap<>();
        for (String word : words) {
            count3.merge(word, 1, Integer::sum);  // 存在则累加，不存在则放 1
        }
        System.out.println(count3);
    }
}
```

> 💡 **三个 API 对比**：`containsKey + get + put` 最啰嗦；`getOrDefault` 简化；`merge` 最优雅。`merge(key, value, remappingFunction)` 的语义是「key 存在时用函数合并旧值和新值，不存在时直接放入」。

### 案例 3：用户会话管理（Web 后台）⭐⭐

Web 系统中，用户登录后用 sessionId 关联用户信息，HashMap 是天然的会话存储：

```java
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

class UserSession {
    String userId;
    String username;
    long loginTime;
    long lastAccessTime;

    UserSession(String userId, String username) {
        this.userId = userId;
        this.username = username;
        this.loginTime = System.currentTimeMillis();
        this.lastAccessTime = this.loginTime;
    }
    void touch() { this.lastAccessTime = System.currentTimeMillis(); }
    boolean isExpired(long timeout) {
        return System.currentTimeMillis() - lastAccessTime > timeout;
    }
}

public class SessionManager {
    // sessionId → 会话
    private static final Map<String, UserSession> SESSIONS = new HashMap<>();
    private static final long TIMEOUT = 30 * 60 * 1000L;  // 30 分钟

    // 登录：创建会话
    public static String login(String userId, String username) {
        String sessionId = UUID.randomUUID().toString();
        SESSIONS.put(sessionId, new UserSession(userId, username));
        return sessionId;
    }

    // 验证会话
    public static UserSession getSession(String sessionId) {
        UserSession session = SESSIONS.get(sessionId);
        if (session == null) return null;  // 无此会话
        if (session.isExpired(TIMEOUT)) {
            SESSIONS.remove(sessionId);    // 过期清理
            return null;
        }
        session.touch();                  // 刷新访问时间
        return session;
    }

    // 登出
    public static void logout(String sessionId) {
        SESSIONS.remove(sessionId);
    }

    public static void main(String[] args) {
        String sid = login("u001", "张三");
        System.out.println("会话: " + getSession(sid).username);  // 张三
        logout(sid);
        System.out.println(getSession(sid));  // null（已登出）
    }
}
```

> ⚠️ **生产环境**会话管理要用 `ConcurrentHashMap`（多线程安全），且需定时清理过期会话。这里仅为演示 HashMap 的应用场景。

### 案例 4：Properties 读取配置文件（系统配置）⭐⭐

数据库连接配置、第三方 API 密钥等通常放在 `.properties` 文件：

```java
import java.util.Properties;
import java.io.FileInputStream;
import java.io.InputStream;

public class ConfigReader {
    public static void main(String[] args) throws Exception {
        Properties props = new Properties();
        // ✅ 从文件读取
        try (InputStream is = new FileInputStream("db.properties")) {
            props.load(is);
        }
        String url = props.getProperty("jdbc.url");
        String user = props.getProperty("jdbc.user", "root");  // 带默认值
        String pwd = props.getProperty("jdbc.password");
        int poolSize = Integer.parseInt(props.getProperty("pool.size", "10"));

        System.out.println("URL: " + url);
        System.out.println("连接池大小: " + poolSize);
    }
}
```

`db.properties` 文件：

```
jdbc.url=jdbc:mysql://localhost:3306/shop
jdbc.user=admin
jdbc.password=secret
pool.size=20
```

> 💡 Spring Boot 项目中，`.properties`/`.yml` 配置会被自动加载到 `@Value` 或 `@ConfigurationProperties` 中，但底层仍是 Properties/Map 机制。

### 案例 5：TreeMap 按日期排序订单（金融系统）⭐⭐

金融系统需要按日期排序展示订单，TreeMap 天然有序：

```java
import java.util.TreeMap;
import java.util.Map;
import java.time.LocalDate;

class Order {
    String orderId;
    double amount;

    Order(String orderId, double amount) {
        this.orderId = orderId; this.amount = amount;
    }
    @Override
    public String toString() { return orderId + "(" + amount + ")"; }
}

public class OrderByDate {
    public static void main(String[] args) {
        // key=日期，按日期自然排序
        TreeMap<LocalDate, Order> orders = new TreeMap<>();
        orders.put(LocalDate.of(2024, 3, 15), new Order("O003", 500));
        orders.put(LocalDate.of(2024, 1, 10), new Order("O001", 1000));
        orders.put(LocalDate.of(2024, 2, 20), new Order("O002", 800));
        orders.put(LocalDate.of(2024, 3, 1), new Order("O004", 300));

        // ✅ 自动按日期升序
        System.out.println("按日期升序:");
        orders.forEach((date, order) ->
            System.out.println(date + " -> " + order));

        // ✅ 查某段时间内的订单
        System.out.println("\n2月的订单:");
        Map<LocalDate, Order> feb = orders.subMap(
            LocalDate.of(2024, 2, 1),
            LocalDate.of(2024, 3, 1));
        feb.forEach((d, o) -> System.out.println(d + " -> " + o));

        // ✅ 最近的订单
        System.out.println("\n最近一笔: " + orders.lastEntry());

        // ✅ 最早的订单
        System.out.println("最早一笔: " + orders.firstEntry());
    }
}
```

### 案例 6：自定义对象做 key 的坑（反面教材）⭐⭐⭐

演示不重写 equals/hashCode 导致的「存了取不出」问题：

```java
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

class Account {
    String accountNo;
    Account(String accountNo) { this.accountNo = accountNo; }

    // ❌ 故意不重写 equals 和 hashCode
}

class AccountFixed {
    String accountNo;
    AccountFixed(String accountNo) { this.accountNo = accountNo; }

    // ✅ 重写
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof AccountFixed)) return false;
        return Objects.equals(accountNo, ((AccountFixed) o).accountNo);
    }
    @Override
    public int hashCode() { return Objects.hash(accountNo); }
}

public class KeyTrap {
    public static void main(String[] args) {
        // ❌ 不重写：存进去取不出来
        Map<Account, Double> bad = new HashMap<>();
        bad.put(new Account("622848001"), 10000.0);
        System.out.println(bad.get(new Account("622848001")));  // null！
        System.out.println(bad.size());  // 1（存了但取不出）

        // ✅ 重写后：正常存取
        Map<AccountFixed, Double> good = new HashMap<>();
        good.put(new AccountFixed("622848001"), 10000.0);
        System.out.println(good.get(new AccountFixed("622848001")));  // 10000.0
        System.out.println(good.size());  // 1
    }
}
```

> ⚠️ **这是真实事故**：某系统用「手机号对象」做 key 存验证码，没重写 equals/hashCode，导致每次 get 都返回 null，验证码永远校验失败。**自定义对象做 key，重写 equals + hashCode 是底线。**

### 案例 7：多值 Map（一个 key 多个 value）

实际开发中常需要「一个 key 对应多个 value」，如一个用户有多个角色、一个分类下多个商品。用 `Map<K, List<V>>` 实现：

```java
import java.util.*;

public class MultiValueMap {
    public static void main(String[] args) {
        // 分类 → 商品列表
        Map<String, List<String>> categoryMap = new HashMap<>();

        // ✅ 传统写法
        addToList(categoryMap, "手机", "iPhone");
        addToList(categoryMap, "手机", "华为");
        addToList(categoryMap, "电脑", "MacBook");
        addToList(categoryMap, "电脑", "ThinkPad");
        System.out.println(categoryMap);
        // {手机=[iPhone, 华为], 电脑=[MacBook, ThinkPad]}

        // ✅ Java 8 computeIfAbsent 更优雅
        Map<String, List<String>> map2 = new HashMap<>();
        map2.computeIfAbsent("手机", k -> new ArrayList<>()).add("iPhone");
        map2.computeIfAbsent("手机", k -> new ArrayList<>()).add("华为");
        map2.computeIfAbsent("电脑", k -> new ArrayList<>()).add("MacBook");
        System.out.println(map2);
    }

    static void addToList(Map<String, List<String>> map, String key, String val) {
        map.computeIfAbsent(key, k -> new ArrayList<>()).add(val);
    }
}
```

> 💡 Guava 的 `Multimap` 和 Apache Commons 的 `MultiValueMap` 封装了这种模式。Java 原生用 `Map<K, List<V>>` + `computeIfAbsent` 是标准做法。

### 案例 8：统计商品销量排行（TreeMap + merge）

```java
import java.util.*;

public class SalesRanking {
    public static void main(String[] args) {
        // 模拟订单流水：商品名 → 销量
        String[] sales = {"iPhone", "iPad", "iPhone", "AirPods",
                          "iPhone", "iPad", "MacBook"};

        Map<String, Integer> count = new HashMap<>();
        for (String s : sales) {
            count.merge(s, 1, Integer::sum);
        }

        // ✅ 按销量降序排序（用 LinkedHashMap 保留排序结果）
        Map<String, Integer> ranked = new LinkedHashMap<>();
        count.entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .forEachOrdered(e -> ranked.put(e.getKey(), e.getValue()));

        System.out.println("销量排行:");
        ranked.forEach((k, v) -> System.out.println(k + ": " + v + " 件"));
        // iPhone: 3 件
        // iPad: 2 件
        // AirPods: 1 件
        // MacBook: 1 件
    }
}
```

> 💡 `Map.Entry.comparingByValue()` 是 Java 8 提供的 Comparator 工厂方法，配合 Stream 可以优雅地对 Map 排序。排序结果用 `LinkedHashMap` 保存，因为 HashMap 不保留顺序。

---

## 🚀 新版本补充

### Java 8：Map 新增的函数式方法

Java 8 给 Map 增加了一批强大的方法（属于基准内容，这里归类说明）：

```java
Map<String, Integer> map = new HashMap<>();
map.put("A", 1); map.put("B", 2); map.put("C", 3);

// forEach 遍历
map.forEach((k, v) -> System.out.println(k + "=" + v));

// computeIfAbsent：key 不存在时计算并放入
map.computeIfAbsent("D", k -> k.length());  // D=1

// computeIfPresent：key 存在时重新计算
map.computeIfPresent("A", (k, v) -> v + 10);  // A=11

// compute：无论存在与否都计算
map.compute("B", (k, v) -> v == null ? 0 : v * 2);  // B=4

// merge：合并
map.merge("A", 100, Integer::sum);  // A=111（旧值 11 + 100）

// getOrDefault：取值带默认
map.getOrDefault("X", 0);  // 0

// replaceAll：批量替换 value
map.replaceAll((k, v) -> v * 10);

// remove 条件删除
map.remove("A", 1110);  // 仅当 key=A 且 value=1110 时删
```

### Java 9：Map 工厂方法 `of()`

```java
// Java 9+ 不可变 Map
Map<String, Integer> immutable = Map.of("A", 1, "B", 2);
// immutable.put("C", 3);  // ❌ UnsupportedOperationException

// 超过 10 对用 ofEntries
Map<String, Integer> big = Map.ofEntries(
    Map.entry("A", 1), Map.entry("B", 2), Map.entry("C", 3));
```

> ⚠️ `Map.of` 不允许 null key/value，不允许重复 key。Java 8 环境可用 `Collections.unmodifiableMap(...)` 实现不可变。

### Java 10：`var` 推断

```java
// Java 10+
var map = new HashMap<String, Integer>();  // 推断为 HashMap<String,Integer>
```

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Map 接口 | 键值对、key 唯一、value 可重复、一键一值 |
| 常用方法 | put/get/remove/containsKey/keySet/values/entrySet |
| Map.Entry | getKey/getValue/setValue |
| 遍历推荐 | entrySet（效率最高）或 forEach |
| HashMap 底层 | 数组+链表+红黑树（JDK 1.8） |
| 核心参数 | 初始容量 16、负载因子 0.75、扩容 2 倍 |
| put 流程 | hash&（n-1）定位桶 → 空则放 → 有则比 key → 树化 |
| 树化条件 | 链表 >8 且数组 >=64；退化条件 节点 <=6 |
| 自定义 key | 必须重写 equals + hashCode，推荐不可变类型 |
| LinkedHashMap | HashMap+双向链表，保留顺序，可做 LRU |
| TreeMap | 红黑树，key 排序，不允许 null key |
| Properties | Hashtable 子类，读 .properties 配置 |
| ConcurrentHashMap | 多线程安全，不允许 null |

---

## 学习建议

1. **吃透 HashMap 底层**：HashMap 是面试和开发的双重重灾区。务必理解「数组+链表+红黑树」结构、put 流程、扩容机制、树化条件，能画出结构图、口述 put 流程。这篇内容建议反复看 3 遍以上。
2. **动手验证自定义 key 的坑**：写一个不重写 equals/hashCode 的类做 key，put 后用「内容相同的新对象」get，亲眼看到 null——这个教训会让你一辈子记住重写规则。
3. **掌握 Java 8 Map 新方法**：`computeIfAbsent`、`merge`、`getOrDefault`、`forEach` 是日常开发高频方法，能把啰嗦的 if-else 压缩成一行，务必熟练使用。
4. **对比四种 Map 的顺序特性**：把同样的数据分别放入 HashMap、LinkedHashMap、TreeMap，打印对比输出，直观感受「无序 / 插入序 / 排序」的差异，建立选型直觉。
5. **理解容量与扩容的性能影响**：记住「初始 16、负载因子 0.75、扩容 2 倍」，并能根据预期元素数估算初始容量。这是 HashMap 性能调优的核心知识点，也是阿里规约的明确要求。
