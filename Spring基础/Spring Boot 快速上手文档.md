# Java Spring Boot 后端快速上手学习文档

> 📅 创建时间：2026-09  
> 🎯 目标读者：有前端开发基础，希望在短时间内看懂 Java 代码、能上手改代码的工程师  
> 📌 文档定位：速成手册 + 实战案例 + 企业真实场景参考  
> ⚡ 核心理念：**不求精通 Java 语法，只求能看懂、能改、能排查**

---

## 📖 目录

- [第一章：Java 基础速览（够用即可）](#第一章java-基础速览够用即可)
- [第二章：Spring Boot 核心概念](#第二章spring-boot-核心概念)
- [第三章：Spring Boot 项目结构详解](#第三章spring-boot-项目结构详解)
- [第四章：完整的请求处理流程](#第四章完整的请求处理流程)
- [第五章：Spring Boot 启动全流程解密](#第五章spring-boot-启动全流程解密)
- [第六章：实战案例——从零搭建一个用户管理 API](#第六章实战案例从零搭建一个用户管理-api)
- [第七章：实战案例——Bug 排查全流程](#第七章实战案例bug-排查全流程)
- [第八章：常见业务场景代码模板](#第八章常见业务场景代码模板)
- [第九章：常用工具与调试技巧](#第九章常用工具与调试技巧)
- [第十章：学习资源与进阶路线](#第十章学习资源与进阶路线)

---

# 第一章：Java 基础速览（够用即可）

> 如果你是前端开发者，可以把 Java 想象成"带类型的 TypeScript + 严谨的语法"。本章只讲看懂代码所需的核心知识。

## 1.1 类型系统

Java 是**强类型**语言，每个变量必须声明类型。这和 TypeScript 很像，但更严格——没有 `any`。

```java
// ===== 基本类型（小写开头，存值） =====
int count = 10;           // 整数
long bigNumber = 100L;    // 长整数（加 L）
double price = 99.99;     // 浮点数
boolean isActive = true;  // 布尔值
char letter = 'A';        // 单个字符

// ===== 引用类型（大写开头，存对象引用） =====
String name = "张三";              // 字符串（最常用）
Integer count2 = 10;               // 整数的包装类（可为 null）
Long bigNumber2 = 100L;
Double price2 = 99.99;
Boolean isActive2 = true;

// ⚠️ 关键区别：基本类型不能为 null，引用类型可以为 null
// 前端类比：基本类型 ≈ number/boolean，引用类型 ≈ 包装对象
```

### 前端开发者的对照表

| 前端 (JS/TS) | Java | 说明 |
|---|---|---|
| `let x = 10` | `int x = 10` | Java 必须声明类型 |
| `let name = "hi"` | `String name = "hi"` | 字符串（S 大写） |
| `let list = [1,2,3]` | `List<Integer> list = Arrays.asList(1,2,3)` | 列表需指定元素类型 |
| `let map = {a: 1}` | `Map<String, Integer> map = new HashMap<>()` | Map 需指定键值类型 |
| `x === null` | `x == null` | Java 用 `==` 比较 null |
| `const fn = () => {}` | `Runnable fn = () -> {}` | Lambda 表达式 |
| `let x: string \| null` | `String x = null` | 引用类型默认可为 null |

## 1.2 类与对象（面向对象核心）

Java 一切皆类（Class）。这比 JS 的 class 更纯粹——连入口函数都必须在类里。

```java
// 定义一个类
public class User {
    // 1. 字段（属性）—— 类比 JS class 的 this.name
    private String name;      // private = 外部不能直接访问
    private int age;
    private String email;

    // 2. 构造方法 —— 类比 JS 的 constructor()
    public User(String name, int age, String email) {
        this.name = name;
        this.age = age;
        this.email = email;
    }

    // 3. Getter/Setter —— Java 的标准做法，用方法访问私有字段
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}

// 使用类
User user = new User("张三", 25, "zhangsan@example.com");
user.getName();   // "张三"
user.setAge(26);  // 修改年龄
```

> **💡 前端开发者提示**：在 Spring Boot 项目中，你经常会看到用 Lombok 注解简化 Getter/Setter，后文会讲。

### 访问修饰符

```java
public class Demo {
    public String pub = "任何地方都能访问";     // 最开放
    private String pri = "只有本类内部能访问";   // 最常用（封装）
    protected String pro = "本类和子类能访问";    // 继承相关
    String def = "同包内能访问";                 // 默认（不写修饰符）
}
```

## 1.3 接口（Interface）

接口是 Java 实现"契约"的方式——定义了"能做什么"，不定义"怎么做"。前后端对接时，接口概念是一样的。

```java
// 定义接口：声明方法签名的集合
public interface UserService {
    User findById(Long id);           // 根据 ID 查找用户
    List<User> listAll();             // 列出所有用户
    User create(User user);           // 创建用户
    void delete(Long id);             // 删除用户
}

// 实现接口：用 implements 关键字
public class UserServiceImpl implements UserService {
    @Override
    public User findById(Long id) {
        // 具体实现：查数据库...
        return new User("张三", 25, "test@test.com");
    }

    @Override
    public List<User> listAll() {
        // ...
        return new ArrayList<>();
    }

    @Override
    public User create(User user) {
        // ...
        return user;
    }

    @Override
    public void delete(Long id) {
        // ...
    }
}
```

> **💡 前端类比**：接口就像 TypeScript 的 `interface`，但 Java 接口还可以被类"实现"（implements），强制类必须提供接口中定义的所有方法。

## 1.4 注解（Annotation）

注解是 Java 的核心特性，Spring Boot 大量使用注解来简化配置。注解以 `@` 开头，可以放在类、方法、字段上。

```java
// 你会在 Spring Boot 中经常看到这些注解：

@RestController  // 标记这个类是 REST API 控制器
@RequestMapping("/api/users")  // 指定 URL 路径前缀
public class UserController {

    @Autowired  // 自动注入依赖（Spring 帮你 new 对象）
    private UserService userService;

    @GetMapping("/{id}")  // 处理 GET 请求
    public User getUser(@PathVariable Long id) {  // @PathVariable 从 URL 提取参数
        return userService.findById(id);
    }

    @PostMapping  // 处理 POST 请求
    public User createUser(@RequestBody User user) {  // @RequestBody 从请求体解析 JSON
        return userService.create(user);
    }
}
```

> **💡 前端类比**：注解就像 JS 的装饰器（Decorator）——`@Component` 类似 `@Component()`，`@GetMapping` 类似 `@Get()`。

## 1.5 泛型（Generics）

Java 的泛型类似 TypeScript 的泛型，用于指定集合中元素的类型。

```java
// 不使用泛型（不推荐）
List list = new ArrayList();
list.add("hello");
list.add(123);  // 可以混入不同类型，不安全
String s = (String) list.get(0);  // 需要强制类型转换

// 使用泛型（推荐）
List<String> list = new ArrayList<>();  // 尖括号里指定类型
list.add("hello");
// list.add(123);  // 编译错误！类型安全
String s = list.get(0);  // 不需要类型转换

// 复杂泛型示例
Map<String, List<User>> userMap = new HashMap<>();  // key=String, value=List<User>

// 方法泛型
public <T> T getFirst(List<T> list) {
    return list.get(0);
}
```

## 1.6 异常处理

Java 把错误分为两类：受检异常（必须处理）和运行时异常（可以不处理）。

```java
// try-catch 基本结构
try {
    // 可能抛出异常的代码
    int result = 10 / 0;
} catch (ArithmeticException e) {
    // 捕获特定异常
    System.out.println("除零错误：" + e.getMessage());
} catch (Exception e) {
    // 捕获所有异常
    e.printStackTrace();  // 打印堆栈（排查问题常用）
} finally {
    // 无论是否异常都会执行（释放资源）
    System.out.println("清理工作");
}

// Spring Boot 中常见的异常处理方式
@RestControllerAdvice  // 全局异常处理器
public class GlobalExceptionHandler {

    @ExceptionHandler(Exception.class)  // 捕获所有 Exception
    public ResponseEntity<String> handleException(Exception e) {
        return ResponseEntity.status(500).body("服务器错误：" + e.getMessage());
    }
}
```

## 1.7 集合框架速查

Java 集合框架就像前端常用的数组和对象，但类型更丰富。

```java
// ===== List：有序可重复（类比 JS Array） =====
List<String> list = new ArrayList<>();
list.add("A");
list.add("B");
list.add("A");  // 可以重复
list.get(0);    // "A"
list.size();    // 3
list.isEmpty(); // false
list.contains("B");  // true

// 遍历
for (String item : list) {  // 增强 for 循环（最常用）
    System.out.println(item);
}

list.forEach(item -> System.out.println(item));  // Lambda 写法

// ===== Set：无序不重复（类比 JS Set） =====
Set<String> set = new HashSet<>();
set.add("A");
set.add("B");
set.add("A");  // 不会重复添加
set.contains("A");  // true

// ===== Map：键值对（类比 JS Map/Object） =====
Map<String, Integer> map = new HashMap<>();
map.put("apple", 3);
map.put("banana", 5);
map.get("apple");       // 3
map.getOrDefault("orange", 0);  // 0（不存在时返回默认值）
map.containsKey("apple");    // true
map.containsValue(5);        // true

// 遍历
for (Map.Entry<String, Integer> entry : map.entrySet()) {
    System.out.println(entry.getKey() + ": " + entry.getValue());
}

map.forEach((key, value) -> System.out.println(key + ": " + value));  // Lambda
```

## 1.8 Stream API（数据处理利器）

Stream 是 Java 8 引入的函数式数据处理方式，类比 JS 的 `map`/`filter`/`reduce` 链式操作。

```java
List<User> users = Arrays.asList(
    new User("张三", 25, "zhang@test.com"),
    new User("李四", 30, "li@test.com"),
    new User("王五", 20, "wang@test.com")
);

// 过滤：找出年龄 > 22 的用户
List<User> adults = users.stream()
    .filter(u -> u.getAge() > 22)       // 类比 JS 的 filter
    .collect(Collectors.toList());       // 转回 List

// 映射：提取所有用户名
List<String> names = users.stream()
    .map(User::getName)                  // 类比 JS 的 map
    .collect(Collectors.toList());       // ["张三", "李四", "王五"]

// User::getName 是方法引用，等价于 u -> u.getName()

// 分组：按年龄分组
Map<Integer, List<User>> byAge = users.stream()
    .collect(Collectors.groupingBy(User::getAge));

// 查找第一个
User first = users.stream()
    .filter(u -> u.getAge() > 25)
    .findFirst()
    .orElse(null);  // 找不到返回 null

// 统计
long count = users.stream().filter(u -> u.getAge() > 22).count();  // 2
```

> **💡 前端对照表**：
> | JS 操作 | Java Stream 等价 |
> |---|---|
> | `arr.filter(fn)` | `.filter(fn).collect(toList())` |
> | `arr.map(fn)` | `.map(fn).collect(toList())` |
> | `arr.find(fn)` | `.filter(fn).findFirst().orElse(null)` |
> | `arr.some(fn)` | `.anyMatch(fn)` |
> | `arr.every(fn)` | `.allMatch(fn)` |
> | `arr.reduce(fn)` | `.reduce(fn)` |
> | `arr.sort(fn)` | `.sorted(Comparator)` |

## 1.9 Optional（处理 null 的优雅方式）

Optional 是 Java 用来避免 NullPointerException（空指针异常）的容器类。

```java
// 不用 Optional（容易出错）
User user = findById(1L);
if (user != null) {
    String name = user.getName();
}

// 用 Optional（更安全）
Optional<User> userOpt = findByIdOptional(1L);
String name = userOpt
    .map(User::getName)           // 如果不为 null，提取 name
    .orElse("未知用户");           // 如果为 null，返回默认值

// 常用方法
userOpt.isPresent();              // 判断是否有值（类似 != null）
userOpt.ifPresent(u -> {...});    // 如果有值，执行操作
userOpt.orElseThrow(() -> new RuntimeException("用户不存在"));  // 为空则抛异常
```

---

# 第二章：Spring Boot 核心概念

## 2.1 什么是 Spring Boot

Spring Boot 是 Java 生态中最流行的后端框架，基于 Spring 框架构建。它的核心价值是**约定大于配置**——帮你省去大量 XML 配置，开箱即用。

> **💡 前端类比**：
> - Spring ≈ React 核心库（提供基础能力）
> - Spring Boot ≈ Next.js / Nuxt.js（带最佳实践的脚手架，开箱即用）
> - Spring MVC ≈ Express.js（处理 HTTP 请求的层）

## 2.2 核心概念速览

```
┌─────────────────────────────────────────────────────┐
│                  Spring Boot 应用                      │
│                                                       │
│  浏览器/前端 → [Controller] → [Service] → [Repository] → [数据库] │
│                 ↑ 控制器     ↑ 业务逻辑   ↑ 数据访问        │
│                                                       │
│  核心机制：                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ IoC 容器  │  │ 依赖注入  │  │ AOP 切面  │            │
│  │ 管理对象  │  │ 自动装配  │  │ 横切逻辑  │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────┘
```

### 2.2.1 IoC 容器（控制反转）

**IoC（Inversion of Control）**：你不需要自己 `new` 对象，Spring 容器帮你创建和管理所有对象。

```java
// 传统方式：你自己 new 对象
UserService userService = new UserServiceImpl();
UserController controller = new UserController(userService);

// Spring 方式：声明你要什么，Spring 帮你注入
@RestController
public class UserController {
    @Autowired
    private UserService userService;  // Spring 自动帮你 new 好并赋值
}
```

> **💡 前端类比**：IoC 就像前端的依赖注入框架（如 Angular 的 DI、Vue 的 provide/inject），你声明依赖，框架帮你注入实例。

### 2.2.2 Bean（Spring 管理的对象）

在 Spring 中，被 Spring 容器管理的对象叫 **Bean**。你可以把 Bean 理解为"被 Spring 托管的单例对象"。

```java
// 标记一个类为 Bean 的几种方式：

@Component  // 通用组件
@Service    // 业务逻辑层组件（语义更明确）
@Repository // 数据访问层组件（语义更明确）
@Controller // 控制器组件（语义更明确）

// 这些注解本质上都是 @Component，只是语义不同，方便分层
```

### 2.2.3 依赖注入（DI）

**DI（Dependency Injection）**：Spring 把 Bean 之间的依赖关系自动"注入"。

```java
// 三种注入方式：

// 方式1：字段注入（@Autowired 在字段上，最常见但不推荐用于测试）
@RestController
public class UserController {
    @Autowired
    private UserService userService;
}

// 方式2：构造器注入（推荐！Spring 官方推荐）
@RestController
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }
}

// 方式3：Lombok 简化构造器注入（企业项目中最常见）
@RestController
@RequiredArgsConstructor  // Lombok 自动生成包含 final 字段的构造器
public class UserController {
    private final UserService userService;
    // 不需要手动写构造器，Lombok 编译时自动生成
}
```

### 2.2.4 AOP（面向切面编程）

AOP 让你在不修改业务代码的情况下，添加横切逻辑（如日志、权限校验、事务管理）。

```java
// 一个简单的日志切面示例
@Aspect
@Component
public class LoggingAspect {

    // 拦截所有 Controller 的方法
    @Around("execution(* com.example.controller.*.*(..))")
    public Object logMethod(ProceedingJoinPoint joinPoint) throws Throwable {
        String methodName = joinPoint.getSignature().getName();
        System.out.println("开始执行：" + methodName);  // 前置操作

        Object result = joinPoint.proceed();  // 执行原方法

        System.out.println("执行完成：" + methodName);  // 后置操作
        return result;
    }
}
```

> **💡 前端类比**：AOP 就像 Express/Koa 的中间件，或 React 的 HOC（高阶组件）——在函数执行前后添加额外逻辑。

## 2.3 Spring Boot 的自动配置

Spring Boot 最大的魔法是**自动配置（Auto-Configuration）**。它会根据你引入的依赖，自动配置好相应的组件。

```java
// 启动类上的 @SpringBootApplication 注解包含了三个注解：
@SpringBootConfiguration  // 标记为配置类
@EnableAutoConfiguration  // 开启自动配置（核心魔法）
@ComponentScan            // 自动扫描当前包下的所有组件
```

**自动配置的工作原理**：

```
1. 你引入 spring-boot-starter-web 依赖
2. Spring Boot 检测到 classpath 中有 Tomcat 和 Spring MVC
3. 自动配置：启动内嵌 Tomcat、注册 DispatcherServlet、配置消息转换器...
4. 你不需要任何 XML 配置，直接写 Controller 就能接收请求
```

---

# 第三章：Spring Boot 项目结构详解

## 3.1 典型项目目录结构

```
project-root/
├── pom.xml                      # Maven 依赖管理（类似 package.json）
├── src/
│   ├── main/
│   │   ├── java/com/example/demo/
│   │   │   ├── DemoApplication.java          # 启动类（入口）
│   │   │   ├── config/                        # 配置类
│   │   │   │   ├── WebConfig.java             # Web 配置（跨域、拦截器等）
│   │   │   │   └── SwaggerConfig.java         # API 文档配置
│   │   │   ├── controller/                    # 控制器层（接收请求）
│   │   │   │   ├── UserController.java
│   │   │   │   └── AuthController.java
│   │   │   ├── service/                       # 业务逻辑层
│   │   │   │   ├── UserService.java           # 接口
│   │   │   │   └── impl/
│   │   │   │       └── UserServiceImpl.java   # 实现
│   │   │   ├── repository/                    # 数据访问层（DAO）
│   │   │   │   └── UserRepository.java
│   │   │   ├── entity/                        # 实体类（数据库表映射）
│   │   │   │   ├── User.java
│   │   │   │   └── BaseEntity.java            # 公共字段基类
│   │   │   ├── dto/                           # 数据传输对象
│   │   │   │   ├── UserCreateRequest.java     # 创建请求
│   │   │   │   ├── UserUpdateRequest.java     # 更新请求
│   │   │   │   └── UserResponse.java          # 返回结果
│   │   │   ├── exception/                     # 自定义异常
│   │   │   │   ├── BusinessException.java
│   │   │   │   └── GlobalExceptionHandler.java
│   │   │   ├── util/                          # 工具类
│   │   │   │   └── JwtUtil.java
│   │   │   └── enums/                         # 枚举类
│   │   │       └── UserStatus.java
│   │   └── resources/
│   │       ├── application.yml                # 主配置文件
│   │       ├── application-dev.yml            # 开发环境配置
│   │       ├── application-prod.yml           # 生产环境配置
│   │       └── mapper/                        # MyBatis SQL 映射文件
│   │           └── UserMapper.xml
│   └── test/                                  # 测试代码
│       └── java/com/example/demo/
│           └── service/
│               └── UserServiceTest.java
```

## 3.2 各层职责说明

| 层 | 包名 | 职责 | 前端类比 |
|---|---|---|---|
| Controller | `controller/` | 接收 HTTP 请求，参数校验，调用 Service，返回响应 | Express Router 的路由处理函数 |
| Service | `service/` | 业务逻辑处理，事务管理，编排多个 Repository | 业务逻辑层（Service 层） |
| Repository | `repository/` | 数据库 CRUD 操作，只负责数据访问 | 数据库 ORM 层（Prisma/TypeORM） |
| Entity | `entity/` | 数据库表对应的 Java 对象（ORM 映射） | Prisma Schema 定义的 Model |
| DTO | `dto/` | 接口输入输出的数据结构（不与数据库绑定） | API 请求/响应的 TypeScript 类型 |

## 3.3 关键文件解读

### pom.xml（项目依赖文件）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <parent>
        <!-- 继承 Spring Boot 父项目，统一版本管理 -->
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>

    <dependencies>
        <!-- Web 启动器：包含 Spring MVC + 内嵌 Tomcat -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>

        <!-- 数据库相关：JPA + 连接池 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>

        <!-- MySQL 驱动 -->
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
        </dependency>

        <!-- Lombok：简化代码（getter/setter/构造器自动生成） -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>

        <!-- 测试 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

> **💡 前端类比**：`pom.xml` ≈ `package.json`，`spring-boot-starter-*` ≈ npm 包，`<parent>` ≈ 继承基础配置。

### application.yml（配置文件）

```yaml
# ===== 服务器配置 =====
server:
  port: 8080                          # 服务端口号

# ===== 数据库配置 =====
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb?useSSL=false&serverTimezone=Asia/Shanghai
    username: root
    password: 123456
    driver-class-name: com.mysql.cj.jdbc.Driver

  # ===== JPA 配置 =====
  jpa:
    hibernate:
      ddl-auto: update                # 自动更新表结构（开发环境用）
    show-sql: true                    # 打印 SQL 语句（调试用）

# ===== 自定义配置 =====
app:
  jwt:
    secret: my-secret-key
    expiration: 86400000              # 24小时，单位毫秒
```

> **💡 前端类比**：`application.yml` ≈ `.env` + `config.js`，集中管理所有配置。

---

# 第四章：完整的请求处理流程

## 4.1 一个请求的完整生命周期

让我们追踪一个 `GET /api/users/1` 请求从进入到返回的完整路径：

```
┌─────────────────────────────────────────────────────────────────┐
│ 第1步：浏览器发送请求                                               │
│ GET http://localhost:8080/api/users/1                            │
│ Header: Authorization: Bearer eyJhbG...                          │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第2步：Tomcat（内嵌服务器）接收请求                                  │
│ - 解析 HTTP 协议                                                  │
│ - 创建 HttpServletRequest / HttpServletResponse 对象             │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第3步：DispatcherServlet（前端控制器）                              │
│ - 这是 Spring MVC 的核心入口                                      │
│ - 根据 URL 查找匹配的 Handler（Controller 方法）                     │
│ - 经过拦截器链（Interceptor）→ 权限校验、日志等                      │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第4步：Controller 层处理                                          │
│ @RestController                                                 │
│ @RequestMapping("/api/users")                                   │
│ public class UserController {                                   │
│     @GetMapping("/{id}")                                        │
│     public UserResponse getUser(@PathVariable Long id) {        │
│         return userService.findById(id);  // 调用 Service        │
│     }                                                           │
│ }                                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第5步：Service 层处理（业务逻辑）                                    │
│ @Service                                                        │
│ public class UserServiceImpl implements UserService {           │
│     public UserResponse findById(Long id) {                     │
│         User user = userRepository.findById(id)                 │
│             .orElseThrow(() -> new NotFoundException("用户不存在"));│
│         return convertToResponse(user);  // Entity → DTO 转换   │
│     }                                                           │
│ }                                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第6步：Repository 层（数据访问）                                    │
│ public interface UserRepository extends JpaRepository<User,Long>{│
│     // Spring Data JPA 自动生成 SQL：SELECT * FROM users WHERE id=?│
│ }                                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第7步：数据库执行 SQL                                              │
│ SELECT id, name, age, email, created_at, updated_at              │
│ FROM users WHERE id = 1                                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第8步：结果逐层返回                                                │
│ DB → Entity → DTO → JSON → HTTP Response                        │
│ {                                                               │
│   "id": 1,                                                      │
│   "name": "张三",                                                │
│   "age": 25,                                                    │
│   "email": "zhang@test.com"                                     │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 4.2 各层代码示例

### Entity（实体类）

```java
package com.example.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity                          // 标记为 JPA 实体
@Table(name = "users")           // 映射到数据库 users 表
@Data                            // Lombok：自动生成 getter/setter/toString/equals/hashCode
@NoArgsConstructor               // Lombok：无参构造器
@AllArgsConstructor              // Lombok：全参构造器
public class User {

    @Id                         // 主键
    @GeneratedValue(strategy = GenerationType.IDENTITY)  // 自增
    private Long id;

    @Column(nullable = false, length = 50)  // 非空，最大长度 50
    private String name;

    @Column(nullable = false)
    private Integer age;

    @Column(unique = true)      // 唯一约束
    private String email;

    @Column(name = "created_at", updatable = false)  // 映射到 created_at 列
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    // 插入前自动设置时间
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    // 更新前自动设置时间
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
```

### DTO（数据传输对象）

```java
package com.example.demo.dto;

import lombok.*;

// 创建用户请求
@Data
public class UserCreateRequest {
    @NotBlank(message = "姓名不能为空")  // 校验注解
    private String name;

    @Min(value = 1, message = "年龄必须大于0")
    @Max(value = 150, message = "年龄不能超过150")
    private Integer age;

    @Email(message = "邮箱格式不正确")
    @NotBlank(message = "邮箱不能为空")
    private String email;
}

// 用户返回结果
@Data
@Builder  // Lombok：支持建造者模式
@NoArgsConstructor
@AllArgsConstructor
public class UserResponse {
    private Long id;
    private String name;
    private Integer age;
    private String email;
    private LocalDateTime createdAt;
}
```

### Controller（控制器）

```java
package com.example.demo.controller;

import com.example.demo.dto.*;
import com.example.demo.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController                                         // = @Controller + @ResponseBody
@RequestMapping("/api/users")                          // 所有方法的基础路径
@RequiredArgsConstructor                               // Lombok：final 字段构造器注入
public class UserController {

    private final UserService userService;

    // GET /api/users —— 获取所有用户
    @GetMapping
    public ResponseEntity<List<UserResponse>> listUsers() {
        return ResponseEntity.ok(userService.listAll());
    }

    // GET /api/users/{id} —— 获取单个用户
    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.findById(id));
    }

    // POST /api/users —— 创建用户
    @PostMapping
    public ResponseEntity<UserResponse> createUser(
            @Valid @RequestBody UserCreateRequest request) {  // @Valid 触发校验
        return ResponseEntity.status(201).body(userService.create(request));
    }

    // PUT /api/users/{id} —— 更新用户
    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateUser(
            @PathVariable Long id,
            @Valid @RequestBody UserUpdateRequest request) {
        return ResponseEntity.ok(userService.update(id, request));
    }

    // DELETE /api/users/{id} —— 删除用户
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        userService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
```

### Service（业务逻辑层）

```java
package com.example.demo.service;

import com.example.demo.dto.*;
import java.util.List;

public interface UserService {
    List<UserResponse> listAll();
    UserResponse findById(Long id);
    UserResponse create(UserCreateRequest request);
    UserResponse update(Long id, UserUpdateRequest request);
    void delete(Long id);
}
```

```java
package com.example.demo.service.impl;

import com.example.demo.dto.*;
import com.example.demo.entity.User;
import com.example.demo.exception.NotFoundException;
import com.example.demo.repository.UserRepository;
import com.example.demo.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)  // 默认只读事务
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;

    @Override
    public List<UserResponse> listAll() {
        return userRepository.findAll()
            .stream()
            .map(this::toResponse)            // 方法引用，等价于 u -> toResponse(u)
            .collect(Collectors.toList());
    }

    @Override
    public UserResponse findById(Long id) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new NotFoundException("用户不存在，ID: " + id));
        return toResponse(user);
    }

    @Override
    @Transactional  // 写操作开启事务
    public UserResponse create(UserCreateRequest request) {
        // 检查邮箱是否已存在
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new BusinessException("邮箱已被注册");
        }

        User user = new User();
        user.setName(request.getName());
        user.setAge(request.getAge());
        user.setEmail(request.getEmail());

        User saved = userRepository.save(user);
        return toResponse(saved);
    }

    @Override
    @Transactional
    public UserResponse update(Long id, UserUpdateRequest request) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new NotFoundException("用户不存在，ID: " + id));

        // 只更新非 null 字段
        if (request.getName() != null) user.setName(request.getName());
        if (request.getAge() != null) user.setAge(request.getAge());
        if (request.getEmail() != null) user.setEmail(request.getEmail());

        User updated = userRepository.save(user);
        return toResponse(updated);
    }

    @Override
    @Transactional
    public void delete(Long id) {
        if (!userRepository.existsById(id)) {
            throw new NotFoundException("用户不存在，ID: " + id);
        }
        userRepository.deleteById(id);
    }

    // Entity → DTO 转换
    private UserResponse toResponse(User user) {
        return UserResponse.builder()
            .id(user.getId())
            .name(user.getName())
            .age(user.getAge())
            .email(user.getEmail())
            .createdAt(user.getCreatedAt())
            .build();
    }
}
```

### Repository（数据访问层）

```java
package com.example.demo.repository;

import com.example.demo.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    // Spring Data JPA 根据方法名自动生成 SQL！
    // 方法名规则：findBy + 字段名 + 条件

    Optional<User> findByEmail(String email);    // WHERE email = ?

    boolean existsByEmail(String email);         // SELECT COUNT(*) > 0 WHERE email = ?

    List<User> findByNameContaining(String keyword);  // WHERE name LIKE '%keyword%'

    List<User> findByAgeGreaterThan(int age);    // WHERE age > ?

    @Query("SELECT u FROM User u WHERE u.age BETWEEN :min AND :max")  // 自定义 JPQL
    List<User> findByAgeRange(@Param("min") int min, @Param("max") int max);
}
```

> **💡 前端类比**：Spring Data JPA 的 Repository 就像 Prisma Client——你定义接口，框架自动生成 SQL。

---

# 第五章：Spring Boot 启动全流程解密

## 5.1 启动入口

```java
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication  // 三合一注解（核心）
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);  // 启动！
    }
}
```

## 5.2 启动流程详解（9 大步骤）

```
SpringApplication.run() 启动流程：

