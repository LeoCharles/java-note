# JDBC 事务管理

前面 JDBC 篇讲了 `setAutoCommit(false)` + `commit`/`rollback` 的基本写法，DBUtils 篇也手动管了事务——但你有没有想过：**事务到底保证了什么？多个操作一起失败就叫事务吗？不同事务之间互相看到什么数据？隔离级别到底怎么选？** 本篇从 ACID 四大特性出发，讲清 JDBC 事务的完整模型：隔离级别、传播行为、保存点、以及生产环境的事务设计原则。这是 Spring `@Transactional` 的底层原理——理解了本篇，`@Transactional` 的隔离级别、传播行为、回滚规则对你就是透明的。

> 💡 本篇建议动手验证"隔离级别"——开两个客户端并发操作同一条数据，切换 READ_COMMITTED 和 REPEATABLE_READ 级别，亲眼看到"不可重复读"和"幻读"的现象。事务的理论听再多遍，不如亲手看到一次"脏数据"来得深刻。

---

## 一、事务的 ACID 四大特性 ⭐

事务（Transaction）是数据库操作的**最小执行单元**——要么全部成功，要么全部失败。ACID 是事务的四个核心保证：

| 特性 | 英文 | 含义 | 反例 |
| :--- | :--- | :--- | :--- |
| **原子性** | Atomicity | 事务中的操作要么全部执行，要么全部不执行 | 转账：扣钱成功、加钱失败——钱凭空消失 |
| **一致性** | Consistency | 事务前后数据满足所有约束（外键、唯一、业务规则） | 转账后总金额变了 |
| **隔离性** | Isolation | 并发事务之间互不干扰，各自独立执行 | 两人同时买最后一件库存——超卖 |
| **持久性** | Durability | 事务提交后数据永久保存，即使宕机也不丢失 | 提交成功，重启后数据没了 |

```
转账示例（从张三向李四转 500 元）：

BEGIN（开启事务）
  ① UPDATE account SET balance = balance - 500 WHERE name = '张三'
  ② UPDATE account SET balance = balance + 500 WHERE name = '李四'
COMMIT（提交）或 ROLLBACK（回滚）

ACID 保证：
- 原子性：①② 要么都执行，要么都不执行（没有只扣不加）
- 一致性：执行前后总金额不变（张三的钱不会消失）
- 隔离性：转账期间其他事务看不到"扣了但没加"的中间态
- 持久性：COMMIT 后钱一定到了，哪怕立刻宕机
```

> 💡 **关键认知**：ACID 不是数据库默认给你的——**A和D 数据库保证，C 靠业务约束保证，I 需要你选择正确的隔离级别**。尤其是隔离性，是事务设计和性能权衡的核心战场。

---

## 二、并发事务的三大问题

如果事务之间完全不加隔离，会出现三类问题。理解这三类问题是正确选择隔离级别的前提。

### 2.1 脏读（Dirty Read）⭐

**读到另一个事务未提交的数据**。另一个事务回滚后，你读到的数据就"脏"了——它从未真正存在过。

```java
// 事务 A：转账 500 → 李四（还未提交）
connA.setAutoCommit(false);
balance = query("SELECT balance FROM account WHERE name='李四'");   // 500
update("UPDATE account SET balance = balance + 500 WHERE name='李四'"); // → 1000
// 此时事务 B 读到李四余额 = 1000（脏数据！）
// 事务 A 回滚：balance 回到 500
connA.rollback();

// 事务 B 读到的 1000 从未真正存在过——这就是脏读
```

### 2.2 不可重复读（Non-Repeatable Read）⭐

**同一事务内两次读取同一条数据，结果不同**（因为中间另一个事务修改并提交了）。

```java
// 事务 A
connA.setAutoCommit(false);
int v1 = queryBalance("张三");   // 1000
// 此时事务 B：UPDATE balance = 800 WHERE name='张三'，提交了
int v2 = queryBalance("张三");   // 800（和 v1 不同——不可重复读！）
connA.commit();
```

> 💡 **脏读 vs 不可重复读**：脏读读到的是**未提交**的数据（可能回滚）；不可重复读读到的是**已提交**的数据（真实存在，但在你事务内变了）。不可重复读虽然拿到的是"真数据"，但在你的事务逻辑里，同一行两次读到的值不一致，可能有业务问题。

