# 迭代器 Iterator

java.util.Iterator 迭代器用于迭代访问(遍历)集合中的元素。

迭代：即集合元素的通用获取方式，在取元素之前先要判断集合中有没有元素，如果有，就把这个元素取出来。

获取迭代器的方法：

`public Iterator iterator()`: 获取集合对应的迭代器，用来遍历集合中的元素。

迭代器接口的常用方法：

`public boolean hasNext()`: 如果仍有元素可以迭代，则返回 true。
`public E next()`: 返回迭代的下一个元素。

jdk1.5 提供了增强 for 循环(foreach)

`Collection<E> extends Iterable<E>`：所有的单列集合都可以使用增强 for 循环。

`public interface Iterable<T>`：实现这个接口允许对象成为 "foreach" 语句的目标。

增强 for 循序专门用来遍历集合和数组。

格式：

```java
for(元素的数据类型 变量名: 集合名/数组名) {
  // ...
}
```

```java
public class IteratorTest {
  public static void main(String[] args) {
    // 创建集合对象，使用多态的方法
    Collection<String> coll = new ArrayList<>();

    // 添加元素
    coll.add("Java");
    coll.add("C++");
    coll.add("Python");
    coll.add("JavaScript");

    // 获取集合对象的迭代器，集合是什么泛型，迭代器就是什么泛型
    Iterator<String> iterator = coll.iterator(); // 把指针(索引)指向集合的 -1 索引
    // 判断集合中有没有下一个元素
    while (iterator.hasNext()) {
      // 取出下一个元素，把指针向后移动一位
      String next = iterator.next();
      System.out.println(next);
    }

    // 使用增强 for 循环遍历集合
    System.out.println("增强 for 循环：");
    for (String s : coll) {
      System.out.println(s);
    }

    // 使用增强 for 循环遍历数组
    int[] arr = {1, 2, 3, 4, 5, 6};
    for (int i : arr) {
      System.out.println(i);
    }
  }
}
```
