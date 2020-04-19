# File 类

java.io.File 类主要用于文件(file)和目录(directory)的创建、查找和删除等操作。

静态成员变量：

+ `static String pathSeparator`：与系统有关的路径分隔符，为了方便，它被表示为一个字符串。
+ `static char pathSeparatorChar`：与系统有关的路径分隔符。
+ `static String separator`：与系统有关的默认名称分隔符，为了方便，它被表示为一个字符串。
+ `static char separatorChar`：与系统有关的默认名称分隔符。

构造方法：

+ `public File(String pathname)`：通过将给定的路径名字符串转换为抽象路径名来创建新的 File实例。
+ `public File(String parent, String child)`：从父路径名字符串和子路径名字符串创建新的 File实例。
+ `public File(File parent, String child)`：从父抽象路径名和子路径名字符串创建新的 File实例。

常用方法：

+ `String getAbsolutePath()`：返回此File的绝对路径名字符串。
+ `String getPath()`：将此File转换为路径名字符串。toString 方法调用的是 getPath
+ `String getName()`：返回由此File表示的文件或目录的名称。
+ `long length()`：返回由此File表示的文件的字节数。
+ `boolean exists()`：此File表示的文件或目录是否实际存在。
+ `boolean isDirectory()`：此File表示的是否为目录。
+ `boolean isFile()`：此File表示的是否为文件。
+ `boolean createNewFile()`：当且仅当具有该名称的文件尚不存在时，创建一个新的空文件。
+ `boolean delete()`：删除由此File表示的文件或目录。
+ `boolean mkdir()`：创建由此File表示的目录。
+ `boolean mkdirs()`：创建由此File表示的目录，包括任何必需但不存在的父目录。
+ `String[] list()`：返回一个String数组，表示该File目录中的所有子文件或目录。
+ `File[] listFiles()`：返回一个File数组，表示该File目录中的所有的子文件或目录。

注意事项:

1. 路径不区分大小写。
2. 反斜杠是转义字符，用两个反斜杠表示一个反斜杠。
3. 操作路径不要写死了，要用 File.separator

java.io.FileFilter 接口，用于抽象路径名(File对象)的过滤器。

该接口用于过滤文件(File对象)只有一个抽象方法：

`boolean accept(File pathname)`：测试pathname是否应该包含在当前File目录中，符合则返回true。

FilenameFilter 和 FileFilter 接口对象可以传递给 listFiles 方法作为参数

listFiles(FileFilter) 方法做了一下3件事：

1. 遍历构造方法中传递的目录，获取目录中每一个文件/文件夹，封装成 File 对象
2. 把遍历得到的 File 对象，传递给过滤器中的 accept 方法的参数 pathname
3. accept 方法返回值是布尔值，如果是 true，就把 File 对象添加到数组中，否则不会添加

