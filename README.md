# java-note

> 一套面向**系统化学习 Java 后端到 Spring Boot 企业级开发**的完整学习笔记。
> 从 Java SE 基础 → JavaWeb 原理 → Spring Boot 工程实践，覆盖 120+ 篇知识点文档，配套学习路线图与思维导图。

## 📌 项目介绍

这套笔记的核心设计理念是：**JavaWeb 学的是"底层原理"，Spring 学的是"工程效率"**。

- **Java基础**：49 篇，打牢语言根基（OOP、集合、IO、并发、反射、JVM）
- **JavaWeb**：21 篇，理解原生 Servlet/JSP/JDBC 原理——它们是 Spring Boot 的底层实现
- **数据库**：3 篇，MySQL/PostgreSQL/JDBC，数据持久化基础
- **Spring**：54 篇 + 3 篇参考，Spring Boot 企业级开发全套实战
- **思维导图**：6 大领域的知识体系总览

每个知识点都遵循统一结构：**概念 → 语法 → 代码 → ⚠️重点 → 💻实战 → 🚀新版本 → 📌在 Spring Boot 中 → 本章小结**。JavaWeb 每篇文末标注"在 Spring Boot 中对应什么"，让你学底层原理时始终知道将来被什么封装了。

---

## 📚 文档索引

### 一、Java 基础（49 篇）