┌────────────────────────────────────────────────────────────────┐
│ Step 1: 创建 SpringApplication 实例                              │
│ - 推断应用类型（SERVLET/REACTIVE/NONE）                           │
│ - 加载 ApplicationContextInitializer（上下文初始化器）             │
│ - 加载 ApplicationListener（事件监听器）                           │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 2: 准备环境（Environment）                                   │
│ - 读取 application.yml / application.properties                │
│ - 读取命令行参数、系统属性、环境变量                                  │
│ - 激活 profile（如 application-dev.yml）                        │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 3: 创建 ApplicationContext（Spring 容器）                    │
│ - 根据应用类型创建对应的 Context（AnnotationConfigServletWeb...）   │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 4: 准备 Context                                            │
│ - 设置 Environment                                             │
│ - 注册 BeanNameGenerator、ResourceLoader 等基础 Bean             │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 5: 刷新 Context（refresh() —— 最核心的步骤！）                │
│ 5.1 准备刷新：初始化 PropertySources、校验 required 属性           │
│ 5.2 获取 BeanFactory：创建 DefaultListableBeanFactory            │
│ 5.3 准备 BeanFactory：设置 ClassLoader、添加 BeanPostProcessor    │
│ 5.4 注册 BeanPostProcessor：后置处理器（AOP 的基础）               │
│ 5.5 初始化 MessageSource：国际化资源                               │
│ 5.6 初始化事件广播器：ApplicationEventMulticaster                  │
│ 5.7 注册 Listeners：事件监听器                                     │
│ 5.8 完成 BeanFactory 初始化                                       │
│     └── 这一步骤会扫描所有 @Component/@Service/@Controller 等     │
│     └── 创建所有单例 Bean（非懒加载的）                             │
│     └── 执行依赖注入（@Autowired）                                  │
│ 5.9 完成刷新：启动内嵌 Web 服务器（Tomcat/Jetty）                    │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 6: 启动内嵌 Tomcat                                          │
│ - 创建 Tomcat 实例                                               │
│ - 注册 DispatcherServlet（前端控制器）                             │
│ - 绑定端口（默认 8080）                                           │
│ - 开始监听 HTTP 请求                                              │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 7: 调用所有 CommandLineRunner / ApplicationRunner            │
│ - 可以用来执行启动后的初始化任务（如预加载数据）                       │
└───────────────────────────┬────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Step 8: 发布 ApplicationReadyEvent（应用就绪事件）                 │
│ - 所有监听器收到通知，应用可以接收请求了                              │
│ - 控制台输出：Started DemoApplication in X seconds               │
└────────────────────────────────────────────────────────────────┘
```

## 5.3 启动日志解读

当你看到以下日志时，说明各个组件已经成功启动：

```
  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/
 :: Spring Boot ::               (v3.2.0)    ← 版本号

