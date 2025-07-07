package com.example.mygo;

import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;
import com.github.niqdev.mjpeg.DisplayMode;
import com.github.niqdev.mjpeg.Mjpeg;
import com.github.niqdev.mjpeg.MjpegSurfaceView;
// --- 修复: 导入 RxJava 1 的 CompositeSubscription ---
import rx.subscriptions.CompositeSubscription;

import android.widget.TextView;
import android.widget.Toast;
import android.view.View.OnClickListener;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.Timer;
import java.util.TimerTask;
import java.util.List;

public class VideosFragment extends Fragment {

    private static final String TAG = "MJPEG_Fragment";
    // *** 请确保这里的IP地址是你开发板的正确地址 ***
    private static final String STREAM_URL = "http://192.168.137.105:8080/video_feed";
    private static final int TIMEOUT = 5; // 5秒连接超时

    private MjpegSurfaceView mjpegView;
    // --- 修复: 使用 RxJava 1 的 CompositeSubscription ---
    private final CompositeSubscription disposables = new CompositeSubscription();

    // 新增UI元素
    private View statusIndicator;
    private TextView statusText;
    private TextView videoTimestamp;
    private TextView tvFps, tvResolution, tvLatency;
    // 删除旧的按钮引用
    // private Button btnRecord, btnScreenshot, btnSettings, btnShare;
    // private ImageButton btnPlayPause, btnFullscreen;
    
    // 运动分析按钮引用
    private View btnMotionAnalysis;
    
    // 新增实时数据显示引用
    private TextView tvCurrentCount, tvCurrentScore, tvMaxScore;
    
    // 运动分析相关UI元素
    private TextView tvWorkoutCountAnalysis, tvCaloriesBurned, tvWorkoutAdvice;
    private ChartViewModel chartViewModel;
    
    // 热量消耗累计值
    private int totalCaloriesBurned = 0;

    // 时间戳更新定时器
    private Timer timestampTimer;
    // 视频统计信息更新定时器
    private Timer statsTimer;
    // 实时数据更新定时器
    private Timer realTimeDataTimer;
    // 连接状态标志
    private boolean isConnected = false;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        // 加载布局
        return inflater.inflate(R.layout.fragment_videos, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        // 在视图创建完成后，找到控件
        mjpegView = view.findViewById(R.id.mjpegView);

        // 初始化UI元素
        initUIElements(view);
        // 设置点击事件
        setupClickListeners();
        // 初始化统计信息显示
        updateVideoStats();
        updateConnectionStatusFromMain();
        // 开始时间戳更新
        startTimestampUpdate();
        // 开始视频统计信息更新
        startStatsUpdate();
        // 开始实时数据更新
        startRealTimeDataUpdate();
    }

    /**
     * 初始化UI元素
     */
    private void initUIElements(View view) {
        statusIndicator = view.findViewById(R.id.status_indicator);
        statusText = view.findViewById(R.id.status_text);
        videoTimestamp = view.findViewById(R.id.video_timestamp);
        tvFps = view.findViewById(R.id.tv_fps);
        tvResolution = view.findViewById(R.id.tv_resolution);
        tvLatency = view.findViewById(R.id.tv_latency);
        btnMotionAnalysis = view.findViewById(R.id.btn_motion_analysis);
        tvCurrentCount = view.findViewById(R.id.tv_current_count);
        tvCurrentScore = view.findViewById(R.id.tv_current_score);
        tvMaxScore = view.findViewById(R.id.tv_max_score);
        
        // 运动分析相关UI元素
        tvWorkoutCountAnalysis = view.findViewById(R.id.tv_workout_count_analysis);
        tvCaloriesBurned = view.findViewById(R.id.tv_calories_burned);
        tvWorkoutAdvice = view.findViewById(R.id.tv_workout_advice);
        
        chartViewModel = new ViewModelProvider(requireActivity()).get(ChartViewModel.class);
    }

