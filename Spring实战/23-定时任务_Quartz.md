# 23 - Spring Boot 集成 Quartz 定时任务

> 对应项目模块：`demo-task-quartz`
> 前置知识：已学完前面的 Spring Task 模块（`demo-task`），了解定时任务的基本概念；了解 MyBatis、Controller、Service 分层。
> 学习目标：理解 Quartz 的核心三件套（Job/Trigger/Scheduler），掌握用 Spring Boot 集成 Quartz 并实现定时任务的可视化管理（增删改查、暂停/恢复）。

---

## 一、本模块要解决什么问题？

前面 `demo-task` 模块用 Spring 自带的 `@Scheduled` 实现了定时任务，简单够用。但它有几个硬伤：

1. **任务在代码里写死**：新增/修改一个任务要改代码、重新部署，无法运行时动态管理。
2. **重启即丢失**：`@Scheduled` 的任务状态在内存里，应用重启后任务从零开始，无法记住"上次执行到哪了"。
3. **无法暂停/恢复**：想临时停一个任务，只能注释掉注解重新发布。
4. **单机局限**：多实例部署时，同一个任务每台机器都会执行一次，重复调度。

**Quartz 就是为了解决这些问题而生的**——它是一个功能强大的企业级作业调度框架，支持：

- **持久化**：任务信息存数据库，重启不丢失。
- **运行时管理**：通过 API 动态新增、删除、暂停、恢复任务。
- **集群**：多节点部署时，通过数据库锁保证同一任务只在一个节点执行。
- **Misfire 策略**：错过的任务怎么补偿，可配置。

本模块演示用 Spring Boot 集成 Quartz，并做一个完整的定时任务管理后台：前端页面增删改查任务，后端用 Quartz API + 数据库持久化。

> 💡 前端类比：`@Scheduled` 像前端在代码里写死的 `setInterval`，重启就没了；Quartz 像一个带数据库持久化的任务调度中心（类似 BullMQ + Redis 的任务队列），任务定义存盘、可动态管理、可分布式。

---

## 二、先搞懂 Quartz 的核心概念

在写代码前，必须先理解 Quartz 的"三件套"，否则代码看不懂。

### 2.1 三大核心组件

| 组件 | 作用 | 前端类比 |
| --- | --- | --- |
| **Job（任务）** | 定义"做什么"——一个实现 `Job` 接口的类，`execute` 方法里写业务逻辑 | 一个任务处理函数 |
| **Trigger（触发器）** | 定义"何时做"——用 Cron 表达式或简单间隔描述执行时机 | `setTimeout`/`setInterval` 的时间规则 |
| **Scheduler（调度器）** | 定义"怎么调度"——把 Job 和 Trigger 绑在一起，负责实际触发执行 | 任务队列的调度引擎 |

一句话：**Scheduler 拿着 Trigger 去定时触发 Job**。

### 2.2 JobDetail 和 Job 的区别

- `Job` 是任务逻辑的类（你写的 `HelloJob`）。
- `JobDetail` 是任务的"描述信息"（名字、所属组、Job 数据等），Quartz 用它来实例化 Job。

为什么要分开？因为 Quartz 每次执行 Job 时都会**新建一个 Job 实例**（不是单例），所以需要 JobDetail 携带元信息来创建。

### 2.3 两种 Trigger

| Trigger 类型 | 说明 | 适用场景 |
| --- | --- | --- |
| `SimpleTrigger` | 简单重复：每隔 N 毫秒执行 M 次 | 固定间隔任务 |
| `CronTrigger` | 用 Cron 表达式描述复杂时间 | "每天 2 点执行"、"每月最后一天" |

本模块用的是 `CronTrigger`，因为 Cron 表达式最灵活、实际开发最常用。

### 2.4 Cron 表达式速览

Cron 有 6-7 位（Quartz 用 6 位 + 可选年）：

```
秒 分 时 日 月 周 [年]
*  *  *  *  *  *  [?]
```

常见例子：

| 表达式 | 含义 |
| --- | --- |
| `0/5 * * * * ?` | 每 5 秒执行一次 |
| `0 0 2 * * ?` | 每天凌晨 2 点 |
| `0 0 0 1 * ?` | 每月 1 号 0 点 |
| `0 0/30 * * * ?` | 每 30 分钟 |

