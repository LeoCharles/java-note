# 42 - Spring Boot 容器化部署 Docker

> 对应项目模块：`demo-docker`
> 前置知识：已学完前 41 个模块，了解 Spring Boot 启动、打包（jar）、运行的基本流程
> 学习目标：理解 Docker 是什么、为什么后端要容器化，能看懂 Dockerfile 每条指令，掌握手动构建和 Maven 插件两种打包方式，把 Spring Boot 应用跑进容器。

---

## 一、本模块要解决什么问题？

在前面的模块里，我们启动 Spring Boot 应用的方式是：

```sh
java -jar demo-xxx.jar
```

这已经很方便了——部署环境只要有 JDK 就能跑。但实际生产环境会面临一连串问题：

1. **环境不一致**："在我电脑上能跑"的经典难题。开发用 JDK 8，测试用 JDK 11，生产用 JDK 8 但打了不同补丁，行为微妙不同。
2. **依赖混乱**：服务器上装了 MySQL 客户端、Redis 客户端、各种工具，版本各异，互相干扰。
3. **部署繁琐**：每台服务器都要手动装 JDK、配环境变量、传 jar 包、写启动脚本，扩容 10 台机器就要重复 10 次。
4. **隔离性差**：多个应用跑在同一台机器上，端口冲突、资源争抢、一个崩了连累一片。

**Docker 解决的核心问题：把应用 + 它的整个运行环境打包成一个不可变镜像，到处运行。**

> 💡 前端类比：Docker 之于后端，就像 Vercel/Netlify 之于前端——你不用关心服务器装了什么，push 代码就自动构建部署。Docker 把"环境"也变成代码（Dockerfile），像 Vite 的 `vite.config.ts` 一样可版本管理、可复现。区别是 Docker 更底层，它连操作系统层面的依赖都打包了。

本模块演示：写一个最简单的 Spring Boot 接口，用 Dockerfile 把它打包成镜像，在容器里跑起来，外部能访问。

---

## 二、项目结构

```
demo-docker/
├── pom.xml                          # Maven 配置（含 dockerfile-maven-plugin）
├── Dockerfile                       # 镜像构建脚本（核心）
├── README.md
└── src/main/
    ├── java/com/xkcoding/docker/
    │   ├── SpringBootDemoDockerApplication.java   # 启动类
    │   └── controller/HelloController.java        # 测试接口
    └── resources/
        └── application.yml           # 配置文件
```

相比前面的模块，这里多了一个根目录下的 `Dockerfile`——它是构建镜像的"配方"。整个模块的业务代码极简（就一个 Hello 接口），重点全在 Dockerfile 和 pom 的打包配置上。

---

## 三、逐行拆解业务代码

先快速过一下业务代码，它们和前面模块几乎一样，只是为容器化提供一个可运行的应用。

### 3.1 启动类

```java
@SpringBootApplication
public class SpringBootDemoDockerApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoDockerApplication.class, args);
    }
}
```

标准的 Spring Boot 启动类，`@SpringBootApplication` 开启自动配置和组件扫描，`SpringApplication.run` 启动内嵌 Tomcat。没有新知识点。

### 3.2 测试接口

```java
@RestController
@RequestMapping
public class HelloController {
    @GetMapping
    public String hello() {
        return "Hello,From Docker!";
    }
}
```

- `@RestController`：返回值直接写进响应体。
- `@RequestMapping` 加在类上但不写路径，相当于根路径。
- `@GetMapping` 也不写路径，表示处理 `GET /`（根路径）请求。

注意 `application.yml` 里配了 `context-path: /demo`，所以完整访问路径是 `http://localhost:8080/demo/`，返回 `Hello,From Docker!`。这个接口的作用就是验证容器里的应用是否正常启动。

### 3.3 配置文件

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

端口 8080，上下文路径 `/demo`。和 HelloWorld 模块一致。容器化后，这个 8080 是**容器内部**的端口，外部访问需要做端口映射（见后文）。

