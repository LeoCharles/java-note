# 22 - Spring Boot 定时任务（Spring Task）

> 对应项目模块：`demo-task`
> 前置知识：已学完前面模块，了解启动类、`@Configuration`、`@Component`、`application.yml` 基本用法
> 学习目标：掌握用 Spring Boot 自带的 Spring Task 实现定时任务，理解 `@Scheduled` 的三种触发方式、cron 表达式、线程池配置，能独立为项目添加定时任务。

---

## 一、本模块要解决什么问题？

很多业务场景需要"定时自动执行某段代码"，不需要人手动触发，比如：

- 每天凌晨 2 点清理过期数据
- 每 10 秒同步一次缓存
- 每小时统计一次报表
- 启动后延迟 5 秒开始，每 4 秒执行一次心跳检测

前端同学对 `setInterval`、`setTimeout` 肯定不陌生，它们是浏览器/Node.js 里的定时器。但后端的定时任务有几个不同点：

| 维度 | 前端 setInterval | 后端定时任务 |
| --- | --- | --- |
| 运行环境 | 浏览器/Node 进程 | 服务器 JVM 进程 |
| 触发方式 | 固定间隔 | 固定间隔 / 固定延迟 / cron 表达式 |
| 进程重启 | 定时器丢失 | 需要重新加载 |
| 多实例问题 | 无 | 多台服务器会重复执行（需分布式锁） |
| 持久化 | 无 | 高级方案支持持久化（Quartz/XXL-JOB） |

本模块用 Spring Boot 自带的 **Spring Task**（也叫 `@Scheduled` 注解方案）实现，它是 JDK `ScheduledExecutorService` 的封装，**零额外依赖、开箱即用**，适合单机、轻量级的定时任务场景。

本模块最终效果：启动后控制台会按三种不同节奏（cron、fixedRate、fixedDelay）打印日志，且任务跑在自定义线程池（20 个线程，名为 `Job-Thread-N`）里，而不是阻塞主线程。

---

## 二、项目结构

```
demo-task/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/task/
    │   ├── SpringBootDemoTaskApplication.java   # 启动类
    │   ├── config/
    │   │   └── TaskConfig.java                  # 定时任务配置（线程池 + @EnableScheduling）
    │   └── job/
    │       └── TaskJob.java                     # 定时任务定义（3 个 @Scheduled 方法）
    └── resources/
        └── application.yml                       # 配置（含注释掉的等价配置）
```

注意分层：`config` 放配置类，`job` 放任务定义。这是真实项目的常见组织方式——把"任务调度配置"和"具体任务逻辑"分开，便于维护。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. commons-lang3，提供 BasicThreadFactory -->
    <dependency>
        <groupId>org.apache.commons</groupId>
        <artifactId>commons-lang3</artifactId>
    </dependency>

    <!-- 3. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 4. Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 5. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

**关键点：没有专门的 `spring-boot-starter-quartz` 或调度依赖。** 因为 Spring Task 是 `spring-context` 的一部分，而 `spring-boot-starter-web` 已经传递引入了 `spring-context`，所以 `@EnableScheduling`、`@Scheduled` 这些注解开箱即用，不需要额外引包。

- `commons-lang3`：本模块用它的 `BasicThreadFactory` 来给线程命名（`Job-Thread-1`、`Job-Thread-2`...），方便排查线程问题。实际开发中也可以用 JDK 自带的 `ThreadFactory` 替代。
- 其余依赖（Lombok、Hutool）和前面模块作用一致。

> 💡 前端类比：Spring Task 之于 Quartz，就像 `setInterval` 之于 node-schedule 或 Bull 队列——简单场景用内置的就够，复杂场景（持久化、分布式、失败重试）才上重型框架。

---

## 四、启动类

`SpringBootDemoTaskApplication.java`：

```java
@SpringBootApplication
public class SpringBootDemoTaskApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoTaskApplication.class, args);
    }
}
```

启动类很简洁，**没有**直接写 `@EnableScheduling`。本模块把开启调度的注解放在了 `TaskConfig` 配置类上。两种写法都可以：

