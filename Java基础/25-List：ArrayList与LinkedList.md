# List：ArrayList 与 LinkedList

`List` 是 Java 集合框架中最常用的接口，它代表**有序、有索引、允许重复**的集合。无论是购物车商品列表、订单流水、分页查询结果，还是后台管理系统的数据列表，几乎都靠 `List` 来承载。`List` 家族有三大实现：`ArrayList`（数组实现，查询快，绝对主力）、`LinkedList`（链表实现，增删快）、`Vector`（线程安全但已淘汰）。理解它们的底层结构和性能差异，是写出高效代码的前提。

> 💡 在阅读本篇前，建议先看 [24-集合框架体系与Collection](24-集合框架体系与Collection.md)，理解 Collection 的通用方法和集合体系，本篇在此基础上深入 List 的特有方法与三大实现。

---

## 一、List 接口的特点

`List` 继承自 `Collection`，在通用方法之外，它最大的特点是**有序、有索引、允许重复**：

| 特点 | 说明 |
| :--- | :--- |
| 有序 | 存入顺序 == 取出顺序（按插入顺序保留） |
| 有索引 | 每个元素有位置索引（从 0 开始），可按索引精确访问 |
| 允许重复 | 同一元素可存多次，靠索引区分 |

```java
import java.util.ArrayList;
import java.util.List;

List<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("A");    // ✅ 允许重复
System.out.println(list);   // [A, B, A]，存入顺序保留
System.out.println(list.get(0));  // A，按索引访问
System.out.println(list.get(2));  // A，重复元素靠索引区分
```

> 💡 与 `Set` 对比：`Set` 无序、无索引、不允许重复。需要去重用 Set，需要保留顺序和重复用 List。

---

## 二、List 的特有方法（基于索引）

因为 `List` 有索引，所以它比 `Collection` 多了一整套**基于索引操作**的方法。

### 2.1 按索引增删改查

```java
import java.util.ArrayList;
import java.util.List;

List<String> list = new ArrayList<>();
list.add("Java");
list.add("Python");
list.add("Go");

// —— 按索引查询 ——
System.out.println(list.get(0));   // Java，获取指定位置元素
System.out.println(list.indexOf("Go"));      // 2，第一次出现的索引
list.add("Python");
System.out.println(list.lastIndexOf("Python"));  // 3，最后一次出现的索引

// —— 按索引修改 ——
list.set(1, "C++");   // 把索引 1 的元素替换为 C++
System.out.println(list);  // [Java, C++, Go, Python]

// —— 按索引插入 ——
list.add(1, "Rust");   // 在索引 1 处插入，原位置及后面的元素后移
System.out.println(list);  // [Java, Rust, C++, Go, Python]

// —— 按索引删除 ——
String removed = list.remove(2);  // 删除索引 2 的元素，返回被删元素
System.out.println(removed);  // C++
System.out.println(list);     // [Java, Rust, Go, Python]
```

> ⚠️ `remove` 有重载：`remove(int index)` 按索引删，`remove(Object o)` 按元素删。当 List 存的是 `Integer` 时要特别小心二者的歧义（见重点 4）。

### 2.2 子列表与批量操作

```java
List<Integer> nums = new ArrayList<>();
nums.add(10);
nums.add(20);
nums.add(30);
nums.add(40);
nums.add(50);

// subList：截取 [fromIndex, toIndex) 的视图
List<Integer> sub = nums.subList(1, 4);
System.out.println(sub);   // [20, 30, 40]

// 批量添加
List<Integer> more = new ArrayList<>();
more.add(60);
more.add(70);
nums.addAll(more);
System.out.println(nums);  // [10, 20, 30, 40, 50, 60, 70]
```

### 2.3 List 特有方法速查表

| 方法 | 说明 | 返回值 |
| :--- | :--- | :--- |
| `add(int index, E e)` | 在指定索引插入 | void |
| `get(int index)` | 获取指定索引元素 | E |
| `set(int index, E e)` | 替换指定索引元素 | E（旧元素） |
| `remove(int index)` | 删除指定索引元素 | E（被删元素） |
| `indexOf(Object o)` | 第一次出现的索引 | int（-1 表示无） |
| `lastIndexOf(Object o)` | 最后一次出现的索引 | int |
| `subList(from, to)` | 截取子列表视图 | List |
| `addAll(int index, Collection c)` | 在指定位置批量插入 | boolean |

