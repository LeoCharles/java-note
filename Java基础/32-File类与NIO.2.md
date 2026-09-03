# File 类与 NIO.2

文件操作是 Java 开发中绕不开的一环：日志写入、配置读取、文件上传、批量处理、数据备份……几乎所有后台系统都要和文件打交道。Java 提供了两套文件 API：老牌的 `java.io.File`（自 JDK 1.0 就有）和 Java 7 引入的 NIO.2（`java.nio.file.Path` + `Files`）。前者简单但功能薄弱、异常处理粗糙；后者设计现代、功能强大、错误信息明确。实际开发中两者都会遇到，本篇带你由浅入深掌握它们。

> 💡 本篇是后续 IO 流（[33-字节流与字符流](33-字节流与字符流.md)）的基础——流的读写离不开文件路径的定位与文件的创建、删除、遍历。

---

## 一、File 类概述

`java.io.File` 是文件和目录路径的**抽象表示**。注意三点：

1. **File 对象不等于真实文件**：`new File("a.txt")` 只是创建了一个内存对象，磁盘上不一定真有这个文件。
2. **File 只管路径元信息**：它能创建、删除、遍历文件，但**不能读写文件内容**（读写内容要用 IO 流）。
3. **跨平台路径问题**：Windows 用 `\`，Linux/Mac 用 `/`，硬编码分隔符会导致跨平台出错。

```java
import java.io.File;

// File 对象只是路径抽象，磁盘上没有这个文件
File f = new File("a.txt");
System.out.println(f.exists());  // false，磁盘上并不存在
```

---

## 二、静态成员与构造方法

### 2.1 路径分隔符（跨平台必备）

| 静态成员 | 含义 | Windows | Linux/Mac |
| :--- | :--- | :---: | :---: |
| `File.separator` | 路径分隔符（分隔目录层级） | `\` | `/` |
| `File.pathSeparator` | 多路径分隔符（分隔多个路径，如 classpath） | `;` | `:` |

```java
// ❌ 错误：硬编码分隔符，换平台就崩
File bad = new File("tmp\\log\\app.log");  // Linux 上路径错乱

// ✅ 正确：用 separator 拼接，跨平台通用
File good = new File("tmp" + File.separator + "log" + File.separator + "app.log");
```

> 📌 **规范**：实际开发中更推荐直接用 `/`——Java 内部会自动把 `/` 转成当前平台的分隔符。所以 `"tmp/log/app.log"` 在所有平台都能工作。`File.separator` 多用于拼接动态路径片段时。

### 2.2 三种构造方法

```java
// 1. 从路径字符串构造（最常用）
File f1 = new File("D:/data/test.txt");

// 2. 从 parent + child 构造（拼接路径更清晰）
File f2 = new File("D:/data", "test.txt");

// 3. 从 File parent + child 构造（parent 已是 File 对象时）
File parent = new File("D:/data");
File f3 = new File(parent, "test.txt");

// 三者指向同一个文件
System.out.println(f1.equals(f2));  // true
```

> 💡 还有一个 `File(URI uri)` 构造方法，用 `file:///D:/data/test.txt` 形式，较少用。

---

## 三、File 常用方法

### 3.1 获取方法

```java
File f = new File("D:/data/test.txt");
f.createNewFile();  // 先创建出来，便于演示

f.getAbsolutePath();   // D:\data\test.txt，绝对路径
f.getPath();           // D:\data\test.txt，构造时传入的路径字符串
f.getName();           // test.txt，文件名
f.getParent();         // D:\data，父路径（字符串）
f.getParentFile();     // D:\data，父路径（File 对象）
f.length();            // 文件字节数（目录返回 0）
f.lastModified();      // 最后修改时间（long 毫秒值）
```

> ⚠️ `length()` 只对文件有效，对目录返回值是不确定的（通常为 0）。要统计目录大小必须递归累加文件长度（见实战案例）。

### 3.2 判断方法

```java
f.exists();        // 是否存在
f.isFile();        // 是否是文件
f.isDirectory();   // 是否是目录
f.isHidden();      // 是否隐藏
f.canRead();       // 是否可读
f.canWrite();      // 是否可写
f.isAbsolute();    // 是否是绝对路径
```

> ⚠️ 调用 `isFile()` / `isDirectory()` 前最好先 `exists()`，因为文件不存在时这两个方法都返回 `false`，容易掩盖问题。

