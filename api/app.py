from flask import Flask, Response, jsonify, request
from .errors import errors
import subprocess
import tempfile
import os
import re


CIC ="cic "
INIT ="init "
DERIVE_ROOT ="derive_root"
DEFAULT_FILE ="/'Configuration (needs derivation).txt'"
DEFAULT_FILE_LAUNCH ="/'Configuration (awaiting launch).txt'"
LAUNCH_SIGNELTON = "launch_singleton "
PAYMENT = "payment "
PUSH_TX = "push_tx "
DEFAULT_FEE = "50000"
COMPLETE = "complete "
COMPLETE_FILE = "complete.signed"
CLAWBACK = "clawback "

app = Flask(__name__)
app.register_blueprint(errors)
@app.route("/")

def index():
    return Response("Hello, world!", status=200)

@app.route("/init", methods=["POST"])
def init():
    payload = request.get_json()
    if payload.get("init_singelton") is True:
        temp_dir = tempfile.TemporaryDirectory()
        withdraw_timelock=payload.get("withdraw_timelock")
        payment_clawback=payload.get("payment_clawback")
        rekey_timelock=payload.get("rekey_timelock")
        rekey_clawback=payload.get("rekey_clawback")
        slow_rekey_penalty=payload.get("slow_rekey_penalty")
        pubkeys_strings= payload.get("pubkeys_strings")
        current_lock_level = payload.get("current_lock_level")
        maximum_lock_level = payload.get("maximum_lock_level")
        print("create tempfiles")
        # Create temp file list
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'.pk'), 'w') as f:
                print("Create files:"+str(i+1))
                f.write(pubkeys_strings[i])
                f.seek(0)
                files.append(f)
                if((i+1)<len(pubkeys_strings)):
                    pub_fileNameList+=f.name + ","
                else:
                    pub_fileNameList+=f.name
                pass

        print(temp_dir.name)
           
        commandInit = CIC + INIT + " -d " + temp_dir.name + " -wt " + withdraw_timelock + " -pc " + payment_clawback + " -rt " + rekey_timelock + " -rc " + rekey_clawback + " -sp " + slow_rekey_penalty
        print(commandInit)

        commandDerive = CIC + DERIVE_ROOT + " -c " + temp_dir.name + DEFAULT_FILE + " -pks " + "'" + pub_fileNameList + "'" + " -m " + current_lock_level + " -n " + maximum_lock_level
        print(commandDerive)

        commandLaunchSingelton = CIC + LAUNCH_SIGNELTON + " -c " + temp_dir.name + DEFAULT_FILE_LAUNCH +" --fee " + DEFAULT_FEE
        print(commandLaunchSingelton)

        try:
            proc = subprocess.Popen(commandInit, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success init")
        except Exception as e:
            print("Error init")
            raise 

        try:
            proc = subprocess.Popen(commandDerive, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success derive")
        except Exception as e:
            print("Error derive")
            raise 

        try:
            proc = subprocess.Popen(commandLaunchSingelton, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success launch")
        except Exception as e:
            print("Error launch")
            raise

        commandGetFileName = "cd "+ temp_dir.name +" && "+ "ls " "*.txt"
        print(commandGetFileName)
        try:
            proc = subprocess.Popen(commandGetFileName, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            launched_fileName_full =  proc.stdout.read().decode("utf-8")
            print("Success Get File Name")
        except Exception as e:
            print("Error Get File Name")
            raise
        
        result = extract_string_between_parentheses(launched_fileName_full)

        commandFileContent = "cat " + temp_dir.name + "/'Configuration ("+result+").txt'" 
        print(commandFileContent)
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read()
            datahex=data.hex()
            databytes=bytes.fromhex(datahex)
            if(databytes==data):
                output = jsonify({"launched_singelton_hex": datahex, "id": result})
            else:
                output = "..."
            print("Success Get File Content")
        except Exception as e:
            output = "..."
            print("Error Get File Content")
            raise

        list(map(lambda f: f.close(), files))
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})
    
    return output

@app.route("/status", methods=["POST"])
def status():
    payload = request.get_json()

    if payload.get("sync") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        temp_dir = tempfile.TemporaryDirectory()
        bytes_data = bytes.fromhex(data)

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ f.name +" -db " + temp_dir.name
        print(commandStatus)
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        commandStatusShow= "cd "+ temp_dir.name+" && cic sync -s" 
        print(commandStatusShow)
        try:
            proc = subprocess.Popen(commandStatusShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            status = proc.stdout.read().decode("utf-8")
            status = status.replace('\n', ' ')
            output=jsonify({"launched_singelton_info": status})
        except Exception as e:
            print("Error status show")
            raise
        
        temp_dir.cleanup()

    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/get_address", methods=["POST"])
def get_address():
    payload = request.get_json()

    if payload.get("address") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ f.name +" -db " + temp_dir.name
        print(commandStatus)
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        commandStatusShow= "cd "+ temp_dir.name +" && cic p2_address --prefix txch" 
        print(commandStatusShow)
        try:
            proc = subprocess.Popen(commandStatusShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            address=proc.stdout.read().decode("utf-8")
            address=address.replace('\n', '')
            output=jsonify({"vault_address": address })
        except Exception as e:
            print("Error get address")
            raise
        
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/withdrawal", methods=["POST"])
def withdrawal():
    payload = request.get_json()

    if payload.get("withdrawal_create") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()
        pubkeys_strings = payload.get("pubkeys_strings")
        withdraw_mojos = payload.get("withdraw_mojos")
        recipient_address = payload.get("recipient address") 

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as temp_file:
            temp_file.write(bytes_data)
            temp_file.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ temp_file.name +" -db " + temp_dir.name
        print(commandStatus)
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        # Create temp file list
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'.pk'), 'w') as f:
                print("Create files:"+str(i+1))
                f.write(pubkeys_strings[i])
                f.seek(0)
                files.append(f)
                if((i+1)<len(pubkeys_strings)):
                    pub_fileNameList+=f.name + ","
                else:
                    pub_fileNameList+=f.name
                pass

        commandWithdraw = CIC + PAYMENT + "-db " + temp_dir.name + " -f "+ temp_dir.name +"/withdrawal.unsigned" + " -pks " + "'" + pub_fileNameList + "'" + " -a " + withdraw_mojos + " -t " + recipient_address +" -ap"
        print(commandWithdraw)
        try:
            proc = subprocess.Popen(commandWithdraw, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error launch")
            raise

        commandFileContent = "cat " + temp_dir.name + "/withdrawal.unsigned"
        print(commandFileContent)
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            output = jsonify({"withdrawal_unsigned": data})
        except Exception as e:
            output = "..."
            print("Error withdrawal unsigned")
            raise
        list(map(lambda f: f.close(), files))
        f.close()
        temp_dir.cleanup()
    elif payload.get("withdrawal_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        data = payload.get("withdrawal_signed")
        bytes_data = bytes.fromhex(data)

        with open(os.path.join(temp_dir.name, 'withdrawal.signed'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass

        commandWithdrawPush = CIC + PUSH_TX + "-b " + f.name + " -m " + DEFAULT_FEE
        print(commandWithdrawPush)
        try:
            proc = subprocess.Popen(commandWithdrawPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            output = jsonify({"message": "Successfull withdrawal_push"})
        except Exception as e:
            print("Error withdrawal push")
            output = jsonify({"message": "..."})
            raise
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/complete", methods=["POST"])
def complete():
    payload = request.get_json()

    if payload.get("complete") is True:
       
       payment_index= payload.get("payment_index")
       temp_dir = tempfile.TemporaryDirectory()
       data=payload.get("launched_singelton_hex")
       id=payload.get("id")

       bytes_data = bytes.fromhex(data)
       
       with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass
       
       commandStatus = CIC + "sync -c "+ f.name +" -db " + temp_dir.name
       print(commandStatus)
       try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
       except:
           print("Error sync")
           raise
       
       commandSync = "cd "+ temp_dir.name + " && "+ CIC + "sync -s "
       print(commandSync)
       try:
            proc = subprocess.Popen(commandSync, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
       except:
           print("Error sync")
           raise
    
       commandComplete = "cd "+ temp_dir.name + " && "+ CIC + COMPLETE + " -f "+ temp_dir.name +"/complete.signed"
       print(commandComplete)
       try:
            proc = subprocess.Popen(commandComplete, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            input_bytes = payment_index.encode('utf-8') + b'\n'
            proc.stdin.write(input_bytes)
            proc.stdin.close()
            output = proc.stdout.read().decode('utf-8')
            print(output)
       except Exception as e:
            print ("Error complete create")
            raise
       
       commandFileContent = "cat " + temp_dir.name + "/complete.signed"
       print(commandFileContent)
       try:
           proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
           proc.wait()
           proc.stdin.close()
           data=proc.stdout.read().decode("utf-8")
           print(data) 
       except Exception as e:
           print("Error get Complete")
           raise

       commandCompletePush = CIC + PUSH_TX + "-b "+ temp_dir.name +"/complete.signed" + " -m " + DEFAULT_FEE
       print(commandCompletePush)
       try:
            proc = subprocess.Popen(commandCompletePush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            output = proc.stdout.read().decode('utf-8')
       except Exception as e:
            print ("Error complete create")
            output = jsonify({"message": "..."})
            raise
       temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/clawback", methods=["POST"])
def clawback():
    payload = request.get_json()
    
    if payload.get("clawback_create") is True:
        clawback_unsigned=payload.get("clawback_unsigned")
        pubkeys_strings = payload.get("pubkeys_strings")

        temp_dir = tempfile.TemporaryDirectory()
        tempFile = tempfile.NamedTemporaryFile('w+t',suffix='.unsigned', dir=temp_dir.name)
        tempFile.write(clawback_unsigned)
        tempFile.seek(0)

        # Create temp file list
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            f = tempfile.NamedTemporaryFile('w+t',suffix=str(i+1)+'.pk', dir=temp_dir.name)
            f.write(pubkeys_strings[i])
            f.seek(0)
            files.append(f)
            if((i+1)<len(pubkeys_strings)):
                pub_fileNameList+=(f.name)+","
            else:
                pub_fileNameList+=(f.name)

        commandClawback = CIC + CLAWBACK + " -f " + temp_dir +"/"+tempFile.name +" -pks " + pub_fileNameList
        try:
            proc = subprocess.Popen(commandClawback, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print ("Error clawback create")
            raise

        list(map(lambda f: f.close(), files))
        tempFile.close()
        temp_dir.cleanup()  

    elif payload.get("clawback_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        clawback_signed = payload.get("clawback_signed")
        file = tempfile.NamedTemporaryFile('w+t',suffix='.signed', dir=temp_dir.name)
        file.write(clawback_signed)
        file.seek(0)

        commandClawbackPush = CIC + PUSH_TX + "-b " + temp_dir.name + "/" + file.name + " -m " + DEFAULT_FEE
        print(commandClawbackPush)
        try:
            proc = subprocess.Popen(commandClawbackPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error clawback push")
            raise

        file.close()
        temp_dir.cleanup()    
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/spendbundle", methods=["POST"])
def custom():
    payload = request.get_json()

    if payload.get("generate_spendbundle") is True:
        data=payload.get("pubkeys_strings")
        output = jsonify({"message": data[0] })
    else:
        output = jsonify({"message": "..."})

    return output


@app.route("/health")
def health():
    return Response("OK", status=200)

def extract_string_between_parentheses(string):
    match = re.search(r'\((.*?)\)', string)
    if match:
        return match.group(1)
    else:
        return None

