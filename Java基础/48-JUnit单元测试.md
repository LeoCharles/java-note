# JUnit 单元测试

单元测试是对程序中**最小功能单元**（通常是一个方法）进行验证的测试。写完代码立刻测、改完 bug 回归测，靠的不是 `System.out.println` 肉眼对，而是用框架自动断言。JUnit 是 Java 生态最主流的单元测试框架，本篇以 **JUnit 4** 为基准（Maven/Gradle 项目默认标配），掌握它你就拥有了「代码可信度」的护城河。

> 💡 本篇假设你已了解 [09-类与对象](09-类与对象：封装与构造方法.md) 和 [23-异常处理](23-异常处理.md)。测试的本质就是「造对象 → 调方法 → 断言结果」，离不开这两块基础。

---

## 一、为什么需要单元测试

先看一个最常见的「肉眼测试」反例：

```java
// ❌ 烂大街的测试方式：main 方法 + 肉眼对比
public class Calculator {
    public int add(int a, int b) { return a + b; }

    public static void main(String[] args) {
        Calculator c = new Calculator();
        System.out.println(c.add(1, 2));   // 3，肉眼对一下
        System.out.println(c.add(-1, 1));  // 0，肉眼对一下
    }
}
```

这种方式的问题：**不可重复、不可回归、无法自动判断对错、改一行代码要重跑一遍人肉对**。一旦方法多了，`main` 方法会膨胀成一锅粥，谁也不敢动。

JUnit 解决的就是这三件事：

| 痛点 | JUnit 怎么解 |
| :--- | :--- |
| 肉眼判断对错 | `Assert.assertEquals(期望, 实际)` 自动断言 |
| 改代码要重测 | `@Test` 方法一键全跑，红绿条一目了然 |
| 测试数据要换多组 | 参数化测试 `@RunWith(Parameterized.class)` |

> 📌 **开发规范**：生产代码和测试代码分离。测试类放 `src/test/java`，和生产类同名加 `Test` 后缀（`Calculator` → `CalculatorTest`），包名保持一致。

---

## 二、JUnit 4 快速上手

### 2.1 引入依赖

Maven 项目在 `pom.xml` 加（JUnit 4 最后一个稳定版 4.13.2）：

```xml
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>   <!-- 只在测试时用，不打进生产包 -->
</dependency>
```

> 💡 非 Maven 项目（纯手写）可直接把 `junit-4.13.2.jar` + `hamcrest-core-1.3.jar` 加进 classpath。但强烈建议用 Maven/Gradle 管理依赖。

### 2.2 被测类

```java
// src/main/java/com/example/Calculator.java
package com.example;

public class Calculator {

    public int add(int a, int b) { return a + b; }

    public int divide(int a, int b) {
        if (b == 0) throw new ArithmeticException("除数不能为 0");
        return a / b;
    }
}
```

### 2.3 第一个测试类

```java
// src/test/java/com/example/CalculatorTest.java
package com.example;

import org.junit.Test;                // ✅ JUnit 4 的注解
import org.junit.Assert;              // ✅ 断言类
import static org.junit.Assert.*;     // ✅ 静态导入，写 assertEquals 更爽

public class CalculatorTest {

    @Test   // ✅ 标记这是测试方法，JUnit 会自动跑
    public void testAdd() {
        Calculator calc = new Calculator();
        int result = calc.add(2, 3);
        Assert.assertEquals(5, result);   // 期望 5，实际 result
    }

    @Test
    public void testDivide() {
        Calculator calc = new Calculator();
        assertEquals(2, calc.divide(10, 5));   // 静态导入后省略类名
    }
}
```

运行结果（IDEA 中点方法左侧绿三角）：

```
✅ testAdd   绿色
✅ testDivide 绿色
```

> ⚠️ **JUnit 4 测试方法的硬性约定**：`public void`、**无参数**、无返回值、方法名以 `test` 开头（非强制但强烈建议）。少了 `public` 或带了参数，`@Test` 不会跑。

---

## 三、常用注解

JUnit 4 的注解控制测试方法的生命周期。理解「每个测试方法独立执行」是关键。

### 3.1 五大核心注解

