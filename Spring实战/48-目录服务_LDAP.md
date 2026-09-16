# 48 - 目录服务 LDAP 集成

> 对应项目模块：`demo-ldap`
> 前置知识：已学完前面模块，了解 Spring Boot 基本结构、`@Repository`、`@Service`、`@RestController` 的分层套路
> 学习目标：理解 LDAP 是什么、为什么企业用它做统一账号管理，能用 Spring Data LDAP 完成目录数据的 CRUD 和登录认证。

---

## 一、本模块要解决什么问题？

### 1.1 一个常见的企业痛点

想象一家公司有多个系统：OA、邮件、GitLab、VPN、门禁……如果每个系统都自己管一套账号密码，员工入职要开 N 个账号、离职要销 N 个账号、改密码要改 N 处——这是运维噩梦。

**LDAP（Lightweight Directory Access Protocol，轻量目录访问协议）** 就是为解决这个痛点而生的：它是一个**集中式的目录服务**，把全公司的账号信息存在一个树形结构里，所有系统都去 LDAP 查"这个人是谁、密码对不对"。员工入职只开一个 LDAP 账号，所有系统通用；离职删一个，全部失效。这就是**统一身份认证**。

> 💡 前端类比：LDAP 之于后端，有点像前端项目里的"统一身份中心"（如 Auth0 / Keycloak / 自建 SSO）。你登录一次，多个应用共享登录态。LDAP 是更底层、更老牌的方案，很多大厂内部仍在用。

### 1.2 为什么是"目录"而不是"数据库"？

LDAP 把数据组织成**树形目录**（DIT，Directory Information Tree），像文件系统的目录结构。每个条目（Entry）有一个唯一路径叫 **DN（Distinguished Name）**，类似文件的绝对路径。

```
dc=example,dc=org                    ← 根节点（类似 /）
├── ou=people                         ← 组织单元：人员（类似 /people/）
│   ├── uid=zhangsan                  ← 具体用户（类似 /people/zhangsan）
│   ├── uid=lisi
│   └── uid=wangwu
└── ou=group                          ← 组织单元：组
    └── cn=dev
```

- `dc`（Domain Component）：域名分量，`example.org` 拆成 `dc=example,dc=org`
- `ou`（Organizational Unit）：组织单元，类似文件夹
- `uid`/`cn`：具体条目名，类似文件名
- `DN`：完整路径，如 `uid=wangwu,ou=people,dc=example,dc=org`

> 💡 前端类比：DN 就像 DOM 树里节点的完整路径，或文件系统里的绝对路径 `/org/example/people/wangwu`。树形结构天然适合"按层级查"的场景。

### 1.3 LDAP vs 关系型数据库

| 维度 | LDAP | MySQL |
| --- | --- | --- |
| 数据模型 | 树形目录 | 二维表 |
| 查询语言 | LDAP 过滤器 `(uid=wangwu)` | SQL |
| 读/写倾向 | **读多写少**（账号很少改） | 读写均衡 |
| 典型场景 | 统一账号、组织架构、证书存储 | 业务数据 |
| 协议 | 标准协议，跨厂商通用 | 各厂商方言 |

本模块用 Spring Data LDAP 把这个目录树抽象成 Java 对象，像操作数据库一样操作 LDAP。

---

## 二、项目结构

```
demo-ldap/
├── pom.xml
└── src/main/java/com/xkcoding/ldap/
    ├── LdapDemoApplication.java          # 启动类
    ├── api/
    │   ├── Result.java                    # 统一响应体
    │   └── ResultCode.java                # 状态码枚举
    ├── entity/
    │   └── Person.java                    # LDAP 实体（@Entry）
    ├── exception/
    │   └── ServiceException.java          # 业务异常
    ├── repository/
    │   └── PersonRepository.java          # 数据访问层
    ├── request/
    │   └── LoginRequest.java              # 登录请求 DTO
    ├── service/
    │   ├── PersonService.java             # 服务接口
    │   └── impl/PersonServiceImpl.java    # 服务实现
    └── util/
        └── LdapUtils.java                 # 密码校验工具
```

