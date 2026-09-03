# 迭代器与增强for

集合是用来「装一堆数据」的，但装进去只是第一步，真正有价值的是「把数据取出来用」——这就是**遍历**。Java 集合框架提供了一套统一的遍历机制：`Iterator`（迭代器）。几乎所有集合（`List`、`Set`）都能通过迭代器遍历，而增强 for（foreach）和 Java 8 的 `forEach` 底层都依赖它。理解迭代器，尤其是 **fail-fast 机制**，是避免 `ConcurrentModificationException` 的关键——这是开发中极高频的踩坑点。

> 💡 在阅读本篇前，建议先看 [24-集合框架体系与Collection](24-集合框架体系与Collection.md)，了解 `Collection` 接口的基本方法，再来理解迭代器会顺理成章。

---

## 一、迭代器 Iterator 接口

### 1.1 什么是迭代器

迭代器是一种**设计模式**：提供一种方法，按顺序访问一个集合中的元素，而又不暴露集合的内部结构（是数组还是链表，调用者无需关心）。

Java 用 `java.util.Iterator` 接口统一了集合的遍历方式：

```java
public interface Iterator<E> {
    boolean hasNext();   // 判断是否还有下一个元素
    E next();             // 取出下一个元素，并后移游标
    default void remove(); // 从集合中删除 next() 刚返回的元素（可选操作）
    // default void forEachRemaining(Consumer)  Java 8 新增，本篇末尾讲
}
```

> 💡 **迭代器像「光标」**：想象迭代器是一个指针，初始指向第一个元素**之前**的位置。`hasNext()` 检查后面有没有元素，`next()` 把光标后移一位并返回它刚跳过的那个元素。

### 1.2 获取迭代器

`Collection` 接口继承了 `Iterable` 接口，因此每个集合都有 `iterator()` 方法用来获取迭代器：

```java
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

List<String> list = new ArrayList<>();
list.add("张三");
list.add("李四");
list.add("王五");

// 获取迭代器
Iterator<String> it = list.iterator();
```

> ⚠️ **每次调用 `iterator()` 都返回一个新的迭代器对象**，光标重置到起点。不要把一个迭代器对象在多处复用，也不要跨方法传递。

### 1.3 遍历集合的标准流程

迭代器遍历集合的固定套路是「`hasNext` 判断 + `next` 取值」：

```java
List<String> list = new ArrayList<>();
list.add("张三");
list.add("李四");
list.add("王五");

Iterator<String> it = list.iterator();
while (it.hasNext()) {        // ✅ 还有下一个才取
    String s = it.next();     // ✅ 取出下一个并后移
    System.out.println(s);
}
// 输出：张三 / 李四 / 王五
```

> ⚠️ **最常见的错误**：不判断 `hasNext` 直接 `next`，集合为空或越界时抛 `NoSuchElementException`：

```java
Iterator<String> it = list.iterator();
String s = it.next();   // ❌ 若集合为空，抛 java.util.NoSuchElementException
```

---

## 二、迭代器的 remove() 方法

### 2.1 为什么需要迭代器的 remove

遍历集合时想删除某些元素，是开发中极高频的需求（比如「删除所有已下架商品」）。但直接用集合的 `remove` 方法会出大问题：

```java
List<Integer> list = new ArrayList<>();
list.add(1);
list.add(2);
list.add(3);

// ❌ 错误：边遍历边用集合的 remove
Iterator<Integer> it = list.iterator();
while (it.hasNext()) {
    Integer n = it.next();
    if (n == 2) {
        list.remove(n);   // ❌ 抛 ConcurrentModificationException
    }
}
```

运行上面代码，会在删除元素后下一次调用 `next()` 时抛出 `ConcurrentModificationException`——这就是 **fail-fast（快速失败）机制**，本篇的重点，下面专门讲。

### 2.2 正确做法：用迭代器的 remove

```java
List<Integer> list = new ArrayList<>();
list.add(1);
list.add(2);
list.add(3);

// ✅ 正确：用迭代器自己的 remove
Iterator<Integer> it = list.iterator();
while (it.hasNext()) {
    Integer n = it.next();
    if (n == 2) {
        it.remove();   // ✅ 删除「最近一次 next 返回的元素」，不抛异常
    }
}
System.out.println(list);  // [1, 3]
```

