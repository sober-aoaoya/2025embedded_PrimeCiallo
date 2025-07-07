import time
import cv2
import numpy as np
import sys
from UI.Ui_main import Ui_Form
from Dialog import CountDialog, TimerDialog
from Chart import MyDataDialog
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialogButtonBox
from PyQt5.QtCore import QThread, Qt, pyqtSignal, QRect, QTimer
#################### 姿态检测模块 #####################
from yolopose_rknn import *
from EMASmoothing import EMASmoothing
from Counter import Counter
from PoseClassify import BodyPoseEmbedder, PoseClassifier
#################### 串口模块 #####################
from MySerial import Myserial
#################### 网络模块 #####################
from flask import Flask, Response, render_template
from data_server import DataBroadcaster
import threading
#################### 模式检测模块 #####################
from yolo_rknn import YOLODetector, YOLOTracker


# --- Flask Web应用初始化 ---
app = Flask(__name__)
# --- 全局变量和锁 ---
web_frame_lock = threading.Lock()
web_frame = None
server = DataBroadcaster()

def send_data_to_app(count, score):
    server.send(count, score)

# HTTP 视频流生成器
def generate_video_stream():
    global web_frame
    while True:
        with web_frame_lock:
            # 如果 output_frame 为空 (例如，线程刚启动或摄像头有问题)，则跳过此次循环
            if web_frame is None:
                continue

            # 将帧编码为JPEG格式
            (flag, encoded_image) = cv2.imencode(".jpg", web_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

            # 确保编码成功
            if not flag:
                continue

        # 使用 multipart/x-mixed-replace MIME类型来构建HTTP响应
        # 这是MJPEG流的标准格式
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
              bytearray(encoded_image) + b'\r\n')