---

## 三、List 的三种遍历

```java
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;

List<String> list = new ArrayList<>();
list.add("Java");
list.add("Python");
list.add("Go");

// 方式 1：普通 for + get（仅 List 有索引，能用）
for (int i = 0; i < list.size(); i++) {
    System.out.println(i + ": " + list.get(i));
}

// 方式 2：迭代器
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    System.out.println(it.next());
}

// 方式 3：增强 for
for (String s : list) {
    System.out.println(s);
}

// 方式 4：ListIterator（List 专属，可双向遍历 + 修改）
ListIterator<String> lit = list.listIterator(list.size());  // 从末尾开始
while (lit.hasPrevious()) {
    System.out.println(lit.previous());  // 倒序遍历
}
```

> 💡 **遍历方式选择**：LinkedList 用普通 for + get 会非常慢（每次 get 都从头遍历），LinkedList 应该用迭代器或增强 for。ArrayList 三种都可以。

> ⚠️ **ListIterator** 是 List 专属的迭代器，支持双向遍历（`hasPrevious`/`previous`）、设置（`set`）、添加（`add`），是遍历中修改 List 的安全方式。

---

## 四、ArrayList（重点 ⭐⭐⭐）

`ArrayList` 是 Java 中**用得最多**的集合，没有之一。理解它的底层结构和扩容机制，是 Java 工程师的基本功。

### 4.1 底层结构：Object[] 数组

`ArrayList` 底层就是一个 `Object[]` 数组，通过维护一个 `size` 计数器记录元素个数：

```java
// JDK 源码（简化版）
public class ArrayList<E> {
    transient Object[] elementData;   // 存元素的数组
    private int size;                  // 元素个数

    // 空参构造：1.8 延迟初始化，指向一个空数组
    public ArrayList() {
        this.elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
    }
}
```

> 💡 **JDK 1.7 vs 1.8 的区别**：
> - JDK 1.7：无参构造**直接创建容量为 10 的数组**（饿汉式）
> - JDK 1.8：无参构造指向一个**空数组**（`{}`），首次 add 时才扩容到 10（延迟初始化，节省内存）

### 4.2 扩容机制：1.5 倍

当数组装满后，再 add 元素会触发扩容：

```java
// 模拟扩容过程
List<Integer> list = new ArrayList<>();
// 此时 elementData = {}（空数组，1.8 延迟初始化）

list.add(1);
// 第一次 add：扩容到 10，elementData = new Object[10]
// size = 1

for (int i = 2; i <= 10; i++) {
    list.add(i);   // 装满 10 个
}
// size = 10，数组已满

list.add(11);
// 触发扩容：新容量 = 10 + 10/2 = 15（1.5 倍）
// Arrays.copyOf 把旧数据拷到新数组
// size = 11
```

扩容的核心逻辑：

```
新容量 = 旧容量 + 旧容量 >> 1   （即旧容量 + 旧容量/2 = 1.5 倍）
```

> ⚠️ 扩容要调用 `Arrays.copyOf` 把旧数组元素拷贝到新数组，这是**性能开销**。如果预先知道元素数量，应该用 `new ArrayList<>(capacity)` 指定初始容量，避免多次扩容。

### 4.3 性能分析

| 操作 | 时间复杂度 | 说明 |
| :--- | :---: | :--- |
| `get(index)` | O(1) | 数组下标直接访问，极快 |
| `add(E)` | O(1) 摊还 | 末尾添加，偶尔扩容 |
| `add(index, E)` | O(n) | 要移动后面所有元素 |
| `remove(index)` | O(n) | 要移动后面所有元素 |
| `contains(o)` | O(n) | 从头遍历找 |

```java
List<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("C");
list.add("D");

// ✅ 末尾添加：O(1)
list.add("E");   // [A, B, C, D, E]

// ⚠️ 中间插入：O(n)，要移动后面的元素
// 在索引 1 插入 "X"，B/C/D/E 全部后移
list.add(1, "X");   // [A, X, B, C, D, E]

// ⚠️ 中间删除：O(n)，要移动后面的元素
list.remove(2);   // 删除 B，C/D/E 全部前移 → [A, X, C, D, E]
```

### 4.4 非线程安全

`ArrayList` **不是线程安全**的。多线程并发修改（如一个线程 add、另一个线程遍历）会抛 `ConcurrentModificationException`，或导致数据错乱。