这是一个标准的分层结构：`entity`（实体）→ `repository`（数据层）→ `service`（业务层）→ `api`（响应封装）。注意**没有 `controller` 包**——本模块用测试类驱动，没写 HTTP 接口（实际项目里可自行加 `@RestController`）。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. LDAP 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-ldap</artifactId>
    </dependency>

    <!-- 2. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 3. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
        <scope>provided</scope>
    </dependency>
</dependencies>
```

- `spring-boot-starter-data-ldap`：一个起步依赖，传递引入了 `spring-ldap-core`（LDAP 客户端核心）、`spring-data-ldap`（Spring Data 风格的 LDAP 封装）、`unboundid-ldapsdk`（嵌入式 LDAP 服务器，用于测试）。引一个就拥有了操作 LDAP 的全部能力。
- Lombok 的 `<scope>provided</scope>`：表示编译期用，运行时由环境提供（这里和 `optional` 一起，确保不传递给依赖本模块的项目）。

> 💡 前端类比：这像 `@auth0/nextjs-auth0` 这种"大礼包"依赖，一个包搞定整个认证链路。

---

## 四、配置文件 application.yml

```yaml
spring:
  ldap:
    urls: ldap://localhost:389
    base: dc=example,dc=org
    username: cn=admin,dc=example,dc=org
    password: admin
```

| 配置项 | 含义 | 前端类比 |
| --- | --- | --- |
| `urls` | LDAP 服务器地址，389 是标准端口 | 像 API 的 baseURL `http://localhost:389` |
| `base` | 查询的根路径，所有操作都基于这个路径 | 像 axios 的 baseURL 前缀 |
| `username` | 管理员 DN（用 DN 当用户名） | 像管理员账号 |
| `password` | 管理员密码 | 像管理员密码 |

注意 `username` 是一个 DN（`cn=admin,dc=example,dc=org`），不是简单的用户名字符串——LDAP 里"用户名"就是条目的 DN。这和数据库用 `root`/`admin` 字符串登录不同。

> ⚠️ 生产环境密码不要明文写死，用环境变量 `${LDAP_PASSWORD}` 注入。

---

## 五、核心实体 Person.java

```java
@Data
@Entry(base = "ou=people", objectClasses = {"posixAccount", "inetOrgPerson", "top"})
public class Person implements Serializable {

    @Id
    private Name id;

    @DnAttribute(value = "uid", index = 1)
    private String uid;

    @Attribute(name = "cn")
    private String personName;

    @Attribute(name = "sn")
    private String surname;

    private String userPassword;
    private String givenName;
    private String mail;
    private String title;
    private String uidNumber;
    private String gidNumber;
    private String homeDirectory;
    private String loginShell;
}
```

这是 LDAP 实体映射的核心，逐个注解看：

### 5.1 `@Entry` —— 映射到 LDAP 条目

类似 JPA 的 `@Entity`，但针对 LDAP：

- `base = "ou=people"`：这个实体对应目录树里 `ou=people` 这个组织单元下的条目。
- `objectClasses`：LDAP 条目的"类型"。`posixAccount`（POSIX 账号）、`inetOrgPerson`（互联网组织人员）、`top`（顶层抽象）——这些是 LDAP 预定义的"对象类"，规定了条目可以有哪些属性。类似前端的"接口/类型定义"，规定了对象的结构。

### 5.2 `@Id` —— 主键

```java
@Id
private Name id;
```

LDAP 里条目的唯一标识是它的 **DN**（完整路径），类型是 `javax.naming.Name`。这个字段存的就是 DN，比如 `uid=wangwu,ou=people,dc=example,dc=org`。

### 5.3 `@DnAttribute` —— DN 分量

```java
@DnAttribute(value = "uid", index = 1)
private String uid;
```

告诉 Spring：这个条目 DN 的第一段（`index = 1`）用的是 `uid` 属性的值。这样保存时 Spring 能自动拼出完整 DN：`uid=值,ou=people,dc=example,dc=org`。

### 5.4 `@Attribute` —— 属性名映射

```java
@Attribute(name = "cn")
private String personName;
```

