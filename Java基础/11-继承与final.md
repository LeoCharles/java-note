# 继承与 final

面向对象三大特性之一——**继承**，是复用代码、建模现实世界的核心机制。当多个类存在共性属性和行为时，把它们抽取到父类中，子类继承后即可直接使用，避免重复造轮子。而 `final` 关键字则从「禁止改变」的角度，为继承体系划定边界：哪些类不能再被继承、哪些方法不能再被重写、哪些变量只能赋值一次。理解继承与 `final`，是掌握多态、设计模式、框架源码阅读的基础。

> 💡 本篇涉及「方法重写」「构造方法链」等内容，建议先回顾 [09-构造方法](09-构造方法.md) 和 [10-封装](10-封装.md)，对 `this` 和 `private` 的理解会更顺畅。

---

## 一、继承的由来

假设我们在开发电商系统，有「图书」「服装」「电子产品」三类商品，每类都有名称、价格、库存等共性属性，又各有特有属性（图书有作者、服装有尺码、电子产品有保修期）。

如果不使用继承，每个类都要重复写名称、价格、库存：

```java
// ❌ 不使用继承：每个类都重复写 name、price、stock，代码冗余
class Book {
    String name;
    double price;
    int stock;
    String author;   // 特有
}

class Clothing {
    String name;     // 重复
    double price;    // 重复
    int stock;       // 重复
    String size;      // 特有
}
```

使用继承后，把共性抽取到父类，子类只写特有内容：

```java
// ✅ 使用继承：共性放父类，子类只写特有内容
class Product {           // 父类
    String name;
    double price;
    int stock;
}

class Book extends Product {       // 子类继承父类
    String author;                 // 只写特有属性
}

class Clothing extends Product {
    String size;
}
```

> 💡 **继承的核心价值**：共性抽取（减少重复代码）、代码复用、建立类与类之间的 `is-a` 关系（图书 *是一种* 商品）。

---

## 二、extends 关键字与单继承

Java 用 `extends` 关键字表示继承关系：

```java
class 父类 {
    // 公共属性和方法
}

class 子类 extends 父类 {
    // 特有属性和方法，同时自动拥有父类非 private 成员
}
```

### 2.1 Java 是单继承

一个类只能有**一个直接父类**，不能同时继承多个类：

```java
class A {}
class B {}
class C {}
// class D extends A, B {}  // ❌ Java 不支持多继承

class D extends A {}        // ✅ 只能继承一个
```

> ⚠️ 为什么不支持多继承？为了避免**菱形问题**（Diamond Problem）：如果 A 和 B 都有 `method()`，C 同时继承 A 和 B，调用 `method()` 时编译器无法决定用哪个。Java 用**接口多实现**来弥补这个限制（接口方法无具体实现，不会冲突）。

### 2.2 多级继承

虽然不能多继承，但可以**多级继承**（A → B → C），形成继承链：

```java
class Animal {              // 爷爷类
    String name;
}

class Dog extends Animal {  // 父类
    void bark() {}
}

class Puppy extends Dog {   // 子类
    void cuteness() {}
}

Puppy p = new Puppy();
p.name = "旺财";   // ✅ 能用爷爷类的属性
p.bark();          // ✅ 能用父类的方法
p.cuteness();      // ✅ 自己的方法
```

### 2.3 所有类的父类是 Object

Java 中**所有类**都直接或间接继承自 `java.lang.Object`。如果一个类没有显式 `extends`，编译器会默认让它继承 `Object`：

```java
class Product {
    // 等价于 class Product extends Object
}

// 所以任何对象都能调用 Object 的方法
Product p = new Product();
System.out.println(p.toString());      // 来自 Object
System.out.println(p.equals(p));       // 来自 Object
System.out.println(p.hashCode());      // 来自 Object
System.out.println(p.getClass());      // 来自 Object
```

> 💡 继承链的**最顶层永远是 `Object`**。`Puppy` 的继承链是 `Puppy → Dog → Animal → Object`，查找方法时一层层往上找，直到 `Object` 为止。

