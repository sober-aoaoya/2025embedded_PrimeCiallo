#include "asr.h"
extern "C"{ void * __dso_handle = 0 ;}
#include "setup.h"
#include "myLib/asr_event.h"
#include "HardwareSerial.h"

uint32_t snid;
void UART1_RX();
void ASR_CODE();

//{speak:云儿-温柔女声,vol:10,speed:6,platform:haohaodada,version:V3}
//{playid:10001,voice:}
//{playid:10002,voice:}

void UART1_RX(){
  while (1) {
    if(Serial.available() > 0){
      //串口接收字符串必须临时声明字符串变量，如下所示
      String Rec = "";
      Rec = Serial.readString();
      Serial.println(Rec);
      if((((uint8_t)(Rec[(int)(0)])) == 0x41) && (((uint8_t)(Rec[(int)(1)])) == 0x41)){
        if(((uint8_t)(Rec[(int)(2)])) == 0x41){
          //{playid:10500,voice:身体下沉过低可能会导致肩部受伤}
          play_audio(10500);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x42){
          //{playid:10501,voice:向下动作不够到位哦}
          play_audio(10501);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x43){
          //{playid:10502,voice:向上动作不够到位哦}
          play_audio(10502);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x44){
          //{playid:10503,voice:注意你的后腿碰到地板了}
          play_audio(10503);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x45){
          //{playid:10504,voice:身体下沉过低可能会导致膝盖受伤}
          play_audio(10504);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x46){
          //{playid:10505,voice:注意双手抱头哦}
          play_audio(10505);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x47){
          //{playid:10506,voice:身体下沉过低，可能会导致腰部受伤}
          play_audio(10506);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x48){
          //{playid:10507,voice:注意双腿不要抬起哦}
          play_audio(10507);
        }
        if(((uint8_t)(Rec[(int)(2)])) == 0x49){
          //{playid:10508,voice:你的姿势很标准哦}
          play_audio(10508);
        }
      }
    }
    delay(2);
  }
  vTaskDelete(NULL);
}

/*描述该功能...
*/
void ASR_CODE(){
  //语音识别功能框，与语音识别成功时被自动调用一次。

}

void hardware_init(){
  //需要操作系统启动后初始化的内容
  vol_set(7);
  setPinFun(13,SECOND_FUNCTION);
  setPinFun(14,SECOND_FUNCTION);
  Serial.begin(9600);
  xTaskCreate(UART1_RX,"UART1_RX",256,NULL,4,NULL);
  vTaskDelete(NULL);
}

void setup()
{
  //需要操作系统启动前初始化的内容
  set_wakeup_forever();
  //{ID:0,keyword:"命令词",ASR:"坤坤",ASRTO:"主人我在呢"}
}