> 💡 前端类比：Cron 表达式像更强大的 `cron` npm 包或 Linux crontab 语法，但 Quartz 多了"秒"级精度。注意 Quartz 的周用 `?`（不指定）而不是 `*`，这是和 Linux cron 的一个区别。

---

## 三、项目结构

```
demo-task-quartz/
├── pom.xml
├── init/dbTables/                       # Quartz 持久化用的建表脚本（各数据库）
│   └── tables_mysql_innodb.sql          # MySQL 用这个
└── src/main/
    ├── java/com/xkcoding/task/quartz/
    │   ├── SpringBootDemoTaskQuartzApplication.java   # 启动类
    │   ├── common/ApiResponse.java                    # 统一响应封装
    │   ├── controller/JobController.java             # 任务管理接口
    │   ├── entity/
    │   │   ├── domain/JobAndTrigger.java              # 查询用 VO
    │   │   └── form/JobForm.java                     # 表单参数
    │   ├── job/
    │   │   ├── base/BaseJob.java                      # Job 基类接口
    │   │   ├── HelloJob.java                          # 示例任务1
    │   │   └── TestJob.java                           # 示例任务2
    │   ├── mapper/JobMapper.java                      # MyBatis Mapper
    │   ├── service/JobService.java + impl/JobServiceImpl.java  # 业务层
    │   └── util/JobUtil.java                          # 反射工具类
    └── resources/
        ├── application.yml
        ├── mappers/JobMapper.xml                      # SQL
        └── static/job.html                            # 前端管理页面
```

注意分层：`controller`（接口）→ `service`（业务）→ `mapper`（数据）→ `job`（任务定义）→ `util`（工具）。这是标准的企业级分层结构。

---

## 四、逐行拆解 pom.xml

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-quartz</artifactId>
</dependency>
```

这是核心依赖——`spring-boot-starter-quartz` 自动引入了 Quartz 的 jar，并配置了一个 `Scheduler` Bean 注入 Spring 容器，你直接 `@Autowired` 就能用。

其他依赖：

```xml
<!-- 通用 Mapper（tk.mybatis）：简化单表 CRUD -->
<dependency>
    <groupId>tk.mybatis</groupId>
    <artifactId>mapper-spring-boot-starter</artifactId>
    <version>${mybatis.mapper.version}</version>
</dependency>

<!-- PageHelper：分页插件 -->
<dependency>
    <groupId>com.github.pagehelper</groupId>
    <artifactId>pagehelper-spring-boot-starter</artifactId>
    <version>${mybatis.pagehelper.version}</version>
</dependency>

<!-- MySQL 驱动 -->
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
</dependency>
```

为什么这里要用 MyBatis + 通用 Mapper + PageHelper？因为本模块要**查询任务列表分页展示**，而 Quartz 的任务信息存在数据库的 `QRTZ_*` 表里，需要写 SQL 联表查询。

> 💡 前端类比：这就像前端用 axios 拉数据 + 一个分页组件。这里 MyBatis 是数据访问层，PageHelper 自动给 SQL 加 `LIMIT`，通用 Mapper 免去手写基础 CRUD。

---

## 五、逐行拆解配置文件 application.yml

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?...
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
    type: com.zaxxer.hikari.HikariDataSource
    hikari:
      minimum-idle: 5
      maximum-pool-size: 20
      ...
  quartz:
    job-store-type: jdbc                          # 关键1：任务存数据库
    wait-for-jobs-to-complete-on-shutdown: true   # 关键2：关闭时等任务跑完
    scheduler-name: SpringBootDemoScheduler
    properties:
      org.quartz.threadPool.threadCount: 5         # 线程池大小
      org.quartz.threadPool.threadPriority: 5
      org.quartz.jobStore.misfireThreshold: 5000  # 错过5秒算misfire
      org.quartz.jobStore.class: org.quartz.impl.jdbcjobstore.JobStoreTX
      org.quartz.jobStore.driverDelegateClass: org.quartz.impl.jdbcjobstore.StdJDBCDelegate
      org.quartz.jobStore.acquireTriggersWithinLock: true  # 防止重复调度
```

### 5.1 `job-store-type: jdbc`（最关键）

Quartz 有两种存储模式：

