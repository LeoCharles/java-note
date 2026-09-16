# 46 - 代码生成器 Codegen

> 对应项目模块：`demo-codegen`
> 前置知识：已学完前面模块，了解 Spring Boot 基本结构、MyBatis-Plus、模板引擎
> 学习目标：理解代码生成器的原理，掌握用 Velocity 模板引擎根据数据库表结构自动生成 Entity/Mapper/Service/Controller/前端 API 代码的完整流程。

---

## 一、本模块要解决什么问题？

做过 CRUD 业务的工程师都有体会：每新建一张表，就要手写一套几乎一模一样的代码——Entity（实体类）、Mapper（数据访问）、Service（业务逻辑）、Controller（接口控制），甚至前端的 API 调用函数。这些代码结构高度重复，但又必须和表字段一一对应，手写既枯燥又容易出错（字段名拼错、类型选错、少写一个注解）。

**代码生成器**就是解决这个痛点的工具：读取数据库表结构（表名、字段名、字段类型、注释），套用预先写好的模板，自动生成一整套代码，打包成 zip 下载。

> 💡 前端类比：这就像前端的脚手架工具 `plop`、`yeoman`，或者 VS Code 的 snippets——你定义好模板，输入参数（表名/组件名），自动生成一堆文件。区别是这里的"参数"来自数据库元数据，而不是手动输入。

本模块的最终效果：打开 `http://localhost:8080/demo/index.html`，输入数据库连接信息，查询出表列表，点"生成代码"，下载一个 zip，解压后就是一整套可直接用的后端代码 + 前端 API 文件。

---

## 二、项目结构

```
demo-codegen/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/codegen/
    │   ├── SpringBootDemoCodegenApplication.java   # 启动类
    │   ├── common/                                  # 通用响应封装
    │   │   ├── R.java                               # 统一响应体
    │   │   ├── PageResult.java                      # 分页结果
    │   │   ├── ResultCode.java                      # 状态码枚举
    │   │   └── IResultCode.java                     # 状态码接口
    │   ├── constants/GenConstants.java              # 常量
    │   ├── controller/CodeGenController.java        # 接口层
    │   ├── entity/                                  # 数据载体
    │   │   ├── TableEntity.java                     # 表元数据
    │   │   ├── ColumnEntity.java                    # 列元数据
    │   │   ├── GenConfig.java                       # 生成配置
    │   │   └── TableRequest.java                    # 查询请求
    │   ├── service/
    │   │   ├── CodeGenService.java                  # 接口
    │   │   └── impl/CodeGenServiceImpl.java         # 实现
    │   └── utils/
    │       ├── CodeGenUtil.java                     # 核心：模板渲染
    │       └── DbUtil.java                          # 数据源构建
    └── resources/
        ├── application.yml                          # 应用配置
        ├── generator.properties                     # 代码生成配置（包名/作者/类型映射）
        ├── jdbc_type.properties                     # 数据库类型→JDBC类型映射
        ├── logback-spring.xml                       # 日志配置
        ├── static/                                  # 前端页面（Vue + iView）
        │   └── index.html
        └── template/                                # Velocity 模板
            ├── Entity.java.vm
            ├── Mapper.java.vm
            ├── Mapper.xml.vm
            ├── Service.java.vm
            ├── ServiceImpl.java.vm
            ├── Controller.java.vm
            └── api.js.vm
```

整个模块的职责清晰：**读数据库元数据 → 套模板渲染 → 打包下载**。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
        <exclusions>
            <exclusion>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-starter-tomcat</artifactId>
            </exclusion>
        </exclusions>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-undertow</artifactId>
    </dependency>
    ...
