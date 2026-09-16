# 声明式事务 @Transactional

数据库操作最怕什么？不是 SQL 写错了，而是**一组操作只成功了一半**。A 扣了钱、B 没收到的场景，只能用事务来保证"要么全成功、要么全回滚"。Spring 把事务管理从"手写 try-catch-rollback"变成了一个 `@Transactional` 注解，但注解背后有很多坑——本篇把这些坑一个一个填平。

> 💡 `@Transactional` 是 Spring 最常用的注解之一，也是线上事故高发区。理解它的原理和失效场景，能帮你避开 80% 的事务 Bug。

---

## 一、事务回顾：为什么需要事务

### 1.1 事务的 ACID

| 特性 | 含义 | 生活类比 |
| :--- | :--- | :--- |
| **原子性（Atomicity）** | 一组操作不可分割，要么全做、要么全不做 | 转钱：扣款 + 收款，必须同时成功 |
| **一致性（Consistency）** | 事务前后，数据状态符合业务规则 | 转账前后，总金额不变 |
| **隔离性（Isolation）** | 并发事务互不干扰 | 多人同时转钱，不能互相影响 |
| **持久性（Durability）** | 事务提交后，数据永久保存 | 钱转完了，重启服务器也不能丢 |

### 1.2 没有事务的代码长什么样

```java
// ❌ 没有事务：中间抛出异常 → 扣了钱但没生成订单
public void createOrder(Order order) {
    accountDao.deduct(order.getUserId(), order.getAmount()); // 扣钱成功了
    // ... 此处系统崩了或抛异常
    orderDao.save(order);  // 订单没保存！
    // 结果：钱扣了，订单没生成 → 用户投诉
}
```

**传统 JDBC 事务处理**：

```java
Connection conn = null;
try {
    conn = dataSource.getConnection();
    conn.setAutoCommit(false);         // 手动开事务

    accountDao.deduct(conn, userId, amount);
    orderDao.save(conn, order);

    conn.commit();                     // 提交
} catch (Exception e) {
    if (conn != null) conn.rollback(); // 回滚
    throw e;
} finally {
    if (conn != null) conn.close();    // 关连接
}
```

每一个需要事务的方法都要写这 10 行模板代码——Spring 的 `@Transactional` 就是帮你省掉这些。

---

## 二、@Transactional 原理

### 2.1 本质是 AOP

`@Transactional` 是 Spring 声明式事务的核心注解。它的本质是 **AOP 的 `@Around` 通知**：

```
事务拦截器（TransactionInterceptor）：
    @Around
    ① 开启事务
    ② proceed() → 执行你的 @Transactional 方法
    ③ 正常返回 → 提交事务
    ④ 抛异常    → 回滚事务
```

### 2.2 基本使用

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder(Order order) {
        accountDao.deduct(order.getUserId(), order.getAmount());
        orderDao.save(order);         // 如果这行抛异常，上面扣的钱自动回滚
        orderItemDao.saveAll(order.getItems());
    }
    // 方法正常结束 → 提交
    // 方法抛 RuntimeException → 回滚
}
```

短短一行 `@Transactional`，等价于之前 10 行 JDBC 样板代码。

### 2.3 事务管理器

Spring 通过 `PlatformTransactionManager` 接口抽象了事务管理，不同数据访问技术有不同实现：

```java
PlatformTransactionManager（接口）
    ├── DataSourceTransactionManager   → JDBC / MyBatis 事务
    ├── JpaTransactionManager          → JPA 事务
    └── JtaTransactionManager          → 分布式事务（JTA）
```

```java
// @Transactional 可以指定使用哪个事务管理器
@Transactional(transactionManager = "jpaTransactionManager")
public void useJpaTransaction() { ... }
```

> 💡 Spring Boot 自动配置了 `DataSourceTransactionManager`，一般不需要手动指定。

---

## 三、回滚规则 ⭐⭐

### 3.1 默认回滚规则：只回滚 RuntimeException + Error

这是 `@Transactional` 最大的坑之一：

```java
@Transactional
public void createOrder(Order order) throws IOException {
    orderDao.save(order);
    throw new IOException("文件写入失败");  // ← 受检异常，默认不回滚！
}
// 结果：抛了异常，但数据还是写入数据库了！
```

**Spring 的回滚规则**：

| 异常类型 | 默认行为 | 父类 |
| :--- | :--- | :--- |
| `RuntimeException` | ✅ 回滚 | `Exception` |
| `Error` | ✅ 回滚 | `Throwable` |
| `Exception`（受检异常）| ❌ **不**回滚 | `Throwable` |
| 子类 | 继承父类行为 | — |

### 3.2 指定回滚异常

```java
// 方式一：让指定受检异常也回滚
@Transactional(rollbackFor = IOException.class)
public void createOrder(Order order) throws IOException {
    orderDao.save(order);
    throw new IOException("文件写入失败");  // 这次会回滚了！
}

