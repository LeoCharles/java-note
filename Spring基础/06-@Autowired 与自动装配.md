# @Autowired 与自动装配

上一篇讲了三种注入方式，其中构造器注入是首选。但实际开发中，`@Autowired` 依然是出现频率最高的注解——不论是注入字段、构造器还是 setter，背后都是 `@Autowired` 在驱动。本篇深入 `@Autowired` 的匹配规则、限定策略和常见陷阱。

> 💡 `@Autowired` 的默认行为是**按类型注入**。但"类型注入"在容器中有多个同类型 Bean 时该怎么办？这就是本篇的核心话题。

---

## 一、@Autowired 的匹配规则

### 1.1 默认：按类型注入（byType）

```java
@Service
public class OrderService {
    @Autowired
    private UserDao userDao;  // Spring: "找类型为 UserDao 的 Bean"
}

@Repository
public class UserDaoImpl implements UserDao { }
// Spring 找到 UserDaoImpl，注入
```

**Spring 的匹配流程**：

```
@Autowired UserDao userDao
        │
        ▼
在容器中查找所有类型为 UserDao 的 Bean
        │
        ├── 找到 1 个 → ✅ 直接注入
        ├── 找到 0 个 → 看 required 属性
        │       ├── required = true （默认）→ ❌ NoSuchBeanDefinitionException
        │       └── required = false       → ✅ 跳过，字段保持 null
        └── 找到多个 → 看下一步：按名称匹配
```

### 1.2 多类型时的处理：按名称降级（byName）

当容器中有多个同类型 Bean 时，Spring 会尝试按**字段名/参数名**匹配：

```java
public interface UserDao { }

@Repository
public class UserDaoImpl implements UserDao { }  // Bean 名：userDaoImpl

@Repository("userDao")  // 显式命名
public class UserDaoCustomImpl implements UserDao { }  // Bean 名：userDao

@Service
public class UserService {
    @Autowired
    private UserDao userDao;  // ← 字段名叫 userDao
    // Spring: 有两个 UserDao → 看字段名 "userDao" → 匹配到 UserDaoCustomImpl！
}
```

> ⚠️ **这就是很多"明明没配置却注入对了"的原因**：字段名恰好和某个 Bean 的名字一样，Spring 按名称降级匹配上了。但这属于"碰巧"，不可依赖——同事改了字段名就炸了。

---

## 二、注入冲突的解决策略

当按类型找到多个 Bean 时，有三种方式明确指定注入哪一个：

### 2.1 @Qualifier：按名称限定

```java
@Service
public class UserService {
    @Autowired
    @Qualifier("userDaoImpl")   // ← 明确指定要叫 "userDaoImpl" 的那个
    private UserDao userDao;
}
```

> 💡 `@Qualifier` 的参数是 **Bean 名称**，不是类名。默认 Bean 名是类名首字母小写。

**@Qualifier 也可以用在构造器注入中**：

```java
@Service
public class OrderService {
    private final UserDao userDao;

    public OrderService(@Qualifier("userDaoImpl") UserDao userDao) {
        this.userDao = userDao;
    }
}
```

### 2.2 @Primary：设置首选 Bean

```java
@Repository
@Primary   // ← 标记"当多个同类型 Bean 时，选我"
public class UserDaoImpl implements UserDao { }

@Repository
public class UserDaoBackupImpl implements UserDao { }  // 备选实现

@Service
public class UserService {
    @Autowired
    private UserDao userDao;  // 注入 UserDaoImpl（因为有 @Primary）
}
```

> 💡 `@Primary` 和 `@Qualifier` 同时存在时，`@Qualifier` 优先。`@Primary` 是"默认选谁"，`@Qualifier` 是"明确要谁"。

### 2.3 注入集合：拿到所有同类型 Bean

```java
@Service
public class ChainService {
    @Autowired
    private List<Validator> validators;  // 注入所有 Validator 类型的 Bean

    @Autowired
    private Map<String, Validator> validatorMap;  // Key=Bean名，Value=Bean实例

    public void validate(Order order) {
        // 责任链模式：遍历所有校验器
        for (Validator v : validators) {
            v.validate(order);
        }
    }
}
```

> 💡 这是实现**策略模式、责任链模式、插件机制**的利器——写一个新 Validator 加 `@Component`，自动加入校验链，零配置扩展。

---

## 三、@Autowired 的高级用法

### 3.1 required = false：可选注入