### 2.3 幻读（Phantom Read）

**同一事务内两次查询同一条件，结果集行数不同**（因为中间另一个事务插入/删除了满足条件的行）。

```java
// 事务 A：统计 age>18 的人数
connA.setAutoCommit(false);
int c1 = count("SELECT COUNT(*) FROM student WHERE age>18");   // 10
// 此时事务 B：INSERT INTO student(name, age) VALUES('王五', 20)，提交了
int c2 = count("SELECT COUNT(*) FROM student WHERE age>18");   // 11（多了一行——幻读！）
connA.commit();
```

> 💡 **不可重复读 vs 幻读**：不可重复读是**同一行数据被修改**了（UPDATE），幻读是**多了或少了几行**（INSERT/DELETE）。MVCC 用不同策略解决——前者用行锁或版本链，后者用间隙锁（Gap Lock）。

---

## 三、四种隔离级别 ⭐⭐

JDBC 通过 `Connection.setTransactionIsolation(int level)` 设置隔离级别。隔离级别越高，数据越安全，但并发性能越差。

| 级别 | JDBC 常量 | 值 | 脏读 | 不可重复读 | 幻读 | MySQL 默认 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 读未提交 | `READ_UNCOMMITTED` | 1 | ✓ 可能 | ✓ 可能 | ✓ 可能 | |
| 读已提交 | `READ_COMMITTED` | 2 | ✗ | ✓ 可能 | ✓ 可能 | |
| 可重复读 | `REPEATABLE_READ` | 4 | ✗ | ✗ | ✓ 可能* | ✅ MySQL 默认 |
| 串行化 | `SERIALIZABLE` | 8 | ✗ | ✗ | ✗ | |

> \* MySQL 的 `REPEATABLE_READ` 通过 **Gap Lock（间隙锁）** 实际解决了大部分幻读问题，比 SQL 标准规定的更强。

### 3.1 读未提交（READ_UNCOMMITTED）

最低级别，几乎不隔离。**实际项目几乎不用**——没人能接受读到脏数据。

```java
conn.setTransactionIsolation(Connection.TRANSACTION_READ_UNCOMMITTED);
```

### 3.2 读已提交（READ_COMMITTED）

只能读到**已提交**的数据，解决了脏读。Oracle 和 PostgreSQL 的默认级别。

```java
conn.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);
```

> 💡 **什么场景用 READ_COMMITTED**：大多数 OLTP（在线交易）系统用这个级别就够了——不允许脏读（银行转账底线），但接受不可重复读（比如列表页查两次，中间有人改了详情页，问题不大）。

### 3.3 可重复读（REPEATABLE_READ）⭐

**MySQL InnoDB 默认级别**。同一事务内多次读同一行，结果一致（用 MVCC 的快照读实现）。解决了脏读和不可重复读。

```java
conn.setTransactionIsolation(Connection.TRANSACTION_REPEATABLE_READ);
```

> ⚠️ **MySQL 的 REPEATABLE_READ 为什么能解决大部分幻读**：InnoDB 使用 **Next-Key Lock**（行锁 + 间隙锁），`SELECT ... FOR UPDATE` 时不仅锁住存在的行，还锁住行之间的"间隙"，阻止其他事务插入。所以 MySQL 的 RR 级别实际上是 SQL 标准 RR + Gap Lock。

### 3.4 串行化（SERIALIZABLE）

最高级别，事务完全串行执行，杜绝一切并发问题。**性能最差，几乎只在金融结账等极严格场景使用**。

```java
conn.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
```

### 3.5 验证隔离级别的代码

写一个测试，用两个连接并发操作同一行，观察不同隔离级别下的现象：

