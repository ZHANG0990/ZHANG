import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Comparator;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.stream.Stream;

// 这个数据类可以保持不变，但为了简洁，我们可以使用 Java 16+ 的 record 特性。
// 这里我们继续使用 class 以保证对旧版 Java 的兼容性。
class LetterFrequency implements Comparable<LetterFrequency> {
    char letter;
    double frequency;

    public LetterFrequency(char letter, double frequency) {
        this.letter = letter;
        this.frequency = frequency;
    }

    @Override
    public String toString() {
        return String.format("%S: %.2f%%", letter, frequency);
    }

    @Override
    public int compareTo(LetterFrequency other) {
        // 比较逻辑不变: 1. 频率降序, 2. 字母升序
        int freqCompare = Double.compare(other.frequency, this.frequency);
        if (freqCompare == 0) {
            return Character.compare(this.letter, other.letter);
        }
        return freqCompare;
    }
}


public class WF {

    public static void main(String[] args) {
        if (args.length != 2 || !args[0].equals("-c")) {
            System.err.println("使用方法: java WF -c <file_name>");
            System.exit(1);
        }
        String filePath = args[1];
        
        analyzeCharacterFrequency(filePath);
    }

    public static void analyzeCharacterFrequency(String filePath) {
        
        try (Stream<String> lines = Files.lines(Paths.get(filePath))) {
            
            // 1. 使用 Streams API 进行流式处理
            Map<Character, Long> letterCounts = lines
                .flatMapToInt(String::chars) // 将每行的 String 转换成 IntStream of characters
                .map(Character::toLowerCase) // 全部转为小写
                .filter(c -> c >= 'a' && c <= 'z') // 只保留 a-z 之间的字母
                .mapToObj(c -> (char) c) // 将 int 转回 Character
                .collect(Collectors.groupingBy(Function.identity(), Collectors.counting())); // 分组并计数

            // 2. 计算字母总数
            long totalLetters = letterCounts.values().stream().mapToLong(Long::longValue).sum();

            if (totalLetters == 0) {
                System.out.println("文件中没有找到任何英文字母。");
                return;
            }

            // 3. 计算频率、排序并打印
            System.out.println("字母频率分析结果 (优化版):");
            
            // 将 'a' 到 'z' 的所有字母都包含进来，即使它们在文本中没有出现
            "abcdefghijklmnopqrstuvwxyz".chars()
                .mapToObj(c -> (char) c)
                .map(letter -> {
                    long count = letterCounts.getOrDefault(letter, 0L);
                    double frequency = ((double) count / totalLetters) * 100;
                    return new LetterFrequency(letter, frequency);
                })
                .sorted() // 使用 LetterFrequency 中定义的 compareTo 方法排序
                .forEach(System.out::println); // 逐行打印

        } catch (IOException e) {
            System.err.println("错误: 读取文件时发生异常 -> " + e.getMessage());
            System.exit(1);
        }
    }
}