```java
@Service
public class OrderService {
    @Autowired(required = false)
    private SmsService smsService;  // 有这个 Bean 就注入，没有也不报错

    public void createOrder(Order order) {
        // 业务逻辑...
        if (smsService != null) {   // 发短信是可选功能
            smsService.send(order.getUserPhone(), "下单成功");
        }
    }
}
```

> ⚠️ 如果用 `required = false`，调用前必须判空，否则 NPE。更优雅的做法是用 `Optional`：

```java
@Autowired(required = false)
private Optional<SmsService> smsService;  // 语义更明确：这是可选的
```

### 3.2 @Autowired 标注在方法上

```java
@Service
public class OrderService {
    private UserDao userDao;
    private OrderDao orderDao;

    @Autowired  // 不是只有字段和构造器能标！方法也可以
    public void prepare(UserDao userDao, OrderDao orderDao) {
        // Spring 会自动从容器中找到参数对应的 Bean 并传入
        this.userDao = userDao;
        this.orderDao = orderDao;
    }
}
```

这个方法不一定是 setter，**任意方法名都可以**。Spring 会解析方法参数，从容器中获取对应的 Bean 并调用这个方法。

### 3.3 @Autowired 保证注入完成

```java
@Component
public class DatabaseInitializer {
    @Autowired
    private DataSource dataSource;

    public DatabaseInitializer() {
        // ⚠️ 这里 dataSource 还是 null！
        // 构造方法执行时，@Autowired 还没注入
    }

    @PostConstruct
    public void init() {
        // ✅ 这里 dataSource 已经注入了
        dataSource.getConnection();
    }
}
```

> ⚠️ **陷阱**：在构造方法中使用 `@Autowired` 注入的字段会得到 null。因为 JVM 是先执行构造方法再处理注解注入的。初始化逻辑请放在 `@PostConstruct` 方法中。

---

## 四、@Autowired vs @Resource

| | `@Autowired` | `@Resource` |
| :--- | :--- | :--- |
| **来源** | Spring 提供（`org.springframework.beans.factory.annotation`） | JDK 提供（`javax.annotation` / `jakarta.annotation`，JSR-250） |
| **匹配顺序** | 默认 **byType** → 多 Bean 时 byName | 默认 **byName** → 找不到时 byType |
| **@Qualifier 支持** | ✅ | ❌（用 `@Resource(name = "xxx")`） |
| **required 属性** | ✅ `@Autowired(required = false)` | ❌（没有，没找到直接抛异常） |
| **推荐** | ⭐⭐⭐ | 了解即可，Spring 生态偏向 @Autowired |

```java
// @Autowired：默认按类型
@Autowired
private UserDao userDao;  // 找类型为 UserDao 的

// @Resource：默认按名称
@Resource
private UserDao userDao;  // 找名称为 "userDao" 的（字段名），找不到再按类型

// @Resource 指定名称
@Resource(name = "userDaoImpl")
private UserDao userDao;  // 明确找名称为 "userDaoImpl" 的
```

> 💡 **选型建议**：Spring 项目中统一用 `@Autowired` + `@Qualifier`。`@Resource` 是 Java 标准注解，理论上与 Spring 解耦，但实际上你不可能脱离 Spring 用它——所以还是用 `@Autowired`。

---

## 💻 实战案例

### 案例 1：@Primary 实现默认实现 + 可切换

```java
// 支付接口
public interface PaymentService {
    void pay(Order order);
}

// 微信支付（默认首选）
@Service
@Primary
public class WechatPaymentService implements PaymentService {
    @Override
    public void pay(Order order) {
        System.out.println("微信支付：" + order.getAmount());
    }
}

// 支付宝支付
@Service
public class AlipayPaymentService implements PaymentService {
    @Override
    public void pay(Order order) {
        System.out.println("支付宝支付：" + order.getAmount());
    }
}

// 业务类：默认走微信，需要支付宝时用 @Qualifier
@Service
public class OrderPaymentService {
    @Autowired
    private PaymentService paymentService;           // 默认 = 微信支付

    @Autowired
    @Qualifier("alipayPaymentService")
    private PaymentService alipayService;            // 明确 = 支付宝

    public void payWithDefault(Order order) {
        paymentService.pay(order);  // 微信
    }

    public void payWithAlipay(Order order) {
        alipayService.pay(order);  // 支付宝
    }
}
```

### 案例 2：用 Map 注入实现策略模式