```java
public class IsolationDemo {
    public static void main(String[] args) throws Exception {
        // 连接 1：读
        Connection conn1 = HikariUtil.getConnection();
        conn1.setAutoCommit(false);
        conn1.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);

        // 连接 2：写
        Connection conn2 = HikariUtil.getConnection();
        conn2.setAutoCommit(false);

        // 连接 1 第一次读
        int v1 = queryBalance(conn1, "张三");
        System.out.println("v1 = " + v1);   // 1000

        // 连接 2 修改并提交
        updateBalance(conn2, "张三", 800);
        conn2.commit();
        System.out.println("连接 2 提交了修改");

        // 连接 1 第二次读（同一事务内）
        int v2 = queryBalance(conn1, "张三");
        System.out.println("v2 = " + v2);
        // READ_COMMITTED：v2 = 800（不可重复读——两次读不同！）
        // REPEATABLE_READ：v2 = 1000（可重复读——快照一致）

        conn1.commit();
        conn1.close();
        conn2.close();
    }
}
```

---

## 四、JDBC 事务的完整写法

### 4.1 标准事务模板

前面 JDBC 篇写过一个简单的转账，这里给出生产级别的完整模板：

```java
public static void transferMoney(DataSource ds, int fromId, int toId, double amount) {
    Connection conn = null;
    try {
        conn = ds.getConnection();
        conn.setAutoCommit(false);            // ① 开启事务
        conn.setTransactionIsolation(         // ② 设置隔离级别（可选）
            Connection.TRANSACTION_READ_COMMITTED);

        // ③ 执行业务 SQL
        try (PreparedStatement ps1 = conn.prepareStatement(
                "UPDATE account SET balance = balance - ? WHERE id = ? AND balance >= ?")) {
            ps1.setDouble(1, amount);
            ps1.setInt(2, fromId);
            ps1.setDouble(3, amount);         // 业务校验：余额必须 ≥ 转出金额
            int rows1 = ps1.executeUpdate();
            if (rows1 == 0) {
                throw new RuntimeException("余额不足或账户不存在");
            }
        }

        try (PreparedStatement ps2 = conn.prepareStatement(
                "UPDATE account SET balance = balance + ? WHERE id = ?")) {
            ps2.setDouble(1, amount);
            ps2.setInt(2, toId);
            int rows2 = ps2.executeUpdate();
            if (rows2 == 0) {
                throw new RuntimeException("目标账户不存在");
            }
        }

        conn.commit();                         // ④ 全部成功，提交
    } catch (Exception e) {
        if (conn != null) {
            try {
                conn.rollback();               // ⑤ 任何异常都回滚
            } catch (SQLException ex) {
                ex.printStackTrace();
            }
        }
        throw new RuntimeException("转账失败", e);   // ⑥ 包装后抛出
    } finally {
        if (conn != null) {
            try {
                conn.setAutoCommit(true);      // ⑦ 恢复默认
                conn.close();                  // ⑧ 归还连接
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }
    }
}
```

> ⚠️ **事务模板的关键点**：
> 1. **rollback 必须在 close 之前**——连接关了再 rollback 抛异常，事务悬空。
> 2. **setAutoCommit(true) 恢复默认**——连接池复用的连接可能带回上一次事务的 autoCommit 状态，不恢复会影响后续操作。
> 3. **业务校验写在 SQL 里**（`balance >= ?`）而非 Java 代码里——并发场景下"先查余额、再判断、再更新"是非原子的。

### 4.2 保存点（Savepoint）

JDBC 支持在事务中设置保存点，允许部分回滚（只回滚到保存点，不回滚整个事务）：

```java
conn.setAutoCommit(false);

// 操作 1
update(conn, "UPDATE account SET balance = balance - 500 WHERE id = 1");
Savepoint sp = conn.setSavepoint("after_debit");   // 设保存点

// 操作 2（可能失败）
try {
    update(conn, "UPDATE account SET balance = balance + 500 WHERE id = 999");  // 假设不存在
} catch (SQLException e) {
    conn.rollback(sp);   // 回滚到保存点，操作 1 保留
    // 尝试其他处理...
}

conn.commit();   // 只提交操作 1（如果操作 2 被跳过）
```

> 💡 **保存点的使用场景**：批量处理中"跳过失败条、继续下一批"，但要慎用——回滚到保存点后事务继续，复杂度高，不如拆成独立小事务。

---

## ⚠️ 重点