> 📌 **规范**：遍历过程中要删除元素，**必须用迭代器的 `remove()`**，不能用集合的 `remove(Object)` 或 `remove(int)`。这是面试高频考点，也是开发高频 bug。

### 2.3 remove 的使用限制

`it.remove()` 只能删除**最近一次 `next()` 返回的元素**，且不能连续调用两次：

```java
Iterator<Integer> it = list.iterator();
it.remove();   // ❌ 还没调用 next 就 remove，抛 IllegalStateException

it.next();     // 取出第一个
it.remove();   // ✅ 删除第一个
it.remove();   // ❌ 连续 remove，上次 next 的元素已被删，抛 IllegalStateException
it.next();     // 必须再 next 一次才能继续 remove
it.remove();   // ✅
```

> 💡 **记忆要点**：`remove` 必须紧跟在 `next` 之后，且一次 `next` 只能配一次 `remove`。可以理解为 `remove` 删的是「光标刚跨过的那个元素」。

---

## 三、fail-fast 机制（重点⭐⭐）

### 3.1 ConcurrentModificationException 的产生原因

`ArrayList` 等集合内部维护一个变量 `modCount`（modification count，修改计数）。**每次对集合做结构性修改**（add、remove、clear）都会让 `modCount + 1`。

获取迭代器时，迭代器会把当前的 `modCount` 记录到自己的 `expectedModCount` 字段。之后每次调用 `next()` / `remove()`，迭代器都会检查：

```java
// ArrayList 内部迭代器的检查逻辑（简化版）
if (modCount != expectedModCount) {
    throw new ConcurrentModificationException();
}
```

也就是说：**迭代器遍历期间，一旦发现集合的 `modCount` 和自己记录的不一致，就认为集合被「别人」改过了，立即抛异常**，避免后续遍历出现不可预期的结果（越界、漏元素、死循环）。

```
集合 modCount = 3
迭代器 expectedModCount = 3（获取时拷贝）

遍历中：
  集合.remove(...) → modCount 变成 4
  迭代器.next() → 检查 4 != 3 → 抛 ConcurrentModificationException
```

> ⚠️ **fail-fast 是「尽力而为」」机制**：它用 `modCount` 检测，但这个检查并非线程安全（没有加锁）。在多线程并发修改时，它**可能**抛异常，**也可能不抛**（取决于时序），所以不能用 fail-fast 来保证线程安全，真正的并发要用 `CopyOnWriteArrayList` 等并发集合（见 [40-JUC并发包](40-JUC并发包.md)）。

### 3.2 为什么迭代器的 remove 不抛异常

因为迭代器的 `remove()` 在删除元素后，会**同步更新自己的 `expectedModCount`**，让它和集合的 `modCount` 重新保持一致：

```java
// ArrayList 迭代器的 remove（简化版）
public void remove() {
    // ...删除元素...
    modCount++;              // 集合 modCount +1
    expectedModCount = modCount;  // ✅ 同步更新，保持一致
    // ...
}
```

所以「迭代器自己删 → 自己更新计数 → 继续遍历」是一条闭环安全的路径，而「集合直接删 → 迭代器不知道 → 下次 next 发现不一致」就会炸。

### 3.3 增强 for 不能修改集合

增强 for 的**底层就是迭代器**（下一节详解），所以它同样受 fail-fast 约束：

```java
List<Integer> list = new ArrayList<>();
list.add(1);
list.add(2);
list.add(3);

// ❌ 增强 for 里调用集合的 remove
for (Integer n : list) {
    if (n == 2) {
        list.remove(n);   // ❌ 抛 ConcurrentModificationException
    }
}
```

> 📌 **铁律**：增强 for 循环体内**不能**调用集合的 `add` / `remove` / `clear` 等结构性修改方法。要边遍历边删，只能用迭代器的 `remove()`，或者用 Java 8 的 `removeIf`（本篇末尾讲）。

### 3.4 一个隐蔽的「假阳性不报错」案例