2026-09-01T10:00:00.000+08:00  INFO 12345 --- [main] com.example.demo.DemoApplication : Starting DemoApplication...
2026-09-01T10:00:01.000+08:00  INFO 12345 --- [main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat started on port 8080  ← 服务启动
2026-09-01T10:00:02.000+08:00  INFO 12345 --- [main] com.example.demo.DemoApplication : Started DemoApplication in 2.5 seconds  ← 启动耗时
```

---

# 第六章：实战案例——从零搭建一个用户管理 API

## 6.1 案例目标

搭建一个完整的用户管理 REST API，包含 CRUD 操作、参数校验、统一异常处理、统一的响应格式。

## 6.2 第一步：创建项目

使用 Spring Initializr（https://start.spring.io/）创建项目，选择以下依赖：
- Spring Web
- Spring Data JPA
- H2 Database（内存数据库，方便演示）
- Lombok
- Validation

## 6.3 完整代码

### 6.3.1 统一响应格式

```java
package com.example.demo.dto;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {
    private int code;        // 状态码
    private String message;  // 提示信息
    private T data;          // 数据

    // 成功响应
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(200, "success", data);
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(200, message, data);
    }

    // 失败响应
    public static <T> ApiResponse<T> error(int code, String message) {
        return new ApiResponse<>(code, message, null);
    }
}
```

### 6.3.2 自定义异常

```java
package com.example.demo.exception;