LDAP 属性名是缩写（`cn` = Common Name，`sn` = Surname），Java 字段名想用可读的名字（`personName`），用 `@Attribute(name = "cn")` 建立映射。不写 `@Attribute` 时，默认用字段名作为 LDAP 属性名（如 `mail`、`title`）。

> 💡 前端类比：这像后端返回的字段是缩写 `cn`，前端想用 `personName`，做个字段映射。`@Entry` 像 ORM 的 `@Entity`，`@Attribute` 像 `@Column`。

---

## 六、数据访问层 PersonRepository.java

```java
@Repository
public interface PersonRepository extends CrudRepository<Person, Name> {

    Person findByUid(String uid);
}
```

- 继承 `CrudRepository<Person, Name>`：泛型是 `实体类型` 和 `主键类型`（DN 是 `Name` 类型）。继承后自动拥有 `save`、`findAll`、`delete` 等方法，不用写实现。
- `Person findByUid(String uid)`：**方法名查询**——Spring Data 根据方法名自动生成 LDAP 过滤器。`findByUid` 会生成过滤器 `(uid=传入的值)` 去查。

> 💡 前端类比：这像 React Query / SWR 的约定式查询——你声明"查什么"，框架帮你拼请求。Spring Data 的方法名查询是它最"魔法"的特性，`findByXxx` 自动翻译成对应查询语言。

---

## 七、服务层 PersonService / PersonServiceImpl

### 7.1 接口定义

```java
public interface PersonService {
    Result login(LoginRequest request);
    Result listAllPerson();
    void save(Person person);
    void delete(Person person);
}
```

四个方法：登录、查全部、保存、删除。

### 7.2 实现类

```java
@Slf4j
@Service
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class PersonServiceImpl implements PersonService {
    private final PersonRepository personRepository;
    // ...
}
```

- `@RequiredArgsConstructor(onConstructor_ = @Autowired)`：Lombok 为 `final` 字段生成构造器，`onConstructor_` 让构造器带上 `@Autowired`——这是构造器注入的简化写法（Spring 4.3+ 单构造器可省 `@Autowired`，这里写上更明确）。

### 7.3 登录逻辑（核心）

```java
public Result login(LoginRequest request) {
    Person user = personRepository.findByUid(request.getUsername());

    if (ObjectUtils.isEmpty(user)) {
        throw new ServiceException("用户名或密码错误，请重新尝试");
    } else {
        user.setUserPassword(LdapUtils.asciiToString(user.getUserPassword()));
        if (!LdapUtils.verify(user.getUserPassword(), request.getPassword())) {
            throw new ServiceException("用户名或密码错误，请重新尝试");
        }
    }
    return Result.success(user);
}
```

登录流程：

1. **查用户**：用 `username` 当 `uid` 去 LDAP 查 `Person`。
2. **用户不存在**：抛 `ServiceException`（注意错误信息故意不区分"用户名错"还是"密码错"，防止枚举攻击——这是安全最佳实践）。
3. **密码转换**：LDAP 存的密码可能是 ASCII 码串（如 `49,50,51,52,53,54` 代表 `123456`），先转成字符串。
4. **密码校验**：LDAP 密码通常用 SSHA/SHA 加密存储，不能直接 `equals` 比较，要用 `LdapUtils.verify` 按摘要算法校验。
5. **成功**：返回用户信息。

> 💡 前端类比：这像前端的登录函数——先 `getUserByName`，再 `bcrypt.compare`olla密码。区别是 LDAP 密码用 SSHA（带盐的 SHA-1），校验逻辑见下节。

### 7.4 其他方法

```java
public Result listAllPerson() {
    Iterable<Person> personList = personRepository.findAll();
    personList.forEach(person -> person.setUserPassword(LdapUtils.asciiToString(person.getUserPassword())));
    return Result.success(personList);
}
```

`findAll` 查全部，再把每个的密码转成字符串。注意这里把密码也返回了——**演示用途，生产环境绝对不能返回密码**。

`save` 和 `delete` 直接委托给 `personRepository`。

---

## 八、密码校验工具 LdapUtils.java

这是本模块技术含量最高的类，讲解 LDAP 的 SSHA 密码校验原理。

