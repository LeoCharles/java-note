# 数学运算：Math 与 BigDecimal

Java 的数学运算看似简单——`+`、`-`、`*`、`/` 谁都会写——但一旦涉及金额、利率、精度控制，`double` 就会原形毕露：`0.1 + 0.2` 算出 `0.30000000000000004`，账目对不上，财务系统直接崩盘。Java 提供了三套应对方案：`Math` 类封装常用数学函数，`BigDecimal` 提供精确的十进制运算，`BigInteger` 应对超大整数。理解它们，是写出正确金融、电商、统计代码的底线——很多线上事故（金额算错、利率偏差、对账失败）都根源于此。

> 💡 在阅读本篇前，建议先看 [04-数据类型与类型转换](04-数据类型与类型转换.md) 中"浮点数精度丢失"一节，理解 `double` 为什么算不准，再看 [19-包装类](19-包装类.md) 了解基本类型与对象的区别，会更容易理解 `BigDecimal` 的不可变性。

---

## 一、Math 类

`java.lang.Math` 提供了一系列静态方法做数学运算，所有方法都是 `static`，直接用类名调用，无需 import。

### 1.1 常用方法总览

| 方法 | 功能 | 示例 | 结果 |
| :--- | :--- | :--- | :--- |
| `abs(a)` | 绝对值 | `Math.abs(-5)` | `5` |
| `ceil(a)` | 向上取整 | `Math.ceil(3.1)` | `4.0` |
| `floor(a)` | 向下取整 | `Math.floor(3.9)` | `3.0` |
| `round(a)` | 四舍五入 | `Math.round(3.5)` | `4` |
| `max(a, b)` | 最大值 | `Math.max(3, 5)` | `5` |
| `min(a, b)` | 最小值 | `Math.min(3, 5)` | `3` |
| `pow(a, b)` | a 的 b 次方 | `Math.pow(2, 10)` | `1024.0` |
| `sqrt(a)` | 平方根 | `Math.sqrt(16)` | `4.0` |
| `cbrt(a)` | 立方根 | `Math.cbrt(27)` | `3.0` |
| `random()` | [0,1) 随机数 | `Math.random()` | `0.xxx` |
| `signum(a)` | 符号函数 | `Math.signum(-5)` | `-1.0` |
| `PI` | 圆周率常量 | `Math.PI` | `3.141592653589793` |
| `E` | 自然常数 | `Math.E` | `2.718281828459045` |

```java
// 基础运算
System.out.println(Math.abs(-10));      // 10
System.out.println(Math.max(3, 7));     // 7
System.out.println(Math.min(3, 7));     // 3
System.out.println(Math.pow(2, 10));    // 1024.0
System.out.println(Math.sqrt(144));     // 12.0
System.out.println(Math.PI);           // 3.141592653589793
```

### 1.2 取整方法详解

三个取整方法容易混淆，务必区分：

```java
// ceil：向上取整（往大的方向）
System.out.println(Math.ceil(3.1));    // 4.0
System.out.println(Math.ceil(3.0));    // 3.0
System.out.println(Math.ceil(-3.1));   // -3.0（负数往大的方向，-3 > -3.1）

// floor：向下取整（往小的方向）
System.out.println(Math.floor(3.9));   // 3.0
System.out.println(Math.floor(3.0));   // 3.0
System.out.println(Math.floor(-3.1));  // -4.0（负数往小的方向，-4 < -3.1）

// round：四舍五入（返回 long/int，不是 double）
System.out.println(Math.round(3.4));   // 3
System.out.println(Math.round(3.5));   // 4
System.out.println(Math.round(-3.5)); // -3（注意：负数 .5 向上取整）
System.out.println(Math.round(-3.6));  // -4
```

> ⚠️ **取整方向记忆**：
> - `ceil`（天花板）→ 向上，往大里取
> - `floor`（地板）→ 向下，往小里取
> - `round` → 四舍五入，返回 `long`/`int`（不是 `double`）
>
> 负数时尤其要小心：`Math.round(-3.5)` 是 `-3` 而不是 `-4`，因为 Java 的 round 是"四舍六入五成双"的变体（实际是 `floor(a + 0.5)`）。

### 1.3 Math.random() 随机数

`Math.random()` 返回 `[0.0, 1.0)` 的 `double`：

```java
// [0, 1) 的 double
double r = Math.random();
System.out.println(r);   // 0.xxx

// [0, 10) 的整数
int n = (int)(Math.random() * 10);
System.out.println(n);   // 0~9

// [1, 100] 的整数（注意闭区间）
int m = (int)(Math.random() * 100) + 1;
System.out.println(m);   // 1~100
```

> 💡 `Math.random()` 底层是 `new Random()` 的语法糖，每次调用都新建一个 Random 实例，性能不如直接用 `Random` 或 `ThreadLocalRandom`。

### 1.4 三角与指数函数

```java
System.out.println(Math.sin(Math.PI / 2));    // 1.0，正弦
System.out.println(Math.cos(0));              // 1.0，余弦
System.out.println(Math.tan(0));              // 0.0，正切
System.out.println(Math.toRadians(180));      // 3.14159...，角度转弧度
System.out.println(Math.toDegrees(Math.PI));  // 180.0，弧度转角度

System.out.println(Math.log(Math.E));         // 1.0，自然对数
System.out.println(Math.log10(1000));         // 3.0，以 10 为底
System.out.println(Math.exp(1));              // 2.718...，e 的 x 次方
```

### 1.5 Math.abs 的负数陷阱

```java
System.out.println(Math.abs(-100));    // 100，正常

// ⚠️ 坑：int 最小值的绝对值溢出
System.out.println(Math.abs(Integer.MIN_VALUE));   // -2147483648！还是负数
System.out.println(Math.abs(Long.MIN_VALUE));       // -9223372036854775808，同样
```