注意 fail-fast 的检查时机是 `next()`，不是 `hasNext()`。如果删除发生在最后一次 `next()` 之后，就**不会**抛异常——但这只是巧合，不能依赖：

```java
List<Integer> list = new ArrayList<>();
list.add(1);
list.add(2);

for (Integer n : list) {
    if (n == 2) {
        list.remove(Integer.valueOf(2));  // 表面没抛异常！
    }
}
// 原因：删完 2 后 hasNext 返回 false，循环结束，没机会再 next 触发检查
System.out.println(list);  // [1]
```

> ⚠️ 这不是「安全删除」，而是「侥幸没报错」。换个删除条件（比如删 `1`）或换个集合大小，立刻就会抛异常。**永远不要依赖这个行为**，统一用迭代器 `remove` 或 `removeIf`。

---

## 四、Iterable 接口与增强 for

### 4.1 Iterable 接口

`java.lang.Iterable` 接口只有一个核心方法（Java 8 后多了两个 default 方法）：

```java
public interface Iterable<T> {
    Iterator<T> iterator();   // 提供迭代器

    // Java 8 新增：
    default void forEach(Consumer<? super T> action) { ... }
    default Spliterator<T> spliterator() { ... }
}
```

`Collection` 接口继承了 `Iterable`，所以所有集合都「可迭代」。**实现 `Iterable` 接口的类都能用增强 for**——这是增强 for 的底层依据。

### 4.2 增强 for（foreach）的格式

```java
for (元素类型 变量名 : 集合或数组) {
    // 使用变量名
}
```

遍历集合：

```java
List<String> list = new ArrayList<>();
list.add("张三");
list.add("李四");

for (String s : list) {     // ✅ 增强 for 遍历集合
    System.out.println(s);
}
```

遍历数组：

```java
int[] arr = {10, 20, 30};
for (int n : arr) {         // ✅ 增强 for 也能遍历数组（底层是普通 for + 下标）
    System.out.println(n);
}
```

### 4.3 增强 for 的本质

增强 for 是**语法糖**。对集合而言，编译器会把它翻译成迭代器写法：

```java
// 你写的：
for (String s : list) {
    System.out.println(s);
}

// 编译器翻译后（等价）：
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    String s = it.next();
    System.out.println(s);
}
```

对数组而言，增强 for 翻译成普通下标 for：

```java
// 你写的：
for (int n : arr) { ... }

// 编译器翻译后：
for (int i = 0; i < arr.length; i++) {
    int n = arr[i];
    // ...
}
```

> 💡 **结论**：增强 for 没有任何性能优势，只是写法简洁。它有两个局限：① 不能拿到下标；② 不能边遍历边删（受 fail-fast 限制）。需要下标或需要修改集合时，用普通 for 或迭代器。

### 4.4 自定义类实现 Iterable

任何自定义类只要实现 `Iterable`，就能用增强 for：

```java
import java.util.Iterator;

// 一个简单的整数范围类，实现 Iterable 后可用增强 for
public class IntRange implements Iterable<Integer> {
    private final int start;
    private final int end;

    public IntRange(int start, int end) {
        this.start = start;
        this.end = end;
    }

    @Override
    public Iterator<Integer> iterator() {
        return new Iterator<Integer>() {
            private int current = start;

            @Override
            public boolean hasNext() {
                return current < end;
            }

            @Override
            public Integer next() {
                if (!hasNext()) {
                    throw new java.util.NoSuchElementException();
                }
                return current++;
            }
        };
    }

    public static void main(String[] args) {
        IntRange range = new IntRange(1, 5);
        for (int n : range) {   // ✅ 自定义类也能用增强 for
            System.out.println(n);  // 1 2 3 4
        }
    }
}
```

> 💡 这就是 `for (String s : myList)` 能工作的根本原因——`List` 实现了 `Iterable`。理解这一点，就理解了增强 for 的全部秘密。

---

## 五、ListIterator：List 专有的双向迭代器

### 5.1 ListIterator 的能力

`ListIterator` 是 `Iterator` 的子接口，**只有 `List` 体系**（`ArrayList`、`LinkedList` 等）能通过 `list.listIterator()` 获取。它比普通 `Iterator` 多了以下能力：