### 8.1 LDAP 密码存储格式

LDAP（OpenLDAP）默认用 **SSHA（Salted SHA-1）** 存密码，格式是：

```
{SSHA}Base64编码的(SHA-1(密码+盐) + 盐)
```

- `{SSHA}` 前缀标识算法
- 后面是 Base64 编码的字节串：前 20 字节是 SHA-1 摘要，后面是随机盐

### 8.2 校验逻辑

```java
public static boolean verify(String ldapPassword, String inputPassword) throws NoSuchAlgorithmException {
    MessageDigest md = MessageDigest.getInstance("SHA-1");

    // 1. 去掉 {SSHA} 或 {SHA} 前缀
    if (ldapPassword.startsWith("{SSHA}")) {
        ldapPassword = ldapPassword.substring(6);
    } else if (ldapPassword.startsWith("{SHA}")) {
        ldapPassword = ldapPassword.substring(5);
    }

    // 2. Base64 解码
    byte[] ldapPasswordByte = Base64.decode(ldapPassword;

    // 3. 前20字节是SHA摘要，后面是盐
    shaCode = new byte[20];
    salt = new byte[ldapPasswordByte.length - 20];
    System.arraycopy(ldapPasswordByte, 0, shaCode, 0, 20);
    System.arraycopy(ldapPasswordByte, 20, salt, 0, salt.length);

    // 4. 用用户输入的密码 + 取出的盐，重新算摘要
    md.update(inputPassword.getBytes());
    md.update(salt);
    byte[] inputPasswordByte = md.digest();

    // 5. 比较两个摘要是否一致
    return MessageDigest.isEqual(shaCode, inputPasswordByte);
}
```

原理：SSHA 是**带盐的单向哈希**。盐存在密码串里，校验时取出盐，把用户输入的密码用同样的盐重新哈希，比较结果。因为加了随机盐，即使两个用户密码相同，存储的哈希也不同，能防彩虹表攻击。

> 💡 前端类比：这和 `bcrypt.compare(用户输入, 数据库哈希)` 是同一类操作——都是"不可逆哈希 + 盐"的校验。区别是 bcrypt 自带盐管理，SSHA 要手动拆盐。

### 8.3 ASCII 转字符串

```java
public static String asciiToString(String value) {
    String[] chars = value.split(",");
    for (String aChar : chars) {
        sbu.append((char) Integer.parseInt(aChar));
    }
    return sbu.toString();
}
```

LDAP 返回的密码可能是 ASCII 码逗号分隔串（`49,50,51,52,53,54`），每个数字转成对应字符（49→`1`，50→`2`...），拼成 `123456`。

---

## 九、统一响应体 Result / ResultCode / 异常

### 9.1 Result.java

```java
@Data
public class Result<T> implements Serializable {
    private int errcode;
    private String errmsg;
    private T data;

    public static <T> Result<T> success() { ... }
    public static <T> Result<T> success(T data) { ... }
}
```

泛型响应体，`errcode` + `errmsg` + `data` 三段式。用静态工厂方法 `Result.success(data)` 创建成功响应。这是后端 API 的标准封装。

### 9.2 ResultCode.java

```java
@Getter
@AllArgsConstructor
public enum ResultCode {
    SUCCESS(0, "Request Successful"),
    FAILURE(-1, "System Busy");
}
```

状态码枚举，`@AllArgsConstructor` 生成全参构造器。

### 9.3 ServiceException.java

```java
public class ServiceException extends RuntimeException {
    private int errcode;
    private String errmsg;
    // 多个构造器...
}
```

业务异常，继承 `RuntimeException`（非受检异常，不用在方法签名声明 throws）。业务出错时 `throw new ServiceException("xxx")`，配合全局异常处理器（见 `demo-exception-handler`）能统一转成错误响应。

### 9.4 LoginRequest.java

```java
@Data
@Builder
public class LoginRequest {
    private String username;
    private String password;
}
```

`@Builder` 让你能用链式构造：`LoginRequest.builder().username("x").password("y").build()`。

---

## 十、运行与验证

### 10.1 准备 LDAP 服务器