| 注解 | 执行时机 | 用途 | 要求 |
| :--- | :--- | :--- | :--- |
| `@BeforeClass` | 所有测试方法前**执行一次** | 加载昂贵资源（连数据库、读配置） | 必须 `static` |
| `@Before` | **每个**测试方法前执行 | 初始化对象、重置状态 | 非 static |
| `@Test` | 标记测试方法 | 实际的测试逻辑 | `public void` 无参 |
| `@After` | **每个**测试方法后执行 | 关闭流、清理临时文件 | 非 static |
| `@AfterClass` | 所有测试方法后**执行一次** | 释放全局资源（关连接） | 必须 `static` |

### 3.2 注解执行顺序演示

```java
import org.junit.*;

public class LifecycleTest {

    @BeforeClass
    public static void initAll() {      // ✅ static！整个类只跑一次
        System.out.println("1. @BeforeClass：类级别初始化（如建连接）");
    }

    @Before
    public void init() {               // ✅ 每个测试方法前都跑
        System.out.println("2. @Before：方法前初始化");
    }

    @Test
    public void testA() {
        System.out.println("3. testA 执行");
    }

    @Test
    public void testB() {
        System.out.println("3. testB 执行");
    }

    @After
    public void tearDown() {           // ✅ 每个测试方法后都跑
        System.out.println("4. @After：方法后清理");
    }

    @AfterClass
    public static void tearDownAll() {  // ✅ static！整个类只跑一次
        System.out.println("5. @AfterClass：类级别清理");
    }
}
```

执行顺序（JUnit 不保证 `testA`/`testB` 谁先，但保证包裹顺序）：

```
1. @BeforeClass
2. @Before → 3. testA → 4. @After
2. @Before → 3. testB → 4. @After
5. @AfterClass
```

> 💡 **为什么 `@Before`/`@After` 每个方法都跑？** 保证测试**隔离性**：每个测试方法拿到的是干净状态，A 改脏的数据不影响 B。这是单元测试「可重复、无副作用」的核心。

### 3.3 @Ignore：临时跳过

```java
@Ignore("TODO：等接口稳定后再测")   // ✅ 标记忽略，运行时显示跳过
@Test
public void testUnfinished() {
    // 这个方法不会执行，也不会算失败
}
```

> 📌 `@Ignore` 一定要写原因，别留个空壳。否则过两个月没人记得为什么跳过，就成了死代码。

---

## 四、断言 Assert

断言是测试的灵魂：**期望值 vs 实际值**，对就绿、错就红。JUnit 4 的断言全在 `org.junit.Assert`。

### 4.1 核心断言一览

```java
import static org.junit.Assert.*;

@Test
public void testAssertions() {
    // 1. 相等：assertEquals(期望, 实际)
    assertEquals(5, 2 + 3);                    // ✅ 通过
    assertEquals("两数相加应为5", 5, 2 + 3);    // ✅ 带消息，失败时更易定位
    // assertEquals(4, 2 + 3);                 // ❌ 失败：期望4，实际5

    // 2. 布尔：assertTrue / assertFalse
    assertTrue("字符串应非空", "abc".length() > 0);   // ✅
    assertFalse("列表应空", new ArrayList<>().isEmpty() == false);  // ❌
    assertTrue(10 > 5);                        // ✅

    // 3. null 判断
    assertNull(null);                          // ✅
    assertNotNull(new Object());               // ✅
    // assertNull("hello");                    // ❌ "hello" 不为 null

    // 4. 数组相等：逐元素比较
    assertArrayEquals(new int[]{1, 2, 3}, new int[]{1, 2, 3});  // ✅
    // assertArrayEquals(new int[]{1, 2}, new int[]{1, 2, 3}); // ❌ 长度不同

    // 5. 同一对象：assertSame（==）/ assertNotSame
    String a = "x";
    assertSame(a, a);                          // ✅ 同一引用
}
```

> ⚠️ **`assertEquals` 对浮点数有陷阱**：`assertEquals(0.3, 0.1 + 0.2)` 会失败（浮点精度问题）。要用带误差的版本：`assertEquals(0.3, 0.1 + 0.2, 0.0001)`（第三个参数是误差范围）。涉及金额请用 `BigDecimal.compareTo`。

### 4.2 assertThat + Hamcrest 匹配器（更灵活）

`assertThat(实际值, 匹配器)` 语义更自然，失败信息更友好：