---

## 四、逐行拆解 Dockerfile（本模块核心）

`Dockerfile` 是构建 Docker 镜像的脚本，每条指令对应镜像的一层。本模块的 Dockerfile：

```dockerfile
# 基础镜像
FROM openjdk:8-jdk-alpine

# 作者信息
MAINTAINER "Yangkai.Shen 237497819@qq.com"

# 添加一个存储空间
VOLUME /tmp

# 暴露8080端口
EXPOSE 8080

# 添加变量，如果使用dockerfile-maven-plugin，则会自动替换这里的变量内容
ARG JAR_FILE=target/spring-boot-demo-docker.jar

# 往容器中添加jar包
ADD ${JAR_FILE} app.jar

# 启动镜像自动运行程序
ENTRYPOINT ["java","-Djava.security.egd=file:/dev/urandom","-jar","/app.jar"]
```

逐条讲解：

### 4.1 `FROM` —— 指定基础镜像

```dockerfile
FROM openjdk:8-jdk-alpine
```

- `FROM` 是 Dockerfile 的第一条指令（除了 ARG），指定本镜像基于哪个镜像构建。
- `openjdk:8-jdk-alpine`：基于 Alpine Linux（一个只有 5MB 的极简 Linux 发行版）+ JDK 8 的官方镜像。选 Alpine 是因为它体积小，最终镜像只有约 119MB（README 里能看到）。

> 💡 前端类比：`FROM` 像 `extends`，你的镜像继承了基础镜像的全部内容。选基础镜像就像选 `node:18-alpine` 作为前端构建镜像——alpine 版本体积小、拉取快。

### 4.2 `MAINTAINER` —— 维护者信息（已废弃）

```dockerfile
MAINTAINER "Yangkai.Shen 237497819@qq.com"
```

- 标注镜像作者。**注意：这个指令在新版 Docker 中已废弃**，官方推荐用 `LABEL` 替代：

```dockerfile
LABEL maintainer="Yangkai.Shen 237497819@qq.com"
```

`LABEL` 更通用，可以加任意键值对元数据。

### 4.3 `VOLUME` —— 声明匿名卷

```dockerfile
VOLUME /tmp
```

- `VOLUME` 声明一个挂载点。这里把容器的 `/tmp` 目录声明为卷。
- Spring Boot 运行时会在 `/tmp` 下创建临时文件（Tomcat 的工作目录等）。声明成卷后，这些临时数据写到宿主机的某个目录，而不是容器的可写层，避免容器存储层膨胀，也便于清理。
- 这是一种**声明式建议**：即使运行时不手动挂载，Docker 也会自动分配一个匿名卷。

### 4.4 `EXPOSE` —— 声明端口

```dockerfile
EXPOSE 8080
```

- 声明容器内应用监听 8080 端口。
- **关键理解：`EXPOSE` 只是声明，并不会自动把端口映射到宿主机。** 真正的端口映射要在 `docker run -p 9090:8080` 时指定。`EXPOSE` 的作用是文档化 + 方便 `-P`（大写）随机映射。

> 💡 前端类比：像 package.json 里的 `exports` 字段声明了模块对外暴露的入口，但别人要不要引入、怎么引入是另一回事。`EXPOSE` 声明"我用了 8080"，但外部要不要映射、映射到哪个端口，是 `docker run` 时决定的。

### 4.5 `ARG` —— 构建期变量

```dockerfile
ARG JAR_FILE=target/spring-boot-demo-docker.jar
```

- `ARG` 定义一个**构建期**变量（不是运行期）。这里定义 `JAR_FILE`，默认值是 `target/spring-boot-demo-docker.jar`。
- 如果用 Maven 的 `dockerfile-maven-plugin`，它会在构建时把这个变量替换成实际 jar 路径（见 pom 配置）。这样 Dockerfile 和具体 jar 名解耦，换 jar 名不用改 Dockerfile。