用 Docker 启动 OpenLDAP（README 已给步骤）：

```sh
docker pull osixia/openldap:1.2.5
docker run -p 389:389 -p 636:636 --name my-openldap --detach osixia/openldap:1.2.5
```

- 389 是标准 LDAP 端口，636 是 LDAPS（SSL 加密）端口。
- 默认管理员：`cn=admin,dc=example,dc=org`，密码 `admin`。

### 10.2 准备测试数据

用 `ldapsearch` 或图形化工具（Apache Directory Studio）往 `ou=people` 下添加几个用户，或直接跑测试类的 `saveTest` 先存一个。

### 10.3 跑测试

```java
@Test
public void loginTest() {
    LoginRequest loginRequest = LoginRequest.builder().username("wangwu").password("123456").build();
    Result login = personService.login(loginRequest);
    System.out.println(login);
}
```

先 `saveTest` 存入 `zhaosi`，再 `loginTest` 用 `wangwu` 登录，观察返回的 `Result`。

> ⚠️ 本模块没有 HTTP 接口，全靠测试类验证。实际项目可加 `@RestController` 暴露 `/login`、`/persons` 等接口。

---

## 十一、动手练习

1. **加一个 HTTP 接口**：写 `PersonController`，暴露 `POST /login`、`GET /persons`，用 Postman 测试。
2. **改密码校验**：研究为什么不能直接 `userPassword.equals(inputPassword)`，理解 SSHA 原理。
3. **加分组功能**：在 LDAP 里建 `ou=group`，写 `Group` 实体和 `GroupRepository`，实现"查某用户所属的组"。
4. **用嵌入式 LDAP 测试**：利用 `unboundid-ldapsdk` 在测试里启动内存 LDAP，不依赖外部 Docker，实现真正的单元测试。
5. **对接 Spring Security**：用 `org.springframework.security.ldap` 让 Spring Security 直接从 LDAP 认证，实现"LDAP 账号登录 Web 应用"。
6. **加 LDAPS**：配置 `ldap://` 改成 `ldaps://` + 证书，理解加密传输的重要性。

---

## 十二、本模块知识点总结（结合实际开发详解）

LDAP 在现代项目里虽不如数据库常见，但在企业内部系统、统一身份管理场景仍是基础设施。下面把核心知识点放到真实开发里讲透。

### 12.1 LDAP 的定位：统一身份目录，不是业务数据库

**实际开发中怎么用？**

LDAP 的正确用法是**只存身份相关数据**：账号、密码、姓名、邮箱、所属组、组织架构。业务数据（订单、文章、日志）绝不存 LDAP——它不适合复杂查询和事务。

典型企业架构：

```
应用层（OA/邮件/GitLab/VPN）
        ↓ 查账号、验密码
LDAP 目录（统一身份源）
        ↓ 同步
业务数据库（MySQL，存业务数据，用 uid 关联）
```

**最佳实践：**

1. **LDAP 当"账号源"，MySQL 当"业务源"**：业务表里用 `uid` 字段关联 LDAP 账号，不复制账号信息到业务库。
2. **读多写少才用 LDAP**：账号一年改不了几次，但每天登录上万次——LDAP 对读优化、对写弱化，正好匹配。
3. **不要把 LDAP 当配置中心**：虽然能存配置，但配置频繁变更，LDAP 不擅长。

**常见坑：**

- 把高频变更的业务数据塞进 LDAP，导致写入性能差、复制延迟。
- 以为 LDAP 支持事务——它的事务模型很弱，不适合需要强一致性的业务。

> 💡 前端类比：LDAP 像"组织架构树 + 通讯录"，是只读为主的目录，不是业务数据库。把它当 Active Directory / 企业通讯录用就对了。

### 12.2 DN 与树形路径：LDAP 的核心心智模型

理解 LDAP 必须先理解 DN（Distinguished Name）。DN 是条目的完整路径，**唯一标识一个条目**，类似文件系统的绝对路径。

**DN 的结构（从右到左是根到叶）：**

```
uid=wangwu,ou=people,dc=example,dc=org
│         │         │           │
│         │         │           └─ 域名分量 org
│         │         └───────────── 域名分量 example
│         └─────────────────────── 组织单元 people
└───────────────────────────────── 用户名 wangwu
```

