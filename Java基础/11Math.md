# Math

java.util.math 类是数学相关的工具类，提供了大量和数学运算相关的操作。

+ abs(): 获取绝对值。
+ ceil(): 向上取值。
+ floor(): 向下取值。
+ round(): 四舍五入。
+ Math.PI: 圆周率常量。

```java
public class MathTest {
  public static void main(String[] args) {

    // 绝对值
    System.out.println(Math.abs(-5));    // 5
    System.out.println(Math.abs(-40L));  // 40
    System.out.println(Math.abs(-2.93)); // 2.93

    // 向上取整
    System.out.println(Math.ceil(8.1)); // 9.0
    System.out.println(Math.ceil(7.9)); // 8.0

    // 向下取整
    System.out.println(Math.floor(8.9)); // 8.0
    System.out.println(Math.floor(9.1)); // 9.0

    // 四舍五入
    System.out.println(Math.round(8.9)); // 9
    System.out.println(Math.round(4.7)); // 5

     // PI 圆周率
    System.out.println(Math.PI);  // 3.141592653589793


  }
}
```
