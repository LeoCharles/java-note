# Spring 单元测试

前面 17 篇学了 Spring 的全部核心机制，最后用测试收尾。Spring 测试框架让你在不启动完整应用的情况下，轻松测试单个组件、模拟外部依赖。写测试和不写测试的区别，就是"改完代码心里没底"和"改完代码跑一遍测试就知道有没有破坏什么"的区别。

> 💡 测试不是"学完再配"的附属品，而是开发的一部分。Spring Boot 从设计之初就为可测试性做了大量工作——构造器注入、`@MockBean`、`@SpringBootTest`——用好它们，测试和写业务一样高效。

---

## 一、测试分层策略

```
┌─────────────────────────────────────┐
│  单元测试（不启动 Spring 容器）       │
│  - 纯 Java + Mockito               │  ← 最快，80% 的测试
│  - 测试单个 Service 的逻辑          │
├─────────────────────────────────────┤
│  集成测试（启动部分 Spring 容器）     │
│  - @SpringBootTest + @MockBean     │  ← 中速，15% 的测试
│  - 测试 Controller/Repository 集成  │
├─────────────────────────────────────┤
│  端到端测试（启动完整应用）           │
│  - TestRestTemplate / MockMvc       │  ← 最慢，5% 的测试
│  - 模拟真实 HTTP 请求               │
└─────────────────────────────────────┘
```

> 💡 **80/15/5 法则**：80% 单元测试（秒级完成） + 15% 集成测试 + 5% 端到端测试。不要每层都启动 Spring 容器——那会让测试变成"启动 30 秒，跑 3 秒"。

---

## 二、纯单元测试（不启动 Spring 容器）

### 2.1 构造器注入的最大好处：可测试

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderDao orderDao;
    private final UserService userService;

    public Order createOrder(CreateOrderRequest request) {
        userService.validate(request.getUserId());
        Order order = buildOrder(request);
        return orderDao.save(order);
    }
}
```

```java
// 单测：不需要 Spring 容器！纯 Java + Mockito
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock  // 模拟的依赖
    private OrderDao orderDao;
    @Mock
    private UserService userService;

    @InjectMocks  // 把 Mock 注入到 OrderService 的构造器中
    private OrderService orderService;

    @Test
    void shouldCreateOrderSuccessfully() {
        // Given（准备）
        CreateOrderRequest request = new CreateOrderRequest();
        request.setUserId(1L);
        request.setProductId(100L);

        Order savedOrder = new Order();
        savedOrder.setId(1L);
        when(orderDao.save(any(Order.class))).thenReturn(savedOrder);

        // When（执行）
        Order result = orderService.createOrder(request);

        // Then（验证）
        assertNotNull(result.getId());
        verify(userService).validate(1L);        // 验证调了 validate
        verify(orderDao).save(any(Order.class));  // 验证调了 save
    }

    @Test
    void shouldThrowWhenUserInvalid() {
        CreateOrderRequest request = new CreateOrderRequest();
        request.setUserId(999L);

        // 让 validate 抛异常
        doThrow(new BusinessException("用户不存在"))
                .when(userService).validate(999L);

        // 验证异常
        assertThrows(BusinessException.class,
                () -> orderService.createOrder(request));
        verify(orderDao, never()).save(any());  // 验证没调 save
    }
}
```

> 💡 这就是为什么构造器注入优于字段注入——`@InjectMocks` 自动把 `@Mock` 注入构造器，一行 `new OrderService` 不用写。如果是字段注入（`@Autowired`），测试就得启动 Spring 容器或用反射设值。

### 2.2 Mockito 核心 API 速查

```java
// 1. 模拟返回值
when(userDao.findById(1L)).thenReturn(Optional.of(user));
when(userDao.findById(anyLong())).thenReturn(Optional.empty());

// 2. 模拟抛异常
doThrow(new RuntimeException("DB down")).when(userDao).save(any());
// （void 方法用 doThrow().when()，有返回值的方法用 when().thenThrow()）

