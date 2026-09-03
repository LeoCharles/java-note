# Java 概述与开发环境

Java 是一门**面向对象、跨平台、多线程**的高级编程语言。自 1995 年 Sun 公司发布以来，Java 凭借「一次编译，到处运行」的特性，成为企业级后台开发、大数据、Android 应用等领域的主流语言。学习 Java 的第一步，不是写代码，而是搞懂 JDK/JRE/JVM 的关系、跨平台原理和开发环境搭建——这些概念会贯穿你整个 Java 学习生涯。

> 💡 本篇是整个 Java SE 系列的开篇。建议边读边动手：装好 JDK、配好环境变量、用命令行编译运行一次 HelloWorld、再用 IDEA 创建第一个工程，亲手走完一遍流程，比看十遍教程都管用。

---

## 一、Java 语言概述

### 1.1 Java 的历史

| 时间 | 事件 |
| :--- | :--- |
| 1991 年 | Sun 公司启动「Green Project」，最初语言叫 Oak，用于家电控制 |
| 1995 年 | 正式更名为 Java，发布 JDK 1.0 |
| 2004 年 | JDK 1.5（Java 5）发布，引入泛型、注解、枚举，是里程碑版本 |
| 2009 年 | Oracle 收购 Sun，Java 归 Oracle 所有 |
| 2014 年 | **Java 8** 发布，Lambda、Stream、新日期 API——目前企业最广泛使用的版本 |
| 2018 年起 | 每 6 个月发布一个小版本（9、10、11、17、21…），LTS 版本为 8/11/17/21 |

> 💡 **为什么以 Java 8 为基准？** 截至目前，绝大多数企业生产环境仍运行在 Java 8（部分升级到 11/17）。Java 8 是 Java 历史上变化最大、最经典的版本，掌握 8 之后再向上兼容学习 11/17 成本很低。

### 1.2 Java 的核心特点

```
Java 特点
├── 跨平台（一次编译，到处运行）—— 靠 JVM 实现
├── 面向对象（封装、继承、多态）
├── 多线程（内置多线程支持，Thread/Runnable）
├── 分布式（内置网络库 RMI、Socket，天然适合网络编程）
├── 安全（强类型、字节码校验、无指针运算、安全管理器）
├── 健壮（强类型 + 异常处理 + 垃圾回收，告别 C 的内存泄漏）
└── 解释执行 + JIT（字节码先解释执行，热点代码 JIT 编译为本地码）
```

```java
// 一段最简单的 Java 程序，体现面向对象
public class Hello {
    public static void main(String[] args) {   // 程序入口
        System.out.println("Hello, Java!");    // ✅ 控制台输出
    }
}
// ❌ 一个 .java 文件只能有一个 public 类，且类名必须和文件名一致
```

> ⚠️ Java 是**强类型语言**：每个变量必须先声明类型，编译期严格检查。这和 JavaScript、Python 这类动态语言完全不同。

### 1.3 Java 的三大技术平台

| 平台 | 全称 | 用途 |
| :--- | :--- | :--- |
| **Java SE** | Standard Edition | 标准版，桌面/基础核心，本系列学习内容 |
| **Java EE** | Enterprise Edition | 企业版（现名 Jakarta EE），Web 后台、分布式 |
| **Java ME** | Micro Edition | 微型版，嵌入式/早期手机应用（已边缘化） |

> 💡 学 Java 一般先学 SE（本系列），再学 EE（Spring Boot 等框架）。SE 是地基，EE 是上层建筑。

---

## 二、JDK / JRE / JVM 三者关系

这是 Java 入门最经典的概念题，面试必考。

### 2.1 三个概念

| 名称 | 全称 | 作用 |
| :--- | :--- | :--- |
| **JVM** | Java Virtual Machine | Java 虚拟机，负责把字节码翻译成对应平台的机器指令执行 |
| **JRE** | Java Runtime Environment | Java 运行环境，包含 JVM + 核心类库（rt.jar），**只能运行**程序 |
| **JDK** | Java Development Kit | Java 开发工具包，包含 JRE + 开发工具（javac、javadoc、jdb 等），**能开发也能运行** |

### 2.2 包含关系

