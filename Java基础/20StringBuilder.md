# StringBuilder

String 字符串是常量，它们的值在创建之后不能更改。

字符串底层是一个被 final 修饰的数组，是一个常量，不能改变。

`private final byte[] value;`

进行字符串相加就会由多个字符串，占用内存多，效率低下。

StringBuilder 字符串缓冲区，可以看作是长度可变的字符串，提高效率。

底层也是一个数组，但没有被 final 修饰。

`byte[] value = new byte(16);`

如果超出了初始的容量，会自动扩容。

## 构造方法

`StringBuilder()`：构造一个不带任何字符的字符串生成器，其初始容量为 16 个字符。

`StringBuilder(String str)`：构造一个字符串生成器，并初始化为指定的字符串内容。

## 成员方法

`public StringBuilder append()`：添加任意类型数据的字符串形式，并返回当前对象自身。

`public String toString()`：将当前 StringBuilder 对象转换为 String 对象。

```java
public class StringBuilderTest {
  public static void main(String[] args) {
    // 空参构造
    StringBuilder str1 = new StringBuilder();
    System.out.println(str1);

    // 传入字符串构造
    StringBuilder str2 = new StringBuilder("hello");
    System.out.println(str2);

    // append 添加任意类型的数据，append 返回 this，可以链式编程
    StringBuilder bu = new StringBuilder();
    bu.append("hello world")
        .append(123)
        .append(false)
        .append(9.9)
        .append('中')
        .append(new Object());
    System.out.println(bu); // hello world123false9.9中java.lang.Object@6acbcfc0

    // toString 方法，将 StringBuilder 转成 String
    str2.append(" world!");
    System.out.println(str2.toString());
  }
}
```