// 方式二：让指定异常不回滚
@Transactional(noRollbackFor = IllegalArgumentException.class)
public void createOrder(Order order) {
    // 抛 IllegalArgumentException 不回滚
}

// 方式三：让所有异常都回滚（推荐做法）
@Transactional(rollbackFor = Exception.class)
public void createOrder(Order order) throws Exception {
    // 任何异常都回滚，最安全
}
```

> 💡 **生产建议**：如果你不确定哪些异常应该回滚，就用 `@Transactional(rollbackFor = Exception.class)`。宁可多回滚一次业务无关的异常，也别漏回滚一个数据相关的异常。

### 3.3 捕获异常后事务行为

```java
@Transactional
public void createOrder(Order order) {
    try {
        orderDao.save(order);
        throw new RuntimeException("模拟异常");
    } catch (Exception e) {
        log.error("捕获了异常", e);
        // ⚠️ 异常被 catch 吞掉了！方法正常返回 → 事务提交！
    }
}
// 结果：明明抛了异常，但数据被提交了！
```

> 💡 **原则**：`@Transactional` 方法内不要用 try-catch 吞掉异常。非要 catch 不可时，在 catch 块里手动设置回滚：

```java
@Transactional
public void createOrder(Order order) {
    try {
        remoteService.call();  // 调远程服务，失败不应影响主流程
    } catch (Exception e) {
        log.error("远程调用失败", e);
        // 方案一：手动标记回滚
        TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
        throw e; // 还是要抛出去让事务回滚
        // 方案二：如果确实不想回滚，只记录日志不抛异常即可
    }
    orderDao.save(order);
}
```

---

## 四、@Transactional 的失效场景 ⭐⭐

### 4.1 场景一：非 public 方法

```java
@Transactional
protected void saveOrder(Order order) { ... }  // ❌ protected，事务不生效

@Transactional
private void saveOrder(Order order) { ... }    // ❌ private，事务不生效
```

原因：Spring 的 AOP 基于代理，代理对象只能拦截 **public** 方法。如果是 CGLIB 代理，protected 和 package-private 方法理论上可以被拦截，但 Spring 默认只处理 public 方法。

### 4.2 场景二：同类内部调用

```java
@Service
public class OrderService {
    public void createOrder(Order order) {
        // ... 一些操作
        doSave(order);  // ← 直接调 this.doSave()，不是调代理对象！
    }

    @Transactional
    public void doSave(Order order) {
        orderDao.save(order);  // 事务不生效
    }
}
```

原因：`this` 是原始对象，不是代理对象。详见 [08-AOP 概念与代理机制](08-AOP%20概念与代理机制.md) 第四章。

### 4.3 场景三：异常被捕获

```java
@Transactional
public void createOrder(Order order) {
    try {
        orderDao.save(order);
        throw new RuntimeException();  // 异常被下面的 catch 吞了
    } catch (Exception e) {
        log.error("出错", e);  // 没有继续抛！事务不会回滚！
    }
}
```

### 4.4 场景四：rollbackFor 配置不当

```java
@Transactional  // 默认不回滚受检异常
public void importData(InputStream in) throws IOException {
    parseData(in);        // 抛 IOException
    orderDao.saveAll(list);  // 这行没有执行
    // 但前面可能有部分写入操作，因为受检异常默认不回滚
}
```

### 4.5 场景五：数据库引擎不支持事务

```sql
CREATE TABLE orders (
    ...
) ENGINE=MyISAM;  -- ❌ MyISAM 不支持事务！@Transactional 形同虚设！
```

必须用 InnoDB 引擎。

### 4.6 场景六：多线程环境

```java
@Transactional
public void batchProcess(List<Order> orders) {
    orders.parallelStream().forEach(order -> {
        orderDao.save(order);  // ❌ 子线程不在当前事务中！
    });
}
```

事务通过 `ThreadLocal` 绑定到当前线程，`parallelStream` 用的线程池里的线程拿不到这个事务上下文。

---

## 💻 实战案例

### 案例：转账操作的事务处理

```java
@Service
@RequiredArgsConstructor
public class TransferService {
    private final AccountDao accountDao;
    private final TransferLogDao transferLogDao;