### 3.3 创建与删除方法

```java
// 创建文件（文件不存在才创建，返回 true；已存在返回 false）
File f = new File("a.txt");
boolean ok = f.createNewFile();  // ✅ 抛 IOException，必须处理

// 创建目录
File dir1 = new File("a");
dir1.mkdir();     // ✅ 只能创建一级目录，父目录不存在则失败

File dir2 = new File("a/b/c");
dir2.mkdirs();   // ✅ 创建多级目录，父目录不存在会一并创建（推荐）

// 删除
f.delete();      // 删除文件或空目录。目录非空则删除失败，返回 false
// f.deleteOnExit();  // JVM 退出时删除，常用于临时文件清理
```

> ⚠️ `mkdir()` 和 `mkdirs()` 不抛异常，只返回 boolean，失败时容易静默出错。开发中要检查返回值。
>
> ⚠️ `delete()` 删除非空目录会**直接失败**（不报错，只返回 false），必须递归删除（见实战案例）。

### 3.4 遍历方法

```java
File dir = new File("D:/data");

// 1. list()：返回 String[] 文件名（不含路径）
String[] names = dir.list();

// 2. listFiles()：返回 File[]（推荐，含完整路径）
File[] files = dir.listFiles();

// 3. listFiles(FileFilter)：过滤
File[] javaFiles = dir.listFiles(file -> file.getName().endsWith(".java"));

// 4. list(FilenameFilter)：按文件名过滤
String[] txtNames = dir.list((d, name) -> name.endsWith(".txt"));
```

> ⚠️ 如果 `dir` 不是目录或不存在，`list()` / `listFiles()` 返回 `null`（不是空数组！）。使用前必须判空，否则 NPE。

---

## 四、递归遍历多级目录

文件搜索、目录大小统计、批量删除等场景都要递归。核心思路：**遇到目录就进，遇到文件就处理**。

```java
import java.io.File;

// 递归打印目录树
public static void printTree(File dir, int level) {
    if (dir == null || !dir.exists()) return;
    // 缩进
    System.out.println("  ".repeat(level) + dir.getName());
    if (dir.isDirectory()) {
        File[] children = dir.listFiles();
        if (children != null) {  // ✅ 必须判空
            for (File child : children) {
                printTree(child, level + 1);
            }
        }
    }
}
```

> 💡 `"  ".repeat(level)` 是 Java 11+ 的 `String.repeat`。Java 8 可用循环拼接空格，或用 `String.format`。

### 4.1 文件搜索：找所有 .java 文件

```java
// 递归搜索指定后缀的文件
public static void searchByExt(File dir, String ext, java.util.List<File> result) {
    if (dir == null || !dir.isDirectory()) return;
    File[] files = dir.listFiles();
    if (files == null) return;
    for (File f : files) {
        if (f.isFile() && f.getName().endsWith(ext)) {
            result.add(f);
        } else if (f.isDirectory()) {
            searchByExt(f, ext, result);  // 递归
        }
    }
}

// 调用
java.util.List<File> list = new java.util.ArrayList<>();
searchByExt(new File("D:/project"), ".java", list);
list.forEach(f -> System.out.println(f.getAbsolutePath()));
```

---

## 五、FileFilter 与 FilenameFilter

这两个是 `java.io` 包下的**函数式接口**（Java 8 起），用于文件过滤。

```java
// FileFilter：接收 File 参数，可判断文件名、是否目录、大小等
@FunctionalInterface
public interface FileFilter {
    boolean accept(File pathname);
}

// FilenameFilter：接收 dir + name，只能按文件名过滤
@FunctionalInterface
public interface FilenameFilter {
    boolean accept(File dir, String name);
}
```

```java
File dir = new File("D:/data");

// FileFilter：只保留 .log 文件
File[] logs = dir.listFiles(file ->
    file.isFile() && file.getName().endsWith(".log"));

// FilenameFilter：只保留 .txt 文件
String[] txts = dir.list((d, name) -> name.endsWith(".txt"));
```

> 💡 **选择**：要判断文件属性（是否目录、大小、修改时间）用 `FileFilter`；只按文件名过滤用 `FilenameFilter` 更轻量。

---

## 六、NIO.2：Path 接口（Java 7+）⭐⭐

`File` 类设计缺陷明显：方法返回 boolean 而非抛异常（失败原因不明）、不支持符号链接、跨文件系统操作薄弱。Java 7 引入 NIO.2（`java.nio.file` 包）全面替代。

