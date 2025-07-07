package com.example.mygo;

import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;
import com.example.mygo.databinding.FragmentHomeBinding;

public class HomeFragment extends Fragment {

    private FragmentHomeBinding binding;
    private SharedPreferences sharedPreferences;
    
    // 快捷操作按钮引用
    private View btnSetGoal;
    
    // 目标完成度相关UI元素
    private TextView tvProgressPercent, tvGoalCount, tvCurrentCount, tvProgressMessage;
    private ProgressBar progressGoal;
    
    // 运动卡片相关UI元素
    private TextView tvWorkoutCount, tvWorkoutDuration;
    
    // ViewModel用于获取图表数据
    private ChartViewModel chartViewModel;
    
    // 数据更新定时器
    private android.os.Handler updateHandler;
    private Runnable updateRunnable;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        binding = FragmentHomeBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        sharedPreferences = getActivity().getSharedPreferences("user_prefs", Context.MODE_PRIVATE);

        // 初始化UI元素
        initUIElements();
        
        // 设置用户信息
        setupUserInfo();
        
        // 设置点击事件
        setupClickListeners();
        
        // 初始化目标完成度显示
        updateGoalProgress();
        
        // 启动数据更新定时器
        startDataUpdateTimer();
    }

    /**
     * 初始化UI元素
     */
    private void initUIElements() {
        btnSetGoal = getView().findViewById(R.id.btn_set_goal);
        
        // 目标完成度相关UI元素
        tvProgressPercent = getView().findViewById(R.id.tv_progress_percent);
        tvGoalCount = getView().findViewById(R.id.tv_goal_count);
        tvCurrentCount = getView().findViewById(R.id.tv_current_count);
        tvProgressMessage = getView().findViewById(R.id.tv_progress_message);
        progressGoal = getView().findViewById(R.id.progress_goal);
        
        // 运动卡片相关UI元素
        tvWorkoutCount = getView().findViewById(R.id.tv_workout_count);
        tvWorkoutDuration = getView().findViewById(R.id.tv_workout_duration);
        
        // 获取ViewModel
        chartViewModel = new ViewModelProvider(requireActivity()).get(ChartViewModel.class);
    }

    /**
     * 设置用户信息
     */
    private void setupUserInfo() {
        // 读取昵称
        String nickname = sharedPreferences.getString("nickname", "运动达人");
        binding.etNickname.setText(nickname);

        // 读取个性签名
        String signature = sharedPreferences.getString("signature", "今天也要加油运动哦！💪");
        binding.etSignature.setText(signature);

        // 读取账号（email）
        String account = sharedPreferences.getString("email", "user@mygo.com");
        binding.tvWechatId.setText("SportAI账号：" + account);

        // 监听昵称变化并保存
        binding.etNickname.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override
            public void afterTextChanged(Editable s) {
                sharedPreferences.edit().putString("nickname", s.toString()).apply();
            }
        });

        // 监听个性签名变化并保存
        binding.etSignature.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override
            public void afterTextChanged(Editable s) {
                sharedPreferences.edit().putString("signature", s.toString()).apply();
            }
        });
    }

    /**
     * 设置点击事件
     */
    private void setupClickListeners() {
        // 设置目标按钮
        btnSetGoal.setOnClickListener(v -> {
            // 检查Fragment是否仍然附加到上下文
            if (!isAdded() || getContext() == null) {
                return;
            }
            showGoalSettingDialog();
        });

        // 登出按钮
        binding.buttonLogout.setOnClickListener(v -> {
            // 检查Fragment是否仍然附加到上下文
            if (!isAdded() || getContext() == null) {
                return;
            }
            
            // 获取 SharedPreferences
            SharedPreferences.Editor editor = sharedPreferences.edit();

            // 清除登录状态
            editor.putBoolean("is_logged_in", false);
            editor.apply();

            // 跳转回登录页面
            Intent intent = new Intent(getActivity(), LoginActivity.class);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
        });
    }

    /**
     * 显示目标设置对话框
     */
    private void showGoalSettingDialog() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        AlertDialog.Builder builder = new AlertDialog.Builder(getContext());
        builder.setTitle("设置今日目标");

        // 创建输入框
        final EditText input = new EditText(getContext());
        input.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        input.setHint("请输入今日运动目标次数");
        
        // 获取当前目标作为默认值
        int currentGoal = sharedPreferences.getInt("daily_goal", 0);
        if (currentGoal > 0) {
            input.setText(String.valueOf(currentGoal));
        }

        builder.setView(input);

        builder.setPositiveButton("确定", (dialog, which) -> {
            String goalText = input.getText().toString();
            if (!goalText.isEmpty()) {
                try {
                    int goal = Integer.parseInt(goalText);
                    if (goal > 0) {
                        // 保存目标
                        sharedPreferences.edit().putInt("daily_goal", goal).apply();
                        Toast.makeText(getContext(), "目标设置成功：" + goal + "次", Toast.LENGTH_SHORT).show();
                        updateGoalProgress();
                    } else {
                        Toast.makeText(getContext(), "请输入大于0的数字", Toast.LENGTH_SHORT).show();
                    }
                } catch (NumberFormatException e) {
                    Toast.makeText(getContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show();
                }
            } else {
                Toast.makeText(getContext(), "请输入目标次数", Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNegativeButton("取消", (dialog, which) -> dialog.cancel());

        builder.show();
    }

    /**
     * 更新目标完成度显示
     */
    private void updateGoalProgress() {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        // 获取今日目标
        int dailyGoal = sharedPreferences.getInt("daily_goal", 0);
        
        // 获取当前完成次数（从ChartViewModel获取）
        int currentCount = chartViewModel.getAllEntries().size();
        
        // 更新运动卡片数据
        updateWorkoutData(currentCount);
        
        // 更新UI显示
        if (dailyGoal > 0) {
            if (tvGoalCount != null) tvGoalCount.setText(String.valueOf(dailyGoal));
            if (tvCurrentCount != null) tvCurrentCount.setText(String.valueOf(currentCount));
            
            // 计算完成度百分比
            int progressPercent = (int)((currentCount * 100.0) / dailyGoal);
            if (progressPercent > 100) progressPercent = 100;
            
            // 更新进度条
            if (progressGoal != null) progressGoal.setProgress(progressPercent);
            if (tvProgressPercent != null) tvProgressPercent.setText(progressPercent + "%");
            
            // 根据完成情况设置颜色和消息
            if (progressPercent >= 100) {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                if (progressPercent > 100) {
                    if (tvProgressMessage != null) {
                        tvProgressMessage.setText("🎉 超额完成！继续保持！");
                        tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                    }
                } else {
                    if (tvProgressMessage != null) {
                        tvProgressMessage.setText("🎉 目标完成！太棒了！");
                        tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_green_dark));
                    }
                }
            } else if (progressPercent >= 80) {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_orange_dark));
                if (tvProgressMessage != null) {
                    tvProgressMessage.setText("💪 接近目标，继续加油！");
                    tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_orange_dark));
                }
            } else if (progressPercent >= 50) {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_blue_dark));
                if (tvProgressMessage != null) {
                    tvProgressMessage.setText("👍 完成过半，继续努力！");
                    tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_blue_dark));
                }
            } else {
                if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
                if (tvProgressMessage != null) {
                    tvProgressMessage.setText("⏰ 还需努力，加油！");
                    tvProgressMessage.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
                }
            }
        } else {
            // 未设置目标
            if (tvGoalCount != null) tvGoalCount.setText("未设置");
            if (tvCurrentCount != null) tvCurrentCount.setText(String.valueOf(currentCount));
            if (progressGoal != null) progressGoal.setProgress(0);
            if (tvProgressPercent != null) tvProgressPercent.setText("0%");
            if (tvProgressPercent != null) tvProgressPercent.setTextColor(getResources().getColor(android.R.color.darker_gray));
            if (tvProgressMessage != null) {
                tvProgressMessage.setText("请先设置今日目标");
                tvProgressMessage.setTextColor(getResources().getColor(android.R.color.darker_gray));
            }
        }
    }

    /**
     * 更新运动数据
     */
    private void updateWorkoutData(int workoutCount) {
        // 检查Fragment是否仍然附加到上下文
        if (!isAdded() || getContext() == null) {
            return;
        }
        
        // 更新运动次数
        if (tvWorkoutCount != null) {
            tvWorkoutCount.setText(String.valueOf(workoutCount));
        }
        
        // 计算运动时长（每次运动增加约4秒）
        double workoutDuration = workoutCount * (1.0 / 15.0);
        if (tvWorkoutDuration != null) {
            // 保留一位小数显示
            String durationText = String.format("%.1f", workoutDuration);
            tvWorkoutDuration.setText(durationText);
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        // 每次回到主页时更新目标完成度
        updateGoalProgress();
        // 重新启动数据更新定时器
        startDataUpdateTimer();
    }
    
    @Override
    public void onPause() {
        super.onPause();
        // 停止数据更新定时器
        stopDataUpdateTimer();
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        // 停止数据更新定时器
        stopDataUpdateTimer();
        binding = null; // 避免内存泄漏
    }
    
    /**
     * 启动数据更新定时器
     */
    private void startDataUpdateTimer() {
        if (updateHandler == null) {
            updateHandler = new android.os.Handler(android.os.Looper.getMainLooper());
        }
        
        if (updateRunnable == null) {
            updateRunnable = new Runnable() {
                @Override
                public void run() {
                    updateGoalProgress();
                    // 每秒更新一次
                    updateHandler.postDelayed(this, 1000);
                }
            };
        }
        
        updateHandler.post(updateRunnable);
    }
    
    /**
     * 停止数据更新定时器
     */
    private void stopDataUpdateTimer() {
        if (updateHandler != null && updateRunnable != null) {
            updateHandler.removeCallbacks(updateRunnable);
        }
    }
}