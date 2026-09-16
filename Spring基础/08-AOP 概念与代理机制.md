# AOP 概念与代理机制

前七篇学完了 IoC 和 DI——Spring 的"正骨"。从本篇开始进入 Spring 的第二大核心：**AOP（面向切面编程）**。如果说 IoC 管"对象的创建和装配"，AOP 就管"横切逻辑的统一管理"——日志、事务、权限、缓存，这些散布在几十个方法中的重复代码，AOP 一次性收拢。

> 💡 本篇专注 AOP 的核心概念和底层代理机制。学完这篇你就知道：为什么 `@Transactional` 内部调用会失效、为什么 `final` 方法不能被代理、为什么 Spring Boot 默认用 CGLIB 而不是 JDK 代理。

---

## 一、AOP 要解决什么问题

### 1.1 横切逻辑的痛点

```java
// ❌ 没有 AOP：横切代码散落在每个方法里
public void createOrder(Order order) {
    log.info("createOrder 开始, 参数: {}", order);     // ← 日志
    SecurityUtils.checkPermission("order:create");     // ← 权限
    try {
        orderDao.save(order);                          // ← 业务
        log.info("createOrder 成功");                  // ← 日志
    } catch (Exception e) {
        log.error("createOrder 失败", e);              // ← 日志
        throw e;
    }
}

public void cancelOrder(Long orderId) {
    log.info("cancelOrder 开始, 参数: {}", orderId);   // ← 一模一样的日志
    SecurityUtils.checkPermission("order:cancel");     // ← 一模一样的权限
    try {
        orderDao.updateStatus(orderId, "CANCELLED");   // ← 业务
        log.info("cancelOrder 成功");                  // ← 一模一样的日志
    } catch (Exception e) {
        log.error("cancelOrder 失败", e);              // ← 一模一样的日志
        throw e;
    }
}
```

**问题**：
- 日志、权限、事务代码在每个方法中重复出现
- 改一处日志格式 → 所有方法都要改
- 业务代码和横切代码混在一起，可读性差

### 1.2 AOP 的解决思路

```
┌───────────────────────────────────────────────────┐
│                    AOP 思想                        │
│                                                   │
│   把"横切逻辑"（日志/权限/事务）                    │
│   从"核心业务"中抽离出来                            │
│   用"切面"统一管理                                  │
│   在运行时动态"织入"到目标方法                       │
│                                                   │
│   createOrder()  ──▶  [日志切面] ──▶  orderDao.save()
│                         [权限切面]                  │
│                         [事务切面]                  │
│                                                   │
│   cancelOrder()  ──▶  同样的切面   ──▶  orderDao.update()
│                                                   │
│   业务方法只写业务，横切逻辑交给切面                  │
└───────────────────────────────────────────────────┘
```

```java
// ✅ 有 AOP：业务方法只写业务
@CheckPermission("order:create")   // 权限 → 切面搞定
public void createOrder(Order order) {
    orderDao.save(order);           // 只有业务
}

@CheckPermission("order:cancel")
public void cancelOrder(Long orderId) {
    orderDao.updateStatus(orderId, "CANCELLED");
}
// 日志、权限、事务全部由切面自动处理，业务方法清爽了
```

---

## 二、AOP 核心概念

### 2.1 五个核心术语

| 术语 | 英文 | 含义 | 生活类比 |
| :--- | :--- | :--- | :--- |
| **切面** | Aspect | 横切逻辑的封装体 = 切点 + 通知 | "日志模块" |
| **切点** | Pointcut | 在哪些方法上织入 | "哪些方法要记录日志" |
| **通知** | Advice | 在什么时机、干什么事 | "执行前记录参数" |
| **连接点** | JoinPoint | 程序执行中能插入切面的点（方法调用） | "每个方法都是一个可能的插入点" |
| **织入** | Weaving | 把切面代码加到目标方法上的过程 | "把日志代码'缝'到业务方法上" |

**它们的关系**：

```
切面（Aspect）
    │
    ├── 切点（Pointcut）── 告诉 Spring "在哪儿切"
    │     execution(* com.example.service.*.*(..))
    │                        ↑
    │               service 包下所有类的所有方法
    │
    └── 通知（Advice）── 告诉 Spring "切了以后干什么"
          @Before   → 执行前
          @After    → 执行后（无论成功还是异常）
          @Around   → 环绕（最强大，包裹整个方法）
          @AfterReturning → 成功返回后
          @AfterThrowing  → 抛出异常后
```