**实际开发要点：**

1. **DN 是主键**：`@Id Name id` 存的就是 DN。增删改都靠 DN 定位条目。
2. **base 配置简化 DN**：`application.yml` 里配 `base: dc=example,dc=org` 后，代码里只需写相对路径 `ou=people`，Spring 自动拼完整 DN。
3. **`@DnAttribute` 决定 DN 拼接**：保存时 Spring 用 `@DnAttribute` 标注的字段值拼 DN，所以这个字段必须填。

**常见坑：**

- 保存时 `uid` 为空，导致拼出的 DN 缺一段，保存失败或覆盖到错误位置。
- 以为 DN 像 SQL 主键自增——LDAP 的 DN 要自己拼，没有自增。
- 删除时只传了部分字段，DN 拼不全，删错条目。

> 💡 前端类比：操作 LDAP 像操作文件系统——你要知道文件路径（DN）才能读写，不能只靠文件名。`base` 配置像 `cd` 到某目录后用相对路径操作。

### 12.3 Spring Data LDAP 的方法名查询

本模块 `PersonRepository` 用了 `findByUid(String uid)`，这是 Spring Data 的"方法名查询"魔法。

**工作原理：** Spring Data 解析方法名，`findBy` 是关键字，`Uid` 是属性名，自动翻译成 LDAP 过滤器 `(uid=参数)`。

**常用方法名模式：**

| 方法名 | 生成的 LDAP 过滤器 |
| --- | --- |
| `findByUid(String)` | `(uid=值)` |
| `findByUidAndMail(String, String)` | `(&(uid=值1)(mail=值2))` |
| `findByUidOrUidNumber(String, String)` | `(\|(uid=值1)(uidNumber=值2))` |
| `findByPersonNameLike(String)` | `(cn=*值*)` |

**最佳实践：**

1. **简单查询用方法名**：一两个条件、等值/模糊查询，方法名最快。
2. **复杂查询用 `@Query`**：多条件、嵌套逻辑，用 `@Query` 注解写原生 LDAP 过滤器：

   ```java
   @Query("(objectClass=inetOrgPerson)")
   List<Person> findAllPersons();
   ```

3. **别过度追求方法名**：方法名太长（`findByUidAndMailAndTitle...`）可读性差，超过 3 个条件改用 `@Query`。

**常见坑：**

- 属性名写错（写成 LDAP 缩写 `cn` 而不是 Java 字段名 `personName`），查不到结果。方法名查询用的是**Java 字段名**，不是 LDAP 属性名。
- 大小写敏感：LDAP 过滤器默认不区分属性名大小写，但值可能区分，排查时容易混淆。

> 💡 前端类比：像 React Query 的约定式 key——你声明"查什么"，框架翻译成请求。但复杂查询还是得手写 fetch。

### 12.4 SSHA 密码校验：为什么不能直接比较

本模块 `LdapUtils.verify` 是密码校验的核心，它揭示了 LDAP 密码存储的安全设计。

**为什么不能 `equals` 比较？**

LDAP（OpenLDAP）默认用 SSHA 存密码，是**单向哈希**——不可逆。存的是 `SHA-1(密码 + 随机盐)`，校验时要把用户输入用同样的盐重新哈希，比较两个哈希值。这和明文存储、可逆加密有本质区别：

| 存储方式 | 安全性 | 校验方式 |
| --- | --- | --- |
| 明文 | 极差 | `equals` |
| 可逆加密（AES） | 一般 | 解密后 `equals` |
| **单向哈希+盐（SSHA/bcrypt）** | **好** | 重新哈希后比较 |

**最佳实践：**

1. **永远不存明文密码**：本模块演示了 SSHA 校验，生产环境用 bcrypt/scrypt/argon2 更现代。
2. **错误信息不区分"用户名错/密码错"**：本模块统一返回"用户名或密码错误"，防止攻击者枚举有效用户名。
3. **登录成功不返回密码**：本模块 `Result.success(user)` 把整个 `Person`（含密码）返回了——**演示用，生产必须把密码字段置空**。