> 入口：[Java基础/00-学习路线图.md](Java基础/00-学习路线图.md)

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 00 | [学习路线图](Java基础/00-学习路线图.md) | 总导航，由浅入深的学习路径 |
| 01 | [Java概述与开发环境](Java基础/01-Java概述与开发环境.md) | 跨平台原理、JDK/JRE/JVM、环境搭建 |
| 02 | [JVM内存模型](Java基础/02-JVM内存模型.md) | 运行时数据区、堆栈方法区 |
| 03 | [基础语法](Java基础/03-基础语法.md) | 标识符、变量、注释 |
| 04 | [数据类型与类型转换](Java基础/04-数据类型与类型转换.md) | 八大基本类型、自动转换 |
| 05 | [运算符](Java基础/05-运算符.md) | 算术/关系/逻辑/位运算 |
| 06 | [流程控制](Java基础/06-流程控制.md) | if/switch/for/while |
| 07 | [方法](Java基础/07-方法.md) | 定义、重载、参数传递 |
| 08 | [数组与Arrays工具类](Java基础/08-数组与Arrays工具类.md) | 一维/二维数组、Arrays |
| 09 | [类与对象：封装与构造方法](Java基础/09-类与对象：封装与构造方法.md) | OOP 入门、封装 |
| 10 | [static关键字与代码块](Java基础/10-static关键字与代码块.md) | 静态成员、静态代码块 |
| 11 | [继承与final](Java基础/11-继承与final.md) | 继承体系、final 修饰 |
| 12 | [多态](Java基础/12-多态.md) | 向上/向下转型、动态绑定 |
| 13 | [接口](Java基础/13-接口.md) | 接口定义、默认方法 |
| 14 | [内部类](Java基础/14-内部类.md) | 成员/局部/匿名内部类 |
| 15 | [权限修饰符与包](Java基础/15-权限修饰符与包.md) | public/protected/默认/private |
| 16 | [枚举enum](Java基础/16-枚举enum.md) | 枚举定义与使用 |
| 17 | [Object类与Objects](Java基础/17-Object类与Objects.md) | toString/equals/hashCode |
| 18 | [字符串String与StringBuilder](Java基础/18-字符串String与StringBuilder.md) | 字符串不可变、拼接优化 |
| 19 | [包装类](Java基础/19-包装类.md) | 自动装箱拆箱、缓存 |
| 20 | [数学运算：Math与BigDecimal](Java基础/20-数学运算：Math与BigDecimal.md) | 精确运算 |
| 21 | [日期时间](Java基础/21-日期时间.md) | Date/Calendar/新时间 API |
| 22 | [System与Runtime类](Java基础/22-System与Runtime类.md) | 系统属性、运行时 |
| 23 | [异常处理](Java基础/23-异常处理.md) | 受检/非受检异常、try-catch |
| 24 | [集合框架体系与Collection](Java基础/24-集合框架体系与Collection.md) | Collection 体系总览 |
| 25 | [List：ArrayList与LinkedList](Java基础/25-List：ArrayList与LinkedList.md) | List 实现、底层原理 |
| 26 | [Set：HashSet与TreeSet](Java基础/26-Set：HashSet与TreeSet.md) | Set 实现与排序 |
| 27 | [Map：HashMap底层与TreeMap](Java基础/27-Map：HashMap底层与TreeMap.md) | HashMap 原理、红黑树 |
| 28 | [迭代器与增强for](Java基础/28-迭代器与增强for.md) | Iterator、fail-fast |
| 29 | [泛型](Java基础/29-泛型.md) | 泛型方法、通配符 |
| 30 | [Collections工具类与排序](Java基础/30-Collections工具类与排序.md) | 工具方法、Comparator |
| 31 | [数据结构基础](Java基础/31-数据结构基础.md) | 链表/栈/队列/树 |
| 32 | [File类与NIO.2](Java基础/32-File类与NIO.2.md) | 文件操作、Path |
| 33 | [字节流与字符流](Java基础/33-字节流与字符流.md) | InputStream/Reader |
| 34 | [缓冲流与转换流](Java基础/34-缓冲流与转换流.md) | BufferedReader/InputStreamReader |
| 35 | [序列化与打印流](Java基础/35-序列化与打印流.md) | Serializable、PrintStream |
| 36 | [标准IO、RandomAccessFile与Properties](Java基础/36-标准IO、RandomAccessFile与Properties.md) | 随机访问、配置文件 |
| 37 | [线程基础](Java基础/37-线程基础.md) | Thread/Runnable、生命周期 |
| 38 | [线程同步](Java基础/38-线程同步.md) | synchronized、锁 |
| 39 | [线程通信](Java基础/39-线程通信.md) | wait/notify、生产消费 |
| 40 | [JUC并发包](Java基础/40-JUC并发包.md) | CAS、AQS、ConcurrentHashMap |
| 41 | [线程池](Java基础/41-线程池.md) | ThreadPoolExecutor、参数 |
| 42 | [ThreadLocal与异步编程](Java基础/42-ThreadLocal与异步编程.md) | 线程隔离、CompletableFuture |
| 43 | [网络编程](Java基础/43-网络编程.md) | Socket/TCP/UDP |
| 44 | [反射](Java基础/44-反射.md) | Class、动态代理 |
| 45 | [注解](Java基础/45-注解.md) | 元注解、自定义注解 |
| 46 | [函数式编程](Java基础/46-函数式编程.md) | Lambda、Stream、方法引用 |
| 47 | [类加载与SPI](Java基础/47-类加载与SPI.md) | 双亲委派、SPI 机制 |
| 48 | [JUnit单元测试](Java基础/48-JUnit单元测试.md) | JUnit5、断言 |
| 49 | [JVM进阶](Java基础/49-JVM进阶.md) | GC、调优、类文件结构 |

### 二、Java Web（21 篇）

> 入口：[JavaWeb/00-学习路线图.md](JavaWeb/00-学习路线图.md)
> 定位：**面向实际开发，为 Spring Boot 打基础**。原生 Servlet/JSP 现代项目已很少直接手写，但它们是 Spring MVC 的底层实现原理。