> 💡 前端类比：`ARG` 像 Vite 的 `define` 或环境变量 `VITE_*`，在**构建时**替换，运行时已经是固定值。区别是 Docker 的 ARG 只在构建 Docker 镜像时生效，容器运行时拿不到这个值（运行时要用 `ENV`）。

### 4.6 `ADD` —— 添加文件到镜像

```dockerfile
ADD ${JAR_FILE} app.jar
```

- 把宿主机上的 jar 包（由 `JAR_FILE` 指定）添加到镜像的根目录，重命名为 `app.jar`。
- `ADD` 和 `COPY` 的区别：`ADD` 能自动解压 tar 包、能从 URL 下载；`COPY` 只能复制本地文件。**最佳实践：纯复制文件用 `COPY` 更清晰**，这里用 `ADD` 是老写法。

### 4.7 `ENTRYPOINT` —— 容器启动命令

```dockerfile
ENTRYPOINT ["java","-Djava.security.egd=file:/dev/urandom","-jar","/app.jar"]
```

- `ENTRYPOINT` 指定容器启动时执行的命令。这里是启动 Java 应用。
- `["java", "-jar", "/app.jar"]` 是 JSON 数组格式（exec 形式），直接执行，不经过 shell。
- `-Djava.security.egd=file:/dev/urandom`：指定随机数生成器的熵源。Tomcat 启动时需要随机数生成 Session ID，默认用 `/dev/random`（阻塞式，熵不足时会卡住），换成 `/dev/urandom`（非阻塞）能加速启动，尤其在容器这种熵有限的环境。

> 💡 前端类比：`ENTRYPOINT` 像 `package.json` 的 `scripts.start`，容器一启动就跑这个命令。区别是 `ENTRYPOINT` 是固定的，`CMD` 可以被 `docker run image cmd` 覆盖，两者配合能实现"固定程序 + 可变参数"的模式。

---

## 五、逐行拆解 pom.xml 的打包配置

### 5.1 基础部分

```xml
<artifactId>demo-docker</artifactId>
<version>1.0.0-SNAPSHOT</version>
<packaging>jar</packaging>

<parent>
    <groupId>com.xkcoding</groupId>
    <artifactId>spring-boot-demo</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</parent>
```

继承父 POM，打包成 jar。和前面模块一致。

### 5.2 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

只引了 web 和 test 两个 Starter，业务极简。

### 5.3 构建插件（重点）

```xml
<properties>
    <dockerfile-version>1.4.9</dockerfile-version>
</properties>

<build>
    <finalName>demo-docker</finalName>
    <plugins>
        <!-- 1. Spring Boot 打包插件：打成可执行 jar -->
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>

        <!-- 2. dockerfile-maven-plugin：根据 Dockerfile 构建镜像 -->
        <plugin>
            <groupId>com.spotify</groupId>
            <artifactId>dockerfile-maven-plugin</artifactId>
            <version>${dockerfile-version}</version>
            <configuration>
                <repository>${project.build.finalName}</repository>
                <tag>${project.version}</tag>
                <buildArgs>
                    <JAR_FILE>target/${project.build.finalName}.jar</JAR_FILE>
                </buildArgs>
            </configuration>
            <!-- executions 被注释掉了 -->
        </plugin>
    </plugins>
</build>
```

**两个插件协作：**

1. `spring-boot-maven-plugin`：先把项目打成可执行 jar（`demo-docker.jar`），放在 `target/` 下。
2. `dockerfile-maven-plugin`（Spotify 出品）：读取 `Dockerfile`，把 `JAR_FILE` 这个构建参数传进去（替换 Dockerfile 里的 `ARG JAR_FILE` 默认值），调用 `docker build` 生成镜像。

**配置项含义：**