**常见坑：**

- 以为 `userPassword` 字段是明文，直接 `equals`，导致永远登录失败。
- 密码是 ASCII 码串（`49,50,...`），忘了先 `asciiToString` 转换。
- 把密码返回给前端，造成信息泄露。

> 💡 前端类比：这和 `bcrypt.compare(input, hash)` 一模一样——后端存哈希，登录时重新哈希比较。前端同学在 Next.js / Nest.js 里做认证时一定见过。

### 12.5 LDAP 与 Spring Security / SSO 的关系

本模块只是"手动查 LDAP + 手动校验密码"，实际项目里 LDAP 通常和 Spring Security 整合，实现声明式认证。

**实际开发的标准做法：**

```java
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(AuthenticationManagerBuilder auth) throws Exception {
        auth.ldapAuthentication()
            .userDnPatterns("uid={0},ou=people")
            .contextSource()
            .url("ldap://localhost:389/dc=example,dc=org");
    }
}
```

这样 Spring Security 自动处理"查用户 + 校验密码 + 建登录态"，不用手写 `LdapUtils.verify`。

**LDAP 在 SSO（单点登录）中的角色：**

```
用户 → 应用A ──┐
用户 → 应用B ──┼──→ SSO Server ──→ LDAP（统一账号源）
用户 → 应用C ──┘
```

LDAP 是最底层的账号源，SSO Server（如 Keycloak / CAS）在上面封装 OAuth2/SAML 协议，应用只对接 SSO，不直接碰 LDAP。

**最佳实践：**

1. **应用不直接读 LDAP**：通过 SSO 间接用，解耦。
2. **LDAP 只做认证（你是谁），授权（能干什么）在应用内**：LDAP 存账号，权限角色存业务库。
3. **高可用部署 LDAP**：LDAP 挂了所有系统登录都瘫痪，必须主从/集群。

**常见坑：**

- 每个应用都直连 LDAP，LDAP 一挂全线瘫痪——应该加 SSO 中间层做缓存和容灾。
- 把权限角色也塞进 LDAP 的 group，导致授权逻辑分散在目录和应用两处，难维护。

> 💡 前端类比：LDAP 像底层的"用户数据库"，Spring Security 像前端的"路由守卫 + axios 拦截器"，SSO Server 像 Auth0/Keycloak——层层封装，应用层只管业务。

### 12.6 嵌入式 LDAP 与测试

`spring-boot-starter-data-ldap` 传递引入了 `unboundid-ldapsdk`，它提供一个**嵌入式 LDAP 服务器**，能在测试时启动内存 LDAP，不依赖外部 Docker。

**实际开发的测试做法：**

```java
@Test
public void testWithEmbeddedLdap() {
    // 用 @EmbeddedLdapServer 注解启动内存 LDAP
    // 测试完自动关闭，不污染环境
}
```

**最佳实践：**

1. **单元/集成测试用嵌入式 LDAP**：快、隔离、不依赖 CI 环境装 Docker。
2. **端到端测试用真实 OpenLDAP**：验证真实环境兼容性。
3. **测试数据用 LDIF 文件初始化**：LDAP 数据交换格式，像 SQL 的 `init.sql`，测试启动时自动导入。

**常见坑：**

- 测试连真实 LDAP，导致依赖环境、测试不稳定、CI 慢。
- 嵌入式 LDAP 和真实 OpenLDAP 行为有细微差异（如密码加密默认算法），测试通过但生产失败——要用 LDIF 显式指定密码哈希方式。

---

> 📌 **学习建议**：LDAP 对前端工程师是个相对陌生的概念，但它的核心心智模型就是"树形目录 + 路径定位"，理解了 DN 这套就通了。在现代项目里，你更可能通过 Spring Security 或 SSO 间接用 LDAP，而不是像本模块这样手动操作。但理解底层原理，能让你在排查"为什么登录失败""为什么查不到用户"时心里有底。另外，密码校验这一节值得反复看——SSHA/bcrypt 这类"单向哈希+盐"是后端安全的基本功，无论用不用 LDAP 都要掌握。