```
┌──────────────────────────────────────────────┐
│                    JDK                       │
│  ┌────────────────────────────────────────┐  │
│  │                JRE                     │  │
│  │  ┌──────────────────────────────────┐  │  │
│  │  │            JVM                    │  │  │
│  │  │  负责解释执行 .class 字节码        │  │  │
│  │  └──────────────────────────────────┘  │  │
│  │     + 核心类库（rt.jar、charsets…）     │  │
│  └────────────────────────────────────────┘  │
│    + 开发工具（javac、javadoc、jar、jdb…）    │
└──────────────────────────────────────────────┘
```

> 💡 **记忆口诀**：**JDK ⊃ JRE ⊃ JVM**。开发要装 JDK，只运行装 JRE 就够（但实际开发都直接装 JDK）。

### 2.3 为什么这样设计

```java
// javac（编译器，在 JDK 里）把源码编译成字节码
//   Hello.java  →  Hello.class
// java（启动器，在 JRE 里）启动 JVM 加载字节码执行
//   java Hello  →  JVM 解释执行 Hello.class

// ✅ 同一个 Hello.class 可以在 Windows/Linux/Mac 的 JVM 上运行
// ❌ 没有 JVM，.class 文件无法直接执行
```

> ⚠️ **常见误区**：以为 JVM 是「跨平台」的。其实 JVM **本身不跨平台**——Windows 装 Windows 版 JVM，Linux 装 Linux 版 JVM。跨平台的是 **.class 字节码**，它能在任何平台的 JVM 上跑。

---

## 三、Java 跨平台原理

### 3.1 一次编译，到处运行

```
                  javac 编译              JVM 解释 + JIT
Hello.java  ───────────────→  Hello.class  ──────────────→  屏幕输出
（源码）                      （字节码）                      （运行结果）
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
      Windows JVM            Linux JVM             Mac JVM
      （输出结果）           （输出结果）           （输出结果）
```

```java
// 在 Windows 上编写并编译
public class CrossPlatform {
    public static void main(String[] args) {
        System.out.println("我在 " + System.getProperty("os.name") + " 上运行");
        // ✅ 同一份 .class 拷到 Linux/Mac 上执行，输出对应系统名
    }
}
```

### 3.2 字节码的好处

| 特性 | 说明 |
| :--- | :--- |
| 跨平台 | 同一 .class 跑遍所有平台 |
| 安全 | 字节码在执行前经过 JVM 校验，防止恶意代码 |
| 高效 | 热点代码由 JIT（即时编译器）编译为本地机器码，接近 C 的速度 |
| 语言无关 | Scala、Kotlin、Groovy 也能编译成 .class，在 JVM 上运行 |

> 💡 **字节码文件用十六进制查看，开头永远是 `CAFE BABE`（咖啡宝贝）**——这是 Java 创始人开的小玩笑，也成了 .class 的魔数标识。

---

## 四、环境变量配置

### 4.1 下载安装 JDK

到 Oracle 官网或 Adoptium 下载 JDK 8（如 `jdk-8uXXX-windows-x64.exe`），按默认路径安装，例如装在：

```
C:\Program Files\Java\jdk1.8.0_XXX
```

### 4.2 三个环境变量

| 变量名 | 作用 | 配置示例 |
| :--- | :--- | :--- |
| `JAVA_HOME` | 指向 JDK 根目录，方便其他工具（Tomcat/Maven）调用 | `C:\Program Files\Java\jdk1.8.0_XXX` |
| `Path` | 让系统在任意目录都能找到 `java`、`javac` 命令 | `%JAVA_HOME%\bin` |
| `classpath` | 类加载路径（Java 5 后基本不用配，默认当前目录） | `.;%JAVA_HOME%\lib\dt.jar` |

```bash
# ✅ Windows 配置后验证
java -version      # 查看 JRE 版本
javac -version     # 查看 JDK 版本，两者版本应一致
```

> ⚠️ **Path 配置的坑**：Windows 安装 JDK 时会自动在 Path 里加一条 `C:\Program Files\Common Files\Oracle\Java\javapath`，它指向公共目录。如果装了多个 JDK 版本，可能因为这条路径优先导致 `java -version` 和 `javac -version` 版本不一致。手动把 `%JAVA_HOME%\bin` **上移到最前**即可解决。

> 💡 **classpath 现在基本不用配**。Java 5 之后默认就是当前目录（`.`），强行配置反而可能导致找不到当前目录的类。新手不配 classpath 就行。

### 4.3 macOS / Linux 配置