| 能力 | Iterator | ListIterator |
| :--- | :---: | :---: |
| 正向遍历 `hasNext`/`next` | ✅ | ✅ |
| **反向遍历** `hasPrevious`/`previous` | ❌ | ✅ |
| **添加** `add(E)` | ❌ | ✅ |
| **修改** `set(E)` | ❌ | ✅ |
| 获取下标 `nextIndex`/`previousIndex` | ❌ | ✅ |

### 5.2 双向遍历

```java
import java.util.ArrayList;
import java.util.List;
import java.util.ListIterator;

List<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("C");

// 正向遍历
ListIterator<String> it = list.listIterator();
while (it.hasNext()) {
    System.out.println(it.next() + " 下标=" + it.nextIndex());
}
// A 下标=1 / B 下标=2 / C 下标=3

// 反向遍历：光标已到末尾，可以往回走
while (it.hasPrevious()) {
    System.out.println(it.previous() + " 下标=" + it.previousIndex());
}
// C 下标=2 / B 下标=1 / A 下标=0
```

> 💡 **反向遍历的前提**：光标得先到末尾。可以 `list.listIterator(list.size())` 直接从末尾开始，也可以正向遍历完再反向。

### 5.3 add 与 set

```java
List<String> list = new ArrayList<>();
list.add("A");
list.add("C");

ListIterator<String> it = list.listIterator();
it.next();        // 跳过 A，光标在 A 和 C 之间
it.add("B");      // ✅ 在光标处插入 B（不影响光标位置）
// list 现在是 [A, B, C]

it.next();        // 跳过 C
it.set("D");      // ✅ 把最近 next 返回的 C 改成 D
// list 现在是 [A, B, D]
```

> ⚠️ `set` 和迭代器 `remove` 一样，要求**先调用 `next` 或 `previous`** 才能用，否则抛 `IllegalStateException`。`add` 则没有这个限制。

---

## 六、迭代器的惰性求值

### 6.1 迭代器是「按需取值」的

迭代器不是一次性把所有元素算好给你，而是**每次 `next()` 才计算/取出下一个**。这叫**惰性求值（lazy evaluation）」。

最典型的例子是某些「无限集合」或「按需生成」的迭代器：

```java
import java.util.Iterator;

// 一个「无限自然数」迭代器，不会内存溢出，因为按需生成
public class NaturalNumbers implements Iterable<Long> {
    @Override
    public Iterator<Long> iterator() {
        return new Iterator<Long>() {
            private long current = 0;

            @Override
            public boolean hasNext() {
                return true;   // 永远有下一个
            }

            @Override
            public Long next() {
                return current++;
            }
        };
    }

    public static void main(String[] args) {
        NaturalNumbers naturals = new NaturalNumbers();
        long sum = 0;
        int count = 0;
        for (long n : naturals) {        // 不会 OOM
            sum += n;
            if (++count == 100) break;   // 只取前 100 个
        }
        System.out.println(sum);  // 0+1+...+99 = 4950
    }
}
```

> 💡 这种「按需取值」的思想在 Java 8 的 `Stream` 中被发扬光大——`Stream` 也是惰性的，终端操作（`collect`、`forEach`）触发时才真正计算。详见 [46-函数式编程](46-函数式编程.md)。

### 6.2 惰性求值的意义

- **节省内存**：不需要预先把所有元素放进内存，适合大文件逐行读取、数据库游标查询。
- **支持无限序列**：上面这种「无限自然数」用普通 List 根本存不下，但迭代器可以。
- **延迟计算**：元素在被 `next` 取出时才真正生成，可以反映生成时的最新状态。

---

## 七、遍历方式对比

Java 集合有四种主流遍历方式，各有适用场景：

```java
List<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("C");

// 方式 1：普通 for + 下标（只有 List 能用，Set/Map 不行）
for (int i = 0; i < list.size(); i++) {
    System.out.println(list.get(i));
}

// 方式 2：迭代器（所有 Collection 通用）
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    System.out.println(it.next());
}

// 方式 3：增强 for（语法糖，底层=迭代器，最简洁）
for (String s : list) {
    System.out.println(s);
}

// 方式 4：Java 8 forEach + Lambda（最现代，函数式风格）
list.forEach(s -> System.out.println(s));
list.forEach(System.out::println);   // ✅ 方法引用更简洁
```