// 业务异常
public class BusinessException extends RuntimeException {
    private final int code;

    public BusinessException(String message) {
        super(message);
        this.code = 400;
    }

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }

    public int getCode() { return code; }
}
```

```java
package com.example.demo.exception;

// 资源不存在异常
public class NotFoundException extends RuntimeException {
    public NotFoundException(String message) {
        super(message);
    }
}
```

### 6.3.3 全局异常处理器

```java
package com.example.demo.exception;

import com.example.demo.dto.ApiResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice  // 全局拦截所有 Controller 的异常
public class GlobalExceptionHandler {

    // 处理参数校验失败
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Map<String, String>>> handleValidation(
            MethodArgumentNotValidException ex) {
        Map<String, String> errors = new HashMap<>();
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            errors.put(error.getField(), error.getDefaultMessage());
        }
        return ResponseEntity.badRequest()
            .body(ApiResponse.error(400, "参数校验失败"));
    }

    // 处理业务异常
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<Void>> handleBusiness(BusinessException ex) {
        return ResponseEntity.badRequest()
            .body(ApiResponse.error(ex.getCode(), ex.getMessage()));
    }

    // 处理资源不存在
    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleNotFound(NotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(ApiResponse.error(404, ex.getMessage()));
    }

    // 处理所有未捕获的异常
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleAll(Exception ex) {
        ex.printStackTrace();  // 打印堆栈，方便排查
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ApiResponse.error(500, "服务器内部错误：" + ex.getMessage()));
    }
}
```

### 6.3.4 配置 application.yml

```yaml
server:
  port: 8080

