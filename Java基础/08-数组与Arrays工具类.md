# 数组与 Arrays 工具类

数组是 Java 中最基础的**引用数据类型**之一：一个容器，存储**同类型**的多个数据，长度**固定**，创建后不可改变。数组看似简单，但它的内存模型、默认值规则、引用赋值特性，是理解后续集合框架、参数传递、对象内存布局的根基——很多新手在数组上踩的坑（越界、空指针、引用混乱），会在整个 Java 学习生涯里反复出现。

> 💡 在阅读本篇前，建议先看 [02-JVM内存模型](02-JVM内存模型.md)，理解「栈存引用、堆存对象」的内存模型，会更容易理解下面的数组内存图与引用赋值。

---

## 一、数组概念与初始化

### 1.1 什么是数组

数组是一种**容器**，用来存储**同一类型**的多个数据。它有三个核心特征：

| 特征 | 说明 |
| :--- | :--- |
| 类型统一 | 数组中所有元素必须是同一数据类型 |
| 长度固定 | 创建后长度不可改变（这是数组与集合的最大区别） |
| 引用类型 | 数组本身是引用数据类型，对象在堆中，变量在栈中存地址 |

```java
// 数组是一种引用数据类型，不是基本类型
int[] arr = new int[3];   // ✅ 推荐写法：类型紧挨 []
int arr2[] = new int[3];  // ✅ C 风格写法，合法但不推荐
```

> 📌 **命名规范**：始终用 `int[] arr` 而非 `int arr[]`，前者更清晰地把 `int[]` 当作一个完整类型。

### 1.2 动态初始化（指定长度）

动态初始化只指定长度，由系统自动填充**默认值**：

```java
int[] arr = new int[3];      // 长度为 3，元素默认值全是 0
System.out.println(arr[0]);  // 0
System.out.println(arr[1]);  // 0
System.out.println(arr[2]);  // 0
```

**各类型动态初始化的默认值**：

| 数据类型 | 默认值 | 说明 |
| :--- | :---: | :--- |
| `byte` / `short` / `int` / `long` | `0` / `0L` | 整型默认 0 |
| `float` / `double` | `0.0f` / `0.0d` | 浮点默认 0.0 |
| `boolean` | `false` | 布尔默认 false |
| `char` | `'\0'` | 空字符（即 Unicode 0，打印为空白） |
| 引用类型（String 等） | `null` | 引用默认 null |

```java
int[] ints = new int[3];          // {0, 0, 0}
double[] doubles = new double[2]; // {0.0, 0.0}
boolean[] bools = new boolean[2]; // {false, false}
char[] chars = new char[3];      // {'\0', '\0', '\0'}
String[] names = new String[3];  // {null, null, null}
```

> ⚠️ `char` 的默认值 `'\0'` 不是空格 `' '`，而是 Unicode 编码为 0 的控制字符，打印出来什么都看不到。新手常误以为是空格。

### 1.3 静态初始化（指定内容）

静态初始化直接给出元素内容，系统自动推算长度：

```java
// 标准格式
int[] arr1 = new int[]{1, 2, 3, 4, 5};

// 简写格式（推荐）
int[] arr2 = {1, 2, 3, 4, 5};

// 两种格式完全等价，简写更简洁
System.out.println(arr1.length);  // 5
System.out.println(arr2.length);  // 5
```

> ⚠️ **简写格式的陷阱**：`{1, 2, 3}` 只能用在声明的同时赋值，不能拆成两步：

```java
int[] arr;
arr = {1, 2, 3};           // ❌ 编译错误：简写不能单独使用
arr = new int[]{1, 2, 3};  // ✅ 分两步必须用标准格式
```

> 💡 **记忆技巧**：简写 `{...}` 是「声明 + 赋值」的语法糖，一旦拆开就不再有声明上下文，编译器无法推断类型，必须用 `new int[]{...}` 显式指定。

---

## 二、数组访问与遍历

### 2.1 索引访问

数组通过**索引**（下标）访问元素，索引从 `0` 开始，到 `length - 1` 结束：

```java
int[] arr = {10, 20, 30, 40, 50};
System.out.println(arr[0]);        // 10，第一个元素
System.out.println(arr[4]);        // 50，最后一个元素
System.out.println(arr.length);    // 5，数组长度

arr[2] = 99;                       // 修改第三个元素
System.out.println(arr[2]);        // 99
```

> 📌 **索引范围**：`0` 到 `arr.length - 1`。这是数组最核心的规则，越界会直接抛异常。

### 2.2 数组遍历——for 循环

最基础的遍历方式，需要索引时用它：

```java
int[] arr = {10, 20, 30, 40, 50};

// 标准 for 循环，通过索引遍历
for (int i = 0; i < arr.length; i++) {
    System.out.println("索引 " + i + " 的值是 " + arr[i]);
}
```