1. **ACID 不是全自动的**：原子性和持久性数据库保证，一致性靠业务约束，隔离性需要你选对隔离级别。
2. **隔离级别是性能与安全性的权衡**：MySQL 默认 REPEATABLE_READ；Oracle 默认 READ_COMMITTED。大多数场景 READ_COMMITTED 已足够。
3. **MySQL 的 RR 比标准更强**：InnoDB 的 Gap Lock 解决了大部分幻读问题。
4. **事务模板的 8 个步骤**：借连接 → 关自动提交 → 设隔离级别 → 执行 SQL → commit → catch 中 rollback → finally 恢复 autoCommit + close。
5. **rollback 必须在 close 之前**——这是事务 bug 的第一高发区。
6. **不要用 `SELECT + if + UPDATE`** 做业务校验——并发时不是原子的，用 `UPDATE ... WHERE 条件` 或 `SELECT ... FOR UPDATE`。
7. **连接归还前必须恢复 autoCommit**——连接池复用，上一次事务的 autoCommit=false 会污染下一次操作。
8. **保存点慎用**：增加复杂度，优先考虑拆成小事务。

---

## 💻 实战案例：转账 + 流水记录的完整事务

需求：转账时同时记录转账流水（transfer_log 表），转账和流水原子执行。

```java
public class TransferService {
    private final DataSource ds;

    public TransferService(DataSource ds) {
        this.ds = ds;
    }

    /**
     * 完整转账：扣钱 + 加钱 + 写流水，一个事务
     */
    public void transfer(int fromId, int toId, double amount) {
        Connection conn = null;
        try {
            conn = ds.getConnection();
            conn.setAutoCommit(false);
            conn.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);

            // 1. 扣款（带余额校验）
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE account SET balance = balance - ? WHERE id = ? AND balance >= ?")) {
                ps.setDouble(1, amount);
                ps.setInt(2, fromId);
                ps.setDouble(3, amount);
                if (ps.executeUpdate() == 0) {
                    throw new RuntimeException("转出账户余额不足或不存在");
                }
            }

            // 2. 加款
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE account SET balance = balance + ? WHERE id = ?")) {
                ps.setDouble(1, amount);
                ps.setInt(2, toId);
                if (ps.executeUpdate() == 0) {
                    throw new RuntimeException("目标账户不存在");
                }
            }

            // 3. 写流水
            try (PreparedStatement ps = conn.prepareStatement(
                    "INSERT INTO transfer_log(from_id, to_id, amount, create_time) VALUES(?, ?, ?, ?)")) {
                ps.setInt(1, fromId);
                ps.setInt(2, toId);
                ps.setDouble(3, amount);
                ps.setTimestamp(4, Timestamp.valueOf(LocalDateTime.now()));
                ps.executeUpdate();
            }

            conn.commit();
            System.out.println("转账成功：" + fromId + " → " + toId + "，金额 " + amount);
        } catch (Exception e) {
            rollbackQuietly(conn);
            throw new RuntimeException("转账失败", e);
        } finally {
            closeQuietly(conn);
        }
    }

    private void rollbackQuietly(Connection conn) {
        if (conn != null) {
            try { conn.rollback(); } catch (SQLException ignored) {}
        }
    }

    private void closeQuietly(Connection conn) {
        if (conn != null) {
            try {
                conn.setAutoCommit(true);     // 恢复默认
                conn.close();
            } catch (SQLException ignored) {}
        }
    }
}

// 使用
TransferService service = new TransferService(HikariUtil.getDataSource());
service.transfer(1, 2, 500);   // 张三 → 李四 500
```

---

## 🚀 新版本补充

- **JDBC 4.0+**：`setTransactionIsolation` 常量定义在 `java.sql.Connection` 中，无需额外导入。
- **MySQL 8.0+**：InnoDB 的 MVCC 实现更成熟，`REPEATABLE_READ` + Gap Lock 的组合在绝大多数场景下足够安全，无需升级到 `SERIALIZABLE`。
- **Spring 6.0+ / Spring Boot 3.x**：`@Transactional` 全面支持 `jakarta.transaction`，底层仍是 JDBC 事务。

---

## 📌 在 Spring Boot 中

> 本篇的全部事务逻辑——`setAutoCommit`、隔离级别设置、commit/rollback、保存点、连接恢复——在 Spring Boot 中被 `@Transactional` 注解全面封装。下面逐一对照，给出实际开发代码，以及"出问题怎么回到原理排查"。