// 3. 验证调用次数
verify(userDao).save(any(User.class));          // 调了 1 次
verify(userDao, times(2)).save(any(User.class));// 调了 2 次
verify(userDao, never()).save(any(User.class)); // 一次没调
verify(userDao, atLeastOnce()).findById(anyLong());

// 4. 捕获参数
ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
verify(userDao).save(captor.capture());
User capturedUser = captor.getValue();
assertEquals("张三", capturedUser.getName());

// 5. Spy：部分 Mock（真实对象 + 部分方法模拟）
@Spy
private OrderService orderService;

@Test
void shouldCallRealMethod() {
    // 大部分方法走真实逻辑，只 Mock 一个特定方法
    doReturn(mockOrder).when(orderService).queryRemote(any());
    // queryRemote 被 Mock 了，其他方法都走真实逻辑
}
```

---

## 三、集成测试（启动部分 Spring 容器）

### 3.1 @SpringBootTest + @MockBean

```java
@SpringBootTest  // 启动完整的 Spring Boot 应用
@AutoConfigureMockMvc  // 自动配置 MockMvc
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;         // 模拟 HTTP 请求

    @MockBean                          // 替换 Spring 容器中的 Bean
    private OrderService orderService; // 真实的 Service 被 Mock 替换

    @Test
    void shouldReturnOrder() throws Exception {
        // Given
        Order order = new Order();
        order.setId(1L);
        when(orderService.findById(1L)).thenReturn(order);

        // When & Then
        mockMvc.perform(get("/api/orders/1")
                        .header("Authorization", "Bearer test-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.id").value(1));
    }

    @Test
    void shouldReturn400WhenInvalidRequest() throws Exception {
        String invalidJson = "{\"userId\":null,\"productId\":null}";

        mockMvc.perform(post("/api/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(invalidJson))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }
}
```

### 3.2 只加载需要的 Bean

```java
// 不启动完整应用，只加载 Controller 层
@WebMvcTest(OrderController.class)  // 只加载 OrderController
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private OrderService orderService;  // Service 用 Mock

    // ... 同上
}

// 只加载 Service 层
@ExtendWith(SpringExtension.class)
@ContextConfiguration(classes = {OrderService.class, OrderDao.class})
class OrderServiceIntegrationTest {
    // ...
}
```

### 3.3 测试数据库操作

```java
@DataJpaTest  // 只加载 JPA 相关 Bean，自动配置 H2 内存数据库
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
// ↑ 如果想用真实数据库而非 H2
class UserRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;  // 用于准备测试数据

    @Autowired
    private UserRepository userRepository;

    @Test
    void shouldFindByName() {
        // Given
        User user = new User("张三", 25);
        entityManager.persistAndFlush(user);  // 写入测试数据库

        // When
        Optional<User> found = userRepository.findByName("张三");

        // Then
        assertTrue(found.isPresent());
        assertEquals(25, found.get().getAge());
    }

    @Test
    @Transactional
    @Rollback  // 测试结束后自动回滚，不影响其他测试
    void shouldSaveUser() {
        User user = userRepository.save(new User("李四", 30));
        assertNotNull(user.getId());
    }
}
```

---

## 四、测试中事务自动回滚

```java
@SpringBootTest
@Transactional  // ← 测试结束后自动回滚！
class UserServiceTest {

    @Autowired
    private UserService userService;

    @Test
    void shouldCreateUser() {
        User user = userService.create(new CreateUserRequest("张三", 20));
        assertNotNull(user.getId());
        // 测试结束 → 事务自动回滚 → 数据库中没有"张三"这条记录
        // 好处：同一个 Test 类中的每个测试互不影响
    }
}
```

> 💡 这是 Spring Test 最实用的特性之一——测试中的数据库操作默认回滚，确保测试之间的数据隔离。

---

## 💻 实战案例

### 案例：完整的三层测试

```java
// ===== 第一层：单元测试（不启动容器） =====
@ExtendWith(MockitoExtension.class)
class OrderServiceUnitTest {
    @Mock private OrderDao orderDao;
    @Mock private InventoryService inventoryService;
    @InjectMocks private OrderService orderService;