```java
import static org.junit.Assert.*;
import static org.hamcrest.CoreMatchers.*;   // ✅ Hamcrest 匹配器

@Test
public void testHamcrest() {
    String s = "hello world";

    assertThat(s, containsString("world"));   // ✅ 包含子串
    assertThat(s, startsWith("hello"));        // ✅ 以...开头
    assertThat(10, greaterThan(5));            // ✅ 大于
    assertThat(10, lessThanOrEqualTo(10));     // ✅ 小于等于
    assertThat(s, not("bye"));                  // ✅ 不等于
    assertThat(7, allOf(        // ✅ 同时满足（AND）
            greaterThan(5),
            lessThan(10)));
    assertThat(7, anyOf(        // ✅ 满足其一（OR）
            greaterThan(100),
            lessThan(10)));
}
```

> 💡 **建议**：新代码尽量用 `assertThat`，可读性强（`assertThat(实际, is(期望))` 像读句子）。但 `assertEquals` 在简单场景依然最常用，两者不冲突。

---

## 五、异常测试

被测方法抛异常是常见行为，要测「**该抛的有没有抛、抛的类型对不对**」。

### 5.1 JUnit 4 写法：@Test(expected=...)

```java
import org.junit.Test;

public class CalculatorTest {
    private final Calculator calc = new Calculator();

    @Test(expected = ArithmeticException.class)   // ✅ 期望抛该异常
    public void testDivideByZero() {
        calc.divide(10, 0);   // 应该抛 ArithmeticException
        // 如果没抛，测试失败；抛了且类型对，测试通过
    }

    @Test(expected = NullPointerException.class)
    public void testNullInput() {
        String s = null;
        s.length();   // ✅ 会抛 NPE
    }
}
```

> ⚠️ `expected` 的局限：**只判断异常类型，不判断异常消息和抛出位置**。如果方法里有多处可能抛 `ArithmeticException`，无法区分是哪一处抛的。JUnit 5 的 `assertThrows` 解决了这个问题（见新版本补充）。

### 5.2 try-fail 模式（更精确）

需要校验异常消息时用这个：

```java
@Test
public void testDivideByZeroMessage() {
    try {
        calc.divide(10, 0);
        fail("应该抛 ArithmeticException，但没抛");   // ✅ 没抛才算失败
    } catch (ArithmeticException e) {
        assertTrue(e.getMessage().contains("除数不能为 0"));   // ✅ 校验消息
    }
}
```

> 💡 这个模式三步走：① 调用期望抛异常的方法；② 紧跟 `fail()`（没抛才算挂）；③ `catch` 里校验消息。比 `expected` 精确，但啰嗦，按需选用。

---

## 六、超时测试

防止死循环、慢操作拖垮测试套件。`@Test(timeout=毫秒)`：超时即失败。

```java
import org.junit.Test;

public class TimeoutTest {

    @Test(timeout = 1000)   // ✅ 1000 毫秒内必须跑完
    public void testQuickSort() {
        // 模拟一个排序，正常应很快返回
        int[] arr = {5, 2, 8, 1, 9};
        // ... 排序逻辑
    }

    @Test(timeout = 100)
    public void testDeadLoop() {
        // ❌ 死循环，100ms 内不返回 → 测试失败
        while (true) { }
    }

    @Test(timeout = 2000)
    public void testNetworkCall() {
        // ⚠️ 单元测试原则上不该真连网络，这里仅演示超时
        // 真实场景应 Mock 掉网络调用
    }
}
```

> ⚠️ 超时测试在单独线程跑，超时后该线程会被 `interrupt()`。但 `interrupt` 不一定能停掉死循环（如果循环里不响应中断），慎用，别拿它当性能基准。

---

## 七、参数化测试

一组数据跑同一个测试逻辑，避免为每组数据写一个 `@Test`。JUnit 4 用 `@RunWith(Parameterized.class)`。

```java
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import java.util.Arrays;
import java.util.Collection;
import static org.junit.Assert.assertEquals;

@RunWith(Parameterized.class)   // ✅ 1. 指定参数化运行器
public class CalculatorParamTest {

    // ✅ 2. 字段对应每组数据的元素
    private int a;
    private int b;
    private int expected;

    // ✅ 3. 构造器注入（参数顺序对应数据顺序）
    public CalculatorParamTest(int a, int b, int expected) {
        this.a = a;
        this.b = b;
        this.expected = expected;
    }

    // ✅ 4. 提供测试数据集，必须 public static，返回 Collection
    @Parameters(name = "{index}: add({0},{1})={2}")   // name 让失败信息更清晰
    public static Collection<Object[]> data() {
        return Arrays.asList(new Object[][]{
                {1, 2, 3},        // a=1, b=2, 期望=3
                {-1, 1, 0},
                {0, 0, 0},
                {100, 200, 300},
                {-5, -5, -10}
        });
    }

    // ✅ 5. 一个 @Test，会被跑 5 次（每组数据一次）
    @Test
    public void testAdd() {
        Calculator calc = new Calculator();
        assertEquals(expected, calc.add(a, b));
    }
}
```