```bash
# 编辑 ~/.bash_profile 或 ~/.zshrc
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.8.0_XXX.jdk/Contents/Home
export PATH=$JAVA_HOME/bin:$PATH

# 生效
source ~/.zshrc
java -version   # ✅ 验证
```

---

## 五、第一个程序 HelloWorld

### 5.1 编写源文件

新建 `HelloWorld.java`（**文件名必须和 public 类名一致**）：

```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

### 5.2 编译与运行

```bash
# 1. 编译：javac 把 .java 编译成 .class
javac HelloWorld.java          # ✅ 生成 HelloWorld.class

# 2. 运行：java 启动 JVM 执行字节码
java HelloWorld                # ✅ 输出 Hello, World!
# 注意：这里写的是类名，不带 .class 后缀
```

完整流程：

```
编写 HelloWorld.java  →  javac 编译  →  生成 HelloWorld.class  →  java 运行  →  控制台输出
```

### 5.3 常见错误

```java
// ❌ 错误 1：文件名和 public 类名不一致
// 文件叫 Test.java，类叫 HelloWorld → 编译报错
public class HelloWorld { }   // 文件应叫 HelloWorld.java

// ❌ 错误 2：main 方法写错
public static void main() { }              // 缺少 String[] args
public void main(String[] args) { }        // 缺少 static
static void main(String[] args) { }        // 缺少 public（能编译，但 JVM 找不到入口）

// ✅ main 方法固定写法
public static void main(String[] args) { }
// public：JVM 要调用，必须公开
// static：无需创建对象即可调用
// void：主方法无返回值
// String[] args：命令行参数
```

```bash
# ❌ 错误 3：运行时带 .class 后缀
java HelloWorld.class    # 报错：找不到或无法加载主类
java HelloWorld          # ✅ 正确

# ❌ 错误 4：运行时带包路径错误
# 如果类有 package com.demo; 则要在包的根目录执行：
java com.demo.HelloWorld   # ✅ 用全限定类名
```

> 📌 **规范**：一个 `.java` 文件只写一个 `public` 类，文件名和 `public` 类名严格一致。非 public 类可以多个，但不推荐。

### 5.4 注释与 API 文档

```java
/**
 * 这是文档注释，javadoc 工具能把它生成 API 文档
 * @author Leo
 * @version 1.0
 */
public class HelloWorld {
    // 单行注释：解释单行代码
    /*
     多行注释：解释一段逻辑
    */
    public static void main(String[] args) {
        System.out.println("Hello");  // 行尾注释
    }
}
```

```bash
# 生成 API 文档（HTML 格式）
javadoc -d doc -author -version HelloWorld.java
```

> 💡 Java 源码自带 API 文档，离线包可到 Oracle 官网下载 `jdk-8-docs-all.zip`。看源码和 API 是进阶必经之路。

---

## 六、IDEA 开发环境

命令行编译运行是理解原理，真正开发都用 IDE。IntelliJ IDEA 是 Java 圈最主流的集成开发环境。

### 6.1 IDEA 工程结构

```
MyProject/                     ← 工程根目录
├── .idea/                     ← IDEA 的配置文件（版本无关，一般不提交 git）
│   ├── misc.xml
│   └── workspace.xml
├── src/                       ← 源码目录（Source Root，蓝色标记）
│   └── com/demo/Hello.java    ← 按包结构组织
├── out/                       ← 编译输出目录（可配置到 target/）
│   └── production/MyProject/
│       └── com/demo/Hello.class
└── MyProject.iml              ← 模块配置文件
```

| 目录 | 作用 |
| :--- | :--- |
| `src` | 写源码的地方，包结构对应文件夹层级 |
| `out` | IDEA 自动编译生成的 .class，一般不用手动管 |
| `.idea` / `.iml` | IDEA 工程配置，换机器可重新生成 |

> ⚠️ **不要把 `.idea`、`out` 提交到 git**，在 `.gitignore` 里忽略掉。团队协作时每个人本地环境不同。

### 6.2 常用快捷键（默认 Keymap）

| 快捷键 | 功能 | 说明 |
| :--- | :--- | :--- |
| `psvm` + Tab | 生成 `public static void main` | main 方法补全 |
| `sout` + Tab | 生成 `System.out.println` | 输出补全 |
| `soutv` + Tab | 输出变量值带变量名 | 调试常用 |
| `Ctrl + Alt + L` | 格式化代码 | 团队风格统一 |
| `Ctrl + D` | 复制当前行 |  |
| `Ctrl + Y` | 删除当前行 |  |
| `Ctrl + /` | 行注释 `//` |  |
| `Ctrl + Shift + /` | 块注释 `/* */` |  |
| `Alt + Enter` | 智能提示（万能键） | 报错时按它自动修复 |
| `Shift + F6` | 重命名 | 变量/类/方法改名 |
| `Ctrl + B` | 跳转到定义 | 看源码必备 |
| `Ctrl + Alt + V` | 提取变量 | 把表达式结果赋给变量 |
| `Ctrl + Shift + T` | 生成测试 |  |