spring:
  # H2 内存数据库（无需安装，启动即用）
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
    username: sa
    password:

  # H2 控制台（可通过浏览器访问 http://localhost:8080/h2-console）
  h2:
    console:
      enabled: true

  # JPA 配置
  jpa:
    hibernate:
      ddl-auto: update
    show-sql: true
    properties:
      hibernate:
        format_sql: true  # 格式化 SQL 输出
```

### 6.3.5 测试运行

启动应用后，用 curl 或 Postman 测试：

```bash
# 创建用户
curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","age":25,"email":"zhang@test.com"}'

# 响应：
# {"code":200,"message":"success","data":{"id":1,"name":"张三","age":25,"email":"zhang@test.com","createdAt":"2026-09-01T10:00:00"}}

# 获取所有用户
curl http://localhost:8080/api/users

# 获取单个用户
curl http://localhost:8080/api/users/1

# 更新用户
curl -X PUT http://localhost:8080/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"张三丰"}'

# 删除用户
curl -X DELETE http://localhost:8080/api/users/1

# 测试参数校验
curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"","age":-1,"email":"invalid"}'

# 响应：
# {"code":400,"message":"参数校验失败","data":null}
```

---

# 第七章：实战案例——Bug 排查全流程

## 7.1 常见 Bug 类型与排查思路

```
Bug 排查的总原则：从现象出发，沿着请求链路逐层排查，缩小范围。