---

## 三、成员变量与成员方法的访问特点

子类访问成员时遵循一条规则：**子类有就用自己的，没有就向上找父类**。

### 3.1 成员变量的访问

```java
class Father {
    String name = "父亲";
    int money = 10000;
}

class Son extends Father {
    String name = "儿子";   // 同名变量，会隐藏父类的
    int money = 500;        // 同名变量
}

Son s = new Son();
System.out.println(s.name);    // 儿子（用子类的）
System.out.println(s.money);   // 500（用子类的）

Father f = new Son();          // 父类引用指向子类对象
System.out.println(f.name);    // 父亲（编译看左，成员变量看左边类型）
System.out.println(f.money);   // 10000
```

> ⚠️ 子类出现和父类同名的成员变量，叫做**隐藏**（不是重写！）。实际开发中应避免这种写法，容易造成混淆。

### 3.2 成员方法的访问

```java
class Father {
    void work() {
        System.out.println("种地");
    }
}

class Son extends Father {
    // 没有写 work()，但能用
    void play() {
        System.out.println("打游戏");
    }
}

Son s = new Son();
s.work();   // ✅ 种地（自己没有，向上找父类的）
s.play();   // ✅ 打游戏（自己的）
```

查找过程：`s.work()` → Son 类没有 `work()` → 向上找到 Father 类的 `work()` → 调用。

---

## 四、方法重写（Override）

**方法重写**：子类中出现了和父类**方法签名完全相同**（方法名、参数列表相同）的方法，子类对象调用时执行子类的方法。这是多态的基础。

### 4.1 基本重写

```java
class Animal {
    void eat() {
        System.out.println("动物吃东西");
    }
}

class Cat extends Animal {
    @Override              // 重写注解，推荐显式写出
    void eat() {
        System.out.println("猫吃鱼");
    }
}

Animal a = new Cat();
a.eat();   // 猫吃鱼（执行子类重写后的方法）
```

### 4.2 @Override 注解

`@Override` 是编译期检查注解，告诉编译器「我这是在重写父类方法，请帮我校验」：

```java
class Cat extends Animal {
    @Override
    void eat() {}      // ✅ 编译通过，确实是重写

    @Override
    void Eat() {}      // ❌ 编译错误：父类没有 Eat()，不是重写
}
```

> 📌 **规范**：重写方法时**必须加 `@Override`**。它能帮你发现拼写错误、参数不一致等低级问题。IDE 也会自动提示。

### 4.3 重写的规则（五大规则）⭐⭐

| 规则 | 说明 |
| | :--- |
| 方法名 | 必须与父类相同 |
| 参数列表 | 必须与父类相同 |
| 返回值类型 | 子类 <= 父类（相同或是子类型） |
| 访问权限 | 子类 >= 父类（不能比父类更严格） |
| 异常 | 子类抛出的异常 <= 父类（不能抛更宽的检查异常） |

```java
class Father {
    public Number test(int a) throws Exception {
        return 0;
    }
}

class Son extends Father {
    @Override
    // ✅ 返回 Integer（Number 的子类）、public（不比父严）、throws IOException（Exception 的子类）
    public Integer test(int a) throws IOException {
        return 1;
    }
}
```

权限修饰符从小到大：`private` < `default`(缺省) < `protected` < `public`

```java
class Father {
    protected void method() {}
}

class Son extends Father {
    // @Override
    // void method() {}        // ❌ 缺省权限 < protected，缩小了权限
    @Override
    public void method() {}    // ✅ public > protected，扩大了权限
}
```

> ⚠️ **private 方法不能被重写**：父类的 `private` 方法对子类不可见，子类写同名方法只是「重新定义」，不算重写，`@Override` 会报错。`static` 方法也不能被重写（只能叫隐藏）。

---

## 五、重写 vs 重载的区别

这两个概念名字像，但完全不同，面试常考：