| 遍历方式 | 适用范围 | 能否拿下标 | 能否边遍历边删 | 性能 | 简洁度 |
| :--- | :--- | :---: | :---: | :--- | :---: |
| 普通 for + get | 仅 List | ✅ | ❌（会漏元素/越界） | List 随机访问快 | 一般 |
| 迭代器 | 所有 Collection | ❌ | ✅（用 `it.remove`） | 好 | 一般 |
| 增强 for | Collection + 数组 | ❌ | ❌（fail-fast） | 同迭代器 | 高 |
| forEach + Lambda | 所有 Iterable | ❌ | ❌（fail-fast） | 好 | 最高 |

> ⚠️ **普通 for + 集合 remove 的坑**：即使不抛异常（List 的 `remove(int)` 改了 `modCount`，但普通 for 不检查 fail-fast），也会**漏删元素**——因为删除后后面的元素前移，下标却 +1 了：

```java
List<Integer> list = new ArrayList<>();
list.add(2);
list.add(2);
list.add(2);

// ❌ 想删除所有 2，结果只删了两个
for (int i = 0; i < list.size(); i++) {
    if (list.get(i) == 2) {
        list.remove(i);   // 删了 i=0，后面的 2 前移到 0，但 i 变成 1，漏了
    }
}
System.out.println(list);  // [2]，还剩一个没删掉
```

> 📌 **结论**：要边遍历边删，**唯一安全的方式是迭代器 `remove()` 或 `removeIf`**。普通 for + `remove` 既会漏元素，List 还会触发 fail-fast。

---

## ⚠️ 重点

### 重点 1：fail-fast 与 ConcurrentModificationException ⭐⭐

遍历集合时，只要用了迭代器（含增强 for、`forEach`），就**不能在循环体内直接调用集合的 `add`/`remove`/`clear`**，否则抛 `ConcurrentModificationException`。

```java
// ❌ 三种都会抛异常
for (String s : list) {
    list.remove(s);        // ❌
}
for (String s : list) {
    list.add("x");         // ❌
}
list.forEach(s -> list.clear());  // ❌
```

```java
// ✅ 正确：迭代器 remove
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if (it.next().equals("x")) {
        it.remove();
    }
}

// ✅ 正确（Java 8+）：removeIf，底层就是迭代器 remove
list.removeIf(s -> s.equals("x"));
```

> 💡 `removeIf` 是 Java 8 给 `Collection` 加的 default 方法，内部封装了「迭代器 + remove」的安全删除逻辑，是现代 Java 删除元素的首选。

### 重点 2：迭代器 remove 的使用规范 ⭐

- 必须先 `next()`（或 `previous()`）再 `remove()`，否则抛 `IllegalStateException`
- 一次 `next` 只能配一次 `remove`
- 只删「最近一次 next 返回的元素」，不能指定删谁

```java
Iterator<String> it = list.iterator();
it.remove();            // ❌ 还没 next
it.next();
it.remove();
it.remove();            // ❌ 连续 remove
it.next();
it.remove();           // ✅
```

### 重点 3：增强 for 的两个局限 ⭐

1. **拿不到下标**：需要下标时（比如打印「第 i 个」）只能用普通 for
2. **不能修改集合**：底层是迭代器，受 fail-fast 限制，不能 add/remove

```java
// ❌ 想知道当前是第几个，增强 for 做不到
for (String s : list) {
    // 没有 i 可用
}

// ✅ 需要下标用普通 for
for (int i = 0; i < list.size(); i++) {
    System.out.println(i + ": " + list.get(i));
}
```

### 重点 4：ListIterator 与 Iterator 的区别 ⭐

| 特性 | Iterator | ListIterator |
| :--- | :--- | :--- |
| 适用范围 | 所有 Collection | 仅 List |
| 方向 | 只能正向 | 可双向 |
| 修改 | 只能 remove | 可 remove/add/set |
| 下标 | 无 | 有 nextIndex/previousIndex |

> 💡 需要在遍历中**插入或替换**元素时（普通迭代器只能删），用 `ListIterator`。