### 6.1 Path 接口

`Path` 替代 `File`，表示路径（**仍是抽象，不要求真实存在**）。

```java
import java.nio.file.Path;
import java.nio.file.Paths;

// Paths.get() 创建 Path（推荐）
Path p1 = Paths.get("D:/data/test.txt");
Path p2 = Paths.get("D:", "data", "test.txt");  // 可变参数拼接

// Java 11+ 可直接用 Path.of()
// Path p3 = Path.of("D:/data/test.txt");

p1.toString();        // D:/data/test.txt
p1.getFileName();     // test.txt
p1.getParent();       // D:/data
p1.getRoot();         // D:/
p1.getNameCount();    // 路径层级数
p1.toAbsolutePath();  // 绝对路径
```

### 6.2 路径操作：resolve / normalize / relativize

```java
// resolve：拼接子路径（类似 new File(parent, child)）
Path base = Paths.get("D:/data");
Path full = base.resolve("log/app.log");  // D:/data/log/app.log

// normalize：消除 . 和 ..
Path messy = Paths.get("D:/data/../data/./test.txt");
Path clean = messy.normalize();  // D:/data/test.txt

// relativize：求相对路径（从 A 到 B 的路径）
Path a = Paths.get("D:/data/log");
Path b = Paths.get("D:/data/backup/db.sql");
Path rel = a.relativize(b);  // ../backup/db.sql
```

> ⚠️ `relativize` 要求两个路径都是绝对路径或都是相对路径，否则抛 `IllegalArgumentException`。

---

## 七、NIO.2：Files 工具类 ⭐⭐

`Files` 是工具类，提供大量静态方法操作文件/目录，**方法失败会抛具体异常**（NoSuchFileException、AccessDeniedException 等），比 `File` 的 boolean 返回值清晰得多。

### 7.1 创建与删除

```java
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

Path p = Paths.get("D:/data/test.txt");
Path dir = Paths.get("D:/data/sub");

// 创建文件（已存在抛 FileAlreadyExistsException）
Files.createFile(p);

// 创建目录（只创建一级，父目录不存在抛异常）
Files.createDirectory(dir);

// 创建多级目录（推荐）
Files.createDirectories(Paths.get("D:/data/a/b/c"));

// 删除（文件不存在抛 NoSuchFileException）
Files.delete(p);
Files.deleteIfExists(p);  // ✅ 不存在不报错，更安全
```

### 7.2 复制与移动

```java
Path src = Paths.get("D:/data/a.txt");
Path dst = Paths.get("D:/data/b.txt");

// 复制文件
Files.copy(src, dst);  // 目标已存在抛 FileAlreadyExistsException
Files.copy(src, dst, StandardCopyOption.REPLACE_EXISTING);  // ✅ 覆盖

// 移动/重命名
Files.move(src, dst, StandardCopyOption.REPLACE_EXISTING);

// 从输入流复制到文件（文件上传常用）
// Files.copy(InputStream in, Path target);
// 从文件复制到输出流（文件下载常用）
// Files.copy(Path source, OutputStream out);
```

### 7.3 读写与元信息

```java
// 判断
Files.exists(p);
Files.isRegularFile(p);
Files.isDirectory(p);
Files.isHidden(p);
Files.size(p);           // 字节数（long）

// 一次性读写小文件（文件大会占内存，慎用）
byte[] bytes = Files.readAllBytes(p);          // 读全部字节
List<String> lines = Files.readAllLines(p);    // 读全部行（UTF-8）
Files.write(p, bytes);                          // 写字节
Files.write(p, lines, StandardOpenOption.APPEND);  // 追加写行
```

> ⚠️ `readAllBytes()` / `readAllLines()` 会把整个文件读进内存。处理大文件（几百 MB 以上）会 OOM，要用流或 `Files.lines()`。

---

## 八、Files.walk 与 walkFileTree 递归遍历

NIO.2 提供了优雅的递归遍历方案，**比手写递归简洁得多**。

### 8.1 Files.walk（返回 Stream）

```java
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.stream.Stream;

// 遍历目录树，返回 Stream<Path>
try (Stream<Path> stream = Files.walk(Paths.get("D:/project"))) {
    stream.filter(Files::isRegularFile)
          .filter(p -> p.toString().endsWith(".java"))
          .forEach(System.out::println);
}  // ✅ try-with-resources 自动关闭 Stream（必须！）
```