> 💡 参数化测试是**数据驱动测试**的利器。电商算价、金融算利息、边界值覆盖，一组数据一个用例，失败时 `{index}` 告诉你是第几组挂了。JUnit 5 的 `@ParameterizedTest` + `@CsvSource` 写法更简洁（见新版本补充）。

---

## 八、测试规范

写测试和写生产代码一样有规矩，乱写的测试比没测试更危险（给你虚假的安全感）。

| 规范 | 说明 |
| :--- | :--- |
| **方法独立** | 每个 `@Test` 互不依赖，单独跑也能通过，不能依赖执行顺序 |
| **可重复** | 跑 100 遍结果一致，不能依赖系统时间、随机数、网络状态 |
| **无副作用** | 测试不能改外部状态（数据库、文件），用完要清理（`@After`） |
| **单一断言原则** | 一个测试方法聚焦一个行为，断言别堆一锅（可放宽，但核心逻辑要单一） |
| **命名清晰** | `test方法名_场景_期望`，如 `testDivide_除零_抛异常` |
| **AAA 结构** | Arrange（准备）→ Act（调用）→ Assert（断言），三段分明 |

```java
@Test
public void testDivide_正常除法_返回商() {
    // Arrange：准备
    Calculator calc = new Calculator();
    // Act：调用
    int result = calc.divide(10, 2);
    // Assert：断言
    assertEquals(5, result);
}
```

> 📌 **测试金字塔**：底层大量单元测试（快、隔离）、中层少量集成测试、顶层极少端到端测试。本篇讲的是最底层的单元测试，是金字塔的基石。

---

## ⚠️ 重点

### 重点 1：JUnit 4 测试方法的硬性约定 ⭐

```java
@Test
public void testAdd() {        // ✅ public、void、无参、test 开头
    assertEquals(5, 2 + 3);
}

@Test
void testBad1() { }            // ❌ 非 public，JUnit 4 不认（JUnit 5 可以）
@Test
public void testBad2(int x) { } // ❌ 带参数，运行报错
@Test
public int testBad3() { return 0; }  // ❌ 带返回值
```

> ⚠️ 这是 JUnit 4 和 JUnit 5 最直观的区别：JUnit 4 必须 `public`，JUnit 5 允许包级私有。新手从教程复制代码时最容易踩这个。

### 重点 2：assertEquals 的参数顺序 ⭐⭐

```java
assertEquals(expected, actual);   // ✅ 期望在前，实际在后
assertEquals(actual, expected);   // ❌ 顺序反了，失败信息会误导
```

> ⚠️ 顺序反了测试照样能跑（比较是双向的），但**失败时的报错信息会反**：「expected 5 but was 3」会变成「expected 3 but was 5」，排查时方向全错。养成「期望在前」的肌肉记忆。

### 重点 3：浮点数断言必须带误差 ⭐⭐

```java
assertEquals(0.3, 0.1 + 0.2);              // ❌ 失败：浮点精度
assertEquals(0.3, 0.1 + 0.2, 0.0001);     // ✅ 第三参数是误差 delta
```

> 💡 详见 [04-数据类型](04-数据类型与类型转换.md) 的浮点精度问题。金额测试请用 `BigDecimal`：`assertTrue(bd1.compareTo(bd2) == 0)`。

### 重点 4：@Before 保证测试隔离 ⭐

```java
public class ListTest {
    private List<Integer> list;

    @Before
    public void setUp() {
        list = new ArrayList<>();   // ✅ 每个测试方法拿到全新的 list
    }

    @Test public void testAdd() { list.add(1); assertEquals(1, list.size()); }
    @Test public void testEmpty() { assertEquals(0, list.size()); }  // ✅ 不受 testAdd 影响
}
```

> 📌 如果不写 `@Before`，多个测试方法共用一个 `list` 字段，`testAdd` 加进去的元素会污染 `testEmpty`，测试就不可重复了。