# Flask 路由
@app.route("/")
def index():
    # 将IP地址硬编码或动态获取以方便测试
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    """
    这个URL提供了MJPEG视频流。
    安卓App将会连接到这个地址。
    """
    # 返回一个流式响应，内容由 generate_video_stream 生成器提供
    return Response(generate_video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

class SendataThread(QThread):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.call_serial = Myserial('COM11')
        self.data = ''
        self._is_run = False
        
    def run(self):
        self._is_run = True
        self.call_serial.write(f"{self.data}\r\n")
        time.sleep(0.1)
        self.call_serial.res = ''
        print('发送完成')
        self.stop()
        
    def stop(self):
        self.wait()
        self._is_run = False

class VideoThread(QThread):
    act_mode_detected_signal = pyqtSignal(int)
    change_pixmap_signal = pyqtSignal(np.ndarray)
    change_count_signal = pyqtSignal(int)
    change_ir_count_signal = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self._run_flag = False
        self._initialized = False
        self.detection_confidence = 0.7
        self.tracking_confidence = 0.7
        self.pose_samples_folder = 'squat.csv'
        self.class_name = 'down'
        self.yolo_need = False
        self.detection_confirmed = False
        
        self.pose_tracker = None
        self.pose_embedder = None
        self.pose_classifier = None
        self.pose_classification_filter = None
        self.repetition_counter = None
        self.yolo_detector = None
        self.yolo_tracker = None
        self.cap = None
        
    def set_detection_confidence(self, value):
        self.detection_confidence = value
        
    def set_tracking_confidence(self, value):
        self.tracking_confidence = value
        
    def set_pose_option(self, option):
        self.pose_option = option
        
    def initialize(self):
        if self._initialized:
            self.cleanup()
            
        print("初始化视频线程组件...")
        self.pose_tracker = yolo_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        print("初始化姿态追踪器")
        
        self.pose_embedder = BodyPoseEmbedder()
        print("初始化姿态嵌入器")
        
        self.pose_classifier = PoseClassifier(
            pose_samples_folder=self.pose_samples_folder,
            pose_embedder=self.pose_embedder,
            top_n_by_max_distance=30,
            top_n_by_mean_distance=10)
        print("初始化姿态分类器")
        
        self.pose_classification_filter = EMASmoothing(window_size=10, alpha=0.2)
        print("初始化EMA平滑器")
        
        self.repetition_counter = Counter(class_name=self.class_name, enter_threshold=6, exit_threshold=4)
        print("初始化计数器")
        
        self.yolo_detector = YOLODetector()
        print("初始化YOLO目标检测器")
        
        self.yolo_tracker = YOLOTracker(detector=self.yolo_detector)
        print("初始化YOLO目标追踪器")
        
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            print("Cannot open camera")
            return False
            
        self._initialized = True
        return True
    
    def set_yolo_need(self, need: bool):
        self.yolo_need = need
        
    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
            self.cap = None
            
        if self.pose_tracker:
            self.pose_tracker.close()
            self.pose_tracker = None
            
        if self.yolo_detector:
            self.yolo_detector.release()
            self.yolo_detector = None
            self.yolo_tracker = None
            
        self._initialized = False
        print("资源已清理")
        
    def run(self):
        """线程执行的主函数"""
        if not self._initialized and not self.initialize():
            return
        
        if self.yolo_need:
            self._run_flag = True
            self.detection_confirmed = False
            
            while self._run_flag:
                ret, frame = self.cap.read()
                if not ret:
                    print("Cannot read frame")
                    break
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yolo_results, yolo_index = self.yolo_tracker.process_frame(rgb_frame)
                # 显示确认的检测结果
                if yolo_index is not None:
                    class_name = self.yolo_detector.get_class_names()[yolo_index]
                    cv2.putText(yolo_results, 
                                f"result: {class_name} ({yolo_index})", 
                                (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 
                                0.7, (0, 0, 255), 2)
                    self.detection_confirmed = True
                    output_frame = cv2.cvtColor(yolo_results, cv2.COLOR_RGB2BGR)
                    # 发到网络
                    with web_frame_lock:
                        global web_frame
                        web_frame = output_frame.copy()
                    ######################################
                    self.change_pixmap_signal.emit(output_frame)
                    self.act_mode_detected_signal.emit(yolo_index)
                    self.set_yolo_need(False)
                    self.msleep(10)
                    break
                else:
                    cv2.putText(yolo_results, 
                                "detecting...", 
                                (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 
                                0.7, (0, 255, 0), 2)
                
                output_frame = cv2.cvtColor(yolo_results, cv2.COLOR_RGB2BGR)
                # 发到网络
                with web_frame_lock:
                    web_frame = output_frame.copy()
                ######################################
                self.change_pixmap_signal.emit(output_frame)
                
        self._run_flag = True
        repetitions_count_monitored = 0
        ir_repetitions_count_monitored = 0
        
        while self._run_flag:
            ret, frame = self.cap.read()
            if not ret:
                print("Cannot read frame")
                break
            
            #cv2.imshow('Camera Feed', frame)
            #cv2.waitKey(1)    
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose_tracker.process(rgb_frame)
            output_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks:
                yolo_drawing.draw_landmarks(
                    output_frame,
                    results.pose_landmarks,
                    yolo_pose.POSE_CONNECTIONS,
                    yolo_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    yolo_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
            
            if results.pose_landmarks:
                frame_height, frame_width = output_frame.shape[0], output_frame.shape[1]
                pose_landmarks = np.array(
                    [[lmk.x * frame_width, lmk.y * frame_height, lmk.z * frame_width] for lmk in
                    results.pose_landmarks.landmark],
                    dtype=np.float32)
                assert pose_landmarks.shape == (33, 3), '意外的关键点形状: {}'.format(pose_landmarks.shape)

                pose_classification = self.pose_classifier(pose_landmarks)
                pose_classification_filtered = self.pose_classification_filter(pose_classification)
                repetitions_count, ir_repetitions_count = self.repetition_counter(pose_classification_filtered)
                if repetitions_count_monitored < repetitions_count:
                    self.change_count_signal.emit(repetitions_count)
                    print(f"计数更新: {repetitions_count} 次")
                    repetitions_count_monitored = repetitions_count
                if ir_repetitions_count_monitored < ir_repetitions_count:
                    self.change_ir_count_signal.emit(ir_repetitions_count)
                    print(f"不规范计数更新: {ir_repetitions_count} 次")
                    ir_repetitions_count_monitored = ir_repetitions_count
            else:
                pose_classification = None
                # 为未来帧进行平滑处理
                pose_classification_filtered = self.pose_classification_filter(dict())
                pose_classification_filtered = None
                # 获取最新的重复次数
                repetitions_count = self.repetition_counter.n_repeats
                if repetitions_count_monitored < repetitions_count:
                    self.change_count_signal.emit(repetitions_count)
                    print(f"计数更新: {repetitions_count} 次")
                    repetitions_count_monitored = repetitions_count
                if ir_repetitions_count_monitored < 0:
                    self.change_ir_count_signal.emit(0)
                    print("不规范计数更新: 0 次")
                    ir_repetitions_count_monitored = 0
            
            cv2.putText(output_frame, f"Counts: {self.repetition_counter.n_repeats}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255,255), 2)
            cv2.putText(output_frame, f"Irregular Counts: {self.repetition_counter.n_irregular}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
                        
            # 发到网络
            with web_frame_lock:
                web_frame = output_frame.copy()
            ######################################
            self.change_pixmap_signal.emit(output_frame)
            self.msleep(5)
        
        #cv2.destroyAllWindows()
        self.cleanup()
            
    def stop(self):
        """停止线程执行"""
        self._run_flag = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        
        self.mode = "计数模式"
        self.mode_flag = False
        self.act_mode = "俯卧撑模式"
        self.act_flag = False
        self.count = 0
        self.ir_count = 0
        self.time = 0  # 单位为秒
        self.mode_count = 0
        self.mode_time = 0  # 单位为秒
        self.score = 100
        self.mode_time_timer = QTimer()
        
        self.ui.setupUi(self)
        self.ui.startpushButton.clicked.connect(lambda: print("Start button clicked!"))
        self.ui.startpushButton.clicked.connect(self.start_act)
        self.ui.finishpushButton.clicked.connect(lambda: print("Finish button clicked!"))
        self.ui.finishpushButton.clicked.connect(self.stop_act)
        self.ui.mydatapushButton.clicked.connect(self.on_my_data_button_clicked)
        self.ui.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.on_ok_clicked)

        # 初始化为None，在start_act中创建
        self.vthread = None
        self.mode_time_timer.timeout.connect(self.on_mode_time_timer_timeout)
        
        self.sthread = SendataThread()
    
    def start_act(self):
        # 确保线程已停止并释放资源
        if self.vthread is not None:
            if self.vthread.isRunning():
                self.vthread.stop()
            self.vthread = None
        
        # 创建新的视频线程
        self.vthread = VideoThread()
        self.vthread.change_pixmap_signal.connect(self.update_image)
        self.vthread.change_count_signal.connect(self.on_count_changed)
        self.vthread.change_ir_count_signal.connect(self.on_ir_count_changed)
        self.vthread.act_mode_detected_signal.connect(self.on_act_mode_detected)
        
        if self.ui.actseccomboBox.currentText() == '自由模式':
            self.vthread.set_yolo_need(True)
        
        # 启动线程
        self.vthread.start()
        
        # 等待初始化完成
        while not self.vthread._initialized:
            time.sleep(0.1)
            
        # 更新UI状态
        self.ui.cameralabel.setGeometry(QRect(80, 30, 681, 461))
        q_pixmap = QPixmap('./assets/none.png')
        self.ui.cameralabel.setPixmap(q_pixmap)
        self.ui.scorelcdNumber.display(100)
            
        if not self.mode_flag:
            self.mode_flag = True
            self.mode = self.ui.modeseccomboBox.currentText()
            self.act_mode = self.ui.actseccomboBox.currentText()
            self.mode_time = 15  # 默认时间为15秒
            self.mode_count = 6  # 默认计数为6次
            self.count = 0
            self.ir_count = 0
            
        if not self.act_flag:
            self.act_flag = True
            self.act_mode = self.ui.actseccomboBox.currentText()
            
        if self.mode == "计时模式":
            self.mode_flag = True
            self.ui.countBox.lower()
            self.ui.timerBox.raise_()
            self.ui.targetimelcdNumber.display(self.mode_time)
            self.ui.timerprogressBar.setValue(0)
            self.time = 0
            self.mode_time_timer.start(1000)
        elif self.mode == "计数模式":
            self.mode_flag = True
            self.ui.timerBox.lower()
            self.ui.countBox.raise_()
            self.ui.targetlcdNumber.display(self.mode_count)
            self.ui.curlcdNumber.display(0)
            self.ui.countprogressBar.setValue(0)
            self.count = 0
            
        self.ui.startpushButton.setEnabled(False)
        self.ui.finishpushButton.setEnabled(True)
        
    def stop_act(self):
        # 停止视频线程
        if self.vthread is not None:
            if self.vthread.isRunning():
                self.vthread.stop()
            self.vthread = None
            
        # 停止计时器
        self.mode_time_timer.stop()
        self.sthread.stop()
        
        # 重置状态变量
        self.time = 0
        self.count = 0
        self.ir_count = 0
        self.mode_flag = False
        self.act_flag = False
        
        # 更新UI
        self.ui.startpushButton.setEnabled(True)
        self.ui.finishpushButton.setEnabled(False)
        time.sleep(0.1)

    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.ui.cameralabel.setPixmap(QPixmap.fromImage(q_image).scaled(
            self.ui.cameralabel.width(), self.ui.cameralabel.height(), Qt.KeepAspectRatio))   
    
    def on_ok_clicked(self):
        """OK按钮点击时根据选项弹出对应对话框"""
        current_option = self.ui.modeseccomboBox.currentText()
        if current_option == "计数模式":
            self.mode = "计数模式"
            dialog = CountDialog(self)
            dialog.count_set_signal.connect(self.on_count_set)
            dialog.exec_()
        elif current_option == "计时模式":
            self.mode = "计时模式"
            dialog = TimerDialog(self)
            dialog.timer_set_signal.connect(self.on_time_set)
            dialog.exec_()
            
    def on_time_set(self, time):
        """处理计时模式下的时间设置"""
        print(f"Selected time: {time.toString()}")
        self.mode_flag = True
        self.mode_time = time.minute() * 60 + time.second()
        
    def on_mode_time_timer_timeout(self):
        self.time += 1
        self.ui.targetimelcdNumber.display(self.mode_time - self.time)
        progress = int(self.time / self.mode_time * 100)
        if self.time >= self.mode_time:
            self.ui.timerprogressBar.setValue(progress)  
            self.stop_act()
        else:
            print(f"计时模式: 已运行 {self.time} 秒")
            self.ui.timerprogressBar.setValue(progress)
            self.mode_time_timer.start(1000)
            
    def on_count_set(self, count):
        """处理计数模式下的计数设置"""
        print(f"Selected count: {count}")
        self.mode_flag = True
        self.mode_count = count
    
    def on_count_changed(self, count):
        """更新计数显示"""
        self.count = count
        self.ui.curlcdNumber.display(self.count)
        progress = int(self.count / self.mode_count * 100)
        if self.count >= self.mode_count and self.mode == '计数模式':
            self.ui.countprogressBar.setValue(progress)
            self.score = self.generate_score()
            print(f"计数模式: 已完成 {self.count} 次，得分: {self.score}")
            self.ui.scorelcdNumber.display(self.score)
            send_data_to_app(self.count+self.ir_count, self.score)
            self.stop_act()
        elif self.mode == '计数模式':
            self.score = self.generate_score()
            print(f"计数模式: 已完成 {self.count} 次，得分: {self.score}")
            self.ui.scorelcdNumber.display(self.score)
            send_data_to_app(self.count+self.ir_count, self.score)
            self.ui.countprogressBar.setValue(progress)
            self.ui.prompttextEdit.setPlainText(
                f"当前模式: {self.act_mode}\n"
                "你当前的姿势很标准哦"
            )          
            self.voice()    
        elif self.mode == '计时模式':
            self.score = self.generate_score()
            print(f"计数模式: 已完成 {self.count} 次，得分: {self.score}")
            self.ui.scorelcdNumber.display(self.score)
            send_data_to_app(self.count, self.score)
            self.ui.prompttextEdit.setPlainText(
                f"当前模式: {self.act_mode}\n"
                f"当前计数: {self.act_mode}\n"
                "你当前的姿势很标准哦"
            )
            self.voice()
    def on_ir_count_changed(self, ir_count):
        """更新不规范计数显示"""
        self.ir_count += 1
        self.score = self.get_score()
        print(f"不规范计数: {ir_count} 次")
        self.ui.scorelcdNumber.display(self.score)
        send_data_to_app(self.count+self.ir_count, self.score)
        
    def voice(self, data='AAI'):
        if self.sthread._is_run==False:
            self.sthread.data = data
            self.sthread.start()
        elif self.sthread._is_run==True:
            self.sthread.stop()
            self.sthread.data = data
            self.sthread.start()
        
    def on_act_mode_detected(self, index):
        if index == 0:
            self.act_mode = '深蹲模式'
        elif index == 1:
            self.act_mode = '仰卧起坐模式'
        elif index == 2:
            self.act_mode = '俯卧撑模式'
    
    def get_score(self):
        return self.score
        
    def get_evaluation(self, rng: int):
        pass
    
    def on_my_data_button_clicked(self):
        print("我的数据按钮被点击")
        dialog = MyDataDialog(self)
        dialog.exec_()
        
if __name__ == "__main__":
    # 启动Flask Web服务器线程
    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8085, 'threaded': True})
    flask_thread.daemon = True
    flask_thread.start()
    server.start()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    server.stop()