</dependencies>
```

### 3.1 替换内嵌容器：Tomcat → Undertow

这里有个值得注意的细节：引入 `spring-boot-starter-web` 后，**排除了默认的 Tomcat**，改用 `spring-boot-starter-undertow`。

- `spring-boot-starter-web` 默认带 Tomcat 作为内嵌容器。
- 通过 `<exclusions>` 排除 Tomcat，再引入 Undertow，就把内嵌容器换成了 Undertow。

**为什么要换？** Undertow 是 JBoss 出品的高性能 Servlet 容器，相比 Tomcat 在高并发下内存占用更低、性能更好。代码生成器这种工具型应用，用 Undertow 更轻量。

> 💡 前端类比：这就像 Vite 默认用 esbuild，但你可以换掉它用 swc——把默认的"运行时"替换成更高性能的实现。

### 3.2 核心依赖一览

| 依赖 | 作用 |
| --- | --- |
| `velocity-engine-core` 2.1 | 模板引擎，渲染 `.vm` 模板生成代码 |
| `commons-text` 1.6 | 提供 `WordUtils` 做字符串命名转换（下划线转驼峰） |
| `HikariCP` | 数据库连接池，临时连用户的数据库读元数据 |
| `mysql-connector-java` | MySQL 驱动 |
| `hutool-all` | 工具类（`Db`、`Entity`、`Props`、`IoUtil` 等） |
| `guava` | `Lists` 等集合工具 |
| `lombok` | 简化实体类样板代码 |

注意：本模块**没有引入 MyBatis-Plus 依赖**，但生成的代码里用了 MyBatis-Plus 的注解（`@TableName`、`BaseMapper`、`IService`）。因为生成的代码是给别人用的，别人的工程里才有这些依赖。代码生成器本身只需要 Velocity + 数据库连接。

---

## 四、配置文件

### 4.1 `application.yml`

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

极简配置，只设端口和上下文路径。前端页面访问 `http://localhost:8080/demo/index.html`。

### 4.2 `generator.properties` —— 代码生成配置

```properties
mainPath=com.xkcoding
package=com.xkcoding
moduleName=generator
author=Yangkai.Shen
tablePrefix=tb_
# 类型转换
tinyint=Integer
smallint=Integer
...
bigint=Long
decimal=BigDecimal
...
datetime=LocalDateTime
```

这是代码生成的**默认配置**，分两部分：

1. **生成参数**：`mainPath`（主路径）、`package`（包名）、`moduleName`（模块名）、`author`（作者）、`tablePrefix`（表前缀，生成类名时去掉）。
2. **类型映射**：数据库字段类型 → Java 类型。比如 `bigint=Long` 表示数据库里的 `bigint` 字段，生成 Java 属性时用 `Long` 类型。

> 💡 前端类比：这就像 GraphQL 的 codegen 配置文件 `codegen.yml`，定义"数据库类型→目标语言类型"的映射规则。

### 4.3 `jdbc_type.properties` —— JDBC 类型映射

```properties
tinyint=TINYINT
int=INTEGER
bigint=BIGINT
varchar=VARCHAR
...
```

这个文件映射数据库类型 → MyBatis 的 `jdbcType`。生成的 `Mapper.xml` 里 `<result>` 标签需要 `jdbcType` 属性（如 `jdbcType="VARCHAR"`），这个映射就是为它准备的。

两个 properties 文件配合：一个决定 Java 类型，一个决定 MyBatis 的 jdbcType。

---

## 五、数据载体：Entity 体系

代码生成器需要几个"数据载体"来承载元数据，它们本身不参与业务逻辑，只是装数据的容器。

### 5.1 `TableRequest` —— 用户查询请求

```java
@Data
public class TableRequest {
    private Integer currentPage;   // 当前页
    private Integer pageSize;       // 每页条数
    private String prepend;         // jdbc 前缀，如 jdbc:mysql://
    private String url;             // jdbc url，如 127.0.0.1:3306/db
    private String username;        // 数据库用户名
    private String password;        // 数据库密码
    private String tableName;       // 表名（模糊查询用）
}
```

前端页面填的数据库连接信息就封装成这个对象。注意 `prepend` 和 `url` 分开——前端选数据库类型（MySQL/Oracle/SQLServer），拼出不同的 jdbc 前缀。

### 5.2 `GenConfig` —— 生成配置

```java
@Data
public class GenConfig {
    private TableRequest request;   // 数据库连接信息
    private String packageName;     // 包名（可覆盖默认）
    private String author;          // 作者
    private String moduleName;       // 模块名
    private String tablePrefix;     // 表前缀
    private String tableName;       // 表名
    private String comments;        // 表注释
}
```

