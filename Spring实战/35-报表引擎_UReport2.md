# 35 - Spring Boot 集成 UReport2 报表引擎

> 对应项目模块：`demo-ureport2`
> 前置知识：已学完前 34 个模块，了解 Spring Boot 基础、JPA、数据源配置
> 学习目标：理解什么是"中国式报表"，掌握 Spring Boot 集成 UReport2 的完整流程，能独立设计并预览一个带查询条件的报表。

---

## 一、本模块要解决什么问题？

### 1.1 什么是"中国式报表"？

如果你做过前端的数据可视化，可能用过 ECharts、AntV 这类图表库画柱状图、折线图。但企业里有一类需求，图表库搞不定——**复杂表格报表**：多层表头、单元格合并、交叉表、小计合计、斑马纹、分页打印、填报回写……这类报表在国内 ERP/财务/政务系统里无处不在，俗称"中国式报表"。

它的特点是**布局极其不规则**，像这样：

```
+----------------------------------------------------+
|                    用户报表                         |  ← 合并单元格做标题
+--------+--------+-----------------+----------------+
| 序号   | 姓名   | 创建时间        | 是否可用        |  ← 表头行
+--------+--------+-----------------+----------------+
| 1      | 张三   | 2020-10-22 ...  | 是              |  ← 数据行（可向下展开）
| 2      | 李四   | 2020-10-23 ...  | 否              |
+--------+--------+-----------------+----------------+
```

用前端 HTML 表格手写也能做，但一旦涉及分页、导出 Excel/PDF、动态数据源、查询条件，工作量巨大。**UReport2 就是为了解决这类需求而生的纯 Java 报表引擎**。

### 1.2 UReport2 是什么？

UReport2 是一款基于 Spring 的纯 Java 高性能报表引擎，核心能力：

- **基于网页的报表设计器**：打开浏览器就能拖拽设计报表，不用装客户端软件（支持 Chrome/Firefox/Edge，不支持 IE）。
- **迭代单元格**：通过单元格的展开方向（向下/向右）实现数据循环填充，能做出任意复杂的表格。
- **多数据源**：支持直连数据库、SQL 数据集、内部数据源（Java 提供 Connection）。
- **多种输出**：网页预览、导出 Excel/PDF/Word。
- **查询表单**：报表可带查询条件，用户输入参数后动态过滤数据。

> 💡 前端类比：UReport2 的设计器类似一个"在线版 Excel + 表单设计器"，报表模板文件（`.ureport.xml`）类似 ECharts 的 option 配置，但它是声明式的单元格布局 + 数据绑定，渲染在服务端。

### 1.3 本模块做了什么？

本模块演示 Spring Boot 集成 UReport2，实现一个用户报表：

- 配置一个 MySQL 数据源
- 注册一个"内部数据源"供报表设计器使用
- 用浏览器打开报表设计器，设计一个带查询条件的用户列表报表
- 保存报表模板，通过 URL 预览

---

## 二、项目结构

```
demo-ureport2/
├── pom.xml
├── README.md
├── doc/
│   ├── sql/t_user_ureport2.sql              # 建表 + 测试数据
│   └── ureport2/user_inner_datasource.ureport.xml  # 报表模板示例
└── src/main/
    ├── java/com/xkcoding/ureport2/
    │   ├── SpringBootDemoUreport2Application.java   # 启动类
    │   └── config/
    │       └── InnerDatasource.java                 # 内部数据源（核心扩展点）
    └── resources/
        └── application.yml                           # 配置
```

注意：本模块**几乎没有业务代码**——启动类是空的，没有 Controller、Service。因为 UReport2 的 starter 帮你注册了报表设计器和预览的 URL 路由，你只要配置好数据源，剩下的都在浏览器里可视化设计。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Web 依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. JPA 依赖（本模块用它自动配置 DataSource） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>

    <!-- 3. MySQL 驱动 -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- 4. UReport2 的 Spring Boot Starter（核心） -->
    <dependency>
        <groupId>com.pig4cloud.plugin</groupId>
        <artifactId>ureport-spring-boot-starter</artifactId>
        <version>0.0.1</version>
    </dependency>

    <!-- 5. 集群模式可选：OSS 存储 -->
    <!--
    <dependency>
        <groupId>com.pig4cloud.plugin</groupId>
        <artifactId>oss-spring-boot-starter</artifactId>
        <version>0.0.2</version>
    </dependency>
    -->

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

