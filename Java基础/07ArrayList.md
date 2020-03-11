# ArrayList

数组的长度不可以发生改变，但是 ArrayList 集合的长度可以随意改变。

ArrayList 中一对尖括号代表泛型，泛型只能是引用类型，不能是基本类型。

对于 ArrayList 来说，直接打印的不是地址，而是内容。

ArrayList 常用方法：

+ add(): 向集合中添加元素，参数的类型和泛型一致。
+ get(): 从集合中获取元素，参数是索引编号，返回值是对应位置元素。
+ remove(): 从集合中删除元素，参数是索引编号，返回值是被删除的元素。
+ size(): 获取集合中包含的元素个数。

```java
public class ArrayListTest {
    public static void main(String[] args) {
        // 创建一个全都是 String 类型的 ArrayList
        ArrayList<String> strArrayList = new ArrayList<>();
        System.out.println(strArrayList); // []
        // 添加数据
        strArrayList.add("学习 Java");
        strArrayList.add("学习 Spring");
        strArrayList.add("学习 React");
        strArrayList.add("学习 Electron");
        // 集合长度
        System.out.println(strArrayList.size()); // 4
        // 获取元素
        System.out.println(strArrayList.get(2)); // 学习 React
        // 删除元素
        String whoRemoved = strArrayList.remove(3);
        System.out.println(whoRemoved); // 学习 Electron
        // 遍历集合
        for (int i = 0; i < strArrayList.size(); i++) {
            System.out.println(strArrayList.get(i));
        }
    }
}
```

如果需要在 ArrayList 中存储基本类型数据，必须使用基本类型的包装类。

+ byte    =>    Byte
+ short   =>    Short
+ int     =>    Integer
+ long    =>    Long
+ float   =>    Float
+ double  =>    Double
+ char    =>    Character
+ boolean =>    Boolean