```java
// 多线程下 ArrayList 出问题
List<Integer> list = new ArrayList<>();
for (int i = 0; i < 100; i++) {
    new Thread(() -> {
        list.add(1);
    }).start();
}
// 可能：部分元素丢失、ArrayIndexOutOfBoundsException、ConcurrentModificationException
```

> 💡 线程安全方案：
> - `Collections.synchronizedList(new ArrayList<>())`（底层 synchronized，性能一般）
> - `CopyOnWriteArrayList`（写时复制，读多写少场景，见 [40-并发集合](40-并发集合.md)）

---

## 五、LinkedList

`LinkedList` 底层是**双向链表**，每个节点存数据 + 前驱指针 + 后继指针。它查询慢但增删快，还能当队列、栈、双端队列用。

### 5.1 底层结构：双向链表

```java
// JDK 源码（简化版）
public class LinkedList<E> {
    transient Node<E> first;   // 头节点
    transient Node<E> last;    // 尾节点
    transient int size;         // 元素个数

    private static class Node<E> {
        E item;            // 数据
        Node<E> next;      // 后继
        Node<E> prev;       // 前驱
        // ...
    }
}
```

结构示意：

```
null <- [Node A] <-> [Node B] <-> [Node C] -> null
        first                    last
```

### 5.2 性能分析

| 操作 | 时间复杂度 | 说明 |
| :--- | :---: | :--- |
| `get(index)` | O(n) | 要从头/尾遍历到目标位置 |
| `add(E)` | O(1) | 末尾添加，只需改指针 |
| `add(index, E)` | O(n) | 遍历定位 + O(1) 改指针 |
| `remove(index)` | O(n) | 遍历定位 + O(1) 改指针 |
| `addFirst/addLast` | O(1) | 首尾操作，直接改指针 |
| `removeFirst/removeLast` | O(1) | 首尾操作 |

```java
LinkedList<String> list = new LinkedList<>();
list.add("A");
list.add("B");
list.add("C");

// ⚠️ get(index) 是 O(n)，千万别在循环里用
for (int i = 0; i < list.size(); i++) {
    System.out.println(list.get(i));  // ❌ 每次都从头遍历，O(n²)
}

// ✅ 用迭代器或增强 for
for (String s : list) {   // ✅ O(n)
    System.out.println(s);
}
```

> ⚠️ **新手大坑**：用 `for + get` 遍历 LinkedList，每次 `get(i)` 都从头遍历，整体 O(n²)。LinkedList 必须用迭代器遍历！

### 5.3 特有方法（首尾操作）

`LinkedList` 实现了 `Deque` 接口，提供了大量首尾操作方法：

```java
import java.util.LinkedList;

LinkedList<String> list = new LinkedList<>();
list.add("B");
list.add("C");

// —— 首部操作 ——
list.addFirst("A");     // 头部添加 → [A, B, C]
list.push("A0");        // 等价于 addFirst → [A0, A, B, C]
System.out.println(list.getFirst());    // A0，获取头部
System.out.println(list.peek());        // A0，获取头部但不删除
System.out.println(list.removeFirst()); // A0，删除并返回头部 → [A, B, C]
System.out.println(list.pop());         // A，等价于 removeFirst → [B, C]

// —— 尾部操作 ——
list.addLast("D");      // 尾部添加 → [B, C, D]
System.out.println(list.getLast());     // D，获取尾部
System.out.println(list.removeLast());  // D，删除并返回尾部 → [B, C]
```

### 5.4 当队列和栈用

```java
import java.util.LinkedList;
import java.util.Queue;
import java.util.Deque;

// —— 当队列用（FIFO 先进先出）——
Queue<String> queue = new LinkedList<>();
queue.offer("A");    // 入队（尾部）
queue.offer("B");
queue.offer("C");
System.out.println(queue.peek());   // A，查看队头
System.out.println(queue.poll());   // A，出队（头部）
System.out.println(queue);          // [B, C]

// —— 当栈用（LIFO 后进先出）——
Deque<String> stack = new LinkedList<>();
stack.push("A");     // 入栈（头部）
stack.push("B");
stack.push("C");
System.out.println(stack.peek());   // C，查看栈顶
System.out.println(stack.pop());    // C，出栈（头部）
System.out.println(stack);          // [B, A]

// —— 当双端队列用 ——
Deque<String> deque = new LinkedList<>();
deque.offerFirst("A");   // 头部入
deque.offerLast("B");     // 尾部入
deque.offerFirst("C");    // 头部入 → [C, A, B]
System.out.println(deque.peekFirst());  // C
System.out.println(deque.peekLast());   // B
```

