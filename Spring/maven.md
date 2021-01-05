# Maven

## Maven 项目标准目录结构

+ `src/main/java`        项目源代码
+ `src/main/resources`   配置文件
+ `src/main/webapp`      页面资源(js、css、html、图片等)
+ `src/test/java`        测试代码
+ `src/test/resources`   测试配置文件
+ `target/`              编译生成的文件
+ `.pom.xml`             maven 项目配置文件

## Maven 常用命令

+ `mvn clean`   清除，删除 `/target` 目录内容
+ `mvn compile` 编译
+ `mvn test`    测试，会执行 `src/test/java` 下的单元测试类
+ `mvn package` 打包，java 工程打成 jar 包，web 工程打成 war 包
+ `mvn install` 安装, 将 jar 包或 war 包发布到本地仓库

## Maven 概念模型

### 对象模型(Project Object Model)

Maven 工程都有一个 `pom.xml` 文件，用来定义项目的坐标、项目依赖、项目信息、插件目标等。

### 依赖管理系统(Dependency Management System)

通过 Maven 的依赖管理系统对项目所依赖的 jar 包进行统一管理。

```xml
<dependencies>
  <dependency>
    <!-- 组织名称 -->
    <groupId>junit</groupId>
    <!-- 项目模块名称 -->
    <artifactId>junit</artifactId>
    <!-- 版本号 -->
    <version>4.9</version>
    <!-- 依赖范围 -->
    <scope>test</scope>
  </dependency>
</dependencies>
```

### 生命周期(Project Lifecycle)

使用 Maven 完成项目的构建，包括：清理(clean)、编译(compile)、测试(test)、打包(package)、安装(install)，Maven 将这些
过程规范为一个生命周期。