| 模式 | 说明 | 适用场景 |
| --- | --- | --- |
| `memory`（默认） | 任务存内存（RAMJobStore），重启丢失 | 测试、简单场景 |
| `jdbc` | 任务存数据库（JobStoreTX），重启不丢 | **生产环境** |

本模块用 `jdbc`，所以需要先执行建表脚本 `init/dbTables/tables_mysql_innodb.sql`，创建 `QRTZ_JOB_DETAILS`、`QRTZ_TRIGGERS`、`QRTZ_CRON_TRIGGERS` 等表。

### 5.2 `wait-for-jobs-to-complete-on-shutdown: true`

应用关闭时，等当前正在执行的任务跑完再退出，避免任务执行到一半被杀掉导致数据不一致。

### 5.3 线程池配置

```properties
org.quartz.threadPool.threadCount: 5
```

Quartz 用线程池执行任务，`threadCount=5` 表示最多 5 个任务并发。如果任务多或耗时长，要调大。

### 5.4 Misfire 阈值

```properties
org.quartz.jobStore.misfireThreshold: 5000
```

如果一个任务本该在 10:00:00 执行，但调度器忙到 10:00:06 才轮到它，超过 5 秒就算"misfire"（错过），按 Misfire 策略处理（忽略/立即补执行/下次再执行）。

### 5.5 防止重复调度

```properties
org.quartz.jobStore.acquireTriggersWithinLock: true
```

集群部署时，多个节点可能同时拉取到同一个 Trigger。开启这个选项后，拉取 Trigger 时加锁，避免重复执行。这是 Quartz 集群的关键配置。

---

## 六、逐行拆解核心代码

### 6.1 Job 基类和示例任务

`job/base/BaseJob.java`：

```java
public interface BaseJob extends Job {
    @Override
    void execute(JobExecutionContext context) throws JobExecutionException;
}
```

- `Job` 是 Quartz 的核心接口（`org.quartz.Job`）。
- 这里又包了一层 `BaseJob`，目的是**让项目内的任务都实现这个接口**，方便统一管理（比如反射实例化时只认 `BaseJob`）。

`job/HelloJob.java`：

```java
@Slf4j
public class HelloJob implements BaseJob {
    @Override
    public void execute(JobExecutionContext context) {
        log.error("Hello Job 执行时间: {}", DateUtil.now());
    }
}
```

- 任务逻辑写在 `execute` 里，这里只是打印日志。
- 注意 `HelloJob` **没有加 `@Component`**——因为 Quartz 每次执行时自己 `newInstance()` 创建实例，不归 Spring 管。这也是为什么 Job 里**不能直接 `@Autowired` Spring Bean**（实例不是 Spring 创建的）。

> ⚠️ 这是 Quartz + Spring 集成的经典坑：Job 类里注入 Spring Bean 会是 null。解决办法是配置 `SpringBeanJobFactory` 把 Job 实例纳入 Spring 管理，本模块没做这层处理（因为示例 Job 不需要注入 Bean）。实际开发中如果 Job 要调 Service，必须处理这个问题。

### 6.2 反射工具类 JobUtil

`util/JobUtil.java`：

```java
public class BaseJob getClass(String classname) throws Exception {
    Class<?> clazz = Class.forName(classname);
    return (BaseJob) clazz.newInstance();
}
```

- 传入全类名（如 `com.xkcoding.task.quartz.job.HelloJob`），用反射创建实例。
- 为什么用反射？因为前端传过来的是**字符串类名**，后端要动态加载对应的 Job 类。这是"运行时动态添加任务"的关键——你不必在代码里写死用哪个 Job，用户在前端填类名，后端反射加载。

> 💡 前端类比：这就像前端用 `import()` 动态导入模块，或 `new this.registry[name]()` 按字符串实例化类。Java 用 `Class.forName` + `newInstance` 实现同样的"按名加载"。

### 6.3 Service 层：任务管理的核心逻辑

`service/impl/JobServiceImpl.java` 是本模块的核心，逐个方法看。

**构造器注入 Scheduler：**

```java
private final Scheduler scheduler;
private final JobMapper jobMapper;

@Autowired
public JobServiceImpl(Scheduler scheduler, JobMapper jobMapper) {
    this.scheduler = scheduler;
    this.jobMapper = jobMapper;
}
```