| 对比项 | 重写（Override） | 重载（Overload） |
| | :--- | :--- |
| 发生位置 | 子类与父类之间 | 同一个类内部 |
| 方法名 | 必须相同 | 必须相同 |
| 参数列表 | 必须相同 | **必须不同** |
| 返回值 | 子类 <= 父类 | 无要求 |
| 访问权限 | 子类 >= 父类 | 无要求 |
| 异常 | 子类 <= 父类 | 无要求 |
| 体现 | 运行时多态 | 编译时多态 |
| 典型场景 | 子类改变父类行为 | 同一方法处理不同参数 |

```java
class Calculator {
    // 重载：同名不同参
    int add(int a, int b) { return a + b; }
    double add(double a, double b) { return a + b; }
    int add(int a, int b, int c) { return a + b + c; }
}

class SuperCalculator extends Calculator {
    @Override
    int add(int a, int b) { return a + b + 1; }  // 重写父类方法
}
```

> 💡 **记忆口诀**：重写是「子类改父类」，重载是「同类同名不同参」。

---

## 六、super 关键字

`super` 代表**父类的引用**，用于在子类中明确访问父类的成员。三种用法：

### 6.1 super.成员变量

```java
class Father {
    String name = "父名";
}

class Son extends Father {
    String name = "子名";

    void show() {
        System.out.println(name);        // 子名（默认用子类的）
        System.out.println(this.name);  // 子名
        System.out.println(super.name); // 父名（明确访问父类）
    }
}
```

### 6.2 super.成员方法

```java
class Animal {
    void breathe() {
        System.out.println("呼吸");
    }
}

class Fish extends Animal {
    @Override
    void breathe() {
        super.breathe();   // 先调用父类的方法
        System.out.println("用鳃呼吸");  // 再补充自己的逻辑
    }
}

Fish f = new Fish();
f.breathe();
// 输出：
// 呼吸
// 用鳃呼吸
```

### 6.3 super(...) 调用父类构造

```java
class Person {
    String name;
    Person(String name) {
        this.name = name;
        System.out.println("Person 构造被调用");
    }
}

class Student extends Person {
    String school;
    Student(String name, String school) {
        super(name);          // ✅ 调用父类有参构造，必须放第一行
        this.school = school;
        System.out.println("Student 构造被调用");
    }
}

Student s = new Student("张三", "清华");
// 输出：
// Person 构造被调用
// Student 构造被调用
```

> 💡 **执行顺序**：创建子类对象时，**先执行父类构造，再执行子类构造**。因为子类可能用到父类的成员，必须保证父类成员已初始化。

---

## 七、构造方法调用规则

### 7.1 子类构造默认先调 super()

如果子类构造方法的第一行没有 `super(...)` 或 `this(...)`，编译器会**自动插入一个无参的 `super()`**：

```java
class Father {
    Father() {
        System.out.println("Father 无参构造");
    }
}

class Son extends Father {
    Son() {
        // 编译器自动插入 super();  ← 隐式调用父类无参构造
        System.out.println("Son 无参构造");
    }
}

new Son();
// 输出：
// Father 无参构造
// Son 无参构造
```

### 7.2 父类没有无参构造时的坑 ⭐

```java
class Father {
    Father(String name) {       // 只有有参构造，无参构造没了
        System.out.println("Father 有参构造");
    }
}

class Son extends Father {
    Son() {
        // 编译器自动插入 super();  ❌ 但父类没有无参构造！编译错误
    }
}
```

修复方式：子类构造中显式调用父类有参构造：

```java
class Son extends Father {
    Son() {
        super("默认名");   // ✅ 显式调用父类有参构造，放第一行
    }
}
```

> ⚠️ **实际开发建议**：父类只要写了有参构造，就**顺手写一个无参构造**，避免子类编译报错。很多框架（如 Spring、MyBatis）反射创建对象时也依赖无参构造。

### 7.3 super() 必须在第一行

```java
class Son extends Father {
    Son() {
        System.out.println("hello");
        super();   // ❌ 编译错误：super 调用必须是构造器第一个语句
    }
}
```