### 重点 5：异常测试别只看类型 ⭐

```java
// ❌ 粗糙：只验类型，方法里任何一处抛 ArithmeticException 都算过
@Test(expected = ArithmeticException.class)
public void testDivideByZero() {
    calc.divide(10, 0);
}

// ✅ 精确：验类型 + 验消息
@Test
public void testDivideByZeroPrecise() {
    try {
        calc.divide(10, 0);
        fail("应抛异常");
    } catch (ArithmeticException e) {
        assertTrue(e.getMessage().contains("除数不能为 0"));
    }
}
```

> 💡 关键路径的异常（如金额不足、权限不足）一定要验消息，否则别人改了错误提示你测不出来，前端拿到的错误码/文案就乱了。

### 重点 6：单元测试不要依赖外部环境 ⭐⭐

```java
// ❌ 依赖真实数据库
@Test
public void testFindUser() {
    User u = userDao.findById(1);   // 数据库挂了测试就挂，不可重复
    assertNotNull(u);
}

// ✅ Mock 掉依赖
@Test
public void testFindUser_Mock() {
    // 用 Mockito 伪造 userDao，不连真实库
    // UserDao mockDao = mock(UserDao.class);
    // when(mockDao.findById(1)).thenReturn(new User(1, "张三"));
    // UserService service = new UserService(mockDao);
    // assertNotNull(service.getUserName(1));
}
```

> ⚠️ 单元测试的「单元」是**单个类/方法**，依赖的数据库、网络、第三方服务都要 Mock 掉。连真实库的叫**集成测试**，是另一回事。Mock 框架常用 Mockito（见实战案例）。

---

## 💻 实战案例

### 案例 1：Calculator 工具类完整测试 ⭐

最经典的入门案例，覆盖正常值、边界值、异常：

```java
package com.example;

import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;

public class CalculatorTest {

    private Calculator calc;

    @Before
    public void setUp() {
        calc = new Calculator();   // 每个测试方法前拿到全新对象
    }

    // 正常值
    @Test
    public void testAdd_正数相加() {
        assertEquals(5, calc.add(2, 3));
    }

    // 边界值
    @Test
    public void testAdd_零值() {
        assertEquals(5, calc.add(5, 0));
        assertEquals(5, calc.add(0, 5));
        assertEquals(0, calc.add(0, 0));
    }

    // 负数
    @Test
    public void testAdd_负数() {
        assertEquals(-5, calc.add(-2, -3));
        assertEquals(1, calc.add(-2, 3));
    }

    // 整数溢出边界
    @Test
    public void testAdd_整数最大值边界() {
        assertEquals(Integer.MAX_VALUE, calc.add(Integer.MAX_VALUE - 1, 1));
        // 注意：MAX_VALUE + 1 会溢出成负数，这是 int 的固有行为
    }

    // 异常：除零
    @Test(expected = ArithmeticException.class)
    public void testDivide_除零_抛异常() {
        calc.divide(10, 0);
    }

    // 异常：消息校验
    @Test
    public void testDivide_除零_异常消息() {
        try {
            calc.divide(10, 0);
            fail("应抛 ArithmeticException");
        } catch (ArithmeticException e) {
            assertTrue(e.getMessage().contains("除数不能为 0"));
        }
    }
}
```

### 案例 2：UserService 业务方法测试（含 Mock 思路）⭐⭐

电商后台典型场景：下单扣库存、查用户。业务层依赖 DAO 层，单测要 Mock 掉 DAO。

```java
// 被测的业务类
package com.example.service;

import com.example.dao.UserDao;
import com.example.model.User;

public class UserService {
    private UserDao userDao;   // 依赖 DAO

    public UserService(UserDao userDao) {
        this.userDao = userDao;
    }

    // 业务：根据 id 查用户名，查不到返回"未知用户"
    public String getUserName(int id) {
        User u = userDao.findById(id);
        if (u == null) return "未知用户";
        return u.getName();
    }

    // 业务：校验用户能否下单（状态正常且未封禁）
    public boolean canOrder(int id) {
        User u = userDao.findById(id);
        if (u == null) return false;
        return u.isActive() && !u.isBanned();
    }
}
```

测试（手写 Mock，不引 Mockito，演示思路）：