> ⚠️ `Files.walk` 返回的 `Stream<Path>` 持有文件系统资源，**必须用 try-with-resources 关闭**，否则可能因文件句柄泄漏导致目录无法删除。

### 8.2 Files.walkFileTree（访问者模式）

```java
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;

Files.walkFileTree(Paths.get("D:/project"), new SimpleFileVisitor<Path>() {
    @Override
    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
        if (file.toString().endsWith(".java")) {
            System.out.println("找到: " + file);
        }
        return FileVisitResult.CONTINUE;
    }

    @Override
    public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
        System.out.println("进入目录: " + dir);
        return FileVisitResult.CONTINUE;
    }
});
```

`walkFileTree` 适合需要区分「进入目录前」「访问文件后」「访问失败」等场景，比 `walk` 更精细。

### 8.3 与 File 的对比与互转

```java
// File → Path
File file = new File("a.txt");
Path path = file.toPath();

// Path → File
Path p = Paths.get("a.txt");
File f = p.toFile();
```

| 对比项 | File（老） | Path + Files（新） |
| :--- | :--- | :--- |
| 异常处理 | 返回 boolean，失败原因不明 | 抛具体异常（NoSuchFileException 等） |
| 符号链接 | 不支持 | 支持（LinkOption） |
| 文件属性 | 仅基础属性 | 支持 BasicFileAttributes、POSIX、ACL |
| 批量操作 | 需手写递归 | walk / walkFileTree 内置 |
| 复制移动 | 无（要手写流复制） | Files.copy / move 一行搞定 |
| 推荐度 | 兼容老代码 | **新项目首选** |

> 📌 **规范**：新项目优先使用 `Path` + `Files`。维护老代码遇到 `File` 时，可在关键操作处用 `toPath()` 转换后用 `Files` 处理。

---

## 九、文件操作异常处理

NIO.2 的异常体系清晰，常见异常：

| 异常 | 触发场景 |
| :--- | :--- |
| `NoSuchFileException` | 文件/目录不存在 |
| `FileAlreadyExistsException` | 创建时已存在 |
| `AccessDeniedException` | 无权限（只读目录写文件） |
| `DirectoryNotEmptyException` | 删除非空目录 |
| `FileSystemException` | 上述异常的父类 |
| `IOException` | 所有 IO 异常的父类 |

```java
import java.nio.file.*;
import java.nio.file.AccessDeniedException;

Path p = Paths.get("D:/system/secret.txt");
try {
    byte[] data = Files.readAllBytes(p);
} catch (NoSuchFileException e) {
    System.err.println("文件不存在: " + e.getMessage());
} catch (AccessDeniedException e) {
    System.err.println("无权限访问: " + e.getMessage());
} catch (IOException e) {
    // 兜底：其他 IO 异常
    e.printStackTrace();
}
```

> 💡 这些具体异常都是 `FileSystemException` 的子类，而 `FileSystemException` 继承 `IOException`。所以精确捕获要从子到父，最后用 `IOException` 兜底。

---

## ⚠️ 重点

### 重点 1：`list()` / `listFiles()` 可能返回 null ⭐

```java
File dir = new File("not-exist");
File[] files = dir.listFiles();
// for (File f : files) { ... }  // ❌ files 为 null，NPE！

if (files != null) {  // ✅ 必须判空
    for (File f : files) { ... }
}
```

> ⚠️ 文件不存在、不是目录、权限不足等情况都会返回 `null`。这是 File API 最隐蔽的 NPE 来源。

### 重点 2：`delete()` 删不掉非空目录 ⭐

```java
File dir = new File("D:/data/old");
dir.delete();  // ❌ 目录非空，返回 false，什么都没删掉

// ✅ 必须递归删除：先删子文件，再删目录本身
public static void deleteRecursively(File f) {
    if (f.isDirectory()) {
        File[] children = f.listFiles();
        if (children != null) {
            for (File child : children) {
                deleteRecursively(child);
            }
        }
    }
    f.delete();
}
```

> 💡 NIO.2 提供了更优雅的方案：`Files.walkFileTree` + `FileVisitor` 递归删除（见实战案例）。

### 重点 3：`length()` 不能统计目录大小 ⭐