### 关键点说明

**1. 为什么引 JPA 但不写 Entity？**

本模块引 `spring-boot-starter-data-jpa` 并不是为了用 JPA 操作实体，而是**借用它的自动配置来创建 `DataSource` Bean**。Spring Boot 检测到 JPA 依赖 + yml 里的 `spring.datasource` 配置，会自动创建一个 HikariCP 数据源的 `DataSource` Bean，而这个 Bean 正好被 `InnerDatasource` 注入使用。这是一种"借鸡生蛋"的简化写法。

**2. `ureport-spring-boot-starter` 是什么？**

UReport2 官方没有提供 Spring Boot Starter，需要手动写一堆 XML 配置集成。这里用的是 [pig-mesh](https://github.com/pig-mesh/ureport-spring-boot-starter) 社区开发的 Starter，它帮你：

- 自动注册 UReport2 的 Servlet（报表设计器、预览、导出的 URL 路由）
- 读取 `ureport.*` 配置项
- 支持单机（本地文件存储）和集群（OSS/Minio 存储）两种模式

**3. `oss-spring-boot-starter`（注释掉的）**

集群模式下，报表模板要存到共享存储（Minio/阿里云 OSS），这个 Starter 兼容所有 S3 协议的对象存储。单机模式不需要。

---

## 四、逐行拆解 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?useUnicode=true&characterEncoding=UTF-8&useSSL=false&autoReconnect=true&failOverReadOnly=false&serverTimezone=GMT%2B8
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
ureport:
  debug: false
  disableFileProvider: false
  disableHttpSessionReportCache: true
  # 单机模式，本地路径需要提前创建
  fileStoreDir: '/Users/yk.shen/Desktop/ureport2'
#oss:
#  access-key: lengleng
#  secret-key: lengleng
#  bucket-name: lengleng
#  endpoint: http://minio.pig4cloud.com
```

### 4.1 数据源配置（`spring.datasource`）

这是标准的数据源配置，和前面 ORM 模块一样。UReport2 的内部数据源会复用这个 `DataSource`。注意 URL 里的参数：

- `serverTimezone=GMT%2B8`：指定时区为东八区（`%2B` 是 `+` 的 URL 编码），避免时间错乱。
- `characterEncoding=UTF-8`：字符集，中文不乱码。
- `useSSL=false`：不启用 SSL（开发环境简化）。

### 4.2 UReport2 配置（`ureport.*`）

| 配置项 | 作用 |
| --- | --- |
| `ureport.debug` | 是否开启调试模式，开启后输出详细日志 |
| `ureport.disableFileProvider` | 是否禁用文件存储提供器，false 表示启用本地文件存储报表模板 |
| `ureport.disableHttpSessionReportCache` | 是否禁用 HttpSession 缓存报表，true 表示禁用（避免 Session 占用内存） |
| `ureport.fileStoreDir` | 报表模板文件的本地存储目录（单机模式），**必须提前手动创建** |

> ⚠️ `fileStoreDir` 是一个经典坑：目录必须**提前创建好**，UReport2 不会自动建目录。如果目录不存在，保存报表会报错。生产环境建议用绝对路径，且应用要有读写权限。

### 4.3 集群配置（`oss.*`，注释掉的）

集群模式把 `fileStoreDir` 换成 OSS 对象存储，配置 `access-key`/`secret-key`/`bucket-name`/`endpoint`，所有节点共享同一份报表模板。

---

## 五、逐行拆解核心代码：内部数据源

`config/InnerDatasource.java` 是本模块**唯一**的业务代码，也是最重要的扩展点：

```java
@Component
public class InnerDatasource implements BuildinDatasource {
    @Autowired
    private DataSource datasource;

    @Override
    public String name() {
        return "内部数据源";
    }

    @SneakyThrows
    @Override
    public Connection getConnection() {
        return datasource.getConnection();
    }
}
```

### 5.1 `BuildinDatasource` 接口

`com.bstek.ureport.definition.datasource.BuildinDatasource` 是 UReport2 定义的接口，实现它就能在报表设计器里把你的应用数据源暴露成一个可选数据源。接口要求实现两个方法：

- `name()`：数据源名称，会显示在设计器的下拉列表里。
- `getConnection()`：返回一个 JDBC `Connection`，报表引擎用它执行 SQL 取数据。

### 5.2 注入 Spring 的 `DataSource`

```java
@Autowired
private DataSource datasource;
```

这里注入的就是 Spring Boot 自动配置的 HikariCP 数据源（来自 yml 的 `spring.datasource` 配置）。`getConnection()` 直接委托给它。这样报表引擎执行的 SQL 和业务代码用的是**同一个连接池**，不会额外占用数据库连接。

### 5.3 `@SneakyThrows`

Lombok 注解，把 `getConnection()` 抛出的 `SQLException`（受检异常）偷偷抛出去，不用在方法签名上写 `throws SQLException`。因为接口 `BuildinDatasource.getConnection()` 没声明 `throws`，实现类也不能加，但 JDBC 方法又必须抛 `SQLException`，`@SneakyThrows` 就是解决这个矛盾的。

> 💡 前端类比：类似 TypeScript 里用 `as any` 绕过类型检查，属于"我知道这有风险但我负责"的偷懒写法。生产代码更严谨的做法是 try-catch 包成运行时异常。

### 5.4 为什么叫"内部"数据源？

UReport2 支持三种数据源：
1. **直连数据库**：在设计器里配 URL/账号密码，报表引擎自己建连接。
2. **Spring 内部数据源**：复用应用的 `DataSource`，就是本模块的做法。
3. **自定义数据源**：实现接口，用任意方式返回数据（甚至调远程 API）。

"内部"指复用应用已有的数据源，避免重复配置和连接泄漏。

---

## 六、启动类与测试类

启动类 `SpringBootDemoUreport2Application.java` 极简：

```java
@SpringBootApplication
public class SpringBootDemoUreport2Application {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoUreport2Application.class, args);
    }
}
```

没有任何额外注解——`ureport-spring-boot-starter` 的自动配置会注册报表相关的 Servlet 和路由，不需要你手动加 `@EnableXxx`。

测试类也是标准的 `contextLoads` 冒烟测试，验证上下文能加载。

---

## 七、报表模板文件结构（`.ureport.xml`）

`doc/ureport2/user_inner_datasource.ureport.xml` 是一个设计好的报表模板。虽然你主要在可视化设计器里操作，但理解它的结构有助于排查问题。核心结构：

```xml
<ureport>
  <!-- 1. 单元格定义：每个 cell 是一个格子 -->
  <cell expand="None" name="A1" row="1" col="1" col-span="4">
    <cell-style font-size="14" bgcolor="92,184,92" bold="true" align="center"/>
    <simple-value><![CDATA[用户报表]]></simple-value>   <!-- 静态文本 -->
  </cell>

  <!-- 数据单元格：expand="Down" 表示向下展开，循环填充数据 -->
  <cell expand="Down" name="A3" row="3" col="1">
    <dataset-value dataset-name="用户报表" aggregate="group" property="id"/>
  </cell>

  <!-- 2. 数据源和数据集定义 -->
  <datasource name="内部数据源" type="buildin">
    <dataset name="用户报表" type="sql">
      <sql><![CDATA[
        ${if(param("status")==null||param("status")==''){
          return "select * from t_user_ureport2"
        }else{
          return "select * from t_user_ureport2 where status = :status"
        }}
      ]]></sql>
      <field name="id"/>
      <parameter name="status" type="Integer" default-value="1"/>
    </dataset>
  </datasource>

  <!-- 3. 纸张/分页配置 -->
  <paper type="A4" paging-mode="fixrows" fixrows="10" orientation="portrait"/>

  <!-- 4. 查询表单 -->
  <search-form>
    <input-select label="是否可用" bind-parameter="status">
      <option label="是" value="1"/>
      <option label="否" value="0"/>
    </input-select>
    <button-submit label="查询"/>
  </search-form>