### 7.4 this(...) 与 super(...) 不能共存

```java
class Son extends Father {
    Son() {
        this("默认");   // ✅ 调用本类的另一个构造
        // super();    // ❌ 不能同时存在：this() 和 super() 都必须在第一行
    }

    Son(String name) {
        super(name);    // ✅
    }
}
```

> 💡 **规则**：`this(...)` 和 `super(...)` 都只能在构造方法的第一行，所以**二者互斥**。但 `this(...)` 最终还是会调到 `super(...)`——构造链的尽头一定是 `super()`。

构造方法调用链：

```
new Son()
  → Son() 调 this("默认")
    → Son(String) 调 super(name)
      → Father(String)
        → 隐式 super() → Object()
```

---

## 八、抽象类 abstract

当父类的某个方法**无法给出具体实现**（只有方法声明，没有方法体），就把它定义为**抽象方法**，用 `abstract` 修饰。包含抽象方法的类必须是**抽象类**。

### 8.1 抽象方法和抽象类

```java
abstract class Shape {           // 抽象类
    abstract double area();      // 抽象方法：只有声明，没有方法体
    abstract double perimeter(); // 抽象方法

    // 抽象类也可以有普通方法
    void describe() {
        System.out.println("面积：" + area() + "，周长：" + perimeter());
    }
}
```

### 8.2 抽象类不能实例化

```java
// Shape s = new Shape();  // ❌ 编译错误：抽象类不能实例化
Shape c = new Circle(5);    // ✅ 只能用具体子类实例化（多态）
```

### 8.3 子类必须重写所有抽象方法

```java
class Circle extends Shape {
    double radius;
    Circle(double radius) { this.radius = radius; }

    @Override
    double area() { return Math.PI * radius * radius; }       // ✅ 重写

    @Override
    double perimeter() { return 2 * Math.PI * radius; }      // ✅ 重写
}

// 如果只重写一个：
class Triangle extends Shape {
    @Override
    double area() { return 0; }
    // ❌ 编译错误：Triangle 不是抽象类，必须重写 perimeter()
}
```

### 8.4 子类也可以是抽象类

如果子类不想重写全部抽象方法，子类自己也得声明为 `abstract`：

```java
abstract class Quadrilateral extends Shape {
    // 没有重写 area() 和 perimeter()，但因为是抽象类，编译通过
    // 把实现责任继续传递给下一级子类
}
```

> 💡 **抽象类的意义**：强制子类必须实现某些方法（统一规范），同时提供共性代码复用。它是「模板方法模式」的基础（见实战案例）。

---

## 九、final 关键字

`final` 表示「最终的、不可改变的」，有四种用法：

### 9.1 final 修饰类——不能被继承

```java
final class Config {       // final 类，不能被继承
    String version = "1.0";
}

// class SubConfig extends Config {}  // ❌ 编译错误：不能继承 final 类
```

> 💡 JDK 中 `String`、`Integer`、`Math` 等都是 `final` 类。原因：保证这些核心类的行为不被子类篡改（安全性、不可变性）。

### 9.2 final 修饰方法——不能被重写

```java
class Account {
    public final void login() {   // final 方法，子类不能重写
        System.out.println("登录流程固定");
    }
}

class VipAccount extends Account {
    // @Override
    // public void login() {}   // ❌ 编译错误：不能重写 final 方法
}
```

> 💡 场景：父类某个方法涉及核心安全逻辑（如权限校验），不希望子类改变其行为，就加 `final`。

### 9.3 final 修饰变量——只能赋值一次

```java
final int MAX = 100;    // 常量，只能赋值一次
// MAX = 200;           // ❌ 编译错误：不能再次赋值

final int x;            // 只声明，未赋值（空白 final）
x = 10;                 // ✅ 第一次赋值
// x = 20;              // ❌ 不能再赋值
```

成员变量被 `final` 修饰时，必须在以下三个位置之一赋值：**声明时、构造代码块、构造方法**。