```java
File dir = new File("D:/data");
System.out.println(dir.length());  // 0 或不确定值，不是目录总大小！

// ✅ 必须递归累加
public static long sizeOf(File f) {
    if (f.isFile()) return f.length();
    long total = 0;
    File[] children = f.listFiles();
    if (children != null) {
        for (File c : children) {
            total += sizeOf(c);
        }
    }
    return total;
}
```

### 重点 4：`Files.walk` 的 Stream 必须关闭 ⭐⭐

```java
// ❌ 错误：Stream 未关闭，文件句柄泄漏
Stream<Path> s = Files.walk(Paths.get("D:/data"));
s.forEach(System.out::println);
// 此后可能无法删除 D:/data 目录！

// ✅ 正确：try-with-resources
try (Stream<Path> s = Files.walk(Paths.get("D:/data"))) {
    s.forEach(System.out::println);
}
```

> ⚠️ 这是 NIO.2 最容易踩的坑。`walk` 打开的目录流若不关闭，Windows 上会导致目录被占用无法删除，Linux 上会泄漏文件描述符。

### 重点 5：路径硬编码是跨平台大忌 ⭐

```java
// ❌ Windows 风格硬编码
File f1 = new File("D:\\data\\test.txt");  // Linux 上 D: 被当成目录名

// ✅ 用 / 或 File.separator
File f2 = new File("D:/data/test.txt");     // ✅ Java 自动转换
File f3 = new File("data" + File.separator + "test.txt");  // ✅
```

### 重点 6：NIO.2 异常比 File 的 boolean 信息量大 ⭐⭐

```java
// File 方式：失败原因不明
new File("a.txt").createNewFile();  // 返回 false，是已存在？还是没权限？还是路径错？

// Files 方式：异常类型明确
Files.createFile(Paths.get("a.txt"));
// FileAlreadyExistsException → 已存在
// AccessDeniedException → 无权限
// NoSuchFileException → 父目录不存在
```

> 📌 **规范**：新代码用 `Files`，异常信息直接进日志，排查问题事半功倍。

---

## 💻 实战案例

### 案例 1：递归删除目录（清理临时文件）⭐⭐

电商系统定时清理过期的上传临时目录：

```java
import java.io.File;

public class DirCleaner {
    // File 方式：递归删除
    public static void deleteDir(File f) {
        if (f.isDirectory()) {
            File[] children = f.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteDir(child);
                }
            }
        }
        if (!f.delete()) {
            System.err.println("删除失败: " + f.getAbsolutePath());
        }
    }

    // NIO.2 方式：walkFileTree 更优雅
    public static void deleteDirNio(java.nio.file.Path path) throws java.io.IOException {
        java.nio.file.Files.walkFileTree(path, new java.nio.file.SimpleFileVisitor<java.nio.file.Path>() {
            @Override
            public java.nio.file.FileVisitResult visitFile(java.nio.file.Path file, java.nio.file.attribute.BasicFileAttributes attrs) throws java.io.IOException {
                java.nio.file.Files.delete(file);
                return java.nio.file.FileVisitResult.CONTINUE;
            }
            @Override
            public java.nio.file.FileVisitResult postVisitDirectory(java.nio.file.Path dir, java.io.IOException exc) throws java.io.IOException {
                java.nio.file.Files.delete(dir);  // 子文件删完后再删目录
                return java.nio.file.FileVisitResult.CONTINUE;
            }
        });
    }
}
```

> 💡 `walkFileTree` 的 `postVisitDirectory` 在子项全部访问完后触发，正好用于「先删内容再删目录」。

### 案例 2：文件搜索——找所有 .java 文件 ⭐

代码审计工具扫描项目源码：

```java
import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class JavaFileScanner {
    // 递归方式
    public static List<File> findJavaFiles(File dir) {
        List<File> result = new ArrayList<>();
        findJavaFiles(dir, result);
        return result;
    }

    private static void findJavaFiles(File dir, List<File> result) {
        if (dir == null || !dir.isDirectory()) return;
        File[] files = dir.listFiles();
        if (files == null) return;
        for (File f : files) {
            if (f.isDirectory()) {
                findJavaFiles(f, result);
            } else if (f.getName().endsWith(".java")) {
                result.add(f);
            }
        }
    }

    // NIO.2 方式：一行流式处理
    public static List<String> findJavaFilesNio(String root) throws java.io.IOException {
        try (java.util.stream.Stream<java.nio.file.Path> stream = java.nio.file.Files.walk(java.nio.file.Paths.get(root))) {
            return stream.filter(java.nio.file.Files::isRegularFile)
                         .filter(p -> p.toString().endsWith(".java"))
                         .map(java.nio.file.Path::toString)
                         .collect(java.util.stream.Collectors.toList());
        }
    }
}
```

