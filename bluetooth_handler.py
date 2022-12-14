import bluetooth
import subprocess
import json
import os
import io
from time import sleep
from database_logger import fetch_guid

def discover_devices():
    subprocess.check_output('sudo hciconfig hci0 sspmode 1',shell=True)
    subprocess.check_output('sudo hciconfig hci0 piscan', shell = True)
    print("Discovering...")
    
def clear_devices():
    connectedDevices = subprocess.check_output("bluetoothctl devices",shell=True).decode('utf-8')
    while connectedDevices != "":
        deviceID = connectedDevices[7:24:1]
        connectedDevices = connectedDevices[connectedDevices.index("\n")+1:len(connectedDevices):1]
        os.system("sudo bluetoothctl disconnect {}".format(deviceID))
        os.system("sudo bluetoothctl remove {}".format(deviceID))
        print("Removed {} from the pairing.".format(deviceID))
    
def Credential_Accepter(app):
    credentials_raw = app.recv(1024).decode("ascii")
    credentials = json.loads(credentials_raw)
    username = credentials["username"]
    print(username)
    password = credentials["password"]
    print(password)
    if not os.path.exists("/home/pi/Athena Data"):
        path = os.path.join("/home/pi","Athena Data")
        try:
            os.mkdir(path)
        except:
            print("Directory Creation Error")
            return None
    with open("/home/pi/Athena Data/Credentials.txt", "w") as cred_file:
        cred_file.write(username+"\r"+password)
        cred_file.close()
    
def Wifi_Scanner(app):
    scan_success = False
    while not scan_success:
        try:#returns in bytes, so can be sent with encoding first
            scanned_wifi = subprocess.check_output('sudo iwlist wlan0 scan|grep SSID', shell=True)
            if scanned_wifi == "wlan0     Interface doesn't support scanning : Device or resource busy":
                raise
            scan_success = True
        except:
            scan_success = False
    wifiList = Reformat_Wifi(scanned_wifi)
    payload = json.dumps(wifiList)
    print(payload)
    app.send(payload.encode('utf-8'),10240)

def Reformat_Wifi(rawBytes):
    wifiList = []
    raw = rawBytes.decode('utf-8')
    while raw != "":
        item = ""
        raw = raw.strip()
        if "\n" in raw:
            item = raw[0:raw.index("\n")]
        else:
            item = raw
        raw = raw.replace(item, "")
        item = item.replace("ESSID:\"","")
        item = item.replace("\"\n","")
        item = item.replace("\"","")
        item = item.replace("\\x00","")
        if item.strip() != "" and item not in wifiList:
            wifiList.append(item)
    
    return wifiList

def Connect_Wifi(app):
    print("Connection Attempt Started")
    reset = False
    while not reset:
        print("Wifi creds listening")
        wifi_data_raw = app.recv(1024).decode('ascii')
        print(wifi_data_raw)
        if wifi_data_raw != "Reset":
            reset = True
            wifi_data = json.loads(wifi_data_raw)
            print(wifi_data)
            #After getting data...
            ssid = wifi_data["SSID"]
            ssid = ssid.strip()
            print(ssid)
            username = wifi_data["identity"]
            if username is not None:
                username = username.strip()
            key = wifi_data["key"]
            key = key.strip()
            print(key)

            subprocess.check_output('sudo sh -c \"wpa_passphrase \'{}\' \'{}\' >> /etc/wpa_supplicant/wpa_supplicant.conf"'.format(ssid, key),shell=True)
            print('sudo sh -c \"wpa_passphrase \'{}\' \'{}\' >> /etc/wpa_supplicant/wpa_supplicant.conf"'.format(ssid, key))
        else:
            Wifi_Scanner(app)
            reset = False
    Reconfigure_Wifi()
    return Check_Connection()

def Reconfigure_Wifi():
    subprocess.check_output('sudo wpa_cli -i wlan0 reconfigure', shell = True)
    
def Check_Connection():
    i = 0
    LINE_UP = '/033[1A'
    LINE_CLEAR = '/x1b[2K'
    print("Checking WiFi Connection...")
    while i <= 30:
        #This doesn't account for website requiring logins
        print('\r',"Attempting Connection... {}".format(i), sep='',end='',flush = True)
        try:
            result = subprocess.check_output('sudo iwgetid', shell = True)
            if result is not None:
                print('')
                return True
            else:
                sleep(1)
                i = i + 1
        except:
            sleep(1)
            i = i + 1
    print('')
    return False
    
def get_guid():
    with open("/home/pi/Athena Data/Credentials.txt", "r") as cred_file:
        raw = cred_file.read()
        print("Found file with data")
        username = raw[0:raw.index('\n')].strip()
        password = raw[raw.index('\n'):len(raw)].strip()
        cred_file.close()
    
    print("Running fetch_guid")
    guid = fetch_guid(username, password)
    if guid == False:
        #Something happened
        print("Uh oh! Login failed!!!")
    elif guid == None:
        #Connection failed
        print("Connection failed!")
    else:
        with open("/home/pi/Athena Data/Guid.txt", "w+") as guid_file:
            guid_file.write(guid)
            guid_file.close()
        os.remove("/home/pi/Athena Data/Credentials.txt")
        print("Got Guid")

def OnboardingProcess():
    is_connected = Check_Connection()
    if not is_connected:
        print("Not Connected... Starting Onboarding.")
        try:
            os.remove("/home/pi/Athena Data/Guid.txt")
            os.remove("/home/pi/Athena Data/Uuid.txt")
        except:
            print("No previous GUID found")
        error = True
        while error:
            try:
                clear_devices()
                discover_devices()
                
                sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                print("sock created")
                sock.bind(("",1))
                sock.listen(1)
                print("listening")
                
                uuid = "a0f9aa1c-465a-45be-8fab-e2c9670ee7c9"
                bluetooth.advertise_service(sock, "ATHENA", service_id=uuid)
                print("Advertising service")
                app_sock, addr = sock.accept()
                print("Accepted connection from ", addr)
                subprocess.check_output('sudo hciconfig hci0 noscan', shell=True)
                Credential_Accepter(app_sock)
                
                Wifi_Scanner(app_sock)
                print("Starting connection read")
                while not is_connected:
                    is_connected = Connect_Wifi(app_sock)
                    print(is_connected)
                    app_sock.send(str(is_connected).encode('ascii'))
                    
                print("Connected successfully! Fetching GUID for use")
                
                app_sock.close()
                sock.close()
                get_guid()
                
                print("GUID successfully obtained! Beginning logging...")
                error = False
            except Exception as BIGOOF:
                #reset everything
                error = True
                print(BIGOOF)
    else:
        print("Already Connected")
    
    #data = phone_sock.recv(1024)
#print("received [%s]" % data)


#OnboardingProcess()
#data = app_sock.recv(1024).decode('ascii')
#print(data)

#newData = "General Kenobi"
#newData = newData.encode('ascii')
#app_sock.send(newData)