```java
class Service {
    final String url;          // 空白 final

    Service(String url) {
        this.url = url;        // ✅ 在构造方法中赋值
    }
}
```

> 📌 **命名规范**：`final` 常量名全大写，单词间用下划线分隔，如 `MAX_CONNECTION`、`DEFAULT_TIMEOUT`。

### 9.4 final 修饰引用类型——地址不可变，内容可变 ⭐⭐

这是最容易踩坑的地方：

```java
final int[] arr = {1, 2, 3};
arr[0] = 99;          // ✅ 内容可以改变
System.out.println(arr[0]);  // 99
// arr = new int[]{4, 5};    // ❌ 地址不能改变

final StringBuilder sb = new StringBuilder("hello");
sb.append(" world");         // ✅ 内容可以改变
System.out.println(sb);      // hello world
// sb = new StringBuilder();  // ❌ 地址不能改变
```

> ⚠️ **关键理解**：`final` 修饰引用类型，锁定的是**引用（地址）**，不是对象本身。对象内部的状态仍然可以修改。这与 `final` 修饰基本类型不同（基本类型存的就是值本身）。

### 9.5 final 与 abstract 互斥

```java
// final abstract class X {}        // ❌ 矛盾：final 不能被继承，abstract 必须被继承
// final abstract void method();    // ❌ 矛盾：final 不能被重写，abstract 必须被重写
```

> 💡 `final` 和 `abstract` 是对立面：一个禁止改变，一个要求改变。二者不能同时出现。

---

## ⚠️ 重点

### 重点 1：方法重写的五大规则 ⭐⭐

这是面试和开发中最常考的知识点。记住核心原则：**子类重写的方法，权限只能更宽、返回只能更小、异常只能更小**。

```java
class Base {
    protected Number calc(int x) throws Exception {
        return x;
    }
}

class Sub extends Base {
    @Override
    public Integer calc(int x) throws IOException {  // ✅ 权限扩大、返回缩小、异常缩小
        return x;
    }
}
```

### 重点 2：子类构造必须先调 super() ⭐

```java
class Father {
    Father() {
        System.out.println("先初始化父类");
    }
}

class Son extends Father {
    Son() {
        // 隐式 super()，先执行父类构造
        System.out.println("再初始化子类");
    }
}
```

> ⚠️ 父类没有无参构造时，子类必须显式 `super(参数)`，否则编译报错。

### 重点 3：final 引用类型的坑 ⭐⭐

```java
final List<String> list = new ArrayList<>();
list.add("a");        // ✅ 内容可变
list.add("b");
list.clear();         // ✅ 内容可变
// list = new LinkedList<>();  // ❌ 引用不能变

// 想要不可变集合：
List<String> immutable = Collections.unmodifiableList(list);
// immutable.add("c");  // ❌ 运行时抛 UnsupportedOperationException
```

### 重点 4：private 和 static 方法不能被重写 ⭐

```java
class Father {
    private void secret() {}
    static void utility() {}
}

class Son extends Father {
    // @Override
    // private void secret() {}    // ❌ 不是重写，是全新定义
    // @Override
    // static void utility() {}   // ❌ 静态方法不能被重写，只能被隐藏
}
```

> ⚠️ 静态方法是基于类型调用的，不参与动态绑定。`Father.utility()` 和 `Son.utility()` 是两个独立的方法。

### 重点 5：抽象类可以有构造方法

```java
abstract class Animal {
    String name;
    Animal(String name) {     // ✅ 抽象类有构造方法，供子类调用
        this.name = name;
    }
    abstract void sound();
}

class Dog extends Animal {
    Dog(String name) {
        super(name);          // ✅ 调用抽象父类的构造
    }
    @Override
    void sound() { System.out.println("汪汪"); }
}
```

> 💡 抽象类不能 `new`，但构造方法存在，是为了让子类在创建对象时初始化父类成员。

---

## 💻 实战案例

### 案例 1：电商商品继承体系 ⭐⭐