```java
package com.example.service;

import com.example.dao.UserDao;
import com.example.model.User;
import org.junit.Test;
import static org.junit.Assert.*;

public class UserServiceTest {

    // 手写一个假 DAO，实现 UserDao 接口
    static class FakeUserDao implements UserDao {
        private User returnUser;
        FakeUserDao(User u) { this.returnUser = u; }
        @Override
        public User findById(int id) { return returnUser; }
    }

    @Test
    public void testGetUserName_用户存在_返回名字() {
        UserDao fakeDao = new FakeUserDao(new User(1, "张三", true, false));
        UserService service = new UserService(fakeDao);
        assertEquals("张三", service.getUserName(1));
    }

    @Test
    public void testGetUserName_用户不存在_返回未知() {
        UserDao fakeDao = new FakeUserDao(null);   // 模拟查不到
        UserService service = new UserService(fakeDao);
        assertEquals("未知用户", service.getUserName(999));
    }

    @Test
    public void testCanOrder_正常用户_可下单() {
        UserDao fakeDao = new FakeUserDao(new User(1, "李四", true, false));
        UserService service = new UserService(fakeDao);
        assertTrue(service.canOrder(1));
    }

    @Test
    public void testCanOrder_封禁用户_不可下单() {
        UserDao fakeDao = new FakeUserDao(new User(1, "王五", true, true));  // banned=true
        UserService service = new UserService(fakeDao);
        assertFalse(service.canOrder(1));
    }

    @Test
    public void testCanOrder_未激活用户_不可下单() {
        UserDao fakeDao = new FakeUserDao(new User(1, "赵六", false, false)); // active=false
        UserService service = new UserService(fakeDao);
        assertFalse(service.canOrder(1));
    }
}
```

> 💡 生产中用 Mockito 写 Mock 更省事：`UserDao mock = mock(UserDao.class); when(mock.findById(1)).thenReturn(new User(...));`。这里手写是为了让你看清 Mock 的本质——**用一个假的实现替换真实依赖，让测试只聚焦被测类的逻辑**。

### 案例 3：参数化测试——电商算价 ⭐⭐

商品单价 × 数量，多组数据一次覆盖：

```java
package com.example;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.Collection;
import static org.junit.Assert.*;

@RunWith(Parameterized.class)
public class PriceCalculatorTest {

    private String price;     // 单价
    private int quantity;     // 数量
    private String expected;  // 期望总价

    public PriceCalculatorTest(String price, int quantity, String expected) {
        this.price = price;
        this.quantity = quantity;
        this.expected = expected;
    }

    @Parameters(name = "{index}: {0}元×{1}={2}元")
    public static Collection<Object[]> data() {
        return Arrays.asList(new Object[][]{
                {"9.90", 1, "9.90"},        // 单买一件
                {"9.90", 3, "29.70"},       // 三件
                {"0.10", 3, "0.30"},        // 经典精度坑，必须 BigDecimal
                {"100.00", 0, "0.00"},      // 边界：买零件
                {"99.99", 100, "9999.00"}   // 大额
        });
    }

    @Test
    public void testTotalPrice() {
        BigDecimal p = new BigDecimal(price);
        BigDecimal total = p.multiply(BigDecimal.valueOf(quantity));
        // ✅ BigDecimal 用 compareTo 比较，equals 会把 1.0 和 1.00 当不等
        assertEquals(0, new BigDecimal(expected).compareTo(total));
    }
}
```

> ⚠️ 注意 `BigDecimal` 比较用 `compareTo` 不用 `equals`：`new BigDecimal("1.0").equals(new BigDecimal("1.00"))` 是 `false`（精度不同），但 `compareTo` 返回 0。金额测试必踩的坑。

### 案例 4：异常场景测试——金融转账 ⭐

转账金额非法时要抛异常，逐个验证：

```java
// 被测类
package com.example.service;

public class TransferService {
    public void transfer(String from, String to, double amount) {
        if (from == null || to == null)
            throw new IllegalArgumentException("账户不能为空");
        if (amount <= 0)
            throw new IllegalArgumentException("转账金额必须大于0");
        if (amount > 50000)
            throw new IllegalStateException("单笔超限，需人工审核");
        // ... 实际转账逻辑
    }
}
```