> ⚠️ **原理**：`int` 范围是 `[-2^31, 2^31-1]`，正数最大是 `2147483647`，而 `Integer.MIN_VALUE` 是 `-2147483648`，它的绝对值 `2147483648` 超出了 `int` 正数范围，溢出后又变回负数。这是 `Math.abs` 最隐蔽的坑，金融校验中若用 `abs` 判断正负，可能漏掉边界值。

---

## 二、Random 类

`java.util.Random` 是更可控的随机数生成器，可指定种子、生成各种类型的随机数。

### 2.1 基本用法

```java
import java.util.Random;

Random random = new Random();

// 随机 int（含负数）
int i = random.nextInt();
System.out.println(i);

// 随机 int [0, bound)
int n = random.nextInt(100);    // 0~99
System.out.println(n);

// 随机 double [0, 1)
double d = random.nextDouble();
System.out.println(d);

// 随机 boolean
boolean b = random.nextBoolean();
System.out.println(b);

// 随机 long
long l = random.nextLong();
System.out.println(l);
```

### 2.2 种子（seed）

传入相同种子，生成的随机数序列**完全一致**——这在测试和复现问题时很有用：

```java
// 相同种子，相同序列
Random r1 = new Random(42);
Random r2 = new Random(42);
System.out.println(r1.nextInt(100));   // 71
System.out.println(r2.nextInt(100));   // 71，和 r1 相同
System.out.println(r1.nextInt(100));   // 29
System.out.println(r2.nextInt(100));   // 29，依然相同
```

> 💡 **种子的本质**：Random 是伪随机数生成器，基于线性同余算法。给定相同初始种子，后续序列完全确定。无参构造 `new Random()` 用当前时间作种子，所以每次运行结果不同。测试时用固定种子可复现问题。

### 2.3 Random vs Math.random()

| 对比项 | `Math.random()` | `Random` |
| :--- | :--- | :--- |
| 返回类型 | `double [0,1)` | int/long/double/boolean 等 |
| 种子 | 不可控（时间） | 可指定 |
| 性能 | 每次新建 Random | 复用同一实例 |
| 适用场景 | 简单随机 | 需要多种类型、可复现 |

```java
// 简单场景用 Math.random
int n = (int)(Math.random() * 10);   // 0~9

// 复杂场景用 Random
Random r = new Random();
int a = r.nextInt(6) + 1;    // 骰子 1~6
boolean flag = r.nextBoolean();
```

---

## 三、ThreadLocalRandom（Java 7+）

多线程下用 `Random` 会有竞争（内部用 CAS 保证线程安全，但性能损耗）。Java 7 引入 `ThreadLocalRandom`，每个线程独立一个实例，无竞争，性能更高。

```java
import java.util.concurrent.ThreadLocalRandom;

// 获取当前线程的实例（无需 new）
ThreadLocalRandom tr = ThreadLocalRandom.current();

int n = tr.nextInt(1, 101);    // [1, 101)，即 1~100
double d = tr.nextDouble(0.0, 1.0);  // [0, 1)
long l = tr.nextLong(1, 100);  // [1, 100)
boolean b = tr.nextBoolean();

System.out.println(n);
System.out.println(d);
```

> ⚠️ **多线程随机数必用 ThreadLocalRandom**：`Random` 在多线程下所有线程共享同一个 seed，CAS 竞争导致性能下降；`ThreadLocalRandom` 每个线程独立 seed，无锁无竞争。并发场景下性能差距可达数倍。

```java
// ❌ 多线程下用 Random，有竞争
Random shared = new Random();
Runnable task = () -> {
    for (int i = 0; i < 1000; i++) {
        shared.nextInt(100);   // 多线程竞争同一 seed
    }
};

// ✅ 多线程下用 ThreadLocalRandom
Runnable task2 = () -> {
    ThreadLocalRandom tr = ThreadLocalRandom.current();
    for (int i = 0; i < 1000; i++) {
        tr.nextInt(100);   // 每个线程独立，无竞争
    }
};
```

---

## 四、BigDecimal（重点）

### 4.1 为什么用 BigDecimal

`double` 用二进制存储，无法精确表示十进制小数，导致运算结果有误差：

```java
System.out.println(0.1 + 0.2);       // 0.30000000000000004  ❌
System.out.println(2.0 - 1.1);       // 0.8999999999999999   ❌
System.out.println(0.1 * 3);         // 0.30000000000000004  ❌
System.out.println(1.0 / 3);         // 0.3333333333333333   ❌
```

> ⚠️ **这是浮点数最危险的坑**：`double` 用 IEEE 754 科学计数法存储，二进制无法精确表示 0.1（类似十进制无法精确表示 1/3）。**凡是涉及金额、利率、计量的计算，绝对不能用 float/double！** 用 `BigDecimal` 做精确的十进制运算。

```java
import java.math.BigDecimal;

BigDecimal a = new BigDecimal("0.1");
BigDecimal b = new BigDecimal("0.2");
System.out.println(a.add(b));   // 0.3  ✅ 精确
```

### 4.2 构造方法（三个，一个有坑）

```java
// ✅ 方式 1：String 构造（推荐）
BigDecimal a = new BigDecimal("0.1");
System.out.println(a);   // 0.1，精确

// ❌ 方式 2：double 构造（有坑！）
BigDecimal b = new BigDecimal(0.1);
System.out.println(b);   // 0.1000000000000000055511151231257827021181583404541015625

// ✅ 方式 3：valueOf 静态方法（推荐）
BigDecimal c = BigDecimal.valueOf(0.1);
System.out.println(c);   // 0.1，内部先 Double.toString 再构造
```

> ⚠️ **铁律**：`new BigDecimal(double)` 是个大坑——它把 `double` 的二进制不精确值**原封不动**带进 BigDecimal，结果一长串。**永远用 String 构造或 `valueOf`**，绝不用 `new BigDecimal(double)`。