```java
public class FileTest {
  public static void main(String[] args) {
    testSeparator();
    testConstructor();
    testFileGet();
    testExists();
    testFileMethod();
    testFileList();
    filterFile(new File("E:\\Java\\java-demo\\module02"));
  }
  // 分隔符
  public static void testSeparator(){
    // 路径分隔符  windows：分号    linux：冒号
    System.out.println("pathSeparator: " + File.pathSeparator); // ;
    // 文件名称分隔符 window：反斜杠 \  linux：正斜杠 /
    System.out.println("separator: " + File.separator); // \
  }

    // 构造方法
  public static void testConstructor() {
    // File(String pathname)
    // 路径可以是绝对路径，也可以是相对路径，可以是文件结尾，也可以以文件夹结尾
    // 创建 File 对象，只是把字符串路径封装为 File 对象，不考虑路径的真实情况
    File f1 = new File("aa.txt"); // 相对路径
    System.out.println(f1);

    // File(String parent, String child)
    // 路径分成父路径和子路径更灵活，父路径和子路径都可变化
    File f2 = new File("E:\\", "bb.txt");
    System.out.println(f2);

    // File(File parent, String child)
    // 父路径是 File 类型，可以使用 File 类的方法进行一些操作
    File parent = new File("E:\\");
    File f3 = new File(parent, "cc.txt");
    System.out.println(f3);
  }

  // 获取相关的方法
  public static void testFileGet() {
    String parent = "E:\\Java\\java-demo\\module02\\src\\demo08";
    File f = new File(parent,"FileTest.java");
    System.out.println(f);

    // getAbsolutePath 获取文件绝对路径
    System.out.println("文件绝对路径：" + f.getAbsolutePath());
    // getPath 获取构造路径
    System.out.println("文件构造路径：" + f.getPath());
    // getName 获取文件名
    System.out.println("文件名：" + f.getName()); // FileTest.java
    // length 获取文件大小
    System.out.println("文件大小： " + f.length()); // 3857字节，路径不存在返回 0
  }

  // 判断相关的方法
  public static void testExists() {
    String parent = "E:\\Java\\java-demo\\module02\\src\\demo08";
    String child = "FileTest.java";
    File f = new File(parent, child);

    // exists 判断文件或目录是否存在
    System.out.println(parent + child + " 是否存在：" + f.exists());
    // 如果路径不存在 isFile 和 isDirectory 都返回 false
    System.out.println(parent + child + " 是文件?：" + f.isFile());
    System.out.println(parent + child + " 是目录?：" + f.isDirectory());
  }

  // 创建删除相关的方法
  public static void testFileMethod() {
      // mkdir 创建文件夹， mkdirs 既可以创建单级文件夹，也可以创建多级文件夹
      // 路径不存在，不会创建，不会抛异常
      File f1 = new File("E:\\Java\\java-demo\\module02\\src\\demo08\\test");
      boolean b1 = f1.mkdirs();
      System.out.println("创建文件夹是否成功：" + b1);

      // createNewFile 当该文件名不存在时，创建新文件
      // 创建的文件路径必须存在，否则抛出异常
      File f2 = new File("E:\\Java\\java-demo\\module02\\src\\demo08\\test\\aa.txt");
      try {
        boolean b2 = f2.createNewFile();
        System.out.println("创建文件是否成功：" + b2);
        System.out.println(f2);
      } catch (IOException e) {
        e.printStackTrace();
      }

      // delete 删除文件或文件夹，删除成功返回 true
      // 文件夹不为空，则删除失败，路径不存在删除失败，返回 false
      // delete 是硬盘删除，谨慎使用
      File f3 = new File("E:\\Java\\java-demo\\module02\\src\\demo08\\test\\aa.txt");
        // boolean b3 = f3.delete();
        // System.out.println("删除是否成功：" + b3);
  }

  // 遍历目录相关的方法
  public static void testFileList() {
    // list 和 listFiles 遍历构造方法中给出的目录
    // 如果路径不存在或路径不是一个目录，会抛出空指针异常
    File f = new File("E:\\Java\\java-demo\\module02\\src\\demo06");

    // list 返回字符串数组
    String[] arr1 = f.list();
    for (String s : arr1) {
      System.out.println(s);
    }

    // listFiles 返回 File 类型数组
    File[] arr2 = f.listFiles();
    for (File file : arr2) {
      System.out.println(file);
    }
  }

  // 过滤文件，获取 java 文件
  public static void filterFile(File dir) {
    // 使用 FileFilter 接口的 Lambda 表达式，重写 accept 方法
    File[] files = dir.listFiles((pathname) -> {
      // 判断  pathname 后缀名是否为 .java，如果就添加到数组
      // 如果 pathname 是文件夹，也返回 true，添加到数组，继续过滤
      return pathname.isDirectory() || pathname.toString().toLowerCase().endsWith(".java");
    });

      // 也可以使用 FilenameFilter 接口的 Lambda 表达式
//      File[] files = dir.listFiles((d, name) -> new File(d, name).isDirectory() || name.toLowerCase().endsWith(".java"));

    for (File f : files) {
      if(f.isDirectory()) {
        filterFile(f);
      } else {
        System.out.println(f);
      }
    }
  }
}
```
