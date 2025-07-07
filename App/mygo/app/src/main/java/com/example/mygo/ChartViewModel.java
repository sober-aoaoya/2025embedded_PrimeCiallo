package com.example.mygo;

import androidx.lifecycle.ViewModel;
import com.github.mikephil.charting.data.Entry;
import java.util.ArrayList;
import java.util.List;

public class ChartViewModel extends ViewModel {
    private final List<Entry> allEntries = new ArrayList<>();
    
    // 添加统计数据字段，用于保存最新的统计数据
    private float currentScore = 0;
    private float maxScore = 0;
    private float averageScore = 0;

    public List<Entry> getAllEntries() {
        return allEntries;
    }

    public void addEntry(Entry entry) {
        allEntries.add(entry);
        // 每次添加新数据时，更新统计数据
        updateStatistics(entry.getY());
    }

    public void clear() {
        allEntries.clear();
        // 清空时重置统计数据
        currentScore = 0;
        maxScore = 0;
        averageScore = 0;
    }
    
    /**
     * 更新统计数据
     */
    private void updateStatistics(float newScore) {
        currentScore = newScore;
        
        // 更新最高分
        if (newScore > maxScore) {
            maxScore = newScore;
        }
        
        // 重新计算平均分
        if (!allEntries.isEmpty()) {
            float totalScore = 0;
            for (Entry entry : allEntries) {
                totalScore += entry.getY();
            }
            averageScore = totalScore / allEntries.size();
        }
    }
    
    /**
     * 获取最高分
     */
    public float getMaxScore() {
        return maxScore;
    }
    
    /**
     * 获取平均分
     */
    public float getAverageScore() {
        return averageScore;
    }
    
    /**
     * 获取当前分数（最新分数）
     */
    public float getCurrentScore() {
        return currentScore;
    }
}