| 配置 | 作用 |
| --- | --- |
| `<repository>${project.build.finalName}</repository>` | 镜像名，这里是 `demo-docker` |
| `<tag>${project.version}</tag>` | 镜像标签，这里是 `1.0.0-SNAPSHOT` |
| `<buildArgs><JAR_FILE>...</JAR_FILE></buildArgs>` | 传给 Dockerfile 的 ARG 变量值 |

**被注释的 `executions`：**

```xml
<!-- <executions>-->
<!--     <execution>-->
<!--         <id>default</id>-->
<!--         <phase>package</phase>-->
<!--         <goals><goal>build</goal></goals>-->
<!--     </execution>-->
<!-- </executions>-->
```

这段如果打开，会在执行 `mvn package` 时**自动**触发 `docker build`。本项目把它注释掉了，所以需要手动执行 `mvn dockerfile:build`。README 里展示了打开它的写法。

> ⚠️ 注意：`dockerfile-maven-plugin` 是 Spotify 的老插件，现已停止维护。现代项目更推荐 `docker-maven-plugin`（JIB、Spring Boot 自带的 `spring-boot:build-image` 用 Buildpacks、或 `dockerfile-maven-plugin` 的替代品）。但原理一致，理解了这套，换插件只是改配置。

---

## 六、运行与验证

### 6.1 方式一：手动构建镜像

**步骤 1：先打 jar 包**

```sh
mvn clean package -DskipTests
```

生成 `target/demo-docker.jar`。

**步骤 2：构建 Docker 镜像**

在 `demo-docker` 目录下（Dockerfile 所在目录）执行：

```sh
docker build -t demo-docker .
```

- `-t demo-docker`：给镜像起名 `demo-docker`。
- `.`：构建上下文是当前目录（Dockerfile 必须在这个目录）。

**步骤 3：查看镜像**

```sh
docker images
```

能看到 `demo-docker` 镜像，约 119MB。

**步骤 4：运行容器**

```sh
docker run -d -p 9090:8080 demo-docker
```

- `-d`：后台运行。
- `-p 9090:8080`：端口映射，宿主机 9090 → 容器 8080。
- `demo-docker`：镜像名。

**步骤 5：验证**

```sh
curl http://localhost:9090/demo/
```

返回 `Hello,From Docker!` 说明容器里的应用正常启动了。

### 6.2 方式二：用 Maven 插件构建

如果 pom 里打开了 `executions` 绑定到 `package` 阶段：

```sh
mvn clean package -DskipTests
```

这一条命令会自动：打 jar → 构建 Docker 镜像。然后：

```sh
docker run -d -p 9090:8080 demo-docker:1.0.0-SNAPSHOT
```

注意用 Maven 插件时镜像 tag 是版本号 `1.0.0-SNAPSHOT`（因为 pom 配了 `<tag>${project.version}</tag>`）。

### 6.3 常用容器管理命令

| 命令 | 作用 |
| --- | --- |
| `docker ps` | 查看运行中的容器 |
| `docker ps -a` | 查看所有容器（含已停止） |
| `docker logs <容器ID>` | 查看容器日志 |
| `docker stop <容器ID>` | 停止容器 |
| `docker rm <容器ID>` | 删除容器 |
| `docker rmi demo-docker` | 删除镜像 |

---

## 七、动手练习

1. **改端口映射**：把 `docker run -p 9090:8080` 改成 `-p 8081:8080`，访问 `localhost:8081/demo/` 验证。
2. **进容器看**：`docker exec -it <容器ID> sh`（Alpine 用 sh 不用 bash），进去看看 `/app.jar` 在不在，`java -version` 是不是 8。
3. **改 Dockerfile 用 COPY**：把 `ADD ${JAR_FILE} app.jar` 改成 `COPY ${JAR_FILE} app.jar`，重新构建，验证效果一致。
4. **打开自动构建**：把 pom 里注释的 `executions` 取消注释，执行 `mvn package`，观察是否自动生成了镜像。
5. **换基础镜像**：把 `FROM openjdk:8-jdk-alpine` 换成 `FROM openjdk:8-jdk-slim`，重新构建，对比镜像体积。
6. **加健康检查**：在 Dockerfile 加 `HEALTHCHECK CMD curl -f http://localhost:8080/demo/ || exit 1`，运行后用 `docker ps` 看健康状态。