### 2.3 数组遍历——增强 for（foreach）

不需要索引时用增强 for，代码更简洁：

```java
int[] arr = {10, 20, 30, 40, 50};

// 增强 for：只读元素，不涉及索引
for (int num : arr) {
    System.out.println(num);
}
```

> ⚠️ **foreach 的局限**：增强 for 中拿到的只是元素的**值拷贝**，无法通过它修改原数组：

```java
int[] arr = {1, 2, 3};
for (int num : arr) {
    num = 0;  // ❌ 只修改了临时变量 num，原数组不受影响
}
System.out.println(arr[0]);  // 1，没变

// ✅ 要修改原数组，必须用标准 for + 索引
for (int i = 0; i < arr.length; i++) {
    arr[i] = 0;
}
System.out.println(arr[0]);  // 0
```

### 2.4 常见异常

数组操作中最常见的两个运行时异常：

```java
// 异常 1：数组越界 ArrayIndexOutOfBoundsException
int[] arr = {1, 2, 3};
System.out.println(arr[3]);   // ❌ 运行时异常：索引 3 超出范围（0~2）
System.out.println(arr[-1]);  // ❌ 运行时异常：负索引也越界

// 异常 2：空指针 NullPointerException
int[] arr2 = null;
System.out.println(arr2[0]);  // ❌ 运行时异常：arr2 不指向任何对象
System.out.println(arr2.length); // ❌ 同样 NPE
```

> ⚠️ 这两个异常是**运行时异常**（RuntimeException），编译器不会强制检查，但运行时一旦触发程序直接崩溃。实际开发中，访问数组前务必确认索引在范围内、数组不为 null。

---

## 三、数组在内存中的存储

### 3.1 数组的内存结构

呼应 [02-JVM内存模型](02-JVM内存模型.md)：数组是引用类型，**数组对象在堆中**，**引用变量在栈中**。

```
栈（Stack）                    堆（Heap）
┌──────────┐                  ┌─────────────────────────┐
│ arr (地址)│ ──────────────→ │ int[] 对象              │
│ 0x001     │                 │ [0]=10  [1]=20  [2]=30  │
└──────────┘                  │ 地址：0x001              │
                              └─────────────────────────┘
```

```java
int[] arr = {10, 20, 30};  // arr 在栈中，保存堆中数组对象的地址
// arr 本质是一个指针，指向堆中的数组对象
```

### 3.2 两个数组指向同一地址（引用赋值）

这是理解引用类型的关键——赋值是**地址拷贝**，不是值拷贝：

```java
int[] arr1 = {1, 2, 3};
int[] arr2 = arr1;    // 把 arr1 的地址赋给 arr2，两个引用指向同一对象

System.out.println(arr1[0]);  // 1
arr2[0] = 99;                 // 通过 arr2 修改元素
System.out.println(arr1[0]);  // 99 —— arr1 也变了！因为它们指向同一块内存
```

内存图：

```
栈                              堆
┌──────────┐                  ┌─────────────────┐
│ arr1      │ ──────────────→ │ [0]=99  [1]=2    │
│ 0x001     │ ──┐             │  [2]=3          │
└──────────┘   │             │ 地址：0x001       │
┌──────────┐   │             └─────────────────┘
│ arr2      │ ──┘
│ 0x001     │
└──────────┘
```

> ⚠️ **新手最常踩的坑**：以为 `arr2 = arr1` 是复制了一个新数组。实际上两个变量指向**同一个对象**，改一个全变。如果要真正复制数组内容，用 `Arrays.copyOf()` 或循环逐个拷贝。

### 3.3 数组作为方法参数和返回值

数组作为引用类型，传递给方法时传的是**地址**，方法内修改会影响原数组：

```java
// 数组作为方法参数
public static void addOne(int[] arr) {
    for (int i = 0; i < arr.length; i++) {
        arr[i] += 1;  // 修改的是原数组
    }
}

int[] nums = {1, 2, 3};
addOne(nums);
System.out.println(nums[0]);  // 2，原数组被修改

// 数组作为方法返回值
public static int[] createArray(int n) {
    int[] arr = new int[n];
    for (int i = 0; i < n; i++) {
        arr[i] = i * i;  // 存平方值
    }
    return arr;  // 返回数组引用
}

int[] squares = createArray(5);
// squares = {0, 1, 4, 9, 16}
```

> 💡 **值传递的本质**：Java 只有值传递。对于引用类型，"值"就是地址。方法内拿到的是地址的副本，但这个副本和原变量指向同一对象，所以修改元素会生效。但重新赋值（`arr = new int[]{...}`）不会影响外部。

---

## 四、二维数组与 Arrays 工具类

### 4.1 二维数组