### 重点 5：遍历 List 用普通 for 还是迭代器 ⭐

- **`ArrayList`**（随机访问）：普通 for `get(i)` 和迭代器性能接近，要下标用 for，要删用迭代器
- **`LinkedList`**（链表）：**绝对不要用普通 for + `get(i)`**！`get(i)` 每次从头数到 i，复杂度 O(n)，整体 O(n²)

```java
LinkedList<String> linked = new LinkedList<>();
// 假设有 10 万元素
for (int i = 0; i < linked.size(); i++) {   // ❌ O(n²)，极慢
    System.out.println(linked.get(i));
}
// ✅ 用迭代器或增强 for，O(n)
for (String s : linked) {
    System.out.println(s);
}
```

> ⚠️ 这是 `LinkedList` 最隐蔽的性能陷阱。`get(i)` 对链表是灾难。判断依据：实现了 `RandomAccess` 接口（如 `ArrayList`）才适合普通 for + get。

---

## 💻 实战案例

### 案例 1：遍历删除符合条件的元素（电商下架商品清理）⭐⭐

电商后台，一个商品列表，需要把所有「已下架」的商品从在售列表中移除：

```java
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

class Product {
    String name;
    boolean onSale;   // 是否在售
    Product(String name, boolean onSale) {
        this.name = name;
        this.onSale = onSale;
    }
    public String toString() { return name + (onSale ? "(在售)" : "(下架)"); }
}

public class ProductCleaner {
    public static void main(String[] args) {
        List<Product> products = new ArrayList<>();
        products.add(new Product("iPhone", true));
        products.add(new Product("旧款手机", false));   // 下架
        products.add(new Product("iPad", true));
        products.add(new Product("旧款平板", false));   // 下架

        // ❌ 错误写法 1：增强 for + 集合 remove → ConcurrentModificationException
        // for (Product p : products) {
        //     if (!p.onSale) products.remove(p);
        // }

        // ❌ 错误写法 2：普通 for + 集合 remove → 漏删
        // for (int i = 0; i < products.size(); i++) {
        //     if (!products.get(i).onSale) products.remove(i);
        // }

        // ✅ 正确写法 1：迭代器 remove
        Iterator<Product> it = products.iterator();
        while (it.hasNext()) {
            if (!it.next().onSale) {
                it.remove();
            }
        }
        System.out.println("迭代器删除后：" + products);
        // [iPhone(在售), iPad(在售)]

        // ✅ 正确写法 2（Java 8+）：removeIf，最简洁
        products.add(new Product("旧款手表", false));
        products.removeIf(p -> !p.onSale);   // 一行搞定
        System.out.println("removeIf 删除后：" + products);
    }
}
```

> 📌 **开发规范**：Java 8 项目里，批量删除元素优先用 `removeIf`，它内部就是安全的迭代器删除，一行代码替代整个 while 循环。

### 案例 2：ListIterator 倒序遍历（金融：按时间倒序展示交易流水）

金融系统展示用户最近交易流水，数据已按时间正序存入 List，需要倒序输出（最新的在前）：

```java
import java.util.ArrayList;
import java.util.List;
import java.util.ListIterator;

class Transaction {
    String time;
    double amount;
    Transaction(String time, double amount) {
        this.time = time;
        this.amount = amount;
    }
    public String toString() { return time + " 交易 ¥" + amount; }
}

public class TransactionViewer {
    public static void main(String[] args) {
        List<Transaction> flow = new ArrayList<>();
        flow.add(new Transaction("09:00", 100.0));
        flow.add(new Transaction("10:30", 200.0));
        flow.add(new Transaction("14:00", 50.0));   // 最新

        // ✅ 用 ListIterator 从末尾倒序遍历
        ListIterator<Transaction> it = flow.listIterator(flow.size());
        while (it.hasPrevious()) {
            System.out.println(it.previous());
        }
        // 14:00 交易 ¥50.0
        // 10:30 交易 ¥200.0
        // 09:00 交易 ¥100.0
    }
}
```

> 💡 倒序遍历也可以用普通 for：`for (int i = list.size()-1; i >= 0; i--)`。但 `ListIterator` 的优势是能同时 `set`/`add`——比如倒序遍历时顺便修正某条记录。