| 编号 | 文档 | 核心主题 | Spring Boot 对应 |
| :---: | :--- | :--- | :--- |
| 00 | [学习路线图](JavaWeb/00-学习路线图.md) | 总导航，八大阶段 | — |
| 01 | [Tomcat 与 Web 服务器](JavaWeb/01-Tomcat%20与%20Web%20服务器.md) | B/S 架构、Tomcat 部署 | 内嵌 Tomcat |
| 02 | [Servlet 入门](JavaWeb/02-Servlet%20入门.md) | 生命周期、@WebServlet | DispatcherServlet |
| 03 | [HTTP 协议](JavaWeb/03-HTTP%20协议.md) | 报文、方法、状态码 | @GetMapping/@PostMapping |
| 04 | [Request 请求对象](JavaWeb/04-Request%20请求对象.md) | 取参、乱码、转发 | @RequestParam/@RequestBody |
| 05 | [Response 响应对象](JavaWeb/05-Response%20响应对象.md) | 响应、重定向 | @ResponseBody/ResponseEntity |
| 06 | [Cookie](JavaWeb/06-Cookie.md) | 会话级与持久级 | @CookieValue |
| 07 | [Session](JavaWeb/07-Session.md) | JSESSIONID、超时 | Spring Session + Redis |
| 08 | [Filter 过滤器](JavaWeb/08-Filter%20过滤器.md) | 过滤链、@WebFilter | FilterRegistrationBean |
| 09 | [Listener 监听器](JavaWeb/09-Listener%20监听器.md) | 八大监听器 | @EventListener |
| 10 | [ServletContext 与四大域对象](JavaWeb/10-ServletContext%20与四大域对象.md) | 域对象、容器思想 | ApplicationContext/IoC |
| 11 | [JSP 基础与原理](JavaWeb/11-JSP%20基础与原理.md) | 编译为 Servlet | Thymeleaf |
| 12 | [EL 表达式与 JSTL](JavaWeb/12-EL%20表达式与%20JSTL.md) | EL 取值、JSTL 标签 | Thymeleaf 表达式 |
| 13 | [MVC 设计模式](JavaWeb/13-MVC%20设计模式.md) | Model2、分层架构 | @Controller/@Service |
| 14 | [AJAX 与 JSON](JavaWeb/14-AJAX%20与%20JSON.md) | XHR、JSON、CORS | @RestController |
| 15 | [文件上传下载](JavaWeb/15-文件上传下载.md) | multipart、Part | MultipartFile |
| 16 | [异步 Servlet](JavaWeb/16-异步%20Servlet.md) | AsyncContext、SSE | @Async/DeferredResult |
| 17 | [数据库连接池](JavaWeb/17-数据库连接池.md) | HikariCP/Druid | spring.datasource.* |
| 18 | [Apache DBUtils](JavaWeb/18-Apache%20DBUtils.md) | QueryRunner 简化 JDBC | JdbcTemplate/MyBatis |
| 21 | [综合案例：学生管理系统](JavaWeb/21-综合案例：学生管理系统.md) | 原生技术栈串讲 | Spring Boot 痛点对照 |

### 三、数据库（3 篇）

> 数据持久化基础，建议在 JavaWeb 阶段五后穿插学习。

| 文档 | 核心主题 | Spring Boot 对应 |
| :--- | :--- | :--- |
| [MySQL学习文档](数据库/MySQL学习文档.md) | SQL 增删改查、多表连接、事务索引 | spring.datasource、JPA/MyBatis |
| [JDBC](数据库/JDBC.md) | 六步流程、PreparedStatement、事务 | JdbcTemplate、@Transactional |
| [PostgreSQL学习文档](数据库/PostgreSQL学习文档.md) | PostgreSQL 语法、Spring Boot 集成 | spring.datasource 配置 |

### 四、Spring Boot（54 篇 + 3 篇参考）

> 入口：[Spring/00-学习路线图.md](Spring/00-学习路线图.md)
> 定位：**面向企业级开发**。学完后能独立搭建带数据库、缓存、认证、消息队列、容器化部署的后端服务。

#### 阶段一：工程入门与骨架

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 01 | [SpringBoot入门_HelloWorld](Spring/01-SpringBoot入门_HelloWorld.md) ⭐ | 项目创建、启动原理、内嵌 Tomcat |
| 02 | [读取配置文件_Properties](Spring/02-读取配置文件_Properties.md) ⭐ | application.yml、@Value、profile |
| 03 | [端点监控_Actuator](Spring/03-端点监控_Actuator.md) | 健康检查、指标暴露 |
| 04 | [可视化管控_Admin](Spring/04-可视化管控_Admin.md) | Admin 面板、多实例监控 |
| 05 | [日志集成_Logback](Spring/05-日志集成_Logback.md) ⭐ | Logback 配置、日志规范 |
| 06 | [AOP请求日志_LogAop](Spring/06-AOP请求日志_LogAop.md) ⭐ | AOP 切面、@Around 日志 |
| 07 | [统一异常处理_ExceptionHandler](Spring/07-统一异常处理_ExceptionHandler.md) ⭐ | @ControllerAdvice 全局异常 |