二维数组本质是「数组的数组」——每个元素本身又是一个一维数组：

```java
// 静态初始化
int[][] matrix = {
    {1, 2, 3},
    {4, 5, 6},
    {7, 8, 9}
};

// 动态初始化（规则二维数组）
int[][] grid = new int[3][4];  // 3 行 4 列，默认值全 0

// 动态初始化（不规则二维数组）
int[][] jagged = new int[3][];
jagged[0] = new int[]{1, 2};
jagged[1] = new int[]{3, 4, 5};
jagged[2] = new int[]{6};
```

> 💡 二维数组 `new int[3][4]` 表示有 3 个一维数组，每个一维数组有 4 个元素。第二维可以省略，后续单独创建每一行。

### 4.2 二维数组遍历

```java
int[][] matrix = {
    {1, 2, 3},
    {4, 5, 6},
    {7, 8, 9}
};

// 双重 for 循环遍历
for (int i = 0; i < matrix.length; i++) {         // matrix.length = 行数
    for (int j = 0; j < matrix[i].length; j++) {   // matrix[i].length = 列数
        System.out.print(matrix[i][j] + " ");
    }
    System.out.println();
}
// 输出：
// 1 2 3
// 4 5 6
// 7 8 9

// 增强 for 遍历
for (int[] row : matrix) {
    for (int num : row) {
        System.out.print(num + " ");
    }
    System.out.println();
}
```

### 4.3 二维数组的内存结构

二维数组在内存中并非真正的"矩阵"，而是「外层数组指向多个内层数组」：

```
栈                              堆
┌──────────┐                  ┌──────────────────┐
│ matrix    │ ──────────────→ │ 外层数组          │
│ 0x100     │                 │ [0]→0x200        │
└──────────┘                  │ [1]→0x300        │
                              │ [2]→0x400        │
                              └──────────────────┘
                  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
                  │ 内层数组 0x200    │  │ 内层数组 0x300    │  │ 内层数组 0x400    │
                  │ [1, 2, 3]        │  │ [4, 5, 6]        │  │ [7, 8, 9]        │
                  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

> 💡 理解这张图，就理解了二维数组：`matrix` 指向外层数组，外层数组的每个元素指向一个内层数组。所以 `matrix[0]` 是一个一维数组的引用，`matrix[0][0]` 才是真正的 int 值。

### 4.4 Arrays 工具类

`java.util.Arrays` 是 Java 提供的数组操作工具类，封装了常用的数组操作。所有方法都是**静态方法**，直接用类名调用。

#### toString()——数组转字符串

```java
import java.util.Arrays;

int[] arr = {3, 1, 4, 1, 5};
System.out.println(arr);              // [I@1540e19d，直接打印数组得到的是地址哈希
System.out.println(Arrays.toString(arr));  // [3, 1, 4, 1, 5]，可读格式