```java
// 在 IDEA 里输入 psvm 然后按 Tab：
public static void main(String[] args) {

}

// 输入 sout 然后按 Tab：
System.out.println();
// 输入 soutv 然后按 Tab：
System.out.println("变量 = " + 变量);
```

> 💡 **新手第一件事**：把 `psvm`、`sout`、`Alt+Enter`、`Ctrl+B` 这四个练熟，效率立刻翻倍。

### 6.3 创建第一个工程

```
1. File → New → Project → 选 Java，SDK 选 jdk1.8
2. 填工程名 MyFirstProject，选存放目录
3. 在 src 上右键 → New → Java Class → 输入 Hello
4. 在类里输入 psvm + Tab，再 sout + Tab
5. 右键类文件 → Run 'Hello.main()'，或按 Ctrl+Shift+F10
```

```java
public class Hello {
    public static void main(String[] args) {
        System.out.println("我的第一个 IDEA 工程！");
        System.out.println("os = " + System.getProperty("os.name"));
        System.out.println("jdk = " + System.getProperty("java.version"));
    }
}
```

---

## 七、编译与运行机制深入

### 7.1 完整流程

```
Hello.java（源码）
     │ javac 编译（词法/语法/语义分析 → 生成字节码）
     ▼
Hello.class（字节码，与平台无关）
     │ java 启动 JVM
     ▼
┌──────── JVM 运行时 ─────────┐
│  类加载器（ClassLoader）加载  │
│  字节码校验器校验安全性        │
│  解释器逐条解释执行           │
│  JIT 编译热点代码为本地码      │
└──────────────────────────────┘
     │
     ▼
屏幕输出 / 文件 / 网络…
```

### 7.2 字节码 vs 源码 vs 机器码

| 形态 | 例子 | 是否跨平台 | 是否可读 |
| :--- | :--- | :---: | :---: |
| 源码 | `Hello.java` | 是（人写的） | 高 |
| 字节码 | `Hello.class` | 是（JVM 跨平台） | 低（二进制） |
| 机器码 | `01101011…` | 否（绑定 CPU） | 无 |

```java
// 用 javap 反汇编查看字节码
// javap -c HelloWorld
// 输出类似：
// 0: getstatic     #2  // Field java/lang/System.out
// 3: ldc           #3  // String Hello, World!
// 5: invokevirtual #4  // Method println
```

> 💡 `javap` 是 JDK 自带的反汇编工具，能让你看到字节码指令。学 JVM 时会用它分析「代码到底怎么执行的」。

### 7.3 JIT 即时编译

```java
// JVM 默认是解释执行，但「热点代码」（频繁执行的方法/循环）
// 会被 JIT（Just-In-Time Compiler）编译成机器码缓存，下次直接跑机器码

// ✅ 这就是 Java「慢」的印象过时的原因
// 现代 JVM（HotSpot）经过 JIT 优化后，很多场景性能接近 C/C++
```

> ⚠️ JIT 是 JVM 内部机制，作为 Java 开发者一般不用关心，知道「热点代码会被优化」即可。调优时才涉及 `-XX:+PrintCompilation` 等参数。

---

## ⚠️ 重点

### 重点 1：JDK / JRE / JVM 的包含关系 ⭐⭐

```
JDK ⊃ JRE ⊃ JVM
开发需要 JDK，运行只需 JRE，执行字节码靠 JVM
```

> 💡 面试高频题：「JDK、JRE、JVM 是什么关系？」答出包含关系 + 各自职责即可。

### 重点 2：跨平台的是字节码，不是 JVM ⭐⭐

```
Hello.class（跨平台）  →  各平台对应的 JVM（不跨平台）  →  各平台机器码
```