电商系统中最典型的继承应用——商品分类。父类定义共性，子类扩展特有属性和计算逻辑。

```java
// 父类：商品
class Product {
    private String name;       // 商品名
    private double price;      // 价格
    private int stock;         // 库存

    public Product(String name, double price, int stock) {
        this.name = name;
        this.price = price;
        this.stock = stock;
    }

    // 计算总价：基础实现
    public double calcTotal(int quantity) {
        return price * quantity;
    }

    // 展示商品信息
    public void display() {
        System.out.println("商品：" + name + "，价格：" + price + "，库存：" + stock);
    }

    public String getName() { return name; }
    public double getPrice() { return price; }
    public int getStock() { return stock; }
}

// 子类：图书（有作者、ISBN）
class Book extends Product {
    private String author;
    private String isbn;

    public Book(String name, double price, int stock, String author, String isbn) {
        super(name, price, stock);   // 调用父类构造
        this.author = author;
        this.isbn = isbn;
    }

    @Override
    public void display() {          // 重写展示方法
        super.display();             // 先展示父类信息
        System.out.println("作者：" + author + "，ISBN：" + isbn);
    }
}

// 子类：电子产品（有保修期，价格可打折）
class Electronics extends Product {
    private int warrantyMonths;      // 保修月数

    public Electronics(String name, double price, int stock, int warrantyMonths) {
        super(name, price, stock);
        this.warrantyMonths = warrantyMonths;
    }

    @Override
    public double calcTotal(int quantity) {   // 重写计算：满 3 件 9 折
        double total = super.calcTotal(quantity);
        if (quantity >= 3) {
            total *= 0.9;
        }
        return total;
    }

    @Override
    public void display() {
        super.display();
        System.out.println("保修：" + warrantyMonths + " 个月");
    }
}

// 使用
Product p1 = new Book("Java编程思想", 99.0, 50, "Bruce Eckel", "9787111218263");
Product p2 = new Electronics("机械键盘", 399.0, 20, 12);

p1.display();
// 商品：Java编程思想，价格：99.0，库存：50
// 作者：Bruce Eckel，ISBN：9787111218263

p2.display();
// 商品：机械键盘，价格：399.0，库存：20
// 保修：12 个月

System.out.println(p1.calcTotal(2));   // 198.0（图书不打折）
System.out.println(p2.calcTotal(3));   // 1077.3（电子产品满3件9折：399*3*0.9）
```

### 案例 2：模板方法模式（抽象类定义流程骨架）⭐⭐

模板方法模式是抽象类最经典的应用：父类定义算法骨架（用 `final` 防止子类改流程），子类只实现具体步骤。