---

## 八、本模块知识点总结（结合实际开发详解）

容器化是现代后端部署的标配，下面把核心知识点放到真实开发场景里讲透。

### 8.1 为什么后端要容器化？jar 包不够吗？

**`java -jar` 裸跑的局限：**

- 环境依赖：JDK 版本、系统库（glibc 版本、字体库、时区）都得在部署机器上预装，"环境不一致"是最大痛点。
- 进程管理：崩了不会自动重启，开机不会自启，要自己写 systemd/supervisor 脚本。
- 资源隔离：多个应用跑一台机器，端口、内存、CPU 互相争抢，没法限制。
- 扩容麻烦：扩 10 台机器要重复装环境 10 次。

**Docker 容器化的价值：**

- **环境一致**：镜像里打包了 OS 库 + JDK + 应用，开发/测试/生产完全一致，消除"在我电脑上能跑"。
- **秒级启动**：容器本质是进程，启动比虚拟机快几个数量级。
- **资源隔离**：通过 cgroups 限制每个容器的 CPU/内存，互不干扰。
- **不可变部署**：镜像一旦构建就不变，回滚只需切回旧镜像，像 git 一样可追溯。
- **编排友好**：K8s/Swarm 等编排工具基于容器实现自动扩缩容、滚动发布、自愈。

**实际开发的选择：**

| 场景 | 推荐方式 |
| --- | --- |
| 单机小项目、演示 | `java -jar` 裸跑或 Docker 单容器 |
| 传统企业部署 | Docker + systemd/supervisor |
| 微服务、云原生 | Docker + K8s 编排 |
| Serverless | 容器化（Fargate/Cloud Run）或函数计算 |

> 💡 前端类比：前端部署经历 "FTP 传静态文件 → nginx 托管 → Vercel/Netlify → Edge Functions" 的演进，后端也经历 "裸 jar → Docker → K8s → Serverless 容器"，思路一致：越来越不用管服务器。

### 8.2 Dockerfile 指令全景与最佳实践

本模块用到的指令和常用指令全集：

| 指令 | 作用 | 本模块是否用到 |
| --- | --- | --- |
| `FROM` | 基础镜像（必须，第一条） | ✅ |
| `MAINTAINER` / `LABEL` | 维护者信息 / 通用元数据 | ✅（MAINTAINER 已废弃） |
| `RUN` | 构建时执行命令（装包等） | ❌ |
| `COPY` / `ADD` | 复制文件到镜像 | ✅ ADD |
| `WORKDIR` | 设置工作目录 | ❌ |
| `ENV` | 设置运行期环境变量 | ❌ |
| `ARG` | 设置构建期变量 | ✅ |
| `EXPOSE` | 声明端口 | ✅ |
| `VOLUME` | 声明挂载点 | ✅ |
| `CMD` | 默认启动命令（可被覆盖） | ❌ |
| `ENTRYPOINT` | 固定启动命令 | ✅ |
| `HEALTHCHECK` | 健康检查 | ❌ |

**实际开发的 Dockerfile 最佳实践：**