    @Transactional(rollbackFor = Exception.class)
    public void transfer(Long fromId, Long toId, BigDecimal amount) {
        // 1. 扣款
        Account from = accountDao.findById(fromId);
        if (from.getBalance().compareTo(amount) < 0) {
            throw new BusinessException("余额不足");
        }
        accountDao.deduct(fromId, amount);

        // 2. 收款（如果这里抛异常，上面的扣款自动回滚）
        Account to = accountDao.findById(toId);
        if (to == null) {
            throw new BusinessException("对方账户不存在");
        }
        accountDao.addBalance(toId, amount);

        // 3. 记录转账日志
        TransferLog log = new TransferLog(fromId, toId, amount, LocalDateTime.now());
        transferLogDao.save(log);
    }
    // 三个操作要么全成功，要么全回滚
}
```

> 💡 把 `rollbackFor = Exception.class` 作为好习惯：默认的"只回滚 RuntimeException"太容易出事故了。你团队里大部分人可能不知道受检异常不会回滚这个规则。

---

## 🎯 面试高频

### Q1：@Transactional 失效的场景有哪些？

**答**：
1. 注解加在非 public 方法上
2. 同类内部调用（`this.xxx()` 不走代理）
3. 异常被 try-catch 吞掉（方法正常返回 → 事务提交）
4. 默认只回滚 RuntimeException，受检异常不回滚（需配置 `rollbackFor`）
5. 数据库引擎不支持事务（如 MySQL MyISAM）
6. 多线程环境（事务绑在线程上，子线程不在同一事务中）
7. 方法没有被 Spring 管理（类没加 `@Service`/`@Component`）

### Q2：@Transactional(rollbackFor = Exception.class) 和默认有什么区别？

**答**：默认只对 RuntimeException 和 Error 回滚，对受检异常(IOException、SQLException 等)不回滚。加上 `rollbackFor = Exception.class` 后，所有异常都回滚。**生产环境建议都加上**——受检异常也回滚比漏回滚更安全。

---

## 📌 在 Spring Boot 中

- Spring Boot 通过 `DataSourceTransactionManagerAutoConfiguration` 自动配置事务管理器
- 如果引入了 `spring-boot-starter-jdbc` 或 `mybatis-spring-boot-starter`，事务管理器已就绪，直接写 `@Transactional` 即可
- Spring Boot 2.x 的默认代理是 CGLIB，所以事务能对没有接口的类生效
- 建议在每个 Service 类的类级别加 `@Transactional(rollbackFor = Exception.class)`，查询方法加 `@Transactional(readOnly = true)` 优化

```java
@Service
@Transactional(rollbackFor = Exception.class)
public class OrderService {
    // 数据变更方法 → 继承类级别的事务配置

    @Transactional(readOnly = true)  // 只读事务，数据库可做优化
    public Order findById(Long id) {
        return orderDao.findById(id);
    }
}
```

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| @Transactional 原理 | AOP 环绕通知：开启事务 → proceed → 提交/回滚 |
| 默认回滚规则 | 只回滚 RuntimeException + Error，受检异常不回滚 |
| rollbackFor | 扩展回滚范围，生产建议用 `rollbackFor = Exception.class` |
| 失效场景 | 非public、内部调用、异常被吞、rollbackFor不当、非InnoDB、多线程 |
| readOnly | `readOnly = true` 用于纯查询，数据库可做只读优化 |

---

## 学习建议

1. **写一个转账 Demo 验证回滚**：两个更新操作，第二个故意抛 RuntimeException，验证第一个操作是否回滚。再换成抛 IOException（受检异常），验证不回滚。再改成 `rollbackFor = Exception.class`，验证回滚。
2. **亲手触发所有失效场景**：非 public、内部调用、try-catch 吞异常——每个场景都亲手触发一次，看见事务没回滚的瞬间，记忆才真正形成。
3. **养成类级别 `@Transactional(rollbackFor = Exception.class)` + 查询方法 `@Transactional(readOnly = true)` 的习惯**。