排查顺序：
1. 看日志（控制台/日志文件）
2. 确定出错的层（Controller? Service? Repository? DB?）
3. 用断点/日志定位具体代码行
4. 分析原因，修复
5. 验证修复
```

## 7.2 案例一：500 错误——空指针异常（NullPointerException）

**现象**：调用 `GET /api/users/999` 返回 500 错误。

**浏览器/Postman 看到的响应**：
```json
{
    "code": 500,
    "message": "服务器内部错误：Cannot invoke \"...\" because \"user\" is null"
}
```

**控制台日志**：
```
java.lang.NullPointerException: Cannot invoke "com.example.demo.entity.User.getName()" because "user" is null
    at com.example.demo.service.impl.UserServiceImpl.findById(UserServiceImpl.java:25)
    at com.example.demo.controller.UserController.getUser(UserController.java:30)
    ...
```

**排查步骤**：

```
Step 1: 看堆栈信息
    at UserServiceImpl.findById(UserServiceImpl.java:25)  ← 错误发生在这里
    at UserController.getUser(UserController.java:30)     ← 从这里调用的

Step 2: 打开 UserServiceImpl.java，找到第 25 行
    public UserResponse findById(Long id) {
        User user = userRepository.findById(id).orElse(null);  // 查不到返回 null
        return toResponse(user);  // 第 25 行，这里 user 是 null！
    }

Step 3: 分析原因
    - ID 为 999 的用户不存在
    - findById 返回 Optional.empty()
    - .orElse(null) 返回了 null
    - toResponse(null) 内部调用了 null.getName() → NullPointerException

Step 4: 修复
    public UserResponse findById(Long id) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new NotFoundException("用户不存在，ID: " + id));
        return toResponse(user);  // user 一定不为 null
    }
```

**修复后响应**：
```json
{
    "code": 404,
    "message": "用户不存在，ID: 999",
    "data": null
}
```

## 7.3 案例二：400 错误——参数校验失败

**现象**：前端传了空的 name，收到 400 错误，但前端说"没看到我写的校验逻辑"。

**排查步骤**：

```
Step 1: 看请求参数
    POST /api/users  Body: {"name": "", "age": 25, "email": "test@test.com"}

Step 2: 看 Controller 方法签名
    @PostMapping
    public ResponseEntity<ApiResponse<UserResponse>> createUser(
            @Valid @RequestBody UserCreateRequest request) {  ← @Valid 注解
        ...
    }

Step 3: 看 DTO 类
    @Data
    public class UserCreateRequest {
        @NotBlank(message = "姓名不能为空")  ← 校验注解在这里！
        private String name;
        ...
    }

Step 4: 看全局异常处理器
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Map<String, String>>> handleValidation(...) {
        ...
    }

结论：校验逻辑在 DTO 的 @NotBlank/@Email/@Min 等注解上，由 @Valid 触发，
     校验失败后抛出 MethodArgumentNotValidException，由全局异常处理器统一处理。
```

## 7.4 案例三：数据库连接失败

**现象**：启动应用时报错，无法启动。

**控制台日志**：
```
com.mysql.cj.jdbc.exceptions.CommunicationsException: Communications link failure
```

**排查步骤**：

```
Step 1: 看日志关键词
    "Communications link failure" = 连不上数据库

Step 2: 检查 application.yml
    spring:
      datasource:
        url: jdbc:mysql://localhost:3306/mydb
        username: root
        password: 123456

Step 3: 依次检查
    □ MySQL 服务是否启动？  → net start mysql 或 检查服务
    □ 端口是否正确？       → 默认 3306
    □ 数据库 mydb 是否存在？ → mysql -u root -p 登录后 SHOW DATABASES;
    □ 用户名密码是否正确？   → 尝试用命令行连接
    □ 防火墙是否拦截？      → 检查 3306 端口
    □ 网络是否通？         → ping localhost