    @Test
    void shouldCreateOrder() {
        Order expected = new Order(1L, "PENDING");
        when(orderDao.save(any())).thenReturn(expected);

        Order result = orderService.createOrder(new CreateOrderRequest(1L, 100L));
        assertNotNull(result);
        verify(inventoryService).deduct(100L, 1);
    }
}

// ===== 第二层：集成测试（Controller + Service） =====
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired private MockMvc mockMvc;
    @MockBean private OrderService orderService;

    @Test
    void shouldReturn200() throws Exception {
        when(orderService.findById(1L)).thenReturn(new Order(1L, "PENDING"));

        mockMvc.perform(get("/api/orders/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(1));
    }
}

// ===== 第三层：Repository 测试 =====
@DataJpaTest
class OrderDaoTest {
    @Autowired private TestEntityManager em;
    @Autowired private OrderDao orderDao;

    @Test
    void shouldFindById() {
        Order order = new Order(null, "PENDING");
        Long id = em.persistAndGetId(order, Long.class);

        Optional<Order> found = orderDao.findById(id);
        assertTrue(found.isPresent());
    }
}
```

---

## 🎯 面试高频

### Q1：@Mock 和 @MockBean 的区别？

**答**：
- `@Mock` 是 Mockito 的注解，只创建 Mock 对象，不影响 Spring 容器
- `@MockBean` 是 Spring Boot Test 的注解，**创建 Mock 对象并替换 Spring 容器中同类型的 Bean**。如果有同类型 Bean 已被注册，`@MockBean` 会替换它

```java
// @Mock：单元测试，不用 Spring 容器
@Mock private OrderService orderService;

// @MockBean：集成测试，替换容器中的真实 Bean
@MockBean private OrderService orderService;
```

### Q2：@SpringBootTest 和 @WebMvcTest 的区别？

**答**：
- `@SpringBootTest`：加载完整 ApplicationContext，启动所有 Bean，最重
- `@WebMvcTest(OrderController.class)`：只加载指定的 Controller 和 MVC 相关组件，Service/Repository 需要 `@MockBean`，轻量得多

---

## 📌 在 Spring Boot 中

- Spring Boot Test Starter 包含：JUnit 5 + Mockito + Spring Test + AssertJ + Hamcrest
- `spring-boot-starter-test` 排除了 JUnit 4，统一使用 JUnit 5（`@ExtendWith` 而非 `@RunWith`）
- 测试配置文件：`src/test/resources/application-test.yml` 可以覆盖默认配置
- `@ActiveProfiles("test")` 激活测试专用 Profile，使用 H2 内存数据库或测试数据库

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 纯单元测试 | `@Mock` + `@InjectMocks`，不启动 Spring 容器，最快 |
| @MockBean | 替换 Spring 容器中的 Bean |
| MockMvc | 模拟 HTTP 请求，测试 Controller 层 |
| @DataJpaTest | 只加载 JPA Bean，自动 H2 + 事务回滚 |
| 事务回滚 | `@Transactional` + 测试 = 自动回滚，测试间数据隔离 |
| 核心原则 | 80% 单元测试 + 15% 集成测试 + 5% E2E 测试 |

---

## 学习建议

1. **从今天开始写测试**。不用追求覆盖率，就从你刚写的 Service 开始，加一个最简单的 `@Test`。养成习惯比追求覆盖率更重要。
2. **多用纯单元测试，少用 @SpringBootTest**。启动容器的测试是"慢"的根源——5 个 `@SpringBootTest` 就可能让测试跑到 30 秒。能用 @Mock 搞定就别启动容器。
3. **MockMvc 是 Controller 测试的利器**。不需启动真实服务器就能模拟 HTTP 请求，验证状态码、响应体、请求头——这是 API 接口的"快照测试"。
4. **@Transactional 回滚机制要理解**：测试类上加 `@Transactional`，每个 `@Test` 方法的事务在结束时自动回滚，保证测试之间互不影响——这是你写数据库相关测试的底气。