点"生成代码"时，前端把连接信息 + 生成参数一起传过来。每个字段都可空，空则用 `generator.properties` 里的默认值。

### 5.3 `TableEntity` / `ColumnEntity` —— 元数据模型

```java
@Data
public class TableEntity {
    private String tableName;        // 表名
    private String comments;         // 表注释
    private ColumnEntity pk;         // 主键列
    private List<ColumnEntity> columns;  // 所有列
    private String caseClassName;    // 驼峰类名，如 UserInfo
    private String lowerClassName;   // 小驼峰，如 userInfo
}

@Data
public class ColumnEntity {
    private String columnName;       // 列名，如 user_name
    private String dataType;         // 数据库类型，如 varchar
    private String comments;         // 列注释
    private String caseAttrName;     // 驼峰属性名，如 UserName
    private String lowerAttrName;    // 小驼峰，如 userName
    private String attrType;         // Java 类型，如 String
    private String jdbcType;         // JDBC 类型，如 VARCHAR
    private String extra;            // 额外信息，如 auto_increment
}
```

这两个类是核心数据模型：从数据库查出的原始元数据，经过转换后存到这里，再传给模板渲染。

---

## 六、核心：`CodeGenUtil` —— 模板渲染引擎

这是整个模块的心脏，负责"元数据 → 代码"的转换。

### 6.1 模板列表

```java
private List<String> getTemplates() {
    List<String> templates = new ArrayList<>();
    templates.add("template/Entity.java.vm");
    templates.add("template/Mapper.java.vm");
    templates.add("template/Mapper.xml.vm");
    templates.add("template/Service.java.vm");
    templates.add("template/ServiceImpl.java.vm");
    templates.add("template/Controller.java.vm");
    templates.add("template/api.js.vm");
    return templates;
}
```

一次生成 7 个文件：6 个后端 + 1 个前端 API。模板放在 `resources/template/` 下，通过 classpath 加载。

### 6.2 主方法 `generatorCode` 流程

```java
public void generatorCode(GenConfig genConfig, Entity table, List<Entity> columns, ZipOutputStream zip) {
    // 1. 读配置
    Props propsDB2Java = getConfig("generator.properties");
    Props propsDB2Jdbc = getConfig("jdbc_type.properties");

    // 2. 构建表元数据
    TableEntity tableEntity = new TableEntity();
    tableEntity.setTableName(table.getStr("tableName"));
    // ... 处理注释、表前缀

    // 3. 表名转 Java 类名
    String className = tableToJava(tableEntity.getTableName(), tablePrefix);
    tableEntity.setCaseClassName(className);
    tableEntity.setLowerClassName(StrUtil.lowerFirst(className));

    // 4. 遍历列，转换成列元数据
    for (Entity column : columns) {
        ColumnEntity columnEntity = new ColumnEntity();
        // 列名转驼峰属性名
        String attrName = columnToJava(columnEntity.getColumnName());
        // 数据库类型转 Java 类型
        String attrType = propsDB2Java.getStr(columnEntity.getDataType(), "unknownType");
        // 数据库类型转 JDBC 类型
        String jdbcType = propsDB2Jdbc.getStr(columnEntity.getDataType(), "unknownType");
        // 判断主键
        if ("PRI".equalsIgnoreCase(column.getStr("columnKey"))) {
            tableEntity.setPk(columnEntity);
        }
        columnList.add(columnEntity);
    }

    // 5. 初始化 Velocity
    Properties prop = new Properties();
    prop.put("file.resource.loader.class", "org.apache.velocity.runtime.resource.loader.ClasspathResourceLoader");
    Velocity.init(prop);

    // 6. 封装模板数据
    Map<String, Object> map = new HashMap<>(16);
    map.put("tableName", tableEntity.getTableName());
    map.put("pk", tableEntity.getPk());
    map.put("className", tableEntity.getCaseClassName());
    map.put("columns", tableEntity.getColumns());
    // ... 其他变量

    VelocityContext context = new VelocityContext(map);

    // 7. 遍历模板，渲染并写入 zip
    for (String template : templates) {
        StringWriter sw = new StringWriter();
        Template tpl = Velocity.getTemplate(template, CharsetUtil.UTF_8);
        tpl.merge(context, sw);
        zip.putNextEntry(new ZipEntry(getFileName(template, ...)));
        IoUtil.write(zip, StandardCharsets.UTF_8, false, sw.toString());
        zip.closeEntry();
    }
}
```