- 写在启动类上：全局开启，简单直接。
- 写在 `@Configuration` 配置类上：职责分离，配置集中管理，更适合多配置类的中大型项目。

> 💡 前端类比：这就像在 `main.ts` 里全局注册插件，还是在单独的 `plugins/scheduler.ts` 里注册——后者更模块化。

---

## 五、核心配置类 TaskConfig（重点）

`config/TaskConfig.java`：

```java
@Configuration
@EnableScheduling
@ComponentScan(basePackages = {"com.xkcoding.task.job"})
public class TaskConfig implements SchedulingConfigurer {
    @Override
    public void configureTasks(ScheduledTaskRegistrar taskRegistrar) {
        taskRegistrar.setScheduler(taskExecutor());
    }

    @Bean
    public Executor taskExecutor() {
        return new ScheduledThreadPoolExecutor(20, new BasicThreadFactory.Builder().namingPattern("Job-Thread-%d").build());
    }
}
```

这是本模块最核心的类，逐行拆解：

### 5.1 `@Configuration` + `@EnableScheduling`

- `@Configuration`：标记为配置类，会被 Spring 容器管理，里面的 `@Bean` 方法会被调用注册 Bean。
- `@EnableScheduling`：**开启定时任务支持的关键注解**。它会让 Spring 扫描容器中所有 `@Scheduled` 注解的方法，并注册到调度器。不加这个注解，`@Scheduled` 不生效。

> ⚠️ 这是新手最常踩的坑：写了 `@Scheduled` 但忘了加 `@EnableScheduling`，任务根本不执行，也不报错，很难排查。

### 5.2 `@ComponentScan(basePackages = {"com.xkcoding.task.job"})`

显式指定扫描 `job` 包下的组件。其实启动类在 `com.xkcoding.task` 包下，默认就能扫到子包 `job`，这里写出来是为了强调"任务类要被扫描到"。**实际开发中，只要启动类在根包下，通常不用显式写 `@ComponentScan`**。

### 5.3 实现 `SchedulingConfigurer` 接口

```java
public class TaskConfig implements SchedulingConfigurer {
    @Override
    public void configureTasks(ScheduledTaskRegistrar taskRegistrar) {
        taskRegistrar.setScheduler(taskExecutor());
    }
```

- `SchedulingConfigurer` 是 Spring 提供的回调接口，允许你**自定义调度器**（默认是单线程的）。
- `configureTasks` 方法在 Spring 注册定时任务时被调用，我们通过 `taskRegistrar.setScheduler(taskExecutor())` 把默认的单线程调度器换成自定义的线程池。

**为什么要换线程池？** 这是本模块的核心知识点：

Spring Task **默认是单线程执行**所有定时任务的。也就是说，如果有 3 个任务，其中 job1 执行慢（比如耗时 30 秒），那么 job2、job3 必须等 job1 跑完才能执行——任务之间会互相阻塞。这在生产环境是不可接受的。

> 💡 前端类比：这就像 `setInterval` 的回调如果执行很慢，会阻塞后续回调。但 JS 是单线程事件循环，而后端 Java 可以用线程池并行执行多个任务，所以我们要显式配置线程池来"并行化"。

### 5.4 自定义线程池

```java
@Bean
public Executor taskExecutor() {
    return new ScheduledThreadPoolExecutor(20, new BasicThreadFactory.Builder().namingPattern("Job-Thread-%d").build());
}
```

- `ScheduledThreadPoolExecutor(20, ...)`：创建一个有 20 个核心线程的调度线程池。这样最多 20 个任务可以并行执行，互不阻塞。
- `BasicThreadFactory.Builder().namingPattern("Job-Thread-%d").build()`：给线程池里的线程命名，`%d` 是自增序号，生成的线程名是 `Job-Thread-1`、`Job-Thread-2`...

