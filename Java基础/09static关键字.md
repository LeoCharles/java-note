# static 关键字

使用 static 关键字修饰成员变量，就是静态变量。静态变量属于所在的类，多个对象可以共享静态变量。

使用 static 关键字修饰成员方法，这就是一个静态方法，可以通过对象名调用，也可以直接通过类名称调用。

无论是静态变量还是静态方法都推荐使用类名称调用。对于本类中的静态方法，可以省略类名称直接调用。

静态方法不能直接访问非静态内容，因为内存中先有静态内容后有非静态内容。

静态方法中不能使用 this，因为 this 代表当前对象。

静态代码块比构造方法先执行，静态代码块只执行一次。

静态代码块的典型用途是一次性的对静态变量进行赋值。

```java
// Student 类
public class Student {
  private int id;
  private String name;
  private int age;
  // 静态变量，所有对象会共享
  static String room;
  private static int idCounter;  // 每当 new 一个新对象时，计数器加 1

  // 静态代码块
  static {
    // 静态代码块的内容只执行一次，一般用来给静态变量赋值
    System.out.println("静态代码块执行");
    idCounter = 10100;
  }

  public Student() {
      idCounter++;
  }

  public Student(String name, int age) {
    System.out.println("构造方法执行");
    this.name = name;
    this.age = age;
    this.id = ++idCounter;
  }

  // 静态方法
  public static void staticMethod() {
    System.out.println("Student 类中的一个静态方法");
    // 静态方法不能直接访问非静态内容
    // System.out.println(id); // 错误写法
    // 静态方法中不能使用this
    // System.out.println(this); // 错误写法
  }

  // 成员方法
  public void method() {
    System.out.println("Student 类中的一个成员方法");
  }
}

// StaticTest 类
public class StaticTest {
  public static void main(String[] args) {

    Student one = new Student("Tom", 20);
    Student two = new Student("Bob", 30);

    // 给静态变量赋值，所有对象都会共享
    Student.room = "101教室";

    // 推荐使用 Student.room ，也可以用 one.room
    System.out.println("姓名：" + one.getName() + ", 年龄：" + one.getAge() + ", 教室：" + Student.room + "，学号：" + one.getId());
    System.out.println("姓名：" + two.getName() + ", 年龄：" + two.getAge()+ ", 教室：" + Student.room + ", 学号：" + two.getId());

    // 使用类名称直接调用静态方法
    Student.staticMethod();
    // 本类中的静态方法可以直接调用，不需要类名称
    myStaticMethod(); // 等效于 StaticTest.myStaticMethod();
  }

  // 本类中的静态方法
  public static void myStaticMethod() {
    System.out.println("本类中的一个静态方法");
  }
}
```

静态代码块

```java

public class 类名称 {
  static {
    // 静态代码块内容
  }
}
```