整个流程分 7 步：读配置 → 建表元数据 → 表名转类名 → 列名转属性名+类型映射 → 初始化 Velocity → 封装模板变量 → 渲染写入 zip。

### 6.3 命名转换：下划线转驼峰

```java
private String columnToJava(String columnName) {
    return WordUtils.capitalizeFully(columnName, new char[]{'_'}).replace("_", "");
}
```

- `WordUtils.capitalizeFully("user_name", new char[]{'_'})` → `User_Name`（以 `_` 为分隔符，每段首字母大写）
- `.replace("_", "")` → `UserName`
- 最终 `tableToJava` 再用 `StrUtil.lowerFirst` 转小驼峰 → `userName`

`tableToJava` 还会先去掉表前缀：`tb_user_info` → 去掉 `tb_` → `user_info` → `UserInfo`。

> 💡 前端类比：这就像 JS 的 `lodash.camelCase` / `lodash.upperFirst`，把 `user_name` 转成 `userName`。后端用 Apache Commons Text 的 `WordUtils` 实现。

### 6.4 文件名生成：`getFileName`

```java
private String getFileName(String template, String className, String packageName, String moduleName) {
    String packagePath = GenConstants.SIGNATURE + "/src/main/java/";
    String resourcePath = GenConstants.SIGNATURE + "/src/main/resources/";
    String apiPath = GenConstants.SIGNATURE + "/api/";

    if (StrUtil.isNotBlank(packageName)) {
        packagePath += packageName.replace(".", "/") + "/" + moduleName + "/";
    }
    // 根据模板类型返回对应路径
    if (template.contains(ENTITY_JAVA_VM)) {
        return packagePath + "entity/" + className + ".java";
    }
    if (template.contains(MAPPER_JAVA_VM)) {
        return packagePath + "mapper/" + className + "Mapper.java";
    }
    ...
}
```

这个方法决定生成的每个文件在 zip 里的路径。比如包名 `com.xkcoding`、模块名 `generator`、类名 `User`，生成的 Entity 路径是：

```
xkcoding代码生成/src/main/java/com/xkcoding/generator/entity/User.java
```

`GenConstants.SIGNATURE = "xkcoding代码生成"` 是 zip 里的根目录名。`packageName.replace(".", "/")` 把包名的点转成路径分隔符。

---

## 七、Velocity 模板逐行拆解

模板是代码生成的灵魂。以 `Entity.java.vm` 为例：

```velocity
package ${package}.${moduleName}.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.activerecord.Model;
import lombok.Data;
import lombok.EqualsAndHashCode;
#if(${hasBigDecimal})
import java.math.BigDecimal;
#end
import java.time.LocalDateTime;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@TableName("${tableName}")
@ApiModel(description = "${comments}")
@EqualsAndHashCode(callSuper = true)
public class ${className} extends Model<${className}> {
    private static final long serialVersionUID = 1L;

  #foreach ($column in $columns)
    /**
     * $column.comments
     */
    #if($column.columnName == $pk.columnName)
    @TableId
    #end
    @ApiModelProperty(value = "$column.comments")
    private $column.attrType $column.lowerAttrName;
  #end
}
```

### 7.1 Velocity 语法速查

| 语法 | 含义 | 示例 |
| --- | --- | --- |
| `${var}` 或 `$var` | 变量替换 | `${className}` → `User` |
| `#if($cond)` ... `#end` | 条件判断 | 有 BigDecimal 时才 import |
| `#foreach($x in $list)` ... `#end` | 循环 | 遍历所有列生成字段 |
| `$obj.prop` | 访问对象属性 | `$column.attrType` |
| `##` | 行注释 | `## 这是注释` |