`Scheduler` 是 Spring Boot 自动配置注入的（因为引了 `spring-boot-starter-quartz`），直接拿来用。

**新增任务 `addJob`：**

```java
public void addJob(JobForm form) throws Exception {
    scheduler.start();   // 1. 启动调度器

    // 2. 构建 JobDetail（任务详情）
    JobDetail jobDetail = JobBuilder.newJob(
            JobUtil.getClass(form.getJobClassName()).getClass())
        .withIdentity(form.getJobClassName(), form.getJobGroupName())
        .build();

    // 3. 构建 Cron 触发器
    CronScheduleBuilder cron = CronScheduleBuilder.cronSchedule(form.getCronExpression());
    CronTrigger trigger = TriggerBuilder.newTrigger()
        .withIdentity(form.getJobClassName(), form.getJobGroupName())
        .withSchedule(cron)
        .build();

    // 4. 注册到调度器
    scheduler.scheduleJob(jobDetail, trigger);
}
```

四步走：启动调度器 → 建 JobDetail → 建 Trigger → 注册。这是 Quartz 编程式添加任务的标准套路。

- `withIdentity(name, group)`：给 Job/Trigger 起名+分组，Quartz 用 `(name, group)` 唯一标识一个 Job/Trigger。
- `scheduleJob(jobDetail, trigger)`：把两者绑定并交给调度器，之后按 Cron 自动触发。

**删除任务 `deleteJob`：**

```java
public void deleteJob(JobForm form) throws SchedulerException {
    scheduler.pauseTrigger(TriggerKey.triggerKey(...));   // 先暂停触发器
    scheduler.unscheduleJob(TriggerKey.triggerKey(...));  // 取消调度
    scheduler.deleteJob(JobKey.jobKey(...));              // 删除任务
}
```

删除要三步：暂停触发器 → 取消触发器 → 删除 Job。顺序不能乱，否则可能删不干净。

**暂停/恢复任务：**

```java
public void pauseJob(JobForm form) throws SchedulerException {
    scheduler.pauseJob(JobKey.jobKey(form.getJobClassName(), form.getJobGroupName()));
}

public void resumeJob(JobForm form) throws SchedulerException {
    scheduler.resumeJob(JobKey.jobKey(form.getJobClassName(), form.getJobGroupName()));
}
```

一行搞定，`pauseJob`/`resumeJob` 是 Scheduler 提供的现成方法。

**修改 Cron `cronJob`：**

```java
public void cronJob(JobForm form) throws Exception {
    TriggerKey triggerKey = TriggerKey.triggerKey(...);
    CronScheduleBuilder scheduleBuilder = CronScheduleBuilder.cronSchedule(form.getCronExpression());
    CronTrigger trigger = (CronTrigger) scheduler.getTrigger(triggerKey);
    trigger = trigger.getTriggerBuilder().withIdentity(triggerKey).withSchedule(scheduleBuilder).build();
    scheduler.rescheduleJob(triggerKey, trigger);   // 用新 trigger 替换旧的
}
```

修改执行时间 = 重建一个 Trigger 替换原来的，用 `rescheduleJob`。

**查询列表 `list`：**

```java
public PageInfo<JobAndTrigger> list(Integer currentPage, Integer pageSize) {
    PageHelper.startPage(currentPage, pageSize);
    List<JobAndTrigger> list = jobMapper.list();
    return new PageInfo<>(list);
}
```

用 PageHelper 分页，查 `QRTZ_*` 表联表查出任务和触发器信息。

### 6.4 Mapper：联表查询 Quartz 表

`mappers/JobMapper.xml`：

```sql
SELECT
    job_details.`JOB_NAME`, job_details.`JOB_GROUP`, job_details.`JOB_CLASS_NAME`,
    cron_triggers.`CRON_EXPRESSION`, cron_triggers.`TIME_ZONE_ID`,
    qrtz_triggers.`TRIGGER_NAME`, qrtz_triggers.`TRIGGER_GROUP`, qrtz_triggers.`TRIGGER_STATE`
FROM `QRTZ_JOB_DETAILS` job_details
    LEFT JOIN `QRTZ_CRON_TRIGGERS` cron_triggers ON ...
    LEFT JOIN `QRTZ_TRIGGERS` qrtz_triggers ON ...
```