```java
// ❌ 错误
BigDecimal bad = new BigDecimal(0.1);   // 0.1000000000000000055...

// ✅ 正确
BigDecimal good1 = new BigDecimal("0.1");      // 推荐
BigDecimal good2 = BigDecimal.valueOf(0.1);     // 推荐，等价于 new BigDecimal(Double.toString(0.1))
BigDecimal good3 = BigDecimal.valueOf(0.1d);     // 同上
```

> 💡 **`valueOf` 的原理**：`BigDecimal.valueOf(double)` 内部调用 `Double.toString(d)` 把 double 转成字符串，再用 String 构造。所以它绕过了 double 的二进制精度问题。但若 double 本身就是计算结果（如 `0.1 + 0.2`），`valueOf` 也救不了，必须用 String。

### 4.3 四则运算

BigDecimal 是**不可变**对象，运算不修改原对象，而是返回新对象：

```java
import java.math.BigDecimal;

BigDecimal a = new BigDecimal("10.5");
BigDecimal b = new BigDecimal("3");

// 加
BigDecimal sum = a.add(b);
System.out.println(sum);   // 13.5

// 减
BigDecimal diff = a.subtract(b);
System.out.println(diff);  // 7.5

// 乘
BigDecimal product = a.multiply(b);
System.out.println(product); // 31.5

// 除（⚠️ 必须指定精度和舍入模式，否则除不尽抛异常）
BigDecimal quotient = a.divide(b, 2, BigDecimal.ROUND_HALF_UP);
System.out.println(quotient);  // 3.50
```

> ⚠️ **divide 的陷阱**：如果除法结果是无限循环小数（如 `10 / 3`），且未指定精度，会抛 `ArithmeticException: Non-terminating decimal expansion`：

```java
BigDecimal x = new BigDecimal("10");
BigDecimal y = new BigDecimal("3");

// ❌ 除不尽，抛异常
// BigDecimal r = x.divide(y);

// ✅ 指定精度和舍入模式
BigDecimal r = x.divide(y, 2, BigDecimal.ROUND_HALF_UP);
System.out.println(r);   // 3.33

// ✅ Java 8+ 用 RoundingMode 枚举（推荐）
import java.math.RoundingMode;
BigDecimal r2 = x.divide(y, 2, RoundingMode.HALF_UP);
System.out.println(r2);  // 3.33
```

> 📌 **开发规范**：`divide` 一律指定精度和舍入模式，**永远不要写裸的 `a.divide(b)`**。这是 BigDecimal 最容易踩的坑，一行除不尽就线上崩溃。

### 4.4 setScale 设置小数位

`setScale` 设置小数位数 + 舍入模式：

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

BigDecimal price = new BigDecimal("19.999");

// 保留 2 位，四舍五入
BigDecimal rounded = price.setScale(2, RoundingMode.HALF_UP);
System.out.println(rounded);   // 20.00

// 保留 2 位，向下取整（截断）
BigDecimal truncated = price.setScale(2, RoundingMode.DOWN);
System.out.println(truncated);  // 19.99

// 保留 0 位
BigDecimal integer = price.setScale(0, RoundingMode.HALF_UP);
System.out.println(integer);    // 20
```

> 💡 `setScale` 和运算常配合使用：先运算，再 `setScale` 规整成统一的小数位。电商金额统一保留 2 位是标准做法。

### 4.5 比较用 compareTo 不用 equals ⭐⭐⭐

这是 BigDecimal **最经典的坑**：

```java
import java.math.BigDecimal;

BigDecimal a = new BigDecimal("1.0");
BigDecimal b = new BigDecimal("1.00");

// ❌ equals 比较：值相等但精度不同，返回 false！
System.out.println(a.equals(b));   // false

// ✅ compareTo 比较：只比较数值大小，返回 0 表示相等
System.out.println(a.compareTo(b));   // 0
System.out.println(a.compareTo(b) == 0);  // true
```

> ⚠️ **原理**：`equals` 不仅比较值，还比较**精度（scale）**。`1.0` 的 scale 是 1，`1.00` 的 scale 是 2，所以 `equals` 返回 false。而 `compareTo` 只比较数值大小，忽略精度差异。**金额比较一律用 `compareTo`**。

```java
// ❌ 错误：金额相等判断
if (amount1.equals(amount2)) { ... }   // 1.0 和 1.00 判为不等

// ✅ 正确
if (amount1.compareTo(amount2) == 0) { ... }   // 数值相等就为真

// 比较大小
if (amount1.compareTo(amount2) > 0) { ... }   // amount1 > amount2
if (amount1.compareTo(amount2) < 0) { ... }   // amount1 < amount2
```

### 4.6 BigDecimal 不可变

运算返回新对象，原对象不变：

```java
BigDecimal a = new BigDecimal("100");
BigDecimal b = new BigDecimal("50");

// ❌ 错误：忘记接收返回值，运算"无效"
a.add(b);
System.out.println(a);   // 100，没变！

// ✅ 正确：接收返回的新对象
a = a.add(b);
System.out.println(a);   // 150

// 或用新变量
BigDecimal sum = a.add(b);
```

> ⚠️ **新手最常踩的坑**：`a.add(b)` 不修改 a，而是返回新对象。忘记接收返回值，运算等于白做。这和 `String` 的不可变性完全一致。

### 4.7 BigDecimal 常用方法

```java
BigDecimal a = new BigDecimal("123.456");

System.out.println(a.intValue());      // 123，转 int（截断）
System.out.println(a.doubleValue());   // 123.456，转 double
System.out.println(a.longValue());     // 123，转 long
System.out.println(a.toString());      // "123.456"