</ureport>
```

### 关键概念

**`expand` 属性（单元格展开）**：UReport2 的灵魂。一个数据单元格设置 `expand="Down"`，引擎会把数据集的每条记录填充到这个格子，并**向下复制整行**。`expand="Right"` 则向右复制列。`expand="None"` 是静态格子。这就是"迭代单元格"实现复杂表格的原理。

**SQL 里的脚本表达式**：`<sql>` 标签里可以用 `${...}` 写脚本（BeanShell 语法），根据参数动态拼 SQL。本例根据 `status` 参数是否为空决定是否加 `where` 条件——类似前端的动态查询参数拼接。

**`mapping-item`（字典映射）**：把数据库存的 `0/1` 映射成 `否/是` 显示，类似前端的枚举字典。

**`condition-property-item`（条件属性）**：满足条件时改变单元格样式，本例用 `&A3%2==0` 实现斑马纹（偶数行变色）。

---

## 八、运行与验证

### 8.1 准备环境

1. 安装 MySQL，创建数据库 `spring-boot-demo`。
2. 执行 `doc/sql/t_user_ureport2.sql` 建表并插入测试数据。
3. 修改 `application.yml` 里的数据库账号密码、`fileStoreDir`（改成你能访问的本地目录，**提前创建好**）。

### 8.2 启动

```sh
mvn spring-boot:run
```

### 8.3 打开报表设计器

浏览器访问：

```
http://127.0.0.1:8080/demo/ureport/designer
```

### 8.4 设计流程（README 有完整截图）

1. **选数据源**：在设计器里选"内部数据源"（就是 `InnerDatasource.name()` 返回的名字）。
2. **加数据集**：右键数据源 → 添加数据集 → 写 SQL（如 `select * from t_user_ureport2`）→ 预览 → 保存。
3. **画表头**：合并单元格做标题，逐个设置表头列。
4. **绑数据**：在数据行单元格里绑定数据集字段，设置 `expand=Down`。
5. **配字典**：给 `status` 列加映射，`1→是`、`0→否`。
6. **改格式**：给 `create_time` 设日期格式 `yyyy-MM-dd HH:mm:ss`。
7. **保存**：保存为 `demo.ureport.xml`，文件会落到 `fileStoreDir` 目录。

### 8.5 预览报表

保存后，通过这个 URL 预览：

```
http://localhost:8080/demo/ureport/preview?_u=file:demo.ureport.xml
```

带查询参数：

```
http://localhost:8080/demo/ureport/preview?_u=file:demo.ureport.xml&status=1
```

### 8.6 UReport2 的常用 URL

| URL | 作用 |
| --- | --- |
| `/ureport/designer` | 报表设计器 |
| `/ureport/preview?_u=file:xxx.xml` | 预览报表 |
| `/ureport/export/pdf?_u=file:xxx.xml` | 导出 PDF |
| `/ureport/export/excel?_u=file:xxx.xml` | 导出 Excel |

（完整路径前都会带 `context-path`，本例是 `/demo`）

---

## 九、动手练习

1. **跑通基础流程**：按上面步骤建库、改配置、启动、打开设计器，设计一个最简单的用户列表报表并预览。
2. **加查询条件**：在设计器里给数据集加 `status` 参数，设计查询表单（下拉选"是/否"），验证预览时能按条件过滤。
3. **实现斑马纹**：用条件属性，让偶数行背景色不同（参考模板里的 `condition-property-item`）。
4. **导出 Excel**：预览页面点导出，用 Excel 打开，观察格式是否保留。
5. **切换集群模式**：本地起一个 Minio（Docker），启用 `oss-spring-boot-starter`，把报表模板存到 Minio，验证多节点共享。
6. **写一个自定义数据源**：实现 `BuildinDatasource`，`getConnection` 返回一个连远程数据库的连接，在设计器里选用它。

---

## 十、本模块知识点总结（结合实际开发详解）

报表引擎是企业级应用的"最后一公里"——数据查出来了，怎么呈现给业务人员看、能不能导出、能不能交互查询，这些需求看似简单却极其繁琐。下面把核心知识点放到真实开发场景里讲透。

### 10.1 报表引擎 vs 前端图表库：什么时候用哪个？

**实际开发中的选型标准：**

| 需求特征 | 选型 | 理由 |
| --- | --- | --- |
| 柱状图/折线图/饼图，纯可视化 | ECharts/AntV（前端） | 交互性强、动画美观 |
| 简单表格展示 + 排序分页 | 前端表格组件（如 vxe-table） | 灵活、体验好 |
| 复杂多层表头、单元格合并、交叉表 | UReport2（后端） | 布局能力强，前端手写成本高 |
| 需要导出 Excel/PDF 且格式精确 | UReport2（后端） | 所见即所得导出，前端导出格式难控 |
| 财务/政务报表，需打印对齐 | UReport2（后端） | 支持纸张尺寸、分页、打印 |
| 填报回写（用户填数据回数据库） | UReport2（后端） | 支持填报，前端难做 |

**最佳实践：** 不要用报表引擎做所有事。可视化看板用前端图表库，复杂表格报表用 UReport2，两者通过 iframe 或链接集成到一个系统里。很多团队踩过"用前端硬扛复杂报表"的坑，最后返工用报表引擎。

**常见坑：** 以为 ECharts 能画表格（它只是图表库，表格能力很弱）；以为前端导出 Excel 很简单（复杂格式、合并单元格、公式几乎做不到精确控制）。

### 10.2 内部数据源：复用 Spring DataSource 的智慧

**为什么不用直连数据库，而要实现 `BuildinDatasource`？**

1. **配置统一**：数据库账号密码只在 `application.yml` 配一次，报表引擎和业务代码共用。
2. **连接池复用**：走同一个 HikariCP 连接池，连接数可控，不会因报表并发查询把数据库打满。
3. **事务一致**：如果需要，报表查询能和业务在同一事务上下文。
4. **安全**：不在报表设计器里暴露数据库密码，避免泄露。

**实际开发的最佳实践：**

- 永远用内部数据源，不要在设计器里配直连。
- 报表查询的 SQL 走只读账号，权限最小化（只给 SELECT）。
- 复杂报表建议建专门的视图或物化表，SQL 别写太复杂。

**常见坑：** 在设计器里配直连数据源，密码明文存在 `.ureport.xml` 里，进了 git 导致泄露。

### 10.3 报表模板存储：单机 vs 集群

**单机模式（`fileStoreDir`）：**
报表模板存本地目录，简单但**集群下各节点模板不一致**。只适合开发或单节点部署。

**集群模式（OSS/Minio）：**
所有节点共享对象存储里的模板，是生产标配。但要注意：

1. **网络延迟**：每次加载模板都走网络，建议加本地缓存。
2. **并发冲突**：多人同时编辑同一模板会互相覆盖，需要加锁或版本控制。
3. **备份**：对象存储也要开版本管理，误删模板能恢复。

**最佳实践：** 生产用集群模式 + 对象存储版本控制；模板文件纳入 Git 管理（`.ureport.xml` 是文本文件，可 diff），部署时同步到对象存储。

**常见坑：** 单机模式部署到 K8s 多副本，A 节点保存的模板 B 节点看不到，导致"有时能预览有时不能"的灵异问题。

### 10.4 动态 SQL 与参数查询

UReport2 的 `<sql>` 标签支持 `${...}` 脚本，能根据参数动态拼 SQL。本模块的写法：

```sql
${if(param("status")==null||param("status")==''){
  return "select * from t_user_ureport2"
}else{
  return "select * from t_user_ureport2 where status = :status"
}}
```

**实际开发的坑与最佳实践：**

1. **SQL 注入风险**：用字符串拼接 `where status = '${status}'` 是危险的，必须用 `:status` 参数绑定（预编译），UReport2 会自动用 PreparedStatement。本模块用的是 `:status`，正确。
2. **脚本语法冷门**：`${...}` 里是 BeanShell 脚本，语法接近 Java 但不完全一样，调试困难。复杂逻辑建议在 Java 侧写好数据集，而不是在 SQL 脚本里绕。
3. **参数必填校验**：如果参数为空导致 SQL 语法错误，报表会直接报错。脚本里要做空值判断（本模块就做了）。
4. **性能**：动态 SQL 每次都解析，复杂报表建议用存储过程或视图。

> 💡 前端类比：这类似 GraphQL 的变量查询，或前端用模板字符串拼 API URL。但后端 SQL 注入的代价远高于前端，必须用参数绑定。

### 10.5 单元格展开：UReport2 的核心心智模型

**`expand` 属性是理解 UReport2 的关键。** 传统表格是"写死行数填数据"，UReport2 是"画一行模板，引擎根据数据自动展开"。

- `expand="Down"`：数据集有 N 条记录，这个单元格所在的行会被复制 N 份，向下排列。
- `expand="Right"`：向右复制列，用于交叉表（行列表头交叉）。
- `expand="None"`：静态格子，不展开。

**实际开发的常见坑：**

1. **展开方向配错**：本该向下展开配成了 None，数据只显示第一条。
2. **父子展开关系**：多个数据列要按同一数据集展开，且"父单元格"要正确设置，否则数据错位。这是新手最痛苦的地方，建议在设计器里多试。
3. **分组与小计**：用 `aggregate="group"` 分组，配合合计行实现小计/总计，逻辑类似 SQL 的 GROUP BY。

**最佳实践：** 复杂报表先在纸上画好布局，标清每个格子的展开方向和父单元格，再到设计器里实现，比盲试快得多。

### 10.6 UReport2 的版本与维护风险

**实际开发中必须知道的现实：**

UReport2 最新版是 `2.2.9`，已经很久不更新了（README 明确提到）。这意味着：

1. **已知 Bug 不会修**：比如打开带条件属性的旧报表可能无法预览（ISSUE #393），条件表达式变成 `undefined`，需要手动重新选表达式。
2. **不兼容新版 Spring Boot 3**：它依赖老版 Servlet API 和 XML 绑定，升 Spring Boot 3 要大量改造。
3. **社区维护靠 Starter**：`ureport-spring-boot-starter` 由 pig-mesh 社区维护，跟着 Spring Boot 版本适配。

**最佳实践：**

- 用前评估：如果是新项目且要升 Spring Boot 3，谨慎选 UReport2，可考虑替代品（如 JimuReport、FineReport）。
- 用了就锁定版本，不要随便升。
- 避免使用"条件属性"等已知有坑的特性，或做好手动修复的预案。
- 报表模板文件纳入 Git，出问题能回滚。

**常见坑：** 升级 Spring Boot 后 UReport2 启动失败，找不到替代类，被迫回退版本。

### 10.7 报表权限与安全

**实际开发必须考虑：**

1. **设计器权限**：`/ureport/designer` 是管理端入口，不能让普通用户访问。生产环境要加拦截器/Security 校验，只有管理员能进。
2. **预览权限**：不同用户能看的报表不同，要在 Controller/拦截器层做数据权限过滤。
3. **数据权限**：报表 SQL 要带租户/部门过滤，避免越权看数据。UReport2 本身不做权限，要你在 SQL 或数据源层注入。
4. **导出控制**：敏感报表限制导出，或加水印。

**最佳实践：** 把 UReport2 的 URL 纳入 Spring Security 统一鉴权，报表设计器只给 ADMIN 角色，预览按业务角色控制，SQL 里强制带数据权限条件。

---

> 📌 **学习建议**：报表引擎是前端工程师较少接触的领域，但它代表了"服务端渲染"的典型思路——布局和数据绑定在服务端完成，浏览器只负责展示和导出。理解 UReport2 的"单元格展开"模型，能帮你建立"声明式布局"的思维，这种思维在前端的表格组件（如 vxe-table 的模板列）里也通用。实际项目里，报表需求往往占后端工作量的不小比例，掌握一个报表引擎是后端的必备技能。建议先把本模块的流程跑通，再尝试设计一个带分组小计的复杂报表，体会"迭代单元格"的威力。
