import sys
import time
import network
import urequests
import machine
from i2c_lcd import I2cLcd 

DURATION_FOR_AUTO_INCREASING = 3
BUFFER_DURATION = 0
DURATION_FOR_UPDATE = 15000
DURATION_FOR_10_MS = 10
update_time = time.ticks_ms()
update_10ms = time.ticks_ms()
index = 9
old_index = 8


#configure esp as a network station
sta = network.WLAN(network.STA_IF)
if not sta.isconnected(): 
  print('connecting to network...') 
  sta.active(True) 
  sta.connect('QUANG THAI','lan1457201') 
  while not sta.isconnected(): 
    pass 
print('network config:', sta.ifconfig())

HTTP_HEADERS = {'Content-Type': 'application/json'} 
THINGSPEAK_WRITE_API_KEY = '9FCZF9HO7Z9H55N7'   
response = ""


#define TDS Pin 
TDS = machine.ADC(machine.Pin(34))          
TDS.atten(machine.ADC.ATTN_11DB)
TDS.width(machine.ADC.WIDTH_10BIT)


#define LCD1602
DEFAULT_I2C_ADDR = 0x27
i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=500000) 
lcd = I2cLcd(i2c, DEFAULT_I2C_ADDR, 2, 16)


#define buttons
ModeButton = machine.Pin(14, machine.Pin.IN)
LeftButton = machine.Pin(16, machine.Pin.IN)
EnterButton = machine.Pin(17, machine.Pin.IN)
RightButton = machine.Pin(25, machine.Pin.IN)


# BUTTON buffer for debouncing
counterForBTN_Press30ms = {
"btn_mode": 0,
"btn_left": 0,
"btn_enter": 0,
"btn_right": 0
}

flagForBTN_Press30ms = {
"btn_mode": False,
"btn_left": False,
"btn_enter": False,
"btn_right": False
}
#define initial mode
MODE = 0
#helping function
def switchMode(MODE):
    global response
    global update_10ms
    global update_time
    if MODE == 0:
      MODE = 1
      lcd.clear()
      lcd.putstr('MEASURING....')
    elif MODE == 1:
      response = urequests.get('https://api.thingspeak.com/channels/1558497/fields/1.json?api_key=1BLMFWISBOB60LD2&results=10')
      lcd.clear()
      lcd.putstr('RECEIVING DATA')
      MODE = 2
    elif MODE == 2:
      lcd.clear()
      lcd.putstr('   CHANGE MEASURING PERIOD')
      MODE = 3
    elif MODE == 3:
      lcd.clear()
      lcd.putstr('WAITING MODE')
      MODE = 0
    update_10ms = time.ticks_ms()
    update_time  = time.ticks_ms()
    return MODE


def lcd_display(TDS_value, mode):
    lcd.clear()
    if mode == 0:
      lcd.putstr('waiting to turn on....')
    elif mode == 1:
      lcd.putstr('TDS:{} ppm'.format(TDS_value))
    elif mode == 2:
      lcd.putstr('old TDS:{} ppm'.format(TDS_value))
 
 
if MODE == 0:
    lcd.clear()
    lcd.putstr('WAITING MODE')
elif MODE == 1:
    lcd.clear()
    lcd.putstr('MEASURING....')
elif MODE == 2:
    lcd.clear()
    lcd.putstr('RECEIVING DATA')
elif MODE == 3:
    lcd.clear()
    lcd.putstr('CHANGE MEASURING     PERIOD')

while True:
    if time.ticks_ms() - update_10ms >= DURATION_FOR_10_MS:
      btn_state={
       "btn_mode": 0,
       "btn_left": 0,
       "btn_enter": 0,
       "btn_right": 0
      } 
      btn_state['btn_mode'] = int(ModeButton.value())
      btn_state['btn_left'] = int(LeftButton.value())
      btn_state['btn_enter'] = int(EnterButton.value())
      btn_state['btn_right'] = int(RightButton.value())
      
      for btn in btn_state:
        if btn_state[btn] == 1 and flagForBTN_Press30ms[btn] == False:
          if btn == "btn_mode":
            if counterForBTN_Press30ms[btn] < DURATION_FOR_AUTO_INCREASING: #<30ms        
              counterForBTN_Press30ms[btn] += 1
            else:
              MODE = switchMode(MODE)
              if MODE == 2:
                index = 9
                old_index = index - 1
              elif MODE == 3:
                BUFFER_DURATION = int(DURATION_FOR_UPDATE /1000)
                lcd.clear()
                lcd.putstr('PERIOD:{} s'.format(BUFFER_DURATION))
              flagForBTN_Press30ms[btn] = True
          elif (btn == "btn_left" or btn == "btn_right") and (MODE == 2 or MODE == 3):
            if counterForBTN_Press30ms[btn] < DURATION_FOR_AUTO_INCREASING:
              counterForBTN_Press30ms[btn] += 1
            else:
              if btn == "btn_left":
                if MODE == 2 and index > 0:
                  index -= 1
                elif MODE == 3 and BUFFER_DURATION > 15:
                  BUFFER_DURATION -= 1
                  lcd.clear()
                  lcd.putstr('Period:{} s'.format(BUFFER_DURATION)) 
                  print('PERIOD:{} s'.format(BUFFER_DURATION))
              elif btn == "btn_right":
                if MODE ==2 and index < 9:
                  index+=1
                elif MODE == 3:
                  BUFFER_DURATION += 1
                  lcd.clear()
                  lcd.putstr('PERIOD:{} s'.format(BUFFER_DURATION))
                  print('PERIOD:{} s'.format(BUFFER_DURATION))
              flagForBTN_Press30ms[btn] = True
          elif btn == "btn_enter" and MODE == 3:
            if counterForBTN_Press30ms[btn] < DURATION_FOR_AUTO_INCREASING:
              counterForBTN_Press30ms[btn] += 1
            else:
              DURATION_FOR_UPDATE = int(BUFFER_DURATION * 1000)
              lcd.clear()
              lcd.putstr('PERIOD IS SET')
              flagForBTN_Press30ms[btn] = True
              print('NEW PERIOD IS:{} s'.format(BUFFER_DURATION))
        else:
          if btn_state[btn] == 0:
            counterForBTN_Press30ms[btn] = 0
            flagForBTN_Press30ms[btn] = False
      update_10ms = time.ticks_ms()
   
    if time.ticks_ms() - update_time >= DURATION_FOR_UPDATE and MODE == 1:
      tds_value = 0 
      tds_value = TDS.read()
      lcd_display(TDS_value=tds_value, mode= 1)
      print('TDS value', tds_value)
      post_val = {'field1':tds_value }
      request = urequests.post( 
        'http://api.thingspeak.com/update?api_key=' + THINGSPEAK_WRITE_API_KEY, 
        json = post_val, 
        headers = HTTP_HEADERS )  
      request.close()
      update_time = time.ticks_ms()
    
    if MODE == 2:      
      data = response.json()
      if old_index != index:
        field1 = str(data['feeds'][index]['field1'])
        print('old value', field1)      
        lcd_display(TDS_value=field1, mode= 2)
        old_index = index 
 