1. **用小基础镜像**：`alpine` 版本体积小、攻击面小。但注意 Alpine 用 musl libc，某些依赖（如需要 glibc 的库）会报错，这时换 `slim` 版。
2. **多阶段构建（Multi-stage build）**：构建期需要 Maven/JDK 来打 jar，运行期只需要 JRE。用多阶段构建，最终镜像只含运行所需内容，体积从几百 MB 降到一百多 MB：

   ```dockerfile
   # 第一阶段：构建
   FROM maven:3.6-jdk-8 AS builder
   WORKDIR /app
   COPY pom.xml .
   RUN mvn dependency:go-offline        # 先下依赖，利用缓存层
   COPY src ./src
   RUN mvn clean package -DskipTests

   # 第二阶段：运行
   FROM openjdk:8-jre-alpine
   COPY --from=builder /app/target/demo-docker.jar /app.jar
   ENTRYPOINT ["java","-jar","/app.jar"]
   ```

3. **利用层缓存**：Dockerfile 每条指令是一层，从上到下执行，某层没变就用缓存。把变化频率低的放前面（如装依赖），变化高的放后面（如 COPY 源码），加速重复构建。
4. **`.dockerignore`**：像 `.gitignore`，排除 `target/`、`.git/`、`node_modules/` 等，避免把垃圾文件打进构建上下文。
5. **非 root 用户运行**：生产镜像用 `USER` 切到非 root 用户，提升安全。
6. **一个容器一个进程**：不要在一个容器里塞 MySQL+Redis+App，每个服务一个容器，用 docker-compose 编排。

**常见坑：**

- `ADD` 从 URL 下载或自动解压的"智能"行为容易出意外，**纯复制优先用 `COPY`**。
- `ENTRYPOINT` 用 shell 形式（`ENTRYPOINT java -jar app.jar`）会经过 shell，信号传递有问题，进程收不到 SIGTERM 导致容器 stop 超时。**用 exec 形式（JSON 数组）**。
- 忘了 `EXPOSE` 虽然不影响 `-p` 映射，但影响 `-P` 随机映射和文档可读性。

### 8.3 端口映射：容器内外是两个世界

本模块 `docker run -p 9090:8080` 把容器内 8080 映射到宿主机 9090。这是新手最容易迷糊的点：

- **容器内**：应用监听 8080（`application.yml` 配的）。容器有自己的网络栈，8080 是容器视角的端口。
- **宿主机**：要访问容器，必须把容器端口映射到宿主机端口。`-p 宿主端口:容器端口`。
- `EXPOSE 8080` 只是声明，不映射。真正映射靠 `-p`。

**实际开发的网络模式：**

| 模式 | 说明 | 适用 |
| --- | --- | --- |
| bridge（默认） | 容器通过虚拟网桥和宿主机通信，需 `-p` 映射 | 单机多容器 |
| host | 容器直接用宿主机网络，无隔离 | 简化网络，但失去隔离 |
| none | 无网络 | 离线计算 |
| container:xxx | 和另一个容器共用网络栈 | sidecar 模式 |

**生产环境一般不用 `-p` 直接映射**，而是：
- 多容器用 docker-compose 编排，容器间用容器名通信（同一网络）。
- 对外暴露用反向代理（nginx/Traefik）统一接管 80/443，再转发到内部容器。

> 💡 前端类比：像 Vite dev server 监听 5173，但你在浏览器访问的是 localhost:5173，因为 dev server 跑在你本机。容器相当于"另一台机器"，它的 8080 在你本机访问不到，必须 `-p` 挖个通道。

### 8.4 镜像构建的两种方式：Dockerfile vs Buildpacks

本模块用 Dockerfile 手写构建脚本，这是最传统也最灵活的方式。但现代 Spring Boot 生态有更省事的方案：

**方式一：Dockerfile（本模块方式）**
- 手写 Dockerfile，用 `docker build` 或 Maven 插件构建。
- 优点：完全可控、灵活。
- 缺点：要维护 Dockerfile，容易写出不规范镜像（体积大、层多、不安全）。

**方式二：Spring Boot Buildpacks（推荐新项目）**
- Spring Boot 2.3+ 内置，无需 Dockerfile：

  ```sh
  mvn spring-boot:build-image
  ```

