import csv
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from Ui_MyData import Ui_MyData
from PyQt5.QtGui import QImage, QPixmap

class MyDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MyData()
        self.ui.setupUi(self)
        
        self.chart_manager = chartManager()
        actcount_data = self.chart_manager.get_actcount_data()
        
        self.ui.exitpushButton.clicked.connect(self.on_exit_clicked)
        self.ui.actfrepushButton.clicked.connect(self.on_frequency_clicked)
        self.ui.scorepushButton.clicked.connect(self.on_score_clicked)
        self.ui.heatpushButton.clicked.connect(self.on_calories_clicked)
        self.ui.timepartpushButton.clicked.connect(self.on_time_proportion_clicked)
        
        self.ui.graphlabel.setText("请选择要查看的图表")
        
    def on_exit_clicked(self):
        self.accept()
        self.close()
        
    def on_frequency_clicked(self):
        self.chart_manager.point_frequency_line_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))
        
    def on_score_clicked(self):
        self.chart_manager.point_score_line_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))
    
    def on_calories_clicked(self):
        self.chart_manager.point_calories_line_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))

        
    def on_time_proportion_clicked(self):
        self.chart_manager.point_time_proportion_pie_chart()
        chart = QImage('temp.png')
        self.ui.graphlabel.setPixmap(QPixmap.fromImage(chart))