System.out.println(a.max(new BigDecimal("100")));  // 123.456
System.out.println(a.min(new BigDecimal("100")));  // 100
System.out.println(a.negate());        // -123.456，取反
System.out.println(a.abs());           // 123.456，绝对值
System.out.println(a.scale());         // 3，小数位数
System.out.println(a.precision());    // 6，有效数字位数

// 幂运算
System.out.println(a.pow(2));          // 15241.538935936，平方
```

---

## 五、BigInteger

`BigInteger` 用于表示超出 `long` 范围的超大整数（任意精度）。用法和 BigDecimal 类似：

```java
import java.math.BigInteger;

// long 最大约 9.2 * 10^18，超出就用 BigInteger
BigInteger big = new BigInteger("999999999999999999999999999999");
System.out.println(big);   // 999999999999999999999999999999

// 四则运算（同样不可变，返回新对象）
BigInteger a = new BigInteger("12345678901234567890");
BigInteger b = new BigInteger("98765432109876543210");

System.out.println(a.add(b));       // 111111111011111111100
System.out.println(b.subtract(a));  // 86419753208641975320
System.out.println(a.multiply(b));  // 超大数
System.out.println(b.divide(a));    // 8（整除）

// 比较用 compareTo
System.out.println(a.compareTo(b));  // -1，a < b

// 常用方法
System.out.println(a.abs());
System.out.println(a.pow(2));        // 平方
System.out.println(a.gcd(b));        // 最大公约数
System.out.println(a.mod(new BigInteger("7")));  // 取模
```

> 💡 **使用场景**：密码学（RSA 大数运算）、阶乘/组合数（超 long 范围）、精确的整数运算。日常业务用得少，但面试可能考阶乘。

---

## 六、舍入模式（RoundingMode）

`BigDecimal` 除法和 `setScale` 都要指定舍入模式，Java 8 推荐用 `RoundingMode` 枚举（替代旧的 `BigDecimal.ROUND_XXX` 常量）。

### 6.1 常用舍入模式

| 模式 | 说明 | 2.5 → | 1.5 → | -2.5 → |
| :--- | :--- | :---: | :---: | :---: |
| `HALF_UP` | 四舍五入 | 3 | 2 | -3 |
| `HALF_DOWN` | 五舍六入 | 2 | 1 | -2 |
| `HALF_EVEN` | 银行家舍入（五成双） | 2 | 2 | -2 |
| `UP` | 远离零舍入 | 3 | 2 | -3 |
| `DOWN` | 向零截断 | 2 | 1 | -2 |
| `CEILING` | 向正无穷舍入 | 3 | 2 | -2 |
| `FLOOR` | 向负无穷舍入 | 2 | 1 | -3 |

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

BigDecimal a = new BigDecimal("2.5");
BigDecimal b = new BigDecimal("1.5");
BigDecimal c = new BigDecimal("-2.5");

// 四舍五入（最常用）
System.out.println(a.setScale(0, RoundingMode.HALF_UP));   // 3
System.out.println(b.setScale(0, RoundingMode.HALF_UP));   // 2

// 截断（直接舍去小数）
System.out.println(a.setScale(0, RoundingMode.DOWN));       // 2
System.out.println(c.setScale(0, RoundingMode.DOWN));      // -2

// 向上取整
System.out.println(a.setScale(0, RoundingMode.UP));         // 3
System.out.println(c.setScale(0, RoundingMode.UP));        // -3

// 银行家舍入（金融常用）
System.out.println(a.setScale(0, RoundingMode.HALF_EVEN)); // 2（2 是偶数）
System.out.println(b.setScale(0, RoundingMode.HALF_EVEN)); // 2
```

> 💡 **HALF_UP vs HALF_EVEN**：
> - `HALF_UP` 是日常"四舍五入"，5 一律进位
> - `HALF_EVEN` 是"银行家舍入"，5 时向最近的**偶数**进位（2.5→2，3.5→4），统计上更公平，金融系统常用
>
> 国内电商一般用 `HALF_UP`，银行/财务系统可能用 `HALF_EVEN`，按业务要求选。

---

## ⚠️ 重点

### 重点 1：金额计算必须用 BigDecimal ⭐⭐⭐

```java
// ❌ 错误：用 double 算钱
double price = 0.1;
double total = price * 3;
System.out.println(total);   // 0.30000000000000004，账目对不上

// ✅ 正确：用 BigDecimal + String 构造
BigDecimal bd1 = new BigDecimal("0.1");
BigDecimal bd2 = new BigDecimal("0.2");
System.out.println(bd1.add(bd2));   // 0.3，精确
```

> ⚠️ **这是开发中最致命的坑**：浮点精度问题在测试环境可能不暴露（数据凑巧），上生产后金额对不上、对账失败、用户投诉。**金额一律 BigDecimal，构造用 String**。

### 重点 2：new BigDecimal(double) 是大坑 ⭐⭐⭐

```java
// ❌ double 构造，带入二进制误差
BigDecimal bad = new BigDecimal(0.1);
System.out.println(bad);   // 0.1000000000000000055511151231257827021181583404541015625

// ✅ String 构造
BigDecimal good1 = new BigDecimal("0.1");    // 0.1
// ✅ valueOf（内部转 String）
BigDecimal good2 = BigDecimal.valueOf(0.1);   // 0.1
```

> 📌 **铁律**：BigDecimal 构造只用两种——`new BigDecimal(String)` 或 `BigDecimal.valueOf(double)`。**永远不要 `new BigDecimal(double)`**。

### 重点 3：divide 必须指定精度和舍入模式 ⭐⭐⭐

```java
BigDecimal a = new BigDecimal("10");
BigDecimal b = new BigDecimal("3");

// ❌ 除不尽，抛 ArithmeticException
// a.divide(b);

// ✅ 指定精度 + 舍入模式
BigDecimal r = a.divide(b, 2, RoundingMode.HALF_UP);
System.out.println(r);   // 3.33
```