### 2.2 一张图看懂切面执行流程

```
方法调用
    │
    ▼
  ┌─────────────────────────────────────────┐
    @Around 开始（环绕通知，可以决定是否继续）
    │
    ▼
  ┌─────────────────────────────────────────┐
    @Before（前置通知）
    │
    ▼
  ┌─────────────────────────────────────────┐
    目标方法执行
    │
    ├── 正常返回 ──▶ @AfterReturning
    │
    ├── 抛异常     ──▶ @AfterThrowing
    │
    └── @Around 结束
    │
    ▼
  ┌─────────────────────────────────────────┐
    @After（最终通知，类似 finally）
  ┌─────────────────────────────────────────┐
    @Around 结束
```

---

## 三、AOP 的底层代理机制 ⭐⭐

Spring AOP **不是修改了你的 class 文件**，而是在运行时**生成一个代理对象**来包裹你的原始对象。

### 3.1 两种代理方式

| | JDK 动态代理 | CGLIB 代理 |
| :--- | :--- | :--- |
| **原理** | 基于接口：生成实现相同接口的代理类 | 基于继承：生成目标类的子类 |
| **要求** | 目标类必须**实现接口** | 目标类**不能是 final** |
| **代理对象类型** | 接口类型（`$ProxyXX`） | 目标类的子类（`Target$$EnhancerBySpringCGLIB$$XX`） |
| **调用方式** | `Proxy.newProxyInstance()` + `InvocationHandler` | `Enhancer.create()` + `MethodInterceptor` |
| **Spring 历史默认** | Spring 早期默认（代理接口） | Spring Boot **默认** |
| **性能** | 反射调用（略慢） | 直接继承调用（略快） |

### 3.2 JDK 动态代理

```java
// 1. 接口（JDK 代理的前置条件）
public interface UserService {
    void save(User user);
}

// 2. 实现类
public class UserServiceImpl implements UserService {
    @Override
    public void save(User user) {
        System.out.println("保存用户：" + user.getName());
    }
}

// 3. JDK 代理
public class JdkProxyDemo {
    public static void main(String[] args) {
        // 原始对象
        UserService target = new UserServiceImpl();

        // 生成代理对象
        UserService proxy = (UserService) Proxy.newProxyInstance(
                target.getClass().getClassLoader(),
                target.getClass().getInterfaces(),    // ← 必须基于接口
                new InvocationHandler() {
                    @Override
                    public Object invoke(Object proxy, Method method, Object[] args)
                            throws Throwable {
                        System.out.println(">> 前置日志：调用 " + method.getName());
                        Object result = method.invoke(target, args);  // 调原始对象
                        System.out.println(">> 后置日志：" + method.getName() + " 完成");
                        return result;
                    }
                });

        proxy.save(new User("张三", "123456"));
        // 输出：
        // >> 前置日志：调用 save
        // 保存用户：张三
        // >> 后置日志：save 完成
    }
}
```

### 3.3 CGLIB 代理

```java
// 1. 目标类（不需要接口！）
public class ProductService {
    public void save(Product product) {
        System.out.println("保存商品：" + product.getName());
    }
}

// 2. CGLIB 代理
public class CglibProxyDemo {
    public static void main(String[] args) {
        Enhancer enhancer = new Enhancer();
        enhancer.setSuperclass(ProductService.class);  // ← 继承目标类
        enhancer.setCallback(new MethodInterceptor() {
            @Override
            public Object intercept(Object obj, Method method, Object[] args,
                                    MethodProxy proxy) throws Throwable {
                System.out.println(">> 前置日志：" + method.getName());
                Object result = proxy.invokeSuper(obj, args);  // 调父类方法
                System.out.println(">> 后置日志：" + method.getName() + " 完成");
                return result;
            }
        });

        ProductService proxy = (ProductService) enhancer.create();
        proxy.save(new Product("电脑", 5999.0));
        // 输出：
        // >> 前置日志：save
        // 保存商品：电脑
        // >> 后置日志：save 完成
    }
}
```

