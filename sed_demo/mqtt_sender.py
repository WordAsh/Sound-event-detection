import json
import time
import paho.mqtt.client as mqtt
import random
from datetime import datetime

# MQTT服务器地址和端口
HOST = "124.223.103.23"
PORT = 1883
TOPIC = "unity/test"
sound_types = ["water", "baby", "car", "fire", "animal", "nock", "music"]

water_set = {"Water","Rain"}
baby_set = {"Baby laughter","Baby cry, infant cry"}
car_set = {"Vehicle","Motor vehicle (road)","Car","Truck","Bus","Emergency vehicle","Motorcycle","Train","Subway, metro, underground","Bicycle"}
fire_set = {"Fire"}
animal_set = {"Animal","Domestic animals, pets","Dog","Bark","Cat","Horse","Cowbell","Pig","Goat","Sheep","Chicken, rooster","Duck","Goose","Wild animals","Bird","Pigeon, dove","Crow","Owl","Bird flight, flapping wings","Insect","Cricket","Mosquito","Frog","Snake"}
knock_set = {"Door","Doorbell","Knock","Bang"}
alarm_set = {"Car alarm","Police car (siren)","Ambulance (siren)","Alarm","Alarm clock","Smoke detector, smoke alarm","Fire alarm","Siren"}

sets = [water_set,baby_set,car_set,fire_set,animal_set,knock_set,alarm_set]
sound_types = ["water", "baby", "car", "fire", "animal", "knock","alarm"]

# MQTT客户端设置
client = mqtt.Client()


def find_sound_type(sound_type):
    if sound_type == "Silence" or sound_type == "Noise" or sound_type == "Music":
        return None
    for i,s in enumerate(sets):
        if sound_type in s:
            return sound_types[i]


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # 连接成功后提醒用户可以发送消息
    print("Ready to send a message.")

def on_publish(client, userdata, mid):
    print("Message Published.")

def send_message(client,sound_type):
    # 获取当前日期和时间
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    # 随机选择一个声音类型
    data = {
        "date": current_date,
        "time": current_time,
        "soundType": sound_type,
    }
    json_data = json.dumps(data)
    client.publish(TOPIC, json_data)

def get_client():
    client = mqtt.Client()
    # 设置连接和发布消息的回调函数
    client.on_connect = on_connect
    client.on_publish = on_publish
    # 连接到MQTT服务器
    client.connect(HOST, PORT, 60)
    # 非阻塞方式调用，客户端会在后台不断尝试与服务器进行通信
    client.loop_start()
    return client

# # 主程序循环，等待按键事件
# try:
#     while True:
#         if keyboard.is_pressed('p'):  # 检测'p'键是否被按下
#             send_message()
#             time.sleep(0.2)  # 防止因按键过快而发送过多消息
# except KeyboardInterrupt:
#     print("程序中断")

# # 停止循环和断开连接
# client.loop_stop()
# client.disconnect()