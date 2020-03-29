# Collections 集合工具类

常用方法：

`public static <T> boolean addAll(Collection<T> c, T... elements)` 往集合中添加一些元素。
`public static void shuffle(List<?> list)` 打乱集合顺序。
`public static <T> void sort(List<T> list)` 将集合中元素按照默认规则排序。
`public static <T> void sort(List<T> list，Comparator<? super T> )` 将集合中元素按照指定规则排序。

自定义类排序必须实现 Comparable 接口的 compareTo 方法。

Comparable:

强行对实现它的每个类的对象进行整体排序。

这种排序被称为类的自然排序，类的 compareTo 方法被称为它的自然比较方法。

只能在类中实现 compareTo 一次，不能经常修改类的代码实现自己想要的排序。

实现此接口的对象列表（和数组）可以通过 Collections.sort（和Arrays.sort）进行自动排序。

对象可以用作有序映射中的键或有序集合中的元素，无需指定比较器。

Comparator：

强行对某个对象进行整体排序。

可以将 Comparator 传递给 sort 方法（如Collections.sort或 Arrays.sort），从而允许在排序顺序上实现精确控制。

还可以使用 Comparator来控制某些数据结构（如有序 set 或有序映射）的顺序。

或者为那些没有自然顺序的对象 collection 提供排序。

```java
public class CollectionsTest {
  public static void main(String[] args) {
    ArrayList<String> list = new ArrayList<>();

    // addAll 往集合中添加多个元素
    Collections.addAll(list, "Amy", "Van", "Bob", "Joy", "Eve", "Rex");
    System.out.println(list);

    // shuffle 打乱集合顺序
    Collections.shuffle(list);
    System.out.println(list);

    // sort 集合排序，默认升序
    Collections.sort(list);
    System.out.println(list);

    // 自定义类集合排序，必须实现 Comparable 接口的 compareTo 方法
    ArrayList<Person> personList = new ArrayList<>();
    personList.add(new Person("Amy", 29));
    personList.add(new Person("Joy", 22));
    personList.add(new Person("Bob", 22));
    personList.add(new Person("Rex", 24));
    System.out.println(personList);
    Collections.sort(personList);
    System.out.println(personList);

    // 使用 sort 方法，传入 Comparator 比较器
    ArrayList<Integer> intList = new ArrayList<>();
    Collections.addAll(intList, 23, 44, 92, 28, 19, 75, 64);
    System.out.println(intList);
    // 使用内部类 传入比较器
    Collections.sort(intList, new Comparator<Integer>() {
        @Override
        public int compare(Integer t1, Integer t2) {
            // 升序：t1 - t2    降序：t2 - t1
            return t2 - t1;
        }
    });
    System.out.println(intList);

    // 传入比较器
    Collections.sort(personList, new Comparator<Person>() {
        @Override
        public int compare(Person p1, Person p2) {
            // 先年龄排序，如果年龄相同按姓名首字母排序
            int res = p1.getAge() - p2.getAge();
            if (res == 0) {
                // 比较姓名首字母
                res = p1.getName().charAt(0) - p2.getName().charAt(0);
            }
            return res;
        }
    });
    System.out.println(personList);
  }
}
```