> 💡 Java 官方推荐用 `Deque` 接口（而非遗留的 `Stack` 类）来实现栈，`ArrayDeque` 性能通常比 `LinkedList` 更好。

---

## 六、Vector

`Vector` 是 JDK 1.0 时代的遗留集合，底层也是数组，但所有方法都加了 `synchronized`，**线程安全但效率低**，现代开发基本不用。

```java
import java.util.Vector;

Vector<String> v = new Vector<>();
v.add("A");
v.add("B");
System.out.println(v);  // [A, B]

// Vector 的扩容是 2 倍（ArrayList 是 1.5 倍）
// 所有方法都有 synchronized，多线程安全但慢
```

| 对比项 | Vector | ArrayList |
| :--- | :--- | :--- |
| 线程安全 | ✅ synchronized | ❌ 不安全 |
| 扩容倍数 | 2 倍 | 1.5 倍 |
| 初始容量 | 10 | 10（1.8 延迟） |
| 效率 | 低 | 高 |
| 使用现状 | 已淘汰 | 主流 |

> ⚠️ **不要用 Vector**。需要线程安全用 `CopyOnWriteArrayList`（读多写少）或 `Collections.synchronizedList`。Vector 的子类 `Stack` 也已过时，用 `Deque` 替代。

---

## 七、ArrayList vs LinkedList vs Vector 对比 ⭐⭐

| 对比项 | ArrayList | LinkedList | Vector |
| :--- | :--- | :--- | :--- |
| 底层结构 | Object[] 数组 | 双向链表 | Object[] 数组 |
| 初始容量 | 10（1.8 延迟） | 0（空链表） | 10 |
| 扩容机制 | 1.5 倍 | 无需扩容 | 2 倍 |
| 查询 get | O(1) ⚡ | O(n) | O(1) |
| 末尾 add | O(1) 摊还 | O(1) | O(1) 摊还 |
| 中间增删 | O(n) 移动元素 | O(n) 定位 + O(1) 改指针 | O(n) |
| 首尾操作 | 头部增删 O(n) | O(1) ⚡ | 头部增删 O(n) |
| 线程安全 | ❌ | ❌ | ✅ synchronized |
| 内存占用 | 较小（连续数组） | 较大（每个节点多两个指针） | 较小 |
| 适用场景 | 通用查询、随机访问 | 频繁首尾增删、队列/栈 | 已淘汰 |
| 推荐度 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |

> 💡 **选型建议**：90% 的场景用 ArrayList。只有频繁在首尾增删、或需要队列/栈结构时才考虑 LinkedList。Vector 永远不要用。

---

## ⚠️ 重点

### 重点 1：ArrayList 的延迟初始化（1.7 vs 1.8）⭐⭐

```java
// JDK 1.7：new ArrayList() 直接创建 Object[10]，浪费内存
// JDK 1.8：new ArrayList() 指向空数组 {}，首次 add 才扩容到 10

List<String> list = new ArrayList<>();
// 1.8 此时 elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA（空数组）
list.add("A");
// 首次 add 触发 ensureCapacity，扩容到 10
```

> 💡 1.8 的延迟初始化是个优化：很多 ArrayList 创建后可能只存一两个元素甚至不存，延迟初始化避免了预分配 10 个槽位的浪费。

### 重点 2：ArrayList 指定初始容量避免扩容 ⭐⭐⭐

```java
// ❌ 反例：已知要存 1000 个元素，却用默认容量 10
List<Integer> list = new ArrayList<>();
for (int i = 0; i < 1000; i++) {
    list.add(i);   // 10→15→22→33→49→73→109→163→244→366→549→823→1234，扩容 12 次！
}

// ✅ 正例：预先指定容量
List<Integer> list2 = new ArrayList<>(1000);
for (int i = 0; i < 1000; i++) {
    list2.add(i);   // 0 次扩容
}
```

> 📌 **开发规范**：已知元素数量时，务必用 `new ArrayList<>(capacity)` 指定初始容量。这是阿里规约推荐，能显著提升性能。

### 重点 3：循环中删除元素的 ConcurrentModificationException ⭐⭐⭐

这是新手最常遇到的运行时异常：