> 💡 前端类比：Velocity 语法类似 EJS/Handlebars/`<%= %>`，`${}` 是变量插值，`#if/#foreach` 是控制流。如果你用过 Vue 的模板语法，会觉得 `#if` 很像 `v-if`，`#foreach` 很像 `v-for`。

### 7.2 条件 import 的妙用

```velocity
#if(${hasBigDecimal})
import java.math.BigDecimal;
#end
```

`hasBigDecimal` 是在 `CodeGenUtil` 里算出的布尔值：只有当表里存在 `decimal` 类型字段时才为 true。这样生成的代码不会无脑 import `BigDecimal`，保持干净。

### 7.3 循环生成字段

```velocity
#foreach ($column in $columns)
    #if($column.columnName == $pk.columnName)
    @TableId
    #end
    @ApiModelProperty(value = "$column.comments")
    private $column.attrType $column.lowerAttrName;
#end
```

遍历所有列，每列生成一个字段。如果列名等于主键列名，额外加 `@TableId` 注解。最终生成类似：

```java
@TableId
@ApiModelProperty(value = "主键ID")
private Long id;

@ApiModelProperty(value = "用户名")
private String username;
```

### 7.4 其他模板要点

- **Controller.java.vm**：生成 RESTful 的增删改查接口，用 MyBatis-Plus 的 `IService` 方法（`page`、`getById`、`save`、`updateById`、`removeById`），还带 Swagger 注解。
- **Mapper.java.vm**：`interface XxxMapper extends BaseMapper<Xxx>`，继承 MyBatis-Plus 的通用 Mapper。
- **Service.java.vm / ServiceImpl.java.vm**：`interface XxxService extends IService<Xxx>` + `class XxxServiceImpl extends ServiceImpl`。
- **Mapper.xml.vm**：生成 `resultMap`，用 `#foreach` 遍历列，主键用 `<id>`，其他用 `<result>`。
- **api.js.vm**：生成前端 axios 调用函数（`fetchList`/`addObj`/`getObj`/`delObj`/`putObj`），这是给前端工程师直接用的。

---

## 八、Service 与 Controller

### 8.1 `CodeGenServiceImpl` —— 业务逻辑

核心是两个方法：

**`listTables`**：分页查询数据库的表列表。用 Hutool 的 `Db` 工具直接查 MySQL 的 `information_schema.tables`（元数据表）：

```java
private final String TABLE_SQL_TEMPLATE = "select table_name tableName, engine, table_comment tableComment, create_time createTime from information_schema.tables where table_schema = (select database()) %s order by create_time desc";
```

`information_schema` 是 MySQL 自带的元数据库，存着所有表/列的信息。`(select database())` 取当前连接的库名。这是代码生成器能"读出表结构"的原理。

**`generatorCode`**：查表信息 + 查列信息 + 调 `CodeGenUtil` 渲染 + 返回 zip 字节数组：

```java
public byte[] generatorCode(GenConfig genConfig) {
    ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
    ZipOutputStream zip = new ZipOutputStream(outputStream);
    Entity table = queryTable(genConfig.getRequest());
    List<Entity> columns = queryColumns(genConfig.getRequest());
    CodeGenUtil.generatorCode(genConfig, table, columns, zip);
    IoUtil.close(zip);
    return outputStream.toByteArray();
}
```

### 8.2 `DbUtil` —— 临时数据源

```java
@UtilityClass
public class DbUtil {
    public HikariDataSource buildFromTableRequest(TableRequest request) {
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(request.getPrepend() + request.getUrl());
        dataSource.setUsername(request.getUsername());
        dataSource.setPassword(request.getPassword());
        return dataSource;
    }
}
```

每次查询都**临时创建一个 HikariDataSource**，用完就 `close()`。因为代码生成器不知道用户要连哪个库，不能预先配置，只能动态创建连接。

### 8.3 `CodeGenController` —— 接口层