> ⚠️ 别说「JVM 跨平台」，JVM 是针对每个平台单独实现的。跨平台的是 .class 字节码。

### 重点 3：`javac` 编译，`java` 运行 ⭐

```bash
javac HelloWorld.java   # 编译，生成 .class
java HelloWorld         # 运行，注意不带 .class 后缀
```

### 重点 4：main 方法固定写法 ⭐

```java
public static void main(String[] args) { }
// public：JVM 要访问
// static：无需 new 对象
// void：无返回值
// String[] args：命令行参数（即使不用也得写）
```

### 重点 5：文件名必须和 public 类名一致 ⭐

```java
// 文件 HelloWorld.java
public class HelloWorld { }   // ✅
// 文件 Test.java
public class HelloWorld { }   // ❌ 编译错误
```

### 重点 6：环境变量只配 `JAVA_HOME` 和 `Path` ⭐

> 📌 现代 Java 开发 classpath 不用配。`JAVA_HOME` 给 Maven/Tomcat 用，`Path` 加 `%JAVA_HOME%\bin` 让命令全局可用。

---

## 💻 实战案例

### 案例 1：命令行编译运行，体会跨平台 ⭐⭐

模拟真实部署场景：在 Windows 上开发编译，把 .class 拷到 Linux 服务器运行。

```java
// 文件：DeployCheck.java
public class DeployCheck {
    public static void main(String[] args) {
        // 打印运行环境信息，验证跨平台
        System.out.println("== 运行环境信息 ==");
        System.out.println("操作系统：" + System.getProperty("os.name"));
        System.out.println("系统架构：" + System.getProperty("os.arch"));
        System.out.println("Java 版本：" + System.getProperty("java.version"));
        System.out.println("Java 家目录：" + System.getProperty("java.home"));

        // 接收命令行参数
        if (args.length > 0) {
            System.out.println("传入参数：" + args[0]);
        } else {
            System.out.println("未传入参数");
        }
    }
}
```

```bash
# Windows 上编译
javac DeployCheck.java          # 生成 DeployCheck.class

# 把 .class 拷到 Linux 服务器（模拟部署）
scp DeployCheck.class user@server:/opt/app/

# 在 Linux 上运行（无需重新编译！）
ssh user@server
cd /opt/app
java DeployCheck env=prod       # ✅ 输出 Linux 的环境信息
# 输出：
# 操作系统：Linux
# Java 版本：1.8.0_XXX
# 传入参数：env=prod
```

> 💡 这就是「一次编译，到处运行」的真实价值：开发机 Windows 编译一次，部署到 Linux 服务器无需重编译，运维省心。

### 案例 2：IDEA 创建第一个工程并调试

电商后台开发场景：模拟一个订单金额计算的小工具。

```java
// 文件：com/demo/OrderTool.java
package com.demo;

public class OrderTool {
    public static void main(String[] args) {
        // 模拟订单计算
        double price = 199.0;        // 商品单价
        int quantity = 3;            // 购买数量
        double discount = 0.8;       // 八折

        double total = price * quantity * discount;
        System.out.println("商品单价：" + price);
        System.out.println("购买数量：" + quantity);
        System.out.println("折扣：" + discount);
        System.out.println("应付金额：" + total);

        // 在 IDEA 里对 total 行打断点（点行号左侧空白）
        // 右键 Run → Debug，程序会停在断点，可以查看每个变量值
    }
}
```

> 📌 **IDEA 调试流程**：行号左侧点一下出现红点（断点）→ 右键 `Debug 'OrderTool.main()'` → 程序停在断点 → F8 单步执行 → 左下角 Variables 面板看变量值。这是排查 bug 的核心技能。

### 案例 3：用 javap 分析字节码

后台系统排查「字符串拼接到底怎么实现的」：

```java
// 文件：StringConcat.java
public class StringConcat {
    public static void main(String[] args) {
        String a = "Hello";
        String b = "Java";
        String c = a + b;
        System.out.println(c);
    }
}
```

```bash
# 编译
javac StringConcat.java

# 反汇编看字节码
javap -c StringConcat
# 输出会看到：
# 9:  invokevirtual #18  // Method java/lang/StringBuilder.append
# 12: invokevirtual #18  // Method java/lang/StringBuilder.append
# 15: invokevirtual #22  // Method java/lang/StringBuilder.toString
# ✅ 结论：a + b 在底层是用 StringBuilder.append 实现的
```