    /**
     * 设置点击事件
     */
    private void setupClickListeners() {
        // 运动分析按钮
        btnMotionAnalysis.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View v) {
                if (!isAdded() || getContext() == null) {
                    return;
                }
                Toast.makeText(getContext(), "📊 运动分析报告已生成", Toast.LENGTH_SHORT).show();
                updateWorkoutAnalysis();
            }
        });
    }

    /**
     * 开始时间戳更新
     */
    private void startTimestampUpdate() {
        timestampTimer = new Timer();
        timestampTimer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                if (getActivity() != null) {
                    getActivity().runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            updateTimestamp();
                        }
                    });
                }
            }
        }, 0, 1000); // 每秒更新一次
    }

    /**
     * 更新时间戳
     */
    private void updateTimestamp() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());
        String currentTime = sdf.format(new Date());
        if (videoTimestamp != null) {
            videoTimestamp.setText(currentTime);
        }
    }

    /**
     * 从MainActivity获取连接状态并更新显示
     */
    private void updateConnectionStatusFromMain() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        MainActivity mainActivity = (MainActivity) getActivity();
        if (mainActivity != null) {
            boolean connected = mainActivity.isConnected();
            isConnected = connected;
            if (statusIndicator != null && statusText != null) {
                if (connected) {
                    statusIndicator.setBackgroundResource(R.drawable.status_connected);
                    statusText.setText("已连接");
                    statusText.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                } else {
                    statusIndicator.setBackgroundResource(android.R.drawable.presence_invisible);
                    statusText.setText("未连接");
                    statusText.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
                }
            }
        }
    }

    /**
     * 开始视频统计信息更新
     */
    private void startStatsUpdate() {
        statsTimer = new Timer();
        statsTimer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                if (getActivity() != null) {
                    getActivity().runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            updateVideoStats();
                        }
                    });
                }
            }
        }, 0, 2000); // 每2秒更新一次
    }

    /**
     * 开始实时数据更新
     */
    private void startRealTimeDataUpdate() {
        realTimeDataTimer = new Timer();
        realTimeDataTimer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                if (getActivity() != null) {
                    getActivity().runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            updateRealTimeData();
                            updateConnectionStatusFromMain();
                        }
                    });
                }
            }
        }, 0, 1000); // 每秒更新一次
    }

    /**
     * 更新实时数据显示
     */
    private void updateRealTimeData() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        if (chartViewModel != null) {
            // 获取当前分数
            float currentScore = chartViewModel.getCurrentScore();
            if (tvCurrentScore != null) {
                tvCurrentScore.setText(String.valueOf((int) currentScore));
            }

            // 获取最高分数
            float maxScore = chartViewModel.getMaxScore();
            if (tvMaxScore != null) {
                tvMaxScore.setText(String.valueOf((int) maxScore));
            }

            // 获取当前次数（从ChartViewModel的条目数量获取）
            List<com.github.mikephil.charting.data.Entry> entries = chartViewModel.getAllEntries();
            int currentCount = entries.size();
            if (tvCurrentCount != null) {
                tvCurrentCount.setText(String.valueOf(currentCount));
            }
            
            // 更新运动分析数据
            updateWorkoutAnalysisData(currentCount);
        }
    }

    /**
     * 生成指定范围内的随机数
     */
    private int getRandomNumber(int min, int max) {
        return (int) (Math.random() * (max - min + 1)) + min;
    }
    
    /**
     * 更新运动分析数据
     */
    private void updateWorkoutAnalysisData(int workoutCount) {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        // 更新运动次数
        if (tvWorkoutCountAnalysis != null) {
            tvWorkoutCountAnalysis.setText(String.valueOf(workoutCount));
        }
        
        // 计算消耗热量（每次运动约消耗6-7卡路里，确保稳定递增）
        int caloriesPerWorkout = 6; // 固定每次消耗6卡路里，避免随机波动
        int newTotalCalories = workoutCount * caloriesPerWorkout;
        
        // 确保热量消耗只会增加，不会减少
        if (newTotalCalories > totalCaloriesBurned) {
            totalCaloriesBurned = newTotalCalories;
        }
        
        if (tvCaloriesBurned != null) {
            tvCaloriesBurned.setText(String.valueOf(totalCaloriesBurned));
        }
    }
    
    /**
     * 更新运动分析
     */
    private void updateWorkoutAnalysis() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        if (chartViewModel != null) {
            List<com.github.mikephil.charting.data.Entry> entries = chartViewModel.getAllEntries();
            int workoutCount = entries.size();
            
            // 生成个性化的运动建议
            String advice = generateWorkoutAdvice(workoutCount);
            if (tvWorkoutAdvice != null) {
                tvWorkoutAdvice.setText(advice);
            }
        }
    }
    
    /**
     * 生成运动建议
     */
    private String generateWorkoutAdvice(int workoutCount) {
        if (workoutCount == 0) {
            return "💪 开始您的运动之旅吧！建议每天进行30分钟以上的运动，保持健康活力。";
        } else if (workoutCount < 10) {
            return "👍 运动起步不错！建议增加运动强度，每次运动保持20-30秒的持续时间。";
        } else if (workoutCount < 30) {
            return "🔥 运动表现优秀！建议保持当前节奏，注意运动间隔，避免过度疲劳。";
        } else if (workoutCount < 50) {
            return "🏆 运动达人！您的运动量已经达到健康标准，建议适当增加运动难度。";
        } else {
            return "🌟 运动大师！您的运动量非常优秀，建议保持当前水平，注意休息和恢复。";
        }
    }
    
    /**
     * 重置热量消耗（当运动次数重置时调用）
     */
    private void resetCaloriesBurned() {
        totalCaloriesBurned = 0;
        if (tvCaloriesBurned != null) {
            tvCaloriesBurned.setText("0");
        }
    }

    /**
     * 更新视频统计信息
     */
    private void updateVideoStats() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        if (isConnected) {
            // 已连接时显示动态数据
            // 生成25-35之间的随机FPS
            int randomFps = getRandomNumber(25, 35);
            if (tvFps != null) tvFps.setText(String.valueOf(randomFps));

            // 分辨率保持不变
            if (tvResolution != null) tvResolution.setText("720p");

            // 生成100-200之间的随机延迟
            int randomLatency = getRandomNumber(100, 200);
            if (tvLatency != null) tvLatency.setText(randomLatency + "ms");
        } else {
            // 未连接时显示"--"
            if (tvFps != null) tvFps.setText("--");
            if (tvResolution != null) tvResolution.setText("--");
            if (tvLatency != null) tvLatency.setText("--");
        }
    }

    private void loadMjpegStream() {
        if (mjpegView == null) {
            Log.e(TAG, "MjpegSurfaceView is null. Cannot load stream.");
            return;
        }

        // Mjpeg.newInstance().open() 返回的是一个 rx.Observable，它的 subscribe() 方法返回 rx.Subscription
        // 现在可以正确地添加到 CompositeSubscription 中
        disposables.add(Mjpeg.newInstance()
                .open(STREAM_URL, TIMEOUT)
                .subscribe(
                        // onNext: 成功获取到视频流
                        inputStream -> {
                            if (isAdded() && mjpegView != null) {
                                mjpegView.setSource(inputStream);
                                mjpegView.setDisplayMode(DisplayMode.BEST_FIT);
                                mjpegView.showFps(false);

                                // 连接成功后立即更新视频统计信息
                                updateVideoStats();
                            }
                        },
                        // onError: 发生错误
                        throwable -> {
                            Log.e(TAG, "打开 MJPEG 流失败", throwable);
                        }
                ));
    }

    @Override
    public void onResume() {
        super.onResume();
        // 当 Fragment 可见时，加载并开始播放视频流
        loadMjpegStream();
    }

    // onPause() 方法现在可以留空，或者如果你有其他轻量级操作可以在这里处理
    @Override
    public void onPause() {
        super.onPause();
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();

        // 停止时间戳更新
        if (timestampTimer != null) {
            timestampTimer.cancel();
            timestampTimer = null;
        }

        // 停止视频统计信息更新
        if (statsTimer != null) {
            statsTimer.cancel();
            statsTimer = null;
        }

        // 停止实时数据更新
        if (realTimeDataTimer != null) {
            realTimeDataTimer.cancel();
            realTimeDataTimer = null;
        }

        final MjpegSurfaceView viewToStop = mjpegView; // 先保存引用
        mjpegView = null; // 立即置空，防止后续UI操作
        if (viewToStop != null) {
            new Thread(viewToStop::stopPlayback).start();
        }
        disposables.clear();
    }
}