```java
List<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("C");

// ❌ 错误 1：增强 for 中删除，抛 ConcurrentModificationException
for (String s : list) {
    if ("B".equals(s)) {
        list.remove(s);   // ❌ modCount != expectedModCount，抛异常
    }
}

// ❌ 错误 2：正序 for 删除，会漏删
for (int i = 0; i < list.size(); i++) {
    if ("B".equals(list.get(i))) {
        list.remove(i);   // 删除 B 后，C 前移到 B 的位置，i++ 跳过了 C
    }
}

// ✅ 正确 1：倒序删除（推荐，简单高效）
for (int i = list.size() - 1; i >= 0; i--) {
    if ("B".equals(list.get(i))) {
        list.remove(i);   // ✅ 倒序删，删除不影响前面未遍历的元素
    }
}

// ✅ 正确 2：迭代器删除（推荐，语义清晰）
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if ("B".equals(it.next())) {
        it.remove();   // ✅ 迭代器自己的 remove，同步 modCount
    }
}

// ✅ 正确 3：Java 8 removeIf（最简洁）
list.removeIf(s -> "B".equals(s));
```

> ⚠️ **fail-fast 机制**：ArrayList 内部有个 `modCount`（修改次数），迭代器创建时记录 `expectedModCount`。每次迭代都检查两者是否相等，不等就抛 `ConcurrentModificationException`。这是为了防止迭代过程中集合被修改导致数据错乱。

### 重点 4：List 存 Integer 时 remove 的歧义 ⭐⭐

```java
List<Integer> list = new ArrayList<>();
list.add(10);
list.add(20);
list.add(30);

// ⚠️ 歧义：remove(1) 是按索引删，还是按元素删 1？
list.remove(1);
System.out.println(list);  // [10, 30]，删除了索引 1 的元素（20）

// 想按元素删除 Integer 对象 10？
// list.remove(10);  // ❌ 会被当成 remove(10) 按索引删，IndexOutOfBoundsException
list.remove(Integer.valueOf(10));  // ✅ 显式传 Integer 对象，按元素删
System.out.println(list);  // [30]
```

> 💡 **原因**：`remove(int index)` 和 `remove(Object o)` 重载，编译器优先匹配 `remove(int)`。要按元素删 Integer，必须用 `Integer.valueOf()` 或强转。

### 重点 5：subList 返回的是视图，不是副本 ⭐⭐

```java
List<Integer> list = new ArrayList<>();
list.add(10);
list.add(20);
list.add(30);
list.add(40);
list.add(50);

List<Integer> sub = list.subList(1, 4);  // [20, 30, 40]
sub.set(0, 999);   // 修改子列表

System.out.println(sub);   // [999, 30, 40]
System.out.println(list);  // [10, 999, 30, 40, 50]，原列表也变了！

// ⚠️ 对原列表结构性修改（add/remove）后再操作子列表，抛异常
list.add(60);
// sub.get(0);  // ❌ ConcurrentModificationException
```

> ⚠️ `subList` 返回的是原 List 的**视图**（view），不是独立副本。修改子列表会影响原列表，反之亦然。要独立副本需 `new ArrayList<>(list.subList(1, 4))`。

### 重点 6：asList 的坑 ⭐⭐

```java
import java.util.Arrays;
import java.util.List;

Integer[] arr = {1, 2, 3};
List<Integer> list = Arrays.asList(arr);

// ⚠️ asList 返回的是 Arrays 的内部类，定长！
// list.add(4);  // ❌ UnsupportedOperationException

list.set(0, 999);   // ✅ 能修改
System.out.println(arr[0]);  // 999，原数组也变了（共享底层数组）

// ⚠️ 基本类型数组的坑
int[] primitiveArr = {1, 2, 3};
List<int[]> wrongList = Arrays.asList(primitiveArr);
System.out.println(wrongList.size());  // 1，整个数组被当成一个元素！

// ✅ 正确：用包装类型数组
Integer[] boxedArr = {1, 2, 3};
List<Integer> rightList = Arrays.asList(boxedArr);
System.out.println(rightList.size());  // 3

// ✅ 想要可变 List
List<Integer> mutable = new ArrayList<>(Arrays.asList(1, 2, 3));
mutable.add(4);  // ✅
```

---

## 💻 实战案例

### 案例 1：ArrayList 实现分页查询 ⭐⭐⭐