```java
@RestController
@RequestMapping("/generator")
public class CodeGenController {
    @GetMapping("/table")
    public R listTables(TableRequest request) { ... }

    @PostMapping("")
    public void generatorCode(@RequestBody GenConfig genConfig, HttpServletResponse response) {
        byte[] data = codeGenService.generatorCode(genConfig);
        response.setHeader(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=" + genConfig.getTableName() + ".zip");
        response.setContentType("application/octet-stream; charset=UTF-8");
        IoUtil.write(response.getOutputStream(), Boolean.TRUE, data);
    }
}
```

两个接口：`GET /generator/table` 查表列表，`POST /generator` 生成代码。

**下载 zip 的关键**：设置 `Content-Disposition: attachment` 让浏览器触发下载，`Content-Type: application/octet-stream` 表示二进制流，把 zip 字节数组写到响应输出流。

> 💡 前端类比：前端用 `responseType: 'arraybuffer'` 接收，再 `new Blob([data], {type: 'application/zip'})` + `URL.createObjectURL` 触发下载——这正是本模块 `index.html` 里的做法。

---

## 九、前端页面

`static/index.html` 是一个 Vue + iView 的单页应用，功能：
1. 填数据库连接信息（URL/用户名/密码）
2. 查询表列表（分页表格）
3. 点"生成代码"弹配置框（包名/作者/模块名/前缀/注释）
4. 调 `POST /generator`，接收 zip 流，触发下载

前端代码对前端工程师来说很熟悉，核心是下载逻辑：

```javascript
http({
  url: '/generator',
  method: 'post',
  data: this.genConfig,
  responseType: 'arraybuffer'   // 关键：接收二进制
}).then((response) => {
  let blob = new Blob([response.data], {type: 'application/zip'});
  let link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(blob);   // 释放内存
});
```

---

## 十、运行与验证

### 10.1 启动

```sh
mvn spring-boot:run
```

### 10.2 使用

1. 浏览器打开 `http://localhost:8080/demo/index.html`
2. 填数据库连接：选 MySQL，URL 填 `127.0.0.1:3306/你的库名`，用户名密码
3. 点查询，看到表列表
4. 点某表的"生成代码"，填配置（可留空用默认），点下载
5. 解压 zip，得到一整套代码

### 10.3 测试类

`CodeGenServiceTest` 提供了两个测试方法，直接连本地库测试查询和生成，无需前端页面。

---

## 十一、动手练习

1. **加一个模板**：在 `template/` 下新建 `Dto.java.vm`，生成一个 DTO 类（只含部分字段），在 `getTemplates()` 和 `getFileName()` 里注册它。
2. **改类型映射**：在 `generator.properties` 里把 `datetime` 的 Java 类型从 `LocalDateTime` 改成 `Date`，重新生成，观察变化。
3. **支持 Oracle**：当前只支持 MySQL（前端限制）。研究 `information_schema` 的 Oracle 等价物（`ALL_TABLES`/`ALL_TAB_COLUMNS`），尝试扩展。
4. **加 Swagger 注解开关**：在 `GenConfig` 加 `hasSwagger` 布尔字段，模板里用 `#if($hasSwagger)` 控制 Swagger 注解是否生成。
5. **生成 Vue 页面**：参考 `api.js.vm`，写一个 `index.vue.vm`，生成一个 Vue 列表页面（含表格+分页+增删改查弹窗）。
6. **改成在线预览**：当前是下载 zip。改成在页面上直接预览生成的代码（用 `GET` 接口返回文件内容，前端用代码高亮组件展示）。

---

## 十二、本模块知识点总结（结合实际开发详解）

代码生成器是"元数据驱动开发"的典型实践，理解它对掌握"模板引擎 + 反射 + 元数据"这一套很有帮助。

### 12.1 代码生成器的价值与边界

**实际开发中怎么用？**

代码生成器适合**结构高度重复的样板代码**——CRUD 的 Entity/Mapper/Service/Controller 几乎每张表都长一样，手写浪费时间且易错。生成器把这件重复劳动自动化，几分钟生成一整套，稍作修改就能用。

**最佳实践：**