> ⚠️ **生产事故高发点**：裸 `divide` 在除得尽时没事（如 10/2=5），一旦除不尽（10/3）直接抛异常崩溃。**所有 divide 调用必须带精度和舍入模式**，无一例外。

### 重点 4：比较用 compareTo 不用 equals ⭐⭐⭐

```java
BigDecimal a = new BigDecimal("1.0");
BigDecimal b = new BigDecimal("1.00");

System.out.println(a.equals(b));      // false！精度不同
System.out.println(a.compareTo(b) == 0); // true，只比数值
```

> ⚠️ **金额相等判断的陷阱**：数据库存 `1.00`，代码里 `new BigDecimal("1.0")`，用 `equals` 比较返回 false，导致"金额相等却判不等"的诡异 bug。**金额比较一律 `compareTo`**。

### 重点 5：BigDecimal 不可变，运算返回新对象 ⭐⭐

```java
BigDecimal a = new BigDecimal("100");
BigDecimal b = new BigDecimal("50");

// ❌ 忘记接收，运算无效
a.add(b);
System.out.println(a);   // 100，没变

// ✅ 接收返回值
a = a.add(b);
System.out.println(a);   // 150
```

### 重点 6：Math.abs 的整数溢出 ⭐

```java
System.out.println(Math.abs(Integer.MIN_VALUE));   // -2147483648，还是负数！
System.out.println(Math.abs(Long.MIN_VALUE));      // -9223372036854775808
```

> ⚠️ `int` 最小值的绝对值超出 `int` 正数范围，溢出后变回负数。校验金额正负时若用 `Math.abs` 判断，可能漏掉这个边界。

---

## 💻 实战案例

### 案例 1：电商金额计算全流程 ⭐⭐⭐

电商下单最核心的金额计算：单价 × 数量 - 优惠 + 运费，全程 BigDecimal：

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public class OrderCalculator {

    /** 商品单价 */
    private BigDecimal price;
    /** 购买数量 */
    private int quantity;
    /** 优惠金额 */
    private BigDecimal discount;
    /** 运费 */
    private BigDecimal shippingFee;

    public OrderCalculator(String price, int quantity, String discount, String shippingFee) {
        this.price = new BigDecimal(price);
        this.quantity = quantity;
        this.discount = new BigDecimal(discount);
        this.shippingFee = new BigDecimal(shippingFee);
    }

    /** 计算商品小计 */
    public BigDecimal subtotal() {
        return price.multiply(new BigDecimal(quantity))
                    .setScale(2, RoundingMode.HALF_UP);
    }

    /** 计算实付金额 = 小计 - 优惠 + 运费 */
    public BigDecimal payable() {
        BigDecimal sub = subtotal();
        BigDecimal pay = sub.subtract(discount).add(shippingFee);
        // 实付不能为负
        if (pay.compareTo(BigDecimal.ZERO) < 0) {
            return BigDecimal.ZERO;
        }
        return pay.setScale(2, RoundingMode.HALF_UP);
    }

    public static void main(String[] args) {
        // 单价 19.9，买 3 件，优惠 10 元，运费 5 元
        OrderCalculator calc = new OrderCalculator("19.9", 3, "10", "5");

        System.out.println("商品小计：" + calc.subtotal());   // 59.70
        System.out.println("优惠金额：" + calc.discount);       // 10
        System.out.println("运费：" + calc.shippingFee);       // 5
        System.out.println("实付金额：" + calc.payable());      // 54.70
    }
}
```

> 📌 **开发规范**：
> - 金额字段一律 `BigDecimal`，构造用 `String`
> - 每步运算后 `setScale(2, HALF_UP)` 保留 2 位
> - 实付金额要做非负校验（`compareTo` 判断）
> - 输出统一 `setScale(2)` 格式化

### 案例 2：利率计算——分期还款 ⭐⭐

金融场景：等额本息月供计算，公式 `M = P * r * (1+r)^n / ((1+r)^n - 1)`：

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public class LoanCalculator {

    /**
     * 等额本息月供计算
     * @param principal 本金（元）
     * @param annualRate 年利率（如 0.06 表示 6%）
     * @param months 期数（月）
     * @return 月供
     */
    public static BigDecimal monthlyPayment(String principal, String annualRate, int months) {
        BigDecimal P = new BigDecimal(principal);
        // 月利率 = 年利率 / 12
        BigDecimal r = new BigDecimal(annualRate)
                          .divide(new BigDecimal("12"), 10, RoundingMode.HALF_UP);
        BigDecimal n = new BigDecimal(months);

        // (1+r)^n
        BigDecimal one = BigDecimal.ONE;
        BigDecimal base = one.add(r);          // 1 + r
        BigDecimal pow = base.pow(months);     // (1+r)^n

        // 分子：P * r * (1+r)^n
        BigDecimal numerator = P.multiply(r).multiply(pow);
        // 分母：(1+r)^n - 1
        BigDecimal denominator = pow.subtract(one);

        // 月供 = 分子 / 分母
        BigDecimal monthly = numerator.divide(denominator, 2, RoundingMode.HALF_UP);
        return monthly;
    }

    public static void main(String[] args) {
        // 借 100000 元，年利率 6%，分 12 期
        BigDecimal pay = monthlyPayment("100000", "0.06", 12);
        System.out.println("月供：" + pay + " 元");   // 8606.64 元

        // 总还款 = 月供 * 期数
        BigDecimal total = pay.multiply(new BigDecimal(12));
        System.out.println("总还款：" + total + " 元");  // 103279.68

        // 总利息 = 总还款 - 本金
        BigDecimal interest = total.subtract(new BigDecimal("100000"));
        System.out.println("总利息：" + interest + " 元");  // 3279.68
    }
}
```