```java
import java.util.ArrayList;
import java.util.List;

class Page<T> {
    private List<T> data;     // 当前页数据
    private int pageNo;       // 当前页码
    private int pageSize;     // 每页条数
    private int total;        // 总记录数

    public Page(List<T> allData, int pageNo, int pageSize) {
        this.pageNo = pageNo;
        this.pageSize = pageSize;
        this.total = allData.size();
        int fromIndex = (pageNo - 1) * pageSize;
        int toIndex = Math.min(fromIndex + pageSize, total);
        // ⚠️ 边界处理：页码超出范围返回空页
        this.data = fromIndex >= total ? new ArrayList<>() : new ArrayList<>(allData.subList(fromIndex, toIndex));
    }

    public int getTotalPage() {
        return (total + pageSize - 1) / pageSize;
    }

    public void show() {
        System.out.println("第 " + pageNo + "/" + getTotalPage() + " 页，共 " + total + " 条");
        data.forEach(System.out::println);
    }
}

public class PaginationDemo {
    public static void main(String[] args) {
        // 模拟数据库查询出的 23 条订单
        List<String> allOrders = new ArrayList<>();
        for (int i = 1; i <= 23; i++) {
            allOrders.add("订单" + i);
        }

        // 查第 2 页，每页 10 条
        new Page<>(allOrders, 2, 10).show();
        // 第 2/3 页，共 23 条
        // 订单11, 订单12, ..., 订单20

        // 查第 3 页（最后一页，只有 3 条）
        new Page<>(allOrders, 3, 10).show();
        // 第 3/3 页，共 23 条
        // 订单21, 订单22, 订单23
    }
}
```

> 💡 分页是后台开发高频场景。`subList` 截取当前页数据，配合 `new ArrayList<>()` 包装成独立副本，避免视图污染。

### 案例 2：LinkedList 做队列与栈 ⭐⭐

```java
import java.util.LinkedList;
import java.util.Queue;
import java.util.Deque;

public class QueueStackDemo {
    public static void main(String[] args) {
        // —— 场景 1：消息队列（FIFO）——
        Queue<String> messageQueue = new LinkedList<>();
        // 生产者：发送消息
        messageQueue.offer("订单创建");
        messageQueue.offer("支付成功");
        messageQueue.offer("发货通知");
        // 消费者：处理消息
        while (!messageQueue.isEmpty()) {
            String msg = messageQueue.poll();  // 取出队头
            System.out.println("处理消息：" + msg);
        }
        // 处理消息：订单创建
        // 处理消息：支付成功
        // 处理消息：发货通知

        // —— 场景 2：撤销操作栈（LIFO）——
        Deque<String> undoStack = new LinkedList<>();
        // 用户操作入栈
        undoStack.push("输入文字");
        undoStack.push("修改样式");
        undoStack.push("插入图片");
        // Ctrl+Z 撤销
        while (!undoStack.isEmpty()) {
            System.out.println("撤销操作：" + undoStack.pop());
        }
        // 撤销操作：插入图片
        // 撤销操作：修改样式
        // 撤销操作：输入文字

        // —— 场景 3：最近访问记录（限制大小）——
        Deque<String> recentAccess = new LinkedList<>();
        recentAccess.push("页面A");
        recentAccess.push("页面B");
        recentAccess.push("页面C");
        // 限制只保留最近 2 条
        while (recentAccess.size() > 2) {
            recentAccess.removeLast();  // 移除最早的
        }
        System.out.println(recentAccess);  // [页面C, 页面B]
    }
}
```

### 案例 3：批量添加与删除（后台批量操作）

```java
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class BatchOperationDemo {
    public static void main(String[] args) {
        // —— 场景：后台批量导入用户 ——
        List<String> existingUsers = new ArrayList<>();
        existingUsers.add("user01");
        existingUsers.add("user02");

        // 批量添加新用户（从 Excel 导入）
        List<String> newUsers = Arrays.asList("user03", "user04", "user05");
        existingUsers.addAll(newUsers);
        System.out.println("导入后：" + existingUsers);
        // [user01, user02, user03, user04, user05]

        // —— 批量删除（删除选中用户）——
        List<String> selected = Arrays.asList("user02", "user04");
        // ⚠️ 批量删除用 removeAll
        existingUsers.removeAll(selected);
        System.out.println("删除后：" + existingUsers);
        // [user01, user03, user05]

        // —— 批量删除（Java 8 removeIf，按条件删除）——
        // 删除所有以 "user0" 开头的用户
        existingUsers.removeIf(u -> u.startsWith("user0"));
        System.out.println("条件删除后：" + existingUsers);  // []

        // —— 批量插入到指定位置 ——
        List<String> list = new ArrayList<>(Arrays.asList("A", "D", "E"));
        List<String> middle = Arrays.asList("B", "C");
        list.addAll(1, middle);  // 在索引 1 处批量插入
        System.out.println(list);  // [A, B, C, D, E]
    }
}
```