```java
package com.example.service;

import org.junit.Test;
import static org.junit.Assert.*;

public class TransferServiceTest {

    private final TransferService service = new TransferService();

    @Test(expected = IllegalArgumentException.class)
    public void transfer_收款账户为空_抛异常() {
        service.transfer("A", null, 100);
    }

    @Test(expected = IllegalArgumentException.class)
    public void transfer_金额为零_抛异常() {
        service.transfer("A", "B", 0);
    }

    @Test(expected = IllegalArgumentException.class)
    public void transfer_金额为负_抛异常() {
        service.transfer("A", "B", -50);
    }

    @Test(expected = IllegalStateException.class)
    public void transfer_超额_抛异常() {
        service.transfer("A", "B", 60000);
    }

    @Test
    public void transfer_正常金额_不抛异常() {
        service.transfer("A", "B", 1000);   // 不抛即通过
    }
}
```

### 案例 5：超时测试——防止慢操作 ⭐

```java
import org.junit.Test;

public class PerformanceTest {

    @Test(timeout = 500)
    public void testListAdd_千次操作_500ms内() {
        java.util.ArrayList<Integer> list = new java.util.ArrayList<>();
        for (int i = 0; i < 10000; i++) {
            list.add(i);
        }
        assertEquals(10000, list.size());
    }

    @Test(timeout = 1000)
    public void testStringBuilder_拼接万次_1s内() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 10000; i++) {
            sb.append("x");
        }
        assertEquals(10000, sb.length());
    }
}
```

> 💡 超时测试不是性能基准测试（那是 JMH 的活），只是防止「某次提交不小心写了 O(n²) 死循环」拖垮整个测试套件。设个宽松上限即可。

### 案例 6：用 Mockito 真实 Mock（开发标配）⭐⭐

实际项目几乎都用 Mockito，这里给个完整可跑的样例（需引 `mockito-core`）：

```java
// pom.xml 加：
// <dependency>
//   <groupId>org.mockito</groupId>
//   <artifactId>mockito-core</artifactId>
//   <version>3.x</version>
//   <scope>test</scope>
// </dependency>

import com.example.dao.UserDao;
import com.example.model.User;
import com.example.service.UserService;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;

import static org.mockito.Mockito.*;
import static org.junit.Assert.*;

@RunWith(MockitoJUnitRunner.class)   // ✅ 初始化 @Mock 字段
public class UserServiceMockTest {

    @Mock
    private UserDao userDao;        // ✅ Mockito 自动生成假实现

    @Test
    public void testGetUserName_查到用户_返回名字() {
        // 打桩：当 findById(1) 被调用时，返回一个伪造的 User
        when(userDao.findById(1))
                .thenReturn(new User(1, "张三", true, false));

        UserService service = new UserService(userDao);
        assertEquals("张三", service.getUserName(1));

        // 验证：findById 确实被调了一次，参数是 1
        verify(userDao, times(1)).findById(1);
    }

    @Test
    public void testGetUserName_查不到_返回未知() {
        when(userDao.findById(999)).thenReturn(null);
        UserService service = new UserService(userDao);
        assertEquals("未知用户", service.getUserName(999));
        verify(userDao).findById(999);   // times(1) 可省略
    }
}
```

> 📌 Mockito 三板斧：① `mock`/`@Mock` 造假对象；② `when(...).thenReturn(...)` 打桩；③ `verify(...)` 验证调用。这是 Java 后端单测的事实标准，务必掌握。

---

## 🚀 新版本补充

### JUnit 5：架构与写法全面革新

JUnit 5（Jupiter）不再是单一 jar，而是 `JUnit Platform + JUnit Jupiter + JUnit Vintage` 三模块。Vintage 用来兼容跑 JUnit 4 的测试。Java 8+ 项目新写测试建议直接用 5。

**核心差异**：

```java
import org.junit.jupiter.api.Test;          // ✅ 注意包名变了：jupiter.api
import org.junit.jupiter.api.BeforeEach;    // ✅ @Before → @BeforeEach
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Disabled;       // ✅ @Ignore → @Disabled
import org.junit.jupiter.api.DisplayName;   // ✅ 新增：测试显示名

import static org.junit.jupiter.api.Assertions.*;

class CalculatorJUnit5Test {                  // ✅ 类不必 public（包级私有即可）

    @BeforeEach
    void setUp() { }                          // ✅ 方法也不必 public

    @Test
    @DisplayName("加法：2 + 3 = 5")            // ✅ 报告里显示中文名
    void addTwoNumbers() {
        assertEquals(5, 2 + 3);
    }

    @Disabled("等接口稳定")
    @Test
    void todoTest() { }
}
```

