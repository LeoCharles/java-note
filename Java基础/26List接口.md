# List 接口

java.util.List 接口继承自 Collection 接口。

List 接口特点：

1. 有序的集合，存储元素和取出元素的顺序一致
2. 有索引，包含了一些带索引的方法
3. 允许存储重复的元素

List 接口中带索引的方法：

`void add(int index, E element)`：将指定的元素，添加到该集合中的指定位置上

`E get(int index)`：返回集合中指定位置的元素

`E remove(int index)`： 移除列表中指定位置的元素, 返回的是被移除的元素

`E set(int index, E element)`：用指定元素替换集合中指定位置的元素, 返回值的更新前的元素

注意操作索引的时候，一定要防止索引越界异常 IndexOutOfBoundsException

## ArrayList

java.util.ArrayList 类是 List 接口的大小可变数组的实现

特点：查询快，增删慢

日常开发中使用最多的功能为查询数据、遍历数据，ArrayList 是最常用的集合

```java
public class ListTest {
  public static void main(String[] args) {
    // 创建一个 List 集合对象，使用多态
    List<String> list = new ArrayList<>();
    list.add("Amy");
    list.add("Eve");
    list.add("Joy");
    list.add("May");
    list.add("Van");
    list.add("Roy");
    list.add("Rex");
    list.add("Jim");
    list.add("Roy"); // 允许重复
    System.out.println(list);
    // 在指定索引位置添加元素
    list.add(2, "Tom");
    System.out.println(list);
    // 移除指定索引位置的元素
    String rmE = list.remove(2);
    System.out.println("删除的元素：" + rmE); // Tom
    // 用指定元素替换指定索引位置的元素，返回被替换的元素
    String setE = list.set(0, "Leo");
    System.out.println("被替换的元素：" + setE);

    // 遍历 List 集合的 3 种方法
    System.out.println("for 循环遍历");
    for (int i = 0; i < list.size(); i++) {
        System.out.println(list.get(i));
    }
    System.out.println("迭代器遍历：");
    Iterator<String> it = list.iterator();
    while (it.hasNext()) {
        System.out.println(it.next());
    }
    System.out.println("增强 for 循环：");
    for (String s : list) {
        System.out.println(s);
    }
  }
}
```

## LinkedList

java.util.LinkedList 类是 List 接口的链接列表实现

特点：查询慢，增删快

LinkedList 提供了大量首尾操作的方法：

`void addFirst(E e)`：将指定元素插入此列表的开头

`void addLast(E e)`：将指定元素添加到此列表的结尾

`void push(E e)`：将元素插入此列表的开头，等效于 addFirst

`E getFirst()`：返回此列表的第一个元素

`E getLast()`：返回此列表的最后一个元素

`E removeFirst()`：移除并返回此列表的第一个元素

`E removeLast()`：移除并返回此列表的最后一个元素

`E pop()`：移除并返回此列表的第一个元素，等效于 removeFirst

```java
public class ListTest {
  public static void main(String[] args) {
    // 创建 LinkedList
    LinkedList<String> linkedList = new LinkedList<>();
    // 将指定元素添加到集合末尾  add / addLast
    linkedList.add("Amy");
    linkedList.add("Eve");
    linkedList.add("Joy");
    linkedList.addLast("Eve");
    System.out.println(linkedList);
    // 判断是否为空
    System.out.println(linkedList.isEmpty());
    // 将指定元素添加到集合开头  addFirst / push
    linkedList.addFirst("Bob");
    linkedList.push("Leo");
    System.out.println(linkedList);
    // 获取第一个元素，移除最后一个元素  getFirst / getLast
    System.out.println(linkedList.getFirst());
    System.out.println(linkedList.getLast());
    // 移除第一个元素 removeFirst / pop
    System.out.println(linkedList.removeFirst());
    System.out.println(linkedList.pop());
    // 移除最后一个元素
    System.out.println(linkedList.removeLast());
    System.out.println(linkedList);
  }
}
```