> ⚠️ **利率计算的精度要求**：月利率 `r` 要保留足够小数位（这里用 10 位），否则幂运算后误差放大。最终月供保留 2 位。金融计算中，中间过程多保留几位，最后再规整。

### 案例 3：随机验证码生成 ⭐

```java
import java.util.Random;

public class VerifyCode {

    /** 生成 6 位数字验证码 */
    public static String numericCode(int length) {
        Random random = new Random();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++) {
            sb.append(random.nextInt(10));   // 0~9
        }
        return sb.toString();
    }

    /** 生成字母+数字混合验证码 */
    public static String mixedCode(int length) {
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
        // 排除易混淆字符（O/0/I/1/l）
        Random random = new Random();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return sb.toString();
    }

    public static void main(String[] args) {
        System.out.println("数字验证码：" + numericCode(6));   // 如 382947
        System.out.println("混合验证码：" + mixedCode(4));      // 如 aB3x
    }
}
```

> 💡 **验证码设计要点**：排除易混淆字符（O/0/I/1/l），用户体验更好。多线程高并发场景用 `ThreadLocalRandom` 替代 `Random`。

### 案例 4：抽奖概率 ⭐⭐

```java
import java.util.Random;

public class Lottery {

    /**
     * 按概率抽奖
     * @param prizes 奖品数组，每个元素 [奖品名, 概率（0~1）]
     * @return 中奖奖品名
     */
    public static String draw(String[][] prizes) {
        Random random = new Random();
        double r = random.nextDouble();   // [0, 1)
        double cumulative = 0;
        for (String[] prize : prizes) {
            cumulative += Double.parseDouble(prize[1]);
            if (r < cumulative) {
                return prize[0];
            }
        }
        return prizes[prizes.length - 1][0];   // 兜底返回最后一个
    }

    public static void main(String[] args) {
        // 一等奖 1%，二等奖 5%，三等奖 10%，未中奖 84%
        String[][] prizes = {
            {"一等奖", "0.01"},
            {"二等奖", "0.05"},
            {"三等奖", "0.10"},
            {"未中奖", "0.84"}
        };

        // 模拟抽奖 10 次
        for (int i = 0; i < 10; i++) {
            System.out.println("第 " + (i + 1) + " 次：" + draw(prizes));
        }

        // 统计概率（抽 100 万次）
        int win1 = 0, win2 = 0, win3 = 0, miss = 0;
        for (int i = 0; i < 1000000; i++) {
            String r = draw(prizes);
            switch (r) {
                case "一等奖": win1++; break;
                case "二等奖": win2++; break;
                case "三等奖": win3++; break;
                default: miss++;
            }
        }
        System.out.println("一等奖：" + win1 / 10000.0 + "%");   // ~1%
        System.out.println("二等奖：" + win2 / 10000.0 + "%");   // ~5%
        System.out.println("三等奖：" + win3 / 10000.0 + "%");   // ~10%
    }
}
```

> 💡 **概率抽奖原理**：累计概率法。生成 [0,1) 随机数，依次累加每个奖品的概率，随机数落在哪个区间就中哪个奖。注意概率总和应为 1。

### 案例 5：BigDecimal 比较金额是否相等 ⭐⭐⭐

```java
import java.math.BigDecimal;

public class AmountCompare {

    /** 判断两个金额是否相等（用 compareTo） */
    public static boolean amountEquals(BigDecimal a, BigDecimal b) {
        if (a == null && b == null) return true;
        if (a == null || b == null) return false;
        return a.compareTo(b) == 0;
    }

    /** 判断金额是否大于零 */
    public static boolean isPositive(BigDecimal amount) {
        return amount != null && amount.compareTo(BigDecimal.ZERO) > 0;
    }

    public static void main(String[] args) {
        // 数据库存 1.00，前端传 1.0
        BigDecimal dbAmount = new BigDecimal("1.00");
        BigDecimal reqAmount = new BigDecimal("1.0");

        // ❌ equals 判断，返回 false
        System.out.println(dbAmount.equals(reqAmount));   // false
        // ✅ compareTo 判断，返回 true
        System.out.println(amountEquals(dbAmount, reqAmount));  // true

        // 金额正负判断
        System.out.println(isPositive(new BigDecimal("0.01")));   // true
        System.out.println(isPositive(new BigDecimal("0.00")));   // false
        System.out.println(isPositive(new BigDecimal("-1")));     // false
        System.out.println(isPositive(null));                      // false
    }
}
```

> ⚠️ **金额比较的三大原则**：
> 1. 用 `compareTo` 不用 `equals`
> 2. 判空（`null` 安全）
> 3. 与 `BigDecimal.ZERO` 比较判断正负

### 案例 6：金额格式化输出 ⭐

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.DecimalFormat;

public class AmountFormat {

