# Object 类

`java.lang.Object` 是所有类的父类。

如果一个类没有特别指定父类，那么默认则继承自 Object 类。

```java
public class ObjectTest /*extends Object*/ {
  // ...
}
```

## toString 方法

`public String toString()`：返回该对象的字符串表示。

Object 类中 toString 方法返回一个由类名 + @ + 内存地址值组成的字符串。

如果不希望使用 toString 方法的默认行为，可以对它进行覆盖重写。

```java
public class Person {
  private String name;
  private int age;

  // 覆盖重写 toString 方法
  @Override
  public String toString() {
    return "Person{" + "name='" + name + "', age=" + age + "}";
  }
}
```

在 IDEA 中使用 Alt + Insert 快捷键，选择覆盖重写 toString 方法

## equals 方法

`public boolean equals(Object obj)`：判断两个对象是否相等。

Object 类中 equals 方法默认进行 == 运算符的对象地址比较，只要不是同一个对象，结果必然为 false 。

如果希望进行对象的内容比较，即所有或指定部分成员变量相同，就判定两个对象相同，可以覆盖重写 equals 方法。

```java
public class Person {
  private String name;
  private int age;

  // 重写 equals
  @Override
  public boolean equals(Object o) {
    // 如果对象地址一样，则认为相同
    if (this == o)
      return true;
    // 如果参数为空，或者类型信息不一样，则认为不同
    // getClass() != o.getClass() 使用反射类型 等效于
    // 等效于 o instanceof Person
    if (o == null || getClass() != o.getClass())
      return false;
    // 转换为当前类型
    Person person = (Person) o;
    // 要求基本类型相等，并且将引用类型交给java.util.Objects类的equals静态方法取用结果
    return age == person.age && Objects.equals(name, person.name);
  }
}
```

在 jdk7 添加了 `java.util.Objects` 工具类，它提供了一些方法来操作对象。

在比较两个对象的时候，Object 的 equals 方法容易抛出空指针异常，而 Objects 类中的 equals 方法可以避免这个问题。

`public static boolean equals(Object a, Object b)`：判断两个对象是否相等。

```java
public static boolean equals(Object a, Object b) {
  // 避免空指针异常
   return (a == b) || (a != null && a.equals(b));
}
```