```java
// 抽象父类：定义电商下单流程骨架
abstract class OrderProcessor {
    // 模板方法：固定下单流程，用 final 防止子类篡改
    public final void process(Order order) {
        validateOrder(order);      // 1. 校验订单
        calculateCost(order);     // 2. 计算费用
        deductStock(order);        // 3. 扣库存
        pay(order);               // 4. 支付
        sendNotification(order);  // 5. 通知
    }

    // 通用逻辑直接实现
    private void validateOrder(Order order) {
        if (order.getQuantity() <= 0) {
            throw new IllegalArgumentException("数量必须大于 0");
        }
        System.out.println("✅ 订单校验通过");
    }

    private void deductStock(Order order) {
        System.out.println("✅ 扣减库存：" + order.getProductName() + " x" + order.getQuantity());
    }

    // 抽象方法：子类必须实现
    abstract void calculateCost(Order order);
    abstract void pay(Order order);

    // 钩子方法：子类可选重写
    void sendNotification(Order order) {
        System.out.println("发送短信通知");
    }
}

// 普通订单处理器
class NormalOrderProcessor extends OrderProcessor {
    @Override
    void calculateCost(Order order) {
        double total = order.getUnitPrice() * order.getQuantity();
        System.out.println("✅ 计算费用：" + total);
    }

    @Override
    void pay(Order order) {
        System.out.println("✅ 微信支付");
    }
}

// 会员订单处理器：有折扣，用余额支付
class VipOrderProcessor extends OrderProcessor {
    @Override
    void calculateCost(Order order) {
        double total = order.getUnitPrice() * order.getQuantity() * 0.8;  // 8 折
        System.out.println("✅ 会员价计算费用：" + total);
    }

    @Override
    void pay(Order order) {
        System.out.println("✅ 会员余额支付");
    }

    @Override
    void sendNotification(Order order) {
        System.out.println("发送 App 推送 + 短信通知");  // 重写钩子
    }
}

// 订单对象
class Order {
    private String productName;
    private int quantity;
    private double unitPrice;
    // 构造、getter 省略
    public Order(String productName, int quantity, double unitPrice) {
        this.productName = productName;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
    }
    public String getProductName() { return productName; }
    public int getQuantity() { return quantity; }
    public double getUnitPrice() { return unitPrice; }
}

// 使用
OrderProcessor normal = new NormalOrderProcessor();
normal.process(new Order("手机壳", 2, 29.9));
// ✅ 订单校验通过
// ✅ 计算费用：59.8
// ✅ 扣减库存：手机壳 x2
// ✅ 微信支付
// 发送短信通知

OrderProcessor vip = new VipOrderProcessor();
vip.process(new Order("耳机", 2, 199.0));
// ✅ 订单校验通过
// ✅ 会员价计算费用：318.4
// ✅ 扣减库存：耳机 x2
// ✅ 会员余额支付
// 发送 App 推送 + 短信通知
```

> 💡 模板方法模式在 Spring 框架中大量使用（如 `JdbcTemplate`、`RestTemplate`），理解它是阅读框架源码的关键。

### 案例 3：final 常量定义配置项

```java
class AppConfig {
    // final 常量：全局配置，不可变
    public static final String DB_URL = "jdbc:mysql://localhost:3306/shop";
    public static final String DB_USER = "root";
    public static final int MAX_RETRY = 3;           // 最大重试次数
    public static final long TIMEOUT_MS = 5000L;     // 超时时间
    public static final double DISCOUNT_RATE = 0.85; // 折扣率

    // final 修饰方法：核心校验逻辑不允许子类篡改
    public final boolean checkPermission(String role) {
        return "admin".equals(role);
    }
}

// 使用常量：类名.常量名
System.out.println(AppConfig.DB_URL);
System.out.println(AppConfig.MAX_RETRY);
```

> 📌 **规范**：配置常量集中放在一个类中（或接口中），全大写命名，便于统一管理。修改配置时只改一处。

### 案例 4：final 修饰集合引用的坑

```java
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

class Cache {
    // ❌ 坑：final 只锁引用，内容仍可变，多线程下不安全
    private final List<String> data = new ArrayList<>();

    public void add(String item) {
        data.add(item);    // ✅ 能加（内容可变），但这可能不是你想要的「不可变」
    }

    public List<String> getData() {
        return data;       // ❌ 返回可变集合，外部可随意修改
    }
}

class SafeCache {
    private final List<String> data;

    public SafeCache(List<String> initial) {
        this.data = new ArrayList<>(initial);  // 防御性拷贝
    }

    public List<String> getData() {
        // ✅ 返回不可变视图，外部修改会抛异常
        return Collections.unmodifiableList(data);
    }
}

// 测试
Cache cache = new Cache();
cache.add("a");
cache.getData().add("b");   // 能加！final 没拦住

SafeCache safe = new SafeCache(java.util.Arrays.asList("a"));
// safe.getData().add("b");  // ❌ UnsupportedOperationException
```

> ⚠️ **开发教训**：`final List` 不等于「不可变 List」。想要真正的不可变集合，用 `Collections.unmodifiableList()` 或 Java 9+ 的 `List.of()`。

### 案例 5：final 类——String 的不可变性