```

## 7.5 案例四：请求 404——接口没生效

**现象**：明明写了 Controller，但访问返回 404。

**排查步骤**：

```
Step 1: 确认 Controller 注解
    @RestController  ← 必须有
    @RequestMapping("/api/users")  ← 路径前缀
    public class UserController {

Step 2: 确认方法注解
    @GetMapping("/{id}")  ← GET + 路径
    public ... getUser(...) { ... }

Step 3: 确认完整路径
    @RequestMapping("/api/users") + @GetMapping("/{id}") = GET /api/users/{id}

Step 4: 确认启动类位置（最常见的坑！）
    @SpringBootApplication 所在的类必须在所有其他类的父包中！

    ✅ 正确：
    com.example.demo.DemoApplication          ← 启动类
    com.example.demo.controller.UserController ← 子包
    com.example.demo.service.UserServiceImpl   ← 子包

    ❌ 错误：
    com.example.demo.controller.DemoApplication ← 启动类在 controller 包下
    com.example.demo.service.UserServiceImpl    ← 其他包不在子包内
    → 扫描不到 controller 包外的类！

Step 5: 确认端口
    server.port: 8080
    访问 http://localhost:8080/api/users/1
    → 如果端口配了 8081，用 8080 访问当然 404
```

## 7.6 调试技巧总结

### 技巧一：用 IDEA 断点调试

```
1. 在可疑代码行左侧点击，设置红色断点
2. 以 Debug 模式启动应用（点击虫子图标）
3. 发送请求触发断点
4. 程序暂停在断点处，可以查看：
   - 所有变量的当前值（Variables 面板）
   - 调用栈（Frames 面板，可以看到谁调用了这个方法）
   - 表达式求值（Alt+F8，输入表达式看结果）
5. 按 F8 单步执行，F9 继续执行
```

### 技巧二：条件断点

```
在断点上右键 → 输入条件，如：
    id == 999  → 只有当 id=999 时才暂停
    user == null → 只有当 user 为 null 时才暂停
```

### 技巧三：日志大法

```java
// 在关键位置加日志
@Slf4j  // Lombok 日志注解
@Service
public class UserServiceImpl implements UserService {

    public UserResponse findById(Long id) {
        log.info("查询用户，ID: {}", id);           // 入参日志
        User user = userRepository.findById(id)
            .orElseThrow(() -> {
                log.error("用户不存在，ID: {}", id); // 错误日志
                return new NotFoundException("用户不存在");
            });
        log.debug("查询结果：{}", user);              // 结果日志（debug 级别）
        return toResponse(user);
    }
}
```

### 技巧四：Actuator 健康检查

```xml
<!-- pom.xml 添加依赖 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health,info,beans,env,mappings
```

```bash
# 检查应用是否存活
curl http://localhost:8080/actuator/health
# {"status":"UP"}

# 查看所有 Bean
curl http://localhost:8080/actuator/beans

# 查看所有 URL 映射
curl http://localhost:8080/actuator/mappings
```

---

# 第八章：常见业务场景代码模板

## 8.1 分页查询

```java
// Controller
@GetMapping
public ResponseEntity<Page<UserResponse>> listUsers(
        @RequestParam(defaultValue = "0") int page,     // 页码，从 0 开始
        @RequestParam(defaultValue = "10") int size,    // 每页大小
        @RequestParam(required = false) String keyword) {  // 可选搜索关键词
    Pageable pageable = PageRequest.of(page, size, Sort.by("id").descending());
    return ResponseEntity.ok(userService.listByPage(pageable, keyword));
}

// Service
public Page<UserResponse> listByPage(Pageable pageable, String keyword) {
    Page<User> userPage;
    if (StringUtils.hasText(keyword)) {
        userPage = userRepository.findByNameContaining(keyword, pageable);
    } else {
        userPage = userRepository.findAll(pageable);
    }
    return userPage.map(this::toResponse);
}
```

## 8.2 文件上传

```java
// Controller
@PostMapping("/upload")
public ResponseEntity<ApiResponse<String>> uploadFile(
        @RequestParam("file") MultipartFile file) {
    if (file.isEmpty()) {
        return ResponseEntity.badRequest()
            .body(ApiResponse.error(400, "文件不能为空"));
    }

    // 文件大小限制
    if (file.getSize() > 10 * 1024 * 1024) {  // 10MB
        return ResponseEntity.badRequest()
            .body(ApiResponse.error(400, "文件大小不能超过 10MB"));
    }

    String url = fileService.upload(file);
    return ResponseEntity.ok(ApiResponse.success("上传成功", url));
}

// Service
@Service
public class FileService {

    @Value("${file.upload-dir}")  // 从配置读取上传目录
    private String uploadDir;

    public String upload(MultipartFile file) {
        try {
            // 生成唯一文件名
            String originalName = file.getOriginalFilename();
            String extension = originalName.substring(originalName.lastIndexOf("."));
            String newFileName = UUID.randomUUID().toString() + extension;

            // 保存文件
            Path filePath = Paths.get(uploadDir, newFileName);
            Files.createDirectories(filePath.getParent());
            file.transferTo(filePath.toFile());

            return "/uploads/" + newFileName;
        } catch (IOException e) {
            throw new BusinessException("文件上传失败：" + e.getMessage());
        }
    }
}
```

## 8.3 JWT 登录认证

```java
// 登录请求
@Data
public class LoginRequest {
    @NotBlank
    private String username;
    @NotBlank
    private String password;
}

// 登录响应
@Data
@Builder
public class LoginResponse {
    private String token;
    private String username;
}

// Controller
@PostMapping("/login")
public ResponseEntity<ApiResponse<LoginResponse>> login(
        @Valid @RequestBody LoginRequest request) {
    LoginResponse response = authService.login(request);
    return ResponseEntity.ok(ApiResponse.success(response));
}

// Service
@Service
@RequiredArgsConstructor
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public LoginResponse login(LoginRequest request) {
        // 1. 查找用户
        User user = userRepository.findByUsername(request.getUsername())
            .orElseThrow(() -> new BusinessException("用户名或密码错误"));

        // 2. 校验密码
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException("用户名或密码错误");
        }

        // 3. 生成 JWT
        String token = jwtUtil.generateToken(user.getId(), user.getUsername());

        return LoginResponse.builder()
            .token(token)
            .username(user.getUsername())
            .build();
    }
}
```

## 8.4 拦截器实现权限校验

```java
// 定义拦截器
@Component
public class AuthInterceptor implements HandlerInterceptor {

    private final JwtUtil jwtUtil;

    public AuthInterceptor(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) {
        // 从请求头获取 Token
        String token = request.getHeader("Authorization");
        if (token == null || !token.startsWith("Bearer ")) {
            response.setStatus(401);
            return false;  // 拦截请求
        }

        token = token.substring(7);  // 去掉 "Bearer " 前缀

        try {
            // 解析 Token
            Long userId = jwtUtil.getUserIdFromToken(token);
            request.setAttribute("userId", userId);  // 传递给 Controller
            return true;  // 放行
        } catch (Exception e) {
            response.setStatus(401);
            return false;
        }
    }
}

// 注册拦截器
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final AuthInterceptor authInterceptor;

    public WebConfig(AuthInterceptor authInterceptor) {
        this.authInterceptor = authInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor)
            .addPathPatterns("/api/**")         // 拦截所有 /api 路径
            .excludePathPatterns("/api/auth/**"); // 排除登录接口
    }
}
```

## 8.5 定时任务

```java
@Component
@Slf4j
public class ScheduledTasks {

    @Scheduled(fixedRate = 60000)  // 每 60 秒执行一次
    public void cleanExpiredSessions() {
        log.info("开始清理过期会话...");
        // ... 清理逻辑
    }

    @Scheduled(cron = "0 0 2 * * ?")  // 每天凌晨 2 点执行
    public void dailyReport() {
        log.info("生成每日报表...");
        // ... 报表逻辑
    }
}