class chartManager:
    """图表管理类"""
    def __init__(self):
        self.csv_manager = csvManager('exercise_records.csv')
        self.data_list = self.csv_manager.read_csv()
        plt.rcParams['font.size'] = 2.4  # 字体大小
    
    def get_actfrequency_data(self):
        """获取近7天三种运动的频率数据（[深蹲,仰卧起坐,俯卧撑]）"""
        date_index_map = {}
        actfrequency_data = []
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            actfrequency_data.append([0, 0, 0])
            
        for record in self.data_list:
            if 'date' in record and 'type' in record:
                date = record['date']
                act_type = record['type']
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':  actfrequency_data[idx][0] += 1
                    elif act_type == '仰卧起坐':  actfrequency_data[idx][1] += 1
                    elif act_type == '俯卧撑':  actfrequency_data[idx][2] += 1
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [actfrequency_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0, 0, 0])
            return recent_data
        return [[0, 0, 0]] * 7


    def get_actcount_data(self):
        """获取近7天三种运动的总次数数据"""
        date_index_map = {}
        actcount_data = []
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            actcount_data.append([0, 0, 0])
        
        for record in self.data_list:
            if 'date' in record and 'type' in record and 'count' in record:
                date = record['date']
                act_type = record['type']
                count = int(record['count'])
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':  actcount_data[idx][0] += count
                    elif act_type == '仰卧起坐':  actcount_data[idx][1] += count
                    elif act_type == '俯卧撑':  actcount_data[idx][2] += count
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [actcount_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0, 0, 0])
            return recent_data
        return [[0, 0, 0]] * 7


    def get_actscore_data(self):
        """获取近7天三种运动的平均评分数据"""
        date_index_map = {}
        actscore_data = []  # 总分
        actcount_data = []  # 次数
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            actscore_data.append([0, 0, 0])
            actcount_data.append([0, 0, 0])
        
        for record in self.data_list:
            if 'date' in record and 'type' in record and 'score' in record:
                date = record['date']
                act_type = record['type']
                score = int(record['score'])
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':
                        actscore_data[idx][0] += score
                        actcount_data[idx][0] += 1
                    elif act_type == '仰卧起坐':
                        actscore_data[idx][1] += score
                        actcount_data[idx][1] += 1
                    elif act_type == '俯卧撑':
                        actscore_data[idx][2] += score
                        actcount_data[idx][2] += 1
        
        # 计算平均分
        for i in range(len(actscore_data)):
            for j in range(3):
                actscore_data[i][j] = actscore_data[i][j]/actcount_data[i][j] if actcount_data[i][j] > 0 else 60.0
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [actscore_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0.0, 0.0, 0.0])
            return recent_data
        return [[0.0, 0.0, 0.0]] * 7

    def get_acttime_proportion(self):
        """获取近7天三种运动的时间占比数据"""
        date_index_map = {}
        acttime_data = []
        all_dates = sorted({record['date'] for record in self.data_list if 'date' in record})
        
        for idx, date in enumerate(all_dates):
            date_index_map[date] = idx
            acttime_data.append([0, 0, 0])
        
        for record in self.data_list:
            if 'date' in record and 'type' in record and 'count' in record:
                date = record['date']
                act_type = record['type']
                count = int(record['count'])
                if date in date_index_map:
                    idx = date_index_map[date]
                    if act_type == '深蹲':  acttime_data[idx][0] += count
                    elif act_type == '仰卧起坐':  acttime_data[idx][1] += count
                    elif act_type == '俯卧撑':  acttime_data[idx][2] += count
        
        # 计算占比
        for i in range(len(acttime_data)):
            total_time = sum(acttime_data[i])
            acttime_data[i] = [time/total_time for time in acttime_data[i]] if total_time > 0 else [0.0, 0.0, 0.0]
        
        if all_dates:
            recent_7_dates = all_dates[-7:] if len(all_dates) > 7 else all_dates
            recent_data = [acttime_data[date_index_map[date]] for date in recent_7_dates]
            while len(recent_data) < 7:
                recent_data.append([0.0, 0.0, 0.0])
            return recent_data
        return [[0.0, 0.0, 0.0]] * 7
    
    def point_frequency_line_chart(self):
        """绘制近7天运动频率折线图，保存为temp.png"""
        actfrequency_data = self.get_actfrequency_data()
        dates = [i for i in range(len(actfrequency_data))]
        squat_freq = [data[0] for data in actfrequency_data]
        situp_freq = [data[1] for data in actfrequency_data]
        pushup_freq = [data[2] for data in actfrequency_data]
        
        plt.figure(figsize=(2.133, 1.266))
        plt.plot(dates, squat_freq, label='squat', marker='o', markersize=3)
        plt.plot(dates, situp_freq, label='situp', marker='o', markersize=3)
        plt.plot(dates, pushup_freq, label='pushup', marker='o', markersize=3)
        plt.title('exercise frequency')
        plt.xlabel('date')
        plt.ylabel('frequency')
        plt.xlim(0, 6)
        plt.legend()
        plt.grid(True)
        plt.xticks(dates)
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
    
    def point_score_line_chart(self):
        """绘制近7天运动评分折线图，保存为temp.png"""
        actscore_data = self.get_actscore_data()
        dates = [i for i in range(len(actscore_data))]
        squat_scores = [data[0] for data in actscore_data]
        situp_scores = [data[1] for data in actscore_data]
        pushup_scores = [data[2] for data in actscore_data]
        
        plt.figure(figsize=(2.133, 1.266))
        plt.plot(dates, squat_scores, label='squat', marker='o', markersize=2)
        plt.plot(dates, situp_scores, label='situp', marker='o', markersize=2)
        plt.plot(dates, pushup_scores, label='pushup', marker='o', markersize=2)
        plt.title('exercise score')
        plt.xlabel('date')
        plt.ylabel('score')
        plt.xlim(0, 6)
        plt.ylim(60, 100)
        plt.legend()
        plt.grid(True)
        plt.xticks(dates)
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
    
    def point_calories_line_chart(self):
        """绘制近7天卡路里消耗热力图，保存为temp.png"""
        actfrequency_data = self.get_actfrequency_data()
        # 卡路里计算：深蹲(0.2-0.5)、仰卧起坐(0.3-0.8)、俯卧撑(0.5-1)
        squat_calories = [data[0] * np.random.uniform(0.2, 0.5) for data in actfrequency_data]
        situp_calories = [data[1] * np.random.uniform(0.3, 0.8) for data in actfrequency_data]
        pushup_calories = [data[2] * np.random.uniform(0.5, 1.0) for data in actfrequency_data]
        calories_data = [squat_calories, situp_calories, pushup_calories]
        dates = [i for i in range(len(calories_data[0]))]
        
        plt.figure(figsize=(2.133, 1.266))
        sns.heatmap(calories_data, annot=True, fmt=".1f", cmap='YlGnBu', xticklabels=dates, yticklabels=['squat', 'sit up', 'push up'])
        plt.title('exercise calories distribution')
        plt.xlabel('date')
        plt.ylabel('exercise type')
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
    
    def point_time_proportion_pie_chart(self):
        """绘制近7天运动时间占比饼图（含总占比），保存为temp.png"""
        acttime_data = self.get_acttime_proportion()
        dates = [i for i in range(len(acttime_data))]
        squat_time = [data[0] for data in acttime_data]
        situp_time = [data[1] for data in acttime_data]
        pushup_time = [data[2] for data in acttime_data]
        
        fig, axs = plt.subplots(2, 4, figsize=(2.133, 1.266))
        axs = axs.flatten()
        for i in range(len(dates)):
            axs[i].pie([squat_time[i], situp_time[i], pushup_time[i]], 
                       labels=['squat', 'situp', 'pushup'], 
                       colors=['blue', 'orange', 'green'], 
                       autopct='%1.1f%%')
            axs[i].set_title(f'date: {dates[i]}')
        
        # 总占比
        axs[-1].pie([sum(squat_time), sum(situp_time), sum(pushup_time)],
                    labels=['squat', 'situp', 'pushup'], 
                    colors=['blue', 'orange', 'green'], 
                    autopct='%1.1f%%')
        axs[-1].set_title('Total time proportion')
        plt.tight_layout()
        plt.savefig('temp.png', bbox_inches='tight', dpi=300)
        
class csvManager:
    """CSV文件管理类（exercise_records.csv）"""
    def __init__(self, filename):
        self.filename = 'exercise_records.csv' if filename is None else filename
    
    def read_csv(self):
        """读取CSV为字典列表（格式:{'date','type','count','score'}）"""
        try:
            df = pd.read_csv(self.filename, encoding='utf-8')
            data_list = df.to_dict(orient='records')
            print(f"读取 {self.filename}，共 {len(data_list)} 条记录")
            return data_list
        except FileNotFoundError:
            print(f"文件 {self.filename} 不存在，返回空列表")
            return []
        except Exception as e:
            print(f"读取错误: {e}")
            return []
    
    def write_to_csv(self, data):
        """写入数据到CSV（每条为{'date','type','count','score'}）"""
        try:
            with open(self.filename, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for record in data:
                    if 'date' in record and 'type' in record and 'count' in record and 'score' in record:
                        writer.writerow([record['date'], record['type'], record['count'], record['score']])
                        print(f"写入记录: {record}")
        except Exception as e:
            print(f"写入错误: {e}")
        
    @staticmethod
    def clear_csv(self):
        """清空CSV内容"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                file.truncate(0)
                print(f"清空 {self.filename}")
        except Exception as e:
            print(f"清空错误: {e}")