### 1. 从"手动事务模板"到"@Transactional"

**原生**：借连接 → 关自动提交 → 执行 SQL → commit → catch 中 rollback → finally 恢复。
**Spring Boot**：一个注解。

```java
@Service
public class TransferService {
    @Autowired
    private JdbcTemplate jdbc;

    @Transactional   // 替代本篇全部事务模板代码
    public void transfer(int fromId, int toId, double amount) {
        jdbc.update("UPDATE account SET balance=balance-? WHERE id=? AND balance>=?",
                amount, fromId, amount);
        jdbc.update("UPDATE account SET balance=balance+? WHERE id=?",
                amount, toId);
        jdbc.update("INSERT INTO transfer_log(from_id,to_id,amount,create_time) VALUES(?,?,?,?)",
                fromId, toId, amount, LocalDateTime.now());
        // 任何一个抛异常，全部自动回滚
    }
}
```

> 💡 **原理对应**：`@Transactional` 底层用 AOP 代理拦截方法调用：方法开始前从 DataSource 借连接、`setAutoCommit(false)`；方法正常结束 `commit()`；任何 RuntimeException 触发 `rollback()`；finally 块中 `setAutoCommit(true)` + 还连接。**本篇的 8 步事务模板，Spring 一个注解全替代**。

> 💡 **原理排查**：`@Transactional` 不生效（不回滚）？三个高频原因：
> 1. **同类方法调用**：`this.transfer()` 不走代理（AOP 失效），必须通过注入的 Bean 调用。
> 2. **异常被 catch 吞了**：Spring 靠异常感知需要回滚——你 catch 并吞了（不重新抛出），Spring 不知道要回滚。
> 3. **方法不是 public**：AOP 基于动态代理，私有方法不代理。

### 2. 隔离级别：从"setTransactionIsolation"到"isolation 属性"

**原生**：`conn.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED)`。
**Spring Boot**：`@Transactional(isolation = ...)`。

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public void transfer(int fromId, int toId, double amount) { ... }

// 三种常用级别
// Isolation.READ_COMMITTED       ← 读已提交（最常用）
// Isolation.REPEATABLE_READ      ← MySQL 默认
// Isolation.SERIALIZABLE         ← 串行化（极少用）
```

> 💡 **原理对应**：`@Transactional(isolation = ...)` 最终调的就是 `conn.setTransactionIsolation(int)`。Spring 只是把常量换成了枚举，值和 JDBC 完全对应。

### 3. 传播行为：JDBC 没有，Spring 独创

**原生 JDBC**：没有"传播行为"概念——一个连接就是一个事务，嵌套调用等于复用同一个连接的事务。
**Spring Boot**：`@Transactional(propagation = ...)` 定义了 7 种传播行为。

```java
@Transactional(propagation = Propagation.REQUIRED)      // 默认：有事务就加入，没有就新建
@Transactional(propagation = Propagation.REQUIRES_NEW)  // 总是新建独立事务（挂起当前）
@Transactional(propagation = Propagation.NESTED)        // 嵌套事务（用保存点实现）
```

| 传播行为 | 当前有事务 | 当前无事务 | 典型场景 |
| :--- | :--- | :--- | :--- |
| `REQUIRED`（默认） | 加入 | 新建 | 大多数场景 |
| `REQUIRES_NEW` | 挂起当前，新建 | 新建 | 写日志（不能随业务回滚） |
| `NESTED` | 嵌套（保存点） | 新建 | 批量处理：出错回滚到保存点，不毁整个事务 |
| `SUPPORTS` | 加入 | 不新建 | 只读查询 |
| `NOT_SUPPORTED` | 挂起当前 | 不新建 | 不需要事务的耗时操作 |
| `NEVER` | 抛异常 | 不新建 | 强制非事务 |
| `MANDATORY` | 加入 | 抛异常 | 强制必须有事务 |

```java
// 典型组合：业务方法 REQUIRED + 日志方法 REQUIRES_NEW
@Service
public class OrderService {
    @Autowired
    private LogService logService;