// 启动类上加 @EnableScheduling
@SpringBootApplication
@EnableScheduling
public class DemoApplication { ... }
```

---

# 第九章：常用工具与调试技巧

## 9.1 Lombok 常用注解速查

Lombok 是 Java 开发中几乎必用的工具，通过注解自动生成样板代码。

| 注解 | 作用 | 生成的代码 |
|---|---|---|
| `@Data` | 综合注解 | getter + setter + toString + equals + hashCode |
| `@Getter` | 生成 getter | 所有字段的 get 方法 |
| `@Setter` | 生成 setter | 所有字段的 set 方法 |
| `@NoArgsConstructor` | 无参构造器 | `public User() {}` |
| `@AllArgsConstructor` | 全参构造器 | `public User(Long id, String name, ...) {}` |
| `@RequiredArgsConstructor` | 必要字段构造器 | 包含 final 和 @NonNull 字段的构造器 |
| `@Builder` | 建造者模式 | `User.builder().name("张三").age(25).build()` |
| `@Slf4j` | 日志 | `private static final Logger log = ...` |
| `@ToString` | toString 方法 | 打印所有字段的字符串 |

## 9.2 IDEA 快捷键（排查问题必备）

| 操作 | Windows/Linux | Mac |
|---|---|---|
| 查找类 | Ctrl+N | Cmd+O |
| 查找文件 | Ctrl+Shift+N | Cmd+Shift+O |
| 查找符号（方法/字段） | Ctrl+Alt+Shift+N | Cmd+Alt+O |
| 跳转到定义 | Ctrl+B | Cmd+B |
| 查找所有引用 | Alt+F7 | Alt+F7 |
| 查看类层级 | Ctrl+H | Ctrl+H |
| 查找 Controller 的 URL 映射 | Ctrl+Shift+F 搜索 `@GetMapping` 等 | |
| 全局搜索 | Ctrl+Shift+F | Cmd+Shift+F |
| 运行 | Shift+F10 | Ctrl+R |
| Debug | Shift+F9 | Ctrl+D |
| 单步执行 | F8 | F8 |
| 进入方法 | F7 | F7 |
| 继续执行 | F9 | F9 |
| 表达式求值 | Alt+F8 | Alt+F8 |

## 9.3 常用 Maven 命令

```bash
# 编译项目
mvn compile

# 运行测试
mvn test

# 打包（生成 jar 文件）
mvn clean package -DskipTests

# 运行 Spring Boot 应用
mvn spring-boot:run

# 查看依赖树（排查依赖冲突）
mvn dependency:tree

# 强制更新依赖
mvn clean install -U
```

## 9.4 数据库调试

```yaml
# application.yml 中开启 SQL 日志
spring:
  jpa:
    show-sql: true              # 控制台打印 SQL
    properties:
      hibernate:
        format_sql: true        # 格式化 SQL
        use_sql_comments: true  # 添加注释（方便定位是哪个方法生成的 SQL）

logging:
  level:
    org.hibernate.SQL: DEBUG              # SQL 日志
    org.hibernate.type.descriptor.sql: TRACE  # 参数绑定日志（可以看到 ? 的值）
```

---

# 第十章：学习资源与进阶路线

## 10.1 快速上手路线（3 天计划）

| 时间 | 学习内容 | 目标 |
|---|---|---|
| **第1天** | 第一章 Java 基础速览 + 第二章 Spring Boot 核心概念 | 能看懂 Java 代码，理解 Controller/Service/Repository 分层 |
| **第2天** | 第三章 项目结构 + 第四章 请求处理流程 + 第六章 实战案例 | 理解整个请求链路，能跟着案例写简单接口 |
| **第3天** | 第七章 Bug 排查 + 第九章 调试技巧 | 能独立排查常见 Bug，会用 IDEA 断点调试 |

## 10.2 日常改代码检查清单

当你接到一个需求要改代码时，按这个清单操作：

```
□ 1. 找到对应的 Controller（搜 URL 路径）
□ 2. 看 Controller 调用了哪个 Service
□ 3. 看 Service 的实现逻辑
□ 4. 看涉及哪些 Entity（数据表结构）
□ 5. 看涉及哪些 Repository（SQL 查询）
□ 6. 修改代码（先理解再动手）
□ 7. 用 Postman/curl 测试修改后的接口
□ 8. 看控制台日志，确认 SQL 正确
□ 9. 检查边界情况（空值、不存在、重复等）
```

## 10.3 进阶学习资源

| 主题 | 推荐资源 |
|---|---|
| Spring Security | 认证和授权框架，企业项目必备 |
| MyBatis / MyBatis-Plus | 国内最流行的 SQL 映射框架（比 JPA 更灵活） |
| Redis | 缓存、分布式锁、Session 共享 |
| Spring Cloud | 微服务框架（服务注册、配置中心、网关） |
| Docker | 容器化部署 |
| 设计模式 | 单例、工厂、代理、策略等在 Spring 中的应用 |

## 10.4 快速查阅网站

- Spring Boot 官方文档：https://docs.spring.io/spring-boot/docs/current/reference/html/
- Spring Data JPA 查询方法规则：https://docs.spring.io/spring-data/jpa/docs/current/reference/html/#jpa.query-methods
- Lombok 注解大全：https://projectlombok.org/features/
- Baeldung（最佳 Spring 教程站）：https://www.baeldung.com/

---

## 📋 附录：前端开发者的 Java 避坑指南

| 坑 | 说明 | 正确做法 |
|---|---|---|
| `==` vs `equals()` | 对于 String 等引用类型，`==` 比较地址，`equals()` 比较内容 | 字符串比较用 `"abc".equals(str)` |
| null 无处不在 | 任何引用类型都可能为 null | 善用 Optional，或加 null 判断 |
| 基本类型 vs 包装类型 | `int` 不能为 null，`Integer` 可以为 null | 数据库查询结果用包装类型 |
| Lombok 依赖 | 项目使用了 Lombok 但 IDE 没装插件 | 安装 Lombok 插件 + 开启注解处理 |
| 方法名自动 SQL | JPA 根据方法名生成 SQL，写错会报错 | 参考 Spring Data JPA 文档的方法命名规则 |
| application.yml 缩进 | YAML 对缩进敏感，空格不能是 Tab | IDEA 会自动识别，用空格缩进 |
| @Transactional 失效 | 同类方法调用时事务不生效 | 事务方法放在不同类中，或注入自己调用 |
| 启动类位置 | 启动类必须在根包下 | 保持 `com.example.demo` 在根，其他在子包 |
| Bean 重复定义 | 两个类实现了同一个接口，Spring 不知道该注入哪个 | 用 `@Primary` 或 `@Qualifier` 指定 |
| 循环依赖 | A 依赖 B，B 又依赖 A，导致启动失败 | 用 `@Lazy` 或重构代码打破循环 |

---

> 📝 **最后的话**：Java 和 Spring Boot 是一个庞大的生态，不要试图一次性全部掌握。作为前端开发者，你的目标是**能看懂代码结构、能改业务逻辑、能排查常见 Bug**。遇到不懂的注解或类，用 IDEA 的 `Ctrl+点击` 跳转进去看看源码，或者搜索注解名 + "Spring Boot" 来查文档。在实践中学习是最快的。