1. **生成后一定要 review**：生成器只能生成"骨架"，业务逻辑（校验、关联、特殊查询）还得手写。生成完要检查字段类型、主键、注释是否正确。
2. **不要反复生成覆盖**：第一次生成后，业务代码会手写进去。如果改了表结构要重新生成，应该只生成新字段部分，手动合并，避免覆盖手写逻辑。很多团队用"生成标记"（如 `// gen-start` / `// gen-end`）做增量合并。
3. **模板要随技术栈演进**：从 MyBatis 到 MyBatis-Plus，从 XML 到注解，模板要跟着升级。本模块模板用 MyBatis-Plus + Swagger + Lombok，是较现代的组合。

**常见坑：**

- 类型映射不全：如果数据库用了 `json`、`enum` 等新类型，`generator.properties` 里没配，会生成 `unknownType`，编译报错。要补全映射。
- 主键判断不准：复合主键时只取第一个当主键，第二主键字段不会标 `@TableId`，需要手动调整。
- 表前缀误删：如果表名是 `user` 但配了 `tablePrefix=tb_`，`replaceFirst` 不会报错但也不生效（没前缀可删）；如果表名是 `tb_user_tb_info`，`replaceFirst` 只删第一个 `tb_`。

### 12.2 Velocity 模板引擎

**实际开发中怎么用？**

Velocity 是老牌 Java 模板引擎，语法简单（`${}`、`#if`、`#foreach`），适合生成代码、邮件模板、SQL 等。本模块用它生成 Java 代码。

**最佳实践：**

1. **模板放 classpath**：用 `ClasspathResourceLoader` 从 classpath 加载模板，这样模板打进 jar 也能用，不依赖外部文件路径。
2. **条件 import**：像本模块 `#if($hasBigDecimal)` 这样，按需 import，避免生成无用 import（虽然 Java 允许无用 import，但不干净）。
3. **模板和代码解耦**：模板只管"怎么渲染"，数据准备在 Java 代码里做。不要在模板里写复杂逻辑。

**常见坑：**

- `$obj.prop` 静默失败：如果 `$obj` 为 null 或属性不存在，Velocity 默认原样输出 `$obj.prop` 而不报错，生成的代码里会残留 `$xxx`。调试时要打开 `runtime.log` 看警告。
- `#if` 空值判断：`#if($var)` 当 `$var` 是空字符串、0、false 时都为 false，要注意区分"未定义"和"假值"。
- 模板更新不生效：`Velocity.init` 只初始化一次，开发时改了模板要重启应用（或关闭模板缓存）。

> 💡 现代项目更多用 FreeMarker 或直接用 MyBatis-Plus / MyBatis Generator 官方工具，Velocity 在新项目里用得少了，但原理相通。

### 12.3 数据库元数据查询

**实际开发中怎么用？**

本模块查 `information_schema.tables` 和 `information_schema.columns` 获取表结构。这是 MySQL 的"数据字典"，存着所有表和列的元信息。

```sql
-- 查表
SELECT table_name, table_comment, create_time
FROM information_schema.tables
WHERE table_schema = (SELECT database());

-- 查列
SELECT column_name, data_type, column_comment, column_key, extra
FROM information_schema.columns
WHERE table_name = ? AND table_schema = (SELECT database())
ORDER BY ordinal_position;
```

**最佳实践：**

1. **用 `ordinal_position` 排序**：保证列顺序和建表顺序一致，生成的字段顺序可读。
2. **`column_key = 'PRI'` 判主键**：`information_schema` 用 `PRI`/`UNI`/`MUL` 标识索引类型，`PRI` 是主键。
3. **`extra` 拿自增信息**：`extra = 'auto_increment'` 表示自增列，生成时可用 `@TableId(type = IdType.AUTO)`。

**常见坑：**

- 不同数据库元数据表不同：MySQL 是 `information_schema`，Oracle 是 `ALL_TAB_COLUMNS`，PostgreSQL 是 `pg_catalog`。要支持多数据库得写多套 SQL。
- `table_schema` 必须指定：不指定会查出所有库的表，混淆。用 `(SELECT database())` 取当前库。
- 注释编码：`column_comment` 可能含特殊字符，生成到 Java 注释里要转义，否则 `*/` 会破坏注释。