直接查 Quartz 自己的表，把 Job 详情、Cron 表达式、触发器状态联表查出来。`TRIGGER_STATE` 字段表示任务状态（WAITING/ACQUIRED/PAUSED 等）。

### 6.5 Controller：RESTful 接口

```java
@RestController
@RequestMapping("/job")
public class JobController {
    @PostMapping              // 新增
    @DeleteMapping            // 删除
    @PutMapping(params = "pause")   // 暂停（URL 带 pause 参数）
    @PutMapping(params = "resume")  // 恢复
    @PutMapping(params = "cron")    // 改 Cron
    @GetMapping               // 列表
}
```

注意 `@PutMapping(params = "pause")` 这种写法——同一个 `/job` 路径，靠查询参数区分不同操作（`/job?pause`、`/job?resume`、`/job?cron`）。这是 RESTful 的一种变体，用查询参数区分动作。

### 6.6 表单校验 JobForm

```java
@Data
@Accessors(chain = true)
public class JobForm {
    @NotBlank(message = "类名不能为空")
    private String jobClassName;
    @NotBlank(message = "任务组名不能为空")
    private String jobGroupName;
    @NotBlank(message = "cron表达式不能为空")
    private String cronExpression;
}
```

- `@NotBlank` 是 JSR-303 校验注解，配合 Controller 上的 `@Valid` 自动校验参数。
- `@Accessors(chain = true)` 是 Lombok 注解，让 setter 返回 `this`，支持链式调用：`form.setJobClassName("x").setJobGroupName("y")`。

---

## 七、运行与验证

### 7.1 准备数据库

1. 创建数据库 `spring-boot-demo`。
2. 执行 `init/dbTables/tables_mysql_innodb.sql`，创建 Quartz 的 11 张表（`QRTZ_JOB_DETAILS` 等）。

### 7.2 启动

```sh
mvn spring-boot:run
```

### 7.3 访问管理页面

浏览器打开 `http://localhost:8080/demo/job.html`，看到 Element-UI 做的任务管理表格。

### 7.4 测试接口

| 操作 | 请求 |
| --- | --- |
| 新增任务 | `POST /demo/job`，参数 `jobClassName=com.xkcoding.task.quartz.job.HelloJob&jobGroupName=test&cronExpression=0/5 * * * * ?` |
| 查询列表 | `GET /demo/job?currentPage=1&pageSize=10` |
| 暂停 | `PUT /demo/job?pause` |
| 恢复 | `PUT /demo/job?resume` |
| 改 Cron | `PUT /demo/job?cron` |
| 删除 | `DELETE /demo/job` |

新增后看控制台，每 5 秒打印一次 `Hello Job 执行时间: ...`，说明任务在跑。

---

## 八、动手练习

1. **新建一个 Job**：写一个 `CleanCacheJob` 实现 `BaseJob`，`execute` 里打印"清理缓存"，前端填这个类名添加任务，验证能执行。
2. **改 Cron**：把任务的 Cron 从 `0/5 * * * * ?` 改成 `0 0 2 * * ?`（每天 2 点），观察列表里 `CRON_EXPRESSION` 变化。
3. **暂停恢复**：暂停一个运行中的任务，看控制台不再打印；恢复后又开始打印。
4. **重启验证持久化**：添加一个任务后重启应用，刷新列表，任务还在（因为存数据库了）。对比 `@Scheduled` 重启即丢的区别。
5. **查 Quartz 表**：新增任务后，去数据库查 `SELECT * FROM QRTZ_JOB_DETAILS` 和 `QRTZ_TRIGGERS`，看任务数据长什么样。
6. **故意写错 Cron**：添加任务时 Cron 写成 `abc`，观察报错，体会 Cron 校验。

---

## 九、本模块知识点总结（结合实际开发详解）

Quartz 是 Java 生态最成熟的调度框架，理解它对做企业级后台很重要。下面把核心知识点放到真实开发场景里讲透。

### 9.1 Spring Task vs Quartz：怎么选？

**实际开发中的选择标准：**