#### 阶段二：Web 接口与视图层

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 08 | [模板引擎_Freemarker](Spring/08-模板引擎_Freemarker.md) | FreeMarker 语法 |
| 09 | [模板引擎_Thymeleaf](Spring/09-模板引擎_Thymeleaf.md) ⭐ | th:text/th:each、HTML 友好 |
| 10 | [模板引擎_Beetl](Spring/10-模板引擎_Beetl.md) | Beetl 国产模板 |
| 11 | [模板引擎_Enjoy](Spring/11-模板引擎_Enjoy.md) | Enjoy 极简模板 |
| 12 | [文件上传_Upload](Spring/12-文件上传_Upload.md) ⭐ | MultipartFile、上传限制 |

#### 阶段三：数据库访问层

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 13 | [数据库操作_JdbcTemplate](Spring/13-数据库操作_JdbcTemplate.md) ⭐ | JdbcTemplate、自动映射 |
| 14 | [数据库操作_JPA](Spring/14-数据库操作_JPA.md) | Spring Data JPA、方法名查询 |
| 15 | [数据库操作_MyBatis](Spring/15-数据库操作_MyBatis.md) ⭐ | @Mapper、XML 映射、resultMap |
| 16 | [MyBatis通用Mapper与分页](Spring/16-MyBatis通用Mapper与分页.md) ⭐ | 通用 Mapper、PageHelper |
| 17 | [数据库操作_MyBatisPlus](Spring/17-数据库操作_MyBatisPlus.md) ⭐ | BaseMapper 通用 CRUD |
| 18 | [数据库操作_BeetlSQL](Spring/18-数据库操作_BeetlSQL.md) | BeetlSQL 国产 ORM |

#### 阶段四：缓存提升性能

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 19 | [Redis缓存_CacheRedis](Spring/19-Redis缓存_CacheRedis.md) ⭐ | @Cacheable、缓存三大问题 |
| 20 | [Ehcache缓存_CacheEhcache](Spring/20-Ehcache缓存_CacheEhcache.md) | 本地堆内缓存、三级 |

#### 阶段五：通用后端能力

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 21 | [邮件服务_Email](Spring/21-邮件服务_Email.md) | JavaMailSender、模板邮件 |
| 22 | [定时任务_Task](Spring/22-定时任务_Task.md) ⭐ | @Scheduled、cron 表达式 |
| 23 | [定时任务_Quartz](Spring/23-定时任务_Quartz.md) | Quartz 调度、集群 |
| 24 | [分布式定时任务_XXL-JOB](Spring/24-分布式定时任务_XXL-JOB.md) | 调度中心、分片广播 |
| 25 | [API文档_Swagger](Spring/25-API文档_Swagger.md) ⭐ | SpringDoc、接口文档 |
| 26 | [增强版API文档_SwaggerBeauty](Spring/26-增强版API文档_SwaggerBeauty.md) | Knife4j 增强 UI |

#### 阶段六：安全与认证

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 27 | [权限控制_RBAC_Security](Spring/27-权限控制_RBAC_Security.md) ⭐ | Spring Security、RBAC、JWT |
| 28 | [统一Session管理_Session](Spring/28-统一Session管理_Session.md) ⭐ | Spring Session、Redis 共享 |
| 29 | [第三方登录_Social](Spring/29-第三方登录_Social.md) | OAuth2、社交登录 |

#### 阶段七：分布式与消息中间件

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 30 | [分布式锁_Zookeeper](Spring/30-分布式锁_Zookeeper.md) | ZK 锁、临时顺序节点 |
| 31 | [消息中间件_RabbitMQ](Spring/31-消息中间件_RabbitMQ.md) ⭐ | Exchange/Queue、可靠投递 |
| 32 | [消息中间件_Kafka](Spring/32-消息中间件_Kafka.md) | Topic/Partition、高吞吐 |

#### 阶段八：实时通信与报表

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 33 | [WebSocket实时通信](Spring/33-WebSocket实时通信.md) | Spring WebSocket、STOMP |
| 34 | [SocketIO实时通信](Spring/34-SocketIO实时通信.md) | Socket.IO、房间机制 |
| 35 | [报表引擎_UReport2](Spring/35-报表引擎_UReport2.md) | 报表设计、导出 |