### 案例 4：subList 的坑与正确用法

```java
import java.util.ArrayList;
import java.util.List;

public class SubListTrap {
    public static void main(String[] args) {
        List<Integer> orders = new ArrayList<>();
        for (int i = 1; i <= 10; i++) {
            orders.add(1000 + i);  // 订单号 1001-1010
        }

        // ❌ 坑 1：修改 subList 影响原 List
        List<Integer> sub = orders.subList(0, 3);  // [1001, 1002, 1003]
        sub.set(0, 9999);
        System.out.println(orders.get(0));  // 9999，原 List 被改了！

        // ❌ 坑 2：原 List 结构修改后，操作 subList 抛异常
        orders.add(9999);
        try {
            sub.size();  // ❌ ConcurrentModificationException
        } catch (Exception e) {
            System.out.println("操作 subList 抛异常：" + e.getClass().getSimpleName());
        }

        // ✅ 正确：用 new ArrayList 包装成独立副本
        List<Integer> safeCopy = new ArrayList<>(orders.subList(0, 3));
        orders.add(8888);   // 修改原 List
        System.out.println(safeCopy.size());  // 3，副本不受影响
    }
}
```

> 📌 **规范**：`subList` 只适合临时只读视图场景。需要独立操作时，务必用 `new ArrayList<>(list.subList(...))` 包装成副本。

### 案例 5：循环中删除元素（电商过滤商品）

```java
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

class Product {
    String name;
    double price;
    int stock;

    Product(String name, double price, int stock) {
        this.name = name;
        this.price = price;
        this.stock = stock;
    }

    @Override
    public String toString() {
        return name + "(¥" + price + ", 库存" + stock + ")";
    }
}

public class FilterDemo {
    public static void main(String[] args) {
        List<Product> products = new ArrayList<>();
        products.add(new Product("Java书", 108.0, 50));
        products.add(new Product("键盘", 399.0, 0));     // 缺货
        products.add(new Product("鼠标", 99.0, 100));
        products.add(new Product("显示器", 1599.0, 0));  // 缺货
        products.add(new Product("耳机", 299.0, 30));

        // 需求：移除所有缺货商品（stock == 0）

        // ❌ 错误：增强 for 中删除，抛 ConcurrentModificationException
        // for (Product p : products) {
        //     if (p.stock == 0) products.remove(p);
        // }

        // ❌ 错误：正序删除会漏删（删除后元素前移，i++ 跳过）
        // for (int i = 0; i < products.size(); i++) {
        //     if (products.get(i).stock == 0) products.remove(i);
        // }

        // ✅ 正确 1：倒序删除
        for (int i = products.size() - 1; i >= 0; i--) {
            if (products.get(i).stock == 0) {
                products.remove(i);
            }
        }
        System.out.println("倒序删除后：" + products);

        // 重新构造数据
        products = new ArrayList<>();
        products.add(new Product("Java书", 108.0, 50));
        products.add(new Product("键盘", 399.0, 0));
        products.add(new Product("鼠标", 99.0, 100));
        products.add(new Product("显示器", 1599.0, 0));
        products.add(new Product("耳机", 299.0, 30));

        // ✅ 正确 2：迭代器删除
        Iterator<Product> it = products.iterator();
        while (it.hasNext()) {
            if (it.next().stock == 0) {
                it.remove();
            }
        }
        System.out.println("迭代器删除后：" + products);

        // 重新构造数据
        products = new ArrayList<>();
        products.add(new Product("Java书", 108.0, 50));
        products.add(new Product("键盘", 399.0, 0));
        products.add(new Product("鼠标", 99.0, 100));
        products.add(new Product("显示器", 1599.0, 0));
        products.add(new Product("耳机", 299.0, 30));

        // ✅ 正确 3：Java 8 removeIf（最简洁）
        products.removeIf(p -> p.stock == 0);
        System.out.println("removeIf 删除后：" + products);
        // [Java书(¥108.0, 库存50), 鼠标(¥99.0, 库存100), 耳机(¥299.0, 库存30)]
    }
}
```