| 维度 | `@Scheduled`（Spring Task） | Quartz |
| --- | --- | --- |
| 任务管理 | 代码写死，无法运行时增删改 | API 动态管理，可做管理后台 |
| 持久化 | 内存，重启丢失 | 数据库，重启不丢 |
| 集群 | 重复执行（每台都跑） | 数据库锁，只跑一次 |
| Misfire 处理 | 简单 | 多种策略可选 |
| 复杂度 | 极简，一个注解 | 要建表、配置、写 Job 类 |
| 适用场景 | 简单固定任务（日报、清理） | 复杂、动态、分布式任务 |

**最佳实践：**

- 简单的固定任务（每天统计、定时清理）用 `@Scheduled`，够用就好，别过度设计。
- 需要"用户在前端动态配任务"或"多节点部署不能重复跑"时，上 Quartz。
- 超大规模分布式调度（几百上千个任务、跨机房）可以考虑 XXL-JOB（后续模块）或 Elastic-Job，它们在 Quartz 之上做了可视化和管理增强。

**常见坑：** 小项目硬上 Quartz，结果为了几个定时任务建一堆表、写一堆管理代码，维护成本反而高。技术选型要匹配规模。

### 9.2 Job 类不能注入 Spring Bean——经典坑

**问题：** `HelloJob` 是 Quartz 用 `newInstance()` 创建的，不归 Spring 管，所以 Job 里 `@Autowired` 的 Service 是 null，调用就 NPE。

**实际开发的解决方案：**

1. **配置 `SpringBeanJobFactory`**（推荐）：自定义一个 `AutoWiringJobFactory`，让 Quartz 创建的 Job 实例被 Spring 自动注入。

   ```java
   @Component
   public class AutoWiringJobFactory extends SpringBeanJobFactory implements ApplicationContextAware {
       private transient AutowireCapableBeanFactory beanFactory;
       @Override
       public void setApplicationContext(ApplicationContext ctx) {
           beanFactory = ctx.getAutowireCapableBeanFactory();
       }
       @Override
       protected Object createJobInstance(TriggerFiredBundle bundle) throws SchedulerException {
           Object job = super.createJobInstance(bundle);
           beanFactory.autowireBean(job);   // 关键：让 Spring 注入依赖
           return job;
       }
   }
   ```

2. **Job 里用 `ApplicationContext` 静态拿 Bean**：在 Job 的 `execute` 里通过 `SpringUtil.getBean(XxxService.class)` 获取，绕开注入。本模块的 Hutool 就提供了 `SpringUtil`。

3. **Job 不调 Service，只发消息**：Job 执行时往消息队列发个事件，由 Spring 管理的消费者处理业务逻辑，彻底解耦。

**最佳实践：** 生产环境用方案 1，一劳永逸；快速演示用方案 2。

### 9.3 持久化与 Quartz 表结构

**实际开发要点：**

1. **建表脚本别自己写**：Quartz 官方提供各数据库的脚本（`init/dbTables` 目录），直接用。MySQL 用 `tables_mysql_innodb.sql`。
2. **表名前缀 `QRTZ_`**：Quartz 默认表前缀，可通过 `org.quartz.jobStore.tablePrefix` 改，但一般不动。
3. **核心表的作用：**

   | 表 | 存什么 |
   | --- | --- |
   | `QRTZ_JOB_DETAILS` | 任务详情（类名、组、是否持久） |
   | `QRTZ_TRIGGERS` | 触发器（状态、下次执行时间） |
   | `QRTZ_CRON_TRIGGERS` | Cron 表达式 |
   | `QRTZ_LOCKS` | 集群锁（防止重复调度） |
   | `QRTZ_SCHEDULER_STATE` | 调度器实例状态（集群心跳） |

4. **不要手动改 Quartz 表**：任务管理一律走 Scheduler API，直接改表会导致内存状态和数据库不一致。

**常见坑：** 以为删掉 `QRTZ_JOB_DETAILS` 里的行就能删任务，结果 Trigger 还在，调度器启动报错。正确做法是 `scheduler.deleteJob()`。

### 9.4 Misfire 策略：错过的任务怎么办？

**实际开发场景：** 一个任务本该 2:00 执行，但 2:00 时服务器在重启，2:10 才起来，这个错过的任务怎么办？

Quartz 的 Misfire 策略（针对 CronTrigger）：