### 案例 3：批量重命名（日志归档）⭐

运维场景：把每天的日志 `app.log` 重命名为 `app-20260903.log` 归档：

```java
import java.io.File;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

public class LogArchiver {
    public static void archive(File logFile) {
        if (!logFile.exists() || !logFile.isFile()) return;
        String name = logFile.getName();  // app.log
        String base = name.substring(0, name.lastIndexOf('.'));  // app
        String ext = name.substring(name.lastIndexOf('.'));       // .log
        String date = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        File renamed = new File(logFile.getParentFile(), base + "-" + date + ext);
        if (logFile.renameTo(renamed)) {  // ✅ renameTo 返回 boolean
            System.out.println("归档成功: " + renamed.getName());
        } else {
            System.err.println("归档失败，目标可能已存在或跨盘");
        }
    }
}
```

> ⚠️ `File.renameTo` 在跨文件系统（跨盘符）时会失败。跨盘移动要用 `Files.move`。

### 案例 4：统计目录大小（磁盘占用分析）⭐⭐

后台系统展示用户上传目录占用：

```java
import java.io.File;
import java.nio.file.*;
import java.util.stream.Stream;

public class DirSizeCalculator {
    // File 递归方式
    public static long sizeOf(File f) {
        if (f.isFile()) return f.length();
        long total = 0;
        File[] children = f.listFiles();
        if (children != null) {
            for (File c : children) total += sizeOf(c);
        }
        return total;
    }

    // NIO.2 流式方式
    public static long sizeOfNio(Path dir) throws java.io.IOException {
        try (Stream<Path> stream = Files.walk(dir)) {
            return stream.filter(Files::isRegularFile)
                         .mapToLong(p -> {
                             try { return Files.size(p); }
                             catch (java.io.IOException e) { return 0; }
                         })
                         .sum();
        }
    }

    public static void main(String[] args) throws java.io.IOException {
        long bytes = sizeOfNio(Paths.get("D:/uploads"));
        System.out.printf("占用: %.2f MB%n", bytes / 1024.0 / 1024.0);
    }
}
```

### 案例 5：用 Files.copy 备份文件 ⭐

数据库导出后自动备份：

```java
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class BackupUtil {
    public static void backup(Path source) throws java.io.IOException {
        String ts = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        Path backupDir = Paths.get("D:/backup");
        Files.createDirectories(backupDir);  // 确保备份目录存在

        String fileName = source.getFileName().toString();
        Path target = backupDir.resolve(fileName + "." + ts + ".bak");
        Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
        System.out.println("备份完成: " + target);
    }

    public static void main(String[] args) throws java.io.IOException {
        backup(Paths.get("D:/data/db.sql"));
    }
}
```

### 案例 6：用 Files.walk 统计项目代码行数 ⭐⭐

技术经理评估代码规模：

```java
import java.nio.file.*;
import java.util.stream.Stream;

public class CodeLineCounter {
    public static long countLines(Path projectDir) throws java.io.IOException {
        long total = 0;
        try (Stream<Path> stream = Files.walk(projectDir)) {
            // 先收集 .java 文件，避免流嵌套
            java.util.List<Path> javaFiles = stream
                .filter(Files::isRegularFile)
                .filter(p -> p.toString().endsWith(".java"))
                .collect(java.util.stream.Collectors.toList());

            for (Path f : javaFiles) {
                try (Stream<String> lines = Files.lines(f)) {  // 每个文件单独开流
                    total += lines.count();
                }
            }
        }
        return total;
    }

    public static void main(String[] args) throws java.io.IOException {
        long lines = countLines(Paths.get("D:/project"));
        System.out.println("Java 代码总行数: " + lines);
    }
}
```

> ⚠️ `Files.walk` 和 `Files.lines` 返回的 Stream 都要关闭。这里外层 walk 用 try-with-resources，内层 lines 也用 try-with-resources，嵌套关闭，安全。

### 案例 7：递归查找最大的 10 个文件（磁盘清理）⭐