- 自动用 Cloud Native Buildpacks 生成符合 OCI 标准的镜像，自动分包、自动选基础镜像、自动加健康检查。
- 优点：零 Dockerfile，开箱即用，镜像规范。
- 缺点：不够灵活，定制困难。

**方式三：Jib（Google 出品）**
- Maven/Gradle 插件，无需 Docker 守护进程就能构建镜像，分层优化好。
- 适合 CI/CD 环境没装 Docker 的场景。

**实际开发选择：**
- 学习、需要深度定制 → Dockerfile。
- 快速上手、标准化 → Buildpacks（`spring-boot:build-image`）。
- CI/CD 优化、无 Docker 环境 → Jib。

### 8.5 docker-compose：多容器编排

本模块只有一个容器，但真实项目往往需要 App + MySQL + Redis + Nginx 多个容器一起跑。手动 `docker run` 一堆太麻烦，用 `docker-compose.yml` 声明式编排：

```yaml
version: '3'
services:
  app:
    build: .
    ports:
      - "9090:8080"
    depends_on:
      - mysql
      - redis
    environment:
      SPRING_PROFILES_ACTIVE: prod
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: 123456
    volumes:
      - mysql-data:/var/lib/mysql
  redis:
    image: redis:6-alpine
volumes:
  mysql-data:
```

一条 `docker-compose up -d` 启动全部，容器间用服务名（`mysql`、`redis`）互相访问。

> 💡 前端类比：docker-compose 像 monorepo 的 `turbo.json` 或 `nx.json`，用一个配置文件管理多个子项目的关系和启动顺序。

### 8.6 Spring Boot 容器化的特殊考量

**1. 配置外部化**
容器化后，配置不能打进镜像（镜像要不可变、多环境复用）。用环境变量覆盖：

```sh
docker run -d -p 9090:8080 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e SPRING_DATASOURCE_PASSWORD=secret \
  demo-docker
```

Spring Boot 的"环境变量覆盖配置文件"机制在这里完美适配。

**2. 日志输出**
容器里别写日志文件，**输出到 stdout/stderr**，让 `docker logs` 能看到，再由日志收集器（ELK/Loki）统一采集。Spring Boot 默认就是控制台输出，天然适配。

**3. 优雅停机**
容器 stop 时发 SIGTERM，Spring Boot 要能优雅关闭（处理完已有请求再退出）。配置：

```yaml
server:
  shutdown: graceful          # 2.3+ 支持，等待处理完请求
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

并确保 ENTRYPOINT 用 exec 形式能收到信号。

**4. 健康检查**
配合 Actuator 的 `/actuator/health`，在 Dockerfile 加 `HEALTHCHECK`，K8s 据此判断容器是否健康、是否需要重启。

**常见坑：**
- 时区问题：容器默认 UTC，日志时间和北京时间差 8 小时。设 `ENV TZ=Asia/Shanghai` 并装 tzdata。
- `openjdk:8-jdk-alpine` 的 musl libc 导致某些 native 库报错，换 `slim` 版解决。
- 容器以 root 跑有安全风险，生产应 `USER nobody` 或建专用用户。
- 镜像 tag 用 `latest` 不可追溯，生产必须用具体版本号或 git commit hash。

---

> 📌 **学习建议**：作为前端转后端的工程师，Docker 是你必须跨过的一道坎——它是后端部署的"通用语言"，后续的 K8s、CI/CD、微服务编排全都建立在容器化之上。建议先把本模块的 Dockerfile 逐行吃透，再用 docker-compose 把一个 Spring Boot + MySQL + Redis 的组合跑起来，体会"声明式编排"的威力。心智模型上要建立：**镜像 = 类，容器 = 实例**，一个镜像可以跑无数个容器实例，这正是扩容的基础。Docker 学好了，后面接触 K8s 会顺理成章，因为 K8s 本质就是在管理一堆容器。