    public static void main(String[] args) {
        BigDecimal amount = new BigDecimal("1234567.891");

        // 方式 1：setScale 保留 2 位
        System.out.println(amount.setScale(2, RoundingMode.HALF_UP));
        // 1234567.89

        // 方式 2：DecimalFormat 千分位格式化
        DecimalFormat df = new DecimalFormat("#,##0.00");
        System.out.println(df.format(amount));   // 1,234,567.89

        // 方式 3：DecimalFormat 不够补 0
        DecimalFormat df2 = new DecimalFormat("0.00");
        System.out.println(df2.format(new BigDecimal("100")));   // 100.00

        // 金额转字符串（带千分位）
        BigDecimal price = new BigDecimal("9999.5");
        System.out.println("¥" + new DecimalFormat("#,##0.00").format(price));
        // ¥9,999.50
    }
}
```

> 💡 `DecimalFormat` 适合展示层格式化（千分位、补零），`setScale` 适合计算层规整精度。两者配合：计算用 `setScale`，展示用 `DecimalFormat`。

### 案例 7：批量金额汇总 ⭐⭐

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

public class BatchAmountSum {

    public static void main(String[] args) {
        // 模拟一批订单金额
        List<BigDecimal> orders = Arrays.asList(
            new BigDecimal("199.00"),
            new BigDecimal("88.50"),
            new BigDecimal("1299.99"),
            new BigDecimal("0.99"),
            new BigDecimal("66.66")
        );

        // 求总和
        BigDecimal total = BigDecimal.ZERO;
        for (BigDecimal order : orders) {
            total = total.add(order);   // 注意接收返回值
        }
        System.out.println("总金额：" + total.setScale(2, RoundingMode.HALF_UP));
        // 1655.14

        // 求平均
        BigDecimal avg = total.divide(
            new BigDecimal(orders.size()), 2, RoundingMode.HALF_UP);
        System.out.println("平均金额：" + avg);   // 331.03

        // 求最大最小
        BigDecimal max = orders.get(0);
        BigDecimal min = orders.get(0);
        for (BigDecimal order : orders) {
            if (order.compareTo(max) > 0) max = order;
            if (order.compareTo(min) < 0) min = order;
        }
        System.out.println("最大：" + max);   // 1299.99
        System.out.println("最小：" + min);   // 0.99
    }
}
```

> ⚠️ **批量汇总的注意点**：
> - 累加用 `BigDecimal.ZERO` 作初始值，每次 `total = total.add(x)` 接收返回值
> - 求平均用 `divide` 必须指定精度（除得尽也可能有精度问题）
> - 比较大小用 `compareTo`

### 案例 8：分摊优惠——金额拆分 ⭐⭐

电商常见：一笔订单优惠 10 元，分摊到 3 件商品上，最后一笔兜底：

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

public class DiscountSplitter {

    /**
     * 把优惠金额分摊到各商品
     * @param amounts 各商品金额
     * @param discount 总优惠
     * @return 各商品分摊后的金额
     */
    public static List<BigDecimal> split(List<BigDecimal> amounts, BigDecimal discount) {
        BigDecimal total = BigDecimal.ZERO;
        for (BigDecimal a : amounts) {
            total = total.add(a);
        }

        List<BigDecimal> result = new ArrayList<>();
        BigDecimal allocated = BigDecimal.ZERO;   // 已分摊金额

        for (int i = 0; i < amounts.size(); i++) {
            if (i == amounts.size() - 1) {
                // 最后一笔兜底：优惠 - 已分摊
                BigDecimal last = discount.subtract(allocated);
                result.add(amounts.get(i).subtract(last));
            } else {
                // 按比例分摊：商品金额 / 总金额 * 优惠
                BigDecimal share = amounts.get(i)
                    .multiply(discount)
                    .divide(total, 2, RoundingMode.HALF_UP);
                result.add(amounts.get(i).subtract(share));
                allocated = allocated.add(share);
            }
        }
        return result;
    }

    public static void main(String[] args) {
        List<BigDecimal> items = Arrays.asList(
            new BigDecimal("100.00"),
            new BigDecimal("200.00"),
            new BigDecimal("50.00")
        );
        BigDecimal discount = new BigDecimal("10.00");

        List<BigDecimal> result = split(items, discount);
        for (int i = 0; i < result.size(); i++) {
            System.out.println("商品" + (i + 1) + "实付：" + result.get(i));
        }
        // 商品1实付：97.14（分摊 2.86）
        // 商品2实付：194.29（分摊 5.71）
        // 商品3实付：38.57（兜底分摊 1.43，补精度差）

        // 验证总和
        BigDecimal sum = BigDecimal.ZERO;
        for (BigDecimal r : result) sum = sum.add(r);
        System.out.println("实付总和：" + sum);   // 330.00（= 350 - 10）
    }
}
```

> 💡 **分摊优惠的关键**：按比例算前 N-1 笔，最后一笔用"总额 - 已分摊"兜底，避免精度累积误差导致总和对不上。这是电商对账的核心技巧。

### 案例 9：百分比计算 ⭐

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public class PercentageCalc {

    /** 计算占比（保留 2 位小数 + %） */
    public static String percent(String part, String total) {
        BigDecimal p = new BigDecimal(part);
        BigDecimal t = new BigDecimal(total);
        if (t.compareTo(BigDecimal.ZERO) == 0) {
            return "0.00%";   // 防除零
        }
        // part / total * 100
        BigDecimal rate = p.multiply(new BigDecimal("100"))
                           .divide(t, 2, RoundingMode.HALF_UP);
        return rate + "%";
    }

    public static void main(String[] args) {
        System.out.println(percent("25", "200"));   // 12.50%
        System.out.println(percent("1", "3"));      // 33.33%
        System.out.println(percent("0", "100"));    // 0.00%
        System.out.println(percent("5", "0"));      // 0.00%（防除零）

        // 计算折扣价：原价 199 打 8 折
        BigDecimal price = new BigDecimal("199.00");
        BigDecimal discount = new BigDecimal("0.8");
        BigDecimal finalPrice = price.multiply(discount)
                                     .setScale(2, RoundingMode.HALF_UP);
        System.out.println("折扣价：" + finalPrice);   // 159.20
    }
}
```

### 案例 10：阶乘（BigInteger）⭐

```java
import java.math.BigInteger;

public class Factorial {

    /** 计算 n 的阶乘 */
    public static BigInteger factorial(int n) {
        if (n < 0) {
            throw new IllegalArgumentException("n 不能为负数");
        }
        BigInteger result = BigInteger.ONE;
        for (int i = 2; i <= n; i++) {
            result = result.multiply(BigInteger.valueOf(i));
        }
        return result;
    }

    public static void main(String[] args) {
        System.out.println(factorial(10));   // 3628800
        System.out.println(factorial(20));   // 2432902008176640000
        System.out.println(factorial(50));   // 30414093201713378043612608166064768844377641568960512000000000000
        // 50 的阶乘远超 long 范围，只能用 BigInteger
    }
}
```