```java
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

public class LargestFilesFinder {
    public static List<Path> findTopLargest(Path root, int topN) throws java.io.IOException {
        try (Stream<Path> stream = Files.walk(root)) {
            return stream.filter(Files::isRegularFile)
                .sorted(Comparator.comparingLong(p -> {
                    try { return -Files.size(p); }  // 负号实现降序
                    catch (java.io.IOException e) { return 0; }
                }).reversed())
                .limit(topN)
                .collect(Collectors.toList());
        }
    }

    public static void main(String[] args) throws java.io.IOException {
        List<Path> largest = findTopLargest(Paths.get("D:/data"), 10);
        for (Path p : largest) {
            System.out.printf("%-12d %s%n", Files.size(p), p);
        }
    }
}
```

---

## 🚀 新版本补充

### Java 8：Files.lines 返回 Stream<String>

`Files.lines(Path)` 按行读取文件为 `Stream<String>`，配合 Stream API 可声明式处理大文本：

```java
try (Stream<String> lines = Files.lines(Paths.get("access.log"))) {
    lines.filter(l -> l.contains("ERROR"))
         .limit(100)
         .forEach(System.out::println);
}
```

> 💡 `Files.lines` 是**惰性加载**，不会一次性读入内存，适合处理 GB 级日志。但 Stream 仍需关闭。

### Java 11：Path.of() 与 Files.readString / writeString

```java
// Java 11 新增 Path.of（替代 Paths.get）
Path p = Path.of("D:/data/test.txt");

// 一次性读写字符串（小文件利器）
String content = Files.readString(p);  // 默认 UTF-8
Files.writeString(p, "new content", StandardOpenOption.CREATE);
```

> ⚠️ Java 8 环境下不可用，但 `Paths.get` + `Files.readAllBytes` + `new String(bytes)` 可达到同样效果。

### Java 8：list 与 walk 的 Stream 化

`Files.list` / `Files.walk` / `Files.find` 都是 Java 8 引入的 Stream 风格 API，让文件遍历可以配合 `filter`、`map`、`collect` 函数式处理，远比 `File.listFiles` + 手写循环简洁。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| File 定位 | 文件/目录的抽象表示，**不能读写内容** |
| 跨平台分隔符 | 用 `/` 或 `File.separator`，别硬编码 `\` |
| 路径分隔符 | `separator` 分隔层级，`pathSeparator` 分隔多路径 |
| 创建文件 | `createNewFile()` 抛 IOException |
| 创建目录 | `mkdir()` 单级，`mkdirs()` 多级（推荐） |
| 删除 | `delete()` 删非空目录会失败，需递归 |
| 遍历 | `listFiles()` 可能返回 null，必须判空 |
| 过滤 | `FileFilter` / `FilenameFilter`（函数式接口） |
| Path（NIO.2） | 替代 File，`Paths.get()` 创建 |
| Files 工具类 | copy/move/delete/createDirectories 一行搞定 |
| 递归遍历 | `Files.walk` 返回 Stream，`walkFileTree` 访问者模式 |
| 异常体系 | NoSuchFileException / AccessDeniedException 等 |
| 互转 | `File.toPath()` / `Path.toFile()` |

---

## 学习建议

1. **两套 API 都要会**：老项目大量使用 `File`，新项目首选 `Path` + `Files`。先用 `File` 理解概念，再用 NIO.2 体验现代写法，对比着学效果最好。
2. **递归是基本功**：手写递归遍历、递归删除至少各敲一遍，理解「进目录前」和「出目录后」的时机。理解后再用 `Files.walk` / `walkFileTree`，你会惊叹于 NIO.2 的优雅。
3. **异常处理要精确**：NIO.2 的具体异常（NoSuchFileException、AccessDeniedException）是排查问题的金矿，不要图省事只 catch `IOException`，至少把 `NoSuchFileException` 和 `AccessDeniedException` 单独捕获，日志里能省下大量排查时间。
4. **Stream 必须关闭**：`Files.walk` / `Files.lines` / `Files.list` 返回的 Stream 持有系统资源，**一律用 try-with-resources 包裹**。这条规则没有例外，养成肌肉记忆。
5. **结合 IO 流一起学**：本篇只解决「文件在哪、怎么建、怎么删、怎么遍历」，文件内容的读写要靠 [33-字节流与字符流](33-字节流与字符流.md)。两篇对照着看，才能拼出完整的文件操作能力。