**为什么要给线程命名？** 当线上出问题（比如 CPU 飙高、死锁）用 `jstack` 打印线程栈时，有意义的线程名能让你一眼看出"这是定时任务的线程"，而不是匿名的 `pool-1-thread-3`。这是生产排查的基本功。

### 5.5 等价的 yml 配置方式

本模块的 `TaskConfig` 其实可以用配置文件替代，`application.yml` 里注释掉的部分就是等价写法：

```yaml
spring:
  task:
    scheduling:
      pool:
        size: 20                 # 线程池大小，等同 new ScheduledThreadPoolExecutor(20)
      thread-name-prefix: Job-Thread-   # 线程名前缀
```

**两种方式怎么选？**

| 方式 | 优点 | 缺点 |
| --- | --- | --- |
| yml 配置（推荐） | 简洁、不写代码、改配置不用重新编译 | 灵活性稍低 |
| `TaskConfig` 代码配置 | 灵活，可定制线程工厂、拒绝策略等 | 要写代码 |

实际开发中，**简单场景用 yml 配置即可**；如果需要定制拒绝策略、线程工厂、监控，才用代码配置。本模块用代码配置是为了演示原理。

---

## 六、定时任务定义 TaskJob（重点）

`job/TaskJob.java`：

```java
@Component
@Slf4j
public class TaskJob {

    /**
     * 按照标准时间来算，每隔 10s 执行一次
     */
    @Scheduled(cron = "0/10 * * * * ?")
    public void job1() {
        log.info("【job1】开始执行：{}", DateUtil.formatDateTime(new Date()));
    }

    /**
     * 从启动时间开始，间隔 2s 执行
     * 固定间隔时间
     */
    @Scheduled(fixedRate = 2000)
    public void job2() {
        log.info("【job2】开始执行：{}", DateUtil.formatDateTime(new Date()));
    }

    /**
     * 从启动时间开始，延迟 5s 后间隔 4s 执行
     * 固定等待时间
     */
    @Scheduled(fixedDelay = 4000, initialDelay = 5000)
    public void job3() {
        log.info("【job3】开始执行：{}", DateUtil.formatDateTime(new Date()));
    }
}
```

### 6.1 前置注解

- `@Component`：把 `TaskJob` 注册成 Spring Bean，这样 `@Scheduled` 方法才会被扫描注册。**不加 `@Component`，任务不执行。**
- `@Slf4j`：Lombok 注解，自动注入 `log` 对象，省得手写 `LoggerFactory.getLogger(...)`。

### 6.2 三种触发方式（核心对比）

本模块用三个方法演示了 `@Scheduled` 的三种触发方式，这是必须彻底理解的知识点：

#### 方式一：`cron` 表达式

```java
@Scheduled(cron = "0/10 * * * * ?")
public void job1() { ... }
```

`cron` 是最灵活、最常用的方式，按"标准时间"触发，和具体执行耗时无关。

`"0/10 * * * * ?"` 的含义：从第 0 秒开始，每 10 秒执行一次。即每分钟的 0、10、20、30、40、50 秒触发。

**cron 表达式 6/7 位字段**（Spring 用 6 位：秒 分 时 日 月 周）：

| 位置 | 字段 | 取值范围 | 允许的特殊字符 |
| --- | --- | --- | --- |
| 1 | 秒 | 0-59 | `, - * /` |
| 2 | 分 | 0-59 | `, - * /` |
| 3 | 时 | 0-23 | `, - * /` |
| 4 | 日 | 1-31 | `, - * ? / L W C` |
| 5 | 月 | 1-12 或 JAN-DEC | `, - * /` |
| 6 | 周 | 0-7 或 SUN-SAT（0和7都是周日） | `, - * ? / L #` |

**特殊字符含义：**

- `*`：任意值（每秒/每分/每小时...）
- `?`：不指定（只能用在日和周，因为这两个会冲突，二选一用 `?`）
- `/`：步长，`0/10` 表示从 0 开始每 10 个单位
- `-`：范围，`10-12` 表示 10 到 12
- `,`：枚举，`MON,WED,FRI` 表示周一三五
- `L`：最后（last），`6L` 表示本月最后一个周五
- `W`：最近工作日，`15W` 表示离 15 号最近的工作日