### 12.4 动态数据源与连接管理

**实际开发中怎么用？**

本模块每次查询都 `new HikariDataSource()`，用完 `close()`。因为用户连的库不固定，无法预先配置。

**最佳实践：**

1. **工具型应用才这么做**：代码生成器、数据库管理工具这类"连任意库"的场景，适合动态创建数据源。
2. **务必关闭**：`HikariDataSource` 持有连接池和线程，不 close 会泄漏。本模块每个方法末尾都 `dataSource.close()`。
3. **考虑连接池复用**：如果频繁连同一个库，可以按 url 缓存 DataSource，避免反复创建。本模块为简单没做缓存。

**常见坑：**

- 忘记 close 导致连接耗尽：高并发下频繁创建不关闭，数据库连接数飙升。
- 密码明文传输：前端把数据库密码传到后端，走 HTTP 明文。生产环境应该用 HTTPS 或让用户在服务端配置，不在前端传。

### 12.5 文件下载的两种方式

**实际开发中怎么用？**

本模块用 `HttpServletResponse` 直接写二进制流下载 zip。这是后端文件下载的标准方式。

```java
response.setHeader(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=xxx.zip");
response.setContentType("application/octet-stream");
IoUtil.write(response.getOutputStream(), true, data);
```

**最佳实践：**

1. **`Content-Disposition: attachment`**：触发浏览器下载而非内联显示。
2. **文件名编码**：中文文件名要用 `URLEncoder.encode` 编码，否则部分浏览器乱码。
3. **大文件用流**：本模块生成的 zip 小，直接 `byte[]`。大文件应该边生成边写流，避免 OOM。

**常见坑：**

- 跨域下载：前后端分离时，`Content-Disposition` 在跨域响应里默认不可见，要在 CORS 配置里暴露 `Content-Disposition` 头（`Access-Control-Expose-Headers`）。
- 响应已提交：如果在写流之前有任何异常处理往 response 写了东西，再写流会报 `getOutputStream() has already been called`。

### 12.6 统一响应体 `R<T>`

本模块定义了 `R<T>` 统一响应体（`code`/`message`/`status`/`data`），配合 `ResultCode` 枚举。这是后端 API 的标准封装。

**最佳实践：**

1. **泛型 `R<T>`**：`data` 用泛型，调用方明确知道返回什么类型，避免强转。
2. **静态工厂方法**：`R.success(data)` / `R.fail(code, msg)`，构造逻辑集中，调用简洁。
3. **状态码枚举**：用 `ResultCode` 枚举管理状态码，避免魔法数字。

> 💡 前端类比：这就像前端 axios 响应拦截器里统一处理 `{ code, message, data }` 结构，`R<T>` 是后端这边的对应物。

### 12.7 代码生成器 vs MyBatis-Plus Generator vs JHipster

**实际开发中怎么选？**

| 方案 | 特点 | 适用场景 |
| --- | --- | --- |
| 自己写（本模块） | 完全可控，模板自定义 | 定制化要求高、想学习原理 |
| MyBatis-Plus Generator | 官方工具，模板丰富，社区支持 | 用 MyBatis-Plus 的项目 |
| JHipster | 全栈脚手架，生成前后端 + 部署配置 | 快速起一个完整项目 |
| IDEA 插件（如 EasyCode） | 图形化，集成在 IDE | 个人开发，不想搭服务 |

本模块的价值在于"透明"——你能看到从数据库到代码的每一步，理解原理后，用任何生成器都能得心应手。

---

> 📌 **学习建议**：代码生成器是"偷懒"的艺术——把重复劳动交给机器。作为前端转后端的工程师，你可能觉得"写个脚本生成代码"很自然（前端早就在用 plop/hygen），后端的代码生成器原理完全一样，只是数据源从"命令行参数"变成了"数据库元数据"。建议你重点理解三件事：① 模板引擎怎么用变量替换 + 循环生成文本；② 数据库元数据怎么查；③ 文件下载怎么实现。掌握后，你可以给自己的项目写一个定制生成器，效率提升立竿见影。