> 💡 这种「写代码 → 看字节码」的思路，是深入理解 Java 的关键方法。后续学字符串、泛型擦除、Lambda 都会用到。

### 案例 4：配置多版本 JDK 切换

开发中常遇到「老项目用 JDK 8，新项目用 JDK 17」的场景：

```bash
# 思路：用 JAVA_HOME 指向不同版本，Path 引用 %JAVA_HOME%\bin

# Windows 批处理切换（switch-jdk8.bat）
@echo off
set JAVA_HOME=C:\Program Files\Java\jdk1.8.0_XXX
set PATH=%JAVA_HOME%\bin;%PATH%
java -version

# macOS 用 jenv 管理
brew install jenv
jenv add /Library/Java/JavaVirtualMachines/jdk1.8.0_XXX.jdk/Contents/Home
jenv global 1.8
```

> 📌 **规范**：生产环境 JDK 版本要和开发环境严格一致，避免「在我机器上能跑」的经典甩锅场景。

---

## 🚀 新版本补充

### Java 9：模块化系统（Jigsaw）

```java
// Java 9 引入 module-info.java
module com.demo.app {
    requires java.sql;          // 依赖 java.sql 模块
    exports com.demo.api;      // 对外暴露 com.demo.api 包
}
```

> ⚠️ 模块化对企业级项目改造成本高，实际开发中多数项目仍不用模块化。了解即可。

### Java 9：jshell 交互式 REPL

```bash
# Java 9 终于有了类似 Python 的交互式命令行
jshell
jshell> int x = 10;
jshell> System.out.println(x * 2);
20
```

> 💡 学新语法、做小测试时 `jshell` 极其方便，Java 8 没有，只能写完整类编译。

### Java 11：直接运行单文件源码

```bash
# Java 11 之前
javac Hello.java && java Hello

# Java 11 起，单文件可跳过 javac 直接运行
java Hello.java       # ✅ 内部自动编译执行
```

### Java 17：LTS 长期支持版本

Java 17 是继 8、11 之后的 LTS 版本，引入密封类、记录类等特性，是企业升级的新目标。

> 💡 本系列以 Java 8 为基准，新版本特性在各篇章的「新版本补充」小节单独介绍，不影响主线学习。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| Java 特点 | 跨平台、面向对象、多线程、安全、健壮 |
| JDK/JRE/JVM | JDK ⊃ JRE ⊃ JVM；开发装 JDK |
| 跨平台原理 | javac 编译成 .class 字节码，各平台 JVM 解释执行 |
| 环境变量 | 配 `JAVA_HOME` + `Path`，classpath 不用配 |
| HelloWorld | 编写 .java → javac 编译 → java 运行 |
| main 方法 | `public static void main(String[] args)` 固定写法 |
| IDEA 工程 | src 放源码，out 放 .class，.idea 放配置 |
| 快捷键 | psvm、sout、Alt+Enter、Ctrl+B 最常用 |
| 编译运行机制 | 源码 → 字节码 → JVM 解释 + JIT 热点编译 |

---

## 学习建议

1. **亲手走一遍命令行流程**：不要一上来就用 IDEA。先用记事本写 HelloWorld，用 `javac`、`java` 命令编译运行，亲眼看到 .class 文件生成，理解「编译」和「运行」是两步。这是理解 Java 跨平台的根基。
2. **搞懂包含关系再写代码**：JDK/JRE/JVM 的关系、跨平台的是字节码不是 JVM——这两个概念务必想透，面试必问，后续学类加载、JVM 调优都建立在此之上。
3. **环境变量配一次就够**：装好 JDK、配好 `JAVA_HOME` 和 `Path`，`java -version` 和 `javac -version` 都能出来就别折腾了。把精力放在写代码上，不要在环境上耗一周。
4. **IDEA 快捷键刻意练习**：`psvm`、`sout`、`Alt+Enter`、`Ctrl+B`、`Shift+F6` 这几个每天用几十次，第一周就练成肌肉记忆，能省下大量时间。
5. **养成看 API 文档和源码的习惯**：遇到不熟悉的方法，`Ctrl+B` 跟进去看源码；遇到不熟悉的类，查 API 文档。这是从「会用」到「精通」的分水岭，越早养成越好。
