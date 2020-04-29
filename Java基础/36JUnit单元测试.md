# JUnit 单元测试

单元测试就是针对最小的功能单元编写测试代码。Java 程序最小的功能单元是方法，对 Java 程序进行单元测试就是针对单个方法的测试。

JUnit是一个开源的 Java 语言的单元测试框架。

JUnit 使用步骤：

+ 定义一个测试类
  + 测试类名：被测试的类名Test
  + 包名：xxx.xxx.xx.test
+ 定义测试方法
  + 方法名：test测试的方法名
  + 返回值：void
  + 参数列表：空参
+ 给测试方法加 @Test 注解
+ 导入 JUnit 依赖环境

JUnit 判定结果：

一般我们会使用断言来处理结果，红色代表失败，绿色代表成功

常用的断言方法：

+ assertEquals(expected, actual)：将期望的结果和运算的结果进行比较
+ assertTrue(): 期待结果为 true
+ assertFalse(): 期待结果为 false
+ assertNotNull(): 期待结果为非 null
+ assertArrayEquals(): 期待结果为数组并与期望数组每个元素的值均相等

常用的注解：

+ @Test 修饰的方法为测试方法
+ @Before 修饰的方法会在测试方法之前被自动执行
+ @After 修饰的方法会在测试方法执行之后自动被执行

```java
public class Calculator {
  // 加法
  public int add(int a, int b) {
    return a + b;
  }

  // 减法
  public int sub(int a, int b) {
    return a - b;
  }
}

public class CalculatorTest {

  Calculator calculator;

  // 所有测试方法在执行之前都会先执行该方法，使用 @Before 注解
  @Before
  public void init() {
    System.out.println("init...");
    // 初始化
    this.calculator = new Calculator();
  }

  // 所有测试方法执行完毕后都会自动执行该方法，使用 @After 注解
  @After
  public void close() {
    System.out.println("close...");
    // 释放资源
    this.calculator = null;
  }

  // 测试 add 方法
  @Test
  public void testAdd() {
    System.out.println("testAdd...");

    int res = this.calculator.add(1, 2);

    // 断言，将自己期望的结果和运算的结果进行比较
    Assert.assertEquals(3, res);
  }

  // 测试 sub 方法
  @Test
  public void testSub() {
    System.out.println("testSub...");

    int res = this.calculator.sub(1, 2);

    Assert.assertEquals(-1, res);
  }
}
```