**异常测试：assertThrows（比 JUnit 4 的 expected 强太多）**：

```java
import static org.junit.jupiter.api.Assertions.*;

@Test
void divideByZeroThrows() {
    // ✅ 返回抛出的异常对象，可继续校验消息
    ArithmeticException ex = assertThrows(
            ArithmeticException.class,
            () -> new Calculator().divide(10, 0)   // lambda 里写期望抛异常的代码
    );
    assertTrue(ex.getMessage().contains("除数不能为 0"));
}
```

**参数化测试：@ParameterizedTest + @CsvSource（告别 @RunWith）**：

```java
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class CalculatorParamTest {

    @ParameterizedTest
    @CsvSource({
            "1, 2, 3",
            "-1, 1, 0",
            "0, 0, 0",
            "100, 200, 300"
    })
    void addMultipleCases(int a, int b, int expected) {
        assertEquals(expected, new Calculator().add(a, b));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "  ", "\t"})   // 单参数场景
    void blankStrings(String s) {
        assertTrue(s.trim().isEmpty());
    }
}
```

**断言分组：assertAll（多个断言一起跑，不全失败再报）**：

```java
@Test
void testAllFields() {
    User u = new User(1, "张三", true, false);
    assertAll("用户属性",
            () -> assertEquals(1, u.getId()),
            () -> assertEquals("张三", u.getName()),
            () -> assertTrue(u.isActive()),
            () -> assertFalse(u.isBanned())
    );
}
```

> 💡 JUnit 4 里一个断言失败后面就不跑了，JUnit 5 的 `assertAll` 让所有断言都执行，一次性报告所有失败，排查更高效。

### Java 8+ 对测试的反哺

- **Lambda 让断言更灵活**：`assertTrue(() -> service.isHealthy())`，延迟计算
- **Stream 生成测试数据**：`IntStream.range(0, 100).forEach(i -> ...)` 批量造数据
- **Optional 测试**：`assertTrue(opt.isPresent())` 或 `assertEquals("值", opt.get())`

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 单元测试 | 对最小功能单元（方法）验证，自动断言、可重复 |
| JUnit 4 约定 | `@Test` 方法必须 `public void` 无参 |
| 五大注解 | `@BeforeClass`/`@Before`/`@Test`/`@After`/`@AfterClass` |
| `@BeforeClass`/`@AfterClass` | 必须 `static`，全类只跑一次 |
| `@Before`/`@After` | 每个测试方法前后各跑一次，保证隔离 |
| 核心断言 | `assertEquals(期望, 实际)`、`assertTrue`、`assertNull`、`assertArrayEquals` |
| `assertThat` | `assertThat(实际, 匹配器)`，Hamcrest 更灵活 |
| 异常测试 | `@Test(expected=...)` 或 try-fail-catch 精确校验 |
| 超时测试 | `@Test(timeout=毫秒)` |
| 参数化测试 | `@RunWith(Parameterized.class)` + `@Parameters` |
| 测试规范 | 独立、可重复、无副作用、AAA 结构 |
| Mock | 用假实现替换真实依赖（Mockito 是标配） |
| JUnit 5 | `@BeforeEach`、`assertThrows`、`@ParameterizedTest`、`assertAll` |

---

## 学习建议

1. **先建一个 Maven 项目跑通第一个测试**：别光看，新建 `pom.xml` 引 JUnit 4，写个 `Calculator` + `CalculatorTest`，在 IDEA 里点绿三角看红绿条。跑通一次比看十遍文档管用。
2. **掌握 assertEquals 参数顺序**：期望在前、实际在后。失败信息方向反了会误导排查，从第一天就养成习惯。
3. **把 Mock 思想吃透**：单元测试的灵魂是「隔离」。被测类依赖的 DAO、远程服务都要 Mock 掉。先手写一个 Fake 类理解原理，再上 Mockito。这是 Java 后端面试和实际开发的硬技能。
4. **参数化测试要会写**：电商算价、金融算息、边界值覆盖，一组数据一个用例。JUnit 4 用 `@RunWith(Parameterized.class)`，新项目直接上 JUnit 5 的 `@CsvSource`。
5. **测试要和生产代码一起维护**：改了生产方法立刻改测试，测试挂了立刻修。否则测试会腐烂成「永远绿的摆设」，给你虚假的安全感。CI 里跑测试是底线。