```java
// 策略接口
public interface ExportStrategy {
    String getType();           // 返回类型标识
    void export(List<Order> orders);
}

// Excel 导出
@Component
public class ExcelExportStrategy implements ExportStrategy {
    @Override public String getType() { return "excel"; }
    @Override public void export(List<Order> orders) {
        System.out.println("导出 Excel...");
    }
}

// PDF 导出
@Component
public class PdfExportStrategy implements ExportStrategy {
    @Override public String getType() { return "pdf"; }
    @Override public void export(List<Order> orders) {
        System.out.println("导出 PDF...");
    }
}

// 策略调度者
@Service
public class ExportService {
    // 注入所有 ExportStrategy → Map<Bean名, 策略>
    @Autowired
    private Map<String, ExportStrategy> strategyMap;

    public void export(String type, List<Order> orders) {
        // 找到匹配的策略
        ExportStrategy strategy = strategyMap.values().stream()
                .filter(s -> s.getType().equals(type))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("不支持的导出类型：" + type));
        strategy.export(orders);
    }
}
```

```java
// 调用
exportService.export("excel", orderList);  // 导出 Excel...
exportService.export("pdf", orderList);    // 导出 PDF...
```

> 💡 新增导出格式：只需写一个新类实现 `ExportStrategy` + `@Component`，零配置自动加入 `strategyMap`，真正的开闭原则（对扩展开放、对修改关闭）。

---

## 🎯 面试高频

### Q1：@Autowired 的匹配过程是怎样的？

**答**：
1. 按类型（byType）在容器中查找所有匹配的 Bean
2. 找到 0 个：`required = true` → 抛异常；`required = false` → 字段为 null
3. 找到 1 个：直接注入
4. 找到多个：尝试按名称（byName，用字段名/参数名）匹配；有一个名称匹配 → 注入它；没有匹配 → 抛 `NoUniqueBeanDefinitionException`
5. 如果使用了 `@Qualifier` → 直接用指定名称匹配
6. 如果某个 Bean 标了 `@Primary` → 多 Bean 时选它（`@Qualifier` 优先级高于 `@Primary`）

### Q2：@Autowired 和 @Resource 的区别？

**答**：
- `@Autowired` 是 Spring 注解，**默认按类型注入**，支持 `@Qualifier` 精细控制
- `@Resource` 是 JSR-250 标准注解，**默认按名称注入**（字段名或 `name` 属性），不匹配再按类型
- 实际开发推荐统一用 `@Autowired`

---

## 📌 在 Spring Boot 中

- `@Autowired` 是 Spring Boot 项目中最常用的注入注解。配合构造器注入（[05-依赖注入方式详解](05-依赖注入方式详解.md)），Spring Boot 官方推荐的单构造器省略 `@Autowired` 写法让代码更简洁。
- Spring Boot Test 提供了 `@MockBean` 和 `@SpyBean`，可以在测试容器中**替换**被 `@Autowired` 注入的 Bean——这也是为什么注入方式要灵活（构造器注入可以直接传 Mock 对象，字段注入必须靠 `@MockBean`）。
- 如果你用 `@Autowired` 注入一个 Bean 时 IDEA 报红"No beans of type found"，可能是忘了加 `@Component` / `@Service` / `@Repository`——检查一下目标类是否被 Spring 扫描到。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 默认匹配 | 按类型 byType → 多 Bean 时按名称 byName |
| @Qualifier | 按 Bean 名称精确限定，"明确要谁" |
| @Primary | 标记首选 Bean，"默认选谁"；@Qualifier 优先级更高 |
| 注入集合 | `List<Interface>` 拿所有实现，实现策略模式/插件机制 |
| required=false | 可选注入，用前判空或用 Optional 包装 |
| @Autowired vs @Resource | @Autowired 默认 byType，@Resource 默认 byName |

---

## 学习建议

1. **亲手触发 NoUniqueBeanDefinitionException**：定义两个同类型 Bean，不给 @Primary 也不给 @Qualifier，用 @Autowired 注入——观察错误信息，理解"Spring 不知道该选谁"的报错长什么样。
2. **写一个策略模式 Demo**：用 `Map<String, Strategy>` 注入所有策略实现，体会"加新策略零配置扩展"的爽感。
3. **区分 @Primary 和 @Qualifier 的优先级**：同时给两个注解，验证 @Qualifier 是否确实覆盖了 @Primary。