### 3.4 Spring Boot 的默认代理策略

Spring Boot 从 **2.0 开始默认使用 CGLIB 代理**。可以通过配置切换：

```properties
# 切换为 JDK 代理（要求目标类实现接口）
spring.aop.proxy-target-class=false
# 默认为 true，即 CGLIB 代理
```

**为什么 Spring Boot 选择 CGLIB？**

1. **不需要接口**：开发时不用为了 AOP 强行给每个 Service 加一个接口
2. **更直观**：`@Autowired UserServiceImpl` 能注入，不像 JDK 代理必须用接口类型注入
3. **Spring Boot 2.x 时代主要的争论点**（JDK 代理要求注入接口类型）不再存在

---

## 四、AOP 的三大局限 ⭐

这是开发中的常见坑，理解了代理机制自然就懂了。

### 4.1 内部调用失效

```java
@Service
public class OrderService {
    @Transactional
    public void createOrder(Order order) {
        orderDao.save(order);
        sendNotification(order);  // ← 类内部直接调用
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(Order order) {
        // 期望：这个方法在独立事务中执行
        notificationService.send(order);
    }
}
```

**问题**：`sendNotification` 的事务不会生效！**`REQUIRES_NEW` 等效于没写**。

**原因**：

```
外部调用 createOrder()
    → Spring 的代理对象.createOrder()
        → 代理打开事务
        → 调原始对象.createOrder()     ← 这里的 this 是原始对象！
            → this.sendNotification()   ← 直接调原始对象的方法，跳过了代理！
```

```
Spring 代理对象（CGLIB）
    ├── createOrder()           ✅ 经过代理 → 事务生效
    │       └── 调用 super.createOrder()（原始对象）
    │               └── this.sendNotification()  ← ❌ this 是原始对象，不经过代理！
    │
    └── sendNotification()      ✅ 只有从外部调才经过代理
```

**解决方案**：

```java
// 方案一：把自己注入进来，通过代理调自己
@Service
public class OrderService {
    @Autowired
    private OrderService self;  // 注入的是代理对象

    @Transactional
    public void createOrder(Order order) {
        orderDao.save(order);
        self.sendNotification(order);  // ← 通过代理调，事务生效
    }
}

// 方案二：拆成两个 Service
@Service
public class OrderService {
    @Autowired private NotificationService notificationService;

    @Transactional
    public void createOrder(Order order) {
        orderDao.save(order);
        notificationService.sendNotification(order);  // ← 调另一个 Bean，经过代理
    }
}
```

> 💡 方案二优于方案一。内部调用失效通常是"职责没分清楚"的信号——你加一个方法，内部又调另一个需要事务/缓存/异步的方法，说明这两个职责可能该拆到两个类中。

### 4.2 final 方法无法代理

```java
@Service
public class OrderService {
    @Transactional
    public final void createOrder(Order order) {  // ❌ final → CGLIB 不能重写
        orderDao.save(order);
    }
}
```

CGLIB 通过**继承**目标类来生成代理。`final` 方法无法被重写 → 代理失效 → `@Transactional` 不生效。

### 4.3 private 方法无法代理

```java
@Service
public class OrderService {
    @Transactional
    private void doSomething() { }  // ❌ private → 代理看不到这个方法
}
```

JDK 代理基于接口（接口没有 private 方法），CGLIB 基于继承（子类看不到父类的 private 方法）。private 方法上的 AOP 注解完全无效。

---

## 💻 实战案例

### 案例：手写"迷你 AOP"框架

