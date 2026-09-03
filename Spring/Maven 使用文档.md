# Maven 使用文档（结合 Spring Boot 实战）

> 📅 创建时间：2026-09  
> 🎯 目标读者：有前端开发基础，希望快速看懂 Maven、能在 Spring Boot 项目中熟练使用 Maven 的工程师  
> 📌 文档定位：速成手册 + 实战案例 + 企业真实场景参考  
> ⚡ 核心理念：**不求精通 Maven 原理，只求能看懂 pom.xml、会用命令、能排查依赖问题**

---

## 📖 目录

- [第一章：Maven 是什么](#第一章maven-是什么)
- [第二章：Maven 项目结构详解](#第二章maven-项目结构详解)
- [第三章：pom.xml 全解密](#第三章pomxml-全解密)
- [第四章：Maven 生命周期与常用命令](#第四章maven-生命周期与常用命令)
- [第五章：依赖管理](#第五章依赖管理)
- [第六章：Maven 仓库与镜像配置](#第六章maven-仓库与镜像配置)
- [第七章：Spring Boot 中的 Maven 实战](#第七章spring-boot-中的-maven-实战)
- [第八章：常见问题排查](#第八章常见问题排查)
- [第九章：速查表](#第九章速查表)

---

# 第一章：Maven 是什么

## 1.1 一句话理解 Maven

Maven 是 Java 生态中最主流的**项目构建和依赖管理工具**。它干两件事：
1. **管理依赖**：帮你自动下载、组织项目用到的第三方 jar 包（类似 npm 管理 node_modules）。
2. **构建项目**：提供一套标准化的生命周期——清理、编译、测试、打包、安装、部署。

> **💡 前端类比**：
> | Maven 概念 | 前端对应物 | 说明 |
> |---|---|---|
> | Maven | npm / yarn / pnpm | 构建工具 + 包管理器 |
> | `pom.xml` | `package.json` | 项目配置和依赖声明 |
> | Maven 中央仓库 | npm registry（registry.npmjs.org） | 公共包托管仓库 |
> | 本地仓库（`~/.m2/repository`） | `node_modules` | 下载的依赖缓存 |
> | `groupId:artifactId:version` | `@scope/name@version` | 包的唯一坐标 |
> | `mvn install` | `npm install` | 安装依赖（但语义不同，见下文） |
> | `spring-boot-starter-web` | `npm i express` | 引入一个功能包 |

## 1.2 Maven vs npm 的关键区别

虽然 Maven 和 npm 角色类似，但有几个**容易踩坑**的区别：

```
┌─────────────────────────────────────────────────────────────┐
│  npm 的依赖装在「每个项目」的 node_modules 里                   │
│  → 项目 A 和项目 B 各自有一份，互不影响                          │
│                                                              │
│  Maven 的依赖装在「全局本地仓库」(~/.m2/repository) 里           │
│  → 所有项目共享同一份缓存，项目里只存一份引用（路径指针）          │
│  → 好处：省磁盘空间，下载一次到处用                              │
│  → 坏处：删某个项目的依赖不会真的删 jar，要手动清本地仓库          │
└─────────────────────────────────────────────────────────────┘
```

> **⚠️ 注意**：`mvn install` 和 `npm install` **语义完全不同**！
> - `npm install` = 根据 package.json **下载**依赖到 node_modules
> - `mvn install` = 把**当前项目**打包后**发布到本地仓库**（让别人能引用）
> - Maven 下载依赖的动作是**自动的**——只要 pom.xml 里声明了依赖，任何 mvn 命令执行时都会自动下载。

## 1.3 安装与验证

```bash
# 检查是否已安装
mvn -version
# 输出示例：
# Apache Maven 3.9.6 (...)
# Maven home: /usr/share/maven
# Java version: 17.0.10, vendor: Oracle Corporation

# 如果用 IDEA 开发 Spring Boot，IDEA 自带 Maven，通常无需单独安装
# 但建议配置独立的 Maven，方便统一管理版本和镜像
```

> **💡 提示**：Spring Boot 3.x 要求 Java 17+，请确保 `mvn -version` 输出的 Java 版本 ≥ 17。

---

# 第二章：Maven 项目结构详解

## 2.1 标准目录结构

Maven 强制约定了一套目录结构，所有 Maven 项目都长一个样（约定大于配置）：

```
project-root/
├── pom.xml                      # 📦 项目配置文件（类似 package.json）
├── src/
│   ├── main/                    # 主代码（会打进最终产物）
│   │   ├── java/                #   Java 源代码
│   │   │   └── com/example/demo/
│   │   │       └── DemoApplication.java
│   │   └── resources/           #   资源文件（配置文件等）
│   │       ├── application.yml
│   │       └── mapper/
│   │           └── UserMapper.xml
│   └── test/                    # 测试代码（不会打进最终产物）
│       ├── java/                #   测试源代码
│       │   └── com/example/demo/
│       │       └── DemoApplicationTests.java
│       └── resources/           #   测试资源文件
└── target/                      # 📤 编译/打包输出（自动生成，可随时删除）
    ├── classes/                 #   编译后的 .class 文件
    ├── test-classes/            #   编译后的测试 .class
    └── demo-1.0.0.jar           #   打包产物
```

## 2.2 各目录职责

| 目录 | 作用 | 前端类比 |
|---|---|---|
| `pom.xml` | 项目配置、依赖声明、插件配置 | `package.json` |
| `src/main/java` | 项目业务源代码 | `src/` 源码目录 |
| `src/main/resources` | 配置文件、SQL 映射、模板等 | `src/` 下的静态资源 |
| `src/main/webapp` | Web 资源（js/css/html/图片），传统 war 工程用 | `public/` 静态资源 |
| `src/test/java` | 单元测试代码 | `__tests__/` 或 `*.test.ts` |
| `src/test/resources` | 测试用的配置文件 | 测试 mock 数据 |
| `target/` | 编译、打包的输出目录 | `dist/` 构建产物 |

> **💡 前端类比**：`target/` ≈ `dist/` 或 `build/`，是构建产物，**不应该提交到 git**（通常在 `.gitignore` 里）。删掉它再重新构建完全没问题。

## 2.3 Spring Boot 项目的目录实践

Spring Boot 遵循 Maven 标准结构，但有些约定：

```
src/main/java/com/example/demo/
├── DemoApplication.java        # 启动类（必须在根包，见 Spring Boot 文档第 7 章）
├── controller/                  # 控制器
├── service/                     # 业务逻辑
├── repository/                  # 数据访问
├── entity/                      # 实体
├── config/                      # 配置类
└── ...
```

> **⚠️ 关键**：启动类 `DemoApplication` 必须放在所有业务包的**父包**下（即 `com.example.demo`），否则 `@ComponentScan` 扫描不到其他类，导致接口 404。这是 Spring Boot + Maven 最常见的坑之一。

---

# 第三章：pom.xml 全解密

`pom.xml`（Project Object Model）是 Maven 的核心配置文件，相当于前端的 `package.json`。一个 Spring Boot 项目的 pom.xml 长这样：

## 3.1 完整示例（带详细注释）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">

    <modelVersion>4.0.0</modelVersion>  <!-- POM 模型版本，固定 4.0.0 -->

    <!-- ============ 1. 继承 Spring Boot 父项目 ============ -->
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/>  <!-- 从仓库查找父 pom，不从本地路径找 -->
    </parent>

    <!-- ============ 2. 项目坐标（唯一标识） ============ -->
    <groupId>com.example</groupId>          <!-- 组织/公司域名倒写 -->
    <artifactId>demo</artifactId>           <!-- 项目模块名 -->
    <version>1.0.0</version>               <!-- 版本号 -->
    <!-- <packaging>jar</packaging> -->     <!-- 打包方式：jar(默认)/war/pom -->

    <!-- ============ 3. 项目信息 ============ -->
    <name>demo</name>
    <description>一个 Spring Boot 示例项目</description>

    <!-- ============ 4. 属性定义（版本号集中管理） ============ -->
    <properties>
        <java.version>17</java.version>              <!-- JDK 版本 -->
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <!-- 自定义版本号，下方用 ${} 引用 -->
        <mybatis-plus.version>3.5.5</mybatis-plus.version>
    </properties>

    <!-- ============ 5. 依赖声明 ============ -->
    <dependencies>
        <!-- Web 启动器 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <!-- 注意：继承父 pom 后，官方 starter 无需写 version -->
        </dependency>

        <!-- 第三方依赖需自己写版本 -->
        <dependency>
            <groupId>com.baomidou</groupId>
            <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
            <version>${mybatis-plus.version}</version>
        </dependency>

        <!-- 测试依赖（只在测试范围生效） -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <!-- ============ 6. 构建配置 ============ -->
    <build>
        <plugins>
            <!-- Spring Boot 打包插件：把项目打成可执行 jar -->
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

## 3.2 项目坐标（GAV）

Maven 用三个字段唯一定位一个依赖，称为 **GAV 坐标**：

```
groupId    :artifactId    :version
com.example:demo          :1.0.0
```

| 字段 | 含义 | 前端类比 | 示例 |
|---|---|---|---|
| `groupId` | 组织/公司标识（通常域名倒写） | npm 包的 scope（`@angular`） | `org.springframework.boot` |
| `artifactId` | 项目/模块名 | npm 包名 | `spring-boot-starter-web` |
| `version` | 版本号 | npm 包版本 | `3.2.0` |

> **💡 前端类比**：`org.springframework.boot:spring-boot-starter-web:3.2.0` ≈ `@springframework.boot/spring-boot-starter-web@3.2.0`。

## 3.3 `<parent>` 继承机制

Spring Boot 项目都会继承 `spring-boot-starter-parent`，它做了三件事：

```
spring-boot-starter-parent
    │
    ├── 1. 统一管理几百个常用依赖的版本号
    │      → 你引入官方 starter 时不写 version，自动用父 pom 规定的版本
    │      → 避免版本冲突，保证兼容性
    │
    ├── 2. 配置默认的插件版本和编译参数
    │      → Java 版本、编码、资源过滤等
    │
    └── 3. 配置 spring-boot-maven-plugin 的默认行为
           → 打包成可执行 jar
```

> **💡 前端类比**：`<parent>` ≈ 继承一个基础配置的 `package.json` 模板，类似 monorepo 里的根 `package.json` 统一管理子包版本。

## 3.4 `<properties>` 属性

集中管理版本号，避免散落各处。用 `${属性名}` 引用：

```xml
<properties>
    <java.version>17</java.version>
    <lombok.version>1.18.30</lombok.version>
</properties>

<dependencies>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <version>${lombok.version}</version>  <!-- 引用属性 -->
    </dependency>
</dependencies>
```

> **💡 前端类比**：类似在 `.env` 里定义版本变量，或 monorepo 里集中声明依赖版本。

---

# 第四章：Maven 生命周期与常用命令

## 4.1 三套生命周期

Maven 有三套**相互独立**的生命周期，每套包含多个阶段（phase）：

```
┌─────────────────────────────────────────────────────────────┐
│  1. Clean 生命周期（清理）                                     │
│     pre-clean → clean → post-clean                           │
│     作用：删除 target/ 目录                                    │
├─────────────────────────────────────────────────────────────┤
│  2. Default 生命周期（构建，最常用）                            │
│     validate → compile → test → package →                    │
│     integration-test → verify → install → deploy             │
│     作用：编译、测试、打包、安装、部署                          │
├─────────────────────────────────────────────────────────────┤
│  3. Site 生命周期（站点文档）                                   │
│     pre-site → site → post-site                              │
│     作用：生成项目文档网站（实际很少用）                         │
└─────────────────────────────────────────────────────────────┘
```

> **💡 关键规则**：执行某个阶段时，Maven 会**从该生命周期的第一个阶段一直执行到指定阶段**。比如执行 `mvn package`，会依次执行 `validate → compile → test → package`。

## 4.2 常用命令速查

```bash
# ===== 基础构建命令 =====
mvn clean                  # 清除 target/ 目录
mvn compile                # 编译 main 下的源代码
mvn test                   # 运行测试（src/test/java 下的单元测试）
mvn package                # 打包（jar/war），会先执行 compile + test
mvn install                # 打包并安装到本地仓库（~/.m2/repository）
mvn deploy                 # 发布到远程仓库（企业私服，CI/CD 用）

# ===== 组合命令（最常用） =====
mvn clean package          # 先清理再打包（推荐，保证干净构建）
mvn clean package -DskipTests   # 打包但跳过测试（赶时间上线用）
mvn clean install          # 清理 + 打包 + 装到本地仓库

# ===== Spring Boot 专属 =====
mvn spring-boot:run        # 直接运行 Spring Boot 应用（开发时常用）
mvn spring-boot:repackage # 重新打包成可执行 jar（plugin 自动做）

# ===== 依赖排查 =====
mvn dependency:tree        # 打印依赖树（排查冲突必备）
mvn dependency:analyze     # 分析依赖（找出未使用/未声明的依赖）
mvn dependency:tree -Dincludes=com.fasterxml.jackson  # 过滤特定依赖

# ===== 其他实用 =====
mvn -v / -version          # 查看版本
mvn validate               # 校验项目是否正确（不编译）
mvn clean compile -o      # -o 离线模式，不联网下载
mvn install -U            # -U 强制更新 SNAPSHOT 和插件
mvn -pl module-a -am build # 多模块只构建 module-a 及其依赖
```

## 4.3 命令与生命周期的关系

```
你输入的命令          实际执行的阶段
─────────────────────────────────────────────
mvn clean        →  clean
mvn compile      →  validate → compile
mvn test         →  validate → compile → test
mvn package      →  validate → compile → test → package
mvn install      →  validate → compile → test → package → install
                    （install 会包含前面所有阶段！）
```

> **⚠️ 注意**：`mvn install` 会**先跑测试**。如果测试失败，install 就会中断。想跳过测试加 `-DskipTests`。

## 4.4 常用参数

| 参数 | 作用 | 前端类比 |
|---|---|---|
| `-DskipTests` | 跳过测试执行（仍编译测试代码） | `npm test -- --skip` |
| `-Dmaven.test.skip=true` | 跳过测试编译和执行（更彻底） | — |
| `-U` | 强制更新 SNAPSHOT 依赖和插件 | `npm update` |
| `-o` | 离线模式，只用本地仓库 | `npm install --offline` |
| `-P dev` | 激活 id 为 dev 的 profile | `--mode=dev` |
| `-pl <模块>` | 只构建指定模块（多模块项目） | monorepo 单包构建 |
| `-am` | 同时构建依赖的模块 | — |
| `-D<属性>=<值>` | 传参覆盖属性 | `--define` |

---

# 第五章：依赖管理

## 5.1 依赖声明

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>     <!-- 组织 -->
        <artifactId>spring-boot-starter-web</artifactId> <!-- 模块名 -->
        <version>3.2.0</version>                         <!-- 版本（继承父pom可省略） -->
        <scope>compile</scope>                            <!-- 依赖范围 -->
        <exclusions>                                      <!-- 排除传递依赖 -->
            <exclusion>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-starter-tomcat</artifactId>
            </exclusion>
        </exclusions>
    </dependency>
</dependencies>
```

## 5.2 依赖范围（scope）

scope 决定依赖在**什么阶段**、**是否打进最终产物**中生效。这是和 npm 最大的区别之一：

| scope | 编译期 | 测试期 | 运行期 | 打进 jar | 前端类比 |
|---|---|---|---|---|---|
| `compile`（默认） | ✅ | ✅ | ✅ | ✅ | `dependencies` |
| `test` | ❌ | ✅ | ❌ | ❌ | `devDependencies` |
| `provided` | ✅ | ✅ | ❌ | ❌ | —（运行环境已提供） |
| `runtime` | ❌ | ✅ | ✅ | ✅ | —（运行时才需要） |
| `system` | ✅ | ✅ | ❌ | ❌ | —（手动指定本地 jar，不推荐） |
| `import` | — | — | — | — | 仅用于 dependencyManagement |

```xml
<!-- 测试依赖：只在测试时用，不打包 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>

<!-- provided：编译需要，但运行时容器已提供，不打包 -->
<dependency>
    <groupId>jakarta.servlet</groupId>
    <artifactId>jakarta.servlet-api</artifactId>
    <scope>provided</scope>
</dependency>

<!-- runtime：编译不需要，运行时才需要（如 JDBC 驱动） -->
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <scope>runtime</scope>
</dependency>
```

> **💡 前端类比**：
> - `compile` ≈ `dependencies`（生产和开发都要）
> - `test` ≈ `devDependencies`（只在测试时用）
> - `provided` ≈ peerDependencies（我知道运行环境已经有了，别重复装）

## 5.3 传递依赖

Maven 会**自动引入依赖的依赖**。比如：

```
你的项目
  └── 依赖 A (spring-boot-starter-web)
        ├── 依赖 B (spring-web)        ← 自动引入
        ├── 依赖 C (spring-webmvc)     ← 自动引入
        └── 依赖 D (tomcat-embed-core) ← 自动引入
```

> **💡 前端类比**：和 npm 的传递依赖一样，你装了 express，express 依赖的 body-parser 等也会自动装上。区别是 Maven 装在全局本地仓库，npm 装在项目 node_modules。

## 5.4 依赖冲突与解决

### 冲突的产生

当多个依赖间接引入了**同一个 jar 的不同版本**，Maven 需要决定用哪个：

```
你的项目
  ├── 依赖 A → 引入 X:v2.0
  └── 依赖 B → 引入 X:v1.0
  → 冲突！用哪个版本？
```

### Maven 的冲突解决规则

```
规则1：最短路径优先
  A → C → X(v2.0)    路径长度 2
  B → D → E → X(v1.0) 路径长度 3
  → 选 v2.0（路径短的赢）

规则2：同路径时，声明顺序优先
  先声明的依赖赢
```

### 排查冲突

```bash
# 打印完整依赖树
mvn dependency:tree

# 过滤查看某个依赖的来源
mvn dependency:tree -Dincludes=com.fasterxml.jackson.core:jackson-databind

# 输出示例：
# [INFO] com.example:demo:jar:1.0.0
# [INFO] +- org.springframework.boot:spring-boot-starter-web:jar:3.2.0:compile
# [INFO] |  +- org.springframework.boot:spring-boot-starter-json:jar:3.2.0:compile
# [INFO] |  |  \- com.fasterxml.jackson.core:jackson-databind:jar:2.15.3:compile  ← 实际用的版本
# [INFO] +- com.baomidou:mybatis-plus:jar:3.5.5:compile
# [INFO] |  \- com.fasterxml.jackson.core:jackson-databind:jar:2.13.0:compile(omitted)  ← 被忽略
```

### 主动排除冲突依赖

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus</artifactId>
    <version>3.5.5</version>
    <exclusions>
        <!-- 排除它自带的旧版 jackson，用 Spring Boot 管理的新版 -->
        <exclusion>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

## 5.5 `<dependencyManagement>` 统一版本

在多模块项目或需要统一版本时，用 `dependencyManagement` **只声明版本，不真正引入**：

```xml
<!-- 父 pom：只管版本，不引入依赖 -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.baomidou</groupId>
            <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
            <version>3.5.5</version>
        </dependency>
    </dependencies>
</dependencyManagement>

<!-- 子模块：引入时不写 version，自动用父 pom 声明的版本 -->
<dependencies>
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
        <!-- 不写 version，由 dependencyManagement 统一管理 -->
    </dependency>
</dependencies>
```

> **💡 前端类比**：`dependencyManagement` ≈ monorepo 根 `package.json` 里统一声明的版本号，子包引用时不指定版本。Spring Boot 的 `spring-boot-dependencies`（通过 parent 继承）就是这么管理几百个依赖版本的。

---

# 第六章：Maven 仓库与镜像配置

## 6.1 三层仓库体系

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   你的项目 pom.xml 声明依赖                                    │
│         │                                                    │
│         ▼                                                    │
│   ┌──────────────────┐  找不到时向上找                       │
│   │ 1. 本地仓库        │  路径：~/.m2/repository              │
│   │   （你的电脑上）    │  所有项目共享缓存                     │
│   └────────┬─────────┘                                       │
│            │ 没有就下载                                       │
│            ▼                                                  │
│   ┌──────────────────┐  找不到时向上找                       │
│   │ 2. 远程仓库/私服   │  企业内部 Nexus/公司私服              │
│   │   （公司内部）      │  团队共享，缓存中央仓库               │
│   └────────┬─────────┘                                       │
│            │ 没有就下载                                       │
│            ▼                                                  │
│   ┌──────────────────┐                                       │
│   │ 3. 中央仓库        │  https://repo.maven.apache.org       │
│   │   （全球公开）      │  Maven 官方维护，所有公开 jar          │
│   └──────────────────┘                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

> **💡 前端类比**：
> - 本地仓库 ≈ `node_modules`（但全局共享）
> - 中央仓库 ≈ `registry.npmjs.org`
> - 私服 ≈ 公司自建 npm registry（如 Verdaccio）

## 6.2 本地仓库

默认路径：`~/.m2/repository`（Windows: `C:\Users\你的用户名\.m2\repository`）

```xml
<!-- 在 settings.xml 中修改本地仓库位置 -->
<settings>
    <localRepository>D:/maven-repo</localRepository>
</settings>
```

> **⚠️ 实用技巧**：依赖下载出问题、版本冲突搞不定时，直接去本地仓库**删掉对应依赖的目录**，再重新构建让 Maven 重新下载，往往能解决疑难杂症。

## 6.3 配置国内镜像（必做！）

中央仓库在国内访问很慢，**强烈建议配置阿里云镜像**。编辑 `~/.m2/settings.xml`（不存在就新建）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.2.0
          https://maven.apache.org/xsd/settings-1.2.0.xsd">

    <!-- 本地仓库路径（可选） -->
    <localRepository>D:/maven-repo</localRepository>

    <mirrors>
        <!-- 阿里云公共仓库（代理中央仓库，国内速度快很多） -->
        <mirror>
            <id>aliyunmaven</id>
            <mirrorOf>*</mirrorOf>            <!-- * 表示代理所有仓库 -->
            <name>阿里云公共仓库</name>
            <url>https://maven.aliyun.com/repository/public</url>
        </mirror>

        <!-- 也可以只代理中央仓库 -->
        <!-- <mirrorOf>central</mirrorOf> -->
    </mirrors>

    <!-- 默认激活的 profile（指定 JDK 版本等） -->
    <profiles>
        <profile>
            <id>jdk-17</id>
            <activation>
                <activeByDefault>true</activeByDefault>
                <jdk>17</jdk>
            </activation>
            <properties>
                <maven.compiler.source>17</maven.compiler.source>
                <maven.compiler.target>17</maven.compiler.target>
            </properties>
        </profile>
    </profiles>
</settings>
```

> **💡 前端类比**：配置镜像 ≈ 在 `.npmrc` 里写 `registry=https://registry.npmmirror.com`，把 npm 源换成淘宝镜像。**这是国内开发的第一步配置**。

## 6.4 settings.xml 的位置

| 位置 | 作用范围 | 路径 |
|---|---|---|
| 全局配置 | 所有用户、所有项目 | `${maven.home}/conf/settings.xml` |
| 用户配置 | 当前用户的所有项目 | `~/.m2/settings.xml`（**推荐改这个**） |
| IDEA 配置 | IDEA 使用的 Maven 设置 | IDEA → Settings → Build → Maven |

> **⚠️ 常见坑**：IDEA 可能用了**自带的 Maven**而非你配置的，导致镜像没生效。在 IDEA 设置里把 Maven 路径和 settings.xml 都指向你自己的。

---

# 第七章：Spring Boot 中的 Maven 实战

## 7.1 Spring Boot 的 Maven 设计

Spring Boot 把 Maven 用到了极致，核心有三件套：

```
┌─────────────────────────────────────────────────────────────┐
│  Spring Boot 的 Maven 三件套                                  │
│                                                              │
│  1. spring-boot-starter-parent  （父 pom）                    │
│     → 统一管理几百个依赖版本 + 默认插件配置                     │
│                                                              │
│  2. spring-boot-starter-*  （启动器）                          │
│     → 按功能打包的依赖集合，引入一个就获得整套能力              │
│     → 如 starter-web = Spring MVC + Tomcat + JSON            │
│                                                              │
│  3. spring-boot-maven-plugin  （打包插件）                     │
│     → 把项目打成「可执行 jar」（内嵌 Tomcat，java -jar 即跑）   │
└─────────────────────────────────────────────────────────────┘
```

## 7.2 Starter 启动器机制

Starter 是 Spring Boot 的精髓——**引入一个 starter，获得一整套功能依赖**：

```xml
<!-- 引入 Web 功能：Spring MVC + 内嵌 Tomcat + Jackson JSON -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- 引入 JPA 数据访问：Spring Data JPA + Hibernate -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
```

| 常用 Starter | 引入的能力 | 前端类比 |
|---|---|---|
| `spring-boot-starter-web` | Web 开发（MVC + Tomcat + JSON） | `npm i express` |
| `spring-boot-starter-data-jpa` | 数据库 ORM（JPA + Hibernate） | `npm i typeorm` |
| `spring-boot-starter-validation` | 参数校验 | `npm i joi` |
| `spring-boot-starter-security` | 认证授权 | `npm i passport` |
| `spring-boot-starter-actuator` | 应用监控端点 | 健康检查中间件 |
| `spring-boot-starter-test` | 测试套件（JUnit + Mockito） | `npm i jest` |
| `spring-boot-starter-redis` | Redis 缓存 | `npm i ioredis` |

> **💡 前端类比**：Starter ≈ 一个"全家桶"npm 包，装一个就把相关生态都带上，不用自己一个个挑版本。继承 parent 后**不用写 version**，版本由父 pom 统一管理。

## 7.3 可执行 jar 与打包插件

普通 Maven 打出的 jar 不能直接 `java -jar` 运行（没有主类信息、依赖 jar 没打进去）。Spring Boot 的打包插件解决了这个问题：

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
            <!-- 父 pom 已配置默认行为，通常不用写 version 和执行 -->
        </plugin>
    </plugins>
</build>
```

打包流程：

```
mvn clean package
       │
       ▼
┌──────────────────────────────────────────┐
│  1. 编译 src/main/java → target/classes   │
│  2. 运行测试                              │
│  3. 打成普通 jar：demo-1.0.0.jar          │
│  4. spring-boot-maven-plugin 重新打包     │
│     → 把所有依赖 jar 解压合并进一个 fat jar │
│     → 内嵌 Tomcat                         │
│     → 指定主类（DemoApplication）          │
│  产物：target/demo-1.0.0.jar（可执行）     │
└──────────────────────────────────────────┘

# 直接运行（无需装 Tomcat！）
java -jar target/demo-1.0.0.jar
```

> **💡 前端类比**：fat jar ≈ 用 webpack/vite 把所有依赖打包成单个 `bundle.js`，一个文件包含一切，部署时只需这一个文件。

## 7.4 多 Profile 环境隔离

实际项目有开发、测试、生产多套环境，Maven profile 可以按环境切换配置：

```xml
<profiles>
    <!-- 开发环境（默认激活） -->
    <profile>
        <id>dev</id>
        <properties>
            <env>dev</env>
        </properties>
        <activation>
            <activeByDefault>true</activeByDefault>
        </activation>
    </profile>
    <!-- 生产环境 -->
    <profile>
        <id>prod</id>
        <properties>
            <env>prod</env>
        </properties>
    </profile>
</profiles>

<build>
    <!-- 资源过滤：用 Maven 属性替换配置文件中的占位符 -->
    <resources>
        <resource>
            <directory>src/main/resources</directory>
            <filtering>true</filtering>
        </resource>
    </resources>
</build>
```

```bash
# 激活生产环境打包
mvn clean package -P prod

# 也可以结合 Spring Boot 的 profile
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

> **💡 提示**：Spring Boot 自身也有 `spring.profiles.active` 机制（在 application.yml 里配），和 Maven profile 是两套体系。通常用 Maven profile 控制**打包时**注入的配置，用 Spring profile 控制**运行时**激活的 yml。新手建议先用 Spring Boot 自带的 `application-dev.yml` / `application-prod.yml`，更简单。

## 7.5 多模块项目结构

企业项目通常拆成多个 Maven 模块（一个父 pom + 多个子模块）：

```
my-project/
├── pom.xml                    # 父 pom（packaging=pom，只管理子模块）
├── my-common/                 # 公共模块
│   ├── pom.xml
│   └── src/
├── my-domain/                 # 领域模型模块
│   ├── pom.xml
│   └── src/
├── my-web/                    # Web 启动模块
│   ├── pom.xml
│   └── src/
└── my-service/               # 业务逻辑模块
    ├── pom.xml
    └── src/
```

父 pom：

```xml
<groupId>com.example</groupId>
<artifactId>my-project</artifactId>
<version>1.0.0</version>
<packaging>pom</packaging>  <!-- 父模块打包方式必须是 pom -->

<modules>
    <module>my-common</module>
    <module>my-domain</module>
    <module>my-service</module>
    <module>my-web</module>
</modules>

<!-- 用 dependencyManagement 统一子模块间依赖版本 -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>my-common</artifactId>
            <version>${project.version}</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

子模块引用其他模块：

```xml
<!-- my-web/pom.xml -->
<dependency>
    <groupId>com.example</groupId>
    <artifactId>my-service</artifactId>
    <!-- 版本由父 pom 的 dependencyManagement 管理 -->
</dependency>
```

```bash
# 构建整个多模块项目
mvn clean package

# 只构建 my-web 及它依赖的模块（-am = also make）
mvn clean package -pl my-web -am
```

> **💡 前端类比**：多模块 ≈ monorepo（pnpm workspace / lerna），父 pom ≈ 根 package.json，子模块 ≈ packages/* 下的子包。

---

# 第八章：常见问题排查

## 8.1 排查总原则

```
Maven 问题排查顺序：
1. 看报错信息（依赖找不到？版本冲突？编译失败？）
2. 用 mvn dependency:tree 看依赖树
3. 检查 pom.xml 的坐标、版本、scope 是否正确
4. 检查 settings.xml 镜像配置是否生效
5. 必要时删本地仓库对应依赖，重新下载
```

## 8.2 案例一：依赖下载失败

**现象**：构建时报 `Could not resolve dependencies` / `Failure to transfer ...`。

```
[ERROR] Failed to execute goal on project demo:
Could not resolve dependencies for project com.example:demo:jar:1.0.0:
Failed to collect dependencies at org.springframework.boot:spring-boot-starter-web:jar:3.2.0:
... was cached in the local repository, resolution will not be reattempted until the update interval has elapsed
```

**排查步骤**：

```
Step 1: 看关键词
    "was cached ... will not be reattempted" = 之前下载失败被缓存了，不会自动重试

Step 2: 强制更新
    mvn clean install -U    # -U 强制更新 SNAPSHOT 和失败的下载

Step 3: 还不行就删本地缓存
    找到 ~/.m2/repository 下对应依赖的目录，整个删掉
    如 ~/.m2/repository/org/springframework/boot/spring-boot-starter-web/
    删掉后重新 mvn clean package

Step 4: 检查镜像配置
    确认 settings.xml 的 mirror 配置生效（看 IDEA 用的哪个 settings.xml）
```

## 8.3 案例二：依赖版本冲突

**现象**：项目启动报 `ClassNotFoundException` 或 `NoSuchMethodError`，明明依赖里有这个类。

**原因**：传递依赖引入了**旧版本**的 jar，覆盖了你需要的新版本。

**排查步骤**：

```bash
# 1. 查看依赖树，找到冲突的依赖
mvn dependency:tree -Dincludes=com.fasterxml.jackson.core

# 输出：
# [INFO] +- spring-boot-starter-web
# [INFO] |  \- jackson-databind:2.15.3   ← 实际用的（新版）
# [INFO] +- mybatis-plus
# [INFO] |  \- jackson-databind:2.13.0 (omitted)  ← 被忽略的（旧版）

# 2. 如果实际用的版本不对，用 exclusions 排除错误来源
```

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus</artifactId>
    <exclusions>
        <exclusion>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

## 8.4 案例三：编译版本不对

**现象**：报 `invalid target release: 17` 或 `Java 17 but you are using ... `。

**原因**：Maven 用的 JDK 版本和项目要求的不一致。

**排查与修复**：

```bash
# 1. 检查 Maven 用的 Java 版本
mvn -version
# 看 "Java version" 那行

# 2. 检查环境变量 JAVA_HOME 指向的 JDK
echo $JAVA_HOME
```

```xml
<!-- 3. 在 pom.xml 中指定 Java 版本（继承 parent 时用这个属性） -->
<properties>
    <java.version>17</java.version>
</properties>

<!-- 或不继承 parent 时显式配置编译插件 -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <configuration>
        <source>17</source>
        <target>17</target>
    </configuration>
</plugin>
```

## 8.5 案例四：打包后运行找不到主类

**现象**：`java -jar demo.jar` 报 `no main manifest attribute` 或找不到启动类。

**原因**：没配置 `spring-boot-maven-plugin`，打出来的是普通 jar。

**修复**：

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
            <!-- 如需指定主类（多模块时可能需要） -->
            <configuration>
                <mainClass>com.example.demo.DemoApplication</mainClass>
            </configuration>
            <executions>
                <execution>
                    <goals>
                        <goal>repackage</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

## 8.6 案例五：IDEA 改了 pom.xml 没生效

**现象**：在 pom.xml 加了依赖，但代码里 import 还是报红。

**排查步骤**：

```
Step 1: 手动刷新 Maven
    IDEA 右侧 Maven 面板 → 点刷新按钮（🔄）
    或快捷键 Ctrl+Shift+O（Mac: Cmd+Shift+I）

Step 2: 开启自动导入
    IDEA 会弹窗 "Maven changes detected, import?" → 选 Enable Auto-Import
    或 Settings → Build → Maven → Importing → Import Maven projects automatically

Step 3: 重新加载项目
    右键 pom.xml → Maven → Reload Project

Step 4: 实在不行，Invalidate Caches and Restart
    File → Invalidate Caches → Invalidate and Restart
```

---

# 第九章：速查表

## 9.1 常用命令速查

| 命令 | 作用 | 使用场景 |
|---|---|---|
| `mvn clean` | 删除 target/ | 构建前清理 |
| `mvn compile` | 编译源代码 | 检查能否编译通过 |
| `mvn test` | 运行单元测试 | 提交前跑测试 |
| `mvn package` | 打包 | 生成 jar/war |
| `mvn install` | 打包并装到本地仓库 | 多模块项目互相依赖时 |
| `mvn clean package -DskipTests` | 跳过测试打包 | 赶时间上线 |
| `mvn spring-boot:run` | 运行 Spring Boot 应用 | 本地开发启动 |
| `mvn dependency:tree` | 查看依赖树 | 排查依赖冲突 |
| `mvn dependency:analyze` | 分析依赖使用情况 | 找未使用/未声明依赖 |
| `mvn clean install -U` | 强制更新依赖 | 依赖下载异常时 |
| `mvn -o package` | 离线打包 | 无网络环境 |
| `mvn -P prod package` | 激活 prod profile | 多环境打包 |

## 9.2 依赖范围速查

| scope | 何时用 | 类比 |
|---|---|---|
| `compile`（默认） | 编译测试运行都要 | `dependencies` |
| `test` | 只测试时用（JUnit） | `devDependencies` |
| `provided` | 运行环境已提供（Servlet API） | `peerDependencies` |
| `runtime` | 运行时才需要（JDBC 驱动） | — |
| `system` | 本地 jar（不推荐） | — |
| `import` | dependencyManagement 中用 | — |

## 9.3 pom.xml 核心标签速查

| 标签 | 作用 | 前端类比 |
|---|---|---|
| `<parent>` | 继承父 pom | 继承基础配置 |
| `<groupId>` | 组织标识 | npm scope |
| `<artifactId>` | 模块名 | npm 包名 |
| `<version>` | 版本号 | npm 版本 |
| `<packaging>` | 打包方式 jar/war/pom | — |
| `<properties>` | 属性/版本号 | 环境变量 |
| `<dependencies>` | 依赖列表 | dependencies |
| `<dependencyManagement>` | 版本管理（不引入） | monorepo 版本统一 |
| `<build><plugins>` | 构建插件 | webpack/vite 配置 |
| `<exclusions>` | 排除传递依赖 | overrides |
| `<profiles>` | 多环境配置 | —mode 参数 |

## 9.4 Spring Boot 常用依赖速查

| 依赖 | 作用 |
|---|---|
| `spring-boot-starter-web` | Web 开发（MVC + Tomcat） |
| `spring-boot-starter-data-jpa` | 数据库 ORM |
| `spring-boot-starter-validation` | 参数校验 |
| `spring-boot-starter-security` | 认证授权 |
| `spring-boot-starter-actuator` | 应用监控 |
| `spring-boot-starter-test` | 测试套件 |
| `spring-boot-starter-data-redis` | Redis |
| `spring-boot-starter-webflux` | 响应式 Web |
| `mysql-connector-j` | MySQL 驱动 |
| `lombok` | 简化样板代码 |
| `mybatis-plus-spring-boot3-starter` | MyBatis-Plus（国内常用） |

## 9.5 settings.xml 镜像速查（国内推荐）

```xml
<mirrors>
    <mirror>
        <id>aliyunmaven</id>
        <mirrorOf>*</mirrorOf>
        <name>阿里云公共仓库</name>
        <url>https://maven.aliyun.com/repository/public</url>
    </mirror>
</mirrors>
```

---

## 📋 附录：Maven 避坑指南

| 坑 | 说明 | 正确做法 |
|---|---|---|
| 依赖下载失败被缓存 | Maven 缓存了失败结果，不自动重试 | 用 `-U` 强制更新，或删本地仓库对应目录 |
| 版本冲突 | 传递依赖引入旧版本覆盖新版本 | `mvn dependency:tree` 排查 + `<exclusions>` 排除 |
| `mvn install` 跑测试失败 | install 会先执行 test 阶段 | 加 `-DskipTests` 跳过测试 |
| IDEA 改 pom 没生效 | 没自动导入依赖 | 开启 Auto-Import 或手动 Reload Project |
| 镜像没生效 | IDEA 用了自带 Maven | IDEA 设置里指定自己的 Maven 和 settings.xml |
| 打包后不能运行 | 没配 spring-boot-maven-plugin | 加上插件打成可执行 jar |
| JDK 版本不对 | Maven 用的 JDK 与项目不符 | 检查 `JAVA_HOME` 和 pom 的 `java.version` |
| 本地仓库越来越大 | 所有项目共享缓存，越积越多 | 定期清理 `~/.m2/repository` 无用依赖 |
| SNAPSHOT 旧版本不更新 | SNAPSHOT 有更新间隔 | 用 `-U` 强制更新快照版本 |
| 多模块循环依赖 | A 依赖 B，B 又依赖 A | 重构拆分，把公共部分提到独立模块 |

---

> 📝 **最后的话**：Maven 看似配置繁琐，但日常开发真正高频用的就几样——**看懂 pom.xml、会跑 `clean package`、会用 `dependency:tree` 排查冲突、配好国内镜像**。结合 Spring Boot 的 parent + starter 机制，大部分依赖版本都不用你操心。遇到报错先看依赖树，再删本地缓存重下，基本能解决 80% 的问题。剩下的 20% 去搜报错关键词 + Maven 版本，总能找到答案。