```java
// String 是 final 类，不能被继承
// class MyString extends String {}  // ❌ 编译错误

// 这保证了 String 的行为永远一致，不会被恶意子类篡改
// 在 HashMap 中作为 key 时，不可变性保证了 hashCode 稳定

String s1 = "hello";
String s2 = s1;       // s2 和 s1 指向同一个对象
s2 = "world";        // s2 指向新对象，s1 不受影响
System.out.println(s1);  // hello（final 类 + 不可变性）
```

---

## 🚀 新版本补充

### Java 9：接口支持 private 方法

虽然接口不是抽象类，但 Java 9 允许接口中定义 `private` 方法，用于复用默认方法中的公共逻辑：

```java
interface Calculator {
    default int add(int a, int b) {
        log("加法");
        return a + b;
    }

    default int subtract(int a, int b) {
        log("减法");
        return a - b;
    }

    // Java 9+：接口私有方法，复用公共逻辑
    private void log(String operation) {
        System.out.println("执行：" + operation);
    }
}
```

> ⚠️ Java 8 环境下不可用。Java 8 接口只能有 `default` 和 `static` 方法。

### Java 17：密封类 sealed（预览版 Java 16，正式 Java 17）

`sealed` 关键字限制哪些类可以继承它，介于 `final`（完全不能继承）和普通类（任意继承）之间：

```java
// Java 17+
sealed class Shape permits Circle, Square, Triangle {}
// 只有 permits 列出的类能继承 Shape

final class Circle extends Shape {}      // ✅ 在 permits 列表中
final class Square extends Shape {}      // ✅
non-sealed class Triangle extends Shape {} // ✅，但 Triangle 的子类不受限
// class Hexagon extends Shape {}         // ❌ 不在 permits 列表中
```

> 💡 密封类在模式匹配（switch 模式匹配）中非常有用，能实现穷尽性检查。Java 8 不支持，了解即可。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 继承关键字 | `extends`，单继承、多级继承 |
| 顶层父类 | 所有类继承 `Object` |
| 成员访问特点 | 子类有用自己的，没有向上找父类 |
| 方法重写 | `@Override`，方法名参数相同，权限>=父类，返回<=父类，异常<=父类 |
| 重写 vs 重载 | 重写是子类改父类，重载是同类同名不同参 |
| super | `super.变量`、`super.方法()`、`super(参数)` 调父类构造 |
| 构造规则 | 子类构造默认先调 `super()`，必须在第一行 |
| this/super 互斥 | `this(...)` 和 `super(...)` 不能同时出现 |
| 抽象类 | `abstract`，不能实例化，子类必须重写所有抽象方法或自身也是抽象类 |
| final 类 | 不能被继承（如 String） |
| final 方法 | 不能被重写 |
| final 变量 | 只能赋值一次（常量） |
| final 引用 | 地址不可变，内容可变 |
| final 与 abstract | 互斥，不能同时使用 |

---

## 学习建议

1. **画继承图理解关系**：把电商商品体系（Product → Book/Electronics/Clothing）画成 UML 类图，标出哪些是父类成员、哪些是子类特有成员，直观感受 `is-a` 关系。
2. **重点掌握方法重写规则**：五大规则（方法名、参数、返回值、权限、异常）是面试高频考点，动手写代码验证「权限扩大、返回缩小」的合法情况，理解为什么这么设计。
3. **理解 super 的三种用法**：`super.变量`、`super.方法()`、`super(参数)` 分别解决什么问题。特别留意构造方法链的执行顺序，这是理解对象创建过程的关键。
4. **final 引用类型要反复练**：`final List` 内容可变这个坑，90% 的新手都会踩。务必区分「引用不可变」和「对象不可变」，结合 `Collections.unmodifiableList()` 理解真正的不可变集合。
5. **用模板方法模式练手**：抽象类 + `final` 模板方法，是设计模式中最实用的之一。试着用这个模式写一个「数据导出流程」（校验 → 查询数据 → 格式化 → 写文件 → 通知），体会抽象类定义骨架、子类填细节的设计思想。