```java
/**
 * 迷你 AOP 框架：用 JDK 代理实现 @Before 通知
 * 理解这段代码，你就懂了 Spring AOP 的骨架
 */
public class MiniAopFramework {

    // 自定义的 @Before 注解
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.METHOD)
    @interface Before {
        String value();  // 切点表达式（简化版：方法名）
    }

    // 切面类
    static class LogAspect {
        @Before("save")   // 在 save 方法执行前
        public void logBefore() {
            System.out.println(">>> [日志] 操作前记录");
        }
    }

    // AOP 工厂：为目标对象创建代理
    @SuppressWarnings("unchecked")
    public static <T> T createProxy(T target, Class<?> targetInterface,
                                     Object aspect) {
        // 1. 解析切面：找到所有 @Before 方法
        Map<String, Method> adviceMap = new HashMap<>();
        for (Method m : aspect.getClass().getDeclaredMethods()) {
            Before before = m.getAnnotation(Before.class);
            if (before != null) {
                adviceMap.put(before.value(), m);
            }
        }

        // 2. 创建代理
        return (T) Proxy.newProxyInstance(
                target.getClass().getClassLoader(),
                new Class[]{targetInterface},
                (proxy, method, args) -> {
                    // 3. 执行前置通知
                    Method adviceMethod = adviceMap.get(method.getName());
                    if (adviceMethod != null) {
                        adviceMethod.invoke(aspect);
                    }
                    // 4. 执行目标方法
                    return method.invoke(target, args);
                });
    }

    // 验证
    public static void main(String[] args) {
        UserService target = new UserServiceImpl();
        LogAspect aspect = new LogAspect();

        UserService proxy = createProxy(target, UserService.class, aspect);
        proxy.save(new User("张三", "123456"));
        // 输出：
        // >>> [日志] 操作前记录
        // 保存用户：张三
    }
}
```

---

## 🎯 面试高频

### Q1：Spring AOP 的底层实现是什么？

**答**：基于**动态代理**。Spring 根据目标类是否实现接口自动选择：

1. **JDK 动态代理**：如果目标类实现了接口，可以用 JDK 的 `Proxy.newProxyInstance()` + `InvocationHandler` 生成代理
2. **CGLIB 代理**：如果目标类没实现接口（或配置了 `proxy-target-class=true`），用 CGLIB 的 `Enhancer` 生成目标类的子类作为代理

Spring Boot 默认使用 CGLIB。

### Q2：为什么 @Transactional 内部调用不生效？

**答**：因为 AOP 是通过代理对象实现的。外部调用 `代理对象.method()` → 代理执行切面逻辑（打开事务）→ 调原始对象.method()。但在原始对象内部 `this.anotherMethod()` 时，`this` 是原始对象，不经过代理 → 切面逻辑（事务）不生效。

解决：通过 `@Autowired` 注入自身的代理对象，或者拆成两个 Service。

---

## 📌 在 Spring Boot 中

- Spring Boot 默认使用 CGLIB 代理。这意味着：1）不需要接口就能 AOP；2）`final` 方法无法代理；3）内部调用不经过代理。
- `@Transactional`、`@Cacheable`、`@Async`、`@PreAuthorize` 全部是 AOP 实现的。它们都遵循同样的代理规则——内部调用失效、final 方法失效、private 方法失效。
- 如果遇到"加了 @Transactional 但不生效"，优先检查这三个原因：1）是不是类内部调用（最常见）；2）方法是 final；3）方法是 private。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| AOP 核心概念 | 切面=Aspect、切点=Pointcut、通知=Advice、织入=Weaving、连接点=JoinPoint |
| JDK 动态代理 | 基于接口，`Proxy.newProxyInstance()`，需要实现接口 |
| CGLIB 代理 | 基于继承，`Enhancer.create()`，不能代理 final 方法，Spring Boot 默认 |
| 内部调用失效 | 类内部 this.xxx() 不经过代理 → @Transactional 等注解不生效 |
| final 方法 | CGLIB 基于继承 → final 方法不能被重写 → 代理失效 |
| private 方法 | 无论 JDK 还是 CGLIB 都无法代理 private 方法 |

---

## 学习建议

1. **手写 JDK 和 CGLIB 两个代理 Demo**。不必背 API，但要知道两种代理的本质区别（接口 vs 继承）。面试时被问到"AOP 底层原理"，你能说"我手写过"——这句话本身就是加分项。
2. **亲手触发内部调用失效**。写一个 Service，两个方法都加 `@Transactional`，A 方法调 B 方法。在 B 方法中故意抛 RuntimeException，看 B 的事务回滚是否生效。再用"注入自己"的方式修复。
3. **下断点看代理对象**。在 `@Autowired` 注入的 Service 上打断点，Debug 模式下看对象的实际类型——会看到 `XXX$$EnhancerBySpringCGLIB$$xxxxx`，这就是代理对象。然后点进这个对象的父类，能看到原始对象的引用。