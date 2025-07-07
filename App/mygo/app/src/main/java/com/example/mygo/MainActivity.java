package com.example.mygo;

import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentManager;
import androidx.fragment.app.FragmentTransaction;
import androidx.lifecycle.ViewModelProvider;
import com.example.mygo.databinding.ActivityMainBinding;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.Socket;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainActivity extends AppCompatActivity {

    private ActivityMainBinding binding;
    private ChartViewModel chartViewModel;
    
    // 全局数据接收相关
    private Thread globalDataThread;
    private final Handler uiHandler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean isConnected = new AtomicBoolean(false);
    
    // 开发板连接配置
    private static final String SERVER_IP = "192.168.137.105";
    private static final int SERVER_PORT = 9999;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        // 初始化ViewModel
        chartViewModel = new ViewModelProvider(this).get(ChartViewModel.class);

        // 设置底部导航栏的监听器
        binding.bottomNavigation.setOnItemSelectedListener(item -> {
            Fragment selectedFragment = null;
            int itemId = item.getItemId();

            if (itemId == R.id.nav_home) {
                selectedFragment = new HomeFragment();
            } else if (itemId == R.id.nav_videos) {
                selectedFragment = new VideosFragment();
            } else if (itemId == R.id.nav_charts) {
                selectedFragment = new ChartsFragment();
            }

            if (selectedFragment != null) {
                // 调用方法来替换 Fragment
                replaceFragment(selectedFragment);
            }
            return true;
        });

        // 设置默认显示的 Fragment
        if (savedInstanceState == null) {
            binding.bottomNavigation.setSelectedItemId(R.id.nav_home);
        }
        
        // 启动全局数据接收
        startGlobalDataReceiver();
    }

    // 一个用于替换 FrameLayout 中 Fragment 的通用方法
    private void replaceFragment(Fragment fragment) {
        FragmentManager fragmentManager = getSupportFragmentManager();
        FragmentTransaction fragmentTransaction = fragmentManager.beginTransaction();
        fragmentTransaction.replace(R.id.fragment_container, fragment);
        fragmentTransaction.commit();
    }
    
    /**
     * 启动全局数据接收
     */
    private void startGlobalDataReceiver() {
        if (globalDataThread != null && globalDataThread.isAlive()) {
            return; // 线程已在运行
        }
        
        globalDataThread = new Thread(() -> {
            try (Socket socket = new Socket(SERVER_IP, SERVER_PORT);
                 BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream()))) {

                // 连接成功
                isConnected.set(true);
                uiHandler.post(() -> {
                    Toast.makeText(this, "已连接到开发板", Toast.LENGTH_SHORT).show();
                });

                String line;
                while (!Thread.currentThread().isInterrupted() && (line = reader.readLine()) != null) {
                    try {
                        JSONObject json = new JSONObject(line);
                        float count = (float) json.getInt("count");
                        float score = (float) json.getInt("score");

                        // 在UI线程上更新ViewModel数据
                        uiHandler.post(() -> {
                            if (chartViewModel != null) {
                                chartViewModel.addEntry(new com.github.mikephil.charting.data.Entry(count, score));
                            }
                        });

                    } catch (JSONException e) {
                        // JSON解析错误
                        System.err.println("JSON 解析错误: " + e.getMessage());
                    }
                }
            } catch (IOException e) {
                // 网络错误
                System.err.println("网络连接错误: " + e.getMessage());
                isConnected.set(false);
                uiHandler.post(() -> {
                    Toast.makeText(this, "无法连接到开发板", Toast.LENGTH_SHORT).show();
                });
            } finally {
                System.out.println("全局数据接收线程已停止。");
                isConnected.set(false);
            }
        });
        globalDataThread.start();
    }
    
    /**
     * 停止全局数据接收
     */
    private void stopGlobalDataReceiver() {
        if (globalDataThread != null) {
            globalDataThread.interrupt();
            globalDataThread = null;
        }
        isConnected.set(false);
    }
    
    /**
     * 获取连接状态
     */
    public boolean isConnected() {
        return isConnected.get();
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        // 停止全局数据接收
        stopGlobalDataReceiver();
    }
}