### 案例 3：ListIterator 遍历中替换元素（后台：批量修正数据）

后台数据清洗：把所有状态为「待审核」的订单标记为「已审核」，并在其后插入一条审核日志：

```java
import java.util.ArrayList;
import java.util.List;
import java.util.ListIterator;

class Order {
    String id;
    String status;
    Order(String id, String status) { this.id = id; this.status = status; }
    public String toString() { return id + "[" + status + "]"; }
}

public class OrderAudit {
    public static void main(String[] args) {
        List<Order> orders = new ArrayList<>();
        orders.add(new Order("O001", "待审核"));
        orders.add(new Order("O002", "已审核"));
        orders.add(new Order("O003", "待审核"));

        ListIterator<Order> it = orders.listIterator();
        while (it.hasNext()) {
            Order o = it.next();
            if ("待审核".equals(o.status)) {
                o.status = "已审核";
                it.set(o);                          // ✅ 替换当前元素
                it.add(new Order(o.id + "-log", "审核日志"));  // ✅ 在其后插入日志
            }
        }
        System.out.println(orders);
        // [O001[已审核], O001-log[审核日志], O002[已审核], O003[已审核], O003-log[审核日志]]
    }
}
```

> 💡 普通迭代器只能 `remove`，要 `set`/`add` 必须用 `ListIterator`。这是 `ListIterator` 最不可替代的场景。

### 案例 4：forEach + Lambda 遍历统计（电商：统计购物车总金额）

```java
import java.util.ArrayList;
import java.util.List;

class CartItem {
    String name;
    double price;
    int qty;
    CartItem(String name, double price, int qty) {
        this.name = name; this.price = price; this.qty = qty;
    }
}

public class CartTotal {
    public static void main(String[] args) {
        List<CartItem> cart = new ArrayList<>();
        cart.add(new CartItem("书", 50.0, 2));
        cart.add(new CartItem("笔", 10.0, 5));
        cart.add(new CartItem("本", 5.0, 10));

        // ✅ forEach + Lambda，外部变量需是 final 或事实 final
        double[] total = {0};   // 用数组绕过 Lambda 的 final 限制
        cart.forEach(item -> {
            total[0] += item.price * item.qty;
        });
        System.out.println("购物车总金额：¥" + total[0]);  // 200.0

        // ✅ 更地道的写法：Java 8 Stream + reduce（见函数式编程篇）
        double sum = cart.stream()
                .mapToDouble(item -> item.price * item.qty)
                .sum();
        System.out.println("Stream 求和：¥" + sum);  // 200.0
    }
}
```

> ⚠️ **Lambda 中引用外部局部变量的坑**：变量必须是 final 或事实 final。上面用 `double[]` 包装是为了在 Lambda 内修改值。更推荐用 `Stream` 的 `mapToDouble + sum`，函数式风格更干净。

### 案例 5：自定义 Iterable 实现分页遍历（后台：游标式遍历大数据）

模拟「分页从数据库取数据」的迭代器，避免一次性把百万数据加载进内存：

```java
import java.util.Iterator;
import java.util.NoSuchElementException;

// 模拟数据库分页查询的迭代器
public class PagedUserIterator implements Iterable<String> {
    private final int pageSize;
    private final int totalPages;

    public PagedUserIterator(int pageSize, int totalPages) {
        this.pageSize = pageSize;
        this.totalPages = totalPages;
    }

    // 模拟「查第 page 页」
    private String[] queryPage(int page) {
        String[] rows = new String[pageSize];
        for (int i = 0; i < pageSize; i++) {
            rows[i] = "user-" + page + "-" + i;
        }
        return rows;
    }

    @Override
    public Iterator<String> iterator() {
        return new Iterator<String>() {
            private int currentPage = 0;     // 当前已查到第几页
            private String[] buffer;         // 当前页的缓存
            private int indexInPage = 0;     // 当前页内下标

            @Override
            public boolean hasNext() {
                // 当前页还有数据，或还有下一页可查
                return (buffer != null && indexInPage < buffer.length)
                        || currentPage < totalPages;
            }

            @Override
            public String next() {
                if (!hasNext()) throw new NoSuchElementException();
                if (buffer == null || indexInPage >= buffer.length) {
                    buffer = queryPage(currentPage);   // 惰性加载下一页
                    currentPage++;
                    indexInPage = 0;
                }
                return buffer[indexInPage++];
            }
        };
    }

    public static void main(String[] args) {
        PagedUserIterator users = new PagedUserIterator(3, 3);  // 每页 3 条，共 3 页
        int count = 0;
        for (String u : users) {   // 不会一次性加载所有数据
            System.out.println(u);
            count++;
        }
        System.out.println("共遍历 " + count + " 条");  // 9
    }
}
```