> 💡 实际开发中，**Java 8 的 `removeIf` 是最推荐的删除方式**，代码简洁且不会抛异常。倒序删除和迭代器删除是 Java 8 之前的方案。

### 案例 6：ArrayList 动态扩容性能对比

```java
import java.util.ArrayList;
import java.util.List;

public class CapacityDemo {
    public static void main(String[] args) {
        int count = 1_000_000;

        // ❌ 不指定容量：多次扩容
        long start1 = System.currentTimeMillis();
        List<Integer> list1 = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            list1.add(i);
        }
        long end1 = System.currentTimeMillis();
        System.out.println("不指定容量：" + (end1 - start1) + "ms");

        // ✅ 指定容量：0 次扩容
        long start2 = System.currentTimeMillis();
        List<Integer> list2 = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            list2.add(i);
        }
        long end2 = System.currentTimeMillis();
        System.out.println("指定容量：" + (end2 - start2) + "ms");
        // 不指定容量通常比指定容量慢 2-3 倍
    }
}
```

> 💡 这个案例直观展示了指定初始容量的性能收益。百万级数据下，不指定容量会触发约 20 次扩容和数组拷贝。

---

## 🚀 新版本补充

### Java 9：List.of 不可变集合

```java
// Java 9 新增 List.of，创建不可变 List
List<String> list = List.of("A", "B", "C");
// list.add("D");  // ❌ UnsupportedOperationException
// list.set(0, "X");  // ❌ UnsupportedOperationException

// 与 Arrays.asList 的区别：
List<String> asList = Arrays.asList("A", "B", "C");
asList.set(0, "X");   // ✅ 可修改
// asList.add("D");   // ❌ 不可增删（定长）

// List.of 完全不可变，连 set 都不行
```

### Java 10：不可变集合拷贝

```java
// Java 10 新增 List.copyOf，创建不可变副本
List<String> original = new ArrayList<>();
original.add("A");
original.add("B");

List<String> copy = List.copyOf(original);
// copy.add("C");  // ❌ 不可变

original.add("C");
System.out.println(copy);  // [A, B]，副本不受原 List 影响
```

> ⚠️ Java 8 环境下 `List.of` 和 `List.copyOf` 不可用，需用 `Collections.unmodifiableList(new ArrayList<>(...))` 替代。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| List 特点 | 有序、有索引、允许重复 |
| List 特有方法 | add(index,e)/get/set/remove(index)/indexOf/lastIndexOf/subList |
| ArrayList 底层 | Object[] 数组，1.8 延迟初始化 |
| ArrayList 扩容 | 1.5 倍，Arrays.copyOf 拷贝 |
| ArrayList 性能 | 查询 O(1)，中间增删 O(n) |
| LinkedList 底层 | 双向链表 |
| LinkedList 性能 | 查询 O(n)，首尾增删 O(1) |
| LinkedList 特有 | addFirst/Last、getFirst/Last、push/pop |
| Vector | synchronized 线程安全，已淘汰 |
| 删除元素 | 倒序删 / 迭代器删 / removeIf，禁止增强 for 删 |
| subList | 返回视图，修改影响原 List |

---

## 学习建议

1. **ArrayList 是绝对主力，先吃透它**：90% 的 List 场景用 ArrayList。重点掌握底层 Object[] 结构、1.5 倍扩容、1.8 延迟初始化，这是面试高频考点。
2. **掌握循环删除元素的三种正确方式**：倒序删除、迭代器 remove、Java 8 removeIf。务必亲手写出 ConcurrentModificationException 的复现代码，理解 fail-fast 机制。
3. **LinkedList 别用 for+get 遍历**：这是性能灾难。LinkedList 只用迭代器或增强 for 遍历，首尾操作用 addFirst/removeFirst 等 O(1) 方法。
4. **已知数量就指定初始容量**：`new ArrayList<>(expectedSize)` 是性能优化的基本操作，尤其批量导入数据时，能省掉多次扩容拷贝。
5. **警惕 subList 和 asList 的视图陷阱**：两者返回的都不是独立副本，修改会影响原数据。需要独立操作时用 `new ArrayList<>()` 包装，这是生产环境常踩的坑。