    @Transactional   // REQUIRED（默认）
    public void createOrder(Order order) {
        orderDao.insert(order);          // 入库——事务内
        logService.log("创建订单", order); // 写日志——独立事务，不随订单回滚
        // 如果订单创建抛异常，日志已提交（因为独立事务）
    }
}

@Service
public class LogService {
    @Transactional(propagation = Propagation.REQUIRES_NEW)   // 独立事务
    public void log(String action, Object detail) {
        logDao.insert(action, detail);
    }
}
```

> 💡 **原理对应**：`REQUIRES_NEW` 的挂起和恢复，底层仍是对同一个 `Connection` 的操作——Spring 在挂起时把当前事务的 `Connection` 暂存，新建一个新的 `Connection`（从池另借一个）执行被调用方法，方法结束后 commit 这个新连接并还回池，然后恢复被挂起的连接继续。**"传播"的本质是"连接的切换和共享策略"**。

> 💡 **原理排查**：`REQUIRES_NEW` 不生效？检查是不是同类调用（`this.log()` 不走代理）；检查数据库是否支持（大部分数据库支持）；注意 `REQUIRES_NEW` 的隔离级别可能不同于外层事务。

### 4. 回滚规则：从"所有异常都回滚"到"默认只回滚 RuntimeException"

**原生**：catch 住任何异常都 rollback（你手动写的 catch 块）。
**Spring Boot**：默认只对 **RuntimeException 和 Error** 回滚，受检异常（checked exception）不回滚。

```java
// Spring 默认：RuntimeException 回滚，IOException 不回滚
@Transactional
public void transfer(int fromId, int toId, double amount) throws IOException {
    // 抛 NullPointerException → 回滚
    // 抛 IOException → 不回滚！（受检异常，Spring 默认不感知）
}

// 指定回滚的异常类型
@Transactional(rollbackFor = Exception.class)      // 所有异常都回滚
@Transactional(noRollbackFor = IllegalArgumentException.class)  // 指定异常不回滚
```

> ⚠️ **`rollbackFor = Exception.class` 几乎是生产标配**：Spring 默认不回滚受检异常，但你业务中抛出的自定义 `BusinessException` 往往是继承 `Exception`（受检），不配 `rollbackFor` 它就不回滚——这是高频坑。

### 5. 只读事务：优化提示

```java
@Transactional(readOnly = true)   // 告知底层本次事务只读
public List<User> findAll() {
    return userDao.findAll();      // Spring 会设 Connection 为只读（JDBC 不支持此优化的驱动会忽略）
}
```

> 💡 **原理对应**：`@Transactional(readOnly = true)` 底层调 `conn.setReadOnly(true)`。MySQL InnoDB 忽略这个提示（没性能差异），但 Hibernate/JPA 会用读写分离路由到从库、跳过脏检查——在 ORM 场景下有实际优化效果。

---

> 一句话：**`@Transactional` 是你本篇学的全部事务模板代码的注解版**——`setAutoCommit(false)` + 隔离级别 + commit/rollback + 连接恢复 + 保存点，Spring 用 AOP 代理全自动完成。传播行为是 Spring 在 JDBC 事务上的高级封装（原生 JDBC 没有传播行为概念）。**出事务不回滚、隔离级别不对、传播行为不生效、`REQUIRES_NEW` 没拿到新连接时，你仍要回到本篇原理排查**：事务靠 AOP 代理、回滚靠异常传播、隔离级别靠 Connection API。

## 本章小结

本篇建立了 JDBC 事务的完整认知：ACID 四大特性是事务的理论根基；并发事务的三大问题（脏读/不可重复读/幻读）决定了隔离级别的选择；四种隔离级别（从 READ_UNCOMMITTED 到 SERIALIZABLE）是性能与安全性的权衡。重点掌握标准事务模板的 8 个步骤、隔离级别的验证实验、保存点的使用场景、以及"rollback 必须在 close 前"和"连接归还前恢复 autoCommit"两条铁律。核心认知：**Spring `@Transactional` 的所有特性——隔离级别、传播行为、回滚规则、只读事务——底层都是本篇的 JDBC 事务 API**。理解了本篇，`@Transactional` 不再是魔法，而是一层"把 8 行模板代码变成 1 行注解"的封装。