#### 阶段九：异步与微服务

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 36 | [异步调用_Async](Spring/36-异步调用_Async.md) ⭐ | @Async、ThreadPoolTaskExecutor |
| 37 | [微服务RPC_Dubbo](Spring/37-微服务RPC_Dubbo.md) | Dubbo、Provider/Consumer |
| 38 | [War包部署_War](Spring/38-War包部署_War.md) | 外部 Tomcat 部署 |

#### 阶段十：搜索与 NoSQL

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 39 | [搜索引擎_ElasticSearch](Spring/39-搜索引擎_ElasticSearch.md) | 倒排索引、全文检索 |
| 40 | [文档数据库_MongoDB](Spring/40-文档数据库_MongoDB.md) | 文档模型、Spring Data |
| 41 | [图数据库_Neo4j](Spring/41-图数据库_Neo4j.md) | 图/节点/关系、Cypher |

#### 阶段十一：容器化与多数据源

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 42 | [Docker容器化_Docker](Spring/42-Docker容器化_Docker.md) ⭐ | Dockerfile、镜像构建 |
| 43 | [多数据源_JPA](Spring/43-多数据源_JPA.md) | JPA 多数据源、分包 |
| 44 | [多数据源_MyBatis](Spring/44-多数据源_MyBatis.md) | MyBatis 多数据源 |
| 45 | [分库分表_ShardingJDBC](Spring/45-分库分表_ShardingJDBC.md) | ShardingSphere、分片 |

#### 阶段十二：工程化与运维

| 编号 | 文档 | 核心主题 |
| :---: | :--- | :--- |
| 46 | [代码生成器_Codegen](Spring/46-代码生成器_Codegen.md) | 根据表生成代码 |
| 47 | [日志管理_Graylog](Spring/47-日志管理_Graylog.md) | 日志集中收集 |
| 48 | [目录服务_LDAP](Spring/48-目录服务_LDAP.md) | 企业目录、AD 集成 |
| 49 | [动态数据源_DynamicDataSource](Spring/49-动态数据源_DynamicDataSource.md) | 运行时切换、@DS |
| 50 | [单机限流_RateLimitGuava](Spring/50-单机限流_RateLimitGuava.md) | Guava 令牌桶 |
| 51 | [分布式限流_RateLimitRedis](Spring/51-分布式限流_RateLimitRedis.md) | Redis+Lua 集群限流 |
| 52 | [HTTPS配置_HTTPS](Spring/52-HTTPS配置_HTTPS.md) | 证书、HTTPS 启用 |
| 53 | [ES高级客户端_RestHighLevelClient](Spring/53-ES高级客户端_RestHighLevelClient.md) | ES 复杂查询 |
| 54 | [数据库版本控制_Flyway](Spring/54-数据库版本控制_Flyway.md) ⭐ | 数据库迁移、版本脚本 |

#### 参考文档

| 文档 | 用途 |
| :--- | :--- |
| [Spring Boot 快速上手文档](Spring/Spring%20Boot%20快速上手文档.md) | 速查向总览 |
| [注解速查手册](Spring/注解速查手册.md) | 注解用法速查 |
| [Maven 使用文档](Spring/Maven%20使用文档.md) | 依赖管理参考 |

### 五、思维导图

> 6 大领域知识体系总览。

| 领域 | 目录 |
| :--- | :--- |
| Java 语言 | [思维导图/Java语言](思维导图/Java语言/) |
| 应用框架 | [思维导图/应用框架](思维导图/应用框架/) |
| 数据库 | [思维导图/数据库](思维导图/数据库/) |
| 数据结构和算法 | [思维导图/数据结构和算法](思维导图/数据结构和算法/) |
| 计算机网络 | [思维导图/计算机网络](思维导图/计算机网络/) |
| 设计模式 | [思维导图/设计模式](思维导图/设计模式/) |

---

## 🗺️ 学习路径

推荐按以下顺序系统学习：