**常见 cron 示例：**

| 表达式 | 含义 |
| --- | --- |
| `0 0 2 * * ?` | 每天凌晨 2 点 |
| `0 0/30 * * * ?` | 每半小时 |
| `0 0 9-18 * * MON-FRI` | 工作日早 9 到晚 6 点整点 |
| `0 0 0 1 * ?` | 每月 1 号 0 点 |
| `0 0 10 ? * 6L` | 每月最后一个周五 10 点 |

> 💡 前端类比：cron 类似 Linux 的 crontab，也像 node-cron 库的表达式。前端同学如果用过 GitHub Actions 的 `schedule.cron`，语法几乎一样（不过 GitHub Actions 用 5 位，没有秒）。

#### 方式二：`fixedRate` 固定间隔

```java
@Scheduled(fixedRate = 2000)
public void job2() { ... }
```

`fixedRate = 2000` 表示**每 2000 毫秒（2 秒）触发一次**，从启动那一刻开始计时。

**关键理解：fixedRate 是"计划间隔"，不是"实际间隔"。** 它的理想状态是每 2 秒一次，但如果任务执行耗时超过 2 秒，会出现两种情况：

- **单线程下**：前一次没执行完，后一次会延迟到前一次执行完后立即触发（不会并发执行同一任务）。
- **多线程下（本模块配了线程池）**：理论上可以并发，但 Spring 默认对同一个 `@Scheduled` 方法不会并发执行（除非加 `@Async`）。

> 💡 前端类比：`fixedRate` 类似 `setInterval(fn, 2000)`——它希望每 2 秒触发，但如果 `fn` 执行慢，定时器会"堆积"或延迟。

#### 方式三：`fixedDelay` 固定延迟

```java
@Scheduled(fixedDelay = 4000, initialDelay = 5000)
public void job3() { ... }
```

- `fixedDelay = 4000`：**前一次执行结束后，等待 4 秒，再触发下一次**。延迟是从"上一次结束"算起，不是从"上一次开始"算起。
- `initialDelay = 5000`：首次执行的延迟，启动后等 5 秒再执行第一次。

**fixedRate vs fixedDelay 的区别（必考）：**

| 维度 | fixedRate | fixedDelay |
| --- | --- | --- |
| 计时起点 | 上一次**开始**时 | 上一次**结束**时 |
| 含义 | 固定频率（理想） | 固定间隔（实际） |
| 任务耗时影响 | 可能堆积/延迟 | 永远间隔固定 |
| 适用场景 | 固定节奏采集、不关心耗时 | 必须等上次完成（如轮询拉取） |

举例：任务耗时 3 秒，间隔设 2 秒：
- `fixedRate=2000`：理想 0s、2s、4s... 触发，但实际 0s 开始执行，3s 才结束，下一次最快 3s 触发（被推迟）。
- `fixedDelay=2000`：0s 开始，3s 结束，再等 2 秒，5s 触发下一次。

#### 三种方式对比表

| 方式 | 触发依据 | 灵活性 | 典型用途 |
| --- | --- | --- | --- |
| `cron` | 标准时间点 | 最高（可精确到日/月/周） | 定时报表、凌晨清理 |
| `fixedRate` | 上次开始 + 间隔 | 中 | 固定频率采集 |
| `fixedDelay` | 上次结束 + 间隔 | 中 | 轮询、串行处理 |

---