> 💡 这就是 MyBatis 等框架「游标查询」的思想：用迭代器按需取数，避免 OOM。理解了惰性求值，就理解了这种模式。

---

## 🚀 新版本补充

### Java 8：forEach 与 removeIf（属于基准内容，此处仅说明归属）

`forEach(Consumer)` 和 `removeIf(Predicate)` 是 Java 8 给 `Iterable`/`Collection` 加的 default 方法，属于 Java 8 基准内容，已在正文重点讲解。它们底层都依赖迭代器，受 fail-fast 约束（`removeIf` 例外，它内部用安全删除）。

### Java 9：不可变集合的迭代器

Java 9 的 `List.of()` / `Set.of()` 创建的不可变集合，迭代器**不支持 `remove`**：

```java
// Java 9+
List<Integer> immutable = List.of(1, 2, 3);
Iterator<Integer> it = immutable.iterator();
it.next();
it.remove();   // ❌ 抛 UnsupportedOperationException
```

### Java 10+：不可变集合拷贝

`List.copyOf(list)`（Java 10）创建不可变副本，同样不支持迭代器 `remove`，遍历删除时要注意。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Iterator 接口 | `hasNext()` 判断、`next()` 取值、`remove()` 安全删除 |
| 获取迭代器 | `collection.iterator()`，每次返回新对象 |
| remove 规范 | 必须先 next 再 remove，一次 next 配一次 remove |
| fail-fast 机制 | 遍历时 modCount 变化 → `ConcurrentModificationException` |
| 安全删除 | 迭代器 `remove()` 或 Java 8 `removeIf(Predicate)` |
| Iterable 接口 | 实现 `iterator()`，是增强 for 的底层依据 |
| 增强 for | 语法糖，集合→迭代器，数组→普通 for；不能修改集合 |
| ListIterator | List 专有，可双向遍历、可 add/set |
| 惰性求值 | 每次 next 才取值，支持无限序列、节省内存 |
| 遍历方式 | for+get（仅 List）、迭代器、增强 for、forEach+Lambda |
| LinkedList 遍历 | 链表禁用 for+get（O(n²)），用迭代器或增强 for |

---

## 学习建议

1. **先把 fail-fast 搞透**：`ConcurrentModificationException` 是开发中极高频的异常，务必亲手敲一遍「错误删除」代码，观察异常抛出的时机，再对照 `modCount`/`expectedModCount` 的原理理解为什么迭代器 `remove` 不报错。
2. **形成删除元素的肌肉记忆」：边遍历边删只有两条安全路径——迭代器 `remove()` 或 `removeIf`。Java 8 项目优先 `removeIf`，一行代码替代整个 while 循环，既安全又简洁。
3. **区分 Iterator 和 ListIterator 的使用场景**：只需要删用 `Iterator`，需要插入/替换/倒序用 `ListIterator`。自己写一遍「遍历中替换元素」的代码，体会 `ListIterator` 不可替代之处。
4. **警惕 LinkedList 的 for+get 陷阱**：这是最隐蔽的性能坑，记住「非 RandomAccess 集合不要用下标遍历」。可以用 `instanceof RandomAccess` 判断，或干脆统一用迭代器/增强 for。
5. **理解惰性求值，为 Stream 打基础**：迭代器「按需取值」的思想是 Java 8 `Stream` 的前身。自己实现一个「无限序列」迭代器（如自然数、斐波那契），能加深对惰性求值的理解，学 [46-函数式编程](46-函数式编程.md) 时会事半功倍。