// 二维数组用 deepToString
int[][] matrix = {{1, 2}, {3, 4}};
System.out.println(Arrays.deepToString(matrix));  // [[1, 2], [3, 4]]
```

> ⚠️ 直接 `System.out.println(arr)` 打印的是地址（如 `[I@1540e19d`），`[I` 表示 int 数组，`@` 后是哈希码。调试时务必用 `Arrays.toString()`。

#### sort()——升序排序

```java
import java.util.Arrays;

int[] arr = {5, 2, 8, 1, 9, 3};
Arrays.sort(arr);  // 原地排序，修改原数组
System.out.println(Arrays.toString(arr));  // [1, 2, 3, 5, 8, 9]

// 部分排序：只排 [fromIndex, toIndex) 范围
int[] arr2 = {5, 2, 8, 1, 9, 3};
Arrays.sort(arr2, 1, 4);  // 只排索引 1~3 的元素
System.out.println(Arrays.toString(arr2));  // [5, 1, 2, 8, 9, 3]
```

> 💡 `Arrays.sort()` 对基本类型使用**双轴快速排序**（Dual-Pivot Quicksort），对引用类型使用**TimSort**（归并排序的优化版）。自定义对象的排序需要实现 `Comparable` 或传入 `Comparator`，这部分在集合篇详讲。

#### binarySearch()——二分查找

```java
import java.util.Arrays;

// 前提：数组必须已排序
int[] arr = {1, 3, 5, 7, 9, 11};
int index = Arrays.binarySearch(arr, 7);   // 返回索引 3
System.out.println(index);  // 3

// 找不到时返回 -(插入点 + 1)
int notFound = Arrays.binarySearch(arr, 6);
System.out.println(notFound);  // -4，表示 6 应插入索引 3 的位置

// ⚠️ 未排序的数组用 binarySearch，结果不可预期
int[] unsorted = {5, 1, 9, 3};
int bad = Arrays.binarySearch(unsorted, 9);  // ❌ 结果不确定
```

> ⚠️ `binarySearch` 的前提是数组**已排序**。如果对未排序的数组使用，不会报错，但返回值毫无意义。找不到时返回 `-(插入点 + 1)`，这个设计很巧妙——既能区分找到/找不到，又能直接算出应该插入的位置。

#### asList()——数组转集合

```java
import java.util.Arrays;
import java.util.List;

String[] arr = {"Java", "Python", "Go"};
List<String> list = Arrays.asList(arr);

System.out.println(list);  // [Java, Python, Go]
System.out.println(list.get(1));  // Python

// ⚠️ 陷阱 1：返回的是固定大小的 List，不能增删
// list.add("C++");     // ❌ UnsupportedOperationException
// list.remove(0);      // ❌ UnsupportedOperationException
list.set(0, "C");         // ✅ 可以修改元素，但原数组也跟着变

// ⚠️ 陷阱 2：修改数组会影响 List（底层是同一份数据）
System.out.println(arr[0]);  // C，被 set 改了

// ✅ 正确做法：包装成真正的 ArrayList
List<String> safe = new java.util.ArrayList<>(Arrays.asList(arr));
safe.add("C++");  // ✅ 没问题
```

> ⚠️ **Arrays.asList 的两个大坑**：
> 1. 返回的 `List` 是 `Arrays$ArrayList`（内部类），**不是** `java.util.ArrayList`，不支持 `add` / `remove`。
> 2. 返回的 List 与原数组**共享数据**，修改一方另一方跟着变。
>
> 📌 **开发规范**：如果需要对转出来的 List 增删，务必 `new ArrayList<>(Arrays.asList(...))` 包一层。

还有一个基本类型的坑：

```java
int[] nums = {1, 2, 3};
List<int[]> list = Arrays.asList(nums);  // ⚠️ 泛型不认 int[]
System.out.println(list.size());  // 1，整个数组被当成一个元素

// ✅ 基本类型数组要先转成包装类
Integer[] boxed = {1, 2, 3};
List<Integer> intList = Arrays.asList(boxed);  // size = 3
```

#### fill()——填充数组

```java
import java.util.Arrays;

int[] arr = new int[5];
Arrays.fill(arr, 66);  // 全部填充 66
System.out.println(Arrays.toString(arr));  // [66, 66, 66, 66, 66]

// 部分填充 [fromIndex, toIndex)
int[] arr2 = {1, 2, 3, 4, 5};
Arrays.fill(arr2, 1, 3, 0);  // 索引 1~2 填 0
System.out.println(Arrays.toString(arr2));  // [1, 0, 0, 4, 5]
```

#### copyOf()——复制数组

```java
import java.util.Arrays;

int[] original = {1, 2, 3, 4, 5};

// copyOf：从索引 0 开始复制，指定新长度
int[] copy1 = Arrays.copyOf(original, 3);   // {1, 2, 3}，截断
int[] copy2 = Arrays.copyOf(original, 7);   // {1, 2, 3, 4, 5, 0, 0}，扩容补默认值

// copyOfRange：复制指定范围 [from, to)
int[] copy3 = Arrays.copyOfRange(original, 1, 4);  // {2, 3, 4}

// 底层等价于 System.arraycopy
int[] copy4 = new int[3];
System.arraycopy(original, 0, copy4, 0, 3);  // {1, 2, 3}
```

> 💡 `Arrays.copyOf` 底层调用 `System.arraycopy`，这是 native 方法，性能比手动循环拷贝高。扩容时多出来的位置填默认值（int 填 0）。

#### equals()——比较数组内容

```java
import java.util.Arrays;

int[] a = {1, 2, 3};
int[] b = {1, 2, 3};
int[] c = a;

System.out.println(a == b);            // false，== 比较的是地址
System.out.println(a.equals(b));      // false，数组没重写 equals，还是比较地址
System.out.println(Arrays.equals(a, b));  // true，逐元素比较内容
System.out.println(a == c);            // true，c 和 a 指向同一对象

// 二维数组用 deepEquals
int[][] m1 = {{1, 2}, {3, 4}};
int[][] m2 = {{1, 2}, {3, 4}};
System.out.println(Arrays.equals(m1, m2));       // false，比较的是外层引用
System.out.println(Arrays.deepEquals(m1, m2));   // true，深度比较
```

> ⚠️ 数组本身**没有重写** `equals()` 方法（继承自 Object），所以 `a.equals(b)` 比较的仍是地址。比较内容必须用 `Arrays.equals()`。

### 4.5 数组与集合的对比

| 对比项 | 数组 | 集合（如 ArrayList） |
| :--- | :--- | :--- |
| 长度 | 固定，创建后不可变 | 可变，自动扩容 |
| 类型 | 可以存基本类型，也可以存引用类型 | 只能存引用类型（基本类型靠自动装箱） |
| 效率 | 高，连续内存，无扩容开销 | 略低，有装箱/拆箱、扩容开销 |
| 功能 | 基础，只有索引访问 | 丰富，有 add/remove/contains 等大量方法 |
| 适用场景 | 长度已知、性能敏感、基本类型批量操作 | 长度不确定、需要频繁增删、业务逻辑复杂 |

```java
// 数组：长度固定，效率高
int[] arr = new int[100];
for (int i = 0; i < 100; i++) {
    arr[i] = i * 2;  // 直接存基本类型，无装箱开销
}

// 集合：长度可变，功能丰富
java.util.ArrayList<Integer> list = new java.util.ArrayList<>();
list.add(1);  // 自动装箱 int → Integer
list.add(2);
list.remove(0);  // 可以删除，数组做不到
```

> 📌 **选择原则**：长度确定且需要存基本类型 → 用数组；长度不确定或需要频繁增删 → 用集合。实际开发中集合用得更多，但数组在底层源码、性能敏感场景中无处不在。

---

## ⚠️ 重点

### 重点 1：数组长度固定，创建后不可改变 ⭐⭐

```java
int[] arr = new int[5];
arr = new int[10];  // ✅ 这是让 arr 指向新数组，原数组没变
// 原 5 长度的数组仍在堆中（等待 GC），arr 指向了新的 10 长度数组
```

> ⚠️ 数组长度在 `new` 的时候就确定了，之后**无法改变**。`arr = new int[10]` 不是"扩容"，而是创建新数组并让引用指向它。真正的动态扩容要用 `ArrayList` 或 `Arrays.copyOf`（本质也是新建数组）。

### 重点 2：索引从 0 到 length-1，越界报异常 ⭐⭐

```java
int[] arr = {1, 2, 3};
// 有效索引：0, 1, 2（即 0 到 length-1）
System.out.println(arr[0]);  // ✅ 1
System.out.println(arr[2]);  // ✅ 3
System.out.println(arr[3]);  // ❌ ArrayIndexOutOfBoundsException
```

> 📌 **编码规范**：遍历数组永远用 `i < arr.length`，不要硬编码长度（如 `i < 5`），防止数组长度变化后越界。

### 重点 3：动态初始化的默认值规则 ⭐

```java
int[] nums = new int[3];      // {0, 0, 0}
String[] strs = new String[3]; // {null, null, null}
boolean[] flags = new boolean[2]; // {false, false}
```

> 💡 **记忆口诀**：整型 0、浮点 0.0、布尔 false、字符 '\0'、引用 null。和成员变量的默认值规则完全一致——因为数组元素存在堆中，和对象的成员变量一样会被初始化为默认值。

### 重点 4：数组是引用类型，赋值是地址拷贝 ⭐⭐

```java
int[] a = {1, 2, 3};
int[] b = a;      // 地址拷贝，a 和 b 指向同一数组
b[0] = 99;
System.out.println(a[0]);  // 99，a 也被改了

// ✅ 真正的内容拷贝
int[] c = Arrays.copyOf(a, a.length);
c[0] = 0;
System.out.println(a[0]);  // 99，a 不受影响
```

> ⚠️ 这是引用类型最核心的特性。`b = a` 不是复制数组，而是让两个变量指向**同一对象**。要复制内容，用 `Arrays.copyOf()`、`System.arraycopy()` 或 `clone()`。

### 重点 5：数组为 null 时调用任何方法都 NPE ⭐

```java
int[] arr = null;
// arr 还不指向任何数组对象
System.out.println(arr.length);  // ❌ NullPointerException
System.out.println(arr[0]);      // ❌ NullPointerException

// ✅ 正确：先 new 再用
int[] arr2 = new int[3];
System.out.println(arr2.length);  // 3
```

> ⚠️ `null` 表示"不指向任何对象"。对 null 引用调用任何方法/字段都会抛 `NullPointerException`。实际开发中，接收外部传入的数组前应做 null 检查：
> ```java
> if (arr != null && arr.length > 0) {
>     // 安全访问
> }
> ```

### 重点 6：Arrays.asList 的坑 ⭐⭐

```java
String[] arr = {"A", "B", "C"};
List<String> list = Arrays.asList(arr);

list.add("D");  // ❌ UnsupportedOperationException
arr[0] = "X";
System.out.println(list.get(0));  // X，数组改了 List 也变
```

> ⚠️ `Arrays.asList()` 返回的是 `Arrays` 的内部类 `ArrayList`（注意不是 `java.util.ArrayList`），它**固定大小**、**与原数组共享数据**。需要增删时务必 `new ArrayList<>(Arrays.asList(...))`。

---

## 💻 实战案例

### 案例 1：学生成绩统计（求 max/min/avg/sum）⭐

后台系统中，对一批成绩做统计分析是最常见的数组应用：

```java
public class ScoreStats {
    public static void main(String[] args) {
        double[] scores = {85.5, 92.0, 78.5, 96.0, 88.0, 73.5, 91.0};

        double max = scores[0];
        double min = scores[0];
        double sum = 0;

        for (double score : scores) {
            if (score > max) max = score;
            if (score < min) min = score;
            sum += score;
        }

        double avg = sum / scores.length;

        System.out.println("最高分：" + max);      // 96.0
        System.out.println("最低分：" + min);      // 73.5
        System.out.println("总分：" + sum);        // 604.5
        System.out.println("平均分：" + avg);      // 86.357...
    }
}
```

> 💡 实际开发中，成绩统计常配合 `Arrays.sort()` 先排序，再取首尾元素即得 min/max。但若只需极值不需排序，遍历一次 O(n) 比排序 O(n log n) 更高效。

### 案例 2：数组反转

```java
public class ArrayReverse {
    public static void main(String[] args) {
        int[] arr = {1, 2, 3, 4, 5};

        // 双指针对调
        for (int i = 0, j = arr.length - 1; i < j; i++, j--) {
            int temp = arr[i];
            arr[i] = arr[j];
            arr[j] = temp;
        }
        System.out.println(Arrays.toString(arr));  // [5, 4, 3, 2, 1]
    }
}
```

### 案例 3：冒泡排序 ⭐

经典排序算法，面试常考，理解排序的基础：

```java
public class BubbleSort {
    public static void main(String[] args) {
        int[] arr = {64, 34, 25, 12, 22, 11, 90};

        // 外层：n-1 轮
        for (int i = 0; i < arr.length - 1; i++) {
            // 内层：每轮把最大值"冒泡"到末尾
            for (int j = 0; j < arr.length - 1 - i; j++) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
        System.out.println(Arrays.toString(arr));
        // [11, 12, 22, 25, 34, 64, 90]
    }
}
```

> 💡 冒泡排序时间复杂度 O(n²)，实际开发中不会手写，直接用 `Arrays.sort()`。但面试常考，且它是理解排序思想的入门。

### 案例 4：选择排序

```java
public class SelectionSort {
    public static void main(String[] args) {
        int[] arr = {64, 25, 12, 22, 11};

        for (int i = 0; i < arr.length - 1; i++) {
            int minIndex = i;
            // 每轮找最小值的索引
            for (int j = i + 1; j < arr.length; j++) {
                if (arr[j] < arr[minIndex]) {
                    minIndex = j;
                }
            }
            // 把最小值交换到当前位置
            int temp = arr[i];
            arr[i] = arr[minIndex];
            arr[minIndex] = temp;
        }
        System.out.println(Arrays.toString(arr));
        // [11, 12, 22, 25, 64]
    }
}
```

### 案例 5：用 Arrays.sort 给成绩排序 ⭐

实际开发中直接用工具类，一行搞定：

```java
import java.util.Arrays;

public class SortScores {
    public static void main(String[] args) {
        double[] scores = {85.5, 92.0, 78.5, 96.0, 88.0};

        Arrays.sort(scores);  // 升序
        System.out.println("升序：" + Arrays.toString(scores));
        // [78.5, 85.5, 88.0, 92.0, 96.0]

        // 降序：排序后反转
        // 基本类型没有直接降序 API，反转即可
        for (int i = 0, j = scores.length - 1; i < j; i++, j--) {
            double temp = scores[i];
            scores[i] = scores[j];
            scores[j] = temp;
        }
        System.out.println("降序：" + Arrays.toString(scores));
        // [96.0, 92.0, 88.0, 85.5, 78.5]
    }
}
```

### 案例 6：Arrays.binarySearch 查找元素 ⭐

电商系统中，在已排序的 SKU 列表中查找商品：

```java
import java.util.Arrays;

public class ProductSearch {
    public static void main(String[] args) {
        // 商品 ID 已排序
        int[] productIds = {1001, 1005, 1010, 1020, 1050, 1080, 1100};

        int target = 1020;
        int index = Arrays.binarySearch(productIds, target);

        if (index >= 0) {
            System.out.println("找到商品，位置：" + index);
        } else {
            System.out.println("未找到，应插入位置：" + (-(index + 1)));
        }
        // 输出：找到商品，位置：3
    }
}
```

> ⚠️ `binarySearch` 返回值 >= 0 表示找到，< 0 表示没找到。没找到时，`-(返回值 + 1)` 就是应该插入的位置，这个设计非常实用。

### 案例 7：Arrays.asList 的坑——修改数组影响 List ⭐⭐

```java
import java.util.Arrays;
import java.util.List;
import java.util.ArrayList;

public class AsListTrap {
    public static void main(String[] args) {
        String[] names = {"张三", "李四", "王五"};

        // ❌ 坑 1：不能增删
        List<String> list = Arrays.asList(names);
        // list.add("赵六");  // 抛 UnsupportedOperationException

        // ❌ 坑 2：修改数组影响 List
        names[0] = "改了";
        System.out.println(list.get(0));  // 改了，List 跟着变

        // ✅ 正确：包装成真正的 ArrayList
        List<String> safe = new ArrayList<>(Arrays.asList(names));
        safe.add("赵六");  // 没问题
        safe.remove(0);    // 没问题
        System.out.println(safe);  // [李四, 王五, 赵六]
    }
}
```

### 案例 8：可变参数与数组

Java 的可变参数（varargs）本质就是数组，底层编译为数组传递：

```java
public class VarargsDemo {
    // 可变参数：本质是 int[] params
    public static int sum(int... params) {
        int total = 0;
        for (int num : params) {
            total += num;
        }
        return total;
    }

    public static void main(String[] args) {
        System.out.println(sum(1, 2, 3));        // 6
        System.out.println(sum(1, 2, 3, 4, 5)); // 15
        System.out.println(sum());               // 0，空数组

        // 也可以直接传数组
        int[] arr = {10, 20, 30};
        System.out.println(sum(arr));  // 60
    }
}
```

> 💡 `int... params` 在编译后等价于 `int[] params`。调用时可以传任意个参数，也可以直接传一个数组。可变参数必须是方法的**最后一个参数**。

### 案例 9：批量数据处理——数组作为方法参数和返回值

模拟后台系统中批量处理用户数据：

```java
import java.util.Arrays;

public class BatchProcessor {
    // 过滤出及格的成绩（>= 60），返回新数组
    public static int[] filterPass(int[] scores) {
        if (scores == null) {
            return new int[0];  // 防御性编程：返回空数组而非 null
        }

        // 第一遍：数及格的有几个
        int count = 0;
        for (int score : scores) {
            if (score >= 60) count++;
        }

        // 第二遍：填入新数组
        int[] result = new int[count];
        int index = 0;
        for (int score : scores) {
            if (score >= 60) {
                result[index++] = score;
            }
        }
        return result;
    }

    public static void main(String[] args) {
        int[] scores = {45, 78, 90, 55, 61, 88, 30, 72};
        int[] passed = filterPass(scores);
        System.out.println("及格成绩：" + Arrays.toString(passed));
        // [78, 90, 61, 88, 72]

        Arrays.sort(passed);
        System.out.println("排序后：" + Arrays.toString(passed));
        // [61, 72, 78, 88, 90]
    }
}
```

> 📌 **开发规范**：方法返回数组时，宁可返回**空数组**（`new int[0]`）也不要返回 `null`，这样调用方无需做 null 检查，减少 NPE 风险。这是《Effective Java》的推荐做法。

### 案例 10：电商订单金额统计

```java
import java.util.Arrays;

public class OrderStats {
    public static void main(String[] args) {
        // 模拟一批订单金额（单位：分，避免浮点精度问题）
        int[] orderAmounts = {19900, 8800, 15600, 4500, 29900, 12800};

        // 统计
        int total = 0;
        int maxOrder = orderAmounts[0];
        int minOrder = orderAmounts[0];
        for (int amount : orderAmounts) {
            total += amount;
            if (amount > maxOrder) maxOrder = amount;
            if (amount < minOrder) minOrder = amount;
        }

        System.out.println("订单总数：" + orderAmounts.length);
        System.out.println("总金额：" + total + " 分 = " + total / 100.0 + " 元");
        System.out.println("最高单笔：" + maxOrder + " 分 = " + maxOrder / 100.0 + " 元");
        System.out.println("最低单笔：" + minOrder + " 分 = " + minOrder / 100.0 + " 元");
        System.out.println("客单价：" + (total / orderAmounts.length) + " 分 = "
                         + (total / orderAmounts.length / 100.0) + " 元");

        // 排序后看分布
        int[] sorted = Arrays.copyOf(orderAmounts, orderAmounts.length);
        Arrays.sort(sorted);
        System.out.println("金额分布（升序）：" + Arrays.toString(sorted));
    }
}
```

> 💡 注意这里金额用**分（int）**存储而非**元（double）**，这是支付系统的常见做法——用整数避免浮点精度问题，呼应 [04-数据类型与类型转换](04-数据类型与类型转换.md) 中 BigDecimal 的教训。

---

## 🚀 新版本补充

### Java 9：Arrays.mismatch()

找出两个数组第一个不同元素的索引：

```java
import java.util.Arrays;

int[] a = {1, 2, 3, 4, 5};
int[] b = {1, 2, 9, 4, 5};
int idx = Arrays.mismatch(a, b);  // 2，索引 2 处不同
System.out.println(idx);

int[] c = {1, 2, 3};
int[] d = {1, 2, 3};
System.out.println(Arrays.mismatch(c, d));  // -1，完全相同
```

### Java 9：Arrays.compare()

按字典序比较两个数组：

```java
import java.util.Arrays;

int[] a = {1, 2, 3};
int[] b = {1, 2, 4};
System.out.println(Arrays.compare(a, b));  // 负数，a < b

int[] c = {1, 2, 3};
int[] d = {1, 2, 3};
System.out.println(Arrays.compare(c, d));  // 0，相等
```

### Java 8：Arrays.parallelSort()（补充）

并行排序，利用多核 CPU 加速大数组排序：

```java
import java.util.Arrays;

int[] bigArr = new int[1000000];
// 填充随机数据
for (int i = 0; i < bigArr.length; i++) {
    bigArr[i] = (int)(Math.random() * 1000000);
}

Arrays.parallelSort(bigArr);  // 并行排序，大数组时比 sort() 快
// 小数组时 parallelSort 内部会退化为普通 sort
```

> 💡 `parallelSort` 将数组分成多块，在 ForkJoinPool 中并行排序后合并。数据量大（上万以上）时才有优势，小数据反而有线程调度开销。

### Java 8：Stream 与数组互操作

```java
import java.util.Arrays;
import java.util.stream.IntStream;

int[] arr = {3, 1, 4, 1, 5, 9, 2, 6};

// 数组转 Stream 操作
int sum = Arrays.stream(arr).sum();           // 求和
int max = Arrays.stream(arr).max().getAsInt(); // 最大值
long count = Arrays.stream(arr).filter(x -> x > 3).count();  // 大于 3 的个数

System.out.println("sum=" + sum + ", max=" + max + ", count=" + count);
// sum=31, max=9, count=4

// Stream 转回数组
int[] filtered = Arrays.stream(arr).filter(x -> x > 3).toArray();
System.out.println(Arrays.toString(filtered));  // [4, 5, 9, 6]
```

> 💡 Java 8 的 Stream API 让数组操作更函数式、更简洁。但 Stream 属于 Java 8 基准内容，这里只是展示它与数组的互操作，详细用法见函数式编程篇。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 数组概念 | 容器，存同类型多个数据，长度固定，引用类型 |
| 动态初始化 | `new int[3]`，指定长度，元素填默认值 |
| 静态初始化 | `new int[]{1,2,3}` 或 `{1,2,3}`，指定内容 |
| 默认值 | 整型 0、浮点 0.0、布尔 false、char '\0'、引用 null |
| 索引范围 | 0 到 length-1，越界抛 ArrayIndexOutOfBoundsException |
| 内存结构 | 数组对象在堆，引用变量在栈 |
| 引用赋值 | `b = a` 是地址拷贝，两个引用指向同一对象 |
| 空指针 | 数组为 null 时访问任何属性/方法都 NPE |
| 二维数组 | 数组的数组，外层指向多个内层数组 |
| Arrays.toString | 数组转可读字符串 |
| Arrays.sort | 升序排序，可指定范围 |
| Arrays.binarySearch | 二分查找，前提已排序，找不到返回 -(插入点+1) |
| Arrays.asList | 数组转 List，固定大小且与原数组共享数据 |
| Arrays.copyOf | 复制数组，可截断或扩容 |
| Arrays.equals | 逐元素比较内容（数组本身 equals 比的是地址） |
| 数组 vs 集合 | 数组长度固定效率高，集合长度可变功能多 |

---

## 学习建议

1. **画内存图理解引用**：拿纸画出「栈中引用 → 堆中数组对象」的内存图，特别是「两个变量指向同一数组」的场景。理解了这张图，后续集合、参数传递、对象内存模型都会豁然开朗，不要死记代码。
2. **牢记五个默认值**：整型 0、浮点 0.0、布尔 false、字符 '\0'、引用 null。和成员变量默认值一致——因为它们都在堆中。面试常考，开发常踩。
3. **手写一遍冒泡排序**：不是为了用，而是为了理解排序思想和双重循环。写完后再对比 `Arrays.sort()` 一行代码搞定，体会工具类的价值。
4. **把 Arrays.asList 的坑刻进脑子**：固定大小、与数组共享数据——这两个特性在实际开发中坑了无数人。养成习惯：需要增删就 `new ArrayList<>(Arrays.asList(...))` 包一层。
5. **区分 == 和 Arrays.equals**：数组用 `==` 比的是地址，用 `equals`（未重写）比的还是地址，只有 `Arrays.equals` 比的是内容。这个区别在调试和单元测试中极其重要，务必形成肌肉记忆。