## 七、配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
# 下面的配置等同于 TaskConfig
#spring:
#  task:
#    scheduling:
#      pool:
#        size: 20
#      thread-name-prefix: Job-Thread-
```

注释掉的部分是 `TaskConfig` 的等价 yml 配置。本模块用代码配置生效，yml 注释仅作对照。实际开发中二选一即可，不要同时配置（可能冲突）。

---

## 八、运行与验证

### 8.1 启动

```sh
mvn spring-boot:run
```

### 8.2 观察控制台日志

启动后控制台会持续打印（节选）：

```
[Job-Thread-1] 【job1】开始执行：2024-01-01 10:00:00
[Job-Thread-2] 【job2】开始执行：2024-01-01 10:00:00
[Job-Thread-3] 【job3】开始执行：2024-01-01 10:00:05   ← 延迟 5 秒后首次
[Job-Thread-1] 【job2】开始执行：2024-01-01 10:00:02   ← job2 每 2 秒
[Job-Thread-2] 【job3】开始执行：2024-01-01 10:00:09   ← job3 上次 10:00:05 结束+4 秒
[Job-Thread-3] 【job1】开始执行：2024-01-01 10:00:10   ← job1 每 10 秒整点
```

**验证要点：**

1. 三个任务并行执行（不同 `Job-Thread-N`），不互相阻塞——证明线程池配置生效。
2. job1 每 10 秒整点触发（cron 按标准时间）。
3. job2 每 2 秒触发（fixedRate）。
4. job3 启动后 5 秒首次触发，之后每 4 秒一次（fixedDelay + initialDelay）。

### 8.3 没有对外接口

注意本模块没有 Controller，定时任务是"后台自动执行"的，不需要 HTTP 请求触发。这也是定时任务和普通接口的区别——它是"推"模式（到点就跑），不是"拉"模式（请求才跑）。

---

## 九、动手练习

1. **加一个 cron 任务**：在 `TaskJob` 里加一个 `@Scheduled(cron = "0 0 2 * * ?")` 的方法，模拟"每天凌晨 2 点清理日志"，观察（可以临时改成每分钟 `0 * * * * ?` 方便观察）。
2. **对比 fixedRate 和 fixedDelay**：写两个方法，方法体里 `Thread.sleep(3000)`（模拟耗时 3 秒），间隔都设 2 秒，一个用 fixedRate 一个用 fixedDelay，观察日志时间戳，体会两者差异。
3. **改线程池大小**：把 `TaskConfig` 的线程池从 20 改成 1，重启，观察三个任务是否开始互相阻塞（job1 慢会影响 job2、job3）。
4. **用 yml 替代代码配置**：注释掉 `TaskConfig` 的 `taskExecutor()` 和 `configureTasks`，改用 `application.yml` 的 `spring.task.scheduling.pool.size=20`，验证效果一致。
5. **故意不加 @EnableScheduling**：把 `TaskConfig` 上的 `@EnableScheduling` 注释掉，重启，观察任务是否还执行（应该不执行），体会这个注解的必要性。
6. **给任务加异常**：在某个 job 方法里 `throw new RuntimeException("故意出错")`，观察后续是否还继续执行（Spring Task 默认遇到异常会终止该任务后续调度，这是个大坑，见知识点总结）。

---

## 十、本模块知识点总结（结合实际开发详解）

定时任务是后端常见需求，Spring Task 是最轻量的方案。下面把核心知识点放到真实开发场景里讲透。

### 10.1 Spring Task 的适用边界：什么时候用它，什么时候不该用？

**实际开发中怎么用？**

Spring Task 适合**单机、轻量、无需持久化**的定时任务，比如：

- 单体应用里每分钟刷新本地缓存
- 每天凌晨清理临时文件
- 定时发送邮件/消息

**什么时候不该用 Spring Task？**

| 场景 | 问题 | 应该用 |
| --- | --- | --- |
| 多实例部署（集群） | 每台机器都会执行，任务重复 | Quartz 集群 / XXL-JOB / Elastic-Job |
| 需要任务持久化 | 重启后任务执行历史丢失 | Quartz（配数据库） / XXL-JOB |
| 需要失败重试、失败告警 | Spring Task 无内置机制 | XXL-JOB |
| 需要动态增删任务 | `@Scheduled` 是静态的，改 cron 要重启 | Quartz / XXL-JOB |
| 需要任务编排（A 完成后执行 B） | Spring Task 不支持 | XXL-JOB 子任务 / 工作流引擎 |

**最佳实践：**

- 小项目、单机：Spring Task 足够，别过度设计。
- 微服务、多实例：上 XXL-JOB（后续模块会讲），它有调度中心统一管理，天然解决重复执行问题。
- 如果用 Spring Task 又要部署多实例，必须配合分布式锁（Redis/Zookeeper）保证只执行一次。

**常见坑：** 直接把 Spring Task 部署到多台服务器，结果定时任务在每台机器都执行一次，比如发短信发了 N 份、数据同步了 N 遍。这是没有分布式协调的典型事故。

### 10.2 `@EnableScheduling` 与 `@Scheduled` 的关系

- `@EnableScheduling` 是**总开关**，开启调度支持，注册 `ScheduledAnnotationBeanPostProcessor` 这个后置处理器。
- `@Scheduled` 是**方法级标记**，标在具体方法上声明触发规则。
- 后置处理器启动时扫描所有 Bean 的 `@Scheduled` 方法，注册到 `ScheduledTaskRegistrar`。

**最佳实践：** `@EnableScheduling` 只需加一次（启动类或一个配置类），不要多处重复加。`@Scheduled` 方法所在类必须是 Spring Bean（加 `@Component` 或在 `@Configuration` 里 `@Bean` 声明）。

**常见坑：**

- `@Scheduled` 方法在非 Bean 类里（比如手动 `new` 出来的对象），不会被扫描，任务不执行。
- `@Scheduled` 方法是 `private` 的，Spring 代理调用不到（虽然 Spring Task 用的是反射，部分情况能跑，但不符合规范，应保持 `public`）。

### 10.3 三种触发方式的精确理解（必考）

**fixedRate（固定频率）：**

- 含义：理想情况下，从上一次**开始**执行算起，每 N 毫秒触发一次。
- 单线程下：如果任务执行超过 N，下一次会推迟到上次执行完立即触发，不会并发。
- 多线程下：理论上可并发，但 Spring 默认不并发执行同一个 `@Scheduled` 方法（除非加 `@Async`）。
- 适用：固定频率采集数据，不关心上次是否完成。

**fixedDelay（固定延迟）：**

- 含义：从上一次**结束**算起，等 N 毫秒再触发下一次。
- 保证：任务间隔永远 ≥ N，不会堆积。
- 适用：轮询拉取、串行处理，必须等上次完成。

**cron（标准时间）：**

- 含义：按标准时间点触发，和执行耗时、上次结束时间无关。
- 灵活：可精确到秒/分/时/日/月/周，但**不能表达"每 N 秒"这种相对时间**（除非用 `0/N`）。
- 注意：cron 是按服务器本地时区的标准时间，跨时区部署要注意。

**最佳实践：**

- 需要"每天某时某分"用 cron。
- 需要"每隔 N 秒"且不关心耗时用 fixedRate。
- 需要"上次完成后等 N 秒"用 fixedDelay。
- fixedRate/fixedDelay 的值可以用 yml 注入：`@Scheduled(fixedRateString = "${task.interval:2000}")`，支持配置化和默认值。

**常见坑：**

- 混淆 fixedRate 和 fixedDelay，导致任务节奏和预期不符。
- cron 表达式写错（日和周冲突没用 `?`），启动时报错或任务不执行。
- cron `0 0 2 * * ?` 想表达"每天 2 点"，结果写成 `0 2 * * * ?`（每小时的第 2 分）——字段顺序记错。

### 10.4 线程池配置：为什么默认单线程是个坑？

Spring Task 默认用单线程调度器（`Executors.newSingleThreadScheduledExecutor()`）。这意味着所有 `@Scheduled` 任务串行执行，一个慢任务会阻塞所有其他任务。

**实际开发中的配置策略：**

1. **简单场景用 yml**：

   ```yaml
   spring:
     task:
       scheduling:
         pool:
           size: 10
         thread-name-prefix: task-
   ```

2. **需要精细控制用代码**：定制线程工厂、拒绝策略、队列大小。

3. **线程数怎么定？** 不是越大越好。定时任务通常是 IO 密集（查库、调接口），可以适当多些（CPU 核数 × 2~5）；如果是 CPU 密集，接近 CPU 核数即可。过多线程会上下文切换开销大。

**最佳实践：**

- 永远显式配置线程池，不要用默认单线程。
- 给线程起有意义的名字（`thread-name-prefix`），方便 jstack 排查。
- 重要任务和次要任务可以分到不同线程池，避免互相影响。

**常见坑：**

- 用默认单线程，job1 卡死（比如调外部接口超时），整个应用所有定时任务停摆，但应用本身还"活着"，监控不易发现。
- 线程数配太大，任务又都是 CPU 密集，导致 CPU 飙高、响应变慢。

### 10.5 异常处理：Spring Task 的"沉默杀手"

**默认行为：** `@Scheduled` 方法抛出未捕获异常时，Spring Task 会**终止该任务的后续调度**（在 ScheduledThreadPoolExecutor 层面，异常导致任务被移除）。而且默认不会有明显报错日志，非常隐蔽。

**实际开发中的处理方案：**

1. **方法内 try-catch**：最简单，捕获所有异常，记录日志，保证不抛出。

   ```java
   @Scheduled(cron = "0 0 2 * * ?")
   public void cleanData() {
       try {
           // 业务逻辑
       } catch (Exception e) {
           log.error("清理数据失败", e);
           // 不抛出，保证下次还能执行
       }
   }
   ```

2. **统一异常处理器**：实现 `SchedulingConfigurer`，自定义 `ErrorHandler`：

   ```java
   @Override
   public void configureTasks(ScheduledTaskRegistrar taskRegistrar) {
       taskRegistrar.setErrorHandler(throwable -> log.error("定时任务异常", throwable));
   }
   ```

3. **配合告警**：异常时发邮件/钉钉通知，避免任务"静默死亡"。

**最佳实践：** 每个定时任务方法体最外层必须 try-catch，绝不让异常逃逸。这是用 Spring Task 的铁律。

**常见坑：** 任务跑了一段时间后突然不再执行，查日志发现几天前某次异常后就没再触发——就是异常导致任务被移除。这是 Spring Task 最隐蔽的坑。

### 10.6 动态化与可观测性：Spring Task 的短板

**动态化：** `@Scheduled` 的 cron 是写死在注解里的，改 cron 要改代码重新部署。实际开发中如果需要动态调整：

- 简单方案：cron 用 yml 配置 `@Scheduled(cron = "${job.cron}")`，改配置重启生效（不是热更新）。
- 真正动态：用 `TaskScheduler` API 编程式注册任务，或上 Quartz/XXL-JOB。

**可观测性：** Spring Task 没有内置的任务监控面板，你不知道：

- 任务执行了没有
- 执行了多久
- 成功还是失败
- 下次什么时候执行

**实际开发的补强方案：**

- 用 AOP 切面拦截 `@Scheduled` 方法，记录执行日志、耗时、异常（类似 `demo-log-aop` 的思路）。
- 接入 Actuator，自定义指标暴露任务执行情况。
- 重要任务上 XXL-JOB，它自带执行日志、失败告警、任务报表。

**最佳实践：** 用 Spring Task 时，至少加一层 AOP 记录任务执行情况，否则线上任务"静默死亡"你都不知道。

---

> 📌 **学习建议**：定时任务是后端的"自动化引擎"，从数据同步到报表生成都靠它。Spring Task 是入门的最佳起点——它足够简单，让你专注理解 cron、fixedRate/fixedDelay、线程池这些核心概念。但要记住它的边界：单机、轻量、静态。真实生产环境一旦上规模（多实例、需要动态调整、需要失败重试），就要迁移到 XXL-JOB（后续模块会讲）。建议先把本模块的"对比 fixedRate 和 fixedDelay"练习做透，这是面试和实战的高频考点；再养成"每个任务方法 try-catch + 有意义线程名"的习惯，这是用 Spring Task 不翻车的基本功。