1. **Java SE 基础**（[Java基础/00-学习路线图](Java基础/00-学习路线图.md)）—— 至少到集合、IO、异常、并发
2. **JavaWeb 原理**（[JavaWeb/00-学习路线图](JavaWeb/00-学习路线图.md)）—— 理解 Servlet/JSP/JDBC 底层
3. **Spring Boot 工程实践**（[Spring/00-学习路线图](Spring/00-学习路线图.md)）—— 企业级开发全套

> 一句话总结：**JavaWeb 学的是"底层原理"，Spring 学的是"工程效率"。** 原生 Servlet/JDBC 知道得越深，用 Spring Boot 时越知道它在帮你省什么、出了问题才知道往哪查。

---

## 📖 文档约定

- 代码块标注语言：```java / ```xml / ```yaml / ```sql / ```html
- ⭐ 标注：企业开发高频/面试重点，务必吃透
- 「选学」标注：特定场景才用，了解存在即可
- 每篇文档统一结构：概念 → 语法 → 代码 → ⚠️重点 → 💻实战 → 🚀新版本 → 📌在 Spring Boot 中 → 本章小结
- JavaWeb 每篇文末设「📌 在 Spring Boot 中」小节，标注本概念被 Spring Boot 的什么特性封装

---

## 🔗 推荐学习项目

> 本笔记 Spring 篇的案例主要参考 [xkcoding/spring-boot-demo](https://github.com/xkcoding/spring-boot-demo)（每个特性一个独立 demo 模块，好上手）。以下项目可作为补充学习资源。

### 综合实战型（推荐）

| 项目 | 说明 |
| :--- | :--- |
| [macrozheng/mall](https://github.com/macrozheng/mall) | 最火的 Spring Boot 电商项目（50k+ star）。完整商城系统，含 Spring Boot + Spring Cloud + MyBatis + Redis + RabbitMQ + ES + Docker，企业级架构集大成者 |
| [macrozheng/mall-learning](https://github.com/macrozheng/mall-learning) | mall 的配套学习版，拆解 mall 各模块的实现原理，适合跟着学 |
| [macrozheng/springboot-learning-example](https://github.com/macrozheng/springboot-learning-example) | macrozheng 的 Spring Boot 基础示例集，和 spring-boot-demo 定位类似 |

### 示例集型（和 spring-boot-demo 类似）

| 项目 | 说明 |
| :--- | :--- |
| [ityouknow/spring-boot-examples](https://github.com/ityouknow/spring-boot-examples) | Spring Boot 各特性独立示例，每个 example 一个知识点，风格接近 spring-boot-demo |
| [elunez/springboot-example](https://github.com/elunez/springboot-example) | Spring Boot + MyBatis + Shiro 实战示例 |
| [wuyouzhuguli/SpringAll](https://github.com/wuyouzhuguli/SpringAll) | Spring 全家桶教程，从 Spring 到 Spring Boot 到 Spring Cloud |

### 源码与原理型

| 项目 | 说明 |
| :--- | :--- |
| [doocs/source-code-hunter](https://github.com/doocs/source-code-hunter) | Java 主流框架源码分析，含 Spring/Spring Boot/MyBatis，适合"知其所以然" |
| [farmer-hutao/spring-boot-starter-kit](https://github.com/farmer-hutao/spring-boot-starter-kit) | Spring Boot 进阶，讲 Starter 自动配置原理 |

### 最佳实践型

| 项目 | 说明 |
| :--- | :--- |
| [javastacks/spring-boot-best-practice](https://github.com/javastacks/spring-boot-best-practice) | Spring Boot 最佳实践 |
| [dunwu/spring-boot-tutorial](https://github.com/dunwu/spring-boot-tutorial) | Spring Boot 教程，含工程化实践 |

> **使用建议**：继续以本笔记为主线系统学习，学完路线图后用 [macrozheng/mall-learning](https://github.com/macrozheng/mall-learning) 做一个完整项目实战，把所有知识点串起来；[ityouknow/spring-boot-examples](https://github.com/ityouknow/spring-boot-examples) 作为查漏补缺的对照参考。先 demo 后 mall 是合理路径。

---

## 📝 维护信息

- 仓库：[github.com/LeoCharles/java-note](https://github.com/LeoCharles/java-note)
- 持续更新中，欢迎 Star ⭐