| 策略 | 行为 |
| --- | --- |
| `MISFIRE_INSTRUCTION_FIRE_NOW` | 立即补执行一次 |
| `MISFIRE_INSTRUCTION_DO_NOTHING` | 忽略，等下次正常触发 |
| `MISFIRE_INSTRUCTION_SMART_POLICY`（默认） | 智能选择 |

**配置方式：**

```java
CronScheduleBuilder cron = CronScheduleBuilder.cronSchedule(expr)
    .withMisfireHandlingInstructionFireAndProceed();   // 错过就立即补执行
```

**最佳实践：**

- 幂等任务（如统计、清理）可以 `FIRE_NOW` 补执行。
- 非幂等任务（如发短信、扣款）用 `DO_NOTHING`，避免重复执行造成业务事故。
- `misfireThreshold`（本模块配 5000ms）决定多久算"错过"，超过这个阈值才触发策略。

**常见坑：** 发送通知类任务配了 `FIRE_NOW`，重启后一次性补发一堆，用户收到一堆重复消息。这类任务务必 `DO_NOTHING`。

### 9.5 集群部署：保证任务只跑一次

**实际开发场景：** 应用部署了 3 个节点，同一个定时任务不能跑 3 次。

Quartz 集群方案：

1. 所有节点连同一个数据库。
2. 每个节点用相同的 `scheduler-name` 和配置。
3. Quartz 通过 `QRTZ_LOCKS` 表加锁，保证同一时刻只有一个节点拉取并执行某个 Trigger。
4. `org.quartz.jobStore.acquireTriggersWithinLock: true`（本模块已配）进一步防止并发拉取。

**集群配置要点：**

- `org.quartz.scheduler.instanceId = AUTO`：每个节点自动生成唯一 ID。
- `org.quartz.jobStore.isClustered = true`：开启集群模式。
- 各节点时间要同步（NTP），否则锁逻辑会乱。

**常见坑：**

- 节点时间不同步，导致任务在错误节点重复执行。
- 一个节点卡住不释放锁，其他节点都等它，任务全停。生产环境要监控 `QRTZ_SCHEDULER_STATE` 的心跳。

### 9.6 动态任务的反射加载与安全

本模块用 `JobUtil.getClass(classname)` 反射加载 Job 类——前端传什么类名就加载什么。这带来灵活性，也有安全隐患。

**实际开发要点：**

1. **限制可加载的类**：不要让用户随便填任意类名（可能加载恶意类），应该维护一个"允许的 Job 类白名单"，只允许从白名单选。
2. **校验类是否实现 BaseJob**：反射加载后 `instanceof BaseJob` 校验，防止加载非 Job 类。
3. **Cron 表达式校验**：添加任务前用 `CronExpression.isValidExpression(expr)` 校验，避免无效 Cron 导致调度异常。

**最佳实践：** 动态任务管理后台要做权限控制（只有管理员能操作）+ 输入校验，这是安全底线。

### 9.7 与 Spring Boot 自动配置的关系

`spring-boot-starter-quartz` 帮你做了：

1. 自动创建 `Scheduler` Bean，按 `application.yml` 的 `spring.quartz.*` 配置。
2. 自动启动调度器。
3. 支持 `jdbc` 模式时自动用 Spring 的 `DataSource`（不用单独配 Quartz 的数据源）。

**实际开发要点：**

- `spring.quartz.job-store-type=jdbc` 后，Spring Boot 启动时如果检测到 Quartz 表不存在会报错，所以**建表脚本必须先执行**。
- 想用编程式配置覆盖自动配置：写一个 `@Configuration` 类，定义 `SchedulerFactoryBean` Bean，Spring Boot 会用它代替自动配置。

---

> 📌 **学习建议**：Quartz 的 API 表面复杂，核心就三件套——Job（做什么）、Trigger（何时做）、Scheduler（怎么调度）。建议先把本模块跑通，在管理页面增删改查几个任务，观察数据库表的变化，建立"任务定义存盘、调度器读盘执行"的直观认识。实际开发中，90% 的定时任务用 `@Scheduled` 就够了，只有遇到"动态管理"或"集群不重复执行"的需求才上 Quartz，别为了用而用。另外务必记住 Job 里注入 Spring Bean 的坑，这是 Quartz + Spring 集成最容易踩的雷。