> 💡 `20!` 已经接近 `long` 上限（`20! = 2432902008176640000`，`Long.MAX_VALUE = 9223372036854775807`），`21!` 就溢出了。超大阶乘必须用 `BigInteger`。

### 案例 11：骰子游戏模拟 ⭐

```java
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

public class DiceGame {

    public static void main(String[] args) {
        // 单线程：用 Random
        Random random = new Random();
        int dice = random.nextInt(6) + 1;   // 1~6
        System.out.println("骰子点数：" + dice);

        // 模拟掷 2 个骰子 1000 次，统计点数和分布
        int[] distribution = new int[13];   // 索引 2~12
        for (int i = 0; i < 1000; i++) {
            int d1 = random.nextInt(6) + 1;
            int d2 = random.nextInt(6) + 1;
            distribution[d1 + d2]++;
        }
        System.out.println("点数和 7 出现次数：" + distribution[7]);  // ~167 次（概率 1/6）

        // 多线程模拟：用 ThreadLocalRandom
        Runnable task = () -> {
            ThreadLocalRandom tr = ThreadLocalRandom.current();
            int d = tr.nextInt(1, 7);   // [1, 7) = 1~6
            System.out.println(Thread.currentThread().getName() + " 掷出 " + d);
        };
        for (int i = 0; i < 5; i++) {
            new Thread(task).start();
        }
    }
}
```

---

## 🚀 新版本补充

### Java 9：BigDecimal 新增方法

Java 9 给 `BigDecimal` 增加了 `stream()` 相关的整合方法，但核心 API 无大变化。主要改进在性能和内部实现。

### Java 8：RoundingMode 枚举（替代旧常量）

Java 8 起，推荐用 `RoundingMode` 枚举替代旧的 `BigDecimal.ROUND_XXX` 整型常量：

```java
import java.math.RoundingMode;

// ❌ 旧写法（Java 8 前的常量，已废弃）
BigDecimal r = a.divide(b, 2, BigDecimal.ROUND_HALF_UP);

// ✅ 新写法（Java 8+ 推荐）
BigDecimal r = a.divide(b, 2, RoundingMode.HALF_UP);
```

> 💡 旧的 `BigDecimal.ROUND_HALF_UP` 等常量从 Java 9 起标记 `@Deprecated`。新代码一律用 `RoundingMode` 枚举，类型安全、可读性好。

### Java 8：Math 新增方法

```java
// 精确加法（处理溢出）
long sum = Math.addExact(1_000_000_000L, 2_000_000_000L);  // 3000000000

// 精确乘法（溢出抛 ArithmeticException）
try {
    int r = Math.multiplyExact(100000, 100000);  // 10^10，超出 int 范围
} catch (ArithmeticException e) {
    System.out.println("溢出");   // 走这里
}

// floorDiv：向下取整除法
System.out.println(Math.floorDiv(-7, 2));   // -4（普通 -7/2 = -3）

// nextDown：浮点数精度
System.out.println(Math.nextDown(1.0));   // 0.9999999999999999
```

> 💡 `addExact`/`multiplyExact` 在溢出时抛异常，比普通运算"静默溢出"更安全，适合金融校验。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Math 类 | abs/ceil/floor/round/max/min/pow/sqrt/random/PI |
| Math.random | 返回 [0,1) 的 double |
| 取整区别 | ceil 向上、floor 向下、round 四舍五入（返回 long） |
| Math.abs 坑 | Integer.MIN_VALUE 的绝对值溢出，仍为负 |
| Random | 可指定种子，生成 int/long/double/boolean |
| ThreadLocalRandom | 多线程高效随机，无竞争（Java 7+） |
| BigDecimal | 精确十进制运算，金额计算必用 |
| 构造方法 | 用 String 或 valueOf，**不用 new(double)** |
| 四则运算 | add/subtract/multiply/divide，不可变返回新对象 |
| divide | **必须指定精度和舍入模式**，否则除不尽抛异常 |
| setScale | 设置小数位 + RoundingMode |
| 比较 | **用 compareTo 不用 equals**（equals 比精度） |
| BigInteger | 超大整数，任意精度 |
| 舍入模式 | HALF_UP（四舍五入）、DOWN（截断）、UP、HALF_EVEN（银行家） |

---

## 学习建议

1. **把 BigDecimal 的三个坑刻进脑子**：`new BigDecimal(double)` 带精度坑、`divide` 不指定精度抛异常、`equals` 比精度导致金额判不等——这三个是开发中最高频的踩坑点，面试也常考。手敲一遍看到结果，比看十遍文字都管用。
2. **金额计算形成模板**：构造用 String、运算接收返回值、除法带精度和舍入、比较用 compareTo、输出 setScale(2)——这套流程是电商/金融代码的标准范式，写熟了以后所有金额代码都按这个套。
3. **理解浮点数为什么算不准**：不要死记"double 不能算钱"，要理解 IEEE 754 二进制无法精确表示 0.1 的原理。理解了原理，你才能判断哪些场景 double 够用（如科学计算）、哪些必须 BigDecimal（如金额）。
4. **区分展示层和计算层**：计算用 `BigDecimal` + `setScale`，展示用 `DecimalFormat` 格式化千分位。不要在计算层用 `DecimalFormat`，也不要在展示层纠结精度，各司其职。
5. **多线程随机数用 ThreadLocalRandom**：并发场景下 `Random` 有竞争，`ThreadLocalRandom` 无锁高效。养成习惯：只要在多线程里生成随机数，就用 `ThreadLocalRandom.current()`，性能差距在大并发下很明显。
