# Arrays

java.util.Arrays 是一个和数组相关的工具类，提供了大量数组操作的静态方法。

+ toString(): 将数组驳岸从字符串。
+ sort(): 将数组按升序排序。
  + 如果是字符串默认按字母升序。
  + 如果是自定义类型，那需要有 Comparable 或 Comparator 接口支持。

```java
public class ArraysTest {
  public static void main(String[] args) {

    // toSting 将数组转换成字符串
    int[] intArr1 = {3, 2, 6, 7, 1, 9};
    String str1 = Arrays.toString(intArr1);
    System.out.println(str1); // [3, 2, 6, 7, 1, 9]

    // sort 将数组按升序排序
    int[] intArr2 = {2, 9, 2, 4, 1, 5, 2, 6};
    Arrays.sort(intArr2); // 没有返回值
    System.out.println(Arrays.toString(intArr2)); // [1, 2, 2, 2, 4, 5, 6, 9]

    String[] arr3 = {"aaa", "vvv", "cc", "dd", "b"};
    Arrays.sort(arr3);
    System.out.println(Arrays.toString(arr3)); // [aaa, b, cc, dd, vvv]
  }
}
```